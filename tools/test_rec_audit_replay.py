"""Pick replay (Recommendation Audit) — pure frame, footer, scorecard, figure."""
from __future__ import annotations

import re

import pandas as pd
import pytest

import rec_audit_replay as rp

REC = "2026-08-14"


def _bars(start: str = "2026-05-01", n: int = 150, px: float = 100.0,
          step: float = 1.0) -> pd.DataFrame:
    idx = pd.bdate_range(start, periods=n)
    close = pd.Series([px + step * i for i in range(n)], index=idx, dtype=float)
    return pd.DataFrame({"open": close - 0.5, "high": close + 1, "low": close - 1,
                         "close": close, "volume": 1000.0}, index=idx)


def _ep(**kw) -> dict:
    ep = dict(episode_id="e1", symbol="TEST", rec_date=REC, close=175.0, entry=175.0,
              stop=160.0, target=200.0, status="matured", plan_outcome="neither",
              plan_sessions=None, ret_21=5.0, excess_21=2.0, data_suspect_date=None,
              family_names="Trend/Momentum")
    ep.update(kw)
    return ep


def _frame(ep=None, bars=None, idx=None, **kw):
    return rp.replay_frame(ep or _ep(), _bars() if bars is None else bars, idx, **kw)


def test_no_hindsight_leak():
    f = _frame()
    assert f["pre"].index.max() <= pd.Timestamp(REC)
    assert f["post"].index.min() > pd.Timestamp(REC)
    assert len(f["pre"]) == 60


def test_levels_and_markers():
    f = _frame()
    post = f["post"]
    assert f["levels"]["entry_px"] == post.iloc[0]["open"]
    assert f["markers"]["entry_date"] == post.index[0]
    assert f["markers"]["window_end"] == post.index[20]
    assert f["markers"]["best_date"] == post.head(63)["high"].idxmax()
    assert f["markers"]["worst_date"] == post.head(63)["low"].idxmin()
    assert f["last_px"] == post.iloc[-1]["close"]


def test_exit_px_target_and_gap():
    post = _frame()["post"]
    o3 = post.iloc[2]["open"]
    f = _frame(_ep(plan_outcome="target_first", plan_sessions=3, target=o3 + 0.3))
    assert f["exit_px"] == pytest.approx(o3 + 0.3)
    assert f["markers"]["plan_date"] == post.index[2]
    f = _frame(_ep(plan_outcome="stop_first", plan_sessions=3, stop=o3 + 2))
    assert f["exit_px"] == pytest.approx(o3)          # gapped through the stop


def test_rvol():
    b = _bars()
    b.loc[pd.Timestamp(REC), "volume"] = 3000.0
    assert _frame(bars=b)["rvol"] == pytest.approx(300.0)


def test_footer_formats():
    post = _frame()["post"]
    o3 = post.iloc[2]["open"]
    ep = _ep(plan_outcome="target_first", plan_sessions=3, target=o3 + 0.3)
    s = rp.footer_line(ep, _frame(ep))
    assert re.fullmatch(r"₹[\d,]+\.\d\d → ₹[\d,]+\.\d\d \([+-]\d+\.\d\d%\) · Target hit day 3 · "
                        r"exited ₹[\d,]+\.\d\d \([+-]\d+\.\d\d%\)", s), s
    ep = _ep(plan_outcome="stop_first", plan_sessions=2, stop=post.iloc[1]["low"])
    assert "SL hit day 2" in rp.footer_line(ep, _frame(ep))
    ep = _ep(plan_outcome="ambiguous", plan_sessions=2)
    s = rp.footer_line(ep, _frame(ep))
    assert "SL hit day 2" in s and "same bar as target" in s
    short = _bars(n=120)                                # 44 sessions since the pick
    assert rp.footer_line(_ep(), _frame(bars=short)).endswith("Neither hit yet")
    # the audit stops looking after 63 sessions, so "yet" would be wrong
    assert rp.footer_line(_ep(), _frame()).endswith("Neither hit in 63 sessions")
    ep = _ep(stop=float("nan"), plan_outcome=None)
    assert rp.footer_line(ep, _frame(ep)).endswith("No plan")


def test_pending_pick():
    b = _bars()
    b = b[b.index <= pd.Timestamp(REC)]
    ep = _ep(status="pending", plan_outcome=None, ret_21=None)
    f = rp.replay_frame(ep, b, None)
    assert f["post"].empty and not f["pre"].empty
    s = rp.footer_line(ep, f)
    assert s.startswith("Picked at ₹") and s.endswith("not entered yet")


