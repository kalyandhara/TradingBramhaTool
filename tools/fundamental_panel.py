#!/usr/bin/env python3
"""fundamental_panel.py — the Strategy Hub fundamentals block, computed (PR-1c).

Roadmap rung PR-1c from `analyses/Pattern-Reporting-Enhancement-Roadmap`, the
third and last frozen literal on that page. `_FS_DATA` held stock, sector, market
cap, a /100 score, EPS CAGR, a PE band, LTP and day change — **all hardcoded**,
beneath a caption reading *"Scores computed from the last fundamental data pull"*.

── The shield's /100 is NOT recomputed, because this desk refused to have one ──
`fundamental_score`'s own docstring is explicit:

    "There is **no overall /100 here.** The dashboard already carries the M1
     technical Overall Rating, the council verdict, and Setup Intelligence; a
     fourth number badged 'Overall' would be read as a competing master score."

It emits business quality as a **word** specifically "so it cannot be mistaken
for a fourth Overall Rating". The frozen block's `🛡 81 /100` is exactly the
number that decision forbids, and recomputing it would mean **inventing** it.

So the shield is replaced by the two readings the scorer actually produces:
**business quality** and **entry price**, scored separately. That is not a
downgrade — it is strictly more informative, and the module that owns the split
says why: *"a good business at a bad price is the single most common way a
fundamentals page misleads."* CRISIL is that case today: GOOD QUALITY (74) at a
STRETCHED entry (42), which one number badged 81 cannot express.

── "EPS 3Y CAGR" is labelled PROFIT CAGR, because that is what is computed ────
`derive_fundamentals` returns `profit_cagr_3y`, not an EPS CAGR. They differ by
dilution, which the same payload measures separately (`dilution_pct`). Printing a
profit CAGR under an EPS label would be a small lie that compounds on any name
that issued stock.

── The PE band is PE AT YEAR-ENDS, not a continuous range ─────────────────────
A true 3-year PE range needs EPS at every point in time; what exists is EPS at
each annual period end. So the band is each year-end's price divided by that
year's EPS — **4 points**, labelled as such. A continuous range computed from 4
annual snapshots would be a different quantity wearing the same name.

── Absent renders absent ─────────────────────────────────────────────────────
Every field is independently optional. A name whose statements do not resolve
shows blanks rather than carrying a frozen value forward, and `note` says what
failed.

CLI:
    py -3 -X utf8 tools/fundamental_panel.py
"""
from __future__ import annotations

import sys
from typing import Any, Callable, Iterable, Optional

#: The roster. (symbol, display). The NAMES are a fixed watch list captured in
#: August 2026 — nothing here re-picks them, and the surface says so. Only the
#: numbers are live.
#:
#: Symbols are pinned, never fuzzy-matched at render time. The near-misses on
#: this very roster include PIRAMALFIN for "Piramal Pharma" and JUBLPHARMA for
#: "Jubilant FoodWorks"; a mis-resolved symbol would score one company and print
#: another's name, which is worse than the frozen number it replaces.
ROSTER: tuple[tuple[str, str], ...] = (
    ("DCMSHRIRAM", "DCM Shriram"),
    ("VEDL",       "Vedanta"),
    ("JUBLFOOD",   "Jubilant FoodWorks"),
    ("CRISIL",     "CRISIL"),
    ("HYUNDAI",    "Hyundai Motor India"),
    ("PPLPHARMA",  "Piramal Pharma"),
)

#: How far back the price history reaches, for the day change and the year-end
#: PE points. 5 years covers the four annual periods yfinance typically serves.
PRICE_PERIOD = "5y"

#: Cache lifetime. Statements change quarterly at best; an hour is generous.
TTL = 3600


def symbols() -> list[str]:
    return [s for s, _ in ROSTER]


def _f(v: Any) -> Optional[float]:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if x == x else None


