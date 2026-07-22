# Methodology

How WikiBias Analyzer turns a Wikipedia article into the numbers on the
dashboard — and, just as importantly, what those numbers do **not** mean.

Written against the code in `wikipedia_sources_bias/` and `backend/`, not
against intentions. Where a step is a heuristic rather than a measurement, it
says so.

---

## 1. Extracting the references

1. Fetch the article HTML.
2. Locate reference containers (`ol.references` and the usual variants), parse
   each citation, and collect its URLs.
3. Unwrap archive links (`web.archive.org/web/…/http://original`) back to the
   original URL, so a source is counted once whether or not it was archived.
4. Deduplicate by URL.
5. Drop a publisher's bare homepage when a deeper link to the same host is
   already present. German-style citations often read *"In: Website
   https://example.org/"*, which yielded both the document and the front page
   and counted that publisher twice.

Only the first `--max-sources` references are analysed unless `--all` is used.
The web app analyses a bounded subset by default; the source count shown is
the number **analysed**, not the number of references in the article.

## 2. Geographic origin

Tried in order, first hit wins:

| Order | Signal | Nature |
|---|---|---|
| 1 | Curated domain database (`heuristics_data.py`) | Editorial, hand-maintained |
| 2 | Country-code TLD (`.fr` → France, `.de` → Germany) | Heuristic |
| 3 | Wikidata publisher country (P17 / P495 on the publisher item) | Sourced |

The **region** (Europe, Americas, Asia, Africa, Oceania) is derived from the
country via a lookup table.

When nothing resolves, the source is marked `unmapped` and carries a reason
code explaining why — `generic_tld` (a `.com`/`.net`/`.org` address carries no
country signal), `no_country_signal`, or `region_missing` (country known, but
absent from the region table). **Unmapped sources are always shown, never
silently dropped or redistributed**, because hiding them would flatter the
diversity numbers.

> **Caveat.** A domain's country is where the *publisher* is registered, not
> necessarily where the reporting was done, who owns the outlet, or what
> perspective it represents. `.com` publishers are systematically harder to
> place, which biases the unmapped bucket toward large international outlets.

## 3. Political leaning

1. Wikidata claims on the publisher item (political ideology, political
   alignment).
2. [Media Bias/Fact Check](https://mediabiasfactcheck.com/) rating, scraped
   live with a Wayback Machine fallback, parsed for the bias label and the
   numeric score.
3. Otherwise `unknown` — and `unknown` is reported, not hidden.

> **Caveat.** MBFC is one organisation's editorial judgement, US-centric in
> both coverage and framing, and thin outside English-language media. A
> left/right axis imported from US politics often does not describe European
> or non-Western outlets well. Treat leaning distributions as indicative.

## 4. Reliability

A tier — `academic`, `high`, `medium`, `low` — from the curated domain
database, structural signals (`.edu`, `.gov`, academic publishers), and MBFC's
factual-reporting rating where available. Absent evidence, a source is
`medium`, which is a default rather than a finding.

## 5. Authors

Two very different classes of data, and the interface must not conflate them:

**Measured (Wikidata).** When an author matches a Wikidata item: gender,
citizenship, occupation, employer, political party. Sourced and checkable via
the item's Q-id.

**Estimated (linguistic heuristics).** Otherwise, `nametrace` or offline
lexical rules infer human-vs-organisation, a gender probability, and a
regional origin from the name. Each carries a `confidence` value and a note
saying it is an estimate.

> **Caveat.** Name-based gender and nationality inference is unreliable for
> non-Western names, initials, pseudonyms and organisational bylines, and it
> encodes the biases of its training data. It is useful for corpus-level
> shape, never for a claim about an individual. Author fields are frequently
> the publication's own name (e.g. "La-Croix.com"), which the classifier may
> treat as a person.

## 6. Language and readability

Lexicon-based scoring of citation text: subjectivity, sensationalism, loaded
words, and an opinion flag, plus Flesch reading-ease where the page body could
be fetched. A transformer sentiment model can be enabled locally; it is
**deliberately excluded from the Toolforge deployment** (a container gets 10 GB
including the image, and there are no GPUs), so the deployed tool uses the
lexical path.

> **Caveat.** Scores come from the *citation text*, which is often a title and
> a date — a very short sample. Coverage counts are reported alongside the
> averages; a metric derived from a handful of sources is labelled as such.

## 7. Identifiers

DOIs are resolved through Crossref, ISBNs through Wikidata and Google Books,
OCLC numbers through WorldCat, to recover publisher and country for book and
journal citations that have no useful domain.

## 8. Politeness and caching

All outbound requests pass through a shared per-host rate limiter, so raising
concurrency never raises the rate any single service sees. `Retry-After` on a
429 backs off every caller to that host. Lookups (Wikidata, MBFC, Crossref,
name inference) are cached — in JSON files for the CLI, in MariaDB for the
deployed tool, so the workers share one cache instead of each re-querying.

## 9. What this tool cannot tell you

- **Citation counts are not influence.** One citation in a lead paragraph and
  one in a footnote count the same.
- **Publisher country is not perspective.** A French-registered outlet may
  publish a foreign correspondent; an international outlet may be intensely
  local.
- **Unknown is not neutral.** Large `unknown`/`unmapped` buckets mean the
  evidence is missing, not that the sources are balanced.
- **Absent is not zero.** A metric nothing was measured for is reported as
  having no data, not as a score of zero.
- **This is not an article-quality judgement.** A well-sourced article on a
  national topic *should* cite national sources. Geographic concentration is a
  description, not a defect.

---

*Project: [Wikimania 2026 — Team 05E Europe, "Deciphering
Biases"](https://wikimania.wikimedia.org/wiki/2026:Team_challenges/Team_05E_Europe).
Source: <https://github.com/Superraptor/Wikipedia-Source-Bias> (MIT).
Contributors: see `AUTHORS.md`.*
