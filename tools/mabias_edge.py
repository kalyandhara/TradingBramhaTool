#!/usr/bin/env python3
"""mabias_edge.py — does the MA Bias verdict carry directional edge? (B-89)

Ports `maBiasCompute` from chart_dashboard.html to Python and scores its
LONG/SHORT verdicts against forward returns using the same rotation-p framework
as svp_structure_backtest.py.

The MA Bias indicator ships five verdicts: LONG, SHORT, COUNTER-TREND, CHOP,
MIXED. The test arms are LONG (A) vs SHORT (B); COUNTER-TREND, CHOP and MIXED
are SKIP (they are not directional calls, and forcing them into a bucket would
dilute whatever signal exists).

Pre-registration follows the SVP Structure template:
* Primary: spread = mean(fwd|LONG) − mean(fwd|SHORT) at h=20.
* Floor: 200 LONG days AND 200 SHORT days.
* Significance: circular rotation, never Welch (state series, autocorrelated).
* Control: SKIP verdicts should sit near baseline.

CLI:
  py -3.14 tools/mabias_edge.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from gamma_regime_backtest import A_GROUP, B_GROUP, SKIP_GROUP

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache" / "backtest"

BASKET = ["^NSEI", "^NSEBANK", "RELIANCE.NS", "TCS.NS",
          "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS"]

HORIZONS = (5, 10, 20, 60)
PRIMARY_H = 20
FLOOR = 200

# ── maBiasCompute options, verbatim from chart_dashboard.html ──────────────
WHIPSAW_WIN = 15
WHIPSAW_N = 3
RECENT = 10
EXT_ATR = 2.0
BRAID_ATR = 0.8
VOL_LEN = 20


# ── Moving average helpers ─────────────────────────────────────────────────
def _ema(closes: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(closes), np.nan)
    if len(closes) < n:
        return out
    k = 2.0 / (n + 1)
    out[n - 1] = np.mean(closes[:n])
    for i in range(n, len(closes)):
        out[i] = closes[i] * k + out[i - 1] * (1 - k)
    return out


def _sma(closes: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(closes), np.nan)
    if len(closes) < n:
        return out
    cs = np.cumsum(closes)
    out[n - 1] = cs[n - 1] / n
    out[n:] = (cs[n:] - cs[:-n]) / n
    return out


def _atr14(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> np.ndarray:
    n = 14
    out = np.full(len(closes), np.nan)
    if len(closes) < n + 1:
        return out
    tr = np.maximum(highs[1:] - lows[1:],
                    np.maximum(np.abs(highs[1:] - closes[:-1]),
                               np.abs(lows[1:] - closes[:-1])))
    out[n] = np.mean(tr[:n])
    k = 2.0 / (n + 1)
    for i in range(n, len(tr)):
        out[i + 1] = tr[i] * k + out[i] * (1 - k)
    return out


# ── Crossings ──────────────────────────────────────────────────────────────
def _crossings(fast: np.ndarray, slow: np.ndarray):
    out = []
    prev = None
    for i in range(len(fast)):
        f, s = fast[i], slow[i]
        if np.isnan(f) or np.isnan(s):
            continue
        diff = f - s
        if prev is not None and ((prev <= 0 and diff > 0) or (prev >= 0 and diff < 0)):
            out.append((i, 1 if diff > 0 else -1))
        prev = diff
    return out


# ── Main verdict computation ──────────────────────────────────────────────
def mabias_verdicts(bars: list[dict]) -> list[str]:
    """Return one verdict per bar (same length as bars). Empty string for bars
    where the computation cannot run (insufficient warmup)."""
    n = len(bars)
    if n < 60:
        return [""] * n

    closes = np.array([b["close"] for b in bars], float)
    highs = np.array([b["high"] for b in bars], float)
    lows = np.array([b["low"] for b in bars], float)
    volumes = np.array([b.get("volume", 0) for b in bars], float)

    e9 = _ema(closes, 9)
    e20 = _ema(closes, 20)
    e50 = _ema(closes, 50)
    s50 = _sma(closes, 50)
    s200 = _sma(closes, 200) if n >= 200 else np.full(n, np.nan)
    atr = _atr14(highs, lows, closes)

    fast_crosses = _crossings(e9, e20)
    regime_crosses = _crossings(s50, s200) if n >= 200 else []

    verdicts = [""] * n

    for i in range(59, n):
        v9, v20, v50_ = e9[i], e20[i], e50[i]
        s50v, s200v = s50[i], s200[i]
        atr_v = atr[i]
        c = closes[i]

        if np.isnan(v9) or np.isnan(v20) or np.isnan(v50_):
            continue

        # Regime
        regime_dir = 0
        has_regime = False
        if not np.isnan(s200v) and not np.isnan(s50v):
            has_regime = True
            above200 = c > s200v
            gc_bull = s50v > s200v
            regime_dir = 1 if (above200 and gc_bull) else (-1 if (not above200 and not gc_bull) else 0)

        # Stack
        with_s200 = not np.isnan(s200v)
        bull_stack = v9 > v20 and v20 > v50_ and (not with_s200 or v50_ > s200v)
        bear_stack = v9 < v20 and v20 < v50_ and (not with_s200 or v50_ < s200v)
        stack_aligned = 1 if bull_stack else (-1 if bear_stack else 0)
        spread = max(v9, v20, v50_) - min(v9, v20, v50_)
        braided = not np.isnan(atr_v) and atr_v > 0 and spread < BRAID_ATR * atr_v

        # Trigger: latest 9/20 cross up to bar i
        last_fc = None
        for ci_idx, ci_dir in fast_crosses:
            if ci_idx > i:
                break
            last_fc = (ci_idx, ci_dir)
        trigger_live = last_fc is not None and (i - last_fc[0]) <= RECENT
        trigger_dir = last_fc[1] if last_fc else 0

        # Whipsaw
        whipsaw_count = sum(1 for ci, _d in fast_crosses if 0 <= i - ci < WHIPSAW_WIN)

        # Verdict ladder
        verdict = "MIXED"
        if braided:
            verdict = "CHOP"
        elif whipsaw_count >= WHIPSAW_N:
            verdict = "CHOP"
        elif has_regime and regime_dir != 0:
            agree = stack_aligned == regime_dir
            if trigger_live and trigger_dir != regime_dir:
                verdict = "COUNTER-TREND"
            elif agree:
                verdict = "LONG" if regime_dir == 1 else "SHORT"

        verdicts[i] = verdict

    return verdicts


# ── Scoring framework (reuses the rotation-p from gamma_regime_backtest) ──

def _safe(sym: str) -> str:
    return sym.replace("^", "_").replace("=", "_").replace("-", "_")


def _bars_path(sym: str) -> Path:
    return CACHE / f"{_safe(sym)}_1d.json"


def _load_bars(sym: str) -> list[dict] | None:
    p = _bars_path(sym)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))["bars"]


WARMUP = 200  # need 200 bars for the 200 SMA to exist


def _fwd(opens: np.ndarray, closes: np.ndarray, t: int, h: int) -> float | None:
    if t + 1 + h > len(closes) - 1 or not (opens[t + 1] > 0):
        return None
    return float((closes[t + 1 + h] / opens[t + 1] - 1.0) * 100.0)


def _panel(symbols: list[str], h: int) -> list[tuple[str, np.ndarray, np.ndarray]]:
    out = []
    for sym in symbols:
        bars = _load_bars(sym)
        if not bars:
            continue
        verdicts = mabias_verdicts(bars)
        opens = np.array([b["open"] for b in bars], float)
        closes = np.array([b["close"] for b in bars], float)
        vals, labs = [], []
        for t in range(WARMUP, len(bars)):
            v = verdicts[t]
            if not v:
                continue
            f = _fwd(opens, closes, t, h)
            vals.append(np.nan if f is None else f)
            if v == "LONG":
                labs.append(A_GROUP)
            elif v == "SHORT":
                labs.append(B_GROUP)
            else:
                labs.append(SKIP_GROUP)
        if len(vals) >= 50:
            out.append((sym, np.asarray(vals, float), np.asarray(labs, int)))
    return out


def _pooled_spread(panel, shift: int = 0) -> float | None:
    a, b = [], []
    for _sym, vals, labs in panel:
        cat = np.roll(labs, shift % len(labs)) if shift else labs
        ok = np.isfinite(vals)
        a.extend(vals[ok & (cat == A_GROUP)])
        b.extend(vals[ok & (cat == B_GROUP)])
    if len(a) < 4 or len(b) < 4:
        return None
    return float(np.mean(a) - np.mean(b))


def pooled_rotation_p(panel, n_shifts: int = 400) -> tuple[float | None, int]:
    obs = _pooled_spread(panel, 0)
    if obs is None:
        return None, 0
    longest = max(len(l) for _s, _v, l in panel)
    step = max(1, longest // n_shifts)
    stats = []
    for s in range(step, longest, step):
        d = _pooled_spread(panel, s)
        if d is not None:
            stats.append(abs(d))
    if len(stats) < 20:
        return None, len(stats)
    return float(np.mean(np.asarray(stats) >= abs(obs))), len(stats)


def _arm(panel, group: int) -> list[float]:
    out = []
    for _sym, vals, labs in panel:
        ok = np.isfinite(vals)
        out.extend(vals[ok & (labs == group)])
    return out


def score(symbols: list[str]) -> dict:
    res = {"horizons": {}, "per_symbol": {}, "verdict_dist": {}}
    for h in HORIZONS:
        panel = _panel(symbols, h)
        if not panel:
            continue
        buy, sell, skip = (_arm(panel, A_GROUP), _arm(panel, B_GROUP),
                           _arm(panel, SKIP_GROUP))
        base = buy + sell + skip
        spread = _pooled_spread(panel, 0)
        p_rot, n_sh = pooled_rotation_p(panel)
        res["horizons"][h] = {
            "n_long": len(buy), "n_short": len(sell), "n_skip": len(skip),
            "long": float(np.mean(buy)) if buy else float("nan"),
            "short": float(np.mean(sell)) if sell else float("nan"),
            "skip": float(np.mean(skip)) if skip else float("nan"),
            "base": float(np.mean(base)) if base else float("nan"),
            "spread": spread, "p_rot": p_rot, "n_shifts": n_sh,
        }
        if h == PRIMARY_H:
            for sym, vals, labs in panel:
                ok = np.isfinite(vals)
                res["per_symbol"][sym] = {
                    "n_long": int(((labs == A_GROUP) & ok).sum()),
                    "n_short": int(((labs == B_GROUP) & ok).sum()),
                    "long": float(np.mean(vals[ok & (labs == A_GROUP)]))
                            if ((labs == A_GROUP) & ok).any() else float("nan"),
                    "short": float(np.mean(vals[ok & (labs == B_GROUP)]))
                             if ((labs == B_GROUP) & ok).any() else float("nan"),
                }

    # Verdict distribution across all symbols
    for sym in symbols:
        bars = _load_bars(sym)
        if not bars:
            continue
        vv = mabias_verdicts(bars)
        from collections import Counter
        c = Counter(v for v in vv[WARMUP:] if v)
        res["verdict_dist"][sym] = dict(c)

    return res


def decision(res: dict) -> tuple[str, str]:
    h = res["horizons"].get(PRIMARY_H)
    if not h:
        return "NO DATA", "the primary horizon produced no panel"
    if h["n_long"] < FLOOR or h["n_short"] < FLOOR:
        return ("INCONCLUSIVE - UNDERPOWERED",
                f"LONG {h['n_long']} / SHORT {h['n_short']} against a floor of {FLOOR} each")
    p, sp = h["p_rot"], h["spread"]
    if p is None:
        return "INCONCLUSIVE", "the rotation null could not be computed"
    if sp > 0 and p < 0.05:
        return "PASS", f"spread {sp:+.2f}%, p_rot {p:.3f}"
    if sp < 0 and p < 0.05:
        return ("INVERTED", f"spread {sp:+.2f}%, p_rot {p:.3f} — "
                            "do NOT ship the mirror; it is a new hypothesis")
    return "NULL", f"spread {sp:+.2f}%, p_rot {p:.3f}"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="B-89 · MA Bias verdict edge test")
    ap.parse_args()

    print("Computing MA Bias verdicts and scoring\n")
    res = score(BASKET)

    print("Verdict distribution:")
    for sym, dist in res["verdict_dist"].items():
        total = sum(dist.values())
        parts = ", ".join(f"{k}:{v}" for k, v in sorted(dist.items()))
        print(f"  {sym:<14} n={total}  {parts}")

    print(f"\n{'h':>4} {'n LONG':>7} {'n SHORT':>8} {'LONG %':>8} {'SHORT %':>8} "
          f"{'SKIP %':>8} {'base %':>8} {'spread':>8} {'p_rot':>7}")
    for h in HORIZONS:
        r = res["horizons"].get(h)
        if not r:
            continue
        p = "n/a" if r["p_rot"] is None else f"{r['p_rot']:.3f}"
        star = "  <- primary" if h == PRIMARY_H else ""
        print(f"{h:>4} {r['n_long']:>7} {r['n_short']:>8} {r['long']:>8.2f} "
              f"{r['short']:>8.2f} {r['skip']:>8.2f} {r['base']:>8.2f} "
              f"{r['spread']:>+8.2f} {p:>7}{star}")

    print(f"\nPer symbol at h={PRIMARY_H}:")
    for sym, r in res["per_symbol"].items():
        print(f"  {sym:<14} LONG {r['n_long']:>5} {r['long']:>+7.2f}%   "
              f"SHORT {r['n_short']:>5} {r['short']:>+7.2f}%")

    v, why = decision(res)
    print(f"\nDECISION (pre-registered): {v}\n  {why}")

    ctrl = res["horizons"].get(PRIMARY_H)
    if ctrl:
        gap = ctrl["skip"] - ctrl["base"]
        note = ("near baseline" if abs(gap) < 0.25
                else "DEPARTS from baseline — the filter selects unusual bars")
        print(f"\nControl — SKIP vs baseline at h={PRIMARY_H}: {gap:+.3f}pp ({note})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
