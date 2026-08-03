---
title: "Article — ForexTester: Breakout Trading (Definition, Strategies, Pros & Cons)"
category: source
tags: [breakout, false-breakout, retest, volume-confirmation, atr-stop, orb, squeeze, measured-move]
created: 2026-08-02
updated: 2026-08-02
sources: 1
related: [concepts/Breakout, concepts/Mean-Reversion, concepts/Volume-Analysis, strategies/Opening-Range-Breakout, concepts/Market-Structure-CHOCH-BOS]
---

# Article — ForexTester: Breakout Trading

## Metadata
- **File:** `raw/Breakout Trading_ Definition, Strategies, Pros & Cons _ FTO.html` (saved page, in the vault's immutable source folder)
- **Author / date:** Forex Tester Online Editorial Team, 26.05.2026
- **Publisher:** ForexTester — fourth ingest from this vendor. Published the same day as [[sources/ForexTester-Mean-Reversion-Guide]] and explicitly framed as its complement.
- **Bias:** Instructional/neutral, beginner-pitched (*"easy enough for beginners"*). No results published; every worked example routes into their simulator.

## Key Takeaways
- **The confirmation stack is the content**, and it is four items long: clean level → **candle close** beyond it (never a wick) → **volume confirmation** → trend filter agrees → ATR stop. Everything else is a variation.
- **Volume threshold: ≥120% of the 20-bar average** — i.e. **1.2×**. See the contradiction block; this disagrees with the same publisher's own volume article.
- **The retest is the risk-reducer:** breakout-close entry is *"fast, but more slippage"*; retest entry gives *"tighter risk and fewer false breakout signals."*
- **"Do not set the stop inside the range you just broke. That gets hit by noise."** The most portable single line in the piece.
- **Volatility contraction precedes expansion** — *"before big moves, volatility often contracts (small candles, narrow ranges)"* — which is the VCP thesis arrived at from the volatility side.
- Nine named setups: ORB · momentum · S/R · trendline · **volatility squeeze** · volume-confirmed · gap · consolidation (rect/triangle/flag) · **Fibonacci** (close beyond 61.8%, targets at 100% and 127.2%).

## Detailed Notes

### Why breakouts work, mechanically
*"Above resistance, trapped shorts buy back and new buyers join. Below support, trapped longs exit and new sellers push."* Order flow from trapped participants plus fresh entries — the same behavioural framing [[concepts/Anchored-VWAP-Pyramiding]] uses for who is above or below water.

### The three trade plans, as given
| Plan | Entry | Stop | Exit |
|---|---|---|---|
| **Breakout close** (momentum) | close above resistance **with volume** | `1.5 × ATR` below the level | 50% at `1.5R`, trail rest by `1 × ATR` |
| **Retest** (conservative) | break → pull back → level holds → small confirming candle | a few ticks beyond the retest extreme, or `1 × ATR` | first target = range height, then trail under swing structure |
| **News momentum** (fast tape) | first clean close through the level after the spike, **heavy volume only** | ATR-based, **never inside the trigger candle** | scale quickly at `1–1.5R`, then trail tight — *"these moves fade fast"* |

### Risk numbers
Stop `1–1.5 × ATR` beyond the level or retest · first target `1.5R–2R` · trail `1 × ATR` · risk `0.5–1%` of equity · measured-move target = pattern height projected from the break · squeeze variant places stops **one ATR inside the base**.

### Avoiding false breakouts
Close not tick · volume rising · prefer a held retest · ATR filter (skip tiny moves in dead volatility, don't chase spikes) · avoid high-impact news · small fixed risk. Exit rule: *"If a false breakout forms (fast close back inside the range), exit and reassess."*

### Stated failure causes
Thin volume · breaking **against the higher-timeframe trend** · major news · *"levels that were not real supply/demand"* — trade breaks from well-defined ranges, triangles and flags, **not random lines**.

## Actionable Insights
1. **Our breakout tooling is strong and our retest tooling is thin.** The scanners detect the *break*; the article's own preference is the *retest* entry, which only `scan_order_block` implements as a first-class idea.
2. **The failed-break rule is already in the repo** — `detect_structure_chain` time-boxes a failed break at *close back inside within 3 bars*, which is a mechanised form of this article's "fast close back inside the range". Worth recording that our version is stricter and countable.
3. **The squeeze setup maps onto existing pieces**: [[concepts/Bollinger-Bands-Squeeze]] plus ATR, both already computed.
4. **Volume threshold needs a decision, not another number** — see below.

## Contradictions with Existing Wiki

> [!contradiction] The same publisher gives two different volume thresholds
> **This article:** *"trade the break only if volume is ≥ 120% of the 20-bar average"* — **1.2×**, stated as a hard rule and repeated three times.
> **[[sources/ForexTester-Volume-Analysis-Guide]]** (same vendor, ingested today): *"1.5× the 20-period average"* is the standard for above-average volume, with breakouts on below-average volume called *"likely false"*.
>
> Same publisher, same month, same concept, **1.2× vs 1.5×**, both presented as the rule. Neither cites a study.
>
> **With our own code that makes four numbers for one idea:** `1.2×`/20 (this article) · `1.5×`/20 (their volume article, and our breakout scanners) · `1.5×`/50 (our VCP) · `1.4×`/50-DMA (our structural breakout). The honest conclusion is that **there is no standard volume-confirmation threshold** — it is a tunable, and every source presenting it as a constant is asserting rather than measuring. Recorded on [[concepts/Volume-Analysis]]; the way to settle it for *our* universe is a threshold sweep through [[analyses/Backtest-Harness]], not another article.

> [!note] Deliberate complement to the mean-reversion ingest — and the mirror of its gap
> Published as the counterpart to [[sources/ForexTester-Mean-Reversion-Guide]], and the two agree on the regime split: breakouts want expansion and trend, reversion wants range. Our `SCANNERS` registry is **heavily weighted to this article** — Stage 2 Uptrend, Consolidation Breakout, Structural Breakout, ATH Breakout, IPO-Base, High Tight Flag, Near Pivot, VCP, Darvas Box, Falling Wedge. That is the exact mirror of the gap recorded yesterday under [[concepts/Mean-Reversion]]: **we are well-tooled for one regime and untooled for the other**, while `classify_regime` reports both.

## Pages Updated
- [[concepts/Breakout]] — **created**: the umbrella page, mirroring [[concepts/Mean-Reversion]]
- [[concepts/Volume-Analysis]] — the 1.2× data point and the "no standard threshold" conclusion
- [[index]], [[log]]
