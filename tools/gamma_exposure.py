"""gamma_exposure.py — naive dealer GEX for NSE index options, from the F&O bhavcopy.

B-44. A **volatility-regime** read, not a direction one: dealer gamma determines which
way market makers must trade to stay delta-neutral, so its sign says whether hedging
flow damps moves or amplifies them.

    positive dealer gamma -> hedging SELLS rallies / BUYS dips -> vol damped, breakouts fail
    negative dealer gamma -> hedging BUYS rallies / SELLS dips -> vol amplified

See concepts/Gamma-Exposure-GEX.md for the mechanism and concepts/Put-Call-Ratio.md for
the sibling read off the same rows.

── No new network call ───────────────────────────────────────────────────────
`nse_oi_momentum._download_bhavcopy` already pulls the whole F&O bhavcopy and
`nse_oi_momentum.fetch_fo_bhavcopy` throws away everything that is not `STF`. The
discarded `IDO` index-option rows — the same ones `pcr.py` reclaimed for Put-Call Ratio —
carry every field this needs:

    StrkPric  OptnTp  OpnIntrst  SttlmPric  XpryDt  UndrlygPric

`UndrlygPric` in particular means spot comes from the same file, so there is no second
source to keep in sync. The fetch is imported, never re-implemented.

── The scope limit, stated up front ─────────────────────────────────────────
Bhavcopy is **END-OF-DAY**. The trader this came from uses a live pre-open gamma read for
a 90-minute intraday session; that is NOT what this is and must not be built into one.
What this produces is a DAILY gamma-regime series — a volatility-regime input at the
swing horizon, next to the RISK-ON/RISK-OFF gate. Treating an EOD profile as an intraday
level map would be the same category error as reading yesterday's close as a live quote.

── The naive convention, named so it can be blamed ───────────────────────────
"Naive" GEX assumes a fixed customer/dealer split rather than inferring it from
trade-level data (which needs CBOE-style licensed feeds, US-index-only and ~$300/month):

    customers BUY puts (protection)      -> dealers are SHORT put gamma
    customers SELL calls (overwriting)   -> dealers are LONG  call gamma

    GEX = SUM(call gamma x OI) - SUM(put gamma x OI), scaled

That assumption is the single biggest source of error, it is a US-equity-market folk
model, and NSE's participant mix is not the US one. If the regime split measures as a
null, suspect THIS before suspecting the mechanism — see `gamma_regime_backtest.py`.

── RETIRED AS A RESEARCH INSTRUMENT (B-44r, 2026-09-05) ───────────────────────
It DID measure null, and the suspicion above was then tested rather than left standing.
B-44: the regime split moved forward vol by +0.28 / +0.24 / −0.40 pp at 5/10/20d
(p_rot 0.84 / 0.83 / 0.67), wrong sign at the longest horizon. B-44r re-ran the whole
thing under the OPPOSITE convention (both sides short, using `gross_gex_cr`) and the
pre-registered direction came back INVERTED — and mechanically so, because BS gamma
carries 1/sigma, so high vol produces low gamma and vol clusters. Stratifying kills
what remains: the effect lives only in the high-trailing-vol tercile and flips sign in
the low one.

Both conventions have now been tested and NEITHER carries forward-vol information on
NSE indices. This module still runs and still prints an honest daily description of
the open book — that is all it is for. It is NOT a volatility-regime input, it does
not sit next to the RISK-ON/RISK-OFF gate, and the scope note above describing it as
such predates the measurement. The remaining gap is per-strike dealer inventory, which
is data this repo does not have — not another assumption about it.

── Two units facts, both measured rather than assumed ────────────────────────
1. `OpnIntrst` is in **index units, not lots**. Measured on 2026-08-28 NIFTY: 868 of 936
   non-zero OI values are exact multiples of the 65 lot size, and the total (550,300,680)
   is ~8.5M lots — the right order of magnitude. So OI is NOT multiplied by lot size here;
   doing so would inflate every number 65-fold.
2. `SttlmPric` is NSE's settlement price, which is model-derived for illiquid strikes.
   That is a feature for this use — it gives an invertible price at strikes that never
   traded — but it means deep-wing IVs are the exchange's model, not the market's.

CLI:
  py -3 tools/gamma_exposure.py                       # latest session, NIFTY + BANKNIFTY
  py -3 tools/gamma_exposure.py --symbol NIFTY --profile
  py -3 tools/gamma_exposure.py --history 400         # build/extend the daily cache
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests

import nse_oi_momentum as oim

HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / "cache" / "gex"

INDEX_OPTION = "IDO"
DEFAULT_SYMBOLS = ("NIFTY", "BANKNIFTY")

#: India risk-free proxy. Gamma is almost insensitive to r (it enters only through d1),
#: so this is a convenience constant, not a calibration knob.
RISK_FREE = 0.065

#: Numerical guards for the IV inversion.
MIN_T = 0.5 / 365.0     # expiry-day options: gamma -> inf as T -> 0, so floor T
MIN_SIGMA = 0.01
MAX_SIGMA = 3.00
MIN_OI = 1              # zero-OI strikes contribute nothing and cost inversion time
MIN_PRICE = 0.05        # below this the settlement price carries no vol information

#: Gamma-flip search grid: +/-10% of spot is wider than any one-day move, so a flip
#: inside it is the one that matters.
FLIP_SPAN = 0.10
FLIP_STEPS = 161        # ~0.125% resolution

CRORE = 1e7


# ── Black-Scholes pieces ──────────────────────────────────────────────────────

def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _norm_cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def _d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
    return (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))


def bs_price(S: float, K: float, T: float, r: float, sigma: float, kind: str) -> float:
    """European option price. `kind` is 'CE' or 'PE'."""
    if T <= 0 or sigma <= 0:
        return max(0.0, (S - K) if kind == "CE" else (K - S))
    d1 = _d1(S, K, T, r, sigma)
    d2 = d1 - sigma * math.sqrt(T)
    disc = math.exp(-r * T)
    if kind == "CE":
        return S * _norm_cdf(d1) - K * disc * _norm_cdf(d2)
    return K * disc * _norm_cdf(-d2) - S * _norm_cdf(-d1)


def bs_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """d2V/dS2 — identical for calls and puts, which is why GEX needs only a sign."""
    if T <= 0 or sigma <= 0 or S <= 0:
        return 0.0
    return _norm_pdf(_d1(S, K, T, r, sigma)) / (S * sigma * math.sqrt(T))


def implied_vol(price: float, S: float, K: float, T: float, r: float,
                kind: str) -> float | None:
    """Bisection inversion of `bs_price`. None when the price carries no vol info.

    Bisection rather than Newton deliberately: vega collapses in the deep wings, where
    most of the strikes are, and Newton diverges there. 60 halvings of [0.01, 3.0] is
    exact to ~1e-16 and costs nothing at this problem size.
    """
    if not (price > MIN_PRICE) or T <= 0 or S <= 0 or K <= 0:
        return None
    # EUROPEAN lower bound, which is the DISCOUNTED intrinsic — not (S-K) / (K-S).
    # A deep-ITM European put legitimately trades below K-S, because exercise is only
    # available at expiry: P >= K*exp(-rT) - S. Testing against undiscounted intrinsic
    # rejected exactly those rows (caught by test_implied_vol_roundtrip), which quietly
    # thinned the PUT side of the chain and therefore biased the net regime label
    # positive — the error would have been invisible in the output.
    disc_k = K * math.exp(-r * T)
    floor = max(0.0, (S - disc_k) if kind == "CE" else (disc_k - S))
    if price <= floor:
        return None                     # at/below the bound -> no time value to invert
    lo, hi = MIN_SIGMA, MAX_SIGMA
    if bs_price(S, K, T, r, hi, kind) < price:
        return None                     # price above the vol ceiling -> unusable quote
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if bs_price(S, K, T, r, mid, kind) < price:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ── Contract extraction ───────────────────────────────────────────────────────

def _contracts(rows: pd.DataFrame, trade_date: datetime) -> list[dict[str, Any]]:
    """One record per live option row, with an inverted IV attached.

    Rows that cannot yield an IV are DROPPED, not defaulted. A fabricated vol would
    silently invent gamma at exactly the wing strikes where the model is least
    trustworthy; the coverage figure reported alongside every result is how the caller
    sees what was lost.
    """
    out: list[dict[str, Any]] = []
    spot = float(rows["UndrlygPric"].iloc[0])
    for _, r in rows.iterrows():
        oi = float(r["OpnIntrst"])
        if oi < MIN_OI:
            continue
        kind = str(r["OptnTp"])
        if kind not in ("CE", "PE"):
            continue
        K = float(r["StrkPric"])
        expiry = pd.to_datetime(r["XpryDt"]).to_pydatetime()
        T = max((expiry - trade_date).days / 365.0, MIN_T)
        price = float(r["SttlmPric"])
        sigma = implied_vol(price, spot, K, T, RISK_FREE, kind)
        if sigma is None:
            continue
        out.append({"strike": K, "kind": kind, "oi": oi, "T": T, "sigma": sigma,
                    "expiry": expiry.strftime("%Y-%m-%d")})
    return out


def _net_gex_at(contracts: list[dict[str, Any]], S: float) -> float:
    """Net dealer GEX in rupees per 1% move, at a hypothetical spot `S`.

    Per-contract IV is held fixed while spot is varied (sticky-strike). That is an
    assumption, and it is the reason the flip level is a zone rather than a price.
    """
    total = 0.0
    for c in contracts:
        g = bs_gamma(S, c["strike"], c["T"], RISK_FREE, c["sigma"])
        sign = 1.0 if c["kind"] == "CE" else -1.0     # the naive convention; see header
        total += sign * g * c["oi"] * S * S * 0.01
    return total


def _gamma_flip(contracts: list[dict[str, Any]], spot: float) -> float | None:
    """Spot level where net GEX crosses zero — the regime boundary.

    Returns the crossing NEAREST spot, because that is the one price has to travel
    through next. None when the profile keeps one sign across the whole +/-10% grid,
    which is a real and common state, not a failure.
    """
    lo, hi = spot * (1 - FLIP_SPAN), spot * (1 + FLIP_SPAN)
    step = (hi - lo) / (FLIP_STEPS - 1)
    grid = [lo + i * step for i in range(FLIP_STEPS)]
    vals = [_net_gex_at(contracts, s) for s in grid]
    best, best_dist = None, float("inf")
    for i in range(1, len(grid)):
        a, b = vals[i - 1], vals[i]
        if a == 0.0:
            cross = grid[i - 1]
        elif (a < 0) != (b < 0):
            cross = grid[i - 1] + (grid[i] - grid[i - 1]) * (-a) / (b - a)   # linear interp
        else:
            continue
        d = abs(cross - spot)
        if d < best_dist:
            best, best_dist = cross, d
    return best


def compute_gex(raw: pd.DataFrame, symbol: str,
                trade_date: datetime) -> dict[str, Any] | None:
    """Full gamma read for one index underlying on one session.

    `raw` is a full bhavcopy frame (all instrument types) — the same object
    `pcr.build_pcr_table` consumes.
    """
    if raw is None or raw.empty or "FinInstrmTp" not in raw.columns:
        return None
    rows = raw[(raw["FinInstrmTp"] == INDEX_OPTION) & (raw["TckrSymb"] == symbol)]
    rows = rows.dropna(subset=["StrkPric", "OptnTp", "OpnIntrst", "SttlmPric",
                               "XpryDt", "UndrlygPric"])
    if rows.empty:
        return None

    spot = float(rows["UndrlygPric"].iloc[0])
    n_rows = int((rows["OpnIntrst"] >= MIN_OI).sum())
    contracts = _contracts(rows, trade_date)
    if not contracts:
        return None

    # Per-strike aggregation, split by side, for the walls.
    call_by_strike: dict[float, float] = {}
    put_by_strike: dict[float, float] = {}
    for c in contracts:
        g = bs_gamma(spot, c["strike"], c["T"], RISK_FREE, c["sigma"])
        notional = g * c["oi"] * spot * spot * 0.01
        tgt = call_by_strike if c["kind"] == "CE" else put_by_strike
        tgt[c["strike"]] = tgt.get(c["strike"], 0.0) + notional

    net = _net_gex_at(contracts, spot)
    flip = _gamma_flip(contracts, spot)          # 161 x n_contracts evals - compute once
    call_wall = max(call_by_strike, key=call_by_strike.get) if call_by_strike else None
    put_wall = max(put_by_strike, key=put_by_strike.get) if put_by_strike else None

    call_gross = sum(call_by_strike.values())
    put_gross = sum(put_by_strike.values())
    gross = call_gross + put_gross

    return {
        "symbol": symbol,
        "date": trade_date.strftime("%Y-%m-%d"),
        "spot": round(spot, 2),
        "net_gex_cr": round(net / CRORE, 2),           # Rs crore per 1% move
        "call_gex_cr": round(call_gross / CRORE, 2),
        "put_gex_cr": round(-put_gross / CRORE, 2),
        "gross_gex_cr": round(gross / CRORE, 2),
        # Net as a fraction of gross. Measured on the first live run: NIFTY net was
        # 3,498 Cr against ~168,000 Cr gross — the regime LABEL is a ~2% residual of two
        # nearly-cancelling sides. That makes the bare sign fragile with respect to the
        # naive convention and to which strikes survived IV inversion, which is why
        # gamma_regime_backtest splits on this DISTRIBUTION as well as on the sign.
        "net_to_gross": round(net / gross, 4) if gross > 0 else 0.0,
        "regime": "positive" if net > 0 else "negative",
        "gamma_flip": round(flip, 2) if flip is not None else None,
        "call_wall": call_wall,
        "put_wall": put_wall,
        # Coverage: what fraction of live OI rows survived the IV inversion. A low
        # number means the profile is built on a thin slice and should not be trusted.
        "n_contracts": len(contracts),
        "n_rows_oi": n_rows,
        "coverage": round(len(contracts) / n_rows, 3) if n_rows else 0.0,
    }


# ── Daily series (cached) ─────────────────────────────────────────────────────

def _cache_path(symbol: str) -> Path:
    return CACHE_DIR / f"{symbol}_gex_daily.json"


def load_series(symbol: str) -> dict[str, dict[str, Any]]:
    p = _cache_path(symbol)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_series(symbol: str, series: dict[str, dict[str, Any]]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(symbol).write_text(json.dumps(series, indent=0, sort_keys=True),
                                   encoding="utf-8")


def build_history(symbols=DEFAULT_SYMBOLS, sessions: int = 400,
                  max_lookback: int | None = None,
                  verbose: bool = True) -> dict[str, dict[str, Any]]:
    """Walk back `sessions` trading days, computing and CACHING each day's read.

    Settled bhavcopies never change, so a day already in the cache is never refetched —
    the expensive part (~1.2 MB and one round trip per session) is paid once. Days with
    no settled file (holidays) are normal and simply skipped.
    """
    max_lookback = max_lookback or int(sessions * 1.6) + 20
    series = {s: load_series(s) for s in symbols}
    session = requests.Session()
    seen = 0
    for days_back in range(1, max_lookback + 1):
        if seen >= sessions:
            break
        day = datetime.today() - timedelta(days=days_back)
        if day.weekday() >= 5:
            continue
        key = day.strftime("%Y-%m-%d")
        if all(key in series[s] for s in symbols):
            seen += 1
            continue
        raw = oim._download_bhavcopy(session, day)
        if raw is None:
            continue
        seen += 1
        for s in symbols:
            if key in series[s]:
                continue
            rec = compute_gex(raw, s, day)
            if rec:
                series[s][key] = rec
        # Checkpoint as we go. A 480-session walk is ~15 minutes of downloads; losing
        # all of it to one network blip at session 470 would be self-inflicted. Writing
        # every 25 sessions makes an interrupted run resumable — the next invocation
        # skips everything already cached.
        if seen % 25 == 0:
            for s in symbols:
                save_series(s, series[s])
            if verbose:
                print(f"  ...{seen} sessions, back to {key}", flush=True)
    for s in symbols:
        save_series(s, series[s])
    return series


def latest(symbols=DEFAULT_SYMBOLS, max_lookback: int = 7) -> list[dict[str, Any]]:
    """Most recent settled session's read for each symbol."""
    raw, day = oim.fetch_fo_bhavcopy_raw(max_lookback)
    if raw.empty or day is None:
        return []
    out = []
    for s in symbols:
        rec = compute_gex(raw, s, day)
        if rec:
            out.append(rec)
    return out


