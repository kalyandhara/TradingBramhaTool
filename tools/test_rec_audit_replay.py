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
