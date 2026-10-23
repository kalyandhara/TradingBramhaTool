"""plan_status.py — the Watchlist's 'is this plan still alive?' column."""
from __future__ import annotations

import pandas as pd
import pytest

import plan_status as ps


def _bars(rows, start="2026-10-01"):
    d = pd.bdate_range(start, periods=len(rows))
    o, h, l, c = zip(*rows)
    return pd.DataFrame({"date": d, "open": o, "high": h, "low": l, "close": c})


LONG = {"entry": 100.0, "stop": 95.0, "target": 110.0, "time_stop": 5}
FLAT = (100, 101, 99, 100)


def test_stop_hit_after_the_run_date():
    df = _bars([FLAT, FLAT, (99, 100, 94, 95)])
    st = ps.judge(LONG, "2026-10-01", df)              # walk starts 10-02
    assert st["status"] == "STOP HIT" and st["r"] < 0


def test_bars_on_or_before_the_run_date_are_never_judged():
    # The stop traded ON the run date — the card was drawn from that bar.
    df = _bars([(99, 100, 90, 95), FLAT, FLAT])
    assert ps.judge(LONG, "2026-10-01", df)["status"] == "LIVE"


def test_same_bar_stop_and_target_is_a_stop():
    df = _bars([FLAT, (100, 111, 94, 105)])
    assert ps.judge(LONG, "2026-10-01", df)["status"] == "STOP HIT"


def test_target_hit():
    df = _bars([FLAT, (101, 111, 100, 110)])
    assert ps.judge(LONG, "2026-10-01", df)["status"] == "TARGET HIT"


def test_expired_on_its_own_time_stop():
    df = _bars([FLAT] * 9)
    st = ps.judge(LONG, "2026-10-01", df)
    assert st["status"] == "EXPIRED"
    assert ps.label(st).endswith("5/5 bars")


def test_no_time_stop_stays_live():
    card = dict(LONG, time_stop=None)
    assert ps.judge(card, "2026-10-01", _bars([FLAT] * 9))["status"] == "LIVE"


def test_short_plan_is_mirrored():
    short = {"entry": 100.0, "stop": 105.0, "target": 90.0, "time_stop": 8}
    assert ps.judge(short, "2026-10-01", _bars([FLAT, (101, 106, 100, 104)]))["status"] == "STOP HIT"
    assert ps.judge(short, "2026-10-01", _bars([FLAT, (99, 100, 89, 90)]))["status"] == "TARGET HIT"


def test_watch_only_card_is_not_judged():
    st = ps.judge(dict(LONG, actionable=False), "2026-10-01", None)
    assert st["status"] == "WATCH ONLY"


def test_datetime_index_works_too():
    df = _bars([FLAT, (99, 100, 94, 95)]).set_index("date")
    assert ps.judge(LONG, "2026-10-01", df)["status"] == "STOP HIT"


def test_pick_plan_prefers_newest_then_actionable():
    rows = [("2026-10-01", "B", LONG),
            ("2026-10-05", "Z", dict(LONG, actionable=False)),
            ("2026-10-05", "A", LONG),
            ("2026-10-09", "C", {"entry": 1, "stop": None, "target": 2})]   # no plan
    assert ps.pick_plan(rows)[:2] == ("2026-10-05", "A")


def test_suggestions_and_failures_stay_per_row():
    good = _bars([FLAT, (99, 100, 94, 95)])

    def rows(sym):
        if sym == "BOOM":
            raise RuntimeError("bad cache")
        return [] if sym == "NONE" else [("2026-10-01", "Order Block Retest", LONG)]

    out = ps.watchlist_status(["OK", "NONE", "BOOM"], rows, lambda s: good)
    assert out["OK"]["status"] in ps.REMOVE_SUGGESTED
    assert ps.plan_source(out["OK"]) == "Order Block Retest · 2026-10-01"
    assert out["NONE"]["status"] == "NO PLAN"
    assert out["BOOM"]["status"] == "NO DATA"
    assert "NO PLAN" not in ps.REMOVE_SUGGESTED and "LIVE" not in ps.REMOVE_SUGGESTED


# ── the entry is an ORDER (backtest.resolve_fill "touch", B-121) ──────────────

BREAKOUT = {"entry": 105.0, "stop": 98.0, "target": 120.0, "time_stop": 10}


def test_entry_never_traded_is_not_filled_after_five_sessions():
    st = ps.judge(BREAKOUT, "2026-10-01", _bars([FLAT] * 7))
    assert st["status"] == "NOT FILLED" and "NOT FILLED" in ps.REMOVE_SUGGESTED


def test_entry_not_traded_yet_is_pending_inside_the_window():
    st = ps.judge(BREAKOUT, "2026-10-01", _bars([FLAT] * 3))
    assert st["status"] == "PENDING" and "PENDING" not in ps.REMOVE_SUGGESTED
    assert ps.label(st).endswith("order 2/5 sessions")


def test_fill_past_the_target_is_missed_not_a_win():
    # The stale-entry case: the session after the card opens above the target.
    st = ps.judge(LONG, "2026-10-01", _bars([FLAT, (115, 118, 114, 116)]))
    assert st["status"] == "MISSED" and st["r"] is None


def test_limit_fill_that_gaps_through_the_stop_claims_no_r():
    limit = {"entry": 97.0, "stop": 95.0, "target": 105.0, "time_stop": 10}
    st = ps.judge(limit, "2026-10-01", _bars([FLAT, (93, 94, 92, 93)]))
    assert st["status"] == "STOP HIT" and st["r"] is None
