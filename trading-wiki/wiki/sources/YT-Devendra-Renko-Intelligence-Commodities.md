---
title: "YT — Devendra: Renko Intelligence on Candles (podcast, part 2)"
category: source
type: source
source_type: youtube-transcript
author: "Devendra (podcast guest; surname not stated in the transcript)"
fetched: 2026-08-29
recorded: 2026-08-24
raw: .raw/transcripts/YT-Devendra-Renko-Intelligence-Commodities-2026-08-29.md
tags: [renko, brick-size, atr, supertrend, commodities, noise-filtering, chart-type, unvalidated]
created: 2026-08-30
updated: 2026-08-30
sources: 0
---

# YT — Devendra: Renko Intelligence on Candles (podcast, part 2)

Second podcast appearance by "Devendra Sir" (surname never stated; host named as both
"Mamta" and "Mukta" in the same transcript). Pitch: candles trap you because they are
**time**-sampled, so on a quiet day a 30-minute chart enters late and a 15-minute chart
never forms a decisive bar. His fix is to keep candles on screen but derive the levels
and the trigger from **Renko**, with a brick size computed from ATR rather than picked
by hand. Extends into commodities (MCX gold/silver/crude/natgas), which he argues
retail has abandoned for index options.

> [!key-insight]
> The one transferable idea here is the **brick-sizing rule**: set the Renko brick to
> the *average range of one bar on your execution timeframe*, obtained by taking ATR(5)
> on a **session-length** bar and dividing by how many execution bars fit inside a
> session. Everything else in the video is either standard Renko/SuperTrend, a paid
> product, or unfalsifiable ("levels protect themselves, you do not need proof").

> [!warning] Commercial content
> The transcript sells a free webinar, a paid "AI-Renko SuperTrend" indicator, and a
> "Mahakal" course, and asks viewers to share the video with ten friends. No backtest,
> no sample size, no losing example is shown anywhere. Treat every performance claim
> as **unmeasured**.

## Core Claims

- **Candles are time-sampled; markets are not.** On a sideways day, a fixed-time bar
  either arrives late (30-min) or never develops (15-min). Renko advances only on
  price movement, so it "pauses" with the market instead of manufacturing bars.
- **Keep candles, trade Renko** ("Renko Intelligence on Candles") — because the
  TradingView Renko/1-second charts sit behind a ~₹5,000 premium subscription that most
  Indian retail traders will not buy. The workaround is to *compute* Renko structure and
  overlay its levels/signals on an ordinary candle chart.
- **Brick size from ATR, not from taste** — see the arithmetic section below.
- **Timeframe = one session.** Nifty read on a ~6-hour bar (NSE session 09:15–15:30),
  commodities on a ~14-hour bar (MCX session 09:00–23:30). Both are just "one bar =
  one trading day for that instrument".
- **AI-Renko SuperTrend** — their product: classic [[concepts/SuperTrend]] with the
  ATR-derived brick size auto-computed per timeframe. Claimed to "remove the lag".
- **Options application** — mark levels on the session bar, buy the ATM strike in the
  direction of the Renko trend (example given: spot 24250 → buy the 24300 strike).
- **Commodities are where price actually moves** — historically the trading market
  (sugar, wheat, rice with their own seasonality); equities were for investment. Retail
  has forgotten commodities since index F&O took over.
- **Risk** — 10% of capital per trade, stop sized from the brick, target 1:2 or 1:3.
- **Reference lead** — credits **Prashant Shah** (real author on Renko / Point-and-Figure
  for Indian markets) as one of the few published Renko practitioners. Worth ingesting
  on its own; the transcript garbles it as "two people named Prashant Shah".

## The brick-size arithmetic — reconstructed and corrected

The transcript states the rule twice and both times the printed numbers are wrong, but
the *rule* underneath is coherent. Reconstructed:

```
brick = ATR(5) on a session-length bar / (execution bars per session)
      = the average range of ONE execution-timeframe bar
```

| instrument | session bar | ATR(5) claimed | execution TF | bars/session | brick (rule) | transcript says |
|---|---|---|---|---|---|---|
| Nifty | 6 h | 100 pts | 30-min | 12 | **8.33** | "≈53" ❌ |
| Gold | 14 h | 1500 pts | 30-min | 28 | **53.6** | "≈53" ✅ (but says ÷30) |

- The Nifty "53" is **contamination from the gold example** — by his own division
  (`100 / 6 / 2`) the answer is 8.33, which is what he writes in Chapter 7, except there
  he labels 8.33 a *1-minute* brick. The 30-min and 1-min labels are swapped somewhere.
- The gold figure is right if you use **28** half-hour blocks in a 14-hour session; the
  stated "30 blocks" gives 50, not 53.
- **"Breaking above 268.2"** (Chapter 5) is an unusable fragment — almost certainly the
  tail of a Nifty level such as 24268.2. Do not carry this number anywhere.

Net: the *method* survives the arithmetic errors, the *numbers* do not. Any
implementation must recompute both from live ATR, never hardcode 53 or 8.33.

## Contradictions with existing wiki

- **"The market is a zero-sum game."** True for futures and options; **false for
  equities**, and this vault has the measurement to say so — the every-bar baseline in
  [[concepts/EVWMA-VWAP-MACD]] is **+0.31 / +0.72 / +1.54 / +5.05%** at 5/10/20/60 days
  across 23 NSE names over ~19 years. Positive drift is exactly what a zero-sum market
  cannot have. The claim matters because it is used to justify hyperactive trading.
- **"10% of capital per trade."** [[concepts/Capital-Management-Methods]] runs a default
  of **0.5% risk per trade** with a **20% max allocation** cap. If Devendra means
  *allocation*, 10% is inside the vault's cap and unremarkable; if he means *risk*, it is
  20× the vault default. The transcript never distinguishes the two — treat as unusable
  guidance rather than as a competing standard.
- **"Removes the lag."** Renko does not remove lag, it *redefines* it: no brick prints
  until price has travelled a full brick, so brick size **is** the lag, and the in-progress
  brick is provisional. The honest claim is that Renko converts *time* lag into *price*
  lag, which is a better-behaved quantity — not that lag disappears. A 1-second chart
  does not change this.

## Actionable insights

1. **ATR-derived brick sizing is testable and buildable** — one function, no product
   needed. Filed as a backlog item (see below) and written up in [[concepts/Renko-Charts]].
2. **Renko-on-candles is the same pattern this repo already uses** — compute in a pure
   module, render markers on the candle series. Exactly how `evmacd`, `prte` and `stai`
   are wired in the chart tool; no new architecture required.
3. **Commodity coverage is a real gap** — the chart tool and every scanner in `tools/`
   are equity/index only. Whether MCX is worth adding is a scope decision for the owner,
   not a foregone conclusion.
4. **Ingest Prashant Shah** on Renko/P&F for Indian markets — a published, checkable
   source for the same material, without the webinar funnel.

## Pages updated

- Created [[concepts/Renko-Charts]] — the chart type, brick sizing, and what is
  actually testable about it.
- [[concepts/Point-and-Figure-Charts]] — cross-linked to Renko as its sibling
  time-independent chart type.
- [[analyses/Open-Backlog]] — **B-43** (ATR-brick Renko engine + measured test).
