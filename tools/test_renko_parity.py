"""Parity test: the Python Renko port must match the shipped JS engine bar-for-bar.

    py -3 tools/test_renko_parity.py        # prints PASS/FAIL, exits nonzero on fail
    pytest tools/test_renko_parity.py

`scanner_templates._renko_flips` is a port of `tools/renko.js`, which is what the chart
draws and what B-43 measured. If the two drift, the scanner fires on bars the chart shows
nothing on — the failure mode that makes a screen untrustworthy without looking broken.

The comparison is on REAL cached bars rather than synthetic ones, because the thing most
likely to diverge is the ATR seeding at the epoch boundaries, and that only bites on
real volatility shifts.

Requires `node` and the cached bars in tools/cache/backtest/. Skips cleanly without them.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

import scanner_templates as sc

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache" / "backtest"

SYMBOLS = ["RELIANCE.NS_1d", "HAL.NS_1d", "_NSEI_1d", "TCS.NS_1d", "INFY.NS_1d"]

_JS = r"""
global.window = global;
require(process.argv[2]);
const fs = require('fs');
const doc = JSON.parse(fs.readFileSync(process.argv[3], 'utf-8'));
const r = RENKO.compute(doc.bars, {atrPeriod: 5});
process.stdout.write(JSON.stringify({
  flips: r.flips.map(f => [f.index, f.dir, f.bricksInPrior]),
  state: r.state,
}));
"""


def _js_flips(bars_path: Path):
    runner = HERE / "_renko_parity_runner.js"
    runner.write_text(_JS, encoding="utf-8")
    try:
        p = subprocess.run(["node", str(runner), str(HERE / "renko.js"), str(bars_path)],
                           capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(p.stderr.strip()[:400])
        return json.loads(p.stdout)
    finally:
        try:
            runner.unlink()
        except OSError:
            pass


def _frame(bars_path: Path) -> pd.DataFrame:
    bars = json.loads(bars_path.read_text(encoding="utf-8"))["bars"]
    return pd.DataFrame({
        "open": [b["open"] for b in bars], "high": [b["high"] for b in bars],
        "low": [b["low"] for b in bars], "close": [b["close"] for b in bars],
        "volume": [b.get("volume", 0) for b in bars],
    })


def _check_one(stem: str) -> tuple[bool, str]:
    p = CACHE / f"{stem}.json"
    if not p.exists():
        return True, f"SKIP {stem} (no cached bars)"
    js = _js_flips(p)
    py = sc._renko_flips(_frame(p))
    a = [tuple(x) for x in js["flips"]]
    b = [(f["index"], f["dir"], f["bricks_in_prior"]) for f in py["flips"]]
    if a == b:
        return True, f"{stem}: {len(a)} flips, identical"
    first = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    return False, (f"{stem}: MISMATCH — js {len(a)} flips vs py {len(b)}; "
                   f"first diff at #{first}: js={a[first:first+1]} py={b[first:first+1]}")


def test_flip_parity_across_symbols():
    fails = []
    for stem in SYMBOLS:
        ok, msg = _check_one(stem)
        if not ok:
            fails.append(msg)
    assert not fails, "; ".join(fails)


#: `renko.js` returns its state through `+x.toFixed(4)`, so its numbers are rounded to
#: 4 decimals on the way out while the Python port returns full precision. The largest
#: observed gap across the basket is 4.5e-5 — squarely inside that rounding bound, not a
#: computation difference (the flip lists, which are exact integers, match perfectly).
#: Tolerance is set AT the bound so a genuine drift still fails.
STATE_TOL = 5e-5


def test_brick_state_parity():
    """Final brick size and standing direction must agree too, not just the flip list."""
    for stem in SYMBOLS:
        p = CACHE / f"{stem}.json"
        if not p.exists():
            continue
        js = _js_flips(p)["state"]
        py = sc._renko_flips(_frame(p))["state"]
        if js is None or py is None:
            assert js == py, f"{stem}: one engine produced no state"
            continue
        assert js["dir"] == py["dir"], f"{stem}: direction {js['dir']} vs {py['dir']}"
        assert abs(js["brick"] - py["brick"]) < STATE_TOL, f"{stem}: brick size differs"
        assert abs(js["lastClose"] - py["last_close"]) < STATE_TOL, f"{stem}: grid level differs"


def _main() -> int:
    print("Renko Python<->JS parity")
    failed = 0
    for stem in SYMBOLS:
        try:
            ok, msg = _check_one(stem)
        except Exception as e:                       # noqa: BLE001 - report, don't mask
            ok, msg = False, f"{stem}: ERROR {type(e).__name__}: {e}"
        print(("  PASS  " if ok else "  FAIL  ") + msg)
        failed += 0 if ok else 1
    try:
        test_brick_state_parity()
        print("  PASS  final brick size / direction / grid level agree")
    except AssertionError as e:
        print(f"  FAIL  state parity: {e}")
        failed += 1
    print(f"\n{'all parity checks passed' if not failed else str(failed) + ' failure(s)'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_main())
