#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from urllib.parse import urlparse
from wikipedia_sources_bias.analysis import analyze_page, _query_wikidata_sparql

# Default fallbacks coordinates for mapping (latitude, longitude)
COUNTRY_COORDINATES = {
    "United States": [37.0902, -95.7129],
    "United Kingdom": [55.3781, -3.4360],
    "France": [46.2276, 2.2137],
    "Germany": [51.1657, 10.4515],
    "Spain": [40.4637, -3.7492],
    "Italy": [41.8719, 12.5674],
    "Canada": [56.1304, -106.3468],
    "Russia": [61.5240, 105.3188],
    "Russia/Eastern Europe": [55.7558, 37.6173],
    "China": [35.8617, 104.1954],
    "India": [20.5937, 78.9629],
    "Japan": [36.2048, 138.2529],
    "South Korea": [35.9078, 127.7669],
    "Switzerland": [46.8182, 8.2275],
    "Australia": [-25.2744, 133.7751],
    "New Zealand": [-40.9006, 174.8860],
    "Brazil": [-14.2350, -51.9253],
    "Mexico": [23.6345, -102.5528],
    "Argentina": [-38.4161, -63.6167],
    "Colombia": [4.5709, -74.2973],
    "South Africa": [-30.5595, 22.9375],
    "Egypt": [26.8206, 30.8025],
    "Israel": [31.0461, 34.8516],
    "Netherlands": [52.1326, 5.2913],
    "Sweden": [60.1282, 18.6435],
    "Norway": [60.4720, 8.4689],
    "Finland": [61.9241, 25.7482],
    "Poland": [51.9194, 19.1451],
    "Ukraine": [48.3794, 31.1656],
    "Taiwan": [23.6978, 120.9605],
    "Singapore": [1.3521, 103.8198],
    "Hong Kong": [22.3193, 114.1694],
    "Austria": [47.5162, 14.5501],
    "Belgium": [50.5039, 4.4699],
    "Ireland": [53.4129, -8.2439],
    "Saudi Arabia": [23.8859, 45.0792],
    "United Arab Emirates": [23.4241, 53.8478],
}

COUNTRY_COORDS_CACHE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
    "country_coordinates_cache.json"
)

def _query_wikidata_country_coords(country_name: str) -> list[float] | None:
    query = f"""
    SELECT ?coords WHERE {{
      ?item rdfs:label "{country_name}"@en.
      ?item wdt:P625 ?coords.
    }} LIMIT 1
    """
    try:
        rows = _query_wikidata_sparql(query)
        if rows and rows[0].get("coords"):
            coords_str = rows[0]["coords"]
            match = re.search(r'Point\(([-\d\.]+)\s+([-\d\.]+)\)', coords_str)
            if match:
                lon = float(match.group(1))
                lat = float(match.group(2))
                return [lat, lon]
    except Exception:
        pass
    return None

