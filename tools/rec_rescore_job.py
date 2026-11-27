#!/usr/bin/env python3
"""rec_rescore_job.py — the nightly pick re-score (scheduler job `rec_rescore`).

Runs after the audit (17:30) has rebuilt the episode list. For every open
Opportunity pick (inside 63 sessions of entry, or picked today) it fetches
400 days of bars with no liquidity floor, computes the Overall Rating and its
parts, runs the scanner pipeline, looks up the pick's rank in tonight's
500-name universe (`universe_ratings`, written by the shortlist job) and writes
one row to `pick_scores` in rec_audit.db, keyed by (episode_id, session_date).

History accrues forward only: nothing is back-filled. Every date stored is the
NSE session the bars end on, never this machine's local date (US Eastern).
Spec: docs/superpowers/specs/2026-11-26-pick-rescore-design.md

  py -3 tools/rec_rescore_job.py
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rec_audit_job as raj  # noqa: E402
import rec_rescore as rr  # noqa: E402

DB_PATH = raj.DB_PATH
_COLS = rr.COLUMNS


def connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute(f"""CREATE TABLE IF NOT EXISTS pick_scores (
        {', '.join(_COLS)}, PRIMARY KEY (episode_id, session_date))""")
    return conn


def _default_scan(symbols, fetch_for, bench):
    import opportunity_hub as oh
    return oh.run_scanner_pipeline(symbols, fetch_for, benchmark_df=bench, attach_pead=False)


def _default_universe(session: str, symbols=None) -> pd.DataFrame:
    import portfolio_db as db
    return db.get_universe_ratings(session, symbols)


def _default_nifty() -> pd.DataFrame | None:
    import screener_pipeline as sp
    try:
        df = sp.fetch_nifty50(days=400)
    except Exception:
        return None
    return df[df["close"].notna()] if df is not None and "close" in df else df


def run(*, eps: pd.DataFrame | None = None, fetch_for=None, nifty_df=None, scan=None,
        universe=None, db_path: Path | str = DB_PATH, known=None, progress=None) -> dict:
    """Re-score every open pick for the latest NSE session. Returns the report."""
    import opportunity_daily as od
    import opportunity_hub as oh
    import rating

    say = progress or (lambda m: None)
    as_of = None
    if eps is None:
        latest = raj.load_latest(db_path, source="opportunity")
        eps, as_of = latest["episodes"], (latest.get("run") or {}).get("as_of")
    excluded: dict[str, int] = {}
    if not eps.empty and {"source", "status"} <= set(eps.columns):
        bad = eps[eps["source"].eq("opportunity")
                  & eps["status"].isin(["no_data", "data_suspect"])]
        excluded = {k: int(v) for k, v in bad["status"].value_counts().items()}
        eps = rr.select_open(eps)
    nifty_df = _default_nifty() if nifty_df is None else nifty_df
    if nifty_df is None or nifty_df.empty:
        return {"ok": False, "reason": "no benchmark"}
    session = rr.completed_session(nifty_df.index)
    if session is None or session != pd.Timestamp(nifty_df.index[-1]).normalize():
        # Measured 2026-11-27 09:24 IST: while NSE is open, Yahoo's daily series drops
        # the previous session for ~1/3 of picks (CIPLA: 25 Nov, then a live 27 Nov).
        return {"ok": False, "reason": "NSE session in progress — Yahoo's daily bars are "
                                       "unreliable until the close; run after 16:00 IST"}
    iso = session.strftime("%Y-%m-%d")
    # Every frame is cut at the session: a stock a day ahead of the benchmark (or a
    # bar still forming in IST market hours) must not be scored under this date.
    nifty_df = rr.cut(nifty_df, session)
    raw_for = fetch_for or od._FetchRouter(days=400, min_turnover=0)

    def fetch_for(name, _raw=raw_for):
        f = _raw(name)
        return lambda s: rr.cut(f(s), session)
    scan = scan or _default_scan
    universe = universe or _default_universe
    version = od.model_version()

    retired = 0
    if not eps.empty:
        age = eps["rec_date"].map(lambda d: rr.benchmark_sessions_since(d, nifty_df.index))
        keep = (eps["status"] == "pending") | (age <= rr.TRACK_SESSIONS)
        retired, eps = int((~keep).sum()), eps[keep]
    fetch = fetch_for(oh.DEFAULT_WINDOW)
    symbols = sorted(set(eps["symbol"].dropna().astype(str))) if not eps.empty else []
    say(f"Re-scoring {len(eps)} picks ({len(symbols)} symbols) for {iso}…")
    frames, details, skipped = {}, {}, {}
    for s in symbols:
        df = fetch(s)
        if df is None or df.empty:
            skipped[s] = "no bars"
            continue
        frames[s] = df
        details[s] = rating.rating_detail(df, nifty_df)
        if details[s] is None:
            skipped[s] = "no rating"
    hits = scan(sorted(frames), fetch_for, nifty_df) if frames else {}
    uni = universe(iso, None)
    available = uni is not None and not uni.empty
    uni_by = ({str(r["symbol"]): r for r in uni.to_dict("records")} if available else {})

    rows, now = [], datetime.now().isoformat(timespec="seconds")
    for ep in eps.to_dict("records"):
        s = str(ep.get("symbol"))
        if s not in frames or details.get(s) is None:
            continue
        r = rr.build_row(ep, frames[s], session, details[s], hits.get(s), uni_by.get(s),
                         available, version, known=known)
        if r is None:
            skipped.setdefault(s, f"no bar for {iso}")
            continue
        rows.append({**r, "created_at": now})

    conn = connect(db_path)
    try:
        conn.executemany(f"INSERT OR REPLACE INTO pick_scores ({', '.join(_COLS)}) "
                         f"VALUES ({', '.join('?' * len(_COLS))})",
                         [tuple(r.get(c) for c in _COLS) for r in rows])
        conn.commit()
    finally:
        conn.close()
    skipped_picks = int(eps["symbol"].astype(str).isin(skipped).sum()) if not eps.empty else 0
    return {"ok": True, "session": iso, "written": len(rows), "skipped": skipped,
            "skipped_picks": skipped_picks, "retired": retired, "excluded": excluded,
            # The audit (17:30) rebuilds the episode list; if it failed or overran,
            # today's picks are missing and lose their day-0 row — say so.
            "episodes_as_of": as_of,
            "stale_episodes": bool(as_of) and str(as_of)[:10] < iso,
            "not_in_universe": sum(r["universe_status"] == "not_in_universe" for r in rows),
            "downgrades": sum(r["downgrade"] for r in rows)}


# ── Read side (the page) ─────────────────────────────────────────────────────
def load_scores(episode_ids: list[str] | None = None,
                db_path: Path | str = DB_PATH) -> pd.DataFrame:
    """Stored re-score rows, oldest session first per episode. Never fetches;
    an empty frame (with the columns) before the first run. Read-only: never
    creates the database file or the table."""
    empty = pd.DataFrame(columns=list(_COLS))
    if not Path(db_path).exists():
        return empty
    conn = sqlite3.connect(str(db_path))
    try:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                            "AND name='pick_scores'").fetchone():
            return empty
        q, params = "SELECT * FROM pick_scores", []
        if episode_ids:
            q += f" WHERE episode_id IN ({', '.join('?' * len(episode_ids))})"
            params = list(episode_ids)
        return pd.read_sql_query(q + " ORDER BY episode_id, session_date", conn, params=params)
    finally:
        conn.close()


def pick_day_universe(symbol: str, rec_date: str) -> dict | None:
    """The symbol's universe_ratings row on its pick session, or None (picks made
    before universe ratings existed have none)."""
    import portfolio_db as db
    got = db.get_universe_ratings(str(rec_date)[:10], [symbol])
    return None if got.empty else got.iloc[0].to_dict()


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Nightly pick re-score")
    ap.add_argument("--db", default=str(DB_PATH), help="rec_audit.db path")
    a = ap.parse_args(argv)
    rep = run(db_path=a.db, progress=lambda m: print(f"  … {m}", flush=True))
    if not rep.get("ok"):
        print(f"FAILED: {rep.get('reason')}")
        return 1
    for sym, why in sorted(rep["skipped"].items()):
        print(f"  skipped {sym}: {why}")
    ex = rep.get("excluded") or {}
    extra = []
    if rep.get("retired"):
        extra.append(f"{rep['retired']} retired (past {rr.TRACK_SESSIONS} sessions)")
    if ex:
        extra.append(f"{sum(ex.values())} excluded ("
                     + ", ".join(f"{k} {v}" for k, v in sorted(ex.items())) + ")")
    if rep.get("stale_episodes"):
        extra.append(f"episodes as of {rep['episodes_as_of']} (audit stale)")
    print(f"##RESULT {rep['session']} · {rep['written']} picks re-scored · "
          f"{rep.get('skipped_picks', len(rep['skipped']))} skipped · "
          f"{rep['not_in_universe']} not in today's 500 · {rep['downgrades']} downgrades"
          + "".join(f" · {x}" for x in extra))
    return 0


if __name__ == "__main__":
    sys.exit(main())
