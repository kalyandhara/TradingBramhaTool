---
title: "Crash-Proof 3-Filter System (Market Health + Stage + Ownership)"
category: strategy
tags: [system, market-health, stage-analysis, ownership-flow, fpv, minervini, trend-following, gate-stack]
timeframe: swing
bias: neutral
created: 2026-07-21
updated: 2026-07-21
sources: 1
related:
  - sources/Crash-Proof-Market-Health-Ownership-Framework.md
  - concepts/FPV-Flow-Price-Volume-Ownership.md
  - concepts/Stage-Analysis.md
  - strategies/Minervini-SEPA.md
  - analyses/Decision-Support-Gating-Roadmap.md
---

# Crash-Proof 3-Filter System

## Core Idea

A **gate stack**, not a scorer: three filters that can each only *veto* a trade. You act only when **all three align**. The design goal is capital preservation first — the market-health gate alone is claimed to remove ~80% of avoidable losses by keeping you flat in hostile regimes. This is [[strategies/Minervini-SEPA]] discipline (regime → stage → confirmation) with an explicit ownership-flow leg added.

## Setup Criteria

Three filters, evaluated in order. A trade requires **A pass AND B pass AND C pass**.

### Filter A — Market health (evaluate first; it can cancel the whole day)
Five conditions:
1. Nifty above 50 EMA
2. Breadth positive
3. Breakouts working (recent breakouts holding)
4. Leaders strong
5. Volatility low

**Gate: if 2 or more fail → STAND DOWN. No trades today, regardless of B and C.**

### Filter B — Stock health (stage filter)
- Price above 50 EMA
- Strong volume
- Confirmed **Stage 2** (see [[concepts/Stage-Analysis]] — the 8-point trend template)
- Leadership returning

**Gate: below 50 EMA or not Stage 2 → skip the name.**

### Filter C — Ownership flow (structural)
- FII increasing
- MF stable or increasing
- Retail decreasing
- DII stable

**Gate: MF selling into a weak market → avoid. FII accumulation into a weak market → watchlist only, not a buy.**

## Entry Rules
- All three filters pass **and** [[concepts/FPV-Flow-Price-Volume-Ownership]] confirms (Price↑ + Volume↑ + FII↑ = strongest).
- Only **buy breakouts** once the name is in Stage 2. Never buy a base or a downtrend, however good the ownership picture.
- **Market-strong + FII-increasing** is the one configuration that permits high-conviction breakout entries.

## Exit Rules (profit target + stop loss)
- **Stop:** below the Stage-2 base / breakout pivot (structure break), consistent with the wiki's [[concepts/Stage-Analysis]] stage-transition signals.
- **Regime exit:** if the market-health gate flips to STAND DOWN (2+ conditions fail) while in a position, tighten or go to cash — the crash-proof flow is `market weakens → breakdown → go to cash → wait → new Stage 2 → attack`.
- **Ownership exit:** MF/FII rotation turning (FII decreasing, retail increasing) removes the structural support even if price hasn't broken yet — reduce.

## Timeframe
Swing / position. Ownership data is quarterly, so the system's structural leg turns slowly; price/volume/stage legs are daily.

## Best Market Conditions
Trending market (Nifty in a clear Stage 2), low volatility, positive breadth, with visible FII accumulation in leadership names.

## Worst Market Conditions
- Choppy / high-volatility markets — the market-health gate should keep you out, and this is the whole point.
- **Weak market + MF selling** — explicitly the "avoid entirely" quadrant; deeper corrections tend to follow.

## Backtest / Track Record
**Not backtested.** The "prevents 80% of losses" and "FIIs buy early in corrections" claims are the source author's, unmeasured here. Flagged for the backtest harness in [[analyses/Dashboard-UI-Roadmap]] Phase 3. Treat as a disciplined framework, not a validated edge, until measured.

## Examples
- **MCX** (the source's worked example): if below 50 EMA → no trades; breakdown with MF selling → stay out; base-building while FII accumulate → watch closely; enters Stage 2 → buy breakouts only.

## Related Concepts
- [[concepts/FPV-Flow-Price-Volume-Ownership]] — the confirmation layer.
- [[concepts/Stage-Analysis]] — Filter B.
- [[strategies/Minervini-SEPA]] — the parent methodology.
- [[concepts/Order-Flow]] — related flow-reading discipline.

## Sources
- [[sources/Crash-Proof-Market-Health-Ownership-Framework]]
