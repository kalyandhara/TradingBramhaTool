"""regime_backtest.py — measure the RISK-OFF premise that gates B-32 / B-33.

The claim (Open-Backlog B-32): *does following the shortlist in RISK-OFF
underperform RISK-ON out-of-sample?* If a scanner's edge survives in RISK-OFF,
throttling output there is NOT earned — you'd just be cutting signals that still
work. If the edge collapses (or flips) in RISK-OFF, the throttle is justified and
B-33's conviction-gate has something to gate on.

The measurement that matters is **regime-matched edge**, not raw return. Of course
the tape is worse below the 200 SMA — that is market beta, and cutting longs in a
downtrend is just position sizing. The throttle is only *earned* if the signal
adds LESS over a random RISK-OFF bar than over a random RISK-ON bar. So for each
regime we compare signal-fired forward returns to the baseline of *every bar in
that same regime*.

Regime mirrors opportunity_daily._market_context exactly, computed point-in-time
on the Nifty (causal rolling SMAs, no look-ahead):
    RISK-ON  : close > SMA200 AND close > SMA50
    RISK-OFF : close < SMA200
    MIXED    : else (above 200, below 50)

Signals are real registered bullish scanners (cheap ones) + a composite "any
fired", the closest proxy for the daily shortlist's long tilt. Welch two-sample
p-value via funnel_backtest._welch_p (scipy-optional).

Live use:
    import screener_pipeline as sp, regime_backtest as rb
    nifty = sp.fetch_nifty50(days=1500)
    print(rb.format_report(rb.backtest_by_regime(rb.DEFAULT_UNIVERSE,
              lambda s: sp.fetch_ohlcv(s, days=1500), nifty)))
"""

from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

import scanner_templates as sc
from funnel_backtest import _welch_p

DEFAULT_HORIZONS = (10, 20, 60)
WARMUP = 210          # 200 SMA + headroom
DEFAULT_STRIDE = 5
REGIMES = ("RISK-ON", "MIXED", "RISK-OFF")

#: Cheap bullish scanners (avoid the expensive VCP/harmonic detectors here).
SIGNALS: dict[str, Callable] = {
    "52w_high":  sc.scan_52w_high_leaders,
    "stage2":    sc.scan_stage2_uptrend,
    "pullback":  sc.scan_pullback_to_ema,
    "momentum":  sc.scan_momentum_continuation,
}
COMPOSITE = "ANY_bullish"

DEFAULT_UNIVERSE = [
    "RELIANCE", "TITAN", "CDSL", "KPITTECH", "PERSISTENT", "INFY", "TCS",
    "HDFCBANK", "ICICIBANK", "LT", "BEL", "IRFC", "TATAPOWER", "SUNPHARMA",
    "DIVISLAB", "PIDILITIND", "BAJFINANCE", "ASIANPAINT", "NESTLEIND", "HAVELLS",
    "MARUTI", "TRENT", "DMART", "ITC", "AXISBANK", "WIPRO", "ULTRACEMCO",
    "TATASTEEL", "JSWSTEEL", "COALINDIA",
]


def nifty_regime_series(nifty_df: pd.DataFrame) -> pd.Series:
    """Point-in-time regime label per Nifty bar (causal SMAs)."""
    c = nifty_df["close"].astype(float)
    sma200 = c.rolling(200).mean()
    sma50 = c.rolling(50).mean()
    lab = np.where(sma200.isna(), "UNKNOWN",
          np.where((c > sma200) & (c > sma50), "RISK-ON",
          np.where(c < sma200, "RISK-OFF", "MIXED")))
    return pd.Series(lab, index=nifty_df.index)


