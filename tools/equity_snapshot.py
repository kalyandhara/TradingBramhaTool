#!/usr/bin/env python3
"""equity_snapshot.py — write today's RECORDED equity row (B-110).

Run after the close by the `equity_snapshot` scheduler job. Same arithmetic as
the reconstruction (`equity_curve.snapshot_row`), dated by the last priced bar,
so a holiday run re-writes the last session instead of inventing one.

  py -3 tools/equity_snapshot.py            # write the row
  py -3 tools/equity_snapshot.py --dry-run  # print it, write nothing
"""
from __future__ import annotations

import argparse
import sys

import equity_curve as ec
import portfolio_db as db
import portfolio_risk as prisk
import screener_pipeline as sp


def _ohlcv(sym: str):
    try:
        return sp.fetch_ohlcv(sym, days=400)
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    capital = float(db.get_setting("total_capital", "0") or 0)
    positions = db.get_all_positions()
    if positions.empty:
        print("no positions — nothing to snapshot")
        return 0

    def _price(sym):
        d = _ohlcv(sym)
        if d is None or d.empty:
            return None
        return float(d["close"].iloc[-1]), float(d["close"].iloc[-2] if len(d) > 1
                                                 else d["close"].iloc[-1])

    open_pos = positions[positions["status"] == "open"]
    risk = prisk.summarise(open_pos, _price, capital) if not open_pos.empty else {}
    # summarise() reports open risk as a % of capital; store the amount. A
    # position with no stop contributes 0 there and is counted in no_stop_count
    # -- unbounded risk is not in this number, as on the Home card.
    open_risk = (risk["open_risk_pct"] * capital / 100.0
                 if risk and capital else None)
    row = ec.snapshot_row(positions, _ohlcv, capital, open_risk=open_risk)
    if row is None:
        print("no priced bar for any position — nothing written", file=sys.stderr)
        return 1
    print(f"{row['date']}: equity {row['equity']:,.2f} (capital {row['capital']:,.0f}, "
          f"realised {row['realised']:,.2f}, unrealised {row['unrealised']:,.2f}, "
          f"{row['n_open']} open, {row['unpriced']} unpriced)")
    if row["unpriced"]:
        print(f"WARNING: {row['unpriced']} open position(s) unpriced — the row is "
              f"stored and drawdown() will skip it", file=sys.stderr)
    if not a.dry_run:
        db.save_equity_snapshot(row)
        print("written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
