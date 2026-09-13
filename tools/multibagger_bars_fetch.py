#!/usr/bin/env python3
"""multibagger_bars_fetch.py — 6y daily bars for the small/micro-cap universe.

B-73 Phase 0 found the screen unmeasurable on the desk's existing panel for two
reasons, one of them fixable: that panel is LARGE-cap (median ~Rs 48,000 Cr) while
the screen's own ceiling is Rs 20,000 Cr. This fetches the universe the screen is
actually about.

── Why a separate cache directory, and this is the whole design decision ────────
`renko_quality_cardinality.export_bars` writes into `cache/cardinality/`, which is
the SHARED panel behind B-43, B-58, B-65, B-74 and the PSAR/PMax overlap counts.
Calling it here would silently rewrite those 460 files with a different window,
changing the panel under every study that has already published a number against
it -- without touching a line of their code.

So this writes to `cache/multibagger_bars/` instead. Two panels is the cost; a
retroactively edited panel is not a cost anyone can pay back.

Six years, because the ownership archive reaches 2021Q3 and an event needs bars
BEFORE it to be priced and after it to be scored.

CLI:
    py -3 tools/multibagger_bars_fetch.py
    py -3 tools/multibagger_bars_fetch.py --years 6 --chunk 100
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache" / "multibagger_bars"

MIN_BARS = 200          # below this a name cannot carry a 3y-deep event study


def fetch(symbols: list[str], years: int = 6, chunk: int = 100) -> dict:
    import pandas as pd
    import yfinance as yf

    CACHE.mkdir(parents=True, exist_ok=True)
    stats = {"asked": len(symbols), "written": 0, "too_short": 0, "missing": 0}

    for i in range(0, len(symbols), chunk):
        batch = symbols[i:i + chunk]
        tickers = [f"{s}.NS" for s in batch]
        try:
            raw = yf.download(tickers, period=f"{years}y", interval="1d",
                              progress=False, auto_adjust=False,
                              group_by="ticker", threads=True)
        except Exception as e:
            print(f"  batch {i // chunk + 1}: download failed ({e})", file=sys.stderr)
            stats["missing"] += len(batch)
            continue
        if raw is None or raw.empty:
            stats["missing"] += len(batch)
            continue

        for sym, tkr in zip(batch, tickers):
            try:
                sub = raw[tkr] if isinstance(raw.columns, pd.MultiIndex) else raw
            except Exception:
                stats["missing"] += 1
                continue
            if sub is None or sub.empty:
                stats["missing"] += 1
                continue
            sub = sub.dropna(subset=["Close", "High", "Low", "Open"])
            # The stub trap `data_source` documents: yfinance intermittently
            # returns 1-3 rows for thinly-traded names. A short frame is dropped
            # rather than cached, so a later study cannot mistake a stub for a
            # young listing.
            if len(sub) < MIN_BARS:
                stats["too_short"] += 1
                continue
            bars = [{"time": int(ts.timestamp()), "open": float(r["Open"]),
                     "high": float(r["High"]), "low": float(r["Low"]),
                     "close": float(r["Close"]),
                     "volume": float(r["Volume"]) if r["Volume"] == r["Volume"] else 0.0}
                    for ts, r in sub.iterrows()]
            (CACHE / f"{sym}_1d.json").write_text(
                json.dumps({"symbol": sym, "tf": "1d", "bars": bars}),
                encoding="utf-8")
            stats["written"] += 1
        print(f"  batch {i // chunk + 1}: {stats['written']} cached", file=sys.stderr)
    return stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=6)
    ap.add_argument("--chunk", type=int, default=100)
    args = ap.parse_args()

    sys.path.insert(0, str(HERE))
    import smallcap_universe as su

    syms = sorted({r["symbol"] for r in su.fetch_universe("both")})
    print(f"small/micro-cap universe: {len(syms)} names -> {CACHE}")
    print(json.dumps(fetch(syms, args.years, args.chunk), indent=1))


if __name__ == "__main__":
    main()
