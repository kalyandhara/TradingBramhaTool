---
title: "Pine Script — Upside Reversal Screener"
category: source
tags: [pine-script, tradingview, tradingview-screener, drop-recovery, reversal]
created: 2026-07-02
updated: 2026-07-02
sources: 1
related:
  - strategies/Drop-Recovery-Reversal-Screen.md
  - strategies/Parabolic-Short-First-Red-Day.md
  - concepts/Stage-Analysis.md
---

# Pine Script — Upside Reversal Screener

## Metadata
- Pine v6, indicator, no overlay-drawing intent — explicitly built for TradingView's native Stock Screener (`isScreenerMode` input, defaults true)
- Ingest trigger: Kalyan pasted the full source directly, continuing the same-session reversal-detection thread (4th script ingested)

## Key Takeaways

- **This is the simplest of the four reversal scripts ingested this session** — no candlestick shapes, no chart-pattern geometry, no oscillator. Just two thresholds: drop % (or ATR-multiple) from a recent high, then recovery % of that drop reclaimed. Full write-up in the new [[strategies/Drop-Recovery-Reversal-Screen]] strategy page.
- **Genuinely new distribution mechanism, not just new logic**: this script's plot outputs (Open/High/Low/Close/Change%/Drop%/Recovery%/Reversed flag) aren't for visual chart labels — `isScreenerMode` suppresses the on-chart triangle entirely and instead emits raw numeric columns meant to be added to **TradingView's own Stock Screener** as custom columns, then filtered natively (e.g. `Reversed == 1`) across the whole market. That's a genuinely different "large scale" answer than anything built or discussed this session (Chartink scan clauses, screener.in queries, Python bulk-fetch scanners) — it runs inside TradingView itself with no external plumbing, though custom-script screener columns are typically a paid TradingView tier feature, not confirmed available on Kalyan's plan.
- **A likely implementation issue worth flagging, not silently trusting**: the `highBeforeLow` calculation walks back up to 500 bars but only accumulates `math.max(highBeforeLow, high[i])` while `dayofmonth(time[i]) != dayofmonth(time)` (daily) / `weekofyear(time[i]) != weekofyear(time)` (weekly) stays false — i.e. while bar `i` is still in "the same period" as the current bar. On a **Daily** chart, consecutive daily bars are on different calendar days almost by definition, so this break condition triggers immediately at `i=1`, and the loop contributes **zero** iterations. Same for **Weekly** (consecutive weekly bars are, by definition, different `weekofyear` values). The runtime guard forces the script to run on exactly these two timeframes — the ones where, on this reading, the loop appears to do nothing. If that's right, `highBeforeLow` collapses to just `math.max(close[1], open)` (the line immediately above the loop) — "yesterday's close vs. today's open," not a meaningful recent swing high. This reads like leftover logic from an intraday-session-aggregation version (grouping multiple intraday bars into one daily/weekly "session"), left in after the script was restricted to D/W-only. **Not verified against a live TradingView run — flagged as a strong static-reading concern, not a confirmed bug.** Worth testing directly before relying on the "drop %" number meaning what its name implies.

## Detailed Notes

The recovery condition is `recoveryAmt >= dropAmt * minRecovery/100` — a fraction of the drop's *dollar/point amount*, not a fraction of the original high. So "60% recovery" means: if a stock dropped from 100 to 90 (10-point drop), it needs to close at ≥96 (60% of the 10-point drop reclaimed) — a fixed anchor to the specific decline being measured, not a generic "back above X% of the old high" rule.

`useATR` toggles between a flat percentage drop threshold and an ATR-normalized one (`dropAmt / atr(21) >= atrMultiplierD`, default 2.0) — a sensible way to make the drop threshold comparable across low-volatility and high-volatility names, similar in spirit to how [[concepts/Percent-R-Trend-Exhaustion]] and [[sources/AGPro-Reversal-Pattern-Quality-Scanner-Pine]] both normalize their own thresholds by ATR rather than raw price.

`requireLowerLow` (off by default) adds a genuine-new-low requirement (`sessionLowPrice < previousLow`) — cheap insurance against flagging a shallow, non-notable dip as a "drop."

## Actionable Insights

- **Investigate whether TradingView's native Stock Screener actually supports this script as a screenable column on Kalyan's plan** — if so, this is a zero-infrastructure way to run a whole-market drop-recovery scan without touching Chartink, screener.in, or this project's own Python pipeline at all. Worth a direct check before assuming it needs porting.
- **If it does need porting to Python** (e.g. to combine with the other 3 reversal signals from this thread), fix the `highBeforeLow` definition rather than replicating it as-is — use an actual N-bar rolling high (e.g. 10-20 day lookback), not the apparently-collapsed "yesterday's close vs. today's open."
- **This is the cheapest possible member of the Early Reversal Detector candidate set** — worth including as a fast pre-filter (drop % + recovery % on raw OHLCV, no pattern computation at all) ahead of the more expensive candlestick/chart-pattern/oscillator checks, rather than as a replacement for them.

## Contradictions with Existing Wiki

None on strategy content. The flagged `highBeforeLow` concern is an internal-consistency question about the script itself (does its lookback logic do what its own naming implies), not a conflict with anything already documented here.

## Pages Updated

- strategies/Drop-Recovery-Reversal-Screen.md — new strategy page, this script is its primary source
