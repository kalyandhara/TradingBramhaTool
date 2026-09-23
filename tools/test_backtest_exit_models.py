"""Tests for `_simulate_plan(exit_model=...)` — B-123.

The harness could express a fixed stop, a fixed target and a time stop, and
nothing that MOVES. So every trailing stop drawn on the chart (PMax, SuperTrend
AI, PSAR) had never been measured as an exit by it, and the LuxAlgo exit list
that raised this would only have added more unmeasured lines.

What is pinned here is the set of rules that decide whether a trail result is
honest, because each one, broken, produces a plausible number rather than an
error:

* ``fixed`` is the pre-B-123 behaviour BIT FOR BIT — every published R came
  through it, so the default must not move.
* a trail only tightens (ratchet-only) and is never set from the bar it exits on;
* model exits are close-based;
* swing pivots are only used once confirmed (p bars later) — no lookahead;
* the short side is a mirror;
* a typo in the model name RAISES instead of quietly measuring the control.

Run:  python -m pytest tools/test_backtest_exit_models.py -q
"""
import numpy as np
import pandas as pd
import pytest

import backtest as bt


def _frame(bars):
    """bars = [(open, high, low, close)]"""
    a = np.asarray(bars, dtype=float)
    return pd.DataFrame({"open": a[:, 0], "high": a[:, 1],
                         "low": a[:, 2], "close": a[:, 3],
                         "volume": np.full(len(a), 1e6)})


def _bar(c, w=0.5):
    return (c, c + w, c - w, c)


def _path(closes, w=0.5):
    return _frame([_bar(c, w) for c in closes])


# ── parsing ──────────────────────────────────────────────────────────────────

def test_parse_defaults_and_arguments():
    assert bt.parse_exit_model(None) == ("fixed", None)
    assert bt.parse_exit_model("fixed") == ("fixed", None)
    assert bt.parse_exit_model("atr_trail") == ("atr_trail", 3.0)
    assert bt.parse_exit_model("ATR_TRAIL:2.5") == ("atr_trail", 2.5)
    assert bt.parse_exit_model("ema_close:10") == ("ema_close", 10.0)


@pytest.mark.parametrize("bad", ["chandelier", "atr", "atr_trail:0", "ema_close:-3"])
def test_a_typo_raises_rather_than_measuring_the_control(bad):
    with pytest.raises(ValueError):
        bt.parse_exit_model(bad)


def test_backtest_scanner_rejects_a_bad_model_before_doing_any_work():
    with pytest.raises(ValueError):
        bt.backtest_scanner("Falling Wedge", [], lambda s: None, exit_model="trail")


# ── fixed is unchanged ───────────────────────────────────────────────────────

@pytest.mark.parametrize("closes, stop, tgt", [
    ([100, 101, 103, 106, 111, 108], 97.0, 110.0),     # target
    ([100, 99, 98, 96, 95, 97], 97.0, 110.0),          # stop
    ([100, 101, 100, 101, 100, 101], 97.0, 110.0),     # open at horizon
])
def test_fixed_is_bit_for_bit_the_old_behaviour(closes, stop, tgt):
    df = _path(closes)
    a = bt._simulate_plan(df, 0, 100.0, stop, tgt, 10)
    b = bt._simulate_plan(df, 0, 100.0, stop, tgt, 10, exit_model="fixed")
    assert a == b
    assert "exit_model" not in a         # no new keys on the fixed path either


# ── the rules every moving model obeys ───────────────────────────────────────

def test_the_initial_stop_still_fires_intraday_under_a_trail():
    df = _frame([_bar(100), _bar(100), (100, 100.5, 94, 99.5)])
    r = bt._simulate_plan(df, 0, 100.0, 95.0, 110.0, 10, exit_model="ema_close:3")
    assert r["outcome"] == "stop" and r["r"] == pytest.approx(-1.0)


def test_a_trail_drops_the_fixed_target_and_says_so():
    """A run straight through the card's target is NOT closed there."""
    closes = [100 + i for i in range(30)]
    r = bt._simulate_plan(_path(closes), 0, 100.0, 95.0, 105.0, 25,
                          exit_model="atr_trail:3")
    assert r["outcome"] == "open"
    assert r["r"] > 3                     # well past the 1R target it ignored
    assert r["target_used"] is False and r["exit_model"] == "atr_trail:3"


