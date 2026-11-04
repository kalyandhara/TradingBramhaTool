#!/usr/bin/env python3
"""FLD-1 — Hurst FLD confluence: a calibrated probability per stock, for sorting.

What this module does
---------------------
1. **FLD per cycle.** For each nominal cycle c (20/40/80/160 bars) the Future
   Line of Demarcation is price displaced forward by half a cycle:
   ``FLD_c[t] = close[t - c/2]``. Its last c/2 values are therefore known in
   advance — that is the "forward projected" dashed line, not a forecast of price.
2. **Signals.** Price crossing an FLD is a signal; the target projects the
   swing before the cross the same distance beyond it:
   down: ``cross - (prior peak - cross)``, up: ``cross + (cross - prior trough)``.
3. **Confluence snapshot** at any bar t, using data up to t only:
   * ``D``  — weighted direction vote, ``Σ √c · side · freshness / Σ √c``
   * ``TC`` — target clustering of the agreeing cycles, in ATR units
   * ``PA`` — phase alignment: longest cycle freshly troughed (long) or peaked
     (short) while the next cycle confirms
   * ``p_hit`` — this stock's own past hit rate, shrunk to 50% (Beta prior)
4. **Probability.** ``P = sigmoid(β · [1, |D|, TC, PA, logit p_hit])``, with β
   fitted by logistic regression on a no-lookahead backtest. Until a model has
   been fitted the defaults are used and every output says *uncalibrated*.
5. **Sort key.** ``EV = P·reward − (1−P)·risk`` in ATR units, where reward is
   the distance to the clustered target and risk the distance to the trigger
   cycle's FLD (the invalidation level), floored at 0.5 ATR.

Honesty rules
-------------
* No lookahead: every snapshot at bar t reads bars ≤ t, and p_hit only counts
  outcomes *resolved* before t. A test asserts this.
* An outcome still open at the end of the data is excluded, never scored as a
  miss or a hit.
* A target price already behind the current price is not a target; a snapshot
  with none ahead returns no setup rather than a fabricated one.

CLI:  python fld_confluence.py calibrate [--limit N]
      fits β on the NIFTY Total Market universe and writes cache/fld_confluence_model.json
"""
from __future__ import annotations

import json
import logging
import math
import time
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

_log = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent
MODEL_FILE = HERE / "cache" / "fld_confluence_model.json"

CYCLES: tuple[int, ...] = (20, 40, 80, 160)
#: Used only until a model is fitted. Picked to be sane, not measured — the UI
#: labels anything produced with these as "uncalibrated".
DEFAULT_BETA: tuple[float, ...] = (-0.4, 1.2, 0.6, 0.5, 1.0)
PRIOR_HIT = 0.5
PRIOR_STRENGTH = 10.0
FEATURES = ("bias", "|D|", "TC", "PA", "logit p_hit")


# ──────────────────────────────────────────────────────────────────────────────
# Primitives
# ──────────────────────────────────────────────────────────────────────────────
def _sigmoid(z: float | np.ndarray):
    return 1.0 / (1.0 + np.exp(-z))


def _logit(p: float) -> float:
    p = min(max(p, 0.05), 0.95)
    return math.log(p / (1 - p))


def atr(df: pd.DataFrame, n: int = 14) -> np.ndarray:
    c = df["close"].to_numpy(float)
    h = df["high"].to_numpy(float) if "high" in df else c
    l = df["low"].to_numpy(float) if "low" in df else c
    pc = np.concatenate([[c[0]], c[:-1]])
    tr = np.maximum.reduce([h - l, np.abs(h - pc), np.abs(l - pc)])
    return pd.Series(tr).rolling(n, min_periods=1).mean().to_numpy()


def fld_series(df: pd.DataFrame, cycle: int) -> tuple[pd.Series, pd.Series]:
    """(FLD on the known dates, forward-projected FLD on the next c/2 business days)."""
    s = cycle // 2
    close = df["close"].astype(float)
    known = close.shift(s)
    fwd_idx = pd.bdate_range(close.index[-1], periods=s + 1)[1:]
    fwd = pd.Series(close.iloc[-s:].to_numpy(), index=fwd_idx)
    return known, fwd


