#!/usr/bin/env python3
"""sentiment_factor_edge.py — B-66: the other three sentiment factors, and the composite.

Runs the design pre-registered in `analyses/Open-Backlog.md` §B-66, committed at
`a912088` BEFORE this scorer existed. Nothing here may change the design; if
something has to change, the entry changes first and says why.

══ WHY THIS EXISTS ══════════════════════════════════════════════════════════════

B-65r measured the PMax factor (weight 20) and found it does not discriminate.
Its consequence rule said re-weighting was a live proposal *complicated by the
other three factors being equally unmeasured* -- moving PMax's 20 points into
them would move weight from one unvalidated input to three others. So: measure
the other three, then the composite they add up to.

══ PRE-REGISTERED DESIGN (mirrored from the entry; do not edit here) ════════════

  PRIMARY per factor   TERCILE SPREAD on NIFTY forward returns:
                       mean(fwd | factor in top third) - mean(fwd | bottom third)
                       at 5 trading days, entry next open, circular-rotation p.
                       PASS: spread > 0 AND p_rot < 0.05.
                       Terciles because these three are continuous -- it asks
                       "does more of this mean more return" without fitting a
                       threshold. Spearman reported as description only.

  CO-PRIMARY           the COMPOSITE: the same tercile spread on the 0-100 score
                       the desk displays, at the shipped weights. A component can
                       be weak and the blend still work, and the blend is the
                       thing on the page. Band spread (Strong Buy vs Strong Sell)
                       reported too, since bands are what the UI shows.

  WINDOWS, declared up front and different per factor:
    A/D      PROXY, 460 cached liquid names, 2023-10 -> 2026-09.  **NOT the
             shipped input**, which uses the full EQ bhavcopy (~2,000 names).
             Rebuilding 750 historical bhavcopies is a data-acquisition project,
             not a measurement. A null here is evidence about breadth-as-signal,
             NOT proof about the shipped factor.
    Sector   11 NSE sector indices, 2011-09 -> 2026-09 (~15y)
    Regime   ^NSEI daily, 2007-09 -> 2026-09 (~19y), four regimes
    Composite  bounded by the A/D proxy's window -- its own power limit

  CONSEQUENCE RULES: nothing is deleted or re-weighted by this run whatever it
  says. If nothing discriminates, the sentiment index is a DESCRIPTIVE DISPLAY
  rather than a forecast, and the honest fix is to say so on the page.
  Relabelling is cheaper than deletion and loses nothing the desk has been shown
  to have.

══ ONE DEFINITION ═══════════════════════════════════════════════════════════════

Each factor's arithmetic is reproduced from `sentiment_index`'s own functions --
the A/D ratio, the (greens + 0.5*flats)/scored count, the clip(0.5 + dist/10)
map and the shipped weights -- because those functions return only TODAY's
reading and a study needs the series. Where state is involved (the PMax ratchet)
the shipped code is imported rather than repeated; the three factors here are
stateless arithmetic, so they are recomputed and the constants are read from
`sentiment_index` rather than retyped.

CLI:
    py -3 tools/sentiment_factor_edge.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import renko_quality_cardinality as card
import sector_rotation as secrot
import sentiment_index as si

try:
    import yfinance as yf
except Exception as e:  # pragma: no cover
    sys.exit(f"yfinance required: {e}")

HERE = Path(__file__).resolve().parent
CACHE = card.CACHE

# ── pre-registered constants. Changing one changes the study. ────────────────
HORIZON = 5          #: trading days, entry next open
ROT_MIN_STATS = 20


# ── the factor series ────────────────────────────────────────────────────────

def nifty_daily(period="max"):
    h = yf.Ticker("^NSEI").history(period=period, interval="1d", auto_adjust=False)
    h = h.dropna(subset=["Close"])
    h.index = pd.to_datetime(h.index).tz_localize(None).normalize()
    return h


def regime_factor(close: pd.Series) -> pd.Series:
    """Input #3: clip(0.5 + dist_pct/10, 0, 1) against the 200-DMA.

    Same map as `si._regime_sma200`, applied at every bar instead of the last.
    """
    sma = close.rolling(200).mean()
    dist = (close / sma - 1.0) * 100.0
    return (0.5 + dist / 10.0).clip(0.0, 1.0)


def sector_factor() -> pd.Series:
    """Input #2: (greens + 0.5*flats) / scored, across the 11 NSE sector indices.

    `si._sector_performance` classifies each sector's LAST session as green/red/
    flat off its own previous close; this reproduces that per day. The staleness
    and coverage guards in the shipped function are live-feed protections, not
    part of the arithmetic, so they have no historical analogue -- a day is scored
    on whichever indices actually traded.
    """
    frames = {}
    for tkr in sorted(set(secrot.SECTOR_INDEX_MAP.values())):
        try:
            h = yf.Ticker(tkr).history(period="max", interval="1d", auto_adjust=False)
            h = h.dropna(subset=["Close"])
            if len(h) < 50:
                continue
            h.index = pd.to_datetime(h.index).tz_localize(None).normalize()
            frames[tkr] = h["Close"].astype(float)
        except Exception:
            continue
    if not frames:
        return pd.Series(dtype=float)
    px = pd.DataFrame(frames).sort_index()
    chg = px.pct_change()
    greens = (chg > 0).sum(axis=1)
    flats = (chg == 0).sum(axis=1)
    scored = chg.notna().sum(axis=1)
    out = (greens + 0.5 * flats) / scored.replace(0, np.nan)
    return out.dropna()


def ad_factor_proxy() -> pd.Series:
    """Input #1, AS A PROXY: advances / (advances + declines) over cached names.

    The shipped factor counts the full EQ bhavcopy (~2,000 names). This counts the
    460 cached liquid names, because rebuilding 750 historical bhavcopies is a
    data-acquisition project rather than a measurement. Liquid-only breadth is
    narrower and less noisy than full-market breadth, so this is evidence about
    breadth-as-a-signal and NOT proof about the shipped input. The output repeats
    that caveat rather than relying on this docstring.
    """
    closes = {}
    for p in sorted(CACHE.glob("*_1d.json")):
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        bars = doc.get("bars") or []
        if len(bars) < 100:
            continue
        idx = pd.to_datetime([b["time"] for b in bars], unit="s").normalize()
        closes[doc["symbol"]] = pd.Series([b["close"] for b in bars], index=idx)
    if not closes:
        return pd.Series(dtype=float)
    px = pd.DataFrame(closes).sort_index()
    chg = px.pct_change()
    adv = (chg > 0).sum(axis=1)
    dec = (chg < 0).sum(axis=1)
    tot = adv + dec
    return (adv / tot.replace(0, np.nan)).dropna()


# ── scoring ──────────────────────────────────────────────────────────────────

def forward(h: pd.DataFrame, horizon: int) -> pd.Series:
    o = h["Open"].astype(float).values
    c = h["Close"].astype(float).values
    n = len(c)
    fwd = np.full(n, np.nan)
    for t in range(n - horizon - 2):
        if o[t + 1] > 0:
            fwd[t] = (c[t + 1 + horizon] / o[t + 1] - 1.0) * 100.0
    return pd.Series(fwd, index=h.index)


def tercile_spread(fac: np.ndarray, fwd: np.ndarray):
    ok = np.isfinite(fac) & np.isfinite(fwd)
    f, r = fac[ok], fwd[ok]
    if len(f) < 100:
        return None
    lo, hi = np.quantile(f, 1 / 3), np.quantile(f, 2 / 3)
    top, bot = r[f >= hi], r[f <= lo]
    if len(top) < 20 or len(bot) < 20:
        return None
    return {"n": len(f), "n_top": len(top), "n_bot": len(bot),
            "top": float(top.mean()), "bot": float(bot.mean()),
            "spread": float(top.mean() - bot.mean()),
            "all": float(r.mean()),
            "hit_top": float((top > 0).mean() * 100.0),
            "hit_bot": float((bot > 0).mean() * 100.0),
            "rho": float(pd.Series(f).corr(pd.Series(r), method="spearman"))}


def rotation_p(fac: np.ndarray, fwd: np.ndarray, observed: float):
    """Rotate the FACTOR series; recompute the same spread.

    These factors are slow and highly autocorrelated (the regime one especially --
    it can sit in a tercile for months), and the returns overlap. An i.i.d. null
    would be meaningless. Rotation keeps the factor's own persistence and its
    tercile structure and destroys only the alignment with returns.
    """
    n = len(fac)
    stats = []
    step = max(5, n // 150)
    for s in range(step, n - step, step):
        r = tercile_spread(np.roll(fac, s), fwd)
        if r is not None:
            stats.append(abs(r["spread"]))
    if len(stats) < ROT_MIN_STATS:
        return None, len(stats)
    return float(np.mean(np.asarray(stats) >= abs(observed))), len(stats)


def _row(label, r, p, window=""):
    if r is None:
        return f"  {label:<26} (too few observations)"
    ptxt = "     -" if p is None else f"{p:6.3f}"
    star = "*" if (p is not None and p < 0.05) else " "
    return (f"  {label:<26} top={r['top']:+6.2f}%  bot={r['bot']:+6.2f}%  "
            f"spread={r['spread']:+6.2f}%  rho={r['rho']:+5.2f}  "
            f"hit={r['hit_top']:4.1f}/{r['hit_bot']:4.1f}  n={r['n']:5d}  "
            f"p_rot={ptxt}{star} {window}")


def main() -> int:
    ap = argparse.ArgumentParser(description="B-66 - the other three sentiment factors + composite")
    ap.add_argument("--horizon", type=int, default=HORIZON)
    args = ap.parse_args()

    print("B-66 - do the sentiment index's other three factors discriminate? And the composite?")
    print(f"PRIMARY statistic: TERCILE SPREAD on NIFTY forward returns @{args.horizon}d,")
    print("entry next open, circular-rotation p. PASS: spread > 0 AND p_rot < 0.05.\n")

    nif = nifty_daily()
    fwd_s = forward(nif, args.horizon)

    print("building factor series...", file=sys.stderr)
    fac = {
        "regime": regime_factor(nif["Close"].astype(float)),
        "sector": sector_factor(),
        "ad": ad_factor_proxy(),
    }

    results = {}
    windows = {}
    for key, label in [("ad", "A/D (w30) *PROXY*"),
                       ("sector", "Sector (w25)"),
                       ("regime", "Regime SMA200 (w25)")]:
        ser = fac[key]
        if ser.empty:
            print(_row(label, None, None))
            continue
        joined = pd.DataFrame({"f": ser, "r": fwd_s}).dropna()
        windows[key] = (joined.index[0].date(), joined.index[-1].date())
        r = tercile_spread(joined["f"].values, joined["r"].values)
        p, _ = (None, 0) if r is None else rotation_p(joined["f"].values, joined["r"].values, r["spread"])
        results[key] = (r, p)
        print(_row(label, r, p, f"{windows[key][0]}->{windows[key][1]}"))

    # ── the composite, at the shipped weights ───────────────────────────────
    pm = si._pmax_direction_nifty_1h  # noqa: F841  (documented below)
    # PMax's 1H direction cannot be reconstructed on a daily index without the 1H
    # series, and B-65r already measured it at no discrimination. The composite is
    # therefore built from the three measurable factors at their shipped weights,
    # with PMax held at its neutral 0.5 -- which is exactly what the shipped code
    # substitutes when the 1H fetch fails. Stated in the output, because a
    # composite missing a fifth of itself is a different object.
    comp = pd.DataFrame({k: v for k, v in fac.items() if not v.empty}).dropna()
    if not comp.empty:
        score = (comp["ad"] * si.W_ADV_DECL
                 + comp["sector"] * si.W_SECTOR
                 + comp["regime"] * si.W_REGIME
                 + 0.5 * si.W_PMAX_1H)
        joined = pd.DataFrame({"f": score, "r": fwd_s}).dropna()
        r = tercile_spread(joined["f"].values, joined["r"].values)
        p, _ = (None, 0) if r is None else rotation_p(joined["f"].values, joined["r"].values, r["spread"])
        results["composite"] = (r, p)
        print()
        print(_row("COMPOSITE 0-100 (co-primary)", r, p,
                   f"{joined.index[0].date()}->{joined.index[-1].date()}"))
        print("  (PMax held at its neutral 0.5 -- exactly what the shipped code substitutes")
        print("   when the 1H fetch fails, and B-65r measured it at no discrimination)")

        # Bands, because bands are what the UI shows.
        sb = joined[joined["f"] >= 80]["r"]
        ss = joined[joined["f"] < 20]["r"]
        print(f"\n  BANDS: Strong Buy (>=80) n={len(sb)}"
              + (f", mean {sb.mean():+.2f}%" if len(sb) else "")
              + f" | Strong Sell (<20) n={len(ss)}"
              + (f", mean {ss.mean():+.2f}%" if len(ss) else ""))
        if len(sb) < 20 or len(ss) < 20:
            print("         too few days at the extremes to compare -- which is itself a")
            print("         finding: the bands the UI is built around are nearly never hit.")

    # ── verdict ─────────────────────────────────────────────────────────────
    print()
    any_disc = False
    for key, name in [("ad", "A/D (proxy)"), ("sector", "Sector"),
                      ("regime", "Regime"), ("composite", "COMPOSITE")]:
        r, p = results.get(key, (None, None))
        if r is None:
            print(f"  {name:<12} no result")
            continue
        disc = r["spread"] > 0 and p is not None and p < 0.05
        any_disc = any_disc or disc
        verdict = "DISCRIMINATES" if disc else "does not discriminate"
        print(f"  {name:<12} {verdict:<22} spread={r['spread']:+.2f}%, "
              f"p_rot={'n/a' if p is None else f'{p:.3f}'}")

    cr, cp = results.get("composite", (None, None))
    comp_disc = cr is not None and cp is not None and cp < 0.05 and cr["spread"] > 0
    print()
    if comp_disc:
        print("READING: the COMPOSITE discriminates. The index stands as a product whatever")
        print("         the parts scored, and weak components are a refinement question.")
    elif any_disc:
        print("READING: a COMPONENT discriminates but the composite does not. The weights are")
        print("         getting in the way of an input that works -- a concrete re-weighting")
        print("         proposal with a named beneficiary, and its own entry.")
    else:
        print("READING: NOTHING discriminates -- not the components, not the blend. On the")
        print("         pre-registered rule, the sentiment index is a DESCRIPTIVE DISPLAY")
        print("         rather than a forecast, and the honest fix is to SAY SO ON THE PAGE.")
        print("         Nothing is deleted and no weight is changed by this run. Relabelling")
        print("         is cheaper than deletion and loses nothing the desk has been shown")
        print("         to have.")

    print("\nLIMITS: the A/D arm is a PROXY on 460 liquid names, not the shipped full-EQ")
    print("        bhavcopy -- evidence about breadth-as-signal, not proof about that")
    print("        input; the composite inherits the proxy's ~3y window while regime")
    print("        alone has ~19y; NIFTY forward returns are one series, so every")
    print("        p here is indicative; and a factor can be useful for POSITION SIZING")
    print("        or narrative while carrying no directional edge, which this does not test.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
