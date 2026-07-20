---
title: "Market Structure: CHOCH vs BOS"
category: concept
tags: [smart-money, smc, choch, bos, mss, market-structure, fvg, liquidity, swing-highs-lows, order-blocks, internal-structure, strong-weak-high-low, luxalgo]
created: 2026-06-22
updated: 2026-07-16
sources: 2
related: [strategies/Supply-Demand-Zone-Trading, concepts/Support-Resistance, concepts/Order-Flow, concepts/Elliott-Wave, concepts/Order-Blocks, concepts/Premium-Discount-Zones, concepts/Equal-Highs-Lows]
---

# Market Structure: CHOCH vs BOS

## Definition
Two complementary Smart Money Concepts (SMC) labels for what a new swing high/low means relative to the *existing* trend — the same raw event (price breaks a prior swing point) is labeled differently depending on whether it agrees with or contradicts the prevailing structure:

- **BOS (Break of Structure)** — price breaks a prior swing point **in the direction of the existing trend**. Confirms trend continuation. In an uptrend: a new Higher High (HH) breaking above the last HH. In a downtrend: a new Lower Low (LL) breaking below the last LL.
- **CHOCH (Change of Character)** — price breaks a prior swing point **against** the existing trend, the first structural sign the trend may be reversing. In an uptrend: price breaks below the most recent Higher Low (HL) — that's a CHOCH signaling a possible shift to bearish. In a downtrend: price breaks above the most recent Lower High (LH) — CHOCH signaling a possible shift to bullish.

Put simply: **BOS = "the trend continues," CHOCH = "the trend might be ending."** Both are defined purely by which prior swing point gets broken and in which direction — same mechanical rule, opposite interpretive context.

## How to Use

### Swing-point labeling vocabulary (prerequisite)
- **HH** = Higher High, **HL** = Higher Low (uptrend structure)
- **LH** = Lower High, **LL** = Lower Low (downtrend structure)
- A trend is intact as long as it keeps printing the matching HH/HL (up) or LH/LL (down) sequence.

### Reading the sequence (from the reference infographic)
1. Uptrend established via repeated HH+BOS / HL pairs (each new HH confirmed by a BOS breaking the prior HH).
2. Trend continues until price fails to make a new HH and instead breaks below the last HL → that break is the **CHOCH** — first warning the uptrend's character has changed.
3. After a CHOCH, price often forms a new lower structure (LH/LL) — if a subsequent break continues in that *new* (now bearish) direction, that next break is reclassified as a **BOS** for the new downtrend, not another CHOCH (CHOCH is the *first* counter-trend break; once the new trend is established, continuation breaks within it are BOS again).
4. **MSS (Market Structure Shift)** appears alongside CHOCH in the reference image as a closely related/overlapping label — used by some traders interchangeably with CHOCH, by others as a confirmation step after CHOCH (a deeper or higher-timeframe-confirmed break). Treat MSS and CHOCH as the same underlying idea (trend-character change) unless a specific source defines them more strictly as sequential steps.

### Supporting structures shown in the same framework
- **HTF POI (Higher-Timeframe Point of Interest)** — a supply or demand zone identified on a higher timeframe than the one being traded; in the reference image, marks the outer boundaries (top supply zone, bottom demand zone) that the whole structure sequence plays out between. Directly maps to this wiki's [[strategies/Supply-Demand-Zone-Trading]] base/zone concept, just labeled from a top-down multi-timeframe perspective.
- **FVG (Fair Value Gap)** — a price imbalance left behind by a strong directional candle (a gap between the wick of one candle and the wick two candles later, on the chart timeframe being analyzed) that price often later returns to "fill." Appears at trend pauses in the reference image, often near a CHOCH. Now has its own page — [[concepts/Fair-Value-Gap]] (quality filters, zone lifecycle, pullback-rejection entry, Python port).
- **LIQ (Liquidity)** — pools of resting stop-loss/pending orders just beyond an obvious swing high/low; price often runs through these ("liquidity grab" or "stop hunt") just before reversing, which is part of why a CHOCH is frequently preceded by a sharp wick beyond the prior swing point rather than a clean break.

### Internal vs Swing structure — SMC is nested on one chart (from the LuxAlgo reference)
The canonical [[sources/LuxAlgo-Smart-Money-Concepts-Pine|LuxAlgo SMC]] indicator runs the *same* swing-detection algorithm at **two lookbacks at once**, which is the missing piece for reading SMC in practice:
- **Swing structure** — long pivot lookback (default 50 bars). The *major* highs/lows and their BOS/CHoCH. Drawn as solid lines.
- **Internal structure** — short pivot lookback (5 bars). The *minor* swings that form *inside* each swing leg. Drawn as dashed lines / tiny labels.

So a single chart shows nested structure: internal CHoCH/BOS ticking inside a still-intact swing trend. An internal CHoCH against the swing trend is an early, low-timeframe warning; a *swing* CHoCH is the major reversal. This is the same weekly/daily/intraday nesting from [[concepts/Multi-Timeframe-Analysis]], expressed as two pivot lengths on one series. The break test itself is identical at both tiers: **`close` crossing the pivot level** (not wick), with a per-tier `trend.bias` deciding BOS (continuation) vs CHoCH (first counter-trend break).

### Strong / Weak High & Low — which extreme is protected
The LuxAlgo reference also tags the most recent swing extremes as **Strong** vs **Weak** by whether the swing trend agrees with them:
- In a **bullish** swing trend: the swing low is a **Strong Low** (defended — breaking it would be a real CHoCH) and the swing high is a **Weak High** (expected to break as continuation).
- In a **bearish** swing trend: the swing high is a **Strong High**, the swing low a **Weak Low**.

