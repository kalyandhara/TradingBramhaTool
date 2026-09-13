#!/usr/bin/env python3
"""multibagger_conviction_study.py — B-73 Phase 0, the measurement that IS powerable.

Phase 0's count (`multibagger_cardinality.py`) established that the shipped
multibagger screen cannot be scored on free data: reconstructed point-in-time it
leaves 46 events against a floor of 200, capped by yfinance's four annual
statement columns, which is a vendor limit and not an assumption. What CAN be
powered is the screen's institutional-conviction CORE, and this is that.

═══ PRE-REGISTRATION — committed to the backlog on 2026-09-12 BEFORE any scorer
    existed, and reproduced here verbatim so the two cannot drift ═══════════════

  CLAIM     does fresh institutional buying into a SMALL-CAP name beat the
            benchmark over 3-6 months? The institutional-conviction core:
            market cap < Rs 20,000 Cr, (FII+DII) change > 1, promoter change > -1.
            The growth and ratio legs are DROPPED, because their point-in-time
            depth does not exist.

  THIS IS NOT THE MULTIBAGGER SCREEN AND MAY NOT BORROW ITS NAME. It drops four
  of seven legs and measures 3-6 months where the word multibagger means years.
  B-65r is the precedent for why this matters: a factor that borrows credibility
  from a nearby measured claim is the specific error this desk has already made
  once.

  HORIZONS  63 and 126 trading days. 252 is reported and CANNOT decide.
  BASELINE  an equal-length window on the same name, per B-74's correction -- a
            raw return would flatter every long-only screen by the drift it sat
            through.
  STATISTIC mean return, symbol-block bootstrap, 29bps, the standing convention.
  FLOOR     200 events per cell, or it concludes nothing.
  PRIOR     no edge. B-34 measured the smallcap conviction lane WEAK
            (-0.12% @60d, +0.20% @120d) on a closely related signal, and that is
            the nearest prior this desk owns.

═══ WHAT THE REGISTRATION LEFT OPEN, resolved here and declared before the run ══

  ENTRY     the NEXT OPEN after the filing date. The registration said "the
            standing convention" and B-65's is next open; a close-of-filing-day
            entry would assume a reader who saw the filing the moment it landed.
            Filings are timestamped in the evening more often than not.

  WHAT "BEAT THE BENCHMARK" MEANS is the edge, not the raw return -- fixed by
  B-74's correction, which is the one thing this study must not repeat. A raw
  mean on a long-only screen in a rising small-cap market is a measure of the
  market, and B-74's registered bar was mis-specified in exactly that way.

  DECISION  for each deciding horizon: the edge, with a symbol-block bootstrap
            CI. An edge whose CI excludes zero and survives costs is a finding;
            anything else is a null and the screen stays a candidate list.
            No arm here can promote the multibagger screen, which drops four of
            these legs -- pre-registered so a positive cell cannot be read as
            vindication of the shipped screen.

CLI:
    py -3 tools/multibagger_conviction_study.py
    py -3 tools/multibagger_conviction_study.py --limit 50     # smoke test
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OWN = HERE / "cache" / "ownership"
BARS = HERE / "cache" / "multibagger_bars"

CR = 1e7
MCAP_MAX_CR = 20_000.0
INST_MIN = 1.0
PROMOTER_MIN = -1.0

HORIZONS_DECIDE = (63, 126)
HORIZON_REPORT = 252
COST_BPS = 29.0
N_BOOT = 2000
MIN_EVENTS = 200
PRICE_TOL_DAYS = 10       # see multibagger_cardinality; an unbounded lookup is a lookahead


def _quarter_key(label: str | None) -> tuple:
    if not label or "Q" not in label:
        return (0, 0)
    y, q = label.split("Q")
    return (int(y), int(q))


def _filed_date(entry: dict) -> dt.date | None:
    raw = (entry or {}).get("filed_on")
    if not raw:
        return None
    try:
        return dt.datetime.strptime(raw.split()[0], "%d-%b-%Y").date()
    except Exception:
        return None


def _bars(sym: str):
    p = BARS / f"{sym}_1d.json"
    if not p.exists():
        return None
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    rows = [b for b in doc.get("bars", [])
            if b and b.get("close") and b.get("open") and b.get("time")]
    if len(rows) < 200:
        return None
    return (np.array([dt.date.fromtimestamp(int(b["time"])).toordinal() for b in rows]),
            np.array([float(b["open"]) for b in rows]),
            np.array([float(b["close"]) for b in rows]))


def _bench(close: np.ndarray, h: int) -> float:
    """Mean h-day return over every valid window on this name — the equal-length
    unconditional comparison B-74's correction requires."""
    if h <= 0 or h >= len(close):
        return 0.0
    a, b = close[:len(close) - h], close[h:]
    ok = a > 0
    if not ok.any():
        return 0.0
    return float(np.mean(b[ok] / a[ok] - 1.0))


