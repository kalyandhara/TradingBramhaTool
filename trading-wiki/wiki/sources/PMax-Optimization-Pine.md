---
title: "Pine Script — Profit Maximizer Enhanced Strategy (pmax_optimization.pine)"
category: source
tags: [pine-script, tradingview, pmax, confluence, elliott-wave, mansfield-rs, automation]
created: 2026-06-14
updated: 2026-06-14
sources: 1
related: [concepts/PMax, concepts/Elliott-Wave, concepts/Mansfield-RS, strategies/PMax-Confluence-Strategy]
---

# Pine Script — Profit Maximizer Enhanced Strategy

## Metadata
- **Author:** Kalyan (© kalyan), enhanced version
- **File:** `C:\Users\dhara\OneDrive\Documents\Python Scripts\pmax_optimization.pine`
- **Platform:** TradingView Pine Script v6, `strategy()` (backtestable)
- **Date ingested:** 2026-06-14

## Key Takeaways
- A personal "all-in-one" TradingView strategy combining the **PMax indicator** (adaptive MA + ATR trailing stop) with a large **multi-factor confluence scoring system** (16 factors) that drives a graded position-sizing/decision matrix.
- Adds an **Elliott Wave v2 engine**: automatic zigzag pivot detection, 9-position wave cycle tracking, forward wave projections with Fibonacci targets, and EW validity checks (Wave 2/3/4 rules).
- New advanced EW analysis layer: **Short/Long-Term Extension**, **Valuation** (over/undervalued), **Earnings Power proxy**, and **Stage Analysis** (1–4, Wininstein-style).
- Adds **Mansfield Relative Strength** vs a configurable benchmark (default SPY) as a confluence factor.
- Backtest position sizing is **confluence-graded**: 85%+ → 100% size, 70–85% → 75%, 50–70% → hold, 25–50% → reduce, <25% → flat. Stops/targets are ATR-based with a configurable R:R (default 2.5) and optional trailing stop.

## Detailed Notes

### 1. PMax Core (original indicator, retained)
- `PMax` = adaptive moving average (`MAvg`, selectable: SMA/EMA/WMA/TMA/VAR/WWMA/ZLEMA/TSF) offset by `Multiplier × ATR` (default ATR length 10, multiplier 3.0), forming a Chandelier-Exit-style trailing stop/trend line.
- `dir` flips between +1 (uptrend, PMax = longStop below price) and -1 (downtrend, PMax = shortStop above price) when `MAvg` crosses the prior stop level.
- Buy/sell signals: `MAvg` crossing `PMax` (`buySignalPmax`/`sellSignalPmax`) or `close` crossing `PMax` (`buySignalPrice`/`sellSignalPrice`).

### 2. Confluence Factor Set (16 factors, `calcConfluence()`)
Each factor contributes 1 point (candlestick pattern confirmation contributes 2):
1. PMax MA cross
2. PMax price cross
3. Volume > 20-period MA
4. ADX > threshold (default 25)
5. MACD bullish/bearish (line vs signal + histogram)
6. RSI condition (oversold/overbought + 50-midline bias)
7. 9/21 EMA cross or alignment
8. Price vs SMA200 (trend filter)
9. Accumulation/Distribution line vs its MA
10. Bollinger Band breakout (close beyond upper/lower band)
11. 20-period resistance/support breakout
12. ATR breakout (close beyond MAvg ± 1.5×ATR, with ADX confirmation)
13. RSI fast/slow divergence (5 vs 14 period)
14. VWAP filter (rolling SMA-based, length 20 — explicitly **not** session-anchored VWAP, chosen for swing/positional use)
15. Candlestick pattern confirmation (engulfing, hammer/shooting star, morning/evening star, EMA retest, inside bar) — worth 2 points
16. Elliott Wave trend alignment (`ewTrendBull`/`ewTrendBear`)
17. Mansfield Relative Strength vs benchmark

`maxSignals = 18` (16 single-point factors + 1 two-point pattern factor). `confluencePct = currStr / 18 * 100`.

### 3. Elliott Wave v2 Engine
- Zigzag pivots via `ta.pivothigh`/`ta.pivotlow` at depth `ewDepth` (default 5; recommended 5=Daily, 3=Weekly, 2=Monthly).
- Maintains arrays of pivot prices/bar-indices/times (`px`, `pt`, `pTime`) and a running pivot count `pivCnt`.
- 9-position cycle model: `W1, 2a, 2b, W2, W3, 4a, 4b, W4, W5` (impulse cycles) / `W, w1, x1, X, Y, y1, z1, XX, Z` (corrective cycles), with prime marks (`'`, `''`, `'''`) for repeated cycles.
- `autoOff9()` auto-detects current wave position by finding the longest of the last ~18 pivot legs and assuming it's Wave 3.
- Forward projection table (`tblEW`): projects up to 36 future segments using Fibonacci ratios — W1=1.0, W2=0.618 retrace, W3=1.618 extension, W4=0.382 retrace of W3, W5=1.0 — with timeframe-aware bar spacing (`f_ewBarSpacing`: 21 bars/segment daily, 4 weekly, 2 monthly, capped 3–390 intraday).
- EW validity (`ewValid`) requires **none** of:
  - Rule 1 (`r1_v`): Wave 2 retraces beyond 100% of Wave 1 start
  - Rule 2 (`r2_v`): Wave 3 is the shortest of W1/W3/W5
  - Rule 3 (`r3_v`): Wave 4 overlaps Wave 1 price territory
