#!/usr/bin/env python3
"""svp_universe_export.py — bars for the SVP structure screen, universe-wide.

Writes one `<SYMBOL>_1d.json` per name into a cache directory, in the shape
`svp_screen_runner.js` reads: `{symbol, tf, bars:[{time,open,high,low,close,volume}]}`.

── Why a separate exporter rather than reusing the backtest one ──────────────
`evwma_vwap_macd_backtest.export_basket` pulls from 2007 because a backtest needs
every bar it can get. This screen needs only enough history for the SVP engine's
retained window — 12 sessions, which on NSE dailies resolve to WEEKLY grain, so
roughly 12 weeks plus warmup. Pulling 18 years for 500 names to read the last 12
weeks would be about 40x the download for the same answer, and yfinance is the
rate limit here, not disk.

`DEFAULT_DAYS = 400` is deliberately generous against that floor: the grain-picker
measures bars-per-day from the data, so a symbol that resolves to DAILY grain (a
24h instrument, or an unusually dense feed) needs more bars than the weekly case,
and a short pull would silently give it fewer sessions rather than failing. Better
to over-fetch once than to produce a screen where some rows quietly rest on less
structure than others.

── Failure policy ───────────────────────────────────────────────────────────
One dead ticker must not kill a 500-symbol run, so fetch errors are counted and
reported at the end rather than raised. A symbol with too few bars is SKIPPED
rather than written thin: `n_sessions` on the screen would show the shortfall, but
a row that reaches the page at all reads as a comparable row, and it would not be.

CLI:
  py -3 tools/svp_universe_export.py                      # nifty500 -> cache/svp_bars
  py -3 tools/svp_universe_export.py --index nifty50
  py -3 tools/svp_universe_export.py --symbols RELIANCE TCS --out cache/svp_bars
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

import nse_universe as nu
import screener_pipeline as sp

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "cache" / "svp_bars"
DEFAULT_DAYS = 400

#: Below this many daily bars the engine cannot build its retained window at any
#: grain, so the symbol is skipped rather than written.
MIN_BARS = 80


def export(symbols: list[str], out_dir: Path, days: int = DEFAULT_DAYS,
           enforce_liquidity: bool = True) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    ok = thin = failed = 0
    for i, sym in enumerate(symbols, 1):
        try:
            # The Rs 1 cr floor is a SCAN filter. It belongs on an --index
            # sweep, where the point is to exclude what cannot be traded, and
            # NOT on symbols the caller named: there the export silently
            # produced no structure for the very names that were asked for.
            # Same rule as cached_fetch_ohlcv's docstring records for the
            # dashboard's by-name pages.
            df = sp.fetch_ohlcv(sym, days=days,
                                min_turnover=None if enforce_liquidity else 0)
        except Exception:
            failed += 1
            continue
        if df is None or len(df) < MIN_BARS:
            thin += 1
            continue
        # Drop bars with no price BEFORE serialising. Python's json writes bare
        # `NaN`, which is not valid JSON and which Node refuses to parse — the
        # runner dies on the whole directory, not just the offending file. This
        # went unnoticed because the liquidity floor had been excluding exactly
        # the thin names whose feeds carry gaps; turning the floor off for
        # named symbols surfaced it immediately.
        df = df.dropna(subset=[c for c in ("open", "high", "low", "close")
                               if c in df.columns])
        if len(df) < MIN_BARS:
            thin += 1
            continue
        idx = pd.to_datetime(df.index)
        bars = [
            {"time": int(t.timestamp()),
             "open": float(r["open"]), "high": float(r["high"]),
             "low": float(r["low"]), "close": float(r["close"]),
             "volume": float(r.get("volume", 0) or 0)}
            for t, (_, r) in zip(idx, df.iterrows())
        ]
        doc = {"symbol": sym, "tf": "1d", "bars": bars}
        # allow_nan=False so a future gap raises HERE, named and per-symbol,
        # instead of writing a file that kills the JS runner on a later pass.
        (out_dir / f"{sym}_1d.json").write_text(
            json.dumps(doc, allow_nan=False), encoding="utf-8")
        ok += 1
        if i % 25 == 0:
            print(f"  [{i}/{len(symbols)}] ok={ok} thin={thin} failed={failed}",
                  flush=True)
    return {"ok": ok, "thin": thin, "failed": failed, "total": len(symbols)}


def main() -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Export bars for the SVP structure screen")
    ap.add_argument("--index", default="nifty500")
    ap.add_argument("--symbols", nargs="*")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--days", type=int, default=DEFAULT_DAYS)
    args = ap.parse_args()

    syms = args.symbols or nu.symbols(args.index)
    # NAMED symbols are never screened out; an --index sweep still is.
    by_name = bool(args.symbols)
    print(f"exporting {len(syms)} symbols ({args.days}d) -> {args.out}"
          f"{' · liquidity floor OFF (symbols named)' if by_name else ''}",
          flush=True)
    res = export(syms, args.out, args.days, enforce_liquidity=not by_name)
    print(f"done: {res['ok']} written, {res['thin']} too thin, "
          f"{res['failed']} failed, of {res['total']}")
    print(f"next: node tools/svp_screen_runner.js --dir {args.out} "
          f"--out tools/cache/svp_screen.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
