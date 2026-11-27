"""equity_snapshot exit codes and pricing.

Two things made this job "fail" 6 of 13 runs:
  * positions were priced through the SCAN fetcher, whose 10-day turnover floor
    (Rs 1 Cr) drops a thin holding like HERANBA — so nothing could be priced;
  * "nothing to price" exited 1, which the hub counts as a failure, burying
    real failures under no-ops.

Run:  python -m pytest tools/test_equity_snapshot.py -q
"""
from __future__ import annotations

import sys

import pandas as pd

import equity_snapshot as es


def test_positions_are_priced_without_the_scan_liquidity_floor(monkeypatch):
    seen = {}

    def fake_fetch(sym, days=300, min_turnover=None):
        seen[sym] = min_turnover
        return None

    monkeypatch.setattr(es.sp, "fetch_ohlcv", fake_fetch)
    es._ohlcv("HERANBA")
    assert seen == {"HERANBA": 0}


def test_nothing_priced_is_a_skip_not_a_failure(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["equity_snapshot.py", "--dry-run"])
    monkeypatch.setattr(es.db, "get_setting", lambda k, d=None: "100000")
    monkeypatch.setattr(es.db, "get_all_positions",
                        lambda: pd.DataFrame([{"symbol": "X", "status": "closed"}]))
    monkeypatch.setattr(es.ec, "snapshot_row", lambda *a, **k: None)

    assert es.main() == 0
    assert "SKIPPED" in capsys.readouterr().out
