#!/usr/bin/env python3
"""
screener_pipeline.py
Daily pipeline: NSE Bhavcopy + Chartink screeners -> strategy scoring -> Excel shortlist.

Steps:
  1. Fetch stock lists from:
       a) NSE Bhavcopy top-volume (top 200 by traded value)
       b) Two Chartink volume screeners (Darvas + Nimblr)
  2. Deduplicate, download 300d OHLCV from yfinance (.NS) + Nifty50 reference
  3. Score each stock against:
       - Minervini Trend Template (8 conditions, corrected from prior 7)
       - TechnoFunda-Swing (6 quantifiable conditions)
       - Elliott Wave analysis (wave position + probabilistic W3/W5 targets)
  4. Export colour-coded Excel: "Shortlist" summary + "EW Detail" sheet

Run manually:  py -3 tools/screener_pipeline.py
Schedule:      run tools/install_task.ps1 once as Administrator
"""

import sys
import re
import html
import time
import logging
import zipfile
import io
from datetime import datetime, timedelta
from pathlib import Path

import requests
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ew_module import analyze_ew, ew_summary_row

try:
    import yfinance as yf
except ImportError:
    sys.exit("Run:  py -3 -m pip install yfinance")

try:
    import ta
    from ta.momentum   import RSIIndicator
    from ta.trend      import ADXIndicator, EMAIndicator, SMAIndicator
    from ta.volatility import AverageTrueRange
except ImportError:
    sys.exit("Run:  py -3 -m pip install ta")

try:
    from openpyxl.styles import PatternFill, Font
    from openpyxl.utils import get_column_letter
except ImportError:
    sys.exit("Run:  py -3 -m pip install openpyxl")

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

BASE_DIR  = Path(__file__).resolve().parent.parent
TOOLS_DIR = BASE_DIR / "tools"
LOG_FILE  = TOOLS_DIR / "pipeline.log"

SCREENER_SLUGS = [
    "copy-amitabh-jha3-volume-shockers-stocks-with-rising-volumes-darvas-100",
    "nimblr-s-volume-shocker",
]

CHARTINK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept":     "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept":     "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer":    "https://www.nseindia.com/",
    "Connection": "keep-alive",
}

# Bhavcopy: top N stocks by traded value to include as candidates
BHAV_TOP_N = 5000

# Minimum data requirements
MIN_BARS   = 60
MIN_VOLUME = 100_000

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Step 1a — NSE Bhavcopy top volume
# ──────────────────────────────────────────────────────────────────────────────

def _bhav_url(date: datetime) -> tuple[str, str]:
    """Return (url, format) for a given date. Tries new NSE zip format first."""
    ymd = date.strftime("%Y%m%d")
    dmy_old = date.strftime("%d%b%Y").upper()

    new_url = (
        f"https://nsearchives.nseindia.com/content/cm/"
        f"BhavCopy_NSE_CM_0_0_0_{ymd}_F_0000.csv.zip"
    )
    old_url = (
        f"https://archives.nseindia.com/products/content/"
        f"sec_bhavdata_full_{dmy_old}.csv"
    )
    return new_url, old_url


def _fetch_bhav_df(session: requests.Session, date: datetime) -> pd.DataFrame | None:
    new_url, old_url = _bhav_url(date)

    # Try new zip format
    try:
        r = session.get(new_url, headers=NSE_HEADERS, timeout=30)
        if r.status_code == 200 and r.content[:2] == b"PK":
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                csv_name = [n for n in z.namelist() if n.endswith(".csv")][0]
                with z.open(csv_name) as f:
                    df = pd.read_csv(f, low_memory=False)
            log.info("Bhavcopy (new zip): %s  rows=%d  cols=%s",
             date.strftime("%Y-%m-%d"), len(df), list(df.columns)[:15])
            return df
    except Exception as e:
        log.debug("New bhav url failed (%s): %s", date.strftime("%Y-%m-%d"), e)

    # Fallback: old full bhavcopy CSV
    try:
        r = session.get(old_url, headers=NSE_HEADERS, timeout=30)
        if r.status_code == 200 and len(r.content) > 1000:
            df = pd.read_csv(io.StringIO(r.text), low_memory=False)
            log.info("Bhavcopy (old csv): %s  rows=%d  cols=%s",
                     date.strftime("%Y-%m-%d"), len(df), list(df.columns)[:15])
            return df
    except Exception as e:
        log.debug("Old bhav url failed (%s): %s", date.strftime("%Y-%m-%d"), e)

    return None


