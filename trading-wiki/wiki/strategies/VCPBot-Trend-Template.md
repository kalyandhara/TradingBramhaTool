---
title: "Minervini Trend Template (8 Conditions)"
category: strategy
tags: [Minervini, trend-template, RS-rank, swing, US-markets, scan-filter, stage2]
timeframe: swing
created: 2026-06-14
updated: 2026-06-15
sources: 2
related:
  - concepts/VCP.md
  - concepts/Stage-Analysis.md
  - strategies/Minervini-SEPA.md
  - analyses/VCPBot-Architecture.md
  - concepts/EMA.md
  - sources/Minervini-Think-Trade-Champion.md
---

# Minervini Trend Template (8 Conditions)

> **Correction**: Prior wiki listed 7 conditions. Minervini's book specifies 8 criteria — the original omitted: (7) RS rank ≥70 with RS line in uptrend ≥6 weeks, and (8) price above 50-day as stock emerges from a base. The VCPBot implementation handles (7) via its separate RS Rank dual-gate and implicitly satisfies (8) via the Trend Template Close>SMA50 condition.

## Purpose
Pre-filter that all stocks must pass before VCP detection runs. Ensures you are only buying stocks in a confirmed uptrend with institutional-quality price structure.

## The 8 Conditions (ALL must be true)

| # | Minervini Criterion | VCPBot Implementation |
|---|--------------------|-----------------------|
| 1 | Close > SMA150 AND Close > SMA200 | Close > SMA150 AND Close > SMA200 |
| 2 | SMA150 > SMA200 | SMA150 > SMA200 |
| 3 | SMA200 trending up ≥1 month | SMA200 slope > 0 over last 30 days |
| 4 | SMA50 > SMA150 AND SMA50 > SMA200 | SMA50 > SMA150 AND SMA50 > SMA200 |
| 5 | Price ≥25% above 52-week low | Close ≥ 52-week low × 1.30 (30%) |
| 6 | Price within 25% of 52-week high | Close ≥ 52-week high × 0.75 |
| 7 | RS rank ≥70 (prefer 90s); RS line uptrend ≥6 weeks | RS Rank dual-gate (separate module; peak RS and current RS ≥80th percentile) |
| 8 | Price above 50-day as stock emerges from base | Close > SMA50 (implicit via condition 4 + Pass 3 micro entry) |

## Why Each Matters
- **Conditions 1–5** ensure the MA stack is properly aligned: SMA50 > SMA150 > SMA200, all sloping up, price above all of them. This is the "MA rainbow" of a healthy uptrend.
- **Condition 6** (≥30% above 52w low) confirms the stock has already made a significant move — you're not buying a base on a falling stock.
- **Condition 7** (within 25% of 52w high) ensures you're buying strength, not a value trap. Stocks near their high are there for a reason.

## Phase 2 Hard Gates (Applied First)
Before the Trend Template runs, stocks must pass:
1. 50-day avg daily volume > 1,000,000 shares (liquidity)
2. Close > $10 (no penny stocks)
3. Close > SMA200 (basic trend filter)

## RS Rank Filter (Applied After Trend Template)
RS Raw = 0.4 × ROC63 + 0.2 × ROC126 + 0.2 × ROC189 + 0.2 × ROC252

Dual-gate:
- **Peak RS** in trailing 60 days ≥ 80th percentile
- **Current RS** ≥ 80th percentile

The peak RS gate prevents buying a formerly strong stock that has recently lost relative strength — even if it still technically passes the trend template.

## Indian Market Adaptation Notes
VCPBot is built for US markets (Alpaca, yfinance, USD). For Indian markets (NSE/BSE):
- Replace SMA200 with equivalent EMA200 (more responsive to Indian volatility)
- Replace 52-week high/low with Nifty-relative RS rank
- Screener.in TechnoFunda query approximates Conditions 1–5: Price > DMA50 AND DMA50 > DMA200
- The full 7-condition template is stricter — the Screener query is a subset

## Stage 2 Context

This Trend Template is designed to confirm a **Stage 2 uptrend** — see [Stage-Analysis](../concepts/Stage-Analysis.md). Minervini found that >95% of superperformance stocks made their gains while in Stage 2.

## Related
- [[concepts/VCP]] — Setup detected after this filter passes
- [[concepts/Stage-Analysis]] — The stage framework this template confirms
- [[strategies/Minervini-SEPA]] — The full trading system
- [[analyses/VCPBot-Architecture]] — Where this fits in the pipeline
- [[strategies/TechnoFunda-Swing]] — Indian market approximation

## Sources
1. VCPBot GitHub repo
2. [Minervini-Think-Trade-Champion](../sources/Minervini-Think-Trade-Champion.md) — Section 6; Trend Template criteria quoted verbatim
