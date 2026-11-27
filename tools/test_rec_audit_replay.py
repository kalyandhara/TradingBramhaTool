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
