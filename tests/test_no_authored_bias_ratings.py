"""The tool must not be an unsourced rater of media bias.

The curated database used to assert a political leaning for 70 of 76 domains
-- "center-left", "far-right", "state-affiliated" -- with no source, no date
and no author. A tool that audits Wikipedia's sourcing cannot itself publish
unattributed editorial judgements about real news organisations.
"""
from wikipedia_sources_bias.heuristics_data import DOMAIN_BIAS_DATABASE
from wikipedia_sources_bias.analysis import analyze_source_bias


def test_the_curated_table_asserts_no_political_leaning():
    offenders = {k: v["political_leaning"]
                 for k, v in DOMAIN_BIAS_DATABASE.items() if "political_leaning" in v}
    assert not offenders, f"unsourced leanings reintroduced: {offenders}"


def test_the_table_still_carries_facts():
    """Country, language and type are facts and must survive the removal."""
    entry = DOMAIN_BIAS_DATABASE["lemonde.fr"]
    assert entry["country"] == "France"
    assert entry["default_language"] == "French"
    assert entry["type"] == "newspaper"


def test_a_curated_domain_starts_with_an_unknown_leaning():
    profile = analyze_source_bias("https://www.lemonde.fr/article")
    assert profile["political_leaning"] == "unknown"
    # And nothing claims to be the source of it.
    assert profile["political_leaning_source"] is None


def test_every_profile_exposes_an_attribution_field():
    """A leaning without a stated source cannot be told from an attributed one."""
    profile = analyze_source_bias("https://example.org/page")
    assert "political_leaning_source" in profile
