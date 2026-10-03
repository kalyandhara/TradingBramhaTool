"""Astro Timing — the first page extracted out of the monolith (B-87r).

B-87 shipped the ratchet and deliberately did NOT do this, for a stated reason:
page bodies live inline under `if current_page == "X":` at module scope, close
over module-level state, and have no page-level tests to catch a mistake. That
reasoning is still right, which is why this page went first — of the thirty
page blocks in `dashboard_app.py`, **Astro Timing is the only large one that
touches no module-level variable and no module-level helper at all** (measured
with `ast`, not grep: 703 lines, zero of each). It is the one extraction that
is a move rather than a refactor.

The body below is the block as it stood, dedented by one level and wrapped in
`render()`. Nothing else was changed — no reordering, no cleanup, no renaming.
A move and an edit in the same commit is a move you cannot verify.
"""
from __future__ import annotations

import csv
from datetime import date, datetime, timedelta, time      # noqa: F401

import pandas as pd
import plotly.graph_objects as go                          # noqa: F401
import streamlit as st

import astro_trading as at
import astrohora_loader as ahl


def render() -> None:
    """The Astro Timing page. Called by `pages.render` from dashboard_app."""
    st.subheader("Astrological Trading Timing")
    st.caption(
        "Lunar cycles, solar timing, and market intensity indicators. "
        "Based on Vedic astrology principles for optimal entry/exit timing."
    )

    # City selector + share button
    col_city, col_date, col_share = st.columns([2, 2, 1])
    with col_city:
        city = st.selectbox("Select Location", list(at.AstroIndicators.CITIES.keys()), index=0)
    with col_date:
        analysis_date = st.date_input("Analysis Date", value=date.today())
    with col_share:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        _gen_card = st.button("📷 Share Card", width="stretch",
                              help="Generate a weekly astro infographic and copy PNG to clipboard")

    ai = at.AstroIndicators(city=city)
    timing = ai.get_trading_timing(analysis_date)

    # Daily summary. AW-0: the lunar figures are None outside the reversal
    # calendar's coverage, and a date we cannot place must render as unplaced
    # rather than as a confident number — that is the whole point of the fix.
    _lun = timing['lunar_phase']
    _unknown = _lun.get('phase') == 'unknown' or _lun.get('cycle_day') is None
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Lunar Phase",
            "—" if _unknown else _lun['phase'].title(),
            "outside calendar coverage" if _unknown
            else f"{_lun['illumination']}% illuminated"
        )
    with col2:
        st.metric(
            "Market Intensity",
            "—" if timing['market_intensity'] is None
            else f"{timing['market_intensity']}/100",
            "Volatility indicator"
        )
    with col3:
        st.metric(
            "Cycle Day",
            "—" if _unknown else f"{_lun['cycle_day']:.1f}",
            "no lunation to measure against" if _unknown
            else f"of {_lun['cycle_length']:.1f}"
        )
    with col4:
        st.metric("Location", city, "")

    if _unknown:
        st.warning(
            f"No lunation covers {analysis_date}. The reversal calendar holds "
            "new/full moons for a fixed window; extend it with "
            "`py -3 tools/reversal_calendar.py build --years …` (needs `ephem`)."
        )
    elif _lun.get("source") == "reversal_calendar":
        st.caption(
            "Lunar figures read from the reversal-calendar DB (PyEphem-derived "
            "instants), not from a mean-cycle approximation."
        )

    # Solar timing
    st.subheader("Solar Timing (IST)")
    scol1, scol2, scol3, scol4 = st.columns(4)
    with scol1:
        st.metric("Sunrise", timing['solar_timing']['sunrise'])
    with scol2:
        st.metric("Sunset", timing['solar_timing']['sunset'])
    with scol3:
        st.metric("Optimal Entry", timing['solar_timing']['optimal_entry'], "15 min post-sunrise")
    with scol4:
        st.metric("Optimal Exit", timing['solar_timing']['optimal_exit'], "15 min pre-sunset")

    # Recommendations
    st.subheader("Trading Recommendations")
    for i, rec in enumerate(timing['recommendations'], 1):
        st.info(f"**{i}.** {rec}")

    # Weekly calendar
    st.subheader("Weekly Astro Calendar")
    today = date.today()
    weekly = ai.get_weekly_calendar(today, days=7)

    # Format for display
    display_cols = ['date', 'lunar_phase', 'illumination', 'market_intensity', 'sunrise', 'sunset']
    display_df = weekly[display_cols].copy()
    display_df.columns = ['Date', 'Lunar Phase', 'Illumination %', 'Market Intensity', 'Sunrise', 'Sunset']

    st.dataframe(display_df, width="stretch", hide_index=True)

    # ── Nakshatra Sector Forecast ──────────────────────────────────────────────
    st.subheader("Nakshatra Sector Forecast — 7-Day Forward")
    st.caption(
        "Moon's nakshatra (lunar mansion) for each trading day ahead. "
        "Each nakshatra rules specific commodities and NSE sectors — use as a "
        "directional bias, not an entry signal."
    )

    _nk_today = ai.get_nakshatra(analysis_date)
    _nk_df = pd.DataFrame()   # always defined; populated below if nakshatra succeeds

    if "error" in _nk_today:
        st.warning(f"Nakshatra engine: {_nk_today['error']}")
    else:
        # Today's nakshatra at a glance
        nk_c1, nk_c2, nk_c3, nk_c4 = st.columns(4)
        with nk_c1:
            st.metric("Today's Nakshatra", _nk_today["nakshatra"],
                      f"#{_nk_today['index']} of 27")
        with nk_c2:
            st.metric("Ruling Planet", _nk_today["planet"],
                      f"{_nk_today['pct']}% through")
        with nk_c3:
            st.metric("Sectors to Watch", " · ".join(_nk_today["sectors"][:2]),
                      _nk_today["sectors"][2] if len(_nk_today["sectors"]) > 2 else "")
        with nk_c4:
            st.metric("Moon Longitude (sid.)", f"{_nk_today['sidereal_lon']}°",
                      f"{_nk_today['deg_in']}° in nakshatra")

        st.info(f"**Commodity theme today:** {_nk_today['theme']}")

        # 7-day table
        _nk_df = ai.get_nakshatra_forecast(analysis_date, days=7)
        if isinstance(_nk_df, list):
            import pandas as _pd_nk
            _nk_df = _pd_nk.DataFrame(_nk_df)

        # Highlight today (first row)
        def _nk_row_style(row):
            if row.name == 0:
                return [f"background:rgba(74,222,128,0.12)" for _ in row]
            return ["" for _ in row]

        st.dataframe(
            _nk_df.style.apply(_nk_row_style, axis=1),
            width="stretch",
            hide_index=True,
        )

        # Sector heatmap — count how many days each sector appears
        from collections import Counter as _Counter
        _sector_days: _Counter = _Counter()
        for _, row in _nk_df.iterrows():
            for _s in row["Watch Sectors"].split(" / "):
                _sector_days[_s] += 1

        st.markdown("**Sector appearance frequency (next 7 days)**")
        _hm_cols = st.columns(min(len(_sector_days), 6))
        for _ci, (_sec, _cnt) in enumerate(sorted(_sector_days.items(), key=lambda x: -x[1])):
            with _hm_cols[_ci % len(_hm_cols)]:
                _pct_bar = int(_cnt / 7 * 100)
                st.markdown(
                    f'<div style="background:rgba(74,222,128,{_cnt/7:.2f});'
                    f'border-radius:8px;padding:8px 12px;margin:2px 0;'
                    f'font-size:13px;font-weight:600;">'
                    f'{_sec}<br>'
                    f'<span style="font-size:11px;font-weight:400;">{_cnt}/7 days</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── Jupiter Crash Signal ───────────────────────────────────────────────────
    st.subheader("Jupiter Crash Signal Monitor")
    st.caption(
        "Three-factor model: Jupiter in Ketu's nakshatra + Shashtashtak Yoga "
        "(6/8 axis) with malefics + Rahu-Ketu nodal influence. "
        "All 4 major Indian crashes (1992/2000/2008/2020) had all three active. "
        "No single factor alone predicts a crash."
    )

    _jp = ai.get_jupiter_position(analysis_date)

    if "error" in _jp:
        st.warning(f"Jupiter engine: {_jp['error']}")
    else:
        # ── Signal banner ──────────────────────────────────────────────────────
        _sig_colors = {
            "CRASH SIGNAL":  ("rgba(220,38,38,0.18)",  "#fca5a5", "🔴"),
            "ELEVATED RISK": ("rgba(234,88,12,0.18)",  "#fdba74", "🟠"),
            "WATCH":         ("rgba(234,179,8,0.15)",  "#fde047", "🟡"),
            "CLEAR":         ("rgba(74,222,128,0.12)", "#86efac", "🟢"),
        }
        _bg, _border_col, _icon = _sig_colors[_jp["signal"]]
        _factors_desc = []
        if _jp["is_ketu_nakshatra"]:
            _factors_desc.append(f"Jupiter in Ketu's nakshatra ({_jp['nakshatra']})")
        if _jp["shashtashtak_with"]:
            _factors_desc.append(f"Shashtashtak with {', '.join(_jp['shashtashtak_with'])}")
        if _jp["nodal_influence"]:
            _factors_desc.append(
                f"Rahu-Ketu nodal influence "
                f"(Rahu {_jp['rahu_arc']}° / Ketu {_jp['ketu_arc']}°)"
            )
        _factors_text = " · ".join(_factors_desc) if _factors_desc else "No active factors"

        st.markdown(
            f'<div style="background:{_bg};border:1px solid {_border_col};'
            f'border-radius:12px;padding:14px 18px;margin:8px 0;">'
            f'<span style="font-size:20px;">{_icon}</span> '
            f'<strong style="font-size:16px;">{_jp["signal"]}</strong> — '
            f'{_jp["factors_active"]}/3 factors active<br>'
            f'<span style="font-size:13px;opacity:0.85;">{_factors_text}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Jupiter position metrics ───────────────────────────────────────────
        jp_c1, jp_c2, jp_c3, jp_c4 = st.columns(4)
        with jp_c1:
            st.metric("Jupiter Sign", _jp["sign"].split("(")[0].strip(),
                      f"Sign #{_jp['sign_index']}")
        with jp_c2:
            _ketu_tag = " ⚠ Ketu's star" if _jp["is_ketu_nakshatra"] else ""
            st.metric("Jupiter Nakshatra", _jp["nakshatra"] + _ketu_tag,
                      f"Ruled by {_jp['nakshatra_planet']}")
        with jp_c3:
            _s6_8 = ", ".join(_jp["shashtashtak_with"]) if _jp["shashtashtak_with"] else "None"
            st.metric("Shashtashtak With", _s6_8, "6th/8th axis malefic")
        with jp_c4:
            st.metric("Jupiter Longitude", f"{_jp['sidereal_lon']}°",
                      "sidereal (Lahiri)")

        # ── Factor checklist ───────────────────────────────────────────────────
        _check = lambda ok: "✅" if ok else "⬜"
        st.markdown(
            f"**Crash signal factors:**  "
            f"{_check(_jp['is_ketu_nakshatra'])} Ketu nakshatra &nbsp;&nbsp;"
            f"{_check(_jp['shashtashtak_with'])} Shashtashtak w/ malefic &nbsp;&nbsp;"
            f"{_check(_jp['nodal_influence'])} Rahu-Ketu nodal influence"
        )

        # ── Historical context note ────────────────────────────────────────────
        with st.expander("Historical crash setups (reference)"):
            st.markdown(
                "| Year | Event | Jupiter Nakshatra | Key Combo | Outcome |\n"
                "|------|-------|-------------------|-----------|--------|\n"
                "| 1992 | Harshad Mehta crash | Magha (Ketu) | Shashtashtak Saturn+Sun; Rahu+Mars | Sensex −57%, 20m recovery |\n"
                "| 2000 | Dot-com bust | Ashwini (Ketu) | Conjunction Saturn; Rahu-Ketu axis | Nifty −53%, 34m recovery |\n"
                "| 2008 | Global financial crisis | Mula (Ketu) | Sun+Mars+Ketu aspect; 8th from Saturn | Nifty −64%, 71m recovery |\n"
                "| 2020 | Covid crash | Mula (Ketu) | Saturn+Sun+Mercury; eclipse; Ketu | Nifty −39%, fast recovery |\n"
                "| **Nov 2026** | **Prediction** | **Magha (Ketu)** | **Rahu-Ketu axis; 8th from Saturn** | **Major crash predicted** |\n"
                "\n"
                "*Exception rule:* Ketu nakshatra alone is NOT sufficient. "
                "1995 (+7%), 2003 (+20%), 2023 (+12%) were all bullish despite "
                "Jupiter in Ketu's star — because Shashtashtak and/or nodal influence was absent."
            )

    # ── India Degree-Matching Alerts ──────────────────────────────────────────
    st.subheader("India Chart — Degree-Matching Alerts (9:15 AM IST)")
    st.caption(
        "Transiting planets within ±2° of India's Independence Chart sensitive degrees "
        "(Aug 15, 1947). When a karaka planet hits these degrees it historically "
        "marks trend acceleration or reversal. Malefics (Saturn/Sun/Rahu/Mars) = bullish "
        "signal; Benefics (Jupiter/Moon/Mercury/Venus) = correction risk."
    )

    _orb_input = st.slider("Orb (degrees)", min_value=0.5, max_value=3.0,
                           value=2.0, step=0.5, key="india_orb")
    _alerts = ai.get_india_chart_alerts(analysis_date, orb=_orb_input)

    if _alerts and "error" in _alerts[0]:
        st.warning(f"India chart engine: {_alerts[0]['error']}")
    elif not _alerts:
        st.success(f"No planets within ±{_orb_input}° of any India chart sensitive degree today.")
    else:
        # Summary count strip
        _bull_alerts = [a for a in _alerts if a["bias"] == "bullish"]
        _bear_alerts = [a for a in _alerts if a["bias"] == "bearish"]
        _amb_alerts  = [a for a in _alerts if a["bias"] == "ambiguous"]

        ia_c1, ia_c2, ia_c3, ia_c4 = st.columns(4)
        with ia_c1:
            st.metric("Active Alerts", len(_alerts), f"within ±{_orb_input}°")
        with ia_c2:
            st.metric("Bullish Signals", len(_bull_alerts),
                      "Saturn/Sun/Rahu/Mars hitting India degrees")
        with ia_c3:
            st.metric("Bearish Signals", len(_bear_alerts),
                      "Jupiter/Moon/Mercury/Venus hitting India degrees")
        with ia_c4:
            st.metric("Ambiguous", len(_amb_alerts), "Ketu")

        # Net bias
        _net = len(_bull_alerts) - len(_bear_alerts)
        if _net > 0:
            _net_label = f"Net BULLISH (+{_net})"
            _net_color = "rgba(74,222,128,0.15)"
            _net_border = "#4ade80"
        elif _net < 0:
            _net_label = f"Net BEARISH ({_net})"
            _net_color = "rgba(220,38,38,0.15)"
            _net_border = "#f87171"
        else:
            _net_label = "Balanced (no edge)"
            _net_color = "rgba(234,179,8,0.12)"
            _net_border = "#fde047"

        st.markdown(
            f'<div style="background:{_net_color};border:1px solid {_net_border};'
            f'border-radius:8px;padding:10px 16px;margin:6px 0;">'
            f'<strong>{_net_label}</strong> — {len(_alerts)} degree matches active'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Alert cards
        _bias_icon = {"bullish": "🟢", "bearish": "🔴", "ambiguous": "🟡"}
        _bias_bg   = {
            "bullish":   "rgba(74,222,128,0.10)",
            "bearish":   "rgba(220,38,38,0.10)",
            "ambiguous": "rgba(234,179,8,0.10)",
        }
        _bias_border = {
            "bullish":   "rgba(74,222,128,0.4)",
            "bearish":   "rgba(220,38,38,0.4)",
            "ambiguous": "rgba(234,179,8,0.4)",
        }

        for _a in _alerts:
            _icon  = _bias_icon.get(_a["bias"], "⬜")
            _bg    = _bias_bg.get(_a["bias"], "transparent")
            _brd   = _bias_border.get(_a["bias"], "rgba(255,255,255,0.1)")
            _exact = " ✦ EXACT" if _a["exact"] else ""
            st.markdown(
                f'<div style="background:{_bg};border:1px solid {_brd};'
                f'border-radius:8px;padding:10px 16px;margin:4px 0;">'
                f'{_icon} <strong>{_a["planet"]}</strong> at '
                f'<strong>{_a["deg_in_sign"]:.1f}°</strong> {_a["sign"]} '
                f'→ matches India <strong>{_a["india_point"]} ({_a["india_deg"]}°)</strong> '
                f'<span style="opacity:0.7;">orb {_a["orb_actual"]}°{_exact}</span><br>'
                f'<span style="font-size:12px;opacity:0.75;">'
                f'Bias: {_a["bias"].upper()} &nbsp;|&nbsp; '
                f'Karaka: {_a["karaka"]}'
                f'</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # India chart degree reference (collapsed)
        with st.expander("India Independence Chart — sensitive degrees reference"):
            _ref_rows = [
                f"| {pt} | {deg}° | ±{_orb_input}° orb = {max(0,deg-_orb_input):.1f}°–{min(30,deg+_orb_input):.1f}° |"
                for pt, deg in ai.INDIA_CHART_DEGREES.items()
            ]
            st.markdown(
                "| Chart Point | Degree | Active Window |\n"
                "|-------------|--------|---------------|\n" +
                "\n".join(_ref_rows)
            )
            st.caption(
                "India Independence Chart: Aug 15, 1947, 12:00 AM, New Delhi. "
                "D1 = Rashi chart. D9 = Navamsa chart. "
                "Degree matching checks the transiting planet's position within its current "
                "sign (lon mod 30°) against these fixed reference degrees."
            )

    # ── Weekly Astro Infographic Card ─────────────────────────────────────────
    if _gen_card:
        try:
            from PIL import Image as _PILImage, ImageDraw as _PILDraw, ImageFont as _PILFont
        except ImportError:
            st.error("Pillow is not installed. Run `pip install Pillow` and restart the app.")
            _PILImage = None
        import io as _io
        import base64 as _b64
        if _PILImage is None:
            pass
        else:
            # ── palette ───────────────────────────────────────────────────────
            _C = {
                "bg":    (15,  10,  6),
                "panel": (28,  20,  16),
                "amber": (234, 88,  12),
                "green": (74,  222, 128),
                "red":   (239, 68,  68),
                "yellow":(253, 224, 71),
                "text":  (255, 245, 235),
                "muted": (168, 133, 106),
                "white": (255, 255, 255),
                "card_b":(38,  28,  20),
            }

            def _font(size, bold=False):
                try:
                    return _PILFont.truetype("arialbd.ttf" if bold else "arial.ttf", size)
                except OSError:
                    return _PILFont.load_default()

            W, H = 1080, 1350
            img = _PILImage.new("RGB", (W, H), _C["bg"])
            dr  = _PILDraw.Draw(img)

            def _rect(x0, y0, x1, y1, fill, r=12):
                dr.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill)

            def _txt(x, y, text, fnt, fill, anchor="la"):
                dr.text((x, y), str(text), font=fnt, fill=fill, anchor=anchor)

            # ── header ────────────────────────────────────────────────────────
            _rect(0, 0, W, 120, _C["amber"], r=0)
            _txt(40,      30, "Trading Bramha",          _font(38, True), _C["white"])
            _txt(40,      76, "ASTRO WEEKLY SNAPSHOT",   _font(18),       _C["white"])
            _txt(W - 40,  30, analysis_date.strftime("%d %b %Y"),
                 _font(28, True), _C["white"], anchor="ra")
            _txt(W - 40,  76, analysis_date.strftime("Week of %a %d %b"),
                 _font(16), _C["white"], anchor="ra")

            # ── running y cursor ───────────────────────────────────────────────
            _cy = [140]

            def _section_lbl(title):
                _txt(40, _cy[0], title.upper(), _font(13), _C["muted"])
                _cy[0] += 28

            def _open_panel(h):
                y0 = _cy[0]
                _rect(30, y0, W - 30, y0 + h, _C["panel"])
                return 30 + 20, y0 + 20

            def _close_panel(h):
                _cy[0] += h + 16

            # ── Moon Nakshatra ─────────────────────────────────────────────────
            _section_lbl("Moon Nakshatra Today")
            if "error" not in _nk_today:
                _ph = 160
                _px, _py = _open_panel(_ph)
                _txt(_px, _py,      _nk_today["nakshatra"],          _font(36, True), _C["text"])
                _txt(_px, _py + 44, f"Ruled by {_nk_today['planet']}  •  #{_nk_today['index']} of 27",
                     _font(18), _C["muted"])
                _txt(_px, _py + 72, "Sectors: " + " / ".join(_nk_today["sectors"]),
                     _font(16), _C["green"])
                _txt(_px, _py + 96, _nk_today["theme"][:70], _font(14), _C["muted"])
                _bw = W - 30 - 20 - _px
                _rect(_px, _py + 122, _px + _bw, _py + 132, _C["card_b"], r=4)
                _filled = max(4, int(_bw * _nk_today["pct"] / 100))
                _rect(_px, _py + 122, _px + _filled, _py + 132, _C["amber"], r=4)
                _txt(_px + _bw + 6, _py + 122, f"{_nk_today['pct']}%", _font(12), _C["muted"])
                _close_panel(_ph)
            else:
                _cy[0] += 60

            # ── Jupiter Crash Signal ───────────────────────────────────────────
            _section_lbl("Jupiter Crash Signal")
            if "error" not in _jp:
                _sig_col = {"CRASH SIGNAL": _C["red"], "ELEVATED RISK": _C["amber"],
                            "WATCH": _C["yellow"], "CLEAR": _C["green"]}.get(_jp["signal"], _C["muted"])
                _ph = 130
                _px, _py = _open_panel(_ph)
                _txt(_px, _py,      f"{_jp['signal']}  —  {_jp['factors_active']}/3 factors",
                     _font(30, True), _sig_col)
                _txt(_px, _py + 44, f"Jupiter in {_jp['nakshatra']} ({_jp['sign'].split('(')[0].strip()})",
                     _font(18), _C["text"])
                _active_parts = []
                if _jp["is_ketu_nakshatra"]:  _active_parts.append("Ketu nakshatra")
                if _jp["shashtashtak_with"]:  _active_parts.append(f"Shashtashtak w/ {', '.join(_jp['shashtashtak_with'])}")
                if _jp["nodal_influence"]:    _active_parts.append("Rahu-Ketu nodal")
                _txt(_px, _py + 70, "  ".join(_active_parts) or "No factors active",
                     _font(14), _C["muted"])
                _txt(_px, _py + 96, "Red flag: Nov 2026 full crash signal — mirrors 1992 & 2008",
                     _font(13), _C["red"])
                _close_panel(_ph)
            else:
                _cy[0] += 40

            # ── India Chart Alerts ─────────────────────────────────────────────
            _section_lbl("India Chart — Top Degree Alerts (9:15 AM IST)")
            _top_al = [a for a in _alerts if "error" not in a][:5]
            if _top_al:
                _bull_n = sum(1 for a in _top_al if a["bias"] == "bullish")
                _bear_n = sum(1 for a in _top_al if a["bias"] == "bearish")
                _net_t  = (f"Net BULLISH +{_bull_n - _bear_n}" if _bull_n > _bear_n else
                           f"Net BEARISH {_bull_n - _bear_n}"  if _bear_n > _bull_n else "Balanced")
                _net_c  = _C["green"] if _bull_n > _bear_n else _C["red"] if _bear_n > _bull_n else _C["yellow"]
                _ph = 36 + len(_top_al) * 24 + 20
                _px, _py = _open_panel(_ph)
                _txt(_px, _py, _net_t, _font(22, True), _net_c)
                for _i, _a in enumerate(_top_al):
                    _ac = (_C["green"] if _a["bias"] == "bullish"
                           else _C["red"] if _a["bias"] == "bearish" else _C["yellow"])
                    _line = (f"{_a['planet']:8s}  {_a['deg_in_sign']:4.1f}°  "
                             f"→ {_a['india_point']:12s} ({_a['india_deg']}°)  orb {_a['orb_actual']}°")
                    _txt(_px, _py + 36 + _i * 24, _line, _font(15), _ac)
                _close_panel(_ph)
            else:
                _cy[0] += 40

            # ── 7-Day Nakshatra Forecast ───────────────────────────────────────
            _section_lbl("7-Day Nakshatra Forecast")
            _nk_df_c = (_nk_df if not isinstance(_nk_df, list)
                        else pd.DataFrame(_nk_df))
            if not _nk_df_c.empty:
                _row_h = 38
                _col_ratios = [0.18, 0.28, 0.16, 0.38]
                _ph = 26 + len(_nk_df_c) * _row_h + 10
                _px, _py = _open_panel(_ph)
                _col_w = [(W - 30 - 20 - _px) * r for r in _col_ratios]
                _hdrs  = ["Date", "Nakshatra", "Planet", "Sectors"]
                _hx = _px
                for _h, _cw in zip(_hdrs, _col_w):
                    _txt(_hx, _py, _h, _font(13), _C["muted"])
                    _hx += _cw
                for _ri, (_, _row) in enumerate(_nk_df_c.iterrows()):
                    _ry = _py + 26 + _ri * _row_h
                    if _ri == 0:
                        _rect(_px - 8, _ry - 4, W - 30 - 20 + 8, _ry + _row_h - 6, (38, 55, 38), r=6)
                    _cx2 = _px
                    _cells = [_row.get("Date", ""), _row.get("Nakshatra", ""),
                              _row.get("Ruling Planet", ""), str(_row.get("Watch Sectors", ""))[:35]]
                    for _cell, _cw in zip(_cells, _col_w):
                        _txt(_cx2, _ry, str(_cell), _font(14, bold=(_ri == 0)),
                             _C["green"] if _ri == 0 else _C["text"])
                        _cx2 += _cw
                _close_panel(_ph)
            else:
                _cy[0] += 40

            # ── footer ────────────────────────────────────────────────────────
            _rect(0, H - 60, W, H, _C["panel"], r=0)
            _txt(W // 2, H - 38,
                 "Trading Bramha  •  Astro Timing Dashboard  •  For reference only",
                 _font(14), _C["muted"], anchor="mm")
            _txt(W // 2, H - 18, "Context, not signal. Always verify with price action.",
                 _font(12), _C["muted"], anchor="mm")

            # ── export ────────────────────────────────────────────────────────
            _buf = _io.BytesIO()
            img.save(_buf, format="PNG", optimize=True)
            _png_bytes = _buf.getvalue()
            _b64_str   = _b64.b64encode(_png_bytes).decode()

            st.image(img, caption="Weekly Astro Card — copy or download below",
                     width=540)

            st.download_button(
                label="⬇ Download PNG",
                data=_png_bytes,
                file_name=f"trading_bramha_astro_{analysis_date.strftime('%Y%m%d')}.png",
                mime="image/png",
                width="content",
            )

            st.iframe(f"""
            <button onclick="copyCard()" style="
                background:#ea580c;color:#fff;border:none;border-radius:8px;
                padding:8px 20px;font-size:14px;font-weight:700;cursor:pointer;">
                \U0001f4cb Copy PNG to Clipboard
            </button>
            <span id="cs" style="margin-left:12px;font-size:13px;"></span>
            <script>
            async function copyCard() {{
                try {{
                    const res  = await fetch("data:image/png;base64,{_b64_str}");
                    const blob = await res.blob();
                    await navigator.clipboard.write([new ClipboardItem({{"image/png": blob}})]);
                    const s = document.getElementById("cs");
                    s.style.color = "#4ade80"; s.textContent = "Copied!";
                    setTimeout(() => s.textContent = "", 3000);
                }} catch(e) {{
                    const s = document.getElementById("cs");
                    s.style.color = "#ef4444";
                    s.textContent = "Copy failed — use Download (" + e.message + ")";
                }}
            }}
            </script>
            """, height=56)

    # Lunar phase chart
    st.subheader("Lunar Phase Progression")

    dates_list = []
    illumination_list = []
    intensity_list = []

    for i in range(30):
        d = date.today() + timedelta(days=i)
        dates_list.append(d.strftime('%m-%d'))
        lunar = ai.get_lunar_phase(d)
        illumination_list.append(lunar['illumination'])
        timing_temp = ai.get_trading_timing(d)
        intensity_list.append(timing_temp['market_intensity'])

    fig_astro = go.Figure()
    fig_astro.add_trace(go.Scatter(
        x=dates_list,
        y=illumination_list,
        mode='lines+markers',
        name='Lunar Illumination %',
        line=dict(color='gold', width=2),
        yaxis='y1'
    ))
    fig_astro.add_trace(go.Scatter(
        x=dates_list,
        y=intensity_list,
        mode='lines+markers',
        name='Market Intensity',
        line=dict(color='crimson', width=2),
        yaxis='y2'
    ))

    fig_astro.update_layout(
        title="30-Day Lunar & Market Intensity Forecast",
        hovermode='x unified',
        xaxis_title="Date",
        yaxis=dict(title="Lunar Illumination %", side='left'),
        yaxis2=dict(title="Market Intensity", side='right', overlaying='y'),
        height=500
    )

    st.plotly_chart(fig_astro, width="stretch")

    # AstroHora integration section
    st.subheader("AstroHora Chart Data Integration")
    st.caption("Load birth charts or event data from AstroHora for deeper astrological analysis.")

    upload_col, manual_col = st.columns(2)

    with upload_col:
        st.write("**Upload AstroHora Data**")
        uploaded_file = st.file_uploader(
            "Load CSV/Excel export from AstroHora",
            type=['csv', 'xlsx'],
            key='astro_upload'
        )

        if uploaded_file:
            aha = ahl.AstroHoraData()
            try:
                if uploaded_file.name.endswith('.csv'):
                    import io
                    stringio = io.StringIO(uploaded_file.getvalue().decode("utf8"))
                    csv_reader = csv.DictReader(stringio)
                    for row in csv_reader:
                        aha._parse_row(row)
                else:
                    # Excel handling
                    import io
                    df = pd.read_excel(uploaded_file)
                    aha._parse_astro_dataframe(df)

                st.success("✓ Chart data loaded")

                summary = aha.get_summary()
                st.json(summary, expanded=False)

            except Exception as e:
                st.error(f"Error loading file: {e}")

    with manual_col:
        st.write("**Or Enter Chart Details**")
        chart_type = st.selectbox("Chart Type", ["natal", "prashna"], key='chart_type_select')
        birth_location = st.text_input("Location (e.g., Mumbai, India)", value="Mumbai, India")

        if st.button("Load Example Chart", key='example_chart_btn'):
            from datetime import time

            aha = ahl.AstroHoraData()
            example_chart = {
                'chart_type': 'natal',
                'birth_date': date(1990, 6, 15),
                'birth_time': time(14, 30),
                'location': birth_location,
                'chart_data': {
                    'Sun': {'sign': 'Gemini', 'longitude': 84.5, 'house': '11'},
                    'Moon': {'sign': 'Libra', 'longitude': 207.2, 'house': '3'},
                    'Mars': {'sign': 'Leo', 'longitude': 123.8, 'house': '1'},
                    'Mercury': {'sign': 'Gemini', 'longitude': 91.3, 'house': '11'},
                    'Jupiter': {'sign': 'Cancer', 'longitude': 99.5, 'house': '12'},
                    'Venus': {'sign': 'Cancer', 'longitude': 108.7, 'house': '12'},
                    'Saturn': {'sign': 'Capricorn', 'longitude': 286.4, 'house': '6'},
                }
            }
            aha.load_from_dict(example_chart)

            col_a, col_b, col_c = st.columns(3)

            with col_a:
                st.write("**Planetary Positions**")
                for planet, data in aha.get_planetary_positions().items():
                    st.text(f"{planet}: {data['sign']} {data['degree']}°")

            with col_b:
                st.write("**Strong Planets**")
                for planet, status in aha.get_strong_planets():
                    st.text(f"{planet}: {status}")

            with col_c:
                st.write("**Major Aspects**")
                for aspect in aha.get_aspectarian():
                    st.text(f"{aspect['planet1']} {aspect['aspect']} {aspect['planet2']}")

            st.write("**Dasha Analysis**")
            dasha = aha.get_vimshottari_dasha(date(1990, 6, 15))
            dasha_col1, dasha_col2, dasha_col3 = st.columns(3)
            with dasha_col1:
                st.metric("Current Dasha", dasha['current_dasha'])
            with dasha_col2:
                st.metric("Years Remaining", f"{dasha['years_remaining']:.1f}")
            with dasha_col3:
                st.metric("Period Length", f"{dasha['period_years']} yrs")
