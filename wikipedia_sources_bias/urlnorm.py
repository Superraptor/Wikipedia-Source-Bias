"""Canonicalisation of Wikipedia article URLs.

Two URLs that name the same article must produce the same cache key, or the
same analysis is queued and recomputed once per link variant. In practice the
variants come from share links:

    https://fr.wikipedia.org/wiki/Le_Média?wprov=sfla1
    https://fr.wikipedia.org/wiki/Le_Média

`wprov` is MediaWiki's own share-provenance marker and says nothing about the
content. The same goes for the usual advertising trackers and for `#fragment`.

Deliberately a DENYLIST rather than "strip the whole query string": some query
parameters do change what is analysed -- `oldid` selects a specific revision,
`action` and `diff` select a different view -- and silently dropping those
would make two genuinely different requests collide on one cache entry.
"""
from __future__ import annotations

from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

# Parameters that never change which content is analysed.
TRACKING_PARAMS = {
    "wprov",          # MediaWiki share provenance
    "fbclid",
    "gclid",
    "msclkid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "s",              # twitter share
    "_ga",
    "yclid",
}
TRACKING_PREFIXES = ("utm_",)


def _is_tracking(key: str) -> bool:
    k = key.lower()
    return k in TRACKING_PARAMS or k.startswith(TRACKING_PREFIXES)


def canonical_page_url(url: str) -> str:
    """Return `url` with tracking parameters and the fragment removed.

    Anything unparseable is returned unchanged: a canonicaliser must never be
    the reason an analysis fails.
    """
    if not url:
        return url
    try:
        parts = urlparse(url)
    except Exception:
        return url

    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if not _is_tracking(k)]

    return urlunparse((
        parts.scheme,
        parts.netloc,
        parts.path,
        parts.params,
        urlencode(kept),
        "",  # drop the fragment; it selects a section, not an article
    ))
