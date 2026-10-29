"""Tests for job_audit — the durable run history behind Scheduler Hub → History.

What is pinned:
  * the wrapper returns the child's exit code unchanged and tees its output;
  * a ##RESULT line is the run's result; without one, the last output line is;
  * the log tail is kept for failed runs only;
  * a command that cannot start is a recorded FAILED run, not a crash;
  * an audit write failure never fails the job;
  * day status distinguishes ok / FAILED / mixed, and backfill is idempotent.
"""
import io
import sqlite3
import sys
from datetime import date, datetime

import pytest

import job_audit as ja


@pytest.fixture
def mem(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(ja._SCHEMA)

    class _NoClose:
        def __getattr__(self, k): return getattr(conn, k)
        def close(self): pass
    monkeypatch.setattr(ja, "_conn", lambda: _NoClose())
    return conn


def _py(code):
    return [sys.executable, "-c", code]


def test_wrapper_passes_exit_code_and_output_and_records(mem):
    out = io.StringIO()
    code = ja.run_wrapped("j", _py("print('hello'); print('##RESULT 3 things'); print('bye')"), out=out)
    assert code == 0
    assert "hello" in out.getvalue() and "bye" in out.getvalue()
    row = dict(mem.execute("SELECT * FROM job_runs").fetchone())
    assert row["outcome"] == "ok" and row["exit_code"] == 0
    assert row["result"] == "3 things"
    assert row["log_tail"] is None


def test_failed_run_keeps_tail_and_last_line_as_result(mem):
    code = ja.run_wrapped("j", _py("import sys; print('step 1'); print('boom'); sys.exit(2)"),
                          out=io.StringIO())
    assert code == 2
    row = dict(mem.execute("SELECT * FROM job_runs").fetchone())
    assert row["outcome"] == "FAILED"
    assert row["result"] == "boom"
    assert "step 1" in row["log_tail"]


def test_command_that_cannot_start_is_a_failed_run(mem):
    code = ja.run_wrapped("j", ["C:/no/such/interpreter.exe"], out=io.StringIO())
    assert code == 127
    assert mem.execute("SELECT outcome FROM job_runs").fetchone()[0] == "FAILED"


def test_audit_failure_never_fails_the_job(monkeypatch):
    def broken():
        raise sqlite3.OperationalError("database is locked")
    monkeypatch.setattr(ja, "_conn", broken)
    assert ja.run_wrapped("j", _py("print('ok')"), out=io.StringIO()) == 0


def test_pick_result():
    assert ja.pick_result(["a", "##RESULT x", "b"]) == "x"
    assert ja.pick_result(["a", "", "b  ", ""]) == "b"
    assert ja.pick_result([]) is None


def test_day_status():
    rows = [
        {"job_id": "a", "started_at": "2026-10-29T09:00:00", "outcome": "ok"},
        {"job_id": "a", "started_at": "2026-10-29T09:15:00", "outcome": "FAILED"},
        {"job_id": "b", "started_at": "2026-10-29T16:00:00", "outcome": "FAILED"},
        {"job_id": "b", "started_at": "2026-10-28T16:00:00", "outcome": "ok"},
    ]
    st = ja.day_status(rows)
    assert st[("a", "2026-10-29")] == "mixed"
    assert st[("b", "2026-10-29")] == "FAILED"
    assert st[("b", "2026-10-28")] == "ok"


def test_today_board_counts_today_only():
    rows = [  # newest first
        {"job_id": "a", "started_at": "2026-10-29T10:00:00", "outcome": "FAILED", "result": "x"},
        {"job_id": "a", "started_at": "2026-10-29T09:00:00", "outcome": "ok", "result": "y"},
        {"job_id": "a", "started_at": "2026-10-28T09:00:00", "outcome": "FAILED", "result": "z"},
    ]
    (a, b) = ja.today_board(rows, ["a", "b"], today=date(2026, 10, 29))
    assert (a["runs_today"], a["failed_today"], a["last_result"]) == (2, 1, "x")
    assert b["runs_today"] == 0 and b["last_outcome"] is None


def test_record_is_idempotent_per_job_and_start(mem):
    r = ja.Run("j", datetime(2026, 10, 29, 9), datetime(2026, 10, 29, 9, 1), 0, "ok",
               source="backfill")
    ja.record(r)
    ja.record(r)
    assert mem.execute("SELECT COUNT(*) FROM job_runs").fetchone()[0] == 1


def test_backfill_skips_runs_the_wrapper_already_recorded(mem, monkeypatch):
    import scheduler_core as sched
    job = sched.JOBS["filings_watch"]
    monkeypatch.setattr(sched, "JOBS", {"filings_watch": job})
    logged = [sched.RunRecord("filings_watch", datetime(2026, 10, 29, 12, 30, 0), "ok"),
              sched.RunRecord("filings_watch", datetime(2026, 10, 29, 12, 0, 0), "ok")]
    monkeypatch.setattr(sched, "parse_run_history", lambda j, max_runs=0: logged)
    # the wrapper recorded the 12:30 run one second later than the .bat stamped it
    ja.record(ja.Run("filings_watch", datetime(2026, 10, 29, 12, 30, 1), None, 0, "ok"))
    assert ja.backfill() == {"filings_watch": 1}
    starts = [r[0] for r in mem.execute("SELECT started_at FROM job_runs ORDER BY 1")]
    assert starts == ["2026-10-29T12:00:00", "2026-10-29T12:30:01"]
