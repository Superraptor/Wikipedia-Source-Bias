import { describe, it, expect } from "vitest";
import { detectImbalance } from "../composables/useImbalance.js";

const fr = "https://fr.wikipedia.org/wiki/X";
const en = "https://en.wikipedia.org/wiki/X";

function make(page_url, agg, source_count = 10) {
  return { page_url, source_count, aggregated_bias: agg };
}

describe("detectImbalance (conservative)", () => {
  it("does NOT flag a French subject with French sources", () => {
    // The user's key case: French person, French sources = normal.
    const { findings } = detectImbalance(make(fr, {
      geography_distribution: { France: { count: 8, percentage: 100 } },
      language_distribution: { French: { count: 8, percentage: 100 } },
    }, 8));
    expect(findings).toEqual([]);
  });

  it("does NOT flag single-country concentration on its own", () => {
    // Raw concentration is deliberately not a trigger: it cannot tell an
    // expected national focus from a real imbalance without the subject's country.
    const { findings } = detectImbalance(make(fr, {
      geography_distribution: { France: { count: 9, percentage: 90 }, Germany: { count: 1, percentage: 10 } },
      language_distribution: { French: { count: 9, percentage: 90 }, German: { count: 1, percentage: 10 } },
    }));
    expect(findings).toEqual([]);
  });

  it("flags a French article sourced overwhelmingly in English", () => {
    const { findings } = detectImbalance(make(fr, {
      language_distribution: { English: { count: 8, percentage: 80 }, French: { count: 2, percentage: 20 } },
    }));
    const lang = findings.find((f) => f.dimension === "language");
    expect(lang.key).toBe("English");
    expect(lang.pct).toBe(80);
    expect(lang.edition).toBe("French");
  });

  it("does NOT flag an English article sourced in English", () => {
    const { findings } = detectImbalance(make(en, {
      language_distribution: { English: { count: 10, percentage: 100 } },
    }));
    expect(findings.find((f) => f.dimension === "language")).toBeUndefined();
  });

  it("raises a coverage caveat when many sources are unplaceable", () => {
    const { findings } = detectImbalance(make(fr, {
      geography_distribution: { France: { count: 5, percentage: 50 }, unmapped: { count: 5, percentage: 50 } },
      language_distribution: { French: { count: 10, percentage: 100 } },
    }));
    expect(findings[0].severity).toBe("coverage");
    expect(findings[0].pct).toBe(50);
  });

  it("stays silent on a tiny corpus", () => {
    const { findings } = detectImbalance(make(fr, {
      language_distribution: { English: { count: 2, percentage: 100 } },
    }, 2));
    expect(findings).toEqual([]);
  });

  it("orders coverage before language", () => {
    const { findings } = detectImbalance(make(fr, {
      geography_distribution: { France: { count: 3, percentage: 30 }, unmapped: { count: 7, percentage: 70 } },
      language_distribution: { English: { count: 9, percentage: 90 }, French: { count: 1, percentage: 10 } },
    }));
    expect(findings[0].severity).toBe("coverage");
    expect(findings[1].dimension).toBe("language");
  });
});
