"""event_study_run.py — run the pre-registered policy event study.

    py -X utf8 tools/event_study_run.py --events mpc,budget

Writes output/event_study/<YYYY-MM-DD>_<sets>.json and .md and prints the .md
path. The study is pre-registered on the wiki (Policy-Event-Study-Pre-
Registration); run it on real data only after that page is committed.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

import event_study as es

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> Path:
    ap = argparse.ArgumentParser(description="Policy event study vs NIFTY and sector indices")
    ap.add_argument("--events", default="mpc,budget", help="comma-separated event types")
    ap.add_argument("--file", default=str(ROOT / "data" / "events" / "policy_events.csv"))
    ap.add_argument("--start", default="2010-01-01")
    ap.add_argument("--draws", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=str(ROOT / "output" / "event_study"))
    ap.add_argument("--no-cache", action="store_true", help="re-download prices")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    types = [t.strip() for t in args.events.split(",") if t.strip()]
    events = es.load_events(args.file, types=types, scheduled_only=False)
    if events.empty:
        raise SystemExit(f"no events of type {types} in {args.file}")

    cache_dir = es.DEFAULT_CACHE
    if args.no_cache:
        (cache_dir / f"closes_{args.start}.csv").unlink(missing_ok=True)
    closes, omitted = es.load_closes([es.MARKET] + es.SECTORS, args.start)
    if es.MARKET in omitted:
        raise SystemExit("NIFTY (^NSEI) download failed — no partial run")

    cfg = es.StudyConfig(draws=args.draws, seed=args.seed)
    result = es.run_study(closes, events, cfg, omitted=omitted)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = out / f"{date.today().isoformat()}_{'_'.join(types)}"
    stem.with_suffix(".json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    md = stem.with_suffix(".md")
    md.write_text(es.render_markdown(result), encoding="utf-8")
    print(md)
    return md


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
