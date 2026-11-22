# Time cycles and FLD on the chart (plan)

**Date:** 2026-11-21 · **Status:** proposed, not built

## Why
The reference chart (NIFTY 1D, "55 Day's Time Cycle") forecasts with time rather than wave shape:

| Layer in the chart | Exists today | Where |
|---|---|---|
| FLD maths (price shifted c/2 bars forward) | Yes, Python only | `fld_confluence.py` (20/40/80/160) |
| **FLD line drawn on the chart, running into future bars** | **No** | — |
| Time-cycle verticals | Partly: fixed Gann day counts from a clicked bar | `chart_drawings.js` `gcycle` |
| **Cycle length measured from troughs + next-trough verticals** | **No** | — |
| **Swing-size boxes copied forward** | **No** | — |
| Oscillator (AKMid 5/10/15) | No; proprietary, will not be cloned | — |
| EW labels, channel, forward path | Yes | `elliott_wave.js` (EW forward-path plan) |

The gray line in the reference chart is the FLD. Its forward part is known data shifted forward, not a prediction. That is what makes it look forward-looking.

## Steps
1. **FLD overlay.**
   - Write a pure JS port `cycles.js` with `CY.fld(closes, cycle)`, which returns the known part and the forward part (the last `c/2` values placed on future bar indices).
   - Add a toggle in `chart_dashboard.html` to draw one FLD per selected cycle: solid up to the last bar, dashed into the future on a canvas overlay. This uses the same bar-index placement and `ewFwdRoom`-style right margin as `drawEwForward`.
   - The cycle length can be chosen: 20/40/80/160, or the one measured in step 2.
   - Add node-run pytest fixtures, including a check that the JS port matches `fld_confluence._fld` on a sample series.
   - **Done 2026-11-21.** As built:
     - `tools/cycles.js` (CY 1.0.0) `CY.fld`, with 3 tests in `tools/test_cycles.py`, including parity with `fld_confluence._prep` for 20/40/80.
     - Three toggles: `fld20`, `fld40`, `fld80` (160 was left out because a dashed tail of 80 bars is too long to be useful).
     - Drawn on `fldCanvas` by `drawFld`; `renderFld` sets `pane.fldRoom`, and `applyRangeView` uses the larger of the EW and FLD margins.
     - `cycles.js` was added to the `sw.js` shell.
     - Verified on ^NSEI 15m with FLD 20 + 40 beside the EW path. Turning them off clears the canvas. There were no console errors.
     - The cycle choice is not yet fed from step 2's measured cycle.
2. **Cycle detection.**
   - Write `CY.dominantCycle(bars)` to find troughs with the existing `EW.computeZigzag` and measure the median trough-to-trough spacing in bars. It also reports the spread (inter-quartile range) and the count of troughs used.
   - Draw verticals at the next expected trough and the half-cycle mark, each with a shaded window of ± the inter-quartile range, not a single exact day.
   - Label the line with the measured length (e.g. "cycle ≈ 52 bars, IQR 44–61, n = 9"). Use the measured length, not the reference chart's 55.
   - **Done 2026-11-21.** As built:
     - `CY.dominantCycle(pivots, lastIdx)` (CY 1.1.0), with 3 tests. It takes pivots rather than bars, so `cycles.js` stays independent of EW; the chart passes `EW.computeZigzag(bars)`.
     - It uses confirmed lows only (provisional ones are ignored) and needs at least 3 spacings.
     - Quartiles use linear interpolation, the same as numpy.
     - When the window has closed without a new low, it is flagged `overdue` and not rolled forward.
     - Chart toggle `cyclewin` draws on `fldCanvas`: the last trough and half-cycle mark as dotted lines, the q1–q3 window shaded, and the median as a solid line labelled "next trough", with a caption giving the length, IQR and n.
     - Verified on ^NSEI 15m (cycle ≈ 24 bars, IQR 21–25, n = 7). Turning it off clears the canvas.
     - Known limits:
       - The measured length depends on the zigzag swing size.
       - The FLD toggles still use fixed 20/40/80 rather than the measured cycle.
3. **Swing boxes.**
   - Optionally copy the last completed trough-to-peak swing (price and bars) forward from the latest trough as a shaded box.
   - Keep it as a drawing only.
4. **Honesty label.**
   - Caption it "Cycles/FLD: drawing aid, not measured" and flag the data with `drawingAid: true`.
   - FLD-1 is still uncalibrated (no fitted model), and the EW structure studies found no edge.
5. **Optional measurement (later).**
   - Measure whether projected trough windows contain actual troughs more often than random windows of the same width. Pre-register the test first.

## Out of scope
- Cloning the AKMid oscillator.
- Auto signals or alerts from cycle dates.
- Changes to `fld_confluence.py` scoring.

## Done when
On NIFTY 1D the dashboard draws the FLD running into future bars, the measured cycle with next-trough windows, and the caption. Unit tests for steps 1–2 pass.
