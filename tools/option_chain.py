"""option_chain.py — strike-level option OI: max pain and OI walls (B-23 / B-28).

The tool has read option OI three ways, and every one of them collapsed the STRIKE
dimension before anyone could look at it:

    nse_oi_momentum  futures only (STF) — options discarded outright
    pcr.py           sums all call OI and all put OI into ONE ratio per underlying
    gamma_exposure   keeps strikes, but INDEX ONLY (IDO) and to compute gamma,
                     not levels

So "where is the option OI actually sitting" had no answer. This module is that
answer, for stocks (STO) and indices (IDO) alike.

── No new network call, and no second parser ─────────────────────────────────
`nse_oi_momentum.fetch_fo_bhavcopy_raw()` already pulls every row. This imports
it, exactly as `pcr.py` and `gamma_exposure.py` do. Three modules now read the
same file for three different questions and none of them re-downloads it.

── What it computes ──────────────────────────────────────────────────────────

**Max pain** — the expiry settlement price at which the total payout to option
HOLDERS is smallest (hence maximum pain for buyers, and the most writers keep):

    pain(K) = SUM_calls OI_c * max(0, K - K_c) + SUM_puts OI_p * max(0, K_p - K)
    max_pain = argmin over candidate K

**OI walls** — the strikes carrying the most open interest:

    highest CALL OI  -> resistance (call writers defend it)
    highest PUT  OI  -> support    (put writers defend it)

── Two correctness rules this module enforces ────────────────────────────────

1. **One expiry at a time.** A max-pain number computed across mixed expiries is
   meaningless — the payoff is settled per expiry, and a far-month strike does
   not pay out on this week's settlement. `load_chain` therefore defaults to the
   NEAREST expiry and always reports which one it used. Passing `expiry="all"`
   is allowed for wall-hunting (where pooled OI is a fair question) but is
   REFUSED for max pain.

2. **OI is in the file's own units.** `gamma_exposure` measured that `OpnIntrst`
   for NIFTY is in index units and already a multiple of lot size, so nothing
   here multiplies by lots either. Max pain and wall RANKING are both invariant
   to a constant scale factor, so this cannot change any level reported — it
   only means the printed OI totals are in the file's units, not lots.

── The claim, and its status ─────────────────────────────────────────────────
"Price gravitates to max pain into expiry" and "an OI wall rejects the first
touch" are the folk claims attached to these numbers. Both are TESTABLE and
NEITHER is tested here. This module ships **levels with context**, labelled
unmeasured, exactly as the backlog scopes B-28. The event study — first-touch
rejection at a wall vs a matched non-wall strike — is the open item, and the
B-19 result (0/41 scanners stable after costs) is the prior to hold while
running it.

CLI:
    py -3 tools/option_chain.py                    # NIFTY, nearest expiry
    py -3 tools/option_chain.py --symbol RELIANCE
    py -3 tools/option_chain.py --symbol NIFTY --expiry all --walls 8
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

import numpy as np
import pandas as pd

import nse_oi_momentum as oi

log = logging.getLogger(__name__)

#: UDiFF instrument types for the two option classes, same mapping as pcr.py.
STOCK_OPTION = "STO"
INDEX_OPTION = "IDO"

#: Underlyings that trade as INDEX options. Everything else is looked up as STO.
INDEX_SYMBOLS = {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNXT50"}

#: A strike with less OI than this is noise on the ranking, not a wall.
MIN_WALL_OI = 1

#: How many strikes each side of spot the "near" summary keeps.
NEAR_STRIKES = 10


def _classify(symbol: str) -> str:
    return INDEX_OPTION if symbol.upper() in INDEX_SYMBOLS else STOCK_OPTION


def load_chain(raw: pd.DataFrame, symbol: str,
               expiry: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Per-strike CE/PE open interest for one underlying.

    `expiry` selects the contract month: None (default) takes the NEAREST expiry,
    a "YYYY-MM-DD" string takes that one, and "all" pools every expiry — which is
    valid for wall-hunting but is refused by `max_pain`, see the module docstring.

    Returns None when the symbol has no option rows in this bhavcopy (a normal
    outcome — not every stock has options), else:
      {"symbol", "class", "expiry", "expiries", "spot", "strikes": DataFrame,
       "trade_date"}
    where `strikes` has columns strike / call_oi / put_oi and is strike-sorted.
    """
    if raw is None or raw.empty or "FinInstrmTp" not in raw.columns:
        return None
    sym = symbol.upper()
    cls = _classify(sym)
    sub = raw[(raw["FinInstrmTp"] == cls) & (raw["TckrSymb"].astype(str).str.upper() == sym)]
    if sub.empty:
        return None

    sub = sub.copy()
    sub["XpryDt"] = pd.to_datetime(sub["XpryDt"], errors="coerce")
    sub = sub[sub["XpryDt"].notna()]
    if sub.empty:
        return None

    expiries = sorted(sub["XpryDt"].dt.strftime("%Y-%m-%d").unique().tolist())
    if expiry == "all":
        chosen = "all"
    elif expiry:
        if expiry not in expiries:
            return None
        chosen = expiry
        sub = sub[sub["XpryDt"].dt.strftime("%Y-%m-%d") == expiry]
    else:
        chosen = expiries[0]
        sub = sub[sub["XpryDt"].dt.strftime("%Y-%m-%d") == chosen]

    # Spot rides along in the same file, so there is no second source to keep in
    # sync — the same reasoning gamma_exposure records for UndrlygPric.
    spot = None
    if "UndrlygPric" in sub.columns:
        vals = pd.to_numeric(sub["UndrlygPric"], errors="coerce").dropna()
        vals = vals[vals > 0]
        if not vals.empty:
            spot = float(vals.iloc[0])

    ce = sub[sub["OptnTp"] == "CE"].groupby("StrkPric")["OpnIntrst"].sum()
    pe = sub[sub["OptnTp"] == "PE"].groupby("StrkPric")["OpnIntrst"].sum()
    if ce.empty and pe.empty:
        return None

    strikes = (pd.DataFrame({"call_oi": ce, "put_oi": pe})
               .fillna(0.0)
               .reset_index()
               .rename(columns={"StrkPric": "strike"}))
    strikes["strike"] = pd.to_numeric(strikes["strike"], errors="coerce")
    strikes = strikes[strikes["strike"].notna()].sort_values("strike").reset_index(drop=True)
    if strikes.empty:
        return None
    strikes["total_oi"] = strikes["call_oi"] + strikes["put_oi"]

    return {
        "symbol": sym,
        "class": "INDEX" if cls == INDEX_OPTION else "STOCK",
        "expiry": chosen,
        "expiries": expiries,
        "spot": spot,
        "strikes": strikes,
    }


