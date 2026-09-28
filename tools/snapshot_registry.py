#!/usr/bin/env python3
"""
snapshot_registry.py — the catalogue of persisted report snapshots.

Each entry names a snapshot, the page that shows it, and a `produce()` that
returns a picklable payload (dicts of DataFrames are fine). Producers are pure
compute — NO Streamlit, no session state — so the same function runs from the
scheduled job (snapshot_refresh.py), from the dashboard's "Refresh now" button
(inside the ui_jobs worker) and from the start-up fill-in thread.

Parameters
----------
A producer computes with the page's DEFAULT parameters and stores the raw
frames alongside the default-parameter result wherever a page has sliders.
The page re-derives its sliders' views live from the stored frames (RRG from
the sector frames, the Darvas thresholds from the bhavcopy, …), so one
snapshot serves every slider position and nothing is computed per combination.

Excluded on purpose
-------------------
- Chartink / Pre-Breakout / High-Growth: need a browser cookie pasted on the
  page; a headless job has none.
- Hidden Treasures, daily opportunity shortlist, scanner runs, orbit charts:
  already persisted by their own tables / dated files.
- Anything symbol-specific (Stock Analyzer, peers, per-symbol shareholding).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Callable

log = logging.getLogger("snapshots")

# Chart-server style sector index tickers → display label. Mirrors the
# dashboard's SECTOR_DISPLAY_NAMES; the dashboard imports THIS one so the two
# can never drift.
SECTOR_DISPLAY_NAMES = {
    "^NSEBANK":            "Banking",
    "NIFTY_FIN_SERVICE.NS": "Fin Services",
    "^CNXIT":              "IT / Telecom",
    "^CNXPHARMA":          "Pharma",
    "^CNXAUTO":            "Auto",
    "^CNXFMCG":            "FMCG / Chem",
    "^CNXMETAL":           "Metals",
    "^CNXREALTY":          "Realty",
    "^CNXINFRA":           "Infra",
    "^CNXENERGY":          "Energy",
    "^CNXCONSUM":          "Cons. Durables",
}
BENCHMARK_TICKER = "^NSEI"
MH_BASKET_SIZE = 60
GAP_VOLUME_DEFAULTS = {"top_n": 500, "gap_pct": 3.0, "vol_mult": 2.0}


@dataclass
class SnapshotSpec:
    name: str                       # storage key, stable
    label: str                      # human label for badges / hub table
    page: str                       # dashboard page that shows it
    produce: Callable[[], Any]
    params: dict = field(default_factory=dict)
    order: int = 100                # scheduled run order (cheap first)
    heavy: bool = False             # minutes rather than seconds


# ── producers ─────────────────────────────────────────────────────────────────
def _yf_frame(ticker: str, period: str = "2y"):
    import pandas as pd
    import yfinance as yf
    df = yf.download(ticker, period=period, interval="1d",
                     progress=False, auto_adjust=True)
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    return df



def _empty(df) -> bool:
    """True for None or an empty frame/series (helpers return either on failure)."""
    return df is None or getattr(df, "empty", False)

def produce_sector_index_data() -> dict:
    """The sector index frames + the NIFTY benchmark, 2y daily. Feeds the
    heatmap, rotation quadrant, RRG and the shareable card."""
    frames: dict = {}
    for t in SECTOR_DISPLAY_NAMES:
        try:
            df = _yf_frame(t)
            if df is not None:
                frames[t] = df
        except Exception as e:                       # noqa: BLE001
            log.warning("sector %s: %s", t, e)
    try:
        bench = _yf_frame(BENCHMARK_TICKER)
    except Exception as e:                           # noqa: BLE001
        log.warning("benchmark: %s", e)
        bench = None
    if not frames:
        raise RuntimeError("no sector index frame could be fetched")
    return {"sector_data": frames, "benchmark": bench}


def produce_sector_money_flow() -> dict:
    import money_flow as _mf
    grid = _mf.sector_grid("nifty500", n=21)
    if grid.get("error"):
        raise RuntimeError(grid["error"])
    if _empty(grid.get("rows")):
        raise RuntimeError("no sector had price data (every constituent fetch failed)")
    return grid


def produce_sector_turnover_share() -> dict:
    import turnover_share as _tsx
    grid = _tsx.rotation_grid("nifty500")
    if grid.get("error"):
        raise RuntimeError(grid["error"])
    return grid


def produce_volume_shockers() -> dict:
    """Bhavcopy frame + the default-threshold Darvas scan. The page re-runs the
    scan from the stored bhavcopy when a slider moves."""
    import trending_stocks as _ts
    bhav, bhav_date = _ts.load_bhav()
    if bhav is None:
        raise RuntimeError("no bhavcopy frame")
    res = _ts.darvas_volume_shockers(bhav, top_n=60, vol_mult=2.0,
                                     move_pct=5.0, min_turnover=0.0)
    res.setdefault("trade_date", None)
    if not res.get("trade_date"):
        res["trade_date"] = bhav_date
    return {"bhav": bhav, "bhav_date": bhav_date, "default": res,
            "default_params": {"top_n": 60, "vol_mult": 2.0,
                               "move_pct": 5.0, "min_turnover_cr": 0.0}}


def produce_trending() -> dict:
    """The 'what moved today' lenses at their page defaults."""
    import trending_stocks as _ts
    bhav, bhav_date = _ts.load_bhav()
    if bhav is None:
        raise RuntimeError("no bhavcopy frame")
    out: dict = {"bhav_date": bhav_date}
    out["movers"] = _ts.price_movers_realtime(bhav, top_n=15, min_turnover=5.0 * 1e7)
    try:
        out["volume"] = _ts.volume_shockers(top_n=15, bhav=bhav)
    except Exception as e:                           # noqa: BLE001
        out["volume_error"] = str(e)
    uni = _ts.liquid_universe(bhav, 200)
    hist = _ts._batch_history(uni, period="max")
    out["extremes"] = {
        "week52": _ts.range_extremes(uni, window=_ts.WEEK52_BARS, near_pct=2.0,
                                     top_n=15, hist=hist),
        "alltime": _ts.range_extremes(uni, window=None, near_pct=2.0,
                                      top_n=15, hist=hist),
        "n_history": len(hist), "universe_n": len(uni),
    }
    return out


def produce_sentiment() -> dict:
    """Sentiment already persists to its own table; this run just refreshes it
    and stores the reading so the badge and the hub see it like the rest."""
    import sentiment_index as senti
    return senti.compute_sentiment(persist=True)


def produce_market_health() -> dict:
    import market_health as mh
    import screener_pipeline as sp
    nifty, vix = mh.fetch_indices()
    symbols = sp.fetch_bhavcopy_top_volume(MH_BASKET_SIZE)
    frames = mh.load_basket(symbols, lambda s: sp.fetch_ohlcv(s, days=260))
    # A run where every source came back empty is a failed run, not an "ok"
    # snapshot of nothing — it must not overwrite the last good payload.
    if _empty(nifty) and _empty(vix) and not frames:
        raise RuntimeError("no index or basket data could be fetched")
    return {"nifty": nifty, "vix": vix, "basket_frames": frames,
            "basket_requested": len(symbols)}


def produce_finviz() -> dict:
    import finviz_sentiment as fvz
    indices, breadth = fvz.fetch_index_snapshot(), fvz.fetch_breadth()
    has_index = (not _empty(indices) and "last" in getattr(indices, "columns", [])
                 and indices["last"].notna().any())
    if not has_index and not breadth:
        raise RuntimeError("finviz returned no index quotes and no breadth")
    return {"indices": indices, "breadth": breadth}


def produce_tv_scan() -> dict:
    import tv_screener as tvs
    df = tvs.fetch_brkoutgeek(min_chg=2.0, min_rel_vol=1.5, min_price_vol_inr=1.0 * 1e7,
                              raise_on_error=True)          # empty = truly no matches
    return {"df": df, "params": {"min_chg": 2.0, "min_rel_vol": 1.5, "min_tv_cr": 1.0}}


def _deals(kind: str) -> dict:
    import pandas as pd
    import india_market_intel as imi
    out: dict = {}
    if kind == "bulk":
        pairs = (("bse", imi.fetch_bse_bulk_deals, "bse_bulk",
                  ["DEAL_DATE", "SCRIP_CODE", "CLIENT_NAME", "QUANTITY", "PRICE"]),
                 ("nse", imi.fetch_nse_bulk_deals, "nse_bulk",
                  ["Date", "Symbol", "Client Name", "Quantity Traded"]))
    else:
        pairs = (("bse", imi.fetch_bse_block_deals, "bse_block",
                  ["DEAL_DATE", "SCRIP_CODE", "CLIENT_NAME", "QUANTITY", "PRICE"]),
                 ("nse", imi.fetch_nse_block_deals, "nse_block",
                  ["Date", "Symbol", "Client Name", "Quantity Traded"]))
    errors = {}
    for exch, fn, ck, keys in pairs:
        try:
            df = fn()
            if not df.empty:
                df = imi.mark_new_rows(df, ck, keys)
        except Exception as e:                       # noqa: BLE001
            df, errors[exch] = pd.DataFrame(), str(e)
        out[exch] = df
    if errors and all(out[k].empty for k in out):
        raise RuntimeError("; ".join(f"{k}: {v}" for k, v in errors.items()))
    out["errors"] = errors
    return out


def produce_bulk_deals() -> dict:
    return _deals("bulk")


def produce_block_deals() -> dict:
    return _deals("block")


def produce_insider_trading() -> dict:
    import india_market_intel as imi
    d_to, d_from = date.today(), date.today() - timedelta(days=7)
    df = imi.fetch_bse_insider_trading(d_from.strftime("%d/%m/%Y"),
                                       d_to.strftime("%d/%m/%Y"))
    if not df.empty:
        df = imi.mark_new_rows(
            df, "bse_insider",
            ["Fld_ID"] if "Fld_ID" in df.columns else df.columns[:3].tolist())
    return {"df": df, "from": d_from.isoformat(), "to": d_to.isoformat()}


def gap_volume_scan(universe: list[str], fetch_ohlcv: Callable, *,
                    gap_pct: float, vol_mult: float,
                    stats: dict | None = None) -> list[dict]:
    """Gap & volume hits over `universe`. Lifted from the India Market Intel
    page so the headless job and the page share one scan. `stats`, if given,
    receives {"scanned": n} — symbols that had a usable frame — so a caller can
    tell "no hits" from "nothing could be fetched"."""
    hits = []
    scanned = 0
    for sym in universe:
        try:
            df = fetch_ohlcv(f"{sym}.NS", days=40)
        except Exception:                             # noqa: BLE001
            continue
        if df is None or len(df) < 21:
            continue
        scanned += 1
        close_col = "close" if "close" in df.columns else "Close"
        open_col = "open" if "open" in df.columns else "Open"
        vol_col = "volume" if "volume" in df.columns else "Volume"
        prev_close = float(df[close_col].iloc[-2])
        today_open = float(df[open_col].iloc[-1])
        if prev_close <= 0:
            continue
        gap = (today_open - prev_close) / prev_close * 100
        vol_avg20 = float(df[vol_col].iloc[-21:-1].mean())
        vol_today = float(df[vol_col].iloc[-1])
        vol_ratio = vol_today / vol_avg20 if vol_avg20 > 0 else 0
        if abs(gap) >= gap_pct or vol_ratio >= vol_mult:
            hits.append({
                "Symbol": sym, "Gap %": round(gap, 2),
                "Vol × 20d Avg": round(vol_ratio, 2),
                "Close": round(float(df[close_col].iloc[-1]), 2),
            })
    if stats is not None:
        stats["scanned"] = scanned
    return sorted(hits, key=lambda h: abs(h["Gap %"]) + h["Vol × 20d Avg"], reverse=True)


def produce_gap_volume() -> dict:
    import screener_pipeline as sp
    p = GAP_VOLUME_DEFAULTS
    universe = sp.fetch_bhavcopy_top_volume(p["top_n"])
    if not universe:
        raise RuntimeError("no universe (bhavcopy top-volume list is empty)")
    stats: dict = {}
    hits = gap_volume_scan(universe, sp.fetch_ohlcv,
                           gap_pct=p["gap_pct"], vol_mult=p["vol_mult"], stats=stats)
    if not stats.get("scanned"):
        raise RuntimeError(f"no OHLCV could be fetched for any of {len(universe)} symbols")
    return {"hits": hits, "universe_n": len(universe),
            "scanned_n": stats["scanned"], "params": dict(p)}


def produce_market_brief() -> dict:
    import market_brief as mbrief
    import sentiment_index as senti
    reading = None
    try:
        import json
        hist = senti.history(days=1)
        if not hist.empty:
            row = hist.iloc[-1]
            reading = {"reading_date": row["reading_date"].date().isoformat(),
                       "score": float(row["score"]), "band": row["band"],
                       "inputs": json.loads(row["inputs_json"])}
    except Exception:                                 # noqa: BLE001
        reading = None
    model = mbrief.build_brief(include_breadth=True, sentiment=reading)
    qm = model.get("quotes_meta") or {}
    quotes = model.get("quotes") or []
    if qm.get("error") or (quotes and qm.get("missing", 0) >= len(quotes)):
        raise RuntimeError(qm.get("error") or "every index quote is missing")
    return model


def produce_institutional_volume() -> dict:
    """Home › Institutional volume: PPV bars with RVOL ≥ 5x in the last 5
    sessions over nifty500. Empty = scanned and found none; a fetch failure
    raises (raise_on_no_data) so it lands as an error row."""
    import institutional_volume_scan as ivs
    df = ivs.scan(raise_on_no_data=True)
    return {"df": df, "params": {"rvol_min": ivs.RVOL_THRESHOLD,
                                 "window": ivs.WINDOW_DAYS, "top_n": ivs.TOP_N}}


# ── registry ──────────────────────────────────────────────────────────────────
SNAPSHOTS: dict[str, SnapshotSpec] = {s.name: s for s in [
    SnapshotSpec("sector_index_data", "Sector index data (heatmap / RRG / card)",
                 "Sector Map", produce_sector_index_data, order=10),
    SnapshotSpec("sector_money_flow", "Sector money flow (CMF)",
                 "Sector Map", produce_sector_money_flow, order=20),
    SnapshotSpec("sector_turnover_share", "Sector turnover share",
                 "Sector Map", produce_sector_turnover_share, order=21),
    SnapshotSpec("volume_shockers", "Volume shockers · Darvas",
                 "Home", produce_volume_shockers, order=30),
    SnapshotSpec("trending", "What moved today",
                 "Home", produce_trending, order=31, heavy=True),
    SnapshotSpec("institutional_volume", "Institutional volume (PPV ≥ 5x RVOL)",
                 "Home", produce_institutional_volume, order=32, heavy=True),
    SnapshotSpec("sentiment", "Market sentiment reading",
                 "Market Sentiment", produce_sentiment, order=40),
    SnapshotSpec("market_health", "Market health gate basket",
                 "Market Sentiment", produce_market_health, order=41),
    SnapshotSpec("finviz", "Finviz US snapshot",
                 "Market Sentiment", produce_finviz, order=42),
    SnapshotSpec("market_brief", "Market brief",
                 "Market Sentiment", produce_market_brief, order=43),
    SnapshotSpec("tv_scan", "TradingView breakout scan",
                 "TradingView", produce_tv_scan, order=50),
    SnapshotSpec("bulk_deals", "Bulk deals (BSE + NSE)",
                 "India Market Intel", produce_bulk_deals, order=60),
    SnapshotSpec("block_deals", "Block deals (BSE + NSE)",
                 "India Market Intel", produce_block_deals, order=61),
    SnapshotSpec("insider_trading", "Insider trading (last 7 days)",
                 "India Market Intel", produce_insider_trading, order=62),
    SnapshotSpec("gap_volume", "Gap & volume scan",
                 "India Market Intel", produce_gap_volume, order=70, heavy=True),
]}


def ordered(names: list[str] | None = None) -> list[SnapshotSpec]:
    specs = [SNAPSHOTS[n] for n in names] if names else list(SNAPSHOTS.values())
    return sorted(specs, key=lambda s: s.order)


def run_one(name: str, *, db_path=None):
    """Compute + persist one snapshot. Returns the SnapshotMeta; never raises —
    a failure is stored as an error row and returned."""
    import snapshot_store as store
    spec = SNAPSHOTS[name]
    t0 = time.time()
    try:
        payload = spec.produce()
        meta = store.save(name, payload, params=spec.params,
                          elapsed=time.time() - t0, db_path=db_path)
        log.info("snapshot %s ok in %.1fs (%d bytes)", name, meta.elapsed, meta.nbytes)
    except Exception as e:                           # noqa: BLE001
        err = f"{type(e).__name__}: {e}"
        meta = store.save_error(name, err, params=spec.params,
                                elapsed=time.time() - t0, db_path=db_path)
        log.warning("snapshot %s FAILED: %s", name, err)
    return meta


def run_all(names: list[str] | None = None, *, progress: Callable[[str], None] | None = None,
            db_path=None) -> list:
    """Run every (or the named) snapshots in order, skip-and-log on failure."""
    out = []
    specs = ordered(names)
    for i, spec in enumerate(specs, 1):
        if progress:
            progress(f"{i}/{len(specs)} {spec.label}")
        out.append(run_one(spec.name, db_path=db_path))
    return out
