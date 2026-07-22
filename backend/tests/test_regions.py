"""One region vocabulary, derived from the country.

The analyzer had two: the TLD table emits 'North America'/'Middle East', while
the country table emitted 'Americas'. The same country therefore landed in
different buckets of one distribution depending on which lookup resolved it --
and the granular values had no translation, so the UI printed the raw key
'region.North America'.
"""
import json
from pathlib import Path

from analyzer import REGIONS, REGION_MAP, _norm_source, normalise_region, UNMAPPED

LOCALES = Path(__file__).resolve().parents[2] / "frontend" / "i18n" / "locales"


def region_of(country, analyzer_region=None):
    geo = {"country": country}
    if analyzer_region:
        geo["region"] = analyzer_region
    return _norm_source({"domain": "x.com", "geography": geo})["geography"]["region"]


def test_country_decides_the_region_not_the_analyzer_field():
    # The analyzer's coarse 'Americas' must not survive when the country is known.
    assert region_of("United States", "Americas") == "North America"
    assert region_of("Brazil", "Americas") == "South America"


def test_both_resolution_paths_agree():
    """A .us source and a Wikidata-resolved US source share one bucket."""
    assert region_of("United States", "North America") == region_of("United States", "Americas")


def test_analyzer_region_is_used_only_when_the_country_is_unknown():
    assert region_of(None, "Middle East") == "Middle East"
    assert region_of(None, None) == UNMAPPED


def test_every_mapped_region_is_canonical():
    for country, region in REGION_MAP.items():
        assert region in REGIONS, f"{country} -> {region}"


def test_aliases_normalise_onto_the_vocabulary():
    assert normalise_region("Latin America") == "South America"
    assert normalise_region("MENA") == "Middle East"
    assert normalise_region("unknown") is None


def test_every_region_has_a_label_in_both_locales():
    """A missing key renders the literal 'region.North America' on screen."""
    for loc in ("fr", "en"):
        labels = json.loads((LOCALES / f"{loc}.json").read_text(encoding="utf-8"))["region"]
        for region in REGIONS:
            assert region in labels, f"{loc} missing {region}"
        # Legacy payloads still carry the coarse bucket.
        assert "Americas" in labels


def test_region_distribution_is_recomputed_not_inherited():
    """Brexit named Australia and Belgium as countries while reporting their
    region as 'Unknown': the upstream aggregate's region_distribution was stale
    and normalize_analysis trusted it wholesale."""
    from analyzer import normalize_analysis

    raw = {
        "page_title": "X",
        "page_url": "https://en.wikipedia.org/wiki/X",
        "sources": [
            {"domain": "a.au", "geography": {"country": "Australia", "region": "Unknown"}},
            {"domain": "b.be", "geography": {"country": "Belgium", "region": "Unknown"}},
            {"domain": "c.us", "geography": {"country": "United States", "region": "Americas"}},
        ],
        "aggregated_bias": {
            # Deliberately wrong, as the real cached payloads are.
            "geography_distribution": {"Australia": {"count": 1, "percentage": 33.3}},
            "region_distribution": {"Unknown": {"count": 3, "percentage": 100.0}},
        },
    }
    out = normalize_analysis(raw)
    regions = out["aggregated_bias"]["region_distribution"]
    assert "Unknown" not in regions
    assert regions["Oceania"]["count"] == 1
    assert regions["Europe"]["count"] == 1
    assert regions["North America"]["count"] == 1


def test_upstream_geography_distribution_is_still_respected():
    """Only regions are recomputed; the rest of the upstream aggregate stays."""
    from analyzer import normalize_analysis

    raw = {
        "sources": [{"domain": "a.fr", "geography": {"country": "France"}}],
        "aggregated_bias": {
            "geography_distribution": {"France": {"count": 99, "percentage": 100.0}},
            "language_distribution": {"French": {"count": 99, "percentage": 100.0}},
        },
    }
    agg = normalize_analysis(raw)["aggregated_bias"]
    assert agg["geography_distribution"]["France"]["count"] == 99
    assert agg["language_distribution"]["French"]["count"] == 99
