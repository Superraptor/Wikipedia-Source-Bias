"""Propose Media Bias/Fact Check IDs (P9852) for Wikidata items.

This tool adds *identifiers*, never ratings. See README.md in this directory
for why that distinction is the whole point of the tool.

It never writes to Wikidata. Its only output is a QuickStatements batch file
and a review table for a human to read first.
"""

__all__ = ["corpus", "domains", "mbfc", "wikidata", "emit"]
