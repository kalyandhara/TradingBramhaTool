"""
data_source.py — Pluggable data source layer for chart_server.py.

To add a new broker (Alpaca, Zerodha, Binance, Polygon, etc.) create a
subclass of DataSource, implement get_ohlcv() and get_latest_price(),
then register it in SOURCES and extend detect_source() to match its symbols.
"""

from __future__ import annotations
import abc
import threading
import time
import logging
from datetime import timezone

import pandas as pd
import requests

log = logging.getLogger(__name__)

# ── Timeframe helpers ─────────────────────────────────────────────────────────

TF_SECONDS = {
    "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "4h": 14400, "1d": 86400, "1w": 604800,
}


# ── Abstract base ─────────────────────────────────────────────────────────────

class DataSource(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    def get_ohlcv(self, symbol: str, timeframe: str, bars: int = 200) -> list[dict]:
        """Return list of {time (unix seconds), open, high, low, close, volume}."""

    @abc.abstractmethod
    def get_latest_price(self, symbol: str) -> float | None:
        """Return the most recent traded price."""

    def get_previous_close(self, symbol: str) -> float | None:
        """Previous *daily* close — the benchmark exchanges/Google Finance use
        for "today's change", independent of whatever intraday timeframe the
        chart is currently displaying. Default implementation derives it from
        the last 2 daily candles; subclasses can override for a cheaper/more
        authoritative source (see YFinanceSource.fast_info)."""
        try:
            bars = self.get_ohlcv(symbol, "1d", bars=2)
        except Exception as e:
            log.warning("get_previous_close fallback fetch failed for %s: %s", symbol, e)
            return None
        if not bars or len(bars) < 2:
            return None
        return bars[-2]["close"]


# ── yfinance ─────────────────────────────────────────────────────────────────

class YFinanceSource(DataSource):
    name = "yfinance"

    # yfinance shares a global HTTP session/cache internally that is not
    # thread-safe — under Flask's threaded=True server, two panes loading
    # at the same time can race and one request can come back with the
    # other ticker's data (observed as one chart's price "replicated" into
    # another). Serialize all yfinance calls to avoid that.
    _lock = threading.Lock()

    _TF = {
        "1m":  ("1m",   "7d"),
        "5m":  ("5m",   "60d"),
        "15m": ("15m",  "60d"),
        "30m": ("30m",  "60d"),
        "1h":  ("1h",   "730d"),
        "4h":  ("1h",   "730d"),   # resample 1h → 4h
        "1d":  ("1d",   "5y"),
        "1w":  ("1wk",  "max"),
    }

    def get_ohlcv(self, symbol: str, timeframe: str, bars: int = 200) -> list[dict]:
        import yfinance as yf
        yf_iv, period = self._TF.get(timeframe, ("1d", "5y"))
        # If caller requests more bars than the default period covers, upgrade
        # the yfinance period so we actually fetch enough history.
        # 252 bars ≈ 1y · 1260 ≈ 5y · 2520 ≈ 10y
        if yf_iv == "1d":
            if bars > 1260:
                period = "max"   # full listing history — covers 10Y+ breakout stocks
            elif bars > 252:
                period = "10y"
            elif bars <= 10:
                # Cheap path for the small daily fetches that run on a timer
                # (previous-close lookup, the live poller). Pulling 5y of daily
                # history to read the last 2-3 rows cost ~0.7s per call, per
                # symbol, every 30s. "1mo" always covers >=10 trading days.
                period = "1mo"
        try:
            with self._lock:
                df = yf.download(symbol, period=period, interval=yf_iv,
                                 progress=False, auto_adjust=True)
        except Exception as e:
            log.warning("yfinance download failed for %s: %s", symbol, e)
            return []
        if df is None or df.empty:
            return []
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]

        df = df.rename(columns=str.title)          # normalise to Title case
        need = ["Open", "High", "Low", "Close", "Volume"]
        for col in need:
            if col not in df.columns:
                return []

        if timeframe == "4h":
            df = (df.resample("4h")
                    .agg({"Open": "first", "High": "max",
                          "Low": "min", "Close": "last", "Volume": "sum"})
                    .dropna(subset=["Open", "Close"]))

        # yfinance sometimes returns a trailing "partial-fill" row where volume
        # is populated but OHLC are NaN (mid-session for a thinly traded name,
        # or a symbol whose exchange feed is a beat behind). If those NaNs land
        # in the JSON response, the browser's strict JSON.parse rejects the
        # `NaN` literal, res.json() throws, and the chart renders blank with
        # no visible error. Drop any row where any of OHLC is NaN before we
        # even reach the tail/serialise step.
        #
        # On a daily request that NaN row is *today's session* — yfinance emits
        # the placeholder before it publishes the aggregated daily candle. So
        # dropping it silently left every NSE/BSE daily chart a session behind,
        # and made "today's change" read exactly +0.00% (the last bar and the
        # previous close both resolved to yesterday). Keep the drop, but
        # remember the placeholder's timestamp so we can rebuild the candle
        # from intraday data below. The placeholder index is authoritative for
        # the timestamp, which avoids inventing one in the wrong timezone.
        live_ts = None
        if timeframe == "1d" and len(df):
            if bool(df[["Open", "High", "Low", "Close"]].iloc[-1].isna().all()):
                live_ts = df.index[-1]
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        df = df.tail(bars)
        import math
        out = []
        for ts, row in df.iterrows():
            try:
                t = int(ts.timestamp())
            except Exception:
                continue
            o, h, l, c = float(row["Open"]), float(row["High"]), float(row["Low"]), float(row["Close"])
            # Defence in depth: dropna above should catch everything, but
            # skip any row that slipped through rather than emit NaN JSON.
            if any(math.isnan(v) for v in (o, h, l, c)):
                continue
            v = row["Volume"]
            v = 0.0 if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)
            out.append({
                "time":   t,
                "open":   round(o, 4),
                "high":   round(h, 4),
                "low":    round(l, 4),
                "close":  round(c, 4),
                "volume": v,
            })

        # Rebuild the current session's daily candle from intraday bars so the
        # chart, the ticker and every indicator see today rather than the last
        # completed session.
        if live_ts is not None:
            live = self._session_bar_from_intraday(symbol, live_ts)
            if live and (not out or live["time"] > out[-1]["time"]):
                out.append(live)
                if len(out) > bars:
                    out = out[-bars:]
        return out

    def _session_bar_from_intraday(self, symbol: str, session_ts) -> dict | None:
        """Aggregate the current session's intraday bars into one daily candle.

        `session_ts` is the timestamp of yfinance's own placeholder row, so the
        synthesized bar lands exactly on the daily grid. Returns None rather
        than guessing whenever the intraday data does not clearly belong to
        that session — a stale-but-honest chart beats a fabricated candle.
        """
        # Relies on yfinance's default prepost=False: the intraday fetch returns
        # regular-session bars only (AAPL 1m over a full day = exactly 390).
        # If that default is ever changed here, a pre-open call would aggregate
        # thin pre-market ticks into what looks like a full daily candle.
        import math
        import yfinance as yf
        for interval in ("1m", "5m"):
            try:
                with self._lock:
                    m = yf.download(symbol, period="1d", interval=interval,
                                    progress=False, auto_adjust=True)
            except Exception as e:
                log.debug("intraday fetch failed for %s @%s: %s", symbol, interval, e)
                continue
            if m is None or m.empty:
                continue
            if isinstance(m.columns, pd.MultiIndex):
                m.columns = [c[0] for c in m.columns]
            m = m.rename(columns=str.title)
            if not {"Open", "High", "Low", "Close"} <= set(m.columns):
                continue
            m = m.dropna(subset=["Open", "High", "Low", "Close"])
            if m.empty:
                continue
            # period="1d" returns the *most recent* session, which on a holiday
            # or over a weekend is not the session we are filling. Yahoo's
            # intraday index is UTC and NSE/BSE/US sessions never straddle a UTC
            # date boundary, so comparing calendar dates is sufficient here.
            try:
                if m.index[-1].date() != session_ts.date():
                    log.debug("intraday session %s != placeholder %s for %s — skipping",
                              m.index[-1].date(), session_ts.date(), symbol)
                    return None
            except Exception:
                return None
            try:
                o = float(m["Open"].iloc[0])
                h = float(m["High"].max())
                l = float(m["Low"].min())
                c = float(m["Close"].iloc[-1])
                v = float(m["Volume"].sum()) if "Volume" in m.columns else 0.0
            except Exception:
                continue
            if any(math.isnan(x) for x in (o, h, l, c)):
                continue
            if math.isnan(v):
                v = 0.0
            return {
                "time":   int(session_ts.timestamp()),
                "open":   round(o, 4),
                "high":   round(h, 4),
                "low":    round(l, 4),
                "close":  round(c, 4),
                "volume": v,
            }
        return None

    def get_latest_price(self, symbol: str) -> float | None:
        import yfinance as yf
        try:
            bars = self.get_ohlcv(symbol, "1m", bars=2)
            return bars[-1]["close"] if bars else None
        except Exception:
            return None

    # NOTE: there used to be a get_previous_close() override here that read
    # yfinance's fast_info.previousClose. It was removed deliberately.
    # fast_info.previousClose is relative to *today*, while the chart's last
    # bar was the last *completed* session — so whenever today's candle was
    # missing the two references collapsed onto the same session and the
    # change read exactly +0.00%. The base implementation derives the previous
    # close from bars[-2] of the same series the chart is drawing, so the two
    # can never disagree by construction. With today's candle now rebuilt
    # above, it yields the same number Google shows during a session, and the
    # last completed session's change outside one.


