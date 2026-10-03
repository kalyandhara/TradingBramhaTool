"""Tests for the No-Supply scanner (B-122).

Run:  py -3 -m pytest tools/test_no_supply.py -q
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scanner_templates as sc
import simple_volume as sv

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache" / "backtest"


def _make_df(n: int = 100, *, close_start: float = 100.0,
             trend_up: bool = True, vol: float = 1000.0) -> pd.DataFrame:
    """Synthetic OHLCV frame."""
    closes = [close_start]
    for i in range(1, n):
        closes.append(closes[-1] * (1.002 if trend_up else 0.998))
    closes = np.array(closes)
    return pd.DataFrame({
        "open": closes * 0.999,
        "high": closes * 1.005,
        "low": closes * 0.995,
        "close": closes,
        "volume": [vol] * n,
    })


class TestSimpleVolumePython:
    def test_classify_length(self):
        df = _make_df(100)
        result = sv.classify(df)
        assert len(result) == 100

    def test_ma_null_before_window(self):
        df = _make_df(60)
        result = sv.classify(df, ma_len=50)
        assert np.isnan(result.iloc[0]["ma"])
        assert not np.isnan(result.iloc[49]["ma"])

    def test_dry_bar(self):
        df = _make_df(60, vol=1000.0)
        df.loc[59, "volume"] = 100.0  # well below MA/5 = 200
        result = sv.classify(df)
        assert result.iloc[59]["kind"] == "dry"

    def test_ppv(self):
        df = _make_df(60, vol=1000.0)
        # Make a down day in the lookback window
        df.loc[55, "close"] = df.loc[55, "open"] - 1
        df.loc[55, "volume"] = 500.0
        # Last bar is an up day with volume beating the down day
        df.loc[59, "close"] = df.loc[59, "open"] + 1
        df.loc[59, "volume"] = 600.0
        result = sv.classify(df)
        assert result.iloc[59]["kind"] == "ppv"

    def test_no_supply_window(self):
        df = _make_df(60, vol=1000.0)
        result = sv.classify(df)
        ns = sv.no_supply_window(result, window=10)
        assert isinstance(ns["red_count"], int)
        assert isinstance(ns["has_supply"], bool)


class TestNoSupplyScanner:
    def test_returns_none_for_downtrend(self):
        df = _make_df(300, trend_up=False)
        assert sc.scan_no_supply(df) is None

    def test_returns_none_for_short_frame(self):
        df = _make_df(30)
        assert sc.scan_no_supply(df) is None

    def test_gate_scanners_field(self):
        """If it fires, gate_scanners lists which family members matched."""
        for f in sorted(CACHE.glob("*_1d.json")):
            with open(f) as fh:
                data = json.load(fh)
            df = pd.DataFrame(data["bars"])
            r = sc.scan_no_supply(df)
            if r is not None:
                assert len(r["gate_scanners"]) >= 1
                assert r["red_count"] == 0
                assert r["ppv_count"] >= 1
                return
        pytest.skip("no hit in cache")

    def test_has_no_entry_stop_target(self):
        """No-Supply is a screen, not a trade trigger."""
        for f in sorted(CACHE.glob("*_1d.json")):
            with open(f) as fh:
                data = json.load(fh)
            df = pd.DataFrame(data["bars"])
            r = sc.scan_no_supply(df)
            if r is not None:
                assert "entry" not in r
                assert "stop" not in r
                assert "target" not in r
                return
        pytest.skip("no hit in cache")

    def test_in_scanner_registry(self):
        assert "No-Supply (new high + clean volume)" in sc.SCANNERS

    def test_category_is_momentum(self):
        assert sc.SCANNERS["No-Supply (new high + clean volume)"]["category"] == "Momentum"
