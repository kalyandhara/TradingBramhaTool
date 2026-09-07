"""Tests for the Shallow Flip screen (B-57), offline.

Two kinds of guarantee here, and the second matters more than the first.

The behavioural ones pin the filter: an UP flip fires only out of a shallow
correction, a deep one is rejected, and the depth is the SAME definition the
study scored with -- if the screen and the measurement that judged it drift
apart, the card's cited number stops describing the card.

The structural ones pin the honesty: no entry/stop/target, never in the
confluence pipeline, score is not conviction. B-57 measured this at no edge, and
those three are how that finding is enforced in code rather than in wording that
a later edit could soften.
"""
import numpy as np
import pandas as pd
import pytest

import opportunity_hub as oh
import scanner_templates as sc

NAME = "Shallow Flip (Renko, bounded correction)"


def _bars(closes: list[float]) -> pd.DataFrame:
    """OHLCV around a close path, with highs/lows tight enough that the peak and
    trough of a leg are the closes themselves — so the expected depth is exact."""
    c = np.array(closes, float)
    return pd.DataFrame({
        "open": c, "high": c * 1.001, "low": c * 0.999, "close": c,
        "volume": np.full(len(c), 1e6),
    })


def _path(up_to: float, down_to: float, back_to: float,
          lead: int = 60, leg: int = 40, back: int = 3) -> list[float]:
    """Rise, fall, rise -- one full flip cycle with a controllable drawdown.

    `back` is short by default so the flip lands INSIDE the shipped freshness
    window (max_bars_ago=2). Tests that reach for a wide window to make a fixture
    fire are testing the scanner outside the range it actually runs in, and the
    score's freshness term dominates there -- which is how the first draft of
    these tests managed to compare two floored scores and call it a bug.
    """
    return (list(np.linspace(100.0, up_to, lead))
            + list(np.linspace(up_to, down_to, leg))
            + list(np.linspace(down_to, back_to, back)))


# ── behaviour ────────────────────────────────────────────────────────────────

def test_a_shallow_correction_fires():
    df = _bars(_path(200.0, 185.0, 205.0))       # ~7.5% down-leg
    hit = sc.scan_shallow_flip(df)
    assert hit is not None
    assert hit["renko_dir"] == "UP"
    assert hit["correction_pct"] <= sc.SHALLOW_CORRECTION_PCT


def test_a_deep_correction_is_rejected():
    df = _bars(_path(200.0, 120.0, 210.0))       # ~40% down-leg — the owner's cap
    assert sc.scan_shallow_flip(df) is None


def test_the_cap_is_the_thing_doing_the_rejecting():
    """Same bars, only the cap changes — so the filter, not the shape, decides."""
    df = _bars(_path(200.0, 150.0, 210.0))       # ~25% down-leg
    assert sc.scan_shallow_flip(df, max_correction=10.0) is None
    assert sc.scan_shallow_flip(df, max_correction=40.0) is not None


def test_a_stale_flip_is_dropped_by_the_freshness_window():
    df = _bars(_path(200.0, 185.0, 205.0) + [205.0] * 30)
    assert sc.scan_shallow_flip(df) is None


def test_too_few_bars_returns_none_rather_than_raising():
    assert sc.scan_shallow_flip(_bars([100.0] * 20)) is None
    assert sc.scan_shallow_flip(None) is None


def test_depth_matches_the_definition_the_study_scored_with():
    """peak -> trough over the down-leg, as a percent of peak.

    The cap is raised here so the DEPTH is what is under test, not the filter --
    a 200 -> 180 leg measures just over 10% and would otherwise be rejected by
    the very threshold this assertion is trying to calibrate.
    """
    df = _bars(_path(200.0, 180.0, 210.0))
    hit = sc.scan_shallow_flip(df, max_correction=15.0)
    assert hit is not None
    # The leg runs 200 -> 180 on closes; lows sit 0.1% under, so ~10.09%.
    assert hit["correction_pct"] == pytest.approx(10.09, abs=0.25)


# ── structure: how B-57's null is enforced in code ───────────────────────────

def test_it_emits_no_trade_plan():
    df = _bars(_path(200.0, 185.0, 205.0))
    hit = sc.scan_shallow_flip(df)
    assert hit is not None
    for k in ("entry", "stop", "target", "stop_loss", "time_stop"):
        assert k not in hit, f"{k} would make an attention list read as a plan"


def test_it_can_never_become_a_confluence_vote():
    assert NAME in oh.PIPELINE_EXCLUDED


def test_it_is_registered_and_points_at_the_right_function():
    assert sc.SCANNERS[NAME]["fn"] is sc.scan_shallow_flip


def test_the_card_states_the_measured_null():
    df = _bars(_path(200.0, 185.0, 205.0))
    hit = sc.scan_shallow_flip(df)
    blob = " ".join(hit["reasons"]) + " " + " ".join(hit["tags"])
    assert "no edge" in blob.lower()
    assert "B-57" in blob
    assert "not a trigger" in blob.lower()


def test_score_falls_as_the_correction_deepens():
    """Score ranks freshness and shallowness, never conviction — so a deeper
    correction must not look 'stronger' just because it moved further."""
    shallow = sc.scan_shallow_flip(_bars(_path(200.0, 192.0, 205.0)))
    deeper = sc.scan_shallow_flip(_bars(_path(200.0, 182.0, 205.0)))
    assert shallow is not None and deeper is not None
    assert shallow["score"] > deeper["score"]


def test_a_down_flip_never_fires_this_screen():
    """It is the BUY read. A down-flip belongs to Renko Flip, which reports both."""
    df = _bars(_path(200.0, 185.0, 205.0) + list(np.linspace(205.0, 150.0, 40)))
    hit = sc.scan_shallow_flip(df)
    assert hit is None or hit["renko_dir"] == "UP"
