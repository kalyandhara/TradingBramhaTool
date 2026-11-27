"""score_calibration_study.py — tercile spread, labels and the decision rule."""
from __future__ import annotations

import numpy as np

import score_calibration_study as st


def _rows(scanner, n_sym, per, slope, seed=0):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n_sym):
        for _ in range(per):
            s = rng.uniform(0, 100)
            out.append({"scanner": scanner, "symbol": f"S{i}", "score": s,
                        "fwd20": slope * s / 100 + rng.normal(0, 0.02),
                        "fwd60": rng.normal(0, 0.02)})
    return out


def test_tercile_spread():
    s = np.arange(9, dtype=float)
    y = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2], dtype=float)
    assert st.tercile_spread(s, y) == 2.0


def test_a_real_slope_ranks_and_noise_does_not():
    rows = _rows("Good", 30, 10, 0.06) + _rows("Noise", 30, 10, 0.0, seed=1)
    res = st.analyse(rows, set())
    assert res["scanners"]["Good"]["h20"]["label"] == "RANKS"
    assert res["scanners"]["Noise"]["h20"]["label"] == "NO EVIDENCE"
    assert res["qualifying"] == 2


def test_risk_scanner_direction_is_flipped():
    rows = _rows("Risky", 30, 10, -0.06)
    assert st.analyse(rows, {"Risky"})["scanners"]["Risky"]["h20"]["label"] == "RANKS"
    assert st.analyse(rows, set())["scanners"]["Risky"]["h20"]["label"] == "INVERTED"


def test_small_and_flat_scanners_are_labelled_not_tested():
    small = _rows("Small", 5, 5, 0.06)
    flat = [dict(r, score=100.0) for r in _rows("Flat", 30, 10, 0.0)]
    res = st.analyse(small + flat, set())
    assert res["scanners"]["Small"]["h20"]["label"] == "INSUFFICIENT"
    assert res["scanners"]["Flat"]["h20"]["label"] == "NO SPREAD"
    assert res["qualifying"] == 0


def test_decision_rule():
    # Seeds 11-14 are ordinary draws. Seed 3 is the most extreme of 300 noise seeds
    # (spread 1.09pp, 3.9 SE) and would make this a test of luck, not of the rule.
    rows = (_rows("Good", 30, 10, 0.06) + _rows("N1", 30, 10, 0, 11)
            + _rows("N2", 30, 10, 0, 12) + _rows("N3", 30, 10, 0, 13) + _rows("N4", 30, 10, 0, 14))
    res = st.analyse(rows, set())
    assert res["ranks_h20"] == 1 and res["decision"].startswith("FILE B-172r")


def test_a_nan_outcome_is_dropped_not_allowed_to_void_the_scanner():
    rows = _rows("Good", 30, 10, 0.06)
    rows[0]["fwd20"] = float("nan")
    lab = st.analyse(rows, set())["scanners"]["Good"]["h20"]
    assert lab["label"] == "RANKS" and lab["hits"] == 299
