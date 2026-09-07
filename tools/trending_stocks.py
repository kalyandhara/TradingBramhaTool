"""trending_stocks.py — the four "what's trending today" lenses, in one place.

Price Movers · Volume Shockers · 52-Week High/Low · All-Time High/Low.

The desk already owned the data for all four, scattered across four modules and
three pages. Nothing here re-implements a primitive; it composes them into the
one view the tool was missing — "what is moving right now, and why".

    Price Movers      screener_pipeline.fetch_bhavcopy_frame (whole market, EOD)
    Volume Shockers   volume_anomaly.scan  (whole market, WITH cause attribution)
    52W / All-Time    batched yfinance history over a bounded liquid universe

── Two limits stated up front, because they change how you read the output ────

1. **Price Movers needs a liquidity floor or it is a penny-stock list.** A ₹3
   share moving 19% is arithmetic, not information; on any given session the
   unfiltered top-gainers list is almost entirely names you cannot trade in size.
   `MIN_TURNOVER` is applied by default and always reported, so the number you
   see is "top movers *among tradeable names*", not "top movers".

2. **52W / All-Time run on a BOUNDED universe, not the whole market.** NSE's
   bhavcopy carries no 52-week columns (verified 2026-09-02 on the UDiFF file:
   34 columns, none of them a range extreme), so the extremes have to be computed
   from history — one download per name. That is bounded to the top
   `universe_n` by turnover and the count is returned in the result, so the
   answer is never mistaken for a full-market scan.

── The tab this deliberately does NOT have ───────────────────────────────────
**"Most Visited"** is crowd page-view data from a site's own traffic logs. There
is no free NSE or public feed for retail attention, and the honest options are a
proxy (delivery spikes, rank churn) that measures something else while wearing
the same label. Left out rather than faked — see the module's page in the
dashboard, which says so where a user would otherwise wonder.

Nothing here is a signal. These are attention lists: a starting point for
"why did this move?", the same footing `volume_anomaly` puts its spikes on.

CLI:
    py -3 tools/trending_stocks.py                    # all four lenses
    py -3 tools/trending_stocks.py --lens movers
    py -3 tools/trending_stocks.py --lens 52w --universe 150
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import numpy as np
import pandas as pd

import screener_pipeline as sp

log = logging.getLogger(__name__)

#: Below this traded value a "top mover" is a penny-stock artefact. Rupees.
MIN_TURNOVER = 5_00_00_000.0        # ₹5 crore

#: How many names each side (gainers / losers, highs / lows).
TOP_N = 15

#: Default bounded universe for the history-dependent lenses.
UNIVERSE_N = 200

#: Trading days in a year — the 52-week window.
WEEK52_BARS = 252

#: Within this % of the extreme still counts as "at" it.
NEAR_PCT = 2.0

CRORE = 1e7


# ── shared ────────────────────────────────────────────────────────────────────

def load_bhav() -> tuple[Optional[pd.DataFrame], Optional[str]]:
    """Latest EQ bhavcopy frame + its trade date, or (None, None)."""
    df = sp.fetch_bhavcopy_frame()
    if df is None or df.empty:
        return None, None
    date = None
    if "trade_date" in df.columns and not df["trade_date"].isna().all():
        date = str(df["trade_date"].dropna().iloc[0])
    return df, date


def liquid_universe(bhav: pd.DataFrame, n: int = UNIVERSE_N) -> list[str]:
    """Top `n` symbols by traded value — the bounded universe for the
    history-dependent lenses."""
    if bhav is None or bhav.empty:
        return []
    d = bhav.dropna(subset=["turnover"]).nlargest(n, "turnover")
    return d["symbol"].astype(str).str.strip().tolist()


def _pct_change(bhav: pd.DataFrame) -> pd.DataFrame:
    d = bhav.copy()
    d["close"] = pd.to_numeric(d["close"], errors="coerce")
    d["prev_close"] = pd.to_numeric(d["prev_close"], errors="coerce")
    d = d[(d["close"] > 0) & (d["prev_close"] > 0)]
    d["chg"] = d["close"] - d["prev_close"]
    d["chg_pct"] = d["chg"] / d["prev_close"] * 100.0
    return d


# ── lens 1 · price movers ─────────────────────────────────────────────────────

def price_movers(bhav: pd.DataFrame, top_n: int = TOP_N,
                 min_turnover: float = MIN_TURNOVER) -> dict[str, Any]:
    """Top gainers and losers among names that actually trade.

    The turnover floor is the whole point — see the module docstring. Both the
    floor and how many names it removed are returned, so the filtering is
    visible rather than silent.
    """
    if bhav is None or bhav.empty:
        return {"gainers": pd.DataFrame(), "losers": pd.DataFrame(),
                "n_universe": 0, "n_filtered": 0, "min_turnover": min_turnover}

    d = _pct_change(bhav)
    n_all = len(d)
    if not bhav.attrs.get("turnover_is_qty", False):
        d = d[d["turnover"] >= min_turnover]
    cols = ["symbol", "close", "chg", "chg_pct", "turnover", "volume"]
    d = d[cols]

    return {
        "gainers": d.nlargest(top_n, "chg_pct").reset_index(drop=True),
        "losers": d.nsmallest(top_n, "chg_pct").reset_index(drop=True),
        "n_universe": n_all,
        "n_filtered": len(d),
        "min_turnover": min_turnover,
        "turnover_is_qty": bool(bhav.attrs.get("turnover_is_qty", False)),
    }


# ── lens 2 · volume shockers ──────────────────────────────────────────────────

def volume_shockers(top_n: int = TOP_N,
                    bhav: Optional[pd.DataFrame] = None,
                    live: bool = True,
                    prefilter_n: int = 750) -> dict[str, Any]:
    """Whole-market volume spikes, WITH the cause, via volume_anomaly.

    This is the one lens where the desk already beats the screener it is modelled
    on: `volume_anomaly` attributes each spike to a corporate filing, prop churn,
    deal activity, or nothing — so the list answers "why" and not only "what".

    Pass `bhav` to reuse the frame the caller already downloaded; `scan()` takes
    an injectable `frame` precisely so this does not become a second download of
    the same file.
    """
    try:
        import volume_anomaly as va
    except Exception as e:
        return {"error": f"volume_anomaly unavailable: {e}", "rows": pd.DataFrame()}

    # yfinance leads here too: `scan()` reads today's volume straight off the
    # frame it is handed, so overlaying the frame is the whole change. Its own
    # baseline already excludes the latest bar, so a live today does not leak
    # into the average it is measured against.
    overlay: dict[str, Any] = {}
    if bhav is None:
        bhav, _ = load_bhav()
    if bhav is not None and not bhav.empty and live:
        try:
            pre = bhav.dropna(subset=["turnover"]).nlargest(
                min(prefilter_n, len(bhav)), "turnover")
            bhav, _h = yf_session_overlay(
                bhav, pre["symbol"].astype(str).str.strip().tolist())
            overlay = dict(bhav.attrs.get("overlay") or {})
        except Exception as e:
            log.warning("session overlay failed, staying on bhavcopy: %s", e)
            overlay = {"error": str(e), "n_overlaid": 0}

    try:
        res = va.scan(frame=bhav) if bhav is not None else va.scan()
    except Exception as e:
        log.warning("volume_anomaly.scan failed: %s", e)
        return {"error": str(e), "rows": pd.DataFrame()}

    if res.get("error"):
        return {"error": res["error"], "rows": pd.DataFrame()}

    # NOTE: scan() returns `hits` as a COUNT and the records under `rows`.
    rows = res.get("rows") or []
    if not rows:
        return {"rows": pd.DataFrame(), "tally": res.get("tally"),
                "trade_date": res.get("trade_date"), "overlay": overlay,
                "raw": res}
    df = pd.DataFrame(rows)
    # scan() ranks by spike multiple already; keep that order, just cap it.
    return {"rows": df.head(top_n).reset_index(drop=True),
            "tally": res.get("tally"),
            "n_hits": res.get("hits"),
            "universe": res.get("universe"),
            "trade_date": res.get("trade_date"),
            "overlay": overlay,
            "raw": res}


# ── the session overlay · yfinance first, bhavcopy as the floor ───────────────
#
# The bhavcopy is EOD-only and its downloader walks BACK from today, so during
# the whole trading day — and any morning before NSE republishes — the "today"
# row in every bhavcopy-driven scan is the PREVIOUS session. That is the staleness
# this overlay fixes: yfinance leads, bhavcopy stays underneath.
#
# The reason bhavcopy was primary in the first place is real and is NOT discarded
# here: yfinance silently serves a stale bar for thinner NSE names (2026-08-28,
# MASTEK/OAL — a 43.9x volume day read as 0.9x). So a yfinance bar is accepted
# ONLY when its date is strictly NEWER than the bhavcopy's trade date. A stale or
# missing yfinance bar cannot overwrite anything; that symbol simply keeps its
# bhavcopy row. Silence downgrades to the old behaviour instead of to a wrong number.
#
# Every overlaid row is marked in a `src` column ("yf" / "bhav") and the counts
# come back in the frame's attrs, so a page can say which source it is reading.

def yf_session_overlay(bhav: pd.DataFrame,
                       symbols: Optional[list[str]] = None,
                       hist: Optional[dict[str, pd.DataFrame]] = None,
                       period: str = "3mo",
                       since: Optional[str] = None,
                       ) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Overlay yfinance's latest bar onto `bhav` for `symbols`.

    Returns the overlaid frame and the history dict, because the caller almost
    always needs the same history for its lookback — downloading it twice is the
    only real cost here, and this hands it back so nobody pays it.

    `since` is the date a yfinance bar must beat. Pass it explicitly when the
    frame has ALREADY been through one overlay pass: its `trade_date` column is
    mixed by then, and inferring the floor from row 0 would read an
    already-freshened row and reject every remaining name.
    """
    if bhav is None or bhav.empty:
        return bhav, (hist or {})

    d = bhav.copy()
    if "src" not in d.columns:
        d["src"] = "bhav"
    syms = symbols if symbols is not None else d["symbol"].astype(str).str.strip().tolist()
    if hist is None:
        hist = _batch_history(syms, period=period)
    if not hist:
        d.attrs.update(bhav.attrs)
        d.attrs["overlay"] = {"n_overlaid": 0, "n_asked": len(syms),
                              "yf_date": None, "reason": "no yfinance history"}
        return d, {}

    bhav_date = pd.to_datetime(since, errors="coerce") if since else None
    if bhav_date is not None and pd.isna(bhav_date):
        bhav_date = None
    if bhav_date is None and "trade_date" in d.columns and not d["trade_date"].isna().all():
        bhav_date = pd.to_datetime(d["trade_date"].dropna().iloc[0], errors="coerce")
    if bhav_date is not None and pd.isna(bhav_date):
        bhav_date = None

    idx = {str(v).strip(): i for i, v in enumerate(d["symbol"].astype(str))}
    n_ok = n_stale = 0
    yf_dates: list[pd.Timestamp] = []
    for sym in syms:
        h = hist.get(sym)
        row_i = idx.get(sym)
        if h is None or h.empty or row_i is None or "Volume" not in h:
            continue
        last_ts = pd.to_datetime(h.index[-1]).tz_localize(None).normalize()
        # The whole guard: only a STRICTLY newer bar may overwrite the bhavcopy.
        if bhav_date is not None and last_ts <= bhav_date.normalize():
            n_stale += 1
            continue
        if len(h) < 2:
            continue
        close = float(h["Close"].iloc[-1])
        prev = float(h["Close"].iloc[-2])
        vol = float(h["Volume"].iloc[-1])
        if not (close > 0 and prev > 0 and vol > 0):
            n_stale += 1
            continue
        d.at[d.index[row_i], "close"] = close
        d.at[d.index[row_i], "prev_close"] = prev
        d.at[d.index[row_i], "volume"] = vol
        # Turnover is a VALUE column; yfinance has no traded value, so close*vol
        # is the only estimate available. It is used for the liquidity floor and
        # for ranking, both of which tolerate an approximation.
        d.at[d.index[row_i], "turnover"] = close * vol
        d.at[d.index[row_i], "src"] = "yf"
        d.at[d.index[row_i], "trade_date"] = last_ts.strftime("%Y-%m-%d")
        yf_dates.append(last_ts)
        n_ok += 1

    d.attrs.update(bhav.attrs)
    d.attrs["overlay"] = {
        "n_overlaid": n_ok,
        "n_stale": n_stale,
        "n_asked": len(syms),
        "yf_date": max(yf_dates).strftime("%Y-%m-%d") if yf_dates else None,
        "bhav_date": bhav_date.strftime("%Y-%m-%d") if bhav_date is not None else None,
    }
    return d, hist


