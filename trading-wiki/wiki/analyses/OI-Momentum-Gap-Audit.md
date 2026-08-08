---
title: "OI Momentum — what we are missing, audited against an independent source"
category: analysis
tags: [oi, open-interest, volume, futures, audit, gap-analysis, index]
timeframe: milestone-plan
created: 2026-08-07
updated: 2026-08-07
sources: 1
related:
  - sources/Fingrad-OI-Analysis-Infographic.md
  - concepts/Put-Call-Ratio.md
  - analyses/PCR-in-OI-Momentum.md
  - analyses/Backtest-Harness.md
---

# Analysis: OI Momentum gap audit — 2026-08-07

## Thesis

[[sources/Fingrad-OI-Analysis-Infographic]] reproduces our four-quadrant OI
framework **exactly**, which is mild corroboration and no news. Its value is the
one axis it treats as first-class and we do not: **volume**.

Audited against the running code, there is **one real hole, two scope gaps, and
two places where we are already ahead of the source.**

## Gap 1 — Volume is collected and then dropped ⚠️ the real one

The sheet's rule is explicit: *High Volume + OI increase = **Strong Signal**;
Low Volume + OI increase = **Weak Confirmation**.*

`build_oi_table()` aggregates `volume=("TtlTradgVol", "sum")` at
[nse_oi_momentum.py:161](tools/nse_oi_momentum.py:161) — and **the column is
referenced nowhere else in the module or the dashboard.** Verified by grep: one
occurrence, the definition. `summarize_symbol()` grades STRONG/MODERATE on price
magnitude and OI magnitude only; `turnover` appears solely as a *disqualifying*
floor (`MIN_TURNOVER`), never as a *confirmation* axis.

So a name can be graded **STRONG** on a large price move and a large OI build
that happened on **below-average participation** — precisely the "weak
confirmation" case the source names — and nothing in the output says so.

**Why it was not trivial to add, and the fix:** "high volume" is *relative*, and
the bhavcopy is a single session. There is no baseline in the file. Two routes,
and the same cross-sectional-vs-time-series split that shaped
[[concepts/Put-Call-Ratio]]:

- *Cross-sectional* — today's volume against the day's F&O universe. One file,
  no history, but it answers "busy vs other stocks", not "busy vs its own norm".
- *Time-series* — today's volume against the symbol's own recent median. Needs
  several bhavcopies; `fetch_fo_bhavcopy` already walks back up to 7 days
  looking for one, so fetching five is a small extension (~6 MB, cached hourly).

**Time-series is the right one** — the source's rule is about a stock trading
more than *it usually does*, not more than its neighbours.

### Measured, 2026-08-06 against a 5-session baseline

Relative volume (today ÷ prior-5-session median), 208 symbols covered:

| Percentile | rvol |
|---|---|
| p5 | 0.36× |
| p25 | 0.60× |
| **p50** | **0.80×** |
| p75 | 1.45× |
| p90 | 2.39× |
| p95 | 3.59× |

Joined to the day's 57 OI readings:

| Strength | n | median rvol |
|---|---|---|
| **STRONG** | 7 | **3.98×** |
| MODERATE | 29 | 1.22× |
| UNSUPPORTED | 21 | 1.48× |

> [!key-insight] The honest version: the hole is real, but it is smaller than the source implies
> STRONG names already run at ~4× normal volume, and **zero** STRONG names on
> this session had rvol < 1. The existing price-and-OI magnitude gates are
> already selecting high-participation names *implicitly*. Adding volume would
> therefore **corroborate** the current tiers far more often than it overturns
> them — on 2026-08-06 it would not have changed a single verdict.
>
> That is still worth building, for one reason: it makes the weak-confirmation
> case **explicit and detectable** instead of merely improbable. But it should
> ship as a *reported column and a downgrade condition*, not as a new strength
> tier, and nobody should expect it to move many names. One session is not a
> distribution — re-measure before trusting the 4× figure.

## Gap 2 — Index OI is not covered at all (scope)

The module is stock futures only (`FinInstrmTp == "STF"`), and says so. But the
source's worked examples are both **NIFTY**, and index futures (`IDF`) sit in
the same file we already download — 5 underlyings, 3 expiries each:

| Index | Series OI | ΔOI | OI % |
|---|---|---|---|
| NIFTY | 13,269,620 | −475,605 | −3.46% |
| BANKNIFTY | 2,292,720 | −69,630 | −2.95% |
| MIDCPNIFTY | 1,984,800 | +480 | +0.02% |
| NIFTYNXT50 | 19,925 | +350 | +1.79% |
| FINNIFTY | 33,840 | +2,040 | +6.42% |

Same quadrant logic, zero extra fetch. **And the same
stock-vs-index separation the PCR work established applies here**: 5 index
underlyings cannot be ranked cross-sectionally, and index OI percentages are not
comparable to single-stock ones. If built, it is a **separate table with its own
floors**, never rows appended to the stock scan.

## Gap 3 — Option-chain OI (scope, partially closed)

The source defines OI over "futures **and** options" and lists Option Chain in
its always-watch-together set. Our quadrant is futures-only.

**Partially closed the same day:** [pcr.py](tools/pcr.py) now reads the STO/IDO
option chains and surfaces PCR beside the OI verdict
([[analyses/PCR-in-OI-Momentum]]). What is still absent is the *quadrant applied
to option OI* — call/put writing build-up per strike, which is a different and
larger tool (it needs strike-level treatment, not an underlying-level sum).

