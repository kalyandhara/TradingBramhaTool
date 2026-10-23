"""B-182 study harness: verdict rules and edge bookkeeping (no network)."""
from __future__ import annotations

import pandas as pd

import bull_trap_study as bts


class _NoCost:
    @staticmethod
    def round_trip_pct(e, x):
        return 0.0


def _res(mean, p, windows, symbols=40, events=150):
    return {"by_h": {20: {"mean_edge_pct": mean, "p": p, "symbols": symbols,
                          "events": events}},
            "windows_pct": windows}


def test_verdict_rules_are_the_preregistered_ones():
    assert bts.verdict(_res(-0.8, 0.01, [-1, -0.5, 0.2])) == "WARNS"
    assert bts.verdict(_res(-0.8, 0.03, [-1, -0.5, -0.2])) == "NOT ESTABLISHED"   # p ≥ 0.025
    assert bts.verdict(_res(-0.8, 0.01, [-1, 0.5, 0.2])) == "NOT ESTABLISHED"     # 1 of 3 windows
    assert bts.verdict(_res(0.8, 0.01, [1, 1, 1])) == "NOT ESTABLISHED"           # wrong sign
    assert bts.verdict(_res(-0.8, 0.01, [-1, -1, -1], symbols=29)) == "TOO FEW"
    assert bts.verdict(_res(-0.8, 0.01, [-1, -1, -1], events=99)) == "TOO FEW"


def test_events_with_edges_uses_next_open_and_the_span_baseline():
    import test_bull_trap as tb
    df = tb._chart(tail=30).reset_index().rename(columns={"index": "date"})
    evs = bts.events_with_edges(df, start=0, cost=_NoCost)
    assert len(evs) == 1 and evs[0]["full"]
    o, c = df["open"].to_numpy(), df["close"].to_numpy()
    t = tb.TRAP
    raw10 = (c[t + 11] / o[t + 1] - 1) * 100
    base10 = pd.Series([(c[k + 11] / o[k + 1] - 1) * 100 for k in range(len(df) - 11)]).mean()
    assert abs(evs[0]["edge"][10] - (raw10 - base10)) < 1e-9
    assert evs[0]["edge"][60] is None                     # horizon past the data


def test_events_before_the_span_are_dropped():
    import test_bull_trap as tb
    df = tb._chart(tail=30).reset_index().rename(columns={"index": "date"})
    assert bts.events_with_edges(df, start=tb.TRAP + 1, cost=_NoCost) == []


def test_paired_difference():
    rows = [{"symbol": "A", "events": [
        {"full": True, "edge": {20: -2.0}}, {"full": False, "edge": {20: 0.0}}]},
            {"symbol": "B", "events": [
        {"full": True, "edge": {20: -1.0}}, {"full": False, "edge": {20: 1.0}}]}]
    got = bts.paired(rows)
    assert got["symbols"] == 2 and got["mean_diff_pct"] == -2.0
