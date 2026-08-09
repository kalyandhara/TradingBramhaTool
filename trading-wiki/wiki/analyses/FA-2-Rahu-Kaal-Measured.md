---
title: "FA-2 measured — Rahu Kaal has no detectable effect on NIFTY, and the design has a hard identification limit"
category: analysis
tags: [FA-2, rahu-kaal, financial-astrology, measured, null-result, intraday, methodology, identification]
timeframe: intraday
created: 2026-08-09
updated: 2026-08-09
sources: 0
related:
  - concepts/Panchang.md
  - analyses/Intraday-Store.md
  - analyses/Financial-Astrology-Sector-Week-Roadmap.md
  - analyses/Backtest-Harness.md
  - concepts/Fair-Value-Gap.md
---

# Analysis: FA-2 measured — 2026-08-09

**The first astro claim in this repo to be measured rather than asserted.** Run as [fa2_rahu_kaal_study.py](tools/fa2_rahu_kaal_study.py) on `^NSEI` 1h bars from the [intraday store](tools/intraday_store.py): **723 sessions, 5,050 bars, 2023-08-28 → 2026-08-07**, of which 827 fall inside Rahu Kaal.

## Thesis

The traditional claim is that Rahu Kaal is inauspicious — avoid new positions. The roadmap's argument for testing it first was that it is the **most falsifiable claim in the repo**: an exact ~90-minute window, known in advance, requiring no detector.

Two forms were tested, because the tradition is a claim about *beginnings* and that is at least as plausibly about volatility as about drift:
- **intra-bar return** `close/open − 1` — no overnight-gap contamination
- **intra-bar range** `(high−low)/open` — volatility

## The confound that dictated the design

Rahu Kaal occupies a **fixed 1/8 day-part per weekday**: on Wednesday it is always midday, on Monday always near the open. Intraday returns have strong time-of-day structure — the opening hour's median range is **47bp** against **23bp** at midday. So comparing "bars inside Rahu Kaal" against "all other bars" mostly measures **time of day** and reports it as Rahu Kaal.

The escape is a natural experiment inside the tradition itself: because the window's position is set by weekday, **the same clock hour is inside Rahu Kaal on one weekday and outside it on another.** So the test stratifies by clock hour, contrasts inside-vs-outside *within* each stratum, and pools by inverse variance. Time of day is then held exactly fixed.

## Conclusion — nothing survives

| Metric | Test A (naive, confounded) | Test B (stratified) | Verdict |
|---|---|---|---|
| **Return** | +0.29 bp, p=0.76 | **+0.66 bp, p=0.39** | no effect |
| **Range** | +0.66 bp, p=0.45 | **+1.41 bp, p=0.021** | artifact — see below |

Four tests were run, so the Bonferroni threshold is **p<0.0125**. Nothing clears it.

**Returns: no effect, and the sign is unstable.** Across the five robustness configurations the pooled difference runs +0.66, +0.23, +0.58, −0.53, −0.56 bp with p from 0.39 to 0.83. A quantity that changes sign as you drop subsets is noise. Note the point estimate is *positive* in the headline run — returns marginally **better** inside Rahu Kaal, the opposite of the tradition, and equally meaningless.

