#!/usr/bin/env python3
"""pattern_reports.py — the Strategy Hub chart-pattern roster, priced live (PR-1).

Roadmap rung PR-1 from `analyses/Pattern-Reporting-Enhancement-Roadmap`.

── What was wrong ────────────────────────────────────────────────────────────
The roster lived in `dashboard_app.py` as a literal of 20 tuples carrying
**stock, pattern, bias, publish date, publish price, LTP and Move % — all
frozen**. The caption said the detections were third-party and historical, which
was true; it did not say the *prices* were hardcoded, so "LTP" read as live and
the footer counted "N above publish price / M below" over numbers nothing was
measuring.

That is not merely stale. Measured 2026-09-17, the frozen rows put at least one
name on the WRONG SIDE of their own scoreboard:

    SPLPETRO    pub 788.00   frozen LTP 685.25 (-13.0%)   live 807.00 (+2.4%)
    MAPMYINDIA  pub 1231.95  frozen LTP 1013.30 (-17.7%)  live 889.80 (-27.8%)
    ZEEL        pub  118.35  frozen LTP   91.56 (-22.6%)  live  78.31 (-33.8%)

── What changed, and what deliberately did NOT ───────────────────────────────
**The detections stay frozen. Only the prices move.** The pattern, bias and
publish date are a historical record of what a third party called and when;
rewriting those would be inventing detections this desk never made. The publish
price is part of that record too — it is the baseline the call was made at.

**LTP and Move % are now computed**, from the same batched fetch the rest of the
desk uses, and Move % is *derived* rather than stored so the two can never
disagree again.

── The symbol is pinned, not matched ─────────────────────────────────────────
Each row carries an explicit NSE symbol. Resolving the display names at render
time by fuzzy match was considered and rejected: on this very roster the closest
matches include **INFY for "CE Info Systems"** (the correct answer is
MAPMYINDIA) and **M&MFIN for "Mahindra & Mahindra"**. A mis-resolved symbol shows
another company's price under this company's name, which is worse than the frozen
number it replaces.

── Absent renders absent ─────────────────────────────────────────────────────
Three rows never had a publish price. They nonetheless carried a hardcoded
Move % (-13.0, -15.3, -9.0) computed from nothing visible. **A move needs a
baseline**, so those are now `None`: the cell is blank rather than asserting a
number no one can reproduce. Equally, a symbol the fetch cannot price gets a
blank LTP, never a carried-forward one.

CLI:
    py -3 -X utf8 tools/pattern_reports.py
"""
from __future__ import annotations

import sys
from typing import Any, Iterable, Optional

#: How far back the price fetch reaches. `trending_stocks._batch_history` drops
#: any symbol with fewer than 30 bars, so a short window returns nothing at all —
#: 6 months is comfortably clear of that floor while staying one request.
PRICE_PERIOD = "6mo"

#: The roster. (symbol, display, pattern, bias, published, pub_price)
#:
#: Detections are a FIXED SAMPLE captured from StockEdge in August 2026 — they
#: are a record, not a feed, and nothing here re-detects them. `pub_price` is
#: part of that record: it is the level the call was published at.
#:
#: `None` pub_price means the source published no price point. Those rows are
#: kept because the DETECTION is still a record; they simply cannot carry a move.
PATTERNS: tuple[tuple, ...] = (
    ("MAPMYINDIA", "CE Info Systems",      "Double Top",         "Bearish", "04 Aug", 1231.95),
    ("ZEEL",       "Zee Entertainment",    "Double Top",         "Bearish", "03 Aug",  118.35),
    ("SPLPETRO",   "Supreme Petrochem",    "Double Top",         "Bearish", "29 Jul",  788.00),
    ("GALLANTT",   "Gallantt Ispat",       "Bearish Flag",       "Bearish", "21 Jul",  618.50),
    ("HEROMOTOCO", "Hero MotoCorp",        "Falling Channel",    "Bearish", "20 Jul", 4942.38),
    ("M&M",        "Mahindra & Mahindra",  "Falling Channel",    "Bearish", "21 Jul", 3172.73),
    ("PNBHOUSING", "PNB Housing Finance",  "Rising Wedge",       "Bearish", "23 Jul", 1073.38),
    ("PINELABS",   "Pine Labs",            "Double Top",         "Bearish", "16 Jul",  164.40),
    ("MUTHOOTFIN", "Muthoot Finance",      "Falling Wedge",      "Bearish", "21 Jul", 3068.97),
    ("JUBLFOOD",   "Jubilant FoodWorks",   "Double Bottom",      "Bullish", "27 Jul",  408.55),
    ("SAPPHIRE",   "Sapphire Foods",       "Sym. Triangle",      "Bullish", "27 Jul",  182.94),
    ("LTM",        "LTM Ltd.",             "Sym. Triangle",      "Bullish", "28 Jul", 4192.58),
    ("PPLPHARMA",  "Piramal Pharma",       "Sym. Triangle",      "Bullish", "17 Jul",  177.18),
    ("RRKABEL",    "RR Kabel",             "Sym. Triangle",      "Bullish", "22 Jul", 2386.29),
    ("CLEAN",      "Clean Science & Tech", "Sym. Triangle",      "Bullish", "20 Jul",  756.03),
    ("HYUNDAI",    "Hyundai Motor India",  "Ascending Triangle", "Bullish", "31 Jul", 2064.80),
    ("CRISIL",     "CRISIL",               "Ascending Triangle", "Bullish", "21 Jul", 4250.00),
    ("BLUESTARCO", "Blue Star",            "Sym. Triangle",      "Neutral", "03 Aug",     None),
    ("ZEEL",       "Zee Entertainment",    "Sym. Triangle",      "Neutral", "27 Jul",     None),
    ("SPLPETRO",   "Supreme Petrochem",    "Falling Channel",    "Bearish", "27 Jul",     None),
)

