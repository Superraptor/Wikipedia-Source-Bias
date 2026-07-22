import { describe, it, expect } from "vitest";
import {
  EVIDENCE,
  PROVENANCE,
  authorGenderEvidence,
  authorNationalityEvidence,
  geographyEvidence,
  isUnknownKey,
  leaningEvidence,
  mbfcRef,
  publisherWikidataRef,
  reliabilityEvidence,
  wikidataUrl,
} from "../utils/provenance.js";

import fr from "./fixtures/analysis-fr.json";
import de from "./fixtures/analysis-de.json";
import en from "./fixtures/analysis-en.json";

/** Find the first source in a fixture matching a predicate. */
const find = (payload, pred) => payload.sources.find(pred);

describe("wikidataUrl", () => {
  it("builds a checkable link from a Q-id", () => {
    expect(wikidataUrl("Q259317")).toBe("https://www.wikidata.org/wiki/Q259317");
    expect(wikidataUrl("q259317")).toBe("https://www.wikidata.org/wiki/Q259317");
  });

  // A malformed id must not produce a link that 404s and looks like evidence.
  it("refuses anything that is not a Q-id", () => {
    for (const bad of [null, undefined, "", "  ", "P31", "Q", "not-an-id", 42]) {
      expect(wikidataUrl(bad), String(bad)).toBeNull();
    }
  });
});

describe("isUnknownKey", () => {
  it("recognises every spelling of an undetermined bucket", () => {
    for (const v of ["unknown", "Unknown", "unmapped", "Non-mappé", "", null, undefined]) {
      expect(isUnknownKey(v), String(v)).toBe(true);
    }
    expect(isUnknownKey("France")).toBe(false);
    expect(isUnknownKey("center-right")).toBe(false);
  });
});

describe("geographyEvidence", () => {
  it("grades a Wikidata-corroborated country as measured and links the item", () => {
    // duden.de: geography.country === "Germany" and wikidata_publisher.countries
    // contains "Germany", so the country is backed by a publisher statement.
    const s = find(de, (x) => x.domain === "duden.de");
    const ev = geographyEvidence(s);
    expect(ev.value).toBe("Germany");
    expect(ev.provenance).toBe(PROVENANCE.WIKIDATA);
    expect(ev.evidence).toBe(EVIDENCE.MEASURED);
    expect(ev.ref.url).toBe("https://www.wikidata.org/wiki/Q73624591");
  });

  it("grades an uncorroborated country as a TLD estimate, not a fact", () => {
    const s = {
      geography: { country: "France", region: "Europe" },
      wikidata_publisher: {},
      mbfc: {},
    };
    const ev = geographyEvidence(s);
    expect(ev.value).toBe("France");
    expect(ev.provenance).toBe(PROVENANCE.TLD);
    expect(ev.evidence).toBe(EVIDENCE.ESTIMATED);
    expect(ev.ref).toBeNull();
  });

  it("uses MBFC as corroboration when Wikidata has no country", () => {
    const s = {
      geography: { country: "France" },
      wikidata_publisher: { countries: [] },
      mbfc: { country: "France", mbfc_url: "https://mediabiasfactcheck.com/marianne/" },
    };
    const ev = geographyEvidence(s);
    expect(ev.provenance).toBe(PROVENANCE.MBFC);
    expect(ev.evidence).toBe(EVIDENCE.MEASURED);
    expect(ev.ref.url).toContain("mediabiasfactcheck.com");
  });

  it("reports an unmapped source as absent and keeps the backend's reason", () => {
    // The English fixture contains a `.com` source the backend explicitly
    // marked unmapped with a `generic_tld` note.
    const s = find(en, (x) => x.geography?.unmapped);
    expect(s, "fixture should contain an unmapped source").toBeTruthy();
    const ev = geographyEvidence(s);
    expect(ev.value).toBeNull();
    expect(ev.evidence).toBe(EVIDENCE.ABSENT);
    expect(ev.provenance).toBe(PROVENANCE.NONE);
    // The reason survives, because it is the useful thing on an empty row.
    expect(ev.note.code).toBe("generic_tld");
  });
});

describe("leaningEvidence", () => {
  it("treats 'unknown' as absent rather than as a leaning called unknown", () => {
    const ev = leaningEvidence({ political_leaning: "unknown" });
    expect(ev.evidence).toBe(EVIDENCE.ABSENT);
    expect(ev.value).toBeNull();
  });

  it("prefers a Wikidata ideology statement and links it", () => {
    const ev = leaningEvidence({
      political_leaning: "conservatism",
      wikidata_publisher: {
        wikidata_id: "Q11109",
        wikidata_name: "Die Welt",
        political_ideologies: ["conservatism"],
      },
    });
    expect(ev.provenance).toBe(PROVENANCE.WIKIDATA);
    expect(ev.evidence).toBe(EVIDENCE.MEASURED);
    expect(ev.ref.url).toBe("https://www.wikidata.org/wiki/Q11109");
  });

  it("falls back to an MBFC bias rating", () => {
    const ev = leaningEvidence({
      political_leaning: "center-right",
      wikidata_publisher: {},
      mbfc: { bias_rating: "RIGHT-CENTER (3.6)", mbfc_url: "https://mediabiasfactcheck.com/die-welt/" },
    });
    expect(ev.provenance).toBe(PROVENANCE.MBFC);
    expect(ev.detail).toBe("RIGHT-CENTER (3.6)");
  });

  it("marks an unsourced leaning as estimated", () => {
    const ev = leaningEvidence({ political_leaning: "center", wikidata_publisher: {}, mbfc: {} });
    expect(ev.provenance).toBe(PROVENANCE.HEURISTIC);
    expect(ev.evidence).toBe(EVIDENCE.ESTIMATED);
  });
});

