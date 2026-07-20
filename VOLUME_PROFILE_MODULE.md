# Volume Profile Module — POC / Value Area / HVN / LVN + Elliott Wave Confluence

Adds Point of Control (POC), Value Area (VAH/VAL), High-Volume Node (HVN) and
Low-Volume Node (LVN) pocket detection to the Trading Bramha multi-chart
dashboard, plus confluence detection against the existing Elliott Wave module.
Also ships as a standalone TradingView Pine Script v5 indicator implementing
the identical math.

---

## 1. What was added

| File | Status | Purpose |
|---|---|---|
| `tools/volume_profile.js` | **new** | Pure computation module — histogram, POC, Value Area, HVN/LVN pockets, confluence matching. Zero chart dependency. |
| `tools/chart_dashboard.html` | modified | Rendering layer: enhanced `drawVolumeProfile()` (POC/VAH/VAL lines + node coloring) and confluence wiring inside `renderElliottWave()`. |
| `tools/chart_server.py` | modified | One new route, `GET /volume_profile.js`. |
| `tools/pine_scripts/EW_VolumeProfile_Confluence.pine` | **new** | Standalone TradingView Pine Script v5 port of the same algorithms (Volume Profile + Elliott Wave + confluence), for use directly on tradingview.com. |

No existing functionality changed. The Elliott Wave module from the prior
round of work (`elliott_wave.js`) is unmodified — this round only adds a
*sibling* module and the glue between the two.

---

## 2. Exact volume pocket boundaries — how every number is computed

All four concepts come from the same binned histogram, built once:

### 2.1 The histogram

The lookback window's bars are binned into `bins` (default 30) equal-width
price rows spanning `[lo, hi]` = the min low / max high over the window.
`binSize = (hi - lo) / bins`; bin `i` spans `[lo + i*binSize, lo + (i+1)*binSize)`.

**Each bar's volume is split across every bin its `[low, high]` range
overlaps**, weighted by the fraction of the bar's range inside that bin —
*not* dumped entirely into the bin containing the close. This is the standard
approximation used whenever only OHLCV (not tick-level) data is available,
and it's materially more accurate than a close-price-only histogram. A
flat/doji bar (high == low) puts its full volume in the single bin containing
its price.

### 2.2 POC (Point of Control)

**The single bin with the most volume.** Its boundaries are simply that
bin's own `[low, high)` edges; the "POC price" quoted on the chart is the
bin's midpoint.

```
pocIdx = argmax(bins)
POC price = (binEdges[pocIdx] + binEdges[pocIdx+1]) / 2
```

### 2.3 Value Area (VAH / VAL)

**The price range containing 70% (configurable) of total traded volume,
built outward from the POC.** Starting with just the POC bin included,
repeatedly compare the bin immediately below the current range to the bin
immediately above it, and add whichever holds *more* volume. Stop once
cumulative volume reaches the target percentage (or no bins remain on either
side).

```
target = totalVolume * 0.70
low = high = pocIdx
cum = bins[pocIdx]
while cum < target and (room below or room above):
    if volume(bin below low) >= volume(bin above high):
        low -= 1 ; cum += bins[low]
    else:
        high += 1 ; cum += bins[high]
VAH = binEdges[high + 1]   (top edge of the topmost included bin)
VAL = binEdges[low]        (bottom edge of the bottommost included bin)
```

This is the standard Market/Volume Profile Value Area algorithm — the exact
same logic used by most professional platforms' "70% Value Area" feature.

### 2.4 HVN (High Volume Node) pockets

**A contiguous price range where trading was significantly heavier than the
profile's average — these act as support/resistance, since lots of resting
volume = lots of resistance to further movement.**

1. **Seed**: bin `i` qualifies as an HVN seed if it's a local maximum
   (`bins[i] >= bins[i-1]` and `>= bins[i+1]`, with no constraint on a
   missing edge neighbor) **and** clears the significance threshold
   `bins[i] >= meanBinVolume * hvnMult` (default `hvnMult = 1.5`).
2. **Expand**: from the seed, absorb each neighboring bin while it stays
   within tolerance of the seed's volume: `bins[neighbor] >= seedVolume * hvnExpandTol`
   (default `hvnExpandTol = 0.85`, i.e. neighbor must be at least 85% of the
   peak). This turns a single peak *row* into the full contiguous price
   **pocket** it actually spans.
