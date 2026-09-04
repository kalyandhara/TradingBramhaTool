"""funnel_backtest.py — measure the delete-funnel's PRICE legs (B-38 claim).

The claim to test (strategies/TechnoFunda-Delete-Funnel, B-38): does the survivor
set out-perform, forward, both (a) a random bar in the same tape and (b) each
single filter applied alone — i.e. does *stacking* the deletes beat any one of
them? This module answers that for the part that can be answered honestly.

What is and isn't testable — stated up front
--------------------------------------------
Point-in-time replay is only valid for signals computable from data available AT
the bar. The funnel's **price legs (F6 200-DMA, F7 relative strength, F8
accumulation) qualify** — they read only the OHLCV slice up to bar t. The
**fundamental legs (F1–F5) do NOT**: they read yfinance's *current* statements, so
evaluating them at a historical date is look-ahead (survivorship + restatement +
as-of bias). yfinance serves no point-in-time fundamental snapshot, so a true
full-funnel historical backtest is blocked on **data acquisition**, not code.

Therefore this backtest covers the **price sub-funnel** (F6 ∧ F7 ∧ F8) and each of
its legs alone. That is a real, publishable answer to half the claim — "do the
chart footprints the funnel demands actually precede out-performance, and does
requiring all three beat requiring one?" The fundamental half stays an open item.

Method (mirrors backtest.py so the numbers are comparable)
----------------------------------------------------------
For each sampled bar: enter at next open, exit at next-open+h close. A signal bar
is one where the filter PASSES. The **baseline** is every sampled bar (a random
entry in the same tape), identical timing. Edge = mean(signal fwd) − mean(baseline
fwd), with a **Welch two-sample t-test** (signal bars vs baseline bars) so the
edge is quoted with a noise probability, not bare. The filter predicates are
imported from `technofunda_funnel` and evaluated via `build_context`, so the
tested rule is byte-for-byte the shipped rule — no drift.

Live wiring (the caller injects, per the no-Streamlit doctrine):
    from functools import partial
    fetch = lambda s: cached_fetch_ohlcv(s, days=1500)   # DatetimeIndex, o/h/l/c/v
    bench = cached_fetch_nifty50(days=1500)
    res = backtest_price_funnel(symbols, fetch, bench)
    print(format_funnel_backtest(res))
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import pandas as pd

# scipy gives the exact Student-t p-value (as backtest.py uses); it is optional
# here. When absent we fall back to a normal approximation, which is very close
# given the large baseline sample (df is in the hundreds+), so the module runs
# anywhere numpy is present.
try:
    from scipy import stats as _stats
except Exception:                       # pragma: no cover
    _stats = None

import technofunda_funnel as tf

# The three point-in-time-testable legs, in funnel order, plus the AND-combo.
PRICE_LEGS = [
    ("F6", "200 DMA",       tf.f6_trend),
    ("F7", "Rel. strength", tf.f7_rs),
    ("F8", "Accumulation",  tf.f8_accumulation),
]
COMBO_ID = "F6∧F7∧F8"

DEFAULT_HORIZONS = (5, 10, 20, 60)
WARMUP = 260            # ≥252 so the 12-month RS leg has a full lookback
DEFAULT_STRIDE = 5      # sample every 5th bar — cuts autocorrelation and cost


@dataclass
class LegStats:
    fid: str
    label: str
    n: int
    sig_mean: dict[int, float]     # horizon -> mean signal fwd return %
    edge: dict[int, float]         # horizon -> sig_mean - base_mean
    p: dict[int, Optional[float]]  # horizon -> Welch p-value vs baseline


@dataclass
class FunnelBacktest:
    horizons: tuple[int, ...]
    n_symbols: int
    n_baseline: int
    base_mean: dict[int, float]
    legs: list[LegStats]
    combo: LegStats
    primary_h: int


def _bench_trailing_return(bench_df: pd.DataFrame, lookback: int) -> Optional[pd.Series]:
    """Trailing `lookback`-bar fractional return of the benchmark, per date."""
    if bench_df is None or "close" not in bench_df:
        return None
    c = bench_df["close"].dropna()
    if len(c) < lookback + 1:
        return None
    return c.pct_change(lookback)


def _welch_p(sig: list[float], base: np.ndarray) -> Optional[float]:
    """Two-sided Welch (unequal-variance) two-sample p-value: signal vs baseline.

    Uses scipy's exact Student-t survival when available; otherwise a normal
    approximation (2·Φ(−|t|)) via math.erf — accurate here because the baseline
    has hundreds+ of observations, so the t-distribution is essentially normal.
    """
    a = np.asarray(sig, float)
    if len(a) < 4 or len(base) < 4:
        return None
    va, vb = a.var(ddof=1), base.var(ddof=1)
    na, nb = len(a), len(base)
    se2 = va / na + vb / nb
    if se2 <= 0:
        return None
    tstat = (a.mean() - base.mean()) / math.sqrt(se2)
    if _stats is not None:
        # Welch–Satterthwaite df, then exact two-sided t p-value.
        df = se2 ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
        return float(2.0 * _stats.t.sf(abs(tstat), df))
    return float(math.erfc(abs(tstat) / math.sqrt(2.0)))   # 2·Φ(−|t|)


def backtest_price_funnel(symbols: list[str], fetch_fn: Callable,
                          benchmark_df: pd.DataFrame,
                          *, horizons: tuple[int, ...] = DEFAULT_HORIZONS,
                          warmup: int = WARMUP, stride: int = DEFAULT_STRIDE,
                          thresholds: tf.Thresholds | None = None,
                          primary_h: int = 20) -> dict:
    """Replay the price sub-funnel over `symbols` and return edge stats.

    `fetch_fn(symbol) -> OHLCV DataFrame` with a **DatetimeIndex** and lowercase
    o/h/l/c/v (the DatetimeIndex is required so the F7 benchmark return can be
    aligned by date). `benchmark_df` is the Nifty OHLCV frame.
    """
    th = thresholds or tf.Thresholds()
    max_h = max(horizons)
    bench_ret = _bench_trailing_return(benchmark_df, th.rs_lookback)

    base_ret: dict[int, list[float]] = {h: [] for h in horizons}
    leg_ret: dict[str, dict[int, list[float]]] = {
        fid: {h: [] for h in horizons} for fid, _, _ in PRICE_LEGS}
    combo_ret: dict[int, list[float]] = {h: [] for h in horizons}
    n_symbols_used = 0

    for sym in symbols:
        try:
            df = fetch_fn(sym)
        except Exception:
            continue
        if df is None or df.empty or not isinstance(df.index, pd.DatetimeIndex):
            continue
        df = df.dropna(subset=["high", "low", "close", "volume"])
        n = len(df)
        if n < warmup + max_h + 2:
            continue
        n_symbols_used += 1
        openp = (df["open"] if "open" in df else df["close"]).to_numpy(float)
        close = df["close"].to_numpy(float)
        last_eval = n - max_h - 2

        for t in range(warmup, last_eval + 1, stride):
            entry = openp[t + 1]
            if entry <= 0:
                continue
            fwd = {h: (close[t + 1 + h] / entry - 1.0) * 100.0 for h in horizons}
            for h in horizons:
                base_ret[h].append(fwd[h])

            # Point-in-time context: only the slice up to t, plus the benchmark's
            # trailing return AS OF this bar's date (no look-ahead).
            date_t = df.index[t]
            b12 = None
            if bench_ret is not None:
                v = bench_ret.asof(date_t)
                b12 = None if pd.isna(v) else float(v)
            ctx = tf.build_context(sym, price=df.iloc[:t + 1], bench_ret_12m=b12)

            passes = {}
            for fid, _, fn in PRICE_LEGS:
                passes[fid] = fn(ctx, th, strict=True).verdict == tf.PASS
                if passes[fid]:
                    for h in horizons:
                        leg_ret[fid][h].append(fwd[h])
            if all(passes.values()):
                for h in horizons:
                    combo_ret[h].append(fwd[h])

    base_mean = {h: (float(np.mean(base_ret[h])) if base_ret[h] else float("nan"))
                 for h in horizons}

    def _mk(fid, label, ret) -> LegStats:
        return LegStats(
            fid, label, n=len(ret[horizons[0]]),
            sig_mean={h: (float(np.mean(ret[h])) if ret[h] else float("nan")) for h in horizons},
            edge={h: ((float(np.mean(ret[h])) - base_mean[h]) if ret[h] else float("nan"))
                  for h in horizons},
            p={h: _welch_p(ret[h], np.asarray(base_ret[h])) for h in horizons})

    legs = [_mk(fid, label, leg_ret[fid]) for fid, label, _ in PRICE_LEGS]
    combo = _mk(COMBO_ID, "ALL THREE", combo_ret)
    return FunnelBacktest(horizons, n_symbols_used, len(base_ret[horizons[0]]),
                          base_mean, legs, combo, primary_h).__dict__


def format_funnel_backtest(res: dict) -> str:
    """Text report: per-leg edge table + the combo-vs-best-single verdict."""
    fb = FunnelBacktest(**res) if isinstance(res, dict) else res
    H = fb.horizons
    out = [
        "Price sub-funnel backtest  (F6∧F7∧F8 — fundamentals F1–F5 not point-in-time testable)",
        f"symbols used: {fb.n_symbols}   baseline bars: {fb.n_baseline}",
        "",
        "  baseline mean fwd %:  " + "  ".join(f"{h}d {fb.base_mean[h]:+.2f}" for h in H),
        "",
        f"  {'leg':<16}{'n':>7}   " + "  ".join(f"{h}d edge (p)".rjust(15) for h in H),
        "  " + "─" * (16 + 7 + 3 + 17 * len(H)),
    ]

    def _row(s: LegStats) -> str:
        cells = []
        for h in H:
            e = s.edge.get(h)
            p = s.p.get(h)
            es = "  n/a" if e is None or (isinstance(e, float) and np.isnan(e)) else f"{e:+.2f}"
            ps = "" if p is None else f" ({p:.2f})"
            star = " *" if (p is not None and p < 0.05) else ""
            cells.append(f"{es}{ps}{star}".rjust(15))
        return f"  {s.fid+' '+s.label:<16}{s.n:>7}   " + "  ".join(cells)

    for s in fb.legs:
        out.append(_row(s))
    out.append(_row(fb.combo))

    # The claim: does stacking beat the best single leg at the primary horizon?
    ph = fb.primary_h
    singles = [(s.fid, s.edge.get(ph)) for s in fb.legs
               if s.edge.get(ph) is not None and not np.isnan(s.edge.get(ph))]
    combo_e = fb.combo.edge.get(ph)
    out += ["", f"Claim @ {ph}d — does F6∧F7∧F8 beat the best single leg?"]
    if singles and combo_e is not None and not np.isnan(combo_e):
        best_fid, best_e = max(singles, key=lambda x: x[1])
        verdict = ("YES — stacking adds edge" if combo_e > best_e
                   else "NO — the combo does not beat the best single leg")
        out.append(f"  combo {combo_e:+.2f}  vs  best single {best_fid} {best_e:+.2f}   → {verdict}")
        cp = fb.combo.p.get(ph)
        out.append(f"  combo edge significance: " +
                   ("n/a" if cp is None else f"p={cp:.3f}" + (" (significant)" if cp < 0.05 else " (not significant)")))
    else:
        out.append("  insufficient signals to judge (widen symbols/history or lower stride)")
    out.append("")
    out.append("* = Welch p<0.05 vs baseline. Edge is mean signal fwd − mean baseline fwd (%).")
    return "\n".join(out)


# ──────────────────────────────────────────────────────────────────────────────
# Synthetic MACHINERY CHECK — no network. Proves the replay/stat wiring runs and
# the report renders; the numbers are from fabricated series and mean nothing.
# Real results require the live wiring in the module docstring.
# ──────────────────────────────────────────────────────────────────────────────
def _demo() -> dict:
    rng = np.random.default_rng(7)
    dates = pd.date_range("2019-01-01", periods=900, freq="B")

    def make(strength: float) -> pd.DataFrame:
        # A drifting series; higher `strength` = cleaner uptrend + up-volume.
        steps = rng.normal(0.0004 * (1 + strength), 0.012 - 0.004 * strength, len(dates))
        close = 100 * np.exp(np.cumsum(steps))
        high = close * (1 + np.abs(rng.normal(0, 0.006, len(dates))))
        low = close * (1 - np.abs(rng.normal(0, 0.006, len(dates))))
        chg = np.diff(close, prepend=close[0])
        vol = np.where(chg > 0, 1.5e5, 0.7e5) * (1 + strength * 0.3)
        return pd.DataFrame({"open": close, "high": high, "low": low,
                             "close": close, "volume": vol}, index=dates)

    symbols = {f"STRONG{i}": make(1.0) for i in range(4)}
    symbols.update({f"WEAK{i}": make(0.0) for i in range(4)})
    bench = make(0.4)   # a middling benchmark so RS separates strong from weak
    return backtest_price_funnel(list(symbols), lambda s: symbols[s], bench,
                                 stride=5)


if __name__ == "__main__":   # py -3 tools/funnel_backtest.py
    print(format_funnel_backtest(_demo()))
    print("\n(Synthetic machinery check — numbers are fabricated. See the module "
          "docstring for live wiring.)")