## Gap 4 — No support/resistance or breakout linkage (scope)

The strategy panel makes breakout/breakdown part of the confirmation:
*price up + OI up + volume up + **resistance breakout***. OI Momentum has no
level awareness at all.

We own the pieces — `scan_structural_breakout`, `scan_all_duration_breakout`,
trendlines — but nothing joins them to the OI read. This is composition, and it
is the natural next step *after* volume, not before it: a breakout tag on an
unsupported move is less informative than knowing the move had no participation.

## Where we are already ahead of the source

1. **Rollover.** The sheet reads OI at face value and never mentions that near
   expiry, OI drains from the front contract into the next. Our module sums OI
   across the whole series and carries `rollover_ratio` and a
   `days_to_expiry` downgrade precisely because the naive read manufactures
   fictitious covering signals. A teaching sheet that omits this is how the trap
   spreads.
2. **Liquidity floors and refusal to classify.** `MIN_PRICE_PCT`,
   `MIN_OI_PCT`, `MIN_TURNOVER` and the `NO_READ` state mean a small move on a
   thin contract returns *no reading* rather than a confident quadrant. The
   source has no equivalent, so every name always gets a label.

## Conclusion — recommended order

1. **Relative volume** (Gap 1). Highest value, self-contained, and it closes a
   hole where we already pay the aggregation cost. Ship as a reported `rvol`
   column plus a **downgrade** when a would-be STRONG name has rvol below ~1,
   with the measured caveat that this will rarely fire.
2. **Index OI table** (Gap 2). Cheap, and the stock/index separation pattern is
   already built and proven in `pcr.py`.
3. **Breakout linkage** (Gap 4). Composition of shipped scanners.
4. **Strike-level option OI** (Gap 3). Largest, and it needs its own design.

Nothing here should move a verdict until measured — the same rule PCR is held
to. [[analyses/Backtest-Harness]] has never tested the OI quadrant either.

## Action Taken / Plan

- ✅ Ingested [[sources/Fingrad-OI-Analysis-Infographic]]; audited the module
  against it and measured relative volume on a 5-session baseline (2026-08-07).
- ✅ **Gap 1 SHIPPED 2026-08-07** — `rvol` column + STRONG downgrade. See Outcome.
- ⏭ Gap 2 — separate index OI table.
- ⏭ Gap 4 — breakout/level linkage.
- ⏭ Gap 3 — strike-level option OI quadrant.

## Outcome

**2026-08-07 — Gap 1 shipped, and it behaves exactly as the measurement said it
would: quietly.**

`fetch_volume_baseline()` downloads the 5 settled sessions **before the scan
date** and returns a per-symbol median; `build_oi_table` and `scan` take it as an
**optional** argument, so every existing caller is unaffected and `rvol` is
simply absent without it. The dashboard caches it hourly alongside the raw
bhavcopy.

Three design rules, each of which the tests pin:

- **Volume is a veto, never a vote.** It can hold a would-be STRONG at MODERATE
  when `rvol < 1.0`; it can never promote MODERATE to STRONG. A large move on a
  large OI build that nobody turned up for is the source's "weak confirmation",
  and price/OI magnitude alone cannot see it.
- **The disqualifiers still win.** Near-expiry and thin-turnover names stay
  UNRELIABLE regardless of how heavy the volume was — verified with `rvol` 5.0
  against both.
- **An absent baseline is absent, not normal.** No baseline, an empty one, or a
  symbol missing from it all yield `rvol = None` and no downgrade. Filling it
  with 1.0 would assert normal participation on no evidence, which is the same
  fault as scoring a missing factor as zero (backlog B-1).

**The baseline must exclude the scan date**, or every symbol is partly compared
against itself and a genuine spike is diluted by its own presence in the
denominator. `before=trade_date` enforces it; verified that 2026-08-06 is absent
from its own baseline.

**Verified:** backward compatibility (no baseline → identical strengths, all
`rvol` None, zero downgrades); with a baseline, 5 sessions and **100% rvol
coverage** on 57 readings; the downgrade path — *unreachable from live data this
session* — exercised synthetically across `rvol` None/3.5/1.0/0.99/0.4, giving
STRONG / STRONG+caveat / STRONG / MODERATE+held / MODERATE+held; promotion
immunity and disqualifier ordering both confirmed; partial baseline leaves the
rest absent rather than 1.0; dashboard rendered clean in an isolated boot with
the live caveats showing ("Volume ran 2.1x…", "…7.6x…").

**As predicted, it downgraded nothing on 2026-08-06.** The seven STRONG names
ran 1.07×–13.78×. That is the honest outcome, not a disappointment: the value is
that the weak-confirmation case is now *detectable and named* rather than
silently graded STRONG. What it does add every day is the positive caveat — 17
of 57 readings carry a "volume ran Nx normal" note that previously existed
nowhere.

**Still open on this gap:** the 1.0× cut and the 5-session window came from one
session's distribution and want re-measuring; and the whole OI quadrant remains
untested by [[analyses/Backtest-Harness]], so `rvol` refines a grade that has
itself never been validated.

## Related Pages

- [[sources/Fingrad-OI-Analysis-Infographic]] — the source audited against
- [[analyses/PCR-in-OI-Momentum]] — the options-side column, shipped same day
- [[concepts/Put-Call-Ratio]] — where the cross-sectional vs time-series
  calibration distinction was first worked out
