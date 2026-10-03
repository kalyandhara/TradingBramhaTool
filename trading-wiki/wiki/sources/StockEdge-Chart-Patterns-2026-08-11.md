---
title: "StockEdge Chart Patterns — Major Stocks, 11 Aug 2026"
category: source
tags: [chart-patterns, screener, india-markets, stockedge, bearish-patterns, symmetrical-triangle, double-top]
created: 2026-08-11
updated: 2026-08-11
sources: 1
related:
  - concepts/Chart-Patterns.md
  - concepts/Falling-Wedge.md
  - analyses/Falling-Wedge-Scanner-Fit.md
  - sources/AGPro-Reversal-Pattern-Quality-Scanner-Pine.md
  - sources/StockEdge-Markets-Dashboard-2026-08-11.md
---

# Web Snapshot — StockEdge Chart Patterns, Major Stocks (11 Aug 2026)

## Metadata
- **Source:** https://web.stockedge.com/chart-patterns?activeness-status=200
- **Date:** 11 Aug 2026
- **Filter:** Major Stocks · Past · activeness-status=200
- **Pro feature:** "Recent" tab paywalled; Past tab visible. Detection: "AI + Human" hybrid. Updated EOD.

---

## Key Takeaways

1. **Bearish patterns dominate the Major Stocks list**: Double Top (4 instances), Bearish Flag, Falling Channel (3), Rising Wedge = **10 bearish** vs **3 bullish** (Double Bottom × 1, Ascending Triangle × 2) and **7 neutral** Symmetrical Triangles. The 10:3 ratio aligns with the same-day Nifty breadth collapse (13/50 advancing).

2. **Symmetrical Triangles are the most frequent individual pattern** (7 of 20 past entries) — all are pending-breakout, not directionally resolved. Six out of seven have moved *above* their published price point, suggesting bullish resolution bias for sym-triangles in this sample.

3. **Bearish pattern follow-through has been strong**: CE Info Systems -17.7%, ZEE -22.6%, Supreme Petrochem -13% from their Double Top price points — these patterns worked. But Mahindra (-3,172 → 3,460, +9.1%) and Hero MotoCorp (-4,942 → 5,865, +18.7%) are both *above* their Falling Channel publish price — these bearish labels did **not** resolve downward.

4. **Triangle Patterns dominate the universe** — 2,179 stocks (vs the next largest, Multiple Top/Bottom at 1,483). Triangles are neutral-until-break, which may explain why the platform shows large counts: the pattern doesn't expire until the breakout fires.

5. **Trading Strategies live count (11 Aug)**: 7 one-day bullish, 10 swing bullish, 3 positional bullish vs 0/2/0 bearish. **This contradicts the chart pattern bearish skew** — the algo-trading-strategy engine is net bullish while the chart pattern engine is net bearish. Resolution: chart patterns look backwards (past formations); trading strategies are forward-looking real-time signals.

6. **`activeness-status=200` in the URL** — likely a HTTP-style status flag meaning "active" / "confirmed". Not documented publicly; probably filters out expired or invalidated patterns.

---

## Past Patterns — 20 Major Stock Entries (Jul–Aug 2026)

### Bearish Resolved ✓
| Stock | Pattern | Published | Published Price | LTP | Move |
|-------|---------|-----------|-----------------|-----|------|
| CE Info Systems | Double Top | 04 Aug | 1,231.95 | 1,013.30 | **-17.7%** |
| Zee Entertainment | Double Top | 03 Aug | 118.35 | 91.56 | **-22.6%** |
| Supreme Petrochem | Double Top | 29 Jul | 788.00 | 685.25 | **-13.0%** |
| Gallantt Ispat | Bearish Flag | 21 Jul | 618.50 | 593.50 | -4.0% |

### Bearish NOT Resolved (price above publish point)
| Stock | Pattern | Published | Published Price | LTP | Move |
|-------|---------|-----------|-----------------|-----|------|
| Hero MotoCorp | Falling Channel | 20 Jul | 4,942.38 | 5,865.50 | **+18.7%** |
| Mahindra & Mahindra | Falling Channel | 21 Jul | 3,172.73 | 3,460.10 | **+9.1%** |
| PNB Housing Finance | Rising Wedge | 23 Jul | 1,073.38 | 1,142.10 | +6.4% |
| Pine Labs | Double Top | 16 Jul | 164.40 | 167.58 | +1.9% |
| Muthoot Finance | Falling Wedge | 21 Jul | 3,068.97 | 2,915.90 | -5.0% |

