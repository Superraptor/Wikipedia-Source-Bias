import { isUnmapped } from "../utils/labels.js";

/**
 * Detect strong concentration in a source corpus, and say WHY it is flagged.
 *
 * Design principles, from METHODOLOGY.md:
 *  - Concentration is a DESCRIPTION, not a verdict. A French-topic article that
 *    cites French sources is behaving normally. So the notice states the fact
 *    and its caveat; it never says the article is "biased".
 *  - Dominance is measured among PLACED sources only. A pile of unmapped
 *    sources must not hide a real 90%-one-country concentration, nor be
 *    counted as if it were diversity.
 *  - A large unmapped share is a DIFFERENT kind of warning: not imbalance, but
 *    "we cannot judge balance", which the reader must be told plainly.
 */

// Share of the dominant bucket at which we speak up. Two calm tiers.
const STRONG = 85;
const NOTABLE = 70;
// Above this share of unmapped sources, the balance numbers are unreliable.
const UNRELIABLE_UNMAPPED = 40;
// Below this many placed sources, percentages are noise, not signal.
const MIN_SOURCES = 4;

function dominant(dist, { excludeUnknown = true } = {}) {
  if (!dist) return null;
  const entries = Object.entries(dist).filter(([k, v]) => {
    if (!v || typeof v.count !== "number") return false;
    if (excludeUnknown && (isUnmapped(k) || k.toLowerCase() === "unknown")) return false;
    return true;
  });
  const total = entries.reduce((a, [, v]) => a + v.count, 0);
  if (total <= 0) return null;
  let top = null;
  for (const [k, v] of entries) {
    if (!top || v.count > top.count) top = { key: k, count: v.count };
  }
  if (!top) return null;
  return { key: top.key, count: top.count, total, pct: Math.round((top.count / total) * 100) };
}

function unmappedShare(dist) {
  if (!dist) return 0;
  let unknown = 0;
  let total = 0;
  for (const [k, v] of Object.entries(dist)) {
    if (!v || typeof v.count !== "number") continue;
    total += v.count;
    if (isUnmapped(k) || k.toLowerCase() === "unknown") unknown += v.count;
  }
  return total ? Math.round((unknown / total) * 100) : 0;
}

function severityFor(pct) {
  if (pct >= STRONG) return "strong";
  if (pct >= NOTABLE) return "notable";
  return null;
}

/**
 * @returns {Array<{dimension, severity, key, pct, count, total}>} findings,
 *          most severe first. Empty when the corpus is balanced or too small.
 */
export function detectImbalance(analysis) {
  const agg = analysis?.aggregated_bias || {};
  const sourceCount = analysis?.source_count ?? analysis?.sources?.length ?? 0;
  const findings = [];

  // Reliability caveat comes first: if half the sources are unplaceable, the
  // concentration numbers below are built on the other half.
  const geoUnmapped = unmappedShare(agg.geography_distribution);
  if (geoUnmapped >= UNRELIABLE_UNMAPPED) {
    findings.push({ dimension: "coverage", severity: "coverage", pct: geoUnmapped });
  }

  const dims = [
    ["geography", agg.geography_distribution],
    ["region", agg.region_distribution],
    ["language", agg.language_distribution],
  ];
  for (const [dimension, dist] of dims) {
    const d = dominant(dist);
    if (!d || d.total < MIN_SOURCES) continue;
    const severity = severityFor(d.pct);
    if (!severity) continue;
    findings.push({ dimension, severity, key: d.key, pct: d.pct, count: d.count, total: d.total });
  }

  // Strongest first; a coverage caveat outranks a concentration notice.
  const rank = { coverage: 3, strong: 2, notable: 1 };
  findings.sort((a, b) => (rank[b.severity] || 0) - (rank[a.severity] || 0));
  return { sourceCount, findings };
}
