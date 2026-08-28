---
title: "Open Backlog — the living index"
category: analysis
tags: [backlog, index, roadmap, open-items, measurement-debt]
timeframe: milestone-plan
created: 2026-08-07
updated: 2026-08-27
sources: 0
related:
  - analyses/Open-Backlog-2026-08-02.md
  - analyses/Backtest-Harness.md
  - analyses/OI-Momentum-Gap-Audit.md
  - analyses/Dashboard-UI-Roadmap.md
  - analyses/Noise-Regime-Coverage-Postmortem.md
---

# Analysis: Open Backlog — the living index

**Supersedes [[analyses/Open-Backlog-2026-08-02]]**, which is kept as the
historical snapshot it was.

**This page is deliberately undated in its filename.** The previous one carried
`2026-08-02` and was stale within five days — two items closed, one turned out
worse than recorded, and seven new ones appeared, while `index.md` still
described it as "the single index of everything left open". An index that goes
stale by construction is not an index. This one gets updated in place; dated
snapshots can be cut from it when a session wants one.

Statuses below were **re-verified against the code on 2026-08-27**, not carried
forward. The failure mode recurred exactly as predicted: on 2026-08-07 two items
had silently changed; by 2026-08-27 **six more had** — four P1 items the top
ledger closed on 2026-08-12 still carried full "still open" essays in the body
(B-25, B-20a, B-20b, B-7), B-5 was closed at the top but called "worse than
recorded" below, and B-11 (MFI) was filed "verified absent" while
`scan_mfi_oversold` had already shipped. The body now agrees with the code again.

## Status since 2026-08-02

| | |
|---|---|
| **Closed** | B-1 (2026-08-05), B-14 (`ephem` now installed), B-18 (remote pushed 2026-08-07), **B-2 (chart_server restarted 2026-08-12, /rsi_divergence.js HTTP 200)** |
| **Closed 2026-08-12** | **B-3** (mean-reversion scanner — `scan_mean_reversion` Connors RSI2, registered), **B-5** (time_stop emitted by 6 scanners: Harmonic/RSI60-40/OrderBlock/FallingWedge/SupportBreakdown/MeanReversion), **B-19b** (support-breakdown detector — `scan_support_breakdown` + `detect_support_breakdown`), **B-20a** (t-test + 95% CI on edge in `_aggregate`), **B-20b** (market-model beta/alpha when benchmark_df supplied to `backtest_scanner`), **B-25** (`backtest_confluence` + `format_confluence_report` measure co-fire vs single-fire), **B-7** (`sweep_volume_threshold` sweeps 1.0/1.2/1.5/2.0× vol floors and ranks by edge) |
| **Closed 2026-08-26** | **B-32** (regime output throttle — `_apply_regime_gate` + `REGIME_GATE`, premise proven `regime_backtest.py`), **B-33** (conviction-sized shortlist — score-floor replaces fixed `top_n`, floors data-calibrated), **B-36** (regime posture banner + Analytics→Research nav fold) |
| **Closed 2026-08-27 (re-verify)** | **B-11** (MFI — `scan_mfi_oversold` + `_mfi_series` shipped and registered; page had it "absent"). Ledger/body sync only: **B-5, B-25, B-20a, B-20b, B-7** were already code-complete but mis-filed as open in the body |
| **Still open** | B-4/B-12, B-6, B-8, B-9, B-10, B-13, B-15, B-16, B-17, B-19, B-21, B-21b, B-22, B-23, B-24, B-26, B-27, B-28, B-29, B-30, B-31 |
| **Open — residual only** | **B-34** (small-cap lane built; quality overlay + dashboard lane + hit-rate backtest remain), **B-35** (family-lens UI, not started), **B-37** (volume share-card, not started), **B-38** (delete-funnel shipped; blocked only on point-in-time fundamentals for the full backtest) |
| **New 2026-08-27** | **B-32r** (calibrate exact regime floors — currently heuristic) |
| **Closed 2026-08-27** | **B-36r** (Screening nav trim — Breakout Screener + TradingView Screener folded into one "Breakout Scans" page with a source toggle; 8 → 7) |

## Ingested-research additions (2026-08-20)

