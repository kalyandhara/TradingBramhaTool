"""Tests for tour_base_rates.py (B-186): the badge on a tour card, measured.

What has to hold for a badge to be honest:

  * an event is recorded on the bar the card would FIRST have appeared, using only
    bars up to that one (a failed breakout is known when it fails, not at the
    breakout);
  * a state that stays true for weeks is one event, not thirty;
  * a planted effect comes out EDGE, a null panel ORDINARY, a thin one TOO_FEW,
    and a bearish card that works is EDGE, not INVERTED.
"""
import numpy as np
import pandas as pd
import pytest

import chart_tour as ct
import tour_base_rates as br
from test_chart_tour import frame


MARK = 7777.0   # a volume value that marks a planted event bar


def _stub(key, kind, claim, tone="up", state_bars=None):
    """A detector that fires when the window's last bar carries the marker volume
    (dated) or while its last bar is inside `state_bars` (state)."""
    def fn(win):
        last = len(win) - 1
        if kind == "dated" and win["volume"].iloc[-1] == MARK:
            return [ct.Finding(f"{key}:{ct.t_of(win, -1)}", key, key, "", {}, ct.t_of(win, -1),
                               0.5, tone, None, [])]
        if kind == "state" and state_bars is not None and win.index[-1] in state_bars:
            return [ct.Finding(f"{key}:state", key, key, "", {}, None, 0.5, tone, None, [])]
        return []
    return ct.Detector(key, key, "evector", kind, claim, fn)


def _panel(n_sym=40, n=420, drift=0.0, every=40, start=150, seed=0, bear=False, magnitude=False,
           first_third_only=False):
    rng = np.random.default_rng(seed)
    frames = {}
    for s in range(n_sym):
        r = rng.normal(0, 0.01, n)
        v = np.full(n, 1000.0)
        for b in range(start, n - 70, every):
            if first_third_only and b > start + (n - 70 - start) / 3:
                continue
            v[b] = MARK
            if magnitude:
                r[b + 1:b + 21] += (0.004 if rng.random() < 0.5 else -0.004)
            else:
                r[b + 1:b + 21] += (-drift if bear else drift) / 20
        frames[f"S{s}"] = frame(100 * np.exp(np.cumsum(r)), volume=v)
    return frames


def test_events_point_in_time_no_lookahead():
    c = np.full(120, 100.0)
    c[90] = 106.0          # breakout over the 55-day closing high
    c[91:95] = 104.0
    c[95:] = 97.0          # fails at bar 95 (< 0.98 x 100)
    df = frame(c)
    ev = br.detector_events(df, {"breakout55": ct.DETECTORS["breakout55"],
                                 "failed_breakout55": ct.DETECTORS["failed_breakout55"]}, start=60)
    assert [e["bar"] for e in ev if e["key"] == "breakout55"] == [90]
    assert [e["bar"] for e in ev if e["key"] == "failed_breakout55"] == [95]


def test_state_refractory_20():
    df = frame(np.full(300, 100.0))
    on = set(df.index[100:130]) | set(df.index[155:170])
    det = {"sq": _stub("sq", "state", "magnitude", "neutral", state_bars=on)}
    ev = br.detector_events(df, det, start=60)
    assert [e["bar"] for e in ev] == [100, 155]
    on2 = set(df.index[100:110]) | set(df.index[115:125])     # back on 15 bars after the event
    ev2 = br.detector_events(df, {"sq": _stub("sq", "state", "magnitude", "neutral", state_bars=on2)},
                             start=60)
    assert [e["bar"] for e in ev2] == [100]                    # 115 - 100 < 20: refractory


def test_planted_edge_labelled_edge():
    det = {"x": _stub("x", "dated", "directional")}
    rows = br.label(br.measure(_panel(drift=0.03), det, start=100))
    assert rows["x"]["label"] == "EDGE"
    # +3% planted; the stock's own baseline includes those windows, so the excess
    # over "a normal day" lands below 3%
    assert rows["x"]["mean20"] > 0.015


