#!/usr/bin/env python3
"""
swing_screener.py
1-5 day swing-trade screener for NSE, built on the 7-point checklist:
  liquidity, volatility, trend alignment, setup trigger, relative strength,
  catalyst proxy (volume shock), and risk:reward.

Reuses data sources already wired up in screener_pipeline.py:
  - NSE Bhavcopy top-volume symbols
  - Chartink volume-shock screeners
  - yfinance OHLCV + Nifty50 reference

Also writes a companion Chartink scan clause (chartink_swing_scan.txt) you
can paste into chartink.com/screener/new for a free, no-code daily check
that approximates the same liquidity+trend+breakout filter.

Run manually:  py -3 tools/swing_screener.py
"""

import sys
import time
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from screener_pipeline import (
    BASE_DIR, BHAV_TOP_N, SCREENER_SLUGS,
    fetch_bhavcopy_top_volume, fetch_screener_stocks,
    fetch_ohlcv, fetch_nifty50,
)

try:
    from ta.momentum import RSIIndicator
    from ta.trend import ADXIndicator
    from ta.volatility import AverageTrueRange
except ImportError:
    sys.exit("Run:  py -3 -m pip install ta")

try:
    from openpyxl.styles import PatternFill, Font
    from openpyxl.utils import get_column_letter
except ImportError:
    sys.exit("Run:  py -3 -m pip install openpyxl")

LOG_FILE = BASE_DIR / "tools" / "swing_pipeline.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ── Thresholds (tune here) ──────────────────────────────────────────────────
MIN_AVG_VOLUME    = 500_000   # 20d avg volume (liquidity floor)
MIN_ATR_PCT       = 1.5       # ATR(14)/close as %, minimum daily range to bother trading
MIN_RR            = 2.0       # reward:risk required to flag a setup as actionable


# ──────────────────────────────────────────────────────────────────────────────
# Scoring: the 7-point swing checklist
# ──────────────────────────────────────────────────────────────────────────────

def score_swing(df: pd.DataFrame, nifty_df: pd.DataFrame | None = None) -> tuple[int, dict, dict]:
    """
    Returns (score 0-7, condition_dict, levels_dict).
    levels_dict carries stop/target/RR/ATR% for the ranked output, independent
    of pass/fail scoring, so you can see *why* something scored low.
    """
    close = df["close"]
    high  = df["high"]
    low   = df["low"]
    vol   = df["volume"]

    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    c   = float(close.iloc[-1])
    e20 = float(ema20.iloc[-1])
    e50 = float(ema50.iloc[-1])

    avg_vol20 = float(vol.tail(20).mean())

    atr_series = AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()
    atr_val    = float(atr_series.iloc[-1]) if not pd.isna(atr_series.iloc[-1]) else 0.0
    atr_pct    = (atr_val / c * 100) if c else 0.0

    rsi_val = float(RSIIndicator(close=close, window=14).rsi().iloc[-1])
    adx_val = float(ADXIndicator(high=high, low=low, close=close, window=14).adx().iloc[-1])

    # ── S1 Liquidity ──
    s1_liquidity = avg_vol20 >= MIN_AVG_VOLUME

    # ── S2 Volatility floor ──
    s2_volatility = atr_pct >= MIN_ATR_PCT

    # ── S3 Trend alignment: price above both EMAs, EMA20 above EMA50 ──
    s3_trend = c > e20 > e50

    # ── S4 Setup trigger: pullback to EMA20 (within 1.5% either side) OR
    #     breakout above prior 10-day high with volume >= 1.5x 20d avg ──
    near_ema20 = abs(c - e20) / c <= 0.015 if c else False
    prior10_high = float(high.iloc[-11:-1].max()) if len(high) > 11 else float("inf")
    vol_today    = float(vol.iloc[-1])
    breakout     = c > prior10_high and vol_today >= 1.5 * avg_vol20
    s4_setup = bool(near_ema20 or breakout)

    # ── S5 Relative strength vs Nifty over 10 trading days ──
    s5_rs = False
    if nifty_df is not None and len(nifty_df) >= 11 and len(close) >= 11:
        try:
            stock_aligned = close.copy()
            stock_aligned.index = pd.to_datetime(stock_aligned.index)
            nifty_close = nifty_df["close"].copy()
            nifty_close.index = pd.to_datetime(nifty_close.index)
            merged = pd.concat([stock_aligned, nifty_close], axis=1, join="inner").dropna()
            merged.columns = ["stock", "nifty"]
            if len(merged) >= 11:
                stock_10d = merged["stock"].iloc[-1] / merged["stock"].iloc[-11] - 1
                nifty_10d = merged["nifty"].iloc[-1] / merged["nifty"].iloc[-11] - 1
                s5_rs = bool(stock_10d > nifty_10d)
        except Exception:
            s5_rs = False

    # ── S6 Momentum/catalyst proxy: RSI 45-70 (room to run, not overbought)
    #     AND ADX > 20 (trend has conviction, not chop) ──
    s6_momentum = bool(45 <= rsi_val <= 70 and adx_val > 20)

    # ── S7 Risk:Reward — stop below recent swing low (5d), target at
    #     20-day high (long bias only) ──
    swing_low_5d = float(low.tail(5).min())
    high_20d     = float(high.tail(20).max())
    risk   = c - swing_low_5d
    reward = high_20d - c
    rr     = (reward / risk) if risk > 0 else 0.0
    s7_rr  = bool(rr >= MIN_RR)

    conds = {
        "S1 Liquidity":      s1_liquidity,
        "S2 Volatility":     s2_volatility,
        "S3 TrendAlign":     s3_trend,
        "S4 SetupTrigger":   s4_setup,
        "S5 RS>Nifty10d":    s5_rs,
        "S6 Momentum":       s6_momentum,
        "S7 RiskReward>=2":  s7_rr,
    }
    levels = {
        "ATR%":     round(atr_pct, 2),
        "RSI14":    round(rsi_val, 1),
        "ADX14":    round(adx_val, 1),
        "Stop":     round(swing_low_5d, 2),
        "Target":   round(high_20d, 2),
        "RR":       round(rr, 2),
        "SetupType": "Breakout" if breakout else ("Pullback" if near_ema20 else "-"),
    }
    return sum(conds.values()), conds, levels


