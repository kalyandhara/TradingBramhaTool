#!/usr/bin/env python3
"""point_in_time_quality.py — what was knowable about a company on a given date.

The blocker under B-57 and B-38. Every fundamental figure this desk holds is a
CURRENT snapshot, and scoring a 2024 entry against 2026 statements is lookahead
of the most flattering kind: the screen "knows" which companies went on to grow.
This module answers the only question a backtest may ask — *what had actually
been published by date T* — and refuses to answer anything else.

── The one rule ─────────────────────────────────────────────────────────────────
A fiscal year is usable only from `period_end + ANNUAL_FILING_LAG_DAYS`. SEBI
LODR gives listed companies 60 days for audited annual results, so a FY ending
31-Mar is not knowable until roughly end-May. That constant and the as-of pattern
are `fundamentals_deep.ANNUAL_FILING_LAG_DAYS` and `.fcf_negative_streak_as_of`
respectively — both are reused here rather than re-derived, so the desk has ONE
filing-lag assumption and not two that drift apart.

── Unknown is not a failure, and this module will not let you conflate them ─────
`verdict` is a **three-state**: True (passed), False (failed), None (could not be
evaluated — too few published years, or no statement coverage). A name that had
not yet reported three years has not failed the gate; it was never tested. Fold
those into a denominator and the pass rate is understated by exactly the coverage
hole, which is the same three-state discipline FR-4's red-flags checklist
enforces (NOT_CHECKED never reads as a pass).

── What this module deliberately does NOT fix ───────────────────────────────────
**Survivorship.** The universe a caller passes in is today's listed names, so
anything delisted in the window is absent and every result built on this is an
UPPER BOUND. No free data source fixes that, and pretending otherwise by silently
proceeding is worse than saying it. `as_of_report()` prints it on every run.

**Restatements.** yfinance serves the CURRENT statement frames. If FY24 was later
restated, this module hands back the restated figure with an FY24 label and a
2024 publication date — the number a screener sees today, not the number the
market saw then. Unfixable without a vendor point-in-time database; recorded
because it is the residual lookahead nobody can close here.

CLI:
    py -3 tools/point_in_time_quality.py RELIANCE --as-of 2024-06-30
    py -3 tools/point_in_time_quality.py --self-test
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Optional

import fundamentals_deep as fd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache" / "pit_quality"

#: Reused, not redefined — see the module docstring.
LAG_DAYS = fd.ANNUAL_FILING_LAG_DAYS

#: Years of published history the gate needs before it will return a verdict.
MIN_YEARS = 3

#: The growth window, in years. 3 to match `revenue_cagr_3y`, the figure the rest
#: of the desk already reasons about.
WINDOW_YEARS = 3

#: The base year is picked by SPAN, not by position, and any span in this band is
#: acceptable -- the one closest to `WINDOW_YEARS` wins. A band rather than a
#: tolerance because yfinance commonly serves only four annual columns, so
#: demanding a base exactly 3y back would refuse every name whose oldest column
#: is 2y old while `MIN_YEARS` said 3 published years was enough. The floor stops
#: a 1-year change being read as a growth rate; the ceiling stops a decade-old
#: base being averaged into one.
MIN_SPAN_YEARS = 1.5
MAX_SPAN_YEARS = 5.0


# ── extraction: values WITH their period ends ────────────────────────────────

class _Frameish:
    """A cached series wearing just enough of a frame's shape to re-enter the
    same extraction path as a live one, instead of a parallel path that drifts."""

    def __init__(self, pairs: list[tuple[dt.date, float]]):
        self.pairs = pairs


def _extract_from_frame(df, names: Iterable[str]) -> list[tuple[dt.date, float]]:
    """`[(period_end, value)]`, newest first, dropping unusable entries.

    `fundamentals_deep._row` returns the values and `._period_ends` the labels;
    neither alone is point-in-time usable, and pairing them is the whole trick —
    without the labels a caller holds five numbers and cannot say which were
    public on a given date.
    """
    row = fd._row(df, names)
    if row is None:
        return []
    ends = fd._period_ends(df)
    out: list[tuple[dt.date, float]] = []
    for i, raw in enumerate(row.tolist()):
        if i >= len(ends):
            break
        val = fd._num(raw)
        if val is None:
            continue
        try:
            end = dt.date.fromisoformat(ends[i])
        except Exception:
            continue
        out.append((end, val))
    out.sort(key=lambda p: p[0], reverse=True)
    return out


def series_with_dates(df, names: Iterable[str]) -> list[tuple[dt.date, float]]:
    """The one extractor every caller uses.

    A cached `_Frameish` already holds the pairs; a live yfinance frame is parsed.
    Dispatching here rather than at the call sites keeps a single extraction rule
    -- two extractors is how a cached study and a live one quietly disagree.
    """
    if isinstance(df, _Frameish):
        return list(df.pairs)
    return _extract_from_frame(df, names)


def known_as_of(series: list[tuple[dt.date, float]], as_of: dt.date,
                lag_days: int = LAG_DAYS) -> list[tuple[dt.date, float]]:
    """Only the years whose results had been PUBLISHED by `as_of`."""
    return [(e, v) for e, v in series if e + dt.timedelta(days=lag_days) <= as_of]


def _base_for(known: list[tuple[dt.date, float]], window: int = WINDOW_YEARS,
              ) -> Optional[tuple[dt.date, float, float]]:
    """The comparison year, plus the TRUE elapsed span between it and the latest.

    Positional indexing ("three columns back") assumes yfinance never drops a
    column and every company reports annually on schedule. Neither holds, and a
    silent 2-year gap scored as a 3-year CAGR overstates growth by half. So the
    base is chosen by DATE, and the span that is actually used is returned with
    it rather than assumed -- `quality_as_of` reports it, so a 2-year rate is
    never read as a 3-year one.

    Among the spans inside [MIN_SPAN_YEARS, MAX_SPAN_YEARS], the one nearest
    `window` wins. Returns None when no year qualifies, which is UNKNOWN and not
    a failure.
    """
    if len(known) < 2:
        return None
    latest_end = known[0][0]
    best = None
    for end, val in known[1:]:
        span = (latest_end - end).days / 365.25
        if span < MIN_SPAN_YEARS or span > MAX_SPAN_YEARS:
            continue
        d = abs(span - window)
        if best is None or d < best[0]:
            best = (d, end, val, span)
    if best is None:
        return None
    _, end, val, span = best
    return end, val, span


# ── the gate ─────────────────────────────────────────────────────────────────

def quality_as_of(stmts: dict[str, Any], as_of, *, lag_days: int = LAG_DAYS,
                  min_years: int = MIN_YEARS) -> dict[str, Any]:
    """Revenue growth AND operating-cash-flow growth, as known on `as_of`.

    Returns the CONTINUOUS measures alongside the boolean, because B-57's
    secondary tightens the gate from a sign test to a cross-sectional
    top-quartile rank — and a function that returned only True/False would force
    that rank to be computed from a second, differently-built number.

    `verdict` is three-state: True / False / None (see the module docstring).
    """
    if isinstance(as_of, dt.datetime):
        as_of = as_of.date()
    elif isinstance(as_of, str):
        as_of = dt.date.fromisoformat(as_of[:10])

    out: dict[str, Any] = {
        "as_of": as_of.isoformat(), "lag_days": lag_days,
        "verdict": None, "reason": None,
        "revenue_cagr": None, "ocf_growth": None,
        "n_years_known": 0, "latest_fy": None, "window_years": None,
    }
    if not stmts:
        out["reason"] = "no statements"
        return out

    rev = known_as_of(series_with_dates(stmts.get("income"), fd._REVENUE),
                      as_of, lag_days)
    ocf = known_as_of(series_with_dates(stmts.get("cashflow"), fd._OCF),
                      as_of, lag_days)
    out["n_years_known"] = min(len(rev), len(ocf))
    if rev:
        out["latest_fy"] = rev[0][0].isoformat()

    if len(rev) < min_years or len(ocf) < min_years:
        out["reason"] = (f"only {out['n_years_known']} published year(s) by "
                         f"{as_of.isoformat()}, need {min_years}")
        return out

    rb, ob = _base_for(rev), _base_for(ocf)
    if rb is None or ob is None:
        out["reason"] = "no base year within tolerance of the growth window"
        return out

    _, rev_base, rev_years = rb
    _, ocf_base, _ = ob
    # The span actually measured, reported so a caller never assumes it was 3.
    out["window_years"] = round(rev_years, 2)
    out["revenue_cagr"] = fd._cagr(rev[0][1], rev_base, rev_years)
    # OCF is routinely negative, and a CAGR through a negative base is undefined
    # (`_cagr` returns None there, correctly). Growth is therefore expressed as a
    # total change over the window rather than annualised — a sign test on
    # "is operating cash flow larger than it was" survives a negative base, which
    # is exactly the company this gate most needs an opinion about.
    out["ocf_growth"] = (round((ocf[0][1] - ocf_base) / abs(ocf_base) * 100, 2)
                         if ocf_base != 0 else None)

    if out["revenue_cagr"] is None:
        out["reason"] = "revenue CAGR undefined (non-positive base year)"
        return out
    if out["ocf_growth"] is None:
        out["reason"] = "OCF growth undefined (zero base year)"
        return out

    out["verdict"] = bool(out["revenue_cagr"] > 0 and out["ocf_growth"] > 0)
    out["reason"] = "evaluated"
    return out


# ── cached statement access, so a 460-name study is not 460 fetches per run ──

def cached_statements(symbol: str, refresh: bool = False) -> dict[str, Any]:
    """Statements as the extracted (date, value) series, cached to disk.

    The raw yfinance frames are not cached — only the two series this module
    reads. Caching frames would mean re-deriving on every load and a cache file
    per symbol large enough to matter; caching the series means the study reloads
    in seconds and the extraction rules live in exactly one place.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{symbol}.json"
    if p.exists() and not refresh:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            return _rehydrate(d)
        except Exception:
            pass
    try:
        stmts = fd.fetch_statements(symbol)
    except Exception:
        stmts = {}
    rev = series_with_dates(stmts.get("income"), fd._REVENUE)
    ocf = series_with_dates(stmts.get("cashflow"), fd._OCF)
    p.write_text(json.dumps({
        "symbol": symbol,
        "revenue": [[e.isoformat(), v] for e, v in rev],
        "ocf": [[e.isoformat(), v] for e, v in ocf],
        "fetched": dt.date.today().isoformat(),
    }), encoding="utf-8")
    return {"income": _Frameish(rev), "cashflow": _Frameish(ocf)}


