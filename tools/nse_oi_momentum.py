"""nse_oi_momentum.py — price change vs open-interest change, per stock future.

NSE's own "Change in Open Interest" page (Market Data > Derivatives) shows this
pairing, and reading it answers a question a price chart cannot: is an up-move
being *built* by fresh positions, or merely *unwound* by traders leaving? Two
stocks can post the same gain because buyers stepped in, or because sellers gave
up. OI is what separates them.

That page is not what this module reads, for two reasons:

  1. www.nseindia.com is Akamai-blocked from some environments (the same reason
     india_market_intel.py uses the static archive subdomain). The F&O bhavcopy
     on nsearchives.nseindia.com is not blocked, and screener_pipeline.py
     already depends on its cash-market sibling.
  2. The web page is dominated by index options and has to be filtered by eye
     to isolate stock derivatives. `FinInstrmTp == "STF"` does that
     mechanically, with no judgement call and no missed rows.

The cost of that choice is honest and worth stating: bhavcopy is END-OF-DAY.
There is no intraday read here. That matches how this data should be used for
study anyway, but it does mean the numbers are last session's, not live.

── The trap this module exists to avoid ──────────────────────────────────────

Reading OI off the near-month contract alone is wrong, and wrong in a way that
looks perfectly reasonable. Near expiry, OI drains out of the front contract and
reappears in the next one. That is ROLLOVER: a bookkeeping move, not a single
short covering. On 2026-07-20 (eight days from expiry) RELIANCE showed
-4,569,000 in the front month against +3,268,500 and +409,000 in the two months
behind it. Read the front month alone and you get a large, confident, entirely
fictitious "short covering" print. Summed across the series the real change is
-891,500 on ~124M outstanding, or -0.7%: barely a shrug.

So OI here is always the SERIES total across every listed expiry, and the
distance to expiry is carried through to the verdict, because in the final days
before expiry even the series total gets noisy.

Everything is RULE-BASED and inspectable — no model, no opinion that is not
traceable to a named field. Materiality floors are set from the observed
cross-sectional distribution (see the constants), not picked to look tidy.

NOT ADVICE. This grades what the tape did to positioning last session. It
describes what has already happened; it does not predict what happens next, and
a "supported" move is not a recommendation to take it.
"""

from __future__ import annotations

import io
import zipfile
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import requests

# Same static-archive host and UA convention screener_pipeline.py uses for the
# cash-market bhavcopy. No cookie warm-up needed on this subdomain.
FO_BHAV_URL = ("https://nsearchives.nseindia.com/content/fo/"
               "BhavCopy_NSE_FO_0_0_0_{ymd}_F_0000.csv.zip")
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# UDiFF instrument type for single-stock futures. IDF is index futures, STO/IDO
# are the option chains that swamp the web page.
STOCK_FUTURE = "STF"

# Materiality floors, set from the cross-section on a normal session (210 stock
# futures): median |price change| ran ~0.95% and median |OI change| ~1.3%. These
# sit just above those medians, so a "reading" means the name actually moved
# more than half the F&O universe did rather than drifting.
MIN_PRICE_PCT = 0.5
MIN_OI_PCT = 1.5

# Above-median conviction on both axes. Roughly the top quartile of each.
STRONG_PRICE_PCT = 1.5
STRONG_OI_PCT = 3.0

# Turnover floor. The 10th percentile of series turnover was ~Rs 92 crore; below
# roughly Rs 50 crore an OI percentage swings on a handful of lots and means
# nothing.
MIN_TURNOVER = 50_00_00_000.0

# Inside this window the series total is still distorted by rollover mechanics,
# so every reading is downgraded rather than reported at face value.
EXPIRY_NOISE_DAYS = 3


# ── Fetch ─────────────────────────────────────────────────────────────────────

def fetch_fo_bhavcopy(max_lookback: int = 7) -> tuple[pd.DataFrame, datetime | None]:
    """Most recent available F&O bhavcopy, STOCK FUTURES only, + trade date.

    Thin filter over `fetch_fo_bhavcopy_raw`. The raw frame also carries the
    option chains (STO/IDO) this module does not need but `pcr.py` does — one
    download, two consumers, rather than two implementations of the same fetch.
    """
    df, day = fetch_fo_bhavcopy_raw(max_lookback)
    if df.empty:
        return df, day
    return df[df["FinInstrmTp"] == STOCK_FUTURE].copy(), day


def fetch_fo_bhavcopy_raw(max_lookback: int = 7) -> tuple[pd.DataFrame, datetime | None]:
    """Most recent available F&O bhavcopy, ALL instrument types, + trade date.

    Returns every row: STF/IDF futures and STO/IDO option chains. An empty frame
    and None mean nothing was reachable in the window — holidays and long
    weekends make that a normal outcome, not an error worth raising.
    """
    session = requests.Session()
    for days_back in range(1, max_lookback + 1):
        day = datetime.today() - timedelta(days=days_back)
        if day.weekday() >= 5:          # NSE does not settle on weekends
            continue
        url = FO_BHAV_URL.format(ymd=day.strftime("%Y%m%d"))
        try:
            r = session.get(url, headers=NSE_HEADERS, timeout=30)
        except Exception:
            continue
        # Trading holidays return an HTML error page, not a zip. The magic-byte
        # check is what distinguishes them without trusting the status code.
        if r.status_code != 200 or r.content[:2] != b"PK":
            continue
        try:
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                name = next(n for n in z.namelist() if n.endswith(".csv"))
                with z.open(name) as fh:
                    df = pd.read_csv(fh, low_memory=False)
        except Exception:
            continue
        if "FinInstrmTp" not in df.columns:
            continue
        return df, day
    return pd.DataFrame(), None


