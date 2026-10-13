---
title: "Qullamaggie (Kristjan Kullamägi) — Momentum Setups"
category: strategy
tags: [momentum, breakout, episodic-pivot, parabolic-short, relative-strength, market-filter, swing]
timeframe: swing
created: 2026-10-12
updated: 2026-10-12
sources: 0
related: [concepts/High-Tight-Flag, strategies/Parabolic-Short-First-Red-Day, strategies/Opening-Range-Breakout, concepts/Breakout]
---

# Qullamaggie — Momentum Setups

## Core Idea
He trades only the strongest relative-strength leaders. Daily charts give the picture and the intraday opening range gives the entry. Holds run from days to weeks. A low win rate (he cites about 25–30%) is expected: the money comes from a few winners worth many times the risk. Risk per trade is 0.5% of the account or less. He trails winners with the 10- or 20-day MA or sells into strength. Source: an owner-pasted summary (2026-10-12) of his public material; no primary source has been ingested yet.

## The three setups

| Setup | Rule (his) | On this desk |
|---|---|---|
| **Breakout / continuation** | Prior run of 30–100%+; tight, orderly base (flag or volatility contraction) riding the rising 10/20 MA; breakout on expanding volume; entry at the opening-range high (ORH), stop at low of day | **`Qullamaggie Breakout`** scanner (`scan_qullamaggie_breakout`), daily bars |
| **Episodic Pivot (EP)** | Gap-up of 8–10%+ on a real catalyst, with a massive volume surge, in a stock that was quiet beforehand; buy the continuation, not the fade | **`Episodic Pivot`** scanner (`scan_episodic_pivot`), daily bars, earnings-calendar tag |
| **Parabolic short** | Short vertical moves (often small caps up hundreds of % in days) once exhaustion shows | Not built. See [[strategies/Parabolic-Short-First-Red-Day]] for the checklist |

**Market filter:** reduce or avoid long breakouts and EPs when the index's 10-day MA is below its 20-day. On this desk this is the **"Momentum longs ON/OFF"** line in the Home verdict card's regime strip (`market_verdict.classify_regime` → `momentum_longs`). It is reported beside the regime label and not folded into it.

## How the desk's versions differ from his
- **No intraday entry.** The desk has no intraday store. A card's entry is the daily close and its stop is that day's low, which makes it a later and wider trade than an ORH entry. The breakout card says so by giving the stop in ATR multiples. A pre-breakout card (`actionable: False`) gives the pivot as the alert level for anyone entering intraday by hand.
- **No target.** He trails, so the cards carry no target. The backtest harness measures the signal and does not simulate a plan.
- **EP catalyst.** Price cannot show the catalyst. The scanner checks the NSE result calendar and tags a hit *Earnings EP* or *Non-earnings gap*. That is a tag only, with no score bonus.
- **Confluence:** neither scanner adds a new family. The breakout votes inside Base/Contraction and the EP inside Event (with PEAD Drift), so each fact is counted once.

## Thresholds (starting points, not fitted)
Breakout: run ≥30% inside 126 sessions; base of 3–30 bars, ≤25% deep; last-5-bar range ≤80% of the range on the leg up; SMA10 > rising SMA20, with the prior close at or above the SMA20; breakout close above the base high on ≥1.5× the 20-day volume; a pre-breakout card within 3% of the pivot.
EP: gap ≥8% (open vs prior close); volume ≥3× the 50-day average; ≤25% gain over the 63 sessions before the gap; close in the upper half of the gap-day range; within 3 sessions and never undercutting the gap-day low.

## Status
**UNMEASURED** — see [[analyses/Open-Backlog#B-147]]. In a first sample of 150 NIFTY 500 names over about 3 years, every 3rd bar checked: the breakout fired on about 0.15% of bars as an actionable breakout (1.8% including pre-breakout cards), and the EP on about 0.08%. On the 2026-10-09 close, NIFTY 500 gave one hit each. Judge them by the size of their winners, not their hit rate (his own win rate is about 25–30%).
