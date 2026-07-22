import { describe, it, expect } from "vitest";
import {
  buildV2Model,
  concentration,
  coverage,
  foldBars,
  genderDisagreements,
  genderEvidenceSplit,
  isEmptyDistribution,
  languageMetrics,
  readabilityMetric,
  sourcesForBucket,
  splitDistribution,
  toEntries,
} from "../composables/useV2Data.js";
import { computeRadarAxes } from "../composables/useRadarData.js";

import fr from "./fixtures/analysis-fr.json";
import de from "./fixtures/analysis-de.json";
import en from "./fixtures/analysis-en.json";

const FIXTURES = { fr, de, en };

/* ------------------------------------------------------------------ *
 * The bugs v2 exists to fix
 * ------------------------------------------------------------------ */

describe("the v1 keys that do not exist", () => {
  it("confirms the backend never sends the keys v1 read", () => {
    for (const [name, payload] of Object.entries(FIXTURES)) {
      const agg = payload.aggregated_bias;
      // v1's authorParity read this. It is not in any response.
      expect(agg.author_gender_distribution, name).toBeUndefined();
      // The real keys:
      expect(agg.author_gender_distribution_estimate, name).toBeDefined();
      expect(agg.human_author_gender_distribution, name).toBeDefined();
      // v1's neutrality read a TOP-LEVEL average_subjectivity_score. The value
      // it wants lives one level down, inside language_bias_metrics.
      expect(agg.language_bias_metrics.average_subjectivity_score, name).toBeDefined();
    }
  });

  it("shows v1's author_parity axis is pinned at zero on every payload", () => {
    // Not a test of v2 — a regression guard on the claim that motivates it.
    // `author_gender_distribution` is undefined, so male/female both read 0.
    for (const [name, payload] of Object.entries(FIXTURES)) {
      expect(computeRadarAxes(payload).author_parity, name).toBe(0);
    }
  });

  it("shows v1's neutrality axis is a constant determined by payload shape", () => {
    // The backend emits two shapes. Older responses (fr, de) have no top-level
    // `average_subjectivity_score` at all, so v1 reads undefined and its guard
    // floors the axis to 0. Newer responses (en) carry a legacy top-level copy
    // whose value is 0.0 — and v1 computes `1 - 0` = a PERFECT 100.
    //
    // So the same article scores 0 or 100 for "neutrality" depending only on
    // which cache format answered. Neither number measured anything: every
    // real payload reports a subjectivity of exactly 0.0.
    expect(fr.aggregated_bias.average_subjectivity_score).toBeUndefined();
    expect(computeRadarAxes(fr).neutrality).toBe(0);
    expect(computeRadarAxes(de).neutrality).toBe(0);

    expect(en.aggregated_bias.average_subjectivity_score).toBe(0);
    expect(computeRadarAxes(en).neutrality).toBe(100);
  });

  it("v2 reports the measured subjectivity as itself, not as a neutrality score", () => {
    // 0.0 subjectivity is reported as 0.0 subjectivity on a 0–1 scale, with its
    // sample size attached. It is never inverted into "100% neutral".
    for (const [name, payload] of Object.entries(FIXTURES)) {
      const m = buildV2Model(payload);
      expect(m.language.subjectivity.value, name).toBe(0);
      expect(m.language.subjectivity.max, name).toBe(1);
    }
  });

  it("reads the corrected keys through the v2 model", () => {
    const model = buildV2Model(de);
    // author_gender_distribution_estimate: {female: 13, male: 13, unknown: 74}
    expect(model.authors.aggregateGenderEstimate.available).toBe(true);
    // language_bias_metrics.average_subjectivity_score, read from the right place.
    expect(model.language.available).toBe(true);
    expect(model.language.sensationalism.value).toBeCloseTo(0.03, 5);
  });
});

/* ------------------------------------------------------------------ *
 * Distribution primitives
 * ------------------------------------------------------------------ */

