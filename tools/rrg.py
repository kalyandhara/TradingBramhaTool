"""rrg.py — Relative Rotation Graph: RS-Ratio vs RS-Momentum, with tails.

SR-6 of [[analyses/Sector-Rotation-Orbit-Data-Source-Roadmap]].

Why this exists
---------------
The Sector Map already has a "Sector Rotation Quadrant", but it plots 1Y return
against 1M return. That is a momentum scatter, not a rotation graph: both axes
are absolute returns, so in a market that rises together every sector sits in the
top-right and the picture says nothing. An RRG measures each sector *against the
benchmark* and adds the second derivative — is its relative strength itself
improving or decaying — which is what makes the four quadrants a cycle rather
than a ranking.

It also needs **no ownership data**, which is the point. The orbit chart's FII
axis is blocked behind quarterly filings and a slow backfill (SR-2); this reads
only prices we already cache for the eleven sector indices, so it ships alone.

What it is NOT: it is a price-relative measure. It says a sector is
outperforming, not that money is flowing into it. Reading one for the other is
the mistake [[concepts/FPV-Flow-Price-Volume-Ownership]] warns about, and the
orbit chart's ownership axis remains the thing this does not replace.

On the formula
--------------
Julius de Kempenaer's JdK RS-Ratio / RS-Momentum are **proprietary**; what
follows is the standard public approximation, and it is written down here rather
than presented as the real thing:

    RS        = 100 × sector / benchmark
    RS-Ratio  = 100 + zscore(RS, window)
    RS-Moment = 100 + zscore(100 × RS-Ratio / RS-Ratio.shift(mom_period), window)

Both axes centre on 100, so the quadrant boundaries are the 100/100 cross.

**The caveat that matters**, stated because the chart cannot state it: the
z-score normalises each sector against *its own* history. So a sector at 101.5 is
1.5 standard deviations strong *for itself*, and comparing 101.5 in one sector
against 101.5 in another is not strictly meaningful — the axis is a per-sector
standardisation, not a common scale. Read the quadrant and the direction of
travel, not the absolute coordinates.

Convention: RRG is normally read on **weekly** bars. Daily is available and is
noticeably noisier — a sector can cross a quadrant boundary and come straight
back on two days of chop.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

#: Rotation is conventionally clockwise: Improving -> Leading -> Weakening ->
#: Lagging -> Improving. Names match the existing quadrant chart on the Sector
#: Map so the two surfaces do not use different words for the same corner.
QUADRANTS = {
    "Leading":   {"tone": "good",   "desc": "Outperforming, and still strengthening"},
    "Weakening": {"tone": "warn",   "desc": "Still outperforming, but momentum is decaying"},
    "Lagging":   {"tone": "risk",   "desc": "Underperforming, and still weakening"},
    "Improving": {"tone": "info",   "desc": "Underperforming, but momentum is turning up"},
}

DEFAULT_WINDOW = 14      # periods used for the z-score
DEFAULT_MOM    = 4       # periods for the RS-Ratio rate of change
DEFAULT_TAIL   = 8       # points drawn per sector


def _close(df: pd.DataFrame) -> pd.Series | None:
    """The close column, whatever this frame calls it. None if absent."""
    if df is None or not len(df):
        return None
    col = next((c for c in ("Close", "close", "Adj Close") if c in df.columns), None)
    if col is None:
        return None
    s = pd.Series(df[col].values, index=pd.to_datetime(df.index)).dropna()
    return s if len(s) else None


def _resample(s: pd.Series, freq: str) -> pd.Series:
    """Daily series -> weekly/monthly closes. 'D' passes through untouched."""
    if freq in ("D", "daily", None):
        return s
    rule = {"W": "W-FRI", "weekly": "W-FRI", "M": "ME", "monthly": "ME"}.get(freq, freq)
    return s.resample(rule).last().dropna()


def _zscore(s: pd.Series, window: int) -> pd.Series:
    mean = s.rolling(window).mean()
    sd = s.rolling(window).std()
    # A window with no dispersion has an undefined z-score, not a zero one — and
    # "no dispersion" has to mean *near* zero, not exactly zero. A window that
    # barely moves leaves sd at ~1e-14, and dividing by that turns floating-point
    # noise into a ±40 standard-score: a violently confident reading computed
    # from nothing. Caught in testing on a synthetic constant-decay series, which
    # produced RS-Momentum 101.5 where the honest answer was "undefined".
    # Threshold is relative to the level so it holds at any price scale.
    sd = sd.mask(sd < (mean.abs() * 1e-9 + 1e-12))
    return (s - mean) / sd


def relative_strength(sector: pd.Series, bench: pd.Series) -> pd.Series:
    """100 × sector / benchmark, on the dates both actually have."""
    joined = pd.concat([sector.rename("s"), bench.rename("b")], axis=1,
                       join="inner").dropna()
    joined = joined[joined["b"] != 0]
    if joined.empty:
        return pd.Series(dtype=float)
    return 100.0 * joined["s"] / joined["b"]


def rs_ratio_momentum(rs: pd.Series, window: int = DEFAULT_WINDOW,
                      mom_period: int = DEFAULT_MOM) -> pd.DataFrame:
    """(rs_ratio, rs_momentum) for one relative-strength series."""
    ratio = 100.0 + _zscore(rs, window)
    mom_raw = 100.0 * ratio / ratio.shift(mom_period)
    momentum = 100.0 + _zscore(mom_raw, window)
    return pd.DataFrame({"rs_ratio": ratio, "rs_momentum": momentum})


def quadrant(rs_ratio: float, rs_momentum: float) -> str:
    if rs_ratio >= 100:
        return "Leading" if rs_momentum >= 100 else "Weakening"
    return "Improving" if rs_momentum >= 100 else "Lagging"


def compute(frames: dict[str, Any], display_names: dict[str, str],
            benchmark: Any, *, freq: str = "W",
            window: int = DEFAULT_WINDOW, mom_period: int = DEFAULT_MOM,
            tail: int = DEFAULT_TAIL) -> dict[str, Any]:
    """RRG tails for every sector with enough history.

    `frames` / `benchmark` are the OHLCV frames the Sector Map already caches.
    A sector without enough bars is **omitted and counted**, never plotted at the
    100/100 origin — a sector we could not measure must not render as one sitting
    neutrally in the middle of the chart.
    """
    bench = _close(benchmark)
    if bench is None:
        return {"sectors": [], "skipped": list(display_names.values()),
                "reason": "benchmark unavailable", "freq": freq,
                "window": window, "mom_period": mom_period, "tail": tail}
    bench = _resample(bench, freq)

    # z-score needs `window` points, the ROC shifts by `mom_period`, and the tail
    # wants `tail` finished points on top of both.
    need = window + mom_period + tail

    out, skipped = [], []
    for ticker, name in display_names.items():
        px = _close(frames.get(ticker))
        if px is None:
            skipped.append(name)
            continue
        rs = relative_strength(_resample(px, freq), bench)
        if len(rs) < need:
            skipped.append(name)
            continue
        rm = rs_ratio_momentum(rs, window, mom_period).dropna()
        if len(rm) < 2:
            skipped.append(name)
            continue
        pts = rm.tail(tail)
        points = [{"date": idx.strftime("%Y-%m-%d"),
                   "rs_ratio": round(float(r.rs_ratio), 2),
                   "rs_momentum": round(float(r.rs_momentum), 2)}
                  for idx, r in pts.iterrows()]
        last = points[-1]
        out.append({
            "ticker": ticker, "name": name, "points": points,
            "rs_ratio": last["rs_ratio"], "rs_momentum": last["rs_momentum"],
            "quadrant": quadrant(last["rs_ratio"], last["rs_momentum"]),
            "tone": QUADRANTS[quadrant(last["rs_ratio"], last["rs_momentum"])]["tone"],
        })

    # Strongest first: distance from the origin along the leading diagonal is the
    # usual reading of "how far into Leading is it".
    out.sort(key=lambda d: (d["rs_ratio"] - 100) + (d["rs_momentum"] - 100),
             reverse=True)
    return {"sectors": out, "skipped": skipped, "reason": None, "freq": freq,
            "window": window, "mom_period": mom_period, "tail": tail,
            "as_of": out[0]["points"][-1]["date"] if out else None}


if __name__ == "__main__":
    ok = True

    # 1. Quadrant boundaries, all four corners plus the 100/100 cross.
    cases = [(101, 101, "Leading"), (101, 99, "Weakening"),
             (99, 99, "Lagging"),   (99, 101, "Improving"),
             (100, 100, "Leading")]
    for r, m, want in cases:
        got = quadrant(r, m)
        ok &= got == want
        print(f"  quadrant({r},{m}) = {got:<10} expected {want:<10} "
              f"{'OK' if got == want else 'FAIL'}")

    idx = pd.date_range("2024-01-01", periods=400, freq="B")
    bench = pd.DataFrame({"Close": np.linspace(100, 130, 400)}, index=idx)

    # 2. ACCELERATING outperformance -> Leading.
    #    Note a *linear* ramp does NOT land here: the ratio of two straight lines
    #    is concave, so relative strength decelerates and the honest answer is
    #    Weakening. Relative strength has to be convex to read as Leading.
    accel = pd.DataFrame({"Close": 100 * np.exp(np.linspace(0, 0.9, 400))}, index=idx)
    # 3. ACCELERATING decline -> Lagging. Convex-down, for the mirror of the
    #    reason above: a steady rate of decay leaves the standardised ratio flat,
    #    so momentum reads neutral rather than negative. Momentum is the change
    #    in the *standardised* ratio, not in raw relative strength.
    fading = pd.DataFrame(
        {"Close": 100 * np.exp(-1.6 * np.linspace(0, 1, 400) ** 2)}, index=idx)
    # 4. Too little history -> skipped, never plotted at the 100/100 origin.
    stub = pd.DataFrame({"Close": np.linspace(100, 110, 5)}, index=idx[:5])

    res = compute({"A": accel, "F": fading, "T": stub},
                  {"A": "Accelerating", "F": "Fading", "T": "TooShort"}, bench)
    for s in res["sectors"]:
        print(f'  {s["name"]:<14} RS-Ratio {s["rs_ratio"]:7.2f}  '
              f'RS-Mom {s["rs_momentum"]:7.2f}  -> {s["quadrant"]}')
    print("  skipped:", res["skipped"])

    got = {s["name"]: s["quadrant"] for s in res["sectors"]}
    ok &= got.get("Accelerating") == "Leading"
    ok &= got.get("Fading") == "Lagging"
    ok &= res["skipped"] == ["TooShort"]
    ok &= "TooShort" not in got

    # 5. A missing benchmark must skip everything rather than invent an origin.
    empty = compute({"A": accel}, {"A": "Accelerating"}, None)
    ok &= empty["sectors"] == [] and empty["reason"] == "benchmark unavailable"
    print(f"  no-benchmark path: {empty['reason']!r}")

    print("SELF-CHECK", "PASSED" if ok else "FAILED")
    raise SystemExit(0 if ok else 1)
