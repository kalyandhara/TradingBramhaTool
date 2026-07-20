---
title: "SwingEdge — EPIGRAL stock detail page (Downside Risk scan, 2026-07-03)"
category: source
tags: [swingedge, epigral, downside-risk, stage-4, distribution, volume-profile, veto, chemicals]
created: 2026-07-03
updated: 2026-07-03
sources: 1
related: [entities/EPIGRAL, concepts/Stage-Analysis, concepts/Distribution-Days, concepts/Volume-Profile, concepts/VCP, sources/SwingEdge-Downside-Risk-Screener]
---

# SwingEdge — EPIGRAL Stock Detail Page (Downside Risk)

## Metadata
- URL: https://www.swingedge.info/stocks/EPIGRAL
- Scan data dated: 2026-07-03 (last daily close, not live)
- Fetched: 2026-07-03 via Playwright (site 403s plain HTTP fetches)
- Scan: **Downside Risk** — first bearish-scan stock page ingested (prior SwingEdge pages were Base Formation / Momentum Continuation / skip-flag cases)

## Key Takeaways
1. **A complete "avoid" profile in one page**: Stage 4 (weekly below 30-wk MA, peer table labels it "Breakdown Started"), RS rank 23, RSI 32 weakening, 10d/20d move −10.5%/−12.8%, 5 distribution days, failure-risk score 78/100, SEI grade **F — "No Edge"**, phase **DISTRIBUTE**, setup window 0 of 20, −51.7% from 52-week high.
2. **"Reasons to skip: disqualifiers that apply even if the score looks good"** — SwingEdge explicitly implements the veto tier (5 distribution days; failure risk 78/100; Stage 4 not Stage 2). Same design conclusion as this wiki's Confirm-Before-Entry doctrine discussion (2026-07-03): no score can override a veto.
3. **Live below-VAL example for the new Volume-Profile check**: profile "bearish" — POC ₹1,225.69, VAH ₹1,312.84, VAL ₹1,030.87, only 43.3% of volume above POC, price ₹1,021.6 = **below the entire value area**. Our `compute_volume_profile_levels()` warning ("trading below the value area — no volume acceptance") would fire on exactly this chart.
4. **Failed VCP anatomy**: 16-week base, 42.4% deep (well beyond Minervini's ~33% limit), contraction ladder L1 13.1% → L2 28.8% → **L3 69%** → L4 28.8% — the legs *expand* mid-ladder instead of contracting; radar VCP sub-score 13/100. A textbook example that "3 contractions detected" means nothing if the sequence isn't tightening.
5. **RS laggard in a healthy sector** — the inverse of the KDDL/NRBBEARING "RS leader in lagging sector" pattern: Chemicals peers are RS 87–100 and Stage 2 (FLUOROCHEM, PIDILITIND, AETHER "Active Breakout", PREMEXPLN RS 100), while EPIGRAL sits at RS ~23–35 in breakdown. Sector strength does not rescue the laggard; it marks where the money rotated *to*.
6. **Institutional read**: avg cost basis ₹1,062.89 — price (₹1,021.6) is **below the institutions' average cost**; CMF −0.29; activity labeled Distribution. Underwater holders = overhead supply (53.1% "some overhead") on any bounce.

## Detailed Notes
- Setup card (long-side framing): pivot ₹1,306.3–1,407.0, support ₹1,333.1, resistance ₹1,680.0, risk 5.3% to stop (₹73.9/share from entry ₹1,407), R:R 3.7×, reward 19.4% — all computed **from the failed entry**, not from current price.
- Context: market regime "Mixed / range-bound"; sector mid-pack #13/36; ADX 27 "Building" (trend strength building *downward* here — ADX is direction-agnostic); ATR 3.6%/day "Healthy"; volume quality 36 "Thin".
- Setup quality radar 26.3/100: VCP 13, RS 0, Stage 50, Volume 36, Low-risk 22, Clear-path 36.
- Seasonality (3y): strongest April (+20.6% avg; Apr 2026 was +50%), weakest December (−14.1% avg); 2026 YTD red every month except April.
- Smart money flow panel: "Mild accumulation" label over 60 sessions (6 acc vs 2 dist sessions) despite CMF −0.295 — see contradictions.
- Multiple RS figures on one page: 23 (score chip / structure), 34 (context list), 35 (peer table) — likely different lookbacks; treat "RS ~23–35, weak" as the reading.

## Contradictions with Existing Wiki / Internal Inconsistencies
- **Page's own template bugs (flag for skepticism when reading SwingEdge prose)**: "Bullish factors: • Price remains below the 150DMA" (bearish fact mislabeled bullish); Intelligence summary says "Strong technical characteristics — momentum and institutional cues show broad alignment" on a grade-F Stage-4 breakdown; "This idea is wrong below ₹1,333.1" while price already sits 23% below that level (the invalidation already happened); peer blurb calls EPIGRAL "a contender at 91" while the SEI grade is F. The structured numbers are coherent — the generated prose is not. **Trust the fields, not the sentences.**
- "Mild accumulation" label vs CMF −0.29 + Distribution phase — the session-count heuristic (6 acc / 2 dist) disagrees with the flow-weighted read; consistent with [[concepts/Distribution-Days]]'s point that distribution shows up in *weighted* volume behavior, not day counts.
- No contradictions with wiki concepts — the page is a clean confirming example of Stage-Analysis, Distribution-Days, deep-base VCP failure, and below-value-area semantics.

## Actionable Insights
- **Validation-layer confirmation**: our 9-check layer would correctly shred this chart — Stage 4 weekly (MTF fail), below VAL (Profile warning), thin volume, RS laggard, no structure break. Good negative-control case for the Early Reversal Detector: drop-recovery gate would also fail (no meaningful recovery of the drop yet at −51.7% from high).
- **Veto-tier design validated by an independent product**: SwingEdge ships "disqualifiers that apply even if the score looks good" as a first-class UI block — adopt the same explicit presentation when the Confirm-Before-Entry doctrine page + card verdicts get built.
- **Watch trigger, not a write-off forever**: reversal interest only above the value area (> ₹1,312 VAH) with a weekly structure repair; April seasonality is the recurring bounce window. Below institutions' cost basis (₹1,063), rallies are supply.

## Pages Updated
- [[entities/EPIGRAL]] — created (bias: bearish/avoid, full scan snapshot)
- [[concepts/Volume-Profile]] — live below-VAL example added
- index.md, log.md
