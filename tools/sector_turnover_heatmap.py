#!/usr/bin/env python3
"""sector_turnover_heatmap.py — ScreeningMantis's two 15-session money-flow heatmaps.

  A/D NET FLOW        per group per session: (turnover of members that closed up
                      − turnover of members that closed down) ÷ group turnover, %.
                      +100 = every rupee traded was in advancing names.
  VS OWN HISTORY      per group per session: turnover ÷ the group's own trailing
                      9-session average. 1.0 = an ordinary day for that group.

Turnover is `turnover_share`'s close × volume proxy (same caveat). Groups come
from `sector_ranking.group_map`, so rows match the ranking and RS panels.

Normalising A/D by the group's own turnover is a choice: raw rupees would rank
Financial Services first every day by size alone. A view, not a signal.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

import turnover_share as tsh

SESSIONS = 15
BASELINE = 9


def _frame(members: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(close, turnover) aligned on dates, one column per member."""
    close = pd.DataFrame({s: pd.to_numeric(tsh._col(d, "close"), errors="coerce")
                          for s, d in members.items()})
    turn = pd.DataFrame({s: tsh.turnover_series(d) for s, d in members.items()})
    return close.sort_index(), turn.sort_index()


def group_series(members: dict[str, pd.DataFrame]) -> tuple[pd.Series, pd.Series]:
    """(A/D net % series, turnover ÷ trailing-9 average series) for one group."""
    close, turn = _frame(members)
    ret = close.pct_change()
    t = turn.where(ret.notna())
    total = t.sum(axis=1)
    net = t.where(ret > 0).sum(axis=1) - t.where(ret < 0).sum(axis=1)
    ad = (100 * net / total).where(total > 0)
    base = total.shift(1).rolling(BASELINE, min_periods=BASELINE).mean()
    rel = (total / base).where(base > 0)
    return ad, rel


def heatmaps(by_group: dict[str, dict[str, pd.DataFrame]],
             sessions: int = SESSIONS) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Two frames: rows = groups, columns = the last `sessions` dates, newest first."""
    ad_rows, rel_rows = {}, {}
    for grp, members in by_group.items():
        ad, rel = group_series(members)
        ad_rows[grp], rel_rows[grp] = ad, rel
    ad = pd.DataFrame(ad_rows).T
    rel = pd.DataFrame(rel_rows).T
    cols = sorted(ad.columns)[-sessions:][::-1]
    ad, rel = ad[cols].round(1), rel.reindex(columns=cols).round(2)
    order = ad[cols[0]].sort_values(ascending=False, na_position="last").index
    fmt = [pd.Timestamp(c).strftime("%d-%m") for c in cols]
    ad, rel = ad.loc[order], rel.loc[order]
    ad.columns = rel.columns = fmt
    return ad, rel


def grid(grouping: str = "sector", min_members: int = 3) -> dict[str, Any]:
    import sector_ranking as srk
    import trending_stocks as ts
    smap = srk.group_map(grouping)
    if not smap:
        return {"error": "no constituents"}
    hist = ts._batch_history(sorted(smap), period="3mo")
    by_group: dict[str, dict[str, pd.DataFrame]] = {}
    for sym, grp in smap.items():
        d = hist.get(sym)
        if d is not None and len(d) > BASELINE + 2:
            by_group.setdefault(grp, {})[sym] = d
    by_group = {g: m for g, m in by_group.items() if len(m) >= min_members}
    if not by_group:
        return {"error": "no group had enough members with history"}
    ad, rel = heatmaps(by_group)
    return {"ad": ad, "rel": rel, "universe": srk.GROUPINGS[grouping]}


def render() -> None:
    import streamlit as st

    @st.cache_data(ttl=900, show_spinner=False)
    def _grid(grouping: str):
        return grid(grouping)

    st.markdown("#### 🌡️ Turnover heatmaps · last 15 sessions")
    grouping = st.session_state.get("srk_group", "industry")
    if not st.session_state.get("tah_ran"):
        if st.button("Build turnover heatmaps", key="tah_run", type="primary"):
            st.session_state["tah_ran"] = True
            st.rerun()
        st.caption("Uses the same grouping as the sector ranking above.")
        return
    with st.spinner("Building heatmaps…"):
        g = _grid(grouping)
    if g.get("error"):
        st.warning(f"Turnover heatmaps unavailable: {g['error']}")
        return

    h = min(38 + 35 * len(g["ad"]), 720)
    st.markdown("**Advance/decline net flow** — (advancing − declining turnover) ÷ group "
                "turnover, % · newest first")
    st.dataframe(g["ad"].style.background_gradient(cmap="RdYlGn", vmin=-60, vmax=60, axis=None)
                 .format("{:+.0f}", na_rep="—"), use_container_width=True, height=h)
    st.markdown(f"**Turnover vs own history** — session turnover ÷ the group's trailing "
                f"{BASELINE}-session average · newest first")
    st.dataframe(g["rel"].style.background_gradient(cmap="Blues", vmin=0.5, vmax=2.0, axis=None)
                 .format("{:.2f}×", na_rep="—"), use_container_width=True, height=h)
    st.caption(f"{len(g['ad'])} groups · {g['universe']} · rows sorted by today's A/D net flow. "
               + tsh.TURNOVER_NOTE + " A view, not a signal — unmeasured.")
