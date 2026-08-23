#!/usr/bin/env python3
"""
svp_backtest_export.py — dump per-symbol OHLCV to JSON for the SVP backtest.

Phase 1 of the SVP Confluence Signal backtest (see the wiki design page
"SVP Confluence Signal — Backtest Design"). yfinance stays the single price
source here; the Node runner (svp_backtest_runner.js) consumes these JSON files
and runs the REAL JS engine over them, so the Python side never re-implements
any signal logic.

Bar shape written (matches window.SVP's expected bar):
  {"time": <unix seconds, UTC>, "open","high","low","close","volume"}

CLI:
  py -3 tools/svp_backtest_export.py                       # primary daily basket
  py -3 tools/svp_backtest_export.py --symbol ^NSEI --tf 1d --start 2007-09-17
  py -3 tools/svp_backtest_export.py --crypto              # BTC/ETH 1h secondary
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "cache" / "backtest"

# Locked pre-registration baskets (see design page).
PRIMARY_DAILY = ["^NSEI", "^NSEBANK", "RELIANCE.NS", "TCS.NS",
                 "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS"]
SECONDARY_1H = ["BTC-USD", "ETH-USD"]   # yfinance crypto proxy for BTC/ETH


def _yf_interval(tf: str) -> str:
    return {"1d": "1d", "1h": "1h", "1w": "1wk"}.get(tf, tf)


def export_symbol(symbol: str, tf: str, start: str, period: str | None) -> Path:
    import yfinance as yf
    interval = _yf_interval(tf)
    kw = dict(interval=interval, progress=False, auto_adjust=False)
    # yfinance caps intraday history (1h ≈ last 730d) — use period, not start.
    if interval in ("1h", "60m", "90m", "30m", "15m", "5m", "1m"):
        df = yf.download(symbol, period=period or "730d", **kw)
    else:
        df = yf.download(symbol, start=start, **kw)
    if df.empty:
        raise SystemExit(f"No data for {symbol} ({tf}).")
    if hasattr(df.columns, "get_level_values"):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna(subset=["Close", "High", "Low"])

    bars = []
    for ts, row in df.iterrows():
        t = int(ts.timestamp())            # tz-aware or naive → UTC seconds
        vol = row.get("Volume", 0)
        bars.append({
            "time": t,
            "open": float(row["Open"]), "high": float(row["High"]),
            "low": float(row["Low"]), "close": float(row["Close"]),
            "volume": float(vol) if vol == vol else 0.0,   # NaN-safe
        })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    safe = symbol.replace("^", "_").replace("=", "_").replace("-", "_")
    out = OUT_DIR / f"{safe}_{tf}.json"
    out.write_text(json.dumps({"symbol": symbol, "tf": tf, "bars": bars}),
                   encoding="utf-8")
    print(f"  {symbol:14} {tf}  {len(bars):>5} bars  "
          f"{df.index[0].date()}..{df.index[-1].date()}  -> {out.name}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Export OHLCV JSON for SVP backtest")
    ap.add_argument("--symbol", help="single symbol (else the locked basket)")
    ap.add_argument("--tf", default="1d")
    ap.add_argument("--start", default="2007-09-17")
    ap.add_argument("--period", default=None, help="intraday period, e.g. 730d")
    ap.add_argument("--crypto", action="store_true",
                    help="export the BTC/ETH 1h secondary basket")
    args = ap.parse_args()

    if args.symbol:
        export_symbol(args.symbol, args.tf, args.start, args.period)
    elif args.crypto:
        print("Exporting secondary 1h basket:")
        for s in SECONDARY_1H:
            export_symbol(s, "1h", args.start, args.period)
    else:
        print("Exporting primary daily basket:")
        for s in PRIMARY_DAILY:
            export_symbol(s, "1d", args.start, args.period)


if __name__ == "__main__":
    main()
