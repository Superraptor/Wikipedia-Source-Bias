"""Render proposals as a QuickStatements batch and a human review table.

Nothing in this package writes to Wikidata. The batch is a file; a human reads
it, then pastes it into https://quickstatements.toolforge.org themselves. That
keeps the edits attributable to a person who checked them, and keeps the whole
run revertable as one EditGroups batch.
"""
from __future__ import annotations

import csv
import io

# Q60741379 is the Wikidata item for Media Bias/Fact Check, and is the declared
# "applicable 'stated in' value" (P9073) on P9852 itself.
MBFC_ITEM = "Q60741379"
STATED_IN = "S248"
REFERENCE_URL = "S854"
RETRIEVED = "S813"


def quickstatements(proposals, retrieved_date):
    """One tab-separated QuickStatements V1 line per proposal.

    `retrieved_date` is passed in rather than read from the clock so a run is
    reproducible and a reviewer can diff two batches meaningfully.
    """
    lines = []
    for row in proposals:
        lines.append(
            "\t".join(
                [
                    row["qid"],
                    "P9852",
                    f"\"{row['slug']}\"",
                    STATED_IN,
                    MBFC_ITEM,
                    REFERENCE_URL,
                    f"\"{row['profile_url']}\"",
                    RETRIEVED,
                    f"+{retrieved_date}T00:00:00Z/11",
                ]
            )
        )
    return "\n".join(lines) + ("\n" if lines else "")


REVIEW_COLUMNS = [
    "domain",
    "citations",
    "qid",
    "label",
    "types",
    "slug",
    "profile_url",
    "stated_source",
    "verified_by",
]


def review_table(proposals):
    """A CSV a reviewer can open and check row by row."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=REVIEW_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in proposals:
        writer.writerow(
            {
                "domain": row["domain"],
                "citations": row["citations"],
                "qid": row["qid"],
                "label": row["label"],
                "types": "; ".join(row.get("type_names", [])),
                "slug": row["slug"],
                "profile_url": row["profile_url"],
                "stated_source": row["stated_source"],
                "verified_by": f"Source: {row['stated_source']} == {row['domain']}",
            }
        )
    return buffer.getvalue()


def rejections_table(rejections):
    """Everything the tool refused, and why. Reviewed as carefully as the batch."""
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer, fieldnames=["domain", "citations", "outcome", "detail"], lineterminator="\n"
    )
    writer.writeheader()
    for row in rejections:
        writer.writerow(
            {
                "domain": row["domain"],
                "citations": row["citations"],
                "outcome": row["outcome"],
                "detail": row["detail"],
            }
        )
    return buffer.getvalue()
