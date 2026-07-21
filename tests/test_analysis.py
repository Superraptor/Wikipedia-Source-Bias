from bs4 import BeautifulSoup

from wikipedia_sources_bias.analysis import analyze_page, extract_references, parse_citations


def test_analyze_page_returns_structured_summary():
    result = analyze_page("https://en.wikipedia.org/wiki/Albert_Einstein")

    assert result["page_title"] == "Albert_Einstein"
    assert result["source_count"] >= 1
    assert len(result["sources"]) >= 1
    assert result["sources"][0]["url"]
    assert "summary" in result


def test_extract_references_and_parse_citations():
    html = """
    <html><body>
    <h2>References</h2>
    <div class="reflist">
      <ol>
        <li id="cite_note-1"><span class="reference-text">Reuters. <a href="https://www.reuters.com/world">Reuters World</a></span></li>
        <li id="cite_note-2">Smith, Jane. “Example.” <a href="https://www.bbc.com/news">BBC News</a></li>
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
