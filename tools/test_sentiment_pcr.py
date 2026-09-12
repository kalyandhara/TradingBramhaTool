"""test_sentiment_pcr.py — factor 5 of the sentiment index (backlog B-22).

Everything here exercises `pcr_factor`, the PURE half of the wiring: it takes a
level, a slope and a stored baseline and returns a factor. That split is the
point — the fetch half is `pcr.load()`, which is already covered by the
OI-Momentum surface that consumes it, and a test that needed the network would
not be run.

The behaviour these pin down, in order of how badly it would hurt to lose it:

  1. Below the history floor the factor is NOT_CHECKED, not 0.5. A neutral-
     looking number from an unmeasurable input is the exact failure the sector
     component was rebuilt to avoid.
  2. The composite EXCLUDES a NOT_CHECKED factor and renormalises, so wiring
     factor 5 does not move today's score.
  3. The percentile is taken against PRIOR sessions only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sentiment_index as si


def _hist(pcrs, chgs=None) -> pd.DataFrame:
    n = len(pcrs)
    return pd.DataFrame({
        "reading_date": [f"2026-01-{i + 1:02d}" for i in range(n)],
        "pcr": pcrs,
        "pcr_chg": chgs if chgs is not None else [None] * n,
    })


# ── The history floor ────────────────────────────────────────────────────────

def test_below_floor_is_not_checked_not_neutral():
    out = si.pcr_factor(1.05, 0.02, _hist([1.0] * (si.MIN_PCR_HISTORY - 1)))
    assert out["state"] == si.NOT_CHECKED
    assert out["factor"] is None
    assert out["score"] == 0.0
    # The level is still REPORTED — it just is not scored.
    assert out["pcr"] == 1.05


def test_empty_history_is_not_checked():
    out = si.pcr_factor(1.05, None, _hist([]))
    assert out["state"] == si.NOT_CHECKED
    assert out["n_history"] == 0


def test_missing_pcr_is_not_checked():
    out = si.pcr_factor(None, None, _hist([1.0] * 100))
    assert out["state"] == si.NOT_CHECKED
    assert out["factor"] is None


def test_exactly_at_floor_computes_the_factor_but_does_not_score_it():
    """At the floor the calibration runs; since B-22r measured the sign as a NULL
    it is reported and EXCLUDED, so the state stays NOT_CHECKED and score is 0."""
    out = si.pcr_factor(1.5, None, _hist([1.0] * si.MIN_PCR_HISTORY))
    assert out["factor"] == 1.0
    assert out["state"] == si.NOT_CHECKED
    assert out["score"] == 0.0
    assert "NOT SCORED" in out["reading"]


# ── The calibration itself ───────────────────────────────────────────────────

def test_level_only_when_no_slope_history():
    """No stored pcr_chg → level carries the whole factor, and the reading says so."""
    out = si.pcr_factor(1.5, 0.05, _hist([1.0] * 100))
    assert out["slope_pct"] is None
    assert out["factor"] == 1.0                      # above every stored session
    # `blend` is only set on the scoring path, which the B-22r null closed; the
    # level-only FALLBACK is what this test is about and it still holds.
    assert out["slope_pct"] is None


def test_blend_weights_level_and_slope():
    # 100 sessions: pcr 0.00..0.99, chg 0.00..0.99. Today sits at the top of the
    # level distribution and the bottom of the slope one.
    h = _hist([i / 100 for i in range(100)], [i / 100 for i in range(100)])
    out = si.pcr_factor(0.995, -1.0, h)
    assert out["level_pct"] == 100.0
    assert out["slope_pct"] == 0.0
    assert out["factor"] == pytest.approx(si.PCR_LEVEL_SHARE)
    # The 70/30 blend is still computed and still correct; it just no longer votes.
    assert out["score"] == 0.0


def test_low_pcr_scores_low_under_the_stated_convention():
    """Documents the SIGN, which is a guess (see the module docstring and B-44r).

    If a measurement ever flips the convention, this is the test that should
    fail — that is what it is for.
    """
    h = _hist([1.0] * 100)
    assert si.PCR_SIGN_CONVENTION == "trend_following"
    assert si.pcr_factor(0.5, None, h)["factor"] == 0.0
    assert si.pcr_factor(1.5, None, h)["factor"] == 1.0


def test_factor_is_bounded():
    h = _hist([i / 100 for i in range(100)], [i / 100 for i in range(100)])
    for pcr in (-5.0, 0.0, 0.5, 50.0):
        f = si.pcr_factor(pcr, 99.0, h)["factor"]
        assert 0.0 <= f <= 1.0


def test_convention_verdict_rides_in_every_branch():
    """The measurement must survive persistence, on every path.

    Before B-22r this asserted `convention_measured is False`. It is now True and
    the VERDICT is the thing that matters -- two separate facts, because a flag
    that only says "measured" is how a null gets read as a pass.
    """
    for out in (si.pcr_factor(1.05, 0.02, _hist([1.0] * 5)),
                si.pcr_factor(1.05, 0.02, _hist([1.0] * 100)),
                si.pcr_factor(None, None, _hist([]))):
        assert out["convention_measured"] is True
        assert out["sign_verdict"] == "null"
        assert out["scores"] is False
        assert out["sign_convention"] == si.PCR_SIGN_CONVENTION


def test_the_null_gate_is_what_zeroes_the_score():
    """Guards the gate itself: if PCR_SCORES is ever flipped back without a new
    pre-registered test, this is the test that should make someone explain why."""
    assert si.PCR_SCORES is False, (
        "factor 5 scores again -- that requires a NEW pre-registered study that "
        "finds signal, not a re-reading of B-22r")


# ── The percentile helper ────────────────────────────────────────────────────

def test_pct_rank_ignores_none_and_nan():
    assert si._pct_rank(0.5, [0.0, None, float("nan"), 1.0]) == 50.0


def test_pct_rank_returns_none_on_empty_sample():
    assert si._pct_rank(0.5, [None, float("nan")]) is None


# ── Weights and the composite's exclusion path ───────────────────────────────

def test_weights_sum_to_one_hundred():
    assert si.W_TOTAL == 100
    assert (si.W_ADV_DECL, si.W_SECTOR, si.W_REGIME, si.W_PMAX_1H, si.W_PCR) == \
        (25, 20, 20, 15, 20)


def test_not_checked_factor_does_not_move_the_score(monkeypatch):
    """The whole claim of this commit: wiring factor 5 changes nothing until the
    baseline exists. Four factors at 0.8 must still score 80, not 64."""
    def fake(weight_key):
        return lambda *a, **k: {"reading": "stub", "factor": 0.8,
                                "score": 0.8 * weight_key}

    monkeypatch.setattr(si, "_advance_decline", fake(si.W_ADV_DECL))
    monkeypatch.setattr(si, "_sector_perf", fake(si.W_SECTOR))
    monkeypatch.setattr(si, "_regime_sma200", fake(si.W_REGIME))
    monkeypatch.setattr(si, "_pmax_direction_nifty_1h", fake(si.W_PMAX_1H))
    monkeypatch.setattr(si, "_pcr_nifty", lambda *a, **k: {
        "state": si.NOT_CHECKED, "factor": None, "score": 0.0,
        "reading": "NOT CHECKED — no baseline yet"})

    r = si.compute_sentiment(persist=False)
    assert r["excluded"] == ["pcr_nifty"]
    assert r["weight_measured"] == 80
    assert r["weight_total"] == 100
    assert r["score"] == pytest.approx(80.0, abs=0.01)
    assert r["band"] == "Strong Buy"
    assert r["inputs"]["pcr_nifty"]["weight"] == si.W_PCR


def test_scored_factor_enters_the_composite(monkeypatch):
    def fake(weight_key, factor):
        return lambda *a, **k: {"reading": "stub", "factor": factor,
                                "score": factor * weight_key}

    monkeypatch.setattr(si, "_advance_decline", fake(si.W_ADV_DECL, 1.0))
    monkeypatch.setattr(si, "_sector_perf", fake(si.W_SECTOR, 1.0))
    monkeypatch.setattr(si, "_regime_sma200", fake(si.W_REGIME, 1.0))
    monkeypatch.setattr(si, "_pmax_direction_nifty_1h", fake(si.W_PMAX_1H, 1.0))
    monkeypatch.setattr(si, "_pcr_nifty", fake(si.W_PCR, 0.0))

    r = si.compute_sentiment(persist=False)
    assert r["excluded"] == []
    assert r["weight_measured"] == 100
    # PCR at zero costs exactly its own weight — no renormalisation.
    assert r["score"] == pytest.approx(80.0, abs=0.01)
