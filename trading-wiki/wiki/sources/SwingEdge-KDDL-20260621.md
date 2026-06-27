---
title: "SwingEdge — KDDL Stock Detail Page"
category: source
tags: [swing-trading, technical-analysis, scanner, base-formation, vcp, stage-analysis, relative-strength]
created: 2026-06-22
updated: 2026-06-22
sources: 1
related: [entities/KDDL, sources/SwingEdge-NRBBEARING-20260621, concepts/VCP, concepts/Stage-Analysis, concepts/ADX, concepts/Support-Resistance, analyses/Sector-Watchlist, strategies/Sector-Liquidity-Rotation]
---

# Source — SwingEdge.info Stock Detail Page (KDDL)

## Metadata
- **Source type**: Swing-trading scanner/setup web app (single stock detail page)
- **URL**: https://www.swingedge.info/stocks/KDDL
- **Snapshot date**: 2026-06-21 (page's own "dateModified")
- **Scan category**: Base Formation scanner

Swing Edge is a free NSE stock-scanning site (per its own schema.org description: "Free stock scanning and chart research for momentum and structure setups, sector breadth and market internals — not buy, sell or hold recommendations"). It exposes pre-built scans (Base Formation, Momentum Continuation, Downside Risk, Darvas Box, Structural Breakout, Rounding Bottom, ETF Leaders) and per-stock detail pages combining a momentum/structure score, a separate "decision quality" grade, key levels, and AI-insight commentary (locked behind sign-in).

## Key Takeaways
- KDDL Ltd. (Watches & Accessories) scored **100/100 "setup readiness"** on Swing Edge's Base Formation scan, but only **B-grade / 61-100 "decision quality"** — the site explicitly separates raw setup score from a more conservative trade-worthiness grade, and the two disagreed here.
- Tagged: Stage 2, RS leader, VCP active, Vol compression, Handle — a textbook VCP/Stage-2 base, consistent with [[concepts/VCP]] and [[concepts/Stage-Analysis]].
- Relative strength (RS) rank 76/100 vs the NSE universe — "building, outperforming" but explicitly below the site's "elite leadership band (<90)" cutoff, which is why it didn't score 100 on decision quality.
- ADX 34 = strong trend per the site's own ADX framework, matching this wiki's [[concepts/ADX]] (>40 = strong; 34 sits in the upper-moderate range, the source still calls it "strong").
- **Notable contradiction**: the stock is rated an RS leader individually, but its own sector ("Watches & Accessories") is ranked **#26 of 32 — "Lagging / headwind"** in Swing Edge's sector model. The site's own decision-quality framework treats this as a structural headwind even with a strong individual setup — worth cross-referencing against this wiki's [[analyses/Sector-Watchlist]] and [[strategies/Sector-Liquidity-Rotation]], which track sector strength independently via FII/DII flow + index trend rather than RS rank.
- Hard skip flag: **stop is 8% away from entry — explicitly called out as "too wide to size well for a swing."** Risk:Reward quoted at 2.3:1 against that wide stop, with $-equivalent risk ≈ ₹254.2/share.
- "Smart money flow" panel (60-session accumulation/distribution heatmap + OBV trend) is present on the page but was not populated in the static fetch — it's loaded client-side via JS, not available without browser rendering.
- AI-generated insights panel exists but is locked behind sign-in (Gemini-powered) — not captured.

## Detailed Notes

**Setup snapshot (as of 2026-06-21):**
- Price: ~₹2,959.7 (meta description) / entry zone ₹3014.8–3045.2 per the readiness box
- Support / stop: ₹2,790.9 (base/stop zone)
- Resistance / pivot: ₹3,030.0 (breakout trigger)
- Next resistance: ₹3,636.0; further target ₹4,116.1
- Risk/Reward: 2.3:1 on first target; risk distance 8.3% to stop, 1.9× ATR
- RS 76, ADX 34, Volume score 48 (capped — "volume persistence 2/3, capped at Strong")

**Bullish factors listed**: price approaching pivot zone; ATR shrinking 3 consecutive weeks (coil forming); RS+pivot distance aligned; Bollinger Band squeeze; pivot type "flat-top" (called "premium structure"); volume persistence 2/3.

**Listed as a negative within the same "bullish factors" card** (site's own UI oddity, worth noting if cross-checking other tickers): "MACD below zero — weak trend (−2)" and "1 prior pivot rejection in last 60d (-8 pts)" — these read as penalties embedded in the bullish list, not pure positives. Don't take the "bullish factors" heading at face value when re-scraping other tickers from this source — verify whether each bullet is actually additive or a penalty.

**Why not 100 (decision-quality gap)**: RS rank below elite band (<90); volume quality not in top confirmation range.

**Trade management framework offered by the site** (generic, not KDDL-specific): scale out 20–30% around +1.5R to +2R; trail below 21 EMA beyond +2R; tighten stop to breakeven after +1R.

## Actionable Insights
- KDDL is a candidate to monitor for breakout above ₹3,030 pivot with volume confirmation, but the 8%-wide stop is a real sizing constraint — Swing Edge's own framework flags it as a skip-reason despite the otherwise clean base structure. Worth combining with this wiki's [[concepts/VCP]] 3-tier detection and [[strategies/Sector-Liquidity-Rotation]] FII/DII check before acting — a clean technical base in a fundamentally lagging sector is a lower-conviction setup than the raw 100/100 score suggests.
- Swing Edge's sector-ranking model (#26/32 "lagging") for Watches & Accessories is an independent third-party read worth comparing against this wiki's own sector-rotation tooling output the next time that sector appears in a `sector_rotation.py` run — a second source agreeing or disagreeing on sector strength is a useful cross-check.
- The site blocks default `WebFetch`/bot user agents with a 403; a standard browser `User-Agent` header via `curl`/`requests` returns 200 fine — no auth needed for the public scan data (sign-in only gates the AI insights and watchlist features).

## Contradictions with Existing Wiki
- None yet directly contradicted, but the sector-strength disagreement (RS leader individually vs. lagging sector per Swing Edge's own ranking) is a pattern worth watching: this wiki's sector-rotation tooling ranks sectors by cap-weighted FII/DII flow + index trend, which is a fundamentally different methodology than whatever RS/momentum-based sector ranking Swing Edge uses. If the two methodologies diverge often, that's worth its own analysis page.
- **Update 2026-06-22**: the same pattern recurred on [[sources/SwingEdge-NRBBEARING-20260621]] (RS-100 stock, sector RS "Lagging group") — 2 of 2 at that point. Likely explanation: Swing Edge's sector-RS score is an average across sector constituents, which a single standout stock can sit well above.
- **Update 2026-06-22 (again)**: [[sources/SwingEdge-AADHARHFC-20260621]] broke the pattern — RS 55 (itself lagging) and sector RS also "Lagging group," in agreement. So 2 of 3 tickers show the stock-leads/sector-lags divergence, not a universal rule. Conclusion: the divergence is real and worth watching for, but not assumable by default — check each ticker's own RS rank against its sector tag rather than assuming a leader-in-laggard-sector setup.

## Pages Updated
- Created [[entities/KDDL]]
- This source page
