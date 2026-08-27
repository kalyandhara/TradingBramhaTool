"""ui_jobs.py — a per-Streamlit-session SERIAL job queue.

The problem
-----------
Streamlit runs ONE script thread per session and reruns (interrupts) it on ANY
widget interaction. So a long task run inline — `od.run(...)`, `compute_sentiment()`
— is CANCELLED the instant the user clicks another button. The user's ask: a click
during a long run should be QUEUED and run AFTER the in-progress job, never cancel it.

The fix
-------
Move long tasks OFF the script thread into a single-worker executor (max_workers=1
= a serial queue). Submitting is instant, so the rerun completes and the UI stays
live; a second submit while one runs simply waits its turn. The script thread only
submits and polls job status.

ScriptRunContext
----------------
Background threads have no Streamlit ScriptRunContext, so `st.cache_data` functions
and `st.session_state` reads fail off-thread (the dashboard already notes this).
We attach the submitting thread's context to the worker via `add_script_run_ctx`,
so cached fetchers and session lookups work from inside a job.

Scope / caveats
---------------
- **Per session, serial.** One worker; jobs run in submit order. This is the
  point — it serialises, it does not parallelise.
- **Jobs must not build UI.** A job returns a value or sets progress text; the
  main thread renders. Don't call `st.write`/element APIs from a job.
- Not cross-tab / cross-session: a queue lives in one session's state.
- The core queue is import-safe without Streamlit (for tests); the `get_queue`
  / `render_status` helpers need `st`.
"""

from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

try:                                    # optional — core queue works without it
    from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
except Exception:                       # pragma: no cover
    add_script_run_ctx = get_script_run_ctx = None


@dataclass
class Job:
    id: str
    label: str
    status: str = "queued"              # queued | running | done | error
    progress: str = ""
    result: Any = None
    error: Optional[str] = None
    submitted: float = field(default_factory=time.time)
    started: Optional[float] = None
    finished: Optional[float] = None

    @property
    def active(self) -> bool:
        return self.status in ("queued", "running")


class JobQueue:
    """One serial worker. `submit` returns immediately; jobs run in order and a
    submit while one runs waits its turn (it never cancels the running job)."""

    def __init__(self, ctx=None):
        self._ex = ThreadPoolExecutor(max_workers=1, thread_name_prefix="uijob")
        self.jobs: list[Job] = []
        self._ctx = ctx

    def submit(self, label: str, fn: Callable, *args,
               progress_kw: Optional[str] = None, **kwargs) -> str:
        """Queue `fn(*args, **kwargs)`. If `progress_kw` is given, a setter that
        updates the job's `progress` text is injected under that keyword (so a
        long fn can report progress the main thread displays)."""
        job = Job(id=uuid.uuid4().hex[:8], label=label)
        self.jobs.append(job)
        ctx = self._ctx
        if progress_kw:
            kwargs[progress_kw] = lambda msg: setattr(job, "progress", str(msg))

        def _run():
            if add_script_run_ctx and ctx is not None:
                try:
                    add_script_run_ctx(ctx=ctx)     # cached fns / session ctx in-thread
                except Exception:
                    pass
            job.status, job.started = "running", time.time()
            try:
                job.result = fn(*args, **kwargs)
                job.status = "done"
            except Exception as e:                  # noqa: BLE001 — surfaced in job.error
                job.status, job.error = "error", f"{type(e).__name__}: {e}"
            finally:
                job.finished = time.time()

        self._ex.submit(_run)
        return job.id

    # ── queries ───────────────────────────────────────────────────────────────
    def active(self) -> list[Job]:
        return [j for j in self.jobs if j.active]

    def has_active(self) -> bool:
        return any(j.active for j in self.jobs)

    def is_active(self, label: str) -> bool:
        return any(j.label == label and j.active for j in self.jobs)

    def latest(self, label: str) -> Optional[Job]:
        for j in reversed(self.jobs):
            if j.label == label:
                return j
        return None

    def take_result(self, label: str):
        """Return (and clear) the most recent COMPLETED result for `label`, so the
        UI consumes a finished job's output exactly once. None if none ready."""
        j = None
        for cand in reversed(self.jobs):
            if cand.label == label and cand.status in ("done", "error"):
                j = cand
                break
        if j is None:
            return None
        self.jobs.remove(j)
        return j


# ──────────────────────────────────────────────────────────────────────────────
# Streamlit glue (needs `st`)
# ──────────────────────────────────────────────────────────────────────────────
def get_queue():
    """The current session's queue, created on first use with this thread's ctx."""
    import streamlit as st
    q = st.session_state.get("_ui_job_queue")
    if q is None:
        ctx = get_script_run_ctx() if get_script_run_ctx else None
        q = JobQueue(ctx=ctx)
        st.session_state["_ui_job_queue"] = q
    return q


def submit_unique(label: str, fn: Callable, *args, progress_kw: Optional[str] = None,
                  **kwargs) -> Optional[str]:
    """Submit unless a job with the same `label` is already queued/running — so a
    double-click (or a rerun) doesn't enqueue the same work twice. Returns the job
    id, or None if one was already active."""
    q = get_queue()
    if q.is_active(label):
        return None
    return q.submit(label, fn, *args, progress_kw=progress_kw, **kwargs)


def render_panel() -> None:
    """Draw a compact panel of running/queued jobs. Call once near the TOP (under
    the nav). Does NOT rerun — so the full page still renders and stays clickable
    while a job runs. Pair with `autorefresh()` at the bottom of the script."""
    import streamlit as st
    q = get_queue()
    if not q.has_active():
        return
    lines = []
    for j in q.jobs:
        if j.status == "running":
            extra = f" — {j.progress}" if j.progress else ""
            lines.append(f"⏳ **{j.label}** running{extra}")
        elif j.status == "queued":
            lines.append(f"🕒 **{j.label}** queued — runs after the current job")
    st.info("Background work in progress — the page stays live; a new action "
            "**queues** behind the running job rather than cancelling it.\n\n"
            + "\n\n".join(lines))


def autorefresh(poll_secs: float = 1.5) -> None:
    """If any job is active, sleep briefly then rerun — a poll loop. Call once at
    the very BOTTOM of the script so the full page renders each cycle (the user
    keeps interacting; the panel + any completed results just refresh)."""
    import streamlit as st
    if get_queue().has_active():
        time.sleep(poll_secs)
        st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# Standalone self-test (no Streamlit): proves serial execution + queueing.
#   py -3 tools/ui_jobs.py
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    order = []

    def work(name, secs):
        order.append(f"{name}:start")
        time.sleep(secs)
        order.append(f"{name}:end")
        return name.upper()

    q = JobQueue()
    q.submit("A (long)", work, "a", 0.5)
    time.sleep(0.1)                      # while A runs…
    q.submit("B (queued)", work, "b", 0.2)   # …B should WAIT, not cancel A
    assert q.is_active("A (long)") or q.is_active("B (queued)")
    while q.has_active():
        time.sleep(0.05)
    # Serial guarantee: A fully finished before B started.
    assert order == ["a:start", "a:end", "b:start", "b:end"], order
    ja, jb = q.latest("A (long)"), q.latest("B (queued)")
    assert ja.status == "done" and ja.result == "A"
    assert jb.status == "done" and jb.result == "B"
    print("ui_jobs self-test PASS — serial order:", order)
