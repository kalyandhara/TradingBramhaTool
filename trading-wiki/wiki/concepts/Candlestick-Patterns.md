---
title: "Candlestick Patterns"
category: concept
tags: [candlestick, reversal, continuation, patterns, price-action, psychology]
created: 2026-06-19
updated: 2026-06-19
sources: 1
related:
  - concepts/Sakata-Method.md
  - concepts/Support-Resistance.md
  - strategies/Candlestick-Filtering.md
  - sources/Litchfield-Morris-Candlestick-Charting-Explained-2006.md
---

# Candlestick Patterns

## Definition
Japanese candlestick patterns are short-term price formations (1–6 bars) that encode the psychology of buyers and sellers through the relationship of open, high, low, and close prices. Each candle body represents the open-to-close range; shadows represent intraday extremes that were rejected.

**Rule #1: Identify the trend first.** A bullish reversal pattern requires a prior downtrend. A bearish reversal requires a prior uptrend. Without trend context, all pattern signals are meaningless.

---

## Candle Anatomy

| Component | Meaning |
|-----------|---------|
| Long white/green body | Bulls dominated; strong close above open |
| Long black/red body | Bears dominated; strong close below open |
| Long lower shadow | Bears initially pushed price down; bulls recovered |
| Long upper shadow | Bulls pushed high; bears rejected the move |
| No shadows (Marubozu) | Complete control open-to-close; no intraday reversal |
| Small body / Doji | Open ≈ close; indecision; power depends on prior trend |

**Long vs Short:** Relative to the most recent 5–10 bars. Context-dependent, not absolute.

---

## Yin (Bearish) and Yang (Bullish) Lines — 9 Basic Types

1. Long white (yang)
2. Long black (yin)
3. Short white
4. Short black
5. Marubozu white (no shadows)
6. Marubozu black
7. Spinning top (small body, long shadows)
8. Doji (open = close)
9. Long-legged doji / Gravestone doji / Dragonfly doji

---

## Reversal Patterns

### Single-Bar Patterns

| Pattern | Setup | Signal |
|---------|-------|--------|
| **Hammer** | Long lower shadow ≥ 2× body; small/no upper shadow | Bullish reversal from downtrend |
| **Hanging Man** | Same shape as hammer | Bearish reversal from uptrend |
| **Inverted Hammer** | Long upper shadow; small body at bottom of range | Bullish reversal (requires confirmation next day) |
| **Shooting Star** | Long upper shadow; small body; gap up at open | Bearish reversal from uptrend |
| **Dragonfly Doji** | Open = close at high; long lower shadow | Bullish reversal |
| **Gravestone Doji** | Open = close at low; long upper shadow | Bearish reversal |
| **Belt Hold (Yang/Yin)** | Open at extreme; no shadow on open side; strong body | Reversal in direction of body color |

### Two-Bar Patterns

| Pattern | Structure | Signal |
|---------|-----------|--------|
| **Engulfing (Bullish)** | Small bearish bar + large bullish bar that engulfs body | Strong bullish reversal |
| **Engulfing (Bearish)** | Small bullish bar + large bearish bar engulfs body | Strong bearish reversal |
| **Harami (Bullish)** | Large bearish bar + small body inside previous body | Bearish momentum slowing |
| **Harami (Bearish)** | Large bullish bar + small body inside | Bullish momentum slowing |
| **Harami Cross** | Harami where second bar is a doji | Stronger indecision signal |
| **Piercing Line** | Gap-down open then close > 50% into prior black body | Bullish reversal |
| **Dark Cloud Cover** | Gap-up open then close < 50% into prior white body | Bearish reversal |
| **Meeting Lines** | Two opposite bars close at same price | Possible reversal |
| **Tweezers (Top/Bottom)** | Same high or same low on consecutive days | Momentum exhaustion |

### Three-Bar Patterns

