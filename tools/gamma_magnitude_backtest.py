"""
gamma_magnitude_backtest.py — B-44r: the naive convention as the suspect.

B-44 measured dealer gamma the US way: customers buy puts and sell calls, so dealers
are long call gamma and short put gamma, and the SIGN of net GEX labels the regime.
That returned a clean null on 480 NSE sessions.

B-44r is the pre-registered alternative, and it is a DIFFERENT measurement rather than
a re-run. Indian index options plausibly invert the US retail structure: retail is a
heavy BUYER of cheap weekly OTM options on both sides, with prop desks and institutions
writing them. If dealers are short gamma on BOTH sides then:

  * net gamma is unconditionally negative, so its sign carries no information at all,
    and the 70% (NIFTY) / 85% (BANKNIFTY) positive-gamma day count B-44 measured is the
    convention talking rather than the market;
  * the quantity that predicts anything is the MAGNITUDE of the dealer book. A bigger
    short-gamma position means more hedging flow in the direction of the move, so more
    amplification.

The magnitude that survives the convention change is `gross_gex_cr` — the sum of
absolute gamma notional across every strike, which `compute_gex` already persists. That
is why this needs no re-download: the backlog assumed a fresh 480-session pass over the
raw chains, but the aggregate the alternative convention needs was already in the cache.

── PRE-REGISTRATION (written before the first run) ──────────────────────────────────

PRIMARY test, one hypothesis, decided in advance:
    predictor  trailing percentile of gross gamma over a 60-session window
    split      above vs below the median percentile
    outcome    forward 5-day realised volatility
    direction  HIGH gross gamma -> HIGHER forward vol
    statistic  exact circular-rotation p-value (Welch printed alongside, not used)

SECONDARY, reported for completeness and NOT eligible to carry the conclusion:
    the same split against 10d and 20d forward vol and next-day absolute move;
    top vs bottom tercile of the same percentile; and the raw gross/spot level split
    at its median.

EXPECTED NULL, a falsification check on the harness itself:
    forward directional return. Magnitude must not predict direction. If it does, the
    machinery is broken, not the market.

ROBUSTNESS, because gamma mechanically spikes into expiry:
    the primary test re-run within a single weekday. If the weekly expiry cycle is
    driving the split, it dies here.

-- ADDED AFTER THE FIRST RUN (post-hoc, and labelled as such) -----------------------

The first run falsified the pre-registered DIRECTION - high gross gamma came with LOWER
forward vol, not higher - while being significant on the rotation test. That inversion
forced a confounder check that should have been pre-registered and was not:

    Black-Scholes gamma carries 1/sigma. High implied vol mechanically produces LOW
    gamma per contract, and realised vol clusters. So "high vol now -> low gross gamma
    now -> high vol next week" reproduces the whole observed relationship with no dealer
    hedging in it at all.

Measured: corr(gross, TRAILING 20d vol) = -0.44 NIFTY / -0.24 BANKNIFTY, and
corr(trailing, forward 5d vol) = +0.43 / +0.49. The product of those two paths is most
of the raw -0.29 / -0.17 that gross shows against forward vol.

The control therefore conditions on trailing vol two ways:
    STRATIFIED  the primary split re-run inside each trailing-vol tercile;
    RESIDUAL    gross regressed on trailing vol, the split taken on the residual.
If the effect is the 1/sigma artefact it collapses in both.

Scope discipline, carried over verbatim from the backlog: this is ONE further
pre-specified hypothesis with an independent market-structure rationale, not licence to
try conventions until something clears p<0.05. If it nulls, GEX is retired as a research
instrument that prints a daily description and nothing more.

CLI:
  py -3 tools/gamma_magnitude_backtest.py
  py -3 tools/gamma_magnitude_backtest.py --symbol BANKNIFTY
"""

from __future__ import annotations

import argparse
import datetime as _dt

import numpy as np

import math

import gamma_exposure as gx
from gamma_regime_backtest import (
    A_GROUP, B_GROUP, SKIP_GROUP, VOL_HORIZONS,
    _fwd_realised_vol, _fwd_return, _paired,
)

