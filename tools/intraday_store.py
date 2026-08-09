#!/usr/bin/env python3
"""
intraday_store.py
Local SQLite persistence for INTRADAY OHLCV bars — the piece three separate
studies were blocked on.

Why this exists
---------------
`chart_server` fetches intraday bars and nothing persists them, which blocked,
in order:
  * **FA-2** — do NIFTY returns inside Rahu Kaal differ from outside it?
    (`analyses/Financial-Astrology-Sector-Week-Roadmap`)
  * the **80% value-area traverse rule** — needs 30-minute bars
    (`concepts/Volume-Profile`)
  * the **4H wick-zone setup** — 4H zone + 15m triggers
    (`strategies/4H-Wick-Zone-FVG-Setup`)

Three ingests in three days hit the same wall, which is what justified building
it rather than continuing to note it.

**The central fact: intraday data is PERISHABLE.** Yahoo serves intraday history
as a *rolling window*, measured 2026-08-09 against RELIANCE.NS:

    interval   deepest backfill   bars      verdict for a ~90-minute window study
    1m         ~8 days            2,555     unusable
    5m         ~81 days           4,340     not yet
    15m        ~81 days (~55 sess) 1,450    not yet — ~8 samples per weekday
    1h         ~1,075 days (~3y)  5,053     yes, coarsely

So this store has two distinct jobs, and conflating them is a mistake:

1. **Backfill 1h deep, now.** ~3 years is a real sample (~750 sessions) and makes
   the FA-2 shape testable today at hourly resolution.
2. **Accumulate 15m/5m forward.** They are only 60-day windows *today*; after a
   year of appends they are a year deep. **Every day this does not run is a day
   of 15m data that can never be recovered** — unlike daily bars, which Yahoo
   will still hand over years later.

That asymmetry is the whole argument for running it on a schedule rather than
on demand.

Design notes
------------
* **Idempotent by construction.** Primary key `(symbol, interval, ts)` with
  `INSERT OR REPLACE`, so re-running a backfill overwrites rather than
  duplicates and a partially-failed run is simply re-runnable.
* **Timestamps stored as ISO-8601 with an explicit +05:30 offset.** Never naive.
  The repo has already been bitten by `ephem.localtime` silently using the
  machine's timezone (see `panchang.py`); a naive intraday timestamp is the same
  bug waiting to happen, and it would silently misplace every Rahu Kaal slice.
* **Coverage is reportable and gaps are visible.** `coverage()` returns bars,
  first/last timestamp, distinct sessions and staleness per (symbol, interval).
  The frozen-feed lesson from `sentiment_index._sector_perf` and the CSI-300
  incident applies here too: the dangerous failure is the fetch that quietly
  returns nothing new.
* **Reads come back in the repo's shape** — lowercase `open/high/low/close/volume`,
  IST-indexed — so existing detectors accept them without adaptation.

Nothing here computes a signal. It stores bars and reports what it has.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import pandas as pd

TOOLS_DIR = Path(__file__).resolve().parent
DB_PATH = TOOLS_DIR / "intraday.db"

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

#: Deepest `period` Yahoo will actually serve per interval, measured 2026-08-09.
#: Requesting more returns an EMPTY frame with a "must be within the last N days"
#: error rather than a truncated one — so asking for too much gets you nothing,
#: not less. Hence the explicit table instead of an optimistic "max".
MAX_PERIOD: dict[str, str] = {
    "1m": "7d",
    "5m": "60d",
    "15m": "60d",
    "30m": "60d",
    "60m": "730d",
    "1h": "730d",
}

#: Short window for incremental top-ups: enough to cover a weekend plus a
#: holiday, small enough to be cheap to run daily.
UPDATE_PERIOD: dict[str, str] = {
    "1m": "7d", "5m": "7d", "15m": "7d", "30m": "7d", "60m": "7d", "1h": "7d",
}

#: What to accumulate by default. 1h for depth (backfillable to ~3y), 15m for
#: resolution (only forward-accumulable), 5m as the finest interval with a
#: usable window.
DEFAULT_INTERVALS: tuple[str, ...] = ("1h", "15m", "5m")

SCHEMA = """
CREATE TABLE IF NOT EXISTS bars (
    symbol   TEXT NOT NULL,
    interval TEXT NOT NULL,
    ts       TEXT NOT NULL,          -- ISO-8601 with +05:30 offset, never naive
    open     REAL,
    high     REAL,
    low      REAL,
    close    REAL,
    volume   REAL,
    PRIMARY KEY (symbol, interval, ts)
);
CREATE INDEX IF NOT EXISTS idx_bars_lookup ON bars (symbol, interval, ts);

