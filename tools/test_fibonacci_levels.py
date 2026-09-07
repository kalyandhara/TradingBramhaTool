"""Tests for fibonacci.js's level grid, run through node (the shipped engine).

Same pattern as `test_renko_parity.py`: the JS is what the chart draws, so it is
what gets tested, rather than a Python re-implementation that could drift.

The 0.886 and 1.13 rungs were added for the QM / CHOCH setups, which price their
deepest entry at 88.6% and their stop at 113%. What these tests mostly guard is
that adding them did NOT change what may move money: 0.886 stays entry-ineligible
unless explicitly asked for, and 1.13 never becomes an entry at all.

Skips cleanly when node is unavailable.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node not available")


def _levels(direction: str = "up", opts: str = "undefined") -> list[dict]:
    """Run FIB.computeLevels on a 100→200 leg and return the level list.

    A range of exactly 100 makes every ratio readable as a price: the 0.886 rung
    lands on 111.4 and nothing has to be reverse-engineered from a float.
    """
    script = f"""
        global.window = global;
        require({str(HERE / 'fibonacci.js').replace(chr(92), '/')!r});
        const swing = {{direction: {direction!r}, high: 200, low: 100, range: 100}};
        process.stdout.write(JSON.stringify(FIB.computeLevels(swing, {opts})));
    """
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def _by_ratio(levels: list[dict], ratio: float, kind: str | None = None) -> dict:
    for l in levels:
        if abs(l["ratio"] - ratio) < 1e-9 and (kind is None or l["kind"] == kind):
            return l
    raise AssertionError(f"no level at ratio {ratio}" + (f" kind {kind}" if kind else ""))


# ── the two new rungs exist and sit where the QM method puts them ────────────

def test_deep_retracement_886_exists_on_the_retracement_grid():
    lv = _by_ratio(_levels(), 0.886, "retracement")
    assert lv["price"] == pytest.approx(111.4, abs=0.01)
    assert lv["deep"] is True


def test_overshoot_113_sits_BEYOND_the_leg_origin():
    """113% is past the swing low — the setup is wrong there, not cheap."""
    lv = _by_ratio(_levels(), 1.13, "overshoot")
    assert lv["price"] == pytest.approx(87.0, abs=0.01)
    assert lv["price"] < 100.0            # the leg origin


def test_both_rungs_mirror_correctly_on_a_down_leg():
    down = _levels(direction="down")
    assert _by_ratio(down, 0.886, "retracement")["price"] == pytest.approx(188.6, abs=0.01)
    # Overshoot runs past the origin on the other side too.
    assert _by_ratio(down, 1.13, "overshoot")["price"] == pytest.approx(213.0, abs=0.01)


# ── what may move money is UNCHANGED ─────────────────────────────────────────

def test_886_is_not_entry_eligible_by_default():
    assert _by_ratio(_levels(), 0.886, "retracement")["entryEligible"] is False


def test_886_becomes_eligible_only_when_explicitly_asked_for():
    deep = _levels(opts="{deepEntry: true}")
    assert _by_ratio(deep, 0.886, "retracement")["entryEligible"] is True
    # and the shallow rungs are untouched by the opt-in
    assert _by_ratio(deep, 0.618, "retracement")["entryEligible"] is True
    assert _by_ratio(deep, 0.236, "retracement")["entryEligible"] is False


def test_113_is_never_an_entry_even_under_deep_entry():
    assert _by_ratio(_levels(opts="{deepEntry: true}"), 1.13, "overshoot")["entryEligible"] is False


def test_the_pre_existing_entry_band_is_unchanged():
    """The rungs that were eligible before must still be exactly the eligible set."""
    eligible = {l["ratio"] for l in _levels() if l["entryEligible"]}
    assert eligible == {0.382, 0.5, 0.618, 0.786}


def test_golden_pocket_did_not_move():
    golden = {l["ratio"] for l in _levels() if l["golden"]}
    assert golden == {0.5, 0.618}


def test_every_level_carries_the_same_keys():
    """A missing key on one rung is how a renderer starts branching on undefined."""
    levels = _levels()
    keys = {"ratio", "price", "kind", "label", "golden", "deep", "entryEligible"}
    for l in levels:
        assert set(l) == keys, f"{l['kind']} {l['ratio']} has {set(l) ^ keys}"
