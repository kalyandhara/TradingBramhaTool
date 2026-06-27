---
title: "Stage Analysis"
category: concept
tags: [stage-analysis, trend, minervini, sepa, market-cycle, stage2]
created: 2026-06-15
updated: 2026-06-19
sources: 3
related:
  - strategies/Minervini-SEPA.md
  - concepts/VCP.md
  - strategies/VCPBot-Trend-Template.md
  - sources/Minervini-Think-Trade-Champion.md
  - strategies/False-Break-Buildup-Trading.md
  - sources/Price-Action-Trading-MTF-Brandon-Kenny-2023.md
---

# Stage Analysis

## Definition

Stage Analysis describes the four distinct phases a stock cycles through during its life cycle. Originally popularized by Stan Weinstein and adopted by Mark Minervini as a core filter in his SEPA methodology, it defines **where** a stock is in its price cycle — not just what pattern it is forming.

> "More than 95 percent of stocks that made huge price gains while in a Stage 2 uptrend." — Minervini

## The Four Stages

| Stage | Name | Description | Action |
|-------|------|-------------|--------|
| **1** | Neglect / Consolidation | Stock trades sideways after a prior decline; no institutional interest; low volume; 200-day MA flat or still declining | Watch only; accumulation phase beginning |
| **2** | Advancing / Accumulation | Stock in a clear uptrend; price > all major MAs; MAs in correct order; 50-day > 150-day > 200-day; 200-day trending up | **BUY ONLY HERE** |
| **3** | Topping / Distribution | Stock begins to stall near highs; bases become wide and loose; volume on down days increases; 50-day starts to flatten or cross below 150-day | Exit long positions; do not initiate new longs |
| **4** | Declining / Capitulation | Stock in a clear downtrend; price below 200-day; 200-day trending down; serial gappers common | Short opportunities; avoid longs entirely |

## How to Use

### Stage 2 Identification Checklist (Minervini Trend Template)

All 8 criteria must be met to confirm a Stage 2 uptrend:

1. Price above both 150-day (30-week) and 200-day (40-week) moving averages
2. 150-day MA above 200-day MA
3. 200-day MA trending up for at least 1 month (preferably 4–5 months)
4. 50-day (10-week) MA above both 150-day and 200-day
5. Current price at least 25% above its 52-week low
6. Current price within 25% of its 52-week high (closer to high = better)
7. Relative Strength (RS) rank ≥70 (preferably 90s); RS line in uptrend for ≥6 weeks
8. Price trading above 50-day MA as stock emerges from a base

**If ANY criterion fails → stock is NOT in a confirmed Stage 2 → skip it.**

### Stage Transition Signals

- **Stage 1 → 2**: Volume picks up meaningfully; 50-day crosses above 200-day; RS line turns up; price makes higher highs
- **Stage 2 → 3**: First base fails; stock forms wide-and-loose consolidation; heavy distribution on up days; RS line deteriorates
- **Stage 3 → 4**: Price closes below 50-day on heavy volume; 200-day begins to roll over; serial gaps lower begin

## Variants / Parameters

- **Base count within Stage 2**: Bases 1–2 = prime buying; Bases 3–4 = OK, treat as trading opportunity; Bases 5–6 = extremely failure-prone, sell into breakouts
- **Serial gappers**: Stocks in Stage 4 often gap down repeatedly — buying these is extremely high risk
- **Stage 1 leaders**: Some stocks bottom in Stage 1 before general market; they lead the next Stage 2 advance

## Common Mistakes

1. **Buying Stage 4 stocks that look "cheap"** — falling stocks appear cheap but are usually expensive; 50/80 Rule applies
2. **Confusing Stage 1 consolidation for Stage 2** — volume and MA direction confirm the difference
3. **Holding through Stage 3** — distribution is hard to see; base counting and P/E expansion flag it
4. **Missing early Stage 2 entries** — stocks always look "expensive" at the start of Stage 2; this is intentional
5. **Bottom-fishing in Stage 4** — even one more leg down can cause catastrophic loss

