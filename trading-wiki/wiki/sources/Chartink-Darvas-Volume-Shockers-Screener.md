---
title: "Chartink Screener — Darvas Volume Shockers (Amitabh Jha3)"
category: source
tags: [chartink, screener, volume, darvas, breakout]
created: 2026-06-15
updated: 2026-06-15
sources: 1
related: [strategies/Screener-Queries.md, concepts/Darvas-Box.md]
---

# Chartink Screener — Darvas Volume Shockers

## Metadata
- URL: https://chartink.com/screener/copy-amitabh-jha3-volume-shockers-stocks-with-rising-volumes-darvas-100
- Original author: Amitabh Jha3 (public copy, owner: Pruthvi / pruthvi-19); screener created 2022-05-03
- Category tags: Darvas, Technical Analysis Scanner
- Description (from page): "Stocks that have seen a sudden rise in their volume by over 2x times the average volume over the past 10 trading sessions and have gained or lost more than 5% today"
- Date ingested: 2026-06-15; HTML fetched via curl, `atlas_query` field extracted from embedded `scan-json` prop

## Scan Clause
Extracted from `atlas_query` (the rendered, human-readable form of `atlas_json`):

```
( {cash} ( latest volume > latest sma( volume,10 ) * 2
  and ( {cash} (   latest close > 1 day ago close * 1.05
               or  latest close < 1 day ago close * 0.95 ) ) ) )
```

**In plain English:**
1. Today's volume > 2× the 10-day simple moving average of volume (a volume spike)
2. AND (today's close is >5% above yesterday's close OR today's close is >5% below yesterday's close) — a ±5% price swing in either direction

Segment: `{cash}` — NSE/BSE cash equities only, no F&O.

## Key Takeaways
- Minimal two-condition screener: volume anomaly + significant price move. No trend filter, no indicator gate (no CCI, no RSI, no MA above/below check).
- **Bidirectional by design** — captures both big-up days and big-down days on high volume. The "Darvas" label in the original title suggests the intent is to find volume-backed moves (Darvas box breakouts are ideally big up-days on volume), but the ±5% OR logic means this screener flags panic sell-offs equally.
- Direct comparison to the existing [[strategies/Screener-Queries]] Chartink scanner #5 (Nimblr's Volume Shocker):

| Criterion | Nimblr Volume Shocker | This (Amitabh Jha3 Darvas) |
|-----------|----------------------|--------------------------|
| Volume lower bound | > 2× SMA(vol,10) | > 2× SMA(vol,10) |
| Volume upper cap | < 5× SMA(vol,10) | none |
| Price direction | any (CCI>110 gives momentum bias) | ±5% explicit (both up and down) |
| Momentum filter | CCI(34) > 110 | none |
| Price floor | close > 100 | none |
| Net effect | Momentum breakouts only, avoids blowout volume | Volume surges with big moves, incl. breakdowns |

## Actionable Insights
- Useful as a **raw activity radar** — catches anything unusual in volume + price, then requires manual filtering for direction and trend context (is the big move a breakout or a breakdown?).
- Because it has no CCI/RSI/MA filter, the false-positive rate is high. Outputs should be filtered by [[concepts/Darvas-Box]] box structure, [[strategies/VCPBot-Trend-Template]] trend-template conditions, or close > MA(200) before acting.
- **Pair with Darvas Box detection**: a stock showing up here that is also at the top of a Darvas box with a valid lollipop low stop is a high-quality setup. A stock showing up here on the down side (decline >5%) may be breaking down from a box — potential short or "avoid" signal.
- The absence of a price floor (no "close > 100") or market-cap filter means micro-caps and penny stocks appear; filter these manually.

## Contradictions with Existing Wiki
- None. This is additive to [[strategies/Screener-Queries]] (existing scanner #5 is a narrower cousin of the same concept).

## Pages Updated
- Created: wiki/sources/Chartink-Darvas-Volume-Shockers-Screener.md (this page)
- Updated: wiki/strategies/Screener-Queries.md (new Chartink scanner entry)
- Updated: wiki/concepts/Darvas-Box.md (cross-link to this screener)
- Updated: wiki/index.md, wiki/log.md
