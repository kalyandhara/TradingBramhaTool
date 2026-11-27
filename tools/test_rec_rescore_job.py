"""rec_rescore_job — the nightly pick re-score: fetch, score, store.

Spec: docs/superpowers/specs/2026-11-26-pick-rescore-design.md §3
"""
from __future__ import annotations

from collections import Counter

import pandas as pd
import pytest

import opportunity_daily as od
import rating
import rec_rescore_job as job
import screener_pipeline as sp

IDX = pd.bdate_range("2026-11-02", "2026-11-27")
SESSION = "2026-11-27"


def _bars(idx=IDX):
    return pd.DataFrame({"open": 10.0, "high": 11.0, "low": 9.0, "close": 10.0,
                         "volume": 1e5}, index=idx)


nifty = _bars()


def _eps(*rows):
    return pd.DataFrame([{"source": "opportunity", "status": "open", "sessions": 3,
                          "overall_rating": 70, "scanners": "A, B", **r} for r in rows])


EPS = _eps({"episode_id": "e1", "symbol": "AAA", "rec_date": "2026-11-20"},
           {"episode_id": "e2", "symbol": "BBB", "rec_date": "2026-11-21"},
           {"episode_id": "e3", "symbol": "CCC", "rec_date": "2026-11-27", "status": "pending",
            "sessions": 0})


class _Fetch:
    def __init__(self, missing=()):
        self.calls = Counter()
        self.missing = set(missing)

    def __call__(self, scanner_name):          # fetch_for(scanner) -> fetch(symbol)
        def fetch(sym):
            self.calls[sym] += 1
            return None if sym in self.missing else _bars()
        return fetch


def fake_scan(symbols, fetch_for, bench):
    return {"AAA": {"scanners": ["A"], "families": ["f"], "edge_points": 1.0, "best_score": 70}}


def fake_universe(session, symbols=None):
    return pd.DataFrame({"symbol": ["AAA", "BBB"], "universe_rank": [4, 146],
                         "universe_size": [500, 500]})


@pytest.fixture(autouse=True)
def after_the_close(monkeypatch):
    """Pin the clock to the morning after the last fixture session (IST), so the
    27 Nov bar is complete regardless of when the suite runs."""
    import rec_rescore as rr
    monkeypatch.setattr(rr, "_utc_now", lambda: pd.Timestamp("2026-11-28 01:00", tz="UTC"))


@pytest.fixture(autouse=True)
def stub_rating(monkeypatch):
    monkeypatch.setattr(rating, "rating_detail", lambda df, n, w=None: {
        "rating": 52, "minervini": 4, "technofunda": 3, "canslim": 2, "canslim_n": 4,
        "ew_conf": 30, "cs_near_high": True, "cs_volume": False, "cs_market": True,
        "cs_rs": False})
    monkeypatch.setattr(od, "model_version", lambda: "vtest")


def _run(tmp_path, eps=EPS, fetch=None, **kw):
    args = dict(eps=eps, fetch_for=fetch or _Fetch(), nifty_df=nifty, scan=fake_scan,
                universe=fake_universe, db_path=tmp_path / "r.db")
    args.update(kw)
    return job.run(**args)


def test_run_writes_one_row_per_open_episode(tmp_path):
    rep = _run(tmp_path)
    got = job.load_scores(db_path=tmp_path / "r.db")
    assert rep["ok"] and rep["session"] == SESSION
    assert rep["written"] == len(got) == 3
    assert set(got["session_date"]) == {SESSION}
    a = got.set_index("episode_id").loc["e1"]
    assert (a["universe_rank"], a["universe_status"], a["rating_drift"], a["downgrade"]) == \
        (4, "ranked", -18, 1)
    assert a["original_still_firing"] == 1 and a["model_version"] == "vtest"
    assert got.set_index("episode_id").loc["e3", "universe_status"] == "not_in_universe"
    assert rep["not_in_universe"] == 1 and rep["downgrades"] == 3


def test_rerun_replaces(tmp_path):
    _run(tmp_path)
    _run(tmp_path)
    assert len(job.load_scores(db_path=tmp_path / "r.db")) == 3


def test_load_scores_filters_by_episode(tmp_path):
    _run(tmp_path)
    assert list(job.load_scores(["e2"], db_path=tmp_path / "r.db")["episode_id"]) == ["e2"]