def fetch_bhavcopy_frame(date=None) -> "pd.DataFrame | None":
    """The most recent EQ bhavcopy as a NORMALISED frame, or None.

    Columns: ``symbol, volume, turnover, close, prev_close, trade_date``.

    NSE has published this file under several layouts, so the column names are
    sniffed rather than assumed. `turnover` is the traded VALUE in rupees where
    the file carries one; when only a quantity column exists it is a stand-in and
    ``turnover_is_qty`` is set on the frame's ``attrs`` so a caller can say so
    rather than silently reporting shares as rupees.

    This is the authoritative same-day source for the whole market (~2,600 EQ
    rows in one free file). It exists because **yfinance is not reliable for the
    latest session on smaller NSE names** — on 2026-08-28 it had no bar at all for
    MASTEK or OAL and silently served the previous day, which turned a 43.9x
    volume day into 0.9x. A daily volume scanner cannot be built on that.
    """
    session = requests.Session()
    try:
        session.get("https://www.nseindia.com/", headers=NSE_HEADERS, timeout=15)
    except Exception:
        pass

    df = None
    if date is not None:
        df = _fetch_bhav_df(session, date)
    else:
        for days_back in range(1, 6):
            candidate = datetime.today() - timedelta(days=days_back)
            if candidate.weekday() >= 5:
                continue
            df = _fetch_bhav_df(session, candidate)
            if df is not None:
                break
    if df is None:
        log.warning("Bhavcopy: could not download any recent file.")
        return None

    df.columns = [c.strip().upper() for c in df.columns]

    def _pick(*exact, contains=()):
        for c in df.columns:
            if c in exact:
                return c
        for c in df.columns:
            if any(t in c for t in contains):
                return c
        return None

    sym_col = _pick("SYMBOL", "TCKRSYMB", contains=("SYMBOL", "SYMB"))
    ser_col = _pick("SERIES", "SCTYSRS", contains=("SERIES", "SCTYSRS"))
    val_col = _pick("TTLTRFVAL", "TOTTRDBVAL", "TOTTRDVAL", "TOTALTRADEDVALUE",
                    "TRADED_VALUE", contains=("TRFVAL", "TRDBVAL", "TRDVAL"))
    qty_col = _pick("TTLTRADGVOL", "TOTTRDQTY", "TTLTRDQTY",
                    contains=("TRADGVOL", "TRDQTY"))
    close_col = _pick("CLSPRIC", "CLOSE", contains=("CLSPRIC",))
    prev_col = _pick("PRVSCLSGPRIC", "PREVCLOSE", contains=("PRVSCLSG",))
    date_col = _pick("TRADDT", "BIZDT", contains=("TRADDT",))

    if sym_col is None or (val_col is None and qty_col is None):
        log.warning("Bhavcopy: could not identify required columns: %s",
                    list(df.columns))
        return None

    if ser_col:
        df = df[df[ser_col].astype(str).str.strip() == "EQ"]
    elif "FININSTRMTP" in df.columns:
        df = df[df["FININSTRMTP"].astype(str).str.strip().isin(["EQ", "ES"])]

    turnover_is_qty = val_col is None
    if turnover_is_qty:
        val_col = qty_col
        log.info("Bhavcopy: no traded-value column; using qty '%s' as a stand-in",
                 qty_col)

    out = pd.DataFrame({
        "symbol":   df[sym_col].astype(str).str.strip(),
        "turnover": pd.to_numeric(df[val_col], errors="coerce"),
        "volume":   (pd.to_numeric(df[qty_col], errors="coerce")
                     if qty_col else pd.NA),
        "close":    (pd.to_numeric(df[close_col], errors="coerce")
                     if close_col else pd.NA),
        "prev_close": (pd.to_numeric(df[prev_col], errors="coerce")
                       if prev_col else pd.NA),
        "trade_date": (df[date_col].astype(str) if date_col else None),
    }).dropna(subset=["turnover"])
    out.attrs["turnover_is_qty"] = turnover_is_qty
    return out.reset_index(drop=True)


