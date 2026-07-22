import hashlib
import json
import zlib

# Payload kinds stored in analysis_result.
JSON = "json"
GEOJSON = "geojson"

# Reports run 3-5MB for large articles and compress roughly tenfold, so this
# is the difference between a few hundred MB of ToolsDB and a few GB against a
# 25GB soft cap.
COMPRESS_LEVEL = 6


def _encode(payload):
    """-> (bytes, compressed?)"""
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return zlib.compress(raw, COMPRESS_LEVEL), True


def _decode(blob, compressed):
    if isinstance(blob, str):
        blob = blob.encode("utf-8")
    if compressed:
        blob = zlib.decompress(blob)
    return json.loads(blob.decode("utf-8"))


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

    def get(self, url, kind=JSON):
        """Completed result for `url`, or None if absent/pending/failed."""
        h = self._hash(url)
        cur = self.conn.cursor()
        try:
            cur.execute(
                "SELECT r.payload, r.compressed FROM analysis_result r "
                "JOIN analysis_cache c ON c.url_hash = r.url_hash "
                "WHERE r.url_hash = %s AND r.kind = %s AND c.status = 'done'",
                (h, kind),
            )
            row = cur.fetchone()
        finally:
            cur.close()
        if row is None or row[0] is None:
            return None
        return _decode(row[0], row[1])

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

    def set(self, url, payload, kind=JSON):
        """Store a completed analysis.

        Metadata and payload go to different tables: the queue and status
        views scan analysis_cache constantly and must not drag megabytes with
        them. INSERT ... ON DUPLICATE KEY UPDATE rather than REPLACE, because
        REPLACE deletes the row and would cascade the other kind's payload
        away via the foreign key.
        """
        h = self._hash(url)
        blob, compressed = _encode(payload)
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO analysis_cache "
                "(url_hash, page_url, page_title, source_count, status) "
                "VALUES (%s, %s, %s, %s, 'done') "
                "ON DUPLICATE KEY UPDATE page_title = VALUES(page_title), "
                "  source_count = VALUES(source_count), status = 'done', error = NULL",
                (h, url, payload.get("page_title"), payload.get("source_count")),
            )
            cur.execute(
                "INSERT INTO analysis_result "
                "(url_hash, kind, payload, compressed, byte_size) "
                "VALUES (%s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE payload = VALUES(payload), "
                "  compressed = VALUES(compressed), byte_size = VALUES(byte_size)",
                (h, kind, blob, 1 if compressed else 0, len(blob)),
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

    def release(self, url):
        """Hand a claimed row back to the queue.

        Used on graceful shutdown so a redeploy does not strand a row in
        'running' until the stale sweep reclaims it. Guarded on the current
        status so it can never resurrect a finished or failed analysis.
        """
        h = self._hash(url)
        cur = self.conn.cursor()
        try:
            cur.execute(
                "UPDATE analysis_cache SET status = 'pending' "
                "WHERE url_hash = %s AND status = 'running'",
                (h,),
            )
            released = cur.rowcount
        finally:
            cur.close()
        self._commit()
        return released

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
            # Ages come from the server clock: pods have their own, and a
            # skewed one would show negative waits.
            cur.execute(
                "SELECT page_url, page_title, status, attempts, error, "
                "       source_count, created_at, updated_at, "
                "       TIMESTAMPDIFF(SECOND, created_at, NOW()) AS age_s, "
                "       TIMESTAMPDIFF(SECOND, updated_at, NOW()) AS since_update_s "
                "FROM analysis_cache "
                "ORDER BY FIELD(status,'running','pending','error','done'), updated_at DESC "
                "LIMIT %s",
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
                # For a running row this is how long it has been analysing;
                # for a pending row, how long it has been waiting.
                "age_seconds": int(r[8]) if r[8] is not None else None,
                "since_update_seconds": int(r[9]) if r[9] is not None else None,
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
