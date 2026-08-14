"""fa2_rahu_kaal_study.py — do NIFTY returns inside Rahu Kaal differ from outside?

**FA-2** from ``analyses/Financial-Astrology-Sector-Week-Roadmap``. The roadmap's
argument for running this first was that Rahu Kaal is the most *falsifiable*
claim in the repo: an exact ~90-minute window, known in advance, requiring no
detector. It only became runnable once ``intraday_store.py`` existed.

The confound that decides the whole design
------------------------------------------
Rahu Kaal occupies a **fixed 1/8 day-part per weekday**, so on Wednesday it is
*always* around midday and on Monday *always* around the open. Intraday returns
have strong time-of-day structure — the opening hour is nothing like the lunch
hour — so comparing "bars inside Rahu Kaal" against "all other bars" would
mostly measure **time of day** and report it as Rahu Kaal. That test would
produce a confident, meaningless number.

The escape is a natural experiment already present in the tradition: because the
window's position is set by weekday, **the same clock hour is inside Rahu Kaal on
one weekday and outside it on another.** So:

    stratify by clock hour, contrast inside-vs-outside WITHIN each stratum,
    then pool the strata by inverse variance.

Time of day is held exactly fixed by construction. Test A (the naive pooled
comparison) is computed too, and reported *only* to show how far off it is.

What is measured
----------------
Per hourly bar, the **intra-bar return** ``close/open - 1`` — what happened
during that hour, with no overnight gap contamination — and the **intra-bar
range** ``(high-low)/open`` as a volatility read. Both are tested: the
traditional claim is that the window is inauspicious for *beginnings*, which is
at least as plausibly a volatility statement as a drift statement, and testing
the stronger form of a claim is the honest way to test it.

A bar counts as inside the window when its **open timestamp** falls in
[rahu_kaal.start, rahu_kaal.end) — the same convention as
``intraday_store.session_slice``.

Run: ``python tools/fa2_rahu_kaal_study.py``
"""
from __future__ import annotations

import datetime as dt
import math
from typing import Any

import pandas as pd

import intraday_store as store
import panchang as pn

IST = store.IST
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri")


# ── Stats (no scipy dependency) ─────────────────────────────────────────────
def _welch(a: pd.Series, b: pd.Series) -> dict[str, Any]:
    """Welch's unequal-variance test. Normal approximation for p (n is large)."""
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return {"n1": n1, "n2": n2, "diff": None, "t": None, "p": None}
    m1, m2 = float(a.mean()), float(b.mean())
    v1, v2 = float(a.var(ddof=1)), float(b.var(ddof=1))
    se = math.sqrt(v1 / n1 + v2 / n2)
    if se == 0:
        return {"n1": n1, "n2": n2, "diff": m1 - m2, "t": None, "p": None}
    t = (m1 - m2) / se
    return {"n1": n1, "n2": n2, "mean1": m1, "mean2": m2, "diff": m1 - m2,
            "se": se, "t": t, "p": math.erfc(abs(t) / math.sqrt(2))}


