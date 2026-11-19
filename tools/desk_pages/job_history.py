"""Scheduler Hub → History tab: every batch run, today and on record.

Reads the `job_runs` table that job_audit.py writes for each scheduled run
(and backfilled from the job logs). The shaping lives in pure functions
(`board_frame`, `grid_frame`, `history_frame`) so it is testable without
Streamlit; `render()` only lays them out.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

import job_audit as ja
import scheduler_core as sched

_MARK = {"ok": "✅", "FAILED": "❌", "mixed": "🟠", "running": "⏳", "no-end": "❔"}


def _label(jid: str) -> str:
    job = sched.JOBS.get(jid)
    return job.label if job else f"{jid} (not in registry)"


def _job_ids(rows: list[dict]) -> list[str]:
    """Registry order first, then any job that ran but has since left it."""
    ids = list(sched.JOBS)
    return ids + sorted({r["job_id"] for r in rows} - set(ids))


def _dur(s) -> str:
    if s is None or pd.isna(s):
        return "—"
    s = int(s)
    return f"{s // 60}m {s % 60:02d}s" if s >= 60 else f"{s}s"


def board_frame(rows: list[dict], today: date | None = None) -> pd.DataFrame:
    board = ja.today_board(rows, _job_ids(rows), today=today)
    return pd.DataFrame([{
        "Job": _label(b["job_id"]),
        "Runs today": b["runs_today"],
        "Failed today": b["failed_today"],
        "Last run": (b["last_started"] or "never").replace("T", " "),
        "Last": _MARK.get(b["last_outcome"], "—"),
        "Last result": b["last_result"] or "",
    } for b in board])


def grid_frame(rows: list[dict], days: int, today: date | None = None) -> pd.DataFrame:
    """Jobs × days, newest day first: ✅ all ok · ❌ all failed · 🟠 some failed."""
    today = today or date.today()
    status = ja.day_status(rows)
    dates = [(today - timedelta(days=i)).isoformat() for i in range(days)]
    return pd.DataFrame(
        [[_MARK.get(status.get((jid, d)), "·") for d in dates] for jid in _job_ids(rows)],
        index=[_label(j) for j in _job_ids(rows)],
        columns=[d[5:] for d in dates])


def history_frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([{
        "Started": str(r["started_at"]).replace("T", " "),
        "Job": _label(r["job_id"]),
        "Outcome": f"{_MARK.get(r['outcome'], '')} {r['outcome']}",
        "Duration": _dur(r["duration_s"]),
        "Exit": "—" if r["exit_code"] is None else str(int(r["exit_code"])),
        "Result": r["result"] or "",
        "Source": r["source"],
    } for r in rows])


def render() -> None:
    import streamlit as st

    st.caption(
        "Every scheduled run, recorded by `job_audit.py` as it happens: start, "
        "duration, exit code, outcome and the job's own one-line result. Runs from "
        "before 2026-10-29 were imported from the job logs and carry no result. "
        "A run that exits non-zero is **FAILED**. For the alert bot that includes "
        "a BLIND pass (its data server was down), which the result says.")

    days = st.select_slider("Window", options=[7, 14, 30, 90, 365], value=30,
                            format_func=lambda d: f"{d} days", key="jh_days")
    try:
        rows = ja.runs(days=days)
    except Exception as exc:
        st.error(f"Could not read the run history: {exc}")
        return
    if not rows:
        st.info("No runs on record yet. Run `py -3 tools/job_audit.py backfill` once "
                "to import past runs from the job logs.")
        return

    since = (pd.Timestamp.now() - pd.Timedelta(hours=24)).isoformat()
    last24 = [r for r in rows if str(r["started_at"]) >= since]
    m = st.columns(4)
    m[0].metric("Runs, last 24h", len(last24))
    m[1].metric("Failed, last 24h", sum(r["outcome"] == "FAILED" for r in last24))
    m[2].metric(f"Runs, {days} days", len(rows))
    m[3].metric(f"Failed, {days} days", sum(r["outcome"] == "FAILED" for r in rows))

    st.markdown("#### Today")
    st.dataframe(board_frame(rows), hide_index=True, width="stretch")

    st.markdown(f"#### Last {min(days, 30)} days")
    st.caption("✅ every run ok · ❌ every run failed · 🟠 some runs failed · "
               "⏳ running · ❔ started but never logged an end (killed or interrupted) · "
               "· no run. Interval jobs (alert bot, filings watch) run many times a day.")
    st.dataframe(grid_frame(rows, min(days, 30)), width="stretch")

    st.markdown("#### Run history")
    c = st.columns([2, 2, 1])
    jobs = ["All jobs"] + _job_ids(rows)
    pick = c[0].selectbox("Job", jobs, key="jh_job",
                          format_func=lambda j: j if j == "All jobs" else _label(j))
    _all = ["ok", "FAILED", "running", "no-end"]
    outs = c[1].multiselect("Outcome", _all, default=_all, key="jh_out")
    shown = [r for r in rows
             if (pick == "All jobs" or r["job_id"] == pick) and r["outcome"] in outs]
    frame = history_frame(shown)
    c[2].download_button("CSV", frame.to_csv(index=False).encode("utf-8"),
                         file_name=f"job_runs_{date.today()}.csv", mime="text/csv",
                         key="jh_csv", width="stretch", disabled=frame.empty)
    st.dataframe(frame, hide_index=True, width="stretch", height=420)

    failed = [r for r in shown if r["outcome"] == "FAILED" and r.get("log_tail")][:10]
    if failed:
        st.markdown("#### Recent failures")
        for r in failed:
            with st.expander(f"❌ {str(r['started_at']).replace('T', ' ')} · "
                             f"{_label(r['job_id'])} · {r['result'] or 'no result'}"):
                st.code(r["log_tail"], language=None)
