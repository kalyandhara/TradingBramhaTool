"""Tests for rs_walk.py (B-63b, RS rank walk), offline.

The whole point of this module is that the DENOMINATOR stops moving, so the
tests are about the rank being a real cross-section:

  * the same stock must rank differently against different peers, and the walk
    must be readable as one population over time;
  * a universe too small to have a percentile must say None, not rank six names
    0-100 and look precise;
  * `?` in the printed walk must mean "did not exist yet", distinguishable from
    a weak rank;
  * the benchmark must be measured at the SAME offset as the stock, or the
    index's own drift manufactures a trend in every row.
"""
import numpy as np
import pandas as pd
import pytest

import rs_walk as rw


def _series(n=400, start=100.0, end=200.0):
    """A close series with a controlled total drift."""
    idx = pd.bdate_range("2024-01-01", periods=n)
    return pd.DataFrame({"close": np.linspace(start, end, n)}, index=idx)


def _flat(n=400, level=100.0):
    idx = pd.bdate_range("2024-01-01", periods=n)
    return pd.DataFrame({"close": np.full(n, level)}, index=idx)


# ── the as-of return ──────────────────────────────────────────────────────────

def test_weighted_return_needs_enough_history():
    assert rw.weighted_return_asof(_series(n=100)) is None
    assert rw.weighted_return_asof(_series(n=400)) is not None


def test_offset_walks_the_series_back():
    """A rising series measured 30 bars ago must show a DIFFERENT return from
    the same series measured today — otherwise the walk is four copies of one
    number."""
    df = _series(n=400, start=100.0, end=300.0)
    now = rw.weighted_return_asof(df, 0)
    past = rw.weighted_return_asof(df, 30)
    assert now is not None and past is not None
    assert now != past


def test_a_frame_without_close_is_none():
    assert rw.weighted_return_asof(pd.DataFrame({"x": [1, 2, 3]})) is None
    assert rw.weighted_return_asof(None) is None


# ── the cross-section ─────────────────────────────────────────────────────────

def test_percentile_puts_best_at_100_and_worst_at_0():
    r = rw.percentile_ranks({"a": -5.0, "b": 0.0, "c": 12.0})
    assert r["c"] == 100
    assert r["a"] < r["b"] < r["c"]


def test_ties_share_a_rank_rather_than_being_ordered_arbitrarily():
    r = rw.percentile_ranks({"a": 5.0, "b": 5.0, "c": 1.0})
    assert r["a"] == r["b"]


def test_a_single_name_is_not_given_a_percentile_of_100():
    """One name is not a cross-section. 50 says 'no information', which is the
    honest reading; 100 would say 'strongest in the market'."""
    assert rw.percentile_ranks({"only": 3.0}) == {"only": 50}


def test_the_same_return_ranks_differently_against_different_peers():
    weak_peers = rw.percentile_ranks({"x": 10.0, "p1": 1.0, "p2": 2.0})
    strong_peers = rw.percentile_ranks({"x": 10.0, "p1": 50.0, "p2": 60.0})
    assert weak_peers["x"] > strong_peers["x"]


# ── the grid ──────────────────────────────────────────────────────────────────

def _universe(n=30):
    """n names with staggered drifts, so the cross-section is not degenerate."""
    return {f"S{i:02d}": _series(n=400, start=100.0, end=100.0 + i * 5.0)
            for i in range(n)}


def test_grid_ranks_every_offset_over_the_whole_universe():
    g = rw.walk_grid(hist=_universe(30))
    assert not g.get("error")
    assert set(g["columns"]) == {"t30", "t15", "t5", "t0"}
    # Every name ranked in every column — the fixed denominator is the point.
    for col in g["columns"]:
        assert g["n_ranked"][col] == 30
    strongest = g["ranks"]["S29"]
    weakest = g["ranks"]["S00"]
    assert strongest["t0"] > weakest["t0"]


