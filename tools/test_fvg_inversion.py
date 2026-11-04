"""fvg.js B-168 additions — CE and inversion, run through node like test_psar.py."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

FVG = str(Path(__file__).resolve().parent / "fvg.js").replace("\\", "/")
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")


def _zones(bars):
    js = f"require({FVG!r}); process.stdout.write(JSON.stringify(FVG.compute({json.dumps(bars)})));"
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def _b(t, o, h, l, c):
    return {"time": t, "open": o, "high": h, "low": l, "close": c, "volume": 1}


BULL_GAP = [_b(1, 100, 101, 99, 100.5), _b(2, 101, 106, 100.8, 105.5), _b(3, 105.5, 107, 103, 106)]


def test_ce_is_the_gap_midpoint():
    z = _zones(BULL_GAP)[0]
    assert z["bullish"] and z["bottom"] == 101 and z["top"] == 103
    assert z["ce"] == 102


def test_wick_through_is_not_an_inversion():
    bars = BULL_GAP + [_b(4, 106, 106, 104, 105), _b(5, 105, 105, 100, 101.5)]   # wick to 100, close 101.5
    z = _zones(bars)[0]
    assert z["filledIdx"] == 4 and z["invertedIdx"] is None


def test_close_through_far_side_inverts():
    bars = BULL_GAP + [_b(4, 106, 106, 104, 105), _b(5, 105, 105, 99, 100)]       # close 100 < bottom 101
    z = _zones(bars)[0]
    assert z["invertedIdx"] == 4 and z["invertedTime"] == 5


def test_bearish_gap_inverts_on_close_above_top():
    bars = [_b(1, 100, 101, 99, 99.5), _b(2, 99, 99.2, 94, 94.5), _b(3, 94.5, 96, 93, 95),
            _b(4, 95, 96, 94, 95.5), _b(5, 96, 100.5, 96, 100)]                   # gap 96..99, close 100
    z = _zones(bars)[0]
    assert not z["bullish"] and z["invertedIdx"] == 4
