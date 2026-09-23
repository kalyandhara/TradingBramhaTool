#!/usr/bin/env python3
"""
backtest.py — point-in-time replay harness for the Scanner Hub scanners.

The dashboard's scanners (``scanner_templates.SCANNERS``) and the council's
thresholds are all *hand-set* — flagged across the wiki as the single biggest
credibility gap (see analyses/Dashboard-UI-Roadmap Phase 3). This module is the
measurement layer: it replays any ``scan_*(df) -> dict | None`` scanner over
historical data, bar by bar, and reports whether firing actually preceded
above-baseline forward returns.

Design (the honesty-critical parts):

  * **No look-ahead.** At bar ``t`` the scanner is handed ONLY ``df.iloc[:t+1]``
    — it physically cannot see the future. Entry is taken at the NEXT bar's open
    (``t+1``), never the signal bar's own close, so a signal that depends on the
    close can't be "traded" on that same close.
  * **Baseline = random entry in the same tape.** Every scanner looks good in a
    bull market. "Edge" here means the signal's average forward return MINUS the
    average forward return of *all bars* over the same symbols and window — i.e.
    did firing beat a coin-flip entry on the same names over the same period.
  * **R-expectancy only where a plan exists.** Scanners that emit
    ``entry``/``stop``/``target`` get a stop-or-target-first simulation and an
    expectancy in R; scanners without a plan get forward-return metrics only.
  * **Thin samples are flagged, not hidden.** A hit-rate off < ``MIN_SAMPLE``
    signals is marked unreliable rather than quoted as a headline number.

Known limitations (labelled, not silently ignored):
  * **Survivorship bias** — only names that exist today are in the universe.
  * **History depth varies** — young listings contribute fewer bars/signals.

Cost models (B-29): ``COST_INDIAN`` (realistic NSE delivery: STT + brokerage +
exchange + GST + stamp + slippage, ~32 bps), ``FlatCost(bps)`` (flat haircut),
or ``COST_GROSS`` (no costs).  Walk-forward (B-21): ``walk_forward_scanner``
splits into N non-overlapping windows and pools OOS results.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

try:
    from scipy import stats as _scipy_stats
except Exception:
    _scipy_stats = None

import scanner_templates as sc


# ---------------------------------------------------------------------------
# Cost models (B-29)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CostModel:
    """Round-trip transaction cost model.

    Subclass or use the two factories below.  The interface is one method:
    ``round_trip_pct(entry, exit)`` → total cost as **percentage points** of
    entry price (comparable to the return numbers the harness works in).
    """

    def round_trip_pct(self, entry: float, exit: float) -> float:
        raise NotImplementedError

    @property
    def label(self) -> str:
        return "unknown"


@dataclass(frozen=True)
class FlatCost(CostModel):
    bps: float = 0

    def round_trip_pct(self, entry: float, exit: float) -> float:
        return self.bps / 100.0

    @property
    def label(self) -> str:
        return f"flat {self.bps:.0f}bps" if self.bps else "GROSS"


@dataclass(frozen=True)
class IndianDeliveryCost(CostModel):
    """NSE cash-equity delivery cost structure (discount broker).

    Each field is a fraction (0.001 = 0.1%).  The model is asymmetric:
    STT is levied on the sell side only for delivery trades.
    """
    stt_sell: float = 0.001          # 0.1% on sell value
    brokerage: float = 0.0003       # 0.03% each side
    exchange_turnover: float = 0.0000345  # NSE turnover charge
    gst_rate: float = 0.18          # 18% on (brokerage + exchange)
    stamp_buy: float = 0.00015      # 0.015% on buy value
    slippage: float = 0.0005        # 0.05% each side (conservative)

    def round_trip_pct(self, entry: float, exit: float) -> float:
        if entry <= 0:
            return 0.0
        buy_val = entry
        sell_val = abs(exit)
        brok_buy = buy_val * self.brokerage
        brok_sell = sell_val * self.brokerage
        exch_buy = buy_val * self.exchange_turnover
        exch_sell = sell_val * self.exchange_turnover
        gst = (brok_buy + brok_sell + exch_buy + exch_sell) * self.gst_rate
        stt = sell_val * self.stt_sell
        stamp = buy_val * self.stamp_buy
        slip = (buy_val + sell_val) * self.slippage
        total = brok_buy + brok_sell + exch_buy + exch_sell + gst + stt + stamp + slip
        return (total / buy_val) * 100.0   # percentage points

    @property
    def label(self) -> str:
        approx_pct = self.round_trip_pct(500, 500)
        return f"Indian delivery ~{approx_pct * 100:.0f}bps"


COST_GROSS = FlatCost(0)
COST_INDIAN = IndianDeliveryCost()

# A scanner needs enough warm-up history before its first honest evaluation
# (Stage-2 wants ~210 bars). Start every replay after this many bars.
WARMUP_BARS = 210

# Below this many recorded signals, aggregate stats are statistically noise.
MIN_SAMPLE = 30

# Default forward-return horizons (in trading bars).
DEFAULT_HORIZONS = (5, 10, 20, 60)

# A trending scanner fires on many consecutive bars; counting each as an
# independent trade inflates and correlates the sample. Enforce a gap (bars)
# between recorded signals per symbol.
DEFAULT_MIN_GAP = 5


def _to_float(x) -> float | None:
    try:
        v = float(x)
        return None if np.isnan(v) else v
    except (TypeError, ValueError):
        return None


#: Exit models `_simulate_plan` understands (B-123). ``fixed`` is the default and
#: is the pre-B-123 behaviour bit for bit, so no published R changes. The others
#: MOVE the stop, which the harness could not express before -- every trailing
#: stop on the chart (PMax, SuperTrend AI, PSAR) had never been measured as an
#: exit by this harness.
EXIT_MODELS = ("fixed", "atr_trail", "ema_close", "structure")
_EXIT_DEFAULTS = {"atr_trail": 3.0, "ema_close": 20, "structure": 5}


def parse_exit_model(spec: str | None) -> tuple[str, float | None]:
    """``"atr_trail:3"`` -> ``("atr_trail", 3.0)``; ``None``/``"fixed"`` -> fixed.

    Unknown names RAISE rather than falling back to ``fixed`` -- a typo that
    silently measured the fixed plan would publish the control as the treatment
    (the same rule ``signal_mode`` follows)."""
    if spec is None:
        return "fixed", None
    name, _, arg = str(spec).strip().lower().partition(":")
    if name not in EXIT_MODELS:
        raise ValueError(f"exit_model must be one of {EXIT_MODELS}, got {spec!r}")
    if name == "fixed":
        return name, None
    val = float(arg) if arg else float(_EXIT_DEFAULTS[name])
    if val <= 0:
        raise ValueError(f"exit_model parameter must be positive, got {spec!r}")
    return name, val


#: Fill models (B-121). ``assumed`` is the pre-B-121 behaviour and the default,
#: for the same reason ``fixed`` is: every published R came through it.
FILL_MODELS = ("assumed", "market", "touch")
FILL_MAX_WAIT = 5


def resolve_fill(df: pd.DataFrame, signal_idx: int, entry: float, side: str,
                 fill_model: str = "assumed",
                 max_wait: int = FILL_MAX_WAIT) -> dict:
    """Where, and at what price, the card's entry would actually have filled.

    Before B-121 the harness simply assumed the card's ``entry`` filled on the
    bar after the signal, at that price, whether or not price ever traded there.
    Sampled on RELIANCE, `scan_flag_pole` returned entry 1469.68 on a bar that
    closed 1441.30 -- 2% above the market -- and the simulation credited the fill
    and measured the stop from it. ``order_block_rules_backtest.pending_limit_fill``
    already knew better; this brings that reasoning into the shared harness.

    * ``assumed`` -- the old behaviour: bar ``signal_idx+1``, at ``entry``.
    * ``market``  -- bar ``signal_idx+1``, at its OPEN. What acting on the card
      the next morning actually gets, whatever the card's number says.
    * ``touch``   -- the card's entry is an ORDER, and its type is read off where
      it sits relative to the signal bar's close. A long entry above the close is
      a BUY-STOP (fills when high reaches it; a gap through fills at the worse
      open); below the close it is a BUY-LIMIT (fills when low reaches it; a gap
      through fills at the better open). Shorts mirror. Waits ``max_wait`` bars,
      then the order is CANCELLED -- an unfilled order is a trade that did not
      happen, and it is counted, never simulated.

    Returns ``{"status": "filled", "idx", "px"}`` or ``{"status": "unfilled"}``.
    """
    if fill_model not in FILL_MODELS:
        raise ValueError(f"fill_model must be one of {FILL_MODELS}, got {fill_model!r}")
    n = len(df)
    nxt = signal_idx + 1
    if nxt >= n:
        return {"status": "unfilled"}
    if fill_model == "assumed":
        return {"status": "filled", "idx": nxt, "px": float(entry)}
    openp = df["open"].to_numpy(dtype=float)
    if fill_model == "market":
        return {"status": "filled", "idx": nxt, "px": float(openp[nxt])}
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    ref = float(df["close"].to_numpy(dtype=float)[signal_idx])
    short = str(side).lower() in ("short", "bear", "bearish", "down")
    # A stop order sits on the side price must MOVE TO; a limit on the side it
    # must come BACK to.
    stop_order = (entry <= ref) if short else (entry >= ref)
    for i in range(nxt, min(n, nxt + max_wait)):
        if short:
            if stop_order and low[i] <= entry:
                return {"status": "filled", "idx": i, "px": float(min(entry, openp[i]))}
            if not stop_order and high[i] >= entry:
                return {"status": "filled", "idx": i, "px": float(max(entry, openp[i]))}
        else:
            if stop_order and high[i] >= entry:
                return {"status": "filled", "idx": i, "px": float(max(entry, openp[i]))}
            if not stop_order and low[i] <= entry:
                return {"status": "filled", "idx": i, "px": float(min(entry, openp[i]))}
    return {"status": "unfilled"}


_EXIT_SERIES_CACHE: dict = {}


def _exit_series(df: pd.DataFrame, name: str, param: float) -> dict:
    """Per-bar series an exit model reads, computed once per (frame, model).

    Every value at index ``i`` uses bars ``<= i`` only. How a model consumes
    them is decided in `_simulate_plan`, where the lookahead argument is made."""
    key = (id(df), len(df), name, param)
    hit = _EXIT_SERIES_CACHE.get(key)
    if hit is not None:
        return hit
    if len(_EXIT_SERIES_CACHE) > 64:
        _EXIT_SERIES_CACHE.clear()
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    out: dict = {}
    if name == "atr_trail":
        # Chandelier's own lookback (22), Wilder smoothing.
        prev = close.shift(1)
        tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()],
                       axis=1).max(axis=1)
        out["atr"] = tr.ewm(alpha=1.0 / 22, adjust=False).mean().to_numpy()
    elif name == "ema_close":
        out["ema"] = close.ewm(span=int(param), adjust=False).mean().to_numpy()
    elif name == "structure":
        # A swing low at j needs `p` bars on EACH side, so it is only KNOWN at
        # bar j+p. `swing_low[i]` is the latest swing low confirmed by bar i --
        # reading the pivot at j would be lookahead by p bars.
        p = int(param)
        hv, lv = high.to_numpy(), low.to_numpy()
        n = len(df)
        known_low = np.full(n, np.nan)
        known_high = np.full(n, np.nan)
        last_l = last_h = np.nan
        for i in range(n):
            j = i - p
            if j - p >= 0:
                if lv[j] == lv[j - p:j + p + 1].min():
                    last_l = lv[j]
                if hv[j] == hv[j - p:j + p + 1].max():
                    last_h = hv[j]
            known_low[i] = last_l
            known_high[i] = last_h
        out["swing_low"], out["swing_high"] = known_low, known_high
    _EXIT_SERIES_CACHE[key] = out
    return out


def _simulate_plan(df: pd.DataFrame, entry_idx: int, entry: float,
                   stop: float, target: float, max_bars: int,
                   time_stop: float | None = None,
                   cost_model: CostModel | None = None,
                   side: str = "long",
                   exit_model: str | None = None) -> dict | None:
    """Stop-or-target-first walk forward from ``entry_idx`` (the entry bar).

    Conservative tie-break: if a single bar's range spans BOTH the stop and the
    target, assume the stop filled first (the pessimistic assumption — never
    credit the win we can't prove came first from daily bars).

    ``time_stop`` is the number of bars the SCANNER ITSELF declares a trade may
    run before being closed regardless of price — the missing time dimension in
    every structured plan (backlog B-5; [[concepts/Mean-Reversion]] names ~10
    bars as standard). When absent the trade simply runs to ``max_bars``, which
    is the measurement horizon rather than a decision, and the two are reported
    as different outcomes so a deliberate exit is never read as a stalled one.

    ``side`` is ``long`` or ``short`` (B-102). This was long-only until
    2026-09-20, and the cost of that was not a missing feature but a SILENT one:
    a short-side plan returned None and was counted as "unsimulatable", so a
    bearish scanner's R-block read as zero measurable plans rather than as a
    measurement nobody had built. Three studies had already written their own
    mirror to get around it (``flag_pole_edge.walk_plan``,
    ``order_block_rules_backtest.simulate``, and the stop study) — three chances
    for the pessimistic tie-break to drift apart.

    The short side is the exact MIRROR, never a sign flip applied to a long
    result: the stop is ABOVE the entry and is hit on ``high``, the target is
    BELOW and is hit on ``low``, and R is ``entry - exit``. A sign flip would
    have scored the short against the long's own stop/target ordering and
    credited the wrong bar.

    Returns None only for a DEGENERATE plan — one whose risk is zero or points
    the wrong way for the side it declares (a "long" whose stop sits above its
    entry is not a long, it is a typo). The caller counts those rather than
    letting them vanish.

    ``exit_model`` (B-123) -- ``fixed`` (default, unchanged), ``atr_trail:k``
    (Chandelier: extreme since entry - k*ATR22), ``ema_close:n`` (close through
    EMA n), ``structure:p`` (close through the latest CONFIRMED swing low/high,
    pivot length p -- the CHoCH that ends a long). Rules every moving model obeys:

    * **The initial stop still defines R and still fires intraday.** A trail can
      only TIGHTEN from it, never loosen -- ratchet-only.
    * **Model exits are CLOSE-based**, filled at that close. Touch-based trails
      are whippier ([[concepts/Capital-Management-Methods]]), and a close rule is
      the one a daily-bar trader can actually follow. The ATR trail, once it has
      ratcheted, is enforced as a resting stop (intraday), like Chandelier.
    * **The ATR trail used on bar i is computed from bars <= i-1.** Swing pivots
      already carry their p-bar confirmation delay. No bar exits on a level it
      helped set.
    * **The fixed target is DROPPED.** Letting winners run is the whole case for
      a trail; capping it at the card's target would measure a fixed plan with a
      tighter stop. The result carries ``target_used: False`` so it is visible.

    Outcomes add ``trail`` (a moving stop closed the trade).
    """
    model, param = parse_exit_model(exit_model)
    short = str(side).lower() in ("short", "bear", "bearish", "down")
    risk = (stop - entry) if short else (entry - stop)
    if risk <= 0:
        return None
    # A target on the STOP side of the entry is not a plan either (B-124): the
    # side is read off the stop, so an inverted stop turns a long into a "short"
    # whose target is then behind it, and every "target hit" books a loss.
    # Harmonic Butterfly/Crab cards did exactly this for a quarter of their
    # hits. Degenerate -> None -> counted as unsimulated, never scored.
    if (target >= entry) if short else (target <= entry):
        return None
    cm = cost_model or COST_GROSS
    n = len(df)
    if entry_idx >= n:
        return None
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)

    def _r(exit_px: float) -> float:
        gross = (entry - exit_px) if short else (exit_px - entry)
        return (gross - entry * cm.round_trip_pct(entry, exit_px) / 100.0) / risk

    horizon = max_bars if time_stop is None else min(max_bars, int(time_stop))
    end = min(n - 1, entry_idx + horizon)

    if model == "fixed":
        for i in range(entry_idx, end + 1):
            hit_stop = (high[i] >= stop) if short else (low[i] <= stop)
            hit_tgt = (low[i] <= target) if short else (high[i] >= target)
            if hit_stop:
                return {"outcome": "stop", "r": _r(stop), "bars": i - entry_idx}
            if hit_tgt:
                return {"outcome": "target", "r": _r(target), "bars": i - entry_idx}
        timed_out = time_stop is not None and (end - entry_idx) >= horizon
        return {"outcome": "time" if timed_out else "open",
                "r": _r(float(close[end])), "bars": end - entry_idx}

    ser = _exit_series(df, model, param)
    tag = f"{model}:{param:g}"
    extra = {"exit_model": tag, "target_used": False}
    live = stop          # ratchets from the initial stop, never loosens
    extreme = entry      # highest high (long) / lowest low (short) since entry
    for i in range(entry_idx, end + 1):
        # 1. The resting stop, intraday, at the level in force coming INTO bar i.
        if (high[i] >= live) if short else (low[i] <= live):
            return {"outcome": "stop" if live == stop else "trail",
                    "r": _r(live), "bars": i - entry_idx, **extra}
        # 2. The model's close-based exit on this bar.
        lvl = None
        if model == "ema_close":
            lvl = ser["ema"][i]
        elif model == "structure":
            lvl = ser["swing_high"][i] if short else ser["swing_low"][i]
        if lvl is not None and not np.isnan(lvl) and (
                (close[i] > lvl) if short else (close[i] < lvl)):
            return {"outcome": "trail", "r": _r(float(close[i])),
                    "bars": i - entry_idx, **extra}
        # 3. Ratchet for the NEXT bar, from information through bar i.
        if model == "atr_trail":
            extreme = min(extreme, low[i]) if short else max(extreme, high[i])
            a = ser["atr"][i]
            if not np.isnan(a):
                cand = extreme + param * a if short else extreme - param * a
                live = min(live, cand) if short else max(live, cand)
    timed_out = time_stop is not None and (end - entry_idx) >= horizon
    return {"outcome": "time" if timed_out else "open",
            "r": _r(float(close[end])), "bars": end - entry_idx, **extra}


def absolute_move(df: pd.DataFrame, entry_idx: int, horizon: int,
                  cost_model: CostModel | None = None) -> float | None:
    """|forward move| over ``horizon`` bars, in percent, net of a round trip.

    The measurement a BILATERAL pattern needs (B-102, for B-101's symmetrical
    triangle). A coil claims no direction, so a directional edge near zero is
    what it SHOULD produce and grading it on one says nothing about whether the
    detector works. What a coil DOES claim is expansion: that price is about to
    leave a range it has been compressing inside. That claim is directionless,
    and this is its unit.

    Entry is the NEXT bar's open, exit the close ``horizon`` bars later — the
    same timing every other signal in this file uses, so a coil and a breakout
    are measured on the same clock. Costs are subtracted from the absolute move
    rather than added to it: a move has to beat the round trip to be worth
    anything, whichever way it went. The caller applies this identically to
    signal and baseline bars, which is what keeps the comparison fair.
    """
    close = df["close"].to_numpy(dtype=float)
    openp = (df["open"].to_numpy(dtype=float) if "open" in df.columns else close)
    t = entry_idx
    if t + 1 + horizon > len(close) - 1:
        return None
    entry = float(openp[t + 1])
    if entry <= 0:
        return None
    exit_px = float(close[t + 1 + horizon])
    cm = cost_model or COST_GROSS
    return abs((exit_px / entry - 1.0) * 100.0) - cm.round_trip_pct(entry, exit_px)


def _resolve_cost(cost_bps: float = 0,
                  cost_model: CostModel | None = None) -> CostModel:
    if cost_model is not None:
        return cost_model
    return FlatCost(cost_bps) if cost_bps else COST_GROSS


def backtest_scanner(scanner_name: str,
                     symbols: list[str],
                     fetch_fn,
                     horizons: tuple[int, ...] = DEFAULT_HORIZONS,
                     min_gap: int = DEFAULT_MIN_GAP,
                     warmup: int = WARMUP_BARS,
                     stride: int = 1,
                     benchmark_df: "pd.DataFrame | None" = None,
                     cost_bps: float = 0,
                     cost_model: CostModel | None = None,
                     signal_mode: str = "all",
                     exit_model: str | None = None,
                     fill_model: str = "assumed",
                     honor_time_stop: bool = True,
                     keep_trades: bool = False,
                     _record_frac: "tuple[float, float] | None" = None) -> dict:
    """Replay ``scanner_name`` over ``symbols`` and return aggregate metrics.

    ``cost_model`` — a ``CostModel`` instance (``COST_INDIAN`` for realistic NSE
    delivery costs, ``FlatCost(bps)`` for a flat haircut).  Overrides ``cost_bps``
    when given.  Costs are applied to BOTH signal and baseline returns so the
    edge comparison is fair.

    ``signal_mode`` — ``all`` (every bar the scanner returns a hit, de-duplicated
    by ``min_gap``) or ``fresh`` (only the bar a hit APPEARS, i.e. the previous
    evaluated bar had none). **The default stays ``all`` on purpose**: every
    number this desk has published came through that path, and flipping the
    default would silently redefine 44 verdicts rather than re-measure them.
    The mode is reported in the result so no figure is ever quoted without it
    (B-120).
    """
    if signal_mode not in ("all", "fresh"):
        raise ValueError(f"signal_mode must be 'all' or 'fresh', got {signal_mode!r}")
    _em, _ep = parse_exit_model(exit_model)          # raises on a typo, up front
    exit_tag = "fixed" if _em == "fixed" else f"{_em}:{_ep:g}"
    if fill_model not in FILL_MODELS:              # same: fail before the work
        raise ValueError(f"fill_model must be one of {FILL_MODELS}, got {fill_model!r}")
    n_unfilled = 0          # orders that never traded -- not trades, not dropped
    n_fill_through = 0      # filled at or beyond the stop: no risk left to measure
    n_fill_past_target = 0  # filled at or beyond the target: nothing left to make
    n_not_actionable = 0    # plans on cards that declare themselves not a trade (B-128)
    slip_pct: list[float] = []   # adverse gap between the card's entry and the fill
    # B-124 hooks. `keep_trades` returns every simulated trade keyed by
    # (symbol, signal bar) so two exit arms can be PAIRED on identical entries
    # and clustered by symbol. `honor_time_stop=False` lets a moving-stop arm run
    # to the measurement horizon instead of the card's own time stop -- the
    # B-123 smoke showed the card's time stop ending 26-39 of 127 trades under
    # every trail, capping exactly the tail a trail is for.
    trades: list[dict] = []
    spec = sc.SCANNERS.get(scanner_name)
    if spec is None:
        return {"error": f"unknown scanner '{scanner_name}'"}
    fn = spec["fn"]
    max_h = max(horizons)
    cm = _resolve_cost(cost_bps, cost_model)

    sig_ret: dict[int, list[float]] = {h: [] for h in horizons}
    base_ret: dict[int, list[float]] = {h: [] for h in horizons}
    # Market-model: parallel lists for the benchmark return and estimated alpha
    # at each signal, per horizon.  Only populated when benchmark_df is supplied.
    mkt_ret: dict[int, list[float]] = {h: [] for h in horizons}
    alpha_ret: dict[int, list[float]] = {h: [] for h in horizons}
    mae_list: list[float] = []           # max adverse excursion per signal (%)
    r_results: list[dict] = []
    n_signals = 0
    n_symbols_used = 0
    total_bars = 0
    n_plans = 0                 # signals that carried a full entry/stop/target
    n_plans_unsimulated = 0     # …of which the long-only sim could not run

    # Pre-process benchmark into a date→close map for fast lookups.
    bench_close: pd.Series | None = None
    if benchmark_df is not None and "close" in benchmark_df.columns:
        bench_close = benchmark_df["close"].dropna()

    for sym in symbols:
        try:
            df = fetch_fn(sym)
        except Exception:
            continue
        if df is None or df.empty:
            continue
        # Keep the DATES before the reset throws them away. Every scanner here
        # works in bar offsets, so the positional index is what the rest of this
        # loop needs — but the market model joins to the benchmark BY DATE, and
        # after `reset_index(drop=True)` there are no dates left to join on.
        # The guard below used to read `hasattr(df.index, "date")`, which is
        # False for the RangeIndex this line produces, so the whole alpha/beta
        # block was unreachable: `alpha_avg` and `alpha_ttest` came back None on
        # every run, including the five dashboard call sites that pass a
        # benchmark. Nothing errored and nothing said so (B-104).
        _dates = df.index if isinstance(df.index, pd.DatetimeIndex) else None
        df = df.dropna(subset=["high", "low", "close", "volume"]).reset_index(drop=True)
        if _dates is not None and len(_dates) != len(df):
            _dates = None          # NaN rows were dropped; the alignment is gone
        n = len(df)
        if n < warmup + max_h + 2:
            continue
        n_symbols_used += 1
        has_open = "open" in df.columns
        close = df["close"].to_numpy(dtype=float)
        low = df["low"].to_numpy(dtype=float)
        openp = df["open"].to_numpy(dtype=float) if has_open else close

        # Baseline: every eligible bar's forward returns (random entry in-tape).
        # Entry at t+1 open, exit at t+1+h close — identical timing to signals.
        last_eval = n - max_h - 2

        # _record_frac: restrict which bars are counted (for walk-forward windows).
        # The scanner still evaluates all bars for lookback; only recording is gated.
        eval_span = last_eval - warmup + 1
        if _record_frac is not None:
            rec_start = warmup + int(eval_span * _record_frac[0])
            rec_end = warmup + int(eval_span * _record_frac[1])
        else:
            rec_start = warmup
            rec_end = last_eval + 1

        for t in range(rec_start, min(rec_end, last_eval + 1)):
            total_bars += 1
            entry_b = openp[t + 1]
            if entry_b <= 0:
                continue
            for h in horizons:
                fwd = close[t + 1 + h]
                cost_pct = cm.round_trip_pct(entry_b, fwd)
                base_ret[h].append((fwd / entry_b - 1.0) * 100.0 - cost_pct)

        # Signals: walk the record window, feed point-in-time slices.
        # Scanner sees df.iloc[:t+1] (full lookback); only the record range counts.
        t = rec_start
        prev_hit = False            # B-120: was the PREVIOUS evaluated bar a hit?
        while t < rec_end and t <= last_eval:
            if stride > 1 and (t - warmup) % stride != 0:
                t += 1
                continue
            try:
                hit = fn(df.iloc[:t + 1])
            except Exception:
                hit = None
            if not hit:
                prev_hit = False
                t += 1
                continue

            # B-120 — a persisting STATE is not a new signal every bar. Most
            # detectors here describe a condition that stays true for a while:
            # `scan_flag_pole` fires on runs of ~4 consecutive bars (longest
            # measured 8), so "all" mode enters the same breakout four times at
            # four different prices. That is defensible for an EDGE question
            # ("do bars in this state outperform?") and indefensible for a PLAN
            # question ("was the stated target reachable from the stated
            # entry?") — which is why every study that cared wrote its own
            # freshness rule (flag_pole_edge, bilateral_expansion, sbc_reading).
            if signal_mode == "fresh" and prev_hit:
                prev_hit = True
                t += 1
                continue
            prev_hit = True

            n_signals += 1
            entry_idx = t + 1
            entry_b = openp[entry_idx]
            if entry_b > 0:
                # ── market-model beta from the 60-bar pre-signal window ──────
                _beta: float | None = None
                if bench_close is not None and _dates is not None:
                    try:
                        _lo = max(0, t - 60)
                        _sym_px = pd.Series(close[_lo: t + 1], index=_dates[_lo: t + 1])
                        _sym_r = _sym_px.pct_change().dropna()
                        # Align benchmark returns to the same dates
                        _b_px = bench_close.reindex(_sym_r.index, method="nearest",
                                                     tolerance=pd.Timedelta("2D"))
                        _b_r = _b_px.pct_change().dropna()
                        _both = pd.concat([_sym_r, _b_r], axis=1).dropna()
                        if len(_both) >= 20:
                            _beta = float(
                                np.cov(_both.iloc[:, 0], _both.iloc[:, 1])[0, 1]
                                / max(np.var(_both.iloc[:, 1]), 1e-12)
                            )
                    except Exception:
                        _beta = None

                for h in horizons:
                    fwd = close[entry_idx + h]
                    cost_pct = cm.round_trip_pct(entry_b, fwd)
                    sr = (fwd / entry_b - 1.0) * 100.0 - cost_pct
                    sig_ret[h].append(sr)

                    # Market return for the same forward window (by date index)
                    if bench_close is not None and _dates is not None:
                        try:
                            _entry_date = _dates[entry_idx]
                            _exit_date = _dates[min(entry_idx + h, len(df) - 1)]
                            _b_entry = float(bench_close.asof(_entry_date))
                            _b_exit = float(bench_close.asof(_exit_date))
                            _mr = (_b_exit / _b_entry - 1.0) * 100.0
                            mkt_ret[h].append(_mr)
                            # alpha = raw_ret - β × mkt_ret; fall back to β=1 if unknown
                            _b = _beta if _beta is not None else 1.0
                            alpha_ret[h].append(sr - _b * _mr)
                        except Exception:
                            pass

                # Max adverse excursion over the longest horizon.
                window_low = float(np.min(low[entry_idx:entry_idx + max_h + 1]))
                mae_list.append((window_low / entry_b - 1.0) * 100.0)

                # R-simulation when the scanner emitted a trade plan.
                entry_p = _to_float(hit.get("entry"))
                stop_p = _to_float(hit.get("stop"))
                tgt = hit.get("target")
                tgt_p = _to_float(tgt[0] if isinstance(tgt, (list, tuple)) and tgt else tgt)
                if entry_p and stop_p and tgt_p and hit.get("actionable") is False:
                    # B-128. The card says its state is not a trade -- a flag not
                    # yet broken, a wedge still forming. Its SIGNAL return above
                    # stays measured (that is the pattern); its PLAN is counted
                    # and never simulated. Before this, Flag & Pole's plan R was
                    # -0.43 with WATCH cards traded and +0.26 without them.
                    n_not_actionable += 1
                elif entry_p and stop_p and tgt_p:
                    n_plans += 1
                    # The SIDE is read off the plan's own geometry (B-102). A stop
                    # ABOVE the entry is a short — there is no other way to read
                    # it — so a bearish scanner's plans are now simulated instead
                    # of counted as unsimulatable. Inferring from the levels beats
                    # trusting a `direction` key most cards do not carry.
                    _side = "short" if stop_p > entry_p else "long"
                    fill = resolve_fill(df, t, entry_p, _side, fill_model)
                    if fill["status"] != "filled":
                        n_unfilled += 1
                        t += 1 if signal_mode == "fresh" else min_gap
                        continue
                    f_idx, f_px = fill["idx"], fill["px"]
                    through = (f_px >= stop_p) if _side == "short" else (f_px <= stop_p)
                    # Filled already PAST the target: the move the card projected
                    # happened before the order did. Scoring it would book a
                    # "target hit" at a price worse than the fill -- a loss with a
                    # winner's label (B-124). Counted beside fill-through-stop.
                    past_tgt = (f_px <= tgt_p) if _side == "short" else (f_px >= tgt_p)
                    if past_tgt and not through:
                        n_fill_past_target += 1
                        t += 1 if signal_mode == "fresh" else min_gap
                        continue
                    if through:
                        n_fill_through += 1
                        t += 1 if signal_mode == "fresh" else min_gap
                        continue
                    slip_pct.append(((f_px - entry_p) if _side == "long"
                                     else (entry_p - f_px)) / entry_p * 100.0)
                    _ts = _to_float(hit.get("time_stop"))
                    if not honor_time_stop and _em != "fixed":
                        _ts = None
                    r = _simulate_plan(df, f_idx, f_px, stop_p, tgt_p,
                                       max_h, _ts,
                                       cost_model=cm, side=_side,
                                       exit_model=exit_model)
                    if r:
                        r_results.append(r)
                        if keep_trades:
                            trades.append({"symbol": sym, "t": int(t),
                                           "side": _side, **r})
                    else:
                        # Degenerate plans (zero risk) are counted, not dropped,
                        # so the report can say how much of the plan coverage it
                        # could actually measure.
                        n_plans_unsimulated += 1

            # In "all" mode min_gap IS the de-duplication. In "fresh" mode the
            # transition rule already did it, and skipping ahead would throw
            # away a genuine new break that happens within min_gap bars.
            t += 1 if signal_mode == "fresh" else min_gap

    out = _aggregate(scanner_name, horizons, sig_ret, base_ret, mae_list,
                     r_results, n_signals, n_symbols_used, total_bars,
                     n_plans, n_plans_unsimulated,
                     mkt_ret=mkt_ret, alpha_ret=alpha_ret,
                     cost_model=cm)
    out["signal_mode"] = signal_mode
    out["exit_model"] = exit_tag
    out["fill_model"] = fill_model
    out["honor_time_stop"] = bool(honor_time_stop)
    if keep_trades:
        out["trades"] = trades
    rb = out.get("r_metrics")
    if (isinstance(rb, dict) or n_unfilled or n_fill_through or n_fill_past_target
            or n_not_actionable):
        rb = rb if isinstance(rb, dict) else {"n_with_plan": 0,
                                              "plans_seen": int(n_plans)}
        # Counted, never dropped: a fill model that silently shrank the sample
        # would look like a cleaner result rather than a smaller one.
        rb["plans_unfilled"] = int(n_unfilled)
        rb["plans_fill_through_stop"] = int(n_fill_through)
        rb["plans_fill_past_target"] = int(n_fill_past_target)
        rb["plans_not_actionable"] = int(n_not_actionable)
        rb["avg_slippage_pct"] = (round(float(np.mean(slip_pct)), 3)
                                  if slip_pct else None)
        out["r_metrics"] = rb
    return out


def walk_forward_scanner(scanner_name: str,
                         symbols: list[str],
                         fetch_fn,
                         n_windows: int = 3,
                         horizons: tuple[int, ...] = DEFAULT_HORIZONS,
                         cost_bps: float = 0,
                         cost_model: CostModel | None = None,
                         **kwargs) -> dict:
    """Run ``backtest_scanner`` over non-overlapping time windows (B-21).

    Each window's signals are out-of-sample relative to the others.  The pooled
    result aggregates the per-window metrics (weighted by signal count) rather
    than re-running the full tape — so "pooled" is a true OOS aggregate, not an
    in-sample number.
    """
    cm = _resolve_cost(cost_bps, cost_model)
    windows = []
    for i in range(n_windows):
        frac = (i / n_windows, (i + 1) / n_windows)
        r = backtest_scanner(scanner_name, symbols, fetch_fn,
                             horizons=horizons, cost_model=cm,
                             _record_frac=frac, **kwargs)
        r["window"] = i + 1
        r["window_frac"] = frac
        windows.append(r)

    # Pool by signal-count-weighted average of per-window metrics (OOS aggregate).
    pooled_horizons = {}
    total_signals = sum(w.get("n_signals", 0) for w in windows)
    total_symbols = max(w.get("n_symbols_used", 0) for w in windows)
    total_baseline = sum(w.get("baseline_bars", 0) for w in windows)
    for h in horizons:
        n_total = 0
        weighted_avg = 0.0
        weighted_base = 0.0
        weighted_hit = 0.0
        all_edges = []
        for w in windows:
            m = w.get("horizons", {}).get(h, {})
            n = m.get("n", 0)
            if n == 0:
                continue
            n_total += n
            weighted_avg += m.get("avg_ret", 0) * n
            weighted_base += m.get("baseline_avg", 0) * n
            weighted_hit += m.get("hit_rate", 0) * n
            all_edges.append(m.get("edge", 0) or 0)
        if n_total > 0:
            avg_ret = weighted_avg / n_total
            base_avg = weighted_base / n_total
            pooled_horizons[h] = {
                "n": n_total,
                "avg_ret": round(avg_ret, 2),
                "baseline_avg": round(base_avg, 2),
                "edge": round(avg_ret - base_avg, 2),
                "hit_rate": round(weighted_hit / n_total, 1),
            }
        else:
            pooled_horizons[h] = {"n": 0}

    pooled = {
        "scanner": scanner_name,
        "n_signals": total_signals,
        "n_symbols_used": total_symbols,
        "baseline_bars": total_baseline,
        "thin_sample": total_signals < MIN_SAMPLE,
        "horizons": pooled_horizons,
        "r_metrics": None,
        "mae_avg": None,
        "limitations": windows[0].get("limitations", []) if windows else [],
        "cost_label": cm.label,
    }

    # Stability: per-horizon sign consistency.
    stability_per_h = {}
    for h in horizons:
        edges = []
        for w in windows:
            m = w.get("horizons", {}).get(h, {})
            edges.append(m.get("edge", 0) or 0)
        n_pos = sum(1 for e in edges if e > 0)
        stable = n_pos == n_windows or n_pos == 0
        stability_per_h[h] = {
            "window_edges": [round(e, 2) for e in edges],
            "n_positive": n_pos,
            "stable": stable,
        }

    all_stable = all(s["stable"] for s in stability_per_h.values())
    any_stable = any(s["stable"] for s in stability_per_h.values())

    # Degradation: pooled edge vs best single window.
    ref_h = max(horizons)
    pooled_edge = pooled["horizons"].get(ref_h, {}).get("edge", 0) or 0
    best_window_edge = max(
        (w.get("horizons", {}).get(ref_h, {}).get("edge", 0) or 0 for w in windows),
        default=0)
    degradation = round(pooled_edge - best_window_edge, 2) if best_window_edge else 0

    if all_stable:
        verdict = "STABLE — edge sign consistent at all horizons"
    elif any_stable:
        stable_hs = [h for h, s in stability_per_h.items() if s["stable"]]
        verdict = f"MIXED — stable at {stable_hs}, unstable at others"
    else:
        verdict = "UNSTABLE — edge sign inconsistent at every horizon"

    # B-116 — carry the TRADE PLAN's own scoreboard out of the walk-forward path.
    # `_aggregate` has always built this per window (target_hits, stop_hits,
    # win_rate, avg_R, expectancy_R) and `format_report` has always printed it,
    # but `walk_forward_scanner` dropped it on the floor — so the B-19 batch,
    # which runs through here, computed target-vs-stop for 44 scanners and threw
    # it away 44 times. Every saved verdict in cache/b19_verdicts/ shows edges
    # and stability and not one R line.
    #
    # Pooled by SUMMING counts rather than averaging rates: three windows with
    # 4, 40 and 400 plans are not three equal opinions about a hit rate.
    # `_aggregate` stores it under "r_metrics". Reading "r_block" here (the
    # local variable's name inside `_aggregate`) silently pooled nothing and the
    # report printed no line at all — a wrong key that looks exactly like "this
    # scanner has no plans". The end-to-end test exists because of it.
    plans = _pool_r_blocks([w.get("r_metrics") for w in windows])

    return {
        "scanner": scanner_name,
        "n_windows": n_windows,
        "windows": windows,
        "pooled": pooled,
        "plans": plans,
        # Reported, never assumed: a hit rate from "all" and one from "fresh"
        # answer different questions, so the number never travels without it.
        "signal_mode": (windows[0].get("signal_mode", "all") if windows else "all"),
        "exit_model": (windows[0].get("exit_model", "fixed") if windows else "fixed"),
        "fill_model": (windows[0].get("fill_model", "assumed") if windows else "assumed"),
        "stability": {
            "per_horizon": stability_per_h,
            "all_stable": all_stable,
            "verdict": verdict,
        },
        "degradation": {
            "ref_horizon": ref_h,
            "pooled_edge": round(pooled_edge, 2),
            "best_window_edge": round(best_window_edge, 2),
            "gap": degradation,
        },
        "cost_label": cm.label,
    }


def _pool_r_blocks(blocks: "list[dict | None]") -> dict | None:
    """Sum the per-window plan scoreboards into one, or None when there are none.

    Counts sum; rates are recomputed from the sums. Averaging three windows'
    win rates would give a 4-plan window the same say as a 400-plan one, which
    is the error this function exists to not make.
    """
    # Unfilled / fill-through counts come from EVERY window (B-121): a window
    # where no order filled has n_with_plan 0 and is dropped below, and its
    # unfilled orders would otherwise vanish with it.
    raw = [b for b in blocks if b]
    unf = sum(int(b.get("plans_unfilled") or 0) for b in raw)
    fth = sum(int(b.get("plans_fill_through_stop") or 0) for b in raw)
    fpt = sum(int(b.get("plans_fill_past_target") or 0) for b in raw)
    nna = sum(int(b.get("plans_not_actionable") or 0) for b in raw)
    blocks = [b for b in raw if int(b.get("n_with_plan") or 0) > 0]
    if not blocks:
        # This used to read `seen = 0 ... if seen else None` -- always None, so a
        # run where plans were SEEN but none simulated (or, since B-121, none
        # FILLED) pooled to nothing and the report printed no plan line at all.
        seen = sum(int(b.get("plans_seen") or 0) for b in raw)
        if not (seen or unf or fth or nna):
            return None
        return {"n_with_plan": 0, "plans_seen": seen,
                "plans_unfilled": unf, "plans_fill_through_stop": fth,
                "plans_fill_past_target": fpt,
                "plans_not_actionable": nna,
                "plans_unsimulated": sum(int(b.get("plans_unsimulated") or 0)
                                         for b in raw)}
    n = sum(int(b["n_with_plan"]) for b in blocks)
    tgt = sum(int(b.get("target_hits") or 0) for b in blocks)
    stp = sum(int(b.get("stop_hits") or 0) for b in blocks)
    opn = sum(int(b.get("open_exits") or 0) for b in blocks)
    tme = sum(int(b.get("time_exits") or 0) for b in blocks)
    trl = sum(int(b.get("trail_exits") or 0) for b in blocks)
    # positive_rate is stored in PERCENT per window; pool it by plan count.
    pos = sum(float(b.get("positive_rate") or 0.0) / 100.0 * int(b["n_with_plan"])
              for b in blocks)
    # avg_R weighted by the plans behind it, for the same reason.
    tot_r = sum(float(b.get("avg_R") or 0.0) * int(b["n_with_plan"]) for b in blocks)
    return {
        "n_with_plan": n,
        "target_hits": tgt, "stop_hits": stp,
        "open_exits": opn, "time_exits": tme, "trail_exits": trl,
        "plans_unfilled": unf, "plans_fill_through_stop": fth,
        "plans_fill_past_target": fpt,
        "plans_not_actionable": nna,
        "positive_rate": round(pos / n, 3),
        "target_rate": round(tgt / n, 3),
        "stop_rate": round(stp / n, 3),
        "win_rate": round(tgt / n, 3),
        "avg_R": round(tot_r / n, 3),
        "plans_seen": sum(int(b.get("plans_seen") or 0) for b in blocks),
        "plans_unsimulated": sum(int(b.get("plans_unsimulated") or 0) for b in blocks),
    }


def format_walk_forward(result: dict) -> str:
    """Human-readable report for walk_forward_scanner."""
    lines = []
    cost_note = result.get("cost_label", "GROSS")
    mode = result.get("signal_mode", "all")
    lines.append(f"=== Walk-Forward: {result['scanner']} "
                 f"({result['n_windows']} windows, {cost_note}, "
                 f"signals={mode}, exit={result.get('exit_model', 'fixed')}, "
                 f"fill={result.get('fill_model', 'assumed')}) ===")
    if result.get("exit_model", "fixed") != "fixed":
        lines.append(f"exit: {result['exit_model']} -- a MOVING stop, target "
                     "dropped; plan R is not comparable to a fixed-exit run (B-123)")
    if mode == "fresh":
        lines.append("signals: FRESH only — a state that persists counts ONCE, "
                     "on the bar it appears (B-120)")
    lines.append("")

    horizons = list(result["pooled"]["horizons"].keys())

    hdr = f"{'window':>7}  {'signals':>8}  " + "  ".join(
        f"{'edge@'+str(h)+'d':>10}" for h in horizons)
    lines.append(hdr)
    for w in result["windows"]:
        cols = [f"{w['window']:>7}", f"{w['n_signals']:>8}"]
        for h in horizons:
            m = w["horizons"].get(h, {})
            e = m.get("edge")
            tt = (m.get("edge_ttest") or {})
            sig = "*" if tt.get("reliable") else " "
            cols.append(f"{(f'{e:+.2f}' if e is not None else '   n/a'):>9}{sig}")
        lines.append("  ".join(cols))

    # Pooled (OOS aggregate)
    cols = [f"{'OOS':>7}", f"{result['pooled']['n_signals']:>8}"]
    for h in horizons:
        m = result["pooled"]["horizons"].get(h, {})
        e = m.get("edge")
        cols.append(f"{(f'{e:+.2f}' if e is not None else '   n/a'):>9} ")
    lines.append("  ".join(cols))

    lines.append("")
    stab = result["stability"]
    lines.append(f"stability: {stab['verdict']}")
    for h, s in stab.get("per_horizon", {}).items():
        tag = "✓" if s["stable"] else "✗"
        lines.append(f"  @{h}d: {tag} edges={s['window_edges']} "
                     f"({s['n_positive']}/{result['n_windows']} positive)")

    deg = result.get("degradation", {})
    if deg:
        lines.append(f"degradation @{deg['ref_horizon']}d: "
                     f"pooled {deg['pooled_edge']:+.2f} vs best-window "
                     f"{deg['best_window_edge']:+.2f} (gap {deg['gap']:+.2f})")

    # The plan's own scoreboard. An edge says the SIGNAL preceded a move; this
    # says whether the TARGET the card prints was reachable before the stop —
    # a different claim, and the one a reader acts on (B-116).
    pl = result.get("plans") or {}
    if pl.get("n_with_plan"):
        lines.append("")
        lines.append(
            f"plan (target vs stop): {pl['n_with_plan']} simulated · "
            f"target {pl['target_rate']:.1%} · stop {pl['stop_rate']:.1%} · "
            f"open {pl['open_exits']} · timed out {pl['time_exits']} · "
            + (f"trailed out {pl['trail_exits']} · " if pl.get("trail_exits") else "")
            + f"R>0 {pl.get('positive_rate', 0):.1%} · "
            f"avg {pl['avg_R']:+.2f}R")
        if pl.get("plans_not_actionable"):
            lines.append(f"  ({pl['plans_not_actionable']} plans on WATCH / forming "
                         f"cards -- counted, not traded; B-128)")
        if pl.get("plans_unfilled") or pl.get("plans_fill_through_stop"):
            lines.append(f"  ({pl.get('plans_unfilled', 0)} orders never filled, "
                         f"{pl.get('plans_fill_through_stop', 0)} filled through "
                         f"the stop -- counted, not simulated; B-121)")
        if pl.get("plans_unsimulated"):
            lines.append(f"  ({pl['plans_unsimulated']} plans could not be "
                         f"simulated — degenerate levels)")
    elif pl.get("plans_seen"):
        lines.append("")
        lines.append(f"plan: {pl['plans_seen']} seen, none simulatable"
                     + (f" ({pl['plans_unfilled']} never filled)"
                        if pl.get("plans_unfilled") else ""))

    lines.append(f"  (* = p<0.05 two-tailed)")
    return "\n".join(lines)


def _ttest_1samp(arr: np.ndarray, null: float = 0.0):
    """One-sample t-test, scipy-optional.  Returns (t, p)."""
    n = len(arr)
    mean = float(np.mean(arr))
    se = float(np.std(arr, ddof=1)) / np.sqrt(n)
    if se < 1e-15:
        return 0.0, 1.0
    t_val = (mean - null) / se
    if _scipy_stats is not None:
        p_val = float(_scipy_stats.t.sf(abs(t_val), df=n - 1) * 2)
    else:
        from math import erfc, sqrt
        p_val = erfc(abs(t_val) / sqrt(2))
    return t_val, p_val


def _ttest_ind(a: np.ndarray, b: np.ndarray, alternative: str = "two-sided"):
    """Two-sample Welch t-test, scipy-optional.  Returns (t, p)."""
    if _scipy_stats is not None:
        t_val, p_val = _scipy_stats.ttest_ind(a, b, equal_var=False,
                                               alternative=alternative)
        return float(t_val), float(p_val)
    na, nb = len(a), len(b)
    ma, mb = float(np.mean(a)), float(np.mean(b))
    va = float(np.var(a, ddof=1))
    vb = float(np.var(b, ddof=1))
    se = np.sqrt(va / na + vb / nb)
    if se < 1e-15:
        return 0.0, 1.0
    t_val = (ma - mb) / se
    from math import erfc, sqrt
    p_val = erfc(abs(t_val) / sqrt(2))
    if alternative == "greater":
        p_val = p_val / 2 if t_val > 0 else 1.0 - p_val / 2
    return t_val, p_val


def _ttest_edge(arr: np.ndarray, null: float = 0.0) -> dict:
    """One-sample t-test: H0 = mean equals null.  Returns t, p, 95% CI."""
    n = len(arr)
    if n < 4:
        return {"t": None, "p": None, "ci95": None, "reliable": False}
    t_val, p_val = _ttest_1samp(arr, null)
    mean = float(np.mean(arr))
    se = float(np.std(arr, ddof=1)) / np.sqrt(n)
    if _scipy_stats is not None:
        ci = _scipy_stats.t.interval(0.95, df=n - 1, loc=mean, scale=se)
        ci_lo, ci_hi = float(ci[0]), float(ci[1])
    else:
        ci_lo = mean - 1.96 * se
        ci_hi = mean + 1.96 * se
    return {
        "t": round(t_val, 3),
        "p": round(p_val, 4),
        "ci95": [round(ci_lo, 3), round(ci_hi, 3)],
        "reliable": bool(p_val < 0.05),
        "approx": _scipy_stats is None,
    }


def _aggregate(scanner_name, horizons, sig_ret, base_ret, mae_list, r_results,
               n_signals, n_symbols_used, total_bars,
               n_plans=0, n_plans_unsimulated=0,
               mkt_ret=None, alpha_ret=None,
               cost_model: CostModel | None = None) -> dict:
    per_h = {}
    for h in horizons:
        s = np.array(sig_ret[h], dtype=float)
        b = np.array(base_ret[h], dtype=float)
        if len(s) == 0:
            per_h[h] = {"n": 0}
            continue
        sig_avg = float(np.mean(s))
        base_avg = float(np.mean(b)) if len(b) else 0.0
        edge_arr = s - base_avg          # each signal's excess over the random-entry mean

        m: dict = {
            "n": int(len(s)),
            "hit_rate": round(float(np.mean(s > 0) * 100), 1),
            "avg_ret": round(sig_avg, 2),
            "median_ret": round(float(np.median(s)), 2),
            "baseline_avg": round(base_avg, 2),
            "edge": round(sig_avg - base_avg, 2),      # signal minus random-entry
            "baseline_hit_rate": round(float(np.mean(b > 0) * 100), 1) if len(b) else None,
            # B-20a — significance: is the edge distinguishable from noise?
            "edge_ttest": _ttest_edge(edge_arr),
        }

        # B-20b — market-model alpha when benchmark data was supplied.
        a_arr = np.array((alpha_ret or {}).get(h, []), dtype=float)
        if len(a_arr) >= 4:
            m["alpha_avg"] = round(float(np.mean(a_arr)), 2)
            m["alpha_ttest"] = _ttest_edge(a_arr)
        else:
            m["alpha_avg"] = None
            m["alpha_ttest"] = None

        per_h[h] = m

    r_block = None
    if not r_results and n_plans:
        # Every plan was unsimulatable. Report that explicitly — an empty R block
        # would otherwise be indistinguishable from a scanner emitting no plans.
        r_block = {"n_with_plan": 0, "plans_seen": int(n_plans),
                   "plans_unsimulated": int(n_plans_unsimulated),
                   "note": "no plan could be simulated long-only (short-side or degenerate)"}
    elif r_results:
        rs = np.array([x["r"] for x in r_results], dtype=float)
        wins = np.array([x["outcome"] == "target" for x in r_results])
        r_block = {
            "n_with_plan": int(len(rs)),
            "win_rate": round(float(np.mean(wins) * 100), 1),
            "avg_R": round(float(np.mean(rs)), 2),
            "expectancy_R": round(float(np.mean(rs)), 2),   # avg R per trade
            "target_hits": int(np.sum([x["outcome"] == "target" for x in r_results])),
            "stop_hits": int(np.sum([x["outcome"] == "stop" for x in r_results])),
            "open_exits": int(np.sum([x["outcome"] == "open" for x in r_results])),
            "time_exits": int(np.sum([x["outcome"] == "time" for x in r_results])),
            # B-123. A moving stop closes trades as "trail", which none of the
            # four counts above sees -- without this key those exits silently
            # vanish from the tallies. And under a trail there IS no target, so
            # win_rate (= target hit) reads 0% by construction; `positive_rate`
            # (R > 0) is the win rate that means the same thing under every
            # exit model, and `r_p90` is the right tail a trail exists to fatten.
            "trail_exits": int(np.sum([x["outcome"] == "trail" for x in r_results])),
            "positive_rate": round(float(np.mean(rs > 0) * 100), 1),
            "r_p90": round(float(np.percentile(rs, 90)), 2),
            # Plan coverage. Without these two a scanner whose plans are all
            # short-side would report an empty R block indistinguishable from one
            # that emits no plans at all.
            "plans_seen": int(n_plans),
            "plans_unsimulated": int(n_plans_unsimulated),
        }

    cm = cost_model or COST_GROSS
    lims = ["survivorship-bias", "history-depth-varies"]
    if not isinstance(cm, FlatCost) or cm.bps > 0:
        lims.append(f"costs: {cm.label}")
    else:
        lims.append("no-costs-slippage")

    return {
        "scanner": scanner_name,
        "n_signals": n_signals,
        "n_symbols_used": n_symbols_used,
        "baseline_bars": total_bars,
        "thin_sample": n_signals < MIN_SAMPLE,
        "horizons": per_h,
        "r_metrics": r_block,
        "mae_avg": round(float(np.mean(mae_list)), 2) if mae_list else None,
        "limitations": lims,
        "cost_label": cm.label,
    }


def format_report(result: dict) -> str:
    """Human-readable text report for one backtest result."""
    if "error" in result:
        return f"ERROR: {result['error']}"
    lines = []
    warn = "  ⚠ THIN SAMPLE — treat as directional only" if result["thin_sample"] else ""
    cost_note = f"  cost={result.get('cost_label', 'GROSS')}"
    lines.append(f"=== {result['scanner']} ===")
    lines.append(f"signals={result['n_signals']}  symbols={result['n_symbols_used']}  "
                 f"baseline-bars={result['baseline_bars']}{cost_note}{warn}")
    has_alpha = any(m.get("alpha_avg") is not None
                    for m in result["horizons"].values() if m.get("n", 0) > 0)
    hdr = (f"{'horizon':>8} {'n':>5} {'hit%':>6} {'avg%':>7} "
           f"{'base%':>7} {'edge%':>7} {'p(edge)':>9} {'med%':>7}")
    if has_alpha:
        hdr += f"  {'alpha%':>7} {'p(α)':>7}"
    lines.append(hdr)
    for h, m in result["horizons"].items():
        if m.get("n", 0) == 0:
            lines.append(f"{h:>7}d {'0':>5}  (no signals)")
            continue
        tt = m.get("edge_ttest") or {}
        p_str = f"{tt['p']:.4f}" if tt.get("p") is not None else "   n/a"
        sig_mark = "*" if tt.get("reliable") else " "
        row = (f"{h:>7}d {m['n']:>5} {m['hit_rate']:>6} {m['avg_ret']:>7} "
               f"{m['baseline_avg']:>7} {m['edge']:>+7} {p_str:>9}{sig_mark}"
               f" {m['median_ret']:>7}")
        if has_alpha:
            at = m.get("alpha_ttest") or {}
            ap_str = f"{at['p']:.4f}" if at.get("p") is not None else "    n/a"
            a_sig = "*" if at.get("reliable") else " "
            a_avg = m.get("alpha_avg")
            row += f"  {(f'{a_avg:+.2f}' if a_avg is not None else '    n/a'):>7} {ap_str:>7}{a_sig}"
        lines.append(row)
    if has_alpha:
        lines.append("  (* = p<0.05 two-tailed; alpha = market-model excess return)")
    if result["mae_avg"] is not None:
        lines.append(f"avg MAE over longest horizon: {result['mae_avg']}%")
    r = result["r_metrics"]
    if r and r.get("n_with_plan"):
        lines.append(f"trade-plan R: n={r['n_with_plan']} win%={r['win_rate']} "
                     f"expectancy={r['expectancy_R']}R "
                     f"(target={r['target_hits']}/stop={r['stop_hits']}"
                     f"/time={r.get('time_exits', 0)}/open={r['open_exits']}"
                     + (f"/trail={r['trail_exits']}" if r.get("trail_exits") else "")
                     + ")")
        # Plan coverage. A scanner can emit plans on every signal and still have
        # half of them unsimulatable (short-side); quoting the expectancy without
        # saying what fraction it was measured on is the partial-result habit.
        seen, unsim = r.get("plans_seen", 0), r.get("plans_unsimulated", 0)
        if unsim:
            lines.append(f"   plan coverage: {r['n_with_plan']}/{seen} simulated "
                         f"({unsim} skipped — short-side or degenerate, sim is long-only)")
    elif r:
        lines.append(f"trade-plan R: none simulatable — {r.get('note', '')} "
                     f"({r.get('plans_seen', 0)} plans seen)")
    else:
        lines.append("trade-plan R: (scanner emits no entry/stop/target — forward-return only)")
    lines.append(f"limitations: {', '.join(result['limitations'])}")
    return "\n".join(lines)


def backtest_confluence(scanner_names: list[str],
                        symbols: list[str],
                        fetch_fn,
                        horizons: tuple[int, ...] = DEFAULT_HORIZONS,
                        min_gap: int = DEFAULT_MIN_GAP,
                        warmup: int = WARMUP_BARS,
                        min_cofiring: int = 2,
                        cost_bps: float = 0,
                        cost_model: CostModel | None = None) -> dict:
    """Measure whether co-firing (≥ min_cofiring scanners agreeing on the same
    bar) beats any single-scanner fire over the same symbols and tape.

    This tests the Opportunity Hub's core premise: that confluence is additive.
    If it is, co-firing bars should show materially higher forward returns than
    single-fire bars, and the difference should be statistically significant.

    Returns a dict with keys:
      ``single``  — aggregate metrics for bars where exactly 1 scanner fired
      ``cofired`` — aggregate metrics for bars where ≥ min_cofiring fired
      ``lift``    — cofired.avg_ret - single.avg_ret per horizon
      ``lift_ttest`` — t-test on whether lift differs from zero (B-20a applied
                       to the confluence question)
    """
    cm = _resolve_cost(cost_bps, cost_model)
    fns: dict[str, object] = {}
    for name in scanner_names:
        spec = sc.SCANNERS.get(name)
        if spec:
            fns[name] = spec["fn"]
    if len(fns) < 2:
        return {"error": "need at least 2 valid scanner names"}

    max_h = max(horizons)
    single_ret: dict[int, list[float]] = {h: [] for h in horizons}
    co_ret:     dict[int, list[float]] = {h: [] for h in horizons}

    for sym in symbols:
        try:
            df = fetch_fn(sym)
        except Exception:
            continue
        if df is None or df.empty:
            continue
        df = df.dropna(subset=["high", "low", "close"]).reset_index(drop=True)
        n = len(df)
        if n < warmup + max_h + 2:
            continue

        has_open = "open" in df.columns
        close = df["close"].to_numpy(dtype=float)
        openp = df["open"].to_numpy(dtype=float) if has_open else close

        last_signal_bar: dict[str, int] = {}   # de-dup per scanner
        last_co_bar = -min_gap                  # de-dup for co-fire events

        t = warmup
        last_eval = n - max_h - 2
        while t <= last_eval:
            fired = []
            for name, fn in fns.items():
                # enforce min_gap per-scanner
                if t - last_signal_bar.get(name, -min_gap) < min_gap:
                    continue
                try:
                    hit = fn(df.iloc[:t + 1])
                except Exception:
                    hit = None
                if hit:
                    fired.append(name)

            entry_idx = t + 1
            entry_b = openp[entry_idx]
            if entry_b > 0 and fired:
                is_co = len(fired) >= min_cofiring
                # co-fire: de-dup so we don't count the same burst multiple times
                if is_co and (t - last_co_bar) < min_gap:
                    is_co = False
                for name in fired:
                    last_signal_bar[name] = t
                if is_co:
                    last_co_bar = t
                bucket = co_ret if is_co else single_ret
                for h in horizons:
                    fwd = close[entry_idx + h]
                    cost_pct = cm.round_trip_pct(entry_b, fwd)
                    bucket[h].append((fwd / entry_b - 1.0) * 100.0 - cost_pct)

            t += 1

    # Aggregate and compare
    result_single = {}
    result_co = {}
    lift = {}
    lift_ttest = {}
    for h in horizons:
        s = np.array(single_ret[h], dtype=float)
        c = np.array(co_ret[h], dtype=float)
        result_single[h] = {
            "n": len(s),
            "avg_ret": round(float(np.mean(s)), 2) if len(s) else None,
            "hit_rate": round(float(np.mean(s > 0) * 100), 1) if len(s) else None,
        }
        result_co[h] = {
            "n": len(c),
            "avg_ret": round(float(np.mean(c)), 2) if len(c) else None,
            "hit_rate": round(float(np.mean(c > 0) * 100), 1) if len(c) else None,
        }
        if len(s) >= 4 and len(c) >= 4:
            _lift = float(np.mean(c)) - float(np.mean(s))
            lift[h] = round(_lift, 2)
            t2, p2 = _ttest_ind(c, s, alternative="greater")
            lift_ttest[h] = {
                "lift": round(_lift, 2),
                "t": round(float(t2), 3),
                "p_one_tail": round(float(p2), 4),
                "reliable": bool(p2 < 0.05),
            }
        else:
            lift[h] = None
            lift_ttest[h] = {"lift": None, "reliable": False,
                             "note": "thin sample — need ≥4 events in each bucket"}

    return {
        "scanners": list(fns.keys()),
        "min_cofiring": min_cofiring,
        "single": result_single,
        "cofired": result_co,
        "lift_per_horizon": lift,
        "lift_ttest": lift_ttest,
        "premise_supported": any(v.get("reliable") for v in lift_ttest.values()),
        "cost_label": cm.label,
    }


def format_confluence_report(result: dict) -> str:
    """Human-readable report for backtest_confluence."""
    if "error" in result:
        return f"ERROR: {result['error']}"
    cost_note = result.get("cost_label", "GROSS")
    lines = [
        "=== Confluence Backtest ===",
        f"scanners: {', '.join(result['scanners'])}",
        f"co-fire threshold: ≥{result['min_cofiring']}  {cost_note}",
        "",
        f"{'horizon':>8}  {'single n':>9} {'single%':>8}  {'cofired n':>9} "
        f"{'cofired%':>8}  {'lift%':>7} {'p(lift)':>8}",
    ]
    for h in result["single"]:
        s = result["single"][h]
        c = result["cofired"][h]
        lt = result["lift_ttest"].get(h, {})
        s_avg = f"{s['avg_ret']:+.2f}" if s.get("avg_ret") is not None else "  n/a"
        c_avg = f"{c['avg_ret']:+.2f}" if c.get("avg_ret") is not None else "  n/a"
        lift_s = f"{lt['lift']:+.2f}" if lt.get("lift") is not None else "   n/a"
        p_s = f"{lt['p_one_tail']:.4f}" if lt.get("p_one_tail") is not None else "    n/a"
        sig = "*" if lt.get("reliable") else " "
        lines.append(
            f"{h:>7}d  {s['n']:>9} {s_avg:>8}  {c['n']:>9} {c_avg:>8}"
            f"  {lift_s:>7} {p_s:>8}{sig}"
        )
    verdict = ("SUPPORTED — co-firing beats single-firing (p<0.05, one-tail)"
               if result.get("premise_supported")
               else "NOT SUPPORTED — co-firing lift not statistically significant")
    lines += ["", f"Confluence premise: {verdict}",
              "  (* = one-tailed p<0.05: co-fired mean > single mean)"]
    return "\n".join(lines)


def sweep_volume_threshold(scanner_name: str,
                           symbols: list[str],
                           fetch_fn,
                           thresholds: tuple[float, ...] = (1.0, 1.2, 1.5, 2.0),
                           horizons: tuple[int, ...] = (10, 20),
                           **backtest_kwargs) -> dict:
    """Sweep volume confirmation multipliers to find the best edge cutoff (B-7).

    For each ``threshold`` in ``thresholds``, wraps the target scanner so that
    its ``vol_x50d`` field must meet the threshold before the signal is counted.
    This is a post-hoc filter on the scanner output — it is NOT the same as
    re-parameterising the scanner's internal logic (some scanners gate on volume
    internally, some score it as a bonus). The sweep tells you: "given this
    scanner's universe of hits, what vol_x multiplier floor maximises edge?"

    Returns a dict keyed by threshold, each containing the backtest result for
    that vol floor, plus a ``best_threshold`` key pointing to whichever threshold
    produced the highest mean edge across all horizons.
    """
    spec = sc.SCANNERS.get(scanner_name)
    if spec is None:
        return {"error": f"unknown scanner '{scanner_name}'"}
    base_fn = spec["fn"]
    results = {}

    for thresh in thresholds:
        # Wrap: only pass through hits that meet the vol threshold
        def _gated(df, _t=thresh, _fn=base_fn):
            hit = _fn(df)
            if hit is None:
                return None
            vx = hit.get("vol_x50d", hit.get("vol_x", None))
            if vx is not None and vx < _t:
                return None
            return hit

        # Temporarily register the gated scanner so backtest_scanner can find it
        _tmp_name = f"__sweep_{scanner_name}_{thresh}"
        sc.SCANNERS[_tmp_name] = {"fn": _gated, "category": "sweep", "description": ""}
        r = backtest_scanner(_tmp_name, symbols, fetch_fn,
                             horizons=horizons, **backtest_kwargs)
        del sc.SCANNERS[_tmp_name]
        r["vol_threshold"] = thresh
        results[thresh] = r

    # Find the threshold with the best average edge across all horizons
    def _avg_edge(r):
        edges = [m.get("edge", 0) or 0 for m in r.get("horizons", {}).values()
                 if m.get("n", 0) > 0]
        return float(np.mean(edges)) if edges else float("-inf")

    best = max(thresholds, key=lambda t: _avg_edge(results[t]))
    return {"results": results, "best_threshold": best,
            "scanner": scanner_name, "thresholds_tested": list(thresholds)}


def format_volume_sweep(sweep: dict) -> str:
    """Human-readable report for sweep_volume_threshold."""
    if "error" in sweep:
        return f"ERROR: {sweep['error']}"
    lines = [
        f"=== Volume Threshold Sweep — {sweep['scanner']} ===",
        f"best threshold: {sweep['best_threshold']}×",
        "",
        f"{'vol≥':>6}  {'signals':>8}  " +
        "  ".join(f"{'edge@' + str(h) + 'd':>10}" for h in
                  (list(next(iter(sweep['results'].values()))
                        .get('horizons', {}).keys()))),
    ]
    for thresh, r in sweep["results"].items():
        n = r.get("n_signals", 0)
        edges = [f"{m.get('edge', 0):>+9.2f}"
                 for m in r.get("horizons", {}).values()]
        lines.append(f"{thresh:>5}×  {n:>8}  " + "  ".join(edges))
    return "\n".join(lines)


# Default liquid ~50-name universe for a v1 run (widen once the engine is trusted).
LIQUID_50 = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "BHARTIARTL",
    "ITC", "LT", "KOTAKBANK", "AXISBANK", "HINDUNILVR", "BAJFINANCE", "MARUTI",
    "ASIANPAINT", "TITAN", "SUNPHARMA", "WIPRO", "HCLTECH", "ULTRACEMCO",
    "NESTLEIND", "TATASTEEL", "JSWSTEEL", "POWERGRID", "NTPC", "ONGC",
    "COALINDIA", "M&M", "ADANIPORTS", "GRASIM", "TECHM", "BAJAJFINSV",
    "HDFCLIFE", "DRREDDY", "CIPLA", "DIVISLAB", "EICHERMOT", "HEROMOTOCO",
    "BRITANNIA", "BPCL", "IOC", "SHREECEM", "APOLLOHOSP", "TATACONSUM",
    "PIDILITIND", "DABUR", "SIEMENS", "HAVELLS", "DMART", "BAJAJ-AUTO",
]


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    import screener_pipeline as sp
    name = sys.argv[1] if len(sys.argv) > 1 else "RSI 60-40 Setup"
    # --cost indian | --cost <bps>
    _cm: CostModel | None = None
    if "--cost" in sys.argv:
        _ci = sys.argv.index("--cost")
        sys.argv.pop(_ci)
        _cv = sys.argv.pop(_ci) if _ci < len(sys.argv) else "indian"
        if _cv.lower() == "indian":
            _cm = COST_INDIAN
        else:
            _cm = FlatCost(float(_cv))
    # --wf [N]  walk-forward with N windows (default 3)
    _wf = 0
    if "--wf" in sys.argv:
        _wi = sys.argv.index("--wf")
        sys.argv.pop(_wi)
        _wf = int(sys.argv.pop(_wi)) if _wi < len(sys.argv) and sys.argv[_wi].isdigit() else 3
    syms = LIQUID_50
    fetch = lambda s: sp.fetch_ohlcv(s, days=1500)
    if _wf:
        res = walk_forward_scanner(name, syms, fetch,
                                   n_windows=_wf, cost_model=_cm)
        print(format_walk_forward(res))
    else:
        res = backtest_scanner(name, syms, fetch, cost_model=_cm)
        print(format_report(res))
