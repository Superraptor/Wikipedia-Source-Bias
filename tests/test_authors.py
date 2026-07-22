"""pyproject and AUTHORS.md must credit the same people.

Paul-Antoine (mentor) was listed on the Wikimania team page and in AUTHORS.md
but missing from pyproject, so the packaged metadata under-credited the team.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def pyproject_authors():
    block = re.search(r"^authors = \[(.*?)^\]", (ROOT / "pyproject.toml").read_text(encoding="utf-8"),
                      re.S | re.M).group(1)
    return set(re.findall(r'\{name = "([^"]+)"\}', block))


def authors_md_names():
    text = (ROOT / "AUTHORS.md").read_text(encoding="utf-8")
    return set(re.findall(r"^\*\*([A-Za-zÀ-ÿ\-]+)(?: \([^)]*\))?\*\*", text, re.M))


def test_the_two_lists_agree():
    assert pyproject_authors() == authors_md_names()


def test_the_whole_team_is_credited():
    assert len(pyproject_authors()) == 10
