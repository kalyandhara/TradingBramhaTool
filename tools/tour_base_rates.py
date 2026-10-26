"""tour_base_rates.py — the badge on every "Tour this chart" card, measured (B-186).

    py -X utf8 tools/tour_base_rates.py --symbols 300

Runs the SAME `chart_tour.DETECTORS` the tour draws with over the B-165 panel
(nifty500 first 300, last 750 daily bars, `crt_sweep_overlap._fetch`) and writes
`tools/cache/tour_base_rates.json`, which `/api/tour` reads.

The rules are fixed in the spec (§3) and pre-registered on the wiki before the
first real run:

  * an EVENT is the bar a card would first have appeared, computed point-in-time
    on the bars up to that one (a failed breakout counts on the day it fails);
    a state card counts when it turns on, and not again within 20 bars;
  * the OUTCOME is the forward 5/20/60-session log return minus the same stock's
    ordinary forward return; bearish cards are sign-aligned, magnitude cards
    (squeeze, ATR expansion) use |return| against the stock's ordinary |return|;
  * the STATISTIC is the per-symbol mean, t-tested across symbols; h=20 decides;
  * the LABEL is EDGE / INVERTED (Holm < 0.05 across all detectors, sign held in
    2 of 3 time-thirds) / ORDINARY / TOO_FEW (< 30 names or < 100 events).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

import chart_tour as ct

HERE = Path(__file__).resolve().parent
OUT = HERE / "cache" / "tour_base_rates.json"
HORIZONS = (5, 20, 60)
WINDOW = 260                 # bars each point-in-time evaluation sees (SMA200 + slack)
EVAL_BARS = 750
REFRACTORY = 20
MIN_SYMBOLS, MIN_EVENTS = 30, 100
ALPHA = 0.05


# --------------------------------------------------------------------------- #
# Events, point in time
# --------------------------------------------------------------------------- #

def _lower_wick_ok(df: pd.DataFrame) -> np.ndarray:
    """Necessary condition for a bullish sweep: the lower wick is at least half
    the bar (detect_liquidity_sweep's min_wick_ratio 0.5 applies to the part of
    the wick beyond the level, which is never longer than the whole wick)."""
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    rng = h - l
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(rng > 0, (np.minimum(o, c) - l) / rng >= 0.5, False)


def _structure_bars(df: pd.DataFrame) -> set[int]:
    """Candidate bars for the structure card: the event bars of one full-series
    run. Each candidate is re-checked point-in-time, so a non-causal event can
    only be dropped, never invented."""
    import scanner_templates as sc
    res = sc.detect_structure_chain(df, pivot_len=15, confirm="close", fail_win=3, max_swings=15)
    return {int(e["bar"]) for e in (res or {}).get("events", []) if isinstance(e.get("bar"), int)}


def _candidates(df: pd.DataFrame, fn, start: int) -> range | list[int]:
    if fn is ct.det_liquidity_sweep_bull:
        ok = _lower_wick_ok(df)
        return [i for i in range(start, len(df)) if ok[i]]
    if fn is ct.det_structure_break_held:
        return sorted(b for b in _structure_bars(df) if b >= start)
    return range(start, len(df))


def detector_events(df: pd.DataFrame, detectors: dict, start: int, window: int = WINDOW) -> list[dict]:
    """Every event of every detector in `detectors` from bar `start` on, each on
    the first bar it would have been visible, using bars <= that bar only."""
    by_fn: dict[int, tuple] = {}
    for key, det in detectors.items():
        by_fn.setdefault(id(det.fn), (det.fn, []))[1].append(key)
    events: list[dict] = []
    for fn, keys in by_fn.values():
        seen: set[str] = set()
        state_prev: dict[str, bool] = {k: False for k in keys}
        last_ev: dict[str, int] = {}
        for i in _candidates(df, fn, start):
            win = df.iloc[max(0, i - window + 1):i + 1]
            try:
                found = fn(win)
            except Exception:                          # noqa: BLE001 - one bar, not the run
                found = []
            on_now: dict[str, str] = {}
            for f in found:
                if f.detector not in keys:
                    continue
                kind = detectors[f.detector].kind
                if kind == "state":
                    on_now[f.detector] = f.tone
                elif f.id not in seen:
                    seen.add(f.id)
                    events.append({"key": f.detector, "bar": i, "tone": f.tone})
            for k in keys:
                if detectors[k].kind != "state":
                    continue
                now = k in on_now
                if now and not state_prev[k] and (k not in last_ev or i - last_ev[k] >= REFRACTORY):
                    events.append({"key": k, "bar": i, "tone": on_now[k]})
                    last_ev[k] = i
                state_prev[k] = now
    return sorted(events, key=lambda e: (e["bar"], e["key"]))


# --------------------------------------------------------------------------- #
# Outcomes and statistics
# --------------------------------------------------------------------------- #

def symbol_events(sym: str, df: pd.DataFrame, detectors: dict, start: int) -> list[dict]:
    """Events for one symbol with their 5/20/60 excess outcomes attached."""
    c = df["close"].to_numpy(float)
    n = len(c)
    base, base_abs, fwd = {}, {}, {}
    for h in HORIZONS:
        r = np.full(n, np.nan)
        r[:n - h] = np.log(c[h:] / c[:n - h])
        fwd[h] = r
        span = r[start:n - h]
        span = span[np.isfinite(span)]
        base[h] = float(span.mean()) if len(span) else np.nan
        base_abs[h] = float(np.abs(span).mean()) if len(span) else np.nan
    rows = []
    for e in detector_events(df, detectors, start):
        det = detectors[e["key"]]
        sign = -1.0 if e["tone"] == "down" else 1.0
        out = {"sym": sym, "key": e["key"], "date": df.index[e["bar"]], "bar": e["bar"]}
        for h in HORIZONS:
            r = fwd[h][e["bar"]]
            if not np.isfinite(r):
                out[f"x{h}"] = np.nan
            elif det.claim == "magnitude":
                out[f"x{h}"] = abs(r) - base_abs[h]
            else:
                out[f"x{h}"] = sign * (r - base[h])
        rows.append(out)
    return rows


def _t_p(values: np.ndarray) -> float:
    """Two-sided one-sample t-test p against 0."""
    v = values[np.isfinite(values)]
    if len(v) < 2 or np.std(v, ddof=1) == 0:
        return 1.0
    try:
        from scipy import stats
        return float(stats.ttest_1samp(v, 0.0).pvalue)
    except Exception:                                  # noqa: BLE001 - normal approximation
        t = v.mean() / (np.std(v, ddof=1) / math.sqrt(len(v)))
        return float(math.erfc(abs(t) / math.sqrt(2)))


def aggregate(rows: list[dict], keys) -> dict:
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["sym", "key", "date", "x5", "x20", "x60"])
    out = {}
    for k in keys:
        d = df[df["key"] == k] if len(df) else df
        d20 = d.dropna(subset=["x20"]) if len(d) else d
        if not len(d20):
            out[k] = {"n_events": 0, "n_symbols": 0, "mean5": None, "mean20": None, "mean60": None,
                      "p20": None, "thirds": [0, 0, 0]}
            continue
        per_sym = d20.groupby("sym")[["x5", "x20", "x60"]].mean()
        dates = pd.to_datetime(d20["date"])
        lo, hi = dates.min(), dates.max()
        thirds = []
        for a in range(3):
            t0 = lo + (hi - lo) * a / 3
            t1 = lo + (hi - lo) * (a + 1) / 3
            m = (dates >= t0) & ((dates <= t1) if a == 2 else (dates < t1))
            mu = d20.loc[m.values, "x20"].mean() if m.any() else 0.0
            thirds.append(int(np.sign(mu)) if np.isfinite(mu) else 0)
        out[k] = {"n_events": int(len(d20)), "n_symbols": int(per_sym.shape[0]),
                  "mean5": float(per_sym["x5"].mean()), "mean20": float(per_sym["x20"].mean()),
                  "mean60": float(per_sym["x60"].mean()) if per_sym["x60"].notna().any() else None,
                  "p20": _t_p(per_sym["x20"].to_numpy(float)), "thirds": thirds}
    return out


def measure(frames: dict[str, pd.DataFrame], detectors: dict, start: int | None = None) -> dict:
    rows = []
    for sym, df in frames.items():
        s = start if start is not None else max(0, len(df) - EVAL_BARS)
        rows += symbol_events(sym, df, detectors, s)
    return aggregate(rows, list(detectors))


def label(rows: dict) -> dict:
    """Holm across every detector with a p, then the spec §3 label."""
    keys = [k for k, r in rows.items() if isinstance(r.get("p20"), (int, float))]
    ps = np.array([rows[k]["p20"] for k in keys], float)
    holm = {}
    if len(ps):
        order = np.argsort(ps)
        m = len(ps)
        adj = np.maximum.accumulate((m - np.arange(m)) * ps[order])
        for j, idx in enumerate(order):
            holm[keys[idx]] = float(min(adj[j], 1.0))
    out = {}
    for k, r in rows.items():
        r = dict(r)
        r["p20_holm"] = holm.get(k)
        thirds = r.get("thirds") or [0, 0, 0]
        if r.get("n_symbols", 0) < MIN_SYMBOLS or r.get("n_events", 0) < MIN_EVENTS or r.get("mean20") is None:
            r["label"] = "TOO_FEW"
        elif r["p20_holm"] is not None and r["p20_holm"] < ALPHA and r["mean20"] > 0 \
                and sum(t > 0 for t in thirds) >= 2:
            r["label"] = "EDGE"
        elif r["p20_holm"] is not None and r["p20_holm"] < ALPHA and r["mean20"] < 0 \
                and sum(t < 0 for t in thirds) >= 2:
            r["label"] = "INVERTED"
        else:
            r["label"] = "ORDINARY"
        out[k] = r
    return out


# --------------------------------------------------------------------------- #
# The real run
# --------------------------------------------------------------------------- #

def _load(sym: str) -> pd.DataFrame | None:
    import crt_sweep_overlap as ov
    raw = ov._fetch(sym)
    if raw is None:
        return None
    df = raw.rename(columns=str.lower).copy()
    df.index = pd.to_datetime(df.pop("date")).dt.tz_localize("UTC")
    return df[["open", "high", "low", "close", "volume"]].astype(float)


def _worker(sym: str) -> list[dict]:
    df = _load(sym)
    if df is None or len(df) < EVAL_BARS + 60:
        return []
    return symbol_events(sym, df, ct.DETECTORS, len(df) - EVAL_BARS)


def write_atomic(path: Path, payload: dict) -> None:
    """Write via a temp file and os.replace, so the tour never reads half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    os.replace(tmp, path)


