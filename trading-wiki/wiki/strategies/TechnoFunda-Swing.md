---
title: "TechnoFunda Swing System"
category: strategy
tags: [swing, technofunda, VWAP, EMA, RSI, ADX, VCP, ATR, indian-markets]
timeframe: swing
created: 2026-06-14
updated: 2026-06-14
sources: 1
related: [concepts/VCP.md, concepts/ADX.md, concepts/Darvas-Box.md, concepts/RSI.md, strategies/Screener-Queries.md]
---

# TechnoFunda Swing System

## Core Idea
A multi-filter swing trading system combining institutional trend (VWAP), momentum (RSI), trend direction (EMA/SMA), trend strength (ADX), breakout quality (ATR), and contraction setup (VCP). Entry only when ALL conditions align.

## The 7 Required Conditions (ALL must be true)

| # | Indicator | Condition | Meaning |
|---|-----------|-----------|---------|
| 1 | VWAP | Price > VWAP | Institutions are net buyers |
| 2 | EMA20 | Price > EMA20 | Short-term trend bullish |
| 3 | SMA50 | Price > SMA50 | Medium-term trend bullish |
| 4 | RSI | RSI > 50 | Bullish momentum |
| 5 | ADX | ADX > 20 | Trend is real (not chop) |
| 6 | VCP | Volume contracting | Pre-breakout squeeze |
| 7 | ATR | Breakout candle > 0.5 × ATR | Real move, not fakeout |

## Entry Signal
BUY when all 7 conditions align on a breakout candle with volume expansion.

## Exit — Stop Loss
- Price crosses below EMA20
- OR price drops below SMA50
- OR EMA20 crosses below SMA50

## Exit — Profit Target
- Use prior swing highs as targets
- Trail stop as price extends
- Partial exit at 1:1.5 risk:reward, trail remainder

## Fundamental Pre-Filter (TechnoFunda)
Before applying TA, stocks must pass fundamental screen:
- YOY Quarterly profit growth > 20%
- YOY Quarterly sales growth > 15%
- ROE > 10%
- Public holding < 49% (room for institutional buying)
- PE < YOY Quarterly profit growth (not overvalued relative to growth)

## Screener Query (Screener.in / Chartink)
```
Market Cap > 500 AND ROE > 10 AND Public holding < 49 AND
YOY Q profit growth > 20 AND YOY Q sales growth > 15 AND
Price > DMA50 AND DMA50 > DMA200 AND
RSI 60–85 AND Volume 1W avg > 1Y avg AND
Return 1D > 2 AND Return 1W > 5 AND PE < YOY Q profit growth
```

## Best Conditions
- Bull market or sector in uptrend
- Low VIX, trending market

## Worst Conditions
- ADX < 20 (chop) — system says NO TRADE
- All 7 not aligned — do not force entry

## Related
- [[concepts/VCP]] — Contraction setup
- [[concepts/ADX]] — Trend strength filter
- [[concepts/Darvas-Box]] — Complementary breakout method
- [[strategies/Screener-Queries]] — Pre-filter queries
