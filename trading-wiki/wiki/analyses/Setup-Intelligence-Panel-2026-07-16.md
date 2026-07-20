---
title: "Analysis: Setup Intelligence Panel — SwingEdge-Style Card on the Council Engine"
category: analysis
tags: [dashboard, stock-analyzer, council, swingedge, ui, feature-build, presentation-layer]
created: 2026-07-16
updated: 2026-07-16
sources: 1
related:
  - analyses/Dashboard-UI-Roadmap.md
  - sources/SwingEdge-KDDL-20260621.md
  - sources/SwingEdge-INDSWFTLAB-20260621.md
  - sources/MarketTerminal-UI-Reference.md
  - concepts/Stage-Analysis.md
  - concepts/Volume-Profile.md
---

# Analysis: Setup Intelligence Panel — SwingEdge-Style Card on the Council Engine
_16 July 2026_

## Thesis
SwingEdge's "Swing Edge Intelligence" card is **a presentation layer, not an analytics engine**. Every input it displays — relative strength, breakout readiness, accumulation, a bullish/risk factor split, an overall view — was *already computed* by our `tools/stock_council.py` 3-POV Council. The gap was never analytical depth; it was that our output was a scored trade card + drill-down tables, while theirs is a scannable plain-language card. Closing it was therefore a **zero-new-computation** job: a pure function over the existing evidence bundle.

## Evidence For

### 1. The council already had every input
| SwingEdge panel element | Existing council source |
|---|---|
| Setup status badge | `TradeCard.verdict` (BUY / WATCH / AVOID) + `conviction` |
| Relative Strength chip | `subscores["rs"]` (from `_relative_strength()` vs Nifty) |
| Breakout Readiness chip | mean of `subscores["proximity_high"]` + `subscores["trend"]` |
| Accumulation chip | `subscores["volume"]` (vol dry-up + OBV slope) |
| Bullish / Risk factors | `facts` dict (EMA stack, stage, RSI/MACD/ADX, RS, 52w, ATR%, OBV, turnover, fundamentals) |
| Overall view | `bull.conviction` / `bear.conviction` / `card.net_score` |

Nothing new had to be fetched or modelled.

### 2. Deriving from the council prevents self-contradiction
The panel's status badge is driven **directly off `card.verdict`**, and its factors are read from the same `EvidenceBundle` the Judge scored. This makes it structurally impossible for the summary card to disagree with the verdict beneath it — a real failure mode when a "summary" is computed independently and then drifts from the engine it summarizes.

### 3. Verified against synthetic scenarios, not assumed
Ran three constructed cases through `run_council()` → `setup_intelligence()`:

| Scenario | Verdict | Status | Bullish | Risk |
|---|---|---|---|---|
| Uptrend / risk-on | BUY | Strong technical characteristics | 10 | 1 |
| Downtrend / risk-off | AVOID | Weak technical characteristics | 2 | 12 |
| Flat / no regime | BUY | Strong technical characteristics | 10 | 2 |

Testing surfaced a genuine defect: bear **thesis-breakers duplicated** ordinary risk factors (e.g. "Thin liquidity (₹0.6 Cr/day)" alongside "₹0.6 Cr daily turnover — thin, slippage/exit risk"). Fixed by prefixing breakers `⚠️ Thesis-breaker —` so the restatement reads as escalation, not redundancy.

### 4. A defect in the reference implementation
> [!key-insight] SwingEdge's own card mislabels a bearish factor
> The ingested screenshot lists **"MACD below zero — weak trend (−2)"** under **BULLISH FACTORS**, carrying a *negative* score. A negatively-weighted item rendering in the positive column is a category bug in their panel. Ours files MACD-below-zero under Risk. **Lesson: SwingEdge is a UI reference, not a logic gold standard** — the same caution already recorded on [[sources/SwingEdge-INDSWFTLAB-20260621]], where their RS-100 framing contradicted [[sources/SwingEdge-NRBBEARING-20260621]].

## Evidence Against

