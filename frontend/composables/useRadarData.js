import { isUnmapped, RADAR_AXES } from "../utils/labels.js";

const RELIABILITY_WEIGHTS = {
  academic: 100,
  high: 80,
  medium: 50,
  low: 20,
  unknown: 0,
};

function geoDiversity(geoDist) {
  if (!geoDist || !Object.keys(geoDist).length) return null;
  let maxPct = 0;
  for (const k of Object.keys(geoDist)) {
    if (isUnmapped(k)) continue;
    maxPct = Math.max(maxPct, geoDist[k].percentage || 0);
  }
  return Math.round((100 - maxPct) * 10) / 10;
}

function politicalPluralism(leanDist) {
  if (!leanDist || !Object.keys(leanDist).length) return null;
  const entries = Object.entries(leanDist).filter(([k]) => k.toLowerCase() !== "unknown");
  const counts = entries.map(([, v]) => v.count || 0).filter((c) => c > 0);
  if (!counts.length) return 0;
  const total = counts.reduce((a, b) => a + b, 0);
  const entropy = counts.reduce((acc, c) => {
    const p = c / total;
    return acc - p * Math.log2(p);
  }, 0);
  const n = counts.length;
  const maxEntropy = n > 1 ? Math.log2(n) : 1;
  return Math.round((entropy / maxEntropy) * 1000) / 10;
}

function authorParity(genderDist) {
  if (!genderDist || !Object.keys(genderDist).length) return null;
  const male = genderDist.male?.percentage ?? 0;
  const female = genderDist.female?.percentage ?? 0;
  return Math.round(Math.min(male, female) * 2 * 10) / 10;
}

// Unlike the other axes, a missing subjectivity score is indistinguishable
// from a genuine 0 -- and `1 - 0` is a perfect 100. An article with no
// references therefore scored full marks for neutrality. `hasData` makes the
// "nothing measured" case explicit.
function neutrality(agg, hasData) {
  if (!hasData) return null;
  // An absent score is NOT a zero. `1 - undefined` coerced to a perfect 100,
  // so an analysis that never measured subjectivity scored full marks for
  // neutrality. sample_count says whether anything was actually measured.
  // A positive sample count is REQUIRED, not merely checked for zero. Legacy
  // payloads carry `average_subjectivity_score: 0` with no count at all, and a
  // corpus whose subjectivity genuinely measured 0 is indistinguishable from
  // one where nothing was measured and the aggregator defaulted. Claiming a
  // perfect 100% neutrality from that is the bug this axis keeps producing.
  const sampled = agg.subjectivity_sample_count;
  if (typeof sampled !== "number" || sampled <= 0) return null;
  const avg = agg.average_subjectivity_score;
  if (typeof avg !== "number") return null;
  return Math.round((1 - avg) * 1000) / 10;
}

function reliability(relDist) {
  if (!relDist || !Object.keys(relDist).length) return null;
  let weighted = 0;
  let total = 0;
  for (const [k, v] of Object.entries(relDist)) {
    const w = RELIABILITY_WEIGHTS[k] ?? 0;
    const c = v.count || 0;
    weighted += w * c;
    total += c;
  }
  if (!total) return null;
  return Math.round((weighted / total) * 10) / 10;
}

export function sourceCountOf(analysis) {
  return analysis?.source_count ?? analysis?.sources?.length ?? 0;
}

// An analysis "has data" if it counted sources OR carries any non-empty
// distribution. Requiring source_count alone would zero out callers that pass
// only an aggregate.
function hasMeasurements(analysis, agg) {
  if (sourceCountOf(analysis) > 0) return true;
  if (
    [
      agg.geography_distribution,
      agg.political_leaning_distribution,
      agg.reliability_distribution,
      agg.author_gender_distribution,
    ].some((d) => d && Object.keys(d).length > 0)
  ) {
    return true;
  }
  // A non-zero subjectivity score also proves something was measured. Zero is
  // excluded deliberately: the aggregator emits exactly 0.0 when it scored
  // nothing, which is the case this guard exists to catch.
  return typeof agg.average_subjectivity_score === "number"
    && agg.average_subjectivity_score > 0;
}

export function computeRadarAxes(analysis) {
  const agg = analysis?.aggregated_bias || {};
  // With nothing analysed, every axis is 0 -- an empty profile, not a perfect
  // one. Zero references must never render as a full-scale radar.
  const hasSources = hasMeasurements(analysis, agg);
  if (!hasSources) {
    // null, not 0: nothing was measured, and a 0 reads as a real score of
    // zero. The UI renders null as "no data".
    return Object.fromEntries(RADAR_AXES.map((a) => [a, null]));
  }
  return {
    geo_diversity: geoDiversity(agg.geography_distribution),
    political_pluralism: politicalPluralism(agg.political_leaning_distribution),
    author_parity: authorParity(agg.author_gender_distribution),
    neutrality: neutrality(agg, hasSources),
    reliability: reliability(agg.reliability_distribution),
  };
}

// Axis wording moved to i18n (`radar.axisLong.*`); only the ordered key list
// belongs in the data layer now.
export { RADAR_AXES };

export function useRadarData() {
  return { computeRadarAxes, RADAR_AXES };
}
