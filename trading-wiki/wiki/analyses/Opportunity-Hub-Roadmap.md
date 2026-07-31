---
title: "Opportunity Hub Roadmap — the top-down Sector→Industry→Stock→Pattern→Entry funnel"
category: analysis
tags: [roadmap, opportunity-hub, sector-rotation, industry, funnel, dashboard, breakout, accumulation, candlestick]
timeframe: milestone-plan
created: 2026-07-25
updated: 2026-07-25
sources: 1
related: [analyses/Dashboard-UI-Roadmap, analyses/PEAD-Scanner-Roadmap, analyses/Sector-Rotation-Tool-Architecture, analyses/Sector-Watchlist, concepts/PEAD]
---

# Analysis: Opportunity Hub Roadmap — Date 2026-07-25

## Thesis

A competitor/peer dashboard post (2026-07-25, user-supplied) pitches an
**"Opportunity Hub"** — framed as a *smart market-selection agent* that runs the
top-down funnel:

> **Right Sector → Right Industry → Right Stock → Right Pattern → Right Entry**

The claim set: find sectors performing with the current trend, hot industries
within them, stocks showing early momentum / coming out of accumulation, near
breakout / retest / reversal zones, with candlestick + chart patterns
(consolidation breakout, trendline breakout, MBO, IPO breakout, ATH breakout)
and entry / exit / risk levels — serving intraday → long-term participants.

**The grounded finding of the 2026-07-25 audit: we already own almost every
building block. What we lack is the *funnel that connects them*.** Our dashboard
is bottom-up (pattern scanners over a flat universe) with a *separate, passive*
Sector Map. The post's whole value proposition is the top-down chaining — leading
sectors *drive* which stocks get scanned — and that orchestration does not exist
as a connected flow.

## Current State (grounded audit, 2026-07-25)