3. **Merge**: if two seeds' expanded pockets touch or overlap, they're
   merged into one pocket. (Verified on real `RELIANCE.NS` data — see
   §4 — two adjacent strong-volume seeds correctly merged into a single
   97-point-wide pocket spanning the distribution's true "shoulder".)

```
HVN pocket boundaries = [binEdges[expandedLowIdx], binEdges[expandedHighIdx + 1]]
```

### 2.5 LVN (Low Volume Node) pockets

**The mirror of HVN — a contiguous range where volume was unusually thin.**
These represent price levels the market moved through quickly with little
resting volume / friction; if price revisits one, it tends to move through
it *fast* rather than react, which is the opposite trading implication of an
HVN.

1. **Seed**: bin `i` qualifies if it's a local minimum and
   `bins[i] <= meanBinVolume * lvnMult` (default `lvnMult = 0.5`).
2. **Expand**: absorb neighbors while `bins[neighbor] <= threshold * lvnExpandTol`
   (default `lvnExpandTol = 1.30`).
3. **Merge**: same overlap-merge as HVN.

```
LVN pocket boundaries = [binEdges[expandedLowIdx], binEdges[expandedHighIdx + 1]]
```

---

## 3. Elliott Wave + Volume Profile confluence

A "confluence zone" is any price where the Elliott Wave module's output and
the Volume Profile module's output **independently** point at the same level
— which is exactly the kind of agreement traders look for to upgrade a setup
from "interesting" to "actionable."

**Confluence rule** (`VP.findConfluence(points, profile, tolPct)`, default
`tolPct = 0.4%` of price): for each point (a wave pivot *or* a forward Fibonacci
target), check:

- **POC** — is `|price - pocPrice| <= price * tolPct`?
- **VAH / VAL** — is the price within tolerance of either Value Area edge?
- **HVN / LVN** — does the price fall inside any pocket's `[low, high]`,
  expanded by the same tolerance buffer?

Two kinds of confluence are checked, both rendered in the dashboard:

1. **Realized wave-point confluence** — did a *confirmed* Elliott pivot (a
   wave 1/2/3/4/5 or A/B/C endpoint) land on a POC/VA/HVN/LVN? Rendered as a
   gold ★-starred marker (vs. the normal cyan/amber dot) plus a line in the
   info panel: `W4 @ 1364.79 → HVN`.
2. **Forward fib-target confluence** — does an *unconfirmed* Fibonacci
   projection (Wave 3, Wave 5, or corrective C target) already sit on a real,
   current volume zone? This is arguably the *stronger* signal — a forward
   projection with existing volume support is more credible than one with
   none. Rendered as a brighter/thicker gold dashed ray with a `★VP` label.

Both checks reuse the same `VP_OPTS` / tolerance constants so dashboard and
Pine results stay comparable.

---

## 4. Testing performed

- **Synthetic clustered data**: a hand-built series with a heavy 101–104
  volume cluster, a thin 110–112 zone, and a secondary 115–116 cluster.
  `VP.computeProfile()` correctly placed POC inside the heavy cluster
  (101.70–102.49), Value Area at 96.92–104.88 (70.1% of volume — within
  rounding of the 70% target), found **two separate HVN pockets** (the
  primary and secondary clusters) and **two LVN pockets** (the thin zone
  plus the low-volume base). `VP.findConfluence()` correctly tagged a point
  at the cluster center as `POC+HVN` and a point in the thin zone as `LVN`.
- **Real market data**: fetched 300 daily bars of `RELIANCE.NS` from the live
  `chart_server.py`. Result: POC at 1401.64, Value Area 1310.76–1464.56, one
  merged HVN pocket (1324.74–1422.61 — confirmed by inspecting the raw bin
  table that this *is* the genuinely elevated "shoulder" of the distribution,
  not a degenerate over-merge), two LVN pockets at the distribution's tails.
- **Full pipeline integration test**: ran `EW.analyze()` → `VP.computeProfile()`
  → `VP.findConfluence()` back-to-back against the same real data with **no
  exceptions**, and got realistic, non-trivial confluence hits — e.g. the
  impulse's Wave 0 and Wave 3 pivots landed almost exactly on VAH/VAL, Wave 5
  landed in an LVN pocket (consistent with "fast move with little
  resistance" — the classic real-world reading of a wave extreme ending in a
  low-volume zone), and several Wave 3/5 Fibonacci targets matched HVN/VAL
  zones.
- **Live endpoints**: `GET /volume_profile.js` → `200 application/javascript`
  on a freshly started server; `/`, `/api/ohlcv`, `/api/symbols/search` all
  regression-checked and unaffected.
- **Pine Script**: no TradingView compiler is available in this environment,
  so the script could not be compile-tested directly. It was instead
  carefully hand-audited against known Pine v5 pitfalls and corrected for
  several real issues caught during that audit (see §6) — paste it into
  TradingView's Pine Editor and check the Console for any remaining issues
  before relying on it; the editor's line-numbered error messages make any
  residual problem fast to spot and fix.

---

## 5. Using the Pine Script on TradingView

1. Open any chart on tradingview.com → **Pine Editor** tab (bottom panel).
2. Delete the default template, paste the contents of
   `tools/pine_scripts/EW_VolumeProfile_Confluence.pine`.
3. Click **Add to Chart**.
4. Adjust inputs via the indicator's settings (gear icon):
   - **Volume Profile** group: lookback bars, price bins, Value Area %,
     HVN/LVN thresholds — same parameters/defaults as the dashboard.
   - **Elliott Wave** group: ATR period/multiplier, minimum confidence score
     to display, max impulses shown.
   - **Confluence** group: tolerance %.
5. The indicator recomputes only on the most recent bar (`barstate.islast`),
   the standard efficient pattern for profile/structure indicators — it will
   not bog down on large lookbacks, and it redraws cleanly on every new tick
   without leaving stale objects behind (it deletes and redraws its own
   boxes/lines/labels each time, bounded by `max_boxes_count`/`max_lines_count`/
   `max_labels_count = 500`).

---

## 6. Pine Script correctness notes (for future maintainers)

Three real Pine v5 pitfalls were caught and fixed during development —
documented here since they're easy to reintroduce when editing this script:

1. **`for i = 0 to array.size(x) - 1` is unsafe when the array can be
   empty.** Pine's `for` infers a *descending* direction whenever the upper
   bound is less than the lower bound — `size=0` makes the bound `-1`, so
   Pine would iterate `i = 0` then `i = -1` (two iterations) instead of
   zero. Every such loop in this script uses an explicit `while i < size`
   instead, which has no such ambiguity.
2. **`x / 0.0` is not a reliable "infinity" sentinel.** An early draft used
   `-1.0/0.0` to represent "no neighbor on this side" at array boundaries.
   Pine's float division by zero semantics (`na` propagation through
   comparisons) interacts asymmetrically with `>=`/`<=` chains and can flip
   which branch executes — in the Value Area loop this could have caused an
   out-of-bounds array access. Replaced with explicit `i == 0 ? true : ...`
   boundary checks throughout.
