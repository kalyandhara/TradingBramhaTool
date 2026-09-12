"""Tests for the shareholding XBRL parser -- B-10's namespace bug above all.

    py -3 -m pytest tools/test_shareholding_parse.py -q

B-10 sat on the backlog for five weeks as "four Nifty-500 symbols uncached", shrank
to one (`BSE`), and carried the diagnosis *"probably our bug in the symbol filter"*
the whole time. Both halves were wrong. NSE serves BSE's 22 filings normally and the
filter is fine; the parser bound its fact regexes to the namespace PREFIX
`in-bse-shp:`, and BSE's own filings use `in-capmkt:` for the identical element
names.

It failed in the quietest way available: no facts matched, `raw` came back empty,
`parse_shareholding` returned None, and the symbol simply had no cache file. One
missing file out of ~1,500 looks like a data gap, not a bug -- which is why it
survived three re-verification passes.
"""

from __future__ import annotations

import pytest

import nse_shareholding_fetch as ns


def _doc(prefix: str, *, promoter: str | None = "0.4521", public: str = "0.5479",
         total: str = "1.0") -> str:
    """A minimal but structurally real SHP filing under one namespace prefix."""
    rows = [("Promoter", promoter, "ShareholdingOfPromoterAndPromoterGroupMember"),
            ("Public", public, "PublicShareholdingMember"),
            ("Total", total, "ShareholdingPatternMember")]
    ctx, facts = [], []
    for cid, val, member in rows:
        if val is None:
            continue
        ctx.append(
            f'<xbrli:context id="{cid}"><xbrli:scenario>'
            f'<xbrldi:explicitMember dimension="in-capmkt:CategoryOfShareholdersAxis">'
            f'in-capmkt:{member}</xbrldi:explicitMember>'
            f'</xbrli:scenario></xbrli:context>')
        facts.append(
            f'<{prefix}:ShareholdingAsAPercentageOfTotalNumberOfShares '
            f'contextRef="{cid}" unitRef="u">{val}'
            f'</{prefix}:ShareholdingAsAPercentageOfTotalNumberOfShares>')
        facts.append(
            f'<{prefix}:NumberOfFullyPaidUpEquityShares contextRef="{cid}" '
            f'unitRef="u">1000000</{prefix}:NumberOfFullyPaidUpEquityShares>')
    return "<xbrli:xbrl>" + "".join(ctx) + "".join(facts) + "</xbrli:xbrl>"


# ── B-10: the prefix must not decide whether a filing parses ────────────────────

@pytest.mark.parametrize("prefix", ["in-bse-shp", "in-capmkt"])
def test_both_namespace_prefixes_parse(prefix):
    out = ns.parse_shareholding(_doc(prefix))
    assert out is not None, f"{prefix}: returned None -- the B-10 failure mode"
    assert out["promoter"] == pytest.approx(45.21, abs=0.01)
    assert out["public"] == pytest.approx(54.79, abs=0.01)


def test_the_two_prefixes_agree_field_for_field():
    """Same document, different alias: the numbers must be identical."""
    a = ns.parse_shareholding(_doc("in-bse-shp"))
    b = ns.parse_shareholding(_doc("in-capmkt"))
    for k in ("promoter", "public", "total", "shares_total"):
        assert a[k] == b[k], f"{k} differs by namespace prefix: {a[k]} vs {b[k]}"


def test_an_unknown_future_prefix_also_parses():
    """The fix is a wildcard, not a second hardcoded alias. SEBI has changed this
    spelling once already (see the 'Catergory' typo note in CATEGORY_MEMBERS), so
    the next vintage must not need a code change."""
    assert ns.parse_shareholding(_doc("in-shp-2027")) is not None


# ── the promoter-less company, which is what BSE actually is ───────────────────

def test_a_company_with_no_promoter_parses_with_promoter_none():
    """BSE Ltd is a professionally managed exchange: 100% public, no promoter
    member in the filing at all. `promoter` must come back None -- NOT 0.0, which
    would read downstream as 'the promoters sold everything'."""
    out = ns.parse_shareholding(_doc("in-capmkt", promoter=None, public="1.0"))
    assert out is not None
    assert out["promoter"] is None
    assert out["public"] == pytest.approx(100.0, abs=0.01)


def test_promoter_none_survives_the_consumers_isinstance_guard():
    """Pins the contract the dashboard and hidden_treasures rely on: they filter
    with isinstance(v, (int, float)), so None must stay None and never become a
    number that looks like a real reading."""
    out = ns.parse_shareholding(_doc("in-capmkt", promoter=None, public="1.0"))
    assert not isinstance(out["promoter"], (int, float))


# ── guards that keep the above from passing vacuously ──────────────────────────

def test_empty_and_junk_input_return_none():
    assert ns.parse_shareholding("") is None
    assert ns.parse_shareholding("<xbrli:xbrl></xbrli:xbrl>") is None


def test_percent_scale_filings_are_not_rescaled():
    """Older filings state percentages (total=100) and newer ones fractions
    (total=1.0). The scale is read per filing; a 45.21 must not become 4521."""
    out = ns.parse_shareholding(
        _doc("in-bse-shp", promoter="45.21", public="54.79", total="100.0"))
    assert out["promoter"] == pytest.approx(45.21, abs=0.01)
    assert out["total"] == pytest.approx(100.0, abs=0.01)