def test_missing_bars():
    f = rp.replay_frame(_ep(symbol="GONE"), None, None)
    assert "GONE" in f["missing"]
    assert f["pre"].empty and f["post"].empty


def test_data_suspect_cut():
    post = _frame()["post"]
    cut = post.index[9]
    f = _frame(_ep(data_suspect_date=cut.date().isoformat()))
    assert f["post"].index.max() < cut
    assert "split" in f["note"]


def test_bench_absent_and_gappy():
    assert _frame()["bench"] is None
    post = _frame()["post"]
    idx = _bars(px=1000.0, step=2.0)
    idx = idx.drop(post.index[::3])
    f = _frame(idx=idx)
    assert f["bench"].index.equals(f["post"].index)
    assert not f["bench"].isna().any()
    assert f["bench"].iloc[-1] > 0
    # the first post date is missing from the index, so its value carries forward
    # from the pick-day close — still rebased to the entry price
    assert f["bench"].iloc[0] == pytest.approx(f["levels"]["entry_px"])


def test_short_history_and_nans():
    b = _bars(start="2026-07-31", n=40)
    b["volume"] = 0.0
    ep = _ep(stop=float("nan"), target=float("nan"), plan_outcome=None,
             family_names=float("nan"), entry=float("nan"))
    f = rp.replay_frame(ep, b, None)
    assert len(f["pre"]) == 11
    assert f["rvol"] is None
    assert "nan" not in rp.footer_line(ep, f).lower()


def test_scorecard():
    eps = pd.DataFrame({
        "status": ["matured"] * 5 + ["pending"],
        "plan_outcome": ["target_first", "stop_first", "ambiguous", "neither", None, None]})
    sc = rp.scorecard(eps)
    assert sc == {"total": 6, "target": 1, "sl": 2, "neither": 1, "no_plan": 1, "pending": 1}
    assert rp.scorecard_text(sc) == ("Total 6 · Target hit 1 · SL hit 2 · Neither 1 · "
                                     "No plan 1 · Pending 1")


def _cands():
    return pd.DataFrame({
        "symbol": list("ABCDE"),
        "rec_date": ["2026-08-01", "2026-09-01", "2026-10-01", "2026-11-01", "2026-07-01"],
        "ret_21": [-20.0, -8.0, 12.0, 6.0, None],
        "excess_21": [-22.0, -9.0, 10.0, 5.0, None],
        "failure": [True, True, False, False, False],
        "review_tag": ["EVENT_GAP", "CHASED", None, None, None]})


def test_candidates_order():
    c = _cands()
    assert list(rp.replay_candidates(c, "losers", None, 21)["symbol"]) == ["A", "B"]
    assert list(rp.replay_candidates(c, "losers", "CHASED", 21)["symbol"]) == ["B"]
    assert list(rp.replay_candidates(c, "winners", None, 21)["symbol"]) == ["C", "D"]
    assert list(rp.replay_candidates(c, "all", None, 21)["symbol"]) == ["D", "C", "B", "A", "E"]


def test_bars_for_reads_cache_only(tmp_path):
    import rec_audit_job as job
    db = tmp_path / "a.db"
    conn = job.connect(db)
    conn.executemany("INSERT INTO price_bars VALUES (?,?,?,?,?,?,?)",
                     [("X.NS", "2026-08-13", 1, 2, 0.5, 1.5, 100),
                      ("X.NS", "2026-08-14", 1.5, 2.5, 1, 2, 200),
                      ("^CRSLDX", "2026-08-14", 9, 9, 9, 9, 0)])
    conn.commit()
    conn.close()
    # the cache keys bars by Yahoo symbol (X.NS); callers ask by NSE symbol (X)
    out = job.bars_for(["X", job.MARKET, "MISSING"], db)
    assert sorted(out) == sorted(["X", job.MARKET])
    assert list(out["X"]["close"]) == [1.5, 2.0]


def test_label():
    r = pd.Series({"symbol": "X", "rec_date": "2026-10-16", "ret_21": -25.36})
    assert rp.replay_label(r, 21) == "X · picked 2026-10-16 · 21d -25.4%"
    r = pd.Series({"symbol": "X", "rec_date": "2026-11-24 00:00:00", "ret_21": float("nan")})
    assert rp.replay_label(r, 21) == "X · picked 2026-11-24 · pending"


