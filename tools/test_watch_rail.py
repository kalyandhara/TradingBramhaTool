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
    assert not p.exists()          # nothing usable -> nothing written


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


def test_names_to_add_skips_already_watched():
    # add_watchlist_symbol is INSERT OR REPLACE: re-adding a watched name would
    # reset its note and added_date (review finding, B-179).
    assert wr.names_to_add(["TCS", "INFY", "TCS"], ["INFY"]) == ["TCS"]
    assert wr.names_to_add(["INFY"], ["INFY"]) == []


def test_table_key_changes_with_context_and_nonce():
    # A dataframe's selection lives under its key; a key that ignores source,
    # filter, snapshot date or a completed action carries row positions over to
    # rows the user never picked (review finding, B-179).
    base = wr.table_key("Banks", "", "2026-10-16", 0)
    assert base != wr.table_key(wr.WATCHLIST_KEY, "", "2026-10-16", 0)
    assert base != wr.table_key("Banks", "ba", "2026-10-16", 0)
    assert base != wr.table_key("Banks", "", "2026-10-17", 0)
    assert base != wr.table_key("Banks", "", "2026-10-16", 1)
    assert base == wr.table_key("Banks", "", "2026-10-16", 0)


def test_unusable_frame_leaves_existing_snapshot_untouched(tmp_path):
    # An all-NA bhavcopy (NSE half-published) must not wipe yesterday's good
    # closes with an empty file (review finding, B-179).
    p = tmp_path / "c.json"
    good = pd.DataFrame({"symbol": ["TCS"], "close": [110.0], "prev_close": [100.0]})
    assert wr.write_closes(good, "2026-10-16", p) == 1
    before = p.read_text()
    nan = pd.DataFrame({"symbol": ["TCS", "INFY"], "close": [float("nan")] * 2,
                        "prev_close": [float("nan")] * 2})
    assert wr.write_closes(nan, "2026-10-17", p) == 0
    assert p.read_text() == before


def test_inf_row_is_skipped_and_the_rest_written(tmp_path):
    # inf passes `> 0`; json.dumps(allow_nan=False) then raised and the whole
    # snapshot silently failed to write.
    p = tmp_path / "c.json"
    f = pd.DataFrame({"symbol": ["A", "B", "C"], "close": ["inf", 10.0, 20.0],
                      "prev_close": [5.0, float("inf"), 19.0]})
    assert wr.write_closes(f, "2026-10-17", p) == 1
    assert wr.read_closes(p)[0] == {"C": (20.0, 19.0)}


def _frame(close):
    return pd.DataFrame({"symbol": ["TCS"], "close": [close], "prev_close": [100.0]})


def test_refresh_reports_a_failed_fetch(tmp_path):
    def boom():
        raise ConnectionError("NSE 403")
    ok, msg = wr.refresh_closes(boom, tmp_path / "c.json")
    assert not ok and "NSE 403" in msg


def test_refresh_reports_no_data_and_unusable_data(tmp_path):
    ok, msg = wr.refresh_closes(lambda: (None, None), tmp_path / "c.json")
    assert not ok and "reach NSE" in msg
    ok, msg = wr.refresh_closes(lambda: (_frame(float("nan")), "2026-10-17"),
                                tmp_path / "c.json")
    assert not ok and "no usable" in msg
    assert not (tmp_path / "c.json").exists()


def test_refresh_success(tmp_path):
    ok, _ = wr.refresh_closes(lambda: (_frame(110.0), "2026-10-17"), tmp_path / "c.json")
    assert ok and wr.read_closes(tmp_path / "c.json")[1] == "2026-10-17"


def test_rail_sector_map_never_fetches(monkeypatch):
    # Home never fetches on load: a cache miss (new month) or NSE down must
    # show "Sector map unavailable", not block the render on an NSE call.
    import portfolio_db
    import sectors

    def no_fetch(*a, **k):
        raise AssertionError("rail sector lookup hit the network")
    monkeypatch.setattr(sectors, "refresh_cache", no_fetch)
    monkeypatch.setattr(sectors, "symbol_map", no_fetch)
    monkeypatch.setattr(portfolio_db, "init_db", lambda: None)
    monkeypatch.setattr(portfolio_db, "get_sector_map", lambda **k: {})
    assert wr.rail_sector_map() == {}
    monkeypatch.setattr(portfolio_db, "get_sector_map", lambda **k: {"TCS": "IT"})
    assert wr.rail_sector_map() == {"TCS": "IT"}


def test_pick_index_follows_the_key_not_the_label():
    keys = [wr.WATCHLIST_KEY, "Banks", "IT"]
    assert wr.pick_index(keys, "IT") == 2
    assert wr.pick_index(keys, "Gone") == 0
    assert wr.pick_index(keys, None) == 0


def test_chart_symbol_suffix_rule():
    assert wr.chart_symbol("TCS") == "TCS.NS"
    assert wr.chart_symbol(" tcs ") == "TCS.NS"
    assert wr.chart_symbol("^NSEI") == "^NSEI"
    assert wr.chart_symbol("MARINE.BO") == "MARINE.BO"


def test_rail_rows_are_json_safe_and_mode_aware():
    import json
    closes = {"TCS": (110.0, 100.0)}
    f = wr.rail_frame("Information Technology", ["INFY"], SMAP, closes)
    rows = wr.rail_rows(f, "Information Technology")
    assert [r["symbol"] for r in rows] == ["TCS", "INFY"]
    assert rows[0]["close"] == 110.0 and math.isclose(rows[0]["day_pct"], 10.0)
    assert rows[1]["close"] is None and rows[1]["day_pct"] is None
    assert [r["watched"] for r in rows] == [False, True]
    assert rows[0]["chart"] == "TCS.NS"
    json.dumps(rows, allow_nan=False)            # no NaN reaches the browser
    wl = wr.rail_rows(wr.rail_frame(wr.WATCHLIST_KEY, ["INFY"], SMAP, {}), wr.WATCHLIST_KEY)
    assert wl[0]["watched"] is None


def test_rail_rows_drop_symbols_with_markup():
    # Defence in depth (security review, B-180): the component escapes, but no
    # markup metacharacter should reach the browser at all.
    smap = {"M&M": "Auto", "BAJAJ-AUTO": "Auto", "A<img src=x onerror=1>": "Auto",
            'X"Y': "Auto"}
    rows = wr.rail_rows(wr.rail_frame("Auto", [], smap, {}), "Auto")
    assert [r["symbol"] for r in rows] == ["BAJAJ-AUTO", "M&M"]
    assert wr.is_safe_symbol("^NSEI") and wr.is_safe_symbol("MARINE.BO")
    assert not wr.is_safe_symbol("A B")
