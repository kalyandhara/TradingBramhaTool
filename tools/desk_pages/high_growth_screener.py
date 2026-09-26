"""High-Growth Screener page — extracted from dashboard_app.py (B-87r)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import browser_cookie_helper as bch
import screener_scraper as ss
import ui_tables as uit


def render() -> None:
    st.subheader("High-Growth Screener — Sustained Growth + Quality Gates")
    st.caption(
        "Pure fundamental screen against screener.in — sustained 5-year sales/profit growth "
        "gated by ROE/ROCE/OPM quality plus a YoY quarterly-profit acceleration kicker "
        "(screener.in has no analyst-consensus 'profit surprise' field; YoY qtr profit growth "
        "is the closest real proxy). No technical filters, no RS/exhaustion/validation "
        "columns — those live on the Scanner Hub cards; this page is fundamental-only."
    )

    hg_left, hg_main = st.columns([1, 3])

    with hg_left:
        st.markdown("**screener.in Session**")
        hg_cookie, hg_browser = bch.get_screener_sessionid()
        if hg_cookie:
            st.session_state["pb_screener_cookie"] = hg_cookie
            st.caption(f"✅ Using screener.in session from local browser ({hg_browser}).")
        else:
            st.caption(
                "⚠️ No screener.in `sessionid` cookie found in your local browsers. "
                "Log into screener.in in your default browser once, then re-run."
            )

        st.divider()
        st.markdown("**Growth & Quality Thresholds**")
        hg_sales5y = st.slider("Min 5Y Sales Growth %", 0, 50, 15, step=1, key="hg_sales5y")
        hg_profit5y = st.slider("Min 5Y Profit Growth %", 0, 80, 15, step=1, key="hg_profit5y")
        hg_yoyq = st.slider("Min YoY Qtr Profit Growth % (surprise proxy)", -20, 100, 15,
                             step=5, key="hg_yoyq")
        hg_roe = st.slider("Min ROE %", 0, 40, 15, step=1, key="hg_roe")
        hg_roce = st.slider("Min ROCE %", 0, 40, 15, step=1, key="hg_roce")
        hg_opm = st.slider("Min OPM %", 0, 50, 10, step=1, key="hg_opm")

        st.divider()
        if st.button("▶ Run High-Growth Screen", type="primary", key="hg_run"):
            cookie = (hg_cookie or "").strip() or st.session_state.get("pb_screener_cookie", "").strip()
            if not cookie:
                st.error("No screener.in `sessionid` cookie found — log into screener.in "
                         "in your default browser, then re-run.")
            else:
                with st.spinner("Querying screener.in…"):
                    try:
                        hg_df = ss.fetch_high_growth_stocks(
                            cookie, min_sales_growth_5y=hg_sales5y, min_profit_growth_5y=hg_profit5y,
                            min_yoy_qtr_profit_growth=hg_yoyq, min_roe=hg_roe, min_roce=hg_roce,
                            min_opm=hg_opm,
                        )
                    except Exception as exc:
                        hg_df = None
                        st.error(f"screener.in fetch failed: {exc}")

                if hg_df is not None:
                    if hg_df.empty:
                        st.session_state["hg_results"] = []
                    else:
                        results = []
                        for _, row in hg_df.iterrows():
                            sym = str(row.get("_slug") or row.get("Name", "")).strip().upper()
                            if not sym:
                                continue
                            rec = {"symbol": sym}
                            for col in hg_df.columns:
                                if col not in ("Name", "_slug"):
                                    rec[col] = row.get(col)
                            results.append(rec)

                        def _sort_key(r):
                            for col in ("Profit growth 5Years", "Sales growth 5Years",
                                        "YOY Quarterly profit growth"):
                                v = pd.to_numeric(r.get(col), errors="coerce")
                                if pd.notna(v):
                                    return -float(v)
                            return 0.0
                        st.session_state["hg_results"] = sorted(results, key=_sort_key)

    with hg_main:
        hg_results = st.session_state.get("hg_results")
        if hg_results is None:
            st.info(
                "Adjust thresholds and click **Run High-Growth Screen**. The screener.in "
                "session is read automatically from your local browser — just stay logged "
                "into screener.in there."
            )
        elif not hg_results:
            st.info(
                "screener.in returned 0 rows for these thresholds. With nominal "
                "settings that usually means the sessionid cookie has expired "
                "(re-paste it and rerun) rather than genuinely no matches — an "
                "expired cookie now raises an error instead, so if you're seeing "
                "this after a clean run, the thresholds really matched nothing."
            )
        else:
            df_hg_res = pd.DataFrame(hg_results)
            df_hg_res["Chart"] = df_hg_res["symbol"].apply(
                lambda s: f"http://localhost:5001/?symbol={s}.NS&tf=1d"
            )
            df_hg_res["Analyze"] = df_hg_res["symbol"].map(uit.analyze_url)

            rename_map = {
                "symbol": "Symbol",
                "Current Price": "Price",
                "Sales growth 5Years": "Sales Gr 5Y %",
                "Profit growth 5Years": "Profit Gr 5Y %",
                "YOY Quarterly profit growth": "YoY Qtr Profit %",
                "Return on equity": "ROE %",
                "Return on capital employed": "ROCE %",
                "OPM": "OPM %",
            }
            df_hg_res = df_hg_res.rename(
                columns={k: v for k, v in rename_map.items() if k in df_hg_res.columns}
            )

            keep_hg = ["Chart", "Analyze", "Symbol", "Price", "Sales Gr 5Y %", "Profit Gr 5Y %",
                       "YoY Qtr Profit %", "ROE %", "ROCE %", "OPM %"]
            keep_hg = [c for c in keep_hg if c in df_hg_res.columns]

            st.caption(
                f"{len(df_hg_res)} stocks passed the growth/quality gate · "
                "sorted by 5Y profit growth"
            )
            col_cfg_hg = {
                "Chart": st.column_config.LinkColumn(
                    "Chart", display_text="Open Chart", width="small",
                ),
                "Analyze": uit.analyze_colcfg(),
            }
            st.dataframe(
                df_hg_res[keep_hg], use_container_width=True, hide_index=True,
                column_config=col_cfg_hg,
            )
            st.caption(
                "Columns showing blank came back missing from screener.in's response for that "
                "field (its raw-query columns can vary); re-check that stock on screener.in directly."
            )