def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser(description="Tour base rates over the B-165 panel")
    ap.add_argument("--symbols", type=int, default=300)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    a = ap.parse_args(argv)
    import nse_universe as nu
    syms = list(nu.symbols("nifty500"))[:a.symbols]
    rows: list[dict] = []
    if a.workers > 1:
        from multiprocessing import Pool
        with Pool(a.workers) as pool:
            for k, part in enumerate(pool.imap_unordered(_worker, syms, chunksize=2), 1):
                rows += part
                if k % 25 == 0:
                    print(f"  {k}/{len(syms)} symbols, {len(rows)} events", flush=True)
    else:
        for s in syms:
            rows += _worker(s)
    labelled = label(aggregate(rows, list(ct.DETECTORS)))
    payload = {"asOf": date.today().isoformat(),
               "panel": f"nifty500[:{a.symbols}], last {EVAL_BARS} daily bars, crt_sweep_overlap._fetch",
               "horizons": list(HORIZONS), "decides": 20,
               "rules": "docs/superpowers/specs/2026-10-26-chart-tour-design.md section 3",
               "detectors": labelled}
    write_atomic(Path(a.out), payload)
    for k, r in labelled.items():
        m = r.get("mean20")
        print(f"{k:22s} {r['label']:9s} n={r['n_events']:6d} syms={r['n_symbols']:4d} "
              f"mean20={'' if m is None else f'{m * 100:+.2f}%':>8s} p={r.get('p20')} holm={r.get('p20_holm')}")
    print(Path(a.out))
    return payload


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    main()
