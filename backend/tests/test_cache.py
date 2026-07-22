import hashlib
import json
import zlib

from cache import Cache, _encode, _decode, JSON, GEOJSON


class FakeConn:
    """Records statements and serves a tiny two-table model."""

    def __init__(self):
        self.meta = {}     # url_hash -> dict
        self.results = {}  # (url_hash, kind) -> (payload, compressed)
        self.statements = []

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        pass


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self._row = None

    def execute(self, sql, args=()):
        self.conn.statements.append(sql)
        s = " ".join(sql.split())

        if s.startswith("SELECT r.payload"):
            h, kind = args[0], args[1]
            meta = self.conn.meta.get(h)
            got = self.conn.results.get((h, kind))
            self._row = got if (got and meta and meta.get("status") == "done") else None
        elif s.startswith("INSERT INTO analysis_cache"):
            h, url, title, count = args[0], args[1], args[2], args[3]
            row = self.conn.meta.setdefault(h, {"attempts": 0, "page_url": url})
            row.update(page_title=title, source_count=count, status="done", error=None)
        elif s.startswith("INSERT INTO analysis_result"):
            h, kind, payload, compressed = args[0], args[1], args[2], args[3]
            self.conn.results[(h, kind)] = (payload, compressed)
        else:
            self._row = None

    def fetchone(self):
        return self._row

    def close(self):
        pass


def make_cache():
    return Cache(FakeConn())


def url_hash(url):
    return hashlib.sha256(url.encode()).hexdigest()


# -- payload encoding ----------------------------------------------------


def test_encode_decode_round_trip_preserves_unicode():
    payload = {"page_title": "Ítest ünicode — é", "sources": [{"n": 1}]}
    blob, compressed = _encode(payload)
    assert compressed is True
    assert isinstance(blob, bytes)
    assert _decode(blob, compressed) == payload


def test_large_payloads_compress_substantially():
    # Real reports are highly repetitive JSON; this is what keeps ToolsDB
    # usage well under the 25GB soft cap.
    payload = {"sources": [{"url": f"https://example.org/{i}", "country": "France",
                            "reliability": "high"} for i in range(2000)]}
    raw = len(json.dumps(payload).encode())
    blob, _ = _encode(payload)
    assert len(blob) < raw / 5, f"{len(blob)} vs {raw}"


def test_decode_handles_uncompressed_rows():
    payload = {"a": 1}
    raw = json.dumps(payload).encode()
    assert _decode(raw, False) == payload
    assert _decode(zlib.compress(raw), True) == payload


# -- cache behaviour -----------------------------------------------------


def test_cache_miss_returns_none():
    cache = make_cache()
    assert cache.get("https://fr.wikipedia.org/wiki/X") is None


def test_cache_set_then_get_roundtrip():
    cache = make_cache()
    url = "https://fr.wikipedia.org/wiki/Emmanuel_Macron"
    payload = {"page_title": "Emmanuel_Macron", "source_count": 881}
    cache.set(url, payload)
    assert cache.get(url) == payload


def test_set_writes_metadata_and_payload_to_separate_tables():
    cache = make_cache()
    url = "https://fr.wikipedia.org/wiki/X"
    cache.set(url, {"page_title": "X", "source_count": 3})
    conn = cache.conn
    assert url_hash(url) in conn.meta
    assert (url_hash(url), JSON) in conn.results
    # The queue table must never carry the payload.
    assert all("payload" not in s for s in conn.statements if "analysis_cache" in s)


def test_geojson_and_json_coexist_for_one_article():
    cache = make_cache()
    url = "https://fr.wikipedia.org/wiki/X"
    cache.set(url, {"page_title": "X", "kind": "report"}, kind=JSON)
    cache.set(url, {"type": "FeatureCollection", "features": []}, kind=GEOJSON)
    assert cache.get(url, kind=JSON)["kind"] == "report"
    assert cache.get(url, kind=GEOJSON)["type"] == "FeatureCollection"


def test_set_does_not_use_replace_into():
    """REPLACE would delete the row and cascade the other kind's payload away."""
    cache = make_cache()
    cache.set("https://fr.wikipedia.org/wiki/X", {"page_title": "X"})
    assert not any(s.strip().upper().startswith("REPLACE") for s in cache.conn.statements)


def test_release_only_affects_running_rows():
    """Must never resurrect a finished or failed analysis."""
    seen = {}

    class Conn:
        def cursor(self):
            return Cur()

        def commit(self):
            pass

    class Cur:
        def execute(self, sql, args=()):
            seen["sql"] = " ".join(sql.split())
            seen["args"] = args
            self.rowcount = 1

        def close(self):
            pass

    Cache(Conn()).release("https://fr.wikipedia.org/wiki/X")
    assert "SET status = 'pending'" in seen["sql"]
    assert "status = 'running'" in seen["sql"]


def test_stale_rows_past_max_attempts_are_failed_not_left_running():
    """They used to sit in 'running' forever: no worker, no error, eternal spinner."""
    seen = []

    class Conn:
        def cursor(self):
            return Cur()

        def commit(self):
            pass

    class Cur:
        def execute(self, sql, args=()):
            seen.append((" ".join(sql.split()), args))
            self.rowcount = 1

        def close(self):
            pass

    requeued, failed = Cache(Conn()).requeue_stale_running(10)
    assert requeued == 1 and failed == 1
    requeue_sql, fail_sql = seen[0][0], seen[1][0]
    assert "SET status = 'pending'" in requeue_sql and "attempts < " in requeue_sql
    assert "SET status = 'error'" in fail_sql and "attempts >= " in fail_sql


def test_release_gives_back_the_attempt():
    """A redeploy interrupting work is not the analysis failing."""
    seen = {}

    class Conn:
        def cursor(self):
            return Cur()

        def commit(self):
            pass

    class Cur:
        def execute(self, sql, args=()):
            seen["sql"] = " ".join(sql.split())
            self.rowcount = 1

        def close(self):
            pass

    Cache(Conn()).release("https://fr.wikipedia.org/wiki/X")
    assert "attempts = GREATEST(0, attempts - 1)" in seen["sql"]