def _prior_volumes(h: pd.DataFrame, session: Optional[pd.Timestamp], n: int = 9) -> list[float]:
    """The `n` sessions BEFORE `session`, as volumes.

    Splitting this out matters once yfinance leads: its history already contains
    today's bar, so taking the plain last-9 would count today twice — once as the
    spike and once inside the average it is measured against.
    """
    v = h["Volume"]
    if session is not None:
        try:
            keep = pd.to_datetime(h.index).tz_localize(None).normalize() < session.normalize()
            v = v[keep]
        except Exception:
            pass
    return [float(x) for x in v.tolist()[-n:] if x and x > 0]


# ── lens 2b · Darvas-box volume shockers (Chartink criteria) ──────────────────
#
# The reference scan ("VOLUME SHOCKERS (STOCKS WITH RISING VOLUMES) DARVAS") is
# two conditions and nothing else:
#
#     Daily Volume > 2 x Daily SMA(volume, 10)
#     AND ( Daily Close > 1.05 x 1-day-ago Close
#           OR Daily Close < 0.95 x 1-day-ago Close )
#
# i.e. a >=5% move in EITHER direction on more than double the 10-day average
# volume — the Darvas premise that a box only breaks on conviction volume.
#
# Two data notes, because they decide whether the numbers match Chartink:
#
# 1. Chartink's SMA(volume,10) INCLUDES the current session. So does this:
#    sma10 = (sum of the prior 9 sessions + today) / 10. Using the prior-10 mean
#    instead would silently loosen the filter for every name.
# 2. Today's volume/close/prev_close come from yfinance when it has a bar NEWER
#    than the bhavcopy, and from the NSE bhavcopy otherwise (see
#    `yf_session_overlay`). The bhavcopy is EOD-only, so before it publishes,
#    a bhavcopy-led scan is yesterday's session while Chartink shows today's
#    -- that gap was the whole reason to promote yfinance. The prior 9 sessions
#    come from the same batched history, with any bar on or after the session
#    date excluded so today is not counted inside its own average.