def _pool_strata(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Inverse-variance pooling of per-stratum differences.

    Standard fixed-effect meta-analysis across strata: each clock hour supplies
    an independent estimate of the inside-minus-outside difference at that hour,
    weighted by its precision. Time of day cannot leak into the pooled estimate
    because it never varies within a stratum.
    """
    usable = [r for r in rows if r["se"] and r["se"] > 0]
    if not usable:
        return {"diff": None, "se": None, "z": None, "p": None, "strata": 0}
    wsum = sum(1.0 / r["se"] ** 2 for r in usable)
    diff = sum(r["diff"] / r["se"] ** 2 for r in usable) / wsum
    se = math.sqrt(1.0 / wsum)
    z = diff / se
    return {"diff": diff, "se": se, "z": z,
            "p": math.erfc(abs(z) / math.sqrt(2)), "strata": len(usable)}


# ── Data assembly ───────────────────────────────────────────────────────────
def build_bars(symbol: str = "^NSEI", interval: str = "1h", *,
               place: pn.Place = pn.MUMBAI) -> pd.DataFrame:
    """Every stored bar, tagged with weekday, clock hour and Rahu-Kaal status."""
    bars = store.read_bars(symbol, interval)
    if bars.empty:
        return bars
    out = bars.copy()
    out["date"] = [t.date() for t in out.index]
    out["clock"] = [t.strftime("%H:%M") for t in out.index]
    out["weekday"] = [t.strftime("%a") for t in out.index]
    out["ret"] = out["close"] / out["open"] - 1.0
    out["rng"] = (out["high"] - out["low"]) / out["open"]

    # One panchang computation per date, not per bar.
    windows: dict[dt.date, tuple[dt.time, dt.time]] = {}
    for d in sorted(set(out["date"])):
        rk = pn.day_parts(d, place)["rahu_kaal"]
        windows[d] = (rk["start"].time(), rk["end"].time())
    times = [t.time() for t in out.index]
    out["in_rk"] = [
        windows[d][0] <= tm < windows[d][1]
        for d, tm in zip(out["date"], times)
    ]
    return out[out["weekday"].isin(WEEKDAYS)]


def run(symbol: str = "^NSEI", interval: str = "1h",
        metric: str = "ret") -> dict[str, Any]:
    """Test A (naive, confounded) and Test B (stratified by clock hour)."""
    bars = build_bars(symbol, interval)
    if bars.empty:
        return {"error": "store is empty — run `python tools/intraday_store.py backfill`"}

    inside, outside = bars[bars["in_rk"]], bars[~bars["in_rk"]]

    # ── Test A: pooled, ignoring time of day. Reported to be dismissed. ──
    test_a = _welch(inside[metric], outside[metric])

    # ── Test B: stratify by clock hour ──
    strata: list[dict[str, Any]] = []
    for clock, g in bars.groupby("clock"):
        gi, go = g[g["in_rk"]], g[~g["in_rk"]]
        if len(gi) < 10 or len(go) < 10:      # a stratum needs both arms
            continue
        w = _welch(gi[metric], go[metric])
        if w["diff"] is None or not w.get("se"):
            continue
        w["clock"] = clock
        w["weekdays_inside"] = sorted(set(gi["weekday"]))
        strata.append(w)
    test_b = _pool_strata(strata)

    return {
        "symbol": symbol, "interval": interval, "metric": metric,
        "sessions": bars["date"].nunique(),
        "bars": len(bars), "bars_inside": len(inside), "bars_outside": len(outside),
        "first": min(bars["date"]), "last": max(bars["date"]),
        "test_a": test_a, "test_b": test_b, "strata": strata,
        "by_weekday": {
            wd: int(bars[(bars["weekday"] == wd) & bars["in_rk"]]["date"].nunique())
            for wd in WEEKDAYS
        },
    }


def _fmt_bp(x: float | None) -> str:
    return "  n/a" if x is None else f"{x * 10000:+6.2f}"


def main() -> None:                                    # pragma: no cover
    print("FA-2 — do NIFTY returns inside Rahu Kaal differ from outside?\n")
    for metric, label, unit in (("ret", "intra-bar RETURN", "bp"),
                                ("rng", "intra-bar RANGE (volatility)", "bp")):
        r = run(metric=metric)
        if r.get("error"):
            print(r["error"]); return
        print("=" * 78)
        print(f"{label}  —  {r['symbol']} {r['interval']}, "
              f"{r['sessions']} sessions {r['first']} -> {r['last']}")
        print(f"{r['bars']} bars: {r['bars_inside']} inside Rahu Kaal, "
              f"{r['bars_outside']} outside")
        print("sessions with >=1 in-window bar, by weekday: "
              + "  ".join(f"{k} {v}" for k, v in r["by_weekday"].items()))

        a, b = r["test_a"], r["test_b"]
        print(f"\n  TEST A (naive — pooled, IGNORES time of day; do not trust it)")
        print(f"    inside {_fmt_bp(a.get('mean1'))} {unit}   "
              f"outside {_fmt_bp(a.get('mean2'))} {unit}   "
              f"diff {_fmt_bp(a['diff'])} {unit}   p={a['p']:.4f}")
        print(f"\n  TEST B (stratified by clock hour — time of day held fixed)")
        print(f"    pooled diff {_fmt_bp(b['diff'])} {unit}   "
              f"z={b['z']:+.2f}   p={b['p']:.4f}   ({b['strata']} strata)")
        print(f"\n    per clock hour:")
        print(f"      {'hour':<6} {'in-RK wd':<18} {'n_in':>5} {'n_out':>6} "
              f"{'inside':>8} {'outside':>8} {'diff':>8} {'p':>8}")
        for s in r["strata"]:
            print(f"      {s['clock']:<6} {','.join(s['weekdays_inside']):<18} "
                  f"{s['n1']:>5} {s['n2']:>6} {_fmt_bp(s['mean1']):>8} "
                  f"{_fmt_bp(s['mean2']):>8} {_fmt_bp(s['diff']):>8} {s['p']:>8.4f}")
        print()

    robustness()

    print("=" * 78)
    print("Test A is confounded by design: Rahu Kaal sits at a fixed clock")
    print("position per weekday, so 'inside' is a time-of-day sample. Test B")
    print("holds the hour fixed and uses the fact that the same hour is inside")
    print("the window on one weekday and outside it on another.")
    print("4 tests run (2 metrics x 2 designs) -> Bonferroni threshold p<0.0125.")
    print()
    print("IDENTIFICATION LIMIT, and it is not fixable by more data: within a")
    print("clock hour, Rahu-Kaal status is determined ENTIRELY by weekday. So")
    print("Test B holds time of day fixed but cannot separate 'Rahu Kaal' from")
    print("'that weekday at that hour'. Any weekday effect masquerades as a")
    print("Rahu Kaal effect -- which is what the 15:15 stratum turns out to be.")


def _stratified(df: pd.DataFrame, metric: str) -> dict[str, Any]:
    strata = []
    for clock, g in df.groupby("clock"):
        gi, go = g[g["in_rk"]], g[~g["in_rk"]]
        if len(gi) < 10 or len(go) < 10:
            continue
        w = _welch(gi[metric], go[metric])
        if w["diff"] is None or not w.get("se"):
            continue
        strata.append(w)
    return _pool_strata(strata)


def robustness() -> None:                              # pragma: no cover
    """Where does the apparent volatility effect actually live?

    Kept in the script rather than in a notebook because the headline number
    (range p=0.021) does NOT survive dropping the 15:15 bar, and a reader who
    only sees the headline would draw the wrong conclusion.
    """
    bars = build_bars()
    if bars.empty:
        return
    print("=" * 78)
    print("ROBUSTNESS — the 15:15 'hour' is a 15-MINUTE STUB (NSE closes 15:30)")
    print("\n  median intra-bar range by clock hour:")
    for clock, g in bars.groupby("clock"):
        flag = "   <-- stub, not an hour" if clock == "15:15" else ""
        print(f"    {clock}  n={len(g):>4}  {g['rng'].median() * 10000:6.1f} bp{flag}")

    print(f"\n  {'configuration':<48} {'range':>8} {'p':>8}   {'return':>8} {'p':>8}")
    for label, df in (
        ("full sample (the headline)", bars),
        ("drop 15:15 stub bar", bars[bars["clock"] != "15:15"]),
        ("drop Tuesday (17 sessions, RK mostly post-close)",
         bars[bars["weekday"] != "Tue"]),
        ("drop stub + Tuesday", bars[(bars["clock"] != "15:15")
                                     & (bars["weekday"] != "Tue")]),
        ("drop stub + Tuesday + opening hour",
         bars[~bars["clock"].isin(["15:15", "09:15"]) & (bars["weekday"] != "Tue")]),
    ):
        pr, pt = _stratified(df, "rng"), _stratified(df, "ret")
        print(f"  {label:<48} {pr['diff'] * 10000:+7.2f} {pr['p']:>8.4f}   "
              f"{pt['diff'] * 10000:+7.2f} {pt['p']:>8.4f}")
    print("\n  Verdict: the volatility result is carried entirely by the stub bar.")
    print("  Remove it and nothing survives in any configuration. The return")
    print("  result is insignificant everywhere and flips sign between them.\n")


if __name__ == "__main__":                             # pragma: no cover
    main()
