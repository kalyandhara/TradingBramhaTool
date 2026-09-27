#!/usr/bin/env python3
"""
snapshot_store.py — persisted report snapshots (SQLite) with a last-run stamp.

The problem
-----------
Most "generate on demand" surfaces in the dashboard (Sector Map's index fetch,
the money-flow grid, the deals tables, the Finviz read, …) lived only in
`st.session_state` or a short `st.cache_data` TTL. Every fresh open of the app
began empty, and every reader paid the fetch again.

The fix
-------
One table, `snapshots`, in the dashboard's existing `trading_bramha.db`. A
snapshot is a named, picklable payload (dicts of DataFrames are fine) plus the
parameters it was computed with, the wall-clock `run_at`, elapsed seconds and a
status (`ok` | `error`). One row per (name, run_date); a re-run on the same date
replaces the row, so the table holds one snapshot per snapshot per day.

The page loads `load_latest(name)` on open and shows `run_at` as "Last run"; the
scheduled job (`snapshot_refresh.py`) and the page's "Refresh now" button both
write through `save()`. Pruning keeps 90 days by default.

This module is import-safe without Streamlit; the dashboard adds its own thin
cache on top (see `dashboard_app.snapshot_panel`).
"""
from __future__ import annotations

import json
import pickle
import sqlite3
import zlib
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

TOOLS_DIR = Path(__file__).resolve().parent
DB_PATH = TOOLS_DIR / "trading_bramha.db"

RETENTION_DAYS = 90