CREATE TABLE IF NOT EXISTS fetch_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol       TEXT NOT NULL,
    interval     TEXT NOT NULL,
    fetched_at   TEXT NOT NULL,
    period       TEXT,
    rows_fetched INTEGER,
    rows_written INTEGER,
    first_ts     TEXT,
    last_ts      TEXT,
    note         TEXT
);
"""


# ── Connection / schema ─────────────────────────────────────────────────────
def get_connection(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | str = DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


# ── Fetch ───────────────────────────────────────────────────────────────────
def _default_download(symbol: str, period: str, interval: str) -> pd.DataFrame:
    import yfinance as yf                      # lazy: optional dep
    return yf.download(symbol, period=period, interval=interval,
                       auto_adjust=False, progress=False)


def _to_ist_iso(index: pd.DatetimeIndex) -> list[str]:
    """DatetimeIndex -> ISO strings in IST, with the offset always present.

    yfinance returns intraday indexes tz-aware in the exchange timezone; a naive
    index (which some paths produce) is assumed to be IST rather than silently
    treated as UTC, because these are NSE bars and guessing UTC would shift every
    timestamp by 5h30 and quietly relocate every clock-window slice.
    """
    idx = pd.DatetimeIndex(index)
    if idx.tz is None:
        idx = idx.tz_localize(IST)
    else:
        idx = idx.tz_convert(IST)
    return [t.isoformat() for t in idx]


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    """yfinance frame -> lowercase ohlcv, NaN bars dropped.

    Handles the MultiIndex columns yfinance returns for a single ticker in some
    versions — the repo's recurring shape wart.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [c[0] for c in out.columns]
    out.columns = [str(c).lower() for c in out.columns]
    keep = [c for c in ("open", "high", "low", "close", "volume") if c in out.columns]
    out = out[keep].dropna(subset=[c for c in keep if c != "volume"])
    return out


def upsert_bars(symbol: str, interval: str, df: pd.DataFrame,
                *, db_path: Path | str = DB_PATH) -> int:
    """Write bars idempotently. Returns rows written (inserted or replaced)."""
    norm = _normalise(df)
    if norm.empty:
        return 0
    ts = _to_ist_iso(norm.index)
    rows = [
        (symbol, interval, ts[i],
         float(norm["open"].iloc[i]), float(norm["high"].iloc[i]),
         float(norm["low"].iloc[i]), float(norm["close"].iloc[i]),
         float(norm["volume"].iloc[i]) if "volume" in norm.columns else None)
        for i in range(len(norm))
    ]
    conn = get_connection(db_path)
    try:
        conn.executemany(
            "INSERT OR REPLACE INTO bars "
            "(symbol, interval, ts, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
        conn.commit()
    finally:
        conn.close()
    return len(rows)


def _log_fetch(symbol: str, interval: str, period: str, fetched: int,
               written: int, first_ts: str | None, last_ts: str | None,
               note: str, db_path: Path | str) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO fetch_log (symbol, interval, fetched_at, period, "
            "rows_fetched, rows_written, first_ts, last_ts, note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (symbol, interval, dt.datetime.now(IST).isoformat(), period,
             fetched, written, first_ts, last_ts, note))
        conn.commit()
    finally:
        conn.close()


