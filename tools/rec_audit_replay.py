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

#: A plan level further than this from the pick-day close is listed, not drawn —
#: one stale level (RAYMOND's ₹2,460 entry vs a ~₹600 price) flattens the panel.
OFF_CHART_PCT = 50.0

_OHLCV = ["open", "high", "low", "close", "volume"]
_LEVEL_LABELS = {"plan_entry": "entry", "stop": "stop", "target": "target", "low20": "20-day low"}


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
        "off_chart": {},
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
    ref = float(hist["close"].iloc[-1])
    if ref > 0:
        out["off_chart"] = {lbl: v for k, lbl in _LEVEL_LABELS.items()
                            if (v := out["levels"][k]) is not None
                            and abs(v / ref - 1) * 100 > OFF_CHART_PCT}

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


def _candles(d: pd.DataFrame, name: str, opacity: float = 1.0):
    import plotly.graph_objects as go
    return go.Candlestick(x=d.index, open=d["open"], high=d["high"], low=d["low"],
                          close=d["close"], name=name, opacity=opacity, showlegend=False)


def _volume(fig, d: pd.DataFrame, col: int, T: dict) -> None:
    import plotly.graph_objects as go
    colours = [T["good"] if c >= o else T["risk"] for o, c in zip(d["open"], d["close"])]
    fig.add_trace(go.Bar(x=d.index, y=d["volume"], marker_color=colours, opacity=0.6,
                         name="volume", showlegend=False), row=2, col=col)
    fig.add_trace(go.Scatter(x=d.index, y=d["vol_avg"], mode="lines", name="20-session avg volume",
                             line=dict(color=T["text_muted"], width=1), showlegend=False),
                  row=2, col=col)


def _levels(fig, lv: dict, col: int, T: dict, entry_key: str, entry_label: str) -> None:
    for key, label, colour in ((entry_key, entry_label, T["accent"]), ("stop", "stop", T["risk"]),
                               ("target", "target", T["good"]), ("low20", "20-day low", T["text_muted"])):
        if lv.get(key) is not None:
            fig.add_hline(y=lv[key], line=dict(color=colour, width=1, dash="dash"), row=1, col=col,
                          annotation_text=f"{label} {_rs(lv[key])}",
                          annotation_font=dict(size=10, color=colour),
                          annotation_position="top left")


def replay_figure(f: dict, ep, h: int = ra.HEADLINE_H):
    """Two panels with volume under each: Pick day (bars up to rec_date only) and
    Since then (faded pre-pick bars + everything after, the headline window shaded,
    markers for best / worst / plan hit, NIFTY 500 rebased to the entry)."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    import report_style as rs
    T = rs.TOKENS
    pre, post, m = f["pre"], f["post"], f["markers"]
    lv = {k: (None if _LEVEL_LABELS.get(k) in f.get("off_chart", {}) else v)
          for k, v in f["levels"].items()}
    rec = str(ep.get("rec_date"))[:10]
    right = f"Since then · to {post.index[-1].date()}" if not post.empty else "Since then"
    fig = make_subplots(rows=2, cols=2, shared_xaxes="columns", row_heights=[0.75, 0.25],
                        column_widths=[0.4, 0.6], horizontal_spacing=0.04, vertical_spacing=0.03,
                        subplot_titles=(f"Pick day · {rec}", right, "", ""))
    if not pre.empty:
        fig.add_trace(_candles(pre, "pick day"), row=1, col=1)
        fig.add_trace(go.Scatter(x=pre.index, y=pre["ema20"], mode="lines", name="20 EMA",
                                 line=dict(color=T["info"], width=1), showlegend=False),
                      row=1, col=1)
        _volume(fig, pre, 1, T)
        _levels(fig, lv, 1, T, "plan_entry", "entry")

    if post.empty:
        fig.add_annotation(xref="x2 domain", yref="y2 domain", x=0.5, y=0.5, showarrow=False,
                           text="Since then: not entered yet — no session since the pick",
                           font=dict(color=T["text_muted"]))
    else:
        both = pd.concat([pre, post])
        fig.add_trace(_candles(pre, "before pick", opacity=0.35), row=1, col=2)
        fig.add_trace(_candles(post, "since pick"), row=1, col=2)
        fig.add_trace(go.Scatter(x=both.index, y=both["ema20"], mode="lines", name="20 EMA",
                                 line=dict(color=T["info"], width=1), showlegend=False),
                      row=1, col=2)
        _volume(fig, both, 2, T)
        _levels(fig, {**lv, "low20": None}, 2, T, "entry_px", "entry")
        x1 = m["window_end"] if m["window_end"] is not None else post.index[-1]
        fig.add_vrect(x0=m["entry_date"], x1=x1, fillcolor=T["info"], opacity=0.08, line_width=0,
                      row=1, col=2, annotation_text=f"{h}-session window",
                      annotation_position="top left", annotation_font=dict(size=10))
        fig.add_vline(x=m["entry_date"], line=dict(color=T["accent"], width=1, dash="dot"),
                      row=1, col=2)
        if f["bench"] is not None:
            fig.add_trace(go.Scatter(x=f["bench"].index, y=f["bench"], mode="lines",
                                     name="NIFTY 500 (rebased)",
                                     line=dict(color=T["text_muted"], width=1.5, dash="dot")),
                          row=1, col=2)
        pts = [("best", m["best_date"], "high", "triangle-up", T["good"]),
               ("worst", m["worst_date"], "low", "triangle-down", T["risk"])]
        for name, d, field, sym, colour in pts:
            if d is not None:
                fig.add_trace(go.Scatter(x=[d], y=[post.at[d, field]], mode="markers", name=name,
                                         marker=dict(symbol=sym, size=11, color=colour)),
                              row=1, col=2)
        if m["plan_date"] is not None:
            hit_target = ep.get("plan_outcome") == "target_first"
            y = f["exit_px"] if f["exit_px"] is not None else post.at[m["plan_date"], "close"]
            fig.add_trace(go.Scatter(x=[m["plan_date"]], y=[y], mode="markers",
                                     name="target hit" if hit_target else "SL hit",
                                     marker=dict(symbol="x", size=12,
                                                 color=T["good"] if hit_target else T["risk"])),
                          row=1, col=2)

    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])], rangeslider_visible=False)
    fig.update_layout(height=620, margin=dict(l=10, r=10, t=40, b=10),
                      legend=dict(orientation="h", y=-0.05), hovermode="x unified")
    return fig


def replay_label(r, h: int) -> str:
    ret = _num(r.get(f"ret_{h}"))
    head = f"{_text(r.get('symbol'))} · picked {str(r.get('rec_date'))[:10]}"
    return f"{head} · {h}d {ret:+.1f}%" if ret is not None else f"{head} · pending"
