"""B-116 census helpers: the placebo rebuilds the bracket, the bootstrap is
trade-weighted and seeded.

    py -3 -m pytest tools/test_target_reach_census.py -q
"""
import numpy as np
import pandas as pd

import target_reach_census as trc


def _frame(n=400, drift=0.002):
    c = 100 * np.cumprod(np.full(n, 1 + drift))
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99,
                         "close": c, "volume": 1e5})


def test_placebo_rising_tape_hits_a_long_target_not_a_short_one():
    df = _frame()
    long_tr = {"entry_px": 100.0, "stop": 95.0, "target": 105.0, "side": "long",
               "time_stop": None}
    short_tr = {"entry_px": 100.0, "stop": 105.0, "target": 95.0, "side": "short",
                "time_stop": None}
    hl, rl = trc.placebo(df, long_tr, np.random.default_rng(1), max_bars=60, warmup=10)
    hs, _ = trc.placebo(df, short_tr, np.random.default_rng(1), max_bars=60, warmup=10)
    assert hl == 1.0 and rl > 0
    assert hs == 0.0


def test_placebo_none_when_no_eligible_bars():
    tr = {"entry_px": 100.0, "stop": 95.0, "target": 105.0, "side": "long",
          "time_stop": None}
    assert trc.placebo(_frame(n=50), tr, np.random.default_rng(1)) is None


def test_cluster_ci_is_trade_weighted_and_seeded():
    by = {"A": [1.0, 1.0, 1.0], "B": [0.0]}
    p, lo, hi = trc.cluster_ci(by, 0.05, n_boot=500)
    assert p == 0.75
    assert lo <= p <= hi
    assert trc.cluster_ci(by, 0.05, n_boot=500) == (p, lo, hi)


def test_labels():
    assert trc.label(0.01, 0.2) == "INFORMATIVE"
    assert trc.label(-0.2, -0.01) == "WORSE THAN CHANCE"
    assert trc.label(-0.1, 0.1) == "NO BETTER THAN CHANCE"