describe("isEmptyDistribution", () => {
  it("distinguishes 'not measured' from a measured zero", () => {
    expect(isEmptyDistribution({})).toBe(true);
    expect(isEmptyDistribution(null)).toBe(true);
    expect(isEmptyDistribution(undefined)).toBe(true);
    // A real, measured zero is NOT empty.
    expect(isEmptyDistribution({ male: { count: 0, percentage: 0 } })).toBe(false);
  });

  it("flags the distributions the backend leaves empty on real articles", () => {
    // Employers are `{}` on all three real payloads. The UI must say "not
    // available", never draw an empty chart or a set of zeroes.
    for (const [name, payload] of Object.entries(FIXTURES)) {
      expect(
        isEmptyDistribution(payload.aggregated_bias.human_author_employer_distribution),
        name,
      ).toBe(true);
    }
  });
});

describe("toEntries", () => {
  it("normalises the counted shape", () => {
    expect(toEntries({ France: { count: 7, percentage: 87.5 }, Unknown: { count: 1, percentage: 12.5 } })).toEqual([
      { key: "France", count: 7, percentage: 87.5 },
      { key: "Unknown", count: 1, percentage: 12.5 },
    ]);
  });

  it("normalises the flat-percentage shape without inventing counts", () => {
    // `author_gender_distribution_estimate` has no counts. Back-computing them
    // from rounded percentages would fabricate numbers, so `count` stays null.
    const out = toEntries({ female: 5.0, male: 5.0, unknown: 90.0 });
    expect(out[0]).toEqual({ key: "unknown", count: null, percentage: 90 });
    expect(out.every((e) => e.count === null)).toBe(true);
  });

  it("returns [] for an empty or missing distribution", () => {
    expect(toEntries({})).toEqual([]);
    expect(toEntries(null)).toEqual([]);
  });

  it("sorts descending, breaking ties by key for a stable order", () => {
    const out = toEntries({ b: { count: 1, percentage: 25 }, a: { count: 1, percentage: 25 }, c: { count: 2, percentage: 50 } });
    expect(out.map((e) => e.key)).toEqual(["c", "a", "b"]);
  });
});

describe("coverage", () => {
  it("computes the 'based on N of M' record", () => {
    expect(coverage(6, 8)).toEqual({ known: 6, total: 8, pct: 75, partial: true, complete: false, empty: false });
    expect(coverage(8, 8).complete).toBe(true);
    expect(coverage(0, 8).empty).toBe(true);
  });

  it("never divides by zero", () => {
    expect(coverage(0, 0)).toEqual({ known: 0, total: 0, pct: 0, partial: false, complete: false, empty: true });
  });
});

describe("splitDistribution", () => {
  it("moves 'unknown' out of the chart and into coverage", () => {
    // Real French payload: 87.5% of leanings are unknown. Charting that dict
    // raw makes "unknown" the tallest bar and the apparent finding.
    const split = splitDistribution(fr.aggregated_bias.political_leaning_distribution, { total: 8 });
    expect(split.known.map((e) => e.key)).toEqual(["center-right"]);
    expect(split.unknown.count).toBe(7);
    expect(split.coverage).toMatchObject({ known: 1, total: 8, partial: true });
  });

  it("treats 'unmapped' the same as 'unknown'", () => {
    const split = splitDistribution({ France: { count: 3, percentage: 75 }, unmapped: { count: 1, percentage: 25 } });
    expect(split.known).toHaveLength(1);
    expect(split.unknown.count).toBe(1);
  });

  it("reports availability false for an empty distribution", () => {
    const split = splitDistribution({});
    expect(split.available).toBe(false);
    expect(split.known).toEqual([]);
  });

  it("handles a distribution that is entirely unknown", () => {
    // The French payload's human_author_gender_distribution is 6 unknown, 0
    // female, 0 male. There is no known bucket at all — and 0/0 must not throw.
    const split = splitDistribution(fr.aggregated_bias.human_author_gender_distribution);
    expect(split.available).toBe(true);
    // female/male are present but zero, so they are "known" buckets with 0.
    expect(split.unknown.count).toBe(6);
    expect(split.coverage.known).toBe(0);
    expect(split.coverage.empty).toBe(true);
  });
});