# ── Task 2: the figure ───────────────────────────────────────────────────────
def _names(fig) -> set[str]:
    return {t.name for t in fig.data if t.name}


def test_figure_no_leak():
    ep = _ep()
    fig = rp.replay_figure(_frame(ep, idx=_bars(px=1000.0)), ep)
    left = [t for t in fig.data if t.xaxis in ("x", "x3") and t.x is not None and len(t.x)]
    assert left, "pick-day column has no traces"
    for t in left:
        assert pd.to_datetime(list(t.x)).max() <= pd.Timestamp(REC), t.name


def test_figure_traces():
    post = _frame()["post"]
    ep = _ep(plan_outcome="stop_first", plan_sessions=2, stop=post.iloc[1]["low"])
    names = _names(rp.replay_figure(_frame(ep, idx=_bars(px=1000.0)), ep))
    assert {"pick day", "since pick", "NIFTY 500 (rebased)", "best", "worst", "SL hit"} <= names


def test_figure_pending():
    b = _bars()
    b = b[b.index <= pd.Timestamp(REC)]
    ep = _ep(status="pending", plan_outcome=None)
    fig = rp.replay_figure(rp.replay_frame(ep, b, None), ep)
    assert "pick day" in _names(fig) and "since pick" not in _names(fig)
    assert any("not entered yet" in (a.text or "") for a in fig.layout.annotations)


def test_far_off_level_is_not_drawn():
    # RAYMOND 2026-08-13: a stale plan entry of ₹2,460 against a ~₹600 price
    # squashed the pick-day panel flat. Such a level is listed, not drawn.
    close = float(_bars().loc[pd.Timestamp(REC), "close"])
    ep = _ep(entry=close * 4)
    f = _frame(ep)
    assert f["off_chart"] == {"entry": pytest.approx(close * 4)}
    fig = rp.replay_figure(f, ep)
    texts = [a.text or "" for a in fig.layout.annotations]
    assert not any(t.startswith("entry ₹") and f"{close * 4:,.2f}" in t for t in texts)
    assert any(t.startswith("stop ₹") for t in texts)          # near levels still drawn


def test_pending_note_uses_paper_coords():
    # In the browser a "x2 domain" note on the empty right panel fell back to data
    # coords (0.5, 0.5) on the left axes, stretching them to 1970 and to 0.
    b = _bars()
    b = b[b.index <= pd.Timestamp(REC)]
    ep = _ep(status="pending", plan_outcome=None)
    fig = rp.replay_figure(rp.replay_frame(ep, b, None), ep)
    note = next(a for a in fig.layout.annotations if "not entered yet" in (a.text or ""))
    assert (note.xref, note.yref) == ("paper", "paper")


# ── Final-review fixes ───────────────────────────────────────────────────────
def test_empty_post_that_is_not_pending_says_so():
    b = _bars()
    b = b[b.index <= pd.Timestamp(REC)]
    ep = _ep(status="no_data", plan_outcome=None)
    s = rp.footer_line(ep, rp.replay_frame(ep, b, None))
    assert "not entered yet" not in s and "no usable session since the pick" in s


def test_bench_rebases_on_index_open_like_the_audit():
    # excess_h is measured from the index's entry-day OPEN (_window_ret), so the
    # drawn NIFTY line must start from that open too, not the close.
    idx = _bars(px=1000.0, step=2.0)
    f = _frame(idx=idx)
    d0 = f["post"].index[0]
    o0, c0 = idx.at[d0, "open"], idx.at[d0, "close"]
    assert f["bench"].iloc[0] == pytest.approx(f["levels"]["entry_px"] * c0 / o0)


def test_candidates_are_keyed_by_episode_id():
    c = _cands().assign(episode_id=[f"ep{i}" for i in range(5)])
    assert list(rp.replay_candidates(c, "losers", None, 21).index) == ["ep0", "ep1"]


# ── Project 1: decision snapshot, verdict, MFE/MAE ladder ────────────────────
def _vep(**kw):
    """A matured pick: clean process, beat the market, made money."""
    base = dict(ext_vs_ema20=3.0, risk_flags="", turnover10_at_rec=5e7, stop=160.0,
                ret_21=6.0, excess_21=2.0, excess_sec_21=1.0, status="matured",
                mfe=9.0, mae=-3.0, days_to_mfe=12, rank=4, appearances=2,
                last_rec_date="2026-08-15")
    base.update(kw)
    return _ep(**base)


