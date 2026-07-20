---
title: "LuxAlgo"
category: entity
entity_type: organization
tags: [luxalgo, tradingview, pine-script, smc, indicator-vendor]
created: 2026-07-16
updated: 2026-07-16
sources: 1
related: [sources/LuxAlgo-Smart-Money-Concepts-Pine, concepts/Order-Blocks, concepts/Market-Structure-CHOCH-BOS]
---

# LuxAlgo

## What
A TradingView indicator publisher / trading-tools vendor, best known for the **[[sources/LuxAlgo-Smart-Money-Concepts-Pine|Smart Money Concepts [LuxAlgo]]]** open-source script — the single most-forked SMC indicator on the platform and the de-facto reference implementation for retail Smart Money Concepts (BOS/CHoCH, order blocks, FVG, equal highs/lows, premium/discount zones).

## Why it matters here
Their open-source Pine scripts are released under **CC BY-NC-SA 4.0** (attribution, non-commercial, share-alike). That makes them a legitimate *reference* for how the SMC community mechanically defines each primitive, but any port into this repo's tooling must stay non-commercial and credit LuxAlgo. Treat their scripts as canonical SMC spec, not as proprietary edge.

## Contributions ingested
- [[sources/LuxAlgo-Smart-Money-Concepts-Pine]] (2026-07-16) — the full SMC superset indicator; primary source for [[concepts/Order-Blocks]], [[concepts/Equal-Highs-Lows]], [[concepts/Premium-Discount-Zones]], and the internal-vs-swing structure model on [[concepts/Market-Structure-CHOCH-BOS]].

## Notes
- Not SEBI/registered advice — an indicator vendor. Their tooling is descriptive (marks structure/zones), not predictive; same "reactive not predictive" framing as [[sources/YT-Samir-Varmer-Physicist-Trader]].
