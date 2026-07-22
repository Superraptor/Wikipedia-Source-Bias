from bs4 import BeautifulSoup

from wikipedia_sources_bias.analysis import (
    analyze_page,
    extract_references,
    parse_citations,
    _extract_authors_from_citation,
    analyze_source_bias,
    analyze_author_bias,
    analyze_language_bias,
    aggregate_page_bias,
    _extract_isbn,
    _calculate_readability,
    _fetch_wikidata_author,
    _fetch_wikidata_publisher,
    _fetch_wikidata_book,
    _extract_google_books_id,
    _extract_oclc,
    _extract_doi,
    _fetch_google_books_metadata,
    _fetch_crossref_metadata,
    _fetch_wikidata_oclc,
    _fetch_wikidata_doi,
    _extract_author_from_html,
    _detect_language,
)


def test_analyze_page_returns_structured_summary():
    result = analyze_page("https://en.wikipedia.org/wiki/Albert_Einstein", max_sources=2)

    assert result["page_title"] == "Albert_Einstein"
    assert result["source_count"] >= 1
    assert len(result["sources"]) >= 1
    assert result["sources"][0]["url"]
    assert "summary" in result
    assert "aggregated_bias" in result
    assert "geography_distribution" in result["aggregated_bias"]


def test_extract_references_and_parse_citations():
    html = """
    <html><body>
    <h2>References</h2>
    <div class="reflist">
      <ol class="references">
        <li id="cite_note-1"><span class="mw-cite-backlink">^</span> <span class="reference-text">Reuters. <a href="https://www.reuters.com/world">Reuters World</a></span></li>
        <li id="cite_note-2"><span class="mw-cite-backlink">^</span> <span class="reference-text">Smith, Jane. “Example.” <a href="https://www.bbc.com/news">BBC News</a></span></li>
      </ol>
    </div>
    </body></html>
    """
    soup = BeautifulSoup(html, "html.parser")
    references = extract_references(soup)
    citations = parse_citations(references[0]["items"])

    assert references[0]["title"] == "References"
    assert len(citations) == 2
    assert citations[0]["urls"][0] == "https://www.reuters.com/world"
    assert "Reuters" in citations[0]["text"]


def test_extract_authors_from_citation():
    # Last, First style
    assert _extract_authors_from_citation("Smith, John. (2020) 'Scientific discovery'") == ["John Smith"]
    # Last, F. style
    assert _extract_authors_from_citation("Curie, M. (1903)") == ["M. Curie"]
    # "by [Name]" style
    assert _extract_authors_from_citation("Published by Jane Doe at the press") == ["Jane Doe"]
    # Organization filtering
    assert _extract_authors_from_citation("Reuters Staff. 'Breaking news'") == []
    # No author
    assert _extract_authors_from_citation("'No author here.' (2025)") == []


def test_analyze_source_bias():
    # Database domain match
    nytimes_res = analyze_source_bias("https://www.nytimes.com/2026/world")
    assert nytimes_res["domain"] == "nytimes.com"
    assert nytimes_res["geography"]["country"] == "United States"
    assert nytimes_res["political_leaning"] == "center-left"
    assert nytimes_res["reliability"] == "unknown"

    # TLD geography & language fallback
    de_res = analyze_source_bias("https://spiegel.de/international")
    assert de_res["domain"] == "spiegel.de"
    assert de_res["geography"]["country"] == "Germany"
    assert de_res["language"] == "German"

    # Academic fallback
    edu_res = analyze_source_bias("https://physics.mit.edu/papers")
    assert edu_res["source_type"] == "academic_institution"
    assert edu_res["reliability"] == "unknown"


def test_analyze_author_bias():
    import wikipedia_sources_bias.analysis as analysis
    original_fn = analysis._get_nametrace_prediction
    analysis._get_nametrace_prediction = lambda name: None
    try:
        # Female gender heuristic, no origin match -> source geography fallback
        author_res = analyze_author_bias("Jane Doe", {"country": "United Kingdom", "region": "Europe"})
        assert author_res["name"] == "Jane Doe"
        assert author_res["gender_probability"]["female"] > 0.8
        assert author_res["nationality_probability"]["United Kingdom"] == 0.7

        # Surname pattern match (Eastern European / Russian)
        author_res2 = analyze_author_bias("Ivan Petrov", {"country": "Germany", "region": "Europe"})
        assert author_res2["nationality_probability"]["Russia/Eastern Europe"] == 0.7
    finally:
        analysis._get_nametrace_prediction = original_fn


