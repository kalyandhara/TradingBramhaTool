---
title: "Setup Intelligence — Visual Presentation Spec (gauges · VCP coil · setup-quality radar · heatmap)"
category: analysis
tags: [ui, presentation-spec, setup-intelligence, radar, heatmap, gauge, vcp, mockup, dashboard]
timeframe: milestone-plan
created: 2026-07-25
updated: 2026-07-25
sources: 1
related:
  - analyses/Setup-Intelligence-Panel-2026-07-16.md
  - concepts/Radar-Chart-Stock-Scoring.md
  - analyses/Radar-Chart-Analyzer-Fit.md
  - analyses/Dashboard-UI-Roadmap.md
  - concepts/VCP.md
---

# Setup Intelligence — Visual Presentation Spec

## Thesis
The user supplied a **UI mockup** (screenshot, 2026-07-25) of the *expected
presentation* for an enhanced **Setup Intelligence** panel. It is the visual
target: a four-panel layout — two semicircular **gauges**, a **Base / VCP coil**
panel, and a **Setup-Quality Radar** with a companion **heatmap bar breakdown**.
This page records that spec exactly so the build has a fixed reference.

**Important distinction — this is a *second, different* radar from the fundamental
one.** [[concepts/Radar-Chart-Stock-Scoring]] / [[analyses/Radar-Chart-Analyzer-Fit]]
is a **fundamental** radar (Growth/Valuation/Finance/Sentiment). *This* is a
**technical setup-quality** radar (VCP/RS/Stage/Volume/Low-risk/Clear-path) whose
axes map onto signals the **council already computes**. Keep them separate; don't
conflate the two "radars" or the two "Overall" numbers.

## Layout (2×2 panels, header "Setup intelligence · Overhead · VCP · radar · risk")

### Panel 1 — OVERHEAD SUPPLY (semicircular gauge)
- Subtitle: "Resistance ceiling above current price".
- **Semicircular gauge**, 0→high left-to-right, coloured needle/dot.
- Center value: **`0%`**; badge **"Clear path"** (green). Footer: "Few recent highs
  above price — room to run".
- **Meaning:** % / count of recent swing highs sitting *above* current price (overhead
  supply). Low = clear path up. Green when low, amber/red as overhead builds.

### Panel 2 — CHASE / FAILURE RISK (semicircular gauge)
- Subtitle: "Honest read on exhaustion & extended moves".
- Semicircular gauge; center **`0`**; label **"Low chase risk"** (green). Footer: "No
  major failure flags in the latest scan."
- **Meaning:** exhaustion/over-extension risk (extension above 200SMA, overbought RSI,
  climax volume, failed-breakout flags). Low = safe entry location.

### Panel 3 — BASE / VCP COIL
- Subtitle: "Depth, contractions & pivot distance".
- **Three stat tiles:** `BASE LENGTH 16w` · `DEPTH 30.6%` · `CONTRACTIONS 1`.
- **Base-zone visual** box (labelled e.g. "Shallow 1", a circled contraction index,
  "Longer →" axis hint).
- **CONTRACTION LADDER:** stacked bars per contraction — `L1 10.7% · L2 13.4% · L3 25% ·
  L4 5.7%` (the VCP footprint, each contraction's depth).
- **PIVOT DISTANCE slider:** range `−12% … At pivot … +3%`, marker at **−1.3%** (green
  zone near pivot). Footer: "Tightness 39.9% · Near pivot — watch for volume".
- **Meaning:** a direct visualization of `scan_vcp`'s output (base length, depth,
  contraction footprint, distance-to-pivot, tightness).

### Panel 4 — SETUP QUALITY RADAR + heatmap
- Subtitle: "Shape of the setup in one view".
- **Radar (spider), 6 axes** clockwise from top: **VCP · RS · Stage · Volume · Low risk ·
  Clear path**, each **0–100**, filled polygon.
- **Center number:** **`82.2`** — this is the **arithmetic mean of the six axis scores**
  (verified: mean(100, 50, 100, 93, 50, 100) = 82.2). The mockup labels it "**/10**",
  which is ambiguous vs the 0–100 axes — **build decision:** show it as `/100` to match
  the axes, or explicitly rescale to `8.2/10`. Recommend `/100`.
- **Companion "heatmap" = a horizontal bar breakdown** under the radar, one 0–100 filled
  bar per axis (the mockup: VCP 100 · RS 50 · Stage 100 · Volume 93 · Low risk 50 · Clear
  path 100). This is the same six numbers as the radar, read as ranked bars — the radar
  shows *shape*, the bars show *exact values*. Colour the fill by score band
  (green ≥ ~80, amber mid, grey/red low) to make it a true heatmap.

