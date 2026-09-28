"""Tests for sector_turnover_heatmap — pure arithmetic, no network."""
from __future__ import annotations

import numpy as np
import pandas as pd

import sector_turnover_heatmap as th


def _bars(closes, vols):
    idx = pd.bdate_range("2026-08-03", periods=len(closes))
    return pd.DataFrame({"close": closes, "volume": vols}, index=idx)


def test_ad_net_is_signed_share_of_group_turnover():
    n = 20
    up = _bars(np.linspace(100, 120, n), [300] * n)
    dn = _bars(np.linspace(100, 80, n), [100] * n)
    ad, _ = th.group_series({"UP": up, "DN": dn})
    last_up, last_dn = up["close"].iloc[-1] * 300, dn["close"].iloc[-1] * 100
    assert abs(ad.iloc[-1] - 100 * (last_up - last_dn) / (last_up + last_dn)) < 1e-9
    assert np.isnan(ad.iloc[0])


def test_turnover_vs_own_history_flags_a_heavy_day():
    n = 20
    vols = [100] * (n - 1) + [300]
    _, rel = th.group_series({"A": _bars([100.0] * n, vols), "B": _bars([50.0] * n, [100] * n)})
    assert abs(rel.iloc[-1] - (30000 + 5000) / (10000 + 5000)) < 1e-9
    assert rel.iloc[:th.BASELINE].isna().all()


def test_heatmaps_last_15_newest_first_sorted_by_today():
    n = 25
    good = {"G1": _bars(np.linspace(100, 130, n), [100] * n),
            "G2": _bars(np.linspace(100, 125, n), [100] * n)}
    bad = {"B1": _bars(np.linspace(100, 70, n), [100] * n),
           "B2": _bars(np.linspace(100, 75, n), [100] * n)}
    ad, rel = th.heatmaps({"Bad": bad, "Good": good})
    assert ad.shape[1] == 15 and list(ad.index) == ["Good", "Bad"]
    assert ad.columns[0] == pd.bdate_range("2026-08-03", periods=n)[-1].strftime("%d-%m")
    assert list(rel.index) == ["Good", "Bad"] and list(rel.columns) == list(ad.columns)
