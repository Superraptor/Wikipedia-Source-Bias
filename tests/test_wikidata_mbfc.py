"""Tests for the P9852 proposal tool.

The verification tests use recorded page fragments rather than the network, so
they assert the *rule* (a profile must name our domain) rather than MBFC's
current content.
"""
import pytest

from wikidata_mbfc import cli, domains, emit, mbfc, wikidata

# Abridged from the real https://mediabiasfactcheck.com/le-monde-bias/
LE_MONDE_PAGE = """
<div class="entry-content">
  <p><strong>Factual Reporting: HIGH</strong></p>
  <p>Country: France</p>
  <p><span>Source: <a href="https://www.lemonde.fr/">https://www.lemonde.fr/</a></span></p>
</div>
"""

# Abridged from https://mediabiasfactcheck.com/cairns-news-bias-and-credibility/,
# which is where MBFC 301-redirects a request for /cairn/.
CAIRNS_NEWS_PAGE = """
<div class="entry-content">
  <p><strong>Factual Reporting: LOW</strong></p>
  <p>Source: <a href="https://cairnsnews.org/">https://cairnsnews.org/</a></p>
</div>
"""

NO_SOURCE_PAGE = "<div class='entry-content'><p>Factual Reporting: HIGH</p></div>"


class FakeResponse:
    def __init__(self, text, url, status_code=200):
        self.text = text
        self.url = url
        self.status_code = status_code
        self.headers = {}


class TestRegistrableDomain:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("https://www.lemonde.fr/politique/article", "lemonde.fr"),
            ("lemonde.fr", "lemonde.fr"),
            ("WWW.LeMonde.FR", "lemonde.fr"),
            ("https://www.bbc.co.uk/news", "bbc.co.uk"),
            ("tempsreel.nouvelobs.com", "nouvelobs.com"),
            ("https://www.lemonde.fr.", "lemonde.fr"),
        ],
    )
    def test_registrable(self, value, expected):
        assert domains.registrable(value) == expected

    def test_lookalike_domain_is_not_the_same_outlet(self):
        # A substring match would accept this; registrable-domain equality must not.
        assert not domains.same_outlet("https://lemonde.fr.evil.com/", "lemonde.fr")

    def test_www_and_path_do_not_matter(self):
        assert domains.same_outlet("https://www.lemonde.fr/a/b", "lemonde.fr")

    @pytest.mark.parametrize(
        "domain",
        ["webcache.googleusercontent.com", "archive.wikiwix.com", "web.archive.org", "youtube.com"],
    )
    def test_infrastructure_is_excluded(self, domain):
        assert domains.is_infrastructure(domain)

    def test_publisher_is_not_infrastructure(self):
        assert not domains.is_infrastructure("lemonde.fr")


class TestVerification:
    def test_accepts_a_profile_that_names_our_domain(self, monkeypatch):
        monkeypatch.setattr(
            mbfc,
            "_get",
            lambda url, **kw: FakeResponse(
                LE_MONDE_PAGE, "https://mediabiasfactcheck.com/le-monde-bias/"
            ),
        )
        result = mbfc.verify("https://mediabiasfactcheck.com/le-monde-bias/", "lemonde.fr")
        assert result["slug"] == "le-monde-bias"
        assert result["stated_source"] == "https://www.lemonde.fr/"

    def test_rejects_the_cairn_fuzzy_redirect(self, monkeypatch):
        """The regression this tool exists for.

        Requesting /cairn/ for cairn.info 301s to the Cairns News profile and
        returns HTTP 200. A status-code check passes; the Source: check must
        not -- cairnsnews.org is not cairn.info.
        """
        monkeypatch.setattr(
            mbfc,
            "_get",
            lambda url, **kw: FakeResponse(
                CAIRNS_NEWS_PAGE,
                "https://mediabiasfactcheck.com/cairns-news-bias-and-credibility/",
            ),
        )
        with pytest.raises(mbfc.Rejected) as excinfo:
            mbfc.verify("https://mediabiasfactcheck.com/cairn/", "cairn.info")
        assert "cairnsnews.org" in str(excinfo.value)
        assert "cairn.info" in str(excinfo.value)

    def test_rejects_a_page_with_no_source_line(self, monkeypatch):
        monkeypatch.setattr(
            mbfc,
            "_get",
            lambda url, **kw: FakeResponse(NO_SOURCE_PAGE, "https://mediabiasfactcheck.com/x/"),
        )
        with pytest.raises(mbfc.Rejected, match="no 'Source:' line"):
            mbfc.verify("https://mediabiasfactcheck.com/x/", "lemonde.fr")

    def test_rejects_non_200(self, monkeypatch):
        monkeypatch.setattr(
            mbfc,
            "_get",
            lambda url, **kw: FakeResponse("", "https://mediabiasfactcheck.com/x/", 404),
        )
        with pytest.raises(mbfc.Rejected, match="HTTP 404"):
            mbfc.verify("https://mediabiasfactcheck.com/x/", "lemonde.fr")

    def test_rejects_a_slug_that_breaks_the_format_constraint(self, monkeypatch):
        monkeypatch.setattr(
            mbfc,
            "_get",
            lambda url, **kw: FakeResponse(
                LE_MONDE_PAGE, "https://mediabiasfactcheck.com/Le_Monde_Bias/"
            ),
        )
        with pytest.raises(mbfc.Rejected, match="format constraint"):
            mbfc.verify("https://mediabiasfactcheck.com/Le_Monde_Bias/", "lemonde.fr")


