#!/usr/bin/env python3
"""sector_indices_table.py — the NSE sectoral-indices table (ScreeningMantis "Sectors").

One row per sectoral / thematic index: close, 1D %, RSI(14), EMA 10/20/50/200
stack, % from 20EMA, 10x20 cross age, daily and weekly pivot zone, and the
RS-rank walk T-30 → T-15 → T-5 → T0.

Nothing here is new arithmetic. Every column is `row_metrics.row()` and the walk
is `rs_walk.walk_grid()`. What this module adds is the HISTORY: yfinance serves
full history for only a few NSE sector indices (B-80: 8 of 11 went dark), so the
series are assembled from NSE's own daily all-indices file, one file per session,
each cached forever by `sector_rotation.fetch_nse_index_closes`. The first build
downloads ~330 files; every build after reads them from disk.

The RS walk's survivorship caveat (`rs_walk.SURVIVORSHIP_NOTE`) does not apply:
this is a fixed list of indices, not a changing constituent set. An index younger
than the walk's 252-bar window shows `?` at the stops it did not exist for.

Descriptions of state, not signals — nothing here votes or has been measured.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from typing import Any, Callable, Optional

import pandas as pd

import row_metrics as rm
import rs_walk as rw
import sector_rotation as sr

#: NSE `Index Name` strings, exactly as the file spells them. The first 45 are
#: ScreeningMantis's set; the rest are sector indices NSE added that they lack.
SECTORAL_INDICES: list[str] = [
    "Nifty 50", "Nifty 100", "Nifty Midcap 150", "Nifty Smallcap 250",
    "Nifty Bank", "Nifty Private Bank", "Nifty PSU Bank", "Nifty Financial Services",
    "Nifty MidSmall Financial Services", "Nifty Capital Markets",
    "Nifty IT", "Nifty MidSmall IT & Telecom", "Nifty India Digital", "Nifty India Internet",
    "Nifty Pharma", "Nifty Healthcare Index", "Nifty MidSmall Healthcare",
    "Nifty Auto", "Nifty EV & New Age Automotive", "Nifty Mobility",
    "Nifty FMCG", "Nifty India Consumption", "Nifty MidSmall India Consumption",
    "Nifty Consumer Durables", "Nifty Rural", "Nifty India Tourism", "Nifty Media",
    "Nifty Metal", "Nifty Commodities", "Nifty Chemicals", "Nifty Energy", "Nifty Oil & Gas",
    "Nifty Realty", "Nifty Housing", "Nifty Core Housing", "Nifty Infrastructure",
    "Nifty Transportation & Logistics", "Nifty India Railways PSU", "Nifty India Defence",
    "Nifty CPSE", "Nifty PSE", "Nifty MNC", "Nifty Services Sector", "Nifty IPO",
    "Nifty Conglomerate 50",
    "Nifty NBFC", "Nifty Insurance", "Nifty Housing Finance", "Nifty Cement",
    "Nifty Construction", "Nifty Capital Goods", "Nifty Power", "Nifty Hospitals",
    "Nifty Telecommunications", "Nifty Retail",
]

BENCHMARK = "Nifty 50"

#: Sessions to assemble: the walk needs 252 bars at T-30, so 252 + 30 plus slack.
DEFAULT_SESSIONS = 330

_OHLC = {"open": "Open Index Value", "high": "High Index Value",
         "low": "Low Index Value", "close": "Closing Index Value"}


def candidate_days(today: date, sessions: int) -> list[date]:
    """Weekdays far enough back to contain `sessions` trading sessions."""
    span = int(sessions * 1.45) + 14
    days = [today - timedelta(days=i) for i in range(span)]
    return [d for d in days if d.weekday() < 5]


def assemble(files: dict[date, pd.DataFrame],
             names: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """`{index name: OHLC frame indexed by date}` from per-session NSE files."""
    want = set(names or SECTORAL_INDICES) | {BENCHMARK}
    rows: dict[str, list[dict[str, Any]]] = {}
    for d in sorted(files):
        df = files[d]
        if df is None or "Index Name" not in df.columns:
            continue
        for rec in df.to_dict("records"):
            name = str(rec.get("Index Name", "")).strip()
            if name not in want:
                continue
            vals = {k: pd.to_numeric(rec.get(col), errors="coerce") for k, col in _OHLC.items()}
            if pd.isna(vals["close"]):
                continue
            for k in ("open", "high", "low"):
                if pd.isna(vals[k]):
                    vals[k] = vals["close"]
            rows.setdefault(name, []).append({"date": pd.Timestamp(d), **vals})
    return {n: pd.DataFrame(r).set_index("date").astype(float) for n, r in rows.items()}


def load_history(sessions: int = DEFAULT_SESSIONS, *, today: date | None = None,
                 fetch: Callable = sr.fetch_nse_index_closes,
                 workers: int = 4) -> dict[str, pd.DataFrame]:
    """Fetch (or read cached) NSE session files and assemble per-index history."""
    days = candidate_days(today or date.today(), sessions)

    def _one(d: date):
        df, got = fetch(d, max_backtrack=0)
        return (d, df) if df is not None and got == d else (d, None)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        got = dict(ex.map(_one, days))
    files = {d: df for d, df in got.items() if df is not None}
    keep = sorted(files)[-sessions:]
    return assemble({d: files[d] for d in keep})


def build_table(hist: dict[str, pd.DataFrame],
                names: list[str] | None = None) -> pd.DataFrame:
    """One row per index, sorted by RS rank today (strongest first)."""
    names = [n for n in (names or SECTORAL_INDICES) if n in hist]
    grid = rw.walk_grid(hist={n: hist[n] for n in names},
                        benchmark=hist.get(BENCHMARK))
    ranks = grid.get("ranks", {})
    cols = grid.get("columns") or [lbl for lbl, _ in rw.OFFSETS]

    out = []
    for n in names:
        df = hist[n]
        c = df["close"]
        m = rm.row(df)
        chg = (float(c.iloc[-1]) / float(c.iloc[-2]) - 1) * 100 if len(c) >= 2 else None
        r = ranks.get(n, {})
        walk = [r.get(k) for k in cols]
        cross = None
        if m["ema_cross_dir"] == "up" and m["ema_cross_age"] is not None:
            cross = m["ema_cross_age"]
        out.append({
            "Index": n,
            "Price": round(float(c.iloc[-1]), 2),
            "% Chg 1D": None if chg is None else round(chg, 2),
            "RSI": m["rsi"],
            "EMAs": m["ema_stack"],
            "% from 20EMA": m["pct_from_20ema"],
            "10x20 up (days)": cross,
            "D-Pivot": m["pivot_d"],
            "W-Pivot": m["pivot_w"],
            "RS T0": r.get(cols[-1]),
            "RS walk": rw.format_walk(r, cols),
            "RS trend": [v for v in walk if v is not None],
            "Bars": len(df),
        })
    t = pd.DataFrame(out)
    if t.empty:
        return t
    for col in ("10x20 up (days)", "RS T0"):
        t[col] = pd.array(t[col], dtype="Int64")
    return t.sort_values("RS T0", ascending=False, na_position="last").reset_index(drop=True)


def as_of(hist: dict[str, pd.DataFrame]) -> Optional[str]:
    b = hist.get(BENCHMARK)
    return None if b is None or b.empty else b.index[-1].date().isoformat()


def render() -> None:
    import streamlit as st

    @st.cache_data(ttl=3600, show_spinner=False)
    def _cached(day: str) -> dict[str, pd.DataFrame]:
        return load_history()

    st.markdown("#### 🏷️ Sectoral indices")
    if not st.session_state.get("sit_ran"):
        if st.button("Build sectoral-indices table", key="sit_run", type="primary"):
            st.session_state["sit_ran"] = True
            st.rerun()
        st.caption("Assembles ~330 sessions of NSE's daily index file. The first build "
                   "downloads them (about a minute); after that they load from disk.")
        return

    with st.spinner("Loading NSE index history…"):
        hist = _cached(date.today().isoformat())
    table = build_table(hist)
    if table.empty:
        st.warning("No NSE index history could be loaded.")
        return

    st.caption(f"{len(table)} NSE sectoral/thematic indices · as of {as_of(hist)} · "
               "sorted by RS rank today")
    st.dataframe(
        table.drop(columns=["Bars"]), hide_index=True, use_container_width=True,
        height=min(38 + 35 * len(table), 720),
        column_config={
            "Price": st.column_config.NumberColumn(format="₹%.1f"),
            "% Chg 1D": st.column_config.NumberColumn(format="%+.2f%%"),
            "RSI": st.column_config.NumberColumn(format="%.1f"),
            "% from 20EMA": st.column_config.NumberColumn(format="%+.1f%%"),
            "10x20 up (days)": st.column_config.NumberColumn(
                help="Sessions since the 10 EMA crossed above the 20 EMA; blank if 10 < 20"),
            "RS T0": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
            "RS walk": st.column_config.TextColumn(help="Percentile rank at T-30 → T-15 → T-5 → T0"),
            "RS trend": st.column_config.LineChartColumn(y_min=0, y_max=100),
        },
    )
    st.caption(
        "RS = IBD-weighted 63/126/189/252-session return minus Nifty 50's, ranked "
        "0-100 across these indices (`rs_walk`). `?` = the index had under 252 "
        "sessions of history at that point. Pivots are classic floor pivots from "
        "the prior day / week. Descriptions of state, not signals — unmeasured.")