@dataclass
class SnapshotMeta:
    name: str
    run_date: str
    run_at: str                     # ISO seconds
    status: str                     # ok | error
    params: dict
    elapsed: float
    error: Optional[str] = None
    nbytes: int = 0

    @property
    def run_at_dt(self) -> datetime:
        return datetime.fromisoformat(self.run_at)

    def age(self, now: datetime | None = None) -> timedelta:
        return (now or datetime.now()) - self.run_at_dt

    @property
    def ok(self) -> bool:
        return self.status == "ok"


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            run_date    TEXT NOT NULL,
            run_at      TEXT NOT NULL,
            status      TEXT NOT NULL,
            params_json TEXT NOT NULL DEFAULT '{}',
            elapsed     REAL NOT NULL DEFAULT 0,
            error       TEXT,
            payload     BLOB,
            UNIQUE(name, run_date)
        );
        CREATE INDEX IF NOT EXISTS idx_snapshots_name_runat
            ON snapshots(name, run_at DESC);
    """)


def _encode(payload: Any) -> bytes:
    return zlib.compress(pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL), 6)


def _decode(blob: bytes | None) -> Any:
    if not blob:
        return None
    return pickle.loads(zlib.decompress(blob))


def _row_meta(r: sqlite3.Row) -> SnapshotMeta:
    return SnapshotMeta(
        name=r["name"], run_date=r["run_date"], run_at=r["run_at"],
        status=r["status"], params=json.loads(r["params_json"] or "{}"),
        elapsed=float(r["elapsed"] or 0), error=r["error"],
        nbytes=int(r["nbytes"] or 0) if "nbytes" in r.keys() else 0,
    )


# ── write ─────────────────────────────────────────────────────────────────────
def save(name: str, payload: Any, *, params: dict | None = None,
         elapsed: float = 0.0, status: str = "ok", error: str | None = None,
         run_at: datetime | None = None, db_path: Path | None = None) -> SnapshotMeta:
    """Persist one snapshot; replaces any row for the same (name, run_date).

    An `error` row keeps the previous day's payload out of the way — it stores
    NO payload — so `load_latest` (which only returns ok rows by default) keeps
    serving the last good result while the badge shows the failed attempt.
    """
    run_at = run_at or datetime.now()
    run_date = run_at.date().isoformat()
    blob = _encode(payload) if status == "ok" else None
    conn = _connect(db_path)
    try:
        _ensure(conn)
        conn.execute("DELETE FROM snapshots WHERE name = ? AND run_date = ?",
                     (name, run_date))
        conn.execute(
            "INSERT INTO snapshots (name, run_date, run_at, status, params_json, "
            "elapsed, error, payload) VALUES (?,?,?,?,?,?,?,?)",
            (name, run_date, run_at.isoformat(timespec="seconds"), status,
             json.dumps(params or {}, default=str), float(elapsed), error, blob),
        )
        conn.commit()
    finally:
        conn.close()
    return SnapshotMeta(name=name, run_date=run_date,
                        run_at=run_at.isoformat(timespec="seconds"), status=status,
                        params=params or {}, elapsed=elapsed, error=error,
                        nbytes=len(blob) if blob else 0)


def save_error(name: str, error: str, *, params: dict | None = None,
               elapsed: float = 0.0, db_path: Path | None = None) -> SnapshotMeta:
    """Record a failed run WITHOUT clobbering the last good payload for a
    different date. If today already holds an ok row it is kept and only the
    error is noted on it (a failed refresh must not erase a good morning run)."""
    run_date = date.today().isoformat()
    conn = _connect(db_path)
    try:
        _ensure(conn)
        row = conn.execute(
            "SELECT status FROM snapshots WHERE name = ? AND run_date = ?",
            (name, run_date)).fetchone()
        if row and row["status"] == "ok":
            conn.execute(
                "UPDATE snapshots SET error = ? WHERE name = ? AND run_date = ?",
                (f"last refresh failed: {error}", name, run_date))
            conn.commit()
            return latest_meta(name, db_path=db_path)  # type: ignore[return-value]
    finally:
        conn.close()
    return save(name, None, params=params, elapsed=elapsed, status="error",
                error=error, db_path=db_path)


# ── read ──────────────────────────────────────────────────────────────────────
def latest_meta(name: str, *, ok_only: bool = False,
                db_path: Path | None = None) -> Optional[SnapshotMeta]:
    conn = _connect(db_path)
    try:
        _ensure(conn)
        q = ("SELECT name, run_date, run_at, status, params_json, elapsed, error, "
             "length(payload) AS nbytes FROM snapshots WHERE name = ?")
        if ok_only:
            q += " AND status = 'ok'"
        q += " ORDER BY run_at DESC LIMIT 1"
        r = conn.execute(q, (name,)).fetchone()
        return _row_meta(r) if r else None
    finally:
        conn.close()


def load_latest(name: str, *, db_path: Path | None = None
                ) -> tuple[Optional[SnapshotMeta], Any]:
    """(meta, payload) of the newest OK snapshot, or (None, None)."""
    conn = _connect(db_path)
    try:
        _ensure(conn)
        r = conn.execute(
            "SELECT name, run_date, run_at, status, params_json, elapsed, error, "
            "length(payload) AS nbytes, payload FROM snapshots "
            "WHERE name = ? AND status = 'ok' ORDER BY run_at DESC LIMIT 1",
            (name,)).fetchone()
        if not r:
            return None, None
        return _row_meta(r), _decode(r["payload"])
    finally:
        conn.close()


def load(name: str, run_date: str, *, db_path: Path | None = None
         ) -> tuple[Optional[SnapshotMeta], Any]:
    conn = _connect(db_path)
    try:
        _ensure(conn)
        r = conn.execute(
            "SELECT name, run_date, run_at, status, params_json, elapsed, error, "
            "length(payload) AS nbytes, payload FROM snapshots "
            "WHERE name = ? AND run_date = ?", (name, run_date)).fetchone()
        if not r:
            return None, None
        return _row_meta(r), _decode(r["payload"])
    finally:
        conn.close()


def run_dates(name: str, *, ok_only: bool = True,
              db_path: Path | None = None) -> list[str]:
    """Dates (newest first) with a stored snapshot for `name`."""
    conn = _connect(db_path)
    try:
        _ensure(conn)
        q = "SELECT run_date FROM snapshots WHERE name = ?"
        if ok_only:
            q += " AND status = 'ok'"
        q += " ORDER BY run_date DESC"
        return [r["run_date"] for r in conn.execute(q, (name,)).fetchall()]
    finally:
        conn.close()


def overview(*, db_path: Path | None = None) -> list[SnapshotMeta]:
    """Newest row per name — for the Scheduler Hub status table."""
    conn = _connect(db_path)
    try:
        _ensure(conn)
        rows = conn.execute("""
            SELECT s.name, s.run_date, s.run_at, s.status, s.params_json,
                   s.elapsed, s.error, length(s.payload) AS nbytes
            FROM snapshots s
            JOIN (SELECT name, MAX(run_at) AS mx FROM snapshots GROUP BY name) m
              ON m.name = s.name AND m.mx = s.run_at
            ORDER BY s.name
        """).fetchall()
        return [_row_meta(r) for r in rows]
    finally:
        conn.close()


# ── housekeeping ──────────────────────────────────────────────────────────────
def prune(days: int = RETENTION_DAYS, *, db_path: Path | None = None) -> int:
    """Drop rows older than `days`. Never drops the newest ok row of a name,
    however old — a stale answer beats no answer on page load."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = _connect(db_path)
    try:
        _ensure(conn)
        cur = conn.execute("""
            DELETE FROM snapshots WHERE run_date < ? AND id NOT IN (
                SELECT id FROM snapshots s
                WHERE status = 'ok' AND run_at = (
                    SELECT MAX(run_at) FROM snapshots
                    WHERE name = s.name AND status = 'ok'))
        """, (cutoff,))
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def delete(name: str, run_date: str | None = None, *,
           db_path: Path | None = None) -> int:
    conn = _connect(db_path)
    try:
        _ensure(conn)
        if run_date:
            cur = conn.execute("DELETE FROM snapshots WHERE name = ? AND run_date = ?",
                               (name, run_date))
        else:
            cur = conn.execute("DELETE FROM snapshots WHERE name = ?", (name,))
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def is_stale(meta: SnapshotMeta | None, *, close_hour: int = 16,
             close_minute: int = 0, now: datetime | None = None) -> bool:
    """A snapshot is stale once a trading session has closed since it ran.

    "Today's close" is the most recent weekday close at or before `now`; a
    snapshot taken after that instant is fresh. Weekend runs stay fresh until
    Monday's close.
    """
    if meta is None:
        return True
    now = now or datetime.now()
    d = now.date()
    last_close = datetime.combine(d, datetime.min.time()).replace(
        hour=close_hour, minute=close_minute)
    if now < last_close:
        d = d - timedelta(days=1)
    while d.weekday() >= 5:
        d = d - timedelta(days=1)
    last_close = datetime.combine(d, datetime.min.time()).replace(
        hour=close_hour, minute=close_minute)
    return meta.run_at_dt < last_close
