"""ml_cross_section_study.py — B-177 feature ranking, purge/embargo and decision rule."""
from __future__ import annotations

import numpy as np
import pandas as pd

import ml_cross_section_study as st


def test_ranks_fill_missing_with_half_and_drop_sparse_names():
    raw = pd.DataFrame({f: [1.0, 2.0, 3.0] for f in st.FEATURES}, index=["A", "B", "C"])
    raw.loc["A", "beta"] = np.nan
    raw.loc["C", ["beta", "resid", "rs"]] = np.nan          # 5 of 8 -> dropped
    X = st.rank_features(raw)
    assert list(X.index) == ["A", "B"] and X.loc["A", "beta"] == 0.5


def _dates(n, signal):
    rng = np.random.default_rng(0)
    out = []
    for i in range(n):
        X = pd.DataFrame(rng.random((60, len(st.FEATURES))), columns=st.FEATURES,
                         index=[f"S{k}" for k in range(60)])
        y = pd.Series(signal * X["r21"].to_numpy() + rng.normal(0, 1, 60), index=X.index) / 100
        px = pd.Series(100.0, index=X.index)
        out.append({"date": f"2020-{i:04d}", "X": X, "y": y, "entry": px, "exit": px * (1 + y)})
    return out


def test_never_trains_on_the_purged_or_embargoed_dates(monkeypatch):
    seen = []
    real = pd.concat

    def spy(objs, *a, **k):
        objs = list(objs)
        seen.append(len(objs))
        return real(objs, *a, **k)
    monkeypatch.setattr(st.pd, "concat", spy)
    rows = st.walk_forward(_dates(st.MIN_TRAIN + st.GAP + 1, 0.0))
    # first test date t = MIN_TRAIN + GAP - 1 trains on exactly MIN_TRAIN dates (<= t - GAP)
    assert rows and seen[0] == st.MIN_TRAIN


def test_learnable_only_when_the_model_beats_rs():
    assert st.summarise(st.walk_forward(_dates(45, 8.0)))["verdict"].startswith("LEARNABLE")
    assert st.summarise(st.walk_forward(_dates(45, 0.0)))["verdict"] == "NOTHING LEARNABLE"