describe("reliabilityEvidence", () => {
  it("is measured only when MBFC actually rated the outlet", () => {
    const rated = reliabilityEvidence({
      reliability: "high",
      mbfc: { credibility_rating: "HIGH CREDIBILITY", mbfc_url: "https://example.org" },
    });
    expect(rated.evidence).toBe(EVIDENCE.MEASURED);
    expect(rated.detail).toBe("HIGH CREDIBILITY");

    // Most sources in every fixture have `mbfc: {}` — the backend's own
    // source-type rule then decides the band, which is a heuristic.
    const unrated = reliabilityEvidence({ reliability: "medium", mbfc: {}, source_type: "web_source" });
    expect(unrated.evidence).toBe(EVIDENCE.ESTIMATED);
    expect(unrated.provenance).toBe(PROVENANCE.HEURISTIC);
  });
});

describe("authorGenderEvidence — the measured/estimated split", () => {
  it("takes Wikidata as ground truth and links the person", () => {
    const ev = authorGenderEvidence({
      name: "Amy Goodman",
      gender: "female",
      confidence: { gender: 0.7 },
      wikidata_author: { wikidata_id: "Q259317", wikidata_name: "Amy Goodman", gender: "female" },
    });
    expect(ev.value).toBe("female");
    expect(ev.provenance).toBe(PROVENANCE.WIKIDATA);
    expect(ev.evidence).toBe(EVIDENCE.MEASURED);
    expect(ev.ref.url).toBe("https://www.wikidata.org/wiki/Q259317");
  });

  it("marks a name-spelling guess as estimated and keeps its confidence and note", () => {
    const ev = authorGenderEvidence({
      name: "Someone",
      gender: "female",
      confidence: { gender: 0.7 },
      notes: "Author background estimated via first name and surname linguistic origin heuristics.",
      wikidata_author: { wikidata_id: "Q1", gender: null },
    });
    expect(ev.evidence).toBe(EVIDENCE.ESTIMATED);
    expect(ev.provenance).toBe(PROVENANCE.HEURISTIC);
    expect(ev.confidence).toBe(0.7);
    expect(ev.note).toContain("heuristics");
  });

  it("returns ABSENT — never a bucket — when the heuristic gives up", () => {
    // This is the real Duden.de profile: gender "unknown" at confidence 0.7.
    // It must not be counted into any gender bucket, in either direction.
    const ev = authorGenderEvidence({
      name: "Duden.de",
      gender: "unknown",
      confidence: { gender: 0.7 },
      wikidata_author: { wikidata_id: "Q73624591", gender: null },
    });
    expect(ev.evidence).toBe(EVIDENCE.ABSENT);
    expect(ev.value).toBeNull();
  });

  it("prefers Wikidata even when the heuristic reached a different answer", () => {
    const ev = authorGenderEvidence({
      gender: "female",
      confidence: { gender: 0.85 },
      wikidata_author: { wikidata_id: "Q2", gender: "male" },
    });
    expect(ev.value).toBe("male");
    expect(ev.evidence).toBe(EVIDENCE.MEASURED);
  });
});

describe("authorNationalityEvidence", () => {
  it("uses Wikidata citizenship when present", () => {
    const ev = authorNationalityEvidence({
      nationality_probability: { Germany: 0.7, Unknown: 0.3 },
      wikidata_author: { wikidata_id: "Q109623417", citizenships: ["Germany"] },
    });
    expect(ev.provenance).toBe(PROVENANCE.WIKIDATA);
    expect(ev.value).toBe("Germany");
  });

  it("falls back to the best non-unknown guess and carries its probability", () => {
    const ev = authorNationalityEvidence({
      nationality_probability: { Germany: 0.7, Unknown: 0.3 },
      wikidata_author: { citizenships: [] },
    });
    expect(ev.provenance).toBe(PROVENANCE.HEURISTIC);
    expect(ev.value).toBe("Germany");
    expect(ev.confidence).toBe(0.7);
  });

  it("is absent when the guess is entirely 'Unknown'", () => {
    const ev = authorNationalityEvidence({
      nationality_probability: { Unknown: 1.0 },
      wikidata_author: {},
    });
    expect(ev.evidence).toBe(EVIDENCE.ABSENT);
  });
});

describe("refs over the real fixtures", () => {
  it("treats the backend's empty `mbfc: {}` as no record at all", () => {
    // Every fixture is dominated by sources with `mbfc: {}`; an empty dict must
    // never produce a chip that implies MBFC rated the outlet.
    const bare = fr.sources.find((s) => !Object.keys(s.mbfc || {}).length);
    expect(bare, "fixture should contain a source with no MBFC record").toBeTruthy();
    expect(mbfcRef(bare)).toBeNull();
  });

  it("only returns a publisher ref when the backend resolved a Q-id", () => {
    for (const payload of [fr, de, en]) {
      for (const s of payload.sources) {
        const ref = publisherWikidataRef(s);
        if (ref) {
          expect(ref.id).toMatch(/^Q\d+$/);
          expect(ref.url).toBe(`https://www.wikidata.org/wiki/${ref.id}`);
        } else {
          expect(s.wikidata_publisher?.wikidata_id).toBeFalsy();
        }
      }
    }
  });
});
