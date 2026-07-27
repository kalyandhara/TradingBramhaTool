---
title: "Obsidian note — Falling-Wedge Breakout Screener (build prompt + UI mockups)"
category: source
tags: [falling-wedge, screener, prompt, full-stack, fastapi, react, scanner, mockup]
created: 2026-07-25
updated: 2026-07-25
sources: 1
related:
  - concepts/Falling-Wedge.md
  - analyses/Falling-Wedge-Scanner-Fit.md
---

# Obsidian note — Falling-Wedge Breakout Screener

## Metadata
- **Source:** Obsidian note "Falling wedge breakout scanner" in the **Trading_Bramha**
  vault (`obsidian://open?vault=Trading_Bramha&file=Falling%20wedge%20breakout%20scanner`),
  ingested 2026-07-25. Contains a detailed **LLM build-prompt** for a full-stack
  falling-wedge screener **+ two UI screenshots** of the target app.
- **Author:** user-curated (the prompt is written *to* an LLM to generate the app).

## Key Takeaways
- A precise, self-contained **falling-wedge detection algorithm** (swings → trendline
  regression → geometric validation → 0–100 confidence → breakout state) — captured as
  [[concepts/Falling-Wedge]].
- The prompt asks for a **whole separate full-stack web app**: Python 3.11 + **FastAPI** +
  **APScheduler** + **yfinance** backend; **React + Vite + Tailwind + TradingView
  Lightweight-Charts** frontend; **Docker-Compose**, **GitHub Actions CI**, tests, linting.
- Universe: **S&P 500** (scraped from Wikipedia, CSV fallback) + **NIFTY 100** (bundled
  CSV, `.NS`); timeframes **15m / 1h / 1d**; scan every **30 min**; 120 candles pulled,
  last **60** used for detection.
- UI (from the screenshots): a **results table** — Ticker · Market · Timeframe ·
  **Confidence** (red→green bar) · **Breakout** badge (none / Forming / Breakout) — and a
  **chart modal** drawing the two green trendlines + a filled wedge, with stat tiles
  **Confidence · Containment% · Convergence% · Pivots (H/L) · volume↓**.

## Detailed Notes
- **Algorithm** — see [[concepts/Falling-Wedge]] §Detection Algorithm for the full spec
  (pivot look-back 1; last 5–10 swings; regress last 2–3 highs/lows; both slopes negative
  + upper steeper + converging + ≥2 touches/side; confidence from touch-ratio /
  convergence / steepness / cleanliness / recency; breakout confirmed >upper, pre-breakout
  within 0.5%).
- **Screenshot 1 (results table):** header "Falling-Wedge Breakout Screener", NIFTY 100 /
  1D, "6 matches" — TATACONSUM.NS 93 Breakout, WIPRO.NS 89 Breakout, NMDC.NS 85 Forming,
  TATASTEEL.NS 84 Forming, COALINDIA.NS 80 Forming, NTPC.NS 67 Breakout.
- **Screenshot 2 (chart modal):** TATACONSUM.NS 1D with the falling wedge overlaid;
  Confidence 93 · Containment 98% · Convergence 93% · Pivots (H/L) 5/6 · vol↓.

## Actionable Insights (for our stack)
- **Take the algorithm, not the app.** The detection spec is the value; the FastAPI /
  React / Docker / CI scaffolding **duplicates infrastructure we already run** (Streamlit
  dashboard, `chart_server`, yfinance fetch, the `SCANNERS` registry that already feeds
  both the Scanner Hub and Opportunity Hub, an existing 4:05 PM scheduled batch, and a
  chart overlay layer that already draws trendlines/VCP-zones/harmonics).
- The right shape for us is a single **`scan_falling_wedge(df)`** function in
  [scanner_templates.py](tools/scanner_templates.py) + a chart overlay — reusing our
  existing swing-pivot detection (`detect_bos_choch`) and linear-fit trendline code
  (`scan_rounding_bottom` uses `np.polyfit`; `/api/trendlines` exists). Full mapping +
  phased plan: [[analyses/Falling-Wedge-Scanner-Fit]].

## Contradictions with Existing Wiki
- **No conceptual conflict.** The only tension is **architectural redundancy** — building
  the prompt's standalone full-stack app would fork a parallel screener/scheduler/chart
  stack next to the one we already maintain. Flagged, not silently followed.

## Pages Updated
- Created [[concepts/Falling-Wedge]] (pattern + algorithm) and
  [[analyses/Falling-Wedge-Scanner-Fit]] (fit + phased plan).
