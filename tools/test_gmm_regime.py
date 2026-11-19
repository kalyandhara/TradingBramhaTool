"""gmm_regime.py — EM recovers planted regimes and stays point-in-time."""
from __future__ import annotations

import numpy as np
import pandas as pd

import gmm_regime as gm


def _two_regime_close(seed=0):
    rng = np.random.default_rng(seed)
    calm = rng.normal(0.0005, 0.007, 600)
    wild = rng.normal(-0.001, 0.025, 200)
    r = np.concatenate([calm, wild, calm[:300], wild[:150], calm[:400]])
    idx = pd.bdate_range("2015-01-01", periods=len(r))
    return pd.Series(100 * np.exp(np.cumsum(r)), index=idx), len(calm)


def test_fit_orders_components_calm_then_stressed():
    rng = np.random.default_rng(1)
    x = np.vstack([rng.normal([0, -1], 0.3, (300, 2)), rng.normal([0, 2], 0.6, (100, 2))])
    m = gm.fit(x)
    assert m["mu"][1, 1] > m["mu"][0, 1]
    assert abs(m["w"][1] - 0.25) < 0.05


def test_fit_is_deterministic():
    rng = np.random.default_rng(2)
    x = rng.normal(size=(400, 2))
    a, b = gm.fit(x), gm.fit(x)
    assert np.allclose(a["mu"], b["mu"]) and a["loglik"] == b["loglik"]


def test_stress_is_high_inside_the_wild_stretch():
    close, n_calm = _two_regime_close()
    p = gm.rolling_stress(close, train=500, refit_every=21)
    f_idx = gm.features(close).index
    start2 = n_calm + 200 + 300 - gm.VOL_WINDOW                   # 2nd wild block, in feature rows
    wild_late = f_idx[start2 + 40: start2 + 130]
    calm_late = f_idx[-200:]
    assert p.reindex(wild_late).mean() > 0.7
    assert p.reindex(calm_late).mean() < 0.3


def test_rolling_stress_does_not_see_the_future():
    close, _ = _two_regime_close()
    full = gm.rolling_stress(close, train=500, refit_every=21)
    cut = close.iloc[:900]
    part = gm.rolling_stress(cut, train=500, refit_every=21)
    common = part.index
    assert np.allclose(full.reindex(common).to_numpy(), part.to_numpy())
