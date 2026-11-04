"""risk_box.js against the Python it mirrors, run through node.

The chart's risk box sizes positions and seeds a default stop; the trade card
does both in Python. If the two disagree the chart shows a different trade than
the card, so the JS is held to `position_sizing.shares_for_risk` and to the stop
rule in `stock_council.judge`. Skips cleanly when node is unavailable.
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from ta.volatility import AverageTrueRange

import position_sizing as ps
import stock_council as council

HERE = Path(__file__).resolve().parent
RB = str(HERE / "risk_box.js").replace("\\", "/")

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node not available")


def _node(expr: str):
    script = f"require({RB!r}); process.stdout.write(JSON.stringify({expr}));"
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


@pytest.mark.parametrize("capital,entry,stop,risk", [
    (100_000, 101.0, 97.7, 2.0),
    (100_000, 100.0, 99.9, 2.0),        # capped by capital
    (2_500_000, 1843.5, 1790.25, 1.0),
    (50_000, 250.0, 262.0, 2.0),        # short-side stop
])
def test_size_matches_python(capital, entry, stop, risk):
    js = _node(f"RISKBOX.size({capital}, {entry}, {stop}, {risk})")
    py = ps.shares_for_risk(capital, entry, stop, risk)
    assert js.keys() == py.keys()
    for k in py:
        assert js[k] == pytest.approx(py[k]), k


def test_constants_match_python():
    js = _node("[RISKBOX.RISK_PER_TRADE_PCT, RISKBOX.MAX_POSITION_PCT, RISKBOX.ATR_STOP_MULT]")
    assert js == [ps.RISK_PER_TRADE_PCT, ps.MAX_POSITION_PCT, council.ATR_STOP_MULT]


def _bars(n=60, seed=7):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1.2, n))
    high = close + rng.uniform(0.2, 2.0, n)
    low = close - rng.uniform(0.2, 2.0, n)
    return pd.DataFrame({"time": np.arange(n) * 86400, "open": close,
                         "high": high, "low": low, "close": close})


@pytest.mark.parametrize("seed", [1, 7, 42])
def test_default_stop_matches_the_trade_card_rule(seed):
    df = _bars(seed=seed)
    bars = df.to_dict("records")
    js = _node(f"RISKBOX.defaultStop({json.dumps(bars)})")
    atr = float(AverageTrueRange(df["high"], df["low"], df["close"], window=14)
                .average_true_range().iloc[-1])
    price, swing = float(df["close"].iloc[-1]), float(df["low"].tail(10).min())
    py = (min(swing, price - council.ATR_STOP_MULT * atr) if swing < price
          else price - council.ATR_STOP_MULT * atr)
    # ta seeds its ATR the same Wilder way; allow float noise only.
    assert js == pytest.approx(py, rel=1e-9)


def test_compute_targets_and_live_r():
    box = _node("RISKBOX.compute({capital: 100000, entry: 100, stop: 95, last: 107.5})")
    assert box["side"] == "long" and box["r"] == 5
    assert [t["price"] for t in box["targets"]] == [105, 110, 115]
    assert box["last_r"] == pytest.approx(1.5)
    assert box["size"]["qty"] == 400                    # 2000 / 5


def test_short_box_mirrors():
    box = _node("RISKBOX.compute({capital: 100000, entry: 100, stop: 104, last: 96})")
    assert box["side"] == "short"
    assert [t["price"] for t in box["targets"]] == [96, 92, 88]
    assert box["last_r"] == pytest.approx(1.0)


def test_degenerate_inputs_draw_nothing():
    assert _node("RISKBOX.compute({entry: 100, stop: 100})") is None
    assert _node("RISKBOX.size(0, 100, 95)") is None
    assert not math.isnan(ps.RISK_PER_TRADE_PCT)
