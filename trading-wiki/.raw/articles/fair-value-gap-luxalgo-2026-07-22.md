---
source_url: https://www.tradingview.com/script/jWY4Uiez-Fair-Value-Gap-LuxAlgo/
fetched: 2026-07-22
---

# Fair Value Gap [LuxAlgo] — TradingView indicator

## Overview
Standalone open-source TradingView indicator by LuxAlgo that identifies fair value
gaps (FVGs) — imbalances between market participants. Displays gaps alongside
**fill percentages** and **average duration in bars before mitigation**.

## Author & Availability
Created by LuxAlgo. Open-source, freely available on TradingView. LuxAlgo maintains
educational content across social platforms and operates luxalgo.com.

## Core detection rules
Bullish FVGs require three conditions:
- Current low exceeds the prior two-period high (`low > high[2]`)
- Previous close surpasses the two-period high (`close[1] > high[2]`) — directional confirmation
- Gap height ratio exceeds the threshold percentage

Bearish FVGs reverse these: current high falls below the prior two-period low, previous
close below the two-period low, gap-height ratio above threshold.

## Key features
- **Mitigation tracking:** by default displays only *unmitigated* gaps. Users can optionally
  view mitigation levels (lower extremity for bullish, upper for bearish). The **"Dynamic"**
  setting allows monitoring evolved mitigated gaps.
- **Threshold filtering:** gaps filtered by height using percentage-based thresholds. An
  **"Auto"** mode applies cumulative-mean analysis to isolate more volatile gaps.
- **Dashboard:** shows fill percentages and average duration (in bars) before mitigation occurs.
- **Alerts:** built-in notifications trigger when gaps become filled.

## Settings
- Threshold percentage for gap filtering
- Auto threshold toggle
- Unmitigated levels count adjustment
- Mitigated levels display option
- Custom timeframe selection

## Trading approaches
- Contrarian: enter at fill confirmation.
- Trend-following: trade gap identification as a direct signal.
