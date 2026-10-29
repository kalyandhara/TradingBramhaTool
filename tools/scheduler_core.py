#!/usr/bin/env python3
"""
scheduler_core.py — data-driven job registry + Windows Task Scheduler wrappers.

Backs the dashboard's Scheduler Hub. Generalises the one-off "Daily Scanner
Scheduler" panel (Scanner Hub) into a registry of batch jobs — each a command run
by a generated `.bat`, registered as a Windows Scheduled Task via `schtasks`.

Jobs (extend JOBS to add more):
  • alert_watcher — the live alert bot (node alert_watcher.js --once), INTERVAL
    mode: every N minutes between market open and close.
  • daily_scanner — the existing after-close scanner suite, DAILY mode. Its task
    (TradingBramha-DailyScanner) may already exist; represented here so the hub
    can show/manage it too.
  • hidden_treasures_daily — small/micro-cap discovery, stored per run date.

Registering/removing a task changes persistent OS configuration — those calls are
made only when the user acts (the hub buttons), never as a side effect of import.

CLI (read-only unless you pass register/remove/run):
  py -3 tools/scheduler_core.py list
  py -3 tools/scheduler_core.py status alert_watcher
  py -3 tools/scheduler_core.py writebat alert_watcher
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
LOG_DIR = HERE / "logs"

# Match the interpreter the existing daily-scanner task uses.
PYTHON_EXE = r"C:\Users\Owner\AppData\Local\Python\pythoncore-3.14-64\python.exe"


def _node_exe() -> str:
    return shutil.which("node") or "node"


@dataclass
class JobSpec:
    id: str
    label: str
    desc: str
    task_name: str
    kind: str                       # "daily" | "interval"
    command: str                    # the command line the .bat executes
    managed_bat: bool = True        # False = bat owned elsewhere (don't regenerate)
    default_time: str = "16:15"     # daily run time / interval start (HH:MM, 24h)
    default_end: str = "15:45"      # interval window end (HH:MM, 24h)
    default_interval: int = 15      # interval minutes
    elevate: bool = False           # /rl HIGHEST (needs admin to register)
    days: str = "MON,TUE,WED,THU,FRI"   # weekly-trigger days (/d); see _TRADING_DAYS

    @property
    def bat_path(self) -> Path:
        return HERE / f"{self.id}.bat"

    @property
    def log_path(self) -> Path:
        return LOG_DIR / f"{self.id}.log"


# ── Registry ─────────────────────────────────────────────────────────────────
JOBS: dict[str, JobSpec] = {
    "alert_watcher": JobSpec(
        id="alert_watcher",
        label="Alert Bot (SVP / indicator signals)",
        desc="Runs the alert engine every interval, round the clock. Each symbol "
             "is evaluated only while its market is open (NSE 09:15-15:45 IST, "
             "crypto always), firing on pattern-buildup transitions. Delivery "
             "per alert_config.json. Needs chart_server running.",
        task_name="TradingBramha-AlertWatcher",
        kind="interval",
        command=f'"{_node_exe()}" "{HERE / "alert_watcher.js"}" --once',
        # All day, every day: the watcher gates each symbol on ITS market's
        # clock (NSE 09:15-15:45 IST; crypto never). A local "09:15-15:45" was
        # 18:45-01:15 IST on this US-Eastern machine, i.e. after the close.
        default_time="00:00", default_end="23:59", default_interval=15,
        days="MON,TUE,WED,THU,FRI,SAT,SUN",
    ),
    "daily_scanner": JobSpec(
        id="daily_scanner",
        label="Daily Scanner Suite",
        desc="Runs the full pattern-scanner suite after market close and writes a "
             "dated results JSON. Also configurable from Scanner Hub.",
        task_name="TradingBramha-DailyScanner",
        kind="daily",
        command="",                 # owned by scanner_daily.bat
        managed_bat=False,
        default_time="16:15",
    ),
    "growth_snapshot": JobSpec(
        id="growth_snapshot",
        label="Growth Snapshot (High-Growth Screener)",
        desc="Refreshes the yfinance fundamentals snapshot behind the High-Growth "
             "Screener (no screener.in login). Runs daily but only re-fetches when "
             "the snapshot is 7+ days old, since statements change quarterly.",
        task_name="TradingBramha-GrowthSnapshot",
        kind="daily",
        command=f'"{PYTHON_EXE}" "{HERE / "growth_screen.py"}" --refresh',
        default_time="17:10",
    ),
    "sentiment_daily": JobSpec(
        id="sentiment_daily",
        label="Daily Market Sentiment",
        desc="Recomputes the 0-100 sentiment composite after close and stores it "
             "in sentiment_history. Home's verdict reads the STORED reading, so "
             "without this the desk shows a hand-refreshed number and counts its "
             "own staleness as a caution flag.",
        task_name="TradingBramha-SentimentDaily",
        kind="daily",
        command=f'"{PYTHON_EXE}" "{HERE / "sentiment_index.py"}"',
        # After the shortlist, not before: nothing in the funnel reads sentiment,
        # so the ordering is free, and running last keeps the heaviest jobs first.
        default_time="16:30",
    ),
    "opportunity_daily": JobSpec(
        id="opportunity_daily",
        label="Daily Opportunity Shortlist",
        desc="Runs the Opportunity Hub funnel headlessly after market close and "
             "stores the ranked shortlist run-date-wise in the daily_opportunities "
             "table (read by the Hub's run-date selector and the digest email). "
             "Replace-on-rerun per date. ~a few minutes at universe 500.",
        task_name="TradingBramha-OpportunityDaily",
        kind="daily",
        command=f'"{PYTHON_EXE}" "{HERE / "opportunity_daily.py"}" '
                f'--universe 500 --top 100',
        default_time="16:20",
    ),
    "snapshot_refresh": JobSpec(
        id="snapshot_refresh",
        label="Report Snapshot Refresh",
        desc="Recomputes every registered report snapshot (Sector Map index data, "
             "money flow, turnover share, volume shockers, sentiment, market "
             "health, Finviz, TradingView scan, deals, gap & volume, market brief) "
             "after the close and stores each in the snapshots table with its run "
             "timestamp. Pages load the stored snapshot on open; ↻ refreshes on "
             "demand. One failing snapshot is logged and skipped. ~5-10 min.",
        task_name="TradingBramha-SnapshotRefresh",
        kind="daily",
        command=f'"{PYTHON_EXE}" "{HERE / "snapshot_refresh.py"}" --all',
        default_time="16:30",
    ),
    "equity_snapshot": JobSpec(
        id="equity_snapshot",
        label="Portfolio Equity Snapshot",
        desc="Writes one row per trading day to equity_snapshots: equity "
             "(capital + realised + unrealised P&L), capital, deployed and open "
             "risk, dated by the last priced bar. This is the RECORDED half of "
             "the Portfolio page's drawdown (B-110); before it has run, the "
             "drawdown is a reconstruction from the positions table. Seconds.",
        task_name="TradingBramha-EquitySnapshot",
        kind="daily",
        command=f'"{PYTHON_EXE}" "{HERE / "equity_snapshot.py"}"',
        default_time="16:10",
    ),
    "hidden_treasures_daily": JobSpec(
        id="hidden_treasures_daily",
        label="Hidden Treasures Discovery",
        desc="Warms the small/micro-cap shareholding cache (only quarters not "
             "yet cached are fetched), ranks the NSE Both universe with the "
             "quality overlay, and stores the top 100 in the hidden_treasures "
             "table with the run's universe and counts. The page opens on the "
             "latest stored run. A manual Discover replaces that day's run. "
             "One yfinance call per name, so ~5-15 min.",
        task_name="TradingBramha-HiddenTreasuresDaily",
        kind="daily",
        command=f'"{PYTHON_EXE}" "{HERE / "hidden_treasures_daily.py"}" '
                f'--kind both --top 100',
        # Last: shareholding moves quarterly, so nothing downstream waits on it,
        # and it is the slowest job after the snapshot refresh.
        default_time="16:45",
    ),
    "rec_audit": JobSpec(
        id="rec_audit",
        label="Recommendation Audit",
        desc="Re-scores every past Opportunity Hub pick against NIFTY 500, Smallcap "
             "250 and its sector index (entry = next open) and stores it in "
             "rec_audit.db for the Recommendation Audit page. Also rewrites "
             "reports/audit/YYYY-MM.md, so each month's last run freezes that "
             "month's report. ~3 min.",
        task_name="TradingBramha-RecAudit",
        kind="daily",
        command=f'"{PYTHON_EXE}" "{HERE / "rec_audit_job.py"}"',
        # After opportunity_daily (16:20) has saved today's picks.
        default_time="17:30",
    ),
    "filings_watch": JobSpec(
        id="filings_watch",
        label="Filings Watch (NSE, my names)",
        desc="Reads today's NSE corporate-filings stream, keeps the material "
             "filings on held / watchlist / latest-pick names, and emails the ones "
             "not sent before. Also feeds the digest's filings section. A failed "
             "NSE read exits 2 and sends nothing. Seconds.",
        task_name="TradingBramha-FilingsWatch",
        kind="interval",
        command=f'"{PYTHON_EXE}" -X utf8 "{HERE / "filings_watch.py"}"',
        # The whole day, not a local "market hours" window: this machine runs on
        # US Eastern time, and NSE filings land through the IST day and evening
        # (results are often filed after the close).
        default_time="00:00", default_end="23:59", default_interval=30,
    ),
    "daily_digest": JobSpec(
        id="daily_digest",
        label="Daily Digest Email",
        desc="Emails the end-of-day digest: market brief, sentiment and verdict, "
             "the stored shortlist, open positions, today's filings on my names "
             "and the alerts that fired. Reads what the earlier jobs stored, so "
             "it runs last.",
        task_name="TradingBramha-DailyDigest",
        kind="daily",
        command=f'"{PYTHON_EXE}" "{HERE / "daily_digest_email.py"}"',
        # After rec_audit (17:30), the last job that writes something it reads.
        default_time="17:45",
    ),
    "batch_screener": JobSpec(
        id="batch_screener",
        label="Batch Screener (Category-Based)",
        desc="Runs all screeners in category-based batches (Entry, Trend, Risk, Pattern), "
             "aggregates confluence, and generates segregated reports (Entry, Risk, Confluence). "
             "Replaces the older scanner_daily_runner. ~15-20 min for universe 500.",
        task_name="TradingBramha-BatchScreener",
        kind="daily",
        command="",  # owned by scanner_batch.bat
        managed_bat=False,
        default_time="16:25",  # Between opportunity_daily (16:20) and sentiment_daily (16:30)
    ),
}


def _scanner_bat() -> Path:
    return HERE / "scanner_daily.bat"


def _batch_bat() -> Path:
    return HERE / "scanner_batch.bat"


# ── .bat generation ──────────────────────────────────────────────────────────
def write_bat(job: JobSpec) -> Path:
    """Write the .bat wrapper for a managed job. Returns the bat path."""
    if not job.managed_bat:
        if job.id == "daily_scanner":
            return _scanner_bat()
        elif job.id == "batch_screener":
            return _batch_bat()
        else:
            return job.bat_path
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = job.log_path
    src = (
        "@echo off\r\n"
        f'set REPO={REPO}\r\n'
        f'set LOG={log}\r\n'
        # The task's console is cp1252; without this a non-ASCII print kills
        # a Python job (snapshot_refresh died at step 6/16 every run).
        'set PYTHONIOENCODING=utf-8\r\n'
        'cd /d "%REPO%"\r\n'
        'echo. >> "%LOG%"\r\n'
        f'echo ===== %DATE% %TIME% -- {job.id} starting ===== >> "%LOG%"\r\n'
        f'{job.command} >> "%LOG%" 2>&1\r\n'
        "if errorlevel 1 (\r\n"
        f'    echo ***** FAILED at %DATE% %TIME% ***** >> "%LOG%"\r\n'
        ") else (\r\n"
        f'    echo ----- ok at %DATE% %TIME% ----- >> "%LOG%"\r\n'
        ")\r\n"
    )
    job.bat_path.write_text(src, encoding="utf-8")
    return job.bat_path


# ── schtasks command construction ────────────────────────────────────────────
#: The default `JobSpec.days`. NSE trades Mon-Fri, so after-close jobs have
#: nothing to do at the weekend. A job that watches 24x7 markets (the alert bot,
#: for crypto) sets its own days.
_TRADING_DAYS = "MON,TUE,WED,THU,FRI"


def _duration(start: str, end: str) -> str:
    """`/du` value (HHHH:MM) spanning `start`..`end`, both "HH:MM", same day.

    schtasks expresses a bounded repeating window as a duration, not as an end
    time — see `register_argv` for why that distinction cost this job its
    schedule.
    """
    try:
        sh, sm = (int(x) for x in start.split(":"))
        eh, em = (int(x) for x in end.split(":"))
    except (ValueError, AttributeError):
        return "0006:30"
    mins = (eh * 60 + em) - (sh * 60 + sm)
    if mins <= 0:                       # end at/before start — treat as a full day
        mins = 24 * 60 - 1
    return f"{mins // 60:04d}:{mins % 60:02d}"


def register_argv(job: JobSpec, *, time: str | None = None,
                  interval: int | None = None, end: str | None = None) -> list[str]:
    """Build (do not run) the schtasks /create argv for a job's schedule.

    ── Why an interval job is WEEKLY and not MINUTE (fixed 2026-09-15) ──
    The first version used `/sc MINUTE /mo N /st 09:15 /et 15:45`, which reads
    like "every N minutes between those times". It is not. `/sc MINUTE` creates a
    **one-time** trigger with a repetition attached, so the task fires once on the
    day it is registered and then has **no next run at all** — `schtasks /query`
    reported `Next Run Time: N/A` on the live AlertWatcher task. `/et` was
    silently dropped too (`Repeat: Until: Time: None`).

    The form that actually recurs is a WEEKLY trigger on the trading days with
    `/ri` (repeat interval, minutes) and `/du` (how long to keep repeating):
    verified to report a real next run at the following 09:15.

    **The failure mode is the dangerous kind** — registration SUCCEEDS, the task
    is Enabled, and the hub shows it as registered. Only the next-run field says
    it will never fire, which is why `status()` returns `next_run` and the hub
    must show it.
    """
    if job.id == "daily_scanner":
        bat = _scanner_bat()
    elif job.id == "batch_screener":
        bat = _batch_bat()
    else:
        bat = job.bat_path
    argv = ["schtasks", "/create", "/f", "/tn", job.task_name, "/tr", str(bat)]
    if job.kind == "interval":
        st = time or job.default_time
        et = end or job.default_end
        mo = int(interval or job.default_interval)
        argv += ["/sc", "WEEKLY", "/d", job.days, "/st", st,
                 "/ri", str(mo), "/du", _duration(st, et)]
    else:  # daily — on trading weekdays; /sc DAILY also fired every Sat/Sun
        st = time or job.default_time
        argv += ["/sc", "WEEKLY", "/d", job.days, "/st", st]
    if job.elevate:
        argv += ["/rl", "HIGHEST"]
    return argv


# ── Actions (each shells out to schtasks) ────────────────────────────────────
SCHTASKS_AVAILABLE = shutil.which("schtasks") is not None
UNAVAILABLE_MSG = ("Windows Task Scheduler (schtasks) is not available on this "
                   "machine — jobs can't be registered here.")


def _schtasks(argv: list[str]) -> subprocess.CompletedProcess:
    """Run a schtasks command; on a machine without schtasks (Linux/macOS, or a
    trimmed Windows) return a failed result instead of raising, so the hub
    page renders read-only rather than crashing at the first status() call."""
    try:
        return subprocess.run(argv, capture_output=True, text=True, shell=False)
    except (FileNotFoundError, OSError) as e:
        return subprocess.CompletedProcess(argv, 127, stdout="",
                                           stderr=f"{UNAVAILABLE_MSG} ({e})")


def task_settings_ps(task_name: str) -> str:
    """PowerShell that sets what `schtasks /create` cannot express.

    * StartWhenAvailable — a run missed while the PC slept fires on wake
      instead of being skipped until tomorrow.
    * Battery — schtasks' defaults refuse to START on battery and KILL a run
      when the laptop unplugs; the logs' `^C` lines and runs stuck "running"
      were this.

    The task object is edited in place rather than replaced with
    New-ScheduledTaskSettingsSet, which would reset every other setting.
    """
    name = task_name.replace("'", "''")
    return (f"$t = Get-ScheduledTask -TaskName '{name}'; "
            "$t.Settings.StartWhenAvailable = $true; "
            "$t.Settings.DisallowStartIfOnBatteries = $false; "
            "$t.Settings.StopIfGoingOnBatteries = $false; "
            "Set-ScheduledTask -InputObject $t | Out-Null")


def register(job: JobSpec, **kw) -> tuple[bool, str]:
    """CREATE/replace the scheduled task. Persistent OS change — user-triggered."""
    if job.managed_bat:
        write_bat(job)
    argv = register_argv(job, **kw)
    res = _schtasks(argv)
    if res.returncode != 0:
        return False, (res.stderr or res.stdout or "schtasks failed").strip()
    msg = (res.stdout or "").strip() or "Task registered."
    ps = _schtasks(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                    task_settings_ps(job.task_name)])
    if ps.returncode != 0:
        # Registered and will run; only catch-up/battery tolerance is missing.
        msg += (" (warning: catch-up/battery settings not applied: "
                f"{(ps.stderr or ps.stdout or 'powershell failed').strip()})")
    return True, msg


def remove(job: JobSpec) -> tuple[bool, str]:
    res = _schtasks(["schtasks", "/delete", "/f", "/tn", job.task_name])
    if res.returncode == 0:
        return True, "Task removed."
    return False, (res.stderr or res.stdout or "not found").strip()


def run_now(job: JobSpec) -> tuple[bool, str]:
    res = _schtasks(["schtasks", "/run", "/tn", job.task_name])
    if res.returncode == 0:
        return True, "Triggered."
    return False, (res.stderr or res.stdout or "run failed").strip()


def status(job: JobSpec) -> dict:
    """Read-only. Returns {registered, state, next_run, last_run, last_result}."""
    res = _schtasks(["schtasks", "/query", "/tn", job.task_name, "/fo", "LIST", "/v"])
    if res.returncode != 0:
        return {"registered": False}
    fields: dict[str, str] = {}
    for line in res.stdout.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fields[k.strip()] = v.strip()
    return {
        "registered": True,
        "state": fields.get("Scheduled Task State") or fields.get("Status", ""),
        "next_run": fields.get("Next Run Time", ""),
        "last_run": fields.get("Last Run Time", ""),
        "last_result": fields.get("Last Result", ""),
    }


def tail_log(job: JobSpec, n: int = 40) -> str:
    if job.id == "daily_scanner":
        p = HERE / "scanner_daily.log"
    elif job.id == "batch_screener":
        p = HERE / "scanner_batch.log"
    elif job.managed_bat:
        p = job.log_path
    else:
        p = HERE / "scanner_daily.log"
    
    if not p.exists():
        return "(no log yet)"
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-n:])
    except Exception as e:
        return f"(log read error: {e})"


# ── Run history ──────────────────────────────────────────────────────────────
_START_RE = re.compile(
    r"=====\s+\w+\s+(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2}\.\d+)\s+--\s+(\S+)\s+starting\s+=====",
)
_START_RE2 = re.compile(
    r"=====\s+\w+\s+(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2}\.\d+)\s+.+?\s+starting\s+=====",
)
_END_OK = re.compile(r"-----\s+ok(?:\s+at\s+\w+\s+(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2}\.\d+))?\s*-----")
_END_FAIL = re.compile(r"\*{5}\s+FAILED(?:\s+at\s+\w+\s+(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2}\.\d+))?\s*\*{5}")


def _parse_dt(date_s: str, time_s: str) -> datetime | None:
    try:
        return datetime.strptime(f"{date_s} {time_s.split('.')[0]}", "%m/%d/%Y %H:%M:%S")
    except (ValueError, IndexError):
        return None


@dataclass
class RunRecord:
    job: str
    started: datetime | None
    outcome: str          # "ok" | "FAILED" | "running"
    ended: datetime | None = None
    duration_s: float | None = None


def parse_run_history(job: JobSpec, *, max_runs: int = 200) -> list[RunRecord]:
    """Parse the log file into a list of run records, newest first."""
    p = job.log_path if job.managed_bat else (
        _scanner_bat().with_suffix(".log") if job.id == "daily_scanner"
        else HERE / f"{job.id}.log")
    if job.id == "daily_scanner":
        p = HERE / "scanner_daily.log"
    if not p.exists():
        return []

    text = p.read_text(encoding="utf-8", errors="replace")
    runs: list[RunRecord] = []
    current_start: datetime | None = None
    current_job: str = job.id

    for line in text.splitlines():
        m = _START_RE.match(line.strip())
        if m:
            if current_start is not None:
                runs.append(RunRecord(job=current_job, started=current_start,
                                      outcome="running"))
            current_start = _parse_dt(m.group(1), m.group(2))
            current_job = m.group(3)
            continue
        if not m:
            m2 = _START_RE2.match(line.strip())
            if m2:
                if current_start is not None:
                    runs.append(RunRecord(job=current_job, started=current_start,
                                          outcome="running"))
                current_start = _parse_dt(m2.group(1), m2.group(2))
                continue

        m_ok = _END_OK.search(line.strip())
        m_fail = _END_FAIL.search(line.strip())
        if m_ok and current_start is not None:
            ended = _parse_dt(m_ok.group(1), m_ok.group(2)) if m_ok.group(1) else None
            dur = (ended - current_start).total_seconds() if ended and current_start else None
            runs.append(RunRecord(job=current_job, started=current_start,
                                  outcome="ok", ended=ended, duration_s=dur))
            current_start = None
        elif m_fail and current_start is not None:
            ended = _parse_dt(m_fail.group(1), m_fail.group(2)) if m_fail.group(1) else None
            dur = (ended - current_start).total_seconds() if ended and current_start else None
            runs.append(RunRecord(job=current_job, started=current_start,
                                  outcome="FAILED", ended=ended, duration_s=dur))
            current_start = None

    if current_start is not None:
        runs.append(RunRecord(job=current_job, started=current_start,
                              outcome="running"))

    runs.reverse()
    return runs[:max_runs]


def run_summary(job: JobSpec) -> dict:
    """Summary stats for a job's run history."""
    runs = parse_run_history(job)
    if not runs:
        return {"total": 0, "instrumented": False}
    ok = sum(1 for r in runs if r.outcome == "ok")
    failed = sum(1 for r in runs if r.outcome == "FAILED")
    durations = [r.duration_s for r in runs if r.duration_s is not None]
    first = runs[-1].started
    last = runs[0].started
    return {
        "total": len(runs),
        "ok": ok,
        "failed": failed,
        "running": sum(1 for r in runs if r.outcome == "running"),
        "first_run": first.isoformat() if first else None,
        "last_run": last.isoformat() if last else None,
        "median_duration_s": sorted(durations)[len(durations)//2] if durations else None,
        "instrumented": True,
    }


def all_run_summaries() -> dict[str, dict]:
    return {jid: run_summary(j) for jid, j in JOBS.items()}


# ── Orphan detection ────────────────────────────────────────────────────────
def orphan_tasks() -> list[str]:
    """List TradingBramha-* scheduled tasks not in JOBS."""
    try:
        res = subprocess.run(
            ["schtasks", "/query", "/fo", "CSV", "/nh"],
            capture_output=True, text=True, shell=False, timeout=10)
    except Exception:
        return []
    known = {j.task_name for j in JOBS.values()}
    orphans = []
    for line in res.stdout.splitlines():
        parts = line.strip().strip('"').split('","')
        if parts and parts[0].startswith("\\TradingBramha-"):
            name = parts[0].lstrip("\\")
            if name not in known:
                orphans.append(name)
    return orphans


# ── CLI (read-only unless you ask otherwise) ─────────────────────────────────
def _main(argv: list[str]) -> None:
    if not argv or argv[0] == "list":
        for jid, j in JOBS.items():
            print(f"{jid:16} [{j.kind:8}] {j.label}  ->  {j.task_name}")
        return
    cmd = argv[0]
    if cmd == "orphans":
        o = orphan_tasks()
        print(f"Orphan tasks: {o}" if o else "No orphan TradingBramha-* tasks.")
        return
    if cmd == "summaries":
        for jid, s in all_run_summaries().items():
            print(f"  {jid:20} total={s['total']:3}  ok={s.get('ok',0):3}  "
                  f"failed={s.get('failed',0)}  last={s.get('last_run','?')}")
        return
    job = JOBS.get(argv[1]) if len(argv) > 1 else None
    if not job:
        print(f"unknown job; try: {', '.join(JOBS)}"); return
    if cmd == "status":
        print(status(job))
    elif cmd == "writebat":
        print("wrote", write_bat(job))
    elif cmd == "registerargv":
        print(" ".join(register_argv(job)))
    elif cmd == "register":
        print(register(job))
    elif cmd == "remove":
        print(remove(job))
    elif cmd == "run":
        print(run_now(job))
    elif cmd == "log":
        print(tail_log(job))
    elif cmd == "history":
        runs = parse_run_history(job, max_runs=30)
        if not runs:
            print(f"  (no runs recorded for {job.id})")
        for r in runs:
            dt = r.started.strftime("%Y-%m-%d %H:%M") if r.started else "?"
            dur = f" ({r.duration_s:.0f}s)" if r.duration_s else ""
            print(f"  {dt}  {r.outcome}{dur}")
        s = run_summary(job)
        print(f"\n  total={s['total']}  ok={s.get('ok',0)}  failed={s.get('failed',0)}"
              f"  median_dur={s.get('median_duration_s', '?')}s")
    else:
        print("commands: list | status | writebat | registerargv | log | "
              "history | summaries | orphans | register | remove | run <job>")


if __name__ == "__main__":
    _main(sys.argv[1:])
