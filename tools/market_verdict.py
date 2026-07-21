"""market_verdict.py — turn the sentiment composite into ONE decision.

The overview ribbon used to show five bare numbers (Nifty, Regime, P&L, Capital
at Risk, Alerts). Every one of them was true and none of them said what to do
about it: RISK-OFF does not tell you whether to trade today, how large, or how
many times.

This module collapses the same inputs into a single verdict on a four-step
ladder — STAND DOWN / SELECTIVE / TRADE / AGGRESSIVE — plus a position-size
multiplier and a trade cap. The rule is deliberately mechanical and fully
inspectable: every flag that fed the decision is returned alongside it, so the
ribbon can show its work and you can disagree with a *specific* flag rather
than with an opaque score.

Design notes
  • Inputs come from sentiment_index.compute_sentiment() — already weighted,
    already persisted daily, so the ribbon reads a DB row instead of paying
    the ~24s recompute on every Streamlit rerun.
  • Each of the four sentiment components votes once, by how much of its own
    weight it earned (its `factor`). That keeps the vote scale-free: a
    component's threshold does not change when its weight is retuned.
  • Portfolio and calendar risks can only ever RAISE caution, never add
    conviction — capital already at risk is a reason to trade smaller, never
    a reason to trade bigger.

The thresholds below are starting points, not truths. Tune them against
Verdict Calibration before trusting the ladder with size.
"""

from __future__ import annotations

from typing import Any

# A component votes "favorable" at/above this share of its own weight, and
# "caution" at/below the lower one. The dead band between them is a real
# answer — it means that input is not currently saying anything useful.
FAVORABLE_AT = 0.60
CAUTION_AT   = 0.40

# Portfolio heat: above this, the book itself is the reason to slow down.
CAPITAL_AT_RISK_CAUTION_PCT = 6.0

# Human labels for the sentiment_index component keys.
COMPONENT_LABELS = {
    "advance_decline":    "Market breadth",
    "sector_performance": "Sector participation",
    "regime_sma200":      "NIFTY vs 200 SMA",
    "pmax_nifty_1h":      "PMax trend (NIFTY 1H)",
}

# verdict → (colour, position-size %, max trades, one-line instruction)
VERDICT_SPECS = {
    "STAND DOWN": ("#c62828", 0,   0,
                   "Sit out. The tape is against you — no size, no exceptions."),
    "SELECTIVE":  ("#b8860b", 50,  2,
                   "Trade only HIGH conviction setups. Reduce position size to 50%."),
    "TRADE":      ("#2e7d32", 100, 3,
                   "Normal conditions. Take your standard setups at full size."),
    "AGGRESSIVE": ("#1b5e20", 100, 4,
                   "Conditions favour you. Full size, and you may run multiple setups."),
    "NO EDGE":    ("#616161", 50,  1,
                   "Nothing is confirming either way. One A+ setup at half size, or nothing."),
}

DECISION_RULE = [
    "2+ caution flags → **STAND DOWN** (skip the day)",
    "1 caution flag → **SELECTIVE** (HIGH conviction only, smaller size)",
    "2+ favorable, 0 caution → **AGGRESSIVE** (multiple setups)",
    "1 favorable, 0 caution → **TRADE** (full size)",
    "no flags either way → **NO EDGE** (one A+ setup at half size)",
]


