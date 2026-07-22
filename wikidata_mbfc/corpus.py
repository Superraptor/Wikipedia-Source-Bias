"""Rank source domains by how often Wikipedia actually cites them.

The rate limit on MBFC is the binding constraint, so the tool must spend its
requests on the domains that carry the most citations. "Main sources" is
defined here as citation frequency across the analysed corpus, not as an
editorial list of important outlets -- the corpus decides.
"""
from __future__ import annotations

import glob
import json
import os
from collections import Counter

from .domains import host_of, is_infrastructure, strip_www

# Analysis outputs that carry a `sources` list. Globs are resolved relative to
# the repository root so the tool works from any working directory.
DEFAULT_CORPUS_GLOBS = (
    "macron_output_all.json",
    "macron_output.json",
    "french_articles_results/*_analysis.json",
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _iter_analysis_files(patterns, root):
    for pattern in patterns:
        for path in sorted(glob.glob(os.path.join(root, pattern))):
            yield path


def count_domains(patterns=DEFAULT_CORPUS_GLOBS, root=REPO_ROOT):
    """Return (Counter of domain -> citations, number of articles parsed).

    Files that do not parse, or that carry no `sources` list, are skipped
    rather than raising: the corpus is a directory of historical outputs and
    an unreadable one should not stop the ranking.
    """
    counts = Counter()
    articles = 0
    for path in _iter_analysis_files(patterns, root):
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict) or not isinstance(data.get("sources"), list):
            continue
        articles += 1
        for source in data["sources"]:
            if not isinstance(source, dict):
                continue
            domain = strip_www(host_of(source.get("domain") or ""))
            if domain:
                counts[domain] += 1
    return counts, articles


def rank_candidates(limit=None, patterns=DEFAULT_CORPUS_GLOBS, root=REPO_ROOT):
    """Domains ordered by citation count, with infrastructure removed.

    Returns a list of dicts so later stages can attach resolution results
    without losing the citation count that justified the lookup.
    """
    counts, articles = count_domains(patterns, root)
    ranked = []
    for domain, n in counts.most_common():
        if is_infrastructure(domain):
            continue
        ranked.append({"domain": domain, "citations": n})
        if limit is not None and len(ranked) >= limit:
            break
    return ranked, articles


def load_publisher_cache(root=REPO_ROOT):
    """The existing domain -> Wikidata publisher cache, if present.

    Used only as a *hint* for which QID to check. Every QID is re-verified
    against the live Wikidata API before anything is proposed, because this
    cache is known to map some domains to the website item rather than the
    outlet item.
    """
    path = os.path.join(root, "wikidata_publisher_cache.json")
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}
