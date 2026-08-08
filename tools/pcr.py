"""pcr.py — Put-Call Ratio from the F&O bhavcopy, per underlying.

    PCR = Total Put OI / Total Call OI

One primitive, two consumers by design: the OI-Momentum page renders it as a
confirm/diverge column beside its futures quadrant, and `sentiment_index` is
meant to take it as a weighted factor. Building it in either of those would have
produced a second implementation of the same quantity — the drift `rating.py`
and `run_scanner_pipeline` exist to prevent.

No new network call. `nse_oi_momentum.fetch_fo_bhavcopy_raw()` already pulls the
whole F&O bhavcopy and keeps only `FinInstrmTp == "STF"`; the option chains it
discards (27,277 STO + 5,026 IDO rows on 2026-08-06) are exactly what PCR needs.
The long-standing "requires an NSE option-chain feed" blocker on the sentiment
index was a measurement nobody had re-run.

── STOCK and INDEX are kept strictly separate, and the data forces it ─────────

Not a stylistic choice. Measured on 2026-08-06:

  STOCK  208 underlyings, median PCR 0.675, p95 1.007
  INDEX    5 underlyings, NIFTY 1.045 / BANKNIFTY 1.019 / MIDCPNIFTY 0.864 /
           FINNIFTY 0.748 / NIFTYNXT50 2.014 — the last off 5,200 contracts
           against NIFTY's 453,484,425

Two consequences, and they run in opposite directions:

  1. **Level.** Index puts are the standard portfolio hedge, so index PCR is
     pushed toward ~1.0 by demand carrying no directional view. Single-stock
     options carry far less of that flow, so their PCR sits structurally lower.
     A stock's 0.68 and an index's 0.68 are not the same statement. The widely
     quoted bands (<0.70 bearish … >1.30 very bullish) are index-shaped: applied
     to the stock cross-section they label 59% of the universe bearish and 5%
     bullish on an ordinary session, the median stock included.

  2. **Calibration METHOD.** With 208 names a day, stock PCR can be ranked
     against its own live cross-section — self-calibrating, no history needed,
     and immune to a market-wide drift in hedging habits. With 5 indices (one of
     them untraded) a cross-sectional percentile is arithmetic without meaning.
     Index PCR needs a TIME-SERIES baseline against its own past, which requires
     stored history this repo does not yet keep.

So the two classes do not merely get different numbers, they get different
machinery — and until an index history exists, `index_reading()` deliberately
returns NO band. Reporting an uncalibrated index level next to a calibrated
stock one, both looking equally confident, is the failure this module is
arranged to avoid.

── What the labels do and do not say ─────────────────────────────────────────

Bands here describe POSITION IN THE DISTRIBUTION ("put-heavy vs peers"), never
direction ("bullish"). PCR has no fixed sign: trend-following reads a high PCR
as bullish, contrarian reads it as crowding, and nothing inside PCR selects the
regime. Naming a band "bullish" would bake one of those readings in and hide the
other. Direction is the consumer's call, made with price context.

See wiki/concepts/Put-Call-Ratio.md and wiki/analyses/PCR-in-OI-Momentum.md.

NOT ADVICE. This measures how option open interest is distributed. It does not
predict price.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

import nse_oi_momentum as oim

# ── Instrument classes. Never mixed, never share a threshold. ────────────────
CLASS_STOCK = "STOCK"
CLASS_INDEX = "INDEX"

#: UDiFF instrument type per class. STO = stock options, IDO = index options.
OPTION_TYPE = {CLASS_STOCK: "STO", CLASS_INDEX: "IDO"}

#: Liquidity floors on TOTAL option OI (puts + calls, all expiries). Below these
#: a PCR swings on a handful of lots and is arithmetic, not positioning.
#: Deliberately one constant per class: the scales differ by orders of magnitude
#: (NIFTY 453M vs a median stock's 10.4M), so a shared floor would either admit
#: junk indices or exclude most of the stock universe.
#:
#: STOCK: p10 of the 2026-08-06 cross-section (p5 1.09M, p10 1.97M, p25 3.94M).
#: INDEX: keeps NIFTY / BANKNIFTY / MIDCPNIFTY; drops FINNIFTY (786,600) and
#: NIFTYNXT50 (5,200 — a PCR of 2.01 off essentially nothing).
#: Both set from ONE session and should be re-measured before they are trusted
#: as stable; that is a known limit, not a hidden one.
MIN_OPTION_OI = {CLASS_STOCK: 2_000_000, CLASS_INDEX: 1_000_000}

#: Cross-sectional percentile cuts for the STOCK class only. Index never reaches
#: these — see the module docstring on why 5 observations cannot be ranked.
STOCK_BANDS = [
    (80, "PUT-HEAVY"),        # top quintile of put-side positioning vs peers
    (60, "PUT-LEANING"),
    (40, "MIDDLE"),
    (20, "CALL-LEANING"),
    (0,  "CALL-HEAVY"),
]

#: |ΔPCR| at or above this is a notable one-day shift. p95 of the stock
#: cross-section's day-change was +0.089 and p5 −0.132 on 2026-08-06, so this
#: sits near the outer decile rather than being a round number.
NOTABLE_PCR_CHG = 0.09


# ── Table ─────────────────────────────────────────────────────────────────────

def build_pcr_table(raw: pd.DataFrame, cls: str) -> pd.DataFrame:
    """One row per underlying for ONE instrument class.

    OI is summed across every listed expiry, for the same reason
    `nse_oi_momentum` sums futures OI across the series: near expiry, OI drains
    out of the front contract and reappears in the next one, and a front-month
    PCR would read that bookkeeping as a change in positioning.

    `pcr_prev` is reconstructed from `ChngInOpnIntrst`, so a one-day PCR slope
    is available from a single file with no stored history. Slope matters more
    than level here — level encodes hedging habits, strike coverage and listing
    age, and most of that differences out.
    """
    if cls not in OPTION_TYPE:
        raise ValueError(f"unknown class {cls!r}; expected one of {list(OPTION_TYPE)}")
    empty = pd.DataFrame(columns=["symbol", "put_oi", "call_oi", "total_oi",
                                  "pcr", "pcr_prev", "pcr_chg", "liquid"])
    if raw is None or raw.empty or "FinInstrmTp" not in raw.columns:
        return empty

    sub = raw[raw["FinInstrmTp"] == OPTION_TYPE[cls]]
    if sub.empty:
        return empty

    rows: list[dict[str, Any]] = []
    for sym, g in sub.groupby("TckrSymb"):
        ce = g[g["OptnTp"] == "CE"]
        pe = g[g["OptnTp"] == "PE"]
        call_oi = float(ce["OpnIntrst"].sum())
        put_oi = float(pe["OpnIntrst"].sum())
        call_prev = call_oi - float(ce["ChngInOpnIntrst"].sum())
        put_prev = put_oi - float(pe["ChngInOpnIntrst"].sum())
        rows.append({
            "symbol": str(sym),
            "put_oi": put_oi,
            "call_oi": call_oi,
            "total_oi": put_oi + call_oi,
            "pcr": (put_oi / call_oi) if call_oi > 0 else np.nan,
            # A negative reconstructed base means the change column disagrees
            # with the level; report NaN rather than a ratio built on it.
            "pcr_prev": (put_prev / call_prev) if call_prev > 0 and put_prev >= 0 else np.nan,
        })

    df = pd.DataFrame(rows)
    df["pcr_chg"] = df["pcr"] - df["pcr_prev"]
    df["liquid"] = df["total_oi"] >= MIN_OPTION_OI[cls]
    return df.sort_values("total_oi", ascending=False).reset_index(drop=True)


# ── Stock calibration: self-calibrating against the live cross-section ───────

def calibrate_stock(table: pd.DataFrame) -> dict[str, Any] | None:
    """Percentile cuts from the day's own LIQUID stock cross-section.

    Self-calibrating on purpose. A fixed band would have to be re-validated every
    time market-wide hedging behaviour drifted; a percentile rank is defined
    against today's market and cannot go stale. It also sidesteps the borrowed
    index bands that mislabel most of the stock universe.

    Returns None when too few liquid names survive to rank meaningfully.
    """
    if table is None or table.empty:
        return None
    live = table[table["liquid"] & table["pcr"].notna()]
    if len(live) < 30:          # below this a percentile is noise dressed as rank
        return None
    cuts = {p: float(live["pcr"].quantile(p / 100.0)) for p, _ in STOCK_BANDS if p}
    return {
        "n": int(len(live)),
        "median": float(live["pcr"].median()),
        "cuts": cuts,
        "values": live["pcr"].to_numpy(),
    }


def stock_percentile(pcr: float, calib: dict[str, Any]) -> float | None:
    """Where `pcr` sits in the day's liquid stock cross-section, 0-100."""
    if calib is None or pcr is None or not np.isfinite(pcr):
        return None
    vals = calib["values"]
    return float((vals < pcr).sum() / len(vals) * 100.0)