def test_analyze_author_bias_nametrace():
    res = analyze_author_bias("Jean Dupont", {"country": "Germany", "region": "Europe"})
    assert res["name"] == "Jean Dupont"
    assert res["gender_probability"]["male"] > 0.6
    # Should resolve to Western Europe via nametrace
    assert any("Western Europe" in k for k in res["nationality_probability"].keys())


def test_analyze_language_bias():
    # Neutral citation
    neutral_res = analyze_language_bias("Standard reports from the committee in 2021.")
    assert neutral_res["subjectivity_score"] == 0.0
    assert neutral_res["sensationalism_score"] == 0.0
    assert neutral_res["sentiment"] == "neutral"

    # Heavily biased/loaded citation
    biased_res = analyze_language_bias("OUTRAGEOUS: The corrupt tyrant mastermind launched a catastrophic disaster!")
    assert biased_res["subjectivity_score"] > 0.3
    assert biased_res["sensationalism_score"] > 0.3
    assert biased_res["sentiment"] == "negative"
    assert biased_res["is_opinion"] is False

    # Opinion citation
    opinion_res = analyze_language_bias("Opinion: The new policy is a complete disaster.")
    assert opinion_res["is_opinion"] is True


def test_aggregate_page_bias():
    sources = [
        {
            "geography": {"country": "United States", "region": "North America"},
            "political_leaning": "center-left",
            "reliability": "high",
            "language": "English",
            "source_type": "newspaper",
            "language_bias": {"subjectivity_score": 0.1, "sensationalism_score": 0.0, "is_opinion": False},
            "author_profiles": [
                {"gender_probability": {"male": 0.85, "female": 0.05, "unknown": 0.10}}
            ]
        },
        {
            "geography": {"country": "United Kingdom", "region": "Europe"},
            "political_leaning": "center",
            "reliability": "high",
            "language": "English",
            "source_type": "newspaper",
            "language_bias": {"subjectivity_score": 0.5, "sensationalism_score": 0.4, "is_opinion": True},
            "author_profiles": []
        }
    ]

    agg = aggregate_page_bias(sources)
    assert agg["source_count"] == 2
    assert agg["geography_distribution"]["United States"]["count"] == 1
    assert agg["political_leaning_distribution"]["center-left"]["count"] == 1
    assert agg["language_bias_metrics"]["opinion_percentage"] == 50.0
    assert agg["author_gender_distribution_estimate"]["male"] == 85.0


def test_extract_isbn():
    assert _extract_isbn("Einstein, Albert. Collected Papers. ISBN 978-3-11-016480-1.") == "9783110164801"
    assert _extract_isbn("Some book, ISBN-10: 0596520689.") == "0596520689"
    assert _extract_isbn("No ISBN identifier here.") is None


def test_readability_calculation():
    # Simple sentences, high readability
    easy_res = _calculate_readability("The cat sat on the mat. The dog ran fast.")
    assert easy_res["flesch_reading_ease"] > 80.0
    assert easy_res["description"] in ("Easy", "Very Easy")

    # Difficult sentences, low readability
    hard_res = _calculate_readability("Computational neuroscience investigates the intricate mechanisms underlying cognitive functionality.")
    assert hard_res["flesch_reading_ease"] < 40.0
    assert hard_res["description"] in ("Difficult", "Very Difficult")


def test_wikidata_fetching_graceful_fallbacks():
    # Test that querying unknown/random strings returns empty dicts or handles timeouts gracefully
    assert _fetch_wikidata_author("NonExistentAuthorXYZ123") == {}
    assert _fetch_wikidata_publisher("nonexistentdomainxyz.xyz") == {}
    assert _fetch_wikidata_book("9999999999999") == {}


def test_google_books_id_extraction():
    assert _extract_google_books_id("https://books.google.com/books?id=9ShCF-9yloEC&pg=PA14") == "9ShCF-9yloEC"
    assert _extract_google_books_id("https://books.google.fr/books?id=abc-123_xyz") == "abc-123_xyz"
    assert _extract_google_books_id("https://www.google.com") is None