#: Volume must exceed this multiple of SMA(volume, 10).
DARVAS_VOL_MULT = 2.0

#: Minimum absolute move vs the previous close, in %.
DARVAS_MOVE_PCT = 5.0

#: Bhavcopy names ranked by turnover that the price gate is applied to.
DARVAS_PREFILTER_N = 750


def darvas_volume_shockers(bhav: Optional[pd.DataFrame] = None,
                           top_n: int = TOP_N,
                           vol_mult: float = DARVAS_VOL_MULT,
                           move_pct: float = DARVAS_MOVE_PCT,
                           min_turnover: float = MIN_TURNOVER,
                           prefilter_n: int = DARVAS_PREFILTER_N,
                           hist: Optional[dict[str, pd.DataFrame]] = None,
                           live: bool = True,
                           ) -> dict[str, Any]:
    """Chartink's Darvas volume-shocker scan, computed locally.

    Returns `rows` ranked by volume multiple, plus the counts at each gate so the
    page can say how many names each condition removed rather than only showing
    the survivors.
    """
    if bhav is None:
        bhav, _ = load_bhav()
    if bhav is None or bhav.empty:
        return {"error": "no bhavcopy frame", "rows": pd.DataFrame()}

    # yfinance FIRST, bhavcopy underneath. The overlay runs on the top
    # `prefilter_n` names by bhavcopy turnover rather than the whole ~2,600-row
    # market: one download of a size the page can afford, and it is the SAME
    # download the SMA lookback needs anyway, so it costs nothing extra.
    overlay: dict[str, Any] = {}
    floor_date: Optional[str] = None
    if "trade_date" in bhav.columns and not bhav["trade_date"].isna().all():
        floor_date = str(bhav["trade_date"].dropna().iloc[0])
    if live:
        pre = bhav.dropna(subset=["turnover"]).nlargest(
            min(prefilter_n * 2, len(bhav)), "turnover")
        pre_syms = pre["symbol"].astype(str).str.strip().tolist()
        try:
            bhav, hist = yf_session_overlay(bhav, pre_syms, hist=hist,
                                            since=floor_date)
            overlay = dict(bhav.attrs.get("overlay") or {})
        except Exception as e:                       # never let live data break EOD
            log.warning("session overlay failed, staying on bhavcopy: %s", e)
            overlay = {"error": str(e), "n_overlaid": 0}

    d = _pct_change(bhav)
    n_universe = len(d)
    d["volume"] = pd.to_numeric(d["volume"], errors="coerce")
    d["turnover"] = pd.to_numeric(d["turnover"], errors="coerce")
    d = d.dropna(subset=["volume"])
    d = d[d["volume"] > 0]

    # Liquidity floor — same reasoning as price movers; skipped when the feed
    # gave us quantity rather than value in the turnover column.
    if not bhav.attrs.get("turnover_is_qty", False):
        d = d[d["turnover"] >= min_turnover]
    n_liquid = len(d)

    # Gate 1 (free): the +-move_pct% price condition, off the bhavcopy alone.
    d = d[d["chg_pct"].abs() >= move_pct]
    d = d.nlargest(min(prefilter_n, len(d)), "turnover")
    n_price = len(d)
    if n_price == 0:
        return {"rows": pd.DataFrame(), "n_universe": n_universe,
                "n_liquid": n_liquid, "n_price": 0, "n_scanned": 0,
                "vol_mult": vol_mult, "move_pct": move_pct,
                "overlay": overlay}

    syms = d["symbol"].astype(str).str.strip().tolist()
    if hist is None:
        hist = _batch_history(syms, period="3mo")
    elif live:
        # The overlay downloaded the top names by turnover; the price gate can
        # let through names below that cut, and a name with no history is a name
        # silently dropped from the scan. Top up rather than lose it. Only when
        # `live` — an injected `hist` with the overlay off is the caller's
        # deliberate, offline choice and must not reach the network.
        missing = [x for x in syms if x not in hist]
        if missing:
            hist = {**hist, **_batch_history(missing, period="3mo")}

    if live:
        # Second pass, over the gated shortlist only. Without it the output is a
        # MIXED-SESSION list — the names below the overlay's turnover cut passed
        # the gate on their last-EOD move and then out-rank today's real movers
        # with a multiple computed from a different day. Now that their history
        # has been fetched anyway, they cost nothing to freshen, and the gate is
        # re-applied so nothing survives on a move it no longer has.
        try:
            d, _ = yf_session_overlay(d, syms, hist=hist, since=floor_date)
            _ov2 = dict(d.attrs.get("overlay") or {})
            # The shortlist pass is the one that describes the OUTPUT, so its
            # counts win — but keep the wide pass's count of what it freshened.
            if _ov2:
                _ov2["n_overlaid_prefilter"] = overlay.get("n_overlaid", 0)
                _ov2["yf_date"] = _ov2.get("yf_date") or overlay.get("yf_date")
                _ov2["bhav_date"] = _ov2.get("bhav_date") or floor_date
                overlay = _ov2
            d = _pct_change(d)
            d = d[d["chg_pct"].abs() >= move_pct]
            n_price = len(d)
        except Exception as e:
            log.warning("shortlist overlay failed, staying on bhavcopy: %s", e)

    out: list[dict[str, Any]] = []
    n_scanned = 0
    for r in d.to_dict("records"):
        sym = str(r["symbol"]).strip()
        h = hist.get(sym)
        if h is None or "Volume" not in h:
            continue
        session = pd.to_datetime(r.get("trade_date"), errors="coerce")
        if pd.isna(session):
            session = None
        prior = _prior_volumes(h, session)
        if len(prior) < 9:
            continue
        n_scanned += 1
        vol = float(r["volume"])
        sma10 = (sum(prior) + vol) / 10.0
        if sma10 <= 0:
            continue
        mult = vol / sma10
        if mult < vol_mult:
            continue
        turnover_cr = (None if bhav.attrs.get("turnover_is_qty", False)
                       else round(float(r["turnover"]) / CRORE, 1))
        out.append({
            "symbol": sym,
            "close": round(float(r["close"]), 2),
            "chg_pct": round(float(r["chg_pct"]), 2),
            "direction": "UP" if r["chg_pct"] > 0 else "DOWN",
            "volume": int(vol),
            "sma_vol10": int(round(sma10)),
            "multiple": round(mult, 1),
            "turnover_cr": turnover_cr,
            "src": str(r.get("src") or "bhav"),
        })

    rows = pd.DataFrame(out)
    if not rows.empty:
        rows = rows.sort_values("multiple", ascending=False).head(top_n)
        rows = rows.reset_index(drop=True)
    return {"rows": rows, "n_universe": n_universe, "n_liquid": n_liquid,
            "n_price": n_price, "n_scanned": n_scanned, "n_hits": len(out),
            "vol_mult": vol_mult, "move_pct": move_pct,
            "overlay": overlay,
            "trade_date": (overlay.get("yf_date") if overlay.get("n_overlaid")
                           else overlay.get("bhav_date"))}


