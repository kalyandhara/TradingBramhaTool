"""model_version + the A0 stamping of stored recommendations."""
from __future__ import annotations

import importlib

import pandas as pd
import pytest

import model_version as mv


def test_fingerprint_ignores_dict_order_and_tracks_values():
    assert mv.fingerprint({"a": 1, "b": 2}) == mv.fingerprint({"b": 2, "a": 1})
    assert mv.fingerprint({"a": 1}) != mv.fingerprint({"a": 2})


def test_version_shape(monkeypatch):
    monkeypatch.setattr(mv, "git_sha", lambda repo=mv.REPO: "abc1234")
    assert mv.version({"w": 1}).startswith("abc1234/w:")
    assert mv.version() == "abc1234"


def test_git_sha_never_raises_outside_a_repo(tmp_path):
    assert mv.git_sha(tmp_path) == "nogit"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    import portfolio_db as pdb
    importlib.reload(pdb)
    monkeypatch.setattr(pdb, "DB_PATH", tmp_path / "t.db")
    pdb.init_db()
    return pdb


def test_daily_opportunities_store_version_and_plan_source(db):
    db.save_daily_opportunities([{"rank": 1, "symbol": "X", "close": 10.0,
                                  "model_version": "abc/w:1", "plan_source": "default"}],
                                run_date="2026-10-22")
    row = db.get_daily_opportunities("2026-10-22").iloc[0]
    assert row["model_version"] == "abc/w:1" and row["plan_source"] == "default"


def test_hidden_treasures_store_version(db):
    db.save_hidden_treasures_run([{"symbol": "Y", "score": 1}], run_date="2026-10-22",
                                 model_version="abc")
    import sqlite3
    conn = sqlite3.connect(db.DB_PATH)
    assert conn.execute("select model_version from hidden_treasures").fetchone()[0] == "abc"


def test_default_plan_uses_20_day_low_and_2r():
    import opportunity_daily as od
    lows = [100.0] * 30
    lows[-5] = 90.0                       # the 20-session low
    df = pd.DataFrame({"low": lows, "close": [100.0] * 30})
    entry, stop, target = od.default_plan(df)
    assert (entry, stop, target) == (100.0, 90.0, 120.0)


def test_default_plan_none_when_close_is_the_low():
    import opportunity_daily as od
    df = pd.DataFrame({"low": [100.0] * 30, "close": [100.0] * 30})
    assert od.default_plan(df) == (100.0, None, None)
