"""Tests for projection.nearby_levels (B-118)."""
from __future__ import annotations

import pandas as pd
import numpy as np
import pytest

import projection as proj


def _ohlcv(n: int = 100, base: float = 100.0, trend: float = 0.5) -> pd.DataFrame:
    """Synthetic uptrending OHLCV with enough bars for structure detection."""
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


def test_returns_list():
    df = _ohlcv(200)
    current = float(df["close"].iloc[-1])
    result = proj.nearby_levels(current + 20, current, df, "up")
    assert isinstance(result, list)
    for item in result:
        assert "price" in item
        assert "source" in item
        assert "dist_pct" in item


def test_empty_on_none_inputs():
    assert proj.nearby_levels(None, 100, _ohlcv(), "up") == []
    assert proj.nearby_levels(120, None, _ohlcv(), "up") == []
    assert proj.nearby_levels(120, 100, None, "up") == []


def test_empty_on_short_df():
    df = _ohlcv(10)
    assert proj.nearby_levels(120, 100, df, "up") == []


def test_at_most_three():
    df = _ohlcv(200)
    current = float(df["close"].iloc[-1])
    result = proj.nearby_levels(current + 50, current, df, "up")
    assert len(result) <= 3


def test_sorted_by_distance_from_target():
    df = _ohlcv(200)
    current = float(df["close"].iloc[-1])
    result = proj.nearby_levels(current + 30, current, df, "up")
    if len(result) >= 2:
        target = current + 30
        dists = [abs(r["price"] - target) for r in result]
        assert dists == sorted(dists), "should be sorted nearest-to-target first"


def test_levels_between_current_and_target():
    df = _ohlcv(200)
    current = float(df["close"].iloc[-1])
    target = current + 30
    result = proj.nearby_levels(target, current, df, "up")
    for r in result:
        assert current < r["price"] < target, (
            f"level {r['price']} not between {current} and {target}")


def test_dist_pct_sign():
    df = _ohlcv(200)
    current = float(df["close"].iloc[-1])
    target = current + 30
    result = proj.nearby_levels(target, current, df, "up")
    for r in result:
        assert r["dist_pct"] < 0, (
            "levels between current and target should have negative dist_pct "
            "(they are BEFORE the target)")


def test_down_direction():
    df = _ohlcv(200, base=200, trend=-0.5)
    current = float(df["close"].iloc[-1])
    target = current - 30
    result = proj.nearby_levels(target, current, df, "down")
    for r in result:
        assert target < r["price"] < current