## Axis → existing computation (grounded)
| Radar axis | Maps to | Where | Status |
|---|---|---|---|
| **RS** | `subscores["rs"]` (RS vs Nifty percentile) | [stock_council.py](tools/stock_council.py) | ✅ have |
| **Volume** | `subscores["volume"]` (accumulation/vol confirmation) | `gather_evidence` | ✅ have |
| **Stage** | `facts["stage"]` (Weinstein 1–4) → normalise (Stage 2 = 100) | `_infer_stage` | ✅ have (needs 1–4 → 0–100 map) |
| **VCP** | `scan_vcp` base quality / footprint score | [scanner_templates.py](tools/scanner_templates.py) | ⚠ computed by the scanner, **not yet in the bundle** — small wire-in |
| **Clear path** | inverse of **Overhead Supply** (Panel 1) — related to `subscores["proximity_high"]` + recent-highs-above-price count | `gather_evidence` | ⚠ gauge is **new** (derive from highs above price) |
| **Low risk** | inverse of **Chase/Failure Risk** (Panel 2) — extension (`pct_above_sma200`), overbought RSI, failure flags | `gather_evidence` / scanners | ⚠ gauge is **new** (compose extension + exhaustion) |

> [!key-insight] Four of six axes already exist; the two new pieces are the gauges
> RS, Volume, Stage, and VCP are already computed (VCP just needs surfacing into the
> bundle). The genuinely new work is the **Overhead Supply** and **Chase/Failure Risk**
> reads — and those two gauges *are* the "Clear path" and "Low risk" radar axes. So
> building the two gauges also completes the radar.

## Evidence For
- **Mostly composition** — like the M4 Predictive page and the fundamental radar, this
  reuses subscores already computed; Plotly (`go.Scatterpolar` + `go.Indicator` gauges)
  is already a dependency, so no new library.
- **The coil panel is a direct render of `scan_vcp`** — the data (base length, depth,
  contraction footprint, pivot distance, tightness) is already produced.
- **One glanceable verdict** — radar shape + heatmap bars turn six technical subscores
  into an instant read, exactly the Setup Intelligence goal.

## Evidence Against
- **"/10 vs /100" ambiguity** — resolve the centre-score scale before building or the
  number contradicts the axes.
- **Two gauges are new computation** — overhead-supply and chase/failure need honest
  definitions + thresholds (hand-set until the [[analyses/Backtest-Harness]] can measure
  whether "low chase risk" actually improves outcomes).
- **Radar-area trap** (per [[concepts/Radar-Chart-Stock-Scoring]]) — read shape/bars, not
  polygon area; axis order changes the shape.
- **Two radars in the product** — this technical one vs the fundamental one; label each
  clearly so users don't confuse a VCP/RS/Stage radar with a Growth/Valuation one.

## Phased plan (for later — not started)
- **SV-1 — Setup-Quality Radar + heatmap** from the four axes that already exist (RS,
  Volume, Stage-normalised, VCP-wired-in), centre = mean, `/100`. Highest-ROI, no new
  signal.
- **SV-2 — Overhead Supply gauge** (recent highs above price) → also fills the "Clear
  path" axis.
- **SV-3 — Chase/Failure Risk gauge** (extension + exhaustion + failure flags) → also
  fills the "Low risk" axis.
- **SV-4 — Base/VCP Coil panel** — render `scan_vcp` output (stat tiles + contraction
  ladder + pivot-distance slider + tightness).
- Sequencing rule (inherited): don't start SV-N until SV-(N−1) ships + one live session.

## Action Taken / Plan
- ✅ Ingested the mockup as this presentation spec (2026-07-25). **Nothing built** —
  captured as the visual target for a later Setup Intelligence enhancement.
- ⏭ When ready: **SV-1** first (radar + heatmap off existing subscores). Packaging =
  **native dashboard feature** (consistent with the radar decision in
  [[analyses/Radar-Chart-Analyzer-Fit]]).

## Outcome (fill in later)
- _2026-07-25: spec ingested from the user's mockup. Awaiting go-ahead on SV-1._

## Related Pages
- [[analyses/Setup-Intelligence-Panel-2026-07-16]] — the current (chips + factor-list) panel this enhances.
- [[concepts/Radar-Chart-Stock-Scoring]] — the radar methodology (fundamental cousin); read-shape-not-area caution applies here too.
- [[analyses/Radar-Chart-Analyzer-Fit]] — the *other* (fundamental) radar; packaging decision shared.
- [[concepts/VCP]] — the base/coil panel visualizes this.
- [[analyses/Dashboard-UI-Roadmap]] — the analyzer this extends.
