---
title: "Market Terminal — UI/UX Design Reference (competitor snapshot)"
category: source
tags: [design, ui, ux, competitor, dashboard, freemium, rating-system, chart-annotation]
created: 2026-07-08
updated: 2026-07-08 (2nd pass — added Predictive Analysis View section from META screenshot)
sources: 1
related: [sources/PreMarketTool-repo, sources/OptionTools-in]
---

# Market Terminal — UI/UX Design Reference (competitor snapshot)

## Metadata
- **Source:** Market Terminal (marketterminal.com) — commercial equity research/screener product.
- **Format:** Screenshot ingest of the "Ex Hours Breakouts" + "AAPL Chart" split view (day view, 2026-07-10 snapshot).
- **Purpose:** Design-language reference for future dashboard iterations. This is *design intelligence*, not methodology — nothing to trade off of; everything to potentially borrow.
- **Date accessed:** 2026-07-08.

## Layout Skeleton (what to steal, what to leave)

Two-column split, ~50/50:

- **Left column** — data table (Ex Hours Breakouts) with paywall fade below the free-tier rows.
- **Right column** — chart panel with a rich rating rail + fundamentals mini-charts docked left of the candlesticks.

### Left column — table pattern
- **Header row** with total count + Play button ("6 Total Results ▶ Play") — the ▶ suggests an *auto-cycle-through-charts* action worth borrowing for our Scanner Hub.
- **Filter dropdown** in the header (Market Cap ⌄) — one prominent sort dial rather than a filter drawer.
- **Column set:** Symbol · Ex Hours $ · Ex Hours Chg % · YTD Chg % · Overall Rating (n/100) · Future Earnings (n/100) · Currency...
- **Rating cells rendered as `n/100`** with color signal (green for high, red for low) — see Rating System section below.

### Right column — chart panel pattern
- **Ticker tab bar** at top: AAPL / Chart / Earnings / Investors / Valuation / Financials / Analysts / Company — tab-per-view rather than a settings-heavy chart.
- **Timeframe row:** Day / Week / Month / Quarter / Year + **AI Prediction** button (purple gradient badge) + date picker + ⚙ Settings.
- **Left rail of drawing tools** — pencil, arrows, text, shapes — vertical strip, always visible (as opposed to hidden behind a toolbar).
- **Info stack docked left of the chart** (this is the distinctive move):
  1. Company header (name / sector / description one-liner)
  2. Metric grid (Avg Vol / Market Cap / P/E / YTD / % to 52W High / Div Yield)
  3. **Ratings card** — six line items with `n/100` scores
  4. **Annual Revenue mini-bar-chart** (past muted, future green, YoY % on each bar)
  5. **Annual Earnings mini-bar-chart** (same treatment)
  6. **Institutional Investors mini-bar-chart** with quarterly bins + growth % annotations
  7. **Growth Ratios line** (Gross Margin +47% > 40 ✓)
  8. **Show Less ▾** collapse control
- **Right-side price card** (floating on chart edge): Market Closed / Ex Hours prices with $-change and %-change
- **Chart annotations baked in**: green "Breakout" zone overlay, green "Overall Rating 85" label with anchor dot on the price series
- **Volume histogram** at bottom of price panel

## Rating System — The Core Design Idea

Every quantitative attribute becomes a `n/100` score with a color:
- Future Earnings 84/100
- Current Strength 99/100
- Inst. Accumulation 71/100
- Industry Leadership 95/100
- Sector Strength 87/100
- **Overall Rating 85/100** (rolled-up composite)

**Why this works as a design pattern:**
- **Universal comparability.** Any two stocks compare on the same 0–100 scale; no need to explain what "P/E of 38.4x" means in isolation.
- **One-glance triage.** Green 85 = worth looking; red 46 = skip. Cognitive load close to zero.
- **The composite is the hook.** "Overall Rating 85" is the number the user actually cares about; the six sub-ratings are provenance for that number.
- **Grade-inflation risk.** If everything scores 80+, the scale loses meaning. The screenshot's 46/100 red row (BYD Future Earnings) suggests the scale is genuinely distributed.

