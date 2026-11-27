"""The ribbon's batch age comes from job_runs, not pipeline.log (SBC_Tool-0gv).

The ribbon used to show pipeline.log's mtime as "batch HH:MM". That log is
written by screener_pipeline's import-time logging setup, so every yfinance
error the DESK logged moved it, while the screener pipeline itself is no longer
scheduled. On 2026-11-23 it read 10:32 -- the time of a BAGMANE.NS download
error. batch_status reads the newest run of the evening batch jobs instead, and
says when that run failed.

    py -3 -m pytest tools/test_batch_status.py -q
"""
from datetime import datetime

import batch_status as bs

NOW = datetime(2026, 11, 23, 13, 0)


def _row(job, start, end=None, outcome="ok"):
    return {"job_id": job, "started_at": start, "ended_at": end, "outcome": outcome}


def test_newest_eod_run_wins_and_other_jobs_are_ignored():
    rows = [_row("alert_watcher", "2026-11-23T12:45:00", "2026-11-23T12:45:02"),
            _row("filings_watch", "2026-11-23T12:30:00", "2026-11-23T12:30:10"),
            _row("snapshot_refresh", "2026-11-20T16:30:00", "2026-11-20T16:35:46"),
            _row("daily_scanner", "2026-11-20T16:15:00", "2026-11-20T16:19:22")]
    assert bs.last_batch(rows)["job_id"] == "snapshot_refresh"


def test_no_batch_rows():
    assert bs.last_batch([_row("alert_watcher", "2026-11-23T12:45:00")]) is None
    assert bs.label(None, now=NOW) == "no batch run recorded"


def test_label_uses_the_end_time_and_age():
    r = _row("snapshot_refresh", "2026-11-20T16:30:00", "2026-11-20T16:35:46")
    assert bs.label(r, now=NOW) == "batch Fri 16:35 · 2d ago"


def test_label_minutes_and_hours():
    r = _row("daily_scanner", "2026-11-23T12:10:00", "2026-11-23T12:20:00")
    assert bs.label(r, now=NOW) == "batch Mon 12:20 · 40m ago"
    r = _row("daily_scanner", "2026-11-23T07:00:00", "2026-11-23T08:00:00")
    assert bs.label(r, now=NOW) == "batch Mon 08:00 · 5h ago"


def test_a_failed_run_says_so():
    r = _row("opportunity_daily", "2026-11-20T16:20:00", "2026-11-20T16:22:54", "FAILED")
    assert bs.label(r, now=NOW) == "batch Fri 16:22 · 2d ago · FAILED (opportunity_daily)"


def test_a_run_with_no_end_uses_its_start():
    r = _row("snapshot_refresh", "2026-11-23T12:00:00", None, "running")
    assert bs.label(r, now=NOW) == "batch Mon 12:00 · 1h ago"


def test_current_never_raises(monkeypatch):
    def boom(**k):
        raise RuntimeError("db locked")
    monkeypatch.setattr(bs.job_audit, "runs", boom)
    assert bs.current(now=NOW) == "batch status unavailable"
