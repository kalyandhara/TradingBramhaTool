#!/usr/bin/env python3
"""flag_pole.py — the general Flag & Pole continuation, both directions (B-92 / PR-3).

From the owner's Spider Software card, `sources/Spider-Software-Flag-Pole-Infographic`:
a vertical **pole**, a shallow counter-trend **flag**, then a break in the pole's
direction. Entry at the flag break, **stop at the far flag boundary**, **target =
the pole height projected from the breakout**.

── What this is NOT, and why it exists ───────────────────────────────────────
`scan_high_tight_flag` is the same family's rarest member: a **>=90% pole inside
~40 bars** with a flag correcting **<=25%**. B-19 could not score it — it was one
of three scanners with **too few signals to measure**. The gates that make it
meaningful are the gates that make it uncheckable.

This is the proportionate version, and it is justified on **COVERAGE, never on
expected edge**. B-19 measured **0 of 41 scanners stable after costs**; a 47th
pattern is not expected to break that. What it buys is a family that fires often
enough to be measured, and a bear half that did not exist here in any form.

── The trap this is built to avoid ───────────────────────────────────────────
Loosen the pole far enough and "flag" becomes "any pullback in an uptrend" —
which this desk already has as `Pullback Entry`, **measured NEGATIVE** (-0.43% /
-1.12%). B-58's quasimodo work is the precedent: an independent pivot search
reported the pattern on **73%** of names, adjacency cut it to 44%, and the true
count was **3%**. So the gates below are deliberately strict, and **the hit rate
is counted and published before any claim is made** (`--count`).

── The parameters, each a decision ───────────────────────────────────────────
**Pole in ATR, not per cent.** A 20% pole means different things on a sleepy
large cap and a micro cap; measuring it in ATR makes one threshold mean one thing
across the universe.

**Flag retracement capped at 50% of the pole.** Past half, the "flag" has given
back most of the move and the continuation thesis is gone. HTF uses 25%; the
classic literature says 38-50%. 50% is the loose end of the classic range and is
the one gate here deliberately NOT tightened, because tightening it is what made
HTF unmeasurable.

**Volume contraction is NOT required, and that is a departure.** HTF rejects a
rising-volume flag outright, and its reasoning is sound: a flag on rising volume
is distribution into strength. But requiring it costs signals, and this detector
exists to be measurable. So it is **measured and reported** (`vol_contract`) as a
field rather than enforced as a gate — a later test can ask whether it matters
instead of assuming it.

**Close-confirmed breakout**, per this desk's convention.

── The plan, and what the target is not ──────────────────────────────────────
Entry, stop and target are all derived from the pattern's own geometry — none is
a number someone picked. The target is the pole height projected from the
breakout, exactly as the card draws it, and it is a **PROJECTION, never a
forecast**: it says where the measured move would end, not that price will get
there. Nothing here has been backtested.

CLI:
    py -3 -X utf8 tools/flag_pole.py --count --symbols 150   # count BEFORE claiming
    py -3 -X utf8 tools/flag_pole.py RELIANCE
"""
from __future__ import annotations

import argparse
import sys
from typing import Any, Optional

import numpy as np
import pandas as pd

#: Bars searched for the pole + flag together.
WINDOW = 90

#: Pole: minimum move in ATR over at most POLE_MAX_BARS bars. 4 ATR over <=15
#: bars is a genuine thrust rather than ordinary drift; see `--count`.
POLE_MIN_ATR = 4.0
POLE_MAX_BARS = 15
POLE_MIN_BARS = 3

#: Flag: how far it may retrace the pole, and how long it may last. Past half the
#: pole the continuation thesis is gone; past 25 bars it is a base, not a pause.
FLAG_MAX_RETRACE = 0.50
FLAG_MIN_BARS = 3
FLAG_MAX_BARS = 25

#: ATR lookback (Wilder).
ATR_N = 14


def _atr(high, low, close, n: int = ATR_N) -> np.ndarray:
    prev = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev), np.abs(low - prev)))
    out = np.full(len(tr), np.nan)
    if len(tr) < n:
        return out
    out[n - 1] = tr[:n].mean()
    for i in range(n, len(tr)):
        out[i] = (out[i - 1] * (n - 1) + tr[i]) / n
    return out


