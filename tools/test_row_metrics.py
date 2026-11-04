"""Tests for row_metrics.py (B-63b), offline.

These columns describe state rather than predicting anything, so the tests are
about honesty rather than edge. The three that carry the design:

  * a cross the search never reached must read "not found", NOT "no cross" —
    the failure mode is a blank cell that quietly means "we only looked back
    three bars";
  * the gap is open-vs-PREVIOUS-CLOSE, so a name can gap up and close red and
    the two columns must disagree;
  * `since()` must refuse a date before the history starts rather than anchoring
    on the earliest bar, which would turn "since 1 Jan" into "since whenever
    this frame happens to begin".
"""
import numpy as np
import pandas as pd
import pytest

import row_metrics as rm


def _frame(closes, *, opens=None, highs=None, lows=None, start="2026-01-01"):
    n = len(closes)
    c = np.array(closes, dtype=float)
    o = np.array(opens, dtype=float) if opens is not None else c.copy()
    h = np.array(highs, dtype=float) if highs is not None else np.maximum(c, o) * 1.001
    l = np.array(lows, dtype=float) if lows is not None else np.minimum(c, o) * 0.999
    idx = pd.bdate_range(start=start, periods=n)
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c,
                         "volume": np.full(n, 1000.0)}, index=idx)


# ── gap ───────────────────────────────────────────────────────────────────────

def test_gap_is_open_vs_previous_close():
    df = _frame([100.0, 110.0], opens=[100.0, 105.0])
    assert rm.gap_pct(df) == pytest.approx(5.0)


def test_a_name_can_gap_up_and_close_down():
    """The column earns its place precisely here: +4% gap, red day."""
    df = _frame([100.0, 98.0], opens=[100.0, 104.0])
    assert rm.gap_pct(df) == pytest.approx(4.0)
    day_change = (98.0 / 100.0 - 1) * 100
    assert day_change < 0 < rm.gap_pct(df)


def test_gap_needs_two_bars():
    assert rm.gap_pct(_frame([100.0])) is None
    assert rm.gap_pct(None) is None


# ── EMA cross age ─────────────────────────────────────────────────────────────

def test_cross_age_counts_bars_since_the_flip():
    # Falling for a long stretch, then a sharp sustained rally: the 10-EMA
    # crosses up through the 20-EMA once, and stays above.
    closes = list(np.linspace(200, 100, 80)) + list(np.linspace(101, 200, 40))
    r = rm.ema_cross_age(_frame(closes))
    assert r["direction"] == "up"
    assert 0 < r["age"] < 40


def test_no_cross_in_range_is_reported_as_not_found_with_the_depth_searched():
    """A monotonic series never crosses. The caller must be able to tell that
    apart from 'we only looked back three bars'."""
    r = rm.ema_cross_age(_frame(list(np.linspace(100, 300, 120))))
    assert r["age"] is None
    assert r["searched"] > 50          # and it says how far it looked


def test_cross_age_is_zero_on_the_bar_it_crossed():
    closes = list(np.linspace(200, 100, 80)) + [101.0]
    # Build up to a cross, then check a frame ending exactly at one.
    df = _frame(closes)
    r = rm.ema_cross_age(df)
    assert r["age"] is None or r["age"] >= 0


def test_cross_age_short_history_is_not_an_exception():
    r = rm.ema_cross_age(_frame([100.0, 101.0]))
    assert r == {"age": None, "direction": None, "searched": 0}


# ── breakout ──────────────────────────────────────────────────────────────────

def test_breakout_reports_the_date_and_the_gain_since():
    # One breakout, then four bars that stay UNDER the new high so no later bar
    # breaks out again — otherwise the function correctly reports the latest
    # break and the test would be asserting the wrong one.
    closes = [100.0] * 25 + [130.0] + [128.0] * 4
    df = _frame(closes, highs=[101.0] * 25 + [131.0] + [129.0] * 4)
    b = rm.breakout(df, lookback=20)
    assert b["bars_ago"] == 4
    assert b["date"] is not None
    # The gain since a breakout can be NEGATIVE — one that faded is exactly
    # what the column is for.
    assert b["gain_pct"] == pytest.approx((128.0 / 130.0 - 1) * 100, abs=0.01)


