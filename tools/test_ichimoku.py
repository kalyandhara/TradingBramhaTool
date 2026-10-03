"""Tests for ichimoku.js (B-46), run through node against the shipped engine.

Same pattern as test_psar.py: the JS is what the chart draws, so the JS is
what gets tested.

Skips cleanly when node is unavailable.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ICHIMOKU = str(HERE / "ichimoku.js").replace("\\", "/")

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node not available")


def _run(bars_js: str, opts: str = "undefined") -> dict:
    script = f"""
        require({ICHIMOKU!r});
        const bars = {bars_js};
        process.stdout.write(JSON.stringify(ICHIMOKU.compute(bars, {opts})));
    """
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def _trending_bars(n: int = 80) -> str:
    """Steadily rising bars — enough for all Ichimoku periods."""
    return (f"(() => {{ const c = []; "
            f"for (let i = 0; i < {n}; i++) c.push({{time: 1700000000 + i * 86400, "
            f"open: 100 + i, high: 101 + i, low: 99 + i, close: 100.5 + i}}); "
            f"return c; }})()")


def _flat_bars(n: int = 80, price: float = 100) -> str:
    """Flat bars at a constant price."""
    return (f"(() => {{ const c = []; "
            f"for (let i = 0; i < {n}; i++) c.push({{time: 1700000000 + i * 86400, "
            f"open: {price}, high: {price + 1}, low: {price - 1}, close: {price}}}); "
            f"return c; }})()")


class TestBasicOutput:
    def test_too_few_bars(self):
        r = _run("[{time:1,open:1,high:2,low:0.5,close:1.5}]")
        assert r["tenkan"] == []
        assert r["state"] is None

    def test_output_keys(self):
        r = _run(_trending_bars())
        for k in ("tenkan", "kijun", "senkouA", "senkouB", "chikou",
                  "kumoUp", "kumoDn", "state", "opts"):
            assert k in r, f"missing key {k}"

    def test_opts_defaults(self):
        r = _run(_trending_bars())
        assert r["opts"]["tenkanP"] == 9
        assert r["opts"]["kijunP"] == 26
        assert r["opts"]["senkouBP"] == 52
        assert r["opts"]["disp"] == 26


class TestTenkanKijun:
    def test_tenkan_starts_at_bar_8(self):
        r = _run(_trending_bars())
        assert len(r["tenkan"]) == 80 - 8  # starts at index 8 (period 9 - 1)

    def test_kijun_starts_at_bar_25(self):
        r = _run(_trending_bars())
        assert len(r["kijun"]) == 80 - 25  # starts at index 25 (period 26 - 1)

    def test_tenkan_is_midpoint_of_9(self):
        """On a steady ramp, tenkan = midpoint of 9-bar high/low range."""
        r = _run(_trending_bars())
        # Bar 8 (0-indexed): highest high = 101+8=109, lowest low = 99+0=99
        # Midpoint = (109 + 99) / 2 = 104
        first = r["tenkan"][0]
        assert first["value"] == 104.0

    def test_flat_bars_tenkan_equals_price(self):
        r = _run(_flat_bars())
        for pt in r["tenkan"]:
            assert pt["value"] == 100.0  # midpoint of (101, 99) = 100


class TestSenkouDisplacement:
    def test_senkou_a_displaced_forward(self):
        """Senkou A points should have times 26 bars ahead of their source."""
        r = _run(_trending_bars())
        assert len(r["senkouA"]) > 0
        # The first Senkou A comes from bar 25 (when both tenkan and kijun exist)
        # displaced by 26, so its time should be bar 51's time
        first = r["senkouA"][0]
        expected_time = 1700000000 + 51 * 86400
        assert first["time"] == expected_time

    def test_senkou_extends_past_last_bar(self):
        """Senkou spans should have points beyond the last bar's time."""
        r = _run(_trending_bars())
        last_bar_time = 1700000000 + 79 * 86400
        senkou_times = [p["time"] for p in r["senkouA"]]
        future = [t for t in senkou_times if t > last_bar_time]
        assert len(future) > 0, "Senkou A should project into the future"


class TestChikou:
    def test_chikou_displaced_backward(self):
        """Chikou plots the close 26 bars behind."""
        r = _run(_trending_bars())
        # Bar 26's close plotted at bar 0's time
        first = r["chikou"][0]
        assert first["time"] == 1700000000  # bar 0's time
        assert first["value"] == 100.5 + 26  # bar 26's close

    def test_chikou_length(self):
        r = _run(_trending_bars())
        # With 80 bars and displacement 26, chikou runs from bar 26..79 plotted at 0..53
        assert len(r["chikou"]) == 80 - 26


class TestCloudSplit:
    def test_kumo_up_and_dn_cover_all_cloud_bars(self):
        """Every bar with both Senkou values should be in kumoUp or kumoDn."""
        r = _run(_trending_bars())
        total = len(r["kumoUp"]) + len(r["kumoDn"])
        # Senkou B starts at bar 51 (period 52 - 1), so cloud exists from there
        assert total == 80 - 51

    def test_flat_cloud_is_all_up(self):
        """Flat bars: Senkou A = Senkou B (both midpoints identical), A >= B → kumoUp."""
        r = _run(_flat_bars())
        assert len(r["kumoDn"]) == 0
        assert len(r["kumoUp"]) > 0


class TestState:
    def test_state_above_cloud_in_uptrend(self):
        r = _run(_trending_bars())
        assert r["state"]["priceVsCloud"] == "above"

    def test_state_tk_cross_bullish_in_uptrend(self):
        r = _run(_trending_bars())
        assert r["state"]["tkCross"] == "bullish"

    def test_state_below_cloud_in_downtrend(self):
        """Falling bars: price should be below the cloud."""
        bars_js = ("(() => { const c = []; "
                   "for (let i = 0; i < 80; i++) c.push({time: 1700000000 + i * 86400, "
                   "open: 200 - i, high: 201 - i, low: 199 - i, close: 199.5 - i}); "
                   "return c; })()")
        r = _run(bars_js)
        assert r["state"]["priceVsCloud"] == "below"
        assert r["state"]["tkCross"] == "bearish"


class TestCustomPeriods:
    def test_custom_tenkan_period(self):
        r = _run(_trending_bars(), '{tenkanPeriod: 5}')
        assert r["opts"]["tenkanP"] == 5
        # Tenkan starts at bar 4 with period 5
        assert len(r["tenkan"]) == 80 - 4


class TestStringTimes:
    def test_string_timestamps_for_future(self):
        """When bars use 'YYYY-MM-DD' strings, future Senkou times are also strings."""
        bars_js = ("(() => { const c = []; const d = new Date('2024-01-01'); "
                   "for (let i = 0; i < 80; i++) { "
                   "const dt = new Date(d); dt.setDate(d.getDate() + i); "
                   "const ts = dt.toISOString().slice(0,10); "
                   "c.push({time: ts, open: 100+i, high: 101+i, low: 99+i, close: 100.5+i}); "
                   "} return c; })()")
        r = _run(bars_js)
        last_senkou = r["senkouA"][-1]
        assert isinstance(last_senkou["time"], str)
        assert last_senkou["time"] > "2024-03-20"
