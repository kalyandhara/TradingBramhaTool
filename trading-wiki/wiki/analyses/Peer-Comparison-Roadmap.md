---
title: "Peer Comparison Roadmap — industry-peer scorecard table"
category: analysis
tags: [roadmap, peer-comparison, industry, relative-strength, stage, table, dashboard, presentation-spec]
timeframe: milestone-plan
created: 2026-07-25
updated: 2026-07-25
sources: 1
related:
  - analyses/Opportunity-Hub-Roadmap.md
  - analyses/Dashboard-UI-Roadmap.md
  - analyses/Setup-Intelligence-Visual-Spec.md
  - concepts/CANSLIM.md
---

# Analysis: Peer Comparison Roadmap

## Thesis
The user supplied a **UI mockup** (screenshot, 2026-07-25) of a **Peer comparison**
view: pick an **anchor stock**, pull its **industry peers**, and rank them side-by-side
on the technicals that decide leadership — RS, RSI, ADX, distance-from-52w-high, Weinstein
stage, and pivot distance — with a peer-group **leader callout** and per-metric badges.

**Grounded finding: this is almost entirely composition of pieces we already shipped.**
Every column is a metric the council/scanners already compute, and the *peer-resolution*
(same-industry constituents) already exists in the Opportunity Hub's yfinance industry
tagging. The genuinely new work is peer-*relative* scoring + the comparison-table UI.

## The mockup spec (record exactly)
- **Header:** "Peer comparison · Forgings · 7 stocks compared".
- **Leader callout:** "MMFL currently leads this peer group with **score 95**. HAPPYFORGE
  remains a contender at **81**." → a composite **peer score (0–100)** per stock.
- **Columns:** Company (ticker + full name) · Price · **RS** · **RSI** · **ADX** · **52w**
  (% from 52-week high) · **Stage** · **Pivot** (% to pivot) · **Compare** ("vs ANCHOR" link).
- **Anchor row highlighted** (HAPPYFORGE) and pinned; every other row gets a "vs
  HAPPYFORGE" compare link.
- **Badges:** a row-level **"RS Leader"** chip next to the ticker; a cell-level **"Best RS"**
  on the group's max-RS cell; **"Strong ADX"** on high-ADX cells.
- **Colour coding:** green = good (high RS, near/above pivot, shallow 52w drawdown), red =
  bad (low RS, deep drawdown, Stage 4). Observed: GANGAFORGE RS 4 / RSI 24 / 52w −59.8% /
  Stage 4 all red; MMFL RS 100 / ADX 42 green + badged.
- **Stage labels are richer than raw 1–4:** "Continuation", "Stage 2", "Stage 2 (Early)",
  "Failed Reclaim", "Stage 4" — a labelling layer over `_infer_stage`.
- **Presentation = a TABLE.** This is a *comparison* surface (N stocks × identical
  columns), where a table is the correct and intended form — **distinct from the Scanner
  Hub**, whose results stay as cards (per the standing card-presentation rule). Don't apply
  the card rule here; the mockup itself is tabular.

