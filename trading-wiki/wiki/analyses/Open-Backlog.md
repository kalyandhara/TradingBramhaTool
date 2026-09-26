---
title: "Open Backlog — the living index"
category: analysis
tags: [backlog, index, roadmap, open-items, measurement-debt]
timeframe: milestone-plan
created: 2026-08-07
updated: 2026-09-20
sources: 0
related:
  - analyses/PCR-Sign-Convention-Pre-Registration.md
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
| **Measured 2026-09-10** | **B-66** (`sentiment_factor_edge.py`) — **the whole sentiment index measured, and NOTHING discriminates.** Tercile spread on NIFTY fwd @5d: **A/D (proxy) −0.03% p=0.855 · Sector −0.01% p=0.908 (19y, n=4,649) · Regime SMA200 −0.08% p=0.829 (18y, n=4,452) · COMPOSITE −0.12% p=0.703**, every rho ≈ 0. The two deep arms span 2008/2013/2020/2022 and land on zero, so this is a measurement rather than a shortage of one. **Kills the re-weighting proposal [[#B-65r]] left live: there is no beneficiary** — every candidate scored the same zero. Pre-registered consequence applies: **the index is a descriptive display, not a forecast, and the fix is to say so on the page** — nothing deleted, no weight changed. Two of four factors now rest on the same substitution B-65r caught (regime-for-signals: **B-32's finding is about SIGNAL performance in a regime, not INDEX returns**). Noted but NOT claimed: high-sentiment days win more often (58.0 vs 51.0) while earning less — a fat left tail, unregistered and unscored. Bands are near-vestigial: 65 of 733 days hit either extreme |
| **Measured 2026-09-10** | **B-65r** (`pmax_nifty_edge.py`) — **the sentiment factor's own claim, and it FAILS.** The factor scores 20 for up / 0 for down, so the claim is DISCRIMINATION and the statistic is a spread. **1H (5,057 bars, the yfinance ceiling): −0.30% at ~5d, p=0.306.** The pre-registered power escape — the same spread on **DAILY NIFTY over 19 years (2007→2026, 4,658 bars, four regimes)** — **also fails: −0.58%, p=0.488.** So not a data problem: on the nearby question the data exists and the answer is no. All four spreads lean the wrong way (down-state beat up-state) and **none is significant**, which is the profile of no information, not of a contra-signal. Resolves the pre-registered disagreement with **B-32**: that measured how SIGNALS perform conditional on regime, this measures how the INDEX performs conditional on trend state — different claims, both can be true, and the factor borrows credibility from the first while making the second. **Nothing deleted**; re-weighting is now a live proposal in its own entry, complicated by the other three factors being unmeasured too |
| **Measured 2026-09-10** | **B-65** (`pmax_edge.py`) — **PMax scored for the first time, and it FAILS.** Flip **−0.55% (p=0.511, n=1,538)**; **state (dir=1) −0.19% on 129,761 bars** — *below* the unconditional baseline in a bull window stacked in its favour, so the pre-registered confound did not save it. Completes a four-detector convergence: Renko −1.01 / STAI-only −1.00 / PSAR-only −0.77 / **PMax −0.55**, no shared code, one mechanism (an up-flip re-enters only after price gave part of the run back), PMax shallowest exactly as its rarer/slower cadence predicted. Only B-43r is individually significant. **Does not retire `W_PMAX_1H`** (a STATE on NIFTY 1H — a different claim) but removes the presumption it is safe, and makes the 1H measurement live. Nothing removed on a null |
| **Measured 2026-09-10** | **B-59r** (`psar_stai_edge.py`, 460 names) — **NEITHER twin carries information.** AGREE (n=4,068) **+0.16% p=0.820** ≈ market; **PSAR-ONLY −0.77% (p=0.053, n=8,576)**; **STAI-ONLY −1.00% (p=0.150, n=1,909)**. Pre-registered "both null" row: trim falls back to cost — keep STAI, PSAR stays an overlay, **nothing deleted**. The shape is the finding: agreement pays the market, disagreement loses in BOTH directions, and −0.77/−1.00% sit beside **B-43r's −1.01% for the Renko flip** — a fourth detector landing on the same mechanism (an up-flip re-enters after price has given back part of a run). Neither p clears 0.05, so convergence, not proof. Leaves **PMax as the only one of the three never scored**, while carrying 20% of the sentiment index |
| **Counted 2026-09-10 (v2, chance-corrected)** | **B-59** re-run with a rotation null after the owner asked whether PMax can be sunset. Raw coverage was mostly base rate; corrected, **PSAR↔STAI agree far above chance (+34.2 lift at ±3) while PSAR↔PMax agree BELOW chance at every tolerance (−12.4 at ±3)**. So: **no, PMax cannot be sunset in favour of PSAR** — it is the least-alike pair, and PMax additionally carries 20% of the sentiment score, a `market_verdict` factor and the chart's trade-state panel. The real redundancy is PSAR↔STAI, and choosing between those two is an edge question nobody has measured. B-46 stands, on better grounds |
| **Counted 2026-09-10** | **B-59 overlap check** (`psar_overlap.js`, 460 names / 322,608 bars) — **PSAR is a SUPERSET, not a subset**: 28,582 flips against PMax 3,396 and STAI 13,050 (8.4× / 2.2×), 68.9% of them uncovered at ±3 bars, while PSAR itself covers 92% of STAI and 70% of PMax at ±10. B-46's zero-unique-cell objection does NOT survive — but it is replaced by a sharper one, since PSAR's whole content is its extra flips. Gate did not close; an edge test on the UNIQUE cells specifically is now owed. PSAR stays a drawn overlay meanwhile |
| **Measured 2026-09-10** | **B-58** (`quasimodo_study.py`) — **INCONCLUSIVE, UNDERPOWERED**: 53 QM zone entries across 356 names / 3 years against a pre-registered floor of 200, and too few for a rotation p to be computable at all. Not a null; the pattern is too rare to measure to this desk's bar on daily bars in one market. QM stays geometry, PIPELINE_EXCLUDED. Three process catches recorded: the equivalence check aborted on SCOPE (355/355 once windowed), the pre-registered baseline could not contain its own signal (a QM's left shoulder is by definition a broken low), and the HARNESS clause fired but was resolved as uninformative when the panel reproduced B-43's null at −0.05% |
| **Corrected 2026-09-10 (re-verify)** | **B-3** and **B-19b** bodies said "absent" for four weeks after the ledger closed them; **B-10** is down to one symbol (`BSE`), not four; **B-17** re-verified still absent and now covers two shipped OBV surfaces |
| **Still open** | ~~*superseded — see [[#THE OPEN ROADMAP — refined 2026-09-17]], which is the current list. B-10 and B-27 in this row have since closed.*~~ B-4/B-12, B-6, B-8, B-9, B-10, B-13, B-15, B-17, B-21b, B-26, B-27, B-30, B-31, B-35, B-37, B-28r — **all re-verified open 2026-09-10** except B-10, which shrank to a single symbol. Spot checks: no AVWAP anchor UI (`avwap` appears in `scanner_templates.py` only), no Volume-Profile 80% rule anywhere in `session_volume_profile.js` / `volume_profile.js`, and `sentiment_index.py` still carries **four** weighted factors (30/25/25/20) with the PCR factor 5 a docstring line only — even though `pcr.py` is now consumed by `dashboard_app.py` in three other places, so B-22 is wiring, not a build — **B-22 and B-20 both actioned 2026-09-11, see their rows; `sentiment_index.py` now carries five factors at 25/20/20/15/20** |
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

## Re-verification 2026-09-19

**Read this section, then the roadmap below it. Everything further down the page
is history.** The three tier tables in the next section are the only current
list of what is open; they have been corrected in place by this pass and each
correction is dated in the row itself.

**What this pass did.** Every open item in the roadmap below was re-read against
the **code**, not against the previous pass — the method the 2026-08-27,
2026-09-10 and 2026-09-11 passes used. `tools/claims_lint.py` was run first:
CHECK 0 (state labels contradicted by a measurement), CHECK 0b (studies missing
from the index) and CHECK 3 (counts disagreeing with the registry) are all
**clean**, which is the first time all three have been. CHECK 0c is not, and
that became [[#B-99]].

### What had moved

| Item | The page said | The code says | 
|---|---|---|
| **B-93 / PR-1** | open, "the only pattern-surface item that currently misleads" | **shipped 2026-09-17** — three commits, the same day this table was refined |
| **B-93 / PR-2** | open, "only 7 of 31 firing scanners emit entry/stop/target" | **shipped 2026-09-17** as `scanner_plans.py`, and the census **corrected the ratio to 14 of 45** — so the row was stale in its build status *and* in its number |
| **B-17** | open BUILD item | **closed 2026-09-11**, and the 2026-09-11 pass recorded that closure **twice** |
| **B-37** | "volume share-card", not started | **scaffold built** — renderer, canvas, deriving factory and invariant verifier all exist; three wiring steps left, named in the file's own header |
| **B-87r** | "ongoing, one page per session" | **96 lines of headroom** on the 13,900-line ratchet, and the statement ratchet raised 320 → 324 rather than lowered |
| **B-59r2** | MEASURABLE NOW | **contested** — struck as discharged on 2026-09-11, re-raised here on 2026-09-17, and the two counts do not match |

### What was checked and is still accurately open

`ichimoku` appears only in a `psar.js` comment (**B-46**); no TPO source outside
the vendored bundle (**B-47**); nothing matches `cumulative_volume_delta`/`cvd`
(**B-48**); no `opening_range`, `year_open` or calendar anchor anywhere
(**B-98**); `pivot_levels()` still has exactly **two** call sites, `pivot_d` and
`pivot_w` (**B-96**, confirming the grep this page already claimed); no pivot
agreement study exists (**B-97**); `mabias` ships in `chart_dashboard.html` and
is scored nowhere (**B-89**); no VWAP+EMA agreement state (**B-90**);
`participant` appears only in `gamma_exposure.py`, an unrelated use (**B-95**);
`max_pain` and `oi_walls` both exist in `option_chain.py`, so **B-94** is a run
and a diff exactly as claimed; `MIN_PRICE_PCT = 0.5` unchanged (**B-26**);
`veto_critical: bool = True` unchanged (**B-34r2**); `tools/sbc_app.py` still
present (**B-84r**).

### The finding, and it is not the same one as last time

Previous passes explained drift two ways: *"an item is only re-read when it is
worked"* (2026-09-10) and *"ranked tables that paraphrase item bodies are a
second source of truth"* (2026-09-11). **Neither explains this pass.** Three of
the six items that moved — B-93/PR-1, B-93/PR-2, B-59r2 — were listed as open by
a table **refined on the same day the work shipped or the day after the debt was
struck**. The drift is no longer in the old unworked items; it is in the newest
table, written by the session that was doing the work.

**The rule that produces it:** a refinement pass reads the *page* to build its
summary, and the page has not yet been updated by the work that session is
simultaneously committing. The summary is therefore written against a snapshot
that is already stale by the time it is saved. **A roadmap table written in the
same session as the work it summarises will be wrong about that work** — which
argues for writing the tier tables from `git log` and grep at the *start* of a
session, never from the page at the end of one.

### Ranked, after the corrections

| Rank | Item | Why |
|---|---|---|
| ~~1~~ | ~~**B-97**~~ | **RUN 2026-09-19 → TWO DIFFERENT READINGS.** It did its job as a gate: B-96 is re-scoped, not unblocked |
| ~~2~~ | ~~**B-94**~~ | **RUN 2026-09-19 → SPLIT.** Max pain exact, call wall exact once the definition matches, put wall unsupported. Raised **B-100** against our own `oi_walls` |
| ~~3~~ | ~~**B-87r**~~ | **FIRST EXTRACTION DONE 2026-09-19** — 696 lines out, ceilings lowered, and the registry makes the next one cheaper than this one. Headroom 96 → 42 lines *below* a ceiling that is itself 750 lower |
| 4 | **B-99** | four measurements already paid for and not written down |
| 5 | **B-96** | **no longer "composed of two built things"** — B-97 turned it into a presentation decision (govern, or print the agreement). Rank unchanged, size is not |
| — | **B-59r2** | re-read the two counts before running anything; it may already be done |

Nothing was closed by this pass that the code did not show closed, and nothing
was invented.


## THE OPEN ROADMAP — refined 2026-09-17, corrected 2026-09-19

**Why this section exists.** The status table above is a *history*, and it had
become the only index of what is open — a "Still open" row that is a comma list
of sixteen ids, two of them (**B-10**, **B-27**) closed weeks ago and still
listed. An index you have to fact-check is not an index. This section is the
opposite shape: **only what is open, one line each, classified by what it is
waiting on.** The history above is left exactly as it is.

**The classification is the point.** Every open item is waiting on one of three
things, and they are not interchangeable — the reason items sit for weeks is that
"needs a decision" and "needs an afternoon" have been living in the same list.

| Class | Meaning | Who unblocks it |
|---|---|---|
| **MEASURABLE NOW** | harness and data both exist; nothing to build first | nobody — just run it |
| **BUILD** | scoped, no open question, only work | a session |
| **OWNER** | a judgement call this desk cannot make for itself | you |

### MEASURABLE NOW — the harness and the data are already here

Re-verified against the code and the stores on 2026-09-17. **This tier was the
discovery of the refinement pass:** three of these were filed as if blocked, and
none of them is.

| # | What is unmeasured | Why it is runnable today |
|---|---|---|
| ~~**B-56**~~ | ~~the SVP **structure** BUY/SELL/HOLD signal~~ — **MEASURED 2026-09-17 → INVERTED** (spread −1.77%, p_rot 0.041, SELL beat BUY 8 of 8). Mirror deliberately not shipped; stays a bystander. [[analyses/SVP-Structure-Signal-Pre-Registration]] | done — the prior was right |
| ~~**B-8**~~ | ~~mean-reversion **stops**~~ — **MEASURED 2026-09-17: CONNORS WAS RIGHT, for tight stops.** The shipped session-low stop costs **−0.64pp** vs no stop (p=0.0086, **n=742**, 300 names, 20y); 2-ATR costs nothing measurable because it is only touched 24.7% of the time. Stop deliberately unchanged; the number is now in the scanner's own plan output | done |
| ~~**B-9**~~ | ~~the Volume-Profile **80% rule**~~ — **MEASURED 2026-09-17: FALSIFIED.** 45.5% (95% CI 37.3–54.0, n=134) against a claimed 80%. Lift over base −4.1pp, p=0.422, explicitly NOT claimed | done — and it was never blocked on data |
| ~~**B-42r**~~ | ~~`pivot_len` 5 vs 15~~ — **MEASURED 2026-09-17: the two settings agree on `state` only 29.6%** of the time (199 names), and 17.6% read DOWNTREND in the scanners against UPTREND on the chart. **Promoted to an OWNER decision** — see below | measured; the decision is yours |
| ~~**B-94**~~ | ~~an outside letter’s option-chain levels have never been checked against our own~~ — **MEASURED 2026-09-19: SPLIT.** Max pain **23,300 reproduces EXACTLY** on the 2026-09-17 chain (and on 09-16), nearest expiry 2026-09-22. Both walls MISS on the whole-chain definition (ours 24,500 call / 22,000 put). **Post-hoc, using the module’s own existing `NEAR_STRIKES = 10` window, the call wall 23,500 also reproduces EXACTLY** — so the call-wall gap was DEFINITIONAL, ours. The put wall 23,100 does not reproduce under either definition: it is our **#8** put strike (5.36M) while 23,000 carries **9.65M**, 80% more. Verdict by the pre-registered rule: **NOT REPRODUCED** (1 of 3 exact); by substance: **2 of 3, and the third is the letter’s weakest claim**. [[#B-94]] | done — and it found a gap in OUR tool, not only in the source |
| ~~**B-97**~~ | ~~nothing has ever scored whether `pivot_d` and `pivot_w` AGREE~~ — **MEASURED 2026-09-19: they agree on the SIDE of the pivot 53.9% of 499 names (chance 41.8%, lift +12.1) and read OPPOSITE sides 37.9%. Median across 29 month-ends: 64.0% side / 27.3% opposite. Both pre-registered bands fail — TWO DIFFERENT READINGS + CONTRADICTION. Agreement is above chance at every date, so the columns are not independent; the shared part is just far smaller than two adjacent columns imply. [[#B-97]]** | done — and it re-scoped B-96 |
| **B-21b** | every floor set on 2026-08-07 came from **one session's cross-section** | the floors are labelled in code and the history to re-measure them on is cached |
| **B-59r2** | ~~PSAR's **unique** flips (68.9% uncovered at ±3) — the edge test the overlap check left owed~~ — **CONTESTED 2026-09-19, see [[#Re-verification 2026-09-19]]. The 2026-09-11 pass struck this debt as already discharged by [[#B-59r]], and this table re-raised it six days later. The counts do not settle it: B-59r scored 8,576 PSAR-not-STAI flips, while "68.9% uncovered" is ~19,693 flips uncovered by *either* twin. Cheap to resolve, and it is a re-read before it is a run** | `psar_stai_edge.py` already scores PSAR-only cells |
| ~~**B-89**~~ | ~~**`mabias`** — a 9/20 EMA-cross verdict ladder shipping LONG/SHORT badges on the chart, **never scored**~~ — **MEASURED 2026-09-24 → NULL.** spread −1.68%, p_rot 0.165; SHORT outperforms LONG in 7 of 8 symbols but not significantly. The badge stays on the chart as a visual aid; it is NOT entered into the confluence pipeline. [[analyses/MA-Bias-Edge-Test]] | done |
| **B-90** | the **VWAP+EMA agreement state** from the owner's card | `intraday_store` already holds 15m bars, 85 sessions, 6 names — no new data |

### BUILD — scoped, nothing to decide

| # | What | Size |
|---|---|---|
| **B-46** | Ichimoku Cloud — verified still absent (`ichimoku` appears only in `psar.js`) | medium |
| **B-47** | TPO / Market Profile pane — verified absent | medium |
| ~~**B-48**~~ | ~~Cumulative volume delta — **answer the DATA question first**, before any indicator~~ — **PROBED 2026-09-21 → FAIL, and the instruction was right.** A true CVD needs the aggressor side of each trade; the desk has OHLCV bars and no tick or bid/ask feed, so only a PROXY is computable (sign the bar's volume by the bar's direction — what every package shipping "CVD" on OHLC data does, usually without saying so). **The probe asked whether that proxy is a property of the market or of the bar size**, with the bar pre-committed in code before the run: ≥90% sign agreement between 5m and 15m session totals, and r ≥ 0.90. **Result: 75.6% and r=0.80 over 435 symbol-sessions.** One session in four changes its mind about who was in control when the bar size changes (28 of 87 on ICICIBANK), and the coarser bars do not just re-sign the day — they **inflate** it 1.4-1.8×, because aggregation hides the intra-bar reversals that cancel at finer resolution. **The two conventional proxies disagree with each other on 26% of sessions on the SAME bars**, so the unstated choice of formula moves the answer about as much as the timeframe does. **One correction made before publishing:** the first run read 79.7% because it included `^NSEI`, which has no volume — every delta zero, every session trivially "agreeing", 87 free sessions of 100%. See [[analyses/CVD-Data-Probe]] | **the indicator is NOT built, and that is the finding.** Three honest options are written up (drop it · ship it as a named bar-size-explicit *delta proxy* with the 76% on the card · buy a tick feed) and **none is chosen here** — the probe was asked whether the data supports the indicator, not which compromise to make |
| **B-6** | retest entries: the desk detects breaks well and retests poorly; `scan_order_block` is the only retest trigger | medium |
| ~~**B-93 / PR-1**~~ | ~~Strategy Hub's pattern table shows 20 hardcoded rows with frozen LTP~~ — **BUILT 2026-09-17** (`a884f11` priced the table live and caught one row on the wrong side of its own scoreboard, `e7b1741` fixed a "Live" heading over a five-week-old literal, `dc7a10e` computed the fundamentals block). Listed open by a table refined the *same day* it shipped | done |
| ~~**B-17**~~ | ~~OBV has no wiki page, and now ships on **two** surfaces~~ — **CLOSED 2026-09-11** ([[concepts/On-Balance-Volume]], `8b29158`). The 2026-09-11 pass recorded this closure **twice** and this table still carried it open six days later | done |
| **B-87r** | the monolith **extraction** the ratchet is holding the line for. **FIRST PAGE EXTRACTED 2026-09-19: Astro Timing → `tools/desk_pages/astro_timing.py`. `dashboard_app.py` 13,804 → 13,108 lines (−696), raw-HTML renders 112 → 102; ceilings lowered 13,900 → 13,150 and 120 → 108.** Chosen because `ast` said it was the only large page touching **zero** module-level variables and **zero** module-level helpers — a move, not a refactor. The dispatch is a shared registry, so **every next extraction now LOWERS the statement ratchet instead of raising it**. Remaining: 29 page blocks, 6,790 inline lines; the next clean targets are Telegram Signals (322 lines, 1 helper) and SVP Structure (219, 2) | ongoing — but now it pays for itself, one page per session |  **SECOND PAGE EXTRACTED 2026-09-21: Telegram Signals → `tools/desk_pages/telegram_signals.py`, and `_paginated_df` → `tools/ui_tables.py` (its only coupling to the monolith, and a helper nine call sites shared). `dashboard_app.py` 13,171 → **12,785 lines**; ratchets lowered 13,150 → 12,800 and, for the first time, module statements FELL (325 → 324) — which is exactly what paying for the dispatch once was supposed to buy. The extraction was not planned for this session: the LINE ratchet refused [[#B-109]]'s twenty-line addition and told it to extract a page instead of raising the number, which is the ratchet working as designed.** **THIRD PAGE EXTRACTED 2026-09-24: SVP Structure → `tools/desk_pages/svp_structure.py` (~225 lines). `dashboard_app.py` 12,785 → 12,713 lines; raw-HTML renders 106 → 104; ratchets lowered 12,800 → 12,750 and 108 → 106.**
| ~~**B-37**~~ | ~~volume share-card~~ — **BUILT 2026-09-24.** `volume_stocks_from_scan()` wires `volume_anomaly.scan()` output to `VolumeStock` dataclass (RVOL ranking, mcap derivation, Q1 fundamentals). Dashboard button on the Anomaly Spikes page renders 1200×675 PNG with slider for 1–2 names, fundamentals enrichment, image display + download | done |
| ~~**B-91**~~ | ~~VWAP's zero-point cases say **why**~~ — **BUILT 2026-09-23.** The indicator label keeps its short form `VWAP (session · intraday only)` and gains a `title` tooltip on hover explaining the two distinct zero-point cases: (1) daily — each bar IS its own session so VWAP collapses to typical price, (2) zero-volume feeds like index spot — undefined. The `vwapSeries` guard at line 1729 (`if (!INTRADAY_TFS.has(tf)) return []`) already prevents drawing; the tooltip now says WHY | done |
| ~~**B-92**~~ | ~~Flag & Pole detector, both directions~~ — **BUILT 2026-09-17**, both cards carry a full plan; counting first caught a breakout condition that was unsatisfiable by construction | done |
| **B-95** | **FII / client participant-wise F&O long:short ratios** — the “88% short is squeeze fuel” claim from [[sources/Bramesh-NIFTY-Gann-1x3-Higher-High-2026-09-18]]. **Probe the DATA first:** nothing here reads NSE’s participant-wise OI (`FII` in the toolchain is a *shareholder-name* classifier in `block_deal_intel.py`; the F&O bhavcopy carries contract OI, not the participant split). If the file is fetchable → pre-register, then measure **with rotation p-values**, because this is an autocorrelated STATE series and a t-test here manufactures significance (known null: p=0.031 Welch vs 0.32 rotation). Needs a control too — extremes cluster in falling markets by construction. See [[concepts/Participant-Positioning-FII-DII]] | data probe, then medium |
| **B-96** | **monthly / quarterly / yearly pivot zones** — `row_metrics.pivot_levels()` already accepts any frame (*"Feed it a weekly-resampled frame to get weekly pivots"*) and `timeframe_board.py` already resamples to `ME`/`2QE`/`YE` from one download. **The only two call sites in all of `tools/` are `pivot_d` and `pivot_w`** (`row_metrics.py:510-511`, grep-verified). No new data, no new arithmetic — a composition of two things already built. From [[sources/Bramesh-TradingView-Gann-Scanners-Product-Line]], where the idea of looking past one timeframe sells for ₹6,666/month | **no longer small — B-97 re-scoped it 2026-09-19.** At 37.9% opposite today and 27.3% at the median, five peer columns would routinely contradict each other with nothing saying which governs. B-96 must either name a governing timeframe or print the AGREEMENT as the reading (a "3 of 5 above" state, B-42's `agreement` shape). The second is the better fit, and it is a design task, not a composition |
| **B-98** | **a calendar-anchored reference level** — **DETECTOR BUILT + PRE-REGISTERED 2026-09-20; the measurement is the open half.** `tools/calendar_anchor.py`: the January high/low as an anchor, a state (ABOVE / BELOW / INSIDE) and the event (first close outside), 16 tests. **The build produced its own prior, counted before any forward return was touched** (120 names, ~10 years, **972 symbol-years**): the range breaks in **971 of them — 99.9%**, median **7 sessions** after January, **42%** inside five sessions, up-share 44.4%, median January width 16.1%. **A construct that fires on 99.9% of symbol-years selects nothing**, so this will not be registered as a shortlist scanner whatever the edge turns out to be — that is settled by the base rate, not by a p-value. The design changed BEFORE the run because of it: [[analyses/Yearly-Opening-Range-Pre-Registration]] tests the break's DIRECTION, the STATE, and whether the break HELD, with a by-year test as the deciding one (every name breaks in the same few weeks of the same year, so a pooled p-value over 971 correlated signals would be the most overstated number here). **Dates are the catch**: `_clean_ohlc` and `backtest_scanner` both `reset_index(drop=True)`, so the module takes a dated frame and RAISES rather than guessing that bar 0 is January — see [[#B-104]], the same class of bug already found live | **detector done; the measurement is next, and it is a study of its own** |
| ~~**B-93 / PR-2**~~ | ~~trade-plan coverage as a visible metric — only **7 of 31** firing scanners emit entry/stop/target~~ — **BUILT 2026-09-17** (`7385a9b`): `tools/scanner_plans.py` + its cache, rendered from `dashboard_app.py:8256`. **The census also corrected the number this row states — 14 of 45, not 7 of 31** | done |
| ~~**B-99**~~ | ~~**four indexed studies ran and left no citable result**~~ — **DOCUMENTED 2026-09-24.** SBC-15m (lift 0.96×, NULL), SBC-muhurat (lift 0.66×, NULL), B-30r newmoon levels (lift 0.95–1.05×, NULL) — three clean nulls. B-38 funnel price legs: machinery verified on synthetic data, live measurement still needs fetcher wiring. [[analyses/B99-Study-Write-Ups]] | done — `claims_lint` CHECK 0c cleared |
| ~~**B-100**~~ | ~~**`oi_walls` ranks the WHOLE chain and does not say so**~~ — **FIXED 2026-09-23.** `oi_walls()` gains a `near_strikes` parameter; when set, ranking is limited to the N strikes nearest spot on each side, so far-OTM weekly inventory no longer appears as "resistance" or "support". `read_levels()` now passes `near_strikes=NEAR_STRIKES` (10) by default, and the response includes `wall_window: 10` so consumers know the window. The chart overlay (B-28) inherits this automatically since it draws what the server returns. 3 new tests (29 total in test_option_chain.py). The `oi_walls(chain, n=3)` call without `near_strikes` still works as before for any caller that wants the whole-chain ranking | done |
| ~~**B-101**~~ | ~~the registry has no BILATERAL pattern — a symmetrical triangle has no honest reading~~ — **BUILT 2026-09-20**. `scan_symmetrical_triangle` + `detect_symmetrical_triangle_geometry` in `tools/scanner_templates.py`, registered as **category `Neutral`** — the desk's first non-directional scanner. It generalises the wedge core's pivots/fit/containment/volume tests and differs in three places: the slopes **oppose**, **neither side may be flat** (a flat side is an ascending or descending triangle, and the ascending case is the one already covered by accident), and **no bare `entry`/`stop`/`target` is emitted at all** — both legs ship as `up_*` / `down_*`, so nothing downstream can read a long out of a coil by picking up a key it expected. **The missing STATE this row was really about is the part that took the work:** `opportunity_hub.NEUTRAL_SCANNERS` + a `neutral` tier at weight 0, and an explicit skip in `tally_evidence` — whose fall-through gives an unmapped non-risk scanner its own family of one, which is the right default for a new directional scanner and exactly wrong here. It is **not** folded into `RISK_SCANNERS`: that would have been the cheap way to stop the vote and would print a bearish flag on a pattern that is not bearish. `scanner_plans` gains a fifth state (`BILATERAL`) for the same reason it already separates UNSEEN from NONE — counting this as "no plan" would put it on the list of things to fix, and the fix would be to invent a direction. **Measured, not assumed: 32 hits over 147 nifty500 names at stride 5** (probed 2026-09-20, same protocol as the PR-2 census) — it fires, and it does not flood. 21 tests in `tools/test_symmetrical_triangle.py` pin the geometry, every neighbouring shape it must refuse, and the two assertions that are the point: no bare `entry` key, and no vote. | **built, then MEASURED 2026-09-20 → NULL — and the FRAMING SURVIVED.** Pre-registered in [[analyses/Bilateral-Expansion-Pre-Registration]], run by `tools/bilateral_expansion_study.py` once B-102 gave the harness a side. **Two runs, and the first one is why the second exists.** Run 1 (150 names, ~900 sessions) returned **28 coils against a pre-registered floor of 200 → INCONCLUSIVE**, with all four horizons leaning positive (+1.02 to +4.47pp) and a 29.2% up-share that looked like a finding. Run 2 ([[#B-103]]: 482 names, ~10 years, **270 coils**) settles it: **a coil precedes an ORDINARY move** — +0.32 / −0.01 / +0.23 / −0.74pp |move| vs an every-bar baseline at 5/10/20/60d, p 0.27–0.98, sign not even stable. **NULL, adequately powered**, which is a result and not an absence of one — and it also fails to support the registered prior (that a coil precedes a SMALLER move). **Claim C is the payoff: 42.7% up-share (105 up / 141 down / 24 undecidable), INSIDE the 40-60% band pre-committed as a falsifier of the "bilateral" label — at a sample that could have fired it.** The non-voting neutral card is kept on evidence rather than taste. Run 1's 29.2% was noise, and the floor is the only reason it was never written up. **Claim B is now well-powered description: the textbook 50-75% apex band carries nothing** (in-band coils expand slightly LESS at every horizon, p 0.37–0.79), so the card now says *position, not edge*, and the 0.12 apex weight is documented as structural (how much triangle is left) rather than predictive. The scanner stays registered, running, visible and non-voting: 270 hits in a decade that predict an ordinary move are context, not a trade |
| ~~**B-102**~~ | ~~a bilateral pattern cannot be scored by a long-only harness~~ — **BUILT 2026-09-20.** `backtest._simulate_plan` takes a `side`, and the short leg is the exact MIRROR (stop above entry hit on the high, target below hit on the low, R = entry − exit) rather than a sign flip applied to a long walk — a flip would have scored the short against the long's own stop/target ordering and credited the wrong bar. **The evidence that it is right is an equivalence test, not an assertion:** it matches `order_block_rules_backtest.simulate` and `flag_pole_edge.walk_plan` bar-for-bar and R-for-R on 60 random frames per side, so every number those two studies already published is unmoved and folding the copies into the shared one is now mechanical. The replay reads the side off the plan's own geometry (a stop above the entry is a short), so a bearish scanner's plans are simulated instead of silently counted as unsimulatable; `plans_unsimulated` now means degenerate plans only. `backtest.absolute_move` is the second half — the directionless unit a coil is scored in. 13 tests in `tools/test_backtest_sides.py` | done — the two hand-written mirrors are now redundant and can fold in whenever that is worth a commit; the equivalence tests are what make that safe |
| ~~**B-103**~~ | ~~the bilateral expansion test is underpowered, and the fix is arithmetic~~ — **RUN 2026-09-20, same day it was raised.** `--symbols 500 --days 2500`: 482 usable names, ~10 years, **270 coils** against the floor of 200. The arithmetic held (0.19 coils per name per 900 sessions predicted ~250). Nothing in the analysis plan moved — event, primary, horizons, pass bar and falsifier all as registered — and each run writes its own file under `cache/bilateral_expansion/`, so the underpowered run is still on the record next to the one that supersedes it. **Both open results closed at once:** the expansion effect is a NULL, and the bilateral framing passed its falsifier at 42.7%. See [[#B-101]] | **done — and the cheapest lesson in the pair.** The two numbers that most looked like findings at n=28 (a +4.47pp @60d lean and a 29.2% up-share) are both gone at n=270. The pre-registered floor cost one extra run and bought not having retracted either |
| ~~**B-104**~~ | ~~the market-model alpha block in `backtest_scanner` has never run~~ — **FOUND AND FIXED 2026-09-20**, while building [[#B-98]] and asking what the harness does with dates. The block computes beta over the 60 bars before a signal and reports alpha = raw − β × market. Its guard read `hasattr(df.index, "date")` — and the frame is `reset_index(drop=True)` **eleven lines above**, so the index is a RangeIndex and the test is always False. **`alpha_avg` and `alpha_ttest` came back None on every run since it shipped**, including the **five dashboard call sites** that fetch a benchmark specifically to pass it in. Nothing errored; the column was simply always empty. Verified live before the fix (28 signals, valid dated benchmark, alpha None) and after (alpha populated, p computed). The fix keeps the dates the reset throws away and **refuses the join when NaN rows were dropped** — a date/bar misalignment would be a plausible wrong number, which is worse than no number. 6 tests in `tools/test_market_model_alpha.py`, including that a beta-2 symbol loses twice as much of a rising market as a beta-1 one. **No published figure moves**: the field was never populated, so nothing ever cited it | **done.** Noted in passing and not fixed: `mkt_ret` is collected and handed to `_aggregate`, which never surfaces it — the market return itself is still invisible |
| ~~**B-105**~~ | ~~a BEARISH scanner is casting a BULLISH confluence vote~~ — **FIXED 2026-09-21.** `Liquidity Sweep Bear` shipped as `category: "Risk"` and was never added to `opportunity_hub.RISK_SCANNERS`, so `scanner_tier()` read it as `unmeasured` and `tally_evidence`'s fall-through — the branch that deliberately gives an unmapped NON-risk scanner its own family of one — counted a breakdown detector as **0.5 points FOR the name**. One line to fix; **the test is the actual deliverable.** `test_support_breakdown_retired.py` already asserted this for ONE scanner and said why in as many words; it did not generalise, which is how this survived. `tools/test_risk_scanner_invariants.py` now asserts it over the WHOLE registry, in both directions (every `category == "Risk"` entry is in the tuple; every tuple entry is category Risk) plus the same invariant for `category == "Neutral"` / `NEUTRAL_SCANNERS` (B-101), and it is **mutation-checked**: restoring the broken tuple in memory makes it fail with the right message. 17 tests. **Blast radius, counted rather than guessed:** the stored shortlist holds **2 affected rows, both QUADFUTURE** (2026-09-19 and 09-20). Before → after: **5 families / 2.50 pts → 4 / 2.00**, and **6 / 2.75 → 5 / 2.25**; the risk-flag list gains `Liquidity Sweep Bear` on both. **Confluence % is 100 either way** (both clear `FULL_CONFLUENCE = 2.0` on the bullish evidence alone), so no ranking actually moved — the note on those rows had simply been listing a bearish detector among the "independent families" supporting the name, one clause away from warning about a different bearish one | **done.** Stored rows are left as they were run — they are a RECORD of what the desk said that day, and rewriting history to match today's code is the one thing a run-date store must not do. Re-running the scan is the owner's call and would change nothing but those two notes |
| ~~**B-106**~~ | ~~"Capital at Risk" is measured from a price that is no longer live~~ — **FIXED 2026-09-21.** The arithmetic left the monolith: `tools/portfolio_risk.py` now computes **both** numbers and `dashboard_app.compute_portfolio_summary` is a five-line adapter over it. **Initial risk keeps its old key and its old meaning** (`capital_at_risk_pct`) — silently redefining a key is how one number ends up read two ways — and the live question gets a new name (`open_risk_pct` = `(last − stop) × qty`). Home's card and `market_verdict`'s 6% flag both read the OPEN number now, with the initial one on the sub-line, because **the gap between them is the read**: it is how much of the original risk the book has retired. **Three things fell out of doing it properly:** a stop ABOVE the live price is floored at zero, not negative, or one winner would net off two losers' real exposure; a position with **no stop** has unbounded risk, is not in the number at all, and now raises its own caution instead of scoring as zero; an **unpriced** position is counted and said out loud rather than skipped. 21 tests — the math was previously untestable, because importing `dashboard_app` runs the app | **done.** The card's own three-way sub-line moved into `prisk.risk_card` too: the monolith ratchet caught the four module-level assignments this started as, and it was right — logic at module scope in that file is logic no test can reach. Net module-statement cost: **zero** |
| **B-107** | **the RISK stage is three-quarters absent, and the quarter that exists is defined twice** — **TWO OF THREE BUILT 2026-09-21; drawdown split out as [[#B-110]].** **Sizing, reconciled:** `prisk.reconcile_size` multiplies the council's per-trade size by the market verdict's 0/50/100% multiplier and checks `max_trades` against the open book, and the council card now SAYS which rule moved the number (*"12.0% at the per-trade risk rule, scaled to 50% by today's SELECTIVE verdict · 1 of 2 trade slot(s) left"*). **No new rule was invented** — both numbers already existed and had simply never met, so a STAND DOWN day left the suggested size untouched. Size and cap are reported SEPARATELY because they fail differently: a halved size still lets you take the trade, being at the cap does not. **Exposure, built:** `prisk.exposure` gives deployed %, largest position, top-3, and sector concentration, on the Portfolio page. Measured against **total capital, not the deployed book** — a share of what is deployed flatters a book that is mostly cash, and the question is what happens to the ACCOUNT when one name gaps. An unmapped symbol is counted as unmapped rather than bucketed into "Other" (the `sector_column` rule). **It reports and does NOT judge: no thresholds.** What counts as too concentrated is risk appetite, which is a decision to be made once and deliberately by the owner, not a default smuggled in by whoever wrote the function. Verified end-to-end on real prices through a THROWAWAY copy of the DB: deployed 38.9%, largest 22.2%, Banks 22.2%, unmapped 4.3%. 36 tests | **max-loss is still a flag, not a limit, and that is deliberate** — enforcing it means refusing to show something, which is a policy decision. Drawdown is [[#B-110]]. What remains here is one owner call: whether any of these numbers should ever BLOCK rather than inform |
| **B-108** | **nine pages answer the SCAN stage and the nav does not say which is canonical** — [[analyses/Pipeline-Alignment-Audit]]. The "Screening" group holds **9 of 23 pages** (Screener, Other Screeners, High-Growth, Hidden Treasures, Breakout Scans, Delete Funnel, plus Opportunity Hub / Scanner Hub / SVP Structure which are really SIGNAL), while RISK has no group at all and is scattered across Home, Portfolio and two research pages. **This is a presentation question, not a defect** — nine entry points may be nine different questions rather than drift — but a reader coming to the desk cold cannot tell which page starts the funnel. Options, in ascending order of disruption: (a) leave the nav, publish the audit as the map; (b) re-blurb each page with the stage it serves, changing no routing; (c) regroup the nav by stage. **(b) is the cheap one and loses nothing** | **OWNER decision on (a)/(b)/(c); (b) is ~23 string edits** |
| ~~**B-109**~~ | ~~the trade plan and the per-name verdict are not on the page a name is chosen from~~ — **BUILT 2026-09-21.** `tools/plan_on_demand.py` puts a *Plan a name from this list* picker on the Opportunity Hub: pick one shortlisted name, get the full council card — BUY / WATCH / AVOID, entry, stop, three targets with R:R, invalidations, horizon, and the size already scaled by today's market verdict ([[#B-107]]). **A click-through, not a column, and the reason is the pipeline itself:** PLAN comes *after* the reader has chosen, so twenty plans before they have chosen is both expensive (the council fetches fundamentals and scores two theses per name) and the wrong shape — a ranked list where every row carries a full plan is not a shortlist any more. The module owns the SELECTION and the framing; the council, the card renderer and the fetchers are injected, so there is no second copy of "how a trade card looks" to drift. Picker order is the RANKING's order — sorting it alphabetically would bury #1 — and a null symbol is dropped rather than stringified into "NONE", which a test caught. **Verified live:** AHCL → *WATCH, conviction 8.7, entry 26.24, stop 15.41, T1/T2/T3, and "size 0.0% — 4.8% at the per-trade risk rule, scaled to 0% by today's STAND DOWN verdict, already at today's cap of 0 trade(s)"* — the B-107 reconciliation doing its job on a real STAND DOWN day | **done.** 8 tests on the selection logic; the Streamlit surface is verified by driving the running app |
| **B-110** | **drawdown cannot be computed because nothing stores the equity curve** — split out of [[#B-107]] 2026-09-21 rather than left as a bullet. The reference pipeline names drawdown as a RISK component and the desk has no peak-to-trough number for the portfolio or for closed trades. **The blocker is data, not arithmetic**: `positions` holds entry/exit prices and dates, and there is **no equity-history table at all** (checked: `portfolio_equity` and `equity_curve` do not exist). Two honest routes — (a) a daily snapshot job writing `{date, equity, deployed, open_risk}` after close, which starts the series TODAY and is worth nothing for a year; (b) RECONSTRUCT the curve from `positions` + cached OHLCV, which gives history immediately and inherits every survivorship and price-adjustment quirk in the cache. **(b) then (a) is the honest pair**: reconstruct to have a number now, snapshot so the number stops depending on a reconstruction. Whichever comes first, the result must say which one it is — a reconstructed drawdown and a recorded one are not the same claim | **medium.** The reconstruction is a walk over open+closed positions; the snapshot is a scheduler job beside the ones `scheduler_core` already registers |
| ~~**B-111**~~ | ~~the desk reads corporate filings one SYMBOL at a time, and the market-wide stream was never read~~ — **BUILT 2026-09-21**, from the owner's question *"can we fetch company deal information yet?"* — checked end to end rather than from the docstrings. **Two halves.** **(a) The filing text was being thrown away:** `volume_anomaly` printed NSE's `desc`, which for a third of filings is the useless *"General Updates"*, while the same payload's `attchmntText` carried the actual event. `filing_headline()` now strips the *"X Limited has informed the Exchange about"* boilerplate and the repeated category, and the 21-Sep card's own "why" comes straight out: SAMBHV reads **"proposed preferential issue of 8,695,400 fully convertible equity warrants"** where it used to read "General Updates". **(b) `tools/nse_filings_feed.py`** reads the market-wide endpoint that was always there — **without a date range it returns 20 rows, with one it returns 1,262 over four days**, which is why *"there is no market-wide feed"* was easy to believe. Bucketed (ORDER_WIN · M&A · FUND_RAISE · CAPACITY · RATING · GOVERNANCE · RESULTS) and de-noised: **1,262 raw → 226 material, 494 dropped as exchange/compliance noise**. Wired into India Market Intel, whose own caption said filings were *"not wired up — the feed is very high volume without a watchlist filter"*; the bucketing IS that filter, and the caption is retired. Verified live: WELCORP's Saudi Aramco order (ORDER_WIN, 20-Sep) and GUJTHEM's acquisition (M&A, 18-Sep) — both names from the owner's screenshots — surface without either being a volume spike. **One real bug caught by its own test:** `[A-Z]{3}` under `re.I` matched the "ver" in *"over 771 million SAR"* and printed **"VER 771 million"**, a plausible amount in a currency that does not exist; currency codes are now an explicit list. 26 tests | **done, and the limit is named on the surface** — see [[#B-112]] |
| **B-112** | **the deal AMOUNTS live in PDFs nobody parses** — the half of the owner's question that [[#B-111]] could not answer. NSE's API carries a category, a one-line text and a LINK: *"₹937 Cr order book"*, *"₹126 Cr contract from Kalpataru"*, *"SAR 771 Mn"*, *"₹1,220 Cr acquisition"* are all attachment content. `amount_from()` reads a figure only when the filing's own text states one and returns None otherwise — **None means "not in the text", never "small"**, and the surface says so. **Measured blind spot, 4 days:** of 1,262 filings, 521 are neither noise nor classifiable — **145 "General Updates" and 76 "Updates"**, generic labels whose content exists only in the PDF. TEGA's ₹126 Cr Kalpataru contract is exactly this case: it filed as *"General Updates — intimation pursuant to Reg. 30"*, which is material BY DEFINITION (Reg 30 is the materiality rule) and unreadable without the attachment | **medium, and it wants a DATA PROBE first, the way [[#B-48]] got one**: how many attachments are text-layer PDFs vs scans, how large (WELCORP's was 3.32 MB), and what share of amounts a regex over the extracted text actually recovers. Build the extractor only if the probe says the text is there |
| ~~**B-113**~~ | ~~scheduler page reports STATE but has no run HISTORY~~ — **BUILT 2026-09-23.** `parse_run_history()` parses log markers into structured run records (job, started, outcome, ended, duration). `run_summary()` gives totals. `orphan_tasks()` finds OS tasks not in JOBS (found: TradingBramha-IntradayUpdate). `write_bat` now stamps end time for duration. CLI: `history`, `summaries`, `orphans`. Current: alert_watcher 144 ok, daily_scanner 4 ok, sentiment_daily 6 ok, opportunity_daily 5 ok, zero failures. 11 tests. **Remaining from the original 7-step plan:** (3) daily_scanner now HAS markers — corrected from the 2026-09-21 count; (4) log rotation not built — 37KB/133KB/27KB/32KB, not urgent; (6) Pipeline Log fold-in: owner decision; (7) page extraction: follow B-87r pattern when next touching the monolith | **done — steps 1,2,5 built; 3 self-corrected; 4,6,7 deferred** |
| ~~**B-114**~~ | ~~the SBC card's new wording is measured on ONE name and cannot be settled there~~ — **POWERED AND SETTLED 2026-09-21.** `walk_fast` made it runnable (one detection pass per symbol instead of two per bar) and was **diffed against the slow walk on BSE before being trusted — 41 events, every field identical**. Then 150 nifty500 names, ~10 years: **4,608 events, 2,525 held vs 2,083 failed**. A break that HELD beat one that FAILED by **+0.35 / +0.86 / +1.28 / +0.96pp** at 5/10/20/60d, direction-signed and net of costs, p<0.001 at the primary horizon and the sign holding everywhere → **POSITIVE at the pre-registered bar**. **It also survives the clustering control** the pooled p cannot supply (symbol as the unit, B-76c's method): 133 names, mean **+1.37pp**, median +1.04pp, **79/133 positive**, p=0.0015. **BSE alone had said +16.05pp — twelve times the powered number**, same direction, and that is the floor's entire argument in one line. **The graded quality score does NOT rank on 4,608 events** (NORMAL −0.37% sits below WEAK +0.52%; `warn` beats `good`), so what carries the result is the binary — price coming back through its own level — and the `0.6·dist/ATR + 0.4·body/ATR` formula the card prints is decoration so far | **done. Two things it deliberately does NOT claim:** it is held-vs-FAILED, **not** held-vs-doing-nothing — no baseline arm was pre-registered or run, and that is the obvious next test ([[#B-115]]); and it is not a trade at +1.28pp over 20 sessions with 59% of names positive |
| ~~**B-115**~~ | ~~"held beats failed" is not "held beats doing nothing"~~ — **RUN 2026-09-21 → POSITIVE, and thin.** Pre-registered and committed BEFORE the run (`26f3fda`): baseline = every eligible bar in the same names and window, same timing, same costs; up-direction only, because a long-only desk's alternative is owning it, not shorting it. **1,545 up-held breaks vs 261,121 eligible bars: +0.21 / +0.31 / +0.82 / +0.75pp** at 5/10/20/60d, **p=0.006 at the primary horizon**, sign positive at all four → POSITIVE as written. **Clustered: 130 symbols, mean +0.67pp, median +0.36pp, 75/130 positive (58%), p=0.0297.** **Read it thinly:** only h=20 clears 0.05 individually, the clustered p is 0.0297 against B-114's 0.0015, and mean-above-median says a minority of names carry more than their share. **So B-114's +1.28pp splits roughly in two** — about +0.8pp of "held is better than average" and the rest from "failed is worse than average"; both real, neither large. **A sign error worth recording:** the first report printed *"held down-breaks fell −0.94%"*. They did not fall — the stored return is signed by the event's direction, so the name ROSE 0.94% against a random bar's +1.47%. A held DOWN break is an **underperformance** read, not a decline, and a test now pins the wording so "fell" cannot reappear for a number that rose | **done.** The card keeps describing structure rather than proposing trades: 0.8pp over 20 sessions on 58% of names is a real effect and a small one. The quality ladder is still unranked and still decoration |
| **B-116** | **every measured-move TARGET this desk prints is unmeasured as a target** — **PLUMBING DONE 2026-09-21, CENSUS BLOCKED, and the block is the finding.** `_aggregate` always built the plan scoreboard (`target_hits`, `stop_hits`, `win_rate`, `avg_R`) and `format_report` always printed it; `walk_forward_scanner` dropped it, so the B-19 batch computed target-vs-stop for 44 scanners and discarded it 44 times. Now pooled across windows — **counts summed, rates recomputed from the sums**, because three windows of 4, 40 and 400 plans are not three equal opinions about a hit rate (averaging says 50% where the truth is 25.7%; there is a test). **Then the control failed, which is why no numbers are published here.** Flag & Pole through the generic harness reads **10.9% target / 82.6% stop / −0.42R**, against B-92's own study of the same scanner at **36.8% / 51.6% / +0.36R**. **RETRACTED 2026-09-21 — the first diagnosis was wrong.** This row originally blamed the EVENT DEFINITION: `scan_flag_pole` fires on runs of ~4 consecutive bars, so the harness supposedly re-entered the same breakout four times. [[#B-120]] built the fix (`signal_mode="fresh"`) and it **did not reproduce B-92 either — 11.8% / 84.4% / −0.40R against "all" mode's 11.0% / 82.5% / −0.42R**. The reason the two modes barely differ was sitting in the code the whole time: **`min_gap=5` already skips five bars after every recorded signal**, so a four-bar run was ALREADY collapsing to roughly one entry (RELIANCE: 13 signals in `all` vs 10 in `fresh`). The run counts were right and the story about them was not. **So the discrepancy is UNEXPLAINED**, and the leading unchecked candidate is now [[#B-121]] — the harness assumes the card's stated entry is filled, at that price, whether or not price ever trades there | **the plumbing is done and worth having. The census needs [[#B-120]] first** — a fresh-signal filter in the shared harness. Three studies have now hand-rolled their own (B-92, B-101, B-114) **EXPLAINED 2026-09-23 — third diagnosis, and this one has a control behind it.** `flag_pole._card` returns a full entry/stop/target for EVERY detected flag, **including `WATCH — unbroken` ones** whose entry is a trigger above the market; the harness takes every card as a trade. B-92 counted only BROKEN flags. Same harness, broken cards only, `market` fill, fresh: **33.8% / 54.0% / +0.26R (n=645)** against B-92's own simulator on the same 150 names **34.6% / 53.2% / +0.29R** — reproduced. So the retracted 'runs of ~4 bars' diagnosis was wrong about the mechanism but right that it was the EVENT DEFINITION. Consequence filed as [[#B-128]] |
| **B-117** | **no target is ever sanity-checked against volatility** — same audit. The desk uses ATR for STOPS (`stock_council.ATR_STOP_MULT`), for sizing, and to measure a flag's POLE (`flag_pole`: *pole 10.79x ATR*) — but **nothing asks how far the TARGET is in ATR terms**. A wedge target 0.4 ATR away and one 5 ATR away are printed identically, and the first is inside the noise while the second needs a move the timeframe rarely produces. The practitioner rule of thumb is a 1-3x ATR band: **under ~0.8x the R:R usually does not survive costs; over ~3-4x the target is unrealistic for the holding period**. `projection.py` ranks candidates by confidence and confluence and never asks this question either | **small.** One function — target distance ÷ ATR — and a line on the card. **But do not let it VETO anything until it is measured**: B-116 is the study that says whether far targets actually fail more, and a filter shipped before that is another inherited rule of thumb, which is the species of claim this desk keeps disproving |
| **B-118** | **targets are never checked against the levels that actually stop price** — same audit. The desk HAS the magnets: session volume profile (POC / VAH / VAL), volume profile, liquidity pools, order blocks, prior swings from `detect_structure_chain`. **Nothing connects a projected target to any of them.** `projection.py` counts agreement BETWEEN projection methods (Elliott vs VCP vs harmonic) and never between a target and the nearest volume node or prior high. A target sitting 0.2% under a POC that has held four times is a different proposition from one in open air, and the card cannot tell the reader which it is | **medium.** The join is easy; the honest part is not overselling it — *"the nearest node is 1.1% below the target"* is a fact, while *"the target is confirmed by volume"* is a claim nobody here has measured. Ship it as DISTANCE TO THE NEAREST LEVEL, not as a confirmation score |
| **B-119** | **analog / pattern-match forward projection — the one method the desk does not have at all** — same audit, and deliberately LAST of the four. Scan history for segments that resemble the recent normalised path, take the best matches, average their forward paths, draw a mean with bands. Nothing in `tools/` does this: no nearest-neighbour search, no DTW, no analog library. `projection.py` is a CONFLUENCE of structural methods, which is a different object. **Why it is last:** it is the most seductive and the least checkable of the five — an averaged forward path from lookalike history is a shape that always looks informative, and this desk has measured three volume-profile reads and a VCP detector to nothing. **Pre-register before building**, not after: what counts as a match, how many analogs, and what beats a same-bar baseline | **medium-large, and it should not start until B-116 says whether the targets we ALREADY print are reachable.** Adding a fourth projection method while three are unmeasured is how a desk acquires surface instead of evidence |
| ~~**B-120**~~ | ~~the shared harness has no notion of a FRESH signal, and three studies have hand-rolled one~~ — **BUILT 2026-09-21, and it did NOT do what it was raised to do.** `backtest_scanner`/`walk_forward_scanner` now take `signal_mode`: **`all`** (every bar the scanner hits, de-duplicated by `min_gap` — the default, unchanged, because every published number came through it and flipping the default would silently redefine 44 verdicts) or **`fresh`** (only the bar a hit APPEARS). The mode travels with the result and prints in the header, so no figure can be quoted without it; `min_gap` is disabled under `fresh` because the transition rule already de-duplicates and skipping ahead would DROP a genuine new break inside the gap; an unknown mode RAISES rather than falling back to `all`. 6 tests. **The honest part: it was raised to explain [[#B-116]]'s control failure and it does not.** Fresh mode moved Flag & Pole from 11.0% → 11.8% target, not to B-92's 36.8%, because `min_gap` had already collapsed the runs. **The feature is still right** — a persisting state IS one signal for a plan test and arguably many for an edge test, and three studies wrote their own rule rather than use the harness — but it bought a correctness property, not the explanation | **done, and the thing it was supposed to explain is still open.** See [[#B-121]] |
| ~~**B-121**~~ | ~~`_simulate_plan` assumes the stated entry is FILLED~~ — **BUILT 2026-09-23, a real bug, and NOT the explanation it was filed as.** `resolve_fill` + `fill_model`: `assumed` (default, unchanged) · `market` (next open) · `touch` (the entry is an ORDER — above the signal close a long is a buy-stop, below it a buy-limit; gaps fill at the open, worse for stops and better for limits; shorts mirror; cancelled after 5 bars). Unfilled orders and fills through the stop are COUNTED, never simulated. 11 tests; gap direction mutation-checked. Two silent losses in `_pool_r_blocks` fixed alongside (windows with no fill dropped before their unfilled counts were summed; a pre-existing `seen = 0 … if seen else None` pooled every plans-seen-none-simulated run to None). **The control, Flag & Pole, 150 names, fresh:** assumed 10.7% / 86.0% / −0.43R · market 13.5% / 82.4% / −1.13R with **316 of 1,555 fills already past the stop** · touch 21.6% / 72.1% / +0.22R with **756 orders never filled**. None reproduces B-92, so the fill model is not the cause — but a harness that credits half its orders as filled was wrong regardless. **A suspicion of my own, refuted before it was published:** B-92's `walk_plan` uses `abs(entry − stop)`, which would score a gap-through-stop as +1R. Checked: **1 of 713** B-92 bull plans opened past the stop. B-92 stands | **done** — see [[#B-116]] for what the cause actually was |
| ~~**B-122**~~ | ~~No-Supply Screener~~ -- **BUILT + MEASURED 2026-09-23, clean negative.** Python port of simple_volume.js with bar-for-bar parity (5 symbols). Scanner `scan_no_supply`: gates on Trend/Momentum family + zero red bars + at least one pocket pivot in last 10 sessions. 3 of 24 cached symbols fire (20% gate rate across 8,580 signals). **Gate-vs-no-gate study (pre-registered, paired by symbol, Bonferroni alpha 0.05/3, floor 20 symbols):** @10d -0.118% (p=0.79), @20d +0.157% (p=0.25), @60d +0.789% (p=0.25) -- **NO DIFFERENCE at any horizon.** The supply filter selects a subset (20%) but not a better one. The scanner ships registered but unmeasured (weight 0) as a SCREEN for attention, not a trigger | **done -- clean negative, as the family itself was** |
| ~~**B-123**~~ | ~~the harness cannot test a trailing exit~~ — **BUILT 2026-09-23.** `_simulate_plan(exit_model=…)` + `backtest_scanner`/`walk_forward_scanner` pass-through, reported in the result and the report header exactly like `signal_mode`. Models: **`fixed`** (default — bit-for-bit the old path, pinned by test, so no published R moves) · **`atr_trail:k`** (Chandelier: extreme since entry − k·ATR22, Wilder) · **`ema_close:n`** · **`structure:p`** (close through the latest CONFIRMED swing low/high — the CHoCH that ends a long). Rules pinned by 18 tests: the initial stop still defines R and fires intraday; trails **only tighten**; the ATR trail on bar i is set from bars ≤ i−1, so no bar exits on a level it made; EMA/structure exits are **close-based**; swing pivots are used only once confirmed (p bars later); shorts mirror; an unknown model **raises** instead of quietly measuring the control. **The fixed target is dropped under a trail** (`target_used: False`) — capping a trail at the card's target would measure a fixed plan with a tighter stop. **Correction to this row as filed:** it said the ATR trail is close-based. It is not — once ratcheted it rests as an intraday stop, which is what Chandelier is; only the EMA and structure exits are close-based. **A silent empty caught before any number was read:** the R block counted target/stop/open/time only, so every `trail` exit would have vanished from the tallies, and `win_rate` (= target hit) reads **0% by construction** once the target is dropped. Added `trail_exits`, **`positive_rate`** (R>0 — the win rate that means the same under every exit model) and **`r_p90`** (the tail a trail exists to fatten); pooled too; a test asserts the five outcomes sum to n. A mutation check (make the trail follow the latest candidate down) fails the ratchet test, so that test has teeth. **Smoke only, NOT a result** (Falling Wedge, 25 names, fresh, 29bps): 127 plans, all 127 accounted for under each model; fixed +0.04R, ATR −0.04R, structure +0.01R, EMA +0.02R. **Do not quote these** — wrong panel, no clustering, no pre-registration. **One thing B-124 must pre-register because of it:** Falling Wedge declares a `time_stop`, and 26–39 of 127 trades ended on it under every trail model — **a card's time stop caps the very tail a trail is for.** B-124 has to state whether the time stop applies to trail arms, before the run | **done.** Harness is ready for [[#B-124]]; [[#B-121]] (fill model) is still open and still applies to every arm |
| ~~**B-124**~~ | ~~exit-model bake-off~~ — **RUN 2026-09-23 (run 2; run 1 void, see below) → NO TRAIL WINS. The prior held.** Pre-registered in `exit_model_bakeoff.py` before either run; run 2 is the registered run repeated unchanged on fixed code. 300 names, fresh signals, next-open fill, 29bps, pairs on (symbol, signal bar), per-symbol means, α = 0.05/6 = 0.0083. **Falling Wedge** (1,210 pairs, 265 symbols; control −0.005R): ATR trail **+0.13R p=0.058** · structure −0.07R p=0.19 · EMA20 −0.10R p=0.045 → **NO DIFFERENCE ×3**. **Harmonic Reversal** (793 pairs, 257 symbols; control −0.15R): ATR −0.07R p=0.40 · structure −0.10R p=0.16 → NO DIFFERENCE; **EMA20 −0.23R p=0.0003 → TRAIL WORSE**. **Read it like this:** 5 of 6 are ties, the one decisive result is a trail LOSING, and the nearest thing to a win (Falling Wedge ATR, +0.13R) misses α by 7×. The ATR trail does what a trail is for — fattens the tail (Falling Wedge r_p90 **2.0 → 2.9R**) — and pays for it in hit rate (R>0 **40% → 28%**); on these entries the two cancel. Tight close-based exits (EMA20, avg **3.6 bars** held on Falling Wedge) just cut winners, the same finding as B-8. **Caveats that stay attached:** Falling Wedge's population includes forming / pre-breakout cards ([[#B-128]]); Harmonic's fixed control is now −0.15R, not the published +0.25R ([[#B-129]]). Both caveats hit both arms equally, so the COMPARISON is fair; the absolute levels are not. **Run 1 is void** — its Harmonic 'TRAIL BETTER ×3' came from inverted plans ([[#B-129]]); kept locally as `cache/exit_model_bakeoff_run1_invalid.json` | **done.** Consequence: [[#B-125]] closes unbuilt; the chart's trail cards say *measured as an exit class: no gain* |
| ~~**B-125**~~ | ~~Statistical Trailing Stop [LuxAlgo]~~ — **CLOSED UNBUILT 2026-09-23 on its own condition.** It was conditional on [[#B-124]] showing any trail beat fixed. None did (5 ties, 1 trail worse). A better-fitted trailing distance cannot rescue an exit class that ties at best, and its in-chart performance dashboard was never evidence | **closed** — reopen only if a setup with a measured positive plan appears where a trail is the thing being tested |
| **B-126** | **Market Structure / FVG / Fibonacci trailing stops [LuxAlgo] — DECLINED as builds; all three are compositions of modules we have.** Market Structure trail = SBC swing levels ratcheted (B-123's `structure` arm covers it). FVG trail = the lowest unmitigated bull FVG from `fvg.js` as the stop. Fib trail = retracement of the latest swing from `fibonacci.js`. Each is ≤1 day on top of B-123 **if** B-124 says structure-type exits win. Sigmoid and Neighboring (k-NN) trails **declined outright** — smoothing and k-NN over one name's own history add parameters, not information, and the desk's record on added parameters is B-65 / B-59r2 | **declined, reopen from B-124's result** |
| ~~**B-127**~~ | ~~the chart draws trails without saying they are unmeasured as exits~~ — **DONE 2026-09-23, and the row as filed was one-third wrong.** **PMax needed nothing**: its card already states B-65 (the signal) AND B-74 (**its trail scored as an exit**, −0.50R vs holding) — the one trail on the chart that WAS measured as an exit, which the filing missed. **The real gap was worse than filed**: SuperTrend AI and PSAR had **no card at all** — the lines just sat under price with nothing beside them. Both now get a status card (`TRAIL_STATUS`, one place to update when B-124 reports): *as a signal* — measured, no edge, B-59r (STAI-only flips −1.00% p=0.150 n=1,909; PSAR-only −0.77% p=0.053 n=8,576, a null not a loss; agreement +0.16% p=0.820 ≈ market); *as an exit* — **never measured**. STAI's card also says its 0–10 arrow strength is scored on the chart it is drawn on, so it is not evidence. Verified in the browser: each card appears with its line and leaves with it | **done** — revisit the two strings when [[#B-124]] reports |
| ~~**B-128**~~ | ~~scanners attach trade plans to WATCH cards and the harness trades them~~ — **BUILT + RE-MEASURED 2026-09-23.** Contract: `actionable: False` keeps the levels for the reader; the harness measures the SIGNAL and counts the plan (`plans_not_actionable`) without simulating it; a missing key means actionable. Set from each card's own state on Flag & Pole (broken), Falling Wedge (confirmed), VCP Coiling (BUY / WEAK BUY / READY — READY is 'place the order'), Rounding Bottom (not WATCH), Double Bottom (not EXTENDED). **Audit test** over every registered scanner on real bars: a card calling itself WATCH / forming / pre-breakout / unbroken / approaching / awaiting / no room may not carry an actionable plan. It found VCP and Rounding Bottom on its first REAL run and fails when VCP's flag is removed. **Its first two runs were not real** — it asked for `RELIANCE.NS`, the cache holds `RELIANCE`, and it SKIPPED, which reads as a pass; B-129's property test had the same mistake. Both fixed. **Re-measured with the B-19 batch's own settings** (LIQUID_50, 3 windows, 29bps, all-mode, assumed fill — so plan R is comparable to the old files, NOT a realistic fill): share of plans that were watch-only — **Flag & Pole 826/913 · VCP Coiling 2,380/3,236 · Double Bottom 1,084/1,528 · Rounding Bottom 354/541 · Falling Wedge 121/273**. Plan R, old → actionable-only: Flag & Pole **−0.42 → +0.65R** (n=87) · VCP **−0.46 → −0.18R** · Rounding Bottom **+0.17 → +0.43R** · Double Bottom **−0.00 → +0.02R** · Falling Wedge **−0.01 → +0.02R**. Signal edges barely move, as they should: the signal side never skipped anything. **Falling Wedge split by state — the result that matters:** confirmed breakouts **+1.37% @20d, +1.98% @60d, stable at 10/20/60d (n=194)**; forming / pre-breakout **−0.27% @20d (n=132)**. The published +0.74% was a DILUTION of a stronger, cleaner edge. **Its measured tier stands and is better supported than before.** **Caveat:** Double Bottom has 71% of its plans flagged EXTENDED — plausible for a detector that keeps reporting a completed pattern, but worth a look before anyone reads its +0.02R | **done.** Every other scanner without the key is unaffected by construction; the audit guards the next one |
| ~~**B-129**~~ | **Harmonic Butterfly/Crab plans had the stop on the profit side** — FIX BUILT 2026-09-23 (stop beyond the more extreme of X and D; property test on real bars, which now actually RUNS — see B-128), plus harness guards (target on the stop side is degenerate; fill past the target is counted). **RE-MEASURED 2026-09-23, and the tier's evidence does not survive it.** The harness's signal edge scores every hit as a LONG — it does not read `direction` — so bearish Harmonic patterns (a SHORT thesis) have always been inside the long edge. Split with the B-19 settings: **bullish only +1.07% @20d, UNSTABLE at every horizon** (2 of 3 windows positive, one at −0.82%; n=116) · **bearish patterns scored as longs +0.72% @20d** (n=145): after a bearish Harmonic the stock ROSE, so the short thesis FAILS, exactly as Inverted Flag & Pole did in B-92. The pooled **+0.88%** that keeps Harmonic in `MEASURED_EDGE_SCANNERS` is a failing short thesis averaged with an unstable long one. **Plan R is still not known.** Under the B-19 settings (assumed fill) the fixed plan reads +1.21R, which is the stale-fill case B-121 exists for — the entry is the D price, up to 10 bars old. Under next-open fill + fresh signals (B-124 run 2) the same scanner's fixed plan was **−0.15R**. **OWNER DECISION, not made here:** the evidence says Harmonic no longer meets 'measured to beat random entry'. Recommended: demote to the weak tier (0.25) and scan bullish patterns only, as the Inverted Flag & Pole precedent did; the `opportunity_hub` comment now states this instead of the old +0.67% / +0.25R **DECIDED 2026-09-23 by the owner: demoted to the weak tier (0.25), bullish patterns only.** `scan_harmonic_reversal` now returns None for bearish patterns (the chart's harmonic overlay reads the detector directly and still draws both); `opportunity_hub` moves it from `MEASURED_EDGE_SCANNERS` to `MEASURED_WEAK_SCANNERS`; the registry description says bullish-only and measured weak. Tests pin both. **Falling Wedge is now the desk's only measured-edge scanner** | **done.** Re-earning a higher tier needs a bullish-only re-measure that is stable across windows, on next-open fills |

| **B-130** | **Stock Summary Card on Predictive Analysis — 52-week context + detected patterns** — a single card per selected symbol, composed from pieces already computed. **Three layers:** (1) **52-week range bar** — `rs.range_spectrum(lo52, hi52, price)` already exists on the Stock Analyzer page (line ~2474), with Sup/Res ticks and a "−X% from high" chip; reuse the call, not the code. (2) **Stage analysis** — `score_minervini(df, nifty_df)` already returns the 8 conditions and a count; display as "Stage-2 ideal band" or equivalent label derived from the count + 52w position. (3) **Detected patterns** — query `scanner_run_cache` for the selected symbol across ALL scanners from the latest run date (not just the one the left panel loaded), render each `pattern_type` as a coloured chip. `db.get_saved_scanner_hits()` can supply the persisted hits too. **What already exists:** `rs.range_spectrum`, `sp.score_minervini`, `sp.score_technofunda`, `scanner_run_cache` table, `_rating_badge_html`. **Build:** one `_render_stock_summary_card(symbol, df, nifty_df)` function called from the `pa_main` block in Predictive Analysis, placed above `render_chart_tool`. No new data, no new computation — pure assembly | **small.** Reuse from Stock Analyzer; the only new code is a pattern-chip query and a card layout |
| **B-131** | **Smart Money Flow card on Predictive Analysis — accumulation vs distribution, OBV trend, CMF** — a per-symbol institutional-flow card, composed from existing modules. **Four components:** (1) **Session flow bar chart** — classify each of the last 60 sessions as accumulation (close > open AND volume > avg) / distribution (close < open AND volume > avg) / neutral, render as a coloured bar strip (green/red/grey). The classification is simple close-vs-open + volume, not a new indicator. (2) **Verdict label** — majority count → "Strong accumulation" / "Mild accumulation" / "Neutral" / "Mild distribution" / "Strong distribution". (3) **OBV trend mini-chart** — `df["close"].diff().apply(np.sign) * df["volume"]` cumulated. The desk has no OBV computation yet (the wiki page [[concepts/On-Balance-Volume]] exists, no code); add `obv(df)` to `money_flow.py` beside `cmf()`. (4) **CMF reading** — `money_flow.cmf(df, n=21)` already exists and is tested. Display as `CMF 0.037 · X acc · Y dist`. **What already exists:** `money_flow.cmf()`, `smart_money.smart_money()` (Layer 4, uses block deals + OI — this card is the SIMPLER read from price/volume alone, complementary not competing). **Build:** `obv(df)` in `money_flow.py` (~5 lines), one `_render_smart_money_flow_card(symbol, df)` function, placed below the stock summary card on `pa_main`. The session-flow strip is a miniature HTML/SVG bar chart inline, similar to the RS-walk sparkline pattern. **Honest caveat on the card:** "Session flow is a bar-level heuristic (close vs open + above-average volume) — it is NOT the same as institutional delivery data and has not been measured against forward returns" | **small-medium.** `obv()` is trivial; the session classifier is ~15 lines; the rest is layout |

### OWNER — a judgement, not a task

| # | The decision |
|---|---|
| **B-73** | the contra-theme **cadence** |
| **B-4 / B-12** | AVWAP click-to-anchor — verified no anchor UI exists. Anchor choice is the subjective half of AVWAP; how much UI is worth building is yours |
| **B-26** | `MIN_PRICE_PCT` is **0.5 against a 0.90 median** — far more permissive than its own comment claims. Deliberately unchanged, because moving it re-grades the whole universe. Decide it on purpose rather than by inheritance |
| **B-34r2** | whether the red-flag veto is ON by default (it vetoes **100 of 249** on Smallcap-250) |
| **B-84r** | retire or document the third app — the candidate is named in [[#B-84]] |
| **B-42r** | which `pivot_len` IS "structure" — 5 (scanners) or 15 (chart). Measured 2026-09-17 at **29.6% agreement on `state`**, with 17.6% of names reading *opposite* directions. Cannot be unified quietly: it re-grades most names |
| **B-30 / B-31 / B-35** | parked by choice; unpark or drop |
| **P2 four** | B-4/12, B-6, B-8, B-9 were "schedule one or mark deferred" as of the design review. **B-8 and B-9 are now scheduled — they are in MEASURABLE NOW above.** |

> [!warning] A specification this page lost
> **B-8 and B-9 were described here as "both fully specified"** — and they were
> not. Both were reduced to a bare heading with one shared sentence under them;
> the actual specifications (the Connors-vs-ForexTester contradiction, the
> 2-consecutive-30-min-bar traverse claim) survived only in the superseded
> [[analyses/Open-Backlog-2026-08-02]] snapshot. **A living page that supersedes
> a snapshot inherits the duty to carry its content**, and this one dropped two
> specs on the way. Restored below, in their own entries.
>
> This is the same failure the page already documents about itself, one level up:
> it re-verifies STATUSES against code and never re-verified that its own
> BODIES survived the migration.


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
| ~~7~~ | ~~**Fib rungs are drawn, not wired**~~ — **SETTLED 2026-09-11** by B-58's FAIL: the geometry they serve does not beat a plain support retest, so neither becomes a `buildPlan` default and **they stay drawn on purpose**. Code re-verified unchanged 2026-09-19, which is the settled state, not an open one | `fibonacci.js` | 0.886 and 1.13 exist as levels but do NOT feed `buildPlan`: 0.886 is entry-ineligible without `{deepEntry:true}`, and 1.13 never becomes the stop. Adopting either changes reward-to-risk — and therefore the `actionable` flag — on plans unrelated to QM. **Changing what a stop means is a measurement, not a default.** |

> [!note] The one thing worth carrying forward from this session's method
> Twice, counting BEFORE measuring saved a week. `renko_quality_cardinality.py`
> killed the 40% correction cap by showing 96% of flips clear it, and the QM
> detector's first version reported a "pattern" on 73% of names until the pivots
> were required to be consecutive. **A filter that admits almost everything is not
> a filter, and that is cheaper to discover by counting than by backtesting.**

**Status of that table on 2026-09-19:** rows 2, 3, 6 and 7 are closed or
settled; **rows 1 (chart-server restart), 4 (B-57 secondaries) and 5 (B-58
residual · multi-timeframe liquidity) are still open and untouched**, all three
re-verified this pass.

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
> [!note] Superseded — history, not a list
> Kept for its reasoning and its "not promoted, and why" notes. The current
> ranking is [[#Ranked, after the corrections]]. Do not pick work from the
> ranked table below: B-10, B-17, B-58, B-22 and the Fib rungs in it have all
> since closed or settled.

Ranked by *what the desk cannot currently answer*, not by size. No new items were
invented in this pass; this is the existing page, sorted.

| Rank | Item | Why it is next | Cost |
|---|---|---|---|
| 1 | **B-58 · run the QM measurement** | The only BUILT-but-UNSCORED detector on the page. `detect_quasimodo` + 17 tests exist, the pre-registration and its control are written, and the skeptical prior (*"QM is a liquidity sweep with extra steps"*) is recorded. Leaving a built detector unmeasured is precisely the debt B-19 was raised over. | One measurement run |
| ~~2~~ | ~~**B-59 · PSAR overlap check**~~ — **DONE 2026-09-10.** It did NOT close on overlap — PSAR is a superset at 8.4× PMax's cadence — and the edge test this row said was "now owed as its own item" **was run the same session as [[#B-59r]]: both twins NEGATIVE on their unique cells. Nothing further is owed.** *(row corrected 2026-09-11)* | Cheap, and it is a **gate**: if PSAR's flips are a subset of `pmax`/`stai`, every downstream PSAR idea is dead and no edge test is owed. An overlap count, not a backtest — the counting-first method that saved a week twice in the 2026-09-07 session. | Hours |
| ~~3~~ | ~~**B-22 · wire sentiment factor 5 (PCR)**~~ — **DONE 2026-09-11.** It shipped NOT_CHECKED by construction (no index-PCR baseline existed, so the wiring also had to start storing one) and therefore changed today's score by zero. What it created is a new debt: the sign convention is unmeasured, and B-44r is the reason that is not a footnote | Now the cheapest real capability on the page: `pcr.py` is built, calibrated and already consumed three times in `dashboard_app.py`; `sentiment_index.py` still runs on four weighted factors (30/25/25/20) and documents the fifth in a docstring. Wiring, not a build — and it re-weights a number the desk already shows. | Small |
| 4 | **B-10 · one symbol, `BSE`** | Was a four-symbol systematic-bug suspicion; it is now a single name. Close it or retire it — a one-line item that has survived five weeks of re-verification costs more to re-read than to fix. | Minutes |
| 5 | **B-17 · OBV concept page** | Two OBV surfaces now ship (the indicator + B-61's divergence overlay) and neither is documented. B-60 wrote its CMF page with the build; this is the same debt, already incurred. | Small |
| — | ~~**B-67 · Top Losers**~~ — **RAISED AND CLOSED 2026-09-11** by the owner spotting dubious figures on the running dashboard. Was a change-basis BUG (first 5m candle, not the previous close), not a measurement gap; fixed, then measured to a clean null on 1,215 sessions. **The lesson is the order:** backtesting it first would have measured the bug | Done |
| 6 | **B-57 secondaries** | Explicitly pre-registered as non-decisive (60d horizon, top-quartile OCF gate, `depth_from_flip`) — they describe rather than rescue. Do them only if a session has slack. | Small, low value |

**Not promoted, and why:** B-35 (family lenses) is measured and ready, but it is a
UI change over 38 scanners that **B-19 found mostly have no edge after costs** —
reshaping the presentation of an unproven set is motion, not progress. B-31
(learned confluence weights) stays parked behind B-25, whose own answer was that
confluence is *not* the additive swing-horizon edge the Hub premise assumes. B-30
(Pushya) is worth running only to retire it, and the desk already holds three
astro nulls.


## Refinement pass 2026-09-11 — re-verified against code, and one item was owed to itself
> [!note] Superseded — history, not a list
> Kept for its correction narrative and the B-22r result in full. The current
> ranking is [[#Ranked, after the corrections]]. **Its adjudication of B-59r2
> is the one still live** — it struck the PSAR unique-cell debt as discharged,
> and the 2026-09-17 table re-raised it; see [[#Re-verification 2026-09-19]].

Same method as 2026-09-10: every item ranked below was re-read against the
**code**, not against the previous pass. Nothing new was invented. What follows is
what changed in one day, what is genuinely next, and one correction.

**The correction, and it is the fastest drift this page has recorded.** The
2026-09-10 ranked table says of B-59: *"an edge test on its unique cells is now
owed as its own item."* That edge test is **[[#B-59r]], and it was run in the same
session** — both twins NEGATIVE on their unique cells, agreement ≈ market. The
debt was discharged roughly an hour after it was written down, and the line
claiming it was owed survived anyway. Previous passes explained drift by *"an item
is only re-read when it is worked"*; this one does not fit that rule — it drifted
**inside** the worked set, because the summary table and the item body were
written at different moments and only the body was updated. **Ranked tables that
paraphrase item bodies are a second source of truth, and they go stale faster than
the bodies do.** Row 2 of that table is struck below; no further PSAR edge test is
owed.

### Re-verified 2026-09-11 (what was actually checked)

| Item | Claim on the page | Verified against | Verdict |
|---|---|---|---|
| **B-45** (ATR/MFI not plottable) | "Neither appears in `INDICATOR_DEFS`" | `INDICATOR_DEFS` at [chart_dashboard.html:1285](tools/chart_dashboard.html:1285) — **48 keys**, no `atr`, no `mfi` | **Open, accurate** |
| **B-46** (Ichimoku) | "absent from `tools/` entirely" | only hit for `ichimoku` repo-wide is a *comment in* `tools/psar.js:14` citing B-46 itself | **Open, accurate** |
| **B-47** (TPO) | absent | no TPO source outside vendored `breakout_scanner` bundles | **Open, accurate** |
| **B-10** (uncached symbols) | "only `BSE`" | `tools/cache/ownership/` — **751 files**, no `BSE*` | **Open, unchanged since 09-10** |
| **B-17** (OBV concept page) | absent | `wiki/concepts/` still has no OBV page; two OBV surfaces ship | ~~Open~~ — **CLOSED 2026-09-11** |
| **Fib rungs** (row 7, 09-07 table) | drawn, not wired | [fibonacci.js:85-96](tools/fibonacci.js:85) — `DEEP_RETRACEMENT` 0.886 still gated behind `{deepEntry:true}`, 1.13 still only in `OVERSHOOTS`, never a stop | **Open, accurate** |
| **B-22** (PCR factor) | "four factors 30/25/25/20" | `sentiment_index.py` now documents **five** at 25/20/20/15/20 | **Closed 2026-09-11** |

Six of seven bodies were accurate. That is a better hit-rate than any previous
re-verification pass on this page, and the reason is visible: those six have not
been touched, so nobody has had the chance to desynchronise a summary from them.

### New item raised by this pass

#### ~~B-22r~~ · The PCR factor's sign convention is unmeasured — **MEASURED 2026-09-11: NULL, and the factor lost its vote**
B-22 shipped `NOT_CHECKED` by construction — no index-PCR baseline existed, so the
wiring had to *start storing* one, and it changed today's score by zero. That is
the honest way to ship it. But it leaves a live claim in the code: **factor 5
asserts a direction** (which way a PCR level and slope should push sentiment) and
that direction has never been scored. [[#B-44r]] is why this is not a footnote —
GEX was retired precisely because the naive convention turned out to be backwards
for NSE, and PCR is the same *shape* of assumption made by the same reasoning. The
factor carries weight 20 of 100.

**Cost:** blocked on data, not on thinking. The baseline began accumulating
2026-09-11, so the earliest defensible measurement is whenever the stored series
is long enough to percentile against — this item's first action is to write down
**how many sessions that is, and pre-register the test now**, while the
convention's author is still in the room. Do not let it ship unmeasured into a
score the desk reads daily.

---

**CLOSED 2026-09-11. Full design and result:
[[analyses/PCR-Sign-Convention-Pre-Registration]]** (pre-registration committed
BEFORE any measurement code was written, deliberately, so the order is on the
record).

> [!key-insight] The blocker was false, and finding that out cost twenty minutes
> This item was filed as *blocked until December* — `MIN_PCR_HISTORY = 60`, and the
> baseline had just started filling. But `_download_bhavcopy(session, day)` takes an
> **arbitrary date** and NSE's F&O archive is date-templated, so the baseline was
> **backfillable all along**. `tools/pcr_backfill.py` pulled **543 sessions back to
> 2024-07-03** in one run. **Three months of waiting turned out to be a property of
> the assumption, not of the data** — the same lesson as the 2026-09-07 session's
> counting-first saves, arriving from a different direction.

**The measurement: NULL.** 483 point-in-time scored sessions (floor: 200), decision
horizon 5d, top-vs-bottom tercile of the 70/30 blend: **+0.135%, p_boot 0.583**.
Planted-effect control detected at p=0.0002 and the shuffle was unremarkable, so the
detector could see and still found nothing. **Not the B-44r outcome** — the shipped
trend-following sign is not backwards, it is merely unsupported, so there is nothing
to flip.

**And this time the null cost the factor its vote.** `PCR_SCORES = False`: factor 5
is computed, reported and recorded, but **excluded from the composite**, with the
other four weights renormalising to 100 — exactly what the module already does for a
stale sector feed. That consequence was fixed in the pre-registration before the
number was known, which is the only reason it happened: **B-66 measured four
sentiment factors as non-discriminating on 2026-09-10 and not one of them was
re-weighted.** This is the first null on this page that actually changed what the
desk scores.

The 1d cell came in at p=0.044 and is **reported, not promoted** — one of twelve
tested, pre-registered as non-decisive, and smaller than the cost of trading it.

**What the desk keeps from a null:** 543 cached sessions, so the next PCR question
starts with two years of history instead of a three-month wait; and one fewer
unmeasured assertion inside a number that gets read daily.

### What is next, ranked

| Rank | Item | Why it is next | Cost |
|---|---|---|---|
| ~~1~~ | ~~**B-45 · wire ATR + MFI into `INDICATOR_DEFS`**~~ — **DONE 2026-09-11**, 48 → 50 indicators, with a parity test that found 1,333 zero-volume NIFTY bars | Both series already exist and are already computed; 48 indicators are reachable and these two are not. **No backtest is owed** — exposing an existing series makes no claim about edge — which makes it the only item on the page that is pure progress with zero measurement debt attached. ATR is also the series stop-sizing actually needs. | Hours |
| ~~2~~ | ~~**B-22r · pre-register the PCR sign test**~~ — **DONE 2026-09-11: pre-registered, then the "blocked until December" premise collapsed (the archive is backfillable), so it was also MEASURED — NULL, and factor 5 now scores zero** | New, and it is a *clock* item: the pre-registration is worth more written today than written correctly in six weeks. Weight 20 of the sentiment score rests on an unmeasured direction, and B-44r is the precedent for that being backwards. | Small now, blocked later |
| ~~3~~ | ~~**B-58 · decide QM's fate**~~ — **DONE 2026-09-11: widened the window, found the 2026-09-10 verdict was an artifact of `max_swings=15`, re-ran at 5,048 events — FAIL (−0.64%, p=0.120). QM stays geometry** | 53 events against a pre-registered floor of 200 is **inconclusive, not null** — and an inconclusive result is the one outcome that does not retire an item. Either extend the universe/era to reach the floor, or retire QM on the recorded prior (*"a liquidity sweep with extra steps"*). Leaving it inconclusive is the worst of the three. | One decision, then maybe one run |
| ~~4~~ | ~~**B-10 · `BSE`, one symbol**~~ — **CLOSED 2026-09-11: a hardcoded XBRL namespace prefix, not the symbol filter. 751 → 752 cached** | Third consecutive pass carrying a single-symbol item whose diagnosis ("probably our bug") is now weak — 1 of ~1,500. Check whether the exchange files under a different NSE symbol string, then close or retire it. **It costs more to re-read than to fix.** | Minutes |
| ~~5~~ | ~~**B-17 · OBV concept page**~~ — **DONE 2026-09-11**, [[concepts/On-Balance-Volume]]. Unchanged from rank 5 last pass. Two shipped surfaces, zero pages; B-60's CMF page is the pattern. | Small |
| ~~6~~ | ~~**Fib rungs (0.886 / 1.13)**~~ — **SETTLED 2026-09-11 by B-58's FAIL: the geometry they serve does not beat a plain support retest, so neither becomes a `buildPlan` default. They stay drawn** | Unchanged and correctly parked: adopting either changes reward-to-risk and therefore the `actionable` flag on plans unrelated to QM. **Changing what a stop means is a measurement, not a default** — so this is gated behind B-58's decision, not independent of it. | Measured, not small |

**Not promoted, and why (unchanged from 2026-09-10):** B-35, B-31 and B-30 stay
where they were, for the reasons already given — no new evidence arrived this pass
to move them.

**The shape of the backlog has not changed.** Last pass's summary was *"the desk
builds faster than it measures"*; this pass adds a second: **the desk summarises
faster than it re-reads.** B-45 is ranked first partly because it is the rare item
that adds a capability without adding to either debt.

## B-68 · Liquidity Sweep had a measured edge and no way to see it — **BUILT 2026-09-11**

Raised by the owner asking a one-line question: *"do we have any indicator for
liquidity sweep by signal"*. The answer was **no**, and checking it turned up a
worse problem than the missing overlay.

**The state before:** `detect_liquidity_pools` + `detect_liquidity_sweep` and two
registered scanners (`Liquidity Sweep` Entry, `Liquidity Sweep Bear` Risk) — but
**no `INDICATOR_DEFS` key**, so the one SMC component with a measured edge was the
one you could not see on a chart. The only chart-side mentions of "sweep" were
plain-English phrasings used to render scanner text.

> [!warning] Found on the way: EVERY remaining "Unmeasured." label in the scanner
> registry was stale
> Both liquidity-sweep descriptions ended with the word **"Unmeasured."** — for the
> scanner B-41m measured at **+0.51% @20d (p=0.005) net of costs**, the only one on
> this desk whose edge survives them. Cross-checking the other eight against
> `cache/b19_verdicts/` found **all eight were stale too**: RSI Divergence
> Bull/Bear, RSI-Fibo Hidden, %R Exhaustion Sell, %R Bottoming, FVG Pullback, ICT
> Setup, Support Breakdown. B-19 measured every one of them on 2026-09-02 and
> nobody updated the text.
>
> **`claims_lint` cannot catch this by design** — it deliberately does not match
> bare "unmeasured", because this repo uses that word as a legitimate state label.
> The stale-claim class it misses is *a state label that was true when written and
> silently became false*. All ten now carry their actual verdicts.
>
> The worst single case was **Support Breakdown**: a Risk flag whose measured
> result is **+0.47% @20d / +1.22% @60d — it points the WRONG WAY**, and its
> description said only "Unmeasured."

**The overlay.** `/api/liquidity` → the SAME `detect_liquidity_pools` /
`detect_liquidity_sweep` the scanner fires on; **nothing recomputed in JS**, so the
zones drawn and the scanner's hits cannot disagree. Pools draw as dashed price
lines labelled `buy-side x3` / `sell-side x5` (touch count IS pool strength), the
swept level draws solid orange, and the sweep itself gets a direction-aware arrow.
`INDICATOR_DEFS` 50 → 51.

**Drawn with price lines rather than a canvas, deliberately:** a pool IS a
horizontal level, price lines cost nothing on pan/zoom, and they cannot repeat the
1×-into-2× snapshot bug that the canvas overlays needed `sizeOverlay()` to fix.

> [!key-insight] The browser caught a bug no unit test would have
> First render put the SWEEP arrow at 1279.45 on RELIANCE — **a level with no line
> under it.** `detect_liquidity_pools` returns the strongest `max_pools` (6) levels
> while `detect_liquidity_sweep` searches its own `lookback`, so **the raided pool
> can legitimately fall outside the top six.** The swept level is now always drawn,
> whether or not it survived the pool cap. An arrow pointing at nothing is worse
> than no arrow.

**No backtest owed.** Drawing an already-measured detector makes no new claim — the
same reasoning as [[#B-45]]. What the overlay must NOT be read as is a plan:
B-41p measured the shipped entry/stop/target at **−0.06R** against **+0.50R** for
the same signal held 20 days with no stop. The signal is measured; the stop is a
known defect, and both facts now travel in the scanner description.

**Operational note:** `chart_server.py` serves each module from an explicit Flask
route and runs without the reloader, so a server started before this commit returns
404 for the new route. Verified on a second instance (`--port 5002`), which is what
that flag exists for; the live 5001 instance needs a restart to pick it up.

## B-69 · `claims_lint`'s blind spot — a state label that silently went false — **CLOSED 2026-09-11**

Raised by [[#B-68]], which found **ten** scanner descriptions claiming
"Unmeasured." after B-19 had measured every one. `claims_lint` could not see them,
**by design**: its own header explains that bare "unmeasured" is NOT matched because
this repo uses it as an honest state label and flagging it returned ~40 correct
lines. *"A lint that is mostly right is one you learn to skim."* That reasoning was
correct and still is.

**What it missed is that the label is CHECKABLE when its subject is a named
scanner**, because `cache/b19_verdicts/` is ground truth: a verdict file exists if
and only if B-19 measured that scanner. No vocabulary heuristic, no context window,
no judgement — a name either has a verdict or it does not. CHECK 0 now reports those,
with the B-19 summary row attached so the fix is a paste rather than a hunt.

> [!key-insight] Two bugs in the new check, and the SECOND one is the lesson
> **1. The regex matched nothing.** `` written through a shell heredoc became a
> literal **backspace byte** (``); the pattern compiled fine and matched
> nothing. **This repo has hit that exact bug before** — the 2026-09-06 log records
> it for `un-?backtested`, in this same file. Caught here only because a test
> asserted the positive case.
>
> **2. The check was INERT on the only file it guards, and looked like a pass.**
> The walk handled `ast.Assign`, but the real registry is written
> `SCANNERS: dict[str, dict] = {` — an **AnnAssign**. It parsed **zero** descriptions
> from `scanner_templates.py`, printed "(none)", and that is indistinguishable from
> success. The synthetic test fixture used a plain `SCANNERS = {` and passed happily.
>
> **A check that reports nothing looks exactly like a check that is working.** Both
> the MFI parity test (B-45) and this one needed a *vacuity guard* before their
> silence meant anything, and that is now the third time this session the same
> shape has appeared — after B-58's equivalence check, which agreed because both
> sides shared a bug.

**It immediately found two more that the manual sweep of B-68 missed** — `HM Buy
(Hilega Milega)` (**+0.63% @20d**, 3,442 signals, the largest count in the batch)
and `Bearish Reversal Candle` (−0.46% / −0.82%). Both escaped a hand grep for
`Unmeasured."`: one is lowercase mid-sentence after a semicolon, the other is
followed by an em-dash. **The lint beat the human pass on its first real run**,
which is the argument for it.

**Scope, stated so it is not mistaken for complete:** this cross-references
`cache/b19_verdicts/` ONLY. A scanner measured by a NAMED STUDY leaves no file
there — `Liquidity Sweep` is measured by B-41m and has no verdict file, so its stale
label had to be found by hand in B-68. Extending this to named studies needs a
machine-readable index of them, which does not exist yet.

`tools/test_claims_lint.py` (9 tests) proves the positive case on synthetic input,
pins the two correct-silence cases, and guards the vacuity.

## B-70 · `Support Breakdown` retired — a risk flag that pointed the wrong way — **2026-09-11**

Surfaced by [[#B-69]]'s new lint check and decided by the owner. B-19 measured it at
**+0.47% @20d / +1.22% @60d on 2,880 signals**: a RISK flag whose flagged names went
**UP** on average.

**What the harm actually was, since it is not the obvious one.** It never *voted* —
risk scanners are excluded from confluence by construction, so it was never adding
weight to a shortlist. But it was **DISPLAYED as a bearish warning on shortlisted
names**, and a warning with no support steers a reader away from names that
outperformed. *A flag is a decision input even when it is not a vote.*

**Retired the way [[#B-44r]] retired GEX: removed as a decision input, kept as a
view.** `opportunity_hub.PIPELINE_EXCLUDED` now contains it, so the pipeline does not
run it and no flag is shown. It stays **registered, runnable in the Scanner Hub and
backtestable** — the standing rule that nothing is deleted on a measurement still
holds.

> [!warning] The evidence is weaker than GEX's, and the record should not pretend
> otherwise
> B-44r's GEX inversion was significant (p_rot 0.004–0.042 with controls). This
> verdict is **"NO BEARISH EDGE [UNSTABLE]"** — *not sign-stable across walk-forward
> windows*. So the honest reading is **"the bearish claim has no support"**, not
> "it is significantly inverted". That is still sufficient to stop displaying the
> warning — a flag needs positive evidence to earn a place on a card — but it is not
> the same finding, and the description says so.

**One subtlety worth recording, because the obvious cleanup would make it worse.**
It stays in `RISK_SCANNERS` even though it is also in `PIPELINE_EXCLUDED`, and the
overlap is deliberate: the exclusion stops the pipeline *running* it, while
`RISK_SCANNERS` is what `scanner_tier()` reads to colour it. **Removing it from
`RISK_SCANNERS` as dead config would re-classify it as an unmapped non-risk scanner
— which counts as "a family of one" — turning a discredited BEARISH flag into a
BULLISH confluence vote.** A test asserts it stays.

`tools/test_support_breakdown_retired.py` (6 tests) pins the exclusion, the continued
registration, the tier, that un-retirement trap, and the description.

## B-71 · The named-study index — closing [[#B-69]]'s stated scope gap — **BUILT 2026-09-11**

B-69 taught `claims_lint` to catch a scanner claiming "Unmeasured." while
`cache/b19_verdicts/` held its result, and recorded its own limit: **that only works
for the B-19 batch.** Every other measurement leaves nothing on disk linking a
subject to a finding. B-41m measured `Liquidity Sweep` at +0.51% @20d **through the
shared harness** and wrote the result into this page as prose — which is exactly why
both liquidity-sweep descriptions sat stale for five days and a human had to find
them.

`tools/named_studies.py` is that missing link: **subjects → the study that measured
them**, for the measurements outside the batch. CHECK 0 now consults both sources.

> [!key-insight] It is an INDEX, not a results database, and the distinction is the
> whole design
> The authoritative numbers stay in the backlog entry each record points at.
> `headline` is one optional line and `verdict` is a five-value label
> (POSITIVE / NEGATIVE / NULL / INCONCLUSIVE / MIXED). **Restating full results in the
> index would create a second place for a figure to go stale**, which is the failure
> this whole tool exists to reduce — it would have been a lint that rots.

> [!key-insight] The property that stops the index itself rotting
> `uncovered_tools()` lists every `*_study.py` / `*_backtest.py` in `tools/` that no
> entry claims, and the lint reports it as **CHECK 0b**. **A new study file is a lint
> finding until it is indexed.** The index cannot quietly fall behind, because the
> tree tells on it.
>
> That matters more than the seed set. An index maintained by discipline decays; one
> that reports its own gaps does not.

**Seeded with 11 entries and 14 declared gaps, deliberately.** Entries were written
only where the mapping was verified against this page in the same session — B-41m,
B-41p, B-57, B-58, B-22r, B-44, B-44r, B-66, B-59r, B-67, B-34. The remaining 14
study files are **listed as coverage gaps rather than guessed at**, which is the
honest state and is visible every run.

**COMPLETED 2026-09-11: all 14 gaps indexed, coverage is now zero.** Working
through them turned up something the index had no vocabulary for.

> [!key-insight] Four studies ran and left no write-up — the stale-claim disease,
> inverted
> `funnel_backtest.py` (B-38), `sbc_backtest.py`, `sbc_muhurat_backtest.py` and
> `newmoon_levels_backtest.py` all exist as measurement tools, and **none has a
> result recorded anywhere this index can cite.** The backlog, the wiki pages and
> their own docstrings state the question and the null hypothesis; **no page states
> what came back.**
>
> That is the same failure as a stale claim seen from the other side: **a claim that
> outlived its measurement vs. a measurement that never became a claim.** Both leave
> a reader trusting something nobody checked.
>
> They are indexed as **`UNRECORDED`** rather than guessed at — the mapping
> (tool → subjects) is what CHECK 0 needs, so their subjects stay checkable either
> way, and a labelled gap is worth more than a fabricated verdict. **CHECK 0c
> reports them every run**, because a measurement with no write-up is debt and debt
> that is not displayed does not get paid. Each should gain a source with real
> numbers or be retired; what it must not do is sit in the index looking measured.

The other ten were verified against their own write-ups first: **B-43** and
**B-43r** (Renko), **B-32** (the regime-gate premise), **B-55** (SVP composite),
**ADX** (mixed — the bare DI cross **loses** at −0.93% @10d while the confirmed
state is +1.82% @60d), the **FVG fill-rate** study (gaps are **not** magnets against
a width-matched placebo), **evmacd**, **FA-2** rahu-kaal and hora, and the **SBC
daily-vedha** negative.

Tests: `test_claims_lint.py` grows to 17 — coverage must stay complete (a new study
file now FAILS a test rather than waiting to be noticed), every `UNRECORDED` entry
must stay reported, and an `UNRECORDED` study must still make its subjects
checkable — including the motivating case — a scanner
with **no** verdict file that the index still catches, asserting the finding names
B-41m — and the guard that an unindexed, genuinely unmeasured scanner stays silent.

## B-72 · A BUY signal on the liquidity-sweep overlay — **BUILT 2026-09-12**

Owner asked whether the sweep overlay ([[#B-68]]) could carry a buy/sell signal. It
can, and the measured evidence makes the answer **asymmetric** — which is the whole
design.

**BUY, bullish side only.** `/api/liquidity` now returns the plan
`scan_liquidity_sweep` already emits — **the scanner's own, not a second plan
invented for the chart**. That matters for the same reason the pools are not
recomputed in JS: one definition, one place to be wrong.

**No SELL signal, and that is evidence rather than taste.**
`scan_liquidity_sweep_bear` is a RISK read whose B-41m arm **never reached
significance** (−0.16 / −0.18 / −0.32 / −0.56% gross, p 0.11–0.063) and which emits
**`target=None`**, so no R can be computed for it at all. A SELL arrow would be a
plan nobody measured. A test pins that reasoning and says what would justify
revisiting it.

**The signal is gated on the SCANNER firing, not on a sweep existing.**
`scan_liquidity_sweep` requires the sweep to be ≤ 3 bars old, so an older sweep keeps
its arrow as CONTEXT and gets no plan. **The difference between "this happened" and
"act on this" is the gate**, and the marker reflects it: `BUY · SWEEP 320 · wick 85%`
when fresh, plain `SWEEP 5153 · wick 56%` when not. Verified live on both cases.

> [!warning] The stop is drawn with its own measurement on the label
> B-41m measured the SIGNAL at **+0.51% @20d (p=0.005) net of costs**. B-41p measured
> **this exact entry/stop/target at +0.06R**, and found the cause is that a stop
> exists *at all*, not where it sits — removing it turned −0.059R into **+0.504R**.
>
> So the stop line's axis label literally reads **`stop · B-41p: this plan returns
> +0.06R`**. Drawing a clean stop with no caveat would have shipped, as a chart
> recommendation, a plan this desk has already measured to return nothing.
>
> That is NOT a licence to trade it unstopped: arm C's downside is uncapped where a
> stopped arm loses at most 1R. A better mean with an unbounded tail is a different
> risk profile, not a better one.

**No new measurement is owed** — nothing new is claimed. The event was measured, the
plan was measured, and both numbers now travel with the pixels that draw them.

## B-73 · "Ultimate All-In-One (Cash Segment)" contra theme — **SCOPED 2026-09-12, NOT STARTED**

Owner's ask, verbatim in intent — a single cash-segment contra pipeline delivering:

1. one separate pipeline for **Multibagger Investing Frameworks**
2. **1–2 Momentum & Swing ideas daily**
3. **1–2 Smallcap Opportunities every month**
4. **SME Opportunities**

Scoped the way [[#B-58]] was: audit what already exists BEFORE proposing a build,
because three of the four are mostly assembly and the fourth is blocked on data.

### Coverage audit — what the four asks already have

| ask | what exists today | state |
|---|---|---|
| **1. Multibagger framework** | `multibagger_candidates.py` — early-stage small/mid-cap screen on fresh institutional conviction + capital efficiency | **built, and UNMEASURED** — no B-19 verdict file, no named study, no reference to a backtest anywhere in the module |
| **2. Momentum & swing daily** | `opportunity_hub.py` (funnel, families, confluence, weights) + `opportunity_daily.py` (scheduler job, persists to `daily_opportunities`) | **built and running daily** |
| **3. Smallcap monthly** | `smallcap_universe.py` (free NSE small/micro universe the Hub's traded-value funnel structurally cannot see) + `smallcap_discovery.py` (B-34 conviction scorer) | **built, MEASURED WEAK** (B-34), gate shipped 2026-09-05 |
| **4. SME** | nothing | **genuine gap, and blocked twice over — see below** |
| *contra framing itself* | [[analyses/Contra-Strategy-Roadmap]] + `value_screen.py`, `contra_inflection.py`, `volume_anomaly.py` | built; the roadmap's own **Phase 0** says measurement debt blocks everything |

**So the honest shape of this theme is: one unmeasured screen, one working daily
pipeline, one measured-weak monthly lane, and one real gap.** It is not four builds.

### The SME ask is blocked twice, independently

> [!warning] Neither blocker is a matter of effort
> **1. SME is in no universe this desk builds.** `smallcap_universe` is drawn from
> **NSE index constituents**, and NSE Emerge (the SME board) is a separate segment
> that is not in them. The Hub's `liquid_universe` is top-N by **traded value** from
> the bhavcopy, and an SME name does not survive a liquidity floor — that is what
> the floor is for.
>
> **2. The price data is known-unreliable for exactly these names.** `data_source`
> carries a retry loop written because *"yfinance intermittently returns an empty /
> 1-3 row STUB for thinly-traded BSE/SME names (e.g. DIACABS.BO, VILAS)"*, and
> `dashboard_app` already warns that growth/ROCE/working-capital reads are
> untrustworthy for thin BSE/SME names.
>
> **This is the B-48 situation, not the B-45 situation:** the blocker is the FEED,
> not the code. Building an SME screen on a feed that stubs would produce a
> plausible-looking screen of names whose history was never there — indistinguishable
> from a working one by eye. **First deliverable for the SME ask is therefore a DATA
> probe, not a screen:** how many NSE Emerge symbols resolve, how often they stub,
> and whether any free source carries their fundamentals.

### The cadence contradiction in ask 3, which is worth deciding before building

**"1–2 smallcap opportunities every month" asks a QUARTERLY signal to speak
monthly.** `smallcap_discovery.score_from_cache` reads **shareholding filings** and
returns `None` with fewer than 2 quarters; conviction is the *change* in
institutional holding between filings, and NSE publishes those **four times a
year**. Two months in every three, a "monthly" idea would be the same filing data
re-ranked, dressed as new information.

Three honest ways out, and the choice is the owner's:
- **(a) Quarterly cadence** for the conviction lane, matching its input.
- **(b) Monthly cadence on a different signal** — price/volume structure on the
  smallcap universe, which updates daily but is NOT what B-34 measured.
- **(c) Monthly delivery, quarterly refresh** — stated plainly on the card, so the
  reader knows which months carry new filings.

### What this must NOT become

> [!warning] The desk has already measured most of what a theme like this would stack
> **B-19 measured most single-condition scanners at no edge after costs.** The three
> "retrace into a level after a structure break" implementations measured
> −0.36% / −0.47% / −0.43% @20d across ~9,000 signals. [[analyses/Contra-Strategy-Roadmap]]
> already records that **the two highest-rated methods on a supplied contra list are
> the two already falsified here** — POC/liquidity-exhaustion (SVP: 5 of 7 factors
> sign-inverted) and astro-contra (SBC daily-vedha: clean negative).
>
> **Bundling unmeasured screens into a themed pipeline does not make them work; it
> makes the failure harder to attribute.** The one component with a measured,
> cost-surviving edge is `Liquidity Sweep` (B-41m, +0.51% @20d) — and even there
> B-41p showed the shipped plan returns +0.06R.

### Proposed sequencing

**Phase 0 — measure what is already built, before adding anything.** This is not new
advice; [[analyses/Contra-Strategy-Roadmap]] already names it as blocking. The
concrete item here is **`multibagger_candidates` has never been measured** and is
ask #1's whole deliverable. One pre-registered event study, the [[#B-22r]] pattern:
design committed before the scorer runs.

#### Phase 0 · **COUNTED 2026-09-12 — the screen CANNOT be measured as specified, and the ceiling is not a matter of effort**

`tools/multibagger_cardinality.py`, and it is deliberately not the event study.
Counting first is this desk's own rule, recorded twice in the 2026-09-07 session
(`renko_quality_cardinality` killed a 40% filter by showing 96% of flips already
cleared it; the QM detector reported a "pattern" on 73% of names until its pivots
were made consecutive). **It saved the study again here, plus a ~370-name
statement refetch.**

**The screen has to be RECONSTRUCTED before it can be scored.** `QUERY` is a live
screener.in query behind a session cookie returning today's snapshot only, so
there is no history to replay. Four of its seven legs are reconstructable from
caches already on disk (market cap from `shares_total` × close, 3y sales growth
from `pit_quality`, FII+DII change and promoter change from `ownership`); the three
ratio legs (OPM, ROCE, D/E) need a statement refetch. **The free four were counted
first, because if they do not leave enough events the refetch is moot.**

| leg, each counted on the survivors above | left | dropped |
|---|---|---|
| quarter-pairs in the cache | 2,491 | |
| priced within 10 days of the filing | 2,410 | 81 |
| market cap < ₹20,000 Cr | 741 | 1,669 |
| (FII + DII) change > 1 | 152 | 589 |
| promoter change > −1 | 122 | 30 |
| 3y sales CAGR > 15 | **46** | 76 |

Plus **35 events UNKNOWN on growth** — too few published years to evaluate, which
is not a failure and is never folded into the denominator, per `point_in_time_quality`'s
three-state rule.

**46 point-in-time events against the desk's floor of 200, and only 10 survive to
252 days.**

> [!note] The table above is POST-pilot, and the delta is the cleanest proof on this page
> These counts were 2,330 pairs → **45** events before the 12-name pilot backfill
> and 2,491 → **46** after it. **161 new quarters of ownership history bought ONE
> event.** The argument that deep ownership depth cannot rescue this screen was made
> from the statement-depth arithmetic below; the backfill then demonstrated it by
> accident. The three ratio legs can only cut further, so they were not fetched.
**Ask #1 of B-73 cannot be delivered as "measured", and the reason is now
documented instead of unexamined.**

**The event date is the FILING date, not the quarter end.** A 30-JUN holding change
becomes public when the pattern is filed, ~3 weeks later; the cache carries
`filed_on` for exactly this. Forming on the quarter end would be weeks of
lookahead on a signal whose entire content is the change.

##### Two independent ceilings, and [[#B-22r]]'s lesson applies to only one of them

**1. The universe is the wrong one, and this IS fixable.** The screen wants
early-stage small caps; the desk's cached panel is large-cap. Of 2,330 priced
events only **27.8%** fall under the ₹20,000 Cr ceiling and **2.4%** under ₹5,000
Cr, median cap **₹53,007 Cr**. Only **97** cached names are small enough to be in
this screen's universe at all.

**2. Annual statement depth is the binding ceiling, and it is NOT fixable.**
B-22r's lesson — *a blocker that is a property of an assumption rather than of the
data* — was checked directly, and this time it cut both ways:

> [!key-insight] The ownership blocker was false; the statement blocker is real
> **Ownership depth was an assumption.** The cache held 5–8 quarters because it was
> filled with `--quarters 8`, not because NSE stops there. Probed live, the filings
> master serves **20 quarter-ends back to 2021Q3 for small caps too**, and a pilot
> backfill of 12 names took **5.4 minutes for 161 new quarters** (~0.45 min/name).
> Third time this pattern has appeared, after B-22r's PCR archive.
>
> **It buys nothing, because the growth leg has no matching depth.** yfinance serves
> **4 annual columns** (435 of 460 names), so with the 60-day filing lag a
> point-in-time 3-year sales-growth verdict first exists at a **median 2025-06-15** —
> **1 name in 200 before 2025-01-01**. Formation dates are capped at ~5 quarters no
> matter how much ownership history is backfilled. **Deep ownership history against
> shallow statement history yields nothing**, and that is a vendor limit, not an
> assumption. Same shape as B-48: the blocker is the FEED.

##### A bug in the probe, found by reading it rather than by a number looking wrong

`searchsorted` on a filing date BEFORE the first cached bar returns index 0, so a
2021 event was silently priced at the 2023 open of the cache window — **a two-year
lookahead reported as a valid event**, and one that made the funnel look healthier.
Now bounded by `PRICE_TOL_DAYS = 10` in both directions. It cost 67 of the pilot's
209 pairs, correctly. **Nothing in the counts would have looked wrong.**

##### PRE-REGISTERED — the nearby question that CAN be powered, and what it may not claim

Written now, while the design is cheap, per B-22r's clock argument. **Not run:** it
is gated on a backfill decision, and the cost is measured, not guessed.

  CLAIM     does fresh institutional buying into a SMALL-CAP name beat the
            benchmark over 3–6 months? The **institutional-conviction core**:
            market cap < ₹20,000 Cr, (FII+DII) change > 1, promoter change > −1.
            The growth and ratio legs are DROPPED, because their point-in-time
            depth does not exist.

  **THIS IS NOT THE MULTIBAGGER SCREEN AND MAY NOT BORROW ITS NAME.** It drops
  four of seven legs and measures 3–6 months where the word multibagger means
  years. [[#B-65r]] is the precedent for why this matters: a factor that borrows
  credibility from a nearby measured claim is the specific error this desk has
  already made once.

  HORIZONS  63 and 126 trading days. **252 is reported and cannot decide** — 10
            events today, and the multibagger horizon is unreachable on free data
            in any case.
  BASELINE  an equal-length window on the same name, per [[#B-74]]'s correction —
            a raw return would flatter every long-only screen by the drift it sat
            through.
  STATISTIC mean return, symbol-block bootstrap, 29bps, the standing convention.
  FLOOR     200 events per cell, or it concludes nothing.
  PRIOR     no edge. [[#B-34]] measured the smallcap conviction lane WEAK
            (−0.12% @60d, +0.20% @120d) on a closely related signal, and that is
            the nearest prior this desk owns.

  **THE BACKFILL IT REQUIRES, costed from the pilot, not estimated:** ownership to
  20 quarters over ~300 small-cap names ≈ **2.3 hours** of paced NSE requests, plus
  a 5-year daily price refetch for names outside the current 3-year panel.
  Projected yield from the pilot's measured rates (16% institutional, 70% promoter)
  is **~600 events** — comfortably powered, and the only version of this question
  that is. **An owner decision, because it is hours of scraping a rate-limited
  public endpoint for a question whose registered prior is no edge.**

**Phase 0's honest status: `multibagger_candidates` remains UNMEASURED, and now
provably so on this desk's data.** What Phase 0 delivered is the count that says
which question is answerable, and at what price.

#### Phase 0 · the conviction core **MEASURED 2026-09-13 — NEGATIVE pooled, and the sign FLIPS by era**

Owner authorised the backfill. It ran **178.6 minutes** over 495 names, landing
**5,169 new quarters** (489 ok, 6 with no filings, 0 errors; 286 names at the full
20 quarters), alongside a 6-year price panel of 493 small/micro-caps in a cache of
its own. The pre-registered study then ran on **1,112 events across 397 symbols**,
median cap **₹7,426 Cr**, window **2022-10-10 → 2026-08-21**. Both deciding cells
clear the floor of 200 by 5×.

| horizon | n | raw | **edge** | 95% CI on the edge | decides |
|---|---|---|---|---|---|
| 63d (~3 mo) | 1,072 | +7.02% | **−2.07%** | [−3.50%, −0.62%] excludes 0 | yes |
| 126d (~6 mo) | 1,021 | +13.43% | **−4.85%** | [−7.20%, −2.39%] excludes 0 | yes |
| 252d (~12 mo) | 946 | +37.67% | −1.46% | [−6.07%, +3.14%] includes 0 | no, reported |

> [!key-insight] The raw column is the whole argument for [[#B-74]]'s correction, in one table
> Raw, this screen looks **excellent**: +7% in three months, +13% in six, **+37.7%
> in twelve**. Measured against an equal-length window on *the same name*, every
> one of those is **negative or indistinguishable from zero**. The screen was not
> picking good windows; it was picking names in a market that rose ~39% per year.
> **B-74's mis-specified bar was caught a day earlier on a different study, and
> without that correction this one would have reported a large positive edge and
> been believed.**

##### The era split changes what may be CLAIMED, and it was not pre-registered

Added after the first run, as description, partition stated first per [[#B-74r]]:
three chronological windows of equal event count, edge basis.

| win | n (63d) | period | raw | edge | 95% CI |
|---|---|---|---|---|---|
| 1 | 357 | 2022-10 → 2023-04 | +5.52% | −3.27% | [−5.82%, −0.69%] excl 0 |
| 2 | 358 | 2023-04 → 2024-10 | +14.62% | **+5.24%** | [+2.71%, +7.73%] **excl 0** |
| 3 | 357 | 2024-10 → 2026-06 | +0.92% | **−8.19%** | [−10.58%, −5.78%] excl 0 |

The 126d rows behave the same, more sharply: **−6.52% / +8.63% / −16.69%**, every
CI excluding zero.

**So the pooled NEGATIVE is an average over a SIGN FLIP.** Window 2 is positive
with a CI excluding zero; window 3 is severely negative. The defensible claim is
therefore **not** "institutional buying into small caps underperforms" but:

> **There is no stable edge here. Pooled, the signal underperforms the names' own
> drift at 3 and 6 months; split by era it changes sign, so any single-period
> reading of it — positive or negative — is a reading of the period.**

This is [[#B-41w]]'s lesson arriving from the other direction: that study asked
whether a POSITIVE result survived era-splitting, and it did. Here a **negative**
one does not survive as a stable claim. **Era-splitting is where results die
regardless of which sign they carry.**

##### Survivorship, and for once it cuts toward the result

The universe is **TODAY's** Smallcap-250 + Microcap-250 membership, so a name that
was small in 2022 and **grew out of those indices** by 2026 is absent — and that is
precisely the outcome this screen hunts. **The winners are the names most likely to
be missing**, so the true edge is plausibly less negative than measured. Stated and
not corrected: no free source fixes it, which is `point_in_time_quality`'s own
recorded caveat. It does not rescue the screen — it bounds how hard the negative
may be read.

##### What this does NOT say, pre-registered and binding

**Nothing here promotes or condemns `multibagger_candidates`.** This study drops
**four of its seven legs** and measures months where the word means years. The
shipped screen stays UNMEASURED and stays a candidate list. The one thing the desk
may now say is narrower: **the conviction core it is built around does not carry a
stable 3–6 month edge, and its raw returns are the market's, not the screen's.**

**A wart fixed in the same pass:** the report called the bootstrap twice for one
quantity, so the table and the decision printed two slightly different intervals
([−3.50, −0.62] and [−3.52, −0.58]). Both were valid draws, which is exactly why it
had to go — a reader cannot tell a resampling wobble from a bug. Computed once now.

**Phase 1 — decide the smallcap cadence** (a/b/c above). A decision, not a build.

**Phase 2 — the SME data probe.** Answers whether ask #4 is possible at all before
any screen is written.

**Phase 3 — assembly.** Only now is there a "pipeline": one page that routes
daily momentum/swing from the Hub, the smallcap lane at its decided cadence, the
multibagger screen at whatever weight its measurement earned, and SME if and only
if Phase 2 says the data exists.

**Nothing in Phase 3 is hard. Phases 0–2 are where this item actually lives.**

## B-74 · The PMax PLAN has never been scored — the B-41p that PMax never got — **MEASURED 2026-09-12: the drawn plan is WORSE THAN HOLDING**

Raised while answering a question, not during a review: owner asked what *"the
band"* means in the PMax card's exit line. Answering it exposed that the card was
drawing an entry, a ratcheting stop, three R-targets and an exit rule **with
nothing behind any of it** — and that the gap is structural, not an oversight.

**The asymmetry, named.** [[#B-72]]'s liquidity-sweep overlay ships with BOTH
measurements attached: **B-41m** scored the signal (+0.51% @20d, p=0.005) and
**B-41p** scored *that exact entry/stop/target* (+0.06R). PMax has only the first
half. [[#B-65]] scored the **SIGNAL** — flip → 20d forward return, **−0.55%,
p=0.511, n=1,538** — and **no one has ever scored the plan the chart draws.** The
card now says so in as many words; this entry is the thing it points at.

**What the shipped plan actually is**, read off `pmaxSignals` in
`chart_dashboard.html` rather than from the card's prose:

- **entry** = the flip bar's close
- **initial stop** = the PMax band *on that bar*, so **R = |entry − stop|**
- **trail** = the live band, which **ratchets** and never loosens while the trend holds
- **exit as displayed** = the opposite flip ("exit when the band flips")
- **targets** = 1R / 2R / 3R markers, with ✓ badges for best excursion since the flip

**PRE-REGISTERED DESIGN — binding, written before any scorer exists.**

  Same panel, harness, universe and baseline as [[#B-65]] (460 names, ~3y daily,
  entry next open, unconditional baseline, costs at 29bps, symbol-block
  bootstrap), so every number lands beside the signal measurement rather than in
  its own frame.

| arm | definition | decides? |
|---|---|---|
| **A · SHIPPED** | enter at the flip close, trail the ratcheting band, exit on the opposite flip | **yes** |
| **B · FROZEN STOP** | same entry, stop held at the flip-bar band (no ratchet), exit on opposite flip or stop | no |
| **C · TIME ONLY** | same entry, no stop, exit at the 20-day close | no — see below |

- **This entry CANNOT promote PMax, and that is pre-registered.** B-41p's result
  worked because removing the stop unlocked an edge **the signal already had**
  (+0.51%, p=0.005). B-65 measured this signal a **null**. There is no edge here
  to unlock, so a positive arm would be a sample artifact rather than a discovery.
  Written down now so a positive number cannot be quietly promoted later — the
  same guard [[#B-65]]'s own state arm carries.
- **Arm C is not independent evidence.** It is B-65's flip → 20d study expressed
  in R, and it doubles as a **harness check**: if C does not reproduce −0.55%
  converted, the harness is wrong, not the finding.
- **What this DOES decide: whether the card keeps its furniture.** If **A is worse
  than C with a bootstrap CI excluding zero**, the trail and target lines are
  drawing a plan that costs the reader money relative to doing nothing, and they
  are **demoted to context** — the [[#B-70]] move, where a surface that points the
  wrong way is retired rather than re-tuned. If **A ≈ C**, the furniture stays and
  the card's existing B-65 caveat is sufficient.

  ABORT   under **200** flips the run is UNDERPOWERED and concludes nothing.
          Not the risk here: B-65 counted **1,538** on this panel.

**PRIOR: all three arms ≈ 0.** A null signal does not become a plan by having a
stop attached to it. The value of running this is not discovery — it is closing
the one gap the card currently admits to in public, and finding out what the
ratcheting exit **costs** against a flat hold.

═══ MEASURED — 2026-09-12, `tools/pmax_plan_study.py` ═══════════════════════════

2,788 trades (1,269 long / 1,519 short) · 448 symbols · 29bps · 2,000-draw
symbol-block bootstrap. Bands emitted by `tools/pmax_bands_emit.js`, which lifts
`pmaxSeries` out of the chart through the new `chart_lift.js` rather than
reimplementing it — so these are the numbers the chart draws.

**EDGE — each arm against an equal-length unconditional window, LONG (decides):**

| arm | edge R | 95% CI |
|---|---|---|
| **A1 · SHIPPED-FLIP** | **−0.500** | [−0.564, −0.433] **excludes 0** |
| A2 · SHIPPED-TRAIL | −0.600 | [−0.696, −0.504] excludes 0 |
| B · FROZEN STOP | −0.533 | [−0.616, −0.458] excludes 0 |
| C · TIME ONLY (20d) | −0.145 | [−0.191, −0.099] excludes 0 |

**VERDICT: DEMOTE.** On equal footing the shipped plan is worse than a plain
20-day hold by **+0.355R (CI [+0.296, +0.412], excludes 0)**, and worse than
simply holding the same stock over the identical window by **half an R per
trade**. The drift the shipped hold sits through is **+0.635R over a median 67
bars**; the plan hands back four fifths of it.

> [!warning] The registered decision bar was MIS-SPECIFIED, and it said KEEP
> As written it compared A1 and C on RAW R. But A1 holds to the opposite flip
> (median **67 bars**) and C exits at a fixed **20**, so A1 collects ~3× the drift
> before any plan quality is involved. On raw R, A1 (+0.135) "beats" C (−0.012)
> and the bar returns **KEEP** — the opposite of the truth. The bar's INTENT
> (*does the drawn plan cost the reader against doing nothing*) is answerable only
> once each arm is measured against its own equal-length window, and then it is
> **DEMOTE**. Both readings are printed by the module so the error stays visible.
>
> **The defect is mine and it is instructive:** B-74's PANEL line said *"B-65's,
> unchanged … unconditional baseline"* and the first cut of the scorer then
> reported raw R. B-65's −0.55% is an EDGE, not a return. A pre-registration that
> names a baseline and a scorer that omits it is how a null becomes a positive.

**The harness reproduces B-65 exactly**, which is why the above can be trusted:
run under B-65's own convention (entry next open, all up-flips, no cost) it
returns **n=1,538, raw +1.214%**, and +1.214% − the unconditional **+1.76%** =
**−0.546%** against B-65's published **−0.55%**. Same count, same number.

**SHORT (description, 1,519 trades): the raw −0.473R is ENTIRELY drift.** Edge on
the short side is **+0.000R [−0.077, +0.102], includes 0** — PMax shorts do no
worse than shorting an arbitrary window of the same length. They look
catastrophic raw only because shorting a rising market loses. **Raw R flatters
longs and damns shorts, and neither is a reading.**

**The prior was wrong in the direction that matters.** It predicted all arms ≈ 0.
Raw, the long plan came in at **+0.135R with a CI excluding zero** — and that is
precisely the confound [[#B-65]] pre-registered against for its own state arm:
*in a window whose unconditional mean is positive, any long-biased hold looks
good*. The edge table is what that prior should have been written against.

**Two findings the study was not looking for:**

1. **The drawn trail is worse than the sentence beside it.** A2 (the "Trail SL"
   line used as a stop) is **−0.099R below A1** raw, CI excludes 0, and −0.600R on
   edge. The card draws a line that, if acted on, is worse than the exit rule
   printed next to it.
2. **Stop PLACEMENT is not the lever here either** — B (frozen stop) sits within
   noise of A1 (−0.033R, CI includes 0). Same shape as [[#B-41p]]'s arm B, and for
   the same reason: what costs is the exit discipline, not where the stop sits.

**CONSEQUENCE APPLIED.** Per the registered bar, the card's furniture is demoted
to context: the PMax card now reads *"Measured, and worse than doing nothing"*
and carries the −0.50R. The lines stay drawn — they are the indicator's own
geometry — but they are no longer presented as a plan. Precedent: [[#B-72]] put
B-41p's number on the stop's axis label rather than removing the stop.

**NOT promoted to anything, and nothing here licenses trading the 20-day hold.**
Arm C is B-65's study in R and is itself **−0.145R on edge, CI excluding zero**.
Every arm loses against the benchmark. The result is a demotion, not a discovery.

### ~~B-74r~~ · Does the demotion hold across eras? — **MEASURED 2026-09-12: YES, 3/3, and it gets WORSE as drift falls**

The one follow-up B-74 left owed. [[#B-41w]] is the precedent and also the source
of the design rule applied here: its recorded defect was a prior naming *"window
2"* without naming the partition, so **the partition is named first** — three
chronological windows of **equal trade count** on the deciding long group, ordered
by entry date. Not equal bar fractions, not equal calendar spans.

**Registered before the run:** basis is the **EDGE** columns, not raw R — the
parent study established that raw R inverts this very comparison, so an era split
on the raw basis would re-inherit the mis-specification. Pass bar: DEMOTE survives
iff **eA1 < 0** and **eA1 < eC** in **all three** windows.

| win | trades | from | to | eA1 | eC | eC−eA1 | drift | 95% CI on eA1 |
|---|---|---|---|---|---|---|---|---|
| 1 | 423 | 2023-12-07 | 2024-12-16 | −0.251 | −0.052 | +0.199 | +0.755 | [−0.394, −0.097] excl 0 |
| 2 | 423 | 2024-12-16 | 2025-08-12 | −0.325 | −0.037 | +0.289 | +0.707 | [−0.466, −0.178] excl 0 |
| 3 | 423 | 2025-08-14 | 2026-08-04 | **−0.924** | −0.346 | +0.577 | **+0.442** | [−1.010, −0.834] excl 0 |

**eA1 < 0: 3/3 · eA1 < eC: 3/3 · VERDICT: DEMOTE SURVIVES.** Every window's CI
excludes zero on its own. The demotion is a property of the plan, not of the
sample, and B-74's consequence stands as applied.

> [!key-insight] The prior's escape clause was falsified, and backwards
> B-74r pre-registered the one way DEMOTE could fail: *"a window with no drift at
> all, where there is little to give back — and in such a window eA1 should
> approach 0 from below."* **Window 3 is the low-drift window (+0.442R against
> +0.755/+0.707) and it is by far the WORST (−0.924R).** The relationship runs the
> other way: the less the window trends, the more the plan costs. That is
> mechanically sensible after the fact — the plan's loss comes from exiting into
> the band after price gives part of a run back, and chop makes it give back
> repeatedly with no run to keep — but it is not what was written down, and the
> pooled −0.500R is now visibly an average over a widening spread rather than a
> stable level.
>
> The drift column itself was added **after** the first run, to explain the
> window-3 outlier. It is description, it is not in the pass bar, and it is
> recorded as post-hoc for the same reason the parent study keeps printing its own
> mis-specified bar.

**Power caveat, stated before the numbers:** B-41w split **six** years; this panel
is ~3, so each window is ~1 year and sees one market phase. Three agreeing windows
here is weaker than three there. **This split can catch era-dependence; it cannot
certify stability.** What it does establish is that the demotion is not resting on
one phase.

**Nothing further is owed on B-74.** The item is closed.

**Not ranked yet.** The 2026-09-11 refinement pass predates it; it takes its place
in the next pass's ordering.

## B-75 · A quarterly profit-growth walk on the tables — **SCOPED 2026-09-12, BUILT 2026-09-16** *(outcome below)*

Owner's ask: a **Q-on-Q profit growth %** walk column, in the shape of the RS walk
([[#B-63b]]) — a per-quarter sequence read oldest → newest, so a name whose profit
growth is decaying reads differently from one that is turning up, without opening
a second page.

**Scoped the way [[#B-73]] and [[#B-58]] were: counted before proposing.** The count
changed the design, so it is recorded before any build.

### What already exists

`fundamentals_deep._quarterly_history` already returns per-quarter `revenue`,
`net_income`, `ebit`, `net_margin`, `opm` and **`profit_yoy`** — so the arithmetic
is built and this is a column, not an engine. `row_metrics` owns the walk columns
and `columns.py` owns the registry entry; both are the shipped pattern.

### The count that changes the design

Measured on five names across the cap range (RELIANCE, JAMNAAUTO, SENCO,
HERITGFOOD, NEOGEN):

| what | result |
|---|---|
| quarterly columns yfinance serves | **5–7** |
| quarters with a computable **YoY** profit | **1–2** |
| frames with a **missing quarter** | RELIANCE lacks 2025-09-30 |

**A year-over-year walk is impossible: one or two points is not a sequence.** The
only walk this data supports is the **sequential** one the owner asked for — 5–7
quarters give 4–6 steps.

> [!warning] And that collides with a decision already recorded in the code
> `_quarterly_history` uses YoY *on purpose*, and says why: *"sequential comparison
> would read seasonality as growth."* For an Indian cash-segment book that is not
> hypothetical — Q3 festive quarters and Q4 year-end push are structural.
>
> **So the ask is buildable and the desk's own reasoning says the result is
> seasonality-exposed.** That is not a reason to refuse it; it is a reason the
> column must be **labelled as sequential**, must never be read as a growth rate,
> and must not become an input to anything that votes. The honest framing is the
> one the RS walk already uses: a **shape**, not a number.

**The gap trap, which the RS walk also hit.** Frames are gapped, so a naive
sequential walk would compare Dec to Jun and present it as one quarter's change.
Either mark the gap (the RS walk's `?` convention) or drop the step — **silently
spanning it is the one option that is wrong**, because it manufactures a number
nobody can see is wrong.

### Proposed shape, for whoever picks it up

* `row_metrics.profit_qoq_walk(symbol)` → the last 4–6 sequential changes,
  oldest → newest, with an explicit marker where a quarter is missing.
* One registry entry in `columns.py`, `text` (it is a sequence), with the
  seasonality caveat in the **tooltip**, not only in a page caption — the tooltip
  travels with the column to every table that mounts it.
* Mounted on the Watchlist and both Scanner Hub tables, the three surfaces
  [[#B-63b]]'s walk columns already reach.
* **No backtest owed** — it exposes an existing series and makes no claim about
  edge, the same footing [[#B-45]] was ranked on. Equally, **no vote, no score, no
  confluence weight** without a measurement.

**Cost:** small. The arithmetic exists, the walk pattern exists, the mount points
exist. The judgement above is the expensive half, and it is written down now.

## Ingested-research additions (2026-09-18) — B-96 / B-97 / B-98

From [[sources/Bramesh-TradingView-Gann-Scanners-Product-Line]] — five paid TradingView Gann scanners, **₹24,330/month for the set**,
all closed-source Pine, all capped at 40 symbols, and across five products **not one
backtest, win rate, sample size or losing example**. Read the way the ScreeningMantis
tables were: as a **catalogue of constructs to check against our own**, never as evidence.

**Nothing worth buying. Three ideas worth stealing — and none of them is a Gann idea.**

What was **declined**, with the reason:

* **"Vibration", square/cube numbers, 180°/360°/540°/720° extensions** — unfalsifiable
  as sold. No anchor rule, no scaling, no construction. Same verdict as
  [[concepts/Gann-Angles-And-Trend-Change-Levels]]: *a level you cannot derive is a level
  you cannot backtest*, and paying for it does not change that.
* **"Institutional Floor"** — the **200 EMA**, renamed. The page says so itself.
* **"Time-cycle averages"** — a moving average with a longer lookback.
* **FRESH / NEAR state labels** — **already shipped as [[#B-63]]b**, and ours is better:
  it prints the **age** (`ema_cross_age`, `bo_date`, the RS-rank walk) rather than a
  two-state flag. Their 0.5% proximity band is also looser than `row_metrics.PIVOT_NEAR`
  at **0.15%**.
* **The drift table** (distance to level, absolute and %) — the arithmetic a `pivot_zone`
  label exists to remove.
* **The 40-symbol cap** — a Pine platform limit, not a design choice. B-92 ran across
  **248 names**. Nothing here inherits it.

> [!key-insight] Two of the three came from noticing something this desk already had and
> was not using
> B-96 is a composition of `pivot_levels()` and `timeframe_board`'s resampling — both
> shipped, never combined. B-97 is a question about two columns that have printed side by
> side since B-63b and were never compared. **Neither needed the source to invent
> anything**; the source's only contribution was to make the absence visible. That is the
> honest value of reading a competitor's feature list, and it is worth more than the
> ₹2.92 lakh/year the list is attached to.

### B-96 · higher-timeframe pivot zones — **BUILD, small**

`pivot_levels()` is frame-agnostic by design; its docstring already invites this. Add
`pivot_m` / `pivot_q` / `pivot_y` alongside `pivot_d` / `pivot_w`, resampling with the
period-END anchors `timeframe_board.RESAMPLE` already uses so a partial current period
shows as a partial bar rather than being dropped.

**Two things to get right, both of which this desk has been bitten by before:**

1. **A yearly pivot needs a PRIOR yearly bar.** `pivot_levels` reads `iloc[-2]`, so a name
   listed inside the window has none — it must return `None`, not a pivot computed from a
   stub. Precedent: `timeframe_board`'s `MIN_BARS` refusal, and PR-1c's *"Hyundai correctly
   reports 2 rather than pretending to four"*.
2. **Absent must render absent** (FR-4). A missing yearly pivot must not read as a verdict.

### B-97 · do the pivot timeframes agree? — **MEASURED 2026-09-19: NO. They agree on the SIDE of the pivot 53.9% of the time and read OPPOSITE sides 37.9%**

**Result first.** `tools/pivot_timeframe_agreement.py`, 499 of 500 NIFTY 500 names (one
excluded — could not produce both reads):

| | observed | chance | lift |
|---|---|---|---|
| zone agreement (7 labels) | **25.9%** | 17.9% | +7.9 |
| **SIDE agreement** (above / at / below the pivot) | **53.9%** | 41.8% | **+12.1** |
| **opposite sides** (one ABOVE, one BELOW) | **37.9%** | — | — |

Against the bands fixed before the run: **TWO DIFFERENT READINGS** (side < 70%) and the
opposite-side flag reads **CONTRADICTION** (≥ 20%). **Worse than the prior.** B-42r found
`pivot_len` 5 vs 15 agreeing 29.6% on `state` with **17.6%** opposite; daily vs weekly
pivots read opposite **37.9%** of the time, more than double that.

**The robustness check, and it is why this is a finding rather than a snapshot.** The
primary run's label distribution came back badly skewed — 249 of 499 names at `R1` on
daily against 199 at `PP-S1` on weekly — which is exactly what a cross-section taken three
sessions into a bounce off a seven-week decline looks like: above yesterday's pivot, below
last week's. Taken alone it would have inflated disagreement by construction. Re-run on
**29 past month-ends** (2024-03 → 2026-07, same frames truncated, nothing re-downloaded):

* **median side agreement 64.0%** (range 50.1 – 91.0)
* **median opposite 27.3%** (range 5.6 – 39.0)
* **22 of 29 dates clear the 20% contradiction threshold**; only **5 of 29** reach the 70%
  "real but narrow" band and only one (2026-03-31, 91.0%) is cosmetic.

So the primary date is at the disagreeable end of the range but **not an outlier, and the
verdict does not depend on it** — the median date still fails both bands. Today was
declared post-hoc in the file and is not restated as the headline.

**What the lift says, and it is the half that is easy to miss.** Agreement is above chance
at every single date (+4.2 to +32.3, median ≈ +16). These two columns are **not
independent** — they carry real shared information. The finding is not "the weekly column
is noise"; it is that the shared part is far smaller than a reader scanning two adjacent
columns would assume.

**The two high-agreement dates are the mechanism.** 2025-02-28 (87.3%) and 2026-03-31
(91.0%) are the dates where nearly everything sat on one side, which is what a strong
trending month does to both timeframes at once. Agreement is a function of the tape, not a
property of the columns.

#### What this decides for [[#B-96]]

B-97 was run first precisely so this question could be answered before three more columns
existed, and the answer is now on the record: **B-96 must not print five peer columns.**
At 37.9% opposite today and 27.3% at the median, a reader scanning five timeframes will
routinely see three say one thing and two the other, with nothing on the surface saying
which governs. Concretely, B-96 must either

1. **name a governing timeframe** and render the others as context subordinate to it, or
2. **print the agreement itself** — a single "3 of 5 above" state, the way B-42's
   `agreement` field collapses CONFIRMED / UNDECIDED — so the split is the reading rather
   than something the reader has to notice.

Option 2 is the better fit for this desk, because it makes the disagreement legible
instead of leaving it as five facts in a row. **Either way B-96 is no longer "small".**

#### Design notes (the file is the pre-registration, committed before the run)

No build at all: `pivot_d` and `pivot_w` both compute today. Score the agreement rate on
`state` across the universe, the way [[#B-42r]] scored `pivot_len` 5 vs 15.

> [!note] What happened to "use a rotation p-value"
> The instruction below was written for scoring a state against forward returns, and this
> study scores no returns — applied literally it would have tested nothing. What survives
> is the part that bites: **a raw agreement rate is mostly base rate.** The statistic is
> therefore agreement **lift over a cross-sectional rotation baseline** that holds both
> label distributions fixed, which is the same correction [[#B-59]]'s v2 re-run applied
> when its raw coverage turned out to be mostly chance. Reported with the raw rate, never
> instead of it.

**Use a rotation p-value.** A pivot zone is a slow, autocorrelated **state series**, not an
event — the same trap recorded in [[concepts/Participant-Positioning-FII-DII]] and measured
in B-56 (`gamma_regime_backtest._rotation_p`: a known null printed **p=0.031** under Welch
and **0.32** under rotation).

**Why this runs before B-96:** if daily and weekly already disagree as badly as `pivot_len`
5 vs 15 did (29.6%), then adding monthly, quarterly and yearly produces **five columns that
contradict each other**, and B-96 ships a confusion rather than a perspective. The
agreement rate is the number that decides how B-96 should present itself.

### B-98 · the calendar-anchored range — **BUILD then PRE-REGISTER**

The January high/low, stripped of the branding, is a **yearly opening-range breakout**. It
is the only construct on that page that can be reproduced here, because unlike every Gann
level it states its anchor.

Verified absent: no `opening_range`, no year-open reference anywhere in `tools/`.

**Scope, deliberately narrow:**
* Anchor = the first calendar month's high/low (the rule the source states — **use theirs
  rather than tuning one**, so the test is of their claim and not of our fitting).
* State = above / inside / below. Event = **the first close outside**.
* Pre-register before measuring, on B-92's shape: **the EVENT is the transition, not every
  bar of the state**, or the harness counts something nobody trades. Signal floor 200 per
  direction, per the B-58 precedent.
* Expect a **momentum confound**, exactly as B-92 has unresolved: a name above its January
  range has been rising all year by construction. **The control belongs in the
  pre-registration this time, not in the write-up afterwards.**

**The prior is skeptical and goes on the record now:** B-19 found **0 of 41 scanners stable
after costs**, and this desk's nearest existing construct — `Breakout` — is already
measured. A yearly range is a 12-month lookback breakout with a calendar anchor; the anchor
is the only novel part, and it is novel for **convenience**, not for any stated mechanism.

---

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

### B-8 · Stops in mean reversion — the Connors contradiction — **MEASURED 2026-09-17: CONNORS WAS RIGHT**

> [!key-insight] The desk's own stop costs it 0.64pp per trade
> `mean_reversion_stop_study.py`, **300 nifty500 names**, ~20 years (5,000
> bars/name), **742 non-overlapping signals** — above the desk's 200 floor —
> `COST_INDIAN` on every arm.
>
> | policy | mean % | median % | win% | stopped% | target% |
> |---|---|---|---|---|---|
> | **NO STOP (Connors)** | **+0.47** | +1.28 | 55.5 | 0.0 | 32.5 |
> | session low ×0.995 (**shipped**) | −0.15 | −1.85 | 30.1 | **68.1** | 21.2 |
> | 1-ATR (ForexTester) | +0.07 | −3.05 | 40.8 | 52.7 | 26.8 |
> | 2-ATR (ForexTester) | +0.33 | +0.84 | 53.1 | 24.7 | 31.4 |
>
> Paired against NO STOP on the same signals: **shipped −0.64pp (p=0.0086)**,
> 1-ATR −0.40pp (p=0.082), 2-ATR −0.14pp (p=0.370). Only the shipped stop is
> significant.
>
> **Both sources are right, about different stops.** Connors' claim — that stops
> remove the edge — holds for TIGHT ones. ForexTester's 2-ATR is
> indistinguishable from no stop at all, and the reason is in the table: it is
> only touched **24.7%** of the time, so it barely binds. The contradiction was
> never really a contradiction; it was two stop widths under one word.
>
> **The desk's shipped stop is the tightest of the three and the worst.** It is
> hit on **more than two trades in three** and cuts the win rate from 55.5% to
> 30.1% — it is closing mean-reversion trades exactly where mean reversion is
> about to happen, which is the failure mode Connors described.

> [!warning] The narrow basket overstated the effect by more than double
> This was first run on **LIQUID_50 only (145 signals)** and read **−1.44pp at
> p=0.0009**. Widened to 300 names and 742 signals, the same test reads
> **−0.64pp at p=0.0086**.
>
> **The direction replicated on 5× the sample and the policy ordering is
> identical** — shipped worst, then 1-ATR, then 2-ATR ≈ no stop, with stop-hit
> rates in the same order. **The size did not replicate.** 1-ATR also lost
> significance (p=0.021 → 0.082), which is what a real-but-smaller effect looks
> like when the basket stops being 50 of the most liquid names on the exchange.
>
> The setup itself is weaker off the large caps too: NO STOP falls from +1.28% to
> +0.47%. **Cite −0.64pp.** The first number was not wrong, it was narrow — and
> the difference between those two is the reason the provisional label existed.

**The stop was NOT removed, and that is deliberate.** The pre-registered
consequence was to record the finding and surface the number, not to silently
change a plan. Two reasons it stands as a decision rather than an oversight
(the third, the sample floor, was retired by the wide run):

1. **The effect is real but modest.** −0.64pp on a setup whose unconditional
   return is +0.47% is most of the edge, but it is a fraction of a per cent and
   it shrank by more than half when the basket widened.
2. **"No stop" is not "no risk control".** The scanner's `time_stop: 10` bounds
   the trade in TIME. Removing the price stop converts a bounded loss into a
   gap-exposed one, and this study measured return, not drawdown or ruin.
3. **2-ATR is the interesting middle** and it is what a follow-up should test as
   the default — it keeps a bound while costing nothing measurable.

**What a reader of the scanner should know now:** the plan's stop is tight enough
that it fires on most trades, and on this evidence it costs return rather than
saving it.

### B-8 · original specification
**Body restored 2026-09-17 from [[analyses/Open-Backlog-2026-08-02]]**, which is
where it had been left behind. What this page carried instead was a bare heading
and the claim that it was "fully specified" — see the warning in the roadmap.

[[strategies/Quantified-MA-Mean-Reversion]] uses **no stop**, because its own
backtests found that stops removed the edge. [[sources/ForexTester-Mean-Reversion-Guide]]
makes **1–2 ATR stops mandatory**. Two sources, one setup, opposite rules.

**And the desk has already taken a side without measuring it.**
`scan_mean_reversion` ships `stop = session_low × 0.995` with `time_stop: 10`.
That is not the neutral position; it is the ForexTester answer, adopted by
inheritance. Run one reversion entry with and without a 2-ATR stop and settle it.

### B-9 · Volume Profile 80% rule — **MEASURED 2026-09-17: FALSIFIED (45.5%, not 80%)**

> [!warning] The claim is off by a factor close to two, and it was never blocked on data
> `value_area_traverse_study.py`, 6 symbols × 84 sessions = **504 sessions**,
> prior session's value area, 30-minute bars aggregated from the stored 15s.
>
> | | |
> |---|---|
> | traverse after a 2-bar hold | **45.5%** (61/134) |
> | 95% CI (Wilson) | **37.3% – 54.0%** |
> | base rate, no hold required | 49.6% (178/359) |
> | lift | −4.1pp (p=0.422) |
> | **the claim** | **80%** |
>
> **80% lies far outside the interval**, so the claim is falsified on one
> proportion — no control needed for that part.
>
> **The lift is NOT claimed.** −4.1pp at p=0.422 is nothing, and the study says so
> in as many words. "Worse than doing nothing" is a stronger statement than "not
> 80%" and must not ride in on the first one's significance. The 15-minute
> sensitivity check agrees on both counts (41.3%, lift −8.9pp, p=0.056).

**Not blocked on data, which is the process finding.** The snapshot said "testable
on NSE 30-min data" and nothing followed, which read as a gap. `intraday_store`
already held 15-minute bars over ~85 sessions for six liquid names, and 30-minute
bars aggregate from them. Counting what is already stored beat waiting — the same
finding as [[analyses/PCR-Sign-Convention-Pre-Registration]]'s "blocked until
December" premise, which was also false.

> [!key-insight] A test caught a bug that moved the headline number
> The first run reported **40.6%**. `resample("30min")` snaps to the hour, and
> **NSE opens at 09:15**, so every session's first "30-minute bar" held a single
> 15-minute bar and the whole sequence was offset from there. Anchoring the
> resample on the session's own first timestamp moved the hit rate to **45.5%**.
>
> The conclusion is unchanged — 80% was never in reach either way — but a
> 5-point swing from a one-line alignment bug is a reminder that **an intraday
> study's bar boundaries are part of its method, not an implementation detail.**
> The test that caught it was written because the fixture looked wrong, not
> because the bug was suspected.

**Recorded, not claimed:** entries from ABOVE traverse at 56.1% (n=66) against
35.3% from below (n=68). Unregistered and unexplained; it is the kind of asymmetry
that deserves its own hypothesis rather than a footnote conclusion.

**Coverage note:** ^NSEI arms **zero** times in 84 sessions — the index rarely
leaves its prior value area and returns in this pattern at all. The rule is a
single-stock construct on this evidence.

### B-9 · original specification
**Body restored 2026-09-17 from the same snapshot.**

The claim: price entering the value area and holding **2 consecutive 30-minute
bars** has a ~**80%** chance of a full **VAL→VAH traverse**. A vendor claim with
no data behind it, and stated precisely enough to be falsified.

**No longer blocked on data.** The snapshot said "testable on NSE 30-min data"
and nothing followed, which read as a data gap. `intraday_store` now holds
**15m bars over 85 sessions for 6 symbols** (plus 1h over 751), and 30-minute
bars aggregate from 15m — so the study is runnable today. Moved to MEASURABLE NOW.

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

### ~~B-66~~ · The other three sentiment factors, and the composite itself — **MEASURED 2026-09-10: NOTHING DISCRIMINATES — not one factor, not the blend**

[[#B-65r]] measured the PMax factor (weight 20) and found it does not
discriminate. Its own consequence rule said re-weighting was a live proposal
*complicated by the fact that the other three factors are equally unmeasured* —
so moving PMax's 20 points into them would move weight from one unvalidated input
to three others. **This measures the other three, and then the composite they add
up to.** Until it runs, nothing about the sentiment index's weights can be
changed on evidence.

**What is being tested, per factor, as the code defines it:**

| # | factor | weight | shape |
|---|---|---|---|
| 1 | Advance/Decline ratio | **30** | `advances / (advances + declines)` on the EQ universe, 0..1 |
| 2 | Sector participation | **25** | `(greens + 0.5·flats) / scored` across 11 NSE sector indices, 0..1 |
| 3 | NIFTY vs SMA200 | **25** | `clip(0.5 + dist_pct/10, 0, 1)` — ±5% from the 200-DMA maps to 1/0 |
| 4 | ~~PMax 1H~~ | ~~20~~ | **measured, does not discriminate — [[#B-65r]]** |

**PRIMARY statistic, per factor: the TERCILE SPREAD** —
`mean(NIFTY fwd | factor in top third) − mean(fwd | bottom third)`, at **5
trading days**, entry next open, **circular-rotation p**, **PASS: spread > 0 AND
p_rot < 0.05.** Terciles rather than the B-65r up/down split because these three
are continuous, and a tercile split is the plainest way to ask "does more of this
mean more return" without fitting a threshold. Spearman rank correlation is
reported alongside as description only.

**THE ARM THAT MATTERS MOST — the COMPOSITE.** The same tercile spread on the
**0-100 score the desk actually displays**, built from the four factors at their
shipped weights. A component can be individually weak and the blend still work,
and the blend is the thing on the page — so this is reported as **co-primary with
the three factors**, and it is the only arm whose failure implicates the product
rather than a part. Also reported: the **BAND spread** (Strong Buy days vs Strong
Sell days), because bands are what the UI shows, with the expectation that n will
be small at the extremes.

**Windows, which differ per factor and are declared now:**

| factor | source | window | note |
|---|---|---|---|
| A/D | **PROXY** — daily advances/declines across the 460 cached liquid names | 2023-10 → 2026-09 | **NOT the shipped input.** The factor uses the full EQ bhavcopy (~2,000 names); this is liquid-only breadth, which is narrower and less noisy. Rebuilding 750 historical bhavcopies is a data-acquisition project, not a measurement. **A null on the proxy is evidence about breadth-as-a-signal, not proof about the shipped factor**, and it is labelled that way in the output |
| Sector | 11 NSE sector indices, yfinance | 2011-09 → 2026-09 (~15y) | all 11 verified live with current history on 2026-09-10 |
| Regime | ^NSEI daily | 2007-09 → 2026-09 (~19y) | the deepest arm, four regimes |
| Composite | all four | **2023-10 → 2026-09**, bounded by the A/D proxy | the shortest leg sets the window; noted as the composite's own power limit |

> [!warning] CORRECTION 2026-09-10 — the "stale claim" fix below was itself wrong
> The note that follows says the sector freeze ended, on the strength of fetching
> all 11 tickers with `period="max"` and seeing current bars. **The running
> dashboard said "only 3/11 sector indices usable" on the same afternoon, and it
> was right.** The difference is the parameter: the shipped code fetches
> `period="1mo"`, which returns **one row** for the 8 affected indices, while
> `"max"` returns 3,681. So the data is **not frozen** — every last bar is today —
> but the feed is **sparse across the outage window**, and the shipped call cannot
> see two bars to difference.
>
> **The component has been reporting NOT_CHECKED for weeks against a feed that
> was quietly recovering.** A fix is available but is NOT a one-word widening:
> `period="3mo"` returns two bars, but the earlier one can be many sessions old,
> and differencing across that gap and printing it as "today's move" is the exact
> trap the module already warns about. It needs a bound on the GAP between the two
> bars used, the way `MAX_STALE_DAYS` bounds the age of the last one — a behaviour
> change to a live component, so it belongs in its own commit.
>
> **The lesson, twice in one session:** verifying through a different code path
> than the one that ships proves nothing about the one that ships. Same shape as
> [[analyses/Open-Backlog#B-63a]]'s stale-module trap and the PWA
> service-worker cache trap.

> [!note] The stale claim this run already corrected
> `_sector_performance`'s docstring records that **Yahoo stopped updating 8 of
> the 11 NSE sector indices on 2026-07-17**, verified 2026-08-05. Checked again
> 2026-09-10 while scoping this: **all 11 now return current history through
> 2026-09-10.** The freeze ended. The comment is a correct record of a real
> outage and a wrong description of today, which is exactly the drift
> `tools/claims_lint.py` exists to catch — fix the comment when this lands.

**PRIOR, stated per factor rather than as one blanket guess:**

- **Regime (25)** — the *most* likely to discriminate, and the only one with
  direct supporting evidence on this desk: [[#B-32]] measured signals doing
  significantly worse below the 200 SMA (p<0.005). But note [[#B-65r]]'s
  distinction, which applies here too and cuts the other way: **B-32 measured
  SIGNAL performance conditional on regime, not INDEX returns conditional on
  regime.** This arm tests the second. They can differ, and PMax already showed
  they do.
- **A/D (30)** — the heaviest weight and, on the literature, the most likely to
  be *contrarian* rather than confirmatory at short horizons: extreme breadth is
  a classic exhaustion read. A monotone tercile spread would be mildly
  surprising; a **negative** one would be more interesting than a null.
- **Sector (25)** — expected weakest. It is a same-day count of which sector
  indices closed green, which is close to a coarse restatement of the market's
  own daily direction. **If it fails, the honest reading is that it was never an
  independent input.**
- **Composite** — genuinely uncertain, and the reason to run it: four weak
  factors can still blend usefully if their errors are uncorrelated, and can also
  be four views of the same thing dressed as diversification.

**CONSEQUENCE RULES, fixed in advance and deliberately conservative:**

- **Nothing is deleted or re-weighted by this run**, whatever it says. Same rule
  as [[#B-59r]], [[#B-65]] and [[#B-65r]]. A null is not evidence of harm.
- **If the composite discriminates**, the index stands as a product regardless of
  how the parts scored, and weak components are a refinement question.
- **If the composite does NOT discriminate while a component does**, the weights
  are actively getting in the way, and *that* is a concrete re-weighting proposal
  with a named beneficiary — its own entry.
- **If nothing discriminates**, the sentiment index is a **descriptive display,
  not a forecast**, and the honest fix is to say so **on the page** rather than to
  delete it. Relabelling is cheaper than deletion and loses nothing the desk has
  been shown to have.

═══ MEASURED — 2026-09-10, `tools/sentiment_factor_edge.py` ═════════════════════

Tercile spread on NIFTY forward returns @5d, entry next open, rotation p.

| factor | weight | window | top / bottom | **spread** | rho | hit | n | p_rot |
|---|---|---|---|---|---|---|---|---|
| A/D **(proxy)** | 30 | 2023-09 → 2026-09 | +0.24 / +0.27 | **−0.03%** | +0.00 | 56.3/52.7 | 734 | 0.855 |
| Sector | 25 | **2007-09 → 2026-09** | +0.20 / +0.21 | **−0.01%** | −0.00 | 55.4/53.7 | 4,649 | 0.908 |
| Regime SMA200 | 25 | **2008-07 → 2026-09** | +0.17 / +0.25 | **−0.08%** | −0.04 | 54.4/54.1 | 4,452 | 0.829 |
| **COMPOSITE 0-100** | — | 2023-09 → 2026-09 | +0.14 / +0.26 | **−0.12%** | +0.01 | 58.0/51.0 | 733 | 0.703 |

**VERDICT: nothing discriminates — not one component, not the blend.** Every
spread is flat-to-slightly-negative, every rank correlation is ~0, and every
rotation p is 0.70–0.91. This is not a marginal result that better data might
rescue: **rho of −0.04 over 4,452 sessions is a measurement, not a shortage of
one.**

**The two arms with real depth are the ones that matter.** Sector has **19
years** (n=4,649) and Regime has **18** (n=4,452), spanning 2008, 2013, 2020 and
2022. Both land on zero. Only the A/D proxy and the composite are short-window,
and they agree with the deep arms rather than disagreeing.

**The pre-registered per-factor priors, scored honestly — I got two of three
wrong in an instructive way:**

- **Sector (predicted weakest, "close to a restatement of the market's own daily
  direction")** — **confirmed**, and more completely than expected: −0.01%,
  rho −0.00 over 19 years. It is not a weak input; it is **not an input**. A
  same-day count of which sector indices closed green is a description of the day
  that just happened.
- **Regime (predicted the most likely to discriminate)** — **wrong.** This was
  the one with supporting evidence on this desk, and it produced the *largest*
  negative spread of the three. See below: it is also the clearest case of
  [[#B-65r]]'s distinction biting.
- **A/D (predicted possibly contrarian, "a negative spread would be more
  interesting than a null")** — neither. **Flat.** −0.03% with rho +0.00 is not a
  contrarian signal hiding behind a bad sign convention; there is simply nothing
  there at this horizon on this proxy.

> [!warning] Regime is where B-32's finding gets misused, and this run pins it
> [[#B-32]] measured **signals** performing significantly worse below the 200 SMA
> (+0.22% RISK-ON vs **−1.78% RISK-OFF, p<0.005**), and that result is not
> challenged here. What B-66 measures is whether **NIFTY's own forward return**
> depends on where NIFTY sits relative to its 200-DMA. **It does not** (−0.08%,
> rho −0.04, 18 years).
>
> Both are true, and the gap between them is the whole point: **"the market is a
> hostile place for our signals right now" is a different claim from "the market
> is about to go down".** The regime factor is built on the second and borrows its
> credibility from the first — exactly the substitution [[#B-65r]] caught the PMax
> factor making. **Two of the four factors now stand on the same confusion.**

**One descriptive oddity, flagged and NOT claimed.** The composite's top tercile
wins **more often** (hit 58.0% vs 51.0%) while earning **less on average**
(−0.12% spread). A/D shows the same shape (56.3 vs 52.7). High-sentiment days are
therefore more frequently green and more severely red — a fat left tail, the
"picking up pennies" profile. **This was not pre-registered, has no p-value and
is not a finding.** It is noted because if the sentiment index has any real use,
that asymmetry is a more plausible place to look for it than directional edge,
and because it would be easy to mistake the hit-rate column for a win.

**The bands the UI is built around are almost never hit.** Of 733 scored days,
**Strong Buy (≥80) occurred 44 times and Strong Sell (<20) 21 times** — 9% of
sessions between them. And the Strong Sell days averaged **+0.84%** against
Strong Buy's +0.23%. At n=21 that is noise and is reported as such, but the
structural point stands independently of it: **a five-band display spends 91% of
its life in three middle bands.**

**CONSEQUENCES — following the rules fixed before the run, which anticipated
exactly this outcome:**

- **Nothing is deleted. No weight is changed.** Same rule as [[#B-59r]],
  [[#B-65]] and [[#B-65r]].
- **The pre-registered consequence for "nothing discriminates" applies: the
  sentiment index is a DESCRIPTIVE DISPLAY, not a forecast, and the honest fix is
  to SAY SO ON THE PAGE.** Relabelling costs one caption and loses nothing the
  desk has been shown to have. That caption is the deliverable this entry hands
  forward.
- **Re-weighting is now formally dead as a proposal.** [[#B-65r]] left it live and
  "complicated by the other three being unmeasured". They are measured. **There
  is no beneficiary to move PMax's 20 points to** — every candidate scored the
  same zero. A re-weighting entry would have been the wrong instinct, and this is
  the run that shows it.

> [!note] What five nulls in one afternoon are actually worth
> The trailing-stop family (five measurements) and now the sentiment index (four
> more) have produced **nine nulls and zero deletions**. That is not a wasted
> afternoon and it is not a case for tearing anything out. **Every one of these
> nine was previously assumed to work, and the desk was making decisions on that
> assumption.** What changed is not the code — it is that nothing on these pages
> is entitled to be believed by default any more, and the two specific
> substitutions caught along the way (regime-for-signals, agreement-for-accuracy)
> are the kind of error that would otherwise have propagated into whatever got
> built on top.

### ~~B-65r~~ · The actual sentiment factor — PMax direction on NIFTY 1H — **MEASURED 2026-09-10: NEITHER ARM DISCRIMINATES, and 19 years of daily data has the power to say so**

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

═══ MEASURED — 2026-09-10, `tools/pmax_nifty_edge.py` ═══════════════════════════

**ARM 1 — ^NSEI 1H, 5,057 bars, 2023-10 → 2026-09** (2,676 up / 2,371 down)

| horizon | up | down | **spread** | hit up/dn | p_rot |
|---|---|---|---|---|---|
| **PRIMARY ~5d (35 bars)** | +0.00% | +0.31% | **−0.30%** | 51.9 / 54.5 | 0.306 |
| desc ~1d (7 bars) | −0.01% | +0.06% | −0.07% | 51.8 / 51.7 | 0.223 |
| desc ~20d (140 bars) | +0.62% | +0.71% | −0.09% | 60.2 / 62.8 | 0.860 |

**ARM 2 — ^NSEI DAILY, 4,658 bars, 2007-09 → 2026-09** (2,862 up / 1,786 down)

| horizon | up | down | **spread** | hit up/dn | p_rot |
|---|---|---|---|---|---|
| 20d | +0.54% | +1.12% | **−0.58%** | 58.3 / 60.1 | 0.488 |

**VERDICT: FAIL on the pre-registered bar, and it is the fourth consequence row —
NEITHER arm discriminates.** The 20 points `W_PMAX_1H` contributes to the
sentiment score rest on something nobody has shown.

**The daily arm is what makes this more than a power complaint.** The
pre-registration anticipated that one 1H series (≈150 independent windows) could
not settle anything, and named the escape: run the same spread on daily NIFTY
over the longest history available. That arm covers **19 years — 2007 to 2026,
including 2008, 2013, 2020 and 2022** — precisely the regimes in which a
trend-direction filter is supposed to earn its place. **It does not discriminate
there either.** So this is not "we lacked the data"; on the nearby question, the
data exists and the answer is no.

**Every point estimate leans the WRONG way, and that deserves stating carefully.**
All four spreads are negative: the PMax-DOWN state returned *more* than the
PMax-UP state, by +0.58% over 19 years of daily bars and +0.30% at the primary
1H horizon. **Not one of them is significant** (p = 0.306, 0.223, 0.860, 0.488),
so **this is a null, not an inversion** — the desk does not get to claim the
factor is backwards. What can be said is that four independent
timeframe/horizon combinations all point the same wrong way while none reaches
significance, which is the profile of *no information*, not of a hidden
contra-signal.

> [!note] The pre-registered disagreement, resolved — and they were never actually
> in conflict
> The prior said this was the one place skepticism was not automatic, because
> [[#B-32]] measured that **regime carries real information** (+0.22% RISK-ON vs
> **−1.78% RISK-OFF, p<0.005**) while [[#B-65]]'s state arm pointed the other way.
> The result resolves it, and the resolution is a distinction worth keeping:
>
> **B-32 measured how SIGNALS perform conditional on regime. This measures how
> the INDEX performs conditional on trend state.** Those are different claims and
> both can be true. Bullish scanner hits really do fail below the 200 SMA — that
> is about signal quality in a hostile tape — while the index's own forward
> return simply does not depend on whether a trailing band is above or below it.
> **"Regime matters" was never the same statement as "this regime indicator
> predicts the index",** and the sentiment factor makes the second claim while
> borrowing credibility from the first.

**Consequences, following the rules fixed before the run:**

- **Nothing is deleted.** Same rule as [[#B-59r]] and [[#B-65]]: a null is not
  evidence of harm, and the factor is not shown to mislead. `W_PMAX_1H` stays at
  20 today.
- **Re-weighting the sentiment index is now a live proposal with evidence behind
  it** — and, as pre-registered, **that proposal is its own entry, not this one.**
  What it will have to weigh: the remaining three factors (adv/decl 30, sector 25,
  regime 25) are **also unmeasured**, so moving PMax's 20 points into them is
  moving weight from one unvalidated input to three others. That is not obviously
  an improvement and must not be done reflexively.
- **The chart's PMax panel and `market_verdict`'s factor row are untouched.**
  Neither claims prediction; they report a state, and the state is real even
  though it is uninformative about what follows.

**The trailing-stop family is now fully measured, and it is a clean sweep.**
Renko (B-43/B-43r), PSAR and STAI (B-59r), PMax as an entry (B-65) and PMax as
the sentiment factor (B-65r): **five measurements, five nulls, zero deletions.**
Every one was assumed to work before this week and not one had been scored.

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

### ~~B-58~~ · Quasimodo (QM) geometry — **MEASURED 2026-09-11 AT POWER: FAILS THE BAR (5,048 events, edge −0.64%, p_rot 0.120)**
*(The 2026-09-10 "too rare to measure" verdict was itself an artifact — see the re-run below.)*

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

═══ AMENDMENT 2026-09-11 — WIDEN THE WINDOW, CHANGE NOTHING ELSE ══════════

**Written and committed BEFORE the re-run**, because the re-run is the move that
needs a paper trail most: *I already know which way the primary pointed.*

The 2026-09-10 run aborted on power, and its own closing sentence named the two
ways out: *"either the window widens (more history, or intraday bars where the
geometry repeats far more often) or B-58 stays unmeasurable."* This takes the
first. The third option — retire QM on the skeptical prior — is deliberately NOT
taken, because retiring a pattern for being rare is not the same as retiring it
for having no edge, and the page should not record the one as the other.

**Why the count was low, and why this fixes it.** The event rate is a property of
the bar supply, not of the pattern: `cache/cardinality/` holds **743 daily bars
per name** (the `--years 2` build, +1y warm-up), which is ~3 years. 53 events came
out of that. The same 460 names carry **up to ~4,700 daily bars** where the full
history exists, so a deeper cache should clear the floor of 200 on arithmetic
alone. **Nothing about the detector, the event, the baseline, the horizon, the
statistic or the pass bar changes** — only how many bars each name brings.

> [!warning] What this amendment is NOT allowed to do, stated so it can be checked
> **Every parameter stays frozen at its pre-registered value**: event = first
> in-zone close after `rh.bar + pivot_len`, baseline = within ±2% of a confirmed
> prior swing low approached from above, horizon 20d, entry next open, statistic
> `mean(signal) − mean(baseline)`, **pass bar `edge > 0 AND p_rot < 0.05`**, abort
> below 200 events. The ONLY change is the bar supply.
>
> **This is a power fix, and it can only be run once.** The first run reported
> PRIMARY +0.71% with no computable p. If the wider window is allowed to be
> re-cut, re-filtered or re-horizoned until that +0.71% acquires a p, the result
> is not a measurement, it is a search. So: one run, on the frozen design, and
> whatever it prints is the answer — including a null, which on this page now has
> teeth (see [[#B-22r]], where a null cost a factor its vote).
>
> **The deeper cache is written to a SEPARATE directory** (`cache/cardinality_deep/`).
> `cache/cardinality/` is the shared panel behind B-43, B-57 and the DIAGNOSTIC
> arm; overwriting it to serve this item would silently re-cut settled results.

**Two known costs of a deeper window, disclosed up front rather than discovered:**

1. **Survivorship gets worse, not better.** The universe is today's liquid 500,
   so extending backwards asks *"how did today's survivors behave in 2010"* — a
   bias that inflates long-horizon returns. It inflates SIGNAL and BASELINE
   together, which is why this study measures a difference and not a level, but
   the CONTRAST and HARNESS arms (which baseline against all bars) get less
   trustworthy, not more. They were already non-decisive.
2. **Era mixing.** 15 years spans regimes with different volatility and different
   microstructure. The pre-registered statistic is a pooled difference and stays
   pooled — splitting by era after the fact would be exactly the search this
   amendment forbids.

═══ RE-RUN — 2026-09-11, AT POWER: **FAIL** ═══════════════════════════

**VERDICT: FAIL against the pre-registered bar** (`edge > 0 AND p_rot < 0.05`).
**5,048 primary events** — 25× the floor of 200, so this is a real answer and the
INCONCLUSIVE of 2026-09-10 is superseded.

| arm | n | signal | baseline | edge | p_rot |
|---|---|---|---|---|---|
| **PRIMARY** QM zone entry vs retests | **5,048** | +0.82% | +1.47% | **−0.64%** | **0.120** |
| CONTROL CHOCH relaxed, vs retests | 15,391 | +0.99% | +1.47% | −0.48% | 0.083 |
| CONTRAST QM zone entry vs ALL bars | 5,048 | +0.82% | +1.97% | −1.15% | 0.015 |
| HARNESS all retests vs ALL bars | 950,658 | +1.47% | +1.97% | −0.50% | 0.000 |
| DIAGNOSTIC bare Renko flip (= B-43) | 27,728 | +1.94% | +1.97% | −0.03% | 0.947 |

**The prior was right, and the control now says why.** Dropping `RH > LH` moves the
edge from −0.64% to −0.48% while tripling the event count — **the change of character
is doing almost nothing**. That is precisely what the control was pre-registered to
detect: `detect_quasimodo` is an inverse-H&S finder with an extra condition that
does not select. The skeptical prior — *"QM is a liquidity sweep with extra steps"*
— survives, and `Liquidity Sweep` (B-41m, **+0.51% @20d, p=0.005**) remains the
measured way to express the mechanic.

**The HARNESS clause did not fire this time, and that is its own result.** At 950k
retest bars it reads **−0.50%**, finally agreeing with B-19's family numbers
(−0.36 / −0.47 / −0.43% @20d) instead of contradicting them at +1.74%. The
2026-09-10 harness anomaly was a small-sample artifact, and the DIAGNOSTIC arm
reproduces B-43's settled null at −0.03% in both runs.

> [!key-insight] The 2026-09-10 verdict was measuring a DEFAULT ARGUMENT, not a pattern
> The re-run's first attempt widened the bar supply 5.5× (743 → 4,122 daily bars per
> name, 264k → 1.50M bars) and the event count went **53 → 68**. It should have gone
> to ~300. **68/53 is exactly 459/356 — the ratio of NAMES, not of history.**
>
> `detect_structure_chain` defaults to **`max_swings=15`**: it returns only the most
> recent fifteen swings. The study took that default, so its "historical walk" could
> never see more than ~12 candidate quadruples per name however many bars it was
> handed — in practice about **one event per name**. Lifting it took the same
> universe from **68 events to 5,050**, a 74× difference in what the study could see.
>
> So *"a shape this rare cannot be measured to this desk's bar on three years of
> daily bars in one market"* — written up as a scoping fact about the pattern — was
> a statement about a keyword argument. **The equivalence check could not catch it:
> `detect_quasimodo` also looks only at a recent window, so the newest pattern agreed
> exactly as designed. A check that compares the NEWEST event is blind to a missing
> HISTORY.**
>
> Both bugs on this page now have regression tests (`tools/test_quasimodo_study.py`),
> because both produced runs that looked completely healthy.

> [!warning] AMENDMENT 2026-09-11 (second one) — "traded above" now means the HIGH
> With 5,050 events the subset assertion failed again, on **8 events across 7 names**
> — invisible at 68. `support_retests` tested *"price has traded clear above the
> band"* on **closes**. When a QM's structure is compressed inside the ±2% tolerance,
> `LH` itself sits inside the band and no close ever prints above it. COFORGE bar
> 1094: LS 39.16, band 38.38–39.94, post-head rally peaked at **39.75 on closes** — a
> real 9.5% grab and a real CHOCH that the close-based rule could not see.
>
> **"Traded" is what the sentence already said, and `high` is what "traded" means.**
> Like the first amendment this changes only which bars the BASELINE is drawn from:
> the event definition, horizon, statistic and pass bar are untouched, **the event
> count is identical before and after so it cannot buy power**, and it *widens* the
> baseline — the conservative direction, since a wider baseline makes any signal
> edge harder to stand out from.

**Consequence — no code change, which is the point.** `detect_quasimodo` was already
geometry-only: no scanner, no `entry`/`stop`/`target`, `PIPELINE_EXCLUDED`, with a
test asserting the absence of those keys. **The measurement confirms that placement
rather than changing it**, and B-58 closes as a measured FAIL rather than an open
inconclusive.

**This also settles the fib rungs** (row 7 of the 2026-09-07 carry-forward table).
0.886 and 1.13 were added for the QM setups and left drawn-but-unwired, deliberately
gated behind this measurement. The geometry they serve does not beat a plain support
retest, so **adopting either as a `buildPlan` default has no support** — they stay
drawn, and now for a measured reason rather than a pending one.

**Reproduce:** `py -3 tools/qm_deep_cache.py` then
`py -3 tools/quasimodo_study.py --cache cache/cardinality_deep`
(`tools/cache/` is gitignored, so the 1.50M-bar panel is rebuilt, not cloned).

**AUDIT 2026-09-11 — did any OTHER caller take the same default?** Asked because
`max_swings=15` had just invalidated a completed measurement, and
`detect_structure_chain` is shared. **Every `detect_structure_chain` call site was
read. The answer is no — with one real exception, now fixed.**

| caller | swing budget | verdict |
|---|---|---|
| `chart_server` `/structure_chain` | caller's own param | correct — a chart wants the drawable tail |
| `read_market_structure` | passes its own through | correct |
| `detect_liquidity_pools` | **explicit `max_swings=200`**, with a comment saying why | correct, and it had already thought about this |
| `scan_*` via `backtest.py` | default, but replayed as `fn(df.iloc[:t+1])` **per bar** | correct — at each bar a trailing window IS the right window, and every bar gets its own chance to fire. **B-41m's Liquidity Sweep result is unaffected** |
| `quasimodo_study` (the walk) | default → **fixed 2026-09-11** | **the bug.** The only ONE-PASS historical walk in the repo |
| **`detect_quasimodo` itself** | default 15, while filtering to `lookback=120` | **also wrong, fixed here** |

> [!key-insight] The shipped detector's window was not the window it documented
> `detect_quasimodo` asks for 15 swings and then filters them to a 120-bar
> lookback — so the cap was removing history the filter was about to keep.
> **Counted on 200 liquid names: 29% carry MORE than 15 swings inside that
> 120-bar window** (median exactly 15, max 20), and in **2%** the cap cost the
> detector a valid pattern. Now `max_swings=max(15, lookback)`.
>
> **The equivalence check had to follow it, and that is the more interesting
> half.** `verify()` built its comparison walk with the bare default, so until
> today it agreed with the detector *because both were capped the same way*. When
> the detector was fixed, the check broke on exactly the names where the cap used
> to bind. **An equivalence check that agrees because two implementations share a
> bug is not checking anything** — it is the same blindness that let
> `max_swings=15` survive a completed study, in a second place.
>
> **B-58's measurement is unaffected and was re-run to prove it:** the study's walk
> was already uncapped, so PRIMARY is byte-identical at 5,048 events, −0.64%,
> p_rot 0.120. The fix changes what the LIVE detector draws, not what was measured
> — and what it draws is ~2% more instances of a shape that just failed.

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

### ~~B-45~~ · Two indicators are already COMPUTED but not plottable — ATR and MFI — **BUILT 2026-09-11**
From [[analyses/Indicator-Coverage-Gap]]. **MFI** exists as `_mfi_series` and
`scan_mfi_oversold` in `scanner_templates.py`; **ATR** is computed 32× inside
`chart_dashboard.html` (Keltner, PMax, Renko). Neither appears in `INDICATOR_DEFS`, so
neither can be put on a chart. This is wiring, not mathematics, and ATR is the series
stop-sizing actually needs. **Do this before building any new indicator.** No backtest is
owed — exposing an existing series makes no claim about edge.

**SHIPPED 2026-09-11.** `INDICATOR_DEFS` goes 48 → 50: `mfi` and `atr` are both
sub-pane oscillators in the Oscillators group, with teardown wired into the
existing sweep and an alias line each so search finds them by the words people
actually type (*"average true range"*, *"money flow index"*, *"position sizing"*).
Verified in the running chart on `RELIANCE.NS` and `^NSEI` — both panes draw, both
tear down cleanly, console clean.

**ATR reuses `atrSeries`, the same Wilder ATR already behind PMax, Keltner, Renko
and AVWAP.** That is the entire point of the item: no second implementation was
created, so there is nothing new to be wrong. It draws with **no guide lines**, on
purpose — ATR is in price units, so no fixed level means the same thing on a ₹50
stock and a ₹5,000 one, and a line drawn there would be a number pretending to be
a threshold.

**MFI is a port, and it got a parity test — because [[#B-24]] is on this page.**
`mfiSeries` is a line-by-line port of `_mfi_series` (`scanner_templates.py:2366`),
which already feeds `scan_mfi_oversold`. B-24 exists because two RSI-divergence
implementations were left to drift until the scanner fired on bars the chart showed
nothing on. `tools/test_mfi_parity.py` (follows the `test_renko_parity.py` pattern)
slices `mfiSeries` out of the HTML by brace-matching, runs it in node, and compares
it to the Python across five cached symbols: **worst |py−js| = 4.3e-14 over
≈19,000 bars.** The 20-line on the pane is not decorative either — it is the exact
level `scan_mfi_oversold` fires a cross-up through, so the guide line is what the
scanner sees, drawn.

> [!key-insight] The parity test's first run found something the build did not
> **`^NSEI` has 1,333 zero-volume bars out of 4,648 — 28.7%.** yfinance does not
> carry turnover for the index, so **MFI is UNDEFINED over a quarter of NIFTY's
> history** (no down-bar carries volume → negative money flow is zero → the ratio
> has no value). Python yields NaN and the JS omits the point, so the chart draws a
> **gap**, which is the honest rendering. A port that had "helpfully" substituted 50
> or 100 there would have drawn a confident line over 1,333 bars of nothing, and it
> would have looked completely normal. The first version of the test flagged this as
> a FAILURE at 27.9%; the finding was that the threshold was wrong, not the port.
> **This is the counting-first method landing again: the cheap check found the data
> problem, not the backtest.**

**No backtest is owed and none was run** — that claim is unchanged and is why this
was ranked first. Neither series makes an assertion about edge. The MFI *scanner*
remains unmeasured and still folds into [[#B-19]].

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

### B-56 · Structural BUY/SELL/HOLD from POC · HVN/LVN · shape series — **BUILT 2026-09-06, MEASURED 2026-09-17 → INVERTED**

> [!warning] MEASURED 2026-09-17 — the read is backwards, and the mirror was NOT shipped
> 8 symbols, ~4,600 bars each, 36,829 rows. At the pre-registered primary horizon
> (20 sessions): **BUY +0.99% · SELL +2.75% · spread −1.77% · p_rot 0.041**, with
> both floors cleared (4,576 BUY / 2,876 SELL against 200 each) and **SELL beating
> BUY in 8 of 8 symbols** — the consistency is the stronger evidence.
>
> The control passed: **HOLD sat −0.146pp from baseline**, so the rules are not
> just selecting unusual bars.
>
> **Every arm is positive** (BUY +0.99, SELL +2.75, HOLD +0.95, base +1.10)
> because the window is a rising market, so "SELL is followed by a bigger bounce"
> is the signature of **mean reversion**, not of a short signal. The rules seem to
> find a pullback and put the wrong label on it. Flipping them would fit a label
> to a bull-market artifact, so per the pre-registered decision table the mirror
> is a **new hypothesis owing its own test**, not a shipped change.
>
> Nothing deleted. The engine stays, the levels keep drawing, the HVN/LVN role
> naming stays. **Still a bystander: no vote, no score, no confluence weight** —
> and the SVP screen's caption now says all of this on the page.
>
> Full design and result: [[analyses/SVP-Structure-Signal-Pre-Registration]].
> **This was the last built-but-unmeasured signal on the desk.**

**Original entry, kept because the build reasoning is still correct:**

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

**Residual → B-42r — MEASURED 2026-09-17, and it is worse than "coarser".**

> [!warning] The chart and the scanners agree on the headline state 29.6% of the time
> `pivot_len_agreement.py`, 199 nifty500 names, both settings on the same frame:
>
> | field | agree |
> |---|---|
> | **`state`** (the word a reader sees) | **29.6%** |
> | `agreement` (is structure turning) | 35.2% |
> | `zone` (premium/discount) | 57.3% |
> | `trend_from_breaks` | 68.3% |
> | median \|zone_pct\| gap | **42.5 pp** |
>
> Most common disagreement: **DOWNTREND in the scanners against UPTREND on the
> chart, on 17.6% of names.** Not coarser — **opposite**. A reader comparing the
> chart to a scanner hit is comparing two definitions under one word.

**This was measured as an AGREEMENT test, not an edge sweep, on purpose.** The
original note said to settle it with the `--wf` harness. That would have been the
wrong first move twice over: **B-19 already measured these scanners at 0 of 41
stable after costs**, so sweeping `pivot_len` for the best forward return would be
parameter-fitting on detectors with no established edge; and `pivot_len` is a
*definition* rather than a signal — it decides what counts as a swing, so the
question is whether the two are the same reading, which needs no forward return at
all. This is the **[[#B-59]] precedent applied**: the first measurement owed was an
overlap check, not an edge test.

**Promoted from residual to an OWNER decision.** It cannot be quietly unified:
changing either default silently re-grades live output (the [[#B-26]] lesson), and
at 29.6% agreement it would move most names. What "structure" means at each
timeframe is a judgement. Mitigation already in place: every read carries its own
`params.pivot_len`, so a consumer can always say which definition produced the
word — and the number is now in the module note instead of an open question.

**Still unbuilt** (unchanged): consuming the read as an actual *filter* inside the
trend/pullback/SMC scanners, which is a detection change and was out of B-42's
additive scope. Also unbuilt: consuming the read
as an actual *filter* inside the trend/pullback/SMC scanners, which is a
detection change and so was out of this item's additive scope.

**Explicit scope decision (not a task):** the **intraday lane** the "Day/Intraday"
style row implies — **Opening Range Breakout, session-VWAP bounce/rejection as
intraday signals, order-flow/DOM scalping** — is **deliberately out of scope**. The
tool is EOD/daily on NSE and ingests no intraday or L2 depth data; ORB/DOM need a
feed the pipeline does not have. Recorded here so the absence is a decision, not an
oversight. (B-40's VWAP work is the *daily/anchored* slice, which IS in scope.)

---

### ~~B-67~~ · Top Losers was measuring the wrong thing — **BUG FIXED + MEASURED 2026-09-11: CLEAN NULL**

Raised by the owner from the running dashboard: *"top looser need back testing
since figure are doubious"*. The instinct was right, and the reason was better
than "unmeasured" — **the figures were wrong**, and the backtest would have
measured the bug.

**The bug.** `trending_stocks.price_movers_realtime` computed the day change as
`closes.iloc[0]` → last — **the first 5-minute candle of the session**. That is
the move since ~09:20, so it **deleted the overnight gap entirely**, which is
where most of a large loser's move lives. Caught live:

    MVELECTRO   panel said  −3.09%   (basis 858.00 = the 09:20 candle)
                actually    −9.72%   (basis 917.50 = the previous close)

The panel's worst "top loser" that session was −3.22% while the real liquid
cross-section held MONEYBOXX at −17.09% and MVELECTRO at −8.94%. **It did not
merely misprint the numbers, it selected the wrong NAMES** — after the fix, MCX
and WHEELS fall off the list entirely and INDNIPPON / NOVARTIND / FINCABLES /
KEI / VAML / DLF appear.

**Why nothing caught it.** No test asserted what the percentage was measured
AGAINST. The number looked plausible in isolation, and a shallow losers list on a
quiet day is not obviously wrong — which is exactly the shape of the sector-feed
bug this file has hit twice before. `test_trending_movers.py` (7 tests) now pins
the basis to hand-checked arithmetic, including the same-session case where the
bhavcopy's `close` IS today and `prev_close` is the right column.

Two disclosures shipped with the fix, both previously absent: bhavcopy
turnover/volume are renamed `turnover_prev`/`volume_prev` (a day-old traded value
must not sit unlabelled beside a live price), and the caption now says the list
is ranked **within the top 200 by traded value** — the worst of the most-traded,
not of the market.

**Then the measurement** (`tools/movers_edge.py`, pre-registered before the first
run, decision horizon 5d, rotation test decisive). Cross-sectional, so it cannot
use `backtest.py`: "worst 15 of the day" is a rank across names, not a
`scan_*(df)`. Baseline is the **same day's own eligible universe**, which differs
out market drift exactly. NIFTY-500, 2021-09-13 → 2026-09-11, **1,215 scored
sessions** — comfortably over the pre-registered floor of 200.

| leg | 1d | 5d | 10d | 20d |
|---|---|---|---|---|
| **losers** spread | −0.065 (rot p 0.14) | **−0.025 (p 0.92)** | −0.051 (p 0.87) | −0.043 (p 0.99) |
| **gainers** spread | −0.088 (rot p 0.008) | −0.146 (p 0.53) | −0.048 (p 0.82) | +0.352 (p 0.66) |

**VERDICT: NULL on both legs.** Being in the day's bottom 15 tells you nothing
about the next five days that the universe does not already tell you. The losers
leg's absolute return is +0.13% gross at 5d against the universe's +0.16% — i.e.
buying the losers list is buying the market, and paying 0.29% round trip to do it.

Three things worth keeping:

  * **The spread is cost-free by construction** and the code says so. Both legs
    pay the same round trip, so it cancels; costs move the ABSOLUTE return of
    either leg, not the comparison. Quoting "net of costs" on a cross-sectional
    spread without saying this would be theatre.
  * **The planted-effect control is in the test suite**, not just asserted in
    prose. `test_a_planted_edge_is_detected` engineers a +1%/day drift onto the
    loser set and requires the study to find it. A null from a detector that
    cannot see anything is not a null, and this is the cheapest possible guard.
  * **The gainers arm was a control, and it earned its keep**: both tails score
    alike, so whatever small 1-day drag exists is "extreme move", not "loser".
    Note the one nominally significant cell — gainers at 1d, rotation p=0.008,
    spread −0.088% — is **smaller than the 0.29% cost of acting on it**, and is
    reported rather than promoted for exactly that reason.

**What this does NOT settle.** `trending_stocks` already calls its four lenses
*attention lists, not signals*. The null does not make the panel wrong; it makes
the panel exactly what its own docstring says. What it retires is the unstated
habit of reading the losers list as a shortlist — so the result ships as a
**caption on the page**, not as a wiki entry nobody re-reads. Survivorship (today's
NIFTY 500) biases the loser leg UPWARD, so the negative result is if anything
understated.

**Not done, and deliberately:** the fix widened nothing. The panel still ranks
within 200 names by traded value because that is what it always did and changing
the universe mid-fix would have made the before/after incomparable. Whether a
wider universe surfaces different names is its own question.

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

### ~~B-10~~ · Four Nifty-500 symbols uncached — **CLOSED 2026-09-11: it was a hardcoded XBRL namespace prefix, not the symbol filter**
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


**CLOSED 2026-09-11. The five-week diagnosis was wrong in both halves.**

`get_shareholding_filings` was never the problem and NSE was never at fault: the
API returns **22 filings for `BSE`**, same shape as `RELIANCE`, and the symbol
filter passes them all. The failure was two layers down, in `parse_shareholding`.

> [!key-insight] The parser was bound to a namespace PREFIX, and the one company it
> could not read was BSE
> The fact regexes matched `<in-bse-shp:ShareholdingAsAPercentageOfTotalNumberOfShares`.
> **BSE's own filings carry the identical element names under `in-capmkt:`.** The
> element names come from SEBI's taxonomy and are what carry the meaning; the prefix
> is a per-document alias the filer picks, so binding to one was never right.
>
> **It failed in the quietest way available.** No facts matched → `raw` empty →
> `parse_shareholding` returned `None` → the symbol got no cache file. *One missing
> file out of ~1,500 looks like a data gap, not a bug* — which is exactly why it
> survived three re-verification passes and a written diagnosis that pointed at the
> wrong function. **The item shrank from four symbols to one on its own** (the other
> three recovered when `get_shareholding_filings` was rewritten), and that shrinkage
> made the remaining one look even more like an NSE-side quirk.

**Fix:** the prefix is now a wildcard (`[\w.-]+:`) in all three fact regexes, not a
second hardcoded alias — SEBI has already changed this spelling once (the
`Catergory` typo recorded in `CATEGORY_MEMBERS`), so the next vintage must not need
a code change. `xbrli:` / `xbrldi:` stay pinned: those are XBRL's own prefixes,
fixed by the spec rather than chosen by the filer.

**Result:** `cache/ownership/` goes **751 → 752**. BSE reads 5 quarters, totals
reconcile, 52 categories parsed on the newest filing. **Regression checked on
RELIANCE / TCS / HDFCBANK / INFY / ITC: every stored field identical**, so no
cached symbol moves.

**BSE has no promoter, and that is data rather than a gap.** It is a professionally
managed exchange — 100% public, no promoter member in the filing at all — so
`promoter` is `None`. Verified the consumers already guard with
`isinstance(v, (int, float))` (`dashboard_app`, `hidden_treasures_backtest._n`), so
it flows through as "no reading" rather than as **0.0**, which would have read as
*"the promoters sold everything"*. A test pins that contract.

**One observation, deliberately NOT patched:** BSE's `30-JUN-2025` filing states
public **79.43%** against a total of 100%, where every later quarter states 100%.
The missing ~20.57% is not reported as a percentage fact anywhere in that document,
so the parser is faithfully reporting what BSE filed. Inventing the remainder would
be worse than showing the step. Recorded here so the jump in BSE's public series has
an explanation attached.

Tests: `tools/test_shareholding_parse.py` (8), covering both prefixes, an unknown
future prefix, the promoter-less company, and the per-filing percent/fraction scale.

---

## P4 — Scoped elsewhere, or small

| | Item | Notes |
|---|---|---|
| ~~B-20~~ | **Index PCR has no history, so no band** — **STORAGE SHIPPED 2026-09-11**, band still absent | Was: `index_reading()` ships deliberately unbanded, and storing a daily index PCR is the whole fix. B-22's wiring added that store — `sentiment_index.pcr_index_history` (date, symbol, pcr, pcr_chg, total_oi), written on every persisted compute. **This does not close the band**, and deliberately so: the baseline starts at zero rows and `pcr.index_reading()` is untouched, so the OI-Momentum page still shows an honest unbanded level. What changed is that the clock is now running — in ~60 sessions there will be something to rank against. First row: NIFTY PCR 0.7519, ΔPCR −0.0793 (F&O bhavcopy 2026-09-09). |
| ~~B-22~~ | **Sentiment Index factor 5 unwired** — **WIRED 2026-09-11** | `sentiment_index.py` now carries five factors on the roadmap's own pre-registered v1 split (25/20/20/15/20, replacing the 30/25/25/20 that was explicitly the "ships without input #5" fallback). `_pcr_nifty()` → `pcr.load()` → `index_reading('NIFTY')`, stored, then ranked against the stored baseline by `pcr_factor()` (0.7 level-percentile + 0.3 slope-percentile). 14 tests in `tools/test_sentiment_pcr.py`. **Two things to hold onto:** (1) it ships NOT_CHECKED and stays that way until 60 sessions are stored, so the composite excludes it and renormalises — verified live, score 14.97 on 60/100 weight, arithmetically identical to what the old weights produced, i.e. **this wiring moved nothing today and was not supposed to**; (2) the sign is a **guess** — high PCR scored bullish (trend-following), `convention_measured: False` in the persisted inputs, and B-44r is the precedent for why that matters: GEX was retired outright once its naive convention was measured backwards for NSE. **An edge test on the convention is now owed**, and it cannot even be run until the baseline fills. |
| ~~B-23~~ | **Strike-level option OI** (OI audit Gap 3) — ✅ **CLOSED 2026-09-02** | Was: "the largest remaining OI item, needs its own design pass." **The premise was stale** — B-44's `gamma_exposure.py` had already built the per-strike bhavcopy reader this was scoped to design, so the remaining work was the LEVELS read, not the feed. Third stale entry this week after B-11 and B-42. Shipped `option_chain.py`: `load_chain` (per-strike CE/PE OI for **stocks (STO) and indices (IDO)** — `gamma_exposure` is index-only), `max_pain`, `oi_walls`, `read_levels` + `format_levels`, plus `/api/option_levels` on chart_server so B-28's overlay has an interface to consume. 26 tests. Live: NIFTY spot 24,055.80 / max pain 24,050 on expiry day (converges, as theory predicts); RELIANCE 1,308.96 between its 1,300 put wall and 1,320 call wall. **Two correctness rules enforced:** max pain REFUSES a pooled-expiry chain (payoff settles per expiry — a far-month strike does not pay out on this week's settlement, so a pooled number is a different quantity, not a smaller error); and call walls are restricted to strikes at/above spot, put walls at/below, because a large call OI far below spot is deep-ITM inventory and ranking it as "resistance" would put the strongest resistance *under* the price. Levels ship **unmeasured** — see B-28. |
| B-13 | AW-1…AW-4 astro weekly card | Good-to-have; AW-0 shipped. |
| B-15 | SR-7 Trendlyne backfill | Optional, only if XBRL coverage proves short. |
| ~~B-17~~ | ~~OBV has no wiki page~~ — **WRITTEN 2026-09-11: [[concepts/On-Balance-Volume]]**, covering both shipped surfaces. Found while writing it: the draft claim that the reused RSI-divergence engine was unmeasured is FALSE — B-19 scored it (Bull +0.36%/+0.93% on 211 signals, Bear −0.84%/−1.18% on 403, **both UNSTABLE**), and that table is now the nearest prior on the page. An **overlap check against the RSI pane** is recorded as owed before any OBV-divergence signal — a gate, not a study, like B-59's. | Verified absent; ships as a chart indicator, undocumented. **Re-verified 2026-09-10: still absent** (`wiki/concepts/` has `Chaikin-Money-Flow.md` from B-60 and no OBV page) — and the debt **grew**, because B-61 shipped an OBV *divergence* overlay on 2026-09-07. Two OBV surfaces, zero pages. The B-60 ingest is the pattern to copy: the concept page was written with the build. |
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

1. ~~**B-42r**~~ — **MEASURED 2026-09-17: 29.6% agreement on `state`.** Now an owner decision, not a task.
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



## B-76 · The three order-block overlay rules — **MEASURED 2026-09-13: one null, one INVERSION, one undecidable**

The chart's Order Block overlay gained a trade plan, a stacked-zone bias gauge and
an early rejection entry in one session, each taken from the conventional SMC
playbook. [[analyses/Backtest-Harness]] had already measured the **Order Block
Retest** scanner at **−0.74% @20d**, so three new rules were being drawn as precise
numbers on top of a substrate already known to be a null.

Pre-registered first ([[analyses/Order-Block-Rules-Pre-Registration]]), results in
[[analyses/Order-Block-Rules-Measured]]. LIQUID_50 / 1500d, point-in-time, stride 5,
baseline **+0.958% @20d**.

| Rule | Measured | Consequence |
|---|---|---|
| **A** target ladder (opposing zone → displacement → 2R) | **null** — paired Δ p=0.76 gross / 0.64 net; and the surviving 2R plan is **−0.095R NET** (+0.026R gross) | **ladder collapsed to flat 2R**; `rr` removed from payload and label |
| **B** stacked-zone bias gauge | **INVERTED** — bullish lean +0.70% vs bearish +2.19% raw @20d, t=−9.05 gross / −12.79 net | **gauge retired outright** |
| **C** early vs confirmed retest | **undecidable** — p=0.26 on *both* cost bases at n≈175/arm | both kept; no difference claimed |

> [!key-insight] The targets differed; the expectancy did not
> Target-hit rates of **26% / 38% / 34%** prove the ladder's three steps were
> picking genuinely different distances — and expectancy was flat across all of
> them anyway. The ladder bought the appearance of structure, not a better exit.
> Precedent [[#B-74]]: keep the geometry, drop the claim.

**The inversion, and the control that earned the retirement.** Pooled, the bias
gauge was backwards at p=2.3e−19 — but a stacked lean *persists*, so those 8,948
observations are nowhere near independent and that p-value could not carry a
retirement on its own. Re-run with the **symbol as the unit** (50 clusters,
`tools/ob_bias_clustered.py`), the inversion held: bullish lean **−0.373pp**
negative on **38/50** names, bearish lean **−2.361pp** negative on **40/44**.
Mechanism, inferred not tested: in a constructive tape a bearish stack accumulates
after a run of weakness, i.e. the gauge was most bearish at local bottoms.

Retired, not flipped — the stack count also failed to grade monotonically
(1× −0.220, 2× −0.373, 3×+ +0.323), so there was no stable structure to invert.
Same treatment as GEX in [[#B-44r]].

**One decision-rule branch was deliberately WITHHELD.** The pre-registration said
*"C — no difference ⇒ collapse to one marker"*. The test returned p=0.26 at n≈175
per arm, which cannot resolve the 0.92pp difference observed. Applying the branch
would have deleted a distinction on the strength of a test too weak to see it, so
both markers stay and neither is claimed better. **Recording this because the honest
failure mode of pre-registration is mechanical application of a branch whose
precondition — a test with the power to distinguish — was never met.**

**NOT promoted to anything.** The surviving 2R plan is **−0.095R net of costs**
(+0.026R gross) — flat before costs, negative after them — and both retest kinds
sit at or below baseline. The
rails stay drawn as the detector's geometry with the measured number in the code
header. This is a calibration, not a discovery.

**Still owed:** a regime split on B (does the inversion hold in a flat or falling
window — the [[#B-74r]] shape), and a wider universe for C if that distinction ever
becomes load-bearing. Neither blocks the consequences already applied.


## B-77 · The daily jobs were never registered — and one of them could not have run — **CLOSED 2026-09-15**

Raised by [[analyses/Design-Review-2026-09-14]] as the review's only P0. Task
Scheduler held **two** TradingBramha tasks (IntradayUpdate, DailyDigest); the three
the Scheduler Hub defines held **none**. `daily_opportunities` last ran
**2026-09-07**, so Home had been ranking week-old names for five sessions.

**The second defect is the one worth keeping, because registering the jobs exposed
it.** `register_argv` built the Alert Bot's schedule as
`/sc MINUTE /mo 15 /st 09:15 /et 15:45`, which reads like "every 15 minutes between
those times" and is not that. **`/sc MINUTE` is a ONE-TIME trigger with a repetition
attached**: `schtasks` returned SUCCESS, the task showed **Enabled**, the hub showed
it **🟢 registered** — and `Next Run Time` was **N/A**. It would never have fired
again. `/et` was silently dropped too (`Repeat: Until: Time: None`).

> [!warning] A registration that succeeds and never runs is worse than one that fails
> Every surface said green. The single field that said otherwise was one metric on
> the hub, reading `N/A`, next to three that looked fine. **The bug was visible and
> unread** — the same shape as [[#B-69]]'s state label, moved from a docstring to a
> scheduled task.

**Fixed to the form that actually recurs**, verified against a scratch task before
the code changed: `/sc WEEKLY /d MON,TUE,WED,THU,FRI /st 09:15 /ri 15 /du 0006:30`
→ next run reported at the following 09:15. Weekday-only is deliberate: NSE is shut
at the weekend and the previous shape would have been 26 no-op runs a day if it had
worked at all.

| job | task | next run |
|---|---|---|
| Alert Bot | `TradingBramha-AlertWatcher` | Mon–Fri 09:15, every 15 min for 6h30m |
| Daily Scanner | `TradingBramha-DailyScanner` | daily 16:15 |
| Opportunity Shortlist | `TradingBramha-OpportunityDaily` | daily 16:20 |

**Verified by running it, not by registering it.** `TradingBramha-OpportunityDaily`
triggered by hand: universe 500, **576 fetches, 76 candidates**, top 5 stored for
`2026-09-15`, exit **Last Result 0**. The Home map went from the stale chip to
today's names on reload.

**Two surfaces gained a warning, both from this failure's own shape:**
* **Home** — "not today" was a grey caption, which is correct *before* the 16:20 job
  fires and badly wrong *after* it fails. It now counts the **weekdays strictly
  between** the stored run and today: one or more is a missed session and renders a
  **risk-toned chip naming the task**. A Friday run read on Monday counts **zero** —
  the weekend is not a missed session.
* **Scheduler Hub** — a registered job whose `next_run` is `N/A` now says so in
  words, instead of leaving the reader to notice one metric among four.

**Pinned by tests, not by memory** — `tools/test_scheduler_core.py` (12 tests) asserts
the interval job never emits `/sc MINUTE` or `/mo`, that it recurs weekly on the
trading days with `/ri` + `/du`, and that `/et` is gone. The duration arithmetic
covers the market window, a reversed window and malformed input from the hub's own
text boxes.

**Noted, not fixed — 122 yfinance `401 Invalid Crumb` errors across 576 fetches in
that run.** The retry path in `data_source` absorbed them and the shortlist came out
complete, so this is degraded-but-working rather than broken. It belongs in its own
item if the rate climbs; a scheduled job failing this way would be silent.


## B-78 · Two PCR baselines, and the live one was empty — **CLOSED 2026-09-15**

Raised by [[analyses/Design-Review-2026-09-14]]. [[#B-22r]] backfilled **543
sessions** to `cache/pcr/nifty_index_pcr.csv` and measured the sign convention on
them. `--write-db` — the separate, opt-in step that loads that cache into
`pcr_index_history`, the table the **live factor** ranks against — **was never
run.** The live table held **one row**, so the dashboard told the reader

> *"only 0 of 60 baseline sessions stored; an index PCR can only be ranked against its own past"*

about a series that was already two years deep.

**This was not a design disagreement.** The pre-registration always intended the
backfill to land in that table; its warning was about doing it *safely* (historical
dates only, idempotent per `(date, symbol)`, verify today's reading afterwards), not
about avoiding it. All three conditions hold. The step was simply never taken, and
**nothing counted the two stores against each other**, so a month passed.

### The latent bug the fill exposed

`_pcr_nifty` **returns before it records** when a session is illiquid, so the live
table contains liquid days only — never as a filter anyone wrote, purely as a
consequence of control flow. The cache deliberately does the opposite: `backfill`
carries `liquid` *"not filtered on, so the study can apply the production liquidity
floor itself"*, and `pcr_sign_study` duly applies it.

**`write_db` applied neither.** It wrote the cache verbatim, so it would have put
sessions into the baseline that the live path could not have produced — and a
percentile is a statement *about its sample*. Every one of the 543 cached rows
happened to be liquid, so nothing was corrupted. **The two paths disagreed about
what the baseline IS, and were one illiquid session away from that being silent and
permanent.** Fixed to apply production's rule.

### Why filling it was safe, established before it was filled

The obvious fear is that deepening the history **enfranchises a factor B-22r
measured as a null**. It does not, and the reason is worth stating because it is
load-bearing: `pcr_factor` sets `state = NOT_CHECKED` **inside** the `if not
PCR_SCORES` branch, so the composite's `state != NOT_CHECKED` filter excludes it at
any depth. Proven as a pure function first — same PCR, 1-session history vs
543-session: both `NOT_CHECKED`, both `score = 0.0`, only `factor` becoming
computable (0.2554, reported not scored).

Confirmed end-to-end after the write: **composite 16.32 "Strong Sell", coverage
60/100, `excluded = [sector_performance, pcr_nifty]`** — unchanged.

### What the reader sees now

| | before | after |
|---|---|---|
| live table | 1 session | **545** sessions |
| PCR line | "only 0 of 60 baseline sessions stored" | "NIFTY PCR 1.01 — 61st pct of 544 sessions — NOT SCORED: the sign convention was measured (B-22r) and found to carry no direction" |
| composite | 16.32, coverage 60/100 | **unchanged** |

The factor stays under **NOT CHECKED** on the verdict, which is correct — it is
excluded. What changed is that it now says *why* it is excluded (measured, null)
instead of *falsely* claiming there is no history to rank it against.

> [!key-insight] The fix made a string render for the first time, and it was wrong
> Because the history had **always** been below `MIN_PCR_HISTORY`, the branch that
> prints the percentile had **never once executed** on the live surface. Its first
> appearance read **"61th"**. A dead branch is not a tested branch, and filling the
> baseline is what turned it on. Fixed with an `_ordinal` helper that handles the
> 11/12/13 exception, pinned by tests.

### Recurrence

`pcr_backfill` gained `reconcile()` / `--status`, and **every CLI run now prints
both counts** whether or not it wrote. A cache deeper than the live table names the
gap and prints the command that closes it. Reporting only; it never writes.

**Tests:** `tools/test_pcr_backfill.py` (10) covers the liquidity rule, idempotence,
the reconcile gap, and the depth invariant — an existing test pins the null gate
exactly *at* the floor, this one pins it at 544 sessions, because the fill is what
moved the history and a depth-dependent regression would not show at 60. Plus 15
ordinal tests. Suite 490 → 514.

**Not done, and not this item's business:** the `--write-db` step is still manual by
design. What changed is that skipping it is no longer silent.


## B-79 · Three state phrases the surface had outlived — **CLOSED 2026-09-15**

Raised by [[analyses/Design-Review-2026-09-14]]. Three claims on the running desk
were false, and none was a figure, so [[#B-69]]'s `claims_lint` could not see any of
them. All three were re-verified against code before being touched.

### 1. The research notice understated its own rigour

Every page footed with *"Scanner edges shown as measured come from a single
backtest window and carry no significance test yet."* Both halves had been false
for weeks — **B-20a** added the t-test and CI (2026-08-12), **B-21** added
walk-forward pooling and **B-29** the ~29bps cost model (2026-09-01).

> [!key-insight] The correction is a STRONGER warning, not a softer one
> The temptation with a stale caveat is to read it as harmlessly over-cautious.
> It was not. What that measurement actually found was **0 of 41 scanners stable
> across horizons** ([[#B-19]]) — so the honest sentence warns the reader *more*
> than the stale one did. **A caveat that understates the work also understates
> the result.** Now: *"walk-forward and net of Indian delivery costs, with a
> significance test — and of the 41 scanners measured that way, none was stable
> across every horizon."* The scanner count is computed.

### 2. "24 pattern scanners", one hover from a tile that said 46

The Scanner Hub's nav tooltip was typed. The registry holds **46**, and the Home
tile beside it computes `len(sc.SCANNERS)` correctly — so the desk contradicted
itself on one screen. **No count in the code equals 24**: not the registry (46),
not the pipeline (41), not non-Risk (40). It was simply true once. Two further
copies had drifted the same way in `opportunity_daily`'s docstring and a
`dashboard_app` comment; both now avoid the bare number. The tooltip is computed,
as is Home's "across 5 sidebar groups".

### 3. The environments page named the wrong interpreter — and contradicted itself

[[analyses/Python-Environments]] existed because **each interpreter had something
the other lacked**: `streamlit` only in `pythoncore-3.14-64`, `ephem` only in
`Programs\Python314`. **Re-measured 2026-09-15: both now carry the full stack.**
The page's working rule therefore named the wrong interpreter for the dashboard,
and had since `launch.json` switched.

> [!warning] It was self-contradictory, which is worse than merely stale
> The rule said *"verify dashboard-facing work with the interpreter from
> `.claude/launch.json`"* and then printed `pythoncore-3.14-64` in a code block
> beneath it. **The prose named a source of truth and the block hard-coded an
> answer**, so the moment `launch.json` changed the page disagreed with itself.
> Rewritten to name the source, not the answer.

**What is still true is narrower and now points the wrong way.** The split is by
**surface**: dashboard and tests under `Programs\Python314`, scheduled batch jobs
under `pythoncore-3.14-64`. Only one has `pytest`. And the version skew has
**inverted** — `yfinance` is **1.6.0** on the interpreter running the *unattended*
jobs and **1.4.1** where everything is verified, so the nightly shortlist fetches
through a newer library than any test exercises. `scipy` differs too, and that
reaches the significance stack ([[#B-39]]).

### The lint extension — CHECK 3, counts against the registry

`claims_lint` gained a check with **ground truth**, the same shape as CHECK 0 and
deliberately unlike CHECK 2: a count in prose that the code can count and that does
not match. It fires only on a real mismatch, so the normal output is empty and every
line is definitely wrong. Registries are read with `ast`, never imported — importing
`dashboard_app` runs a Streamlit app.

> [!key-insight] The first cut returned 14 hits on the shipped tree and every one was wrong
> Matching "<N> … scanners|pages" caught *"exactly 1 scanner fired"*, *"42 scanners,
> 114 candidates rated"*, *"trimmed 12 scanners over"*, `0.30 x best scanner score`
> (a **decimal** read as a count) and `wiki_lint`'s *"4 pages"* (a different registry
> entirely). **`scanner` and `page` are among the commonest nouns in this repo and
> nearly every number near them counts an EVENT, not the inventory.** No blacklist of
> verbs would have held, so the check was narrowed to noun phrases that only ever
> denote the whole registry. It catches less and is worth more — the alternative is
> output you learn to skim, which is the failure `claims_lint` exists to prevent.

**A measurement result over a past registry is deliberately NOT flagged.** *"0/41
scanners stable"* is true about the run it describes, and rewriting it to 46 when the
47th ships would corrupt a finding. The existing `CONTEXT` vocabulary already
separates the two — the regex CHECK 2 uses to decide a number *is* a measurement,
used here inverted.

**Tests:** 12 added to `tools/test_claims_lint.py`, including all seven real false
positives as regression cases and a guard that the check stays silent on the shipped
tree. Suite 514 → 530.

**Residual:** the check covers scanners, pages and sidebar groups. Indicator counts
live in `chart_dashboard.html`'s `INDICATOR_DEFS` and would need a JS-side count to
be checkable; not built, and not currently drifted.


## B-80 · The verdict degraded by default — **CLOSED 2026-09-15**

Raised by [[analyses/Design-Review-2026-09-14]]. Two independent defects fed the
same STAND DOWN reading: sentiment was only ever refreshed by hand, so the verdict
counted its own staleness as a caution; and sector participation had been
NOT_CHECKED on 8 of 11 indices for weeks.

### The sector half, and the fix that could not be built

The 2026-09-10 pass diagnosed this precisely and deliberately deferred the repair
to its own commit, recording the design in the docstring:

> *"A correct fix widens the window AND bounds the GAP BETWEEN the two bars it
> uses… Not done here — it is a behaviour change to a live component."*

**Re-probed before building it, and that plan is unbuildable against today's feed.**

| tickers | rows at `1mo` / `3mo` / `6mo` / `1y` / `max` |
|---|---|
| the 8 dark ones (`^CNXAUTO`, `^CNXFMCG`, `^CNXENERGY`, `^CNXMETAL`, `^CNXREALTY`, `^CNXINFRA`, `^CNXCONSUM`, `NIFTY_FIN_SERVICE.NS`) | **1 / 1 / 1 / 1 / 1** — one bar, dated today |
| `^CNXIT`, `^CNXPHARMA`, `^NSEBANK` | 20 / 64 / 123 / 246 / **4,674** |

**No second bar at any width means no 1-day change at any width.** The window
could not be widened and there was no gap to bound. On 2026-09-10 `period="3mo"`
still returned 28 rows for `^CNXAUTO`; the feed degraded further in the five days
the item sat. **Counting first is the only reason this was found before the fix
was built rather than after it shipped and quietly did nothing.**

> [!key-insight] A recorded fix is a hypothesis with a date on it
> The design was right when written and wrong when read. This page's standing
> lesson is that *items* go stale; this is the first time a **recorded solution**
> did. Re-probe before building from a plan you did not write today.

**What shipped instead is a source repair, not a redefinition.** NSE publishes
every index's close and `Change(%)` for the session in one CSV
(`ind_close_all_DDMMYYYY.csv`), login-free, on the `nsearchives` host
[[#B-34]]'s constituent fetcher already uses. That is **the same quantity the
factor always claimed** — the sector index's own 1-day move — taken from the
exchange that computes it rather than a mirror that stopped carrying it. So no
pre-registration is owed; a constituent-aggregated substitute *would* have needed
one, and was not built for exactly that reason.

* `sector_rotation.fetch_nse_index_closes` / `nse_index_changes` — walks back over
  weekends and holidays, rejects NSE's 200-status HTML holiday page by content
  rather than status, caches per session date (the published file is immutable).
* All **11 of 11** tickers map to exact NSE index names — verified against a live
  download, no fuzzy matching; an unmatched name is omitted, never defaulted to 0.
* **yfinance is kept as a per-ticker fallback**, and the staleness rule applies to
  both sources — a file found by walking back over a long shutdown is stale for
  exactly the reason a stale bar is.

### This one DID move the score, and that is the point

Unlike [[#B-78]], where the null gate kept the factor excluded at any depth, here
restoring coverage **re-enfranchises a scoring component** (weight 20). That is the
designed behaviour returning after weeks dark, not a new claim — [[#B-66]] measured
this factor as non-discriminating and deliberately did **not** demote it.

| | before | after |
|---|---|---|
| sector indices scored | 3 / 11, below the floor -> NOT_CHECKED | **11 / 11**, all from NSE |
| composite | 16.32, coverage **60/100** | **14.51**, coverage **80/100** |
| band | Strong Sell | Strong Sell |

The drop is the factor doing its job on a broadly red session (1 green / 10 red).

### The refresh half

`sentiment_daily` added to the Scheduler Hub registry
(`TradingBramha-SentimentDaily`, daily 16:30) and registered. **Not folded into
`opportunity_daily`**: nothing in that funnel reads sentiment, so coupling them
would have been a dependency invented for scheduling convenience. Verified by
running the task — clean exit, 0 errors, and it persisted the 14.51 reading with
sector at 11/11.

**Tests:** `tools/test_nse_index_closes.py` (15) covers the map's completeness,
weekend backtracking, the HTML-holiday page, per-session caching, absent-renders-
absent, the staleness rule on NSE dates, the yfinance fallback covering only what
NSE did not answer, an NSE exception not taking the factor down, and the green /
red / flat thresholds surviving the source swap. Suite 530 → 545.

**Residual:** the four NSE sector labels with no index ([[#B-64]]'s deliberate
omissions) are unchanged — this repaired the feed, not the taxonomy.


## B-81 · Land the PEAD walk — **CLOSED 2026-09-16**

The four-quarter post-earnings drift walk had sat uncommitted across a session
boundary. [[analyses/Design-Review-2026-09-14]] found the measurement itself sound
— drift taken from the reaction bar, an unfinished window as `None`, a stale
calendar yielding nothing, all pinned by tests — and flagged three things around
it.

### The frame was chosen by registry order

`_attach_pead` resolved its frame with
``next(n for n in sc.SCANNERS if not sc.SCANNERS[n].get("needs_full_history"))``
— **whichever scanner happened to sit first in the dict.** It worked, and it was
wrong: adding a scanner at the top of `SCANNERS`, or reordering it, would have
silently changed which fetch backed the walk, with nothing to notice.

`fetch_for` discriminates on exactly one thing — the `needs_full_history` flag —
so the honest way to ask is to **say what is wanted** rather than name a scanner
that happens to want the same thing. Added `oh.DEFAULT_WINDOW`, a sentinel that is
deliberately *not* a scanner name, and wrote the contract into
`run_scanner_pipeline`'s docstring: **a factory must answer for a name it does not
recognise, with the default-window fetch.** Both shipped callers already did,
since each looks up `SCANNERS.get(name, {})`; a factory that refuses now makes the
walk go quiet instead of taking a scan of hundreds of names down with it.

`_attach_pead` now takes the **fetch function**, not the factory, so the registry
is out of it entirely — which is the actual repair, not just a renamed lookup.

### Untested surface

12 tests in `tools/test_pead_attach.py`: that attaching never adds or removes a
name (it runs after the filter and is context, never a vote), that one symbol's
failure does not stop the rest, that an empty walk leaves **no key at all**, and
that the archived card's JSON round-trip returns a date as a **string** while a
`None` leg stays `None` — "still running" must not render as a value.

### Verified on real stored data, not only on fixtures

The scheduled job's archived cards for 2026-09-15 carry the walk, and the split is
the designed one:

| name | walk | why |
|---|---|---|
| LAURUSLABS | **4 events**, dates back as strings through JSON | newest cached result 54 days old |
| BODALCHEM | absent | newest cached result **2019-05-21**, 2,675 days |
| SOLARA | absent | newest cached result **2023-01-25**, 1,330 days |
| AHCL, ANTELOPUS | absent | no cached calendar at all |

Two of those have calendars and still render nothing — `MAX_EVENT_AGE_DAYS = 400`
refusing to present a four-quarter walk of 2019 results as current. **Absent
renders absent**, confirmed on live data rather than asserted.

### `.gitattributes`

Every commit printed *"LF will be replaced by CRLF"* per staged file. Harmless, and
it trains you to skim the one channel git uses to speak up. `* text=auto` makes
repository STORAGE uniform (LF) as files are touched; `.bat`/`.ps1` are pinned to
CRLF because cmd.exe wants them and `scheduler_core.write_bat` already emits `
`
deliberately; data and binaries are left alone.

> [!warning] Corrected 2026-09-16, one commit later — the claim was too strong
> B-81 said this "ends the warning on every commit". **It does not, and B-82's very
> next commit proved it**: the message reappears for any file a TOOL writes with LF
> endings, because `text=auto` means the next checkout converts it to CRLF. The
> warning is informational about the working tree, not about anything being wrong.
> What `.gitattributes` actually buys is uniform storage and the `.bat`/`.ps1`
> pinning. A one-off `git add --renormalize .` would settle the remaining mixed
> storage, and is deliberately NOT done here: it would touch hundreds of files and
> bury the diff it travelled with. **Recorded rather than quietly left**, because a
> claim that goes false in one commit is exactly what this page exists to catch.

**NOT promoted to anything.** The walk is context on a card. Nothing scores, ranks
or filters on it, `consistency` is not a validated signal, and the attach stage runs
*after* the survivor filter so it cannot change which names appear or in what order.
Suite 545 → 557.


## B-82 · The wiki lint crashed — and its own clock had stopped — **CLOSED 2026-09-16**

Raised by [[analyses/Design-Review-2026-09-14]] as "fix the cp1252 crash, then work
the list behind it". The crash was the smaller half.

### The clock, which is the finding

`TODAY` was **hardcoded** to `dt.date(2026, 8, 9)` and had stayed there for
**38 days**. Section 5 does not report "pages 30+ days old" — it reported pages 30+
days old *as of a date in the past*, drifting further from the truth every day
nobody edited the line, while **every page updated after 2026-08-09 read as a
negative age**.

> [!key-insight] The lint that exists to find claims which go false with time contained one
> In the single line where time enters it. `claims_lint` hunts figures and
> promises, `wiki_lint` §9 hunts phrases that go false when code ships, and
> neither could see a frozen constant inside the linter itself. Now
> `dt.date.today()`, pinned by a test that fails if anyone re-freezes it and a
> second that asserts **no page reports a negative age** — the symptom, not just
> the cause.

`ROOT` was likewise an absolute path to one machine; a lint nobody else can run is
a lint that only ever gets run here. Derived from `__file__` now.

### The crash

No stdout reconfigure, so it died on a circled digit while quoting a roadmap title.
The vault is full of em dashes and arrows, so this was not exotic — it was what
happened on this machine without `-X utf8`. Fixed the way `claims_lint` already
did, and there is a test that runs the lint with `PYTHONIOENCODING=cp1252` rather
than trusting the fix.

### B-27's actual ask, finally done

`index.md`'s own convention comment has said since 2026-08-07: *"A lint should
COMPUTE both rather than trust them."* It never did. The counters are hand-written
in **two** places — frontmatter and the body's `_Last updated: … | Pages: N …` line
— which is how they drifted to two different wrong numbers before. **Found drifted
again this pass, and this time it was the dates**: frontmatter said `2026-09-09`,
the body said `2026-09-14`, and both said 289 against an actual 294.

Two hand-maintained copies of one fact is not a counting problem, it is a second
source of truth. `--fix-index` writes both from one computation; three tests assert
the two copies agree with each other and with the vault.

### The hygiene, and what was deliberately refused

| | before | after |
|---|---|---|
| index counters | 289 vs 294, two different dates | **computed, OK** |
| dead links | 33 in 15 pages | **7 in 5 pages** |
| frontmatter gaps | 30 pages | **17 pages** |

Fixed only where intent was unambiguous: `[[wiki/index]]` / `[[wiki/log]]` (a
prefix that is not part of any page key), wikilinks pointing at **source files**
(which can never resolve — now inline code), and four bare tickers whose
`entities/` pages exist. Also `[[investment-desk-not-trading-system]]`, which was
a **memory slug that had leaked into a wiki page** as though it were a vault page.

**Refused, and reported instead**, on `wiki_lint`'s own stated rule — *"a wrong
count written confidently is worse than a known-inconsistent one"*:
* `timeframe` on **5 strategy pages** — a strategy's horizon is content, and
  swing-vs-intraday is exactly what a reader would trust.
* `timeframe` on **8 measurement/other analyses** — arguable either way.
* The **7 remaining dead links** point at pages that do not exist
  (`entities/TRENT`, `entities/NIFTY`, `AEGISLOG`,
  `concepts/Relative-Strength-RS`, `strategies/Sector-Momentum-Map`,
  `strategies/FIPA-Quality-Momentum`). Creating stubs would be inventing content;
  an empty page pretends knowledge a dead link at least admits is missing.
* The **12 orphans** are unchanged. `CLAUDE.md` says orphans should be *flagged*
  during lint, and flagging is the designed behaviour — linking them means
  deciding what relates to what.

Dates filled on source pages came from **git history for the file**, derived rather
than guessed.

**Newly visible now that section 5 works:** 248 pages are 30+ days old, oldest 94d.
That number was meaningless while the clock was stopped and is not acted on here.
Suite 557 → 566.


## B-83 · 566 tests, one interpreter, and nothing that ran them — **CLOSED 2026-09-16**

Raised by [[analyses/Design-Review-2026-09-14]]. The suite was good and invisible:
no config, no runner, no CI, and it passed under exactly **one** of the three
Pythons on this machine.

| interpreter | runs | pytest |
|---|---|---|
| `Programs\Python314` | the dashboard (`.claude/launch.json`) | ✅ |
| `Python\pythoncore-3.14-64` | **the scheduled jobs** (every `.bat`) | ❌ |
| `hermes-agentenv` | what a bare `python` resolves to | ❌ (no pandas either) |

So `python -m pytest` in a shell was a coin toss, and the one it most often lands
on cannot import pandas.

### What shipped

* **`pytest.ini`** — the suite ran on *defaults*, not decisions: discovery happened
  to find `tools/`, and the `prepend` import mode happened to put each test's own
  directory on `sys.path`, which is the only reason `import scanner_templates`
  resolves. `testpaths` now bounds discovery, and `norecursedirs` keeps the
  vendored `breakout_scanner/node_modules` tree out — it found nothing there
  today; the point is that **a vendored bundle must never be able to fail this
  project's suite**. `--strict-markers` turns a typo'd marker into an error rather
  than a test that looks configured and is not.
* **`run_tests.bat`** — pins the interpreter, passes arguments through, and fails
  with the install command rather than a traceback when pytest is absent.
* **`tools/requirements_dev.txt`** — pytest was installed into one Python and
  **declared nowhere**. That is the `ephem` (B-14) and `lxml` failure a third time:
  *"installed" true of a machine, not of the project.* Kept separate from
  `requirements_pipeline.txt` because a scheduled job does not need a test runner.
* **An opt-in pre-commit hook** (`tools/install_hooks.bat`). Not installed by this
  session — a hook changes what `git commit` does, and that is the owner's call,
  not a side effect of a session that happened to touch the test setup.

### `--batch`, and the gap it is there to keep visible

The runner will also run under the **scheduled-job** interpreter. It has no pytest,
so today it prints the gap and the install line — and that is the useful outcome:
**the code that runs unattended every evening is never exercised under the
interpreter that runs it**, and that interpreter carries a *different yfinance*
(1.6.0 against 1.4.1, see [[analyses/Python-Environments]]). The report is
deliberately **never a gate**: a dev dependency missing on a second interpreter
must not fail an otherwise-green run, and a test asserts the exit code is captured
before the batch report runs.

### The new failure mode a pin creates, and the test for it

Pinning an interpreter invents a fresh way to be wrong: **the pin can drift from
the one the app actually uses.** That is exactly [[#B-79]]'s environments-page
defect one layer down — prose naming a source of truth with a hard-coded answer
beneath it. So a test reads `.claude/launch.json` and asserts `run_tests.bat` and
the hook both pin the *same* interpreter. If Python moves, the suite says so
instead of quietly going green on a Python the dashboard never uses.

**Two verifications worth recording.** The `for %%A in (%*)` + delayed-expansion
idiom for stripping `--batch` **silently passed the literal text `!ARGS!` through
to pytest** — found by running it, not by reading it; replaced with a `shift` loop
and `call set`. And the hook's degrade-open branches were tested by pointing them
at an interpreter with no pytest and at a path that does not exist: both print the
fix and **allow the commit**, because a broken hook must not block work.

Suite 566 → 574.


## B-84 · "Two dashboards, and start.bat points at the wrong one" — **the premise was wrong. CLOSED 2026-09-16**

[[analyses/Design-Review-2026-09-14]] raised this as an owner decision: *"retire
the Dash app or document it as a second product. Point start.bat at the desk
either way."* Checked before deciding anything, and **both halves of the framing
were false.**

### There are THREE apps, not two

| app | product | stack | port | launched by | history |
|---|---|---|---|---|---|
| `dashboard_app.py` | **the desk** | Streamlit | 8760 | *nothing* — only `.claude/launch.json` | the daily surface |
| `dash_trading_dashboard.py` | **SBC / astro** | Dash | 8050 | `start.bat` | 3 commits, last **2026-08-18 adding features** |
| `sbc_app.py` | SBC (earlier) | Streamlit | — | **nothing at all** | **1 commit, 2026-08-16** |

### `start.bat` was never mislabelled

Its title, banner and window name all read *"SBC Dashboard"*, and it launches the
SBC dashboard. It is doing exactly what it says. **The review read "not the desk"
as "the wrong one"**, and a second product is not a wrong one.

Nor is the Dash app an older version of the desk. It imports **twelve `sbc_*`
modules** plus `signal_processing_engine`, `live_movers` and
`financial_astrology_methods` — and `dashboard_app.py` references **none** of them.
There is no overlap to retire; it covers a vertical the desk does not have.

> [!key-insight] The real gap was the opposite of the one reported
> Not "a launcher pointing at the wrong app" but **"the app everyone uses has no
> launcher at all"**. The desk could only be started from `.claude/launch.json`,
> i.e. from inside Claude Code. `start_desk.bat` now starts it on :8760, each
> launcher points at the other in its banner, and neither changes what the other
> does. Verified by running it: HTTP 200 on :8760, then stopped again.

### The retire candidate is a different file, and it is the owner's call

**`sbc_app.py`** is the dead one: a single commit on 2026-08-16, launched by
nothing, importing only `sbc_scoring` — and **superseded two days later** by the
Dash app's SBC tab, which drives the whole `sbc_*` stack. Its own docstring still
gives a `streamlit run` command nothing else references.

**Not deleted here.** Removing a file is destructive and the evidence, while
one-sided, is circumstantial: it may be kept deliberately as a lighter standalone
view. Flagged with the evidence so the decision is one line of reading, not an
investigation.

### Found in passing, and it is the third time

`dash` was installed on this machine and **declared nowhere** — after `ephem`
(B-14) and `lxml` (the earnings calendar), in the same file that already records
both. Declared now. [[#B-83]] hit the identical pattern with `pytest` on the same
day, which makes four; the shape is always *"installed" is true of a machine, not
of the project.*

**Tests:** 5 added, asserting each launcher targets a file that exists, that the
two do not launch the same app, that the desk launcher pins the same interpreter
and port as `launch.json` (the [[#B-83]] drift risk again), and that `dash` is
declared. One of them was **wrong on first write** — it searched the whole file
and so read the new cross-reference banners as the app being launched; it now
matches the launch line. Suite 574 → 579.


## B-85 · One route for the chart modules — **CLOSED 2026-09-16**

17 near-identical routes, one per browser module. **The duplication was not the
cost.** A running server 404s a module added after it started — observed live on
2026-09-07 (`/psar.js`) and carried in this page as *"restart the chart server"*
on two separate sessions. **A restart is not a fix for a routing table that has to
be edited to learn about a file already on disk.**

> [!warning] The obvious fix was the wrong one, and the count says why
> A blanket `/<anything>.js` is what this looks like it wants. `tools/` holds
> **27 `.js` files and the page loads 17.** The other nine are NODE-side:
> `alert_watcher.js`, the backtest and emit runners, the shared SVP engine.
> Serving those over HTTP would publish internal tooling, including the shape of
> the alert delivery config. **Counting the files before writing the route is the
> only reason that was noticed.**

So the allow-list is read from `chart_dashboard.html`: the page is the authority
on what the browser needs, and nothing else is reachable. Cached on the page's
mtime, so adding a module *and its `<script src>` line* works on a running server.

**Verified against the real server, not only the test client.** A probe module was
404 before its script tag was added and **200 immediately after, with no restart**;
`alert_watcher.js` and `svp_backtest_runner.js` stayed 404 throughout; `/sw.js`
keeps its own route because it needs no-cache headers and root scope, and a static
rule outranks a converter rule in Flask's map. Routes 39 → 23.

18 tests, including every Node script asserted unreachable and three traversal
probes.

---

## B-86 · The security report was a month stale — **CLOSED 2026-09-16**

Re-ran bandit. **HIGH 2 → 0**: both were `shell=True` calls that no longer exist
in the code, still being reported by a file dated 2026-08-15.

### The number that ballooned, and why it was not a regression

The first re-run reported **1,134 LOW** against the old report's 53, which reads
like a collapse. It was `-x` being passed as repeated flags — **bandit takes ONE
comma-separated list, so the exclusions silently did nothing** — and what it was
counting was `assert` in a suite that had just grown to 597 tests. A number that
balloons because the project got *better* is a number nobody reads, which is the
failure mode `claims_lint` exists to prevent. `bandit.yaml` now records the exact
command, and the mistake, so the next run is comparable.

**Baseline, tests excluded: HIGH 0 · MEDIUM 4 · LOW 153.**

### All four MEDIUM read, none fixed by a code change

* **B104 bind-all-interfaces** — **ACCEPTED, and the review's recommendation was
  wrong.** It said default to loopback; that was written without checking what
  binds here. The chart is a **PWA with installed clients** — the 2026-08-29 cache
  regression was found precisely because a fix failed to reach one — and **a phone
  on the same wifi cannot reach 127.0.0.1**. Defaulting to loopback would silently
  break the surface the PWA exists for. Added `--host` instead, so loopback is one
  flag away and the exposure is a decision on the record. What makes it tolerable:
  read-only market endpoints, no credentials, no writes, and [[#B-85]]'s route
  serving only what the page references.
* **B608 × 2 in `portfolio_db`** — **false positives, both.** One interpolates
  column names validated against a whitelist two lines earlier; the other
  interpolates a run of `?` placeholders for an `IN` clause, the canonical safe
  form. No user text reaches either string.
* **B310** — a hardcoded https telegram preview URL. Worth re-reading only if it
  ever becomes caller-supplied.

> [!key-insight] The most useful number in the report is not a security number
> **117 of the 153 LOW are silent exception handlers** — 77 `try/except/pass`
> and 40 `try/except/continue`. That is [[#B-87]]'s "nine silent excepts in
> `dashboard_app`" measured across the whole tree, and it arrived from a tool
> nobody was running for that purpose.


## B-87 · The monolith gets a ratchet, not a refactor — **RATCHETED 2026-09-16, extraction still open**

`dashboard_app.py` is 13,846 lines and grows about 500 a week. The item says
*extract one page per session, ongoing, no big bang* — and **an ongoing item with
no measurement is a wish.** Nothing noticed the growth because no page body can be
unit-tested, which is the problem it describes.

### What was deliberately NOT done

Two things, both because the safe-looking version was the dangerous one.

* **No page extraction.** Page bodies live inline under `if current_page == "X":`
  at module scope and close over module-level state. Moving one is a real refactor
  of the product's main surface with **no page-level tests to catch a mistake**.
  Doing it badly to close a P3 item would be the worst trade on this page.
* **No mass rewrite of the silent exception handlers.** The obvious script —
  regex `except X:` / `pass` into `except X as e:` + a log line — was written and
  then **thrown away**. It rewrites exception signatures across 13,846 untested
  lines to add debug logging: real risk of a shadowed name or a syntax error, in
  exchange for information nobody is currently missing.

### What shipped instead: numbers that can only go down

`tools/test_monolith_ratchet.py` pins four readings, measured with `ast` rather
than grep so they are trustworthy enough to gate on:

| reading | today | ceiling |
|---|---|---|
| lines | 13,846 | 13,900 |
| silent handlers (`except: pass` / `continue`) | 11 | 11 |
| module-level statements | 318 | 320 |
| raw-HTML renders | ~112 | 120 |

**Every one is a debt, not a target.** They may fall freely; raising one requires
editing that file and saying why. A sixth test fails if a ceiling drifts far above
reality, because *a ceiling far above the actual value is not a ratchet, it is
decoration*.

**The count came from a tool nobody was running for it.** [[#B-86]]'s bandit
re-run reported **117 silent handlers tree-wide** — 77 `try/except/pass`, 40
`try/except/continue`. Individually each is a defensible best-effort path; the
total is not, and that is exactly why the number needs a ceiling rather than an
argument.

**Still open:** the extraction itself. The destination (`tools/pages/`) is
documented and deliberately **not created empty** — an empty package is a claim
that work has started.

---

## B-88 · Generated files out of the repo root — **CLOSED 2026-09-16**

The root held **30 `.xlsx`, 19 sector-rotation renders and 5 `.csv`**, every one
gitignored and generated. They broke nothing; they buried the docs, which are the
only things at the root a person is meant to read.

> [!warning] It is not a one-line move, and the reason is in the reader
> The dashboard **reads these back**: `glob("sector_rotation_*.xlsx")`,
> `glob("screener_export_*.csv")`, `glob("sector_rotation_orbit_*.html")` and two
> direct `screener_<today>.xlsx` lookups. **Changing only the writers would leave a
> year of exports invisible to the surface that lists them** — a tidy-up that
> silently deletes history from the reader's point of view is worse than the mess.

So `tools/out_paths.py` owns the question: **new files go to `output/`, readers
search `output/` AND the root, and nothing is moved or deleted.** The root stops
growing, existing files keep working where they are, and the pile drains on its own
as old dated files stop being the newest. Six writers and four readers rewired
across five modules plus the dashboard.

Two details that are decisions rather than defaults:
* **Sorted by FILENAME, not mtime.** Every one of these names carries a `YYYYMMDD`
  stamp, and a file copied or restored later would sort wrongly by mtime while its
  name still says exactly which session produced it.
* **`resolve()` returns `None`, never a non-existent `Path`** — a phantom path is
  what turns "no export yet" into a confusing error three calls later.

**Verified against the real tree before committing:** 23 screener workbooks, 7
sector tables, 7 orbit renders and 1 export CSV all still found, a probe file
round-tripped through `output/`, and the dashboard boots clean with no errors.
16 tests, including one that fails if any writer starts targeting the root again.
Suite 597 → 619.


---

## B-75 · The quarterly profit walk — **BUILT 2026-09-16**

The last of the twelve-item design-review batch that did not need an owner
decision. Scoped on 2026-09-12 with the count already taken, so nothing about the
design changed on contact: **yfinance serves 5-7 quarterly columns, of which only
1-2 carry a year-ago match.** A YoY walk is one or two points and is not a
sequence, so the sequential walk is the only walk this data supports.

That collides with a decision already in the code — `_quarterly_history` uses YoY
*on purpose*, saying "sequential comparison would read seasonality as growth" —
and the collision is **not resolved, it is labelled**. The column is published as
a SHAPE, the tooltip says in as many words that a festive Q3 shows up here as
growth, and nothing about it votes, scores or enters a confluence weight. No
backtest is owed because no claim is made.

### The three ways this column could have lied

| | What a naive version does | What it does |
|---|---|---|
| **Gapped quarter** | bridges Sep→Mar and prints it as one quarter | `?`, the same convention `rs_walk.format_walk` already uses |
| **Loss base** | −100 → −10 computes as **+90%**, reads as growth | `L` — the denominator was a loss, which is the fact worth carrying |
| **Missing figure** | prints `?`, which the reader takes for a calendar hole | the step is dropped; an absent row is not a gapped quarter |

Each is a test. The gap case is not hypothetical: **RELIANCE's frame is missing
2025-09-30**, and the live column reads `+39 → ? → -9 → +23` rather than bridging
it. On the running Watchlist, PINELABS reads `L → ? → +40 → -67` and MOBIKWIK
`L → L → +8 → +74` — both of which a percentage-off-a-loss version would have
printed as growth.

### Behind a button, and not in the monolith

The walk reads `derive_fundamentals` — four yfinance calls per symbol, on tables
that carry eighty names — so it follows the pattern the pledge and price columns
already set: a button fills a per-table session cache, and **a table that was
never filled does not get the column at all.** A column of blanks would read as
"no quarterly history for any of these", which is false.

The four helpers were written into `dashboard_app.py` first, and **[[#B-87]]'s
ratchet failed the build** — 13,930 lines against its 13,900, 323 module
statements against 320. That is the ratchet working as designed on the first
change after it landed. They moved to `tools/profit_walk_ui.py`, which left one
import shim in the monolith and made the module testable without Streamlit.

Mounted on the Watchlist and both Scanner Hub tables. Engine in
`row_metrics.profit_qoq_steps` / `format_profit_walk`, registry entry in
`columns.py`, 12 tests, suite 619 → 631, verified on the running page.

**Carried forward from the design review, still open:** [[#B-73]] (needs the
cadence decision), B-76 residuals, [[#B-56]] (the only built-but-unscored signal
left), B-34r2, B-32r/[[#B-21b]]/[[#B-26]], B-35/B-31/B-30 (parked),
[[#B-46]]/[[#B-47]]/[[#B-48]], B-87's extraction, and the four August P2 items
B-4/12, B-6, B-8, B-9 — all of which need either an owner decision or a
measurement, not a session.


---

## VWAP + EMA — validated against a Spider Software infographic, 2026-09-17

Owner brought a "Trading with VWAP & EMA" card: **SHORT when price closes below
both VWAP and EMA, exit when it closes above both**, plus the note *"for indices
VWAP is applicable only on futures charts, not spot"*. Validated against what
actually ships. Three new items fall out: **B-89, B-90, B-91.**

### What is already here, and in one respect it is better than the card

| The card says | The desk has | Verdict |
|---|---|---|
| VWAP on the chart | `vwap` — **session VWAP, intraday-only** | **present, and stricter** |
| EMA on the chart | `ema9 / ema20 / ema50 / ema200` | present |
| "indices: futures only, not spot" | a **volume guard**, not a symbol list | **present, better founded** |
| EMA cross BUY/SELL | `mabias` — 9/20 arrows, 50/200 GC/DC, verdict card | **present, and richer** |
| price below BOTH -> SHORT | — | **ABSENT -> B-90** |

> [!key-insight] The index caveat is handled by measuring the data, not by naming the instrument
> The card states a rule about *instruments* ("indices are futures-only"). The
> desk enforces the underlying *fact*: `vwapSeries` accumulates only where volume
> exists (`if (cumVol > 0)`), so a feed with no traded volume gets no line.
>
> **Verified both ends, 2026-09-17.** `^NSEI` carries **zero volume on all 2,125
> stored 15-minute bars**; RELIANCE.NS carries real volume on 2,119 of 2,121. And
> driven directly in the browser on synthetic bars: `vwapSeries` returns **25
> points with volume, 0 points with zero volume, and 0 points on `1d`**.
>
> That is the card's caveat, generalised — it holds for any volume-less feed, not
> just Indian index spot, and it cannot go stale when an exchange changes what it
> publishes. The in-code comment records that an earlier version fell back to
> `b.close`, which drew **VWAP as the price line** on a volume-less feed: "the
> most convincing way possible to be wrong."
>
> The daily guard is stronger than anything on the card and is measured: on daily
> RELIANCE bars session VWAP equalled `(H+L+C)/3` on **24 of 24** — a typical-price
> line wearing a VWAP label — so daily draws nothing and Anchored VWAP covers it.

### The card's actual rule is NOT implemented, and the near neighbours point down

The card is a **trend-following state agreement**: price on the same side of both
lines. The two VWAP scanners are neither.

* `scan_vwap_reclaim` (B-40) — uses **rolling n-day** VWAP plus `close > EMA-50`
  as a trend gate, which is the closest thing here. But it is an **event**
  (reclaim / pullback), **long-only**, and its VWAP is not the session VWAP the
  card draws.
* `scan_vwap_mean_reversion` (B-40m) — two-sided, but the **opposite thesis**:
  it trades the stretch *away* from the mean snapping back, where the card trades
  continuation away from it.

**The prior is not neutral, and it is already on this page.** The nearest measured
relatives both failed:

| Rule | Verdict |
|---|---|
| `evmacd` — EVWMA/**VWAP** MACD cross | **NEGATIVE**: no edge; stop-and-reverse **-29%** against buy&hold **+827%** |
| ADX/DI bare cross | **the bare DI cross LOSES** (-0.93% @10d, p=0.02) |
| all 41 scanners, walk-forward | **0 of 41 stable** after costs (B-19) |

Two lagging averages crossed and read as a state is the same shape of construct.
That is a reason to **pre-register before measuring**, not a reason to skip it.

**And the card is a SHORT rule.** This repo already records that shorting NSE cash
for a swing hold is not available to most of its users, so even a working version
is an **exit and avoid** signal for a cash book, not an entry. Scope it that way.

### B-89 · `mabias` ships an EMA-cross verdict on the chart and nothing has scored it — **P1**

The card asks whether EMA-cross BUY/SELL is adopted. **It is** — and it is
considerably more careful than the card: 9/20 cross arrows, 50/200 golden/death
markers, volume-grading of the trigger bar, a whipsaw veto, a braided-MA chop
gate, an extension-distrust tier, and a five-way verdict ladder
(`LONG / SHORT / CHOP / COUNTER-TREND / MIXED`).

**It has never been measured.** No entry in `named_studies`, no study file. It is
chart-only — `mabias` appears in no module outside `chart_dashboard.html`, casts
no confluence vote and is not in `SCANNERS` — so the exposure is bounded. But a
**verdict badge that says LONG or SHORT on the screen is a recommendation**, and
this desk closed exactly that class of debt for [[#B-56]] on 2026-09-17.

**First step:** pre-register, then score the `verdict` as a STATE with a rotation
p-value ([[analyses/SVP-Structure-Signal-Pre-Registration]] is the template —
same shape, same autocorrelation problem). The ladder makes this cheap and
informative: `CHOP` and `COUNTER-TREND` are falsifiable on their own, and if the
chop gates carry no information the ladder collapses to a bare 9/20 cross, which
the ADX/DI result already suggests is a loser.

### B-90 · The VWAP+EMA agreement state — measure BEFORE building — **P2**

The card's rule, stated so it can be argued with: **price closes on the same side
of session VWAP and the EMA**. Intraday only, because that is where session VWAP
is defined — and `intraday_store` already holds 15m bars over ~85 sessions for six
names, so this needs **no new data**, the same discovery that unblocked [[#B-9]].

**Do not build a scanner first.** The honest order is the one [[#B-59]] set: score
the state, with the skeptical prior above written down, and build only on a pass.
Baseline matters more than hit rate here — "price below both averages" selects
downtrends, so it will look right in any falling window without carrying
information. **Frame it as an EXIT/AVOID rule for a cash book**, not an entry.

### B-91 · VWAP draws nothing on index spot and does not say why — **P3, small**

The behaviour is correct and the label is half-right. `VWAP (session · intraday
only)` warns about the **timeframe** and says nothing about **volume**, so on
`^NSEI` intraday a user turns VWAP on and gets **silence** — no line, no reason.
Absent renders absent, which is the desk's rule, but this absence has a cause the
reader cannot see and the card is evidence that people expect the line there.

**First step:** when a selected VWAP yields zero points, say which guard fired —
"no traded volume on this feed (index spot — use the futures chart)" or "session
VWAP is undefined on daily bars — use Anchored VWAP". Two strings, one `if`.
Same class as the [[#B-79]] stale-phrase work.


---

## Flag & Pole — ingested 2026-09-17, and the gap is the PLAN, not the pattern

Owner supplied a Spider Software card, [[sources/Spider-Software-Flag-Pole-Infographic]]:
a vertical **pole**, a shallow counter-trend **flag** (channel / wedge /
triangle), then **entry at the flag break, stop at the far flag boundary, target
= the pole height projected**. Presented in both directions.

**It makes no numeric claim at all** — no hit rate, no sample. Unlike the VWAP+EMA
card there is nothing here to falsify: it is a *construction spec*, and should be
read as one.

### What is here, and what is not

| The card specifies | The desk has | Gap |
|---|---|---|
| Bullish pole + flag | `High Tight Flag` — **one extreme variant** (pole ≥90% in ~40 bars, flag ≤25%) | the **general** bull flag is absent |
| **Inverted** (bearish) flag & pole | — | **entirely absent** |
| Entry / stop / target from the geometry | HTF emits **none of the three** | absent |
| Draw it on the chart | `falling_wedge`, `vcp`, `roundbottom`, `harmonic` | **no flag/pole overlay** |

> [!key-insight] The card's whole content is the plan — and 24 of 31 firing scanners have none
> `scan_high_tight_flag` returns `pattern_type`, `tags`, `reasons`, `score` and
> **nothing else**. It is not alone. Measured across 60 nifty500 names on
> 2026-09-17: **31 scanners fired; only 7 emitted a full `entry`/`stop`/`target`.**
>
> This is not cosmetic. `backtest._simulate_plan` walks entry → stop/target, so a
> scanner with no plan **cannot be scored on realised R at all**. Plan coverage is
> a measurement capability, not a display nicety — which is why it is ranked
> above the new detector in the roadmap.

**And the one flag detector we have is too rare to measure.** [[#B-19]] lists
`High Tight Flag` among **three scanners with too few signals** to score. A ≥90%
pole is the rarest member of the family. That is an argument **for** the general
version — it would fire often enough to be measurable — not against it.

### B-92 · Flag & Pole detector — **BUILT + MEASURED 2026-09-17: bull marginal pass, bear INVERTED**

> [!warning] MEASURED — 248 names, 1,189 bull and 979 bear breakouts
> **BULL: edge +0.71% at 20 sessions, p = 0.0499.** A PASS by the pre-registered
> rule and **marginal in the most literal sense** — it sits on the fourth decimal
> of its own threshold. Nothing at 5 or 10 days (p ≈ 0.86); +2.03% at 60 days.
>
> **BEAR: edge +1.33% at 20 sessions, p = 0.0005 — INVERTED.** Breakdowns were
> followed by the stock going UP more than baseline. **The mirror was not
> shipped**; the card now says STRUCTURE only, and its earlier exit/avoid framing
> is retired — a breakdown followed by strength is not a reason to get out.
>
> **The PLAN beat the entry, and that is the best thing here.** Bull: target hit
> **36.8%** against a 51.6% stop rate, **avg +0.36R** — it loses more often than
> it wins and still pays, which is what a measured move is supposed to do. Bear:
> target 8.6% / stop 77.8% / −0.44R.
>
> **The volume gate was NOT added.** The question PR-3 deferred instead of
> assuming: flags on RISING volume returned 3.52% against 2.38% for flags that
> dried up, so HTF's gate would have removed the better subgroup. Pre-registered
> as non-decisive and the subgroup is small (126 vs 1,063), so it reads as **no
> support for gating**, not "rising volume is better".
>
> **The confound is NOT resolved.** This fires only after a ≥4×ATR thrust, so its
> population is momentum names, and an every-bar baseline does not control for
> that. Nothing at 5d/10d against +2.03% at 60d is the shape a trend confound
> produces. **A momentum-matched control is the next test** and needs its own
> pre-registration; until it runs, the bull edge is not distinguishable from being
> in strong names.
>
> Full design and result: [[analyses/Flag-Pole-Pre-Registration]].

**Build entry, kept because the reasoning still holds:**

> [!key-insight] BUILT — and counting first caught a bug that made breakouts impossible
> `tools/flag_pole.py`, two registered cards (**Flag & Pole**, **Inverted Flag &
> Pole**), both emitting entry / stop / pole-projected target. Registry 46 → 48;
> the PR-2 plan ratchet rose **14 → 16** behind them.
>
> **The first `--count` returned 189 patterns and `broken 0`.** The flag boundary
> included the live bar, so `close > flag_high` was unsatisfiable by construction.
> The boundary is now formed strictly before the bar that breaks it.
>
> **Counts, published:** bull present on **5.1%** of bars (broken out on 0.45%),
> bear 3.3% (0.32%). A flag that has not broken is a WATCH, so the actionable rate
> is the second number. The "any pullback" trap named before the build did not open.
>
> **Coverage, concrete:** on the same sample `High Tight Flag` fired **4** times
> against this detector's **66**. HTF is unchanged and still registered.
>
> **UNMEASURED**, and both cards say so. Justified on coverage; B-19's 0-of-41
> stands. Full write-up: [[analyses/Pattern-Reporting-Enhancement-Roadmap]].

**Original scoping, kept because the reasoning still holds:**

Build `detect_flag_pole` emitting the card's three levels, bull and bear.

**Justified on COVERAGE, never on expected edge.** [[#B-19]] measured 0 of 41
scanners stable after costs; a 47th pattern is not expected to break that. It
closes a named absence and it makes the family measurable.

**The trap, and B-58 is the precedent.** Loosen the pole threshold far enough and
"flag" becomes "any pullback in an uptrend" — which this desk already has as
`Pullback Entry`, **measured NEGATIVE** (−0.43% / −1.12%). B-58's quasimodo work
reported the pattern on **73%** of names until pivots were required to be
adjacent, which cut it to 44%, with the true count **3%**. **Count the hits
before trusting the detector**, and publish the count.

Parameters left open on purpose — each is a decision, listed in
[[analyses/Pattern-Reporting-Enhancement-Roadmap]]: pole size **in ATR** not per
cent, flag retracement cap, whether contracting volume is required (HTF rejects a
rising-volume flag outright, and that reasoning is sound — a flag on rising
volume is distribution into strength), and close-confirmed breakout per this
desk's convention.

**Scope the bear half as EXIT/AVOID.** Shorting NSE cash for a swing hold is not
available to most users of this repo — the same scoping [[#B-90]] carries.

### B-93 · Pattern reporting — the page exists, so this is an enhancement roadmap — **PR-1 is P1**

The owner asked for a pattern reporting page, or a roadmap if one exists.
**Two exist:** **Scanner Hub** (46 scanners on any universe — the real one, and
nothing about it needs replacing) and **Strategy Hub § Chart Patterns**.

> [!warning] PR-1 — Strategy Hub's pattern table presents frozen numbers as live
> `_PATTERNS` in `dashboard_app.py` is a **Python literal of 20 tuples**: stock,
> pattern, bias, publish date, publish price, **LTP and Move %** — all hardcoded.
>
> The caption is honest that the detections are third-party and historical. It is
> **not** honest that the table is **static**: the "LTP ₹" column reads as live,
> and the footer computes *"N above publish price · M below"* from those frozen
> numbers — **a scoreboard over data nothing is measuring.**
>
> Same class as [[#B-79]]'s stale state phrases, and `claims_lint` cannot see it
> because the numbers live in a tuple rather than in prose.
>
> **Honest minimum:** say the block is a fixed August sample and delete the
> computed footer. **Better:** recompute LTP from the price cache the rest of the
> desk already uses, which makes the scoreboard real. Either way it must say which
> — silently refreshing in place is the [[#B-26]] error.

Full four-rung roadmap in [[analyses/Pattern-Reporting-Enhancement-Roadmap]]:
**PR-1** the static table (the only rung that fixes something currently
misleading), **PR-2** trade-plan coverage as a visible metric, **PR-3** the B-92
detector, **PR-4** the chart overlay.


## Outcome (fill in later)

## Related Pages

- [[analyses/Open-Backlog-2026-08-02]] — the snapshot this supersedes
- [[analyses/Backtest-Harness]] — where most of P1 lands
- [[analyses/OI-Momentum-Gap-Audit]] — source of B-19b and B-23
- [[analyses/Dashboard-UI-Roadmap]] — the M1–M4 spine
