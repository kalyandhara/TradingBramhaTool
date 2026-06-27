---
title: "YouTube — Built My Own Minervini Market 360 Dashboard for Indian Markets using AI"
category: source
tags: [minervini, vcp, dashboard, ui-ux, alerts, react, fastapi, postgresql, indian-markets]
created: 2026-06-25
updated: 2026-06-25
sources: 1
related: [concepts/VCP, strategies/VCPBot-Trend-Template, strategies/Minervini-SEPA, concepts/Mansfield-RS, analyses/VCPBot-Architecture, analyses/Kalyan-Trading-Philosophy]
---

# YouTube — Built My Own Minervini Market 360 Dashboard for Indian Markets using AI

## Metadata
- **Source type:** YouTube video, summarized into 3 AI-generated implementation docs (MINERVINI_DASHBOARD_GUIDE.md, TECHNICAL_IMPLEMENTATION.md, QUICK_START.md) dropped at the repo root (`Trading_Bramha/`) rather than in the wiki structure
- **Cited sources inside those docs:** Minervini Markets 360 (official), VCP Trading Guide (TradingSim), Mark Minervini VCP Criteria (Finermarketpoints), Trading Dashboard Design (Medium), Stock Market Dashboard Templates (TailAdmin)
- **Date ingested:** 2026-06-25
- **Disposition:** Folded into this single source page + one new analysis page (see Pages Updated). The 3 original root-level files are superseded by this ingest and can be deleted once reviewed — their VCP/RS content is either already covered (more rigorously) elsewhere in this wiki, or factually wrong (see Contradictions).

## Key Takeaways
- A generic, AI-synthesized "rebuild Minervini Market 360 for India" plan: VCP detection + Minervini Trend Template + a from-scratch React/FastAPI/PostgreSQL/Redis/WebSocket dashboard, phased over 12 weeks.
- The **VCP and Trend Template descriptions are simplified/generic** compared to what's already in this wiki — see Contradictions. Not worth replacing existing pages.
- The genuinely new, reusable material is **operational/UX**, not strategy logic: a 6-section dashboard layout spec, a 5-category alert taxonomy, and a time-boxed IST daily workflow. Captured in the new [[analyses/Dashboard-UX-Operational-Requirements]] page.
- **This source assumes building from zero** (PostgreSQL, FastAPI, React, WebSocket, Redis) with no awareness of this project's existing `tools/` pipeline (`screener_pipeline.py` already scores Minervini Trend Template + TechnoFunda + Elliott Wave daily; `tools/dashboard_app.py`, a Streamlit dashboard, was built and verified working the day before this ingest). Treat as a **reference for requirements, not an architecture to adopt** — see Contradictions.

## Detailed Notes

### VCP Criteria (as stated in this source)
A 7-point list: progressive contractions (≥3, each 20–30% smaller), volume dry-up, clear pivot point, Stage 2 confirmation, RS Rating ≥70, earnings growth ≥20%, bullish market environment. Entry at pivot break + volume; stop below prior contraction low (3–5%); trail stop on the way up.

This is a coarser version of what [[concepts/VCP]] already documents in detail: the 3-tier algorithmic detection (macro LSH → contraction tightening with a regression-slope test → micro pivot/stop), the `WW depth/final T_count` footprint notation, and specific hard-reject thresholds (stop >7% of pivot, compression ratio ≤0.85). No new VCP mechanics here worth merging.

### Dashboard UI/UX Spec (genuinely new — not previously in this wiki)
6 sections: Overview/Summary (market status, portfolio P&L, risk %), Stock Screener (sortable table: price, 52w hi/lo, RS rating, MAs, volume trend, VCP status, earnings growth%), Charts (candlestick + MA overlays + VCP shaded zones + entry/exit annotations), Watchlist/Alerts, Portfolio/Position Tracker (entry/current/P&L/stop/target + trade journal), and a dedicated Alerts/Notifications panel. Design notes: dark theme, responsive layout, color-coded gain/loss, one-click actions, keyboard shortcuts.

