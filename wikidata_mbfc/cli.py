"""Command line entry point.

    python -m wikidata_mbfc.cli --limit 40 --out-dir wikidata_mbfc/out

The tool proposes; it never writes. There is deliberately no `--write` flag
and no Wikidata credential anywhere in this package -- publishing a batch is a
manual step a human takes after reading the review table.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

from . import corpus, emit, mbfc, wikidata
from .domains import is_homepage, same_outlet


HUMAN = "Q5"


def _pick_item(candidates, domain, entities):
    """Choose the outlet item for a domain, or explain why we cannot.

    Narrowing runs in order of how much it can be trusted:

    1. Drop humans. A journalist whose staff page lives on `lemonde.fr` is
       never the outlet, even though P9852 does allow items about people.
    2. Keep items whose official website is the bare homepage. A TV programme
       on `francetvinfo.fr/vrai-ou-fake` is not the broadcaster.
    3. Prefer types inside P9852's declared constraint.

    Anything still ambiguous is refused. Guessing at this step is exactly how
    `lemonde.fr` would land on the website item instead of the newspaper.
    """
    summaries = [entities[c["qid"]] for c in candidates if c["qid"] in entities]
    if not summaries:
        return None, "no Wikidata item with an official website on this domain"

    people = [s for s in summaries if HUMAN in s["types"]]
    outlets = [s for s in summaries if HUMAN not in s["types"]]
    if not outlets:
        return None, (
            f"only person items match this domain "
            f"({', '.join(s['qid'] for s in people[:5])})"
        )

    homepage = [
        s
        for s in outlets
        if any(
            same_outlet(site, domain) and is_homepage(site) for site in s["websites"]
        )
    ]
    narrowed = homepage or outlets

    typed = [s for s in narrowed if s["type_ok"]]
    if typed:
        narrowed = typed

    if len(narrowed) > 1:
        listed = ", ".join(f"{s['qid']} ({s['label']})" for s in narrowed[:5])
        return None, f"ambiguous: {len(narrowed)} candidate items -- {listed}"
    return narrowed[0], None


def run(limit, out_dir, retrieved, corpus_root):
    ranked, articles = corpus.rank_candidates(limit=limit, root=corpus_root)
    print(
        f"corpus: {articles} article analyses, "
        f"{len(ranked)} candidate domains after removing infrastructure",
        file=sys.stderr,
    )

    print("fetching slugs already used in Wikidata ...", file=sys.stderr)
    taken = wikidata.used_slugs()
    print(f"  {len(taken)} existing P9852 values", file=sys.stderr)

    proposals, rejections = [], []

    for index, entry in enumerate(ranked, 1):
        domain, citations = entry["domain"], entry["citations"]
        print(f"[{index}/{len(ranked)}] {domain} ({citations} citations)", file=sys.stderr)

        def reject(outcome, detail):
            rejections.append(
                {
                    "domain": domain,
                    "citations": citations,
                    "outcome": outcome,
                    "detail": detail,
                }
            )

        try:
            candidates = wikidata.items_for_domain(domain)
        except Exception as exc:  # network / SPARQL failure is a skip, not a crash
            reject("error", f"Wikidata lookup failed: {exc}")
            continue
        if not candidates:
            reject("no-item", "no Wikidata item has P856 on this domain")
            continue

        try:
            entities = {
                qid: wikidata.summarise(entity)
                for qid, entity in wikidata.get_entities(
                    [c["qid"] for c in candidates]
                ).items()
                if "missing" not in entity
            }
        except Exception as exc:
            reject("error", f"entity fetch failed: {exc}")
            continue

        # Checked before disambiguation: if any item on this domain already
        # carries the identifier, there is nothing to add and no need to pick
        # between items -- or to spend an MBFC request. This is what makes
        # `lemonde.fr` resolve cleanly despite five items matching the domain.
        present = [
            summary
            for summary in entities.values()
            if summary["existing_p9852"] and HUMAN not in summary["types"]
        ]
        if present:
            reject(
                "already-present",
                "; ".join(
                    f"{s['qid']} ({s['label']}) has P9852 = {', '.join(s['existing_p9852'])}"
                    for s in present
                ),
            )
            continue

        item, why = _pick_item(candidates, domain, entities)
        if item is None:
            reject("ambiguous-item", why)
            continue

        try:
            verified, reasons = mbfc.resolve(domain)
        except Exception as exc:
            reject("error", f"MBFC lookup failed: {exc}")
            continue
        if verified is None:
            reject("no-verified-profile", "; ".join(reasons[:3]) or "no candidate profile")
            continue

        slug = verified["slug"]
        if slug in taken:
            reject(
                "slug-taken",
                f"slug {slug!r} is already on {taken[slug]}; "
                f"we would have written it to {item['qid']}",
            )
            continue

        row = {
            "domain": domain,
            "citations": citations,
            "qid": item["qid"],
            "label": item["label"],
            "type_names": item["type_names"],
            "type_ok": item["type_ok"],
            "slug": slug,
            "profile_url": verified["profile_url"],
            "stated_source": verified["stated_source"],
        }
        if not item["type_ok"]:
            reject(
                "type-warning",
                f"{item['qid']} is {', '.join(item['type_names'])}, "
                f"outside P9852's declared type constraint -- review before use",
            )
            continue
        proposals.append(row)
        # Guard against two domains in one run resolving to the same slug.
        taken[slug] = item["qid"]

    os.makedirs(out_dir, exist_ok=True)
    batch_path = os.path.join(out_dir, "batch.quickstatements.tsv")
    review_path = os.path.join(out_dir, "review.csv")
    rejected_path = os.path.join(out_dir, "rejected.csv")
    manifest_path = os.path.join(out_dir, "manifest.json")

    with open(batch_path, "w", encoding="utf-8") as handle:
        handle.write(emit.quickstatements(proposals, retrieved))
    with open(review_path, "w", encoding="utf-8") as handle:
        handle.write(emit.review_table(proposals))
    with open(rejected_path, "w", encoding="utf-8") as handle:
        handle.write(emit.rejections_table(rejections))
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "retrieved": retrieved,
                "articles_analysed": articles,
                "domains_considered": len(ranked),
                "proposed": len(proposals),
                "rejected": len(rejections),
                "rejected_by_outcome": {
                    outcome: sum(1 for r in rejections if r["outcome"] == outcome)
                    for outcome in sorted({r["outcome"] for r in rejections})
                },
            },
            handle,
            indent=2,
        )

    print(
        f"\nproposed {len(proposals)} statements, rejected {len(rejections)} domains\n"
        f"  batch:    {batch_path}\n"
        f"  review:   {review_path}\n"
        f"  rejected: {rejected_path}\n"
        f"\nNothing has been written to Wikidata. Read review.csv, then paste\n"
        f"batch.quickstatements.tsv into https://quickstatements.toolforge.org",
        file=sys.stderr,
    )
    return proposals, rejections


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Propose MBFC IDs (P9852) for Wikidata. Never writes to Wikidata."
    )
    parser.add_argument(
        "--limit", type=int, default=40, help="how many top-cited domains to consider"
    )
    parser.add_argument("--out-dir", default="wikidata_mbfc/out")
    parser.add_argument(
        "--retrieved",
        default=dt.date.today().isoformat(),
        help="retrieval date recorded in the P813 reference (YYYY-MM-DD)",
    )
    parser.add_argument("--corpus-root", default=corpus.REPO_ROOT)
    args = parser.parse_args(argv)
    run(args.limit, args.out_dir, args.retrieved, args.corpus_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
