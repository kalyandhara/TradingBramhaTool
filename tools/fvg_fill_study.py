"""fvg_fill_study.py — does a Fair Value Gap actually act as a price magnet?

Measures the claim every FVG explainer makes and none of them tests: *"the market
seeks balance and will eventually pull back to fill the gap."* Reports **fill %**
and **bars-to-fill** under each of the four fill definitions on
``concepts/Fair-Value-Gap`` — and, crucially, against a **matched control**.

Why a bare fill rate would be worthless
---------------------------------------
"87% of gaps get filled" sounds like evidence and is not. Whether price returns
to a band is driven mostly by two mechanical facts: **how wide the band is** and
**how far it sits from price**. A wide band close to price fills often whether or
not anything special created it. So every real gap here is paired with a
**placebo zone of identical width at an identical distance from the reference
price**, anchored at a random other bar in the same series. The question is not
"do gaps fill" — they do — but **"do gaps fill more, or sooner, than an
equivalent stretch of ordinary price?"**

The four fill definitions (from the DGT source, which resolved the contradiction
between LuxAlgo's wick-through-deletes and the Quant script's close-through):
    any_touch    price reaches the NEAR edge
    midpoint     price reaches 50% of the gap (consequent encroachment)
    wick_sweep   a wick crosses the FAR edge
    body_beyond  a CLOSE pushes past the far edge

Gap detection deliberately mirrors `scanner_templates.detect_fvg_pullback`:
3-candle, directional middle candle, and a `> atr_mult x ATR` size gate. The study
therefore measures the gaps this repo actually detects, not a looser textbook
set — a study of gaps we don't trade would not transfer.

Only gaps with a full `horizon` bars of forward data are measured. Including
partially-observed gaps would count "not filled yet" as "not filled" and bias
every fill rate downward by exactly the amount of the truncation.

Run: `python tools/fvg_fill_study.py` (fetches a small NSE universe).
"""
from __future__ import annotations

import math
import random
from typing import Any, Iterable

import numpy as np
import pandas as pd