# ── Aggregation ───────────────────────────────────────────────────────────────

def build_oi_table(stf: pd.DataFrame, trade_date: datetime | None = None) -> pd.DataFrame:
    """Collapse per-expiry futures rows into one row per underlying.

    OI is summed across the whole series (see the module docstring on rollover).
    Price comes from the NEAR-month contract, which carries the great majority of
    turnover and is the contract a trader is actually looking at. Mixing a
    series-wide OI against a near-month price is deliberate: OI needs the series
    to be truthful, price needs the liquid contract to be meaningful.
    """
    if stf is None or stf.empty:
        return pd.DataFrame()

    df = stf.copy()
    df["XpryDt"] = pd.to_datetime(df["XpryDt"], errors="coerce")
    df = df.dropna(subset=["XpryDt"])

    agg = df.groupby("TckrSymb").agg(
        oi=("OpnIntrst", "sum"),
        oi_chg=("ChngInOpnIntrst", "sum"),
        turnover=("TtlTrfVal", "sum"),
        volume=("TtlTradgVol", "sum"),
        n_expiries=("XpryDt", "nunique"),
    ).reset_index()

    near = (df.sort_values("XpryDt")
              .groupby("TckrSymb")
              .first()[["XpryDt", "ClsPric", "PrvsClsgPric", "UndrlygPric",
                        "ChngInOpnIntrst"]]
              .rename(columns={"XpryDt": "near_expiry",
                               "ChngInOpnIntrst": "near_oi_chg"})
              .reset_index())
    out = agg.merge(near, on="TckrSymb")

    out["price_pct"] = ((out["ClsPric"] - out["PrvsClsgPric"])
                        / out["PrvsClsgPric"].replace(0, pd.NA) * 100.0)
    # Percentage is against YESTERDAY's OI, which is today's total minus today's
    # change. Dividing by today's total would understate every build-up.
    oi_prev = out["oi"] - out["oi_chg"]
    out["oi_pct"] = out["oi_chg"] / oi_prev.replace(0, pd.NA) * 100.0

    # How much of a front-month OI drain was absorbed by later expiries. 1.0
    # means the series is intact and the front month merely rolled.
    far_chg = out["oi_chg"] - out["near_oi_chg"]
    out["rollover_ratio"] = [
        min(f / -n, 1.0) if (n < 0 and f > 0) else 0.0
        for n, f in zip(out["near_oi_chg"], far_chg)
    ]

    ref = trade_date or datetime.today()
    out["days_to_expiry"] = (out["near_expiry"] - pd.Timestamp(ref.date())).dt.days

    return out.dropna(subset=["price_pct", "oi_pct"])


# ── Classification ────────────────────────────────────────────────────────────

# The full four-quadrant grid. The NSE-page write-up covers only the two up-move
# cases, but a scanner has to put every name somewhere, and the down-move pair is
# the same logic with the sign flipped: OI rising means the move is being built,
# OI falling means it is being vacated.
LONG_BUILDUP   = "LONG BUILD-UP"
SHORT_COVERING = "SHORT COVERING"
SHORT_BUILDUP  = "SHORT BUILD-UP"
LONG_UNWINDING = "LONG UNWINDING"
NO_READ        = "NO CLEAR READ"

# Whether fresh positions are backing the move, or it is running on exits.
SUPPORTED = {LONG_BUILDUP, SHORT_BUILDUP}

BIAS = {
    LONG_BUILDUP:   "BULLISH",
    SHORT_COVERING: "BULLISH",
    SHORT_BUILDUP:  "BEARISH",
    LONG_UNWINDING: "BEARISH",
    NO_READ:        "NEUTRAL",
}


def classify(price_pct: float, oi_pct: float) -> str:
    """Quadrant for one name, or NO_READ when either axis is below its floor.

    Refusing to classify small moves is the point: at 0.2% price and 0.3% OI the
    quadrant is real arithmetic and meaningless information.
    """
    if abs(price_pct) < MIN_PRICE_PCT or abs(oi_pct) < MIN_OI_PCT:
        return NO_READ
    if price_pct > 0:
        return LONG_BUILDUP if oi_pct > 0 else SHORT_COVERING
    return SHORT_BUILDUP if oi_pct > 0 else LONG_UNWINDING


# Display rank: supported moves first, unsupported second, unreliable last.
# Sorting by turnover alone would put the largest names on top regardless of
# whether they said anything, which is the inversion this ordering corrects.
STRENGTH_RANK = {"STRONG": 0, "MODERATE": 1, "UNSUPPORTED": 2,
                 "UNRELIABLE": 3, "NONE": 4}
