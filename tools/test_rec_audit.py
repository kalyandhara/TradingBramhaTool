"""rec_audit — episodes, outcomes, post-mortem tags, aggregates (synthetic bars).

Run:  python -m pytest tools/test_rec_audit.py -q
"""
from __future__ import annotations

import pandas as pd
import pytest

import rec_audit as ra

SESS = pd.bdate_range("2026-08-03", periods=120)        # Mon–Fri sessions


def _bars(closes, *, opens=None, lows=None, highs=None, start=SESS[0], vol=1e6):
    idx = pd.bdate_range(start, periods=len(closes))
    c = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame({"open": opens if opens is not None else c.values,
                         "high": highs if highs is not None else c.values * 1.005,
                         "low": lows if lows is not None else c.values * 0.995,
                         "close": c.values, "volume": vol}, index=idx)


def _ep(symbol="A", rec="2026-08-03", **kw):
    d = {"episode_id": f"opportunity:{symbol}:{rec}", "symbol": symbol,
         "rec_date": pd.Timestamp(rec), "stop": None, "target": None, "risk_flags": ""}
    d.update(kw)
    return d


# ── Episodes ─────────────────────────────────────────────────────────────────

def test_weekend_run_maps_to_friday():
    assert ra.rec_session("2026-08-08", SESS) == pd.Timestamp("2026-08-07")


def test_weekend_resave_and_relisting_are_one_episode():
    recs = pd.DataFrame({"run_date": pd.to_datetime(
        ["2026-08-07", "2026-08-08", "2026-08-09", "2026-08-12"]),
        "symbol": ["A"] * 4, "rank": [3, 3, 3, 1]})
    ep = ra.build_episodes(recs, SESS)
    assert len(ep) == 1
    assert ep.loc[0, "appearances"] == 2                  # Fri + Wed; Sat/Sun folded in
    assert ep.loc[0, "rank"] == 3                         # first appearance's attributes
    assert ep.loc[0, "last_rec_date"] == pd.Timestamp("2026-08-12")


def test_a_gap_beyond_merge_window_starts_a_new_episode():
    recs = pd.DataFrame({"run_date": pd.to_datetime(["2026-08-03", "2026-08-31"]),
                         "symbol": ["A", "A"]})
    assert len(ra.build_episodes(recs, SESS)) == 2


# ── Outcome ──────────────────────────────────────────────────────────────────

def test_entry_is_next_session_open_and_excess_uses_same_dates():
    closes = [100.0] + [110.0] * 30
    opens = [100.0, 104.0] + [110.0] * 29
    bars = _bars(closes, opens=opens)
    mkt = _bars([50.0] + [52.0] * 30, opens=[50.0, 50.0] + [52.0] * 29)
    o = ra.episode_outcome(_ep(), bars, mkt)
    assert o["entry_date"] == "2026-08-04" and o["entry_px"] == 104.0
    assert o["ret_5"] == pytest.approx((110 / 104 - 1) * 100)
    assert o["mkt_5"] == pytest.approx((52 / 50 - 1) * 100)
    assert o["excess_5"] == pytest.approx(o["ret_5"] - o["mkt_5"])
    assert o["status"] == "matured"


def test_unmatured_horizons_are_absent_not_zero():
    o = ra.episode_outcome(_ep(), _bars([100.0] * 8), _bars([50.0] * 8))
    assert "ret_21" not in o and o["status"] == "open" and "ret_5" in o


def test_no_bars_after_rec_is_no_data_and_counts_as_failure():
    # The market traded on after the pick; the stock did not (delisted/suspended).
    o = ra.episode_outcome(_ep(rec="2026-08-20"), _bars([100.0] * 5), _bars([50.0] * 40))
    assert o["status"] == "no_data"
    assert ra.is_failure(o) and ra.postmortem_tags(_ep(), o) == ["NO_DATA"]


def test_a_pick_made_on_the_audit_date_is_pending_not_missing():
    # KMEW, recommended 2026-10-21 and audited as of 2026-10-21, was first
    # scored NO_DATA and counted as a failure.
    bars, mkt = _bars([100.0] * 10), _bars([50.0] * 10)
    o = ra.episode_outcome(_ep(rec=str(bars.index[-1].date())), bars, mkt,
                           as_of=bars.index[-1].date())
    assert o["status"] == "pending" and not ra.is_failure(o)


def test_mfe_mae():
    closes = [100.0, 100.0, 120.0, 90.0] + [100.0] * 20
    o = ra.episode_outcome(_ep(), _bars(closes), _bars([1.0] * 24))
    assert o["mfe"] == pytest.approx(120 * 1.005 - 100)
    assert o["mae"] == pytest.approx(90 * 0.995 - 100)
    assert o["days_to_mfe"] == 2


def test_plan_outcome_target_stop_and_ambiguous():
    b = _bars([100.0] * 5, lows=[99, 99, 89, 99, 99], highs=[101, 101, 101, 101, 121])
    assert ra.plan_outcome(b, 90, 120) == ("stop_first", 3)
    b2 = _bars([100.0] * 3, lows=[99, 89, 99], highs=[101, 121, 101])
    assert ra.plan_outcome(b2, 90, 120) == ("ambiguous", 2)
    assert ra.plan_outcome(b2, None, 120) == (None, None)


# ── Post-mortem ──────────────────────────────────────────────────────────────

def test_market_drag_when_benchmark_fell_and_pick_kept_pace():
    o = {"status": "matured", "ret_21": -8.0, "mkt_21": -7.0, "excess_21": -1.0}
    assert ra.is_failure(o)
    assert ra.primary_tag(ra.postmortem_tags(_ep(), o)) == "MARKET_DRAG"


