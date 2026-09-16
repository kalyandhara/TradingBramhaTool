---
title: "VCPBot Risk Management System"
category: analysis
tags: [risk-management, position-sizing, regime, drawdown, portfolio]
created: 2026-06-14
updated: 2026-06-14
related: [analyses/VCPBot-Architecture.md, concepts/VCP.md, analyses/Kalyan-Trading-Philosophy.md]
sources: 0
---

# VCPBot Risk Management System

> Distilled from VCPBot source code and README

## Core Formula
```
Position size (shares) = (Account equity × Risk%) / (Pivot price − Stop price)
```

Example: ₹10L account, 2% risk, pivot ₹500, stop ₹470 (6% below pivot)
→ Risk ₹ = 10,00,000 × 2% = ₹20,000
→ Shares = ₹20,000 / (500 − 470) = 666 shares
→ Position value = 666 × ₹500 = ₹3,33,000 (33% of account in one trade)

Note: The position limit (max 5 positions, max 10% portfolio risk) would further constrain this.

## Regime-Based Risk Adjustment

| Regime | Condition | Risk Per Trade | Notes |
|--------|-----------|---------------|-------|
| NORMAL | SPY ≥ SMA200 | 2% | Full allocation |
| FTD | Day 4–7 rally, SPY/QQQ +1.5% on higher vol | 1% | Cautious re-entry |
| CASH | SPY below SMA200 | 0% (no entries) | Preserve capital |

**Key insight:** Regime isn't just a binary on/off — FTD mode is a "half position" re-entry mechanism. When market gives first signs of recovery (Follow Through Day), bot enters at half size until regime confirms.

## Portfolio-Level Hard Limits
- Max 5 simultaneous positions
- Max 2 positions in any single sector
- Max 10% of portfolio at risk across all open trades

## Trade-Level Hard Limits
- Stop ≤ 7% below pivot (if stop is wider → setup rejected in Phase 4)
- Target = +20% (fixed, bracket order)
- No entry if stock gaps >2% above pivot at open
- No entry if intraday volume < 1.5× expected at 10:30 AM

## Comparison to Kalyan's Manual Rules
| | VCPBot (Automated) | Kalyan's Manual Rules |
|--|---|---|
| Risk per trade | 2% equity | <10% of portfolio per stock |
| Market regime | SPY vs SMA200 | RSI/EMA signals |
| Stop | Low of final contraction | Lollipop low (closing basis) |
| Target | +20% fixed | Prior swing high / 1.5–2× risk |
| SME cap | N/A (US markets) | <20% portfolio |
| Max positions | 5 | Implied via % limits |

## Applicability to Indian Markets
VCPBot's risk system is market-agnostic — the math works the same for NSE/BSE stocks:
1. Replace SPY SMA200 regime with Nifty 50 SMA200
2. Use INR account value instead of USD
3. Replace Alpaca with Zerodha/Upstox Kite Connect API
4. Keep all percentage parameters identical

## Related
- [[analyses/VCPBot-Architecture]] — Where risk sizing fits in pipeline
- [[analyses/Kalyan-Trading-Philosophy]] — Manual equivalent rules
- [[concepts/VCP]] — The setup being sized
