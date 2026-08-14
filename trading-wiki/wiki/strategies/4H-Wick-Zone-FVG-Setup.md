---
title: "4H Wick-Zone → Sweep → BOS → FVG Retest"
category: strategy
tags: [smc, ict, intraday, 4h, 15m, wick-zone, liquidity-sweep, bos, fvg, multi-timeframe, parked, reference-only]
timeframe: intraday
created: 2026-08-09
updated: 2026-08-09
sources: 1
status: parked — reference only, not in use
related:
  - sources/4H-Wick-Zone-FVG-Infographic.md
  - concepts/Fair-Value-Gap.md
  - concepts/Market-Structure-CHOCH-BOS.md
  - concepts/Order-Blocks.md
  - concepts/Multi-Timeframe-Analysis.md
  - concepts/Equal-Highs-Lows.md
  - strategies/False-Break-Buildup-Trading.md
  - strategies/Supply-Demand-Zone-Trading.md
---

# 4H Wick-Zone → Sweep → BOS → FVG Retest

> [!note] Parked on purpose — filed for reuse, not for use
> Ingested 2026-08-09 at the user's request with the explicit caveat *"I am not interested in intraday, however worth keeping it for reuse."* **Not in use, not implemented, and not measured.** It is here for two reasons: the **sequence transfers off intraday** (see the Weekly→Daily translation below), and it is a clean worked example of composing primitives this wiki already holds.

## Core Idea

A large higher-timeframe candle leaves a **wick zone** — the span between its body and its wick extreme. Price returning there is expected to sweep the liquidity resting beyond the body, reverse, and continue in the HTF candle's direction. The trade is not the sweep and not the reversal; it is the **retest of the fair value gap left by the reversal impulse**.

Four legs, in a required order:

```
HTF zone  →  LTF sweep  →  LTF BOS  →  LTF FVG retest
(4H wick)    (15m close    (structure    (entry)
              past body)    breaks back)
```

Each leg removes a different failure mode: the zone gives location, the sweep proves liquidity was taken, the BOS proves the reversal is structural rather than a bounce, and the FVG gives an entry with a definable stop. **The graphic's claimed power has to come from that sequencing**, because no individual leg has a measured edge in this repo.

## Setup Criteria

1. **Mark the HTF wick zone.** On the 4H, take a decisive candle; the zone is body → wick extreme, bounded by the swing high (bullish) or swing low (bearish).
2. **Wait for the sweep.** A 15m **close beyond the 4H body** (below it for a bullish setup, above for bearish). Until this prints, the zone is not live.
3. **Require a BOS.** After the sweep, a 15m break of structure back in the HTF candle's direction ([[concepts/Market-Structure-CHOCH-BOS]]).
4. **Locate the FVG** left by the BOS impulse ([[concepts/Fair-Value-Gap]]).
5. **Enter on the retest** of that gap. Mirror everything for the bearish case.

## Entry Rules

- Enter on the FVG retest **after** the BOS — never on the sweep, never on the BOS itself.
- **Deviation from the source, deliberate:** the graphic implies a resting limit order inside the gap. [[concepts/Fair-Value-Gap]] argues against exactly that — a limit inside the zone fills on the way through in precisely the cases where the gap fails, so the fill is guaranteed when it is least wanted. Use this repo's rule instead: require a **close back above** the gap (below, for shorts) with a dominant rejection wick. Fewer trades, worse average price, only gaps that held.

## Exit Rules (profit target + stop loss)

**The source specifies none of this** — no stop distance, no target, no R:R. What follows is this wiki's convention applied to the structure, and should be read as inference, not as the source's method:

- **Stop:** below the sweep low (bullish) — the sweep extreme is the structural invalidation, and it is tighter than the wick-zone low.
- **Target:** the HTF swing high that bounds the wick zone; a 2R minimum otherwise.
- **Partials:** at the BOS level on the way up, per the convention on [[strategies/False-Break-Buildup-Trading]].

## Timeframe

- **As drawn:** 4H zone → 15m execution (a 16:1 ratio).
- **This repo's own template** ([[concepts/Multi-Timeframe-Analysis]]) is Weekly regime → Daily setup → intraday trigger. The 4H setup collapses that to two rungs and drops the regime layer entirely — **no HTF trend filter appears anywhere in the graphic.** That is a real omission, not a simplification: the sequence will fire against a deteriorating higher timeframe just as readily.

