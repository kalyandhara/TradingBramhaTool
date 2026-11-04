---
title: "Participant Positioning — FII / DII / client long-short ratios"
category: concept
tags: [fii, dii, participant-positioning, long-short-ratio, open-interest, short-squeeze, sentiment, state-series, unmeasured, india, data-gap]
created: 2026-09-18
updated: 2026-09-18
sources: 1
related: [sources/Bramesh-NIFTY-Gann-1x3-Higher-High-2026-09-18, concepts/Put-Call-Ratio, concepts/Market-Sentiment-Index, concepts/Constrained-Participants, concepts/Gamma-Exposure-GEX, analyses/Open-Backlog]
---

# Participant Positioning — FII / DII / client long-short ratios

NSE publishes daily **participant-wise open interest**, splitting F&O positions across
FII/FPI, DII, proprietary and client (retail). The derived reading that Indian market
letters quote is the **long : short ratio** per participant class, alongside cash-segment
net flows.

## The readings

| Reading | What it is | Conventional interpretation |
|---|---|---|
| **FII index-futures long : short** | share of FII index-future OI on each side | extreme short (e.g. **12:88**) read as bearish positioning *and* as squeeze fuel |
| **Client long : short** | the retail side | usually the mirror; extreme retail long read as a contrary warning |
| **FII cash net** | ₹ crore bought − sold, cash segment | flow, not positioning |
| **DII cash net** | domestic institutions | often framed as "absorbing" FII selling |
| **Futures OI change** | contracts added or liquidated | falling OI on a rising market → short covering |

**The cash and the futures readings are different books and routinely disagree.** FIIs
selling cash while adding index shorts is a hedge, not a doubling-down; quoting the two
together as one bearish signal double-counts.

## The squeeze argument, and why it needs care

The standard use is: *FIIs are 88% short; any rally forces covering; covering is fuel;
therefore upside.* Two things are wrong with taking that at face value.

> [!warning] This is a STATE, not an EVENT — and it is the failure mode this desk has
> already been burned by
> An extreme long:short ratio is **slow-moving and heavily autocorrelated**. Today's 88%
> is mostly yesterday's 88%. Scoring each day as an independent observation manufactures
> significance: on this desk's own precedent
> (`gamma_regime_backtest._rotation_p`) a **known null** printed **p = 0.031** under a
> Welch t-test and **p = 0.32** under circular rotation.
>
> **Any test of this must use rotation p-values**, exactly as
> [[analyses/SVP-Structure-Signal-Pre-Registration]] and B-56 did. A t-test here is not a
> conservative choice; it is the wrong test.

**Second: the state coexists with the outcome it supposedly predicts.** An 88% short book
was present throughout the seven-week decline that preceded 2026-09-18. A reading that is
extreme during a fall and still extreme at the bottom has not told anyone when to buy. The
claim that needs measuring is not *"is the ratio extreme"* but *"does entering an extreme
precede a forward return, net of the drift over the same bars"* — and, as with
[[analyses/Flag-Pole-Pre-Registration]], the population needs a control, because extremes
cluster in falling markets by construction.

## Related readings on this desk

* [[concepts/Put-Call-Ratio]] — the same instinct (positioning as contrarian sentiment) in
  the options book, and **already computed here**.
* [[concepts/Gamma-Exposure-GEX]] — positioning with a *mechanical* transmission to price
  (dealers must hedge). Participant ratios have **no such forcing mechanism**: nothing
  compels an FII to cover a hedged short. This is the sharpest distinction on the page, and
  it is the reason GEX is a stronger construct than a long:short ratio.
* [[concepts/Constrained-Participants]] — the honest version of the squeeze argument: it
  works only where a participant is *obliged* to act. Show the obligation or the fuel is
  hypothetical.

## Status on this desk — MEASURED 2026-10-15: NULL

**Data:** `tools/participant_oi.py` reads NSE's participant-wise F&O OI file (2016 onward,
cached per session). **Test:** [[analyses/FII-Short-Squeeze-Study]] (B-95), pre-registered
blind, rotation p-values, prior-move control. FII ≥ 85% short in index futures (261 sessions,
12 episodes): NIFTY 20 sessions later was **1.42 points worse** than otherwise after the
control, rotation p = 0.38 — **NULL**, leaning against the squeeze claim. All 12 episodes are
from 2020 on; heavy FII index shorts are a recent norm, not a rare extreme.

*Earlier status (kept for the record):*  — a DATA gap, not a build gap

**Nothing here reads participant-wise F&O OI.** `FII` appears in the toolchain only inside
`block_deal_intel.py`, where it classifies *shareholder names*, not derivatives positions.
`nse_oi_momentum` pulls the F&O bhavcopy, which carries contract-level OI but **not the
participant split** — that is a separate NSE file.

So the sequence is: **probe the data first, then pre-register, then measure.** Filed as
**B-95** in [[analyses/Open-Backlog]], gated on the probe. Until that runs, participant
ratios are **read as commentary on this desk, not used as input to anything.**

## Common mistakes

1. **Quoting cash flow and futures positioning as one signal.** Different books, often
   hedges of each other.
2. **Converting contracts to rupees with a stale lot size.** The source letter's
   ₹245 crore for 2,040 contracts implies a ~50-unit lot against the NSE's current 75 —
   cite contracts, which are unambiguous.
3. **"DII absorbed the selling"** when DII inflow exceeds FII outflow. −3,208 against
   +3,617 is net institutional **buying**, not absorption.
4. **Reading falling OI as covering without a price direction.** Liquidation on a falling
   market is long unwinding, not short covering.

## Sources

* [[sources/Bramesh-NIFTY-Gann-1x3-Higher-High-2026-09-18]] — 2026-09-18, the only source
  informing this page.
