---
title: "SwingEdge — SIGMA Stock Detail Page"
category: source
tags: [swing-trading, technical-analysis, scanner, stage-4, distribution-days, overhead-supply, low-liquidity, weak-setup]
created: 2026-06-22
updated: 2026-06-22
sources: 1
related: [entities/SIGMA, entities/INDSWFTLAB, entities/AADHARHFC, concepts/Distribution-Days, concepts/Stage-Analysis, concepts/Market-Structure-CHOCH-BOS]
---

# Source — SwingEdge.info Stock Detail Page (SIGMA)

## Metadata
- **Source type**: Swing-trading scanner/setup web app, same source as the 5 prior stock-detail ingests
- **URL**: https://www.swingedge.info/stocks/SIGMA
- **Snapshot date**: 2026-06-21

## Key Takeaways
- Sigma Solve Ltd. (BPO/ITeS) is the **weakest setup ingested from this source so far**: setup readiness **0.0/100** ("Late Stage"), verdict **"Caution — weak structure,"** decision-quality grade **D, 4/100 — "Low-quality — likely skip."** Every prior ticker (KDDL, NRBBEARING, AADHARHFC, INDSWFTLAB) scored at least 55+ on setup readiness and at least a C grade; this is the first D and the first 0.0 score.
- **In Stage 4** (confirmed decline phase, not Stage 2) — the first ticker ingested from this source explicitly *failing* the Stage-2 gate rather than passing it. Directly exercises the bearish/inverse Stage framework documented in [[concepts/Distribution-Days]] from the Downside Risk screener ingest.
- **5 skip reasons — tied with INDSWFTLAB's 4, now the new high-water mark**: thin liquidity (₹0.3 Cr/day — slippage risk), 7 distribution days recently, heavy overhead supply (73%), elevated failure risk (66/100), not in Stage 2 (Stage 4).
- **Three genuinely new metric types not seen on any prior ticker**:
  1. **Liquidity in absolute ₹ terms** ("Thin liquidity (₹0.3 Cr/day) — slippage risk") — prior tickers never had a liquidity/turnover flag at all; this is the first stock small/illiquid enough to trigger it.
  2. **Overhead supply %** ("Heavy overhead supply (73%) — trapped sellers above") — quantifies what fraction of the price-volume profile above current price represents stuck/underwater holders likely to sell into any rally. Worth treating as a concrete, citable concept alongside [[concepts/Distribution-Days]]' support-loss/distribution formulas.
  3. **Explicit numeric "failure risk" score** ("Elevated failure risk (66/100)") — a single composite probability-of-failure number, distinct from (and additional to) the setup-readiness score and the decision-quality grade. This is now a third, separate scoring dimension confirmed on this source (readiness score, decision-quality grade, failure-risk score).
- Despite the overwhelmingly bearish framing, the page still lists "VCP-style base with 7 contraction(s) — supply appears to be fading" and "ATR shrinking 3 consecutive weeks — coil forming" under bullish factors — i.e. the *pattern* (VCP, compression) is present even in a structurally weak, Stage-4 stock. This reinforces the lesson from [[entities/INDSWFTLAB]]: pattern tags (VCP, coiling, BB squeeze) describe shape, not quality or trend context — a textbook-shaped base can occur during a downtrend continuation just as easily as before an uptrend breakout.
- Risk/Reward still computed and shown as a respectable 2.4:1 despite the D grade — confirms R:R math is calculated independently of, and does not gate, the overall quality verdict on this source.
- Sector RS again tagged "Lagging group" — and here, unlike KDDL/NRBBEARING, individual RS (38, "lagging") agrees with the sector tag — third data point (after AADHARHFC) of stock-RS and sector-RS agreeing rather than diverging, keeping the running tally at roughly half-and-half across the 6 tickers ingested so far.

## Detailed Notes

**Setup snapshot (as of 2026-06-21):**
- Price: ~₹38.7 (well below the stated entry zone ₹44.0–48.6 — "Building toward the pivot, 20% below" per the Why Now panel, i.e. price hasn't even reached the scanner's reference entry zone yet, the opposite extreme from INDSWFTLAB which had already blown through its pivot)
- Entry zone: ₹44.0–48.6; Resistance/pivot: ₹48.4; Next resistance: ₹58.1
- Support/stop: ₹44.8 — notably, the stop (₹44.8) is *above* the current price (₹38.7) here, an unusual structural quirk worth flagging: the invalidation panel states "wrong below ₹44.8 (-15.7% away)" with a *negative* distance, meaning price is already below its own stated stop level. This likely reflects the entry zone being a forward-looking "if it gets there" reference rather than a live actionable trade right now — worth treating any SwingEdge entry/stop pair with a negative risk-distance sign as informational/aspirational, not an active setup.
- RS 38 ("lagging"), ADX 9 ("weak/choppy" — the lowest ADX of any ticker ingested so far, well below NRBBEARING's 51 or even AADHARHFC's 15), Volume score 22 (also the lowest seen)

**Bullish factors listed** (continuing the now-fully-confirmed pattern across all 6 tickers: this card mixes true positives with explicit penalties): price near 52-week low (penalty, framed as "recovery risk elevated"), MACD below zero (-2, penalty), price below 50DMA (penalty), price distant from pivot (penalty), RSI 38 weak (penalty) — notably, on this ticker the "bullish factors" card is *majority negative-framed items*, the most lopsided ratio of any ticker ingested, suggesting the card's title becomes increasingly misleading the weaker the overall setup is.

**Why not 100**: RS rank below elite band; volume quality not top-confirmation; **Stage-2 trend confirmation incomplete** (a new why-not-100 reason not seen on prior tickers, since this is the first ticker that fails Stage 2 entirely rather than just lacking elite RS).

## Actionable Insights
- **Overhead supply %** and **explicit failure-risk score** are two new, well-defined metrics worth formalizing in [[concepts/Distribution-Days]] or a new concept page the next time a ticker with these metrics populated is ingested with enough examples to generalize the formula (this page didn't state the underlying calculation, just the output numbers).
- The negative-risk-distance quirk (stop above current price) is a useful general caution: always sanity-check whether a SwingEdge entry/stop pair represents a live, actionable setup or a forward-looking "if price reaches the zone" reference — don't assume every stock-detail page describes a trade that can be entered today.
- This ticker is a clean negative-control example for the wiki: confirms the source's scoring system correctly identifies and heavily penalizes a genuinely weak, Stage-4, illiquid, distribution-heavy stock — useful as a calibration reference when judging how seriously to take a "Strong"/"Workable" verdict on other tickers, since the system clearly does differentiate rather than rating everything moderately positive.

## Contradictions with Existing Wiki
- None. Reinforces existing concepts (Stage Analysis inverse = Stage 4, distribution days, the recurring "bullish factors card includes penalties" UI quirk) with a clean, unambiguous negative example.

## Pages Updated
- Created [[entities/SIGMA]]
- This source page
