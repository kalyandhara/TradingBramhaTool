---
title: "TradingView Screenshot — Goodyear India, PMax+Strat Confluence Dashboard"
category: source
tags: [tradingview, pmax, elliott-wave, percent-r, confluence, screenshot]
created: 2026-07-02
updated: 2026-07-02
sources: 1
related:
  - concepts/Percent-R-Trend-Exhaustion.md
  - concepts/PMax.md
  - concepts/Elliott-Wave.md
  - concepts/Stage-Analysis.md
---

# TradingView Screenshot — Goodyear India, "PMax+Strat" Confluence Dashboard

## Metadata
- Chart: Goodyear India Limited (NSE), 1D, TradingView, captured 2026-07-02 19:38 UTC+5:30
- Indicator: a personal/custom Pine script labeled "PMax+Strat (hl2, 10, 3, EMA, 10, 14, 5, 70, 12, 26, 9, 20, 14, 25, ...)" by TradingView user "happyBus57684" — not a public open-source repo, ingested from the screenshot only
- Ingest trigger: Kalyan shared the chart while asking whether there's a "handy method to detect the early buy sign on large scale," having just told this wiki's own analysis to skip Elliott Wave automation

## Key Takeaways

- **This is the real-world validation the %R Trend Exhaustion port needed.** The bottom pane is literally the same indicator ported into this project ([[concepts/Percent-R-Trend-Exhaustion]]) — confirmed by the exact label "%R Trend Exhaustion [upslidedown] (60, 1 Oscillator Mode, 80, Standard (2 Period), close, 20, ema, 3, 21, 7, 112, 3, ...)". Seeing it fire a clean bullish exhaustion (▲) right at the stock's multi-month low, immediately ahead of a fresh Wave 1-2 impulse, is a real confirming data point that this signal has genuine predictive value here — not just a syntactically-correct port.
- **The chart tells a complete cycle**: a 5-wave impulse top (Feb-Aug 2025, W1-W5 labeled) → a sharp ~45% decline into an A-B-C-style corrective bottom (labeled W3-W4-W5 of the *correction* in the screenshot's own convention, confusingly reusing wave numbers) around early-to-mid 2026 → the %R Trend Exhaustion bullish signal fires almost exactly at that low → price recovers and a fresh W1-W2 impulse structure forms into a "Buy" label near the current bar.
- **The full indicator stack is much richer than just %R/EW**: visible category badges include Trend Align, Momentum, Vol/Stage, Volatility, Breakout, MACD, EMA Cross, VWAP, ATR Break, RSI Div, Extension Risk, Valuation, Earnings Power, ADX+RSI, Rel Strength, and a final CONFLUENCE score. This is a single-symbol "kitchen sink" dashboard, not a bulk screener — the underlying idea (many independent signals converging on one verdict) is the same shape as this wiki's own conviction-score pattern (Pre-Breakout Screener, VCP scoring) but applied per-chart rather than per-scan.
- **PMax is already documented** ([[concepts/PMax]]) — this screenshot's "PMax+Strat" name and the visible chandelier-style band around price during the uptrend/downtrend legs are consistent with that existing concept page's ATR-trailing-stop description.

## Detailed Notes

The wave-target table (bottom right of chart) shows a live Elliott Wave projection: W2 target 841.60 (+5.23%), W3 target 732.05 (-8.47%), W4 target 777.90 (-3.23%), W5 target 706.20 (-11.79%) — i.e. the script is actively forecasting a *lower* W3/W5 even while price sits at 799.75 near a "Buy" label. This internal tension (bullish %R exhaustion + bullish wave label vs. a wave-target table implying more downside) is exactly the kind of subjectivity/reliability problem already flagged when [[concepts/Elliott-Wave]] automation was explicitly deprioritized in this wiki's own analysis — kept here as a concrete example rather than an abstract concern.

## Actionable Insights

Kalyan's question — "do we have a handy method to detect the early buy sign on large scale" — **without** re-opening Elliott Wave automation, answers cleanly with signals already built or cheaply addable in this project:

1. **Bullish %R Trend Exhaustion** (already built, `compute_recent_exhaustion_signal`) — the single most directly-validated signal from this chart. Already wired into the High-Growth Screener.
2. **Price reclaiming a key MA after a decline** (e.g. close crossing back above EMA21/50 having been below it) — cheap, not yet built as a standalone bulk-screenable signal.
3. **RS turning up from a low base** — distinct from "RS is already high" (which the existing CANSLIM/RS-rank logic catches); this is a *second derivative* signal (RS trend improving, even if the absolute RS rank is still low) that specifically catches stocks early in a Stage 1→2 transition rather than ones already recognized as leaders.
4. **Volume drying up into the low, then picking up on the reversal** — classic accumulation signature, cheap to compute from OHLCV already being fetched everywhere in this pipeline.

None of these require wave-counting. Combining #1+#2+#3 (and optionally #4) as an AND-gate or a weighted score is a direct, buildable "Early Reversal / Stage 1→2 Transition Detector" — proposed as a new scanner rather than built here, pending confirmation of thresholds and whether it becomes its own page or an addition to the High-Growth Screener.

## Contradictions with Existing Wiki

None directly — the wave-target table's implied further downside despite a bullish short-term signal restates, rather than contradicts, the already-documented reason Elliott Wave automation was deprioritized (subjective, can point two directions from the same chart at once).

## Pages Updated

- concepts/Percent-R-Trend-Exhaustion.md — new concept page, this screenshot is its motivating real-world example
