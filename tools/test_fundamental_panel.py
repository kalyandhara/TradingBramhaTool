"""Tests for the Strategy Hub fundamentals panel (PR-1c), offline.

The block this replaces held six hardcoded rows under a caption claiming the
scores were "computed from the last fundamental data pull". What these pin is
that the replacement cannot drift back into asserting things it has not computed:

  * **No overall /100 is invented.** `fundamental_score` deliberately emits none,
    and the frozen block's shield was exactly the number that decision forbids.
  * **A loss-making company has no PE**, and no PE band point. The frozen row
    printed 62x for a name whose TTM EPS is -2.4 -- not stale, meaningless.
  * **Every field is independently optional**, so a partial fetch blanks one cell
    rather than dropping the row or carrying a stale value forward.
"""
import pandas as pd
import pytest

import fundamental_panel as fpan


def _closes(prices, start="2022-01-03"):
    idx = pd.bdate_range(start=start, periods=len(prices))
    return pd.Series(prices, index=idx, dtype=float)


def _deep(**over):
    d = {"sector": "Chemicals", "market_cap": 9.8e10, "profit_cagr_3y": -2.15,
         "pe": 14.2, "price": 1143.5,
         "annual": [{"period": "2025-12-31", "eps": 100.0},
                    {"period": "2024-12-31", "eps": 80.0}]}
    d.update(over)
    return d


# ── the decision not to invent a score ────────────────────────────────────────

def test_no_overall_score_field_exists():
    """The shield's /100 must not come back under another name.

    `fundamental_score` refuses to emit an overall precisely so a fourth number
    cannot compete with the technical rating and the council verdict.
    """
    row = fpan.build_row("X", "X Ltd", _deep(), {})
    assert not any("overall" in k.lower() for k in row)
    assert "Business" in row and "Entry" in row


def test_business_and_entry_are_carried_separately():
    row = fpan.build_row("X", "X Ltd", _deep(), {})
    # Both keys exist even when the scorer could not run; they are never merged.
    assert "Business score" in row and "Entry score" in row


# ── the PE band ───────────────────────────────────────────────────────────────

def test_pe_points_are_price_over_that_years_eps():
    closes = _closes([100.0] * 400, start="2024-06-03")
    band = fpan.pe_at_year_ends(
        [{"period": "2024-12-31", "eps": 10.0}], closes)
    assert len(band) == 1
    assert band[0]["pe"] == 10.0          # 100 / 10


def test_a_negative_eps_year_contributes_no_pe_point():
    """The finding that motivated PR-1c, in miniature.

    The frozen table printed a 62x PE and a 40-95x band for Piramal Pharma, whose
    TTM EPS is -2.4. A PE off negative earnings is not stale, it is meaningless.
    """
    closes = _closes([100.0] * 400, start="2024-06-03")
    band = fpan.pe_at_year_ends(
        [{"period": "2024-12-31", "eps": -2.46},
         {"period": "2025-12-31", "eps": 0.0}], closes)
    assert band == []


def test_a_row_with_no_priceable_years_reports_no_band():
    row = fpan.build_row("X", "X Ltd", _deep(annual=[]), {}, _closes([10.0, 11.0]))
    assert row["PE low"] is None and row["PE high"] is None
    assert row["PE points"] == 0


def test_the_band_reports_how_many_years_it_used():
    closes = _closes([100.0] * 900, start="2022-06-01")
    row = fpan.build_row("X", "X Ltd", _deep(), {}, closes)
    assert row["PE points"] == 2          # two annual rows, both positive EPS
    assert row["PE low"] is not None and row["PE high"] >= row["PE low"]


# ── absent renders absent ─────────────────────────────────────────────────────

def test_statements_that_do_not_resolve_blank_the_row_and_say_so():
    row = fpan.build_row("X", "X Ltd", None, None)
    assert row["note"] == "statements did not resolve"
    for k in ("MCap Cr", "Profit CAGR 3Y %", "PE now", "LTP", "Business"):
        assert row[k] is None
    # The row still exists -- the name is a record, the numbers are not.
    assert row["Stock"] == "X Ltd" and row["Symbol"] == "X"


def test_a_missing_field_blanks_only_itself():
    row = fpan.build_row("X", "X Ltd", _deep(pe=None, profit_cagr_3y=None), {},
                         _closes([100.0] * 900, start="2022-06-01"))
    assert row["PE now"] is None
    assert row["Profit CAGR 3Y %"] is None
    assert row["MCap Cr"] is not None          # unaffected


def test_a_nan_is_treated_as_missing_not_as_a_value():
    row = fpan.build_row("X", "X Ltd", _deep(pe=float("nan")), {})
    assert row["PE now"] is None


# ── prices ────────────────────────────────────────────────────────────────────

def test_day_change_comes_from_the_last_two_closes():
    row = fpan.build_row("X", "X Ltd", _deep(), {}, _closes([100.0, 110.0]))
    assert row["LTP"] == 110.0
    assert row["Day %"] == 10.0


def test_a_single_close_gives_a_price_but_no_day_change():
    row = fpan.build_row("X", "X Ltd", _deep(), {}, _closes([110.0]))
    assert row["Day %"] is None


def test_market_cap_is_converted_to_crore():
    row = fpan.build_row("X", "X Ltd", _deep(market_cap=1e9), {})
    assert row["MCap Cr"] == 100.0          # 1e9 rupees = 100 crore


# ── the roster ────────────────────────────────────────────────────────────────

def test_every_roster_entry_is_a_symbol_and_a_display_name():
    assert fpan.ROSTER
    for sym, disp in fpan.ROSTER:
        assert sym and sym == sym.strip().upper()
        # A display name MAY equal its symbol -- CRISIL trades under its own
        # name -- so this only requires both to be present and tidy.
        assert disp and disp == disp.strip()


def test_symbols_are_unique():
    syms = fpan.symbols()
    assert len(syms) == len(set(syms))


def test_build_survives_a_fetch_that_raises(monkeypatch):
    import stock_council as council
    monkeypatch.setattr(council, "fetch_fundamentals",
                        lambda s: (_ for _ in ()).throw(RuntimeError("down")))

    def boom(sym):
        raise RuntimeError("no statements")

    rows = fpan.build(fetch_deep=boom)
    assert len(rows) == len(fpan.ROSTER)
    assert all(r["note"] == "statements did not resolve" for r in rows)
