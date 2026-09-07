"""Tests for psar.js (B-59), run through node against the shipped engine.

Same pattern as `test_renko_parity.py` / `test_fibonacci_levels.py`: the JS is
what the chart draws, so the JS is what gets tested.

The test that earns its keep is `test_the_dot_for_a_bar_does_not_use_that_bar`.
A naive Parabolic SAR seats today's dot from today's extreme; it looks almost
identical on screen and it REPAINTS, so any measurement later built on it gets a
free peek at the bar it is supposed to be trading. That property is invisible to
the eye and trivial to reintroduce, which is exactly what a test is for.

Skips cleanly when node is unavailable.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PSAR = str(HERE / "psar.js").replace("\\", "/")

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node not available")


def _run(bars_js: str, opts: str = "undefined") -> dict:
    script = f"""
        require({PSAR!r});
        const bars = {bars_js};
        process.stdout.write(JSON.stringify(PSAR.compute(bars, {opts})));
    """
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def _ramp(n_up: int = 25, n_dn: int = 15) -> str:
    """A clean rise then a clean fall — one unambiguous reversal."""
    return (f"(() => {{ const c = []; "
            f"for (let i = 0; i < {n_up}; i++) c.push(100 + i * 2); "
            f"for (let i = 0; i < {n_dn}; i++) c.push({100 + 2 * (n_up - 1)} - i * 3); "
            f"return c.map((v, i) => ({{time: 1700000000 + i * 86400, open: v, "
            f"high: v * 1.01, low: v * 0.99, close: v}})); }})()")


# ── causality: the property that makes this backtestable later ───────────────

def test_the_dot_for_a_bar_does_not_use_that_bar():
    """Mutate ONE bar's high and low; its own dot must not move.

    `path[i]` is a function of bar i-1's SAR/EP/AF and the ranges of bars i-1 and
    i-2 — so it is known at bar i's open. Dots AFTER the mutated bar are expected
    to move; that is the state updating, not a look-ahead.
    """
    base = _run(_ramp())
    mutated = _run(
        "(() => { const b = " + _ramp() + "; "
        "b[20].high *= 1.30; b[20].low *= 0.70; return b; })()")
    i = next(k for k, p in enumerate(base["path"])
             if p["time"] == base["path"][0]["time"] + 20 * 86400 - 2 * 86400)
    # path[0] is bar 2, so bar 20 is path index 18.
    assert base["path"][18]["value"] == mutated["path"][18]["value"], (
        "the dot moved when its own bar changed — that is repainting")


def test_dots_before_a_mutated_bar_are_untouched():
    base = _run(_ramp())
    mutated = _run(
        "(() => { const b = " + _ramp() + "; "
        "b[20].high *= 1.30; b[20].low *= 0.70; return b; })()")
    for k in range(18):
        assert base["path"][k]["value"] == mutated["path"][k]["value"]


# ── Wilder's parameters ──────────────────────────────────────────────────────

def test_af_caps_at_020():
    """No reversal in the fixture, deliberately: `state` reports the CURRENT run,
    so a fixture that flips would report the post-flip acceleration instead."""
    r = _run(_ramp(n_up=60, n_dn=0))
    assert not r["flips"]
    assert r["state"]["af"] == pytest.approx(0.20)


def test_af_resets_on_a_flip_and_then_steps_per_new_extreme():
    """A few bars into a fresh down-run the acceleration is small, not the cap.

    `state` is only observable at the end of the series, so the reset is asserted
    through its consequence: the 25-bar up-run reaches the 0.20 cap, and a handful
    of bars after the reversal the value is **0.06**. That is only reachable if
    the flip reset it to the 0.02 seed and it then stepped once per new low —
    had it carried on from the cap it would still read 0.20.
    """
    r = _run(_ramp(n_up=25, n_dn=5))
    assert len(r["flips"]) == 1
    assert r["state"]["dir"] == -1
    assert r["state"]["af"] == pytest.approx(0.06)
    assert r["state"]["af"] < _run(_ramp(n_up=25, n_dn=0))["state"]["af"]


def test_parameters_are_overridable_and_actually_used():
    slow = _run(_ramp(n_up=60, n_dn=0), opts="{afMax: 0.05}")
    assert slow["state"]["af"] == pytest.approx(0.05)
    assert slow["opts"]["afMax"] == pytest.approx(0.05)


# ── the two-bar clamp ────────────────────────────────────────────────────────

def test_sar_never_penetrates_the_last_two_bars_while_long():
    """Wilder's clamp — the one most implementations omit."""
    r = _run(_ramp())
    bars = json.loads(subprocess.run(
        ["node", "-e", f"process.stdout.write(JSON.stringify({_ramp()}))"],
        capture_output=True, text=True).stdout)
    for k, p in enumerate(r["path"]):
        i = k + 2                                   # path[0] is bar 2
        if p["dir"] == 1:
            assert p["value"] <= min(bars[i - 1]["low"], bars[i - 2]["low"]) + 1e-6
        else:
            assert p["value"] >= max(bars[i - 1]["high"], bars[i - 2]["high"]) - 1e-6


# ── shape and behaviour ──────────────────────────────────────────────────────

def test_a_clean_rise_then_fall_produces_exactly_one_flip():
    r = _run(_ramp())
    assert len(r["flips"]) == 1
    assert r["flips"][0]["dir"] == -1


def test_flips_carry_the_bar_index_so_they_are_fillable():
    """Same treatment renko.js gives its brick flips: the flip is known at that
    bar's close and fills at the NEXT open."""
    r = _run(_ramp())
    f = r["flips"][0]
    assert isinstance(f["index"], int) and f["index"] >= 2
    assert f["time"] == r["path"][f["index"] - 2]["time"]


def test_up_and_dn_partition_the_path():
    r = _run(_ramp())
    assert len(r["up"]) + len(r["dn"]) == len(r["path"])
    assert {p["time"] for p in r["up"]} | {p["time"] for p in r["dn"]} == \
           {p["time"] for p in r["path"]}


def test_too_few_bars_returns_empty_rather_than_throwing():
    r = _run("[{time:1,open:1,high:1,low:1,close:1}]")
    assert r["path"] == [] and r["state"] is None


def test_it_emits_no_trade_plan():
    """B-59 is an OVERLAY. No entry/stop/target, and no scanner registration —
    B-46's objection stands against a PSAR signal until an overlap check runs."""
    r = _run(_ramp())
    for k in ("entry", "stop", "target", "score", "signal"):
        assert k not in r
