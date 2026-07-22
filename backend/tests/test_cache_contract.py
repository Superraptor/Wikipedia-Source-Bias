"""The real Cache must implement everything the app and worker call on it.

/api/status returned 500 in production with
`AttributeError: 'Cache' object has no attribute 'queue_stats'`. Every app test
injects a FakeCache, so a method missing from the REAL class was invisible to
the whole suite -- and the frontend silently fell back to its placeholder list,
which is why the landing page claimed "0 sources".
"""
import re
from pathlib import Path

import pytest

from cache import Cache

BACKEND = Path(__file__).resolve().parents[1]
CALLERS = ("app.py", "worker.py", "populate_cache.py")


def called_methods():
    names = set()
    for filename in CALLERS:
        path = BACKEND / filename
        if not path.exists():
            continue
        names |= set(re.findall(r"cache\.([a-zA-Z_][a-zA-Z0-9_]*)\(", path.read_text(encoding="utf-8")))
    return names


def test_every_method_the_callers_use_exists():
    missing = sorted(n for n in called_methods() if not hasattr(Cache, n))
    assert not missing, f"Cache is missing: {missing}"


@pytest.mark.parametrize("name", sorted(called_methods()))
def test_method_is_callable(name):
    assert callable(getattr(Cache, name, None)), name


def test_the_status_view_contract_specifically():
    """These three are what /api/status and /status depend on."""
    for name in ("queue_stats", "recent", "row_for"):
        assert hasattr(Cache, name), name
