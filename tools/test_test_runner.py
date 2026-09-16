"""Tests for the test setup itself — B-83.

The suite passed under exactly one of this machine's three Pythons and nothing
invoked it. `run_tests.bat` removes that coin toss by pinning the interpreter —
which creates a new way to be wrong: **the pin can drift from the one the app
actually uses.** `.claude/launch.json` is the source of truth for "the interpreter
that runs this project", so the test below asserts the runner agrees with it.

That is the same defect shape B-79 found in `analyses/Python-Environments`, where
prose named a source of truth and a code block beneath it hard-coded a different
answer. A pin is only safe if something checks it.

Run:  python -m pytest tools/test_test_runner.py -q
"""
from __future__ import annotations

import configparser
import json
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
RUNNER = REPO / "run_tests.bat"
INI = REPO / "pytest.ini"
LAUNCH = REPO / ".claude" / "launch.json"
HOOK = REPO / "tools" / "hooks" / "pre-commit"


def _bat_var(text: str, name: str) -> str | None:
    m = re.search(rf'(?m)^set "{name}=(.+?)"\s*$', text)
    return m.group(1) if m else None


def _launch_python() -> str:
    cfg = json.loads(LAUNCH.read_text(encoding="utf-8"))
    for c in cfg.get("configurations", []):
        exe = c.get("runtimeExecutable")
        if exe and exe.lower().endswith("python.exe"):
            return exe
    raise AssertionError("no python runtimeExecutable in launch.json")


# ── the pin ──────────────────────────────────────────────────────────────────

def test_the_runner_exists_and_pins_an_interpreter():
    assert RUNNER.is_file()
    assert _bat_var(RUNNER.read_text(encoding="utf-8"), "PY_TEST")


@pytest.mark.skipif(not LAUNCH.is_file(), reason="no launch.json in this checkout")
def test_the_runner_pins_the_same_python_the_app_runs_on():
    """If these drift, the suite is green on an interpreter the dashboard never
    uses — which is precisely the 2026-08-09 failure this desk already paid for
    once, where a feature was verified against the wrong Python and broke on
    first real use."""
    pinned = _bat_var(RUNNER.read_text(encoding="utf-8"), "PY_TEST")
    assert pathlib.PureWindowsPath(pinned) == pathlib.PureWindowsPath(
        _launch_python().replace("/", "\\")), (
        f"run_tests.bat pins {pinned!r} but launch.json runs {_launch_python()!r}")


def test_the_hook_pins_the_same_interpreter_as_the_runner():
    hook = HOOK.read_text(encoding="utf-8")
    m = re.search(r'(?m)^PY="(.+?)"\s*$', hook)
    assert m, "hook no longer pins an interpreter"
    pinned = _bat_var(RUNNER.read_text(encoding="utf-8"), "PY_TEST")
    assert pathlib.PureWindowsPath(m.group(1).replace("/", "\\")) == \
        pathlib.PureWindowsPath(pinned)


def test_the_batch_interpreter_is_named_but_never_gates_the_run():
    """`--batch` reports on the scheduled-job interpreter. It must stay a report:
    a dev dependency missing on a second interpreter must not fail a green run."""
    text = RUNNER.read_text(encoding="utf-8")
    assert _bat_var(text, "PY_BATCH")
    # The exit code comes from RC, captured before the batch report runs.
    assert "set \"RC=%ERRORLEVEL%\"" in text
    assert text.index("set \"RC=%ERRORLEVEL%\"") < text.index("if defined WANT_BATCH")


# ── the config ───────────────────────────────────────────────────────────────

def test_pytest_ini_bounds_discovery_to_our_own_code():
    assert INI.is_file()
    cfg = configparser.ConfigParser()
    cfg.read(INI, encoding="utf-8")
    assert "tools" in cfg["pytest"]["testpaths"]
    norec = cfg["pytest"]["norecursedirs"]
    # The vendored bundle is not this project's code and must never be able to
    # fail this project's suite.
    assert "node_modules" in norec
    assert "breakout_scanner" in norec


def test_strict_markers_is_on():
    """Without it a typo'd @pytest.mark silently does nothing, which is a test
    that looks configured and is not."""
    cfg = configparser.ConfigParser()
    cfg.read(INI, encoding="utf-8")
    assert "--strict-markers" in cfg["pytest"]["addopts"]