def test_unfetchable_symbol_is_counted_not_fatal(tmp_path):
    eps = pd.concat([EPS, _eps({"episode_id": "g", "symbol": "GONE", "rec_date": "2026-11-20"})])
    rep = _run(tmp_path, eps=eps, fetch=_Fetch(missing={"GONE"}))
    assert rep["ok"] and rep["skipped"] == {"GONE": "no bars"} and rep["written"] == 3


def test_two_episodes_one_symbol_fetch_once(tmp_path):
    eps = _eps({"episode_id": "s1", "symbol": "SAME", "rec_date": "2026-11-03"},
               {"episode_id": "s2", "symbol": "SAME", "rec_date": "2026-11-20"})
    f = _Fetch()
    rep = _run(tmp_path, eps=eps, fetch=f)
    assert f.calls["SAME"] == 1 and rep["written"] == 2


def test_no_universe_for_the_session(tmp_path):
    rep = _run(tmp_path, universe=lambda s, syms=None: pd.DataFrame())
    got = job.load_scores(db_path=tmp_path / "r.db")
    assert set(got["universe_status"]) == {"no_universe"} and rep["not_in_universe"] == 0


def test_no_benchmark_writes_nothing(tmp_path):
    rep = _run(tmp_path, nifty_df=pd.DataFrame())
    assert not rep["ok"] and rep["reason"] == "no benchmark"
    assert job.load_scores(db_path=tmp_path / "r.db").empty


def test_main_exits_1_when_run_fails(monkeypatch, capsys):
    monkeypatch.setattr(job, "run", lambda **k: {"ok": False, "reason": "no benchmark"})
    assert job.main([]) == 1
    assert "FAILED: no benchmark" in capsys.readouterr().out


def test_main_prints_the_result_line(monkeypatch, capsys):
    monkeypatch.setattr(job, "run", lambda **k: {
        "ok": True, "session": SESSION, "written": 3, "skipped": {"GONE": "no bars"},
        "not_in_universe": 1, "downgrades": 2})
    assert job.main([]) == 0
    assert (f"##RESULT {SESSION} · 3 picks re-scored · 1 skipped · 1 not in today's 500 · "
            "2 downgrades") in capsys.readouterr().out


def test_load_scores_before_first_run_is_empty(tmp_path):
    got = job.load_scores(db_path=tmp_path / "none.db")
    assert got.empty and "rating_drift" in got.columns


def test_pick_day_universe(monkeypatch):
    import portfolio_db as db
    monkeypatch.setattr(db, "get_universe_ratings", lambda s, syms=None: pd.DataFrame(
        {"symbol": ["AAA"], "universe_rank": [9], "universe_size": [500]}) if s == "2026-11-20"
        else pd.DataFrame())
    assert job.pick_day_universe("AAA", "2026-11-20")["universe_rank"] == 9
    assert job.pick_day_universe("AAA", "2026-11-21") is None


def test_frame_cache_passes_the_liquidity_floor_through(monkeypatch):
    seen = []
    monkeypatch.setattr(sp, "fetch_ohlcv", lambda s, days=300, **k: seen.append(k) or _bars())
    od._FrameCache(400)("X")
    od._FetchRouter(days=400, min_turnover=0).default("Y")
    assert seen == [{}, {"min_turnover": 0}]


def test_default_universe_before_the_table_exists_is_empty(monkeypatch, tmp_path):
    import portfolio_db as db
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "fresh.db")     # no init_db: no table
    assert job._default_universe(SESSION).empty


def test_stock_bars_are_cut_at_the_benchmark_session(tmp_path, monkeypatch):
    """Nifty lagging the stocks by a day must not date rows to D-1 while scoring
    them on D's bars (and overwrite D-1's real row)."""
    seen_rating, seen_scan = [], []
    monkeypatch.setattr(rating, "rating_detail", lambda df, n, w=None: seen_rating.append(
        df.index[-1]) or {"rating": 52, "minervini": 4, "technofunda": 3, "canslim": 2,
                          "canslim_n": 4, "ew_conf": 30, "cs_near_high": True,
                          "cs_volume": False, "cs_market": True, "cs_rs": False})

    def scan(symbols, fetch_for, bench):
        seen_scan.extend(fetch_for("any")(s).index[-1] for s in symbols)
        return {}
    lagging = nifty.iloc[:-1]                                   # ends 2026-11-26
    rep = _run(tmp_path, nifty_df=lagging, scan=scan)
    cut = lagging.index[-1]
    assert rep["session"] == "2026-11-26"
    assert set(seen_rating) == {cut} and set(seen_scan) == {cut}


