---
title: "ICT Methodology"
category: concept
tags: [ICT, smart-money, liquidity, MSS, FVG, OTE, market-structure]
created: 2026-08-13
updated: 2026-08-13
sources: 1
related:
  - concepts/Market-Structure-CHOCH-BOS
  - concepts/Fair-Value-Gap
  - concepts/Fair-Value-Breaker-FBG
  - sources/ICT-Quick-Reference-Guide-2026-08-13
  - sources/LuxAlgo-Smart-Money-Concepts-Pine
---

# ICT Methodology

## Definition

A price-action framework developed by **Michael J. Huddleston (Inner Circle Trader)** centered on the premise that institutional order flow drives price from one **liquidity pool** to another. Entry is taken only after a **Market Structure Shift (MSS)** confirmed by displacement, at the **Optimal Trade Entry (OTE)** zone inside a **Fair Value Gap (FVG)**.

> [!key-insight] The core thesis
> Markets do not trend randomly — they hunt liquidity. Every swing high is a BSL pool; every swing low is an SSL pool. The move from one pool to the next is the trade. Everything else (MSS, FVG, OTE) is the timing layer that tells you *when* the hunt is underway, not *where* it's going.

---

## The Four Primitives

### 1. Liquidity Pools (BSL / SSL)

| Pool | Location | What's resting there |
|------|----------|---------------------|
| **BSL** (Buy Side Liquidity) | Above swing highs | Stop-loss orders from retail shorts; breakout buy orders |
| **SSL** (Sell Side Liquidity) | Below swing lows | Stop-loss orders from retail longs; breakdown sell orders |

Price moves *to* pools (stop hunt / liquidity sweep), not away from them. Target = the pool on the opposite side of the entry.

**Inducement** is a false breakout into a pool. Visually it looks like a pool has been swept, but price reverses sharply before continuing in the original direction. The tell: the sweep is not followed by a displacement candle or structure change.

### 2. Market Structure Shift (MSS)

MSS = **CHoCH (Change of Character) + displacement candle**.

| Term | Definition |
|------|-----------|
| **BOS** | Break of Structure — price closes beyond a prior swing high/low in the *same* trend direction |
| **CHoCH** | Change of Character — first counter-trend structure break (prior swing broken against trend) |
| **Displacement** | A qualifying candle: wide body (>50% of range), no clustering of same-size candles before it, volume above average — proves institutional participation |
| **MSS** | CHoCH confirmed by displacement. Without displacement a CHoCH is just noise |

A standard `detect_bos_choch` implementation (close-above-pivot) fires on every CHoCH regardless of displacement. The ICT filter adds the displacement gate.

### 3. Fair Value Gap (FVG)

Standard 3-candle construction:
- **Bullish FVG**: `candle[0].high < candle[2].low` — gap between top of bar 1 and bottom of bar 3
- **Bearish FVG**: `candle[0].low > candle[2].high`

The displacement candle is typically candle[1] — the large institutional move creates the gap. This is identical to the [[concepts/Fair-Value-Gap]] definition already in the wiki, but ICT adds a crucial gate: **only FVGs formed during an MSS displacement are actionable**. Random FVGs without a preceding MSS carry no institutional authority.

See [[sources/FVG-Zeiierman-MTF-Pine]], [[sources/FVG-DGT-Pine]], [[sources/FVG-LuxAlgo-Pine]] for prior FVG work in this wiki.

### 4. Optimal Trade Entry (OTE)

**OTE = 61.8% – 79% Fibonacci retracement of the displacement leg.**

The displacement leg spans from the last swing low (for a bullish MSS) to the BOS high. The OTE zone is:
- `fib_618 = bos_high - 0.618 × (bos_high - swing_low)`
- `fib_786 = bos_high - 0.786 × (bos_high - swing_low)`

When the OTE zone overlaps with the FVG, confidence is highest. Both methods independently point to the same price area.

