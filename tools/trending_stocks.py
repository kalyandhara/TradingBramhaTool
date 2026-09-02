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
                    bhav: Optional[pd.DataFrame] = None) -> dict[str, Any]:
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
                "trade_date": res.get("trade_date"), "raw": res}
    df = pd.DataFrame(rows)
    # scan() ranks by spike multiple already; keep that order, just cap it.
    return {"rows": df.head(top_n).reset_index(drop=True),
            "tally": res.get("tally"),
            "n_hits": res.get("hits"),
            "universe": res.get("universe"),
            "trade_date": res.get("trade_date"),
            "raw": res}


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
