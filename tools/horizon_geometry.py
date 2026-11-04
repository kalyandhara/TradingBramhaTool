#!/usr/bin/env python3
"""horizon_geometry.py — two long-horizon views for the Six horizons board.

1. **Year spiral** (polar). Angle = day of year (one revolution = one calendar
   year, clockwise from the top), radius = close. Each year is one loop, so the
   same angle is the same time of year across years: seasonality and the size of
   each year's range read at a glance. Radius is LOG by default — on a linear
   radius the early years collapse into the centre and recent years look
   exaggerated, which is the chart's best-known way to mislead.

2. **Pivot geometry** (price-time circles). Major swing pivots from weekly bars;
   around each pivot, circles whose radii reach the pivots one and two swings
   either side of it. Where several circles cross in the FUTURE, that
   point is listed as a price-time node.

── The one thing that makes circles honest: a declared scale ──────────────
A circle on a price chart is only a circle at one zoom. Stretch the time axis
or switch to log and it becomes an ellipse through different points. So the
geometry is computed in a FIXED normalized space, stated here, not on screen:

    x = (date - first pivot) / (span to last bar + projection)   in [0, 1]
    y = (log price - log min) / (log max - log min)              in [0, 1]

Same data, same nodes, every time, on every screen. Drawn back on date/price
axes the circles may look like ellipses; that is the declared space showing
through, not an error.

Context, not a signal — same stance as the rest of the board. Nothing here has
been measured as an edge; a dense lattice always "explains" past turns.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

import numpy as np
import pandas as pd

from harmonic_patterns import find_pivots

#: Spiral keeps the most recent N calendar years (older loops crowd the centre).
SPIRAL_MAX_YEARS = 8
#: Pivot detection on weekly bars; ATR multiple chosen for MAJOR swings only.
PIVOT_ATR_MULT = 3.0
#: How many recent pivots seed circles. More = denser lattice = more false nodes.
MAX_PIVOTS = 6
#: Projection beyond the last bar, as a fraction of the pivot span.
PROJECTION_FRAC = 0.35
#: Intersections closer than this (normalized units) merge into one node.
NODE_EPS = 0.04
#: A node needs at least this many circles through it to be listed.
MIN_NODE_CIRCLES = 3


# ── 1. Year spiral ───────────────────────────────────────────────────────────
def year_spiral(daily: pd.DataFrame, max_years: int = SPIRAL_MAX_YEARS) -> dict[str, pd.DataFrame]:
    """{year: DataFrame(theta, r, date)} with theta = degrees through the year."""
    close = daily["close"].astype(float).dropna()
    close.index = pd.to_datetime(close.index)
    out: dict[str, pd.DataFrame] = {}
    for year, grp in close.groupby(close.index.year):
        if len(grp) < 5:
            continue
        days_in_year = 366 if pd.Timestamp(year=int(year), month=12, day=31).dayofyear == 366 else 365
        theta = (grp.index.dayofyear - 1) / days_in_year * 360.0
        out[str(year)] = pd.DataFrame({"theta": theta, "r": grp.values,
                                       "date": grp.index})
    for k in sorted(out)[:-max_years]:
        del out[k]
    return out


# ── 2. Pivot geometry ────────────────────────────────────────────────────────
@dataclass
class Geometry:
    ok: bool = False
    note: str | None = None
    pivots: list = field(default_factory=list)     # [(date, price, 'H'|'L')]
    circles: list = field(default_factory=list)    # [(cx, cy, r)] normalized
    nodes: list = field(default_factory=list)      # [dict(date, price, circles)]
    to_date: object = None                         # callables: normalized -> real
    to_price: object = None


def _circle_intersections(c1, c2):
    (x1, y1, r1), (x2, y2, r2) = c1, c2
    d = np.hypot(x2 - x1, y2 - y1)
    if d == 0 or d > r1 + r2 or d < abs(r1 - r2):
        return []
    a = (r1 ** 2 - r2 ** 2 + d ** 2) / (2 * d)
    h = np.sqrt(max(r1 ** 2 - a ** 2, 0.0))
    xm, ym = x1 + a * (x2 - x1) / d, y1 + a * (y2 - y1) / d
    return [(xm + h * (y2 - y1) / d, ym - h * (x2 - x1) / d),
            (xm - h * (y2 - y1) / d, ym + h * (x2 - x1) / d)]


def pivot_geometry(daily: pd.DataFrame, *, atr_mult: float = PIVOT_ATR_MULT,
                   max_pivots: int = MAX_PIVOTS) -> Geometry:
    d = daily.copy()
    d.index = pd.to_datetime(d.index)
    w = d.resample("W-FRI").agg({"open": "first", "high": "max",
                                 "low": "min", "close": "last"}).dropna()
    if len(w) < 60:
        return Geometry(note=f"needs ~60 weekly bars, history gives {len(w)}")
    piv = find_pivots(w, atr_mult=atr_mult)[:-1]      # drop provisional tail
    if len(piv) < 3:
        return Geometry(note="fewer than three major swings — no lattice to draw")
    piv = piv[-max_pivots:]
    dates = [w.index[i] for i, _, _ in piv]
    prices = [float(p) for _, p, _ in piv]

    t0, t_last = dates[0], w.index[-1]
    span = (t_last - t0).days
    t_end_days = span * (1 + PROJECTION_FRAC)
    lo, hi = np.log(min(prices)), np.log(max(prices))
    if hi <= lo:
        return Geometry(note="flat pivot range")

    def nx(t):  return (pd.Timestamp(t) - t0).days / t_end_days
    def ny(p):  return (np.log(p) - lo) / (hi - lo)
    def to_date(x):  return t0 + pd.to_timedelta(float(x) * t_end_days, unit="D")
    def to_price(y): return float(np.exp(lo + float(y) * (hi - lo)))

    pts = [(nx(t), ny(p)) for t, p in zip(dates, prices)]
    circles = []
    for i, (cx, cy) in enumerate(pts):
        for j in (i - 2, i - 1, i + 1, i + 2):
            if 0 <= j < len(pts):
                r = float(np.hypot(pts[j][0] - cx, pts[j][1] - cy))
                circles.append((cx, cy, r))

    x_now = nx(t_last)
    hits = []
    for (a, ca), (b, cb) in combinations(enumerate(circles), 2):
        if ca[:2] == cb[:2]:                       # concentric — no crossing
            continue
        for x, y in _circle_intersections(ca, cb):
            if x_now < x <= 1.0 and -0.25 <= y <= 1.25:
                hits.append((x, y, {a, b}))

    clusters: list[dict] = []
    for x, y, ids in hits:
        for c in clusters:
            if np.hypot(c["x"] - x, c["y"] - y) < NODE_EPS:
                c["ids"] |= ids
                c["pts"].append((x, y))
                break
        else:
            clusters.append({"x": x, "y": y, "ids": set(ids), "pts": [(x, y)]})
    nodes = []
    for c in clusters:
        if len(c["ids"]) < MIN_NODE_CIRCLES:
            continue
        x, y = np.mean([p[0] for p in c["pts"]]), np.mean([p[1] for p in c["pts"]])
        nodes.append({"date": to_date(x).normalize(), "price": to_price(y),
                      "circles": len(c["ids"]), "x": x, "y": y})
    nodes.sort(key=lambda n: (-n["circles"], n["date"]))

    return Geometry(ok=True, pivots=list(zip(dates, prices, [k for *_, k in piv])),
                    circles=circles, nodes=nodes[:6], to_date=to_date, to_price=to_price,
                    note=f"{len(piv)} major weekly pivots · {len(circles)} circles · "
                         f"{len(nodes)} future nodes with ≥{MIN_NODE_CIRCLES} crossings")


def circle_path(geo: Geometry, circle, n: int = 180):
    """Sample one normalized circle back to (dates, prices), clipped to [0, 1] x."""
    cx, cy, r = circle
    t = np.linspace(0, 2 * np.pi, n)
    xs, ys = cx + r * np.cos(t), cy + r * np.sin(t)
    keep = (xs >= 0) & (xs <= 1) & (ys >= -0.25) & (ys <= 1.25)
    xs = np.where(keep, xs, np.nan)
    dates = [geo.to_date(x) if np.isfinite(x) else None for x in xs]
    prices = [geo.to_price(y) if np.isfinite(x) else None for x, y in zip(xs, ys)]
    return dates, prices
