---
title: "Pine Script — Volume-Trend Order Block Engine [BigBeluga]"
category: source
tags: [pine-script, order-block, SMC, volume-profile, supertrend, indicator]
created: 2026-09-01
updated: 2026-09-01
sources: 1
related:
  - concepts/Order-Blocks.md
  - analyses/RSI-Fibo-Entry-Scanner-Roadmap.md
---

# [Pine Script] — Volume-Trend Order Block Engine [BigBeluga]

## Metadata
- **Author:** BigBeluga (TradingView)
- **Platform:** TradingView Pine Script v6
- **Chart:** IFCI Limited · 1D · NSE (screenshot provided)

## Key Takeaways

1. **Buy%/Sell% volume split inside each OB zone** — the window around the pivot
   candle is classified bar-by-bar (close >= open = buy volume, else sell volume);
   the zone is visually split at the ratio line with "Buy X%" / "Sell Y%" labels.
   This is the core new mechanic vs our existing OB overlay.

2. **Custom supertrend as the trend filter** — SMA(high-low, 50) × 3.5 multiplier
   replaces BOS/CHOCH for determining when to place bullish vs bearish OBs. Our
   implementation uses structural breaks instead (stronger signal, already shipped).

3. **Non-overlapping constraint** — a new OB is only placed if it doesn't overlap
   the current active OB. Our version already de-duplicates by (dir, ob_idx).

4. **Retest signals with volume threshold** — crossover/crossunder of the OB
   boundary fires a retest marker only when the original OB's Buy% (for bullish)
   or Sell% (for bearish) exceeds a user-configurable threshold (default 50%).

5. **Color palette** — cyan (#00ffcc) for bullish, magenta (#ff007f) for bearish,
   light grey (#e0e0e0) for text. More visually distinct than the standard
   green/red.

6. **Trend cloud fill** — the supertrend trailing stop line fills to the close
   price with a translucent cloud (80% opacity). We don't port this since we
   already have separate trend overlays.

## Actionable Insights

- **Ported:** Buy%/Sell% volume ratio computation added to
  `detect_order_blocks()` in `scanner_templates.py`; chart overlay updated to
  render the split zone with labels and the BigBeluga color scheme.

- **Not ported (by design):** Custom supertrend trend filter — our BOS/CHOCH
  structural break approach is more aligned with SMC methodology. Supertrend
  can be added as a separate overlay if needed.

- **Not ported (future):** Retest signal arrows with volume-threshold gating.
  Could be added as a chart overlay marker (similar to %R exhaustion arrows).

## Contradictions with Existing Wiki

- None — this enriches rather than contradicts the existing Order Blocks concept
  page. The volume-ratio split is a NEW dimension not previously captured.

## Pages Updated

- `scanner_templates.py` — `detect_order_blocks()` now computes `buy_pct` /
  `sell_pct` per zone via `_buy_sell_ratio()`
- `chart_server.py` — API passes `buy_pct` / `sell_pct` to the frontend
- `chart_dashboard.html` — OB overlay draws split zones with Buy%/Sell% labels
  and BigBeluga-style cyan/magenta colors
