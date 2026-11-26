"""Pick replay — one past pick: the chart as it looked on the pick day beside
what the price did since (Recommendation Audit).

Pure: frame, footer text and scorecard. Reads nothing itself; the page passes
in cached bars from `rec_audit_job.bars_for`, so opening a replay never fetches.
Spec: docs/superpowers/specs/2026-11-26-pick-replay-design.md

Post-pick bars are those dated strictly after `rec_date`, the same cut
`rec_audit.episode_outcome` uses, so the pick-day panel can never show a bar
the desk could not have seen.
"""
from __future__ import annotations

import math

import pandas as pd

import rec_audit as ra

#: A "winner" for the replay picker: headline excess vs NIFTY 500 at or above this.
WIN_EXCESS_PCT = 5.0
#: Sessions of history drawn in the pick-day panel.
LOOKBACK = 60
#: Sessions in the volume average (relative volume = pick-day volume vs this).
VOL_AVG = 20
#: The audit looks for a stop/target hit over this many sessions (its longest horizon).
PLAN_SPAN = max(ra.HORIZONS)

_OHLCV = ["open", "high", "low", "close", "volume"]


def _num(v) -> float | None:
    """A float, or None for None / NaN / '' / anything non-numeric."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _text(v) -> str:
    """A display string, '' for None / NaN / 'nan' / 'None'."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    s = str(v).strip()
    return "" if s.lower() in ("nan", "none") else s


def _rs(v: float) -> str:
    return f"₹{v:,.2f}"


def _pc(v: float) -> str:
    return f"{v:+.2f}%"


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=[*_OHLCV, "ema20", "vol_avg"], index=pd.DatetimeIndex([]))


def replay_frame(ep, bars: pd.DataFrame | None, idx_bars: pd.DataFrame | None,
                 h: int = ra.HEADLINE_H, lookback: int = LOOKBACK) -> dict:
    """Everything the two panels and the footer need, for one episode row."""
    rec = pd.Timestamp(str(ep.get("rec_date"))[:10])
    sym = _text(ep.get("symbol")) or "this symbol"
    plan_entry = _num(ep.get("entry"))
    out: dict = {
        "pre": _empty(), "post": _empty(), "bench": None,
        "levels": {"plan_entry": plan_entry if plan_entry is not None else _num(ep.get("close")),
                   "entry_px": None, "stop": _num(ep.get("stop")),
                   "target": _num(ep.get("target")), "low20": None},
        "markers": {"entry_date": None, "best_date": None, "worst_date": None,
                    "plan_date": None, "window_end": None},
        "exit_px": None, "last_px": None, "rvol": None, "missing": None, "note": None,
    }
    if bars is None or bars.empty:
        out["missing"] = (f"No stored daily bars for {sym} around {rec.date()} — "
                          "the next audit run fetches them.")
        return out

    b = bars[_OHLCV].astype(float).sort_index().copy()
    b["ema20"] = b["close"].ewm(span=20, adjust=False).mean()      # causal: no future in pre
    b["vol_avg"] = b["volume"].rolling(VOL_AVG, min_periods=1).mean()
    hist, post = b[b.index <= rec], b[b.index > rec]
    if hist.empty:
        out["missing"] = f"No stored bars for {sym} on or before the pick day {rec.date()}."
        return out

    cut = _text(ep.get("data_suspect_date"))
    if cut:
        c = pd.Timestamp(cut[:10])
        post = post[post.index < c]
        out["note"] = (f"Bars from {c.date()} on are left out: a one-day move of "
                       f"≥{ra.SPLIT_SUSPECT_PCT:.0f}% looks like a split or bonus, "
                       "not a real return.")
    out["pre"], out["post"] = hist.tail(lookback), post

    prior = hist["volume"].iloc[:-1].tail(VOL_AVG)
    if len(prior) >= VOL_AVG and prior.mean() > 0:
        out["rvol"] = float(hist["volume"].iloc[-1] / prior.mean() * 100)
    low20 = _num(ep.get("low20_at_rec"))
    out["levels"]["low20"] = low20 if low20 is not None else float(hist["low"].tail(20).min())

    if post.empty:
        return out
    entry_px = float(post["open"].iloc[0])
    win = post.head(PLAN_SPAN)
    out["levels"]["entry_px"] = entry_px
    out["last_px"] = float(post["close"].iloc[-1])
    m = out["markers"]
    m["entry_date"] = post.index[0]
    m["best_date"], m["worst_date"] = win["high"].idxmax(), win["low"].idxmin()
    m["window_end"] = post.index[h - 1] if len(post) >= h else None

    po, n = ep.get("plan_outcome"), _num(ep.get("plan_sessions"))
    if po in ("target_first", "stop_first", "ambiguous") and n and int(n) <= len(post):
        i = int(n) - 1
        m["plan_date"] = post.index[i]
        o = float(post["open"].iloc[i])
        lvl = out["levels"]["target" if po == "target_first" else "stop"]
        if lvl is not None:   # a gap through the level fills at the open, not the level
            out["exit_px"] = max(lvl, o) if po == "target_first" else min(lvl, o)

    if idx_bars is not None and not idx_bars.empty:
        s = idx_bars["close"].astype(float).sort_index()
        s = s.reindex(s.index.union(post.index)).ffill().reindex(post.index)
        if not s.isna().any() and s.iloc[0] > 0:
            out["bench"] = s / s.iloc[0] * entry_px
    return out


