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


# -- duration reporting on the status view -------------------------------


def test_humanize_durations():
    from app import _humanize

    assert _humanize(None) is None
    assert _humanize(0) == "0 s"
    assert _humanize(45) == "45 s"
    assert _humanize(192) == "3 min 12 s"
    assert _humanize(3725) == "1 h 02 min"
    # A skewed clock must not produce a negative wait.
    assert _humanize(-5) == "0 s"


def test_decorate_picks_the_right_clock_per_status():
    from app import _decorate

    running = _decorate({"status": "running", "page_url": "https://x/wiki/A",
                         "page_title": None, "age_seconds": 900,
                         "since_update_seconds": 120})
    # Running: time since a worker claimed it, not since it was queued.
    assert running["duration"] == "2 min 00 s"
    assert running["duration_label"] == "en cours depuis"

    pending = _decorate({"status": "pending", "page_url": "https://x/wiki/B",
                         "page_title": None, "age_seconds": 300,
                         "since_update_seconds": 300})
    assert pending["duration"] == "5 min 00 s"
    assert pending["duration_label"] == "en attente depuis"


def test_display_title_falls_back_to_the_url_slug():
    from app import _display_title

    assert _display_title({"page_title": "Real Title"}) == "Real Title"
    row = {"page_title": None,
           "page_url": "https://fr.wikipedia.org/wiki/Catherine_Barbaroux"}
    assert _display_title(row) == "Catherine Barbaroux"
    # Percent-encoded titles must decode, not leak %27 into the UI.
    row = {"page_title": None,
           "page_url": "https://fr.wikipedia.org/wiki/Guerre_d%27Alg%C3%A9rie"}
    assert _display_title(row) == "Guerre d'Algérie"


def test_status_rows_link_to_the_tool_not_wikipedia():
    from app import _analysis_url

    row = {"page_url": "https://fr.wikipedia.org/wiki/Catherine_Barbaroux"}
    link = _analysis_url(row)
    assert link.startswith("/article/Catherine_Barbaroux?src=")
    # The source URL must be encoded, or the query string breaks on the ? and &.
    assert "https%3A%2F%2Ffr.wikipedia.org" in link


def test_analysis_url_is_none_without_a_slug():
    from app import _analysis_url

    assert _analysis_url({"page_url": ""}) is None
