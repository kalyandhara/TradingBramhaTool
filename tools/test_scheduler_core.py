"""Tests for the schtasks argv builder — B-77.

These exist because of ONE bug, and it is the bug this file is really about:
`register_argv` emitted `/sc MINUTE` for the interval job, which creates a
**one-time** trigger with a repetition attached. `schtasks /create` returned
SUCCESS, the task showed as Enabled, and the Scheduler Hub reported it
registered — but `Next Run Time` was `N/A` and it would never have fired again.

A registration that succeeds and never runs is worse than one that fails, so the
schedule shape is pinned here rather than left to be re-verified by hand against
a live Task Scheduler.

Run:  python -m pytest tools/test_scheduler_core.py -q
"""
from __future__ import annotations

import pytest

import scheduler_core as sch


def _argv(job_id: str, **kw) -> list[str]:
    return sch.register_argv(sch.JOBS[job_id], **kw)


def _flag(argv: list[str], name: str) -> str | None:
    """Value following `name` in an argv list, or None if the flag is absent."""
    return argv[argv.index(name) + 1] if name in argv else None


# ── The regression this file exists for ──────────────────────────────────────

def test_an_interval_job_never_uses_a_one_time_minute_trigger():
    """`/sc MINUTE` is a ONE-TIME trigger. It registers clean and never recurs."""
    argv = _argv("alert_watcher")
    assert _flag(argv, "/sc") != "MINUTE"
    assert "/mo" not in argv, "/mo belongs to the MINUTE form that cannot recur"


def test_an_interval_job_recurs_weekly_on_the_trading_days():
    argv = _argv("filings_watch")
    assert _flag(argv, "/sc") == "WEEKLY"
    assert _flag(argv, "/d") == "MON,TUE,WED,THU,FRI"
    assert "SAT" not in argv and "SUN" not in argv


def test_the_alert_bot_runs_all_day_every_day_and_gates_itself():
    """A local 09:15-15:45 window was 18:45-01:15 IST on this US-Eastern PC.
    The watcher now gates NSE symbols on the IST clock, so the task just
    repeats round the clock (crypto has no session)."""
    argv = _argv("alert_watcher")
    assert _flag(argv, "/sc") == "WEEKLY"
    assert _flag(argv, "/d") == "MON,TUE,WED,THU,FRI,SAT,SUN"
    assert _flag(argv, "/st") == "00:00"
    assert _flag(argv, "/du") == "0023:59"


def test_the_repeat_window_is_expressed_as_a_duration_not_an_end_time():
    """schtasks silently DROPPED `/et` here (`Repeat: Until: Time: None`)."""
    argv = _argv("alert_watcher", time="09:15", end="15:45")
    assert "/et" not in argv
    assert _flag(argv, "/ri") == "15"
    assert _flag(argv, "/du") == "0006:30"   # 09:15 -> 15:45


def test_a_daily_job_runs_on_trading_weekdays_only():
    # /sc DAILY fired every after-close job on Saturdays and Sundays too —
    # equity_snapshot "failed" on 2026-10-17 and 10-18 with nothing to price.
    argv = _argv("opportunity_daily")
    assert _flag(argv, "/sc") == "WEEKLY"
    assert _flag(argv, "/d") == "MON,TUE,WED,THU,FRI"
    assert _flag(argv, "/st") == "16:20"
    assert "/ri" not in argv and "/du" not in argv


# ── Task settings schtasks /create cannot express ────────────────────────────

def test_settings_script_enables_catch_up_and_battery_runs():
    ps = sch.task_settings_ps("TradingBramha-SnapshotRefresh")
    assert "Get-ScheduledTask -TaskName 'TradingBramha-SnapshotRefresh'" in ps
    assert "StartWhenAvailable = $true" in ps
    assert "DisallowStartIfOnBatteries = $false" in ps
    assert "StopIfGoingOnBatteries = $false" in ps
    assert "Set-ScheduledTask" in ps


def test_settings_script_quotes_a_task_name_with_an_apostrophe():
    assert "'it''s'" in sch.task_settings_ps("it's")


def test_register_applies_settings_after_a_successful_create(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(sch, "HERE", tmp_path)
    monkeypatch.setattr(sch, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(sch, "_schtasks",
                        lambda argv: (calls.append(argv[0]),
                                      sch.subprocess.CompletedProcess(argv, 0, "ok", ""))[1])
    ok, msg = sch.register(sch.JOBS["sentiment_daily"])
    assert ok and calls == ["schtasks", "powershell"]


def test_generated_bats_force_utf8_python_output(monkeypatch, tmp_path):
    # Task Scheduler's console is cp1252; a "≥" in a progress line killed
    # snapshot_refresh at step 6/16 on every scheduled run.
    monkeypatch.setattr(sch, "HERE", tmp_path)
    monkeypatch.setattr(sch, "LOG_DIR", tmp_path / "logs")
    bat = sch.write_bat(sch.JOBS["snapshot_refresh"]).read_text(encoding="utf-8")
    assert "set PYTHONIOENCODING=utf-8" in bat
    assert bat.index("PYTHONIOENCODING") < bat.index("snapshot_refresh.py")


# ── The duration arithmetic ──────────────────────────────────────────────────

@pytest.mark.parametrize("start,end,expected", [
    ("09:15", "15:45", "0006:30"),   # the real market window
    ("09:00", "10:00", "0001:00"),
    ("09:15", "09:30", "0000:15"),   # shorter than one repeat is still valid
    ("00:00", "23:59", "0023:59"),
])
def test_duration_spans_start_to_end(start, end, expected):
    assert sch._duration(start, end) == expected


def test_a_non_positive_window_becomes_a_full_day_rather_than_zero():
    """A zero duration would repeat forever with no bound, or not at all.

    Both are worse than assuming the caller meant "all day", and this is reachable
    from the hub's own time inputs.
    """
    assert sch._duration("15:45", "09:15") == "0023:59"
    assert sch._duration("09:15", "09:15") == "0023:59"


def test_a_malformed_time_falls_back_instead_of_raising():
    """The hub passes user-typed strings straight through."""
    assert sch._duration("", "15:45") == "0006:30"
    assert sch._duration("9am", "3pm") == "0006:30"


# ── Overrides the hub passes ─────────────────────────────────────────────────

def test_hub_overrides_reach_the_argv():
    argv = _argv("alert_watcher", time="10:00", end="14:00", interval=30)
    assert _flag(argv, "/st") == "10:00"
    assert _flag(argv, "/ri") == "30"
    assert _flag(argv, "/du") == "0004:00"


def test_every_job_targets_its_own_task_name_and_an_existing_bat():
    for jid, job in sch.JOBS.items():
        argv = sch.register_argv(job)
        assert _flag(argv, "/tn") == job.task_name, jid
        # daily_scanner's bat is owned by the Scanner Hub, not generated here.
        assert str(_flag(argv, "/tr")).endswith(".bat"), jid
