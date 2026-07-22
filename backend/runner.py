"""The actual analysis call, shared by the web tier and the worker."""
import sys

import config
from analyzer import normalize_analysis


class AnalysisUnavailable(RuntimeError):
    """The real analyzer could not be imported and mocking is not allowed."""


def _load_analyzer():
    """Return a callable url -> raw analysis dict.

    `wikipedia_sources_bias` is installed as a real package (it is listed as
    `.` in requirements.txt), so this import does not depend on the process
    working directory. That matters because gunicorn runs with --chdir backend,
    which drops the repo root from sys.path.
    """
    try:
        from wikipedia_sources_bias import analyze_page

        return analyze_page
    except ImportError as exc:
        if not config.allow_mock():
            raise AnalysisUnavailable(
                "wikipedia_sources_bias is not importable and ALLOW_MOCK_ANALYSIS "
                "is not enabled. Refusing to serve mock data as if it were real. "
                f"Original import error: {exc}"
            ) from exc
        from mock import mock_analysis

        print(
            "WARNING: serving MOCK analysis data (ALLOW_MOCK_ANALYSIS is on).",
            file=sys.stderr,
        )
        return mock_analysis


def run_analysis(url, progress_cb=None):
    analyze = _load_analyzer()
    if progress_cb is None:
        return normalize_analysis(analyze(url))
    try:
        raw = analyze(url, progress_cb=progress_cb)
    except TypeError:
        # The demo mock takes only a url.
        raw = analyze(url)
    return normalize_analysis(raw)
