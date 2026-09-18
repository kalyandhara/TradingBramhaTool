---
title: "Flag & Pole — Test Design (pre-registered)"
category: analysis
tags: [flag-and-pole, pre-registration, continuation, measured-move, backtest, b-92]
timeframe: swing
created: 2026-09-17
updated: 2026-09-17
sources: 0
related:
  - analyses/Open-Backlog.md
  - analyses/Pattern-Reporting-Enhancement-Roadmap.md
  - analyses/SVP-Structure-Signal-Pre-Registration.md
  - sources/Spider-Software-Flag-Pole-Infographic.md
---

# Flag & Pole — Test Design (pre-registered)

**Written before any forward return has been looked at.** B-92 built
`flag_pole.py` on 2026-09-17 explicitly *to be measurable* — that was the whole
justification, since `High Tight Flag` was one of three scanners B-19 could not
score for too few signals. This is the measurement it was built for.

## The prior is skeptical, and it is on the record

**B-19 measured 0 of 41 scanners stable after costs.** A 47th pattern is not
expected to break that, and the build was justified on coverage, never on
expected edge.

Worse for this specific pattern: **its degenerate form has already been measured
NEGATIVE here.** Loosen a flag's gates far enough and it becomes "any pullback in
an uptrend", which ships as `Pullback Entry` and scored **−0.43% / −1.12%**. The
gates are what separate this from that, and whether they separate it *enough* is
exactly what is unknown.

**The honest prior is that this fails.** Saying so now is what stops a marginal
result from being read as a success.

## What is being tested — the BREAKOUT, not the pattern

`detect_flag_pole` returns a pattern whenever one exists, broken or not. An
unbroken flag is a **WATCH**, and nobody trades a watch. The shared
`backtest_scanner` would count every watch bar as a signal and measure something
no one acts on.

So the event is the **transition**: the first bar on which `broken` becomes true
for a symbol+direction, having been false on the previous evaluated bar. Counted
2026-09-17 before any scoring: patterns are present on ~5.1% of bars (bull) but
**broken out on 0.45%**, so this is the selective half.

**Entry at the NEXT bar's open**, the desk's convention — a break confirmed at
today's close cannot be bought at today's close.

## Three separable claims, and they can fail independently

### A. Edge — does the breakout beat doing nothing?

Mean forward return from entry, minus the every-bar baseline over the same
symbols and window, with `COST_INDIAN` on both arms. **Primary horizon h = 20
sessions**, reported at 5 / 10 / 20 / 60.

### B. The measured move — is the pole-height target reachable?

The card's target is the pole height projected from the breakout, and the stop is
the far flag boundary. So walk each trade forward: **which is hit first, target or
stop?** This is the claim the card actually makes, and it is separable from A — a
setup can have positive edge while its stated target is fantasy, and vice versa.

Reported as target-hit %, stop-hit %, timeout %, and realised R.

### C. Does volume contraction matter?

**This is the question B-92 deliberately deferred rather than assumed.** `High
Tight Flag` rejects a rising-volume flag outright, on the sound reasoning that a
flag on rising volume is distribution into strength. B-92 **measured it instead of
gating on it**, and wrote: *"a later test can ask whether it matters instead of
assuming it."* This is that test.

Split the signals on `vol_contract > 0` (volume dried up) versus `<= 0` (it rose)
and compare edge at h=20. **Non-decisive for A**: it cannot rescue a failed
primary, and a split that looks good on a failed overall result is subgroup
mining. It decides only whether a future version should gate on volume.

## The bear half is scored differently, and that is not a detail

`backtest._simulate_plan` is **long-only** — it refuses a plan whose stop sits
above entry. So the inverted flag cannot go through it unmodified.

Bear signals are scored as **plain long forward returns, where a NEGATIVE number
means the pattern had teeth**, exactly as `evwma_vwap_macd_backtest` scores its
crossunders. Its plan is walked with the mirror rule (stop above, target below).

**And the bear half is an EXIT/AVOID signal here, not an entry** — shorting NSE
cash for a swing hold is unavailable to most users of this repo. A positive result
on the bear side means "do not be long", not "go short".

## Floor

**200 signals per direction.** Below it, that direction is reported
**INCONCLUSIVE — UNDERPOWERED**, not as a null. The B-58 precedent: 53 QM events
against a floor of 200 was not evidence of absence, and reporting it as one would
have been the error. This is the same floor B-8 was labelled provisional against.

## Decision rule — written now, so it cannot be chosen later

| Outcome at h=20 | Verdict | Consequence |
|---|---|---|
| edge **> 0**, p **< 0.05**, floor met | **PASS** | measured positive. Still **no confluence vote** — one test buys visibility, not authority. The card's UNMEASURED line is replaced by the number |
| edge ≤ 0 or p ≥ 0.05, floor met | **NULL** | stays a bystander. **The card must say it was measured and failed** — the null goes on the surface, not in the drawer |
| floor unmet | **INCONCLUSIVE** | recorded as underpowered. **Not** a null, and not a licence to widen the gates until it passes |
| edge **< 0**, p **< 0.05** | **INVERTED** | do **not** ship the mirror. A significant inversion on a skeptical prior is a reason to re-read the construction |

**Claim B is reported whatever A says.** If the target is unreachable that is worth
knowing even on a null — it would mean the card's plan geometry is wrong
independently of whether the entry is.

**Nothing is deleted on a null.** The detector stays, the chart keeps drawing it,
and the levels stay — a plan that loses money is still a plan, and the alternative
is the 31 scanners that cannot be scored at all.

**The gates will not be tuned to rescue a failure.** Any change to
`POLE_MIN_ATR`, `FLAG_MAX_RETRACE` or the monotonicity floor after seeing this
result is a new hypothesis needing its own pre-registration and its own window.

## Data

`nse_universe` nifty500, daily bars, walked point-in-time — each evaluation sees
`df.iloc[:t+1]` only. Universe size and window are recorded with the result.

## RESULT

*(empty on purpose until the run)*

## Related Pages

- [[analyses/Open-Backlog]] — B-92 and the B-19 prior
- [[analyses/Pattern-Reporting-Enhancement-Roadmap]] — PR-3, which built it
- [[analyses/SVP-Structure-Signal-Pre-Registration]] — the same shape of test
- [[sources/Spider-Software-Flag-Pole-Infographic]] — the card being tested
