"""Stock-detail panels — fundamentals header/history, red flags, ownership flow,
momentum meter, pattern metrics, horizon geometry.

Extracted verbatim from dashboard_app.py (B-171 monolith ratchet, 2026-10-17).
dashboard_app re-imports every name, so callers are unchanged.
"""
from __future__ import annotations

import fundamentals_deep as fdeep
import horizon_geometry as hgeo
import nse_shareholding_fetch as nse
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import report_style as rs
import scanner_templates as sc
import streamlit as st
import fundamental_score as fscore
import peer_comparison as pcmp


def _cr(v: float | None, currency: str | None = "INR") -> str | None:
    """Indian-crore formatting for statement figures (1 Cr = 1e7).

    Non-INR reporting currencies are left in millions rather than silently
    converted — yfinance reports some cross-listed names in USD and a crore
    label on a dollar figure would be wrong, not just unusual.
    """
    if v is None:
        return None
    if (currency or "INR").upper() != "INR":
        return f"{v/1e6:,.0f}M {currency}"
    return f"₹{v/1e7:,.0f} Cr"


def _q(v: float | None, suffix: str = "", dp: int = 2) -> str | None:
    """Format a number, preserving None so stat_card can render DATA N/A."""
    return None if v is None else f"{v:,.{dp}f}{suffix}"


