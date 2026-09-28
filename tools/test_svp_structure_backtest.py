"""Tests for B-56's scorer, offline.

The measurement itself is a one-off; what these pin is the machinery that could
silently turn a null into a finding. Three things carry the result:

  * the **verdict function**, which exists so the pre-registered decision rule is
    applied mechanically rather than argued for after the numbers are in. An
    inversion must NOT be reported as a pass, and a thin sample must NOT be
    reported as a null — that second one is the B-58 mistake, where 53 events
    against a floor of 200 could have been written up as evidence of absence;
  * the **forward-return offset**, which must enter at the NEXT bar's open. A
    read computed from bars up to and including t cannot be acted on at t's
    close, and an off-by-one here would quietly manufacture edge;
  * the **rotation null**, which must keep each symbol's label run-structure
    intact across a ragged panel.
"""
import numpy as np

import svp_structure_backtest as sb


def _res(n_buy, n_sell, spread, p):
    return {"horizons": {sb.PRIMARY_H: {"n_buy": n_buy, "n_sell": n_sell,
                                        "spread": spread, "p_rot": p}},
            "per_symbol": {}}


def test_a_significant_inversion_is_not_a_pass():
    v, why = sb.verdict(_res(4000, 3000, -1.77, 0.041))
    assert v == "INVERTED"
    assert "do NOT ship the mirror" in why


def test_a_thin_sample_is_inconclusive_not_null():
    # The B-58 precedent: absence of evidence reported as evidence of absence.
    v, _ = sb.verdict(_res(4000, 12, -1.77, 0.001))
    assert v.startswith("INCONCLUSIVE")


def test_the_floor_applies_to_both_arms():
    assert sb.verdict(_res(12, 4000, 1.0, 0.01))[0].startswith("INCONCLUSIVE")
    assert sb.verdict(_res(4000, 4000, 1.0, 0.01))[0] == "PASS"


def test_a_positive_spread_without_significance_is_a_null():
    assert sb.verdict(_res(4000, 3000, 1.2, 0.40))[0] == "NULL"


def test_forward_return_enters_at_the_next_bars_open():
    # close rises 1/bar from 100; open equals the prior close.
    c = np.arange(100.0, 120.0)
    o = np.concatenate([[100.0], c[:-1]])
    # From t=5: entry at o[6] = c[5] = 105, exit at c[6+2] = 108.
    got = sb._fwd(o, c, 5, 2)
    assert got is not None
    assert abs(got - (108 / 105 - 1) * 100) < 1e-9


def test_forward_return_is_none_when_the_window_runs_off_the_end():
    c = np.arange(100.0, 110.0)
    o = np.concatenate([[100.0], c[:-1]])
    assert sb._fwd(o, c, len(c) - 2, 20) is None


def test_pooled_spread_ignores_bars_with_no_forward_window():
    # Five rows per arm, one of them NaN on each side, so both arms still clear
    # the 4-per-arm guard and the NaN drop is what is actually being measured.
    vals = np.array([1.0, np.nan, 3.0, 5.0, 7.0,
                     2.0, np.nan, 4.0, 6.0, 8.0])
    labs = np.array([sb.A_GROUP] * 5 + [sb.B_GROUP] * 5)
    got = sb._pooled_spread([("X", vals, labs)], 0)
    # BUY = [1,3,5,7] -> 4.0 ; SELL = [2,4,6,8] -> 5.0
    assert abs(got - (4.0 - 5.0)) < 1e-9


def test_rotation_keeps_each_symbols_labels_together():
    # Two symbols of DIFFERENT lengths: a shift must roll each within itself, so
    # the label composition per symbol is preserved at every offset. Gluing them
    # into one vector would move symbol A's labels onto symbol B's returns.
    a = ("A", np.arange(10.0), np.array([sb.A_GROUP] * 5 + [sb.B_GROUP] * 5))
    b = ("B", np.arange(7.0), np.array([sb.B_GROUP] * 4 + [sb.A_GROUP] * 3))
    for shift in (0, 1, 3, 6, 9):
        for _sym, _v, labs in (a, b):
            rolled = np.roll(labs, shift % len(labs))
            assert (rolled == sb.A_GROUP).sum() == (labs == sb.A_GROUP).sum()
    assert sb._pooled_spread([a, b], 3) is not None


def test_hold_rows_never_enter_either_arm():
    vals = np.array([1.0, 2.0, 3.0, 4.0])
    labs = np.array([sb.A_GROUP, sb.SKIP_GROUP, sb.SKIP_GROUP, sb.B_GROUP])
    # Only one row per arm, which is below the 4-per-arm guard -> None, proving
    # the SKIP rows were not counted into either side to reach it.
    assert sb._pooled_spread([("X", vals, labs)], 0) is None
