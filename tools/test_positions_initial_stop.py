"""positions.initial_stop — the stop that defines 1R, frozen at entry."""
from __future__ import annotations

import sqlite3

import pytest

import portfolio_db as pdb
import portfolio_risk as prisk


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(pdb, "DB_PATH", tmp_path / "t.db")
    pdb.init_db()
    return pdb


def test_add_position_freezes_the_opening_stop(db):
    pid = db.add_position("TCS", 100.0, 10, "2026-10-01", stop_loss=95.0)
    db.update_position(pid, stop_loss=104.0)            # trade managed: stop raised
    row = db.get_open_positions().iloc[0]
    assert row["stop_loss"] == 104.0
    assert row["initial_stop"] == 95.0


def test_initial_stop_is_not_an_editable_column(db):
    pid = db.add_position("TCS", 100.0, 10, "2026-10-01", stop_loss=95.0)
    with pytest.raises(ValueError):
        db.update_position(pid, initial_stop=90.0)


def test_legacy_rows_are_backfilled_from_stop_loss(tmp_path, monkeypatch):
    path = tmp_path / "legacy.db"
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE positions (id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL, entry_price REAL NOT NULL, quantity REAL NOT NULL,
            entry_date TEXT NOT NULL, stop_loss REAL, target REAL,
            status TEXT NOT NULL DEFAULT 'open', closed_price REAL,
            closed_date TEXT, notes TEXT);
        INSERT INTO positions (symbol, entry_price, quantity, entry_date, stop_loss)
            VALUES ('INFY', 200, 5, '2026-09-01', 190), ('ITC', 400, 5, '2026-09-01', NULL);
    """)
    con.commit(); con.close()
    monkeypatch.setattr(pdb, "DB_PATH", path)
    pdb.init_db()
    df = pdb.get_open_positions().set_index("symbol")
    assert df.loc["INFY", "initial_stop"] == 190
    assert df["initial_stop"].isna()["ITC"]             # no stop -> stays unknown


def test_initial_risk_reads_the_opening_stop_not_the_raised_one():
    # Entry 100, opened with a 95 stop, stop since raised to 98.
    r = prisk.position_risk(entry=100, stop=98, last=110, qty=10, initial_stop=95)
    assert r["initial"] == 50.0                         # (100-95) x 10, day-one risk
    assert r["open"] == 120.0                           # (110-98) x 10, at stake now


def test_without_initial_stop_the_current_stop_stands_in():
    assert prisk.position_risk(100, 90, 100, 10)["initial"] == 100.0
    assert prisk.position_risk(100, 90, 100, 10, float("nan"))["initial"] == 100.0
