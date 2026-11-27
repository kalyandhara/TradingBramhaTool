"""rating.rating_detail — the Overall Rating's parts as numbers (pick re-score).

Spec: docs/superpowers/specs/2026-11-26-pick-rescore-design.md §1
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import rating


def _frame(n=300, start=100.0, drift=0.002, seed=1):
    rng = np.random.default_rng(seed)
    close = start * np.cumprod(1 + drift + rng.normal(0, 0.01, n))
    idx = pd.bdate_range("2025-06-02", periods=n)
    return pd.DataFrame({"open": close * 0.995, "high": close * 1.01, "low": close * 0.99,
                         "close": close, "volume": rng.integers(1e5, 1e6, n).astype(float)},
                        index=idx)


df = _frame()
nifty = _frame(seed=2, drift=0.0005)


def test_detail_matches_overall_rating():
    d = rating.rating_detail(df, nifty)
    r, bd = rating.overall_rating(df, nifty)
    assert d["rating"] == r
    assert bd == {"Minervini": f"{d['minervini']}/8", "TechnoFunda": f"{d['technofunda']}/6",
                  "CANSLIM": f"{d['canslim']}/{d['canslim_n']}", "EW conf": str(d["ew_conf"])}


def test_detail_checks_are_booleans_matching_the_count():
    d = rating.rating_detail(df, nifty)
    checks = [d[k] for k in ("cs_near_high", "cs_volume", "cs_market", "cs_rs")]
    assert all(isinstance(c, bool) for c in checks)
    assert sum(checks) == d["canslim"] and d["canslim_n"] == 4


def test_detail_without_benchmark_has_none_checks():
    d = rating.rating_detail(df, None)
    assert d["cs_market"] is None and d["cs_rs"] is None and d["canslim_n"] == 2


def test_detail_is_none_when_scoring_fails():
    assert rating.rating_detail(df.head(3), nifty) is None
    assert rating.overall_rating(df.head(3), nifty) == (None, {})
