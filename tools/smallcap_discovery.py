#!/usr/bin/env python3
"""
smallcap_discovery.py — the "hidden treasures" scorer (backlog B-34).

Ranks the FREE small/micro-cap universe (smallcap_universe.py) by *institutional
conviction*, read entirely from free NSE shareholding data via ownership_cache —
no screener.in cookie. The thesis (multibagger "engine"): in small/micro-caps a
real multibagger usually shows fresh FII+DII accumulation while promoters are NOT
distributing and pledge is low, ahead of the obvious growth. This surfaces a
DELIBERATELY SMALL, high-conviction list — the opposite of the top-layer funnel.

Reads from ownership_cache (pure disk). Names not yet cached are skipped; run
`backfill()` (or `python smallcap_discovery.py --backfill`) once to warm them.

UNMEASURED: every weight below is a prior. The B-34 test is a forward hit-rate
study of this ranking vs a Smallcap-250 benchmark — until then it's a discovery
lens, not an edge.

  from smallcap_discovery import discover
  hits = discover(limit=25)

CLI:
  py -3 tools/smallcap_discovery.py --backfill --limit 60   # warm the cache
  py -3 tools/smallcap_discovery.py --limit 25              # rank cached names
"""
from __future__ import annotations

import logging

import smallcap_universe as scu
import ownership_cache as oc
import nse_shareholding_fetch as nsf

log = logging.getLogger(__name__)

PLEDGE_MAX = 5.0        # promoter pledge above this = governance veto (flag)
PROMOTER_SELL_PP = 2.0  # promoter stake falling more than this = distribution

# Quality overlay thresholds (B-34 residual).
ROCE_GOOD = 15.0        # ROCE above this gets a quality bonus
OPM_GOOD = 12.0         # operating profit margin floor
DE_MAX = 1.0            # debt/equity above this is a quality penalty


def _ordered_quarters(data: dict) -> list[tuple[str, dict]]:
    q = data.get("quarters") or {}
    return sorted(q.items(), key=lambda t: nsf._period_date(t[0]) or __import__(
        "datetime").datetime.min)


def score_from_cache(symbol: str) -> dict | None:
    """Conviction score for one symbol from cached ownership. None if <2 quarters."""
    data = oc.load(symbol)
    qs = _ordered_quarters(data)
    if len(qs) < 2:
        return None
    (p_old, v_old), (p_new, v_new) = qs[0], qs[-1]

    def _n(v):
        return float(v) if isinstance(v, (int, float)) else None

    fii_new, dii_new = _n(v_new.get("fii")), _n(v_new.get("dii"))
    fii_old, dii_old = _n(v_old.get("fii")), _n(v_old.get("dii"))
    prom_new, prom_old = _n(v_new.get("promoter")), _n(v_old.get("promoter"))
    pledge = _n(v_new.get("promoter_pledge_pct"))

    inst_new = sum(x for x in (fii_new, dii_new) if x is not None)
    inst_old = sum(x for x in (fii_old, dii_old) if x is not None)
    inst_delta = round(inst_new - inst_old, 2)                     # pp accumulation
    prom_delta = (round(prom_new - prom_old, 2)
                  if prom_new is not None and prom_old is not None else None)

    reasons, score = [], 40.0
    # Main engine: FII+DII accumulation RATE (pp per quarter, so windows of
    # different length compare fairly and the score spreads instead of saturating).
    rate = inst_delta / max(1, len(qs) - 1)
    score += max(-6.0, min(6.0, rate)) * 5                         # ±30, ±6pp/q caps
    if inst_delta > 0:
        reasons.append(f"FII+DII accumulating {inst_delta:+.2f}pp ({rate:+.2f}pp/q) "
                       f"over {len(qs)} quarters ({inst_old:.1f}%→{inst_new:.1f}%).")
    else:
        reasons.append(f"FII+DII net {inst_delta:+.2f}pp (no accumulation).")
    # Promoter conduct.
    if prom_delta is not None:
        if prom_delta <= -PROMOTER_SELL_PP:
            score -= 15
            reasons.append(f"⚠ Promoter selling {prom_delta:+.2f}pp — distribution.")
        elif prom_delta >= -0.5:
            score += 10
            reasons.append(f"Promoter steady/adding ({prom_delta:+.2f}pp).")
    # Pledge veto/flag.
    pledge_flag = pledge is not None and pledge > PLEDGE_MAX
    if pledge_flag:
        score -= 20
        reasons.append(f"⚠ Pledge {pledge:.1f}% (> {PLEDGE_MAX:.0f}%) — governance risk.")
    elif pledge is not None:
        reasons.append(f"Pledge {pledge:.1f}%.")

    return {
        "symbol": symbol,
        "score": round(max(0.0, min(100.0, score)), 1),
        "inst_delta": inst_delta,
        "promoter_delta": prom_delta,
        "pledge_pct": pledge,
        "pledge_flag": pledge_flag,
        "as_of": p_new,
        "quarters": len(qs),
        "reasons": reasons,
    }


