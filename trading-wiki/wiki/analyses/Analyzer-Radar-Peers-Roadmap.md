---
title: "Analyzer Radar + Peer Comparison — merged roadmap (2026-09-04 re-audit)"
category: analysis
tags: [roadmap, radar-chart, peer-comparison, stock-analyzer, fundamentals, dashboard, presentation-spec]
timeframe: milestone-plan
created: 2026-09-04
updated: 2026-09-04
sources: 2
related:
  - analyses/Radar-Chart-Analyzer-Fit.md
  - analyses/Peer-Comparison-Roadmap.md
  - analyses/Fundamental-Deep-Dive-Report-Roadmap.md
  - analyses/Opportunity-Hub-Roadmap.md
  - analyses/Open-Backlog.md
---

# Analysis: Analyzer Radar + Peer Comparison (merged roadmap)

Supersedes the *sequencing* in [[analyses/Radar-Chart-Analyzer-Fit]] (RC-1…RC-4) and
[[analyses/Peer-Comparison-Roadmap]] (PC-1…PC-4). Those pages stay for their band
research and mockup spec; this one carries the plan, because a 2026-09-04 re-audit
found **RC-1 as written is now the wrong first step**.

## What changed since the two roadmaps were written (grounded, 2026-09-04)

| RC-1's premise (2026-07-25) | Reality today |
|---|---|
| "fundamentals fetched but barely visualized" | **False now.** `render_fundamental_signals` ([dashboard_app.py:1725](tools/dashboard_app.py)) already draws **six banded axes** as donuts on the Stock Analyzer, called at [:4151](tools/dashboard_app.py), plus Business/Entry verdict chips and a coverage dial. |
| "need a /10 band scorer" | **Shipped** — `score_all()` in [fundamental_score.py:328](tools/fundamental_score.py), six axes 0–100: Valuation · Growth · Health · Returns · Capital Allocation · Earnings Consistency, with per-axis `score / verdict / drivers / missing`, and `score=None` for unknown (never a neutral 50). |
| "3Y CAGR + true ROCE need screener.in" | **Dead.** `derive_fundamentals()` ([fundamentals_deep.py:387](tools/fundamentals_deep.py)) returns `revenue_cagr_3y`, `profit_cagr_3y`, `roce`, `roce_prev` from free yfinance statements. |
| "radar is 4 axes, Growth/Valuation/Finance/Sentiment" | The shipped scorer is **6 axes and all fundamental** — no Sentiment axis, deliberately (technical lives in M1 / Setup Intelligence). The video's 4-tuple is now the *stale* spec; the scorer is the truth. |

**So RC-1 (single-stock fundamental radar) is no longer additive — it would redraw
data already on screen.** That is the whole finding of this re-audit.

## My analysis: where the radar actually earns its place

Current design consensus on radar charts is unflattering and consistent: shape area
scales as the *square* of the values, so small differences read as large ones;
comparison around a circle is harder than along a straight axis; and they degrade
past ~10 axes or ~4 overlaid series. The conditions under which they *do* work are
narrow, and we happen to meet them exactly: **5–7 axes, one shared normalised 0–100
scale, ≤3 overlaid series, and profile/balance mattering as much as individual values.**

That yields a clear rule for this desk:

> [!key-insight] A radar for one stock is decoration; a radar for a stock **against its peer group** is information.
> Six donuts already answer "how does this company score". They cannot answer
> "is this shape normal for this industry" — six numbers against six other numbers is
> exactly the comparison a table does badly and an overlay does well. Build the
> **peer group first**, then the radar as an *overlay* (anchor vs peer median,
> two traces), not as a solo trace.

Corollaries, recorded so they are not relitigated:
- **Two traces max by default** (anchor + peer median); a third only on an explicit
  "compare vs X". Four overlapping polygons is the documented failure mode.
- **Never read area.** Label it a profile, keep the six numbers visible beside it;
  the donuts stay the precise readout, the radar carries the shape.
