---
title: "VCPBot Architecture — 7-Phase Pipeline"
category: analysis
tags: [python, algo-trading, architecture, pipeline, Alpaca, automation]
created: 2026-06-14
updated: 2026-06-14
related: [concepts/VCP.md, strategies/VCPBot-Trend-Template.md, analyses/VCPBot-Risk-System.md]
---

# VCPBot Architecture — 7-Phase Pipeline

> Source: https://github.com/blacckbeard4/VCPBot

## Overview
Fully automated daily swing trading bot. Pipeline runs once per day at 4:05 PM (after market close). Orders placed next morning at 9:30 AM open.

## Tech Stack
- **Python 3.12** — runtime
- **yfinance** — OHLCV price data (free, no API key needed)
- **alpaca-py** — brokerage API (orders, portfolio management)
- **APScheduler** — cron-style 6-job scheduling
- **pandas + pandas-market-calendars** — data + NYSE calendar
- **SQLite (WAL mode)** — persistence across restarts
- **Telegram Bot API** — real-time trade alerts
- **Oracle Cloud VM** — deployment (free tier: 1GB RAM, 1 OCPU)

## The 7 Phases

### Phase 1 — Regime Filter (`regime.py`)
**Runs:** 4:05 PM daily
SPY and QQQ vs SMA200 determine market state:

| State | Condition | Risk |
|-------|-----------|------|
| NORMAL | SPY ≥ SMA200 | 2% per trade |
| CASH | SPY below SMA200 | No new entries |
| FTD | Day 4–7 rally attempt, SPY or QQQ +1.5% on higher vol | 1% per trade |

State persists to SQLite (survives restarts). Telegram alert on regime change.

### Phase 2 — Universe Screen (`tickers.py` + `scanner.py`)
**Hard gates:** ADV50 > 1M shares, Close > $10, Close > SMA200
Downloads all active US equities via yfinance in batches of SCANNER_BATCH_SIZE.
Failures fall back to per-ticker download with exponential backoff (60s, 120s, 180s).

### Phase 3 — Trend Template + RS Rank (`scanner.py`)
All 7 Minervini conditions must pass (see [[strategies/VCPBot-Trend-Template]]).
RS Raw = 0.4×ROC63 + 0.2×ROC126 + 0.2×ROC189 + 0.2×ROC252
Dual-gate: peak RS (60-day trailing) ≥ 80th percentile AND current RS ≥ 80th percentile.
Sector cap: max 2 open positions per sector (via yfinance sector lookup, Finnhub fallback).

### Phase 4 — VCP Detection (`vcp_detector.py`)
3-tier hierarchical detection (see [[concepts/VCP]] for full logic):
- Pass 1: Left Side High (macro, n=15)
- Pass 2: Contraction pairs (adaptive n based on base length)
- Pass 3: Micro pivot + stop (n=3, post-contraction window only)
Earnings blackout check runs here (rejects within N days of earnings).
Outputs: pivot_price, stop_loss_price, base_duration, contraction_depths, ATR%, pattern_type (VCP or VCP_1C).

### Phase 5 — Risk Sizing (`risk_manager.py`)
```
Position size = (Account equity × Risk%) / (Pivot - Stop)
```
- Normal mode: 2% risk per trade
- FTD mode: 1% risk per trade
- Hard limits: stop ≤7% below pivot, max 5 positions, max 10% total portfolio risk
Approved setups written to SQLite as PENDING.

### Phase 6 — Execution (`executor.py`)
**9:30 AM:** Places GTC bracket orders on Alpaca
- Buy stop: pivot + $0.05
- Buy limit (slippage cap): pivot + $0.25
- Take profit: +20% (linked bracket)
- Stop loss: calculated from Phase 5 (server-side bracket)

**Gap check at open:** If price opens >2% above pivot → GAP_CANCELLED (don't chase)

**10:30 AM RVOL check:** If intraday volume < 1.5× expected → RVOL_CANCELLED (weak breakout)

### Phase 7 — Trade Management (`monitor.py`)
Runs every 30 minutes during market hours + EOD.
- Fill confirmation (PLACED → OPEN)
- Stop/target hit detection (OPEN → STOPPED / TARGET_HIT)
- Stale order cancellation (orders not triggered in 1 day → EXPIRED)
- Expectancy tracking written to trade_log.csv

## Trade Status Flow
```
PENDING → PLACED → OPEN → STOPPED / TARGET_HIT
              ↓          ↓
        GAP_CANCELLED  RVOL_CANCELLED
              ↓
           EXPIRED
```

## Daily Schedule
| Time (US/ET) | Action |
|---|---|
| 9:30 AM | Phase 6: Place GTC bracket orders |
| 10:30 AM | Phase 6: RVOL confirmation check |
| Every 30 min | Phase 7: Intraday monitor |
| 4:05 PM | Phase 1–5: Full scan pipeline |
| 4:05 PM | Phase 7: EOD monitor |

## SQLite Schema (5 tables)
- `trades` — PENDING → OPEN → final state
- `scan_log` — daily pipeline stats
- `portfolio_state` — daily NAV + drawdown snapshots
- `regime_state` — Cash/FTD/Normal (survives restarts)
- `errors` — step-level error log

## Key Risk Parameters
| Parameter | Value |
|-----------|-------|
| Risk per trade (Normal) | 2% of equity |
| Risk per trade (FTD) | 1% of equity |
| Max stop distance | 7% below pivot |
| Take-profit target | +20% |
| Entry trigger | pivot + $0.05 |
| Entry limit | pivot + $0.25 |
| Min base | 4 weeks |
| Max final contraction | 8% (standard) |
| RS Rank minimum | 80th percentile |
| ADV50 minimum | 1,000,000 shares |
| Min price | $10 |
| Max positions | 5 |
| Max sector positions | 2 |
| Max portfolio risk | 10% |

## Deployment
Oracle Cloud VM.Standard.E2.1.Micro — 1GB RAM, 1 OCPU, Ubuntu.
Memory-conscious batched processing (important for 1GB constraint).
Runs as systemd service — auto-restarts on crash.

## Related
- [[concepts/VCP]] — Core strategy being automated
- [[strategies/VCPBot-Trend-Template]] — Phase 3 filter detail
- [[analyses/VCPBot-Risk-System]] — Phase 5 risk sizing detail