def _plan_text(ep, f: dict) -> str:
    lv = f["levels"]
    if lv["stop"] is None:
        return "No plan"
    po, n = ep.get("plan_outcome"), _num(ep.get("plan_sessions"))
    day = f" day {int(n)}" if n else ""
    exit_ = ""
    if f["exit_px"] is not None and lv["entry_px"]:
        exit_ = (f" · exited {_rs(f['exit_px'])} "
                 f"({_pc(f['exit_px'] / lv['entry_px'] * 100 - 100)})")
    if po == "target_first":
        return f"Target hit{day}{exit_}"
    if po == "stop_first":
        return f"SL hit{day}{exit_}"
    if po == "ambiguous":
        return f"SL hit{day} (same bar as target){exit_}"
    if len(f["post"]) >= PLAN_SPAN:
        return f"Neither hit in {PLAN_SPAN} sessions"
    return "Neither hit yet"


def footer_line(ep, f: dict) -> str:
    """The owner's one-line result: `₹312.00 → ₹523.00 (+67.63%) · Target hit day 14 · …`."""
    if f["missing"]:
        return f["missing"]
    if f["post"].empty:
        px = _num(ep.get("close"))
        if px is None and not f["pre"].empty:
            px = float(f["pre"]["close"].iloc[-1])
        return f"Picked at {_rs(px)} · not entered yet" if px is not None else "Not entered yet"
    e, last = f["levels"]["entry_px"], f["last_px"]
    return f"{_rs(e)} → {_rs(last)} ({_pc(last / e * 100 - 100)}) · {_plan_text(ep, f)}"


def scorecard(eps: pd.DataFrame) -> dict[str, int]:
    """Plan results across `eps`. Ambiguous counts as SL hit, as the audit does."""
    if eps.empty:
        return {"total": 0, "target": 0, "sl": 0, "neither": 0, "no_plan": 0, "pending": 0}
    status = eps["status"].astype(str) if "status" in eps else pd.Series("", index=eps.index)
    pend = status.eq("pending")
    po = (eps["plan_outcome"] if "plan_outcome" in eps
          else pd.Series(None, index=eps.index, dtype=object))[~pend]
    t = int(po.eq("target_first").sum())
    s = int(po.isin(["stop_first", "ambiguous"]).sum())
    nh = int(po.eq("neither").sum())
    return {"total": len(eps), "target": t, "sl": s, "neither": nh,
            "no_plan": len(po) - t - s - nh, "pending": int(pend.sum())}


def scorecard_text(sc: dict) -> str:
    return (f"Total {sc['total']} · Target hit {sc['target']} · SL hit {sc['sl']} · "
            f"Neither {sc['neither']} · No plan {sc['no_plan']} · Pending {sc['pending']}")


def replay_candidates(eps: pd.DataFrame, kind: str, tag: str | None, h: int) -> pd.DataFrame:
    """Picks for the replay picker: losers worst first, winners best first, all newest first."""
    r, x = f"ret_{h}", f"excess_{h}"
    if eps.empty:
        return eps
    if kind == "losers":
        if r not in eps or "failure" not in eps:
            return eps.iloc[0:0]
        d = eps[eps["failure"].fillna(False).astype(bool) & eps[r].notna()]
        d = d.sort_values(x, na_position="last") if x in d else d
    elif kind == "winners":
        if x not in eps:
            return eps.iloc[0:0]
        d = eps[pd.to_numeric(eps[x], errors="coerce") >= WIN_EXCESS_PCT].sort_values(
            x, ascending=False)
    else:
        d = eps.sort_values("rec_date", ascending=False)
    if tag and "review_tag" in d:
        d = d[d["review_tag"] == tag]
    return d


def replay_label(r, h: int) -> str:
    ret = _num(r.get(f"ret_{h}"))
    head = f"{_text(r.get('symbol'))} · picked {str(r.get('rec_date'))[:10]}"
    return f"{head} · {h}d {ret:+.1f}%" if ret is not None else f"{head} · pending"
