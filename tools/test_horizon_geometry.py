"""Pins the arithmetic of horizon_geometry, not any claim that it predicts."""
import numpy as np
import pandas as pd

import horizon_geometry as hg


def _daily(years=6, seed=1):
    idx = pd.bdate_range("2019-01-01", periods=252 * years)
    t = np.arange(len(idx))
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(0.6 * np.sin(t / 180) + t / 2000 + rng.normal(0, .01, len(t)).cumsum() * .2)
    return pd.DataFrame({"open": close, "high": close * 1.01,
                         "low": close * .99, "close": close}, index=idx)


def test_spiral_one_loop_per_year_and_angle_in_range():
    sp = hg.year_spiral(_daily())
    assert list(sp) == sorted(sp) and len(sp) == 6
    for df in sp.values():
        assert df["theta"].between(0, 360).all()
        assert df["theta"].is_monotonic_increasing


def test_spiral_keeps_most_recent_years():
    sp = hg.year_spiral(_daily(years=10), max_years=3)
    assert len(sp) == 3 and max(sp) == "2028"


def test_intersections_of_two_unit_circles():
    pts = hg._circle_intersections((0, 0, 1), (1, 0, 1))
    ys = sorted(round(y, 6) for _, y in pts)
    assert ys == [round(-np.sqrt(3) / 2, 6), round(np.sqrt(3) / 2, 6)]
    assert hg._circle_intersections((0, 0, 1), (5, 0, 1)) == []


def test_geometry_nodes_are_in_the_future_and_deterministic():
    d = _daily()
    g1, g2 = hg.pivot_geometry(d), hg.pivot_geometry(d)
    assert g1.ok, g1.note
    assert [n["date"] for n in g1.nodes] == [n["date"] for n in g2.nodes]
    for n in g1.nodes:
        assert n["date"] > d.index[-1]
        assert n["circles"] >= hg.MIN_NODE_CIRCLES


def test_short_history_refuses():
    g = hg.pivot_geometry(_daily(years=1))
    assert not g.ok and "weekly bars" in g.note