def backtest_by_regime(symbols: list[str], fetch_fn: Callable, nifty_df: pd.DataFrame,
                       *, horizons: tuple[int, ...] = DEFAULT_HORIZONS,
                       warmup: int = WARMUP, stride: int = DEFAULT_STRIDE) -> dict:
    reg = nifty_regime_series(nifty_df)
    max_h = max(horizons)
    # base[regime][h] and sig[name][regime][h]
    base = {r: {h: [] for h in horizons} for r in REGIMES}
    names = list(SIGNALS) + [COMPOSITE]
    sig = {nm: {r: {h: [] for h in horizons} for r in REGIMES} for nm in names}
    n_used = 0

    for s in symbols:
        try:
            df = fetch_fn(s)
        except Exception:
            continue
        if df is None or len(df) < warmup + max_h + 3 or not isinstance(df.index, pd.DatetimeIndex):
            continue
        df = df.dropna(subset=["high", "low", "close"])
        n = len(df)
        if n < warmup + max_h + 3:
            continue
        openp = (df["open"] if "open" in df else df["close"]).to_numpy(float)
        close = df["close"].to_numpy(float)
        n_used += 1
        last_eval = n - max_h - 2
        last_fire = {nm: -(10 ** 9) for nm in names}

        for t in range(warmup, last_eval + 1, stride):
            entry = openp[t + 1]
            if entry <= 0:
                continue
            r = reg.asof(df.index[t])
            if r not in REGIMES:
                continue
            fwd = {h: (close[t + 1 + h] / entry - 1.0) * 100.0 for h in horizons}
            for h in horizons:
                base[r][h].append(fwd[h])
            fired_any = False
            slc = df.iloc[:t + 1]
            for nm, fn in SIGNALS.items():
                try:
                    hit = fn(slc) is not None
                except Exception:
                    hit = False
                if hit:
                    fired_any = True
                    if t - last_fire[nm] >= stride:
                        last_fire[nm] = t
                        for h in horizons:
                            sig[nm][r][h].append(fwd[h])
            if fired_any and t - last_fire[COMPOSITE] >= stride:
                last_fire[COMPOSITE] = t
                for h in horizons:
                    sig[COMPOSITE][r][h].append(fwd[h])

    # Aggregate
    base_mean = {r: {h: (float(np.mean(base[r][h])) if base[r][h] else float("nan"))
                     for h in horizons} for r in REGIMES}
    base_n = {r: len(base[r][horizons[0]]) for r in REGIMES}
    out_sig = {}
    for nm in names:
        out_sig[nm] = {}
        for r in REGIMES:
            out_sig[nm][r] = {
                "n": len(sig[nm][r][horizons[0]]),
                "edge": {h: ((float(np.mean(sig[nm][r][h])) - base_mean[r][h])
                             if sig[nm][r][h] and not np.isnan(base_mean[r][h]) else float("nan"))
                         for h in horizons},
                "p": {h: _welch_p(sig[nm][r][h], np.asarray(base[r][h])) for h in horizons},
            }
    return {"horizons": horizons, "n_symbols": n_used, "regimes": REGIMES,
            "base_mean": base_mean, "base_n": base_n, "signals": out_sig}


def format_report(res: dict) -> str:
    H = res["horizons"]
    R = res["regimes"]
    out = ["Regime-conditioned edge — does the shortlist's edge survive RISK-OFF? (B-32/B-33)",
           f"symbols used: {res['n_symbols']}", ""]
    # Baseline (market beta) per regime.
    out.append("Baseline mean fwd % (every bar in regime) — this is market beta, not edge:")
    for r in R:
        cells = "  ".join(f"{h}d {res['base_mean'][r][h]:+.2f}" for h in H)
        out.append(f"  {r:<9} n={res['base_n'][r]:>6}   {cells}")
    out.append("")
    out.append("Signal EDGE over a regime-matched random bar (the number that earns the throttle):")
    out.append(f"  {'signal':<12}{'regime':<10}{'n':>7}   " + "  ".join(f"{h}d edge (p)".rjust(15) for h in H))
    out.append("  " + "─" * (12 + 10 + 7 + 3 + 17 * len(H)))
    for nm in list(SIGNALS) + [COMPOSITE]:
        for r in R:
            st = res["signals"][nm][r]
            cells = []
            for h in H:
                e, p = st["edge"][h], st["p"][h]
                if e is None or (isinstance(e, float) and np.isnan(e)):
                    cells.append("n/a".rjust(15))
                else:
                    star = " *" if (p is not None and p < 0.05) else ""
                    cells.append(f"{e:+.2f} ({'n/a' if p is None else f'{p:.2f}'}){star}".rjust(15))
            out.append(f"  {nm:<12}{r:<10}{st['n']:>7}   " + "  ".join(cells))
        out.append("")

    # Headline verdict at the primary (middle) horizon.
    ph = H[len(H) // 2]
    comp = res["signals"][COMPOSITE]
    on_e = comp["RISK-ON"]["edge"].get(ph)
    off_e = comp["RISK-OFF"]["edge"].get(ph)
    out.append(f"VERDICT @ {ph}d (composite 'any bullish scanner'):")
    if on_e is not None and off_e is not None and not (np.isnan(on_e) or np.isnan(off_e)):
        gap = on_e - off_e
        if off_e <= 0 and on_e > 0:
            v = "PREMISE HOLDS — edge is positive in RISK-ON, gone/negative in RISK-OFF → throttle earned."
        elif gap > 0.3:
            v = "PARTIAL — edge shrinks in RISK-OFF but is not gone; a soft throttle, not a kill."
        else:
            v = "PREMISE FAILS — edge is similar across regimes → throttling cuts signals that still work."
        out.append(f"  RISK-ON edge {on_e:+.2f} vs RISK-OFF edge {off_e:+.2f} (gap {gap:+.2f}) → {v}")
    else:
        out.append("  insufficient signals in one regime — widen universe/history.")
    return "\n".join(out)


if __name__ == "__main__":
    import screener_pipeline as sp
    nifty = sp.fetch_nifty50(days=1500)
    res = backtest_by_regime(DEFAULT_UNIVERSE, lambda s: sp.fetch_ohlcv(s, days=1500), nifty)
    print(format_report(res))
