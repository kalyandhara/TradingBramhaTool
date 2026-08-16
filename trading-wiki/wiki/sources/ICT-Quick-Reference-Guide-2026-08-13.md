---
title: "ICT Quick Reference Guide"
category: source
tags: [ICT, smart-money, market-structure, FVG, liquidity, OTE]
created: 2026-08-13
updated: 2026-08-13
sources: 1
related:
  - concepts/ICT-Methodology
  - concepts/Market-Structure-CHOCH-BOS
  - concepts/Fair-Value-Gap
---

# Infographic — ICT Quick Reference Guide

## Metadata
- **Author:** Inner Circle Trader (Michael J. Huddleston) — via community infographic
- **Date:** 2026-08-13 (user-provided screenshot)
- **Format:** 4-panel reference card
- **Raw file:** `.raw/images/ict-quick-reference-guide-2026-08-13.md`

## Key Takeaways

1. **Liquidity pools (BSL/SSL)** are the primary targets — price moves from one pool to the next, not from pattern to pattern.
2. **Inducement** is a deliberate trap: a false break above/below a pool lures retail entries, then institutions sweep the stops and reverse.
3. **MSS requires displacement** — a wide-range candle proving institutional participation. A soft BOS without displacement is just continuation noise.
4. **FVG + OTE is the entry trigger** — after MSS, price retraces into the 3-candle imbalance zone at 61.8–79% Fibonacci of the displacement leg.
5. **Stop above the displacement high** (or below the displacement low for shorts) — the logic being that if price re-enters the displacement candle's body, the thesis is wrong.

## Detailed Notes

### Liquidity & Inducement
- **BSL** (Buy Side Liquidity): resting stop orders above swing highs from retail shorts and breakout buyers.
- **SSL** (Sell Side Liquidity): resting stop orders below swing lows from retail longs.
- Inducement = a false breakout into a pool designed to flush retail stops before the institution's actual trade direction triggers. Differs from a real breakout only by what follows: an inducement reverses sharply, a real break displaces and holds.

### Market Structure Shift (MSS)
- MSS = CHoCH + displacement. The CHoCH alone is just a structure label; the displacement confirms institutions drove the break.
- BOS = continuation of existing trend direction. CHoCH = first counter-trend break.
- Displacement criteria (not specified numerically in the image, but canonical ICT): candle body > 50% of the range, no equal-size candles immediately before, volume above average.

### FVG & OTE
- FVG standard construction: gap between candle[0].high and candle[2].low in a bullish 3-bar sequence.
- OTE zone: Fibonacci 61.8%–79% retracement of the displacement leg (from leg start to BOS level).
- When FVG and OTE overlap, the probability zone is confirmed by two independent methods.

### Execution Blueprint
| Step | Action |
|------|--------|
| 1 | Spot MSS — BOS or CHoCH with displacement candle |
| 2 | Wait for pullback into FVG overlapping the OTE zone (61.8–79%) |
| 3 | Enter; stop loss above the displacement high (long) or below displacement low (short) |
| 4 | Target the opposite liquidity pool (SSL if long, BSL if short) |

## Actionable Insights

### What already exists in the chart tool
| ICT Concept | Existing Implementation |
|-------------|------------------------|
| BOS / CHoCH | `detect_bos_choch()` — swing-labeling walk in `scanner_templates.py:2296` |
| Bearish BOS / CHoCH | `detect_support_breakdown()` — `scanner_templates.py:2337` |
| FVG pullback entry | `scan_fvg_pullback()` — `scanner_templates.py:2781` |
| Horizontal structure break | `scan_structural_breakout()` — `scanner_templates.py:1457` (different concept, not ICT) |

### What ICT adds that is genuinely new
| ICT Concept | Gap |
|-------------|-----|
| BSL / SSL pool identification | No implementation — swing high/low clusters as explicit liquidity targets |
| Inducement sweep pattern | No implementation — false-break then sharp reversal before the real move |
| OTE zone (Fibonacci gate) | No implementation — 61.8–79% Fib of displacement leg |
| Displacement-qualified MSS | `detect_bos_choch()` uses close-above-pivot without requiring a displacement candle |
| Full 4-step execution sequence | No single composite scanner chains all four steps |

### Feasibility assessment
- **BSL/SSL**: implementable as `swing_high_cluster` scan — identify pivot highs within X% of each other over N bars. Medium effort.
- **Displacement qualifier**: add a `wide_range_body` check to `detect_bos_choch`. Low effort, high impact.
- **OTE zone**: `_fib_retracement(start, end, [0.618, 0.786])` is 5 lines, already have Fib math. Low effort.
- **Inducement**: hardest — requires identifying a false break (close beyond pivot then immediate reversal); needs a look-ahead window and definition of "immediate". Medium-high effort.
- **Composite ICT scanner**: chain displacement-MSS → OTE zone → FVG overlap → fire. Medium effort once the primitives exist.

## Contradictions with Existing Wiki

> [!contradiction] Displacement requirement vs current `detect_bos_choch`
> ICT's MSS requires a displacement candle (wide body, institutional quality). [[concepts/Market-Structure-CHOCH-BOS]] documents our implementation which detects BOS/CHoCH by close-above-pivot alone, with no displacement gate. This means we flag every structure break as equal-weight — exactly what ICT argues is wrong. Fix: add an optional `require_displacement=True` param to `detect_bos_choch`.

## Pages Updated
- [[concepts/ICT-Methodology]] (created)
- [[concepts/Market-Structure-CHOCH-BOS]] (cross-reference added)
- [[concepts/Fair-Value-Gap]] (OTE connection noted)
