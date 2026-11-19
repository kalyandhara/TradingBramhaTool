"""plan_odds_labels.py — the B-183c card lines, as pre-registered.

B-183c compared each scanner's plan (entry, stop, target, time stop) with what the
same plan earns on a drift-free replay of the stock's own bars. Its rule, fixed
before the run: a card carries a line only if the strict placebo gate passed, the
verdict is BEATS or BELOW, and the scanner is not "within placebo noise". The gate
passed and no scanner was within noise, so all 14 below qualify. Every other
scanner carries no line.

The line is about the plan's levels, not the signal: Failed Breakdown's plan BEATS
while its signal measured NULL (B-203). Source:
wiki/analyses/Plan-Odds-Baseline-Robust; re-running the study does not change these
numbers until they are updated here.
"""
from __future__ import annotations

#: scanner -> mean d in R, per symbol, net of costs, clipped at ±3R.
PLAN_ODDS_D: dict[str, float] = {
    "Flag & Pole": 0.37,
    "Bullish CHoCH (last 5 sessions)": 0.18,
    "%R Bottoming": 0.17,
    "Failed Breakdown (2-bar sweep)": 0.08,
    "HM Buy (Hilega Milega)": 0.07,
    "RSI 60-40 Setup": 0.07,
    "FVG Pullback": 0.07,
    "Harmonic Reversal (XABCD)": 0.07,
    "Liquidity Sweep": -0.09,
    "VWAP Mean Reversion": -0.16,
    "RSI Divergence Bull": -0.22,
    "Support Breakdown": -0.33,
    "Inverted Flag & Pole": -0.41,
    "Mean Reversion (Connors RSI2)": -0.41,
}


def card_lines(scanner_name: str) -> list[str]:
    """Card reason lines for this scanner; [] for any scanner without a label."""
    d = PLAN_ODDS_D.get(scanner_name)
    if d is None:
        return []
    if d > 0:
        return [f"Plan levels beat the no-edge baseline by +{d:.2f}R (B-183c): "
                "the levels, not the signal"]
    return [f"⚠ Plan levels run {abs(d):.2f}R below the no-edge baseline (B-183c): "
            "the levels, not the signal"]
