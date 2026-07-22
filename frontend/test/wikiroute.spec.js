import { describe, it, expect } from "vitest";
import { parseWikipediaUrl, wikipediaUrl, routeForUrl, routeFor } from "../utils/wikiroute.js";

describe("parseWikipediaUrl", () => {
  it("parses a standard article URL", () => {
    expect(parseWikipediaUrl("https://en.wikipedia.org/wiki/Brexit"))
      .toEqual({ lang: "en", title: "Brexit" });
  });

  it("decodes percent-encoded titles", () => {
    expect(parseWikipediaUrl("https://fr.wikipedia.org/wiki/Guerre_d%27Alg%C3%A9rie"))
      .toEqual({ lang: "fr", title: "Guerre_d'Algérie" });
  });

  it("ignores tracking query strings", () => {
    expect(parseWikipediaUrl("https://fr.wikipedia.org/wiki/Le_M%C3%A9dia?wprov=sfla1"))
      .toEqual({ lang: "fr", title: "Le_Média" });
  });

  it("handles the mobile host", () => {
    expect(parseWikipediaUrl("https://de.m.wikipedia.org/wiki/Berlin").lang).toBe("de");
  });

  it("rejects non-Wikipedia and malformed URLs", () => {
    expect(parseWikipediaUrl("https://example.org/wiki/Brexit")).toBeNull();
    expect(parseWikipediaUrl("https://en.wikipedia.org/w/index.php?title=X")).toBeNull();
    expect(parseWikipediaUrl("not a url")).toBeNull();
    expect(parseWikipediaUrl("")).toBeNull();
    expect(parseWikipediaUrl(null)).toBeNull();
  });
});

describe("routeForUrl", () => {
  it("produces the wikipedia-shaped route", () => {
    expect(routeForUrl("https://en.wikipedia.org/wiki/Brexit")).toBe("/wikipedia/en/Brexit");
  });

  it("drops the query string from the route", () => {
    expect(routeForUrl("https://fr.wikipedia.org/wiki/Brexit?wprov=sfla1"))
      .toBe("/wikipedia/fr/Brexit");
  });

  it("falls back to ?src= for non-Wikipedia sources", () => {
    const r = routeForUrl("https://example.org/page");
    expect(r.startsWith("/article/")).toBe(true);
    expect(r).toContain("src=https%3A%2F%2Fexample.org%2Fpage");
  });
});

describe("wikipediaUrl", () => {
  it("round-trips through parse", () => {
    const url = wikipediaUrl("fr", "Guerre_d'Algérie");
    expect(parseWikipediaUrl(url)).toEqual({ lang: "fr", title: "Guerre_d'Algérie" });
  });

  it("carries no query string", () => {
    expect(wikipediaUrl("en", "Brexit")).toBe("https://en.wikipedia.org/wiki/Brexit");
  });
});

describe("routeFor", () => {
  it("encodes titles safely", () => {
    expect(routeFor("fr", "Guerre d'Algérie")).toBe("/wikipedia/fr/Guerre%20d'Alg%C3%A9rie");
  });
});
