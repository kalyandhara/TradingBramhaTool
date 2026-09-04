"""renko_backtest.py — does a Renko brick flip beat the every-bar baseline?

The measurable claim behind B-43. Scored through the SAME harness as the EVWMA/VWAP MACD
cross (`evwma_vwap_macd_backtest.event_edge` / `.strategy_equity`, with this module's
signal source injected), so the two findings are directly comparable instead of being two
differently-built numbers that happen to share a repo.

── The trap, and how it is closed ────────────────────────────────────────────
Renko bricks are NOT fillable bars: they carry no usable timestamp of their own, several
can print from a single bar, and the newest one is provisional. Backtesting on the brick
series is the classic way this chart type manufactures a fake equity curve — a flat
"chart" of clean alternating runs looks like a trend system that never whipsaws, because
the whipsaws were compressed out of the x-axis.

So the flips emitted by `renko_backtest.js` carry the **underlying bar index that
completed the flip**, and the scorer fills at that bar's NEXT open. Identical treatment to
every other signal here.

The brick size is also causal: `renko.js` re-derives it from ATR only at epoch boundaries,
using bars strictly before that point (see its header). A brick sized from the latest ATR
and applied backwards would repaint all of history — fine for looking at, fatal here.

── Prior (recorded before running, per B-43) ─────────────────────────────────
Neutral-to-skeptical. Renko is a *rendering* choice; a rendering choice that also removed
noise from the signal would be a free lunch. Expect it to land where the DI cross and the
EVWMA/VWAP MACD cross landed: useful context, no standalone edge.

CLI:
  py -3 tools/renko_backtest.py                  # score whatever bars are cached
  py -3 tools/renko_backtest.py --cost-bps 20
  py -3 tools/renko_backtest.py --export         # fetch the basket first
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

import evwma_vwap_macd_backtest as base

HERE = Path(__file__).resolve().parent
CACHE = base.CACHE

#: Same basket as the EVWMA study, so "Renko flip vs EVWMA cross" is a like-for-like
#: comparison on identical names and identical history.
DEFAULT_BASKET = base.DEFAULT_BASKET

#: renko.js needs warmup + atrPeriod + 5 bars before its first brick; 60 is a safe floor
#: and matches the EVWMA harness so the baselines are drawn from the same bars.
WARMUP = 60


def signals_for(bars_path: Path) -> list[dict]:
    """Run the shipped JS Renko engine over `bars_path` and return its flip rows."""
    out_csv = bars_path.with_name(bars_path.stem + "_renko.csv")
    proc = subprocess.run(
        ["node", str(HERE / "renko_backtest.js"), str(bars_path), str(out_csv)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"node runner failed on {bars_path.name}: {proc.stderr.strip()}")
    with out_csv.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return [{"time": int(r["time"]), "index": int(r["index"]), "dir": int(r["dir"]),
             "close": float(r["close"]), "brick": float(r["brick"]),
             "bricks_in_prior": int(r["bricks_in_prior"])} for r in rows]


def format_report(ev: dict, eq: dict | None) -> str:
    txt = base.format_report(ev, eq)
    return txt.replace("EVWMA/VWAP MACD crossover", "Renko brick FLIP (ATR-derived brick)") \
              .replace("cross_up (BUY)", "flip_up (LONG) ") \
              .replace("cross_dn (SELL)", "flip_dn (SHORT)") \
              .replace("cross_dn is scored as a LONG", "flip_dn is scored as a LONG") \
              .replace("the SELL flag had teeth", "the down-flip had teeth")


def main() -> None:
    ap = argparse.ArgumentParser(description="Backtest the Renko brick flip (B-43)")
    ap.add_argument("--export", action="store_true", help="fetch DEFAULT_BASKET first")
    ap.add_argument("--tf", default="1d")
    ap.add_argument("--start", default="2007-09-17")
    ap.add_argument("--cost-bps", type=float, default=0.0)
    ap.add_argument("--symbols", nargs="*")
    args = ap.parse_args()

    if args.export:
        base.export_basket(args.symbols or DEFAULT_BASKET, args.tf, args.start)

    wanted = args.symbols or DEFAULT_BASKET
    paths = [CACHE / f"{base._safe(s)}_{args.tf}.json" for s in wanted]
    paths = [p for p in paths if p.exists()]
    if not paths:
        sys.exit(f"no cached bars in {CACHE} - run with --export first")

    ev = base.event_edge(paths, warmup=WARMUP, signals_fn=signals_for)
    eq = base.strategy_equity(paths, cost_bps=args.cost_bps, warmup=WARMUP,
                              signals_fn=signals_for)
    print(format_report(ev, eq))


if __name__ == "__main__":
    main()
