---
title: "Web App — Flagium AI: structural risk attribution (MAZDOCK)"
category: source
tags: [source, web-app, forensic-accounting, risk-score, red-flags, attribution, nse, earnings-quality]
created: 2026-10-27
updated: 2026-10-27
sources: 1
related: [analyses/Open-Backlog, sources/Web-eVector-Event-Vector-Markets, analyses/Fundamental-Deep-Dive-Report-Roadmap]
---

# Web App — Flagium AI: structural risk attribution (MAZDOCK)

## Metadata

- **Page:** https://flagiumai.com/company/MAZDOCK/attribution, read 2026-10-27, **logged out**.
- **What it is:** an NSE/BSE forensic-accounting risk app. It turns XBRL filings into numbered
  "forensic signals" (F5, F11, F13, F15, M4…), a 0–100 composite risk score, and a
  quarter-on-quarter attribution of what moved that score.
- **How it was read:**
  - the page text;
  - the network log;
  - the **shapes** (field names and counts) of the public JSON endpoints.
- **Bias:** neutral on the stock. It calls itself "algorithmic quantitative observations … not
  allegations … or investment recommendations".

> [!warning] Paywall leak (not used)
> `GET /api/companies/<SYM>` returns **all 10** of MAZDOCK's flags, with full evidence
> dossiers, to a logged-out caller. The UI shows only 2 and gates the other 8. This note uses
> only what the page shows plus field names. The gated content was not read.

## Key takeaways

1. **A risk score is useful because it can be explained.** The 20/100 score is decomposed every
   quarter as a waterfall:
   - prior base **15**;
   - **+27.1** from new risks (3);
   - **+2** escalated;
   - **0** compound interaction;
   - **−13** resolved;
   - **+0.9** pillar cap;
   - **−12** "temporal drift smoother";
   - terminal score **20**.

   Every point is accounted for.
2. **Each flag is an object with a lifecycle, not a tick-box.** Fields:
   - code, name, pillar, severity, momentum (accelerating), "active for N quarters";
   - lifecycle new / escalated / persistent / resolved / improved;
   - the empirical trigger with its numbers and a threshold rule (e.g. "Other Income/PBT ≥ 30 %");
   - a 12-quarter baseline (e.g. "12-qtr median EBITDA margin 24.6 %");
   - what to watch next quarter.
   
   Resolved flags stay visible: "Receivables-Revenue Divergence ✓ (Q1-FY27)".
3. **Six pillars with peer percentiles.** Solvency, Governance, Earnings Quality, Balance Sheet
   Stress, Competitive Position and Growth Sustainability. Each is scored, given a percentile and
   compared with the sector median (Capital Goods, n = 274). The composite is ranked against
   peers: 53rd percentile, sector median 17.
4. **12-quarter structural history.** The page shows the score path, with the largest jump
   marked as the **structural break** (Q2 FY25, +14) and given its own narrative.
5. **Forensic cash and working-capital monitor**, ten years deep:
   - CFO/PAT, CFO/EBITDA;
   - accrual ratio (accruals ÷ average assets, 19.5 % flagged);
   - PAT − CFO "earnings-to-cash divergence" (₹5,469 Cr, 5-year cumulative ₹8,091 Cr);
   - the cash conversion cycle split into DSO / DIO / DPO deltas;
   - receivables-growth-minus-sales-growth and inventory-growth-minus-sales-growth;
   - "consecutive divergence years".
6. **Fundamentals and the market side by side**, in a divergence radar (business 80 / valuation
   45 / trend 40 / flow 32) and a structural matrix (quality × valuation). The market side:
   - a Weinstein stage (Stage 3 "topping", 5 sessions);
   - a delivery-based flow regime ("Distribution −0.71σ");
   - performance against the sector over 1W to 3Y.
7. **Valuation as an expectation gap.** Implied growth from a reverse DCF (Damodaran-style
   drivers: ROIC, WACC, sales-to-capital, reinvestment) against observed growth, with bear / base
   / bull intrinsic values.

## Data shapes (logged-out endpoints)

