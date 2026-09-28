---
title: "YT — Chris Kmer: World Cup championship process (order flow · GEX · volume profile)"
category: source
type: source
source_type: youtube-transcript
author: "[[entities/Chris-Kmer]]"
fetched: 2026-08-29
raw: .raw/transcripts/YT-Chris-Kmer-World-Cup-Order-Flow-2026-08-29.md
tags: [order-flow, gamma-exposure, gex, volume-profile, auction-market-theory, prop-trading, day-trading, futures, psychology, absorption]
created: 2026-08-30
updated: 2026-08-30
sources: 0
---

# YT — Chris Kmer: World Cup championship process (order flow · GEX · volume profile)

Interview with [[entities/Chris-Kmer]], 26, who claims the **July monthly micro day-trading
division of the Robbins World Cup with a 100% return**, hosted on a prop-firm channel
(IQ Capital). He walks a complete intraday MNQ futures process on a whiteboard:
**environment → location → confirmation → management**, using higher-timeframe market
structure and gamma exposure for regime, volume profile + Fibonacci for location, and
footprint/delta order flow for the trigger.

> [!key-insight]
> The load-bearing idea is not the setup — he says so himself. It is **"forced
> participation"**: trade where one side has committed size and is *failing to be
> rewarded for it*, because those participants must eventually transact against
> themselves to get out. Everything else in the process exists to locate that condition
> and confirm it happened. The entry model is explicitly "the final 5–10%".

> [!warning] Commercial framing + single-month sample
> Prop-firm channel, mid-interview sponsor read for $9 / $1 challenges. The championship
> claim is **one month** of one division of a percentage-return contest — a format that
> structurally surfaces the right tail of a high-variance distribution. Nothing here is
> evidence of edge in the sense this vault uses the word; it is a well-articulated
> *process*, and process quality and outcome are separate questions.

## The four-step process

**1. Environment (pre-open, never live).** Higher-timeframe structure on 1h/4h: is value
being built **up**, **down**, or **sideways** (higher highs/higher lows — see
[[concepts/Market-Structure-CHOCH-BOS]]). Plus the **gamma regime** — see
[[concepts/Gamma-Exposure-GEX]] — read as a *volatility* forecast, not a direction:
positive gamma → dealers sell rips / buy dips → **dampened** vol, failed breakouts;
negative gamma → dealers buy rips / sell dips → **amplified** vol. He notes call wall,
put wall and the gamma flip level, but uses the regime rather than trading the levels.
Uses "naive GEX" (broad dealer-positioning assumption) because CBOE-sourced *inferred*
GEX is S&P-only and ~$300/month.

**2. Location — where he is willing to do business.** With value building up, he refuses
to short premium or to "call the top"; he waits for a pullback into **discount**. Discount
is defined two ways that must **agree**:
- below the **value area low** of the profile ([[concepts/Volume-Profile]]), and
- inside a Fibonacci band drawn swing-low → swing-high at **0.705 / 0.786 / 0.886**.

If the fib zone sits *inside* value area, the trade is skipped. Prefers the pullback to
be into an **inefficient / low-volume node** — an area price crossed fast, where little
business was actually transacted.

**3. Confirmation — order flow, on 5-minute candles.** Two footprint views of the same
candle: one with a **volume profile** inside it, one with a **delta profile**. What he
wants at the extreme:
- Aggressive **sellers** concentrated in the lower wick (negative delta ladder, POC at
  the extreme) — effort;
- **No downward result** from that effort — absorption;
- Then a **dominance shift**: candle closes bullish, next candle pulls back, sellers try
  again and **fail higher**, buy-side imbalances light up (his tool bolds ≥ **400%**
  imbalances). He requires the **second** failed attempt before entering — one failure is
  whipsaw, two is a shift.
- Explicit correction he volunteers: **absorption ≠ reversal**. Absorption happens
  constantly; only the dominance shift after it is tradeable.

**Entry** on the flip. **Stop** just beyond the failed sellers' extreme — the level whose
breach falsifies the idea. **Invalidation** if price closes below the **0.886**: the
pullback should have completed before that.

**4. Management and targets.** First checkpoint: do buyers **reclaim the value area**? If
they stall below it while spending aggression, he moves to break-even or cuts. If they
reclaim, targets are the **POC** or a **swing high** (orders cluster at swing points and
psychological levels; book orders get pulled, but clustered ones at swings tend to fill).
Trails behind continued effort-with-result; trails early if approaching a call wall.

**Hard filter — participation.** MNQ, 5-min candles, threshold **20,000 contracts per
candle**. Below that, he does not trade at all. This plus a **90-minute** window after the
NY open is why he takes **0–2 trades a day**.

