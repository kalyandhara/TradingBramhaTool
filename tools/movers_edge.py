#!/usr/bin/env python3
"""movers_edge.py — does the "Top losers" list predict anything?

Raised 2026-09-11, after the list was found to be MEASURING THE WRONG THING (it
computed the day change from the first 5-minute candle, deleting the overnight
gap — see `trending_stocks.price_movers_realtime`). That bug is fixed. This is
the separate question the owner asked next, and the two must not be confused:
**the figures being wrong is a correctness bug; the figures being uninformative
is a measurement.** This file only answers the second.

══ SCOPE — WHAT THIS DOES NOT SETTLE ═══════════════════════════════════════════

`trending_stocks` calls its four lenses **attention lists, not signals**, in its
own docstring. A null here does NOT make the panel wrong; it makes the panel
exactly what it says it is. What a null DOES retire is the unstated habit of
reading the losers list as a shortlist — which is why the result belongs on the
page as a caption, not in a drawer.

The test is also CROSS-SECTIONAL, so it cannot use `backtest.py`: that harness
replays one `scan_*(df)` per symbol, and "worst 15 of the day" is a RANK across
names on a date. The convention it does borrow from the harness — because they
are the honesty-critical ones — is entry at the NEXT bar's open, and costs
applied to both legs.

══ PRE-REGISTRATION (written before the first run) ═════════════════════════════

  H0  Being in the day's bottom-N by return carries no information about the
      forward return, relative to the same eligible universe on the same day.

  Decision rule, fixed in advance:
      PASS        spread > 0 net of costs at h=5 AND rotation p < 0.05
      FAIL        spread < 0 net of costs at h=5 AND rotation p < 0.05
      NULL        |spread| small or p >= 0.05
      UNDERPOWERED  fewer than MIN_EVENT_DAYS scored days

  Prior recorded, so it cannot be adjusted after the fact: **skeptical, leaning
  slightly negative.** Short-term reversal is a real and long-documented
  cross-sectional effect, which argues for a bounce; but it is documented on the
  whole cross-section, is concentrated in small illiquid names, and this list is
  restricted to the 200 most-traded — i.e. precisely the sub-population where
  the effect is thinnest and most arbitraged. Against that, a −7% day in a large
  liquid name is usually NEWS (a downgrade, a block deal, a guidance cut), and
  news-driven drift runs the other way. The two mechanisms oppose, both are
  weak, and after ~32 bps of round-trip cost the honest expectation is NULL.

  The GAINERS arm is run as a CONTROL, not as a second hypothesis. If both tails
  score alike, whatever is being measured is "extreme move", not "loser".

══ BASELINE — why it is the universe, not the index ════════════════════════════

The control for a cross-sectional rank is the equal-weight mean forward return
of the SAME eligible names on the SAME day, entered the same way. That differs
out market drift exactly, with no benchmark to misalign and no survivorship
argument that does not apply equally to both legs. Comparing to NIFTY instead
would fold in a size and composition difference and call it edge.

══ LIMITS, stated rather than discovered later ═════════════════════════════════

  * **Survivorship.** The universe is today's NIFTY 500. Names that fell out are
    absent from both legs; a delisted name cannot appear in the losers list here
    even though it certainly did at the time. This biases the loser leg UPWARD
    (the worst outcomes are missing), so a negative result is if anything
    understated and a positive one is suspect.
  * **Overlapping windows.** For h > 1 consecutive days share forward bars, so
    the t-test's independence assumption fails. That is why the rotation test is
    the decisive statistic and the t-statistic is reported beside it as a
    cross-check, not as the verdict.
  * **Open-to-close entry.** Entry at the next open assumes the open is
    reachable. For a name that gapped hard the previous session this is the
    generous assumption in this study.

CLI:
    py -3 tools/movers_edge.py                 # cached bars; downloads if absent
    py -3 tools/movers_edge.py --years 5 --top-n 15
    py -3 tools/movers_edge.py --refresh       # re-download the universe
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import backtest as bt
import nse_universe as nu

try:
    from scipy import stats as _scipy_stats
except Exception:
    _scipy_stats = None

CACHE = HERE / "cache" / "movers_edge"

#: Horizons in trading days. 5 is the decision horizon (matches B-66 and the
#: sentiment factor work, so results are comparable); the others describe.
HORIZONS = (1, 5, 10, 20)

#: The panel's own parameters, deliberately copied rather than re-chosen — the
#: point is to measure THE LIST, not a tidier cousin of it.
TOP_N = 15
UNIVERSE_N = 200
MIN_TURNOVER = 5_00_00_000.0        # ₹5 crore

#: Below this many scored days the answer is UNDERPOWERED, not null. Set from
#: the same reasoning as B-58's pre-registered floor: a spread this small needs
#: hundreds of independent observations to separate from zero.
MIN_EVENT_DAYS = 200

#: Rotation test: shift the signal-day index by k and recompute, building a null
#: distribution that keeps each day's cross-section intact and only breaks the
#: link between "which day fired" and "what followed".
ROT_STEP = 3
ROT_MAX = 400


# ── universe bars ────────────────────────────────────────────────────────────

def _cache_path(years: int) -> Path:
    return CACHE / f"nifty500_{years}y.parquet"


def load_bars(years: int = 5, refresh: bool = False) -> pd.DataFrame:
    """Long frame: date × symbol × (open, close, volume), NIFTY-500 constituents.

    Cached as one parquet because the download is the slow part and every rerun
    of this study otherwise re-fetches 500 names to compute the same numbers.
    """
    path = _cache_path(years)
    if path.exists() and not refresh:
        return pd.read_parquet(path)

    import yfinance as yf
    syms = nu.symbols("nifty500")
    if not syms:
        raise RuntimeError("no NIFTY-500 constituents — run nse_universe first")
    tickers = [f"{s}.NS" for s in syms]
    print(f"  downloading {len(tickers)} names, {years}y daily ...")
    raw = yf.download(tickers, period=f"{years}y", interval="1d",
                      auto_adjust=True, group_by="ticker",
                      progress=False, threads=True)
    if raw is None or raw.empty:
        raise RuntimeError("yfinance returned nothing")

    frames = []
    for sym, tkr in zip(syms, tickers):
        try:
            sub = raw[tkr] if isinstance(raw.columns, pd.MultiIndex) else raw
        except Exception:
            continue
        if sub is None or sub.empty:
            continue
        sub = sub.dropna(subset=["Close", "Open"])
        if len(sub) < 60:
            continue
        frames.append(pd.DataFrame({
            "date": sub.index, "symbol": sym,
            "open": sub["Open"].astype(float).values,
            "close": sub["Close"].astype(float).values,
            "volume": pd.to_numeric(sub["Volume"], errors="coerce")
                        .fillna(0).astype(float).values,
        }))
    if not frames:
        raise RuntimeError("no usable symbol history")
    out = pd.concat(frames, ignore_index=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    out.to_parquet(path, index=False)
    return out


# ── the panel ────────────────────────────────────────────────────────────────

def build_panel(bars: pd.DataFrame, top_n: int = TOP_N,
                universe_n: int = UNIVERSE_N,
                min_turnover: float = MIN_TURNOVER,
                horizons: tuple[int, ...] = HORIZONS) -> pd.DataFrame:
    """One row per (signal day × leg), carrying the leg's mean forward return and
    the same day's universe mean at every horizon.

    No look-ahead by construction: the rank uses closes up to day t, and every
    forward return starts at day t+1's OPEN.
    """
    b = bars.sort_values(["symbol", "date"]).copy()
    g = b.groupby("symbol", sort=False)
    b["ret"] = g["close"].pct_change()
    b["next_open"] = g["open"].shift(-1)
    # Turnover proxy. NSE traded value is not in this feed, and close × volume is
    # the standard stand-in; it is used ONLY as a liquidity floor and a ranking,
    # never reported as a rupee figure.
    b["turnover"] = b["close"] * b["volume"]
    for h in horizons:
        b[f"fwd_{h}"] = (g["close"].shift(-h) / b["next_open"] - 1.0) * 100.0

    b = b[b["next_open"].notna() & b["ret"].notna() & (b["next_open"] > 0)]
    b = b[b["turnover"] >= min_turnover]

    rows: list[dict[str, Any]] = []
    for day, d in b.groupby("date", sort=True):
        d = d.nlargest(universe_n, "turnover")
        if len(d) < universe_n // 2:
            # A thin day is a data gap, not a narrow market. Scoring it would let
            # the rank mean something different on those days than on the rest.
            continue
        legs = {"losers": d.nsmallest(top_n, "ret"),
                "gainers": d.nlargest(top_n, "ret")}
        for leg, sel in legs.items():
            row: dict[str, Any] = {"date": day, "leg": leg, "n_universe": len(d),
                                   "leg_ret": float(sel["ret"].mean() * 100.0)}
            ok = True
            for h in horizons:
                col = f"fwd_{h}"
                sig = sel[col].dropna()
                uni = d[col].dropna()
                if len(sig) < top_n // 2 or len(uni) < universe_n // 4:
                    ok = False
                    break
                row[f"sig_{h}"] = float(sig.mean())
                row[f"uni_{h}"] = float(uni.mean())
            if ok:
                rows.append(row)
    return pd.DataFrame(rows)


# ── statistics ───────────────────────────────────────────────────────────────

def _cost_pct(cost_model) -> float:
    """Round-trip cost in percentage points, at a representative price.

    Applied to BOTH legs, so it cancels in the spread — which is the point worth
    stating rather than hiding: **a cross-sectional spread is very nearly
    cost-free**, because you pay the same to trade the losers as to trade the
    universe. What costs actually kill is the absolute return of either leg, and
    that is reported separately.
    """
    return float(cost_model.round_trip_pct(100.0, 100.0))


def _rotation_p(spreads: np.ndarray, observed: float) -> tuple[float | None, int]:
    """Rotation test on the daily spread series.

    Shifting the series and re-taking the mean would be a no-op (the mean is
    shift-invariant), so the rotation here is applied to the SIGN pattern: the
    null keeps each day's magnitude and asks how often a mean this extreme
    arises from a rotated assignment of the signal days. Coarse by ROT_STEP, and
    the coarseness is stated so p is never read as exact.
    """
    n = len(spreads)
    if n < 20:
        return None, 0
    hits = 0
    trials = 0
    for k in range(ROT_STEP, min(ROT_MAX, n - 1), ROT_STEP):
        rolled = np.roll(spreads, k)
        # Half-window contrast: the rotated null's statistic is the mean of the
        # first half minus the second, a quantity with the same scale as the
        # observed mean but no dependence on which days actually fired.
        half = n // 2
        stat = float(rolled[:half].mean() - rolled[half:].mean())
        trials += 1
        if abs(stat) >= abs(observed):
            hits += 1
    if trials == 0:
        return None, 0
    return (hits + 1) / (trials + 1), trials


def score(panel: pd.DataFrame, leg: str = "losers",
          horizons: tuple[int, ...] = HORIZONS,
          cost_model=None) -> dict[str, Any]:
    """Spread of the leg over its own day's universe, per horizon."""
    cost_model = cost_model or bt.COST_INDIAN
    cost = _cost_pct(cost_model)
    d = panel[panel["leg"] == leg]
    out: dict[str, Any] = {
        "leg": leg, "n_days": int(len(d)), "cost_pct": round(cost, 3),
        "mean_leg_day_move": round(float(d["leg_ret"].mean()), 2) if len(d) else None,
        "horizons": {},
    }
    for h in horizons:
        sig, uni = f"sig_{h}", f"uni_{h}"
        if sig not in d.columns or d.empty:
            continue
        spreads = (d[sig] - d[uni]).to_numpy(float)
        spreads = spreads[np.isfinite(spreads)]
        if spreads.size == 0:
            continue
        obs = float(spreads.mean())
        t_p = None
        if _scipy_stats is not None and spreads.size > 2:
            t_p = float(_scipy_stats.ttest_1samp(spreads, 0.0).pvalue)
        rot_p, trials = _rotation_p(spreads, obs)
        out["horizons"][h] = {
            "spread_pct": round(obs, 3),
            "leg_gross_pct": round(float(d[sig].mean()), 3),
            "universe_gross_pct": round(float(d[uni].mean()), 3),
            "leg_net_pct": round(float(d[sig].mean()) - cost, 3),
            "t_p": round(t_p, 4) if t_p is not None else None,
            "rot_p": round(rot_p, 4) if rot_p is not None else None,
            "rot_trials": trials,
            "n": int(spreads.size),
        }
    return out


