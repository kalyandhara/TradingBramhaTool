"""Market Health — per-index breadth under the 200 EMA + a 0-100 context score.

Plan: docs/superpowers/plans/2026-11-22-market-health-score.md

Two things, kept apart on purpose:

1. **Index breadth.** For each index the desk already has a constituent list for,
   how many members close above / below their 200-day EMA. A name with fewer
   than 200 bars is "no data" — never silently counted on either side.

2. **Composite context score.** Five pillars, each 0-100, weighted by the
   owner's PRIORS (Trend 30, Breadth 25, Volume 20, Volatility 15, Flows 10).
   These weights are chosen, not measured. Nothing here has been backtested;
   the score describes the tape, it does not forecast it.

Pure functions take frames and return dicts, so the maths is testable without
the network. The `fetch_*` helpers at the bottom are the only I/O.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

log = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")
EMA_LONG = 200
EMA_SHORT = 50
SLOPE_LOOKBACK = 20
VOLUME_WINDOW = 20

#: The owner's priors. Unmeasured — label them that way wherever shown.
WEIGHTS: dict[str, int] = {
    "trend": 30, "breadth": 25, "volume": 20, "volatility": 15, "flows": 10,
}
PILLAR_LABELS = {
    "trend": "Trend", "breadth": "Breadth", "volume": "Volume",
    "volatility": "Volatility", "flows": "Liquidity / Flows",
}


# ── helpers ──────────────────────────────────────────────────────────────────
def _closes(df) -> pd.Series | None:
    if df is None or getattr(df, "empty", True) or "Close" not in df:
        return None
    c = pd.to_numeric(df["Close"], errors="coerce").dropna()
    return c if len(c) else None


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def _clip(x: float) -> float:
    return float(max(0.0, min(100.0, x)))


# ── 1 · per-index breadth ────────────────────────────────────────────────────
def ema_state(df, n: int = EMA_LONG) -> bool | None:
    """True if last close > its n-EMA, False if at/below, None if < n bars."""
    c = _closes(df)
    if c is None or len(c) < n:
        return None
    return bool(c.iloc[-1] > ema(c, n).iloc[-1])


def breadth_counts(members: list[str], frames: dict[str, Any],
                   n: int = EMA_LONG) -> dict[str, Any]:
    """Above / below n-EMA counts for one group of symbols."""
    above = below = 0
    for s in members:
        st = ema_state(frames.get(s), n)
        if st is True:
            above += 1
        elif st is False:
            below += 1
    measured = above + below
    return {
        "members": len(members), "measured": measured,
        "no_data": len(members) - measured,
        "above": above, "below": below,
        "pct_above": round(100 * above / measured, 1) if measured else None,
        "pct_below": round(100 * below / measured, 1) if measured else None,
    }


def breadth_table(groups: dict[str, list[str]], frames: dict[str, Any],
                  n: int = EMA_LONG) -> list[dict[str, Any]]:
    """One row per group, in the order given."""
    return [{"index": name, **breadth_counts(m, frames, n)} for name, m in groups.items()]


def advance_share(frames: dict[str, Any]) -> float | None:
    """% of names whose last close is above the prior close (unchanged excluded)."""
    up = down = 0
    for df in frames.values():
        c = _closes(df)
        if c is None or len(c) < 2:
            continue
        d = c.iloc[-1] - c.iloc[-2]
        if d > 0:
            up += 1
        elif d < 0:
            down += 1
    return round(100 * up / (up + down), 1) if up + down else None


# ── 2 · pillars ──────────────────────────────────────────────────────────────
def _pillar(key: str, score: float | None, inputs: dict, read: str) -> dict[str, Any]:
    return {"key": key, "label": PILLAR_LABELS[key], "weight": WEIGHTS[key],
            "score": None if score is None else round(score, 1),
            "inputs": inputs, "read": read}


def trend_pillar(index_df) -> dict[str, Any]:
    """25 points each: close>50EMA, close>200EMA, 50EMA>200EMA, 200EMA rising."""
    c = _closes(index_df)
    if c is None or len(c) < EMA_LONG + SLOPE_LOOKBACK:
        return _pillar("trend", None, {}, "NIFTY 50 history too short — not assessed.")
    e50, e200 = ema(c, EMA_SHORT), ema(c, EMA_LONG)
    last = float(c.iloc[-1])
    checks = {
        "close > 50 EMA": last > e50.iloc[-1],
        "close > 200 EMA": last > e200.iloc[-1],
        "50 EMA > 200 EMA": e50.iloc[-1] > e200.iloc[-1],
        f"200 EMA rising ({SLOPE_LOOKBACK}d)": e200.iloc[-1] > e200.iloc[-1 - SLOPE_LOOKBACK],
    }
    held = sum(bool(v) for v in checks.values())
    inputs = {"NIFTY 50": round(last, 1), "50 EMA": round(float(e50.iloc[-1]), 1),
              "200 EMA": round(float(e200.iloc[-1]), 1),
              **{k: "yes" if v else "no" for k, v in checks.items()}}
    return _pillar("trend", 25.0 * held, inputs,
                   f"{held} of 4 trend checks hold on NIFTY 50.")


def breadth_pillar(pct_above_200: float | None, adv_pct: float | None) -> dict[str, Any]:
    """0.6 × % above 200 EMA + 0.4 × advancers %. One missing → the other alone."""
    got = [(w, v) for w, v in ((0.6, pct_above_200), (0.4, adv_pct)) if v is not None]
    if not got:
        return _pillar("breadth", None, {}, "Breadth unreadable — not assessed.")
    score = sum(w * v for w, v in got) / sum(w for w, _ in got)
    a = "—" if pct_above_200 is None else pct_above_200
    b = "—" if adv_pct is None else adv_pct
    return _pillar("breadth", _clip(score),
                   {"% NIFTY 500 above 200 EMA": pct_above_200,
                    "% advancing last session": adv_pct},
                   f"{a}% of NIFTY 500 above the 200 EMA; {b}% advanced last session.")


def up_volume_share(frames: dict[str, Any], window: int = VOLUME_WINDOW) -> float | None:
    """Volume on up-close days ÷ volume on up+down days, last `window` sessions, pooled."""
    up = down = 0.0
    for df in frames.values():
        if df is None or getattr(df, "empty", True) or "Volume" not in df:
            continue
        chg = pd.to_numeric(df["Close"], errors="coerce").diff().tail(window)
        vol = pd.to_numeric(df["Volume"], errors="coerce").tail(window)
        up += float(vol[chg > 0].sum())
        down += float(vol[chg < 0].sum())
    return round(100 * up / (up + down), 1) if up + down > 0 else None


def volume_pillar(up_share: float | None) -> dict[str, Any]:
    if up_share is None:
        return _pillar("volume", None, {}, "Volume unreadable — not assessed.")
    return _pillar("volume", _clip(up_share),
                   {f"up-day volume share ({VOLUME_WINDOW}d)": up_share},
                   f"{up_share}% of NIFTY 500 volume over {VOLUME_WINDOW} sessions "
                   "traded on up days.")


def percentile_rank(s: pd.Series, value: float) -> float:
    """% of observations at or below `value`."""
    return float((s <= value).mean() * 100)


def volatility_pillar(vix_df, index_df=None) -> dict[str, Any]:
    """100 − India VIX 1y percentile; fallback: NIFTY 20d realized-vol percentile."""
    c = _closes(vix_df)
    if c is not None and len(c) >= 60:
        last = float(c.iloc[-1])
        pct = percentile_rank(c.tail(250), last)
        return _pillar("volatility", _clip(100 - pct),
                       {"India VIX": round(last, 2), "1y percentile": round(pct, 1)},
                       f"India VIX {last:.2f} sits at the {pct:.0f}th percentile of its year.")
    n = _closes(index_df)
    if n is not None and len(n) >= 80:
        rv = n.pct_change().rolling(20).std().dropna() * (252 ** 0.5) * 100
        last = float(rv.iloc[-1])
        pct = percentile_rank(rv.tail(250), last)
        return _pillar("volatility", _clip(100 - pct),
                       {"NIFTY 20d realized vol %": round(last, 1),
                        "1y percentile": round(pct, 1), "source": "VIX fallback"},
                       f"VIX unavailable — NIFTY realized vol at the {pct:.0f}th percentile.")
    return _pillar("volatility", None, {}, "No VIX or NIFTY history — not assessed.")


def flows_pillar(fii_long_share: float | None, as_of: date | None = None) -> dict[str, Any]:
    """FII long ÷ (long+short) index-futures OI, × 100 (owner-confirmed 2026-11-22)."""
    if fii_long_share is None:
        return _pillar("flows", None, {}, "Participant OI unavailable — not assessed.")
    pct = round(100 * fii_long_share, 1)
    return _pillar("flows", _clip(pct),
                   {"FII index-futures long %": pct,
                    "as of": as_of.isoformat() if as_of else "—"},
                   f"FIIs are {pct}% long / {round(100 - pct, 1)}% short index futures.")


# ── 3 · composite ────────────────────────────────────────────────────────────
def band_for(score: float) -> str:
    if score >= 70:
        return "broadly healthy"
    if score >= 50:
        return "mixed"
    if score >= 30:
        return "weak"
    return "stressed"


def composite(pillars: list[dict[str, Any]]) -> dict[str, Any]:
    """Weighted mean over the pillars that could be read."""
    got = [p for p in pillars if p["score"] is not None]
    w = sum(p["weight"] for p in got)
    if not w:
        return {"score": None, "weight_covered": 0, "band": "not assessed",
                "read": "No pillar could be read."}
    score = sum(p["weight"] * p["score"] for p in got) / w
    band = band_for(score)
    missing = [p["label"] for p in pillars if p["score"] is None]
    read = f"{band.capitalize()} tape ({score:.0f}/100)."
    if missing:
        read += f" Scored on {w}% of the weight — {', '.join(missing)} not assessed."
    return {"score": round(score, 1), "weight_covered": w, "band": band, "read": read}


# ── I/O ──────────────────────────────────────────────────────────────────────
def ist_today() -> date:
    """NSE's date — the machine runs US Eastern."""
    return datetime.now(IST).date()


