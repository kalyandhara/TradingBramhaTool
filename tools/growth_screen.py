#!/usr/bin/env python3
"""growth_screen.py - High-Growth screen on free yfinance data (no screener.in).

Replaces the screener.in-cookie path behind the High-Growth Screener page.

Pipeline
--------
  refresh   one yfinance round trip per symbol via
            `fundamentals_deep.derive_fundamentals` (statements + .info), reduced to
            the screen's fields and written to cache/growth_snapshot.json.
            Fundamentals change quarterly, so a snapshot younger than
            --max-age-days is reused unless --force.
  screen    pure filter over the snapshot - instant, no network. The page's
            sliders call this.

Honest differences from the old screener.in query
-------------------------------------------------
* yfinance usually serves 4 annual columns, so a true 5Y CAGR is often missing.
  Growth uses the 5Y CAGR when it exists, else the 3Y CAGR, and the row says
  which (`growth_basis`). It never invents a 5Y number.
* Each criterion is PASS / FAIL / UNKNOWN (value_screen convention). Missing data
  is UNKNOWN, never a silent fail; `max_unknowns` decides how many are tolerated.
  Banks/NBFCs usually have no OPM/ROCE on Yahoo - they surface as UNKNOWN.
* YoY quarterly profit is matched by date (same quarter a year earlier).

Not backtested - a reading list of growth + quality names, not an edge claim.

CLI
---
    py -3 tools/growth_screen.py --refresh                 # build/refresh snapshot
    py -3 tools/growth_screen.py --refresh --force --universe totalmarket
    py -3 tools/growth_screen.py                           # print hits from snapshot
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
SNAPSHOT = HERE / "cache" / "growth_snapshot.json"
UNIVERSES = {
    "nifty500": HERE / "cache" / "nse_nifty500_constituents.json",
    "totalmarket": HERE / "cache" / "nse_niftytotalmarket_constituents.json",
}
PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"
log = logging.getLogger(__name__)


@dataclass
class Thresholds:
    min_sales_growth: float = 15.0     # % CAGR (5Y if available, else 3Y)
    min_profit_growth: float = 15.0
    min_yoy_qtr_profit: float = 15.0   # latest quarter vs same quarter last year
    min_roe: float = 15.0
    min_roce: float = 15.0
    min_opm: float = 10.0


CRITERIA = (  # (label, row key, threshold attr)
    ("Sales growth", "sales_growth", "min_sales_growth"),
    ("Profit growth", "profit_growth", "min_profit_growth"),
    ("YoY qtr profit", "yoy_qtr_profit", "min_yoy_qtr_profit"),
    ("ROE", "roe", "min_roe"),
    ("ROCE", "roce", "min_roce"),
    ("OPM", "opm", "min_opm"),
)


# ── refresh ──────────────────────────────────────────────────────────────────
def universe(kind: str = "nifty500") -> list[dict]:
    return json.loads(UNIVERSES[kind].read_text(encoding="utf-8"))


def reduce(payload: dict[str, Any], meta: dict | None = None) -> dict[str, Any] | None:
    """derive_fundamentals payload -> one compact snapshot row."""
    if not payload or not payload.get("available"):
        return None
    meta = meta or {}
    q = payload.get("quarters") or []
    yoy = next((r.get("profit_yoy") for r in q if r.get("profit_yoy") is not None), None)
    yoy_period = next((r.get("period") for r in q if r.get("profit_yoy") is not None), None)
    r5, r3 = payload.get("revenue_cagr_5y"), payload.get("revenue_cagr_3y")
    p5, p3 = payload.get("profit_cagr_5y"), payload.get("profit_cagr_3y")
    return {
        "symbol": (payload.get("symbol") or "").replace(".NS", ""),
        "name": payload.get("long_name") or meta.get("name"),
        "industry": meta.get("industry") or payload.get("industry"),
        "price": payload.get("price"),
        "market_cap": payload.get("market_cap"),
        "sales_cagr_5y": r5, "sales_cagr_3y": r3,
        "profit_cagr_5y": p5, "profit_cagr_3y": p3,
        "sales_growth": r5 if r5 is not None else r3,
        "profit_growth": p5 if p5 is not None else p3,
        "growth_basis": "5Y" if (r5 is not None and p5 is not None) else "3Y",
        "yoy_qtr_profit": yoy, "yoy_qtr_period": yoy_period,
        "roe": payload.get("roe"), "roce": payload.get("roce"), "opm": payload.get("opm"),
        "pe": payload.get("pe"),
        "as_of": payload.get("as_of"),
    }


def load_snapshot() -> dict[str, Any] | None:
    try:
        return json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    except Exception:
        return None


def snapshot_age_days(snap: dict | None) -> float | None:
    if not snap or "built_epoch" not in snap:
        return None
    return (time.time() - float(snap["built_epoch"])) / 86400


def refresh(kind: str = "nifty500", *, max_workers: int = 6,
            derive: Callable[[str], dict] | None = None,
            progress_cb: Callable[[int, int, str], None] | None = None) -> dict[str, Any]:
    """Fetch every symbol in the universe and write the snapshot. Returns it."""
    if derive is None:
        import fundamentals_deep as fd
        derive = fd.derive_fundamentals
    uni = universe(kind)
    total = len(uni)

    def _one(m):
        try:
            return reduce(derive(m["symbol"]), m)
        except Exception as exc:        # one bad symbol must not kill the run
            log.warning("derive failed for %s: %s", m.get("symbol"), exc)
            return None

    rows, done = [], 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for m, row in zip(uni, pool.map(_one, uni)):
            done += 1
            if progress_cb:
                try: progress_cb(done, total, m["symbol"])
                except Exception: pass
            if row:
                rows.append(row)
    now = dt.datetime.now()
    snap = {"universe": kind, "built_at": now.isoformat(timespec="minutes"),
            "built_epoch": now.timestamp(), "scanned": total,
            "derived": len(rows), "rows": rows}
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    tmp = SNAPSHOT.with_suffix(".tmp")
    tmp.write_text(json.dumps(snap), encoding="utf-8")
    tmp.replace(SNAPSHOT)                # atomic: the page never reads half a file
    return snap


# ── screen ───────────────────────────────────────────────────────────────────
def evaluate(row: dict, th: Thresholds) -> dict:
    states, fails, unknowns = {}, 0, 0
    for label, key, attr in CRITERIA:
        v, lim = row.get(key), getattr(th, attr)
        if v is None:
            st = UNKNOWN; unknowns += 1
        elif v >= lim:
            st = PASS
        else:
            st = FAIL; fails += 1
        states[label] = st
    return {"states": states, "fails": fails, "unknowns": unknowns,
            "passes": len(CRITERIA) - fails - unknowns}


def screen(rows: list[dict], th: Thresholds | None = None, *,
           max_unknowns: int = 0) -> list[dict]:
    """Rows that FAIL nothing and have at most `max_unknowns` missing fields,
    fastest profit growth first."""
    th = th or Thresholds()
    out = []
    for r in rows:
        ev = evaluate(r, th)
        if ev["fails"] == 0 and ev["unknowns"] <= max_unknowns:
            out.append({**r, **ev})
    out.sort(key=lambda r: (r["unknowns"], -(r.get("profit_growth") or -1e9)))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--force", action="store_true", help="refresh even if snapshot is fresh")
    ap.add_argument("--max-age-days", type=float, default=7.0)
    ap.add_argument("--universe", choices=UNIVERSES, default="nifty500")
    ap.add_argument("--max-unknowns", type=int, default=0)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.WARNING)
    snap = load_snapshot()
    if a.refresh:
        age = snapshot_age_days(snap)
        if (a.force or age is None or age >= a.max_age_days
                or (snap or {}).get("universe") != a.universe):
            print(f"Refreshing {a.universe} from yfinance…", file=sys.stderr)
            snap = refresh(a.universe, progress_cb=lambda d, t, s: (
                print(f"  {d}/{t} {s}", file=sys.stderr) if d % 50 == 0 or d == t else None))
            print(f"snapshot: {snap['derived']}/{snap['scanned']} names -> {SNAPSHOT}")
        else:
            print(f"snapshot is {age:.1f} days old (< {a.max_age_days}); skipped. --force to rebuild")
    if not snap:
        print("No snapshot yet - run with --refresh"); return 1
    hits = screen(snap["rows"], max_unknowns=a.max_unknowns)
    print(f"{len(hits)} hits (snapshot {snap['built_at']}, {snap['universe']})")
    for r in hits[:40]:
        print(f"  {r['symbol']:<12} sales {r['sales_growth']:.1f}% profit {r['profit_growth']:.1f}% "
              f"({r['growth_basis']}) qtr {r['yoy_qtr_profit'] or 0:.0f}% ROE {r['roe'] or 0:.1f} "
              f"ROCE {r['roce'] or 0:.1f} OPM {r['opm'] or 0:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
