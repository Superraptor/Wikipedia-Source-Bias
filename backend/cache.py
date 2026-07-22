import hashlib
import json

PENDING = "pending"
RUNNING = "running"
DONE = "done"
ERROR = "error"

MAX_ATTEMPTS = 3


class Cache:
    """MariaDB-backed cache *and* job queue. Conn is a DB-API 2.0 connection.

    A row is simultaneously the cache entry and the queue item; `status` says
    which. Only the worker ever writes results, so the web tier never blocks on
    an analysis -- see backend/worker.py.
    """

    def __init__(self, conn):
        self.conn = conn

    @staticmethod
    def _hash(url):
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def _commit(self):
        commit = getattr(self.conn, "commit", None)
        if commit is not None:
            commit()

    # -- read path -------------------------------------------------------

    def get(self, url):
        """Completed result for `url`, or None if absent/pending/failed."""
        h = self._hash(url)
        cur = self.conn.cursor()
        try:
            cur.execute(
                "SELECT result FROM analysis_cache "
                "WHERE url_hash = %s AND status = 'done'",
                (h,),
            )
            row = cur.fetchone()
        finally:
            cur.close()
        if row is None or row[0] is None:
            return None
        return json.loads(row[0])

    def status_of(self, url):
        """(status, error) for `url`; (None, None) when the row is absent."""
        h = self._hash(url)
        cur = self.conn.cursor()
        try:
            cur.execute(
                "SELECT status, error FROM analysis_cache WHERE url_hash = %s",
                (h,),
            )
            row = cur.fetchone()
        finally:
            cur.close()
        if row is None:
            return None, None
        return row[0], row[1]

    # -- write path ------------------------------------------------------

    def set(self, url, payload):
        """Store a completed analysis."""
        h = self._hash(url)
        page_title = payload.get("page_title")
        source_count = payload.get("source_count")
        blob = json.dumps(payload, ensure_ascii=False)
        cur = self.conn.cursor()
        try:
            cur.execute(
                "REPLACE INTO analysis_cache "
                "(url_hash, page_url, page_title, result, source_count, status) "
                "VALUES (%s, %s, %s, %s, %s, 'done')",
                (h, url, page_title, blob, source_count),
            )
        finally:
            cur.close()
        self._commit()

    def enqueue(self, url):
        """Register `url` for analysis. Idempotent; never clobbers a result."""
        h = self._hash(url)
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO analysis_cache (url_hash, page_url, status) "
                "VALUES (%s, %s, 'pending') "
                "ON DUPLICATE KEY UPDATE "
                "  status = IF(status = 'error' AND attempts < %s, 'pending', status)",
                (h, url, MAX_ATTEMPTS),
            )
        finally:
            cur.close()
        self._commit()

    # -- worker path -----------------------------------------------------

    def claim_next(self):
        """Atomically take one pending URL, or None. Returns the page URL."""
        cur = self.conn.cursor()
        try:
            cur.execute(
                "SELECT url_hash, page_url FROM analysis_cache "
                "WHERE status = 'pending' ORDER BY created_at LIMIT 1"
            )
            row = cur.fetchone()
            if row is None:
                return None
            h, url = row[0], row[1]
            # The WHERE guard is what makes the claim atomic: a second worker
            # racing on the same row updates 0 rows and moves on.
            cur.execute(
                "UPDATE analysis_cache "
                "SET status = 'running', attempts = attempts + 1 "
                "WHERE url_hash = %s AND status = 'pending'",
                (h,),
            )
            claimed = cur.rowcount == 1
        finally:
            cur.close()
        self._commit()
        return url if claimed else None

    def mark_error(self, url, message):
        h = self._hash(url)
        cur = self.conn.cursor()
        try:
            cur.execute(
                "UPDATE analysis_cache SET status = 'error', error = %s "
                "WHERE url_hash = %s",
                (str(message)[:2000], h),
            )
        finally:
            cur.close()
        self._commit()

    # -- introspection ---------------------------------------------------

    def queue_stats(self):
        """{status: count} across the whole table."""
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT status, COUNT(*) FROM analysis_cache GROUP BY status")
            rows = cur.fetchall()
        finally:
            cur.close()
        return {row[0]: row[1] for row in rows}

    def recent(self, limit=50):
        """Most recently touched rows, newest first.

        Deliberately does NOT select `result`: those blobs run to several MB
        each and the status view only needs metadata.
        """
        cur = self.conn.cursor()
        try:
            cur.execute(
                "SELECT page_url, page_title, status, attempts, error, "
                "       source_count, created_at, updated_at "
                "FROM analysis_cache ORDER BY updated_at DESC LIMIT %s",
                (int(limit),),
            )
            rows = cur.fetchall()
        finally:
            cur.close()
        return [
            {
                "page_url": r[0],
                "page_title": r[1],
                "status": r[2],
                "attempts": r[3],
                "error": r[4],
                "source_count": r[5],
                "created_at": r[6].isoformat() if r[6] else None,
                "updated_at": r[7].isoformat() if r[7] else None,
            }
            for r in rows
        ]

    def requeue_stale_running(self, older_than_minutes=30):
        """Recover rows abandoned by a killed worker."""
        cur = self.conn.cursor()
        try:
            cur.execute(
                "UPDATE analysis_cache SET status = 'pending' "
                "WHERE status = 'running' "
                "  AND updated_at < NOW() - INTERVAL %s MINUTE "
                "  AND attempts < %s",
                (older_than_minutes, MAX_ATTEMPTS),
            )
            n = cur.rowcount
        finally:
            cur.close()
        self._commit()
        return n
