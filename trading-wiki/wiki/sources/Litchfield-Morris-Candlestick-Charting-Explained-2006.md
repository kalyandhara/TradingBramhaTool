---
title: "Book — Candlestick Charting Explained (Litchfield & Morris, 2006)"
category: source
tags: [candlestick, technical-analysis, patterns, statistics, filtering, sakata]
created: 2026-06-19
updated: 2026-06-19
sources: 1
related:
  - concepts/Candlestick-Patterns.md
  - concepts/Sakata-Method.md
  - strategies/Candlestick-Filtering.md
  - concepts/Support-Resistance.md
---

# Book — Candlestick Charting Explained (Litchfield & Morris, 2006)

## Metadata
- **Authors:** Gregory L. Morris (original) + Ryan Litchfield (Ch. 10 addition)
- **Edition:** 3rd edition, McGraw-Hill, 2006 (1st ed. 1992)
- **File:** epub, ~30 HTML chapters
- **Scope:** Complete candlestick reference: anatomy → patterns → statistical validation → filtering → trader application

## Key Takeaways

1. **Trend first, always.** Candle patterns are meaningless without identifying the current short-term trend first. A bullish reversal requires an existing downtrend; a bearish reversal requires an uptrend. This is the single most violated rule by candlestick users.
2. **Statistics are sobering.** Across 7,275 stocks, 13+ years, 14.6M days, 1.7M patterns: average %Wins ranges 41–64%. Only 5 patterns break 59%. Candle patterns alone don't give an overwhelming edge.
3. **Candles + filter = the real edge.** When candlestick patterns are combined with a presignal filter from another indicator (RSI, MACD, stochastic, etc.), performance improves dramatically and consistently outperforms most technical indicators.
4. **Best horizon: 2 days.** Candle pattern signals measured 2 days after the pattern ranked #1 among 14 technical indicators. At 1 day they ranked 5th. They are explicitly short-term tools.
5. **Sakata's Method is the foundation.** All candle pattern philosophy derives from 160 rules written by Munehisa Honma (Sakata, 1750s). The five core formations (San=mountains/rivers/method; Go=five) underlie every continuation pattern.
6. **Anatomy encodes psychology.** Body length, shadow length, gap from prior day, and color each convey a specific psychological narrative (who controlled the day, where sentiment shifted).
7. **CandlePower/CandleVolume** adds volume as body width — wide = heavy volume, thin = light. Engulfing on high volume is more bullish; Morning Star with heavy last-day volume is more reliable.

## Detailed Notes

### Chapter 2 — Candle Anatomy
- **Long day:** body significantly larger than recent 5–10 days; strong one-sided control
- **Short day / Doji:** open ≈ close; indecision; most powerful when prior trend is strong
- **Marubozu:** no shadows (close-cropped); pure control from open to close
- **Spinning tops:** small body, long shadows; indecision / balance of power
- **Shadows:** lower shadow = buyers pushed back intraday; upper shadow = sellers capped the move
- **9 basic yin (bearish) / yang (bullish) lines** → expanded to 15 for nuance

### Chapter 3 — Reversal Patterns (single → multi-candle)
Key bullish reversal patterns:
- **Hammer** (1-bar): long lower shadow ≥ 2× body; occurs in downtrend; hanging man is identical in uptrend (bearish)
- **Inverted Hammer** / **Shooting Star**: long upper shadow; inverted hammer in downtrend = bullish; shooting star in uptrend = bearish
- **Engulfing:** 2-bar; second body completely engulfs first; more reliable with volume expansion
- **Harami:** 2-bar; small body inside prior large body; indecision/reversal
- **Dark Cloud Cover / Piercing Line:** 2-bar; close into the opposite body's midpoint
- **Morning Star / Evening Star:** 3-bar; middle bar gaps away (small body/doji), third bar confirms reversal
- **Three White Soldiers / Three Black Crows:** 3 consecutive long bodies; trend exhaustion reversal
- **Abandoned Baby:** 3-bar; middle is a doji that gaps away from both neighbours; rare, strong reversal