def pe_at_year_ends(annual: Optional[Iterable[dict]], closes) -> list[dict]:
    """PE at each annual period end: that day's close over that year's EPS.

    `closes` is a price Series indexed by date. Returns one row per period that
    could be priced AND had a positive EPS — a negative or missing EPS has no
    meaningful PE, and substituting one would invent the band this exists to
    report honestly.
    """
    out: list[dict] = []
    if closes is None or annual is None:
        return out
    import pandas as pd
    for row in annual:
        eps = _f(row.get("eps"))
        period = row.get("period")
        if eps is None or eps <= 0 or not period:
            continue
        try:
            px = closes.asof(pd.Timestamp(period))
        except Exception:
            continue
        px = _f(px)
        if px is None or px <= 0:
            continue
        out.append({"period": str(period), "eps": round(eps, 2),
                    "price": round(px, 2), "pe": round(px / eps, 1)})
    return out


def build_row(symbol: str, display: str, deep: Optional[dict],
              info: Optional[dict], closes=None) -> dict[str, Any]:
    """One roster row, every field independently optional."""
    d, f = deep or {}, info or {}
    row: dict[str, Any] = {
        "Symbol": symbol, "Stock": display,
        "Sector": d.get("sector") or f.get("sector"),
        "MCap Cr": None, "Business": None, "Business score": None,
        "Entry": None, "Entry score": None, "Profit CAGR 3Y %": None,
        "PE now": None, "PE low": None, "PE high": None, "PE points": 0,
        "LTP": None, "Day %": None, "Coverage": None, "note": None,
    }
    if not d:
        row["note"] = "statements did not resolve"
        return row

    mc = _f(d.get("market_cap"))
    row["MCap Cr"] = round(mc / 1e7, 0) if mc else None     # rupees -> crore
    row["Profit CAGR 3Y %"] = _f(d.get("profit_cagr_3y"))
    row["PE now"] = _f(d.get("pe"))
    row["LTP"] = _f(d.get("price"))

    try:
        import fundamental_score as fs
        sc = fs.score_all(f, d)
        row["Business"] = sc["business"]["word"]
        row["Business score"] = sc["business"]["score"]
        row["Entry"] = sc["entry"]["word"]
        row["Entry score"] = sc["entry"]["score"]
        cov = sc.get("coverage") or {}
        if cov.get("total"):
            row["Coverage"] = f"{cov['have']}/{cov['total']}"
    except Exception:
        row["note"] = "scorer failed"

    band = pe_at_year_ends(d.get("annual"), closes)
    if band:
        pes = [b["pe"] for b in band]
        row["PE low"], row["PE high"] = min(pes), max(pes)
        row["PE points"] = len(pes)

    if closes is not None and len(closes) >= 2:
        last, prev = _f(closes.iloc[-1]), _f(closes.iloc[-2])
        if last is not None:
            row["LTP"] = round(last, 2)
            if prev:
                row["Day %"] = round((last / prev - 1) * 100, 2)
    return row


def build(fetch_deep: Optional[Callable[[str], dict]] = None,
          prices: Optional[dict] = None) -> list[dict[str, Any]]:
    """Every roster row. Injectable so the tests never touch the network."""
    import stock_council as council

    if fetch_deep is None:
        import fundamentals_deep as fdeep
        fetch_deep = fdeep.derive_fundamentals

    out = []
    for sym, disp in ROSTER:
        try:
            deep = fetch_deep(sym)
        except Exception:
            deep = None
        try:
            info = council.fetch_fundamentals(sym)
        except Exception:
            info = None
        out.append(build_row(sym, disp, deep, info,
                             (prices or {}).get(sym)))
    return out


def fetch_closes(syms: Optional[Iterable[str]] = None,
                 period: str = PRICE_PERIOD) -> dict[str, Any]:
    """{symbol: close Series} from one batched request."""
    want = list(syms) if syms is not None else symbols()
    if not want:
        return {}
    try:
        import trending_stocks as ts
        hist = ts._batch_history(want, period=period)
    except Exception:
        return {}
    out = {}
    for sym, df in (hist or {}).items():
        try:
            # CAPITALISED columns -- the same trap B-60's live run hit.
            out[sym] = df["Close"].dropna()
        except (KeyError, TypeError):
            continue
    return out


