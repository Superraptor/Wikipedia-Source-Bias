import os
import json
import pytest
from unittest.mock import patch, MagicMock
from wikipedia_sources_bias.cli import _sanitize_filename, main


def test_sanitize_filename():
    assert _sanitize_filename("Emmanuel Macron") == "emmanuel_macron"
    assert _sanitize_filename("Guerre Israël-Hamas") == "guerre_israël-hamas"
    assert _sanitize_filename("Special/Character? Title") == "special_character_title"
    assert _sanitize_filename("///") == "unnamed_article"
    assert _sanitize_filename("   ") == "unnamed_article"
    assert _sanitize_filename("A/B\\C*D?E\"F<G>H|I") == "a_b_c_d_e_f_g_h_i"


@patch("wikipedia_sources_bias.cli.argparse.ArgumentParser.parse_args")
def test_cli_requires_url_or_batch(mock_parse_args):
    # If neither is provided, parser.error is called
    mock_args = MagicMock()
    mock_args.url = None
    mock_args.batch_file = None
    mock_parse_args.return_value = mock_args

    with pytest.raises(SystemExit):
        main()


@patch("wikipedia_sources_bias.cli.argparse.ArgumentParser.parse_args")
@patch("wikipedia_sources_bias.cli.analyze_page")
def test_cli_single_url_works(mock_analyze, mock_parse_args):
    mock_args = MagicMock()
    mock_args.url = "https://en.wikipedia.org/wiki/Albert_Einstein"
    mock_args.batch_file = None
    mock_args.format = "json"
    mock_args.all = False
    mock_args.max_sources = 10
    mock_args.no_cache = False
    mock_args.countries_only = False
    mock_args.skip_rate_limiting = False
    mock_args.output = None
    mock_parse_args.return_value = mock_args

    mock_analyze.return_value = {"page_title": "Albert_Einstein", "sources": []}

    # Should run to completion without error
    with patch("builtins.print") as mock_print:
        main()
        mock_analyze.assert_called_once_with(
            "https://en.wikipedia.org/wiki/Albert_Einstein",
            max_sources=10,
            no_cache=False,
            countries_only=False,
            skip_rate_limiting=False
        )
        # Verify JSON print was called
        mock_print.assert_called()


@patch("wikipedia_sources_bias.cli.argparse.ArgumentParser.parse_args")
@patch("wikipedia_sources_bias.cli.analyze_page")
@patch("wikipedia_sources_bias.cli.generate_source_map")
def test_cli_batch_mode_works(mock_generate_map, mock_analyze, mock_parse_args, tmp_path):
    # Create a mock batch file with titles
    batch_file = tmp_path / "batch.txt"
    batch_file.write_text("Emmanuel Macron\n# Comment line\nRussie\n\n", encoding="utf-8")

    results_dir = tmp_path / "results"

    mock_args = MagicMock()
    mock_args.url = None
    mock_args.batch_file = str(batch_file)
    mock_args.prefix = "fr"
    mock_args.results_dir = str(results_dir)
    mock_args.all = False
    mock_args.max_sources = 5
    mock_args.no_cache = True
    mock_args.countries_only = False
    mock_args.skip_rate_limiting = True
    mock_parse_args.return_value = mock_args

    # Mock analysis responses
    mock_analyze.side_effect = [
        {"page_title": "Emmanuel_Macron", "sources": [{"domain": "lemonde.fr"}]},
        {"page_title": "Russie", "sources": [{"domain": "rt.com"}]}
    ]

    mock_generate_map.side_effect = [
        {"type": "FeatureCollection", "features": ["map1"]},
        {"type": "FeatureCollection", "features": ["map2"]}
    ]

    main()

    # Assert analyze_page was called for each article with fr prefix and quoted spaces
    mock_analyze.assert_any_call(
        "https://fr.wikipedia.org/wiki/Emmanuel_Macron",
        max_sources=5,
        no_cache=True,
        countries_only=False,
        skip_rate_limiting=True
    )
    mock_analyze.assert_any_call(
        "https://fr.wikipedia.org/wiki/Russie",
        max_sources=5,
        no_cache=True,
        countries_only=False,
        skip_rate_limiting=True
    )

    # Check files were created in results directory
    assert os.path.exists(results_dir / "emmanuel_macron_analysis.json")
    assert os.path.exists(results_dir / "emmanuel_macron_map.json")
    assert os.path.exists(results_dir / "russie_analysis.json")
    assert os.path.exists(results_dir / "russie_map.json")

    # Verify content of saved files
    with open(results_dir / "emmanuel_macron_analysis.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["page_title"] == "Emmanuel_Macron"

    with open(results_dir / "emmanuel_macron_map.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        assert "map1" in data["features"]
