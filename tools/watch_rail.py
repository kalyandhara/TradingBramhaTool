#!/usr/bin/env python3
"""watch_rail.py — pure logic behind Home's left watchlist rail (B-179).

Three jobs, none of which touch Streamlit or the network:

  1. The CLOSE SNAPSHOT. Before B-179 the desk had no closing-price cache on
     disk: every scan pulled the whole-market bhavcopy into memory
     (`st.cache_data`, 15 min) and nothing kept it. Home's rule is that it
     never fetches on load, so a rail with prices needs prices that are
     already on disk. `trending_stocks.load_bhav` writes them here whenever
     any section (or the rail's ↻) loads the bhavcopy; the rail only reads.

  2. The PICKER. One list: your watchlist first, then every canonical NSE
     sector (`sectors.py` — NSE macro is canonical). The key is the raw
     sector string, never parsed back out of the "(N)" label, because sector
     names carry punctuation ("Oil Gas & Consumable Fuels").

  3. The ROWS. Symbol · Close · Day % · ♥ for whichever source is picked.
     A name with no sector or no snapshot row is shown blank, never guessed.
"""
from __future__ import annotations

import json
import logging
import math
from datetime import datetime
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

CLOSES_PATH: Path = Path(__file__).resolve().parent / "cache" / "last_close.json"
WATCHLIST_KEY: str = "__watchlist__"

_COLUMNS = ["Symbol", "Close", "Day %", "♥"]


def write_closes(frame: pd.DataFrame, trade_date: str | None,
                 path: Path = CLOSES_PATH) -> int:
    """Persist `symbol, close, prev_close` from a bhavcopy frame; return rows written.

    Rows with a missing or non-positive close / prev_close are skipped, so the
    JSON never holds NaN or a price that would make Day % infinite. Never
    raises: a snapshot that could not be written must not break the scan that
    loaded the bhavcopy.
    """
    try:
        d = frame[["symbol", "close", "prev_close"]].copy()
        d["close"] = pd.to_numeric(d["close"], errors="coerce")
        d["prev_close"] = pd.to_numeric(d["prev_close"], errors="coerce")
        d = d[(d["close"] > 0) & (d["prev_close"] > 0)]
        rows = {str(s).strip(): [float(c), float(p)]
                for s, c, p in zip(d["symbol"], d["close"], d["prev_close"])
                if str(s).strip()}
        payload = {"trade_date": trade_date,
                   "saved_at": datetime.now().isoformat(timespec="seconds"),
                   "rows": rows}
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")
        tmp.replace(path)
        return len(rows)
    except Exception as e:
        log.warning("close snapshot not written: %s", e)
        return 0


def read_closes(path: Path = CLOSES_PATH) -> tuple[dict[str, tuple[float, float]], str | None]:
    """`({SYMBOL: (close, prev_close)}, trade_date)`, or `({}, None)` when the
    file is missing or unreadable — no prices is a state the rail shows, not
    an error."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = {str(s): (float(v[0]), float(v[1]))
                for s, v in payload["rows"].items()}
        return rows, payload.get("trade_date")
    except Exception:
        return {}, None


def sector_options(sector_map: dict[str, str | None],
                   watchlist: list[str]) -> list[tuple[str, str]]:
    """`(label, key)` pairs: the watchlist first, then sectors A→Z with counts."""
    counts: dict[str, int] = {}
    for label in sector_map.values():
        if label:
            counts[label] = counts.get(label, 0) + 1
    return ([(f"♥ Your watchlist ({len(watchlist)})", WATCHLIST_KEY)]
            + [(f"{s} ({n})", s) for s, n in sorted(counts.items())])


def _day_pct(close: float, prev: float) -> float:
    return (close - prev) / prev * 100.0 if prev else math.nan


def rail_frame(source: str, watchlist: list[str],
               sector_map: dict[str, str | None],
               closes: dict[str, tuple[float, float]],
               query: str = "") -> pd.DataFrame:
    """The rail's rows for `source` (WATCHLIST_KEY or a sector key).

    Watchlist keeps its own order; a sector lists its members A→Z. When any
    row has a price, rows sort by Day % descending with unpriced rows last.
    `query` is a literal, case-insensitive substring on the symbol.
    """
    if source == WATCHLIST_KEY:
        symbols = list(watchlist)
    else:
        symbols = sorted(s for s, lab in sector_map.items() if lab == source)
    watched = set(watchlist)
    recs = []
    for s in symbols:
        c, p = closes.get(s, (math.nan, math.nan))
        recs.append({"Symbol": s, "Close": c,
                     "Day %": _day_pct(c, p) if s in closes else math.nan,
                     "♥": s in watched})
    df = pd.DataFrame(recs, columns=_COLUMNS)
    if query:
        df = df[df["Symbol"].str.contains(query, case=False, regex=False)]
    if df["Day %"].notna().any():
        df = df.sort_values("Day %", ascending=False, na_position="last", kind="stable")
    return df.reset_index(drop=True)
