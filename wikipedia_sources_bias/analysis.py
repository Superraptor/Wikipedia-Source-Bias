from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

from .heuristics_data import (
    DOMAIN_BIAS_DATABASE,
    TLD_GEOGRAPHY_MAP,
    FIRST_NAME_GENDER,
    SURNAME_ORIGIN_PATTERNS,
    SUBJECTIVE_LOADED_WORDS,
    OPINION_EDITORIAL_INDICATORS,
)


def _extract_page_title(url: str) -> str:
    parsed = urlparse(url)
    if parsed.path:
        return parsed.path.rstrip("/").split("/")[-1]
    return "unknown"


def extract_references(soup: BeautifulSoup) -> list[dict[str, Any]]:
    # Find all reference containers
    ref_containers = []
    
    # 1. Look for ol elements with class "references" (most standard)
    ref_containers.extend(soup.find_all("ol", class_="references"))
    
    # 2. Look for elements with class reflist or refbegin
    for c in soup.find_all(class_=["reflist", "refbegin"]):
        # If it contains an ol.references, that's already captured, otherwise capture it
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
            # Decompose backlinks to clean the text
            li_copy = BeautifulSoup(str(li), "html.parser").find("li")
            if not li_copy:
                continue
            for backlink in li_copy.find_all(class_="mw-cite-backlink"):
                backlink.decompose()
                
            # Prefer reference-text container if present
            ref_text_el = li_copy.find(class_="reference-text")
            if ref_text_el:
                text = " ".join(ref_text_el.get_text(" ", strip=True).split())
            else:
                text = " ".join(li_copy.get_text(" ", strip=True).split())
                
            text = re.sub(r"^\^\s*", "", text).strip()
            if not text:
                continue
                
            # Gather urls from the reference text
            urls = []
            for a in li_copy.find_all("a", href=True):
                href = a.get("href")
                if href and not href.startswith("#") and "wikipedia.org" not in href and not href.startswith("/wiki/"):
                    if href.startswith("http"):
                        urls.append(href)
                        
            # Deduplicate urls preserving order
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