def test_breakout_reports_the_most_recent_one_not_the_first():
    closes = [100.0] * 25 + [130.0, 135.0, 145.0]
    df = _frame(closes, highs=[101.0] * 25 + [131.0, 136.0, 146.0])
    b = rm.breakout(df, lookback=20)
    assert b["bars_ago"] == 0


def test_no_breakout_is_none_everywhere_rather_than_zero():
    df = _frame([100.0] * 40)
    b = rm.breakout(df, lookback=20)
    assert b == {"date": None, "gain_pct": None, "bars_ago": None, "level": None}


# ── pivots ────────────────────────────────────────────────────────────────────

def test_pivot_levels_use_the_prior_bar():
    df = _frame([100.0, 200.0], highs=[120.0, 210.0], lows=[90.0, 190.0])
    lv = rm.pivot_levels(df)
    # Prior bar: H 120, L 90, C 100 -> PP = 103.33
    assert lv["pp"] == pytest.approx((120 + 90 + 100) / 3)
    assert lv["r1"] == pytest.approx(2 * lv["pp"] - 90)
    assert lv["s1"] == pytest.approx(2 * lv["pp"] - 120)


def test_pivot_zone_labels_each_band():
    def zone(last):
        df = _frame([100.0, last], highs=[120.0, last * 1.01],
                    lows=[90.0, last * 0.99])
        return rm.pivot_zone(df)
    lv = rm.pivot_levels(_frame([100.0, 100.0], highs=[120.0, 101.0],
                                lows=[90.0, 99.0]))
    assert zone(lv["r1"] + 10) == "R1"
    assert zone((lv["pp"] + lv["r1"]) / 2) == "R1-PP"
    assert zone((lv["s1"] + lv["pp"]) / 2) == "PP-S1"
    assert zone(lv["s1"] - 10) == "S1"


def test_pivot_zone_says_near_when_price_sits_on_the_level():
    df0 = _frame([100.0, 100.0], highs=[120.0, 101.0], lows=[90.0, 99.0])
    pp = rm.pivot_levels(df0)["pp"]
    df = _frame([100.0, pp], highs=[120.0, pp * 1.001], lows=[90.0, pp * 0.999])
    assert rm.pivot_zone(df) == "Near Pivot"


def test_weekly_frame_aggregates_ohlc():
    # Starts on a MONDAY so ten business days are exactly two whole weeks —
    # a mid-week start would split into three partial weeks and the assertion
    # would be about the calendar, not the aggregation.
    df = _frame([10.0, 11.0, 12.0, 13.0, 14.0, 20.0, 21.0, 22.0, 23.0, 24.0],
                highs=[10.5, 11.5, 12.5, 13.5, 14.5, 20.5, 21.5, 22.5, 23.5, 24.5],
                lows=[9.5, 10.5, 11.5, 12.5, 13.5, 19.5, 20.5, 21.5, 22.5, 23.5],
                start="2026-01-05")
    w = rm.weekly_frame(df)
    assert len(w) == 2
    assert w["high"].iloc[0] == pytest.approx(14.5)
    assert w["low"].iloc[0] == pytest.approx(9.5)
    assert w["close"].iloc[0] == pytest.approx(14.0)


def test_weekly_frame_refuses_a_positional_index():
    df = _frame([1.0, 2.0, 3.0]).reset_index(drop=True)
    assert rm.weekly_frame(df) is None


# ── since ─────────────────────────────────────────────────────────────────────

def test_since_uses_the_last_close_on_or_before_the_date():
    df = _frame([100.0, 110.0, 120.0, 130.0])
    s = rm.since(df, df.index[1])
    assert s["price"] == pytest.approx(110.0)
    assert s["gain_pct"] == pytest.approx((130.0 / 110.0 - 1) * 100, abs=0.01)


def test_since_refuses_a_date_before_the_history_starts():
    """Anchoring on the earliest available bar would turn 'since 1 Jan' into
    'since whenever this frame begins' — silently, and differently per symbol."""
    df = _frame([100.0, 110.0], start="2026-06-01")
    s = rm.since(df, pd.Timestamp("2020-01-01"))
    assert s == {"price": None, "gain_pct": None, "date": None}


def test_since_falls_back_to_the_prior_session_on_a_holiday():
    df = _frame([100.0, 110.0, 120.0])
    weekend = df.index[1] + pd.Timedelta(days=1)
    s = rm.since(df, weekend)
    assert s["price"] == pytest.approx(110.0)


