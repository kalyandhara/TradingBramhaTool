"""UI-2 · the per-symbol note store.

One note per symbol, shared by every table that shows one. These tests pin the
three decisions that are easy to get wrong later, each of which cost something
real when it was got wrong before.
"""
import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portfolio_db as db


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    """A throwaway database, so these never touch the desk's real notes.

    Written after a live probe overwrote a real watchlist note during
    verification: the note was recoverable only because the migration is
    non-destructive. A test suite that writes to the production db would make
    that luck rather than design.
    """
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db", raising=False)
    importlib.reload(db)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db", raising=False)
    db.init_db()
    return db


def test_note_roundtrips(fresh_db):
    fresh_db.set_symbol_note("reliance", "watch the 1300 wall")
    assert fresh_db.get_symbol_notes(["RELIANCE"]) == {
        "RELIANCE": "watch the 1300 wall"}


def test_symbol_is_upper_cased_on_both_sides(fresh_db):
    """Otherwise 'reliance' and 'RELIANCE' become two notes on one name."""
    fresh_db.set_symbol_note("TiTaN", "x")
    assert fresh_db.get_symbol_notes(["titan"])["TITAN"] == "x"


def test_blank_deletes_rather_than_storing_empty(fresh_db):
    """'Has a note' should be a row's existence, not a string test — otherwise
    get_symbol_notes() with no argument grows without bound."""
    fresh_db.set_symbol_note("INFY", "something")
    fresh_db.set_symbol_note("INFY", "   ")
    assert fresh_db.get_symbol_notes(["INFY"]) == {}
    assert "INFY" not in fresh_db.get_symbol_notes()


def test_note_is_not_scoped_to_watchlist_membership(fresh_db):
    """The reason this store exists at all. `watchlist.notes` died with the row;
    a note about a name you are no longer watching is still a note."""
    fresh_db.set_symbol_note("ZOMATO", "revisit after Q3")
    assert fresh_db.get_symbol_notes(["ZOMATO"])          # never on the watchlist
    fresh_db.add_watchlist_symbol("ZOMATO")
    fresh_db.remove_watchlist_symbol("ZOMATO")
    assert fresh_db.get_symbol_notes(["ZOMATO"])["ZOMATO"] == "revisit after Q3"


def test_empty_symbol_list_does_not_query_everything(fresh_db):
    """A caller rendering an empty table must get {}, not the whole store."""
    fresh_db.set_symbol_note("A", "note")
    assert fresh_db.get_symbol_notes([]) == {}
    assert fresh_db.get_symbol_notes() == {"A": "note"}


def test_migration_is_idempotent_and_never_overwrites(fresh_db):
    """It runs on every import path that touches the db, so a second run must
    not resurrect an older note over a newer edit."""
    fresh_db.add_watchlist_symbol("TATAMOTORS", notes="old note from watchlist")
    assert fresh_db.migrate_watchlist_notes_to_symbol_notes() == 1
    fresh_db.set_symbol_note("TATAMOTORS", "edited since")
    assert fresh_db.migrate_watchlist_notes_to_symbol_notes() == 0
    assert fresh_db.get_symbol_notes(["TATAMOTORS"])["TATAMOTORS"] == "edited since"


def test_migration_leaves_the_source_column_intact(fresh_db):
    """Dropping watchlist.notes would make a rollback lossy for no gain — and it
    is what made a live mis-write recoverable during verification."""
    fresh_db.add_watchlist_symbol("SBIN", notes="keep me")
    fresh_db.migrate_watchlist_notes_to_symbol_notes()
    row = fresh_db.get_connection().execute(
        "SELECT notes FROM watchlist WHERE symbol = 'SBIN'").fetchone()
    assert row[0] == "keep me"
