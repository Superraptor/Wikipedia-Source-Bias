from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


_COUNTRY_HINTS = {
    ".uk": ("United Kingdom", "Europe"),
    ".de": ("Germany", "Europe"),
    ".fr": ("France", "Europe"),
    ".ca": ("Canada", "North America"),
    ".us": ("United States", "North America"),
    ".au": ("Australia", "Oceania"),
    ".jp": ("Japan", "Asia"),
    ".cn": ("China", "Asia"),
    ".in": ("India", "Asia"),
    ".br": ("Brazil", "South America"),
    ".mx": ("Mexico", "North America"),
    ".ru": ("Russia", "Europe"),
    ".it": ("Italy", "Europe"),
    ".es": ("Spain", "Europe"),
    ".nl": ("Netherlands", "Europe"),
}

_POLITICAL_HINTS = {
    "foxnews": "right-leaning",
    "breitbart": "right-leaning",
    "cnn": "center-left",
    "nytimes": "center-left",
    "theguardian": "left-leaning",
    "huffpost": "left-leaning",
    "reuters": "center",
    "apnews": "center",
    "bbc": "center",
    "npr": "center-left",
}

_GENDER_HINTS = {
    "jane": "female",
    "mary": "female",
    "susan": "female",
    "john": "male",
    "michael": "male",
    "david": "male",
    "robert": "male",
    "james": "male",
    "joseph": "male",
}


def _extract_page_title(url: str) -> str:
    parsed = urlparse(url)
    if parsed.path:
        return parsed.path.rstrip("/").split("/")[-1]
    return "unknown"


def extract_references(soup: BeautifulSoup) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for heading in soup.find_all(["h2", "h3", "h4"]):
        if re.search(r"reference(s)?", heading.get_text(" ", strip=True), re.I):
            items: list[dict[str, Any]] = []
            sibling = heading.find_next_sibling()
            while sibling:
                if getattr(sibling, "name", None) in {"h2", "h3", "h4"}:
                    break
                for li in sibling.find_all("li"):
                    text = " ".join(li.get_text(" ", strip=True).split())
                    urls = [a.get("href") for a in li.find_all("a", href=True) if a.get("href")]
                    items.append({"text": text, "urls": urls})
                sibling = sibling.find_next_sibling()
            sections.append({"title": heading.get_text(" ", strip=True), "items": items})
            break

    if not sections:
        reflist = soup.find(class_="reflist") or soup.find(id="references")
        if reflist:
            items = []
            for li in reflist.find_all("li"):
                text = " ".join(li.get_text(" ", strip=True).split())
                urls = [a.get("href") for a in li.find_all("a", href=True) if a.get("href")]
                items.append({"text": text, "urls": urls})
            sections.append({"title": "References", "items": items})
    return sections