def index_groups() -> dict[str, list[str]]:
    """Index name -> constituent symbols, from the desk's cached NSE CSVs."""
    import nse_universe as nu
    import smallcap_universe as su

    def syms(rows):
        return [str(r["symbol"]).strip().upper() for r in rows if r.get("symbol")]

    n50 = syms(nu.fetch_constituents("nifty50"))
    n50_set = set(n50)
    n100 = syms(nu.fetch_constituents("nifty100"))
    n500_rows = nu.fetch_constituents("nifty500")
    groups: dict[str, list[str]] = {
        "NIFTY 50": n50,
        "NIFTY Next 50": [s for s in n100 if s not in n50_set],
        "NIFTY Midcap 150": syms(su._load_kind("midcap150")),
        "NIFTY Smallcap 250": syms(su._load_kind("smallcap250")),
        "NIFTY 500": syms(n500_rows),
    }
    by_sector: dict[str, list[str]] = {}
    for r in n500_rows:
        ind = (r.get("industry") or "").strip()
        if ind and r.get("symbol"):
            by_sector.setdefault(ind, []).append(str(r["symbol"]).strip().upper())
    for ind in sorted(by_sector):
        groups[f"NIFTY 500 · {ind}"] = by_sector[ind]
    return {k: v for k, v in groups.items() if v}