FILL_MODES = ("any_touch", "midpoint", "wick_sweep", "body_beyond")


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    prev = c.shift(1)
    tr = pd.concat([h - l, (h - prev).abs(), (l - prev).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def find_gaps(df: pd.DataFrame, *, atr_mult: float = 0.5,
              atr_len: int = 14) -> list[dict[str, Any]]:
    """Every size-gated 3-candle FVG in the series.

    Same rule as `detect_fvg_pullback`: wicks of candle 1 and 3 must not overlap,
    the middle candle must be directional, and the gap must exceed
    `atr_mult x ATR`. `ref_price` is the close of the third candle — the price the
    gap is "away from" when it forms, used to match placebos on distance.
    """
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    atr = _atr(df, atr_len)
    out: list[dict[str, Any]] = []
    for i in range(2, len(df)):
        a = float(atr.iloc[i])
        if not np.isfinite(a) or a <= 0:
            continue
        h2, l2 = float(h.iloc[i - 2]), float(l.iloc[i - 2])
        o1, c1 = float(o.iloc[i - 1]), float(c.iloc[i - 1])
        l0, h0, c0 = float(l.iloc[i]), float(h.iloc[i]), float(c.iloc[i])

        if l0 > h2 and c1 > o1 and (l0 - h2) > a * atr_mult:
            out.append({"index": i, "direction": "bull", "bot": h2, "top": l0,
                        "ref_price": c0, "atr": a})
        if h0 < l2 and c1 < o1 and (l2 - h0) > a * atr_mult:
            out.append({"index": i, "direction": "bear", "bot": h0, "top": l2,
                        "ref_price": c0, "atr": a})
    for g in out:
        g["width"] = g["top"] - g["bot"]
        g["width_atr"] = g["width"] / g["atr"]
        # Distance from the reference price to the NEAR edge, as a fraction.
        near = g["top"] if g["direction"] == "bull" else g["bot"]
        g["distance_pct"] = abs(g["ref_price"] - near) / g["ref_price"] * 100.0
    return out


def bars_to_fill(df: pd.DataFrame, start: int, direction: str,
                 bot: float, top: float, horizon: int) -> dict[str, int | None]:
    """Bars from `start` until each fill definition is first satisfied.

    None means "not satisfied within `horizon`". Scans forward once and records
    every mode's first hit, so the four modes are measured on identical data.
    """
    mid = (bot + top) / 2.0
    hi, lo, cl = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    res: dict[str, int | None] = {m: None for m in FILL_MODES}
    end = min(start + horizon, len(df) - 1)

    for j in range(start + 1, end + 1):
        k = j - start
        if direction == "bull":              # gap sits BELOW price; fills downward
            reach_near, reach_mid = lo[j] <= top, lo[j] <= mid
            reach_far, close_past = lo[j] <= bot, cl[j] <= bot
        else:                                # gap sits ABOVE price; fills upward
            reach_near, reach_mid = hi[j] >= bot, hi[j] >= mid
            reach_far, close_past = hi[j] >= top, cl[j] >= top
        for mode, hit in (("any_touch", reach_near), ("midpoint", reach_mid),
                          ("wick_sweep", reach_far), ("body_beyond", close_past)):
            if res[mode] is None and hit:
                res[mode] = k
        if all(v is not None for v in res.values()):
            break
    return res


def placebo_for(df: pd.DataFrame, gap: dict[str, Any], horizon: int,
                rng: random.Random) -> dict[str, Any] | None:
    """A same-width, same-distance zone anchored at a random other bar.

    Reconstructs the gap's geometry *relative to price* at an unrelated bar, so
    the control differs from the real gap in one respect only: nothing special
    happened to create it. Returns None when no anchor with enough forward room
    exists.
    """
    n = len(df)
    lo_i, hi_i = 20, n - horizon - 1
    if hi_i <= lo_i:
        return None
    width = gap["width"]
    near_off = gap["distance_pct"] / 100.0
    for _ in range(20):                       # a few tries, then give up
        j = rng.randint(lo_i, hi_i)
        if abs(j - gap["index"]) < horizon:    # don't overlap the real gap's window
            continue
        p = float(df["close"].iloc[j])
        if gap["direction"] == "bull":
            top = p * (1 - near_off)
            bot = top - width
        else:
            bot = p * (1 + near_off)
            top = bot + width
        if bot <= 0:
            continue
        return {"index": j, "direction": gap["direction"], "bot": bot, "top": top}
    return None


def study_series(df: pd.DataFrame, *, horizon: int = 40,
                 rng: random.Random | None = None,
                 atr_mult: float = 0.5) -> list[dict[str, Any]]:
    """Per-gap records for one symbol: real fills and matched placebo fills."""
    rng = rng or random.Random(7)
    n = len(df)
    rows: list[dict[str, Any]] = []
    for g in find_gaps(df, atr_mult=atr_mult):
        if g["index"] + horizon > n - 1:      # censored — excluded, not counted as unfilled
            continue
        real = bars_to_fill(df, g["index"], g["direction"], g["bot"], g["top"], horizon)
        pb = placebo_for(df, g, horizon, rng)
        fake = (bars_to_fill(df, pb["index"], pb["direction"], pb["bot"], pb["top"], horizon)
                if pb else {m: None for m in FILL_MODES})
        rows.append({
            "direction": g["direction"], "width_atr": g["width_atr"],
            "distance_pct": g["distance_pct"], "has_placebo": pb is not None,
            **{f"real_{m}": real[m] for m in FILL_MODES},
            **{f"placebo_{m}": fake[m] for m in FILL_MODES},
        })
    return rows


def _two_prop_z(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float]:
    """Two-proportion z test (normal approximation) -> (z, two-sided p).

    Included because a fill-rate difference without a significance figure is the
    thing this repo keeps refusing to ship (backlog B-20a). No scipy dependency:
    the normal CDF is `math.erfc`.
    """
    if not n1 or not n2:
        return (float("nan"), float("nan"))
    p1, p2 = k1 / n1, k2 / n2
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return (float("nan"), float("nan"))
    z = (p1 - p2) / se
    return (z, math.erfc(abs(z) / math.sqrt(2)))


def summarize(rows: Iterable[dict[str, Any]], horizon: int = 40) -> dict[str, Any]:
    """Fill % and median bars-to-fill per mode, real vs matched placebo."""
    df = pd.DataFrame(list(rows))
    if df.empty:
        return {"n": 0, "modes": [], "horizon": horizon}
    with_pb = df[df["has_placebo"]]
    modes = []
    for m in FILL_MODES:
        real, fake = df[f"real_{m}"], with_pb[f"placebo_{m}"]
        rk, rn = int(real.notna().sum()), int(len(real))
        pk, pn = int(fake.notna().sum()), int(len(fake))
        z, pval = _two_prop_z(rk, rn, pk, pn)
        modes.append({
            "mode": m,
            "real_fill_pct": rk / rn * 100.0 if rn else None,
            "real_median_bars": float(real.dropna().median()) if rk else None,
            "placebo_fill_pct": pk / pn * 100.0 if pn else None,
            "placebo_median_bars": float(fake.dropna().median()) if pk else None,
            "delta_pct_points": (rk / rn - pk / pn) * 100.0 if rn and pn else None,
            "z": z, "p_value": pval, "n_real": rn, "n_placebo": pn,
        })
    return {
        "n": len(df), "horizon": horizon, "modes": modes,
        "bull": int((df["direction"] == "bull").sum()),
        "bear": int((df["direction"] == "bear").sum()),
        "median_width_atr": float(df["width_atr"].median()),
        "median_distance_pct": float(df["distance_pct"].median()),
    }


# ── Runner ──────────────────────────────────────────────────────────────────
DEFAULT_UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "ITC.NS",
    "SBIN.NS", "LT.NS", "AXISBANK.NS", "MARUTI.NS", "SUNPHARMA.NS", "TITAN.NS",
    "BAJFINANCE.NS", "WIPRO.NS", "ADANIENT.NS", "HINDUNILVR.NS", "NTPC.NS",
    "TATASTEEL.NS", "POWERGRID.NS", "ULTRACEMCO.NS",
]


def run(universe: list[str] | None = None, *, period: str = "5y",
        horizon: int = 40, seed: int = 7) -> dict[str, Any]:
    import warnings
    warnings.filterwarnings("ignore")
    import yfinance as yf

    universe = universe or DEFAULT_UNIVERSE
    data = yf.download(universe, period=period, interval="1d", group_by="ticker",
                       auto_adjust=False, progress=False, threads=True)
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    used = 0
    for s in universe:
        try:
            d = data[s].dropna().rename(columns=str.lower)[
                ["open", "high", "low", "close", "volume"]].reset_index(drop=True)
        except Exception:
            continue
        if len(d) < horizon + 60:
            continue
        used += 1
        rows.extend(study_series(d, horizon=horizon, rng=rng))
    out = summarize(rows, horizon)
    out["symbols_used"] = used
    out["period"] = period
    return out


def main() -> None:                              # pragma: no cover
    res = run()
    print(f"FVG fill study — {res['symbols_used']} symbols, {res['period']} daily, "
          f"horizon {res['horizon']} bars")
    print(f"{res['n']} gaps measured ({res['bull']} bull / {res['bear']} bear); "
          f"median width {res['median_width_atr']:.2f}x ATR, "
          f"median distance {res['median_distance_pct']:.2f}%\n")
    hdr = (f"{'fill definition':<13} {'REAL %':>7} {'med bars':>9} "
           f"{'PLACEBO %':>10} {'med bars':>9} {'delta pp':>9} {'p':>9}")
    print(hdr)
    print("-" * len(hdr))
    for m in res["modes"]:
        print(f"{m['mode']:<13} {m['real_fill_pct']:>6.1f}% "
              f"{(m['real_median_bars'] if m['real_median_bars'] is not None else float('nan')):>9.1f} "
              f"{m['placebo_fill_pct']:>9.1f}% "
              f"{(m['placebo_median_bars'] if m['placebo_median_bars'] is not None else float('nan')):>9.1f} "
              f"{m['delta_pct_points']:>+8.1f} {m['p_value']:>9.4f}")
    print("\nplacebo = same width, same distance from price, random anchor bar.")
    print("p = two-proportion z test on fill rate, real vs placebo.")


if __name__ == "__main__":                       # pragma: no cover
    main()