# ── lens 3 & 4 · range extremes ───────────────────────────────────────────────

def _batch_history(symbols: list[str], period: str = "2y") -> dict[str, pd.DataFrame]:
    """One batched yfinance call for the whole universe.

    Per-symbol `fetch_ohlcv` would be one round trip each — 200 names is a
    two-minute page load. yfinance takes a ticker list and returns a
    column-MultiIndex frame, so this is a single request.
    """
    if not symbols:
        return {}
    try:
        import yfinance as yf
    except Exception as e:
        log.warning("yfinance unavailable: %s", e)
        return {}
    tickers = [f"{s}.NS" for s in symbols]
    try:
        raw = yf.download(tickers, period=period, interval="1d",
                          progress=False, auto_adjust=True, group_by="ticker",
                          threads=True)
    except Exception as e:
        log.warning("batch history failed: %s", e)
        return {}
    if raw is None or raw.empty:
        return {}

    out: dict[str, pd.DataFrame] = {}
    for sym, tkr in zip(symbols, tickers):
        try:
            sub = raw[tkr] if isinstance(raw.columns, pd.MultiIndex) else raw
        except Exception:
            continue
        if sub is None or sub.empty:
            continue
        sub = sub.dropna(subset=["Close"])
        if len(sub) < 30:
            continue
        out[sym] = sub
    return out


