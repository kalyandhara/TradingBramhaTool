---
title: "Analysis: GEX strategy-mapping — what a PoC would cost, 2026-09-05"
category: analysis
tags: [gex, gamma, options, poc, feasibility, variance-risk-premium, premium-selling, measured-null, backlog]
created: 2026-09-05
updated: 2026-09-05
sources: 1
related: [concepts/Gamma-Exposure-GEX, sources/YT-GEX-Dealer-Hedging-Volatility-Primer, sources/YT-Chris-Kmer-World-Cup-Order-Flow, analyses/Open-Backlog]
timeframe: swing
---

# Analysis: GEX strategy-mapping — what a PoC would cost

Probe prompted by [[sources/YT-GEX-Dealer-Hedging-Volatility-Primer]], which prescribes
**premium selling in positive gamma, long options in negative gamma**.

## Thesis

The question is not "can we build GEX" — that is done — but whether the source's
*strategy-selection* claim is separable from the regime claim this repo already measured
to a null, and what it would cost to find out.

## What already exists

Built 2026-08-29 under B-44 and documented on [[concepts/Gamma-Exposure-GEX]]:

- `tools/gamma_exposure.py` — engine + CLI. Per-strike IV inverted from settlement prices
  by bisection; net/gross GEX, gamma flip, call/put wall, coverage.
- `tools/gamma_regime_backtest.py` — regime backtest with an exact circular-rotation
  p-value alongside Welch.
- `tools/test_gamma_exposure.py` — 14 tests.
- `cache/gex/{NIFTY,BANKNIFTY}_gex_daily.json` — **480 sessions**, 2024-09-19 .. 2026-08-28.

It runs today. Reading for 2026-09-04:

```
NIFTY      spot 23,897.70   net GEX  -17,058 Cr/1%  (NEGATIVE)   net/gross  -9.5%
           flip 23,949   call wall 24,000   put wall 23,900   coverage 90% of 954 rows
BANKNIFTY  spot 57,369.65  net GEX     -847 Cr/1%  (NEGATIVE)   net/gross  -6.0%
           flip 57,740   call wall 57,500   put wall 57,500  coverage 96% of 314 rows
```

## Evidence against spending on this

**1. The premise measured null.** Both prescriptions are downstream of one assumption —
that forward realised vol differs materially between regimes. That was tested directly:
+0.28 / +0.24 / **−0.40** pp at 5/10/20d on NIFTY, p_rot 0.84 / 0.83 / 0.67, wrong sign at
the longest horizon. A strategy split that exists to harvest a vol difference has nothing
to harvest if the difference is not there.

**2. The regime label is a thin residual.** Note `net/gross` above: **−9.5%** and
**−6.0%**. The label is the small difference of two large opposing numbers (NIFTY:
+81,542 Cr calls against −98,600 Cr puts). Under the *naive* convention — assume customers
buy options, dealers take the other side — a modest error in who actually holds what flips
the sign. This is exactly **B-44r**, and it sits upstream of every downstream test.

**3. The claim is US-index folklore travelling without a passport.** The source names no
market. The dealer-hedging evidence base is SPX/SPY, where 0DTE flow dominates and dealer
inventory is far better documented than on NSE.

## Evidence for probing anyway

**The data is already paid for.** `nse_oi_momentum._download_bhavcopy` pulls the whole F&O
bhavcopy; the `IDO` rows carry strike, OI, settlement price, expiry and `UndrlygPric`. That
means **option prices per strike per day already pass through this repo** — enough to
reconstruct a condor or a long straddle P&L without a new vendor.

**The right test is cheaper than a strategy simulation.** Premium selling versus long
options is, economically, one number: the **variance risk premium** (realised vol minus
implied vol). If premium selling is better in positive gamma, RV−IV should be more negative
there. That is a direct test of the mechanism the source is invoking, and it skips every
confounder a strategy backtest drags in — strike selection, roll dates, spreads, assignment.

## The blocker, and it is not code

The engine computes per-strike IV but **does not persist it**. Cached fields are:

```
call_gex_cr, call_wall, coverage, date, gamma_flip, gross_gex_cr, n_contracts,
n_rows_oi, net_gex_cr, net_to_gross, put_gex_cr, put_wall, regime, spot, symbol
```

No IV. Adding `atm_iv` to `compute_gex` is a handful of lines — but populating it across
history means a **rebuild of all 480 sessions, and there is no F&O bhavcopy cache** (`find
cache -name "*bhav*"` returns nothing). So the cost is ~480 NSE downloads, rate-limited,
not an afternoon of coding. Worth doing once, and worth caching the zips this time so the
next question about this data is free.

## Conclusion — order of work, if pursued

1. **B-44r first.** Fix or bound the positioning convention. Every downstream test inherits
   the sign of a −6% residual; testing strategy on top of an unvalidated label measures the
   label, not the strategy.
2. **Persist `atm_iv` and cache the bhavcopy zips** during the rebuild, so the third step
   and anything after it costs nothing.
3. **RV−IV by gamma regime** — one split, rotation p-value, same harness as B-44. Decisive
   for the source's claim at a fraction of the cost.
4. **Strategy simulation only if step 3 separates.** Condor/straddle P&L from settlement
   prices is real work and only earns its keep after the premium itself shows a split.

**Recommendation: do not start at step 4**, which is what the source's framing invites.
Steps 1–3 are the honest path, and step 3 is allowed to end this line of work.

## Action taken

None beyond this probe and the ingest. No code written, no backlog item promoted. Filed so
the next time a GEX video lands, the answer is one page away instead of one rebuild away.

## Outcome

_To fill in if B-44r is ever picked up._

## Related pages

- [[concepts/Gamma-Exposure-GEX]] — mechanism, the B-44 null, and the rotation-p finding
- [[sources/YT-GEX-Dealer-Hedging-Volatility-Primer]] — the source that prompted this
- [[analyses/Open-Backlog]] — B-44r
