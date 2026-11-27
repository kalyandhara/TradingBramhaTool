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
        # The audit's excess is measured from the index's entry-day OPEN
        # (rec_audit._window_ret); start the line there so chart and number agree.
        base = (_num(idx_bars["open"].get(post.index[0])) if "open" in idx_bars else None) \
            or _num(s.iloc[0])
        if not s.isna().any() and base and base > 0:
            out["bench"] = s / base * entry_px
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
        status = _text(ep.get("status"))
        tail = ("not entered yet" if status in ("", "pending")
                else f"no usable session since the pick ({status})")
        return f"Picked at {_rs(px)} · {tail}" if px is not None else tail[0].upper() + tail[1:]
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


def group_by_ticker(eps: pd.DataFrame) -> pd.DataFrame:
    """One row per ticker for the card views (spec 2026-11-27): the first row, in
    the incoming order, among the ticker's latest pick date. Adds `scanners_all`
    (every scanner that fired on that date), `earlier_dates` (its other pick
    dates, newest first) and `n_picks`. Statistics never use this — per-scanner
    attribution needs every pick."""
    if eps.empty or "symbol" not in eps:
        return eps.assign(scanners_all=[], earlier_dates=[], n_picks=[]) if eps.empty else eps
    day = (eps["rec_date"].astype(str).str[:10] if "rec_date" in eps
           else pd.Series("", index=eps.index))
    latest = day.groupby(eps["symbol"]).transform("max")
    on_latest = eps[day == latest]
    keep = on_latest[~on_latest["symbol"].duplicated()].copy()
    if "scanner" in eps:
        names = on_latest.groupby("symbol")["scanner"].agg(
            lambda s: ", ".join(dict.fromkeys(_text(x) for x in s if _text(x))))
        keep["scanners_all"] = keep["symbol"].map(names).fillna("")
    else:
        keep["scanners_all"] = ""
    older = (pd.DataFrame({"symbol": eps["symbol"], "day": day})[day != latest]
             .drop_duplicates().sort_values("day", ascending=False)
             .groupby("symbol")["day"].agg(", ".join))
    keep["earlier_dates"] = keep["symbol"].map(older).fillna("")
    keep["n_picks"] = keep["symbol"].map(eps["symbol"].value_counts()).astype(int)
    return keep


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
    d = group_by_ticker(d)          # one entry per ticker, at its latest pick
    if tag and "review_tag" in d:
        d = d[d["review_tag"] == tag]
    # Keyed by episode_id so a picker's stored choice means the same pick after a
    # source switch or an audit re-run (row positions shift; ids do not).
    return d.set_index("episode_id", drop=False) if "episode_id" in d else d


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
    sym = _text(ep.get("symbol"))
    who = f"{sym} · " if sym else ""
    right = (f"{who}Since then · to {post.index[-1].date()}" if not post.empty
             else f"{who}Since then")
    fig = make_subplots(rows=2, cols=2, shared_xaxes="columns", row_heights=[0.75, 0.25],
                        column_widths=[0.4, 0.6], horizontal_spacing=0.04, vertical_spacing=0.03,
                        subplot_titles=(f"{who}Pick day · {rec}", right, "", ""))
    if not pre.empty:
        fig.add_trace(_candles(pre, "pick day"), row=1, col=1)
        fig.add_trace(go.Scatter(x=pre.index, y=pre["ema20"], mode="lines", name="20 EMA",
                                 line=dict(color=T["info"], width=1), showlegend=False),
                      row=1, col=1)
        _volume(fig, pre, 1, T)
        _levels(fig, lv, 1, T, "plan_entry", "entry")

    if post.empty:
        # paper coords: a "x2 domain" ref on the empty panel fell back to the left
        # panel's data axes in the browser and stretched them to 1970 / 0.
        fig.add_annotation(xref="paper", yref="paper", x=0.71, y=0.62, showarrow=False,
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


# ── Decision snapshot, verdict, MFE/MAE ladder ───────────────────────────────
#: Process (how the pick was made) and outcome (what the market did) are judged
#: separately. Process uses only what was known on the pick day, with the audit's
#: own post-mortem thresholds (rec_audit), so nothing new is invented here.
def process_checks(ep) -> list[tuple[bool, str]]:
    """Pick-day process checks; a reading the pick did not record is skipped."""
    out = []
    stop = _num(ep.get("stop"))
    if stop is not None:
        out.append((True, "Plan had a stop"))
    elif _text(ep.get("plan_source")):
        out.append((False, "No stop in the plan"))
    # else: no plan was recorded (picks before 2026-10-22) — unknown, not a failure
    ext = _num(ep.get("ext_vs_ema20"))
    if ext is not None:
        out.append((True, f"Entry not chased ({ext:+.1f}% vs the 20 EMA)")
                   if ext <= ra.CHASED_ABOVE_EMA_PCT
                   else (False, f"Entry chased: {ext:+.1f}% above the 20 EMA"))
    flags = _text(ep.get("risk_flags"))
    out.append((False, f"Risk flag ignored: {flags}") if flags
               else (True, "No risk flag at pick"))
    t10 = _num(ep.get("turnover10_at_rec"))
    if t10 is not None:
        cr = t10 / 1e7
        out.append((True, f"Liquid (₹{cr:,.1f} Cr/day)") if t10 >= ra.ILLIQUID_TURNOVER_RS
                   else (False, f"Illiquid: ₹{cr:,.1f} Cr/day"))
    return out


_COLOUR_LABEL = {"green": "SUCCESS", "amber": "MIXED", "red": "FAILED"}


def verdict(ep, f: dict, h: int = ra.HEADLINE_H) -> dict:
    """Thesis / process / outcome, judged apart, and the Green-Amber-Red colour:
    green = thesis and process right, red = both wrong, amber = mixed."""
    ret, exc = _num(ep.get(f"ret_{h}")), _num(ep.get(f"excess_{h}"))
    checks = process_checks(ep)
    process_ok = all(ok for ok, _ in checks)
    items: list[tuple[bool, str]] = []
    if exc is not None:
        items.append((exc > 0, "THESIS_CORRECT" if exc > 0 else "THESIS_WRONG"))
    items.append((process_ok, "PROCESS_CORRECT" if process_ok else "PROCESS_FLAWED"))
    if ret is not None:
        items.append((ret > 0, "OUTCOME_POSITIVE" if ret > 0 else "OUTCOME_NEGATIVE"))
    stop = []
    if ep.get("plan_outcome") in ("stop_first", "ambiguous") and f["exit_px"] is not None:
        last = f["last_px"]
        saved = last is not None and f["exit_px"] >= last
        note = (f"exited {_rs(f['exit_px'])}; now {_rs(last)}"
                + (" — the stop protected capital" if saved
                   else " — price recovered above the exit") if last is not None else "")
        stop.append((saved, "STOP_EXECUTED", note))
    if exc is None:
        label = "PENDING" if f["post"].empty else "OPEN"
        colour = "grey"
    else:
        colour = ("green" if exc > 0 and process_ok else
                  "red" if exc <= 0 and not process_ok else "amber")
        label = _COLOUR_LABEL[colour]
    return {"colour": colour, "label": label, "items": items, "checks": checks, "stop": stop}


def snapshot(ep, f: dict, h: int = ra.HEADLINE_H) -> dict:
    """The executive-summary numbers for one pick."""
    v = verdict(ep, f, h)
    e, last = f["levels"]["entry_px"], f["last_px"]
    n, last_on = _num(ep.get("appearances")), _text(ep.get("last_rec_date"))[:10]
    shortlist = (f"{int(n)} run{'s' if int(n) != 1 else ''}" + (f" · last {last_on}" if last_on else "")
                 if n else "")
    rank = _num(ep.get("rank"))
    return {"outcome": v["label"], "colour": v["colour"],
            "rank": int(rank) if rank is not None else None, "shortlist": shortlist,
            "entry": e, "current": last,
            "to_date": (last / e * 100 - 100) if e and last is not None else None,
            "ret_h": _num(ep.get(f"ret_{h}")), "vs_n500": _num(ep.get(f"excess_{h}")),
            "vs_sector": _num(ep.get(f"excess_sec_{h}"))}


def excursion_insight(ep, entry_px: float | None = None) -> str:
    """One plain line from the best (MFE) and worst (MAE) move after entry."""
    mfe, mae = _num(ep.get("mfe")), _num(ep.get("mae"))
    if mfe is None or mae is None:
        return ""
    tgt, e = _num(ep.get("target")), entry_px or _num(ep.get("entry"))
    tgt_pct = (tgt / e * 100 - 100) if tgt is not None and e else None
    if mfe < 2.0:
        return f"Never got going: the best was {mfe:+.1f}% before a worst of {mae:+.1f}%."
    if tgt_pct is not None and mfe >= tgt_pct:
        return f"Reached the target zone ({mfe:+.1f}% vs a {tgt_pct:+.1f}% target)."
    d = _num(ep.get("days_to_mfe"))
    return f"Best {mfe:+.1f}%" + (f" on day {int(d)}" if d else "") + f", worst {mae:+.1f}%."


def excursion_figure(ep, f: dict):
    """MFE / MAE ladder: % from the entry, with the plan's target and stop."""
    import plotly.graph_objects as go

    import report_style as rs
    T = rs.TOKENS
    e = f["levels"]["entry_px"]
    fig = go.Figure()
    pts = [("MFE", _num(ep.get("mfe")), "triangle-up", T["good"]),
           ("MAE", _num(ep.get("mae")), "triangle-down", T["risk"]),
           ("now", (f["last_px"] / e * 100 - 100) if e and f["last_px"] is not None else None,
            "circle", T["info"])]
    for name, y, sym, colour in pts:
        if y is not None:
            fig.add_trace(go.Scatter(x=[0], y=[y], mode="markers+text", name=name,
                                     text=[f"{name} {y:+.1f}%"], textposition="middle right",
                                     marker=dict(symbol=sym, size=13, color=colour)))
    fig.add_hline(y=0, line=dict(color=T["text_muted"], width=1),
                  annotation_text="entry", annotation_position="top right")
    for key, label, colour in (("target", "target", T["good"]), ("stop", "stop", T["risk"])):
        lvl = f["levels"].get(key)
        if lvl is not None and e and key not in {_LEVEL_LABELS.get(k) for k in f["off_chart"]}:
            fig.add_hline(y=lvl / e * 100 - 100, line=dict(color=colour, width=1, dash="dash"),
                          annotation_text=f"{label} {lvl / e * 100 - 100:+.1f}%",
                          annotation_position="top right")
    fig.update_layout(height=300, showlegend=False, margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(visible=False, range=[-0.5, 2]),
                      yaxis=dict(ticksuffix="%", zeroline=False))
    return fig


# ── Lessons engine ───────────────────────────────────────────────────────────
#: Lessons are read from the stored audit row alone (no bars), so they aggregate
#: over every pick instantly. Thresholds are the audit's own post-mortem priors
#: (rec_audit) — untested, like them. Breadth is not stored historically, so the
#: market lesson uses NIFTY 500's own move over the window instead.
#: Entry within this % of the pick-day close counts as respected (a desk rule).
#: 2% was tried first: half of all picks gap that much overnight, equally often
#: in winners and losers (lift 1.0) — small-cap noise, so the line is 5%.
ENTRY_GAP_PCT = 5.0
#: Lessons that restate the audit's failure test rather than explain it.
DEFINITIONAL = {"RS_COLLAPSED": "part of the failure definition (excess ≤ −5%), "
                                "so it cannot explain failures",
                "STOPPED_THEN_RECOVERED": "a stop hit inside the window is itself a "
                                          "failure, so this is mostly losers by construction"}
#: Best move at least this large, then a loss at the window = a gain given back.
GAVE_BACK_MFE_PCT = 10.0
#: Best move below this = the setup never got going.
NEVER_WORKED_MFE_PCT = 2.0

LESSON_NAMES = {
    "ENTRY_RESPECTED": "Entry respected", "ENTRY_GAPPED": "Entry gapped away from the pick",
    "RS_HELD": "Held relative strength", "RS_COLLAPSED": "Relative strength collapsed",
    "SECTOR_HELD": "Sector held up", "SECTOR_ROLLED_OVER": "Sector rolled over",
    "MARKET_HELD": "Market held up", "MARKET_FELL": "Market fell (NIFTY 500)",
    "NEVER_WORKED": "Never worked from day one", "GAVE_BACK_GAIN": "Gave back a big gain",
    "ONE_DAY_SHOCK": "One-day shock", "STOP_PROTECTED": "Stop protected capital",
    "STOPPED_THEN_RECOVERED": "Stopped out, then recovered",
    "CHASED": "Entry chased", "WARNING_IGNORED": "Risk flag ignored",
    "ILLIQUID": "Illiquid", "NO_STOP": "No stop in the plan",
}


def _lesson(lid: str, ok: bool, text: str) -> dict:
    return {"id": lid, "ok": ok, "text": text}


def lessons(ep, h: int = ra.HEADLINE_H) -> list[dict]:
    """Machine-readable lessons for one judged pick: [{id, ok, text}], ✓ and ✗.
    [] until the pick has a headline return."""
    ret, e = _num(ep.get(f"ret_{h}")), _num(ep.get("entry_px"))
    if ret is None or not e:
        return []
    out = []
    c = _num(ep.get("close"))
    # a gap past the split/bonus line means the stored close is bad data, not a gap
    if c and abs(e / c * 100 - 100) < ra.SPLIT_SUSPECT_PCT:
        gap = e / c * 100 - 100
        out.append(_lesson("ENTRY_RESPECTED", True,
                           f"Entry respected: opened {gap:+.1f}% vs the pick-day close")
                   if abs(gap) <= ENTRY_GAP_PCT else
                   _lesson("ENTRY_GAPPED", False,
                           f"Entry gapped {gap:+.1f}% vs the pick-day close"))
    for lid_ok, lid_bad, v, line, what in (
            ("RS_HELD", "RS_COLLAPSED", _num(ep.get(f"excess_{h}")), ra.FAIL_EXCESS_PCT,
             "vs NIFTY 500"),
            ("SECTOR_HELD", "SECTOR_ROLLED_OVER", _num(ep.get(f"sec_{h}")),
             ra.MARKET_FALL_PCT, "sector index"),
            ("MARKET_HELD", "MARKET_FELL", _num(ep.get(f"mkt_{h}")), ra.MARKET_FALL_PCT,
             "NIFTY 500")):
        if v is None:
            continue
        if v <= line:
            out.append(_lesson(lid_bad, False, f"{LESSON_NAMES[lid_bad]} ({what} {v:+.1f}%)"))
        elif v >= 0:
            out.append(_lesson(lid_ok, True, f"{LESSON_NAMES[lid_ok]} ({what} {v:+.1f}%)"))
    mfe, wd = _num(ep.get("mfe")), _num(ep.get("worst_day"))
    if mfe is not None and mfe < NEVER_WORKED_MFE_PCT:
        out.append(_lesson("NEVER_WORKED", False,
                           f"Never worked from day one (best {mfe:+.1f}%)"))
    if mfe is not None and mfe >= GAVE_BACK_MFE_PCT and ret <= 0:
        out.append(_lesson("GAVE_BACK_GAIN", False,
                           f"Gave back a {mfe:+.1f}% gain ({h}d {ret:+.1f}%)"))
    if wd is not None and wd <= ra.EVENT_GAP_PCT:
        out.append(_lesson("ONE_DAY_SHOCK", False, f"One-day shock ({wd:+.1f}% in a session)"))
    stop, rtd = _num(ep.get("stop")), _num(ep.get("ret_to_date"))
    if ep.get("plan_outcome") in ("stop_first", "ambiguous") and stop is not None \
            and rtd is not None:
        sp = stop / e * 100 - 100
        out.append(_lesson("STOP_PROTECTED", True,
                           f"Stop protected capital (exit ≈{sp:+.1f}% vs {rtd:+.1f}% now)")
                   if rtd < sp else
                   _lesson("STOPPED_THEN_RECOVERED", False,
                           f"Stopped out at ≈{sp:+.1f}%, then recovered to {rtd:+.1f}%"))
    for ok, label in process_checks(ep):
        if ok:
            continue
        lid = ("NO_STOP" if label.startswith("No stop") else "CHASED" if "chased" in label
               else "WARNING_IGNORED" if label.startswith("Risk flag") else "ILLIQUID")
        out.append(_lesson(lid, False, label))
    return out


def lesson_table(eps: pd.DataFrame, h: int = ra.HEADLINE_H) -> pd.DataFrame:
    """The learning database: each ✗ lesson's share of all judged picks, of losers
    (audit failures) and of winners. A lesson as common among winners as losers
    is not what sank the losers — `lift` = share of losers / share of winners."""
    cols = ["id", "lesson", "picks", "pct_all", "pct_losers", "pct_winners", "lift", "note"]
    if eps.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    for _, r in eps.iterrows():
        ls = lessons(r, h)
        if ls:
            fail = bool(r.get("failure")) if pd.notna(r.get("failure")) else False
            rows.append((fail, {x["id"] for x in ls if not x["ok"]}))
    if not rows:
        return pd.DataFrame(columns=cols)
    n, nl = len(rows), sum(f for f, _ in rows)
    nw = n - nl
    ids = sorted({i for _, s in rows for i in s})
    out = []
    for i in ids:
        k = sum(i in s for _, s in rows)
        kl = sum(i in s for f, s in rows if f)
        pl = kl / nl * 100 if nl else None
        pw = (k - kl) / nw * 100 if nw else None
        out.append({"id": i, "lesson": LESSON_NAMES.get(i, i), "picks": k,
                    "pct_all": k / n * 100, "pct_losers": pl, "pct_winners": pw,
                    "lift": (pl / pw) if pl is not None and pw else None,
                    "note": DEFINITIONAL.get(i, "")})
    return (pd.DataFrame(out, columns=cols)
            .sort_values(["pct_losers", "pct_all"], ascending=False, na_position="last")
            .reset_index(drop=True))


def lessons_jsonl(eps: pd.DataFrame, h: int = ra.HEADLINE_H) -> str:
    """One JSON object per pick: episode_id, symbol, rec_date, lessons."""
    import json
    return "\n".join(json.dumps({"episode_id": _text(r.get("episode_id")),
                                 "symbol": _text(r.get("symbol")),
                                 "rec_date": str(r.get("rec_date"))[:10],
                                 "lessons": lessons(r, h)}, ensure_ascii=False)
                     for _, r in eps.iterrows())


# ── Multi-Chart dual replay link ─────────────────────────────────────────────
#: The chart tool (chart_server) — same convention as ui_tables.chart_url.
CHART_BASE = "http://localhost:5001/"


def multichart_url(ep, f: dict, ddate: str | None = None) -> str:
    """Deep link opening the pick in the Multi-Chart as two panes: the chart as it
    stood on the pick day, and everything since (replay_mode.js reads these)."""
    from urllib.parse import urlencode

    import rec_audit_job as job
    lv, off = f["levels"], f["off_chart"]
    q = {"symbol": _text(ep.get("symbol")), "exchange": "NSE", "tf": "1d",
         "layout": "replay", "replay": str(ep.get("rec_date"))[:10]}
    for key, name in (("plan_entry", "entry"), ("stop", "stop"), ("target", "target")):
        if lv.get(key) is not None and _LEVEL_LABELS[key] not in off:
            q[name] = f"{lv[key]:.2f}"
    if f["markers"]["plan_date"] is not None:
        q["sdate"] = f["markers"]["plan_date"].date().isoformat()
        q["skind"] = "T" if ep.get("plan_outcome") == "target_first" else "S"
    sector = job.SECTOR_INDEX.get(_text(ep.get("sector")))
    if sector:
        q["sector"] = sector
    rank = _num(ep.get("rank"))
    if rank is not None:
        q["rank"] = str(int(rank))
    label = _text(ep.get("family_names")) or _text(ep.get("scanners"))
    if label:
        q["label"] = label[:80]
    if ddate:                       # first session the re-score flagged a downgrade
        q["ddate"] = str(ddate)[:10]
    import ui_tables as uit         # the chart's Back button returns to the audit
    q["back"] = uit.page_link("Recommendation Audit")
    return CHART_BASE + "?" + urlencode(q)


def replay_label(r, h: int) -> str:
    ret = _num(r.get(f"ret_{h}"))
    head = f"{_text(r.get('symbol'))} · picked {str(r.get('rec_date'))[:10]}"
    return f"{head} · {h}d {ret:+.1f}%" if ret is not None else f"{head} · pending"


# ── Re-score: drift, attribution, decay ──────────────────────────────────────
#: Read from `pick_scores` (rec_rescore_job), which accrues forward from the first
#: nightly run; nothing here estimates a past evening. Spec:
#: docs/superpowers/specs/2026-11-26-pick-rescore-design.md §4
#: (key, label, max) — each part's weight comes from rating.OVERALL_WEIGHTS at call
#: time, so "led the drop" follows any retuning of the rating.
_PARTS = (("minervini", "Minervini", 8), ("technofunda", "TechnoFunda", 6))
_CHECK_NAMES = (("cs_near_high", "near high"), ("cs_volume", "volume"),
                ("cs_market", "market"), ("cs_rs", "RS leader"))


def _signed(v: float) -> str:
    v = int(round(v))
    return "0" if v == 0 else (f"+{v}" if v > 0 else f"−{-v}")


def drift_line(ep, scores: pd.DataFrame, pick_uni: dict | None) -> str:
    """`Rating drift −18 (72 → 54) · rank #9 → #146 of 500 · tracking since …`."""
    if scores is None or scores.empty:
        return "Re-score tracking starts with the next nightly run."
    s = scores.sort_values("session_date")
    last, first = s.iloc[-1], str(s["session_date"].iloc[0])[:10]
    now, pick = _num(last.get("rating")), _num(ep.get("overall_rating"))
    head = (f"Rating {int(now)} (no pick-day rating)" if pick is None
            else f"Rating drift {_signed(now - pick)} ({int(pick)} → {int(now)})")
    status = _text(last.get("universe_status"))
    rank, size = _num(last.get("universe_rank")), _num(last.get("universe_size"))
    if status == "ranked" and rank is not None:
        p = _num((pick_uni or {}).get("universe_rank"))
        of = f" of {int(size)}" if size else ""
        rank_txt = (f"rank #{int(p)} → #{int(rank)}{of}" if p is not None
                    else f"rank #{int(rank)}{of} today")
    elif status == "not_in_universe":
        rank_txt = "not in today's 500"
    else:
        rank_txt = "rank starts with the next shortlist run"
    return f"{head} · {rank_txt} · tracking since {first}"


def _part_moves(base, now) -> list[tuple[float, str]]:
    """(weighted rating-point change, 'Minervini 7/8 → 4/8') per rating part."""
    import rating
    w = {k: v * 100 for k, v in rating.OVERALL_WEIGHTS.items()}
    out = []
    for key, label, mx in _PARTS:
        a, b = _num(base.get(key)), _num(now.get(key))
        if a is not None and b is not None:
            out.append(((b - a) / mx * w[key], f"{label} {int(a)}/{mx} → {int(b)}/{mx}"))
    a, an = _num(base.get("canslim")), _num(base.get("canslim_n"))
    b, bn = _num(now.get("canslim")), _num(now.get("canslim_n"))
    if a is not None and b is not None and an and bn:
        out.append(((b / bn - a / an) * w["canslim"],
                    f"CANSLIM {int(a)}/{int(an)} → {int(b)}/{int(bn)}"))
    a, b = _num(base.get("ew_conf")), _num(now.get("ew_conf"))
    if a is not None and b is not None:
        out.append(((b - a) / 100 * w["ew"], f"EW conf {int(a)} → {int(b)}"))
    return out


def what_moved(ep, scores: pd.DataFrame, pick_uni: dict | None) -> str:
    """Which rating part moved most (weighted by its share of the rating) and
    which CANSLIM checks flipped — against the pick day when its parts were
    stored, else against the first tracked night (said with "since")."""
    if scores is None or scores.empty:
        return ""
    s = scores.sort_values("session_date")
    now = s.iloc[-1].to_dict()
    if pick_uni:
        base, since = pick_uni, ""
    elif len(s) >= 2:
        base, since = s.iloc[0].to_dict(), f" · since {str(s['session_date'].iloc[0])[:10]}"
    else:
        return ""
    moves = [m for m in _part_moves(base, now) if abs(m[0]) > 1e-9]
    lost, gained = [], []
    for key, name in _CHECK_NAMES:
        a, b = _num(base.get(key)), _num(now.get(key))
        if a is not None and b is not None and bool(a) != bool(b):
            (gained if b else lost).append(name)
    if not moves and not lost and not gained:
        return "Rating parts unchanged" + since
    bits = []
    if moves:
        lead = max(moves, key=lambda m: abs(m[0]))
        bits.append(f"{lead[1]} led the {'rise' if lead[0] > 0 else 'drop'}")
    if lost:
        bits.append("lost: " + ", ".join(lost))
    if gained:
        bits.append("gained: " + ", ".join(gained))
    return " · ".join(bits) + since


def scanners_line(ep, scores: pd.DataFrame) -> str:
    """`2 of 3 original scanners still fire`, from the latest re-score."""
    import rec_rescore as rr
    n = len(rr.scanner_set(ep.get("scanners")))
    if not n or scores is None or scores.empty:
        return ""
    k = int(_num(scores.sort_values("session_date").iloc[-1].get("original_still_firing")) or 0)
    return f"{k} of {n} original scanner{'s' if n != 1 else ''} still {'fire' if n != 1 else 'fires'}"


def decay_figure(ep, scores: pd.DataFrame):
    """Confidence decay for one pick: rating by session since entry (pick-day
    rating dashed, D threshold dotted, D where it first tripped) above the
    pick's rank in the universe (rank 1 at the top)."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    import rec_rescore as rr
    import report_style as rs
    T = rs.TOKENS
    s = scores.sort_values("session_date")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35],
                        vertical_spacing=0.06)
    fig.add_trace(go.Scatter(x=s["sessions_since_entry"], y=s["rating"], mode="lines+markers",
                             name="rating", line=dict(color=T["info"])), row=1, col=1)
    pick = _num(ep.get("overall_rating"))
    if pick is not None:
        fig.add_hline(y=pick, line=dict(color=T["accent"], width=1, dash="dash"), row=1, col=1,
                      annotation_text=f"pick day {int(pick)}", annotation_position="top left")
        fig.add_hline(y=pick - rr.DOWNGRADE_POINTS, line=dict(color=T["risk"], width=1, dash="dot"),
                      row=1, col=1, annotation_text="D line (a prior)",
                      annotation_position="bottom left")
    d = rr.first_downgrade(s)
    if d is not None:
        r = s[s["session_date"].astype(str).str[:10] == d].iloc[0]
        fig.add_trace(go.Scatter(x=[r["sessions_since_entry"]], y=[r["rating"]],
                                 mode="markers+text", name="D", text=["D"],
                                 textposition="top center",
                                 marker=dict(symbol="triangle-down", size=12, color=T["risk"])),
                      row=1, col=1)
    ranked = s[s["universe_status"] == "ranked"] if "universe_status" in s else s.iloc[0:0]
    fig.add_trace(go.Scatter(x=ranked["sessions_since_entry"], y=ranked["universe_rank"],
                             mode="lines+markers", name="universe rank",
                             line=dict(color=T["text_muted"])), row=2, col=1)
    fig.update_yaxes(title_text="rating", row=1, col=1)
    fig.update_yaxes(title_text="rank", autorange="reversed", row=2, col=1)
    fig.update_xaxes(title_text="sessions since entry", row=2, col=1)
    fig.add_annotation(xref="paper", yref="paper", x=0, y=1.08, showarrow=False,
                       text=f"tracking since {str(s['session_date'].iloc[0])[:10]}",
                       font=dict(size=10, color=T["text_muted"]))
    fig.update_layout(height=320, showlegend=False, margin=dict(l=10, r=10, t=30, b=10))
    return fig


def decay_table(eps: pd.DataFrame, scores: pd.DataFrame, h: int = ra.HEADLINE_H) -> pd.DataFrame:
    """Median rating drift by session since entry, judged winners vs losers
    (loser = audit failure at `h`). Descriptive; fills in as tracking accrues."""
    cols = ["sessions_since_entry", "winners_median", "losers_median", "n_winners", "n_losers"]
    r = f"ret_{h}"
    if scores is None or scores.empty or eps.empty or r not in eps:
        return pd.DataFrame(columns=cols)
    judged = eps[eps[r].notna()][["episode_id", "failure"]]
    d = scores[["episode_id", "sessions_since_entry", "rating_drift"]].merge(judged, on="episode_id")
    d = d[d["rating_drift"].notna()]
    if d.empty:
        return pd.DataFrame(columns=cols)
    d["loser"] = d["failure"].fillna(False).astype(bool)
    rows = []
    for k, g in d.groupby("sessions_since_entry"):
        w, l = g.loc[~g["loser"], "rating_drift"], g.loc[g["loser"], "rating_drift"]
        rows.append({"sessions_since_entry": k,
                     "winners_median": float(w.median()) if len(w) else None,
                     "losers_median": float(l.median()) if len(l) else None,
                     "n_winners": len(w), "n_losers": len(l)})
    return pd.DataFrame(rows, columns=cols)
