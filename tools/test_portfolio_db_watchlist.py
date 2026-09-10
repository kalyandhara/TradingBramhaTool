"""Tests for the watchlist note edit (B-63b write-back).

An in-row edit is the first thing on the Watchlist that WRITES, so the tests are
about what it must never do rather than what it does:

  * it must not reset `added_date` — the obvious implementation
    (`add_watchlist_symbol(sym, notes)`) is an INSERT OR REPLACE and would
    quietly rewrite when you started watching the name;
  * it must not create a row for a symbol that is not on the list, or a stale
    edit posted against a removed name would silently resurrect it.
"""
import importlib

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """A real sqlite file, per test, so nothing touches the desk's own DB."""
    import portfolio_db as pdb
    importlib.reload(pdb)
    monkeypatch.setattr(pdb, "DB_PATH", tmp_path / "t.db")
    pdb.init_db()
    return pdb


def test_note_edit_does_not_reset_added_date(db):
    db.add_watchlist_symbol("ABC", "first note")
    before = db.get_watchlist()
    added = before.loc[before["symbol"] == "ABC", "added_date"].iloc[0]

    changed = db.update_watchlist_notes("ABC", "edited in the table")

    after = db.get_watchlist()
    row = after[after["symbol"] == "ABC"].iloc[0]
    assert changed == 1
    assert row["notes"] == "edited in the table"
    assert row["added_date"] == added          # the whole point


def test_editing_an_absent_symbol_creates_nothing(db):
    assert db.update_watchlist_notes("NOTLISTED", "hello") == 0
    assert db.get_watchlist().empty


def test_an_empty_note_is_stored_as_empty_not_null(db):
    db.add_watchlist_symbol("ABC", "something")
    db.update_watchlist_notes("ABC", "")
    wl = db.get_watchlist()
    assert wl.loc[wl["symbol"] == "ABC", "notes"].iloc[0] == ""


def test_symbol_is_matched_case_insensitively(db):
    db.add_watchlist_symbol("abc", "n")
    assert db.update_watchlist_notes("AbC", "edited") == 1
    wl = db.get_watchlist()
    assert wl.loc[wl["symbol"] == "ABC", "notes"].iloc[0] == "edited"


def test_editing_one_row_leaves_the_others_alone(db):
    db.add_watchlist_symbol("AAA", "note a")
    db.add_watchlist_symbol("BBB", "note b")
    db.update_watchlist_notes("AAA", "changed")
    wl = db.get_watchlist().set_index("symbol")
    assert wl.loc["AAA", "notes"] == "changed"
    assert wl.loc["BBB", "notes"] == "note b"