def price_movers_realtime(bhav: Optional[pd.DataFrame] = None, top_n: int = TOP_N,
                          min_turnover: float = MIN_TURNOVER) -> dict[str, Any]:
    """Real-time price movers using yfinance intraday data.

    Unlike price_movers() which uses EOD bhavcopy (1 day old), this fetches today's
    intraday data from yfinance to show live % changes. Uses bhavcopy for the
    liquid universe (turnover ranking) but gets current prices from yfinance.

    Returns the same structure as price_movers() so it's a drop-in replacement.
    """
    if bhav is None:
        bhav, _ = load_bhav()
    if bhav is None or bhav.empty:
        return {"gainers": pd.DataFrame(), "losers": pd.DataFrame(),
                "n_universe": 0, "n_filtered": 0, "min_turnover": min_turnover}

    try:
        import yfinance as yf
    except Exception as e:
        log.warning("yfinance unavailable for realtime movers: %s", e)
        # Fall back to bhavcopy movers if yfinance isn't available
        return price_movers(bhav, top_n=top_n, min_turnover=min_turnover)

    # Get the liquid universe from bhavcopy (for turnover ranking)
    uni = liquid_universe(bhav, UNIVERSE_N)
    if not uni:
        return {"gainers": pd.DataFrame(), "losers": pd.DataFrame(),
                "n_universe": 0, "n_filtered": 0, "min_turnover": min_turnover}

    # Fetch today's intraday data from yfinance (1d period with 5m interval)
    tickers = [f"{s}.NS" for s in uni]
    try:
        raw = yf.download(tickers, period="1d", interval="5m",
                          progress=False, auto_adjust=True, group_by="ticker",
                          threads=True)
    except Exception as e:
        log.warning("yfinance realtime fetch failed: %s — falling back to bhavcopy", e)
        return price_movers(bhav, top_n=top_n, min_turnover=min_turnover)

    if raw is None or raw.empty:
        log.warning("yfinance returned no data for realtime movers — falling back to bhavcopy")
        return price_movers(bhav, top_n=top_n, min_turnover=min_turnover)

    # Extract latest intraday data for each symbol
    rows = []
    n_universe = len(uni)

    for sym, tkr in zip(uni, tickers):
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                sub = raw[tkr]
            else:
                sub = raw

            if sub is None or sub.empty or "Close" not in sub.columns:
                continue

            # Get the latest close and the opening/previous price from this intraday session
            closes = pd.to_numeric(sub["Close"], errors="coerce").dropna()
            if len(closes) < 1:
                continue

            curr_close = float(closes.iloc[-1])
            if curr_close <= 0:
                continue

            # Use the first intraday close as reference (or first valid close from history)
            # If we only have one candle, we can't compute intraday change, so skip
            if len(closes) < 2:
                # Try to get prev_close from bhavcopy as fallback
                bhav_row = bhav[bhav["symbol"] == sym]
                if bhav_row.empty:
                    continue
                prev_close = pd.to_numeric(bhav_row["prev_close"].iloc[0], errors="coerce")
            else:
                prev_close = float(closes.iloc[0])

            if prev_close <= 0:
                continue

            chg = curr_close - prev_close
            chg_pct = (chg / prev_close) * 100.0

            # Get turnover from bhavcopy for ranking
            bhav_row = bhav[bhav["symbol"] == sym]
            if bhav_row.empty:
                turnover = 0.0
                volume = 0
            else:
                turnover = pd.to_numeric(bhav_row["turnover"].iloc[0], errors="coerce") or 0.0
                volume = pd.to_numeric(bhav_row["volume"].iloc[0], errors="coerce") or 0

            rows.append({
                "symbol": sym,
                "close": curr_close,
                "chg": chg,
                "chg_pct": chg_pct,
                "turnover": turnover,
                "volume": volume,
            })
        except Exception as e:
            log.debug("error processing realtime data for %s: %s", sym, e)
            continue

    if not rows:
        log.warning("no valid realtime data extracted — falling back to bhavcopy")
        return price_movers(bhav, top_n=top_n, min_turnover=min_turnover)

    d = pd.DataFrame(rows)
    n_filtered = len(d)

    # Apply liquidity filter
    if not bhav.attrs.get("turnover_is_qty", False):
        d = d[d["turnover"] >= min_turnover]

    cols = ["symbol", "close", "chg", "chg_pct", "turnover", "volume"]
    d = d[cols]

    return {
        "gainers": d.nlargest(top_n, "chg_pct").reset_index(drop=True),
        "losers": d.nsmallest(top_n, "chg_pct").reset_index(drop=True),
        "n_universe": n_universe,
        "n_filtered": len(d),
        "min_turnover": min_turnover,
        "turnover_is_qty": bool(bhav.attrs.get("turnover_is_qty", False)),
        "source": "yfinance_realtime",
    }


