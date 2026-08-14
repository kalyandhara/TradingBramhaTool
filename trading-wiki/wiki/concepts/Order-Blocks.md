---
title: "Order Blocks (OB)"
category: concept
tags: [order-block, smc, smart-money, ict, supply-demand, mitigation, luxalgo, institutional-footprint, displacement, bos, choch, multi-timeframe]
created: 2026-07-16
updated: 2026-08-08
sources: 2
related: [concepts/Market-Structure-CHOCH-BOS, concepts/Fair-Value-Gap, strategies/Supply-Demand-Zone-Trading, concepts/Support-Resistance, concepts/Premium-Discount-Zones, concepts/Multi-Timeframe-Analysis, concepts/Fair-Value-Breaker-FBG, strategies/RSI-60-40-Setup, analyses/Backtest-Harness, analyses/Dashboard-UI-Roadmap]
---

# Order Blocks (OB)

> [!note] Merged page (2026-08-08)
> This page absorbs the former `concepts/Order-Block.md` (a greenfield page written
> 2026-07-25 to document the shipped scanner). The two pages had drifted into
> **contradicting each other on the selection rule** — see the contradiction
> callout below, which is the substantive finding of the merge, not a formatting note.

## Definition
An **order block** is the last opposing candle *before* an impulsive move that breaks structure — the candle where institutions are presumed to have loaded a position before driving price away. A **bullish OB** is the last down-candle before a strong up-move that breaks a swing high (a demand footprint); a **bearish OB** is the last up-candle before a strong down-move that breaks a swing low (a supply footprint). Price returning to that candle's range is expected to react (bounce/reject) because unfilled institutional orders are assumed to rest there — the zone is **latent demand** (or supply) until something consumes it.

It is the SMC sibling of a supply/demand *base* ([[strategies/Supply-Demand-Zone-Trading]]) and of the origin candle of a [[concepts/Fair-Value-Gap]]. The zone stays valid ("unmitigated") until price trades or closes back through it.

## How to Use

### Mechanical detection (from the [[sources/LuxAlgo-Smart-Money-Concepts-Pine|LuxAlgo SMC]] reference)
An OB is not drawn freehand — it is *derived from a structure break*:
1. A BOS or CHoCH fires ([[concepts/Market-Structure-CHOCH-BOS]]) — say a bullish break of a swing high.
2. Scan every bar between the broken pivot and the break bar.
3. **Bullish OB** = the bar with the **lowest low** in that window (the deepest pullback candle before the impulse). **Bearish OB** = the bar with the **highest high**. That bar's high–low range becomes the order-block zone.
4. **Volatility parsing** (key refinement): before selecting, each bar's high/low is "parsed" — if a bar's range ≥ 2 × ATR(200) it's flagged high-volatility and its high/low are *swapped* for selection purposes, so a single violent spike bar doesn't get mis-picked as the OB.

### Zone refinement on a lower timeframe (2026-08-08)
A single candle's high–low is a **proxy for a base, not the base itself**. The retail framing (user-supplied "ORDER BLOCK" infographic, 2026-08-08) makes this the defining property and states it twice: *the order block is a small consolidation area on the lower timeframe*, and OBs "form from a sharp rally up or decline away from a **base**" — i.e. they look identical to ordinary supply/demand zones because they **are** one, marked with SMC vocabulary.

