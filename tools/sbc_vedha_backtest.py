#!/usr/bin/env python3
"""
sbc_vedha_backtest.py — does SBC *daily* vedha land on real NIFTY turning points?

This is the event study specified in the wiki page "SBC Vedha Backtest Design".
It is the DAILY, index-level test (distinct from sbc_backtest.py, which tests
intraday Moon-pada windows on 24/7 instruments).

Pipeline
--------
1. SIGNAL. For every trading day, compute the geometric vedhas (reusing the
   authentic engine in sbc_scoring.cast_vedas). A "vedha day" = a MALEFIC graha
   pierces the anchor nakshatra with total weight >= --severity.
     * anchor = "natal" : NIFTY janma (Moon) nakshatra from --natal datetime.
     * anchor = "moon"  : the transiting Moon's nakshatra that day (natal-free).
2. LABELS. Objective turning points on ^NSEI daily closes, under 3 definitions:
     fractal k=5, fractal k=10, and a volatility-jump variant. Nothing discretionary.
3. EVENT STUDY. A vedha day "hits" if a turn falls within +/- W trading days.
     recall   = hits / vedha_days
     coverage = P(a random day is within +/-W of a turn)   (the base rate)
     lift     = recall / coverage      (1.0 = no signal)
4. NULL. Structure-preserving circular rotation of the vedha-day series (5000x),
   which holds the vedha-day COUNT and its clustering fixed while breaking its
   alignment to price. Empirical p = fraction of null lifts >= observed.
5. CONTROLS. Re-run with eclipse-adjacent days stripped (eclipses are real vol
   events; if the edge dies without them, vedha added nothing). Contingency
   table + odds ratio reported alongside lift.

Honest limits: ^NSEI daily history on yfinance starts ~2007 (~18y). Mean-node
Rahu/Ketu and Lahiri ayanamsa follow the live tool. Pre-register --window,
--severity and the anchor BEFORE reading the numbers; the decision rule is at
the bottom of the design page, not here.

CLI:
  py -3 tools/sbc_vedha_backtest.py
  py -3 tools/sbc_vedha_backtest.py --anchor moon --window 2 --severity 1.0
  py -3 tools/sbc_vedha_backtest.py --symbol ^NSEBANK --out reports/sbc_vedha_nsebank.md
"""

from __future__ import annotations

import argparse
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

import ephem
from sarvatobhadra_chakra import compute_planets, lahiri_ayanamsa
from sbc_scoring import cast_vedas

IST = timezone(timedelta(hours=5, minutes=30))
MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
NAK_SPAN = 360.0 / 27.0


# --------------------------------------------------------------------------- #
# Signal: vedha days
# --------------------------------------------------------------------------- #

def _dt_utc_for(day: pd.Timestamp, ist_hour: int = 12) -> datetime:
    """Noon-IST of a trading day, as naive UTC (what compute_planets wants)."""
    local = datetime(day.year, day.month, day.day, ist_hour, 0, tzinfo=IST)
    return local.astimezone(timezone.utc).replace(tzinfo=None)


def _moon_nakshatra(dt_utc: datetime) -> str:
    return compute_planets(dt_utc)["Moon"].nakshatra


def natal_nakshatra(natal_ist: datetime) -> str:
    dt_utc = natal_ist.astimezone(timezone.utc).replace(tzinfo=None)
    return _moon_nakshatra(dt_utc)


def vedha_severity(dt_utc: datetime, anchor: str,
                   fixed_anchor_nak: Optional[str]) -> Tuple[float, List[str]]:
    """Total malefic vedha weight onto the anchor nakshatra + which planets.

    anchor 'natal' -> pierce the fixed janma nakshatra.
    anchor 'moon'  -> pierce the transiting Moon's nakshatra that day.
    """
    planets = compute_planets(dt_utc)
    target = fixed_anchor_nak if anchor == "natal" else planets["Moon"].nakshatra
    sev = 0.0
    who: List[str] = []
    for v in cast_vedas(planets):
        if v.nature == "malefic" and v.planet in MALEFICS \
                and v.target_nakshatra == target:
            sev += v.weight
            who.append(f"{v.planet}:{v.veda_type}")
    return sev, who


def build_vedha_series(days: pd.DatetimeIndex, anchor: str,
                       natal_ist: datetime, severity: float
                       ) -> Tuple[np.ndarray, np.ndarray, str]:
    """Return (vedha_bool, severity_float) per day + the resolved anchor label."""
    anchor_nak = natal_nakshatra(natal_ist) if anchor == "natal" else "(transit Moon)"
    sev = np.zeros(len(days), dtype=float)
    fixed = anchor_nak if anchor == "natal" else None
    for i, day in enumerate(days):
        s, _ = vedha_severity(_dt_utc_for(day), anchor, fixed)
        sev[i] = s
    vedha = sev >= severity
    return vedha, sev, anchor_nak


