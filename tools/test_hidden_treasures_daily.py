"""hidden_treasures_daily — headless run stores cards + meta; scheduler registers it."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """A real sqlite file, per test, so nothing touches the desk's own DB."""
    import portfolio_db as pdb
    importlib.reload(pdb)
    monkeypatch.setattr(pdb, "DB_PATH", tmp_path / "t.db")
    pdb.init_db()
    return pdb


def _hit(sym, score):
    return {"symbol": sym, "name": sym.title(), "score": score, "inst_delta": 1.0,
            "promoter_delta": 0.0, "pledge_pct": 0.0, "quality": {"roce": 20.0}}


def test_meta_roundtrip_and_missing(db):
    assert db.get_hidden_treasures_meta("2026-01-01") == {}
    db.save_hidden_treasures_meta("2026-01-01", {"universe_kind": "both", "scanned": 7})
    assert db.get_hidden_treasures_meta("2026-01-01") == {"universe_kind": "both", "scanned": 7}


def test_run_backfills_discovers_and_stores(db, monkeypatch):
    import hidden_treasures_daily as htd
    importlib.reload(htd)
    monkeypatch.setattr(htd, "db", db)
    calls = {}
    monkeypatch.setattr(htd.scd, "backfill", lambda kind, progress=True: calls.setdefault("bf", kind) and 3)
    def _discover(kind, limit, enrich, veto_critical):
        calls["discover"] = (kind, limit, enrich, veto_critical)
        return {"hits": [_hit("AAA", 80), _hit("BBB", 70)], "scanned": 2, "cached": 2,
                "universe": 250, "vetoed": [], "veto_active": False}
    monkeypatch.setattr(htd.scd, "discover", _discover)

    res = htd.run("smallcap250", 50, run_date="2026-09-29")
    assert calls["bf"] == "smallcap250"
    # page defaults: quality overlay on, red-flag veto off
    assert calls["discover"] == ("smallcap250", 50, True, False)
    assert res["saved"] == 2
    assert [c["symbol"] for c in db.get_hidden_treasures_run("2026-09-29")] == ["AAA", "BBB"]
    meta = db.get_hidden_treasures_meta("2026-09-29")
    assert meta["universe_kind"] == "smallcap250" and meta["universe"] == 250
    assert meta["source"] == "scheduled"


def test_no_backfill_skips_warmup(db, monkeypatch):
    import hidden_treasures_daily as htd
    importlib.reload(htd)
    monkeypatch.setattr(htd, "db", db)
    monkeypatch.setattr(htd.scd, "backfill", lambda *a, **k: pytest.fail("backfill ran"))
    monkeypatch.setattr(htd.scd, "discover", lambda **k: {
        "hits": [], "scanned": 0, "cached": 0, "universe": 0, "vetoed": [], "veto_active": False})
    assert htd.run(backfill=False, run_date="2026-09-29")["saved"] == 0


def test_scheduler_registers_the_job():
    import scheduler_core as sched
    job = sched.JOBS["hidden_treasures_daily"]
    assert job.kind == "daily" and job.managed_bat
    assert "hidden_treasures_daily.py" in job.command and "--top 100" in job.command
    assert job.task_name == "TradingBramha-HiddenTreasuresDaily"
    argv = sched.register_argv(job, time="16:45")
    assert "16:45" in argv


def test_meta_falls_back_to_table_columns(db):
    db.save_hidden_treasures_run([_hit("AAA", 80)], universe_kind="microcap250",
                                 universe_size=250, run_date="2026-09-01")
    assert db.get_hidden_treasures_meta("2026-09-01") == {"universe_kind": "microcap250",
                                                          "universe": 250}
    assert db.get_hidden_treasures_meta("2026-08-01") == {}
