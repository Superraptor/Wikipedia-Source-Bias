/**
 * v2 data shaping.
 *
 * v1 turned the payload into five invented composite scores. Two of them read
 * keys that do not exist in any response the backend has ever sent:
 *
 *   - `author_gender_distribution`        -> real key is `author_gender_distribution_estimate`
 *                                            (and `human_author_gender_distribution`)
 *   - `average_subjectivity_score` (top)  -> really `language_bias_metrics.average_subjectivity_score`
 *
 * Both therefore silently evaluated to 0 and the radar drew two axes pinned at
 * the origin for every article ever analysed. v2 does not reproduce those
 * scores. It reads the distributions the backend actually returns and shows
 * them as distributions.
 *
 * Everything in this file is a pure function of the payload so it can be tested
 * without a component or a network call.
 */

import {
  EVIDENCE,
  PROVENANCE,
  authorGenderEvidence,
  authorNationalityEvidence,
  geographyEvidence,
  isUnknownKey,
  leaningEvidence,
  mbfcRef,
  publisherWikidataRef,
  reliabilityEvidence,
} from "../utils/provenance.js";

/** Bars beyond this fold into an "other" bucket; the table view still lists all. */
const MAX_BARS = 12;

/* ------------------------------------------------------------------ *
 * Distribution primitives
 * ------------------------------------------------------------------ */

/**
 * True when the backend returned nothing for a distribution.
 *
 * The backend emits `{}` for distributions it could not compute at all
 * (`human_author_employer_distribution` is `{}` on every article tested). That
 * is "not available", and rendering it as an empty chart — or worse, as a set
 * of zeroes — asserts a measurement that never happened. Callers must branch on
 * this before charting.
 */
export function isEmptyDistribution(dist) {
  return !dist || typeof dist !== "object" || Object.keys(dist).length === 0;
}

/**
 * Normalise the two distribution shapes the backend uses into one.
 *
 *   `{France: {count: 7, percentage: 87.5}}`   -> counted
 *   `{female: 5.0, male: 5.0, unknown: 90.0}`  -> percentage-only (no counts)
 *
 * `count` stays `null` in the second case rather than being back-computed: the
 * percentages are rounded, so any count derived from them would be a fabricated
 * number presented with the authority of a real one.
 */
export function toEntries(dist) {
  if (isEmptyDistribution(dist)) return [];
  return Object.entries(dist)
    .map(([key, value]) => {
      if (value && typeof value === "object") {
        return {
          key,
          count: typeof value.count === "number" ? value.count : null,
          percentage: typeof value.percentage === "number" ? value.percentage : 0,
        };
      }
      return { key, count: null, percentage: typeof value === "number" ? value : 0 };
    })
    .sort((a, b) => b.percentage - a.percentage || String(a.key).localeCompare(String(b.key)));
}

/** `{known, total, pct, partial, complete}` — how much of the corpus a metric covers. */
export function coverage(known, total) {
  const k = Number(known) || 0;
  const t = Number(total) || 0;
  return {
    known: k,
    total: t,
    pct: t > 0 ? Math.round((k / t) * 1000) / 10 : 0,
    partial: t > 0 && k < t,
    complete: t > 0 && k === t,
    empty: k === 0,
  };
}

/**
 * Split a distribution into the buckets that mean something and the
 * "unknown" bucket, and report coverage.
 *
 * Charting "unknown" alongside real categories is the single most misleading
 * thing v1 did: on the French test article `political_leaning_distribution` is
 * 87.5% unknown, and a bar chart of the raw dict makes "unknown" the headline
 * finding about the article's politics. Here "unknown" leaves the chart and
 * becomes a coverage statement printed next to it.
 */
