---
title: "Put-Call Ratio (PCR)"
category: concept
tags: [options, sentiment, open-interest, pcr, contrarian, nse, oi]
created: 2026-08-07
updated: 2026-08-07
sources: 1
related:
  - concepts/Market-Sentiment-Index.md
  - concepts/Order-Flow.md
  - analyses/Market-Sentiment-Futures-Roadmap.md
  - sources/Fingrad-PCR-Infographic.md
---

# Put-Call Ratio (PCR)

## Definition

$$\text{PCR} = \frac{\text{Total Put OI}}{\text{Total Call OI}}$$

A volume-based variant (Put Volume ÷ Call Volume) exists and is noisier — volume
resets daily, OI accumulates a position base. **OI-based PCR is the default
everywhere in this wiki.**

It measures one thing only: how much option open interest sits on the put side
relative to the call side. It is a *positioning* measure, not a price measure.

## How to Use

The textbook reading:

| PCR | Conventional reading |
|---|---|
| > 1 | More put OI — read as bullish sentiment |
| < 1 | More call OI — read as bearish sentiment |
| ≈ 1 | Balanced / range-bound |

**PCR + price action** is the more useful pairing than PCR alone:

| Price | PCR | Reading |
|---|---|---|
| ↑ | ↑ | Bullish confirmation |
| ↓ | ↓ | Bearish confirmation |
| ↑ | ↓ | Possible false breakout |
| ↓ | ↑ | Possible short covering / reversal |

## The contradiction at the centre of PCR — and it is not a mistake

PCR is read **two opposite ways at once**, and any source that presents only one
is hiding the harder half:

- **Trend-following:** PCR > 1 means puts dominate → bullish.
- **Contrarian:** *extreme* PCR means crowding → the crowd is offside → reversal.

[[sources/Fingrad-PCR-Infographic]] states both without reconciling them: its
panel 3 says PCR > 1 is bullish, while panels 4 and 5 say above 1.30 is "very
bullish positioning (sometimes a contrarian signal)" and that extreme values can
reverse the market. Its own worked example does the same — PCR 1.18 is called
bullish strength, but 1.70 is called overcrowded and reversal-prone.

**That is not a flaw in the infographic so much as the nature of the indicator:
PCR has no fixed sign.** The same number is confirmation in one regime and a
warning in another, and nothing inside PCR tells you which regime you are in.
This is why PCR is a *context* input and a poor *decision* input — the same
conclusion [[concepts/RSI]] reaches about divergence being "a tell, not a clock".

## The threshold trap — measured, 2026-08-07

The commonly-quoted bands (**<0.70 bearish · 0.70–1.00 neutral · 1.00–1.30
bullish · >1.30 very bullish**) are **index-calibrated and wrong for single
stocks.**

Measured on the NSE F&O bhavcopy for **2026-08-06**, series-total OI:

| Instrument | PCR |
|---|---|
| NIFTY | 1.045 |
| BANKNIFTY | 1.019 |
| MIDCPNIFTY | 0.864 |
| FINNIFTY | 0.748 |
| NIFTYNXT50 | 2.014 |

**Stock options, cross-section of 208 underlyings:**

| Percentile | PCR |
|---|---|
| p5 | 0.486 |
| p25 | 0.591 |
| **p50 (median)** | **0.675** |
| p75 | 0.788 |
| p90 | 0.939 |
| p95 | 1.007 |

Applying the textbook bands to that cross-section labels **59% of the F&O
universe "bearish" and 5% "bullish" on an ordinary session**, with the *median
stock* (0.675) reading bearish. A scale on which the typical name is bearish
every day is not measuring sentiment, it is measuring its own miscalibration.

**Why the structural gap:** index puts are the standard portfolio hedge, so
index PCR is pushed up toward ~1.0 by demand that has nothing to do with a
directional view. Single-stock options carry far less of that hedging flow, so
their PCR sits structurally lower. Comparing a stock's 0.68 against a threshold
built for NIFTY compares two different things.

