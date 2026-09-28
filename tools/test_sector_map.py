"""Tests for the monthly sector cache (B-64 follow-on).

The cache is what lets every screener table carry a Sector column for free, so
the tests are about the two ways a cache silently lies:

  * a MISS and a stored NULL must stay distinguishable — otherwise an unmapped
    name is re-fetched on every render forever, or worse, gets a guessed label;
  * a period must stay a period — this month's table must not be retro-labelled
    by next month's reclassification, which is the entire reason the period is
    in the key rather than the row just being overwritten.
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


def test_roundtrip_upper_cases_the_symbol(db):
    db.save_sector_map({"reliance": "Oil Gas & Consumable Fuels"})
    assert db.get_sector_map() == {"RELIANCE": "Oil Gas & Consumable Fuels"}


def test_miss_and_stored_null_are_different_facts(db):
    """A name we looked up and found nothing for must READ as looked-up."""
    db.save_sector_map({"KNOWN": "Healthcare", "NOLABEL": None})
    got = db.get_sector_map()
    assert got["NOLABEL"] is None        # stored: we looked, NSE had nothing
    assert "NEVERSEEN" not in got        # absent: we never looked


def test_save_merges_rather_than_replacing(db):
    """Two callers write this table with different symbol sets; the second must
    not delete the first's rows (the bug save_rs_walk documents)."""
    db.save_sector_map({"AAA": "Healthcare"})
    db.save_sector_map({"BBB": "Chemicals"})
    assert db.get_sector_map() == {"AAA": "Healthcare", "BBB": "Chemicals"}


def test_same_symbol_twice_in_one_period_updates_in_place(db):
    db.save_sector_map({"AAA": "Healthcare"})
    db.save_sector_map({"AAA": "Chemicals"})
    assert db.get_sector_map() == {"AAA": "Chemicals"}


def test_periods_do_not_bleed_into_each_other(db):
    """The point of keying by month: a reclassification is visible as a change
    BETWEEN periods, and neither period is rewritten by the other."""
    db.save_sector_map({"AAA": "Services"}, period="2026-08")
    db.save_sector_map({"AAA": "Capital Goods"}, period="2026-09")
    assert db.get_sector_map(period="2026-08") == {"AAA": "Services"}
    assert db.get_sector_map(period="2026-09") == {"AAA": "Capital Goods"}
    assert db.sector_map_periods() == ["2026-09", "2026-08"]


def test_universe_none_merges_every_stored_universe(db):
    """A screener hit can be any listed name, so the render path must not have
    to know which list the symbol was cached under."""
    db.save_sector_map({"AAA": "Healthcare"}, universe="nifty500")
    db.save_sector_map({"BBB": "Realty"}, universe="niftytotalmarket")
    assert db.get_sector_map() == {"AAA": "Healthcare", "BBB": "Realty"}
    assert db.get_sector_map(universe="nifty500") == {"AAA": "Healthcare"}


def test_get_can_narrow_to_symbols(db):
    db.save_sector_map({"AAA": "Healthcare", "BBB": "Realty"})
    assert db.get_sector_map(symbols=["aaa"]) == {"AAA": "Healthcare"}
    assert db.get_sector_map(symbols=[]) == {}


def test_prune_keeps_the_newest_periods_only(db):
    for p in ("2026-05", "2026-06", "2026-07", "2026-08"):
        db.save_sector_map({"AAA": "Healthcare"}, period=p)
    assert db.prune_sector_map(keep=2) == 2
    assert db.sector_map_periods() == ["2026-08", "2026-07"]


def test_prune_is_a_noop_below_the_keep_count(db):
    db.save_sector_map({"AAA": "Healthcare"}, period="2026-08")
    assert db.prune_sector_map(keep=6) == 0


def test_current_period_is_year_month():
    import datetime
    import portfolio_db as pdb
    assert pdb.current_period(datetime.date(2026, 9, 19)) == "2026-09"


def test_lookup_refills_an_empty_period_once(db, monkeypatch):
    """First render of a new month pays one fetch; the next pays none."""
    import sectors as sx
    calls = []

    def fake_symbol_map(universe="nifty500"):
        calls.append(universe)
        return {"AAA": "Healthcare"}

    monkeypatch.setattr(sx, "symbol_map", fake_symbol_map)
    assert sx.lookup() == {"AAA": "Healthcare"}
    assert sx.lookup() == {"AAA": "Healthcare"}
    assert calls == [sx.CACHE_UNIVERSE]      # fetched once, not twice


