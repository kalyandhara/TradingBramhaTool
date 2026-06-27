---
title: "SwingEdge — IZMO Stock Detail Page"
category: source
tags: [swing-trading, technical-analysis, scanner, momentum-continuation, overextended, distribution-days, zero-volume-score]
created: 2026-06-22
updated: 2026-06-22
sources: 1
related: [entities/IZMO, entities/NRBBEARING, entities/KDDL, entities/INDSWFTLAB, concepts/Distribution-Days, concepts/ADX]
---

# Source — SwingEdge.info Stock Detail Page (IZMO)

## Metadata
- **Source type**: Swing-trading scanner/setup web app, same source as the 7 prior stock-detail ingests
- **URL**: https://www.swingedge.info/stocks/IZMO
- **Snapshot date**: 2026-06-22
- **Scan category**: Momentum Continuation

## Key Takeaways
- IZMO Ltd. (IT - Software) scored **82.0/100 setup readiness** — among the highest seen, verdict "Watchlist-worthy setup," decision-quality grade **B, 64/100**. RS rank **100/100** (leader) and ADX **43** (strong trend) — both at or near the top of the range seen across all 8 tickers so far.
- **Volume score: 0.0** — the first ticker ingested with a literal zero on this sub-score, despite the otherwise strong RS/ADX/readiness numbers. This confirms (again) that the three meter sub-scores (RS, ADX, Vol) move independently — a stock can be a clean RS leader in a strong trend while volume quality reads at rock bottom.
- **Sector ranked #41/42 — "Lagging" — the worst sector rank of any ticker ingested from this source so far** (worse than KDDL's #26/32). Combined with IZMO's own RS 100 leadership, this is now the **third clean example** of the "individual RS leader sitting in a lagging sector" pattern first flagged on KDDL/NRBBEARING (vs. AADHARHFC/SIGMA/RELAXO, where stock RS and sector RS agreed) — running tally now roughly even across 8 tickers, reinforcing that neither pattern is the default; check each ticker's own numbers.
- **Stacked overextension/distribution risk despite the high headline score**: "Overextended 34% above MA50 (chase risk, score −2)," RSI 69 (77th percentile over 1 year), "Failure flags: Overextended, Distribution cluster," and 6 distribution days recently — four separate, overlapping bearish risk signals on a stock that nonetheless scored 82/100 and grade B. This is a clear case where the headline score and the risk-factor detail tell different stories; the "Why not 100" panel only lists one reason (volume quality), understating how many actual risk flags are present elsewhere on the same page.
- Gain stats: +9.2% over 10 days, +49.4% over 20 days — a genuinely large recent move, consistent with both the "Momentum Continuation" scan category and the overextension flag; the 20-day gain in particular is the largest seen on any ticker ingested from this source so far.
- "Day-2 confirmed (+10 pts)" — a new scoring-detail bullet not seen on prior tickers, suggesting the model gives a bonus for a breakout holding through a second confirming day rather than reversing immediately (a known continuation-quality signal, consistent with the "day-2 hold" concept already noted from the Learn-series entries lesson).
- Same recurring skip reasons as several prior tickers: stop 11% away (too wide), 6 distribution days (institutional selling).

## Detailed Notes

**Setup snapshot (2026-06-22):**
- Price: ₹1,051.8; Entry zone ₹963.5–1128.9; Resistance/pivot ₹1,123.3 (price ~6.4% below it per FAQ, still building toward it despite the "overextended above MA50" framing — these two facts coexist because the pivot and the 50-day MA are different reference levels)
- Support/stop: ₹1,001.4; Next resistance ₹1,348.0; further target ₹1,672.8
- Risk/Reward 1.7:1 — the lowest R:R ratio seen on any ticker ingested so far; risk ≈ ₹127.53/share from entry ₹1,128.9; risk distance 11.3% to stop (the widest stop-distance percentage seen yet, alongside SIGMA's structurally-odd case)

**Bullish factors listed** (same now-fully-confirmed UI pattern: mixes true positives with penalties under one heading): "Cont: -22.0% from 52wH, RSI 69" (informational), "Day-2 confirmed (+10 pts)" (positive), gain stats (positive), "Overextended 34% above MA50... score −2" (penalty, listed as bullish), RSI 69 percentile detail (informational/risk-adjacent), and "Failure flags: Overextended, Distribution cluster" (clearly a risk statement, listed under the bullish card) — this last one is the most stark example yet of a risk flag appearing under "Bullish factors."

## Actionable Insights
- The "Why not 100" panel is confirmed here to be an incomplete risk summary — it lists only "volume quality," while the bullish-factors card separately contains an overextension penalty and an explicit "Failure flags" line, and the risk-factors card adds 6 distribution days. Anyone using only the readiness score or the "why not 100" panel to gauge risk on this source would significantly underestimate it; the full picture requires reading all three sections together.
- This is now the third clean "RS leader in lagging sector" example (after KDDL, NRBBEARING) vs. three non-divergent examples (AADHARHFC, SIGMA, RELAXO) — the split across 8 tickers is roughly even, confirming this remains ticker-specific rather than systematic.

## Contradictions with Existing Wiki
- None directly, but reinforces the lesson from RELAXO's internal-contradiction finding: free-text bullet lists on this source need to be read in full and cross-checked against each other (bullish card vs. risk card vs. "why not 100" panel), not trusted individually or in isolation.

## Pages Updated
- Created [[entities/IZMO]]
- This source page
