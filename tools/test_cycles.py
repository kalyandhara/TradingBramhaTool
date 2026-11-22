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


def _lows(idxs, highs_between=True, provisional_last=False):
    pv = []
    for k, i in enumerate(idxs):
        pv.append({"idx": i, "type": "low", "price": 100})
        if highs_between:
            pv.append({"idx": i + 2, "type": "high", "price": 110})
    if provisional_last:
        pv[-1 if not highs_between else -2]["provisional"] = True
    return pv


def test_dominant_cycle_median_iqr_and_next_window():
    # low spacings 10, 12, 14, 20 -> median 13, q1 11.5, q3 15.5
    dc = cy("CY.dominantCycle(pv, 60)", pv=_lows([0, 10, 22, 36, 56]))
    assert (dc["median"], dc["q1"], dc["q3"], dc["n"]) == (13, 11.5, 15.5, 4)
    assert dc["lastTrough"] == 56
    assert dc["next"] == {"idx": 69, "from": 68, "to": 72}   # 56+11.5 rounds to 68
    assert dc["half"] == 63 and dc["overdue"] is False and dc["drawingAid"] is True


def test_dominant_cycle_ignores_provisional_and_flags_overdue():
    pv = _lows([0, 10, 20, 30, 33], provisional_last=True)   # 33 is provisional
    dc = cy("CY.dominantCycle(pv, 50)", pv=pv)
    assert dc["median"] == 10 and dc["lastTrough"] == 30
    assert dc["overdue"] is True                              # window 40..40 closed by bar 50


def test_dominant_cycle_null_with_too_few_troughs():
    assert cy("CY.dominantCycle(pv, 30)", pv=_lows([0, 10, 20])) is None
    assert cy("CY.dominantCycle(null, 30)") is None


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
