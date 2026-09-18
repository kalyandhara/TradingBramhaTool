#!/usr/bin/env python3
"""flag_pole_edge.py — does the flag & pole breakout pay? (B-92)

Phase 2 of the pre-registered test in `analyses/Flag-Pole-Pre-Registration`.
The detector is `flag_pole.detect_flag_pole`, built by PR-3 explicitly to be
measurable; this is the measurement.

── The event is the BREAKOUT, not the pattern ────────────────────────────────
`detect_flag_pole` returns a pattern whenever one exists, broken or not, and an
unbroken flag is a WATCH that nobody trades. The shared `backtest_scanner` walks
every bar and would count each watch bar as a signal, measuring something no one
acts on. So the signal here is the **transition**: `broken` becoming true having
been false on the previous evaluated bar.

Counted before any scoring: patterns are present on ~5.1% of bars (bull) and
broken out on **0.45%**. This scores the selective half.

── Three separable claims ────────────────────────────────────────────────────
**A. Edge.** Forward return from the next bar's open, minus the every-bar
baseline over the same symbols and window, `COST_INDIAN` on both arms.

**B. The measured move.** The card's target is the pole height projected and its
stop is the far flag boundary. Which is hit first? A setup can have positive edge
while its stated target is fantasy, so this is reported whatever A says.

**C. Volume.** `High Tight Flag` rejects a rising-volume flag; B-92 measured
`vol_contract` instead of gating on it and promised "a later test can ask whether
it matters". This is that test, and it is **non-decisive** -- it cannot rescue a
failed primary.

── The bear half ────────────────────────────────────────────────────────────
`backtest._simulate_plan` is long-only, so the inverted flag cannot go through it.
Bear signals are scored as **plain long forward returns where NEGATIVE means the
pattern had teeth**, as `evwma_vwap_macd_backtest` scores its crossunders, and
their plans are walked with the mirror rule.

CLI:
  py -3 -X utf8 tools/flag_pole_edge.py --symbols 300
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

import numpy as np

import backtest as bt
import flag_pole as fp

HERE = Path(__file__).resolve().parent
OUT = HERE / "cache" / "flag_pole_edge.json"

HORIZONS = (5, 10, 20, 60)
PRIMARY_H = 20

#: Pre-registered floor per direction. Below it: INCONCLUSIVE, never a null.
FLOOR = 200

#: Outer limit on the plan walk. The card names no time stop, so this is the
#: measurement horizon rather than a rule -- a trade still open at 60 bars is
#: reported as a timeout, not as a win or a loss.
MAX_PLAN_BARS = 60

#: Bars of history before the first evaluation. The detector needs WINDOW+ATR_N.
WARMUP = fp.WINDOW + fp.ATR_N + 5


def _fwd(o: np.ndarray, c: np.ndarray, t: int, h: int, cm) -> Optional[float]:
    """Forward % from the NEXT bar's open to the close h bars later, net of cost."""
    if t + 1 + h > len(c) - 1 or not (o[t + 1] > 0):
        return None
    entry, exit_ = float(o[t + 1]), float(c[t + 1 + h])
    return (exit_ / entry - 1.0) * 100.0 - cm.round_trip_pct(entry, exit_)


def walk_plan(h: np.ndarray, l: np.ndarray, c: np.ndarray, entry_idx: int,
              entry: float, stop: float, target: float, bull: bool,
              cm, max_bars: int = MAX_PLAN_BARS) -> Optional[dict]:
    """Target-or-stop-first walk, both directions. Returns outcome + realised R.

    Conservative tie-break, inherited from `backtest._simulate_plan`: when one
    bar's range spans both levels, the STOP is assumed to have filled first.
    Never credit a win daily bars cannot prove came first.
    """
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    end = min(len(c) - 1, entry_idx + max_bars)
    for i in range(entry_idx, end + 1):
        hit_stop = (l[i] <= stop) if bull else (h[i] >= stop)
        hit_tgt = (h[i] >= target) if bull else (l[i] <= target)
        if hit_stop:
            cost = entry * cm.round_trip_pct(entry, stop) / 100.0
            r = ((stop - entry) if bull else (entry - stop)) - cost
            return {"outcome": "stop", "r": r / risk, "bars": i - entry_idx}
        if hit_tgt:
            cost = entry * cm.round_trip_pct(entry, target) / 100.0
            r = ((target - entry) if bull else (entry - target)) - cost
            return {"outcome": "target", "r": r / risk, "bars": i - entry_idx}
    px = float(c[end])
    cost = entry * cm.round_trip_pct(entry, px) / 100.0
    r = ((px - entry) if bull else (entry - px)) - cost
    return {"outcome": "timeout", "r": r / risk, "bars": end - entry_idx}


