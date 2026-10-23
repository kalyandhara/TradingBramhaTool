"""crt_weekly.py — the B-165 weekly CRT definition, pinned."""
from __future__ import annotations

import pandas as pd

import crt_weekly as crt


def _daily(weeks):
    """weeks: list of (low, high, close) per week; 5 trading days each, Mon–Fri,
    the week's low on Tuesday and high on Thursday."""
    rows, day = [], pd.Timestamp("2026-01-05")          # a Monday
    for lo, hi, cl in weeks:
        mid = (lo + hi) / 2
        for k in range(5):
            l = lo if k == 1 else mid - 0.1
            h = hi if k == 3 else mid + 0.1
            c = cl if k == 4 else mid
            rows.append({"date": day + pd.Timedelta(days=k), "open": mid,
                         "high": max(h, c), "low": min(l, c), "close": c})
        day += pd.Timedelta(days=7)
    return pd.DataFrame(rows)


def test_sweep_below_and_close_inside_is_an_event():
    ev = crt.bullish_events(_daily([(100, 110, 105), (98, 108, 103)]))
    assert len(ev) == 1 and ev[0]["c1_low"] == 100 and ev[0]["low"] == 98


def test_close_below_candle_one_low_is_a_breakdown_not_crt():
    assert crt.bullish_events(_daily([(100, 110, 105), (95, 105, 99)])) == []


def test_close_above_candle_one_high_is_not_inside():
    assert crt.bullish_events(_daily([(100, 110, 105), (98, 110, 111)])) == []


def test_outside_week_is_excluded():
    assert crt.bullish_events(_daily([(100, 110, 105), (98, 112, 104)])) == []


def test_no_sweep_no_event():
    assert crt.bullish_events(_daily([(100, 110, 105), (101, 108, 103)])) == []


def test_partial_last_week_is_dropped():
    df = _daily([(100, 110, 105), (98, 108, 103)]).iloc[:-2]   # last week ends Wed
    assert crt.bullish_events(df) == []
    assert len(crt.weekly_bars(df)) == 1


def test_event_spans_candle_two_trading_days():
    ev = crt.bullish_events(_daily([(100, 110, 105), (98, 108, 103)]))[0]
    assert ev["start"] == pd.Timestamp("2026-01-12") and ev["end"] == pd.Timestamp("2026-01-16")
