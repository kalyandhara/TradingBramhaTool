"""sweep_confirm_study.py — CISD / BOS definitions and the decision rule."""
from __future__ import annotations

import numpy as np

import sweep_confirm_study as st


def test_cisd_closes_above_the_open_of_the_down_run():
    o = np.array([10, 10.0, 9.5, 9.0, 8.4, 8.6, 9.2, 10.4])
    c = np.array([10, 9.5, 9.0, 8.5, 8.2, 9.0, 9.8, 10.6])
    # down run = bars 1..4 (close < open); its first open = 10.0; sweep at 4
    assert st.cisd_bar(o, c, 4) == 7                    # 10.6 > 10.0
    assert st.cisd_bar(o, c, 4, wait=2) is None


def test_bos_uses_only_confirmed_pivots():
    h = np.array([1, 1, 1, 1, 1, 2, 9, 2, 1, 1, 1, 1, 1, 2, 3, 10], dtype=float)
    c = h - 0.1
    # pivot high 9 at index 6 is confirmed at index 11 (p=5); the close 9.9 at 15 breaks it
    assert st.bos_bar(h, c, 10, wait=5) == 15
    # an index-3 "high" with only 3 bars to its left is never a confirmed pivot
    h2 = np.array([1, 2, 3, 9, 3, 2, 1, 1, 1, 1, 1, 2, 3, 4, 10], dtype=float)
    assert st.bos_bar(h2, h2 - 0.1, 9, wait=5) is None


def _rows(diff, n=40, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        evs = []
        for k in range(6):
            cf = k % 2 == 0
            m = diff if cf else 0.0
            evs.append({"date": f"2025-{k + 1:02d}-10", "conf": cf,
                        "edge_arm": {hz: float(rng.normal(m + 0.5, 1.0)) for hz in st.HORIZONS},
                        "edge_sweep": {hz: float(rng.normal(0.5, 1.0)) for hz in st.HORIZONS}})
        rows.append({"symbol": f"S{i}", "events": evs})
    return rows


def test_helps_only_when_confirmation_is_better():
    assert st.analyse(_rows(1.5))["verdict"].startswith("FILTER HELPS")
    assert st.analyse(_rows(0.0, seed=4))["verdict"] == "NO FILTER"
