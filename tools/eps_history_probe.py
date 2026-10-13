#!/usr/bin/env python3
"""eps_history_probe.py — B-141: can this desk get a long per-stock EPS history?

A DATA probe, not a study. It decides whether B-142 (does valuation at entry
predict forward return) and B-143 (an own-history valuation band) are runnable.
The pass bar is fixed HERE, before the numbers were read, the way B-48 did it.

BAR (pre-committed)
  Per name, from quarterly reported EPS in cache/earnings (yfinance earnings
  dates): build a trailing-twelve-month EPS at each quarter end that has four
  consecutive reported quarters.
    TTM_YEARS    years spanned by the TTM series.
  PASS the data question only if BOTH hold:
    1. >= 60% of the NIFTY 500 universe (cache/nse_nifty500_constituents.json)
       has TTM_YEARS >= MIN_YEARS (8), and
    2. where cache/pit_quality annual revenue overlaps, the sign of TTM-EPS growth
       agrees with revenue growth direction in >= 60% of paired years (a sanity
       check that the series is the company's earnings, not noise or a unit slip).
  FAIL otherwise. A FAIL is a finding: it ends the own-history line on this
  source and says what to fetch instead.

What it cannot see: restatements, splits/bonus adjustments (reported EPS is as
published at the time and is NOT split-adjusted by yfinance in every case — a
share-count change shows as a spurious EPS jump; flagged below), consolidated vs
standalone mixing.

CLI: py -3 tools/eps_history_probe.py [--json out.json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EARN = HERE / "cache" / "earnings"
PIT = HERE / "cache" / "pit_quality"
N500 = HERE / "cache" / "nse_nifty500_constituents.json"

MIN_YEARS = 8
COVERAGE_BAR = 0.60
AGREE_BAR = 0.60
JUMP = 4.0   # |TTM_t / TTM_{t-1}| beyond this (or sign flip across zero) is flagged as a possible split/unit artefact


def _universe() -> list[str]:
    try:
        d = json.loads(N500.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows = d if isinstance(d, list) else d.get("symbols") or d.get("constituents") or d.get("data") or []
    out = []
    for r in rows:
        s = r if isinstance(r, str) else (r.get("symbol") or r.get("Symbol"))
        if s:
            out.append(str(s).upper())
    return out


def ttm_series(events: list[dict]) -> list[tuple[str, float]]:
    """(quarter date, TTM EPS) wherever four consecutive REPORTED quarters exist."""
    rep = sorted((e["date"], e["reported"]) for e in events if e.get("reported") is not None)
    out = []
    for i in range(3, len(rep)):
        win = rep[i - 3:i + 1]
        d0 = dt.date.fromisoformat(win[0][0]); d3 = dt.date.fromisoformat(win[3][0])
        # four quarters should span ~9 months between first and last report; reject gaps
        if not (200 <= (d3 - d0).days <= 330):
            continue
        out.append((win[3][0], round(sum(v for _, v in win), 4)))
    return out


def years_spanned(ser: list[tuple[str, float]]) -> float:
    if len(ser) < 2:
        return 0.0
    return (dt.date.fromisoformat(ser[-1][0]) - dt.date.fromisoformat(ser[0][0])).days / 365.25


def artefacts(ser) -> int:
    n = 0
    for (_, a), (_, b) in zip(ser, ser[1:]):
        if a > 0 and b > 0 and (b / a > JUMP or a / b > JUMP):
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    a = ap.parse_args()

    uni = _universe()
    files = {p.stem.upper(): p for p in EARN.glob("*.json")}
    scope = [s for s in uni if s in files] if uni else list(files)
    in_uni = len(uni) or len(files)
    ys, flagged, paired, agree = [], 0, 0, 0
    for s in scope:
        d = json.loads(files[s].read_text(encoding="utf-8"))
        ser = ttm_series(d.get("events", []))
        ys.append(years_spanned(ser))
        if artefacts(ser):
            flagged += 1
        pq = PIT / f"{s}.json"
        if ser and pq.exists():
            rev = {r[0][:4]: r[1] for r in json.loads(pq.read_text(encoding="utf-8")).get("revenue", [])}
            by_y = {}
            for dte, v in ser:
                by_y[dte[:4]] = v           # latest TTM in each calendar year
            for y in sorted(by_y):
                y0 = str(int(y) - 1)
                if y in rev and y0 in rev and y0 in by_y and rev[y0] and by_y[y0]:
                    paired += 1
                    agree += int((rev[y] > rev[y0]) == (by_y[y] > by_y[y0]))
    n = len(ys)
    ok_n = sum(1 for y in ys if y >= MIN_YEARS)
    cov = ok_n / in_uni if in_uni else 0.0
    agr = agree / paired if paired else None
    print(f"universe (NIFTY 500 list): {len(uni)} | with an earnings cache file: {n}")
    print(f"TTM-EPS span, years  — median {sorted(ys)[n//2]:.1f}  max {max(ys):.1f}")
    for k in (3, 4, 5, 6, 8, 10):
        print(f"  >= {k:>2} years: {sum(1 for y in ys if y >= k):>4}  ({sum(1 for y in ys if y >= k)/in_uni*100:5.1f}% of universe)")
    print(f"possible split/unit artefacts (a >{JUMP:.0f}x TTM jump): {flagged} names")
    print(f"sanity (EPS growth direction vs revenue growth): {agree}/{paired}"
          + (f" = {agr*100:.0f}%" if agr is not None else ""))
    p1 = cov >= COVERAGE_BAR
    p2 = agr is not None and agr >= AGREE_BAR
    print(f"\nBAR 1 coverage >= {COVERAGE_BAR:.0%} at >= {MIN_YEARS}y: {cov:.1%} -> {'PASS' if p1 else 'FAIL'}")
    print(f"BAR 2 direction agreement >= {AGREE_BAR:.0%}: {'n/a' if agr is None else f'{agr:.0%}'} -> {'PASS' if p2 else 'FAIL'}")
    print("VERDICT:", "PASS" if (p1 and p2) else "FAIL — a longer EPS source is needed before B-142/B-143")
    if a.json:
        Path(a.json).write_text(json.dumps(dict(universe=len(uni), scoped=n, coverage_8y=cov, agree=agr,
                                                flagged=flagged), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
