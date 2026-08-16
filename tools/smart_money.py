"""smart_money.py — Smart-Money Confluence (Layer 4).

Answers "is institutional money behind this name?" as a transparent, coverage-
aware read. Per the design settled in-conversation (2026-08-16):

  * TWO sub-scores, never one blended composite:
      - Slow-Flow  — ownership *trajectory* (FII/DII/promoter trend over quarters)
      - Fast-Flow  — live tape (block/bulk deals ADV-normalised + OI regime)
    plus an AGREEMENT verdict between them (the divergence cells are the money
    read — "was accumulated, now being sold").
  * Pledge is a RISK VETO that qualifies the headline, NOT an additive component.
  * Earnings surprise is deliberately excluded (it's a Layer-3 factor, not flow).

This v1 implements Slow-Flow + the pledge veto. Fast-Flow is coverage-gated —
it returns None until the deal/OI plumbing is wired, and `agreement` falls back
to a single-sided (slow-only, low-confidence) verdict.

PURE + OFFLINE: reads only local caches (ownership_cache, screener_scraper's
pledge cache). No network, so it is cheap to call and unit-testable. The weights
and thresholds below are PRIORS — they are meant to be recalibrated against a
forward-return backtest, not treated as validated.
"""
from __future__ import annotations

import math

import ownership_cache as oc
import screener_scraper as ss

# ── Tunables (priors — recalibrate by backtest) ──────────────────────────────
#: Relative weight of each ownership leg inside Slow-Flow.
_SLOW_LEG_W = {"fii": 0.45, "dii": 0.35, "promoter": 0.20}
#: tanh saturation (percentage points of quarterly trend that ≈ a strong signal).
_SLOW_K = {"fii": 0.75, "dii": 0.75, "promoter": 0.50}
#: Recency weights over the last N quarterly deltas (newest first).
_TREND_W = (0.5, 0.3, 0.2)
#: Score bands (0–100, 50 = no footprint).
_ACC_BAND, _DIST_BAND = 57.0, 43.0
#: Promoter pledge % above which the veto qualifies the headline.
_PLEDGE_RISK = 5.0
#: A quarterly move smaller than this (pp) reads as "flat", not a trend.
_FLAT_EPS = 0.05

# ── Fast-Flow tunables ───────────────────────────────────────────────────────
#: Family weights inside Fast-Flow (deals less noisy than derivatives).
_FAST_FAMILY_W = {"deals": 0.6, "derivs": 0.4}
#: Net institutional buy as % of 30d traded value that ≈ a strong footprint.
_DEAL_K = 0.5
#: Trading sessions in a ~30-calendar-day window (for ADV → monthly value).
_SESSIONS_30D = 22
#: block_deal_intel.summarize_company strength → magnitude scaler. The module has
#: already judged whether a print is real signal vs churn/self-cross; we defer to it.
_DEAL_QUALITY = {"HIGH": 1.0, "INFORMATIVE": 0.9, "MODERATE": 0.5,
                 "BEARISH": 0.7, "WEAK": 0.25, "LOW": 0.15, "NOISE": 0.0}
#: nse_oi_momentum regime → (base sub-score, optional caveat flag).
_OI_REGIME_SUB = {
    "LONG BUILD-UP":  (0.8, None),
    "SHORT BUILD-UP": (-0.8, None),
    "SHORT COVERING": (0.3, "short-covering may be exhaustion, not accumulation"),
    "LONG UNWINDING": (-0.3, None),
    "NO CLEAR READ":  (0.0, None),
}
#: nse_oi_momentum strength → magnitude scaler.
_OI_STRENGTH = {"STRONG": 1.0, "MODERATE": 0.6, "UNSUPPORTED": 0.3,
                "UNRELIABLE": 0.15, "NONE": 0.0}


def _tanh(x: float) -> float:
    return math.tanh(x)


def _band(score: float | None) -> str:
    if score is None:
        return "unknown"
    if score > _ACC_BAND:
        return "accumulate"
    if score < _DIST_BAND:
        return "distribute"
    return "neutral"


