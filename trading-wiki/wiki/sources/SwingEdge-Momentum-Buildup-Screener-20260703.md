---
title: "SwingEdge — Momentum Buildup Screener (HTF / Active / Fresh Turnaround, 2026-07-03)"
category: source
tags: [swingedge, momentum-buildup, high-tight-flag, active-breakout, fresh-turnaround, screener, volume-confirmation]
created: 2026-07-03
updated: 2026-07-03
sources: 1
related: [concepts/High-Tight-Flag, concepts/VCP, concepts/Stage-Analysis, strategies/Minervini-SEPA, entities/IOLCP, sources/SwingEdge-EPIGRAL-20260703]
---

# SwingEdge — Momentum Buildup Screener

## Metadata
- URL: https://www.swingedge.info/momentum-buildup
- Scan data dated: 2026-07-03 20:47 IST (last daily close, not live)
- Fetched: 2026-07-03 via Playwright (site 403s plain fetches)
- Scope: screener *methodology* page + live scan results (30 qualifiers, 10 focus setups, 3 visible without login)

## Key Takeaways
1. **Three buildup tags, all "first clear" structures** (deliberately earlier-stage than the Momentum Continuation scan's mid-trend pauses):
   - **High Tight Flag**: 90–120% pole in 4–8 weeks, then a 10–25% tight flag on contracting volume — "the momentum pattern of new market leaders."
   - **Active Breakout**: first clear out of a 5–15 week base on **1.5×+ volume** — "the classic Stage 2 launch point."
   - **Fresh Turnaround Breakout**: early reversal clear after a downtrend/base repair, volume-confirmed — SwingEdge's counterpart to this repo's Early Reversal Detector.
2. **Volume confirmation is a hard rule, not decoration**: every tagged row is checked against the 50-day average; low-volume clears are scored *down*; the "Vol ×50d" column shows signal-day participation.
3. **Two-axis card verdicts** — actionability status separate from quality grade: "**At trigger**" (tooltip: "RS, volume, pivot distance, event risk and age all pass") vs "**Watch**" ("pivot distance is not in the preferred action zone"), crossed with **Quality A** ("high-quality setup — trade quality, not just momentum") / **Quality B** ("workable"). Same two-axis idea as the earlier KDDL ingest's setup-readiness vs decision-quality split, now on scan cards.
4. **Recommended workflow**: filter Strong + Vol Confirmed (+ Leading RS) → bucket by pattern (HTF / Active BO / Fresh Turnaround) → confirm on the chart with pivot + T1/T2 projections → apply your own risk framework → cross-watch the Downside Risk scan for the bearish side of the same model.
5. **Live scan (2026-07-03)**: focus top-3 = ATHERENERG (score 100, Vol 0.8×), ZYDUSWELL (98, 1.4×), WABAG (95, 2.1×) — all "At trigger · Active Breakout". Visible cards: ARVIND (At trigger, Quality A, RS 100, vol quality 82), **IOLCP** (Watch, Quality B, RS 100, vol quality 79), SMSPHARMA (Watch, Quality B, RS 83, vol quality 90). Proof-of-follow-through strip: SATIN +8% (since 29 Jun), OFSS +7.4% (24 Jun), ATHERENERG +4.3% (29 Jun).

## Detailed Notes
- Scan cadence: daily; same underlying scan feeds Momentum Continuation (mid-trend) and this page (early-stage) — the tags partition by structure age.
- Card reason lines are check-style ("✔ RS 100 — strong relative strength / ✔ Volume quality 82 / ✔ Active breakout — price cleared pivot with participation") — same pattern as this repo's scanner cards.
- Educational sidebar links: VCP, Stage 2 (Weinstein), RS rank, "Spotting accumulation" (tight flags, volume dry-up, quiet trade into pivots).
- Pre-built scanner roster visible in nav (for coverage comparison with our Scanner Hub): Custom, SEI, Base Formation, Momentum Continuation, Momentum Buildup, Early Momentum, Downside Risk, Darvas Box, **Structural Breakout**, **Rounding Bottom**, ETF Leaders + focus screens (Near Pivot, VCP Coiling, Pullback Entry, 52-Week High Leaders, Stage 2, High RS, Volume Surge). Structural Breakout and Rounding Bottom are the two we don't have an analog for.

## Contradictions with Existing Wiki / Internal Inconsistencies
- **Focus #1 vs its own volume rule**: ATHERENERG ranks #1 with score 100 at **Vol 0.8×** while the page states low-volume clears are scored down and Active Breakout "requires volume participation." Either the tag was earned on an earlier signal day or the focus ranking ignores the volume gate — treat focus rank with the same "trust fields, not prose" skepticism flagged on [[sources/SwingEdge-EPIGRAL-20260703]].
- HTF pole spec here (90–120% in 4–8 weeks) is the strict O'Neil/textbook definition; [[strategies/Minervini-SEPA]] treats HTF as rare and frequently failure-prone when loosely defined — no conflict, but the strictness is the point: dilute the parameters and the pattern's edge dilutes with them.

## Actionable Insights
- **Adopted (2026-07-03)**: `scan_high_tight_flag()` added to `tools/scanner_templates.py` Scanner Hub using this page's parameters (≥90% pole within ≤8 weeks, 10–25% flag on contracting volume, near/at flag breakout scored higher). Fresh Turnaround Breakout needs no port — the Early Reversal Detector + 9-check validation layer already covers it with more machinery.
- **Card-verdict design worth copying** when the Confirm-Before-Entry doctrine gets built into cards: status (At trigger / Watch) and quality (A/B) as *separate* axes, with the blocking reason named ("pivot distance not in preferred action zone") instead of a bare score.
- [[entities/IOLCP]] follow-through: wiki flagged it "breakout soon on volume buildup" 2026-06-14 (FinanceWithSunil); today it prints Active Breakout / Stage 2 / RS 100 / Quality B (Watch — extended from pivot). Entity page updated; chase-risk applies, pullback entry preferred.

## Pages Updated
- [[concepts/High-Tight-Flag]] — created (first dedicated HTF page)
- [[entities/IOLCP]] — 2026-07-03 scan appearance + status recorded
- `tools/scanner_templates.py` — `scan_high_tight_flag()` (code, not wiki)
- index.md, log.md
