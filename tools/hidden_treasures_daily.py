#!/usr/bin/env python3
"""
hidden_treasures_daily.py — the Hidden Treasures discovery, run headlessly once a day.

The page only ran on a "Discover" click, and a fresh session opened on an empty
screen even when a run was stored. This job does the same work unattended and
stores it in the `hidden_treasures` table, which the page now loads on open.

Steps, all reusing the page's own code (no second implementation):
  1. smallcap_discovery.backfill — warm ownership_cache. Resumable: only
     quarters not already cached are fetched, so a daily run costs little and
     still picks up new quarterly shareholding filings as they land.
  2. smallcap_discovery.discover — rank with the quality overlay ON and the
     red-flag veto OFF, the page defaults (veto off since B-34r5: flagged names
     are marked, not removed).
  3. portfolio_db.save_hidden_treasures_run — replace-on-rerun per run date,
     plus the run's meta (universe, scanned, cached, veto) so the page can say
     what the stored list covers.

The table keeps ONE run per date: a manual Discover on the page for another
universe replaces that day's scheduled run (the existing replace-on-rerun
rule). The page labels a restored run with its universe for that reason.

Unvalidated — a discovery lens, not an edge (B-34r4). Storing it daily is for
coverage and history, not because the ranking predicts.

CLI:
  py -3 tools/hidden_treasures_daily.py                 # NSE Both, top 100
  py -3 tools/hidden_treasures_daily.py --kind smallcap250 --top 50
  py -3 tools/hidden_treasures_daily.py --no-backfill   # rank the cache as is
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import portfolio_db as db          # noqa: E402
import smallcap_discovery as scd   # noqa: E402

log = logging.getLogger("hidden_treasures_daily")

#: Page defaults: "NSE Both" universe, quality overlay on, veto off. Top 100 is
#: the page slider's maximum, so any "Show top N" view is served from storage.
DEFAULT_KIND = "both"
DEFAULT_TOP = 100


def run(kind: str = DEFAULT_KIND, top: int = DEFAULT_TOP, *, backfill: bool = True,
        run_date: str | None = None) -> dict:
    """Backfill, discover, store. Returns the discover() result plus `saved`."""
    t0 = time.time()
    if backfill:
        n = scd.backfill(kind, progress=True)
        log.info("backfill: %d names checked", n)
    res = scd.discover(kind=kind, limit=top, enrich=True, veto_critical=False)
    run_date = run_date or date.today().isoformat()
    saved = db.save_hidden_treasures_run(res["hits"], universe_kind=kind,
                                         universe_size=res.get("universe", 0),
                                         run_date=run_date)
    db.save_hidden_treasures_meta(run_date, {
        "universe_kind": kind, "universe": res.get("universe", 0),
        "scanned": res.get("scanned", 0), "cached": res.get("cached", 0),
        "veto_active": res.get("veto_active", False),
        "vetoed": res.get("vetoed") or [], "enrich": True,
        "source": "scheduled", "elapsed_s": round(time.time() - t0, 1),
    })
    res["saved"] = saved
    return res


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="Headless Hidden Treasures run")
    ap.add_argument("--kind", default=DEFAULT_KIND,
                    help="universe: both, smallcap250, microcap250, bse, "
                         "bse_smallcap, bse_microcap, all")
    ap.add_argument("--top", type=int, default=DEFAULT_TOP)
    ap.add_argument("--no-backfill", action="store_true",
                    help="skip the ownership_cache warm-up")
    a = ap.parse_args(argv)
    res = run(a.kind, a.top, backfill=not a.no_backfill)
    print(f"Hidden Treasures {date.today().isoformat()} · universe {res['universe']} · "
          f"cached {res['cached']} · scanned {res['scanned']} · saved {res['saved']}")
    return 0 if res["saved"] else 1   # an empty list is a failure the log should flag


if __name__ == "__main__":
    sys.exit(main())
