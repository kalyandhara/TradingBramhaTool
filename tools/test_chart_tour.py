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
