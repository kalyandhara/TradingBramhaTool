#!/usr/bin/env python3
"""svp_structure_backtest.py — does the SVP STRUCTURE read carry direction? (B-56)

Phase 2 of the pre-registered test in the wiki page "SVP Structure Signal — Test
Design (pre-registered)". Phase 1 is `svp_structure_runner.js`, which walks the
real engine forward and emits one row per bar.

This is NOT `svp_backtest.py`. That scores the seven-factor weighted COMPOSITE,
which measured a clean negative on 2026-08-29. This scores `SVPSTRUCT.read` — a
separate rule-based construction with no weights and no score. They are kept as
two modules because the composite's study is a published measurement and its
inputs should not shift because a second study arrived.

── What is pre-registered, restated here so the code and the page agree ────────
* **Primary:** spread = mean(fwd | BUY) − mean(fwd | SELL) at **h = 20**.
* **Floor:** 200 BUY days AND 200 SELL days. Below either → INCONCLUSIVE, which
  is NOT a null (the B-58 precedent: 53 events against a floor of 200).
* **Significance:** circular rotation, never Welch. The read is a STATE and
  persists in runs, so consecutive rows share most of their forward window;
  `gamma_regime_backtest` printed p=0.031 under Welch and 0.32 under rotation on
  a pre-registered null.
* **Control:** HOLD should sit near baseline. HOLD departing from baseline while
  BUY/SELL do not would mean the rules select unusual bars without selecting a
  direction — a finding about the filter, not the read.

CLI:
  py -3 -X utf8 tools/svp_structure_backtest.py            # score (regen if stale)
  py -3 -X utf8 tools/svp_structure_backtest.py --regen    # force the JS runner
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from gamma_regime_backtest import _rotation_p, A_GROUP, B_GROUP, SKIP_GROUP

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache" / "backtest"

#: The locked Phase-1 daily basket, identical to the composite's so the two
#: findings are comparable bar-for-bar.
BASKET = ["^NSEI", "^NSEBANK", "RELIANCE.NS", "TCS.NS",
          "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS"]

WARMUP = 80
HORIZONS = (5, 10, 20, 60)
PRIMARY_H = 20

#: Pre-registered minimum per arm. Below it the verdict is INCONCLUSIVE.
FLOOR = 200


def _safe(sym: str) -> str:
    return sym.replace("^", "_").replace("=", "_").replace("-", "_")


def _bars_path(sym: str) -> Path:
    return CACHE / f"{_safe(sym)}_1d.json"


def _struct_path(sym: str) -> Path:
    return CACHE / f"{_safe(sym)}_1d_struct.csv"


def ensure_rows(sym: str, regen: bool = False) -> Path:
    """Run the JS runner when the CSV is missing or older than its bars."""
    bars_p, out_p = _bars_path(sym), _struct_path(sym)
    if not bars_p.exists():
        return out_p
    stale = (not out_p.exists()) or out_p.stat().st_mtime < bars_p.stat().st_mtime
    if regen or stale:
        proc = subprocess.run(
            ["node", str(HERE / "svp_structure_runner.js"), str(bars_p), str(out_p)],
            capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"runner failed on {sym}: {proc.stderr.strip()}")
        if proc.stderr.strip():
            print("  " + proc.stderr.strip())
    return out_p


def read_rows(sym: str) -> list[dict]:
    p = _struct_path(sym)
    if not p.exists():
        return []
    out = []
    with p.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                out.append({"i": int(r["i"]), "read": r["read"],
                            "trend": r.get("trend_dir", ""),
                            "shape": r.get("last_shape", "")})
            except (ValueError, KeyError):
                continue
    return out


def _fwd(o: np.ndarray, c: np.ndarray, t: int, h: int) -> float | None:
    """Forward % return from the NEXT bar's open to the close h bars later.

    Entry at t+1's open is what makes the row usable: a read computed from bars
    up to and including t cannot be acted on at t's close.
    """
    if t + 1 + h > len(c) - 1 or not (o[t + 1] > 0):
        return None
    return float((c[t + 1 + h] / o[t + 1] - 1.0) * 100.0)


def _panel(symbols: list[str], h: int) -> list[tuple[str, np.ndarray, np.ndarray]]:
    """Per-symbol aligned (values, labels) for one horizon.

    Kept PER SYMBOL rather than concatenated because the rotation null needs each
    symbol's own autocorrelation preserved — rolling one glued-together vector
    would shift one symbol's labels onto another symbol's returns at the seams.
    """
    out = []
    for sym in symbols:
        bp = _bars_path(sym)
        if not bp.exists():
            continue
        doc = json.loads(bp.read_text(encoding="utf-8"))
        o = np.array([b["open"] for b in doc["bars"]], float)
        c = np.array([b["close"] for b in doc["bars"]], float)
        vals, labs = [], []
        for r in read_rows(sym):
            t = r["i"]
            if t < WARMUP:
                continue
            f = _fwd(o, c, t, h)
            vals.append(np.nan if f is None else f)
            labs.append(A_GROUP if r["read"] == "BUY"
                        else B_GROUP if r["read"] == "SELL" else SKIP_GROUP)
        if len(vals) >= 50:
            out.append((sym, np.asarray(vals, float), np.asarray(labs, int)))
    return out


def _pooled_spread(panel, shift: int = 0) -> float | None:
    """Pooled mean(BUY) − mean(SELL), with every symbol's labels rolled by `shift`.

    `shift` is taken modulo each symbol's own length so a single offset applies
    across a ragged panel. At shift 0 this is the observed statistic.
    """
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
    """Rotation p for the POOLED spread across a ragged multi-symbol panel.

    The single-series test in `gamma_regime_backtest._rotation_p` enumerates every
    shift of one label vector. Here there are eight vectors of different lengths,
    so the extension is: apply the SAME offset to each symbol (modulo its own
    length) and recompute the pooled statistic. Each symbol's label series keeps
    its own run structure, which is the property the test exists to preserve;
    what changes is only the alignment between labels and returns.

    Shifts are subsampled on an even grid rather than enumerated — the panel is
    ~30k rows and the full enumeration buys precision the third decimal of a
    p-value does not need. The grid is deterministic, so there is no seed.
    """
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
    res = {"horizons": {}, "per_symbol": {}}
    for h in HORIZONS:
        panel = _panel(symbols, h)
        if not panel:
            continue
        buy, sell, hold = (_arm(panel, A_GROUP), _arm(panel, B_GROUP),
                           _arm(panel, SKIP_GROUP))
        base = buy + sell + hold
        spread = _pooled_spread(panel, 0)
        p_rot, n_sh = pooled_rotation_p(panel)
        res["horizons"][h] = {
            "n_buy": len(buy), "n_sell": len(sell), "n_hold": len(hold),
            "buy": float(np.mean(buy)) if buy else float("nan"),
            "sell": float(np.mean(sell)) if sell else float("nan"),
            "hold": float(np.mean(hold)) if hold else float("nan"),
            "base": float(np.mean(base)) if base else float("nan"),
            "spread": spread, "p_rot": p_rot, "n_shifts": n_sh,
        }
        if h == PRIMARY_H:
            for sym, vals, labs in panel:
                ok = np.isfinite(vals)
                res["per_symbol"][sym] = {
                    "n_buy": int(((labs == A_GROUP) & ok).sum()),
                    "n_sell": int(((labs == B_GROUP) & ok).sum()),
                    "buy": float(np.mean(vals[ok & (labs == A_GROUP)]))
                           if ((labs == A_GROUP) & ok).any() else float("nan"),
                    "sell": float(np.mean(vals[ok & (labs == B_GROUP)]))
                            if ((labs == B_GROUP) & ok).any() else float("nan"),
                }
    return res


def verdict(res: dict) -> tuple[str, str]:
    """The pre-registered decision rule, applied mechanically.

    Written as a function so the verdict cannot be argued into existence after
    the fact: it reads only the primary horizon, the floor and the p-value.
    """
    h = res["horizons"].get(PRIMARY_H)
    if not h:
        return "NO DATA", "the primary horizon produced no panel"
    if h["n_buy"] < FLOOR or h["n_sell"] < FLOOR:
        return ("INCONCLUSIVE - UNDERPOWERED",
                f"BUY {h['n_buy']} / SELL {h['n_sell']} against a floor of {FLOOR} each")
    p, sp = h["p_rot"], h["spread"]
    if p is None:
        return "INCONCLUSIVE", "the rotation null could not be computed"
    if sp > 0 and p < 0.05:
        return "PASS", f"spread {sp:+.2f}%, p_rot {p:.3f}"
    if sp < 0 and p < 0.05:
        return ("INVERTED", f"spread {sp:+.2f}%, p_rot {p:.3f} - "
                            f"do NOT ship the mirror; it is a new hypothesis")
    return "NULL", f"spread {sp:+.2f}%, p_rot {p:.3f}"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # pragma: no cover
        pass
    ap = argparse.ArgumentParser(description="B-56 · SVP structure read edge test")
    ap.add_argument("--regen", action="store_true", help="force-rerun the JS runner")
    a = ap.parse_args()

    print("Phase 1 - walking the engine forward")
    for sym in BASKET:
        ensure_rows(sym, regen=a.regen)

    print("\nPhase 2 - scoring\n")
    res = score(BASKET)

    print(f"{'h':>4} {'n BUY':>7} {'n SELL':>7} {'BUY %':>8} {'SELL %':>8} "
          f"{'HOLD %':>8} {'base %':>8} {'spread':>8} {'p_rot':>7}")
    for h in HORIZONS:
        r = res["horizons"].get(h)
        if not r:
            continue
        p = "n/a" if r["p_rot"] is None else f"{r['p_rot']:.3f}"
        star = "  <- primary" if h == PRIMARY_H else ""
        print(f"{h:>4} {r['n_buy']:>7} {r['n_sell']:>7} {r['buy']:>8.2f} "
              f"{r['sell']:>8.2f} {r['hold']:>8.2f} {r['base']:>8.2f} "
              f"{r['spread']:>+8.2f} {p:>7}{star}")

    print(f"\nPer symbol at h={PRIMARY_H}:")
    for sym, r in res["per_symbol"].items():
        print(f"  {sym:<14} BUY {r['n_buy']:>5} {r['buy']:>+7.2f}%   "
              f"SELL {r['n_sell']:>5} {r['sell']:>+7.2f}%")

    v, why = verdict(res)
    print(f"\nVERDICT (pre-registered): {v}\n  {why}")

    ctrl = res["horizons"].get(PRIMARY_H)
    if ctrl:
        gap = ctrl["hold"] - ctrl["base"]
        note = ("near baseline, as required" if abs(gap) < 0.25
                else "DEPARTS from baseline - see the control note in the design page")
        print(f"\nControl - HOLD vs baseline at h={PRIMARY_H}: {gap:+.3f}pp ({note})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