def classify_stock(pcr: float, calib: dict[str, Any]) -> str:
    """Positional band for one stock. Says where it sits, NOT which way to trade.

    Returns UNCALIBRATED when the cross-section could not be built — an honest
    absence rather than a middle reading, the same discipline `classify()` in
    nse_oi_momentum applies with NO_READ.
    """
    pct = stock_percentile(pcr, calib)
    if pct is None:
        return "UNCALIBRATED"
    for cut, label in STOCK_BANDS:
        if pct >= cut:
            return label
    return "CALL-HEAVY"


# ── Index: level and slope only, deliberately unbanded ──────────────────────

def index_reading(table: pd.DataFrame, symbol: str = "NIFTY") -> dict[str, Any] | None:
    """Level and one-day slope for one index. **No band, by design.**

    Banding this would need a baseline of the index's OWN history — five
    same-day observations cannot be ranked against each other, and borrowing the
    stock cross-section would compare instruments whose PCR differs structurally
    (see the module docstring). Until a history is stored, `band` is None and
    `band_reason` says why. An uncalibrated number is reportable; an
    uncalibrated number wearing a calibrated label is not.
    """
    if table is None or table.empty:
        return None
    row = table[table["symbol"] == symbol]
    if row.empty:
        return None
    r = row.iloc[0]
    if not bool(r["liquid"]):
        return {
            "symbol": symbol, "pcr": float(r["pcr"]), "pcr_chg": _f(r["pcr_chg"]),
            "total_oi": float(r["total_oi"]), "liquid": False,
            "band": None,
            "band_reason": (f"Total option OI of {r['total_oi']:,.0f} is below the "
                            f"index floor of {MIN_OPTION_OI[CLASS_INDEX]:,} — the "
                            f"ratio swings on too few lots to read."),
        }
    return {
        "symbol": symbol, "pcr": float(r["pcr"]), "pcr_chg": _f(r["pcr_chg"]),
        "total_oi": float(r["total_oi"]), "liquid": True,
        "band": None,
        "band_reason": ("No calibrated band yet: an index PCR can only be ranked "
                        "against its own history, and none is stored. Level and "
                        "one-day change are reportable; a sentiment label is not."),
    }