### Chapter 4 — Continuation Patterns
- **Separating Lines (Ikichigaisen):** same open, opposite colors; trend continuation confirmed
- **On/In Neck / Thrusting Lines:** 2-bar; second day closes at or near previous close; bearish continuation
- **Upside/Downside Tasuki Gap:** 3-bar; gap maintained; continuation with brief pullback
- **Rising/Falling Three Methods:** 5-bar (1 long + 3 short inside + 1 long resumption); strongest continuation pattern; consolidation before continuation
- **Mat Hold:** variant of Three Methods; gap preserved; very bullish

### Chapter 5 — Sakata's Method → see [[concepts/Sakata-Method]]

### Chapter 7 — Reliability Statistics
- Tested on S&P 100 and all NYSE/Nasdaq/Amex stocks (7,275 issues, 13+ years, 14.6M days)
- %Win range: **41–64%**; only 5 patterns exceed 59%
- Candles measured at **prediction intervals** of 1–7 days after pattern
- At 1-day: ranked 5th among 14 indicators
- At **2-day: ranked #1** among all 14 technical indicators
- Trend identification = exponential moving average; if price above EMA → uptrend

### Chapter 8 — Performance vs 14 Indicators
- 14 indicators tested at popular parameters
- Candles(2) = best performer; **candles are short-term tools**
- Tables 8-1 through 8-7: rankings shift by prediction interval
- Tables 8-8 to 8-9: alternative success measurements

### Chapter 9 — Filtering → see [[strategies/Candlestick-Filtering]]

### Chapter 10 — Ryan Litchfield: Candlesticks for Traders
- Integrate candles with **Western support and resistance** at key price structure levels
- Use candles to time entries INTO pre-identified S/R zones (not as standalone signals)
- Candle pattern at a zone dramatically increases signal reliability
- Litchfield was teaching trading seminars in Dallas; Morris added this chapter for practical application context

### Appendix A — Interview with Mr. Takehiro Hikita (Japanese trader)
- Started candlestick trading in his early 40s; all charting by hand until PCs arrived
- Used IBM-5100 (32K memory, 1977), Apple II (1979) for early chart analysis
- Hikita insists: understand the **psychology** behind each pattern, not just the shape
- Japanese practitioners never divorced candle pattern study from market psychology

### Appendix B — Derivative Methods: CandlePower / CandleVolume
- Body width = volume for that day; wide body = high volume, thin = low volume
- Visual immediate recognition of volume-confirmed moves
- Bullish Engulfing with wide second body = strongest bullish signal
- Morning Star with wide third-body = high-confidence reversal

## Actionable Insights
1. **Never trade a candle pattern without first labeling the trend** (EMA filter is simplest: price above/below)
2. **Apply a presignal filter** before candle confirmation: RSI near oversold, MACD diverging, price at S/R → then wait for the candle pattern
3. **2-day measurement horizon**: set profit targets and stops with a 2-day window in mind for pattern-based trades
4. **Prefer patterns with volume confirmation**: Morning Star / Engulfing / Three Soldiers all get stronger with expanding volume on the confirmation bar
5. **S/R + Candle = combined signal**: Litchfield's framework aligns directly with the existing Supply-Demand-Zone-Trading strategy — use S&D zones as the filter, candle pattern as the entry trigger
6. **Memorizing patterns is secondary**: understand yin/yang (body size + shadow) psychology; patterns are just repeatable expressions of that psychology

## Contradictions with Existing Wiki
- None. The filtering philosophy reinforces [[strategies/Supply-Demand-Zone-Trading]] and [[concepts/Support-Resistance]] — candles are the entry trigger, S/R zones are the filter.
- Statistics validate the general wiki principle that no single indicator is sufficient alone.

## Pages Created / Updated
- Created: `concepts/Candlestick-Patterns.md`, `concepts/Sakata-Method.md`, `strategies/Candlestick-Filtering.md`
- Updated: `wiki/index.md`, `wiki/log.md`
