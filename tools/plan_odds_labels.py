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

Corrections applied after B-183c (stop geometry audits):
  B-183f (2026-11-19): RSI Divergence Bull stop was INVERTED; corrected stop gives
    AT BASELINE on fresh panel (+0.005R p 0.89). Card line REMOVED.
  B-183g (2026-11-19): Mean Reversion (Connors RSI2) stop was inside noise (79.1%);
    wider stop entry−2×ATR gives AT BASELINE (+0.056R p 0.44). Card line REMOVED.
"""
from __future__ import annotations

#: scanner -> mean d in R, per symbol, net of costs, clipped at ±3R.
#: Scanners absent here (RSI Divergence Bull, Mean Reversion Connors RSI2) were
#: re-measured after stop geometry fixes and confirmed AT BASELINE — no card line.
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
    "Support Breakdown": -0.33,
    "Inverted Flag & Pole": -0.41,
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