### Alert Taxonomy (genuinely new)
5 categories worth distinguishing explicitly: **Price** (±2–5% from key levels), **Pattern** (VCP completes / pivot breaks / pattern collapses), **Volume** (≥2× average), **News/Earnings** (1 week pre-announcement), **Performance** (portfolio milestones). This is a more complete taxonomy than this wiki currently has anywhere — existing alert logic (e.g. `tools/screener_pipeline.py`, `pmax.pine`'s `alertcondition` blocks) only covers price/pattern/signal triggers, not the full 5-category split.

### Daily Operational Workflow (IST) (genuinely new, complements but doesn't replace Kalyan-Trading-Philosophy)
Pre-market (8:30 AM): news/earnings calendar, review overnight alerts, build watchlist. Market open (9:15 AM): monitor index + portfolio, watch for new VCP breakouts. During session (9:15–3:30): execute on breakouts, manage stops/targets, monitor alerts. Post-market (3:30 PM+): review fills, update portfolio, mark VCP candidates for next day.

### RS Rating Formula (flagged as wrong — see Contradictions)
States: `RS Rating = (52w high − current price) / (52w high − 52w low) × 100`. This is **not** how relative strength works in any methodology already in this wiki — it doesn't reference a benchmark at all, just measures a stock's own position within its own 52-week range (closer to a Stochastic %K computation, inverted). It would rank a stock highest when it's furthest *below* its own high, the opposite of "relative strength."

### Proposed Tech Stack
React/Vue/Angular frontend (TradingView Lightweight Charts or Plotly), FastAPI/Express backend, PostgreSQL + TimescaleDB/InfluxDB for time-series, Redis/RabbitMQ for streaming, WebSocket for real-time push. 12-week phased plan: Weeks 1–4 MVP (screener + portfolio tracker), Weeks 5–8 real-time + backtesting, Weeks 9–12 AI pattern recognition + broker integration.

## Actionable Insights
- Adopt the **6-section layout spec, alert taxonomy, and daily workflow checklist** as requirements for the next iteration of `tools/dashboard_app.py` — captured in [[analyses/Dashboard-UX-Operational-Requirements]] rather than duplicated here.
- Do **not** adopt the VCP detection code or RS Rating formula from this source — both are inferior to or contradict what's already documented and implemented.
- Do **not** start a from-scratch React/FastAPI/PostgreSQL rebuild without an explicit decision to abandon the working Streamlit dashboard — see Contradictions below.

## Contradictions with Existing Wiki

1. **RS Rating formula is wrong.** This source's formula (`(52w_high − price) / (52w_high − 52w_low) × 100`) doesn't compare the stock to any benchmark, unlike both [[concepts/Mansfield-RS]] (`(rsRatio / SMA(rsRatio,52) − 1) × 100`, benchmark-relative) and the [[strategies/VCPBot-Trend-Template]] RS Rank (`0.4×ROC63 + 0.2×ROC126 + 0.2×ROC189 + 0.2×ROC252`, then percentile-ranked across the universe). Flagged in [[concepts/Mansfield-RS]] as a non-standard formula to avoid.
2. **VCP criteria are a simplified restatement**, already superseded in depth by [[concepts/VCP]]'s 3-tier algorithmic detection and Minervini's original footprint notation (both sourced from the actual VCPBot implementation and the SEPA book, not a video summary).
3. **Architecture fork — the big one.** This source's entire premise is building a new system from zero (PostgreSQL + FastAPI + React + Redis + WebSocket, 12-week plan). As of this ingest, `tools/screener_pipeline.py` already runs Minervini Trend Template + TechnoFunda + Elliott Wave scoring daily over ~200-250 NSE stocks, and `tools/dashboard_app.py` (Streamlit) already provides a manual-trigger screener UI + per-stock candlestick/EW chart + chained sector-rotation pipeline — built and verified working one day before this ingest. Following QUICK_START.md literally would mean discarding working infrastructure to rebuild a heavier-weight equivalent. **Not resolved here** — this is a decision for the user: extend the existing Streamlit app with this source's UX/alert/workflow requirements (cheap, additive), or deliberately fork to the React/FastAPI stack for reasons not yet stated (e.g. multi-user access, mobile app, broker order execution — none of which the Streamlit app currently needs).

## Pages Updated
- Created: sources/Minervini-Market360-Dashboard-Video.md (this page), analyses/Dashboard-UX-Operational-Requirements.md
- Updated: concepts/Mansfield-RS.md (flagged non-standard RS Rating formula)
