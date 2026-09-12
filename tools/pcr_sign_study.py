"""B-22r — does NIFTY's index PCR carry the direction `sentiment_index` assumes?

    py -3 tools/pcr_sign_study.py                 # primary + controls + secondaries
    py -3 tools/pcr_sign_study.py --json out.json

**Pre-registered before this file was written**, in
`trading-wiki/wiki/analyses/PCR-Sign-Convention-Pre-Registration.md` (committed
first, deliberately). Nothing here may be adjusted after seeing an outcome; the
horizon, the floor, the statistic, the controls and the decision rule are all fixed
there. This module's job is to execute that document, not to improve on it.

Design, restated only as far as the code needs it:

  * factor  = 0.7 x level percentile + 0.3 x slope percentile, POINT-IN-TIME — each
    day is ranked against sessions strictly before it, and no day scores until 60
    prior sessions exist, exactly as `sentiment_index.pcr_factor` refuses to.
  * outcome = ^NSEI close-to-close forward return; 5d DECIDES, 1/10/20d describe.
  * statistic = mean(fwd | top tercile) - mean(fwd | bottom tercile).
  * significance = moving-block bootstrap, block 10, 5,000 resamples, two-sided.
    A plain t-test on overlapping windows overstates significance, so where the two
    disagree the bootstrap governs.
  * floor = 200 scored sessions; below it the answer is UNDERPOWERED, not null.

Why the level percentile is recomputed here rather than imported: `pcr_factor` takes
a history frame and scores ONE day, which is exactly right for production and wrong
for a 500-day walk. `_pct_rank` — the ranking primitive itself — IS imported, so the
one thing that could silently disagree does not.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import pcr_backfill
from sentiment_index import MIN_PCR_HISTORY, PCR_LEVEL_SHARE, _pct_rank

HERE = Path(__file__).resolve().parent

#: Fixed by the pre-registration. Changing any of these after a run invalidates it.
DECISION_HORIZON = 5
HORIZONS = [1, 5, 10, 20]
MIN_SCORED_SESSIONS = 200
BLOCK = 10                  # 2x the decision horizon
N_BOOT = 5_000
N_SHUFFLE = 200
ALPHA = 0.05
SEED = 20260911             # fixed so the run is reproducible


def load_prices() -> pd.DataFrame:
    """^NSEI daily closes. yfinance, the same series input #3 already uses."""
    import yfinance as yf
    h = yf.Ticker("^NSEI").history(period="5y", interval="1d", auto_adjust=False)
    if h is None or h.empty:
        raise RuntimeError("no ^NSEI history")
    out = pd.DataFrame({"close": h["Close"].astype(float)})
    out.index = pd.to_datetime(h.index).tz_localize(None).normalize()
    return out


def build_panel() -> pd.DataFrame:
    """One row per scored session: factor, its parts, and forward returns."""
    hist = pcr_backfill._load_cache()
    if hist.empty:
        raise RuntimeError("no PCR cache — run tools/pcr_backfill.py first")
    hist = hist.copy()
    hist["reading_date"] = pd.to_datetime(hist["reading_date"]).dt.normalize()
    hist = hist.sort_values("reading_date").reset_index(drop=True)

    # Production applies the index liquidity floor before reading anything; days
    # below it are EXCLUDED rather than scored, so the study excludes them too.
    n_all = len(hist)
    hist = hist[hist["liquid"].astype(bool)].reset_index(drop=True)
    n_illiquid = n_all - len(hist)

    px = load_prices()

    rows = []
    for i in range(len(hist)):
        # Point-in-time: strictly earlier sessions only. This is the one place a
        # study like this usually leaks, so the slice is explicit rather than a
        # rolling/expanding call whose window boundary has to be reasoned about.
        past = hist.iloc[:i]
        if len(past) < MIN_PCR_HISTORY:
            continue
        d = hist.loc[i, "reading_date"]
        pcr_now = float(hist.loc[i, "pcr"])
        chg_now = hist.loc[i, "pcr_chg"]

        level_pct = _pct_rank(pcr_now, past["pcr"].tolist())
        past_chg = [float(x) for x in past["pcr_chg"].tolist() if pd.notna(x)]
        slope_pct = (_pct_rank(float(chg_now), past_chg)
                     if pd.notna(chg_now) and past_chg else None)
        if level_pct is None:
            continue

        if slope_pct is None:
            factor = level_pct / 100.0
        else:
            factor = (PCR_LEVEL_SHARE * level_pct + (1 - PCR_LEVEL_SHARE) * slope_pct) / 100.0

        # The bhavcopy is an EOD file, so the earliest a reading can be acted on is
        # the next session's close. Forward returns start from the first close at or
        # after the reading date and are measured from there.
        fwd = {}
        idx = px.index.searchsorted(d)
        if idx >= len(px):
            continue
        base = float(px["close"].iloc[idx])
        for h in HORIZONS:
            j = idx + h
            fwd[f"fwd{h}"] = (float(px["close"].iloc[j]) / base - 1.0) * 100 if j < len(px) else np.nan

        rows.append({
            "date": d, "pcr": pcr_now, "level_pct": level_pct, "slope_pct": slope_pct,
            "factor": factor,
            "factor_level_only": level_pct / 100.0,
            "factor_slope_only": (slope_pct / 100.0) if slope_pct is not None else np.nan,
            **fwd,
        })

    panel = pd.DataFrame(rows)
    panel.attrs["n_illiquid_excluded"] = n_illiquid
    panel.attrs["n_history_rows"] = n_all
    return panel


