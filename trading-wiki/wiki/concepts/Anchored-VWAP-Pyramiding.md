---
title: "Anchored VWAP & Pyramiding"
category: concept
tags: [vwap, anchored-vwap, pyramiding, position-scaling, confluence]
created: 2026-06-22
updated: 2026-08-02
sources: 2
related: [concepts/Order-Flow, concepts/Support-Resistance, concepts/Capital-Management-Methods, concepts/VWAP, sources/SwingEdge-Learn-Process-Risk-Workflow, sources/ForexTester-Anchored-VWAP-Guide]
---

# Anchored VWAP & Pyramiding

## Definition
**Anchored VWAP (AVWAP)** is VWAP (Volume Weighted Average Price) started from a specific past bar — an earnings day, a major pivot low, a breakout day — rather than reset every session like intraday VWAP. It shows the average price paid by every participant who has traded since that anchor, weighted by their volume.

Developed and popularised by **Brian Shannon** (alphatrends.net), whose methodology is the standard reference for the indicator ([[sources/ForexTester-Anchored-VWAP-Guide]]).

**Formula:**

```
AVWAP = Σ(Typical Price × Volume) ÷ Σ(Volume)     accumulated from the anchor, never reset
Typical Price = (High + Low + Close) / 3
```

**Price-input variants**, in order of responsiveness: `close` (most responsive — intraday preference) · **`(H+L+C)/3` (the default, and the recommended choice for swing and event work)** · `(H+L)/2` · `(O+H+L+C)/4` (smoothest).

**Pyramiding** is the discipline of adding to *winning* trades — never losing ones — using progressively smaller tranches as the trade proves itself further.

## How to Use

### Where to anchor VWAP
Ranked by analytical strength ([[sources/ForexTester-Anchored-VWAP-Guide]]):

1. **Swing high / low** — the most common and the strongest. A swing low marks where latecomers to the *prior* trend entered at the worst possible level; a swing high marks the same for the other side.
2. **Earnings / catalyst day** — where a fundamental shift in valuation expectations began; institutional cost basis since the event.
3. **IPO / first trade date** — average cost since public trading began.
4. **Breakout bar** — confirms the average breakout buyer is still in profit (key for continuation theses).
5. **Macro event (FOMC, CPI, NFP — locally RBI policy, Union Budget)** — where macro repricing began. Useful for index and currency traders tracking post-event positioning.
6. **Top of a base before breakdown** — for shorts, shows where trapped buyers are concentrated.

> [!key-insight] The anchor *is* the analysis
> The maths is trivial; **anchor selection is "the most subjective — and most critical — aspect"** of the indicator. Explicitly avoid random, low-volume bars with no structural significance — an AVWAP from a meaningless bar is a precise number describing nobody's cost basis.

### AVWAP as dynamic support/resistance
Price above a rising AVWAP means the average participant since the anchor is in profit — psychologically, no urgency to sell. Price below means the average participant is underwater — every bounce attracts "get-me-out" supply. This gives AVWAP a direct *behavioral* interpretation, not just a mathematical one, which is why it tends to act as a cleaner dynamic level than an arbitrary moving average.

### The dual-anchor bias read — and "no man's land"
A single AVWAP can only ever say *above* or *below*. **A pair can say "neither"**, which is the state worth having:

| Price is… | Reading |
|---|---|
| Above the AVWAP anchored at the **swing low** | Buyers from that low are profitable — no pressure to sell; dips toward the line attract buying |
| Below the AVWAP anchored at the **swing high** | Sellers from that high are profitable — no pressure to cover; rallies toward the line attract selling |
| **Between the two** | **"No man's land"** — neither cohort is under pressure, the edge dissolves, and trades taken here produce noise |

The third row is the one that changes behaviour: it is an explicit *stand-aside* state, derived rather than guessed, and it is the same discipline as [[strategies/Crash-Proof-3-Filter-System]]'s STAND DOWN — a condition that tells you not to act is worth as much as one that tells you to.

### Multiple AVWAPs as confluence
Plot AVWAP from the prior earnings, from the last major swing low, and from the 52-week high simultaneously. Where two or three converge, that's a confluence zone — a level multiple cohorts of buyers are anchored to. Pullbacks into confluence zones tend to bounce; breakdowns through them tend to extend.

