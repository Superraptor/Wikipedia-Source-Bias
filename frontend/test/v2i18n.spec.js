import { describe, it, expect } from "vitest";
import { createI18n } from "vue-i18n";
import fr from "../i18n/locales/fr.json";
import en from "../i18n/locales/en.json";
import { EVIDENCE, PROVENANCE } from "../utils/provenance.js";
import { buildV2Model } from "../composables/useV2Data.js";

import frPayload from "./fixtures/analysis-fr.json";
import dePayload from "./fixtures/analysis-de.json";
import enPayload from "./fixtures/analysis-en.json";

function makeI18n(locale = "fr") {
  return createI18n({ legacy: false, locale, fallbackLocale: "fr", messages: { fr, en } });
}

function keyPaths(obj, prefix = "") {
  return Object.entries(obj).flatMap(([k, v]) => {
    const path = prefix ? `${prefix}.${k}` : k;
    return v && typeof v === "object" && !Array.isArray(v) ? keyPaths(v, path) : [path];
  });
}

describe("v2 catalogue", () => {
  it("exists in both locales with the same keys", () => {
    expect(fr.v2).toBeTruthy();
    expect(en.v2).toBeTruthy();
    expect(keyPaths(en.v2).sort()).toEqual(keyPaths(fr.v2).sort());
  });

  // vue-i18n reads `|` as a plural separator and `@` as a linked-message
  // marker, so either character silently mangles a sentence.
  it("avoids vue-i18n's control characters", () => {
    for (const [name, cat] of Object.entries({ fr: fr.v2, en: en.v2 })) {
      for (const path of keyPaths(cat)) {
        const value = String(path.split(".").reduce((o, k) => o[k], cat));
        expect(value, `${name}:v2.${path}`).not.toMatch(/[|@]/);
        expect(value.trim(), `${name}:v2.${path}`).not.toBe("");
      }
    }
  });

  it("covers every evidence grade and provenance kind", () => {
    for (const cat of [fr.v2, en.v2]) {
      for (const grade of Object.values(EVIDENCE)) {
        expect(cat.evidence[grade]).toBeTruthy();
        expect(cat.evidence[`${grade}Long`]).toBeTruthy();
      }
      for (const kind of Object.values(PROVENANCE)) {
        expect(cat.provenance[kind]).toBeTruthy();
        expect(cat.provenance[`${kind}Long`]).toBeTruthy();
      }
    }
  });

  it("has coverage wording for both units and all three states", () => {
    for (const cat of [fr.v2, en.v2]) {
      for (const state of ["none", "all", "partial"]) {
        for (const unit of ["sources", "authors"]) {
          expect(cat.coverage[state][unit], `${state}.${unit}`).toBeTruthy();
        }
      }
    }
  });

  it("has an empty-state sentence for both reasons a section can be unavailable", () => {
    for (const cat of [fr.v2, en.v2]) {
      expect(cat.chart.empty.missing).toBeTruthy();
      expect(cat.chart.empty.allUnknown).toBeTruthy();
    }
  });

  it("has a title for every derived indicator the model can emit", () => {
    // buildV2Model emits one concentration record per dimension; each needs a
    // name and a reading sentence, or the panel renders a raw key path.
    const dimensions = new Set(
      [frPayload, dePayload, enPayload].flatMap((p) => buildV2Model(p).derived.map((d) => d.dimension)),
    );
    for (const cat of [fr.v2, en.v2]) {
      for (const d of dimensions) {
        expect(cat.derived.metric[d], d).toBeTruthy();
        expect(cat.derived.reading[d], d).toBeTruthy();
      }
    }
  });

  it("renders the coverage sentences with real numbers in both languages", () => {
    const i18n = makeI18n("fr");
    const t = i18n.global.t;
    expect(t("v2.coverage.partial.sources", { known: 6, total: 8, pct: 75 })).toContain("6 des 8");
    i18n.global.locale.value = "en";
    expect(t("v2.coverage.partial.sources", { known: 6, total: 8, pct: 75 })).toBe(
      "Based on 6 of 8 sources (75%)",
    );
  });

  it("renders the gender disagreement sentences with their placeholders filled", () => {
    const i18n = makeI18n("en");
    const t = i18n.global.t;
    const missed = t("v2.gender.disagree.missed", { measured: "Man", estimated: "—", confidence: 70 });
    expect(missed).toContain("70%");
    expect(missed).toContain("Man");
    expect(missed).not.toContain("{");
  });
});

describe("v2 vocabularies vs the real payloads", () => {
  it("has wording for every source_type the fixtures contain", () => {
    const types = new Set(
      [frPayload, dePayload, enPayload].flatMap((p) => p.sources.map((s) => s.source_type).filter(Boolean)),
    );
    for (const cat of [fr.v2, en.v2]) {
      for (const type of types) expect(cat.sourceType[type], type).toBeTruthy();
    }
  });

  it("has wording for every author_type bucket the backend aggregates", () => {
    const types = new Set(
      [frPayload, dePayload, enPayload].flatMap((p) =>
        Object.keys(p.aggregated_bias.author_type_distribution || {}),
      ),
    );
    for (const cat of [fr.v2, en.v2]) {
      for (const type of types) expect(cat.authorType[type], type).toBeTruthy();
    }
  });

  it("has wording for every gender value that appears in the fixtures", () => {
    const values = new Set();
    for (const p of [frPayload, dePayload, enPayload]) {
      for (const s of p.sources) {
        for (const a of s.author_profiles || []) {
          if (a.gender) values.add(String(a.gender).toLowerCase());
          if (a.wikidata_author?.gender) values.add(String(a.wikidata_author.gender).toLowerCase());
        }
      }
    }
    for (const cat of [fr.v2, en.v2]) {
      for (const v of values) expect(cat.gender.value[v], v).toBeTruthy();
    }
  });
});
