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


class FakeCache:
    def __init__(self):
        self.store = {}
        self.set_calls = []

    def get(self, url):
        return self.store.get(url)

    def set(self, url, payload):
        self.store[url] = payload
        self.set_calls.append((url, payload))


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


def test_analyze_runs_and_caches_on_miss(app_with_fake_cache):
    client, fake = app_with_fake_cache
    url = "https://fr.wikipedia.org/wiki/Y"
    resp = client.get(f"/api/analyze?url={url}")
    assert resp.status_code == 200
    assert len(fake.set_calls) == 1
    assert fake.set_calls[0][0] == url