| Post element | What exists today | Where | Status |
|---|---|---|---|
| Sectors performing with the trend | Sector Map: heatmap (1D–1Y) + rotation quadrant (Leading/Improving/Weakening/Lagging RRG) — **index-level** | [dashboard_app.py](tools/dashboard_app.py) `Sector Map`; [[analyses/Sector-Rotation-Tool-Architecture]] | ✅ Have (index-level) |
| Hot **industries** within sectors | Industry captured per-stock, but only as a **filter column** — no industry leadership view | `screener_scraper.py`, `nse_shareholding_fetch.py` (Industry); dashboard filter | ⚠️ Data yes, analysis no |
| Stocks showing early momentum | Momentum Continuation · 52-Week High Leaders · CANSLIM RS | [scanner_templates.py](tools/scanner_templates.py) | ✅ Have |
| Coming out of **accumulation** | Base Formation scanner + block-deal / FII-DII accumulation intel | `scan_base_formation`, [block_deal_intel.py](tools/block_deal_intel.py) | ⚠️ Partial (no Wyckoff accumulation-emergence detector) |
| Breakout / retest / reversal zones | Structural Breakout (Approaching/Confirmed/**Retest**), Rounding Bottom, Early Reversal, Darvas | `scanner_templates.py` | ✅ Have |
| Candlestick patterns | Candlestick *charts* render; Early-Reversal uses a candle trigger — **no standalone candlestick-pattern detector** | `dashboard_app.py:527` (chart only) | ❌ Mostly missing |
| Consolidation / trendline / MBO / IPO / ATH breakout | Consolidation Breakout 6M–10Y ✅, Trendline ✅, High-Tight-Flag ✅; **no IPO-base breakout, no explicit ATH breakout, MBO undefined** | `scan_all_duration_breakout`, `/api/trendlines`, `scan_high_tight_flag` | ⚠️ ~half |
| Entry / exit / risk levels | `projection.py` + VCP/harmonic trade plans + M3 projection line | [projection.py](tools/projection.py) | ✅ Have |
| Intraday → long-term participants | Scanners are mostly swing/positional | — | ⚠️ Partial |

## The gap (what's actually missing)

**1. The orchestration (the core gap).** No page takes *"these sectors are
Leading → these industries are hot within them → run pattern + entry scans on
ONLY those stocks → rank the results."* Today the user must eyeball the Sector
Map, then separately scan the whole market in the Scanner Hub, then hand-cross-
reference. The "Opportunity Hub" *is* that missing funnel.

**2. Industry-level rotation.** We have industry tags but no industry-strength
ranking — the middle rung of the funnel.

**3. Three greenfield detectors:** candlestick patterns, IPO-base breakout,
explicit ATH (all-time-high) breakout. ("MBO" in the post is undefined — likely
"Mother Base/Momentum Breakout"; clarify before building.)

## Evidence For (why build it)
- **~80% is composition of shipped pieces** — same shape as the M4 Predictive
  Analysis page ([[analyses/Dashboard-UI-Roadmap]]): sector rotation, scanners,
  Overall Rating, and entry/stop/target all already exist; the funnel is wiring.
- **Directly addresses the user's stated pain** — "which stock should I buy" and
  "holding weak sectors, missing the next leadership theme." Top-down is the
  structural fix for both.
- **Turns a passive Sector Map into an actionable engine** — highest-leverage way
  to reuse the rotation quadrant we already ship.

## Evidence Against (why sequence carefully)
- **Sector→stock constituent mapping is a real data dependency.** Sector strength
  is index-level (`SECTOR_DISPLAY_NAMES`); mapping a leading sector to its
  tradeable constituents needs a stock→sector/industry map. We have Industry per
  stock (screener.in/NSE) but not a clean sector-index→constituents list — decide
  the join before Phase 1.
- **Over-promise risk.** The post reads as marketing ("the agent does the work").
  Keep the honesty discipline: the Hub *narrows and ranks*; the user validates and
  manages risk. Don't imply automated picks.
- **Performance.** Chaining rotation → industry → per-stock scans over a wide
  universe is many fetches; lean on the fundamentals/OHLCV caches and rank-then-
  drill (only scan the leading slices).

## Phased plan

### Phase 1 — The funnel MVP — ✅ SHIPPED 2026-07-25
A new **"Opportunity Hub"** page ([dashboard_app.py](tools/dashboard_app.py),
Screening group, first entry) driven by [opportunity_hub.py](tools/opportunity_hub.py):
1. Reads the **existing** Sector Rotation quadrant → takes the top-K **Leading /
   Improving** sectors.
2. Maps those sectors to their constituent stocks (via the stock→sector/industry
   map — resolve the data join first; interim: group the current universe by its
   Industry tag and rank industries by aggregate constituent momentum).
3. Runs the **existing** Scanner Hub scanners (breakout / momentum / base /
   reversal) on **only those stocks**.
4. Ranks hits by **M1 Overall Rating** + scanner score, attaches entry/stop/
   target from `projection.py`.
Ships the whole "Right Sector → Right Stock → Right Pattern → Right Entry" chain
with **no new detectors** — pure composition.

**How the constituent→sector mapping was resolved (the flagged dependency):**
yfinance `.info` carries `sector`/`industry` per stock (login-free), folded into
the same cached fetch as the quality gate (`fetch_fundamentals_yf`). So sector &
industry **strength is derived bottom-up** from the universe's own constituents
(mean momentum + breadth + count via `rank_groups`), in one consistent taxonomy —
no Nifty-index→constituents reconciliation needed. Momentum reuses the scanner
engine's own `_weighted_trailing_return` so the funnel and scanners agree on
"strength". **Verified live:** a 13-name cross-sector universe ranked Healthcare
top (+11% avg, 75% breadth) and Technology bottom (−18%, 0% breadth), drilled
Healthcare → CAPLIPOINT/SUNPHARMA/CIPLA/DRREDDY, and ran the chosen scanner on
just those; page renders end-to-end in an isolated dashboard boot. Caught & fixed
a trailing-NaN-bar bug (a NaN last-close poisoned momentum → the same `dropna`
discipline as scan_pead).

### Phase 2 — Industry-level rotation (the middle rung)
Compute an **industry strength/leadership ranking** (aggregate constituent RS /
momentum, RRG-style) so the funnel shows *Right Industry* explicitly, not just
sector→stock. Reuses the sector-rotation math one level down.

**Sibling view — Peer Comparison ([[analyses/Peer-Comparison-Roadmap]], ingested
2026-07-25).** Peer comparison is *this Phase inverted*: instead of ranking
industries, it fixes one anchor stock's **industry** and compares its constituents
head-to-head (RS/RSI/ADX/52w/Stage/Pivot + a peer score). It reuses the very same
`build_constituent_table` industry tags — the industry-drill and peer-compare views
should share that resolution layer.

### Phase 3 — The three missing detectors — ✅ SHIPPED 2026-07-25
All three are standard `scan_*(df)->dict|None` functions in
[scanner_templates.py](tools/scanner_templates.py), so they appear in **both** the
Scanner Hub and the Opportunity Hub (21 scanners total).
- **`scan_candlestick`** — fresh bullish candlestick on the LATEST bar (Bullish
  Engulfing / Hammer / Piercing Line / Morning Star) with volume confirmation and
  a pullback-location (EMA20) preference; scored modestly (a trigger, not a
  system). Category Entry.
- **`scan_ipo_breakout`** — first-base breakout for recently-listed names; recency
  read from *total* listing history (40–500 bars), new post-listing high out of a
  tight base on ≥1.5× volume, not extended. Category Pattern.
- **`scan_ath_breakout`** — TRUE all-time-high breakout (new closing high over the
  ENTIRE history, ≥250 bars so it isn't just a 1-year high), volume-confirmed, not
  extended, with a coiled-base bonus. Category Pattern.
- **Data-window fix (the real architectural piece):** the default fetch is ~300
  bars, which would make "ATH" a mere 1-year high and hide a stock's true listing
  age. Added a **`needs_full_history`** marker on the ATH & IPO scanners; both hubs
  now select `_scanner_fetch_fn()` → a full-history fetch (`days=6000` ≈ full
  listing) for marked scanners, default window otherwise. Verified `days=6000`
  returns real depth (RELIANCE 5,990 bars to 2002; recent IPOs their short full
  history — OLAELEC 488, SWIGGY 422).
- **MBO** from the post remains undefined → not built; clarify before adding.
- **Verified:** compile clean; candlestick fires on live data (RELIANCE Piercing
  Line, score 61); ATH & IPO fire on synthetic positives (ATH 79 w/ coiled base;
  IPO 87, ~101d listed) and correctly return None on negatives (non-breakout bar;
  600-bar too-old name). Zero live ATH/IPO hits today are genuine — Nifty is below
  its 200-SMA (few names at ATH), not a detector fault.

### Phase 4 — Participant modes + trust
- **Participant presets** (intraday / swing / positional / long-term / IPO / ATH)
  that retune the scanners + timeframes behind one selector.
- **Backtest** the funnel edge — does sector/industry gating actually improve hit-
  rate vs flat scanning? The same measured-not-assumed discipline as every other
  roadmap here.

## Action Taken / Plan
- ✅ Roadmap filed (2026-07-25) — this page (deliverable **A**).
- ✅ **Phase 1 SHIPPED** (deliverable **B**) — Opportunity Hub page + `opportunity_hub.py`, live-verified.
- ✅ **Phase 3 SHIPPED** — candlestick / IPO-base / ATH-breakout detectors (+ the
  full-history fetch marker), in both hubs, verified.
- ⏭ Phase 2 (industry-level rotation is partly here via the industry ranking; the
  RRG-style leadership scoring is the deeper piece), Phase 4 (participant presets +
  backtest — the biggest open credibility item).
- Sequencing rule (as with M1–M4): don't start Phase N until N-1 ships and gets
  one session of live use.

### Phase 1.5 — Automate it + persist the shortlist — ✅ SHIPPED 2026-07-31
Unplanned, and it came from the user saying **"I am not understanding the
Opportunity Hub"**. The diagnosis matters more than the feature: the Hub is a
**five-step** flow that **stores nothing**, so it can't be run the same way twice
and there is never a yesterday to compare against. Anything that hard to operate
reads as "I don't understand it".

[opportunity_daily.py](tools/opportunity_daily.py) runs the identical funnel
headlessly and writes a **top-10 into SQLite** (`daily_opportunities` in
[portfolio_db.py](tools/portfolio_db.py)), one row per symbol per date, so the
table is also a **track record**. `market_regime`/`market_verdict` are stored on
every row — a shortlist built under a sub-200-SMA tape must never later read as
though conditions were good.

**Ranking = location × confluence × quality**, and *scanners are weighted by
measured edge* — Falling Wedge / Harmonic Reversal / Order Block count double
because [[analyses/Backtest-Harness]] found the rest at or below a random-entry
baseline. **This is the first feature to actually spend the backtest's findings**
rather than just record them.

Also forced a good refactor: the M1 rating moved out of `dashboard_app.py` into
[rating.py](tools/rating.py) so the headless job and the interactive Hub cannot
drift apart — the same one-scorer discipline as `fundamental_score.py`.

> [!warning] The bug this surfaced — a throttled fan-out looks like a market result
> `build_constituent_table` fans `.info` across 8 threads; Yahoo answers the burst
> with **HTTP 401 "Invalid Crumb"**, and since failures are swallowed per-symbol
> the output is a **half-empty table**, not an error — sectors would then be ranked
> from whichever names happened to survive. First run: **0 of 60 tagged**. Now 4
> workers, a measured **tag rate**, and a 45s/2-worker retry below 35% (→ 78%).
> Same shape as the NaN forming-bar bug: *a data fault wearing a market result's
> clothes.*

**Open:** nothing schedules it yet — the 4:05 PM Task Scheduler job runs
`screener_pipeline`, not this. Registering a second task is a machine-config
change, left for the user to approve.

## Outcome (fill in later)
- **2026-07-25 — Phase 1 shipped & verified.** Bottom-up sector/industry ranking
  from yfinance tags + reused momentum; drill → existing scanner → Overall-Rating-
  ranked cards. Compile clean (3 files), full funnel logic tested on live data,
  page renders in an isolated boot. **Restart start.bat** to use it. Remaining:
  the genuinely-missing detectors (Phase 3) and a backtest of whether sector/
  industry gating beats flat scanning (Phase 4).

## Related Pages
- [[analyses/Dashboard-UI-Roadmap]] — the M1–M4 spine this composes on top of.
- [[analyses/Sector-Rotation-Tool-Architecture]] — the sector-strength engine Phase 1 reads.
- [[analyses/Sector-Watchlist]] — the sector/industry universe context.
- [[analyses/PEAD-Scanner-Roadmap]] — sibling scanner track; Quality PEAD is a candidate Hub scanner.