def tercile_delta(factor: np.ndarray, fwd: np.ndarray) -> tuple[float, float, float, int, int]:
    """mean(fwd | top third of factor) - mean(fwd | bottom third)."""
    ok = np.isfinite(factor) & np.isfinite(fwd)
    f, y = factor[ok], fwd[ok]
    if len(f) < 6:
        return np.nan, np.nan, np.nan, 0, 0
    lo_cut, hi_cut = np.quantile(f, [1 / 3, 2 / 3])
    lo = y[f <= lo_cut]
    hi = y[f >= hi_cut]
    if len(lo) == 0 or len(hi) == 0:
        return np.nan, np.nan, np.nan, len(lo), len(hi)
    return float(hi.mean() - lo.mean()), float(hi.mean()), float(lo.mean()), len(hi), len(lo)


def block_bootstrap_p(factor: np.ndarray, fwd: np.ndarray, observed: float,
                      block: int = BLOCK, n: int = N_BOOT, seed: int = SEED) -> float:
    """Two-sided p for `observed` under a moving-block resample of the PAIRED series.

    Blocks keep the overlap structure of the forward returns intact: 5-day windows
    sampled daily share four of their five days, so independent resampling of single
    rows would treat ~5x more information as present than there is. The factor series
    is held fixed and the outcome series is block-resampled, which is the null of "no
    relationship" while preserving the outcome's own autocorrelation.
    """
    rng = np.random.default_rng(seed)
    ok = np.isfinite(factor) & np.isfinite(fwd)
    f, y = factor[ok], fwd[ok]
    m = len(y)
    if m < block * 3 or not np.isfinite(observed):
        return np.nan
    n_blocks = int(np.ceil(m / block))
    starts_max = m - block
    hits = 0
    for _ in range(n):
        starts = rng.integers(0, starts_max + 1, size=n_blocks)
        draw = np.concatenate([y[s:s + block] for s in starts])[:m]
        d, *_ = tercile_delta(f, draw)
        if np.isfinite(d) and abs(d) >= abs(observed):
            hits += 1
    return (hits + 1) / (n + 1)


def welch_t(factor: np.ndarray, fwd: np.ndarray) -> tuple[float, float]:
    from scipy import stats
    ok = np.isfinite(factor) & np.isfinite(fwd)
    f, y = factor[ok], fwd[ok]
    if len(f) < 6:
        return np.nan, np.nan
    lo_cut, hi_cut = np.quantile(f, [1 / 3, 2 / 3])
    lo, hi = y[f <= lo_cut], y[f >= hi_cut]
    t, p = stats.ttest_ind(hi, lo, equal_var=False)
    return float(t), float(p)


def run_arm(panel: pd.DataFrame, col: str, horizon: int) -> dict:
    f = panel[col].to_numpy(dtype=float)
    y = panel[f"fwd{horizon}"].to_numpy(dtype=float)
    delta, hi_mean, lo_mean, n_hi, n_lo = tercile_delta(f, y)
    t, p_t = welch_t(f, y)
    p_boot = block_bootstrap_p(f, y, delta)
    return {"arm": col, "horizon": horizon, "delta": delta, "hi_mean": hi_mean,
            "lo_mean": lo_mean, "n_hi": n_hi, "n_lo": n_lo,
            "t": t, "p_t": p_t, "p_boot": p_boot}


def control_planted(panel: pd.DataFrame) -> dict:
    """A factor built FROM the outcome. The study must find this, or it is blind."""
    y = panel[f"fwd{DECISION_HORIZON}"].to_numpy(dtype=float)
    planted = np.where(np.isfinite(y), y, np.nan)
    delta, *_ = tercile_delta(planted, y)
    p = block_bootstrap_p(planted, y, delta)
    return {"delta": delta, "p_boot": p, "passes": bool(np.isfinite(p) and p < 0.01)}


def control_shuffle(panel: pd.DataFrame, observed: float, n: int = N_SHUFFLE,
                    seed: int = SEED) -> dict:
    """Permute the factor against dates. The observed delta must not be typical."""
    rng = np.random.default_rng(seed + 1)
    f = panel["factor"].to_numpy(dtype=float)
    y = panel[f"fwd{DECISION_HORIZON}"].to_numpy(dtype=float)
    deltas = []
    for _ in range(n):
        d, *_ = tercile_delta(rng.permutation(f), y)
        if np.isfinite(d):
            deltas.append(d)
    arr = np.array(deltas)
    frac = float(np.mean(np.abs(arr) >= abs(observed))) if len(arr) and np.isfinite(observed) else np.nan
    return {"n": len(arr), "shuffled_abs_mean": float(np.abs(arr).mean()) if len(arr) else np.nan,
            "frac_as_extreme": frac}


