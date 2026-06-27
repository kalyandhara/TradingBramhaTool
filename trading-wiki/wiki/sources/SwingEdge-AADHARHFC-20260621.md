---
title: "SwingEdge — AADHARHFC Stock Detail Page"
category: source
tags: [swing-trading, technical-analysis, scanner, vcp, stage-analysis, distribution-days, relative-strength]
created: 2026-06-22
updated: 2026-06-22
sources: 1
related: [entities/AADHARHFC, sources/SwingEdge-KDDL-20260621, sources/SwingEdge-NRBBEARING-20260621, concepts/VCP, concepts/Stage-Analysis, concepts/ADX, concepts/RSI]
---

# Source — SwingEdge.info Stock Detail Page (AADHARHFC)

## Metadata
- **Source type**: Swing-trading scanner/setup web app, same source as [[sources/SwingEdge-KDDL-20260621]] and [[sources/SwingEdge-NRBBEARING-20260621]]
- **URL**: https://www.swingedge.info/stocks/AADHARHFC
- **Snapshot date**: 2026-06-21
- **Scan category**: not tagged to a specific pre-built scan on this page (no "Base Formation"/"Momentum Continuation" eyebrow label — just "Finance - Housing"); breadcrumb routes through the generic `/pre-breakout` screener

## Key Takeaways
- Aadhar Housing Finance Ltd. (Finance - Housing, "large mid cap") scored **79/100 setup readiness**, verdict "Watchlist-worthy setup," decision-quality grade **C, 51/100 — "Mixed, needs patience."** This is the weakest decision-quality grade of the three SwingEdge tickers ingested so far (KDDL: B/61, NRBBEARING: B/69, AADHARHFC: C/51).
- **First ticker where RS rank and sector RS actually agree, both lagging**: RS rank 55/100 ("lagging the broader market") and Sector RS also tagged "Lagging group." This breaks the 2-for-2 pattern noted on KDDL and NRBBEARING (RS-leading stock inside a "lagging" sector) — confirming that pattern isn't universal, just common enough on the first two samples to flag. Worth keeping all three data points together if a larger sample is built later.
- ADX 15 — "weak/choppy trend," the first of the three tickers without a confirmed strong trend (KDDL ADX 34, NRBBEARING ADX 51, both "strong"; AADHARHFC explicitly weak).
- Tags: Stage 2, VCP active — no "RS leader" tag here (consistent with its mid-pack RS rank), no "Vol compression"/"Handle" tag either despite a handle being mentioned in the bullish-factors text.
- **New risk-factor type not seen on the first two tickers: "6 distribution days recently — institutional selling"** — flagged both as a risk factor and as the page's sole "reason to skip." Distinct risk character from KDDL's wide-stop concern and NRBBEARING's overextension/chase risk — this one is specifically about detected selling pressure despite the stock otherwise screening as a constructive setup.
- Despite the distribution-day flag, the page's own "Accumulation" metric reads "Constructive" and cites "Recent volume expansion — institutional participation may be returning" and "Volume flow suggests quiet institutional accumulation" as bullish factors — an internal tension the source's own Overall View text acknowledges: "Short-term accumulation is visible, though it should be weighed against trend and RS context."
- Risk/Reward is the best of the three tickers: **3.2:1**, with risk distance only 5.9% to stop (vs. KDDL 8.3%, NRBBEARING 9.6%) — no "stop too wide" skip flag here, unlike both prior tickers.
- "Why now" bullet list mentions "Volume 6.2x the 50-day average" and "RS line at new highs — leadership intact" — phrases that read bullish but sit awkwardly next to the RS rank (55, lagging) and ADX (15, weak) readings elsewhere on the same page; the "Why now" panel and the "Context & regime" panel appear to draw from different underlying signals/timeframes and can disagree with each other on the same page.

## Detailed Notes

**Setup snapshot (as of 2026-06-21):**
- Price: ~₹515.1
- Entry zone: ₹498.9–525.6
- Support / stop: ₹494.6 (4.0% below the pivot's failure level)
- Resistance / pivot: ₹523.0 (price ~1.5% below pivot at snapshot)
- Next resistance: ₹623.6; further target ₹627.6 (unusually close together — only ₹4 apart, likely two independently-computed target methods converging rather than a typo)
- Risk/Reward: 3.2:1; risk ≈ ₹30.99/share from entry ₹525.6

**Bullish factors listed**: coiled at pivot; prior pivot rejection (penalty, same recurring UI quirk noted on KDDL/NRBBEARING — listed under "bullish" but is -8 pts); MACD positive/rising (explicitly "confirmation only — no bonus," unusually transparent about not double-counting); RSI 67 ("ideal setup zone"); handle formation; constructive advance off 52-week low; volume expansion; quiet institutional accumulation.

**Risk factor / skip reason**: 6 distribution days recently — institutional selling (the only skip reason on this page, vs. "stop too wide" on both prior tickers).

**Why not 100**: RS rank below elite band (<90); volume quality not in top confirmation range — identical reasons to KDDL's page.

## Actionable Insights
- Confirms the "bullish factors card mixes penalties with true positives" UI quirk on a third ticker (1 prior pivot rejection, -8 pts, again appears under "Bullish factors"). This is now a structural pattern of the site's template, not a one-off — safe to assume every future SwingEdge ingest will need the same bullet-by-bullet read rather than trusting the card heading.
- AADHARHFC is the first of three tickers where the "RS leader in lagging sector" pattern does NOT hold — both individual RS and sector RS lag together here. Useful negative case: the pattern flagged on KDDL/NRBBEARING is real but not universal: 2 of 3 tickers showed sector-lagging/stock-leading divergence; this one shows simple alignment instead.
- The same page shows conflicting signals in different panels (the "Why now" section claims "RS line at new highs — leadership intact" while the "Context & regime" section tags RS as "Lagging (RS 55)" headwind) — worth treating each SwingEdge panel as drawing from a potentially different lookback/metric rather than assuming page-wide internal consistency.
- "6 distribution days" institutional-selling flag, instead of a wide-stop or overextension flag, raises a different kind of caution than the prior two tickers — useful to cross-reference against this wiki's FII/DII holding-change tooling (it's effectively measuring distribution differently than that flow-based approach: SwingEdge appears to use a price/volume distribution-day count, not actual FII/DII filings).

## Contradictions with Existing Wiki
- None directly. Adds a useful counter-example to the "RS leader in lagging sector" observation tracked across the first two SwingEdge ingests — see updated note on [[sources/SwingEdge-KDDL-20260621]].

## Pages Updated
- Created [[entities/AADHARHFC]]
- This source page
- Updated [[sources/SwingEdge-KDDL-20260621]] (note: pattern not universal — 2 of 3)
