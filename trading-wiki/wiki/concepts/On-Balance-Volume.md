---
title: "On-Balance Volume (OBV)"
category: concept
tags: [indicator, volume, divergence, accumulation-distribution, obv]
timeframe: daily
created: 2026-09-11
updated: 2026-09-11
sources: 4
related:
  - analyses/Open-Backlog.md
  - concepts/Chaikin-Money-Flow.md
  - analyses/Indicator-Coverage-Gap.md
---

# On-Balance Volume (OBV)

Joe Granville's running total of volume, signed by the direction of the close.
It answers one question: **has volume been arriving on up-closes or on
down-closes, cumulatively?**

Written 2026-09-11 for [[analyses/Open-Backlog#B-17]] — the desk shipped **two**
OBV surfaces (the indicator, then B-61's divergence overlay) and documented
neither. [[concepts/Chaikin-Money-Flow]] was written alongside its build; this one
is the same debt, paid late.

## The arithmetic

```
OBV[0] = 0
OBV[i] = OBV[i-1] + Volume[i]    if Close[i] > Close[i-1]
       = OBV[i-1] - Volume[i]    if Close[i] < Close[i-1]
       = OBV[i-1]                if Close[i] = Close[i-1]
```

That is the whole indicator. No window, no smoothing, no parameters — which is
why it has none to tune and none to overfit.

**Two consequences follow directly from the formula, and both matter more than
the formula does:**

1. **The level is meaningless; only the shape is real.** OBV starts at zero at
   whatever bar your series happens to start on, so its absolute value is an
   artifact of the window. Two charts of the same stock over different ranges
   print different OBV levels. **Never compare OBV across symbols, and never read
   a level — read the slope and the sequence of highs and lows.**
2. **A bar's ENTIRE volume is booked on the sign of its close.** A stock that
   closes up ₹0.05 on 10 crore shares adds the whole 10 crore; one that closes
   down ₹20 on 10 crore subtracts the whole 10 crore. **Magnitude of the move is
   discarded entirely.** This is the source of nearly every OBV false signal.

## Reading it

| what you see | reading |
|---|---|
| OBV rising with price | the advance is being paid for — confirmation |
| OBV flat while price rises | the advance is not attracting volume |
| OBV falling while price rises | **bearish divergence** — distribution into strength |
| OBV rising while price falls | **bullish divergence** — accumulation into weakness |
| OBV breaking its own trendline | often precedes the price doing so (Granville's claim) |

Granville's framing was that **volume precedes price**. That is the claim the
divergence surface below is built on, and it is a claim — not something this desk
has measured. See *What this desk has and has not measured*.

## The two surfaces that ship here

### 1. `obv` — the indicator (sub-pane oscillator)

`obvSeries` in `tools/chart_dashboard.html`, drawn in its own sub-pane.

> [!note] Its axis labels are compact for an alignment reason, not a cosmetic one
> Raw OBV is a running share count in the billions, so labels rendered as
> `2934007946.00`. The sub-pane's price scale has a **minimum** width of 72px, and
> twelve digits pushed it past that — which narrowed OBV's plot area, so its right
> edge visibly stopped short of every other sub-pane. `2.93B` fits inside the
> shared 72px, so the panes line up. Recorded because it looks like formatting and
> is actually layout.

### 2. `obvdiv` — OBV Divergence (B-61, `tools/obv_divergence.js`)

The four divergence types read off OBV instead of RSI:

| | price | OBV | meaning |
|---|---|---|---|
| **Regular bullish** | Lower Low | Higher Low | selling pressure not expanding |
| **Regular bearish** | Higher High | Lower High | the advance lacks volume support |
| **Hidden bullish** | Higher Low | Lower Low | continuation |
| **Hidden bearish** | Lower High | Higher High | continuation |

**It contains no divergence walk of its own.** It computes OBV and hands it to
`RSIDIV.compute` as the injected series — that module already walks confirmed
zigzag pivots and applies exactly this table. A second copy of the walk would be
the same logic maintained twice — the failure [[analyses/Open-Backlog#B-24]]
recorded when two RSI-divergence implementations were allowed to disagree (closed
2026-09-02).

> [!warning] OBV is not RSI, and the difference changes how to read the output
> RSI is bounded 0–100 and mean-reverting. **OBV is an unbounded running total, so
> it trends with the market.** In a sustained advance nearly every OBV swing low is
> a higher low, which makes *"price lower low + OBV higher low"* **cheaper to
> satisfy** than the RSI equivalent.
>
> **Expect MORE divergences from this module than from the RSI one on the same
> bars, and do not read the extra ones as extra evidence.** They are a property of
> the series being cumulative, not of the market being more divergent.

## The one-big-bar artifact, and what the desk does about it

Because OBV books a bar's whole volume by the sign of its close, **a single
enormous print — a news candle, an index rebalance, a block deal — can bend the
line into a divergence that no genuine flow produced.** LuxAlgo names this as the
main false-signal source and suggests inspecting the bars by hand.

Every divergence this desk emits carries **`volConcentration`**: the largest
single bar's share of total volume across that divergence's own window. **At 0.5,
one session IS the divergence.** It is returned per-divergence rather than
thresholded in the module, so the reader decides — and `volume_anomaly` can
already attribute such a spike to a cause.

That is the difference between a warning in a docstring and a number on the card.

## OBV vs the desk's other volume tools

| tool | what it measures | shape |
|---|---|---|
| **OBV** | volume signed by **close-to-close direction**, cumulative | unbounded running total |
| [[concepts/Chaikin-Money-Flow]] | where the close sat **inside its own bar's range**, volume-weighted | bounded ratio, ±1 |
| **MFI** (`_mfi_series`) | volume-weighted RSI on **typical price** | 0–100 oscillator |
| **Volume Profile** | volume at **price** | distribution, not a series |

**OBV and CMF fail in opposite directions, which is the useful part.** CMF
*ignores the previous close entirely* — it cannot see gaps, so a hard gap down
that closes mid-range prints rising CMF. OBV *only* sees the previous close — it
cannot see where inside the bar anything happened, so a ₹0.05 up-close books the
same volume as a limit-up move. **Neither is a better version of the other, and
when they disagree that disagreement is information about which artifact is
firing.**

## What this desk has and has not measured

**Not measured, and this is the honest state:** no forward-return test exists for
either OBV surface. B-61 shipped as a **chart overlay, drawn as context**, with
its own docstring saying *"nothing here is a signal"* and pointing at LuxAlgo's
advice to require price confirmation before acting.

The relevant priors from elsewhere on this desk, none of them about OBV directly:

- [[analyses/Open-Backlog#B-19]] measured most single-condition scanners at **no
  edge after costs**, which is the base rate any new volume signal argues against.
- **The RSI-divergence engine this module reuses HAS been scored**, and its result
  is the nearest thing to a prior for this one:

  | B-19 verdict | signals | 20d | 60d | |
  |---|---|---|---|---|
  | RSI Divergence Bull | 211 | +0.36% | +0.93% | POSITIVE EDGE **[UNSTABLE]** |
  | RSI Divergence Bear | 403 | −0.84% | −1.18% | BEARISH EDGE **[UNSTABLE]** |
  | RSI-Fibo Hidden Divergence | 11 | −0.10% | −0.08% | TOO FEW SIGNALS |

  Both directions point the way the concept says they should, and **both are
  flagged UNSTABLE** — which means the sign did not hold across the walk-forward
  windows. That is weak support, not a result to build on, and it says nothing
  about OBV as the input: the same walk on a *cumulative, trending* series is a
  different experiment (see the warning above about divergences being cheaper to
  satisfy).
- `volume_anomaly` ships as an **attention list**, not a signal, for the same
  reason.
- **An overlap check against the RSI pane is owed first**, and it is a gate rather
  than a study: if OBV's divergences are largely the same events the RSI pane
  already marks, there is nothing separate to measure. This is exactly the check
  that killed the PSAR signal idea (B-59: a superset at 8.4× the cadence), and it
  is cheaper than a backtest.

**If OBV divergence is ever promoted past "drawn as context", it needs its own
pre-registered test** — the pattern [[analyses/PCR-Sign-Convention-Pre-Registration]]
and B-58 now set here: fix the event, the baseline, the horizon and the decision
rule before the first number is seen.

## What it is NOT

- **Not order flow.** OBV infers accumulation from the sign of a close. It does
  not see the tape, the bid/ask, or who traded. [[analyses/Open-Backlog#B-48]] is
  the open item about the aggressor side the desk genuinely does not have.
- **Not comparable across symbols.** The level is an artifact of the start bar.
- **Not meaningful without volume.** On a series with no turnover — `^NSEI`
  carries **1,333 zero-volume bars out of 4,648** — OBV is a flat line saying
  nothing. Same data gap that makes MFI undefined over a quarter of NIFTY's
  history (found by B-45's parity test).

## Implementation note: two copies, and why they cannot drift

`obvSeries` exists in **both** `chart_dashboard.html` and `obv_divergence.js`. The
module's copy is a fallback so it works standalone; **the shipped path injects the
chart's own series** (`OBVDIV.compute(bars, {obv: obvData})`), so the line you SEE
and the values a divergence is measured from are the same array. The caller's
series wins whenever there is one.

Worth knowing rather than worth fixing — but if the two ever need to be
reconciled, `tools/test_mfi_parity.py` is the pattern: slice the function out of
the HTML, run it in node, compare.

## Related

- [[concepts/Chaikin-Money-Flow]] — the bounded, range-location counterpart that
  fails in the opposite direction
- [[analyses/Open-Backlog#B-61]] — the divergence overlay build
- [[analyses/Open-Backlog#B-17]] — this page's own backlog item
- [[analyses/Indicator-Coverage-Gap]] — where OBV sits in the coverage inventory
- [[analyses/Open-Backlog#B-48]] — cumulative volume delta, the real order-flow gap

## Sources

- [StockCharts ChartSchool — On Balance Volume (OBV)](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/on-balance-volume-obv)
- [Investopedia — On-Balance Volume (OBV)](https://www.investopedia.com/terms/o/onbalancevolume.asp)
- [LuxAlgo — OBV divergence](https://www.luxalgo.com/library/indicator/on-balance-volume-obv/) — the four-variant table B-61 was built from
