---
title: "Qullamaggie Edge Study (B-147) — Breakout and Episodic Pivot on NSE"
category: analysis
tags: [b-147, b-147b, qullamaggie, breakout, episodic-pivot, momentum, edge-study, pre-registered]
timeframe: swing
created: 2026-10-14
updated: 2026-10-14
sources: 0
related:
  - strategies/Qullamaggie-Momentum-Setups.md
  - analyses/Open-Backlog.md
---

# Qullamaggie Edge Study (B-147, B-147b)

## Pre-registration — written 2026-10-14, BEFORE any run

**Question.** Do the desk's daily-bar versions of Qullamaggie's two long setups —
`Qullamaggie Breakout` and `Episodic Pivot` (`tools/scanner_templates.py`) — pick
bars with better forward returns than an ordinary bar of the same stock, and do
they deliver the right tail his method depends on?

**Data.** `tools/cache/cardinality_deep/` — 459 liquid NSE names, ~19 years of daily
bars (1.50M bars). Warm-up 252 bars per symbol. NIFTYBEES from the same cache is the
NIFTY 50 proxy for the market filter (2009 onward).

**Signals (actionable only).**
- *Breakout*: the scanner returns a card with the `Breakout` tag (close above the
  base pivot on ≥ 1.5× the prior 20-day volume). Pre-breakout cards are not trades
  and are excluded. A 10-session cooldown per symbol after each counted signal, so
  a breakout that keeps firing on following days is one event, not ten.
- *Episodic Pivot*: the scanner fires on the gap day itself (`max_bars_ago=0`).
- Entry = the signal-day close. Stop = the signal-day low (the daily proxy for his
  low-of-day stop; his real entry is intraday and tighter — this is a different,
  later, wider trade, and the result speaks only for this version).
- A vectorised pre-filter selects candidate bars using only conditions the scanner
  itself requires (volume multiple, MA alignment, gap size); the scanner then
  decides. The pre-filter can drop no signal the scanner would have fired.

**Primary test (decides the verdict).** Forward return from the entry close at
5 / 10 / 20 / 60 sessions, net of 29 bps round trip. Paired by symbol: per symbol,
mean signal return minus mean all-bar return (the baseline); one-sample t-test on
those differences, symbol as the unit. α = 0.05 / 4 = 0.0125 per horizon
(Bonferroni). **Decisive horizon: 20 sessions.**
- **PASS**: 20d difference > 0 with p < 0.0125.
- **NEGATIVE**: 20d difference < 0 with p < 0.0125.
- **NULL**: otherwise, with ≥ 20 symbols contributing.
- **INCONCLUSIVE**: fewer than 20 symbols with a signal.

**Right tail (pre-specified, reported with intervals; does not change the verdict
label above but is reported beside it).** A 25–30% win rate is expected, so a
hit-rate reading would misjudge the method. Plan per trade: R = entry − stop;
exit at the stop if a later low reaches it (−1R; if the stop and a target are both
touched on one day, the stop is assumed first), else on the first close below the
10-day SMA (his trail), else at the 60th session's close. Costs charged in R.
Reported: share of trades reaching +3R and +5R before the stop; win rate; average
winner ÷ average loser; expectancy in R. The SAME plan on a fixed random sample of
ordinary bars (up to 100 per symbol, seed 147) is the baseline. 95% interval on the
expectancy difference (signal − baseline) by bootstrap over symbols (2,000 draws).

**Splits (secondary, descriptive — no verdict rides on them).**
1. Momentum longs ON vs OFF — NIFTYBEES SMA10 above SMA20 on the signal date (his
   market filter). Only signals from 2009 onward have a reading.
2. Episodic Pivot: earnings vs non-earnings — an earnings date in
   `cache/earnings/` within the 3 calendar days up to and including the gap day.
   Restricted to 2021 onward, where the calendar has coverage; earlier EPs are not
   classified rather than called non-earnings.