| Pattern | Structure | Signal |
|---------|-----------|--------|
| **Morning Star** | Large black → small body gap lower → large white > 50% into black | Strong bullish reversal |
| **Evening Star** | Large white → small body gap higher → large black > 50% into white | Strong bearish reversal |
| **Doji Star (Morning/Evening)** | Star bar is a doji | Stronger than regular star |
| **Abandoned Baby** | Large body → doji gaps completely away from both sides → large reversal body | Rare; very strong reversal |
| **Three White Soldiers** | 3 consecutive long white bodies; each opens inside prior body; closes near high | Strong bullish reversal (after downtrend) or trend exhaustion (in uptrend) |
| **Three Black Crows** | 3 consecutive long black bodies | Strong bearish reversal |
| **Upside Gap Two Crows** | White body → gap-up small black → larger black that closes gap | Bearish reversal |
| **Unique Three River Bottom** | Three-bar bullish reversal; third closes black but above second low | Bullish reversal |

---

## Continuation Patterns

### Two-Bar

| Pattern | Signal |
|---------|--------|
| **Separating Lines (Ikichigaisen)** | Same open, opposite colors; confirms trend resumption after one-bar contra move |
| **On Neck Line** | Second bar closes at low of first; bearish continuation |
| **In Neck Line** | Second bar closes slightly into first body; bearish continuation |
| **Thrusting Line** | Closes below midpoint of prior bar; bearish continuation |

### Three-Bar

| Pattern | Signal |
|---------|--------|
| **Upside/Downside Tasuki Gap** | Gap maintained; partial fill via contra bar; gap hold = continuation |
| **Side-by-Side White Lines** | Two same-color bars at same level; bullish continuation |
| **Upside/Downside Gap Three Method** | Gap → two small contra bars → gap still intact | continuation |

### Four+ Bar

| Pattern | Signal |
|---------|--------|
| **Rising Three Methods** | Long white → 3 small black inside range → long white above; strongest bullish continuation |
| **Falling Three Methods** | Long black → 3 small white inside range → long black below; strongest bearish continuation |
| **Mat Hold** | Variant of three methods with gap preserved through consolidation |
| **Three-Line Strike** | 3 bars + a 4th that engulfs all three; implies exhaustion pause then resumption |

---

## Statistical Reliability (Morris, 2006 — 7,275 stocks, 13+ years, 14.6M days)

- Average %Win across all patterns: **41–64%**
- Only **5 patterns** exceed 59% win rate
- Best prediction horizon: **2 days after pattern** → ranked #1 vs 14 technical indicators
- At 1-day horizon: ranked 5th
- **Key implication:** Candle patterns alone provide a modest edge; filtering with a second indicator is required for consistent outperformance

---

## How to Use

1. **Establish trend** (EMA is simplest: price above/below 10–21 day EMA)
2. **Identify a pre-signal condition** in a second indicator (RSI near oversold, price at S/R zone, MACD diverging)
3. **Wait for candle pattern confirmation** within the pre-signal zone
4. **Measure reliability**: long shadows, volume expansion, gap from prior bar all increase signal strength
5. **Target 2-day horizon** for initial profit assessment; manage with trailing stop

---

## Common Mistakes
- Trading reversal patterns mid-trend (no prior trend context)
- Treating doji as a signal without trend exhaustion (doji in the middle of a trend = noise)
- Ignoring volume — high-volume confirmation dramatically improves reliability
- Over-relying on pattern alone without a filter
- Using candle patterns on intraday data below daily: overnight gap psychology is the core mechanic; intraday bars don't have this

---

## Variants / Parameters
- **Intraday application:** authors note Japanese tradition firmly places candlestick analysis on daily data; the overnight sentiment shift between close and open is the psychological driver; 10-minute candles don't carry this
- **Open price unavailability:** if open is unavailable, previous close substitutes; this eliminates some patterns (Inverted Hammer, Dark Cloud Cover, Kicking, etc.)
- **CandleVolume/CandlePower:** body width proportional to volume; visually confirms volume-backed moves

---

## Related Concepts
- [[concepts/Sakata-Method]] — the historical 5-formation system underlying continuation patterns
- [[concepts/Support-Resistance]] — the most effective filter for candle signals (Litchfield's framework)
- [[strategies/Candlestick-Filtering]] — systematic methodology for combining candles with indicators
- [[concepts/Elliott-Wave]] — can provide trend context for candle pattern identification
- [[concepts/RSI]] — common presignal filter; RSI oversold + hammer = high-quality entry

## Sources
- [Litchfield-Morris-Candlestick-Charting-Explained-2006](../sources/Litchfield-Morris-Candlestick-Charting-Explained-2006.md)
