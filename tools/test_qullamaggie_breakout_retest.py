"""B-147b re-test — the reused plan is B-147's plan, ATR is what it says, and the
out-of-sample universe really excludes every B-147 name.

Run:  python -m pytest tools/test_qullamaggie_breakout_retest.py -q
"""
import numpy as np
import pandas as pd
import pytest

import qullamaggie_breakout_retest as rt
import qullamaggie_edge_study as qes


def _walk(n=400, seed=7):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.02, n)))
    h = c * (1 + rng.uniform(0, 0.02, n))
    l = c * (1 - rng.uniform(0, 0.02, n))
    return h, l, c


def test_plan_with_signal_low_stop_reproduces_b147_plan():
    h, l, c = _walk()
    sma10 = pd.Series(c).rolling(10).mean().to_numpy()
    checked = 0
    for t in range(20, len(c) - qes.PLAN_MAX - 1):
        ref = qes._plan(h, l, c, sma10, t)
        got = rt._plan_at(h, l, c, sma10, t, l[t])
        if ref is None:
            assert got is None
            continue
        assert abs(ref["pct"] - got) < 1e-12
        checked += 1
    assert checked > 200


def test_atr_is_simple_mean_of_true_range():
    h, l, c = _walk(60)
    atr = rt._atr(h, l, c)
    t = 30
    tr = [max(h[j] - l[j], abs(h[j] - c[j - 1]), abs(l[j] - c[j - 1])) for j in range(t - 13, t + 1)]
    assert abs(atr[t] - np.mean(tr)) < 1e-9
    assert np.isnan(atr[13])


def test_wider_stop_is_never_stopped_out_earlier():
    h, l, c = _walk()
    sma10 = pd.Series(c).rolling(10).mean().to_numpy()
    t = 100
    tight = rt._plan_at(h, l, c, sma10, t, c[t] * 0.999)
    assert tight is not None and rt._plan_at(h, l, c, sma10, t, c[t] * 1.01) is None


def test_oos_universe_excludes_every_in_sample_name_and_funds():
    seen = {f.stem.replace("_1d", "") for f in rt.IN_SAMPLE.glob("*_1d.json")}
    oos = {f.stem.replace("_1d", "") for f in rt.oos_files()}
    if not seen and not oos:
        pytest.skip("no cached daily bars (tools/cache is gitignored) — fresh checkout")
    assert oos and not (oos & seen)
    assert not any(rt._is_fund(s) for s in oos)
