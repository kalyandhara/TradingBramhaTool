#!/usr/bin/env python3
"""multibagger_cardinality.py — B-73 Phase 0, the COUNT before the measurement.

B-73's audit found `multibagger_candidates.py` built, shipped and never measured,
and made measuring it Phase 0 of the whole theme. This module is deliberately NOT
that measurement. It is the count that decides whether the measurement is
possible, and on which claim.

── Why counting first, again ────────────────────────────────────────────────────
The 2026-09-07 session recorded this twice. `renko_quality_cardinality.py` killed
a 40%-correction filter by showing 96% of flips already cleared it, and the QM
detector's first version reported a "pattern" on 73% of names until its pivots
were required to be consecutive. Both saved a week of backtesting a question that
could not have answered anything. B-73's own text applies the same rule to the SME
ask: *"first deliverable is a DATA probe, not a screen."* Phase 0 earns it too.

── What the screen actually is ──────────────────────────────────────────────────
`multibagger_candidates.QUERY` is a LIVE screener.in query behind a session
cookie, returning today's snapshot only. It stores no history, so there is nothing
to replay — the screen has to be RECONSTRUCTED point-in-time before it can be
scored, and this module counts whether that reconstruction has enough left in it
to be worth running.

Seven legs. Point-in-time availability, verified against the caches on disk:

    leg                                 source                        available
    ─────────────────────────────────────────────────────────────────────────────
    Market cap < 20000 Cr               shares_total x close          YES
    Sales growth 3Y > 15                pit_quality revenue           YES
    (FII + DII) change > 1              ownership quarters            YES
    Change in promoter holding > -1     ownership quarters            YES
    OPM > 10                            income stmt operating income  NO - refetch
    ROCE > 15                           balance sheet                 NO - refetch
    Debt to equity < 1                  balance sheet                 NO - refetch

The first four are free; the last three need a ~370-name yfinance statement
refetch this module does not perform. Counting the free four first is the point:
if they alone do not leave enough events, the refetch is moot.

── The event date is the FILING date, not the quarter end ───────────────────────
A holding change for the quarter ending 30-JUN is not knowable then; it becomes
public when the shareholding pattern is filed, typically three weeks later, and
the cache carries `filed_on` for exactly this reason. Forming on the quarter end
would be lookahead worth several weeks of price, on a signal whose entire content
is the change. Same discipline as `point_in_time_quality`'s 60-day annual lag.

CLI:
    py -3 tools/multibagger_cardinality.py
    py -3 tools/multibagger_cardinality.py --mcap-max 50000   # sensitivity
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
from pathlib import Path

import numpy as np

import point_in_time_quality as pit

HERE = Path(__file__).resolve().parent
OWN = HERE / "cache" / "ownership"
BARS = HERE / "cache" / "cardinality"

CR = 1e7                 # one crore, in rupees
MCAP_MAX_CR = 20_000.0   # the screen's ceiling
SALES_CAGR_MIN = 15.0    # "Sales growth 3Years > 15"
INST_MIN = 1.0           # "(Change in FII + Change in DII) > 1"
PROMOTER_MIN = -1.0      # "Change in promoter holding > -1"

#: Forward windows, in trading days. 252 is the shortest horizon on which the
#: word "multibagger" is not absurd, and it is included to show it is unreachable
#: rather than to be used.
HORIZONS = (63, 126, 252)

MIN_EVENTS = 200         # the desk's standing power floor (B-58, B-74)


def _quarter_key(label: str | None) -> tuple:
    """Sortable ('2026Q2' -> (2026, 2)); unlabelled quarters sort first."""
    if not label or "Q" not in label:
        return (0, 0)
    y, q = label.split("Q")
    return (int(y), int(q))


def _filed_date(entry: dict) -> dt.date | None:
    """`filed_on` as a date. '21-JUL-2026 17:03:57' -> 2026-07-21."""
    raw = (entry or {}).get("filed_on")
    if not raw:
        return None
    try:
        return dt.datetime.strptime(raw.split()[0], "%d-%b-%Y").date()
    except Exception:
        return None


def _load_bars(sym: str):
    p = BARS / f"{sym}_1d.json"
    if not p.exists():
        return None, None
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None, None
    rows = [b for b in doc.get("bars", [])
            if b and b.get("close") and b.get("time")]
    if not rows:
        return None, None
    days = np.array([dt.date.fromtimestamp(int(b["time"])).toordinal() for b in rows])
    close = np.array([float(b["close"]) for b in rows])
    return days, close


#: A filing must be met by a bar within this many calendar days to be priceable.
#: Not cosmetic: `searchsorted` on a date BEFORE the first cached bar returns
#: index 0, so a 2021 filing would silently be priced at the 2023 open of the
#: cache window -- a two-year lookahead reported as a valid event. Caught by
#: reading the function rather than by any count looking wrong, which is the
#: argument for bounding a lookup instead of trusting its index.
PRICE_TOL_DAYS = 10


def _bar_at(days, close, on: dt.date):
    """Index of the first bar within PRICE_TOL_DAYS after `on`, and its close.

    Returns (None, None) when the filing falls outside the cached price window in
    EITHER direction -- past the end, or before it begins.
    """
    i = int(np.searchsorted(days, on.toordinal(), side="left"))
    if i >= len(days):
        return None, None
    if days[i] - on.toordinal() > PRICE_TOL_DAYS:
        return None, None
    return i, float(close[i])


def probe(mcap_max: float = MCAP_MAX_CR, verbose: bool = True,
          only: list[str] | None = None) -> dict:
    own_syms = {os.path.basename(f)[:-5] for f in glob.glob(str(OWN / "*.json"))}
    bar_syms = {os.path.basename(f)[:-8] for f in glob.glob(str(BARS / "*_1d.json"))}
    pit_syms = {os.path.basename(f)[:-5]
                for f in glob.glob(str(HERE / "cache" / "pit_quality" / "*.json"))}
    universe = sorted(own_syms & bar_syms & pit_syms)
    if only:
        universe = [s for s in universe if s in {x.upper() for x in only}]

    # Funnel counters. Every leg is counted on the SURVIVORS of the previous one,
    # so the drops are attributable; a leg counted independently tells you its
    # base rate, not its cost.
    n = dict(events=0, dated=0, priced=0, mcap=0, inst=0, promoter=0, growth=0)
    unknown_growth = 0
    mcaps: list[float] = []
    survivors: list[dict] = []
    fwd = {h: 0 for h in HORIZONS}

    for sym in universe:
        try:
            own = json.loads((OWN / f"{sym}.json").read_text(encoding="utf-8"))
        except Exception:
            continue
        quarters = own.get("quarters") or {}
        if len(quarters) < 2:
            continue
        ordered = sorted(quarters.items(), key=lambda kv: _quarter_key(kv[1].get("quarter")))
        days, close = _load_bars(sym)
        if days is None:
            continue
        stmts = pit.cached_statements(sym)

        # Each adjacent pair is one formation event: the change between them,
        # dated at the LATER quarter's filing.
        for (_, prev), (_, cur) in zip(ordered, ordered[1:]):
            n["events"] += 1
            on = _filed_date(cur)
            if on is None:
                continue
            n["dated"] += 1

            i, px = _bar_at(days, close, on)
            if i is None:
                continue
            n["priced"] += 1

            shares = cur.get("shares_total")
            if not shares:
                continue
            mcap_cr = shares * px / CR
            mcaps.append(mcap_cr)
            if mcap_cr >= mcap_max:
                continue
            n["mcap"] += 1

            fii = (cur.get("fii") or 0.0) - (prev.get("fii") or 0.0)
            dii = (cur.get("dii") or 0.0) - (prev.get("dii") or 0.0)
            if (fii + dii) <= INST_MIN:
                continue
            n["inst"] += 1

            prom = (cur.get("promoter") or 0.0) - (prev.get("promoter") or 0.0)
            if prom <= PROMOTER_MIN:
                continue
            n["promoter"] += 1

            q = pit.quality_as_of(stmts, on)
            cagr = q.get("revenue_cagr")
            if cagr is None:
                unknown_growth += 1          # NOT a fail: never evaluated
                continue
            if cagr <= SALES_CAGR_MIN:
                continue
            n["growth"] += 1

            for h in HORIZONS:
                if i + h < len(days):
                    fwd[h] += 1
            survivors.append({"symbol": sym, "on": on.isoformat(),
                              "mcap_cr": round(mcap_cr), "inst": round(fii + dii, 2),
                              "cagr": cagr, "bars_after": int(len(days) - 1 - i)})

    if not verbose:
        return {"funnel": n, "survivors": survivors, "fwd": fwd}

    print()
    print("=== B-73 Phase 0 — CAN the multibagger screen be measured? ===")
    print(f"  universe: {len(universe)} names with ownership + price bars + "
          f"point-in-time revenue")
    print(f"  (ownership {len(own_syms)} · bars {len(bar_syms)} · "
          f"pit_quality {len(pit_syms)})")
    print()
    print("  FUNNEL — each leg counted on the survivors of the one above")
    print(f"  {'leg':<34}{'left':>7}{'dropped':>9}")
    prev_v = None
    for key, label in (("events", "quarter-pairs in the cache"),
                       ("dated", "with a filing date"),
                       ("priced", "with a bar on/after the filing"),
                       ("mcap", f"market cap < {mcap_max:,.0f} Cr"),
                       ("inst", f"(FII+DII) change > {INST_MIN}"),
                       ("promoter", f"promoter change > {PROMOTER_MIN}"),
                       ("growth", f"3y sales CAGR > {SALES_CAGR_MIN}")):
        v = n[key]
        drop = "" if prev_v is None else f"{prev_v - v:>9}"
        print(f"  {label:<34}{v:>7}{drop}")
        prev_v = v
    print(f"  + {unknown_growth} events UNKNOWN on growth (too few published "
          f"years) — not failures, never evaluated")

    if mcaps:
        a = np.array(mcaps)
        print()
        print(f"  MARKET CAP of the cached panel (n={len(a)} priced events): "
              f"median {np.median(a):,.0f} Cr")
        for thr in (5_000, 20_000, 50_000):
            print(f"    < {thr:>6,} Cr: {100 * (a < thr).mean():>5.1f}%")

    print()
    print("  FORWARD COVERAGE of the survivors")
    for h in HORIZONS:
        print(f"    {h:>4} trading days (~{h / 21:.0f} months): "
              f"{fwd[h]:>4} of {n['growth']}")

    print()
    final = n["growth"]
    print(f"  VERDICT: {final} point-in-time events against the desk's floor of "
          f"{MIN_EVENTS}.")
    if final < MIN_EVENTS:
        print("  UNDERPOWERED on the free legs alone, and the three ratio legs")
        print("  (OPM / ROCE / D-E) would only cut further — so the yfinance")
        print("  statement refetch they need is NOT worth paying for yet.")
    else:
        print("  Enough to proceed, BEFORE the three ratio legs are applied;")
        print("  they can only reduce it, so this is an upper bound.")
    if fwd[252] < MIN_EVENTS:
        print(f"  And at 252 days only {fwd[252]} events remain: the MULTIBAGGER")
        print("  horizon is unreachable on this data regardless of the legs.")
    return {"funnel": n, "survivors": survivors, "fwd": fwd}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mcap-max", type=float, default=MCAP_MAX_CR,
                    help="market-cap ceiling in Cr (sensitivity check)")
    ap.add_argument("--symbols", nargs="*", help="restrict to these names")
    args = ap.parse_args()
    probe(args.mcap_max, only=args.symbols)


if __name__ == "__main__":
    main()