def fetch_and_store(symbol: str, interval: str, *, period: str | None = None,
                    download: Callable[..., pd.DataFrame] | None = None,
                    db_path: Path | str = DB_PATH) -> dict[str, Any]:
    """Fetch one (symbol, interval) and upsert it. Never raises on a bad feed.

    `period` defaults to the deepest Yahoo will serve for the interval. Asking
    for more than MAX_PERIOD returns an EMPTY frame, not a truncated one, so
    over-asking loses everything — that is why the cap is a lookup and not a
    guess.
    """
    download = download or _default_download
    period = period or MAX_PERIOD.get(interval, "60d")
    try:
        raw = download(symbol, period, interval)
    except Exception as exc:
        _log_fetch(symbol, interval, period, 0, 0, None, None,
                   f"fetch failed: {type(exc).__name__}: {exc}", db_path)
        return {"symbol": symbol, "interval": interval, "written": 0,
                "error": f"{type(exc).__name__}: {exc}"}

    norm = _normalise(raw)
    if norm.empty:
        _log_fetch(symbol, interval, period, 0, 0, None, None,
                   "empty frame (interval/period likely outside Yahoo's window)",
                   db_path)
        return {"symbol": symbol, "interval": interval, "written": 0,
                "error": "empty frame"}

    ts = _to_ist_iso(norm.index)
    written = upsert_bars(symbol, interval, raw, db_path=db_path)
    _log_fetch(symbol, interval, period, len(norm), written, ts[0], ts[-1],
               "ok", db_path)
    return {"symbol": symbol, "interval": interval, "written": written,
            "first_ts": ts[0], "last_ts": ts[-1], "error": None}


def backfill(symbols: Sequence[str],
             intervals: Iterable[str] = DEFAULT_INTERVALS, *,
             download: Callable[..., pd.DataFrame] | None = None,
             db_path: Path | str = DB_PATH,
             progress: Callable[[str], None] | None = None) -> list[dict[str, Any]]:
    """Deepest available history for every (symbol, interval). Run once, then
    rely on `update()`."""
    init_db(db_path)
    out: list[dict[str, Any]] = []
    for interval in intervals:
        for s in symbols:
            r = fetch_and_store(s, interval, download=download, db_path=db_path)
            out.append(r)
            if progress:
                progress(f"{s} {interval}: {r['written']} bars"
                         + (f" — {r['error']}" if r["error"] else ""))
    return out


def update(symbols: Sequence[str],
           intervals: Iterable[str] = DEFAULT_INTERVALS, *,
           download: Callable[..., pd.DataFrame] | None = None,
           db_path: Path | str = DB_PATH) -> list[dict[str, Any]]:
    """Cheap top-up for scheduled runs: a 7-day window per interval.

    This is the call that makes 15m/5m accumulate into something testable. It
    overlaps deliberately — re-writing a week of bars costs nothing thanks to the
    primary key, and the overlap covers weekends, holidays and a missed run.
    """
    init_db(db_path)
    out: list[dict[str, Any]] = []
    for interval in intervals:
        for s in symbols:
            out.append(fetch_and_store(
                s, interval, period=UPDATE_PERIOD.get(interval, "7d"),
                download=download, db_path=db_path))
    return out


# ── Read ────────────────────────────────────────────────────────────────────
def read_bars(symbol: str, interval: str, *,
              start: dt.datetime | dt.date | None = None,
              end: dt.datetime | dt.date | None = None,
              db_path: Path | str = DB_PATH) -> pd.DataFrame:
    """Bars as the repo's detectors expect them: lowercase ohlcv, IST index."""
    q = "SELECT ts, open, high, low, close, volume FROM bars " \
        "WHERE symbol = ? AND interval = ?"
    params: list[Any] = [symbol, interval]
    if start is not None:
        q += " AND ts >= ?"
        params.append(_bound(start, end_of_day=False))
    if end is not None:
        q += " AND ts <= ?"
        params.append(_bound(end, end_of_day=True))
    q += " ORDER BY ts"

    conn = get_connection(db_path)
    try:
        df = pd.read_sql_query(q, conn, params=params)
    finally:
        conn.close()
    if df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    idx = pd.to_datetime(df["ts"], format="ISO8601", utc=True).dt.tz_convert(IST)
    out = df.drop(columns=["ts"]).set_index(idx)
    out.index.name = "ts"
    return out


def _bound(when: dt.datetime | dt.date, *, end_of_day: bool) -> str:
    if isinstance(when, dt.datetime):
        return (when if when.tzinfo else when.replace(tzinfo=IST)).isoformat()
    t = dt.time(23, 59, 59) if end_of_day else dt.time(0, 0, 0)
    return dt.datetime.combine(when, t, tzinfo=IST).isoformat()


