---
title: "YT — Gamma Exposure (GEX) primer: dealer hedging, the gamma flip, and strategy by regime"
category: source
type: source
source_type: youtube-summary
author: unattributed
fetched: 2026-09-05
raw: pasted summary (no transcript retained)
tags: [gex, gamma, options, dealer-positioning, volatility-regime, market-maker, call-wall, put-wall, gamma-flip, premium-selling, iron-condor, us-equities]
related: [concepts/Gamma-Exposure-GEX, sources/YT-Chris-Kmer-World-Cup-Order-Flow, analyses/Open-Backlog]
created: 2026-09-05
updated: 2026-09-05
sources: 0
---

# YT — Gamma Exposure (GEX) primer: dealer hedging, the gamma flip, and strategy by regime

A second, independent explanation of the same mechanism already documented in
[[concepts/Gamma-Exposure-GEX]]. Ingested as **corroboration plus one new claim**, not as
new ground: this repo has already built the engine and measured the regime claim to a
null (B-44).

## What it says

**Mechanism.** Gamma measures how fast an option's delta changes as spot moves. Aggregate
gamma across open contracts (GEX) determines which way market makers — who want to stay
market-neutral — must trade the underlying to stay hedged.

| dealer gamma | hedging behaviour | market result |
|---|---|---|
| **Positive** — "shock absorber" | trade *against* the move: sell rallies, buy dips | vol damped, range-bound, rallies struggle, dips find support |
| **Negative** — "accelerator" | trade *with* the move: buy rallies, sell dips | vol amplified, sharp rallies, steep crashes, breakouts follow through |

**Landmarks.** *Gamma flip* — the price where the market crosses from positive to negative
gamma, and a calm tape can turn volatile. *Call wall* — heavy call OI with positive gamma,
acts as a ceiling. *Put wall* — heavy put OI, acts as a floor.

**Stated limitations.** Explicitly not a crystal ball. Pair with price action at the flip
and wall levels, historical support/resistance, the IV-implied expected move, and remember
earnings/Fed/data can override gamma entirely.

## The one genuinely new claim: strategy selection by regime

Everything above restates [[concepts/Gamma-Exposure-GEX]]. What this source adds is a
prescription the existing page does not carry:

| regime | recommended | rationale given |
|---|---|---|
| **Positive gamma** (low vol) | premium **selling** — covered calls, cash-secured puts, credit spreads, iron condors | range-bound tape, theta decays faster than the underlying moves |
| **Negative gamma** (high vol) | **long** directional options — long calls/puts | large swings are what long options need to pay |

> [!contradiction] The premise this rests on was measured false on NSE indices
> Both prescriptions are downstream of one assumption: that forward realised volatility is
> **materially different** between the two gamma regimes. [[concepts/Gamma-Exposure-GEX]]
> records the test of exactly that on 480 NSE sessions — forward vol at 5/10/20d separated
> by +0.28 / +0.24 / **−0.40** pp (p_rot 0.84 / 0.83 / 0.67), the 20-day horizon carrying
> the wrong sign. If the vol difference is not there, a strategy split that exists to
> harvest it has nothing to harvest.
>
> This is not a contradiction *of the source* — it is a US-index framing, where the
> mechanism is well evidenced. It is a contradiction of transplanting it to NIFTY /
> BANKNIFTY, which is the only market this desk trades.

## Why this source is weaker than the one already on file

- **Unattributed.** No named speaker, no track record, nothing to weigh the claims against.
  [[sources/YT-Chris-Kmer-World-Cup-Order-Flow]] at least attaches a name and a stated result.
- **No market named.** The dealer-hedging literature is US index options (SPX/SPY, 0DTE).
  The source never says whether its claims are supposed to travel to other exchanges.
- **The "positive ≠ bullish" correction is absent.** The existing concept page leads with
  the most common misreading; this source never warns about it, and its "shock absorber"
  framing arguably invites it.
- **No naive-vs-inferred distinction.** The existing page draws the line between GEX from
  open interest under an assumed convention and GEX from trade-level dealer positioning.
  This source gives no indication which it means — and that distinction is the named
  suspect in B-44r.

## Verdict for this repo

**Corroborates the mechanism, changes nothing about the measured result.** The engine
already exists (`tools/gamma_exposure.py`); the regime claim was already tested and came
back null. The strategy-mapping claim is new, and testable in principle, but it is a second
derivative of a first derivative that measured zero here — so it belongs behind B-44r
(fixing the positioning convention), not in front of it.

See [[analyses/GEX-Strategy-Mapping-PoC-Probe]] for what a PoC would actually cost and what
would have to be true first.
