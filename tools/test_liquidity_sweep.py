"""Tests for the B-41 liquidity-sweep / stop-hunt detector.

Runs two ways so it fits the repo's "__main__ probe" style AND pytest:
    py -3 tools/test_liquidity_sweep.py     # prints PASS/FAIL, exits nonzero on fail
    pytest tools/test_liquidity_sweep.py    # standard collection

Pure, deterministic, no network. Frames are built so the pool, the pierce and the
close are each known by construction, which is what lets the sweep-vs-breakdown
exclusivity be asserted rather than hoped for.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import scanner_templates as sc


# ── helpers ───────────────────────────────────────────────────────────────────
def _mk(bars):
    """bars = [(open, high, low, close), ...] -> OHLCV frame."""
    a = np.asarray(bars, dtype=float)
    return pd.DataFrame({
        "open": a[:, 0], "high": a[:, 1], "low": a[:, 2], "close": a[:, 3],
        "volume": np.full(len(a), 100_000.0),
    })


def _flat(n, price, spread=1.0):
    """Gently undulating filler, NOT dead-flat: in a perfectly flat series every
    bar is simultaneously its window's max and min, so flat padding manufactures
    a pivot on every bar and swamps the real ones."""
    out = []
    for i in range(n):
        p = price + (0.35 if i % 2 else -0.35)
        out.append((p, p + spread, p - spread, p))
    return out


def _vshape(depth_low, n=11, top=100.0):
    """A V: down to depth_low at the midpoint, back to `top`. Creates one low pivot."""
    half = n // 2
    down = np.linspace(top, depth_low, half + 1).tolist()
    up = np.linspace(depth_low, top, half + 1).tolist()[1:]
    path = down + up
    return [(p, p + 0.5, p - 0.5, p) for p in path]


def _pool_frame(lows, pivot_len=3, pad=None, tail=None, lead=None):
    """Build a frame containing one low pivot per entry in `lows`, separated by
    enough filler bars that each confirms as a pivot."""
    pad = pad if pad is not None else _flat(pivot_len + 2, 100.0)
    bars = list(lead) if lead is not None else list(_flat(pivot_len + 5, 100.0))
    for lv in lows:
        bars += _vshape(lv, n=2 * pivot_len + 1, top=100.0)
        bars += list(pad)
    if tail:
        bars += tail
    return _mk(bars)


# ── liquidity pools ───────────────────────────────────────────────────────────
def test_no_pools_on_short_frame():
    assert sc.detect_liquidity_pools(_mk(_flat(10, 100.0)), pivot_len=5) == []


def test_equal_lows_form_a_pool():
    df = _pool_frame([90.0, 90.2, 90.1], pivot_len=3)
    pools = sc.detect_liquidity_pools(df, pivot_len=3, eq_tol_pct=1.0, min_touches=2)
    lows = [p for p in pools if p["kind"] == "low"]
    assert lows, "expected an equal-lows pool"
    assert lows[0]["touches"] >= 2


def test_pool_level_is_the_extreme_not_the_mean():
    """Stops rest beyond the edge of the cluster, so the edge is what gets swept."""
    df = _pool_frame([90.0, 90.4], pivot_len=3)
    pools = sc.detect_liquidity_pools(df, pivot_len=3, eq_tol_pct=1.0, min_touches=2)
    lows = [p for p in pools if p["kind"] == "low" and p["touches"] >= 2]
    assert lows, "expected the two near-equal lows to pool"
    # The V bottoms at 90.0 / 90.4 print lows 0.5 below their close.
    assert lows[0]["level"] <= 89.55


def test_interrupted_touches_still_pool():
    """A low at 90, a higher low at 95, then 90 again IS a pool — the revisits
    are interrupted, which is the normal case. Consecutive-only grouping (the
    first implementation) missed exactly this."""
    df = _pool_frame([90.0, 95.0, 90.1], pivot_len=3)
    pools = sc.detect_liquidity_pools(df, pivot_len=3, eq_tol_pct=1.0, min_touches=2)
    near90 = [p for p in pools if p["kind"] == "low" and p["level"] < 91.0]
    assert near90 and near90[0]["touches"] >= 2


def test_touches_must_be_separated_in_time():
    """A single shelf is one level being defended, not many independent
    stop-runs; min_separation stops it inflating the touch count."""
    shelf = [(90.0, 90.5, 89.5, 90.0)] * 6
    df = _pool_frame([90.0], pivot_len=3, tail=shelf + _flat(8, 100.0))
    pools = sc.detect_liquidity_pools(df, pivot_len=3, eq_tol_pct=1.0,
                                      min_touches=2, min_separation=6)
    for p in pools:
        bars = sorted(p["bars"])
        gaps = [b - a for a, b in zip(bars, bars[1:])]
        assert all(g >= 6 for g in gaps), f"touches too close: {p}"


def test_far_apart_lows_do_not_pool():
    """90 and 70 are nowhere near equal, so no pool may contain both."""
    df = _pool_frame([90.0, 70.0], pivot_len=3)
    pools = sc.detect_liquidity_pools(df, pivot_len=3, eq_tol_pct=0.5, min_touches=2)
    for p in pools:
        lo, hi = p["level"], p["level"] * 1.01
        assert not (lo < 75.0 and hi > 85.0), f"90 and 70 pooled together: {p}"
    assert not [p for p in pools if p["kind"] == "low" and 68 < p["level"] < 92
                and p["width_pct"] > 0.5]


def test_pool_span_never_exceeds_the_tolerance():
    """Distance-from-anchor alone admits a cluster twice the tolerance wide (one
    member a full tol below the anchor, another a full tol above). The whole
    cluster must fit inside ONE band or it is not 'equal' lows."""
    # Each step is 0.9% from the previous; the outer pair is ~1.8% apart.
    df = _pool_frame([90.0, 90.81, 91.63], pivot_len=3)
    for tol in (0.5, 1.0, 2.0):
        pools = sc.detect_liquidity_pools(df, pivot_len=3, eq_tol_pct=tol,
                                          min_touches=2)
        for p in pools:
            assert p["width_pct"] <= tol + 1e-6, f"pool spans wider than tol: {p}"


def test_min_touches_is_respected():
    df = _pool_frame([90.0, 90.1], pivot_len=3)
    three = sc.detect_liquidity_pools(df, pivot_len=3, eq_tol_pct=1.0, min_touches=3)
    assert not [p for p in three if p["kind"] == "low"]


# ── the sweep ─────────────────────────────────────────────────────────────────
def _swept_frame(close_at, pivot_len=3, low=88.0, lead=24):
    """Two equal lows near 90, then a bar that wicks to `low` and closes at
    `close_at`. Whether that bar is a sweep or a breakdown depends only on the
    close, which is exactly what the test varies.

    `lead` pads the front so the frame clears the SCANNERS' history gate
    (pivot_len*2 + 40), which is stricter than the detector's.
    """
    tail = [(95.0, 95.5, low, close_at)] + _flat(1, close_at)
    return _pool_frame([90.0, 90.1], pivot_len=pivot_len,
                       lead=_flat(lead, 100.0), tail=tail)


def test_sweep_detected_when_close_reclaims():
    df = _swept_frame(close_at=94.0, pivot_len=3)
    ev = sc.detect_liquidity_sweep(df, pivot_len=3, eq_tol_pct=1.0,
                                   min_pierce_atr=0.01, min_wick_ratio=0.3)
    assert ev is not None and ev["direction"] == "bullish"
    assert ev["reclaimed"] is True and ev["level"] >= 89.0


def test_breakdown_is_not_a_sweep():
    """Same wick, but the bar CLOSES below the pool — a real break. The two must
    be mutually exclusive or the scanner contradicts detect_support_breakdown."""
    df = _swept_frame(close_at=88.2, pivot_len=3)
    ev = sc.detect_liquidity_sweep(df, pivot_len=3, eq_tol_pct=1.0,
                                   min_pierce_atr=0.01, min_wick_ratio=0.3)
    assert ev is None or ev["direction"] != "bullish"


def test_no_pierce_no_sweep():
    df = _pool_frame([90.0, 90.1], pivot_len=3,
                     tail=[(95.0, 95.5, 92.0, 94.0)] + _flat(1, 94.0))
    ev = sc.detect_liquidity_sweep(df, pivot_len=3, eq_tol_pct=1.0,
                                   min_pierce_atr=0.01, min_wick_ratio=0.3)
    assert ev is None or ev["level"] < 90.0


def test_oversized_pierce_is_rejected_as_a_real_break():
    """A pierce far beyond the pool is a break that kept going, not a stop hunt."""
    df = _swept_frame(close_at=94.0, low=40.0, pivot_len=3)
    ev = sc.detect_liquidity_sweep(df, pivot_len=3, eq_tol_pct=1.0,
                                   min_pierce_atr=0.01, max_pierce_atr=1.5,
                                   min_wick_ratio=0.3)
    assert ev is None


def test_wick_ratio_gate_filters_weak_rejection():
    df = _swept_frame(close_at=94.0, pivot_len=3)
    strict = sc.detect_liquidity_sweep(df, pivot_len=3, eq_tol_pct=1.0,
                                       min_pierce_atr=0.01, min_wick_ratio=0.99)
    assert strict is None


def test_pool_must_predate_the_sweeping_bar():
    """A bar cannot sweep a pool that only exists because of that same bar."""
    df = _swept_frame(close_at=94.0, pivot_len=3)
    ev = sc.detect_liquidity_sweep(df, pivot_len=3, eq_tol_pct=1.0,
                                   min_pierce_atr=0.01, min_wick_ratio=0.3)
    if ev is not None:
        n = len(sc._clean_ohlc(df))
        swept_idx = n - 1 - ev["bars_ago"]
        assert max(ev["pool_bars"]) < swept_idx


def test_short_frame_returns_none():
    assert sc.detect_liquidity_sweep(_mk(_flat(12, 100.0)), pivot_len=5) is None


def test_flat_tape_has_no_sweep():
    assert sc.detect_liquidity_sweep(_mk(_flat(200, 100.0)), pivot_len=5) is None


# ── scanners ──────────────────────────────────────────────────────────────────
def test_bull_scanner_fires_on_a_sweep():
    df = _swept_frame(close_at=94.0, pivot_len=3)
    r = sc.scan_liquidity_sweep(df, max_bars_ago=3, pivot_len=3, eq_tol_pct=1.0)
    assert r is not None, "the constructed sweep must fire the scanner"
    assert r["pattern_type"] == "Bullish Liquidity Sweep"
    assert r["stop"] < r["entry"] < r["target"]
    assert 0 <= r["score_base"] <= 100
    assert any("equal-lows pool" in x for x in r["reasons"])


def test_target_always_clears_the_minimum_rr():
    """The nearest overhead pool can sit just above entry, which yields an R:R
    near zero — not a trade plan. Measured on live data before this gate: NTPC
    emitted entry 330 / target 330.22 / R:R 0.02."""
    df = _swept_frame(close_at=94.0, pivot_len=3)
    r = sc.scan_liquidity_sweep(df, max_bars_ago=3, pivot_len=3, eq_tol_pct=1.0)
    assert r is not None
    rr = (r["target"] - r["entry"]) / (r["entry"] - r["stop"])
    assert rr >= sc.MIN_SWEEP_RR - 1e-9, f"R:R {rr:.2f} below the floor"


def test_bull_scanner_declines_a_breakdown():
    df = _swept_frame(close_at=88.2, pivot_len=3)
    assert sc.scan_liquidity_sweep(df, max_bars_ago=3, pivot_len=3,
                                   eq_tol_pct=1.0) is None


def test_bull_scanner_declines_when_reclaim_was_lost():
    """Swept and reclaimed, but price has since closed back under the pool — the
    trapped-seller read is dead and this is a breakdown after all."""
    tail = [(95.0, 95.5, 88.0, 94.0)] + _flat(3, 85.0)
    df = _pool_frame([90.0, 90.1], pivot_len=3, tail=tail)
    assert sc.scan_liquidity_sweep(df, max_bars_ago=6, pivot_len=3,
                                   eq_tol_pct=1.0) is None


def test_stale_sweep_is_not_reported():
    tail = [(95.0, 95.5, 88.0, 94.0)] + _flat(12, 94.0)
    df = _pool_frame([90.0, 90.1], pivot_len=3, tail=tail)
    assert sc.scan_liquidity_sweep(df, max_bars_ago=2, pivot_len=3,
                                   eq_tol_pct=1.0) is None


def test_bear_scanner_shape_when_it_fires():
    """Equal HIGHS pierced then closed back below."""
    bars = list(_flat(8, 100.0))
    for _ in range(2):
        bars += [(100, 100.5, 99.5, 100)] * 3
        bars += [(105, 110.0, 104.5, 105)]          # high pivot ~110
        bars += [(100, 100.5, 99.5, 100)] * 5
    bars += [(106, 112.0, 105.0, 106.0)]            # pierce 110, close below
    bars += _flat(1, 106.0)
    df = _mk(bars)
    r = sc.scan_liquidity_sweep_bear(df, max_bars_ago=3, pivot_len=3, eq_tol_pct=1.5)
    if r is not None:
        assert r["pattern_type"] == "Bearish Liquidity Sweep"
        assert r["target"] is None            # risk flag, not a short signal
        assert r["stop"] > r["entry"]


def test_both_scanners_registered_with_right_categories():
    assert sc.SCANNERS["Liquidity Sweep"]["category"] == "Entry"
    assert sc.SCANNERS["Liquidity Sweep Bear"]["category"] == "Risk"
    assert sc.SCANNERS["Liquidity Sweep"]["fn"] is sc.scan_liquidity_sweep
    assert sc.SCANNERS["Liquidity Sweep Bear"]["fn"] is sc.scan_liquidity_sweep_bear


def test_scanners_tolerate_junk_input():
    for bad in (None, _mk(_flat(3, 100.0))):
        assert sc.scan_liquidity_sweep(bad) is None
        assert sc.scan_liquidity_sweep_bear(bad) is None


ALL_TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]


if __name__ == "__main__":
    import traceback
    failed = 0
    for t in ALL_TESTS:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL  {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(ALL_TESTS) - failed}/{len(ALL_TESTS)} passed")
    raise SystemExit(1 if failed else 0)
