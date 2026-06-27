---
title: "SwingEdge — Position Sizing Calculator Tool"
category: source
tags: [position-sizing, risk-management, fixed-fractional, r-multiple, gap-risk, swing-trading]
created: 2026-06-22
updated: 2026-06-22
sources: 1
related: [concepts/Kelly-Criterion, concepts/Capital-Management-Methods, sources/SwingEdge-KDDL-20260621, sources/SwingEdge-NRBBEARING-20260621, sources/SwingEdge-AADHARHFC-20260621]
---

# Source — SwingEdge.info Position Sizing Calculator

## Metadata
- **Source type**: Generic calculator tool page (not a stock detail page), same site as the prior 3 SwingEdge stock ingests
- **URL requested**: https://www.swingedge.info/tools/position-sizing?symbol=CGPOWER
- **Canonical URL**: https://www.swingedge.info/tools/position-sizing (the `?symbol=` param only pre-fills the stock-search box; it does not change the page's content)
- **Fetch date**: 2026-06-22

## Important caveat on this fetch
**No CGPOWER-specific data was captured.** The page's entry/stop fields showed generic placeholder defaults (Entry ₹100, Stop ₹90, Capital ₹10,00,000) rather than CGPOWER's actual price or scanner levels. The real per-symbol scanner context (entry/stop/ATR auto-fill) loads via a client-side JS API call after page render — invisible to a static `curl` fetch, unlike the stock detail pages (KDDL/NRBBEARING/AADHARHFC) which embed their data server-side in the initial HTML. To get CGPOWER's specific position-sizing output, either render the page in a browser, or just ingest `https://www.swingedge.info/stocks/CGPOWER` instead (the stock detail page format used for the prior 3 ingests) and run the sizing math manually using the formulas below.

This is therefore filed as a **methodology/tool source**, not a CGPOWER entity update.

## Key Takeaways
- The tool implements straightforward **fixed-fractional position sizing**: shares = (capital × risk%) ÷ (entry − stop), capped by a max-allocation-per-trade limit — directly maps to this wiki's existing [[concepts/Capital-Management-Methods]] page (which already documents Kelly/Optimal-f/Martingale/Fixed-Proportional approaches) and [[concepts/Kelly-Criterion]] (half-Kelly practical default, Minervini's 1.25–2.5% rule).
- **Default risk per trade: 0.5% of capital** (range allowed 0.1%–5%), with explicit guidance: "0.25%–1% ... 0.5% a common default on a ₹10L swing book (₹5,000 at risk). Lower risk (0.25%) suits uncertain or bearish environments." This is a concrete, named default worth comparing against whatever sizing rule is currently in this wiki's trading philosophy/strategy pages.
- **Default max allocation per trade: 20% of capital** — a hard cap on position concentration independent of the risk-per-trade calc, so a very tight stop doesn't let one name dominate the portfolio.
- **Gap-risk simulation**: models a worse fill than the stop limit (default gap buffer 5%, slippage 0.5%) to estimate real loss in ₹ and in R-multiples if a stop doesn't fill cleanly overnight — explicitly flagged as a smallcap/illiquid-name risk on NSE/BSE. This is a useful, underused concept not yet in this wiki's risk-management pages: a "stop-loss-doesn't-guarantee-fill" stress test.
- **R-multiple framework**: 1R = planned loss if stop hits; targets shown at +1R/+2R/+3R. Six selectable exit styles: Fixed R:R (50% at +2R, trail rest), Partial at +1R, Trailing ATR (1.5× ATR below highs), Swing low trail, EMA trail (below 20 EMA), Pyramid mode (adds only after +1R). The pyramid-mode option is conceptually close to this wiki's [[concepts/Kelly-Criterion]] multi-position scaling and the "wash-and-reclaim adds" pyramiding pattern already noted from David Hannan's interview (sources/YT-David-Hannan-Laptop-Legend.md).
- A composite **"Position readiness" score** (0–100) is computed from "volatility, stop distance, scanner setup quality and liquidity" — i.e. the position-sizing tool reuses the same setup-quality scoring infrastructure seen on the stock detail pages (KDDL/NRBBEARING/AADHARHFC), rather than being a purely independent calculator.
- Footer discloses Swing Edge's data sourcing: price feed from NSE/BSE, value-added by Accord Fintech; explicit "not registered with SEBI as a Research Analyst or Investment Adviser" disclaimer.

