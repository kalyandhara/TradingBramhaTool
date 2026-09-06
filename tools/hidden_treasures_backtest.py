"""B-34 hit-rate study — does the Hidden Treasures ranking beat the universe?

Re-scores the small/micro-cap universe at each historical quarter boundary using
only ownership data available at that date, picks the top N, and measures their
forward returns vs the equal-weight universe baseline.

The question: do names ranked highly by institutional conviction (FII+DII
accumulation, promoter conduct, pledge) outperform a random small-cap name
forward?  If stacking the score doesn't beat the baseline, the ranking is
ceremony.

Method
------
For each eval quarter Q where ≥2 prior quarters of ownership data exist:
  1. Filter each symbol's cached quarters to those with period_date ≤ Q.
  2. Score using smallcap_discovery's logic (inst_delta, promoter, pledge).
  3. Quality-enrich if requested (ROCE/OPM/D/E bonus — same as the live page).
  4. Pick top N by score.
  5. Fetch OHLCV for all symbols via yfinance (cached in memory).
  6. Entry = first trading day after the quarter's filing date (~45 days after
     quarter end for NSE).  Exit = entry + horizon days.
  7. Forward return = (close[entry+h] / close[entry] - 1) × 100.
  8. Baseline = equal-weight average forward return of ALL scored names (not
     just the top N) — the "random pick from the same universe" benchmark.

Reports edge = mean(top N fwd) − mean(baseline fwd) per horizon, with a Welch
two-sample t-test (scipy-optional, numpy normal-approx fallback).

Usage:
    py -3 tools/hidden_treasures_backtest.py
    py -3 tools/hidden_treasures_backtest.py --top 15 --kind smallcap250
    py -3 tools/hidden_treasures_backtest.py --enrich   # with quality overlay
"""
from __future__ import annotations

import math
import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

import smallcap_discovery as scd
import smallcap_universe as scu
import ownership_cache as oc
import nse_shareholding_fetch as nsf
import screener_pipeline as sp

try:
    from scipy import stats as _stats
except Exception:
    _stats = None

log = logging.getLogger(__name__)

DEFAULT_HORIZONS = (60, 120)
FILING_LAG_DAYS = 50
MIN_QUARTERS_FOR_SCORE = 2


def _period_date(s: str) -> Optional[datetime]:
    return nsf._period_date(s)


def _score_at_quarter(symbol: str, eval_date: datetime,
                      enrich: bool = False) -> Optional[dict]:
    """Score a symbol using only ownership quarters with period_date ≤ eval_date."""
    data = oc.load(symbol)
    all_qs = data.get("quarters") or {}

    filtered = {}
    for period, legs in all_qs.items():
        pd_ = _period_date(period)
        if pd_ is not None and pd_ <= eval_date:
            filtered[period] = legs

    if len(filtered) < MIN_QUARTERS_FOR_SCORE:
        return None

    fake_data = {"symbol": symbol, "quarters": filtered}
    ordered = scd._ordered_quarters(fake_data)
    if len(ordered) < 2:
        return None

    (p_old, v_old), (p_new, v_new) = ordered[0], ordered[-1]

    def _n(v):
        return float(v) if isinstance(v, (int, float)) else None

    fii_new, dii_new = _n(v_new.get("fii")), _n(v_new.get("dii"))
    fii_old, dii_old = _n(v_old.get("fii")), _n(v_old.get("dii"))
    prom_new, prom_old = _n(v_new.get("promoter")), _n(v_old.get("promoter"))
    pledge = _n(v_new.get("promoter_pledge_pct"))

    inst_new = sum(x for x in (fii_new, dii_new) if x is not None)
    inst_old = sum(x for x in (fii_old, dii_old) if x is not None)
    inst_delta = round(inst_new - inst_old, 2)
    prom_delta = (round(prom_new - prom_old, 2)
                  if prom_new is not None and prom_old is not None else None)

    score = 40.0
    rate = inst_delta / max(1, len(ordered) - 1)
    score += max(-6.0, min(6.0, rate)) * 5
    if prom_delta is not None:
        if prom_delta <= -scd.PROMOTER_SELL_PP:
            score -= 15
        elif prom_delta >= -0.5:
            score += 10
    pledge_flag = pledge is not None and pledge > scd.PLEDGE_MAX
    if pledge_flag:
        score -= 20

    # ── B-34r2: the veto, recomputed POINT-IN-TIME ───────────────────────────
    # Only the two governance criticals can be tested honestly here, and they
    # are tested from the SAME filtered quarters the score uses - no new data,
    # no future information. Thresholds are red_flags' own, not re-picked.
    #
    # Negative FCF and dilution are deliberately NOT applied: `fcf_history` and
    # `shares_history` come back from yfinance as bare value lists with NO year
    # labels, so there is no way to truncate them to "as known at Q". Applying
    # today's FCF streak to a 2024 entry would be vetoing a pick for something
    # that had not happened yet, and would make the whole comparison a
    # hindsight exercise. See the report footer.
    import red_flags as _rf
    # B-34r3: the veto's promoter comparison is BOUNDED to a trailing window,
    # matching red_flags._check_promoter_holding_nse. Using the full filtered
    # history here made the veto rate climb 3% -> 28% across the sample purely
    # because later quarters had more history behind them, which is drift in the
    # measuring instrument rather than in the companies.
    _win = ordered[-_rf._PROMOTER_WINDOW_Q:]
    _pw_old, _pw_new = _n(_win[0][1].get("promoter")), _n(_win[-1][1].get("promoter"))
    prom_delta_win = (round(_pw_new - _pw_old, 2)
                      if _pw_new is not None and _pw_old is not None else None)
    prom_veto = prom_delta_win is not None and prom_delta_win <= -_rf._PROMOTER_DROP_PP
    pledge_veto = pledge is not None and pledge > _rf._PLEDGE_PCT_MAX

    hit = {
        "symbol": symbol,
        "score": round(max(0.0, min(100.0, score)), 1),
        "inst_delta": inst_delta,
        "promoter_delta": prom_delta,
        "pledge_pct": pledge,
        "pledge_flag": pledge_flag,
        "gov_veto": bool(prom_veto or pledge_veto),
        "prom_delta_win": prom_delta_win,
        "gov_veto_why": ([f"promoter {prom_delta_win:+.2f}pp/"
                          f"{len(_win)}q"] if prom_veto else [])
                        + ([f"pledge {pledge:.1f}%"] if pledge_veto else []),
    }

    if enrich:
        scd._enrich_quality(hit)

    return hit