# ── Slow-Flow: ownership trajectory ──────────────────────────────────────────
def _leg_deltas(vals: list[float | None]) -> list[float]:
    """Quarter-over-quarter deltas, newest first, stopping at the first gap so we
    only ever trend over a contiguous stretch of recent history."""
    deltas: list[float] = []
    for i in range(len(vals) - 1):
        a, b = vals[i], vals[i + 1]
        if a is None or b is None:
            break
        deltas.append(a - b)
    return deltas


def _weighted_trend(deltas: list[float]) -> float | None:
    """Recency-weighted mean of the quarterly deltas — accelerating accumulation
    outweighs a stale one-off."""
    if not deltas:
        return None
    w = _TREND_W[:len(deltas)]
    wsum = sum(w)
    return sum(wi * di for wi, di in zip(w, deltas)) / wsum


def _trajectory(deltas: list[float]) -> str:
    """Shape of the dominant leg's recent flow."""
    if not deltas:
        return "n/a"
    d1 = deltas[0]
    if abs(d1) < _FLAT_EPS:
        return "flat"
    if d1 > 0:
        # buying — faster than last quarter = accelerating, else steady
        return "accelerating" if (len(deltas) < 2 or d1 >= deltas[1]) else "steady"
    # selling — flipped down from a prior build = reversing, else distributing
    return "reversing" if (len(deltas) >= 2 and deltas[1] > 0) else "distributing"


def _slow_flow(symbol: str, quarters: int = 4) -> dict | None:
    """Ownership-trend sub-score, or None on insufficient cached history."""
    data = oc.load(symbol)
    qmap = data.get("quarters") or {}

    rows: list[tuple[str, dict]] = []
    for period, legs in qmap.items():
        ql = oc.quarter_label(period)
        if ql:
            rows.append((ql, legs))
    rows.sort(key=lambda r: r[0], reverse=True)          # newest quarter first
    rows = rows[:max(2, quarters)]
    if len(rows) < 2:
        return None

    def series(leg: str) -> list[float | None]:
        out = []
        for _ql, legs in rows:
            v = legs.get(leg)
            out.append(float(v) if v is not None else None)
        return out

    legs_out: dict[str, float] = {}
    deltas_by_leg: dict[str, list[float]] = {}
    num = den = 0.0
    for leg, lw in _SLOW_LEG_W.items():
        deltas = _leg_deltas(series(leg))
        t = _weighted_trend(deltas)
        if t is None:
            continue
        sub = _tanh(t / _SLOW_K[leg])
        legs_out[leg] = round(sub, 3)
        deltas_by_leg[leg] = deltas
        num += lw * sub
        den += lw

    if den == 0:
        return None

    slow_raw = num / den
    score = round(50 + 50 * slow_raw)

    # Trajectory from the highest-priority present leg.
    primary = next((leg for leg in ("fii", "dii", "promoter")
                    if leg in deltas_by_leg), None)
    traj = _trajectory(deltas_by_leg[primary]) if primary else "n/a"

    return {
        "score": score,
        "trajectory": traj,
        "as_of": rows[0][0],
        "legs": legs_out,
        "coverage": f"{len(rows)}q",
        "lagging": True,
    }


# ── Pledge veto (governance overlay, not a flow component) ────────────────────
def _pledge_veto(symbol: str) -> dict:
    rec = ss.read_pledge_cache(symbol)
    if rec is None or rec.get("pledge_pct") is None:
        return {"pledge_pct": None, "status": "unknown"}
    p = float(rec["pledge_pct"])
    status = "clean" if p == 0 else ("pledged" if p > _PLEDGE_RISK else "low")
    return {"pledge_pct": p, "status": status, "as_of": rec.get("as_of")}


# ── Fast-Flow: live tape (block/bulk deals + OI regime) ──────────────────────
def _adv_value_from_ohlcv(ohlcv, sessions: int = _SESSIONS_30D) -> float | None:
    """Average daily traded VALUE (₹) over the last `sessions` bars, tolerant of
    column-name casing. Returns None if the frame is unusable."""
    try:
        df = ohlcv.tail(sessions)
        cols = {str(c).lower(): c for c in df.columns}
        cc, vc = cols.get("close"), cols.get("volume")
        if not cc or not vc:
            return None
        val = (df[cc].astype(float) * df[vc].astype(float)).mean()
        return float(val) if val and val == val else None       # NaN-guard
    except Exception:
        return None


