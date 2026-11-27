"""qullamaggie_edge_study.py — B-147: do the Qullamaggie scanners pick better bars?

    py -3 tools/qullamaggie_edge_study.py            # full run, writes cache/qm147_result.json

PRE-REGISTRATION: trading-wiki/wiki/analyses/Qullamaggie-Edge-Study.md, written
2026-10-14 before this file touched the data. In short:

  * Data: cache/cardinality_deep/ (459 liquid NSE names, ~19y daily), warm-up 252.
  * Signals: actionable `Qullamaggie Breakout` (Breakout tag, 10-session cooldown)
    and `Episodic Pivot` on its gap day. Entry = signal close, stop = signal-day low.
  * PRIMARY: net (29 bps) forward return @5/10/20/60, paired by symbol against the
    all-bar mean, one-sample t on the per-symbol differences, alpha 0.05/4.
    Decisive horizon 20d: PASS / NEGATIVE / NULL / INCONCLUSIVE (< 20 symbols).
  * RIGHT TAIL (reported beside the verdict): stop at the signal low, trail on the
    first close below SMA10, else exit at session 60; share reaching +3R / +5R
    before the stop, win rate, avg win / avg loss, expectancy R — against the same
    plan on a fixed random sample of ordinary bars (<= 100 per symbol, seed 147),
    with a symbol-bootstrap 95% interval on the expectancy difference.
  * SPLITS (descriptive): NIFTYBEES SMA10 > SMA20 on the signal date; EP earnings
    vs not (2021+, earnings date within the 3 calendar days up to the gap day);
    three date-thirds.

The vectorised pre-filter below uses ONLY conditions each scanner itself requires,
so it can skip work but never a signal; the scanner function decides every hit.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scanner_templates as st  # noqa: E402

CACHE = HERE / "cache" / "cardinality_deep"
EARN = HERE / "cache" / "earnings"
OUT = HERE / "cache" / "qm147_result.json"

HORIZONS = (5, 10, 20, 60)
DECISIVE = 20
ALPHA = 0.05 / len(HORIZONS)
COST = 0.0029                 # 29 bps round trip
WARMUP = 252
MIN_SYMBOLS = 20
COOLDOWN = 10
WINDOW = 300                  # bars handed to a scanner — covers its longest lookback
PLAN_MAX = 60
BASE_PER_SYM = 100
SEED = 147
BOOT = 2000
EARN_FROM = date(2021, 1, 1)
SKIP = {"NIFTYBEES", "HDFCNIFTY"}   # index ETFs: the market proxy, not a stock


def _load(path: Path) -> pd.DataFrame | None:
    d = json.loads(path.read_text(encoding="utf-8"))
    df = pd.DataFrame(d.get("bars") or [])
    if df.empty or not {"open", "high", "low", "close", "volume"} <= set(df.columns):
        return None
    df.index = pd.to_datetime(df["time"], unit="s")
    df = df[["open", "high", "low", "close", "volume"]].astype(float)
    df = df.dropna()
    df = df[(df["close"] > 0) & (df["low"] > 0)]
    return df if len(df) > WARMUP + max(HORIZONS) + 10 else None


def _qb_candidates(df: pd.DataFrame) -> np.ndarray:
    """Bars where the breakout scanner's own volume and MA gates already pass."""
    c, v = df["close"], df["volume"]
    sma10, sma20 = c.rolling(10).mean(), c.rolling(20).mean()
    vavg20 = v.shift(1).rolling(20).mean()
    ok = ((v / vavg20) >= 1.5) & (sma10 > sma20) & (sma20 > sma20.shift(5)) & (c.shift(1) >= sma20.shift(1))
    return np.flatnonzero(ok.to_numpy())


def _ep_candidates(df: pd.DataFrame) -> np.ndarray:
    o, c, v = df["open"], df["close"], df["volume"]
    gap = (o / c.shift(1) - 1) * 100
    vavg50 = v.shift(1).rolling(50).mean()
    ok = (gap >= 8.0) & ((v / vavg50) >= 3.0)
    return np.flatnonzero(ok.to_numpy())


def _signals(df: pd.DataFrame) -> dict[str, list[int]]:
    out = {"breakout": [], "ep": []}
    last = -10 ** 9
    for t in _qb_candidates(df):
        if t < WARMUP or t - last < COOLDOWN:
            continue
        card = st.scan_qullamaggie_breakout(df.iloc[max(0, t - WINDOW + 1):t + 1])
        if card and card.get("actionable", True) and "Breakout" in card.get("tags", []):
            out["breakout"].append(int(t)); last = t
    for t in _ep_candidates(df):
        if t < WARMUP:
            continue
        if st.scan_episodic_pivot(df.iloc[max(0, t - WINDOW + 1):t + 1], max_bars_ago=0):
            out["ep"].append(int(t))
    return out


def _fwd(c: np.ndarray, t: int, h: int) -> float | None:
    return None if t + h >= len(c) else (c[t + h] / c[t] - 1) - COST


