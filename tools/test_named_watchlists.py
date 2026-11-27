"""Named watchlists: DB layer, rail picker keys, sparkline store."""
import importlib
import json

import pytest

import watch_rail as wr


@pytest.fixture()
def db(tmp_path, monkeypatch):
    import portfolio_db as pdb
    importlib.reload(pdb)
    monkeypatch.setattr(pdb, "DB_PATH", tmp_path / "t.db")
    pdb.init_db()
    return pdb


# ── DB ────────────────────────────────────────────────────────────────────────

def test_create_list_and_add_remove(db):
    lid = db.create_watchlist("  Swing   picks ")
    assert db.get_watchlists().to_dict("records") == [{"id": lid, "name": "Swing picks", "n": 0}]
    assert db.add_watchlist_item(lid, "tcs") is True
    assert db.add_watchlist_item(lid, "TCS") is False          # no duplicate
    db.add_watchlist_item(lid, "INFY")
    assert set(db.get_watchlist_items(lid)) == {"TCS", "INFY"}
    db.remove_watchlist_item(lid, "tcs")
    assert db.get_watchlist_items(lid) == ["INFY"]


def test_names_unique_ignoring_case_and_not_empty(db):
    db.create_watchlist("Banks")
    with pytest.raises(ValueError, match="already exists"):
        db.create_watchlist("banks")
    with pytest.raises(ValueError, match="empty"):
        db.create_watchlist("   ")
    with pytest.raises(ValueError, match="characters"):
        db.create_watchlist("x" * 41)


def test_rename_refuses_a_taken_name(db):
    a, b = db.create_watchlist("A"), db.create_watchlist("B")
    db.rename_watchlist(a, "Alpha")
    with pytest.raises(ValueError):
        db.rename_watchlist(b, "ALPHA")
    assert list(db.get_watchlists()["name"]) == ["Alpha", "B"]


def test_delete_removes_members_and_leaves_default_list_alone(db):
    db.add_watchlist_symbol("RELIANCE")
    lid = db.create_watchlist("Temp")
    db.add_watchlist_item(lid, "TCS")
    db.delete_watchlist(lid)
    assert db.get_watchlists().empty
    assert db.get_watchlist_items(lid) == []
    assert list(db.get_watchlist()["symbol"]) == ["RELIANCE"]


def test_add_to_missing_list_is_a_no_op(db):
    assert db.add_watchlist_item(999, "TCS") is False
    assert db.get_watchlist_items(999) == []


# ── Rail keys / rows ──────────────────────────────────────────────────────────

def test_list_keys_round_trip():
    k = wr.list_key(7)
    assert wr.list_id_of(k) == 7 and wr.is_list_source(k)
    assert wr.list_id_of("Banks") is None and not wr.is_list_source("Banks")
    assert wr.list_id_of("__list__:x") is None
    assert wr.is_list_source(wr.WATCHLIST_KEY)


def test_picker_order_default_then_lists_then_sectors():
    opts = wr.sector_options({"TCS": "IT"}, ["A"], [(3, "Swing", 2)])
    assert [k for _, k in opts] == [wr.WATCHLIST_KEY, wr.list_key(3), "IT"]
    assert opts[1][0] == "☰ Swing (2)"


def test_named_list_frame_uses_members_and_hides_hearts():
    key = wr.list_key(1)
    f = wr.rail_frame(key, ["TCS"], {}, {"INFY": (110.0, 100.0)}, members=["INFY", "WIPRO"])
    assert list(f["Symbol"]) == ["INFY", "WIPRO"]
    rows = wr.rail_rows(f, key, names={"INFY": "Infosys Ltd"},
                        sparks={"INFY": [100.0, 105.0, 110.0]})
    assert rows[0]["name"] == "Infosys Ltd" and rows[0]["spark"] == [100.0, 105.0, 110.0]
    assert rows[1]["name"] == "" and rows[1]["spark"] == []
    assert all(r["watched"] is None for r in rows)


# ── Sparkline store ───────────────────────────────────────────────────────────

def test_refresh_sparks_merges_and_cleans(tmp_path):
    p = tmp_path / "s.json"
    ok, _ = wr.refresh_sparks(["TCS"], lambda s: {"TCS": [1, 2, 3]}, p)
    assert ok
    ok, msg = wr.refresh_sparks(
        ["INFY", "TCS", "<b>"],
        lambda s: {"INFY": [5, None, float("nan"), 6, 0], "TCS": []}, p)
    assert ok and msg == "Sparklines for 1 of 2"            # markup symbol dropped
    assert wr.read_sparks(p) == {"TCS": [1.0, 2.0, 3.0], "INFY": [5.0, 6.0]}
    json.loads(p.read_text(encoding="utf-8"))                # valid JSON, no NaN


def test_refresh_sparks_failures_keep_store(tmp_path):
    p = tmp_path / "s.json"
    wr.refresh_sparks(["TCS"], lambda s: {"TCS": [1, 2]}, p)

    def boom(_):
        raise RuntimeError("net down")
    assert wr.refresh_sparks(["TCS"], boom, p)[0] is False
    assert wr.refresh_sparks(["TCS"], lambda s: {}, p)[0] is False
    assert wr.refresh_sparks([], lambda s: {}, p)[0] is False
    assert wr.read_sparks(p) == {"TCS": [1.0, 2.0]}


def test_refresh_sparks_keeps_last_30(tmp_path):
    p = tmp_path / "s.json"
    wr.refresh_sparks(["A"], lambda s: {"A": list(range(1, 50))}, p)
    assert wr.read_sparks(p)["A"] == [float(x) for x in range(20, 50)]