export function splitDistribution(dist, { total = null } = {}) {
  const entries = toEntries(dist);
  const known = entries.filter((e) => !isUnknownKey(e.key));
  const unknown = entries.filter((e) => isUnknownKey(e.key));

  const countable = entries.every((e) => typeof e.count === "number");
  const sumCount = (list) => list.reduce((a, e) => a + (e.count || 0), 0);

  const knownCount = countable ? sumCount(known) : null;
  const totalCount = total ?? (countable ? sumCount(entries) : null);

  return {
    available: entries.length > 0,
    entries,
    known,
    unknown: unknown.length
      ? { count: countable ? sumCount(unknown) : null, percentage: unknown.reduce((a, e) => a + e.percentage, 0) }
      : null,
    counted: countable,
    coverage:
      knownCount === null || totalCount === null
        ? coverage(known.length ? 1 : 0, entries.length ? 1 : 0)
        : coverage(knownCount, totalCount),
  };
}

/** Top-N bars plus a folded "other" bucket; nothing is dropped, only grouped. */
export function foldBars(entries, max = MAX_BARS) {
  if (entries.length <= max) return { bars: entries, folded: null };
  const bars = entries.slice(0, max - 1);
  const rest = entries.slice(max - 1);
  return {
    bars,
    folded: {
      key: "__other__",
      count: rest.every((e) => typeof e.count === "number")
        ? rest.reduce((a, e) => a + e.count, 0)
        : null,
      percentage: Math.round(rest.reduce((a, e) => a + e.percentage, 0) * 10) / 10,
      members: rest.map((e) => e.key),
      // The folded entries keep their real values so the table view can list
      // every bucket. Folding is a chart-density decision, never data loss.
      rows: rest,
    },
  };
}

/* ------------------------------------------------------------------ *
 * Drill-down: which sources are in a bucket
 * ------------------------------------------------------------------ */

/**
 * How each chartable dimension reads a value off one source.
 *
 * This is what makes every bar clickable: the chart and the drill-down read the
 * same accessor, so a bar labelled "France · 7" is guaranteed to open exactly
 * seven sources. A bar whose count cannot be reproduced from the sources array
 * is a bug the drill-down makes visible instead of hiding.
 */
export const DIMENSIONS = {
  geography: (s) => s?.geography?.country,
  region: (s) => s?.geography?.region,
  language: (s) => s?.language,
  source_type: (s) => s?.source_type,
  political_leaning: (s) => s?.political_leaning,
  reliability: (s) => s?.reliability,
};

/** The sources that contributed to one bucket of one dimension. */
export function sourcesForBucket(sources, dimension, key) {
  const read = DIMENSIONS[dimension];
  if (!read || !Array.isArray(sources)) return [];
  if (key === "__other__") return [];
  const wanted = String(key).toLowerCase();
  return sources.filter((s) => {
    const v = read(s);
    if (isUnknownKey(key)) return isUnknownKey(v);
    return v != null && String(v).toLowerCase() === wanted;
  });
}

/* ------------------------------------------------------------------ *
 * Authors: the measured / estimated split
 * ------------------------------------------------------------------ */

/** Every author profile in the corpus, tagged with the source it came from. */
export function allAuthors(sources) {
  if (!Array.isArray(sources)) return [];
  return sources.flatMap((s) =>
    (s.author_profiles || []).map((profile) => ({ profile, source: s })),
  );
}

/**
 * Gender, split by how we know it.
 *
 * Deliberately NOT a single merged distribution. Wikidata-sourced gender and
 * name-spelling-guessed gender are different claims about the world and are
 * returned as two separate distributions with their own coverage, so the UI
 * cannot accidentally add them together.
 */
