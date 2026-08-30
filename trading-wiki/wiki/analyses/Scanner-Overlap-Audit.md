---
title: "Scanner Overlap Audit — which of the 40 scanners measure the same thing"
category: analysis
tags: [scanners, overlap, redundancy, b-35, measured, scanner-hub, deduplication]
created: 2026-08-29
updated: 2026-08-29
sources: 0
related: [analyses/Open-Backlog, analyses/Backtest-Harness, concepts/Renko-Charts]
---

# Scanner Overlap Audit

B-35 asks to collapse the Scanner Hub list into family lenses under a stated invariant:
**no unique hit may be lost**. That invariant cannot be checked from names or category
labels, so `tools/scanner_overlap.py` measures it.

**Method.** Replay every registered scanner point-in-time (`fn(df.iloc[:t+1])`, the same
idiom `backtest.backtest_scanner` uses) over a 110-name NIFTY-500 stride sample,
**2,496 (symbol, as-of) cells**, and compare the resulting hit SETS. Three numbers,
because they answer different questions:

- **Jaccard** — symmetric similarity; high = near-clones.
- **Containment** P(B | A) — *asymmetric*, and the one that drives a merge. If 95% of B's
  hits are inside A but only 20% of A's are inside B, B is a near-subset: dropping B costs
  little, dropping A costs a lot. Jaccard alone would call that pair "not very similar".
- **Unique cells** — the B-35 invariant, per scanner. Zero = fully covered by the rest.

Bearish scanners are pooled separately: a bullish and a bearish detector firing on the same
cell is a contradiction, not redundancy, and mixing them would manufacture overlap.

## Result 1 — twelve bullish scanners have ZERO unique cells

Fully covered by the remaining list, i.e. removable without violating B-35's invariant:

| scanner | hits | unique |
|---|---|---|
| Minervini VCP (valchak) | **0** | 0 |
| EMA-50 Coil | **0** | 0 |
| High Tight Flag | 11 | 0 |
| IPO-Base Breakout | 14 | 0 |
| Consolidation Breakout (6M–10Y) | 17 | 0 |
| Structural Breakout | 58 | 0 |
| ATH Breakout (all-time high) | 67 | 0 |
| Triple-RS 52W Cross | 70 | 0 |
| Base Formation | 89 | 0 |
| RSI 60-40 Setup | 91 | 0 |
| RSI Mid-Band Momentum | 269 | 0 |
| 52-Week High Leaders | 401 | 0 |

**Two of them never fired at all** across 2,496 cells — *Minervini VCP (valchak)* and
*EMA-50 Coil*. Those were not redundant, they were **broken**. Both have since been
diagnosed and fixed — see the section below; the table above is the pre-fix state.

## Result 2 — the trend/momentum core is one detector wearing four names

| A | B | Jaccard | A covers B | B covers A |
|---|---|---|---|---|
| Momentum Continuation | Stage 2 Uptrend | 0.72 | 85% | 82% |
| Momentum Continuation | Pullback Entry | 0.60 | 69% | 81% |
| Pullback Entry | Stage 2 Uptrend | 0.54 | 78% | 63% |
| 52-Week High Leaders | Momentum Continuation | 0.47 | 48% | **95%** |
| 52-Week High Leaders | Stage 2 Uptrend | 0.44 | 46% | 89% |

*52-Week High Leaders* is **95% contained** in *Momentum Continuation* — 401 hits, none of
them unique. These four are the "price is in an uptrend and not extended" fact, detected
four ways.

## Result 3 — what genuinely earns its slot

Highest unique contribution (cells no other scanner flags):

| scanner | hits | unique | unique % |
|---|---|---|---|
| **Renko Flip (structure change)** | 607 | **146** | 24% |
| HM Buy (Hilega Milega) | 517 | 125 | 24% |
| Near Pivot | 887 | 68 | 8% |
| Order Block Retest | 276 | 43 | 16% |
| Candlestick Patterns | 147 | 32 | 22% |
| %R Bottoming | 85 | 26 | 31% |
| Harmonic Reversal (XABCD) | 61 | 19 | 31% |
| Falling Wedge | 19 | 7 | 37% |

Both scanners in `MEASURED_EDGE_SCANNERS` (Falling Wedge, Harmonic Reversal) sit in this
group — the two things the vault has measured as having edge are also the two that see
something nothing else sees. That is the pattern worth generalising.

