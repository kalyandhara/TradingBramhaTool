---
title: "Pine Script — Structure Break Chain [SBC] (SharpStrat)"
category: source
tags: [pine-script, smc, bos, choch, market-structure, break-quality, failed-breakout, chain-count, atr, tradingview, sharpstrat]
created: 2026-07-29
updated: 2026-07-29
sources: 1
related:
  - concepts/Market-Structure-CHOCH-BOS.md
  - sources/LuxAlgo-Smart-Money-Concepts-Pine.md
  - sources/BOS-FVG-Pullback-Signals-Pine.md
  - concepts/Order-Blocks.md
  - analyses/Backtest-Harness.md
  - analyses/Dashboard-UI-Roadmap.md
---

# Pine Script — Structure Break Chain [SBC]

## Metadata
- Author: © SharpStrat (TradingView)
- License: **Mozilla Public License 2.0** — permissive; a port is fine **with attribution**
  (contrast [[sources/LuxAlgo-Smart-Money-Concepts-Pine]], which is CC BY-NC-SA / non-commercial)
- Format: Pine Script **v6** indicator, `overlay=true`, `max_labels_count=500`,
  `max_lines_count=500`, `max_boxes_count=200`
- Ingested: 2026-07-29 (pasted source code)

> [!warning] The paste is **truncated** — inputs promise more than the code shows
> The code ends mid-way through the chain-counter block (`lc = trend == 1 ? …`). Present as
> *declared inputs* but **absent from the pasted body**: the **dashboard panel**
> (`i_show_dash`, `i_dash_pos`), the **pullback entry zones** (`i_show_zones`,
> `i_zone_ext`), the **HTF structure overlay** (`i_htf_on`, `i_htf_tf`, `i_htf_alpha`),
> **trend background shading** (`i_show_bg`), and **all `alertcondition`/`alert()` calls**
> (`i_alrt_strong`, `i_milestone`). Everything documented below as mechanics is from code I
> actually read; the missing pieces are noted as intent-only. Paste the tail if the zones or
> the dashboard matter.

## Naming caution — this is **not** our "Structural Breakout"
The request called it a "structural breakout indicator," and we already ship a scanner named
**Structural Breakout** (`scan_structural_breakout`, [scanner_templates.py](tools/scanner_templates.py)
— a multi-week *horizontal resistance* base breakout from the SwingEdge ingest). SBC is a
different animal: **swing-structure BOS/CHoCH labelling with a continuation chain counter**.
Keep the names distinct — conflating them would put an SMC structure walk and a base-breakout
scanner behind one label.

## Key Takeaways
1. **The chain counter is the script's actual idea.** `chain_cnt` counts **consecutive
   same-direction breaks since the last CHoCH**: a CHoCH resets it to 1, each subsequent BOS
   in that direction increments it. A long chain = structurally persistent trend; the reset
   *is* the character change. Nothing in our stack measures this today — we detect the latest
   event, never the run length.
2. **Break quality, ATR-normalised, in three lines.** `f_qual(dist)` scores each break as
   `0.6 × (dist ÷ ATR14) + 0.4 × (|close − open| ÷ ATR14)` → **STRONG ≥ 0.75 · NORMAL ≥ 0.35 ·
   WEAK** otherwise. So quality = 60% *how far beyond the level* price closed + 40% *how
   decisive the breaking candle's body was*, both in ATR units — symbol-agnostic and free.
3. **Failed-BOS detection is explicit and time-boxed.** Every break arms a watch
   (`fail_lvl`/`fail_dir`/`fail_time`); if price **closes back inside** the broken level within
   `i_fail_win` bars (default 3) → `✗ FAILED`. Two details: the failure test always uses
   **close** even when breaks are wick-confirmed, and `elapsed > 0` means it cannot fire on the
   break bar itself. `i_fail_win = 0` silently disables the whole check.
4. **Break confirmation is a user choice.** `i_confirm` switches the comparison series between
   `close` (wait for the close beyond the level) and `high`/`low` (wick — "faster, noisier").
   Our port hard-codes close; this is a real knob we don't expose.
5. **Pivot length 15, not 5.** `ta.pivothigh(high, 15, 15)` — far coarser than our
   `detect_bos_choch(pivot_len=5)` and LuxAlgo's internal tier, closer to LuxAlgo's 50-bar
   *swing* tier. Pivots confirm 15 bars late, and the script back-dates them
   (`sh_bar = bar_index - i_pivot_len`) rather than pretending they were known live.
6. **BOS/CHoCH rule is the community standard — a third independent confirmation.** Trend
   state at break time decides the label (bear trend + up break = CHoCH and flip; already
   bullish = BOS), then the level is **consumed** (`sh := na`) until a fresh pivot forms.
   Identical to LuxAlgo and to our own port — [[concepts/Market-Structure-CHOCH-BOS]]'s rule
   is now triple-sourced.
7. **Quality is encoded as *opacity*, not text.** Label transparency is keyed to the grade
   (STRONG = 0, NORMAL = 28, WEAK = 60) so weak breaks visually recede. A cheap presentation
   idea that transfers to our chart overlays.

## Detailed Notes
- **State machine (per bar, in order):** pivot update → bullish break test → bearish break test
  (guarded by `and not (bos_up or choch_up)` → **one structural event per bar, bull wins ties**)
  → failed-BOS check (skipped on any bar that produced a new event) → statistics → drawing.
