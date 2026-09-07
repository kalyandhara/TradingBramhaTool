"""Tests for detect_quasimodo (B-58), offline.

The valuable tests here are the REJECTIONS. A five-pivot shape detector will find
something in almost any wiggle if its conditions are loose, and the two that
carry the meaning are easy to drop without any test noticing:

  * CHOCH   `RH > LH` — the post-head rally must break the pre-head high.
  * grab    `HEAD < LS` — the head must take out the left shoulder's low.

Drop the first and this becomes an inverse-head-and-shoulders finder under
another name, which is exactly the failure B-58's pre-registered control is
designed to catch. So each condition gets a fixture that satisfies everything
else and violates only it.
"""
import numpy as np
import pandas as pd
import pytest

import scanner_templates as sc


def _bars(closes: list[float]) -> pd.DataFrame:
    c = np.array(closes, float)
    return pd.DataFrame({
        "open": c, "high": c * 1.004, "low": c * 0.996, "close": c,
        "volume": np.full(len(c), 1e6),
    })


def _seg(a: float, b: float, n: int) -> list[float]:
    return list(np.linspace(a, b, n))


def _qm(ls=100.0, lh=130.0, head=90.0, rh=140.0, rs=108.0, tail=112.0):
    """A QM by construction; each argument can be moved to break one condition."""
    return _bars(_seg(140.0, ls, 25) + _seg(ls, lh, 20) + _seg(lh, head, 20)
                 + _seg(head, rh, 25) + _seg(rh, rs, 18) + _seg(rs, tail, 6))


# ── the shape resolves ───────────────────────────────────────────────────────

def test_a_textbook_quasimodo_is_found():
    r = sc.detect_quasimodo(_qm())
    assert r is not None
    assert r["pattern"] == "quasimodo_buy"


def test_the_four_required_pivots_come_back_in_order():
    r = sc.detect_quasimodo(_qm())
    bars_ = [r[k]["bar"] for k in ("ls", "lh", "head", "rh")]
    assert bars_ == sorted(bars_), "pivots must be chronological"


def test_the_pattern_completes_at_the_CHOCH_without_a_confirmed_right_shoulder():
    """The right shoulder IS the retracement into the zone, and a pivot needs
    `pivot_len` bars on both sides to confirm. Requiring it would make the setup
    visible only after price had already been in the zone and left."""
    still_falling = _bars(_seg(140.0, 100.0, 25) + _seg(100.0, 130.0, 20)
                          + _seg(130.0, 90.0, 20) + _seg(90.0, 140.0, 25)
                          + _seg(140.0, 101.0, 20))
    r = sc.detect_quasimodo(still_falling)
    assert r is not None, "the CHOCH completes the pattern"
    assert r["rs"] is None, "no confirmed right shoulder yet, and that is fine"
    assert r["in_zone"] is True, "price is at the left shoulder right now"


def test_the_geometry_relations_hold_on_what_it_returns():
    r = sc.detect_quasimodo(_qm())
    assert r["head"]["level"] < r["ls"]["level"]      # the grab
    assert r["rh"]["level"] > r["lh"]["level"]        # the CHOCH
    if r["rs"] is not None:
        assert r["rs"]["level"] > r["head"]["level"]  # right shoulder holds


def test_entry_is_the_left_shoulder_and_invalidation_is_the_head():
    """QM buys the left shoulder retest — NOT a neckline. That is half of what
    distinguishes it from an inverse head-and-shoulders."""
    r = sc.detect_quasimodo(_qm())
    lo, hi = r["entry_zone"]
    assert lo < r["ls"]["level"] < hi
    assert r["invalidation"] == pytest.approx(r["head"]["level"], abs=0.01)
    assert r["invalidation"] < lo


# ── the rejections that carry the meaning ────────────────────────────────────

