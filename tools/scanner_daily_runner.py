"""Daily scanner runner — executed by the Windows Scheduled Task
TradingBramha-DailyScanner. Do not edit the task directly; regenerate via the
Scanner Hub → Daily Scanner Scheduler panel."""
import sys, os, json, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import scanner_templates as sc
from dashboard_app_helpers import cached_fetch_ohlcv_headless  # noqa

SCANNERS = ["52-Week High Leaders", "Stage 2 Uptrend", "Pullback Entry", "Order Block Retest", "RSI 60-40 Setup", "RSI Divergence Bull", "RSI Divergence Bear", "Darvas Box", "Momentum Continuation", "PEAD Drift", "Zero-Debt Quality PEAD", "Base Formation", "VCP Coiling", "Minervini VCP (valchak)", "Near Pivot", "FVG Pullback", "ICT Setup", "Downside Risk", "Mean Reversion (Connors RSI2)", "Support Breakdown", "Bearish Reversal Candle", "Consolidation Breakout (6M\u201310Y)", "High Tight Flag", "Structural Breakout", "Rounding Bottom", "Early Reversal Detector", "Candlestick Patterns", "IPO-Base Breakout", "ATH Breakout (all-time high)", "Falling Wedge", "Harmonic Reversal (XABCD)", "MFI Oversold Recovery", "EMA-50 Coil", "RSI Mid-Band Momentum", "Triple-RS 52W Cross"]
UNIVERSE_MODE = "Screener results (today's pipeline)"

def _fetch(sym, days=300):
    import data_fetcher as df_mod
    return df_mod.fetch_ohlcv(sym, days=days)

def main():
    import bhavcopy_fetcher as bh
    universe = bh.fetch_top_n(300) if "Bhavcopy" in UNIVERSE_MODE else []
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    out = {}
    for name in SCANNERS:
        if name not in sc.SCANNERS:
            continue
        try:
            hits = sc.run_scanner(name, universe, _fetch)
            out[name] = hits
            print(f"{ts}  {name}: {len(hits)} hits")
        except Exception as exc:
            out[name] = []
            print(f"{ts}  {name}: ERROR {exc}")
    dest = os.path.join(os.path.dirname(__file__), "cache", f"scanner_daily_{ts}.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w") as fh:
        json.dump(out, fh, default=str)
    print(f"Saved → {dest}")

if __name__ == "__main__":
    main()