def _enrich_quality(hit: dict) -> None:
    """Add ROCE/OPM/D/E from fundamentals_deep and adjust the conviction score."""
    try:
        import fundamentals_deep as fdeep
        d = fdeep.derive_fundamentals(hit["symbol"])
    except Exception:
        hit["quality"] = None
        return
    roce = d.get("roce")
    opm = d.get("opm")
    de = d.get("debt_to_equity")
    mc = d.get("market_cap")
    mc_cr = round(mc / 1e7, 0) if mc else None
    hit["quality"] = {"roce": roce, "opm": opm, "debt_to_equity": de,
                      "market_cap": mc, "market_cap_cr": mc_cr}

    bonus = 0.0
    reasons = hit.setdefault("reasons", [])
    if roce is not None and roce >= ROCE_GOOD:
        bonus += 8
        reasons.append(f"ROCE {roce:.1f}% ≥ {ROCE_GOOD:.0f}%.")
    elif roce is not None:
        reasons.append(f"ROCE {roce:.1f}% (below {ROCE_GOOD:.0f}%).")
    if opm is not None and opm >= OPM_GOOD:
        bonus += 5
        reasons.append(f"OPM {opm:.1f}% ≥ {OPM_GOOD:.0f}%.")
    elif opm is not None:
        reasons.append(f"OPM {opm:.1f}%.")
    if de is not None and de > DE_MAX:
        bonus -= 8
        reasons.append(f"⚠ D/E {de:.2f} > {DE_MAX:.1f} — leverage risk.")
    elif de is not None:
        reasons.append(f"D/E {de:.2f}.")
    hit["score"] = round(max(0.0, min(100.0, hit["score"] + bonus)), 1)


def discover(kind: str = "both", limit: int = 25, enrich: bool = False) -> dict:
    """Rank the cached names in the small/micro-cap universe by conviction.
    Pass ``enrich=True`` to add ROCE/OPM/D/E from yfinance (slower — one call
    per name). Returns {"hits": [...ranked...], "scanned", "cached", "universe"}."""
    uni = scu.fetch_universe(kind)
    meta = {e["symbol"]: e for e in uni}
    hits, cached = [], 0
    for e in uni:
        s = score_from_cache(e["symbol"])
        if s is None:
            continue
        cached += 1
        s["name"] = e.get("name")
        s["industry"] = e.get("industry")
        s["index"] = e.get("index")
        if enrich:
            _enrich_quality(s)
        hits.append(s)
    hits.sort(key=lambda h: h["score"], reverse=True)
    return {"hits": hits[:limit], "scanned": len(hits), "cached": cached,
            "universe": len(uni)}


def backfill(kind: str = "both", limit: int | None = None, quarters: int = 6,
             force: bool = False, progress: bool = True) -> int:
    """Warm ownership_cache for the small/micro-cap universe. Resumable — new
    quarters are only fetched when absent. Pass force=True to re-fetch cached
    quarters too (needed once, to add the promoter_pledge_pct column to entries
    cached before it existed). Returns names processed."""
    uni = scu.fetch_universe(kind)
    if limit:
        uni = uni[:limit]
    session = nsf._new_session()
    done = 0
    for i, e in enumerate(uni, 1):
        try:
            oc.fetch_symbol(e["symbol"], session=session, quarters=quarters, force=force)
        except Exception as ex:
            log.warning("[%s] backfill failed: %s", e["symbol"], ex)
        done += 1
        if progress and i % 10 == 0:
            print(f"  …{i}/{len(uni)} ({e['symbol']})")
    return done


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser(description="Small/micro-cap conviction discovery")
    ap.add_argument("--backfill", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="re-fetch cached quarters too (adds pledge to old entries)")
    ap.add_argument("--enrich", action="store_true",
                    help="add ROCE/OPM/D/E quality overlay (slower)")
    ap.add_argument("--kind", default="both")
    ap.add_argument("--limit", type=int, default=None,
                    help="cap names (backfill AND display); default = ALL for "
                         "backfill, top 25 for display")
    ap.add_argument("--quarters", type=int, default=6)
    a = ap.parse_args()
    if a.backfill:
        n = backfill(a.kind, limit=a.limit, quarters=a.quarters, force=a.force)
        print(f"Backfilled {n} names into ownership_cache.")
    res = discover(a.kind, limit=a.limit or 25, enrich=a.enrich)
    print(f"\nUniverse {res['universe']} · cached {res['cached']} · showing "
          f"top {len(res['hits'])}:")
    for h in res["hits"]:
        q = h.get("quality") or {}
        qual = ""
        if q:
            qual = (f" ROCE={q['roce']:.1f}%" if q.get("roce") is not None else "") + \
                   (f" OPM={q['opm']:.1f}%" if q.get("opm") is not None else "") + \
                   (f" D/E={q['debt_to_equity']:.2f}" if q.get("debt_to_equity") is not None else "")
        print(f"  {h['score']:5.1f}  {h['symbol']:12} inst{h['inst_delta']:+.2f} "
              f"prom{h['promoter_delta'] if h['promoter_delta'] is not None else '—'} "
              f"pledge{h['pledge_pct'] if h['pledge_pct'] is not None else '—'}"
              f"{qual}  {h.get('industry','')}")
