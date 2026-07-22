"""Process-wide, per-host politeness limiting.

The analyzer's original approach was a bare `time.sleep(1.0)` before each MBFC
request. That has two problems once anything runs in parallel:

  - It is per call site, not per host, so nothing coordinates the several
    different functions that all hit Wikidata.
  - It is per process. Two worker replicas already halved the intended rate,
    and a thread pool inside one analysis would divide it further.

This module gives one shared limiter per hostname, so concurrency can be raised
without raising the request rate any individual service sees. It also records
`Retry-After` from a 429 so every caller to that host backs off -- previously
only the Wikidata SPARQL path honoured 429 at all, and every other caller
turned a rate-limit response into a silently empty result.
"""
from __future__ import annotations

import threading
import time
from urllib.parse import urlparse

# Minimum seconds between requests to a given host. Defaults are deliberately
# conservative for the hosts we hammer; everything else gets a light default.
DEFAULT_MIN_INTERVAL = 0.2

MIN_INTERVAL_BY_HOST = {
    "mediabiasfactcheck.com": 1.0,
    "www.mediabiasfactcheck.com": 1.0,
    "query.wikidata.org": 1.0,
    "www.wikidata.org": 0.3,
    "api.crossref.org": 0.2,
    "archive.org": 0.5,
    "web.archive.org": 0.5,
    "www.googleapis.com": 0.3,
}


class _HostLimiter:
    def __init__(self, min_interval):
        self.min_interval = min_interval
        self.lock = threading.Lock()
        self.next_allowed = 0.0

    def acquire(self):
        """Block until this host may be called again."""
        while True:
            with self.lock:
                now = time.monotonic()
                if now >= self.next_allowed:
                    # Reserve this slot before releasing the lock, so two
                    # threads cannot both decide they are allowed to go now.
                    self.next_allowed = now + self.min_interval
                    return
                wait = self.next_allowed - now
            time.sleep(wait)

    def penalise(self, seconds):
        """Push the next allowed time out, e.g. after a 429."""
        with self.lock:
            self.next_allowed = max(self.next_allowed, time.monotonic() + seconds)


_limiters: dict[str, _HostLimiter] = {}
_limiters_lock = threading.Lock()


def _host_of(url):
    try:
        return (urlparse(url).netloc or "").lower()
    except Exception:
        return ""


def limiter_for(url):
    host = _host_of(url)
    with _limiters_lock:
        limiter = _limiters.get(host)
        if limiter is None:
            limiter = _HostLimiter(MIN_INTERVAL_BY_HOST.get(host, DEFAULT_MIN_INTERVAL))
            _limiters[host] = limiter
        return limiter


def wait(url):
    """Block until a request to `url`'s host is permitted."""
    limiter_for(url).acquire()


def note_response(url, response):
    """Record a rate-limit response so every caller to that host backs off."""
    status = getattr(response, "status_code", None)
    if status not in (429, 503):
        return
    retry_after = 0
    try:
        raw = response.headers.get("Retry-After")
        if raw and str(raw).strip().isdigit():
            retry_after = int(raw)
    except Exception:
        retry_after = 0
    limiter_for(url).penalise(retry_after or 5)


def reset():
    """Test helper: forget all limiter state."""
    with _limiters_lock:
        _limiters.clear()
