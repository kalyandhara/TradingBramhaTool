"""participant_oi_study.py — B-95: does an extreme FII index-futures short precede gains?

    py -3 tools/participant_oi_study.py     # writes cache/participant_oi_study.json

PRE-REGISTRATION: trading-wiki/wiki/analyses/FII-Short-Squeeze-Study.md, written
2026-10-14 BLIND (no returns, no ratio distribution seen). In short:

  * L = FII index-futures long / (long + short); extreme short = L <= 0.15.
  * NIFTYBEES close (cache/cardinality_deep) as NIFTY; forward 10/20-session return.
  * Statistic: mean fwd return on extreme days minus all other days; p-value from
    exact circular rotation of the state labels (gamma_regime_backtest._rotation_p).
  * T1 raw; T2 (DECISIVE @20) = fwd return minus the mean of its prior-20-session
    return tercile (terciles on the full sample).
  * POSITIVE / NEGATIVE at rotation p < 0.05; NULL otherwise; INCONCLUSIVE under
    30 extreme sessions or 3 episodes.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import participant_oi as poi  # noqa: E402
from gamma_regime_backtest import _rotation_p, A_GROUP, B_GROUP  # noqa: E402

EXTREME = 0.15
HORIZONS = (10, 20)
DECISIVE = 20
PRIOR = 20
ALPHA = 0.05
MIN_DAYS, MIN_EPISODES = 30, 3
EPISODE_GAP = 10
OUT = HERE / "cache" / "participant_oi_study.json"


def _nifty() -> pd.Series:
    bars = json.loads((HERE / "cache" / "cardinality_deep" / "NIFTYBEES_1d.json")
                      .read_text(encoding="utf-8"))["bars"]
    s = pd.Series({datetime.fromtimestamp(b["time"], timezone.utc).date(): float(b["close"])
                   for b in bars if b.get("close")})
    return s.sort_index()


def build() -> pd.DataFrame:
    rows = [(d, poi.index_futures_long_share(r, "FII"), poi.index_futures_long_share(r, "Client"))
            for d, r in poi.load()]
    oi = pd.DataFrame(rows, columns=["date", "fii_long", "client_long"]).dropna(subset=["fii_long"])
    oi = oi.set_index("date").sort_index()
    nifty = _nifty()
    df = oi.join(nifty.rename("close"), how="inner")
    c = df["close"]
    for h in HORIZONS:
        df[f"fwd{h}"] = c.shift(-h) / c - 1
    df["prior"] = c / c.shift(PRIOR) - 1
    df["extreme"] = df["fii_long"] <= EXTREME
    return df


def _resid(df: pd.DataFrame, h: int) -> np.ndarray:
    """Forward return minus the mean of its prior-return tercile (full-sample cuts)."""
    q = df["prior"].quantile([1 / 3, 2 / 3]).to_numpy()
    terc = np.where(df["prior"] <= q[0], 0, np.where(df["prior"] <= q[1], 1, 2))
    terc = np.where(df["prior"].isna(), -1, terc)
    fwd = df[f"fwd{h}"].to_numpy()
    out = np.full(len(df), np.nan)
    for t in (0, 1, 2):
        m = terc == t
        out[m] = fwd[m] - np.nanmean(fwd[m])
    return out


def _test(values: np.ndarray, labels: np.ndarray) -> dict:
    v = np.asarray(values, float)
    ok = np.isfinite(v)
    a, b = v[ok & (labels == A_GROUP)], v[ok & (labels == B_GROUP)]
    return {"n_extreme": int(len(a)), "n_other": int(len(b)),
            "mean_extreme_pct": round(float(a.mean()) * 100, 3) if len(a) else None,
            "mean_other_pct": round(float(b.mean()) * 100, 3) if len(b) else None,
            "diff_pct": round(float(a.mean() - b.mean()) * 100, 3) if len(a) and len(b) else None,
            "rotation_p": _rotation_p(v, labels)}


def episodes(ext: np.ndarray) -> list[int]:
    """Index of the first day of each extreme episode (>= EPISODE_GAP days outside before)."""
    out, last = [], -10 ** 9
    for i, e in enumerate(ext):
        if e and (i - last) > EPISODE_GAP and not ext[max(0, i - EPISODE_GAP):i].any():
            out.append(i)
        if e:
            last = i
    return out


def run() -> dict:
    df = build()
    ext = df["extreme"].to_numpy()
    labels = np.where(ext, A_GROUP, B_GROUP)
    eps = episodes(ext)
    res = {"run": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "sessions": len(df), "from": str(df.index[0]), "to": str(df.index[-1]),
           "extreme_sessions": int(ext.sum()), "episodes": len(eps),
           "episode_starts": [str(df.index[i]) for i in eps],
           "fii_long_share": {"min": round(float(df["fii_long"].min()), 3),
                              "median": round(float(df["fii_long"].median()), 3),
                              "max": round(float(df["fii_long"].max()), 3)}}
    for h in HORIZONS:
        res[f"T1_raw_{h}"] = _test(df[f"fwd{h}"].to_numpy(), labels)
        res[f"T2_controlled_{h}"] = _test(_resid(df, h), labels)
    # Entry-day variant: only the first day of each episode is "extreme".
    entry = np.full(len(df), B_GROUP)
    entry[eps] = A_GROUP
    res["T2_entry_days_20"] = _test(_resid(df, DECISIVE), entry)
    d = res[f"T2_controlled_{DECISIVE}"]
    if res["extreme_sessions"] < MIN_DAYS or res["episodes"] < MIN_EPISODES:
        verdict = "INCONCLUSIVE"
    elif d["rotation_p"] is not None and d["rotation_p"] < ALPHA:
        verdict = "POSITIVE" if d["diff_pct"] > 0 else "NEGATIVE"
    else:
        verdict = "NULL"
    res["verdict"] = verdict
    # Descriptive only: client side.
    res["client_long_share"] = {"median": round(float(df["client_long"].median()), 3),
                                "corr_with_fii": round(float(df["client_long"].corr(df["fii_long"])), 3)}
    OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    return res


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    print(json.dumps(run(), indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
