"""Identity of the inputs and of the method that produced a result.

Without these, nothing the tool reports is reproducible:

  - An article changes continuously, so "Brexit: 50% Europe" is meaningless
    without saying WHICH revision it was computed from.
  - The method changes too. The analyses stored today were produced by more
    than a dozen different versions of this code in a single day, and nothing
    recorded which. They are not comparable with each other, and nothing said so.

`METHOD_VERSION` is a content hash of the modules that actually determine a
result, so it changes exactly when the method changes -- no build step, no git
required in the container, and no way to forget to bump it.
"""
from __future__ import annotations

import hashlib
import os
import re

# Modules whose contents change what the analyser outputs. Adding a heuristic,
# a curated domain or a region mapping all move this fingerprint.
_RESULT_AFFECTING = ("analysis.py", "heuristics_data.py")

_HERE = os.path.dirname(os.path.abspath(__file__))


def fingerprint(paths) -> str:
    """Short, stable content hash over the given files."""
    digest = hashlib.sha256()
    for path in sorted(paths):
        try:
            with open(path, "rb") as handle:
                digest.update(handle.read())
        except OSError:
            # A missing file is itself part of the identity.
            digest.update(f"<missing:{os.path.basename(path)}>".encode())
    return digest.hexdigest()[:12]


METHOD_VERSION = fingerprint(os.path.join(_HERE, name) for name in _RESULT_AFFECTING)

# MediaWiki embeds the revision in the page's JS config, so pinning the input
# costs no extra request.
_REVISION_RE = re.compile(r'"wgRevisionId"\s*:\s*(\d+)')
_PAGE_ID_RE = re.compile(r'"wgArticleId"\s*:\s*(\d+)')


def extract_revision(html: str):
    """(revision_id, page_id) from article HTML; either may be None."""
    if not html:
        return None, None
    rev = _REVISION_RE.search(html)
    page = _PAGE_ID_RE.search(html)
    return (
        int(rev.group(1)) if rev else None,
        int(page.group(1)) if page else None,
    )


def permalink(page_url: str, revision_id) -> str | None:
    """A URL that always shows the exact revision analysed."""
    if not page_url or not revision_id:
        return None
    try:
        from urllib.parse import urlparse

        parts = urlparse(page_url)
        if not parts.netloc:
            return None
        return f"{parts.scheme}://{parts.netloc}/w/index.php?oldid={revision_id}"
    except Exception:
        return None
