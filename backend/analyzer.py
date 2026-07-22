# One canonical region vocabulary.
#
# The analyzer had two, and they collided in a single field: the TLD table
# emits "North America"/"South America"/"Middle East", while this country
# table used to emit "Americas". A .us source resolved by TLD and a US source
# resolved via Wikidata therefore landed in DIFFERENT buckets of the same
# distribution -- and neither "North America" nor "Middle East" had a
# translation, so the UI printed the raw key "region.North America".
#
# The finer split is kept rather than collapsed: for a tool about geographic
# bias, North vs South America is exactly the distinction worth seeing.
REGIONS = (
    "North America", "South America", "Europe", "Asia",
    "Africa", "Oceania", "Middle East", "Global",
)

# Values that older cached payloads or the domain database may still carry.
REGION_ALIASES = {
    "Americas": "Americas",   # too coarse to split without a country; kept
    "americas": "Americas",
    "Latin America": "South America",
    "MENA": "Middle East",
}

REGION_MAP = {
    "France": "Europe", "Germany": "Europe", "United Kingdom": "Europe",
    "Italy": "Europe", "Spain": "Europe", "Switzerland": "Europe",
    "Belgium": "Europe", "Netherlands": "Europe", "Luxembourg": "Europe",
    "Austria": "Europe", "Portugal": "Europe", "Ireland": "Europe",
    "Poland": "Europe", "Czech Republic": "Europe", "Hungary": "Europe",
    "Sweden": "Europe", "Norway": "Europe", "Denmark": "Europe",
    "Finland": "Europe", "Greece": "Europe", "Romania": "Europe",
    "Ukraine": "Europe", "Croatia": "Europe", "Serbia": "Europe",
    "Bulgaria": "Europe", "Slovakia": "Europe", "Slovenia": "Europe",
    "Estonia": "Europe", "Latvia": "Europe", "Lithuania": "Europe",
    "Iceland": "Europe", "Russia": "Europe", "European Union": "Europe",

    "United States": "North America", "Canada": "North America",
    "Mexico": "North America",

    "Brazil": "South America", "Argentina": "South America",
    "Colombia": "South America", "Chile": "South America",
    "Peru": "South America", "Venezuela": "South America",
    "Uruguay": "South America", "Cuba": "South America",

    "China": "Asia", "Japan": "Asia", "India": "Asia",
    "South Korea": "Asia", "Pakistan": "Asia", "Bangladesh": "Asia",
    "Indonesia": "Asia", "Vietnam": "Asia", "Thailand": "Asia",
    "Philippines": "Asia", "Malaysia": "Asia", "Singapore": "Asia",
    "Taiwan": "Asia", "Hong Kong": "Asia", "Kazakhstan": "Asia",

    "Israel": "Middle East", "Iran": "Middle East", "Iraq": "Middle East",
    "Lebanon": "Middle East", "Saudi Arabia": "Middle East",
    "Qatar": "Middle East", "United Arab Emirates": "Middle East",
    "Turkey": "Middle East",

    "Nigeria": "Africa", "Egypt": "Africa", "South Africa": "Africa",
    "Morocco": "Africa", "Algeria": "Africa", "Tunisia": "Africa",
    "Kenya": "Africa", "Ethiopia": "Africa", "Ghana": "Africa",
    "Senegal": "Africa", "Ivory Coast": "Africa", "Cameroon": "Africa",

    "Australia": "Oceania", "New Zealand": "Oceania",
}


def normalise_region(value):
    """Map a region string onto the canonical vocabulary, or None."""
    v = _clean(value)
    if v is None:
        return None
    if v in REGIONS:
        return v
    return REGION_ALIASES.get(v, v)



# A language-neutral key, NOT a display string. The API is consumed by a
# bilingual (fr/en) frontend, so emitting the French "Non-mappé" as data made
# French leak into English dashboards. The frontend translates this key.
UNMAPPED = "unmapped"

# Payloads produced before the switch to a language-neutral key still carry the
# old French display string, so it stays recognised as "missing".
_LEGACY_UNMAPPED = "Non-mappé"

# The analyzer emits the literal string "Unknown" when a heuristic finds
# nothing. Treated as a value rather than as "missing", it defeated the
# region lookup below: a source could carry country="France" and still show
# region="Unknown", because "Unknown" is truthy.
_MISSING = {
    None, "", "unknown", "Unknown", "UNKNOWN", "none", "None",
    UNMAPPED, _LEGACY_UNMAPPED,
}

# Generic TLDs carry no country signal, so a source on one is only mappable
# via Wikidata or the curated domain database.
_GENERIC_TLDS = (".com", ".net", ".org", ".info", ".biz", ".io", ".co")


