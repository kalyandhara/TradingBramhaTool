# Chart Tour ("Tour this chart") — Design (B-186)

**Date:** 2026-10-26
**Status:** design approved in chat; spec awaiting review
**Origin:** [[sources/Web-eVector-Event-Vector-Markets]] — eVector's narrated chart
tour, reverse-engineered (exact detector rules + finding/chart-action protocol). We
adopt the protocol and the rules, and replace eVector's hand-set weights-as-meaning
with the desk's **measured** base rate on every finding.

## 1. Purpose

A "Tour" on the Chart Tool that walks the owner through what the daily chart is
doing **now** and what would change the reading **next**: a fixed opening (Now,
Stock-or-market?) and up to eight findings, each a plain sentence that drives the
chart (zoom, level, highlighted candle, indicators) and carries:

- a **base-rate badge** — what this exact detector has been followed by across the
  NSE panel, versus the same stock's ordinary day; and
- a **Watch** line — the level that would invalidate or confirm it.

It describes; it is not a signal. Most badges are expected to read "Ordinary" —
that is the point (see the desk's B-101, B-147, B-182, FVG-fill nulls).

### Success criteria

- `/api/tour?symbol=RELIANCE.NS` returns Now + Stock-or-market + findings, each with a
  validated action list, badge and watch line.
- The side panel steps through them with `[` `]`/click and the chart obeys the actions
  (browser-verified on :8502).
- `tour_base_rates.py` produces `tools/cache/tour_base_rates.json` for every detector;
  a planted-effect panel comes out Edge and a null panel Ordinary in tests.
- The first real base-rate run is pre-registered on the wiki before it runs.

## 2. Architecture

```
tools/chart_tour.py          pure engine (no I/O)
tools/tour_base_rates.py     study job: same detectors over the panel -> JSON (+ wiki)
tools/chart_server.py        GET /api/tour
tools/chart_dashboard.html   Tour button, side panel, action executor
tools/test_chart_tour.py, tools/test_tour_base_rates.py, tools/test_chart_routes.py (route)
tools/cache/tour_base_rates.json
```

One detector definition feeds both the chart and the base-rate table, so a badge
always describes the rule that drew the card.

### 2.1 Engine (`chart_tour.py`)

```python
@dataclass
class Finding:
    id: str                 # f"{detector}:{time or 'state'}"
    detector: str           # DETECTORS key
    title: str              # one plain sentence
    body: str               # facts in words
    facts: dict             # numbers used in title/body
    time: str | None        # bar date the finding is anchored to; None for state findings
    weight: float           # ordering only (eVector's formulas for ported detectors)
    tone: str               # "up" | "down" | "neutral"
    watch: dict | None      # {"text": str, "level": float | None}
    actions: list[dict]     # validated by validate_actions()

@dataclass
class Detector:
    key: str
    label: str
    family: str             # "evector" | "desk"
    kind: str               # "dated" | "state"
    claim: str              # "directional" | "magnitude"
    fn: Callable[[pd.DataFrame], list[Finding]]

DETECTORS: dict[str, Detector]
now_step(df) -> dict
context_step(df, market_df, sector_df, sector_name) -> dict
build_tour(df, *, market_df, sector_df, sector_name, base_rates: dict | None,
           study_links: dict, max_findings=8) -> dict
validate_actions(actions) -> list[dict]          # raises on unknown type/shape
```

Input `df`: daily OHLCV, DatetimeIndex, columns `open high low close volume`.
Fewer than 80 bars → only the Now step plus a note.

### 2.2 Detectors (v1)

**Ported from eVector, thresholds verbatim** (source: REA pass 2026-10-26):

| key | rule | tone / claim |
|---|---|---|
| `breakout55` | in the last 15 bars a close crosses above the prior 55-session closing high; **not** failed | up / directional |
| `failed_breakout55` | same, and any later close < 0.98 × level | down / directional |
| `breakdown55` | close crosses below the prior 55-session closing low; not failed | down / directional |
| `failed_breakdown55` | same, and any later close > 1.02 × level | up / directional |
| `volume_expansion` | mean volume last 5 / mean of the 50 before ≥ 1.5 | tone = sign of 5-bar price change / directional |
| `atr_expansion` | Wilder ATR14 now / ATR14 42 bars ago ≥ 1.4 | neutral / magnitude |
| `squeeze` | BB(20,2) width÷mid ≤ 1.05 × its 126-bar minimum (≥ 60 values) | neutral / magnitude |
| `bearish_div` / `bullish_div` | last two 5-bar swing highs (lows) in 40 bars: higher high (lower low) with RSI14 lower (higher) by > 4 | down / up, directional |
| `gap_up` / `gap_down` | in the last 10 bars, \|open/prev close − 1\| ≥ 3 % and still unfilled | up / down, directional |
| `above_sma200` / `below_sma200` | close crosses the 200-day SMA (state) | up / down, directional |
| `golden_cross` / `death_cross` | SMA50 crosses SMA200 | up / down, directional |

Weights: eVector's formulas for the ported rules (breakout 0.7 + recency/50 +
min(0.2,(RVOL−1)/5); volume min(0.85, 0.4+(x−1.5)/3); ATR min(0.8, 0.4+(x−1.4)/2);
squeeze 0.65; divergence 0.7; gap 0.6+min(0.2,|gap|)); crosses and SMA200 0.6.
Weights only order the cards; they are never shown as meaning.

