# EW forward path: channel and projected wave path (plan)

**Date:** 2026-11-21 · **Status:** proposed, not built

## Why
The reference chart (NIFTY, 22 Nov 2026) shows three forward-looking layers. Most already exist:

| Layer in the chart | Exists today | Where |
|---|---|---|
| Swing pivots, 1-5 and A-B-C labels | Yes | `elliott_wave.js` `EW.analyze` |
| Fib retracement / extension levels | Yes | `fibonacci.js`, `EW.fibLevelsFor*` |
| W3/W5 target distribution (McDowell) | Yes | `ew_module.py` |
| Single projected price + invalidation | Yes | `projection.py` `/api/projection` |
| **Trend channel extended to the right** | **No** | — |
| **Drawn forward path (zig-zag into future bars)** | **No** | — |
| **Primary vs alternate count** | **No** | — |

So the gap is the presentation of the forecast as a path and a channel, not the wave maths.

## Steps
1. **Channel (`EW.channelFor(structure, barsAhead)`)** in `elliott_wave.js`. Impulse: base line through W2 and W4 ends, parallel through W3 end. Corrective: base through the correction start (5) and B, parallel through A, so it works while C is still forming. Returns two lines extended `barsAhead` bars. Pure function with fixture tests. **Done 2026-11-21** (EW 1.5.0, 3 tests).
2. **Forward path (`EW.forwardPath(analysis, targets)`)**. From the last confirmed pivot, build the expected remaining legs: price from the existing W3/W5 or C targets (`ew_module` distribution, primary = highest probability); time per leg = median duration of same-degree completed legs. Output `[{time, price, label}]` with future timestamps from the bar interval (intraday: skip non-session hours, anchored to IST). **Done 2026-11-21** (EW 1.6.0, 6 tests). As built: JS named priors (A-B-C to 38.2% retrace, B = 50% of A, C = 1.0×A), not the `ew_module` distribution; covers complete impulse → A-B-C and partial corrective → rest of A-B-C; complete corrective returns null. `EW.futureTimes` skips weekends and off-session time (NSE, IST) but not exchange holidays. `channelFor` still extends by linear bar spacing — switch it to `futureTimes` in step 4.
3. **Alternate count.** When the latest structure is ambiguous (completed 5 vs still in W3; A-B-C vs triangle A-E), return up to two paths, each with its invalidation price. **Done 2026-11-21** (EW 1.7.0, `EW.forwardScenarios`, 3 tests). As built: primary is always the textbook continuation (not "invalidation further from price"); alternates are W5 extension (1.618×W1 from W4, dead below W4) and contracting triangle (legs 0.618× previous, dead if C passes A). Known gap: with only 5-A formed, primary is invalidated past the correction start, which would wrongly kill an expanded flat.
4. **Render** in `chart_dashboard.html` beside `renderElliottWave()`: channel as two dashed lines, path as a dashed polyline with wave labels, alternate path fainter. Lightweight-charts discards whitespace points (~line 11963), so draw future segments on the drawing layer (`chart_drawings.js`), not as series data. **Done 2026-11-21** as `ewFwdCanvas` + `drawEwForward()` in `chart_dashboard.html`, placed by bar index via `logicalToCoordinate` (so session-aware timestamps are not needed for drawing); live count only; `applyRangeView` leaves `pane.ewFwdRoom` bars of right margin. Verified on ^NSEI 15m (5-A live: B 25,581 → C 26,036, ✕ 25,353.85). Channel not yet seen on real data (needs a live 5-A-B or impulse).
5. **Honesty label.** Every path shows "drawing aid, not measured". The EW structure studies (B-134/135) found no edge, so this stays a context tool.
6. **Optional measurement (later).** Score path hit rate (target before invalidation) with the B-183 plan-odds harness. Pre-register first.

## Out of scope
Auto trading on the path; a new pivot detector (reuse `EW.computeZigzag`).

## Done when
On NIFTY 15m/1h the dashboard draws the channel, the primary path and (when ambiguous) the alternate path with invalidation, and unit tests for steps 1–3 pass.