def test_atr_trail_ratchets_and_never_loosens():
    """Rise, then a pullback that would LOWER a naive trail. The trail must
    hold its high-water level and take the exit there."""
    up = [100 + 2 * i for i in range(15)]              # to 128
    down = [128 - 1.5 * i for i in range(1, 20)]       # slow give-back
    df = _path(up + down, w=1.0)
    r = bt._simulate_plan(df, 0, 100.0, 90.0, 999.0, 40, exit_model="atr_trail:3")
    assert r["outcome"] == "trail"
    assert r["r"] > 1.0                  # locked in part of the run
    # Independent reference: the stop in force on the exit bar is the MAXIMUM of
    # every candidate so far. A trail that followed the latest candidate down
    # (loosening) would fill lower, and this is the assertion that catches it.
    atr = bt._exit_series(df, "atr_trail", 3.0)["atr"]
    hi, cands = -1e9, [90.0]
    for i in range(r["bars"]):
        hi = max(hi, df["high"][i])
        cands.append(hi - 3.0 * atr[i])
    assert 100.0 + r["r"] * 10.0 == pytest.approx(max(cands))
    assert max(cands) > cands[-1]        # the path really did try to loosen it


def test_atr_trail_is_not_set_from_the_bar_it_exits_on():
    """A single bar with a huge high then a collapse to below that bar's own
    implied trail must not exit on a level it created."""
    closes = [100] * 25
    df = _path(closes, w=0.5)
    df.loc[24, ["high", "low", "close"]] = [150.0, 99.0, 100.0]
    r = bt._simulate_plan(df, 24, 100.0, 90.0, 999.0, 0, exit_model="atr_trail:1")
    # horizon 0 → the entry bar only. Its own 150 high must not have moved the
    # stop it was tested against.
    assert r["outcome"] == "open"


def test_ema_close_exits_on_the_close_not_the_wick():
    closes = [100 + i for i in range(10)]
    bars = [_bar(c) for c in closes]
    bars.append((109, 110, 95, 109.5))    # wick far below the EMA, close above
    bars.append((109, 109.5, 99, 100))    # close below the EMA
    df = _frame(bars)
    r = bt._simulate_plan(df, 5, 105.0, 90.0, 999.0, 20, exit_model="ema_close:3")
    assert r["outcome"] == "trail"
    assert r["bars"] == 11 - 5            # the close bar, not the wick bar
    assert r["r"] == pytest.approx((100 - 105) / 15.0)


def test_structure_uses_a_swing_only_once_it_is_confirmed():
    """Swing low at bar 5 (p=2) is known at bar 7. A close under it at bar 6 is
    NOT a break — the pivot did not exist yet."""
    closes = [110, 108, 106, 104, 103, 100, 99.4, 104, 106, 99]
    lows = [c - 0.5 for c in closes]
    lows[5] = 99.5
    lows[6] = 99.6
    bars = [(c, c + 0.5, l, c) for c, l in zip(closes, lows)]
    df = _frame(bars)
    ser = bt._exit_series(df, "structure", 2.0)
    assert np.isnan(ser["swing_low"][6]) or ser["swing_low"][6] != 99.5
    assert ser["swing_low"][7] == 99.5
    r = bt._simulate_plan(df, 6, 99.4, 90.0, 999.0, 10, exit_model="structure:2")
    assert r["outcome"] == "trail" and r["bars"] == 3     # bar 9's close 99 < 99.5


# ── the short side is a mirror ───────────────────────────────────────────────

def test_short_atr_trail_mirrors_the_long():
    up = [100 + 2 * i for i in range(15)] + [128 - 1.5 * i for i in range(1, 20)]
    long_df = _path(up, w=1.0)
    short_df = _path([200 - c for c in up], w=1.0)
    lr = bt._simulate_plan(long_df, 0, 100.0, 90.0, 999.0, 40,
                           exit_model="atr_trail:3")
    sr = bt._simulate_plan(short_df, 0, 100.0, 110.0, -999.0, 40,
                           side="short", exit_model="atr_trail:3")
    assert sr["outcome"] == lr["outcome"] and sr["bars"] == lr["bars"]
    assert sr["r"] == pytest.approx(lr["r"])


