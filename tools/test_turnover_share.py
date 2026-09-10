"""Tests for turnover_share.py (B-62), offline.

The load-bearing property is that this is a SHARE: the columns must sum the way
a share does, or the whole "zero-sum, every gainer takes from a named loser"
reading is false and the table is just turnover with extra steps.

So the tests pin:
  * shares sum to 1 and the delta column sums to 0;
  * a sector can LOSE share on a day its own turnover ROSE — the property that
    separates this from a turnover column, and the one a reader will disbelieve
    until it is demonstrated;
  * scale-freeness: doubling every symbol's volume changes no share;
  * the aggregation is a SUM, so a heavyweight outweighs a minnow.
"""
import numpy as np
import pandas as pd
import pytest

import turnover_share as tsx


def _bars(turnovers, price=100.0):
    """Bars whose close x volume equals the given per-bar turnovers."""
    n = len(turnovers)
    vol = [t / price for t in turnovers]
    return pd.DataFrame({
        "open": np.full(n, price), "high": np.full(n, price * 1.01),
        "low": np.full(n, price * 0.99), "close": np.full(n, price),
        "volume": vol,
    })


def _grid(hist_by_sector, min_members=1):
    """Build the by_sector structure the share functions take."""
    return {s: dict(m) for s, m in hist_by_sector.items()}


def test_turnover_is_close_times_volume():
    df = _bars([1000.0, 2000.0])
    s = tsx.turnover_series(df)
    assert s.iloc[0] == pytest.approx(1000.0)
    assert s.iloc[-1] == pytest.approx(2000.0)
    assert tsx.turnover_at(df, 0) == pytest.approx(2000.0)
    assert tsx.turnover_at(df, 1) == pytest.approx(1000.0)


def test_shares_sum_to_one():
    by = _grid({
        "A": {"a1": _bars([100.0, 300.0])},
        "B": {"b1": _bars([100.0, 100.0])},
        "C": {"c1": _bars([800.0, 600.0])},
    })
    sh = tsx.shares(by, 0)
    assert sum(sh.values()) == pytest.approx(1.0)
    assert sh["C"] == pytest.approx(600.0 / 1000.0)


def test_a_sector_can_lose_share_on_a_day_its_turnover_rose():
    """The property that makes this a ROTATION column rather than a turnover one.
    B's money went UP 100 -> 150 and its share still FELL, because the market
    grew faster. A turnover column would have called that inflow."""
    by = _grid({
        "A": {"a1": _bars([100.0, 850.0])},
        "B": {"b1": _bars([100.0, 150.0])},
    })
    prev = tsx.shares(by, 1)
    now = tsx.shares(by, 0)
    assert tsx.turnover_at(by["B"]["b1"], 0) > tsx.turnover_at(by["B"]["b1"], 1)
    assert now["B"] < prev["B"]


def test_delta_share_is_zero_sum():
    by = _grid({
        "A": {"a1": _bars([100.0, 300.0])},
        "B": {"b1": _bars([400.0, 200.0])},
        "C": {"c1": _bars([500.0, 500.0])},
    })
    now, prev = tsx.shares(by, 0), tsx.shares(by, 1)
    deltas = [100.0 * (now[s] - prev[s]) for s in by]
    assert sum(deltas) == pytest.approx(0.0, abs=1e-9)


def test_shares_are_scale_free():
    """Doubling every symbol's volume is a heavier session, not rotation."""
    by = _grid({"A": {"a1": _bars([100.0, 300.0])},
                "B": {"b1": _bars([100.0, 100.0])}})
    doubled = _grid({"A": {"a1": _bars([200.0, 600.0])},
                     "B": {"b1": _bars([200.0, 200.0])}})
    assert tsx.shares(by, 0) == pytest.approx(tsx.shares(doubled, 0))


def test_sector_turnover_sums_rather_than_averages():
    """A heavyweight must outweigh a minnow — the same aggregation choice
    money_flow.sector_cmf makes, for the same reason."""
    heavy, light = _bars([1.0, 1_000_000.0]), _bars([1.0, 1.0])
    by = _grid({"BIG": {"h": heavy, "l": light}, "SMALL": {"l2": light}})
    assert tsx.sector_turnover(by["BIG"], 0) == pytest.approx(1_000_001.0)
    sh = tsx.shares(by, 0)
    assert sh["BIG"] > 0.999            # an average would have made this ~0.5


def test_a_dead_session_yields_no_shares_rather_than_nan():
    by = _grid({"A": {"a1": _bars([0.0, 0.0])}, "B": {"b1": _bars([0.0, 0.0])}})
    assert tsx.shares(by, 0) == {}


def test_short_history_is_none_not_an_exception():
    df = _bars([100.0])
    assert tsx.turnover_at(df, 5) is None
    assert tsx.turnover_at(None, 0) is None


def test_a_frame_without_ohlc_is_not_a_member():
    bad = pd.DataFrame({"something_else": [1, 2, 3]})
    assert tsx.turnover_at(bad, 0) is None
    assert tsx.sector_turnover({"x": bad}, 0) == 0.0


def test_rotation_grid_end_to_end_with_injected_history(monkeypatch):
    import types, sys as _sys
    fake_sectors = types.SimpleNamespace(
        symbol_map=lambda u: {"A1": "Capital Goods", "A2": "Capital Goods",
                              "A3": "Capital Goods", "B1": "Realty",
                              "B2": "Realty", "B3": "Realty"})
    monkeypatch.setitem(_sys.modules, "sectors", fake_sectors)
    hist = {s: _bars([100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0])
            for s in ("A1", "A2", "A3", "B1", "B2", "B3")}
    hist["A1"] = _bars([100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 400.0])

    g = tsx.rotation_grid("nifty500", hist=hist)
    assert not g.get("error")
    df = g["rows"]
    assert set(df["sector"]) == {"Capital Goods", "Realty"}
    assert df["share_pct"].sum() == pytest.approx(100.0, abs=0.01)
    assert df["d_share_d"].sum() == pytest.approx(0.0, abs=0.01)
    # Capital Goods gained the share Realty lost, and leads the sort.
    assert df.iloc[0]["sector"] == "Capital Goods"
    assert df.iloc[0]["d_share_d"] > 0
    assert df.iloc[-1]["d_share_d"] < 0


def test_thin_sectors_are_dropped_not_silently_averaged(monkeypatch):
    import types, sys as _sys
    fake_sectors = types.SimpleNamespace(
        symbol_map=lambda u: {"A1": "Capital Goods", "A2": "Capital Goods",
                              "A3": "Capital Goods", "B1": "Realty"})
    monkeypatch.setitem(_sys.modules, "sectors", fake_sectors)
    hist = {s: _bars([100.0] * 7) for s in ("A1", "A2", "A3", "B1")}
    g = tsx.rotation_grid("nifty500", hist=hist, min_members=3)
    assert set(g["rows"]["sector"]) == {"Capital Goods"}


def test_the_unsigned_caveat_travels_with_the_module(monkeypatch):
    """Same guard money_flow keeps: the warning is returned by the function, so a
    page cannot render the grid without having been handed the caveat."""
    import types, sys as _sys
    fake_sectors = types.SimpleNamespace(
        symbol_map=lambda u: {f"A{i}": "Capital Goods" for i in range(3)})
    monkeypatch.setitem(_sys.modules, "sectors", fake_sectors)
    hist = {f"A{i}": _bars([100.0] * 7) for i in range(3)}
    g = tsx.rotation_grid("nifty500", hist=hist)
    assert "unsigned" in g["unsigned_note"].lower()
    assert "proxy" in g["turnover_note"].lower()
