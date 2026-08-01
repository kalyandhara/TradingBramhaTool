#!/usr/bin/env python3
"""
opportunity_daily.py — the Opportunity Hub, run headlessly once a day.

Why this exists
---------------
The interactive Hub is a five-step funnel: pick a universe, build it, choose
leading sectors, choose leading industries, pick ONE of 24 scanners, then scan.
It is powerful and almost impossible to run the same way twice — and nothing
persists, so every session starts from an empty screen and yesterday's shortlist
is gone. This module makes the same funnel a single unattended run that ends in
a stored top-N list, so the question becomes "what did the funnel like today"
instead of "which of 24 scanners should I try".

The funnel, unchanged
---------------------
    universe -> momentum + sector/industry tags   (opportunity_hub)
             -> leading sectors                   (rank_groups)
             -> leading industries within them    (rank_groups)
             -> scanners over ONLY those stocks   (scanner_templates)
             -> rank, keep the top N, store       (portfolio_db)

What "really an opportunity" means here
---------------------------------------
Three things have to agree, and the ranking says so explicitly:

1. **Location** — the stock sits in a leading sector AND a leading industry.
   That is the Hub's whole thesis and it is a hard filter, not a bonus.
2. **Confluence** — more than one scanner fired on it. A single pattern is a
   suggestion; two independent ones on the same chart is a reason to look.
3. **Quality** — the M1 Overall Rating, computed with the SAME code the
   interactive Hub uses (rating.py), not a second implementation.

Scanners are NOT weighted equally. The backtest harness measured most of them,
and only a few beat a random-entry baseline (see wiki/analyses/Backtest-Harness):
Falling Wedge and Harmonic Reversal beat it, Order Block showed +0.11R, while
RSI-60-40, VCP and Structural Breakout came in at or below zero edge. So a hit
from a measured-edge scanner counts double. Treating all 24 alike would have let
the ones we *measured as worthless* outvote the ones that worked.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import screener_pipeline as sp
import scanner_templates as sc
import opportunity_hub as oh
import portfolio_db as db
import rating

#: Scanners with measured forward edge vs a random-entry baseline. A hit here
#: is worth a full point.
MEASURED_EDGE_SCANNERS = (
    "Falling Wedge",
    "Harmonic Reversal (XABCD)",
    "Order Block Retest",
)

#: Unmeasured or weakly-measured scanners, kept for coverage so a quiet day
#: still surfaces something — but worth half a point, and labelled as such.
SUPPORTING_SCANNERS = (
    "Stage 2 Uptrend",
    "Momentum Continuation",
    "52-Week High Leaders",
    "VCP Coiling",
    "Near Pivot",
    "ATH Breakout (all-time high)",
)

EDGE_POINT = 1.0
SUPPORT_POINT = 0.5
#: Edge-points that count as full confluence marks. Two measured hits, or one
#: measured plus two supporting.
FULL_CONFLUENCE = 2.0

#: Final score weights. Quality leads, but neither quality nor a single strong
#: pattern can carry a stock on its own.
W_RATING, W_SCANNER, W_CONFLUENCE = 0.45, 0.30, 0.25


class _FrameCache:
    """Fetch each symbol once and reuse it across every scanner and the rating.

    Without this the same 60-odd frames would be pulled once per scanner — nine
    times over — which is both slow and a good way to get rate-limited.
    """

    def __init__(self, days: int = 400):
        self._days = days
        self._cache: dict[str, pd.DataFrame | None] = {}
        self.misses = 0

    def __call__(self, symbol: str):
        if symbol not in self._cache:
            self.misses += 1
            try:
                df = sp.fetch_ohlcv(symbol, days=self._days)
            except Exception:
                df = None
            # Same forming-bar discipline as the dashboard: a NaN last close
            # silently fails every comparison downstream.
            if df is not None and "close" in getattr(df, "columns", []):
                df = df[df["close"].notna()]
                if df.empty:
                    df = None
            self._cache[symbol] = df
        return self._cache[symbol]


#: Fraction of the universe that must get a sector tag for the run to be
#: trustworthy. Below this the sector ranking is being computed from whichever
#: names happened to survive, which is not the same market.
_MIN_TAG_RATE = 0.35


def _tag_with_retry(universe: list[str], fetch, max_workers: int, say) -> pd.DataFrame:
    """Tag the universe, retrying once, gently, if Yahoo throttled the burst.

    `build_constituent_table` fans out `.info` calls across a thread pool. At 8
    workers over a few hundred symbols Yahoo starts answering HTTP 401 ("Invalid
    Crumb"), and because every failure is swallowed per-symbol the result is not
    an error — it is an empty or half-empty table that would quietly produce a
    sector ranking derived from whatever survived. An unattended job has nobody
    to notice that, so it retries with a smaller pool and reports the tag rate.
    """
    import time

    table = oh.build_constituent_table(universe, fetch, max_workers=max_workers)
    rate = (len(table) / len(universe)) if len(universe) else 0
    if rate >= _MIN_TAG_RATE:
        say(f"Tagged {len(table)}/{len(universe)} ({rate:.0%}).")
        return table

    say(f"Only {len(table)}/{len(universe)} tagged ({rate:.0%}) — Yahoo likely "
        f"throttled the burst. Pausing 45s and retrying with 2 workers…")
    time.sleep(45)
    retry = oh.build_constituent_table(universe, fetch, max_workers=2)
    if len(retry) > len(table):
        table = retry
    rate = (len(table) / len(universe)) if len(universe) else 0
    say(f"After retry: {len(table)}/{len(universe)} tagged ({rate:.0%}).")
    return table


def _market_context(nifty_df) -> dict[str, str]:
    """A plain description of the tape, stored beside every shortlist.

    A shortlist produced on a day the index sits under its 200 SMA is not the same
    artifact as one produced in a healthy tape, and six months later nobody will
    remember which was which unless it is written down with the rows.
    """
    if nifty_df is None or len(nifty_df) < 200:
        return {"regime": "UNKNOWN", "verdict": "Benchmark unavailable — regime not assessed."}
    close = nifty_df["close"]
    last = float(close.iloc[-1])
    sma200 = float(close.rolling(200).mean().iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1])
    dist = (last / sma200 - 1) * 100
    if last > sma200 and last > sma50:
        regime = "RISK-ON"
        verdict = (f"Nifty {last:,.0f} above both its 50 and 200 SMA "
                   f"({dist:+.1f}% vs 200) — trend-following setups have a tailwind.")
    elif last < sma200:
        regime = "RISK-OFF"
        verdict = (f"Nifty {last:,.0f} BELOW its 200 SMA ({dist:+.1f}%) — breakouts "
                   f"follow through less often here. Treat this list as a watchlist, "
                   f"not a buy list.")
    else:
        regime = "MIXED"
        verdict = (f"Nifty {last:,.0f} above its 200 SMA ({dist:+.1f}%) but under the "
                   f"50 — an uptrend in a pullback.")
    return {"regime": regime, "verdict": verdict}


def run(universe_size: int = 200, top_n: int = 100,
        scanners: list[str] | None = None,
        max_sectors: int = 3, min_constituents: int = 3,
        save: bool = True, run_date: str | None = None,
        max_workers: int = 4, progress_cb=None) -> dict:
    """Run the whole funnel and return (and optionally store) the shortlist."""
    run_date = run_date or date.today().isoformat()

    def _say(msg: str):
        if progress_cb:
            progress_cb(msg)

    wanted = list(scanners) if scanners else list(MEASURED_EDGE_SCANNERS) + list(SUPPORTING_SCANNERS)
    # Scanner names carry en-dashes and parentheses; drop anything that is not
    # actually registered rather than failing the whole run on a typo.
    use_scanners = [s for s in wanted if s in sc.SCANNERS]
    dropped = [s for s in wanted if s not in sc.SCANNERS]

    _say(f"Loading top {universe_size} symbols by traded value…")
    universe = sp.fetch_bhavcopy_top_volume(universe_size)
    if not universe:
        return {"ok": False, "reason": "bhavcopy universe empty", "run_date": run_date}

    fetch = _FrameCache()
    try:
        nifty_df = sp.fetch_nifty50(days=400)
        if nifty_df is not None and "close" in nifty_df.columns:
            nifty_df = nifty_df[nifty_df["close"].notna()]
    except Exception:
        nifty_df = None
    market = _market_context(nifty_df)

    _say(f"Tagging sector/industry + momentum for {len(universe)} symbols…")
    table = _tag_with_retry(universe, fetch, max_workers, _say)
    if table is None or table.empty:
        return {"ok": False, "run_date": run_date,
                "reason": ("no stocks could be tagged — yfinance returned no sector "
                           "data for the whole universe, usually rate-limiting "
                           "(HTTP 401 'Invalid Crumb'). Re-run later.")}

    _say("Ranking sectors…")
    sectors = oh.rank_groups(table, "sector", min_constituents=min_constituents)
    if sectors.empty:
        return {"ok": False, "reason": "no sector had enough constituents",
                "run_date": run_date}
    lead_sectors = sectors[sectors["avg_momentum"] > 0]["sector"].head(max_sectors).tolist()
    if not lead_sectors:
        # Nothing is going up. Say so rather than quietly ranking the least-bad.
        lead_sectors = sectors["sector"].head(max_sectors).tolist()
        market["verdict"] += (" No sector has positive average momentum today, so the "
                              "'leading' sectors below are merely the least weak.")

    sub = table[table["sector"].isin(lead_sectors)]
    industries = oh.rank_groups(sub, "industry", min_constituents=1)
    lead_inds = (industries[industries["avg_momentum"] > 0]["industry"].tolist()
                 or industries["industry"].tolist())
    stocks = oh.stocks_in_groups(sub, "industry", lead_inds)
    _say(f"{len(stocks)} stocks in {len(lead_sectors)} leading sectors / "
         f"{len(lead_inds)} industries.")
    if not stocks:
        return {"ok": False, "reason": "no stocks in the leading groups",
                "run_date": run_date}

    # ── Scanners over the leaders only ────────────────────────────────────────
    hits: dict[str, dict] = {}
    for name in use_scanners:
        _say(f"Scanning: {name}…")
        try:
            results = sc.run_scanner(name, stocks, fetch, benchmark_df=nifty_df)
        except Exception:
            continue
        weight = EDGE_POINT if name in MEASURED_EDGE_SCANNERS else SUPPORT_POINT
        for card in results:
            sym = card.get("symbol")
            if not sym:
                continue
            h = hits.setdefault(sym, {"symbol": sym, "scanners": [], "edge_points": 0.0,
                                      "best_score": 0.0, "best_card": None})
            h["scanners"].append(name)
            h["edge_points"] += weight
            if (card.get("score") or 0) >= h["best_score"]:
                h["best_score"] = float(card.get("score") or 0)
                h["best_card"] = card

    if not hits:
        return {"ok": True, "run_date": run_date, "rows": [], "market": market,
                "universe_size": len(universe), "candidates": len(stocks),
                "scanners_used": use_scanners, "scanners_dropped": dropped,
                "reason": "no scanner fired on any leading-industry stock"}

    # ── Rank ──────────────────────────────────────────────────────────────────
    _say(f"Rating {len(hits)} candidates…")
    tags = table.set_index("symbol") if "symbol" in table.columns else None
    rows = []
    for sym, h in hits.items():
        df = fetch(sym)
        if df is None or df.empty:
            continue
        rating_val, _breakdown = rating.overall_rating(df, nifty_df)
        confluence_pct = min(h["edge_points"] / FULL_CONFLUENCE, 1.0) * 100
        score = (W_RATING * (rating_val or 0)
                 + W_SCANNER * min(h["best_score"], 100)
                 + W_CONFLUENCE * confluence_pct)
        card = h["best_card"] or {}
        row = tags.loc[sym] if (tags is not None and sym in tags.index) else None
        rows.append({
            "symbol": sym,
            "score": round(score, 1),
            "overall_rating": rating_val,
            "confluence": len(h["scanners"]),
            "edge_points": h["edge_points"],
            "scanners": ", ".join(h["scanners"]),
            "sector": (row["sector"] if row is not None else None),
            "industry": (row["industry"] if row is not None else None),
            "momentum": (float(row["momentum"]) if row is not None
                         and pd.notna(row.get("momentum")) else None),
            "close": float(df["close"].iloc[-1]),
            "entry": card.get("entry"),
            "stop": card.get("stop"),
            "target": card.get("target"),
            "market_regime": market["regime"],
            "market_verdict": market["verdict"],
            "universe_size": len(universe),
            "notes": _explain(h, rating_val, row),
        })

    rows.sort(key=lambda r: r["score"], reverse=True)
    rows = rows[:top_n]
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    if save and rows:
        db.save_daily_opportunities(rows, run_date=run_date)
        _say(f"Stored {len(rows)} rows for {run_date}.")

    return {"ok": True, "run_date": run_date, "rows": rows, "market": market,
            "universe_size": len(universe), "candidates": len(stocks),
            "lead_sectors": lead_sectors, "lead_industries": lead_inds,
            "scanners_used": use_scanners, "scanners_dropped": dropped,
            "fetches": fetch.misses}


def _explain(hit: dict, rating_val: int | None, row) -> str:
    """One plain sentence saying why this name is on the list."""
    n = len(hit["scanners"])
    measured = [s for s in hit["scanners"] if s in MEASURED_EDGE_SCANNERS]
    bits = [f"{n} scanner{'s' if n != 1 else ''} fired ({', '.join(hit['scanners'])})"]
    if measured:
        bits.append(f"including {len(measured)} with measured backtest edge")
    else:
        bits.append("none of them backtest-measured, so treat as a lead, not a signal")
    if rating_val is not None:
        bits.append(f"Overall Rating {rating_val}/100")
    if row is not None:
        bits.append(f"in {row['industry']} ({row['sector']}), a leading group today")
    return "; ".join(bits) + "."


def main() -> int:
    ap = argparse.ArgumentParser(description="Daily Opportunity Hub shortlist")
    ap.add_argument("--universe", type=int, default=200,
                    help="top N symbols by traded value (default 200)")
    ap.add_argument("--top", type=int, default=100, help="rows to store (default 100)")
    ap.add_argument("--sectors", type=int, default=3, help="leading sectors to drill")
    ap.add_argument("--no-save", action="store_true", help="print without storing")
    ap.add_argument("--date", default=None, help="run date override (YYYY-MM-DD)")
    args = ap.parse_args()

    res = run(universe_size=args.universe, top_n=args.top, max_sectors=args.sectors,
              save=not args.no_save, run_date=args.date,
              progress_cb=lambda m: print(f"  … {m}", flush=True))

    if not res.get("ok"):
        print(f"FAILED: {res.get('reason')}")
        return 1
    m = res["market"]
    print(f"\nRun {res['run_date']} · universe {res['universe_size']} · "
          f"{res['candidates']} candidates in leading groups · {res.get('fetches')} fetches")
    print(f"Market: {m['regime']} — {m['verdict']}")
    if res.get("scanners_dropped"):
        print(f"Unknown scanner names skipped: {res['scanners_dropped']}")
    if not res["rows"]:
        print(f"\nNo shortlist: {res.get('reason')}")
        return 0
    print(f"\n{'#':<3}{'SYMBOL':<14}{'SCORE':>6}{'RATING':>7}{'CONF':>5}  SCANNERS")
    for r in res["rows"]:
        print(f"{r['rank']:<3}{r['symbol']:<14}{r['score']:>6.1f}"
              f"{str(r['overall_rating']):>7}{r['confluence']:>5}  {r['scanners']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
