#!/usr/bin/env python3
"""ew_structure_study.py - B-134 (unusual wave B) and B-135 (W-X-Y depth).

Runs EXACTLY the design pre-registered in Open-Backlog.md, section
"B-133-B-136 . Pre-registration - written 2026-10-08, BEFORE the scorer existed".
Nothing here may change that design; if something must change, the entry
changes first and says why.

Engine = the shipped elliott_wave.js through node (default options), daily bars
from cache/cardinality_deep. Events are dated at the `confirmedAt` bar of their
last pivot. Entry next open, 20d, long only. p = within-symbol label
permutation (2,000), two-sided.

CLI:  py -3 tools/ew_structure_study.py [--horizon 20] [--perms 2000]
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
WARMUP = 60
MIN_EVENTS = 200
BAND = (0.618, 0.786)

NODE = r"""
global.window = global; require(process.argv[2]);
const fs = require('fs');
const files = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const out = {};
for (const f of files) {
  const doc = JSON.parse(fs.readFileSync(f, 'utf8'));
  const bars = doc.bars.map(b => ({time: b.time, open: +b.open, high: +b.high,
                                   low: +b.low, close: +b.close, volume: +(b.volume || 0)}));
  const a = EW.analyze(bars);
  out[f] = {
    pivots: a.pivots.filter(p => !p.provisional).map(p => [p.idx, p.price, p.type, p.confirmedAt]),
    corr: a.correctives.filter(c => c.bullishParent && c.complete && c.final)
            .map(c => [c.points[3].confirmedAt, c.ratios.bAbnormal ? 1 : 0, c.ratios.bSlow ? 1 : 0]),
    cx: a.complex.filter(c => c.direction === 'down' && c.final).map(c => c.points[7].idx),
  };
}
process.stdout.write(JSON.stringify(out));
"""


def run_engine(paths: list[Path]) -> dict:
    with tempfile.TemporaryDirectory() as td:
        lst = Path(td) / "files.json"
        lst.write_text(json.dumps([str(p) for p in paths]))
        js = Path(td) / "run.js"
        js.write_text(NODE)
        r = subprocess.run(["node", str(js), str(HERE / "elliott_wave.js"), str(lst)],
                           capture_output=True, text=True)
    if r.returncode:
        sys.exit("node failed: " + r.stderr[:2000])
    return json.loads(r.stdout)


def fwd_returns(path: Path, horizon: int) -> np.ndarray:
    bars = json.loads(path.read_text(encoding="utf-8"))["bars"]
    o = np.array([b["open"] for b in bars], float)
    c = np.array([b["close"] for b in bars], float)
    m = len(c)
    f = np.full(m, np.nan)
    last = m - horizon - 2
    for t in range(WARMUP, last + 1):
        if o[t + 1] > 0:
            f[t] = (c[t + 1 + horizon] / o[t + 1] - 1.0) * 100.0
    return f


def b135_events(pivots: list, cx_y_idx: set) -> list[tuple[int, int]]:
    """[(t, is_wxy)] per the pre-registered baseline definition."""
    out = []
    for j in range(8, len(pivots)):
        idx, price, kind, conf = pivots[j]
        if kind != "low":
            continue
        win = pivots[j - 7:j]
        highs = [(k, p) for k, p in enumerate(win) if p[2] == "high"]
        if not highs:
            continue
        hk, H = max(highs, key=lambda kp: kp[1][1])
        h = j - 7 + hk
        if h - 1 < 0 or pivots[h - 1][2] != "low":
            continue
        L = pivots[h - 1][1]
        Hp = H[1]
        if Hp <= L:
            continue
        lows_since = [p[1] for p in pivots[h + 1:j] if p[2] == "low"]
        if lows_since and price > min(lows_since):
            continue
        r = (Hp - price) / (Hp - L)
        if BAND[0] <= r <= BAND[1]:
            out.append((conf, 1 if idx in cx_y_idx else 0))
    return out


def edge_and_p(groups: list[tuple[np.ndarray, np.ndarray]], perms: int, seed: int = 7):
    """groups = per-symbol (returns, labels). Edge = mean(sig) - mean(rest)."""
    rets = np.concatenate([g[0] for g in groups]) if groups else np.array([])
    labs = np.concatenate([g[1] for g in groups]) if groups else np.array([])
    if labs.sum() == 0 or (labs == 0).sum() == 0:
        return None
    obs = rets[labs == 1].mean() - rets[labs == 0].mean()
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(perms):
        lp = np.concatenate([rng.permutation(g[1]) for g in groups])
        e = rets[lp == 1].mean() - rets[lp == 0].mean()
        hits += abs(e) >= abs(obs)
    return {"n_sig": int(labs.sum()), "n_rest": int((labs == 0).sum()),
            "sig": float(rets[labs == 1].mean()), "rest": float(rets[labs == 0].mean()),
            "edge": float(obs), "p": hits / perms,
            "hit_sig": float((rets[labs == 1] > 0).mean() * 100),
            "hit_rest": float((rets[labs == 0] > 0).mean() * 100)}


def row(label, r):
    if r is None:
        return f"  {label:<40} (no events in one arm)"
    return (f"  {label:<40} n={r['n_sig']:<5d} vs {r['n_rest']:<6d} sig={r['sig']:+6.2f}%  "
            f"rest={r['rest']:+6.2f}%  edge={r['edge']:+6.2f}%  "
            f"hit={r['hit_sig']:4.1f}/{r['hit_rest']:4.1f}  p={r['p']:.3f}")


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try: s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError): pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--horizon", type=int, default=20)
    ap.add_argument("--perms", type=int, default=2000)
    a = ap.parse_args()
    paths = sorted(CACHE.glob("*_1d.json"))
    eng = run_engine(paths)

    g134, g134s, g135 = [], [], []
    all_fwd = []
    for pth in paths:
        e = eng.get(str(pth))
        if not e:
            continue
        f = fwd_returns(pth, a.horizon)
        all_fwd.append(f[np.isfinite(f)])
        ev = [(t, ab, sl) for t, ab, sl in e["corr"] if t is not None and t < len(f)
              and np.isfinite(f[t])]
        if ev:
            r = np.array([f[t] for t, _, _ in ev])
            g134.append((r, np.array([ab for _, ab, _ in ev])))
            g134s.append((r, np.array([sl for _, _, sl in ev])))
        ev5 = [(t, w) for t, w in b135_events(e["pivots"], set(e["cx"]))
               if t is not None and t < len(f) and np.isfinite(f[t])]
        if ev5:
            g135.append((np.array([f[t] for t, _ in ev5]), np.array([w for _, w in ev5])))

    print(f"bars {CACHE.name} | {len(paths)} names | horizon {a.horizon}d | "
          f"engine elliott_wave.js | perms {a.perms}")
    r134 = edge_and_p(g134, a.perms)
    r134s = edge_and_p(g134s, a.perms)
    r135 = edge_and_p(g135, a.perms)
    allm = float(np.concatenate(all_fwd).mean())
    print(row("B-134 PRIMARY unusual B vs normal B", r134))
    print(row("B-134 secondary slow B vs not", r134s))
    print(row("B-135 PRIMARY W-X-Y vs same-depth corr.", r135))
    if r135:
        base_all = (r135["sig"] * r135["n_sig"] + r135["rest"] * r135["n_rest"]) / \
                   (r135["n_sig"] + r135["n_rest"])
        print(f"  {'B-135 CONTRAST band events vs ALL bars':<40} "
              f"events={base_all:+6.2f}%  all bars={allm:+6.2f}%  diff={base_all - allm:+6.2f}%")

    def v134(r):
        if r is None or r["n_sig"] < MIN_EVENTS:
            return "INCONCLUSIVE - UNDERPOWERED"
        if r["p"] < 0.05:
            return "PASS (marks better outcomes)" if r["edge"] > 0 else "VALID WARNING (marks worse outcomes)"
        return "NULL - label only"

    def v135(r):
        if r is None or r["n_sig"] < MIN_EVENTS:
            return "INCONCLUSIVE - UNDERPOWERED"
        return "PASS" if (r["edge"] > 0 and r["p"] < 0.05) else "FAIL"

    print(f"\nVERDICT B-134: {v134(r134)}")
    print(f"VERDICT B-135: {v135(r135)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