def _welch_p(sig: list[float], base: list[float]) -> Optional[float]:
    a = np.asarray(sig, float)
    b = np.asarray(base, float)
    if len(a) < 4 or len(b) < 4:
        return None
    va, vb = a.var(ddof=1), b.var(ddof=1)
    na, nb = len(a), len(b)
    se2 = va / na + vb / nb
    if se2 <= 0:
        return None
    tstat = (a.mean() - b.mean()) / math.sqrt(se2)
    if _stats is not None:
        df = se2 ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
        return float(2.0 * _stats.t.sf(abs(tstat), df))
    return float(math.erfc(abs(tstat) / math.sqrt(2.0)))


def _fetch_and_cache(symbols: list[str], days: int = 2000) -> dict[str, pd.DataFrame]:
    cache = {}
    for i, sym in enumerate(symbols, 1):
        if i % 25 == 0:
            print(f"  …fetching OHLCV {i}/{len(symbols)}", flush=True)
        try:
            df = sp.fetch_ohlcv(sym, days=days)
            if df is not None and not df.empty:
                cache[sym] = df
        except Exception:
            pass
    return cache


def _fwd_return(df: pd.DataFrame, entry_date: datetime,
                horizon: int) -> Optional[float]:
    """Forward return (%) from the first bar on or after entry_date."""
    if df is None or df.empty:
        return None
    mask = df.index >= pd.Timestamp(entry_date)
    sub = df.loc[mask]
    if len(sub) < horizon + 1:
        return None
    entry_price = float(sub.iloc[0]["close"])
    exit_price = float(sub.iloc[horizon]["close"])
    if entry_price <= 0:
        return None
    return (exit_price / entry_price - 1.0) * 100.0