The new **Renko Flip** screen has the largest unique contribution in the registry, which is
what a *price*-sampled detector buys when every other scanner is *time*-sampled.


## The two dead scanners — diagnosed and fixed (2026-08-29)

Both fired **0 times in 2,496 cells**. Instrumenting each gate and counting survivors gave
two different diagnoses, so they needed two different fixes. Neither was fixed by loosening
a threshold until it fired.

### EMA-50 Coil — two undocumented gates contradicted the scanner's own premise

Survivor funnel: 2,496 cells → 1,546 above EMA200 → 749 ADX≥25 → 409 ADX *rising* → 375
+DI>−DI → **1** within 2% of the EMA-50 → 0 with the thrust.

The port carried **"ADX rising vs prior bar"** and **"+DI > −DI"**, neither of which is in
the documented source (Ashok Daniel's StockEdge screen: *ADX > 25, close within 2% of
EMA-50, close > 1.03× prior on above-average volume*). Those two gates select a stock whose
trend is **already accelerating** — which is, by construction, a stock **extended away from
its 50-EMA**. This scanner exists to catch the opposite state. The measurement shows it
exactly: of the 375 cells that cleared ADX-rising + DI, precisely **one** was also resting
at the mean.

Fix: drop the two undocumented gates, restoring the source. `close > EMA200` is kept as
context and deliberately **not** dropped — doing so would raise hits from 5 to 8, which is
fire-rate chasing, not correctness.

**Result: 5 hits (0.20%), 1 unique.** Still rare *by nature* — "resting at the mean" and
"thrusting 3% today" only coincide when a stock gaps up into its 50-EMA from below. Sample
hit: BEL 2025-01-30, price 275.0 sitting 1.9% below EMA50 280.3, +4.3% thrust on 2.9×
20-day volume, above EMA200. That is the setup as written.

### Minervini VCP (valchak) — the ratio test was applied to the wrong list

Survivor funnel: 756 passed the Trend Template → 111 had geometry → 61 first-depth →
59 final-depth → **0** survived `every step tightens ≤0.9×`.

`detect_vcp_geometry` returns the **raw pivot-to-pivot contractions** in the window, and
real bases oscillate. Measured depth sequences look like:

```
[14.2, 10.2, 8.0, 5.3, 10.5, 5.7]     ratios 0.72 0.78 0.66 1.98 0.54
[18.2,  8.9, 10.0, 6.0, 13.0, 4.8]    ratios 0.49 1.12 0.60 2.17 0.37
```

Clearly contracting overall (14.2 → 5.7), but **one widening leg fails a strict all-pairs
test**, and essentially every real base has one. valchak's script never tests a raw list —
it only *counts* a contraction when it is tighter than the previous, so the ratio test
belongs to a **tightening run**, not to everything the detector saw.

Fix: take the longest run ending at the most recent contraction where each step tightens by
≤ cap, and apply the depth ranges to **that run**. A widening leg earlier in the window now
ends the run instead of invalidating the whole base. The duplicate first/final range checks
on the raw list were removed for the same reason — they were the same bug one layer up. The
reported footprint now describes the run too (it previously printed six legs next to
"2 contractions", inviting the reader to check a number the gates never used).

**Result: 3 hits (0.12%), 0 unique.** Sample: JUBLINGREA 2024-08-07, 2 tightening
contractions 15%→5%, close 661.33 above pivot 616.19 on 4.8× 50-DMA volume, only 7.3%
extended. A textbook VCP breakout.

### Honest read on the two after the fix

- **EMA-50 Coil now earns a slot on this evidence** — small, but it contributes a cell
  nothing else flags.
- **Minervini VCP still contributes zero unique cells.** All 3 hits are also flagged by
  Stage 2 Uptrend, Momentum Continuation, 52-Week High Leaders, ADX Trend Confirmation and
  Early Reversal. That containment is **structural, not coincidental**: its Trend Template
  gate tests essentially what Stage 2 Uptrend tests. Fixing it made it *work*; whether it
  is *kept* is still the B-35 question, and at n=3 the unique measure is noisy either way.
- **Regression checked:** re-running the audit after the fixes, **37 of 40 scanners have
  identical hit counts** — only the two repaired scanners and the newly-added Renko screen
  moved.


## Acted on (2026-08-29) — nine scanners hidden, none deleted

