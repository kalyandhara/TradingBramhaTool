#!/usr/bin/env python3
"""nse_filings_feed.py — the market-wide corporate-filings stream (B-51r/B-111).

`nse_announcements` reads filings for ONE symbol, and `volume_anomaly` uses that
to explain a spike it already found. Both start from a name. **The stream itself
— every material filing the market made today, whether or not the stock moved —
was never read**, although the endpoint has been sitting there the whole time:

    /api/corporate-announcements?index=equities&from_date=DD-MM-YYYY&to_date=…

699 rows for three days, measured 2026-09-21. Without the date range it hands
back only the last 20, which is why "there is no market-wide feed" was an easy
thing to believe.

── What this is for ──────────────────────────────────────────────────────────
The order win, the completed acquisition, the preferential issue: events that are
news on the day they are filed, on names no volume screen surfaced because the
volume had not happened yet. A spike explains itself backwards; this reads
forwards.

── What it can and cannot tell you, stated plainly ──────────────────────────
The API carries a CATEGORY, a one-line text, and a link to the PDF. The **amount
is usually in the PDF** — "₹126 Cr contract", "SAR 771 Mn", "₹937 Cr order book"
are all attachment content. `amount_from` pulls a figure only when the filing's
own text states one (SAMBHV's *"8,695,400 fully convertible warrants at
Rs.115"*), and returns None otherwise rather than guessing. **A missing amount
means "not in the text", never "small".**

> [!important] A NEWS FEED, not a signal. No entry, no stop, no target, and no
> confluence vote. A filing is a reason to go and read the filing.

CLI:
    py -3 -X utf8 tools/nse_filings_feed.py --days 1
    py -3 -X utf8 tools/nse_filings_feed.py --days 3 --bucket ORDER_WIN
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from datetime import date, datetime, timedelta
from typing import Any, Callable, Iterable

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

FEED_URL = ("https://www.nseindia.com/api/corporate-announcements"
            "?index=equities&from_date={frm}&to_date={to}")

#: Buckets, in the order a reader cares about them. The FIRST pattern that
#: matches wins, so the order here is the priority: a preferential issue
#: announced alongside an order win is filed under the money being raised.
BUCKETS: tuple[tuple[str, str], ...] = (
    ("ORDER_WIN",   r"bagging|receiv\w* of orders|order\w*\s*(win|receipt|book)|"
                    r"letter of intent|\bloi\b|work order|contract"),
    ("M&A",         r"acquisition|amalgamation|\bmerger\b|demerger|open offer|"
                    r"scheme of arrangement|slump sale|divest|stake (sale|purchase)"),
    ("FUND_RAISE",  r"preferential|warrant|\bqip\b|rights issue|fund rais|"
                    r"allotment of (securities|shares|equity)|debenture|\bncd\b"),
    ("CAPACITY",    r"capacity|expansion|commission\w+ of|new plant|greenfield|"
                    r"brownfield|capex"),
    ("RATING",      r"credit rating"),
    ("GOVERNANCE",  r"resignation|show cause|penalt|insolvenc|\bnclt\b|"
                    r"sebi order|forensic|fraud|auditor"),
    ("RESULTS",     r"financial result|outcome of board|investor presentation"),
)

#: Exchange-initiated and routine-compliance noise. Dropped before bucketing —
#: these are the reason a raw feed reads as 700 rows of nothing.
NOISE = re.compile(
    r"spurt in (volume|price)|price movement|volume movement|clarification|"
    r"newspaper publication|trading window|compliance certificate|"
    r"surveillance|\basm\b|\bgsm\b|schedule of meet|analysts?/institutional|"
    r"record date|copy of|corrigendum|proceedings of|scrutiniz|"
    r"certificate under|reg\.? 74|reg\.? 39|loss of (share )?certificate|"
    r"duplicate share", re.I)

#: Amounts as a filing's own text states them. Indian formats, in the order that
#: disambiguates them: "Rs. 1,220 crore", "SAR 771 million", "₹126 Cr", and bare
#: share counts with a price ("8,695,400 ... at Rs.115").
#: Foreign currency codes are an EXPLICIT list, not `[A-Z]{3}`. Under re.I the
#: generic pattern matched the "ver" in "over 771 million SAR" and produced
#: "VER 771 million" — a plausible-looking amount in a currency that does not
#: exist, which is worse than no amount at all.
_CCY = "SAR|USD|EUR|AED|GBP|JPY|SGD|CHF|AUD|CAD|QAR|OMR|KWD"
_AMOUNT = re.compile(
    r"(?:(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d+)?)\s*(crore|cr\b|lakh|mn|million|bn|billion)?)"
    r"|(?:\b(" + _CCY + r")\s*([\d,]+(?:\.\d+)?)\s*(million|mn|billion|bn)\b)",
    re.I)


def _norm(row: dict) -> dict[str, Any]:
    return {
        "symbol": (row.get("symbol") or "").strip().upper(),
        "company": (row.get("sm_name") or "").strip(),
        "when": (row.get("an_dt") or row.get("sort_date") or "").strip(),
        "category": (row.get("desc") or "").strip(),
        "text": (row.get("attchmntText") or "").strip(),
        "pdf": (row.get("attchmntFile") or "").strip(),
        "industry": (row.get("smIndustry") or "").strip(),
    }


def bucket_of(category: str, text: str) -> str | None:
    """Which bucket a filing belongs to, or None when it is noise/immaterial."""
    blob = f"{category} {text}"
    if NOISE.search(blob):
        return None
    for name, pattern in BUCKETS:
        if re.search(pattern, blob, re.I):
            return name
    return None


def amount_from(text: str) -> str | None:
    """The amount the filing's OWN TEXT states, or None.

    None means "the text does not say" — most often because the figure is in the
    attached PDF, which nothing here parses. It never means "small", and the
    surface must not render it as a zero.
    """
    m = _AMOUNT.search(text or "")
    if not m:
        return None
    if m.group(1):
        num, unit = m.group(1), (m.group(2) or "").lower()
        unit = {"cr": "crore", "mn": "million", "bn": "billion"}.get(unit, unit)
        return f"₹{num}" + (f" {unit}" if unit else "")
    return f"{m.group(3).upper()} {m.group(4)} {m.group(5).lower()}"


def fetch(days: int = 1, *, session=None, today: date | None = None,
          get: Callable[..., Any] | None = None) -> list[dict[str, Any]]:
    """Raw market-wide filings for the last ``days`` calendar days.

    Without a date range the endpoint returns only the newest 20 rows, which is
    not a feed — it is a sample. The range is what makes this usable.
    """
    import nse_shareholding_fetch as _nsf
    session = session or _nsf._new_session()
    end = today or date.today()
    start = end - timedelta(days=max(0, int(days) - 1))
    url = FEED_URL.format(frm=start.strftime("%d-%m-%Y"), to=end.strftime("%d-%m-%Y"))
    try:
        r = (get or session.get)(url, headers=_nsf.HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []
    return [_norm(row) for row in data] if isinstance(data, list) else []


def material(rows: Iterable[dict], headline_fn: Callable[[str, str], str] | None = None) -> list[dict]:
    """Bucketed, de-noised, de-duplicated filings — newest first.

    De-duplication is by (symbol, bucket, category): a company filing the same
    event twice in a day (the intimation, then the signed copy) is one event, and
    the feed carries both.
    """
    if headline_fn is None:
        from volume_anomaly import filing_headline as headline_fn
    out, seen = [], set()
    for r in rows:
        # Accept a RAW NSE row as well as a normalised one. Handed raw rows this
        # returned an empty list — a silent "no material filings today", which is
        # the worst thing a feed can say when it is wrong.
        if "desc" in r and "category" not in r:
            r = _norm(r)
        b = bucket_of(r.get("category", ""), r.get("text", ""))
        if not b:
            continue
        key = (r.get("symbol"), b, r.get("category"))
        if key in seen:
            continue
        seen.add(key)
        out.append({**r, "bucket": b,
                    "headline": headline_fn(r.get("category", ""), r.get("text", "")),
                    "amount": amount_from(r.get("text", ""))})
    out.sort(key=lambda x: x.get("when", ""), reverse=True)
    return out


def summarise(rows: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["bucket"]] = counts.get(r["bucket"], 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


# ── the desk surface ─────────────────────────────────────────────────────────
def render(days: int = 1, key: str = "filings") -> None:
    """The filings stream on a desk page. Streamlit-only; no logic lives here.

    Rendering is in this module rather than in `dashboard_app` for the reason the
    monolith ratchet exists: a block written on the page is a block no test can
    reach, and this one decides what a reader is told is "material".
    """
    import pandas as pd
    import streamlit as st

    @st.cache_data(ttl=900, show_spinner=False)
    def _load(d: int):
        raw = fetch(d)
        return raw, material(raw)

    with st.spinner("Reading NSE corporate filings…"):
        raw, rows = _load(days)
    if not raw:
        st.info("NSE's announcements endpoint did not answer. Nothing is claimed "
                "about today's filings — this is a failed read, not a quiet day.")
        return

    counts = summarise(rows)
    picked = st.multiselect(
        "Buckets", [b for b, _ in BUCKETS],
        default=[b for b in ("ORDER_WIN", "M&A", "FUND_RAISE", "CAPACITY") if b in counts],
        key=f"{key}_buckets", label_visibility="collapsed")
    shown = [r for r in rows if r["bucket"] in picked] if picked else rows
    st.caption(
        f"**{len(raw)} filings** over {days} day(s) → **{len(rows)} material** "
        + (" · ".join(f"{k} {v}" for k, v in counts.items()) or "none")
        + f" · showing {len(shown)}. Exchange notices and routine compliance are "
        "dropped. **Amounts appear only when the filing's own text states one** — "
        "most figures are in the attached PDF, which is not parsed, so a missing "
        "amount means *not in the text*, never *small*.")

    if not shown:
        st.info("No filings in the selected buckets.")
        return
    st.dataframe(pd.DataFrame([{
        "When": r["when"][:11], "Symbol": r["symbol"], "Bucket": r["bucket"],
        "Amount (as filed)": r["amount"] or "—",
        "What": r["headline"], "Filing": r["pdf"] or None,
    } for r in shown]), use_container_width=True, hide_index=True,
        column_config={"Filing": st.column_config.LinkColumn(
            "Filing", display_text="PDF ↗")})
    st.caption("A NEWS FEED, not a signal — no entry, stop or target, and no "
               "confluence vote. A filing is a reason to go and read the filing.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Market-wide NSE corporate filings")
    ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--bucket", default=None, help="ORDER_WIN / M&A / FUND_RAISE / …")
    ap.add_argument("--limit", type=int, default=40)
    a = ap.parse_args()

    raw = fetch(a.days)
    rows = material(raw)
    if a.bucket:
        rows = [r for r in rows if r["bucket"] == a.bucket.upper()]
    print(f"{len(raw)} filings fetched · {len(rows)} material "
          f"({', '.join(f'{k} {v}' for k, v in summarise(rows).items()) or 'none'})\n")
    for r in rows[:a.limit]:
        amt = f"  [{r['amount']}]" if r["amount"] else ""
        print(f"{r['when'][:11]}  {r['symbol']:<12} {r['bucket']:<11}{amt}")
        print(f"              {r['headline'][:150]}")
    if rows:
        print("\nAmounts are only shown when the filing TEXT states one — most "
              "figures live in the attached PDF, which is not parsed. A missing "
              "amount means 'not in the text', never 'small'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
