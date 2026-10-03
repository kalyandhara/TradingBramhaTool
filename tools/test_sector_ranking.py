"""Tests for sector_ranking — no network; synthetic members."""
from __future__ import annotations

import numpy as np
import pandas as pd

import sector_ranking as srk


def _bars(n: int, drift: float, seed: int, last_jump: float = 0.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    c = 100 * np.cumprod(1 + drift + rng.normal(0, 0.004, n))
    c[-1] = c[-2] * (1 + last_jump)
    idx = pd.bdate_range("2026-03-02", periods=n)
    return pd.DataFrame({"open": c, "high": c * 1.005, "low": c * 0.995,
                         "close": c, "volume": 1e5}, index=idx)


def test_sector_row_counts_advancers_and_leaders():
    members = {"UP1": _bars(80, 0.002, 1, 0.03), "UP2": _bars(80, 0.002, 2, 0.01),
               "DN1": _bars(80, -0.002, 3, -0.02)}
    r = srk.sector_row("Test", members)
    assert r["stocks"] == 3
    assert r["ad_net"] == 1
    assert r["leaders"].split(", ")[0] == "UP1"
    assert r["chg_d"] == round(np.mean([3.0, 1.0, -2.0]), 2)


def test_health_columns_are_bounded_percentages():
    members = {f"S{i}": _bars(80, 0.003, i) for i in range(4)}
    r = srk.sector_row("Up", members)
    assert 0 <= r["pct_above_20ema"] <= 100
    assert 0 <= r["pct_bo_10d"] <= 100
    assert r["pct_above_20ema"] == 100


def test_ranking_grid_sorted_by_delta_share_and_shares_sum_to_100(monkeypatch):
    import sectors
    smap = {f"A{i}": "Alpha" for i in range(3)} | {f"B{i}": "Beta" for i in range(3)}
    monkeypatch.setattr(sectors, "symbol_map", lambda u: smap)
    hist = {s: _bars(80, 0.001, i) for i, s in enumerate(smap)}
    for s in ("A0", "A1", "A2"):
        hist[s].loc[hist[s].index[-1], "volume"] = 5e5
    g = srk.ranking_grid("x", hist=hist)
    df = g["rows"]
    assert df["sector"].tolist() == ["Alpha", "Beta"]
    assert abs(df["share_pct"].sum() - 100) < 0.02
    assert list(df[srk.COLUMNS].columns) == srk.COLUMNS
