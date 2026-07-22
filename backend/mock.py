"""Mock dataset for local development and demo deployments.

This module is a **fallback only**: it is used when the upstream
`wikipedia_source_bias` package is NOT installed (i.e. local dev without
the repo amont, or a demo server without MariaDB cache pre-populated).

On Toolforge with the upstream repo installed and `populate_cache.py` run,
the real analysis flow is used and this module is never reached.

The data for the 4 corpus articles matches the spec §"Exemple de données"
(Emmanuel Macron: 881 sources, 84.7% France, etc.).
"""

import random

CORPUS_PROFILES = {
    "https://fr.wikipedia.org/wiki/Emmanuel_Macron": {
        "page_title": "Emmanuel_Macron",
        "source_count": 881,
        "country_dist": [
            ("France", 746), ("United States", 18), ("United Kingdom", 8),
            ("Switzerland", 5), ("Germany", 3), ("unmapped", 78),
            ("Italy", 10), ("Spain", 8), ("Belgium", 5),
        ],
        "lean_dist": [
            ("unknown", 705), ("neutral", 78), ("conservatism", 44),
            ("progressivism", 27), ("center", 18), ("left", 9),
        ],
        "reliability_dist": [
            ("medium", 441), ("high", 220), ("academic", 132),
            ("unknown", 88),
        ],
        "gender_dist": {"male": 65, "female": 25, "unknown": 10},
        "avg_subjectivity": 0.18,
        "avg_sensationalism": 0.08,
        "opinion_count": 23,
        "domains": [
            "lemonde.fr", "lefigaro.fr", "liberation.fr", "lesechos.fr",
            "lepoint.fr", "nouvelobs.com", "franceinter.fr", "rfi.fr",
            "elysee.fr", "gouvernement.fr", "assemblee-nationale.fr",
            "institutmontaigne.org", "sciencespo.fr", "cairn.info",
            "nytimes.com", "theguardian.com", "bbc.com", "reuters.com",
            "ft.com", "nzz.ch", "spiegel.de", "repubblica.it", "elpais.com",
        ],
    },
    "https://de.wikipedia.org/wiki/Angela_Merkel": {
        "page_title": "Angela_Merkel",
        "source_count": 412,
        "country_dist": [
            ("Germany", 298), ("United States", 24), ("United Kingdom", 14),
            ("France", 12), ("Switzerland", 8), ("Italy", 6),
            ("unmapped", 35), ("Austria", 8), ("Belgium", 7),
        ],
        "lean_dist": [
            ("unknown", 330), ("neutral", 41), ("conservatism", 20),
            ("progressivism", 12), ("center", 9),
        ],
        "reliability_dist": [
            ("medium", 185), ("high", 103), ("academic", 82), ("unknown", 42),
        ],
        "gender_dist": {"female": 58, "male": 32, "unknown": 10},
        "avg_subjectivity": 0.15,
        "avg_sensationalism": 0.06,
        "opinion_count": 11,
        "domains": [
            "spiegel.de", "faz.net", "sueddeutsche.de", "zeit.de",
            "handelsblatt.com", "tagesschau.de", "dw.com", "bild.de",
            "bundestag.de", "bundesregierung.de", "nytimes.com",
            "theguardian.com", "bbc.com", "reuters.com", "ft.com",
            "lemonde.fr", "nzz.ch", "wikipedia.org",
        ],
    },
    "https://en.wikipedia.org/wiki/Brexit": {
        "page_title": "Brexit",
        "source_count": 537,
        "country_dist": [
            ("United Kingdom", 389), ("United States", 42),
            ("Germany", 18), ("France", 16), ("Ireland", 12),
            ("Italy", 8), ("Spain", 6), ("unmapped", 38),
            ("Belgium", 8),
        ],
        "lean_dist": [
            ("unknown", 386), ("conservatism", 54), ("neutral", 42),
            ("progressivism", 30), ("left", 15), ("right", 10),
        ],
        "reliability_dist": [
            ("medium", 241), ("high", 161), ("academic", 81), ("unknown", 54),
        ],
        "gender_dist": {"male": 58, "female": 34, "unknown": 8},
        "avg_subjectivity": 0.24,
        "avg_sensationalism": 0.12,
        "opinion_count": 38,
        "domains": [
            "bbc.com", "theguardian.com", "ft.com", "telegraph.co.uk",
            "thesun.co.uk", "dailymail.co.uk", "independent.co.uk",
            "express.co.uk", "metro.co.uk", "reuters.com", "nytimes.com",
            "politico.eu", "europa.eu", "parliament.uk", "gov.uk",
            "spiegel.de", "lemonde.fr", "irishtimes.com", "ft.com",
        ],
    },
    "https://fr.wikipedia.org/wiki/Guerre_d%27Alg%C3%A9rie": {
        "page_title": "Guerre_d'Alg%C3%A9rie",
        "source_count": 642,
        "country_dist": [
            ("France", 478), ("Algeria", 38), ("United States", 22),
            ("United Kingdom", 14), ("Germany", 8), ("Italy", 6),
            ("unmapped", 58), ("Switzerland", 10), ("Belgium", 8),
        ],
        "lean_dist": [
            ("unknown", 498), ("neutral", 58), ("conservatism", 38),
            ("progressivism", 28), ("left", 20),
        ],
        "reliability_dist": [
            ("medium", 309), ("academic", 148), ("high", 121), ("unknown", 64),
        ],
        "gender_dist": {"male": 72, "female": 18, "unknown": 10},
        "avg_subjectivity": 0.21,
        "avg_sensationalism": 0.09,
        "opinion_count": 19,
        "domains": [
            "lemonde.fr", "lefigaro.fr", "liberation.fr", "lesechos.fr",
            "humanite.fr", "lhistoire.fr", "cairn.info", "persee.fr",
            "jstor.org", "books.google.com", "el-watan.com",
            "tsa-algerie.com", "nytimes.com", "bbc.com", "reuters.com",
            "assemblye-nationale.fr", "senat.fr", "culture.gouv.fr",
        ],
    },
}