Four items below (B-28…B-31) come from a batch of trading videos ingested into the
separate research vault this session (option seller/buyer talks, an astro "Pushya"
video, and an AI-systematic-trading talk). Only the concepts that survive this
backlog's own test — *does it name a build, and can the claim be measured?* — were
promoted. The conceptual-only ones (option buyer-vs-seller economics, LLM-assisted
dev workflow, intraday "wave theory") were **deliberately not added**: they change how
you think, not what the tool does. Every promoted item carries the same
measurement-first caveat as the rest of this page — a new signal is a hypothesis
until the harness says otherwise, and the ingested sources are promotional, so their
own win-rate claims earn zero weight here.

---

## P0 — Live right now

### ~~B-2 · chart_server restart pending~~ — CLOSED 2026-08-12
Restarted via the preview_start tool. `/rsi_divergence.js` confirmed HTTP 200 in the server log.

### ~~B-18 · Nothing pushed, and there is nowhere to push to~~ — CLOSED 2026-08-07
`origin` → `github.com/kalyandhara/TradingBramhaTool` (private). All 88 commits
of history pushed; `master` tracks `origin/master` at 0 ahead / 0 behind. The two
stale `claude/*` worktree branches were deliberately left local.

**Two corrections to how this item was originally written**, both worth keeping
because the item overstated its own case:

- *"No off-site copy"* was **wrong**. The working tree lives under
  `C:\Users\Owner\OneDrive\…`, so OneDrive has been replicating it — including
  `.git` — all along. The real exposure was never "no copy".
- **The actual risk was the opposite of the one stated:** a live `.git`
  directory sitting inside a continuously-syncing OneDrive folder is a known
  corruption hazard. A proper remote fixes that by giving history a home the
  sync engine does not touch, which is a better reason than the one first
  recorded.

**Still to confirm (cannot be verified from here):** that the GitHub repo is set
to **Private**. No `gh` CLI is installed and no API auth is available in-session,
so repo visibility was taken on trust. Check it at Settings → General →
Danger Zone. The wiki carries market views, trading philosophy and research
notes; none of it is credentials, but none of it is meant to be public either.

**Pre-push audit (2026-08-07), recorded so it is not re-done from scratch:**
`.gitignore` excludes `*.db`, `*.csv`, `*.xlsx`, `*.json`, `.env`, `raw/` and
`tools/cache/` (captured screener.in session cookies). A credential scan over all
345 tracked files returned exactly one hit — `first_token = bare.split()[0]` in
`chart_server.py`, a variable name, not a secret. No personal positions in the
vault. 40 MB total.

### B-16 · OI Momentum off-palette colours
`_strength_color` at [dashboard_app.py:9747](tools/dashboard_app.py:9747) (moved
from 6648) still carries hard-coded hexes of the kind removed everywhere else.
Still open on 2026-08-27 — noted originally because that page was edited four times
on 2026-08-07 without anyone fixing it; proximity is not the same as attention.

---

## P1 — The measurement debt

**The dominant theme, and 2026-08-07 made it larger rather than smaller.** Every
feature shipped that day annotates or refines a grade that has itself never been
validated.

### B-19 · Nothing shipped in the 2026-08-07 session is backtested
The OI quadrant, PCR, RSI divergence, family-capped confluence and the level
tags are all unmeasured. Each is *labelled* as such in its own UI, which is the
minimum honest thing, but the stack is now several layers of unvalidated
refinement on an unvalidated base.

### ~~B-25 · Confluence itself is unmeasured~~ — CLOSED 2026-08-12
`backtest_confluence` ([backtest.py:431](tools/backtest.py:431)) replays scanners
co-firing vs single-firing, reports per-horizon `lift_ttest` (Welch, one-sided)
and a `premise_supported` verdict. The co-firing-beats-single-firing premise is
now testable; running it on the live scanner set is a B-19 measurement task, not a
build.

### ~~B-20a · The harness has no significance test~~ — CLOSED 2026-08-12
`_ttest_edge` ([backtest.py:279](tools/backtest.py:279)) attaches a t-stat / p /
95% CI to every edge (`edge_ttest`) and the report stars `p<0.05`. Point estimates
now carry a stated probability of being noise.

### ~~B-20b · Edge is not risk-adjusted~~ — CLOSED 2026-08-12
Market-model alpha shipped: a 60-bar pre-signal β per name feeds
`alpha = raw_ret − β × mkt_ret` with its own `alpha_ttest`
([backtest.py:322](tools/backtest.py:322)), falling back to β=1 only when β is
unknown. Supply `benchmark_df` to `backtest_scanner` to get risk-adjusted edge.

