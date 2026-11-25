"""Market Health page — breadth under the 200 EMA per index + a context score.

Engine: tools/market_breadth_score.py. Plan:
docs/superpowers/plans/2026-11-22-market-health-score.md

The composite's weights are the owner's priors, not measured. The page says so
next to the number, every time.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import market_breadth_score as mbs


@st.cache_data(ttl=3 * 3600, show_spinner=False)
def _load(as_of: str) -> dict:
    """One batched NIFTY 500 download + index/VIX/participant-OI. Keyed on IST date."""
    groups = mbs.index_groups()
    frames = mbs.fetch_history(groups.get("NIFTY 500", []))
    nifty, vix = mbs.fetch_index_frames()
    fii, fii_d = mbs.fetch_fii_long_share()
    out = mbs.build(frames, groups, nifty, vix, fii, fii_d)
    out["as_of"] = as_of
    out["history_names"] = len(frames)
    return out


def _rows_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows).rename(columns={
        "index": "Index / group", "members": "Members", "measured": "With 200+ bars",
        "above": "Above 200 EMA", "below": "Below 200 EMA",
        "pct_below": "% below", "pct_above": "% above", "no_data": "No data"})
    return df[["Index / group", "Members", "Below 200 EMA", "% below",
               "Above 200 EMA", "% above", "No data"]]


def render() -> None:
    st.subheader("Market Health — breadth under the 200 EMA + context score")
    st.caption("Context, not a signal. The composite uses the owner's chosen weights "
               "(Trend 30 · Breadth 25 · Volume 20 · Volatility 15 · Flows 10); they "
               "have not been measured or backtested.")
    as_of = mbs.ist_today().isoformat()
    if st.button("↻ Refresh", key="mhs_refresh"):
        _load.clear()
    with st.spinner("Loading NIFTY 500 history (one batched download, ~10–20s)…"):
        data = _load(as_of)

    comp = data["composite"]
    c1, c2 = st.columns([1, 3])
    with c1:
        st.metric("Market health (context)",
                  "—" if comp["score"] is None else f"{comp['score']:.0f} / 100",
                  help="Weighted mean of the pillars that could be read.")
    with c2:
        st.markdown(f"**{comp['read']}**")
        st.caption(f"IST date {data['as_of']} · {data['history_names']} NIFTY 500 names "
                   "with price history.")

    st.markdown("#### Pillars")
    pr = []
    for p in data["pillars"]:
        contrib = None if p["score"] is None else p["score"] * p["weight"] / 100
        pr.append({"Pillar": p["label"], "Weight %": p["weight"],
                   "Sub-score": p["score"], "Weighted pts": contrib,
                   "Read": p["read"]})
    st.dataframe(pd.DataFrame(pr), hide_index=True, use_container_width=True,
                 column_config={"Sub-score": st.column_config.ProgressColumn(
                     "Sub-score", min_value=0, max_value=100, format="%.0f"),
                     "Weighted pts": st.column_config.NumberColumn(format="%.1f")})
    with st.expander("Pillar inputs"):
        for p in data["pillars"]:
            st.markdown(f"**{p['label']}** ({p['weight']}%)")
            st.json(p["inputs"] or {"status": "not assessed"}, expanded=False)

    st.markdown("#### Breadth under each index — 200-day EMA")
    st.caption("Sector rows are NSE macro-sector groups inside NIFTY 500, not the "
               "official sector indices. 'No data' = fewer than 200 daily bars.")
    st.dataframe(_rows_df(data["rows"]), hide_index=True, use_container_width=True,
                 column_config={"% below": st.column_config.ProgressColumn(
                     "% below", min_value=0, max_value=100, format="%.1f%%"),
                     "% above": st.column_config.NumberColumn(format="%.1f%%")})