def test_process_checks_flag_each_breach():
    ok = rp.process_checks(_vep())
    assert all(c for c, _ in ok) and len(ok) == 4
    bad = dict(rp.process_checks(_vep(ext_vs_ema20=14.1, risk_flags="%R Exhaustion Sell",
                                      turnover10_at_rec=6e6, stop=float("nan"))))
    assert set(bad) == {False}
    labels = " | ".join(lbl for _, lbl in rp.process_checks(
        _vep(ext_vs_ema20=14.1, risk_flags="%R Exhaustion Sell")))
    assert "+14.1% above the 20 EMA" in labels and "%R Exhaustion Sell" in labels


def test_process_checks_skip_unknowns():
    # an early pick with no pick-time readings is not marked wrong for them
    checks = rp.process_checks(_vep(ext_vs_ema20=None, turnover10_at_rec=float("nan")))
    assert len(checks) == 2 and all(c for c, _ in checks)


def test_verdict_colours():
    f = _frame()
    assert rp.verdict(_vep(), f)["colour"] == "green"
    assert rp.verdict(_vep(excess_21=-8.0, ret_21=-9.0, ext_vs_ema20=14.0), f)["colour"] == "red"
    assert rp.verdict(_vep(excess_21=-8.0, ret_21=-9.0), f)["colour"] == "amber"   # process ok
    assert rp.verdict(_vep(ext_vs_ema20=14.0), f)["colour"] == "amber"            # lucky
    v = rp.verdict(_vep(status="open", ret_21=None, excess_21=None), f)
    assert v["colour"] == "grey" and v["label"] == "OPEN"


def test_verdict_items_separate_thesis_process_outcome():
    f = _frame()
    v = rp.verdict(_vep(excess_21=-8.0, ret_21=-9.0), f)
    assert [t for _, t in v["items"]][:3] == ["THESIS_WRONG", "PROCESS_CORRECT",
                                              "OUTCOME_NEGATIVE"]
    assert v["label"] == "MIXED"


def test_verdict_stop_executed_and_protected():
    post = _frame()["post"]
    o3 = post.iloc[2]["open"]
    ep = _vep(plan_outcome="stop_first", plan_sessions=3, stop=o3 + 2)
    v = rp.verdict(ep, _frame(ep))
    stop = [(ok, t, note) for ok, t, note in v["stop"]] if v.get("stop") else []
    assert stop and stop[0][1] == "STOP_EXECUTED"


def test_snapshot_fields():
    f = _frame()
    s = rp.snapshot(_vep(), f)
    assert s["entry"] == f["levels"]["entry_px"] and s["current"] == f["last_px"]
    assert s["to_date"] == pytest.approx(f["last_px"] / f["levels"]["entry_px"] * 100 - 100)
    assert (s["ret_h"], s["vs_n500"], s["vs_sector"], s["rank"]) == (6.0, 2.0, 1.0, 4)
    assert s["shortlist"] == "2 runs · last 2026-08-15"
    assert s["outcome"] == "SUCCESS" and s["colour"] == "green"


def test_excursion_insight():
    assert rp.excursion_insight(_vep(mfe=0.6, mae=-29.5)).startswith("Never got going")
    assert "target zone" in rp.excursion_insight(_vep(mfe=20.0, target=200.0, entry=175.0),
                                                 entry_px=175.0)
    assert rp.excursion_insight(_vep(mfe=None, mae=None)) == ""


def test_excursion_figure():
    f = _frame()
    names = {t.name for t in rp.excursion_figure(_vep(), f).data}
    assert {"MFE", "MAE", "now"} <= names


def test_missing_stop_before_plans_were_recorded_is_not_a_failure():
    # Plans (stop/target, plan_source) were recorded only from 2026-10-22; 411
    # older picks have none. "Not recorded" is unknown, not a flawed process.
    labels = [lbl for _, lbl in rp.process_checks(_vep(stop=None, plan_source=None))]
    assert not any("stop" in lbl.lower() for lbl in labels)
    bad = rp.process_checks(_vep(stop=None, plan_source="scanner"))
    assert (False, "No stop in the plan") in bad