## Detailed Notes

**Default form values observed**: Entry ₹100, Stop ₹90 (10% stop distance — generic placeholder, not derived from CGPOWER), Capital ₹10,00,000, Risk per trade 0.5%, Max allocation 20%, Exit style "Fixed R:R — 50% at +2R, trail rest" (the default selection), Gap buffer 5%, Slippage 0.5% (both under an "Advanced" toggle, hidden by default).

**Educational copy embedded on the page** (useful as a clean, quotable risk-management primer):
- "Position sizing is ... not about conviction — it is about math. You decide the maximum loss you can accept (often expressed as 1R), divide that by your risk per share (entry minus stop), and that yields share count."
- "Most blow-ups are not bad entries — they are oversized positions ... one gap-down or one oversized name can erase months of gains."
- "Fixed fractional sizing means you risk the same fraction of capital on each trade ... so position size in shares automatically shrinks when the stop is wider and grows when the stop is tighter — within your allocation cap."

## Actionable Insights
- The fixed-fractional formula and 0.5%-default/20%-cap pairing is a concrete, reusable reference point — worth comparing against this wiki's existing Kelly/half-Kelly guidance to see whether 0.5% fixed-fractional is more conservative or more aggressive than what's already documented for this portfolio.
- The **gap-risk simulation** concept (worse-fill-than-stop stress test) is not yet represented anywhere in this wiki's risk-management content and is worth adding as a line item to [[concepts/Capital-Management-Methods]] or a new dedicated note, since it's a distinct failure mode from ordinary stop-loss sizing.
- If CGPOWER-specific sizing output is actually wanted, re-fetch `https://www.swingedge.info/stocks/CGPOWER` (the stock detail page) for entry/stop/ATR scanner levels, then apply this tool's formula manually, or use a browser-rendering fetch instead of `curl` for the position-sizing URL itself.

## Update 2026-06-22 — scanner context card explained
The original ingest of this tool's page (`?symbol=CGPOWER`) couldn't capture any symbol-specific data because the scanner context loads via client-side JS. The companion "How to use the Swing Edge position sizing calculator" lesson (`/learn/position-sizing-calculator-guide`, part of [[sources/SwingEdge-Learn-Process-Risk-Workflow]]'s catalog) describes exactly what that card shows once it loads:
- A **trade quality score** — the share of quality checks passed, explicitly "not a buy rating." Green checks list what the scanner liked; grey dots are checks that didn't pass.
- Pills summarizing **sector RS, liquidity tier, volume ratio vs. 50-day average**, and a **sizing hint** (e.g. "full 0.5% risk" vs. "size down").
- Bearish-scanner names show an explicit warning that long-side sizing is "planning only."
- When ATR is available, the tool may suggest a stop near `entry − 1.5×ATR`.
- Best workflow: open the calculator directly from a stock's detail page via "Plan position size" or "Plan this trade" — entry/stop/ATR auto-fill from that stock's latest scanner row. This only works for names with saved scanner levels (Pre-Breakout, Active Breakouts, etc.), not for a generic chart-only lookup.

This means a future re-ingest of any `/tools/position-sizing?symbol=X` page would still need a browser-rendered fetch to see X's actual numbers — but the *meaning* of every field on that card is now documented here regardless.

## Contradictions with Existing Wiki
- None identified — this is additive risk-management methodology, complementary to existing Kelly/Capital-Management content rather than conflicting with it.

## Pages Updated
- This source page (no entity page created — no company-specific data was captured)
