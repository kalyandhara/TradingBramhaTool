---
title: "TradingView — VCP Scanner (Minervini Method) by valchak"
category: source
tags: [vcp, minervini, pine-script, trend-template, scanner, rs-rating, invite-only]
created: 2026-07-06
updated: 2026-07-06
sources: 1
related:
  - concepts/VCP.md
  - strategies/Minervini-SEPA.md
  - strategies/VCPBot-Trend-Template.md
  - concepts/Stage-Analysis.md
  - concepts/Mansfield-RS.md
  - sources/Minervini-Think-Trade-Champion.md
  - sources/VCPBot-github.md
---

# TradingView — VCP Scanner (Minervini Method) by valchak

## Metadata
- **Author**: valchak
- **Type**: Pine Script v5 indicator, **invite-only** (author approval via TradingView DM)
- **URL**: https://www.tradingview.com/script/XKX8RJNc-VCP-Scanner-Minervini-Method/
- **Fetched**: 2026-07-06
- **Latest update**: May 17 — Trend Template panel expanded to full criterion names; RS Rating switched to weighted multi-period formula mirroring IBD's published methodology
- **Methodology credit**: Mark Minervini — [[sources/Minervini-Think-Trade-Champion]]

## Key Takeaways
- **Six-gate signal engine**: Trend Template ∧ VCP Valid ∧ VDU ∧ BreakingOut ∧ VolumeSurge ∧ NotExtended — all must be true on the same bar for the green BUY triangle
- **First operationalisation of Minervini's Trend Template we've seen with explicit thresholds** for what "SMA 200 slope positive" means (≥22 trading days) and what "close to 52-week high" means (within 25%) — see the [[concepts/Stage-Analysis]] "Trend Template" section
- **Contraction depth ranges are quantified**: first pullback 10–35%, final pullback 3–10%, tightening ratio ~0.9× (practical) or 0.5× (textbook-strict). This is more permissive than [[analyses/VCPBot-Architecture]] but tighter than raw Minervini
- **Anti-chase gate ("NotExtended")** is enforced at 12% above pivot by default — codifies Minervini's "do not chase more than 2–3% above pivot" as a hard filter rather than discretion
- **Two named presets** — "Practical Defaults" (US mega-cap growth: NVDA/MSFT/AVGO/PLTR style) vs "Textbook-Strict" (VDU 0.7, extension 5%, tighter ratios). Preset separation makes market-regime adaptation explicit
- **Machine-readable outputs** (Ready to Buy, VCP Valid, Trend Template, Contractions count, RS Rating) → composable with TradingView Pine Screener for universe-wide daily scans

## Detailed Notes

### Six-condition entry logic
| Gate | Meaning | Default threshold |
|------|---------|-------------------|
| Trend Template | All 8 Minervini structural criteria pass | strict AND |
| VCP Valid | 2–6 tightening contractions with valid depths | see below |
| VDU (Volume Dry-Up) | Reduced vol before breakout | ratio 1.0× (disabled by default!) |
| BreakingOut | Close above pivot (final contraction high) | 3-bar left/right confirmation |
| VolumeSurge | Breakout day volume ≥ N× 50d avg | 1.4× |
| NotExtended | Price not too far past pivot | ≤ 12% above pivot |

**Note the odd default**: VDU is *off* by default (threshold 1.0 lets everything through). Only the Textbook-Strict preset enables it at 0.7. This suggests the author found that requiring dry volume screens out too many valid US mega-cap setups where liquidity keeps volume elevated.

