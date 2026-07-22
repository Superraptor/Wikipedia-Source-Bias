import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_analyze_requires_url_param(client):
    resp = client.get("/api/analyze")
    assert resp.status_code == 400
    body = resp.get_json()
    assert "error" in body


def test_robots_txt_is_served(client):
    # Toolforge's shared proxy substitutes a deny-all robots.txt on 404.
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert "Allow: /" in resp.get_data(as_text=True)


class FakeCache:
    def __init__(self):
        self.store = {}
        self.states = {}
        self.set_calls = []
        self.enqueued = []

    def get(self, url):
        return self.store.get(url)

    def set(self, url, payload):
        self.store[url] = payload
        self.states[url] = ("done", None)
        self.set_calls.append((url, payload))

    def status_of(self, url):
        return self.states.get(url, (None, None))

    def enqueue(self, url):
        self.enqueued.append(url)
        self.states[url] = ("pending", None)

    def queue_stats(self):
        counts = {}
        for status, _ in self.states.values():
            counts[status] = counts.get(status, 0) + 1
        return counts

    def recent(self, limit=50):
        return [
            {
                "page_url": url,
                "page_title": None,
                "status": status,
                "attempts": 1,
                "error": err,
                "source_count": None,
                "created_at": None,
                "updated_at": None,
            }
            for url, (status, err) in list(self.states.items())[:limit]
        ]


@pytest.fixture
def app_with_fake_cache(monkeypatch):
    fake = FakeCache()
    monkeypatch.setattr("app.get_cache", lambda: fake)
    monkeypatch.setattr("app.run_analysis", lambda url: {
        "page_title": "X", "page_url": url, "source_count": 1,
        "sources": [], "aggregated_bias": {},
    })
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c, fake


def test_analyze_serves_from_cache_on_hit(app_with_fake_cache):
    client, fake = app_with_fake_cache
    url = "https://fr.wikipedia.org/wiki/X"
    fake.store[url] = {"page_title": "X", "source_count": 42, "sources": [], "aggregated_bias": {}}
    resp = client.get(f"/api/analyze?url={url}")
    assert resp.status_code == 200
    assert resp.get_json()["source_count"] == 42


def test_analyze_runs_and_caches_on_miss_in_sync_mode(app_with_fake_cache, monkeypatch):
    monkeypatch.setattr("app.SYNC_ANALYSIS", True)
    client, fake = app_with_fake_cache
    url = "https://fr.wikipedia.org/wiki/Y"
    resp = client.get(f"/api/analyze?url={url}")
    assert resp.status_code == 200
    assert len(fake.set_calls) == 1
    assert fake.set_calls[0][0] == url


# -- async queue behaviour (how it runs on Toolforge) ---------------------


def test_analyze_enqueues_and_returns_202_on_miss(app_with_fake_cache, monkeypatch):
    monkeypatch.setattr("app.SYNC_ANALYSIS", False)
    client, fake = app_with_fake_cache
    url = "https://fr.wikipedia.org/wiki/Z"
    resp = client.get(f"/api/analyze?url={url}")
    assert resp.status_code == 202
    assert resp.get_json()["status"] == "pending"
    assert fake.enqueued == [url]
    # The request must not have performed the analysis itself.
    assert fake.set_calls == []


def test_analyze_returns_202_while_pending_without_requeueing(
    app_with_fake_cache, monkeypatch
):
    monkeypatch.setattr("app.SYNC_ANALYSIS", False)
    client, fake = app_with_fake_cache
    url = "https://fr.wikipedia.org/wiki/Pending"
    fake.states[url] = ("pending", None)
    resp = client.get(f"/api/analyze?url={url}")
    assert resp.status_code == 202
    assert fake.enqueued == []


def test_analyze_surfaces_worker_error(app_with_fake_cache, monkeypatch):
    monkeypatch.setattr("app.SYNC_ANALYSIS", False)
    client, fake = app_with_fake_cache
    url = "https://fr.wikipedia.org/wiki/Broken"
    fake.states[url] = ("error", "boom")
    resp = client.get(f"/api/analyze?url={url}")
    assert resp.status_code == 500
    assert resp.get_json()["error"] == "boom"


def test_analyze_503_when_cache_unavailable_in_async_mode(monkeypatch):
    monkeypatch.setattr("app.SYNC_ANALYSIS", False)

    def boom():
        raise RuntimeError("no db")

    monkeypatch.setattr("app.get_cache", boom)
    app.config["TESTING"] = True
    with app.test_client() as c:
        resp = c.get("/api/analyze?url=https://fr.wikipedia.org/wiki/A")
    assert resp.status_code == 503


# -- status page ---------------------------------------------------------


def test_api_status_reports_queue_counts(app_with_fake_cache):
    client, fake = app_with_fake_cache
    fake.states["https://fr.wikipedia.org/wiki/A"] = ("pending", None)
    fake.states["https://fr.wikipedia.org/wiki/B"] = ("error", "boom")
    resp = client.get("/api/status")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["counts"]["pending"] == 1
    assert body["counts"]["error"] == 1
    assert len(body["recent"]) == 2


def test_status_page_renders_rows_and_errors(app_with_fake_cache):
    client, fake = app_with_fake_cache
    fake.states["https://fr.wikipedia.org/wiki/Catherine_Barbaroux"] = ("running", None)
    fake.states["https://fr.wikipedia.org/wiki/Broken"] = ("error", "scrape exploded")
    resp = client.get("/status")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Catherine_Barbaroux" in html
    assert "scrape exploded" in html
    assert "s-running" in html and "s-error" in html


def test_status_page_survives_a_dead_database(monkeypatch):
    """The status page is what you open when things are broken."""

    def boom():
        raise RuntimeError("db is down")

    monkeypatch.setattr("app.get_cache", boom)
    app.config["TESTING"] = True
    with app.test_client() as c:
        resp = c.get("/status")
    assert resp.status_code == 200
    assert "db is down" in resp.get_data(as_text=True)


def test_api_status_503_when_cache_unavailable(monkeypatch):
    def boom():
        raise RuntimeError("db is down")

    monkeypatch.setattr("app.get_cache", boom)
    app.config["TESTING"] = True
    with app.test_client() as c:
        resp = c.get("/api/status")
    assert resp.status_code == 503


def test_unknown_api_path_is_404_not_spa(client):
    resp = client.get("/api/nope")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Not found"
