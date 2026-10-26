"""event_study.py — did NIFTY and the NSE sector indices move abnormally on
policy event days, compared with ordinary days?

Spec: docs/superpowers/specs/2026-10-26-policy-event-study-design.md

A measuring instrument, not a signal: every study run through it is
pre-registered on the wiki first, and a null result is calibration. The library
does no file or network I/O of its own except through the loaders, which take
injectable callables so the tests never touch the network.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

MARKET = "^NSEI"
#: The 12 non-market series. ^CNXMEDIA is excluded: Yahoo serves one bar of it
#: (probed 2026-10-26), against 2010-11 starts for everything below.
SECTORS: list[str] = ["^NSEBANK", "^CNXIT", "^CNXPHARMA", "^CNXFMCG", "^CNXMETAL",
                      "^CNXINFRA", "^CNXREALTY", "^CNXENERGY", "^CNXAUTO",
                      "^CNXPSUBANK", "^CNXPSE", "NIFTY_FIN_SERVICE.NS"]
#: Rate-sensitive basket for the MPC directional tests (equal-weighted).
BASKET: list[str] = ["^NSEBANK", "^CNXPSUBANK", "^CNXREALTY", "^CNXAUTO",
                     "NIFTY_FIN_SERVICE.NS"]
DEFAULT_CACHE = Path(__file__).resolve().parent / "cache" / "event_study"

#: Allowed labels per event type. A label outside these is an error, not a
#: silently new bucket — a typo would otherwise become its own tiny sample.
EVENT_LABELS: dict[str, set[str]] = {
    "mpc": {"cut", "hike", "hold"},
    "budget": {"full", "interim"},
}

EVENT_COLUMNS = ["date", "event_type", "label", "scheduled", "time_ist",
                 "source_url", "notes"]


# --------------------------------------------------------------------------- #
# Events
# --------------------------------------------------------------------------- #

def load_events(path, types: list[str] | None = None,
                scheduled_only: bool = True) -> pd.DataFrame:
    """Read and validate the events CSV; validation runs on the whole file, so a
    bad row is caught even when it would have been filtered out."""
    df = pd.read_csv(Path(path), dtype=str, keep_default_na=False)
    missing = [c for c in EVENT_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"events file missing columns: {missing}")
    df = df[EVENT_COLUMNS].copy()
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    df["scheduled"] = df["scheduled"].astype(int)

    for _, r in df.iterrows():
        allowed = EVENT_LABELS.get(r["event_type"])
        if allowed is None:
            raise ValueError(f"unknown event_type {r['event_type']!r} on {r['date'].date()}")
        if r["label"] not in allowed:
            raise ValueError(f"unknown label {r['label']!r} for {r['event_type']} "
                             f"on {r['date'].date()}")
    dup = df.duplicated(["date", "event_type"], keep=False)
    if dup.any():
        raise ValueError("duplicate (date, event_type): "
                         + ", ".join(str(d.date()) for d in df.loc[dup, "date"].unique()))

    if types is not None:
        df = df[df["event_type"].isin(types)]
    if scheduled_only:
        df = df[df["scheduled"] == 1]
    return df.sort_values("date").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Prices
# --------------------------------------------------------------------------- #

def _yahoo_download(tickers: list[str], start: str) -> pd.DataFrame:
    import yfinance as yf
    return yf.download(tickers, start=start, interval="1d", auto_adjust=True,
                       group_by="ticker", progress=False, threads=True)


def _close_frame(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Wide Close frame from whatever shape yfinance returned."""
    if isinstance(raw.columns, pd.MultiIndex):
        lv0 = raw.columns.get_level_values(0)
        out = {t: raw[(t, "Close")] for t in tickers if (t, "Close") in raw.columns}
        if not out and "Close" in lv0:            # (field, ticker) layout
            out = {t: raw[("Close", t)] for t in tickers if ("Close", t) in raw.columns}
    else:                                         # single ticker, flat columns
        out = {tickers[0]: raw["Close"]} if "Close" in raw.columns else {}
    df = pd.DataFrame(out)
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df.sort_index()


def _last_weekday_before(today: pd.Timestamp) -> pd.Timestamp:
    d = today.normalize() - pd.Timedelta(days=1)
    while d.weekday() >= 5:
        d -= pd.Timedelta(days=1)
    return d


def load_closes(tickers: list[str], start: str, download=None,
                cache_dir: Path | None = None, min_obs: int = 250,
                today: pd.Timestamp | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Wide close frame (NaN where a series has no bar) and the omitted tickers.

    The cache is reused only while it reaches the last weekday before `today`,
    so a stale cache silently shortening the sample cannot happen. A ticker with
    fewer than `min_obs` closes is omitted — it cannot carry an estimation
    window — and the caller reports it."""
    cache_dir = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE
    today = pd.Timestamp.today() if today is None else pd.Timestamp(today)
    cache = cache_dir / f"closes_{start}.csv"
    df = None
    if cache.exists():
        cached = pd.read_csv(cache, index_col=0, parse_dates=True)
        if (set(tickers) <= set(cached.columns)
                and cached.index.max() >= _last_weekday_before(today)):
            df = cached[tickers]
    if df is None:
        download = download or _yahoo_download
        df = _close_frame(download(tickers, start), tickers)
        df = df.reindex(columns=tickers)
        cache_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache)
    counts = df.notna().sum()
    omitted = [t for t in tickers if counts.get(t, 0) < min_obs]
    for t in omitted:
        log.warning("event_study: omitting %s (%d closes < %d)", t, counts.get(t, 0), min_obs)
    return df.drop(columns=omitted), omitted


def pair_returns(closes: pd.DataFrame, ticker: str, market: str = MARKET) -> pd.DataFrame:
    """Log returns of `ticker` (r) and the market (m) on the dates BOTH printed.

    A day either series is missing is dropped before differencing, so a gap
    becomes one multi-day return, never a forward-filled zero."""
    both = closes[[ticker, market]].dropna()
    lr = np.log(both).diff().dropna()
    return lr.rename(columns={ticker: "r", market: "m"})


def snap_to_sessions(dates: pd.Series, index: pd.DatetimeIndex) -> tuple[np.ndarray, np.ndarray]:
    """Position of the first session on or after each date (-1 past the end),
    and whether that session differs from the date (a Saturday budget, say)."""
    d = pd.to_datetime(pd.Series(dates)).dt.normalize().to_numpy()
    pos = index.searchsorted(d, side="left")
    snapped = np.zeros(len(d), dtype=bool)
    out = np.full(len(d), -1, dtype=int)
    for i, p in enumerate(pos):
        if p < len(index):
            out[i] = p
            snapped[i] = index[p] != pd.Timestamp(d[i])
    return out, snapped
