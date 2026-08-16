---
title: "StockEdge Trading Strategies — Major Stocks, 11 Aug 2026"
category: source
tags: [trading-strategies, screener, india-markets, stockedge, combination-scans, swing-trading, positional]
created: 2026-08-11
updated: 2026-08-11
sources: 1
related:
  - sources/StockEdge-Chart-Patterns-2026-08-11.md
  - sources/StockEdge-Markets-Dashboard-2026-08-11.md
  - concepts/Chart-Patterns.md
---

# Web Snapshot — StockEdge Trading Strategies, Major Stocks (11 Aug 2026)

## Metadata
- **Source:** https://web.stockedge.com/trading-strategies
- **Date:** 11 Aug 2026 (Tue)
- **Filter:** Major Stocks · Tue 11 Aug 2026
- **Platform description:** "predefined Combination scans segregated into specific categories" — not AI-driven
- **Update frequency:** EOD by 7 PM every trading day

---

## Key Takeaways

1. **Net 10:1 bullish signal skew** on the same day that Chart Patterns showed 10:3 bearish:bullish. 20 total bullish signals (7+10+3) vs 2 bearish. This is the forward-looking vs backward-looking resolution (see Contradiction section).

2. **Swing Bullish leads** with 10 stocks — the largest category. One Day Bullish at 7 is second. Positional (3) is thin, suggesting fewer multi-month setups qualify. Both bearish positional and one-day categories are empty (0 stocks).

3. **Bearish Strategies have near-zero representation today**: Only 2 stocks appear in Swing Bearish; all other bearish categories are zero. On a day when Nifty breadth was 13/50 (26%), the fact that bearish strategies show only 2 stocks suggests the Combination scan criteria are stricter than breadth alone.

4. **Platform architecture**: These are "Combination scans" — rule-based, multi-condition filters (not AI/pattern recognition like Chart Patterns). Individual stock names in each sub-category require authenticated navigation to sub-pages (session authentication dropped on direct URL; counts visible without Pro).

5. **No individual stock names captured** — authentication dropped when navigating to sub-pages. Only the category-level counts and descriptions were captured from the main page.

---

## Strategy Categories (11 Aug 2026, Major Stocks)

| Category | Stocks | Horizon | Description |
|----------|--------|---------|-------------|
| One Day Bullish | **7** | Next session | filters stocks having an upmove potential in the following trading session |
| One Day Bearish | **0** | Next session | filters stocks having a down move potential in the following trading session |
| Swing Bullish | **10** | Next few days | filters bullish stocks which may give momentum directional move or swing move |
| Swing Bearish | **2** | Next few days | filters bearish stocks which may give momentum directional move or swing move |
| Positional Bullish | **3** | Next few months | filters bullish stocks which may give momentum directional move or swing move |
| Positional Bearish | **0** | Next few months | filters bearish stocks which may give momentum directional move or swing move |

**Totals: 20 bullish · 2 bearish · ratio ~10:1 bullish**

---

## Contradiction with Chart Patterns (Same Day)

> [!contradiction] Bullish strategy signals vs bearish chart pattern skew (11 Aug 2026)
> [[sources/StockEdge-Chart-Patterns-2026-08-11]] showed **10 bearish : 3 bullish** patterns in the Major Stocks past list on the same day. This page shows **20 bullish : 2 bearish** strategy signals. The two engines are not in conflict — they measure different things:
> - **Chart Patterns** = backward-looking: formations that appeared days/weeks ago and are still active. A "Falling Channel" published on 20 Jul is still counted even if the stock has since rallied +18.7% (Hero MotoCorp).
> - **Trading Strategies** = forward-looking: EOD combination scans run fresh each day, selecting stocks showing multi-condition setups for tomorrow (one-day) or the next few days/months (swing/positional).
> The bearish-pattern skew reflects where the market *was*; the bullish-strategy skew reflects where the algorithm thinks it *is going*.

---

## Platform Architecture Notes

- **Two tool types on StockEdge**: Chart Patterns (AI + Human hybrid, pattern geometry detection) vs Trading Strategies (rule-based Combination scans, multi-condition filters). Distinct engines.
- **URL scheme for sub-pages**: `/trading-strategies/{category-slug}/{id}` — IDs 11–16 for the six categories (11=one-day-bullish, 12=one-day-bearish, 13=swing-bullish, 14=swing-bearish, 15=positional-bullish, 16=positional-bearish)
- **No Pro gate visible on counts** — category stock counts visible without a Pro subscription. Individual stock names may require authentication.
- **Blog reference**: http://blog.stockedge.com/ready-combination-scans/ — may document the scan logic

---

## Actionable Insights

- **Use Trading Strategies as a forward momentum filter for Chart Pattern candidates.** A stock in the Chart Patterns "Bearish" list that also appears in Swing Bullish Strategies is a divergent signal — the pattern is stale or failing. A stock in Swing Bullish Strategies that also has a Bullish Ascending Triangle in the Chart Patterns list is a converging signal.
- **Track the bullish/bearish count ratio over time.** Today's 10:1 bullish skew is striking on a day with 26% breadth. If the combination scans are genuinely forward-looking, this ratio should be predictive of breadth in 1–5 sessions.
- **Zero positional bearish on an apparent distribution day** is notable. Either the Combination scan criteria for positional bearish are very restrictive, or the market (despite intraday weakness) is not yet showing multi-month breakdown signals in Major Stocks.

---

## Pages Updated
- [[wiki/log]] — appended
- [[wiki/index]] — updated
