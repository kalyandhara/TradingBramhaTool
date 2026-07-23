"""Forward price-projection engine (Milestone 3 — the "prediction line").

Deterministic, offline, and *inspectable* by design. Rather than an opaque LLM
number (the roadmap's cautioned path), this composes projected-price candidates
from computation the repo already trusts:

  • Elliott Wave  — ew_module.analyze_ew() probabilistic Fib targets (W3/W5),
                    carrying their own confidence + wave-basis label.
  • VCP           — scanner_templates.detect_vcp_geometry() measured-move target.
  • Rounding Bottom — scanner_templates.scan_rounding_bottom() target.
  • Harmonic      — harmonic_patterns.detect_last_pattern() D-pivot trade targets.

Each candidate is (price, confidence, reasoning, direction). The engine picks the
highest-confidence candidate as the primary projection and reports **confluence**
— how many independent methods agree within a price tolerance. Agreement is a
stronger, more honest signal than any single number.

Anti-overtrust guardrails (per wiki/analyses/Dashboard-UI-Roadmap.md M3):
  • A projection is returned ONLY when primary confidence ≥ MEDIUM_FLOOR. Below
    that it is "Low" and suppressed entirely (endpoint returns None) — the client
    shows nothing rather than a weak number.
  • The result always carries `reasoning` and `invalidation` (a stop level), so
    the client can render *why*, never a naked target.
  • `band` is High / Medium only (Low is never surfaced).
"""

from __future__ import annotations

import ew_module
import scanner_templates as sc
import harmonic_patterns as hp

# Confidence floors. A primary below MEDIUM_FLOOR is treated as "Low" → hidden.
HIGH_FLOOR = 66
MEDIUM_FLOOR = 45
# Two candidates count as "in agreement" when within this fraction of each other.
CONFLUENCE_TOL = 0.03  # 3%
# Analysis window: detectors are tuned for ~this many bars. The chart client
# fetches far more history for display (TF_BARS['1d'] = 2600 ≈ 10Y), and running
# ZigZag/EW over a decade produces a gigantic W1 leg and absurd Fib targets
# (observed: TITAN +138% "High confidence"). Slice before analyzing so the
# projection is independent of how much history the client happens to fetch.
ANALYSIS_BARS = 300
# Plausibility ceiling on the implied move, per timeframe. A projection beyond
# this is rejected as a candidate outright — belt-and-braces against any
# detector emitting a technically-valid but practically absurd target.
MAX_MOVE_PCT = {
    "1m": 8, "5m": 10, "15m": 12, "30m": 15,
    "1h": 20, "4h": 30, "1d": 60, "1w": 100,
}
# How far forward (in bars) the client draws the projection line. Indicative
# horizon for slope/magnitude — NOT a dated forecast. Tuned per timeframe.
HORIZON_BARS = {
    "1m": 30, "5m": 24, "15m": 20, "30m": 18,
    "1h": 16, "4h": 14, "1d": 20, "1w": 12,
}

# Verdict → confidence maps. Verdict strings mirror the scanner/overlay wording.
_VCP_CONF = {"BUY": 78, "WEAK BUY": 58, "READY": 46, "WATCH": 38}
_RB_CONF = {"BUY": 75, "BUY (retest hold)": 75, "WEAK BUY": 55, "WATCH": 40}


def _band(conf: int) -> str:
    return "High" if conf >= HIGH_FLOOR else "Medium"


def _ew_candidate(df):
    """Elliott Wave projection: the highest-probability active-wave Fib target.
    Only fires for a *confirmed* impulse (W3/W5 above W1) that is not already in
    the exhaustion zone — anticipatory W2 counts are deliberately excluded."""
    try:
        ew = ew_module.analyze_ew(df)
    except Exception:
        return None
    if not ew.get("ew_valid"):
        return None
    wave = ew.get("wave_pos")
    if wave not in ("W3", "W5"):
        return None
    if ew.get("ext_risk") == "EXHAUSTION":
        return None  # target likely already met — don't project into thin air
    targets = ew.get("w3_targets") if wave == "W3" else ew.get("w5_targets")
    if not targets:
        return None
    # Highest-probability target is the primary projection.
    price, prob, label = max(targets, key=lambda t: t[1])
    count_conf = int(ew.get("confidence", 0) or 0)
    # Effective confidence blends the wave-count reliability with the specific
    # target's probability — a 35%-probability Fib level must not surface as
    # "High" purely on the strength of the count.
    conf = round(count_conf * (0.4 + 0.6 * prob / 100.0))
    return {
        "source": f"Elliott Wave {wave}",
        "price": float(price),
        "confidence": conf,
        "direction": "up",  # W3/W5 impulse targets are above current by construction
        "reasoning": f"{wave} Fib target {label} (count confidence {count_conf}%, "
                     f"target prob {prob}%). {ew.get('note', '')}".strip(),
        "invalidation": ew.get("stop_zone"),
    }