Reading: price is *drawn toward* weak extremes (they hold liquidity / are likely to break) and *defends* strong ones. A break of a **strong** high/low is the meaningful structural event; a break of a **weak** one is expected continuation. This pairs directly with [[concepts/Premium-Discount-Zones]] (buy near the strong low in discount) and with [[concepts/Equal-Highs-Lows]] (weak highs above are often the liquidity target).

### Order blocks are derived from the break
A BOS/CHoCH doesn't just label the trend — in SMC it *creates a zone*. The last opposing candle before the impulse that caused the break becomes an **order block** ([[concepts/Order-Blocks]]) — the pullback entry zone for trading the new direction. Structure break → order block → return-to-zone entry is the core SMC loop.

## Variants / Parameters
- **Timeframe dependency**: CHOCH/BOS are timeframe-relative — a CHOCH on the 15-minute chart can be a minor pullback within a still-intact BOS sequence on the daily chart. Always state which timeframe a CHOCH/BOS call applies to.
- **CHOCH vs. simple pullback**: not every break of an HL/LH is a real trend change — this is the SMC equivalent of the false-break risk already documented in [[strategies/False-Break-Buildup-Trading]]; treat a single CHOCH as a *warning*, not a confirmed reversal, until price also fails to reclaim the broken level (echoing the "failed retest" pattern from [[concepts/Distribution-Days]]) or a subsequent BOS confirms the new direction.

## Common Mistakes
- Treating every CHOCH as an immediate reversal trade trigger — it's a character change *warning*, not an entry signal by itself; the reference framework pairs it with FVG/demand-zone confirmation before entries.
- Confusing CHOCH (first counter-trend break) with ordinary continuation BOS breaks that happen later in the new trend — only the *first* counter-trend break after a clean trend is the CHOCH; subsequent same-direction breaks are BOS for the new trend.
- Ignoring timeframe — calling a CHOCH on a low timeframe without checking whether it's just noise inside a higher-timeframe BOS sequence.

## Related Concepts
- [[strategies/Supply-Demand-Zone-Trading]] — HTF POI / supply-demand zones are the same institutional-footprint idea as this page's zones, viewed from the zone side rather than the swing-structure side; flip zones (broken supply → demand) are the S&D-framework equivalent of a CHOCH confirmed by a later BOS.
- [[concepts/Support-Resistance]] — HH/HL/LH/LL swing points are exactly the swing-high/swing-low S&R marking method already documented there; CHOCH/BOS gives those same swing points trend-context labels.
- [[concepts/Order-Flow]] — liquidity grabs/stop hunts (LIQ in the reference image) are the same iceberg/stop-cluster mechanic already documented for VWAP algo behavior.
- [[concepts/Trend-Lines]] — the diagonal counterpart (added 2026-07-03): a body close above the falling supply line joining lower pivot highs breaks the descent *rate* rather than a horizontal swing point, so it usually fires earlier than the CHOCH that breaks the last LH; the Early Reversal validation layer runs both as separate checks.
- [[concepts/Order-Blocks]] — the zone *created by* a BOS/CHoCH break; structure → order block → return-to-zone entry is the core SMC loop.
- [[concepts/Premium-Discount-Zones]] — the swing high/low that defines premium/discount comes from this page's trailing swing extremes; grade break-derived entries by range location.
- [[concepts/Equal-Highs-Lows]] — a liquidity sweep of equal highs/lows is the classic precursor to a CHoCH; weak highs/lows are often the equal-level liquidity target.
- [[concepts/Multi-Timeframe-Analysis]] — internal (5-bar) vs swing (50-bar) structure is the same regime/setup/trigger nesting expressed as two pivot lengths on one chart.
- [[concepts/Elliott-Wave]] — a CHOCH breaking the prior HL often coincides with the start of an Elliott corrective wave (Wave 2/4 or an ABC); a confirming BOS in the new direction often aligns with a new Wave 1/3 impulse. Not a strict mapping, but the two frameworks describe overlapping market behavior from different angles.

## Examples in This Wiki
- **Python port (2026-07-03)**: `detect_bos_choch()` in `tools/scanner_templates.py` implements this page's swing-labeling rule mechanically — confirmed pivot highs/lows (5 bars each side), close above the last swing high = CHOCH when structure is bearish / BOS when already bullish, and a later close below a swing low re-flips structure and invalidates the bullish event (this page's "treat a single CHOCH as a warning" caveat, enforced in code). Used as the Structure check in the Early Reversal Detector's six-check validation layer.
- None yet with live price levels — apply to a specific entity page's chart the next time a live CHOCH/BOS sequence is being tracked on a real ticker.

## Sources
1. Social media trading infographic ("CHOCH vs BOS" comparison card, source/author unattributed in the image) — ingested 2026-06-22, terminology and the annotated chart sequence (HH/HL/LH/LL, BOS, CHOCH, MSS, FVG, LIQ, HTF POI) are this page's primary source.
2. [LuxAlgo-Smart-Money-Concepts-Pine](../sources/LuxAlgo-Smart-Money-Concepts-Pine.md) — Pine v5 indicator by [[LuxAlgo]] (CC BY-NC-SA 4.0), ingested 2026-07-16; source for the internal-vs-swing two-tier model, Strong/Weak High-Low tagging, the close-cross + per-tier-bias break rule, and the structure→order-block linkage.
