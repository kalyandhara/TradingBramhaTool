---
title: "SwingEdge — RELAXO Stock Detail Page"
category: source
tags: [swing-trading, technical-analysis, scanner, internal-contradiction, overhead-supply, microcap]
created: 2026-06-22
updated: 2026-06-22
sources: 1
related: [entities/RELAXO, entities/SIGMA, entities/INDSWFTLAB, concepts/Stage-Analysis, concepts/Distribution-Days]
---

# Source — SwingEdge.info Stock Detail Page (RELAXO)

## Metadata
- **Source type**: Swing-trading scanner/setup web app, same source as the 6 prior stock-detail ingests
- **URL**: https://www.swingedge.info/stocks/RELAXO
- **Snapshot date**: 2026-06-22

## Key Takeaways
- **The page directly contradicts itself on Stage/MA position — the first clear internal-consistency bug found across 7 SwingEdge ingests.** The FAQ schema states: *"RELAXO is in a confirmed Stage 2 uptrend, trading above its rising 50- and 200-day moving averages."* But the on-page "Bullish factors" list states: *"Price trades below the long-term trend anchor (200DMA)"* — the literal opposite claim, on the same page, same snapshot date. The Context & regime panel separately tags "Trend stage: Stage 2 — tradable," siding with the FAQ's claim, which makes the bullish-factors line look like a stale/mismatched data pull rather than a genuine signal. **Treat any single bullet inside the bullish/risk factor lists as lower-confidence than the structured Context & regime panel or the FAQ schema until this is resolved** — this is a stronger caution than the previously-noted "bullish card includes penalties" quirk, since this is an actual factual contradiction, not just a framing inconsistency.
- A second, milder mismatch: the page's own `<meta description>` summarizes the stock as **"Weak"** while the on-page verdict header reads **"Wait and Watch"** and the status pill reads **"Early Trend."** Three different one-word/short-phrase summaries of the same setup on the same page — worth noting that the meta-description summary field appears to lag or diverge from the live verdict shown in the body.
- **Setup readiness 34.0/100** — among the lowest scores seen (above SIGMA's 0.0, well below KDDL/NRBBEARING), with decision-quality grade **C, 46/100 — "Mixed, needs patience."**
- **2 skip reasons**: stop 9% away (too wide), heavy overhead supply 68% ("trapped sellers above") — the overhead-supply metric type first seen on SIGMA, now confirmed on a second ticker.
- RS rank 48 ("lagging") with sector RS also tagged "Lagging group" — both agree (no leader-in-laggard-sector divergence here), consistent with the roughly-50/50 split already observed across prior tickers on this pattern.
- ADX 35 ("strong" trend) despite the otherwise weak setup — a reminder that trend strength (ADX) and setup quality/decision-grade are independent dimensions; a stock can have a strong-trending ADX reading while still scoring poorly overall.
- Classified "microcap" in the meta description despite RELAXO being a well-known, multi-decade-listed footwear brand (Relaxo, Sparx, Flite) — a reminder that SwingEdge's cap-banding doesn't necessarily track brand recognition or business maturity, only current market cap.
- Tags: Stage 2, VCP active, Vol compression — same pattern-presence tags seen on stronger and weaker tickers alike, reinforcing that these describe chart shape, not quality (per the lesson already drawn from INDSWFTLAB and SIGMA).

## Detailed Notes

**Setup snapshot (2026-06-22):**
- Price: ₹356.2; Entry zone ₹357.0–369.3; Resistance/pivot ₹367.4 (price ~3% below it — still building toward it, not yet extended)
- Support/stop: ₹336.9; Next resistance ₹440.9; further target ₹510.6
- Risk/Reward 2.2:1; risk ≈ ₹32.44/share from entry ₹369.3; risk distance 8.8% to stop (~1.9× ATR)

**Bullish factors listed** (continuing the now-fully-established pattern: this card mixes true positives, penalties, and — in this case — an outright contradiction): price below 200DMA (the contradiction, see above), moderate distance from 52w high (-32%, ambiguous framing), RS below leadership threshold (penalty), price approaching pivot, RSI 62 "ideal setup zone," constructive advance from 52w low, VCP-style base with 4 contractions, volatility compression, volume contracting, recent volume expansion, quiet institutional accumulation.

**Why not 100**: RS rank below elite band; volume quality not top-confirmation — same two reasons seen on most prior tickers.

## Actionable Insights
- This is the clearest evidence yet that individual bullet items in the Bullish/Risk factor cards can be **factually wrong**, not just oddly categorized — escalate from "read each bullet individually" (the prior guidance) to "cross-check any single bullet against the Context & regime panel or FAQ schema before trusting it," since those two appear to be more reliable/structured than the free-text bullet lists.
- Overhead-supply percentage is now confirmed on 2 of 7 tickers (SIGMA 73%, RELAXO 68%) as a real, recurring metric — worth treating as a standard field to watch for on future ingests, alongside distribution-day counts and liquidity figures.

## Contradictions with Existing Wiki
- None with prior wiki content — but a genuine, internal, page-level contradiction within this source itself (see Key Takeaways). Worth keeping in mind as a general reliability caveat for this source going forward, not specific to RELAXO.

## Pages Updated
- Created [[entities/RELAXO]]
- This source page
