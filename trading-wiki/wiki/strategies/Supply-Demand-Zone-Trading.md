---
title: "Supply and Demand Zone Trading"
category: strategy
tags: [supply-demand, S&D, zones, smart-money, price-action, RBR, RBD, DBD, DBR, flip-zone, intraday, swing]
created: 2026-06-18
updated: 2026-08-09
sources: 2
related:
  - concepts/Support-Resistance.md
  - concepts/Order-Flow.md
  - strategies/Opening-Range-Breakout.md
  - strategies/Prop-Scalp-NQ-Initial-Balance.md
  - analyses/Kalyan-Trading-Philosophy.md
  - sources/SR-SMC-Supply-Demand-Dhruv-Emily-2022.md
---

# Supply and Demand Zone Trading

## Core Idea

Supply and Demand (S&D) zones are price areas where **Smart Money (institutions) placed large orders** that could not be fully filled before price moved away. When price returns to that zone, the remaining unfilled orders are still there — Smart Money re-enters aggressively, causing a strong reaction.

The S&D framework formalizes support (demand zone) and resistance (supply zone) with a specific mechanism: **the base** (sideways consolidation) identifies the origin of the large unfilled order; the **exit move** (large candle away from the base) confirms the order was large enough to move the market.

## The Four S&D Formations

### Trend Continuation
| Pattern | Structure | Trade |
|---------|-----------|-------|
| **Rally Base Rally (RBR)** | Price rallies → consolidates (base) → rallies again | Long from base on retest; demand zone |
| **Down Base Down (DBD)** | Price drops → consolidates (base) → drops again | Short from base on retest; supply zone |

### Trend Reversal
| Pattern | Structure | Trade |
|---------|-----------|-------|
| **Rally Base Drop (RBD)** | Price rallies → consolidates (base) → drops | Short from base on retest; supply zone at top |
| **Down Base Rally (DBR)** | Price drops → consolidates (base) → rallies | Long from base on retest; demand zone at bottom |

### Flip Zone
When a supply zone (resistance) is broken, it becomes a demand zone (support) for the next pullback — and vice versa. Flip zones are the highest-probability setups because the role inversion is confirmed by the break itself.

## Setup Criteria

1. **Identify the formation** on HTF (weekly/daily): scan for series of large consecutive candles; find the base (sideways area) before those candles; classify as RBR/DBD/RBD/DBR
2. **Draw the zone**: base candle(s) from body to wick; zone must include the entire consolidation area
3. **Assess zone strength** (all four factors; see below)
4. **Wait for price to return** to the zone (first retest preferred)
5. **Validate with TTF entry signal**: pin bar, engulfing, or two-bar reversal inside the zone

## Zone Strength Factors (Rank Order)

1. **Freshness** — first retest only; skip 3rd+ retests
2. **Exit move speed / size** — larger, faster candle away = bigger unfilled order = stronger zone
3. **Time at base** — less time in base = more aggressive Smart Money = stronger zone
4. **Distance of excursion** — further price traveled before returning → higher R:R + higher probability

## Entry Rules

**HTF context → TTF entry**:
1. Mark S&D zone on Daily/Weekly
2. Drop to Trading TF (1H, 15m, 5m)
3. Wait for price to reach the zone
4. Look for one of:
   - **Momentum loss**: candle range and bodies shrinking as price enters zone
   - **Wick formation**: lower wick on demand zone (buyers rejecting lower prices), upper wick on supply zone
   - **Pin bar** or **engulfing** candle at zone boundary
5. Enter at close of signal candle (or limit order at zone boundary)

**Day trading shortcut**: prior day's high = supply zone; prior day's low = demand zone for the next session.

**Index/sector alignment** (odds enhancer): if going long from a demand zone, confirm the broader index and sector are in positive territory.

## Exit Rules

- **Stop loss**: just below the demand zone (for longs); just above the supply zone (for shorts)
  - Do NOT place at the exact zone boundary — use a buffer of 1–2 ATR below (avoids stop hunts)
  - Never use round numbers for stop placement
- **Profit target**: next S&R level in the direction of trade; or 1:2 to 1:3 R:R minimum
- **Take partials** at 1:1 or first S&R in the way; run remainder to final target

## Timeframe

- **Zone identification**: Weekly → Daily (best zones)
- **Entry execution**: 1H → 15m → 5m (depends on position size and style)
- **Applicable to**: day trading, swing trading, position trading — same framework at all TFs

## Best Market Conditions

- Clear trend (up or down) — trade continuation zones (RBR / DBD) in trend direction
- Fresh zone (first retest after a large exit move)
- Zone aligns with HTF S&R (demand zone at weekly support, supply zone at weekly resistance)
- Index and sector aligned with trade direction (odds enhancer)
- Low volume test of zone (confirms remaining orders intact — not consumed)

## Worst Market Conditions

- Choppy / sideways market with no clear trend
- Zone has been tested 3+ times (orders consumed; weak)
- Counter-trend entries at minor S&D zones (daily supply zone inside weekly demand zone = likely to fail)
- Strong momentum move directly into zone (may overwhelm remaining orders)

## Smart Money Market Structure Context