def test_oclc_extraction():
    assert _extract_oclc("https://www.worldcat.org/oclc/2307600") == "2307600"
    assert _extract_oclc("Smith, J. Title. OCLC 123456.") == "123456"
    assert _extract_oclc("No identifiers.") is None


def test_doi_extraction():
    assert _extract_doi("https://doi.org/10.1098%2Frsbm.1955.0005") == "10.1098/rsbm.1955.0005"
    assert _extract_doi("doi:10.1016/j.cell.2021.01.001") == "10.1016/j.cell.2021.01.001"
    assert _extract_doi("No DOI.") is None


def test_apis_graceful_fallbacks():
    assert _fetch_google_books_metadata("nonexistentid123") == {}
    assert _fetch_crossref_metadata("10.9999/nonexistentdoi") == {}
    assert _fetch_wikidata_oclc("000000000") == {}
    assert _fetch_wikidata_doi("10.9999/nonexistentdoi") == {}


def test_detect_language():
    assert _detect_language("The quick brown fox jumps over the lazy dog.") == "English"
    assert _detect_language("Le chat noir boit du lait frais.") == "French"
    assert _detect_language("Der Hund rennt schnell durch den Wald.") == "German"
    assert _detect_language("El perro corre rápidamente por el bosque.") == "Spanish"
    assert _detect_language("Il cane corre velocemente nel bosco.") == "Italian"