export function genderEvidenceSplit(sources) {
  const authors = allAuthors(sources);
  const measured = {};
  const estimated = {};
  let measuredCount = 0;
  let estimatedCount = 0;
  let absentCount = 0;

  for (const { profile } of authors) {
    const ev = authorGenderEvidence(profile);
    if (ev.evidence === EVIDENCE.MEASURED) {
      measured[ev.value] = (measured[ev.value] || 0) + 1;
      measuredCount += 1;
    } else if (ev.evidence === EVIDENCE.ESTIMATED) {
      estimated[ev.value] = (estimated[ev.value] || 0) + 1;
      estimatedCount += 1;
    } else {
      absentCount += 1;
    }
  }

  const asEntries = (obj, denom) =>
    Object.entries(obj)
      .map(([key, count]) => ({
        key,
        count,
        percentage: denom ? Math.round((count / denom) * 1000) / 10 : 0,
      }))
      .sort((a, b) => b.count - a.count);

  return {
    total: authors.length,
    measured: {
      entries: asEntries(measured, measuredCount),
      coverage: coverage(measuredCount, authors.length),
      provenance: PROVENANCE.WIKIDATA,
      evidence: EVIDENCE.MEASURED,
    },
    estimated: {
      entries: asEntries(estimated, estimatedCount),
      coverage: coverage(estimatedCount, authors.length),
      provenance: PROVENANCE.HEURISTIC,
      evidence: EVIDENCE.ESTIMATED,
    },
    undetermined: absentCount,
  };
}

/**
 * Authors where the name-origin guess contradicts (or is beaten by) Wikidata.
 *
 * This is the receipt for treating the two channels differently. On the German
 * test article the heuristic returns `unknown` at confidence 0.7 for
 * Constantin Magnis while Wikidata states `male`; the aggregate
 * `human_author_gender_distribution` reports 87.5% "unknown" as a result. The
 * aggregate is not wrong about what the heuristic produced — it is wrong as a
 * description of the authors.
 */
export function genderDisagreements(sources) {
  const out = [];
  for (const { profile, source } of allAuthors(sources)) {
    const wd = profile?.wikidata_author || {};
    const truth = wd.gender && !isUnknownKey(wd.gender) ? String(wd.gender).toLowerCase() : null;
    if (!truth) continue;
    const guess = isUnknownKey(profile?.gender) ? null : String(profile.gender).toLowerCase();
    if (guess === truth) continue;
    out.push({
      name: profile?.name || wd.wikidata_name || "",
      estimated: guess,
      measured: truth,
      confidence: profile?.confidence?.gender ?? null,
      wikidataId: wd.wikidata_id || null,
      domain: source?.domain || null,
      kind: guess === null ? "missed" : "contradicted",
    });
  }
  return out;
}

/* ------------------------------------------------------------------ *
 * Corpus-level evidence coverage
 * ------------------------------------------------------------------ */

/** How many sources carry a Wikidata publisher item / an MBFC record. */
export function evidenceCoverage(sources) {
  const list = Array.isArray(sources) ? sources : [];
  const total = list.length;
  let wikidata = 0;
  let mbfc = 0;
  let geoMeasured = 0;
  let leanKnown = 0;
  let relMeasured = 0;

  for (const s of list) {
    if (publisherWikidataRef(s)) wikidata += 1;
    if (mbfcRef(s)) mbfc += 1;
    if (geographyEvidence(s).evidence === EVIDENCE.MEASURED) geoMeasured += 1;
    if (leaningEvidence(s).evidence !== EVIDENCE.ABSENT) leanKnown += 1;
    if (reliabilityEvidence(s).evidence === EVIDENCE.MEASURED) relMeasured += 1;
  }

  return {
    total,
    wikidata: coverage(wikidata, total),
    mbfc: coverage(mbfc, total),
    geographyMeasured: coverage(geoMeasured, total),
    leaningKnown: coverage(leanKnown, total),
    reliabilityMeasured: coverage(relMeasured, total),
  };
}

/* ------------------------------------------------------------------ *
 * Derived indicators — the only composites in v2, and they show their work
 * ------------------------------------------------------------------ */

/**
 * Concentration = the share held by the largest known bucket.
 *
 * This is the one composite v2 keeps, and it is kept because it is a single
 * arithmetic step over one visible distribution: the reader can check it by
 * looking at the tallest bar in the chart directly above it. `inputs` and
 * `formula` are returned with the value so the UI can show the exact numbers
 * that went in — that is what makes it inspectable rather than invented.
 *
 * Computed over KNOWN buckets only, so an article whose sources are mostly
 * unplaced does not read as "perfectly diverse".
 */