- **Axis order is fixed** by `fscore.AXES`, because rotating axes changes area and
  therefore changes the apparent verdict for identical data.
- The two-radar collision the old page warned about still stands: this is the
  *fundamental* radar; [[analyses/Setup-Intelligence-Visual-Spec]] is the *technical*
  one. They must never share a legend or an "Overall".

## Presentation spec for the peer table (design-current)

Tabular is correct here (N stocks × identical columns) and is **not** covered by the
scanner card rule — that rule governs the Scanner Hub, and this is a comparison
surface. Current data-table practice adds four things the 2026-07 mockup did not
specify:

- **Frozen first column** (ticker) + **sticky header**; the peer table is wide.
  Watch stacking: header above body, frozen column above body but below the header,
  subtle shadow on the frozen edge so it reads as a layer, not a seam.
- **Right-align numbers, left-align names, centre badges**; dense row height
  (36–40px), not the comfortable 48–52px — this is a scanning surface.
- **Heatmap tint only on a meaningfully sorted table.** Sort by the anchor's weakest
  axis, or by peer score; an unsorted heatmap is noise.
- **In-cell bars over raw colour** where the metric is 0–100 (the six axes) — the bar
  carries magnitude, the tint carries good/bad, and colour-blind users still get the bar.

## Phased plan (replaces the RC-1…RC-4 / PC-1…PC-4 ordering)

