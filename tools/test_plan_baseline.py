"""B-183 no-edge plan baseline engine (synthetic bars, no network).

Run:  py -3 -X utf8 -m pytest tools/test_plan_baseline.py -q
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import backtest as bt
import plan_baseline as pb


def _walk(n: int, sigma: float = 0.015, seed: int = 1) -> pd.DataFrame:
    """OHLC bars with i.i.d. ratios to the previous close — the case where a block
    bootstrap is unbiased by construction."""
    rng = np.random.default_rng(seed)
    o = np.exp(rng.normal(0, sigma / 3, n))
    c = np.exp(rng.normal(0, sigma, n))
    hi = np.maximum(o, c) * np.exp(np.abs(rng.normal(0, sigma / 2, n)))
    lo = np.minimum(o, c) * np.exp(-np.abs(rng.normal(0, sigma / 2, n)))
    prev = 100.0 * np.cumprod(np.r_[1.0, c[:-1]])
    return pd.DataFrame({"open": prev * o, "high": prev * hi, "low": prev * lo,
                         "close": prev * c, "volume": 1e6})


def _constant(n: int) -> pd.DataFrame:
    """Every bar is the SAME ratio row to its previous close, so every replay of
    any pool is the exact path the real bars take. The close ratio is 1.0: the
    engine removes the pool's drift (amendment 2), and a drift-free pool is the
    one where that removal is a no-op."""
    k = np.array([1.001, 1.012, 0.994, 1.0])            # open, high, low, close
    prev = 100.0 * k[3] ** np.arange(n)
    return pd.DataFrame({"open": prev * k[0], "high": prev * k[1], "low": prev * k[2],
                         "close": prev * k[3], "volume": 1e6})


def test_parity_with_simulate_plan_on_a_one_block_pool():
    df = _constant(800)
    e_idx = 600
    entry = float(df["close"].iloc[e_idx - 1])            # prev close = the fill price
    for stop, target in ((entry * 0.99, entry * 1.011), (entry * 0.999, entry * 1.5),
                         (entry * 0.9, entry * 1.01)):
        r = pb.null_plan_odds(df, e_idx, entry, stop, target, max_bars=20)
        sim = bt._simulate_plan(df, e_idx, entry, stop, target, 20)
        assert abs(r["exp_r"] - sim["r"]) < 1e-9
        key = {"stop": "p_stop", "target": "p_target"}.get(sim["outcome"], "p_open")
        assert r[key] == 1.0


def test_parity_is_net_of_costs_too():
    df = _constant(800)
    entry = float(df["close"].iloc[599])
    r = pb.null_plan_odds(df, 600, entry, entry * 0.99, entry * 1.011, max_bars=20,
                          cost_model=bt.COST_INDIAN)
    sim = bt._simulate_plan(df, 600, entry, entry * 0.99, entry * 1.011, 20,
                            cost_model=bt.COST_INDIAN)
    assert abs(r["exp_r"] - sim["r"]) < 1e-9


def test_calibrated_on_a_random_walk():
    df = _walk(6000, sigma=0.015, seed=7)
    rng = np.random.default_rng(3)
    realised, base = [], []
    closes = df["close"].to_numpy()
    for e_idx in rng.integers(600, 5900, size=2000):
        e_idx = int(e_idx)
        entry = float(df["open"].iloc[e_idx])
        risk = 0.015 * entry
        stop, target = entry - risk, entry + 2 * risk
        sim = bt._simulate_plan(df, e_idx, entry, stop, target, 20)
        nb = pb.null_plan_odds(df, e_idx, entry, stop, target, max_bars=20, replays=300,
                               seed=pb.trade_seed("X", e_idx))
        realised.append(sim["r"])
        base.append(nb["exp_r"])
    assert abs(np.mean(realised) - np.mean(base)) <= 0.03
    assert closes[-1] > 0


def test_pool_never_sees_the_entry_bar_or_later():
    df = _walk(900)
    entry = float(df["open"].iloc[600])
    a = pb.null_plan_odds(df, 600, entry, entry * 0.97, entry * 1.06, max_bars=30)
    df2 = df.copy()
    df2.iloc[600:, :4] *= 3.0
    b = pb.null_plan_odds(df2, 600, entry, entry * 0.97, entry * 1.06, max_bars=30)
    assert a == b


def test_thin_pool_returns_none():
    df = _walk(400)
    entry = float(df["open"].iloc[200])
    assert pb.null_plan_odds(df, 200, entry, entry * 0.97, entry * 1.06, max_bars=20) is None


def test_nan_rows_dropped_and_blocks_do_not_span_them():
    df = _walk(900)
    entry = float(df["open"].iloc[700])
    base = pb.null_plan_odds(df, 700, entry, entry * 0.97, entry * 1.06, max_bars=20)
    df2 = df.copy()
    df2.loc[300, "close"] = np.nan
    r = pb.null_plan_odds(df2, 700, entry, entry * 0.97, entry * 1.06, max_bars=20)
    # rows 300 and 301 both reference the NaN close -> two rows removed
    assert r["n_pool"] == base["n_pool"] - 2
    ratios = pb.ohlc_ratios(df2)
    starts = pb._block_starts(ratios, max(1, 700 - pb.LOOKBACK), 700, pb.BLOCK)
    assert all(not np.isnan(ratios[s:s + pb.BLOCK]).any() for s in starts)
    assert not any(s <= 300 < s + pb.BLOCK or s <= 301 < s + pb.BLOCK for s in starts)


def test_path_is_shortened_at_the_end_of_data():
    df = _walk(900)
    e_idx = len(df) - 5
    entry = float(df["open"].iloc[e_idx])
    r = pb.null_plan_odds(df, e_idx, entry, entry * 0.9, entry * 1.2, max_bars=60)
    assert r["n_bars"] == 5             # entry bar + 4 more, as _simulate_plan walks


def test_time_stop_shortens_the_path():
    df = _walk(900)
    entry = float(df["open"].iloc[700])
    r = pb.null_plan_odds(df, 700, entry, entry * 0.9, entry * 1.2, max_bars=60, time_stop=10)
    assert r["n_bars"] == 11


def test_explicit_n_bars_overrides_and_allows_entry_past_the_data():
    df = _walk(900)
    entry = float(df["close"].iloc[-1])
    r = pb.null_plan_odds(df, len(df), entry, entry * 0.97, entry * 1.06, max_bars=60,
                          n_bars=61)
    assert r["n_bars"] == 61


def test_short_is_the_mirror():
    df = _walk(900)
    inv = pd.DataFrame({"open": 1 / df["open"], "high": 1 / df["low"],
                        "low": 1 / df["high"], "close": 1 / df["close"], "volume": 1e6})
    e = 700
    entry = float(df["open"].iloc[e])
    long = pb.null_plan_odds(df, e, entry, entry * 0.97, entry * 1.06, max_bars=20)
    s_entry = 1 / entry
    short = pb.null_plan_odds(inv, e, s_entry, 1 / (entry * 0.97), 1 / (entry * 1.06),
                              max_bars=20, side="short")
    assert abs(long["p_target"] - short["p_target"]) < 1e-12
    assert abs(long["p_stop"] - short["p_stop"]) < 1e-12


def test_degenerate_plan_returns_none():
    df = _walk(900)
    entry = float(df["open"].iloc[700])
    assert pb.null_plan_odds(df, 700, entry, entry * 1.01, entry * 1.06, max_bars=20) is None
    assert pb.null_plan_odds(df, 700, entry, entry * 0.97, entry * 0.99, max_bars=20) is None


def test_same_seed_same_numbers_and_trade_seed_is_stable():
    df = _walk(900)
    entry = float(df["open"].iloc[700])
    a = pb.null_plan_odds(df, 700, entry, entry * 0.97, entry * 1.06, max_bars=20, seed=5)
    b = pb.null_plan_odds(df, 700, entry, entry * 0.97, entry * 1.06, max_bars=20, seed=5)
    assert a == b
    assert pb.trade_seed("RELIANCE", 812) == pb.trade_seed("RELIANCE", 812)
    assert pb.trade_seed("RELIANCE", 812) != pb.trade_seed("RELIANCE", 813)


def test_probabilities_sum_to_one():
    df = _walk(900)
    entry = float(df["open"].iloc[700])
    r = pb.null_plan_odds(df, 700, entry, entry * 0.98, entry * 1.03, max_bars=20)
    assert r["p_target"] + r["p_stop"] + r["p_open"] == pytest.approx(1.0)
    assert r["replays"] == pb.REPLAYS and r["block"] == pb.BLOCK


def test_pool_drift_is_removed():
    # Amendment 2: a steady trend in the history must not leak into the null.
    # Scaling bar i by g**i multiplies every ratio by g; the result must not move.
    df = _walk(900)
    g = 1.004
    up = df.copy()
    up[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].mul(
        g ** np.arange(len(df)), axis=0)
    e = 700
    entry = float(df["open"].iloc[e])
    a = pb.null_plan_odds(df, e, entry, entry * 0.97, entry * 1.06, max_bars=20)
    b = pb.null_plan_odds(up, e, entry, entry * 0.97, entry * 1.06, max_bars=20)
    assert abs(a["exp_r"] - b["exp_r"]) < 1e-9 and a["p_target"] == b["p_target"]


def test_a_trending_pool_is_not_extrapolated():
    # A stock that rose 0.4% a day for 500 bars gets no extra target odds for it.
    df = _walk(900, sigma=0.01)
    up = df.copy()
    up[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].mul(
        1.004 ** np.arange(len(df)), axis=0)
    e = 700
    entry = float(up["open"].iloc[e])
    r = pb.null_plan_odds(up, e, entry, entry * 0.95, entry * 1.05, max_bars=60)
    assert abs(r["p_target"] - r["p_stop"]) < 0.08     # symmetric plan, no drift -> ~even