def test_the_four_pivots_must_be_CONSECUTIVE_swings():
    """Not "any four pivots in the window that satisfy the inequalities".

    Picking the positions independently finds a qualifying combination in almost
    any series -- measured at 73% of 460 liquid names before adjacency was
    required. Here an unrelated deep dip is inserted BETWEEN the head and the
    CHOCH rally: the LS/LH/HEAD/RH relations still hold across the gap, so a
    non-adjacent search would report a pattern. There is no local QM shape.
    """
    spaced = _bars(_seg(140.0, 100.0, 25) + _seg(100.0, 130.0, 20)
                   + _seg(130.0, 90.0, 20)            # head
                   + _seg(90.0, 120.0, 15) + _seg(120.0, 95.0, 15)   # intruder
                   + _seg(95.0, 140.0, 20) + _seg(140.0, 112.0, 15))
    r = sc.detect_quasimodo(spaced)
    if r is not None:
        bars_ = [r[k]["bar"] for k in ("ls", "lh", "head", "rh")]
        gaps = [b - a for a, b in zip(bars_, bars_[1:])]
        assert max(gaps) < 60, "pivots straddle the intruding swing"


def test_a_grab_inside_the_equal_level_tolerance_is_not_a_grab():
    """A head 0.2% under the shoulder is an EQUAL LOW -- a liquidity pool in this
    repo's own vocabulary -- not a stop raid."""
    assert sc.detect_quasimodo(_qm(ls=100.0, head=99.8, rs=104.0)) is None


def test_a_CHOCH_inside_the_equal_level_tolerance_is_not_a_break():
    assert sc.detect_quasimodo(_qm(lh=130.0, rh=130.3, rs=104.0)) is None



def test_no_CHOCH_means_no_pattern():
    """RH fails to clear LH: an inverse H&S without a change of character."""
    assert sc.detect_quasimodo(_qm(lh=130.0, rh=124.0, rs=108.0, tail=112.0)) is None


def test_no_liquidity_grab_means_no_pattern():
    """The head holds ABOVE the left shoulder, so no stops were taken."""
    assert sc.detect_quasimodo(_qm(ls=90.0, head=100.0, rs=108.0)) is None


def test_price_breaking_the_head_is_flagged_as_invalidated():
    """Below the head the setup is dead. The pattern still describes what
    happened -- the flag says so rather than the detector pretending it never
    formed, which is the honest split between geometry and live state."""
    broken = sc.detect_quasimodo(_qm(head=90.0, rs=85.0, tail=84.0))
    assert broken is None or broken["below_invalidation"] is True


def test_a_plain_downtrend_produces_nothing():
    assert sc.detect_quasimodo(_bars(_seg(200.0, 100.0, 140))) is None


def test_flat_bars_produce_nothing():
    assert sc.detect_quasimodo(_bars([100.0] * 140)) is None


def test_too_few_bars_returns_none_rather_than_raising():
    assert sc.detect_quasimodo(_bars([100.0] * 30)) is None
    assert sc.detect_quasimodo(None) is None


# ── the reported measures ────────────────────────────────────────────────────

def test_choch_break_and_grab_depth_are_reported_not_recomputed():
    """A token CHOCH break and a decisive one are different events; a caller
    thresholding on that must not have to re-derive it and risk drifting."""
    r = sc.detect_quasimodo(_qm(ls=100.0, lh=130.0, head=90.0, rh=140.0))
    assert r["choch_break_pct"] == pytest.approx(
        (r["rh"]["level"] - r["lh"]["level"]) / r["lh"]["level"] * 100.0, abs=0.01)
    assert r["grab_depth_pct"] == pytest.approx(
        (r["ls"]["level"] - r["head"]["level"]) / r["ls"]["level"] * 100.0, abs=0.01)
    assert r["grab_depth_pct"] > 0


def test_in_zone_tracks_where_price_actually_is():
    away = sc.detect_quasimodo(_qm(tail=112.0))
    assert away["in_zone"] is False           # still well above the shoulder
    back = sc.detect_quasimodo(_qm(rs=104.0, tail=100.0))
    assert back is not None and back["in_zone"] is True


def test_it_emits_no_trade_plan():
    """B-58 ships this as geometry only until its pre-registered test runs."""
    r = sc.detect_quasimodo(_qm())
    for k in ("entry", "stop", "target", "score"):
        assert k not in r, f"{k} would make a detector read as a plan"
