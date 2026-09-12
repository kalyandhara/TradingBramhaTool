"""Parity test: the chart's MFI must match the scanner's MFI bar-for-bar.

    py -3 tools/test_mfi_parity.py        # prints PASS/FAIL, exits nonzero on fail
    pytest tools/test_mfi_parity.py

B-45 put MFI on the chart by porting `_mfi_series` (scanner_templates.py) into
`mfiSeries` in tools/chart_dashboard.html. B-24 is the reason that port gets a test:
two RSI-divergence implementations were left to drift and ended up disagreeing, so a
scanner fired on bars the chart showed nothing on — a screen that is untrustworthy
without looking broken.

Follows the `test_renko_parity.py` pattern, with one difference: `mfiSeries` lives
INLINE in the dashboard HTML rather than in its own .js module, so the function is
sliced out by brace-matching and run in node. If that slice ever fails to find the
function, the test FAILS rather than skipping — a parity test that silently stops
running is worse than no test.

Requires `node` and the cached bars in tools/cache/backtest/. Skips per-symbol
without them.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

import scanner_templates as sc

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache" / "backtest"
DASH = HERE / "chart_dashboard.html"

SYMBOLS = ["RELIANCE.NS_1d", "HAL.NS_1d", "_NSEI_1d", "TCS.NS_1d", "INFY.NS_1d"]

#: MFI is undefined when a window has no DOWN bar carrying volume (see the note on
#: `mfiSeries`): negative money flow is zero and the ratio has no value. Python yields
#: NaN there and the JS omits the point.
#:
#: This is not a rare edge case, and the first run of this test is how that was found:
#: **`^NSEI` has 1,333 zero-volume bars out of 4,648 (28.7%)** — yfinance does not carry
#: turnover for the index — so 27.9% of its MFI bars are undefined ON BOTH SIDES. That is
#: correct behaviour, not drift: **MFI is a volume oscillator and it has nothing to say
#: about a series with no volume.** The chart draws it as a gap, which is the honest
#: rendering; a naive port that substituted 100 or 50 would have drawn a confident line
#: over a quarter of the index's history.
#:
#: So the guard is expressed against bars that are DEFINABLE at all, not against all bars
#: — its only job is to stop the test passing vacuously if the port started dropping
#: everything.
MIN_COMPARED_FRAC = 0.98


def _extract_mfi_js() -> str:
    """Slice `function mfiSeries(...) {...}` out of the dashboard by brace matching."""
    src = DASH.read_text(encoding="utf-8")
    m = re.search(r"function mfiSeries\s*\(", src)
    assert m, "mfiSeries not found in chart_dashboard.html — the port was renamed or removed"
    i = src.index("{", m.end())
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[m.start():j + 1]
    raise AssertionError("unbalanced braces while slicing mfiSeries")


_RUNNER = """
const fs = require('fs');
__MFI__
const doc = JSON.parse(fs.readFileSync(process.argv[2], 'utf-8'));
process.stdout.write(JSON.stringify(mfiSeries(doc.bars, 14)));
"""


def _js_mfi(bars_path: Path):
    runner = HERE / "_mfi_parity_runner.js"
    runner.write_text(_RUNNER.replace("__MFI__", _extract_mfi_js()), encoding="utf-8")
    try:
        p = subprocess.run(["node", str(runner), str(bars_path)],
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
        "high": [b["high"] for b in bars], "low": [b["low"] for b in bars],
        "close": [b["close"] for b in bars], "volume": [b.get("volume", 0) for b in bars],
    }), [b["time"] for b in bars]


def _definable_bars(df: pd.DataFrame, n: int) -> int:
    """Bars whose n-window contains at least one DOWN typical-price bar with volume.

    Anything outside this set is undefined by the definition of MFI itself, so counting
    it as a 'drop' would penalise the port for being correct on a volume-less series.
    """
    tp = (df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)) / 3.0
    down = ((tp.diff() < 0) & (df["volume"].astype(float) > 0)).astype(int)
    return int((down.rolling(n).sum().iloc[n:] > 0).sum())


def _check_one(stem: str) -> tuple[bool, str]:
    p = CACHE / f"{stem}.json"
    if not p.exists():
        return True, f"SKIP {stem} (no cached bars)"
    df, times = _frame(p)
    py = sc._mfi_series(df, 14)
    js_by_time = {pt["time"]: pt["value"] for pt in _js_mfi(p)}

    # Compare only bars both sides consider defined; then assert the dropped set is small.
    dropped = 0
    worst = 0.0
    worst_at = None
    compared = 0
    for idx, t in enumerate(times):
        pv = py.iloc[idx]
        jv = js_by_time.get(t)
        if pd.isna(pv) or jv is None:
            # Warm-up bars are expected on both sides; past warm-up a one-sided
            # drop is a real disagreement about definedness and must not be hidden.
            if idx >= 14 and (pd.isna(pv) != (jv is None)):
                return False, f"{stem}: definedness mismatch at bar {idx} (py={pv!r}, js={jv!r})"
            if idx >= 14:
                dropped += 1
            continue
        compared += 1
        d = abs(float(pv) - float(jv))
        if d > worst:
            worst, worst_at = d, idx

    if compared == 0:
        return False, f"{stem}: nothing compared — the port produced no overlapping bars"
    definable = _definable_bars(df, 14)
    if definable and compared < MIN_COMPARED_FRAC * definable:
        return False, (f"{stem}: only {compared} of {definable} definable bars compared "
                       f"— the port is dropping bars it should be plotting")
    # Both sides are float64 doing the same sums in the same order; the only gap
    # expected is last-bit rounding, so the tolerance is set at that scale rather
    # than at a comfortable one that would let a real drift through.
    if worst > 1e-9:
        return False, f"{stem}: MISMATCH — worst |py-js| = {worst:.3e} at bar {worst_at}"
    return True, f"{stem}: {compared} bars, worst |py-js| = {worst:.1e}"


def test_mfi_parity_across_symbols():
    fails, msgs = [], []
    for stem in SYMBOLS:
        ok, msg = _check_one(stem)
        msgs.append(msg)
        if not ok:
            fails.append(msg)
    assert not fails, "; ".join(fails)


def test_extractor_still_finds_the_function():
    """Guards the slice itself: a rename in the HTML must fail loudly, not skip."""
    js = _extract_mfi_js()
    assert "mfiSeries" in js and js.rstrip().endswith("}")


if __name__ == "__main__":
    bad = 0
    for stem in SYMBOLS:
        ok, msg = _check_one(stem)
        print(("PASS " if ok else "FAIL ") + msg)
        bad += 0 if ok else 1
    print("PASS" if not bad else f"FAIL ({bad})")
    sys.exit(1 if bad else 0)
