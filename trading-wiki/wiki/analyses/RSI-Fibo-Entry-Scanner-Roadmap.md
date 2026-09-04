---
title: "RSI-Fibo Entry Scanner — Roadmap"
category: analysis
tags: [backlog, scanner, RSI, fibonacci, divergence, swing-trading]
timeframe: swing
created: 2026-08-31
updated: 2026-08-31
sources: 1
related:
  - analyses/Open-Backlog.md
  - concepts/RSI.md
  - concepts/Fibonacci-Retracement.md
---

# Analysis: RSI-Fibo Entry Scanner — Roadmap

## Core Idea

Confluence scanner that fires when **two independent conditions align**:

1. **Hidden RSI Divergence** (bullish continuation) — price makes a higher low
   while RSI(14) makes a lower low, signalling underlying strength during a
   pullback in an uptrend.
2. **50% Fibonacci Retracement hold** — price pulls back to the 50% fib level
   (measured swing-low → swing-high) and holds / bounces, confirming
   institutional demand at the equilibrium zone.

Entry at the 38.2% level (after bounce confirmed), stoploss below 61.8%,
targets at prior swing high / extensions.

## Why it matters

Most divergence scanners fire on *regular* divergence (reversal). Hidden
divergence is a **continuation** signal — it catches pullback entries in
established trends, which have a higher base rate than countertrend reversals.
The fib filter adds a second, geometrically independent confirmation.

## Phased plan

| Phase | Scope | Depends on |
|-------|-------|------------|
| RFE-1 | Swing-high/low detection + RSI hidden-divergence flag (daily) | — |
| RFE-2 | Fib-retracement overlay; confluence when divergence + 50% fib hold | RFE-1 |
| RFE-3 | Scanner Hub card with entry/stop/target levels | RFE-2 |
| RFE-4 | Backtest on NIFTY 500 universe (win-rate, R:R at 38.2 entry / 61.8 stop) | RFE-2 |

### RFE-1 — Hidden divergence detector

- Identify swing highs/lows using fractals or a rolling-window method.
- Compute RSI(14, close).
- Hidden bullish divergence: price higher-low AND RSI lower-low between two
  consecutive swing lows.
- Hidden bearish divergence (optional mirror): price lower-high AND RSI
  higher-high.

### RFE-2 — Fib confluence filter

- Measure last completed swing (low → high for bullish).
- Compute 23.6 / 38.2 / 50.0 / 61.8 / 78.6 retracement levels.
- Fire confluence signal when hidden-bullish-divergence detected AND current
  price is within tolerance (±1.5%) of the 50% retracement level.

### RFE-3 — Scanner Hub integration

- Card output: ticker, divergence type, fib level held, suggested entry
  (38.2%), stoploss (below 61.8%), target (swing high).
- Sortable by R:R ratio.

### RFE-4 — Backtest

- Universe: NIFTY 500 daily, 3-year lookback.
- Entry: next-day open after confluence signal.
- Exit: 38.2% entry → swing-high target (profit) or 61.8% break (stop).
- Metrics: win-rate, avg R:R, max drawdown, Sharpe of signal-only equity curve.

## Open questions

- Swing detection method: fractals (±N bars) vs. ZigZag vs. ATR-filtered?
- Should the scanner require the stock to be above its 200 EMA (trend filter)?
- Include hidden bearish divergence for short/exit signals?

## Related Pages

- [[analyses/Open-Backlog]]
