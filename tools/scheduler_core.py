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

Registering/removing a task changes persistent OS configuration — those calls are
made only when the user acts (the hub buttons), never as a side effect of import.

CLI (read-only unless you pass register/remove/run):
  py -3 tools/scheduler_core.py list
  py -3 tools/scheduler_core.py status alert_watcher
  py -3 tools/scheduler_core.py writebat alert_watcher
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass, field
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
        desc="Runs the alert engine each interval during market hours, evaluating "
             "the live SVP/indicator signals for the watchlist and firing on "
             "pattern-buildup transitions. Delivery per alert_config.json.",
        task_name="TradingBramha-AlertWatcher",
        kind="interval",
        command=f'"{_node_exe()}" "{HERE / "alert_watcher.js"}" --once',
        default_time="09:15", default_end="15:45", default_interval=15,
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
}


def _scanner_bat() -> Path:
    return HERE / "scanner_daily.bat"


# ── .bat generation ──────────────────────────────────────────────────────────
def write_bat(job: JobSpec) -> Path:
    """Write the .bat wrapper for a managed job. Returns the bat path."""
    if not job.managed_bat:
        return _scanner_bat() if job.id == "daily_scanner" else job.bat_path
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = job.log_path
    src = (
        "@echo off\r\n"
        f'set REPO={REPO}\r\n'
        f'set LOG={log}\r\n'
        'cd /d "%REPO%"\r\n'
        'echo. >> "%LOG%"\r\n'
        f'echo ===== %DATE% %TIME% -- {job.id} starting ===== >> "%LOG%"\r\n'
        f'{job.command} >> "%LOG%" 2>&1\r\n'
        "if errorlevel 1 (\r\n"
        '    echo ***** FAILED ***** >> "%LOG%"\r\n'
        ") else (\r\n"
        '    echo ----- ok ----- >> "%LOG%"\r\n'
        ")\r\n"
    )
    job.bat_path.write_text(src, encoding="utf-8")
    return job.bat_path


# ── schtasks command construction ────────────────────────────────────────────
#: Weekdays an interval job runs on. NSE trades Mon-Fri, so a market-hours bot
#: has nothing to do at the weekend and the schedule should say so rather than
#: firing 26 no-op runs every Saturday and Sunday.
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
    bat = _scanner_bat() if job.id == "daily_scanner" else job.bat_path
    argv = ["schtasks", "/create", "/f", "/tn", job.task_name, "/tr", str(bat)]
    if job.kind == "interval":
        st = time or job.default_time
        et = end or job.default_end
        mo = int(interval or job.default_interval)
        argv += ["/sc", "WEEKLY", "/d", _TRADING_DAYS, "/st", st,
                 "/ri", str(mo), "/du", _duration(st, et)]
    else:  # daily
        st = time or job.default_time
        argv += ["/sc", "DAILY", "/st", st]
    if job.elevate:
        argv += ["/rl", "HIGHEST"]
    return argv


# ── Actions (each shells out to schtasks) ────────────────────────────────────
def register(job: JobSpec, **kw) -> tuple[bool, str]:
    """CREATE/replace the scheduled task. Persistent OS change — user-triggered."""
    if job.managed_bat:
        write_bat(job)
    argv = register_argv(job, **kw)
    res = subprocess.run(argv, capture_output=True, text=True, shell=False)
    if res.returncode == 0:
        return True, (res.stdout or "").strip() or "Task registered."
    return False, (res.stderr or res.stdout or "schtasks failed").strip()


def remove(job: JobSpec) -> tuple[bool, str]:
    res = subprocess.run(["schtasks", "/delete", "/f", "/tn", job.task_name],
                         capture_output=True, text=True, shell=False)
    if res.returncode == 0:
        return True, "Task removed."
    return False, (res.stderr or res.stdout or "not found").strip()


def run_now(job: JobSpec) -> tuple[bool, str]:
    res = subprocess.run(["schtasks", "/run", "/tn", job.task_name],
                         capture_output=True, text=True, shell=False)
    if res.returncode == 0:
        return True, "Triggered."
    return False, (res.stderr or res.stdout or "run failed").strip()


def status(job: JobSpec) -> dict:
    """Read-only. Returns {registered, state, next_run, last_run, last_result}."""
    res = subprocess.run(
        ["schtasks", "/query", "/tn", job.task_name, "/fo", "LIST", "/v"],
        capture_output=True, text=True, shell=False,
    )
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
    p = job.log_path if job.managed_bat else HERE / "scanner_daily.log"
    if not p.exists():
        return "(no log yet)"
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-n:])
    except Exception as e:
        return f"(log read error: {e})"


# ── CLI (read-only unless you ask otherwise) ─────────────────────────────────
def _main(argv: list[str]) -> None:
    if not argv or argv[0] == "list":
        for jid, j in JOBS.items():
            print(f"{jid:16} [{j.kind:8}] {j.label}  ->  {j.task_name}")
        return
    cmd = argv[0]
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
    else:
        print("commands: list | status | writebat | registerargv | log | "
              "register | remove | run <job>")


if __name__ == "__main__":
    _main(sys.argv[1:])
