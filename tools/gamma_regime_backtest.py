"""gamma_regime_backtest.py — does the gamma regime actually predict anything?

The measurable claim behind B-44, tested before any of this reaches a dashboard.

The mechanism in `gamma_exposure.py` makes a specific, falsifiable prediction, and it is
about VOLATILITY, not direction:

    negative dealer gamma -> hedging amplifies moves -> HIGHER realised vol
    positive dealer gamma -> hedging damps moves     -> LOWER realised vol, failed breakouts

So the tests are, in order of how directly they probe the mechanism:

  A. Forward realised volatility (5/10/20d) by regime      <- the core claim
  B. Next-day absolute move by regime                      <- same claim, 1-day horizon
  C. Forward DIRECTIONAL return by regime                  <- expected NULL; GEX is not
                                                              a direction signal, and if
                                                              this fires it needs an
                                                              explanation, not a victory lap
  D. Same splits on the net/gross TERCILE rather than the bare sign
  E. 20-day-high breakouts: do they follow through less in positive gamma?

── Two design points that decide whether the answer means anything ───────────

**Look-ahead.** A day's GEX comes from that day's END-OF-DAY bhavcopy, published after
the close. It cannot be acted on until the NEXT session. Every forward window here
therefore starts at t+1, never at t. This is the single easiest way to fake a result in
this study and it is closed by construction.

**The thin-residual problem.** Net GEX is a small difference between two large,
nearly-cancelling sides (measured: NIFTY net 3,498 Cr against ~168,000 Cr gross, ~2%).
The regime LABEL therefore rests on a couple of percent of the profile, and is sensitive
to the naive customer/dealer convention and to which strikes survived IV inversion. That
is why test D exists: if the sign split is noise but the tercile split is not, the
mechanism may be real while the zero-crossing is the wrong threshold. And if the sign is
almost always the same, the CONVENTION is producing the reading rather than the market —
which the report says out loud rather than burying.

Price comes from the GEX cache's own `spot` field (`UndrlygPric` on the same bhavcopy
row), so the price series and the signal series are aligned to the same sessions by
construction, with no second source to drift.

CLI:
  py -3 tools/gamma_regime_backtest.py                  # NIFTY
  py -3 tools/gamma_regime_backtest.py --symbol BANKNIFTY
"""

from __future__ import annotations

import argparse
import math
import sys

import numpy as np

import gamma_exposure as gx
from funnel_backtest import _welch_p

VOL_HORIZONS = (5, 10, 20)
RET_HORIZONS = (1, 5, 10, 20)
BREAKOUT_LOOKBACK = 20
TRADING_DAYS = 252


def _load_aligned(symbol: str):
    """(dates, spot, net_gex, net_to_gross) in chronological order."""
    ser = gx.load_series(symbol)
    if not ser:
        sys.exit(f"no cached GEX for {symbol} — run: py -3 tools/gamma_exposure.py --history 480")
    dates = sorted(ser)
    spot = np.array([ser[d]["spot"] for d in dates], float)
    net = np.array([ser[d]["net_gex_cr"] for d in dates], float)
    n2g = np.array([ser[d].get("net_to_gross", 0.0) for d in dates], float)
    return dates, spot, net, n2g


def _fwd_realised_vol(spot: np.ndarray, t: int, h: int) -> float | None:
    """Annualised stdev of close-to-close log returns over sessions t+1 .. t+h.

    Starts at t+1: the GEX reading for day t is only actionable from the next session.
    """
    if t + h + 1 > len(spot) - 1:
        return None
    seg = spot[t + 1: t + h + 2]
    if len(seg) < 3 or (seg <= 0).any():
        return None
    rets = np.diff(np.log(seg))
    return float(rets.std(ddof=1) * math.sqrt(TRADING_DAYS) * 100.0)


def _fwd_return(spot: np.ndarray, t: int, h: int) -> float | None:
    """Percent return from the NEXT session's level to h sessions after that."""
    if t + 1 + h > len(spot) - 1:
        return None
    a, b = spot[t + 1], spot[t + 1 + h]
    if not (a > 0):
        return None
    return float((b / a - 1.0) * 100.0)


def _split_stats(name_a: str, vals_a: list[float],
                 name_b: str, vals_b: list[float]) -> dict:
    a, b = np.asarray(vals_a, float), np.asarray(vals_b, float)
    return {
        "n_a": len(a), "n_b": len(b),
        "mean_a": float(a.mean()) if len(a) else float("nan"),
        "mean_b": float(b.mean()) if len(b) else float("nan"),
        "diff": (float(a.mean() - b.mean()) if len(a) and len(b) else float("nan")),
        "p": _welch_p(list(a), b) if len(a) >= 4 and len(b) >= 4 else None,
        "name_a": name_a, "name_b": name_b,
    }


