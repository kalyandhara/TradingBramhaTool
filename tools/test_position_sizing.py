"""Tests for position_sizing.py — the one sizing rule the council, the sim and
the chart's risk box all read."""
from __future__ import annotations

import pytest

import position_sizing as ps


def test_council_formula_is_unchanged():
    # stock_council printed round(min(100, 2.0 / risk_pct * 100), 1) on a risk_pct
    # already rounded to 2dp. 100 -> 95 is a 5.00% stop -> 40.0% of capital.
    assert ps.size_pct_from_stop_pct(5.0) == 40.0
    assert ps.size_pct_of_capital(100, 95) == 40.0
    # a 1% stop at 2% risk wants 200% — capped, no leverage
    assert ps.size_pct_of_capital(100, 99) == 100.0


@pytest.mark.parametrize("entry,stop", [(100, 100), (None, 95), (100, None),
                                        (0, 95), (100, float("nan"))])
def test_undefined_risk_is_none_not_zero(entry, stop):
    assert ps.size_pct_of_capital(entry, stop) is None
    assert ps.shares_for_risk(100_000, entry, stop) is None


def test_notional_matches_the_sim_arithmetic():
    equity, entry, stop, risk = 1_000_000.0, 250.0, 240.0, 1.0
    risk_frac = abs(entry - stop) / entry
    assert ps.notional_for_risk(equity, entry, stop, risk) == equity * risk / 100.0 / risk_frac


def test_shares_floor_never_exceeds_budget():
    s = ps.shares_for_risk(100_000, 101.0, 97.7)       # R = 3.3, budget 2000
    assert s["qty"] == 606                              # 2000 / 3.3 = 606.06
    assert s["risk_amount"] <= s["risk_budget"]
    assert not s["capped"]


def test_tight_stop_is_capped_by_capital():
    s = ps.shares_for_risk(100_000, 100.0, 99.9)        # risk asks 20,000 shares
    assert s["capped"]
    assert s["qty"] == 1000 and s["notional"] == 100_000
    assert s["risk_amount"] < s["risk_budget"]


def test_r_multiple_long_and_short():
    assert ps.r_multiple(100, 95, 110) == pytest.approx(2.0)
    assert ps.r_multiple(100, 95, 95) == pytest.approx(-1.0)
    assert ps.r_multiple(100, 105, 90, side="short") == pytest.approx(2.0)


def test_r_multiple_needs_a_stop_on_the_risk_side():
    assert ps.r_multiple(100, None, 110) is None
    assert ps.r_multiple(100, 105, 110) is None         # long with stop above entry
