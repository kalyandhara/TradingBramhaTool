---
title: "Radar Chart → Stock Analyzer Fit (grounded audit + phased plan)"
category: analysis
tags: [radar-chart, roadmap, stock-analyzer, fundamentals, plotly, scorecard, dashboard]
timeframe: milestone-plan
created: 2026-07-25
updated: 2026-07-29
sources: 1
related:
  - analyses/Fundamental-Deep-Dive-Report-Roadmap.md
  - sources/YT-Stock-Radar-Chart-Skill.md
  - concepts/Radar-Chart-Stock-Scoring.md
  - analyses/Dashboard-UI-Roadmap.md
  - analyses/PEAD-Scanner-Roadmap.md
---

# Analysis: Radar Chart → Stock Analyzer Fit

## Thesis
The [[sources/YT-Stock-Radar-Chart-Skill]] radar is a **fundamental scorecard
visualization** (Growth/Valuation/Finance/Sentiment, 0–10, [[concepts/Radar-Chart-Stock-Scoring]]).
Our analyzer is the opposite emphasis — **heavily technical** (Minervini / TechnoFunda /
patterns / Setup Intelligence) with fundamentals *fetched but barely visualized*. So the
radar is **genuinely additive**: it surfaces data we already pull, in a shape we don't
currently draw. **~70% is a data-remap + one Plotly trace; no new dependency, no new
data source for a v1.**

## Current State (grounded audit, 2026-07-25)

| Radar axis | Component metrics | What we already have | Where | Gap |
|---|---|---|---|---|
| **Growth** | Sales 3Y, Profit 3Y, EPS YoY | `revenueGrowth`, `earningsGrowth` (yfinance, ~1yr) | [stock_council.py](tools/stock_council.py) `fetch_fundamentals` | 3Y **CAGRs** need screener.in (yfinance is ~1yr) |
| **Valuation** | P/E, P/B, PEG | `pe`, `pb`, `peg` | `fetch_fundamentals` | ✅ have (PEG sparse for NSE → computed `PE÷growth` fallback, as in Quality-PEAD) |
| **Finance** | ROE, ROCE, Debt | `roe`, `debt_to_equity`, `opm` (+ ROA proxy) | `fetch_fundamentals` | **true ROCE** needs screener.in ([[analyses/PEAD-Scanner-Roadmap]] Phase 5.2 gap) |
| **Sentiment** | price/momentum, 52w position | `rs_pct`, `proximity_high`, `rsi`, trend subscores | `gather_evidence` / `setup_intelligence` | must **define** the composition (which signals, what weight) |
| **Radar viz** | Scatterpolar | **Plotly already a dependency** (`go.Figure`, MACD/TSI plots) | [dashboard_app.py](tools/dashboard_app.py) | ✅ no new dep — `go.Scatterpolar` |
| **Portfolio driver** | holdings list | our **own** portfolio table | [portfolio_db.py](tools/portfolio_db.py) | ✅ no Groww MCP needed |

> [!key-insight] We don't need the Groww MCP or a new library
> The video pulls holdings from Groww MCP and draws with a JS radar; **we already own
> the holdings** (portfolio_db) and **already ship Plotly**. A v1 single-stock radar is
> reachable purely from `fetch_fundamentals` + a `Scatterpolar` trace.

## The gap (what's actually new)
1. **Metric → /10 band scoring**, calibrated to the NSE universe (per-metric bands;
   Valuation inverted). This is the real design work — bad bands = misleading radar.
2. **A defined "Sentiment" axis** — pick its composition from signals we already compute
   (RS% vs Nifty + distance-from-52w-high + RSI/trend is a clean start).
3. **The radar trace + a per-stock card** (four sub-scores + one ✅ strength / one ⚠ concern).
4. **screener.in enrichment** for 3Y CAGRs + true ROCE (only needed to match the video
   exactly; a yfinance-only v1 works with ~1yr growth + ROA-proxy, labelled).

## Evidence For
- **Additive, not duplicative** — our surfaces are technical; this is the fundamental
  half, visualized. Complements M1/Setup Intelligence rather than overlapping.
- **Cheap v1** — reuses `fetch_fundamentals` + Plotly; same "compose what exists" shape as
  the M4 Predictive Analysis page.
- **Portfolio-native** — driving it from our own `portfolio_db` gives the video's
  score-table + compare-overlay for free, on the user's real holdings.

## Evidence Against
- **Band calibration is judgement, not code** — get the /10 bands wrong and users distrust
  the scores (same risk the M1 weights carried). Needs a sensible per-sector default.
- **Two "Overall" scores** — the radar's mean-of-four (fundamental) vs M1's weighted
  technical /100. Must be labelled distinctly or it's a third "Overall" collision (cf.
  [[concepts/FPV-Flow-Price-Volume-Ownership]] FPV flag).