**Adoption fit for our dashboard:** we already compute Minervini/8, TechnoFunda/6, CANSLIM/4. Rolling these into a single **Overall Rating /100** with color-coded sub-scores would materially improve scanner-list readability. Currently the Scanner Hub shows each score in its own column — that's provenance, not headline.

## Chart Annotation Language

Two annotation types visible on the AAPL chart worth borrowing:

1. **Regime/pattern overlay** — the semi-transparent green "Breakout" box from Feb–Mar 2026 spanning the base + breakout. Rendered as a *filled rectangle* on the chart canvas, not a shape drawn by the user. This is auto-detected pattern annotation, not a manual drawing.
2. **Anchored label on price** — green dot at $317.40 with "Overall Rating 85" label attached, floating on the right edge of the price series. Ties the rating system to a specific price/time anchor.

**Adoption fit:** the chart_server already exposes `/api/vcp`, `/api/rounding_bottom`, and now `/api/trendlines` — all pattern-detection endpoints. Rendering the detected pattern as a labeled semi-transparent regime box (like the "Breakout" one here) rather than just lines/points would be a directly reusable idea.

## Freemium UX Pattern

The paywall implementation is worth studying independently of whether we ever use it:

- **First 5 rows visible, remaining ~15 rows blurred** with a lock icon overlay.
- CTA card slides up from the middle of the blurred area: "Unlock All Ex Hours Breakouts & Get Full Access — Try It For Free" → email input → **Take A Free Trial** button.
- Below CTA: bullet list of what's behind the wall ("Company Profiles, Earnings & More · Financials &...").
- Small footer: "Member's Get Real-Time..." — real-time data is the anchor value prop.
- **Lock icons on gated nav tabs** — 🔒 Markets, 🔒 Newsletters, 🔒 Breakouts. The lock as a first-class UI symbol, not hidden.

## Distinctive UI Elements Worth Noting

- **Purple gradient for AI features** — "AI Predictions" nav item and "AI Prediction" button in the chart toolbar both use purple. Consistent visual code that separates AI-generated content from human/rule-based scores.
- **Dark/light toggle** in the top-right (☼/☾ icons) — same pattern as our dashboard.
- **Emoji-prefixed nav items** — 💡 Ideas, 📊 Movers, ⚡ AI Predictions. Adds a scannability aid without leaning on iconography libraries.
- **Value + delta pair everywhere** — every number has a $-change and %-change next to it, styled consistently. Never just the number in isolation.
- **Compact "Show Less ▾" collapse** at the bottom of the info stack — respects that the whole rail is a lot, gives the user a knob.

## Ideas Worth Prioritising for Our Dashboard

Ranked by ROI given our current architecture:

1. **Composite `n/100` rating in Scanner Hub** — roll up Minervini/TechnoFunda/CANSLIM/EW/RS into one Overall Rating column with color, show sub-scores on row expand. **Highest ROI: table becomes triageable at a glance.**
2. **Auto-Play through candidate charts** — a Play button that cycles the chart pane through the current scanner result set, one N-second beat per name. Easy to build on top of the existing pane symbol setter.
3. **Semi-transparent regime overlay** for detected patterns (VCP, Rounding Bottom, Breakout) — filled rectangles labelled with the pattern name, rendered from the existing `/api/*` endpoints.
4. **Info stack docked left of the chart** — fundamentals/ratings summary card that fills the currently-empty left side of the chart pane. Uses data our screener_pipeline already computes.
5. **Anchored labels on the price series** — "Overall Rating 85" style badge tied to the current bar. Reinforces the rating system visually.
6. **Value + delta styled pair everywhere** — small style pass on the dashboard to make sure every metric has its $/% change styled consistently.
7. **Show Less collapse** on any info-heavy panel — an obvious ergonomic missing on some of our tabs.

## Not Worth Copying