def fetch_bhavcopy_top_volume(top_n: int = BHAV_TOP_N) -> list[str]:
    """Top `top_n` EQ symbols by traded value for the most recent session.

    Thin wrapper over :func:`fetch_bhavcopy_frame` — the column sniffing and the
    EQ filter live there so the two cannot drift apart.
    """
    frame = fetch_bhavcopy_frame()
    if frame is None or frame.empty:
        return []
    top = frame.nlargest(top_n, "turnover")["symbol"].tolist()
    log.info("Bhavcopy top-%d by traded value: %d symbols", top_n, len(top))
    return top


# ──────────────────────────────────────────────────────────────────────────────
# Step 1b — Chartink screener results
# ──────────────────────────────────────────────────────────────────────────────

def _get_csrf_and_clause(session: requests.Session, slug: str) -> tuple[str, str]:
    resp = session.get(
        f"https://chartink.com/screener/{slug}",
        headers={"User-Agent": CHARTINK_HEADERS["User-Agent"]},
        timeout=25,
    )
    resp.raise_for_status()

    page = html.unescape(resp.text)

    csrf_m = re.search(r'meta name="csrf-token" content="([^"]+)"', page)
    if not csrf_m:
        raise ValueError(f"No CSRF token on screener/{slug}")

    atlas_m = re.search(r'"atlas_query"\s*:\s*"([^"]+)"', page)
    if atlas_m:
        clause = atlas_m.group(1)
    else:
        old_m = re.search(r'"scan_clause"\s*:\s*"([^"]+)"', page)
        if not old_m:
            raise ValueError(f"No scan clause found on screener/{slug}")
        clause = old_m.group(1)

    return csrf_m.group(1), clause


def fetch_screener_stocks(slug: str) -> list[str]:
    session = requests.Session()
    try:
        csrf, clause = _get_csrf_and_clause(session, slug)
    except Exception as exc:
        log.error(f"[{slug}] Could not read screener page: {exc}")
        return []

    try:
        resp = session.post(
            "https://chartink.com/screener/process",
            data={"_token": csrf, "scan_clause": clause},
            headers={**CHARTINK_HEADERS,
                     "Referer": f"https://chartink.com/screener/{slug}"},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        log.error(f"[{slug}] API call failed: {exc}")
        return []

    stocks  = payload.get("data", [])
    symbols = [s["nsecode"].strip() for s in stocks if s.get("nsecode", "").strip()]
    log.info(f"[{slug[:40]}]  ->  {len(symbols)} stocks")
    return symbols


# ──────────────────────────────────────────────────────────────────────────────
# Step 2 — Download OHLCV from yfinance
# ──────────────────────────────────────────────────────────────────────────────

def fetch_ohlcv(symbol: str, days: int = 300) -> pd.DataFrame | None:
    ticker = f"{symbol}.NS"
    period = "max" if not days or days <= 0 else f"{days}d"
    try:
        df = yf.download(ticker, period=period, interval="1d",
                         progress=False, auto_adjust=True)
    except Exception as e:
        log.warning("  [skip] yfinance error for %s: %s", ticker, e)
        return None

    if df is None or df.empty:
        log.warning("  [skip] %s — empty download (symbol may not exist on yfinance)", ticker)
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0].lower() for c in df.columns]
    else:
        df.columns = [c.lower() for c in df.columns]

    if len(df) < MIN_BARS:
        log.warning("  [skip] %s — only %d bars (need %d)", ticker, len(df), MIN_BARS)
        return None

    avg_vol = df["volume"].tail(10).mean()
    if avg_vol < MIN_VOLUME:
        log.warning("  [skip] %s — 10d avg volume %.0f < %d (too illiquid)",
                    ticker, avg_vol, MIN_VOLUME)
        return None

    return df


