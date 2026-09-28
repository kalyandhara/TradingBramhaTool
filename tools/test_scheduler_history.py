"""Tests for scheduler_core run history parser (B-113).

Run:  py -3 -m pytest tools/test_scheduler_history.py -q
"""
from __future__ import annotations

import textwrap
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

import scheduler_core as sc


@pytest.fixture
def tmp_log(tmp_path):
    """Write a log file and point a fake job at it."""
    log = tmp_path / "test_job.log"
    job = sc.JobSpec(
        id="test_job", label="Test", desc="test", task_name="Test-Job",
        kind="daily", command="echo hi", managed_bat=True,
    )
    # Point log_path at our temp file
    original = sc.LOG_DIR
    sc.LOG_DIR = tmp_path
    yield job, log
    sc.LOG_DIR = original


class TestParseRunHistory:
    def test_empty_log(self, tmp_log):
        job, log = tmp_log
        log.write_text("", encoding="utf-8")
        assert sc.parse_run_history(job) == []

    def test_single_ok_run(self, tmp_log):
        job, log = tmp_log
        log.write_text(textwrap.dedent("""\
            ===== Mon 09/23/2026 16:15:01.38 -- test_job starting =====
            some output
            ----- ok -----
        """), encoding="utf-8")
        runs = sc.parse_run_history(job)
        assert len(runs) == 1
        assert runs[0].outcome == "ok"
        assert runs[0].started == datetime(2026, 9, 23, 16, 15, 1)

    def test_failed_run(self, tmp_log):
        job, log = tmp_log
        log.write_text(textwrap.dedent("""\
            ===== Mon 09/23/2026 16:15:01.38 -- test_job starting =====
            error here
            ***** FAILED *****
        """), encoding="utf-8")
        runs = sc.parse_run_history(job)
        assert len(runs) == 1
        assert runs[0].outcome == "FAILED"

    def test_multiple_runs_newest_first(self, tmp_log):
        job, log = tmp_log
        log.write_text(textwrap.dedent("""\
            ===== Mon 09/20/2026 10:00:01.00 -- test_job starting =====
            ----- ok -----
            ===== Tue 09/21/2026 10:00:01.00 -- test_job starting =====
            ----- ok -----
            ===== Wed 09/22/2026 10:00:01.00 -- test_job starting =====
            ***** FAILED *****
        """), encoding="utf-8")
        runs = sc.parse_run_history(job)
        assert len(runs) == 3
        assert runs[0].started.day == 22  # newest first
        assert runs[0].outcome == "FAILED"
        assert runs[2].started.day == 20

    def test_duration_with_end_timestamp(self, tmp_log):
        job, log = tmp_log
        log.write_text(textwrap.dedent("""\
            ===== Mon 09/23/2026 16:15:00.00 -- test_job starting =====
            output
            ----- ok at Mon 09/23/2026 16:15:30.00 -----
        """), encoding="utf-8")
        runs = sc.parse_run_history(job)
        assert len(runs) == 1
        assert runs[0].duration_s == 30.0

    def test_running_without_end(self, tmp_log):
        job, log = tmp_log
        log.write_text(textwrap.dedent("""\
            ===== Mon 09/23/2026 16:15:01.38 -- test_job starting =====
            still going...
        """), encoding="utf-8")
        runs = sc.parse_run_history(job)
        assert len(runs) == 1
        assert runs[0].outcome == "running"

    def test_max_runs_limit(self, tmp_log):
        job, log = tmp_log
        lines = []
        for d in range(1, 12):
            lines.append(f"===== Mon 09/{d:02d}/2026 10:00:01.00 -- test_job starting =====")
            lines.append("----- ok -----")
        log.write_text("\n".join(lines), encoding="utf-8")
        runs = sc.parse_run_history(job, max_runs=5)
        assert len(runs) == 5


class TestRunSummary:
    def test_summary_counts(self, tmp_log):
        job, log = tmp_log
        log.write_text(textwrap.dedent("""\
            ===== Mon 09/20/2026 10:00:01.00 -- test_job starting =====
            ----- ok -----
            ===== Tue 09/21/2026 10:00:01.00 -- test_job starting =====
            ----- ok -----
            ===== Wed 09/22/2026 10:00:01.00 -- test_job starting =====
            ***** FAILED *****
        """), encoding="utf-8")
        s = sc.run_summary(job)
        assert s["total"] == 3
        assert s["ok"] == 2
        assert s["failed"] == 1


class TestWriteBat:
    def test_bat_includes_end_timestamp(self):
        job = sc.JOBS["sentiment_daily"]
        bat = sc.write_bat(job)
        content = bat.read_text(encoding="utf-8")
        assert "ok at %DATE% %TIME%" in content
        assert "FAILED at %DATE% %TIME%" in content


class TestRealLogs:
    def test_alert_watcher_has_runs(self):
        job = sc.JOBS["alert_watcher"]
        if not job.log_path.exists():
            pytest.skip("no alert_watcher log")
        runs = sc.parse_run_history(job, max_runs=10)
        assert len(runs) >= 1
        assert all(r.outcome in ("ok", "FAILED", "running") for r in runs)

    def test_all_summaries_parse(self):
        sums = sc.all_run_summaries()
        assert len(sums) == len(sc.JOBS)
        for jid, s in sums.items():
            assert "total" in s