GENERIC_DOMAINS = [
    "wikipedia.org", "nytimes.com", "bbc.com", "reuters.com",
    "theguardian.com", "lemonde.fr", "spiegel.de",
]


def _build_sources(profile, rng):
    n = profile["source_count"]
    countries = []
    for c, cnt in profile["country_dist"]:
        countries.extend([c] * cnt)
    countries = countries[:n]
    while len(countries) < n:
        countries.append("unmapped")
    rng.shuffle(countries)

    leans = []
    for l, cnt in profile["lean_dist"]:
        leans.extend([l] * cnt)
    leans = leans[:n]
    while len(leans) < n:
        leans.append("unknown")
    rng.shuffle(leans)

    rels = []
    for r, cnt in profile["reliability_dist"]:
        rels.extend([r] * cnt)
    rels = rels[:n]
    while len(rels) < n:
        rels.append("unknown")
    rng.shuffle(rels)

    opinion_idx = set(rng.sample(range(n), profile["opinion_count"]))
    domains = profile["domains"]

    sources = []
    for i in range(n):
        is_op = i in opinion_idx
        subj = round(rng.uniform(0.05, 0.45), 3) if is_op else round(rng.uniform(0.02, 0.22), 3)
        sources.append({
            "url": f"https://{rng.choice(domains)}/article-{i}",
            "domain": rng.choice(domains),
            "source_type": rng.choice(["web_source", "book", "news_source", "academic"]),
            "language": "unknown",
            "country": countries[i],
            "political_leaning": leans[i],
            "reliability": rels[i],
            "citation_text": "",
            "wikidata_publisher": {} if rng.random() > 0.15 else {
                "qid": f"Q{rng.randint(1000, 99999)}",
                "label": rng.choice(domains).split(".")[0].capitalize(),
            },
            "mbfc": {} if rng.random() > 0.2 else {
                "factual": rng.choice(["high", "mixed", "mostly factual"]),
                "bias": leans[i] if leans[i] != "unknown" else "center",
            },
            "language_bias": {
                "subjectivity_score": subj,
                "sensationalism_score": round(rng.uniform(0.01, 0.15), 3),
                "is_opinion": is_op,
                "sentiment": rng.choice(["neutral", "neutral", "neutral", "positive", "negative"]),
            },
            "author_profiles": [] if rng.random() > 0.3 else [{
                "name": f"Author {rng.randint(1, 200)}",
                "gender": rng.choices(
                    ["male", "female", "unknown"],
                    weights=[profile["gender_dist"].get("male", 0),
                             profile["gender_dist"].get("female", 0),
                             profile["gender_dist"].get("unknown", 0)],
                )[0],
                "author_type": "human",
            }],
        })
    return sources


