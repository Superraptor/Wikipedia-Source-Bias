REGION_MAP = {
    "France": "Europe", "Germany": "Europe", "United Kingdom": "Europe",
    "Italy": "Europe", "Spain": "Europe", "Switzerland": "Europe",
    "United States": "Americas", "Canada": "Americas", "Mexico": "Americas",
    "Brazil": "Americas", "Argentina": "Americas",
    "China": "Asia", "Japan": "Asia", "India": "Asia", "Russia": "Asia",
    "South Korea": "Asia",
    "Nigeria": "Africa", "Egypt": "Africa", "South Africa": "Africa",
    "Australia": "Oceania", "New Zealand": "Oceania",
}


def _norm_country(c):
    if not c:
        return "Non-mappé"
    return c


def _norm_source(s):
    geo_in = s.get("geography") or {}
    country = _norm_country(geo_in.get("country") or s.get("country"))
    region = geo_in.get("region") or REGION_MAP.get(country, "Non-mappé")
    return {
        "url": s.get("url", ""),
        "domain": s.get("domain", ""),
        "source_type": s.get("source_type", "web_source"),
        "language": s.get("language", "unknown"),
        "geography": {"country": country, "region": region},
        "political_leaning": s.get("political_leaning", "unknown"),
        "reliability": s.get("reliability", "unknown"),
        "citation_text": s.get("citation_text", ""),
        "wikidata_publisher": s.get("wikidata_publisher", {}),
        "mbfc": s.get("mbfc", {}),
        "language_bias": s.get("language_bias", {}),
        "author_profiles": s.get("author_profiles", []),
    }


def _aggregate(sources):
    geo = {}
    lean = {}
    gender = {}
    reliability = {}
    source_type = {}
    region = {}
    language = {}
    opinion_count = 0
    subj_scores = []
    sens_scores = []
    for s in sources:
        c = s["geography"]["country"]
        geo.setdefault(c, {"count": 0, "percentage": 0.0})
        geo[c]["count"] += 1
        r = s["geography"]["region"]
        region.setdefault(r, {"count": 0, "percentage": 0.0})
        region[r]["count"] += 1
        l = s.get("political_leaning", "unknown")
        lean.setdefault(l, {"count": 0, "percentage": 0.0})
        lean[l]["count"] += 1
        rel = s.get("reliability", "unknown")
        reliability.setdefault(rel, {"count": 0, "percentage": 0.0})
        reliability[rel]["count"] += 1
        st = s.get("source_type", "web_source")
        source_type.setdefault(st, {"count": 0, "percentage": 0.0})
        source_type[st]["count"] += 1
        lang = s.get("language", "unknown")
        language.setdefault(lang, {"count": 0, "percentage": 0.0})
        language[lang]["count"] += 1
        lb = s.get("language_bias") or {}
        if lb.get("is_opinion"):
            opinion_count += 1
        if "subjectivity_score" in lb and lb["subjectivity_score"] is not None:
            subj_scores.append(lb["subjectivity_score"])
        if "sensationalism_score" in lb and lb["sensationalism_score"] is not None:
            sens_scores.append(lb["sensationalism_score"])
        for ap in s.get("author_profiles", []) or []:
            g = ap.get("gender", "unknown")
            gender.setdefault(g, 0)
            gender[g] += 1
    n = len(sources) or 1
    for d in (geo, lean, reliability, source_type, region, language):
        for k, v in d.items():
            v["percentage"] = round(100.0 * v["count"] / n, 1)
    gender_total = sum(gender.values()) or 1
    gender_dist = {k: {"count": v, "percentage": round(100.0 * v / gender_total, 1)} for k, v in gender.items()}
    avg_subj = round(sum(subj_scores) / len(subj_scores), 3) if subj_scores else 0.0
    avg_sens = round(sum(sens_scores) / len(sens_scores), 3) if sens_scores else 0.0
    return {
        "geography_distribution": geo,
        "political_leaning_distribution": lean,
        "author_gender_distribution": gender_dist,
        "average_subjectivity_score": avg_subj,
        "average_sensationalism_score": avg_sens,
        "opinion_source_count": opinion_count,
        "reliability_distribution": reliability,
        "source_type_distribution": source_type,
        "region_distribution": region,
        "language_distribution": language,
    }


def normalize_analysis(raw):
    sources = [_norm_source(s) for s in raw.get("sources", [])]
    agg = raw.get("aggregated_bias") or {}
    if not agg.get("geography_distribution"):
        agg = _aggregate(sources)
    return {
        "page_title": raw.get("page_title", ""),
        "page_url": raw.get("page_url", ""),
        "source_count": raw.get("source_count", len(sources)),
        "sources": sources,
        "aggregated_bias": agg,
    }