| Phase | Market Action | S&D Implication |
|-------|--------------|-----------------|
| Accumulation | Sideways, low volume | Demand zone forming; Smart Money building longs |
| Trend Up (Rally) | Large up candles, expanding volume | Base left behind = RBR demand zone for next pullback |
| Reaccumulation | Smaller consolidation within uptrend | Minor RBR zone; continuation setup |
| Distribution | Sideways at highs | Supply zone forming; Smart Money exiting longs / building shorts |
| Trend Down (Drop) | Large down candles | Base left behind = DBD supply zone for next bounce |
| Redistribution | Smaller consolidation within downtrend | Minor DBD zone; continuation short setup |

## Relationship to Kalyan's Scalp Setup

Kalyan's sweep-reverse scalp is a **DBR flip zone** entry at intraday scale:
- Price drops into a demand zone (DBR base)
- Sweeps below it (stop hunt = VWAP algo clearing stops per Varmer's mechanism)
- Confirmation candle (structure break upward) signals Smart Money re-entry
- Enter long; stop below the sweep low (buffer below zone); target session high (next supply zone)

The sweep itself is a **spring** (false breakdown below support) — a classic S&D signal that confirms the zone is holding and orders are still there.

## Implementation Coverage in This Repo (2026-08-09)

Drawn while ingesting [[sources/Demand-Supply-Four-Formations-Infographic]]. The four formations have been documented here since 2026-06-18; **this is the first time they were checked against `tools/`.**

| Formation | Type | Detected? | Where |
|---|---|---|---|
| **RBR** Rally-Base-Rally | Continuation (demand) | ⚠️ **partially** | [`scan_base_formation`](tools/scanner_templates.py:863) — but see the contradiction below |
| **DBD** Drop-Base-Drop | Continuation (supply) | ❌ | — |
| **RBD** Rally-Base-Drop | Reversal (supply) | ❌ | — |
| **DBR** Drop-Base-Rally | Reversal (demand) | ❌ | — |

> [!contradiction] The one formation we detect, we trade backwards
> This page says the base **is the zone**: price leaves, returns, and the trade is the **retest**. `scan_base_formation` is Minervini-framed — it requires the full Stage-2 trend template (price > SMA50 > SMA150 > SMA200, within 25% of the 52-week high, ≥25% above the 52-week low), reuses `detect_vcp_geometry` for a contracting base, and buys the **breakout above the pivot**, explicitly *excluding* names that have already broken out. The base is a launchpad there, not a zone to come back to.
>
> **Same shape, opposite trade, different bar.** A Base Formation hit is therefore **not** an RBR demand-zone setup, and wiring one to the other's output would buy the wrong event. Same class of error as treating a wick zone as an order block.

**The gap worth naming: two of the three missing formations are supply-side**, which makes this the fourth instance of a long-only bias found this week — after candlesticks (no bearish patterns until 2026-08-09), [[concepts/Order-Blocks]] (`scan_order_block` long-only) and the same in the FVG scanner.

**DBR is the most interesting absence.** The repo has several reversal-from-decline detectors — Early Reversal Detector, [[concepts/Rounding-Bottom]], [[concepts/Falling-Wedge]], the Drop-Recovery screen — which are the DBR *shape*. But none of them is framed as a base with a tradeable zone, so none emits the zone a retest would be measured against. Turning one into a DBR detector is mostly a matter of marking the base and its retest, not new geometry.

## Backtest / Track Record

- Framework widely used across retail and professional S&D communities
- Aligns mechanically with Varmer's VWAP algo iceberg order model: the base = order accumulation; exit move = institutional buying/selling executed; return to zone = remaining orders filled
- Indian market application: Nifty 50 used as example in the source book for S&D zone illustration

## Examples

- **RBR on Nifty 50**: wide demand zone (prior consolidation) followed by strong upward move; pullback to zone edge = demand zone long entry
- **RBD at session high**: opening rally to prior resistance; consolidation forms; reversal → short from the supply zone
- **Flip zone**: broken resistance on breakout; price pulls back to former resistance (now support) → long entry with stop just below

## Related Concepts

- [[concepts/Support-Resistance]] — S&D zones are the Smart Money / volume-informed version of S&R
- [[concepts/Order-Flow]] — Varmer's iceberg mechanics explain WHY S&D zones work (unfilled orders, VWAP algo re-entry)
- [[concepts/Darvas-Box]] — Darvas consolidation box = S&D base by another name
- [[strategies/Opening-Range-Breakout]] — opening range is the session's first S&D zone; ORB = trading the RBR or DBD from the opening base
- [[concepts/Market-Structure-CHOCH-BOS]] — the swing-structure-labeling half of SMC vocabulary (CHOCH/BOS/MSS/FVG/liquidity), complementary to this page's zone-based half; a flip zone confirmed by a later BOS is the S&D-framework equivalent of a CHOCH

## Sources

1. [SR-SMC-Supply-Demand-Dhruv-Emily-2022](../sources/SR-SMC-Supply-Demand-Dhruv-Emily-2022.md) — all four formations; zone strength factors; entry process; Smart Money signatures; psychology of S&R; breakout conditions
2. [[sources/Demand-Supply-Four-Formations-Infographic]] (2026-08-09) — unattributed retail graphic; **independent corroboration of all four formations and the zone-at-the-base construction, contributing no mechanics this page lacked.** Its value was prompting the implementation-coverage audit above. Useful mnemonic from it: *the middle leg names the zone, the two outer legs name the trade* — same-direction outer legs mean continuation, opposite mean reversal.