_cached_fn = None


def cached_rows() -> list[dict[str, Any]]:
    """`build`, memoised by Streamlit when it is available.

    The caching lives here rather than in `dashboard_app` so the monolith gains
    no function for it (the B-87 ratchet).
    """
    global _cached_fn

    def _go():
        return build(prices=fetch_closes())

    if _cached_fn is None:
        try:
            import streamlit as st
            _cached_fn = st.cache_data(ttl=TTL, show_spinner=False)(_go)
        except Exception:                                    # pragma: no cover
            _cached_fn = _go
    return _cached_fn()


#: Score -> colour, for the two verdict chips. Shared so business and entry are
#: read on the same scale even though they answer different questions.
def _chip(score: Optional[int]) -> str:
    if score is None:
        return "#6c757d"
    if score >= 70:
        return "#2e7d32"
    if score >= 50:
        return "#f9a825"
    return "#c62828"


def _pe_bar(lo, hi, now, width: int = 90) -> str:
    """Where today's PE sits inside the year-end band. '' when not computable."""
    if lo is None or hi is None or now is None or hi <= lo:
        return ""
    frac = max(0.0, min(1.0, (now - lo) / (hi - lo)))
    marker = int(frac * width)
    return (
        f'<div style="position:relative;width:{width}px;height:8px;'
        f'background:#e0e0e0;border-radius:4px;display:inline-block;">'
        f'<div style="width:{marker}px;height:8px;background:#1565c0;'
        f'border-radius:4px;"></div>'
        f'<div style="position:absolute;top:-2px;left:{marker}px;'
        f'width:3px;height:12px;background:#ff6f00;border-radius:2px;"></div>'
        f'</div><span style="font-size:10px;margin-left:5px;">{now:.1f}x</span>'
    )


