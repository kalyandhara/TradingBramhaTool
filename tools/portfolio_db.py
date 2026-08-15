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
        conn.commit()
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


def update_position(position_id: int, **fields) -> None:
    if not fields:
        return
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


init_db()
