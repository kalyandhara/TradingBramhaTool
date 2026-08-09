"""market_brief.py — the market half of the morning brief card.

Global quote strip + constituent-based sector breadth, composed with
``panchang.py`` (the astro half) and the existing sentiment reading into one
model a page or a renderer can lay out. Pure module: no Streamlit, no globals,
mirroring the shape of `pcr.py` and `panchang.py`.

Public API:
    global_snapshot(...)  -> quotes for the card's index/commodity/FX rows
    sector_breadth(...)   -> how many sectors are red, from CONSTITUENTS
    build_brief(...)      -> everything, plus the astro layer, in one dict

Why breadth is computed from constituents rather than sector indices
--------------------------------------------------------------------
The obvious implementation — read the NSE sector indices and count the red ones
— **cannot be trusted here**. `sentiment_index._sector_perf` documents that
Yahoo stopped updating **8 of the 11** NSE sector index feeds on 2026-07-17;
only ^CNXIT, ^CNXPHARMA and ^NSEBANK still move. Worse, the stale feeds do not
error, they return an old bar, so a naive read produces a confident breadth
number from three survivors and calls it the market. That already happened once:
a 2026-08-03 reading scored 3-of-11 indices, all green, and fed a full 25/25
into the composite.

So breadth comes from the **Nifty 500 constituents themselves**, grouped by
NSE's own macro-industry tag (20 of them, from the exchange's published CSV via
`nse_universe.fetch_constituents`, cached 7 days). A sector is red when the
**median** constituent is down — median, not mean, so one collapsing name cannot
paint a sector red on its own.

Staleness is reported, never silently absorbed
----------------------------------------------
Every quote and every constituent bar carries its age, and anything older than
`max_bar_age_days` is counted as stale and **excluded from the breadth maths**
rather than averaged in. Coverage travels with the number. The lesson from the
frozen sector feeds is that the dangerous failure is not the fetch that errors,
it is the one that quietly returns yesterday.

Nothing here is a signal or a recommendation. It is a snapshot.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Callable

import pandas as pd

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

#: The card's quote rows. (display label, yfinance ticker, group).
#: A trailing ``*`` on a label means the row is an **ETF proxy**, not the index
#: itself — said in the label rather than hidden, since a proxy tracks with
#: tracking error and can diverge intraday.
#:
#: Two rows are proxies for the same reason: Yahoo has no free feed for them.
#: MSCI AP ex-Japan never had one. **CSI 300 (`000300.SS`) had one and it froze
#: on 2026-07-17** — verified 2026-08-09, last bar 23 days old while every live
#: China ticker printed 08-07. That is the *same date* the 8 NSE sector index
#: feeds froze (`sentiment_index._sector_perf`), so this looks like one batched
#: Yahoo index-feed drop rather than isolated flakiness. Assume any `^`/index
#: ticker here can go quietly stale; that is what `max_bar_age_days` is for.
QUOTE_ROWS: tuple[tuple[str, str, str], ...] = (
    ("Nifty 50",            "^NSEI",      "india"),
    ("Sensex",              "^BSESN",     "india"),
    ("Nikkei 225",          "^N225",      "asia"),
    ("KOSPI",               "^KS11",      "asia"),
    ("China CSI 300*",      "510300.SS",  "asia"),
    ("MSCI AP ex-Japan*",   "AAXJ",       "asia"),
    ("Dow Jones",           "^DJI",       "us"),
    ("S&P 500",             "^GSPC",      "us"),
    ("Nasdaq",              "^IXIC",      "us"),
    ("Brent Crude",         "BZ=F",       "commodity"),
    ("Gold",                "GC=F",       "commodity"),
    ("US Dollar Index",     "DX-Y.NYB",   "fx"),
    ("USD/INR",             "USDINR=X",   "fx"),
)

GROUP_LABELS = {"india": "India", "asia": "Asian Markets", "us": "Wall Street",
                "commodity": "Commodities", "fx": "Currencies"}


def _default_download(tickers: list[str], period: str) -> pd.DataFrame:
    import yfinance as yf                      # imported lazily: optional dep
    return yf.download(tickers, period=period, interval="1d", group_by="ticker",
                       auto_adjust=False, progress=False, threads=True)


def _last_two_closes(frame: pd.DataFrame) -> tuple[float, float, dt.date] | None:
    """(last_close, prior_close, last_bar_date) from a single ticker's frame."""
    if frame is None or frame.empty:
        return None
    closes = frame["Close"].dropna()
    if len(closes) < 2:
        return None
    idx = closes.index[-1]
    last_date = idx.date() if hasattr(idx, "date") else None
    return float(closes.iloc[-1]), float(closes.iloc[-2]), last_date


