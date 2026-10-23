"""snapshot_refresh under Task Scheduler's console.

The scheduled run's stdout is cp1252. A progress label with a "≥" in it raised
UnicodeEncodeError mid-run on every scheduled refresh from 2026-10-12 to 10-21
(0 ok / 7 failed), so every snapshot after step 6 went stale.

Run:  python -m pytest tools/test_snapshot_refresh.py -q
"""
from __future__ import annotations

import io
import sys

import snapshot_refresh as sr


def test_a_non_cp1252_progress_label_does_not_crash_the_run(monkeypatch):
    raw = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(raw, encoding="cp1252"))

    def fake_run_all(names, progress):
        progress("6/16 Gap ≥ 3% & volume")
        return []

    monkeypatch.setattr(sr.reg, "run_all", fake_run_all)
    monkeypatch.setattr(sr.store, "prune", lambda days: 0)

    assert sr.main(["--all"]) == 0
    sys.stdout.flush()
    assert "≥".encode("utf-8") in raw.getvalue()
