#!/usr/bin/env python3
"""
snapshot_refresh.py — headless runner for the report snapshots.

Registered in the Scheduler Hub as "Report Snapshot Refresh" (daily, after the
close). Computes each snapshot in snapshot_registry.SNAPSHOTS and stores it in
trading_bramha.db with its run timestamp; a failing snapshot is logged, stored
as an error row and skipped, never aborting the run.

  py -3 tools/snapshot_refresh.py --all                # every snapshot
  py -3 tools/snapshot_refresh.py sector_index_data finviz
  py -3 tools/snapshot_refresh.py --list               # names + last run
  py -3 tools/snapshot_refresh.py --missing            # only those without a run today
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import snapshot_registry as reg   # noqa: E402
import snapshot_store as store    # noqa: E402


def _missing_today() -> list[str]:
    today = date.today().isoformat()
    out = []
    for spec in reg.ordered():
        m = store.latest_meta(spec.name, ok_only=True)
        if m is None or m.run_date != today:
            out.append(spec.name)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="*", help="snapshot names (default: --all)")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--missing", action="store_true",
                    help="only snapshots without an ok run dated today")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--prune-days", type=int, default=store.RETENTION_DAYS)
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if args.list:
        for spec in reg.ordered():
            m = store.latest_meta(spec.name)
            stamp = f"{m.run_at} [{m.status}]" if m else "never"
            print(f"{spec.name:22} {spec.page:20} {stamp}")
        return 0

    names = args.names
    if args.missing:
        names = _missing_today()
        if not names:
            print("all snapshots already have an ok run today")
            return 0
    elif not names or args.all:
        names = None
    for n in names or []:
        if n not in reg.SNAPSHOTS:
            print(f"unknown snapshot {n!r}; known: {', '.join(reg.SNAPSHOTS)}")
            return 2

    t0 = time.time()
    metas = reg.run_all(names, progress=lambda s: print("…", s, flush=True))
    # A failed attempt on a day that already has a good run is annotated onto
    # that row (status stays ok, `error` is set) so pages keep the good data —
    # but it is still a failed run and the summary must say so.
    failed = [m for m in metas if not m.ok or m.error]
    pruned = store.prune(args.prune_days)
    print(f"done in {time.time() - t0:.0f}s — {len(metas) - len(failed)} ok, "
          f"{len(failed)} failed, {pruned} old rows pruned")
    for m in failed:
        kept = "  (today's earlier good run kept)" if m.ok else ""
        print(f"  FAILED {m.name}: {m.error}{kept}")
    return 1 if failed and len(failed) == len(metas) else 0


if __name__ == "__main__":
    sys.exit(main())