def test_null_panel_labelled_ordinary():
    det = {"x": _stub("x", "dated", "directional")}
    rows = br.label(br.measure(_panel(drift=0.0), det, start=100))
    assert rows["x"]["label"] == "ORDINARY"


def test_floors_give_too_few():
    det = {"x": _stub("x", "dated", "directional")}
    rows = br.label(br.measure(_panel(n_sym=10, drift=0.03), det, start=100))
    assert rows["x"]["label"] == "TOO_FEW"


def test_bearish_detector_sign_aligned():
    det = {"x": _stub("x", "dated", "directional", tone="down")}
    rows = br.label(br.measure(_panel(drift=0.03, bear=True), det, start=100))
    assert rows["x"]["label"] == "EDGE"


def test_magnitude_detector_uses_abs():
    det = {"x": _stub("x", "dated", "magnitude", tone="neutral")}
    rows = br.label(br.measure(_panel(magnitude=True), det, start=100))
    assert rows["x"]["label"] == "EDGE"
    assert abs(rows["x"]["mean20"]) > 0


def test_holm_across_detectors():
    rows = {k: {"p20": p, "n_events": 500, "n_symbols": 50, "mean20": 0.01, "thirds": [1, 1, 1]}
            for k, p in zip("abcd", [0.01, 0.04, 0.03, 0.005])}
    out = br.label(rows)
    assert [round(out[k]["p20_holm"], 4) for k in "abcd"] == [0.03, 0.06, 0.06, 0.02]
    assert out["d"]["label"] == "EDGE" and out["b"]["label"] == "ORDINARY"


def test_thirds_rule_blocks_one_period_edge():
    det = {"x": _stub("x", "dated", "directional")}
    rows = br.label(br.measure(_panel(drift=0.06, every=12, first_third_only=False), det, start=100))
    assert rows["x"]["label"] == "EDGE"
    rows = {"x": {"p20": 0.0001, "n_events": 500, "n_symbols": 50, "mean20": 0.02, "thirds": [1, -1, -1]}}
    assert br.label(rows)["x"]["label"] == "ORDINARY"


def test_inverted_when_significant_wrong_way():
    rows = {"x": {"p20": 0.0001, "n_events": 500, "n_symbols": 50, "mean20": -0.02, "thirds": [-1, -1, 1]}}
    assert br.label(rows)["x"]["label"] == "INVERTED"


def test_panel_slice_for_the_confirmatory_run():
    syms = [f"S{i}" for i in range(500)]
    assert br.panel_symbols(syms, offset=0, n=300) == syms[:300]
    assert br.panel_symbols(syms, offset=300, n=200) == syms[300:500]


def test_merge_confirmation_marks_only_edge_and_inverted():
    main = {"asOf": "2026-10-26", "detectors": {
        "a": {"label": "EDGE"}, "b": {"label": "EDGE"}, "c": {"label": "INVERTED"}, "d": {"label": "ORDINARY"}}}
    conf = {"asOf": "2026-10-26", "panel": "nifty500[300:500]", "detectors": {
        "a": {"label": "EDGE", "mean20": 0.02, "p20_holm": 0.001}, "b": {"label": "ORDINARY", "mean20": 0.01, "p20_holm": 0.2},
        "c": {"label": "INVERTED", "mean20": -0.01, "p20_holm": 0.01}, "d": {"label": "INVERTED", "mean20": -0.01, "p20_holm": 0.01}}}
    out = br.merge_confirmation(main, conf)
    d = out["detectors"]
    assert d["a"]["confirmed"] is True and d["b"]["confirmed"] is False and d["c"]["confirmed"] is True
    assert d["d"]["confirmed"] is None                 # an ORDINARY needs no confirmation
    assert d["b"]["confirm_label"] == "ORDINARY" and out["confirm_panel"] == "nifty500[300:500]"