### B-21 · Single-window, no costs
One ~6y window, survivorship-biased, gross returns. Needs walk-forward and
transaction costs before any scanner is called validated.

### B-29 · No slippage/cost model — the realistic-fill technique *(ingested 2026-08-20)*
`backtest.py` states its own limitation out loud: gross returns, `no-costs-slippage`
([backtest.py:30](tools/backtest.py:30), and in the `limitations` list at
[backtest.py:368](tools/backtest.py:368)). The systematic-trading talk's concrete fix
is **not a fixed haircut** — it replays the *actual order-placement logic* the live
path uses (market vs limit, price offset, re-quotes) and reads the fill off that, then
budgets **~70-80% of backtest returns** after costs/STT/latency. This is the
execution-realism half of B-21; do it *with* the walk-forward, not instead of it. The
same talk's other lesson is a warning, not a task: sweeping "crores of parameter
variations" on a millisecond engine makes overfitting **cheaper**, and realistic
slippage does not rescue an over-fit signal — only the out-of-sample split and
pre-registered rule (B-20a/B-21) do. So B-29 raises the bar for *realism*; it does
nothing for *significance*, and must not be mistaken for it.

### ~~B-7 · Volume-confirmation threshold sweep~~ — CLOSED 2026-08-12
`sweep_volume_threshold` ([backtest.py:595](tools/backtest.py:595)) sweeps
1.0/1.2/1.5/2.0× vol floors and ranks by edge. The five conflicting repo values
can now be settled empirically; picking the winner and writing it back to the
scanners is a follow-up, not a build.

### B-8 · Stops in mean reversion — the Connors contradiction
### B-9 · Volume Profile 80% rule
Both fully specified, both still taken on faith.

---

## P2 — Capability gaps (the tool contradicts its own advice)

### B-3 · No mean-reversion scanner
`REGIME_PLAYBOOKS["SIDEWAYS"]` prescribes one and nothing implements it.
Re-checked 2026-08-07: the registry's nearest names — Pullback Entry, Early
Reversal Detector, Harmonic Reversal — are with-trend entries or reversal
*structure*, not the Connors-style stretch-and-revert the playbook means.

### ~~B-5 · Time stops: plumbed, and emitted by nothing~~ — CLOSED 2026-08-12
The 2026-08-07 finding was that `time_stop` was consumed by `backtest.py` but
written by no scanner (zero occurrences in `scanner_templates.py`). Re-verified
2026-08-27: **9 occurrences in `scanner_templates.py`** — six scanners
(Harmonic/RSI60-40/OrderBlock/FallingWedge/SupportBreakdown/MeanReversion) now
emit it and the harness reads a field that is actually written.

### B-19b · No support-breakdown detector exists anywhere
New 2026-08-07, found while building the OI level linkage. Verified: **zero
occurrences** of breakdown detection in the codebase. We detect resistance
breaks and have nothing for the mirror, so the **bearish half** of the standard
confirmation rule (price down + OI up + volume up + *support breakdown*) has
nothing behind it but range position. This also explains why composing
`scan_structural_breakout` into the OI table reached only 7% of rows.

### B-4 / B-12 · AVWAP anchors only to swing lows, no click-to-anchor
Anchor choice is the most subjective and most critical part of AVWAP and we
automated it away, so earnings / breakout / IPO / macro anchors are unreachable.

### B-6 · Retest entries barely modelled
Recorded repo asymmetry: **we detect breaks well and retests poorly.**

### ~~B-11 · MFI absent~~ — CLOSED (shipped; found 2026-08-27)
No longer absent: `_mfi_series` ([scanner_templates.py:2307](tools/scanner_templates.py:2307))
+ `scan_mfi_oversold` ([scanner_templates.py:5073](tools/scanner_templates.py:5073))
ship an MFI(14) oversold-recovery scanner, registered as "MFI Oversold Recovery".
The page had this "verified absent 2026-08-07" — it shipped since and nobody moved
the item. Like every scanner here it is unmeasured (folds into B-19).