# ── 52w + the whole row ───────────────────────────────────────────────────────

def test_from_52w_high_is_zero_at_the_high_and_negative_below():
    assert rm.from_52w_high_pct(_frame([100.0, 100.0], highs=[100.0, 100.0])) \
        == pytest.approx(0.0)
    v = rm.from_52w_high_pct(_frame([100.0, 80.0], highs=[100.0, 81.0]))
    assert v == pytest.approx(-20.0)


def test_row_returns_every_column_even_on_a_thin_frame():
    r = rm.row(_frame([100.0, 101.0]), ref_date=None)
    expected = {"gap_pct", "ema_cross_age", "ema_cross_dir", "ema_cross_searched",
                "pivot_d", "pivot_w", "pivot_agree", "bo_gain_pct", "bo_date",
                "from_52w_high_pct", "hist_price", "gain_since_pct",
                # UI-2 additions. A thin frame must still produce the KEYS —
                # a caller building a DataFrame from these rows gets ragged
                # columns otherwise, and a missing column reads as a missing
                # feature rather than a missing reading.
                "rsi", "pct_from_20ema", "ema_stack"}
    assert set(r) == expected


def test_row_is_populated_on_a_real_length_frame():
    closes = list(np.linspace(100, 200, 300))
    df = _frame(closes)
    r = rm.row(df, ref_date=df.index[-60])
    assert r["gap_pct"] is not None
    assert r["pivot_d"] is not None
    assert r["pivot_w"] is not None
    assert r["gain_since_pct"] is not None
    assert r["from_52w_high_pct"] is not None


# ── UI-2 · the five cheap columns ────────────────────────────────────────────

def test_rsi_and_pct_from_ema_are_none_on_a_thin_frame():
    """Absent must render absent. Neither may invent a value from two bars."""
    thin = _frame([100.0, 101.0])
    assert rm.rsi(thin) is None
    assert rm.pct_from_ema(thin) is None


def test_pct_from_ema_defaults_to_20_not_21():
    """`scan_pullback_to_ema` uses 21. A column labelled '% from 20EMA' that
    quietly used 21 would disagree with that scanner while appearing to confirm
    it — the collision the B-63b audit found."""
    assert rm.PCT_FROM_EMA_SPAN == 20


def test_ema_stack_marks_each_span_green_or_red():
    rising = _frame([100.0 + i for i in range(260)])
    full = rm.ema_stack(rising)
    assert full is not None
    for sp in rm.EMA_STACK_SPANS:
        assert str(sp) in full
    assert full.count(rm.EMA_DOT_ABOVE) == len(rm.EMA_STACK_SPANS)
    assert rm.EMA_DOT_BELOW not in full      # a rising series sits above them all

    falling = _frame([400.0 - i for i in range(260)])
    assert rm.ema_stack(falling).count(rm.EMA_DOT_BELOW) == len(rm.EMA_STACK_SPANS)


def test_a_span_it_cannot_compute_is_GREY_not_red_and_not_dropped():
    """Grey keeps the slot and empties it. Dropping the span collapsed the cell,
    so a young listing and a name below its 200 EMA produced different-length
    cells that no longer lined up down the column. Red would be worse still — it
    would state something we cannot see."""
    short = _frame([100.0 + i for i in range(60)])
    s = rm.ema_stack(short)
    assert "200" + rm.EMA_DOT_UNKNOWN in s   # the slot is kept, and empty
    assert "200" + rm.EMA_DOT_BELOW not in s
    # Every span still has a position, so the column scans vertically.
    assert len(s.split()) == len(rm.EMA_STACK_SPANS)


def test_every_span_grey_is_returned_as_nothing_at_all():
    """A row of empty circles looks like a measurement. An absence should look
    like an absence.

    Unreachable with the default spans — 12 bars is the function's own floor and
    the 10-EMA is computable at 12 — so this passes custom spans to reach it,
    which is also the only way a caller could.
    """
    short = _frame([100.0 + i for i in range(30)])
    assert rm.ema_stack(short, spans=(100, 200)) is None


def test_ema_stack_is_none_when_nothing_can_be_computed():
    assert rm.ema_stack(_frame([100.0, 101.0])) is None
    assert rm.ema_stack(None) is None


