"""rec_rescore — which picks are open, and one nightly score row per pick.

Spec: docs/superpowers/specs/2026-11-26-pick-rescore-design.md §3
"""
from __future__ import annotations

import pandas as pd

import opportunity_hub as oh
import rec_rescore as rr

IDX = pd.bdate_range("2026-11-02", "2026-11-27")
S = IDX[-1]
KNOWN = {"A", "B", "C", "X", "Shallow Flip (Renko, bounded correction)"}


def _bars(idx=IDX):
    return pd.DataFrame({"open": 10.0, "high": 11.0, "low": 9.0, "close": 10.0,
                         "volume": 1e5}, index=idx)


bars = _bars()
bars_ending_day_before = _bars(IDX[:-1])


def ep(**kw):
    base = {"episode_id": "opportunity:ABC:2026-11-20", "symbol": "ABC",
            "rec_date": "2026-11-20", "overall_rating": 70, "scanners": "A, B"}
    return {**base, **kw}


def det(rating=60, **kw):
    return {"rating": rating, "minervini": 5, "technofunda": 4, "canslim": 2, "canslim_n": 4,
            "ew_conf": 40, "cs_near_high": True, "cs_volume": False, "cs_market": True,
            "cs_rs": False, **kw}


def row(*a, **k):
    return rr.build_row(*a, known=KNOWN, **k)


def test_select_open_window_and_sources():
    eps = pd.DataFrame([
        {"episode_id": "pending_today", "source": "opportunity", "status": "pending", "sessions": 0},
        {"episode_id": "open_5", "source": "opportunity", "status": "open", "sessions": 5},
        {"episode_id": "matured_63", "source": "opportunity", "status": "matured", "sessions": 63},
        {"episode_id": "matured_64", "source": "opportunity", "status": "matured", "sessions": 64},
        {"episode_id": "scanner_src", "source": "scanner", "status": "open", "sessions": 3},
        {"episode_id": "suspect", "source": "opportunity", "status": "data_suspect", "sessions": 0},
        {"episode_id": "nodata", "source": "opportunity", "status": "no_data", "sessions": 0},
    ])
    assert set(rr.select_open(eps)["episode_id"]) == {"pending_today", "open_5", "matured_63"}


def test_drift_and_downgrade_threshold():
    assert row(ep(overall_rating=70), bars, S, det(rating=55), None, None, True, "v")["downgrade"] == 1
    r = row(ep(overall_rating=70), bars, S, det(rating=56), None, None, True, "v")
    assert r["rating_drift"] == -14 and r["downgrade"] == 0
    assert r["rating_at_pick"] == 70 and r["rating"] == 56


def test_no_pick_day_rating_gives_no_drift():
    for missing in (None, float("nan")):
        r = row(ep(overall_rating=missing), bars, S, det(rating=50), None, None, True, "v")
        assert r["rating_drift"] is None and r["downgrade"] == 0 and r["rating_at_pick"] is None


def test_no_bar_tonight_or_no_rating_gives_no_row():
    assert row(ep(), bars_ending_day_before, S, det(), None, None, True, "v") is None
    assert row(ep(), bars, S, None, None, None, True, "v") is None


def test_row_keys_dates_and_sessions_since_entry():
    r = row(ep(rec_date="2026-11-20"), bars, S, det(), None, None, True, "v9")
    assert (r["episode_id"], r["symbol"], r["session_date"], r["rec_date"]) == \
        ("opportunity:ABC:2026-11-20", "ABC", "2026-11-27", "2026-11-20")
    assert r["sessions_since_entry"] == 5            # 23, 24, 25, 26, 27 Nov
    assert r["model_version"] == "v9" and r["cs_near_high"] == 1 and r["cs_volume"] == 0
    assert row(ep(rec_date="2026-11-27"), bars, S, det(), None, None, True, "v")[
        "sessions_since_entry"] == 0


def test_scanner_part_and_rank():
    r = row(ep(scanners="A, B, C"), bars, S, det(rating=60),
            {"scanners": ["B", "X"], "families": ["f1"], "edge_points": 1.0, "best_score": 80},
            {"universe_rank": 146, "universe_size": 500}, True, "v")
    assert r["original_still_firing"] == 1 and r["scanners_today"] == "B, X"
    assert r["families_today"] == "f1" and r["best_scanner_score"] == 80 and r["edge_points"] == 1.0
    assert (r["universe_rank"], r["universe_size"], r["universe_status"]) == (146, 500, "ranked")
    assert r["score_today"] == round(0.45 * 60 + 0.30 * 80 + 0.25 * oh.confluence_pct(1.0), 1)


def test_no_hit_today_scores_rating_only():
    r = row(ep(), bars, S, det(rating=60), None, None, True, "v")
    assert r["score_today"] == round(0.45 * 60, 1) and r["original_still_firing"] == 0
    assert r["scanners_today"] == "" and r["best_scanner_score"] is None


def test_a_scanner_name_with_a_comma_counts_once():
    name = "Shallow Flip (Renko, bounded correction)"
    r = row(ep(scanners=f"A, {name}"), bars, S, det(),
            {"scanners": [name], "families": [], "edge_points": 0, "best_score": 50},
            None, True, "v")
    assert r["original_still_firing"] == 1
    assert rr.scanner_set(f"A, {name}", KNOWN) == {"A", name}


def test_universe_status():
    assert row(ep(), bars, S, det(), None, None, True, "v")["universe_status"] == "not_in_universe"
    assert row(ep(), bars, S, det(), None, None, False, "v")["universe_status"] == "no_universe"
    r = row(ep(), bars, S, det(), None, None, False, "v")
    assert r["universe_rank"] is None and r["universe_size"] is None


def test_first_downgrade():
    def scores(flags):
        return pd.DataFrame({"session_date": ["2026-12-01", "2026-12-03", "2026-12-05"],
                             "downgrade": flags})
    assert rr.first_downgrade(scores([0, 1, 1])) == "2026-12-03"
    assert rr.first_downgrade(scores([0, 0, 0])) is None
    assert rr.first_downgrade(pd.DataFrame()) is None
