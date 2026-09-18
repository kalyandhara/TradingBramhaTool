"""Tests for the flag & pole detector (B-92 / PR-3), offline.

The detector's own `--count` already guards the loose end: if the gates drifted
wide enough to call every pullback a flag, the hit rate would say so. What these
pin is the geometry, and above all the ONE bug the count caught:

  **The flag boundary must be formed strictly before the bar that breaks it.**
  The first version took the boundary as the max high over the whole flag
  INCLUDING the live bar, then asked whether that bar's close exceeded it — which
  a close can never do, since it cannot exceed its own bar's high. 189 patterns
  detected, `broken 0`. A test that only checked "does it detect a flag" would
  have passed.
"""
import numpy as np
import pandas as pd
import pytest

import flag_pole as fp


def _frame(closes, highs=None, lows=None, vols=None):
    c = np.asarray(closes, float)
    h = np.asarray(highs, float) if highs is not None else c * 1.005
    l = np.asarray(lows, float) if lows is not None else c * 0.995
    v = np.asarray(vols, float) if vols is not None else np.full(len(c), 1e6)
    return pd.DataFrame({"open": c, "high": h, "low": l, "close": c, "volume": v})


def _bull(flag_len=6, retrace=0.3, breakout=False, pad=120, pole=20.0, poles=10):
    """A clean bull flag & pole: flat pad, straight pole, drift down, then maybe a break."""
    base = [100.0] * pad
    up = list(np.linspace(100.0, 100.0 + pole, poles + 1))[1:]
    top = up[-1]
    low = top - pole * retrace
    flag = list(np.linspace(top, low, flag_len))
    tail = [flag[-1] + (pole * 0.9 if breakout else 0.0)]
    return _frame(base + up + flag + tail)


def _bear(flag_len=6, retrace=0.3, breakout=False, pad=120, pole=20.0, poles=10):
    base = [100.0] * pad
    dn = list(np.linspace(100.0, 100.0 - pole, poles + 1))[1:]
    bot = dn[-1]
    hi = bot + pole * retrace
    flag = list(np.linspace(bot, hi, flag_len))
    tail = [flag[-1] - (pole * 0.9 if breakout else 0.0)]
    return _frame(base + dn + flag + tail)


# ── the bug the count caught ──────────────────────────────────────────────────

def test_a_breakout_is_reachable_at_all():
    """The regression: the boundary must come from bars BEFORE the live one.

    If the flag high is computed including the current bar, `close > flag_high`
    is unsatisfiable by construction and the detector can never report a
    breakout -- which is exactly what the first `--count` showed.
    """
    g = fp.detect_flag_pole(_bull(breakout=True), "bull")
    assert g is not None
    assert g["broken"] is True


def test_an_unbroken_flag_is_a_watch_not_a_breakout():
    g = fp.detect_flag_pole(_bull(breakout=False), "bull")
    assert g is not None
    assert g["broken"] is False


def test_the_trigger_does_not_include_the_live_bar():
    """The boundary must not move under the trade when the breakout bar prints."""
    watch = fp.detect_flag_pole(_bull(breakout=False), "bull")
    broke = fp.detect_flag_pole(_bull(breakout=True), "bull")
    assert watch and broke
    assert watch["entry"] == broke["entry"], "the trigger shifted when price broke it"


# ── geometry ──────────────────────────────────────────────────────────────────

def test_the_plan_is_all_three_levels_from_the_geometry():
    g = fp.detect_flag_pole(_bull(), "bull")
    assert g is not None
    assert g["entry"] == g["flag_high"]          # break of the flag boundary
    assert g["stop"] == g["flag_low"]            # the FAR boundary
    # Target = the pole height projected from the trigger.
    pole = g["pole_high"] - g["pole_low"]
    assert abs(g["target"] - (g["entry"] + pole)) < 0.05


def test_the_bear_plan_mirrors_it():
    g = fp.detect_flag_pole(_bear(), "bear")
    assert g is not None
    assert g["entry"] == g["flag_low"]
    assert g["stop"] == g["flag_high"]
    pole = g["pole_high"] - g["pole_low"]
    assert abs(g["target"] - (g["entry"] - pole)) < 0.05


def test_a_stop_on_the_far_side_makes_risk_positive():
    for d, frame in (("bull", _bull()), ("bear", _bear())):
        g = fp.detect_flag_pole(frame, d)
        assert g is not None
        assert abs(g["entry"] - g["stop"]) > 0
        assert g["rr"] and g["rr"] > 0


# ── the gates ─────────────────────────────────────────────────────────────────

