"""pattern_metrics — each block on hand-built frames."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pattern_metrics as pm  # noqa: E402


def _frame(n=520, start=100.0, drift=0.0, seed=3, vol=1_000_000):
    rs = np.random.default_rng(seed)
    idx = pd.date_range("2024-09-25", periods=n, freq="B")
    close = start * np.cumprod(1 + drift + rs.normal(0, 0.004, n))
    df = pd.DataFrame({"open": close, "high": close * 1.004, "low": close * 0.996,
                       "close": close, "volume": float(vol)}, index=idx)
    return df


def test_overhead_supply_clear_at_new_high_and_heavy_after_drawdown():
    up = _frame(drift=0.002)                              # steady uptrend → close near the top
    o = pm.overhead_supply(up)
    assert o["pct"] < pm.OVERHEAD_CLEAR and o["label"] == "Clear path"
    down = _frame(drift=-0.002)                           # steady downtrend → everything overhead
    o2 = pm.overhead_supply(down)
    assert o2["pct"] > pm.OVERHEAD_HEAVY and o2["label"] == "Heavy ceiling"


def test_extension_bands_and_rsi_flag():
    calm = _frame(drift=0.0)
    e = pm.extension(calm)
    assert e["score"] is not None and 0 <= e["score"] <= 100 and e["band"] in ("Lower band", "Middle band", "Upper band")
    hot = _frame(drift=0.0)
    hot.iloc[-8:, :] = hot.iloc[-8:, :].values * np.array([1.0, 1.0, 1.0, 1.0, 1.0]) \
        * np.linspace(1.0, 1.3, 8)[:, None] ** np.array([1, 1, 1, 1, 0])
    e2 = pm.extension(hot)
    assert e2["score"] > e["score"] and e2["band"] == "Upper band"
    assert e2["rsi_pct"] >= pm.RSI_EXHAUST_PCT and e2["rsi_exhaustion"] is True


def test_exceptional_volume_finds_the_spikes():
    df = _frame()
    df.iloc[-40, df.columns.get_loc("volume")] = 6_900_000
    df.iloc[-5, df.columns.get_loc("volume")] = 5_100_000
    x = pm.exceptional_volume(df)
    assert x["count"] == 2 and x["sessions"][0]["ratio"] > x["sessions"][1]["ratio"] > 4.0
    assert x["n_sessions"] == 500 and x["threshold"] == pytest.approx(x["avg_volume"] * 4)


def test_radar_axes_and_score_without_benchmark():
    df = _frame(drift=0.0015)
    r = pm.radar(df)
    assert set(r["axes"]) == {"VCP", "RS", "Stage", "Volume", "Low risk", "Clear path"}
    assert r["axes"]["RS"] is None and r["axes"]["Stage"] == 100.0
    assert 0 <= r["score"] <= 100


def test_radar_rs_uses_benchmark():
    stock = _frame(drift=0.002)
    bench = _frame(drift=0.0, seed=9)
    r = pm.radar(stock, bench)
    assert r["axes"]["RS"] == 100.0                        # far outperformed → capped


def test_vcp_coil_abstains_or_reports_ladder():
    v = pm.vcp_coil(_frame())
    if v is not None:
        assert v["contractions"] == len(v["ladder"]) >= 1 and v["base_weeks"] > 0


def test_compute_all_and_short_frames():
    out = pm.compute_all(_frame(), _frame(seed=5))
    assert set(out) == {"overhead", "extension", "vcp", "radar", "exceptional_volume"}
    assert out["overhead"] and out["extension"] and out["radar"] and out["exceptional_volume"]
    assert pm.overhead_supply(_frame(n=10)) is None and pm.extension(_frame(n=30)) is None