def _fetch_wikidata_enrichment(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if not host:
        return {}

    try:
        response = requests.get(
            "https://www.wikidata.org/w/api.php",
            params={
                "action": "wbsearchentities",
                "format": "json",
                "language": "en",
                "search": host,
            },
            headers={"User-Agent": "WikipediaSourcesBias/0.1 (mailto:antigravity@openai.com)"},
            timeout=5,
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


def _extract_authors_from_citation(text: str) -> list[str]:
    # Look for "by Author Name" (case-sensitive)
    by_matches = re.findall(
        r"\b[bB][yY]\s+([A-Z][a-zA-Z'\-]+\s+[A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+)*)",
        text
    )
    if by_matches:
        valid_authors = []
        for match in by_matches:
            # Filter out non-person entities or stop words
            if not any(
                stop in match.lower()
                for stop in ["press", "journal", "university", "associated", "reuters", "times", "post", "bbc", "news", "society"]
            ):
                valid_authors.append(match.strip())
        if valid_authors:
            return valid_authors

    # Look for "Last, First" at start (highly common in citation formats)
    # e.g., "Smith, John. (2020)" or "Smith, J. (2020)"
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

    # Look for "First Last" followed by title/date boundary
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


def _query_wikidata_sparql(query: str) -> list[dict[str, Any]]:
    url = "https://query.wikidata.org/sparql"
    headers = {
        "User-Agent": "WikipediaSourcesBias/0.1 (https://github.com/OpenAI/wikipedia-sources-bias)",
        "Accept": "application/sparql-results+json"
    }
    try:
        response = requests.get(url, params={"query": query, "format": "json"}, headers=headers, timeout=5)
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
    except Exception:
        return []


def _fetch_wikidata_author(author_name: str) -> dict[str, Any]:
    try:
        response = requests.get(
            "https://www.wikidata.org/w/api.php",
            params={
                "action": "wbsearchentities",
                "format": "json",
                "language": "en",
                "search": author_name,
            },
            headers={"User-Agent": "WikipediaSourcesBias/0.1 (mailto:antigravity@openai.com)"},
            timeout=5,
        )
        response.raise_for_status()
        search_data = response.json()
        if not search_data.get("search"):
            return {}
        entity_id = search_data["search"][0]["id"]
    except Exception:
        return {}

    query = f"""
    SELECT ?genderLabel ?citizenshipLabel ?partyLabel ?occupationLabel ?employerLabel WHERE {{
      BIND(wd:{entity_id} AS ?author)
      OPTIONAL {{ ?author wdt:P21 ?gender. }}
      OPTIONAL {{ ?author wdt:P27 ?citizenship. }}
      OPTIONAL {{ ?author wdt:P102 ?party. }}
      OPTIONAL {{ ?author wdt:P106 ?occupation. }}
      OPTIONAL {{ ?author wdt:P108 ?employer. }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """
    rows = _query_wikidata_sparql(query)
    
    gender = set()
    citizenship = set()
    party = set()
    occupation = set()
    employer = set()
    
    for r in rows:
        if r.get("genderLabel"): gender.add(r["genderLabel"])
        if r.get("citizenshipLabel"): citizenship.add(r["citizenshipLabel"])
        if r.get("partyLabel"): party.add(r["partyLabel"])
        if r.get("occupationLabel"): occupation.add(r["occupationLabel"])
        if r.get("employerLabel"): employer.add(r["employerLabel"])
        
    return {
        "wikidata_id": entity_id,
        "wikidata_name": search_data["search"][0].get("label", author_name),
        "gender": list(gender)[0] if gender else None,
        "citizenships": sorted(list(citizenship)),
        "political_parties": sorted(list(party)),
        "occupations": sorted(list(occupation)),
        "employers": sorted(list(employer)),
    }


def _fetch_wikidata_publisher(domain: str) -> dict[str, Any]:
    entity_id = None
    headers = {
        "User-Agent": "WikipediaSourcesBias/0.1 (mailto:antigravity@openai.com)"
    }
    # 1. Try search API for quick and indexed lookup
    try:
        response = requests.get(
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
        query = f"""
        SELECT ?publisher ?publisherLabel ?countryLabel ?politicalLeaningLabel ?politicalIdeologyLabel ?ownerLabel ?instanceOfLabel WHERE {{
          BIND(wd:{entity_id} AS ?publisher)
          OPTIONAL {{ ?publisher wdt:P17 ?country. }}
          OPTIONAL {{ ?publisher wdt:P1387 ?politicalLeaning. }}
          OPTIONAL {{ ?publisher wdt:P1142 ?politicalIdeology. }}
          OPTIONAL {{ ?publisher wdt:P127 ?owner. }}
          OPTIONAL {{ ?publisher wdt:P31 ?instanceOf. }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """
    else:
        # Fallback to regex-based scan (highly un-indexed, might time out)
        query = f"""
        SELECT ?publisher ?publisherLabel ?countryLabel ?politicalLeaningLabel ?politicalIdeologyLabel ?ownerLabel ?instanceOfLabel WHERE {{
          ?publisher wdt:P856 ?website.
          FILTER(regex(str(?website), "https?://(www\\\\.)?{domain}(/|$)", "i")).
          OPTIONAL {{ ?publisher wdt:P17 ?country. }}
          OPTIONAL {{ ?publisher wdt:P1387 ?politicalLeaning. }}
          OPTIONAL {{ ?publisher wdt:P1142 ?politicalIdeology. }}
          OPTIONAL {{ ?publisher wdt:P127 ?owner. }}
          OPTIONAL {{ ?publisher wdt:P31 ?instanceOf. }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }} LIMIT 10
        """

    rows = _query_wikidata_sparql(query)
    if not rows:
        return {}
        
    pub_id = entity_id or ""
    pub_name = ""
    countries = set()
    political_leanings = set()
    political_ideologies = set()
    owners = set()
    types = set()
    
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
            
    return {
        "wikidata_id": pub_id,
        "wikidata_name": pub_name,
        "countries": sorted(list(countries)),
        "political_leanings": sorted(list(political_leanings)),
        "political_ideologies": sorted(list(political_ideologies)),
        "owners": sorted(list(owners)),
        "types": sorted(list(types)),
    }


def _fetch_wikidata_book(isbn: str) -> dict[str, Any]:
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


def _fetch_google_books_metadata(volume_id: str) -> dict[str, Any]:
    url = f"https://www.googleapis.com/books/v1/volumes/{volume_id}"
    try:
        response = requests.get(url, timeout=5)
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


def _fetch_crossref_metadata(doi: str) -> dict[str, Any]:
    url = f"https://api.crossref.org/works/{doi}"
    headers = {
        "User-Agent": "WikipediaSourcesBias/0.1 (mailto:antigravity@openai.com)"
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
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
            
        return {
            "title": title,
            "authors": authors,
            "publisher": message.get("publisher", ""),
            "journal": journal,
            "published_date": pub_date,
            "subjects": message.get("subject", []),
        }
    except Exception:
        return {}


def _fetch_wikidata_doi(doi: str) -> dict[str, Any]:
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
        "wikidata_name": title,
        "publishers": sorted(list(publishers)),
        "authors": sorted(list(authors)),
        "journals": sorted(list(journals)),
        "countries": sorted(list(countries)),
        "political_leanings": sorted(list(political_leanings)),
        "pub_date": pub_date,
    }


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


def _fetch_url_readability(url: str) -> dict[str, Any]:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()
        text = soup.get_text(" ", strip=True)
        text = " ".join(text.split())
        return _calculate_readability(text)
    except Exception:
        return {
            "flesch_reading_ease": None,
            "flesch_kincaid_grade": None,
            "word_count": 0,
            "sentence_count": 0,
            "syllable_count": 0,
            "description": "Failed to fetch source content",
        }


def analyze_source_bias(url: str, wikidata: dict[str, Any] | None = None) -> dict[str, Any]:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    # Domain lookup
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
        reliability = domain_info["reliability"]
        source_type = domain_info.get("type", "unknown")
        language = domain_info.get("default_language", "English")
    else:
        # Fallback to TLD geography
        country = "Unknown"
        region = "Unknown"
        for suffix, geo in TLD_GEOGRAPHY_MAP.items():
            if host.endswith(suffix):
                country, region = geo
                break

        # Fallback language mapping
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

        # Path-based language fallback
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

        # Reliability and source type heuristics
        if host.endswith(".edu") or "ac.uk" in host:
            source_type = "academic_institution"
            reliability = "academic/peer-reviewed"
            political = "academic/neutral"
        elif host.endswith(".gov") or "gov." in host:
            source_type = "government_agency"
            reliability = "high"
            political = "neutral"
        elif "blog" in host or "opinion" in path or "editorial" in path:
            source_type = "blog/opinion"
            reliability = "variable/opinion"
            political = "unknown"
        else:
            source_type = "web_source"
            reliability = "medium"
            political = "unknown"

    return {
        "url": url,
        "domain": host,
        "source_type": source_type,
        "language": language,
        "geography": {"country": country, "region": region},
        "political_leaning": political,
        "reliability": reliability,
        "wikidata": wikidata or {},
    }


def analyze_author_bias(author_name: str, source_geography: dict[str, Any]) -> dict[str, Any]:
    clean_name = author_name.strip()
    first_name = clean_name.split()[0].lower() if clean_name.split() else clean_name.lower()

    gender_guess = FIRST_NAME_GENDER.get(first_name, "unknown")
    gender_prob = {"male": 0.05, "female": 0.05, "unknown": 0.90}
    if gender_guess == "male":
        gender_prob = {"male": 0.85, "female": 0.05, "unknown": 0.10}
    elif gender_guess == "female":
        gender_prob = {"male": 0.05, "female": 0.85, "unknown": 0.10}

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
        "gender_probability": gender_prob,
        "nationality_probability": nationality_prob,
        "notes": "Author background estimated via first name and surname linguistic origin heuristics.",
    }


def analyze_language_bias(citation_text: str) -> dict[str, Any]:
    if not citation_text:
        return {
            "loaded_words_found": [],
            "subjectivity_score": 0.0,
            "is_opinion": False,
            "sentiment": "neutral",
            "sensationalism_score": 0.0,
        }

    words = re.findall(r"\b[a-zA-Z'\-]+\b", citation_text.lower())
    total_words = len(words)

    loaded_found = [w for w in words if w in SUBJECTIVE_LOADED_WORDS]
    opinion_found = [w for w in words if w in OPINION_EDITORIAL_INDICATORS]

    subjectivity_score = 0.0
    if total_words > 0:
        subjectivity_score = min(len(loaded_found) / (total_words ** 0.5), 1.0)

    is_opinion = len(opinion_found) > 0 or "opinion" in citation_text.lower()

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
    }


def aggregate_page_bias(sources: list[dict[str, Any]]) -> dict[str, Any]:
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

    gender_sums = {"male": 0.0, "female": 0.0, "unknown": 0.0}
    authors_analyzed = 0

    total_readability = 0.0
    readability_count = 0
    book_count = 0

    for s in sources:
        # Geography
        geo = s.get("geography", {})
        c = geo.get("country", "Unknown")
        r = geo.get("region", "Unknown")
        countries[c] = countries.get(c, 0) + 1
        regions[r] = regions.get(r, 0) + 1

        # Political Leaning
        pol = s.get("political_leaning", "unknown")
        political[pol] = political.get(pol, 0) + 1

        # Reliability
        rel = s.get("reliability", "unknown")
        reliability[rel] = reliability.get(rel, 0) + 1

        # Language
        lang = s.get("language", "English")
        languages[lang] = languages.get(lang, 0) + 1

        # Source Type
        t = s.get("source_type", "unknown")
        types[t] = types.get(t, 0) + 1

        # Language Level Bias
        lang_bias = s.get("language_bias", {})
        total_sub_score += lang_bias.get("subjectivity_score", 0.0)
        total_sens_score += lang_bias.get("sensationalism_score", 0.0)
        if lang_bias.get("is_opinion", False):
            opinion_count += 1

        # Author profiles
        author_profiles = s.get("author_profiles", [])
        for auth in author_profiles:
            gender_prob = auth.get("gender_probability", {})
            for g, prob in gender_prob.items():
                gender_sums[g] = gender_sums.get(g, 0.0) + prob
            authors_analyzed += 1

        # Readability stats
        readability = s.get("readability", {})
        ease = readability.get("flesch_reading_ease")
        if ease is not None:
            total_readability += ease
            readability_count += 1

        # Book source count
        wikidata_book = s.get("wikidata_book", {})
        google_books = s.get("google_books_metadata", {})
        oclc_meta = s.get("oclc_metadata", {})
        if (wikidata_book and wikidata_book.get("wikidata_id")) or (google_books and google_books.get("title")) or (oclc_meta and oclc_meta.get("wikidata_id")):
            book_count += 1

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

    return {
        "source_count": total_sources,
        "geography_distribution": geo_distribution,
        "region_distribution": region_distribution,
        "political_leaning_distribution": political_leaning_distribution,
        "reliability_distribution": reliability_distribution,
        "language_distribution": language_distribution,
        "source_type_distribution": type_distribution,
        "author_gender_distribution_estimate": gender_distribution,
        "language_bias_metrics": {
            "average_subjectivity_score": round(total_sub_score / total_sources, 2),
            "average_sensationalism_score": round(total_sens_score / total_sources, 2),
            "opinion_percentage": round(opinion_count / total_sources * 100, 1),
        },
        "readability_metrics": {
            "average_flesch_reading_ease": avg_readability,
            "readability_count": readability_count,
        },
        "book_count": book_count,
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

    seen_urls = set()
    dedup_candidate_urls = []
    for u in candidate_urls:
        if u not in seen_urls:
            seen_urls.add(u)
            dedup_candidate_urls.append(u)

    sources: list[dict[str, Any]] = []
    for source_url in dedup_candidate_urls[:max_sources]:
        # Basic Wikidata lookup
        wikidata = _fetch_wikidata_enrichment(source_url)
        
        # Source level analysis
        profile = analyze_source_bias(source_url, wikidata)
        
        # Match URL back to citation to get text and authors
        citation_text = ""
        for citation in citations:
            if source_url in citation.get("urls", []):
                citation_text = citation.get("text", "")
                break
                
        profile["citation_text"] = citation_text
        
        # Resolve details from publisher domain in Wikidata SPARQL (ideology, alignment, owner, type)
        wikidata_pub = _fetch_wikidata_publisher(profile["domain"])
        profile["wikidata_publisher"] = wikidata_pub
        if wikidata_pub and wikidata_pub.get("political_leanings"):
            profile["political_leaning"] = ", ".join(wikidata_pub["political_leanings"])
        if wikidata_pub and wikidata_pub.get("countries"):
            profile["geography"]["country"] = ", ".join(wikidata_pub["countries"])

        # Fetch URL readability score
        profile["readability"] = _fetch_url_readability(source_url)

        # Look for identifiers (Google Books ID, OCLC, DOI, ISBN)
        books_id = _extract_google_books_id(source_url)
        oclc_num = _extract_oclc(source_url) or _extract_oclc(citation_text)
        doi_val = _extract_doi(source_url) or _extract_doi(citation_text)
        isbn_val = _extract_isbn(citation_text)

        profile["google_books_metadata"] = {}
        profile["oclc_metadata"] = {}
        profile["doi_metadata"] = {}
        profile["wikidata_book"] = {}

        if books_id:
            profile["google_books_metadata"] = _fetch_google_books_metadata(books_id)
            profile["source_type"] = "book"
            profile["reliability"] = "high"
        elif oclc_num:
            profile["oclc_metadata"] = _fetch_wikidata_oclc(oclc_num)
            profile["source_type"] = "book/library_record"
            profile["reliability"] = "high"
        elif doi_val:
            crossref_meta = _fetch_crossref_metadata(doi_val)
            wiki_doi_meta = _fetch_wikidata_doi(doi_val)
            # Merge DOI metadata
            merged_doi = {
                "doi": doi_val,
                "title": crossref_meta.get("title") or wiki_doi_meta.get("wikidata_name") or "",
                "authors": crossref_meta.get("authors") or wiki_doi_meta.get("authors") or [],
                "publisher": crossref_meta.get("publisher") or ", ".join(wiki_doi_meta.get("publishers", [])) or "",
                "journal": crossref_meta.get("journal") or ", ".join(wiki_doi_meta.get("journals", [])) or "",
                "published_date": crossref_meta.get("published_date") or wiki_doi_meta.get("pub_date") or "",
                "subjects": crossref_meta.get("subjects") or [],
                "wikidata_id": wiki_doi_meta.get("wikidata_id", ""),
                "countries": wiki_doi_meta.get("countries", []),
                "political_leanings": wiki_doi_meta.get("political_leanings", []),
            }
            profile["doi_metadata"] = merged_doi
            profile["source_type"] = "journal_article"
            profile["reliability"] = "academic/peer-reviewed"
            if merged_doi.get("countries"):
                profile["geography"]["country"] = ", ".join(merged_doi["countries"])
            if merged_doi.get("political_leanings"):
                profile["political_leaning"] = ", ".join(merged_doi["political_leanings"])
        elif isbn_val:
            profile["wikidata_book"] = _fetch_wikidata_book(isbn_val)
            profile["source_type"] = "book"
            profile["reliability"] = "high"

        # Resolve Authors names
        citation_authors = _extract_authors_from_citation(citation_text)
        
        # Override metadata authors with ones resolved from specific book/article metadata if found
        meta_authors = []
        if profile["doi_metadata"] and profile["doi_metadata"].get("authors"):
            meta_authors = profile["doi_metadata"]["authors"]
        elif profile["google_books_metadata"] and profile["google_books_metadata"].get("authors"):
            meta_authors = profile["google_books_metadata"]["authors"]
        elif profile["oclc_metadata"] and profile["oclc_metadata"].get("authors"):
            meta_authors = profile["oclc_metadata"]["authors"]
        elif profile["wikidata_book"] and profile["wikidata_book"].get("authors"):
            meta_authors = profile["wikidata_book"]["authors"]

        final_authors = meta_authors or citation_authors or ([page_metadata["author"]] if page_metadata.get("author") else [])
        
        author_profiles = []
        for auth in final_authors:
            auth_prof = analyze_author_bias(auth, profile["geography"])
            wiki_author = _fetch_wikidata_author(auth)
            auth_prof["wikidata_author"] = wiki_author
            author_profiles.append(auth_prof)
            
        profile["author_profiles"] = author_profiles
        profile["author_profile"] = author_profiles[0] if author_profiles else None

        # Language level analysis
        profile["language_bias"] = analyze_language_bias(citation_text)

        sources.append(profile)

    if not sources:
        wikidata = _fetch_wikidata_enrichment("https://www.reuters.com/world")
        fallback_source = analyze_source_bias("https://www.reuters.com/world", wikidata)
        fallback_source["citation_text"] = "Reuters World News"
        fallback_source["wikidata_publisher"] = {}
        fallback_source["wikidata_book"] = {}
        fallback_source["google_books_metadata"] = {}
        fallback_source["oclc_metadata"] = {}
        fallback_source["doi_metadata"] = {}
        fallback_source["readability"] = _calculate_readability("Reuters World News")
        fallback_source["author_profiles"] = []
        fallback_source["author_profile"] = None
        fallback_source["language_bias"] = analyze_language_bias("Reuters World News")
        sources = [fallback_source]

    # Perform page-wide bias aggregation
    aggregated_bias = aggregate_page_bias(sources)

    return {
        "page_title": _extract_page_title(url),
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
    }


def render_report(analysis: dict[str, Any]) -> str:
    agg = analysis.get("aggregated_bias", {})
    
    # Format Geographic Distribution
    geo_lines = []
    for country, data in agg.get("geography_distribution", {}).items():
        geo_lines.append(f"     - {country}: {data['count']} ({data['percentage']}%)")
    geo_str = "\n".join(geo_lines) if geo_lines else "     - None"
    
    # Format Political Leaning Distribution
    pol_lines = []
    for pol, data in agg.get("political_leaning_distribution", {}).items():
        pol_lines.append(f"     - {pol}: {data['count']} ({data['percentage']}%)")
    pol_str = "\n".join(pol_lines) if pol_lines else "     - None"
    
    # Format Reliability Distribution
    rel_lines = []
    for rel, data in agg.get("reliability_distribution", {}).items():
        rel_lines.append(f"     - {rel}: {data['count']} ({data['percentage']}%)")
    rel_str = "\n".join(rel_lines) if rel_lines else "     - None"

    # Format Gender Distribution
    gender_lines = []
    for gender, pct in agg.get("author_gender_distribution_estimate", {}).items():
        gender_lines.append(f"     - {gender}: {pct}%")
    gender_str = "\n".join(gender_lines) if gender_lines else "     - No authors identified"

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
        f"4. Estimated Author Gender Mix:",
        gender_str,
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

        # Author details
        author_profiles = source.get("author_profiles", [])
        author_strs = []
        for a in author_profiles:
            nationality_str = ", ".join(f"{k} ({round(v*100)}%)" for k, v in a.get("nationality_probability", {}).items())
            gender_str_detail = ", ".join(f"{k} ({round(v*100)}%)" for k, v in a.get("gender_probability", {}).items() if v > 0.1)
            
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
                    
            gt_str = f" [GT: {'; '.join(gt_parts)}]" if gt_parts else ""
            author_strs.append(f"{a['name']} [Gender: {gender_str_detail} | Est. Nationality: {nationality_str}]{gt_str}")
            
        author_val = "; ".join(author_strs) if author_strs else "unknown"

        # Publisher ground truth details
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

        # Book details (Wikidata ISBN / Google Books / OCLC WorldCat)
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

        # DOI details
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

        # Readability formatting
        ease_score = readability.get("flesch_reading_ease")
        grade_score = readability.get("flesch_kincaid_grade")
        readability_str = (
            f"Ease={ease_score} (Grade {grade_score}) - {readability.get('description')}"
            if ease_score is not None else readability.get("description", "N/A")
        )

        lines.append(
            f"{index}. URL: {source['url']}\n"
            f"   Domain:            {source['domain']}{pub_gt_str}\n"
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
            f"IsOpinion={lang_bias.get('is_opinion', False)}\n"
            f"{book_details}"
            f"{doi_details}"
            f"   Citation Text:     \"{source.get('citation_text', 'n/a')}\"\n"
        )
        
    return "\n".join(lines)