#: Trailing window for the percentile normalisation. 60 sessions ~ a quarter: long
#: enough that the percentile means something, short enough to track the regime in OI
#: growth rather than being dominated by where the index was a year ago.
TRAIL = 60


def _load(symbol: str):
    """(dates, spot, gross) chronological, from the cache B-44 already built."""
    ser = gx.load_series(symbol)
    if not ser:
        raise SystemExit(
            f"no cached GEX for {symbol} — run: py -3 tools/gamma_exposure.py --history 480")
    dates = sorted(ser)
    spot = np.array([ser[d]["spot"] for d in dates], float)
    gross = np.array([ser[d]["gross_gex_cr"] for d in dates], float)
    return dates, spot, gross


def _trailing_pct(x: np.ndarray, window: int = TRAIL) -> np.ndarray:
    """Percentile of each value within the `window` sessions BEFORE it.

    Strictly backward-looking — index t is ranked against t-window .. t-1 and never
    against itself or anything after it, so the series is tradable as of the close of t.
    NaN until the window fills.
    """
    out = np.full(len(x), np.nan)
    for t in range(window, len(x)):
        hist = x[t - window:t]
        hist = hist[np.isfinite(hist)]
        if len(hist) < window // 2:
            continue
        out[t] = float((hist < x[t]).mean())
    return out


def _trailing_vol(spot: np.ndarray, window: int = 20) -> np.ndarray:
    """Annualised realised vol over the `window` sessions ENDING at t (inclusive).

    Backward-looking, so it is known at the close of t and can legitimately be
    conditioned on without leaking the forward window.
    """
    out = np.full(len(spot), np.nan)
    for t in range(window + 1, len(spot)):
        seg = spot[t - window:t + 1]
        if (seg <= 0).any():
            continue
        r = np.diff(np.log(seg))
        out[t] = float(r.std(ddof=1) * math.sqrt(252) * 100.0)
    return out