def _component_flags(inputs: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Vote each sentiment component once, by the share of its weight earned."""
    caution: list[str] = []
    favorable: list[str] = []
    for key, label in COMPONENT_LABELS.items():
        comp = inputs.get(key)
        if not isinstance(comp, dict):
            continue
        factor = comp.get("factor")
        if factor is None:
            weight, score = comp.get("weight"), comp.get("score")
            if not weight or score is None:
                continue
            factor = float(score) / float(weight)
        factor = float(factor)
        reading = comp.get("reading", "")
        if factor <= CAUTION_AT:
            caution.append(f"{label}: {reading}" if reading else label)
        elif factor >= FAVORABLE_AT:
            favorable.append(f"{label}: {reading}" if reading else label)
    return caution, favorable


def build_verdict(reading: dict[str, Any] | None,
                  portfolio: dict[str, Any] | None = None,
                  extra_cautions: list[str] | None = None) -> dict[str, Any]:
    """Collapse a sentiment reading (+ portfolio state) into one decision.

    `reading` is a sentiment_index reading dict. None-safe: with no reading at
    all, the missing data itself files a caution flag, so the ladder lands on
    SELECTIVE rather than erroring or — worse — defaulting to a green light
    that was never actually computed.
    """
    caution: list[str] = []
    favorable: list[str] = []

    if reading and isinstance(reading.get("inputs"), dict):
        caution, favorable = _component_flags(reading["inputs"])
    else:
        caution.append("No sentiment reading yet — refresh Market Sentiment")

    # Portfolio heat and calendar risk are caution-only by design.
    if portfolio:
        car = portfolio.get("capital_at_risk_pct")
        if car is not None and float(car) > CAPITAL_AT_RISK_CAUTION_PCT:
            caution.append(
                f"Capital at risk already {float(car):.1f}% "
                f"(over {CAPITAL_AT_RISK_CAUTION_PCT:.0f}%)")
    for extra in (extra_cautions or []):
        if extra:
            caution.append(extra)

    n_caution, n_favorable = len(caution), len(favorable)
    if n_caution >= 2:
        verdict = "STAND DOWN"
    elif n_caution == 1:
        verdict = "SELECTIVE"
    elif n_favorable >= 2:
        verdict = "AGGRESSIVE"
    elif n_favorable == 1:
        verdict = "TRADE"
    else:
        verdict = "NO EDGE"

    color, size_pct, max_trades, instruction = VERDICT_SPECS[verdict]
    return {
        "verdict":     verdict,
        "color":       color,
        "size_pct":    size_pct,
        "max_trades":  max_trades,
        "instruction": instruction,
        "caution":     caution,
        "favorable":   favorable,
        "n_caution":   n_caution,
        "n_favorable": n_favorable,
        "min_conviction": "HIGH" if verdict in ("STAND DOWN", "SELECTIVE", "NO EDGE") else "NORMAL",
        "score":       (reading or {}).get("score"),
        "band":        (reading or {}).get("band"),
        "as_of":       (reading or {}).get("reading_date"),
        "rule":        DECISION_RULE,
    }


# ── Regime classification ─────────────────────────────────────────────────────
# The old ribbon reduced regime to RISK-ON/RISK-OFF off a single 200 SMA cross.
# That misses the case that actually costs money: a market going nowhere, where
# breakout entries fake out and mean-reversion pays. Distance from the 50 SMA
# separates trending from ranging; realized vol against its own baseline says
# whether to expect follow-through or whipsaw.

SIDEWAYS_BAND_PCT = 2.0    # within this % of the 50 SMA reads as range-bound
VOL_HOT_RATIO     = 1.25   # realized vol this far above baseline reads as hot
# ...but only if it is also high in absolute terms. A trailing-year median
# taken over a calm year sits low enough that an ordinary uptick clears the
# ratio: NIFTY at 12% annualized tripped VOLATILE against a 9.6% baseline,
# which would have mislabelled a quiet range as whipsaw. Both tests must pass.
VOL_ABS_FLOOR_PCT = 15.0

REGIME_PLAYBOOKS = {
    "TRENDING UP":   "Trend-following works. Buy pullbacks into support, let winners run.",
    "TRENDING DOWN": "Downtrend. Rallies get sold — avoid bottom-fishing, respect stops.",
    "SIDEWAYS":      "Range-bound. Mean-reversion works, breakouts fake out.",
    "VOLATILE":      "Whipsaw risk. Widen stops or halve size — normal targets will not survive.",
}


def classify_regime(nifty_df) -> dict[str, Any]:
    """Classify NIFTY into a regime with a plain-English playbook line.

    Expects a DataFrame with a `close` column (>=60 rows for a meaningful
    read). Returns a dict that always includes `label` and `playbook`, with
    numeric fields set to None when there is not enough history.
    """
    out: dict[str, Any] = {"label": "UNKNOWN", "playbook": "Not enough history to classify.",
                           "dist_pct": None, "vol": None, "vol_baseline": None}
    if nifty_df is None or "close" not in getattr(nifty_df, "columns", []):
        return out
    close = nifty_df["close"].dropna()
    if len(close) < 60:
        return out

    import numpy as np

    last = float(close.iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1])
    if not sma50:
        return out
    dist_pct = (last - sma50) / sma50 * 100.0

    # Annualized realized vol: 20-day window against the median of the last
    # year of those same windows, so "high vol" is relative to this market's
    # own habits rather than a hardcoded number.
    rets = close.pct_change().dropna()
    vol = vol_baseline = None
    if len(rets) >= 40:
        rolling_vol = rets.rolling(20).std() * np.sqrt(252) * 100.0
        vol = float(rolling_vol.iloc[-1])
        baseline_window = rolling_vol.dropna().tail(252)
        if len(baseline_window):
            vol_baseline = float(baseline_window.median())

    if (vol is not None and vol_baseline
            and vol > vol_baseline * VOL_HOT_RATIO
            and vol >= VOL_ABS_FLOOR_PCT):
        label = "VOLATILE"
    elif abs(dist_pct) <= SIDEWAYS_BAND_PCT:
        label = "SIDEWAYS"
    elif dist_pct > 0:
        label = "TRENDING UP"
    else:
        label = "TRENDING DOWN"

    out.update({"label": label, "playbook": REGIME_PLAYBOOKS[label],
                "dist_pct": round(dist_pct, 2),
                "vol": None if vol is None else round(vol, 2),
                "vol_baseline": None if vol_baseline is None else round(vol_baseline, 2)})
    return out