def collect(symbols, fetch_fn, stride: int = 1,
            progress=None) -> dict[str, Any]:
    """Walk every symbol, record fresh breakouts and the baseline."""
    cm = bt.COST_INDIAN
    sig: dict[str, list[dict]] = {"bull": [], "bear": []}
    base: dict[int, list[float]] = {h: [] for h in HORIZONS}
    n_sym = 0

    syms = list(symbols)
    for n, sym in enumerate(syms, 1):
        if progress:
            progress(n, len(syms), sym)
        try:
            df = fetch_fn(sym)
        except Exception:
            continue
        if df is None or getattr(df, "empty", True) or len(df) < WARMUP + 80:
            continue
        df = df.dropna(subset=["high", "low", "close"]).reset_index(drop=True)
        if len(df) < WARMUP + 80 or "open" not in df.columns:
            continue
        n_sym += 1
        o = df["open"].to_numpy(float)
        h = df["high"].to_numpy(float)
        l = df["low"].to_numpy(float)
        c = df["close"].to_numpy(float)
        last_eval = len(c) - max(HORIZONS) - 2

        # Baseline: every eligible bar, identical entry/exit timing to a signal.
        for t in range(WARMUP, last_eval, 5):
            for hz in HORIZONS:
                v = _fwd(o, c, t, hz, cm)
                if v is not None:
                    base[hz].append(v)

        # The detector reads only its last WINDOW bars (it does `df.tail(window)`
        # internally) and needs WINDOW+ATR_N rows to clear its length guard. So
        # the slice handed in is exactly that, not the whole history: 35x faster,
        # and verified identical on every value field the study reads --
        # `test_flag_pole_edge.py` pins it against the full-frame call.
        need = fp.WINDOW + fp.ATR_N
        prev = {"bull": False, "bear": False}
        for t in range(WARMUP, last_eval, max(1, stride)):
            sub = df.iloc[t + 1 - need:t + 1]
            for d in ("bull", "bear"):
                try:
                    g = fp.detect_flag_pole(sub, direction=d)
                except Exception:
                    g = None
                broken = bool(g and g["broken"])
                # The EVENT is the transition into broken, not the state.
                fresh = broken and not prev[d]
                prev[d] = broken
                if not fresh:
                    continue
                rec: dict[str, Any] = {
                    "symbol": sym, "i": t, "direction": d,
                    "pole_atr": g["pole_atr"], "retrace": g["retrace"],
                    "vol_contract": g["vol_contract"], "rr": g["rr"],
                }
                for hz in HORIZONS:
                    rec[f"fwd{hz}"] = _fwd(o, c, t, hz, cm)
                entry = float(o[t + 1]) if t + 1 < len(o) else None
                if entry and entry > 0:
                    # The plan's levels come from the DETECTOR, but the trade is
                    # entered at the next open -- so a gap through the stop is a
                    # real outcome and is not smoothed away.
                    pl = walk_plan(h, l, c, t + 1, entry, g["stop"], g["target"],
                                   d == "bull", cm)
                    if pl:
                        rec["plan"] = pl
                sig[d].append(rec)
    return {"symbols_used": n_sym, "symbols_requested": len(syms),
            "stride": stride, "signals": sig,
            "baseline": {str(k): v for k, v in base.items()}}


def _tt(arr: list[float]) -> dict:
    a = np.array([x for x in arr if x is not None], float)
    if len(a) < 3:
        return {"n": len(a), "mean": None, "p": None}
    t, p = bt._ttest_1samp(a, 0.0)
    return {"n": int(len(a)), "mean": float(a.mean()), "t": float(t), "p": float(p)}


def score(res: dict) -> dict:
    out: dict[str, Any] = {"symbols_used": res["symbols_used"], "directions": {}}
    base = {int(k): np.array(v, float) for k, v in res["baseline"].items()}
    out["baseline"] = {h: (round(float(base[h].mean()), 3) if len(base[h]) else None)
                       for h in HORIZONS}
    out["baseline_n"] = {h: int(len(base[h])) for h in HORIZONS}

    for d, rows in res["signals"].items():
        per_h = {}
        for h in HORIZONS:
            vals = [r.get(f"fwd{h}") for r in rows]
            vals = [v for v in vals if v is not None]
            b = float(base[h].mean()) if len(base[h]) else 0.0
            edge = [v - b for v in vals]
            per_h[h] = {
                "n": len(vals),
                "mean": round(float(np.mean(vals)), 3) if vals else None,
                "baseline": round(b, 3),
                "edge": round(float(np.mean(edge)), 3) if edge else None,
                "hit_rate": round(100.0 * sum(v > 0 for v in vals) / len(vals), 1) if vals else None,
                **{k: (round(v, 4) if isinstance(v, float) else v)
                   for k, v in _tt(edge).items() if k in ("p", "t")},
            }
        plans = [r["plan"] for r in rows if r.get("plan")]
        n_p = len(plans)
        outcomes = [p["outcome"] for p in plans]
        rs = [p["r"] for p in plans]
        # Claim C: does volume contraction separate winners from losers?
        dry = [r for r in rows if (r.get("vol_contract") or 0) > 0]
        wet = [r for r in rows if (r.get("vol_contract") or 0) <= 0]
        def _m(sub):
            v = [r.get(f"fwd{PRIMARY_H}") for r in sub]
            v = [x for x in v if x is not None]
            return {"n": len(v), "mean": round(float(np.mean(v)), 3) if v else None}
        out["directions"][d] = {
            "n_signals": len(rows), "horizons": per_h,
            "plan": {
                "n": n_p,
                "target_pct": round(100.0 * outcomes.count("target") / n_p, 1) if n_p else None,
                "stop_pct": round(100.0 * outcomes.count("stop") / n_p, 1) if n_p else None,
                "timeout_pct": round(100.0 * outcomes.count("timeout") / n_p, 1) if n_p else None,
                "avg_r": round(float(np.mean(rs)), 3) if rs else None,
                "median_bars": int(np.median([p["bars"] for p in plans])) if plans else None,
            },
            "volume": {"dried": _m(dry), "rose": _m(wet)},
        }
    return out


