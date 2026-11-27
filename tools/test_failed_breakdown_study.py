"""B-203 study harness: verdict rules and edge bookkeeping (no network)."""
from __future__ import annotations

import pandas as pd

import failed_breakdown_study as fbs


class _NoCost:
    @staticmethod
    def round_trip_pct(e, x):
        return 0.0


def _res(mean, p, windows, symbols=40, events=400):
    return {"by_h": {20: {"mean_edge_pct": mean, "p": p, "symbols": symbols,
                          "events": events}}, "windows_pct": windows}


def test_verdict_rules_are_the_preregistered_ones():
    assert fbs.verdict(_res(0.6, 0.01, [0.5, 0.2, -0.1]), 300) == "EDGE"
    assert fbs.verdict(_res(0.6, 0.03, [0.5, 0.2, 0.1]), 300) == "NULL"      # p >= 0.025
    assert fbs.verdict(_res(0.6, 0.01, [0.5, -0.2, -0.1]), 300) == "NULL"    # 1 of 3
    assert fbs.verdict(_res(-0.6, 0.01, [-1, -1, -1]), 300) == "NULL"        # wrong sign
    assert fbs.verdict(_res(0.6, 0.01, [1, 1, 1], events=299), 300) == "TOO FEW"
    assert fbs.verdict(_res(0.6, 0.01, [1, 1, 1], events=120), 100) == "EDGE"
    assert fbs.verdict(_res(0.6, 0.01, [1, 1, 1], symbols=29), 100) == "TOO FEW"
    assert fbs.MIN_EVENTS == {"ALL": 300, "POOL": 100} and fbs.ALPHA == 0.025


def test_events_with_edges_uses_next_open_and_the_span_baseline():
    import test_failed_breakdown as tf
    df = tf._chart(tail=30).reset_index().rename(columns={"index": "date"})
    evs, base = fbs.events_with_edges(df, 0, _NoCost)
    assert len(evs) == 1 and evs[0]["kind"] == "FB"
    o, c = df["open"].to_numpy(), df["close"].to_numpy()
    t = tf.RCL
    raw10 = (c[t + 11] / o[t + 1] - 1) * 100
    assert abs(evs[0]["edge"][10] - (raw10 - base[10])) < 1e-9
    assert evs[0]["edge"][60] is None


def test_events_before_the_span_are_dropped():
    import test_failed_breakdown as tf
    df = tf._chart(tail=30).reset_index().rename(columns={"index": "date"})
    assert fbs.events_with_edges(df, tf.RCL + 1, _NoCost)[0] == []


def test_evaluate_keeps_only_the_arm():
    rows = [{"symbol": "A", "events": [
        {"date": "2024-01-01", "kind": "FB", "pool": True, "edge": {10: 1.0, 20: 1.0, 60: 1.0}},
        {"date": "2024-02-01", "kind": "FB", "pool": False, "edge": {10: 3.0, 20: 3.0, 60: 3.0}},
        {"date": "2024-03-01", "kind": "SWEEP", "pool": None, "edge": {10: 9.0, 20: 9.0, 60: 9.0}}]}]
    r = fbs.evaluate(rows, lambda e: e["kind"] == "FB" and e["pool"], 0)
    assert r["events"] == 1 and r["by_h"][20]["mean_edge_pct"] == 1.0
