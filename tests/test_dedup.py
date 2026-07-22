"""German-style 'In: Website https://host/' citations yielded the document AND
the publisher homepage, double-counting that publisher in every distribution."""
from wikipedia_sources_bias.analysis import _drop_bare_homepages, _is_bare_homepage


def test_homepage_dropped_when_a_deep_link_exists():
    urls = [
        "https://www.europarl.europa.eu/RegData/etudes/BRIE/2018/EPRS_BRI.pdf",
        "https://www.europarl.europa.eu/",
    ]
    assert _drop_bare_homepages(urls) == [urls[0]]


def test_homepage_kept_when_it_is_the_only_link_to_that_host():
    urls = ["https://www.example.org/", "https://other.org/deep/page"]
    assert _drop_bare_homepages(urls) == urls


def test_order_is_preserved():
    urls = ["https://a.org/x", "https://b.org/", "https://a.org/", "https://c.org/y"]
    assert _drop_bare_homepages(urls) == [
        "https://a.org/x", "https://b.org/", "https://c.org/y",
    ]


def test_is_bare_homepage():
    assert _is_bare_homepage("https://example.org")
    assert _is_bare_homepage("https://example.org/")
    assert not _is_bare_homepage("https://example.org/page")
    # A query string means it addresses something specific.
    assert not _is_bare_homepage("https://example.org/?id=3")