### B-28 · No strike-level OI support/resistance or max pain *(ingested 2026-08-20)*
We read OI at the *underlying* level (momentum quadrant, PCR) but nothing reads the
**strike-by-strike** OI distribution as levels. Verified 2026-08-20: no `max_pain` /
per-strike OI anywhere in `tools/`. The ingested option-trader talks describe the
concrete read: **put-writer strikes act as support, call-writer strikes as
resistance**, with **max pain** as the magnet, and the actionable event is a heavy
**short-straddle breaking → short-cover rally** (a defended wall that, once pierced,
fuels the move it was capping). This is the first concrete deliverable of **B-23**
("strike-level option OI — the largest remaining OI item, needs its own design pass"):
a max-pain + OI-wall S/R overlay, fed by a per-strike chain. Prerequisite is the
per-strike feed B-23 scopes. Measurement caveat, same as everything here: "the wall
rejects the first touch" is a testable, unproven claim — ship it as
**levels-with-context**, label it unmeasured, and event-study it (first-touch
rejection vs a matched non-wall strike) before it grades anything.

---

## P3 — Consistency and correctness debt

### B-24 · Two RSI-divergence implementations that disagree
`detect_bullish_rsi_divergence` in `scanner_templates.py` uses a **rolling-mean
RSI** (not Wilder), tests *last bar vs min of prior 10* rather than swing pivots,
and covers **1 of the 4** variants — while `rsi_divergence.js` shipped
2026-08-07 does all four off shared zigzag pivots. The Python one feeds Early
Reversal's score, so the chart and the scanner will disagree about the same
chart. The JS/Python split is unavoidable; the *definitions* diverging is not.

### B-26 · `MIN_PRICE_PCT` contradicts its own stated rationale
The comment says the floors "sit just above those medians". Measured over 12
sessions that is true of `MIN_OI_PCT` (1.5 against a 1.43 median) and **false of
`MIN_PRICE_PCT` (0.5 against a 0.90 median)** — the price floor is far more
permissive than documented. Deliberately left unchanged, because altering it
would silently re-grade the whole stock universe; recorded in the module so the
rationale stops misleading. Decide it on purpose rather than by inheritance.

### B-21b · Every floor set on 2026-08-07 came from one session
PCR percentile cuts and liquidity floors, the 1.0× rvol veto, the 5-session
volume window, and the index OI floors were each calibrated on a single day's
cross-section (or 12 sessions in the index case). All are labelled as such in
code. **One session is not a distribution** — re-measure before trusting them.

### B-10 · Four Nifty-500 symbols uncached
Re-verified 2026-08-07: still **496** symbols cached. `ABBOTINDIA`, `BAYERCROP`,
`MCX` return *"no filings"* and `BSE` has no cache file, though all four are
large, liquid and certainly file. First suspect remains the
`f["symbol"].upper() == symbol.upper()` filter in `get_shareholding_filings` —
**probably our bug, not NSE's.**

---

## P4 — Scoped elsewhere, or small