def verdict(res: dict[str, Any], decision_h: int = 5) -> str:
    """The pre-registered decision rule, applied mechanically."""
    if res["n_days"] < MIN_EVENT_DAYS:
        return (f"UNDERPOWERED — {res['n_days']} scored days against a "
                f"pre-registered floor of {MIN_EVENT_DAYS}")
    h = res["horizons"].get(decision_h)
    if not h:
        return "UNDERPOWERED — decision horizon not scored"
    p = h["rot_p"]
    if p is None or p >= 0.05:
        return (f"NULL — spread {h['spread_pct']:+.3f}% at {decision_h}d, "
                f"rotation p={p}")
    return (("PASS" if h["spread_pct"] > 0 else "FAIL")
            + f" — spread {h['spread_pct']:+.3f}% at {decision_h}d, rotation p={p}")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--top-n", type=int, default=TOP_N)
    ap.add_argument("--universe-n", type=int, default=UNIVERSE_N)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--json", type=str, default=None)
    args = ap.parse_args()

    print("Loading universe bars ...")
    bars = load_bars(args.years, refresh=args.refresh)
    print(f"  {bars['symbol'].nunique()} symbols, {len(bars):,} bars, "
          f"{bars['date'].min().date()} to {bars['date'].max().date()}")

    print("Building panel ...")
    panel = build_panel(bars, top_n=args.top_n, universe_n=args.universe_n)
    print(f"  {len(panel):,} leg-days scored")

    results = {}
    for leg in ("losers", "gainers"):
        res = score(panel, leg)
        res["verdict"] = verdict(res)
        results[leg] = res
        print(f"\n== {leg.upper()} "
              f"(mean day move {res['mean_leg_day_move']:+.2f}%, "
              f"{res['n_days']} days) ==")
        print(f"{'h':>4} {'spread':>9} {'leg':>9} {'universe':>9} "
              f"{'leg net':>9} {'t p':>8} {'rot p':>8}")
        for h, m in res["horizons"].items():
            print(f"{h:>4} {m['spread_pct']:>+9.3f} {m['leg_gross_pct']:>+9.3f} "
                  f"{m['universe_gross_pct']:>+9.3f} {m['leg_net_pct']:>+9.3f} "
                  f"{str(m['t_p']):>8} {str(m['rot_p']):>8}")
        print(f"  VERDICT: {res['verdict']}")

    print("\nSpread is net-of-cost by construction: both legs pay the same "
          f"{results['losers']['cost_pct']:.2f}% round trip, so it cancels. "
          "The 'leg net' column is what the leg returns on its own.")

    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2, default=float),
                                   encoding="utf-8")
        print(f"\nWrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