def fetch_nifty50(days: int = 300) -> pd.DataFrame | None:
    """Download Nifty 50 index data for RS computation."""
    period = "max" if not days or days <= 0 else f"{days}d"
    try:
        df = yf.download("^NSEI", period=period, interval="1d",
                         progress=False, auto_adjust=True)
    except Exception:
        return None

    if df is None or df.empty:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0].lower() for c in df.columns]
    else:
        df.columns = [c.lower() for c in df.columns]

    return df


# ──────────────────────────────────────────────────────────────────────────────
# Step 3a — Minervini Trend Template (8 conditions)
# Source: wiki/strategies/VCPBot-Trend-Template.md (corrected 7→8 on 2026-06-15)
#
# C1  Close > SMA150 AND Close > SMA200
# C2  SMA150 > SMA200
# C3  SMA200 trending up (today > 30 bars ago)
# C4  SMA50 > SMA150 AND SMA50 > SMA200
# C5  Close ≥ 52-week low × 1.30  (30%+ above 52w low)
# C6  Close ≥ 52-week high × 0.75  (within 25% of 52w high)
# C7  RS vs Nifty50 outperforming over 26 weeks AND RS line in uptrend 6 weeks
# C8  Close > SMA50 AND recently emerged (crossed above SMA50 within last 20 bars)
# ──────────────────────────────────────────────────────────────────────────────

def score_minervini(df: pd.DataFrame,
                    nifty_df: pd.DataFrame | None = None) -> tuple[int, dict]:
    """
    Returns (score 0-8, condition_dict).
    nifty_df is the Nifty50 OHLCV dataframe for C7 RS computation.
    """
    close = df["close"]
    high  = df["high"]
    low   = df["low"]

    sma50  = close.rolling(50).mean()
    sma150 = close.rolling(150).mean()
    sma200 = close.rolling(200).mean()

    c    = float(close.iloc[-1])
    s50  = float(sma50.iloc[-1])
    s150 = float(sma150.iloc[-1])
    s200 = float(sma200.iloc[-1])

    s200_clean = sma200.dropna()
    s200_prev  = float(s200_clean.iloc[-30]) if len(s200_clean) >= 30 else None
    sma200_up  = bool(s200 > s200_prev) if (s200_prev and not pd.isna(s200_prev)) else False

    high_52w = float(high.tail(252).max())
    low_52w  = float(low.tail(252).min())

    # ── C7: RS vs Nifty50 ──
    # Stock 26-week return > Nifty 26-week return  AND
    # RS line (stock/nifty ratio) trending up over last 6 weeks (30 trading days)
    c7 = False
    if nifty_df is not None and len(nifty_df) >= 130 and len(close) >= 130:
        try:
            # Align on dates
            stock_aligned = close.copy()
            stock_aligned.index = pd.to_datetime(stock_aligned.index)
            nifty_close = nifty_df["close"].copy()
            nifty_close.index = pd.to_datetime(nifty_close.index)

            merged = pd.concat([stock_aligned, nifty_close], axis=1, join="inner")
            merged.columns = ["stock", "nifty"]
            merged = merged.dropna()

            if len(merged) >= 130:
                # 26-week (130 bars) return comparison
                stock_26w = merged["stock"].iloc[-1] / merged["stock"].iloc[-130] - 1
                nifty_26w = merged["nifty"].iloc[-1] / merged["nifty"].iloc[-130] - 1
                rs_outperforms = stock_26w > nifty_26w

                # RS line trend: slope over last 30 bars
                rs_line = merged["stock"] / merged["nifty"]
                rs_now  = float(rs_line.iloc[-1])
                rs_30ago = float(rs_line.iloc[-30])
                rs_uptrend = rs_now > rs_30ago

                c7 = rs_outperforms and rs_uptrend
        except Exception:
            c7 = False

    # ── C8: Price above SMA50 AND recently emerged from base ──
    # "Recently emerged" proxy: at some point in the last 20 bars the stock was
    # at or below SMA50, and it is now above — i.e., a recent crossover.
    c8 = False
    above_sma50_now = c > s50
    if above_sma50_now and not pd.isna(s50):
        lookback = min(20, len(close) - 1)
        # Check if stock was at or below SMA50 at any point in the last 20 bars
        recent_close  = close.iloc[-(lookback+1):-1]
        recent_sma50  = sma50.iloc[-(lookback+1):-1]
        was_below = (recent_close <= recent_sma50).any()
        c8 = bool(was_below)

    conds = {
        "C1 Close>SMA150+200": c > s150 and c > s200,
        "C2 SMA150>SMA200":    s150 > s200,
        "C3 SMA200 rising":    sma200_up,
        "C4 SMA50>SMA150+200": s50 > s150 and s50 > s200,
        "C5 30%+above52wLow":  c >= low_52w * 1.30,
        "C6 <=25%from52wHigh": c >= high_52w * 0.75,
        "C7 RS>Nifty26w+trend": c7,
        "C8 Emerging>SMA50":   c8,
    }
    return sum(conds.values()), conds


