"""batch_status.py -- the ribbon's "batch" age, from job_runs (SBC_Tool-0gv).

The desk ribbon used to show pipeline.log's mtime as "batch HH:MM · Xm ago".
That log is written by screener_pipeline's import-time logging setup, so any
yfinance error the desk itself logged moved it -- on 2026-11-23 it read 10:32,
the time of a BAGMANE.NS download error -- and the screener pipeline it was
named for is no longer scheduled.

The evening batch that actually feeds the desk is recorded run by run in
job_runs (job_audit.py). This module reports the newest run of those jobs, its
end time and age, and says when that run FAILED. Times are the machine-local
naive ISO strings job_audit writes.
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable

import job_audit

#: The evening jobs whose output the desk's tables and snapshots are built from.
EOD_JOBS = ("daily_scanner", "opportunity_daily", "snapshot_refresh")


def last_batch(rows: Iterable[dict], jobs: Iterable[str] = EOD_JOBS) -> dict | None:
    """The newest row (by started_at) among `jobs`, or None."""
    wanted = set(jobs)
    best = None
    for r in rows:
        if r.get("job_id") in wanted and (best is None or r["started_at"] > best["started_at"]):
            best = r
    return best


def _rel(seconds: float) -> str:
    if seconds < 3600:
        return f"{max(0, int(seconds // 60))}m ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h ago"
    return f"{int(seconds // 86400)}d ago"


def label(row: dict | None, *, now: datetime | None = None) -> str:
    """'batch Fri 16:35 · 2d ago', plus ' · FAILED (<job>)' when it failed."""
    if row is None:
        return "no batch run recorded"
    when = datetime.fromisoformat(row.get("ended_at") or row["started_at"])
    now = now or datetime.now()
    out = f"batch {when:%a %H:%M} · {_rel((now - when).total_seconds())}"
    if row.get("outcome") == "FAILED":
        out += f" · FAILED ({row['job_id']})"
    return out


def current(*, now: datetime | None = None) -> str:
    """The ribbon text. Never raises: the ribbon renders on every page."""
    try:
        return label(last_batch(job_audit.runs(days=14)), now=now)
    except Exception:                       # noqa: BLE001 -- ribbon must not break
        return "batch status unavailable"