def backtest_hidden_treasures(
    kind: str = "both",
    top_n: int = 25,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    enrich: bool = False,
    gov_veto: bool = False,
) -> dict:
    """Run the hit-rate study. Returns a structured result dict.

    `gov_veto` (B-34r2) drops names carrying a point-in-time governance red flag
    BEFORE the top-N cut, so the comparison is "same ranking, smaller pool".
    The BASELINE is left untouched on purpose: the question is whether vetoing
    improves the picks, not whether it improves the universe average.
    """

    # 1. Get universe and find all unique quarter boundaries from cache
    uni = scu.fetch_universe(kind)
    symbols = [e["symbol"] for e in uni]
    print(f"Universe: {len(symbols)} symbols ({kind})")

    all_quarters: set[str] = set()
    for sym in symbols:
        data = oc.load(sym)
        for period in (data.get("quarters") or {}):
            all_quarters.add(period)

    quarter_dates = []
    for q in all_quarters:
        d = _period_date(q)
        if d is not None:
            quarter_dates.append((q, d))
    quarter_dates.sort(key=lambda x: x[1])

    # Need at least 2 quarters of history before we can score, plus forward room
    if len(quarter_dates) < 3:
        return {"error": "Too few quarters in cache to backtest"}

    # Skip the first quarter (need ≥2 for scoring) and the last (need forward room)
    eval_quarters = quarter_dates[1:-1]
    print(f"Eval quarters: {len(eval_quarters)} "
          f"({eval_quarters[0][0]} … {eval_quarters[-1][0]})")

    # 2. Fetch OHLCV for all symbols
    print("Fetching OHLCV…")
    ohlcv = _fetch_and_cache(symbols)
    print(f"  {len(ohlcv)} symbols with price data")

    max_h = max(horizons)

    # 3. For each eval quarter, score → pick top N → measure forward returns
    per_quarter = []
    top_fwd: dict[int, list[float]] = {h: [] for h in horizons}
    base_fwd: dict[int, list[float]] = {h: [] for h in horizons}

    for q_label, q_date in eval_quarters:
        entry_date = q_date + timedelta(days=FILING_LAG_DAYS)

        # Score all symbols at this quarter
        scored = []
        for sym in symbols:
            s = _score_at_quarter(sym, q_date, enrich=False)
            if s is not None and sym in ohlcv:
                s["_fwd"] = {}
                has_any = False
                for h in horizons:
                    r = _fwd_return(ohlcv[sym], entry_date, h)
                    s["_fwd"][h] = r
                    if r is not None:
                        has_any = True
                if has_any:
                    scored.append(s)

        if len(scored) < top_n + 5:
            continue

        scored.sort(key=lambda x: x["score"], reverse=True)
        eligible = [x for x in scored if not x["gov_veto"]] if gov_veto else scored
        n_vetoed = len(scored) - len(eligible)
        if len(eligible) < top_n:
            # Not enough survivors to fill the same-sized basket. Skipping would
            # silently compare different quarter sets between the two runs, so
            # take what there is and record the shortfall instead.
            log.warning("%s: only %d eligible after veto (wanted %d)",
                        q_label, len(eligible), top_n)
        top = eligible[:top_n]

        q_info = {"quarter": q_label, "entry_approx": entry_date.strftime("%Y-%m-%d"),
                  "scored": len(scored), "top_n": len(top),
                  "vetoed": n_vetoed}

        for h in horizons:
            top_rets = [s["_fwd"][h] for s in top if s["_fwd"].get(h) is not None]
            all_rets = [s["_fwd"][h] for s in scored if s["_fwd"].get(h) is not None]
            top_fwd[h].extend(top_rets)
            base_fwd[h].extend(all_rets)
            q_info[f"top_mean_{h}d"] = round(float(np.mean(top_rets)), 2) if top_rets else None
            q_info[f"base_mean_{h}d"] = round(float(np.mean(all_rets)), 2) if all_rets else None

        per_quarter.append(q_info)

    # 4. Aggregate
    summary = {}
    for h in horizons:
        t = top_fwd[h]
        b = base_fwd[h]
        if not t or not b:
            summary[h] = {"n_top": 0, "n_base": 0}
            continue
        top_mean = float(np.mean(t))
        base_mean = float(np.mean(b))
        edge = top_mean - base_mean
        p = _welch_p(t, b)
        hit_rate = sum(1 for r in t if r > 0) / len(t) * 100
        base_hit = sum(1 for r in b if r > 0) / len(b) * 100
        summary[h] = {
            "n_top": len(t),
            "n_base": len(b),
            "top_mean": round(top_mean, 2),
            "base_mean": round(base_mean, 2),
            "edge": round(edge, 2),
            "p": round(p, 4) if p is not None else None,
            "hit_rate": round(hit_rate, 1),
            "base_hit_rate": round(base_hit, 1),
        }

    n_quarters_used = len(per_quarter)
    # Per-quarter sign consistency
    for h in horizons:
        edges = []
        for q in per_quarter:
            tm = q.get(f"top_mean_{h}d")
            bm = q.get(f"base_mean_{h}d")
            if tm is not None and bm is not None:
                edges.append(tm - bm)
        n_pos = sum(1 for e in edges if e > 0)
        if h in summary and summary[h].get("n_top"):
            summary[h]["quarters_positive"] = n_pos
            summary[h]["quarters_total"] = len(edges)

    return {
        "kind": kind,
        "top_n": top_n,
        "horizons": horizons,
        "n_symbols": len(symbols),
        "n_with_ohlcv": len(ohlcv),
        "n_quarters_eval": n_quarters_used,
        "quarter_range": (eval_quarters[0][0], eval_quarters[-1][0]) if eval_quarters else None,
        "summary": summary,
        "per_quarter": per_quarter,
    }


