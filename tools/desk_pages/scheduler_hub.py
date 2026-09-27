"""Scheduler Hub page — extracted from dashboard_app.py (B-87r).

Batch jobs registered as Windows Scheduled Tasks. Register / Remove / Run now
change persistent OS scheduled tasks. The Alert Bot runs the live SVP / indicator
signal engine each interval during market hours.
"""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

import portfolio_db as db
import report_style as rs
import scheduler_core as sched
import snapshot_registry as snapreg
import snapshot_store as snapstore
import ui_jobs


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

    if not sched.SCHTASKS_AVAILABLE:
        st.warning(
            f"{sched.UNAVAILABLE_MSG} The page is read-only here; "
            "the in-app **↻ Refresh all now** below still works.", icon="⚠️")

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
            if _b[0].button("Register / Update", key=f"sch_{_jid}_reg", type="primary",
                            disabled=not sched.SCHTASKS_AVAILABLE):
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

    # ── Report snapshots — what the Snapshot Refresh job writes ───────────────
    st.divider()
    st.markdown("### Report snapshots")
    st.caption(
        "Every on-demand report the pages load on open, with its last stored run. "
        "The **Report Snapshot Refresh** task above rewrites them after the close; "
        "each page's ↻ recomputes one on demand; the app also fills in any that "
        "are older than the last close when it starts (toggle below)."
    )
    _sf_c1, _sf_c2 = st.columns([1, 3])
    with _sf_c1:
        _snap_all_label = "Refresh · all report snapshots"
        _snap_all_done = ui_jobs.get_queue().take_result(_snap_all_label)
        if _snap_all_done is not None:
            if _snap_all_done.status == "error":
                st.error(f"Snapshot run failed: {_snap_all_done.error}")
            else:
                _bad = [m for m in (_snap_all_done.result or []) if not m.ok]
                st.success(f"All snapshots refreshed — {len(_bad)} failed."
                           if _bad else "All snapshots refreshed.")
        if st.button("↻ Refresh all now (in-app)", key="snap_run_all",
                     width="stretch",
                     disabled=ui_jobs.get_queue().is_active(_snap_all_label),
                     help="Runs every snapshot in this session's background queue — "
                          "the same work the scheduled task does, without schtasks."):
            ui_jobs.submit_unique(_snap_all_label, snapreg.run_all,
                                  progress_kw="progress")
            st.rerun()
    with _sf_c2:
        _fill_on = (db.get_setting("snapshot_startup_fill", "1") or "1") == "1"
        _fill_new = st.checkbox(
            "Fill stale snapshots in the background when the app starts",
            value=_fill_on, key="snap_startup_fill")
        if _fill_new != _fill_on:
            db.set_setting("snapshot_startup_fill", "1" if _fill_new else "0")

    _ov = {m.name: m for m in snapstore.overview()}
    _snap_rows = []
    for _spec in snapreg.ordered():
        _m = _ov.get(_spec.name)
        _snap_rows.append({
            "Snapshot": _spec.label, "Page": _spec.page,
            "Last run": _m.run_at.replace("T", " ") if _m else "never",
            "Status": ("—" if _m is None else
                       "⚠ stale" if snapstore.is_stale(_m if _m.ok else None) and _m.ok else
                       "✅ ok" if _m.ok else "❌ error"),
            "Secs": round(_m.elapsed) if _m else None,
            "KB": round(_m.nbytes / 1024) if _m and _m.nbytes else None,
            "Error": (_m.error or "") if _m else "",
        })
    st.dataframe(pd.DataFrame(_snap_rows), hide_index=True, width="stretch")
