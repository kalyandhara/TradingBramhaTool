"""Other Screeners page — extracted from dashboard_app.py (B-87r)."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

import browser_cookie_helper as bch
import multibagger_candidates as mb
import nse_shareholding_fetch as nse
import out_paths as _out
import promoter_profit_surprise as pps
import screener_pipeline as sp
import screener_scraper as ss
import sector_rotation as secrot
import sector_rotation_trail as secrot_trail


def render() -> None:
    st.subheader("Other Screeners")

    choice = st.selectbox(
        "Screener",
        ["Multibagger Candidates", "GARP / Promoter-Profit Surprise",
         "NSE Shareholding (Free, no login)", "Custom Screener.in Query"],
    )

    SESSION_BACKED = {
        "Multibagger Candidates": (mb, mb.QUERY),
        "GARP / Promoter-Profit Surprise": (pps, pps.QUERY),
        "Custom Screener.in Query": (ss, ss.DEFAULT_QUERY),
    }

    if choice in SESSION_BACKED:
        module, default_query = SESSION_BACKED[choice]
        sessionid, browser = bch.get_screener_sessionid()
        if sessionid:
            st.caption(f"Using screener.in session from local browser ({browser}).")
        else:
            st.warning(
                "No screener.in `sessionid` cookie found in your local browsers "
                "(Chrome / Edge / Brave / Firefox). Log into screener.in in your "
                "default browser once, then re-run."
            )
        query = st.text_area("Query", value=default_query, height=120)

        if st.button("Run", type="primary"):
            if not sessionid:
                st.warning("No local browser cookie available — cannot query screener.in.")
            else:
                try:
                    with st.spinner("Querying screener.in..."):
                        df = module.build_dataset(sessionid, query)
                except Exception as exc:
                    st.error(f"Run failed: {exc}")
                    df = None
                if df is not None:
                    if df.empty:
                        st.warning("Query returned no rows.")
                    else:
                        st.session_state["other_screener_df"] = df
                        st.session_state["other_screener_kind"] = choice
                        st.success(f"Fetched {len(df)} rows.")

    else:  # NSE Shareholding — free, no session needed
        top200 = st.checkbox("Use Top 200 by traded value (Bhavcopy)", value=True)
        manual_syms = ""
        if not top200:
            manual_syms = st.text_area("Symbols (comma or newline separated)")

        if st.button("Run", type="primary"):
            if top200:
                with st.spinner("Fetching Bhavcopy top 200..."):
                    symbols = sp.fetch_bhavcopy_top_volume()
            else:
                symbols = [s.strip().upper() for s in manual_syms.replace(",", "\n").splitlines() if s.strip()]
            if not symbols:
                st.warning("No symbols to process.")
            else:
                df = None
                try:
                    with st.spinner(f"Fetching shareholding data for {len(symbols)} symbols..."):
                        df = nse.build_dataset(symbols)
                except RuntimeError as exc:
                    st.error(str(exc))

                if df is not None:
                    if df.empty:
                        st.warning("No data fetched.")
                    else:
                        st.session_state["other_screener_df"] = df
                        st.session_state["other_screener_kind"] = choice
                        st.success(f"Fetched {len(df)} rows.")

    other_df = st.session_state.get("other_screener_df")
    other_kind = st.session_state.get("other_screener_kind")
    if other_df is not None and other_kind == choice:
        st.dataframe(other_df, width="stretch", hide_index=True)
        st.download_button(
            "Download CSV", data=other_df.to_csv(index=False).encode("utf-8"),
            file_name=f"{choice.lower().replace(' ', '_')}_{date.today():%Y%m%d}.csv",
            mime="text/csv",
        )

        can_chain = other_kind in SESSION_BACKED and "Industry" in other_df.columns
        if can_chain:
            st.divider()
            st.caption(
                "Pipeline this result into Sector Rotation analysis "
                "(requires Industry + FII-holding columns, present in screener.in-backed results)."
            )
            if st.button("Pipeline → Sector Rotation"):
                export_path = _out.out_path(
                    f"screener_export_{date.today():%Y%m%d}.csv")
                other_df.to_csv(export_path, index=False)
                try:
                    with st.spinner("Running sector_rotation + sector_rotation_trail..."):
                        secrot.run(export_path)
                        secrot_trail.run(export_path)
                except Exception as exc:
                    st.error(f"Sector rotation pipeline failed: {exc}")
                else:
                    date_str = date.today().strftime("%Y%m%d")
                    xlsx_path = _out.out_path(f"sector_rotation_{date_str}.xlsx")
                    html_path = _out.out_path(
                        f"sector_rotation_orbit_{date_str}.html")
                    if xlsx_path.exists():
                        st.dataframe(pd.read_excel(xlsx_path), width="stretch")
                    if html_path.exists():
                        st.iframe(
                            html_path.read_text(encoding="utf-8"), height=700
                        )