describe("foldBars", () => {
  it("leaves a short list alone", () => {
    const entries = [{ key: "a", count: 1, percentage: 50 }];
    expect(foldBars(entries, 12)).toEqual({ bars: entries, folded: null });
  });

  it("folds the tail without losing it", () => {
    const entries = Array.from({ length: 6 }, (_, i) => ({ key: `k${i}`, count: 1, percentage: 10 }));
    const { bars, folded } = foldBars(entries, 3);
    expect(bars).toHaveLength(2);
    expect(folded.members).toEqual(["k2", "k3", "k4", "k5"]);
    expect(folded.count).toBe(4);
    // The folded rows keep their real values so the table view stays complete.
    expect(folded.rows).toHaveLength(4);
  });
});

/* ------------------------------------------------------------------ *
 * Drill-down
 * ------------------------------------------------------------------ */

describe("sourcesForBucket", () => {
  it("returns exactly the sources a bar counts", () => {
    // The chart says 7 French sources; the drawer must open 7.
    const bucket = fr.aggregated_bias.geography_distribution.France;
    const got = sourcesForBucket(fr.sources, "geography", "France");
    expect(got).toHaveLength(bucket.count);
  });

  it("reproduces every counted bucket of every dimension on all fixtures", () => {
    const pairs = [
      ["geography", "geography_distribution"],
      ["language", "language_distribution"],
      ["source_type", "source_type_distribution"],
      ["political_leaning", "political_leaning_distribution"],
      ["reliability", "reliability_distribution"],
    ];
    for (const [name, payload] of Object.entries(FIXTURES)) {
      for (const [dimension, key] of pairs) {
        for (const [bucket, v] of Object.entries(payload.aggregated_bias[key])) {
          expect(
            sourcesForBucket(payload.sources, dimension, bucket).length,
            `${name}/${dimension}/${bucket}`,
          ).toBe(v.count);
        }
      }
    }
  });

  it("matches the unknown bucket against every spelling of unknown", () => {
    const sources = [{ geography: { country: "unmapped" } }, { geography: {} }, { geography: { country: "France" } }];
    expect(sourcesForBucket(sources, "geography", "Unknown")).toHaveLength(2);
  });

  it("is empty for the synthetic 'other' bucket and unknown dimensions", () => {
    expect(sourcesForBucket(fr.sources, "geography", "__other__")).toEqual([]);
    expect(sourcesForBucket(fr.sources, "nope", "France")).toEqual([]);
    expect(sourcesForBucket(null, "geography", "France")).toEqual([]);
  });
});

/* ------------------------------------------------------------------ *
 * Measured vs estimated
 * ------------------------------------------------------------------ */

describe("genderEvidenceSplit", () => {
  it("keeps Wikidata and heuristic counts in separate distributions", () => {
    const split = genderEvidenceSplit(de.sources);
    expect(split.total).toBeGreaterThan(0);
    // The two coverages are computed against the same denominator but never
    // summed into one chart.
    expect(split.measured.coverage.total).toBe(split.total);
    expect(split.estimated.coverage.total).toBe(split.total);
    expect(split.measured.provenance).toBe("wikidata");
    expect(split.estimated.provenance).toBe("heuristic");
  });

  it("never counts an author into both channels", () => {
    for (const [name, payload] of Object.entries(FIXTURES)) {
      const s = genderEvidenceSplit(payload.sources);
      const sum = s.measured.coverage.known + s.estimated.coverage.known + s.undetermined;
      expect(sum, name).toBe(s.total);
    }
  });

  it("reports zero confirmed authors as empty coverage, not as a 0% bucket", () => {
    const split = genderEvidenceSplit([
      { author_profiles: [{ name: "X", gender: "unknown", confidence: { gender: 0.7 }, wikidata_author: {} }] },
    ]);
    expect(split.measured.coverage.empty).toBe(true);
    // Crucially: no entries at all, so nothing can render as "0% women".
    expect(split.measured.entries).toEqual([]);
    expect(split.undetermined).toBe(1);
  });

  it("handles a corpus with no authors at all", () => {
    const split = genderEvidenceSplit([{ url: "https://x.test" }]);
    expect(split.total).toBe(0);
    expect(split.measured.coverage.total).toBe(0);
  });
});