The operational consequence:
1. Detect the OB on the working timeframe (the infographic's example is H1) using the structure-break rule above.
2. **Drop one or two timeframes** (H1 → M15/M5) and look *inside* that candle's range for the actual consolidation — the cluster of small-bodied bars the impulse left from.
3. Use the **base's** extremes as the zone, not the parent candle's full range. Stop goes just beyond the base.

This is a **narrower zone**, so the stop is tighter and R:R at the same target improves. The cost is symmetric and must not be glossed: a refined zone is **missed more often**, because price can turn from the unrefined parent range without ever reaching the base. Whether the tighter stop pays for the missed fills is an empirical question, not a stylistic one — and one [[analyses/Backtest-Harness]] can answer.

The wiki already holds both halves of this machinery, which is why the omission is worth flagging rather than merely noting:
- [[strategies/Supply-Demand-Zone-Trading]] is built on exactly this HTF-mark → TTF-entry split, and its rule "zone must include the entire consolidation area" is the same instruction from the S&D side.
- [[concepts/Fair-Value-Gap]] already documents **three-source detection** (current TF + HTF + **LTF/intrabar**) from the DGT source — gaps hidden *inside* the current bar. Order blocks never got the equivalent.
- [[concepts/Multi-Timeframe-Analysis]] — the general form of the drill-down.

### Two tiers, mirroring structure
LuxAlgo derives OBs at both structure tiers: **internal order blocks** (from 5-bar internal structure breaks — minor, more frequent) and **swing order blocks** (from 50-bar swing breaks — major). Only the newest N are kept (default 5 each). Note this is a *nested-structure* tiering on one chart, which is related to but not the same as the LTF zone refinement above.

### Mitigation (when an OB is "used up")
- **Bearish OB** is mitigated when price trades/closes back **above** its high; **bullish OB** when price trades/closes back **below** its low.
- The mitigation source is a choice: **Close** (body close through the block — stricter, fewer invalidations) vs **High/Low** (any wick through — looser). Same close-vs-wick design tension as the [[concepts/Fair-Value-Gap]] lifecycle.
- Once mitigated, the block is removed — it has done its job (or failed).
- **Freshness** — the first retest of an unmitigated block is the highest-quality; each subsequent tap weakens it. Same rank-1 zone-strength factor as [[strategies/Supply-Demand-Zone-Trading]].

### Trading the zone
An unmitigated OB in the trade direction is a **pullback entry zone**: wait for price to return into the block, look for a rejection/confirmation candle, enter with a stop just beyond the block.

- **The retest is the trade, not the displacement.** The impulse bar that creates the OB is the *setup*; the entry is price coming back.
- **Stop** just beyond the zone (below the zone low for a bullish OB), which is what makes the structure attractive — a tight stop against a target set by the prior impulse.
- **Target** the displacement extension, or a 2R minimum.
- Strongest when it aligns with a [[concepts/Premium-Discount-Zones]] read (buy bullish OBs in discount, sell bearish OBs in premium) and the higher-timeframe structure.

## Variants / Parameters
- **Selection rule**: volatility-parsed extreme (LuxAlgo) vs last opposing-close candle — **these are different candles; see the contradiction below.**
- **Zone granularity**: parent candle's full range vs LTF-refined base (see above).
- **Body vs wick zone** — body-only is stricter (fewer, cleaner retests); full range catches more.
- **BOS vs CHoCH** — a block formed on a BOS is a *continuation* demand zone (with-trend, generally higher-probability); a CHoCH block is a *reversal* zone (counter-trend, treat with more care).
- **Filter method**: ATR(200) (default) vs cumulative-mean-range for the volatility parse. LuxAlgo recommends cumulative-mean-range when little data is available.
- **Mitigation basis**: Close vs High/Low (see above).
- **Count**: how many recent OBs to display (default 5 internal, 5 swing).
- Related unstructured OB definitions in the wild also require an FVG immediately after the OB candle ("OB + imbalance"); the LuxAlgo reference does **not** require an FVG — it takes the extreme candle before the break unconditionally.

> [!contradiction] The two selection rules pick different candles — and the shipped scanner uses the weaker one
> The former `Order-Block.md` defined the bullish OB as **the last down-close candle before the break bar**. This page's LuxAlgo-sourced rule takes **the bar with the lowest low between the broken pivot and the break bar, after volatility parsing**. In a multi-bar pullback these are frequently *different candles*, and only the second one is protected against grabbing a violent spike bar.
>
> [`scan_order_block`](tools/scanner_templates.py:3299) implements the **last-down-close** rule ([line 3333](tools/scanner_templates.py:3333)) with **no volatility parse** — which is precisely the failure this page's own Common Mistakes list warns about ("a naive min-low/max-high selection will grab violent bars"). The greenfield page was written to describe the code, so it documented the shortcut as the definition and the contradiction stayed invisible while two pages existed.
>
> **Resolution:** the volatility-parsed extreme is the reference rule; the last-down-close is an unvalidated simplification that happens to be what ships today. Reconciling the code to the reference rule is a named candidate fix against the measured result below.

## Common Mistakes
- **Drawing OBs without a structure break.** A down candle is only a bullish OB if the move *after* it broke structure. No break → not an OB, just a candle. A down candle before a weak drift up is not an order block; the displacement must actually break structure.
- **Trading the displacement, not the retest** — chasing the impulse bar instead of waiting for price to return to the zone.
- Treating every touch as a bounce — an OB is a *zone of interest*, not a guaranteed reversal; it needs confirmation on return, same warning as CHoCH being a warning not a trigger ([[concepts/Market-Structure-CHOCH-BOS]]).
- **Ignoring mitigation** — a block price has already closed through is spent; re-using it is trading a level the market already cleared.
- **Picking the spike bar as the OB** — the volatility-parse step exists precisely to avoid this; a naive min-low/max-high selection will grab violent bars.
- **Trading counter-trend OBs against the HTF regime** — OB entries are timing tools; direction must already be justified by structure and the weekly tape.
- **Volume blind** — a displacement on below-average volume is a weaker block (our detector flags this explicitly).
- **Treating the parent candle's full range as the zone** — it is an unrefined proxy for a base; the wide zone means a wide stop, which quietly halves R:R on every trade.

## Related Concepts
- [[concepts/Market-Structure-CHOCH-BOS]] — OBs are *derived from* BOS/CHoCH breaks; no structure event, no order block. The two-tier (internal/swing) split applies identically.
- [[strategies/Supply-Demand-Zone-Trading]] — an order block is essentially the origin/base candle of a supply or demand zone; RBR/DBD zone-strength factors (freshness, exit-move strength, distance) map directly onto OB quality, and its HTF→TTF entry split is the LTF refinement above.
- [[concepts/Fair-Value-Gap]] — OBs and FVGs are the two dominant SMC "return-to" zones; the impulse that validates an OB usually leaves an FVG, and "OB + FVG confluence" is a common higher-quality entry filter.
- [[concepts/Premium-Discount-Zones]] — grade an OB by where it sits: a bullish OB in discount is higher-probability than one in premium.
- [[concepts/Fair-Value-Breaker-FBG]] — a failed FVG flipped into a breaker; a cousin structure on the reversal side.
- [[concepts/Support-Resistance]] — an OB is a mechanically-defined zone-not-line; the same zone psychology applies.
- [[concepts/Multi-Timeframe-Analysis]] — the drill-down the LTF refinement depends on.
- [[strategies/RSI-60-40-Setup]] — another with-trend continuation entry; an order block that lands at EMA support is confluent with the RSI-40 pullback.

## Examples in This Wiki

### Shipped detector — and it does not currently beat a coin flip
**`scan_order_block`** ([scanner_templates.py:3299](tools/scanner_templates.py:3299)), registered **"Order Block Retest"** (category Entry) — shipped 2026-07-25, closing [[analyses/Dashboard-UI-Roadmap]] Phase 2. It reuses `detect_bos_choch` for the structure break, takes the last down-close candle before the break bar as the zone, requires a ≥1-ATR displacement out of it, checks freshness/mitigation, and fires on the retest while price holds above the zone low. Being the first scanner to emit a structured entry/stop/target, it was also the first to exercise the [[analyses/Backtest-Harness]] R-simulation.

> [!key-insight] Measured, not asserted: 734 signals, **−0.74% forward edge @20d**
> [[analyses/Backtest-Harness]] measures Order Block Retest **at or below a random-entry baseline** on raw forward return (−0.74% @20d), with a mildly positive **+0.11R** from its 2R targets. It is therefore classified in `MEASURED_WEAK_SCANNERS` ([opportunity_hub.py:248](tools/opportunity_hub.py:248)) and carries confluence weight **0.25** vs 1.0 for the two scanners that did beat the baseline. Caveat as ever: gross, survivorship-biased, one universe, one ~6y window — directional, not a verdict.

The concept is well-sourced; **the implementation is the thin part**, and the gap between them is the most likely explanation for that number. Documented on this page but absent from the code:

| Documented here | In `scan_order_block`? |
|---|---|
| Volatility-parsed extreme selection | ✗ — last down-close, no parse |
| LTF-refined zone (base, not parent candle) | ✗ — full parent candle range |
| Internal (5-bar) vs swing (50-bar) tiers | ✗ — single tier |
| Close vs High/Low mitigation as a choice | ✗ — hardcoded close-below |
| Premium/discount grading | ✗ — score is displacement · volume · freshness · zone position |
| HTF-regime gate on CHoCH (reversal) blocks | ✗ — CHoCH blocks accepted ungated |
| Bearish OBs | ✗ — long-only |
| OB + FVG confluence | ✗ — though [`detect_fvg_pullback`](tools/scanner_templates.py:2570) already exists to supply it |

Cheapest candidates to move the measured number: the **volatility parse** (correctness fix, per the contradiction above), and a **premium/discount or HTF-regime gate** (the page's own rank-1 quality filter). Unlike most tuning, there is a harness to check them against — so these are hypotheses to measure, not improvements to assume.

### Live examples
- No live-ticker example yet — annotate an entity page when an OB rejection fires on a tracked stock. (Nearest thing on record: LTFOODS made a 2026-07-31 Scanner Hub run on a **single** Order Block hit and was ranked #9 accordingly — see [[log]] 2026-07-31.)

## Sources
1. [LuxAlgo-Smart-Money-Concepts-Pine](../sources/LuxAlgo-Smart-Money-Concepts-Pine.md) — Pine v5 indicator by [[entities/LuxAlgo]] (CC BY-NC-SA 4.0), ingested 2026-07-16; the derive-from-structure-break selection rule, volatility parsing, two-tier internal/swing split, and Close-vs-High/Low mitigation are all from this script.
2. User-supplied **"ORDER BLOCK" infographic** (in-conversation image, 2026-08-08) — source for the LTF zone-refinement section: OB as "a small consolidation area on lower timeframe", forming from a sharp rally/decline away from a base, and explicitly identical in appearance to ordinary supply/demand zones. **Provenance: unattributed retail educational graphic** — no author, no data, no track record. Treated as a framing contribution (it names a real gap the mechanical sources left) rather than as evidence that refinement improves results; that claim is unmeasured.