# ── the dev dependency, declared rather than assumed ─────────────────────────

def test_pytest_is_declared_as_a_dependency():
    """It was installed into one of three Pythons and declared nowhere. That is
    the `ephem` and `lxml` failure again: "installed" true of a machine, not of
    the project."""
    req = (REPO / "tools" / "requirements_dev.txt").read_text(encoding="utf-8")
    assert re.search(r"(?m)^pytest\b", req)


def test_dev_requirements_are_kept_out_of_the_pipeline_requirements():
    """A scheduled job does not need a test runner, and mixing them makes the
    batch interpreter's requirements look bigger than they are."""
    pipeline = (REPO / "tools" / "requirements_pipeline.txt").read_text(encoding="utf-8")
    assert not re.search(r"(?m)^pytest\b", pipeline)


# ── the launchers (B-84) ─────────────────────────────────────────────────────
#
# This repo ships THREE apps and had a .bat for one of them. The review that
# raised B-84 said start.bat "launches the older one"; it does not — it launches
# the SBC/astro dashboard and says so in its own title. The real gap was that the
# DESK could only be started from .claude/launch.json, i.e. from inside Claude
# Code. Recorded here because the wrong diagnosis is the more interesting half.

DESK_LAUNCHER = REPO / "start_desk.bat"
SBC_LAUNCHER = REPO / "start.bat"


def _launch_line(bat: pathlib.Path) -> str:
    """The `start "..." ...` line that actually launches the app.

    Matched on the LAUNCH LINE rather than the whole file on purpose: both
    launchers now mention the other by name, in a comment and in a "run the other
    one instead" banner. A whole-file search would read those cross-references as
    the app being launched — which is how a test ends up asserting the opposite of
    what it means.
    """
    for line in bat.read_text(encoding="utf-8", errors="replace").splitlines():
        st = line.strip()
        if st.lower().startswith("start ") and ".py" in st:
            return st
    raise AssertionError(f"no launch line found in {bat.name}")


def test_each_launcher_targets_a_file_that_exists():
    for bat, target in ((DESK_LAUNCHER, r"tools\dashboard_app.py"),
                        (SBC_LAUNCHER, r"tools\dash_trading_dashboard.py")):
        assert bat.is_file(), bat
        assert target in _launch_line(bat), bat.name
        assert (REPO / target.replace("\\", "/")).is_file()


def test_the_two_launchers_do_not_launch_the_same_app():
    """They serve different products on different ports. If these ever converge,
    one is redundant and should be retired rather than duplicated."""
    desk, sbc = _launch_line(DESK_LAUNCHER), _launch_line(SBC_LAUNCHER)
    assert "dash_trading_dashboard" not in desk
    assert "dashboard_app.py" not in sbc
    assert desk != sbc


@pytest.mark.skipif(not LAUNCH.is_file(), reason="no launch.json in this checkout")
def test_the_desk_launcher_pins_the_same_python_as_launch_json():
    """Same drift risk as run_tests.bat: a launcher that starts the desk on a
    different interpreter than the one it is developed and tested against."""
    pinned = _bat_var(DESK_LAUNCHER.read_text(encoding="utf-8", errors="replace"),
                      "PYTHON")
    assert pathlib.PureWindowsPath(pinned) == pathlib.PureWindowsPath(
        _launch_python().replace("/", "\\"))


def test_the_desk_launcher_uses_the_port_launch_json_serves():
    cfg = json.loads(LAUNCH.read_text(encoding="utf-8"))
    port = next(c["port"] for c in cfg["configurations"] if c.get("name") == "dashboard")
    text = DESK_LAUNCHER.read_text(encoding="utf-8", errors="replace")
    assert _bat_var(text, "PORT") == str(port)


def test_dash_is_declared_now_that_a_launcher_depends_on_it():
    """Third instance of the undeclared-dependency pattern this repo already
    records for ephem and lxml: installed on the machine, absent from the project."""
    req = (REPO / "tools" / "requirements_pipeline.txt").read_text(encoding="utf-8")
    assert re.search(r"(?m)^dash\b", req)
