"""Tests for the market-model block in `backtest_scanner` — B-104.

The block computes beta over the 60 bars before a signal and reports alpha =
raw − β × market for each horizon. It was **unreachable** from the day it shipped:
the symbol frame is `reset_index(drop=True)` a few lines above, and the guard on
the block read `hasattr(df.index, "date")`, which a RangeIndex does not have. So
`alpha_avg` and `alpha_ttest` came back None on every run — including the five
dashboard call sites that go to the trouble of fetching a benchmark and passing
it in. Nothing errored. Nothing said so. That is the failure mode this file
exists to keep closed.

The scanner is a stub injected into the registry rather than a real one: the
subject here is the harness's date handling, and a real scanner would make the
test depend on whether that scanner happens to fire on the fixture.
"""
import numpy as np
import pandas as pd
import pytest

import backtest as bt
import scanner_templates as sc

STUB = "_test_every_bar_stub"


@pytest.fixture
def stub_scanner():
    """Fires on every bar, so signal count is a property of the frame, not luck."""
    sc.SCANNERS[STUB] = {"fn": lambda df: {"pattern_type": "stub"},
                         "description": "test stub", "category": "Pattern"}
    try:
        yield STUB
    finally:
        sc.SCANNERS.pop(STUB, None)


def _dated(n=400, start="2023-01-02", drift=0.001, seed=3, index=True):
    rng = np.random.default_rng(seed)
    px = 100.0 * np.cumprod(1 + rng.normal(drift, 0.01, n))
    df = pd.DataFrame({"open": px, "high": px * 1.005,
                       "low": px * 0.995, "close": px,
                       "volume": np.full(n, 1e6)})
    if index:
        df.index = pd.bdate_range(start, periods=n)
    return df


def test_alpha_is_populated_when_a_benchmark_is_supplied(stub_scanner):
    """The regression. Before the fix this returned None on every horizon."""
    bench = _dated(seed=9)
    res = bt.backtest_scanner(stub_scanner, ["A", "B"], lambda s: _dated(seed=hash(s) % 50),
                              benchmark_df=bench, stride=7)
    assert res["n_signals"] > 20, "fixture should produce a usable sample"
    m = res["horizons"][20]
    assert m["alpha_avg"] is not None
    assert m["alpha_ttest"] is not None


def test_no_benchmark_means_no_alpha_not_a_crash(stub_scanner):
    res = bt.backtest_scanner(stub_scanner, ["A"], lambda s: _dated(), stride=7)
    assert res["horizons"][20]["alpha_avg"] is None


def test_an_undated_frame_degrades_quietly(stub_scanner):
    """A caller with no DatetimeIndex cannot be joined to a benchmark by date.
    That has to stay a None, not an exception and not a silent wrong number."""
    res = bt.backtest_scanner(stub_scanner, ["A"], lambda s: _dated(index=False),
                              benchmark_df=_dated(seed=9), stride=7)
    assert res["horizons"][20]["alpha_avg"] is None


def _tracking(bench, beta=1.0, seed=5, noise=0.004):
    """A symbol that genuinely tracks `bench` with the given beta.

    Independent random walks would give a beta of roughly zero with either sign,
    and alpha would then sit on whichever side of the raw return the noise put
    it — a test built on that measures the fixture, not the harness.
    """
    rng = np.random.default_rng(seed)
    b_r = bench["close"].pct_change().fillna(0.0).to_numpy()
    r = beta * b_r + rng.normal(0.0, noise, len(b_r))
    px = 100.0 * np.cumprod(1 + r)
    df = pd.DataFrame({"open": px, "high": px * 1.005, "low": px * 0.995,
                       "close": px, "volume": np.full(len(px), 1e6)},
                      index=bench.index)
    return df


def test_alpha_is_below_raw_return_when_the_market_rose(stub_scanner):
    """Sign check, not just presence: for a symbol that tracks a RISING
    benchmark, subtracting β × market must leave LESS than the raw return. A
    block that quietly handed back the raw number again would pass a presence
    test and fail this one."""
    bench = _dated(drift=0.004, seed=9)            # the market rips
    res = bt.backtest_scanner(stub_scanner, ["A", "B"],
                              lambda s: _tracking(bench, seed=hash(s) % 50),
                              benchmark_df=bench, stride=7)
    m = res["horizons"][20]
    assert m["alpha_avg"] is not None
    assert m["alpha_avg"] < m["avg_ret"], (
        f"alpha {m['alpha_avg']} should trail the raw {m['avg_ret']} "
        "once a rising market is subtracted")


def test_a_beta_two_symbol_loses_more_of_a_rising_market_than_a_beta_one(stub_scanner):
    """Beta is not decoration: the whole point of the market model is that a
    symbol which moves twice as hard with the index gets twice as much of the
    index's move subtracted."""
    bench = _dated(drift=0.004, seed=9)
    one = bt.backtest_scanner(stub_scanner, ["A"],
                              lambda s: _tracking(bench, beta=1.0),
                              benchmark_df=bench, stride=7)["horizons"][20]
    two = bt.backtest_scanner(stub_scanner, ["A"],
                              lambda s: _tracking(bench, beta=2.0),
                              benchmark_df=bench, stride=7)["horizons"][20]
    assert (two["avg_ret"] - two["alpha_avg"]) > (one["avg_ret"] - one["alpha_avg"])


def test_dropped_nan_rows_disable_the_join_rather_than_misalign_it(stub_scanner):
    """The dates are captured BEFORE the dropna+reset. If rows then disappear,
    date i no longer belongs to bar i, and a join on it would be quietly wrong —
    which is worse than no alpha at all. So it must fall back to None."""
    def fetch(_sym):
        df = _dated()
        df.loc[df.index[50], "close"] = np.nan
        return df
    res = bt.backtest_scanner(stub_scanner, ["A"], fetch,
                              benchmark_df=_dated(seed=9), stride=7)
    assert res["horizons"][20]["alpha_avg"] is None
