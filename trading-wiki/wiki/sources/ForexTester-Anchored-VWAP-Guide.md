---
title: "Article — ForexTester: Anchored VWAP (AVWAP)"
category: source
tags: [vwap, anchored-vwap, avwap, brian-shannon, anchor-selection, backtest, forex]
created: 2026-08-02
updated: 2026-08-02
sources: 1
related: [concepts/Anchored-VWAP-Pyramiding, concepts/VWAP, analyses/Dashboard-UI-Roadmap]
---

# Article — ForexTester: Anchored VWAP (AVWAP)

## Metadata
- **URL:** https://forextester.com/blog/anchored-vwap/
- **Publisher:** ForexTester (backtesting-software vendor — the strategy section doubles as a product demo, which is worth holding in mind when reading its 30-trade result)
- **Ingested:** 2026-08-02
- **Bias:** Instructional/neutral. Carries its own disclaimer: *"for educational purposes only and are not financial advice."*
- **Attribution:** Credits **Brian Shannon** (alphatrends.net) as having developed and popularised AVWAP, and calls his methodology "the standard reference for the indicator."

## Key Takeaways
- **The formula is explicit and matches ours:** `AVWAP = Σ(Typical Price × Volume) ÷ Σ(Volume)` with `Typical Price = (H+L+C)/3`, accumulated from the anchor forward with **no reset**.
- **Four price inputs are offered**, with stated preferences: `(H+L+C)/3` (default, recommended for swing/event work), `close` (more responsive, intraday), `(H+L)/2`, `(O+H+L+C)/4` (smoothest).
- **Anchors are ranked by analytical strength:** swing high/low → earnings/catalyst → IPO/first trade → breakout candle → macro event (FOMC/CPI/NFP). Explicit instruction to **avoid random, low-volume bars with no structural significance**.
- **The dual-anchor bias framework is the article's real contribution** and is new to this wiki — see below.
- **Anchor selection is named as "the most subjective — and most critical — aspect."** The indicator's math is trivial; the judgement is entirely in the anchor.
- A mechanical backtest is included, and so is the caveat that guts it: **30 trades is not a result.**

## Detailed Notes

### The dual-AVWAP bias framework — "no man's land"
The behavioural reading this wiki already records ([[concepts/Anchored-VWAP-Pyramiding]] §AVWAP as dynamic support/resistance) is extended to **two** simultaneous anchors:

- **Above the AVWAP anchored at a swing low** — buyers from that low are profitable, have no pressure to sell, and dips toward the line attract more buying.
- **Below the AVWAP anchored at a swing high** — sellers from that high are profitable, have no pressure to cover, and rallies toward the line attract more selling.
- **Between the two** — *"no man's land"*: neither cohort is under pressure, the edge dissolves, and trades taken there produce noise.

That third state is the part worth having. A single AVWAP always says "above" or "below"; only a pair can say **"neither, so stand aside."**

### VWAP vs AVWAP, as the article frames it
| | Session VWAP | Anchored VWAP |
|---|---|---|
| Start | Fixed at session open | Any candle |
| Reset | Daily | Never — cumulative from anchor |
| Use case | Intraday mean reversion | Multi-day trend, event-driven |
| Timeframe | **Intraday only** | Any |
| Main weakness | *"Useless for swing analysis; gaps overnight"* | Requires judgement picking anchors |

### The mechanical example (USDJPY, prior-day anchors)
- Long on a **close above** the AVWAP anchored at the **prior day's high**; short on a **close below** the AVWAP anchored at the **prior day's low**.
- Opposite signal reverses the position. **Exit end-of-day only** — no fixed stop or target.
- No trade if the session opens already outside both AVWAPs; wait for the next signal.
- Reported: **53% win rate · 2.02 profit factor · $3,322 net on a $10K account · 30 trades.**
- Their own exit optimiser suggested ~58.9 pip stop / ~239.0 pip target.

> [!caution] The sample size is the finding, not the profit factor
> The article says it plainly: *"30 trades is enough to see that the logic has some signal, but not enough to draw firm conclusions about live performance"*, and that the strategy *"isn't a smooth compounder — it's a trend-following system with inherent variance."* A 2.02 profit factor over 30 trades on one instrument is indistinguishable from luck. [[analyses/Backtest-Harness]] measured five of our own scanners and found only one beat a random-entry baseline; the same standard applies here.

## Actionable Insights
1. **Add a high-anchored AVWAP** so the "no man's land" state becomes expressible. Our chart draws only a low-anchored line, so it can currently say "buyers are in profit" but never "neither side is."
2. **Prior-day high/low is an anchor class we do not implement** — session-relative rather than structure-relative, and the only one in the article with a mechanical rule attached.
3. **The (H+L+C)/3 default is confirmed correct** for swing/event use, which is what our implementation hardcodes.
4. **Macro-event anchors (FOMC/CPI/NFP)** are a natural fit for NIFTY around RBI policy and Union Budget dates — and would compose with [[analyses/Astro-Weekly-Forecast-Card-Fit]]'s calendar machinery, which already stores dated events.

## Contradictions with Existing Wiki

> [!note] No contradictions — one confirmation and one gap
> Nothing here conflicts with [[concepts/VWAP]] or [[concepts/Anchored-VWAP-Pyramiding]]. The article **confirms** two things this wiki already asserts: that session VWAP must not be applied to swing trades (VWAP.md §Common Mistakes), and that AVWAP's power is behavioural rather than mathematical (Anchored-VWAP-Pyramiding.md).

**Against the shipped implementation** ([chart_dashboard.html](tools/chart_dashboard.html), commits `70601b3` / `f7570b0`) the comparison is:

| Article says | Our implementation | Verdict |
|---|---|---|
| `Σ(HLC/3 × V) / Σ(V)`, no reset | identical | ✅ match |
| Anchor at swing high **or** low | swing **low** only | ❌ **gap — blocks the no-man's-land read** |
| Avoid structurally insignificant bars | prominence filter ≥ 2.0 ATR on both legs | ✅ we are stricter, and measured |
| Session VWAP is intraday-only | disabled on 1d/1w | ✅ match |
| (silent on missing volume) | emits no point rather than substituting close | ✅ we are stricter |
| Anchor selection is the critical judgement | automated from the zigzag | ⚠️ we removed the judgement rather than exposing it — no click-to-anchor |

## Pages Updated
- [[concepts/Anchored-VWAP-Pyramiding]] — formula, price-input variants, Shannon attribution, dual-anchor/no-man's-land, macro-event anchors, implementation cross-reference
- [[concepts/VWAP]] — Shannon attribution and the AVWAP comparison table
- [[index]], [[log]]
