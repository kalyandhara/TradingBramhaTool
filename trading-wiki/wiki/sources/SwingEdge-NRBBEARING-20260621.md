---
title: "SwingEdge — NRBBEARING Stock Detail Page"
category: source
tags: [swing-trading, technical-analysis, scanner, momentum-continuation, vcp, stage-analysis, relative-strength, overextended]
created: 2026-06-22
updated: 2026-06-22
sources: 1
related: [entities/NRBBEARING, sources/SwingEdge-KDDL-20260621, concepts/VCP, concepts/Stage-Analysis, concepts/ADX, concepts/RSI]
---

# Source — SwingEdge.info Stock Detail Page (NRBBEARING)

## Metadata
- **Source type**: Swing-trading scanner/setup web app (single stock detail page), same source as [[sources/SwingEdge-KDDL-20260621]]
- **URL**: https://www.swingedge.info/stocks/NRBBEARING
- **Snapshot date**: 2026-06-21
- **Scan category**: Momentum Continuation (different scan bucket than KDDL's Base Formation — this is a stock already moving, not coiling pre-breakout)

## Key Takeaways
- NRB Bearings Ltd. (Bearings sector) scored **79/100 setup readiness**, verdict "Watchlist-worthy setup" (one notch below KDDL's "Strong momentum structure" verdict) — decision-quality grade **B, 69/100**.
- RS rank **100/100** — "a market leader, stronger than most NSE stocks" per the source's own FAQ language. ADX 51 = strong trend (well above the >40 "strong" threshold in this wiki's [[concepts/ADX]] page).
- Tagged: Stage 2, RS leader, VCP active — same tag set pattern as KDDL minus "Vol compression" / "Handle".
- **Key new risk signal not seen on the KDDL page: an explicit "Overextended" failure flag**, with supporting detail "Overextended 25% above MA50 (chase risk, score −2)" and "RSI 71 (90th pct 1y, ATR vol 96th pct)." This is a momentum-continuation-specific risk (chasing an extended move) distinct from KDDL's base-formation risk (wide stop on a still-coiling setup).
- Gain stats: +11.0% over 10 days, +16.7% over 20 days — explicitly listed as a bullish factor, but read alongside the overextension flag this is also the source of the chase risk.
- Stage 2 trend-template score: **8/8** (full marks) — the strongest Stage-2 confirmation reading seen from this source so far.
- Volume: 0.4× the 50-day average, flagged "[dry-up ✓]" — a constructive low-volume pullback/coil signature even within an extended momentum stock.
- Same recurring skip reason as KDDL: **stop is 10% away from entry — "too wide to size well for a swing."** Risk/Reward 2.0:1, risk ≈ ₹44.01/share from entry ₹458.1.
- **Sector RS explicitly labeled "Lagging group" / headwind** — same pattern as KDDL: an individual RS-100 leader sitting inside a sector the source itself rates as lagging. Two-for-two on this contradiction now; worth treating as a recurring pattern from this source rather than a one-off, per [[sources/SwingEdge-KDDL-20260621]]'s note.
- Market regime context (site-wide, not stock-specific): "Mixed / range-bound" — identical regime tag to the KDDL snapshot from the same date, confirming this is a site-wide regime read, not per-stock.

## Detailed Notes

**Setup snapshot (as of 2026-06-21):**
- Price: ~₹428.2 (meta description)
- Entry zone: ₹451.1–458.1
- Support / stop: ₹414.1 (3.3% below the pivot's failure re-entry level)
- Resistance / pivot: ₹455.8 (price ~6.0% below pivot, "still building toward it" per FAQ — interesting given the RS-100 / momentum-continuation framing, suggesting the continuation move has paused below the pivot rather than already cleared it)
- Next resistance: ₹547.0; further target ₹711.9
- Risk/Reward: 2.0:1 on first target; risk distance 9.6% to stop, 1.9× ATR

**Bullish factors listed**: gain 10d/20d stats; overextension flag (again, listed under "bullish" but is a penalty, same UI quirk noted for KDDL); RSI 71 reading; Stage2 8/8; volume dry-up.

**Why not 100**: only one reason given — "Volume quality is not in top confirmation range yet" (RS rank itself is already maxed at 100, so unlike KDDL the RS-band reason doesn't apply here).

## Actionable Insights
- This source's "bullish factors" list mixes true positives with explicitly negative-scored items (overextension −2, prior pivot rejections on KDDL) inside the same UI card — confirmed across two tickers now. Treat every bullet individually, don't assume the card heading implies all-positive when scraping further tickers from this source.
- The "lagging sector, RS-leading individual stock" pattern has now appeared on both tickers ingested from this source (KDDL — Watches & Accessories #26/32; NRBBEARING — sector RS "Lagging group"). If this keeps recurring across more tickers, it likely reflects how Swing Edge's sector-RS model is constructed (probably equal-weighted average RS of sector constituents, which a sector's single best stock can sit well above) rather than a genuine signal — worth testing against this wiki's FII/DII-based [[strategies/Sector-Liquidity-Rotation]] methodology once enough tickers accumulate.
- Momentum Continuation scans (like this one) carry a different risk profile than Base Formation scans (like KDDL): chase/overextension risk vs. wide-stop/un-triggered-pivot risk. Worth tagging future SwingEdge ingests by scan type so the wiki can distinguish "still coiling" from "already extended" setups at a glance.

## Contradictions with Existing Wiki
- None directly, but reinforces the KDDL source page's flagged pattern (RS-leading stock inside a "lagging" sector per this source) — now seen twice, elevating it from a one-off note to a recurring methodology question worth its own analysis page if a third example appears.

## Pages Updated
- Created [[entities/NRBBEARING]]
- This source page
- Updated [[sources/SwingEdge-KDDL-20260621]] cross-link (no edit needed yet, referenced via `related`)
