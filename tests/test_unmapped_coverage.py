"""Coverage for domains measured as unmapped across the live corpus.

28.9% of analysed sources had no country. The causes were concrete: missing
supranational/multi-part TLDs, and registries and academic hosts absent from
the curated database (the subdomain-stripping lookup already existed, it just
had nothing to find).
"""
import pytest

from wikipedia_sources_bias.analysis import analyze_source_bias

# domain -> expected country. Every one of these was unmapped in production.
PREVIOUSLY_UNMAPPED = [
    ("https://meta.wikimedia.org/wiki/X", "United States"),
    ("https://ganglia.wikimedia.org/x", "United States"),
    ("https://portal.issn.org/resource/ISSN/1234-5678", "France"),
    ("https://www.cairn.info/revue-x.htm", "France"),
    ("https://functionallinguistics.springeropen.com/articles/1", "Germany"),
    ("https://www.politico.eu/article/x/", "European Union"),
    ("https://data.worldbank.org/indicator/X", "United States"),
    ("https://hdr.undp.org/reports", "United States"),
]


@pytest.mark.parametrize("url,expected", PREVIOUSLY_UNMAPPED)
def test_previously_unmapped_domains_now_resolve(url, expected):
    got = analyze_source_bias(url)["geography"]["country"]
    assert got == expected, f"{url} -> {got}"


@pytest.mark.parametrize("url,expected", [
    ("https://www.abc.net.au/news/x", "Australia"),
    ("https://www.stuff.co.nz/x", "New Zealand"),
    ("https://www.asahi.co.jp/x", "Japan"),
    ("https://g1.globo.com.br/x", "Brazil"),
    ("https://www.bbc.co.uk/news/x", "United Kingdom"),
    ("https://www.ox.ac.uk/x", "United Kingdom"),
])
def test_multi_part_tlds_carry_a_country(url, expected):
    assert analyze_source_bias(url)["geography"]["country"] == expected


def test_subdomains_fall_back_to_the_registrable_domain():
    """The lookup walks up the labels, so a subdomain inherits its parent."""
    deep = analyze_source_bias("https://a.b.c.wikimedia.org/x")["geography"]
    assert deep["country"] == "United States"
