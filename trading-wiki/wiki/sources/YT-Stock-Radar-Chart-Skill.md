---
title: "YouTube — Stock Radar Chart (Claude Skill) for screener.in fundamentals"
category: source
tags: [radar-chart, claude-skill, screener-in, fundamentals, scorecard, portfolio, visualization, groww]
created: 2026-07-25
updated: 2026-07-25
sources: 1
related:
  - concepts/Radar-Chart-Stock-Scoring.md
  - analyses/Radar-Chart-Analyzer-Fit.md
---

# YouTube — Stock Radar Chart (Claude Skill)

## Metadata
- **Type:** YouTube video walkthrough (title / URL / author **not captured** — ingested
  from three screenshots the user shared 2026-07-25). Provenance is the screenshots,
  not the video itself; treat specifics below as read off those frames.
- **Subject:** a personal **Claude Skill** named `stock-radar-chart` that fetches
  Indian-stock fundamentals from **screener.in** and renders a four-axis **radar
  chart** per stock, plus a portfolio-wide score table and a compare overlay.

## Key Takeaways
- **Four scored dimensions, each 0–10:** **Growth · Valuation · Finance · Sentiment**,
  plotted as a radar (spider) chart per stock.
- **Overall = the simple mean of the four axes** (verified against the screenshot
  table: CAMS 8.0/2.0/10.0/7.0 → 6.8; SUPRIYA 7.3/5.0/8.0/7.7 → 7.0; TATACOMM
  2.7/2.0/5.0/7.0 → 4.2).
- **Each axis is itself an average of component metrics scored /10** — e.g. Growth ←
  Sales growth (3Y CAGR), Profit growth (3Y CAGR), EPS growth (YoY); Valuation ← P/E,
  P/B, PEG; Finance ← ROE, ROCE, debt/balance-sheet; Sentiment ← price/momentum context
  (e.g. distance from 52-week high).
- **Auto strength/concern callouts** per stock: one ✅ strength ("Near-zero debt, ROCE
  27.5%, strong balance sheet") and one ⚠ concern ("~31% below 52W high; valuation not
  cheap at P/E 25x").
- **Portfolio flow:** pulls holdings from **Groww MCP** (`get_portfolio_holdings`) or
  takes manually-supplied tickers; **caps at ≤10 stocks** per run for readability; the
  score table is **sorted by invested value**; a **compare overlay** superimposes several
  stocks' radars.
- Packaged as a Claude Skill with `Trigger: Slash command + auto` — fires on "analyse my
  stocks", "create a radar chart", "score my portfolio", "compare on growth/valuation/…".

## Detailed Notes
- **Data source:** screener.in company pages (the same fundamentals surface our own
  `screener_login.py` session capture already reaches). Key metrics shown per stock:
  Sales growth 3Y CAGR, Profit growth 3Y CAGR, EPS growth YoY, P/E, Price/Book, ROE,
  ROCE, debt — each mapped to a 0–10 sub-score, then averaged into its axis.
- **Scoring is band-based** (a raw metric → /10). The exact bands aren't shown, but the
  examples imply higher-is-better for Growth/Finance and cheaper-is-better for Valuation
  (P/E 25.3x → 4/10; P/B 4.36x → 4/10; EPS growth +57.8% → 10/10; ROCE 27.5% → high).
- **Visualization:** a filled radar per stock (Growth top, Valuation right, Finance
  bottom, Sentiment left), a per-stock card with the four sub-scores + strength/concern,
  and a portfolio table + overlay.

## Actionable Insights (for our stack)
- We already fetch most of these fundamentals **login-free via yfinance**
  (`stock_council.fetch_fundamentals`: ROE, OPM, D/E, revenue/earnings growth, P/E, P/B,
  PEG, market cap) and can enrich the **3Y CAGRs + true ROCE** from **screener.in**
  (session capture exists — see [[analyses/PEAD-Scanner-Roadmap]] Phase 5.2).
- Our dashboard already uses **Plotly** (`plotly.graph_objects`), so a radar is a
  `Scatterpolar` trace — **no new dependency**.
- Our **portfolio table** ([portfolio_db.py](tools/portfolio_db.py)) can drive the
  multi-stock radar directly — **no Groww MCP needed** (we have the holdings ourselves).
- Full mapping + a phased plan to add this to the Stock Analyzer: [[analyses/Radar-Chart-Analyzer-Fit]].

## Contradictions with Existing Wiki
- **None substantive — it's complementary.** One naming caution: the radar's "Overall"
  (mean of four *fundamental/sentiment* axes) is **not** our M1 **Overall Rating /100**
  (a weighted blend of *technical* systems — Minervini/TechnoFunda/CANSLIM/EW). If both
  ship, label them distinctly to avoid a third "Overall" collision (cf. the FPV
  naming-collision flag in [[concepts/FPV-Flow-Price-Volume-Ownership]]).

## Pages Updated
- Created [[concepts/Radar-Chart-Stock-Scoring]] (the methodology).
- Created [[analyses/Radar-Chart-Analyzer-Fit]] (grounded fit + phased plan).
