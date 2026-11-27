"""breakout_scan.py — the Breakout Scans page's engine, with no Chartink session.

Replaced `chartink_scraper` on that page (2026-10-06). Chartink needed a
`_chartink_session` cookie pasted by hand every time it expired; this needs no
login at all:

    universe  NSE bhavcopy, top N by traded value  (nseindia.com, public)
    bars      yfinance daily history, batch-downloaded, period="max"
    rules     scanner_templates' own consolidation-breakout engine (6M → 10Y)
              and the Chartink pre-breakout clause re-evaluated locally

Results will NOT match Chartink one-for-one, and that is a correction rather
than drift: Chartink's clauses gate the prior range with
`min(low) < max(high)`, which is true of every stock that ever moved, so they
had no consolidation test. The engine here rejects ranges wider than a
per-duration limit (see `scanner_templates._consolidation_breakout`). The
universe is also the top-N liquid names, not the whole cash market.

No Streamlit import: the page caches `run()`; tests call it on synthetic frames.
"""

from __future__ import annotations

from typing import Callable, Iterable

import pandas as pd

import scanner_templates as sc

#: yfinance tickers per batch request — large enough to amortise the call, small
#: enough that one bad response does not lose the whole universe.
CHUNK = 100


def download_history(symbols: list[str], period: str = "max",
                     progress: Callable[[float, str], None] | None = None,
                     ) -> dict[str, pd.DataFrame]:
    """{symbol: lower-cased OHLCV frame} for every symbol yfinance could serve."""
    import yfinance as yf

    frames: dict[str, pd.DataFrame] = {}
    chunks = [symbols[i:i + CHUNK] for i in range(0, len(symbols), CHUNK)]
    for n, chunk in enumerate(chunks, 1):
        if progress:
            progress((n - 1) / max(len(chunks), 1),
                     f"Downloading history {n}/{len(chunks)} ({len(chunk)} symbols)…")
        tickers = [s if "." in s else f"{s}.NS" for s in chunk]
        try:
            raw = yf.download(tickers, period=period, interval="1d",
                              group_by="ticker", auto_adjust=True,
                              progress=False, threads=True)
        except Exception:
            continue
        if raw is None or raw.empty:
            continue
        avail = set(raw.columns.get_level_values(0)) if isinstance(
            raw.columns, pd.MultiIndex) else set()
        for sym, tk in zip(chunk, tickers):
            try:
                f = raw[tk].copy() if tk in avail else (
                    raw.copy() if len(tickers) == 1 else None)
            except Exception:
                f = None
            if f is None:
                continue
            f.columns = [str(c).lower() for c in f.columns]
            f = f.dropna(subset=[c for c in ("open", "high", "low", "close", "volume")
                                 if c in f.columns])
            if not f.empty:
                frames[sym] = f
    return frames


def breakouts(frames: dict[str, pd.DataFrame],
              tiers: Iterable[str] | None = None) -> list[dict]:
    """One row per symbol that cleared at least one selected duration tier.

    A 10-year breakout also clears every shorter high, so each row records ALL
    tiers cleared plus the longest one, and rows sort longest first.
    """
    want = set(tiers) if tiers else None
    rows = []
    for sym, df in frames.items():
        cleared, best = [], None
        for days, label, fn in sc.BREAKOUT_TIERS:
            if want is not None and label not in want:
                continue
            try:
                hit = fn(df)
            except Exception:
                hit = None
            if hit:
                cleared.append(label)
                if best is None:
                    best = (days, label, hit)
        if best is None:
            continue
        days, label, hit = best
        close = df["close"]
        rows.append({
            "symbol": sym, "longest": label, "duration_days": days,
            "tiers": ", ".join(cleared),
            "price": round(float(close.iloc[-1]), 2),
            "chg_pct": (round((float(close.iloc[-1]) / float(close.iloc[-2]) - 1) * 100, 2)
                        if len(close) > 1 else None),
            "broke_level": hit.get("broke_level"),
            "breakout_pct": hit.get("breakout_pct"),
            "range_pct": hit.get("range_pct"),
            "vol_ratio": hit.get("vol_ratio"),
            "years_history": round(len(df) / 252, 1),
            "as_of": str(df.index[-1])[:10],
        })
    rows.sort(key=lambda r: (-r["duration_days"], -(r["breakout_pct"] or 0)))
    return rows


def pre_breakouts(frames: dict[str, pd.DataFrame], min_conviction: float = 0) -> list[dict]:
    """Local Chartink pre-breakout gate, then the 0-100 conviction score."""
    out = []
    for sym, df in frames.items():
        d = df.tail(120)
        try:
            if not sc.pre_breakout_gate(d):
                continue
            hit = sc.compute_pre_breakout_conviction(d)
        except Exception:
            continue
        if hit is None or hit["conviction"] < min_conviction:
            continue
        close = d["close"]
        hit.update({"symbol": sym, "price": round(float(close.iloc[-1]), 2),
                    "pct_chg": round((float(close.iloc[-1]) / float(close.iloc[-2]) - 1)
                                     * 100, 2)})
        out.append(hit)
    return sorted(out, key=lambda h: h["conviction"], reverse=True)


def short_history(frames: dict[str, pd.DataFrame], sessions: int) -> list[str]:
    """Symbols whose history is too short for a tier — stated, never implied."""
    return sorted(s for s, f in frames.items() if len(f) < sessions + 5)
