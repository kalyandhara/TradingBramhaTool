"""cpr_vp — CPR band normalisation, position, RVOL, confluence and the five
playbook setups, each on a hand-built last bar."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cpr_vp  # noqa: E402


def _frame(n=80, seed=1, last=None, prev=None):
    """Flat-ish history around 100 so the profile has a fat HVN at 100, then a
    hand-written prior bar and last bar."""
    rs = np.random.default_rng(seed)
    idx = pd.date_range("2026-05-01", periods=n, freq="B")
    close = 100 + rs.normal(0, 0.3, n).cumsum() * 0.2
    df = pd.DataFrame({"open": close, "high": close + 0.4, "low": close - 0.4,
                       "close": close, "volume": 1_000_000}, index=idx)
    if prev:
        df.iloc[-2, :] = [prev["o"], prev["h"], prev["l"], prev["c"], prev.get("v", 1_000_000)]
    if last:
        df.iloc[-1, :] = [last["o"], last["h"], last["l"], last["c"], last.get("v", 1_000_000)]
    return df


def test_band_is_normalised_and_position_read():
    # prior bar h=102 l=98 c=98 -> pp=99.33 bc=100 tc=98.67 (tc<bc raw) -> swapped
    df = _frame(prev={"o": 100, "h": 102, "l": 98, "c": 98},
                last={"o": 100.5, "h": 101, "l": 100.2, "c": 100.8})
    r = cpr_vp.read(df)
    assert r["levels"]["tc"] > r["levels"]["bc"]
    assert r["position"] == "above_tc" and r["band"] in ("narrow", "normal", "wide")
    assert r["rvol"] == pytest.approx(1.0)


def test_hold_above_cpr_with_volume_fires_only_with_rvol():
    prev = {"o": 100, "h": 101, "l": 99, "c": 100.5}       # pp 100.17 bc 100 tc 100.33
    quiet = _frame(prev=prev, last={"o": 100.6, "h": 101.5, "l": 100.4, "c": 101.2})
    loud = _frame(prev=prev, last={"o": 100.6, "h": 101.5, "l": 100.4, "c": 101.2, "v": 3_000_000})
    assert "hold_above_cpr_volume" not in cpr_vp.read(quiet)["setups"]
    r = cpr_vp.read(loud)
    assert "hold_above_cpr_volume" in r["setups"] and r["bias"] == "bullish"
    assert r["rvol"] == pytest.approx(3.0)


def test_rejection_and_breakdown_are_bearish():
    prev = {"o": 100, "h": 101, "l": 99, "c": 100.5}       # bc 100, tc 100.33
    rej = _frame(prev=prev, last={"o": 100.4, "h": 100.6, "l": 99.0, "c": 99.2, "v": 3_000_000})
    r = cpr_vp.read(rej)
    assert "rejection_at_cpr" in r["setups"] and r["bias"] == "bearish"
    assert "breakdown_below_cpr" not in r["setups"]          # rejection takes precedence


def test_cpr_retest_buying():
    prev = {"o": 100, "h": 101, "l": 99, "c": 100.5}       # bc 100, tc 100.33
    df = _frame(prev=prev, last={"o": 100.4, "h": 101.0, "l": 100.1, "c": 100.9})  # low dipped into band, closed above
    r = cpr_vp.read(df)
    assert "cpr_retest_buying" in r["setups"]


def test_confluence_names_the_level_and_zone():
    # 80 flat bars at ~100 -> the profile's HVN/POC sits at 100; a CPR band at 100 is inside it
    df = _frame(prev={"o": 100, "h": 100.3, "l": 99.7, "c": 100.0},
                last={"o": 100, "h": 100.2, "l": 99.8, "c": 100.0})
    r = cpr_vp.read(df)
    assert r["cpr_in_hvn"] is True
    assert any(t in ("HVN", "POC") for t in r["confluence"].get("P", []))
    assert "P∈" in cpr_vp.confluence_text(r)


def test_scan_keeps_setups_or_confluence_and_counts_scanned():
    prev = {"o": 100, "h": 101, "l": 99, "c": 100.5}
    loud = _frame(prev=prev, last={"o": 100.6, "h": 101.5, "l": 100.4, "c": 101.2, "v": 3_000_000})
    # far from the profile and no setup: a quiet bar way above everything
    quiet = _frame(prev={"o": 120, "h": 121, "l": 119, "c": 120}, last={"o": 130, "h": 131, "l": 129, "c": 130})
    frames = {"LOUD": loud, "QUIET": quiet, "NONE": None}
    stats = {}
    rows = cpr_vp.scan(["LOUD", "QUIET", "NONE"], lambda s, days=140: frames[s], stats=stats)
    assert stats["scanned"] == 2
    assert [r["Symbol"] for r in rows] == ["LOUD"]
    assert rows[0]["Setups"] == "Holds above CPR with volume" and rows[0]["Bias"] == "bullish"


def test_read_returns_none_on_short_or_bad_frames():
    assert cpr_vp.read(None) is None
    assert cpr_vp.read(pd.DataFrame({"close": [1, 2]})) is None
    assert cpr_vp.read(_frame(n=10)) is None