3. **Built-in style constants (`line.style_dashed`, etc.) are not plain
   `int`/`string`.** A helper function originally declared its style
   parameter as `int lineStyle`; passing `line.style_dashed` into an
   explicitly-`int`-typed parameter risks a type-mismatch compile error.
   Fixed by leaving that parameter untyped and letting Pine infer it from
   the call site.

Also note: functions **must** be declared at the script's top level in Pine
v5 — never nested inside `if`/`for`/`while` blocks. All seven helper
functions here (`f_deleteBoxes/Lines/Labels`, `f_buildHistogram`,
`f_mergeRanges`, `f_checkConfluence`, `f_drawWavePoint`, `f_drawFibLevel`)
are declared before either `barstate.islast` block for this reason.

---

## 7. Files changed/added — quick reference

```
tools/volume_profile.js                          [NEW]  ~250 lines
tools/pine_scripts/EW_VolumeProfile_Confluence.pine [NEW]  ~565 lines
tools/chart_dashboard.html                       [MODIFIED]
  - <script src="/volume_profile.js"> tag
  - INDICATORS dropdown label updated: "Volume Profile (POC/VA/HVN/LVN)"
  - drawVolumeProfile() rewritten to use VP.computeProfile() + draw
    POC/VAH/VAL lines and HVN/LVN-colored histogram bars
  - renderElliottWave() / renderEwFibLevels() / renderEwInfo() extended
    with EW+VP confluence detection, marker styling, and info panel lines
tools/chart_server.py                            [MODIFIED]
  - +1 route: GET /volume_profile.js
VOLUME_PROFILE_MODULE.md                         [NEW]  this file
```

---

**Status:** ✅ JS module + dashboard integration tested end-to-end on real
data. Pine Script hand-audited and pitfall-corrected, but not compiler-
verified (no TradingView access in this environment) — please paste it in
and check the Pine Editor's Console before trading off of it.
