"""Tests for portfolio_sim — B-159.

Pinned here: the sizing arithmetic (fixed fractional on closed equity, P&L =
R × risk actually taken), every cap and the reason it is COUNTED when it bites,
the same-day rule (a stop hit today cannot fund an entry today), shorts skipped
by default, the closed-curve drawdown, seed determinism, and that the harness's
kept trades now carry the dates and levels the account needs.

Run:  python -m pytest tools/test_portfolio_sim.py -q
"""
import numpy as np
import pandas as pd
import pytest

import backtest as bt
import portfolio_sim as ps
import rule_engine as re_
import scanner_templates as sc

D = pd.Timestamp


def _t(sym, entry, exit_, r, entry_px=100.0, stop=95.0, side="long"):
    return {"symbol": sym, "side": side, "entry_px": entry_px, "stop": stop,
            "r": r, "entry_date": D(entry), "exit_date": D(exit_)}


def _run(trades, **kw):
    kw.setdefault("n_seeds", 1)
    return ps.simulate(trades, ps.Settings(**kw))


def _path(res):
    return res["paths"][0]


def test_sizing_is_fixed_fractional_and_pnl_is_r_times_risk():
    # 1% of 1,000,000 = 10,000 at risk; 5% stop → 200,000 notional (= the 20% cap).
    res = _run([_t("A", "2024-01-01", "2024-01-10", 2.0)])
    assert _path(res)["final_equity"] == pytest.approx(1_020_000)
    assert _path(res)["capped"] == 0


def test_position_cap_shrinks_the_risk_and_is_counted():
    # 1% stop wants 1,000,000 notional; capped to 200,000 → risk 2,000.
    res = _run([_t("A", "2024-01-01", "2024-01-10", 1.0, stop=99.0)])
    assert _path(res)["final_equity"] == pytest.approx(1_002_000)
    assert _path(res)["capped"] == 1


def test_sizing_compounds_on_closed_equity_only():
    trades = [_t("A", "2024-01-01", "2024-01-05", 2.0),      # +20,000 → 1,020,000
              _t("B", "2024-01-08", "2024-01-12", -1.0)]     # risks 1% of 1,020,000
    assert _path(_run(trades))["final_equity"] == pytest.approx(1_020_000 - 10_200)


def test_max_open_skips_and_counts():
    trades = [_t(s, "2024-01-01", "2024-01-10", 1.0) for s in "ABC"]
    p = _path(_run(trades, max_open=2))
    assert p["taken"] == 2 and p["skipped"] == {"no_free_slot": 1}


def test_no_leverage_skips_when_cash_runs_out():
    trades = [_t(s, "2024-01-01", "2024-01-10", 1.0, stop=99.0) for s in "ABC"]
    p = _path(_run(trades, max_position_pct=50.0))
    assert p["taken"] == 2 and p["skipped"] == {"no_cash": 1}


def test_a_stop_hit_today_cannot_fund_an_entry_today():
    a = _t("A", "2024-01-01", "2024-01-05", -1.0)
    same_day = _t("B", "2024-01-05", "2024-01-09", 1.0)
    next_day = _t("C", "2024-01-06", "2024-01-09", 1.0)
    p = _path(_run([a, same_day], max_open=1))
    assert p["taken"] == 1 and p["skipped"] == {"no_free_slot": 1}
    assert _path(_run([a, next_day], max_open=1))["taken"] == 2


def test_one_position_per_symbol():
    trades = [_t("A", "2024-01-01", "2024-01-10", 1.0),
              _t("A", "2024-01-03", "2024-01-12", 1.0)]
    assert _path(_run(trades))["skipped"] == {"already_holding_symbol": 1}


def test_shorts_skipped_unless_allowed():
    s = _t("A", "2024-01-01", "2024-01-10", 1.0, entry_px=100, stop=105, side="short")
    assert _path(_run([s]))["skipped"] == {"short": 1}
    assert _path(_run([s], allow_short=True))["final_equity"] == pytest.approx(1_010_000)


def test_closed_curve_drawdown():
    trades = [_t("A", "2024-01-01", "2024-01-02", 2.0),      # 1,020,000 (peak)
              _t("B", "2024-01-03", "2024-01-04", -1.0),     # −10,200
              _t("C", "2024-01-05", "2024-01-06", -1.0)]     # −1% of 1,009,800
    p = _path(_run(trades))
    trough = 1_009_800 * 0.99
    assert p["max_dd_closed_pct"] == pytest.approx((trough / 1_020_000 - 1) * 100)
    assert p["longest_dd_days"] == 2


def test_seeds_are_deterministic_and_selection_luck_shows():
    rng = np.random.default_rng(0)
    trades = [_t(f"S{i}", "2024-01-01", "2024-02-01", float(rng.normal(0, 2)))
              for i in range(30)]
    a = _run(trades, max_open=3, n_seeds=10)
    b = _run(trades, max_open=3, n_seeds=10)
    assert a["summary"] == b["summary"]
    s = a["summary"]["total_return_pct"]
    assert s["p10"] < s["p90"]          # which 3 of 30 got in matters, and shows


def test_unusable_trades_are_counted_not_hidden():
    bad = [{"symbol": "A", "r": 1.0, "entry_px": 100, "stop": 95},          # no dates
           {**_t("B", "2024-01-01", "2024-01-02", 1.0), "stop": 100.0}]       # zero risk
    res = _run(bad)
    assert res["dropped"] == {"no_dates": 1, "zero_risk": 1}
    assert "error" in res


@pytest.mark.parametrize("bad", [dict(risk_pct=0), dict(max_open=0),
                                 dict(max_position_pct=150), dict(capital=-1)])
def test_settings_are_validated(bad):
    with pytest.raises(ValueError):
        _run([_t("A", "2024-01-01", "2024-01-02", 1.0)], **bad)


def test_report_states_the_drawdown_caveat():
    txt = ps.format_report(_run([_t("A", "2024-01-01", "2024-01-10", 2.0)]))
    assert "CLOSED-trade" in txt and "survivors only" in txt


# ── the harness now keeps what the account needs ─────────────────────────────

def test_kept_trades_carry_dates_and_levels():
    rng = np.random.default_rng(3)
    n = 500
    close = 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.018, n)))
    idx = pd.bdate_range("2020-01-01", periods=n)
    df = pd.DataFrame({"open": close * (1 + rng.normal(0, 0.003, n)),
                       "high": close * 1.01, "low": close * 0.99,
                       "close": close, "volume": np.full(n, 1e6)}, index=idx)
    rule = re_.compile_rule({
        "name": "pt", "hypothesis": "h",
        "steps": [{"all": [{"lhs": "close", "op": "crosses_above", "rhs": "ema:20"}]}],
        "plan": {"stop": "pct:3", "target_r": 2, "time_stop": 15}})
    name = re_.register(rule)
    try:
        res = bt.backtest_scanner(name, ["X"], {"X": df}.get, horizons=(5, 20),
                                  signal_mode="fresh", fill_model="market",
                                  keep_trades=True)
    finally:
        sc.SCANNERS.pop(name, None)
    tr = res["trades"]
    assert tr
    for t in tr:
        assert t["entry_date"] == idx[t["entry_idx"]]
        assert t["exit_date"] == idx[min(t["entry_idx"] + t["bars"], n - 1)]
        assert t["entry_date"] > idx[t["t"]]                  # entry is after the signal bar
        assert t["stop"] < t["entry_px"] * 1.0001 or t["side"] == "short"
    out = ps.simulate(tr, ps.Settings(n_seeds=2))
    assert out["n_usable"] == len(tr)
