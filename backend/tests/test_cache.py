import hashlib
from cache import Cache


class FakeConn:
    def __init__(self):
        self.rows = {}

    def cursor(self):
        return FakeCursor(self.rows)

    def commit(self):
        pass


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, sql, args=()):
        if sql.startswith("SELECT"):
            row = self.rows.get(args[0])
            self._last = (row[3],) if row else None
        elif sql.startswith("INSERT") or sql.startswith("REPLACE"):
            self.rows[args[0]] = args

    def fetchone(self):
        return self._last

    def close(self):
        pass


def make_cache():
    return Cache(FakeConn())


def url_hash(url):
    return hashlib.sha256(url.encode()).hexdigest()


def test_cache_miss_returns_none():
    cache = make_cache()
    assert cache.get("https://fr.wikipedia.org/wiki/X") is None


def test_cache_set_then_get_roundtrip():
    cache = make_cache()
    url = "https://fr.wikipedia.org/wiki/Emmanuel_Macron"
    payload = {"page_title": "Emmanuel_Macron", "source_count": 881}
    cache.set(url, payload)
    got = cache.get(url)
    assert got == payload
