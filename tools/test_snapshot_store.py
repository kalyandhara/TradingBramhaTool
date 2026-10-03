"""snapshot_store / snapshot_registry — persistence, staleness, error rows,
pruning, and the registry's skip-and-log run loop."""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import snapshot_registry as reg   # noqa: E402
import snapshot_store as store    # noqa: E402


@pytest.fixture
def dbp(tmp_path):
    return tmp_path / "snap.db"


def test_save_and_load_roundtrip_dataframes(dbp):
    payload = {"df": pd.DataFrame({"a": [1, 2]}), "n": 3}
    meta = store.save("x", payload, params={"p": 1}, elapsed=2.5, db_path=dbp)
    assert meta.ok and meta.run_date == date.today().isoformat() and meta.nbytes > 0
    m2, back = store.load_latest("x", db_path=dbp)
    assert m2.run_at == meta.run_at and m2.params == {"p": 1}
    pd.testing.assert_frame_equal(back["df"], payload["df"])
    assert back["n"] == 3


def test_rerun_same_day_replaces_row(dbp):
    store.save("x", {"v": 1}, db_path=dbp)
    store.save("x", {"v": 2}, db_path=dbp)
    assert store.run_dates("x", db_path=dbp) == [date.today().isoformat()]
    assert store.load_latest("x", db_path=dbp)[1] == {"v": 2}


def test_error_row_keeps_last_good_payload(dbp):
    yday = datetime.now() - timedelta(days=1)
    store.save("x", {"v": "good"}, run_at=yday, db_path=dbp)
    m = store.save_error("x", "boom", db_path=dbp)
    assert not m.ok and m.error == "boom"
    ok_meta, payload = store.load_latest("x", db_path=dbp)
    assert payload == {"v": "good"} and ok_meta.run_date == yday.date().isoformat()
    # latest_meta (any status) is the failed attempt — what the badge shows
    assert store.latest_meta("x", db_path=dbp).status == "error"
    assert store.latest_meta("x", ok_only=True, db_path=dbp).ok


def test_error_after_good_run_today_annotates_not_clobbers(dbp):
    store.save("x", {"v": "morning"}, db_path=dbp)
    m = store.save_error("x", "afternoon failed", db_path=dbp)
    assert m.ok and "afternoon failed" in (m.error or "")
    assert store.load_latest("x", db_path=dbp)[1] == {"v": "morning"}


def test_prune_keeps_newest_ok_row_even_if_old(dbp):
    old = datetime.now() - timedelta(days=200)
    older = datetime.now() - timedelta(days=300)
    store.save("x", {"v": 1}, run_at=older, db_path=dbp)
    store.save("x", {"v": 2}, run_at=old, db_path=dbp)
    store.save("y", {"v": 9}, db_path=dbp)
    assert store.prune(90, db_path=dbp) == 1
    assert store.load_latest("x", db_path=dbp)[1] == {"v": 2}
    assert store.load_latest("y", db_path=dbp)[1] == {"v": 9}


def test_overview_lists_newest_per_name(dbp):
    store.save("a", 1, run_at=datetime.now() - timedelta(days=1), db_path=dbp)
    store.save("a", 2, db_path=dbp)
    store.save("b", 3, db_path=dbp)
    ov = {m.name: m for m in store.overview(db_path=dbp)}
    assert set(ov) == {"a", "b"}
    assert ov["a"].run_date == date.today().isoformat()


@pytest.mark.parametrize("run_at,now,stale", [
    # Wednesday 17:00 run, checked Thursday 09:00 → fresh (Thu close not yet)
    ("2026-09-23T17:00:00", "2026-09-24T09:00:00", False),
    # Wednesday 15:00 run, checked Wednesday 17:00 → stale (Wed close passed)
    ("2026-09-23T15:00:00", "2026-09-23T17:00:00", True),
    # Friday 17:00 run, checked Sunday → fresh (no session closed since)
    ("2026-09-25T17:00:00", "2026-09-27T12:00:00", False),
    # Thursday 17:00 run, checked Saturday → stale (Friday closed)
    ("2026-09-24T17:00:00", "2026-09-26T12:00:00", True),
])
def test_is_stale_uses_last_weekday_close(run_at, now, stale):
    m = store.SnapshotMeta(name="x", run_date=run_at[:10], run_at=run_at,
                           status="ok", params={}, elapsed=0)
    assert store.is_stale(m, now=datetime.fromisoformat(now)) is stale


def test_is_stale_none_is_stale():
    assert store.is_stale(None) is True


