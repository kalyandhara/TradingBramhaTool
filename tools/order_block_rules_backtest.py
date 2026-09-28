"""Measure the three unmeasured Order Block rules B-76 shipped onto the chart.

Pre-registered in ``analyses/Order-Block-Rules-Pre-Registration`` — read that
first; the hypotheses, the floor and the decision rule (including what happens on
a null) were fixed before any forward return was looked at.

    A  target selection  — opposing zone vs displacement extension vs flat 2R
    B  stacked-zone bias — does the .ob-info lean predict direction?
    C  rejection entry   — early (wick) vs confirmed (cross) retests

Protocol follows ``analyses/Backtest-Harness`` so the numbers sit on the same
page as the six scanners already measured there: point-in-time slices, next-bar
entry, baseline = random entry in the same tape, pessimistic tie-break, costs
gross AND net, t-tests, thin samples flagged rather than hidden.

Two deliberate departures from ``backtest.backtest_scanner``, both forced:

  * **Direction-aware simulation.** ``backtest._simulate_plan`` is long-only and
    returns None for a short plan. Half the rules under test are bearish, so a
    long-only simulator would measure the bullish half and call it the rule.
  * **Stride 5 with same-bar-only recording.** An event is recorded only when its
    defining bar IS ``t``. Detecting at ``t > m`` and back-dating the event would
    drop events on zones violated in between — the detector's retest pass skips
    violated zones — which is survivorship, not sampling. The stride costs an
    unbiased 1-in-5 sample and buys correctness.

Run headless (~15 min over LIQUID_50):

    python tools/order_block_rules_backtest.py
    python tools/order_block_rules_backtest.py --symbols 12 --stride 10
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

import backtest as bt
import scanner_templates as sc

HORIZONS = (5, 10, 20, 60)
STRIDE = 5
WARMUP = 250          # detect_order_blocks needs pivot_len*4+20; 250 is generous
PIVOT_LEN = 6         # the /api/order_blocks daily default
MAX_FILL_BARS = 40    # Rule A: how long a pending limit entry stays live
MAX_HOLD_BARS = 60    # …and how long the filled trade may run
THIN = 30             # below this, directional-only (harness convention)

# Raw per-run output. cache/, not the tools/ root: each pass writes ~6.5MB and the
# repo .gitignore swallows *.json, so writing beside the source would pile up
# invisibly. Same home as pmax_plan_study's cardinality cache.
OUT_DIR = Path(__file__).resolve().parent / "cache" / "ob_rules"


# ── direction-aware plan simulation ──────────────────────────────────────────
def simulate(df: pd.DataFrame, entry_idx: int, entry: float, stop: float,
             target: float, direction: str, cost_model,
             max_bars: int = MAX_HOLD_BARS) -> dict | None:
    """Stop-or-target-first walk forward, long OR short.

    Mirrors ``backtest._simulate_plan`` including its pessimistic tie-break (a
    bar spanning both levels counts as the stop) — the short side is the exact
    mirror, never a sign flip applied to a long result.
    """
    risk = (entry - stop) if direction == "bull" else (stop - entry)
    if risk <= 0:
        return None
    n = len(df)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)
    end = min(n - 1, entry_idx + max_bars)
    if entry_idx >= n:
        return None

    for i in range(entry_idx, end + 1):
        if direction == "bull":
            hit_stop, hit_tgt = low[i] <= stop, high[i] >= target
        else:
            hit_stop, hit_tgt = high[i] >= stop, low[i] <= target
        if hit_stop:
            cost = entry * cost_model.round_trip_pct(entry, stop) / 100.0
            r = ((stop - entry) if direction == "bull" else (entry - stop))
            return {"outcome": "stop", "r": (r - cost) / risk, "bars": i - entry_idx}
        if hit_tgt:
            cost = entry * cost_model.round_trip_pct(entry, target) / 100.0
            r = ((target - entry) if direction == "bull" else (entry - target))
            return {"outcome": "target", "r": (r - cost) / risk, "bars": i - entry_idx}

    exit_px = close[end]
    cost = entry * cost_model.round_trip_pct(entry, exit_px) / 100.0
    r = ((exit_px - entry) if direction == "bull" else (entry - exit_px))
    return {"outcome": "open", "r": (r - cost) / risk, "bars": end - entry_idx}


def pending_limit_fill(df: pd.DataFrame, start_idx: int, entry: float,
                       direction: str, max_wait: int = MAX_FILL_BARS) -> int | None:
    """First bar at/after ``start_idx`` whose range touches ``entry``, or None.

    Rule A's plan is a limit at the zone edge, not a market order — measuring it
    as a market fill at the break bar would test a trade the overlay never
    proposed."""
    n = len(df)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    for i in range(start_idx, min(n, start_idx + max_wait)):
        if low[i] <= entry <= high[i]:
            return i
    return None


def fwd_returns(df: pd.DataFrame, t: int, direction: str, cost_model) -> dict:
    """Signed forward return per horizon: entry at t+1 open, exit at close.

    Signed by ``direction`` so a bearish signal that precedes a fall scores
    POSITIVE — otherwise every short-side rule would read as an inverted long.
    """
    close = df["close"].to_numpy(dtype=float)
    openp = (df["open"].to_numpy(dtype=float) if "open" in df.columns else close)
    out = {}
    e = openp[t + 1]
    if e <= 0:
        return out
    for h in HORIZONS:
        if t + 1 + h >= len(df):
            continue
        fwd = close[t + 1 + h]
        raw = (fwd / e - 1.0) * 100.0
        if direction == "bear":
            raw = -raw
        out[h] = raw - cost_model.round_trip_pct(e, fwd)
    return out


# ── the replay ───────────────────────────────────────────────────────────────
def run(symbols: list[str], days: int = 1500, stride: int = STRIDE,
        cost_model=None, verbose: bool = True) -> dict:
    import screener_pipeline as sp
    cm = cost_model or bt.COST_GROSS

    # Rule A: paired R per target variant, keyed by variant name.
    a_r: dict[str, list[float]] = defaultdict(list)
    a_outcome: dict[str, list[str]] = defaultdict(list)
    a_unfilled = 0
    a_plans = 0
    # Rule B: forward returns bucketed by lean sign and by stack count.
    b_by_lean: dict[str, dict[int, list[float]]] = {
        "bull": defaultdict(list), "bear": defaultdict(list)}
    b_by_stack: dict[int, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    # Rule C: forward returns and R by retest kind.
    c_fwd: dict[str, dict[int, list[float]]] = {
        "early": defaultdict(list), "confirmed": defaultdict(list)}
    c_r: dict[str, list[float]] = defaultdict(list)
    # Baseline: every eligible bar, unsigned (the coin-flip entry).
    base: dict[int, list[float]] = defaultdict(list)

    n_syms = 0
    total_calls = 0
    t_start = time.time()

    for si, sym in enumerate(symbols):
        try:
            df = sp.fetch_ohlcv(sym, days=days)
        except Exception:
            continue
        if df is None or df.empty:
            continue
        df = df.dropna(subset=["high", "low", "close", "volume"]).reset_index(drop=True)
        n = len(df)
        if n < WARMUP + max(HORIZONS) + 5:
            continue
        n_syms += 1
        close = df["close"].to_numpy(dtype=float)
        openp = (df["open"].to_numpy(dtype=float) if "open" in df.columns else close)
        last_eval = n - max(HORIZONS) - 2

        # Baseline over the identical bar range and timing as the signals.
        for t in range(WARMUP, last_eval + 1):
            e = openp[t + 1]
            if e <= 0:
                continue
            for h in HORIZONS:
                fwd = close[t + 1 + h]
                base[h].append((fwd / e - 1.0) * 100.0 - cm.round_trip_pct(e, fwd))

        for t in range(WARMUP, last_eval + 1, stride):
            sub = df.iloc[:t + 1]
            try:
                zones, retests = sc.detect_order_blocks(sub, pivot_len=PIVOT_LEN)
            except Exception:
                continue
            total_calls += 1
            live = [z for z in zones if z["state"] != "violated"]

            # ── Rule B — the lean as the gauge computes it, at every stride bar
            if live:
                def tally(d):
                    zs = [z for z in live if z["dir"] == d]
                    fresh = sum(1 for z in zs if z["state"] == "fresh")
                    return len(zs), fresh * 2 + (len(zs) - fresh)
                nb, wb = tally("bull")
                nr, wr = tally("bear")
                lean = wb - wr
                if lean != 0:
                    d = "bull" if lean > 0 else "bear"
                    stack = max(nb, nr)
                    fr = fwd_returns(df, t, d, cm)
                    for h, v in fr.items():
                        b_by_lean[d][h].append(v)
                        b_by_stack[min(stack, 3)][h].append(v)

            # ── Rule A — zones whose BREAK bar is exactly t (same-bar only)
            for z in live:
                if z.get("break_idx") != t or z.get("target") is None:
                    continue
                a_plans += 1
                fill = pending_limit_fill(df, t + 1, z["entry"], z["dir"])
                if fill is None:
                    a_unfilled += 1
                    continue
                risk = (abs(z["entry"] - z["stop"]))
                variants = {
                    "opposing_zone": z["target"],
                    "displacement": z.get("ext"),
                    "flat_2R": (z["entry"] + 2 * risk if z["dir"] == "bull"
                                else z["entry"] - 2 * risk),
                }
                for name, tgt in variants.items():
                    if tgt is None:
                        continue
                    # A target on the wrong side of entry is not a target.
                    if z["dir"] == "bull" and tgt <= z["entry"]:
                        continue
                    if z["dir"] == "bear" and tgt >= z["entry"]:
                        continue
                    r = simulate(df, fill, z["entry"], z["stop"], tgt, z["dir"], cm)
                    if r:
                        a_r[name].append(r["r"])
                        a_outcome[name].append(r["outcome"])

            # ── Rule C — retests whose bar is exactly t (same-bar only)
            for rt in retests:
                if rt.get("idx") != t:
                    continue
                kind = rt.get("kind", "confirmed")
                fr = fwd_returns(df, t, rt["dir"], cm)
                for h, v in fr.items():
                    c_fwd[kind][h].append(v)
                # R using the retest's OWN zone's shipped plan, entered next
                # bar open. Joined on ob_idx — matching on direction alone picks
                # an arbitrary same-side zone and measures a different trade.
                z = next((q for q in live
                          if q["ob_idx"] == rt.get("ob_idx")
                          and q.get("target") is not None), None)
                if z:
                    sim = simulate(df, t + 1, openp[t + 1], z["stop"], z["target"],
                                   z["dir"], cm)
                    if sim:
                        c_r[kind].append(sim["r"])

        if verbose:
            el = time.time() - t_start
            print(f"  [{si+1}/{len(symbols)}] {sym:<14} calls={total_calls:<6} "
                  f"A={a_plans} C={sum(len(v) for v in c_r.values())} "
                  f"{el:.0f}s", flush=True)

    return {
        "n_symbols": n_syms, "stride": stride, "days": days,
        "cost": type(cm).__name__,
        "a": {"r": dict(a_r), "outcome": dict(a_outcome),
              "plans": a_plans, "unfilled": a_unfilled},
        "b": {"lean": {k: dict(v) for k, v in b_by_lean.items()},
              "stack": {k: dict(v) for k, v in b_by_stack.items()}},
        "c": {"fwd": {k: dict(v) for k, v in c_fwd.items()}, "r": dict(c_r)},
        "baseline": dict(base),
    }


# ── reporting ────────────────────────────────────────────────────────────────
def _stat(arr):
    a = np.asarray(arr, dtype=float)
    if a.size == 0:
        return None
    tt = bt._ttest_1samp(a)
    return {"n": int(a.size), "mean": float(a.mean()),
            "t": tt[0] if isinstance(tt, tuple) else tt.get("t"),
            "p": tt[1] if isinstance(tt, tuple) else tt.get("p")}


def _fmt(s, thin=THIN):
    if s is None:
        return "     —"
    flag = "  ⚠thin" if s["n"] < thin else ""
    p = s.get("p")
    ptxt = f"p={p:.3f}" if isinstance(p, float) else "p=—"
    return f"{s['mean']:+7.3f}  n={s['n']:<5} {ptxt}{flag}"


def report(res: dict) -> str:
    L = []
    L.append("=" * 78)
    L.append(f"ORDER BLOCK RULES — measured  ({res['n_symbols']} symbols, "
             f"stride {res['stride']}, {res['days']}d, cost={res['cost']})")
    L.append("Pre-registered: analyses/Order-Block-Rules-Pre-Registration")
    L.append("=" * 78)

    base = {h: _stat(v) for h, v in res["baseline"].items()}
    L.append("\nBASELINE (random entry, same tape, same timing)")
    for h in HORIZONS:
        b = base.get(h) or base.get(str(h))
        L.append(f"  {h:>3}d  {_fmt(b)}")

    # ── A
    L.append("\n" + "-" * 78)
    L.append("RULE A — target selection (paired: same zone, same entry, same stop)")
    a = res["a"]
    L.append(f"  plans {a['plans']}, unfilled limit entries {a['unfilled']}")
    for name in ("opposing_zone", "displacement", "flat_2R"):
        rs = a["r"].get(name, [])
        s = _stat(rs)
        oc = a["outcome"].get(name, [])
        hit = (100.0 * sum(1 for o in oc if o == "target") / len(oc)) if oc else 0.0
        L.append(f"  {name:<15} R {_fmt(s)}   target-hit {hit:5.1f}%")
    base_v = a["r"].get("flat_2R", [])
    for name in ("opposing_zone", "displacement"):
        v = a["r"].get(name, [])
        if len(v) > 5 and len(base_v) > 5:
            m = min(len(v), len(base_v))
            d = np.asarray(v[:m]) - np.asarray(base_v[:m])
            s = _stat(d)
            L.append(f"  paired Δ vs flat_2R: {name:<15} {_fmt(s)}")

    # ── B
    L.append("\n" + "-" * 78)
    L.append("RULE B — stacked-zone bias (signed by lean; + = lean was right)")
    for d in ("bull", "bear"):
        for h in HORIZONS:
            v = res["b"]["lean"][d].get(h) or res["b"]["lean"][d].get(str(h)) or []
            L.append(f"  {d:<5} {h:>3}d  {_fmt(_stat(v))}")
    L.append("  by stack count (20d):")
    for k in sorted(res["b"]["stack"], key=lambda x: int(x)):
        v = res["b"]["stack"][k].get(20) or res["b"]["stack"][k].get("20") or []
        lbl = f"{k}×" + ("+" if int(k) >= 3 else "")
        L.append(f"    {lbl:<4} {_fmt(_stat(v))}")

    # ── C
    L.append("\n" + "-" * 78)
    L.append("RULE C — early (wick rejection) vs confirmed (cross) retest")
    for kind in ("early", "confirmed"):
        for h in HORIZONS:
            v = res["c"]["fwd"][kind].get(h) or res["c"]["fwd"][kind].get(str(h)) or []
            L.append(f"  {kind:<10} {h:>3}d  {_fmt(_stat(v))}")
        L.append(f"  {kind:<10}   R  {_fmt(_stat(res['c']['r'].get(kind, [])))}")
    e20 = res["c"]["fwd"]["early"].get(20) or res["c"]["fwd"]["early"].get("20") or []
    c20 = res["c"]["fwd"]["confirmed"].get(20) or res["c"]["fwd"]["confirmed"].get("20") or []
    if len(e20) > 2 and len(c20) > 2:
        tt = bt._ttest_ind(np.asarray(e20, float), np.asarray(c20, float))
        L.append(f"  early vs confirmed @20d: {tt}")
    L.append("=" * 78)
    return "\n".join(L)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:]
    nsym = 50
    stride = STRIDE
    if "--symbols" in argv:
        nsym = int(argv[argv.index("--symbols") + 1])
    if "--stride" in argv:
        stride = int(argv[argv.index("--stride") + 1])
    syms = bt.LIQUID_50[:nsym]
    print(f"universe {len(syms)} names, stride {stride}\n", flush=True)
    for cm, tag in ((bt.COST_GROSS, "GROSS"), (bt.COST_INDIAN, "NET")):
        print(f"\n### {tag}", flush=True)
        res = run(syms, stride=stride, cost_model=cm)
        print(report(res))
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out = OUT_DIR / f"ob_rules_{tag.lower()}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(res, f, default=str)
        print(f"raw results -> {out}", flush=True)