# ── Reporting ─────────────────────────────────────────────────────────────────

def _regime_line(rec: dict[str, Any]) -> str:
    if rec["regime"] == "positive":
        read = "vol DAMPED - dealers sell rips / buy dips; expect failed breakouts"
    else:
        read = "vol AMPLIFIED - dealers buy rips / sell dips; expect faster, larger moves"
    flip = f"{rec['gamma_flip']:,.0f}" if rec["gamma_flip"] is not None else "none in +/-10%"
    return (f"  {rec['symbol']:<10} {rec['date']}  spot {rec['spot']:>10,.2f}\n"
            f"    net GEX  {rec['net_gex_cr']:>12,.0f} Cr/1%   ({rec['regime'].upper()})  -> {read}\n"
            f"    calls    {rec['call_gex_cr']:>12,.0f} Cr     puts {rec['put_gex_cr']:>12,.0f} Cr\n"
            f"    net/gross{rec.get('net_to_gross', 0.0):>12.1%}   <- the regime label is this thin a residual\n"
            f"    flip     {flip:>12}          call wall {rec['call_wall']:,.0f}   "
            f"put wall {rec['put_wall']:,.0f}\n"
            f"    coverage {rec['coverage']:>12.0%} of {rec['n_rows_oi']} live-OI rows")


