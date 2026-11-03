"""B-183: kept trades carry the plan levels the no-edge baseline needs."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import backtest as bt
import scanner_templates as sc

NAME = "_TEST keep_trades levels"


@pytest.fixture()
def one_shot():
    def fn(df):
        if len(df) != 300:
            return None
        return {"pattern_type": "t", "entry": 100.0, "stop": 95.0, "target": 110.0,
                "time_stop": 5, "score_base": 50}
    sc.SCANNERS[NAME] = {"fn": fn, "description": "test", "category": "Entry"}
    yield NAME
    sc.SCANNERS.pop(NAME, None)


def test_kept_trades_carry_target_time_stop_and_horizon(one_shot):
    n = 500
    c = 100.0 + np.sin(np.arange(n)) * 0.1
    df = pd.DataFrame({"open": c, "high": c + 0.5, "low": c - 0.5, "close": c,
                       "volume": 1e6}, index=pd.bdate_range("2024-01-01", periods=n))
    out = bt.backtest_scanner(one_shot, ["X"], lambda s: df, keep_trades=True,
                              fill_model="market")
    tr = out["trades"][0]
    assert (tr["target"], tr["time_stop"], tr["max_bars"]) == (110.0, 5.0, 60)
