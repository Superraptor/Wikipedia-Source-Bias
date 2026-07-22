"""A page we could not read must never be turned into an analysis.

analyze_page used to substitute a hand-written HTML page containing a Reuters
link whenever the article fetch raised, and to invent a Reuters "source" when
an article yielded none. Both fabricated findings out of nothing.
"""
import pytest
import requests

from wikipedia_sources_bias import analysis
from wikipedia_sources_bias.analysis import ArticleNotFound


class _Resp:
    def __init__(self, status):
        self.status_code = status
        self.text = ""
        self.headers = {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_404_raises_article_not_found(monkeypatch):
    monkeypatch.setattr(analysis, "_polite_get", lambda url, **kw: _Resp(404))
    with pytest.raises(ArticleNotFound):
        analysis.analyze_page("https://fr.wikipedia.org/wiki/Nope", no_cache=True)


def test_network_failure_raises_rather_than_inventing_a_page(monkeypatch):
    def boom(url, **kw):
        raise requests.ConnectionError("dns")

    monkeypatch.setattr(analysis, "_polite_get", boom)
    with pytest.raises(ArticleNotFound):
        analysis.analyze_page("https://fr.wikipedia.org/wiki/Nope", no_cache=True)


def test_the_reuters_fabrication_is_gone():
    """Guards the exact shape of the old bug: a synthesised fallback source."""
    src = (analysis.analyze_page.__doc__ or "") + open(analysis.__file__, encoding="utf-8").read()
    assert "fallback_source" not in src
    assert "Fallback page" not in src
