import { describe, it, expect } from "vitest";
import { computeRadarAxes } from "../composables/useRadarData.js";

describe("computeRadarAxes", () => {
  it("diversity = 100 - dominant country percentage", () => {
    const agg = { geography_distribution: { France: { count: 746, percentage: 84.7 } } };
    const axes = computeRadarAxes({ aggregated_bias: agg });
    expect(axes.geo_diversity).toBeCloseTo(15.3, 1);
  });

  it("pluralism is normalized entropy excluding unknown leans", () => {
    const agg = {
      political_leaning_distribution: {
        left: { count: 50, percentage: 50 },
        center: { count: 30, percentage: 30 },
        right: { count: 20, percentage: 20 },
        unknown: { count: 100, percentage: 100 },
      },
    };
    const axes = computeRadarAxes({ aggregated_bias: agg });
    expect(axes.political_pluralism).toBeGreaterThan(90);
    expect(axes.political_pluralism).toBeLessThanOrEqual(100);
  });

  it("pluralism is low for echo chamber (single lean)", () => {
    const agg = {
      political_leaning_distribution: {
        left: { count: 100, percentage: 100 },
        unknown: { count: 0, percentage: 0 },
      },
    };
    const axes = computeRadarAxes({ aggregated_bias: agg });
    expect(axes.political_pluralism).toBeLessThan(5);
  });

  it("author parity = min(%H, %F) * 2", () => {
    const agg = {
      author_gender_distribution: {
        male: { count: 65, percentage: 65 },
        female: { count: 25, percentage: 25 },
      },
    };
    const axes = computeRadarAxes({ aggregated_bias: agg });
    expect(axes.author_parity).toBe(50);
  });

  it("neutrality = (1 - subjectivity) * 100", () => {
    const agg = { average_subjectivity_score: 0.18 };
    const axes = computeRadarAxes({ aggregated_bias: agg });
    expect(axes.neutrality).toBeCloseTo(82, 0);
  });

  it("reliability is weighted average", () => {
    const agg = {
      reliability_distribution: {
        academic: { count: 15, percentage: 15 },
        high: { count: 25, percentage: 25 },
        medium: { count: 50, percentage: 50 },
        low: { count: 0, percentage: 0 },
        unknown: { count: 10, percentage: 10 },
      },
    };
    const axes = computeRadarAxes({ aggregated_bias: agg });
    // (15*100 + 25*80 + 50*50 + 0*20 + 10*0) / 100 = 6000/100 = 60
    expect(axes.reliability).toBe(60);
  });

  it("returns all 5 axes with labels", () => {
    const axes = computeRadarAxes({ aggregated_bias: {} });
    expect(axes).toHaveProperty("geo_diversity");
    expect(axes).toHaveProperty("political_pluralism");
    expect(axes).toHaveProperty("author_parity");
    expect(axes).toHaveProperty("neutrality");
    expect(axes).toHaveProperty("reliability");
  });
});

describe("empty analyses", () => {
  it("scores every axis 0 when there are no references", () => {
    // Regression: neutrality is (1 - subjectivity), and a missing score read
    // as 0, so an article with no sources rendered a perfect 100% neutrality.
    const axes = computeRadarAxes({ source_count: 0, sources: [], aggregated_bias: {} });
    for (const [name, value] of Object.entries(axes)) {
      expect(value, name).toBe(0);
    }
  });

  it("scores 0 when aggregated_bias is missing entirely", () => {
    const axes = computeRadarAxes({ source_count: 0 });
    expect(Object.values(axes).every((v) => v === 0)).toBe(true);
  });

  it("still reports neutrality for a real analysis", () => {
    const axes = computeRadarAxes({
      source_count: 3,
      aggregated_bias: { average_subjectivity_score: 0.25 },
    });
    expect(axes.neutrality).toBe(75);
  });
});
