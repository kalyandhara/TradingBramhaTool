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


def discover(kind: str = "both", limit: int = 25) -> dict:
    """Rank the cached names in the small/micro-cap universe by conviction.
    Returns {"hits": [...ranked...], "scanned", "cached", "universe"}."""
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
        hits.append(s)
    hits.sort(key=lambda h: h["score"], reverse=True)
    return {"hits": hits[:limit], "scanned": len(hits), "cached": cached,
            "universe": len(uni)}


def backfill(kind: str = "both", limit: int | None = None, quarters: int = 6,
             progress: bool = True) -> int:
    """Warm ownership_cache for the small/micro-cap universe. Bounded, resumable
    (ownership_cache skips symbols already fresh). Returns names processed."""
    uni = scu.fetch_universe(kind)
    if limit:
        uni = uni[:limit]
    session = nsf._new_session()
    done = 0
    for i, e in enumerate(uni, 1):
        try:
            oc.fetch_symbol(e["symbol"], session=session, quarters=quarters)
        except Exception as ex:
            log.warning("[%s] backfill failed: %s", e["symbol"], ex)
        done += 1
        if progress and i % 10 == 0:
            print(f"  …{i}/{len(uni)}")
    return done


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser(description="Small/micro-cap conviction discovery")
    ap.add_argument("--backfill", action="store_true")
    ap.add_argument("--kind", default="both")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--quarters", type=int, default=6)
    a = ap.parse_args()
    if a.backfill:
        n = backfill(a.kind, limit=a.limit, quarters=a.quarters)
        print(f"Backfilled {n} names into ownership_cache.")
    res = discover(a.kind, limit=a.limit)
    print(f"\nUniverse {res['universe']} · cached {res['cached']} · showing "
          f"top {len(res['hits'])}:")
    for h in res["hits"]:
        print(f"  {h['score']:5.1f}  {h['symbol']:12} inst{h['inst_delta']:+.2f} "
              f"prom{h['promoter_delta'] if h['promoter_delta'] is not None else '—'} "
              f"pledge{h['pledge_pct'] if h['pledge_pct'] is not None else '—'}  "
              f"{h.get('industry','')}")