# --------------------------------------------------------------------------- #
# Labels: turning points
# --------------------------------------------------------------------------- #

def fractal_pivots(close: np.ndarray, high: np.ndarray, low: np.ndarray,
                   k: int) -> np.ndarray:
    """Bool array: bar is a swing high or low (extreme over +/-k bars)."""
    n = len(close)
    piv = np.zeros(n, dtype=bool)
    for i in range(k, n - k):
        if high[i] == high[i - k:i + k + 1].max():
            piv[i] = True
        elif low[i] == low[i - k:i + k + 1].min():
            piv[i] = True
    return piv


def voljump_pivots(close: np.ndarray, lookback: int = 60,
                   q: float = 0.95) -> np.ndarray:
    """Bool array: |daily return| exceeds its rolling q-quantile."""
    ret = np.abs(np.diff(np.log(close), prepend=np.log(close[0])))
    s = pd.Series(ret)
    thr = s.rolling(lookback, min_periods=lookback // 2).quantile(q)
    return (s > thr).to_numpy(dtype=bool)


def label_sets(df: pd.DataFrame) -> Dict[str, np.ndarray]:
    c, h, l = df["Close"].to_numpy(), df["High"].to_numpy(), df["Low"].to_numpy()
    return {
        "fractal_k5": fractal_pivots(c, h, l, 5),
        "fractal_k10": fractal_pivots(c, h, l, 10),
        "voljump_p95": voljump_pivots(c),
    }


# --------------------------------------------------------------------------- #
# Eclipse detection (syzygy + low lunar latitude)
# --------------------------------------------------------------------------- #

def eclipse_days(days: pd.DatetimeIndex, elong_tol: float = 7.0,
                 lat_tol: float = 1.4, pad: int = 3) -> np.ndarray:
    """Bool per day: within +/-pad days of a solar/lunar eclipse syzygy.

    Approx: Sun-Moon elongation near 0 (new) or 180 (full) AND |Moon ecliptic
    latitude| small -> the Moon is near a node at syzygy -> an eclipse.
    """
    core = np.zeros(len(days), dtype=bool)
    for i, day in enumerate(days):
        dt = _dt_utc_for(day)
        sun, moon = ephem.Sun(), ephem.Moon()
        obs = ephem.Observer(); obs.date = ephem.Date(dt)
        sun.compute(obs); moon.compute(obs)
        slon = math.degrees(float(ephem.Ecliptic(sun).lon))
        mlon = math.degrees(float(ephem.Ecliptic(moon).lon))
        mlat = math.degrees(float(ephem.Ecliptic(moon).lat))
        elong = ((mlon - slon) % 360.0)
        near_new = min(elong, 360.0 - elong) < elong_tol
        near_full = abs(elong - 180.0) < elong_tol
        if (near_new or near_full) and abs(mlat) < lat_tol:
            core[i] = True
    if pad:
        padded = core.copy()
        idx = np.where(core)[0]
        for j in idx:
            padded[max(0, j - pad):min(len(days), j + pad + 1)] = True
        return padded
    return core


# --------------------------------------------------------------------------- #
# Event study + circular-rotation null
# --------------------------------------------------------------------------- #

def within_window(pivots: np.ndarray, w: int) -> np.ndarray:
    """Bool per day: a pivot falls within +/-w trading days of this day."""
    n = len(pivots)
    out = np.zeros(n, dtype=bool)
    idx = np.where(pivots)[0]
    for j in idx:
        out[max(0, j - w):min(n, j + w + 1)] = True
    return out


def study(vedha: np.ndarray, pivots: np.ndarray, w: int,
          n_boot: int = 5000, seed: int = 7) -> Dict[str, float]:
    cover_bool = within_window(pivots, w)
    coverage = cover_bool.mean()
    nv = int(vedha.sum())
    if nv == 0 or coverage == 0:
        return {"vedha_days": nv, "coverage": coverage, "recall": 0.0,
                "lift": 0.0, "p_value": 1.0, "null_lift": 0.0,
                "odds_ratio": 0.0}
    recall = cover_bool[vedha].mean()
    lift = recall / coverage

    rng = np.random.default_rng(seed)
    null_lift = np.empty(n_boot)
    base = cover_bool.astype(float)
    n = len(vedha)
    vpos = np.where(vedha)[0]
    for b in range(n_boot):
        r = int(rng.integers(1, n))
        rolled = (vpos + r) % n
        null_lift[b] = base[rolled].mean() / coverage
    p_value = float((null_lift >= lift).mean())

    # 2x2 contingency: vedha(y/n) x pivot-in-window(y/n) + odds ratio
    a = int((vedha & cover_bool).sum())
    b_ = int((vedha & ~cover_bool).sum())
    c = int((~vedha & cover_bool).sum())
    d = int((~vedha & ~cover_bool).sum())
    orr = ((a + 0.5) * (d + 0.5)) / ((b_ + 0.5) * (c + 0.5))  # Haldane-Anscombe

    return {"vedha_days": nv, "coverage": coverage, "recall": recall,
            "lift": lift, "p_value": p_value,
            "null_lift": float(null_lift.mean()), "odds_ratio": orr}


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #

def load_prices(symbol: str, start: str) -> pd.DataFrame:
    import yfinance as yf
    print(f"Downloading {symbol} daily from {start} ...")
    df = yf.download(symbol, start=start, interval="1d", progress=False,
                     auto_adjust=False)
    if df.empty:
        raise SystemExit(f"No data for {symbol}.")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna(subset=["Close", "High", "Low"])
    return df


def run(args) -> str:
    df = load_prices(args.symbol, args.start)
    days = df.index
    natal_ist = datetime.fromisoformat(args.natal).replace(tzinfo=IST)

    print(f"{len(days)} trading days · {days[0].date()}..{days[-1].date()}")
    print("Computing daily vedha signal (ephem) ...")
    vedha, sev, anchor_nak = build_vedha_series(days, args.anchor, natal_ist,
                                                args.severity)
    print(f"Anchor: {args.anchor} = {anchor_nak} · "
          f"vedha days: {int(vedha.sum())}/{len(days)} "
          f"({vedha.mean():.1%}) at severity>={args.severity}")

    print("Detecting eclipse-adjacent days ...")
    ecl = eclipse_days(days, pad=args.eclipse_pad)
    vedha_noecl = vedha & ~ecl
    print(f"Eclipse-adjacent days: {int(ecl.sum())} · "
          f"vedha days after stripping eclipses: {int(vedha_noecl.sum())}")

    labels = label_sets(df)

    lines: List[str] = []
    hdr = (f"# SBC Vedha Backtest — {args.symbol}\n\n"
           f"- Window: +/-{args.window} trading days · severity>={args.severity} "
           f"· anchor={args.anchor} ({anchor_nak})\n"
           f"- Sample: {days[0].date()}..{days[-1].date()} ({len(days)} days)\n"
           f"- Vedha days: {int(vedha.sum())} ({vedha.mean():.1%}); "
           f"eclipse-adjacent: {int(ecl.sum())}\n"
           f"- Null: {args.bootstrap} circular rotations · "
           f"OR uses Haldane-Anscombe correction\n")
    lines.append(hdr)
    lines.append("| label | set | vedha_days | coverage | recall | "
                 "**lift** | null_lift | p | odds_ratio |")
    lines.append("|---|---|--:|--:|--:|--:|--:|--:|--:|")

    def row(label, tag, vset, pivots):
        r = study(vset, pivots, args.window, args.bootstrap)
        lines.append(
            f"| {label} | {tag} | {r['vedha_days']} | {r['coverage']:.1%} | "
            f"{r['recall']:.1%} | **{r['lift']:.2f}x** | {r['null_lift']:.2f}x | "
            f"{r['p_value']:.3f} | {r['odds_ratio']:.2f} |")
        return r

    print("\nRunning event study across label definitions ...\n")
    for lname, piv in labels.items():
        row(lname, "full", vedha, piv)
        row(lname, "no-eclipse", vedha_noecl, piv)

    report = "\n".join(lines)
    # decision-rule reminder (from the wiki design page)
    report += (
        "\n\n## Decision rule (pre-registered)\n"
        "Promote to a watch-window ONLY if, out-of-sample: lift >= 1.3 AND "
        "p < 0.01 AND it survives eclipse-stripping AND holds across >=2 label "
        "defs and >=2 instruments. A lift ~1.0 with p>0.1 is a clean negative — "
        "that is a valid, useful result. Direction is NOT tested here and is not "
        "implied. Educational, not investment advice.\n")
    print(report)
    if args.out:
        import os
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"\nWrote {args.out}")
    return report


def main() -> None:
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Daily SBC vedha event study vs NIFTY turns")
    ap.add_argument("--symbol", default="^NSEI")
    ap.add_argument("--start", default="2007-09-17",
                    help="history start (yfinance ^NSEI begins ~2007-09)")
    ap.add_argument("--anchor", default="natal", choices=["natal", "moon"])
    ap.add_argument("--natal", default="1995-11-03T09:00",
                    help="NIFTY janma datetime (IST) for anchor=natal")
    ap.add_argument("--severity", type=float, default=1.0,
                    help="min total malefic vedha weight to flag a day "
                         "(1.0 = one front vedha or ~2 diagonals)")
    ap.add_argument("--window", type=int, default=2,
                    help="+/- trading-day match window")
    ap.add_argument("--eclipse-pad", type=int, default=3)
    ap.add_argument("--bootstrap", type=int, default=5000)
    ap.add_argument("--out", default="")
    run(ap.parse_args())


if __name__ == "__main__":
    main()
