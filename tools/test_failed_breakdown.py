"""B-203 Failed Breakdown (two-candle sell-side sweep) detector + scanner.

Run:  python -m pytest tools/test_failed_breakdown.py -q
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import scanner_templates as sc

#: Flat-base length: long enough that the old low sits past BT_RSI_WARMUP.
BASE = 125
OLD, BRK, RCL = BASE + 22, BASE + 33, BASE + 34      # old low, break bar, reclaim bar


def _chart(*, break_vol=5e5, hold=False, tail=8, pool=False, fall_back=False):
    """A sell-off to an old low on bar OLD (low 48), a bounce, a close BELOW 48
    on bar BRK (the stop candle), then a close back above it on bar RCL — or
    staying below when `hold`."""
    closes = [100.0] * BASE + list(np.linspace(98, 50, 20))       # .. OLD-3
    closes += [50.0] * 4                                           # plateau incl. OLD
    closes += list(np.linspace(52, 60, 8))
    closes += [52.0, 47.0]                                         # BRK-1, BRK
    after = 45.0 if hold else 51.0
    closes += [after] + [after + (0 if hold else 1)] * tail
    if fall_back:
        closes[-1] = 46.0
    n = len(closes)
    c = pd.Series(closes, dtype=float)
    low = c - 0.5
    low[OLD] = 48.0
    if pool:
        low[OLD - 3] = 48.2                                        # a second touch
    low[BRK] = 46.0
    vol = pd.Series(1e6, index=range(n), dtype=float)
    vol[BRK] = break_vol
    idx = pd.bdate_range("2026-01-01", periods=n)
    return pd.DataFrame({"open": c.values, "high": (c + 0.5).values, "low": low.values,
                         "close": c.values, "volume": vol.values}, index=idx)


def test_close_below_then_back_above_is_an_event():
    ev = sc.failed_breakdown_events(_chart())
    assert len(ev) == 1
    e = ev[0]
    assert (e["break_bar"], e["reclaim_bar"], e["sup_bar"]) == (BRK, RCL, OLD)
    assert e["level"] == 48.0 and e["trough_low"] == 46.0
    assert e["weak_vol"] and e["divergence"] and not e["pool"]


def test_two_touches_make_a_pool():
    e = sc.failed_breakdown_events(_chart(pool=True))[0]
    assert e["pool"] and e["touches"] == 2


def test_a_breakdown_that_holds_is_no_event():
    assert sc.failed_breakdown_events(_chart(hold=True)) == []


def test_heavy_break_volume_is_still_an_event_but_not_weak():
    e = sc.failed_breakdown_events(_chart(break_vol=3e6))[0]
    assert not e["weak_vol"]


def test_no_look_ahead_the_event_is_known_at_the_reclaim_close():
    assert sc.failed_breakdown_events(_chart().iloc[:RCL + 1]) == sc.failed_breakdown_events(_chart())


def test_a_one_candle_sweep_is_not_this_event():
    # Wick below the old low but the SAME bar closes back above: Liquidity
    # Sweep's case, not a close below support.
    df = _chart(hold=True).iloc[:BRK + 1].copy()
    df.iloc[BRK, df.columns.get_loc("close")] = 50.0
    assert sc.failed_breakdown_events(df) == []


def test_scanner_fires_fresh_with_a_plan():
    hit = sc.scan_failed_breakdown(_chart(tail=1))
    assert hit and hit["pattern_type"] == "Failed Breakdown (2-bar sweep)"
    assert hit["stop"] < 46.0 and hit["target"] > hit["entry"] > hit["stop"]
    assert abs((hit["target"] - hit["entry"]) - 2 * (hit["entry"] - hit["stop"])) < 0.02


def test_scanner_is_silent_when_old_or_lost_again():
    assert sc.scan_failed_breakdown(_chart(tail=8)) is None
    assert sc.scan_failed_breakdown(_chart(tail=1, fall_back=True)) is None


def test_registered_to_screen_but_kept_out_of_the_vote():
    import opportunity_hub as oh
    name = "Failed Breakdown (2-bar sweep)"
    assert sc.SCANNERS[name]["category"] == "Entry"
    assert name in oh.PIPELINE_EXCLUDED and name not in oh.pipeline_scanners()


def test_chart_endpoint_serves_the_scanners_own_events(monkeypatch):
    import chart_server as cs
    df = _chart(tail=1)
    bars = [{"time": int(ts.timestamp()), "open": r.open, "high": r.high, "low": r.low,
             "close": r.close, "volume": r.volume} for ts, r in df.iterrows()]

    class _Src:
        def get_ohlcv(self, symbol, timeframe, n):
            return bars

    monkeypatch.setattr(cs.ds, "detect_source", lambda s: _Src())
    monkeypatch.setattr(cs.sym_dir, "resolve_symbol", lambda s: s)
    cs.app.config["TESTING"] = True
    with cs.app.test_client() as c:
        got = c.get("/api/failed_breakdown?symbol=TEST&timeframe=1d").get_json()
    assert got["fired"] is True and len(got["events"]) == 1
    e = got["events"][0]
    assert e["level"] == 48.0 and e["reclaim_time"] == bars[RCL]["time"]
    assert e["break_time"] == bars[BRK]["time"]


def test_chart_page_wires_the_overlay():
    from pathlib import Path
    html = (Path(__file__).resolve().parent / "chart_dashboard.html").read_text(encoding="utf-8")
    assert "key:'failbreak'" in html and "renderFailedBreakdown(pane)" in html
    assert "clearFailedBreakdown(pane)" in html and "/api/failed_breakdown" in html
