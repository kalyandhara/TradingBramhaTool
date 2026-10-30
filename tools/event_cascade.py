"""B-190 — reverse event cascade for the Stock Analyzer.

stock (depth 0) → its NSE sector index (1) → the events that reached it (2):
the last Budget / RBI MPC days (policy_events.csv) and the stock's own last
results days. A flat parent-pointer `nodes[]`, the eVector Event Explorer shape
([[sources/Web-eVector-Event-Vector-Markets]]).

Each event node carries the stock's and the sector's cumulative abnormal return
over d0..d+5 (market model vs NIFTY 50, from event_study) and the stock's z.
Edges say what the desk knows, using chart_events.STATUS:

  solid   the event kind is measured (B-184: Budget, MPC)
  dashed  hypothesis (results days and anything not yet studied)
  dotted  second order: the stock only rode its sector that day

`expected` is filled only where there is a basis (the sign of the earnings
surprise); Budget direction was never measured, so it stays blank. Descriptive,
not a signal. The industry / thematic layer and the price-only cohort root of
the backlog sketch are not here yet.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

import chart_events as ce
import event_study as es
from context_ladder import _close

WINDOW = (0, 5)
WINDOW_LABEL = "d0..d+5"
FLAT_PCT = 0.5          # |move| under this is "flat"
RIDE_MIN_PCT = 1.0      # sector excess needed before "rode its sector" applies
RIDE_RATIO = 0.5        # stock-own excess under half the sector's → dotted
MAX_POLICY = 6
MAX_RESULTS = 4


def earnings_events(payload: dict | None) -> list[dict]:
    out = []
    for e in (payload or {}).get("events") or []:
        s = e.get("surprise_pct")
        exp = None if s is None else "up" if s > 0 else "down" if s < 0 else None
        label = "Results" + (f" · surprise {s:+.1f} %" if s is not None else "")
        out.append({"date": e["date"], "kind": "E", "label": label,
                    "status_key": "E", "expected": exp})
    return out


def policy_events(df: pd.DataFrame) -> list[dict]:
    return [dict(r, expected=None) for r in ce.policy_rows(df)]


def _car_z(pr: pd.DataFrame, when: pd.Timestamp) -> tuple[float, float] | None:
    """(CAR % over WINDOW, z of that CAR against the estimation residuals)."""
    q = int(pr.index.searchsorted(when, side="left"))
    if q >= len(pr):
        return None
    ar = es.market_model_ar(pr, q)
    car = None if ar is None else es._window_sum(ar, WINDOW)
    if car is None:
        return None
    lo, hi = max(0, q + es.EST[0]), q + es.EST[1] + 1
    r, m = pr["r"].to_numpy()[lo:hi], pr["m"].to_numpy()[lo:hi]
    beta, alpha = np.polyfit(m, r, 1)
    sd = float(np.std(r - (alpha + beta * m), ddof=2))
    n = WINDOW[1] - WINDOW[0] + 1
    z = car / (sd * np.sqrt(n)) if sd > 0 else 0.0
    return car * 100, float(z)


def _pairs(series: pd.Series | None, market: pd.Series) -> pd.DataFrame | None:
    if series is None:
        return None
    closes = pd.concat({"x": series, es.MARKET: market}, axis=1)
    return es.pair_returns(closes, "x")


def _direction(move: float) -> str:
    return "flat" if abs(move) < FLAT_PCT else "up" if move > 0 else "down"


def build_cascade(symbol: str, stock, market, sector, *, events: list[dict],
                  sector_ticker: str | None, sector_label: str | None) -> dict:
    s, mk, sx = _close(stock), _close(market), _close(sector)
    nodes = [{"id": "stock", "parent": None, "depth": 0, "kind": "stock",
              "label": symbol, "missing": s is None}]
    nodes.append({"id": "sector", "parent": "stock", "depth": 1, "kind": "sector",
                  "label": sector_label or sector_ticker or "Sector unknown",
                  "ticker": sector_ticker, "missing": sx is None})
    parent = "stock" if sx is None else "sector"
    ps = _pairs(s, mk) if mk is not None else None
    px = _pairs(sx, mk) if mk is not None else None
    evs = []
    for i, e in enumerate(sorted(events, key=lambda r: r["date"])):
        when = pd.Timestamp(e["date"])
        st = _car_z(ps, when) if ps is not None else None
        if st is None:
            continue
        move, z = st
        sx_res = _car_z(px, when) if px is not None else None
        smove = None if sx_res is None else sx_res[0]
        status = ce.status_for(e["status_key"])
        measured = status.startswith("measured")
        rode = (smove is not None and abs(smove) >= RIDE_MIN_PCT
                and abs(move - smove) < RIDE_RATIO * abs(smove))
        d = _direction(move)
        evs.append({"id": f"ev-{i}", "parent": parent, "depth": 2,
                    "kind": e["kind"], "label": e["label"], "date": e["date"],
                    "window": WINDOW_LABEL, "move": move, "sector_move": smove, "z": z,
                    "expected": e.get("expected"), "direction": d,
                    "miss": bool(e.get("expected")) and d != "flat" and d != e["expected"],
                    "edge": "dotted" if rode else "solid" if measured else "dashed",
                    "measured": measured, "status": status})
    up = sum(n["direction"] == "up" for n in evs)
    down = sum(n["direction"] == "down" for n in evs)
    kinds = {n["kind"] for n in evs}
    known = ("only Budget and MPC days are measured" if kinds - {"M"}
             else "all measured (B-184)" if kinds else "")
    text = (f"{len(evs)} linked events: {up} up, {down} down · {known}" if evs
            else "No linked events with enough history.")
    return {"symbol": symbol, "nodes": nodes + evs, "up": up, "down": down, "text": text}


def collect(symbol: str, stock, market, sector, *, sector_ticker: str | None,
            sector_label: str | None, earnings_fn: Callable | None = None,
            policy_fn: Callable | None = None) -> dict:
    """The latest MAX_POLICY policy days and MAX_RESULTS results days inside the
    stock's bars. A failing source is listed in `missing`; the rest still draws."""
    if earnings_fn is None:
        from earnings_calendar import fetch_earnings as earnings_fn
    policy_fn = policy_fn or ce._load_policy
    s = _close(stock)
    hi = str(s.index[-1].date()) if s is not None else "9999"
    rows, missing = [], []
    for kind, fn, cap in (("M", lambda: policy_events(policy_fn()), MAX_POLICY),
                          ("E", lambda: earnings_events(earnings_fn(symbol)), MAX_RESULTS)):
        try:
            got = sorted((r for r in fn() if r["date"] <= hi), key=lambda r: r["date"])
            rows += got[-cap:]
        except Exception:
            missing.append(kind)
    out = build_cascade(symbol, stock, market, sector, events=rows,
                        sector_ticker=sector_ticker, sector_label=sector_label)
    out["missing"] = missing
    return out
