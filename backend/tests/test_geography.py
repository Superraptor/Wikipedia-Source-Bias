"""Regressions for the geography normalisation seen on Catherine Barbaroux.

Two distinct bugs showed up in one dashboard:
  - la-croix.com and adie.org had country="France" but region="Unknown",
    because Wikidata fills the country after the TLD pass without revisiting
    the region, and "Unknown" is truthy so `region or REGION_MAP[...]` kept it.
  - marianne.net was unmapped with no way to tell why.

The unmapped marker and the note are language-neutral *keys* rather than
French sentences: the same JSON feeds a French and an English dashboard, and
"Non-mappé" used to leak into the English one.
"""
from analyzer import (
    NOTE_GENERIC_TLD,
    NOTE_NO_COUNTRY_SIGNAL,
    NOTE_REGION_MISSING,
    UNMAPPED,
    _norm_source,
    normalize_analysis,
)


def test_unmapped_marker_is_language_neutral():
    # Guards the contract with the frontend: it looks up the translation for
    # this exact key. A display string here would ship French to English users.
    assert UNMAPPED == "unmapped"


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
    assert geo["note"] == {"code": NOTE_GENERIC_TLD, "params": {"tld": ".net"}}


def test_unmapped_domain_without_a_generic_tld_reports_no_signal():
    s = _norm_source({
        "domain": "example.museum",
        "geography": {"country": "Unknown", "region": "Unknown"},
    })
    assert s["geography"]["note"] == {"code": NOTE_NO_COUNTRY_SIGNAL, "params": {}}


def test_resolved_source_carries_no_note():
    s = _norm_source({
        "domain": "lemonde.fr",
        "geography": {"country": "France", "region": "Europe"},
    })
    assert s["geography"].get("unmapped") is not True
    assert "note" not in s["geography"]


def test_country_resolved_but_region_unknown_is_explained():
    s = _norm_source({
        "domain": "example.fr",
        "geography": {"country": "Kiribati", "region": "Unknown"},
    })
    assert s["geography"]["region"] == UNMAPPED
    assert s["geography"]["note"] == {
        "code": NOTE_REGION_MISSING,
        "params": {"country": "Kiribati"},
    }
    # A region-only failure is not an unmapped source: the country is known.
    assert s["geography"]["unmapped"] is False


def test_note_carries_no_prose():
    """The note must stay machine-readable; wording belongs to the frontend."""
    s = _norm_source({"domain": "marianne.net", "geography": {"country": "Unknown"}})
    note = s["geography"]["note"]
    assert set(note) == {"code", "params"}
    assert " " not in note["code"]


def test_all_the_missing_spellings_are_treated_alike():
    # "Non-mappé" is the pre-i18n display string; cached payloads still carry it.
    for missing in (None, "", "unknown", "Unknown", "none", UNMAPPED, "Non-mappé"):
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
    assert out["sources"][0]["geography"]["note"]["code"] == NOTE_GENERIC_TLD
