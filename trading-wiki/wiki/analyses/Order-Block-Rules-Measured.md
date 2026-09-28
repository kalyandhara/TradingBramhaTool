---
title: "Order Block Rules — MEASURED 2026-09-13: one null, one inversion, one undecidable"
category: analysis
tags: [order-blocks, smc, backtest, measured, b-76, measured-null, inverted-signal, retired]
created: 2026-09-13
updated: 2026-09-13
sources: 0
related:
  - analyses/Order-Block-Rules-Pre-Registration
  - analyses/Backtest-Harness
  - analyses/Open-Backlog
  - concepts/Order-Blocks
---

# Order Block Rules — MEASURED

Results for the three rules pre-registered in
[[analyses/Order-Block-Rules-Pre-Registration]]. **The design, the floor and the
decision rule were fixed before any forward return was looked at**, and every
consequence below was written down in advance of the number that triggered it.

**Universe** `backtest.LIQUID_50`, 1500d daily, stride 5, point-in-time slices,
entry at next bar's open, pessimistic tie-break. **Baseline @20d = +0.958% gross /
+0.662% net** (`COST_INDIAN`) — a constructive tape, which is exactly why "edge"
means *against that*, not against zero.

Both cost bases were run in full. **Net changes no sign and no consequence**, and
it makes Rule A worse and Rule B's bearish side worse — so every headline below is
quoted net where net exists, with gross alongside.

## Headline

| Rule | Claim as shipped | Measured | Consequence applied |
|---|---|---|---|
| **A** target ladder | nearest opposing zone beats the fallbacks | **null** — no separation between the three; all negative net | **ladder collapsed to flat 2R** |
| **B** stacked-zone bias | stacked zones confirm the lean | **INVERTED** — points the wrong way, 40/44 names | **gauge retired** |
| **C** early vs confirmed | they are different entries | **undecidable at this n** | both kept, difference not claimed |

---

## Rule A — target selection: a null, and the ladder is gone

374 plans, 270 filled (72% fill rate on a 40-bar limit window). Measured
**paired** — same zone, same entry, same stop, only the target varying.

| Target rule | R gross | R **net** | target-hit | stopped |
|---|---|---|---|---|
| nearest opposing zone | +0.007R (p=0.94) | **−0.125R** (p=0.22) | 26.2% | 70% |
| displacement extension | −0.032R (p=0.68) | **−0.164R** (p=0.037) | 38.0% | 61% |
| flat 2R | +0.026R (p=0.76) | **−0.095R** (p=0.27) | 33.9% | 65% |

Paired against flat 2R — gross **−0.019R (p=0.76)** / **−0.058R (p=0.26)**; net
**−0.030R (p=0.64)** / **−0.069R (p=0.19)**. Null on both cost bases.

> [!warning] Net of costs the plan is not merely flat — it is negative
> Gross, the surviving 2R plan reads as indistinguishable from zero. Net of NSE
> delivery costs it is **−0.095R**, and the displacement target it replaced is the
> only arm significantly negative (−0.164R, p=0.037). A plan that does not survive
> its own costs is not a plan, and the code header now says so in those words.

> [!key-insight] The targets differ; the expectancy does not
> Target-hit rates of 26% / 38% / 34% prove the three rules were picking
> genuinely different distances — this is not a case of three labels for one
> number. And expectancy is flat across all of them anyway. The ladder was
> buying **the appearance of structure**, not a better exit.

