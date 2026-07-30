---
title: "Fundamental Deep-Dive Report → Stock Analyzer Enhancement (ingested mockup + phased plan)"
category: analysis
tags: [roadmap, stock-analyzer, fundamentals, presentation-spec, visual-spec, design-system, red-flags, projections, eps, data-honesty, dashboard]
timeframe: milestone-plan
created: 2026-07-29
updated: 2026-07-29
sources: 1
related:
  - analyses/Dashboard-UI-Roadmap.md
  - analyses/Radar-Chart-Analyzer-Fit.md
  - analyses/Peer-Comparison-Roadmap.md
  - analyses/PEAD-Scanner-Roadmap.md
  - analyses/Decision-Support-Gating-Roadmap.md
  - analyses/Setup-Intelligence-Visual-Spec.md
---

# Analysis: Fundamental Deep-Dive Report → Stock Analyzer Enhancement

## Source
**4 screenshots supplied in-session (2026-07-29)** of a long-horizon fundamental
research report for **Aeroflex Industries Ltd** (NSE: AEROFLEX / BSE: 543972, ₹401.00,
as-of 2026-05-29) — an LLM-authored "15-Year Horizon" analyzer page with a
`✔ WEB-VERIFIED DATA` provenance badge (watermark suggests a walkthrough video).
Images were pasted into the conversation, **not filed to `raw/assets/`** (no file
handle available); the captured spec below is the durable record.

## Captured spec — what the mockup actually renders

**Shell**
1. **Sticky header** — company name · NSE/BSE codes · horizon label · price + %chg + as-of
   date · classification chips (`IRON & STEEL PRODUCTS`, `SMALL CAP`, `80% EXPORTS`) ·
   a **data-provenance badge** (`✔ WEB-VERIFIED DATA`).
2. **9-metric strip** (always visible, colour-coded): 52W range · Mkt cap · P/E (TTM) ·
   P/B · EPS TTM · ROE · ROCE · D/E · Div yield.
3. **Tab nav**: Valuation · Growth & Earnings · Health · Returns & Capital · Ownership ·
   Peers · View.

**Verdict layer**
4. **Verdict card** — `MODERATE` + a **data-score dial (8/11)** + a separate
   **confidence band** (MODERATE) + a 4-sentence narrative + 4 chips
   (`15-YR HORIZON`, `Entry: OVERVALUED`, `Business: GOOD QUALITY`, `FY27 Watch: SKID RAMP`).
   Note the deliberate split: **good business, bad entry price** — two verdicts, not one.