def _rotation_p(values: np.ndarray, labels: np.ndarray) -> float | None:
    """Exact circular-rotation p-value for the group-mean difference.

    Welch is WRONG here and the first dry run showed exactly how wrong: with daily
    sampling and a 20-day forward window, consecutive observations share 19/20 of their
    data, so the independence assumption fails and p-values come out far too small. On
    100 sessions the directional test — the one predicted to be NULL — printed p=0.013
    purely on that artefact.

    The fix keeps both series exactly as they are and only moves their alignment: for
    every circular shift of the LABEL vector, recompute the same statistic. Rotation
    preserves the autocorrelation of the labels AND of the outcomes, so the null
    distribution it generates is "this regime series, offset in time" — which is the
    honest null for "does the regime label carry information beyond its own persistence".

    Every shift is enumerated rather than sampled, so there is no seed and no Monte-Carlo
    error; p is exact given the data. Returns None when either group is too small.

    `values` may contain NaN for sessions with no forward window; those drop out of
    whichever group they land in, on every shift.
    """
    n = len(labels)
    if n < 20:
        return None
    valid = np.isfinite(values)
    obs = None
    stats = []
    for s in range(n):
        cat = np.roll(labels, s)
        ga = values[valid & (cat == A_GROUP)]
        gb = values[valid & (cat == B_GROUP)]
        if len(ga) < 4 or len(gb) < 4:
            continue
        d = float(ga.mean() - gb.mean())
        if s == 0:
            obs = d
        stats.append(abs(d))
    if obs is None or len(stats) < 20:
        return None
    return float(np.mean(np.asarray(stats) >= abs(obs)))


#: Group codes used by the rotation test and by `_paired`. A third code (SKIP) lets a
#: three-way split (the net/gross terciles) reuse the same machinery: the middle group is
#: carried through the rotation so the label series keeps its real composition, but never
#: enters either arm of the comparison.
A_GROUP, B_GROUP, SKIP_GROUP = 1, 0, 2


def _paired(values: np.ndarray, cats: np.ndarray, name_a: str, name_b: str) -> dict:
    """Split-stats + the rotation p-value, from aligned value/category arrays."""
    valid = np.isfinite(values)
    st = _split_stats(name_a, list(values[valid & (cats == A_GROUP)]),
                      name_b, list(values[valid & (cats == B_GROUP)]))
    st["p_rot"] = _rotation_p(values, cats)
    return st


def run(symbol: str = "NIFTY") -> dict:
    dates, spot, net, n2g = _load_aligned(symbol)
    n = len(dates)

    # Category vector for the sign split: A = negative gamma (the "amplified" arm, so a
    # POSITIVE diff supports the mechanism), B = positive gamma.
    sign_cat = np.where(net > 0, B_GROUP, A_GROUP)

    def vol_series(h: int) -> np.ndarray:
        return np.array([_fwd_realised_vol(spot, t, h) if _fwd_realised_vol(spot, t, h)
                         is not None else np.nan for t in range(n)], float)

    def ret_series(h: int, absolute: bool = False) -> np.ndarray:
        out = np.full(n, np.nan)
        for t in range(n):
            r = _fwd_return(spot, t, h)
            if r is not None:
                out[t] = abs(r) if absolute else r
        return out

    out: dict = {"symbol": symbol, "n_sessions": n,
                 "span": (dates[0], dates[-1]) if dates else (None, None),
                 "n_pos": int((net > 0).sum()), "n_neg": int((net <= 0).sum())}

    # ── A. forward realised vol by regime sign ────────────────────────────────
    out["vol_by_sign"] = {h: _paired(vol_series(h), sign_cat,
                                     "negative-gamma", "positive-gamma")
                          for h in VOL_HORIZONS}

    # ── B. next-day absolute move (non-overlapping by construction) ───────────
    out["absmove_by_sign"] = _paired(ret_series(1, absolute=True), sign_cat,
                                     "negative-gamma", "positive-gamma")

    # ── C. directional forward return (expected null) ─────────────────────────
    out["ret_by_sign"] = {h: _paired(ret_series(h), sign_cat,
                                     "negative-gamma", "positive-gamma")
                          for h in RET_HORIZONS}

    # ── D. tercile split on net/gross, since the sign is a thin residual ──────
    out["vol_by_tercile"] = {}
    if n >= 30:
        lo_cut, hi_cut = np.percentile(n2g, [33.3, 66.7])
        # A = lowest net/gross (most negative-leaning), B = highest, middle carried
        # through the rotation as SKIP so the label series keeps its real composition.
        terc = np.full(n, SKIP_GROUP)
        terc[n2g <= lo_cut] = A_GROUP
        terc[n2g >= hi_cut] = B_GROUP
        out["vol_by_tercile"] = {h: _paired(vol_series(h), terc,
                                            "lowest net/gross tercile",
                                            "highest net/gross tercile")
                                 for h in VOL_HORIZONS}
        out["tercile_cuts"] = (float(lo_cut), float(hi_cut))

    # ── E. breakout follow-through by regime ─────────────────────────────────
    # A 20-day-high close is the crudest possible breakout, deliberately: the claim
    # under test is about the ENVIRONMENT, so the event should carry no cleverness of
    # its own that could explain the result instead. Non-breakout sessions are NaN, so
    # they drop out of both arms while the label series stays intact for the rotation.
    out["breakout"] = {}
    for h in (5, 10):
        vals = ret_series(h).copy()
        for t in range(n):
            if t < BREAKOUT_LOOKBACK or spot[t] < spot[t - BREAKOUT_LOOKBACK:t].max():
                vals[t] = np.nan
        out["breakout"][h] = _paired(vals, sign_cat,
                                     "breakout in negative gamma",
                                     "breakout in positive gamma")
    return out