def format_backtest(res: dict) -> str:
    if "error" in res:
        return f"ERROR: {res['error']}"
    lines = [
        "Hidden Treasures hit-rate backtest (B-34)",
        f"Universe: {res['kind']} ({res['n_symbols']} symbols, "
        f"{res['n_with_ohlcv']} with OHLCV)",
        f"Top N: {res['top_n']}   "
        f"Eval quarters: {res['n_quarters_eval']} "
        f"({res['quarter_range'][0]} … {res['quarter_range'][1]})" if res.get("quarter_range") else "",
        "",
        f"  {'horizon':>8}  {'top mean':>10}  {'base mean':>10}  {'edge':>8}  "
        f"{'p':>8}  {'hit%':>6}  {'base hit%':>10}  {'Q+/Q':>6}",
        "  " + "─" * 80,
    ]

    for h in res["horizons"]:
        s = res["summary"].get(h, {})
        if not s.get("n_top"):
            lines.append(f"  {h:>5}d    insufficient data")
            continue
        star = " *" if s.get("p") is not None and s["p"] < 0.05 else ""
        qp = s.get("quarters_positive", "?")
        qt = s.get("quarters_total", "?")
        p_s = f"{s['p']:.4f}{star}" if s.get("p") is not None else "     n/a"
        lines.append(
            f"  {h:>5}d  {s['top_mean']:>+10.2f}%  {s['base_mean']:>+10.2f}%  "
            f"{s['edge']:>+8.2f}%  {p_s:>10}  "
            f"{s['hit_rate']:>5.1f}%  {s['base_hit_rate']:>9.1f}%  "
            f"{qp}/{qt}"
        )

    lines += [
        "",
        "  * = Welch p<0.05 vs universe baseline",
        f"  n(top) = {res['summary'].get(res['horizons'][0], {}).get('n_top', 0)}  "
        f"n(base) = {res['summary'].get(res['horizons'][0], {}).get('n_base', 0)}",
        "",
        "Claim: do the top-ranked conviction names beat a random universe pick?",
    ]

    # Verdict
    primary = res["horizons"][-1]
    s = res["summary"].get(primary, {})
    if s.get("edge") is not None:
        if s["edge"] > 0 and s.get("p") is not None and s["p"] < 0.05:
            lines.append(f"  → YES — edge {s['edge']:+.2f}% at {primary}d (p={s['p']:.4f})")
        elif s["edge"] > 0 and s.get("p") is not None and s["p"] < 0.10:
            lines.append(f"  → MARGINAL — edge {s['edge']:+.2f}% at {primary}d (p={s['p']:.4f})")
        elif s["edge"] <= 0:
            lines.append(f"  → NO — edge {s['edge']:+.2f}% at {primary}d")
        else:
            lines.append(f"  → WEAK — edge {s['edge']:+.2f}% at {primary}d (p={s['p']:.4f})")
    else:
        lines.append("  → INSUFFICIENT DATA")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse, io, sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    logging.basicConfig(level=logging.WARNING)

    ap = argparse.ArgumentParser(description="B-34 Hidden Treasures hit-rate backtest")
    ap.add_argument("--kind", default="both",
                    help="Universe: both, smallcap250, microcap250, bse, all")
    ap.add_argument("--top", type=int, default=25, help="Top N to measure")
    ap.add_argument("--enrich", action="store_true",
                    help="Apply quality overlay scoring (slower)")
    ap.add_argument("--gov-veto", action="store_true",
                    help="B-34r2: drop names with a point-in-time governance red "
                         "flag (promoter stake -2pp+, pledge >5%%) before the top-N cut")
    ap.add_argument("--horizons", default="60,120",
                    help="Comma-separated forward horizons in trading days")
    a = ap.parse_args()

    horizons = tuple(int(x) for x in a.horizons.split(","))
    res = backtest_hidden_treasures(kind=a.kind, top_n=a.top,
                                    horizons=horizons, enrich=a.enrich,
                                    gov_veto=a.gov_veto)
    print(format_backtest(res))
