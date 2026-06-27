---
title: "Dashboard UX, Alert Taxonomy & Daily Operational Workflow"
category: analysis
tags: [dashboard, ui-ux, alerts, workflow, streamlit, requirements]
created: 2026-06-25
updated: 2026-06-26
related: [sources/Minervini-Market360-Dashboard-Video, analyses/VCPBot-Architecture, analyses/Kalyan-Trading-Philosophy, strategies/PMax-Confluence-Strategy]
---

# Dashboard UX, Alert Taxonomy & Daily Operational Workflow

> Distilled from [[sources/Minervini-Market360-Dashboard-Video]] — the operational/UX portions worth keeping, independent of that source's VCP/RS content (superseded elsewhere) and its from-scratch tech stack (see that page's Contradictions section for the open architecture-fork decision).

## Purpose
A requirements checklist for the next iteration of `tools/dashboard_app.py` (Streamlit, built 2026-06-24) — what a complete trading dashboard's surface area looks like, independent of which stack renders it.

## Dashboard Layout Spec (6 sections)
1. **Overview/Summary** — market status (index price/change/volume), portfolio value + P&L, % capital at risk, alert ticker
2. **Stock Screener** — sortable table: symbol, price, 52w hi/lo, RS rating, MA50/150/200, volume trend, pattern status, earnings growth%; bulk add-to-watchlist
3. **Charts/Technical Analysis** — candlestick + MA overlays + volume + pattern/consolidation zones shaded + entry/exit annotations; timeframe selector
4. **Watchlist/Alert Management** — live price monitoring, custom alert thresholds, one-click add-to-portfolio
5. **Portfolio/Position Tracker** — entry price, current price, unrealized P&L, stop-loss level, target price, trade history/journal
6. **Alerts/Notifications** — consolidated feed across all 5 alert categories below

**Status against `tools/dashboard_app.py` (updated 2026-06-26):** All 6 sections now exist and are enhanced. Sections 2 (Screener) and 3 (Stock Analyzer chart) existed as of 2026-06-24; sections 1 (Overview panel — Nifty status, portfolio P&L framed against Nifty's day change, % capital at risk, triggered-alert count, all rendered above the tabs per the Lollypop "always visible" UX research), 4 (Watchlist tab — live price/day-change/Minervini+TechnoFunda mini-score per symbol), 5 (Portfolio tab — add/close positions, live P&L + R-multiple, closed-position trade journal), and 6 (Alerts tab — structured category/metric/operator/threshold alerts, checked on-demand each refresh, no eval()) were added 2026-06-25, backed by a new local SQLite file (`tools/trading_bramha.db` via `tools/portfolio_db.py`) rather than the source's proposed PostgreSQL. The chained sector-rotation output (Other Screeners tab) remains a 7th capability this source doesn't anticipate at all. Enhancements added 2026-06-26: **Section 2** — bulk add-to-watchlist (multiselect → one button). **Section 3** — chart lookback selector (90/180/300/365 days), "Add to Watchlist" button after analysis. **Section 4** — quick-add-to-portfolio expander (current price pre-filled, quantity + optional stop entry). **Overview area** — Daily Workflow (IST) expander showing the 4-slot routine above the tabs.

## Alert Taxonomy (5 categories)
| Category | Trigger | Coverage in dashboard_app.py (Alerts tab, 2026-06-25) |
|---|---|---|
| Price | User-set threshold vs `close`, any operator | Implemented — checked against `cached_fetch_ohlcv` on each refresh |
| Pattern | `total_score` (Minervini+TechnoFunda) threshold, or `wave_pos` equality | Implemented — reuses the same scoring functions as the Screener/Stock Analyzer tabs |
| Volume | `volume_ratio` (today vs 20d avg) threshold | Implemented |
| Earnings | Within 7 days of a user-entered `target_date` | Implemented as a manual-reminder date, not an auto-fetched earnings calendar (no such data source exists in this project) |
| Performance | `portfolio_pl_pct` threshold | Implemented — reads live `compute_portfolio_summary()` over open positions |

All 5 categories are now checked on-demand (no background process, no push notifications — structured comparisons only, no `eval()`) rather than aspirational. `pmax.pine`'s price-cross `alertcondition`s remain a separate, TradingView-side mechanism and are not consolidated with this dashboard's alerts.

## Daily Operational Workflow (IST)
| Time | Action |
|---|---|
| 8:30 AM | Review news/earnings calendar, check overnight alerts, build the day's watchlist |
| 9:15 AM | Monitor index + existing portfolio at open; watch for new pattern breakouts |
| 9:15 AM – 3:30 PM | Execute on confirmed breakouts; manage stops/targets; monitor live alerts |
| 3:30 PM onward | Review the day's fills; update portfolio; mark next day's candidates |

Complements [[analyses/Kalyan-Trading-Philosophy]] (which is mindset/rules-level — "don't react," cash discipline, position caps) with a concrete time-boxed routine. Also aligns with the existing screener's scheduled run time (`tools/install_task.ps1` fires at 4:05 PM, i.e. just after this workflow's post-market window opens) — the daily routine and the automation schedule are already in sync without needing changes.

## Open Decision — Resolved 2026-06-25
Built as additions to the existing Streamlit `tools/dashboard_app.py` (new tabs + a local SQLite file), not the React/FastAPI/PostgreSQL rebuild from [[sources/Minervini-Market360-Dashboard-Video]]. No need for multi-device access, sub-second WebSocket pushes, or broker order placement has emerged — the rebuild path remains available if one does, but is no longer the default assumption for this project.

## Related
- [[sources/Minervini-Market360-Dashboard-Video]] — full source ingest, including what was explicitly rejected (VCP detection code, RS Rating formula)
- [[analyses/VCPBot-Architecture]] — the existing full-pipeline architecture this dashboard sits in front of
- [[analyses/Kalyan-Trading-Philosophy]] — the mindset-level rules this workflow operationalizes
- [[strategies/PMax-Confluence-Strategy]] — existing alert/decision-matrix pattern (TradingView-side) that the Pattern/Volume alert categories above should eventually mirror in the dashboard
