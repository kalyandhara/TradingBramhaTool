"""index_valuation.py — B-145: Nifty P/E, P/B and dividend yield from the NSE
index files already cached, shown WITH the window they rest on.

Source: cache/nse_indices/ind_close_all_YYYY-MM-DD.csv (NSE's daily index close
file; columns P/E, P/B, Div Yield). Held since 2025-05-23, so the history is
months, not cycles.

The rule this module enforces: a level is shown with its window and its position
inside that window, and is NEVER labelled cheap or expensive. Calling today's P/E
"cheap" because it is the lowest of 17 months would be a claim the data cannot
carry; B-141 found the desk has no multi-cycle history to support one.
"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path
from typing import Any

CACHE = Path(__file__).resolve().parent / "cache" / "nse_indices"


def _f(v: Any) -> float | None:
    try:
        x = float(str(v).strip())
    except (TypeError, ValueError):
        return None
    return x if x > 0 else None      # NSE writes '-' or 0 where undefined


def history(index: str = "Nifty 50", cache: Path = CACHE) -> list[dict[str, Any]]:
    """Oldest-first rows: date, close, pe, pb, dy. Missing values are None."""
    rows = []
    for p in sorted(cache.glob("ind_close_all_*.csv")):
        try:
            with open(p, encoding="utf-8", errors="replace", newline="") as fh:
                for r in csv.DictReader(fh):
                    if (r.get("Index Name") or "").strip() != index:
                        continue
                    d = dt.datetime.strptime(r["Index Date"].strip(), "%d-%m-%Y").date()
                    rows.append({"date": d, "close": _f(r.get("Closing Index Value")),
                                 "pe": _f(r.get("P/E")), "pb": _f(r.get("P/B")),
                                 "dy": _f(r.get("Div Yield"))})
        except (OSError, KeyError, ValueError):
            continue
    rows.sort(key=lambda x: x["date"])
    return rows


def _pos(vals: list[float], v: float) -> float:
    """Percentile rank of v inside vals, 0..100 (share of values at or below v)."""
    return 100.0 * sum(1 for x in vals if x <= v) / len(vals)


def summary(index: str = "Nifty 50", cache: Path = CACHE) -> dict[str, Any] | None:
    h = history(index, cache)
    if not h:
        return None
    last = h[-1]
    out: dict[str, Any] = {"index": index, "asof": last["date"], "sessions": len(h),
                           "since": h[0]["date"],
                           "months": round((last["date"] - h[0]["date"]).days / 30.4, 1)}
    for k in ("pe", "pb", "dy"):
        vals = [x[k] for x in h if x[k] is not None]
        v = last[k]
        if v is None or len(vals) < 2:
            out[k] = None
            continue
        out[k] = {"value": v, "min": min(vals), "max": max(vals),
                  "pctile": round(_pos(vals, v), 0), "n": len(vals)}
    return out


def caption(s: dict[str, Any]) -> str:
    """One honest sentence. No cheap/expensive word, on purpose."""
    pe = s.get("pe")
    if not pe:
        return "Index valuation unavailable."
    return (f"Held for {s['sessions']} sessions since {s['since']:%d %b %Y} ({s['months']:.0f} months). "
            f"P/E {pe['value']:.1f} is at the {pe['pctile']:.0f}th percentile of that window "
            f"({pe['min']:.1f}–{pe['max']:.1f}). A window this short is not a cycle, so this is context, "
            f"not a verdict on whether the market is cheap.")
