#!/usr/bin/env python3
"""job_audit.py — durable run history for every scheduled batch job.

Each job's `.bat` runs its command THROUGH this module:

    python job_audit.py run <job_id> -- <command> [args...]

which times the run, passes the command's output straight through to the
job's log, and records one row in the `job_runs` table: start, end, duration,
exit code, outcome, a one-line result, and the log tail when the run failed.
The child's exit code is returned unchanged, so the .bat's ok/FAILED line and
the task's Last Result mean what they meant before.

── Why a table and not the logs ─────────────────────────────────────────────
The logs only say "ok" or "FAILED". On 2026-10-29 the alert bot logged "ok"
every 15 minutes while checking nothing, because its data server was down. A
run's RESULT ("checked 0 · errors 6") is what an audit needs, and the logs
also grow without limit and get truncated by hand.

── The result line ──────────────────────────────────────────────────────────
A job reports what it did by printing one line:

    ##RESULT 57 scanners · 1155 hits

The last such line wins. A job that prints none gets its last non-empty output
line as the result, which is usually its own summary.

Recording must never break a job: if the database write fails, the run still
returns the child's exit code and the failure goes to stderr (the job's log).

CLI:
    py -3 tools/job_audit.py run filings_watch -- python tools/filings_watch.py
    py -3 tools/job_audit.py backfill        # import past runs from the logs, once
    py -3 tools/job_audit.py recent [job_id]
"""
from __future__ import annotations

import io
import json
import socket
import subprocess
import sys
from collections import deque
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

RESULT_TAG = "##RESULT "
TAIL_LINES = 40
RESULT_MAX = 300

_SCHEMA = """
CREATE TABLE IF NOT EXISTS job_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT NOT NULL,
    started_at  TEXT NOT NULL,          -- local ISO time, second precision
    ended_at    TEXT,
    duration_s  REAL,
    exit_code   INTEGER,
    outcome     TEXT NOT NULL,          -- ok | FAILED | running | no-end (backfill)
    result      TEXT,                   -- the job's one-line account of the run
    log_tail    TEXT,                   -- kept only for failed runs
    source      TEXT NOT NULL,          -- wrapper | backfill
    host        TEXT,
    UNIQUE (job_id, started_at)
);
CREATE INDEX IF NOT EXISTS ix_job_runs_started ON job_runs (started_at);
"""


def _conn():
    import portfolio_db as db
    conn = db.get_connection()
    conn.executescript(_SCHEMA)
    return conn


def _now() -> datetime:
    return datetime.now().replace(microsecond=0)


@dataclass
class Run:
    job_id: str
    started_at: datetime
    ended_at: datetime | None
    exit_code: int | None
    outcome: str
    result: str | None = None
    log_tail: str | None = None
    source: str = "wrapper"

    @property
    def duration_s(self) -> float | None:
        if self.ended_at is None:
            return None
        return (self.ended_at - self.started_at).total_seconds()


def outcome_of(exit_code: int | None) -> str:
    if exit_code is None:
        return "running"
    return "ok" if exit_code == 0 else "FAILED"


def pick_result(lines: Iterable[str]) -> str | None:
    """The run's one-line result: the last ##RESULT line, else the last
    non-empty line. None when the job printed nothing."""
    tagged, last = None, None
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if s.startswith(RESULT_TAG.strip()):
            tagged = s[len(RESULT_TAG.strip()):].strip()
        last = s
    out = tagged if tagged is not None else last
    return out[:RESULT_MAX] if out else None


def record(run: Run, conn=None) -> None:
    own = conn is None
    conn = conn or _conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO job_runs (job_id, started_at, ended_at, duration_s, "
            "exit_code, outcome, result, log_tail, source, host) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (run.job_id, run.started_at.isoformat(),
             run.ended_at.isoformat() if run.ended_at else None,
             run.duration_s, run.exit_code, run.outcome, run.result,
             run.log_tail, run.source, socket.gethostname()))
        conn.commit()
    finally:
        if own:
            conn.close()


# ── the wrapper ──────────────────────────────────────────────────────────────
def run_wrapped(job_id: str, cmd: list[str], *, out=None) -> int:
    """Run `cmd`, tee its output to `out`, record the run, return its exit code."""
    out = out or sys.stdout
    started = _now()
    tail: deque[str] = deque(maxlen=TAIL_LINES)
    results: list[str] = []
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            out.write(line + "\n")
            out.flush()
            tail.append(line)
            if line.strip().startswith(RESULT_TAG.strip()):
                results.append(line)
        code = proc.wait()
    except OSError as exc:
        # The command could not even start (bad interpreter path): that is a
        # failed run, and the most important kind to have on record.
        msg = f"could not start: {exc}"
        out.write(msg + "\n")
        tail.append(msg)
        code = 127
    run = Run(job_id=job_id, started_at=started, ended_at=_now(), exit_code=code,
              outcome=outcome_of(code),
              result=pick_result(results or list(tail)),
              log_tail="\n".join(tail) if code != 0 else None)
    try:
        record(run)
    except Exception as exc:                 # never fail the job over the audit
        sys.stderr.write(f"[job_audit] could not record run: {exc}\n")
    return code


