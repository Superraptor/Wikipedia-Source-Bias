"""Falsifiable checks on the tool's own output.

These are not unit tests: they run against real stored analyses in production
and are published, so a reader -- including a critic -- can see where the tool
currently fails rather than only what it claims.

The one that matters most is `no_fabricated_analysis`. The tool once replaced
an unreadable article with a synthetic page citing Reuters and analysed that,
producing a complete and confident report out of nothing. Six other articles
reported a known country with an unmapped region for hours. Both were invisible
until someone happened to look.
"""

CANONICAL_REGIONS = {
    "North America", "South America", "Europe", "Asia", "Africa",
    "Oceania", "Middle East", "Global", "Americas", "unmapped",
}

# Counted distributions that must account for every analysed source.
COUNTED_DISTRIBUTIONS = (
    "geography_distribution",
    "region_distribution",
    "reliability_distribution",
    "language_distribution",
)


def _dists(agg, key):
    d = agg.get(key) or {}
    return {k: v for k, v in d.items() if isinstance(v, dict)}


def check_analysis(payload):
    """Run every invariant over one analysis. Returns a list of failures."""
    failures = []
    sources = payload.get("sources") or []
    agg = payload.get("aggregated_bias") or {}
    declared = payload.get("source_count")

    if declared is not None and declared != len(sources):
        failures.append((
            "source_count_matches_sources",
            f"source_count={declared} but {len(sources)} sources present",
        ))

    for key in COUNTED_DISTRIBUTIONS:
        dist = _dists(agg, key)
        if not dist:
            continue
        total = sum(v.get("count", 0) for v in dist.values())
        if total != len(sources):
            failures.append((
                "distribution_totals_match",
                f"{key} counts sum to {total}, expected {len(sources)}",
            ))
        pct = sum(v.get("percentage", 0) for v in dist.values())
        if not (99.0 <= pct <= 101.0):
            failures.append((
                "percentages_sum_to_100", f"{key} percentages sum to {pct}",
            ))

    for key in ("region_distribution",):
        for name in _dists(agg, key):
            if name not in CANONICAL_REGIONS:
                failures.append((
                    "regions_are_canonical", f"{key} contains {name!r}",
                ))

    for s in sources:
        geo = s.get("geography") or {}
        country, region = geo.get("country"), geo.get("region")
        if country not in (None, "", "unmapped") and region == "unmapped":
            failures.append((
                "known_country_has_a_region",
                f"{s.get('domain')}: country {country!r} but region unmapped",
            ))
            break

    if len(sources) == 1 and (sources[0].get("domain") or "").endswith("reuters.com"):
        failures.append((
            "no_fabricated_analysis",
            "single reuters.com source: the old synthetic-fallback fingerprint",
        ))

    if agg.get("subjectivity_sample_count") == 0 and agg.get("average_subjectivity_score"):
        failures.append((
            "no_score_without_a_sample",
            "subjectivity score reported with zero samples",
        ))

    # Provenance: a figure that cannot be traced to an input is not checkable.
    if not payload.get("revision_id"):
        failures.append((
            "input_is_pinned",
            "no revision_id: this analysis cannot be reproduced",
        ))
    if not payload.get("method_version"):
        failures.append((
            "method_is_pinned",
            "no method_version: unknown which code produced this",
        ))

    return failures


INVARIANTS = (
    ("source_count_matches_sources", "The declared source count matches the list."),
    ("distribution_totals_match", "Every distribution accounts for every source."),
    ("percentages_sum_to_100", "Percentages within a distribution sum to 100."),
    ("regions_are_canonical", "Region values come from one fixed vocabulary."),
    ("known_country_has_a_region", "A source with a known country has a region."),
    ("no_fabricated_analysis", "No analysis carries the synthetic-fallback fingerprint."),
    ("no_score_without_a_sample", "No score is reported without an underlying sample."),
    ("input_is_pinned", "Every analysis records the article revision it read."),
    ("method_is_pinned", "Every analysis records the code version that produced it."),
)
