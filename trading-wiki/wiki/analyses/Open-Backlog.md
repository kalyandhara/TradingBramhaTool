---
title: "Open Backlog — the living index"
category: analysis
tags: [backlog, index, roadmap, open-items, measurement-debt]
timeframe: milestone-plan
created: 2026-08-07
updated: 2026-09-10
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

**Re-verified again on 2026-09-10, and the drift rate has NOT improved — it has
just moved.** The recent, actively-worked entries (B-57…B-64) are accurate to the
commit log; the drift is now entirely in the **old, unworked** items, which is the
harder half because nobody re-reads them. Found this pass: **B-3** and **B-19b**
still carried full "nothing implements it" / "zero occurrences" essays in P2
although the top ledger closed both on 2026-08-12 (`scan_mean_reversion`,
`detect_support_breakdown` + `scan_support_breakdown` all present), and **B-10**
had silently shrunk from four uncached symbols to **one** (`BSE`), which also
undercuts its stated diagnosis. Three of the four items sampled had moved.
**The rule that keeps producing this: an item is only re-read when it is worked,
so the staleness concentrates exactly where confidence is highest.** Bodies
corrected in place below, each marked with the date.

## Status since 2026-08-02

| | |
|---|---|
| **Closed** | B-1 (2026-08-05), B-14 (`ephem` now installed), B-18 (remote pushed 2026-08-07), **B-2 (chart_server restarted 2026-08-12, /rsi_divergence.js HTTP 200)** |
| **Closed 2026-08-12** | **B-3** (mean-reversion scanner — `scan_mean_reversion` Connors RSI2, registered), **B-5** (time_stop emitted by 6 scanners: Harmonic/RSI60-40/OrderBlock/FallingWedge/SupportBreakdown/MeanReversion), **B-19b** (support-breakdown detector — `scan_support_breakdown` + `detect_support_breakdown`), **B-20a** (t-test + 95% CI on edge in `_aggregate`), **B-20b** (market-model beta/alpha when benchmark_df supplied to `backtest_scanner`), **B-25** (`backtest_confluence` + `format_confluence_report` measure co-fire vs single-fire), **B-7** (`sweep_volume_threshold` sweeps 1.0/1.2/1.5/2.0× vol floors and ranks by edge) |
| **Closed 2026-08-26** | **B-32** (regime output throttle — `_apply_regime_gate` + `REGIME_GATE`, premise proven `regime_backtest.py`), **B-33** (conviction-sized shortlist — score-floor replaces fixed `top_n`, floors data-calibrated), **B-36** (regime posture banner + Analytics→Research nav fold) |
| **Closed 2026-09-01** | **B-21** (walk-forward OOS pooling + per-horizon stability), **B-29** (Indian delivery cost model ~29bps, applied everywhere), **B-39** (scipy-optional fallback) |
| **Closed 2026-09-02** | **B-16** (OI Momentum `_strength_color` → `rs.TOKENS`), **B-24** (RSI divergence Python/JS agreement — `detect_bullish_rsi_divergence` rewritten to Wilder RSI + pivot lows + 3-pt gap), **B-34** (small-cap lane complete — quality overlay + dashboard lane shipped earlier; hit-rate backtest measured → WEAK, see below), **B-42** (shared market-structure read — HH/HL/LH/LL sequence + state + premium/discount + sequence-vs-breaks `agreement`; invariant clean on 30 large-caps; residual **B-42r**), **B-41** (liquidity sweep / stop hunt — pools + bidirectional detector + Entry & Risk scanners, built on B-42's equal-level labelling; SMC stack complete at 44 scanners), **B-23** (strike-level option OI — `option_chain.py` max pain + OI walls for stocks AND indices, `/api/option_levels`; premise was stale, B-44 had already built the per-strike feed), **B-28** (the overlay — `oiwalls` indicator via `createPriceLine`, expiry selector, unmeasured caveat; residual **B-28r**) |
| **Closed 2026-08-27 (re-verify)** | **B-11** (MFI — `scan_mfi_oversold` + `_mfi_series` shipped and registered; page had it "absent"). Ledger/body sync only: **B-5, B-25, B-20a, B-20b, B-7** were already code-complete but mis-filed as open in the body |
| **Closed 2026-09-09** | **B-62** (turnover-share rotation column), **B-63a** (`tools/columns.py` shared column registry), **B-63b** (row_metrics — the nine "how long has this been true" columns, incl. the RS-rank walk and in-row Notes), **B-64** (canonical sector vocabulary). Also shipped that day and NOT from the backlog: the liquidity-floor sweep across all 20 `cached_fetch_ohlcv` call sites (7 by-name callers switched to `enforce_liquidity=False`) |
| **Closed 2026-09-10** | **B-63a targeted sweep** — registry now **46 ids, 15 aliases, 9 documented refusals**; the "incomplete by design, 4 of 43" claim was retracted (28 call sites pass `column_config`; 15 already reach the registry). Singletons deliberately declined rather than promoted |
| **Measured 2026-09-10** | **B-65** (`pmax_edge.py`) — **PMax scored for the first time, and it FAILS.** Flip **−0.55% (p=0.511, n=1,538)**; **state (dir=1) −0.19% on 129,761 bars** — *below* the unconditional baseline in a bull window stacked in its favour, so the pre-registered confound did not save it. Completes a four-detector convergence: Renko −1.01 / STAI-only −1.00 / PSAR-only −0.77 / **PMax −0.55**, no shared code, one mechanism (an up-flip re-enters only after price gave part of the run back), PMax shallowest exactly as its rarer/slower cadence predicted. Only B-43r is individually significant. **Does not retire `W_PMAX_1H`** (a STATE on NIFTY 1H — a different claim) but removes the presumption it is safe, and makes the 1H measurement live. Nothing removed on a null |
| **Measured 2026-09-10** | **B-59r** (`psar_stai_edge.py`, 460 names) — **NEITHER twin carries information.** AGREE (n=4,068) **+0.16% p=0.820** ≈ market; **PSAR-ONLY −0.77% (p=0.053, n=8,576)**; **STAI-ONLY −1.00% (p=0.150, n=1,909)**. Pre-registered "both null" row: trim falls back to cost — keep STAI, PSAR stays an overlay, **nothing deleted**. The shape is the finding: agreement pays the market, disagreement loses in BOTH directions, and −0.77/−1.00% sit beside **B-43r's −1.01% for the Renko flip** — a fourth detector landing on the same mechanism (an up-flip re-enters after price has given back part of a run). Neither p clears 0.05, so convergence, not proof. Leaves **PMax as the only one of the three never scored**, while carrying 20% of the sentiment index |
| **Counted 2026-09-10 (v2, chance-corrected)** | **B-59** re-run with a rotation null after the owner asked whether PMax can be sunset. Raw coverage was mostly base rate; corrected, **PSAR↔STAI agree far above chance (+34.2 lift at ±3) while PSAR↔PMax agree BELOW chance at every tolerance (−12.4 at ±3)**. So: **no, PMax cannot be sunset in favour of PSAR** — it is the least-alike pair, and PMax additionally carries 20% of the sentiment score, a `market_verdict` factor and the chart's trade-state panel. The real redundancy is PSAR↔STAI, and choosing between those two is an edge question nobody has measured. B-46 stands, on better grounds |
| **Counted 2026-09-10** | **B-59 overlap check** (`psar_overlap.js`, 460 names / 322,608 bars) — **PSAR is a SUPERSET, not a subset**: 28,582 flips against PMax 3,396 and STAI 13,050 (8.4× / 2.2×), 68.9% of them uncovered at ±3 bars, while PSAR itself covers 92% of STAI and 70% of PMax at ±10. B-46's zero-unique-cell objection does NOT survive — but it is replaced by a sharper one, since PSAR's whole content is its extra flips. Gate did not close; an edge test on the UNIQUE cells specifically is now owed. PSAR stays a drawn overlay meanwhile |
| **Measured 2026-09-10** | **B-58** (`quasimodo_study.py`) — **INCONCLUSIVE, UNDERPOWERED**: 53 QM zone entries across 356 names / 3 years against a pre-registered floor of 200, and too few for a rotation p to be computable at all. Not a null; the pattern is too rare to measure to this desk's bar on daily bars in one market. QM stays geometry, PIPELINE_EXCLUDED. Three process catches recorded: the equivalence check aborted on SCOPE (355/355 once windowed), the pre-registered baseline could not contain its own signal (a QM's left shoulder is by definition a broken low), and the HARNESS clause fired but was resolved as uninformative when the panel reproduced B-43's null at −0.05% |
| **Corrected 2026-09-10 (re-verify)** | **B-3** and **B-19b** bodies said "absent" for four weeks after the ledger closed them; **B-10** is down to one symbol (`BSE`), not four; **B-17** re-verified still absent and now covers two shipped OBV surfaces |
| **Still open** | B-4/B-12, B-6, B-8, B-9, B-10, B-13, B-15, B-17, B-21b, B-22, B-26, B-27, B-30, B-31, B-35, B-37, B-28r — **all re-verified open 2026-09-10** except B-10, which shrank to a single symbol. Spot checks: no AVWAP anchor UI (`avwap` appears in `scanner_templates.py` only), no Volume-Profile 80% rule anywhere in `session_volume_profile.js` / `volume_profile.js`, and `sentiment_index.py` still carries **four** weighted factors (30/25/25/20) with the PCR factor 5 a docstring line only — even though `pcr.py` is now consumed by `dashboard_app.py` in three other places, so B-22 is wiring, not a build |
| **Open — residual only** | **B-35** (family-lens UI, not started), **B-37** (volume share-card, not started), **B-38** (delete-funnel shipped; blocked only on point-in-time fundamentals for the full backtest) |
| **New 2026-08-27** | **B-32r** (calibrate exact regime floors — currently heuristic), **B-39** (pin `scipy` in requirements / make `backtest.py` scipy-optional — the hard import silently broke the significance stack on Python 3.14) |
| **New 2026-08-27 (strategy-coverage gaps)** | **B-40** (VWAP as a signal — **scanner SHIPPED same day**), ~~**B-41**~~ (**CLOSED 2026-09-02** — `detect_liquidity_pools` + `detect_liquidity_sweep` + both scanners; SMC stack now complete), ~~**B-42**~~ (**CLOSED 2026-09-02**; residual **B-42r** — the pivot_len 5-vs-15 split, to be settled on data). Intraday lane (ORB/DOM/scalping) recorded as an explicit out-of-scope decision. From the profitable-trader strategy-combination audit. |
| **Closed 2026-09-05** | ~~**B-44r**~~ **MEASURED → FALSIFIED, GEX retired** (magnitude convention inverted the pre-registered direction and what survives the 1/σ control flips sign between vol terciles — see below). **B-34r** *(new, shipped same day)* — **Hidden Treasures gained its first HARD gate**: `red_flags.py` (FR-4) wired into `smallcap_discovery`, critical flags veto, watch flags cost 6 pts, NOT_CHECKED never reads as a pass. Zero extra fetches (rides the quality overlay's payload; `sessionid=None` keeps screener.in dormant). **Vetoes 100 of 249 on Smallcap-250** — 59 negative FCF, 51 promoter stake reduction, 28 pledge, 5 dilution. Toggleable and every exclusion is listed, because the default is NOT settled: see **B-34r2**. |
| **New 2026-08-29** | ~~**B-43**~~ **BUILT + MEASURED → clean null** (flip edge ~0, negative on the long leg; beat buy&hold 0/23 — but fires 40% less often than the EVWMA cross, i.e. noise reduction without edge). Chart overlay kept, labelled FLIP not BUY/SELL. MCX still gated. From the Renko podcast ingest. ~~**B-44**~~ **BUILT + MEASURED same day → clean null** (see below); residual **B-44r** (is the naive dealer convention backwards for NSE?). From the Chris Kmer order-flow ingest. |
| **New 2026-09-07** | ~~**B-57**~~ **PRE-REGISTERED then MEASURED same day → FAILS the bar** (edge **−0.25%**, p_rot=0.714, n=207). Owner proposed a Renko flip + ≤40%-correction + revenue/cash-flow screen. `tools/renko_quality_cardinality.py` counted first and **killed the 40% version before any return was scored**: 4,407 of 4,598 flip_ups (96%) clear a 40% cap, so it is not a filter, and its median `bricks_in_prior` = 3 sits on B-43r's worst bucket (−1.30%). The ≤10% rung was the only uncovered one; `tools/point_in_time_quality.py` (12 tests) closed the lookahead leg. Result: **B-43/B-43r stand**, but the null is **soft** — B-43r's −1.01% (p=0.000) dissolves to −0.25%, which is what its own mechanism predicts. CONTROL2 misbehaved (+3.37%, p=0.211); a HARNESS arm reproducing B-43's null (+0.49%, p=0.376) cleared the scorer, so that control is uninformative rather than contradictory. Cite as "no edge found, underpowered", not a settled zero. |
| **New 2026-09-07 (from a QM/CHOCH setups chart)** | **B-58** (**DETECTOR BUILT, measurement not run**) — coverage audit of a "4 Setups for BUY Entry / QM patterns" chart: CHOCH, key levels, order blocks, the fib grid and the stop-hunt read are all already present, and the two missing rungs (**88.6% entry, 113% stop**) were **added to `fibonacci.js` the same day** (drawn only — deliberately NOT wired into `buildPlan`, since changing what a stop means is a measurement, not a default). The image's setups 1–3 are the retrace-after-structure-break family this desk has measured NEGATIVE three times (`ICT Setup` −0.36%/−1.24%, `Order Block Retest` −0.47%/−0.70%, `Pullback Entry` −0.43%/−1.12%, ~9,000 signals), so they are not proposed. Setup 4's stop-hunt mechanic is `Liquidity Sweep`, **already measured POSITIVE** (B-41m, +0.51% @20d p=0.005). The one real gap is the **QM geometry** itself — the `RH > LH` CHOCH plus a left-shoulder entry, which is what distinguishes it from an inverse H&S. `detect_quasimodo` built the same day with 17 tests. Two corrections came out of running it: the right shoulder had to become OPTIONAL (it is the retracement into the zone, so requiring a confirmed pivot made the setup visible only after it was untradeable), and the four pivots had to be made CONSECUTIVE — searching them independently reported a "pattern" on **73%** of 460 names, adjacency cut that to **44%**, and only **14 (3%)** have price in the zone with the head unbroken. Pre-registration written, skeptical prior, measurement NOT yet run. Multi-timeframe liquidity ("HTF LQ") deferred; note `HTF` in this repo means High Tight Flag, not higher timeframe. |
| **New 2026-09-07 (from a PSAR chart)** | ~~**B-59**~~ **BUILT same day** — Parabolic SAR was absent (the `sar` key in `evwma_vwap_macd_backtest.py` is stop-and-reverse EQUITY, not Wilder's dots; not in `INDICATOR_DEFS`, so it cannot be charted). Scoped as an **overlay only**: B-46 already ruled PSAR out, but that objection was about a SCANNER creating a zero-unique registry entry next to `pmax`/`stai` — an overlay makes no claim and votes in nothing, which is the same split B-46 itself used for Ichimoku. Wilder's parameters and the two-bar penetration clamp are pinned in the entry, along with the causality requirement (bar *i*'s dot from bars ≤ *i−1*, so it does not repaint). No backtest owed for the overlay; before any PSAR *signal*, the first measurement owed is an **overlap check against `pmax`/`stai`**, not an edge test. `psar.js` + 11 tests, verified on RELIANCE.NS (2,598 dots over 2,600 bars, no console errors); drawn as dots rather than a line, and with NO flip markers since pmax/stai already draw arrows on that pane. **A chart server already running returns 404 for `/psar.js` until restarted.** |
| **New 2026-09-07 (from a Screeningmantis screenshot)** | ~~**B-60**~~ **BUILT same day** — **sector money-flow heatmap**: sectors x `today/1W/2W/1M`, shaded by Chaikin Money Flow, with a Trend column, on the Sector page and pipelined to Home with positive-flow sectors highlighted. Indicator ingested to [[concepts/Chaikin-Money-Flow]]. Mostly **assembly, not invention** — `nse_universe`, `sector_rotation.SECTOR_INDEX_MAP`, the Sector Map page, the Home `_action_card` hook and `_batch_history` all already exist, and no new data source is needed. Two design calls recorded up front: aggregate by **summing money-flow volume over the sector and dividing by summed volume** (a mean of constituent CMFs lets a smallcap outvote a heavyweight), and the four columns are **overlapping 21-bar windows, not independent observations**. Ships as a VIEW — no entry/stop/target, not in `SCANNERS`, never a confluence vote. **Live: 500/501 symbols, 20 sectors**, readings inside ±0.25 as the clip assumes; a test shows the naive mean INVERTS a sector's reading vs volume weighting. The live run caught an integration bug no unit test would have (`_batch_history` returns capitalised OHLC columns). |\n| **New 2026-09-07 (from LuxAlgo's OBV-divergence page)** | ~~**B-61**~~ **BUILT same day** — OBV Divergence on the chart, beside RSI Divergence. Contains **no divergence walk**: it computes OBV and hands it to `RSIDIV.compute` through the injection point that module already exposes, so there is one implementation of the four-variant table rather than two to drift. Two things recorded because they change how it reads: **OBV is an unbounded running total**, so it trends and divergences are cheaper to satisfy than RSI's — expect more, and do not read the extra ones as extra evidence; and every divergence carries **`volConcentration`**, the largest bar's share of its window's volume, which MEASURES the single-huge-print artifact LuxAlgo says to inspect by hand (chart marks ≥0.5 with `!`). Live on RELIANCE.NS: 6 divergences, all 0.12–0.14 concentration. The browser caught a first-activation half-render (`setTimeout` retry, not rAF, which does not fire in a hidden tab). Context, not a signal; an **overlap check against the RSI pane** is owed before any OBV-divergence signal. |\n| **Closed 2026-08-27** | **B-36r** (Screening nav trim — Breakout Screener + TradingView Screener folded into one "Breakout Scans" page with a source toggle; 8 → 7) |
| **Measured 2026-08-27** | **B-25** first actually run (`backtest_confluence`, 13 bullish scanners × LIQUID_50): co-fire lift is significant **only at 60d (+0.38%, p=0.025)**, trivial + non-sig at 5–20d — confluence is *not* the additive swing-horizon edge the Hub premise assumes. Required installing `scipy 1.18.1` (backtest's hard scipy import was broken on Python 3.14) |
| **Shipped 2026-09-02 (not from the backlog)** | **Trending Stocks page** — `trending_stocks.py` + a Market-Intel page with four lenses: Price Movers (whole-market bhavcopy, turnover-floored), Volume Shockers (reuses `volume_anomaly` **with cause attribution** — the one lens the desk does better than the commercial screener it was modelled on), 52-Week and All-Time High/Low (computed from batched history over a bounded top-N-by-turnover universe, since NSE's UDiFF bhavcopy carries **no 52-week columns** — verified, 34 columns, none a range extreme). Requested from a screenshot of a commercial "Trending Stocks" page. **Deliberately NO "Most Visited" lens** — that is crowd page-view data from a site's own traffic logs, there is no free public feed for retail attention, and a proxy (delivery spikes, rank churn) would measure something else under the same label. Recorded as a decision, not an oversight, the same way the intraday ORB/DOM lane is. Two things the build forced: a **turnover floor**, without which the movers list is almost entirely penny stocks (a ₹3 share moving 19% is arithmetic), and a **cash-equivalent filter** reusing the chart's existing `isLikelyLiquidETF` definition, because a liquid ETF is *permanently* at its all-time high by construction and squatted on the first ATH run. |
| **Measured 2026-09-02** | **B-19** batch walk-forward on all 41 scanners (LIQUID_50, 3 windows, Indian delivery ~29bps): **0/41 stable** across all horizons; 11 show positive 20d edge but all UNSTABLE; strongest = %R Bottoming (+2.68% @60d, stable @20d+60d), Falling Wedge (+1.58% @60d); **most scanners show negative edge after costs**. 3 too-few-signals (High Tight Flag, Minervini VCP, RSI-Fibo Hidden Div). 3/5 risk scanners show bearish edge. Full table in `tools/cache/b19_verdicts/_summary_table.txt`. |

## Left open by the 2026-09-07 session — carried forward, re-checked 2026-09-10

Everything below is committed and pushed (`96a3112..5562552`). These are the
threads that were deliberately NOT closed, with why, so none of it has to be
reconstructed from the commit log.

| # | pending | where | why it was left |
|---|---|---|---|
| 1 | **Restart the chart server** | operational, 2 min | `chart_server.py` serves each module from an explicit Flask route and runs without the reloader, so an instance that was already running returns **404 for `/psar.js`**. Observed live during verification. Nothing to fix in code. |
| ~~2~~ | ~~**B-58 · run the QM measurement**~~ **RUN 2026-09-10 → INCONCLUSIVE, UNDERPOWERED (53 events vs a floor of 200)** | [[#B-58]] | `detect_quasimodo` is BUILT (17 tests) but is geometry only — no scanner registered, no forward returns scored. The pre-registration and its control (relax `RH > LH`; if the score is unchanged the detector is an inverse-H&S finder) are written and unrun. Prior recorded: skeptical — the honest hypothesis is *"QM is a liquidity sweep with extra steps"*. |
| ~~3~~ | ~~**B-59 · PSAR overlap check**~~ **RUN 2026-09-10 → PSAR is a superset, gate did not close** | [[#B-59]] | Owed BEFORE any PSAR signal, and it is an **overlap** check against `pmax`/`stai`, not an edge test. B-46's objection is that the flip may carry zero unique cells; if PSAR's flips are a subset of PMax's there is nothing left to measure. The overlay itself needs no backtest and ships as-is. |
| 4 | **B-57 · secondaries** | [[#B-57]] | The primary FAILED (−0.25%, p_rot=0.714) and that is settled. Unrun: the 60d horizon, the quality gate tightened from a sign test to a top-quartile OCF rank, and `depth_from_flip` as the depth definition. All were pre-registered as non-decisive, so they describe rather than rescue. |
| 5 | **B-58 residual · multi-timeframe liquidity** | [[#B-58]] | "HTF LQ" from the source chart. `detect_liquidity_pools` takes one `df` — single timeframe. Bigger build, own entry when picked up. **Naming trap:** `HTF` in this repo means **High Tight Flag**, not higher timeframe, so grepping for it gives false confidence the feature exists. |
| ~~6~~ | ~~**B-60 · sector money-flow heatmap**~~ | [[#B-60]] | **BUILT 2026-09-07** — `money_flow.py` + 18 tests, on Sector Map and Home, verified in the running dashboard. Ships as a view; unmeasured. |
| 7 | **Fib rungs are drawn, not wired** | `fibonacci.js` | 0.886 and 1.13 exist as levels but do NOT feed `buildPlan`: 0.886 is entry-ineligible without `{deepEntry:true}`, and 1.13 never becomes the stop. Adopting either changes reward-to-risk — and therefore the `actionable` flag — on plans unrelated to QM. **Changing what a stop means is a measurement, not a default.** |

> [!note] The one thing worth carrying forward from this session's method
> Twice, counting BEFORE measuring saved a week. `renko_quality_cardinality.py`
> killed the 40% correction cap by showing 96% of flips clear it, and the QM
> detector's first version reported a "pattern" on 73% of names until the pivots
> were required to be consecutive. **A filter that admits almost everything is not
> a filter, and that is cheaper to discover by counting than by backtesting.**

**Status of that table on 2026-09-10:** rows 2 and 3 were **run this session**
([[#B-58]] — inconclusive for lack of events, not a null; [[#B-59]] — PSAR is a
superset of pmax/stai, so the gate did not close); rows 4, 5 and 7 are **still
open and untouched** — the 2026-09-09/10 sessions went into the column library
(B-62/63/64) instead, which was the owner's ask, not a slip. Row 1 (chart-server
restart) is operational and cannot be verified from the repo; `psar.js` exists on
disk, so the only question is whether the running process predates it. **Nothing
in that table has aged badly, but note what it is: four of the five survivors are
MEASUREMENTS owed, not builds.** That is the standing shape of this backlog — the
desk builds faster than it measures.

## Refinement pass 2026-09-10 — what is actually next

Ranked by *what the desk cannot currently answer*, not by size. No new items were
invented in this pass; this is the existing page, sorted.

| Rank | Item | Why it is next | Cost |
|---|---|---|---|
| 1 | **B-58 · run the QM measurement** | The only BUILT-but-UNSCORED detector on the page. `detect_quasimodo` + 17 tests exist, the pre-registration and its control are written, and the skeptical prior (*"QM is a liquidity sweep with extra steps"*) is recorded. Leaving a built detector unmeasured is precisely the debt B-19 was raised over. | One measurement run |
| ~~2~~ | ~~**B-59 · PSAR overlap check**~~ — **DONE 2026-09-10.** It did NOT close: PSAR is a superset at 8.4× PMax's cadence, so an edge test on its unique cells is now owed as its own item | Cheap, and it is a **gate**: if PSAR's flips are a subset of `pmax`/`stai`, every downstream PSAR idea is dead and no edge test is owed. An overlap count, not a backtest — the counting-first method that saved a week twice in the 2026-09-07 session. | Hours |
| 3 | **B-22 · wire sentiment factor 5 (PCR)** | Now the cheapest real capability on the page: `pcr.py` is built, calibrated and already consumed three times in `dashboard_app.py`; `sentiment_index.py` still runs on four weighted factors (30/25/25/20) and documents the fifth in a docstring. Wiring, not a build — and it re-weights a number the desk already shows. | Small |
| 4 | **B-10 · one symbol, `BSE`** | Was a four-symbol systematic-bug suspicion; it is now a single name. Close it or retire it — a one-line item that has survived five weeks of re-verification costs more to re-read than to fix. | Minutes |
| 5 | **B-17 · OBV concept page** | Two OBV surfaces now ship (the indicator + B-61's divergence overlay) and neither is documented. B-60 wrote its CMF page with the build; this is the same debt, already incurred. | Small |
| 6 | **B-57 secondaries** | Explicitly pre-registered as non-decisive (60d horizon, top-quartile OCF gate, `depth_from_flip`) — they describe rather than rescue. Do them only if a session has slack. | Small, low value |

**Not promoted, and why:** B-35 (family lenses) is measured and ready, but it is a
UI change over 38 scanners that **B-19 found mostly have no edge after costs** —
reshaping the presentation of an unproven set is motion, not progress. B-31
(learned confluence weights) stays parked behind B-25, whose own answer was that
confluence is *not* the additive swing-horizon edge the Hub premise assumes. B-30
(Pushya) is worth running only to retire it, and the desk already holds three
astro nulls.


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

### ~~B-3 · No mean-reversion scanner~~ — CLOSED 2026-08-12 *(body corrected 2026-09-10)*
The 2026-08-07 finding was that `REGIME_PLAYBOOKS["SIDEWAYS"]` prescribed a
mean-reversion scanner and nothing implemented it. **`scan_mean_reversion`
([scanner_templates.py:4633](tools/scanner_templates.py:4633)) is the Connors
RSI2 stretch-and-revert scanner, registered, and it emits `time_stop`.** The
ledger closed this on 2026-08-12; the body kept the "nothing implements it"
essay for a further four weeks. Same drift as B-5/B-11/B-19b — see the
re-verification note at the top.

### ~~B-5 · Time stops: plumbed, and emitted by nothing~~ — CLOSED 2026-08-12
The 2026-08-07 finding was that `time_stop` was consumed by `backtest.py` but
written by no scanner (zero occurrences in `scanner_templates.py`). Re-verified
2026-08-27: **9 occurrences in `scanner_templates.py`** — six scanners
(Harmonic/RSI60-40/OrderBlock/FallingWedge/SupportBreakdown/MeanReversion) now
emit it and the harness reads a field that is actually written.

### ~~B-19b · No support-breakdown detector exists anywhere~~ — CLOSED 2026-08-12 *(body corrected 2026-09-10)*
**`detect_support_breakdown` ([scanner_templates.py:3119](tools/scanner_templates.py:3119))
+ `scan_support_breakdown` ([scanner_templates.py:3188](tools/scanner_templates.py:3188))
ship the mirror detector**, and `test_liquidity_sweep.py` exercises it. The
original 2026-08-07 finding, kept for the record:

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

### ~~B-40~~ · VWAP is a chart line, not a signal — **CLOSED 2026-09-06: MEASURED NEGATIVE**
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

**The open measurable claim is now closed, and the answer is worse than null.**
Ran 2026-09-06 on 50 symbols, **2745 signals**:

| horizon | hit% | edge% | p | net-of-cost median |
|---|---|---|---|---|
| 5d | 52.3 | −0.02 | 0.77 | −0.14% |
| 10d | 50.9 | **−0.20** | **0.042** | −0.16% |
| 20d | 51.9 | **−0.45** | **0.0006** | −0.02% |
| 60d | 57.4 | **−0.50** | **0.033** | +1.85% |

**A VWAP reclaim does not merely fail to predict — it selects bars that do WORSE
than a random bar from the same pool.** −0.45% @20d at p=0.0006 is the most
statistically solid number this desk has produced on a VWAP rule in either
direction. Net of Indian delivery costs the hit rate is under 50% at 5/10/20d and
the median return is negative at all three.

> [!key-insight] Independently corroborated by B-19, which nobody had connected
> B-19's batch walk-forward (2026-09-02, LIQUID_50, 3 windows, ~29bps) already had
> VWAP Reclaim/Support at **−0.58% @20d / −0.93% @60d on 2706 signals, "NO EDGE
> [UNSTABLE]"**. Today's run measured −0.45% @20d on 2745 signals through a
> different harness. **Two independent measurements, same sign, similar magnitude** —
> which raises confidence in the negative well above what one run supports. The B-19
> number was sitting in `cache/b19_verdicts/` for four days and nobody joined it to
> this item; `claims_lint` surfaced it while sweeping for stale claims.

**Two things explain the shape, and both were foreseeable from this item's own
notes.** It fires 2745 times against VWAP Mean Reversion's 275, so the gates are
loose — "a stock in an uptrend near its mean" rather than an event — which is also
why an effect this small is detectable at all. And the design correction recorded
above says the first cut never fired and the gates were loosened until it did.
This is what that loosening bought.

**Not a licence to fade reclaims.** That is a different claim, needs its own
pre-registered test, and −0.45% would not survive costs on the short side either.

**No R-multiple line:** the scanner emits no entry/stop/target. Adding one now
would measure a trade plan invented after the fact, on a signal already shown to
select badly. Left as it is.

**Consequence applied, in two steps.** First demoted to `MEASURED_WEAK_SCANNERS`
(0.25, from 0.5). **That was not enough** — a weak weight still counts toward
`FULL_CONFLUENCE`, so a detector measured *negative* could still help push a name
onto the shortlist. It is now in **`PIPELINE_EXCLUDED`**, the same enforcement
Renko Flip gets under B-43, one step further along: Renko measured NO edge, this
measured a negative one, and letting it vote would spend ranking weight *against*
the ranking.

It stays registered, visible and runnable in the Scanner Hub, and backtestable.
The measurement rules out a vote, not the view. VWAP Mean Reversion stays at
weak weight — null is not negative, so a quarter-vote is the honest setting.

**Still open:** the **anchored-VWAP-from-catalyst** support read (earnings /
breakout / IPO anchor) + the chart's click-to-anchor — that half is **B-4/B-12**
and is untouched by this result, since it is a different mean and a different
claim.

> [!key-insight] All three VWAP-derived rules on this desk have now been measured
> EVWMA/VWAP MACD crossovers: no edge, stop-and-reverse −29% vs buy&hold +827%
> (2026-08-29). VWAP Mean Reversion: null, −0.19R after costs (B-40m). VWAP
> Reclaim/Support: significantly negative (this item). Three rules, three
> different mechanisms — momentum, reversion, trend-pullback — all built on the
> same mean, none of them a trigger. **On NSE daily bars VWAP is context.**
>
> The untested case is the one all three were adapted FROM: the intraday session
> VWAP. That needs an intraday store this repo does not have — a data gap, not a
> parameter to tune, and not a reason to re-open the intraday lane.

**Adjacent measured result (2026-08-29) — a *different* VWAP rule, tested and dead.**
The owner's TradingView `EVWMA_VWAP_MACD[QN]` BUY/SELL strategy was ported into the
chart tool (`evmacd`) and put through the same harness: **no edge at any horizon**
(BUY-cross +0.10/+0.04/+0.17/+0.04% at 5/10/20/60d, p 0.32–0.91, 23 names × ~19y),
stop-and-reverse median **−29%** vs buy&hold **+827%**. Full write-up in
[[concepts/EVWMA-VWAP-MACD]]. This does **not** settle B-40's open claim — that one
is about the *reclaim/pullback-hold* event on a rolling 20-day VWAP, a different
rule — but it is a second data point that VWAP-derived **crossovers** are context,
not triggers, and the reclaim scanner should be measured expecting the same.

### ~~B-40m~~ · VWAP mean reversion + volume — **BUILT + MEASURED 2026-09-06 → NULL, NEGATIVE AFTER COSTS**

Prompted by a "VWAP Mean Reversion + Volume" playbook card. The rule: price deviates
far from VWAP on EXTREME volume, rejects, and reverts to the mean on RISING volume.
Long below VWAP, short above, exit at VWAP.

**Nothing here could express it, which is why it was worth building.** `evmacd` fires
when price pulls AWAY from the volume anchor — the opposite trigger, and already dead
(B-40's adjacent result). `scan_vwap_reclaim` is long-only, with-trend, and treats
volume as a participation floor. What is new is the **double volume role**: capitulation
volume marking the deviation, then rising volume confirming the turn. A reversion on
falling volume is the failure case the rule exists to skip, and no existing tool could
say that.

**Shipped as one rule in two places** so it could be graded rather than admired:
`tools/vwap_mean_reversion.js` (chart bands + BUY/TRIM arrows) and
`scan_vwap_mean_reversion` (registry #45). Both report which VWAP they used —
`session` intraday, `rolling` on daily+ — because those are different claims.

**Forward returns (50 symbols, 275 signals, ~1500 bars each):**

| horizon | hit% | edge% | p |
|---|---|---|---|
| 5d | 54.9 | +0.19 | 0.51 |
| 10d | 53.5 | +0.19 | 0.57 |
| 20d | 56.0 | +0.72 | 0.14 |
| 60d | 62.9 | +1.54 | **0.053** |

**The 60d number is a trap and is recorded as one.** The rule targets VWAP — 3-6% away,
10-bar time stop — so its claim lives at 5-10d, where the edge is +0.19% at p≈0.5. An
edge that appears only well beyond the holding period is drift, not the rule.

**The R-multiple sim is the decisive test, and it settles it:**

| | expectancy | win% | target / stop / time |
|---|---|---|---|
| gross | **+0.04R** | 43.1 | 50 / 53 / 13 |
| Indian delivery ~29bps | **−0.19R** | 43.1 | 50 / 53 / 13 |

n=116 (long side only; the sim is long-only and the bearish half is a trim read anyway).
Target hit 50 times, stop 53 — a coin flip at ~1:1. Gross expectancy is zero with a
rounding error; **realistic NSE costs make it a losing rule.**

**Third VWAP-derived rule measured to nothing on this desk.** EVWMA/VWAP MACD crossovers
outright (2026-08-29), this one now; `scan_vwap_reclaim` remains the one unmeasured VWAP
claim. The pattern is consistent enough to state: **on NSE daily bars VWAP is context,
not a trigger.**

**The honest limitation, which is a DATA gap and not a parameter to tune.** The playbook
rule is natively intraday against a session VWAP. On daily bars a session VWAP collapses
to the bar's own (H+L+C)/3, so what was measured is the rolling-VWAP variant — labelled
`source: 'rolling'` in both implementations precisely so the two are never conflated.
Testing the poster's actual claim needs an intraday store this repo does not have. That
is the same wall B-40 hit and the same one the intraday lane was explicitly scoped out
over; **it is not re-opened by this result.**

**Kept, not deleted.** The bands are a genuine chart read — "how stretched is this, for
this symbol, lately" — and the scanner is honest coverage of a setup the funnel has no
other way to see. What is retired is any claim that it triggers.

**Cross-implementation checking earned its keep.** The JS trailing volume average summed
19 bars over a divisor of 20, inflating every multiplier ~5% and firing a TATASTEEL
signal the Python correctly rejected. Neither implementation looked wrong alone; they
only disagreed. They now agree signal-for-signal on RELIANCE / TATASTEEL / DLF.

### ~~B-60~~ · Sector money-flow heatmap (CMF) — **BUILT 2026-09-07**

From a Screeningmantis screenshot the owner brought in: sectors down the rows,
`today / 1W ago / 2W ago / 1M ago` across the columns, each cell shaded red-to-green
by Chaikin Money Flow, and a **Trend** column labelling each row *Accumulation /
Distribution / Increasing / flat*. Wanted on a sector-analysis page and pipelined
to Home with positive-flow sectors highlighted.

Indicator ingested to [[concepts/Chaikin-Money-Flow]] — formula, the ±0.25
practical range that sets the colour scale, and the gap flaw that bounds what it
can claim.

**Why CMF is the right statistic for a sector heatmap, in one line:** it divides
by total volume, so it is a bounded ratio in [-1, +1] and a ₹40,000cr sector and a
₹400cr sector produce directly comparable numbers. Raw traded value does not, and
that single property is what makes a cross-sector grid legible at all.

## What already exists — this is mostly assembly, not invention

| piece | where | |
|---|---|---|
| sector → constituents | `nse_universe.fetch_constituents`, `.index_for_sector` | reuse |
| sector index tickers | `sector_rotation.SECTOR_INDEX_MAP`, `.index_for_industry` | reuse |
| a Sector page + RRG | dashboard "Sector Map" | mount point |
| Home action-card pipeline | `_action_card(... "Sector Map", "sect")` | the Home hook already exists |
| batched OHLCV | `trending_stocks._batch_history` | reuse — do NOT add a second downloader |
| MFI (a DIFFERENT indicator) | `scanner_templates._mfi_series` | do not conflate; see the concept page |

**Nothing here needs a new data source.** CMF needs high/low/close/volume, which
the bhavcopy + `_batch_history` path already delivers.

## Build plan

**1 · `tools/money_flow.py` — the computation, no UI.**
`cmf(df, n=21)` per symbol, then `sector_cmf(...)` aggregating constituents.

> [!warning] The aggregation choice is the whole design, and the obvious one is wrong
> A **mean of constituent CMFs** treats a ₹200cr smallcap as equal to a ₹5trn
> index heavyweight, so the sector reading gets driven by its tail. The correct
> aggregation follows CMF's own construction — **sum the money-flow volume across
> the sector and divide by the sector's summed volume**:
>
> `sector_CMF = sum(MFV over all constituents, N) / sum(Volume over all constituents, N)`
>
> That is literally CMF applied to the sector as one synthetic instrument, keeps
> the [-1, +1] bound, and weights each name by the volume it actually traded —
> which is the honest definition of "where money went". Record the constituent
> count and the coverage fraction on every cell; a sector computed from 4 of 18
> names is not a sector reading and the card must be able to say so.

**2 · Four columns, and they are a LOOKBACK, not a history.**
`today / 1W / 2W / 1M` are each a 21-bar CMF ending at that date — so the columns
overlap heavily (21-bar windows 5 days apart share 16 bars). **They are not
independent observations**, and the Trend column must not be read as four
confirmations. State it on the card.

**3 · The Trend label.** Pre-register the rule before writing it, or it becomes a
vibe: *Accumulation* = CMF > 0 across all four columns; *Distribution* = < 0
across all four; *Increasing/Decreasing* = monotone across the four with a sign
change; otherwise flat. Simple, checkable, and no thresholds tuned to make the
current screenshot look good.

**4 · Rendering — a table here, and that is deliberate.**
[[analyses/Scanner-Overlap-Audit]]-era convention says Scanner Hub results stay as
CARDS. This is not scanner results: it is one metric across ~25 sectors and 4
dates, where the reader scans a column to find the outlier. That is the job cards
are worst at. `st.dataframe` with a red-white-green background gradient, clipped
at **±0.25** so ordinary readings use the whole scale instead of hugging white.

**5 · Home pipeline.** Reuse the existing `_action_card(..., "Sector Map", "sect")`
hook — a compact strip of positive-CMF sectors, click through to the full grid.
Home must stay cheap to open, so it renders from the SAME cached frame the page
computes and never triggers its own fetch (the pattern `_darvas_window(compact=True)`
already follows).

═══ BUILT — `tools/money_flow.py` + 18 tests, on Sector Map and Home ════════════

Live on NIFTY-500: **500/501 symbols with history, 20 sectors**, rendered as the
reference layout — sectors down the rows, `today / 1W / 2W / 1M` across, red-to-
green shading, Trend column. Verified in the running dashboard, not just in
isolation.

| sector | today | 1W | 2W | 1M | trend |
|---|---|---|---|---|---|
| Realty | +0.146 | −0.069 | +0.020 | +0.056 | — |
| Metals & Mining | +0.078 | +0.153 | +0.090 | −0.011 | — |
| Consumer Services | +0.070 | +0.037 | +0.085 | +0.046 | Accumulation |
| … | | | | | |
| Telecommunication | −0.002 | −0.127 | −0.061 | −0.243 | Distribution |
| Power | −0.200 | −0.290 | −0.203 | −0.194 | Distribution |

**The readings land inside ±0.25**, which is what `HEAT_CLIP` assumes — so the
colour scale uses its whole range instead of every cell hugging white. Had this
been scaled to CMF's theoretical ±1 bound the grid would have been unreadable.

**Aggregation went in as scoped, and a test proves the difference is real** rather
than asserting it in a comment: one heavyweight accumulating on 10m volume against
three smallcaps distributing on 1k each reads **+0.99 volume-weighted** and
**negative** as a mean of members. The naive average inverts the sector's reading.
`mode="mean_of_members"` is kept so the two can be compared, not hidden.

**One integration bug the live run caught that no unit test would have.**
`trending_stocks._batch_history` hands back yfinance's capitalised
`High/Low/Close/Volume`; the module and its tests used lowercase. It failed with a
`KeyError` 300 symbols into a download. Fixed with a case-insensitive `_col()`
rather than by making callers normalise — both conventions are legitimate here,
since the bhavcopy path is lowercase.

**Rendering is a TABLE, deliberately**, against the cards-not-tables convention
that governs Scanner Hub. That convention is about scanner RESULTS, where each hit
is an object with its own reasons. This is one metric across 20 sectors and 4
dates and the reader's job is to scan a column for the outlier — the job cards are
worst at.

**Three captions ship with the grid**, all verified present in the DOM: the
aggregation method and coverage, the overlapping-window warning, and the gap
caveat. `CAVEAT` lives in `money_flow.py` and is rendered from there, so the page
and the module cannot drift apart.

**Home mounting** is the positive-flow strip only, scan-on-click, reading from the
same cached frame — Home never fetches on load, the pattern `_darvas_window`
already follows. `_money_flow_window` is defined ONCE above both mount points;
the first wiring put the definition after Home's call and Streamlit raised
`NameError` on load, which the browser check caught.

**Ships as a VIEW, as scoped.** Not in `SCANNERS`, no entry/stop/target, never a
confluence vote, and a test asserts it stays unregistered. Nothing here has been
measured — if it is ever to become a signal, the pre-registered question above
(top-CMF sector vs the equal-weighted sector basket, sector-MATCHED baseline)
is what has to run first.

## What this must NOT become

**It ships as a VIEW, not a signal**, and the reason is on the record rather than
cautionary: B-19 measured most single-condition scanners negative after costs, and
this desk's volume tools (`volume_anomaly`) already ship as attention lists. So:
no `entry`/`stop`/`target`, **not** registered in `SCANNERS`, and never a
confluence vote. Highlighting positive-flow sectors on Home is a *reading order*,
not a buy list, and the card should say what the highlight means.

**If it is ever to become a signal**, the pre-registered question is
*"does buying the top-CMF sector index beat buying the equal-weighted sector
basket over 20d?"* — a **sector-matched** baseline, per the rule B-43r and B-44r
were written to enforce: filter the baseline with whatever you filter the signal.
An unmatched baseline would measure "sectors went up", not the flow signal.

## The honest caveat that belongs ON the page

CMF **ignores the previous close**, so gaps are invisible to it — a sector can gap
down, close sharply lower on heavy volume, and still print rising CMF because
closes sat above their bars' midpoints. Idiosyncratic gaps wash out in a sector
aggregate; an **index-level** gap (budget day, a global risk event) does not, and
CMF will misread that session for the whole board. Put it in the caption, not a
tooltip.

**Prior:** none recorded, because nothing is being claimed. This is a coverage
build — the desk has volume at PRICE (Volume Profile), volume SPIKES
(`volume_anomaly`), and no view of **where money is going by sector over time**.
That gap is real regardless of whether the metric predicts anything.

### ~~B-61~~ · OBV Divergence — chart overlay — **BUILT 2026-09-07**

Requested from [LuxAlgo's OBV-divergence page](https://www.luxalgo.com/library/concept/obv-divergence/).
`tools/obv_divergence.js` + 11 tests, wired into the chart beside RSI Divergence.

Their four-variant table is the one `rsi_divergence.js` has carried since
2026-06-22, so this is that concept pointed at a different series, not a new
claim:

| | regular (reversal) | hidden (continuation) |
|---|---|---|
| **Bullish** | price LL + OBV HL | price HL + OBV LL |
| **Bearish** | price HH + OBV LH | price LH + OBV HH |

**This module contains no divergence walk.** It computes OBV and hands it to
`RSIDIV.compute` through the injection point that module already exposes — the
same hook the dashboard uses to pass its own RSI in so the drawn line and the
measured values cannot drift. A second copy of the walk would be one rule
maintained twice, which is the shape of bug `test_renko_parity.py` exists to
catch elsewhere. Its output field is renamed `rsi` → `obv` on the way out, and a
test asserts that, so no downstream reader is told they are looking at an
oscillator they are not.

> [!warning] OBV is not RSI, and it changes the base rate
> RSI is bounded 0-100 and mean-reverting. **OBV is an unbounded running total,
> so it trends with the market.** In a sustained advance nearly every OBV swing
> low is a higher low, which makes "price LL + OBV HL" cheaper to satisfy than
> the RSI equivalent. **Expect MORE divergences here than the RSI pane gives on
> the same bars, and do not read the extra ones as extra evidence.** Live on
> RELIANCE.NS, 2,600 bars: 6 divergences.

**The artifact is MEASURED here, not just warned about.** LuxAlgo names the main
false-signal source precisely: OBV books a bar's ENTIRE volume by the sign of its
close-to-close change, so one enormous print — a news candle, an index rebalance,
a block deal — can bend the line into a divergence no genuine flow produced.
Their suggested audit is to inspect the bars by hand.

Every divergence instead carries **`volConcentration`**: the largest single bar's
share of total volume across the divergence's own window. Evenly spread over N
bars it reads 1/N; where one session carries half the volume it reads 0.5. The
chart marks those `!`. On RELIANCE the six read 0.12–0.14 — genuinely distributed
flow. `volume_anomaly` already attributes such spikes to a cause, so a flagged
divergence has somewhere to go next.

**A first-activation bug the browser caught and no unit test would have.**
Turning `obvdiv` on ADDS `obv` in the same pass, and the sub-pane is constructed
*after* the render call — so the first draw put the price half on the chart and
silently dropped the OBV half (measured: priceLines 6, obvLines 0 on pass one;
6 and 6 on pass two). Fixed with a one-shot retry. It uses **`setTimeout`, not
`requestAnimationFrame`** — rAF does not fire while a tab is hidden, so a chart
opened in a background tab would have stayed half-drawn until looked at. That
second point was itself caught by the verification pane being hidden.

**Ships as context, not a signal.** No entry/stop/target, not registered in
`SCANNERS`, never a confluence vote — LuxAlgo's own advice is to require price
confirmation (a reversal bar or a swing break) before acting, and this desk has
measured no forward edge for OBV divergence. It inherits `rsi_divergence.js`'s
coarser zigzag (2.0/1.5), the setting measured to stop divergence-between-two-
wiggles, so the two panes stay comparable.

**Owed before any OBV-divergence SIGNAL:** the same thing owed for PSAR — an
**overlap check against the RSI divergence pane**, not an edge test. Two
divergence detectors on one chart that fire on the same swings are one detector
with two colours.

### B-65r · The actual sentiment factor — PMax direction on NIFTY 1H — **PRE-REGISTERED 2026-09-10**

[[#B-65]] deliberately did not test this. It scored PMax on daily EQUITY bars and
said so before running, because `W_PMAX_1H` is a different claim: a direction
**state**, on **NIFTY**, at **1H**, worth **20 of the sentiment index's 100
points**. B-65's state arm came back *below* the market on the nearest daily
analogue, which is what makes this worth the trouble rather than a formality.

**THE CLAIM, stated as the code makes it.** `_pmax_direction_nifty_1h` returns
`factor = 1.0` when PMax direction is up and `0.0` when it is down, and that
factor is multiplied by 20 and added to the score. So the assertion is **not**
"up-state earns a positive return" — it is that **the two states are different**.
A factor that scores 20 for up and 0 for down claims to *discriminate*.

**PRIMARY is therefore a SPREAD, not an edge:**
`mean(fwd | dir=1) − mean(fwd | dir=−1)`. Testing up-vs-all instead would let a
factor that never discriminates pass on market drift alone, which is exactly the
confound B-65's state arm was written to expose.

**PRE-REGISTERED DESIGN — binding, written before `pmax_nifty_edge.py` exists.**

| | |
|---|---|
| series | `^NSEI` 1H, **730d — the yfinance ceiling**, 5,057 bars, 2023-10 → 2026-09 |
| indicator | `sentiment_index._pmax_direction_nifty_1h`'s own parameters (ATR 10, mult 3.0, MA 10), reusing the shipped port, not a copy |
| **PRIMARY** | **spread at 5 trading days ≈ 34 bars**, entry next bar's open |
| statistic | `mean(up) − mean(down)`, percent, **circular-rotation p** |
| PASS BAR | `spread > 0 AND p_rot < 0.05` |
| descriptive | the same spread at ~1 day (7 bars) and ~20 days (135 bars); up-vs-all and down-vs-all separately |

**POWER — declared in advance, because it is the whole problem here.** This is
**one series**, not a cross-section. 5,057 bars at a 34-bar horizon is roughly
**150 independent windows**, and the sign of the whole thing can turn on a
handful of 2024 swings. **A null in this arm does NOT retire the factor** — it
means the exact claim is *unvalidatable at the depth free data allows*, which is
a different and more honest statement.

**SECOND ARM — same question, real power, different timeframe.**
`^NSEI` **DAILY**, the longest history yfinance serves, same PMax parameters,
same spread statistic at a 20-day horizon. This is **not** the factor's claim —
the factor is 1H — and it cannot pass or fail `W_PMAX_1H` on its own. What it
CAN answer is the question standing behind it: **does PMax direction on this
index discriminate at all, over a sample long enough to contain more than one
regime?** If the daily arm is also flat, the 1H version is not likely to be
carrying something the daily one misses, and the factor's 20 points rest on
nothing anyone has shown. If the daily arm discriminates, the 1H null is a power
problem and the factor survives on inherited plausibility.

**REGIME CAVEAT, pre-registered.** The 1H window (2023-10 → 2026-09) is
substantially one bull regime. A direction factor is exactly the kind of thing
that looks fine in a trend and fails at the turn, so **a positive 1H result must
be read as "unfalsified in one regime", never as validation.** The daily arm
exists partly to escape this.

**PRIOR: genuinely uncertain, and this is the one place on this page where the
skeptical prior is NOT the automatic call.** [[#B-32]] measured that regime
carries real information — bullish signals lose significantly below the 200 SMA
(+0.22% RISK-ON vs **−1.78% RISK-OFF, p<0.005**) — so a trend-direction state on
the index *plausibly* discriminates even though every flip-as-entry test has
failed. B-65's daily-equity state arm points the other way. **These two pieces of
this desk's own evidence disagree, and that is why this is worth running.**

**CONSEQUENCE RULES, fixed in advance:**

- **Both arms discriminate** → the factor is supported; leave `W_PMAX_1H` alone
  and record it as measured.
- **Daily discriminates, 1H null** → power, not absence. Factor stays; the entry
  says so.
- **Neither discriminates** → **the 20 points are unsupported.** Even then
  **nothing is deleted on this result alone** — the same rule as B-59r and B-65 —
  but re-weighting the sentiment index becomes a live proposal with evidence
  behind it, and that proposal is its own entry, not this one.

### ~~B-65~~ · PMax has never been scored, and it carries a fifth of the sentiment index — **MEASURED 2026-09-10: FAIL. The flip is negative, and the STATE does not even capture the bull drift**

Falls out of [[#B-59r]]. PSAR and STAI have now both been measured on their
flips; **PMax never has**, and it is the one of the three with actual authority
in the desk:

- `W_PMAX_1H = 20` in `sentiment_index.py` — **a fifth of the sentiment score** —
  with its own Python port on NIFTY 1H.
- a named factor row in `market_verdict.py` (`pmax_nifty_1h`).
- a live trade-state panel in `dashboard_app.py` with stop and T1/T2/T3 derived
  from the band.

Three surfaces, zero measurements. That is the sharpest unmeasured claim left in
the trailing-stop family.

> [!warning] SCOPE — what this test does NOT settle, stated before it runs
> This scores **PMax flips and PMax state on DAILY EQUITY bars**, because that is
> what the cached universe holds and what makes the result comparable to B-43,
> B-59r and the rest. **The sentiment factor is a different claim**: a direction
> *state*, on **NIFTY**, at **1H**. A null here does NOT retire `W_PMAX_1H`, and
> saying it did would be exactly the over-reading this page keeps catching
> elsewhere. What a null here *would* do is remove the presumption that the
> factor is safe because "PMax works", and make the 1H index version its own
> owed measurement.

**PRE-REGISTERED DESIGN — binding, written before `pmax_edge.py` exists.**

  Same panel, harness, universe and baseline as [[#B-59r]] (460 names, ~3y daily,
  20d horizon, entry next open, unconditional baseline, costs cancel), so every
  number lands beside the twins rather than in its own frame.

| arm | definition | decides? |
|---|---|---|
| **PRIMARY · flip** | PMax up-flips, all of them | **yes** |
| **SECONDARY · state** | every bar where PMax `dir == 1` | no — see below |
| **CONTEXT · lonely flip** | PMax up-flips with NO PSAR up-flip within ±3 bars | no |
| **CONTEXT · joint flip** | PMax up-flips WITH a PSAR up-flip within ±3 bars | no |

- **PRIMARY** is the direct analogue of what B-59r scored for the twins, and the
  only arm that can conclude anything. **PASS BAR: `edge > 0 AND p_rot < 0.05`.**
- **SECONDARY (state)** is the nearest daily-equity analogue of the *sentiment
  factor's* actual claim — "is the trend up" rather than "did it just turn". It
  is **explicitly not decisive**, and the reason is a confound I will not be able
  to remove with this baseline: **in a window whose unconditional mean 20-day
  return is +1.76%, any up-trend filter will look good simply by sitting out the
  falls.** A positive state arm therefore measures "trend filter in a bull
  sample" and must be read that way. Recorded now so a positive number cannot be
  quietly promoted later.
- **The two CONTEXT arms exist because of B-59's oddest finding** — PMax and PSAR
  agree *below chance*. So: does a PMax flip that PSAR happens to confirm behave
  differently from one it does not? Pure description; no decision hangs on it.

  ABORT   any arm under **200** events is UNDERPOWERED and concludes nothing.

**PRIOR: skeptical on the flip, genuinely uncertain on the state.** The flip is
the fourth member of a family that has now measured −1.01% (Renko, B-43r),
−0.77% (PSAR-only) and −1.00% (STAI-only) — and PMax flips are *rarer and
slower*, which is the one structural reason it might not share their fate: it
does not re-enter after every wobble. The state arm is a different animal and
[[#B-32]] found regime *does* carry information (bullish signals lose
significantly below the 200 SMA), so a positive state reading would be
consistent with this desk's own evidence — and just as consistent with the
confound above.

═══ MEASURED — 2026-09-10, `tools/pmax_edge.py` ═════════════════════════════════

| arm | n | signal | baseline | edge | p_rot |
|---|---|---|---|---|---|
| **PRIMARY · flip** | 1,538 | +1.21% | +1.76% | **−0.55%** | 0.511 |
| **SECONDARY · state (dir=1)** | 129,761 | +1.57% | +1.76% | **−0.19%** | 0.857 |
| CONTEXT · lonely flip (no PSAR) | 1,264 | +1.11% | +1.76% | −0.65% | 0.444 |
| CONTEXT · joint flip (with PSAR) | 274 | +1.70% | +1.76% | −0.06% | 0.947 |

**VERDICT: FAIL on the pre-registered bar.** The flip is negative and
insignificant — a null, in the same direction as every other member of the
family.

**The state arm is the one that carries new information, and it is the opposite
of what the pre-registered confound warned about.** The warning was that *any*
up-trend filter would look good in a window whose unconditional mean 20-day
return is +1.76%, simply by sitting out the falls. **It did not look good. It
came in slightly BELOW the unconditional baseline** (+1.57% vs +1.76%, hit rate
51.9% vs 52.6%), across 129,761 bars — roughly 43% of the sample. Being "in a
PMax uptrend" was very slightly worse than being in the market at random, in a
bull window stacked in its favour. **The confound that should have inflated this
number did not save it, which makes the null harder rather than softer.**

**Four detectors, four negatives, one mechanism.**

| detector | selective-cell edge @20d | p |
|---|---|---|
| Renko flip, state-matched (B-43r) | **−1.01%** | 0.000 |
| STAI-only flip (B-59r) | **−1.00%** | 0.150 |
| PSAR-only flip (B-59r) | **−0.77%** | 0.053 |
| **PMax flip (B-65)** | **−0.55%** | 0.511 |

Four independently-implemented trailing-stop / brick detectors, none sharing
code, all landing between −0.55% and −1.01%. **PMax is the shallowest, which is
what the pre-registered prior said to expect** — it flips rarest and slowest, so
it re-enters after fewer wobbles, and B-43r's mechanism (an up-flip buys back in
only after price has given part of the run away) bites it least. **Only B-43r is
individually significant.** This is a convergence across four measurements, not
four proofs, and it should be cited that way.

**What this does and does not do to the sentiment factor.** As scoped before the
run: this is daily EQUITY bars, and `W_PMAX_1H` is a direction STATE on NIFTY at
1H. **This does not retire the factor.** What it removes is the presumption that
the factor is safe because PMax works — and the state arm makes that presumption
harder to hold, because the closest daily-equity analogue of exactly that claim
(*"is the trend up"*) returned **less than the market**. The 1H index version is
now its own owed measurement, and it is a live question rather than a formality:
**a fifth of the sentiment score currently rests on an indicator whose only
measurement is negative on its nearest testable analogue.**

**Nothing is removed on this result.** Same rule as B-59r: a null is not evidence
of harm, PMax's chart panel and factor stay where they are, and what changes is
what the desk is entitled to *assume*. That is the whole return on this
afternoon — four indicators that were all assumed to work are now four
indicators known not to have been shown to.

> [!note] The prediction that came true, and the one that did not
> **True:** PMax would be the shallowest negative of the family, because it flips
> rarest. Written before the run; −0.55% against the others' −0.77 to −1.01.
>
> **False:** the state arm would be flattered by the bull window. It was not.
> Writing the confound down in advance is what makes that readable — had it come
> back at +1.5% the entry would have had to discount it, and because it came back
> NEGATIVE the same note now works in the opposite direction, as evidence.
> **A pre-registered caveat is worth as much when it fails to apply as when it
> applies.**

### ~~B-59r~~ · PSAR vs STAI — which of the two agreeing detectors carries the information? — **MEASURED 2026-09-10: NEITHER. Both twins NEGATIVE on their unique cells, agreement ≈ market**

Falls directly out of [[#B-59]]'s chance-corrected run. The desk now knows that
**PSAR and STAI describe the same reversals** (+34.2 lift over rotation at ±3)
and that **PSAR and PMax do not** (−12.4, below chance). So the trailing-stop
role is not held by three detectors — it is held by **PMax, plus one detector
implemented twice**. This entry asks which of the twins to keep, and it is the
only version of that question that can be answered with evidence rather than
taste.

**It is also the first time any of PSAR / STAI / PMax will have been scored on
this desk at all.** Agreement was measured; accuracy never was.

**PRE-REGISTERED DESIGN — binding, written before `psar_stai_edge.py` exists.**

  EVENTS   long side only (up-flips), so the question stays single. Three
           mutually exclusive arms, each an event vector over the same bars:

  | arm | definition |
  |---|---|
  | **AGREE** | a PSAR up-flip with an STAI up-flip within ±3 bars |
  | **PSAR-ONLY** | a PSAR up-flip with NO STAI up-flip within ±3 bars |
  | **STAI-ONLY** | an STAI up-flip with NO PSAR up-flip within ±3 bars |

  ±3 is not re-chosen here — it is B-59's middle rung, fixed before these
  numbers were seen.

  CAUSALITY  an AGREE event is dated at **`max(psar_bar, stai_bar)`** — the bar
             on which both are known. Dating it at the earlier one would trade
             on a confirmation that had not arrived. Entry is the NEXT OPEN.
  BASELINE   every bar in the same names (unconditional), the same construction
             as B-43 and B-58's CONTRAST arm, so the three arms are comparable
             to each other AND to this desk's existing null.
  HORIZON    20 trading days.
  STATISTIC  mean(arm) − mean(baseline), percent. **Circular rotation p.**
  COSTS      none: every arm is differenced against the same baseline held the
             same 20 days, so the ~29bps model cancels.

**THE DECISION RULE, fixed in advance — this is a SELECTION, not a pass/fail.**

| outcome | reading |
|---|---|
| PSAR-ONLY significant, STAI-ONLY not | PSAR sees something STAI misses → keeping PSAR is justified |
| STAI-ONLY significant, PSAR-ONLY not | the reverse → PSAR adds nothing and stays an overlay for good |
| **both null** | **neither twin's unique cells carry measurable information.** The trim cannot be decided on edge, and falls back to cost: **keep STAI**, which is already wired, and PSAR stays a drawn overlay. **No indicator is deleted on a null** — a null is not evidence of harm |
| both positive | the disagreement is noise in both directions and the AGREE arm is the interesting one |

  AGREE is **context, never decisive**: if it beats both singles, that is a
  confluence finding for a later entry, not a reason to keep or drop either.

  ABORT   any arm under **200** events is reported UNDERPOWERED for that arm and
          cannot support a conclusion about it.

**PRIOR: skeptical, and specifically so.** B-19 measured 0/41 scanners stable
across horizons with most negative after costs, and a trailing-stop up-flip is a
trend-following entry *after* a move — the same shape as the Renko flip, which
B-43 measured at a clean null and B-43r at **−1.01%** once state-matched. The
honest expectation is **both twins null**, landing on row 3: keep STAI, PSAR
stays an overlay, and the desk stops asking.

**What this deliberately does NOT do:** it does not re-open PMax. B-59 settled
that PMax is not interchangeable with either twin, and nothing here bears on it.

═══ MEASURED — 2026-09-10, `tools/psar_stai_edge.py` ════════════════════════════

460 names, ~3 years of daily bars, 20d horizon, entry next open, unconditional
baseline, no costs (they cancel).

| arm | n | signal | baseline | edge | p_rot |
|---|---|---|---|---|---|
| **AGREE** both flip up within ±3 | 4,068 | +1.92% | +1.76% | **+0.16%** | 0.820 |
| **PSAR-ONLY** no STAI flip near it | 8,576 | +0.99% | +1.76% | **−0.77%** | 0.053 |
| **STAI-ONLY** no PSAR flip near it | 1,909 | +0.77% | +1.76% | **−1.00%** | 0.150 |

**VERDICT: BOTH NULL — the pre-registered third row, with its consequence already
named. The trim cannot be decided on edge, so it falls back to cost: KEEP STAI
(already wired), PSAR stays a drawn overlay, and NOTHING IS DELETED.** A null is
not evidence of harm, and neither twin has been shown to mislead anyone.

**But the shape of the null is more interesting than the null.** All three arms
tell one coherent story, and it is not "these indicators do nothing":

- **Where the twins AGREE, the flip is worth the market** — +0.16% against a
  +1.76% baseline, p=0.820. Agreement buys you the index, no more.
- **Where they DISAGREE, both sides lose** — −0.77% and −1.00%. A trailing-stop
  up-flip that its twin does not confirm is a **worse-than-market entry**, in
  both directions, and it is the disagreement cells that make up the bulk of the
  events (10,485 of 14,553).

**That number should look familiar: B-43r measured the bare Renko flip at
−1.01%.** Three independently-implemented flip detectors — Renko bricks, PSAR
dots, STAI's adaptive trail — now land within a quarter-point of each other on
their selective cells, and B-43r's mechanism explains all three: **an up-flip
re-enters only after price has already given back part of a run**, so it
systematically buys the worse half of the distribution. Neither p here clears
0.05 (0.053 and 0.150), so this is **a convergence worth noting, not a proven
result** — but it is the fourth measurement pointing the same way, and the desk
should stop expecting a flip detector to be an entry.

**Consequences, all of them "keep what exists":**

- **PSAR**: drawn overlay, permanently. B-46's exclusion is now supported by a
  measurement rather than an argument — and by a stronger one than B-46 made,
  since the objection was redundancy and the finding is that its unique cells are
  *negative*.
- **STAI**: unchanged, and note that this is the **first time it has ever been
  scored on this desk**. Its unique flips are the worst arm of the three. It
  stays because it is wired and harmless, not because it was vindicated.
- **PMax**: untouched by this test, as pre-registered. It remains **the only one
  of the three that has never been scored at all** — and it carries a fifth of
  the sentiment index. That is now the sharpest unmeasured claim in the
  trailing-stop family, and it deserves its own entry.
- **AGREE as a confluence idea**: dead on arrival. +0.16%, p=0.820 — two
  detectors agreeing does not beat one, which is the same answer B-25 got for
  confluence generally.

> [!warning] Agreement was measured first, and it was the cheap half
> B-59 established that PSAR and STAI say the same thing. B-59r establishes that
> **what they say is not worth acting on**. The order mattered — counting first
> cost an afternoon and told us which pair was even worth scoring — but it would
> have been easy to stop at B-59 and conclude "PSAR is redundant, STAI is fine".
> **Redundancy said nothing about whether the surviving twin was any good.**

### ~~B-59~~ · Parabolic SAR — chart overlay — **BUILT 2026-09-07 · OVERLAP CHECKED 2026-09-10**

═══ OVERLAP CHECK — 2026-09-10, `tools/psar_overlap.js` ═════════════════════════

**The check the overlay owed before any PSAR signal, and it is not an edge test.**
460 names, 322,608 daily bars, the same cached universe as B-43/B-57/B-58.

| | PSAR | PMax | STAI |
|---|---|---|---|
| flips | **28,582** | 3,396 | 13,050 |

**PSAR fires 8.4× as often as PMax and 2.2× as often as STAI.** That ratio is the
finding; everything below is a consequence of it.

| tol | covered by PMax | by STAI | by EITHER | **PSAR-unique** |
|---|---|---|---|---|
| ±0 | 0.3% | 11.9% | 12.2% | 87.8% |
| ±1 | 0.9% | 20.6% | 21.3% | 78.7% |
| ±2 | 1.5% | 25.8% | 26.9% | 73.1% |
| **±3** | **2.1%** | **29.7%** | **31.1%** | **68.9%** |
| ±5 | 3.7% | 35.4% | 37.4% | 62.6% |
| ±10 | 9.2% | 46.0% | 49.3% | 50.7% |

**The mirror table is the honest read, and it says the opposite of the primary
one.** How much of the others does PSAR cover?

| tol | PMax covered by PSAR | STAI covered by PSAR |
|---|---|---|
| ±3 | 17.9% | **64.7%** |
| ±10 | 69.6% | **92.0%** |

**Answer: PSAR is a SUPERSET at a faster cadence — not a duplicate, and not a new
detector.** It sees nearly everything STAI sees (92% at ±10) and most of what
PMax sees (70%), then keeps flipping. The 68.9% "unique" share is largely
**arithmetic**: there are only 3,396 PMax flips in existence, so they cannot
cover 28,582 PSAR flips at any tolerance. Reporting that number without the
cadence beside it would have flattered PSAR into looking like new information.

**What this does to B-46, stated precisely.** B-46's objection was
*zero-unique-cells* — a detector that fires only where others already fire. **That
objection does not survive: the cells are not zero, they are the majority.** But
the objection that replaces it is no weaker, and it is more specific: *PSAR's
entire content is its extra flips.* So the question is no longer "does it
duplicate" but "**are the 19,690 uncovered flips signal or noise**", and that is
answerable only by scoring the UNIQUE cells against the COVERED ones — on the
standing prior that a detector firing 8× as often is mostly firing on chop.
**Uniqueness is not edge**; [[analyses/Scanner-Overlap-Audit]] says so, and this
run does not change it.

**Status unchanged by design.** PSAR stays a drawn overlay: no scanner, no
registry entry, no confluence vote. The gate this check existed to open —
*"if its flips are a subset there is nothing left to measure"* — **did not close
the question**, so the edge test is now genuinely owed rather than moot. It is a
new item, not this one; see the ranking.

> [!note] Two method points worth keeping
> **Exact-bar matching would have proved nothing.** Three trailing stops with
> different smoothing do not turn on the same bar even when describing the same
> reversal, so ±0 reports 87.8% "unique" for what is obviously overlapping
> behaviour. The tolerance is swept (0/1/2/3/5/10) rather than chosen, because
> the honest answer to "is this redundant" is a **shape, not a number**.
>
> **`pmaxSeries` and `atrSeries` are LIFTED from `chart_dashboard.html` at
> runtime, not copied.** They live inline in the HTML; a copy would drift the
> moment the chart changed and this file would go on reporting an overlap against
> an indicator nobody runs — the same failure the `columns.py` registry (B-63a)
> was built to end. The lift is brace-matched and **throws loudly** if the
> function is renamed.

═══ CHANCE BASELINE — added 2026-09-10, and it INVERTS half the reading ═════════

**Asked directly: can we sunset PMax in favour of PSAR? No — and the corrected
numbers say it more strongly than the raw ones did.**

The first pass reported raw coverage, which is close to meaningless on its own.
PSAR alternates every ~11 bars, so a **same-direction** PSAR flip comes round
about every 22; a ±10 window is 21 bars wide and will catch one most of the time
**whether or not the two indicators are describing the same reversal**. The
tolerance sweep was partly showing the shape of a base rate. Fixed with the null
this desk uses everywhere else (B-43r/B-57/B-58): **circular rotation** of the
comparator's flips — same count, same direction mix, same spacing, alignment
destroyed. Coverage above that is agreement; coverage at it is arithmetic.

**PSAR flips covered (observed / chance / lift):**

| tol | by PMax | by STAI | by EITHER |
|---|---|---|---|
| ±0 | 0.3 / 0.5 / **−0.2** | 11.9 / 2.0 / **+9.9** | 12.2 / 2.5 / +9.7 |
| ±3 | 2.1 / 3.7 / **−1.6** | 29.7 / 14.1 / **+15.6** | 31.1 / 17.1 / +14.0 |
| ±10 | 9.2 / 11.0 / **−1.8** | 46.0 / 40.4 / **+5.6** | 49.3 / 44.9 / +4.4 |

**The mirror — the direction a sunset argument actually needs:**

| tol | PMax covered by PSAR | STAI covered by PSAR |
|---|---|---|
| ±3 | 17.9 / 30.3 / **−12.4** | 64.7 / 30.5 / **+34.2** |
| ±10 | 69.6 / 78.1 / **−8.5** | 92.0 / 78.7 / **+13.3** |

**Two findings, and the second was invisible before the baseline.**

**1. PSAR and STAI describe the same reversals.** +34.2 lift at ±3 in the mirror,
+15.6 in the primary. This is real, large agreement — not a base-rate artifact.

**2. PSAR and PMax agree LESS than chance — at every tolerance, in both
directions.** Not "independent": **systematically avoiding each other**. The
earlier reading of the raw ±10 mirror number (69.6% covered) as evidence that
*"PSAR nearly contains PMax"* was **wrong** — chance alone is 78.1% there, so the
observed figure is 8.5 points *below* what rotation produces. A plausible
mechanism is that PMax only flips once a trend has genuinely turned, by which
point PSAR has flipped already — **that is unmeasured and is not being claimed.**

**What follows for the sunset question:**

- **Retiring PMax in favour of PSAR is the worst available swap of the three.**
  They are the least-alike pair on this desk's own null. Whatever PMax
  contributes, PSAR is demonstrably not a substitute for it.
- **PMax is also not just a chart overlay.** It carries `W_PMAX_1H = 20` in
  `sentiment_index.py` — **a fifth of the sentiment score** — with its own Python
  port on NIFTY 1H, a named factor row in `market_verdict.py`, and a live
  trade-state panel with stop and T1/T2/T3 in `dashboard_app.py`. PSAR has none
  of that. A sunset is a rewiring, not a deletion.
- **The redundancy that DOES exist is PSAR↔STAI**, and it is the pair to look at
  if the desk wants one fewer trailing-stop indicator. **That choice is an EDGE
  question, not a counting one** — and neither has ever been measured here.
- **B-46 stands, on better grounds than it was argued.** PSAR would be a third
  detector in an occupied role, and it duplicates **STAI specifically**. Overlay,
  as shipped.

> [!warning] Agreement is not accuracy
> Nothing in this file scores a forward return, and **none of PSAR, PMax or STAI
> has ever been measured on this desk**. Two indicators can agree perfectly and
> both be worthless. Everything above is about whether they say the same thing,
> never about whether what they say is right. They live inline in the HTML; a copy would drift the
> moment the chart changed and this file would go on reporting an overlap against
> an indicator nobody runs — the same failure the `columns.py` registry (B-63a)
> was built to end. The lift is brace-matched and **throws loudly** if the
> function is renamed.

Absent. `grep -ri "parabolic\|psar" tools/` returns nothing but a false positive:
`evwma_vwap_macd_backtest.py`'s `sar` key is **stop-and-reverse equity**, not
Wilder's indicator. Not in `INDICATOR_DEFS` (36 entries), so it cannot be put on
a chart. Asked for from a "How To Use PSAR Indicator" chart.

> [!warning] There is already a decision on record against this, and it is narrower than it looks
> B-46 says **"Parabolic SAR is explicitly NOT bundled — `pmax` and `stai`
> already occupy the trailing-stop-flip role, and adding a third would risk
> another zero-unique entry of the kind [[analyses/Scanner-Overlap-Audit]] just
> trimmed."** [[analyses/Indicator-Coverage-Gap]] repeats it.
>
> That objection is about a **scanner**, not an **overlay**. A zero-unique entry
> is a registry problem: a scanner that fires where others already fire adds
> decisions without adding information. A chart overlay makes no claim and votes
> in nothing — and B-46's own resolution for Ichimoku was *"ship the overlay
> first; any BUY/SELL reading is a separate, measured question."* The same split
> applies here, so **this entry is the overlay only** and the objection stands
> unchanged against a PSAR scanner.

**Build.** `tools/psar.js` as a pure computation library (no DOM), matching
`renko.js` / `fibonacci.js` / `supertrend_ai.js`; render in
`chart_dashboard.html`; one `INDICATOR_DEFS` row in `Trend & Bands` beside
`pmax` and `stai`, where a reader comparing the three trailing-stop tools will
look for it.

Wilder's rule, stated so the parameters are not quietly invented: AF starts at
**0.02**, steps **0.02** on each new extreme, caps at **0.20**;
`SAR(next) = SAR + AF × (EP − SAR)`; on a flip, SAR seats at the prior EP and AF
resets. The two clamps that everyone omits and then wonders why their dots look
wrong: SAR may not penetrate **either of the last two bars'** range on the side
it is trailing.

**Causality.** The dot for bar *i* is computed from bars ≤ *i−1* and is therefore
known at *i*'s open. That makes it honest to plot and honest to backtest later —
unlike a naive implementation that seats today's dot from today's extreme, which
repaints and would flatter any measurement built on it.

**No backtest owed for the overlay** — exposing a series makes no edge claim, the
same footing B-45 puts Keltner/PMax/Renko wiring on. What IS owed, before any
PSAR *signal* ships: a pre-registered test AND an overlap check against `pmax`
and `stai`, because B-46's objection is precisely that the flip may carry zero
unique cells. **The right first measurement is the overlap, not the edge** — if
its flips are a subset of PMax's, there is nothing to measure afterwards.

═══ BUILT — `tools/psar.js` + 11 tests, wired into the chart ════════════════════

Overlay only, exactly as scoped. `psar.js` is pure computation (no DOM, no
charting-library dependency) beside `renko.js` / `supertrend_ai.js` /
`fibonacci.js`; one `INDICATOR_DEFS` row in **Trend & Bands** next to `pmax` and
`stai`, where a reader comparing the three trailing-stop tools will look for it.

**Verified on real bars through the chart**, not just in isolation: RELIANCE.NS,
2,600 bars → 1,368 long dots + 1,230 short dots = 2,598 (the two-bar seed
accounts for the rest). Green below price in up-trends, red above in down-trends,
switching sides at each reversal. No console errors, all module fetches 200.

**Drawn as DOTS, not a line.** Consecutive SAR values sit on opposite sides of
price across a reversal, so joining them would stroke a line straight through the
candles that no part of the indicator asserts. lightweight-charts has no points
series, so it is a line with `lineVisible:false` and point markers — added as a
shared `addDots()` helper beside `addLine()`.

**No flip markers, deliberately.** `pmax` and `stai` already draw BUY/SELL arrows
on the same pane; a third set would read as three independent confirmations of
one idea when they are three renderings of the same trailing-stop concept. That
is B-46's objection expressed in pixels rather than in the registry.

**Causality is the part that was worth writing carefully, and it has a test.**
`path[i]` uses bar i-1's SAR/EP/AF and the ranges of bars i-1 and i-2 — nothing
from bar i — so the dot is known at bar i's OPEN. `test_the_dot_for_a_bar_does_not_use_that_bar`
mutates one bar's high and low by ±30% and asserts that bar's own dot does not
move. A naive implementation seats today's dot from today's extreme: it looks
almost identical on screen and it repaints, so any later measurement inherits a
peek at the bar it is meant to be trading. Invisible to the eye, trivial to
reintroduce, which is exactly what the test is for.

Wilder's two-bar clamp is also asserted directly (SAR may not penetrate either of
the last two bars' range on the side it trails), along with the AF schedule:
0.02 seed, 0.02 step, 0.20 cap, reset on flip. `flips` carry their bar index and
are fillable at the next open, the same treatment `renko.js` gives brick flips —
so if the overlap check ever licenses a signal, the harness can score it without
this module changing.

> [!note] The running chart server must be restarted to pick this up
> `chart_server.py` serves each module from an explicit route, and Flask is
> started without the reloader. A server already running when this shipped
> returns **404 for `/psar.js`** until restarted — observed on the live instance
> during verification. `sw.js`'s precache list carries `/psar.js` too, and code is
> already fetched network-first there (see the PWA cache postmortem), so no
> service-worker flush is needed beyond the restart.

**Still owed before any PSAR SIGNAL:** the overlap check against `pmax` and
`stai`, NOT an edge test. B-46's objection is that the flip may carry zero unique
cells; if its flips are a subset of PMax's there is nothing left to measure.

**Note on the source chart.** The image's second panel pairs PSAR with a
trendline and labels a "Take profit level" at a PSAR flip. That is the
trailing-stop use, which is the one use the desk's own [[analyses/Indicator-Coverage-Gap]]
grants it — B-41p is the relevant prior here, and it found that on the Liquidity
Sweep signal **removing the stop entirely** turned −0.059R into +0.504R. A
trailing stop is not free, and PSAR is a fairly tight one. Ship the picture; do
not assume the exit rule.

### B-58 · Quasimodo (QM) geometry — **MEASURED 2026-09-10: INCONCLUSIVE — UNDERPOWERED (53 events against a pre-registered floor of 200)**

From a "4 Setups for BUY Entry, based on QM patterns (CHOCH)" chart the owner
brought in. A coverage audit of that image against the repo found most of its
parts already present, one part measured NEGATIVE under another name, one part
measured POSITIVE under another name, and exactly one genuine gap. This entry
scopes the gap.

**What the audit found — the reason this is narrow rather than a four-scanner build.**

| element in the image | repo | |
|---|---|---|
| CHOCH / BOS | `detect_bos_choch` (B-42) | covered |
| Key level | `detect_order_blocks`, structural support | covered |
| fib entry grid | `fibonacci.js` | covered |
| 88.6% entry / 113% stop | **added 2026-09-07**, drawn but not wired into `buildPlan` | covered |
| OB confluence (setup 3) | `detect_order_blocks` | covered |
| stop hunt (setup 4) | `detect_liquidity_sweep` | covered |
| "HTF LQ" | liquidity pools are SINGLE-timeframe | **gap, deferred** |
| QM geometry itself | nothing | **gap, this entry** |

> [!warning] Setups 1–3 are a family this desk has already measured at no edge
> `scan_ict_setup` chains CHOCH-with-displacement → OTE 61.8–79% fib → FVG
> confluence → stop below zone → target at the next pool. That IS the image's
> setups 2 and 3, and B-19 measured it at **−0.36% @20d / −1.24% @60d, NO EDGE
> [UNSTABLE]** on 158 signals. `Order Block Retest` reads **−0.47% / −0.70%** on
> 2,341, and `Pullback Entry` **−0.43% / −1.12%** on 6,485. Three independent
> implementations of "retrace into a level after a structure break", ~9,000
> signals, all negative. **Rebuilding setups 1–3 as new scanners would re-derive
> that**, which is why this entry does not propose them.
>
> The exception points the other way and is the interesting part: the stop-hunt
> mechanic, which is the image's setup 4, is `Liquidity Sweep` — B-41m measured
> **+0.51% @20d (p=0.005), +0.91% @60d (p=0.002)** net of ~29bps, walk-forward,
> the desk's best result. The picture's own author marks setup 4 as the best R/R
> quadrant, and it is the only quadrant this desk has independently measured an
> edge in. That agreement is worth more than the taxonomy around it.

**So the only thing worth building is the QM GEOMETRY**, because it is a
genuinely different selection rule from "CHOCH then retrace" — the rule the
nulls above all share. A Quasimodo requires a specific left-shoulder / head /
right-shoulder arrangement, and the CHOCH must break the *left shoulder's* low.
Nothing in the registry tests that shape.

**Definition to build against (BUY-side QM), pinned so it cannot drift.**

> [!warning] CORRECTED 2026-09-07, before the build
> The first version of this entry described the sequence with `LS` as a swing
> HIGH and the head above it. **That is the SELL-side pattern**, written under a
> heading that said bullish, and the distinguishing condition given (`RL < LL`)
> was wrong for a second reason as well — see below. Pinning a definition is only
> worth doing if the definition is right, so it is corrected here rather than
> quietly fixed in code.

Over the swing sequence from `detect_structure_chain` — the same source
`detect_liquidity_pools` uses, so QM, the pools and the BOS/CHOCH engine can
never disagree about where a swing is. Chronological, kinds alternating:

1. `LS` left shoulder — a swing **LOW**
2. `LH` — the swing **HIGH** after it
3. `HEAD` — a swing **LOW below `LS`**. The liquidity grab: it takes out the
   resting sell-side stops under the left shoulder.
4. `RH` — a swing **HIGH above `LH`**. **This is the CHOCH** — the post-head
   rally breaks the pre-head high, which is the change of character.
5. `RS` right shoulder — a swing **LOW above `HEAD`**

Entry zone is the **`LS` level**, retested from above — the left shoulder's low
becomes the support the fib rungs land on. Invalidation is below `HEAD`.

**What actually separates this from an inverse head-and-shoulders**, corrected:
it is NOT the head being below the shoulders — an inverse H&S has that by
definition, so the original entry's claim was empty. The two real differences are
**(a) the CHOCH condition `RH > LH`**, and **(b) where the entry sits**: QM buys
the retest of the LEFT SHOULDER, while an inverse H&S buys the neckline break.
A detector that drops `RH > LH` fires on both shapes and measures neither, which
is what the pre-registered control below is for.

**Build shape (mirrors `detect_bos_choch` so the two are comparable):**
`detect_quasimodo(df, pivot_len=5, lookback=120, tol_pct=2.0)` returning the five
pivots, the entry zone (`LS` ± `tol_pct`), the invalidation (`HEAD`), and
`bars_ago`. A scanner wraps it. **Registered as a SCREEN on first ship** —
`PIPELINE_EXCLUDED`, no entry/stop/target — until it has its own pre-registered
measurement, exactly as B-57's Shallow Flip did.

═══ BUILD — 2026-09-07, `detect_quasimodo` + 17 tests ═══════════════════════════

Detector only. No scanner registered yet, no forward returns scored, and the
pre-registration below is still what has to run before anything ships.

**Two corrections the build forced, both from running it rather than reading it.**

**1. The right shoulder had to become OPTIONAL.** A swing pivot needs `pivot_len`
bars on each side to confirm, and the right shoulder IS the retracement into the
entry zone — so requiring a confirmed `RS` made the pattern visible only *after*
price had been in the zone and left it. A detector that can only see the setup
once it is untradeable is a chart annotator, not a screen. The pattern therefore
completes at the **CHOCH** (`LS, LH, HEAD, RH`); `rs` is reported when a
confirmed low exists and is `None` otherwise, and whether price is in the zone
*right now* is a separate live field.

**2. The four pivots must be CONSECUTIVE, which is what makes it a shape at all.**
First version searched the four positions independently across the 120-bar
window. Measured on 460 liquid NSE names it reported a pattern on **73%** of
them — that is not a pattern, it is "this stock has had a pullback and a rally".
Adding minimum sizes for the grab and the CHOCH only moved it to **67%**, because
the search simply selected a different, deeper quadruple. Requiring the pivots to
be **adjacent in the zigzag** — which is how the pattern is drawn — took it to
**44%**.

| version | names reporting a pattern |
|---|---|
| independent search | 73% |
| + minimum grab / CHOCH size | 67% |
| **+ consecutive pivots** | **44%** |

**Presence is not the screen; presence AND location is.** Of 460 names, **202**
carry a QM somewhere in the window and only **14 (3%)** have price inside the
entry zone with the head unbroken. That 3% is the number a Hub card would show.
Median grab 2.7%, median CHOCH break +6.5%, median 35 bars since the CHOCH — so
a freshness bound belongs in the wrapping scanner, not in the detector, which
reports `bars_ago` and lets the caller decide.

**The minimum grab and CHOCH sizes are not invented.** Both floor at **0.75%**,
which is `detect_liquidity_pools`'s existing equal-level tolerance: that function
already treats levels within 0.75% as EQUAL — a liquidity *pool* rather than a
break. A "grab" shallower than the desk's own definition of equal is not a grab,
and a "break" that small is not a break. Reusing the constant keeps one
definition of when two levels are the same price.

**Structural honesty, same as B-57's Shallow Flip.** No `entry` / `stop` /
`target` / `score` keys — a test asserts their absence — so the detector cannot
be mistaken for a plan before its measurement exists.

**Pre-registration sketch, to be completed BEFORE the first scoring run.**
Primary: QM completions vs a **state-matched** baseline — bars in the same names
that are also retesting a prior swing high from above without the QM sequence.
Matching on the retest state is the whole point: unmatched, this would measure
"buying support", which the three nulls above already measured. Horizon 20d,
entry next open, rotation p, pass bar `edge > 0 AND p_rot < 0.05`. Control: the
same geometry with the CHOCH condition `RH > LH` RELAXED — if the relaxed
version scores the same, the change of character is decorative and the detector
is an inverse-H&S finder wearing a different name.

**Prior recorded in advance:** skeptical. The family this belongs to is 0-for-3
on this desk at ~9,000 signals. What buys it a test at all is that the `RL < LL`
condition makes it a strict subset of that family selected on the one mechanic
(`Liquidity Sweep`) that DID measure positive — so the honest hypothesis is not
"QM works" but "QM is a liquidity sweep with extra steps, and the sweep is
already the better-tested way to express it." The control is designed to catch
exactly that.

═══ PRE-REGISTRATION — COMPLETED 2026-09-10, BEFORE THE SCORER EXISTED ══════════

The sketch above is now binding, with three things it left open filled in and
**one thing in it corrected**. Written and committed before
`tools/quasimodo_study.py`, on the B-57 rule: the design changes first, in
public, or not at all.

> [!warning] CORRECTION to the sketch's baseline — it named the wrong side
> The sketch says the baseline is *"bars in the same names that are also
> retesting a prior swing **high** from above"*. That is incoherent: a retest of
> a swing high **from above** is a support test of a broken resistance, and the
> QM entry is not there. **QM buys the retest of the LEFT SHOULDER, which is a
> swing LOW** (`entry_zone = LS ± tol_pct`, `invalidation = HEAD`). The baseline
> is therefore *a confirmed swing **LOW**, retested from above, still unbroken* —
> the plainest possible statement of "buying support". This is the second
> high/low slip in this entry (the first put `LS` on the wrong side of the
> pattern), and both were found by reading rather than by running, which is the
> argument for pinning definitions in prose before scoring them.

**EVENT — the zone entry, not the CHOCH.** The pattern *completes* at the CHOCH
(`RH`), but nothing is tradeable there: the entry is the retest of `LS` that
follows. So the scored event is the **first bar after the CHOCH is knowable on
which the close falls inside `LS ± 2%` with the head unbroken**. This is the
detector's own `in_zone` field, and it is the 3%-of-names number a Hub card would
show — the 44% presence number is not a signal and is not scored.

**CAUSALITY.** A swing pivot at bar *j* is only knowable at *j + pivot_len*
(`detect_structure_chain` appends it exactly there). The event bar must therefore
satisfy `t > rh.bar + pivot_len`, and entry is the **next open** after *t*. No
arm may use a pivot before its confirmation bar.

**ARMS.**

| arm | signal | baseline | decides? |
|---|---|---|---|
| **PRIMARY** | QM zone entries | every bar in the same names that is a **support retest**: close within ±2% of a confirmed, unbroken swing low, approached from above | **yes** |
| **CONTROL · relax the CHOCH** | the same walk with `RH > LH` dropped (`min_choch_pct = −∞`) | same | no |
| **CONTRAST** | QM zone entries | every bar (no state filter) | no |
| **HARNESS** | all support retests | every bar | no |

- **PRIMARY** is the only arm that can pass anything. Horizon **20 trading days**,
  entry next open, statistic `mean(signal) − mean(baseline)` in percent,
  **circular-rotation p** (Welch is invalid — overlapping windows,
  cross-sectionally correlated), **PASS BAR: `edge > 0 AND p_rot < 0.05`.**
- **CONTROL** is the sketch's control, made operational. If dropping `RH > LH`
  leaves the edge materially unchanged, the change of character is decorative and
  `detect_quasimodo` is an inverse-H&S finder wearing a different name.
- **CONTRAST** is the size of the illusion — what a careless version of this test
  would have published by baselining against all bars.
- **HARNESS** exists because of what B-57 learned when CONTROL2 misbehaved: point
  the machinery at a settled number before believing it on a new one. "Buy a
  support retest" is the family measured at **−0.36% / −0.47% / −0.43% @20d**
  across ~9,000 signals, so this arm should read **flat-to-negative**. A strongly
  positive HARNESS means the panel is wrong and **no other number in the run may
  be reported**.

**ABORT.** Fewer than **200** primary events ⇒ **INCONCLUSIVE — UNDERPOWERED**,
explicitly not a null. (The detector's own cardinality run makes this a live
risk: 14 of 460 names were in-zone on a single day.)

**COSTS.** None applied, and that is not an oversight — signal and baseline are
the same instrument held the same 20 days, so the ~29bps Indian delivery model
cancels in the difference. An absolute return from this study would need it; the
edge does not.

**EQUIVALENCE, not a second implementation.** The study needs an event *history*,
and `detect_quasimodo` returns only the newest pattern. The historical walk is
therefore reimplemented over the same `detect_structure_chain` swings — which is
exactly how definitions drift, so the study **asserts that its last-pattern
output matches `detect_quasimodo`'s on the full frame, per symbol**, and reports
the agreement count. A mismatch aborts the run rather than being reported.

> [!warning] AMENDMENT 2026-09-10, after the first run ABORTED — the baseline as
> written could not contain the signal
> The design says the baseline is a *"confirmed, **still-unbroken** swing low,
> approached from above"*. The scorer asserts that the QM events are a subset of
> that state before scoring anything, and the assertion **failed**.
>
> It failed for a reason that is the pattern itself: **a Quasimodo's left shoulder
> is a low that HAS been broken — the head is the break.** The grab takes out the
> stops under `LS`, and the entry is the retest of that level *after* price
> reclaimed it. So "still-unbroken" excludes, by construction, every bar the
> signal fires on. I wrote a baseline that the signal can never belong to, which
> would have measured QM entries against a state they are disjoint from and called
> the difference an edge.
>
> **Amended:** the state drops the permanence of the break — *close within ±2% of
> a confirmed prior swing low, approached from above (close at or above the
> level)*. A level that broke and was reclaimed is still the level being retested.
> Nothing else changes: same event, same horizon, same statistic, same bar.
>
> **This amendment cannot buy power and does not touch the signal.** It changes
> only which bars the baseline is drawn from; the event count is identical before
> and after. Recorded here rather than fixed quietly because a baseline change
> after seeing a run is exactly the move that needs a paper trail.
>
> **It also sharpens what the test is asking.** "Retest of a reclaimed low" is
> nearer to the sweep mechanic than "retest of support" was — which is the
> skeptical prior below, now baked into the baseline rather than left as a
> hypothesis. If QM is a liquidity sweep with extra steps, this baseline is where
> that shows up as a flat PRIMARY.

**PRIOR, restated and unchanged:** skeptical. Family is 0-for-3 at ~9,000
signals. The honest hypothesis remains *"QM is a liquidity sweep with extra
steps"* — and if so, the PRIMARY should land near the family nulls while the
already-measured `Liquidity Sweep` (+0.51% @20d, p=0.005) stays the better way to
express the same mechanic.

═══ MEASURED — 2026-09-10, `tools/quasimodo_study.py` ═══════════════════════════

**VERDICT: INCONCLUSIVE — UNDERPOWERED. This is NOT a null, and QM is not
retired.** 53 primary events against the pre-registered floor of 200.

356 liquid names, ~3 years of daily bars (2023-09 → 2026-09), horizon 20d, entry
next open, no costs (they cancel in a differential edge).

| arm | n | signal | baseline | edge | p_rot |
|---|---|---|---|---|---|
| **PRIMARY** QM zone entry vs retests | **53** | +4.31% | +3.61% | **+0.71%** | **none computable** |
| CONTROL CHOCH relaxed, vs retests | 176 | +3.05% | +3.61% | −0.55% | 0.818 |
| CONTRAST QM zone entry vs ALL bars | 53 | +4.31% | +1.86% | +2.45% | 0.556 |
| HARNESS all retests vs ALL bars | 6,669 | +3.61% | +1.86% | +1.74% | 0.707 |
| DIAGNOSTIC bare Renko flip (= B-43) | 4,718 | +1.82% | +1.86% | −0.05% | 0.932 |

**The primary could not even be given a p-value.** `_rotation_p` needs ≥20 rotated
offsets each landing ≥5 events inside the baseline mask, and 53 sparse events on a
narrow mask does not supply that. A missing p is not a weak p — it is the power
problem stated a second way, and it is why nothing here is reported as a result.

**The count was foreseen and is the honest headline.** The build note already
said 202 of 460 names carry a QM but only 14 (3%) had price in the zone on a
given day. Over three years that yields **53 scoreable entries across 356 names**
— 165 of them never form the pattern at all. **A shape this rare cannot be
measured to this desk's bar on three years of daily bars in one market.** Either
the window widens (more history, or intraday bars where the geometry repeats far
more often) or B-58 stays unmeasurable, and that is a scoping fact about the
pattern rather than a finding about its edge.

**What the arms hint at, held loosely and not to be cited as a result:** the
primary's +0.71% and the CHOCH-relaxed control's −0.55% point the *right* way —
dropping `RH > LH` triples the event count to 176 and makes the edge worse, which
is what you would see if the change of character were doing real selection rather
than decoration. At p=0.818 and with no p on the primary, that is a direction to
re-test, not a claim. **`detect_quasimodo` stays geometry: no scanner, no
entry/stop/target, PIPELINE_EXCLUDED**, and `Liquidity Sweep` (B-41m, +0.51%
@20d, p=0.005) remains the measured way to express the same mechanic.

> [!warning] Three things the run caught that reading the design could not
> **1. The equivalence check aborted first, and was right to.** 37 of 355 names
> came back `shipped=None walk=pattern`. Not drift: the shipped detector keeps
> only swings within `lookback` of **today**, so it answers *"is there a QM in the
> last 120 bars"*, while the study needs every QM in the history. Scoping the
> check to the same trailing window took it to **355 agree, 0 disagree**. The
> generalisation is recorded in the code: the detector cuts at a fixed distance
> from the END of the frame, the study cuts each candidate at a fixed distance
> from its OWN completion — for the newest pattern the two coincide, and for older
> ones only the span form means anything.
>
> **2. The baseline as pre-registered could not contain the signal** — see the
> amendment above. Caught by an assertion that ran before any number was scored,
> which is the only reason it was caught at all.
>
> **3. The HARNESS clause fired, and the DIAGNOSTIC arm resolved it.** The
> support-retest state read **+1.74%** against all bars where the family measured
> −0.36/−0.47/−0.43%, which by the pre-registration meant *stop, nothing is
> reportable*. The clause says debug the panel, so the panel was pointed at a
> settled number: **B-43's bare Renko flip reproduced at −0.05% against its known
> −0.02%.** The scorer is sound; the harness arm is **uninformative, not
> contradictory** — exactly B-57's CONTROL2 episode. **The pre-registered
> expectation was the thing that was wrong:** it assumed comparability with B-19's
> family numbers, which are cost-applied walk-forward scanner backtests on
> LIQUID_50 across three windows, against a single uncosted ~3-year window of
> today's liquid 356 here. **Two backtests of "the same idea" are not comparable
> unless universe, window, costs and baseline all match** — and the +1.86% mean
> 20-day return on all bars says most of this window's level is market drift.

**Deferred, not forgotten: multi-timeframe liquidity ("HTF LQ").**
`detect_liquidity_pools` takes one `df`. Real HTF liquidity needs a second
timeframe's pools projected onto the entry chart. That is a bigger build than
this entry and belongs on its own. **Naming trap for whoever picks it up:** `HTF`
in this repo means **High Tight Flag**, not higher timeframe — grepping for it
will produce false confidence that the feature exists.

### ~~B-57~~ · Does a Renko flip out of a SHALLOW correction work on quality names? — **MEASURED 2026-09-07: NO — a soft null, and it CONFIRMS B-43r's mechanism**

Owner's screen idea: cherry-pick names showing a Renko buy flip whose preceding
sell-side flip carried **at most a 40% correction**, and which are fundamentally
sound on revenue and cash-flow growth. This entry is the pre-registration for the
only part of that idea the desk has not already measured.

**The 40% version was killed by counting, before any return was scored.**
`tools/renko_quality_cardinality.py` (committed `f46c638`, counting only — no
forward returns) ran the shipped `renko.js` over 460 liquid NSE names, 3y of bars,
2y scoring window:

| cap on correction | flip_ups kept | share | median `bricks_in_prior` |
|---|---|---|---|
| ≤5% | 19 | 0.4% | — |
| **≤10%** | **631** | **13.7%** | **1** |
| ≤15% | 1,768 | 38.5% | 1 |
| ≤20% | 2,829 | 61.5% | 2 |
| **≤40%** | **4,407** | **95.8%** | **3** |
| none | 4,598 | 100% | 3 |

Median correction into a flip is **17.4%**, p90 is **32%**. A 40% cap therefore
removes 4% of events — **it is not a filter.** Paired with a quality gate that
70% of the sample passes (revenue 3Y CAGR > 0 AND OCF growing; 91% statement
coverage on 80 names), the screen retains ~two thirds of all flips, i.e. it is
substantially the bare flip that [[#B-43r]] measured at **−1.01%, p_rot = 0.000**.

**And the cap is largely a re-run of B-43r's own secondary.** `depth_from_peak`
correlates **0.74** with `bricks_in_prior`. Depth and counter-run length are close
to the same variable, and at a 40% cap the median event carries
`bricks_in_prior = 3` — precisely B-43r's `run ≥ 3` bucket, its **worst** measured
result at −1.30%. Testing 40% would spend a week reproducing a number already on
the page.

What survives is the **tight** end: at ≤10% the median event carries
`bricks_in_prior = 1`, which is the complement of what B-43r tested, and 631
events over 247 names is enough to measure. That is what this entry pre-registers.

> [!warning] The threshold was chosen on cardinality and prior coverage, NOT on returns
> Seven caps were swept in the cardinality study. None of them was scored against
> forward returns, and 10% was selected because it is (a) the tightest rung with
> workable n and (b) the only rung B-43r's secondary does not already cover. No
> return information entered the choice. This is stated because a swept parameter
> that later "works" is the classic way a study launders selection into a result.

═══ PRE-REGISTRATION — written before the first run, per B-43r / B-41p precedent ═══

**PRIMARY TEST (the only one that decides anything)**

| | |
|---|---|
| signal | `flip_up` where `depth_from_peak ≤ 10%` AND the name passes the point-in-time quality gate at that date |
| baseline | **bars in the SAME quality-passing names that are also within 10% of their trailing 60d peak, but carry no flip** |
| horizon | 20 trading days, entry at the next open |
| statistic | mean(signal) − mean(baseline), in percent |
| p-value | circular-rotation test (Welch is invalid — overlapping windows, cross-sectional correlation) |
| **PASS BAR** | **edge > 0 AND p_rot < 0.05.** Anything else is a null and the screen does not ship as a signal. |

**Why the baseline is state-matched, and not "every bar in a quality name".**
Compare a shallow-dip flip against an unconditional baseline and a positive edge
is close to free: shallow dips in growing companies resolve upward often enough
on their own. That would measure *the dip state and the quality screen*, not the
flip. So the baseline is drawn from bars in the same names in the same state,
differing only by whether a flip printed. This is the rule B-44r and B-43r were
both written to enforce: **filter the baseline with whatever you filter the
signal.** The unconditional comparison is still computed and printed, labelled
**STATE CONTRAST**, because the gap between the two is the size of the illusion.

**CONTROLS (expected null / expected negative; if they misbehave, nothing else counts)**

1. **Directional control** — `flip_dn` under identical depth and quality filters,
   scored as a long. B-43r's down leg was a clean null (p=0.331). If this lights
   up, the filters are selecting the dip state rather than the flip, and the
   primary number means nothing either.
2. **Depth-inversion control** — `flip_up` where `depth_from_peak ≥ 25%`, same
   quality gate. **Pre-registered expectation: negative**, reproducing B-43r.
   This is a harness check: if the deep bucket comes out positive, this study
   disagrees with a settled result and must be debugged, not reported.

**SECONDARY (reported, NOT decisive, meaningful only if PRIMARY clears)**
- 60d horizon at the same cap.
- Quality gate tightened from a sign test to a top-quartile OCF-growth rank.
- `depth_from_flip ≤ 10%` as the depth definition instead of `depth_from_peak`.

Three tests on one dataset is already three chances to be fooled. These describe
a surviving effect; they do not hunt for one.

**ABORT CONDITION, declared in advance.** If the point-in-time quality gate leaves
**fewer than 200 signal events**, the result is reported as **INCONCLUSIVE —
UNDERPOWERED**, not as a null. A null and "we could not tell" are different
findings and the desk has conflated them before.

═══ POINT-IN-TIME FUNDAMENTALS — **BUILT 2026-09-07**, and it moved the design ═══

`tools/point_in_time_quality.py` + 12 offline tests. The flip side was already
solved (`renko.js` sizes bricks causally at epoch boundaries; `renko_backtest.js`
emits the underlying bar index, so the harness fills at the next open like every
other signal here). This closes the fundamentals side.

1. **Reporting lag = 60 days, not the 90 this entry first proposed.**
   `fundamentals_deep.ANNUAL_FILING_LAG_DAYS` already encodes SEBI LODR's 60-day
   deadline for audited annual results, with the reasoning written down. Reusing
   it beats inventing a second, more conservative constant that would silently
   disagree with `fcf_negative_streak_as_of`. **One filing-lag assumption on the
   desk, not two.** Lag sensitivity moves to a secondary: re-run at 90d and 120d.
2. **Fewer than 3 published FYs at date T ⇒ EXCLUDED, not FAILED.** `verdict` is
   three-state (True / False / None), the same discipline FR-4's checklist
   enforces. Folding "never tested" into the denominator would understate the
   pass rate by exactly the coverage hole.
3. **Survivorship stands, acknowledged and unfixable on free data.** Every number
   built on this is an **upper bound**; `as_of_report()` prints that on each run.
4. **Restatements are the residual lookahead nobody can close here.** yfinance
   serves the CURRENT frames, so a later-restated FY24 comes back with an FY24
   label and a 2024 publication date — the number a screener sees today, not the
   one the market saw then. Recorded rather than papered over.

> [!warning] The build changed the sample, and the change is not cosmetic
> **yfinance serves exactly FOUR annual columns** (verified: RELIANCE and TCS both
> return FY23–FY26 and nothing older). So the count of *published* years is a
> function of the as-of date, and it is small early in any backtest window:
>
> | as-of | published FYs | usable? |
> |---|---|---|
> | 2024-06-30 | FY23, FY24 | **no** — 2 years |
> | 2025-07-15 | FY23, FY24, FY25 | yes — span **2.0y** |
> | 2026-09-07 | FY23…FY26 | yes — span **3.0y** |
>
> Two consequences, both pre-registered here rather than discovered mid-run:
>
> **(a) The scoring window truncates to 2025-05-30 → 2026-09-07** (~15 months),
> the date FY25 publication makes a third year available. At cap ≤10% that leaves
> **498 events over 233 names** — above the 200-event abort bar, so the study
> remains powered, but the margin is thinner than the 631 the cardinality run
> suggested.
>
> **(b) `WINDOW_YEARS` is FIXED AT 2 for the primary.** Left at 3 the growth span
> would be 2.0y before FY26 publishes and 3.0y after — a gate whose *definition*
> changes mid-sample, so early and late events would not be the same test. Fixing
> the span keeps one definition across the sample; the 3-year version becomes a
> secondary. **The primary must therefore not be described as a "3Y CAGR"** — it
> is a 2-year growth rate, and `quality_as_of` returns `window_years` on every
> event so the claim can be checked rather than assumed.

**One design note worth keeping.** The base year is selected by DATE, not by
column position. Positional indexing assumes yfinance never drops a column and
every company reports on schedule; neither holds, and a dropped year turns a
2-year span into a number labelled 3-year, overstating growth by half. OCF growth
is also expressed as total change over the span rather than annualised, because
a CAGR through a negative base is undefined — and a company whose operating cash
flow was negative three years ago is exactly the one this gate most needs an
opinion about.

═══ RESULT — 2026-09-07, `tools/renko_shallow_quality_study.py` ═════════════════

460 liquid names, 335 quality-passing, 79,401 evaluable bars, window
2025-05-30 → 2026-09-07, 20d horizon, entry next open.

| arm | n | signal | baseline | edge | hit% | p_rot |
|---|---|---|---|---|---|---|
| **PRIMARY** flip_up ≤10%, quality, state-matched | 207 | +0.98% | +1.23% | **−0.25%** | 54.1 / 51.7 | 0.714 |
| CONTROL1 flip_dn as long, same state | 447 | +1.02% | +1.23% | −0.21% | 53.5 / 51.7 | 0.699 |
| CONTROL2 flip_up ≥25%, deep-matched | 113 | +6.81% | +3.44% | **+3.37%** | 59.3 / 55.9 | 0.211 |
| STATE CONTRAST vs ALL quality bars | 269 | +0.67% | +1.59% | −0.93% | 51.7 / 51.3 | 0.173 |
| HARNESS bare flip_up vs ALL bars (= B-43) | 2,742 | +2.08% | +1.58% | +0.49% | 52.0 / 51.7 | 0.376 |

**FAILS the pre-registered bar** (`edge > 0 AND p_rot < 0.05`): the edge is
negative and nowhere near significant. **B-43 and B-43r stand.** Renko remains a
chart overlay labelled FLIP and remains in `PIPELINE_EXCLUDED`.

> [!key-insight] The null is SOFT, and that is the informative part
> B-43r measured the flip at **−1.01%, p_rot = 0.000**. Restricted to shallow
> corrections on quality names it reads **−0.25%, p_rot = 0.714** — the penalty
> has essentially dissolved. That is exactly what B-43r's mechanism predicts: an
> up-flip is punished because it re-enters after giving back part of a run, and a
> ≤10% pullback gives back little. **The prior recorded in advance said "a small
> positive edge that fails the p-bar"; the outcome was a small NEGATIVE edge that
> fails it.** Half right — the direction was wrong, the significance call was not.
> The mechanism survives as an explanation; the trade does not appear.

**CONTROL2 did NOT behave as pre-registered, and that is a real limitation.**
The entry pre-registered the deep bucket as **negative**, reproducing B-43r. It
came back **+3.37%**. Per the pre-registration's own clause a misbehaving control
means debug rather than report, so a **HARNESS arm** was added: the bare flip
against an unconditional baseline, which is B-43's construction and B-43's settled
clean null (−0.02%). It reproduces as a null here (+0.49%, p=0.376) — significance
agrees; the point estimate differs because this panel is 460 names over 15 months
rather than 22 names over years. **The scorer is therefore not broken, and
CONTROL2's sign is a property of its sample: 113 events in deeply drawn-down names
across a window that was kind to them, at p = 0.211 — not significantly different
from zero and not evidence of anything.** It neither reproduces nor contradicts
B-43r. The control was uninformative, which is weaker than the design assumed, and
the primary should be read with that slack in mind.

**The illusion ran BACKWARDS from B-43r, which is worth recording.** There the
unmatched baseline flattered the signal. Here the STATE CONTRAST is **−0.93%**
against the matched **−0.25%**: a careless test would have *over-condemned* the
flip. Baseline matching is not a one-way correction toward pessimism — it moves
the answer toward the truth, in whichever direction that lies.

**Limits, and they are not small.** 207 primary events against B-43r's 576. One
15-month window in one regime — the point-in-time gate needs three published
fiscal years and yfinance serves only four annual columns, which is what truncated
it. Survivorship makes every figure an UPPER BOUND. The rotation grid is coarse
(every 3rd offset), so p is indicative. **This is a weaker null than B-43r's, and
should be cited as "no edge found, underpowered" rather than as a settled zero.**

**What ships: the attention list, and NOTHING that votes.** The pre-registered
fail path said a null leaves the screen available as a view rather than a signal,
and that is what was built the same day: **`scan_shallow_flip`**, registered as
*Shallow Flip (Renko, bounded correction)* with 12 tests.

The null is enforced structurally, not by wording a later edit could soften —
the same three locks `scan_renko_flip` carries:

| lock | why |
|---|---|
| no `entry` / `stop` / `target` keys | those are what make a hit read as a plan |
| in `opportunity_hub.PIPELINE_EXCLUDED` | it can never become a confluence vote |
| `score` = freshness + shallowness | never conviction; B-57 measured no edge |

The card states the measured number in its own reasons — `−0.25% at 20d,
p_rot=0.714, n=207` — and a test asserts that text is present, so the finding
cannot quietly fall out of the UI.

**Quality is NOT filtered inside the scanner.** Registry scanners are pure price
functions of `df`, and the Hub card already renders a fundamentals strip beside
every hit, so cash-flow and EPS sit next to the flip and the reader decides.
Filtering on it in a price scanner would hide the disagreements, which on an
attention list is precisely the information.

**Live check on the 460-name cache: 5 hits** (MON100 3.8%, VOLTAMP 9.3%,
IDFCFIRSTB 7.0%, SHILPAMED 8.2%, ANDHRAPAP 9.2%). Selective rather than a
firehose, which is what a ≤10% cap buys — the ≤40% version would have returned
the flip list nearly whole. One of the five is an ETF, so the Hub's universe
should carry the cash-equivalent filter the Trending Stocks build already
defines (`isLikelyLiquidETF`) if this screen is ever pointed at a raw universe.

**The owner's 40% version was never run**, because `renko_quality_cardinality.py`
showed it is not a filter (96% of flips clear it) and that its median
`bricks_in_prior` = 3 sits on B-43r's worst measured bucket. Counting first saved
the study that would have reproduced a known negative.

═══ SCOPE — what a pass would and would not license ══════════════════════════════

A pass licenses **one** thing: a further pre-registered test on a walk-forward
sample that did not select the threshold. It does **not** grant MEASURED_EDGE
status, does not move Renko out of `PIPELINE_EXCLUDED`, and does not relabel the
chart overlay from FLIP to BUY. B-41p's scope clause is the precedent.

A fail leaves the screen available as an **attention list** — "quality names that
just turned up after a shallow pullback" is a defensible thing to put in front of
a human, and this desk's convention is that such lists ship labelled as questions,
not as entries. That is the Scanner-Hub-shaped outcome, and it needs no edge to
justify itself.

**Prior recorded in advance.** Skeptical, but less so than for B-43r. Two nulls and
one significant negative sit behind this signal, and the mechanism B-43r identified
— an up-flip selects the moment just after a counter-move, and holding beats
re-entering — **weakens but does not vanish** at a 10% cap, because a shallow
pullback gives back little of the run. Against that, the quality gate is doing work
B-43r's basket never had. Expected outcome: a small positive edge that fails the
p-bar. If it clears, the depth-inversion control is what decides whether to believe it.

### ~~B-43r~~ · Does the Renko flip work once sideways chop is cut? — **MEASURED 2026-09-06: NO, IT IS SIGNIFICANTLY WORSE**

Owner's observation from watching the chart: flips look convincing when momentum is
trending and worthless when it is sideways, so a trend filter should recover the edge
B-43 could not find. A real, testable claim — and the shape of claim that most often
produces a false positive, so `tools/renko_regime_study.py` was written to make that
hard: pre-registration in the docstring, one primary test, a directional control, and
secondaries explicitly labelled non-decisive.

**Pre-registered before running:** long flips with ADX(14) >= 25, against a baseline of
**every bar with ADX(14) >= 25**, 20d horizon, entry next open, rotation p-value.
Pass bar: `edge > 0 AND p_rot < 0.05`.

| test | n | signal | baseline | edge | hit% | p_rot |
|---|---|---|---|---|---|---|
| **PRIMARY** flip_up, ADX-matched | 576 | +1.13% | +2.14% | **−1.01%** | 53.1 / 57.7 | **0.000** |
| CONTROL flip_dn as long | 655 | +2.52% | +2.14% | +0.38% | 56.9 / 57.7 | 0.331 |
| SECONDARY flip_up, brick run ≥3 | 394 | +0.84% | +2.14% | **−1.30%** | 53.0 | — |
| B-43 reproduction, no filter | 1766 | +1.60% | +1.61% | −0.02% | 56.0 / 55.7 | — |

**Inside a trend, a flip marks a moment measurably WORSE than an average moment in that
same trend.** Not "no better" — worse, by a full percent at 20d with p_rot = 0.000.

**The mechanism is legible, which is why the sign is believable.** ADX >= 25 means a
trend is running. An up-flip *requires* price to have first fallen enough to print down
bricks and then turned back up, so it systematically selects the moment just after a
counter-move: part of the run already given back, and the point where a pullback is
hardest to tell from a real reversal. The matched baseline — "any bar in a trend" — is
simply already long and holding. **Holding beats re-entering.** The brick-run secondary
sharpens the same point: the longer the counter-run before the flip, the more of the
trend was missed, and the worse it gets (−1.30%).

**The controls behave, which is what licenses the sign.** The down-flip control is a
clean null (p=0.331), so the ADX gate is not merely selecting good periods and lifting
everything. And the unfiltered arm reproduces B-43 (−0.02% vs its clean null), so the
harness agrees with the study it is extending.

> [!key-insight] Why it looked convincing, and what the REGIME CONTRAST line is for
> In a strong trend everything looks convincing in hindsight — the flips looked right
> because the trend was right. The study prints the same flips against an UNFILTERED
> baseline precisely to size that illusion. Here it reads **−0.48%**, so even the
> careless version of this test would not have shown an edge. **The illusion was
> visual, not arithmetic** — which is the more common of the two and the one no
> baseline correction can catch.

**Methodological point worth keeping.** Gating the signal on ADX while comparing to an
unconditional baseline would have measured the regime, not the flip. That is the same
trap that killed B-44r (BS gamma carries 1/σ, so "high gamma" proxied for "low vol")
and the same shape as B-34r4's drifting window. **Filter the baseline with whatever you
filter the signal.**

**Not a licence to fade flips in trends.** The pre-registered bar was `edge > 0`, so a
significant negative FAILS it; "flips are contrarian" is a new claim needing its own
pre-registration, and −1% would not survive costs on the short side. Limitations: 22
symbols, one threshold, survivorship in the basket.

**No change to what ships.** Renko stays a chart overlay labelled FLIP (not BUY/SELL)
and stays in `PIPELINE_EXCLUDED`. B-43 already put it there for measuring no edge; this
result only strengthens the case for the exclusion that already exists.

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

**Deliberately out of scope here, done next:** the SCORE's promoter term — **B-34r4**.

### ~~B-34r4~~ · The score's promoter term had the same drift — **MEASURED 2026-09-05: the lane's edge was the bug**

`score_from_cache`'s −15 / +10 promoter term compared the oldest cached quarter against the
newest, exactly as the veto did. The institutional term never had the problem — it already
divides by `(len-1)` into a pp/quarter rate. Bounded to the same 4-quarter window, then
re-measured.

All rows below: Smallcap-250, top 25, 6 eval quarters, same session, so they are
comparable to each other rather than to the historical B-34 figure (which used a different
universe).

| score term | veto | 60d edge | p | 120d edge | p | hit% 60d |
|---|---|---|---|---|---|---|
| unbounded | none | +0.91% | 0.539 | +1.47% | 0.543 | 59.3% |
| unbounded | drifting | +1.21% | 0.417 | +2.15% | 0.388 | 60.7% |
| unbounded | bounded | +1.02% | 0.495 | +1.46% | 0.550 | 60.0% |
| **bounded** | **none** | **−0.12%** | 0.936 | **+0.20%** | 0.935 | 56.0% |
| **bounded** | **bounded** | **+0.05%** | 0.973 | **+0.33%** | 0.892 | 56.0% |

Universe baseline hit rate is 56.5% at 60d. **With both windows bounded the ranking sits at
or below a random pick from the same universe, and the veto changes nothing.**

**Every positive number this lane has ever shown traces to one defect.** A cumulative
promoter drop measured over an ever-lengthening window made names look progressively worse
as the cache deepened, and the ranking was partly sorting on that artefact rather than on
conviction. Remove it and the edge is gone.

**What survives is what B-34 always said was the primary value: coverage.** The lane
surfaces real small/micro-caps the large-cap funnel structurally cannot see. What does not
survive is any claim that ranking them by institutional conviction beats picking from the
same universe at random.

> [!contradiction] B-34's headline figure is superseded
> B-34 closed with "+2.51% @60d (p=0.22), +6.29% @120d (p=0.14) → WEAK". That was measured
> with the unbounded promoter term in the score. It is not a like-for-like comparison with
> the table above (different universe), but it is measured on the same defect, so the
> positive reading should not be relied on. A clean re-run on `kind="both"` would settle
> the number; the direction is already clear.

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

**The blocker is gone — the test is now possible (2026-09-05).** `fundamentals_deep` was
calling `.tolist()` on statement rows and discarding the frame's column dates, so
`fcf_history` was five numbers with no way to say which years they covered. `_period_ends()`
keeps them as **`fcf_years` / `shares_years`**, aligned by position, and
`fcf_negative_streak_as_of(deep, as_of)` counts only years published by a given date —
fiscal year end plus **60 days** (SEBI LODR's deadline for audited annual results, so a
31-Mar year end is not knowable until roughly end-May).

No new source and no scraping was needed: the labels were already in the yfinance payload
being thrown away. A commercial site was offered and declined — scraping today's page still
would not give history *as it was known then*, which is the only thing that makes this test
honest.

**The look-ahead was real, and is now measured rather than asserted.** SAILIFE, the name the
original veto removed from the top of the list:

| as of | streak | years known |
|---|---|---|
| 2024-09-30 | **0** | 3 |
| 2025-09-30 | **1** | 4 |
| 2026-09-05 | **2** | 5 |

Today's payload reports streak 2. Vetoing SAILIFE at a September-2024 entry — exactly what
the live gate did before the demotion — used a fact that was not public for another two
years.

An *unknown* streak is neither a veto nor a pass: symbols with no cash-flow frame, or with
nothing filed by the entry date, carry no FCF verdict at all. Same principle as FR-4's
NOT_CHECKED.

**MEASURED 2026-09-05.** All arms on the bounded score, Smallcap-250, top 25, 6 quarters:

| arm | 60d edge | p | 120d edge | p | hit% 60d | hit% 120d |
|---|---|---|---|---|---|---|
| no veto | −0.12% | 0.936 | +0.20% | 0.935 | 56.0% | 55.2% |
| governance veto | +0.05% | 0.973 | +0.33% | 0.892 | 56.0% | 56.0% |
| **FCF veto (point-in-time)** | **+0.22%** | 0.888 | **+0.69%** | 0.800 | 56.0% | **52.8%** |
| governance + FCF | +0.22% | 0.888 | +0.69% | 0.800 | 56.0% | 52.8% |

Universe baseline: 56.5% @60d, 53.6% @120d.

**The demotion stands, and now for a measured reason rather than an untestable one.** The
point-in-time FCF veto is the best arm on mean edge (+0.69% vs +0.20% at 120d) and it is
still nothing: **p = 0.80**. It also *lowers* the 120d hit rate to 52.8%, below the 53.6%
baseline — edge up while hit rate falls means a few large winners, not more winners. There
is no case here for restoring it to a hard veto, and none for removing the penalty either.

**The two veto arms are byte-identical, and that is correct, not a bug.** Checked directly:
**zero** of the FCF-eligible top-25 carry a governance flag, in *every* one of the 7
quarters.

| quarter | gov-vetoed (all) | fcf-vetoed (all) | gov-vetoed **inside top-25** |
|---|---|---|---|
| 31-DEC-2024 | 7 | 48 | **0** |
| 30-JUN-2025 | 43 | 51 | **0** |
| 31-DEC-2025 | 50 | 52 | **0** |
| 30-JUN-2026 | 47 | 59 | **0** |

**The governance veto is redundant with the score.** Promoter selling already costs −15,
pledge −20, promoter steady/adding +10 — so a governance-flagged name essentially cannot
reach the top 25 on score alone, and the veto only ever removes names far below the cut.
That also explains B-34r3's near-zero measured effect. It is not useless — the vetoed list
is informative on the page, and it protects a thin universe where 25 names might otherwise
be scraped from the bottom — but it should not be described as improving the shortlist,
because on this evidence it cannot.

**Shipped 2026-09-06 — the Hidden Treasures page now carries this number.** The caption
still advertised B-34's "+2.5% @60d (p=0.22)", i.e. the figure this item retracted, so the
one place a reader actually meets the lane was quoting the artefact. It now reads
−0.12% @60d (p=0.94) / +0.20% @120d (p=0.94), cites B-34r4 rather than B-34, and says why
the old number was wrong — a reader who remembers +2.5% sees where it went instead of
assuming a typo. `tools/dashboard_app.py`, commit `d6c9dd7`.

### ~~B-34r5~~ · Gate or display? — **MEASURED → display. SHIPPED 2026-09-05**

Measured on the LIVE scoring path (not the backtest) by ranking without the veto and
finding where flagged names actually land:

| universe | scored | flagged | first flagged rank | in top 25 / 50 / 100 |
|---|---|---|---|---|
| Smallcap-250 | 249 | 50 | **128th** | 0 / 0 / 0 |
| Microcap-250 | 250 | 56 | **60th** | 0 / 0 / **1** |

The page's "Show top N" maxes at **100**, so the gate can reach **at most one visible name,
usually none**. It was removing names nobody was going to see, while the banner implied the
list had been filtered.

**The reason is structural, not luck.** The score already costs −15 for promoter selling
and −20 for pledge, so a governance-flagged name cannot climb into the top ranks. The veto
was re-applying, as a hard cut, a judgement the ranking had already made — which is also
why B-34r2's two veto arms came back byte-identical and B-34r3's fix measured near zero.

**Shipped:** the toggle defaults **off**, and flagged names are **marked on their own card**
with the specific flag ("⛔ Equity dilution (share count)") rather than removed. That is
strictly more information than a veto — you see the name, its score and the reason at the
point of use. The toggle stays for anyone who wants the hard cut. Verified on Microcap-250:
100 hits returned, INOXGREEN marked at #60 instead of vanishing.

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

### B-56 · Structural BUY/SELL/HOLD from POC · HVN/LVN · shape series — **BUILT 2026-09-06, PRE-REGISTERED TEST PENDING**

Owner's push-back, and it was right: retiring the SVP *composite* does not retire
structural inference from volume profile. `tools/svp_structure_signal.js` is a
SECOND, separate construction — different inputs, explicit named rules, no
weights and no score, and it does not read the composite.

> [!key-insight] The directional correction that makes this buildable at all
> The proposal was "HVN as resistance, LVN as support". Half right, and the wrong
> half would have made the signal wrong by construction. **HVN is ACCEPTED price**
> — congestion, so it is resistance approached from below and support approached
> from above; either way price stalls in it. **LVN is REJECTED price** — thin
> trade, no inventory, so price traverses it FAST. An LVN is not support; it is an
> accelerant and a boundary between value areas. **A stop below an LVN sits in the
> one place the market moves through quickest**, and gets hit on the way somewhere
> else. Stops belong behind an HVN, targets beyond an LVN. The emitted fields are
> named by ROLE (`support_hvn`, `fast_below`) so the error cannot be reintroduced
> downstream.

**Trend comes from POC MIGRATION, not the shape sequence.** Migration is the path
of per-session POCs: rising POCs mean buyers accepting higher prices session after
session, which is trend by definition rather than by pattern-matching. Measured as
a monotonicity FRACTION (≥0.60), not first-vs-last — two POCs 10% apart with chaos
between is not a trend and first-vs-last cannot tell the difference. The shape
series is the secondary read.

**The rules, stated so they can be argued with.** BUY = migration rising AND price
at/above composite POC AND the nearest structure below is an HVN not an LVN AND
last shape P or D. SELL mirrors. Everything else HOLD, explicitly including
balance-dominant sequences. **No weights** — each rule is a named boolean and the
page prints which fired, because the specific failure of the composite it replaces
is that `trap` carried weight 1.5 and attributed at −0.51 and no reader could have
seen that from the card.

**Universe result (nifty500, 500 symbols): HOLD 366 / SELL 97 / BUY 37** — 7.4%
BUY, selective rather than firing on everything.

**UNMEASURED, and the prior evidence points AGAINST it.** The 2026-08-29
attribution scored `sequence` at −0.67 and `va` at −0.71, and those are exactly the
inputs this uses. That is a reason to measure it, not to skip building it — but it
means B-56's pre-registered test is required before this goes near the pipeline,
and it stays a bystander until then per B-55's gate.

**Engine change:** `SVP.analyze` now also returns `compositeProfile` (the full
profile behind `composite`, with `hvnZones`/`lvnZones`). Additive — `composite`
keeps its `{poc,vah,val}` shape, every existing caller untouched — and exposed
rather than recomputed outside, which would be a second profile free to disagree
with the one the card draws.

**Also shipped:** the standard action-icon family on the table (Chart 👁 / Analyze
↗ / TradingView / Screener / Google Finance), so a row reaches the chart, the
analyzer and the watchlist without retyping a symbol.

### B-55b · SVP screen on the full universe, BUY-first — **SHIPPED 2026-09-06**

`svp_universe_export.py` (nifty500 -> `cache/svp_bars`) + the existing runner.
**500 of 501 exported** (1 too thin, 0 failed); the screen reads all 500.

| read | count |
|---|---|
| HOLD | 366 |
| SELL | 97 |
| **BUY** | **37** |

Migration across the universe: falling 171 / mixed 195 / rising 134. **BUY+D = 24**,
the page's default view (23 shown — PTCIL sits 33.5% from its POC and is cut by the
default 25% proximity slider).

**Defaults are BUY + D, not restrictions.** SELL and HOLD stay computed and one
click away: a screen that can only show one side loses the ability to say *that
side is empty*, which is itself information on a quiet day. The D default is
STRICTER than the rule — BUY accepts P or D, and 13 of the 37 BUYs are P-shape, so
the default hides them. The help text says so.

> [!key-insight] A blank `res HVN` on a BUY row is meaningful, not missing
> `support_hvn` is populated on **37 of 37** BUY rows and `resistance_hvn` on
> **97 of 97** SELL rows — each rule requires that node to exist. So a BUY with
> nothing above means price has cleared every accepted zone: no overhead supply,
> the bullish reading. **But it also means there is no structural target.** The
> construction yields an entry and a stop (behind `sup HVN`) and nothing to aim
> at. That is a real limitation of the method, not a gap in the data, and the page
> says so rather than leaving the column looking broken.

**Export is deliberately light:** 400 daily bars, not the backtest cache's 2007
start. The screen reads ~12 retained sessions, so 18 years for 500 names would be
~40x the download for the same answer, and yfinance is the rate limit. 400 is
generous against the floor because the grain-picker measures bars-per-day from the
data — a symbol resolving to DAILY grain needs more bars than the weekly case, and
a short pull would silently give it fewer sessions rather than failing.

Generated data (`cache/svp_bars/`, `svp_screen.csv`) is gitignored — regenerated,
not source.

**Still a bystander.** B-55's gate is unchanged: nothing reaches the pipeline until
B-56's pre-registered test runs.

### B-55 · SVP Structure screen — **SHIPPED 2026-09-06 as a BYSTANDER, promotion deliberately deferred**

Owner asked for a screener on the chart tool's SVP confluence. Built as
`tools/svp_screen_runner.js` (batch the REAL engine headlessly, same modules the
chart loads) + a **SVP Structure** page under Screening.

**What it screens on, and the one thing it refuses to.** Structure only: value-area
state, distance to composite POC, session shape sequence, trap/accumulation state.
**Not the confluence score and not its BUY/SELL direction** — that score measured a
clean negative on 2026-08-29 (corr(score, 20d fwd) = −0.041, deciles
non-monotonic, BUY-high confidence performing WORSE than BUY-low, 5 of 7 factor
families sign-inverted including `trap` at the largest weight). A screener exists
to surface its top-ranked names, so ranking on that score would systematically
surface what the measurement says to avoid.

**Bystander by explicit instruction, and the instruction is the useful part.**
Owner: *"I wish to have the SVP screener as bystander now, based on accuracy we
can take a call to wire it into pipeline, that too at the end of the pipeline."*
So: not a registered scanner, not in `pipeline_scanners()`, no ranking weight,
nothing downstream reads it. Verified — `SVP in scanner registry: False`, `SVP in
pipeline: False`.

**The promotion gate, recorded now so it is not invented later:** a measured
accuracy result on the STRUCTURAL fields, and even then it enters at the END of
the pipeline. That ordering matters — a late-stage lens filters a shortlist
someone else ranked, where an early-stage one shapes what gets considered at all,
and a lens whose parent score measured negative should not be shaping the
candidate set.

**Two stale things found while building.** (1) The engine retains
`maxSessions = 12`, but the card's prose calls it "the 5-session acceptance
range" — the screen reports `n_sessions` per row rather than forcing 5, since
changing it would make the screen disagree with the chart. (2) On NSE dailies the
measured grain-picker resolves to **weekly**, so a "session" here is a week
(24 of 26 rows) — worth knowing before reading "last 5 sessions" literally.

**Node, not a Python port**, importing the same modules the chart loads. Not
hypothetical caution: on 2026-09-06 the VWAP mean-reversion JS and Python
disagreed because one averaged 19 bars over a divisor of 20 — a bug neither
implementation revealed alone.

### ~~B-41w~~ · Does the time-only plan hold across eras? — **PRE-REGISTERED, PASSED 2026-09-06**

The single follow-up B-41p's scope clause licensed. Design committed before the
run; pass bar was arm C positive in all three chronological windows AND ahead of
the shipped plan in all three.

| window | trades | from | to | C mean R | A mean R | C−A |
|---|---|---|---|---|---|---|
| 1 | 1618 | 2020-11-13 | 2023-04-10 | +0.335 | −0.032 | +0.367 |
| 2 | 1618 | 2023-04-10 | 2025-04-03 | **+0.927** | +0.005 | +0.922 |
| 3 | 1618 | 2025-04-03 | 2026-08-06 | +0.273 | −0.146 | +0.419 |

**arm C positive 3/3 · C beats A 3/3 · VERDICT: STABLE.**

The shipped plan is negative in two windows of three and never above +0.005R. The
time-only exit is positive in all three and ahead in all three. **The conclusion
from B-41p survives era-splitting**, which B-19's 0/41 says is where these results
usually die.

> [!key-insight] The registered prior was wrong, and the reason matters more than the miss
> B-41w predicted window 2 would be the weak one, because B-41m's forward
> walk-forward had its window 2 at +0.06%. Window 2 came back **strongest**
> (+0.927R). The prior was not actually testable as written: `walk_forward_scanner`
> splits by **bar fraction** (`i/n` to `(i+1)/n` of the bar range) while B-41w
> splits by **equal trade counts**. Those are different partitions, so "window 2"
> names different periods in the two studies and the prediction never mapped.
>
> Recorded rather than quietly dropped. A prior that turns out to be untestable is
> a defect in the pre-registration, not a free pass — the fix next time is to
> state the partition, not just the window number.

**What still does not follow.** The scope clause held across both tests and holds
now: **the scanner is not promoted.** Arm C's downside is uncapped where a stopped
arm loses at most 1R, so "positive mean R in every era" is not the same as
tradeable. What the three studies jointly establish is narrower and worth stating
exactly:

> The Liquidity Sweep signal carries forward information that is stable across
> symbols (B-41p bootstrap) and across eras (B-41w), and **any stop of the shipped
> magnitude destroys it** — not because the stop is misplaced (arm B: +0.012R, CI
> includes zero) but because the drawdown path is part of the edge.

The open design question is a risk control that is not a stop — position sizing,
a volatility cap, a portfolio-level limit. **None of these tests touch that**, and
it is not a small step: a plan with uncapped per-trade downside needs its risk
handled somewhere, and "hold 20 days and hope" is not a plan.

**Reproducibility note.** Re-running B-41p on freshly fetched bars moved arm A
from −0.059R to −0.058R and arm C from +0.504R to +0.511R. Same code, same
symbols; yfinance returned marginally different history between runs. ~0.01R on
4,854 trades is benign, but it is the reason figures here are quoted to three
decimals and not more.

**Trades cached** to `cache/b41p_trades.csv` (4,854 rows with dates), so the next
pre-registered test on this data costs nothing to collect.

### ~~B-41p~~ · Is the STOP why the sweep edge does not convert? — **PRE-REGISTERED, PASSED 2026-09-06**

Design committed at `f2c4982` **before the first run**, three fixed arms, one pass
bar, Bonferroni across the two comparisons. `tools/sweep_plan_study.py`.

| arm | mean R | win% | vs SHIPPED | 97.5% CI |
|---|---|---|---|---|
| A — SHIPPED (wick stop + pool target) | −0.059 | 43.2 | — | — |
| B — ATR stop (1.5×ATR14, same target) | −0.047 | 50.8 | +0.012 | [−0.077, +0.102] **includes 0** |
| C — TIME ONLY (no stop, exit 20d close) | **+0.504** | 54.9 | **+0.564** | **[+0.337, +0.798] excludes 0** |

4,854 trades, 50 symbols, 29bps, 2,000-draw symbol-block bootstrap.
**C passes; B does not.**

> [!key-insight] It is not WHERE the stop is. It is that there is one.
> Swapping the wick stop for an ATR-derived stop moves the result by +0.012R with
> a CI straddling zero — nothing. Removing the stop entirely turns −0.059R into
> **+0.504R**. The shipped stop is not badly placed; a 20-day hold on this signal
> cannot survive a stop of that magnitude at all. **The drawdown path is part of
> the edge**, which the −7.3% average MAE in B-41m already hinted at and nobody
> had connected.

**What arm C actually is, stated so it is not oversold.** It is B-41m's forward
study expressed in R: buy next open, exit at the 20-day close. So its passing is
not independent evidence of profit — it is the SAME +0.51% @20d, converted. The
new information is the *comparison*: identical signal, identical horizon, +0.50R
unstopped against −0.06R stopped.

**Three things this does not license.**

1. **Not a promotion.** The pre-registration's scope clause said a pass licenses
   one thing — a further pre-registered test of the plan — and explicitly not
   MEASURED_EDGE status, which needs the new plan on its own walk-forward rather
   than on the sample that selected it. The scanner stays at unmeasured weight.
2. **A stopless hold is not "safer" because its mean R is higher.** Arm C's
   downside is uncapped; the other arms lose at most 1R by construction. A better
   average with an unbounded tail is a different risk profile, not a strictly
   better one, and position sizing off +0.504R would be a category error.
3. **The trade count is not comparable to B-41m's.** This study takes every firing
   bar (4,854); `backtest_scanner` dedupes with `min_gap=5` (1,400). The extra
   trades are clustered repeats of the same setup, so they are more correlated
   than n suggests — which is exactly why the bootstrap resamples symbols and not
   trades.

**The smoke run is a worked example of why 2 symbols is not a sample.** On
RELIANCE + TCS alone arm C read **−0.469R**; on 50 it reads **+0.504R**. The
bootstrap resamples symbols, so a 2-symbol CI (±1.88) is meaningless by
construction. Recorded because the temptation to read a fast smoke number as a
result is exactly how a desk fools itself.

**Prior recorded in advance: "C beats A; B lands between." C beat A; B did not
land between — it was indistinguishable from A.** Half right, and the half that
was wrong is the informative half: it rules out stop *placement* as the lever.

### ~~B-41m~~ · Liquidity Sweep measured — **2026-09-06: the desk's best result, and its plan does not harvest it**

B-41 shipped the detector; nothing had ever measured it. B-19's batch never covered
it (no `Liquidity_Sweep` file in `cache/b19_verdicts/`), so its docstring correctly
still said "not been through the backtest harness" — the one such claim of three
that survived this morning's sweep.

**Bullish arm, 1400 signals, LIQUID_50:**

| horizon | hit% | edge gross | p | edge net | p |
|---|---|---|---|---|---|
| 5d | 53.3 | +0.12 | 0.23 | +0.13 | 0.19 |
| 10d | 56.1 | +0.25 | 0.062 | +0.26 | 0.056 |
| 20d | 57.5 | **+0.50** | **0.0065** | **+0.51** | **0.0053** |
| 60d | 64.1 | **+0.87** | **0.0032** | **+0.91** | **0.0022** |

**It survives costs**, which nothing else measured this session does.

**Walk-forward (3 windows, ~29bps) — MIXED, stable at 10/20/60d:**

| window | signals | 5d | 10d | 20d | 60d |
|---|---|---|---|---|---|
| 1 | 400 | +0.31 | +0.47 | +0.51 | **+1.42*** |
| 2 | 404 | −0.15 | +0.03 | +0.06 | +0.12 |
| 3 | 603 | +0.24 | +0.36 | **+1.00*** | **+1.70*** |
| OOS | 1407 | +0.15 | +0.29 | +0.59 | +1.16 |

Sign-consistent 3/3 at 10d, 20d and 60d. **Against B-19's 0/41 stable, that is the
strongest stability this desk has recorded** — and B-19 never tested this scanner,
so it is a gap being filled, not a contradiction.

> [!key-insight] Two things stop this being called an edge, and both matter
> **1. The magnitude lives in two windows of three.** Window 2 is +0.03 / +0.06 /
> +0.12 — indistinguishable from zero. The SIGN is stable; the SIZE is not.
> Degradation confirms it: pooled +1.16 @60d against a best window of +1.70, a
> −0.54 gap. Part of this is period, not signal.
>
> **2. Its own trade plan converts the edge to nothing.** R expectancy is +0.23R
> gross and **+0.06R after costs**, on win% 39.2 with target hit 549 times against
> stop 842. The signal carries forward information and the shipped stop/target
> throws it away — the stop is hit three times for every two targets.

**The obvious fix is the one thing not done here.** Widening the stop after seeing
which stop lost is fitting the plan to its own answer. If the levels are worth
revisiting it needs a pre-registered test, the way B-43r was written before it ran.
Recorded as the open question, deliberately unanswered.

**Bearish arm — 1471 signals, negative at every horizon** (−0.16 / −0.18 / −0.32 /
−0.56 gross), p 0.11 / 0.19 / 0.084 / 0.063. Scored as forward LONGS, so negative is
the direction a bearish signal should point, but nothing reaches significance.
Suggestive, not established. **No R line: it emits `entry` and `stop` but
`target=None`**, so the harness correctly reports no plan — a real gap in the
scanner, not a harness limitation.

**Verdict: a LEAD, and the desk's best one.** Not promoted to MEASURED_EDGE, which
requires an edge the plan can actually harvest. Left at unmeasured weight in
`opportunity_hub` rather than upgraded, because the honest reading of +0.06R is that
trading it as shipped returns nothing.

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

**Re-verified 2026-09-10 — three of the four fixed themselves, and the item
shrank without anyone closing it.** `tools/cache/ownership/` now holds **751**
files, not 496, and `ABBOTINDIA`, `BAYERCROP` and `MCX` each have a populated
cache. **Only `BSE` is still missing.** Note what that does to the diagnosis:
one uncached symbol out of ~1,500 is not evidence of a systematic filter bug, so
the "probably our bug" prior is now weak. `get_shareholding_filings` was
rewritten since (it sorts on the parsed `date` and dedupes revisions — the old
`toDate` sort key was absent on every row), which is the likely cause of the
recovery. Remaining work is one symbol: check whether `BSE` — the exchange
itself — is filed under a different NSE symbol string, before touching the
filter again.

---

## P4 — Scoped elsewhere, or small

| | Item | Notes |
|---|---|---|
| B-20 | **Index PCR has no history, so no band** | `index_reading()` ships deliberately unbanded. Five same-day observations cannot be ranked; an index can only be ranked against its own past. Storing a daily index PCR is the whole fix. |
| B-22 | **Sentiment Index factor 5 unwired** | `pcr.py` exists and is the primitive that factor was always waiting for; nothing consumes it there yet. |
| ~~B-23~~ | **Strike-level option OI** (OI audit Gap 3) — ✅ **CLOSED 2026-09-02** | Was: "the largest remaining OI item, needs its own design pass." **The premise was stale** — B-44's `gamma_exposure.py` had already built the per-strike bhavcopy reader this was scoped to design, so the remaining work was the LEVELS read, not the feed. Third stale entry this week after B-11 and B-42. Shipped `option_chain.py`: `load_chain` (per-strike CE/PE OI for **stocks (STO) and indices (IDO)** — `gamma_exposure` is index-only), `max_pain`, `oi_walls`, `read_levels` + `format_levels`, plus `/api/option_levels` on chart_server so B-28's overlay has an interface to consume. 26 tests. Live: NIFTY spot 24,055.80 / max pain 24,050 on expiry day (converges, as theory predicts); RELIANCE 1,308.96 between its 1,300 put wall and 1,320 call wall. **Two correctness rules enforced:** max pain REFUSES a pooled-expiry chain (payoff settles per expiry — a far-month strike does not pay out on this week's settlement, so a pooled number is a different quantity, not a smaller error); and call walls are restricted to strikes at/above spot, put walls at/below, because a large call OI far below spot is deep-ITM inventory and ranking it as "resistance" would put the strongest resistance *under* the price. Levels ship **unmeasured** — see B-28. |
| B-13 | AW-1…AW-4 astro weekly card | Good-to-have; AW-0 shipped. |
| B-15 | SR-7 Trendlyne backfill | Optional, only if XBRL coverage proves short. |
| B-17 | OBV has no wiki page | Verified absent; ships as a chart indicator, undocumented. **Re-verified 2026-09-10: still absent** (`wiki/concepts/` has `Chaikin-Money-Flow.md` from B-60 and no OBV page) — and the debt **grew**, because B-61 shipped an OBV *divergence* overlay on 2026-09-07. Two OBV surfaces, zero pages. The B-60 ingest is the pattern to copy: the concept page was written with the build. |
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

### ~~B-62~~ · Turnover-share rotation column (sector) — **BUILT 2026-09-09**

From [[sources/ScreeningMantis-Price-Volume-Sector-Rotation-2026-09-09]], the one
idea on that site the vault did not already hold. Concept:
[[concepts/Turnover-Share-Rotation]].

Per sector, per day: turnover as a **share of total market turnover**, and the
**change in that share in percentage points** over 1 day and 5 days.

Why it is worth a column and not a scanner:

- **Zero-sum by construction** — the shares sum to 1, so the Δ column sums to
  zero and every gainer takes from a named loser. A sector-return column has no
  such constraint and says little on a broad day.
- **It disagrees with price, usefully.** 2026-09-09: IT took **+2.70 pt of
  turnover share** while NIFTY IT fell **-3.24%**. Money in, price out.
- **Turnover is unsigned**, so it cannot tell accumulation from distribution.
  That is what the B-60 money-flow heatmap is already for — the two belong in the
  same view, one giving location, the other direction.

**Was blocked on [[#B-64]]** (built first, same day) — turnover share is a ratio over a denominator, and the
desk currently buckets symbols under three non-joining sector vocabularies. Pick
one first or the column silently means something different from the heatmap next
to it.

**Cost: low.** Same daily bars `money_flow.py` and the Sector Map already pull;
no new source, no auth. **Ships as a VIEW** — no entry/stop/target, not in
`SCANNERS`, never a confluence vote, on the same terms as B-60.


**BUILT 2026-09-09 — `tools/turnover_share.py` + 12 tests, live on Sector Map.**
Renders **directly beneath the money-flow grid**, and the pairing is load-bearing
rather than layout: delta-share is unsigned, CMF is signed, so each answers half
the question. Same aggregation choice as B-60 (turnover **summed** across a
sector, not averaged) for the same reason.

**Turnover is a PROXY here — `close x volume`, not exchange traded value.** It
differs from the bhavcopy figure by the gap between the close and the day's VWAP;
small for a liquid name, smaller across a sector, and named in `TURNOVER_NOTE`
which the grid returns so the page cannot drift from the module.

The tests pin the property that makes this a rotation column rather than a
turnover one: **a sector can LOSE share on a day its own turnover ROSE** (its
money went up 100 -> 150 while the market grew faster). A turnover column calls
that inflow; a share column calls it what it is. Also pinned: shares sum to 1,
deltas sum to 0, doubling every volume changes no share, and a heavyweight
outweighs a minnow.

> [!note] An independent corroboration nobody asked for
> First live run, 2026-09-09, nifty500, 500/501 symbols, 20 sectors:
> **Information Technology +2.73 pt** of turnover share. ScreeningMantis printed
> **+2.70 pt** for the same sector on the same date — computed over **a different
> universe (1,538 stocks), a different sector taxonomy (~45-50 labels) and
> probably true exchange turnover rather than our close x volume proxy.**
>
> Two independent implementations landing within 0.03 pt is worth more than
> either number: it says the measure is **robust to the taxonomy**, which was the
> open worry behind B-64. It says **nothing whatever about edge** — both are
> descriptions of the same session, and agreement between two thermometers is not
> evidence that the temperature predicts anything.
>
> The day's own reading remains the argument for the column: IT took that share
> **while NIFTY IT fell -3.24%**. Money in, price out.

**Still unmeasured, and shipping that way.** No entry/stop/target, not in
`SCANNERS`, never a confluence vote. The pre-registered event study above is
unrun and its expected result is still no lift.

**Prior: low, and stated before building.** Turnover concentration spikes on
news, index rebalances, block deals and expiry — none of which is rotation in the
sense a trader means. The measurement, if it is ever run:

> Rank sectors by Δ share (D and W); score forward 5/20-day sector-index returns
> of the top and bottom quintile against a random-sector null. **Expected: no
> lift.** The only interesting outcome is *W* showing something *D* does not,
> which would mean the measure needs a week to shed one-day event noise.

### B-63 · Shared column library for every table in the desk — **PROPOSED 2026-09-09, refined on request**

Owner's ask, verbatim in intent: bring ScreeningMantis's stock-table column
structure into our system and **use it for all the tabular displays we have across
the different pages**. Full 28-column header captured in
[[sources/ScreeningMantis-Price-Volume-Sector-Rotation-2026-09-09#1 — The PRICE & VOLUME column group (stock table)]].

This is two separable pieces of work and they should not be done in one commit.

#### ~~B-63a~~ · `tools/columns.py` — one definition per column — **BUILT 2026-09-09**

**The problem it fixes, counted before proposing anything:** `st.dataframe` is
called **43 times** across `tools/` (42 in `dashboard_app.py`), with
`column_config` built inline **122 times** and `help=` passed **121 times** — and
not one of those definitions is shared. The same quantity is therefore labelled,
formatted, coloured and explained differently on different pages, and a column
added to one table reaches no other. That is the actual blocker behind "use those
for all the tabular displays": there is nowhere to put a column once.

Shape:

```python
COLUMNS = {                      # id -> ColSpec
  "rvol":  ColSpec(label="Vol Spike", help="Today's volume / 20-day average. 2x = twice normal.",
                   fmt="%.1fx", width="small", tone="heat"),
  ...
}
def configure(df, *ids, **overrides) -> dict   # -> st.column_config for st.dataframe
```

Rules that make it worth building rather than a second way to do the same thing:

- **One id, one label, one tooltip, one format.** A caller picks ids; it may
  override width and label, never the definition of the number.
- **It emits config, it does not render.** `_paginated_df` stays the single
  render path and keeps its pagination; the 5 chart-icon LinkColumns already
  centralised for the Scanner Hub tables move in as ids rather than being
  rebuilt.
- ~~**`sector` is NOT an id until [[#B-64]] lands.**~~ B-64 landed first, so
  `sector` IS an id, and its tooltip names the canonical vocabulary and says
  Yahoo's is description rather than a join key.
- **Adoption is incremental and per-call-site.** A table not yet migrated keeps
  working. Do NOT convert all 43 in one pass — migrate the Scanner Hub summary +
  confluence tables first (they already have the richest config), then the rest
  as they are touched.

> [!warning] This does not turn cards into tables
> The Scanner Hub results grid is a **3-column card grid and stays one** — that
> decision is settled and the column library has nothing to say about it.
> Structure belongs in sort order and tags there. B-63 touches the **dataframes
> only**: summary/confluence tables, Sector Map, watchlist, portfolio, alerts,
> saved rotation, telegram signals, the Opportunity Hub tables.

**BUILT 2026-09-09 — `tools/columns.py` + 13 tests, 4 call sites migrated.**
33 column ids, 7 aliases, every one carrying a tooltip (a test asserts that: an
untooltipped column is how the old mess started).

**The rule is enforced, not documented.** `configure()` accepts `label` and
`width` overrides and **raises** on anything else — a column needing a different
format or tooltip needs its own id. `test_the_definition_may_not_be_overridden`
pins it.

**Two drifts closed on the first pass**, both of which were live in one function:
"Chg%" defined twice under `chg_pct` and `day_pct`, and "Turnover ₹Cr" defined
twice forty lines apart. `ALIASES` maps the second spelling onto the first, and
`configure()` keys its output by **the name the caller passed**, so a frame whose
column is still `day_pct` adopts the shared definition without being renamed.

**What the registry refuses to merge is as important as what it merges:**

- `rvol` (20-day mean) and `rvol_median5` (5-session median) stay **separate
  ids**, each saying so in its tooltip. Folding them would be a behaviour change
  dressed as a refactor.
- raw-rupee `turnover` is **not** aliased to `turnover_cr` — they differ by 1e7,
  and a wrong alias there mislabels by seven orders of magnitude. The trending
  lens now *renames* on conversion instead.

Migrated: the chart-icon family helper (so all ~7 of its call sites inherit at
once), Volume Shockers, the trending-movers lens, and the new turnover-share
grid. `configure_df()` leaves unknown columns to Streamlit, which is what makes
a half-migrated table safe — `src` in Volume Shockers renders untouched.

> [!note] Two things the live run caught that no unit test would
> **Stale module in a running Streamlit process.** `columns.py` is imported
> inside functions, so editing it did NOT take effect on a hot reload — the page
> kept rendering the old format and the first verification pass was quietly
> testing nothing. Restarting the server showed the change. **Verify a
> registry edit through a restarted process, or you are reading a cache.**
>
> **`turnover_cr` uses `format="localized"`, not printf.** The Styler that used
> to supply `{:,.0f}` is gone (one formatter, not two), and printf has no comma
> flag — at crore scale the thousands separator is worth more than a fixed
> decimal. Confirmed live: `6,196` / `6,812.9`. The cost is **ragged decimals**
> within the column, which is a real if minor ugliness and is the reason this is
> written down rather than left to be rediscovered.

> [!note] Targeted sweep, 2026-09-10 — and a correction to what "incomplete by design" meant
> The claim that adoption was "incomplete by design, 4 of 43" was challenged and
> did not survive contact with the numbers. **43 `st.dataframe` calls, but only
> 28 pass `column_config` at all**, and **15 call sites already reach the
> registry** — more than 4, because `_chart_family_colcfg` delegates and ~7
> tables inherit through it. Incremental adoption is sound; describing the
> remaining drift as *design* was not.
>
> What was left split in two, and only one half was drift.
>
> **Migrated — same quantity, different spelling, defined inline:** `% Chg` and
> `Price` (conviction board) → `chg_pct` / `close`; `Gap %` (gap-volume scan) →
> `gap_pct`; `LTP ₹` (pattern table) → `close`; `Price %`, `OI %`, `RVol` at
> **both** OI-momentum tables → new futures ids.
>
> **The clearest case for doing it:** the OI-momentum STOCK table carried a
> careful tooltip on `RVol`, and the INDEX table below rendered the same three
> columns with **none**. One definition now, so the explanation travels with the
> number instead of living at one of the two call sites.
>
> **New ids rather than reuse, deliberately.** Futures `RVol` is futures volume
> over a 5-session median — a **third** base after the equity 20-day mean and
> 5-session median. Mapping it onto either would silently redefine the number
> under the reader.
>
> **Declined, and kept declined by a test** (`NOT_ALIASED`): `Turnover ₹` is raw
> RUPEES while `turnover_cr` is crore — 1e7 apart, the exact trap the module
> docstring already warns about. The rest (`Pub Price ₹`, `Mkt Cap ₹`,
> `Basis %`, `Breadth %`, `Median %`, `Avg Mom %`, `# Stocks`, `Move %`) are
> each defined once and used once: **promoting a singleton creates a shared id
> nothing else asks for**, which is the opposite of the point.
>
> One visible consequence, recorded at the call site: adopting `close` for
> `LTP ₹` drops the ₹ glyph from those cells, because the format is part of the
> definition and every other table prints LTP without it.
>
> Registry: **46 ids, 15 aliases, 9 documented refusals.**

#### ~~B-63b~~ · The new columns themselves — **BUILT 2026-09-09**

Ordered by cost. Every one of them describes bars we already pull — **no new data
source, no auth, no vendor**.

| Column | What it needs | Note |
|---|---|---|
| **Gap (opening)** | open vs prior close | already computed in places, never a column |
| **Price header carries its as-of date** | pass the scan date into the label | one line; kills "is this today's close?" |
| **EMA cross age (10x20), in days** | a boolean cross series + distance-to-last-True | **the cheapest column here** — both halves already exist, see the note below |
| **Breakout DATE beside BO gain%** | the date is already known when the gain is computed | we print the gain and drop the date |
| **Pivot ZONE label** (`R1-PP`, `PP-S1`, `Near Pivot`) | **extract** CPR from `build_chart()` into a function, then bucket price against it | levels are computed but **trapped in a plotting function** — see the audit below |
| **Stage-2 as `x/7`** | count conditions instead of gating on them | keeps near-misses visible; see below |
| **W-Pivot** (weekly zone) | resample to weekly first — **no weekly pivot exists at all** | strictly more than D-Pivot, do it second |
| **RS rank walk T-30/T-15/T-5/T0** | a **universe-wide** RS rank (today's is scan-relative) + daily persistence for the whole universe | **by far the most expensive column here** — it is a data-collection project, not a column; see below |
| **Hist. price + Gain% since (user date)** | re-base the table on a date the reader picks | a different question from any our pages answer |
| **In-row watchlist toggle + Notes** | `st.data_editor` on the 1 table that should be editable | write-back; scope it to one table first |

#### What the code actually holds today (audited 2026-09-09, before proposing)

Checked against `tools/`, because two of the columns above were nearly filed as
"we already have this" when we do not, and one as missing when we do.

| Column | Reality in this repo |
|---|---|
| Price / 1D% / Ticker / Sector / Cap | `data_source` OHLCV + `nse_universe`. Fine. |
| RSI | `scanner_templates._rsi_series`, Wilder n=14. One implementation. Fine. |
| 52W high | `df["high"].tail(252).max()`. Fine. |
| **Vol spike** | **four different definitions live at once** — see below |
| % from 20EMA | computed inline at `scanner_templates.py:4340`, never exposed |
| EMA spans in use | 10, 20, **21**, 50, 200 — `scan_pullback_to_ema` uses **21**, so it and a "% from 20EMA" column disagree by construction |
| **EMA cross age** | **absent as a pair (10x20 is computed nowhere), but neither half is new** — cross detection and an age helper both exist. See below |
| **D-Pivot** | CPR pivot/BC/TC/**R1/S1** ARE computed — `dashboard_app.py:3391-3401` — but **inside `build_chart()`, as plot traces**. Daily only, not a function, no zone label |
| **W-Pivot** | **absent** |
| "pivot" in `scanner_templates.py` | **swing** pivots (`pivot_len`), NOT floor pivots. `scan_near_pivot` is swing-high proximity. Reads like coverage; is not |
| **RS rank** | **EXISTS** — `_rs_raw` + `_finalize_relative_strength` (`scanner_templates.py:76-111`) produce a 0-100 percentile, also worth 25% of the blended score. But its denominator is **the scan's matched set**, and it is **not persisted**. See the correction below |
| **Stage 2** | `scan_stage2_uptrend` is a **hard gate** returning `None` on any failed leg — there is no `x/7` to surface |

> [!warning] "Vol Spike" already means four different numbers here
> This is B-63a's case, made by the codebase rather than by argument. The same
> column name is currently computed as:
>
> | Base | Where |
> |---|---|
> | 20-day **mean** | `scanner_templates.py:4336` |
> | 50-day **mean** | `scanner_templates.py:1770` |
> | 5-day / 20-day **ratio of means** | `scan_pullback_to_ema` |
> | **5-session MEDIAN** | `nse_oi_momentum.py:100` (`VOLUME_BASELINE_SESSIONS = 5`) |
>
> Four windows, two central tendencies, zero shared definition — and
> ScreeningMantis's **9-day** base would have been a fifth had it been copied.
> A reader comparing "2.4x" on one page against "2.4x" on another is comparing
> nothing. **`rvol` is therefore the first id to land in `columns.py`**, and the
> migration must state which base wins (default 20-day mean) and leave the
> 5-session median where it is with its own id — `nse_oi_momentum` uses a median
> deliberately, on intraday-ish data, and collapsing the two would be a silent
> behaviour change dressed as a refactor.

> [!note] EMA cross age is assembly, not invention — copy `_percentr_exhaustion`
> The 10x20 pair is computed nowhere (`_ema_series` is called with 10 only once,
> on **weekly** closes at `scanner_templates.py:3342`), and the nearest thing —
> `scanner_templates.py:6546` "golden-cross zone" — is **SMA20 > SMA50**, a
> *state*, not an event, on SMAs not EMAs. So the column is genuinely absent.
>
> But both halves of it are already written and should be reused rather than
> re-derived:
>
> - **Cross detection**, the `prev <= x, now > x` idiom, appears at
>   `scanner_templates.py:6775-6783` (RSI/VWMA vs mid), `hm_indicator.js:194`,
>   `adx_di.js:94` (+DI/-DI) and `evwma_vwap_macd.js:156` (MACD/signal).
> - **Age of an event** is `_bars_ago` inside `_percentr_exhaustion`
>   (`scanner_templates.py:2042`): a boolean event series, then the distance from
>   the last `True` to the end. `bars_since` in `block_deal_intel.py:311` and
>   `bars_ago` in `chart_server.py:1025` are the same pattern surfaced in the UI,
>   so **the desk already has a house style for printing "N days ago"** — follow
>   it rather than inventing a second phrasing.
>
> **One difference to get right:** `_percentr_exhaustion` searches only its
> `lookback` window (3 bars) and returns `None` outside it. The cross-age column
> needs an **unbounded** search back, and must distinguish *"crossed more than N
> bars ago"* from *"never crossed in the loaded history"* — their UI leaves the
> cell **blank** for the second case, and a blank that silently means "we only
> looked back 3 bars" would be a lie. State the search depth in the tooltip.

> [!warning] Correction — RS rank exists; the sparkline still does not follow
> An earlier pass on this page said no RS-rank function exists. **Wrong.**
> `scanner_templates.py:76-111`:
>
> - `_weighted_trailing_return` — IBD-style weighted trailing return,
>   **63/126/189/252 days at 0.4/0.2/0.2/0.2**, degrading on short history.
> - `_rs_raw` — that return **minus the benchmark's** when `run_scanner` set one
>   (excess return vs Nifty), else absolute.
> - `_finalize_relative_strength` — ranks `rs_raw` across the results into
>   **`rs_rank`, 0-100**, and blends it in at **25%** of `score` for scanners
>   exposing `score_base`.
>
> **Two things block the T-30 -> T0 walk, and neither is "we don't compute RS".**
>
> **1. The denominator moves.** `rs_rank` is a percentile **across that scan's
> matched set** — deliberately so ("RS rank is by definition relative to the rest
> of the scan"). A rank of 90 among 12 hits and a rank of 90 among 400 are not
> the same statement, so **four such ranks in a row are not a trend line** — the
> sparkline would be plotting a changing population as if it were a moving stock.
> A universe-wide rank (all ~1,500 names, fixed denominator, computed daily
> whether or not the name is a hit) is a **different measure** that would have to
> be added beside the existing one, not a persistence change.
>
> **2. Only survivors are stored, and thinly.** Checked in
> `tools/trading_bramha.db` on 2026-09-09: `daily_opportunities` has **no
> `rs_rank` column** at all (it stores `momentum`), the frozen
> `daily_opportunity_cards` JSON carries `rs_rank` in **91 of 204** cards
> (scanners that emit `rs_raw`), and there are **14 run dates** total, irregular,
> spanning 2026-08-24..2026-09-07 in the cards table with row counts swinging
> 5-100. T-30/T-15/T-5 need a **per-symbol daily series for the whole universe**.
> What exists is a sparse shortlist of that day's winners — so a name that fell
> out of the shortlist would render as a **gap, not a decline**, which is exactly
> backwards from what the column is for. **Survivorship, printed as a sparkline.**
>
> **Consequence for B-63b:** this column is not "cheap, no new data source" like
> the rest. It is a universe-wide RS rank plus a daily snapshot table, and it
> should be split out and scheduled on its own rather than shipped with the
> column library. Everything else in B-63b stands.

**BUILT 2026-09-09 — `tools/row_metrics.py` + 21 tests, live on the Watchlist.**
All nine shipped — seven on 2026-09-09 and the note editor in a follow-up commit
the same day. The one item genuinely declined is Stage-2 `x/7`, because it
already exists.

The Watchlist is the mount point because it **already fetches full OHLCV per
symbol** for its Minervini/TechnoFunda scores — so the technical row costs no new
fetch. Columns now on it: `LTP (09 Sep)` (dated header), `Chg%`, `Gap%`,
`EMA cross (d)`, `D-Pivot`, `W-Pivot`, `52W high %`, `BO gain%`, `BO date`,
`Minervini`, `TechnoFunda`, plus `Hist. price` / `Gain% since` when a re-base
date is picked. All config comes from [[#B-63a]].

**Two items were NOT built, and the reason is the same in both cases — they
already existed or should not exist twice:**

- **Stage 2 as `x/7`.** `screener_pipeline.score_minervini` already returns
  `(0-8, conditions)` and the Watchlist has rendered it as **"x/8" all along**.
  The teardown's finding was real but narrower than it read: it is the SCANNER
  (`scan_stage2_uptrend`) that is a hard gate, not the desk. Surfacing the
  existing score is the fix; a second Stage-2 scorer would be one idea with two
  implementations, drifting.
- ~~**In-row watchlist toggle + Notes.**~~ **BUILT 2026-09-09**, in its own
  commit as promised. `st.data_editor` with **every computed column disabled**,
  so the table is a working surface for the one field that is genuinely yours
  without becoming a place where a stray keystroke rewrites a price. The
  watchlist *toggle* was not added: the page already has an add form and
  row-select → ♥, and a third way to do it is not a feature.

  **The trap this avoided, pinned by a test:** the obvious implementation is
  `add_watchlist_symbol(sym, notes)` — which is an `INSERT OR REPLACE` and would
  silently **reset `added_date` to today**, rewriting when you started watching
  the name. `portfolio_db.update_watchlist_notes()` updates the note only, and
  returns **0 rather than inserting** for a symbol no longer on the list, so a
  stale edit posted against a removed name cannot resurrect it (the page reports
  those as skipped).

  **Verified by actually editing a cell in the browser**, not just by unit test:
  typed a note into MUKKA's row, and confirmed in sqlite that the note changed
  **and `added_date` stayed 2026-09-02**. Test data restored afterwards.

**Design decisions that are load-bearing, each pinned by a test:**

- **`ema_cross_age` returns `searched` alongside `age`.** `age=None` means "no
  cross within N bars", never "no cross ever" — the borrowed `_bars_ago` idiom
  windows its search and returns None outside it, and a blank cell that silently
  meant "we only looked back three bars" would be a lie. Rendered **signed**
  (`+15` crossed up 15 sessions ago, `−38` crossed down 38 ago) because the
  direction is the reading and `"%d days"` printed the absurd `"1 days"`.
- **`breakout()` uses the plainest definition available** — the last close above
  its prior 20-bar high — deliberately NOT a scanner's pattern, or the column
  would mean whichever scanner it borrowed from. Its gain **can be negative**,
  which is the point: a faded breakout is exactly what the pair reveals.
- **`since()` refuses a date before the history starts** rather than anchoring on
  the earliest available bar, which would quietly turn "since 1 Jan" into "since
  whenever this frame happens to begin" — differently per symbol.
- **`pivot_levels()` is the arithmetic extracted from `build_chart()`**, not a
  reimplementation, and `weekly_frame()` feeds it for W-Pivot. It returns None on
  a positional index rather than resampling nonsense.

**First live read, and it makes the case for the time-derivative columns better
than the argument did.** SHAKTIPUMP: `EMA cross −38`, `Near S1`, `52W high
−48.72%`, **`BO gain −20.71%` dated `2026-06-24`**. A breakout column showing
only the gain would have printed a number; showing the date reveals a break that
is nearly three months old and now 20% underwater. RELIANCE via the CLI reads the
same way: cross down 1 session ago, S1 daily AND weekly, last breakout 2026-05-04
now −12.18%.

> [!warning] The empty rows were not missing data — they were a SCAN filter
> Three of eight watchlist rows (AKI, MARALOVER, PRAENG) rendered blank, and the
> obvious reading — "yfinance has nothing for them" — was wrong. All three have
> **297 bars of perfectly good history**. They were being dropped by the
> **liquidity floor**, `MIN_TURNOVER = ₹1 cr` (`screener_pipeline.py:103`,
> mirrored in `volume_fetcher.py:50`):
>
> | Symbol | Bars | 10d avg turnover | vs ₹1 cr floor |
> |---|---|---|---|
> | AKI | 297 | ₹0.712 cr | below |
> | MARALOVER | 297 | ₹0.368 cr | below |
> | PRAENG | 297 | ₹0.500 cr | below |
> | SARVESHWAR | 299 | ₹1.099 cr | clears it by 10% |
>
> The Watchlist called `cached_fetch_ohlcv(symbol)` with the default
> `enforce_liquidity=True`. **That floor belongs to SCANNING** — it keeps
> untradeable names out of a 2,000-symbol sweep — and a watchlist is curated by
> hand: the user typed those symbols. This is the identical failure that
> function's own docstring records for CENTUM: *"the same app refusing to open a
> door it just pointed at."* Fixed the same way, with `enforce_liquidity=False`.
>
> **The illiquidity is now shown rather than hidden:** a `Turnover ₹Cr` column
> per row, plus a caption naming which rows sit under the floor and why that
> matters (a level on a name trading a few lakh a day is worth less than the
> same level on a liquid one, and the position may be hard to exit). The `None`
> rendering in empty numeric cells disappeared with the cause.
>
> **Swept 2026-09-09.** All 20 `cached_fetch_ohlcv` call sites audited against
> one rule: **the floor is a SCAN filter — keep it ON where the symbol arrived
> from a sweep, turn it OFF wherever the symbol was NAMED.**
>
> **Seven switched to `enforce_liquidity=False`:**
>
> | Call site | Why the floor was wrong there |
> |---|---|
> | Portfolio valuation | **You already OWN it** — the P&L silently omitted the holding |
> | Portfolio positions table | same |
> | Alert evaluation | an alert the user SET BY NAME could never fire, and **an alert that cannot trigger looks exactly like one that has not triggered** |
> | Watchlist | the original find |
> | Watchlist quick-add prefill | prices a name the user is adding by hand |
> | Peer-comparison technical columns | peers are named by the comparison; a thin peer became a hole that read as missing data |
> | Bulk/block deal price context | **the floor was reporting thin NSE names as "not NSE-listed"** — a different and false statement, and bulk deals happen in illiquid scrips more often than liquid ones, so it bit hardest exactly where that page looks |
> | Institutional footprint | a symbol the user typed |
>
> **Ten verified as correctly floored** and left alone: `_scanner_fetch_fn` and
> the scanner prefetch fallback, the gap/volume universe scan, the Chartink
> conviction scoring, the price-legs backtest (a backtest must not include names
> you could not have traded), the funnel context builder, and the three
> Overall-Rating calls plus the levels fetch that run on hits which had already
> passed the floor — moot there.
>
> The rule and the audit are now recorded in `cached_fetch_ohlcv`'s own
> docstring, so the next reader learns it once rather than at seven call sites.
>
> **Not changed: the default stays `True`.** Scanning is the higher-volume
> caller and the floor is right for it; flipping the default would silently
> re-admit untradeable names to every sweep. The bug was never the default — it
> was that by-name callers inherited it without saying so.

#### RS-rank walk — **BUILT 2026-09-09**, `tools/rs_walk.py` + 23 tests

**The blocker that was real, and the one that was not.**

*Real:* the existing `rs_rank` is a percentile **across a scan's matched set**,
so four in a row plot a changing population. `rs_walk` computes a
**universe-wide** rank — one fixed denominator, every constituent with history,
whether or not a scanner fired. It sits BESIDE the scan-relative rank; both are
valid answers to different questions.

*Not real:* this page previously said the walk needed a daily snapshot table
filled in over 30 sessions. **It did not.** `rs_raw` as of a past date is a pure
function of the price series up to that date, so the whole walk was computable
the same afternoon from history the desk already downloads. **The persistence is
a cache, not a prerequisite** — that assumption is what kept this filed as a
"data-collection project" instead of a column.

**The design fault caught only by running it.** The first version shipped with
the column **empty on every row**: it ranked the nifty500, and a personal
watchlist is made of exactly the small names that are *not* constituents — **7 of
8 here**. Fixed with `rank_against()`: a non-constituent is placed **into** the
universe's distribution without **joining** it. Membership is not a prerequisite
for asking how a return compares; the index is the *yardstick*. Guests never
enter the denominator (or the yardstick would depend on whose watchlist was
open) and are marked with a trailing `*`. Four tests pin that.

**First live read, 508 names ranked (500 constituents + 8 guests):**

| Symbol | T-30 → T-15 → T-5 → T0 | reading |
|---|---|---|
| AKI | 0 → 0 → 1 → 80 | a month on the floor, then a violent turn |
| SARVESHWAR | 1 → 2 → 3 → 31 | waking up from the bottom |
| CENTUM | 92 → 85 → 75 → 94 | dipped and recovered |
| SHAKTIPUMP | 4 → 5 → 4 → 6 | persistently weak — and its other columns agree (EMA cross −38, −48.7% from the 52w high) |

That last row is the argument for the whole B-63b set: four independent columns
telling one consistent story about a name, none of which this desk could show
before today.

**Extended to the Scanner Hub 2026-09-09.** The column now sits on the pipeline
**summary** table (each scanner's top symbol) and the **confluence** table (one
row per name firing in 2+ scanners). Both READ the stored grid and never compute
— ranking the universe takes a minute and a table render must not pay it. The
Hub carries its own button to rank *that run's* names as guests, because a
full-market scan surfaces names outside the nifty500 by design and a column
blank for half its rows is not much of a column.

The pairing earns its place immediately: **ACMESOLAR** fired in **12 scanners**
and its walk reads **92 → 94 → 35 → 36**. Confluence says how many detectors
agree; the walk says the market stopped agreeing a fortnight ago. Neither is
visible from the other.

> [!warning] Two bugs the live run caught that the unit tests could not
> **1. The `*` meant nothing.** `in_universe` was computed but never STORED, so
> every row read back as a guest and the "ranked against, not within" asterisk
> appeared on constituents too — BAJAJ-AUTO, a nifty500 member, wore one. Not a
> blank, a *wrong mark*, which is worse. Column added by migration, existing
> rows backfilled from the constituent list, and a test now pins the round-trip.
>
> **2. Two pages were deleting each other's guests.** `save_rs_walk` replaced
> the whole run_date, so a Scanner-Hub compute dropped the Watchlist's guests
> and vice versa — the column silently went blank on whichever page was not
> looked at last. Now a **merge** (upsert per symbol), which is safe because
> every row inside one run_date comes from the same day's prices. Verified live:
> 558 rows = 500 constituents + 58 guests, both pages' sets intact.

**Still survivorship-tinted, and it says so.** T-30 ranks *today's* universe as
it stood 30 sessions ago — prices point-in-time, membership present-day.
`SURVIVORSHIP_NOTE` travels with the grid so the page cannot drift from the
module, and it is why this is a reading, not a signal.

**Nothing here is measured, and there is nothing to measure:** these report
conditions already computed elsewhere. No scanner registration, no confluence
vote, no entry/stop/target.

**`x/7` instead of a gate is the one with a consequence worth stating.** Turning a
boolean into a count of conditions met changes what the table *hides*: their own
top-20 mixes 7/7, 3/7 and 0/7 rows, and a hard gate would have dropped most of
them. That is a deliberate widening of what reaches the eye, in a desk whose
[[analyses/Open-Backlog#B-19]] finding is that most single-condition scanners have
no edge after costs — so it belongs as a **column**, not as a relaxed filter.

**Deliberately NOT copied:** their **9-day** RVOL base. Ours is 20-day; a 9-day
mean reacts about twice as fast and lets one prior spike deflate the ratio for a
fortnight. Keep 20 and keep the numbers comparable to our own history.

**No measurement owed.** These columns describe state that is already computed —
they make no claim of edge, register no scanner and cast no confluence vote. The
one thing to watch is the opposite failure: **28 columns is a lot of table**, and
the reason theirs stays legible is that every header carries an `i` tooltip. The
tooltip is not decoration here; it is the thing that makes the width affordable,
which is why B-63a puts `help=` in the definition rather than at the call site.

### ~~B-64~~ · Pick the canonical sector vocabulary — **BUILT 2026-09-09**

Fell out of the B-63 column audit. "Sector" looked like the one column we
certainly had. We have it **three times, in three vocabularies that do not join**,
and the one actually persisted is the one nothing else uses.

| # | Vocabulary | Size | Where it lives | What it looks like |
|---|---|---|---|---|
| 1 | **NSE macro** (constituent CSV) | **20** labels on nifty500, **22** on niftytotalmarket | `nse_universe`, `NSE_SECTOR_INDEX_MAP` -> 11 indices | "Capital Goods", "Oil Gas & Consumable Fuels" |
| 2 | **screener.in Industry** | ~130 values, **97** mapped | `sector_rotation.SECTOR_INDEX_MAP` | fine-grained, needs a manual export |
| 3 | **Yahoo / yfinance** | 11 sectors + ~150 industries | **the only one PERSISTED** — `daily_opportunities.sector` / `.industry` | "Healthcare" / "Drug Manufacturers - Specialty & Generic" |

The damning number is already in our own code comment, measured 2026-08-01:
**0 of NSE's 20 labels appear among screener.in's 97 keys** — "the two share
**nothing**", which is why `nse_universe` had to define a *second* map rather than
extend the first. Nobody has since asked what happens when a third one is stored.

**Two traps found while checking, both worth more than the tidy-up:**

- **The field called `industry` holds a SECTOR.** `nse_universe.fetch_constituents`
  emits `{"industry": ...}` from the CSV's `Industry` column, but the values are
  NSE's 20 **macro sector** labels. `money_flow.sector_grid` groups on
  `r["industry"]` and — correctly — calls the result `sector`. The name lies at
  the boundary; a reader wiring a genuinely industry-level view off that key will
  get sectors and no error.
- **The label set depends on the universe.** nifty500 yields 20 labels,
  niftytotalmarket 22 (`Forest Materials`, `Utilities` appear). So even *within*
  vocabulary 1, two runs can disagree about what sectors exist.

**Why this blocks [[#B-62]].** Turnover share is `sector_turnover / total_turnover`
— a ratio whose denominator is only meaningful if every symbol is bucketed once,
under one taxonomy, over a stable universe. Today B-60's money-flow grid buckets
by **NSE macro (20)** while the stored opportunity rows carry **Yahoo (11/150)**,
so the two sector views on the desk cannot be laid side by side, and a Δ-share
column computed against either would silently mean something different from the
heatmap beside it. **Ship B-62 after this, not before.**

It also constrains [[#B-63a]]: `sector` cannot be an id in `columns.py` until
there is one definition for it to point at. Anything else just standardises the
*label* over three different meanings, which is worse than the mess it replaces —
it hides it.

**The decision, stated so it can be argued with:** adopt **NSE macro (20/22)** as
canonical. It is free, refreshed from NSE itself with a 7-day cache, already
covers 501/754 constituents, and is the only one with an honest index mapping
(11 indices, 4 labels **deliberately unmapped** rather than guessed — Services,
Diversified, Textiles, Media, 5.4% of constituents, left "unscored"). Yahoo's is
richer and free but is a US-shaped taxonomy applied to Indian names; screener.in's
is the most granular and the least reachable (manual authenticated export).

Consequences to accept, not paper over:

- **ScreeningMantis's ~45-50 labels do not map onto 20.** "Auto Components",
  "Refineries & Lubricants", "Jewellery & Watches" are Yahoo-*industry*-grained.
  A comparison against their sector table is therefore **not** cell-to-cell, and
  any note that implies otherwise is wrong.
- Yahoo sector/industry **stays stored** on opportunity rows — it is useful
  description. It just stops being a join key. One canonical column, additional
  labels as attributes.
- The `industry`-holding-sectors misnomer gets renamed at the same time, or the
  next person repeats this audit.

Cost: small — a mapping table plus a rename, no new data source. Value: it is a
prerequisite for two other items, and prerequisites bought late are bought twice.

**BUILT 2026-09-09 — `tools/sectors.py` + 11 tests.** NSE macro adopted as
canonical, exactly as proposed above. What the build added beyond the decision:

- **`from_yahoo(sector, industry)` takes the industry too**, because four Yahoo
  sectors are irreducibly ambiguous against NSE's vocabulary (Industrials, Basic
  Materials, Consumer Cyclical, Utilities). Those four have **no sector-level
  fallback at all** — a test asserts their absence — so an unresolvable pair
  returns **None**, never a nearest guess. Two industry overrides earn their keep
  on their own: Yahoo files **gas distribution under Utilities** where NSE files
  it under Oil Gas & Consumable Fuels, and **Solar under Technology** where NSE
  files it under Capital Goods.
- **Every mapping target is asserted to be in `CANONICAL`**, so a typo in a table
  fails a test rather than inventing a 23rd sector at runtime.
- **`symbol_map()` is the honest-name replacement** for reaching into
  `nse_universe.fetch_constituents()` and reading `r["industry"]` — the key whose
  values are SECTORS. New callers use `symbol_map`; the misnamed key is left
  untouched rather than renamed under the existing readers.

**Live coverage, measured not assumed:** nifty500 gives **501/501 symbols across
20 labels, 100% canonical**. Against the Yahoo pairs actually stored in
`daily_opportunities`: **447 of 453 resolve (98.7%)**, and all six failures are
rows whose stored sector is the empty string — bad data, not an unmapped pair.



## Outcome (fill in later)

## Related Pages

- [[analyses/Open-Backlog-2026-08-02]] — the snapshot this supersedes
- [[analyses/Backtest-Harness]] — where most of P1 lands
- [[analyses/OI-Momentum-Gap-Audit]] — source of B-19b and B-23
- [[analyses/Dashboard-UI-Roadmap]] — the M1–M4 spine
