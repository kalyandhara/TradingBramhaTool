#!/usr/bin/env python3
"""cycle_window_study.py - B-204: do measured cycle-trough windows catch troughs?

Runs EXACTLY the design pre-registered in trading-wiki/wiki/analyses/Open-Backlog.md,
section "B-204 . Pre-registration - written 2026-11-21, BEFORE the scorer existed".
Nothing here may change that design; if something must change, the entry
changes first and says why.

Engine = shipped elliott_wave.js computeZigzag (defaults) + cycles.js 1.2.0
dominantCycle, through node. Daily bars from cache/cardinality_deep.

CLI:  py -3 tools/cycle_window_study.py [--boot 2000]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache" / "cardinality_deep"
START, STEP, SETTLE, MIN_EVENTS = 120, 20, 30, 200

NODE = r"""
global.window = global; require(process.argv[2]); require(process.argv[3]);
const fs = require('fs');
const files = JSON.parse(fs.readFileSync(process.argv[4], 'utf8'));
const [START, STEP] = [+process.argv[5], +process.argv[6]];
const out = {};
for (const f of files) {
  const doc = JSON.parse(fs.readFileSync(f, 'utf8'));
  const bars = doc.bars.map(b => ({time: b.time, open: +b.open, high: +b.high,
                                   low: +b.low, close: +b.close, volume: +(b.volume || 0)}));
  const lows = EW.computeZigzag(bars).filter(p => p.type === 'low' && !p.provisional);
  const ev = [];
  for (let t = START; t < bars.length; t += STEP) {
    const known = lows.filter(p => p.confirmedAt != null && p.confirmedAt <= t);
    const dc = CY.dominantCycle(known, t);
    if (!dc || dc.overdue) continue;
    ev.push([t, dc.next.from, dc.next.to, dc.lastTrough, dc.median]);
  }
  out[f] = {n: bars.length, lows: lows.map(p => p.idx), ev, v: CY.VERSION};
}
process.stdout.write(JSON.stringify(out));
"""


def run_engine(paths: list[Path]) -> dict:
    with tempfile.TemporaryDirectory() as td:
        lst = Path(td) / "files.json"
        lst.write_text(json.dumps([str(p) for p in paths]))
        js = Path(td) / "run.js"
        js.write_text(NODE)
        r = subprocess.run(["node", str(js), str(HERE / "elliott_wave.js"), str(HERE / "cycles.js"),
                            str(lst), str(START), str(STEP)], capture_output=True, text=True)
    if r.returncode:
        sys.exit("node failed: " + r.stderr[:2000])
    return json.loads(r.stdout)


def score_event(t: int, nfrom: int, nto: int, last: int, median: float,
                lows: np.ndarray, n: int) -> tuple[int, float] | None:
    """(hit, baseline) for one decision bar per the pre-registration, or None if skipped."""
    a, b = max(nfrom, t + 1), nto
    if b < a or nto + SETTLE >= n:
        return None
    w = b - a + 1
    s0, s1 = t + 1, int(round(last + 2 * median))
    if s1 - s0 + 1 < w:
        return None
    has = np.zeros(s1 + 2, bool)
    ok = lows[(lows >= s0) & (lows <= s1)]
    has[ok] = True
    csum = np.concatenate([[0], np.cumsum(has[s0:s1 + 1])])
    starts = np.arange(0, (s1 - s0 + 1) - w + 1)
    base = float(((csum[starts + w] - csum[starts]) > 0).mean())
    hit = int(((lows >= a) & (lows <= b)).any())
    return hit, base


def cluster_boot(groups: list[np.ndarray], boots: int, seed: int = 7) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    k = len(groups)
    stats = []
    for _ in range(boots):
        pick = rng.integers(0, k, k)
        stats.append(np.concatenate([groups[i] for i in pick]).mean())
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try: s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError): pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--boot", type=int, default=2000)
    a = ap.parse_args()
    paths = sorted(CACHE.glob("*_1d.json"))
    eng = run_engine(paths)

    groups, hits, bases, meds = [], [], [], []
    ver = None
    for p in paths:
        e = eng.get(str(p))
        if not e:
            continue
        ver = e["v"]
        lows = np.array(e["lows"], int)
        d = []
        for t, nf, nt, last, med in e["ev"]:
            r = score_event(t, nf, nt, last, med, lows, e["n"])
            if r is None:
                continue
            d.append(r[0] - r[1]); hits.append(r[0]); bases.append(r[1]); meds.append(med)
        if d:
            groups.append(np.array(d, float))

    n = len(hits)
    print(f"bars {CACHE.name} | {len(paths)} files | cycles.js {ver} | start {START} step {STEP} "
          f"| boot {a.boot}")
    if n == 0:
        print("VERDICT B-204: INCONCLUSIVE - no events"); return 0
    edge = (np.mean(hits) - np.mean(bases)) * 100
    lo, hi = (x * 100 for x in cluster_boot(groups, a.boot))
    print(f"  events {n} in {len(groups)} symbols | median cycle {np.median(meds):.1f} bars")
    print(f"  hit rate {np.mean(hits) * 100:.1f}%  baseline {np.mean(bases) * 100:.1f}%  "
          f"edge {edge:+.2f} pts  95% CI [{lo:+.2f}, {hi:+.2f}]")
    if n < MIN_EVENTS:
        v = "INCONCLUSIVE - UNDERPOWERED"
    else:
        v = "PASS" if (edge > 0 and lo > 0) else "FAIL"
    print(f"\nVERDICT B-204: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
