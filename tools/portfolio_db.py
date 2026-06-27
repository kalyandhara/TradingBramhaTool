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
    "Pattern": ["total_score", "wave_pos"],
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
            """
        )
        conn.commit()
    finally:
        conn.close()


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


init_db()
