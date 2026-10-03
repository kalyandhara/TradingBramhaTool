"""Tests for the PCR backfill's live-state step — B-78.

Two stores hold NIFTY's index-PCR baseline: the study cache on disk
(`cache/pcr/nifty_index_pcr.csv`) and `pcr_index_history` in the live database,
which is what the daily factor actually ranks today's reading against. On
2026-09-11 the backfill cached **543** sessions and the B-22r study measured on
them, but `--write-db` was never run — so the live table held **one** row and the
dashboard told the reader "only 0 of 60 baseline sessions stored" about a series
that was already two years deep.

These tests cover the two things that failure taught:

  * `write_db` must apply **production's** liquidity rule, not the cache's. The
    live path returns before recording an illiquid session, so the live table
    contains liquid days only — never as a filter anyone wrote, purely by
    construction. Writing the cache verbatim would put days into a baseline that
    the live path could not have produced, and a percentile is a statement about
    its sample.
  * The divergence must be **countable**, because for a month nothing counted it.

Nothing here touches the real database: `_record_pcr` and `pcr_history` are
replaced by an in-memory store.

Run:  python -m pytest tools/test_pcr_backfill.py -q
"""
from __future__ import annotations

import pandas as pd
import pytest

import pcr_backfill as pb
import sentiment_index as si


def _cache(rows) -> pd.DataFrame:
    """Cache frame in the shape `backfill` writes: (date, pcr, chg, oi, liquid)."""
    return pd.DataFrame(
        [{"reading_date": d, "pcr": p, "pcr_chg": 0.01, "total_oi": 1e7,
          "liquid": liq} for d, p, liq in rows])


@pytest.fixture
def store(monkeypatch):
    """In-memory stand-in for `pcr_index_history`; returns the written rows."""
    written: dict[str, dict] = {}

    def _rec(reading_date, rec):
        written[str(reading_date)] = dict(rec)

    def _hist(symbol="NIFTY", before=None):
        rows = [{"reading_date": d, "pcr": r["pcr"], "pcr_chg": r.get("pcr_chg")}
                for d, r in sorted(written.items())
                if before is None or d < before]
        return pd.DataFrame(rows, columns=["reading_date", "pcr", "pcr_chg"])

    monkeypatch.setattr(si, "_record_pcr", _rec)
    monkeypatch.setattr(si, "pcr_history", _hist)
    return written


# ── The liquidity rule belongs to production ─────────────────────────────────

def test_an_illiquid_cached_session_never_reaches_the_live_table(store, monkeypatch):
    """The live path RETURNS before recording an illiquid day, so the baseline
    contains liquid sessions only. The backfill must not widen it."""
    monkeypatch.setattr(pb, "_load_cache", lambda: _cache([
        ("2026-09-01", 0.90, True),
        ("2026-09-02", 1.40, False),   # below the production floor
        ("2026-09-03", 0.95, True),
    ]))
    assert pb.write_db(verbose=False) == 2
    assert sorted(store) == ["2026-09-01", "2026-09-03"]
    assert "2026-09-02" not in store


def test_an_all_liquid_cache_is_written_whole(store, monkeypatch):
    """The 2026-09-11 cache was 543/543 liquid — the bug above was latent, and a
    fix that quietly dropped good sessions would be the worse failure."""
    monkeypatch.setattr(pb, "_load_cache", lambda: _cache([
        (f"2026-09-{d:02d}", 0.9, True) for d in range(1, 11)]))
    assert pb.write_db(verbose=False) == 10
    assert len(store) == 10


def test_a_cache_without_a_liquid_column_is_still_written(store, monkeypatch):
    """Older cache files predate the column; absent must not mean illiquid."""
    df = _cache([("2026-09-01", 0.9, True)]).drop(columns=["liquid"])
    monkeypatch.setattr(pb, "_load_cache", lambda: df)
    assert pb.write_db(verbose=False) == 1


