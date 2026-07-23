import pytest
from wikipedia_sources_bias.map_sources import generate_source_map

def test_generate_source_map_produces_features():
    data = {
        "page_title": "Donald_Trump",
        "page_url": "https://fr.wikipedia.org/wiki/Donald_Trump",
        "sources": [
            {
                "url": "https://www.nytimes.com/article",
                "domain": "nytimes.com",
                "geography": {"country": "United States", "region": "North America"},
                "language": "English",
                "political_leaning": "center-left",
                "reliability": "high credibility",
                "mbfc": {"bias_rating": "LEFT-CENTER"}
            },
            {
                "url": "https://www.lemonde.fr/article",
                "domain": "lemonde.fr",
                "geography": {"country": "France", "region": "Europe"},
                "language": "French",
                "political_leaning": "center-left",
                "reliability": "high credibility",
                "mbfc": {"bias_rating": "LEFT-CENTER"}
            }
        ]
    }
    
    geojson = generate_source_map(data, filter_unresolved=False, split_multiple=False)
    
    assert geojson["type"] == "FeatureCollection"
    assert geojson["page_title"] == "Donald_Trump"
    assert len(geojson["features"]) == 2
    assert len(geojson["country_features"]) == 2
    
    countries = {f["properties"]["country"] for f in geojson["features"]}
    assert "United States" in countries
    assert "France" in countries
    
    us_feature = next(f for f in geojson["features"] if f["properties"]["country"] == "United States")
    assert us_feature["geometry"]["type"] == "Point"
    assert us_feature["geometry"]["coordinates"] == [-95.7129, 37.0902]