def _prep(close: np.ndarray, cycle: int) -> dict:
    """Arrays for one cycle: FLD, side, and every cross with its target."""
    n, s = len(close), cycle // 2
    fld = np.full(n, np.nan)
    if n > s:
        fld[s:] = close[:-s]
    raw = np.sign(close - fld)
    side = pd.Series(raw).replace(0, np.nan).ffill().to_numpy()
    prev = np.concatenate([[np.nan], side[:-1]])
    idx = np.where(~np.isnan(side) & ~np.isnan(prev) & (side != prev))[0]
    tgt, dirs, keep = [], [], []
    for i in idx:
        look = close[max(0, i - s):i]
        if len(look) == 0:
            continue
        x, up = close[i], side[i] > 0
        tgt.append(x + (x - look.min()) if up else x - (look.max() - x))
        dirs.append(1 if up else -1)
        keep.append(i)
    return {"cycle": cycle, "fld": fld, "side": side, "x_idx": np.array(keep, int),
            "x_tgt": np.array(tgt, float), "x_dir": np.array(dirs, int)}


def _state_at(p: dict, close: np.ndarray, t: int) -> dict | None:
    k = int(np.searchsorted(p["x_idx"], t, side="right")) - 1
    if k < 0 or np.isnan(p["fld"][t]):
        return None
    c, i = p["cycle"], int(p["x_idx"][k])
    win = close[max(0, t - c + 1):t + 1]
    return {"cycle": c, "side": int(p["x_dir"][k]), "bars": t - i,
            "fresh": math.exp(-(t - i) / (c / 4)), "target": float(p["x_tgt"][k]),
            "fld_now": float(p["fld"][t]),
            "since_trough": (len(win) - 1 - int(np.argmin(win))) / c,
            "since_peak": (len(win) - 1 - int(np.argmax(win))) / c}


