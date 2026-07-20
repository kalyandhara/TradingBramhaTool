---
title: "PMax (Profit Maximizer / ATR Trailing Stop)"
category: concept
tags: [pmax, atr, trailing-stop, chandelier-exit, trend-following]
created: 2026-06-14
updated: 2026-06-15
sources: 2
related: [concepts/EMA, concepts/ADX, strategies/PMax-Confluence-Strategy, strategies/Systematic-Strategy-Search.md]
---

# PMax (Profit Maximizer / ATR Trailing Stop)

## Definition
A Chandelier-Exit-style trend/trailing-stop indicator. It combines an adaptive moving average (`MAvg`) with an ATR-based offset to form a single line (`PMax`) that the price trends along, flips direction on a cross, and can be used both as a trend filter and a trailing stop.

## How to Use
- `MAvg` = moving average of `src` (default `hl2`), selectable type (SMA/EMA/WMA/TMA/VAR/WWMA/ZLEMA/TSF), default length 10.
- `atr` = ATR(10) by default (or SMA of true range if `changeATR=false`).
- `longStop = MAvg − Multiplier × ATR` (default Multiplier = 3.0), ratchets up only (never decreases while in uptrend).
- `shortStop = MAvg + Multiplier × ATR`, ratchets down only while in downtrend.
- `dir` (trend direction) flips from -1→+1 when `MAvg` crosses above the prior `shortStop`, and +1→-1 when `MAvg` crosses below the prior `longStop`.
- `PMax = dir==1 ? longStop : shortStop` — plotted as a single trailing line; price staying above PMax = uptrend, below = downtrend.
- Signals: `MAvg` crossing `PMax` (signal-line cross) or `close` crossing `PMax` (price cross) — the latter is faster/noisier.

## Variants / Parameters
- ATR Length: 10 (default)
- ATR Multiplier: 3.0 (default) — larger = wider stop, fewer whipsaws, more lag
- MA type/length: EMA(10) default — switching to ZLEMA/TSF reduces lag further
- `Normalize` option divides the ATR offset by `close` (percentage-based stop instead of absolute)

## Alternative: "Trailing System Order" Algorithm (Dolzhenko)
A second, rule-based trailing-stop algorithm (distinct from the ATR/Chandelier approach above), useful as a comparison or alternative implementation:
- State variables: `TrailingPrice` (the ratchet anchor, moves only favorably), `ProfitBorderCoeff` and `StopBorderCoeff` (define the take-profit and stop-loss bands as % distances from `TrailingPrice`), `BorderChangeCoeff` (% by which the profit/stop band narrows *each time* `TrailingPrice` ratchets forward), and `DecisionCoeff`/`DecisionSignal`/`DecisionCount` (bookkeeping for the ratchet decision).
- Mechanics: as price moves favorably, `TrailingPrice` ratchets up (for longs) and the profit/stop borders are recalculated *closer* to `TrailingPrice` by `BorderChangeCoeff` each time — i.e. the band progressively tightens as a position becomes more profitable, locking in gains faster the further price runs.
- Worked example from source: `TrailingPrice` ratchets 90 → 97 as price rises; the profit border narrows accordingly to 103.79; when price reaches 105 (exceeding the narrowed profit border), the position is closed.
- Conceptually similar to PMax's ratcheting `longStop`/`shortStop`, but explicitly couples the *tightening rate* to how far price has already run, rather than using a constant ATR multiplier.

## Common Mistakes
- Using PMax alone for entries without trend/momentum confirmation — it's a **trailing stop and trend filter**, best combined with other confluence factors (see [[strategies/PMax-Confluence-Strategy]]).
- Too tight a multiplier (e.g. <2) in choppy/range-bound markets causes frequent direction flips and false signals.

## Related Concepts
- [[concepts/EMA]] — PMax's `MAvg` is often an EMA
- [[concepts/ADX]] — ADX filter helps avoid PMax whipsaws in low-trend regimes
- [[strategies/PMax-Confluence-Strategy]] — full system using PMax as the core trend line

## Examples in This Wiki
- [[strategies/PMax-Confluence-Strategy]] — PMax cross is factor #1/#2 of a 16-factor confluence score driving position sizing

## Sources
- [[sources/PMax-Optimization-Pine]] (2026-06-14)
- [[sources/Dolzhenko-Algorithmic-Trading-Systems-2024]] (2026-06-15) — Trailing System Order algorithm
- [[sources/TradingView-Goodyear-PMax-Strat-Confluence-2026]] (2026-07-02) — a personal "PMax+Strat" script combining this indicator with Elliott Wave, %R Trend Exhaustion, and ~13 other confluence factors into a single-chart dashboard