def _rehydrate(d: dict) -> dict[str, Any]:
    def _mk(rows):
        return _Frameish([(dt.date.fromisoformat(e), float(v)) for e, v in rows])
    return {"income": _mk(d.get("revenue") or []),
            "cashflow": _mk(d.get("ocf") or [])}


# ── reporting ────────────────────────────────────────────────────────────────

def as_of_report(symbol: str, as_of, **kw) -> str:
    r = quality_as_of(cached_statements(symbol), as_of, **kw)
    v = {True: "PASS", False: "FAIL", None: "UNKNOWN"}[r["verdict"]]
    return (f"{symbol:14} as of {r['as_of']}  {v:8} "
            f"rev_cagr={r['revenue_cagr']}  ocf_growth={r['ocf_growth']}  "
            f"window={r['window_years']}y  "
            f"known={r['n_years_known']}y  latest_fy={r['latest_fy']}  "
            f"({r['reason']})\n"
            f"{'':14} NOTE: universe is today's listed names — survivorship "
            f"makes any result built on this an UPPER BOUND.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Point-in-time quality gate")
    ap.add_argument("symbols", nargs="*")
    ap.add_argument("--as-of", default=dt.date.today().isoformat())
    ap.add_argument("--lag-days", type=int, default=LAG_DAYS)
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    if not args.symbols:
        sys.exit("give at least one symbol")
    for s in args.symbols:
        if args.refresh:
            cached_statements(s, refresh=True)
        print(as_of_report(s, args.as_of, lag_days=args.lag_days))


if __name__ == "__main__":
    main()
