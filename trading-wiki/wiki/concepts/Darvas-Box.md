---
title: "Darvas Box / DarvaX"
category: concept
tags: [breakout, box-theory, darvas, momentum, swing]
created: 2026-06-14
updated: 2026-06-15
sources: 2
related: [concepts/VCP.md, concepts/RSI.md, concepts/EMA.md, strategies/TechnoFunda-Swing.md, strategies/Screener-Queries.md]
---

# Darvas Box / DarvaX

## Definition
A breakout strategy where price consolidates in a "box" after a strong move, then breaks out to new highs. Developed by Nicolas Darvas; adapted by Indian traders as "DarvaX."

## DarvaX High Dry Fry Pattern
1. Stock moves **20–50% on huge volume** (the initial run)
2. **Correction of 10–20%** from peak (healthy pullback)
3. **Small baby candles cluster** together at lows (the DarvaX box — tight, low-volume consolidation)
4. Breakout from box on volume = entry

## Screener.in Query
```
100*((High price - Current price)/High price) < 10 AND
100*((High price - Current price)/High price) > 0 AND
100*(Current price / Low price - 1) > 100 AND
Current price > 10 AND
Volume > 100000
```
Link: https://screener.in/screens/4928/darvas-scan/

## Entry & Stop Loss Rules
- **Entry:** Breakout above the box on volume confirmation
- **Stop Loss:** Lollipop Low = the low of the box, on **daily or weekly closing basis** (not intraday wick)
- **Stage transition** (e.g. price reclaims key level like ₹250 → new uptrend target ₹300+)

## Combined Tools (DarvaX Toolkit)
- Darvas Box (price structure)
- RSI (momentum confirmation)
- EMA (trend filter)
- Fibonacci (target projection)
- Price Action (volume, candle quality)
- Discipline + Patience (without these, all above = garbage)

## Key Insight from Notes
"If you don't have discipline and patience, all the above is garbage."

## Common Mistakes
- Entering during the consolidation box (before breakout)
- Using intraday low as stop (must use closing basis)
- Ignoring volume on breakout candle

## Chartink Scanner
A dedicated Chartink screener for high-volume Darvas-style moves is documented in [[strategies/Screener-Queries]] (Chartink scanner #9): finds stocks with volume > 2× SMA(volume,10) AND price ±5% from prior close. Bidirectional — flags both breakouts and breakdowns; filter output by trend context (close > MA(200), box structure) before acting. Source: [[sources/Chartink-Darvas-Volume-Shockers-Screener]].

## Related
- [[concepts/VCP]] — Similar contraction-before-expansion logic
- [[concepts/RSI]] — Use RSI to confirm momentum on breakout
- [[strategies/TechnoFunda-Swing]] — DarvaX combined with fundamentals
- [[strategies/Screener-Queries]] — Chartink #9 (Darvas Volume Shockers) and Screener.in query above
