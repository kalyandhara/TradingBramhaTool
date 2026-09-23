"""Tests for `resolve_fill` and the harness's `fill_model` — B-121.

The harness used to assume the card's stated entry FILLED, at that price, on
the bar after the signal. Sampled on RELIANCE, `scan_flag_pole` returned entry
1469.68 on a bar closing 1441.30: the simulation credited a fill 2% above the
market and measured the stop from it, on a trade nobody could have taken there.

Pinned here:

* ``assumed`` is the old behaviour exactly, and stays the default.
* ``touch`` reads the ORDER TYPE off where the entry sits against the signal
  bar's close — a long above it is a buy-stop, below it a buy-limit — and a gap
  THROUGH the level fills at the open, which is worse for a stop order and
  better for a limit. Getting that direction wrong silently flatters every
  breakout card, which is the whole class of card this row was raised about.
* an order that never trades is CANCELLED after the wait and COUNTED; a fill at
  or beyond the stop is counted separately. Neither may silently shrink n.
* a window where nothing filled still reports its unfilled count when pooled
  (it used to pool to None — a pre-existing bug, fixed alongside).

Run:  python -m pytest tools/test_backtest_fill_models.py -q
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


SIGNAL = (100, 100.5, 99.5, 100)          # signal bar, closes at 100


def test_unknown_model_raises():
    with pytest.raises(ValueError):
        bt.resolve_fill(_frame([SIGNAL, SIGNAL]), 0, 100.0, "long", "limit")
    with pytest.raises(ValueError):
        bt.backtest_scanner("Falling Wedge", [], lambda s: None, fill_model="stop")


def test_assumed_is_the_old_behaviour():
    df = _frame([SIGNAL, (100, 101, 99, 100)])
    f = bt.resolve_fill(df, 0, 102.0, "long", "assumed")
    assert f == {"status": "filled", "idx": 1, "px": 102.0}   # even though 102 never traded


def test_market_fills_at_the_next_open_whatever_the_card_says():
    df = _frame([SIGNAL, (100.7, 101, 99, 100)])
    assert bt.resolve_fill(df, 0, 102.0, "long", "market") == \
        {"status": "filled", "idx": 1, "px": 100.7}


# ── touch: the order type is read off the level ──────────────────────────────

def test_long_entry_above_the_close_is_a_buy_stop():
    """Entry 102 over a 100 close: nothing until a bar trades up to 102."""
    df = _frame([SIGNAL, (100, 101, 99.5, 100.5), (100.8, 102.4, 100.5, 102)])
    assert bt.resolve_fill(df, 0, 102.0, "long", "touch") == \
        {"status": "filled", "idx": 2, "px": 102.0}


def test_a_gap_through_a_buy_stop_fills_at_the_WORSE_open():
    df = _frame([SIGNAL, (104, 105, 103.5, 104.5)])
    assert bt.resolve_fill(df, 0, 102.0, "long", "touch")["px"] == 104.0


def test_long_entry_below_the_close_is_a_buy_limit_and_a_gap_fills_better():
    df = _frame([SIGNAL, (100, 100.5, 99.2, 99.8), (97, 98, 96.5, 97.5)])
    f = bt.resolve_fill(df, 0, 98.0, "long", "touch")
    assert f == {"status": "filled", "idx": 2, "px": 97.0}


def test_short_mirrors_both_order_types():
    # sell-stop below the close; a gap down through it fills at the worse open
    df = _frame([SIGNAL, (96, 96.5, 95, 95.5)])
    assert bt.resolve_fill(df, 0, 98.0, "short", "touch")["px"] == 96.0
    # sell-limit above the close; a gap up through it fills at the better open
    df = _frame([SIGNAL, (104, 105, 103, 104)])
    assert bt.resolve_fill(df, 0, 102.0, "short", "touch")["px"] == 104.0


def test_an_order_that_never_trades_is_cancelled_after_the_wait():
    bars = [SIGNAL] + [(100, 101, 99.5, 100)] * 10
    bars[bt.FILL_MAX_WAIT + 1] = (103, 104, 102.5, 103)   # first touch, one bar too late
    df = _frame(bars)
    assert bt.resolve_fill(df, 0, 102.0, "long", "touch") == {"status": "unfilled"}
    assert bt.resolve_fill(df, 0, 102.0, "long", "touch",
                           max_wait=bt.FILL_MAX_WAIT + 1)["status"] == "filled"


def test_no_bar_after_the_signal_is_unfilled_not_an_error():
    assert bt.resolve_fill(_frame([SIGNAL]), 0, 100.0, "long", "market") == \
        {"status": "unfilled"}


# ── pooling keeps what did not fill ──────────────────────────────────────────

def test_a_window_where_nothing_filled_is_not_lost_when_pooled():
    blocks = [
        {"n_with_plan": 0, "plans_seen": 7, "plans_unfilled": 7,
         "plans_fill_through_stop": 0},
        {"n_with_plan": 3, "plans_seen": 5, "plans_unfilled": 1,
         "plans_fill_through_stop": 1, "target_hits": 1, "stop_hits": 2,
         "open_exits": 0, "time_exits": 0, "positive_rate": 33.3, "avg_R": 0.1},
    ]
    pooled = bt._pool_r_blocks(blocks)
    assert pooled["plans_unfilled"] == 8          # 7 from the empty window survive
    assert pooled["plans_fill_through_stop"] == 1


def test_all_unfilled_pools_to_a_report_not_to_none():
    """Pre-existing bug: `seen = 0 ... if seen else None` always returned None,
    so plans seen but never simulated printed nothing."""
    pooled = bt._pool_r_blocks([{"n_with_plan": 0, "plans_seen": 4,
                                 "plans_unfilled": 4}])
    assert pooled is not None
    assert pooled["plans_seen"] == 4 and pooled["plans_unfilled"] == 4


def test_harmonic_plans_are_never_inverted_on_real_bars():
    """The property, not the source text: on cached bars, every Harmonic card's
    stop and target sit on OPPOSITE sides of its entry."""
    import screener_pipeline as sp
    import scanner_templates as sc
    fn = sc.SCANNERS["Harmonic Reversal (XABCD)"]["fn"]
    checked = 0
    for sym in ("360ONE.NS", "ABB.NS", "ACC.NS"):
        try:
            df = sp.fetch_ohlcv(sym, days=1500)
        except Exception:
            continue
        if df is None or len(df) < 300:
            continue
        for t in range(250, len(df) - 1, 7):
            c = fn(df.iloc[:t + 1])
            if not c:
                continue
            e, st, tg = c["entry"], c["stop"], c["target"]
            assert (st < e < tg) or (tg < e < st), (sym, t, e, st, tg)
            checked += 1
    if not checked:
        pytest.skip("no cached bars")


# ── B-124 findings: inverted plans and fills past the target ─────────────────

def test_a_target_on_the_stop_side_is_degenerate_not_scored():
    """Harmonic Butterfly/Crab put the stop beyond X while D sat beyond X, so a
    bullish plan's stop was ABOVE its entry, the side was read as short, and its
    target was behind it -- every 'target hit' booked a loss."""
    df = _frame([SIGNAL] + [(100, 101, 99, 100)] * 5)
    assert bt._simulate_plan(df, 1, 100.0, 95.0, 90.0, 5) is None
    assert bt._simulate_plan(df, 1, 100.0, 105.0, 110.0, 5, side="short") is None


def test_pooling_keeps_fills_past_the_target():
    pooled = bt._pool_r_blocks([
        {"n_with_plan": 0, "plans_seen": 3, "plans_fill_past_target": 3},
        {"n_with_plan": 2, "plans_seen": 3, "plans_fill_past_target": 1,
         "target_hits": 1, "stop_hits": 1, "open_exits": 0, "time_exits": 0,
         "positive_rate": 50.0, "avg_R": 0.0},
    ])
    assert pooled["plans_fill_past_target"] == 4
