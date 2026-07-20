# Elliott Wave Module — Trading Bramha Multi-Chart

Adaptive Elliott Wave detection (Impulse 1–5, Corrective A–B–C) with Fibonacci
projections, integrated as a plug-in indicator on the existing Lightweight
Charts multi-chart dashboard (`tools/chart_dashboard.html` +
`tools/chart_server.py`). Also adds a dedicated **Volume** histogram
sub-pane, requested alongside the Elliott Wave work.

---

## 1. What was added

| File | Status | Purpose |
|---|---|---|
| `tools/elliott_wave.js` | **new** | Pure computation module — ZigZag pivots, impulse/corrective detection, Fibonacci levels. Zero chart-library dependency. |
| `tools/chart_dashboard.html` | modified | Rendering/integration layer: indicator toggle, line/marker drawing, fib rays, info panel, Volume sub-pane. |
| `tools/chart_server.py` | modified | One new route, `GET /elliott_wave.js`, to serve the module file (mirrors the existing `index()` pattern). |

No existing functionality was changed or removed. Every prior indicator
(SMA/EMA/VWAP, Bollinger/Donchian/Keltner, RSI/MACD/OBV/RS, Volume Profile,
symbol search, live WebSocket ticks, grid layouts, per-pane persistence)
behaves exactly as before.

---

## 2. How the wave-detection logic works

### 2.1 Pivot detection — adaptive ZigZag (`EW.computeZigzag`)

Elliott Wave theory is defined over *swing points*, not raw candles, so the
first step reduces the bar series to alternating high/low pivots.

- **Volatility-adaptive threshold.** A reversal is only confirmed once price
  retraces by at least `max(price × minPct%, ATR(14) × atrMult)`. Using
  Wilder's ATR rather than a fixed percentage means the same module works
  unmodified on a ₹50 small-cap, a ₹140,000 BTC chart, or a calm vs. volatile
  regime of the *same* instrument — the threshold stretches and shrinks with
  recent realized volatility automatically. Defaults: `atrPeriod=14`,
  `atrMult=1.2`, `minPct=0.5` (the `%` floor protects against degenerate
  near-zero ATR on very quiet/illiquid bars).
- **Non-repainting by construction.** Every pivot in the list *except the
  last* represents a reversal that has already been confirmed by a
  subsequent opposite move of at least the threshold size — that is a fact
  about historical price action and can never change. Only the trailing
  pivot is `provisional: true`; it tracks the still-extending current
  extreme and may keep moving until a future bar confirms a reversal away
  from it. This single property is what the entire no-repaint guarantee
  downstream is built on.

### 2.2 Impulse detection — Wave 1–5 (`EW.detectImpulses`)

A greedy left-to-right scan slides a 6-point window (5 legs) across the
pivot list. For each window:

1. **Direction & alternation check** — the 6 points must alternate
   low/high/low/high/low/high (bullish) or the mirror (bearish); this is
   already guaranteed by the ZigZag's own alternation, but is re-verified
   defensively.
2. **Hard Elliott rules** (a window is rejected outright if any fail):
   - *Rule 1:* Wave 2 never retraces more than 100% of Wave 1 (price never
     crosses back past the start of Wave 1).
   - *Rule 2:* Wave 3 travels beyond the end of Wave 1 (trend continuation).
   - *Rule 3:* Wave 3 is never the shortest of waves 1, 3, 5.
3. **Diagonal flag (not a hard rule)** — classic Rule 4 says Wave 4 must not
   overlap Wave 1's price territory, *except* in diagonal triangle patterns.
   Rather than discarding these, the module flags `diagonal: true` so the
   info panel can surface "⚠ W4 overlaps W1" instead of silently hiding a
   potentially valid (diagonal) count.
