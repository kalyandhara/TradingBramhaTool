"""Pick re-score — which picks are open, and one nightly score row per pick.

Pure: no I/O. `rec_rescore_job.py` fetches, scans and stores; this module
decides what a row says. Spec: docs/superpowers/specs/2026-11-26-pick-rescore-design.md

Why the score is split: the shortlist score is 0.45·rating + 0.30·best scanner
+ 0.25·confluence, and scanners mostly fire on one day (a breakout fires on the
breakout). Drift on that composite would flag nearly every pick by day 2. So
drift and the D (downgrade) flag use the Overall Rating alone, against its
stored pick-day value; the scanner part is kept beside it as "is the setup
still there".
"""
from __future__ import annotations

import math
from typing import Iterable, Mapping

import pandas as pd

#: D = rating at least this far below the pick-day rating. A named prior, not
#: measured: one Minervini check is ~4.4 rating points, one TechnoFunda ~4.2,
#: one CANSLIM ~5, so 15 is roughly three checks lost.
DOWNGRADE_POINTS = 15
#: Track a pick for this many sessions after entry (the audit's longest horizon).
TRACK_SESSIONS = 63

PARTS = ("rating", "minervini", "technofunda", "canslim", "canslim_n", "ew_conf")
CHECKS = ("cs_near_high", "cs_volume", "cs_market", "cs_rs")
COLUMNS = ("episode_id", "session_date", "symbol", "rec_date", "sessions_since_entry",
           *PARTS, *CHECKS, "scanners_today", "families_today", "best_scanner_score",
           "edge_points", "original_still_firing", "score_today", "universe_rank",
           "universe_size", "universe_status", "rating_at_pick", "rating_drift",
           "downgrade", "model_version", "created_at")


