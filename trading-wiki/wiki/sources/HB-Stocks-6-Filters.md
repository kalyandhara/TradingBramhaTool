---
title: "Image — 6 Filters Saved Me From Hundreds of Bad Charts (Haseeb Badar)"
category: source
tags: [screener, filters, rejection, stock-selection, trend, stage-analysis, consolidation, volume, ADR, moving-averages]
created: 2026-06-17
updated: 2026-06-17
sources: 1
related:
  - concepts/Stage-Analysis.md
  - concepts/VCP.md
  - strategies/VCPBot-Trend-Template.md
  - strategies/Screener-Queries.md
  - analyses/Kalyan-Trading-Philosophy.md
---

# Image — 6 Filters Saved Me From Hundreds of Bad Charts (Haseeb Badar)

## Metadata
- **Creator:** Haseeb Badar (@hb_stocks)
- **Format:** Social media infographic series, slide 1 of 7 (only slide 1 ingested)
- **Tagline:** "Selection is an edge. Use it. Protect it. Profit from it."

> Note: This is slide 1/7 — the remaining slides (2–7) are not yet ingested. Re-ingest if the full series becomes available.

## Key Takeaways

1. **Rejection filter philosophy**: These 6 criteria are NOT entry signals. They are filters that reject charts not worth your capital. Stock selection = eliminating what is unworthy, not searching for what to buy.

2. **Funnel model**: Most charts get filtered out. Only the few that pass all 6 filters deserve attention — and even then, further entry analysis is needed.

3. **Consistency from quality selection**: "Don't search for stocks. Search with a system. Filter out the weak. Protect your capital. Focus only on the strong. Consistency comes from quality selection."

4. **ADR as minimum volatility filter** (Filter 3): A stock must have enough average daily range to cover your stop, slippage, and expected holding time. Low-ADR stocks cannot generate meaningful returns per unit of time/risk.

5. **MA alignment = trend strength confirmation** (Filter 4): Price above 20, 50, 150, AND 200 MAs simultaneously is not just a condition — it signals all timeframes aligned; institutional accumulation is ongoing.

## The 6 Rejection Filters

| # | Filter | Criteria | Wiki Cross-Reference |
|---|--------|----------|---------------------|
| 1 | **Linear Mover** | Clean moves. Higher highs, higher lows. Respect for structure. | Stage 2 uptrend definition; [Stage-Analysis](../concepts/Stage-Analysis.md) |
| 2 | **Near 52-Week High** | Strong stocks stay near highs. Supply is getting absorbed. | Trend Template condition 6 (within 25% of 52W high); [Stage-Analysis](../concepts/Stage-Analysis.md) |
| 3 | **High ADR** | Needs enough range to cover risk, slippage, and time. | New concept — see detailed note below |
| 4 | **Above Key Moving Averages** | Price above 20, 50, 150 & 200 MAs. Alignment = strength. | Trend Template conditions 1, 2, 4; [Stage-Analysis](../concepts/Stage-Analysis.md); [EMA](../concepts/EMA.md) |
| 5 | **Quality Consolidation** | Controlled base. Volume dries. Price holds levels. Tight structure. | VCP base phase; [VCP](../concepts/VCP.md) |
| 6 | **Good Volume Activity** | Strong volume on up moves. Lower volume on pullbacks. Buyers active. Sellers passive. | RVOL confirmation; [VCPBot-Trend-Template](../strategies/VCPBot-Trend-Template.md) |

## Detailed Notes

### The Rejection Filter Philosophy
The critical reframe: most traders scan for stocks to buy. Haseeb's framework inverts this. The question is not "what looks good?" but "what fails any test?" A stock that fails even one filter is rejected and not considered further. This is:
- Computationally efficient (elimination is fast; analysis is slow)
- Psychologically protective (fewer decisions = less cognitive bias)
- Portfolio-quality maximizing (only genuinely strong stocks pass all 6)

This maps directly to Kalyan's [Philosophy](../analyses/Kalyan-Trading-Philosophy.md) principle: "market always has opportunity; never FOMO" — because with a rejection system, you can wait patiently for stocks that pass all 6.

### Filter 3 — ADR (Average Daily Range)

**ADR = Average of (Daily High − Daily Low) over N days**, typically expressed as a % of price.

- Common period: 14 days or 20 days
- Typical minimum threshold: 2–3% for short-term swing trades; 1.5% for positional
- **Why it matters**: if a stock moves 0.5% per day and your stop is 3% below entry, you'd need to hold for weeks to reach a 2:1 target — inefficient use of capital and time
- **Application**: after scanning for fundamentals, filter out stocks where ATR(14)/Close < 1.5% (or 2%)
- **Screener.in formula**: `ATR 14 / Close * 100 > 2` (adds an ADR % filter to any existing screen)

ADR is closely related to ATR (Average True Range) — the difference is ADR uses High−Low only; ATR accounts for overnight gaps. In practice, for trend-following swing trades, ATR(14) % is equivalent.

### Filter Comparison to Minervini Trend Template

| Haseeb Filter | Minervini Trend Template Equivalent |
|---------------|-------------------------------------|
| Linear Mover (HH/HL) | Implicit in all 8 criteria (Stage 2 = uptrend) |
| Near 52W High | Condition 6: price within 25% of 52W high |
| High ADR | Not explicitly in Trend Template (additional filter) |
| Above 20/50/150/200 MAs | Conditions 1, 2, 4 (150>200, 50>150>200, price>50) |
| Quality Consolidation | VCP/base pattern as entry trigger |
| Good Volume Activity | RVOL confirmation + contraction during base |

**Key difference**: Haseeb adds 20 MA (very short-term) and ADR explicitly. Minervini emphasizes the 150-day and 200-day more. Combined, Haseeb's 6 filters are a simplified, visual-first implementation of the same underlying Minervini framework.

## Screener.in Implementation (Draft)

A Screener.in query capturing filters 2, 3, and 4:
```
Close > EMA 20 days AND
Close > EMA 50 days AND
Close > EMA 150 days AND
Close > EMA 200 days AND
High - Low / Close * 100 > 2 AND
Close > 0.75 * High 52 Weeks
```
Filters 1, 5, and 6 require visual chart confirmation (chart quality cannot be fully automated).

See [Screener-Queries](../strategies/Screener-Queries.md) for the full screener library.

## Actionable Insights for Kalyan

1. **Add ADR filter to existing screeners**: add `ATR 14 / Close * 100 > 2` to existing screens to eliminate low-range stocks that won't generate meaningful returns per unit of time
2. **Use as a rejection checklist before analysis**: before spending time on any stock, run the 6 filters mentally/visually in 10 seconds; if it fails any, move on
3. **Filter 5 (quality consolidation)**: confirms that your TechnoFunda-Swing and VCP-based scans already capture this — but the visual check of "does it hold levels? does volume dry up?" is done by eye, not screener
4. **Re-ingest slides 2–7**: the remaining slides likely detail each filter's specifics; source slides from @hb_stocks on X/Instagram

## Contradictions with Existing Wiki

None. This framework is a simplified, visual implementation of the Minervini Trend Template / Stage 2 criteria already in the wiki. The only genuine addition is the ADR filter (Filter 3) and the explicit "rejection filter philosophy" framing.

## Pages Updated

- Updated: [Stage-Analysis](../concepts/Stage-Analysis.md) — added cross-reference to Haseeb Badar's 6-filter framework
- Updated: [wiki/index.md](../index.md)
