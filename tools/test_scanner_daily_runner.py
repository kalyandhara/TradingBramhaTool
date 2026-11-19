"""Tests for the nightly runner's hand-off to the Scanner Hub cache.

Until 2026-10-29 the nightly run wrote only cache/scanner_daily_<ts>.json, which
nothing read, so the Hub's "Cached results" stayed weeks old while fresh hits
sat on disk. What is pinned:
  * every scanner that RAN is published under its own name and the run date;
  * a scanner that ERRORED is not published, so it cannot wipe a manual run
    saved earlier the same day (save_scanner_run replaces per name and date);
  * cards survive values json cannot encode natively (Timestamps, numpy).
"""
import datetime as dt

import numpy as np
import pandas as pd

import scanner_daily_runner as r


def test_publish_saves_ran_scanners_and_skips_failed(monkeypatch):
    saved = {}
    monkeypatch.setattr(r.db, "save_scanner_run",
                        lambda name, cards, run_date=None: saved.setdefault(name, (cards, run_date)))
    payload = {"Darvas Box": [{"symbol": "TRF", "score": 0.7}],
               "Episodic Pivot": [],
               "Broken One": []}
    n = r.publish_to_hub(payload, failed={"Broken One"}, run_date="2026-10-29")
    assert n == 2
    assert set(saved) == {"Darvas Box", "Episodic Pivot"}
    assert saved["Darvas Box"] == ([{"symbol": "TRF", "score": 0.7}], "2026-10-29")


def test_publish_makes_cards_json_safe(monkeypatch):
    saved = {}
    monkeypatch.setattr(r.db, "save_scanner_run",
                        lambda name, cards, run_date=None: saved.setdefault(name, cards))
    r.publish_to_hub({"X": [{"symbol": "A", "when": pd.Timestamp("2026-10-28"),
                             "score": np.float64(1.5), "d": dt.date(2026, 10, 28)}]},
                     failed=set(), run_date="2026-10-29")
    card = saved["X"][0]
    assert card["score"] == 1.5
    assert card["when"].startswith("2026-10-28")


def test_run_records_failed_scanners(monkeypatch):
    class _Router:
        misses = 0
        def __init__(self, days): pass
        def __call__(self, name): return None
    monkeypatch.setattr(r, "_FetchRouter", _Router)
    monkeypatch.setattr(r.sp, "fetch_nifty50", lambda days: None)
    monkeypatch.setitem(r.sc.SCANNERS, "__ok", object())
    monkeypatch.setitem(r.sc.SCANNERS, "__bad", object())

    def fake_run(name, universe, fetch, benchmark_df=None):
        if name == "__bad":
            raise RuntimeError("boom")
        return [{"symbol": "A"}]
    monkeypatch.setattr(r.sc, "run_scanner", fake_run)
    failed: set[str] = set()
    out = r.run(["__ok", "__bad"], ["A"], failed=failed)
    assert out == {"__ok": [{"symbol": "A"}], "__bad": []}
    assert failed == {"__bad"}