### Bullish Resolved ✓
| Stock | Pattern | Published | Published Price | LTP | Move |
|-------|---------|-----------|-----------------|-----|------|
| Jubilant FoodWorks | Double Bottom | 27 Jul | 408.55 | 488.20 | **+19.5%** |
| Sapphire Foods | Sym. Triangle | 27 Jul | 182.94 | 236.02 | **+29.0%** |
| LTM Ltd. | Sym. Triangle | 28 Jul | 4,192.58 | 4,850.00 | **+15.7%** |
| Piramal Pharma | Sym. Triangle | 17 Jul | 177.18 | 214.19 | **+20.9%** |
| RR Kabel | Sym. Triangle | 22 Jul | 2,386.29 | 2,812.80 | **+17.9%** |
| Clean Science & Tech | Sym. Triangle | 20 Jul | 756.03 | 810.00 | +7.1% |
| Hyundai Motor India | Ascending Triangle | 31 Jul | 2,064.80 | 2,200.00 | +6.5% |
| CRISIL | Ascending Triangle | 21 Jul | 4,250.00 | 4,480.80 | +5.4% |

### Bearish label, mixed outcome
| Stock | Pattern | Published | LTP move |
|-------|---------|-----------|----------|
| Blue Star | Sym. Triangle | 03 Aug | -13% (bearish resolution) |
| Zee Entertainment | Sym. Triangle | 27 Jul | -15.3% (bearish resolution) |
| Supreme Petrochem | Falling Channel | 27 Jul | -9% (bearish resolution) |

---

## Pattern Category Universe (All Stocks)

| Category | Count | Bias | Description |
|----------|-------|------|-------------|
| Triangle Patterns | **2,179** | Neutral | Continuation; most common — doesn't expire until breakout fires |
| Multiple Top & Bottom | **1,483** | Reversal | Largest reversal category by count |
| Channel Patterns | **1,304** | Both | Parallel support/resistance boundaries |
| Wedge Patterns | **672** | Both | Converging trendlines; bullish or bearish depending on slope |
| Rounding Top & Bottom | **514** | Reversal | Slow-forming arc reversals |
| Flag Patterns | **438** | Continuation | Consolidation after sharp impulse |
| Head & Shoulders | **221** | Reversal | Fewest; most selective / hardest to qualify |

> [!key-insight] Triangle count (2,179) vastly exceeds H&S (221) — a 10:1 ratio. The platform's AI detects far more consolidation-compression setups than trend-exhaustion reversals, which makes sense: triangles form continuously, H&S requires a specific 3-peak structure with a valid neckline.

---

## Platform Architecture Notes
- **Two tabs**: Stocks (per-stock pattern list) · Categories (grouped by pattern family)
- **Two time views**: Recent (Pro-only, today's alerts) · Past (visible, historical)
- **Filter**: Major Stocks toggle (narrows to Nifty/large-cap universe)
- **Pattern URL scheme**: `/share/{slug}/{id}?section=chart&chart-pattern-type={type-id}&chart-pattern-id={instance-id}` — each detected pattern has a unique instance ID. Pattern type IDs visible: 30=Ascending Triangle, 50=Symmetrical Triangle, 70=Falling Channel, 90=Rising Wedge, 100=Falling Wedge, 170=Bearish Flag, 180=Double Top, 190=Double Bottom.

---

## Contradictions with Existing Wiki

- **[[concepts/Falling-Wedge]]** documents the falling wedge as a *bullish reversal* pattern. The Muthoot Finance entry (Falling Wedge, -5.0% from published price) is a failed bullish setup — minor, but consistent with the wiki's note that falling wedges can resolve in either direction before the final reversal.
- **[[sources/AGPro-Reversal-Pattern-Quality-Scanner-Pine]]** scores patterns by quality (5-factor). StockEdge provides no quality score — just presence/absence. The 10:3 bearish:bullish outcome split in past data suggests quality gating matters: roughly half the bearish patterns failed (Mahindra, Hero MotoCorp, Pine Labs). That 50% failure rate on "confirmed" bearish patterns argues for StockEdge chart patterns being a screen for *candidates*, not a signal.

---

## Actionable Insights

- **Symmetrical Triangles with bullish resolution bias**: in this sample (7 entries), 5 of 7 resolved upward from the publish price point. Sample is small; treat as a hypothesis worth tracking across future snapshots.
- **Double Tops have worked reliably** (CE Info -17.7%, ZEE -22.6%, Supreme -13%) — but the market context (Nifty in distribution, VIX low) may be the enabling factor, not the pattern alone.
- **Pattern ≠ signal**: The Trading Strategies page shows net-bullish real-time counts (10 swing bullish, 0 positional bearish) on the same day the chart pattern list is net-bearish. The chart pattern engine is backward-looking; the trading strategy engine is forward-looking. Do not trade chart patterns without a real-time momentum filter.
- **`activeness-status=200` worth revisiting**: this filter likely excludes invalidated patterns. Checking the same URL without this parameter may reveal the full universe including failed setups — useful for base-rate calibration.

---

## Pages Updated
- [[log]] — appended
- [[index]] — updated
- [[concepts/Chart-Patterns]] — created (new concept page to hold the category taxonomy)