def test_a_universe_too_small_for_a_percentile_returns_none(caplog):
    g = rw.walk_grid(hist=_universe(5), min_universe=20)
    for col in g["columns"]:
        assert all(r[col] is None for r in g["ranks"].values())


def test_a_short_history_name_is_ranked_only_where_it_has_bars():
    hist = _universe(25)
    # A recent listing: enough bars to rank today, not enough 30 sessions back.
    hist["IPO"] = _series(n=rw.MIN_BARS + 10)
    g = rw.walk_grid(hist=hist)
    assert g["ranks"]["IPO"]["t0"] is not None
    assert g["ranks"]["IPO"]["t30"] is None
    assert g["n_ranked"]["t30"] == 25          # the IPO is not in that denominator


def test_the_benchmark_is_measured_at_the_same_offset():
    """A rising benchmark measured only at T0 would subtract a big number from
    today and a small one from the past, inventing a downtrend in every row.
    Excess returns must therefore differ from the absolute ones by a per-column
    constant, not by a single one."""
    hist = _universe(25)
    bench = _series(n=400, start=100.0, end=400.0)
    with_b = rw.walk_grid(hist=hist, benchmark=bench)
    assert with_b["benchmark"] is True
    # Subtracting a constant per column cannot change the ORDER within a column.
    without_b = rw.walk_grid(hist=hist)
    for col in with_b["columns"]:
        a = sorted(hist, key=lambda s: with_b["ranks"][s][col])
        b = sorted(hist, key=lambda s: without_b["ranks"][s][col])
        assert a == b


def test_the_survivorship_caveat_travels_with_the_grid():
    g = rw.walk_grid(hist=_universe(25))
    assert "survivorship" in g["survivorship_note"].lower() or \
           "removed from the index" in g["survivorship_note"]


# ── the printed walk ──────────────────────────────────────────────────────────

def test_format_walk_reads_oldest_first():
    s = rw.format_walk({"t30": 18, "t15": 86, "t5": 95, "t0": 99})
    assert s == "18 → 86 → 95 → 99"


def test_question_mark_means_did_not_exist_not_weak():
    s = rw.format_walk({"t30": None, "t15": None, "t5": 1, "t0": 96})
    assert s == "? → ? → 1 → 96"
    assert "0 → 0" not in s


# ── persistence (a cache, not a journal) ──────────────────────────────────────

@pytest.fixture()
def db(tmp_path, monkeypatch):
    import importlib
    import portfolio_db as pdb
    importlib.reload(pdb)
    monkeypatch.setattr(pdb, "DB_PATH", tmp_path / "t.db")
    pdb.init_db()
    return pdb


def test_walk_round_trips_through_the_db(db):
    ranks = {"AAA": {"t30": 10, "t15": 40, "t5": 80, "t0": 95},
             "BBB": {"t30": None, "t15": None, "t5": 5, "t0": 12}}
    assert db.save_rs_walk(ranks, run_date="2026-09-09") == 2
    got = db.get_rs_walk("2026-09-09")
    assert got["AAA"]["t0"] == 95
    assert got["BBB"]["t30"] is None          # "did not exist yet" survives storage


def test_saving_the_same_day_twice_replaces_rather_than_duplicates(db):
    db.save_rs_walk({"AAA": {"t0": 1}}, run_date="2026-09-09")
    db.save_rs_walk({"AAA": {"t0": 99}}, run_date="2026-09-09")
    got = db.get_rs_walk("2026-09-09")
    assert len(got) == 1 and got["AAA"]["t0"] == 99


def test_get_without_a_date_returns_the_latest_run(db):
    db.save_rs_walk({"AAA": {"t0": 1}}, run_date="2026-09-01")
    db.save_rs_walk({"AAA": {"t0": 50}}, run_date="2026-09-09")
    got = db.get_rs_walk()
    assert got["AAA"]["t0"] == 50
    assert got["AAA"]["run_date"] == "2026-09-09"