3. Era robustness — the 20d paired difference in three equal date-thirds.

**What would NOT be claimed.** Any result for his intraday opening-range entry; any
split as a finding unless it is pre-registered as a test later.

## Results

*(appended after the run — nothing above this line is edited once the run starts)*

**Run 2026-10-14** — `tools/qullamaggie_edge_study.py`, result file `tools/cache/qm147_result.json`.
436 symbols with enough history (1.48M bars). Deterministic: a re-run reproduced every
pre-registered number.

### Verdicts (pre-registered)
| Scanner | Signals | Symbols | 5d | 10d | **20d (decisive)** | 60d | Verdict |
|---|---|---|---|---|---|---|---|
| Qullamaggie Breakout | 3,672 | 400 | +0.29 (p 0.060) | +0.39 (p 0.078) | **+0.67 (p 0.031)** | +1.76 (p 0.005) | **NULL** |
| Episodic Pivot | 320 | 171 | +0.36 (p 0.55) | −0.24 (p 0.76) | **+0.47 (p 0.68)** | +6.16 (p 0.026; median +0.05) | **NULL** |

Points of forward return over the same stock's ordinary bar, net of 29 bps, symbol as the
unit; bar p < 0.0125. **The breakout leans positive at every horizon and clears the bar at
60d, but the pre-registered decisive horizon is 20d, where it misses.** That is a reason
to look again under a new pre-registration, not a finding. The EP's 60d mean is carried by
a few large winners (median +0.05).

### Right tail (pre-specified, reported beside the verdict)
| | Trades | Win rate | +3R before stop | +5R before stop | Avg win ÷ avg loss | Expectancy |
|---|---|---|---|---|---|---|
| Breakout | 3,581 | 33% | 19.1% | 9.0% | 2.66 | +0.18R |
| Episodic Pivot | 314 | 34% | 18.2% | 8.6% | 2.46 | +0.15R |

Win rates sit where his method expects (25–35%) and winners are about two and a half times
the losers. **The pre-registered baseline for this table is void:** the same plan on an
ordinary bar puts the stop at that bar's low, which is often a hair below the close, so R is
near zero and its R-multiples explode (baseline avg win 14.5R, expectancy +1.05R). Comparing
R against that is meaningless, and no claim is made from it.

**POST-HOC (added after the run, labelled as such):** the same plan in PERCENT, which has no
such denominator — Breakout **+0.73% a trade vs +0.12%** for ordinary bars (symbol-bootstrap
95% interval on the difference **+0.29 to +0.99 points**); EP +0.15% vs +0.12% (−1.23 to
+1.23). A lead for the breakout, to be pre-registered before it is believed.

### Splits (descriptive — raw 20d means, NOT adjusted for the stock's baseline)
- **Market filter (NIFTYBEES SMA10 > SMA20): did not help.** Breakout 20d +2.95% with it ON
  (n=2,786) vs +3.30% OFF (n=730); EP +3.09% ON (172) vs +4.78% OFF (117). Pre-2009
  signals (no reading) were negative for both.
- **EP earnings vs non-earnings, 2021+:** +8.89% @20d (n=21) vs −0.73% (n=33). Too few to
  call; the direction matches his preference for earnings EPs.
- **Eras (20d):** Breakout +2.13% / +3.03% / +2.92% across 2007–15, 2015–21, 2021–26 —
  raw mean positive in all three. EP +2.71% / +0.15% / +4.49%.

### What changed in the code
- Both scanner descriptions cite the result instead of "UNMEASURED".
- Opportunity Hub tier: unmeasured (0.50) → **weak (0.25)** for both — the desk's rule for
  measured-and-not-shown-to-beat-the-baseline (VCP precedent).
- `named_studies.STUDIES` gains B-147; the market_verdict comment on his filter notes it did
  not help here.

---

## B-147b — confirmatory re-test of the Breakout lead