export function concentration(dist, { dimension = null } = {}) {
  const split = splitDistribution(dist);
  if (!split.known.length) {
    return { available: false, dimension, value: null, coverage: split.coverage };
  }

  const knownTotal = split.counted
    ? split.known.reduce((a, e) => a + (e.count || 0), 0)
    : split.known.reduce((a, e) => a + e.percentage, 0);
  const top = split.known[0];
  const topValue = split.counted ? top.count || 0 : top.percentage;
  const value = knownTotal > 0 ? Math.round((topValue / knownTotal) * 1000) / 10 : 0;

  return {
    available: true,
    dimension,
    value,
    top: top.key,
    formula: "share = largest known bucket / all known buckets × 100",
    inputs: {
      topKey: top.key,
      topValue,
      knownTotal,
      unit: split.counted ? "sources" : "percent",
      excluded: split.unknown ? split.unknown.count ?? split.unknown.percentage : 0,
    },
    coverage: split.coverage,
  };
}

/* ------------------------------------------------------------------ *
 * Language & readability metrics (the keys v1 read from the wrong place)
 * ------------------------------------------------------------------ */

/**
 * Language-bias metrics, read from `language_bias_metrics` where they actually
 * live. v1 read `average_subjectivity_score` off the top level of
 * `aggregated_bias`, got `undefined`, and computed `1 - undefined` -> `NaN`,
 * which its own guard then floored to 0.
 *
 * Coverage comes from `subjectivity_sample_count` / `sensationalism_sample_count`
 * when the backend sends them (older payloads omit them) and falls back to the
 * source count, flagged as unverified.
 */
export function languageMetrics(agg, sourceCount) {
  const lbm = agg?.language_bias_metrics || {};
  const has = (v) => typeof v === "number" && Number.isFinite(v);

  const subjSamples = has(agg?.subjectivity_sample_count) ? agg.subjectivity_sample_count : null;
  const sensSamples = has(agg?.sensationalism_sample_count)
    ? agg.sensationalism_sample_count
    : null;

  return {
    available: Object.keys(lbm).length > 0,
    subjectivity: has(lbm.average_subjectivity_score)
      ? {
          value: lbm.average_subjectivity_score,
          max: 1,
          coverage: coverage(subjSamples ?? sourceCount, sourceCount),
          sampled: subjSamples !== null,
        }
      : null,
    sensationalism: has(lbm.average_sensationalism_score)
      ? {
          value: lbm.average_sensationalism_score,
          max: 1,
          coverage: coverage(sensSamples ?? sourceCount, sourceCount),
          sampled: sensSamples !== null,
        }
      : null,
    opinion: has(lbm.opinion_percentage)
      ? {
          value: lbm.opinion_percentage,
          max: 100,
          coverage: coverage(sourceCount, sourceCount),
          sampled: true,
        }
      : null,
  };
}

/**
 * Readability. `readability_count` is the backend telling us exactly how many
 * sources it could actually score — the sample size v1 never showed.
 */
export function readabilityMetric(agg, sourceCount) {
  const rm = agg?.readability_metrics || {};
  if (typeof rm.average_flesch_reading_ease !== "number") {
    return { available: false };
  }
  const scored = typeof rm.readability_count === "number" ? rm.readability_count : null;
  return {
    available: true,
    value: rm.average_flesch_reading_ease,
    coverage: coverage(scored ?? 0, sourceCount),
    sampled: scored !== null,
    // Flesch bands, so the number means something to a reader who has never
    // heard of Flesch. Bands are the standard published ones.
    band:
      rm.average_flesch_reading_ease >= 60
        ? "easy"
        : rm.average_flesch_reading_ease >= 30
          ? "difficult"
          : "veryDifficult",
  };
}

/* ------------------------------------------------------------------ *
 * The model
 * ------------------------------------------------------------------ */

