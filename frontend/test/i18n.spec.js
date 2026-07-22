import { describe, it, expect, beforeEach } from "vitest";
import { createI18n } from "vue-i18n";
import fr from "../i18n/locales/fr.json";
import en from "../i18n/locales/en.json";
import {
  countryLabel,
  geographyNote,
  isUnmapped,
  leanBadge,
  regionLabel,
  reliabilityBadge,
  reliabilityLabel,
  RADAR_AXES,
  UNMAPPED,
} from "../utils/labels.js";

// The same vue-i18n instance the app builds, wired to the real catalogues, so
// these assertions fail if a key is renamed in a component but not in the JSON.
function makeI18n(locale = "fr") {
  return createI18n({
    legacy: false,
    locale,
    fallbackLocale: "fr",
    messages: { fr, en },
  });
}

function keyPaths(obj, prefix = "") {
  return Object.entries(obj).flatMap(([k, v]) => {
    const path = prefix ? `${prefix}.${k}` : k;
    return v && typeof v === "object" && !Array.isArray(v) ? keyPaths(v, path) : [path];
  });
}

describe("locale catalogues", () => {
  it("fr and en define exactly the same keys", () => {
    const frKeys = keyPaths(fr).sort();
    const enKeys = keyPaths(en).sort();
    expect(enKeys).toEqual(frKeys);
  });

  it("has no empty translation", () => {
    for (const [name, cat] of Object.entries({ fr, en })) {
      for (const path of keyPaths(cat)) {
        const value = path.split(".").reduce((o, k) => o[k], cat);
        expect(String(value).trim(), `${name}:${path}`).not.toBe("");
      }
    }
  });

  // Interpolation placeholders are part of the contract with the components:
  // a translator dropping {pct} silently produces a sentence missing its number.
  it("keeps the same interpolation placeholders in both locales", () => {
    const placeholders = (s) => (String(s).match(/\{\w+\}/g) || []).sort();
    for (const path of keyPaths(fr)) {
      const frValue = path.split(".").reduce((o, k) => o[k], fr);
      const enValue = path.split(".").reduce((o, k) => o[k], en);
      expect(placeholders(enValue), path).toEqual(placeholders(frValue));
    }
  });

  it("covers every radar axis in both locales", () => {
    for (const cat of [fr, en]) {
      for (const axis of RADAR_AXES) {
        expect(cat.radar.axis[axis]).toBeTruthy();
        expect(cat.radar.axisLong[axis]).toBeTruthy();
      }
    }
  });

  // The backend's reason codes (backend/analyzer.py) are the other half of this
  // contract; an unknown code would render as a raw key in the tooltip.
  it("has a sentence for every backend geography note code", () => {
    for (const cat of [fr, en]) {
      expect(Object.keys(cat.geography.note).sort()).toEqual([
        "generic_tld",
        "no_country_signal",
        "region_missing",
      ]);
    }
  });
});

describe("locale switching", () => {
  let i18n;
  beforeEach(() => {
    i18n = makeI18n("fr");
  });

  it("renders French by default and English once the locale changes", () => {
    const t = i18n.global.t;
    expect(t("header.queue")).toBe("File d'analyse");
    i18n.global.locale.value = "en";
    expect(t("header.queue")).toBe("Analysis queue");
  });

  it("interpolates counts and percentages in both locales", () => {
    const t = i18n.global.t;
    expect(t("kpi.dominantHint", { pct: 84.7 })).toContain("84.7");
    i18n.global.locale.value = "en";
    expect(t("kpi.dominantHint", { pct: 84.7 })).toBe("84.7% of sources");
  });

  it("pluralises the unmapped-sources notice", () => {
    const t = i18n.global.t;
    expect(t("dashboard.unmappedNotice", { count: 1, pct: 0.4 }, 1)).toContain(
      "1 source non-mappée",
    );
    expect(t("dashboard.unmappedNotice", { count: 78, pct: 8.9 }, 78)).toContain(
      "78 sources non-mappées",
    );
    i18n.global.locale.value = "en";
    expect(t("dashboard.unmappedNotice", { count: 1, pct: 0.4 }, 1)).toContain(
      "1 unmapped source (",
    );
    expect(t("dashboard.unmappedNotice", { count: 78, pct: 8.9 }, 78)).toContain(
      "78 unmapped sources",
    );
  });

  it("falls back to French when a key is missing from English", () => {
    const partial = createI18n({
      legacy: false,
      locale: "en",
      fallbackLocale: "fr",
      messages: { fr, en: { header: {} } },
    });
    expect(partial.global.t("header.queue")).toBe("File d'analyse");
  });
});

