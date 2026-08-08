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

# UDiFF instrument types. STO/IDO are the option chains that swamp the web page
# (and feed pcr.py); the two futures types each get their own scan and their own
# floors — see INDEX_FLOORS.
STOCK_FUTURE = "STF"
INDEX_FUTURE = "IDF"

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

# ── Relative volume ───────────────────────────────────────────────────────────
# OI says whether a move was built or vacated. Volume says how many people
# turned up to do it, and "high volume" is a RELATIVE claim: the question is
# whether a stock traded more than IT usually does, not more than its neighbours.
# That needs a per-symbol baseline, and the bhavcopy is a single session — hence
# the extra downloads below rather than a cross-sectional shortcut.
#
# A trading week of prior sessions. Long enough to absorb one quiet day, short
# enough that the baseline still describes the current regime.
VOLUME_BASELINE_SESSIONS = 5

# A symbol seen fewer times than this has a "median" of one or two observations,
# which is a number without being an average. Those get no rvol at all.
MIN_BASELINE_SESSIONS = 3

# A STRONG grade claims the move was built with conviction. Requiring the day to
# at least match the symbol's own median participation is the cheapest possible
# version of that claim. Measured 2026-08-06: STRONG names ran a median 3.98x
# and NOT ONE sat below 1.0x, so this fires rarely by construction — it exists to
# make the "large move, large OI, nobody there" case DETECTABLE, not to re-rank
# the universe. Volume can only ever downgrade here; it never promotes.
MIN_STRONG_RVOL = 1.0

# ── Floor sets, one per instrument class ─────────────────────────────────────
# An index is a diversified average, so it does not move like the names inside
# it, and reusing the stock floors would be wrong in BOTH directions. Measured
# over 12 sessions (60 index symbol-days, 2,506 stock symbol-days):
#
#              median |price %|      median |OI %|
#   STOCK           0.90                1.43
#   INDEX           0.52                3.08
#
# Indices move about 58% as much on price, and their OI swings roughly twice as
# hard — index futures carry far fewer contracts, so a single large roll moves
# the percentage much further. Both floors therefore have to change, and in
# opposite directions.
#
# The rule is the module's existing one: a floor sits near the class median, so
# "a reading" means the instrument moved more than half its own class did.
#
# NOTE on the stock set: the comment above MIN_PRICE_PCT says its floors "sit
# just above those medians". That is true of MIN_OI_PCT (1.5 vs a 1.43 median)
# but NOT of MIN_PRICE_PCT (0.5 against a 0.90 median) — the price floor is
# considerably more permissive than the docstring claims. Left as-is because
# changing it would silently re-grade the whole stock universe; recorded here so
# the next reader is not misled by the stated rationale.
STOCK_FLOORS: dict[str, Any] = {
    "label":            "stock future",
    "min_price_pct":    MIN_PRICE_PCT,
    "min_oi_pct":       MIN_OI_PCT,
    "strong_price_pct": STRONG_PRICE_PCT,
    "strong_oi_pct":    STRONG_OI_PCT,
    "min_turnover":     MIN_TURNOVER,
    "min_oi":           0.0,          # turnover is the stock liquidity gate
}

#: Index floors, calibrated on the LIQUID index distribution only (36 symbol-days
#: over 12 sessions): |price| p50 0.43, p75 0.80, p90 0.93; |OI| p50 2.02,
#: p75 3.61, p90 4.70.
#:
#: Calibrating on liquid names only is the correction that matters here. The
#: first cut pooled all five indices and got |OI| p75 4.86 / p90 7.83 — badly
#: inflated, because FINNIFTY and NIFTYNXT50 swing 20%+ on twenty-odd thousand
#: contracts. A STRONG cut taken from that pool (6.0) sat ABOVE the liquid p90
#: and fired on 0 of 36 liquid symbol-days: a grade that cannot be earned. Since
#: an illiquid index is forced to UNRELIABLE by `min_oi` regardless, the only
#: population a STRONG threshold can ever apply to is the liquid one, so that is
#: the population it must be measured on.
#:
#: The result matches the stock scan's selectivity closely, which is the
#: cross-check: STRONG lands on 3% of liquid index symbol-days against 3.4% of
#: stock symbol-days, and a reading on 19% against 27%.
#:
#: `min_oi` is the liquidity gate here rather than turnover: NIFTY carried a
#: median 14.3M contracts, BANKNIFTY 2.35M and MIDCPNIFTY 1.98M, against
#: FINNIFTY's 32,010 and NIFTYNXT50's 18,962 — two orders of magnitude apart.
#: 1,000,000 is the same index floor pcr.py uses, kept identical on purpose.
INDEX_FLOORS: dict[str, Any] = {
    "label":            "index future",
    "min_price_pct":    0.5,          # liquid p50 0.43
    "min_oi_pct":       2.5,          # liquid p50 2.02
    "strong_price_pct": 0.9,          # liquid p90 0.93
    "strong_oi_pct":    4.5,          # liquid p90 4.70
    "min_turnover":     0.0,          # OI is the index liquidity gate
    "min_oi":           1_000_000.0,
}


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
        df = _download_bhavcopy(session, day)
        if df is not None:
            return df, day
    return pd.DataFrame(), None