**Desk detectors, called not copied:**

| key | source | tone / claim | study link (strict) |
|---|---|---|---|
| `structure_break_held` | `scanner_templates.detect_structure_chain` (overlay defaults) — latest break not failed | by break side / directional | B-114 |
| `liquidity_sweep_bull` | `scanner_templates.detect_liquidity_sweep` (bull) | up / directional | B-41m |
| `flag_pole_bull` | `flag_pole.detect_flag_pole(direction="bull")` | up / directional | B-92 |
| `abcd` | `harmonic_patterns.detect_last_pattern` (the "Harmonic Reversal (XABCD)" scanner's detector), bullish only, `pattern` containing "AB=CD", stop D − 2×ATR14 (`scanner_templates.ABCD_STOP_ATR`) | up / directional | B-132 |
| `adx_up_state` | ADX confirmed up-state (ADX study rule) | up / directional | ADX (the `named_studies` entry) |

Study links follow `indicator_evidence`'s rule: a study is linked only where it
tested **this exact detector**. eVector-ported detectors get no study link.

`kind="state"` detectors fire on the first bar the condition becomes true and cannot
re-fire within 20 bars (for the base-rate job; the tour shows the current state).

### 2.3 Fixed steps

- **Now:** close; 63-bar range low–high and % from each end; trend word (close vs
  SMA20 and SMA20's 5-bar slope: Uptrend / Downtrend / Sideways); RVOL (last bar
  volume ÷ 20-bar mean). Actions: `CLEAR`, `ZOOM_TO_RANGE` (63 bars), `PRICE_LEVEL`
  ×2 (range high/low), `HIGHLIGHT_CANDLE` (last bar).
- **Stock or market?:** 20-session return of the stock vs NIFTY (`^NSEI`) and its
  sector index (the Stock Analyzer's existing sector→index map); "ahead" if stock −
  max(NIFTY, sector) > +5 pp, "behind" if < −5 pp, else "in line". Actions: `COMPARE`
  [^NSEI, sector index], `ZOOM_TO_RANGE` 20 bars. Sector unknown → NIFTY only.

### 2.4 Watch lines

| detector | watch |
|---|---|
| breakout55 | close < 0.98 × level → becomes failed breakout |
| failed_breakout55 / failed_breakdown55 | reclaim of the level |
| breakdown55 | close > 1.02 × level → becomes failed breakdown |
| gap_up / gap_down | prior close (the fill level) |
| squeeze | BB upper / lower — whichever breaks first |
| divergences | the swing high / low measured from |
| above/below_sma200, crosses | SMA200 (and SMA50 for crosses) current value |
| liquidity_sweep_bull | the swept level |
| structure_break_held | the break level (B-114's failed rule) |
| flag_pole_bull | the detector's stop |
| abcd | D − 2 × ATR14 |
| atr_expansion, volume_expansion | none (text only) |
| adx_up_state | −DI crossing back above +DI |

### 2.5 Action protocol

`CLEAR` · `ZOOM_TO_RANGE{from,to}` · `PRICE_LEVEL{price,label,tone}` ·
`HIGHLIGHT_CANDLE{time,tone}` · `HIGHLIGHT_RANGE{from,to,tone}` ·
`INDICATORS{ids}` (existing `INDICATOR_DEFS` keys only) · `COMPARE{symbols}`.
Times are ISO dates of bars in the response; tone ∈ up/down/neutral/accent.
`validate_actions` rejects anything else; the JS executor ignores unknown types.

## 3. Base rates (`tour_base_rates.py`)

- **Panel:** the B-165 panel — `nu.symbols("nifty500")[:300]`, last 750 daily bars,
  via `crt_sweep_overlap._fetch` (same as B-182).
- **Event:** dated detectors at their bar; state detectors at the first bar the state
  turns true, 20-bar refractory.
- **Outcome:** forward log return t→t+h, h ∈ {5, 20, 60}, minus the same symbol's mean
  forward h-return over all panel bars ("vs a normal day"). Directional detectors are
  sign-aligned to their tone (down-tone negated). Magnitude detectors use
  |fwd| − mean |fwd| of the symbol.
- **Statistic:** per-symbol mean excess; one-sample t across symbols; h=20 decides.
- **Labels** (family = all detectors, Holm at α 0.05 on the h=20 p-values):
  - `EDGE` — ≥ 30 symbols, ≥ 100 events, Holm p < 0.05, positive (sign-aligned),
    same sign in ≥ 2 of 3 equal time-thirds of event dates;
  - `INVERTED` — same floors and significance, negative;
  - `ORDINARY` — floors met, not significant;
  - `TOO_FEW` — floors not met.
- **Output** `tools/cache/tour_base_rates.json`: `{asOf, panel, horizons, detectors:
  {key: {label, n_events, n_symbols, mean20, p20, p20_holm, mean5, mean60, thirds}}}`.
- **Badge text:** `"<Label> · <±x.x%> vs a normal day @20d · <n> events / <m> names ·
  p <p> · as of <YYYY-MM>"`; gross of costs (tooltip says so). Study links appear as
  a second line with the study's own headline and date; panel and study numbers are
  shown side by side if they disagree — neither overrides.
- **Pre-registration:** the first real run gets a wiki pre-registration page with
  these rules before it runs (desk norm); result page after.

## 4. API

`GET /api/tour?symbol=&timeframe=1d` → `{symbol, asOf, steps:[now, context,
...findings], base_rates_asOf, notes:[...]}`.

- timeframe ≠ `1d` → 200 with `{steps: [], notes: ["The tour is daily-only: its base
  rates are measured on daily bars."]}`.
- Bars: `source.get_ohlcv(symbol, "1d", 400)` (same resolution path as `/api/ohlcv`).
- A detector raising → skipped, logged, `notes` mentions it; the tour still returns.
- Base-rate file missing → every badge `NOT_MEASURED`; older than 45 days → badge
  carries `stale: true` (rendered amber with its date).

## 5. Chart UI (`chart_dashboard.html`)

- A **Tour** button in the chart toolbar opens a right side panel (layout A, chosen in
  the visual companion): header "Tour · SYMBOL · daily · as of DATE", step list,
  `[` `]` and click to step; the active step's actions run on the chart; closing the
  panel runs `CLEAR`.
- Badge colours: Edge green, Inverted red ("worked backwards"), Ordinary grey, Too few
  / Not measured amber.
- Actions draw on a dedicated tour layer (price lines/markers/range shading) that
  `CLEAR` removes without touching the user's own indicators or drawings; `INDICATORS`
  toggles existing indicators and `CLEAR` restores the user's prior set.

## 6. Testing

- Per detector: a synthetic series it must catch, a near-miss it must not, and the
  threshold edges (0.98 / 1.02, 1.5×, 1.4×, 1.05× BB minimum, RSI 4-point, 3 % gap,
  filled vs unfilled).
- `validate_actions` accepts the seven types and rejects others.
- `build_tour`: < 80 bars → Now only; a raising detector is skipped with a note;
  ordering newest-then-weight; max 8.
- `/api/tour` with a stubbed data source; non-daily timeframe note.
- Base-rate job: planted-effect panel → EDGE; null panel → ORDINARY; floors → TOO_FEW;
  Holm and the thirds rule on hand-built inputs; refractory window.
- Browser verification of the panel and every action type on :8502.

## 7. Out of scope (v1)

Intraday tours; AI "ask the chart"; momentum lifecycle state (B-185 — slots into Now
later); chart event markers (B-188); costs in base rates.
