"""adx_di_backtest.py — measure ADX/DI rule variants, point-in-time.

Companion to concepts/ADX.md's measured-evidence section: a permanent, re-runnable
harness for the ADX/DI *rules* (which are not registered scanners), so the claim
"DI crosses are lagging, the confirmed state is neutral" can be re-measured on any
universe instead of quoted from one run.

Rules measured (bullish = long entry test; bearish = downside/short-avoid test):
    di_cross_bull          +DI crosses above −DI (bare)
    state_bull_adx_rising  +DI>−DI AND ADX≥25 AND rising  (the ADX Trend
                           Confirmation scanner's exact state)
    di_cross_bear          −DI crosses above +DI (bare)
    state_bear_adx         −DI>+DI AND ADX≥25            (the Downside-Risk
                           directional confirmation)

Method mirrors backtest.py / funnel_backtest.py: enter next open, exit
next-open+h close; edge = signal mean fwd − every-bar baseline mean fwd; a Welch
two-sample p-value (scipy-optional via funnel_backtest._welch_p). The indicator is
the repo's own `scanner_templates._adx_di_series` (Wilder, causal → indexing at t
is look-ahead-free), so the tested rule is the shipped rule.

Note on interpretation: a bullish rule's edge is measured as a plain long forward
return; a *bearish* rule's forward return being BELOW baseline is the "signal
works" direction (the name underperforms after the flag), so read bearish edges
with the sign flipped — a negative edge there means the downside flag had teeth.

Live use (inject the fetcher, per the no-Streamlit doctrine):
    import screener_pipeline as sp, adx_di_backtest as ab
    print(ab.format_report(ab.backtest_adx_di(ab.DEFAULT_UNIVERSE,
                                              lambda s: sp.fetch_ohlcv(s, days=1500))))
"""

from __future__ import annotations

from typing import Callable

import numpy as np

import scanner_templates as sc
from funnel_backtest import _welch_p

DEFAULT_HORIZONS = (5, 10, 20, 60)
WARMUP = 40           # ADX needs ~2n(=28) bars to settle; 40 is a safe floor
DEFAULT_STRIDE = 5    # sample every 5th bar to cut autocorrelation
ADX_TREND = 25.0

#: A liquid default universe (same set used for the funnel price-legs test, so the
#: two findings are comparable). Callers can pass any list.
DEFAULT_UNIVERSE = [
    "RELIANCE", "TITAN", "CDSL", "KPITTECH", "PERSISTENT", "INFY", "TCS",
    "HDFCBANK", "ICICIBANK", "LT", "BEL", "IRFC", "TATAPOWER", "SUNPHARMA",
    "DIVISLAB", "PIDILITIND", "BAJFINANCE", "ASIANPAINT", "NESTLEIND", "HAVELLS",
]

# Each rule: (pdi, mdi, adx, i) -> bool, evaluated at bar i (all arrays finite there).
RULES: dict[str, Callable] = {
    "di_cross_bull":         lambda p, m, a, i: p[i - 1] <= m[i - 1] and p[i] > m[i],
    "state_bull_adx_rising": lambda p, m, a, i: p[i] > m[i] and a[i] >= ADX_TREND and a[i] > a[i - 1],
    "di_cross_bear":         lambda p, m, a, i: m[i - 1] <= p[i - 1] and m[i] > p[i],
    "state_bear_adx":        lambda p, m, a, i: m[i] > p[i] and a[i] >= ADX_TREND,
}
BEARISH = {"di_cross_bear", "state_bear_adx"}