# ── Project 2: open the pick in the Multi-Chart dual replay ──────────────────
def test_multichart_url_carries_the_replay():
    from urllib.parse import parse_qs, urlsplit
    post = _frame()["post"]
    o3 = post.iloc[2]["open"]
    ep = _vep(plan_outcome="stop_first", plan_sessions=3, stop=o3 + 2,
              sector="Healthcare", family_names="HM Buy (Hilega Milega)")
    url = rp.multichart_url(ep, _frame(ep))
    u = urlsplit(url)
    q = {k: v[0] for k, v in parse_qs(u.query).items()}
    assert url.startswith("http://localhost:5001/?")
    assert (q["symbol"], q["exchange"], q["tf"], q["layout"]) == ("TEST", "NSE", "1d", "replay")
    assert q["replay"] == REC and q["rank"] == "4" and q["label"] == "HM Buy (Hilega Milega)"
    assert float(q["stop"]) == pytest.approx(o3 + 2) and float(q["target"]) == 200.0
    assert q["sdate"] == post.index[2].date().isoformat() and q["skind"] == "S"
    assert q["sector"] == "^CNXPHARMA"


def test_multichart_url_drops_far_off_levels_and_missing_hits():
    from urllib.parse import parse_qs, urlsplit
    close = float(_bars().loc[pd.Timestamp(REC), "close"])
    ep = _vep(entry=close * 4, sector="Unknown sector")
    q = parse_qs(urlsplit(rp.multichart_url(ep, _frame(ep))).query)
    assert "entry" not in q and "sdate" not in q and "skind" not in q and "sector" not in q


# ── Project 3: lessons engine ────────────────────────────────────────────────
def _lep(**kw):
    """A matured pick row as the audit stores it (no bars needed)."""
    base = dict(symbol="X", status="matured", close=100.0, entry_px=100.5, stop=92.0,
                target=116.0, ret_21=8.0, excess_21=4.0, mkt_21=1.0, sec_21=2.0,
                mfe=12.0, mae=-3.0, worst_day=-2.0, ret_to_date=9.0, plan_outcome="neither",
                plan_source="scanner", ext_vs_ema20=3.0, risk_flags="",
                turnover10_at_rec=5e7, failure=False)
    base.update(kw)
    return base


def _ids(ls, ok=None):
    return {x["id"] for x in ls if ok is None or x["ok"] is ok}


def test_lessons_clean_winner_are_all_ticks():
    ls = rp.lessons(_lep())
    assert _ids(ls, False) == set()
    assert {"ENTRY_RESPECTED", "RS_HELD", "SECTOR_HELD", "MARKET_HELD"} <= _ids(ls, True)
    assert all(set(x) == {"id", "ok", "text"} for x in ls)


def test_lessons_paushak_like_failure():
    ep = _lep(entry_px=107.0, ret_21=-25.4, excess_21=-31.5, mkt_21=6.0, sec_21=-4.0,
              mfe=0.6, mae=-29.5, worst_day=-12.0, ret_to_date=-28.3,
              plan_outcome="stop_first", stop=90.0, ext_vs_ema20=14.1, failure=True)
    bad = _ids(rp.lessons(ep), False)
    assert {"ENTRY_GAPPED", "RS_COLLAPSED", "SECTOR_ROLLED_OVER", "NEVER_WORKED",
            "ONE_DAY_SHOCK", "CHASED"} <= bad
    good = _ids(rp.lessons(ep), True)
    assert "STOP_PROTECTED" in good          # exited near -13%, now -28%
    assert "MARKET_HELD" in good              # the market rose: not the market's fault


def test_lessons_stop_then_recovered_and_gave_back():
    ep = _lep(plan_outcome="stop_first", stop=92.0, ret_to_date=15.0, ret_21=-1.0,
              mfe=14.0, excess_21=-3.0)
    ls = rp.lessons(ep)
    assert "STOPPED_THEN_RECOVERED" in _ids(ls, False)
    assert "GAVE_BACK_GAIN" in _ids(ls, False)


def test_lessons_unknowns_are_skipped_and_pending_has_none():
    ls = rp.lessons(_lep(sec_21=None, mkt_21=float("nan"), stop=None, plan_source=None,
                         ext_vs_ema20=None, turnover10_at_rec=None))
    ids = _ids(ls)
    assert not ids & {"SECTOR_HELD", "SECTOR_ROLLED_OVER", "MARKET_HELD", "MARKET_FELL",
                      "CHASED", "ILLIQUID", "NO_STOP"}
    assert rp.lessons(_lep(status="pending", ret_21=None, entry_px=None)) == []


