"""marianne.net was unmapped: .net gives no country signal and the domain had
no Wikidata publisher match, so a plainly French outlet had no origin."""
from wikipedia_sources_bias.heuristics_data import DOMAIN_BIAS_DATABASE


def test_marianne_resolves_to_france():
    entry = DOMAIN_BIAS_DATABASE["marianne.net"]
    assert entry["country"] == "France"
    assert entry["region"] == "Europe"
    assert entry["default_language"] == "French"


def test_curated_entries_carry_no_political_leaning_at_all():
    """Country and language are facts; a bias rating is an editorial judgement
    and comes from Wikidata or MBFC, never from this table. The field is absent
    rather than "unknown", so it cannot be quietly filled in later."""
    for domain in ("marianne.net", "mediapart.fr"):
        assert "political_leaning" not in DOMAIN_BIAS_DATABASE[domain]
