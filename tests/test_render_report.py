from wikipedia_sources_bias.analysis import analyze_page, render_report


def test_render_report_is_readable():
    result = analyze_page("https://en.wikipedia.org/wiki/Albert_Einstein", max_sources=2)
    output = render_report(result)

    assert "Wikipedia Source & Bias Analysis Report" in output
    assert "AGGREGATE PAGE-WIDE BIAS METRICS" in output
    assert "DETAILED SOURCE ANALYSIS" in output
    assert result["sources"][0]["url"] in output
