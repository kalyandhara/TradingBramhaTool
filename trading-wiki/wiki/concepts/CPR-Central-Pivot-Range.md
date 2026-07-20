---
title: "CPR — Central Pivot Range"
category: concept
tags: [cpr, pivots, intraday, indian-retail, range-forecasting, floor-pivots]
created: 2026-07-08
updated: 2026-07-08
sources: 1
related: [sources/CPR-GuruprasadMeduri-Pine, concepts/VWAP]
---

# CPR — Central Pivot Range

## Definition
**CPR (Central Pivot Range)** is a three-line intraday support/resistance band computed from the **previous day's High, Low, and Close**:

```
Pivot  =  (H + L + C) / 3          ← central pivot line
BC     =  (H + L) / 2               ← bottom central line
TC     =  (Pivot − BC) + Pivot      ← top central line
       =  2·Pivot − BC              (equivalent form)
```

The three lines are drawn horizontally across today's session. The **band width** — the vertical distance from BC to TC — is itself a forecasting signal for the day: narrow band predicts a trending day, wide band predicts a range-bound day.

## How to Use
CPR is a **day-forecasting + zone identification tool**, not an entry trigger. Read it in three steps every morning before market open.

### Step 1 — Read the band width for the day's regime
- **Narrow CPR** (band < ~0.3% of price, or narrower than the last 3-5 sessions): market is **coiled**. Expect a **trending day** with a decisive direction move away from the CPR. Trade the breakout out of CPR on either side; avoid mean-reversion inside the CPR.
- **Wide CPR** (band > ~1% of price, wider than usual): market is **loose**. Expect a **range-bound day**. Fade the CPR edges; avoid chasing breakouts because the CPR band itself is where price will hover.
- **Normal CPR** (band ~0.5% of price): default, no strong day-forecast bias.

### Step 2 — Read the position relative to yesterday's CPR
- **Today's CPR entirely above yesterday's CPR** → **bullish structural bias**. Base case: buy dips to today's CPR.
- **Today's CPR entirely below yesterday's CPR** → **bearish structural bias**. Base case: sell rallies into today's CPR.
- **Overlapping CPRs (today's crosses yesterday's)** → **no directional bias**. Regime-agnostic day; go by intraday price action.
- **Untested CPR** — if price opens away from CPR and doesn't return in the first hour, CPR often magnets price by mid-session (mean-reversion tell).

### Step 3 — Trade around the levels
- **Pivot line** = the strongest of the three; often the day's fair value. Watch closely for reactions.
- **BC as support / TC as resistance** in a range-bound day.
- **CPR + floor pivots** (S1/R1/S2/R2/S3/R3) — CPR gives the range shape, floor pivots give the extension targets. Both come from the same previous-day H/L/C, so they compose naturally.
- **CPR + VWAP** — [[concepts/VWAP]] gives the intraday anchor; CPR gives the daily-derived reference band. **When VWAP is inside the CPR**, expect chop. **When VWAP is above TC or below BC**, the day's directional bias is confirmed.

## Variants / Parameters

### Weekly and Monthly CPR
Same formula, different bar. Weekly CPR uses last week's H/L/C — persists for a week. Monthly CPR uses last month's H/L/C — persists for the month. **Confluence reading:** when daily-CPR, weekly-CPR, and monthly-CPR *all overlap* at a common level, that level is high-conviction support/resistance.

### CPR width thresholds (rules of thumb)
| Band width (% of price) | Regime forecast |
|---|---|
| < 0.3% | Trending day — trade breakout |
| 0.3–0.5% | Slight trend bias |
| 0.5–1.0% | Normal — no strong prior |
| > 1.0% | Range day — fade edges |

Thresholds are indicative — calibrate by watching your specific instrument's typical CPR width over 20 sessions.

### Timeframe applicability
- **Daily CPR:** intraday charts (1m, 5m, 15m). This is the canonical use.
- **Weekly CPR:** intraday + daily charts.
- **Monthly CPR:** daily + weekly charts.
- CPR does *not* meaningfully apply to sub-minute charts (noise) or crypto (no daily session close boundary — needs an anchor definition).

## Common Mistakes
- **Treating CPR as an entry signal.** It's a *range and regime forecast*, not "buy at BC, sell at TC" mechanically. Confirm with price action.
- **Ignoring band width.** The single most-neglected signal on this indicator. Traders draw the lines and forget to check whether it's wide or narrow — but that IS the day's regime forecast.
- **Using single-timeframe CPR only.** Daily CPR alone is decent; daily + weekly + monthly confluence is where the real edge sits. Skipping the MTF read leaves ~half the value on the table.
- **Applying CPR to markets without a defined daily session.** Crypto 24/7 → CPR needs an anchor (e.g., 00:00 UTC boundary). Otherwise the pivot is ambiguous.
- **Extending CPR across too many days.** Yesterday's CPR is relevant *today only*. By tomorrow, use tomorrow's CPR — the old one is no longer load-bearing.
- **Confusing "narrow CPR = bullish."** Narrow CPR is *directional*, not directional-up. It forecasts *movement*, not *direction of movement*.

## Related Concepts
- [[concepts/VWAP]] — intraday anchor. Composes naturally with CPR: VWAP is the mid-day anchor, CPR is the whole-session frame. See "Step 3" above for the confluence read.
- [[concepts/Multi-Timeframe-Analysis]] — CPR's real strength is the daily + weekly + monthly confluence stack.
- **Floor pivots (S1-S3, R1-R3)** — CPR's siblings from the same previous-day H/L/C computation. Concept page not yet in wiki — flagged as follow-up.
- **Camarilla pivots** — alternative pivot system using different weights on H/L/C. Not covered by this ingest; noted for future.

## Examples in This Wiki
- **[[sources/CPR-GuruprasadMeduri-Pine]]** — Pine v4 implementation with the full daily/weekly/monthly stack and style-coding (daily solid, weekly `+`, monthly `o` markers) that makes the confluence readable.
- **Live use example flagged for future analysis** — apply CPR + weekly CPR to a NIFTY reversal day (e.g. 2026-07-07, see [[analyses/Nifty-Options-EOD-20260707]]) and cross-reference against the OI-flow read. Both signals should agree on regime characterization if the tool is sound.

## Sources
- [[sources/CPR-GuruprasadMeduri-Pine]] — Pine script formulas, MTF style-coding, and configuration options.