# ──────────────────────────────────────────────────────────────────────────────
# Chartink companion scan (free, no-code, paste into chartink.com/screener/new)
# ──────────────────────────────────────────────────────────────────────────────

def write_chartink_companion() -> None:
    path = BASE_DIR / "tools" / "chartink_swing_scan.txt"
    notes = (
        "Chartink companion scan for the 1-5 day swing screener.\n"
        "This mirrors S1 (liquidity), S3 (trend), S5/S6 (momentum) and a rough\n"
        "version of S4 (pullback-to-EMA20 OR volume breakout). Chartink cannot\n"
        "compute the Nifty-relative-strength (S5) or stop/target/R:R (S7) parts\n"
        "the Python script does -- use this for a fast free daily shortlist,\n"
        "then run swing_screener.py on the results for full scoring.\n\n"
        "How to use:\n"
        "  1. Go to chartink.com/screener/new\n"
        "  2. Paste the clause below into the scan box (remove the outer\n"
        "     Python-format braces, Chartink's editor adds its own structure --\n"
        "     easiest is to build it visually using the conditions below)\n"
        "  3. Save as a scan, run each morning before market open\n\n"
        "Conditions to set (visual builder, one per line, all AND):\n"
        "  - Daily volume > 500000\n"
        "  - Close > EMA(close, 20)\n"
        "  - EMA(close, 20) > EMA(close, 50)\n"
        "  - RSI(14) > 45 and RSI(14) < 70\n"
        "  - ADX(14) > 20\n"
        "  - ( Close > 1.5 * SMA(volume, 20) 1 day ago )  [volume breakout variant]\n"
        "    OR\n"
        "  - ( abs(Close - EMA(close,20)) / Close < 0.015 )  [pullback variant]\n"
        "    (Chartink doesn't support OR across saved scans cleanly -- easiest\n"
        "     is to save TWO scans: 'Swing Breakout' and 'Swing Pullback', and\n"
        "     review both lists together each morning.)\n"
    )
    path.write_text(notes, encoding="utf-8")
    log.info("Chartink companion notes written -> %s", path)


