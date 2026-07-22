"""Discover and *verify* an MBFC profile slug for a domain.

The rule this module exists to enforce: a slug is never accepted because it
looks right. It is accepted only when the profile page itself states a
`Source:` URL on the same registrable domain we started from.

That rule is not theoretical. MBFC runs on WordPress, which fuzzy-matches
unknown slugs and answers with a 301 to the nearest post. The analyzer's
existing `_fetch_mbfc_rating` guesses a slug from the domain and follows those
redirects, so:

    cairn.info   -> /cairn/       -> 301 -> /cairns-news-bias-and-credibility/
    lefigaro.fr  -> /le-figaro/   -> 301 -> (correct page, by luck)

`cairns-news` is an Australian conspiracy site; `cairn.info` is a French
academic publisher. Both requests return HTTP 200 and parse cleanly, so a
status-code check does not catch it. Only the `Source:` comparison does.
"""
from __future__ import annotations

import html
import re

import requests

from wikipedia_sources_bias import ratelimit

from .domains import registrable, same_outlet

MBFC_BASE = "https://mediabiasfactcheck.com"

# A contactable UA. MBFC's terms allow reading the site; identifying the tool
# is politeness, and it lets them block us specifically rather than broadly.
USER_AGENT = (
    "WikidataMBFCIdBot/0.1 (+https://github.com/Superraptor/Wikipedia-Source-Bias; "
    "identifier-only; contact via repository issues)"
)

# P9852's format constraint (P1793) on Wikidata.
SLUG_PATTERN = re.compile(r"^[a-z\d]+(-[a-z\d]+)*$")

_SOURCE_LINE = re.compile(r"Source:\s*(https?://[^\s<\"]+)", re.I)
_SEARCH_HIT = re.compile(
    r"<h[23][^>]*class=\"[^\"]*(?:entry-title|post-title)[^\"]*\"[^>]*>\s*"
    r"<a[^>]*href=\"(https://mediabiasfactcheck\.com/[a-z0-9-]+/)\"",
    re.I | re.S,
)


class Rejected(Exception):
    """A candidate slug failed verification. Carries a human-readable reason."""


def _get(url, allow_redirects=True, timeout=15):
    ratelimit.wait(url)
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        allow_redirects=allow_redirects,
        timeout=timeout,
    )
    ratelimit.note_response(url, response)
    return response


def _page_text(markup: str) -> str:
    stripped = re.sub(r"<script.*?</script>|<style.*?</style>", " ", markup, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", stripped)))


def stated_source_url(markup: str) -> str | None:
    """The `Source:` URL MBFC prints on a profile page, if present."""
    match = _SOURCE_LINE.search(_page_text(markup))
    return match.group(1) if match else None


def slug_of(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def search_slugs(domain: str, limit=6):
    """Candidate profile URLs from MBFC's own site search.

    Search is a *discovery* mechanism only. Its hits are frequently wrong --
    searching `lexpress` returns Le Point -- so every hit still goes through
    `verify`.
    """
    query = registrable(domain).rsplit(".", 1)[0]
    response = _get(f"{MBFC_BASE}/?s={requests.utils.quote(query)}")
    if response.status_code != 200:
        return []
    hits = []
    for url in _SEARCH_HIT.findall(response.text):
        if url not in hits:
            hits.append(url)
        if len(hits) >= limit:
            break
    return hits


def verify(candidate_url: str, domain: str):
    """Confirm a candidate profile really describes `domain`.

    Returns a dict on success. Raises `Rejected` with a reason otherwise.
    Redirects are followed, but the *final* URL supplies the slug and the page
    must name our domain -- so a fuzzy-match redirect to another outlet is
    caught by the `Source:` comparison rather than by trusting the URL.
    """
    response = _get(candidate_url, allow_redirects=True)
    if response.status_code != 200:
        raise Rejected(f"HTTP {response.status_code} for {candidate_url}")

    final_url = response.url
    slug = slug_of(final_url)
    if not SLUG_PATTERN.match(slug):
        raise Rejected(f"slug {slug!r} violates the P9852 format constraint")

    stated = stated_source_url(response.text)
    if not stated:
        raise Rejected(f"{final_url} prints no 'Source:' line to verify against")

    if not same_outlet(stated, domain):
        raise Rejected(
            f"{final_url} states Source: {stated} "
            f"({registrable(stated)}), which is not {registrable(domain)}"
        )

    return {
        "slug": slug,
        "profile_url": final_url,
        "stated_source": stated,
        "redirected": final_url.rstrip("/") != candidate_url.rstrip("/"),
    }


def resolve(domain: str):
    """Find a verified MBFC slug for `domain`, or return the rejection reasons.

    Tries the conventional slug shapes first because they cost one request and
    usually hit, then falls back to site search. Every path ends in `verify`.
    """
    stem = registrable(domain).rsplit(".", 1)[0].replace(".", "-")
    attempts = [
        f"{MBFC_BASE}/{stem}-bias-and-credibility/",
        f"{MBFC_BASE}/{stem}-bias/",
        f"{MBFC_BASE}/{stem}/",
    ]
    reasons = []
    seen = set()
    for url in attempts:
        try:
            result = verify(url, domain)
        except Rejected as exc:
            reasons.append(str(exc))
            continue
        except requests.RequestException as exc:
            reasons.append(f"network error for {url}: {exc}")
            continue
        return result, reasons

    try:
        hits = search_slugs(domain)
    except requests.RequestException as exc:
        reasons.append(f"search failed: {exc}")
        hits = []

    for url in hits:
        if url in seen:
            continue
        seen.add(url)
        try:
            result = verify(url, domain)
        except Rejected as exc:
            reasons.append(str(exc))
            continue
        except requests.RequestException as exc:
            reasons.append(f"network error for {url}: {exc}")
            continue
        return result, reasons

    return None, reasons
