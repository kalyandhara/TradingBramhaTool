---
title: "Flag & Pole — Test Design (pre-registered) — BULL MARGINAL PASS, BEAR INVERTED"
category: analysis
tags: [flag-and-pole, pre-registration, continuation, measured-move, backtest, b-92, measured-inverted, marginal-pass]
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

> [!warning] Superseded by this page's own result — added 2026-09-17 after the run
> The exit/avoid framing assumed the bear half would at worst be uninformative.
> **It came back INVERTED**: breakdowns were followed by strength (+1.33%,
> p=0.0005). So it is not an exit signal either — acting on it would have meant
> selling into recoveries. The framing above is kept as written, because a
> pre-registration edited after its result is worthless, and corrected here.

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

## RESULT — measured 2026-09-17: **bull MARGINAL PASS, bear INVERTED**

`flag_pole_edge.py`, **248 nifty500 names**, daily bars walked point-in-time at
stride 1, 58,718 baseline observations. **1,189 bull and 979 bear breakouts** —
both directions clear the 200 floor comfortably, so neither is underpowered.

### A — edge

| | h | n | signal % | baseline % | **edge** | hit % | p |
|---|---|---|---|---|---|---|---|
| **BULL** | 5 | 1,189 | 0.25 | 0.22 | +0.03 | 47.0 | 0.886 |
| | 10 | 1,189 | 0.79 | 0.74 | +0.05 | 51.6 | 0.859 |
| | **20** | **1,189** | **2.50** | **1.79** | **+0.71** | **54.6** | **0.0499** |
| | 60 | 1,189 | 8.11 | 6.09 | +2.03 | 60.6 | 0.003 |
| **BEAR** | 5 | 979 | 0.50 | 0.22 | +0.28 | 51.3 | 0.163 |
| | 10 | 979 | 1.66 | 0.74 | +0.91 | 56.3 | 0.0009 |
| | **20** | **979** | **3.12** | **1.79** | **+1.33** | **59.0** | **0.0005** |
| | 60 | 979 | 7.34 | 6.09 | +1.25 | 61.9 | 0.072 |

**BULL = PASS, and it is marginal in the most literal sense: p = 0.0499 against a
pre-registered threshold of 0.05.** The rule was fixed in advance and the number
clears it, so the verdict is PASS — but a result sitting on the fourth decimal of
its own threshold should be read as "not distinguishable from nothing by much",
and a slightly different universe or window would flip it.

**BEAR = INVERTED, and this one is not marginal.** Bear-flag breakdowns were
followed by the stock rising **+1.33% MORE than baseline** at 20 sessions,
p = 0.0005. The pre-registered consequence applies: **the mirror was not shipped.**

### B — the measured move, and it is the part that held up

| | target hit | stop hit | timeout | avg R | median bars |
|---|---|---|---|---|---|
| **BULL** | **36.8%** | 51.6% | 11.6% | **+0.36R** | 16 |
| **BEAR** | 8.6% | **77.8%** | 13.6% | **−0.44R** | 14 |

> [!key-insight] The bull plan loses more often than it wins and still pays
> 36.8% of bull trades reach a target two to three times the risk, against a
> 51.6% stop rate — so expectancy is **+0.36R** despite a losing hit rate.
>
> **That is what a measured move is supposed to do**, and it is the strongest
> thing in this result. The card's plan geometry — stop at the far flag boundary,
> target at the projected pole — is better supported than the entry it is
> attached to.
>
> On the bear side the same geometry collapses: the target is reached **1 time in
> 12** while the stop fires on more than three trades in four.

### C — volume, the question B-92 deferred rather than assumed

When PR-3 chose to **measure** `vol_contract` instead of gating on it, it wrote
that "a later test can ask whether it matters instead of assuming it". Asked:

| | n | mean @20d |
|---|---|---|
| flag volume **dried up** | 1,063 | 2.38% |
| flag volume **ROSE** | 126 | **3.52%** |

`High Tight Flag` rejects a rising-volume flag outright, on the reasoning that it
is distribution into strength. **On this evidence that gate would have removed the
better-performing subgroup.**

**Stated carefully, because it was pre-registered as non-decisive:** 126 against
1,063 is a small and unbalanced subgroup, and this cannot rescue or strengthen
claim A. The honest reading is **"no support for adding a volume gate"**, not
"rising volume is better". Measuring the field rather than gating on it was the
right call, and the gate stays off.

### The confound this test does NOT resolve

**The detector fires only after a ≥4×ATR thrust**, so its population is momentum
names by construction. The every-bar baseline controls for the market's drift over
the same bars; it does **not** control for being in a strong name.

The shape of the bull result is exactly what a trend confound would produce:
**nothing at 5 and 10 days (p ≈ 0.86), then +2.03% at 60 days.** A breakout whose
effect only appears after three months is not behaving like a breakout.

**A momentum-matched control was not pre-registered here and has not been run.**
Until it does, the honest statement is that the bull edge is **not distinguishable
from simply being in strong names**. That control is the next test, and it needs
its own pre-registration.

### Consequences applied, exactly as pre-registered

* **Bull:** the card's UNMEASURED line is replaced by the numbers. **No confluence
  vote** — one test buys visibility, not authority, and this one is marginal.
* **Bear:** the inversion is on the surface. The registry entry now reads
  *"MEASURED and INVERTED — do not trade it in either direction"*, and the card
  calls it **STRUCTURE only**: it marks a down thrust that paused, which is worth
  seeing, but on this evidence it is **neither a short nor an exit signal**. Its
  earlier exit/avoid framing is retired — a breakdown followed by strength is not
  a reason to get out.
* **Nothing deleted.** Both detectors stay, the chart keeps drawing them, the
  levels stay.
* **The gates were not tuned.** No parameter moved after seeing this.

### Where this sits

B-19 found **0 of 41 scanners stable after costs**. This does not overturn that:
one marginal pass at a single horizon, with an unresolved confound, on a detector
whose degenerate form (`Pullback Entry`) measured negative. What it adds is a
**plan that pays** — the first thing on this desk to show positive expectancy
from its own stated geometry rather than from its entry.

## Related Pages

- [[analyses/Open-Backlog]] — B-92 and the B-19 prior
- [[analyses/Pattern-Reporting-Enhancement-Roadmap]] — PR-3, which built it
- [[analyses/SVP-Structure-Signal-Pre-Registration]] — the same shape of test
- [[sources/Spider-Software-Flag-Pole-Infographic]] — the card being tested
