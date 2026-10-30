"""htf_sweep_study.py — HTF levels are point-in-time; the sweep uses the daily rules."""
from __future__ import annotations

import numpy as np
import pandas as pd

import htf_sweep_study as hs


def _df(n=120, seed=0):
    rng = np.random.default_rng(seed)
    c = 100 + np.cumsum(rng.normal(0, 0.5, n))
    d = pd.bdate_range("2026-01-05", periods=n)
    return pd.DataFrame({"date": d, "open": c, "high": c + 1, "low": c - 1, "close": c})


def test_levels_never_include_the_current_week():
    df = _df()
    lv = hs.htf_levels(df)
    i = 60
    wk = pd.Timestamp(df["date"].iloc[i]).to_period("W-FRI")
    this_week_low = df.loc[pd.DatetimeIndex(df["date"]).to_period("W-FRI") == wk, "low"].min()
    prev = df.loc[pd.DatetimeIndex(df["date"]).to_period("W-FRI") < wk, "low"]
    assert lv[i][0] == df.loc[pd.DatetimeIndex(df["date"]).to_period("W-FRI") == wk - 1, "low"].min()
    assert this_week_low not in lv[i] or this_week_low in prev.values


def test_sweep_needs_reclaim_and_shadow():
    df = _df(seed=1)
    i = 80
    L = hs.htf_levels(df)[i][0]
    a = 2.0                                                 # synthetic bar around L
    df.loc[i, ["open", "high", "low", "close"]] = [L + 1.0, L + 1.2, L - 0.3, L + 1.1]
    df.loc[i - 1, "close"] = L + 2
    assert i in hs.htf_sweeps(df, i)
    df.loc[i, "close"] = L - 0.1                            # closes below: a breakdown
    assert i not in hs.htf_sweeps(df, i)