- **Fundamental snapshot ≠ timing** — keep it beside the setup read; don't let a pretty
  radar imply an entry.
- **screener.in dependency is fragile** — the session-capture path has been flaky on this
  machine ([[analyses/PEAD-Scanner-Roadmap]] Phase 5.1 notes); keep ROCE/CAGR optional so
  a v1 never blocks on it.

## Phased plan (for later — not started)
- **RC-1 — Single-stock radar on the Stock Analyzer (yfinance-only).** `radar_score(fundamentals) → {growth, valuation, finance, sentiment, overall, strengths, concerns}` + a `go.Scatterpolar` trace + a per-stock card. Reuses `fetch_fundamentals`; Sentiment from `rs_pct` + 52w-position + RSI. Ships the whole visual with zero new data source. *Highest ROI, lowest risk.*
- **RC-2 — screener.in enrichment.** Add 3Y sales/profit CAGR + true ROCE from the
  screener.in session (rides Phase 5.2 plumbing) to match the video's Growth/Finance
  fidelity; degrade gracefully to yfinance when the session is down.
  > **2026-07-29 — RC-2 may not need screener.in at all.** The
  > [[analyses/Fundamental-Deep-Dive-Report-Roadmap]] audit found yfinance's
  > `income_stmt` / `balance_sheet` / `cashflow` (free, no login, *unused anywhere in the
  > repo*) make 3Y/5Y CAGRs and ROCE (EBIT ÷ (equity+debt)) computable directly. If **FR-1**
  > lands first, RC-2 collapses into "read the new layer" and the flaky session path is
  > only a fallback. Also: RC-1's four axes and FR-2's six donuts **must share one
  > `fundamental_score` module** — two scorers would be two fundamental opinions.
  > **✅ 2026-07-30 — confirmed: RC-2 no longer needs screener.in.** FR-1 shipped
  > ([fundamentals_deep.py](tools/fundamentals_deep.py), `0821fdb`) and
  > `derive_fundamentals()` returns `revenue_cagr_3y` / `profit_cagr_3y` / **`roce`**
  > (+ `roce_prev`) live — measured on ITC 37.54% and TITAN 17.23%. RC-2 is now
  > "read the new layer"; the screener.in path is dead weight for this purpose.
  > Caveat carried forward: yfinance returns 4–5 annual columns for most NSE names, so
  > **5Y CAGRs are usually `None`** — RC-2 must render those axes `DATA N/A`, not 0.
- **RC-3 — Portfolio radar + compare overlay + score table.** Drive from `portfolio_db`
  holdings (sorted by invested value, ≤10), overlay several radars, render the score table
  — the video's portfolio view, on our own holdings, no Groww MCP.
- **RC-4 — Fuse with the existing rating.** Optionally blend the fundamental radar with the
  technical M1 Overall Rating into a single two-lens view on the Predictive Analysis page;
  keep both labelled. Backtest whether the fundamental tilt adds edge (rides the
  [[analyses/Backtest-Harness]]).

## Packaging — DECIDED 2026-07-25: native dashboard feature
User chose **(a) native dashboard feature** — a Streamlit Plotly `Scatterpolar` on the
Stock Analyzer / Predictive Analysis page, reusing our data + Plotly, working offline of
Claude. (Option (b), a Claude Skill mirroring the video, was declined for now — it would
live in Claude and re-fetch rather than reuse our pipeline; revisit only if a
conversational "analyse my stocks" flow is wanted later.)

## Action Taken / Plan
- ✅ Ingested the source + methodology (2026-07-25); this fit-analysis filed. **Nothing
  built** — the user is planning the analyzer feature for later.
- ⏭ When ready: **RC-1** first (single-stock radar, yfinance-only) as the first PR.

## Outcome (fill in later)
- _2026-07-25: ingested & scoped. **Decisions locked:** packaging = **native dashboard
  feature**; **RC-1 (single-stock radar, yfinance-only) is the agreed first PR** but
  deferred — user is planning it for later, nothing built yet. Pick up at RC-1._

## Related Pages
- [[sources/YT-Stock-Radar-Chart-Skill]] · [[concepts/Radar-Chart-Stock-Scoring]] — the source + methodology.
- [[analyses/Setup-Intelligence-Visual-Spec]] — the **other** radar: a *technical* setup-quality radar (VCP/RS/Stage/Volume/Low-risk/Clear-path) for the Setup Intelligence panel. Different data, different purpose — keep the two radars (and their two "Overall" numbers) distinct.
- [[analyses/Dashboard-UI-Roadmap]] — the analyzer this would extend (Phase 2 "features").
- [[analyses/PEAD-Scanner-Roadmap]] — Phase 5.2 screener.in fundamentals plumbing RC-2 rides.