**Consequence:** any PCR threshold here must be **per-instrument-class and set
from the observed cross-sectional distribution** — the same rule
`nse_oi_momentum.py` already states for its own materiality floors ("set from
the observed cross-sectional distribution, not picked to look tidy"). A stock at
p90 of *stock* PCR is the meaningful statement; "above 1.30" is not.

## Level vs change

PCR *level* is heavily structural — it encodes hedging habits, listing age and
strike coverage as much as sentiment. **PCR change (slope) carries more signal
per unit of noise**, because the structural component largely differences out.
[[analyses/Market-Sentiment-Futures-Roadmap]] already specifies "PCR + PCR-slope"
for exactly this reason.

## Common Mistakes

- **Using index thresholds on single stocks** — see above; it mislabels the
  majority of the universe.
- **Reading level without regime.** PCR has no fixed sign; trend-following and
  contrarian readings of the same number are both standard.
- **Treating a rising PCR as bullish demand.** Rising put OI can be hedging
  against a long book, not a directional bet — the position says nothing about
  the holder's view on its own.
- **Mixing OI-PCR and volume-PCR** and comparing them to the same thresholds.
- **Quoting an intraday PCR against an EOD-derived band.** Our bhavcopy-derived
  PCR is end-of-day; most published PCR commentary is intraday.

## Status in this repo (2026-08-07) — ✅ SHIPPED, stock-first

[pcr.py](tools/pcr.py) is the single primitive. **Stock and index are kept
structurally separate** — different instrument-type filters, different liquidity
floors, and, crucially, **different calibration machinery**:

| | STOCK | INDEX |
|---|---|---|
| Rows/day | 208 | 5 |
| Calibration | cross-sectional percentile vs today's liquid peers | **none — needs its own history** |
| Liquidity floor | 2,000,000 total option OI (p10) | 1,000,000 |
| Band shown | yes (positional) | **no, deliberately** |

The asymmetry is forced, not stylistic: 208 same-day observations can be ranked
against each other; 5 cannot — and one of those five (NIFTYNXT50) carried a PCR
of 2.014 off **5,200 contracts** against NIFTY's 453,484,425. So `index_reading()`
returns level and one-day slope with `band=None` and a `band_reason` saying why.
An uncalibrated number is reportable; an uncalibrated number wearing a
calibrated label is not.

**Bands name a position, never a direction** — `PUT-HEAVY` / `PUT-LEANING` /
`MIDDLE` / `CALL-LEANING` / `CALL-HEAVY`, cut at the 20/40/60/80th percentiles of
the day's liquid stock cross-section. Calling a band "bullish" would bake in the
trend-following reading and hide the contrarian one; direction is the consumer's
call, made with price context.

**Live in OI Momentum** as a separate `PCR / PCR %ile / ΔPCR / Options` column
group plus a per-name line, explicitly outside the futures verdict. Join
coverage on 2026-08-06 was **52 of 57 readings (91%)**; the confirm/diverge tag
fired on 13 and stayed silent on 44, which is the intended behaviour — it speaks
only when the one-day PCR shift clears ±0.09 (≈ the outer decile).

**Still true:** unmeasured by [[analyses/Backtest-Harness]], so it annotates a
verdict and never moves one. And the floors above were set from **one session**
and should be re-measured before they are trusted as stable.

### History (superseded)

- PCR *was* a documented *planned* input to
  [[concepts/Market-Sentiment-Index]] (`sentiment_index.py` header: factor 5,
  "PCR + PCR-slope on NIFTY options, weight ~20"), gated on an option-chain
  feed. The dashboard's sentiment page says the same in its caption.
- **The feed gate is stale.** The planned blocker was NSE option-chain access,
  but the **F&O bhavcopy `nse_oi_momentum.py` already downloads** carries
  **27,277 stock-option (STO) and 5,026 index-option (IDO) rows** with
  `OptnTp` (CE/PE), `OpnIntrst` and `ChngInOpnIntrst`. Both index and per-stock
  PCR are computable from a file already on disk, at **zero additional network
  cost**. The module discards those rows only because it filters
  `FinInstrmTp == "STF"` for futures. Same lesson as the PEAD
  "no consensus estimate for NSE" episode: *a data-source limitation is a
  measurement with a date on it, not a property of the world.*
- **Whether PCR belongs in the OI-Momentum verdict:** see
  [[analyses/PCR-in-OI-Momentum]].

## Related Concepts

- [[concepts/Market-Sentiment-Index]] — PCR's assigned home (factor 5, unbuilt)
- [[concepts/Order-Flow]] — positioning-based reads generally
- [[concepts/RSI]] — same "a tell, not a clock" discipline about divergence
- **Max Pain** — the strike where most option OI expires worthless. Different
  question (probable expiry zone from *total* option OI) from PCR's
  (sentiment from the put/call *split*). No page yet.

## Sources

- [[sources/Fingrad-PCR-Infographic]] (ingested 2026-08-07)