- Additional "modern constraint" checks: alternation (`c_alt`, |W2/W1 − W4/W3| > 0.2) and Fibonacci alignment (`c_fib`, W3 ≥ 1.618×W1 and W2 between 50–78.6% of W1).

### 4. New Advanced EW Analysis Layer
- **Short-Term Extension**: true if price has already exceeded the *next* Fibonacci wave target (e.g., past the W3 1.618 target while "in" W1).
- **Long-Term Extension**: true if the most recent 9-pivot net move is >3× the average of the last 8 swing legs.
- **Valuation**: "Overvalued" at W3/W5 peaks (bull) or troughs (bear) combined with RSI overbought/oversold; "Undervalued" at W2/W4 extremes with RSI extremes, or early W1 with RSI<40; else "Fair".
- **Earnings Power** (proxy, not real fundamentals): "Strong" = impulse phase (W1/W3/W5) + volume above MA + ADX>threshold; "Weak" = corrective phase + volume below MA; else "Moderate"/"Neutral".
- **Stage Analysis** (Weinstein-style 1–4): maps current wave position + bull/bear context to Accumulation / Advancing / Distribution / Declining, with an override to "Correction within Up/Downtrend" on odd EW cycles.

### 5. Mansfield Relative Strength
- `rsRatio = close / benchmarkClose` (benchmark via `request.security`, default SPY — should be swapped to a local index/ETF for Indian markets per the tooltip).
- `rsMansfield = (rsRatio / SMA(rsRatio, 52) − 1) × 100` — classic Stan Weinstein 52-period normalization.
- `rsBullish` = rsMansfield > 0 (outperforming benchmark); `rsRising`/`rsFalling` compare to value 5 bars back.

### 6. Decision Matrix & Position Sizing (Backtest)
| Confluence | Direction | Decision | Position Size |
|---|---|---|---|
| ≥85% + strong signal | Long | STRONG BUY [NEW] | 100% |
| 70–85% + momentum gaining | Long | BUY - ACCUMULATE | 75% (add) |
| 50–70% + momentum weakening | Long | BOOK PROFIT [25%] | hold, scale out 25% |
| 50–70% | Long | HOLD - MAINTAIN | 50% hold |
| <50% (from ≥50%, weakening) | Long | SCALE OUT [50%] | reduce |
| <50% | Long | EXIT / WAIT | 0% |
| (mirrored for Short: SELL/COVER/UNWIND/CLOSE) |

- Stops/targets: `longSL = close − ATR(10)×atrRiskMult(2.0)`; `longTP = close + (close−longSL)×rrRatio(2.5)` (mirrored for shorts).
- Optional trailing stop (`trailPerc`, default 1.0%) applied via `strategy.exit` trail params.
- Entries only fire `if withinWindow` (date-range filter, default 2023-01-01 to 2099-12-31 — effectively "always on" once live).

## Actionable Insights
- This is the user's **personal algorithmic trading system** (Pine Script, TradingView-deployable) — distinct from but complementary to [[strategies/TechnoFunda-Swing]] and [[strategies/VCPBot-Trend-Template]] (Python/screener-based). All three share the "multi-factor confluence" philosophy.
- The **PMax + ATR trailing stop** mechanism is a reusable concept (Chandelier Exit family) — now documented at [[concepts/PMax]].
- The Elliott Wave advanced analysis (Extension/Valuation/Earnings/Stage) substantially extends [[concepts/Elliott-Wave]] from pure pattern theory into an automatable signal — wiki page updated.
- **Mansfield RS vs benchmark** is a new reusable concept ([[concepts/Mansfield-RS]]) — for Indian markets, the benchmark symbol should be set to NIFTY 50 / a relevant sector index rather than the SPY default.
- Default RR (2.5) and ATR risk multiplier (2.0) imply roughly a 1:2.5 reward:risk per the system's own stop placement — worth comparing against [[analyses/Kalyan-Trading-Philosophy]] position-sizing rules.

## Contradictions with Existing Wiki
- None identified. The confluence/multi-filter philosophy is consistent with [[strategies/TechnoFunda-Swing]] (7-condition system) and [[strategies/VCPBot-Trend-Template]] — this Pine script is effectively a TradingView-native implementation of the same "don't trade unless multiple signals align" principle, generalized to a 0–100% confluence score rather than a binary pass/fail.

## Pages Updated
- Created: concepts/PMax.md, concepts/Mansfield-RS.md, strategies/PMax-Confluence-Strategy.md
- Updated: concepts/Elliott-Wave.md (added Extension/Valuation/Earnings/Stage analysis, validity rules), wiki/index.md, wiki/log.md
