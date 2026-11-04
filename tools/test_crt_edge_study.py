"""crt_edge_study.py — per-symbol clustering, populations and the decision rule."""
from __future__ import annotations

import numpy as np

import crt_edge_study as st


def _rows(n_sym=40, per=10, mu=0.0, covered_mu=None, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_sym):
        evs = []
        for k in range(per):
            cov = k % 2 == 0
            m = covered_mu if (cov and covered_mu is not None) else mu
            evs.append({"date": f"2025-{1 + k:02d}-15", "covered": cov,
                        "edge": {h: float(rng.normal(m, 2.0)) for h in st.HORIZONS}})
        rows.append({"symbol": f"S{i}", "events": evs})
    return rows


def test_real_edge_is_found_and_noise_is_not():
    assert st.evaluate(_rows(mu=1.5), "ALL")["verdict"] == "EDGE"
    assert st.evaluate(_rows(mu=0.0, seed=7), "ALL")["verdict"] == "NULL"


def test_uncovered_population_excludes_covered_events():
    rows = _rows(mu=0.0, covered_mu=3.0, seed=2)
    allp, unc = st.evaluate(rows, "ALL"), st.evaluate(rows, "UNCOVERED")
    assert unc["events"] == allp["events"] // 2
    assert unc["by_h"][20]["mean_edge_pct"] < allp["by_h"][20]["mean_edge_pct"]


def test_too_few_events_cannot_be_edge():
    assert st.evaluate(_rows(n_sym=10, per=5, mu=3.0), "ALL")["verdict"] == "NULL"


def test_symbols_are_the_unit_not_events():
    rows = _rows(n_sym=40, per=10, mu=0.0, seed=3)
    rows[0]["events"] *= 50                         # one name firing 500 times
    for e in rows[0]["events"]:
        e["edge"] = {h: 10.0 for h in st.HORIZONS}
    res = st.evaluate(rows, "ALL")
    assert res["by_h"][20]["symbols"] == 40         # still one opinion
