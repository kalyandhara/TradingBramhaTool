"""Tests for projection.target_atr_distance (B-117)."""
from __future__ import annotations

import pandas as pd
import numpy as np
import pytest

import projection as proj


def _ohlcv(n: int = 100, base: float = 100.0, trend: float = 0.5) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    closes = base + np.cumsum(rng.normal(trend, 1.5, n))
    highs = closes + rng.uniform(0.5, 2.0, n)
    lows = closes - rng.uniform(0.5, 2.0, n)
    opens = closes + rng.normal(0, 0.5, n)
    volume = rng.integers(100_000, 1_000_000, n)
    return pd.DataFrame({
        "open": opens, "high": highs, "low": lows,
        "close": closes, "volume": volume,
    })


def test_returns_float():
    df = _ohlcv(100)
    current = float(df["close"].iloc[-1])
    result = proj.target_atr_distance(current + 10, current, df)
    assert isinstance(result, float)
    assert result > 0


def test_none_on_bad_inputs():
    assert proj.target_atr_distance(None, 100, _ohlcv()) is None
    assert proj.target_atr_distance(120, None, _ohlcv()) is None
    assert proj.target_atr_distance(120, 100, None) is None


def test_none_on_short_df():
    df = _ohlcv(10)
    assert proj.target_atr_distance(120, 100, df) is None


def test_symmetry():
    df = _ohlcv(100)
    current = float(df["close"].iloc[-1])
    up = proj.target_atr_distance(current + 10, current, df)
    down = proj.target_atr_distance(current - 10, current, df)
    assert up == down


def test_larger_distance_gives_larger_multiple():
    df = _ohlcv(100)
    current = float(df["close"].iloc[-1])
    small = proj.target_atr_distance(current + 5, current, df)
    large = proj.target_atr_distance(current + 20, current, df)
    assert large > small