- **Statistics:** `tot_bos`, `tot_choch`, `max_chain`, and a completed-chain average built from
  `n_chains`/`sum_chains`, accumulated **only at CHoCH** using `chain0` (the chain length
  captured *before* this bar's mutation). So the average deliberately excludes the in-progress
  chain — an honest choice, and the reason `chain0` is snapshotted globally each bar.
- **ATR** is `ta.atr(14)` floored at 0.001 (`math.max(nz(...), 0.001)`) — guards flat/illiquid
  series. Our `_atr_series` is the same Wilder/RMA smoothing, so no new math to port.
- **Swing lines** are drawn for *every* confirmed pivot (dashed, from pivot bar to current bar),
  independent of whether it was ever broken.
- **Label offsets** scale with ATR: BOS at 0.7 × ATR from the bar's low/high, CHoCH at 1.6 ×,
  FAILED at 2.4 × — stacking rule, so co-located labels don't overlap.
- **`prev_sh`/`prev_sl` are tracked and stored** (`bos_prev`) but never used in the pasted code —
  presumably feeding the truncated pullback-zone logic (the prior swing is the natural zone
  boundary).
- Chain bubble redraws only on `barstate.islast` (delete-and-recreate) — a live readout, not
  history.

## Actionable Insights
Grounded against our code (`detect_bos_choch`, [scanner_templates.py](tools/scanner_templates.py)
line 2084): our detector walks the **same** structure rule but returns only
`{signal, level, bars_ago}`, bullish-only, close-confirmed, `pivot_len=5`. It has **no quality
grade, no chain count, and no fast-failure flag** — precisely SBC's three contributions. Three
consumers depend on the current return shape (the SMC checklist's Structure check, `scan_order_block`,
and a `BOS/CHOCH` tag), so **additive keys are backward-compatible**.

- **SBC-1 — enrich `detect_bos_choch` (additive, low risk).** Add `quality` (STRONG/NORMAL/WEAK
  + the raw 0.6/0.4 score), `chain` (consecutive same-direction breaks since the last CHoCH),
  `failed` + `failed_bars` (close back inside within N bars), and `direction`; expose
  `confirm="close"|"wick"` and keep `pivot_len` configurable. Reuses `_atr_series`; no new
  dependency, no new data.
- **SBC-2 — spend the new fields where they change decisions.** Gate the SMC checklist's
  Structure check on `quality != "WEAK"`; feed `chain` into `setup_intelligence` as a
  trend-persistence factor; surface `failed` as a **fail-risk chip** (the scanner cards already
  carry a fail-risk flag row, `scanner_templates.py` ~line 895). A failed break is exactly the
  "structural caution" that row exists for.
- **SBC-3 — measure it, don't assume it (the decisive step).** [[analyses/Backtest-Harness]]
  measured **Structural Breakout at ≤0 forward edge**, and `scan_order_block` (+0.11R) consumes
  `detect_bos_choch` directly. So the honest question is whether *quality ≠ WEAK* or *chain ≥ N*
  actually improves those two. Cheap to test — the detector is already inside the scanner path,
  and both filters are one boolean each.
- **SBC-4 — chart overlay.** ✅ **SHIPPED 2026-07-29** (out of sequence — the user asked for the
  chart first). `detect_structure_chain()` in [scanner_templates.py](tools/scanner_templates.py)
  walks the full series and returns every event with quality/chain/failed (`detect_bos_choch` left
  untouched, so no consumer moved); `/api/structure_chain` on [chart_server.py](tools/chart_server.py)
  maps bars → timestamps with per-timeframe pivot defaults; the `structure_chain` indicator in
  [chart_dashboard.html](tools/chart_dashboard.html) draws 12 dashed swing levels, a marker per
  event (BOS arrows · CHoCH circles · purple `✗ FAILED` squares) and a collapsible chain card in
  the `.action-stack`, with **quality encoded as marker opacity** as in the source. Live-verified
  on TITAN: 47 markers read back off the series, clean teardown to 0, zero console errors; and
  `confirm=wick` measured as materially noisier than `close` (CHoCH 6→13, failed 7→15, max chain
  5→3 over 600 daily bars) — the source's "faster, noisier" note, quantified. **Display only:
  nothing is scored or gated by these fields yet**, so SBC-1/SBC-2 and the load-bearing SBC-3
  backtest remain open.

## Contradictions with Existing Wiki
- **Pivot length disagreement, and it's substantive.** SBC uses **15**; our port uses **5**;
  LuxAlgo runs **5 (internal) + 50 (swing)**. These are different claims about what a "swing" is,
  not a tuning detail — at 5 bars our detector is labelling LuxAlgo's *internal* structure while
  reading it as major structure. Worth resolving deliberately (SBC-1's configurable `pivot_len`
  is the cheap route; two tiers is the LuxAlgo answer).
- **Wick-vs-close confirmation is an open question our port silently answered.** LuxAlgo and our
  port both use close; SBC treats it as a user choice and admits wick = "faster, noisier."
  No contradiction in mechanics, but our hard-coding was never a measured decision.
- **Failure handling is coarser in our port.** Ours only invalidates a bullish event when a later
  close breaks a *swing low* — a slow, structural invalidation. SBC's 3-bar close-back-inside
  test catches the immediate fakeout our version rides through. Both are defensible; ours has no
  fast path, which is a gap, not a disagreement.
- **Name collision** with our existing `scan_structural_breakout` — see the caution above.
- No contradiction on the BOS/CHoCH definition itself: SBC agrees with LuxAlgo and with
  [[concepts/Market-Structure-CHOCH-BOS]], which is now triple-sourced.

## Pages Updated
- [[concepts/Market-Structure-CHOCH-BOS]] — added the SBC layer (break-quality grading, the chain
  counter, time-boxed failed breaks, wick-vs-close confirmation, the pivot-length disagreement);
  sources 2 → 3.
- [[analyses/Dashboard-UI-Roadmap]] — Phase 2 pointer to the SBC-1…SBC-4 port plan above.
- No code changed — **nothing built.**
