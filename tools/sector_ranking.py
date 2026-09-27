#!/usr/bin/env python3
"""sector_ranking.py — the ScreeningMantis "Sector ranking" table.

One row per sector, two halves:

  ROTATION  stocks · turnover · % change D/W · share % · Δ share D/W (points)
  HEALTH    A/D net · avg RSI · % above 20EMA · % broke out in last 10 days · leaders

Nothing is new arithmetic. Share and Δshare are `turnover_share.shares` (same
proxy, same caveats); RSI, % from 20EMA and breakout are `row_metrics`. Sector
buckets are `sectors.symbol_map` — the one vocabulary the other grids use.

% change is the EQUAL-weight mean of member returns: the question is how the
sector's stocks did, and a cap-weighted figure would just be its largest name.
Leaders are the three best 1D movers, not the biggest turnover.

A view, not a signal: nothing here votes and nothing has been measured.
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

import row_metrics as rm
import turnover_share as tsh

BO_WINDOW = 10
N_LEADERS = 3


def _ret(df: pd.DataFrame, offset: int) -> Optional[float]:
    c = pd.to_numeric(tsh._col(df, "close"), errors="coerce").astype(float)
    if len(c) <= offset:
        return None
    a, b = float(c.iloc[-1]), float(c.iloc[-1 - offset])
    return (a / b - 1) * 100 if b > 0 and np.isfinite(a) else None


def _mean(vals: list[Optional[float]]) -> Optional[float]:
    v = [x for x in vals if x is not None and np.isfinite(x)]
    return float(np.mean(v)) if v else None


def _pct(flags: list[Optional[bool]]) -> Optional[float]:
    v = [f for f in flags if f is not None]
    return 100.0 * sum(v) / len(v) if v else None


def sector_row(sector: str, members: dict[str, pd.DataFrame]) -> dict[str, Any]:
    d1 = {s: _ret(df, 1) for s, df in members.items()}
    w1 = {s: _ret(df, 5) for s, df in members.items()}
    pfe = {s: rm.pct_from_ema(df) for s, df in members.items()}
    bo = [rm.breakout(df)["bars_ago"] for df in members.values()]
    movers = sorted((s for s, r in d1.items() if r is not None), key=lambda s: -d1[s])
    adv = sum(1 for r in d1.values() if r is not None and r > 0)
    dec = sum(1 for r in d1.values() if r is not None and r < 0)
    r2 = lambda x, n=2: None if x is None else round(x, n)
    return {
        "sector": sector,
        "stocks": len(members),
        "turnover_cr": round(tsh.sector_turnover(members, 0) / 1e7, 1),
        "chg_d": r2(_mean(list(d1.values()))),
        "chg_w": r2(_mean(list(w1.values()))),
        "ad_net": adv - dec,
        "avg_rsi": r2(_mean([rm.rsi(df) for df in members.values()]), 0),
        "pct_above_20ema": r2(_pct([None if v is None else v > 0 for v in pfe.values()]), 0),
        "pct_bo_10d": r2(_pct([b is not None and b < BO_WINDOW for b in bo]), 0),
        "leaders": ", ".join(movers[:N_LEADERS]),
    }


#: Grouping choices: (universe, label source). "industry" is NSE's basic
#: industry via `industry_map` (Sugar, Paints…); "sector" is the ~20-label
#: vocabulary the other grids use.
GROUPINGS = {"industry": "niftytotalmarket", "sector": "nifty500"}


def group_map(grouping: str) -> dict[str, str]:
    universe = GROUPINGS[grouping]
    if grouping == "industry":
        import industry_map as im
        return im.symbol_map(universe, level="basic")
    import sectors as sc
    return sc.symbol_map(universe)


def ranking_grid(universe: str = "nifty500",
                 hist: dict[str, pd.DataFrame] | None = None,
                 min_members: int = 3,
                 smap: dict[str, str] | None = None) -> dict[str, Any]:
    """One row per sector, sorted by Δshare today (money moving in first)."""
    if smap is None:
        import sectors as sc
        smap = sc.symbol_map(universe)
    if not smap:
        return {"error": "no constituents", "rows": pd.DataFrame()}
    if hist is None:
        import trending_stocks as ts
        hist = ts._batch_history(sorted(smap), period="6mo")

    by_sector: dict[str, dict[str, pd.DataFrame]] = {}
    for sym, sector in smap.items():
        df = hist.get(sym)
        if df is not None and len(df) > 6:
            by_sector.setdefault(sector, {})[sym] = df
    n_thin = sum(1 for m in by_sector.values() if len(m) < min_members)
    by_sector = {s: m for s, m in by_sector.items() if len(m) >= min_members}
    if not by_sector:
        return {"error": "no sector had enough members with history", "rows": pd.DataFrame()}

    now, pd_, pw = (tsh.shares(by_sector, o) for o in (0, tsh.DAY_OFFSET, tsh.WEEK_OFFSET))
    rows = []
    for sector, members in by_sector.items():
        r = sector_row(sector, members)
        s = now.get(sector)
        r["share_pct"] = None if s is None else round(100 * s, 2)
        r["d_share_d"] = None if s is None or sector not in pd_ else round(100 * (s - pd_[sector]), 2)
        r["d_share_w"] = None if s is None or sector not in pw else round(100 * (s - pw[sector]), 2)
        rows.append(r)
    df = pd.DataFrame(rows).sort_values("d_share_d", ascending=False, na_position="last")
    return {"rows": df.reset_index(drop=True), "universe": universe,
            "n_symbols": len(smap), "n_sectors": len(by_sector), "n_thin": n_thin}


COLUMNS = ["sector", "stocks", "turnover_cr", "chg_d", "chg_w", "share_pct",
           "d_share_d", "d_share_w", "ad_net", "avg_rsi", "pct_above_20ema",
           "pct_bo_10d", "leaders"]


def render() -> None:
    import streamlit as st

    @st.cache_data(ttl=900, show_spinner=False)
    def _grid(grouping: str):
        return ranking_grid(GROUPINGS[grouping], smap=group_map(grouping))

    st.markdown("#### 🧭 Sector ranking · rotation + health")
    grouping = st.radio(
        "Group by", ["industry", "sector"], horizontal=True, key="srk_group",
        format_func=lambda g: {"industry": "Industry (Nifty Total Market, ~750)",
                               "sector": "Broad sector (Nifty 500)"}[g])
    if not st.session_state.get("srk_ran"):
        if st.button("Build sector ranking", key="srk_run", type="primary"):
            st.session_state["srk_ran"] = True
            st.rerun()
        st.caption("Downloads 6 months of daily bars for the chosen universe.")
        return

    with st.spinner("Ranking…"):
        g = _grid(grouping)
    if g.get("error"):
        st.warning(f"Sector ranking unavailable: {g['error']}")
        return
    df = g["rows"][COLUMNS]
    cc = st.column_config
    st.caption(f"{g['n_sectors']} groups · {g['universe']} · sorted by Δ share today"
               + (f" · {g['n_thin']} groups with <3 stocks hidden" if g.get("n_thin") else ""))
    st.dataframe(
        df.style.background_gradient(cmap="RdYlGn", subset=["d_share_d", "d_share_w"],
                                     vmin=-2.0, vmax=2.0)
                .background_gradient(cmap="RdYlGn", subset=["chg_d", "chg_w"],
                                     vmin=-3.0, vmax=3.0),
        hide_index=True, use_container_width=True,
        height=min(38 + 35 * len(df), 720),
        column_config={
            "sector": cc.TextColumn("Sector"),
            "stocks": cc.NumberColumn("Stocks"),
            "turnover_cr": cc.NumberColumn("Turnover", format="₹%.0f Cr"),
            "chg_d": cc.NumberColumn("% Chg D", format="%+.2f%%"),
            "chg_w": cc.NumberColumn("% Chg W", format="%+.2f%%"),
            "share_pct": cc.NumberColumn("Share %", format="%.2f"),
            "d_share_d": cc.NumberColumn("Δ Share D", format="%+.2f"),
            "d_share_w": cc.NumberColumn("Δ Share W", format="%+.2f"),
            "ad_net": cc.NumberColumn("A/D Net", format="%+d"),
            "avg_rsi": cc.NumberColumn("Avg RSI", format="%.0f"),
            "pct_above_20ema": cc.ProgressColumn("% > 20EMA", min_value=0, max_value=100, format="%d%%"),
            "pct_bo_10d": cc.ProgressColumn("% BO 10d", min_value=0, max_value=100, format="%d%%"),
            "leaders": cc.TextColumn("Leaders", help="Top 3 members by 1D % change"),
        },
    )
    st.caption(
        "% change = equal-weight mean of member returns. Share / Δ share = turnover "
        "share in percentage points (close × volume proxy, unsigned). A/D net = "
        "advancers − decliners today. % BO 10d = members whose close cleared their "
        "prior 20-day high within the last 10 sessions. A view, not a signal — unmeasured.")