def _summary(qid, label, types, websites, p9852=()):
    return {
        "qid": qid,
        "label": label,
        "types": list(types),
        "type_names": list(types),
        "websites": list(websites),
        "existing_p9852": list(p9852),
        "type_ok": any(t in wikidata.ALLOWED_TYPES for t in types),
    }


class TestItemDisambiguation:
    def _pick(self, summaries, domain):
        candidates = [{"qid": s["qid"]} for s in summaries]
        entities = {s["qid"]: s for s in summaries}
        return cli._pick_item(candidates, domain, entities)

    def test_journalists_never_win_over_the_outlet(self):
        """Laura Motet's staff page is on lemonde.fr; she is not Le Monde."""
        item, why = self._pick(
            [
                _summary("Q56651625", "Laura Motet", ["Q5"], ["https://www.lemonde.fr/journaliste/x"]),
                _summary("Q12461", "Le Monde", ["Q1110794"], ["https://www.lemonde.fr"]),
            ],
            "lemonde.fr",
        )
        assert why is None
        assert item["qid"] == "Q12461"

    def test_programmes_lose_to_the_broadcaster(self):
        item, why = self._pick(
            [
                _summary("Q105605556", "Vrai ou fake", ["Q15416"], ["https://www.francetvinfo.fr/vrai-ou-fake"]),
                _summary("Q25395519", "franceinfo", ["Q1153191"], ["https://www.francetvinfo.fr/"]),
            ],
            "francetvinfo.fr",
        )
        assert why is None
        assert item["qid"] == "Q25395519"

    def test_genuine_ambiguity_is_refused_not_guessed(self):
        item, why = self._pick(
            [
                _summary("Q12461", "Le Monde", ["Q1110794"], ["https://www.lemonde.fr"]),
                _summary("Q69565062", "lemonde.fr", ["Q1153191"], ["https://www.lemonde.fr"]),
            ],
            "lemonde.fr",
        )
        assert item is None
        assert "ambiguous" in why
        assert "Q12461" in why and "Q69565062" in why

    def test_all_person_items_is_refused(self):
        item, why = self._pick(
            [_summary("Q1", "Someone", ["Q5"], ["https://example.org/"])],
            "example.org",
        )
        assert item is None
        assert "only person items" in why


class TestQuickStatements:
    def test_line_shape_and_reference(self):
        line = emit.quickstatements(
            [
                {
                    "qid": "Q770596",
                    "slug": "lexpress-bias",
                    "profile_url": "https://mediabiasfactcheck.com/lexpress-bias/",
                }
            ],
            "2026-07-22",
        ).strip()
        fields = line.split("\t")
        assert fields[:3] == ["Q770596", "P9852", '"lexpress-bias"']
        # Every statement must carry stated in / reference URL / retrieved.
        assert fields[3:5] == ["S248", "Q60741379"]
        assert fields[5] == "S854"
        assert fields[7] == "S813"
        assert fields[8] == "+2026-07-22T00:00:00Z/11"

    def test_empty_batch_is_empty_not_a_blank_line(self):
        assert emit.quickstatements([], "2026-07-22") == ""

    def test_batch_never_contains_a_rating_property(self):
        """This tool proposes identifiers only. Ratings have no property and
        an incompatible licence -- see the module README."""
        batch = emit.quickstatements(
            [
                {
                    "qid": "Q1",
                    "slug": "x",
                    "profile_url": "https://mediabiasfactcheck.com/x/",
                }
            ],
            "2026-07-22",
        )
        for forbidden in ("P1387", "P1552", "P2308"):
            assert forbidden not in batch