def test_a_pick_past_the_window_in_benchmark_sessions_is_retired(tmp_path, monkeypatch):
    """A dead symbol's own bar count freezes; age picks by benchmark sessions."""
    import rec_rescore as rr
    monkeypatch.setattr(rr, "TRACK_SESSIONS", 5)
    eps = pd.concat([EPS, _eps({"episode_id": "old", "symbol": "DEAD", "rec_date": "2026-11-03",
                                "sessions": 2})])
    rep = _run(tmp_path, eps=eps, fetch=_Fetch(missing={"DEAD"}))
    assert "DEAD" not in rep["skipped"] and rep["retired"] == 1 and rep["written"] == 3


def test_run_during_ist_market_hours_refuses(tmp_path, monkeypatch):
    import rec_rescore as rr
    monkeypatch.setattr(rr, "_utc_now", lambda: pd.Timestamp("2026-11-27 03:54", tz="UTC"))
    rep = _run(tmp_path)
    # Yahoo's daily series drops the previous session for many NSE names while the
    # market is open (CIPLA: 25 Nov then a live 27 Nov), so the job refuses to run.
    assert not rep["ok"] and "session in progress" in rep["reason"]
    assert job.load_scores(db_path=tmp_path / "r.db").empty


# ── Deferred minors (final review 2026-11-26) ────────────────────────────────
def test_a_stale_episode_list_is_flagged(tmp_path, monkeypatch):
    import rec_audit_job as raj
    monkeypatch.setattr(raj, "load_latest", lambda db_path=None, source="opportunity": {
        "episodes": EPS, "run": {"as_of": "2026-11-26"}})
    rep = _run(tmp_path, eps=None)
    assert rep["ok"] and rep["episodes_as_of"] == "2026-11-26" and rep["stale_episodes"]
    monkeypatch.setattr(raj, "load_latest", lambda db_path=None, source="opportunity": {
        "episodes": EPS, "run": {"as_of": "2026-11-27"}})
    assert not _run(tmp_path, eps=None)["stale_episodes"]


def test_skipped_counts_picks_not_symbols(tmp_path):
    eps = _eps({"episode_id": "g1", "symbol": "GONE", "rec_date": "2026-11-03"},
               {"episode_id": "g2", "symbol": "GONE", "rec_date": "2026-11-20"},
               {"episode_id": "ok", "symbol": "AAA", "rec_date": "2026-11-20"})
    rep = _run(tmp_path, eps=eps, fetch=_Fetch(missing={"GONE"}))
    assert rep["skipped"] == {"GONE": "no bars"} and rep["skipped_picks"] == 2


def test_no_data_and_suspect_picks_are_counted_not_scored(tmp_path):
    eps = pd.concat([EPS, _eps({"episode_id": "nd", "symbol": "NOD", "rec_date": "2026-11-20",
                                "status": "no_data"},
                               {"episode_id": "ds", "symbol": "SPL", "rec_date": "2026-11-20",
                                "status": "data_suspect"})])
    rep = _run(tmp_path, eps=eps)
    assert rep["written"] == 3 and rep["excluded"] == {"no_data": 1, "data_suspect": 1}


def test_result_line_reports_picks_exclusions_and_staleness(monkeypatch, capsys):
    monkeypatch.setattr(job, "run", lambda **k: {
        "ok": True, "session": SESSION, "written": 3, "skipped": {"GONE": "no bars"},
        "skipped_picks": 2, "not_in_universe": 1, "downgrades": 2, "retired": 0,
        "excluded": {"no_data": 1}, "episodes_as_of": "2026-11-26", "stale_episodes": True})
    assert job.main([]) == 0
    out = capsys.readouterr().out
    assert "· 2 skipped ·" in out and "1 excluded (no_data 1)" in out
    assert "episodes as of 2026-11-26 (audit stale)" in out


def test_load_scores_never_creates_the_db_or_table(tmp_path):
    p = tmp_path / "absent.db"
    assert job.load_scores(db_path=p).empty and not p.exists()
    import sqlite3
    sqlite3.connect(p).execute("CREATE TABLE other (x)").connection.close()
    got = job.load_scores(db_path=p)
    assert got.empty and "rating_drift" in got.columns
    tabs = {r[0] for r in sqlite3.connect(p).execute("SELECT name FROM sqlite_master")}
    assert tabs == {"other"}
