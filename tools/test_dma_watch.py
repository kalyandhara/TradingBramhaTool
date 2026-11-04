"""Tests for dma_watch — B-198's close-below-200-DMA trigger on my names.

What is pinned:
  * it fires on the CROSS (yesterday at/above, today below), not on every day
    spent below, so a name that lives under its 200-DMA is not re-alerted daily;
  * too little history is "cannot tell", never a cross;
  * a cross is keyed by symbol and bar date, so re-runs the same day send nothing.
"""
import pandas as pd

import dma_watch as dw


def _closes(vals):
    return pd.Series(vals, index=pd.date_range("2026-01-01", periods=len(vals), freq="B"))


def test_cross_below_fires_once():
    s = _closes([100.0] * 200 + [101.0, 90.0])     # above, then below
    c = dw.dma_cross(s, n=200)
    assert c is not None and c["close"] == 90.0
    assert c["dma"] > 90.0 and c["prev_close"] >= c["prev_dma"]
    assert c["pct_below"] < 0


def test_already_below_is_not_a_cross():
    s = _closes([100.0] * 200 + [90.0, 89.0])
    assert dw.dma_cross(s, n=200) is None


def test_reclaiming_above_is_not_a_cross_below():
    s = _closes([100.0] * 200 + [90.0, 105.0])
    assert dw.dma_cross(s, n=200) is None


def test_too_short_history_is_none():
    assert dw.dma_cross(_closes([100.0] * 150 + [90.0]), n=200) is None


def test_new_crosses_dedupe_on_symbol_and_date():
    crosses = [{"symbol": "TRF", "date": "2026-10-30", "why": "watchlist"}]
    seen = set()
    assert len(dw.new_crosses(crosses, seen)) == 1
    assert dw.new_crosses(crosses, seen) == []


def test_email_lists_held_first():
    rows = [{"symbol": "TRF", "why": "watchlist", "date": "2026-10-30", "close": 90.0,
             "dma": 95.0, "pct_below": -5.26},
            {"symbol": "HERANBA", "why": "held", "date": "2026-10-30", "close": 200.0,
             "dma": 210.0, "pct_below": -4.76}]
    subject, body = dw.render_email(rows)
    assert "2 names" in subject and "1 held" in subject
    assert body.index("HERANBA") < body.index("TRF")
    assert "-5.3%" in body