def max_pain(chain: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Strike at which option holders collectively receive the least.

    Refuses a pooled-expiry chain: payoff settles per expiry, so summing a
    far-month strike into this week's settlement is not a smaller effect, it is
    a different quantity. Returning a number there would be worse than returning
    nothing.

    Returns {"strike", "pain", "curve": DataFrame(strike, pain)} or None.
    """
    if not chain or chain.get("expiry") == "all":
        return None
    df = chain.get("strikes")
    if df is None or df.empty:
        return None

    K = df["strike"].to_numpy(dtype=float)
    c = df["call_oi"].to_numpy(dtype=float)
    p = df["put_oi"].to_numpy(dtype=float)
    if K.size == 0 or (c.sum() + p.sum()) <= 0:
        return None

    # pain[i] = payout to holders if settlement lands on K[i]. Vectorised as an
    # outer difference: rows = candidate settlements, cols = existing strikes.
    diff = K[:, None] - K[None, :]              # settle - strike
    call_pay = np.clip(diff, 0, None) @ c       # calls pay when settle > strike
    put_pay = np.clip(-diff, 0, None) @ p       # puts  pay when settle < strike
    pain = call_pay + put_pay

    i = int(np.argmin(pain))
    return {
        "strike": float(K[i]),
        "pain": float(pain[i]),
        "curve": pd.DataFrame({"strike": K, "pain": pain}),
    }


def oi_walls(chain: dict[str, Any], n: int = 3,
             above_below_spot: bool = True) -> dict[str, list[dict[str, float]]]:
    """Highest-OI strikes: call walls (resistance) and put walls (support).

    With `above_below_spot` (default) call walls are restricted to strikes AT OR
    ABOVE spot and put walls to strikes AT OR BELOW it — the only side on which
    each reading means anything. A large call OI far below spot is deep-ITM
    inventory, not a ceiling; ranking it as "resistance" would put the strongest
    resistance underneath the price.

    Returns {"resistance": [...], "support": [...]}, strongest first, each entry
    {"strike", "oi", "dist_pct"}.
    """
    out: dict[str, list[dict[str, float]]] = {"resistance": [], "support": []}
    if not chain:
        return out
    df = chain.get("strikes")
    if df is None or df.empty:
        return out
    spot = chain.get("spot")

    def _pick(col: str, side: str) -> list[dict[str, float]]:
        d = df[df[col] >= MIN_WALL_OI]
        if above_below_spot and spot:
            d = d[d["strike"] >= spot] if side == "resistance" else d[d["strike"] <= spot]
        if d.empty:
            return []
        d = d.nlargest(n, col)
        return [{
            "strike": float(r["strike"]),
            "oi": float(r[col]),
            "dist_pct": (round((r["strike"] - spot) / spot * 100, 2) if spot else None),
        } for _, r in d.iterrows()]

    out["resistance"] = _pick("call_oi", "resistance")
    out["support"] = _pick("put_oi", "support")
    return out


def read_levels(symbol: str = "NIFTY", expiry: Optional[str] = None,
                walls: int = 3,
                raw: Optional[pd.DataFrame] = None,
                trade_date: Optional[datetime] = None) -> Optional[dict[str, Any]]:
    """Composed strike-level read: spot, max pain, walls, and where price sits.

    Pass `raw` to reuse a bhavcopy already in hand (scanning many symbols should
    fetch once); omit it and one session is downloaded.
    """
    if raw is None:
        raw, trade_date = oi.fetch_fo_bhavcopy_raw()
    if raw is None or raw.empty:
        return None

    chain = load_chain(raw, symbol, expiry=expiry)
    if chain is None:
        return None

    mp = max_pain(chain)
    w = oi_walls(chain, n=walls)
    spot = chain.get("spot")
    df = chain["strikes"]

    pcr_oi = None
    tot_c = float(df["call_oi"].sum())
    tot_p = float(df["put_oi"].sum())
    if tot_c > 0:
        pcr_oi = round(tot_p / tot_c, 3)

    mp_dist = None
    if mp and spot:
        mp_dist = round((mp["strike"] - spot) / spot * 100, 2)

    return {
        "symbol": chain["symbol"],
        "class": chain["class"],
        "expiry": chain["expiry"],
        "expiries": chain["expiries"],
        "trade_date": trade_date.strftime("%Y-%m-%d") if trade_date else None,
        "spot": spot,
        "max_pain": mp["strike"] if mp else None,
        "max_pain_dist_pct": mp_dist,
        "resistance": w["resistance"],
        "support": w["support"],
        "total_call_oi": tot_c,
        "total_put_oi": tot_p,
        "pcr_oi": pcr_oi,
        "n_strikes": int(len(df)),
        "unmeasured": True,   # see the module docstring — levels, not a signal
    }


def format_levels(r: dict[str, Any]) -> str:
    """Human-readable report for `read_levels`."""
    if not r:
        return "No option chain available for that symbol/session."
    L = [
        f"Strike-level option OI — {r['symbol']} ({r['class']})",
        f"Session {r.get('trade_date') or '?'} · expiry {r['expiry']} "
        f"· {r['n_strikes']} strikes",
        "",
    ]
    spot = r.get("spot")
    L.append(f"  spot          {spot:,.2f}" if spot else "  spot          n/a")
    if r.get("max_pain") is not None:
        d = r.get("max_pain_dist_pct")
        L.append(f"  max pain      {r['max_pain']:,.2f}"
                 + (f"   ({d:+.2f}% from spot)" if d is not None else ""))
    else:
        L.append("  max pain      n/a (pooled expiry — settles per expiry)")
    if r.get("pcr_oi") is not None:
        L.append(f"  PCR (OI)      {r['pcr_oi']:.3f}")
    L.append("")

    def _rows(items, label):
        if not items:
            return [f"  {label}: none above/below spot"]
        out = [f"  {label}"]
        for it in items:
            dist = f"{it['dist_pct']:+.2f}%" if it.get("dist_pct") is not None else "  n/a"
            out.append(f"    {it['strike']:>12,.2f}  OI {it['oi']:>15,.0f}  {dist}")
        return out

    L += _rows(r["resistance"], "Call walls (resistance)")
    L += [""]
    L += _rows(r["support"], "Put walls (support)")
    L += [
        "",
        "  ⚠ Levels with context, NOT a signal. 'Price gravitates to max pain' and",
        "    'a wall rejects the first touch' are both untested here — the event",
        "    study (first touch at a wall vs a matched non-wall strike) is open.",
    ]
    return "\n".join(L)


def main() -> None:
    import argparse, io, sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    logging.basicConfig(level=logging.WARNING)

    ap = argparse.ArgumentParser(description="B-23 strike-level option OI")
    ap.add_argument("--symbol", default="NIFTY")
    ap.add_argument("--expiry", default=None,
                    help="YYYY-MM-DD, or 'all' to pool every expiry (no max pain)")
    ap.add_argument("--walls", type=int, default=3)
    ap.add_argument("--list-expiries", action="store_true")
    a = ap.parse_args()

    raw, td = oi.fetch_fo_bhavcopy_raw()
    if raw is None or raw.empty:
        print("No F&O bhavcopy reachable in the lookback window.")
        return

    if a.list_expiries:
        ch = load_chain(raw, a.symbol, expiry="all")
        if not ch:
            print(f"No option rows for {a.symbol}.")
            return
        print(f"{ch['symbol']} expiries: " + ", ".join(ch["expiries"]))
        return

    r = read_levels(a.symbol, expiry=a.expiry, walls=a.walls, raw=raw, trade_date=td)
    print(format_levels(r))


if __name__ == "__main__":
    main()
