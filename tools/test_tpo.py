"""Tests for tpo.js (B-47), run through node against the shipped engine.

Same pattern as test_psar.py / test_ichimoku.py.

Skips cleanly when node is unavailable.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TPO = str(HERE / "tpo.js").replace("\\", "/")

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node not available")


def _run(bars_js: str, opts: str = "undefined") -> dict:
    script = f"""
        require({TPO!r});
        const bars = {bars_js};
        process.stdout.write(JSON.stringify(TPO.compute(bars, {opts})));
    """
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def _intraday_bars(n: int = 120, base: float = 100, step: float = 0.5) -> str:
    """Simulate 30-min intraday bars across 1 day (enough for several brackets)."""
    return (f"(() => {{ const c = []; "
            f"for (let i = 0; i < {n}; i++) c.push({{time: 1700000000 + i * 1800, "
            f"open: {base} + i * {step}, high: {base} + i * {step} + 1, "
            f"low: {base} + i * {step} - 1, close: {base} + i * {step} + 0.5}}); "
            f"return c; }})()")


def _flat_intraday(n: int = 60, price: float = 100) -> str:
    """Flat bars at a constant price, 30-min intervals."""
    return (f"(() => {{ const c = []; "
            f"for (let i = 0; i < {n}; i++) c.push({{time: 1700000000 + i * 1800, "
            f"open: {price}, high: {price + 1}, low: {price - 1}, close: {price}}}); "
            f"return c; }})()")


def _daily_bars(n: int = 80) -> str:
    """Daily bars for weekly grouping."""
    return (f"(() => {{ const c = []; "
            f"for (let i = 0; i < {n}; i++) c.push({{time: 1700000000 + i * 86400, "
            f"open: 100 + i, high: 101 + i, low: 99 + i, close: 100.5 + i}}); "
            f"return c; }})()")


class TestBasicOutput:
    def test_too_few_bars(self):
        r = _run("[{time:1,open:1,high:2,low:0.5,close:1.5}]")
        assert r["sessions"] == []
        assert r["state"] is None

    def test_output_keys(self):
        r = _run(_intraday_bars())
        assert "sessions" in r
        assert "state" in r
        assert "opts" in r

    def test_opts_defaults(self):
        r = _run(_intraday_bars())
        assert r["opts"]["bracketMinutes"] == 30
        assert r["opts"]["valueAreaPct"] == 0.70
        assert r["opts"]["tickSize"] == "auto"


class TestSessionStructure:
    def test_session_has_required_keys(self):
        r = _run(_intraday_bars())
        s = r["sessions"][0]
        for k in ("key", "letters", "grid", "pocPrice", "vaHigh", "vaLow",
                  "ibHigh", "ibLow", "singlePrints", "shape", "hi", "lo",
                  "startTime", "endTime", "tickSize", "nRows", "nBrackets",
                  "tpoCounts", "pocRow", "pocMax", "priceLow", "priceHigh"):
            assert k in s, f"missing key {k}"

    def test_letters_length_equals_nrows(self):
        r = _run(_intraday_bars())
        s = r["sessions"][0]
        assert len(s["letters"]) == s["nRows"]

    def test_poc_is_within_range(self):
        r = _run(_intraday_bars())
        s = r["sessions"][0]
        assert s["lo"] <= s["pocPrice"] <= s["hi"]


class TestValueArea:
    def test_va_contains_poc(self):
        r = _run(_intraday_bars())
        s = r["sessions"][0]
        assert s["vaLow"] <= s["pocPrice"] <= s["vaHigh"]

    def test_va_within_session_range(self):
        r = _run(_intraday_bars())
        s = r["sessions"][0]
        assert s["lo"] <= s["vaLow"]
        assert s["vaHigh"] <= s["hi"]


class TestInitialBalance:
    def test_ib_exists_for_multi_bracket(self):
        r = _run(_intraday_bars(20))
        s = r["sessions"][0]
        assert s["ibHigh"] is not None
        assert s["ibLow"] is not None
        assert s["ibLow"] <= s["ibHigh"]


class TestShape:
    def test_shape_is_valid(self):
        r = _run(_intraday_bars())
        for s in r["sessions"]:
            assert s["shape"] in ("D", "P", "B", "I")

    def test_flat_bars_produce_i_shape(self):
        r = _run(_flat_intraday())
        s = r["sessions"][0]
        assert s["shape"] == "I"


class TestSinglePrints:
    def test_single_prints_are_prices(self):
        r = _run(_intraday_bars())
        s = r["sessions"][0]
        for p in s["singlePrints"]:
            assert isinstance(p, (int, float))
            assert s["lo"] <= p <= s["hi"]


class TestState:
    def test_state_has_required_keys(self):
        r = _run(_intraday_bars())
        st = r["state"]
        for k in ("pocPrice", "vaHigh", "vaLow", "ibHigh", "ibLow",
                  "shape", "priceVsPoc", "nSinglePrints"):
            assert k in st, f"missing state key {k}"

    def test_price_vs_poc_is_valid(self):
        r = _run(_intraday_bars())
        assert r["state"]["priceVsPoc"] in ("above_va", "below_va", "at_poc", "in_va")


class TestDailyGrain:
    def test_daily_bars_use_weekly_grain(self):
        """Daily bars should group into weekly sessions."""
        r = _run(_daily_bars())
        assert len(r["sessions"]) > 1
        assert "W" in r["sessions"][0]["key"]


class TestCustomOpts:
    def test_custom_bracket_minutes(self):
        r = _run(_intraday_bars(), '{bracketMinutes: 60}')
        assert r["opts"]["bracketMinutes"] == 60

    def test_custom_tick_size(self):
        r = _run(_intraday_bars(), '{tickSize: 1.0}')
        s = r["sessions"][0]
        assert s["tickSize"] == 1.0


class TestLetterAssignment:
    def test_letters_contain_only_valid_chars(self):
        r = _run(_intraday_bars(20))
        s = r["sessions"][0]
        valid = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
        for row_letters in s["letters"]:
            for ch in row_letters:
                assert ch in valid, f"invalid letter {ch}"

    def test_first_bracket_is_A(self):
        r = _run(_intraday_bars(20))
        s = r["sessions"][0]
        has_a = any("A" in l for l in s["letters"])
        assert has_a