| | Item | Notes |
|---|---|---|
| B-20 | **Index PCR has no history, so no band** | `index_reading()` ships deliberately unbanded. Five same-day observations cannot be ranked; an index can only be ranked against its own past. Storing a daily index PCR is the whole fix. |
| B-22 | **Sentiment Index factor 5 unwired** | `pcr.py` exists and is the primitive that factor was always waiting for; nothing consumes it there yet. |
| B-23 | **Strike-level option OI** (OI audit Gap 3) | The largest remaining OI item. Needs per-strike treatment, not an underlying-level sum — its own design pass. |
| B-13 | AW-1…AW-4 astro weekly card | Good-to-have; AW-0 shipped. |
| B-15 | SR-7 Trendlyne backfill | Optional, only if XBRL coverage proves short. |
| B-17 | OBV has no wiki page | Verified absent; ships as a chart indicator, undocumented. |
| B-27 | **Wiki hygiene** | Index counters had drifted to two *different* wrong numbers (frontmatter 204/78, body 198/81, actual 226/91) — corrected 2026-08-07, but a lint should **compute** these rather than trust them. Also an empty brace-expansion artifact directory `{entities,concepts,strategies,sources,analyses}` in the vault, untracked and harmless. |
| B-14 | ~~`ephem` not installed~~ | **CLOSED** — verified `ephem 4.2.1` present 2026-08-07. The reversal calendar can now be rebuilt; that rebuild has not been run, and coverage still ends **2027-12-28**. |
| B-30 | **Moon-in-Pushya reversal event-study** *(ingested 2026-08-20)* | Astro video claims Moon-in-Pushya days (~13-14/yr) mark major Nifty reversals. We already cache `gurupushya`/`ravipushya` muhurat dates and run muhurat/vedha/newmoon backtests; this adds the *general* Pushya-transit claim as one more event-study, reusing `newmoon_levels_backtest.py` (first-touch reversal vs a **matched non-Pushya control**, permutation null, eclipse strip). Textbook base-rate trap — ~13-14 dates/yr against typical 300-600pt 2-day ranges — so **expect a null**, consistent with the newmoon and sbc-vedha nulls. Worth running only to retire it with evidence. |
| B-31 | **Learned / regime-adaptive confluence weights — NOT NEXT** *(ingested 2026-08-20)* | The "signal-fusion" talk suggests *learning* confluence weights from historical performance and adapting them by volatility regime (IV<HV → defensive). We already cap correlated families (`scanner_weight`) and carry a RISK-ON/OFF flag, but weights are hand-set. Deliberately parked: learning weights is refinement on the base **B-25/B-19** already flag as unvalidated. Gate: close B-25 (does co-firing beat single-firing at all?) and B-21/B-29 (costs, walk-forward) first. Recorded so the idea is not lost — not so it is built next. |
| ~~B-32~~ | **Regime-PRESCRIPTIVE output throttle** — ✅ **CLOSED 2026-08-26** | Premise proven (`regime_backtest.py`, ~7,400 bars): bullish edge +0.22 @20d RISK-ON vs **−1.78 RISK-OFF (p<0.005)**, and the RISK-OFF baseline was *positive* — the signals actively pick bull traps below the 200 SMA, not beta. Shipped as `opportunity_daily.REGIME_GATE` + `_apply_regime_gate` (regime score-floor + name cap, applied in `run()` and the dashboard live pipeline). Residual → **B-32r** (exact floors still heuristic). Full history in [[analyses/Noise-Regime-Coverage-Postmortem]]. |
| ~~B-33~~ | **Conviction-sized shortlist (kill fixed top_n=100)** — ✅ **CLOSED 2026-08-26** | Score-floor replaces the flat `top_n` cut inside `_apply_regime_gate`, so the list sizes itself to conviction × regime. Floors data-calibrated (`regime_backtest.py --calibrate`, 55 names + kept-vs-tail test): **RISK-ON** floor ≈50 genuinely sorts (kept +0.4–0.5%, tail negative); **MIXED** edge ≈0, floor 50 is a mild filter only (the earlier "+1.2%" was a 15-name artifact); **RISK-OFF** `min_rating=None` + hard cap 5, since higher-rated names do *significantly worse* than the tail there. Floors are data-set, not judgment. |
| B-34 | **Small/micro-cap "hidden treasures" lane** *(2026-08-23)* | The funnel universe is `fetch_bhavcopy_top_volume` = top-by-traded-value = **large-cap only**; small/micro-cap multibaggers never enter. `multibagger_candidates.py` exists but is a standalone screener.in-gated screen. Build: a **FREE** small-cap universe (NSE Smallcap-250 / Microcap-250 constituents — no cookie) run through the multibagger criteria **plus the now-free NSE promoter% + pledge% checks** (its header's "pledge not scrapable" caveat is obsolete), surfaced as a deliberately SMALL high-conviction lane. **Measurable:** coverage (names outside the top-value set) + forward hit-rate of the criteria vs a Smallcap-250 benchmark. Closes the owner's core coverage gap. **STARTED 2026-08-24:** `smallcap_universe.py` (free 502-name NSE Smallcap-250+Microcap-250 universe, 24h cache) + `smallcap_discovery.py` (ranks by free FII+DII accumulation-rate + promoter conduct + pledge veto from `ownership_cache`; `--force` backfill added). **Full backfill DONE 2026-08-24** — 499/502 scoreable, pledge populated for 97 names (69 vetoed >5%: AFCONS 100%, STAR 38%…); top-15 surfaces real microcaps (CORONA, STLTECH, ASTRAMICRO, UJJIVANSFB, MASTEK) the large-cap funnel can't see. *(Caught a CLI bug: `--limit` defaulted to 25 and silently capped the first "full" run — fixed.)* **Still TODO:** distinguish pledge 0% vs unknown via the `WhetherAnySharesHeldByPromotersAreEncumbered` boolean (398 names show pledge `None` = fact omitted when clean); quality overlay (ROCE/OPM/D/E); dashboard "Hidden Treasures" lane; the forward hit-rate backtest (the measurable claim). |
| B-35 | **Collapse 38 scanners into family "lenses" (UI)** *(2026-08-23)* | 38 scanners (13 Entry + 12 Pattern overlap on the same facts); the confluence **family** de-dup already fixes scoring but the UI still lists all 38 as independent choices. Build: default the Scanner Hub to a curated core, group the rest under their `SCANNER_FAMILIES` lens behind "advanced". **Verifiable invariant (not taste):** no unique hit is lost — every family stays reachable and the union of hits is unchanged. Behavioral noise reduction with a checkable guarantee. |
| ~~B-36~~ | **Regime posture header + nav consolidation** — ✅ **CLOSED 2026-08-26** | Regime-coloured posture banner atop the Opportunity Hub, pulled from the same `REGIME_GATE` it enforces (RISK-ON green "full run, rating ≥50" → RISK-OFF red "≤5 names — bullish signals below the 200 SMA LOSE"). Nav: folded the single-page Analytics group (Strategy Hub) into Research, 6 groups → 5, no page removed. Residual → **B-36r** (Screening-group trim, held for an owner usage call). |
| B-32r | **Calibrate exact regime floors** *(2026-08-27)* | The `REGIME_GATE` floors/caps shipped in B-32 have the right *direction* (measured) but the exact numbers are heuristic. Re-run `regime_backtest.py --calibrate` on a larger, walk-forward split once B-21 lands and set the floors from that, rather than the single-pass calibration. Small; gated behind B-21's out-of-sample split so the floors aren't fit on the same window they're tested on. |
| ~~B-36r~~ | **Trim the 8-page Screening nav group** — ✅ **CLOSED 2026-08-27** | Owner chose the safe fold: **Breakout Screener + TradingView Screener → one "Breakout Scans" page** with a Chartink/TradingView source toggle (`bscan_src` radio), 8 pages → 7. Same task (external new-high breakout feed), two providers — structural redundancy, not a usage guess, matching the Analytics→Research standard. Both feeds stay reachable; the two page bodies are unchanged, only re-guarded. `PAGE_GROUPS`/`PAGE_BLURBS` updated; file compiles clean. Further trimming of the *distinct* screeners (Scanner Hub / High-Growth / Screener / Other) was deliberately declined without usage instrumentation. |
| B-38 | **TechnoFunda delete-funnel as a watchlist noise sieve** *(2026-08-25)* | Wire [[strategies/TechnoFunda-Delete-Funnel]] as a subtractive 8-filter funnel over a watchlist/universe: growth 6–8Q · CFO-vs-PAT · leverage (incl. **interest coverage <3×**, currently absent) · ROCE/ROE ≥15% · governance veto (`red_flags.py` — plus the missing related-party/dilution flags) · >200 DMA · relative strength vs **index AND sector** · accumulation base + up-volume. Each filter only **deletes**; survivors are a *shortlist, not a buy list*. ~7 of 8 legs already exist (see the coverage map on the strategy page) — this is mostly **assembly + the 3 gaps**, not new primitives. **Measurable claim to test (via [[analyses/Backtest-Harness]]):** does the survivor set beat (a) the unfiltered leading universe and (b) any single filter alone, forward? If stacking the deletes doesn't beat the best single delete, the funnel is ceremony. Directly serves the noise-reduction thrust; pairs with B-32/B-33 (regime throttle + conviction-sized list). **STARTED 2026-08-25:** `technofunda_funnel.py` — data-injected engine (`build_context`→`run_funnel`), all 8 filters short-circuiting on first delete, per-stage drop-off report, strict missing-data policy; **interest-coverage + D/E gap CLOSED** at the data layer (`fundamentals_deep` `interest_coverage`/`debt_to_equity`, verified live: TITAN 6.76×/1.95, RELIANCE 6.12×/0.44). **Still TODO:** live wiring into the dashboard (inject `derive_fundamentals` + `red_flags.evaluate` + cached OHLCV + Nifty/sector 12m return), the F2 multi-year CFO/PAT ratio (needs OCF in the payload), ROE alongside ROCE, related-party/dilution flags, an explicit base-tightness detector for F8. **BACKTEST shipped 2026-08-25 (scoped):** `funnel_backtest.py` tests the **price sub-funnel (F6∧F7∧F8)** point-in-time — next-open→+h-close forward return, edge vs every-bar baseline, **Welch two-sample t-test** (scipy-optional, numpy normal-approx fallback), and a "does stacking beat the best single leg?" verdict; predicates imported from `technofunda_funnel` so the tested rule = the shipped rule. **Honest limit:** the fundamental legs F1–F5 are **not point-in-time testable** (yfinance serves only current statements → look-ahead), so the **full-funnel forward test is blocked on point-in-time fundamental data acquisition, not code** — now the single open item on the measurable claim. **DASHBOARD LANE shipped 2026-08-25:** "Delete Funnel" page under Screening — universe source (Watchlist / paste / top-volume, capped at 50), Strict toggle, threshold overrides, a **drop-off table** (where the universe died), **survivor cards** (8 filter chips + why-expander + Watchlist/Analyze/Roster actions), and a reject ledger; reuses the cached fundamentals-deep / red-flags / OHLCV / Nifty fetchers. **Nearly closed — only point-in-time fundamentals remain:** ~~F2 CFO/PAT ratio~~ (DONE 2026-08-25 — `cfo_pat_ratio` = ΣOCF/ΣPAT over ≤5 matched years; live TITAN 0.54, RELIANCE 2.25), ~~ROE~~ (DONE — `roe`/`roe_prev`, F4 now gates ROCE **and** ROE), ~~F1 acceleration read~~ (DONE — deletes profit-YoY-turned-negative), ~~test suite~~ (DONE — `test_technofunda_funnel.py`, 13 tests), ~~in-UI backtest~~ (DONE — "Backtest the price legs" expander on the Delete Funnel lane), ~~dilution flag~~ (DONE 2026-08-25 — `dilution_pct` share-count trend in `red_flags._check_dilution`; live YESBANK +20% flagged, TITAN clean; related-party stays honestly NOT_CHECKED, no free feed), ~~explicit base detector~~ (DONE 2026-08-25 — F8 now uses `detect_vcp_geometry`, heuristic only as fallback), and the point-in-time fundamentals for the full backtest. |
| B-37 | **"Volume is the story" unusual-volume share card** *(2026-08-25)* | A new **editorial infographic** template: pick the day's top RVOL names (today's volume vs 1-yr avg), render a 1200×675 dark-navy/amber PNG comparing 1-2 stocks — RVOL multiple + mini bar, turnover (₹Cr), **% of mcap traded**, price %, and a per-stock **trigger** (catalyst read from filings) with Q1 Sales/PAT growth, plus a "**THE CONTRAST**" callout (small turnover moving price harder than a large one = float/liquidity tell). Build on the **existing PIL pipeline** (`opportunity_report.render_png` + `report_style` tokens `rs.TOKENS`), fed by `volume_fetcher.py` for RVOL/turnover; catalyst + Q1 lines are hand-supplied (or pulled from the fundamentals cache), not invented. **Not a signal — a distribution artifact**, so it carries the same footer discipline as every export ("⚠ No Buy/Sell recommendation · SEBI Reg."). **Verifiable invariant (not taste):** every printed number reconciles to source — `turnover ≈ today_vol × VWAP`, `%mcap = turnover / mcap`, `RVOL = today_vol / 1yr_avg_vol` — the card must never show a figure it can't derive. Scoped small: one template function + a Scanner/Opportunity-Hub "Share this" button reusing the `_render_export_controls` download pattern. |

