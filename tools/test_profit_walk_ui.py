"""Tests for the profit-walk table mount (B-75), offline.

No streamlit, no network: every function that touches session state takes the
store as an argument, so the behaviour that matters can be pinned without a
running app. What matters is the absent/blank distinction — a table that was
never filled must not show a column of blanks, because that reads as "no
quarterly history for any of these" and it is false.
"""
import pandas as pd

import profit_walk_ui as pw

_Q = {"quarters": [{"period": "2026-06-30", "net_income": 120.0},
                   {"period": "2026-03-31", "net_income": 100.0}]}


def _fetch(symbol):
    return _Q


def _df():
    return pd.DataFrame({"Symbol": ["AAA", "BBB"], "Score": [1, 2]})


def test_a_table_that_was_never_filled_gets_no_column():
    out = pw.attach(_df(), "Symbol", "wl", state={})
    assert pw.COLUMN not in out.columns


def test_filling_adds_the_column_for_that_table_only():
    state = {}
    pw.fill(["AAA", "BBB"], "wl", fetch=_fetch, state=state)
    assert pw.attach(_df(), "Symbol", "wl", state=state)[pw.COLUMN].tolist() \
        == ["+20", "+20"]
    # The confluence table holds a different symbol set; it must not be served
    # the watchlist's answers.
    assert pw.COLUMN not in pw.attach(_df(), "Symbol", "confluence",
                                      state=state).columns


def test_a_name_with_no_history_is_answered_not_left_pending():
    state = {}
    pw.fill(["AAA"], "wl", fetch=lambda s: {"quarters": []}, state=state)
    assert pw.pending(["AAA"], "wl", state) == []
    assert state[pw.STATE_KEY]["wl"]["AAA"] == ""


def test_a_failing_fetch_does_not_raise_and_does_not_retry_forever():
    state = {}

    def boom(symbol):
        raise RuntimeError("yfinance said no")

    assert pw.fill(["AAA"], "wl", fetch=boom, state=state) == 1
    assert pw.pending(["AAA"], "wl", state) == []


def test_pending_normalises_and_dedupes():
    assert pw.pending([" aaa ", "AAA", "—", ""], "wl", {}) == ["AAA"]


def test_fill_is_idempotent():
    state = {}
    assert pw.fill(["AAA"], "wl", fetch=_fetch, state=state) == 1
    assert pw.fill(["AAA"], "wl", fetch=_fetch, state=state) == 0