> [!key-insight] The one apparently-significant result is a 15-minute bar pretending to be an hour
> Range came out at p=0.021 — below 0.05, above the corrected threshold. It does not survive inspection:
>
> | Configuration | Range diff | p |
> |---|---|---|
> | Full sample (the headline) | +1.41 bp | **0.0210** |
> | **Drop the 15:15 bar** | +0.59 bp | **0.5070** |
> | Drop Tuesday only | +1.93 bp | 0.0025 |
> | Drop 15:15 + Tuesday | +1.00 bp | 0.2601 |
> | Drop 15:15 + Tuesday + opening hour | +0.59 bp | 0.5336 |
>
> **NSE closes at 15:30, so the "1h" bar opening at 15:15 is a 15-minute stub** — median range **11.9 bp** against 22–47 bp for real hours. The entire volatility signal lives in it: remove that one bar and the effect collapses from p=0.021 to **p=0.51**, and stays dead in every further configuration.
>
> (Dropping Tuesday *alone* looks stronger at p=0.0025. That is not encouraging — it removes Tuesday's 17 noisy in-window sessions at 15:15 and sharpens the same stub-bar contrast. It is the artifact getting cleaner, not a finding emerging.)

## Evidence Against — a limit that more data cannot fix

> [!warning] Within a clock hour, Rahu-Kaal status *is* weekday. The design cannot separate them.
> Test B holds time of day fixed, but it does so by contrasting weekdays — and within a stratum, "inside Rahu Kaal" is determined **entirely** by which weekday it is. So **any weekday-specific effect at that hour is indistinguishable from a Rahu Kaal effect.**
>
> That is exactly what the 15:15 stratum is: its in-window weekdays are Thursday and Tuesday, so the "effect" is really *"Thursday's last 15 minutes are more volatile than Monday/Wednesday/Friday's"*. A day-of-week close effect, wearing astrological clothing.
>
> **More sessions will not fix this**, because the confound is structural rather than statistical. A genuine identification strategy exists though: **Rahu Kaal's start time drifts ~50 minutes across the year** with sunrise, while the weekday stays fixed. Contrasting early-window against late-window sessions *within the same weekday* would vary Rahu Kaal while holding weekday constant. That is a real design, and it needs finer bars than 1h to have any resolution — so it waits on 15m accumulation.

Other limits:
- **1h resolution against a ~97-minute window** is coarse: ~2 bars per session inside, and partial overlap at both edges is absorbed rather than modelled.
- **One instrument.** `^NSEI` only. A per-stock version would multiply the multiple-comparison burden without addressing the identification problem.
- **Tuesday is effectively unmeasurable** — its window is 15:11–17:41, almost entirely after the close, giving 17 usable sessions against ~143 for other weekdays (see [[analyses/Intraday-Store]]).

## The hora half of FA-2 (added 2026-08-09)

The roadmap's second pre-registered astro claim: *"do Mercury/Jupiter hora blocks show different mean returns than Saturn/Mars blocks?"* Run as [hora_study.py](tools/hora_study.py) on the same 5,050 bars.

**Hora looked more promising than Rahu Kaal, for a real reason.** Horas are *seasonal* — 12 equal divisions of a sunrise-to-sunset day — so their boundaries drift through the year. A fixed clock hour on a fixed weekday could therefore fall under different lords in summer and winter, which would allow weekday **and** time-of-day to be held fixed at once. That is precisely what Rahu Kaal could not support.

> [!warning] Measured, the hope dies: of 35 (weekday, clock-hour) cells, only 5 contain more than one hora lord — and all five are the 15:15 stub
> A ~10-minute seasonal boundary drift cannot reclassify a 60-minute bar; it only bites at the session edge, on the same 15-minute stub that manufactured the volatility artifact above. So within a clock hour the five weekdays map **one-to-one** onto five lords, making **hora lord a deterministic function of (weekday, clock hour)**. It carries no information beyond those 35 cells, so a hora effect cannot be told apart from a weekday×hour pattern. Not a sample-size problem.
>
> Note the two partitions are *not* globally identical — 7 lords against 5 weekdays, since a weekday maps to a different lord at each hour. So the right question is not "is hora significant" but **"which grouping explains more?"**

| Grouping (stub excluded, 4,328 bars) | Return F | ANOVA p | Perm p | Range F | Perm p |
|---|---|---|---|---|---|
| **Hora lord** (7 groups) | 2.002 | 0.062 | 0.042 | 0.513 | 0.784 |
| **Weekday** (5 groups) | **3.725** | **0.0050** | **0.0065** | 1.428 | 0.228 |

**Three conclusions:**

1. **Hora fails on its own terms.** 8 tests were run (2 metrics × 2 groupings × 2 samples), so Bonferroni is p<0.00625. Hora clears nothing, and on volatility it is nowhere near (p≈0.78–0.88).
2. **Weekday explains more than hora in every configuration.** Since hora is a deterministic function of weekday×hour, and plain weekday accounts for more, the astrological relabelling is doing no work. Day-of-week effects in equity returns are a long-documented phenomenon requiring no astrology — and at p=0.005–0.0065 that weekday effect is the one real signal here, sitting right at the corrected threshold.
3. **The per-lord ordering contradicts the tradition.** Mean residual return by lord runs **Mars −1.48 bp · Venus −1.38 · Moon −0.27 · Sun +0.01 · Mercury +0.25 · Jupiter +1.18 · Saturn +1.67 bp.** **Saturn — classically the most malefic hora — is the best**, and Venus, a benefic, is second worst. Insignificant, so this is not a counter-finding; but it means even the *sign pattern* offers the tradition no support.

**What would fix the identification: 15-minute bars.** At 15m a ~10-minute boundary drift *does* reclassify bars, breaking the collinearity and allowing weekday and hour to be controlled simultaneously. Another reason the store accumulates fine intervals forward.

## Action Taken / Plan

- ✅ FA-2 run and reproducible: `python tools/fa2_rahu_kaal_study.py` prints both designs, the per-stratum table, and the robustness pass. **The robustness pass is in the script deliberately** — a reader who saw only the p=0.021 headline would draw the wrong conclusion.
- ✅ **Recorded as a null.** No detectable effect of Rahu Kaal on NIFTY hourly returns or volatility.
- ⏭ **The roadmap's ordering is now vindicated and should be honoured.** FA-2 was specified to precede FA-3 (the planet→sector map) precisely so that mapping planets to named stocks would not be built on untested windows. **FA-2 found nothing, so FA-3 should not be built** — and per FA-6, if a card is ever produced, this null belongs on its face.
- ⏭ The within-weekday seasonal-drift design, once 15m depth allows it. It is the only way to separate Rahu Kaal from day-of-week.
- ✅ **Hora run 2026-08-09** — see the section above. Also null, also unidentified at 1h, and **weekday explains more than hora in every configuration**. Its per-lord ordering puts Saturn best and Venus second-worst, contradicting the tradition's own polarity.

## Outcome

**A clean null on the repo's most falsifiable astro claim, plus a methodological finding worth more than the result:** the stub-bar artifact would have been reported as a real volatility effect by any analysis that stopped at the headline p-value, and the weekday/Rahu-Kaal collinearity means even a real-looking effect could not have been attributed to Rahu Kaal.

This is the second measured claim this week to survive its headline and die on a control — after the [[concepts/Fair-Value-Gap]] "magnet" (~2pp over a matched placebo, vanishing at longer horizons). The pattern is consistent: **these claims do not fail because the data is thin; they fail because nobody had built the control.**

## Related Pages

- [[concepts/Panchang]] — computes the windows; verified to the minute against a published card
- [[analyses/Intraday-Store]] — supplied the bars, and surfaced the Tuesday/session-hours constraint first
- [[analyses/Financial-Astrology-Sector-Week-Roadmap]] — FA-2 is this; FA-3 should now not proceed
- [[concepts/Fair-Value-Gap]] — the other measured-against-a-control null this week