def is_liquid_etf(df: pd.DataFrame) -> bool:
    """Cash-equivalent instrument check — same definition as the chart's
    `isLikelyLiquidETF` (chart_dashboard.html), deliberately not a second one.

    Median daily |return| < 0.05% and worst < 0.5%: a money-market / liquid ETF
    accrues instead of trading. This matters here more than anywhere else in the
    repo, because such an instrument is *permanently* at its all-time high by
    construction — LIQUIDCASE topped the first ATH run — and would squat on the
    list forever while telling you nothing.
    """
    if df is None or len(df) < 60:
        return False
    c = pd.to_numeric(df["Close"], errors="coerce").dropna()
    if len(c) < 60:
        return False
    rets = (c.pct_change().abs() * 100).dropna()
    if len(rets) < 60:
        return False
    return bool(rets.median() < 0.05 and rets.max() < 0.5)


def range_extremes(symbols: list[str], window: Optional[int] = WEEK52_BARS,
                   near_pct: float = NEAR_PCT, top_n: int = TOP_N,
                   hist: Optional[dict[str, pd.DataFrame]] = None,
                   drop_cash_equivalents: bool = True) -> dict[str, Any]:
    """Names at or near their range high / low.

    `window` is the lookback in trading days; None means the full downloaded
    history (the all-time lens, bounded by what yfinance serves).

    Ranking is by how CLOSE the last price sits to the extreme, not by the size
    of the move, because the question this lens answers is "who is at their
    high", not "who rose most" — that is the Price Movers lens and duplicating
    it here would make two tabs show the same list.
    """
    if hist is None:
        hist = _batch_history(symbols, period="2y" if window else "max")
    rows = []
    n_cash = 0
    for sym, df in hist.items():
        if drop_cash_equivalents and is_liquid_etf(df):
            n_cash += 1
            continue
        d = df if not window else df.tail(window)
        if d.empty:
            continue
        close = float(d["Close"].iloc[-1])
        hi = float(d["High"].max())
        lo = float(d["Low"].min())
        if not (close > 0 and hi > 0 and lo > 0) or hi <= lo:
            continue
        rows.append({
            "symbol": sym,
            "close": round(close, 2),
            "range_high": round(hi, 2),
            "range_low": round(lo, 2),
            "from_high_pct": round((close - hi) / hi * 100, 2),   # <= 0
            "from_low_pct": round((close - lo) / lo * 100, 2),    # >= 0
            "bars": int(len(d)),
        })
    if not rows:
        return {"highs": pd.DataFrame(), "lows": pd.DataFrame(),
                "n_scanned": 0, "near_pct": near_pct, "n_cash_equivalents": n_cash}

    df = pd.DataFrame(rows)
    highs = (df[df["from_high_pct"] >= -near_pct]
             .sort_values("from_high_pct", ascending=False).head(top_n))
    lows = (df[df["from_low_pct"] <= near_pct]
            .sort_values("from_low_pct").head(top_n))
    return {
        "highs": highs.reset_index(drop=True),
        "lows": lows.reset_index(drop=True),
        "n_scanned": len(df),
        "near_pct": near_pct,
        "window": window,
        "n_cash_equivalents": n_cash,
    }


