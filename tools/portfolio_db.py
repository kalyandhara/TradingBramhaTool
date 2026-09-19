#!/usr/bin/env python3
"""
portfolio_db.py
Local SQLite persistence for the dashboard's Portfolio Tracker, Watchlist, and
Alerts — used by dashboard_app.py. No server, no Postgres: a single file
(trading_bramha.db) next to pipeline.log.

Alert conditions are structured (category/metric/operator/threshold), never
free-text eval'd, so checking them is just a comparison — see
dashboard_app.py's check_alert() for the on-refresh evaluation logic.
"""

import sqlite3
from datetime import date, datetime
from pathlib import Path

import pandas as pd

TOOLS_DIR = Path(__file__).resolve().parent
DB_PATH = TOOLS_DIR / "trading_bramha.db"

ALERT_CATEGORIES = ["Price", "Pattern", "Volume", "Earnings", "Performance"]
ALERT_METRICS = {
    "Price": ["close"],
    "Volume": ["volume_ratio"],
    "Pattern": ["total_score", "wave_pos", "rsi_60_40"],
    "Performance": ["portfolio_pl_pct"],
    "Earnings": [],  # uses target_date instead of metric/operator/threshold
}
ALERT_OPERATORS = [">", "<", ">=", "<=", "=="]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                entry_price REAL NOT NULL,
                quantity REAL NOT NULL,
                entry_date TEXT NOT NULL,
                stop_loss REAL,
                target REAL,
                status TEXT NOT NULL DEFAULT 'open',
                closed_price REAL,
                closed_date TEXT,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS watchlist (
                symbol TEXT PRIMARY KEY,
                added_date TEXT NOT NULL,
                notes TEXT
            );

            -- UI-2 (2026-09-10). ONE note per symbol, for every surface that
            -- shows one. The Watchlist had `watchlist.notes`, which is scoped to
            -- membership: remove a name and the note goes with it, and a note on
            -- a Scanner-Hub row had nowhere to live at all. A second store keyed
            -- differently would have been the "Vol Spike means four numbers"
            -- failure again, so there is one table and `watchlist.notes` is
            -- migrated into it rather than kept alongside.
            CREATE TABLE IF NOT EXISTS symbol_notes (
                symbol     TEXT PRIMARY KEY,
                note       TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                category TEXT NOT NULL,
                metric TEXT,
                operator TEXT,
                threshold,
                target_date TEXT,
                note TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_date TEXT NOT NULL,
                last_triggered_date TEXT
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS scanner_saved (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                scanner_name TEXT NOT NULL,
                pattern_type TEXT,
                notes TEXT,
                saved_date TEXT NOT NULL,
                UNIQUE(symbol, scanner_name)
            );

            -- Daily Opportunity Hub shortlist. One row per symbol per run date,
            -- so the table doubles as a track record: what did the funnel like on
            -- a given day, and what happened next. `market_regime` and
            -- `market_verdict` are stored WITH each row on purpose — a shortlist
            -- produced on a STAND DOWN day must never be read later as if the
            -- tape had been supportive.
            CREATE TABLE IF NOT EXISTS daily_opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT NOT NULL,
                rank INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                score REAL,
                overall_rating INTEGER,
                confluence INTEGER,
                scanners TEXT,
                sector TEXT,
                industry TEXT,
                momentum REAL,
                close REAL,
                entry REAL,
                stop REAL,
                target REAL,
                market_regime TEXT,
                market_verdict TEXT,
                universe_size INTEGER,
                notes TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(run_date, symbol)
            );
            """
        )
        # CREATE TABLE IF NOT EXISTS never alters a table that already exists, so
        # columns added after the first release need an explicit backfill or a
        # machine that has been running the job just silently keeps the old
        # schema and the new INSERT fails.
        _add_missing_columns(conn, "daily_opportunities", {
            "families": "INTEGER",        # independent scanner families hit
            "family_names": "TEXT",
            "edge_points": "REAL",        # family-capped weight the score spent
            "risk_flags": "TEXT",         # bearish scanners that also fired
        })
        # Full per-card snapshot for a run date (Opportunity Hub). Stores the
        # frozen hit payload as JSON so a historical run renders identically to
        # the day it fired, instead of being re-derived from today's prices.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_opportunity_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                rank INTEGER,
                card_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(run_date, symbol)
            );
            """
        )
        # Universe-wide RS rank walk (B-63b). A CACHE, not a journal: the walk is
        # recomputable from price history at any time, so a missing run_date
        # costs a recompute rather than a hole in a record. Keyed by run_date so
        # yesterday's grid is still readable after today's is written.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rs_rank_walk (
                run_date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                universe TEXT NOT NULL,
                t30 INTEGER,
                t15 INTEGER,
                t5 INTEGER,
                t0 INTEGER,
                created_at TEXT NOT NULL,
                UNIQUE(run_date, symbol, universe)
            );
            """
        )
        # in_universe says whether the name is a CONSTITUENT or was ranked as a
        # guest against the universe's distribution. It was missing from the
        # first release, and the consequence was not a blank but a WRONG mark:
        # `r.get("in_universe")` read None for every stored row, so the "ranked
        # against, not within" asterisk appeared on all of them and meant
        # nothing. Added here rather than in the CREATE so existing databases
        # migrate instead of keeping the old shape silently.
        _add_missing_columns(conn, "rs_rank_walk", {"in_universe": "INTEGER"})
        # Symbol -> canonical NSE macro sector (B-64, tools/sectors.py), cached
        # by CALENDAR MONTH. A CACHE, not a journal: every row is recomputable
        # from NSE's constituent CSV, so a missing period costs one fetch rather
        # than a hole in a record.
        #
        # Monthly because that is the rate the underlying fact changes. NSE
        # reconstitutes its indices semi-annually and reclassifies a name's macro
        # sector rarely; the 7-day fetch cache `sectors.symbol_map` already has is
        # about the CSV going stale, not about the sector moving. Keeping the
        # period in the key means a table rendered in September and the same table
        # rendered in October are each labelled with the vocabulary that was true
        # when they were drawn, instead of both being retro-labelled by today's.
        #
        # `sector` is NULLABLE on purpose and NULL means UNMAPPED, never
        # "Unknown" as a 23rd bucket — the same rule sectors.from_yahoo holds by
        # returning None rather than a nearest guess.
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sector_map (
                symbol TEXT NOT NULL,
                universe TEXT NOT NULL,
                sector TEXT,
                source TEXT NOT NULL,
                period TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(symbol, universe, period)
            );
            CREATE INDEX IF NOT EXISTS idx_sector_map_period
                ON sector_map(period, universe);
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_rs_walk(ranks: dict, run_date: str | None = None,
                 universe: str = "nifty500") -> int:
    """MERGE the walk into `run_date` — upsert per symbol. Returns rows written.

    Deliberately not a delete-and-replace of the whole run. Two pages compute
    this grid with different GUESTS: the Watchlist ranks its own names, the
    Scanner Hub ranks that run's hits. A wholesale replace meant whichever ran
    last silently deleted the other's guests, and the column went blank on the
    page that was not looked at most recently — observed live, 2026-09-09.

    Merging is safe because every row inside one `run_date` is computed from the
    same day's prices: two computes on the same date agree about the
    constituents and differ only in which guests they carried.
    """
    run_date = run_date or date.today().isoformat()
    now = datetime.now().isoformat(timespec="seconds")
    conn = get_connection()
    try:
        rows = [(run_date, sym, universe, r.get("t30"), r.get("t15"),
                 r.get("t5"), r.get("t0"), now,
                 1 if r.get("in_universe") else 0)
                for sym, r in ranks.items()]
        conn.executemany(
            "INSERT OR REPLACE INTO rs_rank_walk (run_date, symbol, universe,"
            " t30, t15, t5, t0, created_at, in_universe)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def get_rs_walk(run_date: str | None = None,
                universe: str = "nifty500") -> dict:
    """`{symbol: {t30, t15, t5, t0}}` for a run date, or the LATEST stored one.

    Returns `{}` when nothing is stored — the caller offers a recompute rather
    than rendering a column of blanks that looks like every name is unranked.
    """
    conn = get_connection()
    try:
        if run_date is None:
            row = conn.execute(
                "SELECT MAX(run_date) FROM rs_rank_walk WHERE universe = ?",
                (universe,)).fetchone()
            run_date = row[0] if row else None
            if not run_date:
                return {}
        cur = conn.execute(
            "SELECT symbol, t30, t15, t5, t0, in_universe FROM rs_rank_walk "
            "WHERE run_date = ? AND universe = ?", (run_date, universe))
        return {r[0]: {"t30": r[1], "t15": r[2], "t5": r[3], "t0": r[4],
                       "in_universe": bool(r[5]), "run_date": run_date}
                for r in cur.fetchall()}
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Sector map — the desk's monthly symbol -> canonical sector cache
# ──────────────────────────────────────────────────────────────────────────────

def current_period(when: "date | None" = None) -> str:
    """The cache bucket a date falls in: `YYYY-MM`."""
    return (when or date.today()).strftime("%Y-%m")


def save_sector_map(mapping: dict, universe: str = "nifty500",
                    source: str = "nse", period: str | None = None) -> int:
    """Upsert `{symbol: sector}` into one period. Returns rows written.

    MERGE, not delete-and-replace, for the reason `save_rs_walk` documents: two
    callers write this table with different symbol sets (the universe fetch
    writes constituents, a by-name lookup writes guests), and a wholesale
    replace meant whichever ran last silently dropped the other's rows.

    A None value is STORED rather than skipped. "We looked and NSE has no macro
    sector for this name" and "we never looked" are different facts, and only
    storing the first lets `get_sector_map` tell them apart — otherwise every
    unmapped name is re-fetched on every render forever.
    """
    period = period or current_period()
    now = datetime.now().isoformat(timespec="seconds")
    conn = get_connection()
    try:
        rows = [(str(sym).strip().upper(), universe,
                 (str(sec).strip() or None) if sec else None,
                 source, period, now)
                for sym, sec in mapping.items() if str(sym).strip()]
        conn.executemany(
            "INSERT OR REPLACE INTO sector_map"
            " (symbol, universe, sector, source, period, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)", rows)
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def get_sector_map(universe: str | None = None, period: str | None = None,
                   symbols=None) -> dict:
    """`{SYMBOL: sector_or_None}` for a period — THIS month unless told otherwise.

    `universe=None` merges every universe stored for the period. That is the
    form the dashboard wants: a screener hit can be any listed name, and asking
    "which universe was this cached under" at render time would make a table's
    sector column depend on which list the page happened to think it was showing.
    A symbol present under two universes carries the same NSE label in both, so
    the merge has nothing to resolve.

    Returns `{}` when the period is empty, which the caller reads as a cache MISS
    and refills — distinct from a dict of Nones, which is a period that was
    fetched and genuinely had no label for those names.
    """
    period = period or current_period()
    sql = "SELECT symbol, sector FROM sector_map WHERE period = ?"
    args: list = [period]
    if universe:
        sql += " AND universe = ?"
        args.append(universe)
    if symbols is not None:
        syms = [str(s).strip().upper() for s in symbols if str(s).strip()]
        if not syms:
            return {}
        sql += f" AND symbol IN ({','.join('?' * len(syms))})"
        args.extend(syms)
    conn = get_connection()
    try:
        return {r[0]: r[1] for r in conn.execute(sql, args).fetchall()}
    finally:
        conn.close()


def sector_map_periods() -> list:
    """Stored periods, newest first — what the cache actually holds."""
    conn = get_connection()
    try:
        return [r[0] for r in conn.execute(
            "SELECT DISTINCT period FROM sector_map ORDER BY period DESC")]
    finally:
        conn.close()


def prune_sector_map(keep: int = 6) -> int:
    """Drop all but the `keep` newest periods. Returns rows deleted.

    The history is worth something (it is how a reclassification becomes
    visible), but not unboundedly — this is a cache of a fact anyone can refetch.
    """
    periods = sector_map_periods()
    if len(periods) <= keep:
        return 0
    drop = periods[keep:]
    conn = get_connection()
    try:
        cur = conn.execute(
            f"DELETE FROM sector_map WHERE period IN ({','.join('?' * len(drop))})",
            drop)
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def _add_missing_columns(conn, table: str, columns: dict[str, str]) -> None:
    """ALTER TABLE ADD COLUMN for any column not already present."""
    have = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    for name, decl in columns.items():
        if name not in have:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")


# ──────────────────────────────────────────────────────────────────────────────
# Positions
# ──────────────────────────────────────────────────────────────────────────────

def add_position(symbol: str, entry_price: float, quantity: float, entry_date: str,
                  stop_loss: float | None = None, target: float | None = None,
                  notes: str = "") -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO positions (symbol, entry_price, quantity, entry_date, "
            "stop_loss, target, status, notes) VALUES (?, ?, ?, ?, ?, ?, 'open', ?)",
            (symbol.upper(), entry_price, quantity, entry_date, stop_loss, target, notes),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


_POSITION_COLUMNS = frozenset({
    "symbol", "entry_price", "quantity", "entry_date",
    "stop_loss", "target", "status", "closed_price", "closed_date", "notes",
})


def update_position(position_id: int, **fields) -> None:
    if not fields:
        return
    bad = set(fields) - _POSITION_COLUMNS
    if bad:
        raise ValueError(f"update_position: unknown column(s): {bad}")
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn = get_connection()
    try:
        conn.execute(f"UPDATE positions SET {cols} WHERE id = ?",
                     (*fields.values(), position_id))
        conn.commit()
    finally:
        conn.close()


def close_position(position_id: int, closed_price: float,
                    closed_date: str | None = None) -> None:
    update_position(
        position_id,
        status="closed",
        closed_price=closed_price,
        closed_date=closed_date or date.today().isoformat(),
    )


def get_open_positions() -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql_query(
            "SELECT * FROM positions WHERE status = 'open' ORDER BY entry_date DESC", conn
        )
    finally:
        conn.close()


def get_closed_positions() -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql_query(
            "SELECT * FROM positions WHERE status = 'closed' ORDER BY closed_date DESC", conn
        )
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Watchlist
# ──────────────────────────────────────────────────────────────────────────────

def add_watchlist_symbol(symbol: str, notes: str = "") -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO watchlist (symbol, added_date, notes) VALUES (?, ?, ?)",
            (symbol.upper(), date.today().isoformat(), notes),
        )
        conn.commit()
    finally:
        conn.close()


def get_symbol_notes(symbols=None) -> dict[str, str]:
    """{SYMBOL: note} for the given symbols, or every stored note when None.

    Returns a plain dict so a caller can `.get(sym, "")` without a second query
    per row — these are read once per table render, not once per cell.
    """
    conn = get_connection()
    try:
        if symbols is None:
            rows = conn.execute(
                "SELECT symbol, note FROM symbol_notes").fetchall()
        else:
            syms = [str(x).upper() for x in symbols]
            if not syms:
                return {}
            qs = ",".join("?" * len(syms))
            rows = conn.execute(
                f"SELECT symbol, note FROM symbol_notes WHERE symbol IN ({qs})",
                syms).fetchall()
        return {r[0]: (r[1] or "") for r in rows}
    finally:
        conn.close()


def set_symbol_note(symbol: str, note: str) -> None:
    """Write one symbol's note. Creates the row; blank note deletes it.

    Deleting on blank rather than storing "" keeps the table to symbols that
    actually carry a note, so `get_symbol_notes()` with no argument stays small
    and "has a note" is a row's existence rather than a string test.

    Unlike `update_watchlist_notes` this is NOT scoped to watchlist membership —
    that is the whole reason it exists. A note about a name you are not watching
    is still a note, and removing a name from the watchlist should not silently
    destroy what you wrote about it.
    """
    sym = str(symbol).upper()
    conn = get_connection()
    try:
        if not (note or "").strip():
            conn.execute("DELETE FROM symbol_notes WHERE symbol = ?", (sym,))
        else:
            conn.execute(
                "INSERT INTO symbol_notes (symbol, note, updated_at) "
                "VALUES (?, ?, ?) ON CONFLICT(symbol) DO UPDATE SET "
                "note = excluded.note, updated_at = excluded.updated_at",
                (sym, note, datetime.now().isoformat(timespec="seconds")),
            )
        conn.commit()
    finally:
        conn.close()


def migrate_watchlist_notes_to_symbol_notes() -> int:
    """One-way lift of existing `watchlist.notes` into `symbol_notes`.

    Idempotent and NON-destructive: it never overwrites a note already in
    `symbol_notes` (that one is newer by construction) and it leaves
    `watchlist.notes` in place. Dropping the old column would make a rollback
    lossy for no gain — the column simply stops being read.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT symbol, notes FROM watchlist "
            "WHERE notes IS NOT NULL AND TRIM(notes) <> ''").fetchall()
        moved = 0
        now = datetime.now().isoformat(timespec="seconds")
        for sym, note in rows:
            cur = conn.execute(
                "INSERT INTO symbol_notes (symbol, note, updated_at) "
                "VALUES (?, ?, ?) ON CONFLICT(symbol) DO NOTHING",
                (str(sym).upper(), note, now))
            moved += cur.rowcount
        conn.commit()
        return moved
    finally:
        conn.close()