describe("genderDisagreements", () => {
  it("finds the authors the heuristic got wrong on the real German payload", () => {
    // Constantin Magnis: heuristic returns "unknown" at confidence 0.7 while
    // Wikidata states "male". This is the receipt for splitting the channels.
    const diffs = genderDisagreements(de.sources);
    const magnis = diffs.find((d) => d.name === "Constantin Magnis");
    expect(magnis).toBeTruthy();
    expect(magnis.kind).toBe("missed");
    expect(magnis.estimated).toBeNull();
    expect(magnis.measured).toBe("male");
    expect(magnis.wikidataId).toBe("Q109623417");
  });

  it("classifies a contradiction separately from a miss", () => {
    const diffs = genderDisagreements([
      {
        author_profiles: [
          { name: "A", gender: "female", confidence: { gender: 0.9 }, wikidata_author: { wikidata_id: "Q1", gender: "male" } },
          { name: "B", gender: "unknown", confidence: { gender: 0.7 }, wikidata_author: { wikidata_id: "Q2", gender: "female" } },
        ],
      },
    ]);
    expect(diffs.map((d) => d.kind)).toEqual(["contradicted", "missed"]);
  });

  it("says nothing when the two channels agree", () => {
    const diffs = genderDisagreements([
      { author_profiles: [{ name: "A", gender: "female", wikidata_author: { wikidata_id: "Q1", gender: "female" } }] },
    ]);
    expect(diffs).toEqual([]);
  });
});

/* ------------------------------------------------------------------ *
 * Metrics with sample sizes
 * ------------------------------------------------------------------ */

describe("languageMetrics", () => {
  it("reads the nested key v1 read from the top level", () => {
    const m = languageMetrics(en.aggregated_bias, en.source_count);
    expect(m.available).toBe(true);
    expect(m.subjectivity.value).toBe(
      en.aggregated_bias.language_bias_metrics.average_subjectivity_score,
    );
  });

  it("uses the backend's own sample counts when it sends them", () => {
    // The English payload carries subjectivity_sample_count / sensationalism_sample_count.
    const m = languageMetrics(en.aggregated_bias, en.source_count);
    expect(m.subjectivity.sampled).toBe(true);
    expect(m.subjectivity.coverage.known).toBe(en.aggregated_bias.subjectivity_sample_count);
  });

  it("flags a fallback sample size as unverified rather than claiming full coverage", () => {
    // The French and German payloads omit the sample counts entirely.
    const m = languageMetrics(fr.aggregated_bias, fr.source_count);
    expect(m.subjectivity.sampled).toBe(false);
  });

  it("returns nulls rather than zeroes when the block is missing", () => {
    const m = languageMetrics({}, 5);
    expect(m.available).toBe(false);
    expect(m.subjectivity).toBeNull();
    expect(m.sensationalism).toBeNull();
  });

  it("keeps a genuine 0.0 as a value, not as 'missing'", () => {
    // Every real payload has average_subjectivity_score === 0.0. That is a
    // measurement, and must survive as one.
    const m = languageMetrics(fr.aggregated_bias, 8);
    expect(m.subjectivity).not.toBeNull();
    expect(m.subjectivity.value).toBe(0);
  });
});

describe("readabilityMetric", () => {
  it("uses readability_count as the real sample size", () => {
    const r = readabilityMetric(fr.aggregated_bias, fr.source_count);
    expect(r.available).toBe(true);
    // 7 of 8 sources could actually be scored.
    expect(r.coverage).toMatchObject({ known: 7, total: 8, partial: true });
    expect(r.sampled).toBe(true);
  });

  it("bands the Flesch score", () => {
    expect(readabilityMetric({ readability_metrics: { average_flesch_reading_ease: 70 } }, 1).band).toBe("easy");
    expect(readabilityMetric({ readability_metrics: { average_flesch_reading_ease: 36.87 } }, 1).band).toBe("difficult");
    expect(readabilityMetric({ readability_metrics: { average_flesch_reading_ease: 12 } }, 1).band).toBe("veryDifficult");
  });

  it("is unavailable rather than zero when nothing was scored", () => {
    expect(readabilityMetric({}, 5)).toEqual({ available: false });
    expect(readabilityMetric({ readability_metrics: {} }, 5)).toEqual({ available: false });
  });
});

/* ------------------------------------------------------------------ *
 * The one composite
 * ------------------------------------------------------------------ */