def _build_aggregated(profile):
    n = profile["source_count"]
    geo = {}
    for c, cnt in profile["country_dist"]:
        geo[c] = {"count": cnt, "percentage": round(100.0 * cnt / n, 1)}

    lean = {}
    for l, cnt in profile["lean_dist"]:
        lean[l] = {"count": cnt, "percentage": round(100.0 * cnt / n, 1)}

    rel = {}
    for r, cnt in profile["reliability_dist"]:
        rel[r] = {"count": cnt, "percentage": round(100.0 * cnt / n, 1)}

    gd = profile["gender_dist"]
    gt = sum(gd.values()) or 1
    gender = {k: {"count": v, "percentage": round(100.0 * v / gt, 1)} for k, v in gd.items()}

    return {
        "geography_distribution": geo,
        "political_leaning_distribution": lean,
        "author_gender_distribution": gender,
        "average_subjectivity_score": profile["avg_subjectivity"],
        "average_sensationalism_score": profile["avg_sensationalism"],
        "opinion_source_count": profile["opinion_count"],
        "reliability_distribution": rel,
        "source_type_distribution": {},
        "region_distribution": {},
        "language_distribution": {},
    }


def mock_analysis(url):
    """Return raw analysis data (pre-normalization) for a URL.

    For the 4 corpus URLs, returns spec-matching demo data.
    For any other URL, returns a small generic dataset so the dashboard renders.
    """
    profile = CORPUS_PROFILES.get(url)
    if profile is None:
        return _generic_analysis(url)
    rng = random.Random(hash(url) % 2**31)
    return {
        "page_title": profile["page_title"],
        "page_url": url,
        "source_count": profile["source_count"],
        "sources": _build_sources(profile, rng),
        "aggregated_bias": _build_aggregated(profile),
    }


def _generic_analysis(url):
    rng = random.Random(hash(url) % 2**31)
    n = rng.randint(20, 60)
    countries = rng.choices(
        ["France", "United States", "United Kingdom", "Germany", "Italy",
         "unmapped"],
        weights=[40, 25, 15, 8, 5, 7],
        k=n,
    )
    sources = []
    for i in range(n):
        c = countries[i]
        sources.append({
            "url": f"https://{rng.choice(GENERIC_DOMAINS)}/ref-{i}",
            "domain": rng.choice(GENERIC_DOMAINS),
            "source_type": "web_source",
            "language": "unknown",
            "country": c,
            "political_leaning": rng.choices(
                ["unknown", "neutral", "conservatism", "progressivism"],
                weights=[70, 15, 8, 7])[0],
            "reliability": rng.choices(
                ["medium", "high", "academic", "unknown"],
                weights=[45, 25, 15, 15])[0],
            "citation_text": "",
            "wikidata_publisher": {},
            "mbfc": {},
            "language_bias": {
                "subjectivity_score": round(rng.uniform(0.05, 0.3), 3),
                "sensationalism_score": round(rng.uniform(0.01, 0.1), 3),
                "is_opinion": rng.random() < 0.05,
                "sentiment": "neutral",
            },
            "author_profiles": [],
        })
    title = url.rsplit("/", 1)[-1] if "/" in url else url
    return {
        "page_title": title,
        "page_url": url,
        "source_count": n,
        "sources": sources,
        "aggregated_bias": {},
    }