`opportunity_hub.COVERED_SCANNERS` + `core_scanners()`; the Scanner Hub card grid defaults
to the **32-scanner core**, with a **"Show 9 covered scanners"** checkbox restoring the
rest. Hidden, never removed — they stay registered, runnable, backtestable and active in
the confluence pipeline.

### The stability rule

The audit was run on **two independent samples** — a 1500-day window and full listing
history — and three scanners *disagree* between them, which is the signature of a sampling
artefact rather than a property of the scanner:

| scanner | 1500-day | full history | verdict |
|---|---|---|---|
| High Tight Flag | 11 hits, **0** unique | 19 hits, **1** unique | unstable → stays visible |
| Structural Breakout | 58 hits, **0** unique | 64 hits, **2** unique | unstable → stays visible |
| Rounding Bottom | 89 hits, **1** unique | 75 hits, **0** unique | unstable → stays visible |

**So the rule is: hide only what measures zero-unique in BOTH samples.** The first cut of
this list was made on the single 1500-day run and hid *High Tight Flag* and *Structural
Breakout* — two scanners that do carry unique hits on the better data. That was wrong and
is corrected here; the episode is the argument for the two-sample rule.

### The hidden nine (zero unique in both samples)

| hidden | 1500d | full | note |
|---|---|---|---|
| 52-Week High Leaders | 401 | 285 | 95% contained in Momentum Continuation |
| RSI Mid-Band Momentum | 269 | 200 | 93% contained in Pullback Entry |
| Base Formation | 89 | 95 | 99% contained in Stage 2 Uptrend |
| RSI 60-40 Setup | 91 | 84 | |
| Triple-RS 52W Cross | 70 | 63 | 99% contained in 52-Week High Leaders |
| ATH Breakout (all-time high) | 67 | 45 | see the correction below |
| Consolidation Breakout (6M–10Y) | 17 | 8 | 100% contained in Pullback Entry |
| IPO-Base Breakout | 14 | 6 | see the correction below |
| Minervini VCP (valchak) | 3 | 4 | containment is structural |

### Correction — ATH and IPO-Base were measured invalidly the first time

An earlier version of this page called their counts "floors". That was wrong: they were
**unusable**. The replay hands each scanner `df.iloc[:t+1]`, which only means "everything
known at t" if the frame **starts at the listing**. On truncated frames:

- **ATH Breakout** read the slice max as an all-time high — on a 261-bar slice that is a
  one-year high, so it fired on fake ATHs;
- **IPO-Base Breakout** gates on listing age as `len(df)`, so at early as-of dates every
  stock looked freshly listed and it fired on decades-old companies.

The full-history re-run confirms both artefacts directly: **ATH fell 67 → 45 hits and
IPO-Base 14 → 6** once fed real history. Both then measure zero-unique in *both* samples,
which is why they are now hidden. `scanner_overlap.py` documents `--days 0` as required for
any `needs_full_history` scanner and caches those frames separately so the runs cannot mix.

### Why hidden and not deleted

The measurement licenses exactly one claim: *removing these from the default view loses no
hit another scanner does not already flag*. It does **not** show they are worthless — a
covered scanner can be the more precise expression of a setup, and coverage says nothing
about edge. Deletion would assert something unmeasured. The change reduces what has to be
**read**, not what the system can do. The question deletion turns on is
`backtest.backtest_scanner` per scanner, which has not been run for these.

Guards: the currently-selected scanner stays visible even when covered (so a saved session
never shows a caption with no card), and *Minervini VCP* is hidden on n=3/4 only because
its containment is structural — its Trend Template gate tests what Stage 2 Uptrend tests.

## What this does and does not license

- It **does** justify collapsing the trend/momentum quartet and retiring the zero-unique
  twelve behind a lens, with the B-35 invariant provably intact.
- It does **not** say the zero-unique scanners are worthless. A scanner with no unique
  cells can still add *precision* — a tighter, higher-quality subset of a broader
  detector. Overlap measures coverage, not quality.
- **Overlap is not edge.** Two scanners can be perfect clones and both be worthless; the
  edge question belongs to `backtest.backtest_scanner`. Cutting the list on overlap alone
  optimises for tidiness, not for returns.
- ATH / IPO-base breakout carry `needs_full_history`; the first run measured them
  **invalidly**, not conservatively — see the correction above. Use `--days 0`.

## Reproduce

```
py -3 tools/scanner_overlap.py --limit 110 --asof 26
```

Frames cache to `tools/cache/overlap/`, so re-runs cost nothing.
