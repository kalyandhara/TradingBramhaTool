#!/usr/bin/env python3
"""cpr_vp.py — CPR × Volume Profile confluence read. Context, NOT a signal.

The desk already had both halves: CPR (TC / Pivot / BC + R1 / S1 from the
prior bar, `row_metrics.pivot_levels`) and the Volume Profile (POC / Value
Area / HVN / LVN, `volume_profile.py`). They never met: CPR was drawn only on
the classic Plotly chart, the profile only on the Chart Tool, and nothing
asked whether a CPR level sits inside a high-volume node. This module is the
one place that asks, so the Chart Tool card, Setup Intelligence and the Home
scan cannot disagree about what "TC inside an HVN" means.

What it reports (`read`):
  * the CPR band (normalised so `tc >= bc` whatever the prior close did),
    its width as % of price and a narrow / normal / wide label;
  * where the last close sits: above_tc / inside / below_bc;
  * RVOL — today's volume over the prior `rvol_window` bars' mean;
  * confluence — which CPR levels line up with POC / VAH / VAL / HVN / LVN,
    via `volume_profile.find_confluence` with the same tolerance the chart uses;
  * the five auction-style setups the "Volume Profile + CPR" playbook names,
    each a countable boolean on the LAST bar only.

Every setup is a description of what the bar did against the levels. None of
them has been measured for forward return here — the SVP composite in this
repo scored negative when it was, and these are the same genre — so the desk
shows them as context with the wording to match, never as BUY / SELL.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

import row_metrics as rm
import volume_profile as vp

LOOKBACK = 60          # bars of profile the read is taken against
RVOL_WINDOW = 20       # prior bars for the volume baseline
RVOL_STRONG = 1.5      # "with volume" — same bar as the playbook's "high volume"
TOL_PCT = 0.004        # level-to-zone tolerance, identical to the chart's
NARROW_PCT = 0.5       # CPR width as % of pivot: below = narrow (trend day prone)
WIDE_PCT = 1.5         # above = wide (range day prone)

SETUP_LABELS = {
    "hold_above_cpr_volume":  "Holds above CPR with volume",
    "breakout_from_hvn":      "Breakout from HVN",
    "cpr_retest_buying":      "CPR retest, buying pressure",
    "rejection_at_cpr":       "Rejection from CPR",
    "rejection_at_hvn":       "Rejection at HVN with selling",
    "breakdown_below_cpr":    "Breakdown below CPR with volume",
}
BULLISH = {"hold_above_cpr_volume", "breakout_from_hvn", "cpr_retest_buying"}
BEARISH = {"rejection_at_cpr", "rejection_at_hvn", "breakdown_below_cpr"}


def _zone_at(price: float, zones: list[dict]) -> dict | None:
    for z in zones:
        if z["low"] <= price <= z["high"]:
            return z
    return None


def read(df: pd.DataFrame, *, lookback: int = LOOKBACK,
         rvol_window: int = RVOL_WINDOW, tol_pct: float = TOL_PCT) -> dict | None:
    """The CPR × profile read on the last bar of `df` (lowercase OHLCV)."""
    if df is None or not {"open", "high", "low", "close", "volume"}.issubset(df.columns):
        return None
    d = df.dropna(subset=["open", "high", "low", "close", "volume"])
    if len(d) < max(3, rvol_window + 2):
        return None

    lv = rm.pivot_levels(d)
    if not lv:
        return None
    tc, bc = max(lv["tc"], lv["bc"]), min(lv["tc"], lv["bc"])
    pp, r1, s1 = lv["pp"], lv["r1"], lv["s1"]

    o = float(d["open"].iloc[-1]); h = float(d["high"].iloc[-1])
    lo = float(d["low"].iloc[-1]); c = float(d["close"].iloc[-1])
    prev_c = float(d["close"].iloc[-2])
    if not all(np.isfinite(v) for v in (o, h, lo, c, prev_c)) or pp <= 0:
        return None

    base = float(d["volume"].iloc[-rvol_window - 1:-1].mean())
    v_today = float(d["volume"].iloc[-1])
    rvol = (v_today / base) if base > 0 else None
    strong = rvol is not None and rvol >= RVOL_STRONG

    width_pct = (tc - bc) / pp * 100.0
    band = "narrow" if width_pct < NARROW_PCT else "wide" if width_pct > WIDE_PCT else "normal"
    position = "above_tc" if c > tc else "below_bc" if c < bc else "inside"

    profile = vp.compute_profile(d, lookback=lookback)
    points = [{"name": n, "price": p} for n, p in
              (("TC", tc), ("P", pp), ("BC", bc), ("R1", r1), ("S1", s1))]
    conf_rows = vp.find_confluence(points, profile, tol_pct) if profile else []
    confluence = {r["name"]: sorted({m["type"] for m in r["matches"]}) for r in conf_rows}
    band_types = set().union(*(set(confluence.get(n, [])) for n in ("TC", "P", "BC")))
    cpr_in_hvn = bool(band_types & {"HVN", "POC"})
    cpr_in_lvn = "LVN" in band_types and not cpr_in_hvn

    hvn_zones = profile["hvn_zones"] if profile else []
    prev_hvn = _zone_at(prev_c, hvn_zones)
    high_hvn = _zone_at(h, hvn_zones)
    tol = c * tol_pct

    setups: list[str] = []
    if c > tc and lo >= bc - tol and strong:
        setups.append("hold_above_cpr_volume")
    if prev_hvn is not None and c > prev_hvn["high"] + tol and c > o:
        setups.append("breakout_from_hvn")
    if bc - tol <= lo <= tc + tol and c > tc and c > o and "hold_above_cpr_volume" not in setups:
        setups.append("cpr_retest_buying")
    if h >= bc - tol and c < bc and c < o and strong and prev_c >= bc:
        setups.append("rejection_at_cpr")
    if high_hvn is not None and c < high_hvn["low"] - tol and c < o and strong:
        setups.append("rejection_at_hvn")
    if c < bc and prev_c >= bc and strong and "rejection_at_cpr" not in setups:
        setups.append("breakdown_below_cpr")

    has_bull = any(s in BULLISH for s in setups)
    has_bear = any(s in BEARISH for s in setups)
    bias = ("mixed" if has_bull and has_bear else "bullish" if has_bull
            else "bearish" if has_bear else "none")

    return {
        "close": c, "chg_pct": (c / prev_c - 1) * 100.0 if prev_c else None,
        "rvol": rvol, "strong_volume": strong,
        "levels": {"tc": tc, "p": pp, "bc": bc, "r1": r1, "s1": s1},
        "width_pct": width_pct, "band": band, "position": position,
        "confluence": confluence, "cpr_in_hvn": cpr_in_hvn, "cpr_in_lvn": cpr_in_lvn,
        "poc": profile["poc"]["price"] if profile else None,
        "vah": profile["value_area"]["high"] if profile else None,
        "val": profile["value_area"]["low"] if profile else None,
        "setups": setups, "bias": bias,
    }


def confluence_text(r: dict) -> str:
    """'TC∈HVN · BC≈POC' — the confluence dict as one short cell."""
    parts = []
    for name in ("TC", "P", "BC", "R1", "S1"):
        types = r.get("confluence", {}).get(name)
        if types:
            parts.append(f"{name}∈{'/'.join(types)}")
    return " · ".join(parts)


POSITION_LABELS = {"above_tc": "above TC", "inside": "inside CPR", "below_bc": "below BC"}


def scan(universe: list[str], fetch_ohlcv: Callable, *, days: int = 140,
         lookback: int = LOOKBACK, stats: dict | None = None) -> list[dict]:
    """Rows for every name whose last bar fired at least one setup, or whose
    CPR band sits inside a high-volume node (the confluence the playbook is
    about). `stats` receives {"scanned": n} — names with a usable frame — so a
    caller can tell "nothing fired" from "nothing could be fetched"."""
    rows: list[dict] = []
    scanned = 0
    for sym in universe:
        try:
            df = fetch_ohlcv(sym, days=days)
        except Exception:                                    # noqa: BLE001
            continue
        if df is None or len(df) < RVOL_WINDOW + 2:
            continue
        scanned += 1
        r = read(df, lookback=lookback)
        if not r or (not r["setups"] and not r["cpr_in_hvn"]):
            continue
        rows.append({
            "Symbol": sym,
            "Close": round(r["close"], 2),
            "Chg %": round(r["chg_pct"], 2) if r["chg_pct"] is not None else None,
            "RVOL": round(r["rvol"], 2) if r["rvol"] is not None else None,
            "CPR": POSITION_LABELS[r["position"]],
            "Width %": round(r["width_pct"], 2),
            "Band": r["band"],
            "Confluence": confluence_text(r),
            "Setups": ", ".join(SETUP_LABELS[s] for s in r["setups"]),
            "Bias": r["bias"],
            "TC": round(r["levels"]["tc"], 2), "P": round(r["levels"]["p"], 2),
            "BC": round(r["levels"]["bc"], 2),
            "POC": round(r["poc"], 2) if r["poc"] is not None else None,
        })
    if stats is not None:
        stats["scanned"] = scanned
    rows.sort(key=lambda x: ((x["Bias"] != "none"), x["RVOL"] or 0), reverse=True)
    return rows