---

## Execution Blueprint

```
1. Identify BSL/SSL pools on HTF (the destination)
2. Wait for MSS: CHoCH + displacement candle → trend has shifted
3. Wait for pullback into FVG that overlaps OTE zone (61.8–79%)
4. Enter at the FVG/OTE confluence
   - Stop: above the displacement high (longs) / below displacement low (shorts)
   - Target: the opposite liquidity pool (SSL → BSL or BSL → SSL)
```

---

## Implementation Status in This Repo

| Primitive | Status | File / Function |
|-----------|--------|-----------------|
| BOS / CHoCH detection | ✅ Shipped | `scanner_templates.py:2296` `detect_bos_choch()` |
| Bearish BOS / CHoCH | ✅ Shipped | `scanner_templates.py:2337` `detect_support_breakdown()` |
| FVG pullback entry scanner | ✅ Shipped | `scanner_templates.py:2781` `scan_fvg_pullback()` |
| Displacement qualifier on BOS | ❌ Missing | Add `require_displacement=True` param to `detect_bos_choch` |
| BSL / SSL pool identification | ❌ Missing | New function: cluster pivot highs/lows within N% over M bars |
| OTE Fibonacci zone | ❌ Missing | 5-line addition: `_fib_retracement(start, end, [0.618, 0.786])` |
| Inducement sweep detection | ❌ Missing | Complex: false-break then reversal within K bars — medium-high effort |
| Composite ICT scanner | ❌ Missing | Chain: displacement-MSS → OTE overlap → FVG rejection → fire |

### Recommended build order
1. **Displacement gate** — low effort, high impact; makes existing CHoCH/BOS detections more precise
2. **OTE zone** — low effort, pure Fibonacci; immediately usable as a filter on existing FVG scanner
3. **BSL/SSL pools** — medium effort; most useful for chart overlay, less so for screening
4. **Composite ICT scanner** — medium effort once 1–3 done; the full 4-step blueprint as a single `scan_ict_setup()` function
5. **Inducement** — medium-high effort; deprioritize until 1–4 are measured and paying

---

## Contradictions with Existing Wiki

> [!contradiction] Displacement requirement
> ICT's MSS requires a displacement candle as the qualifying gate for a structure break. [[sources/Structure-Break-Chain-SBC-Pine]] uses a `break quality` score (0.6×dist/ATR + 0.4×body/ATR) as a proxy — similar intent, different formula. Our current `detect_bos_choch` has neither. All three approaches agree the *size* of the break matters; they disagree on how to measure it.

> [!contradiction] FVG entry style
> [[sources/FVG-DGT-Pine]] documents four fill modes (Any Touch / Midpoint / Wick Sweep / Body Beyond), of which "Any Touch" = enter on any pullback into the zone. ICT prescribes limit orders *inside* the FVG, which is closer to "Any Touch." [[sources/BOS-FVG-Pullback-Signals-Pine]] and our `scan_fvg_pullback()` both require a *close back above* the FVG top (rejection, not touch) — more conservative, fewer fills, but only captures gaps that held. The right answer depends on gap fill rate, which `fvg_fill_study.py` can answer.

---

## Related Concepts
- [[concepts/Market-Structure-CHOCH-BOS]] — BOS/CHoCH implementation details and SBC quality scoring
- [[concepts/Fair-Value-Gap]] — FVG construction, fill statistics, mitigation modes
- [[concepts/Fair-Value-Breaker-FBG]] — When an FVG fails and becomes a reversal zone
- [[strategies/Supply-Demand-Zone-Trading]] — Overlapping framework (S&D zones vs liquidity pools)
- [[sources/LuxAlgo-Smart-Money-Concepts-Pine]] — Prior SMC implementation reference (EQH/EQL are LuxAlgo's proxy for BSL/SSL)

## Sources
- [[sources/ICT-Quick-Reference-Guide-2026-08-13]]
