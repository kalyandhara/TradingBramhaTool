---
title: "Bramesh Tech Analysis — NIFTY: first higher high in 20 sessions, 1×3 Gann angle, and a claimed institutional short squeeze"
category: source
type: source
source_type: blog-post (daily market letter, named author, commercial site)
author: Bramesh Bhandari (Bramesh Tech Analysis)
url: https://brameshtechanalysis.com/2026/09/18/nifty-forms-first-higher-high-in-20-days-1x3-gann-reversal-meets-heavy-institutional-short-squeeze/
fetched: 2026-09-18
for_session: 2026-09-18 (NSE)
tags: [nifty, gann, gann-angles, trend-change-level, option-chain, max-pain, open-interest, put-call-ratio, fii-dii, participant-positioning, short-squeeze, intraday, date-decaying, unbacktested]
related: [entities/NIFTY, concepts/Gann-Angles-And-Trend-Change-Levels, concepts/Participant-Positioning-FII-DII, concepts/Put-Call-Ratio, concepts/Support-Resistance, analyses/Open-Backlog]
created: 2026-09-18
updated: 2026-09-18
sources: 0
---

# Bramesh Tech Analysis — NIFTY, 2026-09-18

**First named-author Indian daily market letter in this vault**, and the first source
here that is *entirely* about the index rather than about a method. That changes how it
should be read: almost everything in it is **a call for one session**, and a call for one
session decays to nothing within a day. The durable content is the **vocabulary and the
mechanism** — Gann angles, the Trend Change Level, participant-wise F&O positioning —
which is why those were promoted to concept pages and the levels were not.

Author's own disclaimer, reproduced because it belongs on the page: *"I am not a SEBI
Registered Advisor"*, content *"intended solely for educational purposes."*

## What it says

**The headline claim.** Nifty closed **23,270** on 2026-09-17, **+61 points**, and in doing
so *"generated its first higher high in 20 sessions right off the foundational 1×3 Gann
angle"*, after seven consecutive weeks of decline.

### Levels

| Role | Level | Author's reason |
|---|---|---|
| Resistance | **23,500** | highest **call** OI — primary ceiling |
| Resistance | 23,440 | overhead descending trendline |
| **Positional TCL** | **23,372** | trend-change level; the bull case is contingent on holding above it |
| Intraday TCL | 23,327 | intraday trend-change pivot |
| Max pain | 23,300 | — |
| **Spot** | **23,270** | — |
| Support | 23,244 | double-ingress low & Gann inflection |
| Support | 23,189 | Gann harmonic number |
| **Invalidation** | **23,135** | must-hold buffer; failure *"closes the door toward 23,000"* |
| Support | 23,100 | highest **put** OI — major institutional floor |
| Bear acceleration | 23,070 / 23,000 | — |

Intraday ladder: bull trigger **23,350** → T1 **23,396** / T2 **23,444** / T3 **23,484**;
bear trigger slip **23,312** → S1 23,280 / S2 23,244 / S3 23,208. Stated upside once shorts
cover: **23,484 / 23,550**.

Intraday "time reversal windows": **10:07, 11:35, 12:45, 13:30, 14:48**.

### Positioning — the actual argument

| Reading | Value |
|---|---|
| FII index-futures **long : short** | **12 : 88** (ratio 0.14) |
| FII day's change | +102 longs vs **+2,040 shorts** (**₹245 crore**) |
| Client/retail long : short | 84 : 16 (ratio 5.25) |
| Client day's change | +5,180 longs, −466 shorts |
| FII **cash** | **−₹3,208 crore** |
| DII cash | **+₹3,617 crore** |
| Sept Nifty futures OI | ₹1.76 lakh crore |
| OI change | **−0.79 lakh contracts** (author reads as short covering) |
| PCR | **0.99**, rebounded from 0.65 |
| Breadth | 36 : 14 advance–decline |

The thesis: **88% short is fuel.** A bounce off the 1×3 angle forces that book to cover,
which carries the index to 23,484 / 23,550.

## Arithmetic and internal consistency — checked

