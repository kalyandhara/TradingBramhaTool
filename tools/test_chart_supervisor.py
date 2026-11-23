"""chart_supervisor: the alert job brings the chart server up itself (SBC_Tool-j0x).

alert_watcher.js reads candles from chart_server on :5001, which only ever
started with the desk. From 2026-10-23 to 2026-11-23, 813 of 1,965 alert runs
were BLIND (nothing could be fetched) because nobody had the desk open. The
alert job now runs through `chart_supervisor.py ensure -- <watcher>`, which
starts the server when the port is closed.

    py -3 -m pytest tools/test_chart_supervisor.py -q
"""
import sys

import chart_supervisor as sup
import scheduler_core as sc


class _Proc:
    def __init__(self, pid=123, code=None):
        self.pid, self._code = pid, code

    def poll(self):
        return self._code


def _ensure(up_seq, proc=None, spawn_exc=None):
    """Run ensure() with a scripted port state; return (status, spawned argvs)."""
    seq = list(up_seq)
    spawned = []

    def is_up(port):
        return seq.pop(0) if len(seq) > 1 else seq[0]

    def spawn(argv):
        if spawn_exc:
            raise spawn_exc
        spawned.append(argv)
        return proc or _Proc()

    st = sup.ensure(5001, is_up=is_up, spawn=spawn, wait_s=1.0, sleep=lambda s: None)
    return st, spawned


def test_running_server_is_left_alone():
    st, spawned = _ensure([True])
    assert st == "already running" and spawned == []


def test_closed_port_starts_the_server_and_waits_for_it():
    st, spawned = _ensure([False, False, True])
    assert st == "started (pid 123)"
    argv = spawned[0]
    assert argv[1].endswith("chart_server.py")
    assert argv[2:] == ["--port", "5001"]           # loopback default: no --lan


def test_a_child_that_dies_is_reported():
    st, _ = _ensure([False], proc=_Proc(code=1))
    assert st == "exited with code 1 (see logs/chart_server.log)"


def test_a_slow_child_is_reported_not_waited_on_forever():
    st, _ = _ensure([False])
    assert st == "launched (pid 123), port not open yet"


def test_a_launch_error_is_reported():
    st, _ = _ensure([False], spawn_exc=OSError("no python"))
    assert st.startswith("launch failed: ")


def test_a_locked_log_falls_back_instead_of_failing_the_launch(tmp_path, monkeypatch):
    """Found live 2026-11-23: a running server held chart_server.log open
    without write-sharing, so open(LOG, "ab") raised PermissionError and the
    supervisor could not start a second server. The launch must not depend on
    the log."""
    locked = tmp_path / "chart_server.log"
    monkeypatch.setattr(sup, "LOG", locked)
    real_open = open

    def fake_open(path, *a, **k):
        if str(path) == str(locked):
            raise PermissionError(13, "Permission denied")
        return real_open(path, *a, **k)

    monkeypatch.setattr(sup, "_builtin_open", fake_open)
    fh = sup._open_log()
    try:
        assert fh.name == str(tmp_path / "chart_server.supervisor.log")
    finally:
        fh.close()


def test_main_runs_the_command_and_returns_its_exit_code(monkeypatch, capsys):
    monkeypatch.setattr(sup, "ensure", lambda port, **k: "already running")
    code = sup.main(["ensure", "--", sys.executable, "-c", "import sys; sys.exit(3)"])
    assert code == 3
    assert "[chart_supervisor] :5001 already running" in capsys.readouterr().out


def test_main_without_a_command_returns_0_when_up(monkeypatch):
    monkeypatch.setattr(sup, "ensure", lambda port, **k: "started (pid 9)")
    monkeypatch.setattr(sup, "is_up", lambda port: True)
    assert sup.main(["ensure"]) == 0


def test_the_alert_job_runs_through_the_supervisor():
    cmd = sc.JOBS["alert_watcher"].command
    assert "chart_supervisor.py" in cmd and " ensure -- " in cmd
    assert cmd.index("chart_supervisor.py") < cmd.index("alert_watcher.js")
    assert cmd.rstrip().endswith("--once")
