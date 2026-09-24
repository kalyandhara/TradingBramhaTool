"""institutional_volume_scan.py — 5-day sliding window for PPV bars with RVOL >= threshold.

Scans the nifty500 universe for pocket pivot volume bars (blue bars from
simple_volume) where the bar's volume is >= a threshold multiple of the
50-bar MA.  Returns the 10 most recent events within the last 5 trading days.

The PPV edge study (ppv_edge_study.py / ppv_variant_study.py) showed that
standalone PPV carries NO measurable forward-return edge at any threshold.
This scan is therefore CONTEXT — institutional footprint detection — not a
signal.  The Home card says so.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

RVOL_THRESHOLD = 5.0
WINDOW_DAYS = 5
TOP_N = 10
HISTORY_PERIOD = "6mo"


@lru_cache(maxsize=1)
def _universe() -> list[str]:
    try:
        import nse_universe as nu
        return nu.symbols("nifty500")
    except Exception as e:
        log.warning("nse_universe unavailable: %s", e)
        return []


def _batch_download(symbols: list[str]) -> dict[str, pd.DataFrame]:
    if not symbols:
        return {}
    try:
        import yfinance as yf
    except Exception as e:
        log.warning("yfinance unavailable: %s", e)
        return {}
    tickers = [f"{s}.NS" if not s.startswith("^") and "." not in s else s
               for s in symbols]
    try:
        raw = yf.download(tickers, period=HISTORY_PERIOD, interval="1d",
                          progress=False, auto_adjust=True, group_by="ticker",
                          threads=True)
    except Exception as e:
        log.warning("batch download failed: %s", e)
        return {}

    out = {}
    if isinstance(raw.columns, pd.MultiIndex):
        for tk in tickers:
            try:
                df = raw[tk].dropna(subset=["Close"])
                if len(df) >= 60:
                    out[tk] = df
            except Exception:
                pass
    elif len(tickers) == 1:
        df = raw.dropna(subset=["Close"])
        if len(df) >= 60:
            out[tickers[0]] = df
    return out


def scan(symbols: list[str] | None = None,
         rvol_min: float = RVOL_THRESHOLD,
         window: int = WINDOW_DAYS,
         top_n: int = TOP_N) -> pd.DataFrame:
    """Scan for recent PPV bars with high RVOL.

    Returns a DataFrame with columns:
      symbol, date, close, change_pct, rvol, volume, ma50_vol, sector
    sorted by date descending then rvol descending, capped at top_n.
    """
    import simple_volume as sv

    if symbols is None:
        symbols = _universe()
    if not symbols:
        return pd.DataFrame()

    hists = _batch_download(symbols)
    if not hists:
        return pd.DataFrame()

    try:
        ind_map = {}
        import nse_universe as nu
        ind_map = nu.industry_map("nifty500")
    except Exception:
        pass

    cutoff = pd.Timestamp(date.today() - timedelta(days=window * 2))
    rows = []

    for ticker, df in hists.items():
        bare = ticker.replace(".NS", "").replace(".BO", "")
        try:
            classified = sv.classify(df)
        except Exception:
            continue

        kinds = classified["kind"].values
        mas = classified["ma"].values
        vols = classified["volume"].values
        closes = df["Close"].values
        dates = df.index

        for i in range(max(0, len(df) - window), len(df)):
            if kinds[i] != "ppv":
                continue
            m = mas[i]
            v = vols[i]
            if np.isnan(m) or m <= 0:
                continue
            rvol = v / m
            if rvol < rvol_min:
                continue

            prev_close = closes[i - 1] if i > 0 else closes[i]
            chg = (closes[i] / prev_close - 1) * 100 if prev_close > 0 else 0

            rows.append({
                "symbol": bare,
                "date": pd.Timestamp(dates[i]).strftime("%Y-%m-%d"),
                "close": round(float(closes[i]), 2),
                "change_pct": round(chg, 2),
                "rvol": round(rvol, 1),
                "volume": int(v),
                "ma50_vol": int(m),
                "sector": ind_map.get(bare, ""),
            })

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows)
    result = result.sort_values(["date", "rvol"], ascending=[False, False])
    return result.head(top_n).reset_index(drop=True)


if __name__ == "__main__":
    import sys
    print("Scanning nifty500 for PPV bars with RVOL >= 5x in last 5 sessions...")
    df = scan()
    if df.empty:
        print("No results.")
        sys.exit(0)
    print(f"\n{len(df)} results:\n")
    for _, r in df.iterrows():
        print(f"  {r['symbol']:20s}  {r['date']}  close={r['close']:>10.2f}  "
              f"chg={r['change_pct']:+.1f}%  rvol={r['rvol']:.1f}x  "
              f"sector={r['sector']}")
