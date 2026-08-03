---
title: "Article — ForexTester: Volume Analysis in Trading"
category: source
tags: [volume, tick-volume, obv, mfi, volume-profile, vsa, wyckoff, breakout-confirmation, forex]
created: 2026-08-02
updated: 2026-08-02
sources: 1
related: [concepts/Volume-Analysis, concepts/Volume-Profile, concepts/VWAP, concepts/FPV-Flow-Price-Volume-Ownership]
---

# Article — ForexTester: Volume Analysis in Trading

## Metadata
- **URL:** https://forextester.com/blog/volume-analysis-trading/
- **Publisher:** ForexTester — same vendor as [[sources/ForexTester-Anchored-VWAP-Guide]]. Prescriptive rather than empirical; the backtesting workflow it recommends runs on their product.
- **Ingested:** 2026-08-02
- **Bias:** Instructional/neutral. Carries the usual disclaimer: *"for educational purposes only and are not financial advice. Past performance does not guarantee future results."*
- **Attribution:** Names **Wyckoff** (Volume Spread Analysis) as the structured framework. No individuals, papers, or third-party studies cited.

## Key Takeaways
- **The FX volume caveat is the most important thing here.** Forex is OTC with no central exchange, so *"true volume data doesn't exist the way it does in stocks or futures."* Platforms show **tick volume** — the count of price changes per bar — which the article says correlates with real volume *"at roughly 90%+ on liquid pairs like EUR/USD and GBP/USD"*, and explicitly weaker on exotics. **A reliable proxy, not a measure.**
- **1.5× the 20-period average is the stated standard** for "above-average" volume; 2× for higher conviction. Breakouts on below-average volume are called *"likely false breakout"*.
- **Climax volume inverts the usual reading:** a spike *"500%+ above the recent average"* at resistance *"isn't necessarily bullish — it can signal a reversal"*.
- **The Volume Profile "80% rule"** is new to this wiki: if price enters the value area and holds for **two consecutive 30-minute bars**, there is a stated ~80% probability it traverses the entire VAL→VAH range.
- **No results are reported at all.** The article recommends tagging **50–100 trades** before drawing conclusions and publishes none of its own — which is more honest than publishing thirty, as its AVWAP companion piece did.

## Detailed Notes

### The price + volume matrix
| Combination | Reading |
|---|---|
| Rising price + rising volume | Strong, believable trend |
| Rising price + falling volume | Weak trend, possible reversal ahead |
| Break of resistance on **≥1.5× average** | High-probability breakout |
| Break of resistance on below-average volume | Likely false breakout |
| Volume rising on impulse legs | Trend healthy, continuation likely |
| Volume shrinking on impulse legs | Trend weakening |
| High volume at a key level | Confirmed support/resistance |
| **500%+ spike at resistance** | Climactic — reversal risk, not continuation |
| OBV/MFI lower high vs price higher high | Bearish divergence — fewer participants behind the move |
| OBV/MFI holding vs price lower low | Bullish divergence — selling drying up |

### Indicators named
**OBV** (cumulative, adds volume on up-days, subtracts on down-days) · **MFI** (volume-weighted RSI, 0–100, >80 overbought / <20 oversold) · **VWAP** (session) · **Anchored VWAP** · **Rolling VWAP** (e.g. 20 sessions) · **Volume Profile** fixed-range and visible-range (POC / VAH / VAL / HVN / LVN). No formulas are disclosed for OBV, MFI or VWAP.

### Wyckoff VSA
Reads bar **spread**, **close position within the bar**, and **volume** together:
- Wide-spread up-bar, close near the high, above-average volume → genuine buying strength.
- Narrow-spread up-bar, close mid-bar, above-average volume → potential distribution.

That second line is the useful one: identical volume, opposite implication, resolved only by where the bar closed.

### Numeric thresholds, collected
`1.5×` 20-period average (above-average) · `2×` (high conviction) · `500%+` (climactic) · `70%` (value area) · `80%` traverse probability after 2 consecutive 30-min bars in value · MFI `>80` / `<20` · tick-vs-real volume `~90%+` on liquid majors · `50–100` trades before concluding.

## Actionable Insights
1. **The tick-volume caveat applies to our crypto charts.** `HyperliquidSource` feeds the chart tool, and every volume-derived overlay we draw there — Volume Profile, OBV, AVWAP — inherits whatever that venue's volume actually represents. Worth stating on the chart rather than assuming exchange-quality volume.
2. **MFI is not implemented anywhere in this repo** and is the cheapest addition on the list: it is RSI weighted by volume, and `_rsi_series` (Wilder) already exists in `scanner_templates.py`.
3. **The 80% rule is a testable claim**, not a maxim — it names an entry condition, a target and a probability, so [[analyses/Backtest-Harness]] can measure it directly on NSE 30-min data.
4. **Our own volume thresholds are inconsistent** and this source is the prompt to reconcile them — see below.

## Contradictions with Existing Wiki

> [!note] No contradictions with the wiki — but it exposes an inconsistency in our code
> The stated standard (**≥1.5× the 20-period average** confirms a breakout) **matches `scan_*` breakout confirmation exactly** — `scanner_templates.py` lines ~1191 and ~1276 both read `vol_ratio >= 1.5` against `vol_avg_20`. Independent agreement on both the multiple and the lookback.
>
> But two other call sites in the same file disagree with those two:
> - **VCP** (`~755`): `last_vol >= 1.5 * vol50` — right multiple, **50-period** lookback.
> - **Structural breakout** (`~1032`): rejects below `vol_mult < 1.4` against the **50-DMA** — **1.4×**, neither the article's number nor our own 1.5×.
>
> Three thresholds, two lookbacks, one concept. None is *wrong*, but nothing records why they differ, which means the difference is probably accidental rather than chosen.

> [!contradiction] Apparent conflict on volume dry-up — resolved by context, worth stating
> The article: *"volume shrinking on uptrend impulse legs → trend weakening, watch for reversal."*
> Our VCP scanner (`~294`): `base_vol_ratio <= 0.7` → **"Dry-up in base"**, treated as *constructive*.
>
> These are not in conflict — they describe different places in the structure. Contraction on an **impulse leg** means demand is failing; contraction inside a **base** means supply has been exhausted and is the defining feature of a VCP ([[concepts/VCP]]). The same measurement flips meaning depending on whether price is trending or consolidating, and neither page said so until now.

## Pages Updated
- [[concepts/Volume-Analysis]] — **created**: the umbrella page this wiki lacked (tick vs real volume, the price+volume matrix, thresholds, VSA, divergence discipline)
- [[concepts/Volume-Profile]] — the 80% rule, and a link to the new umbrella page
- [[index]], [[log]]