def _vcp_candidate(df):
    try:
        g = sc.detect_vcp_geometry(df)
    except Exception:
        return None
    if not g or g.get("target") is None:
        return None
    verdict = g.get("verdict", "")
    conf = _VCP_CONF.get(verdict, 30)
    rr = g.get("risk_reward")
    rr_txt = f"R:R {rr}×" if isinstance(rr, (int, float)) else "R:R —"
    return {
        "source": "VCP",
        "price": float(g["target"]),
        "confidence": conf,
        "direction": "up",
        "reasoning": f"VCP measured-move target (verdict {verdict or 'n/a'}, "
                     f"footprint {g.get('footprint', '—')}, {rr_txt}).",
        "invalidation": g.get("stop"),
    }


def _rb_candidate(df):
    try:
        hit = sc.scan_rounding_bottom(df)
    except Exception:
        return None
    if not hit or "geometry" not in hit:
        return None
    g = hit["geometry"]
    if g.get("target") is None:
        return None
    verdict = g.get("verdict", "")
    conf = _RB_CONF.get(verdict, 30)
    rr = g.get("risk_reward")
    rr_txt = f"R:R {rr}×" if isinstance(rr, (int, float)) else "R:R —"
    return {
        "source": "Rounding Bottom",
        "price": float(g["target"]),
        "confidence": conf,
        "direction": "up",
        "reasoning": f"Saucer rim measured-move target (verdict {verdict or 'n/a'}, "
                     f"score {g.get('score', '—')}/100, {rr_txt}).",
        "invalidation": g.get("stop"),
    }


def _harmonic_candidate(df, timeframe):
    try:
        max_age = {"1m": 8, "5m": 12, "15m": 15, "30m": 20,
                   "1h": 25, "4h": 30, "1d": 50, "1w": 20}.get(timeframe, 30)
        m = hp.detect_last_pattern(df, max_age_bars=max_age)
    except Exception:
        return None
    if not m:
        return None
    trade = m.get("trade") or {}
    targets = trade.get("targets") or []
    if not targets:
        return None
    direction = m.get("direction", "bullish")
    # Age-decayed moderate confidence — a valid completed XABCD, softened as the
    # D-pivot recedes into the past.
    age = int(m.get("age_bars", 0) or 0)
    conf = max(35, 55 - age // 5)
    return {
        "source": f"Harmonic {m.get('pattern', '')}".strip(),
        "price": float(targets[0]),
        "confidence": conf,
        "direction": "up" if direction == "bullish" else "down",
        "reasoning": f"{m.get('pattern', 'Harmonic')} {direction} — first target "
                     f"(0.382 AD), pattern age {age} bars.",
        "invalidation": trade.get("stop"),
    }


def compute_projection(df, timeframe: str = "1d") -> dict | None:
    """Return the best forward projection for `df`, or None if nothing confident.

    None means "show nothing" — the guardrail against surfacing a weak number.
    """
    if df is None or len(df) < 30:
        return None
    # Fixed analysis window — see ANALYSIS_BARS note above.
    df = df.iloc[-ANALYSIS_BARS:]
    current = float(df["close"].iloc[-1])

    candidates = [
        c for c in (
            _ew_candidate(df),
            _vcp_candidate(df),
            _rb_candidate(df),
            _harmonic_candidate(df, timeframe),
        ) if c is not None
    ]
    # Plausibility gate: drop any candidate whose implied move exceeds the
    # timeframe's ceiling — absurd targets never even compete for primary.
    cap = MAX_MOVE_PCT.get(timeframe, 60)
    candidates = [
        c for c in candidates
        if abs(c["price"] - current) / current * 100.0 <= cap
    ]
    if not candidates:
        return None

    # Primary = highest confidence. Suppress entirely if that's still "Low".
    primary = max(candidates, key=lambda c: c["confidence"])
    if primary["confidence"] < MEDIUM_FLOOR:
        return None

    # Confluence: other candidates agreeing on price (within tolerance) AND
    # direction. Agreement bumps the band one notch (capped at High).
    agree = [
        c for c in candidates
        if c is not primary
        and c["direction"] == primary["direction"]
        and abs(c["price"] - primary["price"]) / primary["price"] <= CONFLUENCE_TOL
    ]
    confidence = primary["confidence"]
    if agree:
        confidence = min(100, confidence + 8 * len(agree))

    pct_move = (primary["price"] - current) / current * 100.0

    return {
        "projected_price": round(primary["price"], 2),
        "current_price": round(current, 2),
        "pct_move": round(pct_move, 2),
        "direction": primary["direction"],
        "confidence": int(confidence),
        "band": _band(confidence),
        "source": primary["source"],
        "reasoning": primary["reasoning"],
        "invalidation": (round(primary["invalidation"], 2)
                         if isinstance(primary.get("invalidation"), (int, float))
                         else None),
        "horizon_bars": HORIZON_BARS.get(timeframe, 20),
        "confluence_count": 1 + len(agree),
        "confluence": [
            {"source": c["source"], "price": round(c["price"], 2),
             "confidence": c["confidence"]}
            for c in [primary, *agree]
        ],
        # Every candidate considered (incl. non-agreeing) — for the reasoning panel.
        "all_sources": [
            {"source": c["source"], "price": round(c["price"], 2),
             "confidence": c["confidence"], "reasoning": c["reasoning"]}
            for c in sorted(candidates, key=lambda c: -c["confidence"])
        ],
    }
