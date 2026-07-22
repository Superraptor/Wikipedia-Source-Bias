"""The mock must never stand in for a real analysis without being asked.

Before this, `run_analysis` caught ImportError and silently substituted
backend/mock.py. Because gunicorn runs with --chdir backend, a packaging
mistake that made `wikipedia_sources_bias` unimportable produced a perfectly
green deploy that served fabricated numbers as if they were measurements.
"""
import builtins

import pytest

import runner
from runner import AnalysisUnavailable


@pytest.fixture
def analyzer_unimportable(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "wikipedia_sources_bias":
            raise ImportError("simulated missing package")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)


def test_missing_analyzer_raises_when_mock_disallowed(
    analyzer_unimportable, monkeypatch
):
    monkeypatch.setattr(runner.config, "allow_mock", lambda: False)
    with pytest.raises(AnalysisUnavailable):
        runner._load_analyzer()


def test_missing_analyzer_falls_back_only_when_explicitly_allowed(
    analyzer_unimportable, monkeypatch
):
    monkeypatch.setattr(runner.config, "allow_mock", lambda: True)
    analyze = runner._load_analyzer()
    assert analyze is not None
    result = analyze("https://fr.wikipedia.org/wiki/Emmanuel_Macron")
    assert isinstance(result, dict)


def test_real_analyzer_is_preferred(monkeypatch):
    sentinel = {"page_title": "Real", "sources": [], "source_count": 0}
    monkeypatch.setattr(runner.config, "allow_mock", lambda: True)

    import wikipedia_sources_bias

    monkeypatch.setattr(
        wikipedia_sources_bias, "analyze_page", lambda url: sentinel, raising=False
    )
    analyze = runner._load_analyzer()
    assert analyze("https://example.org") is sentinel