# ──────────────────────────────────────────────────────────────────────────────
# Excel export
# ──────────────────────────────────────────────────────────────────────────────

_GREEN = PatternFill("solid", fgColor="C6EFCE")
_RED   = PatternFill("solid", fgColor="FFC7CE")
_AMBER = PatternFill("solid", fgColor="FFEB9C")


def _style_sheet(ws, df: pd.DataFrame) -> None:
    ws.freeze_panes = "A2"
    col_map = {name: idx + 1 for idx, name in enumerate(df.columns)}
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for row_idx in range(2, len(df) + 2):
        for col_name, col_idx in col_map.items():
            cell = ws.cell(row=row_idx, column=col_idx)
            val = cell.value
            if col_name == "Score /7":
                cell.fill = _GREEN if (val or 0) >= 6 else (_AMBER if (val or 0) >= 4 else _RED)
            elif col_name == "RR":
                cell.fill = _GREEN if (val or 0) >= MIN_RR else _RED
            elif col_name.startswith("S"):
                cell.fill = _GREEN if val else _RED

    for col_name, col_idx in col_map.items():
        col_letter = get_column_letter(col_idx)
        max_len = max(len(str(ws.cell(r, col_idx).value or "")) for r in range(1, len(df) + 2))
        ws.column_dimensions[col_letter].width = min(max_len + 2, 30)


def _export_excel(df: pd.DataFrame, path: Path) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="SwingShortlist")
        _style_sheet(writer.sheets["SwingShortlist"], df)
    log.info("Saved -> %s", path)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def run_swing_screener() -> pd.DataFrame | None:
    log.info("=" * 60)
    log.info("Swing Screener (1-5 day) — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    log.info("=" * 60)

    write_chartink_companion()

    symbol_sources: dict[str, list[str]] = {}

    bhav_syms = fetch_bhavcopy_top_volume(BHAV_TOP_N)
    for s in bhav_syms:
        symbol_sources.setdefault(s, []).append("Bhav")
    time.sleep(1)

    for slug in SCREENER_SLUGS:
        label = "Darvas" if "darvas" in slug else "Nimblr"
        syms = fetch_screener_stocks(slug)
        for s in syms:
            symbol_sources.setdefault(s, []).append(label)
        time.sleep(2)

    all_symbols = sorted(symbol_sources)
    log.info("Unique stocks to score: %d", len(all_symbols))
    if not all_symbols:
        log.warning("No stocks fetched — check network or data sources.")
        return None

    log.info("Downloading Nifty50 reference data...")
    nifty_df = fetch_nifty50(days=60)

    rows: list[dict] = []
    for i, sym in enumerate(all_symbols, 1):
        log.info("[%d/%d] %s", i, len(all_symbols), sym)
        df = fetch_ohlcv(sym, days=120)
        if df is None:
            continue
        try:
            score, conds, levels = score_swing(df, nifty_df=nifty_df)
        except Exception as exc:
            log.warning("  [skip] scoring error: %s", exc)
            continue

        row = {
            "Symbol":   sym,
            "Close":    round(float(df["close"].iloc[-1]), 2),
            "Sources":  "+".join(symbol_sources.get(sym, [])),
            "Score /7": score,
        }
        row.update(levels)
        row.update(conds)
        rows.append(row)
        time.sleep(0.4)

    if not rows:
        log.warning("Nothing scored — no output file written.")
        return None

    results = (
        pd.DataFrame(rows)
        .sort_values(["Score /7", "RR"], ascending=[False, False])
        .reset_index(drop=True)
    )

    out_path = BASE_DIR / f"swing_screener_{datetime.today().strftime('%Y%m%d')}.xlsx"
    _export_excel(results, out_path)

    actionable = results[(results["Score /7"] >= 5) & (results["RR"] >= MIN_RR)]
    log.info(
        "\nActionable (Score>=5 AND RR>=%.1f): %d of %d\n%s",
        MIN_RR, len(actionable), len(results),
        actionable[["Symbol", "Close", "SetupType", "Stop", "Target", "RR", "Score /7"]].head(15).to_string(index=False),
    )
    log.info("Pipeline complete. %d stocks scored.", len(results))
    return results


if __name__ == "__main__":
    run_swing_screener()
