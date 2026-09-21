"""Tests for the market-wide filings feed — B-111.

Every fixture string below is a REAL one from the 2026-09-21 NSE feed, because
the whole difficulty of this module is that the real rows are messier than any
invented one: the category is often "General Updates", the text repeats the
category, and the amount that makes the filing interesting is usually not in the
payload at all.

What is pinned:
  * exchange noise is dropped BEFORE bucketing (it is ~40% of the raw feed);
  * a missing amount stays None and never becomes a zero;
  * the date range is what makes the endpoint a feed rather than a 20-row sample.
"""
import datetime as dt

import pytest

import nse_filings_feed as ff


# ── bucketing ─────────────────────────────────────────────────────────────────
def test_an_order_win_is_bucketed():
    assert ff.bucket_of(
        "Bagging/Receiving of orders/contracts",
        "Welspun Corp Limited has informed the Exchange about Bagging/Receiving "
        "of orders/contracts: Large order win announced by the Company s "
        "associate Company viz. East Pipes Integrated Company for Industry, KSA"
    ) == "ORDER_WIN"


def test_an_acquisition_is_bucketed_even_under_a_generic_category():
    """GUJTHEM's ₹1,220 Cr acquisition was filed as "General Updates" — the
    category says nothing and the TEXT says "Acquisition"."""
    assert ff.bucket_of(
        "General Updates",
        "Gujarat Themis Biosyn Limited has informed the Exchange about Acquisition"
    ) == "M&A"


def test_a_preferential_issue_is_a_fund_raise():
    assert ff.bucket_of(
        "General Updates",
        "The Company has informed about the general updates relating to the "
        "proposed preferential issue of 8,695,400 fully convertible warrants"
    ) == "FUND_RAISE"


def test_exchange_noise_is_dropped_before_bucketing():
    """A "Spurt in Volume" notice quotes the company's reply, which routinely
    contains material keywords. Testing materiality first would bucket the
    exchange's own reaction as news."""
    assert ff.bucket_of(
        "Spurt in Volume",
        "Significant increase in volume has been observed in Tega Industries "
        "Limited. The Exchange, in order to ensure that investors have latest "
        "relevant information about the company, including any order or contract"
    ) is None


def test_routine_compliance_is_dropped():
    for cat in ("Copy of Newspaper Publication", "Trading Window",
                "Record Date", "Analysts/Institutional Investor Meet",
                "Corrigendum to the Notice"):
        assert ff.bucket_of(cat, f"X Limited has informed the Exchange about {cat}") is None


def test_an_unclassifiable_filing_is_dropped_rather_than_guessed():
    """TEGA's ₹126 Cr contract was filed as "General Updates" with the text
    "intimation pursuant to Reg. 30" — material by definition, and unreadable
    without the PDF. Inventing a bucket for it would be worse than missing it."""
    assert ff.bucket_of(
        "General Updates",
        "Tega Industries Limited has informed the Exchange about intimation "
        "pursuant to Reg. 30 of the SEBI LODR Regulations, 2015.") is None


def test_the_first_matching_bucket_wins_in_priority_order():
    """A filing that mentions both a raise and a contract is filed under the
    money. The ORDER of BUCKETS is the decision, so it is tested."""
    b = ff.bucket_of("General Updates",
                     "preferential issue to fund the new work order")
    assert b == "ORDER_WIN"          # ORDER_WIN precedes FUND_RAISE in BUCKETS


# ── amounts ───────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("text,expected", [
    ("contract worth Rs. 126 crore from Kalpataru", "₹126 crore"),
    ("order value of ₹1,220 Cr", "₹1,220 crore"),
    ("over 771 million SAR", None),          # unit BEFORE currency — not matched
    ("valued at SAR 771 million", "SAR 771 million"),
    ("warrants at Rs.115 each", "₹115"),
])
def test_amounts_are_read_only_when_the_text_states_them(text, expected):
    assert ff.amount_from(text) == expected


def test_a_filing_with_no_amount_returns_none_not_zero():
    """The number is usually in the PDF. None means "not in the text" — a zero
    would read as "a small deal", which is a different and false claim."""
    assert ff.amount_from(
        "Welspun Corp Limited has informed the Exchange about Bagging/Receiving "
        "of orders/contracts") is None
    assert ff.amount_from("") is None


# ── the feed ──────────────────────────────────────────────────────────────────
class _Resp:
    def __init__(self, payload): self._p = payload
    def raise_for_status(self): pass
    def json(self): return self._p


def _row(symbol, desc, text, when="21-Sep-2026 12:00:00"):
    return {"symbol": symbol, "sm_name": f"{symbol} Limited", "an_dt": when,
            "desc": desc, "attchmntText": text, "attchmntFile": "x.pdf",
            "smIndustry": "Test"}


def test_the_date_range_is_what_makes_it_a_feed():
    """Without from_date/to_date the endpoint returns the newest 20 rows, which
    is a sample, not a feed. Measured 2026-09-21: 20 rows vs 699 for three days."""
    seen = {}

    def _get(url, **kw):
        seen["url"] = url
        return _Resp([])

    ff.fetch(3, session=object(), today=dt.date(2026, 9, 21), get=_get)
    assert "from_date=19-09-2026" in seen["url"]
    assert "to_date=21-09-2026" in seen["url"]


def test_a_failed_read_returns_nothing_rather_than_raising():
    def _boom(url, **kw):
        raise RuntimeError("NSE said no")
    assert ff.fetch(1, session=object(), get=_boom) == []


def test_material_dedupes_a_repeated_filing():
    """A company files the intimation and then the signed copy. One event."""
    rows = [_row("ACME", "Acquisition", "ACME Limited has informed the Exchange about Acquisition"),
            _row("ACME", "Acquisition", "ACME Limited has informed the Exchange about Acquisition")]
    assert len(ff.material(rows)) == 1


def test_material_sorts_newest_first():
    rows = [_row("OLD", "Acquisition", "about Acquisition", when="19-Sep-2026 10:00:00"),
            _row("NEW", "Acquisition", "about Acquisition", when="21-Sep-2026 10:00:00")]
    assert [r["symbol"] for r in ff.material(rows)] == ["NEW", "OLD"]


def test_material_attaches_a_headline_and_an_amount():
    rows = [_row("ACME", "Bagging/Receiving of orders/contracts",
                 "ACME Limited has informed the Exchange about a work order "
                 "worth Rs. 126 crore")]
    out = ff.material(rows)[0]
    assert out["bucket"] == "ORDER_WIN"
    assert out["amount"] == "₹126 crore"
    assert "126" in out["headline"]


def test_summarise_counts_by_bucket():
    rows = ff.material([
        _row("A", "Acquisition", "about Acquisition"),
        _row("B", "Credit Rating", "about Credit Rating"),
        _row("C", "Acquisition", "about Acquisition")])
    assert ff.summarise(rows) == {"M&A": 2, "RATING": 1}
