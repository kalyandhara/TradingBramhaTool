"""B-116 — target-reach census. Design: [[analyses/Target-Reach-Census]].

Pre-registered (commit 1762553) before any census number was read. For every
scanner whose cards carry entry/stop/target, replay it through the shared
harness (fresh signals, market fill, fixed exit, Indian costs) and ask whether
its FIRST target is reached more often than the same bracket placed at random
bars of the same stock.

    py -3 tools/target_reach_census.py --control     # Flag & Pole on nifty500[:150]
    py -3 tools/target_reach_census.py               # the census, nifty500[150:300]

Bars are fetched once per panel and frozen in tools/cache/b116/ so a re-run
reads the same bars; per-scanner results (trades included) land beside them.
"""
from __future__ import annotations

import io
import json
import os
import pickle
import sys
import time
import zlib
from multiprocessing import Pool

import numpy as np
import pandas as pd

import backtest as bt

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "b116")
COVERAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "scanner_plan_coverage.json")
DAYS = 1500
K_PLACEBO = 20
N_BOOT = 2000
SEED = 116
MIN_TRADES, MIN_SYMBOLS = 30, 10
# "fresh_plan", not the registered "fresh": deviation 1 on the design page.
SETTINGS = dict(signal_mode="fresh_plan", fill_model="market", exit_model=None,
                cost_model=bt.COST_INDIAN, honor_time_stop=True, keep_trades=True)
CONTROL = {"scanner": "Flag & Pole", "target_rate": 0.338, "stop_rate": 0.540,
           "avg_r": 0.26, "n": 645}
_COLS = ["high", "low", "close", "volume"]

_DATA: dict[str, pd.DataFrame] = {}


def plan_scanners() -> list[str]:
    """The scanners whose cards carry a full plan (B-171's coverage census)."""
    with open(COVERAGE, encoding="utf-8") as f:
        cov = json.load(f)["scanners"]
    return sorted(k for k, v in cov.items() if v.get("with_plan"))


def panel(control: bool) -> list[str]:
    import nse_universe as nu
    syms = nu.symbols("nifty500")
    return syms[:150] if control else syms[150:300]


def load_bars(symbols: list[str], tag: str) -> dict[str, pd.DataFrame]:
    # Pickle is safe here: the only file read is the one this function wrote,
    # in the gitignored tools/cache/b116/, never anything fetched or shared.
    path = os.path.join(OUT_DIR, f"bars_{tag}.pkl")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    import screener_pipeline as sp
    out = {}
    for i, s in enumerate(symbols, 1):
        try:
            df = sp.fetch_ohlcv(s, days=DAYS)
        except Exception:
            df = None
        if df is not None and not df.empty:
            out[s] = df
        print(f"\r  fetched {i}/{len(symbols)}", end="", flush=True)
    print()
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(out, f)
    return out


def harness_frame(df: pd.DataFrame) -> pd.DataFrame:
    """The frame the harness indexes trades against (same dropna + reset)."""
    return df.dropna(subset=_COLS).reset_index(drop=True)


def placebo(df: pd.DataFrame, trade: dict, rng: np.random.Generator,
            k: int = K_PLACEBO, max_bars: int = max(bt.DEFAULT_HORIZONS),
            warmup: int = bt.WARMUP_BARS) -> tuple[float, float] | None:
    """Mean (target hit, R) of the trade's bracket entered at k random bars.

    Same side, same % distance to stop and target, same time stop, same cost,
    entered at the bar's open. Bars are those the harness could have entered on.
    """
    e = float(trade["entry_px"])
    sf = abs(e - float(trade["stop"])) / e
    tf = abs(float(trade["target"]) - e) / e
    short = trade["side"] == "short"
    openp = df["open"].to_numpy(dtype=float)
    lo, hi = warmup + 1, len(df) - max_bars - 1
    if hi <= lo:
        return None
    hits, rs = [], []
    for b in rng.integers(lo, hi + 1, size=k):
        px = openp[b]
        if not px > 0:
            continue
        stop = px * (1 + sf) if short else px * (1 - sf)
        tgt = px * (1 - tf) if short else px * (1 + tf)
        r = bt._simulate_plan(df, int(b), px, stop, tgt, max_bars,
                              trade.get("time_stop"), cost_model=bt.COST_INDIAN,
                              side=trade["side"])
        if r:
            hits.append(1.0 if r["outcome"] == "target" else 0.0)
            rs.append(r["r"])
    if not hits:
        return None
    return float(np.mean(hits)), float(np.mean(rs))


def cluster_ci(by_symbol: dict[str, list[float]], alpha: float,
               n_boot: int = N_BOOT, seed: int = SEED) -> tuple[float, float, float]:
    """Trade-weighted mean, and its symbol-cluster bootstrap interval."""
    keys = sorted(by_symbol)
    sums = np.array([sum(by_symbol[k]) for k in keys])
    cnts = np.array([len(by_symbol[k]) for k in keys])
    point = float(sums.sum() / cnts.sum())
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(keys), size=(n_boot, len(keys)))
    boots = sums[idx].sum(axis=1) / cnts[idx].sum(axis=1)
    lo, hi = np.quantile(boots, [alpha / 2, 1 - alpha / 2])
    return point, float(lo), float(hi)


def label(lo: float, hi: float) -> str:
    if lo > 0:
        return "INFORMATIVE"
    if hi < 0:
        return "WORSE THAN CHANCE"
    return "NO BETTER THAN CHANCE"


def _init(path: str) -> None:
    global _DATA
    with open(path, "rb") as f:
        _DATA = pickle.load(f)


