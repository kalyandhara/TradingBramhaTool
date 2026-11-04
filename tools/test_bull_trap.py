"""B-182 Bull Trap detector + risk scanner (synthetic bars, no network).

Run:  python -m pytest tools/test_bull_trap.py -q
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import scanner_templates as sc


#: Flat-base length: long enough that the old high sits past BT_RSI_WARMUP.
BASE = 125
OLD, BRK, TRAP = BASE + 22, BASE + 33, BASE + 34      # 147, 158, 159


def _chart(*, breakout_vol=5e5, hold=False, tail=8, reclaim=False, base=BASE):
    """A flat base, a run-up and plateau with the old high on bar OLD (high 152),
    a pullback, a close above 152 on bar BRK, then back below on bar TRAP (a
    trap) — or holding above when `hold`."""
    off = base - BASE
    closes = [100.0] * base + list(np.linspace(102, 150, 20))
    closes += [150.0] * 4                                             # 45..48 plateau
    closes += list(np.linspace(148, 140, 8))                          # 49..56
    closes += [148.0, 153.0]                                          # 57, 58 breakout
    after = 155.0 if hold else 149.0
    closes += [after] + [after - (0 if hold else 1)] * tail           # 59..
    if reclaim:
        closes[-1] = 156.0
    n = len(closes)
    c = pd.Series(closes, dtype=float)
    high = c + 0.5
    high[OLD + off] = 152.0
    high[BRK + off] = 154.0
    vol = pd.Series(1e6, index=range(n), dtype=float)
    vol[BRK + off] = breakout_vol
    idx = pd.bdate_range("2026-01-01", periods=n)
    return pd.DataFrame({"open": c.values, "high": high.values, "low": (c - 0.5).values,
                         "close": c.values, "volume": vol.values}, index=idx)


def test_a_weak_volume_failed_breakout_with_divergence_is_a_full_trap():
    ev = sc.bull_trap_events(_chart())
    assert len(ev) == 1
    e = ev[0]
    assert (e["breakout_bar"], e["trap_bar"], e["res_bar"]) == (BRK, TRAP, OLD)
    assert e["level"] == 152.0 and e["vol_x"] == 0.5
    assert e["weak_vol"] and e["divergence"] and e["full"]
    assert e["div_pts"] >= sc.BT_DIV_MIN_PTS


def test_heavy_breakout_volume_is_a_failed_breakout_but_not_a_trap():
    e = sc.bull_trap_events(_chart(breakout_vol=2e6))[0]
    assert not e["weak_vol"] and not e["full"]


def test_a_breakout_that_holds_is_no_event():
    assert sc.bull_trap_events(_chart(hold=True)) == []


def test_no_look_ahead_the_event_is_known_at_the_trap_close():
    full = sc.bull_trap_events(_chart())
    cut = sc.bull_trap_events(_chart().iloc[:TRAP + 1])
    assert cut == full


def test_events_are_spaced_by_min_gap():
    df = _chart()
    assert sc.bull_trap_events(df, min_gap=10**6)[0]["trap_bar"] == TRAP


def test_scanner_fires_on_a_fresh_trap_with_a_card():
    hit = sc.scan_bull_trap(_chart(tail=1))
    assert hit and hit["pattern_type"] == "Bull Trap"
    assert hit["stop"] > 154.0 and hit["target"] is None
    assert any("divergence" in r for r in hit["reasons"])


def test_scanner_is_silent_when_old_or_reclaimed():
    assert sc.scan_bull_trap(_chart(tail=8)) is None                 # trap 8 bars ago
    assert sc.scan_bull_trap(_chart(tail=1, reclaim=True)) is None   # back above 152


def test_registered_as_a_risk_flag():
    import opportunity_hub as oh
    assert sc.SCANNERS["Bull Trap"]["category"] == "Risk"
    assert "Bull Trap" in oh.RISK_SCANNERS


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
        got = c.get("/api/bull_trap?symbol=TEST&timeframe=1d").get_json()
    assert got["fired"] is True and len(got["events"]) == 1
    e = got["events"][0]
    assert e["full"] and e["level"] == 152.0
    assert e["trap_time"] == bars[TRAP]["time"] and e["breakout_time"] == bars[BRK]["time"]


def test_chart_page_wires_the_overlay():
    from pathlib import Path
    html = (Path(__file__).resolve().parent / "chart_dashboard.html").read_text(encoding="utf-8")
    assert "key:'bulltrap'" in html and "renderBullTrap(pane)" in html
    assert "clearBullTrap(pane)" in html and "/api/bull_trap" in html


def test_a_plain_failed_breakout_does_not_suppress_a_full_trap():
    """Amended before the run: under the first spacing rule a non-full failed
    breakout 5 sessions earlier consumed the 10-session gap and hid the trap."""
    df = _chart()
    # An earlier failed breakout of the same old high, on HEAVY volume (not a
    # trap), 5 sessions before the real one.
    df = df.copy()
    df.iloc[BRK - 6, df.columns.get_loc("close")] = 152.5
    df.iloc[BRK - 6, df.columns.get_loc("high")] = 152.6
    df.iloc[BRK - 5, df.columns.get_loc("close")] = 145.0
    df.iloc[BRK - 6, df.columns.get_loc("volume")] = 3e6
    ev = sc.bull_trap_events(df)
    assert [e["full"] for e in ev] == [False, True]
    assert ev[-1]["trap_bar"] == TRAP


def test_no_divergence_is_read_inside_the_rsi_warm_up():
    """Amended before the run: on SUNPHARMA a 300-bar window read a 4.5-pt
    divergence at a prior high ~30 bars in; the full history read 0.3."""
    e = sc.bull_trap_events(_chart(base=25))[0]
    assert e["res_bar"] < sc.BT_RSI_WARMUP
    assert not e["divergence"] and not e["full"]