> [!key-insight] The reusable version: Weekly → Daily, which this repo *can* test
> Shift every rung up two and the strategy becomes computable from bars already stored:
>
> | Leg | As drawn | Transferred | Already implemented? |
> |---|---|---|---|
> | Zone | 4H candle wick | **Weekly** candle wick | no — trivial geometry |
> | Sweep | 15m close past body | **Daily** close past the weekly body | no — trivial |
> | BOS | 15m | **Daily** | ✅ `detect_bos_choch` |
> | FVG retest | 15m | **Daily** | ✅ `scan_fvg_pullback` |
>
> Two of four legs exist; the other two are a few lines of candle geometry. **This version needs no intraday store**, which makes it testable against [[analyses/Backtest-Harness]] the way the FVG fill study was. That is the concrete reason this page is worth keeping.

## Best Market Conditions

- Trending HTF where the wick zone sits with the trend (the missing filter above, supplied manually).
- Liquid instruments — the sweep leg assumes stops are actually resting beyond the body.

## Worst Market Conditions

- Chop: a 4H candle's wick zone is wide, so sweeps and BOS prints occur constantly with no follow-through.
- Against the higher timeframe — and nothing in the strategy stops you.
- Thin instruments where the "sweep" is one print rather than genuine liquidity being taken.

## Backtest / Track Record

**None. Nothing here is measured, by the source or by us.**

- The source claims "simple & powerful" with no sample, win rate, or period.
- **Untestable as specified**: intraday, and `chart_server` fetched intraday bars while nothing persisted them. This was the **third claim blocked on that same gap** — after FA-2 (Rahu Kaal/hora) and the [[concepts/Volume-Profile]] 80% value-area rule. **An [intraday store](tools/intraday_store.py) was built 2026-08-09**, which removes the blocker in principle; this strategy's 15m trigger leg still needs depth beyond the current **58 sessions**, so it becomes testable through forward accumulation rather than more work. The **Weekly→Daily translation above needs none of that and is testable today.** See [[analyses/Intraday-Store]].
- The **FVG leg has a measured null on its own mechanism**: the 2026-08-09 fill study found ~2pp of "magnet" effect over a width-and-distance-matched placebo, collapsing to nothing at longer horizons. That does *not* refute this use of the gap — here it is an entry location after a confirmed BOS, not a prediction of return — but it does mean the FVG contributes no independent edge.
- The Weekly→Daily translation above **is** testable and has not been tested either.

## Examples

None recorded — nothing has been traded or scanned from this. Annotate here if the Weekly→Daily variant is ever built and fires on a tracked name.

## Related Concepts

- [[strategies/False-Break-Buildup-Trading]] — **the closest sibling already on file**: same HTF-zone-plus-LTF-trigger shape, but the zone is a consolidation rather than one candle's wick, and the trigger **fades** the false break instead of **joining** the reversal after a BOS. Two spellings of one idea; neither measured.
- [[concepts/Order-Blocks]] — the zone this is most often confused with. An OB *requires* a structure-breaking displacement; a wick zone requires only a big candle. See the contradiction on the source page.
- [[strategies/Supply-Demand-Zone-Trading]] — supplies the HTF-mark → TTF-entry discipline this strategy is an instance of, plus the zone-strength factors (freshness, exit-move speed) the graphic omits.
- [[concepts/Fair-Value-Gap]] — the entry leg, and the reason our entry rule is stricter than the source's.
- [[concepts/Market-Structure-CHOCH-BOS]] — the confirmation leg; note a BOS here is *counter* to the immediately preceding sweep, so it is the CHoCH-flavoured reading.
- [[concepts/Equal-Highs-Lows]] — what a "liquidity sweep" is sweeping: resting liquidity at prior equal highs/lows.
- [[concepts/Multi-Timeframe-Analysis]] — the three-rung template this strategy collapses to two, dropping the regime filter.

## Sources
1. [4H-Wick-Zone-FVG-Infographic](../sources/4H-Wick-Zone-FVG-Infographic.md) — unattributed retail educational graphic, supplied 2026-08-09. Six steps, no numbers, no provenance. Credited for the **sequencing and the "wick zone" label**, not as authority on any leg.