def _fmt(st: dict, unit: str = "%") -> str:
    """One row. p_rot is the headline; Welch is shown beside it, marked optimistic."""
    pr = st.get("p_rot")
    pw = st.get("p")
    rot = "n/a" if pr is None else f"{pr:.3f}"
    wel = "n/a" if pw is None else f"{pw:.3f}"
    star = " *" if (pr is not None and pr < 0.05) else ""
    return (f"{st['name_a']:<26}{st['mean_a']:>8.2f}{unit} (n={st['n_a']:>4})  "
            f"{st['name_b']:<26}{st['mean_b']:>8.2f}{unit} (n={st['n_b']:>4})  "
            f"diff {st['diff']:>+6.2f}  p_rot={rot}{star}  (welch {wel})")


def format_report(res: dict) -> str:
    L = [
        f"Gamma-regime study - {res['symbol']}   {res['n_sessions']} sessions  "
        f"{res['span'][0]} .. {res['span'][1]}",
        f"regime days: positive {res['n_pos']}   negative {res['n_neg']}",
        "all forward windows start at t+1 (the EOD reading is not actionable until the next session)",
        "",
        "A. FORWARD REALISED VOLATILITY (annualised %) - the mechanism's core prediction:",
        "   negative gamma should be HIGHER (diff > 0 supports the mechanism)",
    ]
    for h, st in res["vol_by_sign"].items():
        L.append(f"   {h:>2}d  " + _fmt(st))

    L += ["", "B. NEXT-DAY ABSOLUTE MOVE (%) - same claim at a 1-day horizon:",
          "       " + _fmt(res["absmove_by_sign"])]

    L += ["", "C. DIRECTIONAL FORWARD RETURN (%) - expected NULL (GEX is not a direction signal):"]
    for h, st in res["ret_by_sign"].items():
        L.append(f"   {h:>2}d  " + _fmt(st))

    if res.get("vol_by_tercile"):
        lo, hi = res["tercile_cuts"]
        L += ["", f"D. FORWARD REALISED VOL by net/gross TERCILE (cuts {lo:+.3f} / {hi:+.3f}) -",
              "   the sign is a thin residual, so this asks whether the EXTREMES separate:"]
        for h, st in res["vol_by_tercile"].items():
            L.append(f"   {h:>2}d  " + _fmt(st))

    L += ["", "E. 20-DAY-HIGH BREAKOUT follow-through (%) - positive gamma should be WORSE",
          "   (diff > 0 supports 'breakouts fail in positive gamma'):"]
    for h, st in res["breakout"].items():
        L.append(f"   {h:>2}d  " + _fmt(st))

    L += ["",
          "p_rot = EXACT circular-rotation p (every shift of the label series enumerated);",
          "it is the headline because forward windows overlap and Welch's independence",
          "assumption fails there - compare the two columns to see the size of that gap.",
          "* marks p_rot < 0.05. Sign convention is NAIVE (dealers long calls / short puts);",
          "if these are null, that assumption is the first suspect - see gamma_exposure.py."]

    # The honest headline, computed rather than asserted.
    share = res["n_pos"] / max(res["n_sessions"], 1)
    if share > 0.9 or share < 0.1:
        L += ["",
              f"!! WARNING: {share:.0%} of sessions carry the same sign. At that imbalance the",
              "   naive convention, not the market, is producing the regime label - the sign",
              "   split below is close to meaningless and test D is the one to read."]
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description="Test the GEX regime split (B-44)")
    ap.add_argument("--symbol", default="NIFTY")
    args = ap.parse_args()
    print(format_report(run(args.symbol)))


if __name__ == "__main__":
    main()