# ──────────────────────────────────────────────────────────────────────────────
# Step 3b — TechnoFunda-Swing (6 quantifiable conditions)
# Source: wiki/strategies/TechnoFunda-Swing.md
# ──────────────────────────────────────────────────────────────────────────────

def score_technofunda(df: pd.DataFrame) -> tuple[int, dict]:
    """
    Returns (score 0-6, condition_dict).
    T1  Close > EMA20
    T2  Close > SMA50
    T3  RSI(14) > 50
    T4  ADX(14) > 20
    T5  Volume contracting: 5d avg < 20d avg (pre-squeeze proxy)
    T6  Today's range >= 0.5 × ATR(14)  [real move, not noise]
    """
    close = df["close"]
    high  = df["high"]
    low   = df["low"]
    vol   = df["volume"]

    ema20 = close.ewm(span=20, adjust=False).mean()
    sma50 = close.rolling(50).mean()

    rsi_series = RSIIndicator(close=close, window=14).rsi()
    adx_series = ADXIndicator(high=high, low=low, close=close, window=14).adx()
    atr_series = AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()

    c         = float(close.iloc[-1])
    rsi_val   = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else None
    adx_val   = float(adx_series.iloc[-1]) if not pd.isna(adx_series.iloc[-1]) else None
    atr_val   = float(atr_series.iloc[-1]) if not pd.isna(atr_series.iloc[-1]) else None
    day_range = float(high.iloc[-1]) - float(low.iloc[-1])

    vol5  = float(vol.tail(5).mean())
    vol20 = float(vol.tail(20).mean())

    conds = {
        "T1 Close>EMA20":    c > float(ema20.iloc[-1]),
        "T2 Close>SMA50":    c > float(sma50.iloc[-1]),
        "T3 RSI>50":         rsi_val is not None and rsi_val > 50,
        "T4 ADX>20":         adx_val is not None and adx_val > 20,
        "T5 VolContracting": vol5 < vol20 * 0.90,
        "T6 RangeVsATR":     atr_val is not None and day_range >= 0.5 * atr_val,
    }
    return sum(conds.values()), conds


# ──────────────────────────────────────────────────────────────────────────────
# Step 4 — Format and export Excel
# ──────────────────────────────────────────────────────────────────────────────

_GREEN      = PatternFill("solid", fgColor="C6EFCE")
_RED        = PatternFill("solid", fgColor="FFC7CE")
_AMBER      = PatternFill("solid", fgColor="FFEB9C")
_BLUE_LIGHT = PatternFill("solid", fgColor="DDEBF7")
_GREY       = PatternFill("solid", fgColor="D9D9D9")

