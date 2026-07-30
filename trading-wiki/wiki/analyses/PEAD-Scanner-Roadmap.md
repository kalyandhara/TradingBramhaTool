---
title: "PEAD Scanner Roadmap (M5) — Post-Earnings Announcement Drift"
category: analysis
tags: [roadmap, scanner, PEAD, earnings, drift, NSE, dashboard]
created: 2026-07-23
updated: 2026-07-24
sources: 2
related: [analyses/Dashboard-UI-Roadmap, concepts/PEAD, concepts/Pocket-Pivot, concepts/VCP, concepts/ADX, sources/TV-PEAD-Screener-PineScript]
---

# Analysis: PEAD Scanner Roadmap (M5) — Date 2026-07-23

Beyond the M1–M4 UI spine ([[analyses/Dashboard-UI-Roadmap]]), **M5 opens a new
*scanner* track**: a Post-Earnings Announcement Drift (PEAD) scanner in the
Scanner Hub. PEAD is the well-documented tendency of a stock to keep drifting in
the direction of an earnings surprise for days-to-weeks after the report.

## Thesis

PEAD's core is two things only: an **earnings surprise** (the trigger) and
**drift** (continuation after it). Everything else people bundle in — VCP, ADX,
ATR breakouts — are *confirmation filters*, not PEAD itself. A scanner is
buildable on our existing pipeline, but its honesty depends entirely on the
surprise source.

## The central constraint (evidence against a "true" PEAD on NSE)

A *true* PEAD ranks by **SUE** = (actual EPS − consensus estimate) / σ. That
needs analyst consensus estimates. **Our Python data sources have none for NSE**
— documented in our own code ([screener_scraper.py](tools/screener_scraper.py)):
*"screener.in has no analyst-consensus 'profit surprise %' field … YoY Quarterly
profit growth is the closest real proxy … not a true estimate-vs-actual
surprise."*

