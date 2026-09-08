"""Tests for obv_divergence.js (B-61), run through node against the shipped JS.

Same pattern as test_psar.py / test_fibonacci_levels.py.

Two things are pinned here. The OBV arithmetic, because its whole character —
a running total that books the ENTIRE bar volume by the close-to-close sign — is
what produces both its signal and its main artifact. And `volConcentration`,
which is this module's answer to that artifact: LuxAlgo names a single enormous
print as the main false-signal source and suggests inspecting bars by hand, so
the number that makes that inspectable must not silently break.

There is deliberately NO test of the divergence walk itself. That lives in
rsi_divergence.js and is exercised there; duplicating it would be testing the
same logic twice and would mask a drift rather than catch one.

Skips cleanly when node is unavailable.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_P = lambda name: str(HERE / name).replace("\\", "/")

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node not available")


def _run(body: str) -> dict:
    script = f"""
        global.window = global;
        require({_P('elliott_wave.js')!r});
        require({_P('rsi_divergence.js')!r});
        require({_P('obv_divergence.js')!r});
        {body}
    """
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


_MAKE_BARS = """
        function seg(bars, a, b, n, vol) {
          for (let i = 0; i < n; i++) {
            const v = a + (b - a) * i / (n - 1);
            const t = 1700000000 + bars.length * 86400;
            bars.push({time: t, open: v, high: v * 1.02, low: v * 0.98,
                       close: v, volume: vol});
          }
        }
"""


# ── OBV arithmetic ───────────────────────────────────────────────────────────

def test_obv_adds_the_whole_bar_volume_on_an_up_close():
    r = _run("""
        const bars = [
          {time: 1, close: 100, volume: 500},
          {time: 2, close: 101, volume: 300},
          {time: 3, close: 102, volume: 200},
        ];
        process.stdout.write(JSON.stringify(OBVDIV.obvSeries(bars)));
    """)
    assert [p["value"] for p in r] == [0, 300, 500]


def test_obv_subtracts_the_whole_bar_volume_on_a_down_close():
    r = _run("""
        const bars = [
          {time: 1, close: 100, volume: 500},
          {time: 2, close: 99, volume: 300},
          {time: 3, close: 98, volume: 200},
        ];
        process.stdout.write(JSON.stringify(OBVDIV.obvSeries(bars)));
    """)
    assert [p["value"] for p in r] == [0, -300, -500]


def test_a_flat_close_leaves_obv_unchanged():
    r = _run("""
        const bars = [
          {time: 1, close: 100, volume: 500},
          {time: 2, close: 100, volume: 900},
          {time: 3, close: 101, volume: 100},
        ];
        process.stdout.write(JSON.stringify(OBVDIV.obvSeries(bars)));
    """)
    assert [p["value"] for p in r] == [0, 0, 100]


# ── volConcentration: the artifact made measurable ───────────────────────────

def test_evenly_spread_volume_scores_one_over_n():
    r = _run("""
        const bars = [];
        for (let i = 0; i < 10; i++) bars.push({time: i, close: 100, volume: 1000});
        process.stdout.write(JSON.stringify({c: OBVDIV.volConcentration(bars, 0, 9)}));
    """)
    assert r["c"] == pytest.approx(0.1, abs=0.001)


def test_one_enormous_print_dominating_the_window_scores_near_one():
    """The exact artifact LuxAlgo warns about: one session IS the divergence."""
    r = _run("""
        const bars = [];
        for (let i = 0; i < 10; i++) bars.push({time: i, close: 100, volume: 100});
        bars[4].volume = 100000;
        process.stdout.write(JSON.stringify({c: OBVDIV.volConcentration(bars, 0, 9)}));
    """)
    assert r["c"] > 0.99


def test_zero_volume_window_is_none_not_a_divide_by_zero():
    r = _run("""
        const bars = [];
        for (let i = 0; i < 5; i++) bars.push({time: i, close: 100, volume: 0});
        process.stdout.write(JSON.stringify({c: OBVDIV.volConcentration(bars, 0, 4)}));
    """)
    assert r["c"] is None


# ── integration: the shape that comes back ───────────────────────────────────

def test_a_bullish_regular_divergence_is_found_and_labelled():
    """Price makes a lower low while OBV makes a higher low."""
    r = _run(_MAKE_BARS + """
        const bars = [];
        seg(bars, 100, 130, 25, 1e6);
        seg(bars, 130, 95, 25, 1.5e6);
        seg(bars, 95, 120, 25, 1e6);
        seg(bars, 120, 90, 25, 3e5);
        const res = OBVDIV.compute(bars);
        process.stdout.write(JSON.stringify(res.divergences));
    """)
    assert r, "the fixture must produce a divergence"
    d = r[0]
    assert d["label"] == "Regular Bullish"
    assert d["to"]["price"] < d["from"]["price"], "price lower low"
    assert d["to"]["obv"] > d["from"]["obv"], "OBV higher low"


def test_every_divergence_carries_obv_not_rsi():
    """RSIDIV's output field is named `rsi`; leaking that name here would tell a
    reader they are looking at an oscillator they are not."""
    r = _run(_MAKE_BARS + """
        const bars = [];
        seg(bars, 100, 130, 25, 1e6); seg(bars, 130, 95, 25, 1.5e6);
        seg(bars, 95, 120, 25, 1e6);  seg(bars, 120, 90, 25, 3e5);
        process.stdout.write(JSON.stringify(OBVDIV.compute(bars).divergences));
    """)
    for d in r:
        assert "obv" in d["from"] and "obv" in d["to"]
        assert "rsi" not in d["from"] and "rsi" not in d["to"]
        assert d["volConcentration"] is not None


def test_it_returns_empty_rather_than_throwing_without_the_divergence_engine():
    """Load order is stated in the header; a missing dependency must degrade to
    an empty overlay, never to a silently wrong one."""
    out = subprocess.run(
        ["node", "-e", f"""
            global.window = global;
            require({_P('obv_divergence.js')!r});
            const bars = [];
            for (let i = 0; i < 60; i++) bars.push(
              {{time: i, open: 100, high: 101, low: 99, close: 100, volume: 1000}});
            process.stdout.write(JSON.stringify(OBVDIV.compute(bars)));
        """], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout)["divergences"] == []


def test_too_few_bars_returns_empty():
    r = _run("""
        process.stdout.write(JSON.stringify(OBVDIV.compute(
          [{time:1, open:1, high:1, low:1, close:1, volume:1}])));
    """)
    assert r["divergences"] == [] and r["obv"] == []


def test_it_emits_no_trade_plan():
    """Context, not a signal — LuxAlgo's own advice is to require price
    confirmation, and this desk has measured no forward edge for it."""
    r = _run(_MAKE_BARS + """
        const bars = [];
        seg(bars, 100, 130, 25, 1e6); seg(bars, 130, 95, 25, 1.5e6);
        seg(bars, 95, 120, 25, 1e6);  seg(bars, 120, 90, 25, 3e5);
        process.stdout.write(JSON.stringify(OBVDIV.compute(bars).divergences));
    """)
    for d in r:
        for k in ("entry", "stop", "target", "score"):
            assert k not in d