| Endpoint | Shape (fields only) |
|---|---|
| `GET /api/companies/<SYM>` | `company`, `annual[5]`, `quarterly[12]`, `pnl/balance_sheet/cash_flow[10]` (one flat row type: revenue, ebitda, net_profit, ocf, fcf, debt, inventory, receivables, payables, other_income, capex…; bank fields such as gnpa and casa are null for non-banks), `*_forensic` blocks (`periods`, `sections`, `summary_kpis`, `warning_chips`), `shareholding.quarters[12]`, `flags[]`, `flags_history[18]`, `valuation`, `analysis` |
| `analysis.structural_causality.latest_transition` | `score_start/end/delta, risk_class_start/end, percentile_start/end, primary_driver(+evidence), new/escalated/resolved/improved/persistent_flags, pillar_deltas, interaction_boost_delta, saturation_adjustment, drift_adjustment_pts, reconciliation, executive_summary`; plus `all_transitions[13]` and `turning_points{structural_break, structural_recovery}` |
| `analysis.predictive` | `trend, delta_qoq, slope_12q, acceleration, volatility, elasticity, escalation_prob, projected_stress, inflection_label, sector_percentile` |
| flag object | `flag_code, flag_name, severity, category, pillar, impact_weight, duration_quarters, momentum, primary_metric{label,value,delta,is_bad}, details{…trigger numbers}, evidence_dossier{lifecycle_status, is_resolved, why_this_matters, surveillance_checks, forward_monitoring_checklist, statutory_lineage, kpi_strip, time_series_table, potential_explanations, analyst_actions}` |
| `GET /api/companies/<SYM>/market-structure-history?days=N` | daily `{ohlcv, delivery_qty, delivery_pct, delivery_21/50/200/250, ma_150, ma_200, z_score, ad_flow, rs, rs_z, rtr, rtr_z, stage, is_delivery_spike}` |
| other | `/earnings-intelligence`, `/announcements?limit=50`, `/super-investors`, `/version` |

## Contradictions / cautions (read on this page)

> [!contradiction] The page contradicts itself in four places
> - **"6.8 % YoY deterioration in net profit to ₹2,578 Cr, compared with ₹2,413.5 Cr"** is a
>   6.8 % *increase*. The generated narrative attached the wrong sign.
> - **Inventory divergence (F15) fired with the wrong sign.** The card says "inventory growth
>   outpaced revenue by +45.8 pp", but its own ledger row reads inventory YoY **−27.5 %** against
>   revenue **−15.7 %**. Inventory fell *faster* than sales, and the annual table shows inventory
>   falling from ₹7,357 Cr to ₹2,617 Cr over three years. A +9.6-point contribution rests on it.
> - **The summary and the diagnosis disagree.** "Improving fundamentals … base building" sits
>   beside "Structural Deterioration Signature" and "escalating risk".
> - **The smoother hides most of the move.** The raw score was 32 and the published one is 20;
>   the "temporal drift smoother" removed 12 of the 17 gross points. The page discloses this,
>   which is to its credit, but the headline +5 hides it.

- **Nothing is measured.** No back-test links the risk score, a class (WATCH/ELEVATED) or any
  flag to forward drawdowns or returns. "Severe risk chance 5 %" and `escalation_prob` have no
  stated calibration. That is the same gap B-185 found at eVector.
- **The thresholds are hand-set** (Other Income/PBT ≥ 30 %, the elevated line at 66). On this
  desk they need pre-registered measurement before they count as anything (see
  [[investment-desk-not-trading-system]] in memory: calibration, not edge).

## Actionable insights (ranked for this desk)

1. **Flag lifecycle on `red_flags.py`.** FR-4 is yearly and static: FLAG / CLEAN / NOT_CHECKED
   per check. Adding quarterly evaluation, `first_seen`, `duration_quarters`, momentum and a
   **resolved** state would let the Stock Analyzer say "new this quarter", "third quarter
   running" or "cleared in Q1". This builds on the FR-4 three-state design; it doesn't replace it.
2. **Cash and accrual forensics from data the desk already has.** These are all computable from
   the FR-1 statement layer and XBRL quarterlies:
   - CFO/PAT, CFO/EBITDA;
   - accrual ratio;
   - cumulative PAT − CFO;
   - CCC split into DSO / DIO / DPO deltas;
   - receivables-minus-sales and inventory-minus-sales growth;
   - other income as a share of PBT.
   
   Each becomes a three-state check, and **every sign is tested against the raw numbers**:
   Flagium's F15 fired backwards.
3. **Attribution, not just a score.** If the desk ever builds a composite, it should ship with
   a reconciling waterfall (new / escalated / resolved / caps) and show raw against smoothed.
   Better still, it should skip the smoother.
4. **Measure before showing a probability.** Pre-register a study: do stocks whose forensic flag
   count or score *rises* quarter-on-quarter show worse forward drawdowns and returns than their
   sector? It would use the desk's own flags, run point-in-time on the filing date to avoid
   look-ahead, and follow the rec_audit / event_study pattern. Until that study runs, any
   "severe risk chance" is decoration.
5. **Delivery-based flow regime.** Flagium's `market-structure-history` carries delivery % with
   21/50/200/250 averages and a delivery-spike flag. The desk's volume-anomaly and B-51 cause
   attribution partly cover this. A delivery-z flow regime would sit next to the smart-money
   layer, unmeasured until scored.

## Pages updated

- [[analyses/Open-Backlog]]: B-191 to B-193 filed
- `index.md`, `log.md`