# ── backfill from the logs ───────────────────────────────────────────────────
def backfill(conn=None) -> dict[str, int]:
    """Import the runs the job logs hold from BEFORE the wrapper recorded them.

    Idempotent: (job_id, started_at) is unique. Runs from the job's first
    wrapper-recorded run on are skipped, because the .bat's start stamp and
    the wrapper's can differ by a second and would both be kept.
    """
    import scheduler_core as sched
    own = conn is None
    conn = conn or _conn()
    counts: dict[str, int] = {}
    try:
        for jid, job in sched.JOBS.items():
            before = conn.total_changes
            first = conn.execute(
                "SELECT MIN(started_at) FROM job_runs WHERE job_id = ? AND source = 'wrapper'",
                (jid,)).fetchone()[0]
            cutoff = datetime.fromisoformat(first) - timedelta(seconds=5) if first else None
            stale = _now() - timedelta(hours=6)
            for r in sched.parse_run_history(job, max_runs=100_000):
                if r.started is None or (cutoff and r.started >= cutoff):
                    continue
                code = {"ok": 0, "FAILED": 1}.get(r.outcome)
                # A logged start with no end line, hours ago, is a run that was
                # killed or lost its log tail. It is not "running".
                outcome = ("no-end" if r.outcome == "running" and r.started < stale
                           else r.outcome)
                record(Run(job_id=jid, started_at=r.started, ended_at=r.ended,
                           exit_code=code, outcome=outcome, source="backfill"),
                       conn=conn)
            counts[jid] = conn.total_changes - before
    finally:
        if own:
            conn.close()
    return counts


# ── reads for the History tab ────────────────────────────────────────────────
def runs(job_id: str | None = None, *, days: int = 30, conn=None) -> list[dict]:
    """Runs started in the last `days` days, newest first."""
    own = conn is None
    conn = conn or _conn()
    try:
        since = (_now() - timedelta(days=days)).isoformat()
        q = "SELECT * FROM job_runs WHERE started_at >= ?"
        args: list = [since]
        if job_id:
            q += " AND job_id = ?"
            args.append(job_id)
        q += " ORDER BY started_at DESC"
        return [dict(r) for r in conn.execute(q, args).fetchall()]
    finally:
        if own:
            conn.close()


def day_status(rows: Iterable[dict]) -> dict[tuple[str, str], str]:
    """(job_id, YYYY-MM-DD) → ok | FAILED | mixed | running | no-end, from run rows.

    `mixed` means some runs that day failed and some passed: the usual shape
    of an interval job (alert bot, filings watch) having a bad hour.
    """
    seen: dict[tuple[str, str], set[str]] = {}
    for r in rows:
        key = (r["job_id"], str(r["started_at"])[:10])
        seen.setdefault(key, set()).add(r["outcome"])
    out = {}
    for key, outs in seen.items():
        if outs == {"ok"}:
            out[key] = "ok"
        elif "ok" in outs and "FAILED" in outs:
            out[key] = "mixed"
        elif "FAILED" in outs:
            out[key] = "FAILED"
        elif "running" in outs:
            out[key] = "running"
        elif "ok" in outs:                  # ok plus a run with no end line
            out[key] = "ok"
        else:
            out[key] = "no-end"
    return out


def today_board(rows: list[dict], job_ids: Iterable[str],
                today: date | None = None) -> list[dict]:
    """One line per job: today's run counts and its most recent run."""
    today_s = (today or date.today()).isoformat()
    board = []
    for jid in job_ids:
        mine = [r for r in rows if r["job_id"] == jid]      # newest first
        todays = [r for r in mine if str(r["started_at"])[:10] == today_s]
        last = mine[0] if mine else None
        board.append({
            "job_id": jid,
            "runs_today": len(todays),
            "failed_today": sum(r["outcome"] == "FAILED" for r in todays),
            "last_started": last["started_at"] if last else None,
            "last_outcome": last["outcome"] if last else None,
            "last_result": last["result"] if last else None,
        })
    return board


def main(argv: list[str]) -> int:
    if len(argv) >= 4 and argv[1] == "run" and "--" in argv:
        i = argv.index("--")
        return run_wrapped(argv[2], argv[i + 1:])
    if len(argv) >= 2 and argv[1] == "backfill":
        for jid, n in backfill().items():
            print(f"{jid:<24} {n} run(s) imported")
        return 0
    if len(argv) >= 2 and argv[1] == "recent":
        for r in runs(argv[2] if len(argv) > 2 else None, days=2)[:30]:
            print(f"{r['started_at']}  {r['job_id']:<22} {r['outcome']:<7} {r['result'] or ''}")
        return 0
    print(__doc__)
    return 64


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  line_buffering=True)
    sys.exit(main(sys.argv))
