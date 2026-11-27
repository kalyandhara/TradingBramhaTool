"""Universe ratings: the shortlist job rates its whole 500-name universe nightly
so the pick re-score has a stable pool to rank against.

Spec: docs/superpowers/specs/2026-11-26-pick-rescore-design.md §2
"""
from __future__ import annotations

import pandas as pd
import pytest

import opportunity_daily as od
import opportunity_hub as oh
import portfolio_db as db
import rating
import screener_pipeline as sp
from test_rating_detail import _frame

RATINGS = {"A": 80, "B": 60, "C": 80, "D": None}


def _bars(sym):
    """Stand-in bars: a one-row frame carrying the rating the stub returns."""
    return pd.DataFrame({"r": [RATINGS[sym]]})


def _detail(r):
    if isinstance(r, pd.DataFrame):
        r = r["r"].iloc[0]
    return None if r is None or pd.isna(r) else {
        "rating": r, "minervini": 6, "technofunda": 4, "canslim": 3, "canslim_n": 4,
        "ew_conf": 50, "cs_near_high": True, "cs_volume": False, "cs_market": True,
        "cs_rs": True}


@pytest.fixture
def tmp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "tb.db")
    db.init_db()
    return tmp_path / "tb.db"


@pytest.fixture
def stub_rating(monkeypatch):
    monkeypatch.setattr(rating, "rating_detail", lambda df, nifty, w=None: _detail(df))


def test_rank_is_descending_with_shared_ties(stub_rating):
    rows = od.rate_universe(["A", "B", "C", "D"], _bars, None, "v1")
    got = {r["symbol"]: (r["universe_rank"], r["universe_size"]) for r in rows}
    assert got == {"A": (1, 3), "C": (1, 3), "B": (3, 3)}
    assert all(r["model_version"] == "v1" for r in rows)


def test_a_name_without_bars_is_left_out(stub_rating):
    rows = od.rate_universe(["A", "GONE"], lambda s: None if s == "GONE" else _bars(s),
                            None, "v1")
    assert [r["symbol"] for r in rows] == ["A"]


def _rows(*syms):
    return [{**_detail(70), "symbol": s, "universe_rank": i + 1, "universe_size": len(syms),
             "model_version": "v1"} for i, s in enumerate(syms)]


def test_save_replaces_the_session(tmp_db):
    db.save_universe_ratings(_rows("A", "B"), "2026-11-26", "2026-11-26")
    db.save_universe_ratings(_rows("C"), "2026-11-26", "2026-11-26")
    db.save_universe_ratings(_rows("A"), "2026-11-25", "2026-11-25")
    got = db.get_universe_ratings("2026-11-26")
    assert list(got["symbol"]) == ["C"]
    assert bool(got["cs_near_high"].iloc[0]) is True
    assert list(db.get_universe_ratings("2026-11-25", ["A", "Z"])["symbol"]) == ["A"]
    assert db.get_universe_ratings("2026-01-01").empty


# ── run() wiring: every network call stubbed ─────────────────────────────────
@pytest.fixture
def stub_run(monkeypatch):
    saved = {}
    frame = _frame(n=300)
    monkeypatch.setattr(sp, "fetch_bhavcopy_top_volume", lambda n: ["A", "B"])
    monkeypatch.setattr(sp, "fetch_ohlcv", lambda s, days=400, **k: frame)
    monkeypatch.setattr(sp, "fetch_nifty50", lambda days=400: frame)
    monkeypatch.setattr(oh, "build_constituent_table", lambda u, f, max_workers=4: pd.DataFrame(
        {"symbol": ["A", "B"], "sector": ["S", "S"], "industry": ["I", "I"],
         "momentum": [1.0, 2.0]}))
    monkeypatch.setattr(oh, "rank_groups", lambda t, col, min_constituents=1: pd.DataFrame(
        {col: [t[col].iloc[0]], "avg_momentum": [1.0]}))
    monkeypatch.setattr(oh, "stocks_in_groups", lambda t, col, groups: ["A"])
    monkeypatch.setattr(oh, "run_scanner_pipeline", lambda *a, **k: {"A": {
        "best_score": 90, "edge_points": 2.0, "best_card": {}, "scanners": ["X"],
        "families": ["f"], "risk_flags": []}})
    monkeypatch.setattr(rating, "overall_rating", lambda df, n: (90, {}))
    monkeypatch.setattr(db, "save_daily_opportunities",
                        lambda rows, run_date=None: saved.setdefault("shortlist", rows))
    monkeypatch.setattr(db, "save_opportunity_cards",
                        lambda cards, run_date=None: saved.setdefault("cards", cards))
    monkeypatch.setattr(db, "save_universe_ratings",
                        lambda rows, session_date, run_date: saved.setdefault(
                            "universe", (rows, session_date)))
    saved["session"] = frame.index[-1].strftime("%Y-%m-%d")
    return saved


def test_run_stores_universe_ratings_by_session_date(stub_run, stub_rating, monkeypatch):
    monkeypatch.setattr(rating, "rating_detail", lambda df, nifty, w=None: _detail(70))
    res = od.run(universe_size=2, top_n=10, save=True, run_date="2026-11-26")
    rows, session = stub_run["universe"]
    assert res["ok"] and stub_run["shortlist"]
    assert session == stub_run["session"] and len(rows) == 2
    assert res["universe_ratings"] == {"ok": True, "n": 2, "session_date": session}


def test_a_rating_failure_never_breaks_the_shortlist(stub_run, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(od, "rate_universe", boom)
    res = od.run(universe_size=2, top_n=10, save=True, run_date="2026-11-26")
    assert res["ok"] and stub_run["shortlist"]
    assert res["universe_ratings"] == {"ok": False, "error": "boom"}
    assert "universe" not in stub_run


def test_universe_bars_are_cut_at_the_benchmark_session(monkeypatch):
    seen = []
    monkeypatch.setattr(rating, "rating_detail",
                        lambda df, nifty, w=None: seen.append(df.index[-1]) or _detail(70))
    bars = _frame(n=300)
    nifty_lag = bars.iloc[:-1]
    od.rate_universe(["A"], lambda s: bars, nifty_lag, "v1")
    assert seen == [nifty_lag.index[-1]]
