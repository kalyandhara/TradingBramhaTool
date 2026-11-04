"""B-192 — cash and accrual forensic checks (red_flags.py + fundamentals_deep.py)."""
import pandas as pd
import pytest

import fundamentals_deep as fd
import red_flags as rf

YEARS = pd.to_datetime(["2026-03-31", "2025-03-31", "2024-03-31", "2023-03-31"])


def _frame(rows: dict) -> pd.DataFrame:
    return pd.DataFrame(rows, index=YEARS).T


def _stmts(ni, ocf, assets, inventory, revenue):
    return {
        "income": _frame({"Total Revenue": revenue, "Net Income": ni}),
        "balance": _frame({"Total Assets": assets, "Inventory": inventory}),
        "cashflow": _frame({"Operating Cash Flow": ocf}),
    }


def _by_key(res, key):
    return next(f for f in res["flags"] if f["key"] == key)


# ── derived fields ────────────────────────────────────────────────────────────
def test_accrual_ratio_is_profit_minus_cash_over_average_assets():
    s = _stmts(ni=[200, 150, 120, 100], ocf=[50, 140, 110, 90],
               assets=[1100, 900, 800, 700], inventory=[1, 1, 1, 1],
               revenue=[1000, 900, 800, 700])
    d = fd.derive_fundamentals("X", s)
    # (200 - 50) / ((1100 + 900) / 2) = 15 %
    assert d["accrual_ratio"] == pytest.approx(15.0)


def test_inventory_days_history_is_newest_first_and_date_matched():
    s = _stmts(ni=[1, 1, 1, 1], ocf=[1, 1, 1, 1], assets=[1, 1, 1, 1],
               inventory=[200, 150, 100, 50], revenue=[1000, 1000, 1000, 1000])
    d = fd.derive_fundamentals("X", s)
    assert d["inventory_days_history"] == pytest.approx([73.0, 54.8, 36.5, 18.2], abs=0.1)


def test_missing_rows_leave_fields_unknown_not_zero():
    s = _stmts(ni=[1, 1, 1, 1], ocf=[1, 1, 1, 1], assets=[1, 1, 1, 1],
               inventory=[1, 1, 1, 1], revenue=[1, 1, 1, 1])
    s["balance"] = s["balance"].drop(index=["Total Assets", "Inventory"])
    d = fd.derive_fundamentals("X", s)
    assert d["accrual_ratio"] is None
    assert all(v is None for v in d["inventory_days_history"])


# ── checks ────────────────────────────────────────────────────────────────────
def test_cash_conversion_three_states():
    assert rf._check_cash_conversion({"cfo_pat_ratio": 0.3, "cfo_pat_years": 5})["state"] == rf.FLAG
    assert rf._check_cash_conversion({"cfo_pat_ratio": 1.1, "cfo_pat_years": 5})["state"] == rf.CLEAN
    assert rf._check_cash_conversion({"cfo_pat_ratio": None, "cfo_pat_years": 0})["state"] == rf.NOT_CHECKED
    assert rf._check_cash_conversion({"cfo_pat_ratio": 0.3, "cfo_pat_years": 2})["state"] == rf.NOT_CHECKED


def test_accruals_sign_profit_ahead_of_cash_is_the_bad_side():
    assert rf._check_accruals({"accrual_ratio": 15.0})["state"] == rf.FLAG
    assert rf._check_accruals({"accrual_ratio": 3.0})["state"] == rf.CLEAN
    # cash ahead of profit is the GOOD side, however large
    assert rf._check_accruals({"accrual_ratio": -20.0})["state"] == rf.CLEAN
    assert rf._check_accruals({})["state"] == rf.NOT_CHECKED


def test_inventory_days_rising_flags_and_falling_is_clean():
    rising = rf.evaluate("X", None, {"inventory_days_history": [150.0, 120.0, 90.0, 60.0]})
    assert _by_key(rising, "inventory_days_trend")["state"] == rf.FLAG
    # MAZDOCK-shaped: inventory days 315 -> 68. Flagium's F15 fired on this; it must not.
    falling = rf.evaluate("X", None, {"inventory_days_history": [68.0, 132.0, 197.0, 315.0]})
    assert _by_key(falling, "inventory_days_trend")["state"] == rf.CLEAN


def test_evaluate_runs_the_three_new_checks():
    keys = {f["key"] for f in rf.evaluate("X", None, {})["flags"]}
    assert {"cash_conversion", "accrual_ratio", "inventory_days_trend"} <= keys


def test_cash_conversion_says_why_when_profits_were_losses():
    """Paytm: 4 matched years but losses in total, so CFO/PAT is undefined — the
    reason must say that, not 'have 4' beside a need for 3."""
    r = rf._check_cash_conversion({"cfo_pat_ratio": None, "cfo_pat_years": 4})
    assert r["state"] == rf.NOT_CHECKED and "loss" in r["detail"].lower()