def run_one(name: str) -> dict:
    t0 = time.time()
    res = bt.backtest_scanner(name, sorted(_DATA), _DATA.get, **SETTINGS)
    trades = res.pop("trades", []) or []
    frames = {}
    for tr in trades:
        s = tr["symbol"]
        if s not in frames:
            frames[s] = harness_frame(_DATA[s])
        rng = np.random.default_rng(
            [SEED, zlib.crc32(name.encode()), zlib.crc32(s.encode()), int(tr["t"])])
        p = placebo(frames[s], tr, rng)
        tr["placebo_hit"], tr["placebo_r"] = (p if p else (None, None))
        for k in ("entry_date", "exit_date"):
            if k in tr:
                tr[k] = str(tr[k])[:10]
    return {"scanner": name, "seconds": round(time.time() - t0, 1),
            "n_signals": res.get("n_signals"), "r_metrics": res.get("r_metrics"),
            "trades": trades}


def summarise(rows: list[dict]) -> tuple[list[dict], int, float]:
    qual = []
    for r in rows:
        tr = [t for t in r["trades"] if t.get("placebo_hit") is not None]
        r["n_trades"] = len(tr)
        r["n_symbols"] = len({t["symbol"] for t in tr})
        r["qualifies"] = r["n_trades"] >= MIN_TRADES and r["n_symbols"] >= MIN_SYMBOLS
        if r["qualifies"]:
            qual.append(r)
    alpha = 0.05 / max(1, len(qual))
    out = []
    for r in rows:
        tr = [t for t in r["trades"] if t.get("placebo_hit") is not None]
        rm = r.get("r_metrics") or {}
        row = {"scanner": r["scanner"], "signals": r["n_signals"],
               "trades": r["n_trades"], "symbols": r["n_symbols"],
               "not_actionable": rm.get("plans_not_actionable"),
               "unfilled": rm.get("plans_unfilled"),
               "fill_through_stop": rm.get("plans_fill_through_stop"),
               "fill_past_target": rm.get("plans_fill_past_target")}
        if tr:
            oc = pd.Series([t["outcome"] for t in tr])
            row.update({
                "target_rate": float((oc == "target").mean()),
                "stop_rate": float((oc == "stop").mean()),
                "time_open_rate": float(oc.isin(["time", "open"]).mean()),
                "avg_r": float(np.mean([t["r"] for t in tr])),
                "placebo_target_rate": float(np.mean([t["placebo_hit"] for t in tr])),
                "placebo_avg_r": float(np.mean([t["placebo_r"] for t in tr])),
                "median_bars_to_target": (float(np.median(
                    [t["bars"] for t in tr if t["outcome"] == "target"]))
                    if (oc == "target").any() else None),
            })
        if r["qualifies"]:
            dh, dr = {}, {}
            for t in tr:
                dh.setdefault(t["symbol"], []).append(
                    (1.0 if t["outcome"] == "target" else 0.0) - t["placebo_hit"])
                dr.setdefault(t["symbol"], []).append(t["r"] - t["placebo_r"])
            row["hit_diff"], row["hit_lo"], row["hit_hi"] = cluster_ci(dh, alpha)
            row["r_diff"], row["r_lo"], row["r_hi"] = cluster_ci(dr, alpha)
            row["label"] = label(row["hit_lo"], row["hit_hi"])
        else:
            row["label"] = "TOO FEW"
        out.append(row)
    return out, len(qual), alpha


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    control = "--control" in sys.argv
    tag = "control" if control else "census"
    data = load_bars(panel(control), tag)
    print(f"{tag}: {len(data)} symbols with bars")
    names = [CONTROL["scanner"]] if control else plan_scanners()
    path = os.path.join(OUT_DIR, f"bars_{tag}.pkl")
    rows = []
    with Pool(min(len(names), max(1, (os.cpu_count() or 2) - 2)),
              initializer=_init, initargs=(path,)) as pool:
        for r in pool.imap_unordered(run_one, names):
            print(f"  {r['scanner']}: {len(r['trades'])} trades, {r['seconds']}s",
                  flush=True)
            rows.append(r)
    rows.sort(key=lambda r: r["scanner"])
    with open(os.path.join(OUT_DIR, f"raw_{tag}.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, default=str)
    table, k, alpha = summarise(rows)
    with open(os.path.join(OUT_DIR, f"summary_{tag}.json"), "w", encoding="utf-8") as f:
        json.dump({"k": k, "alpha": alpha, "rows": table}, f, indent=1, default=str)
    print(f"\nqualifying K={k}, two-sided alpha={alpha:.4f}")
    for r in table:
        if "target_rate" not in r:
            print(f"{r['scanner']:<34} no simulated trades (signals {r['signals']})")
            continue
        ci = (f"Δhit {r['hit_diff']:+.3f} [{r['hit_lo']:+.3f},{r['hit_hi']:+.3f}] "
              f"ΔR {r['r_diff']:+.2f} [{r['r_lo']:+.2f},{r['r_hi']:+.2f}]"
              if "hit_diff" in r else "")
        print(f"{r['scanner']:<34} n={r['trades']:>4} sym={r['symbols']:>3} "
              f"tgt {r['target_rate']:.1%} stop {r['stop_rate']:.1%} "
              f"R {r['avg_r']:+.2f} | placebo tgt {r['placebo_target_rate']:.1%} "
              f"R {r['placebo_avg_r']:+.2f} | {ci} {r['label']}")
    if control:
        r = table[0]
        ok = (abs(r["target_rate"] - CONTROL["target_rate"]) <= 0.05
              and abs(r["stop_rate"] - CONTROL["stop_rate"]) <= 0.05
              and abs(r["avg_r"] - CONTROL["avg_r"]) <= 0.10
              and abs(r["trades"] / CONTROL["n"] - 1) <= 0.15)
        print("\nCONTROL", "PASSES" if ok else "FAILS", CONTROL)


if __name__ == "__main__":
    main()
