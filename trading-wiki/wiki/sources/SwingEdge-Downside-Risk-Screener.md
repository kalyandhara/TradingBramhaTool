---
title: "SwingEdge — Downside Risk Screener (Methodology)"
category: source
tags: [swing-trading, bearish, distribution-days, support-loss, screener, stage-analysis]
created: 2026-06-22
updated: 2026-06-22
sources: 1
related: [concepts/Distribution-Days, concepts/Stage-Analysis, concepts/Support-Resistance, entities/AADHARHFC, sources/SwingEdge-KDDL-20260621, sources/SwingEdge-Position-Sizing-Tool]
---

# Source — SwingEdge.info Downside Risk Screener

## Metadata
- **Source type**: Pre-built scanner listing page, same site as the 3 prior stock-detail ingests and the position-sizing tool ingest
- **URL**: https://www.swingedge.info/breakdowns
- **Fetch date**: 2026-06-22

## Important caveat on this fetch
**No live scanner results (actual flagged tickers) were captured.** Like the position-sizing tool page, this screener's result table (`#scannerCards`) loads via client-side JS after page render — the static HTML only contains the page shell, methodology copy, FAQ schema, and an empty-state placeholder. This is filed as a **methodology source**, documenting how the Downside Risk screener works, not as a list of specific bearish stocks. To get the live flagged list, the page would need a browser-rendering fetch.

## Key Takeaways
- This is the explicit **bearish counterpart** to the Base Formation ([[sources/SwingEdge-KDDL-20260621]]) and Momentum Continuation ([[sources/SwingEdge-NRBBEARING-20260621]]) scans — same underlying scoring infrastructure, run in reverse.
- **Support-loss detection methodology** (concrete and falsifiable): "The scanner identifies pivot lows (local minima with at least two confirming candles on each side) as the true support levels. A close more than 0.5% below pivot support triggers a structural break flag." This is a real definition worth adopting as a standard rather than a vague "broke support" eyeball call — added to [[concepts/Distribution-Days]] and cross-linked to [[concepts/Support-Resistance]].
- **Distribution-day formula, precisely stated**: "price closing down, volume at least 0.5 standard deviations above the 50-day average, a wide spread and a close near the low of the day." This directly explains the skip-flag language seen earlier on [[entities/AADHARHFC]] ("6 distribution days recently") — now formally defined in a new [[concepts/Distribution-Days]] concept page rather than left as an unexplained source quote.
- **"Bearish DMA stack" = explicit inverse of Stage 2**: "When faster averages sit under slower ones with negative slopes it matches the inverse of popular Stage 2 illustrations." This confirms SwingEdge's Stage framework is the same Weinstein-style 4-stage model already in this wiki's [[concepts/Stage-Analysis]] page, just applied in reverse for the bearish case (effectively Stage 4 / decline phase).
- **Confidence tiers, with explicit numeric bands**: Severe (80+ score) = "many independent rules fired together"; High (65–80) = "several confirmed stressors"; Moderate (50–65) = "fewer simultaneous triggers." These thresholds are now documented for cross-reference against any future SwingEdge bearish-ticker ingest.
- **Composite score inputs** (named explicitly in the FAQ schema): "DMA position and slope, pivot retests, volume z-scores on down days, RSI/MACD softness, RS percentile, trend-strength components and lower-high geometry" — i.e. the same category of inputs as the bullish scans, scored for the opposite outcome.
- Heavy, repeated legal/regulatory hedging throughout: "not personalised sell or short advice," "not a blanket short list or exit order," explicit "Does Swing Edge tell me to short or exit? No." — notably more disclaimer density than the bullish stock-detail pages, likely because short/avoid signals carry more perceived liability than buy/watch signals.
- Practical workflow section ("How Practitioners Combine This Screener With Their Process") suggests: (1) cross-check own holdings against the list after each refresh, (2) read the Notes column for which specific rules fired, (3) be wary of "cheap can stay cheap" with sharp drawdowns + bearish structure, (4) optionally map stressed cash names to derivatives for hedging (with an explicit "Swing Edge never places those trades" disclaimer), (5) watch for failed retests of broken pivots (price revisits the broken level and fails to reclaim it, settling back under — a bearish confirmation pattern).

## Detailed Notes
**Retest-failure pattern, explicitly named**: "When price fails to reclaim a broken pivot on a second settlement below, our tagger records the sequence" — this is the bearish mirror of a classic breakout-and-retest continuation pattern, and is functionally identical in spirit to this wiki's existing [[concepts/Support-Resistance]] "flip zones" idea (a broken support becoming resistance), just framed from the failure side.

**Data freshness note** (applies to all SwingEdge scanner pages, worth remembering generally): "Prices and day-change figures use the last daily close from the latest scan — not live intraday NSE quotes."

## Actionable Insights
- The support-loss and distribution-day formulas given here are precise enough to be useful as general technical-analysis reference points even outside SwingEdge itself — captured in the new [[concepts/Distribution-Days]] concept page so future ingests/strategy work can cite a concrete definition instead of an intuitive one.
- If a future ingest wants the live flagged ticker list from this or any other SwingEdge scanner page (`/breakouts`, `/pre-breakout`, `/darvas-box`, etc.), a plain `curl` will not work — these all render their result tables client-side. A browser-based fetch (or the per-stock `/stocks/<TICKER>` page, which does embed data server-side) is required instead.

## Contradictions with Existing Wiki
- None. This formalizes and sharpens existing concepts ([[concepts/Stage-Analysis]], [[concepts/Support-Resistance]]) rather than contradicting them.

## Pages Updated
- Created [[concepts/Distribution-Days]]
- This source page
