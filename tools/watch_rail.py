#!/usr/bin/env python3
"""watch_rail.py — pure logic behind Home's left watchlist rail (B-179).

Three jobs, none of which touch Streamlit or the network:

  1. The CLOSE SNAPSHOT. Before B-179 the desk had no closing-price cache on
     disk: every scan pulled the whole-market bhavcopy into memory
     (`st.cache_data`, 15 min) and nothing kept it. Home's rule is that it
     never fetches on load, so a rail with prices needs prices that are
     already on disk. `trending_stocks.load_bhav` writes them here whenever
     any section (or the rail's ↻) loads the bhavcopy; the rail only reads.

  2. The PICKER. One list: your default watchlist first, then your named
     watchlists, then every canonical NSE sector (`sectors.py` — NSE macro is
     canonical). The key is the raw sector string (or `__list__:<id>`), never
     parsed back out of the "(N)" label, because sector names carry
     punctuation ("Oil Gas & Consumable Fuels").

  3. The ROWS. Symbol · name · sparkline · Close · Day % for whichever source
     is picked. A name with no sector or no snapshot row is shown blank,
     never guessed.

  4. The SPARKLINE STORE (2026-10-22). One month of closes per symbol, on
     disk, filled only by a user action (↻, or adding a stock) through one
     batched download. The rail reads it; Home still never fetches on load.
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
SPARKS_PATH: Path = Path(__file__).resolve().parent / "cache" / "rail_sparks.json"
WATCHLIST_KEY: str = "__watchlist__"
LIST_PREFIX: str = "__list__:"

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


def list_key(list_id: int) -> str:
    return f"{LIST_PREFIX}{int(list_id)}"


def list_id_of(key: str | None) -> int | None:
    """The named list's id for a `__list__:<id>` key, else None."""
    if not key or not str(key).startswith(LIST_PREFIX):
        return None
    try:
        return int(str(key)[len(LIST_PREFIX):])
    except ValueError:
        return None


def is_list_source(key: str | None) -> bool:
    """The default watchlist or a named one — anything that is not a sector."""
    return key == WATCHLIST_KEY or list_id_of(key) is not None


