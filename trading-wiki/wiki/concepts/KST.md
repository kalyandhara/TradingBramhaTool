---
title: "KST — Know Sure Thing Indicator"
category: concept
tags: [momentum, oscillator, Martin-Pring, ROC, trend-reversal]
created: 2026-06-14
updated: 2026-06-14
sources: 1
related: [concepts/RSI.md, concepts/ADX.md, concepts/MACD-Divergence.md]
---

# KST — Know Sure Thing Indicator

## Definition
Momentum oscillator by Martin Pring. Measures rate-of-change (ROC) across multiple timeframes to identify major trend reversals. Similar to MACD but uses ROC instead of price MAs.

## Formula Concept
```
KST = (ROC1 × 1) + (ROC2 × 2) + (ROC3 × 3) + (ROC4 × 4)
```
Where ROC1–4 = rate of change over different periods (e.g., 10, 15, 20, 30 days).
Then smoothed with a signal line (moving average of KST).

## Interpretation Table
| Condition | Meaning | Signal |
|-----------|---------|--------|
| KST crosses above signal line | Momentum turning bullish | Buy / upside reversal |
| KST crosses below signal line | Momentum turning bearish | Sell / downside reversal |
| KST rising above zero | Long-term uptrend confirmed | Bullish strength |
| KST falling below zero | Long-term downtrend | Bearish strength |
| KST divergence vs price | Reversal warning | Early warning |

## Key Nuance (from notes)
KST cross above signal line **below zero** = only short-term pullback within downtrend.
True uptrend confirmation requires KST to rise **above zero**.

## Combine With
- RSI < 30 recovering → early reversal attempt
- Price above EMA ribbon → trend confirmation
- VPCI (Volume Price Confirmation Indicator) → accumulation signal

## Related
- [[concepts/RSI]] — Use together for reversal confirmation
- [[concepts/ADX]] — ADX for trend strength; KST for momentum direction
