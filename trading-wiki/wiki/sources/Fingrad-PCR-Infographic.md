---
title: "Fingrad — Put-Call Ratio (PCR) Infographic"
category: source
tags: [infographic, pcr, options, sentiment, open-interest, max-pain, hindi]
created: 2026-08-07
updated: 2026-08-07
sources: 1
related:
  - concepts/Put-Call-Ratio.md
  - concepts/Market-Sentiment-Index.md
  - analyses/PCR-in-OI-Momentum.md
---

# Source — Fingrad PCR Infographic

## Metadata
- **Type:** Single social-media infographic (image), Hindi/English mixed.
- **Title:** "Put-Call Ratio (PCR) क्या होता है? — Market Sentiment पहचानने का सबसे आसान तरीका"
- **Watermark:** FINGRAD. Same publisher as
  [[sources/Fingrad-Trading-Infographics-Collection]] (ingested 2026-07-19).
- **Supplied:** 2026-08-07, pasted into chat.
- **Bias:** Educational reference. No SEBI/registered-advisor status stated;
  generic technique material, not a market call.

## Key Takeaways

- **Definition:** PCR = Total Put OI ÷ Total Call OI (a Put Volume ÷ Call Volume
  variant is noted; the sheet says it uses the OI-based form).
- **Nine panels:** definition · worked example · interpretation · ideal range ·
  psychology · PCR + price action · practical example · trading strategy ·
  PCR vs Max Pain.
- **Bands given:** <0.70 bearish · 0.70–1.00 neutral · 1.00–1.30 bullish ·
  >1.30 very bullish positioning (and "sometimes a contrarian signal").
  It does caveat that thresholds are not fixed and shift with market conditions.
- **PCR + price action grid** (the most transferable panel): price↑/PCR↑ bullish
  confirmation; price↓/PCR↓ bearish confirmation; price↑/PCR↓ possible false
  breakout; price↓/PCR↑ possible short covering or reversal.
- **Psychology:** rising put OI is read as expected support, rising call OI as
  expected resistance — i.e. option writers' strikes as S/R.
- **PCR vs Max Pain:** PCR = market sentiment from the put/call split, best for
  trend analysis; Max Pain = probable expiry zone from total option OI, best for
  expiry analysis. A clean separation worth keeping.

## Detailed Notes

Worked example given: Put OI 18,00,000 and Call OI 12,00,000 → PCR 1.50.
Practical example: NIFTY 25,350 with PCR 1.18 and price making higher highs on
rising volume is called bullish strength; the same sheet says PCR reaching 1.70
would mean an overcrowded market with reversal potential.

Strategy panel splits by participant: **buyers** use PCR for trend confirmation
alongside price action and volume/OI; **sellers** watch extreme PCR levels and
use the put/call OI walls as support and resistance for hedging and risk
management.

## Errors and Contradictions

- **Arithmetic typo in panel 2.** It prints `PCR = 18,00,000 + 12,00,000 = 1.50`.
  The operator must be **÷**, not `+` (18 ÷ 12 = 1.50; the stated answer is
  correct, the symbol is not). Harmless here but it is the defining formula on a
  teaching sheet.
- **Unreconciled trend-following vs contrarian reading.** Panel 3 says PCR > 1
  is bullish; panels 4, 5 and 7 say extreme/high PCR is crowding and
  reversal-prone. Both are standard, and the sheet never says which regime
  selects which. Recorded as the central ambiguity on
  [[concepts/Put-Call-Ratio]] — it is a property of the indicator, not just of
  this source.
- **The bands do not survive contact with NSE stock options.** Measured on the
  2026-08-06 F&O bhavcopy, the median single-stock PCR is **0.675** and the
  sheet's scale labels **59% of 208 underlyings "bearish" and 5% "bullish"** on
  an ordinary session. The bands are index-calibrated (NIFTY 1.045, BANKNIFTY
  1.019 that day) and structurally wrong one level down. Full distribution and
  the reason on [[concepts/Put-Call-Ratio]].
- The image is OCR-noisy in places (garbled Devanagari in several caption
  lines); readings above are taken only from panels that were legible.

## Actionable Insights

1. **PCR is computable today at zero network cost** — the F&O bhavcopy
   `nse_oi_momentum.py` already downloads carries the option rows it filters
   out. This falsifies the "needs an option-chain feed" blocker recorded against
   `sentiment_index.py` factor 5.
2. **Do not ship these thresholds.** Use per-instrument-class percentiles from
   the observed cross-section.
3. **The price × PCR grid is the useful export**, not the level bands — it is
   the same confirm/diverge shape our OI-momentum quadrant already uses.
4. **Max Pain is a separate, unbuilt tool** with a clearly different purpose.
   Candidate for its own page if it is ever built.

## Pages Updated

- Created [[concepts/Put-Call-Ratio]]
- Created [[analyses/PCR-in-OI-Momentum]] (the "should it join the verdict"
  question this ingest was requested alongside)
- `wiki/index.md`, `wiki/log.md`