def backtest_adx_di(symbols: list[str], fetch_fn: Callable, *,
                    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
                    warmup: int = WARMUP, stride: int = DEFAULT_STRIDE) -> dict:
    """Replay the ADX/DI rules over `symbols` and return per-rule edge stats.

    `fetch_fn(symbol) -> OHLCV DataFrame` with high/low/close (+ open preferred).
    """
    max_h = max(horizons)
    base = {h: [] for h in horizons}
    sig = {r: {h: [] for h in horizons} for r in RULES}
    n_used = 0

    for s in symbols:
        try:
            df = fetch_fn(s)
        except Exception:
            continue
        if df is None or len(df) < warmup + max_h + 3 or "close" not in df:
            continue
        df = df.dropna(subset=["high", "low", "close"]).reset_index(drop=True)
        n = len(df)
        if n < warmup + max_h + 3:
            continue
        openp = (df["open"] if "open" in df else df["close"]).to_numpy(float)
        close = df["close"].to_numpy(float)
        pdi, mdi, adx = (x.to_numpy(float) for x in sc._adx_di_series(df))
        n_used += 1
        last_eval = n - max_h - 2
        last_fire = {r: -(10 ** 9) for r in RULES}

        for t in range(warmup, last_eval + 1, stride):
            entry = openp[t + 1]
            if entry <= 0:
                continue
            fwd = {h: (close[t + 1 + h] / entry - 1.0) * 100.0 for h in horizons}
            for h in horizons:
                base[h].append(fwd[h])
            if not all(np.isfinite(v) for v in (pdi[t], mdi[t], adx[t], pdi[t - 1], adx[t - 1])):
                continue
            for r, fn in RULES.items():
                if fn(pdi, mdi, adx, t) and t - last_fire[r] >= stride:
                    last_fire[r] = t
                    for h in horizons:
                        sig[r][h].append(fwd[h])

    bmean = {h: (float(np.mean(base[h])) if base[h] else float("nan")) for h in horizons}
    rules_out = {}
    for r in RULES:
        rules_out[r] = {
            "n": len(sig[r][horizons[0]]),
            "edge": {h: ((float(np.mean(sig[r][h])) - bmean[h]) if sig[r][h] else float("nan"))
                     for h in horizons},
            "p": {h: _welch_p(sig[r][h], np.asarray(base[h])) for h in horizons},
            "bearish": r in BEARISH,
        }
    return {"horizons": horizons, "n_symbols": n_used,
            "n_baseline": len(base[horizons[0]]), "base_mean": bmean, "rules": rules_out}


def format_report(res: dict) -> str:
    H = res["horizons"]
    out = [
        "ADX/DI rule backtest  (point-in-time; edge = signal mean fwd − baseline mean fwd %)",
        f"symbols used: {res['n_symbols']}   baseline bars: {res['n_baseline']}",
        "  baseline mean fwd %:  " + "  ".join(f"{h}d {res['base_mean'][h]:+.2f}" for h in H),
        "",
        f"  {'rule':<24}{'n':>6}   " + "  ".join(f"{h}d edge (p)".rjust(16) for h in H),
        "  " + "─" * (24 + 6 + 3 + 18 * len(H)),
    ]
    for r, st in res["rules"].items():
        cells = []
        for h in H:
            e, p = st["edge"][h], st["p"][h]
            if e is None or (isinstance(e, float) and np.isnan(e)):
                cells.append("n/a".rjust(16))
            else:
                star = " *" if (p is not None and p < 0.05) else ""
                cells.append(f"{e:+.2f} ({'n/a' if p is None else f'{p:.2f}'}){star}".rjust(16))
        tag = " [bear]" if st["bearish"] else ""
        out.append(f"  {r+tag:<24}{st['n']:>6}   " + "  ".join(cells))
    out += [
        "",
        "* = Welch p<0.05 vs baseline. For [bear] rules a NEGATIVE edge = the flag",
        "worked (the name underperformed after it). See concepts/ADX.md.",
    ]
    return "\n".join(out)


# ── synthetic machinery check (no network) ────────────────────────────────────
def _demo() -> dict:
    import pandas as pd
    rng = np.random.default_rng(11)

    def make(drift):
        n = 500
        idx = pd.date_range("2022-01-01", periods=n, freq="B")
        c = 100 * np.exp(np.cumsum(rng.normal(drift, 0.012, n)))
        h = c * (1 + np.abs(rng.normal(0, 0.006, n)))
        l = c * (1 - np.abs(rng.normal(0, 0.006, n)))
        return pd.DataFrame({"open": c, "high": h, "low": l, "close": c,
                             "volume": np.full(n, 1e5)}, index=idx)

    syms = {f"UP{i}": make(0.0008) for i in range(4)}
    syms.update({f"DN{i}": make(-0.0006) for i in range(4)})
    return backtest_adx_di(list(syms), lambda s: syms[s])


if __name__ == "__main__":
    import sys
    if "--live" in sys.argv:
        import screener_pipeline as sp
        res = backtest_adx_di(DEFAULT_UNIVERSE, lambda s: sp.fetch_ohlcv(s, days=1500))
    else:
        res = _demo()
        print("(synthetic machinery check — run with --live for real data)\n")
    print(format_report(res))