COLUMNS = ("Symbol", "Stock", "Pattern", "Bias", "Published", "Pub Price ₹",
           "LTP ₹", "Move %")


def symbols() -> list[str]:
    """Distinct symbols on the roster, in roster order.

    Distinct because two names appear twice with different patterns; fetching
    either one twice would be a wasted request against the same ticker.
    """
    seen: dict[str, None] = {}
    for row in PATTERNS:
        seen.setdefault(row[0], None)
    return list(seen)


def fetch_prices(syms: Optional[Iterable[str]] = None,
                 period: str = PRICE_PERIOD) -> dict[str, float]:
    """{symbol: last close} from one batched request.

    Returns only what actually priced. A symbol missing from the result is
    missing on purpose — the caller renders it blank rather than substituting
    anything.
    """
    want = list(syms) if syms is not None else symbols()
    if not want:
        return {}
    try:
        import trending_stocks as ts
        hist = ts._batch_history(want, period=period)
    except Exception:
        return {}
    out: dict[str, float] = {}
    for sym, df in (hist or {}).items():
        try:
            # `_batch_history` returns CAPITALISED OHLC columns. Lower-case
            # indexing here would silently price nothing, which is the
            # integration bug B-60's live run caught on this same helper.
            close = df["Close"].dropna()
            if len(close):
                out[sym] = float(close.iloc[-1])
        except (KeyError, IndexError, TypeError, ValueError):
            continue
    return out


#: Cache lifetime for the live prices. 15 minutes because this is a review
#: table, not a trading surface: a quarter hour of staleness is invisible here,
#: and the roster is fixed so the fetch is the same tickers every time.
PRICE_TTL = 900

#: Built once, lazily, so importing this module never requires Streamlit — the
#: CLI and the tests both use it headless.
_cached_fn = None


def cached_prices() -> dict[str, float]:
    """`fetch_prices`, memoised by Streamlit when it is available.

    The caching lives here rather than in `dashboard_app` so the monolith gains
    no function for it (the B-87 ratchet), and so a headless caller gets the
    same answer through the same entry point.
    """
    global _cached_fn
    if _cached_fn is None:
        try:
            import streamlit as st
            _cached_fn = st.cache_data(ttl=PRICE_TTL, show_spinner=False)(fetch_prices)
        except Exception:                                    # pragma: no cover
            _cached_fn = fetch_prices
    return _cached_fn()


def move_pct(pub: Optional[float], ltp: Optional[float]) -> Optional[float]:
    """Per-cent move from the publish price to the last trade.

    None whenever either end is unknown or the baseline is not positive. A move
    without a baseline is not a small number, it is not a number.
    """
    if pub is None or ltp is None or not (pub > 0):
        return None
    return round((ltp / pub - 1.0) * 100.0, 1)


def build_rows(prices: Optional[dict[str, float]] = None) -> list[dict[str, Any]]:
    """The roster with LTP and Move % computed from `prices`.

    Move % is DERIVED here rather than stored on the roster, so the printed move
    and the printed prices cannot drift apart — which is exactly how the frozen
    version came to put a name on the wrong side of its own scoreboard.
    """
    px = prices if prices is not None else {}
    rows = []
    for sym, name, pattern, bias, published, pub in PATTERNS:
        ltp = px.get(sym)
        rows.append({
            "Symbol": sym, "Stock": name, "Pattern": pattern, "Bias": bias,
            "Published": published, "Pub Price ₹": pub,
            "LTP ₹": ltp, "Move %": move_pct(pub, ltp),
        })
    return rows


def scoreboard(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    """Counts over rows that actually have a move — never over the whole roster.

    `scored` is reported alongside `total` so the caption can say what the count
    is out of. Saying "12 above / 5 below" out of 20 without naming the three
    that could not be scored would be the same overclaim in a smaller form.
    """
    rows = list(rows)
    # `is not None` is NOT enough. Going through a DataFrame turns a None into a
    # float NaN, which is not None -- so a naive check counted the price-less
    # rows as SCORED while they fell out of both above and below, and the live
    # footer read "12 above, 5 below, scored on 20 of 20". Caught on the running
    # page, not by a unit test that passed real Nones.
    moves = [m for m in (r.get("Move %") for r in rows)
             if isinstance(m, (int, float)) and m == m]
    return {
        "total": len(rows), "scored": len(moves),
        "above": sum(1 for m in moves if m > 0),
        "below": sum(1 for m in moves if m < 0),
        "flat": sum(1 for m in moves if m == 0),
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # pragma: no cover
        pass
    px = fetch_prices()
    rows = build_rows(px)
    print(f"{len(px)} of {len(symbols())} symbols priced\n")
    print(f"{'Symbol':<12}{'Stock':<24}{'Pattern':<20}{'Pub':>9}{'LTP':>10}{'Move%':>8}")
    for r in rows:
        pub = "-" if r["Pub Price ₹"] is None else f"{r['Pub Price ₹']:.2f}"
        ltp = "-" if r["LTP ₹"] is None else f"{r['LTP ₹']:.2f}"
        mv = "-" if r["Move %"] is None else f"{r['Move %']:+.1f}"
        print(f"{r['Symbol']:<12}{r['Stock']:<24}{r['Pattern']:<20}{pub:>9}{ltp:>10}{mv:>8}")
    s = scoreboard(rows)
    print(f"\n{s['scored']} of {s['total']} scored · {s['above']} above · "
          f"{s['below']} below · {s['flat']} flat")
    return 0


if __name__ == "__main__":
    sys.exit(main())
