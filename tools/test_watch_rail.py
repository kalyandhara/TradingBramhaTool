"""Tests for the Home watchlist rail's pure logic (B-179).

    py -3 -m pytest tools/test_watch_rail.py -q
"""
from __future__ import annotations

import math

import pandas as pd

import watch_rail as wr

SMAP = {"TCS": "Information Technology", "INFY": "Information Technology",
        "HDFCBANK": "Financial Services", "ONGC": "Oil Gas & Consumable Fuels",
        "XYZ": None}


def test_write_then_read_round_trip(tmp_path):
    p = tmp_path / "c.json"
    f = pd.DataFrame({"symbol": ["TCS", "INFY"], "close": [100.0, 50.0],
                      "prev_close": [80.0, 50.0]})
    assert wr.write_closes(f, "2026-10-17", p) == 2
    rows, td = wr.read_closes(p)
    assert td == "2026-10-17" and rows["TCS"] == (100.0, 80.0)


def test_write_skips_nan_and_zero(tmp_path):
    p = tmp_path / "c.json"
    f = pd.DataFrame({"symbol": ["A", "B", "C"], "close": [float("nan"), 0.0, 10.0],
                      "prev_close": [5.0, 5.0, 0.0]})
    assert wr.write_closes(f, None, p) == 0
    assert "NaN" not in p.read_text() and "Infinity" not in p.read_text()


def test_read_missing_or_corrupt_is_empty(tmp_path):
    assert wr.read_closes(tmp_path / "nope.json") == ({}, None)
    bad = tmp_path / "bad.json"
    bad.write_text('{"rows": {"TCS": [1')
    assert wr.read_closes(bad) == ({}, None)


def test_write_never_raises(tmp_path):
    assert wr.write_closes(pd.DataFrame({"x": [1]}), None, tmp_path / "c.json") == 0


def test_sector_options_order_counts_and_raw_keys():
    opts = wr.sector_options(SMAP, ["TCS", "XYZ"])
    assert opts[0] == ("♥ Your watchlist (2)", wr.WATCHLIST_KEY)
    assert opts[1:] == [("Financial Services (1)", "Financial Services"),
                        ("Information Technology (2)", "Information Technology"),
                        ("Oil Gas & Consumable Fuels (1)", "Oil Gas & Consumable Fuels")]


def test_watchlist_frame_keeps_unmapped_names_blank():
    df = wr.rail_frame(wr.WATCHLIST_KEY, ["XYZ", "TCS"], SMAP, {})
    assert list(df.columns) == ["Symbol", "Close", "Day %", "♥"]
    assert list(df["Symbol"]) == ["XYZ", "TCS"]          # source order, no prices
    assert df["♥"].all() and df["Close"].isna().all()


def test_sector_frame_marks_watched_and_sorts_by_day_pct():
    closes = {"TCS": (110.0, 100.0), "INFY": (90.0, 100.0)}
    df = wr.rail_frame("Information Technology", ["INFY"], SMAP, closes)
    assert list(df["Symbol"]) == ["TCS", "INFY"]
    assert list(df["♥"]) == [False, True]
    assert math.isclose(df.iloc[0]["Day %"], 10.0)


def test_unpriced_rows_sort_last():
    df = wr.rail_frame("Information Technology", [], SMAP, {"INFY": (90.0, 100.0)})
    assert list(df["Symbol"]) == ["INFY", "TCS"]


def test_filter_is_literal_case_insensitive():
    smap = {"M&M": "Automobile and Auto Components",
            "BAJAJ-AUTO": "Automobile and Auto Components"}
    df = wr.rail_frame("Automobile and Auto Components", [], smap, {}, query="m&")
    assert list(df["Symbol"]) == ["M&M"]
    assert wr.rail_frame("Automobile and Auto Components", [], smap, {}, query="(").empty


def test_load_bhav_writes_snapshot(tmp_path, monkeypatch):
    import trending_stocks as ts
    frame = pd.DataFrame({"symbol": ["TCS"], "close": [110.0], "prev_close": [100.0],
                          "trade_date": ["2026-10-17"]})
    monkeypatch.setattr(ts.sp, "fetch_bhavcopy_frame", lambda: frame)
    monkeypatch.setattr(wr, "CLOSES_PATH", tmp_path / "c.json")
    df, td = ts.load_bhav()
    assert td == "2026-10-17"
    assert wr.read_closes(tmp_path / "c.json")[0]["TCS"] == (110.0, 100.0)
