"""Tests for the Scheduler Hub History tab's shaping (desk_pages/job_history).

Pinned: every registry job appears even with no runs; a job that left the
registry but has runs still appears; the grid marks mixed days; durations
read as minutes and seconds.
"""
from datetime import date

from desk_pages import job_history as jh


ROWS = [  # newest first, as job_audit.runs returns them
    {"job_id": "filings_watch", "started_at": "2026-10-29T12:30:00", "outcome": "FAILED",
     "duration_s": 3.0, "exit_code": 2, "result": "NSE did not answer", "source": "wrapper"},
    {"job_id": "filings_watch", "started_at": "2026-10-29T12:00:00", "outcome": "ok",
     "duration_s": 7.0, "exit_code": 0, "result": "1762 filings · 16 new", "source": "wrapper"},
    {"job_id": "batch_screener", "started_at": "2026-10-28T16:25:00", "outcome": "ok",
     "duration_s": 905.0, "exit_code": 0, "result": None, "source": "backfill"},
]


def test_board_lists_every_job_and_counts_today():
    b = jh.board_frame(ROWS, today=date(2026, 10, 29)).set_index("Job")
    fw = b.loc["Filings Watch (NSE, my names)"]
    assert (fw["Runs today"], fw["Failed today"], fw["Last"]) == (2, 1, "❌")
    assert b.loc["Daily Digest Email"]["Last run"] == "never"
    assert "batch_screener (not in registry)" in b.index


def test_grid_marks_mixed_and_missing_days():
    g = jh.grid_frame(ROWS, 2, today=date(2026, 10, 29))
    assert list(g.columns) == ["10-29", "10-28"]
    assert g.loc["Filings Watch (NSE, my names)", "10-29"] == "🟠"
    assert g.loc["Filings Watch (NSE, my names)", "10-28"] == "·"


def test_history_formats_duration():
    h = jh.history_frame(ROWS)
    assert list(h["Duration"]) == ["3s", "7s", "15m 05s"]