- **FP-1 — Peer resolution + fundamental peer table.** Anchor → its `industry` tag
  (reuse `build_constituent_table`, [opportunity_hub.py:89](tools/opportunity_hub.py),
  yfinance `.info`, login-free) → same-industry names → `score_all()` per peer → a
  table of the six axes + Business/Entry words, anchor row pinned and highlighted.
  *No new engine, no new scorer, no new data source.*
  **Guards this phase must ship with:** a **minimum peer count** (≥4, else say "too
  few peers tagged" rather than draw a comparison of two); a **hard cap** on peers
  scored (≤12, ranked by market cap) because each peer costs an `.info` plus three
  statement fetches; `st.cache_data` on the per-peer score; and an explicit
  **coverage column** — a peer whose statements did not resolve must show DATA N/A,
  never a low score.
- **FP-2 — The radar, as an overlay.** `go.Scatterpolar`, two traces: anchor vs
  **peer median** per axis (median, not mean — one loss-maker skews a 6-name group).
  Plotly is already a dependency. Renders beside the existing donuts, captioned as a
  profile, not a score.
- **FP-3 — Peer-relative reading + leader callout.** The anchor's rank within its
  group per axis ("Valuation: cheapest of 9"), a leader chip on the group's best cell
  per axis, and the "X leads this group, Y is a contender" line.
  **Label absolute vs peer-relative per column** — the old roadmap's sharpest catch:
  mixing an RS-vs-Nifty percentile with a within-group rank in one table misleads.
  Any composite "peer score" here is unbacktested and must be worded as a ranking of
  the six axes, not an edge claim.
- **FP-4 — Technical columns + "vs anchor" drill.** Add the 2026-07 mockup's
  RS / RSI / ADX / 52w / Stage / Pivot columns from the council facts, the richer
  stage labels (Continuation / Stage 2 Early / Failed Reclaim / Stage 4), and a
  two-stock head-to-head reusing the council + Setup Intelligence read.
- **FP-5 (optional) — Surface twice.** The same component drilled from the Opportunity
  Hub industry ranking, and dropped into the deep-dive report's **Peers** tab.

Sequencing rule inherited: do not start FP-N until FP-(N−1) ships and gets one live
session. Packaging unchanged: **native dashboard feature**, not a Claude skill.

## Evidence against (kept honest)
- **Industry tags are yfinance-quality** — coarse or missing for NSE mid/small-caps.
  FP-1's minimum-peer-count guard is the whole mitigation; expect some names to have
  no usable peer group at all, and say so plainly.
- **Latency is the real cost**, not code. Twelve peers × four network fetches is the
  slowest thing on the Stock Analyzer. It must be lazy — behind an expander or a
  "Compare peers" button, never on the default Analyze path.
- **Rank in a 6-name group is a weak statistic.** Report rank ("3rd of 7"), not a
  smooth percentile, below ~10 peers.
- **Growth saturates.** In both measured groups nearly every peer scored Growth 90-100,
  because the band tops out at 25% CAGR and post-COVID Indian jewellers and insurers all
  clear it. An axis where everyone scores full marks discriminates nothing — a *peer*
  table is what made this visible, since the anchor's own donut looked fine. Recorded
  against `fundamental_score.py`'s bands, not fixed here.
- **Still no backtest.** Nothing here claims edge; it is a context surface, consistent
  with the desk being a research desk rather than a signal generator.

## Action Taken / Plan
- ✅ 2026-09-04: re-audit filed. RC-1 **retired as written** (its output already ships
  as donuts); the radar is demoted to FP-2 and redefined as an overlay.
- ✅ **2026-09-04 — FP-1 SHIPPED.** [peer_comparison.py](tools/peer_comparison.py)
  (resolution + scoring + `table_html`) and `render_peer_comparison` in
  [dashboard_app.py](tools/dashboard_app.py), behind a **Compare peers** button on the
  Stock Analyzer. Measured: TITAN → *Luxury Goods*, 9 jewellers; RELIANCE → *Oil & Gas
  Refining & Marketing*, 8 names; NIACL → 12 insurers.
  **Three things the build forced, all worth keeping:**
  1. **A widening rung the plan did not have.** yfinance's fine industry is *too* fine
     for NSE: NIACL's "Insurance - Diversified" holds exactly one other listed name and
     IRCTC's "Travel Services" three, so the MIN_PEERS floor refused nearly every
     financial. yfinance industry strings are hierarchical by convention
     ("Insurance - Life", "Banks - Regional"), so the ladder now widens one rung to the
     **family** and labels the group `Widened` when it does. The floor was not lowered.
  2. **Peer resolution is two-stage** — the offline NSE constituent files narrow by macro
     sector (their `industry` field is really the macro sector: "Financial Services" is
     121 names), and only that pool gets the network industry tag, cached to disk for 30
     days in `cache/peer_tags.json`. First anchor in a sector pays ~40-120 `.info` calls;
     every later one in that sector is free.
  3. **pandas re-introduced the exact dishonesty the scorer bans.** A column of ints and
     `None` becomes float64 with `NaN`, and `NaN is None` is False — so an unscored axis
     rendered as the literal text `nan`. `_score_or_none` now guards it. The no-neutral-50
     rule has to be defended at the render boundary too, not just in the bands.
- ⏭ Next: **FP-2**, the anchor-vs-peer-median radar overlay (`peer_median()` already
  returns exactly the vector it needs).

## Related Pages
- [[analyses/Radar-Chart-Analyzer-Fit]] · [[analyses/Peer-Comparison-Roadmap]] — the two superseded plans; keep for band research and the mockup spec.
- [[analyses/Fundamental-Deep-Dive-Report-Roadmap]] — owns the Peers tab FP-5 fills.
- [[analyses/Opportunity-Hub-Roadmap]] — supplies the industry tagging FP-1 reuses.
- [[analyses/Setup-Intelligence-Visual-Spec]] — the *other* radar; keep distinct.

## Sources
- Highcharts, "Radar chart explained: when they work, when they fail" (2026) — axis/series limits, shared normalised scale.
- Scott Logic, "A Critique of Radar Charts" (2011) — area-scales-as-square, circular comparison cost.
- Setproduct, "Data table UI design reference guide for 2026"; Pencil & Paper, enterprise data-table UX patterns — frozen column, sticky header, density, heatmap sorting.
