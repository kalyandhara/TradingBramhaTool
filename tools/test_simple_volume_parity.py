"""Parity test: simple_volume.py must match simple_volume.js bar-for-bar.

Same pattern as test_mfi_parity.py / test_renko_parity.py.

Run:  python -m pytest tools/test_simple_volume_parity.py -q
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import simple_volume as sv

HERE = Path(__file__).resolve().parent
JS_MOD = str(HERE / "simple_volume.js").replace("\\", "/")
CACHE = HERE / "cache" / "backtest"

SYMBOLS = ["RELIANCE.NS_1d", "HAL.NS_1d", "TCS.NS_1d", "INFY.NS_1d", "BEL.NS_1d"]

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node not available")


def _load(sym: str):
    """Load cached JSON, return (df, bars_list) or (None, None)."""
    p = CACHE / f"{sym}.json"
    if not p.exists():
        return None, None
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    bars = data["bars"]
    df = pd.DataFrame(bars)
    df.rename(columns={"open": "Open", "close": "Close",
                       "high": "High", "low": "Low", "volume": "Volume"},
              inplace=True)
    return df, bars


def _js_classify(bars: list[dict]) -> list[dict]:
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False,
                                     encoding="utf-8")
    json.dump(bars, tmp)
    tmp.close()
    tmp_path = tmp.name.replace("\\", "/")
    script_code = f"""
        global.window = global;
        require({JS_MOD!r});
        const fs = require('fs');
        const bars = JSON.parse(fs.readFileSync({tmp_path!r}, 'utf8'));
        const rows = window.SimpleVolume.classify(bars);
        console.log(JSON.stringify(rows.map(r => ({{kind: r.kind, ma: r.ma, volume: r.value}}))));
    """
    script_file = tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False,
                                              encoding="utf-8")
    script_file.write(script_code)
    script_file.close()
    try:
        out = subprocess.run(["node", script_file.name],
                             capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        return json.loads(out.stdout)
    finally:
        os.unlink(tmp.name)
        os.unlink(script_file.name)


@pytest.mark.parametrize("sym", SYMBOLS)
def test_parity(sym: str):
    df, bars = _load(sym)
    if df is None:
        pytest.skip(f"{sym} not cached")

    py_sv = sv.classify(df)
    js_rows = _js_classify(bars)

    assert len(py_sv) == len(js_rows), f"length mismatch: {len(py_sv)} vs {len(js_rows)}"

    mismatches = []
    for i in range(len(py_sv)):
        py_kind = py_sv.iloc[i]["kind"]
        js_kind = js_rows[i]["kind"]
        if py_kind != js_kind:
            mismatches.append((i, py_kind, js_kind))

    if mismatches:
        sample = mismatches[:10]
        msg = f"{len(mismatches)} kind mismatches in {sym}; first 10: {sample}"
        pytest.fail(msg)

    # MA parity where both are defined
    compared = 0
    for i in range(len(py_sv)):
        py_ma = py_sv.iloc[i]["ma"]
        js_ma = js_rows[i]["ma"]
        if js_ma is None:
            assert np.isnan(py_ma), f"bar {i}: JS ma=null but Python ma={py_ma}"
            continue
        assert not np.isnan(py_ma), f"bar {i}: JS ma={js_ma} but Python ma=NaN"
        if abs(py_ma) > 1e-9:
            assert abs(py_ma - js_ma) / abs(py_ma) < 1e-6, \
                f"bar {i}: MA diverged: py={py_ma} js={js_ma}"
        compared += 1

    assert compared >= 50, f"only {compared} MA bars compared"
