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

    def row_for(self, url):
        if url not in self.states:
            return None
        status, err = self.states[url]
        return {
            "page_url": url, "page_title": None, "status": status,
            "attempts": 1, "error": err, "source_count": None,
            "created_at": None, "updated_at": None,
            "age_seconds": 30, "since_update_seconds": 5,
            "stage": "sources", "progress_done": 2, "progress_total": 10,
            "eta_seconds": 120, "running_seconds": 30,
        }

    def queue_position(self, url):
        return 0

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


# -- ETA stability -------------------------------------------------------


def test_coarse_buckets_widen_with_the_estimate():
    from app import _coarse

    assert _coarse(None) is None
    assert _coarse(30) == "moins d'une minute"
    assert _coarse(240) == "~4 min"
    # 10-60 min rounds to 5-minute buckets so it stops twitching each refresh.
    assert _coarse(23 * 60) == "~25 min"
    assert _coarse(90 * 60) == "~1.5 h"
    assert _coarse(5 * 3600) == "~5 h"


def test_eta_uses_the_worker_estimate_not_queue_wait():
    from app import _progress

    row = {
        "progress_done": 10, "progress_total": 100,
        "eta_seconds": 600, "since_update_seconds": 0,
        # A long queue wait must not inflate the estimate.
        "age_seconds": 100000, "running_seconds": 120,
    }
    pct, text, eta = _progress(row)
    assert pct == 10 and text == "10/100"
    assert eta == "~10 min"


def test_eta_counts_down_between_progress_writes():
    from app import _progress

    row = {"progress_done": 5, "progress_total": 10, "eta_seconds": 600,
           "since_update_seconds": 300, "running_seconds": 600}
    assert _progress(row)[2] == "~5 min"


def test_eta_falls_back_to_running_time_not_age():
    from app import _progress

    row = {"progress_done": 5, "progress_total": 10, "eta_seconds": None,
           "since_update_seconds": 0,
           "running_seconds": 300,   # 60s per source -> 5 remaining -> 300s
           "age_seconds": 99999}     # must be ignored
    assert _progress(row)[2] == "~5 min"


def test_no_progress_yields_no_eta():
    from app import _progress

    assert _progress({"progress_done": None, "progress_total": None}) == (None, None, None)


# -- "is it stuck, or just long?" ----------------------------------------


def test_pending_202_carries_progress_so_users_can_tell_it_is_alive():
    """A bare 'pending' gave users no way to distinguish slow from dead."""
    import app as appmod

    fake = FakeCache()
    url = "https://fr.wikipedia.org/wiki/Big"
    fake.states[url] = ("running", None)
    appmod.app.config["TESTING"] = True
    import pytest as _pytest

    mp = _pytest.MonkeyPatch()
    mp.setattr("app.get_cache", lambda: fake)
    mp.setattr("app.SYNC_ANALYSIS", False)
    try:
        with appmod.app.test_client() as c:
            body = c.get(f"/api/analyze?url={url}").get_json()
    finally:
        mp.undo()

    assert body["status"] == "pending"
    assert body["queue_state"] == "running"
    assert body["progress_done"] == 2 and body["progress_total"] == 10
    assert body["progress_pct"] == 20
    assert body["health"] == "working"
    assert body["eta"]


def test_health_flags_a_silent_worker_as_stalled():
    from app import _health, STALL_SECONDS

    assert _health({"status": "running", "since_update_seconds": 10}) == "working"
    assert _health({"status": "running",
                    "since_update_seconds": STALL_SECONDS + 1}) == "stalled"
    # Not running: health is not a meaningful question.
    assert _health({"status": "pending", "since_update_seconds": 9999}) is None
    assert _health({"status": "done", "since_update_seconds": 9999}) is None


def test_status_page_states_are_distinct_in_the_progress_column(app_with_fake_cache):
    """'Avancement' must read differently for done / error / pending / running."""
    client, fake = app_with_fake_cache
    fake.states["https://fr.wikipedia.org/wiki/Done"] = ("done", None)
    fake.states["https://fr.wikipedia.org/wiki/Err"] = ("error", "boom")
    fake.states["https://fr.wikipedia.org/wiki/Wait"] = ("pending", None)
    html = client.get("/status").get_data(as_text=True)
    assert "Analyse terminée" in html
    assert "Échec" in html
    assert "en attente d&#39;un worker" in html or "en attente d'un worker" in html