## Current State (grounded audit, 2026-07-25)
| Column / piece | What we already have | Where | Gap |
|---|---|---|---|
| **Peer resolution** (same-industry constituents) | `build_constituent_table` tags each stock's **industry** (yfinance `.info`, login-free) | [opportunity_hub.py](tools/opportunity_hub.py) | just filter the universe to the **anchor's** industry |
| **RS** | `rs_rank` / `rs_pct` (RS percentile / vs Nifty) | `_finalize_relative_strength` ([scanner_templates.py](tools/scanner_templates.py)), council | decide **peer-relative** rank vs absolute (mockup's "Best RS" implies within-group) |
| **RSI** | `RSIIndicator(14)` | council `facts["rsi"]`, screener_pipeline | ✅ have |
| **ADX** | `ADXIndicator(14)` | council `facts["adx"]` | ✅ have (+ "Strong ADX" badge ≥ ~25) |
| **52w** | `pct_from_52w_high` | council `facts` | ✅ have |
| **Stage** | `_infer_stage` (1–4) | [stock_council.py](tools/stock_council.py) | **richer labels** (Continuation / Early / Failed Reclaim) |
| **Pivot** | `dist_to_pivot_pct` (`scan_vcp`) / `scan_near_pivot` | scanner_templates | ✅ have |
| **Peer score (95/81)** | M1 `_overall_rating` (/100) | [dashboard_app.py](tools/dashboard_app.py) | reuse, or a peer-relative composite |
| **Comparison table UI** | — | — | **new** — table + badges + colour + anchor pin + "vs anchor" link |

> [!key-insight] Peer comparison is the Opportunity Hub, inverted
> The Opportunity Hub goes *sector → industry → constituents*. Peer comparison fixes the
> anchor's **industry** and compares its **constituents** head-to-head. It reuses the same
> `build_constituent_table` industry tags and the same per-stock metrics — it's a new
> *view*, not a new engine. Natural drill-in from both the Stock Analyzer and the
> Opportunity Hub industry ranking.

## Evidence For
- **~80% composition** — every metric and the industry map already exist; this is a query
  + a table.
- **Answers a real question** — "is my stock the best horse in its race?" Leadership is
  relative; an absolute Overall Rating doesn't say whether a *peer* is stronger.
- **Compounds two shipped systems** — the M1 Overall Rating and the Opportunity Hub
  industry tagging both get more useful behind one comparison view.

## Evidence Against
- **Peer-relative vs absolute scoring is a real design choice** — RS "100 = Best RS" reads
  as *within-group* max, but our `rs_pct` is *vs Nifty*. Mixing the two would mislead;
  pick one per column and label it.
- **Industry tags are yfinance-quality** — occasionally coarse/missing for NSE
  mid/small-caps (same caveat as the Opportunity Hub); a thin peer group (1–2 names) isn't
  a comparison. Guard with a minimum-peer-count.
- **Stage labels need calibration** — "Failed Reclaim" / "Continuation" are richer than the
  1–4 heuristic; defining them adds surface for disagreement with the Judge.
- **Hand-set peer score** — the 95/81 composite is unbacktested like every other weight;
  route it through the [[analyses/Backtest-Harness]] before trusting it as leadership truth.

## Phased plan (for later — foundation only)
- **PC-1 — Peer resolution + comparison table (absolute metrics).** Anchor → its industry
  (`build_constituent_table`) → same-industry peers → columns RS/RSI/ADX/52w/Stage/Pivot
  from the council metrics, rendered as a table with the anchor pinned. Ships the whole
  comparison with no new signal.
- **PC-2 — Peer-relative scoring + badges + leader callout.** Rank RS/ADX *within the peer
  group* (Best-RS / Strong-ADX / RS-Leader badges), compute the composite **peer score**
  (0–100), and the "X leads this group, Y is a contender" callout.
- **PC-3 — Colour coding + anchor highlight + "vs anchor" drill.** Green/red bands per
  column; "vs ANCHOR" opens a two-stock head-to-head (reuse the council/Setup-Intelligence
  read for both).
- **PC-4 — Stage-label enrichment + surfacing.** Continuation / Stage-2-Early / Failed
  Reclaim / Stage-4 labels over `_infer_stage`; wire the panel onto the **Stock Analyzer**
  (peers of the analysed name) and as a **drill from the Opportunity Hub** industry ranking.
- Sequencing rule (inherited): don't start PC-N until PC-(N−1) ships + one live session.
- **Packaging:** native dashboard feature (consistent with the radar/setup-intel decisions).

## Action Taken / Plan
- ✅ Foundation ingested into the roadmap (2026-07-25); this page + pointers from
  [[analyses/Dashboard-UI-Roadmap]] (Phase 2) and [[analyses/Opportunity-Hub-Roadmap]]
  (sibling to industry rotation). **Nothing built.**
- ⏭ When ready: **PC-1** first (peer resolution + table off existing metrics).

## Outcome (fill in later)
- _2026-07-25: foundation ingested from the user's mockup. Awaiting go-ahead on PC-1._

## Related Pages
- [[analyses/Opportunity-Hub-Roadmap]] — provides the industry-tagging engine peer resolution reuses; peer comparison is its inverted (constituent-vs-anchor) view.
- [[analyses/Dashboard-UI-Roadmap]] — the analyzer this extends (Phase 2 features).
- [[analyses/Setup-Intelligence-Visual-Spec]] — sibling ingested mockup; the "vs anchor" drill reuses the Setup Intelligence read.
