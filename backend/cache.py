import hashlib
import json


class Cache:
    """MariaDB-backed cache. Conn is a DB-API 2.0 connection (PyMySQL)."""

    def __init__(self, conn):
        self.conn = conn

    @staticmethod
    def _hash(url):
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def get(self, url):
        h = self._hash(url)
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT result FROM analysis_cache WHERE url_hash = %s", (h,))
            row = cur.fetchone()
        finally:
            cur.close()
        if row is None:
            return None
        return json.loads(row[0])

    def set(self, url, payload):
        h = self._hash(url)
        page_title = payload.get("page_title")
        source_count = payload.get("source_count")
        blob = json.dumps(payload, ensure_ascii=False)
        cur = self.conn.cursor()
        try:
            cur.execute(
                "REPLACE INTO analysis_cache (url_hash, page_url, page_title, result, source_count) "
                "VALUES (%s, %s, %s, %s, %s)",
                (h, url, page_title, blob, source_count),
            )
        finally:
            cur.close()
        self.conn.commit()
