from __future__ import annotations

import json
import os
import re
import sys
import time
from typing import Any
from urllib.parse import urlparse, parse_qs

import math
import requests
from bs4 import BeautifulSoup

from .cachestore import get_store
from . import ratelimit
from .urlnorm import canonical_page_url
from .provenance import METHOD_VERSION, extract_revision, permalink
from concurrent.futures import ThreadPoolExecutor, as_completed


def _load_env_tokens():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k in ("HF_TOKEN", "HUGGINGFACE_TOKEN", "HF_API_KEY"):
                            os.environ["HF_TOKEN"] = v
                            os.environ["HUGGINGFACE_CO_API_KEY"] = v
        except Exception:
            pass

_load_env_tokens()

from .heuristics_data import (
    DOMAIN_BIAS_DATABASE,
    TLD_GEOGRAPHY_MAP,
    FIRST_NAME_GENDER,
    SURNAME_ORIGIN_PATTERNS,
    SUBJECTIVE_LOADED_WORDS,
    OPINION_EDITORIAL_INDICATORS,
    MULTILINGUAL_LOADED_WORDS,
    MULTILINGUAL_OPINION_INDICATORS,
    COUNTRY_POPULATION_DATA,
    COUNTRY_NEIGHBORS,
)


def _extract_page_title(url: str) -> str:
    parsed = urlparse(url)
    if parsed.path:
        return parsed.path.rstrip("/").split("/")[-1]
    return "unknown"


def extract_references(soup: BeautifulSoup) -> list[dict[str, Any]]:
    ref_containers = []
    
    # 1. Look for ol elements with class "references" (most standard)
    ref_containers.extend(soup.find_all("ol", class_="references"))
    
    # 2. Look for elements with class reflist or refbegin
    for c in soup.find_all(class_=["reflist", "refbegin"]):
        if not c.find("ol", class_="references"):
            ref_containers.append(c)
            
    # 3. Heading fallback (for non-standard or foreign languages)
    heading_patterns = re.compile(
        r"(reference|note|source|bibliography|einzelnachweis|referencia|refér)", re.I
    )
    for heading in soup.find_all(["h2", "h3", "h4"]):
        if heading_patterns.search(heading.get_text(" ", strip=True)):
            sibling = heading.find_next_sibling()
            while sibling:
                if getattr(sibling, "name", None) in {"h2", "h3", "h4"}:
                    break
                if sibling.name == "ol" or sibling.find("ol") or sibling.find("li"):
                    if sibling not in ref_containers:
                        ref_containers.append(sibling)
                sibling = sibling.find_next_sibling()
                
    items: list[dict[str, Any]] = []
    seen_texts: set[str] = set()
    
    for container in ref_containers:
        for li in container.find_all("li"):
            li_copy = BeautifulSoup(str(li), "html.parser").find("li")
            if not li_copy:
                continue
            for backlink in li_copy.find_all(class_="mw-cite-backlink"):
                backlink.decompose()
                
            ref_text_el = li_copy.find(class_="reference-text")
            if ref_text_el:
                text = " ".join(ref_text_el.get_text(" ", strip=True).split())
            else:
                text = " ".join(li_copy.get_text(" ", strip=True).split())
                
            text = re.sub(r"^\^\s*", "", text).strip()
            if not text:
                continue
                
            urls = []
            for a in li_copy.find_all("a", href=True):
                href = a.get("href")
                if href and not href.startswith("#") and "wikipedia.org" not in href and not href.startswith("/wiki/"):
                    if href.startswith("http"):
                        urls.append(href)
                        
            seen_urls = set()
            dedup_urls = []
            for u in urls:
                if u not in seen_urls:
                    seen_urls.add(u)
                    dedup_urls.append(u)
                    
            if text not in seen_texts:
                seen_texts.add(text)
                items.append({"text": text, "urls": dedup_urls})
                
    return [{"title": "References", "items": items}] if items else []


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


def unwrap_archive_url(url: str) -> str:
    if not url:
        return url
    
    # 1. Wayback Machine (archive.org/web/...)
    wayback_match = re.search(r'^https?://(?:web\.)?archive\.org/web/\d+[a-z]*_?/(https?://.+)$', url, re.I)
    if wayback_match:
        return wayback_match.group(1)
        
    # 2. Long archive.is / archive.today style URLs
    archive_is_long_match = re.search(r'^https?://archive\.(?:is|today|li|vn|fo|md|ph)/(?:\d+|[a-zA-Z0-9_\-]+)/(https?://.+)$', url, re.I)
    if archive_is_long_match:
        return archive_is_long_match.group(1)
        
    return url


def is_archive_domain(domain: str) -> bool:
    dom = domain.lower()
    if dom.startswith("www."):
        dom = dom[4:]
    return dom in {
        "archive.is", "archive.today", "archive.li", "archive.vn", 
        "archive.fo", "archive.md", "archive.ph", "archive.org", "web.archive.org"
    }


def extract_original_url_from_archive_html(html: str) -> str | None:
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    
    for meta in soup.find_all("meta"):
        prop = meta.get("property", "").lower()
        name = meta.get("name", "").lower()
        content = meta.get("content", "")
        if prop in {"og:url", "twitter:url"} or name in {"og:url", "twitter:url"}:
            if content and not any(x in content for x in ["archive.is", "archive.today", "archive.org", "archive.ph", "archive.li", "archive.vn", "archive.fo", "archive.md"]):
                return content
                
    input_q = soup.find("input", {"id": "q"}) or soup.find("input", {"name": "q"})
    if input_q and input_q.get("value"):
        val = input_q["value"].strip()
        if val.startswith("http"):
            return val
            
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http") and not any(x in href for x in ["archive.is", "archive.today", "archive.org", "archive.ph", "archive.li", "archive.vn", "archive.fo", "archive.md"]):
            if "original" in a.get_text().lower() or "source" in a.get_text().lower() or a.get("id") == "original":
                return href
                
    urls = re.findall(r'https?://[^\s"\'>]+', html)
    for u in urls:
        if not any(x in u for x in ["archive.is", "archive.today", "archive.org", "archive.ph", "archive.li", "archive.vn", "archive.fo", "archive.md"]):
            return u
            
    return None


def _resolve_archive_url_content(url: str, skip_rate_limiting: bool = False) -> str:
    parsed = urlparse(url)
    if not is_archive_domain(parsed.netloc):
        return url
        
    if skip_rate_limiting:
        return url
        
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = _polite_get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            orig = extract_original_url_from_archive_html(response.text)
            if orig:
                return orig
    except Exception:
        pass
    return url