def test_a_pole_below_the_atr_floor_is_not_a_pole():
    # A 1-unit drift over 10 bars on a frame whose ATR is ~1 is ordinary movement.
    assert fp.detect_flag_pole(_bull(pole=1.0), "bull") is None


def test_a_flag_retracing_past_the_cap_is_rejected():
    assert fp.detect_flag_pole(_bull(retrace=0.80), "bull") is None


def test_a_flag_that_is_too_long_is_a_base_not_a_pause():
    assert fp.detect_flag_pole(_bull(flag_len=fp.FLAG_MAX_BARS + 8), "bull") is None


def test_a_flag_body_making_a_new_high_is_not_a_flag():
    # Continuation already under way: the consolidation exceeded the pole high
    # before any breakout bar, so there is no pause to trade.
    f = _bull(breakout=False)
    c = f["close"].to_numpy(float).copy()
    c[-4] = c.max() + 5.0                       # inside the flag body
    frame = _frame(c)
    assert fp.detect_flag_pole(frame, "bull") is None


def test_a_choppy_thrust_is_not_a_pole():
    """Net move alone is not a pole -- a V-shaped swing would qualify on it.

    The monotonicity gate is what separates a thrust from a round trip.
    """
    base = [100.0] * 120
    zig = []
    v = 100.0
    for i in range(14):                         # net up, but half the steps down
        v += 4.0 if i % 2 == 0 else -2.0
        zig.append(v)
    flag = list(np.linspace(zig[-1], zig[-1] - 3, 6))
    g = fp.detect_flag_pole(_frame(base + zig + flag + [flag[-1]]), "bull")
    if g is not None:
        assert g["pole_monotonicity"] >= 0.60


# ── reporting, not gating ─────────────────────────────────────────────────────

def test_rising_flag_volume_is_reported_not_rejected():
    """HTF rejects a rising-volume flag; this one measures it instead.

    Enforcing it is what made HTF too rare to score, so the field exists for a
    later test to ask whether it matters.
    """
    f = _bull()
    v = np.full(len(f), 1e6)
    v[-8:] = 5e6                                # flag volume far ABOVE the pole
    frame = _frame(f["close"].to_numpy(float), vols=v)
    g = fp.detect_flag_pole(frame, "bull")
    assert g is not None, "a rising-volume flag must still be detected"
    assert g["vol_contract"] is not None and g["vol_contract"] < 0


def test_volume_absent_reports_none_rather_than_zero():
    f = _bull()
    frame = f.drop(columns=["volume"])
    g = fp.detect_flag_pole(frame, "bull")
    assert g is not None
    assert g["vol_contract"] is None


# ── contract ──────────────────────────────────────────────────────────────────

def test_a_short_frame_returns_none():
    assert fp.detect_flag_pole(_frame([100.0] * 20), "bull") is None


def test_an_unknown_direction_raises():
    with pytest.raises(ValueError):
        fp.detect_flag_pole(_bull(), "sideways")


def test_indices_point_into_the_passed_frame():
    frame = _bull()
    g = fp.detect_flag_pole(frame, "bull")
    assert g is not None
    for k in ("pole_start", "pole_end", "flag_start", "flag_end"):
        assert 0 <= g[k] < len(frame)
    assert g["pole_start"] < g["pole_end"] < g["flag_start"] <= g["flag_end"]


# ── the registered cards ──────────────────────────────────────────────────────

def test_both_cards_are_registered_and_emit_a_full_plan():
    import scanner_plans as spl
    import scanner_templates as sc
    for name, frame in (("Flag & Pole", _bull(breakout=True)),
                        ("Inverted Flag & Pole", _bear(breakout=True))):
        assert name in sc.SCANNERS
        hit = sc.SCANNERS[name]["fn"](frame)
        assert hit, f"{name} did not fire on its own fixture"
        assert spl.has_plan(hit), f"{name} fired without a full entry/stop/target"


def test_the_card_says_the_target_is_a_projection():
    hit = fp.scan_flag_pole(_bull(breakout=True))
    assert hit
    blob = " ".join(hit["reasons"])
    assert "PROJECTED" in blob and "not a forecast" in blob
    assert "UNMEASURED" in blob


def test_the_bear_card_is_scoped_as_exit_not_entry():
    assert "EXIT / AVOID" in (fp.scan_inverted_flag_pole.__doc__ or "")


def test_a_frame_with_no_pattern_returns_none_from_both_cards():
    flat = _frame([100.0] * 160)
    assert fp.scan_flag_pole(flat) is None
    assert fp.scan_inverted_flag_pole(flat) is None
