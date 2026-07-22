/**
 * Translation of the API's *data* vocabulary.
 *
 * The backend emits language-neutral keys ("unmapped", "high", "generic_tld").
 * Everything that turns one of those into a sentence lives here, as plain
 * functions taking the vue-i18n `t`, so the mapping is unit-testable without
 * mounting a component.
 */

/** The language-neutral marker emitted by backend/analyzer.py. */
export const UNMAPPED = "unmapped";

// Analyses produced before the backend switched to a neutral key are still in
// the cache (and in backend/mock.py), so the old French display string and the
// analyzer's raw "Unknown" both have to keep resolving to "unmapped".
const UNMAPPED_ALIASES = new Set(["unmapped", "non-mappé", "non-mappe", "unknown", ""]);

/** True when a country/region value means "we could not place this source". */
export function isUnmapped(value) {
  if (value == null) return true;
  return UNMAPPED_ALIASES.has(String(value).trim().toLowerCase());
}

/**
 * Country names come from Wikidata in English and are proper nouns, so they
 * are passed through untouched; only the "unmapped" marker is translated.
 */
export function countryLabel(value, t) {
  if (isUnmapped(value)) return t("geography.unmapped");
  return value;
}

/** Region buckets are a closed set, so they are fully translated. */
export function regionLabel(region, t) {
  if (isUnmapped(region)) return t("region.unmapped");
  return t(`region.${region}`);
}

// Several analyzer vocabularies collapse onto the same badge. Keeping the
// collapse here (rather than in the locale files) avoids duplicating
// "conservatism -> Droite/Right" in every language.
const LEAN_KEYS = {
  left: "left",
  center: "center",
  right: "right",
  conservatism: "right",
  progressivism: "left",
  neutral: "neutral",
  "neutral/academic": "neutral",
  academic: "academic",
  unknown: "unknown",
};

const LEAN_CLASSES = {
  left: "lean lean--left",
  center: "lean lean--center",
  right: "lean lean--right",
  neutral: "lean lean--neutral",
  academic: "lean lean--neutral",
  unknown: "lean lean--unknown",
};

const RELIABILITY_KEYS = ["academic", "high", "medium", "low", "unknown"];

const RELIABILITY_CLASSES = {
  academic: "rel rel--academic",
  high: "rel rel--high",
  medium: "rel rel--medium",
  low: "rel rel--low",
  unknown: "rel rel--unknown",
};

/** `{ label, cls }` for a political lean badge; unknown values pass through. */
export function leanBadge(lean, t) {
  const key = LEAN_KEYS[lean];
  if (!key) return { label: lean || t("app.empty"), cls: LEAN_CLASSES.unknown };
  return { label: t(`lean.${key}`), cls: LEAN_CLASSES[key] };
}

/** `{ label, cls }` for a reliability badge; unknown values pass through. */
export function reliabilityBadge(level, t) {
  if (!RELIABILITY_KEYS.includes(level)) {
    return { label: level || t("app.empty"), cls: RELIABILITY_CLASSES.unknown };
  }
  return { label: t(`reliability.${level}`), cls: RELIABILITY_CLASSES[level] };
}

/** Just the wording of a reliability level, for the sidebar. */
export function reliabilityLabel(level, t) {
  return reliabilityBadge(level, t).label;
}

/**
 * Renders `geography.note` — `{ code, params }` since the backend stopped
 * emitting a French sentence. Pre-i18n payloads carry a plain string, which is
 * shown as-is rather than dropped.
 */
export function geographyNote(note, t) {
  if (!note) return "";
  if (typeof note === "string") return note;
  if (!note.code) return "";
  return t(`geography.note.${note.code}`, note.params || {});
}

/** The radar axes, in display order. Labels live in `radar.axis.*`. */
export const RADAR_AXES = [
  "geo_diversity",
  "political_pluralism",
  "author_parity",
  "neutrality",
  "reliability",
];
