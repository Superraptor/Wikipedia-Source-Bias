import pytest
from analyzer import normalize_analysis


def test_normalize_produces_required_top_keys():
    raw = {
        "page_title": "Emmanuel_Macron",
        "page_url": "https://fr.wikipedia.org/wiki/Emmanuel_Macron",
        "source_count": 881,
        "sources": [],
        "aggregated_bias": {},
    }
    out = normalize_analysis(raw)
    assert set(["page_title", "page_url", "source_count", "sources", "aggregated_bias"]).issubset(out.keys())


def test_normalize_source_has_geography_and_reliability():
    raw = {
        "sources": [
            {
                "url": "https://lemonde.fr",
                "domain": "lemonde.fr",
                "reliability": "medium",
                "country": "France",
                "political_leaning": "unknown",
            }
        ],
    }
    out = normalize_analysis(raw)
    src = out["sources"][0]
    assert src["geography"]["country"] == "France"
    assert "reliability" in src


def test_normalize_unknown_country_becomes_non_mapped():
    raw = {"sources": [{"url": "x", "domain": "x", "reliability": "unknown", "country": None}]}
    out = normalize_analysis(raw)
    assert out["sources"][0]["geography"]["country"] == "Non-mappé"


def test_normalize_aggregated_bias_has_geography_distribution():
    raw = {
        "sources": [
            {"domain": "a", "country": "France", "reliability": "medium"},
            {"domain": "b", "country": "France", "reliability": "high"},
            {"domain": "c", "country": "United States", "reliability": "low"},
        ],
        "aggregated_bias": {},
    }
    out = normalize_analysis(raw)
    geo = out["aggregated_bias"]["geography_distribution"]
    assert geo["France"]["count"] == 2
    assert abs(geo["France"]["percentage"] - 66.67) < 0.1