def _plan(h: np.ndarray, l: np.ndarray, c: np.ndarray, sma10: np.ndarray, t: int) -> dict | None:
    """Entry close[t], stop low[t]; trail on the first close below SMA10."""
    entry, stop = c[t], l[t]
    r = entry - stop
    if not r > 0 or t + PLAN_MAX >= len(c):
        return None
    hit3 = hit5 = False
    exit_px = None
    for j in range(t + 1, t + PLAN_MAX + 1):
        if l[j] <= stop:                       # stop first when both touch one day
            exit_px = stop
            break
        if h[j] >= entry + 3 * r:
            hit3 = True
        if h[j] >= entry + 5 * r:
            hit5 = True
        if c[j] < sma10[j]:
            exit_px = c[j]
            break
    if exit_px is None:
        exit_px = c[t + PLAN_MAX]
    return {"R": (exit_px - entry) / r - COST * entry / r, "hit3": hit3, "hit5": hit5,
            "pct": exit_px / entry - 1 - COST}


def _earn_dates() -> dict[str, list[date]]:
    out = {}
    for f in EARN.glob("*.json"):
        try:
            ev = json.loads(f.read_text(encoding="utf-8")).get("events") or []
            out[f.stem] = sorted(date.fromisoformat(e["date"]) for e in ev if e.get("date"))
        except Exception:
            continue
    return out


def _paired(per_sym: dict[str, dict], key: str, h: int) -> dict:
    diffs = [s[key][h] - s["base"][h] for s in per_sym.values()
             if s[key].get(h) is not None and s["base"].get(h) is not None]
    if len(diffs) < 2:
        return {"n_sym": len(diffs)}
    t, p = sp_stats.ttest_1samp(diffs, 0.0)
    return {"n_sym": len(diffs), "mean_diff_pct": round(float(np.mean(diffs)) * 100, 3),
            "median_diff_pct": round(float(np.median(diffs)) * 100, 3),
            "pos_share": round(float(np.mean(np.array(diffs) > 0)), 3),
            "t": round(float(t), 3), "p": float(p)}


def _tail(trades: list[dict]) -> dict:
    if not trades:
        return {"n": 0}
    R = np.array([x["R"] for x in trades])
    wins, losses = R[R > 0], R[R <= 0]
    return {"n": len(R), "win_rate": round(float((R > 0).mean()), 3),
            "hit3R": round(float(np.mean([x["hit3"] for x in trades])), 4),
            "hit5R": round(float(np.mean([x["hit5"] for x in trades])), 4),
            "avg_win_R": round(float(wins.mean()), 3) if len(wins) else None,
            "avg_loss_R": round(float(losses.mean()), 3) if len(losses) else None,
            "win_loss_ratio": round(float(wins.mean() / -losses.mean()), 3)
            if len(wins) and len(losses) and losses.mean() < 0 else None,
            "expectancy_R": round(float(R.mean()), 4)}


def _boot_diff(sig: dict[str, list[float]], base: dict[str, list[float]]) -> list[float] | None:
    syms = [s for s in sig if sig[s] and base.get(s)]
    if len(syms) < 2:
        return None
    rng = np.random.default_rng(SEED)
    out = []
    for _ in range(BOOT):
        pick = rng.choice(syms, size=len(syms), replace=True)
        a = np.concatenate([sig[s] for s in pick]); b = np.concatenate([base[s] for s in pick])
        out.append(a.mean() - b.mean())
    return [round(float(np.percentile(out, 2.5)), 4), round(float(np.percentile(out, 97.5)), 4)]


def _verdict(primary: dict) -> str:
    d = primary.get(DECISIVE, {})
    if d.get("n_sym", 0) < MIN_SYMBOLS:
        return "INCONCLUSIVE"
    if d["p"] < ALPHA:
        return "PASS" if d["mean_diff_pct"] > 0 else "NEGATIVE"
    return "NULL"


