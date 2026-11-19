#!/usr/bin/env python3
"""capture_ew_fixture.py - save the Nifty 15m bars behind the B-135 regression test.

The test `test_elliott_wave.py::test_nifty_15m_oct_3_to_8_contains_a_down_wxy`
pins the W-X-Y detector to the SweeGlu chart of 2026-10-08 (Nifty 50, 15m,
Oct 3 -> Oct 8). It skips until this file exists:

    tools/cache/fixtures/nifty_15m_2026-10-03_08.json

Run once:   py -3 tools/capture_ew_fixture.py

Yahoo only serves 15-minute bars for roughly the last 60 days, so this has to
be captured before about the first week of December 2026 or the window is gone.
The fixture pins BEHAVIOUR; one hand-picked chart is not evidence of edge.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "cache" / "fixtures" / "nifty_15m_2026-10-03_08.json"


def main() -> int:
    import pandas as pd
    import yfinance as yf
    df = yf.download("^NSEI", start="2026-10-01", end="2026-10-10", interval="15m",
                     progress=False, auto_adjust=False)
    if df is None or df.empty:
        print("Yahoo returned no 15m bars - window may have aged out.", file=sys.stderr)
        return 1
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    ist = df.index.tz_convert("Asia/Kolkata")
    keep = (ist.date >= pd.Timestamp("2026-10-03").date()) & \
           (ist.date <= pd.Timestamp("2026-10-08").date())
    df = df[keep].dropna(subset=["Open", "High", "Low", "Close"])
    bars = [{"time": int(ts.timestamp()), "open": float(r.Open), "high": float(r.High),
             "low": float(r.Low), "close": float(r.Close),
             "volume": float(r.Volume or 0)} for ts, r in df.iterrows()]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"symbol": "^NSEI", "interval": "15m",
                               "window": "2026-10-03..2026-10-08 IST",
                               "source": "yfinance", "bars": bars}), encoding="utf-8")
    print(f"{len(bars)} bars -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
