"""Tests for cycles.js (window.CY), run through node."""
import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
JS = os.path.join(HERE, "cycles.js").replace("\\", "/")
sys.path.insert(0, HERE)

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def cy(expr: str, **data):
    binds = "".join(f"const {k} = {json.dumps(v)};\n" for k, v in data.items())
    script = (f"global.window = global; require({JS!r});\n{binds}"
              f"process.stdout.write(JSON.stringify({expr}));")
    out = subprocess.run(["node", "-"], input=script, capture_output=True,
                         text=True, encoding="utf-8")
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_fld_splits_known_and_forward_at_last_bar():
    closes = [float(x) for x in range(10, 20)]          # 10 bars
    f = cy("CY.fld(c, 6)", c=closes)
    assert f["shift"] == 3 and f["drawingAid"] is True
    assert [p["idx"] for p in f["known"]] == list(range(3, 10))
    assert f["known"][0]["value"] == 10.0                # close[0] lands on bar 3
    # forward part: bars 10..12 carry the last 3 closes
    assert f["forward"] == [{"idx": 10, "value": 17.0}, {"idx": 11, "value": 18.0},
                            {"idx": 12, "value": 19.0}]


def test_fld_odd_cycle_floors_and_null_when_too_short():
    assert cy("CY.fld(c, 41).shift", c=[1.0] * 30) == 20
    assert cy("[CY.fld([1,2,3], 6), CY.fld([1,2,3,4], 1), CY.fld(null, 20)]") == [None, None, None]


def test_fld_matches_python_fld_confluence():
    fc = pytest.importorskip("fld_confluence")
    rng = np.random.default_rng(7)
    close = 100 + np.cumsum(rng.normal(0, 1, 120))
    for cycle in (20, 40, 80):
        py = fc._prep(close, cycle)["fld"]
        js = cy("CY.fld(c, n).known", c=close.tolist(), n=cycle)
        got = np.full(len(close), np.nan)
        for p in js:
            got[p["idx"]] = p["value"]
        np.testing.assert_allclose(got, py, equal_nan=True)
