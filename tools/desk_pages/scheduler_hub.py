"""Scheduler Hub page — extracted from dashboard_app.py (B-87r).

Batch jobs registered as Windows Scheduled Tasks. Register / Remove / Run now
change persistent OS scheduled tasks. The Alert Bot runs the live SVP / indicator
signal engine each interval during market hours.
"""
from __future__ import annotations

import json

import streamlit as st

import report_style as rs
import scheduler_core as sched


def render() -> None:
    st.subheader("Scheduler Hub")
    st.caption(
        "Batch jobs registered as Windows Scheduled Tasks. **Register / Remove / "
        "Run now change persistent OS scheduled tasks.** The Alert Bot runs the live "
        "SVP / indicator signal engine each interval during market hours and fires on "
        "pattern-buildup transitions."
    )
    st.info(
        "Jobs read live bars from the chart server (http://127.0.0.1:5001) and the "
        "dashboard cache — keep the chart server running during market hours so the "
        "Alert Bot has data.", icon="ℹ️",
    )

    for _jid, _job in sched.JOBS.items():
        _stt = sched.status(_job)
        _reg = _stt.get("registered")
        with st.container(border=True):
            _hdr = st.columns([3, 1])
            _hdr[0].markdown(f"### {_job.label}")
            _hdr[0].caption(_job.desc)
            _hdr[1].markdown(f"**{'🟢 registered' if _reg else '⚪ not registered'}**")
            _hdr[1].caption(f"`{_job.task_name}`")

            if _reg:
                _m = st.columns(4)
                _m[0].metric("State", _stt.get("state", "—"))
                _m[1].metric("Next run", _stt.get("next_run", "—"))
                _m[2].metric("Last run", _stt.get("last_run", "—"))
                _m[3].metric("Last result", _stt.get("last_result", "—"))
                if str(_stt.get("next_run", "")).strip().upper() in ("N/A", "", "—"):
                    st.markdown(
                        rs.callout(
                            "Registered, but it has no next run.",
                            "Windows accepted the task and reports it Enabled, yet "
                            "there is no scheduled next fire — so it will not run. "
                            "Re-register it below; if it comes back N/A the schedule "
                            "shape is wrong, not the times.",
                            tone="risk"),
                        unsafe_allow_html=True)

            if _job.kind == "interval":
                _c = st.columns(3)
                _v_st = _c[0].text_input("Start (HH:MM)", value=_job.default_time, key=f"sch_{_jid}_st")
                _v_et = _c[1].text_input("End (HH:MM)", value=_job.default_end, key=f"sch_{_jid}_et")
                _v_mo = _c[2].number_input("Every N min", 1, 240, int(_job.default_interval), key=f"sch_{_jid}_mo")
                _sched_kw = dict(time=_v_st, end=_v_et, interval=int(_v_mo))
            else:
                _c = st.columns(3)
                _v_t = _c[0].text_input("Run time (HH:MM)", value=_job.default_time, key=f"sch_{_jid}_t")
                _sched_kw = dict(time=_v_t)

            _b = st.columns(4)
            if _b[0].button("Register / Update", key=f"sch_{_jid}_reg", type="primary"):
                _ok, _msg = sched.register(_job, **_sched_kw)
                if _ok:
                    st.success(_msg); st.rerun()
                else:
                    st.error(_msg)
                    st.code(" ".join(sched.register_argv(_job, **_sched_kw)), language="bat")
                    st.caption("If it's a permissions error, run the command above in an elevated terminal.")
            if _b[1].button("Run now", key=f"sch_{_jid}_run", disabled=not _reg):
                _ok, _msg = sched.run_now(_job)
                (st.success if _ok else st.error)(_msg)
            if _b[2].button("Remove", key=f"sch_{_jid}_del", disabled=not _reg):
                _ok, _msg = sched.remove(_job)
                (st.success if _ok else st.warning)(_msg); st.rerun()

            with st.expander("Log tail", expanded=False):
                st.code(sched.tail_log(_job, 40), language=None)

            if _jid == "alert_watcher":
                _cfg_path = sched.HERE / "alert_config.json"
                try:
                    _cfg = json.loads(_cfg_path.read_text(encoding="utf-8"))
                except Exception:
                    _cfg = {}
                _delivery = _cfg.get("delivery", [])
                if not _delivery or _delivery == ["log"]:
                    st.warning(
                        "Delivery is **dry-run** (log only) — no email/Telegram channel wired "
                        "yet. Fired alerts go to `tools/cache/alerts/alerts.jsonl`.", icon="⚠️",
                    )
                _watch = _cfg.get("watch", [])
                if _watch:
                    st.caption("Watchlist: " + " · ".join(f"{w.get('symbol')}·{w.get('tf')}" for w in _watch)
                               + "   |   Rules: " + ", ".join(r.get("id", "?") for r in _cfg.get("rules", [])))
                _feed = sched.HERE / "cache" / "alerts" / "alerts.jsonl"
                if _feed.exists():
                    _rows = [r for r in _feed.read_text(encoding="utf-8").splitlines() if r.strip()][-10:]
                    if _rows:
                        with st.expander(f"Recent alerts ({len(_rows)})", expanded=False):
                            for _r in reversed(_rows):
                                try:
                                    _a = json.loads(_r)
                                    st.markdown(f"- `{_a.get('ts','')}` — **{_a.get('headline','')}**")
                                except Exception:
                                    pass
