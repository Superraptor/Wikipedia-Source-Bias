"""Domain normalisation and comparison.

The verification step compares the domain we started from against the domain
MBFC states on its own profile page. That comparison decides whether a
statement is proposed at all, so it has to be strict about the things that
matter (a different registrable domain is a different outlet) and forgiving
about the things that do not (`www.`, scheme, path, trailing dot, case).
"""
from __future__ import annotations

from urllib.parse import urlparse

# Second-level suffixes under which registrations happen, so `bbc.co.uk` is a
# registrable domain and `co.uk` is not. This is a deliberate subset of the
# Public Suffix List: the full list is a dependency and a data-update burden,
# and an unlisted suffix fails *safe* here -- it makes the comparison stricter,
# which sends a candidate to review rather than proposing a bad statement.
_MULTIPART_SUFFIXES = frozenset(
    {
        "co.uk", "org.uk", "gov.uk", "ac.uk", "me.uk", "net.uk", "sch.uk",
        "com.au", "net.au", "org.au", "edu.au", "gov.au",
        "co.nz", "org.nz", "govt.nz", "ac.nz",
        "co.za", "org.za", "gov.za", "ac.za",
        "com.br", "org.br", "gov.br", "net.br",
        "co.jp", "or.jp", "ne.jp", "ac.jp", "go.jp",
        "co.kr", "or.kr", "go.kr",
        "com.mx", "org.mx", "gob.mx",
        "com.ar", "org.ar", "gob.ar",
        "co.in", "org.in", "net.in", "gov.in", "ac.in",
        "com.tr", "org.tr", "gov.tr",
        "com.cn", "org.cn", "net.cn", "gov.cn", "edu.cn",
        "com.hk", "org.hk", "gov.hk",
        "com.sg", "org.sg", "gov.sg",
        "gouv.fr", "asso.fr", "com.es", "gob.es",
    }
)

# Hosts that are infrastructure rather than publishers. They appear in the
# citation frequency ranking (an archive link is still a citation) but they
# must never be handed to MBFC: `webcache.googleusercontent.com` is not an
# outlet, and asking MBFC about it invites exactly the fuzzy-slug mismatch
# this tool exists to prevent.
INFRASTRUCTURE_DOMAINS = frozenset(
    {
        "archive.org", "web.archive.org", "archive.today", "archive.ph",
        "archive.is", "archive.wikiwix.com", "wikiwix.com",
        "savethearchive.com", "webcache.googleusercontent.com",
        "cache.google.com", "google.com", "books.google.com",
        "scholar.google.com", "translate.google.com",
        "doi.org", "dx.doi.org", "portal.issn.org", "worldcat.org",
        "isbnsearch.org", "crossref.org", "handle.net",
        "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com",
        "twitter.com", "x.com", "facebook.com", "instagram.com",
        "linkedin.com", "t.me", "reddit.com",
        "wikipedia.org", "wikidata.org", "wikimedia.org", "wikisource.org",
        "scribd.com", "issuu.com", "calameo.com", "slideshare.net",
        "amazon.com", "amazon.fr", "worldcat.com",
    }
)


def host_of(value: str) -> str:
    """Extract a bare lowercase hostname from a URL or a bare domain."""
    if not value:
        return ""
    value = value.strip()
    if "//" not in value:
        value = "//" + value
    host = (urlparse(value).hostname or "").lower().rstrip(".")
    return host


def strip_www(host: str) -> str:
    """Drop leading `www.` / `www2.` style prefixes."""
    parts = host.split(".")
    while len(parts) > 2 and parts[0].startswith("www"):
        parts = parts[1:]
    return ".".join(parts)


def registrable(host_or_url: str) -> str:
    """Reduce to the registrable domain: `www.lemonde.fr/x` -> `lemonde.fr`.

    Falls back to the full host when the suffix structure is unrecognised,
    which makes the later equality test stricter rather than looser.
    """
    host = host_of(host_or_url)
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    last_two = ".".join(parts[-2:])
    if last_two in _MULTIPART_SUFFIXES:
        return ".".join(parts[-3:]) if len(parts) >= 3 else host
    return last_two


def is_infrastructure(domain: str) -> bool:
    """True when the domain is an archive, cache, aggregator or platform."""
    host = strip_www(host_of(domain))
    if host in INFRASTRUCTURE_DOMAINS:
        return True
    return registrable(host) in INFRASTRUCTURE_DOMAINS


def is_homepage(url: str) -> bool:
    """Whether a URL points at a site root rather than a page inside it.

    The outlet's item carries the bare homepage as its official website; a
    journalist's item or a TV programme's item carries a path underneath it.
    That difference is what separates `francetvinfo.fr` the broadcaster from
    the ten programme items that also cite the domain.
    """
    parsed = urlparse(url if "//" in url else "//" + url)
    return parsed.path in ("", "/") and not parsed.query


def same_outlet(a: str, b: str) -> bool:
    """Whether two URLs/domains refer to the same registrable domain."""
    ra, rb = registrable(a), registrable(b)
    return bool(ra) and ra == rb