## Stated performance — and the arithmetic

| claim | value |
|---|---|
| Win rate | 60–65% |
| Typical realised R | 1.5–2R |
| Profit factor | ~1.8 |

**These three cannot all hold at once.** With a 1R stop and a 1.5R average win, profit
factor is `W × 1.5 / (1 − W)`: at 60% that is **2.25**, at 65% **2.79** — not 1.8. Solve
the other way and PF 1.8 implies either a **54.5%** win rate at 1.5R, or a realised
average win of **~1.1R** at 62.5%.

The likely reconciliation is benign and visible in his own description: he moves to
break-even and trails constantly, so **1.5R is the target, not the realised average**.
Take **PF ≈ 1.8** as the load-bearing number — it is the one computed from actual P&L
rather than from intent. That still implies a healthy **+0.3R per trade** expectancy.

**What a 100% month implies about sizing.** At +0.3R/trade and ~30 trades a month (1–2
per day), doubling needs `(1 + 0.3r)^30 = 2` → **r ≈ 7.8% of account risked per trade**;
at the more generous +0.56R it is still **~4%**. So the championship number is consistent
with risking **4–8% per trade** — 8–16× the **0.5%** default in
[[concepts/Capital-Management-Methods]]. He half-says this himself ("you have to risk
more, right? And to risk more, it's slightly dangerous"). The contest return is a
*sizing* artifact at least as much as a skill one.

## Contradictions with existing wiki

- **"Drawdown 2,000, target 3,000 — that's literally a 1.5R, so if you just constantly
  take 1.5R trades you'll be fine."** This is a unit error. **R is per-trade**; the
  3,000/2,000 ratio is **per-account**. Whether you reach +3,000 before −2,000 is a
  gambler's-ruin question governed by per-trade risk size, win rate and sequencing, not
  by the payoff ratio of individual trades. His edge probably *does* pass evaluations —
  but not for the reason given. See [[concepts/Prop-Trading-Funded-Model]].
- **Risk sizing.** 4–8% per trade (inferred above) sits far outside this vault's
  documented 0.5%-risk / 20%-allocation frame. It is a **prop-evaluation** adaptation —
  the trader's downside is capped at the evaluation fee, which changes the optimal
  aggression. It does **not** transfer to a personal account, and the transcript never
  draws that line.
- **"Anyone can go do this."** The process needs a footprint/delta platform, live
  order-flow data, and discretionary reads on absorption and dominance shift that he
  admits are "not so cookie cutter" with "edge cases". The claim is channel copy, not a
  claim the process itself supports.

## Actionable insights

1. **GEX as a volatility-regime input is the transferable piece** — and unlike the rest of
   this process, it is buildable here. See [[concepts/Gamma-Exposure-GEX]] and **B-44**.
2. **The behavioural model is the most portable content in the source**, and it is
   timeframe-agnostic: A/B/C-game sessions scored on *execution not P&L*;
   **back-end optimisation** (remove bad losses) over front-end (find more setups); the
   good-loss/bad-loss split defined by process compliance rather than outcome — a
   *winning* trade taken out-of-process is still a bad trade; rules need an **action**
   attached ("stop after 2 consecutive losses", "hard shut-off 90 min after open"), and
   must be derived from your own logged breaking point. Folded into
   [[concepts/Trading-Psychology-Champion]].
3. **Selective participation as an explicit edge** — "the most informed decision is
   usually not to participate", and a hard *volume* floor to enforce it. This is the same
   thrust as the vault's noise-reduction work (regime gate, conviction-sized shortlist).
4. **Out of scope for this repo's tooling, and that is a decision, not an oversight** —
   footprint/delta order flow needs tick-level data the repo has never carried, and the
   intraday futures lane was already recorded as out-of-scope in
   [[analyses/Open-Backlog]]. Filed as knowledge, not as a build item, except for GEX.

## Pages updated

- Created [[entities/Chris-Kmer]] and [[concepts/Gamma-Exposure-GEX]].
- Created [[strategies/Forced-Participation-Reversal]] — the process as a strategy page.
- [[concepts/Order-Flow]] — absorption ≠ reversal, the two-attempt rule, footprint
  imbalance threshold, participation floor.
- [[concepts/Trading-Psychology-Champion]] — A/B/C-game, back-end optimisation,
  good vs bad loss, rules-need-actions.
- [[concepts/Premium-Discount-Zones]] — the 0.705/0.786/0.886 variant and the
  must-be-outside-value-area constraint.
- [[analyses/Open-Backlog]] — **B-44** (daily gamma-regime read for NIFTY/BANKNIFTY).