- **Aggressive paywall gating** — doesn't apply to a personal-use dashboard, but the *visual language* of lock + blur + CTA is a reference point for any future "beta features" gating pattern if we ever share the tool.
- **Emoji-heavy nav** — nice for a marketing-facing product, might feel cluttered in an internal power-user tool. Optional.
- **AI Prediction as headline feature** — treating LLM-generated forecasts as a first-class product surface is a marketing choice, not a research choice. Our stack already routes LLM analysis into the Pree Market Tool report — that's where the AI content belongs, not on the chart.

## Predictive Analysis View (second screenshot — META, 2026-07-10)

A separate view of the same platform, showing the **AI Prediction** feature applied to META. This is the specific view the user has flagged as a future build target. Files everything from the base UI reference above plus these predictive-specific elements:

### Elements on the predictive view
- **`AI Prediction` button in the chart header** — purple gradient, primary action. Toggles the projection on/off.
- **`Clear Prediction` button** (top-right, purple) — dismissal control once a prediction is drawn.
- **Forward projection line** — dashed blue line extending from current price ($654.44) forward past the visible range, terminating at a labelled endpoint `$693.80` with `AI Prediction +9.87%` annotation on the right edge. **Two numbers surfaced together**: the projected price *and* the expected % move. Never one without the other.
- **Auto-detected pattern boxes rendered on the chart:**
  - Left-side **`Breakout`** — light-green filled band spanning the base + breakout zone (~$479.80 → ~$581 area, Feb–Aug 2025).
  - Right-side **`Breakdown`** — light-red filled band around the recent top rollover.
- **Click-a-pattern-for-detail tooltip** on the Breakdown box (visible in screenshot):

| Metric | Value |
|---|---|
| Consolidation | 88 days |
| Breakout Pivot | $581.25 |
| Breakdown Pivot | $744.00 |
| Depth | 21.88% |

This is a **structured pattern metadata tooltip** — not just a name label. It exposes the geometry the detector found (consolidation duration, pivot levels, depth %) so the user can validate the detection at a glance.

### What makes this specific view worth building

The predictive-analysis view is **where the platform's rating system, pattern-detection engine, and AI projection converge into one screen**:
- The **Ratings rail** (Future Earnings 99, Current Strength 44, Overall 70) provides the *why*.
- The **pattern boxes** (Breakout/Breakdown with metadata tooltip) provide the *where* on the chart.
- The **AI Prediction line + %** provides the *what next*.
- The **fundamentals mini-charts** below (Revenue, Earnings, Institutional Investors, Growth Ratios) provide *the context to weight the prediction*.

One screen answers "should I take this trade, and if so, what's the target and confidence." That's the whole point.

### Adoption plan for our dashboard (concrete)

Mapping directly to what we already have:
1. **Ratings rail** — roll up Minervini/8 + TechnoFunda/6 + CANSLIM/4 + EW confidence into `n/100` sub-scores; composite as Overall Rating. Already flagged as highest-ROI change.
2. **Pattern boxes** — the endpoints exist: `/api/vcp`, `/api/rounding_bottom`, `/api/trendlines`. Rendering their detection as a filled semi-transparent rectangle labelled with the pattern name (+ click-for-metadata tooltip using the geometry the detector already returns) is a directly executable extension.
3. **AI Prediction line + %** — the Pree Market Tool already runs a two-brain LLM analysis (Claude + Codex → merged report). Extending that to emit a projected price + % move (with structured reasoning) that the chart can render is the natural bridge between the two workstreams.
4. **Consolidated screen** — the "Stock Analyzer" tab in [tools/dashboard_app.py](tools/dashboard_app.py) is already 80% of this. Adding the ratings rail + pattern-metadata tooltip + AI projection turns it into the equivalent view.

Full ticket breakdown queued in [[analyses/Dashboard-UI-Roadmap]] (see follow-up).

## Contradictions with Existing Wiki
- None. This is a design source; no methodology conflict.

## Pages Updated
- Created: `wiki/sources/MarketTerminal-UI-Reference.md` (this page)
- Updated: `wiki/index.md`, `wiki/log.md`
- **Flagged (not created this ingest):**
  - `analyses/Dashboard-UI-Roadmap.md` — a prioritised plan folding the top 3–4 ideas above into concrete tickets (Overall Rating rollup, Play-through, regime overlays, info stack).
