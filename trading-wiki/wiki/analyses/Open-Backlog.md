---
title: "Open Backlog — the living index"
category: analysis
tags: [backlog, index, roadmap, open-items, measurement-debt]
timeframe: milestone-plan
created: 2026-08-07
updated: 2026-09-02
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
| **Closed 2026-09-01** | **B-21** (walk-forward OOS pooling + per-horizon stability), **B-29** (Indian delivery cost model ~29bps, applied everywhere), **B-39** (scipy-optional fallback) |
| **Closed 2026-09-02** | **B-16** (OI Momentum `_strength_color` → `rs.TOKENS`), **B-24** (RSI divergence Python/JS agreement — `detect_bullish_rsi_divergence` rewritten to Wilder RSI + pivot lows + 3-pt gap), **B-34** (small-cap lane complete — quality overlay + dashboard lane shipped earlier; hit-rate backtest measured → WEAK, see below), **B-42** (shared market-structure read — HH/HL/LH/LL sequence + state + premium/discount + sequence-vs-breaks `agreement`; invariant clean on 30 large-caps; residual **B-42r**), **B-41** (liquidity sweep / stop hunt — pools + bidirectional detector + Entry & Risk scanners, built on B-42's equal-level labelling; SMC stack complete at 44 scanners), **B-23** (strike-level option OI — `option_chain.py` max pain + OI walls for stocks AND indices, `/api/option_levels`; premise was stale, B-44 had already built the per-strike feed), **B-28** (the overlay — `oiwalls` indicator via `createPriceLine`, expiry selector, unmeasured caveat; residual **B-28r**) |
| **Closed 2026-08-27 (re-verify)** | **B-11** (MFI — `scan_mfi_oversold` + `_mfi_series` shipped and registered; page had it "absent"). Ledger/body sync only: **B-5, B-25, B-20a, B-20b, B-7** were already code-complete but mis-filed as open in the body |
| **Still open** | B-4/B-12, B-6, B-8, B-9, B-10, B-13, B-15, B-17, B-21b, B-22, B-26, B-27, B-30, B-31, B-35, B-37, B-28r |
| **Open — residual only** | **B-35** (family-lens UI, not started), **B-37** (volume share-card, not started), **B-38** (delete-funnel shipped; blocked only on point-in-time fundamentals for the full backtest) |
| **New 2026-08-27** | **B-32r** (calibrate exact regime floors — currently heuristic), **B-39** (pin `scipy` in requirements / make `backtest.py` scipy-optional — the hard import silently broke the significance stack on Python 3.14) |
| **New 2026-08-27 (strategy-coverage gaps)** | **B-40** (VWAP as a signal — **scanner SHIPPED same day**), ~~**B-41**~~ (**CLOSED 2026-09-02** — `detect_liquidity_pools` + `detect_liquidity_sweep` + both scanners; SMC stack now complete), ~~**B-42**~~ (**CLOSED 2026-09-02**; residual **B-42r** — the pivot_len 5-vs-15 split, to be settled on data). Intraday lane (ORB/DOM/scalping) recorded as an explicit out-of-scope decision. From the profitable-trader strategy-combination audit. |
| **Closed 2026-09-05** | ~~**B-44r**~~ **MEASURED → FALSIFIED, GEX retired** (magnitude convention inverted the pre-registered direction and what survives the 1/σ control flips sign between vol terciles — see below). **B-34r** *(new, shipped same day)* — **Hidden Treasures gained its first HARD gate**: `red_flags.py` (FR-4) wired into `smallcap_discovery`, critical flags veto, watch flags cost 6 pts, NOT_CHECKED never reads as a pass. Zero extra fetches (rides the quality overlay's payload; `sessionid=None` keeps screener.in dormant). **Vetoes 100 of 249 on Smallcap-250** — 59 negative FCF, 51 promoter stake reduction, 28 pledge, 5 dilution. Toggleable and every exclusion is listed, because the default is NOT settled: see **B-34r2**. |
| **New 2026-08-29** | ~~**B-43**~~ **BUILT + MEASURED → clean null** (flip edge ~0, negative on the long leg; beat buy&hold 0/23 — but fires 40% less often than the EVWMA cross, i.e. noise reduction without edge). Chart overlay kept, labelled FLIP not BUY/SELL. MCX still gated. From the Renko podcast ingest. ~~**B-44**~~ **BUILT + MEASURED same day → clean null** (see below); residual **B-44r** (is the naive dealer convention backwards for NSE?). From the Chris Kmer order-flow ingest. |
| **Closed 2026-08-27** | **B-36r** (Screening nav trim — Breakout Screener + TradingView Screener folded into one "Breakout Scans" page with a source toggle; 8 → 7) |
| **Measured 2026-08-27** | **B-25** first actually run (`backtest_confluence`, 13 bullish scanners × LIQUID_50): co-fire lift is significant **only at 60d (+0.38%, p=0.025)**, trivial + non-sig at 5–20d — confluence is *not* the additive swing-horizon edge the Hub premise assumes. Required installing `scipy 1.18.1` (backtest's hard scipy import was broken on Python 3.14) |
| **Shipped 2026-09-02 (not from the backlog)** | **Trending Stocks page** — `trending_stocks.py` + a Market-Intel page with four lenses: Price Movers (whole-market bhavcopy, turnover-floored), Volume Shockers (reuses `volume_anomaly` **with cause attribution** — the one lens the desk does better than the commercial screener it was modelled on), 52-Week and All-Time High/Low (computed from batched history over a bounded top-N-by-turnover universe, since NSE's UDiFF bhavcopy carries **no 52-week columns** — verified, 34 columns, none a range extreme). Requested from a screenshot of a commercial "Trending Stocks" page. **Deliberately NO "Most Visited" lens** — that is crowd page-view data from a site's own traffic logs, there is no free public feed for retail attention, and a proxy (delivery spikes, rank churn) would measure something else under the same label. Recorded as a decision, not an oversight, the same way the intraday ORB/DOM lane is. Two things the build forced: a **turnover floor**, without which the movers list is almost entirely penny stocks (a ₹3 share moving 19% is arithmetic), and a **cash-equivalent filter** reusing the chart's existing `isLikelyLiquidETF` definition, because a liquid ETF is *permanently* at its all-time high by construction and squatted on the first ATH run. |
| **Measured 2026-09-02** | **B-19** batch walk-forward on all 41 scanners (LIQUID_50, 3 windows, Indian delivery ~29bps): **0/41 stable** across all horizons; 11 show positive 20d edge but all UNSTABLE; strongest = %R Bottoming (+2.68% @60d, stable @20d+60d), Falling Wedge (+1.58% @60d); **most scanners show negative edge after costs**. 3 too-few-signals (High Tight Flag, Minervini VCP, RSI-Fibo Hidden Div). 3/5 risk scanners show bearish edge. Full table in `tools/cache/b19_verdicts/_summary_table.txt`. |

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

### ~~B-16 · OI Momentum off-palette colours~~ — CLOSED 2026-09-02
`_strength_color` now sources from `rs.TOKENS` (good/info/accent/absent) instead of
hard-coded hexes. The four colours track the shared palette and will follow any
future token change automatically.

---

## P1 — The measurement debt

**The dominant theme, and 2026-08-07 made it larger rather than smaller.** Every
feature shipped that day annotates or refines a grade that has itself never been
validated.

### ~~B-19 · Nothing shipped in the 2026-08-07 session is backtested~~ — **MEASURED 2026-09-02**
The OI quadrant, PCR, RSI divergence, family-capped confluence and the level
tags are all unmeasured. Each is *labelled* as such in its own UI, which is the
minimum honest thing, but the stack is now several layers of unvalidated
refinement on an unvalidated base.

**Batch walk-forward run completed 2026-09-02** — `backtest_all_scanners.py`, 41
scanners × LIQUID_50 (49 symbols), 3 OOS windows, Indian delivery ~29bps. Key
findings:

- **0/41 scanners are stable** across all four horizons (5/10/20/60d)
- **11/41 show positive 20d edge** but all marked UNSTABLE
- **Most scanners show negative edge after costs** — the ~29bps round-trip eats
  whatever gross edge existed
- Strongest candidates (positive at BOTH 20d and 60d): %R Bottoming (+0.55%/+2.68%,
  stable @20d+60d), Falling Wedge (+0.83%/+1.58%), HM Buy (+0.63%/+0.56%),
  Harmonic Reversal (+0.90%/+0.40%), IPO-Base Breakout (+0.54%/+0.58%),
  RSI Divergence Bull (+0.36%/+0.93%)
- 3 scanners never/barely fire on LIQUID_50: High Tight Flag (0), Minervini VCP (8),
  RSI-Fibo Hidden Div (11)
- 3/5 risk (bearish) scanners show bearish edge; 2 don't (Downside Risk, Support
  Breakdown)

**Implication:** the scanner stack is a **screening tool, not a trading signal**.
Individual scanners do not reliably beat costs on large-caps. The remaining
value is in coverage (surfacing names to look at) and the confluence premise
(B-25 showed co-firing adds a small edge at 60d). Scanner weight calibration
(B-8) and learned weights (B-31) are weakened — there may not be enough edge
to weight.

### ~~B-25 · Confluence itself is unmeasured~~ — TOOL CLOSED 2026-08-12 · **MEASURED 2026-08-27**
`backtest_confluence` ([backtest.py:431](tools/backtest.py:431)) replays scanners
co-firing vs single-firing, reports per-horizon `lift_ttest` (Welch, one-sided)
and a `premise_supported` verdict.

**First actually run 2026-08-27** — 13 bullish trend/breakout scanners (52w
High, Stage 2, ADX, Pullback, Momentum, VCP, Base, Structural Breakout, ATH,
RSI 60-40, Consolidation, Darvas, High Tight Flag) × `LIQUID_50`, days=1500,
co-fire ≥2, n=13,407 single / 5,921 co-fired bars:

| horizon | single% | cofired% | lift% | p(lift) |
|---|---|---|---|---|
| 5d  | +0.14 | +0.15 | +0.01 | 0.42 |
| 10d | +0.37 | +0.41 | +0.04 | 0.32 |
| 20d | +0.83 | +0.90 | +0.08 | 0.24 |
| 60d | +2.61 | +2.99 | **+0.38** | **0.025\*** |

**Verdict: premise SUPPORTED only at 60d, and marginally.** `premise_supported`
returns `True`, but that flag hangs entirely on the one significant horizon — at
the swing horizons the Opportunity Hub actually ranks on (5–20d) the co-fire lift
is trivial (+0.01 to +0.08%) and **not** significant (p 0.24–0.42). So confluence
is **not** the additive edge the ranking premise assumes over 5–20d; its only
measurable benefit shows up at position-trade horizons. Same caveats as B-21:
single ~6y window, gross, `LIQUID_50` is large-cap/survivorship-biased — so
even the 60d result is an in-sample point estimate until walk-forward + costs.
**Enabling fix:** `backtest.py` hard-imports `scipy`, which was **not installed**
on the project's Python 3.14 — the whole significance stack (this + B-20a) could
not import; `scipy 1.18.1` installed 2026-08-27 to unblock the run.

### ~~B-20a · The harness has no significance test~~ — CLOSED 2026-08-12
`_ttest_edge` ([backtest.py:279](tools/backtest.py:279)) attaches a t-stat / p /
95% CI to every edge (`edge_ttest`) and the report stars `p<0.05`. Point estimates
now carry a stated probability of being noise.

### ~~B-20b · Edge is not risk-adjusted~~ — CLOSED 2026-08-12
Market-model alpha shipped: a 60-bar pre-signal β per name feeds
`alpha = raw_ret − β × mkt_ret` with its own `alpha_ttest`
([backtest.py:322](tools/backtest.py:322)), falling back to β=1 only when β is
unknown. Supply `benchmark_df` to `backtest_scanner` to get risk-adjusted edge.

### ~~B-21 · Single-window, no costs~~ — CLOSED 2026-09-01
`walk_forward_scanner` splits each symbol's evaluable bar range into N non-overlapping
windows and pools the OOS results (signal-count-weighted average, not a full-tape re-run).
Per-horizon sign-consistency stability check (STABLE/MIXED/UNSTABLE) + degradation
metric (pooled edge vs best single window — regime-dependence detector). CLI: `--wf 3`.

### ~~B-29 · No slippage/cost model~~ — CLOSED 2026-09-01
`IndianDeliveryCost` dataclass models the actual NSE delivery cost structure: STT 0.1%
on sell, brokerage 0.03%/side, exchange turnover 0.00345%, GST 18% on brokerage+exchange,
stamp duty 0.015% on buy, slippage 0.05%/side — ~29 bps round-trip on a ₹500 stock.
Applied to BOTH signal AND baseline returns (fair comparison) AND to the R-simulation
(`_simulate_plan`). `FlatCost(bps)` preserved for backward compat. CLI: `--cost indian`
or `--cost 20`. Also closed **B-39** (scipy-optional): `_ttest_1samp` / `_ttest_ind`
fallback to a normal approximation when scipy is absent, mirroring `funnel_backtest.py`.

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

### ~~B-28 · No strike-level OI support/resistance or max pain~~ — **CLOSED 2026-09-02** *(ingested 2026-08-20)*
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

**OVERLAY SHIPPED 2026-09-02 — B-28 CLOSED.** B-23 supplied `option_chain.py`
(`max_pain`, `oi_walls`, `read_levels`) and `/api/option_levels`; this added the
chart layer.

Shipped as the `oiwalls` indicator (Levels & Projection group): call walls as red
resistance lines, put walls as green support lines, max pain **dashed** in purple
so it never reads as a barrier, with line weight following OI rank so the
heaviest wall is the heaviest line without needing the numbers. The card carries
the expiry selector, spot, PCR, per-wall OI, and the unmeasured caveat.

**Drawn with `createPriceLine`, not a canvas.** These are horizontal PRICE levels,
so Lightweight Charts owns the anchoring and the axis label and there is no
pan/zoom redraw to get wrong — the exact trap the user-drawing layer (shipped
the same day) had to solve with a deferred-rAF repaint. Choosing the primitive
correctly removed the whole class of bug.

Both B-23 rules are respected, and the expiry one **visibly matters**: RELIANCE
Sep-29 reads max pain 1320 with call walls [1320, 1400, 1350]; Oct-27 reads max
pain 1300 with [1400, 1360, 1500]. Pooling those would produce a blended fiction,
which is why `max_pain` refuses a pooled chain server-side and the card makes
expiry an explicit choice rather than a silent default.

Verified in the browser: 7 price lines (3 CE + 3 PE + max pain); expiry switch
refetches and redraws; a non-F&O symbol degrades to "no F&O chain for X" with
zero lines and no error; toggling off removes every line and the card; no console
errors.

**Still open — the actual testable claim.** The **short-straddle-break →
short-cover rally** event is unbuilt, and that is the real signal here: the wall
existing is not the event, the wall being *pierced* is. Alongside it the two folk
claims remain untested — "price gravitates to max pain" and "a wall rejects the
first touch" — needing a first-touch event study against a matched non-wall
strike. B-19 (0/41 scanners stable after costs) is the prior to hold. Filed as
**B-28r**.

### B-40 · VWAP is a chart line, not a signal — **SCANNER SHIPPED 2026-08-27**
Was: zero occurrences of `vwap` in `scanner_templates.py`; VWAP existed only as a
chart overlay. **Shipped** `scan_vwap_reclaim` (registry "VWAP Reclaim/Support",
category Entry, scanner #40) + `_rolling_vwap` + `_anchored_vwap` helpers.

**Design correction, recorded so it isn't re-litigated:** the first cut anchored
VWAP to the lowest low of the last 120 bars (Brian-Shannon style) — but on daily
data that mean sits far below price in any healthy trend, so the "not-extended"
gate always rejected and the scanner never fired (0/8 real, even a hand-built
pullback). A *pullback/reclaim* event needs a mean price actually oscillates
around, so the scanner uses a **rolling 20-day VWAP**; the `_anchored_vwap` helper
is kept for the complementary catalyst-anchor read. Fires on a **reclaim** (close
crosses back above a rising VWAP on ≥20d-avg volume) OR a **pullback-hold** (a bar
tags VWAP within 1% and bounces), with-trend only (close > EMA-50), not extended
(≤6% above the mean). Verified: fires selectively (1/8 large-caps: TITAN
pullback-hold; downtrend correctly rejected; module compiles).

**Still open:** (a) the **anchored-VWAP-from-catalyst** support read (earnings /
breakout / IPO anchor) + the chart's click-to-anchor — that half is **B-4/B-12**;
(b) **unmeasured** — like every scanner it needs `backtest_scanner` run on it
(does a VWAP-reclaim beat the every-bar baseline?) before it grades anything. That
is the one open measurable claim.

**Adjacent measured result (2026-08-29) — a *different* VWAP rule, tested and dead.**
The owner's TradingView `EVWMA_VWAP_MACD[QN]` BUY/SELL strategy was ported into the
chart tool (`evmacd`) and put through the same harness: **no edge at any horizon**
(BUY-cross +0.10/+0.04/+0.17/+0.04% at 5/10/20/60d, p 0.32–0.91, 23 names × ~19y),
stop-and-reverse median **−29%** vs buy&hold **+827%**. Full write-up in
[[concepts/EVWMA-VWAP-MACD]]. This does **not** settle B-40's open claim — that one
is about the *reclaim/pullback-hold* event on a rolling 20-day VWAP, a different
rule — but it is a second data point that VWAP-derived **crossovers** are context,
not triggers, and the reclaim scanner should be measured expecting the same.

### ~~B-43~~ · Renko / time-independent chart engine — ✅ **BUILT + MEASURED 2026-08-29 → CLEAN NULL**
`grep -ri renko tools/` returns **nothing**. Every chart type and every scanner in this
repo is time-sampled (candles, Heikin Ashi), so the whole family of price-sampled charts
— Renko, and the [[concepts/Point-and-Figure-Charts]] we already document but never
compute — is absent. Raised by [[sources/YT-Devendra-Renko-Intelligence-Commodities]];
written up in [[concepts/Renko-Charts]].

**Build (normal-sized, no new architecture):** `renko.js` pure module (bricks from OHLC,
2-brick reversal) + a rendering plug in `chart_dashboard.html` that keeps the candles and
draws Renko *structure* on them — the same compute-module-plus-plug shape as `evmacd`,
`prte` and `stai`. Brick size **derived, not tuned**: `ATR(5)` on a session-length bar ÷
execution bars per session (≈8.3 pts for Nifty 30-min; the source's own worked numbers
are internally inconsistent — corrected on the concept page).

**Measurable claim, and the trap:** does a Renko brick-flip beat the every-bar baseline
on the *underlying OHLC*? Renko bricks are **not fillable bars** — no usable timestamp,
the last brick repaints, and one brick can span many real bars — so the test must enter on
the bar that *completes* the brick, scored through the standard harness. A backtest run on
the brick series itself is the classic way this chart type manufactures a fake equity
curve; whoever builds this must not take that shortcut.

**Prior:** neutral-to-skeptical. Renko is a *rendering* choice; a rendering choice that
also removed noise from the signal would be a free lunch. Expect the honest result to
land where the DI cross and the EVWMA/VWAP MACD cross landed — useful context, no
standalone edge — and build it to find out, not to confirm.

**RESULT — the flip has no edge, exactly as the prior said.** Shipped `renko.js`
(close-based bricks, 2-brick reversal, **causal ATR-epoch brick sizing** — re-derived every
20 bars from ATR over strictly prior bars, because rebuilding the grid from the latest ATR
repaints all of history), the `renko` chart overlay (two-colour staircase on the candles +
flip arrows + a labelled state price line), `renko_backtest.js` and `renko_backtest.py`.
Engine invariant verified in-browser: zero violations of the 2-brick reversal rule across
470 live bars.

Scored through the **same harness** as the EVWMA cross — `event_edge`/`strategy_equity`
now take an injected `signals_fn`, so there is one scorer and several engines rather than
a second copy of the Welch machinery — on the identical 23-name basket and ~19 years:

```
flip_up (LONG)    n=1862   -0.06 / -0.08 / -0.04 / -0.77 %   p 0.62 / 0.60 / 0.85 / 0.07
flip_dn (SHORT)   n=1871   +0.11 / +0.05 / -0.19 / -1.00 %   p 0.35 / 0.76 / 0.40 / 0.01*
```

The long leg is **negative at every horizon**. The single starred cell is not a finding:
8 cells tested (~0.4 expected under 0.05 by chance), at the longest horizon, where
overlapping windows inflate Welch hardest — the artefact B-44 measured directly. Equity:
stop-and-reverse median **−39%**, beating buy&hold **0/23**; long-only +267% vs +827%,
1/23. At 20bps: −56% / +223%.

**The finding worth carrying forward:** Renko *did* reduce noise — on the same names it
fires about **40% fewer times** than the EVWMA cross (RELIANCE 202 vs 320). It removed
signals without improving the survivors. **Fewer decisions of the same quality is an
ergonomic benefit, not an edge**, and this repo should stop treating the two as the same
claim — several open items (B-35 family-lens UI, and the noise-reduction thrust generally)
rest on exactly that conflation.

**Chart feature kept**, labelled **FLIP up / FLIP down** and never BUY/SELL, with no
wording implying a trigger. Full write-up in [[concepts/Renko-Charts]].

**Gated sub-item — commodities (MCX).** The source's other theme is that real movement
lives in commodities. The chart tool and all 40 scanners are equity/index only, and MCX
needs a different data source, session calendar (09:00–23:30) and contract/expiry
handling. Recorded as a scope decision for the owner, **not** assumed in scope.

### ~~B-44~~ · Gamma-regime (GEX) read — ✅ **BUILT + MEASURED 2026-08-29 → CLEAN NULL**
The vault has [[concepts/Put-Call-Ratio]] and OI momentum but **nothing on dealer gamma
positioning**, which is a *mechanical* volatility-regime driver rather than a sentiment
proxy: positive dealer gamma → hedging sells rips and buys dips → **volatility damped,
breakouts fail**; negative gamma → hedging buys rips and sells dips → **volatility
amplified**. Raised by [[sources/YT-Chris-Kmer-World-Cup-Order-Flow]]; mechanism written
up in [[concepts/Gamma-Exposure-GEX]].

**Why this is cheap:** `nse_oi_momentum.fetch_fo_bhavcopy_raw()` already pulls the **whole**
F&O bhavcopy from the non-Akamai-blocked archive and keeps only `FinInstrmTp == "STF"`.
The discarded `STO`/`IDO` option rows — the same ones `pcr.py` reclaimed for Put-Call
Ratio — carry strike and open interest, which is the raw material for a **naive GEX** on
NIFTY/BANKNIFTY. Gamma per strike needs a vol input, obtainable by inverting
Black-Scholes on the bhavcopy settlement prices. **No new network call.**

**The limit that sets the scope, stated up front:** bhavcopy is **end-of-day**. The
source's use is a pre-open *intraday* regime read; what this data supports is a **daily**
gamma-regime series — a volatility-regime input to the swing-horizon stack, adjacent to
the RISK-ON/RISK-OFF gate from B-32, not an intraday tool. Do not let it be built as one.

**Measurable claim (test before any dashboard):** does the forward-return distribution
differ significantly between positive- and negative-gamma days? Two concrete legs — (a) do
breakout/momentum signals underperform *their own* baseline on positive-gamma days, and
(b) is realised volatility higher on negative-gamma days? Both are event studies against
the existing harness.

**Prior: cautiously positive — the most favourable prior recorded in this backlog.** Unlike
the pattern-spotting items, GEX rests on a documented hedging obligation. But the Indian
options market's dealer structure is not the US one, and the naive-GEX positioning
assumption ("customers buy options") is exactly what the test must not assume. If the
regime split shows nothing on NSE data, that assumption is the first suspect, and the
finding should be recorded either way.

**RESULT — the pre-registered claim failed.** Shipped `gamma_exposure.py` (naive dealer
GEX from the `IDO` bhavcopy rows: per-strike IV inverted from settlement prices, net/gross
GEX, gamma flip, call/put walls, coverage), `gamma_regime_backtest.py`, and
`test_gamma_exposure.py` (14 tests). Built the full **480-session** history
(2024-09-19 .. 2026-08-28 — all the UDiFF-format bhavcopy there is), coverage 87.5% NIFTY
/ 89.7% BANKNIFTY. Every test is a null:

| test | NIFTY | p_rot |
|---|---|---|
| forward realised vol 5/10/20d | +0.28 / +0.24 / **−0.40** pp | 0.84 / 0.83 / 0.67 |
| next-day absolute move | +0.03 pp | 0.69 |
| directional return (expected null) | +0.04 … +0.70 pp | 0.22–0.69 ✓ |
| net/gross **tercile** vol split | +0.06 … +0.63 pp | 0.58–0.95 |
| 20-day-high breakout follow-through | −0.10 pp (49 events) | 0.84 |

BANKNIFTY has the right sign at every vol horizon (+0.77 / +1.02 / +1.59 pp) but p_rot
0.75 / 0.68 / 0.58 — a hint, not a result. **The "cautiously positive" prior recorded on
this item was wrong**, and the tercile split being null too means it is not merely the
zero-threshold being in the wrong place. **Nothing was wired into `REGIME_GATE` or any
dashboard** — the item said test first, and the test failed. Full write-up in
[[concepts/Gamma-Exposure-GEX]].

**A methodology finding that outlives the null, and applies repo-wide.** The first pass
used Welch, as every other backtest here does, and reported the **expected-null**
directional test at **p=0.031**. Artefact: daily sampling against a 20-day forward window
means consecutive observations share 19/20 of their data, so Welch's independence
assumption fails. The harness now leads with an **exact circular-rotation p-value** (every
shift of the label series enumerated, preserving the autocorrelation of both series),
which reads **0.32** on the same test, and prints both columns side by side. Every repo
backtest that samples daily against multi-day horizons carries this exposure —
`stride=5` mitigates it, rotation measures it. Worth retro-fitting where a marginal
Welch result is currently load-bearing.

### ~~B-34r~~ · Hidden Treasures had no gate at all — **SHIPPED 2026-09-05**

Owner asked whether the small/micro-cap lane has a value-trap avoidance gate. It had **no
gate of any kind**. Every factor in `smallcap_discovery.score_from_cache` was a soft score
adjustment, including the one the page called a *"pledge veto"* — in code it was **−20
points**. A name with 40% pledge and promoters distributing scored ~27, stayed in the
universe, and merely ranked low; in a thin universe it could still surface.

`red_flags.py` (FR-4) already existed and was imported by `dashboard_app`,
`market_health` and `technofunda_funnel` — but **not** by this lane. So the fix was
wiring, not writing.

**Cost: zero extra requests.** The checklist reads the same `fundamentals_deep` payload
the quality overlay already fetches, and the promoter/pledge checks are fed from
`ownership_cache`, so `sessionid=None` leaves the screener.in path dormant.

**The obvious gate is a trap.** `red_flags.no_critical_flags()` returns `False` for *every*
symbol by design — auditor qualification, related-party dealing and contingent liabilities
live in filing prose nothing in this stack parses, so they are permanently `NOT_CHECKED`
and a helper demanding every critical check be CLEAN can never pass. Gating on it would
empty the list. The gate is `counts["critical_flagged"]`: a critical check that ran **and**
failed.

Behaviour: critical flag fired → **veto**; watch-level flag → **−6** each; `NOT_CHECKED`
counted and reported, never a pass. Vetoes require the quality overlay (they need its
payload); with it off, `veto_active` is False and the page says nothing was screened.

**Measured, Smallcap-250, 249 scoreable:**

| reason | names |
|---|---|
| Negative free cash flow | 59 |
| Promoter stake reduction | 51 |
| Promoter share pledging | 28 |
| Equity dilution | 5 |
| **vetoed total** | **100 (40%)** — 37 tripped more than one |

**SAILIFE, the highest-scoring name in the universe (76.9), is vetoed** on two years of
negative FCF. So are JSWCEMENT and GRSE.

### B-34r2 · Should the veto stay on? — **HALF MEASURED 2026-09-05**

`hidden_treasures_backtest.py --gov-veto`. Smallcap-250, top 25, 6 eval quarters,
30-SEP-2024 … 31-MAR-2026.

| arm | 60d edge | p | hit% | 120d edge | p | hit% | Q+/Q 60d |
|---|---|---|---|---|---|---|---|
| no veto | +0.91% | 0.5393 | 59.3% | +1.47% | 0.5425 | 58.4% | 3/6 |
| **governance veto** | **+1.21%** | 0.4170 | **60.7%** | **+2.15%** | 0.3884 | **60.0%** | 4/6 |

> [!contradiction] Superseded by B-34r3
> These figures were produced with the **unbounded** promoter window. Re-measured after
> B-34r3 bounded it, the 120d edge falls from +2.15% to **+1.46%**, against +1.47% for no
> veto at all — the improvement below was mostly the drift. Read the B-34r3 table instead.

**Every metric moves the right way and none of it is significant.** Baselines are identical
in both arms (+4.61 / +6.84), which confirms the veto touched only the picks; n(top)=150 in
both, so the basket filled in every quarter. Verdict is the same class as B-34 itself:
**WEAK — it does not hurt, and it cannot be shown to help.**

**Only half the question was testable, and it is the smaller half.** FCF and dilution cause
**64 of the 100** live vetoes, but `fcf_history` and `shares_history` come back from
yfinance as bare value lists with **no year labels**, so they cannot be truncated to "as
known at Q". Applying today's FCF streak to a 2024 entry vetoes a pick for something that
had not happened yet. **The headline question — should negative FCF veto — remains open and
is not answerable with the current data.** It needs a point-in-time fundamentals store
(year-labelled annual history), not another run against the present one.

**A flaw the run exposed, affecting the LIVE page too.** The veto rate is not stationary —
it climbs with the length of the lookback window, because `_check_promoter_holding_nse`
compares oldest→newest across however many quarters it is handed:

| quarter | scored | vetoed | veto rate |
|---|---|---|---|
| 31-DEC-2024 | 224 | 7 | 3% |
| 31-MAR-2025 | 232 | 11 | 5% |
| 30-JUN-2025 | 232 | 43 | 19% |
| 31-DEC-2025 | 242 | 58 | 24% |
| 30-JUN-2026 | 249 | 70 | 28% |

A 2pp promoter drop spread over 8 quarters is much weaker evidence than the same drop over
2, and the check does not distinguish them. So the veto silently tightens as the ownership
cache deepens — on the live page as well.

### ~~B-34r3~~ · Bound the promoter window — **SHIPPED 2026-09-05**

`red_flags._PROMOTER_WINDOW_Q = 4`. Fixed **at the source, not in the lane**: both promoter
paths (free NSE and screener.in) compared oldest-vs-newest across the whole cached series,
so the flaw belonged to the module and `dashboard_app`'s Analyzer inherited it too. The
`hidden_treasures_backtest` veto is bounded to match, and every detail string now names the
span it actually compared ("fell 2.8pp over the last 4 NSE-filed quarters") so a verdict
can never be read without knowing its window.

**Veto rate is now stationary where it can be:**

| quarter | before | after |
|---|---|---|
| 31-DEC-2024 | 3% | 3% |
| 31-MAR-2025 | 5% | 5% |
| 30-JUN-2025 | 19% | 19% |
| 30-SEP-2025 | 22% | **20%** |
| 31-DEC-2025 | 24% | **21%** |
| 31-MAR-2026 | 26% | **20%** |
| 30-JUN-2026 | 28% | **19%** |

**The residual ramp at the start is not the same defect.** Those quarters hold only two or
three quarters of history in total, so the window is short — and a 2pp cumulative drop is
*harder* to reach in two quarters than in four. That bias runs toward NOT flagging on thin
history, the opposite of the original defect, where a longer window quietly made the same
threshold easier to trip.

**Deliberately out of scope:** the SCORE's promoter term (−15 / +10 in `score_from_cache`)
still uses the unbounded oldest-to-newest delta and has the same drift. Changing it moves
the ranking itself and would invalidate B-34's measured baseline — that is a
re-measurement, not a bug fix, and it needs its own item rather than being smuggled into
this one. **B-34r4.**

**Edge re-measured with the bounded veto — and most of B-34r2's improvement was the bug.**

| arm | 60d edge | p | hit% | 120d edge | p | hit% |
|---|---|---|---|---|---|---|
| no veto | +0.91% | 0.5393 | 59.3% | +1.47% | 0.5425 | 58.4% |
| veto, **drifting window** (B-34r2) | +1.21% | 0.4170 | 60.7% | **+2.15%** | 0.3884 | 60.0% |
| veto, **bounded window** (correct) | +1.02% | 0.4945 | 60.0% | **+1.46%** | 0.5498 | 59.2% |

At 120d the corrected veto is **+1.46% against no-veto's +1.47%** — indistinguishable. The
+2.15% that made the veto look worthwhile was substantially an artefact of a gate that
tightened as the cache deepened, i.e. of the measuring instrument rather than of the
screen. Hit rate and Q+/Q still tick up slightly (60.0% vs 59.3%, 4/6 vs 3/6 at 60d), so
the honest verdict is **NEUTRAL: the governance veto does not hurt and does not measurably
help.**

**This retracts the recommendation given earlier in B-34r2.** "Keep them, they are
directionally positive" rested partly on the drift. The case for keeping the governance
vetoes is now a governance-risk argument — you do not want to hold a name whose promoters
are selling into a pledge — and explicitly **not** a measured-edge one.

**Resolved 2026-09-05 — negative FCF demoted to a penalty.** The two governance vetoes stay
(measured harmless and directionally positive, and testable point-in-time); FCF now costs
**12 points** via `RF_DEMOTED` instead of removing the name. 12 sits between the watch
penalty (6) and the pledge penalty (20).

| | before | after |
|---|---|---|
| vetoed (Smallcap-250) | 100 | **72** |
| kept | 149 | **177** |
| veto causes | promoter 51 · pledge 28 · dilution 5 · **FCF 59** | promoter 51 · pledge 28 · dilution 5 |

51 kept names now carry the FCF flag as a penalty. **SAILIFE**, the top-scoring name in the
universe, is back at 64.9 (76.9 less 12) having been removed entirely before.

Two implementation notes worth keeping:
- The demotion is computed from the **flag list**, not from `counts["critical_flagged"]` —
  that count still includes `negative_fcf`, so gating on it would have silently ignored the
  demotion.
- Demotion applies to the **CRITICAL grade only**. `red_flags` scores a single negative-FCF
  year as WATCH ("one year alone can be a capex cycle rather than a problem"), so charging
  it the full 12 would have been harsher than the source module's own reading. Caught on
  SUNTV, a one-year dip: 50.9 → 56.9 once it took the watch 6 instead.

**Still open:** whether FCF *should* veto remains unanswered rather than answered — the
demotion is a judgement made because the test was impossible, not because the test came
back negative. A point-in-time fundamentals store would let it be settled properly.

### B-34r2 · original framing *(2026-09-05)*

The default shipped as "yes" and I am not confident it is right. Three reasons to doubt it:

1. **Negative FCF is the single biggest cause** (59 of 100) and for a reinvesting small-cap
   it is frequently the business model, not a value trap.
2. **This lane has no valuation input at all** — no P/E, P/B or price enters the score. It
   is an ownership-conviction screen, so "value trap" may be the wrong frame entirely; its
   real failure mode is an **ownership trap** (institutions accumulating a deteriorating
   business, or passive flow misread as conviction).
3. **B-34 measured the ungated ranking at +2.51% @60d (p=0.22) / +6.29% @120d (p=0.14) —
   WEAK.** Changing what the list contains changes that number in an unknown direction.

The gate is therefore a **toggle**, defaulted on, with all 100 exclusions listed in the UI.
Deciding it properly is a measurement, not an opinion: re-run `hidden_treasures_backtest.py`
with and without the veto and compare hit rates. That is the same experiment shape as B-34,
B-49 and B-50 — the shared event-study harness Phase 0 keeps asking for.

Sub-question if the answer is "penalise, not veto": governance items (pledge, promoter
dumping, egregious dilution) have a much better claim to vetoing than FCF does, so the
split may be per-flag rather than all-or-nothing.

### ~~B-44r~~ · Is the naive convention backwards for NSE? — **MEASURED 2026-09-05: FALSIFIED, GEX RETIRED**

`tools/gamma_magnitude_backtest.py`. **No re-download was needed**: the note below says
"needs a fresh 480-session pass over the raw chains", and that was wrong — the quantity the
both-sides-short convention needs is `gross_gex_cr`, which `compute_gex` already persists.

The pre-registered direction (bigger dealer book → **higher** forward vol) came back
**inverted** on both indices at every horizon: NIFTY −2.47 pp / p_rot 0.042, BANKNIFTY
−4.27 pp / p_rot 0.004 on the primary 5d test. The expected-null directional control
behaved (p_rot 0.77 / 0.57), so the harness is sound.

Most of the inversion is mechanical — BS gamma carries **1/σ**, so high vol produces low
gamma, and vol clusters: corr(gross, trailing vol) = −0.44 / −0.24 against
corr(trailing, forward) = +0.43 / +0.49. Controls halve NIFTY's effect to insignificance
(p_rot 0.029–0.067); BANKNIFTY survives them (p_rot 0.021–0.033) but the **stratified** test
kills it: the effect lives only in the high-trailing-vol tercile (−9.25 pp) and **flips
sign** in the low-vol tercile (+1.23 pp, p_rot 0.44).

Per the scope-discipline clause written into this item in advance, GEX is now **retired as
a research instrument** — it prints a daily description and nothing more. Both conventions
have now been tested and neither carries forward vol information on NSE indices. The
remaining gap is per-strike dealer inventory, which is data this repo does not have, not
another assumption about it. Full write-up on [[concepts/Gamma-Exposure-GEX]].

<details><summary>Original item, kept for the record</summary>

### B-44r · Is the naive convention backwards for NSE? *(2026-08-29)*
The pre-registered first suspect, now the only live thread. Naive GEX hard-codes a
**US-equity** folk model — customers buy puts and sell calls, so dealers are long call
gamma and short put gamma. Indian index options may be close to the mirror image: retail
is a heavy **buyer** of cheap weekly OTM options on both sides, with prop desks and
institutions **writing** them. Under that structure dealers are short gamma on *both*
sides, and the measured 70% (NIFTY) / 85% (BANKNIFTY) positive-gamma day count is the
convention talking, not the market.

**This is not a re-run, it is a different measurement.** "Dealers short both sides" makes
net GEX unconditionally negative, so the *sign* carries no information and the test has
to move to gamma **magnitude** (normalised by spot, or by gross, or against its own
trailing distribution) as the vol predictor. Needs a fresh 480-session pass over the raw
chains — the cache stores aggregates, not per-strike rows. **Scope discipline:** this is
ONE further pre-specified hypothesis with an independent market-structure rationale, not
licence to try conventions until something clears p<0.05; if it also nulls, GEX gets
retired as a research instrument that prints a daily description and nothing more.

**Explicitly NOT in scope from the same source:** footprint/delta order flow (needs
tick data the repo has never carried) and the intraday futures lane, already recorded as
out-of-scope. Filed as knowledge in [[strategies/Forced-Participation-Reversal]].

</details>

### B-49 · Free quality-value screen — **SHIPPED 2026-08-31** *(`tools/value_screen.py`)*
Owner asked whether the "deep value" card format (P/E, P/S, OPM, ROE, ROCE, D/E,
revenue & profit growth) could be reproduced from **freely available data**. Tested
before promising: on AGI Greenpac the free path reproduces **6 of 8 figures to within
rounding**, and the two that miss are **definition mismatches, not data gaps**.

Closes the gap between two modules that each had half of it:
`multibagger_candidates.py` runs almost this exact query but is **screener.in
cookie-gated**; `smallcap_discovery.py` is free but scores **ownership only**.

Built free-only, reusing rather than re-deriving: universe from
`smallcap_universe` (NSE Smallcap-250 + Microcap-250 archive CSVs), every metric
from `fundamentals_deep.derive_fundamentals`, governance flags from
`ownership_cache` when warm.

**Three findings that shaped the design, each from measurement:**

1. **`.info` returns `returnOnEquity: None` for AGI Greenpac.** A screen keyed on
   `.info` alone would have silently dropped its own worked example. Metrics
   therefore come from the **statements** path first; `.info` supplies only the
   multiples. Criteria are three-state **PASS / FAIL / UNKNOWN** (the FR-4
   convention) and a missing figure is **never counted as a fail**.
2. **The card's growth figures use the shortest available window.** It advertises
   "+14% revenue / +12% profit"; those are the `.info` quarterly figures. From the
   annual statements the same company grows **5.4% YoY and 5.7% over 3 years**.
   Its "OPM 22%" is likewise the latest *quarter* against 19.3% for the full year.
   The screen therefore tests the **3Y CAGR** and *reports* the 1Y beside it, with a
   note when 1Y exceeds the CAGR by >= 6pp — flagged, never screened on, because a
   genuine inflection and a flattered one look identical from the outside.
3. **`fetch_statements` already called `.info`** and kept only four fields. Extended
   it to carry `market_cap / pe / ps / price / sector / industry`, so the screen makes
   **one** yfinance round trip per symbol instead of two. P/S falls back to
   market-cap / revenue (tagged `ps_source: calc`) because yfinance's own is sparse
   on NSE.

Verified end to end over 80 free small-caps: **80/80 derived** (full coverage on the
free path), 1 hit under the strict defaults. 27 tests in `test_value_screen.py`, all
passing, none touching the network (`screen` takes an injected `derive`).

> [!warning] Reading list, not edge.
> Ranking is *passes -> fewest unknowns -> ROCE*, stated as such in the module and in
> the CLI footer. It is **not a conviction score and not backtested**. "Cheap with
> good ROCE" is among the most crowded screens in existence. The measurement that
> would change this is a forward hit-rate study against a Smallcap-250 benchmark —
> **the same test B-34 still owes**, and the two should be run together.

**Not done, deliberately:** not registered in `scheduler_core` and not surfaced in any
dashboard page. Both are cheap, and both should wait until the hit-rate study says
whether the list is worth reading daily.

### B-50 · Contra margin-inflection screen — **SHIPPED 2026-08-31** *(`tools/contra_inflection.py`)*
Owner asked whether the OPM-jump / PEAD / EPS-acceleration shape on a "deep value"
card could be caught systematically, as a **contra** strategy aimed at rising stars.
It can, from free data. See [[concepts/Margin-Inflection-Contra]].

**The design point:** B-49 screens on **level**, this screens on **change**, and they
select disjoint sets. OCCL Ltd fails B-49 outright (ROCE 11.6%, ROE 11.1%) while its
June-2026 quarter shows OPM 25.6% vs 16.0% a year earlier and PAT +206%. Annual
figures average the turn away -- OCCL's annual OPMs read 12.0/11.1/-/15.5 -- so the
signal only exists at quarterly grain. `fundamentals_deep._quarterly_history` gained
an `opm` / `ebit` / `opm_yoy_base` field for this.

**Output is a verdict LABEL, not a score:** `INFLECTING` / `MARGIN_LED` /
`RECOVERING` / `SINGLE_QUARTER` / `UNVERIFIED` / `ONE_OFF_SUSPECT` /
`NO_INFLECTION` / `INSUFFICIENT_DATA`, each with its reasons printed.

**Two bugs found by running it, not by reading it:**

- **`operating_led` demanded EBIT keep PACE with PAT**, which flags ordinary
  deleveraging and tax-rate changes as accounting one-offs — the AGI Greenpac
  card's own "debt cut by over half" pitch is exactly that shape. The test is now
  **participation, not parity** (`EBIT_PARTICIPATION = 0.25`).
- **An unevaluated guard was being read as a passed guard.** ITI Limited took the
  top `INFLECTING` slot on OPM 72.7% vs 3.9% with all four prior quarters
  loss-making and revenue **down 40%**; `pat_yoy`, `operating_led` and
  `cfo_pat_ratio` were all `None`, so every check silently no-opped. Fixed with an
  explicit evidence gate + the `UNVERIFIED` verdict + a `loss_in_base` flag. Same
  failure mode as B-49's `.info` ROE hole.

**Measured on 120 free small/micro-caps:** 120/120 derived; 11 `INFLECTING`,
1 `MARGIN_LED`, 1 `RECOVERING`, 19 `SINGLE_QUARTER`, 22 `ONE_OFF_SUSPECT`,
1 `UNVERIFIED`, 64 `NO_INFLECTION`. **The guards reject 42 names a naive
"profit up X%" filter would have handed over** — which is the whole value of the
module. 33 tests, none touching the network.

> [!warning] Unvalidated, and the honest limit is narrower than it looks.
> [[concepts/PEAD]] is real in Indian equities. That supports *prices under-react to
> earnings surprises*; it does **not** support this filter set finding multibaggers.
> Also: yfinance returns only ~5-6 quarters and `_year_ago_index` matches a year-ago
> quarter for the newest one or two only, so **persistence is measured
> quarter-on-quarter and is seasonality-exposed** — reported as a count, never as a
> pass/fail, because it cannot be cleaned up with the data available.

**Owed:** a forward event study — enter at the first `INFLECTING` print, hold N days,
against a matched non-inflecting control, using the exact rotation p-value. Run it
with B-34's and B-49's hit-rate study; all three are the same experiment shape.
**Not** scheduled and **not** wired to a dashboard until that runs.

### B-51 · Volume-anomaly screen with CAUSE attribution — **SHIPPED 2026-08-31** *(`tools/volume_anomaly.py`)*
Whole-market volume spikes (latest session vs the name's own 1-year average),
each attributed to a cause read from free NSE feeds. **A screen, not a trigger** —
no entry/stop/target and never a confluence vote, wired like the Renko Flip screen.

**Why bhavcopy is the same-day source and yfinance is not.** Verified: on
2026-08-28 yfinance had **no bar at all** for MASTEK or OAL and silently served the
previous day, turning MASTEK's 43.9x volume day into **0.9x** — not an error, a
plausible-looking normal reading. `screener_pipeline` gained
`fetch_bhavcopy_frame()`; `fetch_bhavcopy_top_volume` is now a thin wrapper over it,
because it already did the column sniffing and threw the volume away. Bhavcopy also
carries `prev_close`, so the 1-day return needs no second source.

**Cause taxonomy:** `CORPORATE_ACTION` / `PROP_CHURN` / `DEAL_DRIVEN` /
`UNEXPLAINED`, using `nse_announcements` (per symbol) and
`india_market_intel`'s bulk/block feeds. The Market Intel page's note that the
whole-market announcement feed is too high-volume to wire up **does not apply here**:
announcements are fetched only for names that already cleared the volume filter —
tens of calls *after* the funnel, not thousands before it.

**The bug the first live run found, and the reason this module works at all:**
NSE files a **"Spurt in Volume"** notice *because* volume spiked. Counting it as the
cause is circular, and it labelled **7 of 9** spikes `CORPORATE_ACTION`, starving
`UNEXPLAINED` — the only bucket worth attention. A `REACTIVE_SUBJECTS` exclusion
now runs **before** the material-keyword test (order matters: a clarification reply
quotes the company and routinely contains material words). Distribution moved from
`UNEXPLAINED=2 / CORPORATE_ACTION=9` to `UNEXPLAINED=5 / CORPORATE_ACTION=5`.

**A correction carried in the code:** the pitch for this module claimed prop churn
explained MASTEK's spike. Measured, the visible round-trip is 528,244 of 5,449,060
shares — **9.7%**, below `CHURN_SHARE_MIN`. It is also a **lower bound**: NSE only
requires a bulk deal to be reported above 0.5% of listed shares, so smaller desks
never appear. Churn share is therefore printed on every row and only becomes the
headline cause above the threshold. A test pins MASTEK to `DEAL_DRIVEN` so the
threshold cannot be quietly re-tuned to fit the example.

**Live result** (2026-08-28, 2,629 EQ universe, top 300 by turnover, >=8x):
13 spikes — 5 `CORPORATE_ACTION`, 5 `UNEXPLAINED`, 2 `PROP_CHURN`, 1 `DEAL_DRIVEN`;
19 names skipped for short history rather than scored against a meaningless average.
21 tests, all offline.

> [!warning] Unvalidated, and one hard operational limit.
> No forward-return study: nothing says an `UNEXPLAINED` spike precedes anything.
> And **the NSE bulk/block endpoints return only the current day** — no history —
> so a back-dated run finds the volume but not the deals. Daily capture into an
> archive is the obvious follow-on and is **not** built.

### B-45 · Two indicators are already COMPUTED but not plottable — ATR and MFI *(2026-08-30)*
From [[analyses/Indicator-Coverage-Gap]]. **MFI** exists as `_mfi_series` and
`scan_mfi_oversold` in `scanner_templates.py`; **ATR** is computed 32× inside
`chart_dashboard.html` (Keltner, PMax, Renko). Neither appears in `INDICATOR_DEFS`, so
neither can be put on a chart. This is wiring, not mathematics, and ATR is the series
stop-sizing actually needs. **Do this before building any new indicator.** No backtest is
owed — exposing an existing series makes no claim about edge.

### B-46 · Ichimoku Cloud — the largest single named absence *(2026-08-30)*
The most consistently cited "complete system" indicator and absent from `tools/` entirely
(`grep -ri ichimoku tools/` → 0). Five lines (Tenkan 9, Kijun 26, Senkou A/B, Chikou) with
Senkou shifted **forward** 26 bars — the forward shift is the only non-trivial part, and
`padSeries` already pads with whitespace points for exactly this reason. Ship the overlay
first; any BUY/SELL reading is a separate, measured question. **Parabolic SAR is explicitly
NOT bundled** — `pmax` and `stai` already occupy the trailing-stop-flip role, and adding a
third would risk another zero-unique entry of the kind [[analyses/Scanner-Overlap-Audit]]
just trimmed.

### B-47 · TPO / Market Profile pane — the half of profile we don't have *(2026-08-30)*
`volprofile` and `svp` give **volume**-at-price. **TPO** gives **time**-at-price: which
prices were visited in each half-hour bracket, letter by letter. Different lens, same bars
— **no data blocker**, unlike B-48. Complements the session profile rather than duplicating
it, and is standard on every prop platform surveyed. Needs intraday bars at 30m or finer,
which `data_source.py` already serves.

### B-48 · Cumulative volume delta — answer the DATA question before writing any indicator *(2026-08-30)*
The one real information gap ([[analyses/Indicator-Coverage-Gap]] Tier 3): the tool has the
volume-at-price half of order flow and **none** of the aggressor half — footprint bars,
delta, CVD — which is what [[entities/Chris-Kmer]] describes trading from and what the
prop-desk toolset converges on. See [[concepts/Order-Flow]].

> [!warning] This item's deliverable is a NOTE, not a chart.
> CVD requires **tick or bid/ask-classified trade data**. `data_source.py` serves OHLCV
> bars from yfinance and Hyperliquid. The tempting shortcut — a bar-level proxy such as
> close-position-in-range × volume — would render a plausible-looking chart of something
> that **is not delta**, and would be indistinguishable from the real thing by eye. Do not
> write the indicator until the feed is identified. Hyperliquid is the only feed in this
> stack that could plausibly supply trade-side data; establish whether it does, and whether
> any NSE path exists, first.

### ~~B-41 · No liquidity-sweep / stop-hunt detector — the missing third of the SMC stack~~ — **CLOSED 2026-09-02** *(2026-08-27)*
Zero occurrences of `liquidity sweep`, `stop hunt`, or `equal highs/lows` in `tools/`.
We ship FVG Pullback, Order Block Retest and ICT Setup — **two-thirds of the ICT
stack** — but not the **sweep-and-reverse**: an equal-highs/lows liquidity pool that
gets run (a stop hunt beyond a prior swing) and then reverses. This is the event that
*validates* the OB/FVG entries already scanned, so it is complementary, not a new
family. Build: detect equal highs/lows (clustered swing pivots within a tolerance),
flag a wick that pierces then closes back inside, direction-aware. Relates to B-19b
(support-breakdown) but distinct — a sweep is a *false* break that reverses, not a
real breakdown. Unmeasured until event-studied (sweep-reversal vs matched clean-break).

**SHIPPED 2026-09-02**, built directly on B-42's equal-level labelling (which is
what `eq_tol_pct` was added for — the two items composed as predicted):

- `detect_liquidity_pools()` — equal-highs/lows clusters. Level is the cluster's
  **extreme**, not its mean, because that is the edge stops actually sit beyond.
- `detect_liquidity_sweep()` — bidirectional. Requires a wick pierce of
  0.05–2.0 ATR (floor rejects a graze, ceiling rejects a break that kept going),
  a close back **inside**, and a dominant rejection wick.
- `scan_liquidity_sweep` (Entry) and `scan_liquidity_sweep_bear` (Risk) — the
  mirror is registered too, so this does not repeat the repo's orphaned-detector
  pattern. Registry is now **44 scanners, 6 Risk**.
- `test_liquidity_sweep.py` — 24 tests, all passing.

**Live check, 49 NSE large-caps:** pools on 49/49, a sweep event on 37, 7 bull
fires and 4 bear fires at `max_bars_ago=5`, all 7 trade plans well-formed
(R:R 1.15–4.03).

**Three bugs the build surfaced, all found by testing rather than review:**

1. **Consecutive-only clustering missed the normal case.** The first
   implementation grouped only *adjacent* pivots, so a low at 90, a rally, a low
   at 95, then 90 again never pooled — yet that interrupted revisit is exactly
   what a double bottom is. Clustering is now level-based across the window.
2. **The wick ratio measured the wrong quantity** — the pierce depth below the
   pool as a fraction of range (0.2 on the test bar) rather than the bar's
   rejection shadow (0.8). It was silently rejecting real sweeps.
3. **Targets with no room.** The nearest overhead pool can sit fractionally above
   entry: NTPC emitted entry 330 / target 330.22, an **R:R of 0.02**. A
   `MIN_SWEEP_RR` floor now falls back to 2R rather than print a plan that is not
   one.

**Exclusivity with B-19b is PER LEVEL, not global** — worth recording so a future
session does not "fix" it. A bar can legitimately sweep a pool below it while
still closing under a higher swing low, so both detectors firing on one bar is
coherent (measured: 1 of 49, ULTRACEMCO closing above its 11254 pool and below
its 11396 swing low). Only "swept and reclaimed level X" and "closed below level
X" are mutually exclusive, and a test pins that.

**Also recorded:** `session_volume_profile.js` already had a *different* sweep —
current session's extreme vs the prior session's, intraday. Two claims sharing a
name; the docstring says so, so nobody assumes they agree (the B-24 lesson).

**Still unmeasured**, and the claim is specific: sweep-reversal vs a **matched
clean break**, not whether the scanner wins in isolation. That event study is the
open item, and B-19 sets the expectation — most scanners show no edge after costs.

### ~~B-42 · No shared market-structure engine (BOS / CHoCH, HH-HL-LH-LL)~~ — **CLOSED 2026-09-02** *(2026-08-27)*
Swing traders read **market structure** first — the HH/HL/LH/LL sequence and its
**break of structure (BOS)** / **change of character (CHoCH)** — and every entry
hangs off it. The tool has a weekly-regime read
([scanner_templates.py:2827](tools/scanner_templates.py:2827)) and MTF breakout logic,
plus Structural Breakout / Support Breakdown that *imply* structure, but **no
first-class structure-state primitive** the scanners share. Build: one engine that
labels the current swing sequence + last BOS/CHoCH off shared zigzag pivots (the
`rsi_divergence.js` zigzag already exists), consumed as a filter/context by the
trend, pullback and SMC scanners — so "structure" means the same thing everywhere,
the way B-24 wants for RSI-divergence. Verifiable invariant available: the labelled
sequence must reconcile to the pivots it is built from.

**Re-verified against the code 2026-09-02 — the premise was partly stale**, the
same way B-11 was. Three structure walks already existed: `detect_bos_choch`
(pivot_len=5, bullish only, consumed by 4 scanners), `detect_support_breakdown`
(its bearish mirror), and `detect_structure_chain` (pivot_len=15, both
directions, with quality/chain/failed grading — but **consumed only by the chart
overlay**, no scanner). What genuinely did not exist was the **sequence
labelling** the item names.

**SHIPPED 2026-09-02, scoped deliberately additive** (owner's call — unifying the
two `pivot_len` defaults would silently re-grade live scanner output, the B-26
lesson):

- `label_swing_sequence()` — labels each swing HH/LH/EQH or HL/LL/EQL against the
  prior swing **of the same kind**, with an `eq_tol_pct` that turns near-equal
  levels into EQH/EQL (equal highs/lows are a liquidity pool, not a trend step —
  this is **B-41's raw material**).
- `read_market_structure()` — the first-class shared read. Composes the existing
  walk with the sequence and returns `state` (UPTREND / DOWNTREND / RANGE /
  BROADENING / TRANSITION / UNKNOWN), the premium/discount `zone`, the last
  graded event, and `agreement`.
- `_verify_swing_sequence()` — **the invariant the item asked for**, implemented:
  every label is re-derived from its own pivots and any mismatch is reported.
  Measured **0 violations across 30 NSE large-caps**.
- `/api/structure_chain` now returns a `structure` block and a `label` on each
  swing, reusing its existing walk (a `chain=` parameter avoids a second pass);
  a parity test pins reuse == recompute, so chart and scanners cannot drift.
- `test_market_structure.py` — 23 tests, all passing.

**Two things the real data forced, neither anticipated:**

1. **Plateau duplicates.** `detect_structure_chain` legitimately registers one
   pivot per bar across a flat top, so a single real swing arrives as several
   identical entries and the duplicate is always EQH/EQL — which collapsed every
   trend read to TRANSITION. `label_swing_sequence` now collapses consecutive
   same-kind swings at an identical level (marking them `duplicate_of`) so the
   sequence describes the market, not the sampling.
2. **`agreement` — the sequence lags, the breaks lead.** A pivot needs
   `pivot_len` bars to confirm while a break prints immediately, so the two reads
   can disagree. Rather than hide it, the read reports CONFIRMED / DIVERGING /
   UNDECIDED. **6 of 30 large-caps were DIVERGING** — e.g. KOTAKBANK reading
   DOWNTREND under a STRONG CHOCH *up* 5 bars prior, ASIANPAINT UPTREND with a
   CHOCH *down* the previous session. That disagreement is the earliest honest
   warning structure is turning, and it is the most useful field on the object.

**Residual → B-42r:** the `pivot_len` split (5 in the scanners, 15 on the chart
and in the shared read) is untouched and documented in-module. "Structure" is
still coarser on the chart than in the scanners. Settle it on data — the same
`--wf` harness B-19 used — not by inheritance. Also unbuilt: consuming the read
as an actual *filter* inside the trend/pullback/SMC scanners, which is a
detection change and so was out of this item's additive scope.

**Explicit scope decision (not a task):** the **intraday lane** the "Day/Intraday"
style row implies — **Opening Range Breakout, session-VWAP bounce/rejection as
intraday signals, order-flow/DOM scalping** — is **deliberately out of scope**. The
tool is EOD/daily on NSE and ingests no intraday or L2 depth data; ORB/DOM need a
feed the pipeline does not have. Recorded here so the absence is a decision, not an
oversight. (B-40's VWAP work is the *daily/anchored* slice, which IS in scope.)

---

## P3 — Consistency and correctness debt

### ~~B-24 · Two RSI-divergence implementations that disagree~~ — CLOSED 2026-09-02
`detect_bullish_rsi_divergence` rewritten to use Wilder RSI (`_rsi_series`) and
swing-pivot lows with a ≥3-point RSI gap threshold — the same definition as
`scan_rsi_divergence_bull`. Early Reversal now agrees with the RSI Divergence
scanner (and the JS chart). The only remaining difference is recency gating:
the standalone scanner requires the pivot within the last 3 bars; the Early
Reversal helper accepts any pivot pair within 80 bars (appropriate for its
composite-scoring role where recency is not the gate).

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
| ~~B-23~~ | **Strike-level option OI** (OI audit Gap 3) — ✅ **CLOSED 2026-09-02** | Was: "the largest remaining OI item, needs its own design pass." **The premise was stale** — B-44's `gamma_exposure.py` had already built the per-strike bhavcopy reader this was scoped to design, so the remaining work was the LEVELS read, not the feed. Third stale entry this week after B-11 and B-42. Shipped `option_chain.py`: `load_chain` (per-strike CE/PE OI for **stocks (STO) and indices (IDO)** — `gamma_exposure` is index-only), `max_pain`, `oi_walls`, `read_levels` + `format_levels`, plus `/api/option_levels` on chart_server so B-28's overlay has an interface to consume. 26 tests. Live: NIFTY spot 24,055.80 / max pain 24,050 on expiry day (converges, as theory predicts); RELIANCE 1,308.96 between its 1,300 put wall and 1,320 call wall. **Two correctness rules enforced:** max pain REFUSES a pooled-expiry chain (payoff settles per expiry — a far-month strike does not pay out on this week's settlement, so a pooled number is a different quantity, not a smaller error); and call walls are restricted to strikes at/above spot, put walls at/below, because a large call OI far below spot is deep-ITM inventory and ranking it as "resistance" would put the strongest resistance *under* the price. Levels ship **unmeasured** — see B-28. |
| B-13 | AW-1…AW-4 astro weekly card | Good-to-have; AW-0 shipped. |
| B-15 | SR-7 Trendlyne backfill | Optional, only if XBRL coverage proves short. |
| B-17 | OBV has no wiki page | Verified absent; ships as a chart indicator, undocumented. |
| B-27 | **Wiki hygiene** | Index counters had drifted to two *different* wrong numbers (frontmatter 204/78, body 198/81, actual 226/91) — corrected 2026-08-07, but a lint should **compute** these rather than trust them. Also an empty brace-expansion artifact directory `{entities,concepts,strategies,sources,analyses}` in the vault, untracked and harmless. |
| B-14 | ~~`ephem` not installed~~ | **CLOSED** — verified `ephem 4.2.1` present 2026-08-07. The reversal calendar can now be rebuilt; that rebuild has not been run, and coverage still ends **2027-12-28**. |
| B-30 | **Moon-in-Pushya reversal event-study** *(ingested 2026-08-20)* | Astro video claims Moon-in-Pushya days (~13-14/yr) mark major Nifty reversals. We already cache `gurupushya`/`ravipushya` muhurat dates and run muhurat/vedha/newmoon backtests; this adds the *general* Pushya-transit claim as one more event-study, reusing `newmoon_levels_backtest.py` (first-touch reversal vs a **matched non-Pushya control**, permutation null, eclipse strip). Textbook base-rate trap — ~13-14 dates/yr against typical 300-600pt 2-day ranges — so **expect a null**, consistent with the newmoon and sbc-vedha nulls. Worth running only to retire it with evidence. |
| B-31 | **Learned / regime-adaptive confluence weights — NOT NEXT** *(ingested 2026-08-20)* | The "signal-fusion" talk suggests *learning* confluence weights from historical performance and adapting them by volatility regime (IV<HV → defensive). We already cap correlated families (`scanner_weight`) and carry a RISK-ON/OFF flag, but weights are hand-set. Deliberately parked: learning weights is refinement on the base **B-25/B-19** already flag as unvalidated. Gate: close B-25 (does co-firing beat single-firing at all?) and B-21/B-29 (costs, walk-forward) first. Recorded so the idea is not lost — not so it is built next. |
| ~~B-32~~ | **Regime-PRESCRIPTIVE output throttle** — ✅ **CLOSED 2026-08-26** | Premise proven (`regime_backtest.py`, ~7,400 bars): bullish edge +0.22 @20d RISK-ON vs **−1.78 RISK-OFF (p<0.005)**, and the RISK-OFF baseline was *positive* — the signals actively pick bull traps below the 200 SMA, not beta. Shipped as `opportunity_daily.REGIME_GATE` + `_apply_regime_gate` (regime score-floor + name cap, applied in `run()` and the dashboard live pipeline). Residual → **B-32r** (exact floors still heuristic). Full history in [[analyses/Noise-Regime-Coverage-Postmortem]]. |
| ~~B-33~~ | **Conviction-sized shortlist (kill fixed top_n=100)** — ✅ **CLOSED 2026-08-26** | Score-floor replaces the flat `top_n` cut inside `_apply_regime_gate`, so the list sizes itself to conviction × regime. Floors data-calibrated (`regime_backtest.py --calibrate`, 55 names + kept-vs-tail test): **RISK-ON** floor ≈50 genuinely sorts (kept +0.4–0.5%, tail negative); **MIXED** edge ≈0, floor 50 is a mild filter only (the earlier "+1.2%" was a 15-name artifact); **RISK-OFF** `min_rating=None` + hard cap 5, since higher-rated names do *significantly worse* than the tail there. Floors are data-set, not judgment. |
| ~~B-34~~ | **Small/micro-cap "hidden treasures" lane** — ✅ **CLOSED 2026-09-02** *(2026-08-23)* | The funnel universe is `fetch_bhavcopy_top_volume` = top-by-traded-value = **large-cap only**; small/micro-cap multibaggers never enter. `multibagger_candidates.py` exists but is a standalone screener.in-gated screen. Build: a **FREE** small-cap universe (NSE Smallcap-250 / Microcap-250 constituents — no cookie) run through the multibagger criteria **plus the now-free NSE promoter% + pledge% checks** (its header's "pledge not scrapable" caveat is obsolete), surfaced as a deliberately SMALL high-conviction lane. **Measurable:** coverage (names outside the top-value set) + forward hit-rate of the criteria vs a Smallcap-250 benchmark. Closes the owner's core coverage gap. **STARTED 2026-08-24:** `smallcap_universe.py` (free 502-name NSE Smallcap-250+Microcap-250 universe, 24h cache) + `smallcap_discovery.py` (ranks by free FII+DII accumulation-rate + promoter conduct + pledge veto from `ownership_cache`; `--force` backfill added). **Full backfill DONE 2026-08-24** — 499/502 scoreable, pledge populated for 97 names (69 vetoed >5%: AFCONS 100%, STAR 38%…); top-15 surfaces real microcaps (CORONA, STLTECH, ASTRAMICRO, UJJIVANSFB, MASTEK) the large-cap funnel can't see. **Quality overlay DONE** (`_enrich_quality` ROCE/OPM/D-E bonus). **Dashboard lane DONE** (Hidden Treasures page in Screening group). **Hit-rate backtest MEASURED 2026-09-02** (`hidden_treasures_backtest.py`, 502 symbols, 6 eval quarters 30-SEP-2024…31-MAR-2026, top-25 vs equal-weight universe baseline): **edge +2.51% @60d (p=0.22), +6.29% @120d (p=0.14) → WEAK** — positive but not statistically significant. The ranking surfaces real small-cap coverage the large-cap funnel misses (its primary value), but conviction-ranked top-25 do not reliably beat a random universe pick forward. Same experiment shape as B-49/B-50. |
| B-35 | **Collapse 38 scanners into family "lenses" (UI)** *(2026-08-23)* — **MEASURED 2026-08-29** (`tools/scanner_overlap.py`, 110 names × 2,496 cells): **12 bullish scanners have ZERO unique cells** and are removable without breaking the invariant; **2 of them (Minervini VCP valchak, EMA-50 Coil) never fired at all** — dead, not redundant, triage before any UI change; the trend/momentum quartet (52W High Leaders / Momentum Continuation / Stage 2 / Pullback Entry) is one detector under four names (52W is **95% contained** in Momentum Continuation, 401 hits, 0 unique). Full table: [[analyses/Scanner-Overlap-Audit]]. Caveat recorded: overlap is not edge, and a zero-unique scanner may still add precision. | 38 scanners (13 Entry + 12 Pattern overlap on the same facts); the confluence **family** de-dup already fixes scoring but the UI still lists all 38 as independent choices. Build: default the Scanner Hub to a curated core, group the rest under their `SCANNER_FAMILIES` lens behind "advanced". **Verifiable invariant (not taste):** no unique hit is lost — every family stays reachable and the union of hits is unchanged. Behavioral noise reduction with a checkable guarantee. |
| ~~B-36~~ | **Regime posture header + nav consolidation** — ✅ **CLOSED 2026-08-26** | Regime-coloured posture banner atop the Opportunity Hub, pulled from the same `REGIME_GATE` it enforces (RISK-ON green "full run, rating ≥50" → RISK-OFF red "≤5 names — bullish signals below the 200 SMA LOSE"). Nav: folded the single-page Analytics group (Strategy Hub) into Research, 6 groups → 5, no page removed. Residual → **B-36r** (Screening-group trim, held for an owner usage call). |
| B-32r | **Calibrate exact regime floors** *(2026-08-27)* | The `REGIME_GATE` floors/caps shipped in B-32 have the right *direction* (measured) but the exact numbers are heuristic. Re-run `regime_backtest.py --calibrate` on a larger, walk-forward split once B-21 lands and set the floors from that, rather than the single-pass calibration. Small; gated behind B-21's out-of-sample split so the floors aren't fit on the same window they're tested on. |
| ~~B-39~~ | ~~**Pin scipy / make backtest.py scipy-optional**~~ — **CLOSED 2026-09-01** with B-29. `_ttest_1samp` and `_ttest_ind` now fall back to a normal approximation when scipy is absent, mirroring `funnel_backtest.py`. |
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
| RSI-Fibo Entry | RFE-1 hidden-divergence + 50% fib scanner | [[analyses/RSI-Fibo-Entry-Scanner-Roadmap]] |
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

The first measurement chore landed 2026-08-27 and immediately paid off:
**B-25 run for real showed confluence adds no significant edge at 5–20d** — the
Opportunity Hub's whole premise — and only a marginal +0.38% at 60d. The honest
"unmeasured" label had been hiding a premise that is, on this window, close to
false at the horizons that matter. That is why the running matters as much as the
building — and it also surfaced that the significance stack could not even import
(`scipy` was missing on the project interpreter), so "the tool exists" had been
true only on paper.

## Action Taken / Plan

**Suggested order (updated 2026-08-12):**

1. ~~**B-2** — one restart.~~ Done 2026-08-12.
2. ~~**B-20a + B-20b** — significance test and market-model edge.~~ Done 2026-08-12.
3. ~~**B-25** — measure confluence.~~ Done 2026-08-12 (`backtest_confluence`).
4. ~~**B-7** — volume threshold sweep.~~ Done 2026-08-12 (`sweep_volume_threshold`).
5. ~~**B-5** — time stops.~~ Done 2026-08-12 (6 scanners now emit `time_stop`).
6. ~~**B-19b** — support-breakdown detector.~~ Done 2026-08-12 (`scan_support_breakdown`).
7. ~~**B-3** — mean-reversion scanner.~~ Done 2026-08-12 (`scan_mean_reversion` Connors RSI2).

**Next (updated 2026-09-02):**

1. **B-42r** — settle the `pivot_len` 5-vs-15 split on data (harness, not taste).
2. **B-32r** — recalibrate regime floors with walk-forward (now unblocked).
3. **B-28r** — the option-OI event studies, now that the levels are on the chart:
   the **short-straddle break → short-cover rally** (the wall being *pierced* is
   the event, not the wall existing), plus first-touch rejection at a wall vs a
   matched non-wall strike, and whether price actually drifts to max pain.
4. **B-41 event study** — sweep-reversal vs a **matched clean break**. The two new
   scanners are unmeasured, and B-19's result (0/41 stable after costs) says to
   measure before adding them to any scoring path.
5. **B-31** — learned confluence weights (was gated behind B-19, now unblocked —
   but the B-19 results show most scanners have no edge after costs, so the premise
   of weighting them is weakened).
6. **B-35** / **B-22** — scanner family de-dup + lens UI (the B-19 + B-35 overlap
   audit together suggest a significant cull: 3 scanners never fire, 12 have zero
   unique hits, and most show no edge).

**Parked / gated:** B-38 full-funnel test is blocked on point-in-time fundamental
data, not code; B-31 (learned weights) is now unblocked but weakened by B-19's
finding that most scanners lack individual edge after costs; B-28/B-30 are
capability/research items; B-35/B-37 are noise-reduction/distribution polish
with no dependency.

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
