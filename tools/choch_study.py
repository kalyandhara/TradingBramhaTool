#!/usr/bin/env python3
"""choch_study.py - does a bullish CHoCH select anything? (gate for the Opportunity pipeline)

Scored through the SAME harness as B-43/B-57/B-58 (`renko_regime_study._edge`,
`_rotation_p`, `_row`) over the deep bar cache (`cache/cardinality_deep`).

PRE-REGISTERED DESIGN (2026-10-07, written before the first run)
  WALK      the SMC swing walk of `choch_scan.bullish_choch` / `detect_bos_choch`,
            pivot_len 5: a pivot at j is knowable at j+5. Close > last confirmed
            swing high while trend != up = bullish CHoCH; while up = BOS. Close <
            last confirmed swing low flips trend down.
  ENTRY     next open after the signal bar; HORIZON 20 trading days.
  PRIMARY   signal   CHoCH bars
            baseline every bar on which structure is BEARISH going into the close
                     (the only state a CHoCH can fire from) - so the test is "does
                     the break select vs simply being in a downtrend", not a
                     re-measure of mean reversion.
            PASS     edge > 0 AND p_rot < 0.05, n >= 200.
  SCANNER   what the Scanner Hub card shows: any bar 0-4 sessions after a CHoCH
            that has not been invalidated, vs ALL bars. Decides nothing alone.
  DISPLACE  CHoCH with break-candle body >= 0.5 of range, vs bearish state.
  CONTRAST  CHoCH vs ALL bars - size of the illusion, never decisive.
  BOS       continuation breaks vs ALL bars - context.
  COSTS     none: signal and baseline are the same instrument, same hold.

CLI:  py -3 tools/choch_study.py [--horizon 20] [--cache DIR] [--verify]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import renko_regime_study as reg

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache" / "cardinality_deep"
WARMUP = 60
HORIZON = 20
PIVOT_LEN = 5
WINDOW = 5
MIN_BODY = 0.5
MIN_EVENTS = 200


def _load(path: Path):
    doc = json.loads(path.read_text(encoding="utf-8"))
    b = doc["bars"]
    f = lambda k: np.array([x[k] for x in b], float)
    return doc.get("symbol", path.stem.split("_")[0]), f("open"), f("high"), f("low"), f("close")


def walk(o, h, l, c, pivot_len=PIVOT_LEN):
    m = len(c)
    choch = np.zeros(m, bool); bos = np.zeros(m, bool); bear = np.zeros(m, bool)
    disp = np.zeros(m, bool); live = np.zeros(m, bool)
    sh = sl = None; trend = 0; last_choch = None
    for i in range(pivot_len * 2, m):
        j = i - pivot_len
        if j >= pivot_len:
            if h[j] == h[j - pivot_len: j + pivot_len + 1].max(): sh = h[j]
            if l[j] == l[j - pivot_len: j + pivot_len + 1].min(): sl = l[j]
        bear[i] = trend == -1
        if sh is not None and c[i] > sh:
            if trend != 1:
                choch[i] = True; last_choch = i
                rng = h[i] - l[i]
                disp[i] = rng > 0 and abs(c[i] - o[i]) / rng >= MIN_BODY
            else:
                bos[i] = True
            trend = 1; sh = None
        elif sl is not None and c[i] < sl:
            trend = -1; sl = None; last_choch = None
        live[i] = last_choch is not None and i - last_choch < WINDOW
    return choch, bos, bear, disp, live


def build_panel(paths, horizon):
    out = []
    for p in paths:
        sym, o, h, l, c = _load(p)
        m = len(c)
        if m < WARMUP + horizon + 3:
            continue
        fwd = np.full(m, np.nan)
        last = m - horizon - 2
        ok = o[WARMUP + 1:last + 2] > 0
        idx = np.arange(WARMUP, last + 1)[ok]
        fwd[idx] = (c[idx + 1 + horizon] / o[idx + 1] - 1.0) * 100.0
        choch, bos, bear, disp, live = walk(o, h, l, c)
        rng = np.zeros(m, bool); rng[WARMUP:last + 1] = True
        out.append({"sym": sym, "fwd": fwd, "all": rng, "choch": choch & rng,
                    "bos": bos & rng, "bear": bear & rng, "disp": (choch & disp) & rng,
                    "live": live & rng, "path": p, "ohlc": (o, h, l, c)})
    return out


def verify(panel):
    """Last-bar `live` must equal the shipped scanner on the full frame."""
    from choch_scan import bullish_choch
    agree = bad = 0; msgs = []
    for d in panel:
        o, h, l, c = d["ohlc"]
        df = pd.DataFrame({"open": o, "high": h, "low": l, "close": c})
        mine, _, _, _, live = walk(o, h, l, c)
        shipped = bullish_choch(df, lookback=10**9, within=WINDOW) is not None
        if bool(live[-1]) == shipped:
            agree += 1
        else:
            bad += 1; msgs.append(d["sym"])
    return agree, bad, msgs


def _arm(panel, key, mask_fn):
    r = reg._edge(panel, key, mask_fn)
    if r is None:
        return None, None, 0
    p, nrot = reg._rotation_p(panel, key, mask_fn, r["edge"])
    return r, p, nrot


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try: s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError): pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--horizon", type=int, default=HORIZON)
    ap.add_argument("--cache", type=str, default=None)
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    cache = Path(a.cache) if a.cache else CACHE
    paths = sorted(cache.glob("*_1d.json"))
    if not paths:
        sys.exit(f"no bars in {cache}")
    panel = build_panel(paths, a.horizon)
    ag, bad, msgs = verify(panel)
    print(f"bars {cache.name} | {len(panel)} names | horizon {a.horizon}d | pivot {PIVOT_LEN}")
    print(f"equivalence vs choch_scan.bullish_choch: {ag} agree, {bad} disagree {msgs[:8]}")
    if bad:
        sys.exit("ABORT - study walk and shipped scanner disagree")
    if a.verify:
        return 0
    allm = lambda d: d["all"]
    bearm = lambda d: d["bear"] | d["choch"]   # CHoCH bars are bearish going in
    arms = [("PRIMARY  CHoCH vs bearish state", "choch", bearm),
            ("SCANNER  live 0-4d vs ALL bars", "live", allm),
            ("DISPLACE CHoCH+body vs bearish", "disp", bearm),
            ("CONTRAST CHoCH vs ALL bars", "choch", allm),
            ("BOS      continuation vs ALL", "bos", allm)]
    res = {}
    for label, key, fn in arms:
        r, p, n = _arm(panel, key, fn)
        print(reg._row(label, r, p, n)); res[label.split()[0]] = (r, p)
    r, p = res["PRIMARY"]
    if r is None or r["n_sig"] < MIN_EVENTS:
        verdict = "INCONCLUSIVE - UNDERPOWERED"
    elif r["edge"] > 0 and p is not None and p < 0.05:
        verdict = "PASS"
    else:
        verdict = "FAIL"
    print(f"\nVERDICT (PRIMARY): {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
