# wikidata_mbfc — propose MBFC identifiers for Wikidata

Proposes **[P9852](https://www.wikidata.org/wiki/Property:P9852) (Media
Bias/Fact Check ID)** statements for the news outlets Wikipedia cites most, as
a QuickStatements batch for a human to review and run.

It adds **identifiers only**. It does not, and will not, copy MBFC's bias or
factual-reporting ratings into Wikidata.

---

## Why identifiers only

Two independent blockers, either of which is sufficient on its own.

**1. No property exists, and the community has twice declined to create one.**

- [`Property proposal/bais`](https://www.wikidata.org/wiki/Wikidata:Property_proposal/bais)
  (Oct 2024) — closed **not done**. ArthurPSmith: *"opinion, not data."*
  ChristianKl: *"it needs a lot of thought about how to find a system that's
  not just a bunch of opinions."* Its stated use case was scraping media-bias
  trackers — precisely this.
- [`Property proposal/assessed_source_reliability`](https://www.wikidata.org/wiki/Wikidata:Property_proposal/assessed_source_reliability)
  — proposed specifically to hold MBFC Credibility and Factual Reporting
  ratings. **Withdrawn** June 2023.

The nearest existing property, P1387 *political alignment*, carries ~7,500
statements, of which **8** cite MBFC. That is not a precedent.

**2. The licence cannot be reconciled with CC0.** MBFC's
[terms](https://mediabiasfactcheck.com/terms-and-conditions/): *"Reproduction,
redistribution, or manipulation of this material… is strictly prohibited."*
Their API licence §4: *"All intellectual property rights in the API data **and
any derivatives thereof** remain the sole property of Media Bias Fact Check."*
Wikidata is CC0 — an **irrevocable** waiver. You cannot CC0-dedicate data whose
owner asserts continuing rights in its derivatives.

An external identifier is different in kind: it is a pointer to a page, not a
copy of a dataset, and it makes no claim about the outlet. That is why P9852
exists (~3,300 items) while the rating properties do not.

**Also worth knowing before you run this.** English Wikipedia rates MBFC
[generally unreliable](https://en.wikipedia.org/wiki/Wikipedia:Reliable_sources/Perennial_sources)
(`WP:MBFC`): *"generally unreliable, as it is self-published. Editors have
questioned the methodology of the site's ratings."* Adding the identifier is
defensible — it aids navigation and asserts nothing. Deferring to the ratings
is not. If anyone objects on Project Chat, stop and discuss.

---

## The verification rule

**A slug is never accepted because it looks right.** It is accepted only when
the MBFC profile page itself prints `Source: <url>` on the same registrable
domain we started from.

This is not hypothetical. MBFC runs on WordPress, which fuzzy-matches unknown
slugs and answers with a 301 to the nearest post. The analyzer's existing
`_fetch_mbfc_rating` guesses a slug from the domain and follows those
redirects:

| guessed slug | 301 → | actual outlet |
|---|---|---|
| `/cairn/` | `/cairns-news-bias-and-credibility/` | Cairns News (Australian conspiracy site) |
| `/en/` | `/en-volve/` | En-Volve |
| `/fr/` | `/fr24-news/` | FR24 News |
| `/information/` | `/information-clearing-house/` | Information Clearing House |

Every one returns **HTTP 200** and parses cleanly, so a status-code check does
not catch it — which is why `cairn.info`, a French academic publisher, is
currently rated EXTREME RIGHT / LOW factuality in `mbfc_cache.json`. Only the
`Source:` comparison catches this. See
`tests/test_wikidata_mbfc.py::TestVerification::test_rejects_the_cairn_fuzzy_redirect`.

## The slug is the primary key

P9852 has a **distinct-values** constraint. The repo's
`wikidata_publisher_cache.json` maps `lemonde.fr` to Q69565062 (`lemonde.fr`,
the *website*), while `le-monde-bias` already sits on Q12461 (*Le Monde*, the
*newspaper*). Keying on the domain would have duplicated the identifier onto
the wrong item. So the tool checks every slug against **all ~3,300 already in
Wikidata** and skips anything taken.

---

## Usage

```bash
python -m wikidata_mbfc.cli --limit 40 --out-dir wikidata_mbfc/out
```

Outputs, none of which touch Wikidata:

| file | contents |
|---|---|
| `review.csv` | one row per proposal, with the evidence that verified it |
| `batch.quickstatements.tsv` | the batch, for you to paste in |
| `rejected.csv` | every domain refused, and why |
| `manifest.json` | counts, retrieval date, rejection breakdown |

**There is no `--write` flag and no credential anywhere in this package.** To
publish, read `review.csv`, then paste the batch into
[quickstatements.toolforge.org](https://quickstatements.toolforge.org) yourself.

## Before you publish

- [ ] Read `review.csv` row by row. For each, open `profile_url` and confirm
      the `Source:` line matches `domain`.
- [ ] Read `rejected.csv` too — a wrong *refusal* is a bug worth knowing about.
- [ ] Keep the first batch to **≤50 statements** and check them after running.
      [Wikidata:Bots](https://www.wikidata.org/wiki/Wikidata:Bots) expects a
      50–250-edit test run, *announced before it starts*.
- [ ] For anything larger, or if this becomes recurring, file a
      [request for bot permission](https://www.wikidata.org/wiki/Wikidata:Requests_for_permissions/Bot)
      first. Help:QuickStatements: *"Very large runs or potentially-controversial
      runs should go through the approval process described in Wikidata:Bots."*
- [ ] Note the batch's [EditGroups](https://www.wikidata.org/wiki/Wikidata:Edit_groups)
      URL. It reverts the whole run in one click.

Every statement carries a reference — `stated in` MBFC (P248 → Q60741379),
`reference URL` (P854) the profile, `retrieved` (P813) — as
[Wikidata:Bots](https://www.wikidata.org/wiki/Wikidata:Bots) requires:
*"Add sources to any statement that is added."*

## Rate limits

All requests pass through the repo's shared per-host limiter
(`wikipedia_sources_bias.ratelimit`), which already caps
`mediabiasfactcheck.com` at 1 request/second. Slug resolution costs up to 3
requests per domain, plus a search only on failure. The corpus ranking exists
so those requests are spent on the most-cited domains first.
