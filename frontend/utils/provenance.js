/**
 * Provenance & evidence grading — the spine of the v2 dashboard.
 *
 * The v1 dashboard presented every attribute identically, whether it came from
 * a Wikidata statement or from guessing a person's gender out of the letters in
 * their name. Those are not the same kind of fact and must never look the same.
 *
 * This module answers two questions about any single attribute:
 *
 *   1. WHERE did it come from?   -> `PROVENANCE` (wikidata | mbfc | tld | heuristic | none)
 *   2. HOW MUCH is it worth?     -> `EVIDENCE`   (measured | estimated | absent)
 *
 * Everything here is a pure function over one backend object, so the rules are
 * unit-testable without mounting a component. No i18n: callers translate the
 * returned codes.
 */

import { isUnmapped } from "./labels.js";

/** Where an attribute's value came from. */
export const PROVENANCE = {
  /** A statement on a Wikidata item. Ground truth, and linkable. */
  WIKIDATA: "wikidata",
  /** A Media Bias/Fact Check rating. Third-party editorial judgement, linkable. */
  MBFC: "mbfc",
  /** Inferred from the domain's top-level domain (.fr -> France). */
  TLD: "tld",
  /** Inferred by the backend's own heuristics (name-origin, source-type rules). */
  HEURISTIC: "heuristic",
  /** Nothing was found. */
  NONE: "none",
};

/**
 * How strongly the value is supported.
 *
 * `MEASURED` means a named third party asserts it and we can link to that
 * assertion. `ESTIMATED` means *we* guessed it. `ABSENT` means we do not know —
 * which is emphatically not the same as a value of zero, and is the case v1
 * kept collapsing into "0%".
 */
export const EVIDENCE = {
  MEASURED: "measured",
  ESTIMATED: "estimated",
  ABSENT: "absent",
};

/** Provenance kinds that carry an outbound link the reader can check. */
export const LINKED_PROVENANCE = new Set([PROVENANCE.WIKIDATA, PROVENANCE.MBFC]);

export function wikidataUrl(id) {
  if (!id || typeof id !== "string") return null;
  if (!/^Q\d+$/i.test(id.trim())) return null;
  return `https://www.wikidata.org/wiki/${id.trim().toUpperCase()}`;
}

/**
 * Bucket keys that mean "we could not determine this".
 *
 * These must be split out of every distribution before it is charted: a corpus
 * that is 87.5% "unknown" political leaning has *not* measured a leaning for
 * 87.5% of its sources, and drawing "unknown" as the winning bar states the
 * opposite of what happened.
 */
export function isUnknownKey(key) {
  if (key == null) return true;
  const k = String(key).trim().toLowerCase();
  return k === "" || k === "unknown" || k === "unmapped" || isUnmapped(k);
}

const evidenceOf = (provenance) => {
  if (provenance === PROVENANCE.NONE) return EVIDENCE.ABSENT;
  return LINKED_PROVENANCE.has(provenance) ? EVIDENCE.MEASURED : EVIDENCE.ESTIMATED;
};

/**
 * Build one grading record.
 *
 * `evidence` is derived from `provenance` rather than passed in, so the two can
 * never drift apart: anything sourced from Wikidata or MBFC is measured, and
 * anything we inferred ourselves is estimated. There is exactly one place to
 * change that rule.
 */
function grade(value, provenance, extra = {}) {
  return {
    value: value ?? null,
    provenance,
    evidence: evidenceOf(provenance),
    ...extra,
  };
}

const absent = (extra = {}) => grade(null, PROVENANCE.NONE, extra);

const firstOf = (arr) => (Array.isArray(arr) && arr.length ? arr[0] : null);

/* ------------------------------------------------------------------ *
 * Per-source attributes
 * ------------------------------------------------------------------ */

/**
 * Where a source is published.
 *
 * The backend resolves a country either by matching the publisher in Wikidata
 * or by reading the TLD, and only the former is a fact about the publisher —
 * `lemonde.fr` being French is a real inference, but `.com` tells you nothing,
 * which is exactly what `geography.note.generic_tld` reports.
 */
export function geographyEvidence(source) {
  const geo = source?.geography || {};
  const note = geo.note || null;
  if (geo.unmapped || isUnmapped(geo.country)) {
    return absent({ note, region: null });
  }

  const country = geo.country;
  const region = geo.region && !isUnmapped(geo.region) ? geo.region : null;
  const publisher = source?.wikidata_publisher || {};
  const mbfc = source?.mbfc || {};

  if (Array.isArray(publisher.countries) && publisher.countries.includes(country)) {
    return grade(country, PROVENANCE.WIKIDATA, {
      region,
      note,
      ref: {
        id: publisher.wikidata_id || null,
        name: publisher.wikidata_name || null,
        url: wikidataUrl(publisher.wikidata_id),
      },
    });
  }

  if (mbfc.country && mbfc.country === country) {
    return grade(country, PROVENANCE.MBFC, {
      region,
      note,
      ref: { name: mbfc.media_type || null, url: mbfc.mbfc_url || null },
    });
  }

  // Nothing corroborated it, so this is the TLD reading. Keep it, but say so.
  return grade(country, PROVENANCE.TLD, { region, note, ref: null });
}

/**
 * A source's political leaning.
 *
 * Wikidata's `political_ideologies` / `political_leanings` are statements about
 * the publisher; MBFC's `bias_rating` is a published rating. Anything else is
 * the backend's own guess.
 */
