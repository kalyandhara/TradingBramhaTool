"""Tests for B-9's value-area traverse study, offline.

Three things in this study could turn a falsification into a confirmation, and
they are what these pin:

  * the **30-minute aggregation must not bridge the overnight gap**. Resampling
    the whole frame would glue 15:15 to the next morning's 09:15 into one "bar",
    which is not a 30-minute bar and would invent value-area crossings that never
    happened;
  * a **traverse must reach the FAR boundary**. Counting a return to the side it
    entered from would make the rule unfalsifiable, which is the single easiest
    way to accidentally confirm a vendor claim;
  * the **claim and the lift are separate questions**. 80% is decided by one
    proportion's confidence interval; "worse than the base rate" needs its own
    test and must not ride in on the first one's significance.
"""
import numpy as np
import pandas as pd

import value_area_traverse_study as va


def _intraday(prices_by_day, start_hour=9, start_min=15, freq="15min"):
    """Build a multi-session 15-minute frame from {date: [closes]}."""
    frames = []
    for day, closes in prices_by_day.items():
        idx = pd.date_range(f"{day} {start_hour:02d}:{start_min:02d}",
                            periods=len(closes), freq=freq, tz="Asia/Kolkata")
        c = np.array(closes, float)
        frames.append(pd.DataFrame(
            {"open": c, "high": c + 0.5, "low": c - 0.5, "close": c,
             "volume": np.full(len(c), 1000.0)}, index=idx))
    out = pd.concat(frames)
    out.index.name = "ts"
    return out


def test_thirty_minute_bars_never_bridge_the_overnight_gap():
    df = _intraday({"2026-01-01": [100, 101, 102, 103],
                    "2026-01-02": [200, 201, 202, 203]})
    g = va.to_30m(df)
    # Four 15m bars per session -> two 30m bars per session, four in total, and
    # no bar may mix a 100-ish close with a 200-ish one.
    assert len(g) == 4
    for _ts, row in g.iterrows():
        assert row["high"] - row["low"] < 50


def test_sessions_are_split_by_date_and_ordered():
    df = _intraday({"2026-01-02": [10, 11, 12, 13],
                    "2026-01-01": [20, 21, 22, 23]})
    days = va.sessions(df)
    assert len(days) == 2
    assert days[0].index[0].date() < days[1].index[0].date()


def _session(closes):
    return _intraday({"2026-01-02": closes})


def test_a_return_to_the_entry_side_is_not_a_traverse():
    # Band 95-105. Price comes from BELOW, holds two bars inside, then falls back
    # out through the low without ever reaching 105. Failed setup, not a
    # traverse — and counting it would make the rule unfalsifiable.
    r = va.evaluate_session(_session([90, 90, 100, 100, 92, 90, 90]), 95.0, 105.0)
    assert r["armed"] and r["side"] == "below"
    assert r["traversed"] is False


def test_reaching_the_far_boundary_is_a_traverse():
    r = va.evaluate_session(_session([90, 90, 100, 100, 104, 106, 106]), 95.0, 105.0)
    assert r["armed"] and r["side"] == "below"
    assert r["traversed"] is True


def test_entering_from_above_requires_the_low_side():
    # Mirror case: comes from ABOVE, so the far boundary is the LOW.
    r = va.evaluate_session(_session([120, 120, 100, 100, 96, 94, 94]), 95.0, 105.0)
    assert r["armed"] and r["side"] == "above"
    assert r["traversed"] is True
    r2 = va.evaluate_session(_session([120, 120, 100, 100, 104, 120, 120]), 95.0, 105.0)
    assert r2["side"] == "above" and r2["traversed"] is False


def test_one_bar_inside_does_not_arm_the_setup():
    # The rule requires TWO consecutive closes inside. One touch is not a hold.
    r = va.evaluate_session(_session([90, 100, 90, 100, 90, 90, 90]), 95.0, 105.0)
    assert r["armed"] is False
    assert r["traversed"] is None


def test_a_session_opening_inside_the_band_never_arms():
    # There is no "entry" without a prior close outside, so `side` is unknown and
    # the setup must not fire. Arming here would score sessions that simply
    # started in value as if they had returned to it.
    r = va.evaluate_session(_session([100, 100, 101, 100, 106, 106]), 95.0, 105.0)
    assert r["armed"] is False


def test_the_control_is_independent_of_the_hold():
    # Never arms (no two consecutive inside closes), but the session does cross
    # the band end to end — the control must still record that. Bars are built
    # wide enough to overlap the band, as real ones would.
    df = _session([90, 100, 90, 100, 106])
    df["high"] = df["close"] + 8
    df["low"] = df["close"] - 8
    r = va.evaluate_session(df, 95.0, 105.0)
    assert r["armed"] is False
    assert r["ctrl_traverse"] is True
    assert r["touched"] is True


def test_the_claim_is_falsified_when_eighty_is_outside_the_interval():
    s = {"n_armed": 128, "n_hits": 52, "rate": 40.6,
         "ci": va._wilson(52, 128), "base": 48.7, "lift": -8.1,
         "lift_p": 0.114}
    tag, why = va.verdict(s)
    assert tag == "CLAIM FALSIFIED"
    assert "outside that interval" in why


def test_a_negative_lift_that_is_not_significant_is_not_claimed():
    s = {"n_armed": 128, "n_hits": 52, "rate": 40.6,
         "ci": va._wilson(52, 128), "base": 48.7, "lift": -8.1,
         "lift_p": 0.114}
    _tag, why = va.verdict(s)
    assert "UNDERPERFORMS" not in why
    assert "no claim either way" in why


def test_a_significant_negative_lift_is_stated():
    s = {"n_armed": 400, "n_hits": 150, "rate": 37.5,
         "ci": va._wilson(150, 400), "base": 50.0, "lift": -12.5,
         "lift_p": 0.001}
    _tag, why = va.verdict(s)
    assert "UNDERPERFORMS" in why


def test_a_thin_sample_is_inconclusive():
    s = {"n_armed": 12, "n_hits": 5, "rate": 41.7, "ci": va._wilson(5, 12),
         "base": 48.0, "lift": -6.3, "lift_p": 0.5}
    tag, _ = va.verdict(s)
    assert tag.startswith("INCONCLUSIVE")


def test_wilson_stays_inside_zero_to_one_hundred():
    lo, hi = va._wilson(0, 5)
    assert lo >= 0.0 and hi <= 100.0
    lo, hi = va._wilson(5, 5)
    assert lo >= 0.0 and hi <= 100.0


def test_wilson_brackets_the_point_estimate():
    lo, hi = va._wilson(52, 128)
    assert lo < 100 * 52 / 128 < hi
