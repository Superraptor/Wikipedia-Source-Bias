from wikipedia_sources_bias.analysis import analyze_page, render_report


def test_render_report_is_readable():
    result = analyze_page("https://en.wikipedia.org/wiki/Albert_Einstein")
    output = render_report(result)

    assert "Wikipedia source analysis" in output
    assert "Sources:" in output
    assert result["sources"][0]["url"] in output
