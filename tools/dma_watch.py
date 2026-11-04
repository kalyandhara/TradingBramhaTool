#!/usr/bin/env python3
"""dma_watch.py — B-198: email when one of MY names closes below its 200-DMA.

Runs once a day after the NSE close. For every held / watchlist / latest-pick
name (the same list filings_watch uses), it reads daily bars and fires on the
CROSS: the previous session closed at or above its 200-day simple moving
average and the latest session closed below it. A name that already lives
below its 200-DMA is not re-alerted every day; a name that reclaims it and
falls back through it fires again.

Each cross is emailed once (keyed by symbol and bar date in
cache/alerts/dma_seen.json, written only after the send succeeds) and
appended to cache/alerts/alerts.jsonl, so the digest's "Alerts Fired"
section shows it.

> [!important] A trend-state CHANGE, not a sell signal. Nothing on this desk
> has measured what a 200-DMA break on these names does next; the alert says
> the line was crossed and how far, and nothing more.

A run where no name could be fetched exits 2 (the .bat logs FAILED): checking
nothing is not a quiet day.

CLI:
    py -3 -X utf8 tools/dma_watch.py            # check once, email new crosses
    py -3 -X utf8 tools/dma_watch.py --dry-run  # print, send nothing, mark nothing seen
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

ALERT_DIR = HERE / "cache" / "alerts"
SEEN_PATH = ALERT_DIR / "dma_seen.json"
FEED_PATH = ALERT_DIR / "alerts.jsonl"
SEEN_KEEP = 2000
DMA_N = 200
FETCH_DAYS = 420          # calendar days; ~290 sessions, enough for 200 + 1

_RANK = {"held": 0, "watchlist": 1, "pick": 2}


def dma_cross(close, n: int = DMA_N) -> dict | None:
    """The cross below the n-day SMA on the LAST bar, or None.

    None also means "cannot tell": fewer than n + 1 bars gives no previous-day
    average to compare against, and that is not a cross.
    """
    close = close.dropna()
    if len(close) < n + 1:
        return None
    sma = close.rolling(n).mean()
    prev_c, last_c = float(close.iloc[-2]), float(close.iloc[-1])
    prev_s, last_s = float(sma.iloc[-2]), float(sma.iloc[-1])
    if not (prev_c >= prev_s and last_c < last_s):
        return None
    return {"date": str(close.index[-1])[:10], "close": last_c, "dma": last_s,
            "prev_close": prev_c, "prev_dma": prev_s,
            "pct_below": (last_c / last_s - 1.0) * 100.0}


def cross_key(c: dict) -> str:
    return f"dma{DMA_N}_below|{c['symbol']}|{c['date']}"


def new_crosses(crosses: Iterable[dict], seen: set[str]) -> list[dict]:
    out = []
    for c in crosses:
        k = cross_key(c)
        if k in seen:
            continue
        seen.add(k)
        out.append(c)
    return out


def headline(c: dict) -> str:
    return (f"{c['symbol']} closed below its {DMA_N}-DMA · {c['close']:,.2f} vs "
            f"{c['dma']:,.2f} ({c['pct_below']:+.1f}%) · {c['why']}")


def render_email(rows: list[dict]) -> tuple[str, str]:
    rows = sorted(rows, key=lambda r: (_RANK.get(r["why"], 9), r["symbol"]))
    held = sum(r["why"] == "held" for r in rows)
    n = len(rows)
    subject = (f"Trading Bramha Alert · {DMA_N}-DMA break · {n} name{'s' if n > 1 else ''}"
               + (f" · {held} held" if held else ""))
    body = ("\n".join(f"{r['symbol']} ({r['why']}) · close {r['close']:,.2f} < "
                      f"{DMA_N}-DMA {r['dma']:,.2f} · {r['pct_below']:+.1f}% · {r['date']}"
                      for r in rows)
            + f"\n\nEach name closed at or above its {DMA_N}-day average the session "
              "before and below it on the date shown. A trend-state change, not a sell "
              "signal: what a break does next on these names is unmeasured."
            + f"\n— Trading Bramha {DMA_N}-DMA watch ({datetime.now():%Y-%m-%d %H:%M})")
    return subject, body


def _load_seen() -> list[str]:
    try:
        return json.loads(SEEN_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def main() -> int:
    ap = argparse.ArgumentParser(description=f"Email {DMA_N}-DMA breaks on my names.")
    ap.add_argument("--dry-run", action="store_true",
                    help="print crosses; send nothing, mark nothing seen")
    a = ap.parse_args()

    import screener_pipeline as sp
    from filings_watch import load_names

    names = load_names()
    crosses, fetched, below = [], 0, 0
    for sym, why in names.items():
        # min_turnover=0: these names were asked for by name, so the scan's
        # liquidity floor is the wrong rule here (see fetch_ohlcv).
        df = sp.fetch_ohlcv(sym, days=FETCH_DAYS, min_turnover=0)
        if df is None or df.empty:
            continue
        fetched += 1
        close = df["close"]
        if len(close) > DMA_N and close.iloc[-1] < close.rolling(DMA_N).mean().iloc[-1]:
            below += 1
        c = dma_cross(close)
        if c:
            crosses.append({**c, "symbol": sym, "why": why})

    seen_list = _load_seen()
    fresh = new_crosses(crosses, set(seen_list))
    print(f"{fetched}/{len(names)} names fetched · {below} below their {DMA_N}-DMA · "
          f"{len(crosses)} crossed below on the last bar · {len(fresh)} new")
    print(f"##RESULT {fetched}/{len(names)} names · {below} below {DMA_N}-DMA · "
          f"{len(fresh)} new break{'s' if len(fresh) != 1 else ''}"
          + (": " + ", ".join(c["symbol"] for c in fresh) if fresh else ""))
    if names and not fetched:
        print("no name could be fetched — nothing was checked")
        return 2
    if not fresh:
        return 0

    subject, body = render_email(fresh)
    if a.dry_run:
        print(f"\n{subject}\n\n{body}")
        return 0

    from alert_email_send import send
    print("  ✉ ", send(subject, body))
    ALERT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().isoformat(timespec="seconds")
    with FEED_PATH.open("a", encoding="utf-8") as f:
        for c in fresh:
            f.write(json.dumps({"ts": stamp, "symbol": c["symbol"], "tf": "1d",
                                "rule": f"dma{DMA_N}_below", "headline": headline(c),
                                "close": c["close"], "dma": c["dma"], "why": c["why"]},
                               ensure_ascii=False) + "\n")
    seen_list += [cross_key(c) for c in fresh]
    SEEN_PATH.write_text(json.dumps(seen_list[-SEEN_KEEP:]), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.exit(main())