def _f(v) -> float | None:
    try:
        f = float(v)
        return f if np.isfinite(f) else None
    except (TypeError, ValueError):
        return None


# ── Confirm / diverge against a price move ──────────────────────────────────

def price_pcr_tag(price_pct: float, pcr_chg: float | None,
                  min_chg: float = NOTABLE_PCR_CHG) -> dict[str, str] | None:
    """The price × PCR grid, as a tag to sit BESIDE a verdict — never inside one.

    Deliberately built on the day-CHANGE, not the level: a stock whose PCR is
    structurally 0.5 is not "bearish", but a 0.5 that jumped 0.12 today has
    said something. Returns None when the shift is too small to read, which is
    the common case and should stay silent rather than print a weak opinion.
    """
    if pcr_chg is None or price_pct is None:
        return None
    if abs(pcr_chg) < min_chg or abs(price_pct) < oim.MIN_PRICE_PCT:
        return None
    up_px, up_pcr = price_pct > 0, pcr_chg > 0
    if up_px and up_pcr:
        return {"tag": "CONFIRMS", "note": "Price rose and put-side OI grew with it."}
    if not up_px and not up_pcr:
        return {"tag": "CONFIRMS", "note": "Price fell and call-side OI grew with it."}
    if up_px and not up_pcr:
        return {"tag": "DIVERGES",
                "note": "Price rose while option positioning moved to the call side."}
    return {"tag": "DIVERGES",
            "note": "Price fell while option positioning moved to the put side."}


# ── One-call convenience ────────────────────────────────────────────────────

def load(max_lookback: int = 7) -> dict[str, Any]:
    """Fetch once, build BOTH class tables, calibrate the stock cross-section.

    One download feeds both classes; they are still returned as separate tables
    with separate calibration, and nothing downstream can accidentally rank a
    stock against an index.
    """
    raw, day = oim.fetch_fo_bhavcopy_raw(max_lookback)
    if raw is None or raw.empty:
        return {"ok": False, "reason": "no F&O bhavcopy reachable", "date": None}
    stock = build_pcr_table(raw, CLASS_STOCK)
    index = build_pcr_table(raw, CLASS_INDEX)
    return {
        "ok": True,
        "date": day.date().isoformat() if isinstance(day, datetime) else None,
        "stock": stock,
        "index": index,
        "stock_calib": calibrate_stock(stock),
    }
