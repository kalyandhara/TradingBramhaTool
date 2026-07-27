---
title: "PEAD — Post-Earnings Announcement Drift"
category: concept
tags: [PEAD, earnings, drift, surprise, SUE, anomaly, swing]
created: 2026-07-23
updated: 2026-07-23
sources: 1
related: [concepts/Pocket-Pivot, concepts/ADX, analyses/PEAD-Scanner-Roadmap, sources/TV-PEAD-Screener-PineScript]
---

# PEAD — Post-Earnings Announcement Drift

## Definition
PEAD is the empirical tendency of a stock's price to keep drifting in the
**direction of an earnings surprise** for days-to-weeks *after* the report — one
of the most durable anomalies in the academic finance literature. A large
positive surprise tends to be followed by continued outperformance; a large
negative surprise by continued underperformance. The market underreacts at the
announcement and prices in the news gradually.

Two ingredients, and only two, define it:
1. **The surprise** — how far actual results beat/missed expectations (the trigger).
2. **The drift** — sustained continuation after the reaction (the tradeable edge).

Everything else (VCP, ADX, ATR breakouts, pocket pivots) is *confirmation*, not PEAD.

## How to Use
Long the strongest positive-surprise names while the post-earnings reaction is
still **holding or extending**; avoid/short the strongest negative surprises.
The window is finite — the drift decays over roughly 1–10 weeks, so **Days Since
D0** (the earnings-reaction day) is itself a signal: earlier = more edge left.

## Measuring the surprise
- **SUE — Standardized Unexpected Earnings** = (actual EPS − expected EPS) / σ.
  - *Analyst-based:* expected = consensus estimate; σ = stdev of recent forecast errors.
  - *Time-series:* expected = EPS 4 quarters ago; σ = stdev of recent YoY changes. **Needs no analyst data — only EPS history.**
- **SURGE** — the same idea on revenue (actual − estimate, z-scored).
- **SUV — Standardized Unexpected Volume** — a volume z-score confirming the
  reaction had institutional participation (right-skewed, so a log variant helps).

## Anchoring the event (D0)
The reaction day "D0" is the bar that actually prices the news. Best practice
([[sources/TV-PEAD-Screener-PineScript]]): take the reported earnings date and
**refine ±1 day** to the bar maximizing `max(volume-z, 0) × range-expansion` —
the volume + range signature of the true reaction, since BMO vs AMC timing shifts
which session gaps.

## Confirmation filters (not PEAD itself)
- **% from D0 High** — drift measured from the earnings-day high (pullback-failure
  convention: strong while price holds ≥ the D0 high).
- **Strong ATR Drift** — `(close − D0 close) / D0 ATR$`; > 1.5 over ≥ 5 days = real drift, not noise.
- **[[concepts/ADX]] / DI** — trend strength + direction on the drift.
- **Institutional accumulation** — CLV (Close Location Value = (close−low)/(high−low)),
  large-block volume, and a 3-tier temporal model (Early D0–D4 / Mid D5–D9 / Late D10+).
- **[[concepts/Pocket-Pivot]]** count since earnings — Morales/Kacher accumulation footprints.

## Common Mistakes
- **Calling a price gap "SUE."** Without an estimate (or at least a time-series
  baseline), a gap is a *proxy*, not a standardized surprise. Label it honestly.
- **Contaminated volume baselines.** The post-earnings bars inflate a trailing
  volume average; anchor "normal" volume to *before* D0.
- **Trading stale drift.** Past ~10 sessions the edge fades; Days-Since-D0 matters.
- **NaN bars slipping through.** Gap/holiday NaN rows bypass numeric gates because
  every NaN comparison is False — drop them first (see [[analyses/PEAD-Scanner-Roadmap]]).

## Related Concepts
- [[concepts/Pocket-Pivot]] · [[concepts/ADX]] · [[concepts/VCP]] · [[concepts/High-Tight-Flag]]

## Examples in This Wiki
- Our NSE "Proxy-PEAD Drift" scanner (`scan_pead`) — Phase 1, price-inferred event.
  Live hits 2026-07-23: HCLTECH, TCS, INFY (Q1 IT-major drifts). See [[analyses/PEAD-Scanner-Roadmap]].

## Sources
- [[sources/TV-PEAD-Screener-PineScript]] — 8-criteria TradingView PEAD screener.