# ──────────────────────────────────────────────────────────────────────────────
# Snapshot — the confluence reading at one bar
# ──────────────────────────────────────────────────────────────────────────────
def _snapshot(preps: list[dict], close: np.ndarray, t: int, atr_t: float,
              p_hit: float, beta: Iterable[float]) -> dict | None:
    states = [s for p in preps if (s := _state_at(p, close, t))]
    if len(states) < 2 or not atr_t or atr_t <= 0:
        return None
    states.sort(key=lambda s: s["cycle"])
    w = {s["cycle"]: math.sqrt(s["cycle"]) for s in states}
    D = sum(w[s["cycle"]] * s["side"] * s["fresh"] for s in states) / sum(w.values())
    side = 1 if D >= 0 else -1
    price = float(close[t])
    agree = [s for s in states if s["side"] == side]
    ahead = [s["target"] for s in agree if (s["target"] - price) * side > 0]
    if not ahead:
        return None
    T = float(np.median(ahead))
    TC = 0.5 if len(ahead) == 1 else float(np.clip(1 - np.std(ahead) / (2 * atr_t), 0, 1))
    L, S = states[-1], states[-2]
    if side > 0:
        PA = 1.0 if (L["since_trough"] < 0.25 and S["side"] > 0 and S["fresh"] > 0.5) else \
             0.5 if (L["since_trough"] < 0.5 and S["side"] > 0) else 0.0
    else:
        PA = 1.0 if (L["since_peak"] < 0.25 and S["side"] < 0 and S["fresh"] > 0.5) else \
             0.5 if (L["since_peak"] < 0.5 and S["side"] < 0) else 0.0
    trig = max(agree, key=lambda s: w[s["cycle"]] * s["fresh"])
    stop = trig["fld_now"]
    reward = abs(T - price) / atr_t
    risk = max(abs(price - stop) / atr_t, 0.5)
    x = np.array([1.0, abs(D), TC, PA, _logit(p_hit)])
    P = float(_sigmoid(float(np.dot(np.asarray(list(beta), float), x))))
    return {"t": t, "side": side, "D": D, "TC": TC, "PA": PA, "p_hit": p_hit,
            "P": P, "price": price, "target": T, "stop": stop, "atr": atr_t,
            "reward": reward, "risk": risk, "EV": P * reward - (1 - P) * risk,
            "trigger_cycle": trig["cycle"], "horizon": max(10, trig["cycle"] // 2),
            "x": x.tolist(), "states": states}


def _outcome(close, high, low, t: int, side: int, target: float, stop: float,
             horizon: int) -> tuple[int | None, int | None]:
    """(hit 1/0, resolving bar) — target touched before a close beyond the stop
    within the horizon. Same-bar conflicts count as a miss. (None, None) while
    the window is still open at the end of the data."""
    last = len(close) - 1
    for j in range(t + 1, min(t + horizon, last) + 1):
        if side > 0:
            if close[j] < stop:
                return 0, j
            if high[j] >= target:
                return 1, j
        else:
            if close[j] > stop:
                return 0, j
            if low[j] <= target:
                return 1, j
    if t + horizon <= last:
        return 0, t + horizon
    return None, None


# ──────────────────────────────────────────────────────────────────────────────
# History (no-lookahead backtest) and today's score
# ──────────────────────────────────────────────────────────────────────────────
def history(df: pd.DataFrame, beta: Iterable[float] | None = None,
            cycles: tuple[int, ...] = CYCLES) -> tuple[list[dict], dict]:
    """Snapshots at every FLD cross bar, each with its eventual outcome.

    Returns (rows, ctx). ``ctx`` carries the arrays and the running hit tally so
    `score` can read today's p_hit without recomputing.
    """
    beta = tuple(beta or DEFAULT_BETA)
    close = df["close"].to_numpy(float)
    high = df["high"].to_numpy(float) if "high" in df else close
    low = df["low"].to_numpy(float) if "low" in df else close
    a = atr(df)
    preps = [_prep(close, c) for c in cycles]
    warm = max(cycles)
    events = sorted({int(i) for p in preps for i in p["x_idx"] if i >= warm})
    resolved: list[tuple[int, int]] = []          # (resolve_bar, hit)
    rows = []
    for t in events:
        done = [h for rb, h in resolved if rb < t]
        p_hit = (sum(done) + PRIOR_STRENGTH * PRIOR_HIT) / (len(done) + PRIOR_STRENGTH)
        snap = _snapshot(preps, close, t, float(a[t]), p_hit, beta)
        if not snap:
            continue
        hit, rb = _outcome(close, high, low, t, snap["side"], snap["target"],
                           snap["stop"], snap["horizon"])
        snap.update(hit=hit, resolve_bar=rb, date=str(df.index[t])[:10])
        rows.append(snap)
        if hit is not None:
            resolved.append((rb, hit))
    ctx = {"close": close, "atr": a, "preps": preps, "resolved": resolved}
    return rows, ctx


def load_model(path: Path = MODEL_FILE) -> dict | None:
    try:
        m = json.loads(path.read_text(encoding="utf-8"))
        return m if isinstance(m.get("beta"), list) and len(m["beta"]) == len(FEATURES) else None
    except Exception:
        return None


def score(df: pd.DataFrame | None, model: dict | None = None,
          cycles: tuple[int, ...] = CYCLES) -> dict | None:
    """Today's confluence reading for one stock, or None when there is too
    little history (needs ~1.5× the longest cycle) or no target ahead."""
    if df is None or len(df) < int(max(cycles) * 1.5):
        return None
    beta = tuple(model["beta"]) if model else DEFAULT_BETA
    rows, ctx = history(df, beta, cycles)
    t = len(ctx["close"]) - 1
    done = [h for rb, h in ctx["resolved"] if rb <= t]
    p_hit = (sum(done) + PRIOR_STRENGTH * PRIOR_HIT) / (len(done) + PRIOR_STRENGTH)
    snap = _snapshot(ctx["preps"], ctx["close"], t, float(ctx["atr"][t]), p_hit, beta)
    if not snap:
        return None
    snap.update(calibrated=bool(model), n_signals=len(done), n_hits=int(sum(done)),
                ev_long=snap["EV"] if snap["side"] > 0 else None,
                ev_short=snap["EV"] if snap["side"] < 0 else None)
    return snap


# ──────────────────────────────────────────────────────────────────────────────
# Calibration — logistic regression in numpy, out-of-sample reliability
# ──────────────────────────────────────────────────────────────────────────────
def fit_logistic(X: np.ndarray, y: np.ndarray, l2: float = 1e-2,
                 iters: int = 3000, lr: float = 0.5) -> np.ndarray:
    """Plain gradient descent; the bias term is not penalised."""
    X, y = np.asarray(X, float), np.asarray(y, float)
    b = np.zeros(X.shape[1])
    pen = np.full(X.shape[1], l2)
    pen[0] = 0.0
    for _ in range(iters):
        g = X.T @ (_sigmoid(X @ b) - y) / len(y) + pen * b
        b -= lr * g
    return b


def reliability(P: np.ndarray, y: np.ndarray, bins: int = 10) -> list[dict]:
    """Predicted vs realised hit rate per probability bucket (empty buckets dropped)."""
    edges = np.linspace(0, 1, bins + 1)
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (P >= lo) & (P < hi if hi < 1 else P <= hi)
        if m.sum():
            out.append({"bucket": f"{lo:.1f}–{hi:.1f}", "n": int(m.sum()),
                        "predicted": float(P[m].mean()), "actual": float(y[m].mean())})
    return out


def calibrate(frames: dict[str, pd.DataFrame | None], *, label: str = "",
              train_frac: float = 0.7, min_rows: int = 200,
              save_to: Path | None = MODEL_FILE) -> dict:
    """Fit β on every resolved snapshot across `frames`.

    Split by DATE, not by row: the first `train_frac` of the timeline trains,
    the rest is the out-of-sample check the reliability table reports. The
    saved model is then refit on everything.
    """
    rows = []
    for sym, df in frames.items():
        if df is None or len(df) < int(max(CYCLES) * 1.5):
            continue
        try:
            r, _ = history(df)
        except Exception as e:                       # one bad frame must not sink the fit
            _log.warning("fld_confluence: history failed for %s: %s", sym, e)
            continue
        rows += [x for x in r if x["hit"] is not None]
    if len(rows) < min_rows:
        return {"ok": False, "n": len(rows),
                "reason": f"Only {len(rows)} resolved FLD signals — at least {min_rows} are "
                          f"needed for a fit worth trusting."}
    rows.sort(key=lambda r: r["date"])
    cut = rows[int(len(rows) * train_frac)]["date"]
    tr = [r for r in rows if r["date"] < cut]
    te = [r for r in rows if r["date"] >= cut]
    Xtr, ytr = np.array([r["x"] for r in tr]), np.array([r["hit"] for r in tr])
    Xte, yte = np.array([r["x"] for r in te]), np.array([r["hit"] for r in te])
    b_tr = fit_logistic(Xtr, ytr)
    Pte = _sigmoid(Xte @ b_tr)
    base = float(ytr.mean())
    brier = float(np.mean((Pte - yte) ** 2))
    brier_base = float(np.mean((base - yte) ** 2))
    X, y = np.array([r["x"] for r in rows]), np.array([r["hit"] for r in rows])
    beta = fit_logistic(X, y)
    model = {"beta": [float(v) for v in beta], "features": list(FEATURES),
             "cycles": list(CYCLES), "n": len(rows), "n_train": len(tr), "n_test": len(te),
             "split_date": cut, "base_rate": float(y.mean()),
             "oos_brier": brier, "oos_brier_baseline": brier_base,
             "oos_skill": 1 - brier / brier_base if brier_base else None,
             "reliability_oos": reliability(Pte, yte), "universe": label,
             "n_symbols": sum(1 for d in frames.values() if d is not None),
             "trained_at": time.strftime("%Y-%m-%d %H:%M")}
    if save_to:
        try:
            save_to.parent.mkdir(parents=True, exist_ok=True)
            save_to.write_text(json.dumps(model, indent=1), encoding="utf-8")
        except Exception as e:
            _log.warning("fld_confluence: could not save model: %s", e)
    return {"ok": True, **model}


# ──────────────────────────────────────────────────────────────────────────────
# CLI — calibrate on the NIFTY Total Market universe
# ──────────────────────────────────────────────────────────────────────────────
def _main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["calibrate"])
    ap.add_argument("--limit", type=int, default=0, help="first N symbols only")
    ap.add_argument("--chunk", type=int, default=100)
    a = ap.parse_args(argv)
    import peer_comparison as pcmp
    import sector_lobby as sl
    syms = sorted(pcmp._constituents())
    if a.limit:
        syms = syms[:a.limit]
    frames: dict[str, Any] = {}
    for i in range(0, len(syms), a.chunk):
        part = syms[i:i + a.chunk]
        frames.update(sl.fetch_frames(part, period="3y"))
        print(f"downloaded {min(i + a.chunk, len(syms))}/{len(syms)}")
    res = calibrate(frames, label=f"NIFTY Total Market ({len(syms)})")
    if not res["ok"]:
        print(res["reason"])
        return 1
    print(f"fitted on {res['n']} signals; base rate {res['base_rate']:.1%}; "
          f"OOS Brier {res['oos_brier']:.4f} vs baseline {res['oos_brier_baseline']:.4f} "
          f"(skill {res['oos_skill']:+.1%})")
    for b in res["reliability_oos"]:
        print(f"  {b['bucket']}  n={b['n']:5d}  predicted {b['predicted']:.2f}  actual {b['actual']:.2f}")
    print("beta:", dict(zip(FEATURES, (round(v, 3) for v in res["beta"]))))
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