4. **Soft Fibonacci scoring (0–100)** — among windows that pass the hard
   rules, a confidence score is computed from how close the retracement/
   extension ratios sit to classic Elliott/Fibonacci zones (W2 retrace
   ≈38.2/50/61.8/78.6%, W3 extension ≈1.0/1.618/2.618×, W4 retrace
   ≈23.6/38.2/50%, W5 ≈0.618/1.0/1.618× W1). This is *informational*, not a
   pass/fail gate — real markets rarely print textbook-perfect ratios.
5. Once a valid window is accepted, the scan resumes **after** its Wave 5
   pivot — producing one clean, non-overlapping sequence of impulses across
   the chart, the same way a human analyst marks one count at a time,
   instead of an explosion of overlapping candidate counts.

### 2.3 Corrective detection — Wave A–B–C (`EW.detectCorrectives`)

For every detected impulse, the pivots immediately following its Wave 5
point are labeled `5, A, B, C` (up to 3 further legs). The module supports
*partial* corrections in real time — if only A has formed so far, it still
reports `lenA`; once B forms it computes `bRetracePct` and classifies the
shape heuristically (`zigzag` if B retraces ≤80% of A, `flat` if 80–105%,
`expanded-flat` beyond that); once C forms it adds `cVsA`.

### 2.4 Fibonacci projections (`EW.fibLevelsForImpulse` / `…Corrective`)

- **Wave 3 targets**, projected from the end of Wave 2: 1.0×, 1.618×, 2.618×
  the Wave 1 length.
- **Wave 5 targets**, projected from the end of Wave 4: 0.618×, 1.0×,
  1.618× Wave 1, plus the common "0.618× of the net 0→3 move" equality rule.
- **Corrective C target**, projected from the end of Wave B: 0.618×, 1.0×,
  1.618× the Wave A length, continuing in Wave A's direction.

Levels are returned as `{fromTime, price, label}` — the rendering layer
draws them as a horizontal ray from the anchor point to the current bar
(not an infinite line across the whole chart), so old projections from a
completed wave don't clutter unrelated history.

### 2.5 Rendering / selection policy (chart_dashboard.html)

`elliott_wave.js` deliberately knows nothing about charts or DOM. The
integration layer (`renderElliottWave()` in `chart_dashboard.html`) is the
"plug" that:

- Calls `EW.analyze(bars, opts)` to get all pivots/impulses/correctives.
- **Ranks impulses by confidence score** (ties broken by recency) and
  **caps display to the top 3** with `score ≥ 25`. This is a *presentation*
  policy, intentionally kept separate from the detection module — on
  choppy/flat data the ZigZag will still find small adaptive swings (that's
  correct, volatility-adaptive behavior), but the score-based ranking keeps
  the chart from being cluttered with low-confidence noise while always
  showing the cleanest counts found.
- Draws each shown structure as its own `LineSeries` connecting the wave
  points (solid cyan for impulses, dashed amber for correctives), plus text
  markers (`1,2,3,4,5,A,B,C`) via `series.setMarkers()`.
- Draws Fibonacci levels for the single most recent impulse/corrective as
  short dashed gold rays with on-chart price labels.
- Updates a small overlay info panel (top-left of the price pane) with
  numeric wave lengths, retracement %, extension ratios, and the confidence
  score.
- **Incremental, non-repainting redraw.** Because `EW.computeZigzag` only
  ever marks the *trailing* pivot as provisional, any structure rendered
  whose last point is not that trailing pivot is final and will never
  change on a later call — only the most recent (still-forming) structure's
  line/markers move as new bars arrive.

---

## 3. Summary of new functions

### `tools/elliott_wave.js` (pure module, `window.EW`)

