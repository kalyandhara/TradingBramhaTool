"""rec_audit.py — what happened to every stock the desk recommended (A1).

Pure functions: no network, no DB. `rec_audit_job.py` feeds them prices and
stores the result. Design and rationale: trading-wiki
`analyses/Recommendation-Audit-Roadmap.md`.

Unit — the EPISODE
------------------
One stock's run on the list. `daily_opportunities` re-lists the same name day
after day and, before R0's weekday schedule, re-saved Friday's list on Saturday
and Sunday; counting rows would count one idea five times. So:
  * a run date maps to the last trading session on or before it (weekend → Fri);
  * a re-appearance within MERGE_GAP_DAYS of the previous one extends the
    episode; the first appearance supplies every attribute (rank, score, …).

Entry — the NEXT session's open
-------------------------------
The list is made after the close; the stored close was not tradable. Entry is
the open of the first session after the recommendation session.

Every return is also measured against benchmarks over the SAME dates (open on
the entry day → close on the exit day): NIFTY 500 (market), Smallcap 250 (the
size most picks live in) and the pick's sector index where one maps.
"""
from __future__ import annotations

import math
from datetime import date

import numpy as np
import pandas as pd

MERGE_GAP_DAYS = 14
HORIZONS: tuple[int, ...] = (5, 10, 21, 63)
#: The audit's headline horizon (sessions). A month of trading.
HEADLINE_H = 21
MATURE_H = HEADLINE_H

# ── Failure + post-mortem thresholds — every one an untested prior ───────────
FAIL_RET_PCT = -5.0          # raw 21-session return at or below this …
FAIL_EXCESS_PCT = -5.0       # … or excess vs NIFTY 500 at or below this
MARKET_FALL_PCT = -3.0       # benchmark fell at least this much over the window
DRAG_TOLERANCE_PCT = -2.0    # and the pick did no worse than this vs it
EVENT_GAP_PCT = -7.0         # one session's close-to-close at or below this
SETUP_FAIL_SESSIONS = 5      # broke stop / 20-day low within this many sessions
CHASED_ABOVE_EMA_PCT = 10.0  # rec close this far above EMA 20 = extended entry
ILLIQUID_TURNOVER_RS = 1e7   # 10-session average traded value below ₹1 Cr
#: A one-session move this large is read as an unadjusted corporate action
#: (split/bonus), not a price move: NSE circuit bands cap most stocks at ±20%.
#: HEG printed −62.6% on 2026-09-07 then traded on at the new level.
SPLIT_SUSPECT_PCT = 35.0
MIN_N = 30                   # attribution cells below this are "insufficient"

#: Primary-tag precedence: the first that applies explains the failure.
TAG_ORDER: tuple[str, ...] = ("NO_DATA", "MARKET_DRAG", "SECTOR_DRAG", "EVENT_GAP",
                              "SETUP_FAILED", "CHASED", "WARNING_IGNORED",
                              "ILLIQUID")
UNEXPLAINED = "STOCK_SPECIFIC"


# ──────────────────────────────────────────────────────────────────────────────
# Episodes
# ──────────────────────────────────────────────────────────────────────────────
def rec_session(run_date, sessions: pd.DatetimeIndex) -> pd.Timestamp | None:
    """Last session on or before `run_date` (a Saturday run → Friday)."""
    ts = pd.Timestamp(run_date)
    i = sessions.searchsorted(ts, side="right") - 1
    return sessions[i] if i >= 0 else None