def session_slice(symbol: str, interval: str, day: dt.date,
                  start_time: dt.time, end_time: dt.time, *,
                  db_path: Path | str = DB_PATH) -> pd.DataFrame:
    """Bars on `day` whose timestamp falls in [start_time, end_time).

    This is the read the three blocked studies need — hand it a Rahu Kaal window
    from `panchang.day_parts()` and it returns the bars inside it. Bar timestamps
    are interval *open* times, which is the convention to hold consistently when
    comparing a window against its complement.
    """
    day_bars = read_bars(symbol, interval, start=day, end=day, db_path=db_path)
    if day_bars.empty:
        return day_bars
    t = day_bars.index.time
    mask = (t >= start_time) & (t < end_time)
    return day_bars[mask]


# ── Coverage ────────────────────────────────────────────────────────────────
def coverage(*, symbol: str | None = None, interval: str | None = None,
             db_path: Path | str = DB_PATH) -> pd.DataFrame:
    """What the store actually holds, per (symbol, interval).

    Reports distinct sessions and staleness alongside bar counts, because "bars
    exist" and "bars are current" are different facts and only reporting the
    first is how a frozen feed hides.
    """
    q = ("SELECT symbol, interval, COUNT(*) AS bars, MIN(ts) AS first_ts, "
         "MAX(ts) AS last_ts, COUNT(DISTINCT substr(ts, 1, 10)) AS sessions "
         "FROM bars")
    where, params = [], []
    if symbol:
        where.append("symbol = ?"); params.append(symbol)
    if interval:
        where.append("interval = ?"); params.append(interval)
    if where:
        q += " WHERE " + " AND ".join(where)
    q += " GROUP BY symbol, interval ORDER BY symbol, interval"

    conn = get_connection(db_path)
    try:
        df = pd.read_sql_query(q, conn, params=params)
    finally:
        conn.close()
    if df.empty:
        return df
    today = dt.datetime.now(IST).date()
    df["last_bar_age_days"] = [
        (today - dt.datetime.fromisoformat(t).date()).days for t in df["last_ts"]
    ]
    df["span_days"] = [
        (dt.datetime.fromisoformat(b).date()
         - dt.datetime.fromisoformat(a).date()).days
        for a, b in zip(df["first_ts"], df["last_ts"])
    ]
    return df


def db_size_mb(db_path: Path | str = DB_PATH) -> float:
    p = Path(db_path)
    return p.stat().st_size / 1_048_576 if p.exists() else 0.0


# ── CLI ─────────────────────────────────────────────────────────────────────
#: NIFTY plus a handful of liquid names. Deliberately small: the FA-2 question is
#: about the index, and every extra symbol multiplies fetch time for no gain on
#: that question.
DEFAULT_SYMBOLS: tuple[str, ...] = (
    "^NSEI", "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "TCS.NS",
)


def main(argv: Sequence[str] | None = None) -> int:   # pragma: no cover
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[2])
    ap.add_argument("mode", choices=("backfill", "update", "coverage"),
                    help="backfill = deepest history; update = 7-day top-up")
    ap.add_argument("--symbols", nargs="*", default=list(DEFAULT_SYMBOLS))
    ap.add_argument("--intervals", nargs="*", default=list(DEFAULT_INTERVALS))
    a = ap.parse_args(argv)

    init_db()
    if a.mode == "coverage":
        cov = coverage()
        print(cov.to_string(index=False) if not cov.empty else "store is empty")
        print(f"\ndb: {DB_PATH}  ({db_size_mb():.2f} MB)")
        return 0

    fn = backfill if a.mode == "backfill" else update
    results = fn(a.symbols, a.intervals,
                 **({"progress": lambda m: print("  " + m)}
                    if a.mode == "backfill" else {}))
    ok = sum(1 for r in results if not r["error"])
    total = sum(r["written"] for r in results)
    print(f"\n{a.mode}: {ok}/{len(results)} fetches ok, {total} bars written")
    for r in (r for r in results if r["error"]):
        print(f"  FAILED {r['symbol']} {r['interval']}: {r['error']}")
    cov = coverage()
    print()
    print(cov.to_string(index=False) if not cov.empty else "store is empty")
    print(f"\ndb: {DB_PATH}  ({db_size_mb():.2f} MB)")
    return 0


if __name__ == "__main__":                            # pragma: no cover
    raise SystemExit(main())