describe("concentration", () => {
  it("computes the share of the largest known bucket and shows its inputs", () => {
    // German payload: 10 of 10 sources are German, so 100% — and the reader
    // can check it against the chart directly above.
    const c = concentration(de.aggregated_bias.geography_distribution, { dimension: "geography" });
    expect(c.available).toBe(true);
    expect(c.top).toBe("Germany");
    expect(c.value).toBe(100);
    expect(c.inputs).toMatchObject({ topKey: "Germany", topValue: 10, knownTotal: 10 });
    expect(c.formula).toContain("largest known bucket");
  });

  it("excludes unknown buckets so an unplaceable corpus cannot read as diverse", () => {
    // French payload: France 7, Unknown 1. Over KNOWN buckets that is 7/7 = 100%,
    // not 7/8 = 87.5%. The excluded source is reported separately.
    const c = concentration(fr.aggregated_bias.geography_distribution, { dimension: "geography" });
    expect(c.value).toBe(100);
    expect(c.inputs.knownTotal).toBe(7);
    expect(c.inputs.excluded).toBe(1);
    expect(c.coverage).toMatchObject({ known: 7, total: 8 });
  });

  it("is unavailable — not zero — when nothing is known", () => {
    expect(concentration({}, { dimension: "geography" }).available).toBe(false);
    expect(concentration({ Unknown: { count: 5, percentage: 100 } }).available).toBe(false);
  });
});

/* ------------------------------------------------------------------ *
 * The whole model, against all three real payloads
 * ------------------------------------------------------------------ */

describe("buildV2Model", () => {
  it.each(Object.keys(FIXTURES))("builds a complete model for the %s payload", (name) => {
    const payload = FIXTURES[name];
    const m = buildV2Model(payload);

    expect(m.sourceCount).toBe(payload.source_count);
    expect(m.sources).toHaveLength(payload.sources.length);
    expect(m.evidence.total).toBe(payload.sources.length);

    // Every distribution section is well-formed whether or not it has data.
    const sections = [
      ...Object.values(m.corpus),
      ...Object.values(m.editorial),
      m.authors.type,
      m.authors.nationality,
      m.authors.citizenship,
      m.authors.occupation,
      m.authors.employer,
    ];
    for (const s of sections) {
      expect(typeof s.available).toBe("boolean");
      expect(Array.isArray(s.bars)).toBe(true);
      // An unavailable section must carry a reason, so the UI can say WHY.
      if (!s.available) expect(["missing", "allUnknown"]).toContain(s.reason);
    }
  });

  it("marks the empty employer distributions as missing on every real payload", () => {
    for (const [name, payload] of Object.entries(FIXTURES)) {
      const m = buildV2Model(payload);
      expect(m.authors.employer.available, name).toBe(false);
      expect(m.authors.employer.reason, name).toBe("missing");
      expect(m.authors.employerCountry.reason, name).toBe("missing");
    }
  });

  it("degrades gracefully on the sparse German payload", () => {
    const m = buildV2Model(de);
    // Occupations ARE present here (journalist/writer/author) but employers are not.
    expect(m.authors.occupation.available).toBe(true);
    expect(m.authors.employer.available).toBe(false);
    // Citizenship covers only 2 of 8 human authors — a real partial coverage.
    expect(m.authors.citizenship.available).toBe(true);
  });

  it("survives an empty, partial or malformed payload without throwing", () => {
    for (const bad of [null, undefined, {}, { sources: null }, { aggregated_bias: null, sources: [] }]) {
      const m = buildV2Model(bad);
      expect(m.sourceCount).toBe(0);
      expect(m.sources).toEqual([]);
      expect(m.authors.gender.total).toBe(0);
      expect(m.derived.every((d) => !d.available)).toBe(true);
      expect(m.language.available).toBe(false);
      expect(m.readability.available).toBe(false);
    }
  });

  it("counts evidence coverage against the real corpus", () => {
    const m = buildV2Model(de);
    // Every coverage record is a subset of the corpus, never more.
    for (const k of ["wikidata", "mbfc", "geographyMeasured", "leaningKnown", "reliabilityMeasured"]) {
      expect(m.evidence[k].known).toBeLessThanOrEqual(m.evidence.total);
      expect(m.evidence[k].known).toBeGreaterThanOrEqual(0);
    }
  });
});
