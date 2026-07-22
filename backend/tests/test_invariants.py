"""The published checks must actually catch the failures they claim to."""
from invariants import check_analysis, INVARIANTS

GOOD = {
    "source_count": 2,
    "revision_id": 1234,
    "method_version": "abc123",
    "sources": [
        {"domain": "a.fr", "geography": {"country": "France", "region": "Europe"}},
        {"domain": "b.us", "geography": {"country": "United States", "region": "North America"}},
    ],
    "aggregated_bias": {
        "geography_distribution": {"France": {"count": 1, "percentage": 50.0},
                                   "United States": {"count": 1, "percentage": 50.0}},
        "region_distribution": {"Europe": {"count": 1, "percentage": 50.0},
                                "North America": {"count": 1, "percentage": 50.0}},
    },
}


def names(failures):
    return {n for n, _ in failures}


def test_a_sound_analysis_passes_everything():
    assert check_analysis(GOOD) == []


def test_it_catches_a_count_mismatch():
    bad = {**GOOD, "source_count": 5}
    assert "source_count_matches_sources" in names(check_analysis(bad))


def test_it_catches_a_distribution_that_loses_sources():
    bad = {**GOOD, "aggregated_bias": {
        **GOOD["aggregated_bias"],
        "region_distribution": {"Europe": {"count": 1, "percentage": 100.0}}}}
    assert "distribution_totals_match" in names(check_analysis(bad))


def test_it_catches_a_non_canonical_region():
    bad = {**GOOD, "aggregated_bias": {
        **GOOD["aggregated_bias"],
        "region_distribution": {"Middle Earth": {"count": 2, "percentage": 100.0}}}}
    assert "regions_are_canonical" in names(check_analysis(bad))


def test_it_catches_a_known_country_without_a_region():
    bad = {**GOOD, "sources": [
        {"domain": "x.fr", "geography": {"country": "France", "region": "unmapped"}},
        GOOD["sources"][1]]}
    assert "known_country_has_a_region" in names(check_analysis(bad))


def test_it_catches_the_fabrication_fingerprint():
    bad = {"source_count": 1, "revision_id": 1, "method_version": "a",
           "sources": [{"domain": "reuters.com", "geography": {}}],
           "aggregated_bias": {}}
    assert "no_fabricated_analysis" in names(check_analysis(bad))


def test_it_catches_an_unreproducible_analysis():
    bad = {k: v for k, v in GOOD.items() if k not in ("revision_id", "method_version")}
    failed = names(check_analysis(bad))
    assert {"input_is_pinned", "method_is_pinned"} <= failed


def test_every_declared_invariant_is_reachable():
    """A published check that no code can ever emit would be decoration."""
    declared = {n for n, _ in INVARIANTS}
    emitted = set()
    for payload in (
        {**GOOD, "source_count": 5},
        {**GOOD, "aggregated_bias": {"region_distribution": {"Nowhere": {"count": 9, "percentage": 5.0}}}},
        {**GOOD, "sources": [{"domain": "x.fr", "geography": {"country": "France", "region": "unmapped"}}]},
        {"source_count": 1, "sources": [{"domain": "reuters.com", "geography": {}}], "aggregated_bias": {}},
        {**GOOD, "aggregated_bias": {"subjectivity_sample_count": 0, "average_subjectivity_score": 0.4}},
    ):
        emitted |= names(check_analysis(payload))
    assert declared <= emitted, f"never emitted: {declared - emitted}"