| Function | Returns |
|---|---|
| `atr(bars, period)` *(internal)* | Wilder's ATR, index-aligned, nulls before warm-up |
| `computeZigzag(bars, opts)` | `pivots[]` — `{idx, time, price, type, provisional?}` |
| `fibScore(value, idealRatios, tol)` *(internal)* | 0–100 proximity score |
| `scoreImpulse(ratios)` *(internal)* | 0–100 composite confidence |
| `detectImpulses(pivots)` | `impulse[]` — `{id, bullish, points, ratios, diagonal, final, score, lengths}` |
| `detectCorrectives(pivots, impulses)` | `corrective[]` — `{id, parentImpulseId, points, ratios, complete, final}` |
| `fibLevelsForImpulse(impulse)` | `[{role, ratio, fromTime, price, label}]` |
| `fibLevelsForCorrective(corrective)` | `[{role, ratio, fromTime, price, label}]` |
| `analyze(bars, opts)` | `{pivots, impulses, correctives}` — convenience entry point |

### `tools/chart_dashboard.html` (integration layer)

| Function | Purpose |
|---|---|
| `volumeBarSeries(bars)` | Builds histogram data for the new Volume sub-pane, colored like the candles |
| `ensureEwState(pane)` | Lazily creates the per-pane Elliott Wave render-state cache |
| `clearElliottWave(pane)` | Removes all EW series/markers/info when the toggle is switched off |
| `selectStructuresToRender(impulses)` | Confidence-ranks and caps which structures get drawn |
| `ewWavePointPosition(p)` | Maps a pivot's high/low type to a marker's above/below placement |
| `renderElliottWave(pane)` | Main entry point — calls `EW.analyze`, applies selection policy, draws lines/markers |
| `renderEwFibLevels(pane, impulse, corrective)` | Draws the gold dashed Fibonacci projection rays |
| `renderEwInfo(pane, impulse, corrective)` | Updates the numeric wave-stats overlay panel |

### `tools/chart_server.py`

| Route | Purpose |
|---|---|
| `GET /elliott_wave.js` | Serves the new plug-in module (mirrors the existing `index()` route) |

---

## 4. How it merges into the existing system

Everything plugs into the **existing, generic indicator framework** — no
new UI chrome, no parallel toggle system:

1. `chart_dashboard.html` already had an `INDICATOR_DEFS` catalogue driving
   a checkbox dropdown (`renderIndicatorPanel()`) and a single dispatcher
   (`applyIndicators(pane)`) that creates/destroys overlay series or
   sub-panes per the checked set, with per-pane state persisted to
   `localStorage`.
2. Two new catalogue entries were appended:
   ```js
   {key:'volume',  label:'Volume',                    group:'Volume',              color:'#888888'},
   {key:'elliott', label:'Elliott Wave (1-5, A-B-C)',  group:'Pattern Recognition', color:'#00e5ff'},
   ```
   and a new group, `'Pattern Recognition'`, added to `INDICATOR_GROUPS`.
3. `applyIndicators()` gained two `if (pane.indicators.has(...))` blocks —
   one creating the Volume sub-pane (reusing `addSubPane`/`removeSubPane`,
   the exact same mechanism RSI/MACD/OBV/RS already use), one calling
   `renderElliottWave(pane)`. A matching cleanup line tears down the EW
   overlay when unchecked.
4. **ON/OFF toggle, persistence, restore-on-reload** — all free, inherited
   automatically from the existing generic checkbox/`savePaneCfg()`
   machinery. No bespoke toggle code was needed.

### To merge this into another branch / environment

1. Copy `tools/elliott_wave.js` into the target `tools/` directory.
2. Apply the `chart_server.py` diff (one new route).
3. Apply the `chart_dashboard.html` diff:
   - `<script src="/elliott_wave.js"></script>` tag (loaded after the
     Lightweight Charts CDN script, before the inline `<script>` block).
   - `.ew-info` CSS block.
   - Two `INDICATOR_DEFS` entries + `'Pattern Recognition'` group.
   - `volumeBarSeries()` function.
   - The Elliott Wave rendering block (`ensureEwState` through
     `renderEwInfo`).
   - The two `applyIndicators()` hook lines (cleanup + creation, both for
     `volume` and `elliott`).
