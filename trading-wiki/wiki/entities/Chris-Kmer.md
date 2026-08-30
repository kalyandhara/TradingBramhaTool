---
title: "Chris Kmer"
category: entity
entity_type: person
role: Intraday futures trader (MNQ); claimed Robbins World Cup micro day-trading monthly champion, July
bias: n/a
tags: [person, day-trader, futures, order-flow, prop-trading, world-cup]
created: 2026-08-29
updated: 2026-08-29
sources: 1
related: [strategies/Forced-Participation-Reversal, concepts/Gamma-Exposure-GEX, concepts/Order-Flow, concepts/Prop-Trading-Funded-Model, concepts/Trading-Psychology-Champion, sources/YT-Chris-Kmer-World-Cup-Order-Flow]
---

# Chris Kmer

US (West Coast) intraday futures trader, 26 at time of interview. Trades **MNQ** in the
first ~90 minutes after the New York open, 0–2 trades a day, through prop-firm evaluation
and funded accounts as well as a personal account. Claims the **July monthly micro
day-trading division of the Robbins World Cup with a 100% return**.

Self-described arc: quit a job to travel, learned trading from social media, lost his
savings and went into debt, then rebuilt by sizing down to a single micro contract and
scoring himself on execution rather than P&L.

## Known Views

- **Setups are the last 5–10%.** The work is understanding *who else is in the auction,
  what they are forced to do, and where.* His organising idea is **forced participation** —
  see [[strategies/Forced-Participation-Reversal]].
- **Absorption ≠ reversal.** Absorption happens constantly; only the subsequent
  **dominance shift** is tradeable, and he requires a *second* failed attempt before
  entering. Recorded in [[concepts/Order-Flow]].
- **GEX is a volatility read, not a direction read** — positive gamma dampens (and kills
  breakouts), negative gamma amplifies. See [[concepts/Gamma-Exposure-GEX]].
- **Order flow should reduce your trade count, not raise it.** He uses it primarily as a
  filter; "the most informed decision is usually not to participate."
- **Back-end optimisation over front-end.** Consistency comes from eliminating
  *unnecessary* losses, not from finding more A+ setups — you don't control how many of
  those the market offers. See [[concepts/Trading-Psychology-Champion]].
- **A rule without an action isn't a rule.** "Don't overtrade" is not a rule; "stop after
  two consecutive losses" and "hard shut-off 90 minutes after the open" are — and both
  came from logging where his own decision quality broke down.
- **Prop-firm sizing is a different game.** Argues small drawdown buffers force larger
  per-trade risk. His stated reasoning for why 1.5R suffices in evaluations contains a
  per-trade/per-account unit error — see the source page.

## Caveats

Interview ran on a prop firm's channel with a mid-roll sponsor read; the "anyone can do
this" framing is channel copy the process does not support (it needs a footprint platform,
live order-flow data, and discretionary reads he calls "not so cookie cutter"). The
championship is **one month** of a percentage-ranked contest, and the implied position
sizing (~4–8% risk per trade) is 8–16× this vault's documented default.

## Sources

- [[sources/YT-Chris-Kmer-World-Cup-Order-Flow]] (2026-08-29) — whiteboard walkthrough of
  the full process plus the behavioural material.