# ── Hyperliquid ───────────────────────────────────────────────────────────────

class HyperliquidSource(DataSource):
    name = "hyperliquid"
    _API = "https://api.hyperliquid.xyz/info"

    _TF = {
        "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
        "1h": "1h", "4h": "4h", "1d": "1d",   "1w":  "1w",
    }

    def get_ohlcv(self, symbol: str, timeframe: str, bars: int = 200) -> list[dict]:
        interval = self._TF.get(timeframe, "1h")
        secs = TF_SECONDS.get(timeframe, 3600)
        end_ms = int(time.time() * 1000)
        start_ms = end_ms - (bars + 5) * secs * 1000
        try:
            r = requests.post(self._API, json={
                "type": "candleSnapshot",
                "req": {"coin": symbol, "interval": interval,
                        "startTime": start_ms, "endTime": end_ms},
            }, timeout=10)
            r.raise_for_status()
            candles = r.json()
        except Exception as e:
            log.warning("Hyperliquid REST failed for %s: %s", symbol, e)
            return []

        out = []
        for c in candles[-bars:]:
            try:
                out.append({
                    "time":   int(c["t"]) // 1000,
                    "open":   float(c["o"]),
                    "high":   float(c["h"]),
                    "low":    float(c["l"]),
                    "close":  float(c["c"]),
                    "volume": float(c["v"]),
                })
            except Exception:
                continue
        return out

    def get_latest_price(self, symbol: str) -> float | None:
        try:
            r = requests.post(self._API, json={"type": "allMids"}, timeout=5)
            mids = r.json()
            v = mids.get(symbol)
            return float(v) if v else None
        except Exception:
            return None


# ── Registry ──────────────────────────────────────────────────────────────────

SOURCES: dict[str, DataSource] = {
    "yfinance":    YFinanceSource(),
    "hyperliquid": HyperliquidSource(),
    # Add new brokers here:
    # "alpaca":   AlpacaSource(),
    # "zerodha":  ZerodhaSource(),
    # "binance":  BinanceSource(),
    # "polygon":  PolygonSource(),
}


def detect_source(symbol: str) -> DataSource:
    """Choose a data source automatically from the symbol format."""
    s = symbol.upper()
    if s.endswith((".NS", ".BO", ".BSE")):
        return SOURCES["yfinance"]
    # Index symbols (^NSEI, ^NSEBANK, ^CNXIT …) and US tickers
    if s.startswith("^") or s.endswith((".NYSE", ".NASDAQ", ".AMEX")):
        return SOURCES["yfinance"]
    # Bare US stock tickers (AAPL, MSFT …) from the symbol directory
    try:
        from symbol_directory import is_known_equity_symbol
        if is_known_equity_symbol(s):
            return SOURCES["yfinance"]
    except Exception:
        pass
    # Default: treat bare coin names (BTC, ETH, SOL …) as Hyperliquid
    return SOURCES["hyperliquid"]
