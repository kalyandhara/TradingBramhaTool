---
title: "Multi-Timeframe (MTF) Analysis"
category: concept
tags: [multi-timeframe, regime, weekly-daily-intraday, alignment]
created: 2026-06-22
updated: 2026-06-22
sources: 1
related: [concepts/ADX, concepts/MACD-Divergence, concepts/Stage-Analysis, sources/Price-Action-Trading-MTF-Brandon-Kenny-2023, sources/SwingEdge-Learn-Process-Risk-Workflow]
---

# Multi-Timeframe (MTF) Analysis

## Definition
The discipline of reading at least two — ideally three — timeframes before committing capital, because a chart pattern's follow-through probability depends heavily on what the larger timeframe is doing, even when the pattern itself looks identical. A daily breakout on a stock whose weekly is rolling over has a completely different base rate than the same daily breakout on a stock whose weekly is coiling up.

## How to Use

### The three-timeframe template
| Timeframe | Job | What to read |
|---|---|---|
| **Weekly** | Regime & bias | Position vs. 30/50-week MA, slope of that average, weekly HH/HL sequence, weekly RSI above/below 50, weekly MACD position vs. zero |
| **Daily** | Setup & structural level | Base shape, pivot location, MA stack, invalidation level |
| **Intraday** (60-min or 15-min) | Trigger & timing | When the breakout actually happens; is volume confirming |

### Alignment rules of thumb
- All three agree → high-quality setup; size up within your risk plan.
- Weekly + daily agree, intraday is muddy → still tradeable, but use intraday for trigger only, not for thesis.
- Weekly + daily disagree → skip, or size very small — you're fighting one of them no matter which way you trade.
- **The most common trap**: daily setup looks great but the weekly is rolling over. Pretty daily charts inside a deteriorating weekly tape fail repeatedly.

### Why one timeframe alone can mislead
A daily chart can look bullish in isolation while the weekly shows a clear topping pattern about to break — the daily breakout might even close strong and still mark the high of the move, because the weekly is dictating the bigger picture. The reverse also holds: a weak-looking daily can be a normal pullback inside a strong weekly uptrend, where the correct trade is to buy it, not avoid it.

### MTF for exits, not just entries
A trailing stop should respect the timeframe that produced the entry. A daily-entry swing trade shouldn't be exited on a 15-minute wobble — use intraday for trigger management ("is the move continuing today?") and daily for the stop trail ("is the swing structure intact?"). Mismatching entry and exit timeframes is a common, avoidable source of premature stop-outs.

## Common Mistakes
- **Timeframe shopping** — flipping through 5m/15m/60m/daily/weekly until one of them confirms what you already wanted to do.
- Using too many timeframes — five charts of the same stock at different intervals is noise; three is the practical sweet spot.
- Mismatching entry and exit timeframe (see above).
- Forgetting the index — even with perfect MTF alignment on the stock itself, an index-level breakdown can override an individual setup overnight.

## Related Concepts
- [[concepts/ADX]] — the two-level (stock + index) ADX regime filter is a specific case of this same top-down logic
- [[concepts/MACD-Divergence]] — the weekly-regime/daily-setup/intraday-trigger MACD template applies this framework to one specific indicator
- [[concepts/Stage-Analysis]] — weekly Stage context (e.g. confirmed Stage 2 on the weekly) is the regime layer this framework asks you to check before trusting a daily pattern
- [[sources/Price-Action-Trading-MTF-Brandon-Kenny-2023]] — prior wiki coverage of HTF-buildup + LTF-false-break entries, a related but distinct MTF application focused on entry timing rather than regime/setup/trigger layering
- [[concepts/Volume-Profile]] — the volume-structure application of this framework (added 2026-07-03): profiles per timeframe stacked side by side, reading POC/value-area confluence across timeframes instead of trend alignment

## Sources
- [[sources/SwingEdge-Learn-Process-Risk-Workflow]] (2026-06-22) — three-timeframe template, alignment rules, MTF-for-exits rule