def test_extract_author_from_html():
    html_meta = '<html><head><meta name="author" content="Jane Doe"></head><body></body></html>'
    soup = BeautifulSoup(html_meta, "html.parser")
    assert _extract_author_from_html(soup) == "Jane Doe"

    html_json_ld = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "NewsArticle",
          "author": {
            "@type": "Person",
            "name": "Jean Dupont"
          }
        }
        </script>
      </head>
      <body></body>
    </html>
    """
    soup_json = BeautifulSoup(html_json_ld, "html.parser")
    assert _extract_author_from_html(soup_json) == "Jean Dupont"

    html_fallback = '<html><body><span class="author">By Marie Curie</span></body></html>'
    soup_fb = BeautifulSoup(html_fallback, "html.parser")
    assert _extract_author_from_html(soup_fb) == "Marie Curie"


def test_split_items_and_aggregate_split_multiple():
    from wikipedia_sources_bias.analysis import _split_items, aggregate_page_bias

    assert _split_items("Canada, United States") == ["Canada", "United States"]
    assert _split_items("France / Germany") == ["France", "Germany"]
    assert _split_items("center-left, center-right") == ["center-left", "center-right"]

    mock_sources = [
        {
            "geography": {"country": "Canada, United States", "region": "North America"},
            "political_leaning": "center-left, center-right",
            "reliability": "high",
            "language": "English",
            "source_type": "journal_article",
        }
    ]

    # Without split_multiple
    agg_single = aggregate_page_bias(mock_sources, split_multiple=False)
    assert "Canada, United States" in agg_single["geography_distribution"]
    assert agg_single["geography_distribution"]["Canada, United States"]["count"] == 1

    # With split_multiple
    agg_split = aggregate_page_bias(mock_sources, split_multiple=True)
    assert "Canada" in agg_split["geography_distribution"]
    assert "United States" in agg_split["geography_distribution"]
    assert agg_split["geography_distribution"]["Canada"]["count"] == 1
    assert agg_split["geography_distribution"]["United States"]["count"] == 1
    assert "center-left" in agg_split["political_leaning_distribution"]
    assert "center-right" in agg_split["political_leaning_distribution"]


def test_database_domain_detection():
    from wikipedia_sources_bias.analysis import _is_database_domain

    assert _is_database_domain("pubmed.ncbi.nlm.nih.gov") is True
    assert _is_database_domain("ncbi.nlm.nih.gov") is True
    assert _is_database_domain("europepmc.org") is True
    assert _is_database_domain("books.google.fr") is True
    assert _is_database_domain("nytimes.com") is False


def test_parse_mbfc_scores_and_composite_reliability():
    from wikipedia_sources_bias.analysis import _parse_mbfc_scores, _calculate_composite_reliability

    mbfc_sample = {
        "credibility_rating": "HIGH CREDIBILITY",
        "factual_reporting": "MOSTLY FACTUAL (2.9)",
        "bias_rating": "LEFT-CENTER (-3.5)",
    }
    parsed = _parse_mbfc_scores(mbfc_sample)
    assert parsed["mbfc_credibility_score"] == 100.0
    assert parsed["mbfc_factuality_score"] == 60.0

    profile = {
        "source_type": "news_outlet",
    }
    rel = _calculate_composite_reliability(profile, mbfc_sample)
    assert rel["composite_reliability_score"] > 70.0
    assert profile["reliability"] == "high credibility"
    assert "Media Bias/Fact Check (MBFC)" in rel["provenance"]


def test_geographic_diversity_score_and_jsd():
    from wikipedia_sources_bias.analysis import (
        _calculate_jsd,
        _determine_geographic_specificity,
        _calculate_geographic_diversity_score,
    )

    p = {"France": 0.6, "Germany": 0.4}
    q = {"France": 0.6, "Germany": 0.4}
    assert _calculate_jsd(p, q) == 0.0

    p_diff = {"France": 1.0}
    q_diff = {"China": 1.0}
    assert _calculate_jsd(p_diff, q_diff) == 1.0

    country_counts_local = {"France": 8, "Germany": 2}
    scope_local, primary_local = _determine_geographic_specificity("Emmanuel Macron", [], country_counts_local)
    assert scope_local == "local"
    assert primary_local == "France"

    country_counts_global = {"United States": 3, "France": 3, "Japan": 3, "Brazil": 3}
    scope_global, primary_global = _determine_geographic_specificity("Climate Change", [], country_counts_global)
    assert scope_global == "global"

    mock_sources = [
        {"geography": {"country": "France", "region": "Europe"}},
        {"geography": {"country": "France", "region": "Europe"}},
        {"geography": {"country": "Germany", "region": "Europe"}},
        {"geography": {"country": "United States", "region": "North America"}},
    ]
    geo_metrics = _calculate_geographic_diversity_score(mock_sources, page_title="Emmanuel Macron")
    assert "geographic_diversity_score" in geo_metrics
    assert 0.0 <= geo_metrics["geographic_diversity_score"] <= 100.0
    assert geo_metrics["geographic_scope"] == "local"
    assert geo_metrics["primary_country"] == "France"


def test_political_spread_score_and_axis_mapping():
    from wikipedia_sources_bias.analysis import (
        _map_political_to_numeric_axis,
        _detect_consensus_topic_type,
        _calculate_political_spread_score,
    )

    assert _map_political_to_numeric_axis("Far Left") == -3.0
    assert _map_political_to_numeric_axis("Center-Left") == -1.0
    assert _map_political_to_numeric_axis("Center") == 0.0
    assert _map_political_to_numeric_axis("Right-Center") == 1.0
    assert _map_political_to_numeric_axis("Far Right") == 3.0
    assert _map_political_to_numeric_axis(None, mbfc_bias_score=-5.0) == -1.5

    assert _detect_consensus_topic_type("Global warming") == "consensus_science"
    assert _detect_consensus_topic_type("Carbon tax policy") == "mixed_policy"
    assert _detect_consensus_topic_type("French presidential election") == "open_political"

    mock_sources = [
        {"political_leaning": "Left-Center", "mbfc": {"mbfc_bias_score": -3.0}},
        {"political_leaning": "Center", "mbfc": {"mbfc_bias_score": 0.0}},
        {"political_leaning": "Right-Center", "mbfc": {"mbfc_bias_score": 3.0}},
    ]
    pol_metrics = _calculate_political_spread_score(mock_sources, page_title="Taxation in France")
    assert "political_spread_score" in pol_metrics
    assert 0.0 <= pol_metrics["political_spread_score"] <= 100.0
    assert pol_metrics["spread_category"] == "healthy_diversity"


def test_population_caching_and_gender_parity_metrics():
    from wikipedia_sources_bias.analysis import (
        _get_cached_country_population,
        analyze_author_bias,
        _calculate_gender_parity_metrics,
    )

    # Test population caching
    pop_fr = _get_cached_country_population("France")
    assert pop_fr > 60000000.0

    # Test author gender inference & provenance
    auth_female = analyze_author_bias("Marie Curie", {"country": "France"}, skip_rate_limiting=True)
    assert auth_female["is_human"] is True
    assert auth_female["gender"] in ("female", "unknown")
    assert "gender_source" in auth_female

    # Test gender parity metrics calculation
    mock_sources = [
        {
            "author_profiles": [
                {"is_human": True, "gender": "female", "gender_source": "Nametrace", "gender_probability": {"female": 0.95}},
                {"is_human": True, "gender": "male", "gender_source": "Nametrace", "gender_probability": {"male": 0.90}},
            ]
        },
        {
            "author_profiles": [
                {"is_human": True, "gender": "female", "gender_source": "Genderize.io", "gender_probability": {"female": 0.80}},
                {"is_human": True, "gender": "unknown", "gender_source": "unknown", "gender_probability": {"unknown": 0.90}},
            ]
        }
    ]
    parity_metrics = _calculate_gender_parity_metrics(mock_sources)
    assert "gender_parity_score" in parity_metrics
    assert 0.0 <= parity_metrics["gender_parity_score"] <= 100.0
    assert parity_metrics["human_author_count"] == 4
    assert parity_metrics["gender_counts"]["female"] == 2
    assert parity_metrics["gender_counts"]["male"] == 1
    assert parity_metrics["gender_counts"]["unknown"] == 1
    assert parity_metrics["unknown_author_proportion"] == 0.25
    assert parity_metrics["provenance_breakdown"]["Nametrace"] == 2
    assert parity_metrics["provenance_breakdown"]["Genderize.io"] == 1


def test_multilingual_sentiment_and_neutrality_score():
    from wikipedia_sources_bias.analysis import (
        analyze_language_bias,
        _calculate_neutrality_metrics,
    )

    # Test analyze_language_bias with fallback provenance
    res_en = analyze_language_bias("The article provides an objective summary of recent developments.")
    assert "sentiment" in res_en
    assert "sentiment_source" in res_en

    res_fr = analyze_language_bias("Un rapport catastrophique et monstrueux publié par le gouvernement.")
    assert res_fr["detected_language"] == "French"
    assert res_fr["subjectivity_score"] > 0.0

    # Test neutrality score calculation
    mock_sources = [
        {
            "language_bias": {
                "subjectivity_score": 0.10,
                "sensationalism_score": 0.05,
                "is_opinion": False,
                "loaded_words_found": [],
                "sentiment": "neutral",
                "sentiment_source": "Multilingual Lexical Heuristics",
            }
        },
        {
            "language_bias": {
                "subjectivity_score": 0.20,
                "sensationalism_score": 0.15,
                "is_opinion": True,
                "loaded_words_found": ["disastrous"],
                "sentiment": "negative",
                "sentiment_source": "Hugging Face (XLM-RoBERTa)",
            }
        }
    ]
    neutrality = _calculate_neutrality_metrics(mock_sources)
    assert "neutrality_score" in neutrality
    assert 0.0 <= neutrality["neutrality_score"] <= 100.0
    assert neutrality["opinion_citation_percentage"] == 50.0
    assert neutrality["sentiment_source_breakdown"]["Hugging Face (XLM-RoBERTa)"] == 1
    assert neutrality["sentiment_source_breakdown"]["Multilingual Lexical Heuristics"] == 1


def test_wikidata_neighbors_caching_and_metric_descriptions():
    from wikipedia_sources_bias.analysis import (
        _get_cached_country_neighbors,
        aggregate_page_bias,
    )

    # Test P47 Wikidata border caching
    neighbors = _get_cached_country_neighbors("France", skip_rate_limiting=True)
    assert isinstance(neighbors, set)
    assert len(neighbors) > 0

    # Test metric description fields in aggregate output
    mock_sources = [
        {
            "geography": {"country": "France", "region": "Europe"},
            "political_leaning": "Center",
            "mbfc": {"mbfc_bias_score": 0.0, "credibility_rating": "HIGH"},
            "language_bias": {"subjectivity_score": 0.10, "sensationalism_score": 0.05, "is_opinion": False},
        }
    ]
    agg = aggregate_page_bias(mock_sources, page_title="Emmanuel Macron")
    assert "description" in agg["reliability_metrics"]
    assert "description" in agg["geographic_diversity_metrics"]
    assert "description" in agg["political_spread_metrics"]
    assert "description" in agg["gender_parity_metrics"]
    assert "description" in agg["neutrality_metrics"]
    assert "description" in agg["language_bias_metrics"]









