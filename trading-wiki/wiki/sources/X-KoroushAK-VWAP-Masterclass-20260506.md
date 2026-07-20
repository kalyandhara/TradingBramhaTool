---
title: "X Article — Koroush AK: VWAP Masterclass"
category: source
tags: [vwap, indicators, breakout, reversal, momentum, mean-reversion, crypto]
created: 2026-07-06
updated: 2026-07-06
sources: 1
related: [concepts/VWAP, concepts/Anchored-VWAP-Pyramiding]
---

# X Article — Koroush AK: VWAP Masterclass

## Metadata
- **Author:** Koroush AK (@KoroushAK) — crypto trader, 9 years, 378K followers
- **URL:** https://x.com/KoroushAK/status/2052011140410925333 (X long-form article, id 2050699973017407488)
- **Posted:** 2026-05-06 (modified 2026-05-08)
- **Title:** "VWAP Masterclass: Indicators, Strategy and Trade Examples"
- **Engagement:** 606 likes, 1414 bookmarks, 323K views
- **Format:** X long-form article — 3 lessons + student trade examples (Brandon, Josh, Kim from author's coaching team)
- **Date accessed:** 2026-07-06

## Key Takeaways
- **VWAP = volume-weighted average price** — anchor price the market gravitates around; filters out low-volume spikes that mislead unweighted averages.
- **Chart setup (author's TradingView defaults):** Anchor = Session (resets daily); Bands = ±1 standard deviation; VWAP light blue, bands dark blue/purple.
- **3 signals to read off VWAP** — position, slope, bandwidth. These jointly decide *direction* and *strategy type*.
- **Directional bias:** price above VWAP → uptrend (favours longs / breakouts); below → downtrend (favours shorts / breakdowns). Above both VWAP *and* upper band = extra strength.
- **Strategy bias — the core decision rule:**
  - Steep slope + wide bands → **momentum / continuation** (breakout play)
  - Flat slope + tight bands → **mean reversion** (reversal play)
- **Slope crossovers as confluence:** fewer VWAP-price crossovers = cleaner trend = favours momentum; frequent crossovers = chop = favours reversal.
- Author frames VWAP as a "level 3" tool in his trader roadmap — not for absolute beginners; assumes basic S/R and trend-reading skill first.

## Detailed Notes

### Lesson 1 — What VWAP is
- Weights each price tick by traded volume, so quick low-volume spikes don't move the line: "if 90% of trades happen at $10 but price briefly spikes to $12, VWAP stays near $10."
- Bands at ±1 SD show how far price is stretching from the anchor — proxy for realized volatility of the session.
- Three signal channels the author isolates:
  1. **Position** of price vs. VWAP → breakout vs. breakdown regime
  2. **Slope** of VWAP → trending vs. ranging
  3. **Bandwidth** → conviction / continuation vs. hesitation / reversal

### Lesson 2 — VWAP for Breakout Strategies (momentum / continuation)
Setup for a momentum long:
- Directional bias: price above VWAP (bonus: above upper band too)
- Strategy bias: steep VWAP slope + widening bands as price approaches the breakout level
- Fewer VWAP-price crossovers on the run-up = trend cleanliness

Real trades cited (author's coaches):
- **Brandon — breakdown short.** Price below both VWAP and lower band; as price approached previous-day low, slope steepened and bands widened → grabbed the momentum leg.
- **Josh — momentum long in crypto.** Price above VWAP and upper band; steep slope + widening bands justified entering *after* the initial move rather than fading it (a common crypto continuation pattern the author flags).

### Lesson 3 — VWAP for Reversal Strategies (mean reversion)
Setup for a reversal:
- Strategy bias: flat VWAP slope + tight bands = chop / weak conviction
- Multiple VWAP-price crossovers = the "market is choppy" tell — reversal edge is highest here

Real trades cited:
- **Brandon — reversal short.** Tight bands, flat slope → classic mean-reversion setup.
- **Kim — avoided a fakeout.** Price ripped higher, looked like continuation, but VWAP stayed flat with tight bands and multiple crossovers → classified as reversal, not continuation, and avoided chasing.

### Combined decision matrix (reconstructed from the article)
| Slope | Bands | Directional bias | Play |
|-------|-------|------------------|------|
| Steep up | Widening | Price > VWAP (best: > upper band) | Momentum long / breakout |
| Steep down | Widening | Price < VWAP (best: < lower band) | Momentum short / breakdown |
| Flat | Tight | Either side | Reversal / mean reversion |
| Flat | Tight, many crossovers | Price faking a breakout | Fade the move |

## Actionable Insights
- **Adopt the ±1 SD session-anchored VWAP** as the default working setup on any intraday chart in the dashboard — matches the author's config and the "level 3" idea that VWAP is a filter, not a signal generator.
- **Use the 3-signal read (position / slope / bandwidth) before every intraday entry.** If any two of the three disagree, downgrade conviction — the article's examples are all "all three agree" setups.
- **Bandwidth as regime switch:** Wide+steep → treat setups as continuation. Tight+flat → treat setups as mean reversion. This maps cleanly onto the existing dashboard split between breakout screeners and reversal-calendar work.
- **Fakeout guard:** flat VWAP slope + multiple crossovers overrides an apparent breakout — worth codifying as a filter in the Scanner Hub / Breakout Screener rather than trusting price action alone.
- **Cross-timeframe use is not covered** — author sticks to session VWAP. For multi-day setups, cross-reference the existing [[concepts/Anchored-VWAP-Pyramiding]] which uses AVWAP from an event anchor rather than session reset.

## Contradictions with Existing Wiki
- None. Complements [[concepts/Anchored-VWAP-Pyramiding]] (event-anchored, swing timeframe) with a session-anchored, intraday framing. The two are compatible: session VWAP for intraday direction, anchored VWAP from an event low/high for pyramiding stops on the swing.
- Author's "price above VWAP = uptrend" is consistent with the VWAP condition already in [[strategies/TechnoFunda-Swing]] — but that strategy uses close > VWAP as a binary gate rather than reading slope/bandwidth. Worth extending that gate to also require non-flat slope on entry day.

## Pages Updated
- Created: `wiki/concepts/VWAP.md`
- Updated: `wiki/index.md` (added source and concept rows), `wiki/log.md`
