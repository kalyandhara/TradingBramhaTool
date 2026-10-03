"""Tests for simple_volume.js, run through node against the shipped JS.

Same pattern as test_obv_divergence.py / test_psar.py.

What is pinned here is the CLASSIFICATION BOUNDARY, because this indicator has
no output other than a colour: there is no line, no number, no crossing. If a
bar is the wrong colour the reader has no second channel to catch it with, and
a pocket pivot that is one bar too generous looks exactly like a real one.

Three decisions in particular are held:

* **The MA is null until its window is full.** A partial average would colour an
  IPO's whole history against a number that does not exist yet.
* **The pocket-pivot lookback is `ppvLen` TRADING days**, and we take the down
  days inside it — not the last `ppvLen` down days however far back they run.
  The author corrected his own published wording on this, and the corrected rule
  is strictly tighter, so drifting back to the loose reading would quietly
  multiply the blue bars.
* **An empty comparison is not a pass.** With no down day in the window there is
  nothing for the up volume to have overwhelmed.

Note for anyone editing these: the last bar is INSIDE its own MA window, so
changing its volume moves the average it is compared against. The tests derive
the MA from the output rather than assuming the flat value — an earlier draft of
this file assumed it and produced three failures that were the test's fault.

Skips cleanly when node is unavailable.

Run:  python -m pytest tools/test_simple_volume.py -q
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_MOD = str(HERE / "simple_volume.js").replace("\\", "/")

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node not available")


def _run(body: str):
    script = f"""
        global.window = global;
        require({_MOD!r});
        const {{classify, stats}} = window.SimpleVolume;
        {body}
    """
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


#: 60 flat bars of volume 1000, so the 50-day average is exactly 1000 until
#: something is edited. `up` sets the close above the open.
_MK = """
const mk = (n, v, up) => Array.from({length:n}, (_,i) => ({
  time: i+1, open: up?10:12, close: up?12:10, volume: v}));
const lastOf = r => r[r.length-1];
"""


def _kinds(edits: str, n: int = 60) -> str:
    """Build 60 flat up-bars, apply `edits`, print the last bar's row."""
    return _MK + f"""
      const bars = mk({n}, 1000, true);
      {edits}
      console.log(JSON.stringify(lastOf(classify(bars))));
    """


# ── the average ──────────────────────────────────────────────────────────────

def test_the_average_is_null_until_its_window_is_full():
    rows = _run(_MK + """
      const r = classify(mk(60, 1000, true));
      console.log(JSON.stringify([r[48].ma, r[49].ma]));
    """)
    assert rows == [None, 1000]


# ── dry volume ───────────────────────────────────────────────────────────────

def test_volume_at_exactly_a_fifth_of_average_is_dry_and_a_hair_above_is_not():
    # Solve for the volume that lands exactly on MA/5, remembering the bar is in
    # its own window:  v = ((49*1000 + v)/50)/5  =>  v = 49000/249.
    assert _run(_kinds("bars[59].volume = 49000/249;"))["kind"] == "dry"
    assert _run(_kinds("bars[59].volume = 49000/249 + 1;"))["kind"] == "noise"


def test_dry_outranks_everything_else():
    """A dry bar on an up day is dry, not 'up' — the quiet is the observation."""
    assert _run(_kinds("bars[59].volume = 1;"))["kind"] == "dry"


# ── pocket pivots ────────────────────────────────────────────────────────────

def test_up_volume_above_the_recent_down_day_high_is_a_pocket_pivot():
    edits = """
      bars[55] = {time:56, open:12, close:10, volume:3000};
      bars[59].volume = 3500;
    """
    assert _run(_kinds(edits))["kind"] == "ppv"


def test_up_volume_below_that_down_day_is_only_up():
    edits = """
      bars[55] = {time:56, open:12, close:10, volume:3000};
      bars[59].volume = 2500;
    """
    assert _run(_kinds(edits))["kind"] == "up"


def test_the_lookback_is_trading_days_not_down_days():
    """A huge down day 19 bars back is out of the 10-day window and must not
    block a pivot; a smaller one inside the window must."""
    out = """
      bars[40] = {time:41, open:12, close:10, volume:9000};
      bars[55] = {time:56, open:12, close:10, volume:1500};
      bars[59].volume = 2000;
    """
    assert _run(_kinds(out))["kind"] == "ppv"
    inside = out.replace("volume:1500", "volume:2500")
    assert _run(_kinds(inside))["kind"] == "up"


def test_no_down_day_to_beat_is_not_a_pivot():
    """Ten straight up days contain no selling to overwhelm, so an empty
    comparison is NOT treated as passed."""
    assert _run(_kinds("bars[59].volume = 5000;"))["kind"] == "up"


# ── down days and noise ──────────────────────────────────────────────────────

def test_down_days_split_on_the_average():
    edits = "bars[59] = {time:60, open:12, close:10, volume:%s};"
    assert _run(_kinds(edits % "2000"))["kind"] == "down"
    assert _run(_kinds(edits % "900"))["kind"] == "noise"


def test_before_the_average_exists_nothing_is_coloured():
    """With 10 bars there is no 50-day average, so no bar may claim to be above
    or below one."""
    rows = _run(_MK + """
      console.log(JSON.stringify(classify(mk(10, 1000, true)).map(r => r.kind)));
    """)
    assert set(rows) == {"noise"}


# ── the card's readout ───────────────────────────────────────────────────────

def test_rvol_is_measured_against_the_bars_own_average():
    out = _run(_MK + """
      const bars = mk(60, 1000, true); bars[59].volume = 2000;
      const rows = classify(bars);
      console.log(JSON.stringify([stats(rows).rvol, lastOf(rows).ma]));
    """)
    rvol, ma = out
    assert rvol == pytest.approx(2000 / ma * 100)


def test_rvol_is_null_while_the_average_is_still_filling():
    assert _run(_MK + """
      console.log(JSON.stringify(stats(classify(mk(10, 1000, true))).rvol));
    """) is None


def test_no_bars_gives_no_stats_rather_than_a_fabricated_one():
    assert _run("console.log(JSON.stringify([stats([]), stats(null)]));") == [None, None]


def test_the_counts_look_back_twenty_bars():
    # 80 bars, not 60: with 60 there is no index that is both outside the last
    # 20 AND old enough to have an average, so a shorter series cannot tell the
    # window rule from the null-MA rule.
    out = _run(_MK + """
      const bars = mk(80, 1000, true);
      // two dry bars inside the last 20 (60..79), one outside it
      bars[55].volume = 1; bars[65].volume = 1; bars[70].volume = 1;
      console.log(JSON.stringify(stats(classify(bars)).dry20));
    """)
    assert out == 2