export function leaningEvidence(source) {
  const lean = source?.political_leaning;
  const publisher = source?.wikidata_publisher || {};
  const mbfc = source?.mbfc || {};

  if (isUnknownKey(lean)) return absent();

  const wdLean =
    firstOf(publisher.political_leanings) || firstOf(publisher.political_ideologies);
  if (wdLean) {
    return grade(lean, PROVENANCE.WIKIDATA, {
      detail: wdLean,
      ref: {
        id: publisher.wikidata_id || null,
        name: publisher.wikidata_name || null,
        url: wikidataUrl(publisher.wikidata_id),
      },
    });
  }

  if (mbfc.bias_rating) {
    return grade(lean, PROVENANCE.MBFC, {
      detail: mbfc.bias_rating,
      ref: { name: mbfc.media_type || null, url: mbfc.mbfc_url || null },
    });
  }

  return grade(lean, PROVENANCE.HEURISTIC, { detail: null, ref: null });
}

/**
 * A source's reliability band.
 *
 * MBFC publishes credibility and factual-reporting ratings; without one, the
 * band is the backend's own rule over the source type, which is a heuristic.
 */
export function reliabilityEvidence(source) {
  const level = source?.reliability;
  if (isUnknownKey(level)) return absent();

  const mbfc = source?.mbfc || {};
  const rating = mbfc.credibility_rating || mbfc.factual_reporting;
  if (rating) {
    return grade(level, PROVENANCE.MBFC, {
      detail: rating,
      ref: { name: mbfc.media_type || null, url: mbfc.mbfc_url || null },
    });
  }

  return grade(level, PROVENANCE.HEURISTIC, { detail: source?.source_type || null, ref: null });
}

/* ------------------------------------------------------------------ *
 * Per-author attributes
 * ------------------------------------------------------------------ */

/**
 * An author's gender.
 *
 * This is the sharpest measured/estimated split in the whole payload.
 * `wikidata_author.gender` is a sourced statement about a named person.
 * `author_profiles[].gender` is the output of "estimated via first name and
 * surname linguistic origin heuristics" carrying `confidence.gender = 0.7` —
 * a guess from spelling. v1 fed the aggregate of the second into a "parity"
 * score and rendered it as a fact.
 *
 * The two also disagree in practice (see `genderDisagreements`), so Wikidata is
 * always preferred when present.
 */
export function authorGenderEvidence(profile) {
  const wd = profile?.wikidata_author || {};
  if (wd.gender && !isUnknownKey(wd.gender)) {
    return grade(String(wd.gender).toLowerCase(), PROVENANCE.WIKIDATA, {
      ref: {
        id: wd.wikidata_id || null,
        name: wd.wikidata_name || null,
        url: wikidataUrl(wd.wikidata_id),
      },
    });
  }

  const guess = profile?.gender;
  if (!isUnknownKey(guess)) {
    return grade(String(guess).toLowerCase(), PROVENANCE.HEURISTIC, {
      confidence: profile?.confidence?.gender ?? null,
      note: profile?.notes || null,
      ref: null,
    });
  }

  // The heuristic ran and produced "unknown": nothing is known, and the author
  // must not be counted into any gender bucket.
  return absent({ confidence: profile?.confidence?.gender ?? null, note: profile?.notes || null });
}

/** An author's nationality — Wikidata citizenship, else the name-origin guess. */
export function authorNationalityEvidence(profile) {
  const wd = profile?.wikidata_author || {};
  const citizenship = firstOf(wd.citizenships);
  if (citizenship && !isUnknownKey(citizenship)) {
    return grade(citizenship, PROVENANCE.WIKIDATA, {
      ref: {
        id: wd.wikidata_id || null,
        name: wd.wikidata_name || null,
        url: wikidataUrl(wd.wikidata_id),
      },
    });
  }

  // `nationality_probability` is a distribution; take the best non-unknown
  // guess and carry its probability so the UI can show how thin it is.
  const probs = profile?.nationality_probability || {};
  const best = Object.entries(probs)
    .filter(([k]) => !isUnknownKey(k))
    .sort((a, b) => (b[1] || 0) - (a[1] || 0))[0];
  if (best) {
    return grade(best[0], PROVENANCE.HEURISTIC, {
      confidence: best[1] ?? null,
      note: profile?.notes || null,
      ref: null,
    });
  }

  return absent({ note: profile?.notes || null });
}

/** True when an author has any Wikidata item at all (linkable, even if sparse). */
export function authorWikidataRef(profile) {
  const wd = profile?.wikidata_author || {};
  if (!wd.wikidata_id) return null;
  return { id: wd.wikidata_id, name: wd.wikidata_name || null, url: wikidataUrl(wd.wikidata_id) };
}

/** The publisher's Wikidata item, when the backend resolved one. */
export function publisherWikidataRef(source) {
  const wd = source?.wikidata_publisher || {};
  if (!wd.wikidata_id) return null;
  return { id: wd.wikidata_id, name: wd.wikidata_name || null, url: wikidataUrl(wd.wikidata_id) };
}

/** The MBFC record, when there is one. `{}` is how the backend says "none". */
export function mbfcRef(source) {
  const mbfc = source?.mbfc || {};
  if (!mbfc || !Object.keys(mbfc).length) return null;
  return {
    url: mbfc.mbfc_url || null,
    bias: mbfc.bias_rating || null,
    credibility: mbfc.credibility_rating || null,
    factual: mbfc.factual_reporting || null,
    mediaType: mbfc.media_type || null,
    country: mbfc.country || null,
  };
}