### Trend Template — quantified
Minervini's book states the 8 criteria but doesn't put numbers on the slope duration or "close to high" tolerance. This script commits to:
- **200-day slope positive** = uptrending ≥ 22 trading days (≈ 1 month; Minervini's book says "at least 1 month, prefer 4–5 months")
- **Price ≥ 30% above 52-week low** (Minervini's book says "≥ 25%"; valchak tightens this to 30%)
- **Price within 25% of 52-week high** — matches book exactly
- **RS threshold 70** (matches book minimum; book prefers 90s)

### VCP pattern criteria
| Parameter | valchak default | Textbook-strict |
|-----------|-----------------|-----------------|
| Contraction count | 2–6 | 2–6 |
| First contraction depth | 10–35% | 10–35% |
| Final contraction depth | 3–10% | tighter |
| Tightening ratio (each vs prior) | ≤ 0.9× | ≤ 0.5× |
| Base duration | 15–325 bars (~3–65 weeks) | same |
| Higher lows | Required | Required |
| Extension cap above pivot | 12% | 5% |
| Pivot confirmation bars (L/R) | 3 | 5 |

**Comparison with [[analyses/VCPBot-Architecture]]** (our internal 3-tier detection): VCPBot requires ≥30% prior advance and ≥15% initial pullback as macro anchors — valchak's script has no equivalent "left-side-high" precondition. It relies purely on the Trend Template gate to confirm the stock is in a proper Stage 2.

### RS Rating methodology
Weighted 12-month excess return vs benchmark (default `SP:SPX`):
- 40% weight on most recent quarter
- 20% each on quarters 2, 3, 4

This is explicitly a **proxy** for IBD's proprietary RS Rating. Mirrors the published IBD approach but not identical. See [[concepts/Mansfield-RS]] for another RS methodology used in this wiki.

### Visual output
- SMA 50 (blue) / SMA 150 (orange) / SMA 200 (red) — the trend template stack
- **Cyan pivot line** at breakout level (final contraction high)
- **Red stop-loss line** below final contraction low
- Translucent blue box outlining the detected base
- T1/T2/T3 labels with contraction depth %
- Top-right status panel with Trend Template pass/fail states

### Workflow the script enables
1. **Universe scan** — TradingView Pine Screener with filters "VCP Valid = 1" and optionally "Trend Template = 1" produces the daily candidate list
2. **Monitor candidates** — three approaches:
   - Morning visual scan of the candidate universe
   - TV price alerts on the cyan pivot line
   - "VCP Pivot Approached" alert (±2% of pivot)
3. **Signal fires** — green BUY triangle when all 6 gates align intraday
4. **Manual confirmation** — verify SPX/QQQ uptrend, extension, size to 1.25–2.5% risk

## Actionable Insights

### 1. Numeric commitments update [[concepts/VCP]]
Our VCP page borrows book-level guidance. valchak's numeric ranges (first contraction 10–35%, final 3–10%, tightening ~0.9×) are worth pinning as a **second reference implementation** alongside the VCPBot 3-tier detection. They will differ — that's the point.

### 2. NotExtended as a first-class gate
Our internal detection lacks an anti-chase filter as a discrete gate. Consider adding "extension above pivot > 12% → skip" as a separate rejection reason (currently we handle this loosely via the gap-check at open). Update [[strategies/VCPBot-Trend-Template]] entry rules to log this rejection code.

### 3. Preset separation is a good pattern
The Practical/Textbook split is exactly the kind of regime-adaptation pattern we should adopt in our Scanner Hub. Consider adding a "strict/lenient" preset switch to `scan_vcp()` in `tools/scanner_templates.py` — strict mode is the archival "does this still work in ranges" test, lenient is the "am I missing the current cohort" test.

### 4. RS proxy formula worth cloning
The 40/20/20/20 quarter-weighted excess return is a cheap, well-known IBD proxy. Our current RS Rating comes from an internal function — worth adding this weighted variant as a second RS column so we can compare regimes where recent momentum matters more (40%-weighted) vs where 12-month steady leadership matters (equal-weighted).

### 5. Invite-only access is the friction
The script is invite-only — we cannot pull the actual Pine source. We have the criteria and defaults from the published description, but not the exact tightening-ratio calculation or the pivot-confirmation logic. If we ever get access, extract the Pine and add it under `tools/pine_scripts/vcp-scanner-minervini-valchak.pine`.

## Contradictions with Existing Wiki

> [!contradiction] Trend Template — 25% vs 30% above 52-week low
> [[sources/Minervini-Think-Trade-Champion]] and our [[strategies/Minervini-SEPA]] page state criterion 5 as "**≥25%** above 52-week low". valchak's script defaults to **≥30%**.
> Resolution: the book value is the source of truth; valchak's 30% is a discretionary tightening. Note both values on the Trend Template page and mark the strict variant as "valchak default".

> [!contradiction] Pivot confirmation vs immediate breakout
> Minervini's book teaches acting on the breakout intraday when volume confirms. valchak's script requires 3 bars left/right of pivot confirmation *before* the pivot is even drawn on the chart. This is safer (avoids fake pivots) but structurally later than the book teaching.
> Resolution: this is a *scanner* design choice, not a doctrine change — the scanner is showing you completed bases, not signaling on breakout candles. Signal timing is separate from base validity.

## Pages Updated
- Created: [[sources/TV-VCP-Scanner-Minervini-valchak]] (this page)
- Updated: [[concepts/VCP]] — added valchak numeric preset table
- Updated: [[strategies/Minervini-SEPA]] — cross-referenced as Pine-scanner implementation
- Updated: [[wiki/index]], [[wiki/log]]