def detect_flag_pole(df: pd.DataFrame, direction: str = "bull",
                     window: int = WINDOW) -> Optional[dict[str, Any]]:
    """Geometry for the most recent flag & pole, or None.

    `direction` is "bull" (up pole, down flag) or "bear" (the mirror).

    Returns bar indices into the PASSED frame so a chart overlay can map them to
    timestamps, plus the plan and the fields a later measurement would need.
    """
    if df is None or len(df) < window + ATR_N:
        return None
    if direction not in ("bull", "bear"):
        raise ValueError(f"direction must be 'bull' or 'bear', got {direction!r}")

    w = df.tail(window).reset_index(drop=True)
    off = len(df) - len(w)
    high = w["high"].to_numpy(float)
    low = w["low"].to_numpy(float)
    close = w["close"].to_numpy(float)
    vol = (w["volume"].to_numpy(float) if "volume" in w.columns
           else np.full(len(w), np.nan))
    n = len(w)
    atr = _atr(high, low, close)
    a = atr[-1]
    if not np.isfinite(a) or a <= 0:
        return None

    bull = direction == "bull"

    # ── 1. The pole: the strongest qualifying thrust that leaves room for a flag.
    # Searched newest-first so the flag is the RECENT consolidation, not an old one.
    best = None
    for end in range(n - FLAG_MIN_BARS - 2, POLE_MIN_BARS - 1, -1):
        for length in range(POLE_MIN_BARS, POLE_MAX_BARS + 1):
            start = end - length
            if start < 0:
                break
            if bull:
                p_lo, p_hi = float(low[start]), float(high[end])
                move = p_hi - p_lo
            else:
                p_hi, p_lo = float(high[start]), float(low[end])
                move = p_hi - p_lo
            if move <= 0:
                continue
            if move / a < POLE_MIN_ATR:
                continue
            # The thrust must be monotone ENOUGH: the pole's own close-to-close
            # path should mostly go one way, or a V-shaped swing qualifies as a
            # "pole" on its net move alone.
            steps = np.diff(close[start:end + 1])
            if len(steps) == 0:
                continue
            frac = (float((steps > 0).mean()) if bull else float((steps < 0).mean()))
            if frac < 0.60:
                continue
            if best is None or move / a > best["atr_mult"]:
                best = {"start": start, "end": end, "lo": p_lo, "hi": p_hi,
                        "move": move, "atr_mult": move / a, "mono": frac}
    if best is None:
        return None

    # ── 2. The flag BODY is everything after the pole EXCEPT the current bar.
    #
    # Excluding the current bar is not a detail, it is what makes a breakout
    # possible at all. The first version took the boundary as the max high over
    # the whole flag INCLUDING the live bar, and then asked whether that bar's
    # close exceeded it -- which a close can never do, since it cannot exceed its
    # own bar's high. The count caught it instantly: 189 patterns, `broken 0`.
    #
    # So the boundary is the consolidation's, formed strictly before the bar that
    # breaks it, and it does not move under the trade once it is set.
    f0 = best["end"] + 1
    body_end = n - 1                       # exclusive: the live bar is the test
    flag_len = body_end - f0
    if not (FLAG_MIN_BARS <= flag_len <= FLAG_MAX_BARS):
        return None
    f_high = float(high[f0:body_end].max())
    f_low = float(low[f0:body_end].min())

    # Retracement, and the direction check. A bull flag must drift DOWN from the
    # pole high; a flag BODY that makes a new high is not a flag, it is
    # continuation already under way. The live bar is exempt -- breaking out IS
    # making a new high, and rejecting that would reject every breakout.
    if bull:
        retrace = (best["hi"] - f_low) / best["move"]
        if f_high > best["hi"]:
            return None
    else:
        retrace = (f_high - best["lo"]) / best["move"]
        if f_low < best["lo"]:
            return None
    if not (0 < retrace <= FLAG_MAX_RETRACE):
        return None

    # ── 3. The plan, all three levels from the geometry.
    # Breakout level is the flag boundary in the pole's direction; the stop is the
    # FAR boundary, exactly as the card draws it.
    if bull:
        trigger, stop = f_high, f_low
        target = trigger + best["move"]
    else:
        trigger, stop = f_low, f_high
        target = trigger - best["move"]
    last = float(close[-1])
    broken = last > trigger if bull else last < trigger

    # Volume: measured, never gated. A flag on rising volume is distribution into
    # strength (HTF's reasoning), but enforcing that is what made HTF too rare to
    # score -- so it is reported and a later test can ask whether it matters.
    pv = vol[best["start"]:best["end"] + 1]
    fv = vol[f0:body_end]
    def _mean(arr):
        # `np.nanmean` on an all-NaN slice warns and returns NaN. A frame with no
        # volume column takes that path every time, so it is checked rather than
        # suppressed -- a warning nobody reads is how a real one gets missed.
        arr = arr[np.isfinite(arr)] if len(arr) else arr
        return float(arr.mean()) if len(arr) else None

    pole_vol = _mean(pv)
    flag_vol = _mean(fv)
    vol_contract = (None if not pole_vol or not flag_vol or pole_vol <= 0
                    else round(1.0 - flag_vol / pole_vol, 3))

    risk = abs(trigger - stop)
    return {
        "direction": direction,
        "pole_start": off + best["start"], "pole_end": off + best["end"],
        "pole_low": round(best["lo"], 2), "pole_high": round(best["hi"], 2),
        "pole_bars": best["end"] - best["start"],
        "pole_atr": round(best["atr_mult"], 2),
        "pole_monotonicity": round(best["mono"], 2),
        "flag_start": off + f0, "flag_bars": flag_len,
        "flag_end": off + body_end - 1,
        "flag_high": round(f_high, 2), "flag_low": round(f_low, 2),
        "retrace": round(retrace, 3),
        "vol_contract": vol_contract,
        "broken": bool(broken),
        # The plan. `entry` is the trigger level, not the last close: a setup that
        # has not broken yet is a WATCH, and pretending otherwise would put an
        # entry on a trade nobody could have taken.
        "entry": round(trigger, 2),
        "stop": round(stop, 2),
        "target": round(target, 2),
        "rr": (round(abs(target - trigger) / risk, 2) if risk > 0 else None),
        "atr": round(float(a), 2),
    }


