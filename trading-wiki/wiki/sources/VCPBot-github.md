---
title: "VCPBot — GitHub Repository"
category: source
tags: [VCP, python, algo-trading, Minervini, Alpaca, swing-trading, automation, US-markets]
created: 2026-06-14
updated: 2026-06-14
author: blacckbeard4
url: https://github.com/blacckbeard4/VCPBot
related: [concepts/VCP.md, strategies/TechnoFunda-Swing.md, analyses/VCPBot-Architecture.md]
---

# VCPBot — GitHub Repository

## Metadata
- **URL:** https://github.com/blacckbeard4/VCPBot
- **Type:** Open-source Python trading bot
- **Market:** US equities (Alpaca brokerage)
- **Style:** Minervini-style VCP, long-only, daily timeframe
- **Status:** Paper trading by default (flip ALPACA_PAPER=false for live)

## Key Takeaways

1. **Full VCP automation** — 7-phase pipeline runs daily at 4:05 PM after close, placing GTC bracket orders at 9:30 AM next morning
2. **3-tier hierarchical detection** — Macro pivots (n=15) → contraction detection (n=8) → micro pivot/stop (n=3)
3. **Minervini Trend Template** — all 7 conditions must pass before VCP detection even runs
4. **RS Rank dual-gate** — peak RS ≥ 80th percentile AND current RS ≥ 80th percentile over 60-day trailing window
5. **Regime-aware risk sizing** — 2% risk in NORMAL, 1% risk in FTD (Follow Through Day) mode, no new entries in CASH mode
6. **RVOL confirmation** — at 10:30 AM, cancels order if intraday volume < 1.5× expected (prevents false breakouts)
7. **Gap filter** — cancels if stock gaps >2% above pivot at open (chasing prevention)
8. **Earnings blackout** — rejects any setup with earnings within N days
9. **Max 5 positions, max 2 per sector, max 10% total portfolio risk**
10. **Target +20%, stop ≤7% below pivot** → Risk:Reward ≥ 1:2.8

## Pages Updated
- [[concepts/VCP]] — updated with exact algorithmic detection logic
- [[analyses/VCPBot-Architecture]] — new detailed architecture page
- [[strategies/VCPBot-Trend-Template]] — new Minervini Trend Template page
- [[analyses/VCPBot-Risk-System]] — new risk management page