### Pre-registration — written 2026-10-14, BEFORE any B-147b run

**Why.** B-147 left two leads for the Breakout and no claim: (1) the post-hoc percent-plan
comparison (+0.73% vs +0.12% a trade), which was chosen *after* seeing the data and whose
baseline puts the stop at an ordinary bar's own low — a different trade with a much
tighter stop; (2) the +1.76pp @60d reading, which was not the decisive horizon. Both were
read off the same 436 names × 19 years. B-147b tests them once, on data B-147 never touched,
with the stop-distance mismatch removed. The Episodic Pivot is not re-tested (no lead).

**Out-of-sample universe (decisive).** Every NSE symbol with a daily file in
`cache/multibagger_bars/`, `cache/cardinality/` or `cache/svp_bars/` whose name has **no**
file in `cache/cardinality_deep/` — names B-147 never saw. Per name, the file with the most
bars is used (ties: multibagger_bars, then cardinality, then svp_bars). Excluded: the B-147
SKIP list and any name ending in `BEES` or containing `ETF` (funds, not stocks). The same
`_load` as B-147 (≥ 323 clean bars). Before writing this only file counts, bar counts and
first/last dates of these folders were inspected — no returns, no signals. Known
differences, stated now so a NULL is not explained away later: these are mostly small/
micro-caps (`multibagger_bars`, ~6 years, 2020–26), so signals start ~2021 and 29 bps
under-states their real cost; one market regime (2021–26) dominates.

**Signals.** Unchanged from B-147: `qullamaggie_edge_study._signals` (actionable Breakout
card, 10-session cooldown, warm-up 252). Entry = signal close.

**Hypothesis (a) — DECISIVE: the percent plan beats a stop-matched ordinary bar.**
- Signal trade: B-147's plan unchanged — stop = signal-day low; exit at the stop if a later
  low reaches it (stop first if both touch one day), else the first close below SMA10, else
  the close of session 60; return in percent, net of 29 bps.
- Baseline trade: the SAME plan on ordinary bars of the same symbol, except the stop is
  `entry − k × ATR14` (ATR14 = simple 14-bar mean of true range ending on the entry bar).
  `k` is fixed BEFORE the out-of-sample run, from the **in-sample** B-147 breakout signals
  (`cardinality_deep`): the median of (close − low) / ATR14 on the signal day. Only that
  geometry is read in-sample, no outcomes. Up to 100 ordinary bars per symbol, drawn
  uniformly from bars with a full 60-session future and ATR14 > 0 (numpy seed 1472, files in
  sorted order).
- Test: per symbol, mean signal-trade % minus mean baseline-trade %; one-sample t-test on
  those differences, symbol as the unit, two-sided.

**Hypothesis (b) — secondary, pre-registered: the 60-session forward return.** Net 60d
forward return from the signal close, paired by symbol against the same stock's all-bar
60d mean — B-147's primary statistic, at 60d, on the new names.

**α.** 0.05 / 2 = **0.025** for each of (a) and (b) (Bonferroni over the two).

**Verdict (rides on (a) only).**
- **PASS** (index verdict POSITIVE): (a) difference > 0, p < 0.025, ≥ 20 symbols.
- **NEGATIVE**: (a) difference < 0, p < 0.025.
- **NULL**: otherwise with ≥ 20 symbols. **INCONCLUSIVE**: fewer than 20 symbols with a trade.
- (b) is reported beside the verdict with its own p against 0.025; it does not change the
  label. A PASS on (a) with (b) failing is written as exactly that.

**Reported beside the verdict (descriptive — no verdict rides on them).**
1. Symbol-bootstrap 95% interval (2,000 draws, seed 1472) on the (a) difference.
2. The OOS signals' own median (close − low)/ATR14, to show how well the in-sample `k` matches.
3. (a) with costs at 60 bps (small-cap realism).
4. A trend-matched baseline: ordinary bars restricted to close > SMA10 and SMA10 > SMA20 —
   does the breakout add anything over merely being in an uptrend?