def render(tokens: Optional[dict] = None) -> None:
    """The panel. Rendering lives here so the monolith gains one call (B-87)."""
    import streamlit as st

    muted = (tokens or {}).get("text_muted", "#8b949e")
    border = (tokens or {}).get("border", "#30363d")

    st.markdown("#### Fundamentals  \u00b7  Watch List")
    st.caption(
        "**The six names are a fixed watch list from August 2026** \u2014 nothing "
        "here re-picks them. **Every number is computed** from `fundamentals_deep` "
        "+ `fundamental_score` at load (PR-1c).\n\n"
        "**There is no /100 shield, on purpose.** `fundamental_score` deliberately "
        "emits no overall score \u2014 a fourth number badged 'Overall' would compete "
        "with the technical rating and the council verdict \u2014 so this shows the two "
        "readings it does produce. **A good business at a bad price is the most "
        "common way a fundamentals page misleads**, and one number cannot say both."
    )

    rows = cached_rows()
    for r in rows:
        c1, c2, c3, c4, c5, c6 = st.columns([2.4, 2.0, 1.1, 1.8, 1.6, 1.0])
        with c1:
            mc = ("" if r["MCap Cr"] is None
                  else f" \u00b7 \u20b9{r['MCap Cr']:,.0f}Cr")
            st.markdown(
                f'<div style="padding-top:4px;font-weight:600;">{r["Stock"]}</div>'
                f'<div style="font-size:11px;color:{muted};">'
                f'{r["Sector"] or "sector n/a"}{mc}</div>',
                unsafe_allow_html=True)
        with c2:
            def _pill(word, score):
                if not word:
                    return f'<span style="font-size:11px;color:{muted};">n/a</span>'
                return (f'<span style="background:{_chip(score)};color:#fff;'
                        f'border-radius:6px;padding:2px 8px;font-size:11px;'
                        f'font-weight:600;">{word}'
                        + (f' {score}' if score is not None else '') + '</span>')
            st.markdown(
                f'<div style="padding-top:2px;">{_pill(r["Business"], r["Business score"])}</div>'
                f'<div style="padding-top:3px;">{_pill(r["Entry"], r["Entry score"])}</div>'
                f'<div style="font-size:10px;color:{muted};">business \u00b7 entry'
                + (f' \u00b7 {r["Coverage"]} inputs' if r["Coverage"] else '')
                + '</div>',
                unsafe_allow_html=True)
        with c3:
            cg = r["Profit CAGR 3Y %"]
            body = ('<span style="font-size:11px;color:%s;">n/a</span>' % muted
                    if cg is None else
                    f'<span style="color:{"#2e7d32" if cg >= 0 else "#c62828"};'
                    f'font-weight:600;">{cg:+.1f}%</span>')
            st.markdown(
                f'<div style="padding-top:6px;font-size:12px;">{body}'
                f'<br><span style="font-size:10px;color:{muted};">'
                f'Profit CAGR 3Y</span></div>', unsafe_allow_html=True)
        with c4:
            bar = _pe_bar(r["PE low"], r["PE high"], r["PE now"])
            if bar:
                label = (f'PE at {r["PE points"]} year-ends: '
                         f'{r["PE low"]:.0f}\u2013{r["PE high"]:.0f}x')
            else:
                # A loss-making company has no PE. Saying so beats a blank, and
                # beats the 62x the frozen table printed for exactly this case.
                label = ("no PE \u2014 not profitable on TTM earnings"
                         if r["PE now"] is None else f'PE {r["PE now"]:.1f}x \u00b7 no band')
            st.markdown(
                f'<div style="padding-top:8px;">{bar}</div>'
                f'<div style="font-size:10px;color:{muted};">{label}</div>',
                unsafe_allow_html=True)
        with c5:
            ltp = "n/a" if r["LTP"] is None else f'\u20b9{r["LTP"]:,.2f}'
            day = r["Day %"]
            sub = ('' if day is None else
                   f'<div style="font-size:11px;color:'
                   f'{"#2e7d32" if day >= 0 else "#c62828"};">{day:+.2f}% today</div>')
            st.markdown(
                f'<div style="padding-top:4px;font-size:14px;font-weight:700;">'
                f'{ltp}</div>{sub}', unsafe_allow_html=True)
        with c6:
            st.markdown(
                f'<div style="padding-top:6px;">'
                f'<a href="?nav=analyze&symbol={r["Symbol"]}" target="_self" '
                f'style="font-size:11px;">Analyze \u2197</a></div>',
                unsafe_allow_html=True)
        if r["note"]:
            st.caption(f'{r["Stock"]}: {r["note"]}')
        st.markdown(
            f'<hr style="border:none;border-top:1px solid {border};'
            f'margin:4px 0;">', unsafe_allow_html=True)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # pragma: no cover
        pass
    rows = build(prices=fetch_closes())
    print(f"\n{'Stock':<22}{'Business':<16}{'Entry':<13}{'CAGR3Y':>8}"
          f"{'PE':>7}{'PE band':>14}{'LTP':>10}{'Day%':>7}")
    for r in rows:
        biz = f"{r['Business'] or '-'} {r['Business score'] or ''}".strip()
        ent = f"{r['Entry'] or '-'} {r['Entry score'] or ''}".strip()
        cagr = "-" if r["Profit CAGR 3Y %"] is None else f"{r['Profit CAGR 3Y %']:+.1f}"
        pe = "-" if r["PE now"] is None else f"{r['PE now']:.1f}"
        band = ("-" if r["PE low"] is None
                else f"{r['PE low']:.0f}-{r['PE high']:.0f}x ({r['PE points']}y)")
        ltp = "-" if r["LTP"] is None else f"{r['LTP']:,.2f}"
        day = "-" if r["Day %"] is None else f"{r['Day %']:+.2f}"
        print(f"{r['Stock']:<22}{biz:<16}{ent:<13}{cagr:>8}{pe:>7}{band:>14}"
              f"{ltp:>10}{day:>7}")
        if r["note"]:
            print(f"{'':<22}note: {r['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