def test_an_empty_cache_writes_nothing_and_does_not_raise(store, monkeypatch):
    monkeypatch.setattr(pb, "_load_cache", lambda: pd.DataFrame())
    assert pb.write_db(verbose=False) == 0
    assert store == {}


def test_writing_twice_is_idempotent(store, monkeypatch):
    """`_record_pcr` upserts per (date, symbol), so a re-run must not duplicate."""
    monkeypatch.setattr(pb, "_load_cache", lambda: _cache([
        ("2026-09-01", 0.90, True), ("2026-09-02", 0.95, True)]))
    pb.write_db(verbose=False)
    pb.write_db(verbose=False)
    assert len(store) == 2


# ── The divergence has to be countable ───────────────────────────────────────

def test_reconcile_reports_the_gap_that_went_unnoticed_for_a_month(store, monkeypatch):
    """The real 2026-09-11 state: 543 cached, 1 live, and nothing saying so."""
    monkeypatch.setattr(pb, "_load_cache", lambda: _cache([
        (f"2026-{m:02d}-{d:02d}", 0.9, True)
        for m in (7, 8) for d in range(1, 29)]))
    store["2026-09-11"] = {"pcr": 0.77, "pcr_chg": 0.0}

    r = pb.reconcile()
    assert r["cache_sessions"] == 56
    assert r["live_sessions"] == 1
    assert r["missing_from_live"] == 55
    assert r["live_scores"] is False        # 1 row is far below MIN_PCR_HISTORY


def test_reconcile_is_clean_once_the_cache_has_been_loaded(store, monkeypatch):
    rows = [(f"2026-07-{d:02d}", 0.9, True) for d in range(1, 29)]
    monkeypatch.setattr(pb, "_load_cache", lambda: _cache(rows))
    pb.write_db(verbose=False)

    r = pb.reconcile()
    assert r["missing_from_live"] == 0
    assert r["live_sessions"] == r["cache_sessions"] == 28


def test_reconcile_counts_only_liquid_cache_rows(store, monkeypatch):
    """Otherwise the gap never closes: the live table can never hold the illiquid
    days, so counting them would report a permanent phantom shortfall."""
    monkeypatch.setattr(pb, "_load_cache", lambda: _cache([
        ("2026-09-01", 0.9, True), ("2026-09-02", 1.4, False)]))
    pb.write_db(verbose=False)
    assert pb.reconcile()["missing_from_live"] == 0


def test_reconcile_never_writes(store, monkeypatch):
    monkeypatch.setattr(pb, "_load_cache", lambda: _cache([
        ("2026-09-01", 0.9, True)]))
    pb.reconcile()
    assert store == {}


# ── Why filling the baseline was safe to do at all ───────────────────────────

def test_a_deep_baseline_still_does_not_give_the_measured_null_a_vote():
    """THE invariant that made B-78 safe, and the one to break loudly.

    Before the fill the factor read NOT_CHECKED because the history was too
    shallow. That is the RIGHT answer for the WRONG reason, and it hid the
    question: what happens when the history is deep? B-22r measured the sign
    convention as a null and `PCR_SCORES = False` is the consequence, so the
    answer must still be NOT_CHECKED — reported, never scored.

    An existing test pins the same gate exactly AT the floor. This one pins it
    far above, because the fill is what moved the history from 1 session to 544
    and a depth-dependent regression would not show up at 60.
    """
    hist = pd.DataFrame({"reading_date": [f"d{i}" for i in range(544)],
                         "pcr": [0.8 + (i % 50) / 100 for i in range(544)],
                         "pcr_chg": [0.01] * 544})
    out = si.pcr_factor(1.01, -0.01, hist)

    assert out["n_history"] == 544
    assert out["factor"] is not None        # computed and reported
    assert out["state"] == si.NOT_CHECKED   # but excluded from the composite
    assert out["score"] == 0.0
    assert "NOT SCORED" in out["reading"]
