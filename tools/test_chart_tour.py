"""Tests for chart_tour.py (B-186, "Tour this chart"), offline.

The tour is a reading of the chart, so the tests pin three things:

  * every detector fires on the rule eVector ships and not one bar or one
    percent either side of it — the badge on a card describes exactly that rule;
  * the chart is only ever asked to do one of seven things, so the page can
    never be told to touch the user's own indicators or drawings;
  * a broken detector costs its own card, never the tour.
"""
import numpy as np
import pandas as pd
import pytest

import chart_tour as ct


def frame(close, *, high=None, low=None, open_=None, volume=None, start="2023-01-02"):
    close = np.asarray(close, float)
    n = len(close)
    idx = pd.bdate_range(start, periods=n, tz="UTC")
    return pd.DataFrame({
        "open": close if open_ is None else np.asarray(open_, float),
        "high": close * 1.005 if high is None else np.asarray(high, float),
        "low": close * 0.995 if low is None else np.asarray(low, float),
        "close": close,
        "volume": np.full(n, 1000.0) if volume is None else np.asarray(volume, float),
    }, index=idx)


# ── actions ───────────────────────────────────────────────────────────────────

ALL_SEVEN = [
    {"type": "CLEAR"},
    {"type": "ZOOM_TO_RANGE", "from": 1, "to": 2},
    {"type": "PRICE_LEVEL", "price": 10.0, "label": "x", "tone": "up"},
    {"type": "HIGHLIGHT_CANDLE", "time": 1, "tone": "accent"},
    {"type": "HIGHLIGHT_RANGE", "from": 1, "to": 2, "tone": "neutral"},
    {"type": "INDICATORS", "ids": ["ema20", "rsi"]},
    {"type": "COMPARE", "symbols": ["^NSEI"]},
]


def test_validate_actions_accepts_the_seven():
    assert ct.validate_actions(ALL_SEVEN) == ALL_SEVEN


def test_validate_actions_rejects_unknown_type():
    with pytest.raises(ValueError, match="DRAW_ARROW"):
        ct.validate_actions([{"type": "DRAW_ARROW"}])


def test_validate_actions_rejects_bad_tone():
    with pytest.raises(ValueError, match="green"):
        ct.validate_actions([{"type": "PRICE_LEVEL", "price": 1.0, "label": "x", "tone": "green"}])


def test_validate_actions_rejects_missing_field():
    with pytest.raises(ValueError, match="price"):
        ct.validate_actions([{"type": "PRICE_LEVEL", "label": "x", "tone": "up"}])


# ── Now ───────────────────────────────────────────────────────────────────────

def test_now_step_range_and_trend():
    df = frame(np.linspace(100, 200, 100))
    s = ct.now_step(df)
    assert s["id"] == "now"
    assert s["facts"]["trend"] == "Uptrend"
    assert s["facts"]["hi63"] == pytest.approx(df["high"].iloc[-63:].max())
    assert s["facts"]["lo63"] == pytest.approx(df["low"].iloc[-63:].min())
    types = [a["type"] for a in s["actions"]]
    assert types.count("PRICE_LEVEL") == 2
    zoom = next(a for a in s["actions"] if a["type"] == "ZOOM_TO_RANGE")
    assert zoom["from"] == ct.t_of(df, -63) and zoom["to"] == ct.t_of(df, -1)
    ct.validate_actions(s["actions"])


def test_now_step_downtrend_and_sideways():
    assert ct.now_step(frame(np.linspace(200, 100, 100)))["facts"]["trend"] == "Downtrend"
    assert ct.now_step(frame(np.full(100, 100.0)))["facts"]["trend"] == "Sideways"


def test_now_step_rvol_skips_zero_volume():
    s = ct.now_step(frame(np.linspace(100, 200, 100), volume=np.zeros(100)))
    assert s["facts"]["rvol"] is None
    assert "volume" not in s["body"].lower()


def test_t_of_is_unix_seconds():
    df = frame(np.full(5, 1.0), start="2024-01-01")
    assert ct.t_of(df, 0) == int(pd.Timestamp("2024-01-01", tz="UTC").timestamp())


# ── breakout / breakdown (55-session closing extremes) ───────────────────────

def _flat_then(n=80, at=-5, value=106.0, after=105.0, base=100.0):
    c = np.full(n, base)
    k = n + at
    c[k] = value
    c[k + 1:] = after
    return c


def test_breakout55_fires_and_watch_is_98pct():
    df = frame(_flat_then())
    f = ct.det_breakout55(df)
    assert len(f) == 1 and f[0].detector == "breakout55" and f[0].tone == "up"
    assert f[0].facts["level"] == pytest.approx(100.0)
    assert f[0].watch["level"] == pytest.approx(98.0)
    assert f[0].time == ct.t_of(df, -5)
    ct.validate_actions(f[0].actions)


def test_breakout_becomes_failed_below_98pct():
    df = frame(_flat_then(after=97.5))
    f = ct.det_breakout55(df)
    assert f[0].detector == "failed_breakout55" and f[0].tone == "down"


def test_breakout_at_exactly_98pct_is_not_failed():
    assert ct.det_breakout55(frame(_flat_then(after=98.0)))[0].detector == "breakout55"


def test_breakout_older_than_15_bars_ignored():
    assert ct.det_breakout55(frame(_flat_then(at=-20))) == []


def test_breakout_weight_formula():
    c = _flat_then(at=-1, value=106.0)
    v = np.full(80, 1000.0)
    v[-1] = 2000.0
    f = ct.det_breakout55(frame(c, volume=v))
    assert f[0].weight == pytest.approx(0.7 + 14 / 50 + 0.2)


def test_breakdown55_mirror_and_failed_at_102pct():
    f = ct.det_breakdown55(frame(_flat_then(value=94.0, after=95.0)))
    assert f[0].detector == "breakdown55" and f[0].tone == "down"
    assert f[0].watch["level"] == pytest.approx(102.0)
    g = ct.det_breakdown55(frame(_flat_then(value=94.0, after=102.5)))
    assert g[0].detector == "failed_breakdown55" and g[0].tone == "up"


# ── gaps ──────────────────────────────────────────────────────────────────────

def _gap_frame(gap=0.035, at=-4, fill=False, n=80):
    c = np.full(n, 100.0)
    k = n + at
    c[k:] = 100.0 * (1 + gap)
    o = c.copy()
    lo = c * 0.995
    hi = c * 1.005
    if fill:
        lo[k + 1] = 99.9 if gap > 0 else lo[k + 1]
        hi[k + 1] = 100.1 if gap < 0 else hi[k + 1]
    return frame(c, open_=o, low=lo, high=hi)


def test_gap_up_unfilled_fires_filled_does_not():
    f = ct.det_gaps(_gap_frame())
    assert len(f) == 1 and f[0].detector == "gap_up"
    assert f[0].watch["level"] == pytest.approx(100.0)
    assert ct.det_gaps(_gap_frame(fill=True)) == []


def test_gap_down_unfilled():
    f = ct.det_gaps(_gap_frame(gap=-0.04))
    assert f[0].detector == "gap_down" and f[0].tone == "down"


def test_gap_below_3pct_ignored():
    assert ct.det_gaps(_gap_frame(gap=0.029)) == []


def test_gap_older_than_10_bars_ignored():
    assert ct.det_gaps(_gap_frame(at=-12)) == []