Every stated ratio reconciles: 12/88 = 0.136 ≈ **0.14 ✓**; 84/16 = **5.25 ✓**;
36 + 14 = **50 ✓** (Nifty 50 constituents, so the breadth is the index's own).

**Three things do not.**

1. **The ₹245 crore does not match 2,040 NIFTY contracts at current lot size.**
   2,040 × 23,270 = ₹4.75 crore of index points; at the NSE's **75-unit** lot that is
   **₹356 crore**, and net of the 102 longs, **₹338 crore**. ₹245 crore implies a lot of
   roughly **50** — the pre-2024 size — or a different contract mix than the label says.
   The *direction* is unaffected; the **rupee figure is not reproducible from the contract
   count as printed**, so cite the contracts, not the crores.

2. **"FIIs added 2,040 shorts" and "OI liquidation of 0.79 lakh contracts signals short
   covering" point opposite ways** in the same section. Both can be true of different books
   — FIIs adding while someone else unwinds — but the letter uses each where it helps, and
   never reconciles them.

3. **"DII absorbing the selling" understates it.** −3,208 FII against +3,617 DII is
   **net institutional +₹409 crore**. Domestics did not absorb the selling; they out-bought
   it.

## The load-bearing weakness: a *level* offered as a *trigger*

> [!warning] 88% short is a state, and that state was already true while the market fell
> The squeeze thesis rests on the FII short ratio being extreme. But an extreme ratio is
> a **persistent state**, not an event — and by the letter's own framing it persisted
> through **seven consecutive weeks of decline**. Whatever the reading was worth, it was
> not worth being long during those seven weeks.
>
> This is exactly the failure mode [[analyses/SVP-Structure-Signal-Pre-Registration]] was
> written around: a slow-moving state series scored as if each day were an independent
> observation. On this desk's own precedent (`gamma_regime_backtest._rotation_p`) a known
> null printed **p = 0.031** under a t-test and **p = 0.32** under circular rotation. Any
> future test of "extreme FII short ratio → forward return" **must** use rotation, or it
> will manufacture significance out of autocorrelation. Filed as **B-95**.

Two smaller reads worth keeping:

* **At 23,270 the letter's own stance is neutral, not bullish.** The bull case needs
  23,372 (+102, +0.44%) and dies below 23,135 (−135, −0.58%). Spot sits between them, so
  the "bullish continuation" label describes a condition that has not occurred yet.
* **Max pain at 23,300 is 0.13% from spot** and therefore carries no directional
  information this session. It is reported as if it did.
* The five "time reversal windows" are ~one per 75 minutes of a 6h15m session. With no
  stated construction and no hit criterion, the claim is **not falsifiable as written**.

## What this desk can actually check

**The option-chain block is fully reproducible here, today.** `tools/option_chain.py`
already computes max pain and the OI walls for indices (IDO) from the F&O bhavcopy, with
the one-expiry rule enforced. So 23,300 / 23,500 / 23,100 are not claims that have to be
taken on trust — they can be recomputed. Filed as **B-94**, and it is the cheapest
verification available: it scores a source's reliability against a tool that already exists.

**The participant block cannot.** Grepping the toolchain, `FII` appears only in
`block_deal_intel.py`, where it is a *shareholding-name classifier* — nothing on this desk
reads NSE's participant-wise F&O OI. That is a data gap, not a build gap, and B-95 is
gated on closing it first.

## Contradictions with existing wiki

**None.** The PCR reading is consistent with [[concepts/Put-Call-Ratio]] and the OI-wall
logic matches what `option_chain.py` already implements (call wall = resistance, put wall =
support), which is mild corroboration from an independent practitioner. Gann angles and the
Trend Change Level were simply **absent** — no page claimed anything about them to
contradict.

## What was promoted, and what was declined

**Promoted:**
* [[concepts/Gann-Angles-And-Trend-Change-Levels]] — the geometry and the TCL construct,
  the author's actual method.
* [[concepts/Participant-Positioning-FII-DII]] — the long:short ratio framework, with the
  state-vs-event warning attached at birth.
* [[entities/NIFTY]] — created; the index had no page despite being the reference for
  everything on this desk.

**Declined, with reasons:**
* **Every specific level.** They are one session old by the time anyone reads this. They
  are recorded above as a *dated snapshot* and are not restated on the entity page as
  live levels.
* **The 23,484 / 23,550 targets.** A projection contingent on a squeeze that has not
  happened, from an unbacktested method.
* **The time-reversal windows.** Unfalsifiable as stated.
* **"Double ingress"** — used without definition. Not documented rather than guessed at.

## Provenance tier

**Mid.** Named author, dated, live URL, specific falsifiable levels, and an explicit
non-advisor disclaimer — materially better than this vault's AI-summary tier. But: a
commercial site whose business is daily calls, **no backtest, no hit rate, no sample, and
no losing example**. Treat as **a well-specified opinion with checkable inputs**, and check
the inputs.