_WAVE_FILLS = {
    "W3":      PatternFill("solid", fgColor="C6EFCE"),
    "W5":      PatternFill("solid", fgColor="DDEBF7"),
    "W2":      PatternFill("solid", fgColor="FFEB9C"),
    "W2-deep": PatternFill("solid", fgColor="FFC7CE"),
    "ABC":     PatternFill("solid", fgColor="FFC7CE"),
    "unclear": PatternFill("solid", fgColor="D9D9D9"),
}
_EXT_FILLS = {
    "EXTENDED":   PatternFill("solid", fgColor="FFEB9C"),
    "EXHAUSTION": PatternFill("solid", fgColor="FFC7CE"),
}

# Source label → background colour for the Sources column
_SOURCE_FILLS = {
    "Bhav":   PatternFill("solid", fgColor="E2EFDA"),   # soft green = high-volume/liquid
    "Darvas": PatternFill("solid", fgColor="DDEBF7"),   # blue = Darvas breakout
    "Nimblr": PatternFill("solid", fgColor="FFEB9C"),   # amber = Nimblr momentum
}


def _style_sheet(ws, df: pd.DataFrame) -> None:
    ws.freeze_panes = "A2"
    col_map = {name: idx + 1 for idx, name in enumerate(df.columns)}

    for cell in ws[1]:
        cell.font = Font(bold=True)

    for row_idx in range(2, len(df) + 2):
        for col_name, col_idx in col_map.items():
            cell = ws.cell(row=row_idx, column=col_idx)
            val  = cell.value

            if col_name == "Total /14":
                cell.fill = _GREEN if (val or 0) >= 11 else (_AMBER if (val or 0) >= 8 else _RED)
            elif col_name == "Minervini /8":
                cell.fill = _GREEN if (val or 0) >= 7 else (_AMBER if (val or 0) >= 5 else _RED)
            elif col_name == "TechnoFunda /6":
                cell.fill = _GREEN if (val or 0) >= 5 else (_AMBER if (val or 0) >= 3 else _RED)
            elif col_name == "EW Wave":
                cell.fill = _WAVE_FILLS.get(str(val or "unclear"), _GREY)
                cell.font = Font(bold=True)
            elif col_name == "EW Confidence":
                cell.fill = _GREEN if (val or 0) >= 60 else (_AMBER if (val or 0) >= 40 else _RED)
            elif col_name in ("W3 T1 1.618 (45%)", "W3 T2 2.618 (30%)", "W3 T3 1.000 (15%)"):
                if val:
                    cell.fill = PatternFill("solid", fgColor="E2EFDA")
            elif col_name in ("W5 T1 eq (35%)", "W5 T2 ext (15%)"):
                if val:
                    cell.fill = _BLUE_LIGHT
            elif col_name == "W2 Low (stop)":
                if val:
                    cell.fill = _RED
            elif col_name == "Ext Risk":
                fill = _EXT_FILLS.get(str(val or "NORMAL"))
                if fill:
                    cell.fill = fill
            elif col_name == "Sources":
                # Colour by source priority: Bhav+Darvas > Darvas > Nimblr
                val_str = str(val or "")
                if "Bhav" in val_str and ("Darvas" in val_str or "Nimblr" in val_str):
                    cell.fill = _GREEN        # confirmed by bhavcopy AND screener
                elif "Bhav" in val_str:
                    cell.fill = _SOURCE_FILLS["Bhav"]
                elif "Darvas" in val_str:
                    cell.fill = _SOURCE_FILLS["Darvas"]
                elif "Nimblr" in val_str:
                    cell.fill = _SOURCE_FILLS["Nimblr"]
            elif col_name.startswith(("C", "T")):
                cell.fill = _GREEN if val else _RED

    for col_name, col_idx in col_map.items():
        col_letter = get_column_letter(col_idx)
        max_len = max(len(str(ws.cell(r, col_idx).value or "")) for r in range(1, len(df) + 2))
        ws.column_dimensions[col_letter].width = min(max_len + 2, 35)


