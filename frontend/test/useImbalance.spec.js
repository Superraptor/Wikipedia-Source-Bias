import { describe, it, expect } from "vitest";
import { detectImbalance } from "../composables/useImbalance.js";

function analysis(dists, sourceCount = 10) {
  return { source_count: sourceCount, aggregated_bias: dists };
}

const geo = (m) => ({ geography_distribution: m });

describe("detectImbalance", () => {
  it("says nothing for a balanced corpus", () => {
    const { findings } = detectImbalance(analysis(geo({
      France: { count: 3, percentage: 30 },
      "United States": { count: 3, percentage: 30 },
      Germany: { count: 2, percentage: 20 },
      Japan: { count: 2, percentage: 20 },
    })));
    expect(findings).toEqual([]);
  });

  it("flags strong single-country concentration", () => {
    const { findings } = detectImbalance(analysis(geo({
      France: { count: 9, percentage: 90 },
      Germany: { count: 1, percentage: 10 },
    })));
    const geoF = findings.find((f) => f.dimension === "geography");
    expect(geoF.severity).toBe("strong");
    expect(geoF.pct).toBe(90);
    expect(geoF.key).toBe("France");
  });

  it("measures dominance among PLACED sources, ignoring unmapped", () => {
    // 5 France, 1 US, 4 unmapped: among placed, France is 5/6 = 83% -> notable.
    const { findings } = detectImbalance(analysis(geo({
      France: { count: 5, percentage: 50 },
      "United States": { count: 1, percentage: 10 },
      unmapped: { count: 4, percentage: 40 },
    })));
    const geoF = findings.find((f) => f.dimension === "geography");
    expect(geoF.pct).toBe(83);
    // And the 40% unmapped raises a separate coverage caveat, ranked first.
    expect(findings[0].severity).toBe("coverage");
  });

  it("does not flag concentration on a tiny corpus", () => {
    // 2 of 2 France is 100% but 2 sources is noise, not signal.
    const { findings } = detectImbalance(analysis(geo({
      France: { count: 2, percentage: 100 },
    }), 2));
    expect(findings.find((f) => f.dimension === "geography")).toBeUndefined();
  });

  it("raises a coverage caveat when many sources are unplaceable", () => {
    const { findings } = detectImbalance(analysis(geo({
      France: { count: 5, percentage: 50 },
      unmapped: { count: 5, percentage: 50 },
    })));
    expect(findings[0].severity).toBe("coverage");
    expect(findings[0].pct).toBe(50);
  });

  it("flags language and region too", () => {
    const { findings } = detectImbalance(analysis({
      region_distribution: { Europe: { count: 9, percentage: 90 }, Asia: { count: 1, percentage: 10 } },
      language_distribution: { French: { count: 10, percentage: 100 } },
    }));
    expect(findings.some((f) => f.dimension === "region" && f.severity === "strong")).toBe(true);
    expect(findings.some((f) => f.dimension === "language" && f.severity === "strong")).toBe(true);
  });

  it("orders coverage first, then strong, then notable", () => {
    const { findings } = detectImbalance(analysis({
      geography_distribution: {
        France: { count: 5, percentage: 50 },
        unmapped: { count: 5, percentage: 50 },
      },
      region_distribution: { Europe: { count: 5, percentage: 100 } },
    }));
    expect(findings[0].severity).toBe("coverage");
  });
});
