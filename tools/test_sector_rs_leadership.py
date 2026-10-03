"""Tests for sector_rs_leadership.leadership — pure aggregation, no network."""
from __future__ import annotations

import sector_rs_leadership as rsl


def _r(t5, t0):
    return {"t5": t5, "t0": t0}


def test_means_sorting_and_change():
    ranks = {"A1": _r(40, 90), "A2": _r(50, 80), "A3": _r(60, 70),
             "B1": _r(80, 20), "B2": _r(70, 30), "B3": _r(90, 40)}
    smap = {s: s[0] for s in ranks}
    df = rsl.leadership(ranks, smap)
    assert df["group"].tolist() == ["A", "B"]
    a = df.iloc[0]
    assert a["rs_t0"] == 80.0 and a["rs_t5"] == 50.0 and a["change"] == 30.0
    assert a["leaders"].split(", ")[0] == "A1"
    assert a["pct_top_quartile"] == 67


def test_thin_groups_and_unranked_stocks_are_dropped():
    ranks = {"A1": _r(50, 60), "A2": _r(50, 60), "A3": {"t5": None, "t0": None},
             "B1": _r(10, 20), "B2": _r(10, 20), "B3": _r(10, 20)}
    smap = {s: s[0] for s in ranks}
    df = rsl.leadership(ranks, smap)
    assert df["group"].tolist() == ["B"]


def test_missing_t5_leaves_change_blank():
    ranks = {f"C{i}": {"t5": None, "t0": 50 + i} for i in range(3)}
    df = rsl.leadership(ranks, {s: "C" for s in ranks})
    assert df.iloc[0]["rs_t5"] is None and df.iloc[0]["change"] is None
