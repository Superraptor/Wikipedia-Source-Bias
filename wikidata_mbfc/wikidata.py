"""Wikidata lookups for the P9852 proposal pipeline.

Three checks matter here, and all three are refusals rather than fixes:

1. Which item is the outlet? The repo's `wikidata_publisher_cache.json` maps
   `lemonde.fr` to Q69565062 (`lemonde.fr`, the *website*), while `le-monde-bias`
   already sits on Q12461 (*Le Monde*, the newspaper). Writing to the cached QID
   would have duplicated the identifier onto the wrong item.
2. Does the item already carry P9852? Then there is nothing to add.
3. Is the slug already used anywhere? P9852 has a distinct-values constraint,
   so a slug in use elsewhere means our item is either wrong or redundant.

Check 3 is what makes the slug, not the domain, the primary key of this tool.
"""
from __future__ import annotations

import time

import requests

from wikipedia_sources_bias import ratelimit

from .domains import registrable, same_outlet

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
API_ENDPOINT = "https://www.wikidata.org/w/api.php"

USER_AGENT = (
    "WikidataMBFCIdBot/0.1 (+https://github.com/Superraptor/Wikipedia-Source-Bias; "
    "identifier-only; contact via repository issues)"
)

# P9852's type constraint (Q21503250) allowed classes. An item outside these
# is not necessarily wrong -- subclasses count and the constraint is advisory --
# so a miss is reported as a warning on the row, never a silent pass.
ALLOWED_TYPES = {
    "Q5": "human",
    "Q11033": "mass media",
    "Q43229": "organization",
    "Q35127": "website",
    "Q1002697": "periodical",
    "Q30849": "blog",
    "Q24634210": "podcast",
    "Q102345381": "social media account",
    "Q16334295": "media outlet",
    "Q1110794": "daily newspaper",
    "Q11032": "newspaper",
    "Q1153191": "online newspaper",
    "Q1616075": "television station",
    "Q14350": "radio station",
    "Q41298": "magazine",
    "Q1002954": "news agency",
}


def _sparql(query: str, timeout=90, attempts=3):
    """Run a SPARQL query, retrying timeouts.

    The public endpoint intermittently times out on the P856 substring scan;
    a transient failure there would otherwise silently drop a high-citation
    domain from the run, which is a worse outcome than waiting.
    """
    last = None
    for attempt in range(attempts):
        ratelimit.wait(SPARQL_ENDPOINT)
        try:
            response = requests.get(
                SPARQL_ENDPOINT,
                params={"query": query, "format": "json"},
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/sparql-results+json",
                },
                timeout=timeout,
            )
            ratelimit.note_response(SPARQL_ENDPOINT, response)
            response.raise_for_status()
            return response.json()["results"]["bindings"]
        except (requests.Timeout, requests.HTTPError, ValueError) as exc:
            last = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt * 5)
    raise last


def used_slugs():
    """Every MBFC slug already present in Wikidata, as a slug -> QID map.

    One query, ~3.3k rows. Fetched once per run and used to reject candidates,
    which is both cheaper and safer than asking per item.
    """
    rows = _sparql(
        "SELECT ?item ?id WHERE { ?item wdt:P9852 ?id. }"
    )
    return {
        row["id"]["value"]: row["item"]["value"].rsplit("/", 1)[-1]
        for row in rows
    }


def _homepage_urls(root: str):
    """The URL spellings a homepage plausibly takes as a P856 value."""
    urls = []
    for scheme in ("https", "http"):
        for host in (f"www.{root}", root):
            urls.append(f"{scheme}://{host}/")
            urls.append(f"{scheme}://{host}")
    return urls


def _collect(rows, limit):
    out = []
    for row in rows:
        site = row["site"]["value"]
        qid = row["item"]["value"].rsplit("/", 1)[-1]
        if any(existing["qid"] == qid for existing in out):
            continue
        out.append(
            {
                "qid": qid,
                "label": row.get("itemLabel", {}).get("value", ""),
                "site": site,
            }
        )
        if len(out) >= limit:
            break
    return out


def items_for_domain(domain: str, limit=10):
    """Candidate items whose official website (P856) is on `domain`.

    Two strategies, cheapest and most precise first:

    1. Exact match against the handful of URL spellings a homepage takes,
       via a `VALUES` block. This uses the P856 index -- ~0.3s -- and returns
       only items that claim the site *root*, which is already most of the
       disambiguation work: `lefigaro.fr` yields Le Figaro alone, with no
       journalists or programme items.
    2. Only if that finds nothing, fall back to a substring scan. It is far
       slower and the public endpoint times out on it, so it is a last resort
       for outlets whose P856 carries a path or a redirect host.

    Either way the result is re-checked in Python with registrable-domain
    equality, because a substring match would happily accept
    `lemonde.fr.evil.com`.
    """
    root = registrable(domain)
    values = " ".join(f"<{url}>" for url in _homepage_urls(root))
    exact = f"""
    SELECT ?item ?itemLabel ?site WHERE {{
      VALUES ?site {{ {values} }}
      ?item wdt:P856 ?site .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,fr". }}
    }} LIMIT {limit * 5}
    """
    out = _collect(_sparql(exact), limit)
    if out:
        return out

    fallback = f"""
    SELECT ?item ?itemLabel ?site WHERE {{
      ?item wdt:P856 ?site .
      FILTER(CONTAINS(LCASE(STR(?site)), "{root}"))
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,fr". }}
    }} LIMIT {limit * 5}
    """
    rows = [row for row in _sparql(fallback) if same_outlet(row["site"]["value"], root)]
    return _collect(rows, limit)


def get_entities(qids):
    """Fetch labels, P31 and P9852 for up to 50 items per request."""
    entities = {}
    qids = list(qids)
    for start in range(0, len(qids), 50):
        chunk = qids[start : start + 50]
        ratelimit.wait(API_ENDPOINT)
        response = requests.get(
            API_ENDPOINT,
            params={
                "action": "wbgetentities",
                "ids": "|".join(chunk),
                "props": "labels|claims",
                "languages": "en|fr",
                "format": "json",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        ratelimit.note_response(API_ENDPOINT, response)
        response.raise_for_status()
        entities.update(response.json().get("entities", {}))
    return entities


def summarise(entity):
    """Reduce a raw entity to the fields the review table needs."""
    labels = entity.get("labels", {})
    claims = entity.get("claims", {})

    def _values(prop):
        out = []
        for claim in claims.get(prop, []):
            snak = claim.get("mainsnak", {})
            if snak.get("snaktype") != "value":
                continue
            value = snak.get("datavalue", {}).get("value")
            out.append(value["id"] if isinstance(value, dict) and "id" in value else value)
        return out

    types = _values("P31")
    return {
        "qid": entity.get("id", ""),
        "label": (labels.get("en") or labels.get("fr") or {}).get("value", ""),
        "types": types,
        "type_names": [ALLOWED_TYPES.get(t, t) for t in types],
        "existing_p9852": _values("P9852"),
        "websites": _values("P856"),
        "type_ok": any(t in ALLOWED_TYPES for t in types),
    }
