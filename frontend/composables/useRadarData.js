const RELIABILITY_WEIGHTS = {
  academic: 100,
  high: 80,
  medium: 50,
  low: 20,
  unknown: 0,
};

function geoDiversity(geoDist) {
  if (!geoDist || !Object.keys(geoDist).length) return 0;
  let maxPct = 0;
  for (const k of Object.keys(geoDist)) {
    if (k.toLowerCase() === "non-mappé" || k.toLowerCase() === "unknown") continue;
    maxPct = Math.max(maxPct, geoDist[k].percentage || 0);
  }
  return Math.round((100 - maxPct) * 10) / 10;
}

function politicalPluralism(leanDist) {
  if (!leanDist) return 0;
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
  if (!genderDist) return 0;
  const male = genderDist.male?.percentage ?? 0;
  const female = genderDist.female?.percentage ?? 0;
  return Math.round(Math.min(male, female) * 2 * 10) / 10;
}

function neutrality(avgSubj) {
  const s = typeof avgSubj === "number" ? avgSubj : 0;
  return Math.round((1 - s) * 1000) / 10;
}

function reliability(relDist) {
  if (!relDist) return 0;
  let weighted = 0;
  let total = 0;
  for (const [k, v] of Object.entries(relDist)) {
    const w = RELIABILITY_WEIGHTS[k] ?? 0;
    const c = v.count || 0;
    weighted += w * c;
    total += c;
  }
  if (!total) return 0;
  return Math.round((weighted / total) * 10) / 10;
}

export function computeRadarAxes(analysis) {
  const agg = analysis?.aggregated_bias || {};
  return {
    geo_diversity: geoDiversity(agg.geography_distribution),
    political_pluralism: politicalPluralism(agg.political_leaning_distribution),
    author_parity: authorParity(agg.author_gender_distribution),
    neutrality: neutrality(agg.average_subjectivity_score),
    reliability: reliability(agg.reliability_distribution),
  };
}

export const RADAR_LABELS = {
  geo_diversity: "Diversité géographique",
  political_pluralism: "Pluralisme politique",
  author_parity: "Parité auteur",
  neutrality: "Neutralité",
  reliability: "Fiabilité",
};

export function useRadarData() {
  return { computeRadarAxes, RADAR_LABELS };
}