def _residualise(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    """y with its OLS linear dependence on x removed. NaN where either is missing."""
    out = np.full(len(y), np.nan)
    ok = np.isfinite(y) & np.isfinite(x)
    if ok.sum() < 30:
        return out
    slope, intercept = np.polyfit(x[ok], y[ok], 1)
    out[ok] = y[ok] - (intercept + slope * x[ok])
    return out


def _median_split(vals: np.ndarray) -> np.ndarray:
    """A = above median (the 'more dealer gamma' arm), B = below. NaN -> SKIP."""
    cats = np.full(len(vals), SKIP_GROUP)
    ok = np.isfinite(vals)
    if ok.sum() < 20:
        return cats
    med = float(np.median(vals[ok]))
    cats[ok & (vals > med)] = A_GROUP
    cats[ok & (vals <= med)] = B_GROUP
    return cats


def _tercile_split(vals: np.ndarray) -> np.ndarray:
    """A = top third, B = bottom third, middle carried as SKIP so rotation keeps
    the real label composition (same trick the net/gross tercile test uses)."""
    cats = np.full(len(vals), SKIP_GROUP)
    ok = np.isfinite(vals)
    if ok.sum() < 30:
        return cats
    lo, hi = np.percentile(vals[ok], [33.33, 66.67])
    cats[ok & (vals >= hi)] = A_GROUP
    cats[ok & (vals <= lo)] = B_GROUP
    return cats


def _outcome(spot: np.ndarray, fn, h: int) -> np.ndarray:
    return np.array([(lambda v: np.nan if v is None else v)(fn(spot, t, h))
                     for t in range(len(spot))], float)


def run(symbol: str = "NIFTY") -> dict:
    dates, spot, gross = _load(symbol)
    n = len(dates)

    pct = _trailing_pct(gross)
    lvl = gross / spot                     # secondary: raw level, spot-normalised

    cats_primary = _median_split(pct)
    cats_terc = _tercile_split(pct)
    cats_level = _median_split(lvl)

    vol = {h: _outcome(spot, _fwd_realised_vol, h) for h in VOL_HORIZONS}
    absmove = np.array([abs(v) if v is not None else np.nan
                        for v in (_fwd_return(spot, t, 1) for t in range(n))], float)
    ret5 = _outcome(spot, _fwd_return, 5)

    A, B = "high gamma", "low gamma"
    res: dict = {
        "symbol": symbol,
        "n_sessions": n,
        "span": (dates[0], dates[-1]),
        "n_high": int((cats_primary == A_GROUP).sum()),
        "n_low": int((cats_primary == B_GROUP).sum()),
        "gross_median_cr": float(np.median(gross)),
        # PRIMARY
        "primary": _paired(vol[5], cats_primary, A, B),
        # SECONDARY
        "vol10": _paired(vol[10], cats_primary, A, B),
        "vol20": _paired(vol[20], cats_primary, A, B),
        "absmove": _paired(absmove, cats_primary, A, B),
        "tercile_vol5": _paired(vol[5], cats_terc, A, B),
        "level_vol5": _paired(vol[5], cats_level, A, B),
        # EXPECTED NULL
        "ret5": _paired(ret5, cats_primary, A, B),
    }

    # ROBUSTNESS — same primary test inside one weekday, to see whether the weekly
    # expiry cycle is doing the work. Gamma is mechanically largest near expiry.
    wd = np.array([_dt.date.fromisoformat(d).weekday() for d in dates])
    best_wd = int(np.bincount(wd).argmax())
    mask = wd == best_wd
    cats_wd = np.where(mask, cats_primary, SKIP_GROUP)
    res["weekday"] = best_wd
    res["weekday_n"] = int(mask.sum())
    res["weekday_vol5"] = _paired(vol[5], cats_wd, A, B)

    # -- POST-HOC confounder control: gamma carries 1/sigma, and vol clusters --------
    tvol = _trailing_vol(spot)
    ok = np.isfinite(tvol) & np.isfinite(gross)
    res["corr_gross_tvol"] = (float(np.corrcoef(gross[ok], tvol[ok])[0, 1])
                              if ok.sum() > 30 else float("nan"))
    okf = np.isfinite(tvol) & np.isfinite(vol[5])
    res["corr_tvol_fvol"] = (float(np.corrcoef(tvol[okf], vol[5][okf])[0, 1])
                             if okf.sum() > 30 else float("nan"))
    okg = np.isfinite(gross) & np.isfinite(vol[5])
    res["corr_gross_fvol"] = (float(np.corrcoef(gross[okg], vol[5][okg])[0, 1])
                              if okg.sum() > 30 else float("nan"))

    # STRATIFIED - the same split inside each trailing-vol tercile.
    strata = _tercile_split(tvol)      # A = high trailing vol, B = low, SKIP = middle
    res["strat"] = {}
    for lbl, code in (("low trailing vol", B_GROUP), ("high trailing vol", A_GROUP)):
        m = strata == code
        res["strat"][lbl] = _paired(vol[5], np.where(m, cats_primary, SKIP_GROUP), A, B)

    # RESIDUAL - split on gross with its linear dependence on trailing vol removed.
    resid = _residualise(gross, tvol)
    res["resid_pct"] = _paired(vol[5], _median_split(_trailing_pct(resid)), A, B)
    res["resid_raw"] = _paired(vol[5], _median_split(resid), A, B)

    # A LINEAR residual cannot remove a 1/sigma dependence, and 1/sigma is the exact
    # shape Black-Scholes gamma carries. Whatever survives the linear control is
    # therefore still a candidate for leftover curvature rather than information, so
    # residualise against 1/trailing-vol as well - the functional form of the artefact.
    with np.errstate(divide="ignore", invalid="ignore"):
        inv = np.where(np.isfinite(tvol) & (tvol > 0), 1.0 / tvol, np.nan)
    resid_inv = _residualise(gross, inv)
    res["resid_inv"] = _paired(vol[5], _median_split(resid_inv), A, B)
    okc = np.isfinite(gross) & np.isfinite(inv)
    res["corr_gross_invtvol"] = (float(np.corrcoef(gross[okc], inv[okc])[0, 1])
                                 if okc.sum() > 30 else float("nan"))
    return res


def _fmt(st: dict, unit: str = "pp") -> str:
    if st is None or not np.isfinite(st.get("diff", np.nan)):
        return "      n/a"
    p = st.get("p")
    pr = st.get("p_rot")
    return (f"{st['diff']:+7.2f} {unit}   n={st['n_a']:>3}/{st['n_b']:<3}  "
            f"welch={'  n/a' if p is None else f'{p:.3f}'}   "
            f"p_rot={'  n/a' if pr is None else f'{pr:.3f}'}")


def format_report(r: dict) -> str:
    L = []
    L.append(f"B-44r — gamma MAGNITUDE as the vol predictor · {r['symbol']}")
    L.append(f"  {r['n_sessions']} sessions, {r['span'][0]} .. {r['span'][1]}   "
             f"high/low = {r['n_high']}/{r['n_low']}   "
             f"median gross {r['gross_median_cr']:,.0f} Cr")
    L.append("  Convention: dealers short gamma on BOTH sides -> the sign is constant "
             "and only the size can carry information.")
    L.append("  Prediction: HIGH gross gamma -> HIGHER forward vol (bigger short-gamma "
             "book -> more hedging flow with the move).")
    L.append("")
    L.append("  PRIMARY (pre-registered, carries the conclusion)")
    L.append(f"    fwd 5d realised vol        {_fmt(r['primary'])}")
    L.append("")
    L.append("  SECONDARY (reported, cannot carry the conclusion)")
    L.append(f"    fwd 10d realised vol       {_fmt(r['vol10'])}")
    L.append(f"    fwd 20d realised vol       {_fmt(r['vol20'])}")
    L.append(f"    next-day absolute move     {_fmt(r['absmove'], '%')}")
    L.append(f"    tercile split, 5d vol      {_fmt(r['tercile_vol5'])}")
    L.append(f"    raw gross/spot, 5d vol     {_fmt(r['level_vol5'])}")
    L.append("")
    L.append("  EXPECTED NULL (falsification check on the harness)")
    L.append(f"    fwd 5d return              {_fmt(r['ret5'], '%')}")
    L.append("")
    L.append(f"  ROBUSTNESS — within weekday {r['weekday']} only "
             f"({r['weekday_n']} sessions), expiry-cycle control")
    L.append(f"    fwd 5d realised vol        {_fmt(r['weekday_vol5'])}")
    L.append("")
    L.append("  POST-HOC CONFOUNDER CONTROL - BS gamma carries 1/sigma, and vol clusters")
    L.append(f"    corr(gross, trailing vol)  {r['corr_gross_tvol']:+.3f}")
    L.append(f"    corr(trailing, fwd 5d vol) {r['corr_tvol_fvol']:+.3f}")
    L.append(f"    corr(gross, fwd 5d vol)    {r['corr_gross_fvol']:+.3f}   (uncontrolled)")
    for lbl, st in r["strat"].items():
        L.append(f"    stratified: {lbl:<18}{_fmt(st)}")
    L.append(f"    residual pct split         {_fmt(r['resid_pct'])}")
    L.append(f"    residual raw split         {_fmt(r['resid_raw'])}")
    L.append(f"    corr(gross, 1/trailing vol){r['corr_gross_invtvol']:+.3f}   "
             f"(the artefact's own shape)")
    L.append(f"    residual vs 1/vol split    {_fmt(r['resid_inv'])}")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description="B-44r: gamma magnitude vs forward vol")
    ap.add_argument("--symbol", default="NIFTY")
    ap.add_argument("--both", action="store_true", help="run NIFTY and BANKNIFTY")
    args = ap.parse_args()
    syms = ["NIFTY", "BANKNIFTY"] if args.both else [args.symbol]
    for s in syms:
        print(format_report(run(s)))
        print()


if __name__ == "__main__":
    main()