# ── registry ──────────────────────────────────────────────────────────────────
def test_registry_ordered_and_unique_pages():
    names = [s.name for s in reg.ordered()]
    assert names[0] == "sector_index_data"
    assert len(names) == len(set(names)) == len(reg.SNAPSHOTS)
    assert all(callable(s.produce) for s in reg.SNAPSHOTS.values())


def test_run_all_skips_failures_and_logs(dbp, monkeypatch):
    calls = []
    good = reg.SnapshotSpec("good", "G", "P", lambda: {"ok": True}, order=1)
    bad = reg.SnapshotSpec("bad", "B", "P",
                           lambda: (_ for _ in ()).throw(RuntimeError("nope")), order=2)
    monkeypatch.setattr(reg, "SNAPSHOTS", {"good": good, "bad": bad})
    metas = reg.run_all(progress=calls.append, db_path=dbp)
    assert [m.name for m in metas] == ["good", "bad"]
    assert metas[0].ok and not metas[1].ok and "nope" in metas[1].error
    assert calls == ["1/2 G", "2/2 B"]
    assert store.load_latest("good", db_path=dbp)[1] == {"ok": True}
    assert store.load_latest("bad", db_path=dbp) == (None, None)


def test_gap_volume_scan_shape_matches_page():
    idx = pd.date_range("2026-08-01", periods=25, freq="B")
    calm = pd.DataFrame({"open": 100.0, "close": 100.0, "volume": 1000}, index=idx)
    gapper = calm.copy()
    gapper.loc[gapper.index[-1], ["open", "close", "volume"]] = [105.0, 106.0, 5000]

    def fetch(sym, days=40):
        return gapper if sym == "GAP.NS" else calm

    hits = reg.gap_volume_scan(["GAP", "CALM"], fetch, gap_pct=3.0, vol_mult=2.0)
    assert [h["Symbol"] for h in hits] == ["GAP"]
    assert set(hits[0]) == {"Symbol", "Gap %", "Vol × 20d Avg", "Close"}
    assert hits[0]["Gap %"] == 5.0 and hits[0]["Vol × 20d Avg"] == 5.0


# ── empty-result guards: a fetch that yields nothing must fail the run ────────
def test_market_health_all_empty_raises(monkeypatch):
    import types
    mh = types.SimpleNamespace(fetch_indices=lambda: (pd.DataFrame(), pd.DataFrame()),
                               load_basket=lambda syms, f: {})
    sp = types.SimpleNamespace(fetch_bhavcopy_top_volume=lambda n: [],
                               fetch_ohlcv=lambda s, days=260: None)
    monkeypatch.setitem(sys.modules, "market_health", mh)
    monkeypatch.setitem(sys.modules, "screener_pipeline", sp)
    with pytest.raises(RuntimeError, match="no index or basket"):
        reg.produce_market_health()
    # a basket alone is enough to be a real run
    mh.load_basket = lambda syms, f: {"X": pd.DataFrame({"close": [1.0]})}
    assert reg.produce_market_health()["basket_frames"]


def test_finviz_all_none_raises(monkeypatch):
    import types
    blank = pd.DataFrame({"index": ["DOW"], "last": [None], "chg_pct": [None]})
    fvz = types.SimpleNamespace(fetch_index_snapshot=lambda: blank, fetch_breadth=lambda: {})
    monkeypatch.setitem(sys.modules, "finviz_sentiment", fvz)
    with pytest.raises(RuntimeError, match="finviz returned no"):
        reg.produce_finviz()
    fvz.fetch_breadth = lambda: {"adv": 1200, "dec": 800}
    assert reg.produce_finviz()["breadth"]["adv"] == 1200


# ── scheduler_core must not crash where schtasks does not exist ───────────────
def test_scheduler_status_without_schtasks(monkeypatch):
    import subprocess
    import scheduler_core as sc

    def boom(*a, **k):
        raise FileNotFoundError("schtasks")
    monkeypatch.setattr(subprocess, "run", boom)
    job = next(iter(sc.JOBS.values()))
    assert sc.status(job) == {"registered": False}
    ok, msg = sc.register(job)
    assert not ok and "not available" in msg
    assert sc.run_now(job)[0] is False and sc.remove(job)[0] is False


