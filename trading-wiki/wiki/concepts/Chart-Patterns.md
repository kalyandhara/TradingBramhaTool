---
title: "Chart Patterns"
category: concept
tags: [chart-patterns, technical-analysis, triangles, wedges, flags, channels, reversal, continuation]
created: 2026-08-11
updated: 2026-08-11
sources: 3
related:
  - concepts/Falling-Wedge.md
  - concepts/Candlestick-Patterns.md
  - concepts/Market-Structure-CHOCH-BOS.md
  - concepts/Support-Resistance.md
  - sources/StockEdge-Chart-Patterns-2026-08-11.md
  - sources/AGPro-Reversal-Pattern-Quality-Scanner-Pine.md
  - sources/Obsidian-Falling-Wedge-Screener-Prompt.md
---

# Chart Patterns

## Definition
Multi-bar price formations that traders classify by their geometry (converging lines, parallel channels, distinct peaks/troughs) and use to anticipate the next directional move. Classified as:
- **Continuation** — pattern resolves in the prior trend direction
- **Reversal** — pattern signals a trend change
- **Neutral / Bilateral** — pattern can resolve either way (most triangles)

---

## Category Taxonomy (StockEdge universe, as of Aug 2026)

| Category | Bias | # Stocks (Major universe) | Notes |
|----------|------|---------------------------|-------|
| Triangle Patterns | Neutral | 2,179 | Most common; includes ascending, descending, symmetrical |
| Multiple Top & Bottom | Reversal | 1,483 | Double/Triple Top and Bottom |
| Channel Patterns | Both | 1,304 | Rising/Falling/Horizontal — parallel trendlines |
| Wedge Patterns | Both | 672 | Converging; falling wedge = bullish reversal, rising wedge = bearish |
| Rounding Top & Bottom | Reversal | 514 | Slow arc reversals; rare in volatile environments |
| Flag Patterns | Continuation | 438 | Sharp pole + tight consolidation; bullish or bearish |
| Head & Shoulders | Reversal | 221 | Most selective; requires clear 3-peak structure + neckline |

> [!key-insight] **Triangle count (2,179) is 10× H&S count (221).** Triangles form continuously and don't expire until the breakout; H&S requires a very specific 3-peak structure. Large triangle counts indicate a compression phase in the market — many stocks coiling for a move.

---

## Triangle Patterns

### Symmetrical Triangle
- Both trendlines converge at similar slopes (one up, one down)
- **Neutral / bilateral** — breakout direction uncertain until the candle close
- Most frequent pattern in Indian equity markets
- StockEdge 2026 observation: 5 of 7 sym-triangle past entries resolved *upward* (small sample; treat as hypothesis)

### Ascending Triangle
- Flat upper trendline (resistance) + rising lower trendline (higher lows)
- **Bullish continuation** bias — buyers pressuring a fixed supply zone
- Examples: Hyundai Motor India (+6.5%), CRISIL (+5.4%)

### Descending Triangle
- Flat lower trendline (support) + falling upper trendline (lower highs)
- **Bearish continuation** bias

---

## Reversal Patterns

### Double Top / Triple Top
- Price tests a resistance level twice (or thrice), fails both times → bearish
- Confirmed on break below the "neckline" (the trough between the two peaks)
- StockEdge accuracy (small sample): CE Info -17.7%, ZEE -22.6%, Supreme -13%. Failure cases: Pine Labs +1.9%

### Double Bottom / Triple Bottom
- Mirror of Double Top → bullish reversal
- Example: Jubilant FoodWorks published 408.55 → LTP 488.20 (+19.5%)

### Head & Shoulders (H&S)
- Left shoulder + head (higher peak) + right shoulder → neckline break → bearish
- Inverse H&S = bullish reversal
- Rarest pattern by count; most selective criterion

### Rounding Bottom (Saucer)
- Slow, arc-shaped accumulation; no sharp pivot points
- See [[sources/SwingEdge-Rounding-Bottom-Screener-20260703]] for detection algorithm

---

## Continuation Patterns

### Flag / Pennant
- Sharp impulse (pole) followed by tight consolidation (flag)
- Flag = parallel channel consolidation; Pennant = converging (small triangle)
- Bullish Flag or Bearish Flag depending on pole direction
- Example: Gallantt Ispat Bearish Flag published 618.50 → LTP 593.50 (-4%)

### Channel (Rising / Falling / Horizontal)
- Price oscillates between two parallel trendlines
- Falling channel = bearish trend; rising channel = bullish trend
- Key risk: **mean-reversion within the channel** vs **breakout from it** — two opposite trades
- StockEdge outcome split: Falling Channels had mixed results — Hero MotoCorp +18.7% (channel breakout upward), Supreme Petrochem -9%, Mahindra +9.1%

---

## Wedge Patterns

### Falling Wedge
- Both trendlines slope downward, upper steeper than lower → converging downward
- **Bullish reversal** signal — selling is losing momentum
- Example: Muthoot Finance published 3,068.97, LTP 2,915.90 (-5%) — failed near-term; pattern not yet resolved
- See [[concepts/Falling-Wedge]] for detection algorithm

### Rising Wedge
- Both trendlines slope upward, lower steeper than upper → converging upward
- **Bearish reversal** signal — buying is losing momentum
- Example: PNB Housing Finance published 1,073.38 → LTP 1,142.10 (+6.4%) — failed (price continued higher)

---

## How to Use

1. **Pattern = screen, not signal.** Chart patterns are candidates. A Double Top tells you *where* supply may overwhelm demand; it does not tell you *when* or *if* the pattern will resolve. Always require a breakout/breakdown confirmation candle.
2. **Quality gate matters.** StockEdge's AI detects presence; [[sources/AGPro-Reversal-Pattern-Quality-Scanner-Pine]] adds 5-factor scoring (symmetry, depth, volume, location, time). The ~50% failure rate on confirmed bearish patterns in the Aug 2026 StockEdge snapshot argues that presence alone is insufficient.
3. **Market regime context.** In a downtrend (Nifty breadth <30%), bearish patterns resolve more reliably. In an uptrend, bearish patterns fail often (Hero MotoCorp +18.7% despite Falling Channel label).
4. **Volume confirmation on breakout.** See [[concepts/Volume-Analysis]] for thresholds (≥1.5× 20-day average = above-average; ≥2× = high conviction).

---

## Common Mistakes

- **Trading the pattern, not the breakout.** Entry inside the pattern is counter-productive — the resolution can go either way until the close beyond the boundary.
- **Ignoring HTF context.** A bullish triangle inside a weekly downtrend is a lower-probability setup.
- **Conflating pattern type with edge.** H&S has fewer occurrences because the criterion is strict, not because it has better accuracy. Accuracy data is pattern- and market-specific.

---

## Related Concepts
- [[concepts/Falling-Wedge]] — detection algorithm + scanner fit
- [[concepts/Candlestick-Patterns]] — single/two-bar patterns at the trigger point
- [[concepts/Market-Structure-CHOCH-BOS]] — BOS/CHoCH as a confirmation layer for pattern breakouts
- [[concepts/Support-Resistance]] — necklines and pattern boundaries as S/R zones
- [[concepts/Volume-Analysis]] — volume confirmation thresholds

---

## Sources
1. [[sources/StockEdge-Chart-Patterns-2026-08-11]] — 20 Major Stock pattern outcomes, category universe counts
2. [[sources/AGPro-Reversal-Pattern-Quality-Scanner-Pine]] — 5-factor quality scoring for Double Top/Bottom and H&S
3. [[sources/Obsidian-Falling-Wedge-Screener-Prompt]] — full Falling Wedge detection algorithm
