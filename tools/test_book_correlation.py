"""book_correlation.py — clusters and effective number of bets (B-173)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import book_correlation as bc


def _closes(n_days=200, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2026-01-01", periods=n_days)
    m1, m2 = rng.normal(0, 0.01, n_days), rng.normal(0, 0.01, n_days)
    noise = lambda: rng.normal(0, 0.002, n_days)
    rets = {"A1": m1 + noise(), "A2": m1 + noise(), "A3": m1 + noise(),
            "B1": m2 + noise(), "B2": m2 + noise(),
            "C": rng.normal(0, 0.01, n_days)}
    return {k: pd.Series(100 * np.exp(np.cumsum(v)), index=idx) for k, v in rets.items()}


def test_clusters_find_the_two_hidden_factors():
    a = bc.analyse(_closes())
    groups = [set(c["names"].split(", ")) for c in a["clusters"]]
    assert {"A1", "A2", "A3"} in groups and {"B1", "B2"} in groups
    assert a["singletons"] == ["C"]


def test_n_eff_counts_independent_bets_not_names():
    a = bc.analyse(_closes())
    assert a["n"] == 6
    assert 2.5 < a["n_eff"] < 3.5                  # three factors, not six names


def test_n_eff_bounds():
    idx = pd.bdate_range("2026-01-01", periods=150)
    rng = np.random.default_rng(1)
    clones = rng.normal(0, 0.01, 150)
    same = {f"S{i}": pd.Series(100 * np.exp(np.cumsum(clones)), index=idx) for i in range(4)}
    assert bc.analyse(same)["n_eff"] == pytest.approx(1.0, abs=0.05)
    indep = {f"I{i}": pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 150))), index=idx)
             for i in range(4)}
    assert bc.analyse(indep)["n_eff"] > 3.3


def test_weighting_concentrated_in_one_cluster_lowers_n_eff():
    c = _closes()
    even = bc.analyse(c, weights={k: 1.0 for k in c})["n_eff_weighted"]
    piled = bc.analyse(c, weights={"A1": 5, "A2": 5, "A3": 5, "B1": 1, "B2": 1, "C": 1})["n_eff_weighted"]
    assert piled < even


def test_short_history_is_dropped_not_guessed():
    c = _closes()
    c["NEW"] = c["C"].iloc[-20:]                     # 20 sessions < 60 overlap
    a = bc.analyse(c)
    assert "NEW" in a["dropped"] and a["n"] == 6


def test_summary_line_states_it_is_not_a_forecast():
    assert "not a forecast" in bc.summary_line(bc.analyse(_closes()))
    assert bc.summary_line({"n": 0}).startswith("Correlation: not enough")