/** A chartable distribution section, ready for `V2BarChart`. */
function distributionSection(id, dist, { dimension = null, sources = [], total = null } = {}) {
  const split = splitDistribution(dist, { total });
  const { bars, folded } = foldBars(split.known);
  return {
    id,
    dimension,
    available: split.available && split.known.length > 0,
    // An `{}` from the backend and "we looked and found only unknowns" are
    // different states and get different empty copy.
    reason: !split.available ? "missing" : split.known.length ? null : "allUnknown",
    bars,
    folded,
    unknown: split.unknown,
    counted: split.counted,
    coverage: split.coverage,
    clickable: Boolean(dimension && sources.length),
  };
}

/**
 * Build the whole v2 view model from one `/api/analyze` payload.
 *
 * Returns plain data only — no refs, no components — so tests can assert on it
 * directly and so the same model could be rendered by something other than Vue.
 */
export function buildV2Model(analysis) {
  const agg = analysis?.aggregated_bias || {};
  const sources = Array.isArray(analysis?.sources) ? analysis.sources : [];
  const sourceCount = analysis?.source_count ?? agg.source_count ?? sources.length ?? 0;
  const authors = allAuthors(sources);

  const opts = (dimension) => ({ dimension, sources, total: sourceCount });

  return {
    title: analysis?.page_title || "",
    url: analysis?.page_url || "",
    sourceCount,
    bookCount: typeof agg.book_count === "number" ? agg.book_count : null,
    authorCount: authors.length,
    sources,

    evidence: evidenceCoverage(sources),

    corpus: {
      geography: distributionSection("geography", agg.geography_distribution, opts("geography")),
      region: distributionSection("region", agg.region_distribution, opts("region")),
      language: distributionSection("language", agg.language_distribution, opts("language")),
      sourceType: distributionSection("sourceType", agg.source_type_distribution, opts("source_type")),
    },

    editorial: {
      leaning: distributionSection(
        "leaning",
        agg.political_leaning_distribution,
        opts("political_leaning"),
      ),
      reliability: distributionSection(
        "reliability",
        agg.reliability_distribution,
        opts("reliability"),
      ),
    },

    authors: {
      total: authors.length,
      type: distributionSection("authorType", agg.author_type_distribution, {
        total: authors.length,
      }),
      gender: genderEvidenceSplit(sources),
      disagreements: genderDisagreements(sources),
      // Read from the corrected keys. Kept for the methodology panel so the
      // aggregate the backend publishes can be compared against the per-author
      // walk above; not used as the headline number.
      aggregateGenderEstimate: distributionSection(
        "aggregateGenderEstimate",
        agg.author_gender_distribution_estimate,
      ),
      aggregateHumanGender: distributionSection(
        "aggregateHumanGender",
        agg.human_author_gender_distribution,
      ),
      nationality: distributionSection(
        "authorNationality",
        agg.human_author_nationality_distribution,
      ),
      subregion: distributionSection("authorSubregion", agg.human_author_subregion_distribution),
      citizenship: distributionSection(
        "authorCitizenship",
        agg.human_author_citizenship_distribution,
      ),
      occupation: distributionSection("authorOccupation", agg.human_author_occupation_distribution),
      employer: distributionSection("authorEmployer", agg.human_author_employer_distribution),
      employerCountry: distributionSection(
        "authorEmployerCountry",
        agg.human_author_employer_country_distribution,
      ),
    },

    language: languageMetrics(agg, sourceCount),
    readability: readabilityMetric(agg, sourceCount),

    derived: [
      concentration(agg.geography_distribution, { dimension: "geography" }),
      concentration(agg.language_distribution, { dimension: "language" }),
    ],
  };
}

/** Composable wrapper, matching the shape of the other composables. */
export function useV2Data() {
  return {
    buildV2Model,
    sourcesForBucket,
    concentration,
    splitDistribution,
    coverage,
    isEmptyDistribution,
  };
}
