---
title: "Pine Script — PEAD Screener (8-criteria, TradingView v6)"
category: source
tags: [source, pinescript, tradingview, PEAD, earnings, drift, scanner]
created: 2026-07-23
updated: 2026-07-23
sources: 1
related: [concepts/PEAD, concepts/Pocket-Pivot, analyses/PEAD-Scanner-Roadmap, concepts/ADX]
---

# Source: Pine Script — PEAD Screener (8-criteria)

## Metadata
- Type: TradingView Pine v6 `indicator` (Pine Screener–compatible), daily-only.
- Author: user-supplied; ingested 2026-07-23. Raw copy: [[raw/TV-PEAD-Screener-pine-2026-07-23]].
- Purpose: screen for Post-Earnings Announcement Drift ([[concepts/PEAD]]) candidates via an 8-criteria dashboard + 9-chip banner.

## Key Takeaways (3–7 bullets)
1. **It computes *true* SUE and revenue surprise** using TradingView's `request.earnings(…, earnings.estimate)` and `request.financial(…, "SALES_ESTIMATES")`. Analyst consensus estimates ARE reachable inside Pine — see Contradictions below.
2. **Two SUE methods**, one estimate-free: *Analyst-based* (actual−estimate, z-scored over a rolling forecast-error window) and *Time-series* (actual − actual 4 quarters ago, z-scored) — the latter needs only EPS history, no analyst data.
3. **SUV — Standardized Unexpected Volume**: a proper volume z-score (raw or log), anti-leaked with a `volume[1]` baseline, 0.2σ floor, `[-10, 20]` clamp — far more principled than a bare relative-volume ratio.
4. **D0 anchoring is refined, not naïve**: it takes TradingView's earnings-bar mark and refines ±1 day to the bar maximizing `max(volZ,0) × range-expansion` — the true reaction bar, not just the calendar date.
5. **A temporal institutional-accumulation model**: three tiers (Early D0–D4 / Mid D5–D9 / Late D10+) built from CLV, large-block volume, drift, up-day consistency, and a *pre-D0-anchored* volume ratio. Several thresholds are honestly flagged "directional convention only, not statistically calibrated."
6. **Pocket Pivots** (Morales/Kacher — [[concepts/Pocket-Pivot]]) counted since earnings, with MA-proximity / extension / trend filters.
7. **Drift is anchored to the earnings-day HIGH** (pullback-failure convention), and separately as **ATR-normalized drift** `(close − D0 close) / D0 ATR$ > 1.5`.

## Detailed Notes
The 8 criteria: **SUE** · **SURGE** (revenue z) · **SUV** (volume z) · **% from D0 High** · **# Pocket Pivots** · **ADX/DI** · **Institutional Buying (3-tier)** · **Strong ATR Drift**. All eight are surfaced as `display.data_window` plot columns (so Pine Screener can sort/filter) plus a 9-chip banner (adds Days-Since-D0). Two `alertcondition`s double as boolean Screener filters.

Engineering craft worth stealing: daily-only `runtime.error` guard; `isNum_d0(x) = not na(x) and not (x != x)` NaN check (the exact NaN-slips-through-comparisons bug class we hit in `scan_pead`); `inRange()` bounding every historical subscript; anti-leak baselines (`volume[1]`, `rev_estimate[1]`); the **pre-D0 volume baseline** insight (`vol20[reactionIdx+1]`, because the live `vol20` is contaminated by post-earnings bars); sigma floors and output clamps; `max_bars_back` sized to the deepest subscript.

## Actionable Insights (what to absorb — see [[analyses/PEAD-Scanner-Roadmap]])
- **Time-series SUE is adoptable in our Python pipeline today** — z-score of YoY EPS change from EPS history. Upgrades our Phase-1 "gap only" to a real surprise proxy without needing analyst estimates.
- **Upgrade `vol_x50d` → a SUV z-score** (raw + log option) with anti-leak baseline and clamp.
- **Refine D0 detection** with the `volZ × range-expansion` argmax once we have earnings dates (Phase 2).
- **Add CLV + the 3-tier institutional model** as a later phase; add **Pocket Pivot** as a detector.
- **ATR-drift-from-D0** is a cleaner score than our event-bar `react/ATR`; and **ADX** confirms the planned Phase-3 filter.

## Contradictions with Existing Wiki
- **CORRECTION to my 2026-07-23 assessment** in [[analyses/PEAD-Scanner-Roadmap]] that "NSE has no free consensus estimate." That is true of **our Python data sources** (yfinance/screener.in — screener.in returns nothing for "surprise"), but **NOT of the TradingView platform**: Pine's `request.earnings(…, earnings.estimate)` and `request.financial(…, "SALES_ESTIMATES")` expose consensus estimates. So a **TradingView-hosted** PEAD screener CAN compute true SUE/SURGE — *subject to TV's estimate coverage for NSE names, which is unverified and often sparse for Indian mid/small-caps.* Net: the "no true SUE" limit is a property of our pipeline, not of the data universe. Roadmap updated to say so.

## Pages Updated
- Created: [[concepts/PEAD]], [[concepts/Pocket-Pivot]], [[raw/TV-PEAD-Screener-pine-2026-07-23]]
- Updated: [[analyses/PEAD-Scanner-Roadmap]] (absorbed techniques + contradiction), [[index]], [[log]]
