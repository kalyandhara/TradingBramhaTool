"""Tests for B-8's stop-policy study, offline.

The result of this study turns on two things a bug could silently invert, so
those are what these pin:

  * the **no-stop arm must actually have no stop** — if `stop=None` were treated
    as a stop at zero, or skipped, the Connors side of the contradiction would
    never get a fair run and the shipped stop would win by default;
  * the **conservative tie-break** — when one bar spans both stop and target, the
    stop fills first. Crediting the target instead would flatter every stopped
    arm in exactly the comparison this study exists to make.

The metric is realised per cent, never R. That choice is argued in the module
docstring and pinned here by a test that would fail if a stop's width changed a
trade's reported return when the trade never touched the stop.
"""
import numpy as np
import pandas as pd

import mean_reversion_stop_study as ms


class _NoCost:
    def round_trip_pct(self, a, b):
        return 0.0


def _frame(highs, lows, closes):
    n = len(closes)
    return pd.DataFrame({"open": closes, "high": highs, "low": lows,
                         "close": closes, "volume": np.full(n, 1e6)})


def test_the_no_stop_arm_runs_to_the_time_stop():
    # Price dives then recovers: a stop would cut it, no stop rides to the end.
    df = _frame([100, 95, 90, 100, 105], [100, 80, 70, 95, 100],
                [100, 85, 75, 98, 104])
    r = ms._run_one(df, 0, 100.0, None, target=999.0, time_stop=4, cm=_NoCost())
    assert r["outcome"] == "time"
    assert abs(r["pct"] - 4.0) < 1e-9          # exits at close 104 from 100


def test_a_stop_cuts_the_same_trade():
    df = _frame([100, 95, 90, 100, 105], [100, 80, 70, 95, 100],
                [100, 85, 75, 98, 104])
    r = ms._run_one(df, 0, 100.0, 90.0, target=999.0, time_stop=4, cm=_NoCost())
    assert r["outcome"] == "stop"
    assert abs(r["pct"] - (-10.0)) < 1e-9


def test_a_bar_spanning_both_fills_the_stop_first():
    # One bar reaches the target AND the stop. The pessimistic assumption is the
    # only honest one from daily bars.
    df = _frame([120], [80], [100])
    r = ms._run_one(df, 0, 100.0, 90.0, target=110.0, time_stop=5, cm=_NoCost())
    assert r["outcome"] == "stop"


def test_a_stop_that_is_never_touched_does_not_change_the_return():
    # The metric is realised per cent, not R: a wider stop that never fills must
    # report exactly what the no-stop arm reports. Under R it would not.
    df = _frame([100, 102, 104], [99, 101, 103], [100, 102, 104])
    none = ms._run_one(df, 0, 100.0, None, 999.0, 2, _NoCost())
    wide = ms._run_one(df, 0, 100.0, 50.0, 999.0, 2, _NoCost())
    tight = ms._run_one(df, 0, 100.0, 98.0, 999.0, 2, _NoCost())
    assert none["pct"] == wide["pct"] == tight["pct"]


def test_atr_is_wilder_and_starts_after_its_lookback():
    n = 40
    df = _frame(np.full(n, 101.0), np.full(n, 99.0), np.full(n, 100.0))
    a = ms._atr(df, 14)
    assert np.isnan(a[12])
    # Constant 2-wide bars -> ATR converges to 2 (the first TR uses close[0] as
    # the previous close, which is inside that range).
    assert abs(a[-1] - 2.0) < 1e-6


def test_verdict_calls_connors_when_stops_significantly_cost_return():
    s = {"n": 400, "arms": {"none": {}}, "paired": {
        "shipped": {"diff": -1.44, "p": 0.0009, "n": 138, "t": -3.4}}}
    v, why = ms.verdict(s)
    assert v == "CONNORS"
    assert "PROVISIONAL" not in v
    assert "COST return" in why


def test_a_thin_sample_is_labelled_provisional():
    s = {"n": 145, "arms": {"none": {}}, "paired": {
        "shipped": {"diff": -1.44, "p": 0.0009, "n": 138, "t": -3.4}}}
    v, _ = ms.verdict(s)
    assert v.startswith("CONNORS")
    assert "PROVISIONAL" in v and str(ms.FLOOR) in v


def test_no_significant_difference_is_not_settled():
    s = {"n": 400, "arms": {"none": {}}, "paired": {
        "shipped": {"diff": -0.2, "p": 0.72, "n": 69, "t": -0.36}}}
    v, why = ms.verdict(s)
    assert v.startswith("NOT SETTLED")
    assert "RISK argument" in why