def render_fundamental_header(symbol: str, df: pd.DataFrame,
                              fundamentals: dict, deep: dict) -> None:
    """FR-1 — sticky identity header + the 9-metric strip, plus the growth and
    quality figures that only exist now that statements are fetched.

    Tone discipline: colour is applied only where this repo already has a stated
    threshold (D/E, ROE, ROCE — the High-Growth Screener sliders and the
    multibagger query use exactly these floors). Valuation bands (P/E, P/B) are
    deliberately left neutral here: band-scoring is FR-2's job and must live in
    ONE shared scorer feeding both these figures and the radar's axes, or the
    page grows a fourth competing "overall" verdict.
    """
    f, d = fundamentals or {}, deep or {}
    cur = d.get("currency") or "INR"

    price = float(df["close"].iloc[-1])
    prev = float(df["close"].iloc[-2]) if len(df) > 1 else price
    chg = (price / prev - 1) * 100 if prev else 0.0
    as_of = str(df.index[-1])[:10]
    # A move that rounds to 0.00% is flat, not a down day — an unqualified ▼ on
    # "-0.00%" reads as a rendering fault.
    if chg > 0.005:
        chg_arrow, chg_col = "▲", rs.TOKENS["good"]
    elif chg < -0.005:
        chg_arrow, chg_col = "▼", rs.TOKENS["risk"]
    else:
        chg_arrow, chg_col = "•", rs.TOKENS["text_muted"]

    # ── Identity header ──
    chips = []
    if f.get("sector"):
        chips.append(rs.chip(f["sector"], "info"))
    if f.get("industry"):
        chips.append(rs.chip(f["industry"], "neutral"))
    mcap = f.get("market_cap")
    if mcap:
        # NSE convention: >₹20,000 Cr large, ₹5,000-20,000 Cr mid, below small.
        cr = mcap / 1e7
        band = "LARGE CAP" if cr >= 20000 else ("MID CAP" if cr >= 5000 else "SMALL CAP")
        chips.append(rs.chip(band, "neutral"))
    cov = d.get("coverage") or {}
    if cov:
        cov_tone = "good" if cov.get("have", 0) >= cov.get("total", 11) - 2 else "warn"
        chips.append(rs.chip("STATEMENT FIELDS", cov_tone,
                             f"{cov.get('have', 0)}/{cov.get('total', 0)}"))
    if not d.get("available"):
        chips.append(rs.chip("NO STATEMENTS", "absent"))

    st.markdown(
        f"""
        <div style="position:sticky;top:0;z-index:99;background:{rs.TOKENS['surface_warm']};
                    border:1px solid {rs.TOKENS['border']};border-radius:12px;
                    padding:11px 15px;margin:4px 0 10px 0;">
          <div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;">
            <span style="font-family:Georgia,'Times New Roman',serif;font-size:23px;
                         font-weight:700;color:{rs.TOKENS['accent']};">{symbol}</span>
            <span style="font-size:13px;color:{rs.TOKENS['text_body']};">
              {d.get('long_name') or ''}</span>
            <span class="tb-mono" style="font-size:26px;font-weight:700;
                         color:{rs.TOKENS['text']};margin-left:auto;">₹{price:,.2f}</span>
            <span class="tb-mono" style="font-size:14px;font-weight:700;color:{chg_col};">
              {chg_arrow} {chg:+.2f}%</span>
          </div>
          <div style="margin-top:7px;">{''.join(chips)}</div>
          <div class="tb-micro" style="margin-top:2px;">
            PRICE AS OF {as_of} · STATEMENTS AS OF {d.get('as_of') or '—'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── 9-metric strip ──
    d2e, roe, roce = f.get("debt_to_equity"), f.get("roe"), d.get("roce")
    # 52W range is computed from the loaded frame, but only when the frame
    # actually covers a year. On a 3M lookback a 60-bar high/low labelled
    # "52W RANGE" would be a quietly wrong number, so it renders DATA N/A.
    if len(df) >= 252:
        hi = float(df["high"].tail(252).max())
        lo = float(df["low"].tail(252).min())
    else:
        hi = lo = None
    cells = [
        rs.stat_card("P / E", _q(f.get("pe"), "×")),
        rs.stat_card("P / B", _q(f.get("pb"), "×")),
        # yfinance reports debtToEquity as a percentage (50 = 0.50×).
        rs.stat_card("D / E", None if d2e is None else f"{d2e/100:,.2f}×",
                     tone=("good" if (d2e is not None and d2e < 50)
                           else "risk" if (d2e is not None and d2e > 100) else "neutral")),
        rs.stat_card("ROE", _q(roe, "%"),
                     tone="good" if (roe is not None and roe >= 15) else "neutral"),
        rs.stat_card("ROCE", _q(roce, "%"),
                     sub=None if d.get("roce_prev") is None else f"prev {d['roce_prev']:.1f}%",
                     tone="good" if (roce is not None and roce >= 15) else "neutral"),
        rs.stat_card("EPS TTM", _q(f.get("eps_ttm") if f.get("eps_ttm") is not None
                                   else d.get("eps_ttm"))),
        rs.stat_card("DIV YIELD", _q(f.get("dividend_yield"), "%")),
        rs.stat_card("MKT CAP", _cr(mcap, cur)),
        rs.stat_card("52W RANGE",
                     None if (hi is None or lo is None) else f"{lo:,.0f}–{hi:,.0f}"),
    ]
    st.markdown(rs.section("Valuation & Quality"), unsafe_allow_html=True)
    # Both rows on a 5-column grid: the second row holds 4 cards and simply
    # leaves the fifth slot empty, so card widths stay identical down the page.
    st.markdown(rs.strip(cells[:5], cols=5) + rs.strip(cells[5:], cols=5),
                unsafe_allow_html=True)

    # ── Statement-derived figures (the layer FR-1 adds) ──
    if d.get("available"):
        g = [
            rs.stat_card("REV CAGR 3Y", _q(d.get("revenue_cagr_3y"), "%"),
                         sub=_q(d.get("revenue_cagr_5y"), "% (5Y)") or "5Y n/a"),
            rs.stat_card("PROFIT CAGR 3Y", _q(d.get("profit_cagr_3y"), "%"),
                         sub=_q(d.get("profit_cagr_5y"), "% (5Y)") or "5Y n/a"),
            rs.stat_card("NET MARGIN", _q(d.get("net_margin"), "%"),
                         sub=_q(d.get("opm"), "% OPM")),
            rs.stat_card("FREE CASH FLOW", _cr(d.get("fcf"), cur),
                         sub=(f"{d['fcf_negative_streak']}y negative streak"
                              if d.get("fcf_negative_streak") else None),
                         tone="risk" if d.get("fcf_negative_streak") else "neutral"),
            rs.stat_card("DEBTOR DAYS", _q(d.get("debtor_days"), "d", 0),
                         sub=_q(d.get("wc_days"), "d working cap", 0)),
        ]
        st.markdown(rs.section("Growth & Quality — from financial statements"),
                    unsafe_allow_html=True)
        st.markdown(rs.strip(g, cols=5), unsafe_allow_html=True)
        miss = (d.get("coverage") or {}).get("missing") or []
        st.caption(
            f"{d.get('annual_periods', 0)} annual / {d.get('quarterly_periods', 0)} "
            f"quarterly periods available from yfinance"
            + (f" · not computable: {', '.join(miss)}" if miss else "")
            + " · a 5Y CAGR needs six annual columns; fewer means it is genuinely "
              "unavailable, not zero."
        )
    else:
        st.markdown(
            rs.callout("No financial statements.",
                       "yfinance returned no income statement, balance sheet or "
                       "cash-flow for this symbol — common for newly-listed and "
                       "thin BSE/SME names. Growth, ROCE and working-capital "
                       "figures are not shown rather than estimated.",
                       tone="absent"),
            unsafe_allow_html=True)


def _axis_tone(score: int | None) -> str:
    """Score band -> semantic tone. Absent scores are grey, never a middling
    amber that would read as 'average' when it means 'unknown'."""
    if score is None:
        return "absent"
    if score >= 70:
        return "good"
    if score >= 45:
        return "warn"
    return "risk"


def render_horizon_geometry(symbol: str, df: "pd.DataFrame") -> None:
    """Year spiral (polar) + pivot price-time geometry — see horizon_geometry.py.

    Context, not a signal. Both are long-horizon perspective views; the pivot
    nodes are computed in a declared normalized space so they do not move with
    zoom, and nothing here has been measured as an edge.
    """
    st.markdown(rs.section("Horizon geometry"), unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**Year spiral** — angle = day of year, radius = close (log)")
        sp = hgeo.year_spiral(df)
        if len(sp) < 2:
            st.markdown(rs.callout("Not shown.", "needs two calendar years",
                                   tone="absent"), unsafe_allow_html=True)
        else:
            fig = go.Figure()
            newest = max(sp)
            for yr in sorted(sp):
                d = sp[yr]
                now = yr == newest
                fig.add_trace(go.Scatterpolar(
                    r=d["r"], theta=d["theta"], mode="lines", name=yr,
                    customdata=d["date"].dt.strftime("%d %b %Y"),
                    hovertemplate="%{customdata}<br>%{r:,.2f}<extra></extra>",
                    line=dict(width=2.6 if now else 1.1,
                              color=rs.TOKENS["accent"] if now else None),
                    opacity=1.0 if now else 0.6))
            fig.update_layout(
                height=420, margin=dict(l=20, r=20, t=20, b=20),
                legend=dict(font=dict(size=9), orientation="h", y=-0.08),
                polar=dict(
                    radialaxis=dict(type="log", tickfont=dict(size=9)),
                    angularaxis=dict(rotation=90, direction="clockwise",
                                     tickmode="array",
                                     tickvals=[i * 30 for i in range(12)],
                                     ticktext=["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])))
            st.plotly_chart(fig, width="stretch", key=f"hg_spiral_{symbol}")
            st.caption("One loop per calendar year, clockwise from January at the "
                       "top. Same angle = same time of year, so seasonal habits and "
                       "each year's range compare directly. Log radius so early "
                       "years are not crushed into the centre.")

    with c2:
        st.markdown("**Pivot geometry** — circles on major weekly swings")
        geo = hgeo.pivot_geometry(df)
        if not geo.ok:
            st.markdown(rs.callout("Not shown.", geo.note or "no data",
                                   tone="absent"), unsafe_allow_html=True)
        else:
            fig = go.Figure()
            w = df["close"].astype(float)
            w.index = pd.to_datetime(w.index)
            w = w.resample("W-FRI").last().dropna()
            fig.add_trace(go.Scatter(x=w.index, y=w.values, mode="lines",
                                     name="weekly close",
                                     line=dict(width=1.4, color=rs.TOKENS["accent"])))
            for circ in geo.circles:
                xs, ys = hgeo.circle_path(geo, circ)
                fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", hoverinfo="skip",
                                         showlegend=False, connectgaps=False,
                                         line=dict(width=0.8, color=rs.TOKENS["absent"]),
                                         opacity=0.55))
            pd_, pp_, pk_ = zip(*geo.pivots)
            fig.add_trace(go.Scatter(x=pd_, y=pp_, mode="lines+markers", name="pivots",
                                     line=dict(width=1.6, color="#f5a623"),
                                     marker=dict(size=7, symbol="square")))
            if geo.nodes:
                fig.add_trace(go.Scatter(
                    x=[n["date"] for n in geo.nodes], y=[n["price"] for n in geo.nodes],
                    mode="markers", name="future nodes",
                    marker=dict(size=11, symbol="diamond", color=rs.TOKENS["risk"]),
                    hovertemplate="%{x|%d %b %Y}<br>%{y:,.2f}<extra></extra>"))
            fig.add_vline(x=w.index[-1], line_width=1, line_dash="dot",
                          line_color=rs.TOKENS["border_strong"])
            lo, hi = min(pp_), max(pp_)
            fig.update_layout(height=420, margin=dict(l=4, r=4, t=6, b=4),
                              yaxis=dict(type="log", range=[np.log10(lo * 0.6),
                                                            np.log10(hi * 1.6)]),
                              legend=dict(font=dict(size=9), orientation="h", y=-0.12))
            st.plotly_chart(fig, width="stretch", key=f"hg_geo_{symbol}")
            st.caption(geo.note)
            if geo.nodes:
                st.dataframe(pd.DataFrame([{
                    "Node date": n["date"].strftime("%d %b %Y"),
                    "Price": round(n["price"], 2),
                    "Circles crossing": n["circles"]} for n in geo.nodes]),
                    hide_index=True, width="stretch")

    st.caption(
        "**Context, not a signal.** Pivot circles are computed in a fixed "
        "normalized space (time scaled to the pivot span plus a projection, log "
        "price scaled to the pivot range), so nodes do not move with zoom — drawn "
        "on date/price axes they can look like ellipses. A dense lattice always "
        "fits past turns; only nodes named before price arrives carry information."
    )


def render_momentum_meter(df: "pd.DataFrame") -> None:
    """RSI(14) and ADX(14) as banded gauges — CONTEXT, never a signal.

    Its own section rather than inside Fundamental signals, deliberately. RSI and
    ADX are price-derived; filing them under a heading that says "fundamental"
    would misdescribe them, and this page's whole convention is that the
    fundamental read and the technical read are separate questions that never get
    merged into one number (see `render_fundamental_signals`). Adjacent, not
    merged.

    Why gauges and not donuts: these live on scales with MEANINGFUL REGIONS.
    RSI 36 is not "36% of something" — it sits in a zone, and the zone is the
    information. A donut would draw it as a third-full ring and say nothing about
    oversold. `rs.gauge` exists for exactly this distinction.

    Bands are the textbook ones and are NOT measured here:
      RSI  <30 oversold · 30-70 neutral · >70 overbought
      ADX  <20 no trend · 20-25 forming · >25 trending
    They are conventions, not thresholds this desk has tested. Anything stronger
    would need the harness, and B-19 measured most single-indicator readings at or
    below a random-entry baseline. Hence the caption, and hence no BUY/SELL.
    """
    if df is None or len(df) < 30:
        return
    try:
        rsi_v = float(sc._rsi_series(df["close"].astype(float), 14).iloc[-1])
        adx_s, _pdi, _mdi = sc._adx_di_series(df, 14)
        adx_v = float(adx_s.iloc[-1])
    except Exception:
        return
    rsi_v = None if not np.isfinite(rsi_v) else rsi_v
    adx_v = None if not np.isfinite(adx_v) else adx_v

    st.markdown(rs.section("Momentum"), unsafe_allow_html=True)

    rsi_word = (None if rsi_v is None else
                "OVERSOLD" if rsi_v < 30 else
                "OVERBOUGHT" if rsi_v > 70 else "NEUTRAL")
    adx_word = (None if adx_v is None else
                "NO TREND" if adx_v < 20 else
                "FORMING" if adx_v < 25 else "TRENDING")

    g_rsi = rs.gauge(rsi_v, "RSI 14", verdict=rsi_word,
                     bands=[(30, "risk"), (70, "neutral"), (100, "good")])
    g_adx = rs.gauge(adx_v, "ADX 14", verdict=adx_word, hi=60.0,
                     bands=[(20, "absent"), (25, "warn"), (60, "good")])
    # 52-week position under the dials. RSI and ADX say how price is MOVING;
    # this says WHERE it is. Both are the same kind of read - descriptive, no
    # verdict - so they share one card rather than being split by a heading.
    close = df["close"].astype(float)
    win = close.tail(252)
    lo52, hi52 = float(win.min()), float(win.max())
    price = float(close.iloc[-1])
    # Nearest swing levels from the same window, as reference ticks. Taken from
    # the recent extremes rather than a pivot detector: this bar is orientation,
    # not a levels engine, and a second definition of "support" on this page
    # would be one more thing that can silently disagree with the chart.
    tail = close.tail(60)
    marks = []
    if len(tail) >= 20:
        sup, res = float(tail.min()), float(tail.max())
        if sup < price:
            marks.append((sup, f"Sup {sup:,.0f}"))
        if res > price:
            marks.append((res, f"Res {res:,.0f}"))
    spectrum = rs.range_spectrum(lo52, hi52, price, marks=marks)

    st.markdown(
        rs.card(f'<div style="display:flex;gap:26px;justify-content:center;'
                f'align-items:flex-start;">{g_rsi}{g_adx}</div>'
                f'{spectrum}'),
        unsafe_allow_html=True,
    )
    st.caption(
        "**Context, not a signal.** Both are descriptive readings of price, and the "
        "bands are textbook conventions rather than thresholds measured here — "
        "B-19's walk-forward put most single-indicator readings at or below a "
        "random-entry baseline, so neither dial implies an action. ADX measures "
        "trend STRENGTH and is direction-blind: a high reading is as consistent "
        "with a strong downtrend as an uptrend. The 52-week bar shows POSITION, "
        "not direction — near the high is green because it means strength, but "
        "B-19 measured 52-Week High Leaders at −0.51% @20d, so green there is "
        "emphatically not 'buy'. Sup/Res ticks are the 60-day extremes, "
        "orientation rather than a levels engine. Read all of it beside the "
        "fundamental block above, not merged into it."
    )


_FLAG_TONE = {
    ("FLAG", "critical"): "risk",
    ("FLAG", "watch"):    "warn",
    ("CLEAN", "critical"): "good",
    ("CLEAN", "watch"):    "good",
}


_FLAG_WORD = {"FLAG": "FLAG", "CLEAN": "CHECKED · CLEAN", "NOT_CHECKED": "NOT CHECKED"}


def render_red_flags(res: dict) -> None:
    """FR-4 — the three-state red-flag list.

    Ordered FLAG → NOT CHECKED → CLEAN, which is deliberately not the flattering
    order. The unchecked items sit second, above the clean ones, because an
    unexamined governance surface deserves more of the reader's attention than a
    check that passed.
    """
    flags = res.get("flags") or []
    c = res.get("counts") or {}
    if not flags:
        return

    st.markdown(rs.section("Red flags"), unsafe_allow_html=True)

    ran = c.get("flagged", 0) + c.get("clean", 0)
    total = len(flags)
    header_chips = (
        rs.chip("Flagged", "risk" if c.get("flagged") else "neutral", str(c.get("flagged", 0)))
        + rs.chip("Checked & clean", "good", str(c.get("clean", 0)))
        + rs.chip("Not checked", "absent", str(c.get("not_checked", 0)))
    )

    # The source mockup shows a green "No Critical Red Flags" panel. It is only
    # honest when every critical check actually ran, which — with three
    # unsourceable governance items — it never does here.
    if res.get("no_critical_flags"):
        verdict = rs.callout("No critical red flags.",
                             "Every critical check ran and came back clean.", tone="good")
    else:
        verdict = rs.callout(
            f"{ran} of {total} checks could run.",
            "This is not a clean bill of health. Auditor qualifications, "
            "related-party transactions and revenue concentration live in "
            "annual-report prose that nothing here parses, so they are shown as "
            "<b>not checked</b> rather than omitted — an unexamined risk is not "
            "an absent one.",
            tone="warn")
    st.markdown(rs.card(f'<div style="margin-bottom:8px;">{header_chips}</div>{verdict}'),
                unsafe_allow_html=True)

    # Plan C — a "verify" deep link per gray-zone flag, so a NOT CHECKED item is
    # actionable (go look here) rather than a dead end. Screener's consolidated
    # page carries promoter/pledge tables AND the annual-report documents; the
    # NSE quote page carries the official shareholding pattern.
    from urllib.parse import quote as _q
    _sym = res.get("symbol", "")
    _scr = f"https://www.screener.in/company/{_q(_sym)}/consolidated/"
    _nseq = f"https://www.nseindia.com/get-quotes/equity?symbol={_q(_sym)}"
    _verify_links = {
        "promoter_holding":      [("screener.in ↗", _scr), ("NSE filing ↗", _nseq)],
        "promoter_pledge":       [("screener.in ↗", _scr), ("NSE filing ↗", _nseq)],
        "auditor_qualification": [("Annual report ↗", _scr)],
        "related_party_txns":    [("Annual report ↗", _scr)],
        "revenue_concentration": [("Annual report ↗", _scr)],
    }
    _link_col = rs.TOKENS.get("accent", "#3fb950")

    order = {"FLAG": 0, "NOT_CHECKED": 1, "CLEAN": 2}
    rows = []
    for f in sorted(flags, key=lambda x: (order.get(x["state"], 9),
                                          0 if x["severity"] == "critical" else 1)):
        tone = _FLAG_TONE.get((f["state"], f["severity"]), "absent")
        fg, bg = rs.tone_colors(tone)
        sev = ("critical" if f["severity"] == "critical" else "watch")
        _lk = _verify_links.get(f["key"])
        links_html = ""
        if _lk:
            anchors = " · ".join(
                f'<a href="{u}" target="_blank" rel="noopener" '
                f'style="color:{_link_col};text-decoration:none;">{t}</a>' for t, u in _lk)
            links_html = (f'<div class="tb-micro" style="margin-top:3px;">'
                          f'Verify manually: {anchors}</div>')
        rows.append(
            f'<div style="display:flex;gap:10px;align-items:flex-start;padding:7px 0;'
            f'border-top:1px solid {rs.TOKENS["border"]};">'
            f'<span class="tb-chip" style="background:{bg};color:{fg};'
            f'border:1px solid {fg}33;min-width:118px;text-align:center;flex-shrink:0;">'
            f'{_FLAG_WORD.get(f["state"], f["state"])}</span>'
            f'<div style="flex:1;min-width:0;">'
            f'<b style="font-size:12.5px;color:{rs.TOKENS["text"]};">{f["label"]}</b>'
            f'<span class="tb-micro" style="margin-left:7px;">{sev} · {f["source"]}</span>'
            f'<div style="font-size:12px;color:{rs.TOKENS["text_body"]};line-height:1.45;">'
            f'{f["detail"]}</div>{links_html}</div></div>'
        )
    st.markdown("".join(rows), unsafe_allow_html=True)


#: |YoY| beyond this on a quarter is annotated rather than left for the reader
#: to spot. Wide enough that ordinary Indian seasonality doesn't trip it.
_QTR_ANOMALY_PCT = 40.0


def render_fundamental_history(deep: dict) -> None:
    """FR-3 — the annual table and the quarterly EPS card grid.

    Two different surfaces on purpose. Years are a *comparison* (how did margin
    trend over five years) and a table is the honest shape for that. Quarters
    are read one at a time, with their own annotations, so they get cards.

    Nothing here is fetched: FR-1's `derive_fundamentals()` already returns
    `annual` and `quarters` with date-matched YoY.
    """
    d = deep or {}
    annual, quarters = d.get("annual") or [], d.get("quarters") or []
    cur = d.get("currency") or "INR"
    if not annual and not quarters:
        return

    if annual:
        st.markdown(rs.section("Annual financials"), unsafe_allow_html=True)
        rows = []
        for a in annual:
            rows.append({
                "Year":        a["period"],
                "Revenue":     _cr(a.get("revenue"), cur) or "—",
                "Rev YoY":     "—" if a.get("revenue_yoy") is None else f"{a['revenue_yoy']:+.1f}%",
                "Net Profit":  _cr(a.get("net_income"), cur) or "—",
                "Profit YoY":  "—" if a.get("profit_yoy") is None else f"{a['profit_yoy']:+.1f}%",
                "Net Margin":  "—" if a.get("net_margin") is None else f"{a['net_margin']:.1f}%",
                "OPM":         "—" if a.get("opm") is None else f"{a['opm']:.1f}%",
                "EPS":         "—" if a.get("eps") is None else f"{a['eps']:,.2f}",
            })
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    if quarters:
        n = len(quarters)
        st.markdown(rs.section(f"Quarterly earnings — last {n} reported"),
                    unsafe_allow_html=True)

        revs = [q.get("revenue") for q in quarters if q.get("revenue") is not None]
        best_rev = max(revs) if revs else None

        cells = []
        for q in quarters:
            eps, yoy = q.get("eps"), q.get("profit_yoy")
            tone = "neutral" if yoy is None else ("good" if yoy >= 0 else "risk")
            # "Highest of the N shown" — NOT "record quarter". yfinance returns
            # about six quarters, so an all-time claim would be unsupported.
            is_best = (best_rev is not None and q.get("revenue") == best_rev)

            sub_bits = []
            if q.get("revenue") is not None:
                sub_bits.append(_cr(q["revenue"], cur))
            if yoy is not None:
                sub_bits.append(f"{'▲' if yoy >= 0 else '▼'} {yoy:+.1f}% profit YoY")
            elif q.get("revenue_yoy") is None:
                sub_bits.append("no year-ago quarter filed")

            card_tone = "good" if is_best else tone
            body = rs.stat_card(
                fdeep.fiscal_quarter_label(q["period"]),
                None if eps is None else f"{eps:,.2f}",
                sub=" · ".join(b for b in sub_bits if b),
                tone=card_tone,
            )
            flags = ""
            if is_best:
                flags += rs.chip(f"Highest revenue of the {n} shown", "good")
            if yoy is not None and abs(yoy) >= _QTR_ANOMALY_PCT:
                flags += rs.chip("Outlier" if yoy > 0 else "Sharp drop",
                                 "good" if yoy > 0 else "risk",
                                 f"{yoy:+.0f}% YoY")
            cells.append(f'<div style="flex:1;min-width:165px;">{body}'
                         f'<div style="margin-top:4px;">{flags}</div></div>')

        st.markdown(
            f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin:4px 0;">'
            f'{"".join(cells)}</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Card value is **EPS**; revenue and profit-YoY sit underneath. YoY is "
            "matched to the same quarter a year earlier **by date** — yfinance's "
            "quarterly frames have gaps, and counting four columns back would "
            "compare a March quarter against the previous December."
        )

    # The honest panel the source mockup shipped, kept as copy rather than built.
    st.markdown(
        rs.callout(
            "Consensus data unavailable.",
            "There is no free NSE analyst-consensus feed, so this page cannot show "
            "a beat/miss record or an estimate-revision trend — and does not "
            "approximate one. What is shown above is entirely reported actuals: "
            "filed revenue, profit, margin and EPS, with year-on-year changes "
            "computed from the filings themselves.",
            tone="risk"),
        unsafe_allow_html=True,
    )


# ── Filter C — ownership flow (DS-2) ──────────────────────────────────────────
#: Cached a full day: the underlying filing is QUARTERLY, so anything shorter
#: re-downloads two ~500 KB XBRLs from NSE to redraw an identical card.
@st.cache_data(ttl=86400, show_spinner=False)
def cached_ownership(symbol: str):
    return nse.fetch_ownership(symbol)


def render_ownership_flow(symbol: str) -> None:
    """Filter C of the Crash-Proof system — the quarter-over-quarter rotation.

    Behind a button because each read pulls two multi-hundred-KB XBRL filings
    from NSE, and because the data only changes once a quarter — paying that on
    every analyzer run would be pure waste.
    """
    st.markdown(rs.section("Filter C — ownership flow (quarterly)"),
                unsafe_allow_html=True)
    _key = f"own_{symbol}"
    if not st.session_state.get(_key):
        if st.button("Fetch shareholding pattern", key=f"own_btn_{symbol}",
                     help="Reads the last two quarterly SEBI shareholding filings "
                          "from NSE (~10s)."):
            st.session_state[_key] = True
            st.rerun()
        st.caption("Not fetched — the ownership leg is unmeasured until you pull it.")
        return

    with st.spinner("Reading the last two shareholding filings…"):
        try:
            own = cached_ownership(symbol)
        except Exception as exc:
            own = None
            st.warning(f"Shareholding fetch failed — {exc}")
    if not own:
        st.info("No readable shareholding filing for this symbol. The ownership "
                "leg stays unmeasured — that is not the same as 'no institutions'.")
        return

    rot = nse.interpret_rotation(own["change"])
    _fg, _bg = rs.tone_colors(rot["tone"])

    # The filing period leads the card. A shareholding read presented without its
    # quarter invites being taken as current positioning, which it never is.
    st.markdown(
        rs.callout(f'{rot["headline"]} — as of {own["as_of"]}'
                   + (f' (vs {own["prev_as_of"]})' if own["prev_as_of"]
                      else ' · no prior quarter to compare'),
                   rot["detail"], tone=rot["tone"]),
        unsafe_allow_html=True)

    if not own["reconciles"]:
        st.warning("This filing did **not** reconcile against NSE's own promoter / "
                   "public figures — treat the split below as unverified.")

    _latest = own["latest"]
    _labels = {"fii": "FII / FPI", "dii": "DII", "mf": "Mutual funds",
               "retail": "Retail", "promoter": "Promoter"}
    for _col, _leg in zip(st.columns(len(nse.HEADLINE_LEGS)), nse.HEADLINE_LEGS):
        _held, _chg = _latest.get(_leg), own["change"].get(_leg)
        _dir = nse.direction(_chg)
        _dc = {"up": rs.TOKENS["good"], "down": rs.TOKENS["risk"],
               "flat": rs.TOKENS["text_muted"], "unknown": rs.TOKENS["absent"]}[_dir]
        with _col:
            st.markdown(
                rs.card(
                    f'<div class="tb-micro">{_labels[_leg]}</div>'
                    f'<div class="tb-mono" style="font-size:17px;font-weight:700;'
                    f'margin-top:2px;">'
                    + (rs.NA if _held is None else f'{_held:.2f}%') + '</div>'
                    f'<div style="font-size:11px;color:{_dc};font-weight:600;'
                    f'margin-top:2px;">{nse.ARROWS[_dir]} '
                    + ("no prior quarter" if _chg is None else f'{_chg:+.2f} pp') +
                    '</div>'),
                unsafe_allow_html=True)

    _marks = {nse.MET: ("✓", rs.TOKENS["good"]), nse.NOT_MET: ("✗", rs.TOKENS["risk"]),
              nse.UNKNOWN: ("?", rs.TOKENS["absent"])}
    _crit = "".join(
        f'<span class="tb-chip" style="background:{_marks[c["state"]][1]}1a;'
        f'color:{_marks[c["state"]][1]};border:1px solid {_marks[c["state"]][1]}33;">'
        f'{_marks[c["state"]][0]} {c["label"]}</span>'
        for c in rot["criteria"])
    st.markdown(
        f'<div style="margin-top:6px;"><span class="tb-micro" '
        f'style="margin-right:6px;">FILTER C CRITERIA</span>{_crit}</div>',
        unsafe_allow_html=True)

    st.caption(
        f"Read straight from the SEBI shareholding-pattern XBRL (the regulatory "
        f"filing, not an aggregator). **Mutual funds are a subset of DII** — those "
        f"two bars overlap and do not add. Moves under "
        f"{rot['flat_band_pp']:.2f} pp read as flat (filing noise). "
        "**Quarterly and lagging**: this describes the register on the filing date, "
        "not today's positioning. It is the *structural* leg only — the framework "
        "reads it against market health (DS-3) and price+volume (DS-4) before it "
        "means buy or avoid. On its own, FII↑ into a falling price is a watchlist, "
        "not a signal.")


def _gauge_svg(pct: float, color: str, label: str, sub: str, size: int = 150) -> str:
    """A half-ring gauge 0-100 as inline SVG (no plotly for one number)."""
    import math
    pct = max(0.0, min(100.0, float(pct)))
    r, cx, cy, w = size * 0.4, size / 2, size * 0.56, size * 0.085
    def arc(a0, a1):
        x0, y0 = cx + r * math.cos(math.pi * (1 - a0)), cy - r * math.sin(math.pi * (1 - a0))
        x1, y1 = cx + r * math.cos(math.pi * (1 - a1)), cy - r * math.sin(math.pi * (1 - a1))
        # A half ring spans 180° at most, so the SVG large-arc flag is never set:
        # with it, anything past 50% drew the long way round the circle.
        return f"M{x0:.1f},{y0:.1f} A{r:.1f},{r:.1f} 0 0 1 {x1:.1f},{y1:.1f}"
    t = rs.TOKENS
    fg = arc(0, max(0.004, pct / 100.0))
    return (f'<svg width="{size}" height="{size * 0.68:.0f}" viewBox="0 0 {size} {size * 0.68:.0f}">'
            f'<path d="{arc(0, 1)}" fill="none" stroke="{t["surface_alt"]}" stroke-width="{w:.1f}" stroke-linecap="round"/>'
            f'<path d="{fg}" fill="none" stroke="{color}" stroke-width="{w:.1f}" stroke-linecap="round"/>'
            f'<text x="{cx}" y="{cy - 2}" text-anchor="middle" font-size="{size * 0.17:.0f}" font-weight="800" fill="{t["text"]}">{label}</text>'
            f'<text x="{cx}" y="{cy + size * 0.1:.0f}" text-anchor="middle" font-size="{size * 0.075:.0f}" font-weight="700" fill="{color}">{sub}</text>'
            f'</svg>')


def render_pattern_metrics(df, nifty_df=None, *, key: str = "pm") -> None:
    """Historical pattern metrics — overhead supply, extension, base / VCP coil,
    scanner-metric radar, exceptional volume. Descriptions of the history the
    page already holds; nothing here is a signal (pattern_metrics.py)."""
    import pattern_metrics as pm
    t = rs.TOKENS
    try:
        m = pm.compute_all(df, nifty_df)
    except Exception as e:                                # noqa: BLE001
        st.caption(f"Historical pattern metrics unavailable: {e}")
        return
    st.markdown("#### 📐 Historical pattern metrics")
    st.caption("Volume · overhead · VCP · normalised fields — read from the daily bars "
               "already loaded. Descriptive only; none of these has been measured for "
               "forward return here.")

    micro = f'font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:{t["text_muted"]};'
    c1, c2 = st.columns(2)
    oh, ex = m["overhead"], m["extension"]
    with c1:
        if oh:
            col = t["good"] if oh["pct"] < pm.OVERHEAD_CLEAR else t["accent"] if oh["pct"] < pm.OVERHEAD_HEAVY else t["risk"]
            gauge = _gauge_svg(oh["pct"], col, f"{oh['pct']:.0f}%", oh["label"])
            body = (f'<div style="{micro}">Overhead supply</div>'
                    f'<div style="font-size:12px;color:{t["text_muted"]};">Prior highs above the current price · last {oh["bars"]} sessions</div>'
                    f'<div style="text-align:center;">{gauge}</div>'
                    f'<div style="font-size:12px;color:{t["text_muted"]};text-align:center;">{oh["note"]}</div>')
            st.markdown(rs.card(body), unsafe_allow_html=True)
    with c2:
        if ex and ex["score"] is not None:
            col = t["good"] if ex["score"] < 33 else t["accent"] if ex["score"] < 66 else t["risk"]
            gauge = _gauge_svg(ex["score"], col, f"{ex['score']:.0f}", ex["band"])
            flag = (f'<div style="font-size:12px;color:{t["risk"]};">⚠ RSI exhaustion — '
                    f'{ex["rsi_pct"]:.0f}th pct of two years, {ex["run5_pct"]:+.1f}% in 5 sessions</div>'
                    if ex["rsi_exhaustion"] else
                    f'<div style="font-size:12px;color:{t["text_muted"]};">RSI {ex["rsi"]:.0f} · '
                    f'{(ex.get("above_sma50_pct") or 0):+.1f}% vs 50-day · {ex["run5_pct"]:+.1f}% / 5d</div>'
                    if ex.get("rsi") is not None else "")
            body = (f'<div style="{micro}">Extension metric</div>'
                    f'<div style="font-size:12px;color:{t["text_muted"]};">Composite: above 50-day and 20-day means, RSI percentile, 5-day run</div>'
                    f'<div style="text-align:center;">{gauge}</div>'
                    f'{flag}')
            st.markdown(rs.card(body), unsafe_allow_html=True)

    c3, c4 = st.columns(2)
    vc, rd = m["vcp"], m["radar"]
    with c3:
        if vc:
            tiles = "".join(
                f'<div style="flex:1;background:{t["surface_alt"]};border-radius:8px;padding:8px 6px;text-align:center;">'
                f'<div style="font-size:16px;font-weight:800;color:{t["text"]};">{v}</div>'
                f'<div style="{micro}font-size:9.5px;">{k}</div></div>'
                for k, v in (("Base length", f"{vc['base_weeks']:.0f}w"),
                             ("Depth", f"{vc['depth_pct']:.1f}%"),
                             ("Contractions", f"{vc['contractions']}")))
            mx = max(vc["ladder"]) or 1.0
            ladder = "".join(
                f'<div style="flex:1;text-align:center;">'
                f'<div style="height:6px;margin:0 8px;border-radius:3px;background:{t["accent"]};'
                f'width:{max(12, d / mx * 100):.0f}%;margin-left:auto;margin-right:auto;"></div>'
                f'<div style="font-size:11px;font-weight:700;color:{t["text_muted"]};margin-top:4px;">L{i + 1}</div>'
                f'<div style="font-size:12px;color:{t["text"]};">{d:.1f}%</div></div>'
                for i, d in enumerate(vc["ladder"]))
            tight = (f'Tightness {vc["tightness_pct"]:.1f}% — final contraction as a share of the first (lower is tighter)'
                     if vc["tightness_pct"] is not None else "")
            body = (f'<div style="{micro}">Base / VCP coil</div>'
                    f'<div style="font-size:12px;color:{t["text_muted"]};">Depth and contractions from the pivot-based detector'
                    f'{" · still forming" if vc["in_progress"] else ""}</div>'
                    f'<div style="display:flex;gap:8px;margin:8px 0;">{tiles}</div>'
                    f'<div style="{micro}font-size:10px;margin-top:4px;">Contraction ladder</div>'
                    f'<div style="display:flex;gap:4px;margin-top:6px;">{ladder}</div>'
                    f'<div style="font-size:11.5px;color:{t["text_muted"]};text-align:center;margin-top:8px;">{tight}</div>')
            st.markdown(rs.card(body), unsafe_allow_html=True)
        else:
            st.markdown(rs.card(f'<div style="{micro}">Base / VCP coil</div>'
                                f'<div style="font-size:12px;color:{t["text_muted"]};">No confirmed contraction '
                                f'sequence in the last 120 sessions — the detector abstains rather than guess.</div>'),
                        unsafe_allow_html=True)
    with c4:
        if rd:
            axes = {k: v for k, v in rd["axes"].items() if v is not None}
            names, vals = list(axes), [axes[k] for k in axes]
            fig = go.Figure(go.Scatterpolar(r=vals + vals[:1], theta=names + names[:1],
                                            fill="toself", line=dict(color="#5b4bd6", width=2),
                                            fillcolor="rgba(91,75,214,0.18)", hoverinfo="theta+r"))
            fig.update_layout(height=230, margin=dict(l=30, r=30, t=20, b=10),
                              polar=dict(radialaxis=dict(range=[0, 100], showticklabels=False, gridcolor="#e8e2d6"),
                                         angularaxis=dict(tickfont=dict(size=11), gridcolor="#e8e2d6"),
                                         bgcolor="rgba(0,0,0,0)"),
                              paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
                              annotations=[dict(text=f"<b>{rd['score']:.1f}</b>" if rd["score"] is not None else "—",
                                                x=0.5, y=0.5, showarrow=False, font=dict(size=22, color=t["text"]))])
            bars = "".join(
                f'<div style="display:flex;align-items:center;gap:8px;font-size:12px;margin:3px 0;">'
                f'<div style="width:70px;color:{t["text_muted"]};">{k}</div>'
                f'<div style="flex:1;height:6px;background:{t["surface_alt"]};border-radius:3px;">'
                f'<div style="width:{v:.0f}%;height:6px;border-radius:3px;background:linear-gradient(90deg,#8a7cf0,#5b4bd6);"></div></div>'
                f'<div style="width:28px;text-align:right;font-weight:700;color:{t["text"]};">{v:.0f}</div></div>'
                for k, v in axes.items())
            st.markdown(f'<div style="{micro}">Scanner metric radar</div>'
                        f'<div style="font-size:12px;color:{t["text_muted"]};">Six normalised axes (0-100) and their mean</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(fig, width="stretch", key=f"{key}_radar", config={"displayModeBar": False})
            st.markdown(bars, unsafe_allow_html=True)
            st.caption("VCP: contraction count, shrinkage, tightness · RS: 1y vs benchmark, ±40pp · Stage: "
                       "Weinstein stack · Volume: share of the last 60 sessions' volume on up bars · "
                       "Low risk: distance to the 10-bar swing low, ≤3% best · Clear path: 100 − overhead %.")

    xv = m["exceptional_volume"]
    if xv:
        # The window is whatever the page loaded (≤ 2 years), so name it by
        # its real length instead of always calling it "two-year".
        _yrs = xv["n_sessions"] / 250
        _win = "two-year" if _yrs >= 1.9 else f"{_yrs:.1f}-year"
        tiles = "".join(
            f'<div style="flex:1;background:{t["surface"]};border:1px solid {t["surface_alt"]};border-radius:8px;padding:10px 12px;">'
            f'<div style="font-size:18px;font-weight:800;color:{t["text"]};">{v}</div>'
            f'<div style="{micro}font-size:9.5px;">{k}</div></div>'
            for k, v in ((f"{_win} avg volume", f"{xv['avg_volume']:,.0f}"),
                         ("Exceptional sessions", f"{xv['count']}"),
                         (f"{xv['mult']:.0f}× threshold", f"{xv['threshold']:,.0f}")))
        top = xv["sessions"][:8]
        mx = max((s["ratio"] for s in top), default=1.0)
        rows = "".join(
            f'<div style="display:flex;align-items:center;gap:10px;font-size:12px;padding:6px 0;border-top:1px solid {t["surface_alt"]};">'
            f'<div style="width:90px;color:{t["text"]};">{pd.Timestamp(s["date"]).strftime("%d %b %Y")}</div>'
            f'<div style="flex:1;height:8px;background:{t["surface_alt"]};border-radius:4px;">'
            f'<div style="width:{s["ratio"] / mx * 100:.0f}%;height:8px;border-radius:4px;background:linear-gradient(90deg,#f6b73c,#e8590c);"></div></div>'
            f'<div style="width:110px;text-align:right;color:{t["text_muted"]};">{s["volume"]:,.0f}</div>'
            f'<div style="width:48px;text-align:right;font-weight:800;color:{t["risk"]};">{s["ratio"]:.1f}×</div></div>'
            for s in top) or f'<div style="font-size:12px;color:{t["text_muted"]};">No session reached the threshold.</div>'
        body = (f'<div style="{micro}">Exceptional volume activity</div>'
                f'<div style="font-size:12px;color:{t["text_muted"]};">Sessions with at least {xv["mult"]:.0f}× the {_win} average volume</div>'
                f'<div style="display:flex;gap:10px;margin:8px 0 10px;">{tiles}</div>{rows}'
                f'<div style="font-size:11px;color:{t["text_muted"]};text-align:center;margin-top:8px;">'
                + (f'Top {len(top)} of {xv["count"]} shown · ' if xv["count"] > len(top) else '')
                + f'{xv["n_sessions"]} trading sessions · {xv["from"]} to {xv["to"]}</div>')
        st.markdown(rs.card(body), unsafe_allow_html=True)


def _period_return(df: pd.DataFrame, days: int) -> float | None:
    col = next((c for c in ("Close", "close") if c in df.columns), None)
    if col is None or len(df) < 2:
        return None
    close = df[col]
    idx = max(0, len(close) - 1 - days)
    start, end = float(close.iloc[idx]), float(close.iloc[-1])
    return round((end / start - 1) * 100, 2) if start != 0 else None


def fmt_money(x: float) -> str:
    if x is None or pd.isna(x):
        return "—"
    sign = "-" if x < 0 else ""
    return f"{sign}₹{abs(x):,.0f}"


def fmt_pct(x: float) -> str:
    if x is None or pd.isna(x):
        return "—"
    return f"{x:+.2f}%"


def gain_loss_badge(x: float) -> str:
    """Icon + sign, never color alone (accessibility — see Lollypop UX research)."""
    if x is None or pd.isna(x):
        return "—"
    arrow = "▲" if x >= 0 else "▼"
    return f"{arrow} {x:+.2f}%"


def render_condition_table(mv_conds: dict, tf_conds: dict,
                            canslim_conds: dict | None = None) -> None:
    rows = [{"Strategy": "Minervini", "Condition": k, "Pass": "✅" if v else "❌"}
            for k, v in mv_conds.items()]
    rows += [{"Strategy": "TechnoFunda", "Condition": k, "Pass": "✅" if v else "❌"}
             for k, v in tf_conds.items()]
    if canslim_conds:
        rows += [{"Strategy": "CANSLIM", "Condition": k,
                  "Pass": ("✅" if v else "❌") if v is not None else "—"}
                 for k, v in canslim_conds.items()]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def _render_thesis(title: str, thesis, accent: str) -> None:
    st.markdown(f"**{title} — conviction {thesis.conviction}/10**")
    rows = [{"Pillar": p.name, "Score": f"{p.score:.0f}/100",
             "Weight": p.weight, "Reasoning": p.reason} for p in thesis.pillars]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    if thesis.breakers:
        st.caption("⚠️ Thesis-breakers: " + "; ".join(thesis.breakers))


def render_fundamental_signals(score: dict) -> None:
    """FR-2 — six signal donuts, the coverage dial, and the good-business vs
    bad-entry split, all off the one shared scorer in fundamental_score.py.

    No overall number is rendered here on purpose. The page already carries the
    M1 technical Overall Rating and the council verdict; a fourth /100 badged
    "fundamental" would be read as a competing master score. The split is two
    words instead.
    """
    axes, cov = score.get("axes") or {}, score.get("coverage") or {}
    biz, entry = score.get("business") or {}, score.get("entry") or {}

    st.markdown(rs.section("Fundamental signals"), unsafe_allow_html=True)

    # ── Verdict chips + coverage dial ──
    biz_tone = _axis_tone(biz.get("score"))
    entry_tone = _axis_tone(entry.get("score"))
    chips = (
        rs.chip("Business", biz_tone, biz.get("word") or rs.NA) +
        rs.chip("Entry", entry_tone, entry.get("word") or rs.NA)
    )
    have, total = cov.get("have", 0), cov.get("total", 0)
    dial = rs.donut(f"{have}/{total}" if total else None, "Scored inputs",
                    pct=(have / total * 100) if total else None,
                    tone="good" if (total and have / total >= 0.8) else "warn")
    st.markdown(
        rs.card(
            f'<div style="display:flex;align-items:center;gap:18px;">'
            f'  <div style="flex:1;">{chips}'
            f'    <div style="font-size:12px;color:{rs.TOKENS["text_body"]};margin-top:6px;">'
            f'      A good business and a good entry price are separate questions — '
            f'      this page answers them separately and never merges them into one '
            f'      number. Fundamental read only; the technical Overall Rating '
            f'      /100 is a different lens.</div>'
            f'  </div>{dial}</div>'
        ),
        unsafe_allow_html=True,
    )

    # ── Six donuts ──
    cells = []
    for name in fscore.AXES:
        a = axes.get(name) or {}
        s = a.get("score")
        cells.append(
            f'<div style="flex:1;min-width:120px;">'
            f'{rs.donut(None if s is None else str(s), a.get("label", name), a.get("verdict"), pct=s, tone=_axis_tone(s))}'
            f'<div style="font-size:9.5px;color:{rs.TOKENS["text_muted"]};'
            f'text-align:center;margin-top:2px;line-height:1.35;">'
            f'{a.get("drivers") or "no inputs available"}</div></div>'
        )
    st.markdown(
        f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin:4px 0 6px 0;">'
        f'{"".join(cells)}</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Bands are calibrated for NSE listed equity and live in one place "
        "(`fundamental_score.py`) so this page and the fundamental radar can "
        "never disagree. Earnings Consistency measures **realised** results "
        "(profitable years, growth years, margin stability) — consensus "
        "estimates have no free NSE source, so this is not a beat/miss record."
    )


def _peer_head_to_head(anchor: str, other: str, df, with_technicals: bool) -> None:
    """Two names, axis by axis, with the gap stated in the direction that matters.

    The mockup's "vs ANCHOR" link. It reuses the rows already scored for the table
    rather than re-fetching, so the drill costs nothing and — more importantly —
    cannot disagree with the table it was opened from.
    """
    a_row = df[df["symbol"] == anchor]
    b_row = df[df["symbol"] == other]
    if not len(a_row) or not len(b_row):
        return
    a_row, b_row = a_row.iloc[0], b_row.iloc[0]

    rows = []
    for ax in fscore.AXES:
        av, bv = pcmp._score_or_none(a_row[ax]), pcmp._score_or_none(b_row[ax])
        if av is None or bv is None:
            gap_txt, tone = rs.NA, "absent"
        else:
            gap = av - bv
            gap_txt = f"{gap:+d}"
            tone = "good" if gap > 5 else ("risk" if gap < -5 else "neutral")
        fg = rs.tone_colors(tone)[0]
        rows.append(
            f'<tr><td style="padding:3px 8px;font-size:11.5px;">'
            f'{fscore.AXIS_LABELS[ax]}</td>'
            f'<td class="tb-mono" style="text-align:right;padding:3px 8px;">'
            f'{"—" if av is None else av}</td>'
            f'<td class="tb-mono" style="text-align:right;padding:3px 8px;">'
            f'{"—" if bv is None else bv}</td>'
            f'<td class="tb-mono" style="text-align:right;padding:3px 8px;'
            f'color:{fg};font-weight:600;">{gap_txt}</td></tr>'
        )
    if with_technicals and "stage_label" in df.columns:
        for col, label, _d in pcmp.TECH_COLUMNS:
            av, bv = a_row.get(col), b_row.get(col)
            # Same formatter as the table: the drill must not render 52w as a
            # bare 3.2 while the row above it says -3.2%.
            fmt = lambda v: pcmp.tech_text(v, col)
            rows.append(
                f'<tr><td style="padding:3px 8px;font-size:11.5px;color:'
                f'{rs.TOKENS["text_muted"]};">{label}</td>'
                f'<td class="tb-mono" style="text-align:right;padding:3px 8px;">{fmt(av)}</td>'
                f'<td class="tb-mono" style="text-align:right;padding:3px 8px;">{fmt(bv)}</td>'
                f'<td></td></tr>'
            )

    st.markdown(
        rs.card(
            f'<table style="width:100%;border-collapse:collapse;">'
            f'<thead><tr>'
            f'<th style="text-align:left;font-size:10px;text-transform:uppercase;'
            f'letter-spacing:.04em;color:{rs.TOKENS["text_muted"]};padding:3px 8px;"></th>'
            f'<th style="text-align:right;font-size:11px;padding:3px 8px;">{anchor}</th>'
            f'<th style="text-align:right;font-size:11px;padding:3px 8px;">{other}</th>'
            f'<th style="text-align:right;font-size:10px;text-transform:uppercase;'
            f'letter-spacing:.04em;color:{rs.TOKENS["text_muted"]};padding:3px 8px;">Gap</th>'
            f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
            f'<div style="font-size:11px;color:{rs.TOKENS["text_muted"]};margin-top:6px;">'
            f'Gap is {anchor} minus {other} in score points, so positive favours '
            f'{anchor}. Technical rows carry no gap column on purpose — a 12-point '
            f'RSI difference is not comparable to a 12-point axis difference.</div>',
            title=f"{anchor} vs {other}",
        ),
        unsafe_allow_html=True,
    )


def _volume_profile(df: pd.DataFrame, n_bins: int = 50):
    """Return (bin_centers, volume_at_price) arrays across the full price range."""
    lo_p, hi_p = df["low"].min(), df["high"].max()
    bins = np.linspace(lo_p, hi_p, n_bins + 1)
    bin_centers = (bins[:-1] + bins[1:]) / 2
    highs   = df["high"].values.astype(float)
    lows    = df["low"].values.astype(float)
    volumes = df["volume"].values.astype(float)
    ranges  = np.where(highs - lows > 0, highs - lows, 1e-9)
    vap = np.zeros(n_bins)
    for i in range(n_bins):
        overlaps = np.maximum(0.0, np.minimum(highs, bins[i + 1]) - np.maximum(lows, bins[i]))
        vap[i] = np.sum(volumes * overlaps / ranges)
    return bin_centers, vap


def _compare(value, operator: str, threshold) -> bool:
    try:
        if isinstance(value, str):
            return (value == threshold) if operator == "==" else False
        v, t = float(value), float(threshold)
    except (TypeError, ValueError):
        return False
    return {">": v > t, "<": v < t, ">=": v >= t, "<=": v <= t, "==": v == t}.get(operator, False)


# The overview strip was the last native `st.metric` row on the page: cold grey
# labels, a proportional face on the figures, and no semantic colour, sitting
# directly above a token-styled verdict card. It now uses the same stat cards as
# everything else, so the numbers line up in mono and each one states its own
# verdict through tone rather than being uniformly black.
def _tone_signed(v, *, good_when_positive=True):
    """Tone for a signed number; neutral when it is missing or flat."""
    if v is None or pd.isna(v) or abs(float(v)) < 1e-9:
        return "neutral"
    up = float(v) > 0
    return "good" if up == good_when_positive else "risk"


def _flag_col(items: list[str], label: str, tone: str, mark: str) -> str:
    """One flag column — micro header in the tone, then the flags themselves.

    Empty columns still render (as a dash) so the three keep their widths and
    the reader can see that a category is empty rather than missing.
    """
    fg, _bg = rs.tone_colors(tone)
    rows = "".join(
        f'<div style="font-size:11.5px;color:{fg};line-height:1.5;">{mark} {i}</div>'
        for i in items) or (
        f'<div style="font-size:11.5px;color:{rs.TOKENS["absent"]};'
        f'line-height:1.5;">—</div>')
    return (f'<div style="flex:1;min-width:150px;">'
            f'<div class="tb-micro" style="color:{fg};">{label}</div>{rows}</div>')

def render_context_ladder(symbol: str, df: "pd.DataFrame", nifty_df) -> None:
    """B-187 — market → sector rungs and 'was it the stock or the market?'.

    Descriptive context, never a signal: the trend word is close vs a rising /
    falling 20-day average, and the attribution just splits last month's move.
    The sector frame comes from the `sector_index_data` snapshot (no new fetch);
    a missing frame says so rather than disappearing.
    """
    import context_ladder as cl
    import nse_universe as nseu
    import snapshot_store as snaps
    try:
        imap = nseu.industry_map("nifty500")
    except Exception:
        imap = {}
    ticker, label = cl.sector_for(symbol, imap)
    sector_df = None
    if ticker:
        try:
            _meta, payload = snaps.load_latest("sector_index_data")
            sector_df = ((payload or {}).get("sector_data") or {}).get(ticker)
        except Exception:
            sector_df = None
    lad = cl.build_ladder(df, nifty_df, sector_df, sector_label=label,
                          sector_ticker=ticker)
    tone = {"Up": "good", "Down": "risk"}
    tiles = []
    for r in lad["rungs"]:
        if r["missing"]:
            sub = ("no index for this sector" if not ticker
                   else "index frame not in the snapshot")
            tiles.append(rs.stat_card(f'{r["rung"]} · {r["label"]}', None, sub))
            continue
        d1 = "—" if r["d1"] is None else f'{r["d1"]:+.1f} %'
        m1 = "—" if r["m1"] is None else f'{r["m1"]:+.1f} %'
        tiles.append(rs.stat_card(f'{r["rung"]} · {r["label"]}', r["trend"] or "—",
                                  f"1D {d1} · 1M {m1}", tone.get(r["trend"], "neutral")))
    if not label:
        tiles.append(rs.stat_card("Sector", None, "not in NIFTY 500 — sector unknown"))
    st.markdown(rs.section("Context ladder"), unsafe_allow_html=True)
    st.markdown('<div style="display:flex;flex-wrap:wrap;gap:8px;">'
                + "".join(tiles) + "</div>", unsafe_allow_html=True)
    st.caption(f'**{lad["text"]}** · Description of the last month, not a signal. '
               "Trend: Up = close above a rising 20-day average, Down = below a "
               "falling one, Mixed otherwise.")
