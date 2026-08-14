---
title: "Infographic — The 4H Setup (wick zone → sweep → BOS → FVG retest)"
category: source
tags: [infographic, intraday, smc, ict, 4h, 15m, wick-zone, liquidity-sweep, bos, fvg, multi-timeframe, parked]
created: 2026-08-09
updated: 2026-08-09
sources: 1
related:
  - strategies/4H-Wick-Zone-FVG-Setup.md
  - concepts/Fair-Value-Gap.md
  - concepts/Market-Structure-CHOCH-BOS.md
  - concepts/Multi-Timeframe-Analysis.md
  - strategies/False-Break-Buildup-Trading.md
---

# Infographic — The 4H Setup (wick zone → sweep → BOS → FVG retest)

## Metadata
- **Author:** unattributed retail educational graphic ("THE 4H SETUP — A Simple & Powerful Intraday Strategy")
- **Date:** supplied 2026-08-09
- **Format:** single image, 6 numbered steps with schematic candle diagrams
- **Ingest trigger:** user supplied it with an explicit instruction — *"I am not interested in intraday, however worth keeping it for reuse."* Filed accordingly: documented in full, **parked** as a strategy, and mined for the part that transfers off intraday.

## Key Takeaways

1. **The zone is one HTF candle's wick region.** Take a 4H candle; the area between its **body** and its **wick extreme** is the "candle wick zone", bounded by the swing high/low. This is a *new label* in this wiki for a zone defined by a single candle's geometry — see the definitional note below, because it is neither an order block nor an S&D base.
2. **Confirmation of the zone is a liquidity sweep on the LTF.** Wait for a **15-minute close below the 4H body** (bullish case). Only then is the wick area treated as live. The graphic labels this "LIQUIDITY SWEEP".
3. **Then structure must break.** After the sweep, look for a **BOS** on the 15m inside/above the wick zone. The sweep alone is not the trade.
4. **Entry is the FVG retest, not the BOS.** The impulse that produced the BOS leaves a fair value gap; the entry is price returning into that gap. Stop implied below the wick zone / sweep low.
5. **Mirrored for bearish** — a red 4H candle, 15m close above the body, BOS down, short the FVG retest.
6. **Timeframe pair is fixed at 4H → 15m** (a 16:1 ratio), with the 4H supplying the zone and the 15m supplying every trigger.

## Detailed Notes

The full sequence as drawn, bullish case:

| Step | Action | Timeframe |
|---|---|---|
| 1 | Mark the 4H candle's wick zone (body → wick extreme), bounded by swing high/low | 4H |
| 2 | Wait for a 15m **close below the 4H body** — the liquidity sweep that confirms the wick area | 15m |
| 3 | Price trades down into the wick zone (the red 15m sequence), then prints a **BOS** upward | 15m |
| 4 | The BOS impulse leaves an **FVG**; enter on the **retest** of that gap | 15m |
| 5 | Hold for continuation — "price moves higher with strong bullish momentum" | 15m |
| 6 | Bearish is the exact mirror | both |

No stop distances, targets, R:R, session filters, or instrument scope are specified. No win rate, sample, or backtest is claimed anywhere on the graphic — it asserts "simple & powerful" and leaves it there.

## Actionable Insights

- **The transferable part is the sequence, not the timeframes.** *HTF zone → LTF sweep → LTF BOS → LTF FVG retest* is timeframe-agnostic. Run it **Weekly → Daily** and every leg is computable from bars this repo already stores — see [[strategies/4H-Wick-Zone-FVG-Setup]] for that translation, which is the version worth testing.
- **Every primitive is already implemented here.** `detect_bos_choch` (structure break), `detect_fvg_pullback` / `scan_fvg_pullback` (gap + rejection entry), and the HTF-zone-then-LTF-entry discipline on [[strategies/Supply-Demand-Zone-Trading]] and [[concepts/Order-Blocks]]. The graphic contributes **ordering and a name**, not a new detector.
- **Our FVG entry is already stricter than step 4 implies.** The graphic says "enter at the FVG retest"; `detect_fvg_pullback` additionally requires price to **close back above** the gap with a dominant lower wick. That difference matters — see the contradiction below.

## Contradictions with Existing Wiki

> [!contradiction] "The wick zone" is a fourth zone definition, and it is not any of our existing three
> This wiki already carries three mechanically distinct HTF zones: an **[[concepts/Order-Blocks|order block]]** (last opposing candle before a structure-breaking displacement — *requires the break*), an **S&D base** ([[strategies/Supply-Demand-Zone-Trading]] — *requires consolidation*, RBR/DBD), and an **[[concepts/Fair-Value-Gap|FVG]]** (*requires a 3-candle non-overlap*).
>
> The "wick zone" requires **none of those**: it is just one large candle's body-to-wick span. Any big 4H candle qualifies, with no structure event, no consolidation and no imbalance. That makes it the **loosest** of the four — which is not automatically wrong, but it means the zone contributes little selectivity and the *sweep + BOS + FVG* legs are doing the actual filtering. Do not treat "wick zone" as a synonym for order block; the graphic's own diagram shows a zone that a BOS-based OB detector would not mark.

> [!contradiction] Step 4's entry is the one our own measurement warns about
> The graphic says enter "at the FVG retest", drawn as price arriving in the zone. Read as a resting limit order that is the entry [[concepts/Fair-Value-Gap]] specifically argues against: it fills on the way through in exactly the cases where the gap fails. Our port requires the **close back above** the zone instead.
>
> Related but distinct: the **2026-08-09 fill study** found FVG "magnet" behaviour worth only ~2pp over a width-and-distance-matched placebo, collapsing to nothing at longer horizons. That does **not** refute this strategy's use of the FVG — here the gap is an *entry location after a confirmed BOS*, not a prediction that price will return. But it does mean **the FVG leg carries no measured edge of its own**, so the strategy's claimed power must come from the sweep + BOS sequencing, which is untested.

- **Close sibling already on file:** [[strategies/False-Break-Buildup-Trading]] is the same HTF-zone-plus-LTF-trigger shape (HTF buildup + LTF false break). The differences are what defines the zone (consolidation vs one candle's wick) and what the trigger does (**fade** the false break vs **join** the reversal after BOS). Neither is measured; worth noting they are two spellings of one idea.
- **No conflict on BOS or FVG mechanics** — the graphic's usage matches [[concepts/Market-Structure-CHOCH-BOS]] and [[concepts/Fair-Value-Gap]] as documented.

> [!warning] Third claim in a row that this repo cannot test, all blocked on the same thing
> The strategy as specified is **intraday and therefore unmeasurable here**: `chart_server` fetches intraday bars and **nothing persists them**. That now blocks, in order: **FA-2** (Rahu Kaal / hora windows), the **[[concepts/Volume-Profile]] 80% value-area rule**, and this. One intraday store unblocks all three, and that is the highest-leverage piece of unbuilt infrastructure in the repo.

## Pages Updated
- [[strategies/4H-Wick-Zone-FVG-Setup]] — **created** (the strategy itself, parked as intraday, plus the Weekly→Daily translation)
- [[concepts/Fair-Value-Gap]] — cross-referenced as a composition that uses the gap as a post-BOS entry location
- [[concepts/Market-Structure-CHOCH-BOS]] — cross-referenced as the sequence's confirmation leg
- `wiki/index.md`, `wiki/log.md`
- **`wiki/overview.md` deliberately untouched** — the user does not trade intraday, so this shifts no thesis.
