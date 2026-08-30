"""evwma_vwap_macd_backtest.py — does the EVWMA/VWAP MACD cross actually pay?

Scores the BUY/SELL crossovers of the chart's `evmacd` indicator (a port of
QuantNomad's Pine v4 "EVWMA VWAP MACD Strategy") the same way every other rule in
this repo is scored, so the answer is comparable to the ADX/DI and delete-funnel
findings rather than to a TradingView equity curve.

Two independent readings, because they answer different questions:

  1. EVENT EDGE (the honest one) — point-in-time, enter next open, exit
     next-open + h closes later; edge = signal mean forward return − the
     every-bar baseline mean over the SAME bars, with a Welch two-sample
     p-value (`funnel_backtest._welch_p`, scipy-optional). A rule that only
     inherits the drift of a rising market shows edge ≈ 0 here even while its
     equity curve climbs. Short crossunders are measured as plain LONG forward
     returns, so for those a NEGATIVE edge means the flag had teeth.

  2. STRATEGY EQUITY (what the Pine script actually does) — stop-and-reverse,
     always in the market, flipping at every cross, plus a long-only variant
     (crossunder = go flat) because shorting NSE cash for a swing hold is not a
     thing most of this repo's users can do. Reported against buy-and-hold over
     the identical span, with a per-flip cost knob in bps — the repo's standing
     `no-costs-slippage` caveat is a switch here, not a footnote.

The signals come from the SHIPPED JS engine via `evwma_vwap_macd_backtest.js`
(node subprocess), never from a Python re-implementation — same discipline as the
SVP backtest. Every term in the indicator is backward-looking, so one pass over
the series and indexing at bar t is already look-ahead-free.

CLI:
  py -3 tools/evwma_vwap_macd_backtest.py                 # score whatever is cached
  py -3 tools/evwma_vwap_macd_backtest.py --export        # fetch the basket first
  py -3 tools/evwma_vwap_macd_backtest.py --cost-bps 20
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from funnel_backtest import _welch_p

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache" / "backtest"

DEFAULT_HORIZONS = (5, 10, 20, 60)
WARMUP = 60            # sumLength(30) + slow EMA(20) + slack; the JS emits nothing earlier
DEFAULT_STRIDE = 5     # baseline sampling, to cut autocorrelation (as adx_di_backtest)

#: The liquid basket adx_di_backtest.py already uses, in yfinance form, so this
#: finding and the ADX one are measured on the same names — plus the two indices
#: and HAL (the symbol on the reference chart this port was verified against).
DEFAULT_BASKET = [
    "RELIANCE.NS", "TITAN.NS", "CDSL.NS", "KPITTECH.NS", "PERSISTENT.NS",
    "INFY.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "LT.NS", "BEL.NS",
    "IRFC.NS", "TATAPOWER.NS", "SUNPHARMA.NS", "DIVISLAB.NS", "PIDILITIND.NS",
    "BAJFINANCE.NS", "ASIANPAINT.NS", "NESTLEIND.NS", "HAVELLS.NS",
    "HAL.NS", "^NSEI", "^NSEBANK",
]


def _safe(symbol: str) -> str:
    return symbol.replace("^", "_").replace("=", "_").replace("-", "_")


def export_basket(symbols: list[str], tf: str = "1d", start: str = "2007-09-17") -> None:
    """Fetch bars into cache/backtest via the existing exporter (yfinance)."""
    import svp_backtest_export as ex
    for s in symbols:
        try:
            ex.export_symbol(s, tf, start, None)
        except Exception as e:              # one dead ticker must not kill the run
            print(f"  {s:14} SKIPPED ({e})")


def signals_for(bars_path: Path) -> list[dict]:
    """Run the shipped JS engine over `bars_path` and return its crossover rows."""
    out_csv = bars_path.with_name(bars_path.stem + "_evmacd.csv")
    proc = subprocess.run(
        ["node", str(HERE / "evwma_vwap_macd_backtest.js"), str(bars_path), str(out_csv)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"node runner failed on {bars_path.name}: {proc.stderr.strip()}")
    with out_csv.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return [{"time": int(r["time"]), "index": int(r["index"]), "dir": int(r["dir"]),
             "close": float(r["close"]), "histPct": float(r["histPct"])} for r in rows]


def _load(bars_path: Path):
    doc = json.loads(bars_path.read_text(encoding="utf-8"))
    bars = doc["bars"]
    o = np.array([b["open"] for b in bars], float)
    c = np.array([b["close"] for b in bars], float)
    return doc["symbol"], doc["tf"], o, c


# ── 1. event edge ─────────────────────────────────────────────────────────────
def event_edge(paths: list[Path], *, horizons=DEFAULT_HORIZONS,
               warmup: int = WARMUP, stride: int = DEFAULT_STRIDE,
               signals_fn=None) -> dict:
    """`signals_fn(bars_path) -> [{index, dir, ...}]` defaults to this module's engine.

    Injected rather than hardcoded so a second signal source (renko_backtest) scores
    through the SAME harness instead of growing a second copy of the edge-vs-baseline
    and Welch machinery — one scorer, several engines.
    """
    signals_fn = signals_fn or signals_for
    max_h = max(horizons)
    base = {h: [] for h in horizons}
    sig = {1: {h: [] for h in horizons}, -1: {h: [] for h in horizons}}
    n_used = 0

    for p in paths:
        symbol, tf, o, c = _load(p)
        n = len(c)
        if n < warmup + max_h + 3:
            continue
        rows = signals_fn(p)
        n_used += 1
        last_eval = n - max_h - 2

        def fwd_at(t: int):
            entry = o[t + 1]
            if not (entry > 0):
                return None
            return {h: (c[t + 1 + h] / entry - 1.0) * 100.0 for h in horizons}

        for t in range(warmup, last_eval + 1, stride):
            f = fwd_at(t)
            if f is None:
                continue
            for h in horizons:
                base[h].append(f[h])

        for r in rows:
            t = r["index"]
            if t < warmup or t > last_eval:
                continue
            f = fwd_at(t)
            if f is None:
                continue
            for h in horizons:
                sig[r["dir"]][h].append(f[h])

    bmean = {h: (float(np.mean(base[h])) if base[h] else float("nan")) for h in horizons}
    legs = {}
    for d, name in ((1, "cross_up (BUY)"), (-1, "cross_dn (SELL)")):
        legs[name] = {
            "n": len(sig[d][horizons[0]]),
            "mean": {h: (float(np.mean(sig[d][h])) if sig[d][h] else float("nan")) for h in horizons},
            "edge": {h: ((float(np.mean(sig[d][h])) - bmean[h]) if sig[d][h] else float("nan"))
                     for h in horizons},
            "p": {h: _welch_p(sig[d][h], np.asarray(base[h])) for h in horizons},
            "bearish": d == -1,
        }
    return {"horizons": horizons, "n_symbols": n_used,
            "n_baseline": len(base[horizons[0]]), "base_mean": bmean, "legs": legs}


# ── 2. strategy equity ────────────────────────────────────────────────────────
def strategy_equity(paths: list[Path], *, cost_bps: float = 0.0,
                    warmup: int = WARMUP, signals_fn=None) -> dict:
    """Replay the Pine strategy (stop-and-reverse) and a long-only variant.

    Entry/exit at the NEXT bar's open after the cross — the cross is only known
    at that bar's close, so filling at its own close would be look-ahead.
    """
    per_symbol, sar_all, lo_all, bh_all = [], [], [], []
    cost = cost_bps / 10_000.0

    for p in paths:
        symbol, tf, o, c = _load(p)
        rows = [r for r in (signals_fn or signals_for)(p) if warmup <= r["index"] < len(c) - 2]
        if len(rows) < 4:
            continue
        start_i = rows[0]["index"] + 1
        eq_sar, eq_lo = 1.0, 1.0
        for a, b in zip(rows, rows[1:]):
            entry, exit_ = o[a["index"] + 1], o[b["index"] + 1]
            if not (entry > 0 and exit_ > 0):
                continue
            leg = exit_ / entry - 1.0
            eq_sar *= (1.0 + (leg if a["dir"] == 1 else -leg)) * (1.0 - cost)
            if a["dir"] == 1:
                eq_lo *= (1.0 + leg) * (1.0 - cost)     # long-only: flat while short
        # Mark the final open position out at the last close, both variants.
        last = rows[-1]
        entry, final = o[last["index"] + 1], c[-1]
        if entry > 0:
            leg = final / entry - 1.0
            eq_sar *= 1.0 + (leg if last["dir"] == 1 else -leg)
            if last["dir"] == 1:
                eq_lo *= 1.0 + leg
        bh = c[-1] / o[start_i] if o[start_i] > 0 else float("nan")
        per_symbol.append({"symbol": symbol, "n_flips": len(rows),
                           "sar": (eq_sar - 1) * 100, "long_only": (eq_lo - 1) * 100,
                           "buyhold": (bh - 1) * 100,
                           "bars": len(c) - start_i})
        sar_all.append((eq_sar - 1) * 100)
        lo_all.append((eq_lo - 1) * 100)
        bh_all.append((bh - 1) * 100)

    return {"cost_bps": cost_bps, "per_symbol": per_symbol,
            "median_sar": float(np.median(sar_all)) if sar_all else float("nan"),
            "median_long_only": float(np.median(lo_all)) if lo_all else float("nan"),
            "median_buyhold": float(np.median(bh_all)) if bh_all else float("nan"),
            "beat_bh_sar": sum(1 for a, b in zip(sar_all, bh_all) if a > b),
            "beat_bh_lo": sum(1 for a, b in zip(lo_all, bh_all) if a > b),
            "n": len(sar_all)}


def format_report(ev: dict, eq: dict | None = None) -> str:
    H = ev["horizons"]
    out = [
        "EVWMA/VWAP MACD crossover  (point-in-time; edge = signal mean fwd - baseline mean fwd %)",
        f"symbols used: {ev['n_symbols']}   baseline bars: {ev['n_baseline']}",
        "  baseline mean fwd %:  " + "  ".join(f"{h}d {ev['base_mean'][h]:+.2f}" for h in H),
        "",
        f"  {'leg':<20}{'n':>6}   " + "  ".join(f"{h}d edge (p)".rjust(17) for h in H),
        "  " + "-" * (20 + 6 + 3 + 19 * len(H)),
    ]
    for name, st in ev["legs"].items():
        cells = []
        for h in H:
            e, p = st["edge"][h], st["p"][h]
            if e is None or (isinstance(e, float) and np.isnan(e)):
                cells.append("n/a".rjust(17))
            else:
                star = " *" if (p is not None and p < 0.05) else ""
                cells.append(f"{e:+.2f} ({'n/a' if p is None else f'{p:.2f}'}){star}".rjust(17))
        out.append(f"  {name:<20}{st['n']:>6}   " + "  ".join(cells))
    out += [
        "",
        "* = Welch p<0.05 vs the every-bar baseline. cross_dn is scored as a LONG",
        "forward return, so a NEGATIVE edge there means the SELL flag had teeth.",
    ]

    if eq:
        out += [
            "",
            f"Strategy equity - stop-and-reverse vs long-only vs buy&hold  "
            f"(cost {eq['cost_bps']:.0f} bps/flip, next-open fills)",
            f"  {'symbol':<14}{'flips':>6}{'S&R %':>12}{'long-only %':>14}{'buy&hold %':>13}",
            "  " + "-" * 59,
        ]
        for r in eq["per_symbol"]:
            out.append(f"  {r['symbol']:<14}{r['n_flips']:>6}{r['sar']:>12,.0f}"
                       f"{r['long_only']:>14,.0f}{r['buyhold']:>13,.0f}")
        out += [
            "  " + "-" * 59,
            f"  {'MEDIAN':<14}{'':>6}{eq['median_sar']:>12,.0f}"
            f"{eq['median_long_only']:>14,.0f}{eq['median_buyhold']:>13,.0f}",
            f"  beat buy&hold: stop-and-reverse {eq['beat_bh_sar']}/{eq['n']}, "
            f"long-only {eq['beat_bh_lo']}/{eq['n']}",
        ]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Backtest the EVWMA/VWAP MACD crossover")
    ap.add_argument("--export", action="store_true", help="fetch DEFAULT_BASKET first (yfinance)")
    ap.add_argument("--tf", default="1d")
    ap.add_argument("--start", default="2007-09-17")
    ap.add_argument("--cost-bps", type=float, default=0.0, help="round-trip cost per flip, bps")
    ap.add_argument("--symbols", nargs="*", help="restrict to these symbols")
    args = ap.parse_args()

    if args.export:
        export_basket(args.symbols or DEFAULT_BASKET, args.tf, args.start)

    wanted = args.symbols or DEFAULT_BASKET
    paths = [CACHE / f"{_safe(s)}_{args.tf}.json" for s in wanted]
    paths = [p for p in paths if p.exists()]
    if not paths:
        sys.exit(f"no cached bars in {CACHE} — run with --export first")

    ev = event_edge(paths)
    eq = strategy_equity(paths, cost_bps=args.cost_bps)
    print(format_report(ev, eq))


if __name__ == "__main__":
    main()
