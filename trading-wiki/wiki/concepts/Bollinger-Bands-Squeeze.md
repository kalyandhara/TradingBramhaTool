---
title: "Bollinger Bands — Squeeze & Band Walk"
category: concept
tags: [volatility, bollinger-bands, squeeze, band-walk, percent-b]
created: 2026-06-22
updated: 2026-06-22
sources: 1
related: [concepts/VCP, concepts/ADX, concepts/EMA, sources/SwingEdge-Learn-Indicators-Deep-Dive]
---

# Bollinger Bands — Squeeze & Band Walk

## Definition
A 20-period SMA (middle band) with upper/lower bands placed 2 standard deviations above/below it. Statistically ~95% of price action sits inside the bands. Bands measure **volatility**, not direction — the common mistake is treating a band touch as an automatic reversal signal.

## How to Use

### The squeeze
When the upper and lower bands contract toward each other, bandwidth is at a multi-month/multi-quarter low — volatility has collapsed. Historically, periods of unusually low volatility precede periods of unusually high volatility. **The squeeze does not predict direction — it predicts that something is coming.** This is the same underlying phenomenon as the "ATR shrinking 3 consecutive weeks" / "BB squeeze" flags repeatedly seen in the SwingEdge stock-detail ingests (KDDL, SIGMA, etc.) and is one input into [[concepts/VCP]]'s volatility-contraction detection.

- **Bollinger Bandwidth** = (upper − lower) / middle. Six-month lows in bandwidth are the most powerful squeezes.
- The actionable trade is the **close** beyond the bands when the squeeze resolves — a single bar piercing the band and reversing is a false resolution; wait for the close, not the wick.
- Squeezes resolving in the direction of the larger trend have higher follow-through than counter-trend resolutions.
- A squeeze inside a tight base under resistance is a far better setup than a squeeze in chop — combine with structure, don't trade the squeeze in isolation.

### Band walk — continuation, not reversal
In a strong trend, price pins against the upper (or lower) band and "walks" along it, sometimes for weeks. This is the highest-momentum tape — the classic amateur mistake is shorting the "overbought" name during a band walk. The trade is to stay long with it, manage with a trailing stop, and exit only when price closes back inside the middle band on volume.

### Middle band as dynamic mean
The 20 SMA at the center is the same short-term mean many traders already watch. In trending tape, pullbacks to the middle band that hold and reverse are low-risk continuation entries; pullbacks that pierce it and start using it as resistance are early signs of trend fatigue.

### %B and bandwidth as scan features
- **%B** normalizes price within the bands (0 = at lower band, 1 = at upper band). %B > 0.95 with rising bandwidth signals strong breakout potential.
- **Bandwidth percentile** shows where current volatility sits historically — below the 10th percentile is a textbook squeeze.
- Combining %B with regime (e.g. MACD position, see [[concepts/MACD-Divergence]]) and structure (recent base) outperforms using any single one alone.

## Common Mistakes
- Selling at the upper band as "overbought" in a trending stock — band walks are continuation, not reversal.
- Treating every band touch as a mean-reversion signal — that only works in chop; diagnose the regime first (cf. [[concepts/ADX]]).
- Ignoring bandwidth — a band touch without volatility context is close to meaningless.
- Using default 20/2 settings in every market — for thinly-traded names, a longer period reduces noise.

## Related Concepts
- [[concepts/VCP]] — squeeze/bandwidth contraction is one of the inputs informal VCP detection draws on
- [[concepts/ADX]] — pair band-walk reads with a trend-strength filter to avoid mistaking chop-range touches for genuine continuation
- [[concepts/EMA]] — the middle band (20 SMA) plays a similar dynamic-support role to the 20 EMA

## Sources
- [[sources/SwingEdge-Learn-Indicators-Deep-Dive]] (2026-06-22) — squeeze/bandwidth formula, band-walk framing, %B scan usage
- [[sources/Fingrad-Trading-Infographics-Collection]] (2026-07-19) — squeeze uptrend/downtrend entry-exit walkthrough; middle-band entry/exit rule (restates the above; corroborating reference)
