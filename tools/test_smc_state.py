"""smc_state.py — the Watchlist's SMC columns under the B-42r decision."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import scanner_templates as sc
import smc_state as sm


@pytest.mark.parametrize("st,sw,want", [
    ("UPTREND", "UPTREND", "agree"),
    ("DOWNTREND", "UPTREND", "opposite"),
    ("UPTREND", "RANGE", "split"),
    ("UNKNOWN", "UPTREND", "unknown"),
    (None, "UPTREND", "unknown"),
])
def test_agreement(st, sw, want):
    assert sm.agreement(st, sw) == want


def test_one_cell_names_both_definitions():
    assert sm.structure_cell("DOWNTREND", "UPTREND") == "ST ▼ · SW ▲ — opposite"


def test_pd_cell():
    assert sm.pd_cell({"zone": "DISCOUNT", "zone_pct": 22.4}) == "DISC 22%"
    assert sm.pd_cell({"zone": None, "zone_pct": None}) == ""
    assert sm.pd_cell(None) == ""
    assert sm.pd_cell({"zone": "PREMIUM", "zone_pct": 579.0}) == "ABOVE swing high"
    assert sm.pd_cell({"zone": "DISCOUNT", "zone_pct": -8.0}) == "BELOW swing low"


def _frame(lows, highs):
    n = len(lows)
    c = [(l + h) / 2 for l, h in zip(lows, highs)]
    return pd.DataFrame({"open": c, "high": highs, "low": lows, "close": c,
                         "volume": [1e6] * n})


def test_pierced_pool_is_spent_not_resting():
    df = _frame([100, 99, 98, 101, 102, 103], [110] * 6)       # close 106.5
    pools = [{"kind": "low", "level": 99.5, "last_bar": 0},     # pierced at bar 1-2
             {"kind": "low", "level": 97.0, "last_bar": 2},     # untouched since
             {"kind": "high", "level": 112.0, "last_bar": 3}]
    ssl, bsl = sm.nearest_untouched_pools(df, pools)
    assert ssl == 97.0 and bsl == 112.0


def test_columns_use_the_decided_pivot_lengths(monkeypatch):
    seen = {"ms": [], "pools": None, "sweep": None}
    real_ms = sc.read_market_structure

    def ms(d, pivot_len=15, **kw):
        seen["ms"].append(pivot_len)
        return real_ms(d, pivot_len=pivot_len, **kw)

    monkeypatch.setattr(sc, "read_market_structure", ms)
    monkeypatch.setattr(sc, "detect_liquidity_pools",
                        lambda d, pivot_len=5, **kw: seen.__setitem__("pools", pivot_len) or [])
    monkeypatch.setattr(sc, "detect_liquidity_sweep",
                        lambda d, pivot_len=5, **kw: seen.__setitem__("sweep", pivot_len))
    rng = np.random.default_rng(3)
    c = 100 + np.cumsum(rng.normal(0, 1.5, 300))
    df = pd.DataFrame({"open": c, "high": c + 1.5, "low": c - 1.5, "close": c,
                       "volume": np.full(300, 1e6)})
    out = sm.row(df)
    assert sorted(seen["ms"]) == [sm.SHORT_TERM, sm.SWING] == [5, 15]
    assert seen["pools"] == 5 and seen["sweep"] == 5          # liquidity uses short-term
    assert out["smc_structure"].startswith("ST ")


def test_short_history_is_blank_not_a_guess():
    df = _frame([100] * 20, [101] * 20)
    out = sm.row(df)
    assert out["smc_structure"] == "" and out["ssl_atr"] is None
