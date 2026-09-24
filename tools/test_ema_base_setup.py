"""Tests for the 20 EMA Base Setup composite scanner."""
import numpy as np
import pandas as pd
import pytest

import scanner_templates as sc

NAME = "20 EMA Base Setup"


def _bars(n: int = 200, base_price: float = 100.0, trend: float = 0.05,
          body_noise: float = 0.3, vol_base: float = 1e6) -> pd.DataFrame:
    """Gentle uptrend with small candles — the ideal base shape."""
    rng = np.random.RandomState(42)
    closes = base_price * np.cumprod(1 + trend / n + rng.randn(n) * 0.003)
    opens = closes * (1 - rng.uniform(-0.002, 0.002, n))
    highs = np.maximum(opens, closes) * (1 + rng.uniform(0, 0.003, n))
    lows = np.minimum(opens, closes) * (1 - rng.uniform(0, 0.003, n))
    vol = np.full(n, vol_base)
    # Make red-candle volume low in the last 20 bars
    for i in range(n - 20, n):
        if closes[i] < opens[i]:
            vol[i] = vol_base * 0.4
    return pd.DataFrame({
        "open": opens, "high": highs, "low": lows, "close": closes,
        "volume": vol,
    })


def test_registered():
    assert NAME in sc.SCANNERS
    assert sc.SCANNERS[NAME]["category"] == "Entry"


def test_fires_on_ideal_base():
    df = _bars()
    hit = sc.scan_ema_base_setup(df)
    assert hit is not None
    assert hit["score"] >= 40
    assert "stop" in hit
    assert "ema20" in hit
    assert "scores_detail" in hit
    detail = hit["scores_detail"]
    assert set(detail.keys()) == {
        "candle_quality", "volume_dryup", "range_compression",
        "higher_lows", "breakout_volume",
    }


def test_rejects_below_ema():
    """Price well below EMA20 should not fire."""
    df = _bars(base_price=100, trend=-0.3)
    hit = sc.scan_ema_base_setup(df)
    assert hit is None


def test_rejects_short_history():
    df = _bars(n=30)
    hit = sc.scan_ema_base_setup(df)
    assert hit is None


def test_wide_red_bars_penalise():
    """A base with big red candles should score lower on candle quality."""
    df = _bars()
    # Inject wide red bars
    for i in range(len(df) - 15, len(df) - 5):
        df.iloc[i, df.columns.get_loc("close")] = df.iloc[i]["open"] * 0.95
        df.iloc[i, df.columns.get_loc("low")] = df.iloc[i]["close"] * 0.99
    hit_clean = sc.scan_ema_base_setup(_bars())
    hit_dirty = sc.scan_ema_base_setup(df)
    if hit_clean and hit_dirty:
        assert hit_dirty["scores_detail"]["candle_quality"] <= hit_clean["scores_detail"]["candle_quality"]


def test_high_red_volume_penalises():
    """Heavy volume on red candles should score low on dryup."""
    df = _bars()
    for i in range(len(df) - 20, len(df)):
        if df.iloc[i]["close"] < df.iloc[i]["open"]:
            df.iloc[i, df.columns.get_loc("volume")] = 3e6
    hit = sc.scan_ema_base_setup(df)
    if hit:
        assert hit["scores_detail"]["volume_dryup"] <= 8


def test_description_says_unmeasured():
    assert "UNMEASURED" in sc.SCANNERS[NAME]["description"]