**CONSEQUENCE APPLIED** (pre-registered: *"no separation ⇒ collapse the ladder to
the simplest rule (2R) and say why"*). `detect_order_blocks` now sets
`target = entry ± 2R` and the three-step ladder is deleted. `rr` is gone from the
payload and from the chart label: with a flat 2R the ratio is a constant, and
printing a constant every time dresses a definition up as a finding.

**What this does NOT license.** The surviving plan is **−0.095R net** (+0.026R
gross) — flat before costs and negative after them. The rails stay drawn as the
detector's own geometry, and the number is now in the code header and docstring so
the next reader cannot mistake it for an edge. This is the
[[analyses/Open-Backlog#B-74]] move: keep the geometry, drop the claim.

---

## Rule B — stacked-zone bias: inverted, and retired

Raw 20-day forward return, against a +0.958% gross / +0.662% net baseline:

| Gauge said | Raw fwd @20d (gross / net) | n | Edge vs **direction-matched** benchmark |
|---|---|---|---|
| BULLISH | +0.696% / **+0.398%** | 8,948 / 8,921 | −0.262pp / **−0.264pp** (p=4.2e−4) |
| BEARISH | +2.186% / **+2.501%** | 2,143 / 2,164 | −1.229pp / **−1.839pp** (p=5.6e−35) |

Direct test of the pre-registered H1 (*bullish lean → higher forward return than
bearish lean*): **t = −9.05, p = 2.3e−19** gross and **t = −12.79, p = 1.3e−36**
net, difference **−1.49pp / −2.10pp in the wrong direction.** When the gauge said
BEARISH, the tape went **up more** than when it said BULLISH — and costs widen the
gap, because they penalise the (wrong) short side hardest.

### The control that mattered

The pooled test is not sufficient on its own and the pre-registration should have
said so. A stacked lean **persists** — one regime supplies dozens of consecutive
stride bars on one name — so n=8,948 is nowhere near 8,948 independent draws and
the pooled p-value is inflated by an unknown factor. A retirement cannot rest on it.

Re-run with the **symbol as the unit of analysis** (`tools/ob_bias_clustered.py`),
one number per name, 50 clusters:

| Lean | Mean edge | Median | t | Names negative |
|---|---|---|---|---|
| bullish (vs long-random) | **−0.373pp** | −0.197pp | −4.60 | **38 / 50** |
| bearish (vs short-random) | **−2.361pp** | −1.961pp | −6.54 | **40 / 44** |

The inversion survives clustering. It is not an artefact of counting the same
regime many times.

**Mechanism, plausibly.** In a constructive tape, a bearish stack accumulates
precisely after a run of weakness — which is when mean reversion is most likely.
The gauge was systematically most bearish at local bottoms. That is worse than
noise: it is a signal that is confidently wrong when it is loudest.

**CONSEQUENCE APPLIED** (pre-registered: *"inverted ⇒ retire the gauge, B-44r
precedent"*). The `.ob-info` card, `renderObBias`, its CSS and its teardown are
deleted; a tombstone comment carrying these numbers sits where it was. Not
relabelled, not inverted-and-kept — **retired**, exactly as GEX was in
[[analyses/Open-Backlog#B-44r]].

> [!warning] Why it was not simply flipped
> Flipping an inverted signal is fitting the sign to one window. The stack count
> also failed to grade monotonically (1× −0.220, 2× −0.373, 3×+ +0.323), so there
> is no stable structure to invert — only a number that happened to lean the wrong
> way in this tape. Net, the grading is worse: **1× −0.713, 2× −0.592, 3×+ +0.009** —
> every bucket at or below zero, and the *largest* stack the least wrong of the three.

---

## Rule C — early vs confirmed: undecidable at this sample

| Kind | fwd @20d net | edge vs baseline net | R gross / net | n |
|---|---|---|---|---|
| early (wick rejection) | −0.408% | −1.070pp (p=0.07) | +0.102R / **−0.006R** | 190 |
| confirmed (cross) | +0.528% | −0.134pp (p=0.82) | −0.052R / **−0.119R** | 160 |

early vs confirmed @20d: **t = −1.12, p = 0.26** gross; **t = −1.14, p = 0.26** net.
The test is stable across cost bases and still cannot separate them.

**This is a failure to reject, not a demonstration of equivalence.** At n≈175 per
arm the test cannot resolve a difference of the size observed (0.92pp), so the
pre-registered *"no difference ⇒ collapse to one marker"* branch is **not** applied:
applying it here would mean deleting a distinction on the strength of a test too
weak to see it. Both markers stay, and the chart continues to distinguish them —
but nothing claims one is better, and the pre-registration's own note stands that
"early is better" was never the hypothesis.

Both sit at or below baseline, consistent with the harness's earlier
**−0.74% @20d** on the Order Block Retest scanner. The zone remains a null.

---

## Evidence For / Against

**For:** pre-registered before the data; point-in-time by construction; the
same-bar-only recording rule closes the survivorship hole that back-dating events
would have opened; the inversion is confirmed under clustering, which is the
conservative unit.

**Against:** one universe, one ~6y mostly-constructive window, survivorship bias
(names listed today), no walk-forward. Rule B's mechanism is *inferred*, not tested
— a regime split would test it and has not been run. Rule C is underpowered and
honestly so. Daily bars cannot resolve intra-bar stop-vs-target order, hence the
pessimistic tie-break.

## Action Taken

- ✅ **Rule A ladder collapsed to flat 2R**; `rr` removed from payload and label;
  the **−0.095R net** measurement written into the code header and the docstring.
- ✅ **Rule B gauge retired outright**, tombstone comment carries the numbers.
- ⏭ **Rule C left standing, undecided.** Reopen with a wider universe if the
  distinction is ever load-bearing; it is not today.
- ⏭ **Rule B regime split** — does the inversion hold in a flat or falling window?
  The [[analyses/Open-Backlog#B-74r]] shape. Not required for the retirement, which
  already holds 3 ways (pooled, direction-matched, clustered).