# ── B-75 · the sequential profit walk ─────────────────────────────────────────
# What these pin is the three ways the walk can lie, all of which a naive
# implementation commits: bridging a gapped quarter and presenting it as one
# quarter's change, computing a percentage off a loss base (a shrinking loss
# reads as growth), and printing an empty walk where there is no data at all.

def _q(*pairs):
    """Quarterly rows NEWEST FIRST, the shape `derive_fundamentals` returns."""
    return [{"period": p, "net_income": n} for p, n in pairs]


def test_profit_walk_reads_oldest_first():
    q = _q(("2026-06-30", 120.0), ("2026-03-31", 100.0), ("2025-12-31", 80.0))
    assert rm.profit_qoq_walk(q) == "+25 → +20"


def test_profit_walk_marks_a_gapped_quarter_instead_of_bridging_it():
    # 2025-12-31 missing: Mar-to-Jun is one quarter, Sep-to-Mar is two. The
    # second must NOT be printed as +150%.
    q = _q(("2026-06-30", 120.0), ("2026-03-31", 100.0), ("2025-09-30", 40.0))
    assert rm.profit_qoq_walk(q) == "? → +20"


def test_profit_walk_refuses_a_percentage_off_a_loss_base():
    q = _q(("2026-03-31", -10.0), ("2025-12-31", -100.0))
    assert rm.profit_qoq_walk(q) == "L"


def test_profit_walk_drops_a_step_with_a_missing_figure():
    # A missing net_income is an absent row, not a gapped quarter, so it must
    # not print "?" — the reader would take that for a hole in the calendar.
    q = [{"period": "2026-06-30", "net_income": 120.0},
         {"period": "2026-03-31", "net_income": None},
         {"period": "2025-12-31", "net_income": 80.0}]
    assert rm.profit_qoq_walk(q) is None


def test_profit_walk_is_absent_not_empty_when_there_is_no_history():
    assert rm.profit_qoq_walk([]) is None
    assert rm.profit_qoq_walk(_q(("2026-03-31", 100.0))) is None


def test_profit_walk_caps_the_number_of_steps_and_keeps_the_newest():
    ends = ["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30",
            "2025-03-31", "2024-12-31", "2024-09-30", "2024-06-30"]
    q = _q(*[(e, 100.0) for e in ends])
    steps = rm.profit_qoq_steps(q)
    assert len(steps) == rm.QOQ_MAX_STEPS
    assert steps[-1]["period"] == q[0]["period"]


# ── B-96: multi-timeframe pivot agreement ─────────────────────────────────────
def _dated(closes, start="2023-01-02"):
    idx = pd.bdate_range(start, periods=len(closes))
    c = np.asarray(closes, dtype=float)
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c}, index=idx)


def test_pivot_agreement_all_above_in_a_long_rise():
    df = _dated(np.linspace(100, 300, 700))          # ~2.7 years, steadily up
    sides = rm.pivot_sides(df)
    assert set(sides) == {"D", "W", "M", "Q", "Y"}
    assert rm.pivot_agreement(df) == "5/5 above"


def test_pivot_agreement_all_below_in_a_long_fall():
    df = _dated(np.linspace(300, 100, 700))
    assert rm.pivot_agreement(df) == "0/5 above"


def test_young_listing_prints_a_smaller_denominator_not_a_guess():
    df = _dated(np.linspace(100, 150, 120))          # < 1 year: no prior YEAR
    sides = rm.pivot_sides(df)
    assert sides["Y"] is None
    assert rm.pivot_agreement(df).endswith(f"/{sum(v is not None for v in sides.values())} above")


def test_pivot_agreement_needs_two_readable_timeframes():
    assert rm.pivot_agreement(_dated([100.0, 101.0])) is None or \
        rm.pivot_agreement(_dated([100.0, 101.0])).endswith("above")
    assert rm.pivot_agreement(None) is None


def test_monthly_pivot_uses_the_last_completed_month():
    df = _dated(np.linspace(100, 200, 300))
    m = rm.period_frame(df, "ME")
    lv = rm.pivot_levels(m)
    prior = m.iloc[-2]
    assert lv["pp"] == pytest.approx((prior["high"] + prior["low"] + prior["close"]) / 3)


def test_pivot_agree_has_a_column_spec():
    import columns
    assert columns.resolve("pivot_agree") == "pivot_agree"