def _fast_flow(symbol: str, *, deals_summary: dict | None = None,
               oi=None, adv_value: float | None = None, ohlcv=None) -> dict | None:
    """Live-tape sub-score from caller-injected market data. One representative
    value per evidence family (deals, derivatives) so a single flow can't be
    double-counted. Returns None when neither family has usable data."""
    fam: dict[str, float] = {}
    families_out: dict[str, float] = {}
    flags: list[str] = []

    # Family A — block/bulk deals, ADV-normalised and quality-scaled.
    if deals_summary:
        buy = float(deals_summary.get("buy_value") or 0.0)
        sell = float(deals_summary.get("sell_value") or 0.0)
        adv = adv_value if adv_value is not None else _adv_value_from_ohlcv(ohlcv)
        if adv and adv > 0 and (buy or sell):
            net_pct = (buy - sell) / (adv * _SESSIONS_30D) * 100.0
            quality = _DEAL_QUALITY.get(
                str(deals_summary.get("strength", "")).upper(), 0.5)
            self_cross = float(deals_summary.get("self_cross_ratio") or 0.0)
            sub = _tanh(net_pct / _DEAL_K) * quality * (1.0 - self_cross)
            sub = max(-1.0, min(1.0, sub))
            fam["deals"] = sub
            families_out["deals"] = round(sub, 3)

    # Family B — OI + price regime. Accept a raw regime string or the
    # nse_oi_momentum.summarize_symbol dict ({reading, strength}).
    reading = oi_strength = None
    if isinstance(oi, dict):
        reading, oi_strength = oi.get("reading"), oi.get("strength")
    elif isinstance(oi, str):
        reading = oi
    if reading in _OI_REGIME_SUB:
        base, caveat = _OI_REGIME_SUB[reading]
        scale = _OI_STRENGTH.get(str(oi_strength).upper(), 1.0) if oi_strength else 1.0
        sub = base * scale
        if abs(sub) > 1e-9:
            fam["derivs"] = sub
            families_out["derivs"] = round(sub, 3)
            if caveat:
                flags.append(caveat)

    if not fam:
        return None

    num = sum(_FAST_FAMILY_W[k] * v for k, v in fam.items())
    den = sum(_FAST_FAMILY_W[k] for k in fam)
    score = round(50 + 50 * (num / den))
    return {
        "score": score,
        "families": families_out,
        "window": "30d",
        "coverage": f"{len(fam)}/2",
        "flags": flags,
    }


# ── Agreement verdict ────────────────────────────────────────────────────────
#: Both sub-scores present: (slow_band, fast_band) -> (enum, headline).
_AGREE_MATRIX = {
    ("accumulate", "accumulate"): ("confirmed_accumulation",
        "Institutions accumulating — slow + live agree"),
    ("distribute", "distribute"): ("confirmed_distribution",
        "Institutions distributing — slow + live agree"),
    ("accumulate", "distribute"): ("bought_now_selling",
        "⚠ Was accumulated, live tape now distributing"),
    ("distribute", "accumulate"): ("early_reversal",
        "Live buying against a weak ownership base — early reversal?"),
    ("accumulate", "neutral"): ("accumulated_quiet",
        "Accumulated on ownership; live tape quiet"),
    ("neutral", "accumulate"): ("fresh_buying",
        "Fresh live buying; ownership not yet reflecting it"),
    ("distribute", "neutral"): ("distributed_quiet",
        "Distributed on ownership; live tape quiet"),
    ("neutral", "distribute"): ("fresh_selling",
        "Fresh live selling; ownership not yet reflecting it"),
    ("neutral", "neutral"): ("no_footprint", "No institutional footprint"),
}

#: Slow-only fallback (Fast-Flow not yet wired) -> (enum, headline).
_SLOW_ONLY = {
    "accumulate": ("slow_accumulation",
        "Institutions accumulating (ownership trend; live tape not yet wired)"),
    "distribute": ("slow_distribution",
        "Institutions distributing (ownership trend; live tape not yet wired)"),
    "neutral": ("slow_neutral", "No clear ownership footprint"),
}