def test_an_empty_store_returns_empty_not_a_wall_of_blanks(db):
    assert db.get_rs_walk() == {}


# ── guests: ranked against the universe without joining it ────────────────────

def test_a_non_constituent_is_ranked_against_the_universe():
    """The column was empty for every watchlist name on first ship, because a
    personal watchlist is made of exactly the stocks that are NOT in the index.
    Membership is not a prerequisite for asking how a return compares."""
    hist = _universe(30)
    guest = {"MICROCAP": _series(n=400, start=100.0, end=400.0)}   # strongest of all
    g = rw.walk_grid(hist=hist, extra_hist=guest)
    assert g["ranks"]["MICROCAP"]["t0"] is not None
    assert g["ranks"]["MICROCAP"]["t0"] >= 95
    assert g["ranks"]["MICROCAP"]["in_universe"] is False
    assert g["ranks"]["S00"]["in_universe"] is True


def test_a_guest_does_not_enter_the_denominator():
    """Otherwise the yardstick would depend on who happens to be on a watchlist,
    and two users would get different ranks for the same stock."""
    hist = _universe(30)
    plain = rw.walk_grid(hist=hist)
    with_guest = rw.walk_grid(hist=hist,
                              extra_hist={"G": _series(n=400, start=100, end=900)})
    assert with_guest["n_ranked"] == plain["n_ranked"]
    assert with_guest["n_guests"] == 1
    for sym in hist:
        assert with_guest["ranks"][sym]["t0"] == plain["ranks"][sym]["t0"]


def test_a_weak_guest_ranks_low_not_missing():
    hist = _universe(30)
    weak = {"DOG": _series(n=400, start=200.0, end=100.0)}   # falling
    g = rw.walk_grid(hist=hist, extra_hist=weak)
    assert g["ranks"]["DOG"]["t0"] == 0


def test_a_guest_already_in_the_universe_is_not_double_counted():
    hist = _universe(30)
    g = rw.walk_grid(hist=hist, extra_hist={"S05": hist["S05"]})
    assert g["n_guests"] == 0
    assert g["ranks"]["S05"]["in_universe"] is True


def test_rank_against_an_empty_distribution_says_no_information():
    assert rw.rank_against([], 5.0) == 50


def test_in_universe_survives_storage(db):
    """It did not, in the first release — and the consequence was not a blank
    but a WRONG mark: every stored row read as a guest, so the 'ranked against,
    not within' asterisk appeared on constituents too and meant nothing."""
    db.save_rs_walk({
        "MEMBER": {"t30": 50, "t15": 50, "t5": 50, "t0": 50, "in_universe": True},
        "GUEST": {"t30": 10, "t15": 10, "t5": 10, "t0": 10, "in_universe": False},
    }, run_date="2026-09-09")
    got = db.get_rs_walk("2026-09-09")
    assert got["MEMBER"]["in_universe"] is True
    assert got["GUEST"]["in_universe"] is False


def test_two_computes_on_one_day_keep_each_others_guests(db):
    """The Watchlist ranks its own names; the Scanner Hub ranks that run's hits.
    A wholesale replace meant whichever ran last silently deleted the other's
    guests and the column went blank on the page not looked at most recently —
    observed live before this was a merge."""
    db.save_rs_walk({"MEMBER": {"t0": 50, "in_universe": True},
                     "WATCHLIST_GUEST": {"t0": 12, "in_universe": False}},
                    run_date="2026-09-09")
    db.save_rs_walk({"MEMBER": {"t0": 50, "in_universe": True},
                     "HUB_GUEST": {"t0": 88, "in_universe": False}},
                    run_date="2026-09-09")
    got = db.get_rs_walk("2026-09-09")
    assert set(got) == {"MEMBER", "WATCHLIST_GUEST", "HUB_GUEST"}
    assert got["WATCHLIST_GUEST"]["t0"] == 12
    assert got["HUB_GUEST"]["t0"] == 88

