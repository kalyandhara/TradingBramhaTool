---
source_url: https://www.tradingview.com/script/5jS51RsP-Multitimeframe-Fair-Value-Gap-FVG-Zeiierman/
fetched: 2026-07-22
---

# Multitimeframe Fair Value Gap (FVG) [Zeiierman] — TradingView indicator

## Overview
Open-source TradingView indicator analyzing institutional imbalances (Fair Value Gaps)
across multiple timeframes to identify price inefficiencies and potential entries.
Advanced visualization + true multi-timeframe capability.

## Core functionality
- **FVG detection:** three-candle sequence where a market imbalance leaves a gap between
  the wicks of candle 1 and candle 3 (wick logic).
- **Multitimeframe:** analyze FVGs from a higher OR lower timeframe regardless of current
  chart, via `request.security()` fetching OHLCV independently.

## Key features & algorithm
- **Wick sensitivity & impulse filter:** measures wick sizes of potential FVG candles
  against a running average; filters gaps below a user-controlled sensitivity threshold
  to eliminate weak signals.
- **Midpoint mitigation logic:** FVGs marked "mitigated" when price revisits the gap;
  user controls whether full closure OR midpoint touch triggers removal.
- **Bull & Bear Power visualization:** volume-weighted sub-bars within each FVG box show
  estimated buy/sell effort — Buy Volume ≈ effort from low to close; Sell Volume ≈ effort
  from high to close. Bars proportionally colored bullish/bearish by dominance.
- **FVG table:** optional on-chart side panel listing all currently active (unmitigated)
  FVGs with timestamps, color-coding, auto-updates.
- **Trend filter (Butterworth smoother):** two-pole Butterworth low-pass filter computes a
  smoothed trendline to categorize FVGs as trend-aligned or countertrend.

## Settings / parameters
- **FVG Timeframe:** independent timeframe source
- **Sensitivity:** impulse-strength filter
- **Mitigated on Mid:** midpoint vs full-fill closure logic
- **Table Settings:** position and width
- **FVG Style:** box colors, length, overlay options
- **Trend Filter:** enable/disable; smoothing controls (Passband Ripple in dB;
  Cutoff Frequency 0–0.5)

## Distinguishing features
1. True multitimeframe analysis independent of chart timeframe.
2. Volume-contextualized gap analysis via bull/bear power.
3. Butterworth-filtered trend logic for signal categorization.
4. Real-time FVG table watchlist overlay.

## Author
Zeiierman (TradingView Wizard). zeiierman.com; Discord (discord.gg/zeiiermantrading);
X, YouTube, Facebook, Instagram.