def decide(primary: dict, n_scored: int, controls_ok: bool) -> tuple[str, str]:
    """The pre-registered decision rule, transcribed. No branch is added here."""
    if not controls_ok:
        return "INVALID", ("A control failed, so the run says nothing about PCR — "
                           "a harness that cannot see a planted effect cannot report a null.")
    if n_scored < MIN_SCORED_SESSIONS:
        return "UNDERPOWERED", (
            f"{n_scored} scored sessions against a pre-registered floor of "
            f"{MIN_SCORED_SESSIONS}. Not a null. No code change; item stays open.")
    d, p = primary["delta"], primary["p_boot"]
    if np.isfinite(p) and p < ALPHA and d > 0:
        return "CONFIRMED", ("Trend-following convention holds: the high-PCR tercile "
                             "outperformed. Set convention_measured=True, keep the sign.")
    if np.isfinite(p) and p < ALPHA and d < 0:
        return "BACKWARDS", ("The convention is inverted for NIFTY. Flip "
                             "PCR_SIGN_CONVENTION to contrarian -- legitimate only "
                             "because it was pre-registered. This is the B-44r outcome.")
    return "NULL", ("No measurable direction. Per the pre-registration the factor "
                    "STOPS CARRYING SCORE (reverts to NOT_CHECKED, weight 20 "
                    "renormalises away) and is NOT deleted.")


def main() -> int:
    ap = argparse.ArgumentParser(description="B-22r PCR sign-convention study")
    ap.add_argument("--json", type=str, default=None)
    a = ap.parse_args()

    panel = build_panel()
    n = len(panel)
    print(f"panel: {n} scored sessions "
          f"({panel['date'].min().date() if n else '-'} to {panel['date'].max().date() if n else '-'}), "
          f"from {panel.attrs['n_history_rows']} cached PCR rows "
          f"({panel.attrs['n_illiquid_excluded']} below the liquidity floor, "
          f"{MIN_PCR_HISTORY} consumed as warm-up)")
    if n == 0:
        print("nothing scored -- backfill more history")
        return 1

    primary = run_arm(panel, "factor", DECISION_HORIZON)
    planted = control_planted(panel)
    shuffle = control_shuffle(panel, primary["delta"])
    # A shuffle is a sanity check on the pipeline, not a second significance test:
    # it fails only if the observed delta is unremarkable AND the bootstrap called
    # it significant, which would mean the spread came from drift, not the factor.
    shuffle_ok = not (np.isfinite(primary["p_boot"]) and primary["p_boot"] < ALPHA
                      and np.isfinite(shuffle["frac_as_extreme"]) and shuffle["frac_as_extreme"] > 0.10)
    controls_ok = planted["passes"] and shuffle_ok

    print("\ncontrols")
    print(f"  planted effect : delta {planted['delta']:+.3f}%  p_boot {planted['p_boot']:.4f}  "
          f"{'PASS' if planted['passes'] else 'FAIL'}")
    print(f"  shuffle        : {shuffle['n']} permutations, mean |delta| "
          f"{shuffle['shuffled_abs_mean']:.3f}%, {shuffle['frac_as_extreme']:.1%} as extreme as observed  "
          f"{'PASS' if shuffle_ok else 'FAIL'}")

    print(f"\nPRIMARY (pre-registered decision horizon {DECISION_HORIZON}d, factor = "
          f"{PCR_LEVEL_SHARE:.0%} level / {1 - PCR_LEVEL_SHARE:.0%} slope)")
    print(f"  top tercile  {primary['hi_mean']:+.3f}%  (n={primary['n_hi']})")
    print(f"  bottom       {primary['lo_mean']:+.3f}%  (n={primary['n_lo']})")
    print(f"  delta        {primary['delta']:+.3f}%   p_boot {primary['p_boot']:.4f}   "
          f"(Welch t {primary['t']:+.2f}, p {primary['p_t']:.4f})")

    print("\nDESCRIPTIVE ONLY -- these decide nothing")
    rows = []
    for arm in ["factor", "factor_level_only", "factor_slope_only"]:
        for h in HORIZONS:
            r = run_arm(panel, arm, h)
            rows.append(r)
            flag = "  <- decides" if (arm == "factor" and h == DECISION_HORIZON) else ""
            print(f"  {arm:<18} {h:>2}d  delta {r['delta']:+.3f}%  p_boot "
                  f"{r['p_boot']:.4f}{flag}")

    verdict, why = decide(primary, n, controls_ok)
    print(f"\nVERDICT: {verdict}\n  {why}")

    if a.json:
        Path(a.json).write_text(json.dumps({
            "n_scored": n, "primary": primary, "planted": planted, "shuffle": shuffle,
            "grid": rows, "verdict": verdict, "why": why,
            "preregistration": "trading-wiki/wiki/analyses/PCR-Sign-Convention-Pre-Registration.md",
        }, indent=2, default=str), encoding="utf-8")
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
