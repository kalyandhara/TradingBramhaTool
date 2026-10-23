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
import re
import logging
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

CLOSES_PATH: Path = Path(__file__).resolve().parent / "cache" / "last_close.json"
WATCHLIST_KEY: str = "__watchlist__"

_COLUMNS = ["Symbol", "Close", "Day %", "♥"]


def write_closes(frame: pd.DataFrame, trade_date: str | None,
                 path: Path = CLOSES_PATH) -> int:
    """Persist `symbol, close, prev_close` from a bhavcopy frame; return rows written.

    Rows with a missing, non-finite or non-positive close / prev_close are
    skipped, so the JSON never holds NaN/inf or a price that would make Day %
    infinite. When NO row survives (a half-published, all-NA bhavcopy) nothing
    is written and the previous snapshot stays: an empty file would blank a
    rail that had good closes. Never raises: a snapshot that could not be
    written must not break the scan that loaded the bhavcopy.
    """
    try:
        d = frame[["symbol", "close", "prev_close"]].copy()
        d["close"] = pd.to_numeric(d["close"], errors="coerce")
        d["prev_close"] = pd.to_numeric(d["prev_close"], errors="coerce")
        d = d[np.isfinite(d["close"]) & np.isfinite(d["prev_close"])
              & (d["close"] > 0) & (d["prev_close"] > 0)]
        rows = {str(s).strip(): [float(c), float(p)]
                for s, c, p in zip(d["symbol"], d["close"], d["prev_close"])
                if str(s).strip()}
        if not rows:
            log.warning("close snapshot not written: no usable rows")
            return 0
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


def refresh_closes(loader, path: Path = CLOSES_PATH) -> tuple[bool, str]:
    """The rail's ↻: run `loader` (`trending_stocks.load_bhav`) and say what
    happened as `(ok, message)` — never raises, because a failed refresh is a
    toast, not a broken Home.

    `load_bhav` already writes the snapshot but discards the count, so the
    frame is written again here to learn whether any row was usable.
    """
    try:
        df, trade_date = loader()
    except Exception as e:
        return False, f"Price refresh failed ({e}). The last snapshot stays."
    if df is None:
        return False, "Couldn't reach NSE for prices. The last snapshot stays."
    if write_closes(df, trade_date, path) == 0:
        return False, "NSE returned no usable prices. The last snapshot stays."
    return True, f"Closes refreshed ({trade_date or 'date unknown'})"


def rail_sector_map() -> dict[str, str | None]:
    """This month's stored sector map, read from disk only.

    `sectors.lookup` refills a cache MISS from NSE — right for a scan the user
    started, wrong for the rail, which renders on every Home load. A miss (a
    new month before any scan ran) or an unreadable database is `{}`, which
    the rail shows as "Sector map unavailable".
    """
    try:
        import portfolio_db as pdb
        pdb.init_db()
        return pdb.get_sector_map()
    except Exception as e:
        log.warning("rail sector map unavailable: %s", e)
        return {}


def pick_index(keys: list[str], saved: str | None) -> int:
    """Position of the remembered picker key, else 0 (the watchlist).

    The picker remembers its KEY, not its label: "Banks (12)" becoming
    "Banks (13)" must not drop the user back to the watchlist.
    """
    return keys.index(saved) if saved in keys else 0


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


def names_to_add(picked: list[str], watchlist: list[str]) -> list[str]:
    """Picked names not already watched, first-seen order, no duplicates.

    `portfolio_db.add_watchlist_symbol` is INSERT OR REPLACE, so re-adding a
    watched name would reset its note and `added_date` — the facts the row
    exists to carry.
    """
    have = set(watchlist)
    out: list[str] = []
    for s in picked:
        if s not in have and s not in out:
            out.append(s)
    return out


def table_key(source: str, query: str, trade_date: str | None, nonce: int) -> str:
    """Widget key for the rail table.

    Streamlit keeps a dataframe's row selection under its key, as row
    POSITIONS. A key that ignored the source, filter or snapshot date would
    carry a selection onto different rows; `nonce` is bumped after Add/Remove
    so the rows that shifted up are not pre-selected for a second click.
    """
    return f"home_rail_tbl|{source}|{query}|{trade_date}|{nonce}"


def chart_symbol(sym: str) -> str:
    """The ticker the :5001 chart server expects: bare NSE names get `.NS`;
    indices (`^…`) and already-suffixed names pass through — the same rule
    as `ui_tables.chart_url`."""
    s = str(sym).strip().upper()
    return s if (s.startswith("^") or "." in s) else f"{s}.NS"


_SAFE_SYMBOL = re.compile(r"\^?[A-Z0-9][A-Z0-9&._-]{0,24}")


def is_safe_symbol(sym: str) -> bool:
    """NSE/BSE ticker characters only — no markup or URL metacharacters."""
    return bool(_SAFE_SYMBOL.fullmatch(str(sym).strip().upper()))


def rail_rows(frame: pd.DataFrame, source: str) -> list[dict]:
    """`rail_frame` as JSON-safe dicts for the watch_rail component (B-180).

    NaN becomes None (JSON has no NaN). `watched` is None in watchlist mode,
    where every row is watched and the ♥ column is not drawn.
    """
    def num(v):
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        return None if math.isnan(f) else f

    mode_watch = source == WATCHLIST_KEY
    return [{"symbol": str(r["Symbol"]),
             "close": num(r["Close"]),
             "day_pct": num(r["Day %"]),
             "watched": None if mode_watch else bool(r["♥"]),
             "chart": chart_symbol(r["Symbol"])}
            for _, r in frame.iterrows() if is_safe_symbol(r["Symbol"])]