def build_episodes(recs: pd.DataFrame, sessions: pd.DatetimeIndex,
                   source: str = "opportunity") -> pd.DataFrame:
    """Rows of (run_date, symbol, …) → one row per episode.

    Adds: episode_id, source, rec_date (session), last_rec_date, appearances.
    Attributes come from the episode's first appearance.
    """
    if recs.empty:
        return recs.assign(episode_id=[], source=[], rec_date=[],
                           last_rec_date=[], appearances=[])
    df = recs.copy()
    df["rec_date"] = [rec_session(d, sessions) for d in df["run_date"]]
    df = df.dropna(subset=["rec_date"])
    # One row per (symbol, session): a weekend re-save is the Friday pick again.
    df = (df.sort_values(["symbol", "rec_date", "run_date"])
            .drop_duplicates(["symbol", "rec_date"], keep="first"))
    gap = df.groupby("symbol")["rec_date"].diff().dt.days
    df["_new"] = gap.isna() | (gap > MERGE_GAP_DAYS)
    df["_ep"] = df.groupby("symbol")["_new"].cumsum()
    g = df.groupby(["symbol", "_ep"], sort=False)
    first = g.head(1).set_index(["symbol", "_ep"])
    first["last_rec_date"] = g["rec_date"].max()
    first["appearances"] = g.size()
    out = first.reset_index().drop(columns=["_ep", "_new"])
    out["source"] = source
    out["episode_id"] = (out["source"] + ":" + out["symbol"] + ":"
                         + pd.to_datetime(out["rec_date"]).dt.strftime("%Y-%m-%d"))
    return out.sort_values(["rec_date", "symbol"]).reset_index(drop=True)


# ──────────────────────────────────────────────────────────────────────────────
# One episode's outcome
# ──────────────────────────────────────────────────────────────────────────────
def _pct(a, b) -> float | None:
    if a is None or b is None or not b or pd.isna(a) or pd.isna(b):
        return None
    return (float(a) / float(b) - 1.0) * 100.0


def _window_ret(bars: pd.DataFrame | None, start: pd.Timestamp,
                end: pd.Timestamp) -> float | None:
    """Open on `start` → close on `end`; None when either session is missing."""
    if bars is None or bars.empty or start not in bars.index or end not in bars.index:
        return None
    return _pct(bars.at[end, "close"], bars.at[start, "open"])


def plan_outcome(after: pd.DataFrame, stop, target) -> tuple[str | None, int | None]:
    """First of stop/target touched, walking daily bars from the entry session.

    Returns (outcome, sessions_to_outcome). A bar that spans BOTH levels is
    'ambiguous' (daily bars cannot order them); stats count it as stop-first.
    """
    if stop is None or pd.isna(stop):
        return None, None
    has_target = target is not None and not pd.isna(target)
    for i, (_, b) in enumerate(after.iterrows(), 1):
        hit_stop = b["low"] <= stop
        hit_tgt = has_target and b["high"] >= target
        if hit_stop and hit_tgt:
            return "ambiguous", i
        if hit_stop:
            return "stop_first", i
        if hit_tgt:
            return "target_first", i
    return "neither", None


