---
title: "ADX — Average Directional Index"
category: concept
tags: [trend-strength, ADX, DMI, directional-movement, regime-filter]
created: 2026-06-14
updated: 2026-08-26
sources: 2
related: [concepts/RSI.md, concepts/EMA.md, strategies/TechnoFunda-Swing.md, strategies/TechnoFunda-Delete-Funnel.md, sources/SwingEdge-Learn-Indicators-Deep-Dive]
---

# ADX — Average Directional Index

## Definition
Non-directional trend strength indicator. Part of the Directional Movement Index (DMI) system. It does not tell you to buy or sell — it tells you whether the market is trending strongly enough for breakout-style setups to make sense, or whether you're in chop where breakouts fail at high rates.

## Key Levels (refined, 2026-06-22)
| ADX Value | Meaning |
|-----------|---------|
| < 20 | No trend — breakouts fail more often than they continue; mean-reversion/range trades work better here |
| 20–25 | Early or weak trend — setup quality matters more than the indicator signal itself |
| 25–40 | **Actionable trend** — most breakouts that follow through happen in this zone |
| > 40 | Strong trend — pullbacks tend to be shallow/brief; adding to winners works, counter-trend trades fail badly |
| > 50–60 | Exhaustion zone — extreme readings often precede *consolidation*, not reversal, but reduce new-entry aggression here |

(Supersedes the earlier coarser 20/40 split — keep the 5-band table above as the working reference.)

## Components
- **+DI (Positive Directional Indicator):** Measures upward movement
- **-DI (Negative Directional Indicator):** Measures downward movement
- **ADX line:** Overall trend strength (direction-agnostic)

## Reading the Signal
- ADX rising + **+DI > -DI** = strong **uptrend**
- ADX rising + **-DI > +DI** = strong **downtrend**
- ADX falling = trend weakening regardless of direction
- **Slope matters more than absolute level**: ADX 28 rising from 22 is bullish for trend continuation; ADX 28 *falling* from 35 means the trend is losing strength even though the absolute reading still looks fine.
- DI crosses are sometimes used as standalone entries, but are better used as *confirmation* of price structure than as signals on their own.

## Application in Swing System
ADX > 20 is a prerequisite for entry in the full swing system.
If ADX < 20 = chop = no trade, even if all other signals align.

**Two-level regime filter (2026-06-22 addition)**: apply ADX both at the individual-stock level *and* at the index level (e.g. Nifty). A strong individual setup can still fail in index-level chop — low index ADX = reduce size or skip new trades altogether, regardless of how clean any single stock's chart looks.

## Measured Evidence (2026-08-26) — DI signals are not standalone entries

Backtested the ADX/DI rules directly (repo's own `_adx_di_series`, point-in-time,
20 liquid NSE names, **27,860 baseline bars, ~6y**; enter next open, exit
next-open+h close; edge = signal mean fwd − every-bar baseline mean fwd; Welch
two-sample p). This confirms the "confirmation, not signal" stance with numbers:

| Rule | n | 20d edge (p) | 60d edge (p) |
|---|---|---|---|
| Bullish +DI/−DI cross (bare) | 1042 | −0.05 (0.86) | **−1.01 (0.04)** * |
| DI-cross **and** ADX>25 rising (same bar) | 6 | — | — (fires almost never) |
| DI **state**: +DI>−DI, ADX>25 rising | 1091 | +0.10 (0.70) | +0.86 (0.10) |

- **The bare bullish DI cross has NEGATIVE forward edge** — significantly so at
  60d (−1.01%, p=0.04). By the time +DI crosses −DI the easy move is spent; you
  buy the lag. As a standalone *buy* trigger it underperforms a random bar.
- **A fresh cross almost never coincides with ADX already >25 and rising** (n=6 in
  6 years), so the "clean textbook" combined trigger is a near-nonexistent event —
  not a practical signal generator.
- **The confirmed DI+ADX *state* is ~neutral**, not predictive: flat at 5/10/20d,
  a weak +0.86% at 60d that is **not significant** (p=0.10). Being "in a confirmed
  uptrend per ADX/DI" does not itself beat the tape — it just says you're not in
  chop.
- **Takeaway (measured):** ADX/DI earns its place as a **regime/context filter and
  confirmation of a price+volume trigger**, never as the entry itself — exactly how
  the swing system and `scan` (`scanner_templates.py`) already use it. Caveats:
  liquid, mostly-trending universe, long-only, pre-cost (the cross's negative edge
  worsens after costs). Mirrors the [[strategies/TechnoFunda-Delete-Funnel]]
  price-leg finding: the mild edge lives in longer-horizon strength, not triggers.

## Common Mistakes
- Confusing ADX with a directional signal — it is strength-only; always pair with DI or price structure for direction.
- Using ADX on a single low-volume stock without checking liquidity — the math can break down on thin tickers.
- Ignoring the index-level ADX when trading individual stocks.
- Tuning the ADX period away from the default 14 to fit historical data — that's curve-fitting, not edge.

## Related
- [[strategies/TechnoFunda-Swing]] — ADX is one of 7 required conditions
- [[concepts/RSI]] — RSI for momentum, ADX for trend strength
- [[concepts/SuperTrend]] — the *SuperTrend + RSI + ADX* confluence uses **ADX crossing above 25** as the "is there a trend at all" gate before acting on a SuperTrend flip
- [[concepts/Multi-Timeframe-Analysis]] — index-level ADX regime check is a specific case of top-down MTF context

## Sources
- [[sources/SwingEdge-Learn-Indicators-Deep-Dive]] (2026-06-22) — 5-band value table, slope-over-level rule, two-level (stock + index) regime-filter application
- [[sources/Fingrad-Trading-Infographics-Collection]] (2026-07-19) — ADX>25 as the trend gate in the SuperTrend+RSI+ADX confluence setup
