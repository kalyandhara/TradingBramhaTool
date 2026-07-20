---
title: "%R Trend Exhaustion"
category: concept
tags: [williams-percent-r, oscillator, reversal, trend-exhaustion, overbought-oversold]
created: 2026-07-02
updated: 2026-07-02
sources: 1
related:
  - concepts/RSI.md
  - concepts/ADX.md
  - concepts/Stage-Analysis.md
  - sources/TradingView-Goodyear-PMax-Strat-Confluence-2026.md
---

# %R Trend Exhaustion

## Definition

A dual-length Williams %R oscillator ("%R Trend Exhaustion [upslidedown]", Pine v6, community indicator) that prints a reversal signal the bar a stock **leaves** an overbought or oversold zone, rather than the bar it enters one. The entry into the zone is a "trend warning"; the exit is the actual "exhaustion" signal — the trend that pushed price into the extreme has run out of energy.

Built and ported into this project twice: a JS version for the live chart dashboard ([[sources/YT-MultiChart-TradingView-Alternative]]'s chart tool) and a Python version (`scanner_templates.compute_recent_exhaustion_signal`) for bulk screening.

## How to Use

- Two Williams %R lines: **fast** (21-period, EMA-7 smoothed) and **slow** (112-period, EMA-3 smoothed). Both range -100 (extreme low) to 0 (extreme high).
- **Overbought**: both fast and slow %R ≥ -threshold (default threshold 20, so ≥ -20).
- **Oversold**: both fast and slow %R ≤ -(100-threshold) (≤ -80).
- **Bearish exhaustion (▼)**: price *was* overbought, now isn't — the up-move that pushed it there is exhausted. Sell/caution signal.
- **Bullish exhaustion (▲)**: price *was* oversold, now isn't — the down-move is exhausted. Buy/reversal signal.
- Requiring *both* the fast and slow line to agree filters out the fast line's whipsaws — the slow (112-period) line acts as a regime filter on top of the fast line's timing.

## Variants / Parameters

- Threshold: 20 (default) — lower values (tighter zone) = fewer, higher-conviction signals; higher values = more signals, more noise.
- Smoothing type: EMA (default) or SMA in this project's ports; the original Pine script also offers HMA/RMA/WMA/VWMA/SWMA/linreg/median/mom/percentrank — not ported (diminishing returns vs. added complexity).
- "Average formula" mode (average the fast/slow lines into one, apply zone logic to the average) exists in the original script — not ported; the two-line AND-gate is the version implemented here.

## Common Mistakes

- Treating the *entry* into the zone (the "trend warning" square marker) as the trade signal — it isn't; the *exit* (the arrow) is the actual reversal signal. Entering a zone means the trend is extended, not that it's over.
- Using this in isolation. Per the real-world example below, the reliable version of this signal is *confirmed by* other structure (price recovering above a key MA, RS turning up) — not fired alone.

## Examples in This Wiki

- [dashboard_app.py](../../tools/dashboard_app.py) — "High-Growth Screener" page uses `compute_recent_exhaustion_signal` to flag a bullish/bearish signal within the last 3 bars per stock.
- [chart_dashboard.html](../../tools/chart_dashboard.html) — live oscillator pane via `percent_r_trend_exhaustion.js`, with the same fast/slow lines and reversal-arrow markers.
- [[sources/TradingView-Goodyear-PMax-Strat-Confluence-2026]] — real-world validation: the indicator fired a clean bullish exhaustion right at a multi-month low on Goodyear India, ahead of a fresh Wave 1-2 impulse.

## Related Concepts

- [[concepts/RSI]] — same overbought/oversold family of oscillator, different formula (RSI uses average gain/loss, %R uses position within the high/low range)
- [[concepts/ADX]] — a trend-strength filter that pairs naturally with this: exhaustion signals during a *strong* trend (high ADX) are lower-conviction reversal calls than ones during a *weakening* trend
- [[concepts/Stage-Analysis]] — a bullish exhaustion signal forming near a stock's lows is one candidate confirming signal for a Stage 1→2 transition (see the early-buy-detector discussion in the same ingest)
- [[concepts/Reversal-Chart-Patterns]] — that pattern-detector's "exhaustion context" score component is a lightweight, single-bar cousin of this full oscillator; its Follow-Through Proof mechanism (grade each signal against real forward price action at a fixed horizon) is a generic idea worth porting back onto this indicator's own signals

## Sources

- [[sources/TradingView-Goodyear-PMax-Strat-Confluence-2026]] (2026-07-02)