# ── "fetched nothing" fails; "scanned, found nothing" is a valid run ──────────
def test_gap_volume_distinguishes_no_data_from_no_hits(monkeypatch):
    import types
    calm_idx = pd.date_range("2026-08-01", periods=25, freq="B")
    calm = pd.DataFrame({"open": 100.0, "close": 100.0, "volume": 1000}, index=calm_idx)
    sp = types.SimpleNamespace(fetch_bhavcopy_top_volume=lambda n: ["A", "B"],
                               fetch_ohlcv=lambda s, days=40: None)
    monkeypatch.setitem(sys.modules, "screener_pipeline", sp)
    with pytest.raises(RuntimeError, match="no OHLCV"):
        reg.produce_gap_volume()
    sp.fetch_bhavcopy_top_volume = lambda n: []
    with pytest.raises(RuntimeError, match="no universe"):
        reg.produce_gap_volume()
    sp.fetch_bhavcopy_top_volume = lambda n: ["A", "B"]
    sp.fetch_ohlcv = lambda s, days=40: calm
    out = reg.produce_gap_volume()
    assert out["hits"] == [] and out["scanned_n"] == 2


def test_tv_scan_raises_when_unreachable(monkeypatch):
    import types
    def fetch(**kw):
        if kw.get("raise_on_error"):
            raise RuntimeError("TradingView scan unreachable: boom")
        return pd.DataFrame()
    monkeypatch.setitem(sys.modules, "tv_screener", types.SimpleNamespace(fetch_brkoutgeek=fetch))
    with pytest.raises(RuntimeError, match="unreachable"):
        reg.produce_tv_scan()


def test_tv_screener_empty_vs_raise(monkeypatch):
    import tv_screener as tvs
    def post(*a, **k):
        raise ConnectionError("down")
    monkeypatch.setattr(tvs.requests, "post", post)
    assert tvs.fetch_brkoutgeek().empty                       # page behaviour unchanged
    with pytest.raises(RuntimeError, match="unreachable"):
        tvs.fetch_brkoutgeek(raise_on_error=True)


def test_sector_money_flow_empty_rows_raises(monkeypatch):
    import types
    mf = types.SimpleNamespace(sector_grid=lambda u, n: {"error": None, "rows": pd.DataFrame()})
    monkeypatch.setitem(sys.modules, "money_flow", mf)
    with pytest.raises(RuntimeError, match="no sector had price data"):
        reg.produce_sector_money_flow()
    mf.sector_grid = lambda u, n: {"error": None, "rows": pd.DataFrame({"sector": ["IT"]})}
    assert len(reg.produce_sector_money_flow()["rows"]) == 1


def test_market_brief_all_quotes_missing_raises(monkeypatch):
    import types
    def brief(missing):
        q = [{"ticker": "^NSEI", "missing": missing}, {"ticker": "^NSEBANK", "missing": missing}]
        return {"quotes": q, "quotes_meta": {"error": None, "missing": 2 if missing else 0}}
    senti = types.SimpleNamespace(history=lambda days=1: pd.DataFrame())
    monkeypatch.setitem(sys.modules, "sentiment_index", senti)
    monkeypatch.setitem(sys.modules, "market_brief",
                        types.SimpleNamespace(build_brief=lambda **k: brief(True)))
    with pytest.raises(RuntimeError, match="every index quote is missing"):
        reg.produce_market_brief()
    monkeypatch.setitem(sys.modules, "market_brief",
                        types.SimpleNamespace(build_brief=lambda **k: brief(False)))
    assert len(reg.produce_market_brief()["quotes"]) == 2


def test_institutional_volume_no_data_vs_no_hits(monkeypatch):
    import types
    def scan(raise_on_no_data=False, **kw):
        if raise_on_no_data:
            raise RuntimeError("no universe (nifty500 constituents unavailable)")
        return pd.DataFrame()
    ivs = types.SimpleNamespace(scan=scan, RVOL_THRESHOLD=5.0, WINDOW_DAYS=5, TOP_N=10)
    monkeypatch.setitem(sys.modules, "institutional_volume_scan", ivs)
    with pytest.raises(RuntimeError, match="no universe"):
        reg.produce_institutional_volume()
    ivs.scan = lambda raise_on_no_data=False, **kw: pd.DataFrame()   # scanned, no hits
    out = reg.produce_institutional_volume()
    assert out["df"].empty and out["params"]["rvol_min"] == 5.0
    assert "institutional_volume" in reg.SNAPSHOTS


def test_scan_raise_on_no_data_flag(monkeypatch):
    import institutional_volume_scan as ivs
    monkeypatch.setattr(ivs, "_universe", lambda: [])
    assert ivs.scan().empty
    with pytest.raises(RuntimeError, match="no universe"):
        ivs.scan(raise_on_no_data=True)
    monkeypatch.setattr(ivs, "_universe", lambda: ["A"])
    monkeypatch.setattr(ivs, "_batch_download", lambda syms: {})
    with pytest.raises(RuntimeError, match="no price history"):
        ivs.scan(raise_on_no_data=True)