def test_short_ema_close_exits_on_a_close_above():
    closes = [100 - i for i in range(10)] + [100]
    df = _path(closes)
    r = bt._simulate_plan(df, 5, 95.0, 110.0, -999.0, 20,
                          side="short", exit_model="ema_close:3")
    assert r["outcome"] == "trail" and r["bars"] == 5


# ── the report must SEE trail exits ──────────────────────────────────────────

def test_pooling_counts_trail_exits_and_the_exit_neutral_win_rate():
    """The first smoke run of B-123 would have lost every trail exit: the R
    block counted target/stop/open/time only, and win_rate is "target hit",
    which is 0% by construction once the target is dropped. Pinned so a trail
    run can never report a tidy, empty tally."""
    blocks = [
        {"n_with_plan": 4, "target_hits": 0, "stop_hits": 1, "open_exits": 0,
         "time_exits": 0, "trail_exits": 3, "positive_rate": 75.0, "avg_R": 0.5},
        {"n_with_plan": 6, "target_hits": 0, "stop_hits": 3, "open_exits": 1,
         "time_exits": 0, "trail_exits": 2, "positive_rate": 50.0, "avg_R": -0.1},
    ]
    pooled = bt._pool_r_blocks(blocks)
    assert pooled["trail_exits"] == 5
    assert pooled["positive_rate"] == pytest.approx((3 + 3) / 10)
    assert pooled["target_rate"] == 0.0     # true, and exactly why it is not the win rate
    counted = (pooled["target_hits"] + pooled["stop_hits"] + pooled["open_exits"]
               + pooled["time_exits"] + pooled["trail_exits"])
    assert counted == pooled["n_with_plan"]


# ── B-124 hooks ──────────────────────────────────────────────────────────────

def _stub_frame(n=320):
    rng = np.random.default_rng(7)
    c = 100 + np.cumsum(rng.normal(0.1, 1.0, n))
    return pd.DataFrame({"open": c, "high": c + 1, "low": c - 1, "close": c,
                         "volume": np.full(n, 1e6)})


@pytest.fixture
def stub_scanner(monkeypatch):
    """Fires every 25th bar with a 1-ATR-ish plan and a 3-bar time stop."""
    import scanner_templates as sc

    def fn(df):
        if len(df) % 25:
            return None
        last = float(df["close"].iloc[-1])
        return {"entry": last, "stop": last - 3, "target": last + 30, "time_stop": 3}
    monkeypatch.setitem(sc.SCANNERS, "_stub_b124", {"fn": fn})
    return "_stub_b124"


def test_trades_are_kept_and_pair_across_exit_arms(stub_scanner):
    df = _stub_frame()
    kw = dict(fetch_fn=lambda s: df, keep_trades=True, fill_model="market",
              signal_mode="fresh")
    a = bt.backtest_scanner(stub_scanner, ["X", "Y"], **kw)
    b = bt.backtest_scanner(stub_scanner, ["X", "Y"], exit_model="atr_trail:3", **kw)
    ka = {(x["symbol"], x["t"]) for x in a["trades"]}
    kb = {(x["symbol"], x["t"]) for x in b["trades"]}
    assert ka and ka == kb                       # identical entries, pairable
    assert {x["symbol"] for x in a["trades"]} == {"X", "Y"}


def test_honor_time_stop_false_frees_only_the_moving_arms(stub_scanner):
    df = _stub_frame()
    kw = dict(fetch_fn=lambda s: df, keep_trades=True, fill_model="market",
              honor_time_stop=False)
    fixed = bt.backtest_scanner(stub_scanner, ["X"], **kw)
    trail = bt.backtest_scanner(stub_scanner, ["X"], exit_model="atr_trail:3", **kw)
    # fixed still obeys the card: nothing runs past 3 bars
    assert max(x["bars"] for x in fixed["trades"]) <= 3
    # the trail arm is released to the horizon
    assert max(x["bars"] for x in trail["trades"]) > 3
    assert trail["honor_time_stop"] is False
