#!/usr/bin/env python3
"""renko_quality_cardinality.py — how many names actually clear the four gates?

The cheapest question to ask about the Renko-flip + bounded-correction + quality
screen, and the one that decides whether a backtest is even possible: if the
joint filter yields a fraction of a name per day, there is no study to run,
because the n needed for significance would take a decade to accumulate.

This is a COUNTING exercise, not a measurement. It scores no forward returns and
makes no claim about edge. B-43 and B-43r already measured the flip itself
(clean null, then significantly negative under an ADX-matched baseline); nothing
here revisits that.

── The gates, in the order they are cheapest to apply ───────────────────────────
  1. universe      top N by bhavcopy turnover (liquid, tradeable)
  2. flip_up       a Renko brick flip to +1, from the SHIPPED engine (renko.js)
  3. correction    the drawdown into the preceding flip_dn was <= cap%
  4. quality       revenue growth AND operating-cash-flow growth

Gate 3 is swept across caps rather than fixed at one, because the whole question
is where the count falls off — a cap that admits everything is not a filter, and
one that admits nothing is not a screen.

── Two honesty limits, stated because they bound what the output means ─────────
1. **The quality gate uses TODAY's statements.** That is fine for counting how
   many names clear a screen run today, and fatal for a backtest — a 2024 flip
   scored against 2026 fundamentals is lookahead. Gate 4 is therefore reported
   as a same-day pass RATE and combined multiplicatively, never as a historical
   per-day count. Point-in-time reconstruction is a separate build.
2. **The universe is today's listed, liquid names.** Anything delisted or
   illiquid in the window is absent, so every count here is an upper bound.

CLI:
    py -3 tools/renko_quality_cardinality.py --universe 500 --years 2
    py -3 tools/renko_quality_cardinality.py --stage bars      # fetch only
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache" / "cardinality"

#: renko.js needs warmup + atrPeriod + 5 bars before its first brick. Same floor
#: as the B-43 harness so the flips are drawn from comparably seasoned series.
WARMUP = 60

#: Correction caps to sweep, in percent. 40 is the figure under discussion; the
#: tighter rungs are where B-43r's brick-run gradient implies the effect lives.
CAPS = [5.0, 10.0, 15.0, 20.0, 30.0, 40.0, 100.0]


# ── stage 1 · universe ────────────────────────────────────────────────────────

def universe(n: int) -> tuple[list[str], Optional[str]]:
    import trending_stocks as ts
    bhav, date = ts.load_bhav()
    if bhav is None or bhav.empty:
        return [], None
    return ts.liquid_universe(bhav, n), date


# ── stage 2 · bars ────────────────────────────────────────────────────────────

def export_bars(symbols: list[str], years: int, chunk: int = 100) -> list[Path]:
    """Batched download into a cache of its own.

    Per-symbol `export_symbol` is one round trip each; 500 names is twenty
    minutes for bytes yfinance will hand over in five requests.
    """
    import yfinance as yf
    CACHE.mkdir(parents=True, exist_ok=True)
    period = f"{years + 1}y"          # +1y so the first year is warmup, not signal
    out: list[Path] = []
    for i in range(0, len(symbols), chunk):
        batch = symbols[i:i + chunk]
        tickers = [f"{s}.NS" for s in batch]
        try:
            raw = yf.download(tickers, period=period, interval="1d", progress=False,
                              auto_adjust=False, group_by="ticker", threads=True)
        except Exception as e:
            print(f"  batch {i}: download failed ({e})", file=sys.stderr)
            continue
        if raw is None or raw.empty:
            continue
        for sym, tkr in zip(batch, tickers):
            try:
                sub = raw[tkr] if isinstance(raw.columns, pd.MultiIndex) else raw
            except Exception:
                continue
            if sub is None or sub.empty:
                continue
            sub = sub.dropna(subset=["Close", "High", "Low", "Open"])
            if len(sub) < 200:
                continue
            bars = [{"time": int(ts.timestamp()), "open": float(r["Open"]),
                     "high": float(r["High"]), "low": float(r["Low"]),
                     "close": float(r["Close"]),
                     "volume": float(r["Volume"]) if r["Volume"] == r["Volume"] else 0.0}
                    for ts, r in sub.iterrows()]
            p = CACHE / f"{sym}_1d.json"
            p.write_text(json.dumps({"symbol": sym, "tf": "1d", "bars": bars}),
                         encoding="utf-8")
            out.append(p)
        print(f"  batch {i // chunk + 1}: {len(out)} cached so far", file=sys.stderr)
    return out


# ── stage 3 · flips, from the shipped engine ─────────────────────────────────

def flips_for(bars_path: Path) -> list[dict]:
    out_csv = bars_path.with_name(bars_path.stem + "_renko.csv")
    if not out_csv.exists():
        proc = subprocess.run(
            ["node", str(HERE / "renko_backtest.js"), str(bars_path), str(out_csv)],
            capture_output=True, text=True)
        if proc.returncode != 0 or not out_csv.exists():
            return []
    with out_csv.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return [{"time": int(r["time"]), "index": int(r["index"]), "dir": int(r["dir"]),
             "close": float(r["close"]), "bricks_in_prior": int(r["bricks_in_prior"])}
            for r in rows]


# ── stage 4 · the correction into each flip ──────────────────────────────────

def flip_events_raw(bars_path: Path) -> list[dict]:
    """EVERY flip, up and down, with its bar index and the depth before it.

    Split out of `flip_events` so B-57's scorer reads the same depth definition
    this module counted with, rather than re-deriving one that could drift. The
    window filtering and the up-only restriction stay in `flip_events`, which is
    a reporting view over this.

    `depth_from_peak` / `depth_from_flip` are computed for UP-flips only and left
    as None for down-flips. The measure is "how far did it fall before turning
    back up" -- there is no coherent reading of that for a flip in the other
    direction, and inventing one to fill the column would be worse than a gap.
    """
    doc = json.loads(bars_path.read_text(encoding="utf-8"))
    bars = doc["bars"]
    if len(bars) < WARMUP + 120:
        return []
    high = np.array([b["high"] for b in bars], float)
    low = np.array([b["low"] for b in bars], float)

    fl = flips_for(bars_path)
    if not fl:
        return []

    out: list[dict] = []
    for k, f in enumerate(fl):
        row = {"symbol": doc["symbol"], "index": f["index"], "dir": f["dir"],
               "time": f["time"], "bricks_in_prior": f["bricks_in_prior"],
               "depth_from_peak": None, "depth_from_flip": None,
               "days_down": None}
        if f["dir"] == 1:
            prev_dn = next((fl[j] for j in range(k - 1, -1, -1)
                            if fl[j]["dir"] == -1), None)
            if prev_dn is not None:
                prev_up = next((fl[j] for j in range(k - 1, -1, -1)
                                if fl[j]["dir"] == 1
                                and fl[j]["index"] < prev_dn["index"]), None)
                i_dn, i_up = prev_dn["index"], f["index"]
                if i_up > i_dn:
                    trough = float(low[i_dn:i_up + 1].min())
                    peak_from = (prev_up["index"] if prev_up is not None
                                 else max(0, i_dn - 120))
                    peak = float(high[peak_from:i_dn + 1].max())
                    if trough > 0 and peak > 0:
                        row["depth_from_peak"] = round((peak - trough) / peak * 100, 2)
                        row["depth_from_flip"] = round(
                            (prev_dn["close"] - trough) / prev_dn["close"] * 100, 2)
                        row["days_down"] = int(i_up - i_dn)
        out.append(row)
    return out


def flip_events(bars_path: Path, years: int) -> list[dict]:
    """Every flip_up in the scoring window, with the depth of the fall before it.

    Two depths, because "40% correction" is ambiguous and the two readings differ
    by a lot on a name that kept falling after its sell flip:

      depth_from_peak  highest high between the PRIOR flip_up and the flip_dn,
                       down to the lowest low before this flip_up. The real
                       correction — what a chart reader would call it.
      depth_from_flip  the flip_dn's own close down to that same low. What the
                       sell SIGNAL would have saved you, which is smaller.
    """
    doc = json.loads(bars_path.read_text(encoding="utf-8"))
    n_bars = len(doc["bars"])
    # The scoring window is the last `years` of bars; earlier flips exist only to
    # supply each event its preceding down-flip.
    cutoff_i = max(WARMUP, n_bars - int(years * 252))
    return [{
        "symbol": r["symbol"],
        "date": pd.to_datetime(r["time"], unit="s").strftime("%Y-%m-%d"),
        "depth_from_peak": r["depth_from_peak"],
        "depth_from_flip": r["depth_from_flip"],
        "days_down": r["days_down"],
        "bricks_in_prior": r["bricks_in_prior"],
    } for r in flip_events_raw(bars_path)
        if r["dir"] == 1 and r["index"] >= cutoff_i
        and r["depth_from_peak"] is not None]


# ── stage 5 · the quality gate, as a pass RATE ───────────────────────────────

def quality_pass(symbol: str) -> Optional[bool]:
    """Revenue growing AND operating cash flow growing. None = cannot tell.

    None is not False: a name yfinance has no statements for has not failed the
    gate, it was never tested, and folding those into the denominator would
    understate the pass rate by exactly the coverage hole.
    """
    import fundamentals_deep as fd
    try:
        stmts = fd.fetch_statements(symbol)
        deep = fd.derive_fundamentals(symbol, stmts)
    except Exception:
        return None
    rev = deep.get("revenue_cagr_3y")
    ocf = [v for v in (fd._ocf_series(stmts) or []) if v is not None]
    if rev is None or len(ocf) < 3:
        return None
    # OCF newest-first; grew if the latest beats the value three years back.
    return bool(rev > 0 and ocf[0] > ocf[min(2, len(ocf) - 1)])


def main() -> None:
    ap = argparse.ArgumentParser(description="Cardinality of the Renko+quality screen")
    ap.add_argument("--universe", type=int, default=500)
    ap.add_argument("--years", type=int, default=2)
    ap.add_argument("--sample", type=int, default=80, help="names for the quality rate")
    ap.add_argument("--stage", choices=["bars", "flips", "all"], default="all")
    args = ap.parse_args()

    syms, bhav_date = universe(args.universe)
    print(f"universe: {len(syms)} names by turnover (bhavcopy {bhav_date})")
    if not syms:
        sys.exit("no universe")

    have = [p for p in (CACHE / f"{s}_1d.json" for s in syms) if p.exists()]
    if len(have) < len(syms) * 0.5:
        print(f"fetching bars ({args.years + 1}y) ...")
        export_bars(syms, args.years)
        have = [p for p in (CACHE / f"{s}_1d.json" for s in syms) if p.exists()]
    print(f"bars cached: {len(have)} names")
    if args.stage == "bars":
        return

    events: list[dict] = []
    n_ok = 0
    for p in have:
        ev = flip_events(p, args.years)
        if ev:
            n_ok += 1
        events.extend(ev)
    print(f"renko engine ran on {n_ok}/{len(have)} names")
    df = pd.DataFrame(events)
    df.to_csv(CACHE / "flip_events.csv", index=False)
    print(f"flip_up events in the last {args.years}y: {len(df)}")
    if df.empty:
        return

    days = args.years * 252
    print(f"\n-- gate 3 - correction cap sweep ({len(df)} flip_ups, {days} trading days) --")
    print(f"{'cap%':>6} {'from_peak n':>12} {'/day':>7} {'from_flip n':>12} {'/day':>7}")
    for cap in CAPS:
        a = int((df["depth_from_peak"] <= cap).sum())
        b = int((df["depth_from_flip"] <= cap).sum())
        print(f"{cap:>6.0f} {a:>12} {a / days:>7.2f} {b:>12} {b / days:>7.2f}")

    for col in ("depth_from_peak", "depth_from_flip"):
        pct = "  ".join(f"p{q}={np.percentile(df[col], q):.1f}%" for q in (10, 25, 50, 75, 90))
        print(f"{col} percentiles: {pct}")

    if args.stage != "all":
        return
    import random
    random.seed(7)
    samp = random.sample(syms, min(args.sample, len(syms)))
    res = [quality_pass(s) for s in samp]
    tested = [r for r in res if r is not None]
    if not tested:
        print("\nquality gate: no coverage, cannot estimate")
        return
    rate = sum(tested) / len(tested)
    print("\n-- gate 4 - quality (revenue 3Y CAGR > 0 AND OCF growing) --")
    print(f"sampled {len(samp)} names, statements for {len(tested)} "
          f"({len(tested) / len(samp) * 100:.0f}% coverage), pass rate {rate * 100:.0f}%")
    print("\n-- joint estimate (independence ASSUMED - see caveat) --")
    print(f"{'cap%':>6} {'events/yr':>10} {'events/day':>11}")
    for cap in CAPS:
        a = int((df["depth_from_peak"] <= cap).sum()) * rate
        print(f"{cap:>6.0f} {a / args.years:>10.1f} {a / days:>11.2f}")


if __name__ == "__main__":
    main()