**Correction (2026-07-23, after ingesting [[sources/TV-PEAD-Screener-PineScript]]):**
the "no consensus estimate" limit is a property of *our pipeline*, not the data
universe. TradingView's Pine exposes consensus via `request.earnings(…,
earnings.estimate)` and `request.financial(…, "SALES_ESTIMATES")`, so a
**TradingView-hosted** PEAD screener CAN compute true SUE/SURGE — subject to TV's
NSE estimate coverage, which is unverified and often sparse for Indian
mid/small-caps. **There is also an estimate-free path we CAN take today:
time-series SUE** (z-score of YoY EPS change from EPS history) — a real
standardized surprise that needs no analyst data. See Absorption below.

Decision (2026-07-23, user): build **NSE Proxy-PEAD** in our Python pipeline —
infer the event from price, stay honest about it — and upgrade the surprise from
"gap only" toward **time-series SUE** as EPS history is wired in.

## What we already had (evidence the build is cheap)

| PEAD ingredient | Status |
|---|---|
| OHLCV + gap detection | ✅ [data_source.py](tools/data_source.py) (yfinance + hyperliquid) |
| ATR filter | ✅ `_atr_series` / `compute_atr_filter` |
| VCP contraction | ✅ `scan_vcp` |
| Momentum continuation | ✅ `scan_momentum_continuation` |
| Scanner plug-in slot | ✅ `scan_*(df)->dict` + `SCANNERS` registry |
| **ADX** trend strength | ❌ not present — the one genuine gap (Phase 3) |
| **Consensus estimate** | ❌ not free for NSE — routed around via proxy |

## Phased plan

### Phase 1 — Gap-and-drift MVP (price-only) — ✅ SHIPPED 2026-07-23
`scan_pead()` in [scanner_templates.py](tools/scanner_templates.py), registered
as **"Proxy-PEAD Drift"** (category Momentum). Infers the earnings event from a
large high-volume up-reaction (≥1.5×ATR14, ≥4% close-to-close, ≥1.5× 50-day
median volume in the last 20 sessions) and fires only while the reaction is still
held/extending (drift). 0–100 score (surprise magnitude + drift + volume
conviction) tuned to the Hub strength pills; emits `vol_x50d` for the "Vol
Confirmed" pill. Renders as **cards** (not a table).

- **Honesty guardrail:** labelled "Proxy-PEAD" everywhere; every card carries the
  line "event inferred from the price gap, not a confirmed earnings date."
- **Verified live** through `run_scanner` over 30 liquid NSE names in Q1 earnings
  season → HCLTECH (+5.6% gap → +10%/15d, score 78), TCS (+5.4%, +3%/9d, 65),
  INFY (+5.6%, +1%/16d, 56). Bug caught + fixed: a NaN yfinance bar bypassed the
  gates (ULTRACEMCO "nan% gap", score 100) → fixed with `dropna` + `np.isnan`
  guards. See [[log]] 2026-07-23.

### Phase 2 — Confirm the event is really earnings
Pull NSE result dates via `yfinance.get_earnings_dates()` (returns the *date* for
`.NS` even when the surprise column is empty; **requires `lxml`**). Tag hits
`confirmed-earnings` vs `gap-only (unconfirmed)` — honest labelling instead of
silently guessing.

### Phase 3 — Real time-series SUE + confirmation filters
Upgrade the fundamental surprise from a proxy toward a **true time-series SUE**
(z-score of YoY EPS change). Data path is now unblocked:
- **Session-gating solved (2026-07-24):** `tools/screener_login.py` + `screener_login.bat`
  capture a valid screener.in `sessionid` via a Playwright login window and cache
  it; `get_screener_sessionid()` reads that cache first (Chrome app-bound cookie
  encryption made the direct browser read fail on Windows). See [[log]].
- **Depth is sufficient:** screener.in company pages carry ~12–13 quarters of EPS
  (vs yfinance's ~6) — enough YoY diffs to z-score credibly.
- **Remaining work:** add `fetch_quarterly_eps(session, slug)` (parser sibling to
  `_parse_quarterly_holding`); compute SUE (+SURGE/PE/PEG while on the page) in
  the **daily 4:05 PM batch**, cache per symbol; have `scan_pead` read the cached
  SUE (the scanner is symbol-blind at scan time, so this must be a pre-enrichment
  join, not an in-scanner fetch).

Also add an **ADX** filter (~20 lines; the one real gap vs the source
recommendations) plus optional ATR/VCP tags and YoY-profit-growth tiering.

### Phase 4 — Backtest the drift edge
Measure whether the drift is real on NSE using existing history +
[projection.py](tools/projection.py) patterns; tune the ATR/volume/drift-window
thresholds. Replace hand-set thresholds with measured hit-rates — the same
credibility gap flagged for the M1–M4 spine.

### Phase 5 — Quality-gated Small-Cap Proxy-PEAD (new composite scanner)
**Request (2026-07-24, user):** a scanner for **small-cap stocks that are Zero
Debt + High ROE / ROCE / OPM**, carrying the **PEAD drift advantage** — i.e.
earnings-drift *only in fundamentally clean small-cap compounders*.

**Why the combination is more than the sum.** PEAD is an under-reaction anomaly,
and under-reaction is **largest where analyst coverage is thinnest and the float
is smallest — exactly small-caps**. Layering a hard quality gate (no leverage,
high capital efficiency, fat margins) filters out the low-quality "gap-and-fade"
names where a post-earnings pop is a pump, not a re-rating. So the drift you keep
is more likely a genuine institutional re-rating of a compounder. This is the
quality-momentum / "Coffee-Can-meets-drift" sweet spot.

**The build is cheap because both halves already exist:**

| Half | Already built | Where |
|---|---|---|
| Quality small-cap screen (Mkt cap < ceiling, Debt/equity < 1, ROCE > 15, OPM > 10) | ✅ | [multibagger_candidates.py](tools/multibagger_candidates.py) — the exact screener.in query |
| ROE / ROCE / OPM floors as tunable gates | ✅ | High-Growth Screener page ([dashboard_app.py](tools/dashboard_app.py) — `hg_roe`/`hg_roce`/`hg_opm` sliders) |
| Proxy-PEAD drift engine (event inference + SUV + drift score) | ✅ | `scan_pead` ([scanner_templates.py](tools/scanner_templates.py)) |
| screener.in session to pull fundamentals | ✅ | `screener_login.py` / `get_screener_sessionid()` (Phase-3 unblock) |
| ADX / deeper-quality tiers | ❌ | shared with Phase 3 gap |

**The architectural key — combine at the *universe* level, not inside the scanner.**
`run_scanner` is symbol-blind (`spec["fn"](df)` runs on OHLCV only; the symbol is
attached *after* the fn returns — [scanner_templates.py](tools/scanner_templates.py)
`run_scanner`). The scanner therefore **cannot** read fundamentals per bar. But it
doesn't need to: the quality filter is a property of the *symbol*, so apply it as a
**pre-filter on the symbol list** before `run_scanner`, then run Proxy-PEAD over the
survivors. This sidesteps the exact plumbing problem that made Phase-3 SUE hard.

**Sub-phases (each independently useful):**

- **5.1 — Quality gate ∩ Proxy-PEAD — ✅ SHIPPED 2026-07-24 (on yfinance, not
  screener.in).** Registered scanner **"Quality Small-Cap PEAD"** (category
  Momentum) in [scanner_templates.py](tools/scanner_templates.py): a yfinance
  fundamentals gate (`fetch_fundamentals_yf` + `passes_quality_gate`) pre-filters
  the universe at the **symbol level**, then `scan_pead` runs on the survivors
  (`run_quality_pead`), attaching quality pills to each hit. Tunable in the
  Scanner Hub (market-cap ceiling, Max D/E, Min ROE, Min OPM, "require complete
  fundamentals" toggle).
  - **Deliberate deviation from the original plan:** this was scoped against the
    `multibagger_candidates.py` **screener.in** query, but the screener.in
    session-capture path was abandoned as too fragile on this machine (see
    [[log]] 2026-07-24 — the launcher's login window kept failing; a
    `UnicodeEncodeError` crash was fixed but the interactive capture still
    didn't land). **yfinance `.info` exposes marketCap / debtToEquity / ROE /
    OPM with NO login**, so the gate was built on that instead — the MVP no
    longer depends on the blocked session at all.
  - **Units pinned (verified live):** yfinance `debtToEquity` is **percent form**
    (95.4 ⇒ D/E 0.95), ROE/OPM/ROA are ratios. "Zero Debt" = D/E ratio ≤ 0.10.
  - **ROCE gap:** yfinance has no true ROCE (EBIT/capital-employed); `returnOnAssets`
    is carried as a **labelled ROA proxy**. Real ROCE stays a screener.in job → 5.2.
  - **Coverage caveat:** yfinance NSE fundamentals are patchy (many names return
    `None`); `require_complete=True` (default) drops names whose gate can't be
    verified — honest over permissive.
  - **Verified live:** gate correctly passed CAPLIPOINT (D/E 0.001, ROE 20, OPM 31,
    ₹18,753 Cr) and MAPMYINDIA, and rejected TATAELXSI (mcap > ceiling), JSWSTEEL
    & NESTLEIND (large-cap / high-debt). End-to-end `run_quality_pead` over 4 names
    → **MAPMYINDIA "Quality Small-Cap PEAD" score 84** (Zero-Debt ✓ · ROE 16% ·
    OPM 39% · +14.8% earnings-like reaction, SUV 11.5σ, drift intact) with the two
    failing names dropped before the OHLCV fetch.
- **5.2 — Register a dedicated "Quality Small-Cap PEAD" scanner + fundamentals on
  the card.** A thin wrapper scanner (category Momentum) that *is* Proxy-PEAD but
  presents the quality context. Attaching ROE/ROCE/OPM/D-E **to each card** needs
  the **same symbol→fundamentals pre-enrichment join as Phase-3 SUE** (fetch in the
  batch, cache per symbol, join before scan) — so 5.2 rides Phase 3's plumbing.
  Add a **quality tier** into the 0–100 score (or a separate "Quality" pill:
  Zero-Debt ✓ · ROCE ≥ 20 · OPM ≥ 15) so the Hub/M1 rollup can rank
  drift-in-quality above bare drift. Renders as **cards** (standing rule).
- **5.3 — Backtest the composite edge (rides Phase 4).** Test the specific claim:
  does the quality gate *improve* PEAD hit-rate/expectancy on NSE small-caps vs
  ungated Proxy-PEAD? If quality doesn't lift the edge, keep it as a risk filter,
  not a score booster — measured, not assumed.

**Honesty guardrails (same discipline as the rest of this track):**
- Still **Proxy-PEAD** — the event is inferred from price, not a confirmed
  earnings date. The quality gate does not upgrade it to "true SUE."
- **"Zero Debt" is operationalised as Debt/equity < 0.1**, not literally zero —
  label the pill accordingly.
- Fundamentals are screener.in's **latest reported quarter** — can be one quarter
  stale vs the price event; note it on the card.
- Small-cap liquidity: keep the existing volume/SUV gates so illiquid names that
  can't actually be traded don't score.

## Absorption — from the TradingView 8-criteria PEAD screener (2026-07-23)

Ingested [[sources/TV-PEAD-Screener-PineScript]] — a far more complete PEAD model
than our Phase 1. What to absorb, ranked by value/effort for our Python pipeline:

| Idea from the Pine screener | New to us? | Absorb into | Effort |
|---|---|---|---|
| **SUV z-score** (raw + log), `volume[1]` anti-leak baseline, 0.2σ floor, `[-10,20]` clamp | ✅ | **Phase 1.1 — ✅ SHIPPED 2026-07-24** — `_suv_series()` replaces the `vol_x50d` ratio gate with a real standardized-unexpected-volume z-score | Low |
| **Pre-D0 volume baseline** — anchor "normal" volume *before* D0 (trailing avg is contaminated by post-earnings bars) | ✅ | **✅ SHIPPED 2026-07-24** — baked into `_suv_series` (`shift(1)` window excludes the event + post bars) | Low |
| **Time-series SUE** — z-score of YoY EPS change (no analyst data needed) | ✅ | **Phase 3 (revised — NOT low-effort)** — see note below: scanner is symbol-blind + yfinance quarterly EPS is only ~6 quarters (too thin to z-score); needs deeper EPS history (screener.in) + a plumbing change | Med-High |
| **D0 refinement** — argmax `max(volZ,0) × range-expansion` within ±1d of the earnings date | ✅ | **Phase 2** — sharpen event anchoring once earnings dates are wired | Med |
| **% from D0 HIGH** (pullback-failure), −3% neutral floor | partial | refine `scan_pead` drift anchor (we use event *close*) | Low |
| **ATR drift from D0** — `(close − D0 close) / D0 ATR$ > 1.5, days ≥ 5` | partial | cleaner score than our event-bar `react/ATR` | Low |
| **CLV** (Close Location Value) + **3-tier institutional model** (Early/Mid/Late) | ✅ | **Phase 3+** — temporal accumulation scoring | Med-High |
| **Pocket Pivots** ([[concepts/Pocket-Pivot]]) counted since earnings | ✅ | **Phase 3** — new detector / confirmation tag | Med |
| **ADX/DI** trend strength + direction | ✅ (planned) | **Phase 3** — confirms the ADX filter we already scoped | Low |
| **Robustness patterns** — NaN `x!=x` guard, daily-only gate, sigma floors, output clamps | already partly done | hardening (we already added `dropna`/`np.isnan` after a live NaN bug) | — |

Two structural lessons worth carrying into every scanner: (1) **anti-leak
baselines** — never let the event's own bars pollute the "normal" it's compared
against; (2) the author marks uncalibrated thresholds *"directional convention
only, not statistically calibrated"* — the same honesty discipline we use, and a
reminder that **Phase 4 backtest** is what turns these into real numbers.

**Update 2026-07-24 — SUV shipped; why SUE could NOT be a quick win.** The
volume z-score + pre-D0 baseline landed in `scan_pead` (`_suv_series()`); the
gate is now SUV ≥ 1.5σ vs a 30-bar pre-event baseline instead of a raw
×-median ratio. Live re-run: HCLTECH (SUV 3.2σ) and TCS (2.2σ) held; **INFY
dropped** — its 1.66× median bump was under 1.5σ against its own baseline, i.e.
the z-score is correctly more discriminating than the ratio. Time-series SUE,
which I had billed as low-effort, turned out **not** to be: (a) `scan_pead` is
*symbol-blind* — `run_scanner` attaches the symbol only AFTER the scan fn runs,
so the fn cannot fetch EPS; and (b) yfinance `quarterly_income_stmt` exposes only
~6 quarters of EPS — ~1–2 YoY diffs, far too thin to z-score a σ credibly.
Forcing it would manufacture fake precision (the exact dishonesty we avoid). So
SUE stays Phase 3 and needs deeper EPS history (screener.in) plus a plumbing
change to pass the symbol/EPS into the scanner.

## Conclusion

Phase 1 is live and honest. The academic ceiling on NSE is capped by the missing
consensus-estimate feed, so the design leans on price + YoY-growth proxies and
labels itself as such. The highest-value next step is **Phase 4 (backtest)** —
until measured, every threshold here is hand-set.

## Action Taken / Plan
- ✅ Phase 1 shipped + live-verified (2026-07-23).
- ✅ Phase 1.1 (SUV z-score + pre-D0 baseline) shipped 2026-07-24.
- ⏭ Phase 2 (earnings-date reconcile) when `lxml` is installed.
- ⏭ Phase 3 (time-series SUE via screener.in EPS + ADX), Phase 4 (backtest).
- **Phase 5 (new, 2026-07-24) — Quality-gated Small-Cap Proxy-PEAD**
  (Zero-Debt + high ROE/ROCE/OPM small caps carrying the drift edge).
  - ✅ **5.1 SHIPPED** — **"Zero-Debt Quality PEAD"** scanner, built on **yfinance**
    fundamentals (no login) after the screener.in session path was abandoned;
    quality gate pre-filters the universe, Proxy-PEAD runs on survivors, pills on
    each card. Live-verified.
    - **Revised same day (user):** made **cap-agnostic** (all market caps by
      default; an "All market caps" toggle hides the optional small/mid-cap
      ceiling), added **PE + PEG** to the card alongside ROE/OPM/mcap (PEG falls
      back to a computed `PE÷growth` marked `~` when yfinance's vendor PEG is
      absent — sparse for NSE), and added optional **Max PE / Max PEG** valuation
      filters to the gate (0 = off). Renamed from "Quality Small-Cap PEAD".
  - ⏭ **5.2** — ~~true ROCE + deeper fundamentals from screener.in (needs a working
    session)~~ **unblocked 2026-07-30 — no screener.in session needed.** FR-1 shipped
    [fundamentals_deep.py](tools/fundamentals_deep.py) (`0821fdb`): `derive_fundamentals()`
    returns **true ROCE** (EBIT ÷ (equity + total debt)) plus 3Y CAGRs, margins, FCF and
    working-capital days from free yfinance statements. 5.2 is now "swap the ROA proxy for
    `roce` and widen the gate", plus the quality-tier score booster. Note the gate runs
    per-symbol, so budget four statement calls per name (cached 1h in the dashboard).
  - ⏭ **5.3** — backtest whether the quality gate lifts PEAD expectancy (rides Phase 4).

## Outcome (fill in later)
_TBD — pending one session of live use and a Phase 4 backtest._

## Related Pages
- [[analyses/Dashboard-UI-Roadmap]] — the M1–M4 UI spine this extends
- [[concepts/VCP]], [[concepts/ADX]] — confirmation filters
- [[log]] — build record
