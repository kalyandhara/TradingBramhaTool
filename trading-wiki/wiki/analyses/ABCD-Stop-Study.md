---
title: "AB=CD Stop Study (B-132) — is the edge lost to a stop that is too tight?"
category: analysis
tags: [b-132, harmonic, abcd, stop-placement, plan, edge-study, pre-registered]
timeframe: swing
created: 2026-10-14
updated: 2026-10-14
sources: 0
related:
  - analyses/Open-Backlog.md
  - concepts/Chart-Patterns.md
---

# AB=CD Stop Study (B-132)

## Pre-registration — written 2026-10-14, BEFORE any run

**Why.** The B-129 re-measure (`tools/harmonic_bull_remeasure.py`, 2026-10-05) found
bullish AB=CD signals positive @20d in 3 of 3 windows (clustered p = 0.0066), yet the
card's plan returned −0.17R with 68% of plans stopped out. The card's stop is D − 0.5% of
D — on a typical NSE name, a fraction of one day's range. The question: **is the signal's
edge being given away by the stop?** Owner chose to pursue it (2026-10-14).

**What is held fixed.** The signal set is the AB=CD-only arm of B-129r, unchanged: the
registered `Harmonic Reversal (XABCD)` scanner (bullish only, R:R-to-T2 ≥ 1.5 gate on the
card's own stop), filtered to `AB=CD` hits. Entry = the card's entry (D); target = T2
(0.618 of CD); time stop = 10 bars; harness = `backtest.backtest_scanner` with
`COST_INDIAN`, `signal_mode="fresh"`, `fill_model="market"` (next open) — B-129r's settings.
**Only the stop changes.** A bullish AB=CD has no point below D (there is no X), so a
structural stop "beyond the BC leg" does not exist for it; the alternative is a stop sized
to the stock's volatility.

**Arms.** ATR14 = Wilder ATR on the signal bar (`scanner_templates._atr_series`).
- **A0 (control)** — the card's stop, D − 0.5%·D.
- **A1** — D − 1.0 × ATR14.
- **A2** — D − 2.0 × ATR14.

**Fresh panel.** `nse_universe.symbols("nifty500")` names **301–500** (B-129r used the
first 300), 1,500 days, daily, fetched the same way as B-129r.

**Measure.** Because a wider stop makes R bigger, R is not comparable across arms; the
primary measure is the plan's return in **percent of entry**, net of costs:
R × (entry − stop) / entry for each simulated trade.

**Primary tests (decide).** For each of A1 and A2: per symbol, mean plan % on that arm
minus mean plan % on A0 (symbols with trades on both); one-sample t-test across symbols,
two-sided. α = 0.05 / 2 = **0.025** per arm.

**Decision rule.**
- An arm **SHIPS** as the AB=CD card's stop if (i) it beats A0 with p < 0.025, AND (ii) its
  own plan % is positive: pooled mean > 0 and the per-symbol mean > 0 with one-sample
  p < 0.05, AND (iii) ≥ 30 symbols and ≥ 150 trades on that arm. If both arms ship, the one
  with the larger mean difference.
- Otherwise **NO CHANGE** — the card keeps D − 0.5%.
- Tier: this study does **not** change the Harmonic scanner's tier. If an arm ships, the
  B-129r promotion check is re-run on the full scanner with the new stop before any tier
  talk — and that is the owner's call.

**Reported beside the decision (descriptive).** Per arm: n trades, target / stop / time-exit
rates, avg R, mean plan %. The AB=CD **signal** edge @10/20/60d on the fresh panel — B-132's
premise, re-read out of sample. Plans unfilled / filled through the stop.

**Prior (written down so a positive has to beat it).** A1 or A2 beats A0 on plan % — a
wider stop should convert many of the 68% stop-outs — but whether the plan turns positive
is open: the 10-bar time stop and a T2 target were set for the tight stop.

## Results

*(appended after the run — nothing above this line is edited once the run starts)*

**Run 2026-10-14** — `tools/abcd_stop_study.py`, result `tools/cache/abcd_stop_study.json`.
200 names requested, 183 with AB=CD trades; 1,405 fresh signals. **Decision: SHIP A2.**

| Arm | Stop | Trades | Plan % / trade | Per-symbol p (own) | vs A0 | Target / stop / time exits | avg R |
|---|---|---|---|---|---|---|---|
| A0 | card, D − 0.5% | 1,315 | **+0.01%** | 0.81 | — | 25% / 67% / 8% | −0.16R |
| A1 | D − 1 × ATR14 | 1,374 | **+0.40%** | 0.039 | +0.37pp, p 0.010 | 34% / 40% / 26% | +0.04R |
| A2 | D − 2 × ATR14 | 1,385 | **+0.56%** | 0.012 | **+0.52pp, p 0.0019** | 36% / 21% / 43% | +0.04R |

Both wider stops pass every pre-registered condition; A2 has the larger gain and ships.
The control reproduces the B-129r picture out of sample (−0.16R vs −0.17R, 67% vs 68%
stopped), and the **signal** edge holds on the fresh names too: +0.84 / +0.89 / +1.12% at
10 / 20 / 60d — B-132's premise confirmed on data it was not found on.

**Read with care.**
- The win is in the plan, not a new signal: same 1,405 signals, only the stop moved.
- With the stop wider, 43% of A2 trades now leave on the **10-bar time stop** — the
  pattern's resolution window, set for the tight stop. The time stop was held fixed here
  by design; whether it is now too short is a separate question, not answered here.
- avg R reads +0.04 for both wide arms because R itself grew; the percent figure is the
  comparable one.

**What changed.** `scanner_templates.scan_harmonic_reversal`: for AB=CD only, the card's
stop is now D − `ABCD_STOP_ATR` (2.0) × ATR14; the R:R gate still uses the original stop,
so the signal set is the measured one. XABCD stops unchanged. The Harmonic scanner's
tier is **not** changed — re-running B-129r's promotion check with the new stop is the
next step if wanted, and the tier is the owner's call.

## B-132r — tier re-check with the new stop

### Pre-registration — written 2026-10-14, BEFORE `tools/harmonic_tier_recheck.py` was first run

**Why.** B-132 shipped D − 2×ATR14 as the AB=CD plan stop. Its pre-registration said that
before any tier talk, B-129r's promotion check is re-run on the full scanner with the new
stop. This is that re-run. Nothing in B-129r's rule is changed.

**What is re-used, unchanged.** `tools/harmonic_bull_remeasure.py`'s `summarise`,
`clustered` and `decide` (imported, not edited), its arm wiring and its constants.

**R0 reproduction gate — run, not skipped.** Exactly B-129r's R0: XABCD-only bullish on
`backtest.LIQUID_50`, 3 windows, `COST_INDIAN`, `signal_mode="all"`,
`fill_model="assumed"`, 1,500 days; PASS if n within ±15% of 116 and pooled @20d edge
within ±0.30pp of +1.07%. The stop change does not touch XABCD or any signal, so R0 should
pass as it did on 2026-10-05 (n=115, +1.08%); it is run anyway because it is what detects
that the data or the code moved underneath. If it fails, the panel is not read.

**Panel.** B-129r's own: `nse_universe.symbols("nifty500")`, **first 300 names**, 1,500
days daily, `COST_INDIAN`, `signal_mode="fresh"`, `fill_model="market"` (next open), fixed
exits with the card's time stop, 3 non-overlapping walk-forward windows. This is the
comparable choice. These 300 names helped choose nothing in B-132 — B-132 picked the stop
on names 301–500 — so for the stop they are out of sample. (They are *not* out of sample
for the signal: B-129r already measured these same signals on them.)

**Arm that decides.** **P** — the registered `Harmonic Reversal (XABCD)` as it votes today
(bullish XABCD + AB=CD, AB=CD plans on the new stop). PX and PA are not re-run; B-129r
already reported them and the stop change does not alter which signals fire.

**Rule — B-129r's five conditions, all on P, unchanged.**
1. floors: ≥ 150 signals and ≥ 30 symbols with a signal
2. pooled edge @20d > 0 AND positive in 3 of 3 windows @20d
3. positive in 3/3 windows at one more of {10d, 60d}
4. clustered: per-symbol mean edge @20d > 0, one-sample t across symbols, p < 0.05
5. pooled plan avg_R > 0 under market fill

All five → **PROMOTE** recommendation. Pooled @20d < 0, negative 3/3, clustered p < 0.05
with a negative mean → **RECOMMEND EXCLUSION**. Floor 1 fails → **INCONCLUSIVE**.
Otherwise **STAYS WEAK** (0.25).

**Descriptive only (does not enter the rule).** Pooled plan return in % of entry, net
(R × risk / entry, as in B-132), and target / stop / time-exit rates on P — because a
wider stop makes R bigger, avg R alone understates or overstates the change.

**Output is a RECOMMENDATION only.** `opportunity_hub.py` tiers are not edited by this
study; the tier is the owner's call.

**Prior (written down so a positive has to beat it).** **STAYS WEAK.** Conditions 1–4 read
the signal, and the stop change does not move any signal: B-129r's P passed 1, 3 and 4
and **failed 2** (window 2 @20d −0.03%). Unless bars added since 2026-10-05 flip that
window, condition 2 still fails and the scanner cannot promote whatever the plan does.
Condition 5 is the one this study can move: B-129r's P plan was −0.18R; B-132's AB=CD
arm went to +0.04R on the wide stop and AB=CD is ~90% of P's signals, so 5 may well pass.

### Results — B-132r

*(appended after the run — the pre-registration above is not edited)*

**Run 2026-10-14** — `tools/harmonic_tier_recheck.py`, result `tools/cache/harmonic_tier_recheck.json`.

**R0: PASS** — n = 109 (B-129: 116; B-129r on 2026-10-05: 115), pooled @20d +1.10% (B-129:
+1.07%). Inside tolerance, but n moved by 6 in nine days: the data under the panel has
shifted a little since B-129r.

**Arm P — rule result: PROMOTE (all five conditions pass). Recommendation only.**

| Condition | B-129r (2026-10-05) | B-132r (today) | |
|---|---|---|---|
| 1 floors | 2,389 signals / 286 symbols | 2,349 / 281 | pass |
| 2 @20d pooled, windows | +0.55%; +0.27 / **−0.03** / +1.22 | +0.55%; +0.33 / **+0.15** / +1.06 | **fail → pass** |
| 3 10d or 60d 3/3 | 10d +0.14 / +0.67 / +0.65 | 10d +0.03 / +0.88 / +0.52 (60d +1.57 / −0.89 / +0.13) | pass |
| 4 clustered @20d | +0.82, p 0.019 | +0.76, p **0.025** (156 of 281 symbols positive) | pass |
| 5 plan avg_R (market fill) | **−0.18R**, 64% stopped | **+0.04R**, 23% stopped | **fail → pass** |

Descriptive plan (outside the rule): +0.55% of entry a trade, 2,286 trades; 36% target /
23% stop / 41% time exits; 9 plans filled through the stop, 0 unfilled.

**My prior was wrong, and why matters.** I predicted STAYS WEAK because condition 2 reads the
signal and the stop cannot move a signal. Condition 2 flipped anyway — **not because of the
stop**, but because the window edges moved: nine days of new bars shift where the three
walk-forward windows fall, and the middle window went from −0.03% to +0.15%. So of the two
conditions that flipped:
- **Condition 5 flipped because of B-132** — the thing this study set out to test. The stop
  was chosen on names 301–500; this is the first 300, so for the stop it is out of sample.
- **Condition 2 flipped through calendar drift**, with a thin margin (+0.15%). B-129r's
  middle window was −0.03% on the same scanner nine days ago. This pass is fragile.

**Read with care.**
- Margins are thin at three places: window 2 @20d +0.15%, clustered p 0.025 (bar 0.05),
  plan +0.04R. The 60d middle window is −0.89%; condition 3 passes on 10d only, as before.
- The signal set did not change (R:R gate still on the original stop); signals fell
  2,389 → 2,349 only through the data moving.
- 41% of plans now exit on the 10-bar time stop (B-132 saw 43%). Not changed here.

**Recommendation for the owner:** by the pre-registered rule, **PROMOTE** Harmonic
Reversal (XABCD) from the weak tier (0.25) to `MEASURED_EDGE_SCANNERS` (1.0). The plan
defect that blocked it is fixed and out of sample, but the window-2 pass came from the
calendar moving, not from B-132, and is thin. A cautious alternative is to hold one more
re-run on a later data date before acting. `opportunity_hub.py` is **not** changed by
this study.