def read_sparks(path: Path = SPARKS_PATH) -> dict[str, list[float]]:
    """`{SYMBOL: [closes oldest→newest]}`, or `{}` when missing/unreadable."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {str(s): [float(x) for x in v] for s, v in payload["rows"].items()}
    except Exception:
        return {}


def refresh_sparks(symbols: list[str], downloader,
                   path: Path = SPARKS_PATH) -> tuple[bool, str]:
    """Fetch closes for `symbols` with `downloader(symbols) -> {sym: [closes]}`
    and merge them into the store. Symbols that came back empty keep their old
    line. Never raises: `(ok, message)` for a toast.
    """
    syms = [s for s in dict.fromkeys(symbols) if is_safe_symbol(s)]
    if not syms:
        return False, "No symbols to fetch."
    try:
        got = downloader(syms) or {}
    except Exception as e:
        return False, f"Sparkline fetch failed ({e})."
    fresh = {}
    for s, closes in got.items():
        vals = []
        for c in closes:
            try:
                f = float(c)
            except (TypeError, ValueError):
                continue
            if math.isfinite(f) and f > 0:
                vals.append(f)
        if len(vals) >= 2:
            fresh[str(s)] = vals[-30:]
    if not fresh:
        return False, "No price history came back."
    rows = read_sparks(path)
    rows.update(fresh)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"saved_at": datetime.now().isoformat(timespec="seconds"),
                                   "rows": rows}, allow_nan=False), encoding="utf-8")
        tmp.replace(path)
    except Exception as e:
        return False, f"Sparklines not saved ({e})."
    return True, f"Sparklines for {len(fresh)} of {len(syms)}"


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
                   watchlist: list[str],
                   lists: list[tuple[int, str, int]] = ()) -> list[tuple[str, str]]:
    """`(label, key)` pairs: the default watchlist, then named lists
    (`(id, name, count)`, in the order given), then sectors A→Z with counts."""
    counts: dict[str, int] = {}
    for label in sector_map.values():
        if label:
            counts[label] = counts.get(label, 0) + 1
    return ([(f"♥ Your watchlist ({len(watchlist)})", WATCHLIST_KEY)]
            + [(f"☰ {name} ({n})", list_key(i)) for i, name, n in lists]
            + [(f"{s} ({n})", s) for s, n in sorted(counts.items())])


def _day_pct(close: float, prev: float) -> float:
    return (close - prev) / prev * 100.0 if prev else math.nan


def rail_frame(source: str, watchlist: list[str],
               sector_map: dict[str, str | None],
               closes: dict[str, tuple[float, float]],
               query: str = "", members: list[str] | None = None) -> pd.DataFrame:
    """The rail's rows for `source` (WATCHLIST_KEY, a named-list key whose
    symbols are `members`, or a sector key).

    A list keeps its own order; a sector lists its members A→Z. When any
    row has a price, rows sort by Day % descending with unpriced rows last.
    `query` is a literal, case-insensitive substring on the symbol.
    """
    if source == WATCHLIST_KEY:
        symbols = list(watchlist)
    elif list_id_of(source) is not None:
        symbols = list(members or [])
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


def rail_rows(frame: pd.DataFrame, source: str,
              names: dict[str, str] | None = None,
              sparks: dict[str, list[float]] | None = None) -> list[dict]:
    """`rail_frame` as JSON-safe dicts for the watch_rail component (B-180).

    NaN becomes None (JSON has no NaN). `watched` is None in any list mode,
    where the ♥ column is not drawn. `name` is the company name ('' when
    unknown) and `spark` the stored closes ([] when none).
    """
    names, sparks = names or {}, sparks or {}
    def num(v):
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        return None if math.isnan(f) else f

    mode_watch = is_list_source(source)
    return [{"symbol": str(r["Symbol"]),
             "name": str(names.get(str(r["Symbol"]), "") or ""),
             "close": num(r["Close"]),
             "day_pct": num(r["Day %"]),
             "watched": None if mode_watch else bool(r["♥"]),
             "spark": [round(x, 4) for x in sparks.get(str(r["Symbol"]), [])],
             "chart": chart_symbol(r["Symbol"])}
            for _, r in frame.iterrows() if is_safe_symbol(r["Symbol"])]


#: Cell formats the watch_rail component knows how to draw for scan tables.
SCAN_FORMATS = ("x", "pct", "date", "text", "num")


def scan_rows(df: pd.DataFrame | None, extra_cols: list[dict], *, close_col: str,
              pct_col: str, names: dict[str, str] | None = None,
              sparks: dict[str, list[float]] | None = None) -> list[dict]:
    """A scan's hits as rows for the watch_rail component in table mode.

    Same row shape as `rail_rows` plus `extra` = {key: value} for each of
    `extra_cols` ({key, label, fmt, width}). `pct_col` fills the Day % slot,
    whatever day it measures (the caller labels it). Missing columns and NaN
    become None; symbols with markup characters are dropped.
    """
    for c in extra_cols:
        if c.get("fmt") not in SCAN_FORMATS:
            raise ValueError(f"unknown cell format {c.get('fmt')!r}")
    if df is None or getattr(df, "empty", True):
        return []
    names, sparks = names or {}, sparks or {}

    def num(v):
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        return None if math.isnan(f) else f

    def cell(r, c):
        v = r.get(c["key"]) if c["key"] in r else None
        if c["fmt"] in ("x", "pct", "num"):
            return num(v)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return None
        return str(v)

    out = []
    for _, r in df.iterrows():
        sym = str(r["symbol"])
        if not is_safe_symbol(sym):
            continue
        out.append({"symbol": sym, "name": str(names.get(sym, "") or ""),
                    "close": num(r.get(close_col)), "day_pct": num(r.get(pct_col)),
                    "watched": None,
                    "spark": [round(x, 4) for x in sparks.get(sym, [])],
                    "chart": chart_symbol(sym),
                    "extra": {c["key"]: cell(r, c) for c in extra_cols}})
    return out


CANDIDATE_CAP = 30


def _candidate(key: str, label: str, rows: list[dict], fallback: str) -> dict | None:
    """One switcher entry. The pattern/note goes in the header when every row
    shares it, and on each row (`tag`) only when the rows differ."""
    rows = [r for r in rows if is_safe_symbol(r["symbol"])]
    if not rows:
        return None
    notes = {r["note"] for r in rows}
    one = len(notes) == 1
    return {"key": key, "label": label, "count": len(rows),
            "header": (next(iter(notes)) or fallback) if one else fallback,
            "tag": not one,
            "df": pd.DataFrame(rows, columns=["symbol", "rating", "note"])}


def candidate_lists(hits: list[dict] | None, ran_for: str, sent: dict | None,
                    watchlist: pd.DataFrame | None) -> list[dict]:
    """The Stock Analyzer's candidate lists: Scanner hits (by Overall Rating,
    unrated last, capped), a list sent from another table, and watchlist names
    not already in either. Empty lists are left out."""
    ranked = sorted(hits or [], key=lambda h: (h.get("overall") is not None,
                                               h.get("overall") or 0), reverse=True)
    sc = [{"symbol": str(h["symbol"]), "rating": h.get("overall"),
           "note": str(h.get("pattern_type") or ran_for or "")}
          for h in ranked if is_safe_symbol(h.get("symbol", ""))][:CANDIDATE_CAP]
    items = (sent or {}).get("items") or []
    se = [{"symbol": str(i["symbol"]), "rating": None, "note": str(i.get("note") or "")}
          for i in items[:60]]
    seen = {r["symbol"] for r in sc} | {r["symbol"] for r in se}
    wl = []
    if watchlist is not None and not watchlist.empty:
        for _, r in watchlist.iterrows():
            s = str(r["symbol"])
            if s not in seen:
                n = r.get("notes") if "notes" in watchlist.columns else ""
                wl.append({"symbol": s, "rating": None,
                           "note": "" if n is None or (isinstance(n, float) and math.isnan(n)) else str(n)})
    out = [_candidate("scanner", "Scanner", sc, ran_for or "Scanner"),
           _candidate("sent", "Sent", se, (sent or {}).get("source") or "Sent list"),
           _candidate("watchlist", "♥ Watchlist", wl, "Watchlist")]
    return [c for c in out if c]


def with_closes(df: pd.DataFrame, closes: dict[str, tuple[float, float]]) -> pd.DataFrame:
    """`close` and `day_pct` from the stored closes file; NaN when unknown."""
    out = df.copy()
    out["close"] = [closes[s][0] if s in closes else float("nan") for s in out["symbol"]]
    out["day_pct"] = [_day_pct(*closes[s]) if s in closes else float("nan")
                      for s in out["symbol"]]
    return out
