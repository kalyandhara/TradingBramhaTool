---
title: "Hyperliquid 3-Filter Momentum Screener (Volume + Momentum Floor/Ceiling + EMA/VWAP Trend)"
category: strategy
tags: [crypto, day-trading, swing, screener, hyperliquid, volume, momentum, ema, vwap, telegram-alerts, claude-code]
created: 2026-06-29
updated: 2026-06-29
sources: 1
related:
  - strategies/Screener-Queries.md
  - concepts/EMA.md
  - concepts/ADX.md
  - sources/YT-MultiChart-TradingView-Alternative.md
  - sources/YT-Breakout-Screener-AIUniversity-20260629.md
---

# Hyperliquid 3-Filter Momentum Screener

## Core Idea

Don't trade on one signal. A single indicator (price up, volume high, EMA cross) fires
constantly on fake pumps, dead-cat bounces, and wash trades. Combine three
**independent** confirmations that each verify a different dimension of the same move —
participation, timing, and direction — and only flag setups where all three agree
simultaneously.

## Setup Criteria

**Filter 1 — Volume surge (participation)**
```
24h volume / market cap > 0.10
```
More than 10% of a coin's total market value traded in a single day = real capital
moving, not noise. Dividing by market cap normalizes across coin sizes so a $500M asset
and a $5B asset are compared fairly. Non-negotiable — no volume, no move.

**Filter 2 — Short-term momentum with floor AND ceiling (timing)**
```
1h change:  +1% to +5%
24h change: +5% to +15%
```
- **Floor** (+1%/+5%) confirms the move has already started — you're confirming entry,
  not predicting.
- **Ceiling** (+5%/+15%) prevents chasing. A coin up 20%+ in 24h is overextended, profit
  takers are heavy, risk/reward has already turned against you. Most tutorials/screeners
  only set a floor — the ceiling is what separates a real signal from a chase trade.

**Filter 3 — Trend confirmation (direction)**
```
EMA9 > EMA21 > EMA50   (ascending stack — short/medium/long-term agree)
Price > VWAP            (buyers in control since session open)
```
Fake pumps almost always fail EMA alignment or sit below VWAP — this filter kills them.

## Entry Rules

Flag/alert only when **all three filters fire simultaneously**:
volume confirms real participation + momentum confirms the move started without being
overextended + trend confirms direction. Not a buy signal by itself — "the algorithm
finds the setup, your analysis and judgment decide what to do with it."

## Exit Rules (profit target + stop loss)

Not specified in the source — this is a *screener*, not a full trading system. No exit
rules given; treat as a watchlist-generation filter to feed into whatever entry/exit
system is already in use (e.g. [[strategies/Screener-Queries]] or a Stage-2/EMA-pullback
approach for the equities side).

## Timeframe

- Selectable scan timeframe: 1m / 5m / 15m / 1h / 1d (re-screens automatically on that
  interval and re-fires Telegram alerts on each pass)
- **Day trading mode**: as configured above
- **Swing trading mode**: same three filters, just widen the momentum floor/ceiling
  thresholds and lengthen the scan timeframe — "flips this from a day trading screener
  to a swing trading screener without rewriting a single function." Exact swing
  thresholds weren't given numerically in the transcript.

## Best Market Conditions

- Active/trending crypto markets with dispersion across coins (so volume/cap and
  momentum filters can actually discriminate)
- Useful as a pre-filter before manual chart review — replaces "staring at 50 charts and
  guessing"

## Worst Market Conditions

- Broad, low-dispersion markets (everything moves together) — the screener will either
  flag too many or too few coins, since the filters rely on relative outperformance
- Not designed for stops/targets — applying it as a complete system without overlaying
  risk management would be a misuse

## Backtest / Track Record

None given — this is a screening/alerting tool, not a backtested strategy. No win rate,
no track record claimed by the creator.

## Examples

- Live demo: 5-minute timeframe scan flagged two coins ("PENDLE" and "NIL", per the
  transcript's "pandle and nil") that passed all three filters; Telegram alert fired
  immediately, then re-fired with two more coins on the next 5-minute refresh cycle.

## Implementation Notes (for replication)

- **Data source**: Hyperliquid public API — free, no API key, no signup. Gives live
  prices, 24h change, volume, and candle history for every perpetual market on the
  exchange. This is the same Hyperliquid REST/WS source already implemented in
  [data_source.py](../../../tools/data_source.py) (`HyperliquidSource`) and
  [chart_server.py](../../../tools/chart_server.py) for the multi-chart dashboard from
  [[sources/YT-MultiChart-TradingView-Alternative]] — the EMA/VWAP/volume math could be
  layered on top of that existing connection rather than rebuilt from scratch.
- **Alerting**: Telegram Bot API. Setup = create bot via @BotFather (`/newbot` → display
  name + unique `_bot`-suffixed username → bot token), then get chat ID via
  `https://api.telegram.org/bot<TOKEN>/getUpdates` after sending the bot a `/start`
  message and one text message.
- **Stack**: Python + FastAPI backend + simple web UI, built via Claude Code (Opus 4.7)
  from a single detailed prompt plus follow-up prompts for UI tweaks (filter toggles,
  per-timeframe presets, chart-icon drill-down, auto-refresh + alert checkbox). Runs on
  `localhost:8000`.
- **UI exposed all filter parameters as adjustable controls**: relative volume threshold,
  min/max 24h % change, min/max move for the selected timeframe, EMA fast/mid/slow
  periods (default 9/21/50), and an above-VWAP / below-VWAP toggle (for long vs. short
  setups) — plus a "reset to default" button.

## Related Concepts

- [[concepts/EMA]] — the 9/21/50 ascending-stack trend filter is the same multi-EMA
  alignment principle documented there
- [[strategies/Screener-Queries]] — equities-side screener catalog; this is the crypto
  analog with an explicit floor+ceiling momentum band that the existing CCI-gated
  scanners don't use
- [[sources/YT-MultiChart-TradingView-Alternative]] — same channel, same Hyperliquid data
  source, companion charting tool

## Sources

1. [YT-Breakout-Screener-AIUniversity-20260629](../sources/YT-Breakout-Screener-AIUniversity-20260629.md) — full transcript ingested 2026-06-29
