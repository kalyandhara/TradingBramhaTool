"""residual_momentum_study.py — residual score and decision rule."""
from __future__ import annotations

import numpy as np

import residual_momentum_study as st


def test_beta_is_removed():
    rng = np.random.default_rng(0)
    m = rng.normal(0.001, 0.01, 252)
    high_beta = 2.0 * m + rng.normal(0, 0.002, 252)     # rises only with the market
    alpha = 0.5 * m + 0.002 + rng.normal(0, 0.002, 252) # steady own drift
    assert st.resid_score(alpha, m) > st.resid_score(high_beta, m)


def test_skip_month_is_excluded():
    rng = np.random.default_rng(1)
    m = rng.normal(0, 0.01, 252)
    r = 0.8 * m + rng.normal(0, 0.003, 252)
    jumped = r.copy()
    jumped[-5] += 0.05                                   # a jump inside the skipped month
    # Only beta can move (the jump enters the fit); the formation sum must not
    # pick the jump up — so the scores stay close, unlike a 0.05 / 0.003 ≈ 17 sd move.
    # (measured: 5.17 -> 6.21, all of it via beta 0.808 -> 0.822)
    assert abs(st.resid_score(jumped, m) - st.resid_score(r, m)) < 2.0


def test_too_little_shared_history_is_none():
    r = np.full(252, np.nan); r[-150:] = 0.01
    assert st.resid_score(r, np.zeros(252)) is None


def test_decision_requires_all_three_conditions():
    rows = [{"date": f"d{i}", "n": 100, "ic_rs": 0.0, "ic_resid": 0.05 + 0.01 * (i % 3)} for i in range(30)]
    assert st.summarise(rows)["verdict"].startswith("RESID ADDS")
    rows = [{"date": f"d{i}", "n": 100, "ic_rs": 0.05, "ic_resid": 0.05 + 0.001 * ((-1) ** i)} for i in range(30)]
    assert st.summarise(rows)["verdict"] == "NO CHANGE"