ACTIONABLE_STRENGTHS = ("STRONG", "MODERATE")


def summarize_symbol(row: pd.Series) -> dict[str, Any]:
    """Reading, strength, and a plain-language explanation for one underlying."""
    sym = str(row["TckrSymb"])
    px, oi = float(row["price_pct"]), float(row["oi_pct"])
    reading = classify(px, oi)
    dte = int(row["days_to_expiry"])
    rollover = float(row["rollover_ratio"])
    turnover = float(row["turnover"])

    # Strength, ordered so the disqualifying cases win. A thin or
    # rollover-contaminated name is not promoted by a large price move.
    if reading == NO_READ:
        strength = "NONE"
    elif turnover < MIN_TURNOVER:
        strength = "UNRELIABLE"
    elif dte <= EXPIRY_NOISE_DAYS:
        strength = "UNRELIABLE"
    elif reading in SUPPORTED:
        strength = ("STRONG"
                    if abs(px) >= STRONG_PRICE_PCT and abs(oi) >= STRONG_OI_PCT
                    else "MODERATE")
    else:
        # Covering and unwinding are directionally informative but describe
        # positions leaving, so they never earn the top tier.
        strength = "UNSUPPORTED"

    detail = {
        LONG_BUILDUP: (
            "Price rose on fresh long positions. New money committed at higher "
            "prices, so participation is broadening rather than thinning — the "
            "move is supported rather than borrowed."),
        SHORT_COVERING: (
            "Price rose while positions were closed out. The rise came from "
            "covering pressure, not new buying. Covering can be sharp while it "
            "lasts, but it exhausts itself: once the shorts are out, the bid "
            "that drove the move is gone."),
        SHORT_BUILDUP: (
            "Price fell on fresh short positions. Traders are actively "
            "positioning for further downside rather than merely exiting, so "
            "the decline has real conviction behind it."),
        LONG_UNWINDING: (
            "Price fell as existing longs exited. This is holders leaving "
            "rather than sellers pressing, which tends to fade once the "
            "supply clears."),
        NO_READ: (
            "Price and OI both moved too little to read. Not a neutral signal — "
            "an absent one."),
    }[reading]

    caveats: list[str] = []
    if dte <= EXPIRY_NOISE_DAYS:
        caveats.append(
            f"{dte} session(s) to expiry — rollover distorts OI in this window, "
            f"so treat the reading as unreliable rather than merely weak.")
    if rollover >= 0.5 and reading in (SHORT_COVERING, LONG_UNWINDING):
        caveats.append(
            f"{rollover:.0%} of the front-month OI decline was picked up by "
            f"later expiries. Most of what looks like positions closing is "
            f"rollover into the next series.")
    if turnover < MIN_TURNOVER:
        caveats.append(
            f"Series turnover of Rs {turnover/1e7:,.1f} crore is thin; the OI "
            f"percentage swings on very few lots.")

    return {
        "symbol": sym,
        "reading": reading,
        "bias": BIAS[reading],
        "supported": reading in SUPPORTED,
        "strength": strength,
        "price_pct": px,
        "oi_pct": oi,
        "oi": float(row["oi"]),
        "oi_chg": float(row["oi_chg"]),
        "turnover": turnover,
        "close": float(row["ClsPric"]),
        "spot": float(row["UndrlygPric"]),
        "days_to_expiry": dte,
        "rollover_ratio": rollover,
        "detail": detail,
        "caveats": caveats,
    }


def sort_key(rec: dict[str, Any]) -> tuple:
    return (STRENGTH_RANK.get(rec.get("strength"), 9),
            -abs(float(rec.get("oi_pct") or 0.0)))


def scan(stf: pd.DataFrame, trade_date: datetime | None = None,
         min_turnover: float = MIN_TURNOVER,
         include_no_read: bool = False) -> list[dict[str, Any]]:
    """Full scan of the stock-futures universe, strongest reading first.

    `include_no_read` keeps the names that failed the materiality floors. Off by
    default, since on a normal session they are roughly a third of the universe
    and carry nothing.
    """
    table = build_oi_table(stf, trade_date)
    if table.empty:
        return []
    out = [summarize_symbol(r) for _, r in table.iterrows()]
    if not include_no_read:
        out = [r for r in out if r["reading"] != NO_READ]
    out = [r for r in out if r["turnover"] >= min_turnover
           or r["strength"] == "UNRELIABLE"]
    out.sort(key=sort_key)
    return out


def breadth(records: list[dict[str, Any]]) -> dict[str, int]:
    """Count per reading. A universe-wide tilt toward build-up versus covering
    is itself a breadth signal, and cheaper to read than any single name."""
    counts = {k: 0 for k in (LONG_BUILDUP, SHORT_COVERING,
                             SHORT_BUILDUP, LONG_UNWINDING, NO_READ)}
    for r in records:
        counts[r["reading"]] = counts.get(r["reading"], 0) + 1
    return counts
