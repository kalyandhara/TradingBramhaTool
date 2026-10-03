"""harmonic_patterns — the four-point AB=CD family on hand-built pivots."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import harmonic_patterns as hp  # noqa: E402


def _legs(points, bars_per_leg=12):
    """Straight-line OHLCV through the given pivot prices, tiny ranges so the
    ATR ZigZag confirms exactly these pivots."""
    prices = []
    for a, b in zip(points, points[1:]):
        prices.extend(np.linspace(a, b, bars_per_leg, endpoint=False))
    prices.append(points[-1])
    c = np.array(prices, dtype=float)
    idx = pd.date_range("2026-01-01", periods=len(c), freq="B")
    return pd.DataFrame({"open": c, "high": c + 0.05, "low": c - 0.05,
                         "close": c, "volume": 1000.0}, index=idx)


def test_match_abcd_ratios():
    assert hp._match_abcd(100, 90, 96.2, 86.2)["pattern"] == "AB=CD"           # CD = 1.0 AB
    assert hp._match_abcd(100, 90, 96.2, 80.0)["pattern"] == "Alt AB=CD 1.618"  # CD = 1.62 AB
    assert hp._match_abcd(100, 90, 99.5, 80.0) is None                          # BC retrace too deep
    assert hp._match_abcd(100, 90, 96.2, 91.0) is None                          # CD too short


def test_bullish_abcd_detected_with_plan():
    # lead-in low, A high 100, B low 90, C high 96, D low 86 (CD = AB)
    df = _legs([80, 100, 90, 96, 86])
    m = hp.detect_last_pattern(df, max_age_bars=5, atr_mult=2.0)
    assert m is not None and m["pattern"] == "AB=CD" and m["direction"] == "bullish"
    assert set(m["points"]) == {"A", "B", "C", "D"}
    t = m["trade"]
    assert t["stop"] < t["entry"] < t["targets"][0] < t["targets"][1] <= t["targets"][2]
    assert t["targets"][2] == pytest.approx(96, abs=0.2)


def test_bearish_alternate_abcd():
    # lead-in high, A low 100, B high 110, C low 104, D high 120.2 (CD = 1.62 AB)
    df = _legs([120, 100, 110, 104, 120.2])
    m = hp.detect_last_pattern(df, max_age_bars=5, atr_mult=2.0)
    assert m is not None and m["pattern"].startswith("Alt AB=CD") and m["direction"] == "bearish"
    t = m["trade"]
    assert t["stop"] > t["entry"] > t["targets"][0] > t["targets"][1]


def test_xabcd_still_wins_when_five_pivots_match():
    # A Gartley: X 100, A 120, B 107.6 (0.62), C 115 (0.6 of AB), D 104.3 (AD 0.786 XA)
    df = _legs([110, 100, 120, 107.6, 115.0, 104.3])   # lead-in HIGH so X (100) is a low
    m = hp.detect_last_pattern(df, max_age_bars=5, atr_mult=2.0)
    assert m is not None and m["pattern"] == "Gartley" and "X" in m["points"]


# ── resolve_after_d: what price did after D ──────────────────────────────────
def _plan(direction, d_idx, stop, targets):
    return {"direction": direction, "points": {"D": {"idx": d_idx}},
            "trade": {"stop": stop, "targets": targets}}


def _bars(prices):
    c = np.array(prices, dtype=float)
    return pd.DataFrame({"high": c + 0.5, "low": c - 0.5}, index=range(len(c)))


def test_resolve_live_when_nothing_touched():
    st = hp.resolve_after_d(_bars([100, 101, 100.5]), _plan("bullish", 0, 97, [103, 105, 108]))
    assert st == {"state": "live", "targets_hit": 0, "stop_hit": False, "resolved": False}


def test_resolve_partial_then_complete_bullish():
    part = hp.resolve_after_d(_bars([100, 103, 104]), _plan("bullish", 0, 97, [103, 105, 108]))
    assert part["state"] == "partial" and part["targets_hit"] == 1 and not part["resolved"]
    done = hp.resolve_after_d(_bars([100, 104, 106, 109]), _plan("bullish", 0, 97, [103, 105, 108]))
    assert done["state"] == "complete" and done["targets_hit"] == 3 and done["resolved"]


def test_resolve_stopped_after_t1_bearish():
    # bearish: targets below, stop above; T1 touched, then the stop
    st = hp.resolve_after_d(_bars([100, 97, 101, 104]), _plan("bearish", 0, 103, [97, 95, 92]))
    assert st["state"] == "stopped" and st["targets_hit"] == 1 and st["resolved"]


def test_resolve_same_bar_counts_as_stopped():
    df = pd.DataFrame({"high": [100.5, 104.0], "low": [99.5, 96.0]})
    st = hp.resolve_after_d(df, _plan("bullish", 0, 97, [103, 105, 108]))
    assert st["state"] == "stopped" and st["targets_hit"] == 0


def test_detect_attaches_status():
    m = hp.detect_last_pattern(_legs([80, 100, 90, 96, 86]), max_age_bars=5, atr_mult=2.0)
    assert m["status"]["state"] == "live"
