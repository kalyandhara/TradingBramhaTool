---
title: "Anchored VWAP & Pyramiding"
category: concept
tags: [vwap, anchored-vwap, pyramiding, position-scaling, confluence]
created: 2026-06-22
updated: 2026-06-22
sources: 1
related: [concepts/Order-Flow, concepts/Support-Resistance, concepts/Capital-Management-Methods, sources/SwingEdge-Learn-Process-Risk-Workflow]
---

# Anchored VWAP & Pyramiding

## Definition
**Anchored VWAP (AVWAP)** is VWAP (Volume Weighted Average Price) started from a specific past bar — an earnings day, a major pivot low, a breakout day — rather than reset every session like intraday VWAP. It shows the average price paid by every participant who has traded since that anchor, weighted by their volume.

**Pyramiding** is the discipline of adding to *winning* trades — never losing ones — using progressively smaller tranches as the trade proves itself further.

## How to Use

### Where to anchor VWAP
- **Last major swing low** — shows who is in profit since the bottom of the current leg.
- **Earnings/news day** — shows whether reactive buyers are above water.
- **Breakout bar** — confirms the average breakout buyer is still in profit (key for continuation theses).
- **Top of a base before breakdown** — for shorts, shows where trapped buyers are concentrated.

### AVWAP as dynamic support/resistance
Price above a rising AVWAP means the average participant since the anchor is in profit — psychologically, no urgency to sell. Price below means the average participant is underwater — every bounce attracts "get-me-out" supply. This gives AVWAP a direct *behavioral* interpretation, not just a mathematical one, which is why it tends to act as a cleaner dynamic level than an arbitrary moving average.

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

## Related Concepts
- [[concepts/Order-Flow]] — AVWAP's behavioral "average participant in profit/loss" framing is the same underlying mechanic as the iceberg-order/stop-cluster logic already documented there
- [[concepts/Support-Resistance]] — AVWAP confluence zones are a volume-weighted variant of standard multi-touch S/R zones
- [[concepts/Capital-Management-Methods]] — see that page's existing "Pyramiding (Adding to Winners)" section (wash-and-reclaim mechanism) for the original version this page's sizing ladder and stop-rolling rule refine

## Sources
- [[sources/SwingEdge-Learn-Process-Risk-Workflow]] (2026-06-22) — AVWAP anchor selection, confluence-zone framing, pyramiding ladder and stop-rolling rules
