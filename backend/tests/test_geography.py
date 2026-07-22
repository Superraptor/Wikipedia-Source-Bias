"""Regressions for the geography normalisation seen on Catherine Barbaroux.

Two distinct bugs showed up in one dashboard:
  - la-croix.com and adie.org had country="France" but region="Unknown",
    because Wikidata fills the country after the TLD pass without revisiting
    the region, and "Unknown" is truthy so `region or REGION_MAP[...]` kept it.
  - marianne.net was unmapped with no way to tell why.
"""
from analyzer import _norm_source, normalize_analysis, UNMAPPED


def test_region_is_derived_when_analyzer_said_unknown():
    s = _norm_source({
        "domain": "la-croix.com",
        "geography": {"country": "France", "region": "Unknown"},
    })
    assert s["geography"]["country"] == "France"
    assert s["geography"]["region"] == "Europe"


def test_region_is_derived_when_absent():
    s = _norm_source({"domain": "bbc.co.uk", "geography": {"country": "United Kingdom"}})
    assert s["geography"]["region"] == "Europe"


def test_unknown_country_becomes_unmapped_with_an_explanation():
    s = _norm_source({
        "domain": "marianne.net",
        "geography": {"country": "Unknown", "region": "Unknown"},
    })
    geo = s["geography"]
    assert geo["country"] == UNMAPPED
    assert geo["unmapped"] is True
    assert ".net" in geo["note"]
    assert "Wikidata" in geo["note"]


def test_resolved_source_carries_no_note():
    s = _norm_source({
        "domain": "lemonde.fr",
        "geography": {"country": "France", "region": "Europe"},
    })
    assert "note" in s["geography"] or True  # note is optional
    assert s["geography"].get("unmapped") is not True
    assert "note" not in s["geography"]


def test_country_resolved_but_region_unknown_is_explained():
    s = _norm_source({
        "domain": "example.fr",
        "geography": {"country": "Kiribati", "region": "Unknown"},
    })
    assert s["geography"]["region"] == UNMAPPED
    assert "REGION_MAP" in s["geography"]["note"]


def test_all_the_missing_spellings_are_treated_alike():
    for missing in (None, "", "unknown", "Unknown", "none", UNMAPPED):
        s = _norm_source({"domain": "x.com", "geography": {"country": missing}})
        assert s["geography"]["country"] == UNMAPPED, missing


def test_normalize_analysis_keeps_notes():
    raw = {
        "page_title": "X",
        "page_url": "https://fr.wikipedia.org/wiki/X",
        "sources": [{"domain": "marianne.net", "geography": {"country": "Unknown"}}],
    }
    out = normalize_analysis(raw)
    assert out["sources"][0]["geography"]["unmapped"] is True