def fetch_history(symbols: list[str]) -> dict[str, pd.DataFrame]:
    """2y daily bars in one batched call (2y so the 200 EMA is warmed up)."""
    import trending_stocks as ts
    try:
        return ts._batch_history(symbols, period="2y")
    except Exception as e:
        log.warning("history fetch failed: %s", e)
        return {}


def fetch_index_frames() -> tuple[Any, Any]:
    """(NIFTY 50 2y, India VIX 1y)."""
    import market_health as mh
    return mh._fetch_index("^NSEI", "2y"), mh._fetch_index("^INDIAVIX", "1y")


def fetch_fii_long_share(max_back: int = 10) -> tuple[float | None, date | None]:
    """Latest FII index-futures long share, walking back from the IST date."""
    try:
        import participant_oi as po
    except Exception:
        return None, None
    d = ist_today()
    for i in range(max_back):
        day = d - timedelta(days=i)
        if day.weekday() >= 5:
            continue
        txt = po.fetch(day)
        rec = po.parse(txt) if txt else None
        share = po.index_futures_long_share(rec) if rec else None
        if share is not None:
            return share, day
    return None, None


def build(frames: dict[str, Any], groups: dict[str, list[str]], index_df, vix_df,
          fii_share: float | None, fii_date: date | None) -> dict[str, Any]:
    """Everything the page shows, from already-fetched inputs."""
    rows = breadth_table(groups, frames)
    n500 = next((r for r in rows if r["index"] == "NIFTY 500"), None)
    universe = {s: frames[s] for s in groups.get("NIFTY 500", []) if s in frames}
    pillars = [
        trend_pillar(index_df),
        breadth_pillar(n500["pct_above"] if n500 else None, advance_share(universe)),
        volume_pillar(up_volume_share(universe)),
        volatility_pillar(vix_df, index_df),
        flows_pillar(fii_share, fii_date),
    ]
    return {"rows": rows, "pillars": pillars, "composite": composite(pillars)}