5. **In-sample re-read**: (a) with the stop-matched baseline on `cardinality_deep` — the
   corrected version of B-147's post-hoc number. Labelled in-sample; not evidence.

**What would NOT be claimed.** A PASS speaks for the daily-bar breakout with a signal-low
stop and SMA10 trail on these names and years — not his intraday entry, not large caps
outside the sample, and not a tier change by itself (the tier is the owner's call).

### B-147b results

*(appended after the run — the B-147b pre-registration above is unedited)*

**Run 2026-10-14** — `tools/qullamaggie_breakout_retest.py`, result file `tools/cache/qm147b_result.json`.
Deterministic: a second run reproduced every number. In-sample `k` = **1.317** (median
(close − low)/ATR14 over 3,656 in-sample breakout signals); the out-of-sample signals' own
median is 1.370, so the stop match holds. Out of sample: 424 unseen names, 397 usable, **874
breakout signals on 290 symbols** (first signal 2021-09-17).

#### Verdict (pre-registered)
| Test | Symbols | Signal trade | Baseline trade | Paired diff (mean / median) | p | Bar | Result |
|---|---|---|---|---|---|---|---|
| **(a) % plan vs stop-matched bar — decisive** | 290 | +0.42% | +0.09% | **+0.09pp** / −1.59pp | **0.85** | 0.025 | **NULL** |
| (b) 60d forward vs same stock's all-bar mean | 290 | — | — | +0.47pp / −1.68pp | 0.68 | 0.025 | not passed |

**B-147b: NULL.** On names B-147 never saw, the breakout's percent plan does not beat the
same plan on an ordinary bar of the same stock with a matched stop: +0.09pp a trade, 37% of
symbols positive, bootstrap 95% interval −0.56 to +1.00pp. The 60-session lead does not
carry over either (+0.47pp, p=0.68, median symbol negative). Neither B-147 lead confirms.

#### Descriptive (no verdict rides on these)
- **Trend-matched baseline** (ordinary bars with close > SMA10 > SMA20): −0.06pp (p=0.90).
- **Costs at 60 bps:** signal +0.11% vs baseline −0.23% a trade. The paired difference is
  unchanged (+0.09pp), because a flat cost moves both sides equally — this item, as
  pre-registered, could only ever move levels, not the test. Recorded as a design slip.
- **In-sample re-read on `cardinality_deep`, stop-matched baseline (not evidence):** +0.51pp
  paired (p=0.028, CI +0.16..+0.85). Pooled, the B-147 post-hoc gap (+0.73% vs +0.12%,
  +0.61pp) becomes +0.74% vs +0.25% (+0.49pp) once the baseline's stop is matched; against a trend-matched baseline it falls to
  +0.23pp (p=0.32). Most of the in-sample "edge" was the breakout being in an uptrend. The
  in-sample 60d reading reproduces (+1.73pp, p=0.006) — and does not replicate out of sample.
- **Universe caveat (stated in the pre-registration):** the out-of-sample names are mostly
  small/micro-caps over 2021–26, one regime. A NULL here does not prove the breakout is
  worthless on large caps; it means the B-147 leads did not survive the only independent
  data the desk has.

#### Found in passing
- `cardinality_deep` holds 12 funds (BANKBEES, GOLDBEES, LIQUIDBEES, SILVERBEES, …);
  B-147's SKIP list excludes only NIFTYBEES and HDFCNIFTY, so its 436 "symbols" included 10
  ETFs (16 of its 3,672 breakout signals). B-147b's in-sample re-read excludes them (426
  names). Too small to move B-147's verdict; not corrected in B-147's pre-registered code.

#### What changed
- No tier change proposed: the test did not pass, so both scanners stay **weak (0.25)**.
- `named_studies.STUDIES` gains B-147b (NULL).
