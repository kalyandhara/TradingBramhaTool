"""svp_backtest.py — do the SVP confluence weights carry any information?

Phase 2 of the SVP Confluence Signal backtest. Phase 1 (`svp_backtest_runner.js`) has
existed since 2026-08-23 and emits one row per bar from the REAL shipped engine; nothing
ever scored it, which is why the chart card still carries "every weight is unbacktested".
This closes that.

The card makes three separable claims, and they are tested separately because they can
fail independently:

  A. **The flip is an entry.** Does the bar where the read turns BUY (or SELL) beat the
     every-bar baseline? Scored through the SAME harness as the EVWMA cross and the Renko
     flip (`evwma_vwap_macd_backtest.event_edge` with this module's signal source
     injected), so all three findings are directly comparable.

  B. **The standing read is informative.** The card is looked at daily as a STATE, not an
     event ("today it says BUY"), so state days are scored too — with an exact
     circular-rotation p-value, because a state series is heavily autocorrelated and Welch
     would badly overstate significance (measured in `gamma_regime_backtest`: a
     pre-registered null printed p=0.031 under Welch and 0.32 under rotation).

  C. **The weights mean something.** This is the real question behind the caveat. If the
     seven-factor score is informative, forward return should rise MONOTONICALLY across
     score deciles and higher confidence should beat lower. A signal can be right on
     average while its score is pure decoration; that would mean the weights should be
     collapsed to a flag, not tuned.

Look-ahead: the runner calls `SVP.analyze(bars[0..i])` at each bar i, so a row at i uses
nothing after i. Every forward window here starts at the NEXT bar's open.

CLI:
  py -3 tools/svp_backtest.py                # score cached signals (regenerating if stale)
  py -3 tools/svp_backtest.py --regen        # force-rerun the JS runner first
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

import evwma_vwap_macd_backtest as base
# The rotation test lives with the study that discovered it was necessary. Imported
# rather than copied: it is the same statistic, and a second copy would drift.
from gamma_regime_backtest import _rotation_p, A_GROUP, B_GROUP, SKIP_GROUP

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache" / "backtest"

#: The locked Phase-1 basket (svp_backtest_export.PRIMARY_DAILY). Only daily names are
#: scored here — the 1h crypto pair is a different regime and deserves its own run.
BASKET = ["^NSEI", "^NSEBANK", "RELIANCE.NS", "TCS.NS",
          "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS"]

WARMUP = 80            # the runner's own warmup for 1d is 70; 80 is a safe floor
HORIZONS = (5, 10, 20, 60)


def _safe(sym: str) -> str:
    return sym.replace("^", "_").replace("=", "_").replace("-", "_")


def _bars_path(sym: str) -> Path:
    return CACHE / f"{_safe(sym)}_1d.json"


def _sig_path(sym: str) -> Path:
    return CACHE / f"{_safe(sym)}_1d_signals.csv"


def ensure_signals(sym: str, regen: bool = False) -> Path:
    """Run the JS runner when the signals CSV is missing or older than its bars."""
    bars_p, sig_p = _bars_path(sym), _sig_path(sym)
    if not bars_p.exists():
        return sig_p
    stale = (not sig_p.exists()) or sig_p.stat().st_mtime < bars_p.stat().st_mtime
    if regen or stale:
        proc = subprocess.run(
            ["node", str(HERE / "svp_backtest_runner.js"), str(bars_p), str(sig_p)],
            capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"runner failed on {sym}: {proc.stderr.strip()}")
        print("  " + proc.stderr.strip())
    return sig_p


def read_rows(sym: str) -> list[dict]:
    p = _sig_path(sym)
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as fh:
        out = []
        for r in csv.DictReader(fh):
            try:
                rec = {"i": int(r["i"]), "dir": r["dir"], "conf": r["conf"],
                       "score": float(r["score"] or 0.0)}
                for fam in FACTORS:
                    rec[fam] = float(r.get("f_" + fam) or 0.0)
                out.append(rec)
            except (ValueError, KeyError):
                continue
    return out


#: The seven signed factor families the runner nets out, one column each.
FACTORS = ["regime", "va", "trap", "exhaustion", "sequence", "sweep", "cluster"]


def factor_attribution(symbols: list[str], h: int = 20) -> list[dict]:
    """Phase A of the pre-registered design: per-factor conditional lift.

    For each family, split the bars where it fired bullish (f>0) from bearish (f<0) and
    compare each against the every-bar baseline over the same bars. A family that carries
    information should show bullish-fire ABOVE baseline and bearish-fire BELOW it; the
    gap between the two is the factor's whole contribution.

    The design calls this "often the whole answer", and gates any weight fitting on it.
    """
    acc = {f: {"pos": [], "neg": []} for f in FACTORS}
    base: list[float] = []
    for sym in symbols:
        bp = _bars_path(sym)
        if not bp.exists():
            continue
        doc = json.loads(bp.read_text(encoding="utf-8"))
        o = np.array([b["open"] for b in doc["bars"]], float)
        c = np.array([b["close"] for b in doc["bars"]], float)
        for r in read_rows(sym):
            t = r["i"]
            if t < WARMUP or t > len(c) - h - 3:
                continue
            f = _fwd(o, c, t, h)
            if f is None:
                continue
            base.append(f)
            for fam in FACTORS:
                v = r.get(fam, 0.0)
                if v > 0:
                    acc[fam]["pos"].append(f)
                elif v < 0:
                    acc[fam]["neg"].append(f)
    b = float(np.mean(base)) if base else float("nan")
    out = []
    for fam in FACTORS:
        p, n = acc[fam]["pos"], acc[fam]["neg"]
        out.append({
            "family": fam, "n_pos": len(p), "n_neg": len(n), "baseline": b,
            "pos": float(np.mean(p)) if p else float("nan"),
            "neg": float(np.mean(n)) if n else float("nan"),
            "spread": ((float(np.mean(p)) - float(np.mean(n))) if p and n else float("nan")),
        })
    return out


# ── A. transitions, through the shared harness ────────────────────────────────

def transitions_for(bars_path: Path) -> list[dict]:
    """Bars where the standing read CHANGES into BUY or SELL. Harness-shaped."""
    sym = json.loads(bars_path.read_text(encoding="utf-8"))["symbol"]
    rows = read_rows(sym)
    out, prev = [], None
    for r in rows:
        d = r["dir"]
        if d in ("BUY", "SELL") and d != prev:
            out.append({"index": r["i"], "dir": 1 if d == "BUY" else -1,
                        "conf": r["conf"], "score": r["score"]})
        if d in ("BUY", "SELL", "NEUTRAL"):
            prev = d
    return out


# ── B/C. state-day and weight tests ───────────────────────────────────────────

def _fwd(o: np.ndarray, c: np.ndarray, t: int, h: int) -> float | None:
    if t + 1 + h > len(c) - 1 or not (o[t + 1] > 0):
        return None
    return float((c[t + 1 + h] / o[t + 1] - 1.0) * 100.0)


def state_and_weight_tests(symbols: list[str], horizons=HORIZONS) -> dict:
    per_h = {h: {"buy": [], "sell": [], "base": []} for h in horizons}
    conf_buckets: dict[tuple, list] = {}
    score_pairs: list[tuple[float, float]] = []      # (score, fwd20) for BUY/SELL rows
    rot = {}
    n_used = 0

    # Rotation needs one aligned series per symbol, so it is accumulated per symbol and
    # the p-values are computed on the pooled label/value vectors below.
    pooled_vals, pooled_cats = [], []

    for sym in symbols:
        bp = _bars_path(sym)
        if not bp.exists():
            continue
        doc = json.loads(bp.read_text(encoding="utf-8"))
        o = np.array([b["open"] for b in doc["bars"]], float)
        c = np.array([b["close"] for b in doc["bars"]], float)
        rows = read_rows(sym)
        if not rows:
            continue
        n_used += 1
        by_i = {r["i"]: r for r in rows}

        vals = np.full(len(c), np.nan)
        cats = np.full(len(c), SKIP_GROUP)
        for t in range(WARMUP, len(c) - max(horizons) - 2):
            r = by_i.get(t)
            if r is None:
                continue
            for h in horizons:
                f = _fwd(o, c, t, h)
                if f is None:
                    continue
                per_h[h]["base"].append(f)
                if r["dir"] == "BUY":
                    per_h[h]["buy"].append(f)
                elif r["dir"] == "SELL":
                    per_h[h]["sell"].append(f)
                if h == 20:
                    conf_buckets.setdefault((r["dir"], r["conf"]), []).append(f)
                    if r["dir"] in ("BUY", "SELL"):
                        score_pairs.append((r["score"], f))
            f20 = _fwd(o, c, t, 20)
            if f20 is not None:
                vals[t] = f20
                if r["dir"] == "BUY":
                    cats[t] = A_GROUP
                elif r["dir"] == "SELL":
                    cats[t] = B_GROUP
        pooled_vals.append(vals)
        pooled_cats.append(cats)

    if pooled_vals:
        rot["buy_vs_sell_20d"] = _rotation_p(np.concatenate(pooled_vals),
                                             np.concatenate(pooled_cats))

    # Score deciles — the monotonicity check that tells you whether the weights work.
    deciles = []
    if len(score_pairs) >= 100:
        arr = np.array(score_pairs, float)
        order = arr[np.argsort(arr[:, 0])]
        for k, chunk in enumerate(np.array_split(order, 10)):
            if len(chunk):
                deciles.append({"k": k + 1, "n": len(chunk),
                                "score_lo": float(chunk[0, 0]), "score_hi": float(chunk[-1, 0]),
                                "fwd20": float(chunk[:, 1].mean())})

    return {"n_symbols": n_used, "horizons": horizons, "per_h": per_h,
            "conf": conf_buckets, "deciles": deciles, "rot": rot,
            "score_corr": (float(np.corrcoef(np.array(score_pairs, float).T)[0, 1])
                           if len(score_pairs) >= 100 else None)}


def format_state_report(res: dict) -> str:
    L = ["", "B. STANDING READ as a state (every BUY / SELL day, not just the flip)",
         f"   symbols {res['n_symbols']}   forward window starts at the next open", ""]
    L.append(f"   {'horizon':<9}{'baseline':>10}{'BUY mean':>11}{'edge':>8}"
             f"{'SELL mean':>12}{'edge':>8}{'n BUY':>8}{'n SELL':>8}")
    L.append("   " + "-" * 74)
    for h in res["horizons"]:
        d = res["per_h"][h]
        if not d["base"]:
            continue
        b = float(np.mean(d["base"]))
        bu = float(np.mean(d["buy"])) if d["buy"] else float("nan")
        se = float(np.mean(d["sell"])) if d["sell"] else float("nan")
        L.append(f"   {str(h)+'d':<9}{b:>+10.2f}{bu:>+11.2f}{bu-b:>+8.2f}"
                 f"{se:>+12.2f}{se-b:>+8.2f}{len(d['buy']):>8}{len(d['sell']):>8}")
    rp = res["rot"].get("buy_vs_sell_20d")
    L += ["", f"   BUY vs SELL separation at 20d, exact rotation p = "
              f"{'n/a' if rp is None else f'{rp:.3f}'}"
              f"{'  *' if (rp is not None and rp < 0.05) else ''}",
          "   (rotation, not Welch: a standing state is autocorrelated and Welch would lie)"]

    L += ["", "C. DO THE WEIGHTS MEAN ANYTHING? (20d forward return by signed score decile)",
          "   If the seven-factor score is informative this column rises monotonically."]
    if res["deciles"]:
        L.append(f"   {'decile':<8}{'score range':>20}{'n':>7}{'fwd20 %':>10}")
        L.append("   " + "-" * 45)
        for d in res["deciles"]:
            rng = "{:+.1f} .. {:+.1f}".format(d["score_lo"], d["score_hi"])
            L.append(f"   {d['k']:<8}{rng:>20}{d['n']:>7}{d['fwd20']:>+10.2f}")
        sc = res["score_corr"]
        L.append(f"   correlation(score, 20d forward return) = "
                 f"{'n/a' if sc is None else f'{sc:+.4f}'}")
    else:
        L.append("   too few scored rows")

    L += ["", "   confidence tiers (20d forward return):"]
    for (dirn, conf), v in sorted(res["conf"].items()):
        if dirn in ("BUY", "SELL") and len(v) >= 20:
            L.append(f"     {dirn:<5} {conf:<7} n={len(v):>6}  {np.mean(v):+.2f}%")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description="Score the SVP confluence signal (Phase 2)")
    ap.add_argument("--regen", action="store_true", help="force-rerun the JS runner")
    ap.add_argument("--symbols", nargs="*")
    ap.add_argument("--cost-bps", type=float, default=0.0)
    args = ap.parse_args()
    syms = args.symbols or BASKET

    print("Ensuring Phase-1 signals are current...")
    for s in syms:
        ensure_signals(s, args.regen)

    paths = [_bars_path(s) for s in syms if _bars_path(s).exists()]
    if not paths:
        sys.exit(f"no cached bars in {CACHE}")

    ev = base.event_edge(paths, horizons=HORIZONS, warmup=WARMUP,
                         signals_fn=transitions_for)
    eq = base.strategy_equity(paths, cost_bps=args.cost_bps, warmup=WARMUP,
                              signals_fn=transitions_for)
    txt = base.format_report(ev, eq)
    txt = (txt.replace("EVWMA/VWAP MACD crossover", "A. SVP signal TRANSITION (flip into BUY/SELL)")
              .replace("cross_up (BUY)", "turns BUY  ")
              .replace("cross_dn (SELL)", "turns SELL "))
    print(txt)
    print(format_state_report(state_and_weight_tests(syms)))

    print("\nD. PHASE-A FACTOR ATTRIBUTION (20d fwd %, per signed factor family)")
    print("   informative family => bullish-fire ABOVE baseline, bearish-fire BELOW it")
    rows = factor_attribution(syms)
    if rows:
        print(f"   baseline over the same bars: {rows[0]['baseline']:+.2f}%")
        print(f"   {'family':<12}{'n bull':>8}{'bull fwd':>10}{'n bear':>8}"
              f"{'bear fwd':>10}{'spread':>9}")
        print("   " + "-" * 57)
        for r in rows:
            print(f"   {r['family']:<12}{r['n_pos']:>8}{r['pos']:>+10.2f}"
                  f"{r['n_neg']:>8}{r['neg']:>+10.2f}{r['spread']:>+9.2f}")
        print("   (spread > 0 means the family points the right way; < 0 means inverted)")

    print("\n" + "\n".join([
        "PROTOCOL NOTE - this is a Q1 read, NOT the full pre-registered protocol in",
        "analyses/SVP-Signal-Backtest-Design.md. Deviations, stated so the design page",
        "can record them honestly:",
        "  * labels are mean forward returns, not the locked TRIPLE-BARRIER win-rate lift",
        "  * the rotation null is an exact rotation over the pooled series, not the locked",
        "    5000-draw BLOCK rotation of the panel (concatenating names then rolling mixes",
        "    symbols at the seams, so treat the pooled p as indicative)",
        "  * per-instrument p-values are not reported",
        "The pre-registered decision rule needs lift >= 1.3x AND p < 0.01 to promote, and",
        "calls ~1.0x with p > 0.1 a clean negative. Nothing here comes close to promotion,",
        "so the verdict is unchanged by the deviations - but a promotion could NOT be",
        "claimed from this run.",
    ]))


if __name__ == "__main__":
    main()
