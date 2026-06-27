---
title: "YouTube — Free TradingView Plus Alternative (Multi-Chart Web App with Claude Code)"
category: source
tags: [tools, charting, lightweight-charts, tradingview, claude-code, yfinance, live-data, nse, bse, crypto, volume-profile, fair-value-gap, vwap]
created: 2026-06-16
updated: 2026-06-16
sources: 1
related:
  - concepts/VCP.md
  - concepts/Elliott-Wave.md
  - analyses/Kalyan-Trading-Philosophy.md
---

# [YouTube] — Free TradingView Plus Alternative: Multi-Chart Web App via Claude Code

## Metadata
- **Title**: "I Cancelled TradingView Plus After This 1 Claude Code Prompt | Multi Chart & Advanced Indicators"
- **Channel**: AI University (Nitin)
- **URL**: https://www.youtube.com/watch?v=LnyjLNizKHw
- **Ingested**: 2026-06-16
- **Relevance**: Directly actionable — builds a free charting tool covering NSE/BSE live data with premium indicators (Volume Profile, Fair Value Gap) and multi-pane layout. Complements the existing `tools/screener_pipeline.py`.

## Key Takeaways

1. **TradingView free tier limitations** ($30+/month to bypass): single chart, max 2 indicators, no Volume Profile, no Fair Value Gap.

2. **Free replacement stack** built in <15 minutes with one Claude Code prompt:
   - **Charting**: [Lightweight Charts](https://github.com/tradingview/lightweight-charts) — open-source library released by TradingView themselves
   - **Data (crypto)**: Hyperliquid Exchange WebSocket — live prices, no API key, no rate limits
   - **Data (NSE/BSE + US)**: `yfinance` Python library — same library already in screener_pipeline.py
   - **Layout**: Plain HTML/CSS responsive grid, no React; 1/2/4/6/8 simultaneous panes

3. **Premium indicators available for free** via Lightweight Charts + custom code:
   - Volume Profile (VAH, POC, VAL distribution)
   - Fair Value Gap (green = bullish FVG, red = bearish FVG)
   - Plus standard: RSI, MACD, Bollinger Bands, VWAP, Williams %R — unlimited indicators simultaneously

4. **Multi-timeframe capability**: 1m / 5m / 15m / 30m / 1h / Daily / Monthly — same stock across all panes simultaneously.

5. **Multi-market in one app**: Indian stocks (NSE: `RELIANCE.NS`), US stocks (`AAPL`, `TSLA`), crypto (`BTC`, `ETH`, `SOL`) — all on one screen, same layout.

6. **Extensible data feeds**: Hyperliquid and yfinance are pluggable defaults. Can swap in Alpaca (US), Zerodha/Upstox API (Indian), Binance/Coinbase (crypto) with a follow-up Claude Code prompt.

7. **Runs locally**: `localhost:5000`, no deployment, no cloud, no monthly cost.

## Detailed Notes

### Tech Stack (Full)
```
Frontend:  Lightweight Charts (TradingView OSS) + HTML/CSS grid
Backend:   Python (Flask/server on port 5000)
Data:
  - Crypto live:   Hyperliquid WebSocket (no auth required)
  - Stocks live:   yfinance (Yahoo Finance) → NSE, BSE, NYSE tickers
  - Alternatives:  Alpaca API (US), Zerodha KiteConnect / Upstox API (India),
                   Binance / Coinbase API (crypto)
```

### Indicators Available
| Indicator | Type | Notes |
|-----------|------|-------|
| RSI | Standard | Unlimited instances |
| MACD | Standard | |
| Bollinger Bands | Standard | |
| VWAP | Standard | |
| Williams %R | Standard | |
| Volume | Standard | |
| Volume Profile | **Premium** (free here) | VAH, POC, VAL + distribution histogram |
| Fair Value Gap | **Premium** (free here) | Green = bullish FVG, Red = bearish FVG |

### Market Status Logic
- Crypto (Hyperliquid): always live — 24/7
- Indian stocks (yfinance): shows "Indian market closed" outside NSE hours; loads last-close candles
- US stocks (yfinance): same — "US market closed" outside NYSE hours

### Build Steps (Replication)
1. Install VS Code + Claude Code extension (14M downloads, search "Claude Code")
2. Create/open a project folder in VS Code
3. Select model: Sonnet 4.6 (free in most regions) or Opus 4.7 (subscription)
4. Paste the prompt (available in creator's School community — link in video description)
5. Approve all permission dialogs Claude Code requests
6. Run the Python server commands Claude generates
7. Open `http://localhost:5000`

### Prompt Structure (Paraphrased)
> "Please initialize the project and build me a web app that displays a configurable number of live trading charts on a responsive split-screen layout using Lightweight Charts [+ data sources + indicators]."

A single prompt + a few follow-up prompts for extra features built the complete app.

### Extensions Mentioned
- **Price alert script** on top of the same data feed
- **Backtest engine** using the same candle data
- **AI agent** watching a watchlist 24/7 and pinging Telegram
- **Crypto screener + Telegram bot** (separate video)
- **Stock screener (NSE/US) + Telegram alerts** (separate video)

## Actionable Insights for Kalyan's Setup

1. **Direct integration opportunity**: The screener_pipeline.py already uses `yfinance`. Adding a Lightweight Charts frontend dashboard would give live multi-pane charting on whatever stocks the pipeline shortlists — no separate TradingView subscription needed.

2. **Volume Profile for VCP confirmation**: The manual VCP identification step (find base → check volume contraction → confirm pivot) could use the Volume Profile overlay to verify that the POC (Point of Control) is building above prior distribution — a cleaner confirmation of the "overhead supply cleared" signal from [VCP](../concepts/VCP.md).

3. **Fair Value Gap for entry timing**: Fair value gaps mark imbalance zones; a stock breaking out of a VCP base into a bullish FVG has additional momentum context. Useful overlay on the [Minervini SEPA](../strategies/Minervini-SEPA.md) pivot-buy entries.

4. **Multi-timeframe on watchlist names**: With 8 panes, show the same stock on 1H + Daily + Weekly simultaneously — matches Minervini's "check higher timeframe context before entering on daily pivot."

5. **Hyperliquid WebSocket for crypto**: If crypto trading is added to the strategy, Hyperliquid gives free institutional-grade live data. The existing pipeline architecture can be extended with the same WebSocket.

## Contradictions with Existing Wiki
- None. This is a tooling/implementation video, not a strategy or methodology source.

## Pages Updated
- Updated: `wiki/index.md` (pages +1, sources +1)
- Updated: `wiki/log.md`