def run() -> dict:
    t0 = time.time()
    files = [f for f in sorted(CACHE.glob("*_1d.json")) if f.stem.replace("_1d", "") not in SKIP]
    nb = _load(CACHE / "NIFTYBEES_1d.json")
    mom = None
    if nb is not None:
        mom = (nb["close"].rolling(10).mean() > nb["close"].rolling(20).mean())
        mom = mom[nb["close"].rolling(20).mean().notna()]
    earn = _earn_dates()
    rng = np.random.default_rng(SEED)

    per = {k: {} for k in ("breakout", "ep")}
    tails = {k: [] for k in ("breakout", "ep")}
    tail_by_sym = {k: {} for k in ("breakout", "ep")}
    base_tail, base_by_sym, base_pct_by_sym = [], {}, {}
    pct_by_sym = {k: {} for k in ("breakout", "ep")}
    events = {k: [] for k in ("breakout", "ep")}
    n_sym = n_bars = 0
    for i, f in enumerate(files, 1):
        sym = f.stem.replace("_1d", "")
        df = _load(f)
        if df is None:
            continue
        n_sym += 1; n_bars += len(df)
        c, h, l = (df[x].to_numpy() for x in ("close", "high", "low"))
        sma10 = df["close"].rolling(10).mean().to_numpy()
        idx = np.arange(WARMUP, len(df))
        base = {hz: float(np.mean(c[WARMUP + hz:] / c[WARMUP:len(c) - hz] - 1) - COST)
                for hz in HORIZONS}
        sample = rng.choice(idx[idx + PLAN_MAX < len(c)], size=min(BASE_PER_SYM, int((idx + PLAN_MAX < len(c)).sum())),
                            replace=False) if (idx + PLAN_MAX < len(c)).any() else []
        bt = [x for x in (_plan(h, l, c, sma10, int(t)) for t in sample) if x]
        base_tail += bt
        base_by_sym[sym] = [x["R"] for x in bt]
        base_pct_by_sym[sym] = [x["pct"] for x in bt]
        sig = _signals(df)
        for kind, ts in sig.items():
            if not ts:
                continue
            fwd = {hz: [r for r in (_fwd(c, t, hz) for t in ts) if r is not None] for hz in HORIZONS}
            per[kind][sym] = {"sig": {hz: (float(np.mean(v)) if v else None) for hz, v in fwd.items()},
                              "base": base, "n": len(ts)}
            trades = []
            for t in ts:
                pl = _plan(h, l, c, sma10, t)
                d = df.index[t].date()
                m = None
                if mom is not None and df.index[t] in mom.index:
                    m = bool(mom.loc[df.index[t]])
                e = None
                if kind == "ep" and d >= EARN_FROM and sym in earn:
                    e = any(0 <= (d - x).days <= 3 for x in earn[sym])
                events[kind].append({"sym": sym, "date": d.isoformat(), "fwd20": _fwd(c, t, 20),
                                     "mom": m, "earn": e, "R": pl["R"] if pl else None})
                if pl:
                    trades.append(pl)
            tails[kind] += trades
            tail_by_sym[kind][sym] = [x["R"] for x in trades]
            pct_by_sym[kind][sym] = [x["pct"] for x in trades]
        if i % 50 == 0:
            print(f"  {i}/{len(files)} symbols · {time.time() - t0:.0f}s", flush=True)

    result = {"run": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "n_symbols": n_sym, "n_bars": n_bars, "baseline_plan": _tail(base_tail)}
    for kind in ("breakout", "ep"):
        primary = {hz: _paired({s: {"sig": v["sig"], "base": v["base"]} for s, v in per[kind].items()}, "sig", hz)
                   for hz in HORIZONS}
        ev = events[kind]

        def _split(pred):
            xs = [e["fwd20"] for e in ev if pred(e) and e["fwd20"] is not None]
            rs = [e["R"] for e in ev if pred(e) and e["R"] is not None]
            return {"n": len(xs), "mean_fwd20_pct": round(float(np.mean(xs)) * 100, 3) if xs else None,
                    "expectancy_R": round(float(np.mean(rs)), 4) if rs else None}

        dates = sorted(e["date"] for e in ev)
        eras = {}
        if len(dates) >= 3:
            cuts = [dates[len(dates) // 3], dates[2 * len(dates) // 3]]
            for name, lo, hi in (("first", "", cuts[0]), ("middle", cuts[0], cuts[1]), ("last", cuts[1], "9999")):
                eras[name] = {"from": lo or dates[0], **_split(lambda e, lo=lo, hi=hi: lo <= e["date"] < hi)}
        result[kind] = {
            "n_signals": len(ev), "n_symbols_with_signal": len(per[kind]),
            "verdict": _verdict(primary),
            "primary": {str(hz): v for hz, v in primary.items()},
            "right_tail": _tail(tails[kind]),
            "expectancy_diff_vs_baseline_R_ci95": _boot_diff(tail_by_sym[kind], base_by_sym),
            "split_momentum": {"on": _split(lambda e: e["mom"] is True),
                               "off": _split(lambda e: e["mom"] is False),
                               "no_reading": _split(lambda e: e["mom"] is None)},
            "split_eras": eras,
            # POST-HOC, added 2026-10-14 after the run: the pre-registered R
            # baseline divides by (close - low) of an ORDINARY bar, which is often
            # ~0, so its R multiples explode (avg win 14.5R) and the comparison is
            # void. The same plan measured in PERCENT has no such denominator.
            "posthoc_plan_pct": {
                "signal_mean_pct": round(float(np.mean([x["pct"] for x in tails[kind]])) * 100, 3) if tails[kind] else None,
                "baseline_mean_pct": round(float(np.mean([x["pct"] for x in base_tail])) * 100, 3) if base_tail else None,
                "diff_ci95_pct": [round(v * 100, 3) for v in (_boot_diff(pct_by_sym[kind], base_pct_by_sym) or [])],
            },
        }
        if kind == "ep":
            result[kind]["split_earnings_2021plus"] = {
                "earnings": _split(lambda e: e["earn"] is True),
                "non_earnings": _split(lambda e: e["earn"] is False)}
    result["elapsed_s"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    return result


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    r = run()
    print(json.dumps({k: (v if k not in ("breakout", "ep") else {
        kk: vv for kk, vv in v.items()}) for k, v in r.items()}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