def _download_bhavcopy(session: requests.Session, day: datetime) -> pd.DataFrame | None:
    """One session's F&O bhavcopy, or None if that day has no settled file.

    None covers every non-answer identically — network failure, trading holiday,
    a malformed zip — because the caller's response to all of them is the same:
    try another day. Trading holidays return an HTML error page rather than a
    404, so the magic-byte check is what distinguishes them without trusting the
    status code.
    """
    url = FO_BHAV_URL.format(ymd=day.strftime("%Y%m%d"))
    try:
        r = session.get(url, headers=NSE_HEADERS, timeout=30)
    except Exception:
        return None
    if r.status_code != 200 or r.content[:2] != b"PK":
        return None
    try:
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            name = next(n for n in z.namelist() if n.endswith(".csv"))
            with z.open(name) as fh:
                df = pd.read_csv(fh, low_memory=False)
    except Exception:
        return None
    return df if "FinInstrmTp" in df.columns else None


def fetch_volume_baseline(sessions: int = VOLUME_BASELINE_SESSIONS,
                          max_lookback: int = 20,
                          before: datetime | None = None,
                          instrument: str = STOCK_FUTURE) -> dict[str, Any]:
    """Per-symbol median futures volume over the N sessions BEFORE `before`.

    `instrument` selects the class (STF or IDF). One call per class rather than
    a combined map: symbol namespaces do not overlap, but keeping them apart
    means an index can never accidentally be handed a stock's baseline.

    Costs `sessions` extra downloads (~1.2 MB each), which is why callers are
    expected to cache it — the underlying files are settled and never change.

    `before` must be the scan's own trade date, not today: the baseline has to
    EXCLUDE the session being measured, or every symbol is partly compared
    against itself and a genuine volume spike is diluted by its own presence in
    the denominator.

    Returns {"median": {symbol: volume}, "sessions": n, "dates": [...]}, with
    symbols seen fewer than MIN_BASELINE_SESSIONS times omitted entirely. An
    empty median map means no baseline was reachable, and every caller must then
    report rvol as ABSENT rather than assume 1.0 — an unmeasured participation
    level is not an average one.
    """
    session = requests.Session()
    start = before or datetime.today()
    seen: list[pd.Series] = []
    dates: list[str] = []
    days_back = 1
    while len(seen) < sessions and days_back <= max_lookback:
        day = start - timedelta(days=days_back)
        days_back += 1
        if day.weekday() >= 5:
            continue
        df = _download_bhavcopy(session, day)
        if df is None:
            continue
        sub = df[df["FinInstrmTp"] == instrument]
        if sub.empty or "TtlTradgVol" not in sub.columns:
            continue
        seen.append(sub.groupby("TckrSymb")["TtlTradgVol"].sum())
        dates.append(day.strftime("%Y-%m-%d"))

    if not seen:
        return {"median": {}, "sessions": 0, "dates": []}

    wide = pd.concat(seen, axis=1)
    counts = wide.notna().sum(axis=1)
    med = wide.median(axis=1, skipna=True)
    keep = (counts >= min(MIN_BASELINE_SESSIONS, len(seen))) & (med > 0)
    return {
        "median": {str(s): float(v) for s, v in med[keep].items()},
        "sessions": len(seen),
        "dates": dates,
    }


# ── Aggregation ───────────────────────────────────────────────────────────────

