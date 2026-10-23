#!/usr/bin/env python3
"""yearly_opening_range_study.py — B-98 measurement.

Runs the design in analyses/Yearly-Opening-Range-Pre-Registration.md.

Implementation choices (stated here so they cannot drift):
  PANEL     tools/cache/cardinality_deep/*_1d.json: 442 names, event years 2007-2026
            (20 calendar years; early years are thinly populated). The by-year test
            therefore has up to 20 independent observations.
  A         event = first close outside the January range (calendar_anchor).
            entry = next open, exit = close h sessions later, signed by direction.
            BASELINE = mean signed return of EVERY bar in the same symbol-year
            (Feb..Dec) with the same horizon, same sign. Same-year baseline cancels
            the market-year effect. Costs are identical on both arms so they cancel
            in the difference; absolute edge is shown net of COST_INDIAN round trip.
            DECIDING TEST: one mean excess per calendar year, t-test across years.
  B         state on the last session of each quarter: ABOVE vs BELOW, forward h=60
            from next open. One spread per quarter-end date, tested across dates.
  C         DEVIATION from the registered text: `still_outside` is measured at the
            frame END, which uses the future. Here HELD = close still beyond the
            level HOLD_K sessions after the break (known then); returns start at
            the open after that bar, for HELD vs FAILED, signed.
  FLOOR     n >= 200 per arm else INCONCLUSIVE.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import calendar_anchor as ca  # noqa: E402

DEEP = HERE / "cache" / "cardinality_deep"
HORIZONS = (20, 60, 120)
PRIMARY = 60
HOLD_K = 10
MIN_N = 200
COST_PCT = 0.29  # ~COST_INDIAN round trip, percent


def t_sf(t: float, df: int) -> float:
    """Two-sided p for Student t via numerical integration (no scipy here)."""
    if df < 1 or not np.isfinite(t):
        return float("nan")
    x = np.linspace(0, abs(t), 20001)
    lc = math.lgamma((df + 1) / 2) - math.lgamma(df / 2) - 0.5 * math.log(df * math.pi)
    pdf = np.exp(lc - (df + 1) / 2 * np.log1p(x * x / df))
    area = float(np.sum((pdf[1:] + pdf[:-1]) / 2 * np.diff(x)))
    return float(min(1.0, max(0.0, 1 - 2 * area)))


def ttest(x):
    x = np.asarray([v for v in x if np.isfinite(v)], float)
    n = len(x)
    if n < 2:
        return float(x.mean()) if n else float("nan"), float("nan"), n
    sd = x.std(ddof=1)
    if sd == 0:
        return float(x.mean()), float("nan"), n
    t = x.mean() / (sd / math.sqrt(n))
    return float(x.mean()), t_sf(t, n - 1), n


def load():
    out = {}
    for p in sorted(DEEP.glob("*_1d.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        b = d["bars"]
        if len(b) < 300:
            continue
        idx = pd.to_datetime([x["time"] for x in b], unit="s").normalize()
        df = pd.DataFrame({k: [x[k] for x in b] for k in ("open", "high", "low", "close")}, index=idx)
        df = df[~df.index.duplicated()]
        out[d["symbol"]] = df
    return out


def fwd(o, c, t, h):
    """Return % from open[t+1] to close[t+1+h], or nan."""
    if t + 1 + h >= len(c) or o[t + 1] <= 0:
        return np.nan
    return (c[t + 1 + h] / o[t + 1] - 1) * 100.0


def main() -> int:
    panel = load()
    print(f"panel: {len(panel)} names")
    A = {h: [] for h in HORIZONS}      # rows: year, sign*ret, sign*baseline, dir, sym
    C = {h: [] for h in HORIZONS}
    B = {}                              # (date) -> {'ABOVE': [...], 'BELOW': [...]}
    nyears = 0
    for sym, df in panel.items():
        o = df["open"].to_numpy(float); c = df["close"].to_numpy(float)
        idx = df.index
        for y in ca.years_covered(df):
            # require a full January: first session within the first week
            rng = ca.yearly_opening_range(df, y)
            if rng is None or rng["sessions"] < 15:
                continue
            ev = ca.detect_yearly_opening_range(df, y)
            if ev is None or not ev["broke"]:
                continue
            nyears += 1
            pos = idx.get_loc(pd.Timestamp(ev["break_date"]))
            sgn = 1.0 if ev["direction"] == "up" else -1.0
            yr_bars = np.where((idx.year == y) & (idx.month > 1))[0]
            hi, lo = rng["high"], rng["low"]
            for h in HORIZONS:
                f = np.array([fwd(o, c, t, h) for t in yr_bars])
                base = np.nanmean(f) if np.isfinite(f).any() else np.nan
                r = fwd(o, c, pos, h)
                if np.isfinite(r) and np.isfinite(base):
                    A[h].append((y, sgn * r, sgn * base, ev["direction"], sym))
                # claim C: held/failed known at pos+HOLD_K
                q = pos + HOLD_K
                if q + 1 < len(c) and idx[q].year == y:
                    held = (c[q] > hi) if sgn > 0 else (c[q] < lo)
                    rr = fwd(o, c, q, h)
                    bb = np.nanmean([fwd(o, c, t, h) for t in yr_bars if t > q] or [np.nan])
                    if np.isfinite(rr) and np.isfinite(bb):
                        C[h].append((y, sgn * rr, sgn * bb, bool(held), sym))
            # claim B: quarter-end state
            for qm in (3, 6, 9, 12):
                m = np.where((idx.year == y) & (idx.month == qm))[0]
                if len(m) == 0 or m[-1] + 1 >= len(c):
                    continue
                t = m[-1]
                st = "ABOVE" if c[t] > hi else "BELOW" if c[t] < lo else "INSIDE"
                r = fwd(o, c, t, PRIMARY)
                if st != "INSIDE" and np.isfinite(r):
                    B.setdefault(idx[t].date().isoformat(), {"ABOVE": [], "BELOW": []})[st].append(r)

    print(f"symbol-years with a break: {nyears}\n")
    res = {}
    print("== A: direction of the first break (signed, vs same-symbol-year every-bar baseline) ==")
    for h in HORIZONS:
        rows = A[h]
        n = len(rows)
        if not n:
            continue
        ex = np.array([r[1] - r[2] for r in rows])
        raw = np.array([r[1] for r in rows])
        pm, pp, _ = ttest(ex)
        byyear = {}
        for y in sorted({r[0] for r in rows}):
            byyear[y] = float(np.mean([r[1] - r[2] for r in rows if r[0] == y]))
        ym, yp, yn = ttest(list(byyear.values()))
        npos = sum(v > 0 for v in byyear.values())
        status = "INCONCLUSIVE(n<200)" if n < MIN_N else ""
        print(f"h={h:>3}: n={n} raw signed {raw.mean():+.2f}% (net {raw.mean()-COST_PCT:+.2f}%) "
              f"excess {pm:+.2f}pp pooled p={pp:.3f} | BY-YEAR mean {ym:+.2f}pp p={yp:.3f} "
              f"({npos}/{yn} yrs +) {status}")
        print("        by year: " + ", ".join(f"{y}:{v:+.2f}" for y, v in byyear.items()))
        up = [r for r in rows if r[3] == "up"]; dn = [r for r in rows if r[3] == "down"]
        print(f"        up n={len(up)} excess {np.mean([r[1]-r[2] for r in up]):+.2f} | "
              f"down n={len(dn)} excess {np.mean([r[1]-r[2] for r in dn]):+.2f}")
        res[f"A_h{h}"] = dict(n=n, excess=pm, pooled_p=pp, byyear=byyear, byyear_mean=ym, byyear_p=yp)

    print("\n== B: quarter-end state, ABOVE minus BELOW, fwd 60d, one spread per date ==")
    sp = []; na = nb = 0
    for d, v in sorted(B.items()):
        if len(v["ABOVE"]) >= 10 and len(v["BELOW"]) >= 10:
            sp.append(np.mean(v["ABOVE"]) - np.mean(v["BELOW"]))
        na += len(v["ABOVE"]); nb += len(v["BELOW"])
    m, p, n = ttest(sp)
    print(f"dates={n} spread {m:+.2f}pp p={p:.3f} (ABOVE obs {na}, BELOW obs {nb}; dates overlap -> description)")
    res["B"] = dict(dates=n, spread=m, p=p)

    print(f"\n== C: HELD vs FAILED at +{HOLD_K} sessions (signed, excess over same-year baseline) ==")
    for h in HORIZONS:
        rows = C[h]
        hd = [r for r in rows if r[3]]; fl = [r for r in rows if not r[3]]
        if not hd or not fl:
            continue
        yrs = sorted({r[0] for r in rows})
        diffs = []
        for y in yrs:
            a = [r[1] - r[2] for r in hd if r[0] == y]; b = [r[1] - r[2] for r in fl if r[0] == y]
            if len(a) >= 10 and len(b) >= 10:
                diffs.append(np.mean(a) - np.mean(b))
        ym, yp, yn = ttest(diffs)
        st = "INCONCLUSIVE" if min(len(hd), len(fl)) < MIN_N else ""
        print(f"h={h:>3}: held n={len(hd)} {np.mean([r[1]-r[2] for r in hd]):+.2f}pp | failed n={len(fl)} "
              f"{np.mean([r[1]-r[2] for r in fl]):+.2f}pp | BY-YEAR held-failed {ym:+.2f}pp p={yp:.3f} "
              f"({sum(d>0 for d in diffs)}/{yn} yrs +) {st}")
        res[f"C_h{h}"] = dict(held=len(hd), failed=len(fl), byyear_diff=ym, p=yp)

    out = HERE / "cache" / "yearly_opening_range_study.json"
    out.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
