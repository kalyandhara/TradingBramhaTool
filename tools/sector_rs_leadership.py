#!/usr/bin/env python3
"""sector_rs_leadership.py — "Relative-strength leadership" (ScreeningMantis Sector breadth).

Average RS rank by group, today (T-0) vs 5 sessions ago (T-5), sorted by T-0.

Each stock's rank is `rs_walk.walk_grid`'s universe-wide percentile (IBD-weighted
63/126/189/252-session return minus Nifty 50's), so every rank shares one fixed
denominator. A group's reading is the plain mean of its members' ranks: 50 is
the universe average, above 50 means the group's stocks are leading.

Groups come from `sector_ranking.group_map` — the same Industry / Sector choice
as the ranking table, so the two panels always agree on who is in which group.

A view, not a signal: nothing here votes and nothing has been measured.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

import rs_walk as rw

OFFSETS = [("t5", 5), ("t0", 0)]


def leadership(ranks: dict[str, dict], smap: dict[str, str],
               min_members: int = 3) -> pd.DataFrame:
    """One row per group: members ranked, mean rank T-5 / T-0, change, top names."""
    groups: dict[str, list[str]] = {}
    for sym, grp in smap.items():
        if ranks.get(sym, {}).get("t0") is not None:
            groups.setdefault(grp, []).append(sym)
    rows = []
    for grp, syms in groups.items():
        if len(syms) < min_members:
            continue
        t0 = [ranks[s]["t0"] for s in syms]
        t5 = [ranks[s]["t5"] for s in syms if ranks[s].get("t5") is not None]
        top = sorted(syms, key=lambda s: -ranks[s]["t0"])[:3]
        a0 = float(np.mean(t0))
        a5 = float(np.mean(t5)) if t5 else None
        rows.append({
            "group": grp, "stocks": len(syms),
            "rs_t5": None if a5 is None else round(a5, 1),
            "rs_t0": round(a0, 1),
            "change": None if a5 is None else round(a0 - a5, 1),
            "pct_top_quartile": round(100 * sum(r >= 75 for r in t0) / len(t0)),
            "leaders": ", ".join(top),
        })
    df = pd.DataFrame(rows)
    return df.sort_values("rs_t0", ascending=False).reset_index(drop=True) if not df.empty else df


def grid(grouping: str = "industry") -> dict[str, Any]:
    import sector_ranking as srk
    import trending_stocks as ts
    import yfinance as yf

    smap = srk.group_map(grouping)
    if not smap:
        return {"error": "no constituents", "rows": pd.DataFrame()}
    hist = ts._batch_history(sorted(smap), period="2y")
    bench = yf.download("^NSEI", period="2y", progress=False, auto_adjust=True)
    if isinstance(bench.columns, pd.MultiIndex):
        bench.columns = [c[0] for c in bench.columns]
    g = rw.walk_grid(hist=hist, benchmark=bench if not bench.empty else None, offsets=OFFSETS)
    return {"rows": leadership(g.get("ranks", {}), smap),
            "universe": srk.GROUPINGS[grouping], "n_ranked": g.get("n_ranked", {})}


def render() -> None:
    import streamlit as st

    @st.cache_data(ttl=900, show_spinner=False)
    def _grid(grouping: str):
        return grid(grouping)

    st.markdown("#### 🏁 Relative-strength leadership")
    st.caption("Average RS rank by group, today (T-0) vs 5 sessions ago (T-5), sorted by T-0.")
    grouping = st.session_state.get("srk_group", "industry")
    if not st.session_state.get("rsl_ran"):
        if st.button("Build RS leadership", key="rsl_run", type="primary"):
            st.session_state["rsl_ran"] = True
            st.rerun()
        st.caption("Downloads 2 years of daily bars (the RS weighting reaches back 252 sessions). "
                   "Uses the same grouping as the sector ranking above.")
        return

    with st.spinner("Ranking relative strength…"):
        g = _grid(grouping)
    if g.get("error") or g["rows"].empty:
        st.warning(f"RS leadership unavailable: {g.get('error') or 'no groups ranked'}")
        return
    df = g["rows"]
    cc = st.column_config
    st.dataframe(
        df.style.background_gradient(cmap="RdYlGn", subset=["change"], vmin=-10, vmax=10),
        hide_index=True, width="stretch", height=min(38 + 35 * len(df), 720),
        column_config={
            "group": cc.TextColumn("Group"),
            "stocks": cc.NumberColumn("Stocks"),
            "rs_t5": cc.ProgressColumn("Avg RS T-5", min_value=0, max_value=100, format="%.0f"),
            "rs_t0": cc.ProgressColumn("Avg RS T-0", min_value=0, max_value=100, format="%.0f"),
            "change": cc.NumberColumn("Δ (T-0 − T-5)", format="%+.1f"),
            "pct_top_quartile": cc.ProgressColumn("% in top quartile", min_value=0,
                                                  max_value=100, format="%d%%"),
            "leaders": cc.TextColumn("Top RS names"),
        },
    )
    st.caption(
        f"{len(df)} groups · {g['universe']}. RS rank = universe-wide percentile of the "
        "IBD-weighted 63/126/189/252-session return minus Nifty 50's (`rs_walk`); a group "
        "reads the mean of its members, so 50 is the universe average. Groups with fewer "
        "than 3 ranked stocks are hidden. " + rw.SURVIVORSHIP_NOTE)