def global_snapshot(rows: tuple[tuple[str, str, str], ...] = QUOTE_ROWS,
                    *, download: Callable[..., pd.DataFrame] | None = None,
                    max_bar_age_days: int = 5,
                    today: dt.date | None = None) -> dict[str, Any]:
    """Last close, prior close and % change for each quote row.

    One batched download for every ticker. Each quote carries `stale` and
    `bar_age_days`; nothing is dropped silently, because a missing Nikkei and a
    three-week-old Nikkei are different problems with the same symptom.
    """
    download = download or _default_download
    today = today or dt.datetime.now(IST).date()
    tickers = [t for _, t, _ in rows]
    try:
        data = download(tickers, "1mo")
    except Exception as exc:                     # network/vendor failure
        return {"quotes": [], "error": f"{type(exc).__name__}: {exc}",
                "fetched_at": dt.datetime.now(IST)}

    quotes: list[dict[str, Any]] = []
    for label, ticker, group in rows:
        try:
            frame = data[ticker]
        except Exception:
            frame = None
        got = _last_two_closes(frame) if frame is not None else None
        if got is None:
            quotes.append({"label": label, "ticker": ticker, "group": group,
                           "last": None, "change_pct": None, "stale": True,
                           "bar_age_days": None, "missing": True})
            continue
        last, prior, bar_date = got
        age = (today - bar_date).days if bar_date else None
        quotes.append({
            "label": label, "ticker": ticker, "group": group,
            "last": last, "prior_close": prior,
            "change_pct": (last - prior) / prior * 100.0 if prior else None,
            "bar_date": bar_date,
            "bar_age_days": age,
            "stale": age is not None and age > max_bar_age_days,
            "missing": False,
        })
    return {
        "quotes": quotes,
        "fetched_at": dt.datetime.now(IST),
        "missing": sum(1 for q in quotes if q["missing"]),
        "stale": sum(1 for q in quotes if q["stale"] and not q["missing"]),
        "error": None,
    }


def sector_breadth(index: str = "nifty500", *,
                   download: Callable[..., pd.DataFrame] | None = None,
                   min_constituents: int = 5,
                   max_bar_age_days: int = 5,
                   today: dt.date | None = None) -> dict[str, Any]:
    """How many NSE macro-sectors are red, measured from their constituents.

    A sector is red when the **median** constituent's 1-day change is negative.
    Sectors with fewer than `min_constituents` *scored* names are reported
    separately rather than counted — a two-stock "sector" is not breadth.
    """
    import nse_universe as nu                   # lazy: reads a cached NSE CSV

    download = download or _default_download
    today = today or dt.datetime.now(IST).date()

    rows = nu.fetch_constituents(index)
    by_symbol = {f"{r['symbol']}.NS": r["industry"] for r in rows if r.get("industry")}
    if not by_symbol:
        return {"sectors": [], "error": "no constituents with an industry tag"}

    try:
        data = download(sorted(by_symbol), "1mo")
    except Exception as exc:
        return {"sectors": [], "error": f"{type(exc).__name__}: {exc}"}

    per_sector: dict[str, list[float]] = {}
    scored = stale = missing = 0
    for ticker, industry in by_symbol.items():
        try:
            frame = data[ticker]
        except Exception:
            frame = None
        got = _last_two_closes(frame) if frame is not None else None
        if got is None:
            missing += 1
            continue
        last, prior, bar_date = got
        if bar_date and (today - bar_date).days > max_bar_age_days:
            stale += 1                           # excluded, not averaged in
            continue
        if not prior:
            missing += 1
            continue
        per_sector.setdefault(industry, []).append((last - prior) / prior * 100.0)
        scored += 1

    sectors: list[dict[str, Any]] = []
    thin: list[str] = []
    for name, changes in sorted(per_sector.items()):
        if len(changes) < min_constituents:
            thin.append(name)
            continue
        s = pd.Series(changes)
        median = float(s.median())
        sectors.append({
            "sector": name,
            "median_change_pct": median,
            "mean_change_pct": float(s.mean()),
            "constituents": len(changes),
            "pct_green": float((s > 0).mean() * 100.0),
            "direction": "red" if median < 0 else ("green" if median > 0 else "flat"),
        })
    sectors.sort(key=lambda x: x["median_change_pct"])

    red = sum(1 for s in sectors if s["direction"] == "red")
    green = sum(1 for s in sectors if s["direction"] == "green")
    return {
        "sectors": sectors,
        "red": red,
        "green": green,
        "flat": len(sectors) - red - green,
        "total": len(sectors),
        "universe": index,
        "coverage": {"scored": scored, "stale_excluded": stale,
                     "missing": missing, "universe_size": len(by_symbol),
                     "thin_sectors": thin},
        "error": None,
    }