- **Not full SwingEdge parity.** Their card shows volume-profile factors ("80% of profile volume above POC", "price above value area high", "price holding above POC") and pivot-quality/compression reads. Ours cannot: **volume profile is JS-only** (`tools/volume_profile.js`) with no Python port, so `stock_council.py` has no POC/VAH access. See [[concepts/Volume-Profile]].
- **Deliberately scoped down.** Granular factors available in `tools/scanner_templates.py` — `scan_near_pivot()`, `detect_vcp_geometry()` (compression ratio), `compute_pre_breakout_conviction()`, `detect_bullish_candlestick()` — were **not** wired in. The panel is council-evidence-only by choice, trading granularity for guaranteed verdict-consistency and a smaller surface.
- **Thresholds are hand-set, not fitted.** The factor cut-points (RSI 75 overbought, ADX 25 trending, ATR 2–6% healthy, turnover ₹5 Cr liquid, 200SMA +40% extended) are judgement calls inherited from the wiki's existing concept pages, not backtested. They shape what the card *says* without changing what the Judge *scores* — cosmetic drift risk only, but worth revisiting.
- **Chip banding is coarse.** Three bands (70 / 45 cut-points) on a 0-100 subscore will show "Strong" across a wide range; a 68 and a 46 both read "Moderate".

## Conclusion
Shipped and verified. The highest-value insight is architectural: **we were closer to SwingEdge than the UI suggested.** The council had the analytics; only the presentation was missing. This reframes competitor-parity work — before building analytics to match a competitor surface, check whether the evidence already exists and only the rendering is absent.

The remaining true gaps vs SwingEdge are narrow and specific: volume-profile POC factors (needs a Python port) and pivot/compression granularity (needs wiring, code already exists).

## Action Taken / Plan

**Done (2026-07-16)** — code, not wiki:
- `tools/stock_council.py` — added `SetupIntel` dataclass + `setup_intelligence(bundle, bull, bear, card)`; pure function, no fetches, no new computation. Also `_band()` helper for subscore→(label, tone) mapping.
- `tools/dashboard_app.py` — added `render_setup_intelligence()` (bordered containers, colour-coded chips, two-column factor lists, research-only disclaimer matching existing wording); wired into the Stock Analyzer **above** the Council verdict so the plain-language read comes first and the Bull/Bear/Judge drill-down follows.

**Deferred (ranked):**
1. **Port `volume_profile.js` → `tools/volume_profile.py`** — unlocks the POC/value-area factors *and* would serve the wider toolchain (scanner validations, chart server), not just this panel. Highest leverage of the three.
2. **Wire `scanner_templates.py` factors** into the panel (pivot proximity/quality, VCP compression ratio, pre-breakout conviction, candlestick trigger). Code exists; this is plumbing.
3. **Revisit thresholds** — consider deriving cut-points from the scan population (percentile-based) rather than fixed constants.

## Outcome (fill in later)
- _Does the panel actually change the read-speed of the analyzer in daily use, or is it decoration on top of the council card?_
- _Do the hand-set thresholds produce factor lists that feel right across a real scan population (esp. thin/illiquid NSE names)?_
- _Does "10 bullish factors" ever mislead by counting weak factors equally with strong ones? (Current design deliberately doesn't weight the display — the Judge does the weighting.)_

## Related Pages
- [[analyses/Dashboard-UI-Roadmap]] — the M1 "Overall Rating rollup" milestone shares this page's finding: composite/summary surfaces are rollups of evidence we already compute.
- [[sources/MarketTerminal-UI-Reference]] — same competitor-UI-as-design-intelligence pattern (their `n/100` rating rollup is the analogue of this panel's chips).
- [[sources/SwingEdge-KDDL-20260621]], [[sources/SwingEdge-INDSWFTLAB-20260621]] — the ingested SwingEdge detail pages this panel is modelled on, including their internal contradiction.
- [[concepts/Volume-Profile]] — the POC/value-area concepts behind the one factor family we can't yet render.
- [[concepts/Stage-Analysis]] — the stage read feeding the panel's trend factors.