def _card(df: pd.DataFrame, direction: str) -> Optional[dict[str, Any]]:
    """Scanner-registry card for one direction, or None."""
    g = detect_flag_pole(df, direction=direction)
    if g is None:
        return None
    bull = direction == "bull"
    label = "Flag & Pole" if bull else "Inverted Flag & Pole"
    state = "BROKEN OUT" if g["broken"] else "WATCH — unbroken"
    vc = g["vol_contract"]
    vol_txt = ("volume not available" if vc is None
               else f"flag volume {'dried up' if vc > 0 else 'ROSE'} {abs(vc) * 100:.0f}% vs the pole")
    return {
        "pattern_type": label,
        "tags": [f"pole {g['pole_atr']}x ATR", f"retrace {g['retrace'] * 100:.0f}%",
                 f"flag {g['flag_bars']}b", state],
        "reasons": [
            f"Pole: {g['pole_bars']} bars, {g['pole_atr']}x ATR "
            f"({g['pole_low']} → {g['pole_high']}), {g['pole_monotonicity'] * 100:.0f}% of "
            f"closes in the pole's direction",
            f"Flag: {g['flag_bars']} bars retracing {g['retrace'] * 100:.0f}% of the pole "
            f"(cap {FLAG_MAX_RETRACE * 100:.0f}%) — {vol_txt}",
            f"{state} — trigger {g['entry']}",
            f"Trade plan — entry {g['entry']} · stop {g['stop']} (far flag boundary) "
            f"· target {g['target']} · R:R {g['rr']}",
            "Target is the POLE HEIGHT PROJECTED from the trigger — a measured "
            "move, not a forecast. UNMEASURED: this detector has no backtest, and "
            "B-19 found 0 of 41 scanners stable after costs.",
        ],
        "score_base": round(min(100.0, 40 + g["pole_atr"] * 6
                                + (1 - g["retrace"]) * 30), 1),
        "entry": g["entry"], "stop": g["stop"], "target": g["target"],
        "flag_pole": g,
    }