def overall_tone(nifty_change: float | None, red: int, total: int) -> str:
    """A one-word tone for the card header, from price and breadth only.

    Deliberately mechanical and deliberately NOT astrological: the astro layer
    on this card states almanac facts and makes no directional claim, because
    FA-2 (measuring those windows) has never been run.
    """
    if nifty_change is None:
        return "UNKNOWN"
    # Breadth is optional (the page has a checkbox, and a failed constituent
    # fetch also lands here). Degrade to a price-only read rather than reporting
    # UNKNOWN while holding a perfectly good Nifty change — but note the
    # price-only STRONG is the more generous call, since breadth cannot veto it.
    breadth_red = (red / total) if total else None
    if nifty_change <= -0.5 or (breadth_red is not None and breadth_red >= 0.70):
        return "WEAK"
    if nifty_change >= 0.5 and (breadth_red is None or breadth_red <= 0.30):
        return "STRONG"
    return "CAUTIOUS"


def build_brief(*, when: dt.datetime | None = None,
                include_breadth: bool = True,
                download: Callable[..., pd.DataFrame] | None = None,
                sentiment: dict[str, Any] | None = None) -> dict[str, Any]:
    """The whole card model: quotes + breadth + panchang + sentiment.

    `sentiment` is passed in rather than fetched so the page keeps using the one
    reading it already owns — a second sentiment source would be the same
    two-surfaces-disagreeing mistake the moon phase avoids.
    """
    when = when or dt.datetime.now(IST)
    snap = global_snapshot(download=download)
    breadth = (sector_breadth(download=download) if include_breadth
               else {"sectors": [], "red": 0, "total": 0, "coverage": {}, "error": None})

    # The astro layer is OPTIONAL and must not be able to take down the market
    # half. `panchang` needs `ephem`, and this repo runs two separate Python 3.14
    # installs — the dashboard's `pythoncore-3.14-64` and a second
    # `Programs\Python\Python314` — which do not have the same packages. A hard
    # import here meant a missing `ephem` produced "Brief build failed" and no
    # quotes, no breadth, nothing: an optional dependency erasing the whole card.
    # `astro_trading` already models this correctly with its HAS_EPHEM flag.
    pan: dict[str, Any] | None = None
    pan_error: str | None = None
    try:
        import panchang as pn
        pan = pn.panchang(when.date(), now=when)
    except ImportError as exc:
        pan_error = (f"panchang unavailable — {exc}. Install into the interpreter "
                     f"running this app (see analyses/Intraday-Store for the "
                     f"two-interpreter hazard).")
    except Exception as exc:
        pan_error = f"panchang failed — {type(exc).__name__}: {exc}"

    nifty = next((q for q in snap["quotes"] if q["ticker"] == "^NSEI"), None)
    tone = overall_tone(nifty["change_pct"] if nifty else None,
                        breadth.get("red", 0), breadth.get("total", 0))

    return {
        "as_of": when,
        "date": when.date(),
        "quotes": snap["quotes"],
        "quotes_meta": {k: snap[k] for k in ("fetched_at", "missing", "stale", "error")},
        "breadth": breadth,
        "panchang": pan,
        "panchang_error": pan_error,
        "sentiment": sentiment,
        "tone": tone,
        "disclaimer": ("Educational snapshot. Not investment advice. The astro "
                       "layer states almanac facts only — none of it is measured "
                       "against market outcomes in this repo."),
    }