---

## Not started — each has a scoped first PR

| Track | First step | Roadmap |
|---|---|---|
| Falling Wedge | FW-1 scanner, then chart overlay | [[analyses/Falling-Wedge-Scanner-Fit]] |
| Market Sentiment Futures | MSF-1 global cues strip (login-free) | [[analyses/Market-Sentiment-Futures-Roadmap]] |
| Peer Comparison | PC-1 peer resolution + table | [[analyses/Peer-Comparison-Roadmap]] |
| Radar Chart | RC-1 single-stock radar, yfinance-only | [[analyses/Radar-Chart-Analyzer-Fit]] |
| Setup Intelligence | SV-1 radar + heatmap off existing subscores | [[analyses/Setup-Intelligence-Visual-Spec]] |
| Decision Support | DS-3 market × ownership matrix (both axes exist) | [[analyses/Decision-Support-Gating-Roadmap]] |
| Opportunity Hub | Phase 2 industry RRG · Phase 4 presets + backtest | [[analyses/Opportunity-Hub-Roadmap]] |
| PEAD | Phase 4 backtest · ADX filter | [[analyses/PEAD-Scanner-Roadmap]] |
| Backtest Harness | Dashboard surface (Ops tab) | [[analyses/Backtest-Harness]] |
| Fundamental Deep Dive | FR-6② LLM narration — **genuinely blocked, no API key** | [[analyses/Fundamental-Deep-Dive-Report-Roadmap]] |