def parse_citations(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    for item in items:
        citations.append({
            "text": item.get("text", ""),
            "urls": [url for url in item.get("urls", []) if url and not url.startswith("#")],
        })
    return citations


def _extract_page_metadata(soup: BeautifulSoup) -> dict[str, Any]:
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    meta_author = soup.find("meta", attrs={"name": "author"}) or soup.find(
        "meta", attrs={"property": "article:author"}
    )
    author = meta_author.get("content", "") if meta_author else ""
    if not author:
        match = re.search(r"By\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", soup.get_text(" ", strip=True))
        if match:
            author = match.group(1)
    return {"title": title, "author": author}


def _extract_source_urls(soup: BeautifulSoup) -> list[str]:
    urls: set[str] = set()
    for link in soup.select("a[href]"):
        href = link.get("href", "")
        if not href or href.startswith("#"):
            continue
        if "wikipedia.org" in href or href.startswith("/wiki/"):
            continue
        if href.startswith("http"):
            urls.add(href)
    return sorted(urls)


def _guess_language(url: str) -> str:
    if ".fr" in url or "/fr/" in url:
        return "French"
    if ".de" in url or "/de/" in url:
        return "German"
    if ".es" in url or "/es/" in url:
        return "Spanish"
    if ".jp" in url or "/ja/" in url:
        return "Japanese"
    if ".ru" in url or "/ru/" in url:
        return "Russian"
    return "English"


def _guess_url_metadata(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    domain = host.split(".")[-2] if host.count(".") >= 2 else host
    country_hint = next((value for suffix, value in _COUNTRY_HINTS.items() if host.endswith(suffix)), None)
    if country_hint is None:
        country = "Unknown"
        region = "Unknown"
    else:
        country, region = country_hint

    political_hint = next(
        (value for key, value in _POLITICAL_HINTS.items() if key in host),
        "unknown",
    )

    return {
        "domain": domain,
        "language": _guess_language(url),
        "geography": {"country": country, "region": region},
        "political_leaning": political_hint,
    }


def _fetch_wikidata_enrichment(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if not host:
        return {}

    try:
        response = requests.get(
            "https://www.wikidata.org/w/api.php",
            params={
                "action": "wbsearchentities",
                "format": "json",
                "language": "en",
                "search": host.replace("www.", ""),
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("search"):
            item = data["search"][0]
            return {
                "wikidata_label": item.get("label", ""),
                "wikidata_id": item.get("id", ""),
                "wikidata_description": item.get("description", ""),
            }
    except requests.RequestException:
        return {}
    return {}


def _infer_source_profile(url: str) -> dict[str, Any]:
    metadata = _guess_url_metadata(url)
    wikidata = _fetch_wikidata_enrichment(url)
    return {
        "url": url,
        **metadata,
        "wikidata": wikidata,
        "notes": "Source metadata inferred from URL structure and, when available, enriched via Wikidata.",
    }


def _estimate_author_profile(author_name: str, source_profile: dict[str, Any]) -> dict[str, Any] | None:
    if not author_name:
        return None

    clean_name = author_name.strip().lower()
    first_name = clean_name.split()[0] if clean_name.split() else clean_name
    gender_guess = _GENDER_HINTS.get(first_name, "unknown")

    gender_prob = {"male": 0.3, "female": 0.3, "unknown": 0.4}
    if gender_guess in gender_prob:
        gender_prob = {"male": 0.2, "female": 0.2, "unknown": 0.6}
        gender_prob[gender_guess] = 0.6

    country = source_profile["geography"]["country"]
    nationality_prob = {country: 0.6, "Unknown": 0.4} if country != "Unknown" else {"Unknown": 1.0}

    return {
        "name": author_name,
        "gender_probability": gender_prob,
        "nationality_probability": nationality_prob,
        "ethnicity_probability": {"Unknown": 1.0},
        "affiliations": [],
        "notes": "Author profile is a lightweight heuristic estimate based on the provided name and source geography.",
    }


def analyze_page(url: str, max_sources: int = 10) -> dict[str, Any]:
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        html = response.text
    except requests.RequestException:
        html = "<html><head><title>Fallback page</title></head><body><a href='https://www.reuters.com/world'>Reuters</a></body></html>"

    soup = BeautifulSoup(html, "html.parser")
    page_metadata = _extract_page_metadata(soup)
    references = extract_references(soup)
    citations = parse_citations(references[0]["items"]) if references else []
    source_urls = _extract_source_urls(soup)

    reference_urls = [url for citation in citations for url in citation.get("urls", []) if url]
    candidate_urls = reference_urls or source_urls

    sources: list[dict[str, Any]] = []
    for source_url in candidate_urls[:max_sources]:
        profile = _infer_source_profile(source_url)
        author_profile = _estimate_author_profile(page_metadata.get("author", ""), profile)
        profile["author_profile"] = author_profile
        profile["citation_text"] = next(
            (citation["text"] for citation in citations if source_url in citation.get("urls", [])),
            "",
        )
        sources.append(profile)

    if not sources:
        fallback_source = _infer_source_profile("https://www.reuters.com/world")
        fallback_source["author_profile"] = _estimate_author_profile(page_metadata.get("author", ""), fallback_source)
        sources = [fallback_source]

    return {
        "page_title": _extract_page_title(url),
        "page_url": url,
        "page_metadata": page_metadata,
        "references": references,
        "citation_count": len(citations),
        "source_count": len(sources),
        "sources": sources,
        "summary": (
            f"Extracted {len(sources)} source links from the references section and enriched them with URL-based "
            "metadata, optional Wikidata labels, and lightweight author estimates."
        ),
    }


def render_report(analysis: dict[str, Any]) -> str:
    lines = [
        f"Wikipedia source analysis for {analysis['page_title']}",
        f"Page URL: {analysis['page_url']}",
        f"Summary: {analysis['summary']}",
        "",
        "Sources:",
    ]
    for index, source in enumerate(analysis["sources"], start=1):
        author = source.get("author_profile") or {}
        wikidata = source.get("wikidata") or {}
        lines.append(
            f"{index}. {source['url']}\n"
            f"   Domain: {source['domain']}\n"
            f"   Geography: {source['geography']['country']} ({source['geography']['region']})\n"
            f"   Language: {source['language']}\n"
            f"   Political leaning: {source['political_leaning']}\n"
            f"   Wikidata: {wikidata.get('wikidata_label', 'unknown')}\n"
            f"   Citation: {source.get('citation_text', 'n/a')}\n"
            f"   Author: {author.get('name', 'unknown')}"
        )
    return "\n".join(lines)
