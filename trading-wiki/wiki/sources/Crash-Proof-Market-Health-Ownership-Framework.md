---
title: "Framework — Crash-Proof Market-Health + Ownership-Flow Decision System"
category: source
tags: [framework, market-health, ownership-flow, fpv, shareholding, stage-analysis, minervini, decision-system, infographic]
created: 2026-07-21
updated: 2026-07-21
sources: 1
related:
  - strategies/Crash-Proof-3-Filter-System.md
  - concepts/FPV-Flow-Price-Volume-Ownership.md
  - concepts/Stage-Analysis.md
  - strategies/Minervini-SEPA.md
  - analyses/Decision-Support-Gating-Roadmap.md
---

# Source — Crash-Proof Market-Health + Ownership-Flow Framework

## Metadata
- **Type:** Written decision framework, pasted by the user 2026-07-21, synthesised from a trading infographic ("crash-proof system" flow) plus a live read of the dashboard's shareholding tab for **MCX** (Multi Commodity Exchange, NSE) used as the worked example.
- **Author bias:** Trend-following / Minervini-Weinstein school. Bullish-structural on the MCX example, but explicitly gated on market health.
- **Status:** Educational framework, not a registered-advisor call. Every rule is a filter, not a signal to buy.

## Key Takeaways
1. **Market health is the master switch.** Five conditions (Nifty > 50 EMA, positive breadth, breakouts working, leaders strong, low volatility). If **2 or more fail → no trades**, however good a single stock looks. Claimed to prevent "80% of unnecessary losses."
2. **Shareholding pattern is a structural filter**, read as a smart-money rotation: FII increasing = absorption, MF decreasing = supply, retail decreasing = less noise, DII stable = trend stability. Bullish structurally — **but only when market health supports it**.
3. **The power is in the combination**, not either filter alone. Market-weak + FII-increasing = accumulate the watchlist, do not buy yet. Market-strong + FII-increasing = high-conviction breakouts allowed. Market-weak + MF-selling = avoid entirely.
4. **Stage analysis governs the individual name.** Below 50 EMA → no trades; base-building while FII accumulate → watch; Stage 2 (above 50 EMA) → buy breakouts only. This is [[concepts/Stage-Analysis]] applied to the example.
5. **FPV (Flow of Price, Volume, Ownership) is the timing confirmation** — the four price/volume/ownership combinations that time the entry once the two structural filters agree. See [[concepts/FPV-Flow-Price-Volume-Ownership]].
6. **The system = three filters that must all align:** Market filter + Stock filter + Ownership filter. Trade only on full alignment.

## Detailed Notes

### Filter A — Market health (the market filter)
- Nifty above 50 EMA
- Breadth positive
- Breakouts working (recent breakouts holding, not failing)
- Leaders strong (leadership names trending, not breaking down)
- Volatility low
- **Rule:** ≥2 fail → stand down for the day.

### Filter B — Stock health (stage filter)
- Above 50 EMA · strong volume · confirmed Stage 2 · leaders returning.

### Filter C — Ownership flow (the shareholding filter)
- FII increasing · MF stable or increasing · retail decreasing · DII stable.

### The combination matrix (the actionable core)
| Market | Ownership (FII) | Action |
|--------|-----------------|--------|
| Weak | FII increasing | **Accumulate watchlist, don't buy yet** (FIIs buy early in corrections) |
| Strong | FII increasing | **High-conviction breakout trades allowed** |
| Weak | MF selling | **Avoid fresh trades** (MF selling in weak markets → deeper corrections) |

### Crash-proof stage flow (applied to a name)
`Market weakens → breakdown → go to cash → wait → new Stage 2 begins → attack.`
Applied to MCX: below 50 EMA → no trades; breakdown with MF selling → stay out; base while FII accumulate → watch closely; Stage 2 (above 50 EMA) → buy breakouts only.

## Actionable Insights
- The **2-of-5 market-health kill switch** is the single highest-value rule and is close to what [market_verdict.py](tools/market_verdict.py) already computes ("2+ caution flags → STAND DOWN").
- **Ownership flow needs the full FII/DII/MF/retail split**, not just FII — the current [nse_shareholding_fetch.py](tools/nse_shareholding_fetch.py) fetches FII change only.
- The framework is a **gate stack**, not a scorer: each filter can only *veto*. That matches the dashboard's existing verdict ladder better than a weighted score would.

## Contradictions with Existing Wiki
- **None on substance.** Reinforces [[concepts/Stage-Analysis]] (buy only in Stage 2) and [[strategies/Minervini-SEPA]] (market-regime filter first).
- **Naming collision on "FPV".** In this session the acronym was also used for the chart **Fibonacci + confluence overlay** (price projection + volume profile). That feature does **not** include ownership data. See the flag in [[concepts/FPV-Flow-Price-Volume-Ownership]] — the two must not be conflated.

## Pages Created
- [[concepts/FPV-Flow-Price-Volume-Ownership]]
- [[strategies/Crash-Proof-3-Filter-System]]
- [[analyses/Decision-Support-Gating-Roadmap]]

## Pages Updated
- [[analyses/Dashboard-UI-Roadmap]] (Phase 2 pointer), [[index]], [[log]]
