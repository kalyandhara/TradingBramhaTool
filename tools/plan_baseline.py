"""plan_baseline.py — B-183: what would a plan have earned with no edge at all?

Pre-registered in trading-wiki/wiki/analyses/Plan-Odds-Baseline-Pre-Registration.md
(2026-10-25) before any trade was scored against it.

Every plan-R number the harness publishes is compared against ZERO, and zero is
the wrong null for a plan: the same 1R-stop / 2R-target geometry earns a
different expected R on a calm stock than on a volatile one before any signal is
involved. This module answers, per trade: given THIS plan's levels and THIS
stock's own recent behaviour, what R would a signal carrying no information have
earned?

  * Pool: the stock's own daily bars strictly before the entry bar, the last
    LOOKBACK (500), each as four ratios (open, high, low, close) to the previous
    close. Fewer than MIN_POOL (250) usable rows -> None (the caller counts it).
  * Resampling: blocks of BLOCK (5) consecutive rows, drawn with replacement, so
    short volatility clusters survive; a block never spans a removed row.
    REPLAYS (2,000) paths per trade.
  * Path: starts at the fill price; each simulated bar is the previous simulated
    close times the drawn ratios; as many bars as the real trade had.
  * Scoring: `backtest._simulate_plan`'s fixed exit exactly — stop checked before
    target on every bar, a bar touching both is the stop, stop/target fill at
    their level, R net of the cost model, short = exact mirror.
  * Drift is kept: the null is "no information beyond what the tape already
    showed", the same null as the harness's random-entry baseline.
"""
from __future__ import annotations

import math
import zlib

import numpy as np
import pandas as pd

REPLAYS = 2000
BLOCK = 5
LOOKBACK = 500
MIN_POOL = 250
SEED = 19


def trade_seed(symbol: str, entry_idx: int) -> int:
    """Per-trade seed: same data -> same numbers on any machine."""
    return SEED ^ zlib.crc32(f"{symbol}:{entry_idx}".encode())


def ohlc_ratios(df: pd.DataFrame) -> np.ndarray:
    """(len(df), 4): row i = open, high, low, close of bar i / close of bar i-1.
    Row 0, and any row touching a NaN or non-positive price, is NaN."""
    o, h, lo, c = (df[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
    prev = np.r_[np.nan, c[:-1]]
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.column_stack([o / prev, h / prev, lo / prev, c / prev])
    bad = ~np.isfinite(out).all(axis=1) | (out <= 0).any(axis=1)
    out[bad] = np.nan
    return out


def _block_starts(ratios: np.ndarray, lo: int, hi: int, block: int) -> np.ndarray:
    """Start rows s in [lo, hi) whose whole block s .. s+block-1 is inside the
    window and free of removed (NaN) rows."""
    ok = ~np.isnan(ratios[lo:hi]).any(axis=1)
    if len(ok) < block:
        return np.empty(0, dtype=int)
    run = np.convolve(ok.astype(int), np.ones(block, dtype=int), mode="valid")
    return np.flatnonzero(run == block) + lo


def null_plan_odds(df: pd.DataFrame, entry_idx: int, entry: float, stop: float,
                   target: float, max_bars: int, time_stop: float | None = None,
                   side: str = "long", cost_model=None, replays: int = REPLAYS,
                   block: int = BLOCK, lookback: int = LOOKBACK, seed: int = SEED,
                   n_bars: int | None = None) -> dict | None:
    """No-edge odds and expected R for one plan, or None (degenerate plan, thin
    pool, or nothing left to walk).

    `n_bars=None` walks exactly the bars the real trade had (the study's
    like-for-like case); an explicit `n_bars` is a forward-looking path length and
    then `entry_idx` may equal `len(df)`.
    """
    import backtest as bt
    short = str(side).lower() in ("short", "bear", "bearish", "down")
    risk = (stop - entry) if short else (entry - stop)
    if not risk > 0:
        return None
    if (target >= entry) if short else (target <= entry):
        return None
    cm = cost_model or bt.COST_GROSS
    horizon = max_bars if time_stop is None else min(max_bars, int(time_stop))
    if n_bars is None:
        if entry_idx >= len(df):
            return None
        n_bars = min(horizon, len(df) - 1 - entry_idx) + 1
    if n_bars < 1:
        return None

    ratios = ohlc_ratios(df.iloc[:entry_idx])         # never a bar at or after entry
    lo = max(1, entry_idx - lookback)
    n_pool = int((~np.isnan(ratios[lo:entry_idx]).any(axis=1)).sum())
    if n_pool < MIN_POOL:
        return None
    starts = _block_starts(ratios, lo, entry_idx, block)
    if len(starts) == 0:
        return None

    rng = np.random.default_rng(seed)
    n_blocks = math.ceil(n_bars / block)
    pick = rng.choice(starts, size=(replays, n_blocks))
    rows = (pick[:, :, None] + np.arange(block)).reshape(replays, -1)[:, :n_bars]
    r = ratios[rows]                                              # (replays, n_bars, 4)
    prev = entry * np.cumprod(np.c_[np.ones(replays), r[:, :-1, 3]], axis=1)
    high, low, close = prev * r[..., 1], prev * r[..., 2], prev * r[..., 3]

    hit_stop = (high >= stop) if short else (low <= stop)
    hit_tgt = (low <= target) if short else (high >= target)
    never = n_bars
    f_stop = np.where(hit_stop.any(axis=1), hit_stop.argmax(axis=1), never)
    f_tgt = np.where(hit_tgt.any(axis=1), hit_tgt.argmax(axis=1), never)
    is_stop = (f_stop < never) & (f_stop <= f_tgt)               # a tie is the stop
    is_tgt = (f_tgt < never) & ~is_stop
    is_open = ~is_stop & ~is_tgt

    exit_px = np.where(is_stop, stop, np.where(is_tgt, target, close[:, -1]))
    cost = np.empty(replays)
    cost[is_stop] = cm.round_trip_pct(entry, stop)
    cost[is_tgt] = cm.round_trip_pct(entry, target)
    if is_open.any():
        cost[is_open] = [cm.round_trip_pct(entry, float(x)) for x in exit_px[is_open]]
    gross = (entry - exit_px) if short else (exit_px - entry)
    rr = (gross - entry * cost / 100.0) / risk
    return {"p_target": float(is_tgt.mean()), "p_stop": float(is_stop.mean()),
            "p_open": float(is_open.mean()), "exp_r": float(rr.mean()),
            "n_pool": n_pool, "n_bars": int(n_bars), "replays": int(replays),
            "block": int(block), "seed": int(seed)}