---

## Thesis

The 2026-08-02 page's thesis was *"six bugs, zero exceptions — every one a
confident number with nothing behind it."* Five days on, that still holds and has
acquired a second half.

**Every bug found on 2026-08-07 was a number that could not be wrong out loud.**
A confluence count that treated five correlated scanners as five votes. A STRONG
index grade whose threshold sat above the p90 of the only population that could
earn it. A share card that clipped the sentence saying the market was RISK-OFF.
An "all-time high" computed from 400 bars. None threw an exception; all four
would have read as results.

The defence has not changed and is still cheap: **carry coverage with the data,
refuse to score below a floor, and calibrate on the population the grade can
actually apply to.**

The new half is this. **Measurement debt still exceeds feature debt — but its
shape changed.** As of 2026-08-27 the *harness* is no longer the gap: B-20a
(significance), B-20b (risk-adjusted alpha), B-25 (confluence lift) and B-7
(threshold sweep) all shipped. What remains is (a) **running** them on the live
scanner/confluence set — that is B-19, now a measurement chore, not a build — and
(b) the two credibility gates the harness still cannot supply on its own:
**walk-forward and realistic costs (B-21 / B-29)**. Until a scanner has been
through those two, "edge" is still an in-sample gross number. The regime work
(B-32/33/36) is the one place a claim was measured *before* it shipped — that is
the bar the rest of the stack has not yet cleared.