def events(limit: int = 0) -> list[dict]:
    own_syms = {os.path.basename(f)[:-5] for f in glob.glob(str(OWN / "*.json"))}
    bar_syms = {os.path.basename(f)[:-8] for f in glob.glob(str(BARS / "*_1d.json"))}
    universe = sorted(own_syms & bar_syms)
    if limit:
        universe = universe[:limit]

    cost = COST_BPS / 10000.0
    out: list[dict] = []
    for sym in universe:
        try:
            own = json.loads((OWN / f"{sym}.json").read_text(encoding="utf-8"))
        except Exception:
            continue
        quarters = own.get("quarters") or {}
        if len(quarters) < 2:
            continue
        loaded = _bars(sym)
        if loaded is None:
            continue
        days, opens, close = loaded
        ordered = sorted(quarters.items(), key=lambda kv: _quarter_key(kv[1].get("quarter")))

        for (_, prev), (_, cur) in zip(ordered, ordered[1:]):
            on = _filed_date(cur)
            if on is None:
                continue
            # entry = the NEXT open after the filing
            i = int(np.searchsorted(days, on.toordinal(), side="right"))
            if i >= len(days) or days[i] - on.toordinal() > PRICE_TOL_DAYS:
                continue
            entry = float(opens[i])
            if not entry > 0:
                continue

            shares = cur.get("shares_total")
            if not shares:
                continue
            mcap_cr = shares * entry / CR
            if mcap_cr >= MCAP_MAX_CR:
                continue

            fii = (cur.get("fii") or 0.0) - (prev.get("fii") or 0.0)
            dii = (cur.get("dii") or 0.0) - (prev.get("dii") or 0.0)
            if (fii + dii) <= INST_MIN:
                continue
            prom = (cur.get("promoter") or 0.0) - (prev.get("promoter") or 0.0)
            if prom <= PROMOTER_MIN:
                continue

            row = {"symbol": sym, "on": on.isoformat(), "mcap_cr": mcap_cr,
                   "inst": fii + dii, "promoter": prom}
            for h in (*HORIZONS_DECIDE, HORIZON_REPORT):
                if i + h < len(close):
                    raw = float(close[i + h] / entry - 1.0) - cost
                    row[f"r{h}"] = raw
                    row[f"e{h}"] = raw - _bench(close, h)
                else:
                    row[f"r{h}"] = None
                    row[f"e{h}"] = None
            out.append(row)
    return out


def _boot(rows: list[dict], key: str, rng) -> tuple[float, float]:
    by: dict[str, list[float]] = {}
    for r in rows:
        if r.get(key) is not None:
            by.setdefault(r["symbol"], []).append(r[key])
    keys = sorted(by)
    if not keys:
        return (float("nan"), float("nan"))
    arrs = {s: np.array(by[s], float) for s in keys}
    draws = np.empty(N_BOOT)
    for b in range(N_BOOT):
        pick = rng.choice(keys, size=len(keys), replace=True)
        draws[b] = np.concatenate([arrs[s] for s in pick]).mean()
    return float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    ev = events(args.limit)
    rng = np.random.default_rng(20260912)

    print()
    print("=== B-73 Phase 0 — the institutional-conviction core, scored ===")
    print("  NOT the multibagger screen: four of seven legs dropped, months not years.")
    print(f"  {len(ev)} events · {len({r['symbol'] for r in ev})} symbols · "
          f"{COST_BPS:.0f}bps · {N_BOOT}-draw symbol bootstrap")
    if ev:
        caps = np.array([r["mcap_cr"] for r in ev])
        dates = sorted(r["on"] for r in ev)
        print(f"  market cap: median {np.median(caps):,.0f} Cr · "
              f"window {dates[0]} -> {dates[-1]}")

    print()
    print(f"  {'horizon':<22}{'n':>6}{'raw':>9}{'edge':>9}   "
          f"{'95% CI on the edge':<28}decides")
    for h in (*HORIZONS_DECIDE, HORIZON_REPORT):
        rows = [r for r in ev if r.get(f"e{h}") is not None]
        n = len(rows)
        decides = "yes" if h in HORIZONS_DECIDE else "NO (reported only)"
        if not n:
            print(f"  {h:>4}d{'':<17}{n:>6}{'-':>9}{'-':>9}   {'-':<28}{decides}")
            continue
        raw = float(np.mean([r[f"r{h}"] for r in rows]))
        edge = float(np.mean([r[f"e{h}"] for r in rows]))
        lo, hi = _boot(rows, f"e{h}", rng)
        excl = "EXCLUDES 0" if (lo > 0 or hi < 0) else "includes 0"
        flag = "" if n >= MIN_EVENTS else "  UNDERPOWERED"
        print(f"  {h:>4}d (~{h // 21:>2} months){'':<6}{n:>6}"
              f"{100 * raw:>+8.2f}%{100 * edge:>+8.2f}%   "
              f"[{100 * lo:+.2f}%, {100 * hi:+.2f}%] {excl:<12}{decides}{flag}")

    print()
    print("  DECISION, as pre-registered")
    any_decided = False
    for h in HORIZONS_DECIDE:
        rows = [r for r in ev if r.get(f"e{h}") is not None]
        if len(rows) < MIN_EVENTS:
            print(f"    {h}d: {len(rows)} events under the floor of {MIN_EVENTS} — "
                  f"CONCLUDES NOTHING")
            continue
        any_decided = True
        edge = float(np.mean([r[f"e{h}"] for r in rows]))
        lo, hi = _boot(rows, f"e{h}", rng)
        if lo > 0:
            v = "EDGE — positive and the CI excludes zero"
        elif hi < 0:
            v = "NEGATIVE — the CI excludes zero on the wrong side"
        else:
            v = "NULL — CI includes zero"
        print(f"    {h}d: edge {100 * edge:+.2f}%  CI [{100 * lo:+.2f}%, "
              f"{100 * hi:+.2f}%]  -> {v}")
    if any_decided:
        print()
        print("  Pre-registered and binding: NOTHING here promotes the shipped")
        print("  multibagger screen, which requires four legs this study drops.")


if __name__ == "__main__":
    main()