def episode_outcome(ep: pd.Series | dict, bars: pd.DataFrame | None,
                    market: pd.DataFrame | None, *, smallcap: pd.DataFrame | None = None,
                    sector: pd.DataFrame | None = None,
                    as_of: date | None = None) -> dict:
    """Everything the audit records about one episode. Never raises on thin data."""
    rec = pd.Timestamp(ep["rec_date"])
    out: dict = {"episode_id": ep["episode_id"]}
    if bars is not None and as_of is not None:
        bars = bars[bars.index <= pd.Timestamp(as_of)]
    after = bars[bars.index > rec] if bars is not None and not bars.empty else None
    if after is None or after.empty:
        # No session has opened since the pick (it was made on the audit date):
        # that is "not yet entered", not a missing stock.
        mk = market if market is None or as_of is None else market[market.index <= pd.Timestamp(as_of)]
        if mk is not None and not (mk.index > rec).any():
            out.update(status="pending", sessions=0)
        else:
            out.update(status="no_data", sessions=0)
        return out

    # Cut the window at a suspected corporate action: returns before it stand,
    # nothing after it is comparable. Too short to judge → set aside.
    rec_close = bars.loc[bars.index <= rec, "close"]
    path = pd.concat([rec_close.tail(1), after["close"]])
    jumps = path.pct_change().iloc[1:].abs() * 100
    bad = jumps[jumps >= SPLIT_SUSPECT_PCT]
    if not bad.empty:
        out["data_suspect_date"] = bad.index[0].date().isoformat()
        after = after[after.index < bad.index[0]]
        if after.empty:
            out.update(status="data_suspect", sessions=0)
            return out

    entry_day = after.index[0]
    entry_px = float(after["open"].iloc[0])
    status = "matured" if len(after) >= MATURE_H else "open"
    if not bad.empty and len(after) < MATURE_H:
        status = "data_suspect"
    out.update(entry_date=entry_day.date().isoformat(), entry_px=entry_px,
               sessions=len(after), status=status)

    for h in HORIZONS:
        if len(after) < h:
            continue
        exit_day = after.index[h - 1]
        out[f"ret_{h}"] = _pct(after["close"].iloc[h - 1], entry_px)
        m = _window_ret(market, entry_day, exit_day)
        s = _window_ret(smallcap, entry_day, exit_day)
        x = _window_ret(sector, entry_day, exit_day)
        out[f"mkt_{h}"] = m
        out[f"excess_{h}"] = None if m is None else out[f"ret_{h}"] - m
        out[f"excess_sc_{h}"] = None if s is None else out[f"ret_{h}"] - s
        out[f"excess_sec_{h}"] = None if x is None else out[f"ret_{h}"] - x
        out[f"sec_{h}"] = x

    out["ret_to_date"] = _pct(after["close"].iloc[-1], entry_px)
    win = after.head(max(HORIZONS))
    out["mfe"] = _pct(win["high"].max(), entry_px)
    out["mae"] = _pct(win["low"].min(), entry_px)
    out["days_to_mfe"] = int(np.argmax(win["high"].to_numpy())) + 1

    po, n_po = plan_outcome(after.head(max(HORIZONS)), ep.get("stop"), ep.get("target"))
    out["plan_outcome"], out["plan_sessions"] = po, n_po

    before = bars[bars.index <= rec]
    if len(before) >= 1:
        ema20 = before["close"].ewm(span=20, adjust=False).mean().iloc[-1]
        out["ext_vs_ema20"] = _pct(before["close"].iloc[-1], ema20)
        out["low20_at_rec"] = float(before["low"].tail(20).min())
        if "volume" in before:
            out["turnover10_at_rec"] = float(
                (before["close"] * before["volume"]).tail(10).mean())
    out["worst_day"] = (float(after["close"].head(max(HORIZONS)).pct_change().min() * 100)
                        if len(after) > 1 else None)
    out["broke_low20_by"] = (
        bool((after["close"].head(SETUP_FAIL_SESSIONS) < out["low20_at_rec"]).any())
        if "low20_at_rec" in out else None)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Post-mortem
# ──────────────────────────────────────────────────────────────────────────────
def _num(v) -> float | None:
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else v


def is_failure(o: dict, h: int = HEADLINE_H) -> bool:
    """A failure at horizon h: raw or excess return past its line, or the stop
    went first inside the horizon. Unmatured and data-suspect episodes are not judged."""
    if o.get("status") == "no_data":
        return True
    if o.get("status") == "data_suspect":
        return False
    ret, exc = _num(o.get(f"ret_{h}")), _num(o.get(f"excess_{h}"))
    if ret is None:
        return False
    stop_first = (o.get("plan_outcome") in ("stop_first", "ambiguous")
                  and (o.get("plan_sessions") or 10**9) <= h)
    return (ret <= FAIL_RET_PCT or (exc is not None and exc <= FAIL_EXCESS_PCT)
            or stop_first)


def postmortem_tags(ep: pd.Series | dict, o: dict, h: int = HEADLINE_H) -> list[str]:
    """Every tag that applies, in TAG_ORDER. Not exclusive; [0] is primary."""
    if o.get("status") == "no_data":
        return ["NO_DATA"]
    tags = []
    m, exc = _num(o.get(f"mkt_{h}")), _num(o.get(f"excess_{h}"))
    sec, exc_sec = _num(o.get(f"sec_{h}")), _num(o.get(f"excess_sec_{h}"))
    if m is not None and m <= MARKET_FALL_PCT and exc is not None and exc > DRAG_TOLERANCE_PCT:
        tags.append("MARKET_DRAG")
    if (sec is not None and sec <= MARKET_FALL_PCT and exc_sec is not None
            and exc_sec > DRAG_TOLERANCE_PCT):
        tags.append("SECTOR_DRAG")
    wd = _num(o.get("worst_day"))
    if wd is not None and wd <= EVENT_GAP_PCT:
        tags.append("EVENT_GAP")
    early_stop = (o.get("plan_outcome") in ("stop_first", "ambiguous")
                  and (o.get("plan_sessions") or 10**9) <= SETUP_FAIL_SESSIONS)
    if early_stop or o.get("broke_low20_by"):
        tags.append("SETUP_FAILED")
    ext = _num(o.get("ext_vs_ema20"))
    if ext is not None and ext > CHASED_ABOVE_EMA_PCT:
        tags.append("CHASED")
    if str(ep.get("risk_flags") or "").strip():
        tags.append("WARNING_IGNORED")
    t10 = _num(o.get("turnover10_at_rec"))
    if t10 is not None and t10 < ILLIQUID_TURNOVER_RS:
        tags.append("ILLIQUID")
    return tags


