---
title: "PMax Confluence Strategy (Profit Maximizer Enhanced)"
category: strategy
tags: [pmax, confluence, elliott-wave, mansfield-rs, atr, pine-script, tradingview, automation]
timeframe: swing
created: 2026-06-14
updated: 2026-06-14
sources: 1
related: [concepts/PMax, concepts/Elliott-Wave, concepts/Mansfield-RS, concepts/ADX, concepts/RSI, concepts/EMA, strategies/TechnoFunda-Swing, strategies/VCPBot-Trend-Template]
---

# PMax Confluence Strategy (Profit Maximizer Enhanced)

## Core Idea
A TradingView Pine Script (v6) strategy that scores up to 16 independent technical factors into a single 0–100% **confluence score**, and uses that score plus a 17th Elliott Wave trend filter to drive a graded decision matrix (STRONG BUY → ACCUMULATE → HOLD → BOOK PROFIT → SCALE OUT → EXIT) and position sizing (0%/25%/50%/75%/100%). [[concepts/PMax]] (ATR trailing stop on an adaptive MA) is the central trend line; everything else either confirms or contradicts its direction.

## Setup Criteria
Core trend line: [[concepts/PMax]] — `PMax = dir==1 ? (MAvg − 3×ATR10) : (MAvg + 3×ATR10)`, where `MAvg` is a 10-period EMA (configurable) of `hl2`.

### The 16 Confluence Factors (1 pt each, candlestick pattern = 2 pts; max = 18)
1. PMax MA cross (`MAvg` crosses `PMax`)
2. PMax price cross (`close` crosses `PMax`)
3. Volume > 20-period volume MA
4. ADX(14) > 25 (trend strength)
5. MACD(12,26,9) bullish/bearish + crossover
6. RSI(14): oversold/overbought + 50-midline bias
7. 9/21 EMA cross or alignment
8. Price vs SMA(200) — long-term trend
9. Accumulation/Distribution line vs its 14-period MA
10. Bollinger Bands(20, 2σ) breakout
11. 20-period resistance/support breakout
12. ATR(14) breakout: close beyond `MAvg ± 1.5×ATR` with ADX confirmation
13. RSI divergence: 5-period vs 14-period RSI
14. Rolling VWAP(20) — SMA-based, not session-anchored (chosen for swing/positional holding)
15. Candlestick pattern (engulfing, hammer/shooting star, morning/evening star, EMA retest, inside bar) — **2 points**
16. Elliott Wave trend alignment ([[concepts/Elliott-Wave]] v2 engine, 9-position cycle)
17. [[concepts/Mansfield-RS]] vs benchmark (default SPY — use NIFTY 50 for Indian equities)

`confluencePct = (sum of factors aligned with current direction / 18) × 100`

## Entry Rules
- **STRONG BUY/SELL [NEW]** — `confluencePct ≥ 85%` AND a "strong" signal (all enabled filters aligned + a confirming candlestick pattern + valid, aligned Elliott Wave) → enter 100% position.
- **ACCUMULATE/REDUCE [70–85%]** — confluence 70–85% with momentum *gaining* (current confluence > previous bar's) → add 75% position.
- Entries gated by `withinWindow` (date-range filter; defaults effectively "always on").

## Exit Rules (profit target + stop loss)
- **Stop loss:** `ATR(10) × 2.0` from entry (long: `close − 2×ATR`; short: `close + 2×ATR`).
- **Take profit:** Risk × 2.5 R:R (`longTP = close + (close − longSL) × 2.5`).
- **Trailing stop:** optional, 1.0% trail once enabled (`useTrailing`).
- **Scale-out logic** (signal-based, not just price-based):
  - 50–70% confluence + momentum *weakening* → **BOOK PROFIT [25%]**
  - confluence drops below 50% from ≥50% while weakening → **SCALE OUT [50%]** (long) / **UNWIND [50%]** (short)
  - confluence < 50% → **EXIT/WAIT** (long) / **CLOSE/WAIT** (short) — close remainder

## Timeframe
Swing (designed with daily bars in mind; EW pivot depth and bar-spacing presets also support weekly/monthly/intraday).

## Best Market Conditions
- Trending markets where PMax direction persists and multiple factors (trend, momentum, volume, RS) align in the same direction — same regime where [[strategies/TechnoFunda-Swing]] and [[strategies/VCPBot-Trend-Template]] also perform best.
- Elliott Wave impulse phases (W1/W3/W5) with high volume + ADX>25 register as "Strong" Earnings Power and reinforce the signal.

## Worst Market Conditions
- Choppy/range-bound markets: PMax direction flips frequently, ADX stays <25 (factor 4 fails), and confluence rarely exceeds 50% → system correctly stays in WAIT/HOLD, but whipsaws are possible if `Multiplier` is set too low.
- Elliott Wave "INVALID" state (Wave 2 >100% retrace, Wave 3 shortest, or Wave 4 overlaps Wave 1) suppresses both strong buy and strong sell signals (`ewValid` gate).

## Backtest / Track Record
- Not yet run/recorded. Built-in `strategy()` backtester with `initial_capital=10000`, `default_qty_type=percent_of_equity`. Position sizing scales with confluence: 100% (≥85%), 75% (70–85%), 50% (50–70% hold), 25% (25–50% reduce), 0% (<25%).
- TODO: log actual backtest results here once run on target symbols/timeframes.

## Examples
- None logged yet — file via TRADE LOG operation once live signals are taken.

## Related Concepts
- [[concepts/PMax]] — core trailing-stop/trend line
- [[concepts/Elliott-Wave]] — v2 pivot engine + Extension/Valuation/Earnings/Stage analysis layer
- [[concepts/Mansfield-RS]] — relative strength factor
- [[concepts/ADX]], [[concepts/RSI]], [[concepts/EMA]] — component filters
- [[strategies/TechnoFunda-Swing]], [[strategies/VCPBot-Trend-Template]] — sibling multi-factor confluence systems (screener/Python-based vs this Pine/TradingView implementation)

## Sources
- [[sources/PMax-Optimization-Pine]] (2026-06-14)