5. **6-signal donut row**, each donut = verdict word + the metric line that justifies it:
   Valuation `OVERVALUED` (P/E 96×, PEG 4.79×) · Growth `SLOWING` (3Y 18% < 5Y 25%) ·
   Financial Health `MODERATE` (debt-free, FCF −ve on capex) · Returns `AVERAGE`
   (ROE 14.1%, ROCE 18.8%) · Capital Allocation `INVEST. PHASE` (score 1/3, "deliberate
   capex") · Earnings Consistency **`DATA N/A`** with a 🚩 "Consensus not available".

**Analysis layer**
6. **3-year forward projections (FY26→FY29)** — Bull / Base / Bear revenue bars with
   CAGR, ₹Cr, margin and NOPAT est., plus an **inline derivation footnote**
   ("Bull: 5Y CAGR × 1.15 = 28.75%, FY26 best margin 23%. Base: × 0.85 … Bear: × 0.50,
   5Y worst margin 15%") — the assumptions are shown, not hidden.
7. **Strengths (3) / Risks (2)** cards — icon + bold claim + quantified prose
   (e.g. "WC days 69→127 over 4 years, debtor days 107").
8. **"1 Thing to Track — Q1/Q2 FY27"** — a single **falsifiable** KPI with a numeric
   pass/fail line: *"If Q1 FY27 revenue is ~₹140+ Cr (35% growth) with skid contribution
   crossing 10%, the thesis holds. If not, re-evaluate."*
9. **Red-flags aggregation** — count + criticality (`2 Flags Detected — Non-Critical`),
   each flag with its history; plus an explicit **`✅ No Critical Red Flags`** panel that
   *names what was checked* (pledging 0%, auditor qualification, revenue concentration,
   RPT, consecutive earnings misses).
10. **Key management quotes** — speaker + role + call date (FY26 call, 2026-05-06) +
    topic tags ("On US Tariffs (Q2 FY26)").

**History layer**
11. **Annual financials table** (net margin, EPS per year) with footnotes on pre-IPO
    share count and the depreciation step-up.
12. **EPS — last 8 quarters as a card grid** with YoY % per card and event annotations
    (`US tariff shock`, `Record Quarter`), the anomaly card visually highlighted.
13. **Quarterly anomaly explainer callout** (why Q1 FY26 fell; no order cancellations).
14. **Consensus EPS beat/miss tracker** → rendered as an honest
    **`Consensus Data Unavailable`** panel naming the sources checked (Tickertape,
    Trendlyne, MoneyControl) and stating that beat/miss classification *cannot* be done.

> [!key-insight] The transferable value is the **honesty scaffolding**, not the prose
> The four devices that make this page trustworthy are nearly free to build and match
> this repo's existing labelled-degradation culture: the **data-score dial (8/11)**, the
> **`DATA N/A` donut** (a missing axis renders as missing, not as a neutral 50), the
> **"Consensus Unavailable" panel** (states what it *checked*), and the **inline
> derivation footnote** on every projection. Copy these first — they cost hours, not days.

## Design layout & visual system (captured 2026-07-29)

> [!warning] Colours below are **eyeballed from the screenshots, not pixel-sampled**
> The images were pasted in-session, so no file was available to sample. Treat every hex
> as "≈" — a family, not a spec. The **semantic roles** are the reliable part; re-sample
> from an image file before hard-coding tokens.

### Layout geometry
- **Centred content column** (~1000px of a ~1370px viewport), everything else gutter.
  One column of stacked **section cards**, ~20–24px vertical gap between them.
- **Section card**: dark panel, ~1px hairline border, ~10–12px radius, ~20px padding.
  Sub-cards nest inside with the same recipe one step lighter.
- **Grids**: 6 signals = 3 × 2 · EPS quarters = 4 × 2 · strengths/risks = 2 side-by-side
  cards. All equal-width, equal-height cells — the grid *is* the comparison.
- **Sticky shell**: header + metric strip stay pinned (identical across all four
  screenshots while the body scrolls); the strip closes with a full-width bottom rule.

### Type system
- **Company name**: serif display, warm gold, ~24px — deliberately editorial, the only
  serif on the page.
- **All figures**: monospace (price ~40px; metric values ~16px; card values ~22px).
  Numbers never in the body face.
- **Micro-labels**: uppercase, ~10–11px, letter-spaced ~0.08em, muted slate
  (`52W RANGE`, `MKT CAP`, `Q1 FY25`, `DATA SCORE`).
- **Section headers**: `• SECTION NAME` — a small amber dot, then uppercase letter-spaced
  slate. Used verbatim for all eight sections seen.
- **Body prose**: sans, ~13–14px, muted light-slate (≈`#a8b2c1`), ~1.55 line-height. Bold
  coloured **lead-in labels** open each strength/risk/flag item ("Zero-Debt + Strong OCF:").

### Semantic colour language (consistent across all four screens)
| Role | Hue (≈) | Where it appears |
|---|---|---|
| Primary accent / caution / neutral-positive | amber-gold `#e8b96a` | company name, section dots, active tab + underline, data-score arc, `MODERATE`, `SLOWING`, `AVERAGE`, `INVEST. PHASE`, watch-panel border, quote accent bar |
| Good / confirmed | green `#3fb950` · teal `#2ea88a` | `D/E 0.02×`, `Net Margin 12.6%`, `▲ YoY`, bull scenario bar, `Record Quarter` border, `✅ No Critical Red Flags` panel |
| Risk / stretched | red-pink `#f0526a` | `OVERVALUED` donut, `▼ −1.47%`, `−42.7% YoY`, bear bar, `Extreme Valuation Risk`, `Consensus Data Unavailable` panel, 🚩 |
| Informational / watch | cyan `#4aa8c8` | sector chip, `FY27 Watch: SKID RAMP`, base-case bar, the tariff quote's accent bar |
| Absent / muted | slate `#7d8799` | micro-labels, body prose, `DATA N/A` arc |
| Surfaces | page ≈`#0b0e14` · card ≈`#131a26` · border ≈`#232a3a` | — |

Two rules fall out of this and are worth keeping: **a value's colour states its verdict**
(P/E 95.7× is amber *because* it's stretched, D/E 0.02× is green *because* it's clean), and
**border colour + weight encodes emphasis** — 1px hairline = normal card, 2px amber all
round = highest emphasis ("1 Thing to Track"), 2px amber top-rail = verdict card,
amber-bordered inner panel = watch, green-bordered = clean, red-bordered = data missing.

### Component recipes
- **Donut** (×7: 6 signals + data-score) — partial arc, ~28px radius, ~6px stroke, dark
  track, arc coloured by verdict; centre holds the mono value (`8/11`) or nothing; verdict
  word below **in the arc's colour**; then one small grey line naming the metrics that
  justified it (`P/E 96×, PEG 4.79×`). `DATA N/A` = faint slate arc + 🚩 caption.
- **Chip / pill** — ~99px radius, translucent tint of its hue + 1px border of the same hue,
  ~11px text. Two kinds: classification (sector / `SMALL CAP` / `80% EXPORTS` /
  `✔ WEB-VERIFIED DATA`) and verdict (`Entry: OVERVALUED`, `Business: GOOD QUALITY`).
- **Scenario bar** — label row (`Bull Case (CAGR 28.75%)` in the scenario's hue, left) +
  right-aligned `₹943 Cr · Margin 23%`; then a gradient-filled bar, **width proportional
  to value**, with `₹943 Cr | NOPAT est. ₹163 Cr` set in mono *inside* the fill; grey
  derivation footnote under the whole group.
- **Quarter card** — micro-label (`Q1 FY26`) · big mono value · `▲/▼ N% YoY` in green/red ·
  optional annotation line (`US tariff shock` grey / `Record Quarter` green). Anomaly and
  record cards get a coloured 1px border; all others hairline.
- **Callout panel** — left 3px accent bar + bold coloured lead-in + grey body
  (`Q1 FY26 anomaly:`). Same recipe for quote blocks, with speaker name as the lead-in.
- **Tab bar** — uppercase letter-spaced items with a `⊙` glyph prefix, muted; active item
  amber with a 2px amber underline.

> [!key-insight] The mockup's chrome is our **chart tool's** theme, not our dashboard's
> The report is dark editorial (page ≈`#0b0e14`, gold, monospace figures) — which is
> almost exactly [chart_dashboard.html](tools/chart_dashboard.html)'s existing token set
> (`--bg-page: #0d1117`, `--bg-header: #161b22`, `--bg-pane: #131722`, plus a light
> variant). The **Streamlit dashboard is the opposite**: its 19 `unsafe_allow_html`
> surfaces are a cream/brown theme (`#fff8e1`, `#f7efe3`, `#fde0c0`, `#8d6e63`). So the
> dark skin is **not** free on the analyzer page — porting it wholesale would clash with
> every existing card. Take the **structure + semantic roles**, map them onto the
> dashboard's existing hues, and keep the dark palette only if the report is ever built
> as an HTML surface served by `chart_server` (where it's already themed).

## Current State (grounded audit, 2026-07-29)

| Mockup component | What we have today | Where | Gap |
|---|---|---|---|
| Header: price, %chg, as-of | ✅ | `cached_fetch_ohlcv` in [dashboard_app.py](tools/dashboard_app.py) | layout only |
| Sector / industry / mcap chips | ✅ | `fetch_fundamentals` in [stock_council.py](tools/stock_council.py) | cap-band + export-% labels are new (export % has **no source**) |
| Metric strip: P/E, P/B, D/E, ROE, div yield, mcap | ✅ | `fetch_fundamentals` | — |
| Metric strip: 52W range | ✅ | `facts["high_52w"/"low_52w"]` (`gather_evidence`) | — |
| Metric strip: **EPS TTM** | ⚠️ available, unmapped | yfinance `trailingEps` | one-line add |
| Metric strip: **ROCE** | ❌ | — | same gap [[analyses/Radar-Chart-Analyzer-Fit]] RC-2 and [[analyses/PEAD-Scanner-Roadmap]] 5.2 hit; **computable from yfinance statements** (EBIT ÷ (equity+debt)) — no screener.in needed |
| Verdict card + confidence | ✅ equivalent, technical-tilted | `judge()` verdict + `setup_intelligence` | needs a **fundamental** verdict + the good-business-vs-bad-entry split |
| **Data-score dial (N/M)** | ❌ | — | trivial: count non-`None` fields; high honesty ROI |
| 6 donuts: Valuation / Growth / Health / Returns | ✅ inputs exist | `fetch_fundamentals` (pe/pb/peg/roe/opm/npm/d2e/growth) | band-scoring + Plotly donuts (Plotly already a dependency) |
| 6 donuts: Capital Allocation, Earnings Consistency | ❌ | — | Capital Allocation needs cashflow (capex/FCF); Earnings Consistency needs consensus → **render `DATA N/A`** |
| **Annual + quarterly financial history** | ❌ **not fetched anywhere** | grep: no `income_stmt` / `quarterly_income_stmt` / `balance_sheet` / `cashflow` in `tools/` | the one real new data layer — **free, login-free yfinance**, just unused |
| 8-quarter EPS grid | ❌ | — | rides the same fetch (`quarterly_income_stmt`, `get_earnings_dates`) |
| Forward revenue/NOPAT scenarios | ⚠️ **wrong kind** exists | [projection.py](tools/projection.py) projects *price* (EW Fib / VCP / harmonic measured moves) | fundamental scenarios are new — but pure arithmetic on FR-1's revenue+margin history |
| Red flag: promoter-holding change | ✅ parser exists | `_parse_quarterly_holding` in [screener_scraper.py](tools/screener_scraper.py) (used by `promoter_profit_surprise.py`, `multibagger_candidates.py`) | wire into a per-symbol view |
| Red flag: promoter **pledge %** | ⚠️ gated | `fetch_fundamental_safe_symbols(sessionid, max_pledge_pct)` — needs a screener.in cookie, historically flaky | keep optional; never claim "0% pledge" without a successful fetch |
| Red flag: WC days / debtor days / −ve FCF streak | ❌ | — | computable from FR-1 balance sheet + cashflow |
| Red flag: auditor qualification · RPT · revenue concentration | ❌ **no source** | annual-report text only | must render **"not checked"**, never as ✅ clean |
| Consecutive earnings misses | ❌ structurally unavailable | established in [[analyses/PEAD-Scanner-Roadmap]] (no free NSE consensus) | adopt the mockup's N/A panel; **do not build** |
| Management quotes / concall | ❌ no infra | — | heaviest lift; manual-paste fallback |
| **Peers tab** | 🔜 already scoped | [[analyses/Peer-Comparison-Roadmap]] PC-1…PC-4 | reuse, don't duplicate |
| **Ownership tab** | 🔜 partially scoped | [[analyses/Decision-Support-Gating-Roadmap]] DS-2 (FII/DII/MF/Retail split) | reuse |

## The gap (what's actually new)
1. **A fundamental data layer** — one module fetching yfinance annual/quarterly
   statements + balance sheet + cashflow (free, no login, *currently unused in the whole
   repo*) and deriving 3Y/5Y CAGRs, per-year net margin, ROCE, debtor/WC days, FCF.
   This single piece unblocks the history tables, the scenarios, three red flags, **and
   dissolves RC-2's screener.in dependency.**
2. **Band-scoring for the 6 axes** — the same judgement work [[analyses/Radar-Chart-Analyzer-Fit]]
   flagged; must be **one shared scorer**, not a second opinion.
3. **The report surface** — tab shell, donut row, data-score dial, card grids, callouts.
4. **Scenario arithmetic** with the derivation shown inline.
5. **Three-state red-flag rendering** — FLAG / CLEAN (checked) / NOT CHECKED (no source).
6. **A shared style primitive.** The design section above is ~6 recipes reused ~40 times
   (card · chip · donut · scenario bar · stat card · accent callout). Today each of the 19
   `unsafe_allow_html` sites in [dashboard_app.py](tools/dashboard_app.py) hard-codes its
   own hexes inline. One `_report_css()` token block + helpers is the difference between
   this page looking designed and looking assembled — and it retro-tidies the existing
   surfaces.

## Evidence For
- **~75% composition.** Every valuation/quality metric, the verdict engine, the promoter
  parser, Plotly and the analyzer page already exist; the only new *data* is a
  login-free yfinance call we simply never made.
- **It is the missing lens.** Our stack is technical-heavy ([[analyses/Setup-Intelligence-Visual-Spec]],
  M1 /100); fundamentals are fetched as a snapshot and barely surfaced. Same argument
  that justified the radar — but this is the *page* the radar is one widget on.
- **FR-1 pays a debt twice over.** ROCE + 3Y/5Y CAGRs from statements retires the
  screener.in dependency that has blocked [[analyses/Radar-Chart-Analyzer-Fit]] RC-2 and
  [[analyses/PEAD-Scanner-Roadmap]] Phase 5.2.
- **The honesty devices are cheap and on-culture** — the repo already ships labelled
  degradation (M3's confidence floor → draw nothing; "Proxy-PEAD" naming). This page
  formalises it.

## Evidence Against
- **The prose is LLM-authored; we have no LLM.** The verdict paragraph, strengths/risks
  copy, quotes and "1 thing to track" are written text. No API key is configured anywhere
  in the repo (the M3 finding). So narrative must be **deterministic templates** over the
  same facts — or the section waits. Don't let a template pretend to be analysis.
- **Horizon mismatch.** This is a 15-year investor report; our stack is swing/position
  (Minervini, VCP, RS). Keep it a **separate tab** and never fuse it into the entry-timing
  verdict — "good business" must not read as "buy now" (the mockup itself splits them).
- **A fourth "Overall" is a real risk.** We already carry M1 technical /100, the RC radar
  mean, and the council verdict. This page adds `MODERATE` + a data-score dial. Fix by
  construction: **one `fundamental_score` module** feeds both the radar axes and these
  donuts; the data-score dial is explicitly a *coverage* meter, not a quality score.
- **Band calibration is judgement.** P/E 96× reading `OVERVALUED` is easy; NSE small-cap
  bands generally are not. Wrong bands = distrust (the M1-weights lesson).
- **Statement data for small/newly-listed caps is patchy** (the mockup's own pre-IPO EPS
  footnote proves it). Every derived figure needs a coverage flag, and the dial must
  actually fall when fields are missing.

## Phased plan (nothing built)
- **FR-0 — Style primitive (half a day, unblocks the look of everything else).** One
  `_report_css()` CSS-variable block + six helpers (`card`, `chip`, `donut`, `bar_row`,
  `stat_card`, `callout`) carrying the semantic roles from the design section — mapped onto
  the dashboard's **existing** hues, not the mockup's dark palette. Micro-label /
  mono-figure / section-header type rules included. Do this with FR-1 or immediately after;
  every later phase just calls the helpers.
- **FR-1 — Fundamental data layer + header & metric strip.** New `fundamentals_deep.py`:
  cached yfinance `income_stmt` / `quarterly_income_stmt` / `balance_sheet` / `cashflow`;
  derive 5Y & 3Y revenue/profit CAGR, per-year net margin, **ROCE**, debtor & WC days,
  FCF; map `trailingEps` / `bookValue` into `fetch_fundamentals`. Render the sticky header
  + 9-metric strip on the Stock Analyzer. *Foundation for FR-2…FR-5 and unblocks RC-2 /
  PEAD 5.2.* **Do this first.**
- **FR-2 — 6-signal donut row + data-score dial + verdict chips.** One shared
  `fundamental_score` (band → verdict word + the justifying metric line) consumed by
  **both** these donuts and [[analyses/Radar-Chart-Analyzer-Fit]] RC-1's axes. Absent
  axes render `DATA N/A` (never a neutral 50). Dial = coverage count N/M. Chips carry the
  good-business-vs-bad-entry split.
- **FR-3 — History surfaces.** Annual revenue/margin/EPS table (a comparison surface →
  table is correct here) + the **8-quarter EPS card grid** with YoY and auto-annotated
  anomalies (|YoY| beyond threshold → callout). Ships the "Consensus Data Unavailable"
  panel as *copy*, not a build.
- **FR-4 — Red-flag aggregation with three-state rendering.** Promoter-holding delta
  (existing parser) · pledge % (optional screener.in) · WC/debtor-day trend · negative-FCF
  streak; criticality classifier (Critical / Non-Critical / Watch). Unsourceable checks
  (auditor, RPT, concentration) render **"not checked"**. Never a blanket ✅.
- **FR-5 — Forward scenarios + "1 Thing to Track."** Bull/Base/Bear revenue & margin →
  NOPAT bars with the multiplier derivation printed inline; labelled *arithmetic
  extrapolation, not a forecast*, and visually distinct from `projection.py`'s price
  target. "1 Thing to Track" derived from the largest-variance driver with a numeric
  threshold — rule-based, template-worded.
- **FR-6 — Narrative & concall layer (last, optional).** Management quotes via concall
  links + manual paste; LLM narration only if an API key ever appears. Deliberately last,
  same discipline that put M3 after M1/M2.

**Tab mapping:** Valuation / Growth & Earnings / Health / Returns & Capital → FR-2 axes ·
**Ownership** → [[analyses/Decision-Support-Gating-Roadmap]] DS-2 · **Peers** →
[[analyses/Peer-Comparison-Roadmap]] PC-1…PC-4. The shell mostly *composes* work already
sequenced elsewhere.

## Packaging
**Native dashboard feature** — a Fundamentals report tab on the Stock Analyzer (same
decision as [[analyses/Radar-Chart-Analyzer-Fit]]): reuses our fetch layer + Plotly, works
without Claude. The mockup's own page is an LLM artifact; we take its **structure and
honesty devices**, not its generation model.

**Surface choice (open, recommendation recorded).** Two viable homes, and the design audit
above is what decides it:
- **(a) Streamlit page + `_report_css()` — recommended.** Everything stays on the Stock
  Analyzer beside the technical read; the 19 existing `unsafe_allow_html` sites prove the
  card/chip/grid recipes are achievable, and Plotly covers the donuts. Cost: the mockup's
  dark editorial skin is dropped in favour of our cream theme. **The layout survives; only
  the palette changes** — and the layout is the part carrying the meaning.
- **(b) HTML report page served by `chart_server`.** Reproduces the mockup near-exactly —
  [chart_dashboard.html](tools/chart_dashboard.html) already ships the dark tokens, a
  light/dark switch, and the sticky-header pattern. Cost: a second surface to maintain, an
  iframe or a tab away from the analyzer, and fundamentals data would need an endpoint.
  Only worth it if the dark editorial look is itself a requirement.

Pick before FR-0 — it's the one decision that's expensive to reverse later.

> [!done] **Surface decided 2026-07-30: (a) Streamlit + a shared style primitive.**
> Built as [report_style.py](tools/report_style.py) (`report_css()` + six helpers) rather
> than a `_report_css()` private in `dashboard_app.py`, so the chart tool or any future
> surface can import the same tokens. The dark editorial skin was dropped as predicted;
> the structure and the semantic roles carried over intact.

## Action Taken / Plan
- ✅ Ingested the 4 screenshots (2026-07-29) — **both layers**: the information
  architecture (14 components) *and* the design/visual system (geometry, type, semantic
  colour roles, 6 component recipes). Grounded audit filed; pointers added from
  [[analyses/Dashboard-UI-Roadmap]] Phase 2 and [[analyses/Radar-Chart-Analyzer-Fit]].
  **Nothing built.**
- ✅ **Surface decided + FR-0 & FR-1 SHIPPED 2026-07-30** (`0821fdb`) — see Outcome.
- ⏭ **FR-2 next** — the shared `fundamental_score` band scorer. FR-1 deliberately left
  valuation untoned so FR-2 owns *all* band judgement in one place.
- ⚠️ If the pixel-exact palette ever matters, **get the screenshot files onto disk** and
  re-sample; the hexes here are eyeballed.

## Outcome (fill in later)
- _2026-07-29: ingested & scoped. Grounded finding: **~75% composition, one new
  login-free data layer**. FR-1 recommended as the first PR; narrative/LLM sections
  (FR-6) deliberately last given no configured LLM._
- _2026-07-29 (same session, follow-up): **design layer added** after the user asked
  whether the layout was ingested too — it initially wasn't. Captured the visual system
  and found the theme conflict: the mockup's dark editorial chrome matches
  `chart_dashboard.html`'s tokens, **not** the Streamlit dashboard's cream theme. Added
  **FR-0** (shared style primitive) and an explicit surface choice ahead of it._
- **2026-07-30 — FR-0 + FR-1 SHIPPED, verified & deployed** (`0821fdb`).
  - **FR-1 — [fundamentals_deep.py](tools/fundamentals_deep.py)**, the first code in this
    repo to fetch yfinance's statements (`income_stmt` / `quarterly_income_stmt` /
    `balance_sheet` / `cashflow` — free, login-free, previously unused). Derives 3Y/5Y
    revenue & profit CAGR, per-year net margin & OPM, **ROCE**, debtor & working-capital
    days, FCF + negative-FCF streak, and a `coverage` meter (have/total/missing).
  - **The blocked dependency is retired:** ROCE = EBIT ÷ (equity + total debt) now comes
    from free data, so [[analyses/Radar-Chart-Analyzer-Fit]] **RC-2** and
    [[analyses/PEAD-Scanner-Roadmap]] **5.2** no longer wait on a screener.in session.
  - **FR-0 — [report_style.py](tools/report_style.py)**: `report_css()` token block + six
    helpers (card · chip · stat_card · bar_row · callout · donut). Semantic roles carried
    over from the mockup; palette mapped onto the dashboard's **cream/brown** hues as the
    design audit predicted. Donut is inline SVG — a dial, not a chart, so no Plotly.
  - **Surface:** built as a **module**, not a `_report_css()` private, so any surface can
    import the same tokens.
  - **Stock Analyzer now leads with** a sticky identity header (name · price · change ·
    sector/industry/cap-band/coverage chips · statement as-of) + a 9-metric valuation
    strip + a 5-metric statement-derived growth strip.
  - **Honesty devices are in the data layer, not the view:** missing is `None` (never a
    default), a CAGR through a loss is `None`, `available` reflects whether statements
    actually came back, 52W range renders `DATA N/A` on a <252-bar lookback rather than
    mislabelling a 60-bar range, and `coverage` is explicitly a *coverage* meter.
  - **Found & fixed a real unit bug while displaying it:** `fetch_fundamentals` multiplied
    `dividendYield` by 100, but yfinance 1.4.1 already returns a **percentage** — TITAN
    read **31%** (actual 0.31% = ₹15 on ₹4,850) and ITC **559%** (actual 5.59%). The
    sibling margin/growth fields *are* fractions and keep their ×100. No other consumer.
  - **Verified live:** ITC → P/E 17.25× · D/E 0.03× (green) · ROE 29.34% · ROCE 37.54%
    (prev 38.4%) · div yield 5.59% post-fix · net margin 26.45% · FCF ₹16,281 Cr · debtor
    days 18 · coverage **9/11** with both 5Y CAGRs correctly *not computable* (yfinance
    returns 4–5 annual columns; a 5Y CAGR needs six). TITAN cross-checked. Sticky header
    held across a 622px scroll; all 14 stat cards at equal width; zero console errors, no
    server exceptions.
  - **Deliberately NOT in this phase:** band-scoring. Only D/E, ROE and ROCE are toned,
    using floors this repo already states (High-Growth sliders, multibagger query).
    Valuation bands are FR-2's, in **one** shared `fundamental_score`.

## Related Pages
- [[analyses/Dashboard-UI-Roadmap]] — the analyzer this extends (Phase 2 features).
- [[analyses/Radar-Chart-Analyzer-Fit]] — the fundamental **radar**; must share FR-2's
  scorer, and RC-2's screener.in dependency dissolves once FR-1 lands.
- [[analyses/Peer-Comparison-Roadmap]] — fills this mockup's **Peers** tab.
- [[analyses/Decision-Support-Gating-Roadmap]] — DS-2 ownership split fills the
  **Ownership** tab.
- [[analyses/PEAD-Scanner-Roadmap]] — the no-free-NSE-consensus constraint this page's
  Earnings-Consistency `DATA N/A` inherits; Phase 5.2 fundamentals gap FR-1 closes.
- [[analyses/Setup-Intelligence-Visual-Spec]] — the **technical** counterpart panel; keep
  the two lenses (and their verdicts) labelled distinctly.