describe("data vocabulary translation", () => {
  const t = makeI18n("fr").global.t;
  const tEn = makeI18n("en").global.t;

  it("recognises every spelling of an unmapped country", () => {
    // "unmapped" is what the backend emits today; the others are cached or
    // mock payloads produced before the key became language-neutral.
    for (const v of [UNMAPPED, "Non-mappé", "unknown", "Unknown", "", null, undefined]) {
      expect(isUnmapped(v), String(v)).toBe(true);
    }
    expect(isUnmapped("France")).toBe(false);
  });

  it("translates the unmapped marker but leaves real country names alone", () => {
    expect(countryLabel("unmapped", t)).toBe("Non-mappé");
    expect(countryLabel("unmapped", tEn)).toBe("Unmapped");
    expect(countryLabel("United Kingdom", tEn)).toBe("United Kingdom");
    expect(countryLabel("United Kingdom", t)).toBe("United Kingdom");
  });

  it("translates region buckets", () => {
    expect(regionLabel("Americas", t)).toBe("Amériques");
    expect(regionLabel("Americas", tEn)).toBe("Americas");
    expect(regionLabel(UNMAPPED, tEn)).toBe("Unmapped");
  });

  it("maps the analyzer's lean vocabularies onto translated badges", () => {
    expect(leanBadge("conservatism", t)).toEqual({ label: "Droite", cls: "lean lean--right" });
    expect(leanBadge("conservatism", tEn).label).toBe("Right");
    expect(leanBadge("progressivism", tEn).label).toBe("Left");
    expect(leanBadge("neutral/academic", tEn).label).toBe("Neutral");
    // An unforeseen value must still be displayed, not swallowed.
    expect(leanBadge("libertarian", tEn)).toEqual({
      label: "libertarian",
      cls: "lean lean--unknown",
    });
    expect(leanBadge(undefined, tEn).label).toBe("—");
  });

  it("translates reliability levels", () => {
    expect(reliabilityBadge("high", t)).toEqual({ label: "Élevée", cls: "rel rel--high" });
    expect(reliabilityBadge("high", tEn).label).toBe("High");
    expect(reliabilityLabel("academic", tEn)).toBe("Academic");
    expect(reliabilityBadge("weird", tEn)).toEqual({ label: "weird", cls: "rel rel--unknown" });
  });

  it("renders the backend's structured geography note in either language", () => {
    const note = { code: "generic_tld", params: { tld: ".net" } };
    expect(geographyNote(note, t)).toContain("(.net)");
    expect(geographyNote(note, t)).toContain("Domaine générique");
    expect(geographyNote(note, tEn)).toBe(
      "Generic domain (.net): the TLD carries no country signal, and no publisher match was found in Wikidata or in the domain database.",
    );
    expect(geographyNote({ code: "region_missing", params: { country: "Kiribati" } }, tEn)).toContain(
      "Kiribati",
    );
    expect(geographyNote(null, tEn)).toBe("");
  });

  it("still shows the plain-string note of a pre-i18n cached payload", () => {
    expect(geographyNote("Domaine générique (.net) : …", tEn)).toBe("Domaine générique (.net) : …");
  });
});