def primary_tag(tags: list[str]) -> str:
    return tags[0] if tags else UNEXPLAINED


# ──────────────────────────────────────────────────────────────────────────────
# Aggregates
# ──────────────────────────────────────────────────────────────────────────────
def t_stat(x: pd.Series) -> float | None:
    x = pd.to_numeric(x, errors="coerce").dropna()
    if len(x) < 2 or x.std(ddof=1) == 0:
        return None
    return float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x))))


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """Numeric column, or all-NaN when the column is absent (nothing matured)."""
    if name not in df:
        return pd.Series(float("nan"), index=df.index)
    return pd.to_numeric(df[name], errors="coerce")


def summarise(df: pd.DataFrame, h: int = HEADLINE_H) -> dict:
    """Headline numbers over episodes matured at horizon h."""
    r, e, esc = _col(df, f"ret_{h}"), _col(df, f"excess_{h}"), _col(df, f"excess_sc_{h}")
    m = r.notna()
    po = df.get("plan_outcome")
    plans = po[po.notna() & m] if po is not None else pd.Series(dtype=object)
    decided = plans[plans != "neither"]
    return {
        "h": h, "episodes": int(len(df)), "n": int(m.sum()),
        "no_data": int((df.get("status") == "no_data").sum()),
        "pending": int((df.get("status") == "pending").sum()),
        "data_suspect": int((df.get("status") == "data_suspect").sum()),
        "hit_rate": _rate(r[m] > 0),
        "beat_market_rate": _rate(e[e.notna()] > 0),
        "mean_ret": _f(r[m].mean()), "median_ret": _f(r[m].median()),
        "mean_excess": _f(e.mean()), "median_excess": _f(e.median()),
        "t_excess": t_stat(e),
        "median_excess_smallcap": _f(esc.median()), "t_excess_smallcap": t_stat(esc),
        **_weekly(df, e, esc),
        "median_mfe": _f(_col(df, "mfe")[m].median()),
        "median_mae": _f(_col(df, "mae")[m].median()),
        "plans": int(len(plans)),
        "target_first_rate": _rate(decided == "target_first") if len(decided) else None,
        "failures": int(df.get("failure", pd.Series(dtype=bool)).fillna(False).sum()),
    }


def _weekly(df: pd.DataFrame, e: pd.Series, esc: pd.Series) -> dict:
    """Significance with picks grouped by ENTRY WEEK. Picks entered the same week
    ride the same tape, so 483 August picks are ~8 observations, not 483; the
    per-pick t overstates confidence. This t is over weekly mean excesses."""
    if "entry_date" not in df:
        return {"weeks": 0, "t_excess_weekly": None, "t_excess_smallcap_weekly": None}
    wk = pd.to_datetime(df["entry_date"], errors="coerce").dt.to_period("W")
    w1 = e.groupby(wk).mean().dropna()
    w2 = esc.groupby(wk).mean().dropna()
    return {"weeks": int(len(w1)), "t_excess_weekly": t_stat(w1),
            "t_excess_smallcap_weekly": t_stat(w2)}


def _rate(mask: pd.Series) -> float | None:
    return round(float(mask.mean()) * 100, 1) if len(mask) else None


def _f(v) -> float | None:
    return None if v is None or pd.isna(v) else round(float(v), 2)