def trending(universe_n: int = UNIVERSE_N, top_n: int = TOP_N,
             lenses: tuple[str, ...] = ("movers", "volume", "52w", "ath")
             ) -> dict[str, Any]:
    """All four lenses off ONE bhavcopy download and ONE batched history call."""
    bhav, date = load_bhav()
    out: dict[str, Any] = {"trade_date": date, "universe_n": universe_n,
                           "top_n": top_n}
    if bhav is None:
        out["error"] = "no bhavcopy reachable"
        return out

    if "movers" in lenses:
        out["movers"] = price_movers(bhav, top_n=top_n)
    if "volume" in lenses:
        out["volume"] = volume_shockers(top_n=top_n, bhav=bhav)

    if "52w" in lenses or "ath" in lenses:
        uni = liquid_universe(bhav, universe_n)
        out["universe"] = uni
        # "max" covers both lenses from a single download; the 52-week view is
        # just its last 252 bars. Two downloads would be two minutes for nothing.
        hist = _batch_history(uni, period="max")
        out["n_history"] = len(hist)
        if "52w" in lenses:
            out["week52"] = range_extremes(uni, window=WEEK52_BARS,
                                           top_n=top_n, hist=hist)
        if "ath" in lenses:
            out["alltime"] = range_extremes(uni, window=None,
                                            top_n=top_n, hist=hist)
    return out