def test_lesson_table_compares_losers_with_winners():
    eps = pd.DataFrame([
        _lep(symbol="L1", failure=True, sec_21=-5.0, excess_21=-9.0, ret_21=-9.0),
        _lep(symbol="L2", failure=True, sec_21=-6.0, excess_21=-8.0, ret_21=-8.0),
        _lep(symbol="W1", sec_21=-4.0),
        _lep(symbol="W2"),
        _lep(symbol="P", status="pending", ret_21=None, entry_px=None),
    ])
    t = rp.lesson_table(eps).set_index("id")
    row = t.loc["SECTOR_ROLLED_OVER"]
    assert (row["picks"], row["pct_all"], row["pct_losers"], row["pct_winners"]) == \
        (3, 75.0, 100.0, 50.0)
    assert row["lift"] == pytest.approx(2.0)
    assert t.index[0] in ("RS_COLLAPSED", "SECTOR_ROLLED_OVER")   # sorted by share of losers
    assert "ENTRY_RESPECTED" not in t.index                      # only the ✗ lessons
    assert rp.lesson_table(eps.iloc[0:0]).empty


def test_lessons_jsonl_is_machine_readable():
    import json
    eps = pd.DataFrame([_lep(symbol="A", episode_id="e1", rec_date="2026-10-16")])
    rows = [json.loads(line) for line in rp.lessons_jsonl(eps).splitlines()]
    assert rows[0]["episode_id"] == "e1" and rows[0]["symbol"] == "A"
    assert rows[0]["lessons"] and {"id", "ok", "text"} == set(rows[0]["lessons"][0])


def test_entry_gap_threshold_and_bad_close():
    # small caps gap 2% overnight half the time; 5% is the line (desk rule)
    assert "ENTRY_RESPECTED" in _ids(rp.lessons(_lep(entry_px=104.0)), True)
    assert "ENTRY_GAPPED" in _ids(rp.lessons(_lep(entry_px=106.0)), False)
    # a stored close off by 100x is bad data, not a gap
    assert not _ids(rp.lessons(_lep(close=1.0, entry_px=100.5))) & {"ENTRY_GAPPED",
                                                                    "ENTRY_RESPECTED"}


def test_lesson_table_flags_lessons_that_define_failure():
    eps = pd.DataFrame([_lep(symbol="L", failure=True, excess_21=-9.0, ret_21=-9.0),
                        _lep(symbol="W")])
    t = rp.lesson_table(eps).set_index("id")
    assert "failure definition" in t.loc["RS_COLLAPSED", "note"]
    assert "STOPPED_THEN_RECOVERED" in rp.DEFINITIONAL      # a stop hit in the window = failure


# ── Re-score: drift, attribution, decay (spec 2026-11-26 pick-rescore §4) ────
def _rows(dates=("2026-11-26",), **cols) -> pd.DataFrame:
    n = len(dates)
    base = {"episode_id": ["e1"] * n, "session_date": list(dates),
            "sessions_since_entry": list(range(3, 3 + n)), "rating": [55] * n,
            "minervini": [5] * n, "technofunda": [4] * n, "canslim": [2] * n,
            "canslim_n": [4] * n, "ew_conf": [40] * n, "cs_near_high": [1] * n,
            "cs_volume": [1] * n, "cs_market": [1] * n, "cs_rs": [1] * n,
            "universe_rank": [146] * n, "universe_size": [500] * n,
            "universe_status": ["ranked"] * n, "original_still_firing": [0] * n,
            "rating_at_pick": [50] * n, "rating_drift": [5] * n, "downgrade": [0] * n}
    base.update({k: list(v) for k, v in cols.items()})
    return pd.DataFrame(base)


def test_drift_line_with_pick_rank():
    s = _rows(("2026-11-26", "2026-11-27"), rating=[60, 54], universe_rank=[120, 146])
    assert rp.drift_line(_ep(overall_rating=72), s, {"universe_rank": 9}) == \
        "Rating drift −18 (72 → 54) · rank #9 → #146 of 500 · tracking since 2026-11-26"


def test_drift_line_without_pick_rank():
    assert rp.drift_line(_ep(overall_rating=50), _rows(), None) == \
        "Rating drift +5 (50 → 55) · rank #146 of 500 today · tracking since 2026-11-26"