## Plain-Language Variant (Brandon's 4 Stages)

[Price-Action-Trading-MTF-Brandon-Kenny-2023](../sources/Price-Action-Trading-MTF-Brandon-Kenny-2023.md) restates the same 4-stage cycle (Accumulation/Advancing/Distribution/Declining) using only the 200-day MA as a gate, without Minervini's 8-criterion precision:

| Stage | 200-day MA behavior |
|---|---|
| 1. Accumulation | Flattening; price whips around it |
| 2. Advancing | Sloping up, price above |
| 3. Distribution | Flattening; price whips around it |
| 4. Declining | Sloping down, price below |

Key addition: in Stages 1 and 3 (direction undetermined), trade the range edges with [[strategies/False-Break-Buildup-Trading]] (false breaks, buildup breakouts) rather than waiting for stage confirmation — and the same cycle repeats fractally at lower timeframes (a daily distribution stage can look like a head-and-shoulders top on the 4H chart).

## Related Concepts

- [VCP](VCP.md) — the specific entry pattern within Stage 2
- [Minervini-SEPA Strategy](../strategies/Minervini-SEPA.md) — the full framework built around Stage 2
- [VCPBot Trend Template](../strategies/VCPBot-Trend-Template.md) — automated implementation of 8-criterion filter
- [[strategies/False-Break-Buildup-Trading]] — discretionary entries for Stage 1/3 ranges where direction isn't yet confirmed
- [[concepts/Distribution-Days]] — SwingEdge's "bearish DMA stack" (faster MAs under slower, negative slopes) is explicitly the mirror image of the Stage 2 trend template here, i.e. Stage 4/decline; distribution-day clustering is one of its composite-score inputs

## Examples in This Wiki

- Most large Indian multibagger moves (e.g., JAYBARMARU, sector leaders) share Stage 2 characteristics
- VCPBot's 7-condition Minervini filter approximates Stage 2 (now updated to 8 criteria)

## Haseeb Badar's 6-Filter Framework (Simplified Stage 2 Check)

[@hb_stocks](../sources/HB-Stocks-6-Filters.md) distilled a visually-oriented "rejection filter" version of Stage 2 into 6 sequential filters:

| Filter | Description | Equivalent Stage 2 Criterion |
|--------|-------------|------------------------------|
| Linear Mover | Higher highs, higher lows, clean structure | Stage 2 uptrend definition |
| Near 52-Week High | Price within striking distance of highs | Criterion 6 (within 25% of 52W high) |
| High ADR | Daily range % large enough to cover stop + profit | Not in Minervini — additional filter |
| Above 20/50/150/200 MAs | Full MA alignment | Criteria 1, 2, 4 |
| Quality Consolidation | Controlled base, volume dry-up, tight structure | VCP base (entry trigger within Stage 2) |
| Good Volume Activity | Strong on up days, light on pullbacks | Institutional accumulation signal |

Key philosophy: **these are rejection filters, not entry signals**. A stock failing any single filter is immediately eliminated — don't waste analysis time on it. See [HB-Stocks-6-Filters](../sources/HB-Stocks-6-Filters.md) for ADR screener formula and full notes.

**ADR filter addition** (new vs. Minervini): Filter 3 requires `ATR(14)/Close > 2%` (or 1.5% for longer holds). This prevents low-volatility stocks from passing the trend filter despite inadequate daily range to generate meaningful returns per unit of time.

## Sources

1. [Minervini-Think-Trade-Champion](../sources/Minervini-Think-Trade-Champion.md) — Sections 6, 7, 9; Stage definitions and 8-criterion template
2. [HB-Stocks-6-Filters](../sources/HB-Stocks-6-Filters.md) — Slide 1/7; visual rejection-filter framework (slide 1 only)
3. [Price-Action-Trading-MTF-Brandon-Kenny-2023](../sources/Price-Action-Trading-MTF-Brandon-Kenny-2023.md) — Chapter 2; plain-language 4-stage variant gated on 200-day MA only