def build_oi_table(stf: pd.DataFrame, trade_date: datetime | None = None,
                   volume_baseline: dict[str, Any] | None = None) -> pd.DataFrame:
    """Collapse per-expiry futures rows into one row per underlying.

    OI is summed across the whole series (see the module docstring on rollover).
    Price comes from the NEAR-month contract, which carries the great majority of
    turnover and is the contract a trader is actually looking at. Mixing a
    series-wide OI against a near-month price is deliberate: OI needs the series
    to be truthful, price needs the liquid contract to be meaningful.

    `volume_baseline` (from `fetch_volume_baseline`) is optional. Supplied, it
    adds `avg_volume` and `rvol`; omitted, both are NaN and every downstream
    consumer treats participation as unmeasured rather than as normal.
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

    # Relative volume against the symbol's OWN prior median. NaN where no
    # baseline exists for that name — never filled with 1.0, which would assert
    # normal participation on no evidence.
    base = (volume_baseline or {}).get("median") or {}
    out["avg_volume"] = out["TckrSymb"].map(base).astype("float64")
    out["rvol"] = out["volume"] / out["avg_volume"].replace(0, pd.NA)

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


def classify(price_pct: float, oi_pct: float,
             floors: dict[str, Any] = STOCK_FLOORS) -> str:
    """Quadrant for one name, or NO_READ when either axis is below its floor.

    Refusing to classify small moves is the point: at 0.2% price and 0.3% OI the
    quadrant is real arithmetic and meaningless information. `floors` selects the
    instrument class — an index clears a different bar from a single stock.
    """
    if (abs(price_pct) < floors["min_price_pct"]
            or abs(oi_pct) < floors["min_oi_pct"]):
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


def summarize_symbol(row: pd.Series,
                     floors: dict[str, Any] = STOCK_FLOORS) -> dict[str, Any]:
    """Reading, strength, and a plain-language explanation for one underlying."""
    sym = str(row["TckrSymb"])
    px, oi = float(row["price_pct"]), float(row["oi_pct"])
    reading = classify(px, oi, floors)
    dte = int(row["days_to_expiry"])
    rollover = float(row["rollover_ratio"])
    turnover = float(row["turnover"])
    rvol = float(row["rvol"]) if "rvol" in row and pd.notna(row.get("rvol")) else None

    # Set when a would-be STRONG grade is held back for want of participation.
    thin_participation = False

    # Strength, ordered so the disqualifying cases win. A thin or
    # rollover-contaminated name is not promoted by a large price move.
    if reading == NO_READ:
        strength = "NONE"
    elif turnover < floors["min_turnover"]:
        strength = "UNRELIABLE"
    elif float(row["oi"]) < floors["min_oi"]:
        strength = "UNRELIABLE"
    elif dte <= EXPIRY_NOISE_DAYS:
        strength = "UNRELIABLE"
    elif reading in SUPPORTED:
        strength = ("STRONG"
                    if abs(px) >= floors["strong_price_pct"]
                    and abs(oi) >= floors["strong_oi_pct"]
                    else "MODERATE")
        # Volume is a veto on STRONG, never a promotion to it. A big move on a
        # big OI build that nobody showed up for is the textbook weak
        # confirmation, and price and OI magnitude alone cannot see it.
        if (strength == "STRONG" and rvol is not None
                and rvol < MIN_STRONG_RVOL):
            strength = "MODERATE"
            thin_participation = True
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
    if turnover < floors["min_turnover"]:
        caveats.append(
            f"Series turnover of Rs {turnover/1e7:,.1f} crore is thin; the OI "
            f"percentage swings on very few lots.")
    if float(row["oi"]) < floors["min_oi"]:
        caveats.append(
            f"Series open interest of {float(row['oi']):,.0f} contracts is below "
            f"the {floors['label']} floor of {floors['min_oi']:,.0f}. The OI "
            f"percentage here moves on a handful of lots and is not comparable "
            f"to the liquid contracts in this table.")
    if thin_participation:
        caveats.append(
            f"Held at MODERATE despite the size of the move: volume was "
            f"{rvol:.2f}x the symbol's own {VOLUME_BASELINE_SESSIONS}-session "
            f"median, so the positions were built on below-normal "
            f"participation. Fresh OI on thin volume is a weaker confirmation "
            f"than the same OI on a crowd.")
    elif rvol is not None and rvol >= 2.0 and reading in SUPPORTED:
        caveats.append(
            f"Volume ran {rvol:.1f}x the symbol's own "
            f"{VOLUME_BASELINE_SESSIONS}-session median — the build had "
            f"unusually broad participation behind it.")

    return {
        "symbol": sym,
        "reading": reading,
        "bias": BIAS[reading],
        "supported": reading in SUPPORTED,
        "strength": strength,
        "price_pct": px,
        "oi_pct": oi,
        "rvol": rvol,
        "thin_participation": thin_participation,
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


def scan_index(idf: pd.DataFrame, trade_date: datetime | None = None,
               include_no_read: bool = False,
               volume_baseline: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """The same four quadrants over INDEX futures, on index floors.

    A separate entry point rather than extra rows on the stock scan, and
    deliberately so. The two classes are not comparable: an index OI percentage
    of 3% is an ordinary day where a stock's would be a strong build, and there
    are five index underlyings against ~210 stocks. Appending them to one table
    would invite exactly the cross-class comparison the floors exist to prevent —
    the same separation `pcr.py` enforces for the option side.
    """
    return scan(idf, trade_date, include_no_read=include_no_read,
                volume_baseline=volume_baseline, floors=INDEX_FLOORS)


def scan(stf: pd.DataFrame, trade_date: datetime | None = None,
         min_turnover: float | None = None,
         include_no_read: bool = False,
         volume_baseline: dict[str, Any] | None = None,
         floors: dict[str, Any] = STOCK_FLOORS) -> list[dict[str, Any]]:
    """Full scan of the stock-futures universe, strongest reading first.

    `include_no_read` keeps the names that failed the materiality floors. Off by
    default, since on a normal session they are roughly a third of the universe
    and carry nothing.

    `volume_baseline` is optional and costs extra downloads to build, so the
    scan stays fully usable without it — omitted, `rvol` is None everywhere and
    no name is downgraded for participation nobody measured.
    """
    if min_turnover is None:
        min_turnover = floors["min_turnover"]
    table = build_oi_table(stf, trade_date, volume_baseline=volume_baseline)
    if table.empty:
        return []
    out = [summarize_symbol(r, floors) for _, r in table.iterrows()]
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
