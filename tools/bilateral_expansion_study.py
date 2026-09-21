#!/usr/bin/env python3
"""bilateral_expansion_study.py — B-101/B-102: does a coil precede expansion?

PRE-REGISTERED in `analyses/Bilateral-Expansion-Pre-Registration`, committed
before this file ran. Nothing here decides a threshold; the page did.

── Why this cannot be the B-19 harness ───────────────────────────────────────
`Symmetrical Triangle (bilateral)` claims no direction, so the directional edge
the batch runner computes is not the test — a coil that resolves both ways
SHOULD measure near zero there, and reading that as "NO EDGE" would retire a
detector doing exactly what it says. What the pattern claims is EXPANSION: that
price is about to leave the range it has been compressing inside. The unit for
that is `backtest.absolute_move` (B-102), and this file is the walk around it.

── The three claims, as registered ───────────────────────────────────────────
  A (primary)  mean |forward move| from a coil vs from every eligible bar, both
               net of COST_INDIAN. Passes only with a positive edge at h=20,
               p<0.05, and the SIGN holding at 5/10/20/60.
  B            does the 50-75% apex band the card cites carry anything?
  C            is it actually bilateral? Up-share outside 40-60% at n>=200
               falsifies the framing, not just the edge.

B and C are reported as description when A fails. That is the multiple-
comparisons rule the page fixed in advance.

── The power extension (B-103) ───────────────────────────────────────────────
The first run (2026-09-20, 150 names × ~900 sessions) returned **28 signals
against the floor of 200** and therefore INCONCLUSIVE. Widening the sample is the
remedy the pre-registration itself prescribed for exactly that outcome, so
`--symbols` and `--days` exist to run the SAME analysis plan over more data. What
must not change is the plan: event, primary, horizons, pass bar and the claim-C
falsifier all stay as registered, and a run that reaches the floor reports
whatever it finds. Each run writes its own file under `cache/bilateral_expansion/`
so a later, wider run never overwrites the record of an earlier one.

CLI:
    py -3 -X utf8 tools/bilateral_expansion_study.py --run [--symbols 150] [--days 900]
    py -3 -X utf8 tools/bilateral_expansion_study.py            # print the newest run
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

# Only when run as a script: rewrapping stdout at IMPORT time closes the file
# pytest is capturing through, and the test module that pins this study's
# pre-registered thresholds has to import it.
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import backtest as bt
import scanner_templates as sc

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "cache" / "bilateral_expansion"


def _out_path(symbols: int, days: int) -> "Path":
    """One file per sample, named for it. A wider run is a SECOND result, not a
    replacement — overwriting would erase the underpowered run the wider one is
    supposed to be compared against."""
    return OUT_DIR / f"result_{symbols}x{days}.json"


def _newest() -> "Path | None":
    runs = sorted(OUT_DIR.glob("result_*.json"), key=lambda p: p.stat().st_mtime)
    return runs[-1] if runs else None

HORIZONS = (5, 10, 20, 60)
PRIMARY_H = 20
WARMUP = 220              # parity with scanner_plans / the shared harness
STRIDE = 5
MIN_GAP = bt.DEFAULT_MIN_GAP
MIN_N = 200               # below this the verdict is INCONCLUSIVE, never NULL
APEX_BAND = (0.50, 0.75)  # the band the card cites, tested rather than assumed


def _events(df, scan, max_h: int) -> list[dict]:
    """Detection bars for one symbol: a hit where the previous eval bar had none.

    The EVENT is detection, not breakout (pre-registration §The event). At a
    breakout the pattern has already resolved and the direction is known, which
    is a different and directional question.
    """
    out: list[dict] = []
    prev_hit = False
    skip_until = -1
    n = len(df)
    for t in range(WARMUP, n - max_h - 2, STRIDE):
        try:
            hit = scan(df.iloc[:t + 1])
        except Exception:
            hit = None
        fresh = bool(hit) and not prev_hit
        prev_hit = bool(hit)
        if not fresh or t < skip_until:
            continue
        skip_until = t + MIN_GAP
        out.append({
            "t": t,
            "apex_progress": (hit.get("apex_progress_pct") or 0.0) / 100.0,
            "up_entry": hit.get("up_entry"),
            "down_entry": hit.get("down_entry"),
        })
    return out


def _resolution(df, t: int, up: float | None, down: float | None,
                horizon: int = PRIMARY_H) -> str | None:
    """Which line broke first within the horizon — 'up', 'down' or None.

    Claim C. First TOUCH, not the sign of the move: a coil that breaks up and
    then fades still resolved upward, and scoring it by the h=20 sign would
    quietly turn a direction test into a momentum test.
    """
    if up is None or down is None:
        return None
    high = df["high"].to_numpy(float)
    low = df["low"].to_numpy(float)
    end = min(len(df) - 1, t + horizon)
    for i in range(t + 1, end + 1):
        hit_up = high[i] >= up
        hit_dn = low[i] <= down
        if hit_up and hit_dn:
            return "both"            # one bar spanned the whole coil; no order
        if hit_up:
            return "up"
        if hit_dn:
            return "down"
    return None


def run(symbols: list[str], fetch_fn, progress=None) -> dict[str, Any]:
    scan = sc.SCANNERS["Symmetrical Triangle (bilateral)"]["fn"]
    cm = bt.COST_INDIAN
    max_h = max(HORIZONS)

    sig: dict[int, list[float]] = {h: [] for h in HORIZONS}
    base: dict[int, list[float]] = {h: [] for h in HORIZONS}
    in_band: dict[int, list[float]] = {h: [] for h in HORIZONS}
    out_band: dict[int, list[float]] = {h: [] for h in HORIZONS}
    resolutions: list[str] = []
    n_sym = 0

    for i, sym in enumerate(symbols, 1):
        if progress:
            progress(i, len(symbols), sym)
        try:
            df = fetch_fn(sym)
        except Exception:
            continue
        if df is None or getattr(df, "empty", True):
            continue
        df = df.dropna(subset=["high", "low", "close"]).reset_index(drop=True)
        if len(df) < WARMUP + max_h + 10:
            continue
        n_sym += 1

        # Baseline: every eligible bar on the same stride, same entry/exit
        # timing. Identical treatment is what makes the comparison fair — the
        # signal arm is a SUBSET of these bars, not a different population.
        for t in range(WARMUP, len(df) - max_h - 2, STRIDE):
            for h in HORIZONS:
                v = bt.absolute_move(df, t, h, cost_model=cm)
                if v is not None:
                    base[h].append(v)

        for ev in _events(df, scan, max_h):
            t = ev["t"]
            band = APEX_BAND[0] <= ev["apex_progress"] <= APEX_BAND[1]
            for h in HORIZONS:
                v = bt.absolute_move(df, t, h, cost_model=cm)
                if v is None:
                    continue
                sig[h].append(v)
                (in_band if band else out_band)[h].append(v)
            r = _resolution(df, t, ev["up_entry"], ev["down_entry"])
            if r:
                resolutions.append(r)

    return {
        "n_symbols": n_sym,
        "n_signals": len(sig[PRIMARY_H]),
        "stride": STRIDE, "warmup": WARMUP, "min_gap": MIN_GAP,
        "cost_model": cm.label,          # a property, not a method
        "A": {str(h): _arm(sig[h], base[h]) for h in HORIZONS},
        "B": {str(h): _arm(in_band[h], out_band[h]) for h in HORIZONS},
        "C": {k: resolutions.count(k) for k in ("up", "down", "both")},
    }


def _arm(a: list[float], b: list[float]) -> dict[str, Any]:
    """Signal arm vs baseline arm — means, edge, Welch t-test."""
    if not a or not b:
        return {"n": len(a), "n_base": len(b), "edge": None}
    arr_a, arr_b = np.asarray(a, float), np.asarray(b, float)
    t_val, p_val = bt._ttest_ind(arr_a, arr_b)
    return {
        "n": len(a), "n_base": len(b),
        "mean": round(float(arr_a.mean()), 4),
        "mean_base": round(float(arr_b.mean()), 4),
        "edge": round(float(arr_a.mean() - arr_b.mean()), 4),
        "t": round(float(t_val), 3), "p": round(float(p_val), 4),
    }


def verdict(res: dict) -> str:
    """The pre-registered pass bar, applied mechanically."""
    n = res["n_signals"]
    if n < MIN_N:
        return f"INCONCLUSIVE — {n} signals, under the pre-registered floor of {MIN_N}"
    a = res["A"]
    prim = a[str(PRIMARY_H)]
    edges = [a[str(h)]["edge"] for h in HORIZONS if a[str(h)]["edge"] is not None]
    sign_stable = all(e > 0 for e in edges) or all(e < 0 for e in edges)
    if prim["edge"] is None:
        return "INCOMPLETE"
    if prim["edge"] > 0 and prim["p"] < 0.05 and all(e > 0 for e in edges):
        return "POSITIVE — a coil precedes a bigger move than a random bar"
    if prim["edge"] < 0 and prim["p"] < 0.05 and sign_stable:
        return "NEGATIVE — a coil precedes a SMALLER move than a random bar"
    return "NULL — no expansion effect at the pre-registered bar"


def report(res: dict) -> str:
    L = [f"Bilateral expansion — {res['n_symbols']} symbols, {res['n_signals']} coils, "
         f"stride {res['stride']}, {res['cost_model']}", ""]
    L.append("A. |move| vs every-bar baseline")
    L.append(f"{'h':>5}{'n':>7}{'coil%':>9}{'base%':>9}{'edge':>9}{'p':>9}")
    for h in HORIZONS:
        m = res["A"][str(h)]
        if m["edge"] is None:
            L.append(f"{h:>5}{m['n']:>7}{'n/a':>9}")
            continue
        L.append(f"{h:>5}{m['n']:>7}{m['mean']:>9.2f}{m['mean_base']:>9.2f}"
                 f"{m['edge']:>+9.2f}{m['p']:>9.3f}")
    L += ["", "B. inside the 50-75% apex band vs outside"]
    for h in HORIZONS:
        m = res["B"][str(h)]
        if m["edge"] is None:
            L.append(f"  @{h}d: n/a (n={m['n']} in-band, {m['n_base']} out)")
        else:
            L.append(f"  @{h}d: {m['mean']:.2f}% in-band (n={m['n']}) vs "
                     f"{m['mean_base']:.2f}% out (n={m['n_base']}), p={m['p']:.3f}")
    c = res["C"]
    tot = c["up"] + c["down"]
    L += ["", "C. resolution direction (first line touched, 20 bars)"]
    if tot:
        L.append(f"  up {c['up']} · down {c['down']} · same-bar both {c['both']} — "
                 f"up-share {100.0 * c['up'] / tot:.1f}%")
    else:
        L.append("  no resolutions inside the horizon")
    L += ["", f"VERDICT: {verdict(res)}"]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="B-101/B-102 — bilateral expansion test")
    ap.add_argument("--run", action="store_true", help="measure and cache")
    ap.add_argument("--symbols", type=int, default=150)
    ap.add_argument("--days", type=int, default=900)
    a = ap.parse_args()

    if a.run:
        import nse_universe as nu
        import screener_pipeline as sp
        syms = list(nu.symbols("nifty500"))[:a.symbols]
        res = run(syms, lambda s: sp.fetch_ohlcv(s, days=a.days),
                  progress=lambda i, n, s: print(f"  [{i}/{n}] {s}", end="\r", flush=True))
        res["symbols_requested"] = a.symbols
        res["days"] = a.days
        print()
        out = _out_path(a.symbols, a.days)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(res, indent=1, sort_keys=True), encoding="utf-8")
        print(f"cached -> {out}\n")
    else:
        newest = _newest()
        if newest is None:
            print("No result cached. Run with --run.")
            return 1
        print(f"({newest.name})\n")
        res = json.loads(newest.read_text(encoding="utf-8"))
    print(report(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
