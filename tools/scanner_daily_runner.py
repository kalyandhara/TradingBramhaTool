#!/usr/bin/env python3
"""
scanner_daily_runner.py — headless nightly run of the Scanner Hub suite.

Executed by the Windows Scheduled Task **TradingBramha-DailyScanner**, whose
`.bat` wrapper the Scanner Hub -> Daily Scanner Scheduler panel writes.

> [!important] This file is CHECKED IN. It is no longer generated.
> Until 2026-08-31 the dashboard wrote this file from an f-string template every
> time the scheduler panel was used, and the template was broken: the `for` body
> was un-indented (`IndentationError: expected an indented block`, so the module
> never parsed), it imported three modules that do not exist in this repo
> (`data_fetcher`, `bhavcopy_fetcher`, `dashboard_app_helpers`), and the
> "Screener results" universe evaluated to `[]` because a headless task has no
> Streamlit session to read results from. Nothing read its output either, and no
> output file was ever produced. Generated Python cannot be imported, compiled,
> linted or tested by anything, which is exactly how it rotted unnoticed; the
> dashboard now writes only the `.bat`, which calls this module with arguments.

What it does
------------
Runs the selected scanners over one universe and writes a JSON snapshot to
``tools/cache/scanner_daily_<ts>.json``. It also publishes each scanner's hits
to the Scanner Hub cache (``scanner_run_cache``, via ``db.save_scanner_run``),
so the Hub opens on last night's results. Until 2026-10-29 only the JSON was
written, nothing read it, and the Hub's cache was weeks old.

Two things it gets right that the old template did not, both reused from
:mod:`opportunity_daily` rather than re-implemented:

* **One download per symbol per run.** ``_FetchRouter`` caches frames across
  scanners; the template refetched every symbol for every scanner, which is slow
  and a good way to be rate-limited.
* **``needs_full_history`` routing.** ATH / IPO-base breakout are *wrong*, not
  merely weaker, on a short window: ``scan_ath_breakout`` needs only 250 bars, so
  on a 400-bar frame it reports a ~1.6-year high as an ALL-TIME high. The router
  sends those two through a full-history fetch.

It also passes a Nifty benchmark, so RS is excess return over the index rather
than an absolute trailing return.

> [!warning] Scores are NOT comparable across scanners.
> ``scanner_templates._finalize_relative_strength`` ranks ``rs_raw`` *within one
> scanner's matched set* ("RS rank is by definition relative to the rest of the
> scan") and folds it in at 25% weight. A name at rs_rank 100 in a 5-hit scanner
> and one in a 400-hit scanner do not mean the same thing. This snapshot is one
> file per scanner-run, not a scored universe, and reading across its sections as
> though the scores were on one scale is a mistake the file format cannot prevent.

Usage
-----
    py -3 tools/scanner_daily_runner.py --universe bhavcopy --top-n 300
    py -3 tools/scanner_daily_runner.py --universe screener
    py -3 tools/scanner_daily_runner.py --scanners "Pullback Entry" "Darvas Box"
"""
from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import portfolio_db as db               # noqa: E402
import screener_pipeline as sp          # noqa: E402
import scanner_templates as sc          # noqa: E402
# The frame cache + needs_full_history router already exist and are already
# exercised by the nightly Opportunity job. Importing them keeps the two nightly
# paths from drifting, which is the failure mode this file is a monument to.
from opportunity_daily import _FetchRouter   # noqa: E402

log = logging.getLogger("scanner_daily")

DEFAULT_DAYS = 400
DEFAULT_TOP_N = 300
CACHE_DIR = HERE / "cache"


def build_universe(mode: str, top_n: int) -> list[str]:
    """Symbols for the run. Raises RuntimeError with a readable reason on empty.

    ``screener`` runs the pipeline itself. The old template read "today's
    pipeline" from Streamlit session state, which a scheduled task does not have
    -- so it silently scanned an empty list and reported success.
    """
    if mode == "bhavcopy":
        syms = sp.fetch_bhavcopy_top_volume(top_n) or []
        if not syms:
            raise RuntimeError(
                "bhavcopy returned no symbols - NSE may not have published "
                "today's file yet, or the network is blocked")
        return list(syms)

    if mode == "screener":
        df = sp.run_pipeline()
        if df is None or df.empty or "Symbol" not in df.columns:
            raise RuntimeError(
                "screener pipeline returned nothing - run it interactively to "
                "see why, or use --universe bhavcopy")
        return sorted(df["Symbol"].dropna().unique().tolist())

    raise ValueError(f"unknown universe mode {mode!r}")