def test_drift_line_universe_states():
    out = _rows(universe_status=["not_in_universe"], universe_rank=[None], universe_size=[None])
    none = _rows(universe_status=["no_universe"], universe_rank=[None], universe_size=[None])
    assert rp.drift_line(_ep(overall_rating=50), out, None) == \
        "Rating drift +5 (50 → 55) · not in today's 500 · tracking since 2026-11-26"
    assert rp.drift_line(_ep(overall_rating=50), none, None) == \
        "Rating drift +5 (50 → 55) · rank starts with the next shortlist run · " \
        "tracking since 2026-11-26"


def test_drift_line_edge_cases():
    assert rp.drift_line(_ep(), _rows().iloc[0:0], None) == \
        "Re-score tracking starts with the next nightly run."
    assert rp.drift_line(_ep(overall_rating=None), _rows(), None) == \
        "Rating 55 (no pick-day rating) · rank #146 of 500 today · tracking since 2026-11-26"
    assert rp.drift_line(_ep(overall_rating=55), _rows(), None).startswith("Rating drift 0 (55 → 55)")


def test_what_moved_names_the_biggest_weighted_change():
    s = _rows(("2026-11-26", "2026-11-27"), minervini=[7, 4], technofunda=[5, 5],
              canslim=[3, 1], cs_rs=[1, 0], cs_volume=[1, 0])
    assert rp.what_moved(_ep(), s, None) == \
        "Minervini 7/8 → 4/8 led the drop · lost: volume, RS leader · since 2026-11-26"


def test_what_moved_from_the_pick_day_and_rises():
    pick = {"minervini": 5, "technofunda": 2, "canslim": 2, "canslim_n": 4, "ew_conf": 40,
            "cs_near_high": 0, "cs_volume": 1, "cs_market": 1, "cs_rs": 1}
    s = _rows(technofunda=[6], cs_near_high=[1])
    assert rp.what_moved(_ep(), s, pick) == \
        "TechnoFunda 2/6 → 6/6 led the rise · gained: near high"
    assert rp.what_moved(_ep(), _rows(), None) == ""        # one row, no pick-day parts


def test_what_moved_when_nothing_moved():
    assert rp.what_moved(_ep(), _rows(("2026-11-26", "2026-11-27")), None) == \
        "Rating parts unchanged · since 2026-11-26"


def test_scanners_line():
    assert rp.scanners_line(_ep(scanners="A, B, C"), _rows(original_still_firing=[2])) == \
        "2 of 3 original scanners still fire"
    assert rp.scanners_line(_ep(scanners="A"), _rows(original_still_firing=[1])) == \
        "1 of 1 original scanner still fires"
    assert rp.scanners_line(_ep(scanners="A"), _rows().iloc[0:0]) == ""


def test_multichart_url_carries_ddate():
    ep = _ep()
    assert "ddate=2026-12-03" in rp.multichart_url(ep, _frame(ep), ddate="2026-12-03")
    assert "ddate" not in rp.multichart_url(ep, _frame(ep))


def test_decay_table():
    eps = pd.DataFrame({"episode_id": ["w", "l", "open"], "ret_21": [5.0, -9.0, None],
                        "failure": [False, True, False]})
    s = pd.DataFrame({"episode_id": ["w", "w", "l", "l", "open"],
                      "sessions_since_entry": [1, 2, 1, 2, 1],
                      "rating_drift": [2, 4, -10, -20, -50]})
    t = rp.decay_table(eps, s, 21)
    assert list(t.columns) == ["sessions_since_entry", "winners_median", "losers_median",
                               "n_winners", "n_losers"]
    assert t.set_index("sessions_since_entry").loc[2].tolist() == [4.0, -20.0, 1, 1]
    assert rp.decay_table(eps, s.iloc[0:0], 21).empty


def test_decay_figure_builds_and_marks_the_downgrade():
    s = _rows(("2026-11-26", "2026-11-27"), rating=[60, 54], rating_drift=[-12, -18],
              downgrade=[0, 1])
    fig = rp.decay_figure(_ep(overall_rating=72), s)
    names = {t.name for t in fig.data}
    assert {"rating", "D", "universe rank"} <= names