def _export_excel(df: pd.DataFrame, path: Path) -> None:
    ew_all_cols = [c for c in df.columns if c.startswith((
        "EW ", "W1 ", "W2 ", "W3 ", "W4 ", "W5 ", "OWL ", "PTF ", "Ext "))]
    ew_summary  = ["EW Wave", "EW Confidence", "W3 T1 1.618 (45%)", "W5 T1 eq (35%)", "EW Note"]

    main_cols   = [c for c in df.columns if c not in ew_all_cols or c in ew_summary]
    detail_cols = ["Symbol", "Close"] + ew_all_cols

    df_main   = df[[c for c in main_cols   if c in df.columns]]
    df_detail = df[[c for c in detail_cols if c in df.columns]]

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df_main.to_excel(writer,   index=False, sheet_name="Shortlist")
        df_detail.to_excel(writer, index=False, sheet_name="EW Detail")

        _style_sheet(writer.sheets["Shortlist"], df_main)
        _style_sheet(writer.sheets["EW Detail"], df_detail)

    log.info("Saved -> %s", path)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def run_pipeline() -> pd.DataFrame | None:
    log.info("=" * 60)
    log.info("Screener Pipeline — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    log.info("=" * 60)

    # ── 1. Fetch stock lists ──────────────────────────────────────
    symbol_sources: dict[str, list[str]] = {}

    # 1a. NSE Bhavcopy top volume
    bhav_syms = fetch_bhavcopy_top_volume(BHAV_TOP_N)
    for s in bhav_syms:
        symbol_sources.setdefault(s, []).append("Bhav")
    time.sleep(1)

    # 1b. Chartink screeners
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

    # ── 2. Download Nifty50 reference once (for RS computation in C7) ──
    log.info("Downloading Nifty50 reference data...")
    nifty_df = fetch_nifty50(days=300)
    if nifty_df is None:
        log.warning("Could not fetch Nifty50 — C7 RS condition will default to False.")

    # ── 3. Download OHLCV and score ───────────────────────────────
    rows: list[dict] = []
    for i, sym in enumerate(all_symbols, 1):
        log.info("[%d/%d] %s  (sources: %s)",
                 i, len(all_symbols), sym,
                 "+".join(symbol_sources.get(sym, [])))

        df = fetch_ohlcv(sym)
        if df is None:
            log.warning("  [skip] no usable data")
            continue

        try:
            mv_score, mv_conds = score_minervini(df, nifty_df=nifty_df)
            tf_score, tf_conds = score_technofunda(df)
            ew     = analyze_ew(df)
            ew_row = ew_summary_row(ew)
        except Exception as exc:
            log.warning("  [skip] scoring error: %s", exc)
            continue

        close  = float(df["close"].iloc[-1])
        volume = int(df["volume"].iloc[-1])
        total  = mv_score + tf_score

        row: dict = {
            "Symbol":         sym,
            "Close":          round(close, 2),
            "Volume":         volume,
            "Sources":        "+".join(symbol_sources.get(sym, [])),
            "Minervini /8":   mv_score,
            "TechnoFunda /6": tf_score,
            "Total /14":      total,
        }
        row.update(ew_row)
        row.update(mv_conds)
        row.update(tf_conds)
        rows.append(row)

        time.sleep(0.4)

    if not rows:
        log.warning("Nothing scored — no output file written.")
        return None

    results = (
        pd.DataFrame(rows)
        .sort_values("Total /14", ascending=False)
        .reset_index(drop=True)
    )

    # ── 4. Export ─────────────────────────────────────────────────
    out_path = BASE_DIR / f"screener_{datetime.today().strftime('%Y%m%d')}.xlsx"
    _export_excel(results, out_path)

    top = results[["Symbol", "Close", "Sources",
                   "Minervini /8", "TechnoFunda /6", "Total /14"]].head(10)
    log.info("\nTop 10 shortlist:\n%s", top.to_string(index=False))
    log.info("Pipeline complete. %d stocks scored.", len(results))

    return results


if __name__ == "__main__":
    run_pipeline()
