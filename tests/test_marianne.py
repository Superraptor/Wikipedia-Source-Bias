"""marianne.net was unmapped: .net gives no country signal and the domain had
no Wikidata publisher match, so a plainly French outlet had no origin."""
from wikipedia_sources_bias.heuristics_data import DOMAIN_BIAS_DATABASE


def test_marianne_resolves_to_france():
    entry = DOMAIN_BIAS_DATABASE["marianne.net"]
    assert entry["country"] == "France"
    assert entry["region"] == "Europe"
    assert entry["default_language"] == "French"


def test_curated_entries_do_not_assert_a_political_leaning_without_a_source():
    """Country and language are facts; a bias rating is an editorial judgement
    and should come from Wikidata or MBFC, not from this table."""
    for domain in ("marianne.net", "mediapart.fr"):
        assert DOMAIN_BIAS_DATABASE[domain]["political_leaning"] == "unknown"