def _num(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


#: NSE closes 15:30 IST; a bar dated today (IST) before this time is still forming.
#: The machine runs on US Eastern, whose evening is IST market hours, so a manual
#: run there would otherwise score a live, thin bar.
IST_OFFSET = pd.Timedelta(hours=5, minutes=30)
SESSION_FINAL_IST = pd.Timedelta(hours=16)


def _utc_now() -> pd.Timestamp:
    return pd.Timestamp.now(tz="UTC")


def completed_session(index, now: pd.Timestamp | None = None) -> pd.Timestamp | None:
    """The last bar date in `index` whose NSE session has closed: the last bar,
    unless it is dated today in IST and it is not yet 16:00 IST."""
    idx = pd.DatetimeIndex(index).normalize()
    if idx.empty:
        return None
    now = (now if now is not None else _utc_now()).tz_convert("UTC").tz_localize(None)
    ist = now + IST_OFFSET
    last = idx[-1]
    if last >= ist.normalize() and ist - ist.normalize() < SESSION_FINAL_IST:
        return idx[-2] if len(idx) > 1 else None
    return last


def cut(df: pd.DataFrame | None, session: pd.Timestamp) -> pd.DataFrame | None:
    """Bars up to and including `session` — the row's date and its data agree."""
    if df is None or df.empty:
        return df
    return df[pd.DatetimeIndex(df.index).normalize() <= session]


def benchmark_sessions_since(rec_date, sessions: pd.DatetimeIndex) -> int:
    """Benchmark sessions after the pick day — the pick's age even when its own
    bars have stopped (delisted, suspended, renamed)."""
    rec = pd.Timestamp(str(rec_date)[:10])
    return int((pd.DatetimeIndex(sessions).normalize() > rec).sum())


def select_open(eps: pd.DataFrame) -> pd.DataFrame:
    """Opportunity episodes still inside the tracking window, plus pending ones
    (picked, no entry session yet)."""
    if eps.empty:
        return eps
    sessions = pd.to_numeric(eps.get("sessions"), errors="coerce")
    keep = (eps["source"].eq("opportunity")
            & (eps["status"].eq("pending")
               | (eps["status"].isin(["open", "matured"]) & sessions.le(TRACK_SESSIONS))))
    return eps[keep]


def scanner_set(text, known: Iterable[str] | None = None) -> set[str]:
    """Scanner names in a stored ", "-joined list. One registered name contains
    a comma ("Shallow Flip (Renko, bounded correction)"), so names are matched
    against the registry with their delimiters, not split blindly."""
    s = "" if text is None or (isinstance(text, float) and math.isnan(text)) else str(text)
    if not s.strip():
        return set()
    if known is None:
        import scanner_templates as sc
        known = sc.SCANNERS
    wrapped = f", {s}, "
    got = {n for n in known if f", {n}, " in wrapped}
    return got or {p.strip() for p in s.split(",") if p.strip()}


def _bool(v):
    return None if v is None else int(bool(v))


def build_row(ep: Mapping, bars: pd.DataFrame, session: pd.Timestamp, detail: dict | None,
              hit: dict | None, uni: Mapping | None, universe_available: bool, version: str,
              known: Iterable[str] | None = None) -> dict | None:
    """One pick_scores row for `session`, or None when the pick has no bar on
    that session (suspended, fetch failed) or no rating could be computed.

    universe_status: "ranked"; "not_in_universe" (tonight's universe has ratings,
    not this name); "no_universe" (no universe ratings for the session at all).
    """
    session = pd.Timestamp(session).normalize()
    if detail is None or bars is None or bars.empty:
        return None
    idx = pd.DatetimeIndex(bars.index).normalize()
    if session not in idx:
        return None
    import opportunity_daily as od
    import opportunity_hub as oh

    rec = pd.Timestamp(str(ep.get("rec_date"))[:10])
    since = int(((idx > rec) & (idx <= session)).sum())
    at_pick = _num(ep.get("overall_rating"))
    drift = None if at_pick is None else detail["rating"] - at_pick
    today = list((hit or {}).get("scanners") or [])
    best = _num((hit or {}).get("best_score"))
    edge = _num((hit or {}).get("edge_points"))
    score = (od.W_RATING * detail["rating"] + od.W_SCANNER * min(best or 0.0, 100.0)
             + od.W_CONFLUENCE * (oh.confluence_pct(edge) if edge else 0.0))
    original = scanner_set(ep.get("scanners"), known)
    if uni is not None:
        status, rank, size = "ranked", uni.get("universe_rank"), uni.get("universe_size")
    else:
        status = "not_in_universe" if universe_available else "no_universe"
        rank = size = None
    return {
        "episode_id": ep.get("episode_id"), "session_date": session.strftime("%Y-%m-%d"),
        "symbol": ep.get("symbol"), "rec_date": rec.strftime("%Y-%m-%d"),
        "sessions_since_entry": since,
        **{k: detail.get(k) for k in PARTS}, **{k: _bool(detail.get(k)) for k in CHECKS},
        "scanners_today": ", ".join(today),
        "families_today": ", ".join((hit or {}).get("families") or []),
        "best_scanner_score": best, "edge_points": edge,
        "original_still_firing": len(original & set(today)),
        "score_today": round(score, 1),
        "universe_rank": None if rank is None else int(rank),
        "universe_size": None if size is None else int(size), "universe_status": status,
        "rating_at_pick": None if at_pick is None else int(at_pick),
        "rating_drift": None if drift is None else int(drift),
        "downgrade": int(drift is not None and drift <= -DOWNGRADE_POINTS),
        "model_version": version,
    }


def first_downgrade(scores: pd.DataFrame) -> str | None:
    """Earliest session on which the pick was flagged D, or None."""
    if scores is None or scores.empty or "downgrade" not in scores:
        return None
    d = scores[pd.to_numeric(scores["downgrade"], errors="coerce").fillna(0).astype(int) == 1]
    return None if d.empty else str(d["session_date"].min())[:10]
