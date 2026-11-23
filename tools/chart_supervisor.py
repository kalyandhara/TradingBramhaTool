#!/usr/bin/env python3
"""chart_supervisor.py -- start the chart server if nothing is listening (SBC_Tool-j0x).

alert_watcher.js reads candles from chart_server.py on :5001. That server only
ever started with the desk (dashboard_app's autostart), so on days nobody opened
the desk the alert bot ran BLIND: 813 of 1,965 runs from 2026-10-23 to
2026-11-23 checked nothing. The alert job now runs through this module:

    python chart_supervisor.py ensure -- node alert_watcher.js --once

`ensure` probes 127.0.0.1:<port>; if it is closed it launches chart_server.py
DETACHED (it outlives this run, like the desk's autostart) with output appended
to logs/chart_server.log, waits up to WAIT_S for the port, prints one status
line, then runs the command after `--` and returns ITS exit code -- so the
alert watcher's own BLIND exit (2) still reaches job_audit if the server could
not be brought up.

The server binds loopback by default (chart_server.py); the phone PWA needs a
server started with --lan, which this module never does.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "chart_server.py"
LOG = HERE / "logs" / "chart_server.log"
PORT = 5001
WAIT_S = 10.0


def is_up(port: int = PORT, timeout: float = 0.4) -> bool:
    try:
        socket.create_connection(("127.0.0.1", port), timeout=timeout).close()
        return True
    except OSError:
        return False


_builtin_open = open      # indirection so a test can simulate a locked log


def _open_log():
    """LOG for appending; if another process holds it without write-sharing
    (a server started with `cmd ... >> chart_server.log` does), fall back to
    chart_server.supervisor.log, then to no log -- the launch never depends on
    the log. The child owns the returned handle."""
    LOG.parent.mkdir(parents=True, exist_ok=True)
    for path in (LOG, LOG.with_name("chart_server.supervisor.log")):
        try:
            return _builtin_open(path, "ab")     # noqa: SIM115 -- child owns it
        except OSError:
            continue
    return subprocess.DEVNULL


def _spawn(argv: list[str]) -> subprocess.Popen:
    """Launch detached, output appended to the log from _open_log()."""
    log_fh = _open_log()
    kw: dict = {"stdout": log_fh, "stderr": subprocess.STDOUT,
                "stdin": subprocess.DEVNULL, "cwd": str(HERE)}
    if os.name == "nt":
        flags = (subprocess.CREATE_NEW_PROCESS_GROUP
                 | getattr(subprocess, "DETACHED_PROCESS", 0)
                 | getattr(subprocess, "CREATE_NO_WINDOW", 0))
        # Escape the scheduled task's job object when it allows it, so ending
        # the task instance cannot take the server down with it.
        try:
            return subprocess.Popen(
                argv, creationflags=flags | getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0),
                **kw)
        except OSError:
            return subprocess.Popen(argv, creationflags=flags, **kw)
    kw["start_new_session"] = True
    return subprocess.Popen(argv, **kw)


def ensure(port: int = PORT, *, is_up: Callable[[int], bool] = is_up,
           spawn: Callable[[list[str]], object] = _spawn,
           wait_s: float = WAIT_S, sleep: Callable[[float], None] = time.sleep) -> str:
    """Make sure a chart server listens on `port`; return a one-line status."""
    if is_up(port):
        return "already running"
    argv = [sys.executable, str(SCRIPT), "--port", str(port)]
    try:
        proc = spawn(argv)
    except Exception as exc:                      # noqa: BLE001 -- reported, not raised
        return f"launch failed: {exc}"
    step = 0.25
    for _ in range(max(1, int(wait_s / step))):
        if is_up(port):
            return f"started (pid {proc.pid})"
        code = proc.poll()
        if code is not None:
            return f"exited with code {code} (see logs/chart_server.log)"
        sleep(step)
    return f"launched (pid {proc.pid}), port not open yet"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    cmd: list[str] = []
    if "--" in args:
        i = args.index("--")
        args, cmd = args[:i], args[i + 1:]
    if not args or args[0] != "ensure":
        print("usage: chart_supervisor.py ensure [--port N] [-- command ...]")
        return 64
    port = PORT
    if "--port" in args:
        port = int(args[args.index("--port") + 1])
    status = ensure(port)
    print(f"[chart_supervisor] :{port} {status}", flush=True)
    if cmd:
        return subprocess.call(cmd)
    return 0 if is_up(port) else 1


if __name__ == "__main__":
    sys.exit(main())
