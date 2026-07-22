"""MariaDB-backed CacheStore for the analyzer's lookup caches.

Installed by the web app and the worker at startup. Without it the analyzer
writes its caches into the container filesystem, which is wiped on every
restart and not shared between worker replicas -- so every analysis re-hits
Crossref, MBFC, Wikidata and archive.org from scratch and burns rate-limit
headroom for nothing.

Writes are best-effort by design, matching FileCacheStore: a caching failure
degrades performance, it must never fail an analysis.
"""
import hashlib
import json
import sys
import threading

from wikipedia_sources_bias.cachestore import CacheStore


def _hash(key):
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class MariaDBCacheStore(CacheStore):
    def __init__(self, connect_fn):
        """connect_fn: zero-arg callable returning a fresh DB-API connection."""
        self._connect = connect_fn
        # One connection PER THREAD. Sources are analysed by a thread pool
        # (see WSB_SOURCE_CONCURRENCY) and every one of them reads and writes
        # these caches; a pymysql connection is not thread-safe, and sharing
        # one would interleave protocol traffic and corrupt results.
        self._local = threading.local()

    def _conn_for_thread(self):
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = self._connect()
            self._local.conn = conn
        try:
            # Workers idle for long stretches between queue items, comfortably
            # past MariaDB's idle timeout.
            conn.ping(reconnect=True)
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            conn = self._connect()
            self._local.conn = conn
        return conn

    def _cursor(self):
        return self._conn_for_thread().cursor()

    def load_all(self, namespace):
        try:
            cur = self._cursor()
            try:
                cur.execute(
                    "SELECT cache_key, value FROM kv_cache WHERE namespace = %s",
                    (namespace,),
                )
                rows = cur.fetchall()
            finally:
                cur.close()
        except Exception as e:
            print(f"kv_cache load_all({namespace}) failed: {e}", file=sys.stderr)
            return {}

        out = {}
        for key, value in rows:
            try:
                out[key] = json.loads(value)
            except Exception:
                continue
        return out

    def get(self, namespace, key):
        try:
            cur = self._cursor()
            try:
                cur.execute(
                    "SELECT value FROM kv_cache WHERE namespace = %s AND key_hash = %s",
                    (namespace, _hash(key)),
                )
                row = cur.fetchone()
            finally:
                cur.close()
        except Exception as e:
            print(f"kv_cache get({namespace}) failed: {e}", file=sys.stderr)
            return None
        if row is None:
            return None
        try:
            return json.loads(row[0])
        except Exception:
            return None

    def put(self, namespace, key, value):
        try:
            blob = json.dumps(value, ensure_ascii=False)
        except Exception:
            return
        try:
            conn = self._conn_for_thread()
            cur = conn.cursor()
            try:
                cur.execute(
                    "INSERT INTO kv_cache (namespace, key_hash, cache_key, value) "
                    "VALUES (%s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE value = VALUES(value)",
                    (namespace, _hash(key), key, blob),
                )
            finally:
                cur.close()
            conn.commit()
        except Exception as e:
            print(f"kv_cache put({namespace}) failed: {e}", file=sys.stderr)


def install(connect_fn):
    """Point the analyzer at ToolsDB. Returns the store."""
    from wikipedia_sources_bias.cachestore import set_store

    store = MariaDBCacheStore(connect_fn)
    set_store(store)
    return store
