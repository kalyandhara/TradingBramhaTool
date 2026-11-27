"""Tests for market_breadth_score — breadth counts and score maths, no network."""
import numpy as np
import pandas as pd
import pytest

import market_breadth_score as m


def _frame(closes, vols=None):
    closes = list(closes)
    return pd.DataFrame({"Close": closes,
                         "Volume": vols if vols is not None else [100] * len(closes)})


UP = _frame(np.linspace(100, 300, 260))      # rising -> above 200 EMA
DOWN = _frame(np.linspace(300, 100, 260))    # falling -> below
SHORT = _frame(np.linspace(100, 120, 150))   # < 200 bars -> no data


def test_ema_state():
    assert m.ema_state(UP) is True
    assert m.ema_state(DOWN) is False
    assert m.ema_state(SHORT) is None
    assert m.ema_state(None) is None


def test_breadth_counts_excludes_no_data_and_missing():
    frames = {"A": UP, "B": DOWN, "C": DOWN, "D": SHORT}
    r = m.breadth_counts(["A", "B", "C", "D", "E"], frames)
    assert r == {"members": 5, "measured": 3, "no_data": 2, "above": 1, "below": 2,
                 "pct_above": 33.3, "pct_below": 66.7}


def test_breadth_counts_empty_group():
    r = m.breadth_counts(["X"], {})
    assert r["pct_below"] is None and r["no_data"] == 1


def test_breadth_table_keeps_order():
    rows = m.breadth_table({"Z": ["A"], "A": ["B"]}, {"A": UP, "B": DOWN})
    assert [r["index"] for r in rows] == ["Z", "A"]
    assert rows[1]["below"] == 1


def test_advance_share():
    assert m.advance_share({"A": UP, "B": DOWN, "C": UP}) == pytest.approx(66.7)
    assert m.advance_share({}) is None


def test_up_volume_share():
    up = _frame([1, 2, 3], [0, 300, 300])
    dn = _frame([3, 2, 1], [0, 100, 100])
    assert m.up_volume_share({"a": up, "b": dn}) == 75.0


def test_trend_pillar_all_up_all_down_and_short():
    assert m.trend_pillar(UP)["score"] == 100
    assert m.trend_pillar(DOWN)["score"] == 0
    assert m.trend_pillar(SHORT)["score"] is None


def test_breadth_pillar_weights_and_single_input():
    assert m.breadth_pillar(50, 100)["score"] == pytest.approx(70.0)
    assert m.breadth_pillar(None, 40)["score"] == 40
    assert m.breadth_pillar(None, None)["score"] is None


def test_volatility_pillar_inverts_percentile():
    vix = _frame(list(range(1, 101)))              # last value is the max
    assert m.volatility_pillar(vix)["score"] == 0
    vix2 = _frame(list(range(100, 0, -1)))         # last value is the min
    assert m.volatility_pillar(vix2)["score"] == 99.0


def test_flows_pillar():
    assert m.flows_pillar(0.12)["score"] == 12.0
    assert m.flows_pillar(None)["score"] is None


def test_weights_are_the_owner_priors():
    assert m.WEIGHTS == {"trend": 30, "breadth": 25, "volume": 20,
                         "volatility": 15, "flows": 10}
    assert sum(m.WEIGHTS.values()) == 100


def _p(key, score):
    return {"key": key, "label": m.PILLAR_LABELS[key], "weight": m.WEIGHTS[key],
            "score": score}


def test_composite_full_weight():
    ps = [_p("trend", 100), _p("breadth", 40), _p("volume", 50),
          _p("volatility", 20), _p("flows", 10)]
    c = m.composite(ps)
    # 30 + 10 + 10 + 3 + 1 = 54
    assert c["score"] == 54.0 and c["weight_covered"] == 100 and c["band"] == "mixed"


def test_composite_renormalises_over_missing_pillar():
    ps = [_p("trend", 100), _p("breadth", 40), _p("volume", 50),
          _p("volatility", 20), _p("flows", None)]
    c = m.composite(ps)
    assert c["weight_covered"] == 90
    assert c["score"] == pytest.approx(53 / 0.9, abs=0.05)
    assert "Liquidity / Flows not assessed" in c["read"]


def test_composite_nothing_read():
    assert m.composite([_p("trend", None)])["score"] is None


@pytest.mark.parametrize("s,band", [(80, "broadly healthy"), (70, "broadly healthy"),
                                    (55, "mixed"), (35, "weak"), (10, "stressed")])
def test_bands(s, band):
    assert m.band_for(s) == band


def test_build_end_to_end():
    frames = {"A": UP, "B": DOWN}
    out = m.build(frames, {"NIFTY 500": ["A", "B"]}, UP, None, 0.5, None)
    assert out["rows"][0]["below"] == 1
    assert {p["key"] for p in out["pillars"]} == set(m.WEIGHTS)
    assert out["composite"]["score"] is not None
