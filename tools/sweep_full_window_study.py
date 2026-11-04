"""B-186d — the bullish liquidity sweep card re-measured with full-history detection.

Pre-registered at trading-wiki/wiki/analyses/Sweep-Full-Window-Pre-Registration.md
(commit 48560ea, before this file existed). Deciding panel: nifty500[300:500]
(unseen with a full window). The main panel nifty500[:300] is reported but was
already seen (B-186a S5).

Run:  python -X utf8 tools/sweep_full_window_study.py [--workers 8] [--write-badge]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import sweep_reconcile_study as srs  # noqa: E402
import tour_base_rates as tbr  # noqa: E402

KEY = srs.KEY
FAMILY = 20
ALPHA = 0.05
OUT = HERE / "cache" / "sweep_full_window.json"
RATES = HERE / "cache" / "tour_base_rates.json"


def label(r: dict) -> dict:
    r = dict(r)
    p = r.get("p20")
    r["p20_bonf"] = None if p is None else round(min(1.0, p * FAMILY), 10)
    thirds = r.get("thirds") or [0, 0, 0]
    if r.get("n_symbols", 0) < tbr.MIN_SYMBOLS or r.get("n_events", 0) < tbr.MIN_EVENTS \
            or r.get("mean20") is None:
        r["label"] = "TOO_FEW"
    elif r["p20_bonf"] < ALPHA and r["mean20"] > 0 and sum(t > 0 for t in thirds) >= 2:
        r["label"] = "EDGE"
    elif r["p20_bonf"] < ALPHA and r["mean20"] < 0 and sum(t < 0 for t in thirds) >= 2:
        r["label"] = "INVERTED"
    else:
        r["label"] = "ORDINARY"
    return r


def merge_badge(rates: dict, main: dict, fresh: dict) -> dict:
    out = json.loads(json.dumps(rates))
    out["detectors"][KEY] = {
        **{k: main.get(k) for k in ("n_events", "n_symbols", "mean5", "mean20", "mean60",
                                    "p20", "thirds", "label")},
        "p20_holm": main.get("p20_bonf"),
        "confirm_label": fresh["label"], "confirm_mean20": fresh.get("mean20"),
        "confirm_p20_holm": fresh.get("p20_bonf"),
        # as merge_confirmation: only an EDGE/INVERTED main label can be (un)confirmed
        "confirmed": (fresh["label"] == main["label"]) if main["label"] in ("EDGE", "INVERTED") else None,
        "window": "full history (B-186d)",
    }
    return out


def _worker(args):
    sym, raw = args
    if raw is None:
        return []
    df = srs.clean(raw)
    if len(df) < srs.MIN_BARS:
        return []
    return srs.tour_rows(sym, df, len(df) - srs.EVAL_BARS, srs.FULL_WINDOW)


def run_panel(syms, frames, workers):
    from multiprocessing import Pool
    rows = []
    with Pool(workers) as pool:
        for part in pool.imap_unordered(_worker, [(s, frames.get(s)) for s in syms], chunksize=2):
            rows += part
    x = tbr.aggregate(rows, [KEY])[KEY]
    return label({k: x[k] for k in ("n_events", "n_symbols", "mean5", "mean20", "mean60", "p20", "thirds")})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    ap.add_argument("--write-badge", action="store_true")
    a = ap.parse_args(argv)
    import nse_universe as nu
    allsyms = nu.symbols("nifty500")
    main_syms, fresh_syms = tbr.panel_symbols(allsyms, 0, 300), tbr.panel_symbols(allsyms, 300, 200)
    frames = srs.fetch_frames(main_syms + fresh_syms)
    fresh = run_panel(fresh_syms, frames, a.workers)
    main_ = run_panel(main_syms, frames, a.workers)
    payload = {"asOf": date.today().isoformat(),
               "preregistration": "trading-wiki/wiki/analyses/Sweep-Full-Window-Pre-Registration.md (48560ea)",
               "fresh_panel_deciding": fresh, "main_panel_seen": main_}
    OUT.write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    for name, r in (("fresh (decides)", fresh), ("main (seen)", main_)):
        print(f"{name:16s} {r['label']:9s} n={r['n_events']} syms={r['n_symbols']} "
              f"mean20={r['mean20'] * 100:+.2f}% p={r['p20']:.4g} bonf={r['p20_bonf']:.4g} thirds={r['thirds']}")
    if a.write_badge:
        rates = json.loads(RATES.read_text(encoding="utf-8"))
        tbr.write_atomic(RATES, merge_badge(rates, main_, fresh))
        print("badge written:", RATES)
    return payload


if __name__ == "__main__":
    main()
