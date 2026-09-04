---
title: "YT — Murshid Ali: 3-6-9 'Time-Machine' Market-Timing Indicator"
category: source
tags: [market-timing, time-cycles, 3-6-9, tesla, intraday, numerology, promotional, unbacktested, event-study]
created: 2026-08-23
updated: 2026-08-23
sources: 1
related:
  - "[[concepts/Sarvatobhadra-Chakra]]"
  - "[[concepts/Mercury-Retrograde-Market-Cycle]]"
  - "[[analyses/Backtest-Harness]]"
  - "[[analyses/SVP-Signal-Backtest-Design]]"
  - "[[sources/Sarvatobhadra-Chakra-Market-Prediction-2026-08-15]]"
---

# YT — Murshid Ali: 3-6-9 "Time-Machine" Market-Timing Indicator

## Metadata

- **Presenter / guest**: Murshid Ali (self-described 17 yrs trading experience; ex-VFX artist)
- **Format**: Host + guest interview (Hindi/English), promotional for a paid indicator
- **Products named**: the 3-6-9 timing indicator, "Rocket Momentum Indicator", "Level-Finder" tool, a "Podcast" strategy; a broker-API auto-trade beta "later this year"
- **Instruments discussed**: Nifty, Bank Nifty, Sensex, BTC
- **Claim type**: intraday *time-of-day* signal — "when the market opens it tells you exactly when a trade will appear, with entry/SL/target"
- **Date ingested**: 2026-08-23

---

## The one falsifiable claim (everything else is decoration)

Strip the Tesla framing and the strategy reduces to a **fixed intraday clock schedule**:

> At ~2 pre-computed times per session (the demo showed **11:30** and **14:15 IST**),
> a "decisive candle" forms. Trade the **break of that candle** (long if it breaks up,
> short if down), stop **just beyond the candle's opposite extreme**, target **1:3 to
> 1:5 R**, optional trailing stop. The schedule resets each session and shifts per
> market open time (e.g. BTC 05:30 IST).

That is a clean, testable, numerology-free hypothesis (see **Actionable** below). The
"3, 6 and 9 control the universe" wrapper adds **nothing verifiable** to it.

## Detailed notes

- **Tesla 3-6-9 premise.** Numbers 3/6/9 are claimed as a "universal energy" governing
  natural and market cycles; the times when decisive candles form are said to derive
  from a daily 3-6-9 "time cycle" that the software auto-resets.
- **The "proof" offered is a digit-sum trick.** 360° → 3+6+0 = 9; 3600 s/hr → 9;
  86400 s/day → 8+6+4+0 = 18 → 9; etc. This is simply the **divisibility-by-9 rule**:
  *every* multiple of 9 digit-sums to 9, and 360/3600/86400 are multiples of 9 only
  because our angle and time units are base-60/base-360 human conventions — it says
  nothing about price. Not evidence; framing.
- **Manifestation aside.** "Write your goals 3× in the morning, 6× at night, 9× total
  and the universe aligns." Recorded as stated; not a market mechanism.
