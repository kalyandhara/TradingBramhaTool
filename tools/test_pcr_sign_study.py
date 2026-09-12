"""Tests for the B-22r sign-convention study's machinery.

    py -3 -m pytest tools/test_pcr_sign_study.py -q

These test the STATISTICS and the DECISION RULE, not PCR. The point is that when
the study reports a null, the null came from the data rather than from a detector
that cannot see anything -- so the detector is tested on effects whose answer is
known by construction.

The decision-rule tests matter as much as the statistical ones: the pre-registration
is only binding if the code actually implements it, and "we agreed in advance" is
worth nothing if the NULL branch quietly does the same thing as the CONFIRMED one.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import pcr_sign_study as st


def _panel(n: int, factor: np.ndarray, fwd5: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=n, freq="B"),
        "factor": factor,
        "fwd5": fwd5,
    })


def test_tercile_delta_sees_a_planted_positive_effect():
    rng = np.random.default_rng(0)
    f = rng.random(300)
    y = 5 * f + rng.normal(0, 0.1, 300)          # strongly increasing in f
    delta, hi, lo, n_hi, n_lo = st.tercile_delta(f, y)
    assert delta > 2.0 and hi > lo
    assert n_hi >= 90 and n_lo >= 90


def test_tercile_delta_sees_a_planted_negative_effect():
    """The BACKWARDS branch has to be reachable, or the test can only confirm."""
    rng = np.random.default_rng(1)
    f = rng.random(300)
    y = -5 * f + rng.normal(0, 0.1, 300)
    delta, *_ = st.tercile_delta(f, y)
    assert delta < -2.0


def test_tercile_delta_is_near_zero_on_noise():
    rng = np.random.default_rng(2)
    f, y = rng.random(400), rng.normal(0, 1, 400)
    delta, *_ = st.tercile_delta(f, y)
    assert abs(delta) < 0.5


def test_bootstrap_rejects_a_real_effect_and_not_noise():
    rng = np.random.default_rng(3)
    n = 400
    f = rng.random(n)
    y_eff = 5 * f + rng.normal(0, 0.5, n)
    d_eff, *_ = st.tercile_delta(f, y_eff)
    p_eff = st.block_bootstrap_p(f, y_eff, d_eff, n=400)
    assert p_eff < 0.05, f"failed to detect a planted effect (p={p_eff})"

    y_noise = rng.normal(0, 1, n)
    d_noise, *_ = st.tercile_delta(f, y_noise)
    p_noise = st.block_bootstrap_p(f, y_noise, d_noise, n=400)
    assert p_noise > 0.05, f"called pure noise significant (p={p_noise})"


def test_bootstrap_p_is_never_zero():
    """(hits+1)/(n+1) -- a p of exactly 0 would be a claim no resample can support."""
    rng = np.random.default_rng(4)
    f = rng.random(300)
    y = 100 * f
    d, *_ = st.tercile_delta(f, y)
    p = st.block_bootstrap_p(f, y, d, n=100)
    assert p > 0


def test_bootstrap_blocks_preserve_autocorrelation():
    """Block length must exceed the horizon, or overlap is treated as independent."""
    assert st.BLOCK >= 2 * st.DECISION_HORIZON


# ── the pre-registered decision rule ────────────────────────────────────────────

def _primary(delta: float, p: float) -> dict:
    return {"delta": delta, "p_boot": p}


def test_decision_confirmed():
    v, _ = st.decide(_primary(0.8, 0.01), 300, True)
    assert v == "CONFIRMED"


def test_decision_backwards():
    v, why = st.decide(_primary(-0.8, 0.01), 300, True)
    assert v == "BACKWARDS" and "contrarian" in why


def test_decision_null_when_not_significant():
    v, why = st.decide(_primary(0.8, 0.40), 300, True)
    assert v == "NULL"
    # The consequence, not just the label: a null must cost the factor its score.
    assert "NOT_CHECKED" in why and "not deleted" in why.lower()


def test_underpowered_is_not_a_null():
    """B-58 earned this distinction at 53 events; it must not collapse into NULL."""
    v, why = st.decide(_primary(0.8, 0.40), st.MIN_SCORED_SESSIONS - 1, True)
    assert v == "UNDERPOWERED" and "Not a null" in why


def test_failed_control_invalidates_everything():
    """Even a significant-looking result is void if the harness proved blind."""
    v, _ = st.decide(_primary(0.8, 0.001), 300, False)
    assert v == "INVALID"


def test_floor_and_horizon_match_the_preregistration():
    """Guards the constants themselves -- editing them after a run voids the study."""
    assert st.DECISION_HORIZON == 5
    assert st.MIN_SCORED_SESSIONS == 200
    assert st.ALPHA == 0.05
    assert st.N_BOOT == 5_000


def test_planted_control_passes_on_its_own_construction():
    rng = np.random.default_rng(5)
    n = 300
    y = rng.normal(0, 1, n)
    panel = _panel(n, rng.random(n), y)
    out = st.control_planted(panel)
    assert out["passes"], f"the planted-effect control failed: {out}"