4. Restart `chart_server.py`; hard-refresh the browser tab (the new
   `elliott_wave.js` script tag needs a fresh load).

No database migrations, no new Python dependencies, no changes to
`data_source.py` or `symbol_directory.py`.

---

## 5. Testing performed

- **Syntax**: both the inline `<script>` block and `elliott_wave.js` parse
  cleanly (`new Function(...)` in Node); `chart_server.py` byte-compiles.
- **Synthetic textbook pattern**: a hand-built 5-wave impulse (Wave 2
  retrace 60%, Wave 3 extension 1.6×, Wave 4 retrace 38%, Wave 5 ≈1.2× Wave
  1) plus a zigzag A-B-C correction was fed through `EW.analyze()`. Result:
  the intended impulse was correctly identified with **score 66/100**, all
  ratios matched the intended Fibonacci targets within a few percent, and
  the corrective A-B-C points matched the synthetic legs exactly
  (`bRetracePct≈0.56`, `cVsA≈1.26`, pattern correctly guessed `'zigzag'`).
- **Real market data**: fetched 300 daily bars of `RELIANCE.NS` from the
  live `chart_server.py` and ran the same pipeline:
  - **Performance: 1 ms** for 300 bars → 130 pivots → 18 candidate
    impulses + 18 correctives. Negligible cost even on every WebSocket tick.
  - Trailing pivot correctly flagged `provisional: true`; all others final.
  - Confidence scores spread realistically from 9–49 (real markets don't
    print textbook ratios) — the selection policy correctly surfaced only
    the 3 highest-scoring (45–49) structures, discarding the noisy ones.
- **Live endpoints**: with a freshly started `chart_server.py`, confirmed
  `GET /elliott_wave.js` → `200 application/javascript`, `GET /` (the
  dashboard) → `200`, and the pre-existing `/api/ohlcv` and
  `/api/symbols/search` endpoints are unaffected (regression check after
  touching `chart_server.py`).
- Manual verification still needed: open the dashboard in a browser, tick
  **Elliott Wave (1-5, A-B-C)** in a pane's INDICATORS dropdown, and confirm
  the visual line/markers/info panel render as described (this environment
  has no headless browser available to automate that last visual step).

---

## 6. Optional optimizations / future enhancements

Already applied:
- **Cheap recompute guard** — `renderElliottWave` skips re-running
  `EW.analyze` if `bars.length` + the last bar's `time`/`close` are
  unchanged since the previous call (e.g., when an unrelated indicator
  checkbox is toggled and `applyIndicators` re-runs everything).
- **Greedy non-overlapping scan** — O(pivots), not O(pivots²), since each
  accepted window jumps the scan pointer forward by 5 instead of 1.

Possible future work (not implemented, out of current scope):
- **Nested/fractal degree counts** — currently detects a single primary
  degree; a recursive call of `detectImpulses` on the *intra-wave* bars of
  each leg would surface sub-waves (i, ii, iii, iv, v) for multi-timeframe
  confluence.
- **Triangle/double-three corrective patterns** — only zigzag/flat/
  expanded-flat are heuristically distinguished today; contracting/
  expanding triangles and W-X-Y double corrections are not separately
  classified.
- **Truncated 5th wave detection** — currently requires Wave 5 to exceed
  Wave 3's start; a rare truncated-5 (Wave 5 fails to exceed Wave 3) is
  rejected by Rule 2 rather than specially flagged.
- **Web Worker offload** — at 1 ms/300 bars this isn't currently necessary,
  but if `EW_MAX_RENDERED` or pane count grows substantially, the analysis
  call could be moved off the main thread.
- **Heliocentric/declination-style multi-source confirmation** — combining
  this module's signal with the repo's existing `financial_astrology_methods.py`
  cycle/timing signals (already in `tools/`) as a confluence filter is a
  natural follow-up, not attempted here to keep this change scoped to
  charting only.