def update_watchlist_notes(symbol: str, notes: str) -> int:
    """Edit ONLY the note on an existing watchlist row. Returns rows changed.

    Deliberately not `add_watchlist_symbol(symbol, notes)`: that is an
    INSERT OR REPLACE, so reusing it to edit a note would silently reset
    `added_date` to today — quietly rewriting when you started watching the name,
    which is a fact the row exists to carry.

    Returns 0 for a symbol not on the list rather than inserting one, so an edit
    can never create a row by accident.
    """
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE watchlist SET notes = ? WHERE symbol = ?",
            (notes or "", symbol.upper()),
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def remove_watchlist_symbol(symbol: str) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol.upper(),))
        conn.commit()
    finally:
        conn.close()


def get_watchlist() -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql_query("SELECT * FROM watchlist ORDER BY added_date DESC", conn)
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Alerts
# ──────────────────────────────────────────────────────────────────────────────

def add_alert(symbol: str, category: str, metric: str | None = None,
              operator: str | None = None, threshold: float | str | None = None,
              target_date: str | None = None, note: str = "") -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO alerts (symbol, category, metric, operator, threshold, "
            "target_date, note, active, created_date) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)",
            (symbol.upper(), category, metric, operator, threshold, target_date, note,
             datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_alerts(active_only: bool = True) -> pd.DataFrame:
    conn = get_connection()
    try:
        query = "SELECT * FROM alerts"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY created_date DESC"
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


def deactivate_alert(alert_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("UPDATE alerts SET active = 0 WHERE id = ?", (alert_id,))
        conn.commit()
    finally:
        conn.close()


def mark_alert_triggered(alert_id: int, when: str | None = None) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE alerts SET last_triggered_date = ? WHERE id = ?",
            (when or datetime.now().isoformat(timespec="seconds"), alert_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_alert(alert_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        conn.commit()
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Settings (key-value)
# ──────────────────────────────────────────────────────────────────────────────

def get_setting(key: str, default: str | None = None) -> str | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default
    finally:
        conn.close()


def set_setting(key: str, value: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
        )
        conn.commit()
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Scanner saved results
# ──────────────────────────────────────────────────────────────────────────────

def save_scanner_hit(symbol: str, scanner_name: str, pattern_type: str = "",
                     notes: str = "") -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO scanner_saved "
            "(symbol, scanner_name, pattern_type, notes, saved_date) VALUES (?, ?, ?, ?, ?)",
            (symbol.upper(), scanner_name, pattern_type, notes, date.today().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def remove_scanner_hit(symbol: str, scanner_name: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM scanner_saved WHERE symbol = ? AND scanner_name = ?",
            (symbol.upper(), scanner_name),
        )
        conn.commit()
    finally:
        conn.close()


def get_saved_scanner_hits(scanner_name: str | None = None) -> pd.DataFrame:
    conn = get_connection()
    try:
        if scanner_name:
            return pd.read_sql_query(
                "SELECT * FROM scanner_saved WHERE scanner_name = ? ORDER BY saved_date DESC",
                conn, params=(scanner_name,),
            )
        return pd.read_sql_query(
            "SELECT * FROM scanner_saved ORDER BY saved_date DESC", conn
        )
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Daily Opportunity Hub shortlist
# ──────────────────────────────────────────────────────────────────────────────
def save_daily_opportunities(rows: list[dict], run_date: str | None = None) -> int:
    """Replace the shortlist for `run_date` and return the number of rows saved.

    Replace, not append: a re-run on the same day supersedes the earlier one
    rather than leaving two half-lists that later read as twenty picks.
    """
    run_date = run_date or date.today().isoformat()
    now = datetime.now().isoformat(timespec="seconds")
    conn = get_connection()
    try:
        conn.execute("DELETE FROM daily_opportunities WHERE run_date = ?", (run_date,))
        for r in rows:
            conn.execute(
                """
                INSERT INTO daily_opportunities
                    (run_date, rank, symbol, score, overall_rating, confluence,
                     families, family_names, edge_points, risk_flags,
                     scanners, sector, industry, momentum, close, entry, stop,
                     target, market_regime, market_verdict, universe_size, notes,
                     created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (run_date, r.get("rank"), r.get("symbol"), r.get("score"),
                 r.get("overall_rating"), r.get("confluence"),
                 r.get("families"), r.get("family_names"), r.get("edge_points"),
                 r.get("risk_flags"), r.get("scanners"),
                 r.get("sector"), r.get("industry"), r.get("momentum"),
                 r.get("close"), r.get("entry"), r.get("stop"), r.get("target"),
                 r.get("market_regime"), r.get("market_verdict"),
                 r.get("universe_size"), r.get("notes"), now),
            )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def get_daily_opportunities(run_date: str | None = None) -> pd.DataFrame:
    """Shortlist for one date, or the whole history when `run_date` is None."""
    conn = get_connection()
    try:
        if run_date:
            return pd.read_sql_query(
                "SELECT * FROM daily_opportunities WHERE run_date = ? ORDER BY rank",
                conn, params=(run_date,),
            )
        return pd.read_sql_query(
            "SELECT * FROM daily_opportunities ORDER BY run_date DESC, rank", conn
        )
    finally:
        conn.close()


def get_opportunity_run_dates() -> list[str]:
    """Dates that have a stored shortlist, newest first."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT DISTINCT run_date FROM daily_opportunities ORDER BY run_date DESC")
        return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


def save_opportunity_cards(cards: list[dict], run_date: str | None = None) -> int:
    """Replace the full per-card snapshots for `run_date`. Each item is
    {"symbol", "rank", "card_json"} — card_json already serialised by the caller
    (it owns the numpy/pandas coercion). Replace-on-rerun, mirroring the summary."""
    run_date = run_date or date.today().isoformat()
    now = datetime.now().isoformat(timespec="seconds")
    conn = get_connection()
    try:
        conn.execute("DELETE FROM daily_opportunity_cards WHERE run_date = ?", (run_date,))
        for c in cards:
            conn.execute(
                "INSERT INTO daily_opportunity_cards "
                "(run_date, symbol, rank, card_json, created_at) VALUES (?,?,?,?,?)",
                (run_date, c["symbol"], c.get("rank"), c["card_json"], now))
        conn.commit()
        return len(cards)
    finally:
        conn.close()


def get_opportunity_cards(run_date: str | None = None) -> list[dict]:
    """[{symbol, rank, card_json}] for a run date, rank order. Empty if none."""
    run_date = run_date or date.today().isoformat()
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT symbol, rank, card_json FROM daily_opportunity_cards "
            "WHERE run_date = ? ORDER BY rank", (run_date,))
        return [{"symbol": s, "rank": r, "card_json": j} for s, r, j in cur.fetchall()]
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Scanner run cache
# ──────────────────────────────────────────────────────────────────────────────
# Stores the full card list from every scanner run so the user can reload
# yesterday's (or today's) results without re-fetching OHLCV data. One row per
# symbol per (scanner_name, run_date); the complete card dict is serialised as
# JSON so no schema migration is needed when scanner fields evolve.

def _ensure_scanner_cache_table(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS scanner_run_cache (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date      TEXT    NOT NULL,
            scanner_name  TEXT    NOT NULL,
            symbol        TEXT    NOT NULL,
            card_json     TEXT    NOT NULL,
            created_at    TEXT    NOT NULL,
            UNIQUE(run_date, scanner_name, symbol)
        );
        CREATE INDEX IF NOT EXISTS idx_src_scanner_date
            ON scanner_run_cache(scanner_name, run_date);
    """)


def save_scanner_run(scanner_name: str, cards: list[dict],
                     run_date: str | None = None) -> int:
    """Persist a complete scanner result list.  Replaces any prior run for the
    same (scanner_name, run_date) pair so a re-run always reflects the latest
    data rather than appending stale rows."""
    import json as _json
    run_date = run_date or date.today().isoformat()
    now = datetime.now().isoformat(timespec="seconds")
    conn = get_connection()
    try:
        _ensure_scanner_cache_table(conn)
        conn.execute(
            "DELETE FROM scanner_run_cache WHERE run_date = ? AND scanner_name = ?",
            (run_date, scanner_name),
        )
        for card in cards:
            sym = card.get("symbol", "")
            conn.execute(
                "INSERT OR REPLACE INTO scanner_run_cache "
                "(run_date, scanner_name, symbol, card_json, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (run_date, scanner_name, sym.upper(), _json.dumps(card), now),
            )
        conn.commit()
        return len(cards)
    finally:
        conn.close()


def get_scanner_run(scanner_name: str, run_date: str) -> list[dict]:
    """Restore a cached scanner run.  Returns [] if nothing is stored."""
    import json as _json
    conn = get_connection()
    try:
        _ensure_scanner_cache_table(conn)
        rows = conn.execute(
            "SELECT card_json FROM scanner_run_cache "
            "WHERE scanner_name = ? AND run_date = ? ORDER BY id",
            (scanner_name, run_date),
        ).fetchall()
        return [_json.loads(r[0]) for r in rows]
    finally:
        conn.close()


def get_scanner_run_dates(scanner_name: str) -> list[str]:
    """Dates (newest first) that have a stored run for this scanner."""
    conn = get_connection()
    try:
        _ensure_scanner_cache_table(conn)
        rows = conn.execute(
            "SELECT DISTINCT run_date FROM scanner_run_cache "
            "WHERE scanner_name = ? ORDER BY run_date DESC",
            (scanner_name,),
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def delete_scanner_run(scanner_name: str, run_date: str) -> None:
    """Remove a single cached run (e.g. to force a fresh fetch)."""
    conn = get_connection()
    try:
        _ensure_scanner_cache_table(conn)
        conn.execute(
            "DELETE FROM scanner_run_cache WHERE scanner_name = ? AND run_date = ?",
            (scanner_name, run_date),
        )
        conn.commit()
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Hidden Treasures — historical scan fact table
# ──────────────────────────────────────────────────────────────────────────────
# One row per (run_date, symbol). Stores the conviction score, ownership deltas,
# quality overlay, and the full card JSON so any past scan reproduces exactly.
# Analogous to daily_opportunities but for the small/micro-cap discovery lane.

def _ensure_hidden_treasures_table(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS hidden_treasures (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date         TEXT    NOT NULL,
            symbol           TEXT    NOT NULL,
            name             TEXT,
            rank             INTEGER,
            score            REAL,
            inst_delta       REAL,
            promoter_delta   REAL,
            pledge_pct       REAL,
            pledge_flag      INTEGER DEFAULT 0,
            roce             REAL,
            opm              REAL,
            debt_to_equity   REAL,
            market_cap_cr    REAL,
            universe_kind    TEXT,
            universe_size    INTEGER,
            index_source     TEXT,
            card_json        TEXT    NOT NULL,
            created_at       TEXT    NOT NULL,
            UNIQUE(run_date, symbol)
        );
        CREATE INDEX IF NOT EXISTS idx_ht_date
            ON hidden_treasures(run_date);
        CREATE INDEX IF NOT EXISTS idx_ht_symbol
            ON hidden_treasures(symbol);
    """)


def save_hidden_treasures_run(hits: list[dict], universe_kind: str = "both",
                              universe_size: int = 0,
                              run_date: str | None = None) -> int:
    """Persist a Hidden Treasures discovery run. Replaces any prior run for the
    same run_date so a re-run reflects the latest data."""
    import json as _json
    run_date = run_date or date.today().isoformat()
    now = datetime.now().isoformat(timespec="seconds")
    conn = get_connection()
    try:
        _ensure_hidden_treasures_table(conn)
        conn.execute("DELETE FROM hidden_treasures WHERE run_date = ?", (run_date,))
        for rank, h in enumerate(hits, 1):
            q = h.get("quality") or {}
            conn.execute(
                """
                INSERT INTO hidden_treasures
                    (run_date, symbol, name, rank, score, inst_delta,
                     promoter_delta, pledge_pct, pledge_flag,
                     roce, opm, debt_to_equity, market_cap_cr,
                     universe_kind, universe_size, index_source,
                     card_json, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (run_date, h.get("symbol"), h.get("name"), rank,
                 h.get("score"), h.get("inst_delta"),
                 h.get("promoter_delta"), h.get("pledge_pct"),
                 1 if h.get("pledge_flag") else 0,
                 q.get("roce"), q.get("opm"), q.get("debt_to_equity"),
                 q.get("market_cap_cr"),
                 universe_kind, universe_size, h.get("index"),
                 _json.dumps(h), now),
            )
        conn.commit()
        return len(hits)
    finally:
        conn.close()


def get_hidden_treasures_run(run_date: str) -> list[dict]:
    """Restore a cached Hidden Treasures run. Returns [] if nothing stored."""
    import json as _json
    conn = get_connection()
    try:
        _ensure_hidden_treasures_table(conn)
        rows = conn.execute(
            "SELECT card_json FROM hidden_treasures "
            "WHERE run_date = ? ORDER BY rank",
            (run_date,),
        ).fetchall()
        return [_json.loads(r[0]) for r in rows]
    finally:
        conn.close()


def get_hidden_treasures_dates() -> list[str]:
    """Dates (newest first) that have a stored Hidden Treasures run."""
    conn = get_connection()
    try:
        _ensure_hidden_treasures_table(conn)
        rows = conn.execute(
            "SELECT DISTINCT run_date FROM hidden_treasures ORDER BY run_date DESC"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def get_hidden_treasures_history(symbol: str) -> pd.DataFrame:
    """All historical Hidden Treasures appearances for a symbol, newest first."""
    conn = get_connection()
    try:
        _ensure_hidden_treasures_table(conn)
        return pd.read_sql_query(
            "SELECT run_date, rank, score, inst_delta, promoter_delta, "
            "pledge_pct, roce, opm, debt_to_equity, market_cap_cr "
            "FROM hidden_treasures WHERE symbol = ? ORDER BY run_date DESC",
            conn, params=(symbol.upper(),),
        )
    finally:
        conn.close()


init_db()