def test_stock_specific_when_nothing_explains_it():
    o = {"status": "matured", "ret_21": -9.0, "mkt_21": 1.0, "excess_21": -10.0}
    assert ra.primary_tag(ra.postmortem_tags(_ep(), o)) == ra.UNEXPLAINED


def test_tags_are_not_exclusive_and_follow_precedence():
    o = {"status": "matured", "ret_21": -20.0, "mkt_21": 0.0, "excess_21": -20.0,
         "worst_day": -12.0, "ext_vs_ema20": 15.0, "turnover10_at_rec": 5e6}
    tags = ra.postmortem_tags(_ep(risk_flags="Downside Risk"), o)
    assert tags == ["EVENT_GAP", "CHASED", "WARNING_IGNORED", "ILLIQUID"]


def test_early_stop_is_setup_failed():
    o = {"status": "matured", "ret_21": -3.0, "excess_21": -1.0, "mkt_21": 0.0,
         "plan_outcome": "stop_first", "plan_sessions": 2}
    assert ra.is_failure(o) and "SETUP_FAILED" in ra.postmortem_tags(_ep(), o)


def test_a_small_loss_inside_lines_is_not_a_failure():
    assert not ra.is_failure({"status": "matured", "ret_21": -2.0, "excess_21": -1.0})


def test_unmatured_is_not_judged():
    assert not ra.is_failure({"status": "open", "ret_5": -30.0})


# ── Aggregates ───────────────────────────────────────────────────────────────

def test_attribution_explodes_comma_lists_and_flags_small_cells():
    df = pd.DataFrame({"excess_21": [1.0, -1.0, 3.0], "family_names": ["A, B", "A", ""]})
    out = ra.attribution(df, "family_names", min_n=2).set_index("family_names")
    assert out.loc["A", "n"] == 2 and bool(out.loc["A", "sufficient"])
    assert out.loc["B", "n"] == 1 and not bool(out.loc["B", "sufficient"])
    assert out.loc["(none)", "n"] == 1


def test_summary_counts_and_rates():
    df = pd.DataFrame({"ret_21": [5.0, -5.0, None], "excess_21": [2.0, -1.0, None],
                       "status": ["matured", "matured", "no_data"],
                       "plan_outcome": ["target_first", "stop_first", None]})
    s = ra.summarise(df)
    assert (s["episodes"], s["n"], s["no_data"]) == (3, 2, 1)
    assert s["hit_rate"] == 50.0 and s["beat_market_rate"] == 50.0
    assert s["target_first_rate"] == 50.0


def test_paper_portfolio_equal_weights_active_positions():
    a = _bars([100.0, 110.0, 121.0], opens=[100.0, 110.0, 121.0])
    mkt = _bars([1.0, 1.0, 1.0])
    df = pd.DataFrame([{"symbol": "A", "entry_date": "2026-08-03"}])
    eq = ra.paper_portfolio(df, {"A": a}, mkt, hold=3)
    assert eq["basket"].iloc[-1] == pytest.approx(1.21)
    assert eq["market"].iloc[-1] == pytest.approx(1.0)
    assert ra.max_drawdown(pd.Series([1.0, 1.2, 0.9])) == -25.0


def test_paper_portfolio_ends_at_mean_holding_return_and_freezes_exits():
    # A doubles over its 2-session hold then crashes (after exit — ignored);
    # B enters a day later and is flat. Final = mean(2.0, 1.0) = 1.5.
    a = _bars([100.0, 200.0, 10.0, 10.0], opens=[100.0, 200.0, 10.0, 10.0])
    b = _bars([50.0, 50.0, 50.0, 50.0])
    mkt = _bars([1.0] * 4)
    df = pd.DataFrame([{"symbol": "A", "entry_date": "2026-08-03"},
                       {"symbol": "B", "entry_date": "2026-08-04"}])
    eq = ra.paper_portfolio(df, {"A": a, "B": b}, mkt, hold=2)
    assert eq["basket"].iloc[0] == pytest.approx(1.0)       # only A deployed, day 1
    assert eq["basket"].iloc[-1] == pytest.approx(1.5)
    assert eq["active"].tolist() == [1, 2, 1]                # ends at the last exit


def test_a_split_sized_jump_cuts_the_window_and_sets_short_episodes_aside():
    # HEG, 2026-09-07: −62.6% in one session, then normal trading at the new level.
    closes = [100.0] * 10 + [37.0] * 30
    b = _bars(closes, opens=closes)
    o = ra.episode_outcome(_ep(), b, _bars([1.0] * 40))
    assert o["status"] == "data_suspect" and o["data_suspect_date"] == str(b.index[10].date())
    assert "ret_21" not in o and o["ret_5"] == pytest.approx(0.0)
    assert not ra.is_failure(o)


def test_returns_before_a_late_split_still_count():
    closes = [100.0] * 30 + [40.0] * 10
    o = ra.episode_outcome(_ep(), _bars(closes, opens=closes), _bars([1.0] * 40))
    assert o["status"] == "matured" and "ret_21" in o and "ret_63" not in o


def test_a_20pct_circuit_is_a_real_move_not_a_split():
    closes = [100.0] * 5 + [80.0, 64.0, 51.2] + [51.2] * 30
    o = ra.episode_outcome(_ep(), _bars(closes, opens=closes), _bars([1.0] * 38))
    assert o["status"] == "matured" and "data_suspect_date" not in o
