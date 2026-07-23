import { isUnmapped } from "../utils/labels.js";

/**
 * Flag genuine imbalance in a source corpus -- and NOT the concentration that
 * simply matches the subject.
 *
 * The hard case, and why this is deliberately conservative:
 *   A French person cited by French sources is NORMAL. An African person cited
 *   only by French sources is the real concern. Raw concentration cannot tell
 *   them apart -- both are "90% one country". Distinguishing them needs the
 *   SUBJECT's own country (from its Wikidata entity), which the pipeline does
 *   not yet fetch. The backend's diversity score can't either: it infers the
 *   subject's country FROM the sources, which is circular.
 *
 * So this flags only what is unambiguous from the payload alone, with no false
 * positives:
 *   1. Coverage -- a large share of sources could not be placed, so the
 *      geographic picture rests on the rest.
 *   2. Cross-language dependence -- the sources are overwhelmingly in a
 *      language OTHER than the article's own edition (e.g. a French article
 *      sourced almost entirely in English). That is observable and meaningful,
 *      and it stays silent when a French article cites French sources.
 *
 * Single-country concentration is intentionally NOT flagged until the subject's
 * own country is available; see PROPOSAL in the notice and METHODOLOGY.
 */

const UNRELIABLE_UNMAPPED = 40;   // % unplaceable above which coverage is caveated
const CROSS_LANG = 70;            // % of sources in a non-edition language
const MIN_SOURCES = 4;            // below this, percentages are noise

// fr.wikipedia.org -> "French", en -> "English", ... matched against the
// language values the analyzer emits.
const EDITION_LANGUAGE = {
  fr: "French", en: "English", de: "German", es: "Spanish", it: "Italian",
  pt: "Portuguese", nl: "Dutch", ru: "Russian", ja: "Japanese", zh: "Chinese",
  ar: "Arabic", ms: "Malay", pl: "Polish", sv: "Swedish", uk: "Ukrainian",
};

function editionLanguage(pageUrl) {
  const m = (pageUrl || "").match(/^https?:\/\/([a-z-]+)\.(?:m\.)?wikipedia\.org/i);
  return m ? EDITION_LANGUAGE[m[1].toLowerCase()] || null : null;
}

function unmappedShare(dist) {
  if (!dist) return 0;
  let unknown = 0, total = 0;
  for (const [k, v] of Object.entries(dist)) {
    if (!v || typeof v.count !== "number") continue;
    total += v.count;
    if (isUnmapped(k) || k.toLowerCase() === "unknown") unknown += v.count;
  }
  return total ? Math.round((unknown / total) * 100) : 0;
}

export function detectImbalance(analysis) {
  const agg = analysis?.aggregated_bias || {};
  const sourceCount = analysis?.source_count ?? analysis?.sources?.length ?? 0;
  const findings = [];

  if (sourceCount < MIN_SOURCES) return { sourceCount, findings };

  const geoUnmapped = unmappedShare(agg.geography_distribution);
  if (geoUnmapped >= UNRELIABLE_UNMAPPED) {
    findings.push({ dimension: "coverage", severity: "coverage", pct: geoUnmapped });
  }

  // Cross-language dependence: dominant source language vs the edition's own.
  const edition = editionLanguage(analysis?.page_url);
  const langs = agg.language_distribution || {};
  const total = Object.values(langs).reduce((a, v) => a + (v?.count || 0), 0);
  if (edition && total >= MIN_SOURCES) {
    let top = null;
    for (const [k, v] of Object.entries(langs)) {
      if (!v || typeof v.count !== "number") continue;
      if (!top || v.count > top.count) top = { key: k, count: v.count };
    }
    if (top && top.key !== edition) {
      const pct = Math.round((top.count / total) * 100);
      if (pct >= CROSS_LANG) {
        findings.push({ dimension: "language", severity: "notable", key: top.key, pct, edition });
      }
    }
  }

  const rank = { coverage: 2, notable: 1 };
  findings.sort((a, b) => (rank[b.severity] || 0) - (rank[a.severity] || 0));
  return { sourceCount, findings };
}