### Pyramiding rules
1. Add only after a new structural pivot (new higher low for longs, new lower high for shorts) — never simply because price moved up.
2. Each add is smaller than the previous — a common ladder is 1 / ½ / ¼ of the original size.
3. Move the stop on *all* units up to below the new pivot after every add — never let the original stop linger once size has grown.
4. Cap total position size at a pre-defined R-equivalent — uncapped pyramiding can blow past account-level risk limits.

### Why progressively smaller adds, not equal-size adds
Equal-size adds (100%+100%+100%) create a top-heavy position: if the last add was at a higher price and the trade reverses, the blended average moves up sharply and the stop hits sooner. Progressively smaller adds keep blended cost closer to the original entry, preserving the asymmetry that made the trade attractive in the first place. This refines the wash-and-reclaim pyramiding mechanism already documented in [[concepts/Capital-Management-Methods]] (David Hannan / Laptop Legend source) with an explicit sizing ladder and a stop-rolling rule.

### Pyramiding vs. averaging down
Pyramiding adds to winners; averaging down adds to losers. The math is the asymmetry: pyramiding caps loss at the original stop and lets upside compound, while averaging down expands loss linearly with every add — and the trade being "saved" was already wrong by definition, since its invalidation was already violated. **Never add at the entry level after a pullback** — that's averaging down disguised as pyramiding.

## Common Mistakes
- Adding too late in the move — a third pyramid at the top of a 10R run is exactly the wrong time; pyramid early, not late.
- Treating AVWAP confluence as a standalone thesis — it's context, not a signal; still need structure and a defined invalidation.
- Equal-sized adds (see above) — they make blended cost climb too fast and turn small reversals into stop-outs.
- Forgetting to roll the stop forward after each add — the trade then quietly grows past the account-level risk limit it was supposed to respect.

## Implemented in this repo
Shipped 2026-08-02 in [chart_dashboard.html](tools/chart_dashboard.html) as the **Anchored VWAP (last major swing low)** indicator (`70601b3`, refined in `f7570b0`):

- `Σ(HLC/3 × V) / Σ(V)` accumulated from the anchor, never reset — **matches the reference formula exactly**.
- Anchors to the last **confirmed** zigzag swing low. Confirmed matters: the trailing pivot is provisional and moves as bars arrive, so anchoring there would slide the anchor and redraw the whole line every bar.
- **Prominence filter ≥ 2.0 ATR** on the smaller of the decline into the low and the advance out of it — a mechanical form of this page's "avoid structurally insignificant bars" rule. Measured across 7 NSE names: prominence runs median ≈1.55 ATR, p90 ≈2.25, so 2.0 keeps roughly the top fifth of lows and places the anchor 5–86 bars back instead of 3–5.
- Emits no point when volume is absent rather than substituting the close — stricter than the reference, which is silent on the case.

> [!gap] Two known gaps against this page
> **1. Only the low side is anchored.** With no high-anchored line the chart cannot express "no man's land" — it can say buyers are in profit, never that *neither* side is. Closing this is the highest-value next change to the indicator.
> **2. The anchor judgement was automated away, not exposed.** This page says anchor selection is the critical subjective act; our implementation picks it from the zigzag with no click-to-anchor, so earnings, breakout, IPO and macro-event anchors are unreachable.

## Related Concepts
- [[concepts/VWAP]] — the session-reset parent; that page's decision matrix (position / slope / bandwidth) applies to AVWAP too.
- [[concepts/Order-Flow]] — AVWAP's behavioral "average participant in profit/loss" framing is the same underlying mechanic as the iceberg-order/stop-cluster logic already documented there
- [[concepts/Support-Resistance]] — AVWAP confluence zones are a volume-weighted variant of standard multi-touch S/R zones
- [[concepts/Capital-Management-Methods]] — see that page's existing "Pyramiding (Adding to Winners)" section (wash-and-reclaim mechanism) for the original version this page's sizing ladder and stop-rolling rule refine

## Sources
- [[sources/SwingEdge-Learn-Process-Risk-Workflow]] (2026-06-22) — AVWAP anchor selection, confluence-zone framing, pyramiding ladder and stop-rolling rules
- [[sources/ForexTester-Anchored-VWAP-Guide]] (2026-08-02) — the explicit formula and price-input variants, Brian Shannon attribution, the anchor-strength ranking, and the dual-anchor "no man's land" state
