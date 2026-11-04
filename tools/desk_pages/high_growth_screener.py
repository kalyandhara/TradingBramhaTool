"""High-Growth Screener page - free yfinance fundamentals, no screener.in login.

Reads the snapshot built by growth_screen.py (scheduled job "growth_snapshot",
or the Refresh button here). Sliders filter the snapshot instantly.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import growth_screen as gs
import ui_tables as uit


def render() -> None:
    st.subheader("High-Growth Screener — Sustained Growth + Quality Gates")
    st.caption(
        "Fundamental screen on free yfinance statements — no screener.in login. "
        "Sales/profit CAGR (5Y when Yahoo has 5 years, otherwise 3Y — the Basis column "
        "says which), a YoY quarterly-profit kicker, gated by ROE/ROCE/OPM. Data comes "
        "from a snapshot refreshed by the scheduled job; sliders filter it instantly. "
        "Not backtested — a reading list, not an edge claim."
    )

    snap = gs.load_snapshot()
    hg_left, hg_main = st.columns([1, 3])

    with hg_left:
        st.markdown("**Data snapshot**")
        age = gs.snapshot_age_days(snap)
        if snap:
            st.caption(f"✅ {snap['derived']}/{snap['scanned']} names · {snap['universe']} · "
                       f"built {snap['built_at']} ({age:.1f} days ago)")
        else:
            st.caption("⚠️ No snapshot yet — click Refresh below (≈5–10 min for Nifty 500), "
                       "or enable the 'Growth Snapshot' job in Scheduler Hub.")
        uni = st.selectbox("Universe", list(gs.UNIVERSES), key="hg_universe",
                           index=list(gs.UNIVERSES).index((snap or {}).get("universe", "nifty500")))
        if st.button("⟳ Refresh from yfinance", key="hg_refresh"):
            bar = st.progress(0.0, text="Starting…")
            snap = gs.refresh(uni, progress_cb=lambda d, t, s: bar.progress(
                d / t, text=f"{d}/{t} · {s}"))
            bar.empty()
            st.success(f"Snapshot rebuilt: {snap['derived']}/{snap['scanned']} names.")

        st.divider()
        st.markdown("**Growth & Quality Thresholds**")
        th = gs.Thresholds(
            min_sales_growth=st.slider("Min Sales Growth % (CAGR)", 0, 50, 15, key="hg_sales5y"),
            min_profit_growth=st.slider("Min Profit Growth % (CAGR)", 0, 80, 15, key="hg_profit5y"),
            min_yoy_qtr_profit=st.slider("Min YoY Qtr Profit Growth %", -20, 100, 15, step=5,
                                         key="hg_yoyq"),
            min_roe=st.slider("Min ROE %", 0, 40, 15, key="hg_roe"),
            min_roce=st.slider("Min ROCE %", 0, 40, 15, key="hg_roce"),
            min_opm=st.slider("Min OPM %", 0, 50, 10, key="hg_opm"),
        )
        max_unk = st.slider("Allow missing fields (Yahoo gaps)", 0, 3, 0, key="hg_unk",
                            help="Banks/NBFCs usually have no OPM/ROCE on Yahoo. "
                                 "Missing is never counted as a pass or a fail.")

    with hg_main:
        if not snap:
            st.info("Build the snapshot first (Refresh on the left).")
            return
        hits = gs.screen(snap["rows"], th, max_unknowns=max_unk)
        if not hits:
            st.info("No stocks pass these thresholds. Loosen a slider or allow missing fields.")
            return
        df = pd.DataFrame(hits)
        df["Chart"] = df["symbol"].apply(lambda s: f"http://localhost:5001/?symbol={s}.NS&tf=1d")
        df["Analyze"] = df["symbol"].map(uit.analyze_url)
        df["Missing"] = df["states"].apply(
            lambda s: ", ".join(k for k, v in s.items() if v == gs.UNKNOWN) or "")
        df = df.rename(columns={
            "symbol": "Symbol", "name": "Name", "industry": "Industry", "price": "Price",
            "sales_growth": "Sales Gr %", "profit_growth": "Profit Gr %",
            "growth_basis": "Basis", "yoy_qtr_profit": "YoY Qtr Profit %",
            "yoy_qtr_period": "Qtr", "roe": "ROE %", "roce": "ROCE %", "opm": "OPM %",
            "pe": "P/E"})
        keep = ["Chart", "Analyze", "Symbol", "Name", "Industry", "Price", "Sales Gr %",
                "Profit Gr %", "Basis", "YoY Qtr Profit %", "Qtr", "ROE %", "ROCE %",
                "OPM %", "P/E", "Missing"]
        keep = [c for c in keep if c in df.columns]
        st.caption(f"{len(df)} stocks passed · sorted by profit growth · "
                   f"snapshot {snap['built_at']}")
        st.dataframe(
            df[keep].round(1), width="stretch", hide_index=True,
            column_config={
                "Chart": st.column_config.LinkColumn("Chart", display_text="Open Chart",
                                                     width="small"),
                "Analyze": uit.analyze_colcfg(),
            },
        )
        st.caption("Basis 3Y = Yahoo had fewer than 5 annual statements, so the 3-year CAGR "
                   "is used. 'Missing' lists fields Yahoo didn't report for that stock.")