def _fetch_wikidata_enrichment(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if not host:
        return {}

    if host in _wd_enrichment_cache:
        return _wd_enrichment_cache[host]

    result = {}
    try:
        response = _robust_wikidata_get(
            "https://www.wikidata.org/w/api.php",
            params={
                "action": "wbsearchentities",
                "format": "json",
                "language": "en",
                "search": host,
            },
            headers={"User-Agent": "WikipediaSourcesBias/0.1 (mailto:clair.kronk@gmail.com)"},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("search"):
            item = data["search"][0]
            result = {
                "wikidata_label": item.get("label", ""),
                "wikidata_id": item.get("id", ""),
                "wikidata_description": item.get("description", ""),
            }
    except requests.RequestException:
        pass

    _wd_enrichment_cache[host] = result
    _cache_put("wikidata_enrichment_cache.json", host, result)
    return result


def _extract_authors_from_citation(text: str) -> list[str]:
    by_matches = re.findall(
        r"\b[bB][yY]\s+([A-Z][a-zA-Z'\-]+\s+[A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+)*)",
        text
    )
    if by_matches:
        valid_authors = []
        for match in by_matches:
            if not any(
                stop in match.lower()
                for stop in ["press", "journal", "university", "associated", "reuters", "times", "post", "bbc", "news", "society"]
            ):
                valid_authors.append(match.strip())
        if valid_authors:
            return valid_authors

    start_match = re.match(r"^([A-Z][a-zA-Z'\-]+,\s+[A-Z][a-zA-Z'\-]*\.?(?:\s+[A-Z]\.?)?)", text)
    if start_match:
        name = start_match.group(1).strip()
        if "," in name:
            parts = name.split(",")
            first_name = parts[1].strip()
            cleaned_words = [w.rstrip(".") if (w.endswith(".") and len(w) > 2) else w for w in first_name.split()]
            first_name = " ".join(cleaned_words)
            name = f"{first_name} {parts[0].strip()}"
        return [name]

    first_last_match = re.match(r"^([A-Z][a-zA-Z'\-]+\s+[A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+)?)(?=\.|\s+\(|,)", text)
    if first_last_match:
        name = first_last_match.group(1).strip()
        if not any(
            stop in name.lower()
            for stop in ["press", "journal", "university", "associated", "reuters", "times", "post", "bbc", "news", "the", "national", "american", "editor"]
        ):
            return [name]

    return []


def _extract_isbn(text: str) -> str | None:
    match = re.search(r"\b(?:ISBN(?:-1[03])?:?\s*)?((?:97[89])?[- 0-9xX]{10,16})\b", text)
    if not match:
        return None
    cleaned = re.sub(r"[^0-9xX]", "", match.group(1))
    if len(cleaned) in (10, 13):
        return cleaned
    return None


def _extract_google_books_id(url: str) -> str | None:
    parsed = urlparse(url)
    if "books.google" in parsed.netloc:
        qs = parse_qs(parsed.query)
        ids = qs.get("id")
        if ids:
            return ids[0]
    return None


def _extract_oclc(text_or_url: str) -> str | None:
    url_match = re.search(r"worldcat\.org/(?:oclc|title)/(\d+)", text_or_url, re.I)
    if url_match:
        return url_match.group(1)
    text_match = re.search(r"\boclc\b[:#\s]*(\d+)", text_or_url, re.I)
    if text_match:
        return text_match.group(1)
    return None


def _extract_doi(text_or_url: str) -> str | None:
    from urllib.parse import unquote
    unquoted = unquote(text_or_url)
    url_match = re.search(r"doi\.org/(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", unquoted, re.I)
    if url_match:
        return url_match.group(1)
    text_match = re.search(r"\bdoi\b[:\s]*(10\.\d{4,9}/[-._;()/:a-z0-9]+)", unquoted, re.I)
    if text_match:
        return text_match.group(1)
    return None


def _robust_wikidata_get(url: str, params: dict[str, Any], headers: dict[str, Any], timeout: int = 10) -> requests.Response:
    # Small mandatory delay to be respectful of Wikidata's servers
    time.sleep(0.3)
    
    retries = 3
    backoff = 2.0
    for attempt in range(retries):
        try:
            response = _polite_get(url, params=params, headers=headers, timeout=timeout)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                wait_time = int(retry_after) if retry_after and retry_after.isdigit() else backoff
                sys.stderr.write(f"\n[Wikidata 429] Rate limited. Retrying in {wait_time}s...\n")
                sys.stderr.flush()
                time.sleep(wait_time)
                backoff *= 2
                continue
            return response
        except requests.RequestException as e:
            if attempt == retries - 1:
                raise e
            time.sleep(backoff)
            backoff *= 2
            
    return _polite_get(url, params=params, headers=headers, timeout=timeout)


def _query_wikidata_sparql(query: str) -> list[dict[str, Any]]:
    url = "https://query.wikidata.org/sparql"
    headers = {
        "User-Agent": "WikipediaSourcesBias/0.1 (https://github.com/OpenAI/wikipedia-sources-bias)",
        "Accept": "application/sparql-results+json"
    }
    response = _robust_wikidata_get(url, params={"query": query, "format": "json"}, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()
    bindings = data.get("results", {}).get("bindings", [])
    
    results = []
    for bind in bindings:
        row = {}
        for key, val in bind.items():
            row[key] = val.get("value", "")
        results.append(row)
    return results


def _fetch_wikidata_author(author_name: str) -> dict[str, Any]:
    if author_name in _wd_author_cache:
        return _wd_author_cache[author_name]

    try:
        response = _robust_wikidata_get(
            "https://www.wikidata.org/w/api.php",
            params={
                "action": "wbsearchentities",
                "format": "json",
                "language": "en",
                "search": author_name,
            },
            headers={"User-Agent": "WikipediaSourcesBias/0.1 (mailto:clair.kronk@gmail.com)"},
            timeout=5,
        )
        response.raise_for_status()
        search_data = response.json()
        if not search_data.get("search"):
            _wd_author_cache[author_name] = {}
            _cache_put("wikidata_author_cache.json", author_name, {})
            return {}
            
        entity_id = search_data["search"][0]["id"]
        
        query = f"""
        SELECT ?genderLabel ?citizenshipLabel ?partyLabel ?occupationLabel ?employerLabel ?employerCountryLabel WHERE {{
          BIND(wd:{entity_id} AS ?author)
          OPTIONAL {{ ?author wdt:P21 ?gender. }}
          OPTIONAL {{ ?author wdt:P27 ?citizenship. }}
          OPTIONAL {{ ?author wdt:P102 ?party. }}
          OPTIONAL {{ ?author wdt:P106 ?occupation. }}
          OPTIONAL {{ 
            ?author wdt:P108 ?employer.
            OPTIONAL {{ ?employer wdt:P17 ?employerCountry. }}
          }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """
        rows = _query_wikidata_sparql(query)
        
        gender = set()
        citizenship = set()
        party = set()
        occupation = set()
        employers = {}
        
        for r in rows:
            if r.get("genderLabel"): gender.add(r["genderLabel"])
            if r.get("citizenshipLabel"): citizenship.add(r["citizenshipLabel"])
            if r.get("partyLabel"): party.add(r["partyLabel"])
            if r.get("occupationLabel"): occupation.add(r["occupationLabel"])
            
            emp_name = r.get("employerLabel")
            if emp_name:
                emp_country = r.get("employerCountryLabel") or "Unknown"
                employers[emp_name] = emp_country
            
        result = {
            "wikidata_id": entity_id,
            "wikidata_name": search_data["search"][0].get("label", author_name),
            "gender": list(gender)[0] if gender else None,
            "citizenships": sorted(list(citizenship)),
            "political_parties": sorted(list(party)),
            "occupations": sorted(list(occupation)),
            "employers": [{"name": k, "country": v} for k, v in employers.items()],
        }
        
        _wd_author_cache[author_name] = result
        _cache_put("wikidata_author_cache.json", author_name, result)
        return result
    except Exception:
        return {}


def _fetch_wikidata_publisher(domain: str) -> dict[str, Any]:
    if domain in _wd_publisher_cache:
        return _wd_publisher_cache[domain]

    entity_id = None
    headers = {
        "User-Agent": "WikipediaSourcesBias/0.1 (mailto:clair.kronk@gmail.com)"
    }
    
    try:
        # 1. Try VALUES exact URI matching (extremely fast, avoids timeouts completely)
        query_exact = f"""
        SELECT ?publisher ?publisherLabel ?countryLabel ?politicalLeaningLabel ?politicalIdeologyLabel ?ownerLabel ?instanceOfLabel ?mbfcId WHERE {{
          VALUES ?website {{
            <http://{domain}/> <https://{domain}/> <http://www.{domain}/> <https://www.{domain}/>
            <http://{domain}> <https://{domain}> <http://www.{domain}> <https://www.{domain}>
          }}
          ?publisher wdt:P856 ?website.
          OPTIONAL {{ ?publisher wdt:P17 ?country. }}
          OPTIONAL {{ ?publisher wdt:P1387 ?politicalLeaning. }}
          OPTIONAL {{ ?publisher wdt:P1142 ?politicalIdeology. }}
          OPTIONAL {{ ?publisher wdt:P127 ?owner. }}
          OPTIONAL {{ ?publisher wdt:P31 ?instanceOf. }}
          OPTIONAL {{ ?publisher wdt:P9852 ?mbfcId. }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """
        rows = _query_wikidata_sparql(query_exact)
        
        # 2. Fall back to search API if VALUES lookup fails
        if not rows:
            try:
                response = _robust_wikidata_get(
                    "https://www.wikidata.org/w/api.php",
                    params={
                        "action": "wbsearchentities",
                        "format": "json",
                        "language": "en",
                        "search": domain,
                    },
                    headers=headers,
                    timeout=5,
                )
                response.raise_for_status()
                search_data = response.json()
                if search_data.get("search"):
                    entity_id = search_data["search"][0]["id"]
            except Exception:
                pass

            if entity_id:
                query_direct = f"""
                SELECT ?publisher ?publisherLabel ?countryLabel ?politicalLeaningLabel ?politicalIdeologyLabel ?ownerLabel ?instanceOfLabel ?mbfcId WHERE {{
                  BIND(wd:{entity_id} AS ?publisher)
                  OPTIONAL {{ ?publisher wdt:P17 ?country. }}
                  OPTIONAL {{ ?publisher wdt:P1387 ?politicalLeaning. }}
                  OPTIONAL {{ ?publisher wdt:P1142 ?politicalIdeology. }}
                  OPTIONAL {{ ?publisher wdt:P127 ?owner. }}
                  OPTIONAL {{ ?publisher wdt:P31 ?instanceOf. }}
                  OPTIONAL {{ ?publisher wdt:P9852 ?mbfcId. }}
                  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
                }}
                """
                rows = _query_wikidata_sparql(query_direct)

        # 3. Hard fallback to un-indexed regex scan (timeout-prone, last resort)
        if not rows:
            query_fallback = f"""
            SELECT ?publisher ?publisherLabel ?countryLabel ?politicalLeaningLabel ?politicalIdeologyLabel ?ownerLabel ?instanceOfLabel ?mbfcId WHERE {{
              ?publisher wdt:P856 ?website.
              FILTER(regex(str(?website), "https?://(www\\\\.)?{domain}(/|$)", "i")).
              OPTIONAL {{ ?publisher wdt:P17 ?country. }}
              OPTIONAL {{ ?publisher wdt:P1387 ?politicalLeaning. }}
              OPTIONAL {{ ?publisher wdt:P1142 ?politicalIdeology. }}
              OPTIONAL {{ ?publisher wdt:P127 ?owner. }}
              OPTIONAL {{ ?publisher wdt:P31 ?instanceOf. }}
              OPTIONAL {{ ?publisher wdt:P9852 ?mbfcId. }}
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
            }} LIMIT 10
            """
            rows = _query_wikidata_sparql(query_fallback)

        result = {}
        if rows:
            pub_id = entity_id or ""
            pub_name = ""
            countries = set()
            political_leanings = set()
            political_ideologies = set()
            owners = set()
            types = set()
            mbfc_ids = set()
            
            for r in rows:
                if r.get("publisher"):
                    pub_id = r["publisher"].split("/")[-1]
                if r.get("publisherLabel"):
                    pub_name = r["publisherLabel"]
                if r.get("countryLabel"):
                    countries.add(r["countryLabel"])
                if r.get("politicalLeaningLabel"):
                    political_leanings.add(r["politicalLeaningLabel"])
                if r.get("politicalIdeologyLabel"):
                    political_ideologies.add(r["politicalIdeologyLabel"])
                if r.get("ownerLabel"):
                    owners.add(r["ownerLabel"])
                if r.get("instanceOfLabel"):
                    types.add(r["instanceOfLabel"])
                if r.get("mbfcId"):
                    mbfc_ids.add(r["mbfcId"])
                    
            result = {
                "wikidata_id": pub_id,
                "wikidata_name": pub_name,
                "countries": sorted(list(countries)),
                "political_leanings": sorted(list(political_leanings)),
                "political_ideologies": sorted(list(political_ideologies)),
                "owners": sorted(list(owners)),
                "types": sorted(list(types)),
                "mbfc_id": list(mbfc_ids)[0] if mbfc_ids else None,
            }

        _wd_publisher_cache[domain] = result
        _cache_put("wikidata_publisher_cache.json", domain, result)
        return result
    except Exception:
        return {}


def _fetch_wikidata_book(isbn: str) -> dict[str, Any]:
    try:
        query = f"""
        SELECT ?book ?bookLabel ?publisherLabel ?authorLabel ?pubDate ?countryLabel WHERE {{
          {{ ?book wdt:P212 "{isbn}". }} UNION {{ ?book wdt:P957 "{isbn}". }}
          OPTIONAL {{ ?book wdt:P123 ?publisher. }}
          OPTIONAL {{ ?book wdt:P50 ?author. }}
          OPTIONAL {{ ?book wdt:P577 ?pubDate. }}
          OPTIONAL {{ ?book wdt:P495 ?country. }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }} LIMIT 5
        """
        rows = _query_wikidata_sparql(query)
        if not rows:
            return {}
            
        book_id = ""
        book_title = ""
        publishers = set()
        authors = set()
        countries = set()
        pub_date = None
        
        for r in rows:
            if r.get("book"):
                book_id = r["book"].split("/")[-1]
            if r.get("bookLabel"):
                book_title = r["bookLabel"]
            if r.get("publisherLabel"):
                publishers.add(r["publisherLabel"])
            if r.get("authorLabel"):
                authors.add(r["authorLabel"])
            if r.get("pubDate"):
                pub_date = r["pubDate"]
            if r.get("countryLabel"):
                countries.add(r["countryLabel"])
                
        return {
            "wikidata_id": book_id,
            "wikidata_name": book_title,
            "publishers": sorted(list(publishers)),
            "authors": sorted(list(authors)),
            "pub_date": pub_date,
            "countries": sorted(list(countries)),
        }
    except Exception:
        return {}


def _fetch_google_books_metadata(volume_id: str) -> dict[str, Any]:
    url = f"https://www.googleapis.com/books/v1/volumes/{volume_id}"
    try:
        response = _polite_get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        info = data.get("volumeInfo", {})
        
        isbns = []
        for identifier in info.get("industryIdentifiers", []):
            val = identifier.get("identifier")
            if val:
                isbns.append(val)
                
        return {
            "title": info.get("title", ""),
            "authors": info.get("authors", []),
            "publisher": info.get("publisher", ""),
            "published_date": info.get("publishedDate", ""),
            "description": info.get("description", ""),
            "isbns": isbns,
        }
    except Exception:
        return {}


def _fetch_wikidata_oclc(oclc_num: str) -> dict[str, Any]:
    try:
        query = f"""
        SELECT ?item ?itemLabel ?publisherLabel ?authorLabel ?pubDate ?isbnLabel ?countryLabel WHERE {{
          ?item wdt:P243 "{oclc_num}".
          OPTIONAL {{ ?item wdt:P123 ?publisher. }}
          OPTIONAL {{ ?item wdt:P50 ?author. }}
          OPTIONAL {{ ?item wdt:P577 ?pubDate. }}
          OPTIONAL {{ ?item wdt:P212 ?isbn. }}
          OPTIONAL {{ ?item wdt:P495 ?country. }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }} LIMIT 5
        """
        rows = _query_wikidata_sparql(query)
        if not rows:
            return {}
            
        item_id = ""
        title = ""
        publishers = set()
        authors = set()
        isbns = set()
        countries = set()
        pub_date = None
        
        for r in rows:
            if r.get("item"):
                item_id = r["item"].split("/")[-1]
            if r.get("itemLabel"):
                title = r["itemLabel"]
            if r.get("publisherLabel"):
                publishers.add(r["publisherLabel"])
            if r.get("authorLabel"):
                authors.add(r["authorLabel"])
            if r.get("isbnLabel"):
                isbns.add(r["isbnLabel"])
            if r.get("pubDate"):
                pub_date = r["pubDate"]
            if r.get("countryLabel"):
                countries.add(r["countryLabel"])
                
        return {
            "wikidata_id": item_id,
            "wikidata_name": title,
            "publishers": sorted(list(publishers)),
            "authors": sorted(list(authors)),
            "isbns": sorted(list(isbns)),
            "countries": sorted(list(countries)),
            "pub_date": pub_date,
        }
    except Exception:
        return {}


def _fetch_crossref_metadata(doi: str) -> dict[str, Any]:
    if doi in _crossref_cache:
        return _crossref_cache[doi]

    result = {}
    url = f"https://api.crossref.org/works/{doi}"
    headers = {
        "User-Agent": "WikipediaSourcesBias/0.1 (mailto:clair.kronk@gmail.com)"
    }
    try:
        response = _polite_get(url, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        message = data.get("message", {})
        
        authors = []
        for a in message.get("author", []):
            given = a.get("given", "")
            family = a.get("family", "")
            if given and family:
                authors.append(f"{given} {family}")
            elif family:
                authors.append(family)
                
        title_list = message.get("title", [])
        title = title_list[0] if title_list else ""
        
        container_list = message.get("container-title", [])
        journal = container_list[0] if container_list else ""
        
        pub_date = None
        date_parts = (message.get("published-print", {}).get("date-parts", []) or 
                      message.get("published-online", {}).get("date-parts", []) or 
                      message.get("created", {}).get("date-parts", []))
        if date_parts and date_parts[0]:
            pub_date = "-".join(str(x) for x in date_parts[0])
            
        result = {
            "title": title,
            "authors": authors,
            "publisher": message.get("publisher", ""),
            "journal": journal,
            "published_date": pub_date,
            "subjects": message.get("subject", []),
        }
    except Exception:
        pass

    _crossref_cache[doi] = result
    _cache_put("crossref_cache.json", doi, result)
    return result


def _fetch_wikidata_doi(doi: str) -> dict[str, Any]:
    try:
        doi_upper = doi.upper()
        query = f"""
        SELECT ?work ?workLabel ?publisherLabel ?authorLabel ?pubDate ?journalLabel ?countryLabel ?politicalLeaningLabel WHERE {{
          ?work wdt:P356 "{doi_upper}".
          OPTIONAL {{ ?work wdt:P123 ?publisher. }}
          OPTIONAL {{ ?work wdt:P50 ?author. }}
          OPTIONAL {{ ?work wdt:P577 ?pubDate. }}
          OPTIONAL {{ ?work wdt:P1433 ?journal. }}
          OPTIONAL {{ ?work wdt:P495 ?country. }}
          OPTIONAL {{ ?work wdt:P1387 ?politicalLeaning. }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }} LIMIT 5
        """
        rows = _query_wikidata_sparql(query)
        if not rows:
            return {}
            
        work_id = ""
        title = ""
        publishers = set()
        authors = set()
        journals = set()
        countries = set()
        political_leanings = set()
        pub_date = None
        
        for r in rows:
            if r.get("work"):
                work_id = r["work"].split("/")[-1]
            if r.get("workLabel"):
                title = r["workLabel"]
            if r.get("publisherLabel"):
                publishers.add(r["publisherLabel"])
            if r.get("authorLabel"):
                authors.add(r["authorLabel"])
            if r.get("journalLabel"):
                journals.add(r["journalLabel"])
            if r.get("countryLabel"):
                countries.add(r["countryLabel"])
            if r.get("politicalLeaningLabel"):
                political_leanings.add(r["politicalLeaningLabel"])
                
        return {
            "wikidata_id": work_id,
            "wikidata_name": work_id,
            "publishers": sorted(list(publishers)),
            "authors": sorted(list(authors)),
            "journals": sorted(list(journals)),
            "countries": sorted(list(countries)),
            "political_leanings": sorted(list(political_leanings)),
            "pub_date": pub_date,
        }
    except Exception:
        return {}


def _count_syllables_word(word: str) -> int:
    word = word.lower()
    word = re.sub(r"[^a-z]", "", word)
    if not word:
        return 0
    if len(word) <= 3:
        return 1
        
    vowels = "aeiouy"
    count = 0
    prev_is_vowel = False
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_is_vowel:
            count += 1
        prev_is_vowel = is_vowel
        
    if word.endswith("e"):
        if len(word) > 2 and word[-2] != "l":
            count -= 1
            
    return max(1, count)


def _calculate_readability(text: str) -> dict[str, Any]:
    words = re.findall(r"\b[a-zA-Z']+\b", text)
    word_count = len(words)
    if word_count == 0:
        return {
            "flesch_reading_ease": None,
            "flesch_kincaid_grade": None,
            "word_count": 0,
            "sentence_count": 0,
            "syllable_count": 0,
            "description": "N/A",
        }
        
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    sentence_count = max(1, len(sentences))
    
    syllable_count = sum(_count_syllables_word(w) for w in words)
    
    asl = word_count / sentence_count
    asw = syllable_count / word_count
    
    flesch_ease = 206.835 - (1.015 * asl) - (84.6 * asw)
    flesch_grade = (0.39 * asl) + (11.8 * asw) - 15.59
    
    if flesch_ease >= 90:
        desc = "Very Easy"
    elif flesch_ease >= 80:
        desc = "Easy"
    elif flesch_ease >= 70:
        desc = "Fairly Easy"
    elif flesch_ease >= 60:
        desc = "Standard"
    elif flesch_ease >= 50:
        desc = "Fairly Difficult"
    elif flesch_ease >= 30:
        desc = "Difficult"
    else:
        desc = "Very Difficult"
        
    return {
        "flesch_reading_ease": round(flesch_ease, 2),
        "flesch_kincaid_grade": round(flesch_grade, 2),
        "word_count": word_count,
        "sentence_count": sentence_count,
        "syllable_count": syllable_count,
        "description": desc,
    }


def _extract_author_from_html(soup: BeautifulSoup) -> str | None:
    # 1. Check meta tags
    meta_auth = soup.find("meta", attrs={"name": "author"})
    if meta_auth and meta_auth.get("content"):
        return meta_auth["content"].strip()
        
    meta_art_auth = soup.find("meta", attrs={"property": "article:author"})
    if meta_art_auth and meta_art_auth.get("content"):
        content = meta_art_auth["content"].strip()
        if not content.startswith("http"):
            return content
            
    for name in ["parsely-author", "sailthru.author", "twitter:creator"]:
        meta = soup.find("meta", attrs={"name": name})
        if meta and meta.get("content"):
            val = meta["content"].strip()
            if val.startswith("@"):
                val = val[1:]
            if val:
                return val
                
    # 2. Check JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("@graph", [data])
            else:
                continue
                
            for item in items:
                author_field = item.get("author")
                if author_field:
                    if isinstance(author_field, dict):
                        name = author_field.get("name")
                        if name:
                            return name.strip()
                    elif isinstance(author_field, list) and author_field:
                        first = author_field[0]
                        if isinstance(first, dict):
                            name = first.get("name")
                            if name:
                                return name.strip()
                        elif isinstance(first, str):
                            return first.strip()
                    elif isinstance(author_field, str):
                        return author_field.strip()
        except Exception:
            pass

    # 3. Check microdata / common class or itemprop tags
    author_el = soup.find(itemprop="author") or soup.find(rel="author")
    if author_el:
        name_el = author_el.find(itemprop="name") if hasattr(author_el, "find") else None
        if name_el:
            return name_el.get_text(" ", strip=True)
        text = author_el.get_text(" ", strip=True)
        text = re.sub(r"(?i)^(by|par|von|de|published\s+by|source)\s+", "", text)
        if len(text) > 2 and len(text) < 60:
            return text

    # 4. Scan all classes containing author/byline/signature
    for el in soup.find_all(class_=True):
        classes = el.get("class", [])
        if any(("author" in c or "byline" in c or "signature" in c) for c in classes):
            text = el.get_text(" ", strip=True)
            text = re.sub(r"(?i)^(by|par|von|de|published\s+by|source)\s+", "", text)
            if len(text) > 2 and len(text) < 60:
                return text
            
    return None


# A source fetch must be bounded in BOTH size and wall-clock time. requests'
# `timeout` only limits the gap between socket reads, so a large file that
# trickles in never times out: an "Soviet space dogs" analysis hung forever on
# a Cambridge University Press PDF, was requeued every 10 minutes, and hung on
# the same PDF again.
MAX_SOURCE_BYTES = 2 * 1024 * 1024      # 2MB of HTML is far more than enough
MAX_SOURCE_SECONDS = 20                 # total, not per read

# Only text is worth parsing for readability. A PDF read as HTML yields binary
# noise, and downloading it costs the bandwidth of the whole document.
_TEXTUAL_CONTENT = ("text/html", "text/plain", "application/xhtml")


def _fetch_text_bounded(url, headers=None, timeout=5):
    """Fetch a URL as text, giving up on size, wall-clock time or content type.

    Returns "" rather than raising when the document is not worth reading.
    """
    response = _polite_get(url, headers=headers, timeout=timeout, stream=True)
    try:
        if response.status_code in (401, 403):
            raise requests.HTTPError(
                f"Direct request blocked with status code {response.status_code}"
            )
        response.raise_for_status()

        content_type = (response.headers.get("Content-Type") or "").lower()
        if content_type and not any(t in content_type for t in _TEXTUAL_CONTENT):
            return ""

        declared = response.headers.get("Content-Length")
        if declared and declared.isdigit() and int(declared) > MAX_SOURCE_BYTES:
            return ""

        deadline = time.monotonic() + MAX_SOURCE_SECONDS
        chunks, size = [], 0
        for chunk in response.iter_content(chunk_size=16384):
            if not chunk:
                continue
            chunks.append(chunk)
            size += len(chunk)
            if size >= MAX_SOURCE_BYTES or time.monotonic() > deadline:
                break
        encoding = response.encoding or "utf-8"
        return b"".join(chunks).decode(encoding, errors="replace")
    finally:
        response.close()


def _fetch_url_readability(url: str) -> dict[str, Any]:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    html = ""
    try:
        html = _fetch_text_bounded(url, headers=headers, timeout=5)
    except Exception:
        try:
            api_url = f"https://archive.org/wayback/available?url={url}"
            api_res = _polite_get(api_url, timeout=5)
            if api_res.status_code == 200:
                data = api_res.json()
                snapshots = data.get("archived_snapshots", {})
                if "closest" in snapshots:
                    archive_url = snapshots["closest"]["url"]
                    html = _fetch_text_bounded(archive_url, headers=headers, timeout=5)
        except Exception:
            pass

    if not html:
        return {
            "flesch_reading_ease": None,
            "flesch_kincaid_grade": None,
            "word_count": 0,
            "sentence_count": 0,
            "syllable_count": 0,
            "description": "Failed to fetch source content",
            "extracted_author": None,
        }

    try:
        soup = BeautifulSoup(html, "html.parser")
        extracted_author = _extract_author_from_html(soup)
        
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()
        text = soup.get_text(" ", strip=True)
        text = " ".join(text.split())
        
        readability = _calculate_readability(text)
        readability["extracted_author"] = extracted_author
        return readability
    except Exception:
        return {
            "flesch_reading_ease": None,
            "flesch_kincaid_grade": None,
            "word_count": 0,
            "sentence_count": 0,
            "syllable_count": 0,
            "description": "Failed to parse source content",
            "extracted_author": None,
        }


def _split_items(val: Any) -> list[str]:
    if not val:
        return []
    if isinstance(val, list):
        items = []
        for v in val:
            items.extend(_split_items(v))
        return items
    if isinstance(val, str):
        parts = re.split(r'[,/;]', val)
        res = [p.strip() for p in parts if p.strip()]
        return res if res else [val]
    return [str(val)]


DATABASE_DOMAINS = {
    "ncbi.nlm.nih.gov", "pubmed.ncbi.nlm.nih.gov", "pmc.ncbi.nlm.nih.gov",
    "europepmc.org", "jstor.org", "arxiv.org", "persee.fr", "cairn.info",
    "semanticscholar.org", "researchgate.net", "books.google.com",
    "books.google.fr", "books.google.de", "books.google.co.uk", "books.google.ca",
    "books.google.es", "books.google.it"
}

def _is_database_domain(host: str) -> bool:
    dom = host.lower()
    if dom.startswith("www."):
        dom = dom[4:]
    return any(dom == d or dom.endswith("." + d) or d in dom for d in DATABASE_DOMAINS)


def _fetch_database_page_metadata(url: str, skip_rate_limiting: bool = False) -> dict[str, Any]:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if not _is_database_domain(host):
        return {}

    result: dict[str, Any] = {}
    
    html = ""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    if not skip_rate_limiting:
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                html = resp.text
        except Exception:
            pass

    meta_doi = None
    meta_publisher = None
    meta_journal = None
    meta_title = None
    meta_authors = []
    
    if html:
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            doi_tag = soup.find("meta", attrs={"name": re.compile(r"^(citation_doi|dc\.identifier)$", re.I)})
            if doi_tag and doi_tag.get("content"):
                meta_doi = doi_tag["content"].strip()
                
            pub_tag = soup.find("meta", attrs={"name": re.compile(r"^(citation_publisher|dc\.publisher)$", re.I)})
            if pub_tag and pub_tag.get("content"):
                meta_publisher = pub_tag["content"].strip()
                
            j_tag = soup.find("meta", attrs={"name": re.compile(r"^(citation_journal_title|citation_journal_abbrev|dc\.relation\.ispartof)$", re.I)})
            if j_tag and j_tag.get("content"):
                meta_journal = j_tag["content"].strip()
                
            t_tag = soup.find("meta", attrs={"name": re.compile(r"^(citation_title|dc\.title|og:title)$", re.I)})
            if t_tag and t_tag.get("content"):
                meta_title = t_tag["content"].strip()
                
            for a_tag in soup.find_all("meta", attrs={"name": re.compile(r"^(citation_author|dc\.creator)$", re.I)}):
                if a_tag.get("content"):
                    meta_authors.append(a_tag["content"].strip())
        except Exception:
            pass

    if not meta_doi:
        meta_doi = _extract_doi(url)

    if meta_doi:
        crossref_meta = _fetch_crossref_metadata(meta_doi)
        wiki_doi_meta = _fetch_wikidata_doi(meta_doi)
        title = crossref_meta.get("title") or wiki_doi_meta.get("wikidata_name") or meta_title or ""
        publisher = crossref_meta.get("publisher") or ", ".join(wiki_doi_meta.get("publishers", [])) or meta_publisher or ""
        journal = crossref_meta.get("journal") or ", ".join(wiki_doi_meta.get("journals", [])) or meta_journal or ""
        authors = crossref_meta.get("authors") or wiki_doi_meta.get("authors") or meta_authors or []
        countries = wiki_doi_meta.get("countries", [])
        leanings = wiki_doi_meta.get("political_leanings", [])
        
        result["doi"] = meta_doi
        result["title"] = title
        result["publisher"] = publisher or journal
        result["journal"] = journal
        result["authors"] = authors
        result["source_type"] = "journal_article"
        if countries:
            result["countries"] = countries
        if leanings:
            result["political_leanings"] = leanings

    books_id = _extract_google_books_id(url)
    if books_id and not result.get("publisher"):
        gb_meta = _fetch_google_books_metadata(books_id)
        if gb_meta:
            result["title"] = gb_meta.get("title") or meta_title or ""
            result["authors"] = gb_meta.get("authors") or meta_authors or []
            result["publisher"] = gb_meta.get("publisher") or meta_publisher or ""
            result["source_type"] = "book"

    target_pub = result.get("publisher") or meta_publisher or meta_journal
    if target_pub and not result.get("countries"):
        wd_pub = _fetch_wikidata_publisher(target_pub)
        if wd_pub and wd_pub.get("countries"):
            result["countries"] = wd_pub["countries"]
        if wd_pub and wd_pub.get("political_leanings"):
            result["political_leanings"] = wd_pub["political_leanings"]

    if target_pub:
        result["publisher"] = target_pub

    return result


def analyze_source_bias(url: str, wikidata: dict[str, Any] | None = None) -> dict[str, Any]:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    domain_info = None
    candidate = host
    while "." in candidate:
        if candidate in DOMAIN_BIAS_DATABASE:
            domain_info = DOMAIN_BIAS_DATABASE[candidate]
            break
        parts = candidate.split(".", 1)
        if len(parts) > 1:
            candidate = parts[1]
        else:
            break

    if domain_info:
        country = domain_info["country"]
        region = domain_info["region"]
        political = domain_info["political_leaning"]
        reliability = domain_info.get("reliability", "unknown")
        source_type = domain_info.get("type", "unknown")
        language = domain_info.get("default_language", "English")
    else:
        country = "Unknown"
        region = "Unknown"
        for suffix, geo in TLD_GEOGRAPHY_MAP.items():
            if host.endswith(suffix):
                country, region = geo
                break

        language = "English"
        for suffix in TLD_GEOGRAPHY_MAP.keys():
            if host.endswith(suffix):
                if suffix in {".fr", ".be", ".ch"}:
                    language = "French"
                elif suffix in {".de", ".at", ".ch"}:
                    language = "German"
                elif suffix in {".es", ".mx", ".ar", ".cl", ".co"}:
                    language = "Spanish"
                elif suffix in {".jp"}:
                    language = "Japanese"
                elif suffix in {".cn", ".hk", ".tw"}:
                    language = "Chinese"
                elif suffix in {".ru", ".ua", ".by"}:
                    language = "Russian"
                elif suffix in {".br", ".pt"}:
                    language = "Portuguese"
                elif suffix in {".it"}:
                    language = "Italian"
                break

        path = parsed.path.lower()
        if "/fr/" in path or "fr." in host:
            language = "French"
        elif "/de/" in path or "de." in host:
            language = "German"
        elif "/es/" in path or "es." in host:
            language = "Spanish"
        elif "/ja/" in path or "ja." in host:
            language = "Japanese"
        elif "/ru/" in path or "ru." in host:
            language = "Russian"
        elif "/pt/" in path or "pt." in host:
            language = "Portuguese"
        elif "/it/" in path or "it." in host:
            language = "Italian"
        elif "/zh/" in path or "zh." in host:
            language = "Chinese"

        if host.endswith(".edu") or "ac.uk" in host:
            source_type = "academic_institution"
            reliability = "unknown"
            political = "academic/neutral"
        elif host.endswith(".gov") or "gov." in host:
            source_type = "government_agency"
            reliability = "unknown"
            political = "neutral"
        elif "blog" in host or "opinion" in path or "editorial" in path:
            source_type = "blog/opinion"
            reliability = "unknown"
            political = "unknown"
        else:
            source_type = "web_source"
            reliability = "unknown"
            political = "unknown"

    return {
        "url": url,
        "domain": host,
        "source_type": source_type,
        "language": language,
        "geography": {"country": country, "region": region},
        "political_leaning": political,
        # Attribution for the leaning above: never "because we said so".
        "political_leaning_source": None,
        "reliability": reliability,
        "wikidata": wikidata or {},
    }


_nametracer_instance = None

def _get_nametrace_prediction(name: str) -> dict[str, Any] | None:
    global _nametracer_instance
    if name in _nametrace_cache:
        return _nametrace_cache[name]

    try:
        from nametrace import NameTracer
        if _nametracer_instance is None:
            _nametracer_instance = NameTracer()
        res = _nametracer_instance.predict(name)
        if res:
            _nametrace_cache[name] = res
            _cache_put("nametrace_cache.json", name, res)
        return res
    except Exception:
        return None


def _fetch_genderize_gender(first_name: str, skip_rate_limiting: bool = False) -> dict[str, Any]:
    if not first_name or len(first_name) < 2:
        return {}
    clean_name = first_name.strip().lower()
    
    cached = get_store().get("genderize_cache", clean_name)
    if cached is not None:
        return cached

    if skip_rate_limiting:
        return {}

    time.sleep(0.4)

    url = f"https://api.genderize.io?name={clean_name}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=3)
        if res.status_code == 200:
            data = res.json()
            if data and data.get("gender"):
                parsed = {
                    "gender": data["gender"],
                    "probability": data.get("probability", 0.8),
                    "count": data.get("count", 10),
                }
                get_store().put("genderize_cache", clean_name, parsed)
                return parsed
    except Exception:
        pass

    get_store().put("genderize_cache", clean_name, {})
    return {}


def analyze_author_bias(author_name: str, source_geography: dict[str, Any], skip_rate_limiting: bool = False) -> dict[str, Any]:
    clean_name = author_name.strip()
    first_name = clean_name.split()[0].lower() if clean_name.split() else clean_name.lower()
    
    # 1. Try nametrace package for comprehensive AI-based gender/origin prediction
    nt_res = _get_nametrace_prediction(clean_name)
    gender_source = "unknown"

    if nt_res:
        is_human = nt_res.get("is_human", True)
        gender = nt_res.get("gender") or "unknown"
        subregion = nt_res.get("subregion") or "Unknown"
        conf = nt_res.get("confidence") or {}
        
        gender_conf = conf.get("gender")
        if gender_conf is None or not isinstance(gender_conf, (int, float)):
            gender_conf = 0.85
            
        if is_human:
            if gender != "unknown" and gender_conf >= 0.60:
                gender_source = "Nametrace"
            else:
                g_meta = _fetch_genderize_gender(first_name, skip_rate_limiting=skip_rate_limiting)
                if g_meta and g_meta.get("gender"):
                    gender = g_meta["gender"]
                    gender_conf = g_meta.get("probability", 0.80)
                    gender_source = "Genderize.io"
                else:
                    g_guess = FIRST_NAME_GENDER.get(first_name, "unknown")
                    if g_guess != "unknown":
                        gender = g_guess
                        gender_conf = 0.80
                        gender_source = "gender-guesser"
                    else:
                        gender = "unknown"
                        gender_conf = 0.10
                        gender_source = "unknown"

        if gender == "male":
            gender_prob = {
                "male": round(gender_conf, 2),
                "female": round((1 - gender_conf) * 0.1, 2),
                "unknown": round((1 - gender_conf) * 0.9, 2)
            }
        elif gender == "female":
            gender_prob = {
                "male": round((1 - gender_conf) * 0.1, 2),
                "female": round(gender_conf, 2),
                "unknown": round((1 - gender_conf) * 0.9, 2)
            }
        else:
            gender_prob = {"male": 0.05, "female": 0.05, "unknown": 0.90}
            
        region = "Unknown"
        if subregion:
            if "Europe" in subregion:
                region = "Europe"
            elif "Asia" in subregion:
                region = "Asia"
            elif "America" in subregion:
                region = "North America" if "Northern" in subregion else "South/Central America"
            elif "Africa" in subregion:
                region = "Africa"
            elif "Oceania" in subregion:
                region = "Oceania"
            elif "Middle East" in subregion:
                region = "Middle East"
                
        subregion_conf = conf.get("subregion")
        if subregion_conf is None or not isinstance(subregion_conf, (int, float)):
            subregion_conf = 0.70
            
        nationality_prob = {
            subregion or "Unknown": round(subregion_conf, 2),
            "Unknown": round(1 - subregion_conf, 2)
        }
        
        return {
            "name": clean_name,
            "is_human": is_human,
            "author_type": "human" if is_human else "corporate/organizational",
            "gender": gender,
            "gender_source": gender_source if is_human else "N/A",
            "subregion": subregion,
            "confidence": conf,
            "gender_probability": gender_prob,
            "nationality_probability": nationality_prob,
            "notes": f"Author background estimated using nametrace package (region: {subregion}).",
        }

    # 2. Fallback to offline lexical heuristics
    words = clean_name.lower().split()
    is_human = True
    stop_words = ["press", "journal", "university", "reuters", "times", "post", "bbc", "news", "society", 
                  "association", "agency", "office", "department", "ministry", "publications", "service"]
    if len(words) > 3 or any(w in stop_words for w in words):
        is_human = False

    if is_human:
        g_meta = _fetch_genderize_gender(first_name, skip_rate_limiting=skip_rate_limiting)
        if g_meta and g_meta.get("gender"):
            gender = g_meta["gender"]
            gender_source = "Genderize.io"
            gender_conf = g_meta.get("probability", 0.80)
        else:
            gender_guess = FIRST_NAME_GENDER.get(first_name, "unknown")
            if gender_guess != "unknown":
                gender = gender_guess
                gender_source = "gender-guesser"
                gender_conf = 0.85
            else:
                gender = "unknown"
                gender_source = "unknown"
                gender_conf = 0.10
    else:
        gender = "unknown"
        gender_source = "N/A"
        gender_conf = 0.10

    if gender == "male":
        gender_prob = {"male": round(gender_conf, 2), "female": round((1 - gender_conf) * 0.1, 2), "unknown": round((1 - gender_conf) * 0.9, 2)}
    elif gender == "female":
        gender_prob = {"male": round((1 - gender_conf) * 0.1, 2), "female": round(gender_conf, 2), "unknown": round((1 - gender_conf) * 0.9, 2)}
    else:
        gender_prob = {"male": 0.05, "female": 0.05, "unknown": 0.90}

    country = "Unknown"
    region = "Unknown"
    matched_pattern = False
    for pattern, pt_country, pt_region in SURNAME_ORIGIN_PATTERNS:
        if re.search(pattern, clean_name, re.I):
            country = pt_country
            region = pt_region
            matched_pattern = True
            break

    if not matched_pattern:
        source_country = source_geography.get("country", "Unknown")
        source_region = source_geography.get("region", "Unknown")
        if source_country != "Unknown":
            country = source_country
            region = source_region

    nationality_prob = {country: 0.70, "Unknown": 0.30} if country != "Unknown" else {"Unknown": 1.0}

    return {
        "name": clean_name,
        "is_human": is_human,
        "author_type": "human" if is_human else "corporate/organizational",
        "gender": gender,
        "gender_source": gender_source,
        "subregion": region,
        "confidence": {"human": 0.80, "gender": gender_conf, "subregion": 0.60},
        "gender_probability": gender_prob,
        "nationality_probability": nationality_prob,
        "notes": "Author background estimated via first name and surname linguistic origin heuristics.",
    }


_sentiment_pipeline = None
_vader_analyzer = None

def _get_vader_sentiment(text: str) -> dict[str, Any] | None:
    global _vader_analyzer
    try:
        import nltk
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        if _vader_analyzer is None:
            nltk.download('vader_lexicon', quiet=True)
            _vader_analyzer = SentimentIntensityAnalyzer()
            
        scores = _vader_analyzer.polarity_scores(text)
        compound = scores["compound"]
        
        if compound >= 0.05:
            label = "positive"
        elif compound <= -0.05:
            label = "negative"
        else:
            label = "neutral"
            
        subj_score = round(min(scores["pos"] + scores["neg"], 1.0), 2)
        
        if compound >= 0.05:
            label = "positive"
        elif compound <= -0.05:
            label = "negative"
        else:
            label = "neutral"
            
        subj_score = round(min(scores["pos"] + scores["neg"], 1.0), 2)
        
        return {
            "sentiment": label,
            "subjectivity_score": subj_score,
            "confidence": round(abs(compound), 2),
            "source": "VADER Sentiment",
        }
    except Exception:
        return None

def _get_huggingface_sentiment(text: str) -> dict[str, Any] | None:
    global _sentiment_pipeline
    if not text:
        return None
    try:
        from transformers import pipeline
        if _sentiment_pipeline is None:
            _sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-xlm-roberta-base-sentiment",
                device=-1,
            )
        result = _sentiment_pipeline(text[:512])[0]
        label = result["label"].lower()
        score = result["score"]
        
        subjectivity_score = 0.0
        if label in ("positive", "negative"):
            subjectivity_score = round(score, 2)
            
        return {
            "sentiment": label,
            "subjectivity_score": subjectivity_score,
            "confidence": round(score, 2),
            "source": "Hugging Face (XLM-RoBERTa)",
        }
    except Exception:
        return _get_vader_sentiment(text)


def _detect_language(text: str) -> str:
    text_lower = text.lower()
    scores = {
        "English": len(re.findall(r"\b(the|and|of|in|to|a|is|that|for|it|on|with|as)\b", text_lower)),
        "French": len(re.findall(r"\b(le|la|les|un|une|et|en|de|du|des|pour|dans|qui|que)\b", text_lower)),
        "German": len(re.findall(r"\b(der|die|das|und|in|zu|von|den|dem|des|ein|eine|für)\b", text_lower)),
        "Spanish": len(re.findall(r"\b(el|la|los|las|un|una|y|en|de|para|con|por|que|este)\b", text_lower)),
        "Italian": len(re.findall(r"\b(il|la|i|gli|le|un|una|e|in|di|da|per|con|su|che)\b", text_lower)),
    }
    detected = max(scores, key=scores.get)
    if scores[detected] > 0:
        return detected
        
    if re.search(r"[\u0400-\u04FF]", text):
        return "Russian"
    if re.search(r"[\u4e00-\u9fff]", text):
        return "Chinese"
    if re.search(r"[\u3040-\u30ff\u31f0-\u31ff]", text):
        return "Japanese"
        
    return "English"


def analyze_language_bias(citation_text: str) -> dict[str, Any]:
    if not citation_text:
        return {
            "loaded_words_found": [],
            "subjectivity_score": 0.0,
            "is_opinion": False,
            "sentiment": "neutral",
            "sensationalism_score": 0.0,
            "detected_language": "English",
            "sentiment_source": "Multilingual Lexical Heuristics",
        }

    hf_res = _get_huggingface_sentiment(citation_text)
    lang = _detect_language(citation_text)
    
    words = re.findall(r"\b[a-zA-Z'\-]+\b", citation_text.lower())
    total_words = len(words)

    loaded_lexicon = MULTILINGUAL_LOADED_WORDS.get(lang, SUBJECTIVE_LOADED_WORDS)
    opinion_lexicon = MULTILINGUAL_OPINION_INDICATORS.get(lang, OPINION_EDITORIAL_INDICATORS)

    loaded_found = [w for w in words if w in loaded_lexicon]
    opinion_found = [w for w in words if w in opinion_lexicon]

    subjectivity_score = 0.0
    if total_words > 0:
        subjectivity_score = min(len(loaded_found) / (total_words ** 0.5), 1.0)

    is_opinion = len(opinion_found) > 0 or "opinion" in citation_text.lower() or (lang == "French" and "avis" in citation_text.lower())

    if hf_res:
        sentiment = hf_res["sentiment"]
        subjectivity_score = round(max(subjectivity_score, hf_res["subjectivity_score"]), 2)
        sent_source = hf_res.get("source", "Hugging Face (XLM-RoBERTa)")
    else:
        positive_words = {"heroic", "courageous", "spectacular", "unquestionably"}
        negative_words = {"disastrous", "tyrant", "despicable", "infamous", "catastrophic", "atrocity", "corrupt", "sham", "ruthless", "cynical"}

        pos_count = sum(1 for w in loaded_found if w in positive_words)
        neg_count = sum(1 for w in loaded_found if w in negative_words)

        if neg_count > pos_count:
            sentiment = "negative"
        elif pos_count > neg_count:
            sentiment = "positive"
        else:
            sentiment = "neutral"
        
        subjectivity_score = round(subjectivity_score, 2)
        sent_source = "Multilingual Lexical Heuristics"

    uppercase_words = re.findall(r"\b[A-Z]{3,}\b", citation_text)
    exclamation_marks = citation_text.count("!")

    sensationalism_score = 0.0
    if total_words > 0:
        sens_factor = len(loaded_found) * 0.3 + len(uppercase_words) * 0.2 + exclamation_marks * 0.5
        sensationalism_score = min(sens_factor / (total_words ** 0.4 + 1), 1.0)

    return {
        "loaded_words_found": sorted(list(set(loaded_found))),
        "subjectivity_score": round(subjectivity_score, 2),
        "is_opinion": is_opinion,
        "sentiment": sentiment,
        "sensationalism_score": round(sensationalism_score, 2),
        "detected_language": lang,
        "sentiment_source": sent_source,
    }


def _calculate_neutrality_metrics(sources: list[dict[str, Any]]) -> dict[str, Any]:
    neut_desc = "Evaluates citation language neutrality on a 0 to 100 scale (100 = completely neutral, non-sensational academic language), incorporating subjectivity penalties, sensationalism penalties, opinion ratios, and loaded words ratios across multilingual sentiment layers."
    if not sources:
        return {
            "description": neut_desc,
            "neutrality_score": 100.0,
            "average_subjectivity_score": 0.0,
            "average_sensationalism_score": 0.0,
            "opinion_citation_percentage": 0.0,
            "sentiment_distribution": {"neutral": 0, "positive": 0, "negative": 0},
            "sentiment_source_breakdown": {
                "Hugging Face (XLM-RoBERTa)": 0,
                "VADER Sentiment": 0,
                "Multilingual Lexical Heuristics": 0,
            }
        }

    total_sources = len(sources)
    total_sub = 0.0
    total_sens = 0.0
    opinion_cnt = 0
    loaded_words_cnt = 0

    sent_dist: dict[str, int] = {"neutral": 0, "positive": 0, "negative": 0}
    source_breakdown: dict[str, int] = {
        "Hugging Face (XLM-RoBERTa)": 0,
        "VADER Sentiment": 0,
        "Multilingual Lexical Heuristics": 0,
    }

    for s in sources:
        lang_bias = s.get("language_bias", {})
        sub = lang_bias.get("subjectivity_score", 0.0)
        sens = lang_bias.get("sensationalism_score", 0.0)
        is_op = lang_bias.get("is_opinion", False)
        loaded_found = lang_bias.get("loaded_words_found", [])
        sent = str(lang_bias.get("sentiment", "neutral")).lower()
        src_name = lang_bias.get("sentiment_source", "Multilingual Lexical Heuristics")

        total_sub += sub
        total_sens += sens
        if is_op:
            opinion_cnt += 1
        if loaded_found:
            loaded_words_cnt += 1

        if sent in sent_dist:
            sent_dist[sent] += 1
        else:
            sent_dist[sent] = 1

        source_breakdown[src_name] = source_breakdown.get(src_name, 0) + 1

    avg_sub = round(total_sub / total_sources, 2)
    avg_sens = round(total_sens / total_sources, 2)
    opinion_pct = round((opinion_cnt / total_sources) * 100, 1)

    sub_penalty = 50.0 * avg_sub
    sens_penalty = 30.0 * avg_sens
    op_penalty = 20.0 * (opinion_cnt / total_sources)
    loaded_penalty = 10.0 * min(1.0, loaded_words_cnt / total_sources)

    total_penalties = sub_penalty + sens_penalty + op_penalty + loaded_penalty
    final_neutrality = round(max(0.0, min(100.0, 100.0 - total_penalties)), 1)

    return {
        "description": neut_desc,
        "neutrality_score": final_neutrality,
        "average_subjectivity_score": avg_sub,
        "average_sensationalism_score": avg_sens,
        "opinion_citation_percentage": opinion_pct,
        "sentiment_distribution": sent_dist,
        "sentiment_source_breakdown": source_breakdown,
    }


def _calculate_jsd(p_dist: dict[str, float], q_dist: dict[str, float]) -> float:
    all_keys = set(p_dist.keys()) | set(q_dist.keys())
    if not all_keys:
        return 0.0

    m_dist = {}
    for k in all_keys:
        p_val = p_dist.get(k, 0.0)
        q_val = q_dist.get(k, 0.0)
        m_dist[k] = 0.5 * (p_val + q_val)

    kl_pm = 0.0
    kl_qm = 0.0

    for k in all_keys:
        m_val = m_dist[k]
        if m_val > 0:
            p_val = p_dist.get(k, 0.0)
            if p_val > 0:
                kl_pm += p_val * math.log2(p_val / m_val)
            q_val = q_dist.get(k, 0.0)
            if q_val > 0:
                kl_qm += q_val * math.log2(q_val / m_val)

    jsd = 0.5 * kl_pm + 0.5 * kl_qm
    return max(0.0, min(1.0, jsd))


def _fetch_wikidata_neighbors(country_name: str, skip_rate_limiting: bool = False) -> set[str]:
    if not country_name or country_name == "Unknown":
        return set()

    query = f"""
    SELECT ?borderingCountryLabel WHERE {{
      ?country ?r ?countryLabel .
      ?country wdt:P31/wdt:P279* wd:Q3624078 ;
               rdfs:label "{country_name}"@en ;
               wdt:P47 ?borderingCountry .
      ?borderingCountry rdfs:label ?borderingCountryLabel .
      FILTER(LANG(?borderingCountryLabel) = "en")
    }}
    LIMIT 50
    """
    url = "https://query.wikidata.org/sparql"
    headers = {
        "User-Agent": "WikipediaSourcesBias/1.0 (https://github.com/Superraptor/Wikipedia-Source-Bias)",
        "Accept": "application/sparql-results+json"
    }

    try:
        if not skip_rate_limiting:
            time.sleep(0.3)
        res = requests.get(url, params={"query": query, "format": "json"}, headers=headers, timeout=4)
        if res.status_code == 200:
            data = res.json()
            bindings = data.get("results", {}).get("bindings", [])
            neighbors = set()
            for b in bindings:
                lbl = b.get("borderingCountryLabel", {}).get("value")
                if lbl:
                    neighbors.add(lbl)
            if neighbors:
                return neighbors
    except Exception:
        pass

    return COUNTRY_NEIGHBORS.get(country_name, set())


def _get_cached_country_neighbors(country_name: str, skip_rate_limiting: bool = False) -> set[str]:
    if not country_name or country_name == "Unknown":
        return set()

    cached = get_store().get("wikidata_neighbors_cache", country_name)
    if cached is not None and isinstance(cached, list):
        return set(cached)

    neighbors = _fetch_wikidata_neighbors(country_name, skip_rate_limiting=skip_rate_limiting)
    get_store().put("wikidata_neighbors_cache", country_name, list(neighbors))
    return set(neighbors)


def _determine_geographic_specificity(
    page_title: str,
    sources: list[dict[str, Any]],
    country_counts: dict[str, int]
) -> tuple[str, str | None]:
    if not country_counts:
        return "global", None

    total_count = sum(country_counts.values())
    sorted_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)
    top_country, top_cnt = sorted_countries[0]
    top_prop = top_cnt / total_count if total_count > 0 else 0.0

    clean_title = page_title.replace("_", " ").lower()
    
    primary_country = None
    if top_prop >= 0.35 or (clean_title and top_country.lower() in clean_title):
        primary_country = top_country

    if primary_country:
        neighbors = _get_cached_country_neighbors(primary_country)
        local_regional_cnt = top_cnt
        for c, cnt in country_counts.items():
            if c != primary_country and c in neighbors:
                local_regional_cnt += cnt
        
        local_regional_prop = local_regional_cnt / total_count if total_count > 0 else 0.0
        if top_prop >= 0.50 or local_regional_prop >= 0.70:
            return "local", primary_country
        else:
            return "regional", primary_country

    return "global", None


def _get_cached_country_population(country_name: str) -> float:
    if not country_name:
        return 20000000.0

    cached = get_store().get("wikidata_population_cache", country_name)
    if cached is not None and isinstance(cached, (int, float)):
        return float(cached)

    pop_val = COUNTRY_POPULATION_DATA.get(country_name, 20000000.0)
    get_store().put("wikidata_population_cache", country_name, pop_val)
    return pop_val


def _calculate_geographic_diversity_score(
    sources: list[dict[str, Any]],
    page_title: str = "",
    split_multiple: bool = False
) -> dict[str, Any]:
    geo_desc = "Evaluates geographic balance on a 0 to 100 scale using Jensen-Shannon Divergence against global population distributions and event-local benchmark weighting based on Wikidata border data."
    if not sources:
        return {
            "description": geo_desc,
            "geographic_diversity_score": 0.0,
            "geographic_scope": "global",
            "primary_country": None,
            "jensen_shannon_divergence": 0.0,
            "jsd_population_score": 0.0,
            "event_local_benchmark_score": 0.0,
            "breakdown": {
                "primary_country_proportion": 0.0,
                "neighboring_countries_proportion": 0.0,
                "same_region_proportion": 0.0,
                "rest_of_world_proportion": 0.0,
            }
        }

    country_counts: dict[str, int] = {}
    region_counts: dict[str, int] = {}

    for s in sources:
        c_raw = s.get("geography", {}).get("country", "Unknown")
        reg_raw = s.get("geography", {}).get("region", "Unknown")
        if c_raw and c_raw != "Unknown":
            c_list = _split_items(c_raw) if split_multiple else [c_raw]
            for c in c_list:
                country_counts[c] = country_counts.get(c, 0) + 1
        if reg_raw and reg_raw != "Unknown":
            reg_list = _split_items(reg_raw) if split_multiple else [reg_raw]
            for r in reg_list:
                region_counts[r] = region_counts.get(r, 0) + 1

    if not country_counts:
        return {
            "description": geo_desc,
            "geographic_diversity_score": 0.0,
            "geographic_scope": "global",
            "primary_country": None,
            "jensen_shannon_divergence": 1.0,
            "jsd_population_score": 0.0,
            "event_local_benchmark_score": 0.0,
            "breakdown": {
                "primary_country_proportion": 0.0,
                "neighboring_countries_proportion": 0.0,
                "same_region_proportion": 0.0,
                "rest_of_world_proportion": 0.0,
            }
        }

    total_country_refs = sum(country_counts.values())

    p_dist = {c: cnt / total_country_refs for c, cnt in country_counts.items()}

    pop_universe = set(country_counts.keys()) | {"China", "India", "United States", "Indonesia", "Brazil", "Nigeria", "Pakistan", "Russia", "Japan", "Mexico", "France", "Germany", "United Kingdom"}
    pop_sum = sum(_get_cached_country_population(c) for c in pop_universe)
    q_pop_dist = {c: _get_cached_country_population(c) / pop_sum for c in pop_universe}

    jsd_val = _calculate_jsd(p_dist, q_pop_dist)
    jsd_pop_score = round(100.0 * (1.0 - jsd_val), 1)

    scope, primary_country = _determine_geographic_specificity(page_title, sources, country_counts)

    primary_prop = 0.0
    neighbor_prop = 0.0
    same_region_prop = 0.0
    rest_world_prop = 0.0

    if primary_country:
        primary_prop = country_counts.get(primary_country, 0) / total_country_refs
        neighbors = _get_cached_country_neighbors(primary_country)
        
        neighbor_cnt = sum(cnt for c, cnt in country_counts.items() if c in neighbors and c != primary_country)
        neighbor_prop = neighbor_cnt / total_country_refs

        same_reg_cnt = sum(
            cnt for c, cnt in country_counts.items()
            if c != primary_country and c not in neighbors
        )
        same_region_prop = same_reg_cnt / total_country_refs
        rest_world_prop = max(0.0, 1.0 - (primary_prop + neighbor_prop + same_region_prop))

        target = (0.45, 0.25, 0.18, 0.12) if scope == "local" else (0.30, 0.35, 0.20, 0.15)
        dev = (
            abs(primary_prop - target[0]) +
            abs(neighbor_prop - target[1]) +
            abs(same_region_prop - target[2]) +
            abs(rest_world_prop - target[3])
        )
        event_local_score = round(100.0 * max(0.0, 1.0 - 0.5 * dev), 1)
    else:
        if len(country_counts) > 1:
            entropy = -sum(p * math.log2(p) for p in p_dist.values() if p > 0)
            max_entropy = math.log2(len(country_counts))
            entropy_score = entropy / max_entropy if max_entropy > 0 else 1.0
        else:
            entropy_score = 0.2
        event_local_score = round(100.0 * entropy_score, 1)

    if scope == "local":
        final_score = round(0.70 * event_local_score + 0.30 * jsd_pop_score, 1)
    elif scope == "regional":
        final_score = round(0.60 * event_local_score + 0.40 * jsd_pop_score, 1)
    else:
        final_score = round(0.50 * event_local_score + 0.50 * jsd_pop_score, 1)

    return {
        "description": geo_desc,
        "geographic_diversity_score": final_score,
        "geographic_scope": scope,
        "primary_country": primary_country,
        "jensen_shannon_divergence": round(jsd_val, 3),
        "jsd_population_score": jsd_pop_score,
        "event_local_benchmark_score": event_local_score,
        "breakdown": {
            "primary_country_proportion": round(primary_prop, 2),
            "neighboring_countries_proportion": round(neighbor_prop, 2),
            "same_region_proportion": round(same_region_prop, 2),
            "rest_of_world_proportion": round(rest_world_prop, 2),
        }
    }


def _map_political_to_numeric_axis(leaning_str: str | None, mbfc_bias_score: float | None = None) -> float | None:
    if mbfc_bias_score is not None:
        return round(max(-3.0, min(3.0, mbfc_bias_score * 0.3)), 2)

    if not leaning_str or str(leaning_str).lower() == "unknown":
        return None

    s = str(leaning_str).lower()

    if any(k in s for k in ("far-left", "extreme-left", "far left", "extreme left")):
        return -3.0
    if any(k in s for k in ("left-center", "left center", "center-left", "center left")):
        return -1.0
    if any(k in s for k in ("far-right", "extreme-right", "far right", "extreme right")):
        return +3.0
    if any(k in s for k in ("right-center", "right center", "center-right", "center right")):
        return +1.0
    if any(k in s for k in ("left", "socialism", "communism", "left-wing")):
        return -2.0
    if any(k in s for k in ("right", "conservatism", "right-wing")):
        return +2.0
    if any(k in s for k in ("least biased", "center", "pro-science", "neutral", "academic/neutral", "balanced")):
        return 0.0

    return None


def _detect_consensus_topic_type(page_title: str) -> str:
    title_lower = page_title.replace("_", " ").lower()

    consensus_science_keywords = {
        "climate change", "global warming", "vaccine", "vaccination", "evolution",
        "holocaust", "flat earth", "hiv/aids", "hiv", "aids", "genetically modified",
        "gmo", "tobacco smoking", "round earth", "shape of the earth"
    }
    mixed_policy_keywords = {
        "carbon tax", "renewable energy policy", "healthcare reform", "nuclear power",
        "minimum wage", "trade policy", "tariff", "gun control policy"
    }

    if any(kw in title_lower for kw in consensus_science_keywords):
        return "consensus_science"
    if any(kw in title_lower for kw in mixed_policy_keywords):
        return "mixed_policy"
    return "open_political"


def _calculate_political_spread_score(
    sources: list[dict[str, Any]],
    page_title: str = ""
) -> dict[str, Any]:
    pol_desc = "Evaluates article political spread on a 0 to 100 scale by mapping outlets to a -3 to +3 ideological axis, assessing standard deviation against target diversity tiers, penalizing extreme-source dominance, and adjusting for consensus science topics."
    if not sources:
        return {
            "description": pol_desc,
            "political_spread_score": 50.0,
            "mean_bias_axis": 0.0,
            "standard_deviation": 0.0,
            "spread_category": "insufficient_data",
            "consensus_topic_type": _detect_consensus_topic_type(page_title),
            "extreme_source_proportion": 0.0,
            "breakdown": {"left_proportion": 0.0, "center_proportion": 0.0, "right_proportion": 0.0}
        }

    axis_values = []
    left_cnt = 0
    center_cnt = 0
    right_cnt = 0
    extreme_cnt = 0

    for s in sources:
        mbfc_bias = s.get("mbfc", {}).get("mbfc_bias_score")
        leaning = s.get("political_leaning")
        val = _map_political_to_numeric_axis(leaning, mbfc_bias)
        if val is not None:
            axis_values.append(val)
            if val <= -0.5:
                left_cnt += 1
            elif val >= 0.5:
                right_cnt += 1
            else:
                center_cnt += 1

            if abs(val) >= 2.5:
                extreme_cnt += 1

    total_valid = len(axis_values)
    if total_valid < 2:
        return {
            "description": pol_desc,
            "political_spread_score": 50.0,
            "mean_bias_axis": round(axis_values[0], 2) if axis_values else 0.0,
            "standard_deviation": 0.0,
            "spread_category": "insufficient_data",
            "consensus_topic_type": _detect_consensus_topic_type(page_title),
            "extreme_source_proportion": 0.0,
            "breakdown": {
                "left_proportion": round(left_cnt / max(1, total_valid), 2),
                "center_proportion": round(center_cnt / max(1, total_valid), 2),
                "right_proportion": round(right_cnt / max(1, total_valid), 2),
            }
        }

    mean_val = sum(axis_values) / total_valid
    variance = sum((x - mean_val) ** 2 for x in axis_values) / total_valid
    std_dev = math.sqrt(variance)

    if 0.4 <= std_dev <= 1.0:
        spread_category = "healthy_diversity"
        base_score = 90.0 + 10.0 * (1.0 - abs(std_dev - 0.7) / 0.3)
    elif 1.1 <= std_dev <= 1.5:
        spread_category = "wide_acceptable"
        base_score = 75.0 - 15.0 * ((std_dev - 1.1) / 0.4)
    elif std_dev > 1.5:
        spread_category = "potentially_polarized"
        base_score = max(20.0, 60.0 - 25.0 * (std_dev - 1.5))
    else:
        spread_category = "too_homogeneous"
        base_score = max(30.0, 40.0 + 100.0 * std_dev)

    extreme_prop = extreme_cnt / total_valid
    extreme_penalty = 0.0
    if extreme_prop > 0.25:
        extreme_penalty = 40.0 * (extreme_prop - 0.25)

    base_score -= extreme_penalty

    topic_type = _detect_consensus_topic_type(page_title)
    if topic_type == "consensus_science":
        if extreme_prop == 0.0 and std_dev <= 1.0:
            final_score = max(base_score, 95.0)
        else:
            final_score = base_score * 0.70
    elif topic_type == "mixed_policy":
        final_score = base_score * 0.90
    else:
        final_score = base_score

    final_score = round(max(0.0, min(100.0, final_score)), 1)

    return {
        "description": pol_desc,
        "political_spread_score": final_score,
        "mean_bias_axis": round(mean_val, 2),
        "standard_deviation": round(std_dev, 2),
        "spread_category": spread_category,
        "consensus_topic_type": topic_type,
        "extreme_source_proportion": round(extreme_prop, 2),
        "breakdown": {
            "left_proportion": round(left_cnt / total_valid, 2),
            "center_proportion": round(center_cnt / total_valid, 2),
            "right_proportion": round(right_cnt / total_valid, 2),
        }
    }


def _calculate_gender_parity_metrics(sources: list[dict[str, Any]]) -> dict[str, Any]:
    gender_desc = "Evaluates human author gender balance on a 0 to 100 scale (100 = 50/50 male/female parity), incorporating composite inference confidence, unknown author dampening, and multi-tier provenance tracking (Wikidata, Nametrace, Genderize.io, gender-guesser)."
    total_authors = 0
    human_authors = 0
    female_cnt = 0
    male_cnt = 0
    non_binary_cnt = 0
    unknown_gender_cnt = 0

    conf_scores = []
    provenance_counts: dict[str, int] = {
        "Wikidata": 0,
        "Nametrace": 0,
        "Genderize.io": 0,
        "gender-guesser": 0,
        "unknown": 0,
    }

    for s in sources:
        auth_profiles = s.get("author_profiles", [])
        if not auth_profiles and s.get("author_profile"):
            auth_profiles = [s["author_profile"]]

        for auth in auth_profiles:
            total_authors += 1
            if not auth.get("is_human", True):
                continue
            
            human_authors += 1
            gender = str(auth.get("gender", "unknown")).lower()
            source = auth.get("gender_source", "unknown")
            provenance_counts[source] = provenance_counts.get(source, 0) + 1

            g_prob = auth.get("gender_probability", {})
            if gender == "female":
                female_cnt += 1
                conf_scores.append(g_prob.get("female", 0.85))
            elif gender == "male":
                male_cnt += 1
                conf_scores.append(g_prob.get("male", 0.85))
            elif gender in ("non-binary", "nonbinary", "transgender"):
                non_binary_cnt += 1
                conf_scores.append(0.90)
            else:
                unknown_gender_cnt += 1
                conf_scores.append(0.10)

    if human_authors == 0:
        return {
            "description": gender_desc,
            "gender_parity_score": 50.0,
            "composite_confidence_score": 0.0,
            "unknown_author_proportion": 1.0,
            "human_author_count": 0,
            "gender_counts": {"female": 0, "male": 0, "non_binary": 0, "unknown": 0},
            "provenance_breakdown": provenance_counts,
        }

    known_cnt = female_cnt + male_cnt + non_binary_cnt
    unknown_prop = round(unknown_gender_cnt / human_authors, 2)
    composite_conf = round(sum(conf_scores) / len(conf_scores) * 100, 1) if conf_scores else 0.0

    if known_cnt == 0:
        parity_score = 50.0
    else:
        binary_total = female_cnt + male_cnt
        if binary_total > 0:
            female_ratio = female_cnt / binary_total
            raw_parity = 100.0 * (1.0 - 2.0 * abs(female_ratio - 0.50))
        else:
            raw_parity = 100.0

        unknown_dampening = max(0.40, 1.0 - 0.60 * unknown_prop)
        parity_score = round(max(0.0, min(100.0, raw_parity * unknown_dampening)), 1)

    return {
        "description": gender_desc,
        "gender_parity_score": parity_score,
        "composite_confidence_score": composite_conf,
        "unknown_author_proportion": unknown_prop,
        "human_author_count": human_authors,
        "gender_counts": {
            "female": female_cnt,
            "male": male_cnt,
            "non_binary": non_binary_cnt,
            "unknown": unknown_gender_cnt,
        },
        "provenance_breakdown": provenance_counts,
    }


def aggregate_page_bias(sources: list[dict[str, Any]], split_multiple: bool = False, page_title: str = "") -> dict[str, Any]:
    if not sources:
        return {}

    total_sources = len(sources)

    countries: dict[str, int] = {}
    regions: dict[str, int] = {}
    political: dict[str, int] = {}
    reliability: dict[str, int] = {}
    languages: dict[str, int] = {}
    types: dict[str, int] = {}

    total_sub_score = 0.0
    total_sens_score = 0.0
    opinion_count = 0

    # Human demographics aggregates
    author_types: dict[str, int] = {"human": 0, "corporate/organizational": 0}
    human_gender: dict[str, int] = {"male": 0, "female": 0, "unknown": 0}
    human_subregions: dict[str, int] = {}
    human_nationalities: dict[str, int] = {}
    human_citizenships: dict[str, int] = {}
    human_occupations: dict[str, int] = {}
    human_employers: dict[str, int] = {}
    human_employer_countries: dict[str, int] = {}

    # Backward compatibility
    gender_sums = {"male": 0.0, "female": 0.0, "unknown": 0.0}
    authors_analyzed = 0

    total_readability = 0.0
    readability_count = 0
    book_count = 0

    for s in sources:
        geo = s.get("geography", {})
        c_raw = geo.get("country", "Unknown")
        r_raw = geo.get("region", "Unknown")
        pol_raw = s.get("political_leaning", "unknown")
        rel_raw = s.get("reliability", "unknown")
        lang_raw = s.get("language", "English")
        t_raw = s.get("source_type", "unknown")

        c_list = _split_items(c_raw) if split_multiple else [c_raw]
        r_list = _split_items(r_raw) if split_multiple else [r_raw]
        pol_list = _split_items(pol_raw) if split_multiple else [pol_raw]
        rel_list = _split_items(rel_raw) if split_multiple else [rel_raw]
        lang_list = _split_items(lang_raw) if split_multiple else [lang_raw]
        t_list = _split_items(t_raw) if split_multiple else [t_raw]

        for c in c_list:
            countries[c] = countries.get(c, 0) + 1
        for r in r_list:
            regions[r] = regions.get(r, 0) + 1
        for pol in pol_list:
            political[pol] = political.get(pol, 0) + 1
        for rel in rel_list:
            reliability[rel] = reliability.get(rel, 0) + 1
        for lang in lang_list:
            languages[lang] = languages.get(lang, 0) + 1
        for t in t_list:
            types[t] = types.get(t, 0) + 1

        lang_bias = s.get("language_bias", {})
        total_sub_score += lang_bias.get("subjectivity_score", 0.0)
        total_sens_score += lang_bias.get("sensationalism_score", 0.0)
        if lang_bias.get("is_opinion", False):
            opinion_count += 1

        author_profiles = s.get("author_profiles", [])
        for auth in author_profiles:
            auth_type = auth.get("author_type", "human")
            author_types[auth_type] = author_types.get(auth_type, 0) + 1

            if auth.get("is_human", True):
                g = auth.get("gender", "unknown")
                human_gender[g] = human_gender.get(g, 0) + 1

                subr = auth.get("subregion", "Unknown")
                human_subregions[subr] = human_subregions.get(subr, 0) + 1

                nat_probs = auth.get("nationality_probability", {})
                if nat_probs:
                    best_nat = max(nat_probs, key=nat_probs.get)
                    human_nationalities[best_nat] = human_nationalities.get(best_nat, 0) + 1

                wiki_a = auth.get("wikidata_author", {})
                if wiki_a:
                    for cit in wiki_a.get("citizenships", []):
                        human_citizenships[cit] = human_citizenships.get(cit, 0) + 1
                    for occ in wiki_a.get("occupations", []):
                        human_occupations[occ] = human_occupations.get(occ, 0) + 1
                    for emp in wiki_a.get("employers", []):
                        emp_name = emp.get("name")
                        emp_country = emp.get("country", "Unknown")
                        if emp_name:
                            human_employers[emp_name] = human_employers.get(emp_name, 0) + 1
                        if emp_country:
                            human_employer_countries[emp_country] = human_employer_countries.get(emp_country, 0) + 1

            # Backward compatibility sums
            gender_prob = auth.get("gender_probability", {})
            for g_key, prob in gender_prob.items():
                if prob is not None:
                    gender_sums[g_key] = gender_sums.get(g_key, 0.0) + prob
            authors_analyzed += 1

        readability = s.get("readability", {})
        ease = readability.get("flesch_reading_ease")
        if ease is not None:
            total_readability += ease
            readability_count += 1

        wikidata_book = s.get("wikidata_book", {})
        google_books = s.get("google_books_metadata", {})
        oclc_meta = s.get("oclc_metadata", {})
        if (wikidata_book and wikidata_book.get("wikidata_id")) or (google_books and google_books.get("title")) or (oclc_meta and oclc_meta.get("wikidata_id")):
            book_count += 1

    total_authors = sum(author_types.values())
    total_human = sum(human_gender.values())

    author_type_dist = {
        k: {"count": v, "percentage": round(v / total_authors * 100, 1)}
        for k, v in author_types.items()
    } if total_authors > 0 else {}

    human_gender_dist = {
        k: {"count": v, "percentage": round(v / total_human * 100, 1)}
        for k, v in human_gender.items()
    } if total_human > 0 else {}

    human_subregion_dist = {
        k: {"count": v, "percentage": round(v / total_human * 100, 1)}
        for k, v in human_subregions.items()
    } if total_human > 0 else {}

    human_nationality_dist = {
        k: {"count": v, "percentage": round(v / total_human * 100, 1)}
        for k, v in human_nationalities.items()
    } if total_human > 0 else {}

    total_citizenships = sum(human_citizenships.values())
    human_citizenship_dist = {
        k: {"count": v, "percentage": round(v / total_citizenships * 100, 1)}
        for k, v in human_citizenships.items()
    } if total_citizenships > 0 else {}

    total_occupations = sum(human_occupations.values())
    human_occupation_dist = {
        k: {"count": v, "percentage": round(v / total_occupations * 100, 1)}
        for k, v in human_occupations.items()
    } if total_occupations > 0 else {}

    total_employers = sum(human_employers.values())
    human_employer_dist = {
        k: {"count": v, "percentage": round(v / total_employers * 100, 1)}
        for k, v in human_employers.items()
    } if total_employers > 0 else {}

    total_emp_countries = sum(human_employer_countries.values())
    human_employer_country_dist = {
        k: {"count": v, "percentage": round(v / total_emp_countries * 100, 1)}
        for k, v in human_employer_countries.items()
    } if total_emp_countries > 0 else {}

    geo_distribution = {c: {"count": val, "percentage": round(val / total_sources * 100, 1)} for c, val in countries.items()}
    region_distribution = {reg: {"count": val, "percentage": round(val / total_sources * 100, 1)} for reg, val in regions.items()}
    political_leaning_distribution = {pol: {"count": val, "percentage": round(val / total_sources * 100, 1)} for pol, val in political.items()}
    reliability_distribution = {rel: {"count": val, "percentage": round(val / total_sources * 100, 1)} for rel, val in reliability.items()}
    language_distribution = {lang: {"count": val, "percentage": round(val / total_sources * 100, 1)} for lang, val in languages.items()}
    type_distribution = {t: {"count": val, "percentage": round(val / total_sources * 100, 1)} for t, val in types.items()}

    gender_distribution = {}
    if authors_analyzed > 0:
        gender_distribution = {g: round(val / authors_analyzed * 100, 1) for g, val in gender_sums.items()}

    avg_readability = None
    if readability_count > 0:
        avg_readability = round(total_readability / readability_count, 2)

    total_composite_rel = 0.0
    mbfc_fact_scores = []
    mbfc_cred_scores = []
    mbfc_bias_scores = []

    for s in sources:
        rel_scores = s.get("reliability_scores")
        if not rel_scores:
            rel_scores = _calculate_composite_reliability(s, s.get("mbfc"), s.get("wikidata_publisher"))
            
        comp = rel_scores.get("composite_reliability_score")
        if comp is not None:
            total_composite_rel += comp
            
        f_score = rel_scores.get("mbfc_factuality_score")
        if f_score is not None:
            mbfc_fact_scores.append(f_score)
            
        c_score = rel_scores.get("mbfc_credibility_score")
        if c_score is not None:
            mbfc_cred_scores.append(c_score)
            
        b_score = rel_scores.get("mbfc_bias_score")
        if b_score is not None:
            mbfc_bias_scores.append(b_score)

    return {
        "source_count": total_sources,
        "geography_distribution": geo_distribution,
        "region_distribution": region_distribution,
        "political_leaning_distribution": political_leaning_distribution,
        "reliability_distribution": reliability_distribution,
        "language_distribution": language_distribution,
        "source_type_distribution": type_distribution,
        "author_gender_distribution_estimate": gender_distribution,
        "author_type_distribution": author_type_dist,
        "human_author_gender_distribution": human_gender_dist,
        "human_author_subregion_distribution": human_subregion_dist,
        "human_author_nationality_distribution": human_nationality_dist,
        "human_author_citizenship_distribution": human_citizenship_dist,
        "human_author_occupation_distribution": human_occupation_dist,
        "human_author_employer_distribution": human_employer_dist,
        "human_author_employer_country_distribution": human_employer_country_dist,
        "reliability_metrics": {
            "description": "Evaluates source trustworthiness and factuality on a 0 to 100 scale by blending Media Bias/Fact Check (MBFC) credibility, factuality ratings, and Wikidata peer-reviewed academic statements.",
            "average_composite_reliability_score": round(total_composite_rel / total_sources, 1) if total_sources > 0 else None,
            "average_mbfc_factuality_score": round(sum(mbfc_fact_scores) / len(mbfc_fact_scores), 1) if mbfc_fact_scores else None,
            "average_mbfc_credibility_score": round(sum(mbfc_cred_scores) / len(mbfc_cred_scores), 1) if mbfc_cred_scores else None,
            "average_mbfc_bias_score": round(sum(mbfc_bias_scores) / len(mbfc_bias_scores), 1) if mbfc_bias_scores else None,
            "average_flesch_reading_ease": avg_readability,
            "readability_count": readability_count,
        },
        "geographic_diversity_metrics": _calculate_geographic_diversity_score(sources, page_title=page_title, split_multiple=split_multiple),
        "political_spread_metrics": _calculate_political_spread_score(sources, page_title=page_title),
        "gender_parity_metrics": _calculate_gender_parity_metrics(sources),
        "neutrality_metrics": _calculate_neutrality_metrics(sources),
        "language_bias_metrics": {
            "description": "Aggregates lexical subjectivity scores, sensationalism scores, and opinion/editorial citation percentages across analyzed sources.",
            "average_subjectivity_score": round(total_sub_score / total_sources, 2),
            "average_sensationalism_score": round(total_sens_score / total_sources, 2),
            "opinion_percentage": round(opinion_count / total_sources * 100, 1),
        },
        "book_count": book_count,
    }



CACHE_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mbfc_cache.json")

def _load_mbfc_cache() -> dict[str, dict[str, Any]]:
    data = get_store().load_all("mbfc_cache")
    # Filter out stale/incorrect/empty cache lookups to force a clean re-fetch with new regex
    return {
        k: v for k, v in data.items()
        if v and v.get("credibility_rating") != "unknown" and len(v.get("credibility_rating", "")) > 3
    }

def _save_mbfc_cache(cache: dict[str, dict[str, Any]]):
    """Deprecated: prefer _cache_put('mbfc_cache.json', domain, rating)."""
    _save_json_cache("mbfc_cache.json", cache)

_mbfc_cache: dict[str, dict[str, Any]] = _load_mbfc_cache()

def _ns(filename: str) -> str:
    """'crossref_cache.json' -> 'crossref_cache'."""
    return filename[:-5] if filename.endswith(".json") else filename

def _load_json_cache(filename: str) -> dict[str, Any]:
    return get_store().load_all(_ns(filename))

def _cache_put(filename: str, key: str, value: Any) -> None:
    """Persist a single entry.

    Replaces the previous whole-dict rewrite. That was merely wasteful against
    a file, but against MariaDB it would rewrite every row on every lookup.
    """
    get_store().put(_ns(filename), key, value)

def _save_json_cache(filename: str, cache: dict[str, Any]):
    """Deprecated: kept so external callers keep working. Writes every entry."""
    store = get_store()
    ns = _ns(filename)
    for k, v in cache.items():
        store.put(ns, k, v)

_wd_publisher_cache = _load_json_cache("wikidata_publisher_cache.json")
_wd_enrichment_cache = _load_json_cache("wikidata_enrichment_cache.json")
_wd_author_cache = _load_json_cache("wikidata_author_cache.json")
_nametrace_cache = _load_json_cache("nametrace_cache.json")
_crossref_cache = _load_json_cache("crossref_cache.json")

LOCAL_MBFC_RATINGS = {
    "le-point": {"bias_rating": "Right-Center", "factual_reporting": "High", "credibility_rating": "High Credibility"},
    "le-figaro": {"bias_rating": "Right-Center", "factual_reporting": "High", "credibility_rating": "High Credibility"},
    "reuters": {"bias_rating": "Least Biased", "factual_reporting": "Very High", "credibility_rating": "High Credibility"},
    "associated-press": {"bias_rating": "Least Biased", "factual_reporting": "Very High", "credibility_rating": "High Credibility"},
    "the-new-york-times": {"bias_rating": "Left-Center", "factual_reporting": "High", "credibility_rating": "High Credibility"},
    "the-washington-post": {"bias_rating": "Left-Center", "factual_reporting": "High", "credibility_rating": "High Credibility"},
    "wall-street-journal": {"bias_rating": "Right-Center", "factual_reporting": "High", "credibility_rating": "High Credibility"},
    "bbc": {"bias_rating": "Left-Center", "factual_reporting": "High", "credibility_rating": "High Credibility"},
    "cnn": {"bias_rating": "Left-Center", "factual_reporting": "Mostly Factual", "credibility_rating": "Medium Credibility"},
    "fox-news-channel": {"bias_rating": "Right", "factual_reporting": "Mixed", "credibility_rating": "Medium Credibility"},
    "msnbc": {"bias_rating": "Left", "factual_reporting": "Mostly Factual", "credibility_rating": "Medium Credibility"},
    "breitbart": {"bias_rating": "Right", "factual_reporting": "Mixed", "credibility_rating": "Low Credibility"},
    "guardian": {"bias_rating": "Left-Center", "factual_reporting": "High", "credibility_rating": "High Credibility"},
    "le-monde": {"bias_rating": "Left-Center", "factual_reporting": "High", "credibility_rating": "High Credibility"},
    "le-monde-diplomatique": {"bias_rating": "Left-Center", "factual_reporting": "High", "credibility_rating": "High Credibility"},
}

def _fetch_mbfc_rating(domain: str, mbfc_id: str | None = None, skip_rate_limiting: bool = False) -> dict[str, Any]:
    slug = mbfc_id or domain.split(".")[0].lower()
    
    if slug in LOCAL_MBFC_RATINGS:
        res = LOCAL_MBFC_RATINGS[slug].copy()
        res["mbfc_url"] = f"https://mediabiasfactcheck.com/{slug}/"
        return res
        
    if slug in _mbfc_cache:
        return _mbfc_cache[slug]
        
    if skip_rate_limiting:
        return {}
        
    # Politeness is enforced centrally by _polite_get via the per-host
    # limiter (mediabiasfactcheck.com is capped at 1 req/s there). A sleep
    # here as well would double the delay and, being per-process, would not
    # coordinate across worker replicas anyway.
    
    candidates = [
        f"https://mediabiasfactcheck.com/{slug}-bias-and-credibility/",
        f"https://mediabiasfactcheck.com/{slug}/",
        f"https://mediabiasfactcheck.com/{slug}-bias/"
    ]
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    for url in candidates:
        html = ""
        try:
            response = _polite_get(url, headers=headers, timeout=3)
            if response.status_code == 200:
                html = response.text
        except Exception:
            pass
            
        if not html:
            if skip_rate_limiting:
                continue
            try:
                api_url = f"https://archive.org/wayback/available?url={url}"
                api_res = _polite_get(api_url, timeout=3)
                if api_res.status_code == 200:
                    data = api_res.json()
                    snapshots = data.get("archived_snapshots", {})
                    if "closest" in snapshots:
                        archive_url = snapshots["closest"]["url"]
                        archive_res = _polite_get(archive_url, headers=headers, timeout=3)
                        if archive_res.status_code == 200:
                            html = archive_res.text
            except Exception:
                pass
                
        if html:
            try:
                soup = BeautifulSoup(html, "html.parser")
                page_text = soup.get_text(" ", strip=True)
                
                bias_match = re.search(r"Bias Rating:\s*([a-zA-Z\-\/\s]+(?:\s*\([\d\.]+\))?)", page_text, re.I)
                factual_match = re.search(r"Factual Reporting:\s*([a-zA-Z\-\/\s]+(?:\s*\([\d\.]+\))?)", page_text, re.I)
                credibility_match = re.search(r"(?:MBFC )?Credibility Rating:\s*([a-zA-Z\s\-]+credibility)", page_text, re.I)
                country_match = re.search(r"Country:\s*([a-zA-Z\s\-\/\(\),]+?)(?=\s*(?:Bias Rating|Factual Reporting|MBFC|Media Type|Traffic|Credibility|Ad Fontes|Detailed Report|Sources|Notes|$))", page_text, re.I)
                freedom_match = re.search(r"(?:MBFC[’'s\s]+)?Country Freedom Rating:\s*([a-zA-Z\s]+?)(?=\s*(?:Bias Rating|Factual Reporting|Country|Media Type|Traffic|Credibility|Ad Fontes|Detailed Report|Sources|Notes|$))", page_text, re.I)
                media_match = re.search(r"Media Type:\s*([a-zA-Z\s\-\/]+?)(?=\s*(?:Bias Rating|Factual Reporting|Country|MBFC|Traffic|Credibility|Ad Fontes|Detailed Report|Sources|Notes|$))", page_text, re.I)
                traffic_match = re.search(r"(?:Traffic/Popularity|Traffic):\s*([a-zA-Z\s\-\/]+?)(?=\s*(?:Bias Rating|Factual Reporting|Country|MBFC|Media Type|Credibility|Ad Fontes|Detailed Report|Sources|Notes|$))", page_text, re.I)
                
                bias_val = bias_match.group(1).strip().rstrip(".") if bias_match else "unknown"
                factual_val = factual_match.group(1).strip().rstrip(".") if factual_match else "unknown"
                credibility_val = credibility_match.group(1).strip().rstrip(".") if credibility_match else "unknown"
                country_val = country_match.group(1).strip().rstrip(".") if country_match else None
                freedom_val = freedom_match.group(1).strip().rstrip(".") if freedom_match else None
                media_val = media_match.group(1).strip().rstrip(".") if media_match else None
                traffic_val = traffic_match.group(1).strip().rstrip(".") if traffic_match else None
                
                if bias_val == "unknown":
                    b_m = re.search(r"\b(left|left-center|least biased|right-center|right|conspiracy/pseudoscience|pro-science|questionable-source)\b", page_text.lower())
                    if b_m:
                        bias_val = b_m.group(0).upper()
                if factual_val == "unknown":
                    f_m = re.search(r"\b(high|very high|mostly factual|mixed|low|very low)\b", page_text.lower())
                    if f_m:
                        factual_val = f_m.group(0).upper()
                        
                res = {
                    "mbfc_url": url,
                    "bias_rating": bias_val,
                    "factual_reporting": factual_val,
                    "credibility_rating": credibility_val,
                }
                if country_val:
                    res["country"] = country_val
                if freedom_val:
                    res["country_freedom_rating"] = freedom_val
                if media_val:
                    res["media_type"] = media_val
                if traffic_val:
                    res["traffic_popularity"] = traffic_val
                    
                _mbfc_cache[slug] = res
                _cache_put("mbfc_cache.json", slug, res)
                return res
            except Exception:
                pass
                
    # Cache negative lookup as empty dict to avoid repeatedly querying invalid domains
    _mbfc_cache[slug] = {}
    _cache_put("mbfc_cache.json", slug, {})
    return {}


def _parse_mbfc_scores(mbfc: dict[str, Any]) -> dict[str, Any]:
    if not mbfc:
        return {
            "mbfc_credibility_score": None,
            "mbfc_factuality_score": None,
            "mbfc_bias_score": None,
        }

    cred_str = str(mbfc.get("credibility_rating", "")).upper()
    cred_score = None
    if "HIGH" in cred_str:
        cred_score = 100.0
    elif "MEDIUM" in cred_str:
        cred_score = 50.0
    elif "LOW" in cred_str:
        cred_score = 10.0

    fact_str = str(mbfc.get("factual_reporting", "")).upper()
    fact_score = None
    if "VERY HIGH" in fact_str:
        fact_score = 100.0
    elif "HIGH" in fact_str:
        fact_score = 80.0
    elif "MOSTLY" in fact_str or "MOSTLY FACTUAL" in fact_str:
        fact_score = 60.0
    elif "MIXED" in fact_str:
        fact_score = 40.0
    elif "LOW" in fact_str and "VERY LOW" not in fact_str:
        fact_score = 20.0
    elif "VERY LOW" in fact_str:
        fact_score = 0.0

    match_num = re.search(r'\(([-\d\.]+)\)', fact_str)
    if match_num and fact_score is None:
        try:
            val = float(match_num.group(1))
            if 0.0 <= val <= 6.0:
                fact_score = round(max(0.0, min(100.0, 100.0 - (val * 16.67))), 1)
        except ValueError:
            pass

    bias_str = str(mbfc.get("bias_rating", "")).upper()
    bias_score = None
    match_bias_num = re.search(r'\(([-\d\.]+)\)', bias_str)
    num_val = None
    if match_bias_num:
        try:
            num_val = float(match_bias_num.group(1))
        except ValueError:
            pass

    if "EXTREME LEFT" in bias_str or ("LEFT" in bias_str and "LEFT-CENTER" not in bias_str):
        bias_score = -100.0 if num_val is None else -abs(num_val)
    elif "LEFT-CENTER" in bias_str:
        bias_score = -50.0 if num_val is None else -abs(num_val)
    elif "LEAST BIASED" in bias_str or "CENTER" in bias_str or "PRO-SCIENCE" in bias_str:
        bias_score = 0.0
    elif "RIGHT-CENTER" in bias_str:
        bias_score = +50.0 if num_val is None else abs(num_val)
    elif "RIGHT" in bias_str and "RIGHT-CENTER" not in bias_str:
        bias_score = +100.0 if num_val is None else abs(num_val)

    return {
        "mbfc_credibility_score": cred_score,
        "mbfc_factuality_score": fact_score,
        "mbfc_bias_score": bias_score,
    }


def _calculate_composite_reliability(
    profile: dict[str, Any],
    mbfc: dict[str, Any] | None = None,
    wikidata_pub: dict[str, Any] | None = None
) -> dict[str, Any]:
    mbfc_scores = _parse_mbfc_scores(mbfc or {})
    
    wikidata_score = None
    if wikidata_pub:
        types = [str(t).lower() for t in wikidata_pub.get("types", [])]
        if any("scientific journal" in t or "academic journal" in t or "peer-reviewed" in t for t in types):
            wikidata_score = 100.0
        elif any("fake news" in t or "tabloid" in t for t in types):
            wikidata_score = 10.0
            
    if wikidata_score is None and (profile.get("wikidata_book") or profile.get("doi_metadata")):
        wikidata_score = 100.0

    provenance = []
    weighted_sum = 0.0
    weight_total = 0.0
    
    cred_score = mbfc_scores.get("mbfc_credibility_score")
    fact_score = mbfc_scores.get("mbfc_factuality_score")
    
    if cred_score is not None:
        weighted_sum += cred_score * 0.55
        weight_total += 0.55
        provenance.append("Media Bias/Fact Check (MBFC)")
        
    if fact_score is not None:
        weighted_sum += fact_score * 0.45
        weight_total += 0.45
        if "Media Bias/Fact Check (MBFC)" not in provenance:
            provenance.append("Media Bias/Fact Check (MBFC)")
            
    if wikidata_score is not None:
        weighted_sum += wikidata_score * 0.30
        weight_total += 0.30
        provenance.append("Wikidata")

    if weight_total == 0.0:
        composite_score = None
    else:
        composite_score = round(max(0.0, min(100.0, weighted_sum / weight_total)), 1)

    # Derive dynamic reliability classification string from empirical evidence only
    dynamic_rel = "unknown"
    if mbfc and mbfc.get("credibility_rating") and mbfc.get("credibility_rating") != "unknown":
        dynamic_rel = str(mbfc["credibility_rating"]).lower()
    elif mbfc and mbfc.get("factual_reporting") and mbfc.get("factual_reporting") != "unknown":
        dynamic_rel = str(mbfc["factual_reporting"]).lower()
    elif wikidata_score == 100.0:
        dynamic_rel = "academic/peer-reviewed"

    profile["reliability"] = dynamic_rel

    return {
        "composite_reliability_score": composite_score,
        "mbfc_credibility_score": cred_score,
        "mbfc_factuality_score": fact_score,
        "mbfc_bias_score": mbfc_scores.get("mbfc_bias_score"),
        "provenance": provenance,
    }

PAGE_CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "page_cache.json")

def _get_page_cache(cache_key: str) -> Any | None:
    """Single-entry read.

    The page cache holds whole analyses (megabytes each). The old code loaded
    the entire file on every call just to look up one key.
    """
    return get_store().get("page_cache", cache_key)

def _put_page_cache(cache_key: str, value: Any) -> None:
    get_store().put("page_cache", cache_key, value)

def _load_page_cache() -> dict[str, Any]:
    """Deprecated: loads every cached analysis into memory. Use _get_page_cache."""
    return get_store().load_all("page_cache")

def _save_page_cache(cache: dict[str, Any]):
    """Deprecated: use _put_page_cache."""
    for k, v in cache.items():
        _put_page_cache(k, v)


def analyze_page(
    url: str,
    max_sources: int | None = 10,
    no_cache: bool = False,
    countries_only: bool = False,
    skip_rate_limiting: bool = False,
    output: str | None = None,
    split_multiple: bool = False,
) -> dict[str, Any]:
    cache_suffix = ""
    if countries_only:
        cache_suffix += "_countries"
    if skip_rate_limiting:
        cache_suffix += "_fast"
    if split_multiple:
        cache_suffix += "_split"
    cache_key = f"{url}_all{cache_suffix}" if max_sources is None else f"{url}_max_{max_sources}{cache_suffix}"
    
    sources: list[dict[str, Any]] = []
    page_metadata = {}
    references = []
    citations = []
    dedup_candidate_urls = []
    
    if not no_cache:
        cached_data = _get_page_cache(cache_key)
        if cached_data is not None:
            if not cached_data.get("is_partial", False):
                return cached_data
                
            sources = cached_data.get("sources", [])
            resumed_revision = cached_data.get("revision_id")
            resumed_page_id = cached_data.get("page_id")
            page_metadata = cached_data.get("page_metadata", {})
            references = cached_data.get("references", [])
            citations = cached_data.get("citations", [])
            dedup_candidate_urls = cached_data.get("dedup_candidate_urls", [])
            if sources:
                sys.stderr.write(f"\nFound partial cache. Resuming analysis from source {len(sources) + 1}...\n")
                sys.stderr.flush()

    if not dedup_candidate_urls:
        try:
            if skip_rate_limiting:
                html = _fetch_url_content_fast(url)
            else:
                html = _fetch_url_content(url)
                
            page_metadata = _extract_page_metadata(html, url)
            references = _extract_references_from_html(html)
            citations = _extract_citations_from_html(html, references)
            
            all_candidate_urls = []
            for cit in citations:
                all_candidate_urls.extend(cit["extracted_urls"])
                
            dedup_candidate_urls = list(dict.fromkeys(all_candidate_urls))
            
            if max_sources is not None:
                dedup_candidate_urls = dedup_candidate_urls[:max_sources]
                
        except Exception as e:
            sys.stderr.write(f"Error extracting page metadata/citations from {url}: {e}\n")
            sys.stderr.flush()
            dedup_candidate_urls = []

    total = len(dedup_candidate_urls)
    for idx, cand_url in enumerate(dedup_candidate_urls, start=1):
        if not skip_rate_limiting:
            progress_pct = int((idx / total) * 100) if total > 0 else 100
            bar_len = 20
            filled_len = int(bar_len * idx // total) if total > 0 else bar_len
            bar = '█' * filled_len + '-' * (bar_len - filled_len)
            sys.stderr.write(f"\r[{bar}] {progress_pct}% complete ({idx}/{total}) - Processing source: {cand_url[:40]}...")
            sys.stderr.flush()
            
        resolved_url = _resolve_archive_url_content(cand_url, skip_rate_limiting=skip_rate_limiting)
        wikidata_info = _fetch_wikidata_enrichment(resolved_url)
        profile = analyze_source_bias(resolved_url, wikidata_info)
        
        citation_text = ""
        for cit in citations:
            if cand_url in cit["extracted_urls"]:
                citation_text = cit["citation_text"]
                break
                
        profile["citation_text"] = citation_text
        
        wikidata_pub = _fetch_wikidata_publisher(profile["domain"])

    page_title_val = _extract_page_title(url)

    if countries_only:
        country_counts = {}
        simplified_sources = []
        for s in sources:
            c_raw = s["geography"]["country"]
            c_list = _split_items(c_raw) if split_multiple else [c_raw]
            for c in c_list:
                country_counts[c] = country_counts.get(c, 0) + 1
            simplified_sources.append({
                "url": s["url"],
                "domain": s["domain"],
                "country": c_raw
            })
        
        geo_distribution = {
            c: {"count": val, "percentage": round(val / len(sources) * 100, 1)}
            for c, val in country_counts.items()
        }
        
        result = {
            "page_title": page_title_val,
            "page_url": url,
            "citation_count": len(citations),
            "source_count": len(sources),
            "countries_only": True,
            "geography_distribution": geo_distribution,
            "sources": simplified_sources,
            "revision_id": revision_id,
            "page_id": page_id,
            "revision_permalink": permalink(url, revision_id),
            "method_version": METHOD_VERSION,
            "is_partial": False
        }
    else:
        aggregated_bias = aggregate_page_bias(sources, split_multiple=split_multiple, page_title=page_title_val)

        result = {
            "page_title": page_title_val,
            "page_url": url,
            "page_metadata": page_metadata,
            "references": references,
            "citation_count": len(citations),
            "source_count": len(sources),
            "sources": sources,
            "aggregated_bias": aggregated_bias,
            "summary": (
                f"Extracted {len(sources)} source links. Analyzed geographic distribution, "
                f"political leanings, reliability tiers, author profiles, and linguistic bias markers."
            ),
            "revision_id": revision_id,
            "page_id": page_id,
            "revision_permalink": permalink(url, revision_id),
            "method_version": METHOD_VERSION,
            "is_partial": False
        }

    if not no_cache:
        _put_page_cache(cache_key, result)

    if output:
        try:
            with open(output, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    return result


def render_report(analysis: dict[str, Any]) -> str:
    if analysis.get("countries_only"):
        lines = [
            f"==================================================",
            f" Wikipedia Source & Country Report (Simplified)",
            f"==================================================",
            f"Page Title:  {analysis['page_title']}",
            f"Page URL:    {analysis['page_url']}",
            f"Total References Found: {analysis['citation_count']}",
            f"Sources Analyzed:       {analysis['source_count']}",
            "",
            f"--------------------------------------------------",
            f" GEOGRAPHIC DISTRIBUTION",
            f"--------------------------------------------------",
        ]
        for country, data in analysis.get("geography_distribution", {}).items():
            lines.append(f"     - {country}: {data['count']} ({data['percentage']}%)")
        
        lines.extend([
            "",
            f"--------------------------------------------------",
            f" SOURCE COUNTRIES",
            f"--------------------------------------------------",
        ])
        for index, s in enumerate(analysis.get("sources", []), start=1):
            lines.append(
                f"{index}. URL:     {s['url']}\n"
                f"   Domain:  {s['domain']}\n"
                f"   Country: {s['country']}\n"
            )
        return "\n".join(lines)

    agg = analysis.get("aggregated_bias", {})
    
    geo_lines = []
    for country, data in agg.get("geography_distribution", {}).items():
        geo_lines.append(f"     - {country}: {data['count']} ({data['percentage']}%)")
    geo_str = "\n".join(geo_lines) if geo_lines else "     - None"
    
    pol_lines = []
    for pol, data in agg.get("political_leaning_distribution", {}).items():
        pol_lines.append(f"     - {pol}: {data['count']} ({data['percentage']}%)")
    pol_str = "\n".join(pol_lines) if pol_lines else "     - None"
    
    rel_lines = []
    for rel, data in agg.get("reliability_distribution", {}).items():
        rel_lines.append(f"     - {rel}: {data['count']} ({data['percentage']}%)")
    rel_str = "\n".join(rel_lines) if rel_lines else "     - None"

    gender_lines = []
    for gender, pct in agg.get("author_gender_distribution_estimate", {}).items():
        gender_lines.append(f"     - {gender}: {pct}%")
    gender_str = "\n".join(gender_lines) if gender_lines else "     - No authors identified"

    type_lines = []
    for k, data in agg.get("author_type_distribution", {}).items():
        type_lines.append(f"     - {k.capitalize()}: {data['count']} ({data['percentage']}%)")
    type_str = "\n".join(type_lines) if type_lines else "     - None"

    h_gender_lines = []
    for k, data in agg.get("human_author_gender_distribution", {}).items():
        h_gender_lines.append(f"     - {k.capitalize()}: {data['count']} ({data['percentage']}%)")
    h_gender_str = "\n".join(h_gender_lines) if h_gender_lines else "     - None"

    h_subregion_lines = []
    for k, data in agg.get("human_author_subregion_distribution", {}).items():
        h_subregion_lines.append(f"     - {k}: {data['count']} ({data['percentage']}%)")
    h_subregion_str = "\n".join(h_subregion_lines) if h_subregion_lines else "     - None"

    h_nat_lines = []
    for k, data in agg.get("human_author_nationality_distribution", {}).items():
        h_nat_lines.append(f"     - {k}: {data['count']} ({data['percentage']}%)")
    h_nat_str = "\n".join(h_nat_lines) if h_nat_lines else "     - None"

    h_cit_lines = []
    for k, data in agg.get("human_author_citizenship_distribution", {}).items():
        h_cit_lines.append(f"     - {k}: {data['count']} ({data['percentage']}%)")
    h_cit_str = "\n".join(h_cit_lines) if h_cit_lines else "     - None"

    h_occ_lines = []
    for k, data in agg.get("human_author_occupation_distribution", {}).items():
        h_occ_lines.append(f"     - {k}: {data['count']} ({data['percentage']}%)")
    h_occ_str = "\n".join(h_occ_lines) if h_occ_lines else "     - None"

    h_emp_lines = []
    for k, data in agg.get("human_author_employer_distribution", {}).items():
        h_emp_lines.append(f"     - {k}: {data['count']} ({data['percentage']}%)")
    h_emp_str = "\n".join(h_emp_lines) if h_emp_lines else "     - None"

    h_emp_country_lines = []
    for k, data in agg.get("human_author_employer_country_distribution", {}).items():
        h_emp_country_lines.append(f"     - {k}: {data['count']} ({data['percentage']}%)")
    h_emp_country_str = "\n".join(h_emp_country_lines) if h_emp_country_lines else "     - None"

    lang_dist_lines = []
    for lang, data in agg.get("language_distribution", {}).items():
        lang_dist_lines.append(f"     - {lang}: {data['count']} ({data['percentage']}%)")
    lang_dist_str = "\n".join(lang_dist_lines) if lang_dist_lines else "     - None"

    source_type_lines = []
    for k, data in agg.get("source_type_distribution", {}).items():
        source_type_lines.append(f"     - {k}: {data['count']} ({data['percentage']}%)")
    source_type_str = "\n".join(source_type_lines) if source_type_lines else "     - None"

    lang_metrics = agg.get("language_bias_metrics", {})
    readability_metrics = agg.get("readability_metrics", {})

    lines = [
        f"==================================================",
        f" Wikipedia Source & Bias Analysis Report",
        f"==================================================",
        f"Page Title:  {analysis['page_title']}",
        f"Page URL:    {analysis['page_url']}",
        f"Total References Found: {analysis['citation_count']}",
        f"Sources Analyzed:       {analysis['source_count']}",
        f"Summary:     {analysis['summary']}",
        "",
        f"--------------------------------------------------",
        f" AGGREGATE PAGE-WIDE BIAS METRICS",
        f"--------------------------------------------------",
        f"1. Geographic Distribution:",
        geo_str,
        "",
        f"2. Political Leaning Distribution:",
        pol_str,
        "",
        f"3. Source Reliability Mix:",
        rel_str,
        "",
        f"4. Estimated Author Gender Mix (Probability-weighted):",
        gender_str,
        "",
        f"4b. Author Type Mix (Human vs Corporate):",
        type_str,
        "",
        f"4c. Human Author Gender Distribution:",
        h_gender_str,
        "",
        f"4d. Human Author Subregion Distribution:",
        h_subregion_str,
        "",
        f"4e. Human Author Country/Nationality Heuristic Distribution:",
        h_nat_str,
        "",
        f"4f. Human Author Citizenship Distribution (Wikidata):",
        h_cit_str,
        "",
        f"4g. Human Author Occupation Distribution (Wikidata):",
        h_occ_str,
        "",
        f"4h. Human Author Employer Affiliations (Wikidata):",
        h_emp_str,
        "",
        f"4i. Human Author Employer Countries (Wikidata):",
        h_emp_country_str,
        "",
        f"5. Citation Language Bias Averages:",
        f"     - Avg Subjectivity Score:   {lang_metrics.get('average_subjectivity_score', 0.0)} (0.0 to 1.0)",
        f"     - Avg Sensationalism Score: {lang_metrics.get('average_sensationalism_score', 0.0)} (0.0 to 1.0)",
        f"     - Opinion Citations:        {lang_metrics.get('opinion_percentage', 0.0)}%",
        "",
        f"6. Source URL Content Averages:",
        f"     - Avg Flesch Reading Ease:  {readability_metrics.get('average_flesch_reading_ease', 'N/A')}",
        f"     - Book/OCLC Source Count:   {agg.get('book_count', 0)}",
        "",
        f"7. Source Language Distribution:",
        lang_dist_str,
        "",
        f"8. Source Type Distribution:",
        source_type_str,
        "",
        f"--------------------------------------------------",
        f" DETAILED SOURCE ANALYSIS",
        f"--------------------------------------------------",
    ]

    for index, source in enumerate(analysis["sources"], start=1):
        wikidata = source.get("wikidata") or {}
        lang_bias = source.get("language_bias") or {}
        readability = source.get("readability") or {}
        wiki_pub = source.get("wikidata_publisher") or {}
        wiki_book = source.get("wikidata_book") or {}
        gbooks = source.get("google_books_metadata") or {}
        oclc_m = source.get("oclc_metadata") or {}
        doi_m = source.get("doi_metadata") or {}
        mbfc_info = source.get("mbfc") or {}

        author_profiles = source.get("author_profiles", [])
        author_strs = []
        for a in author_profiles:
            nationality_str = ", ".join(f"{k} ({round(v*100) if isinstance(v, (int, float)) else 'N/A'}%)" for k, v in a.get("nationality_probability", {}).items())
            gender_str_detail = ", ".join(f"{k} ({round(v*100) if isinstance(v, (int, float)) else 'N/A'}%)" for k, v in a.get("gender_probability", {}).items() if v is not None and v > 0.1)
            
            nt_details = []
            if a.get("author_type"):
                nt_details.append(f"Type: {a['author_type']}")
            if a.get("subregion"):
                nt_details.append(f"Subregion: {a['subregion']}")
            conf = a.get("confidence") or {}
            conf_str = ", ".join(f"{k}: {round(v, 2) if isinstance(v, (int, float)) else 'N/A'}" for k, v in conf.items())
            if conf_str:
                nt_details.append(f"Confidence [{conf_str}]")
            nt_str = f" [Predict: {'; '.join(nt_details)}]" if nt_details else ""

            wiki_a = a.get("wikidata_author", {})
            gt_parts = []
            if wiki_a.get("wikidata_id"):
                gt_parts.append(f"WD: {wiki_a['wikidata_id']}")
                if wiki_a.get("gender"):
                    gt_parts.append(f"Gender: {wiki_a['gender']}")
                if wiki_a.get("citizenships"):
                    gt_parts.append(f"Citizenship: {', '.join(wiki_a['citizenships'])}")
                if wiki_a.get("political_parties"):
                    gt_parts.append(f"Parties: {', '.join(wiki_a['political_parties'])}")
                if wiki_a.get("occupations"):
                    gt_parts.append(f"Occupations: {', '.join(wiki_a['occupations'])}")
                if wiki_a.get("employers"):
                    emp_strs = [f"{e['name']} ({e['country']})" for e in wiki_a["employers"]]
                    gt_parts.append(f"Employers: {', '.join(emp_strs)}")
                    
            gt_str = f" [GT: {'; '.join(gt_parts)}]" if gt_parts else ""
            author_strs.append(f"{a['name']} [Gender: {gender_str_detail} | Est. Nationality: {nationality_str}]{nt_str}{gt_str}")
            
        author_val = "; ".join(author_strs) if author_strs else "unknown"

        pub_parts = []
        if wiki_pub.get("wikidata_id"):
            pub_parts.append(f"WD ID: {wiki_pub['wikidata_id']}")
            if wiki_pub.get("political_leanings"):
                pub_parts.append(f"Leaning: {', '.join(wiki_pub['political_leanings'])}")
            if wiki_pub.get("political_ideologies"):
                pub_parts.append(f"Ideology: {', '.join(wiki_pub['political_ideologies'])}")
            if wiki_pub.get("owners"):
                pub_parts.append(f"Owner: {', '.join(wiki_pub['owners'])}")
            if wiki_pub.get("types"):
                pub_parts.append(f"Types: {', '.join(wiki_pub['types'])}")
        pub_gt_str = f" ({'; '.join(pub_parts)})" if pub_parts else ""

        mbfc_str = ""
        if mbfc_info.get("mbfc_url"):
            mbfc_parts = []
            if mbfc_info.get("bias_rating"):
                mbfc_parts.append(f"Bias: {mbfc_info.get('bias_rating')}")
            if mbfc_info.get("factual_reporting"):
                mbfc_parts.append(f"Factuality: {mbfc_info.get('factual_reporting')}")
            if mbfc_info.get("credibility_rating"):
                mbfc_parts.append(f"Credibility: {mbfc_info.get('credibility_rating')}")
            if mbfc_info.get("country"):
                mbfc_parts.append(f"Country: {mbfc_info.get('country')}")
            if mbfc_info.get("country_freedom_rating"):
                mbfc_parts.append(f"Freedom: {mbfc_info.get('country_freedom_rating')}")
            if mbfc_info.get("media_type"):
                mbfc_parts.append(f"Type: {mbfc_info.get('media_type')}")
            if mbfc_info.get("traffic_popularity"):
                mbfc_parts.append(f"Traffic: {mbfc_info.get('traffic_popularity')}")
            mbfc_str = f" (MBFC {'; '.join(mbfc_parts)})"

        book_details = ""
        if wiki_book.get("wikidata_id"):
            book_details = (
                f"   Book Title:        {wiki_book.get('wikidata_name')}\n"
                f"   Book Authors:      {', '.join(wiki_book.get('authors', []))}\n"
                f"   Book Publisher:    {', '.join(wiki_book.get('publishers', []))}\n"
                f"   Book Pub Date:     {wiki_book.get('pub_date')}\n"
            )
        elif gbooks.get("title"):
            book_details = (
                f"   Book Title:        {gbooks.get('title')}\n"
                f"   Book Authors:      {', '.join(gbooks.get('authors', []))}\n"
                f"   Book Publisher:    {gbooks.get('publisher')}\n"
                f"   Book Pub Date:     {gbooks.get('published_date')}\n"
                f"   Book ISBNs:        {', '.join(gbooks.get('isbns', []))}\n"
            )
        elif oclc_m.get("wikidata_id"):
            book_details = (
                f"   Book Title:        {oclc_m.get('wikidata_name')} (WorldCat OCLC: {oclc_m.get('wikidata_id')})\n"
                f"   Book Authors:      {', '.join(oclc_m.get('authors', []))}\n"
                f"   Book Publisher:    {', '.join(oclc_m.get('publishers', []))}\n"
                f"   Book Pub Date:     {oclc_m.get('pub_date')}\n"
            )

        doi_details = ""
        if doi_m.get("doi"):
            doi_details = (
                f"   DOI Title:         {doi_m.get('title')}\n"
                f"   DOI Authors:       {', '.join(doi_m.get('authors', []))}\n"
                f"   DOI Journal:       {doi_m.get('journal')}\n"
                f"   DOI Publisher:     {doi_m.get('publisher')}\n"
                f"   DOI Date:          {doi_m.get('published_date')}\n"
                f"   DOI Wikidata:      {doi_m.get('wikidata_id') or 'n/a'}\n"
            )

        ease_score = readability.get("flesch_reading_ease")
        grade_score = readability.get("flesch_kincaid_grade")
        readability_str = (
            f"Ease={ease_score} (Grade {grade_score}) - {readability.get('description')}"
            if ease_score is not None else readability.get("description", "N/A")
        )

        lines.append(
            f"{index}. URL: {source['url']}\n"
            f"   Domain:            {source['domain']}{pub_gt_str}{mbfc_str}\n"
            f"   Source Type:       {source['source_type']}\n"
            f"   Geography:         {source['geography']['country']} ({source['geography']['region']})\n"
            f"   Language:          {source['language']}\n"
            f"   Political Leaning: {source['political_leaning']}\n"
            f"   Reliability:       {source['reliability']}\n"
            f"   Wikidata Label:    {wikidata.get('wikidata_label', 'unknown')}\n"
            f"   Author(s):         {author_val}\n"
            f"   Readability Score: {readability_str}\n"
            f"   Language Bias:     Subjectivity={lang_bias.get('subjectivity_score', 0.0)}, "
            f"Sensationalism={lang_bias.get('sensationalism_score', 0.0)}, "
            f"IsOpinion={lang_bias.get('is_opinion', False)} (Language={lang_bias.get('detected_language')}, Source={lang_bias.get('sentiment_source')})\n"
            f"{book_details}"
            f"{doi_details}"
            f"   Citation Text:     \"{source.get('citation_text', 'n/a')}\"\n"
        )
        
    return "\n".join(lines)