def scan_flag_pole(df: pd.DataFrame) -> Optional[dict[str, Any]]:
    """Bullish flag & pole — up thrust, shallow pullback, break of the flag high."""
    return _card(df, "bull")


def scan_inverted_flag_pole(df: pd.DataFrame) -> Optional[dict[str, Any]]:
    """Bearish (inverted) flag & pole — down thrust, shallow bounce, break lower.

    **EXIT / AVOID, not an entry.** Shorting NSE cash for a swing hold is not
    available to most users of this repo, so the useful reading of this is "do not
    be long here", the same scoping B-90 carries.
    """
    return _card(df, "bear")


def count(symbols, fetch_fn, stride: int = 10) -> dict[str, Any]:
    """How often does this fire? Counted BEFORE any claim is made.

    B-58's discipline: a detector that reports a pattern on a large share of a
    universe has defined the pattern too loosely, and the count is what reveals
    it. Published in the write-up either way.
    """
    out = {"symbols": 0, "bars": 0,
           "bull": 0, "bear": 0, "bull_broken": 0, "bear_broken": 0,
           "symbols_with_bull": 0, "symbols_with_bear": 0}
    for sym in symbols:
        try:
            df = fetch_fn(sym)
        except Exception:
            continue
        if df is None or getattr(df, "empty", True) or len(df) < WINDOW + 40:
            continue
        out["symbols"] += 1
        saw_b = saw_s = False
        for t in range(WINDOW + ATR_N, len(df) - 1, max(1, stride)):
            sub = df.iloc[:t + 1]
            out["bars"] += 1
            for d, key in (("bull", "bull"), ("bear", "bear")):
                g = detect_flag_pole(sub, direction=d)
                if g:
                    out[key] += 1
                    if g["broken"]:
                        out[key + "_broken"] += 1
                    if d == "bull":
                        saw_b = True
                    else:
                        saw_s = True
        out["symbols_with_bull"] += int(saw_b)
        out["symbols_with_bear"] += int(saw_s)
    for k in ("bull", "bear"):
        out[k + "_pct_of_bars"] = (round(100.0 * out[k] / out["bars"], 2)
                                   if out["bars"] else None)
        out[k + "_pct_of_symbols"] = (
            round(100.0 * out["symbols_with_" + k] / out["symbols"], 1)
            if out["symbols"] else None)
    return out


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # pragma: no cover
        pass
    ap = argparse.ArgumentParser(description="B-92 / PR-3 · flag & pole")
    ap.add_argument("symbol", nargs="?", default="RELIANCE")
    ap.add_argument("--count", action="store_true", help="count hits on a universe")
    ap.add_argument("--symbols", type=int, default=100)
    ap.add_argument("--stride", type=int, default=10)
    a = ap.parse_args()

    import screener_pipeline as sp
    if a.count:
        import nse_universe as nu
        syms = list(nu.symbols("nifty500"))[:a.symbols]
        c = count(syms, lambda s: sp.fetch_ohlcv(s, days=700), stride=a.stride)
        print(f"\n{c['symbols']} symbols · {c['bars']} evaluated bars "
              f"(every {a.stride}th)\n")
        for d in ("bull", "bear"):
            print(f"  {d:<5} {c[d]:>6} hits  "
                  f"{c[d + '_pct_of_bars']:>6}% of bars  "
                  f"{c['symbols_with_' + d]:>4}/{c['symbols']} symbols "
                  f"({c[d + '_pct_of_symbols']}%)  "
                  f"broken {c[d + '_broken']}")
        return 0

    df = sp.fetch_ohlcv(a.symbol, days=700)
    if df is None or df.empty:
        print(f"no data for {a.symbol}")
        return 1
    for d in ("bull", "bear"):
        g = detect_flag_pole(df, direction=d)
        print(f"\n=== {a.symbol} {d} ===")
        if not g:
            print("  no pattern")
            continue
        for k, v in g.items():
            print(f"  {k:20} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