def _load_coords_cache() -> dict[str, list[float]]:
    cache = COUNTRY_COORDINATES.copy()
    if os.path.exists(COUNTRY_COORDS_CACHE_FILE):
        try:
            with open(COUNTRY_COORDS_CACHE_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                for k, v in loaded.items():
                    if isinstance(v, list) and len(v) == 2:
                        cache[k] = v
        except Exception:
            pass
    return cache

def _save_coords_cache(cache: dict[str, list[float]]):
    try:
        with open(COUNTRY_COORDS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def get_country_coordinates(country_name: str, cache: dict[str, list[float]]) -> list[float] | None:
    if not country_name or country_name == "Unknown":
        return None
    if country_name in cache:
        return cache[country_name]
        
    coords = _query_wikidata_country_coords(country_name)
    if coords:
        cache[country_name] = coords
        _save_coords_cache(cache)
        return coords
        
    return None

from typing import Any

def generate_source_map(
    data: dict[str, Any],
    coords_cache: dict[str, list[float]] | None = None,
    filter_unresolved: bool = False,
    split_multiple: bool = False,
) -> dict[str, Any]:
    if coords_cache is None:
        coords_cache = _load_coords_cache()
        
    features = []
    country_counts = {}
    
    sources = data.get("sources", [])
    total_srcs = len(sources)

    for s in sources:
        geo = s.get("geography", {})
        country_raw = geo.get("country") or s.get("country", "Unknown")
        region = geo.get("region", "Unknown")
        
        if split_multiple and country_raw:
            target_countries = [c.strip() for c in re.split(r'[,/;]', country_raw) if c.strip()]
        else:
            primary = country_raw.split(",")[0].strip() if country_raw else "Unknown"
            target_countries = [primary]

        for primary_country in target_countries:
            coords = get_country_coordinates(primary_country, coords_cache)
            if filter_unresolved:
                if primary_country == "Unknown" or not coords or coords == [0.0, 0.0]:
                    continue
                    
            country_counts[primary_country] = country_counts.get(primary_country, 0) + 1
            
            if not coords:
                # Fallback by region
                if region == "Europe":
                    coords = [48.69096, 9.14062]
                elif region == "Asia":
                    coords = [34.04786, 100.61035]
                elif region == "North America":
                    coords = [45.4161, -75.7]
                elif region == "South/Central America":
                    coords = [-15.0, -50.0]
                elif region == "Africa":
                    coords = [8.7832, 34.5085]
                elif region == "Middle East":
                    coords = [29.2985, 42.5510]
                elif region == "Oceania":
                    coords = [-22.7359, 140.0188]
                else:
                    coords = [0.0, 0.0]  # Null Island fallback

            # Build geo feature
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [coords[1], coords[0]] # geojson coordinates order: [longitude, latitude]
                },
                "properties": {
                    "url": s.get("url"),
                    "domain": s.get("domain"),
                    "publisher_name": s.get("wikidata_publisher", {}).get("wikidata_name") or s.get("wikidata", {}).get("wikidata_label") or s.get("domain"),
                    "country": primary_country,
                    "region": region,
                    "language": s.get("language"),
                    "political_leaning": s.get("political_leaning"),
                    "reliability": s.get("reliability"),
                    "mbfc": s.get("mbfc", {}),
                }
            }
            features.append(feature)

    # Build country-level features for heatmaps
    country_features = []
    for cname, count in country_counts.items():
        coords = get_country_coordinates(cname, coords_cache)
        if filter_unresolved:
            if cname == "Unknown" or not coords or coords == [0.0, 0.0]:
                continue
        if not coords:
            coords = [0.0, 0.0]
        country_features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [coords[1], coords[0]]
            },
            "properties": {
                "country": cname,
                "source_count": count,
                "percentage": round(count / total_srcs * 100, 1) if total_srcs > 0 else 0.0
            }
        })

    geojson = {
        "type": "FeatureCollection",
        "page_title": data.get("page_title"),
        "page_url": data.get("page_url"),
        "features": features,
        "country_features": country_features
    }
    return geojson

def main() -> None:
    parser = argparse.ArgumentParser(description="Map out Wikipedia page sources geographically")
    parser.add_argument("url", help="Wikipedia article URL")
    parser.add_argument("--max-sources", type=int, default=20, help="Max sources to analyze")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Analyze all sources on the page (overrides --max-sources)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass page cache and force fresh analysis",
    )
    parser.add_argument(
        "--skip-rate-limiting",
        action="store_true",
        help="Bypass all sleep delays and external rate-limited lookups",
    )
    parser.add_argument(
        "--filter-unresolved",
        action="store_true",
        help="Filter out sources that do not resolve to a known country in COUNTRY_COORDINATES",
    )
    parser.add_argument(
        "--split-multiple",
        action="store_true",
        help="Count each country individually when multiple are listed (e.g. 'Canada, United States')",
    )
    parser.add_argument("--output", type=str, default="sources_map.json", help="Path to write JSON mapping to")
    args = parser.parse_args()

    max_sources = None if args.all else args.max_sources
    print(f"Analyzing page: {args.url}...", file=sys.stderr)
    try:
        data = analyze_page(
            args.url,
            max_sources=max_sources,
            no_cache=args.no_cache,
            skip_rate_limiting=args.skip_rate_limiting,
            countries_only=True,
            split_multiple=args.split_multiple
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    geojson = generate_source_map(data, filter_unresolved=args.filter_unresolved, split_multiple=args.split_multiple)

    try:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)
        print(f"Geographic source map successfully written to: {args.output}")
    except Exception as e:
        print(f"Failed to write map output: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