def test_lookup_returns_empty_when_the_cache_is_unreachable(db, monkeypatch):
    """A screener table renders with no sector column rather than not at all."""
    import sectors as sx
    monkeypatch.setattr(sx, "_db", lambda: (_ for _ in ()).throw(RuntimeError("no db")))
    assert sx.lookup() == {}


def test_lookup_narrows_without_inventing_a_label(db, monkeypatch):
    import sectors as sx
    monkeypatch.setattr(sx, "symbol_map", lambda universe="x": {"AAA": "Healthcare"})
    got = sx.lookup(["AAA", "NOSUCHSYM"])
    assert got == {"AAA": "Healthcare"}      # unknown is ABSENT, never guessed


# ──────────────────────────────────────────────────────────────────────────────
# The column itself. These are the tests that could not exist while the helper
# lived inside dashboard_app.py — which is the reason it does not any more.
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def sc(monkeypatch):
    """sector_column with a stubbed map, so no test touches the desk's cache."""
    import sector_column as _sc
    monkeypatch.setattr(_sc, "symbol_sectors",
                        lambda syms: {s: "Healthcare" for s in syms
                                      if str(s).upper() == "AAA"})
    return _sc


def _df(**cols):
    import pandas as pd
    return pd.DataFrame(cols)


def test_attach_puts_sector_beside_the_symbol(sc):
    out = sc.attach(_df(symbol=["AAA"], close=[1.0]), "symbol")
    assert list(out.columns) == ["symbol", "sector", "close"]
    assert out["sector"].iloc[0] == "Healthcare"


def test_attach_orders_cap_then_sector_then_the_numbers(sc):
    out = sc.attach(_df(close=[1.0], cap_bucket=["LC"], Symbol=["AAA"]), "Symbol")
    assert list(out.columns) == ["Symbol", "cap_bucket", "sector", "close"]


def test_an_unknown_symbol_is_blank_never_guessed(sc):
    out = sc.attach(_df(symbol=["AAA", "NOSUCHSYM"]), "symbol")
    assert list(out["sector"]) == ["Healthcare", ""]


def test_an_unreachable_cache_adds_no_column_at_all(monkeypatch):
    """A column of blanks would assert 'none of these has a sector'. Absent."""
    import sector_column as _sc
    monkeypatch.setattr(_sc, "symbol_sectors", lambda syms: {})
    out = _sc.attach(_df(symbol=["AAA"], close=[1.0]), "symbol")
    assert "sector" not in out.columns


def test_the_lead_reorder_survives_an_unreachable_cache(monkeypatch):
    """_hub_enrich leans on this call to place Cap; losing the sector cache must
    not also lose that placement."""
    import sector_column as _sc
    monkeypatch.setattr(_sc, "symbol_sectors", lambda syms: {})
    out = _sc.attach(_df(close=[1.0], cap_bucket=["LC"], Symbol=["AAA"]), "Symbol")
    assert list(out.columns) == ["Symbol", "cap_bucket", "close"]


def test_attach_does_not_mutate_the_caller_s_frame(sc):
    df = _df(symbol=["AAA"])
    sc.attach(df, "symbol")
    assert "sector" not in df.columns


@pytest.mark.parametrize("bad", ["nosuchcol"])
def test_attach_is_safe_on_a_frame_without_the_symbol_column(sc, bad):
    df = _df(symbol=["AAA"])
    assert sc.attach(df, bad) is df


def test_attach_is_safe_on_empty_and_none(sc):
    import pandas as pd
    assert sc.attach(None, "symbol") is None
    assert sc.attach(pd.DataFrame(), "symbol").empty


def test_the_column_id_is_the_one_in_the_shared_registry(sc):
    """One id, one label, one tooltip (B-63a) — the frame must use the registry's
    spelling or the table renders a bare 'sector' header with no explanation."""
    import columns as C
    out = sc.attach(_df(symbol=["AAA"]), "symbol")
    assert "sector" in out.columns
    assert C.resolve("sector") == "sector"
    assert C.spec("sector").label == "Sector"
    assert C.spec("sector").help          # the header carries its explanation