#: Fast-only fallback (ownership not yet cached) -> (enum, headline).
_FAST_ONLY = {
    "accumulate": ("fast_accumulation",
        "Live tape buying (ownership trend not yet cached)"),
    "distribute": ("fast_distribution",
        "Live tape selling (ownership trend not yet cached)"),
    "neutral": ("fast_neutral", "No clear live-tape footprint"),
}


def _agreement(slow_band: str, fast_band: str) -> tuple[str, str]:
    if slow_band == "unknown" and fast_band == "unknown":
        return "no_data", "No ownership data cached"
    if fast_band == "unknown":
        return _SLOW_ONLY[slow_band]
    if slow_band == "unknown":
        return _FAST_ONLY[fast_band]
    return _AGREE_MATRIX[(slow_band, fast_band)]


# ── Public entry point ───────────────────────────────────────────────────────
_POSITIVE_AGREE = {"confirmed_accumulation", "slow_accumulation",
                   "fast_accumulation", "early_reversal", "fresh_buying",
                   "accumulated_quiet"}


def smart_money(symbol, *, quarters: int = 4, ohlcv=None, sessionid=None,
                deals_summary: dict | None = None, oi=None,
                adv_value: float | None = None) -> dict:
    """Smart-Money Confluence read for `symbol`.

    Slow-Flow (ownership trajectory, from local cache) + pledge veto are computed
    with no network. Fast-Flow (live tape) scores caller-INJECTED market data —
    pass `deals_summary` (block_deal_intel.summarize_company), `oi`
    (nse_oi_momentum regime string or summarize_symbol dict), and either
    `adv_value` (avg daily traded ₹) or `ohlcv` (to derive it). Omit them and
    Fast-Flow stays absent, collapsing to a single-sided (slow-only) verdict.

    Never a bare number — the caller should render `slow.legs` / `fast.families`
    (the drivers) alongside the headline.
    """
    sym = str(symbol).upper().replace(".NS", "").strip()

    slow = _slow_flow(sym, quarters=quarters)
    fast = _fast_flow(sym, deals_summary=deals_summary, oi=oi,
                      adv_value=adv_value, ohlcv=ohlcv)
    veto = _pledge_veto(sym)

    slow_band = _band(slow["score"]) if slow else "unknown"
    fast_band = _band(fast["score"]) if fast else "unknown"
    agreement, headline = _agreement(slow_band, fast_band)

    # Distinguish "nothing cached" from "cached but <2 quarters" — the design
    # forbids conflating no-data with insufficient-history.
    if slow is None and fast is None:
        _n_q = len(oc.load(sym).get("quarters") or {})
        if _n_q >= 1:
            agreement = "insufficient_history"
            headline = f"Only {_n_q}q ownership cached — need ≥2 quarters to trend"

    flags: list[str] = list(fast["flags"]) if fast else []
    if veto["status"] == "pledged":
        flags.append(f"governance risk — promoter pledge {veto['pledge_pct']:.1f}%")
        if agreement in _POSITIVE_AGREE:
            headline += " — but governance risk (pledged)"

    if slow and fast:
        confidence = "high"           # two-sided: ownership + live tape
    elif slow:
        confidence = "low"            # single-sided + lagging by construction
    elif fast:
        confidence = "medium"         # live tape only, no ownership confirmation
    else:
        confidence = "none"

    return {
        "symbol": sym,
        "slow": slow,
        "fast": fast,
        "agreement": agreement,
        "headline": headline,
        "veto": veto,
        "confidence": confidence,
        "flags": flags,
    }


if __name__ == "__main__":
    import sys
    import json
    _sym = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE"
    print(json.dumps(smart_money(_sym), indent=2, ensure_ascii=False))
    if smart_money(_sym)["slow"] is None:
        print(f"\n(no cached ownership quarters for {_sym} — warm the cache with "
              f"`py -3 tools/ownership_cache.py --backfill`)", file=sys.stderr)