def _clean(value):
    """Normalise the analyzer's several spellings of 'I don't know' to None."""
    if value in _MISSING:
        return None
    return value


def _norm_country(c):
    return _clean(c) or UNMAPPED


# Stable reason codes for `geography.note`. They are keys, not sentences: the
# frontend owns the wording and renders it in the reader's language. Adding a
# code here means adding `geography.note.<code>` to frontend/i18n/locales/*.
NOTE_GENERIC_TLD = "generic_tld"
NOTE_NO_COUNTRY_SIGNAL = "no_country_signal"
NOTE_REGION_MISSING = "region_missing"


def _geo_note(domain, country, region):
    """Explain why a source could not be placed.

    Without this an unmapped source was indistinguishable from a bug: you
    could see that it was unmapped, but not whether the domain gave no signal,
    or a lookup failed, or the region table simply lacked the country.

    Returns ``{"code": <reason code>, "params": {...}}`` or ``None``. The
    params carry the only values the sentence needs to interpolate, so the
    human wording lives in the frontend locale files instead of here.
    """
    if country == UNMAPPED:
        if domain and domain.lower().endswith(_GENERIC_TLDS):
            tld = "." + domain.rsplit(".", 1)[-1]
            return {"code": NOTE_GENERIC_TLD, "params": {"tld": tld}}
        return {"code": NOTE_NO_COUNTRY_SIGNAL, "params": {}}
    if region == UNMAPPED:
        return {"code": NOTE_REGION_MISSING, "params": {"country": country}}
    return None


def _norm_source(s):
    geo_in = s.get("geography") or {}
    country = _norm_country(_clean(geo_in.get("country")) or _clean(s.get("country")))
    # The country decides the region whenever it is known. Trusting the
    # analyzer's own region field let a .us source ("North America") and a
    # Wikidata-resolved US source ("Americas") occupy two buckets of one chart.
    # Only when the country is unknown do we fall back to whatever region the
    # analyzer managed to infer.
    region = (
        REGION_MAP.get(country)
        or normalise_region(geo_in.get("region"))
        or UNMAPPED
    )

    domain = s.get("domain", "")
    note = _geo_note(domain, country, region)
    geography = {"country": country, "region": region}
    if note:
        geography["note"] = note
        geography["unmapped"] = country == UNMAPPED

    return {
        "url": s.get("url", ""),
        "domain": domain,
        "source_type": s.get("source_type", "web_source"),
        "language": s.get("language", "unknown"),
        "geography": geography,
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
    # How many sources actually contributed a score. Without this the frontend
    # cannot tell "measured, and it was 0" from "never measured", and
    # neutrality (1 - subjectivity) turns a missing score into a perfect 100.
    return {
        "geography_distribution": geo,
        "political_leaning_distribution": lean,
        "author_gender_distribution": gender_dist,
        "average_subjectivity_score": avg_subj,
        "average_sensationalism_score": avg_sens,
        "opinion_source_count": opinion_count,
        "subjectivity_sample_count": len(subj_scores),
        "sensationalism_sample_count": len(sens_scores),
        "reliability_distribution": reliability,
        "source_type_distribution": source_type,
        "region_distribution": region,
        "language_distribution": language,
    }


# Fields the upstream analyzer's own aggregate does not always produce. When
# they are missing the frontend cannot distinguish absent from zero, so they
# are recomputed from the normalised sources rather than left undefined.
_DERIVED_KEYS = (
    "average_subjectivity_score",
    "average_sensationalism_score",
    "opinion_source_count",
    "subjectivity_sample_count",
    "sensationalism_sample_count",
)


def normalize_analysis(raw):
    sources = [_norm_source(s) for s in raw.get("sources", [])]
    agg = raw.get("aggregated_bias") or {}
    if not agg.get("geography_distribution"):
        agg = _aggregate(sources)
    else:
        computed = _aggregate(sources)
        agg = dict(agg)
        # Fill in what the upstream aggregate omits.
        for k in _DERIVED_KEYS:
            agg.setdefault(k, computed[k])
        # ALWAYS recompute the region distribution. _norm_source is now the
        # authority on regions (it derives them from the country), but the
        # upstream aggregate carries its own, older answer -- which is how
        # Brexit reported Australia and Belgium as region "Unknown" while
        # naming both countries correctly in the same payload.
        agg["region_distribution"] = computed["region_distribution"]
    return {
        "page_title": raw.get("page_title", ""),
        "page_url": raw.get("page_url", ""),
        "source_count": raw.get("source_count", len(sources)),
        "sources": sources,
        "aggregated_bias": agg,
    }