## Action Taken / Plan

**Suggested order (updated 2026-08-12):**

1. ~~**B-2** — one restart.~~ Done 2026-08-12.
2. ~~**B-20a + B-20b** — significance test and market-model edge.~~ Done 2026-08-12.
3. ~~**B-25** — measure confluence.~~ Done 2026-08-12 (`backtest_confluence`).
4. ~~**B-7** — volume threshold sweep.~~ Done 2026-08-12 (`sweep_volume_threshold`).
5. ~~**B-5** — time stops.~~ Done 2026-08-12 (6 scanners now emit `time_stop`).
6. ~~**B-19b** — support-breakdown detector.~~ Done 2026-08-12 (`scan_support_breakdown`).
7. ~~**B-3** — mean-reversion scanner.~~ Done 2026-08-12 (`scan_mean_reversion` Connors RSI2).

**Next (updated 2026-08-27):**

1. **B-21 + B-29 together** — walk-forward split + realistic costs. The single
   highest-leverage measurement item now that the significance/alpha/confluence
   tooling exists. Everything downstream (B-19 verdicts, B-32r floor recalibration,
   B-31's gate) waits on this. `no-costs-slippage` still appears in
   [backtest.py:368](tools/backtest.py:368).
2. **B-19** — actually *run* B-20a/b/B-25 on the live scanner + confluence set and
   record the verdicts. Now a chore, not a build.
3. **B-34 residual** — finish the small-cap lane (quality overlay, dashboard
   "Hidden Treasures" lane, the forward hit-rate backtest — the measurable claim).
4. **B-16** (OI momentum palette) and **B-24** (RSI-divergence Python/JS
   disagreement) — small correctness cleanups, land anytime.

**Parked / gated:** B-38 full-funnel test is blocked on point-in-time fundamental
data, not code; B-31 (learned weights) stays gated behind B-21/B-29; B-28/B-30 are
capability/research items behind the measurement work; B-35/B-37 (family-lens UI,
volume share-card) are noise-reduction/distribution polish with no dependency.

**What's done (2026-08-26):** the 2026-08-23 strategic thrust largely landed —
B-32 (regime throttle, premise proven first), B-33 (conviction-sized list), B-36
(posture banner + nav fold). B-34 is most of the way there. That leaves the
measurement gates (B-21/B-29) as the load-bearing next step.

## Outcome (fill in later)

## Related Pages

- [[analyses/Open-Backlog-2026-08-02]] — the snapshot this supersedes
- [[analyses/Backtest-Harness]] — where most of P1 lands
- [[analyses/OI-Momentum-Gap-Audit]] — source of B-19b and B-23
- [[analyses/Dashboard-UI-Roadmap]] — the M1–M4 spine