def run(scanners: list[str], universe: list[str], *,
        days: int = DEFAULT_DAYS, failed: set[str] | None = None) -> dict[str, list[dict]]:
    """Run each scanner over `universe`. One broken scanner never kills the run.

    A scanner that raises still gets `[]` in the result (the JSON snapshot keeps
    every section), and its name goes into `failed` so it is not published as
    a real zero-hit run.
    """
    router = _FetchRouter(days=days)
    try:
        bench = sp.fetch_nifty50(days=days)
    except Exception as exc:
        log.warning("benchmark fetch failed (%s) - RS falls back to absolute return", exc)
        bench = None

    out: dict[str, list[dict]] = {}
    for i, name in enumerate(scanners, 1):
        if name not in sc.SCANNERS:
            log.warning("[%d/%d] %s: not a registered scanner, skipped",
                        i, len(scanners), name)
            continue
        try:
            hits = sc.run_scanner(name, universe, router(name), benchmark_df=bench)
            out[name] = hits
            log.info("[%d/%d] %s: %d hits", i, len(scanners), name, len(hits))
        except Exception as exc:
            out[name] = []
            if failed is not None:
                failed.add(name)
            log.error("[%d/%d] %s: ERROR %s", i, len(scanners), name, exc,
                      exc_info=True)
    log.info("Fetched %d distinct symbol-frames for %d scanners "
             "(one download per symbol, not one per scanner)",
             router.misses, len(scanners))
    return out


def save(payload: dict[str, list[dict]], meta: dict, dest: Path | None = None) -> Path:
    """Write the snapshot. `meta` records what produced it, so a stale file can
    be told from a fresh one without guessing from the filename."""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    dest = dest or (CACHE_DIR / f"scanner_daily_{ts}.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    body = {"meta": {**meta, "generated_at": datetime.datetime.now().isoformat(timespec="seconds")},
            "scanners": payload}
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(body, fh, default=str, indent=1)
    return dest


def publish_to_hub(payload: dict[str, list[dict]], *, failed: set[str],
                   run_date: str | None = None) -> int:
    """Save each scanner that ran into the Scanner Hub cache. Returns the count.

    Errored scanners are skipped: save_scanner_run REPLACES the (scanner, date)
    entry, so publishing an error's empty list would wipe a manual run saved
    earlier that day. A real zero-hit run is published, so the Hub can tell
    "ran, found nothing" from "never ran". One save failing skips that scanner.
    """
    n = 0
    for name, hits in payload.items():
        if name in failed:
            continue
        try:
            # The same json round-trip the snapshot uses: cards carry Timestamps
            # and numpy scalars, and save_scanner_run json.dumps without default.
            cards = json.loads(json.dumps(hits, default=str))
            db.save_scanner_run(name, cards, run_date=run_date)
            n += 1
        except Exception as exc:
            log.error("publish %s to Hub cache failed: %s", name, exc)
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Headless nightly Scanner Hub run")
    ap.add_argument("--universe", default="bhavcopy", choices=["bhavcopy", "screener"])
    ap.add_argument("--top-n", type=int, default=DEFAULT_TOP_N,
                    help=f"bhavcopy universe size (default {DEFAULT_TOP_N})")
    ap.add_argument("--scanners", nargs="*", default=None,
                    help="scanner names; default = every registered scanner")
    ap.add_argument("--days", type=int, default=DEFAULT_DAYS)
    ap.add_argument("--out", default=None, help="explicit output path")
    ap.add_argument("--no-hub", action="store_true",
                    help="write the JSON snapshot only; leave the Scanner Hub cache alone")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO, stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    names = args.scanners if args.scanners else list(sc.SCANNERS.keys())
    try:
        universe = build_universe(args.universe, args.top_n)
    except Exception as exc:
        # A scheduled task that "succeeds" on an empty universe is worse than one
        # that fails, so this exits non-zero and the .bat logs ***** FAILED *****.
        log.error("Universe build failed: %s", exc)
        return 1

    log.info("Universe: %d symbols (%s) | scanners: %d",
             len(universe), args.universe, len(names))
    failed: set[str] = set()
    payload = run(names, universe, days=args.days, failed=failed)
    dest = save(payload, {"universe_mode": args.universe,
                          "universe_size": len(universe),
                          "days": args.days,
                          "scanners_requested": len(names)},
                Path(args.out) if args.out else None)
    total = sum(len(v) for v in payload.values())
    log.info("Saved -> %s (%d scanners, %d hits total)", dest, len(payload), total)
    if not args.no_hub:
        n = publish_to_hub(payload, failed=failed)
        log.info("Published %d/%d scanners to the Scanner Hub cache%s", n, len(payload),
                 f" ({len(failed)} errored, not published)" if failed else "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
