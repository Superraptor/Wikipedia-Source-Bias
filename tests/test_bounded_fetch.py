"""Source fetches must be bounded in size, time and content type.

requests' `timeout` only limits the gap between socket reads, so a large file
that trickles in never times out. An analysis hung indefinitely on a Cambridge
University Press PDF, was requeued every 10 minutes by the stale sweep, and
hung on the same PDF again -- forever.
"""
import time

from wikipedia_sources_bias import analysis
from wikipedia_sources_bias.analysis import (
    MAX_SOURCE_BYTES, _fetch_text_bounded,
)


class FakeResponse:
    def __init__(self, headers=None, chunks=(), status=200):
        self.headers = headers or {"Content-Type": "text/html"}
        self.status_code = status
        self.encoding = "utf-8"
        self._chunks = chunks

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError("should not be reached in these tests")

    def iter_content(self, chunk_size=None):
        yield from self._chunks

    def close(self):
        pass


def _patch(monkeypatch, response):
    monkeypatch.setattr(analysis, "_polite_get", lambda url, **kw: response)


def test_a_pdf_is_not_downloaded_at_all(monkeypatch):
    _patch(monkeypatch, FakeResponse(
        headers={"Content-Type": "application/pdf"},
        chunks=[b"%PDF-1.7" + b"x" * 10_000_000],
    ))
    assert _fetch_text_bounded("https://example.org/paper.pdf") == ""


def test_a_declared_oversize_document_is_skipped(monkeypatch):
    _patch(monkeypatch, FakeResponse(
        headers={"Content-Type": "text/html",
                 "Content-Length": str(MAX_SOURCE_BYTES * 4)},
        chunks=[b"<html>"],
    ))
    assert _fetch_text_bounded("https://example.org/huge.html") == ""


def test_an_undeclared_oversize_document_is_truncated(monkeypatch):
    _patch(monkeypatch, FakeResponse(chunks=[b"a" * 16384] * 400))
    got = _fetch_text_bounded("https://example.org/stream")
    assert len(got) <= MAX_SOURCE_BYTES + 16384


def test_a_slow_trickle_stops_at_the_deadline(monkeypatch):
    def slow():
        for _ in range(100):
            time.sleep(0.03)
            yield b"a" * 8

    monkeypatch.setattr(analysis, "MAX_SOURCE_SECONDS", 0.2)
    _patch(monkeypatch, FakeResponse(chunks=slow()))
    started = time.monotonic()
    _fetch_text_bounded("https://example.org/slow")
    # Without the deadline this would run for ~3s; the cap is 0.2s.
    assert time.monotonic() - started < 1.5


def test_html_still_comes_through(monkeypatch):
    _patch(monkeypatch, FakeResponse(chunks=[b"<html><body>hi</body></html>"]))
    assert "hi" in _fetch_text_bounded("https://example.org/page")