def attribution(df: pd.DataFrame, by: str, h: int = HEADLINE_H,
                min_n: int = MIN_N) -> pd.DataFrame:
    """Median/mean excess, hit rate, n and t per value of `by`. Multi-valued
    text columns (comma lists like family_names) count an episode once per value."""
    col = f"excess_{h}"
    d = df[df[col].notna()].copy() if col in df else df.iloc[0:0]
    if d.empty or by not in d:
        return pd.DataFrame(columns=[by, "n", "median_excess", "mean_excess",
                                     "beat_market_rate", "t", "sufficient"])
    if (not pd.api.types.is_numeric_dtype(d[by])
            and d[by].astype(str).str.contains(",").any()):
        d = d.assign(**{by: d[by].fillna("").astype(str).str.split(r",\s*")}).explode(by)
    d[by] = d[by].fillna("(none)").replace("", "(none)")
    rows = []
    for key, g in d.groupby(by):
        e = pd.to_numeric(g[col], errors="coerce")
        rows.append({by: key, "n": len(g), "median_excess": _f(e.median()),
                     "mean_excess": _f(e.mean()), "beat_market_rate": _rate(e > 0),
                     "t": None if t_stat(e) is None else round(t_stat(e), 2),
                     "sufficient": len(g) >= min_n})
    return pd.DataFrame(rows).sort_values("n", ascending=False).reset_index(drop=True)


def cohorts(df: pd.DataFrame) -> pd.DataFrame:
    """Recommendation month × horizon: n, median excess, beat-market rate."""
    if df.empty:
        return pd.DataFrame()
    d = df.assign(month=pd.to_datetime(df["rec_date"]).dt.to_period("M").astype(str))
    rows = []
    for mth, g in d.groupby("month"):
        row = {"month": mth, "episodes": len(g)}
        for h in HORIZONS:
            e = _col(g, f"excess_{h}").dropna()
            row[f"n_{h}"] = len(e)
            row[f"med_excess_{h}"] = _f(e.median()) if len(e) else None
            row[f"beat_{h}"] = _rate(e > 0) if len(e) else None
        rows.append(row)
    return pd.DataFrame(rows)


def paper_portfolio(df: pd.DataFrame, bars: dict[str, pd.DataFrame],
                    market: pd.DataFrame, hold: int = HEADLINE_H) -> pd.DataFrame:
    """₹1 into every episode at its entry open, held `hold` sessions, then left
    in cash at its exit value. A shadow ₹1 goes into the market over the SAME
    dates. Returns date-indexed average P&L per rupee deployed so far
    (`basket`, `market`, as 1 + return) and `active` positions.

    Buy-and-hold per position, not a daily-rebalanced basket: rebalancing a
    basket of volatile small caps every day bleeds (volatility drag) and would
    not match the per-episode returns the rest of the audit reports — the
    first backfill showed −14% for that basket against a +1.2% median excess.
    """
    paths, shadows = [], []
    for _, ep in df.iterrows():
        b = bars.get(ep["symbol"])
        if b is None or pd.isna(ep.get("entry_date")):
            continue
        start = pd.Timestamp(ep["entry_date"])
        held = b[b.index >= start].head(hold)
        mk = market[market.index >= start].head(len(held))
        if held.empty or mk.empty:
            continue
        paths.append(held["close"] / held["open"].iloc[0])
        shadows.append(mk["close"] / mk["open"].iloc[0])
    if not paths:
        return pd.DataFrame(columns=["basket", "market", "active"])
    idx = market.index[(market.index >= min(p.index[0] for p in paths))
                       & (market.index <= max(p.index[-1] for p in paths))]

    def _avg(series: list[pd.Series]) -> pd.Series:
        # Before entry: not deployed (NaN, excluded). After exit: frozen value.
        m = pd.concat([s.reindex(idx).where(idx >= s.index[0]).ffill()
                       .where(idx >= s.index[0]) for s in series], axis=1)
        return m.mean(axis=1)

    active = pd.concat([pd.Series(1, index=p.index).reindex(idx) for p in paths],
                       axis=1).sum(axis=1)
    return pd.DataFrame({"basket": _avg(paths), "market": _avg(shadows),
                         "active": active.astype(int)})


def max_drawdown(equity: pd.Series) -> float | None:
    if equity is None or equity.empty:
        return None
    return _f(((equity / equity.cummax()) - 1).min() * 100)