def main() -> None:
    ap = argparse.ArgumentParser(description="Naive dealer GEX for NSE index options")
    ap.add_argument("--symbol", nargs="*", default=list(DEFAULT_SYMBOLS))
    ap.add_argument("--history", type=int, default=0,
                    help="build/extend the cached daily series over N sessions")
    ap.add_argument("--profile", action="store_true",
                    help="print the cached series tail instead of a single reading")
    args = ap.parse_args()
    symbols = tuple(args.symbol)

    if args.history:
        print(f"Building GEX history ({args.history} sessions, cached in {CACHE_DIR})")
        series = build_history(symbols, args.history)
        for s in symbols:
            days = sorted(series[s])
            if days:
                print(f"  {s:<10} {len(days)} sessions  {days[0]} .. {days[-1]}")
        return

    if args.profile:
        for s in symbols:
            ser = load_series(s)
            print(f"\n{s}: {len(ser)} cached sessions")
            for k in sorted(ser)[-10:]:
                r = ser[k]
                print(f"  {k}  spot {r['spot']:>10,.2f}  net {r['net_gex_cr']:>12,.0f} Cr  "
                      f"{r['regime']}")
        return

    print("Naive dealer GEX - EOD bhavcopy (see module header for the scope limit)\n")
    for rec in latest(symbols):
        print(_regime_line(rec))
        print()


if __name__ == "__main__":
    main()