# ── reporting ─────────────────────────────────────────────────────────────────

def _fmt_table(df: pd.DataFrame, cols: list[tuple[str, str]]) -> str:
    """Fixed-width table sized to its CONTENT — a long categorical value like
    CORPORATE_ACTION overflows any hard-coded column width and silently welds
    itself to the number beside it."""
    if df is None or df.empty:
        return "    (none)"

    def cell(v):
        return (f"{v:,.2f}" if isinstance(v, (int, float, np.floating))
                and not isinstance(v, bool) else str(v))

    widths = []
    for key, lbl in cols:
        w = len(lbl)
        for _, r in df.iterrows():
            w = max(w, len(cell(r.get(key))))
        widths.append(w + 2)

    lines = ["    " + "".join(f"{lbl:>{w}}" for (_, lbl), w in zip(cols, widths))]
    lines.append("    " + "-" * sum(widths))
    for _, r in df.iterrows():
        lines.append("    " + "".join(f"{cell(r.get(k)):>{w}}"
                                      for (k, _), w in zip(cols, widths)))
    return "\n".join(lines)


def format_trending(res: dict[str, Any]) -> str:
    if res.get("error"):
        return f"ERROR: {res['error']}"
    L = [f"Trending Stocks — session {res.get('trade_date') or '?'}", ""]

    m = res.get("movers")
    if m:
        L += [f"PRICE MOVERS  (turnover ≥ ₹{m['min_turnover']/CRORE:.0f} Cr — "
              f"{m['n_filtered']} of {m['n_universe']} names clear it)", "",
              "  Gainers", _fmt_table(m["gainers"],
                  [("symbol", "Symbol"), ("close", "LTP"), ("chg", "Chg"), ("chg_pct", "Chg%")]),
              "", "  Losers", _fmt_table(m["losers"],
                  [("symbol", "Symbol"), ("close", "LTP"), ("chg", "Chg"), ("chg_pct", "Chg%")]), ""]

    v = res.get("volume")
    if v:
        if v.get("error"):
            L += [f"VOLUME SHOCKERS  unavailable ({v['error']})", ""]
        else:
            rows = v["rows"]
            tally = v.get("tally") or {}
            tally_s = "  ".join(f"{k.replace('_', ' ').lower()} {n}"
                                for k, n in tally.items() if n)
            L += [f"VOLUME SHOCKERS  ({v.get('n_hits', len(rows))} spikes"
                  + (f" — {tally_s}" if tally_s else "") + ")", ""]
            if rows.empty:
                L += ["    (none)", ""]
            else:
                L += [_fmt_table(rows,
                        [("symbol", "Symbol"), ("close", "LTP"),
                         ("multiple", "x avg vol"), ("day_pct", "Chg%"),
                         ("cause", "Cause")]), ""]

    for key, label in (("week52", "52-WEEK HIGH / LOW"), ("alltime", "ALL-TIME HIGH / LOW")):
        r = res.get(key)
        if not r:
            continue
        L += [f"{label}  ({r['n_scanned']} of top {res['universe_n']} by turnover, "
              f"within {r['near_pct']}% of the extreme)", "",
              "  At/near highs", _fmt_table(r["highs"],
                  [("symbol", "Symbol"), ("close", "LTP"),
                   ("range_high", "High"), ("from_high_pct", "From hi%")]),
              "", "  At/near lows", _fmt_table(r["lows"],
                  [("symbol", "Symbol"), ("close", "LTP"),
                   ("range_low", "Low"), ("from_low_pct", "From lo%")]), ""]

    L += ["  ⚠ Attention lists, not signals. A move or a spike is a QUESTION",
          "    ('why did this happen?'), not a position. No Most-Visited lens:",
          "    crowd page-view data has no free feed and a proxy would measure",
          "    something else under the same name."]
    return "\n".join(L)


def main() -> None:
    import argparse, io, sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    logging.basicConfig(level=logging.WARNING)

    ap = argparse.ArgumentParser(description="Trending stocks — four lenses")
    ap.add_argument("--lens", default="all",
                    choices=["all", "movers", "volume", "52w", "ath"])
    ap.add_argument("--universe", type=int, default=UNIVERSE_N)
    ap.add_argument("--top", type=int, default=TOP_N)
    a = ap.parse_args()

    lenses = (("movers", "volume", "52w", "ath") if a.lens == "all" else (a.lens,))
    res = trending(universe_n=a.universe, top_n=a.top, lenses=lenses)
    print(format_trending(res))


if __name__ == "__main__":
    main()
