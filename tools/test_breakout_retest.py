"""Tests for scan_breakout_retest (B-6).

Builds synthetic price series that exercise each stage of the scanner:
resistance cluster → breakout → pullback → retest hold.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scanner_templates import scan_breakout_retest


def _make_df(prices: list[tuple], vol: float = 1_000_000) -> pd.DataFrame:
    """Build a DataFrame from (open, high, low, close) tuples."""
    rows = []
    for i, (o, h, l, c) in enumerate(prices):
        rows.append({
            "open": o, "high": h, "low": l, "close": c,
            "volume": vol,
        })
    return pd.DataFrame(rows)


def _base_then_breakout_then_retest(
    n_base: int = 40, level: float = 100.0, n_touches: int = 5,
    breakout_bars: int = 3, pullback_bars: int = 5, hold_bars: int = 3,
    vol: float = 1_000_000, breakout_vol_mult: float = 2.0,
    pullback_depth_pct: float = 0.005,
) -> pd.DataFrame:
    """Synthetic series: flat base → breakout → pullback to level → hold."""
    prices = []
    # Phase 1: flat base with touches at the ceiling
    touch_every = max(1, n_base // n_touches)
    for i in range(n_base):
        if i % touch_every == 0:
            prices.append((level - 3, level, level - 5, level - 1))
        else:
            prices.append((level - 5, level - 2, level - 7, level - 4))

    vols = [vol] * n_base

    # Phase 2: breakout bars — close above the level
    for i in range(breakout_bars):
        prices.append((level + 1, level + 4 + i, level, level + 3 + i))
        vols.append(vol * breakout_vol_mult)

    # Phase 3: pullback — low dips back near the level
    pb_close = level + 1
    for i in range(pullback_bars):
        pb_low = level * (1 + pullback_depth_pct)
        prices.append((pb_close + 1, pb_close + 2, pb_low, pb_close))
        vols.append(vol * 0.5)  # low volume pullback

    # Phase 4: hold — close above the level
    for i in range(hold_bars):
        prices.append((level + 1, level + 3, level + 0.5, level + 2))
        vols.append(vol)

    rows = []
    for i, (o, h, l, c) in enumerate(prices):
        rows.append({"open": o, "high": h, "low": l, "close": c, "volume": vols[i]})
    return pd.DataFrame(rows)


class TestBasicDetection:
    def test_fires_on_classic_retest(self):
        df = _base_then_breakout_then_retest()
        result = scan_breakout_retest(df)
        assert result is not None
        assert result["pattern_type"] == "Breakout Retest"

    def test_has_trade_plan(self):
        df = _base_then_breakout_then_retest()
        result = scan_breakout_retest(df)
        assert result is not None
        assert "entry" in result
        assert "stop" in result
        assert "target" in result
        assert result["stop"] < result["entry"]
        assert result["target"] > result["entry"]

    def test_has_metadata(self):
        df = _base_then_breakout_then_retest()
        result = scan_breakout_retest(df)
        assert result is not None
        assert result["touches"] >= 3
        assert result["bars_since_break"] >= 2
        assert "level" in result


class TestRejections:
    def test_no_breakout(self):
        """Price never breaks above the ceiling → no signal."""
        prices = [(95, 100, 93, 97)] * 60
        df = _make_df(prices)
        assert scan_breakout_retest(df) is None

    def test_no_pullback(self):
        """Breakout without any pullback (price just keeps going) → no signal."""
        prices = [(95, 100, 93, 97)] * 40  # base
        for i in range(20):
            prices.append((101 + i, 105 + i, 100 + i, 104 + i))
        df = _make_df(prices)
        assert scan_breakout_retest(df) is None

    def test_level_violated(self):
        """Price breaks through, pulls back, but closes BELOW the level → no signal."""
        prices = [(95, 100, 93, 97)] * 40
        prices += [(101, 105, 100, 104)] * 3  # breakout
        prices += [(99, 101, 94, 95)] * 5     # falls well below level
        df = _make_df(prices)
        assert scan_breakout_retest(df) is None

    def test_too_few_bars(self):
        prices = [(50, 52, 48, 51)] * 10
        df = _make_df(prices)
        assert scan_breakout_retest(df) is None

    def test_too_extended(self):
        """Price ran too far past the level (anti-chase) → no signal."""
        df = _base_then_breakout_then_retest()
        # Manually make the close very extended
        df.loc[df.index[-1], "close"] = 200.0
        df.loc[df.index[-1], "high"] = 201.0
        assert scan_breakout_retest(df) is None

    def test_too_few_touches(self):
        """Only 1-2 touches at the ceiling → no signal."""
        prices = [(90, 95, 88, 92)] * 50  # mostly below
        prices[10] = (95, 100, 93, 97)     # one touch
        prices += [(101, 105, 100, 104)] * 3  # breakout
        prices += [(100, 102, 99, 101)] * 5   # pullback
        df = _make_df(prices)
        assert scan_breakout_retest(df) is None


class TestScoring:
    def test_score_in_range(self):
        df = _base_then_breakout_then_retest()
        result = scan_breakout_retest(df)
        assert result is not None
        assert 0 < result["score"] <= 100

    def test_more_touches_higher_score(self):
        df3 = _base_then_breakout_then_retest(n_touches=3)
        df7 = _base_then_breakout_then_retest(n_touches=7)
        r3 = scan_breakout_retest(df3)
        r7 = scan_breakout_retest(df7)
        if r3 is not None and r7 is not None:
            assert r7["score"] >= r3["score"]

    def test_volume_flags(self):
        df = _base_then_breakout_then_retest(breakout_vol_mult=2.0)
        result = scan_breakout_retest(df)
        if result is not None:
            assert "breakout_vol_ok" in result
            assert "dry_pullback" in result


class TestTimingConstraints:
    def test_old_breakout_rejected(self):
        """A breakout that happened > 30 bars ago is too stale."""
        df = _base_then_breakout_then_retest(
            pullback_bars=20, hold_bars=15,
        )
        result = scan_breakout_retest(df)
        # With 20 + 15 = 35 bars after the breakout, it exceeds the 30-bar limit
        assert result is None

    def test_fresh_breakout_rejected(self):
        """A breakout that happened only 1 bar ago — no time for pullback."""
        df = _base_then_breakout_then_retest(
            breakout_bars=1, pullback_bars=0, hold_bars=1,
        )
        result = scan_breakout_retest(df)
        assert result is None


class TestRsRaw:
    def test_rs_raw_present(self):
        df = _base_then_breakout_then_retest()
        result = scan_breakout_retest(df)
        if result is not None:
            assert "rs_raw" in result
