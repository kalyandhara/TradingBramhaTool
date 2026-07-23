---
source_url: https://www.tradingview.com/script/Onab2fvE-Fair-Value-Gaps-by-DGT/
fetched: 2026-07-22
---

# Fair Value Gaps by DGT — TradingView indicator

## Core functionality
Detects and visualizes Fair Value Gaps (FVGs) — institutional imbalance zones
representing liquidity displacement. Continuously tracks unfilled, partially repaired,
and fully resolved imbalances across multiple timeframe perspectives.

## Key features

### Multi-timeframe detection (three sources)
Identifies FVGs from:
- the current chart timeframe,
- higher timeframes (HTF),
- lower timeframes (LTF / intrabar).
When set to "Auto," it selects the optimal lower timeframe based on chart resolution.

### Smart fill tracking
Monitors each gap's fill progress in real time with live percentage updates showing
completion status.

### Custom fill logic (four definitions)
Users select how a gap is classified as "filled":
- Any Touch
- Midpoint Reached
- Wick Sweep
- Body Beyond

### Dynamic labels & tooltips
Labels can be toggled on/off; detailed tooltips remain accessible by hovering over
FVG midpoints (persistent info access).

## Creator & categorization
Published by **dgtrd** (a Pine Wizard on TradingView). Open-source. Emphasizes
structural market analysis related to ICT (Inner Circle Trader) methodology, market
structure, and multi-timeframe analysis.

## Disclaimer
Intended for informational and educational purposes only; not financial or trading advice.
