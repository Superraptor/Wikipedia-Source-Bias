"""Share links must not each get their own analysis."""
from wikipedia_sources_bias.urlnorm import canonical_page_url
from cache import Cache


def test_wprov_share_parameter_is_stripped():
    a = "https://fr.wikipedia.org/wiki/Le_M%C3%A9dia?wprov=sfla1"
    b = "https://fr.wikipedia.org/wiki/Le_M%C3%A9dia"
    assert canonical_page_url(a) == b
    assert Cache._hash(a) == Cache._hash(b)


def test_utm_and_social_trackers_are_stripped():
    for junk in ("utm_source=twitter&utm_medium=social", "fbclid=abc123", "ref=share"):
        got = canonical_page_url(f"https://en.wikipedia.org/wiki/Brexit?{junk}")
        assert got == "https://en.wikipedia.org/wiki/Brexit", junk


def test_fragment_is_dropped():
    assert canonical_page_url(
        "https://en.wikipedia.org/wiki/Brexit#Timeline"
    ) == "https://en.wikipedia.org/wiki/Brexit"


def test_meaningful_parameters_are_preserved():
    """oldid selects a revision: dropping it would collide two real requests."""
    url = "https://en.wikipedia.org/wiki/Brexit?oldid=123456"
    assert canonical_page_url(url) == url
    assert Cache._hash(url) != Cache._hash("https://en.wikipedia.org/wiki/Brexit")


def test_mixed_tracking_and_meaningful_parameters():
    got = canonical_page_url(
        "https://en.wikipedia.org/wiki/Brexit?oldid=99&wprov=sfla1&utm_source=x"
    )
    assert got == "https://en.wikipedia.org/wiki/Brexit?oldid=99"


def test_garbage_is_returned_unchanged():
    assert canonical_page_url("") == ""
    assert canonical_page_url("not a url") == "not a url"