- **Confluence positioning.** Presented as *orthogonal* to price/volume tools — it tells
  you *when* to look, then you confirm *direction* with RSI/EMA/Fibonacci. So the time
  cue is a **filter/trigger**, not a directional edge on its own (guest's own words).
- **Performance claims (as given, uncorroborated):** ~587 trades over 12 months;
  Nifty ≈ 30% return on capital, avg ~1:3 win/loss; Bank Nifty similar, higher vol;
  Sensex net ≈ ₹1,40,000 over three months with ~₹9,000 monthly drawdowns; "≈32%
  annualized **gross, before brokerage, taxes and slippage**"; personal win rate "rose
  to ~70%".
- **Stated drawbacks (his own):** misses moves outside the fixed windows; requires you
  to be at the screen at the magic times (set alarms); not 100% accurate.
- **Roadmap:** 5,000-stock scaling is compute-bound → a beta watchlist scanner; quarterly
  releases + auto-update; broker-API full automation in sandbox.

## Actionable — how THIS repo would test it

The falsifiable claim is a textbook **event study**, identical in shape to the one already
built for astro timing in [[analyses/Backtest-Harness]] and `tools/sbc_vedha_backtest.py`:

> **H:** intraday candles at the fixed clock times (~11:30 and ~14:15 IST, or whatever
> pre-committed 3-6-9-derived schedule) are "decisive" — they mark the session's
> directional extreme or a reversal pivot — **more often than candles at randomly chosen
> intraday times.**

Design, pre-registered before looking:
1. **Signal:** the fixed time-of-day slots (locked in advance, NOT chosen after seeing
   which worked — the whole failure mode of this genre).
2. **Label (objective):** a candle is "decisive" if e.g. its range > k·ATR **and** its
   break sets the session high/low that survives to close; plus a reversal-pivot variant.
3. **Base rate:** P(a random intraday slot is decisive) — the honest benchmark.
4. **Null:** circular-rotation / random-slot permutation → empirical p (same machinery as
   `sbc_vedha_backtest.study`).
5. **Costs:** net of brokerage + slippage — decisive at 2 trades/day (gross ≠ net).

**Blocker (known, repo-wide):** nothing here persists intraday bars — flagged already on
[[sources/4H-Wick-Zone-FVG-Infographic]] and the SBC pages. yfinance 5m/1h gives a few
months of history, enough for a first pass. Until such a study runs, the time schedule is
an **unmeasured prior**, exactly like the SVP confluence weights in
[[analyses/SVP-Signal-Backtest-Design]].

**Steelman worth keeping:** intraday *time-of-day effects are real* (opening/closing
volatility, the ~11:30–13:00 lunch lull). A **pre-committed time to check for a range
breakout**, with a candle-extreme stop and fixed R:R, is a legitimate structuring
discipline *regardless of the 3-6-9 story*. That structuring — not the numerology — is the
only transferable part.

## Contradictions / red flags logged

- **Returns quoted "before brokerage, taxes and slippage"** for a 2-trade/day intraday
  system — the costs are precisely what decide intraday viability; gross is not a result.
- **Figures don't reconcile:** "30%/yr Nifty", "₹1,40,000 over 3 months Sensex", "32%
  annualized gross", "587 trades/yr", "70% win rate at 1:3 R" — mixed periods/units, and
  70% at 1:3 would be an extraordinary, implausible expectancy if real; none audited,
  no per-trade log shown.
- **The headline cycle example refutes itself:** "corrections in 2008, 2018, 2026" — gaps
  of **10 and 8 years**, not 9; the cycle doesn't fit its own showcase.
- **Times are asserted, never derived:** the transcript never shows how 3-6-9 yields
  11:30 / 14:15. (Post-hoc, 9:15→11:30 = 135 min → 1+3+5 = 9; that a retrofit exists for
  any chosen time is the point — unfalsifiable unless the schedule is fixed in advance.)
- **Commercial incentive:** a paid indicator + upcoming "AI auto-trade" beta; the wiki's
  measurement-first ethos gives promotional win-rate claims **zero weight** (same call as
  the [2026-08-20] log entry).
- **Parallel to [[sources/Sarvatobhadra-Chakra-Market-Prediction-2026-08-15]]:** another
  "fixed intraday window → decisive/reversal candle" timing claim. That family, when
  actually tested here (daily-vedha NIFTY event study), came back a **clean negative — no
  edge** (see [[concepts/Sarvatobhadra-Chakra]] / the SBC backtest). Prior here is therefore
  "expect ~1.0× lift" until a 5m study says otherwise.

## Pages updated

- Created this source page. Added to [[index]] and [[log]].
- **No concept page created** — the 3-6-9 numerology does not warrant one; the testable
  core (intraday time-of-day breakout windows) lives here and links to the existing
  timing/backtest pages. Promote to a concept only if a 5m event study shows non-null lift.