def verdict(scored: dict, direction: str = "bull") -> tuple[str, str]:
    """The pre-registered rule, applied mechanically."""
    d = scored["directions"].get(direction)
    if not d:
        return "NO DATA", "no signals collected"
    h = d["horizons"].get(PRIMARY_H) or {}
    n, edge, p = h.get("n", 0), h.get("edge"), h.get("p")
    if n < FLOOR:
        return ("INCONCLUSIVE - UNDERPOWERED",
                f"{n} signals against a floor of {FLOOR}")
    if edge is None or p is None:
        return "INCONCLUSIVE", "edge or p could not be computed"
    # The bear half is scored as a LONG return, so a negative mean is the win --
    # but the pre-registered rule is stated on EDGE, and for a short the edge
    # that matters is the mirror. Reported explicitly rather than sign-flipped
    # silently, so the table and the verdict cannot disagree.
    if direction == "bear":
        if edge < 0 and p < 0.05:
            return "PASS (bear: negative edge = teeth)", f"edge {edge:+.2f}%, p {p:.3f}"
        if edge > 0 and p < 0.05:
            return "INVERTED", f"edge {edge:+.2f}%, p {p:.3f} - breakdowns went UP"
        return "NULL", f"edge {edge:+.2f}%, p {p:.3f}"
    if edge > 0 and p < 0.05:
        return "PASS", f"edge {edge:+.2f}%, p {p:.3f}"
    if edge < 0 and p < 0.05:
        return "INVERTED", f"edge {edge:+.2f}%, p {p:.3f} - do NOT ship the mirror"
    return "NULL", f"edge {edge:+.2f}%, p {p:.3f}"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # pragma: no cover
        pass
    ap = argparse.ArgumentParser(description="B-92 - flag & pole breakout edge")
    ap.add_argument("--symbols", type=int, default=300)
    ap.add_argument("--stride", type=int, default=1)
    a = ap.parse_args()

    import nse_universe as nu
    import screener_pipeline as sp
    syms = list(nu.symbols("nifty500"))[:a.symbols]

    def _p(i, n, sym):
        print(f"  [{i}/{n}] {sym}        ", end="\r", flush=True)

    res = collect(syms, lambda s: sp.fetch_ohlcv(s, days=1500),
                  stride=a.stride, progress=_p)
    print()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(score(res), indent=1), encoding="utf-8")
    s = score(res)

    print(f"\n{s['symbols_used']} symbols\n")
    for d in ("bull", "bear"):
        dd = s["directions"][d]
        print(f"=== {d.upper()}  ({dd['n_signals']} breakouts) ===")
        print(f"{'h':>4} {'n':>6} {'mean%':>8} {'base%':>8} {'edge%':>8} "
              f"{'hit%':>7} {'p':>8}")
        for h in HORIZONS:
            r = dd["horizons"][h]
            p = "-" if r.get("p") is None else f"{r['p']:.3f}"
            star = "  <- primary" if h == PRIMARY_H else ""
            print(f"{h:>4} {r['n']:>6} {r['mean']:>8} {r['baseline']:>8} "
                  f"{r['edge']:>8} {r['hit_rate']:>7} {p:>8}{star}")
        pl = dd["plan"]
        print(f"  PLAN  n={pl['n']}  target {pl['target_pct']}%  "
              f"stop {pl['stop_pct']}%  timeout {pl['timeout_pct']}%  "
              f"avg R {pl['avg_r']}  median {pl['median_bars']} bars")
        v = dd["volume"]
        print(f"  VOLUME (non-decisive)  dried n={v['dried']['n']} "
              f"{v['dried']['mean']}%   rose n={v['rose']['n']} {v['rose']['mean']}%")
        vv, why = verdict(s, d)
        print(f"  VERDICT: {vv}\n    {why}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
