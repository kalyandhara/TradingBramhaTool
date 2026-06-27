---
title: "SwingEdge — Sector Momentum Map"
category: source
tags: [sector-rotation, relative-strength, RRG, quadrant, NSE, momentum]
created: 2026-06-22
updated: 2026-06-22
sources: 1
related: [strategies/Sector-Liquidity-Rotation, analyses/Sector-Watchlist, sources/SwingEdge-KDDL-20260621, sources/SwingEdge-INDSWFTLAB-20260621]
---

# Source — SwingEdge.info Sector Momentum Map

## Metadata
- **Source type**: Live sector-rotation listing page (data IS server-rendered this time, unlike the position-sizing/breakdowns tool pages)
- **URL**: https://www.swingedge.info/sectors/momentum
- **Snapshot date**: 2026-06-22 (page footnote: "Updated at each market close")
- Covers **~140 NSE sector, thematic, broad-market and factor indices**, ranked against the Nifty 500.

## Key Takeaways — this is the same quadrant framework as our own sector tooling, computed a completely different way

This page implements a **4-quadrant Leading/Improving/Weakening/Lagging rotation map** — the exact same quadrant naming and structure as this wiki's own [[strategies/Sector-Liquidity-Rotation]] (`tools/sector_rotation.py` / `sector_rotation_trail.py`). But the inputs are entirely different:

| | This wiki's tool | SwingEdge's Sector Momentum Map |
|---|---|---|
| Signal axis 1 | Cap-weighted FII/DII holding change | 3-month relative return vs Nifty 500 |
| Signal axis 2 | Sector index 1Y trailing trend | "Pace" — recent rate of change in that relative return |
| Quadrant logic | Inflow/Outflow × Rising/Falling index | Positive/Negative 3mo RS × Accelerating/Decelerating pace |
| Data source | screener.in shareholding pattern (per-company, self-sourced) | NSE index price data only — no institutional-flow signal at all |

**Precise quadrant definitions, quoted directly** (from this page's own FAQ — more explicit than our tool's bias table): "Leading sectors have positive three-month relative strength vs the Nifty 500 and positive recent pace — they are outperforming and still gaining momentum. Weakening sectors may still show positive three-month returns but have slowing pace, meaning outperformance is fading versus the benchmark." (Improving/Lagging are the implied other two quadrant combinations: Improving = negative 3mo RS but positive/improving pace; Lagging = negative 3mo RS and negative pace.)

**Snapshot counts (2026-06-22)**: 14 Leading, 34 Improving, 56 Weakening, 35 Lagging (out of ~140 indices) — market-wide framing: "up 7.7% over the past three months... 14 sectors leading with strong, improving momentum... Standouts today include Nifty IPO, Nifty Media, Nifty Realty... 34 sectors gaining ground... 35 sectors continue to trail."

**Top Leading (3mo vs market)**: Nifty IPO (+16.7%), Nifty Media (+9.5%), Nifty Realty (+8.6%), Nifty EV & New Age Automotive (+6.6%), Nifty India New Age Consumption (+5.2%).

**Top Improving (by Pace)**: Nifty50 Dividend Points (+426.8% — an extreme outlier, likely a low-base/index-construction artifact rather than a real tradeable signal), Nifty PSU Bank (+8.8%), Nifty Bank (+5.7%), Nifty Consumer Durables (+4.2%), NIFTY50 USD (+3.9%).

**Top Weakening (losing pace, by Pace)**: Nifty Capital Markets (-8.7%), Nifty Metal (-6.2%), Nifty Midcap Liquid 15 (-5.9%), Nifty MidSmall Healthcare (-5.7%), **Nifty Pharma (-4.3%)**.

**Top Lagging (3mo vs market)**: India VIX (-47.6% — a volatility index, not a sector, included presumably for completeness/context), Nifty IT (-13.2%), Nifty50 TR/PR 1x Inverse (leveraged/inverse products, not real sectors), Nifty CPSE (-9.4%).

## Detailed Notes

**"Setups in hot sectors" cross-sell panel** lists specific stock picks tied to the leading sectors at snapshot time: SANGHVIMOV (100.0, Breakout), PSPPROJECT (100.0, Breakout), WELENT (83.4, Breakout), POWERMECH (80.1, Breakout), ATALREAL (76.5, Breakout), GVPIL (75.1, Breakout), CEMPRO (78.4, Pre-breakout) — all infrastructure/EPC/power-adjacent names, consistent with broader infra/realty leadership showing up in the quadrant data.

**Pharma is currently Weakening** on this page (-4.3% pace) — directly relevant since [[entities/INDSWFTLAB]] (Pharmaceuticals & Drugs) was already ingested with a cautious "Wait and Watch" verdict; this sector-level read is consistent with, and adds context to, that individual stock's weak setup quality.

**Index universe breadth**: includes not just real economic sectors (Bank, IT, Pharma, Auto, Metal, FMCG, etc.) but thematic baskets (EV & New Age Automotive, India Tourism, India Digital, Mobility), factor/style indices (Momentum, Quality, Low-Volatility, Alpha, Value), broad-market variants (Equal Weight, Multicap blends), bond indices (Bharat Bond series, G-Sec maturities), and even India VIX and leveraged/inverse products — a much broader and noisier universe than a clean "sector" list. Filtering by the page's own `data-category` tag (sector/thematic/broad/factor) would be needed before treating "#1 Lagging" type rankings as meaningful, since bond indices and VIX sitting at the extremes are not actionable equity-sector signals.

## Actionable Insights
- **Direct cross-check opportunity**: the next time `tools/sector_rotation.py` is run with a fresh screener.in export, compare its FII/DII-flow-based sector bias against this page's price-RS-based quadrant for the same sectors. Agreement would reinforce a sector call; disagreement (e.g. FII inflow into a sector that SwingEdge shows as "Weakening" on pure price RS) would be a genuinely interesting early-divergence signal worth a dedicated note — institutional accumulation often precedes price strength, so a flow/price split is informative either way.
- Treat the "140 indices" universe with the filtering caveat above — restrict to `data-category=sector` entries for genuine industry-sector comparisons; thematic/factor/broad/bond entries answer a different question.
- The Nifty50 Dividend Points "+426.8% pace" outlier is a good reminder to sanity-check any single extreme reading against the underlying index's construction before treating it as a real signal — total-return/points-based indices can produce distorted percentage changes that look dramatic but aren't comparable to price-return sector indices.

## Contradictions with Existing Wiki
- None yet — this is a complementary, independently-computed sector-strength read (pure price RS) sitting alongside this wiki's flow-based [[strategies/Sector-Liquidity-Rotation]] tool. The two should be compared on a shared sector list once both have current data, rather than assumed to agree.

## Pages Updated
- Updated [[strategies/Sector-Liquidity-Rotation]] — added a cross-reference note pointing to this page as an independent, price-RS-based sector rotation read to validate against
- This source page