def test_what_moved_weights_follow_the_rating_weights(monkeypatch):
    import rating
    s = _rows(("2026-11-26", "2026-11-27"), minervini=[7, 5], technofunda=[6, 4])
    # default weights: Minervini 2/8·35 = 8.75 > TechnoFunda 2/6·25 = 8.3
    assert rp.what_moved(_ep(), s, None).startswith("Minervini")
    monkeypatch.setattr(rating, "OVERALL_WEIGHTS",
                        {"minervini": 0.10, "technofunda": 0.50, "canslim": 0.20, "ew": 0.20})
    assert rp.what_moved(_ep(), s, None).startswith("TechnoFunda")


# ── One card per ticker (spec 2026-11-27) ────────────────────────────────────
def test_group_by_ticker_keeps_latest_and_lists_scanners():
    eps = pd.DataFrame({"episode_id": list("abcde"), "symbol": ["M", "M", "M", "X", "M"],
                        "scanner": ["Base", "VCP", "Base", "S", "Old"],
                        "rec_date": ["2026-10-13", "2026-10-13", "2026-10-13", "2026-10-13",
                                     "2026-08-14"]})
    g = rp.group_by_ticker(eps)
    m = g.set_index("symbol").loc["M"]
    assert list(g["symbol"]) == ["M", "X"] and m["episode_id"] == "a"
    assert m["scanners_all"] == "Base, VCP" and m["earlier_dates"] == "2026-08-14"
    assert m["n_picks"] == 4


def test_group_by_ticker_without_scanner_column_and_empty():
    eps = pd.DataFrame({"episode_id": ["a", "b"], "symbol": ["M", "M"],
                        "rec_date": ["2026-10-13", "2026-11-02"]})
    g = rp.group_by_ticker(eps)
    assert list(g["episode_id"]) == ["b"] and g["scanners_all"].iloc[0] == ""
    assert g["earlier_dates"].iloc[0] == "2026-10-13"
    assert rp.group_by_ticker(eps.iloc[0:0]).empty


def test_replay_candidates_one_per_ticker():
    c = pd.DataFrame({"episode_id": ["a", "b", "c"], "symbol": ["M", "M", "X"],
                      "scanner": ["Base", "VCP", "S"], "rec_date": ["2026-10-13"] * 3,
                      "ret_21": [-9.0, -9.0, -3.0], "excess_21": [-12.0, -12.0, -6.0],
                      "failure": [True, True, True], "review_tag": ["EVENT_GAP"] * 3})
    got = rp.replay_candidates(c, "losers", None, 21)
    assert list(got["symbol"]) == ["M", "X"] and got.loc["a", "scanners_all"] == "Base, VCP"


def test_replay_titles_name_the_ticker():
    ep = _ep(symbol="TEST")
    fig = rp.replay_figure(_frame(ep), ep)
    titles = [a.text for a in fig.layout.annotations]
    assert f"TEST · Pick day · {REC}" in titles
    assert any(t.startswith("TEST · Since then") for t in titles if t)


def test_multichart_url_carries_a_back_link():
    from urllib.parse import parse_qs, urlsplit
    ep = _ep()
    q = parse_qs(urlsplit(rp.multichart_url(ep, _frame(ep))).query)
    assert q["back"] == ["http://localhost:8501/?nav=page&page=Recommendation%20Audit"]


# ── Compact pop-up (2026-11-27) ──────────────────────────────────────────────
def test_numbers_line():
    s = {"entry": 33.55, "current": 13.68, "ret_h": -57.2, "to_date": -59.23,
         "vs_n500": -54.86, "vs_sector": None}
    assert rp.numbers_line(s, 21) == ("₹33.55 → ₹13.68 · 21D -57.20% · to date -59.23% · "
                                      "vs NIFTY 500 -54.86% · vs sector —")
    assert rp.numbers_line({**s, "entry": None, "current": None}, 21).startswith(
        "not entered yet · 21D")


def test_verdict_summary():
    v = {"items": [(False, "THESIS_WRONG"), (False, "PROCESS_FLAWED"), (True, "OUTCOME_POSITIVE")]}
    assert rp.verdict_summary(v, [{"ok": False}, {"ok": True}, {"ok": False}]) == \
        "Verdict ✗ thesis ✗ process ✓ outcome · 3 lessons"
    assert rp.verdict_summary({"items": [(True, "PROCESS_CORRECT")]}, []) == \
        "Verdict ✓ process"


def test_replay_figure_height_is_adjustable():
    ep = _ep()
    assert rp.replay_figure(_frame(ep), ep).layout.height == 620
    assert rp.replay_figure(_frame(ep), ep, height=420).layout.height == 420
