#!/usr/bin/env python3
"""rec_audit_job.py — run the recommendation audit and store it (A1).

Reads every stored Opportunity Hub pick (`portfolio_db.daily_opportunities`),
fetches daily bars for the picks and the benchmarks in batched yfinance calls,
scores each episode with `rec_audit`, and writes:

  tools/rec_audit.db
    price_bars      (symbol, date) OHLCV cache — the page reads prices from here
    audit_episodes  latest audit, one row per episode (replaced each run)
    audit_runs      one row per run: as_of + summary JSON (the continuity log)

No liquidity floor anywhere: a thin pick that went nowhere is exactly what an
audit must see (the ₹1 Cr scan floor silently dropped HERANBA from
equity_snapshot until 2026-10-22). A pick with no bars is NO_DATA, never dropped.

  py -3 tools/rec_audit_job.py              # audit as of today, print the report
  py -3 tools/rec_audit_job.py --as-of 2026-10-21
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rec_audit as ra  # noqa: E402

TOOLS_DIR = Path(__file__).resolve().parent
DB_PATH = TOOLS_DIR / "rec_audit.db"
#: One markdown report per month, overwritten by every run inside that month,
#: so the last run of a month leaves that month's verdict frozen in git.
REPORTS_DIR = TOOLS_DIR.parent / "reports" / "audit"

MARKET = "^CRSLDX"                 # NIFTY 500
SMALLCAP = "NIFTYSMLCAP250.NS"     # NIFTY Smallcap 250
#: daily_opportunities.sector carries Yahoo's sector names; map them to the
#: nearest NSE sector index. A sector with no sensible index stays unmapped
#: (sector excess None) rather than borrowing a wrong one.
SECTOR_INDEX = {
    "Technology": "^CNXIT", "Healthcare": "^CNXPHARMA",
    "Financial Services": "NIFTY_FIN_SERVICE.NS", "Consumer Defensive": "^CNXFMCG",
    "Basic Materials": "^CNXMETAL", "Industrials": "^CNXINFRA",
    "Real Estate": "^CNXREALTY", "Energy": "^CNXENERGY", "Utilities": "^CNXENERGY",
    "Consumer Cyclical": "^CNXCONSUM", "Communication Services": "^CNXMEDIA",
}
#: Yahoo serves only ~4 days of history for most NSE sector indices (probed
#: 2026-10-22: FMCG, Infra, Fin Services, Metal, Realty, Energy, Consumption),
#: so sector bars are rebuilt from NSE's own daily all-indices file instead
#: (`sector_rotation.fetch_nse_index_closes`, disk-cached per session).
#: Contradicted 2026-10-26 (B-184): single-ticker `yf.download(t, start=2010)` gave
#: full 2010-11 history for all of these except ^CNXMEDIA (1 bar), with closes equal
#: to NSE's to the paisa. Either the 10-22 probe hit a transient Yahoo gap or the
#: request shape differs; the NSE path is kept because it is never worse.
NSE_SECTOR_NAMES = {
    "^CNXIT": "Nifty IT", "^CNXPHARMA": "Nifty Pharma",
    "NIFTY_FIN_SERVICE.NS": "Nifty Financial Services", "^CNXFMCG": "Nifty FMCG",
    "^CNXMETAL": "Nifty Metal", "^CNXINFRA": "Nifty Infrastructure",
    "^CNXREALTY": "Nifty Realty", "^CNXENERGY": "Nifty Energy",
    "^CNXCONSUM": "Nifty India Consumption", "^CNXMEDIA": "Nifty Media",
}
CHUNK = 40
LOOKBACK_DAYS = 60                 # bars before the first rec (EMA 20, 20-day low)

Downloader = Callable[[list[str], str, str], dict[str, pd.DataFrame]]


# ── Prices ───────────────────────────────────────────────────────────────────
def yahoo_symbol(nse: str) -> str:
    return nse if nse.startswith("^") or nse.endswith(".NS") else f"{nse}.NS"


def _split_download(raw: pd.DataFrame, tickers: list[str]) -> dict[str, pd.DataFrame]:
    """yf.download(group_by='ticker') frame → {ticker: lowercase OHLCV}. The
    ticker level is present even for ONE ticker, so always look it up."""
    out = {}
    if raw is None or raw.empty:
        return out
    for t in tickers:
        if isinstance(raw.columns, pd.MultiIndex):
            if t not in raw.columns.get_level_values(0):
                continue
            d = raw[t].copy()
        else:
            d = raw.copy()
        d.columns = [str(c).lower() for c in d.columns]
        d = d.dropna(subset=["close"])
        if d.empty:
            continue
        d.index = pd.to_datetime(d.index).tz_localize(None).normalize()
        out[t] = d[["open", "high", "low", "close", "volume"]].astype(float)
    return out


def yf_downloader(tickers: list[str], start: str, end: str) -> dict[str, pd.DataFrame]:
    import yfinance as yf
    out: dict[str, pd.DataFrame] = {}
    for i in range(0, len(tickers), CHUNK):
        part = tickers[i:i + CHUNK]
        try:
            raw = yf.download(part, start=start, end=end, interval="1d",
                              group_by="ticker", auto_adjust=True, progress=False,
                              threads=True)
        except Exception:
            continue
        out.update(_split_download(raw, part))
    return out


def nse_sector_bars(start: str, end: str, fetch=None) -> dict[str, pd.DataFrame]:
    """{yahoo-style ticker: OHLC} for NSE_SECTOR_NAMES, one NSE file per weekday.
    `fetch(day) -> (DataFrame|None, session_date|None)`; missing days are skipped."""
    if fetch is None:
        import sector_rotation as sr
        fetch = lambda d: sr.fetch_nse_index_closes(d, max_backtrack=0)  # noqa: E731
    want = {v: k for k, v in NSE_SECTOR_NAMES.items()}
    rows: dict[str, list] = {k: [] for k in NSE_SECTOR_NAMES}
    for d in pd.bdate_range(start, end):
        df, got = fetch(d.date())
        if df is None or got != d.date():
            continue
        for _, r in df[df["Index Name"].isin(want)].iterrows():
            try:
                rows[want[r["Index Name"]]].append(
                    (pd.Timestamp(got), float(r["Open Index Value"]),
                     float(r["High Index Value"]), float(r["Low Index Value"]),
                     float(r["Closing Index Value"])))
            except (TypeError, ValueError):
                continue                       # "-" on a day the index didn't print
    out = {}
    for t, rs in rows.items():
        if rs:
            out[t] = (pd.DataFrame(rs, columns=["date", "open", "high", "low", "close"])
                      .set_index("date").assign(volume=0.0))
    return out


# ── Store ────────────────────────────────────────────────────────────────────
def connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS price_bars (
            symbol TEXT NOT NULL, date TEXT NOT NULL,
            open REAL, high REAL, low REAL, close REAL, volume REAL,
            PRIMARY KEY (symbol, date));
        CREATE TABLE IF NOT EXISTS audit_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, as_of TEXT NOT NULL,
            source TEXT NOT NULL, created_at TEXT NOT NULL, summary_json TEXT);
        -- The owner's post-mortem review. Kept apart from audit_episodes (which
        -- every run replaces) so a note outlives the re-run that follows it.
        CREATE TABLE IF NOT EXISTS postmortem_notes (
            episode_id TEXT PRIMARY KEY, tag_override TEXT, note TEXT,
            updated_at TEXT NOT NULL);
    """)
    return conn


def save_bars(conn, bars: dict[str, pd.DataFrame]) -> None:
    rows = [(sym, d.strftime("%Y-%m-%d"), *map(float, r))
            for sym, df in bars.items()
            for d, r in zip(df.index, df[["open", "high", "low", "close", "volume"]]
                            .fillna(0).to_numpy())]
    conn.executemany("INSERT OR REPLACE INTO price_bars VALUES (?,?,?,?,?,?,?)", rows)
    conn.commit()


def load_bars(conn, symbols: list[str]) -> dict[str, pd.DataFrame]:
    out = {}
    for s in symbols:
        d = pd.read_sql_query("SELECT date, open, high, low, close, volume FROM price_bars "
                              "WHERE symbol = ? ORDER BY date", conn, params=(s,),
                              parse_dates=["date"]).set_index("date")
        if not d.empty:
            out[s] = d
    return out


# ── Run ──────────────────────────────────────────────────────────────────────
def load_recs() -> pd.DataFrame:
    import portfolio_db as db
    df = db.get_daily_opportunities(None)
    df["run_date"] = pd.to_datetime(df["run_date"])
    return df


def run_audit(recs: pd.DataFrame | None = None, *, as_of: date | None = None,
              download: Downloader | None = None, sector_fetch=None,
              db_path: Path | str = DB_PATH, source: str = "opportunity") -> dict:
    """Fetch → episodes → outcomes → store. Returns the report dict.
    `sector_fetch` is passed to `nse_sector_bars` (tests stub it)."""
    as_of = as_of or date.today()
    recs = load_recs() if recs is None else recs
    download = download or yf_downloader
    conn = connect(db_path)
    try:
        start = (recs["run_date"].min() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
        end = (pd.Timestamp(as_of) + timedelta(days=1)).strftime("%Y-%m-%d")
        bench = sorted({MARKET, SMALLCAP, *SECTOR_INDEX.values()})
        stocks = sorted({yahoo_symbol(s) for s in recs["symbol"].dropna()})
        save_bars(conn, download([MARKET, SMALLCAP] + stocks, start, end))
        save_bars(conn, nse_sector_bars(start, as_of.isoformat(), fetch=sector_fetch))
        bars = load_bars(conn, bench + stocks)

        market = bars.get(MARKET)
        if market is None:
            raise RuntimeError(f"no bars for the market benchmark {MARKET}")
        sessions = market.index[market.index <= pd.Timestamp(as_of)]
        eps = ra.build_episodes(recs, sessions, source=source)

        rows = []
        for _, ep in eps.iterrows():
            o = ra.episode_outcome(ep, bars.get(yahoo_symbol(ep["symbol"])), market,
                                   smallcap=bars.get(SMALLCAP),
                                   sector=bars.get(SECTOR_INDEX.get(ep.get("sector") or "")),
                                   as_of=as_of)
            fail = ra.is_failure(o)
            tags = ra.postmortem_tags(ep, o) if fail else []
            o.update(failure=fail, tags=", ".join(tags),
                     primary_tag=ra.primary_tag(tags) if fail else None)
            rows.append(o)
        out = eps.merge(pd.DataFrame(rows), on="episode_id", how="left")
        out["as_of"] = as_of.isoformat()

        report = build_report(out, bars, market)
        keep = out.drop(columns=[c for c in ("notes", "market_verdict") if c in out])
        _sqlable(keep).to_sql("audit_episodes", conn, if_exists="replace", index=False)
        port = report["portfolio"]
        port_rows = (port.rename_axis("date").reset_index() if not port.empty
                     else pd.DataFrame(columns=["date", "basket", "market", "active"]))
        _sqlable(port_rows).to_sql("audit_portfolio", conn, if_exists="replace", index=False)
        conn.execute("INSERT INTO audit_runs (as_of, source, created_at, summary_json) "
                     "VALUES (?,?,?,?)",
                     (as_of.isoformat(), source, datetime.now().isoformat(timespec="seconds"),
                      json.dumps(report["summary"])))
        conn.commit()
        report["episodes_df"] = out
        return report
    finally:
        conn.close()


def build_report(out: pd.DataFrame, bars: dict, market: pd.DataFrame) -> dict:
    h = ra.HEADLINE_H
    matured = out[out[f"ret_{h}"].notna()] if f"ret_{h}" in out else out.iloc[0:0]
    port = ra.paper_portfolio(matured.assign(symbol=matured["symbol"].map(yahoo_symbol)),
                              bars, market)
    summary = ra.summarise(out)
    if not port.empty:
        summary.update(basket_ret=ra._f((port["basket"].iloc[-1] - 1) * 100),
                       market_ret=ra._f((port["market"].iloc[-1] - 1) * 100),
                       basket_max_dd=ra.max_drawdown(port["basket"]),
                       market_max_dd=ra.max_drawdown(port["market"]))
    fails = out[out["failure"].fillna(False).astype(bool) & out[f"ret_{h}"].notna()] \
        if f"ret_{h}" in out else out.iloc[0:0]
    return {
        "summary": summary,
        "cohorts": ra.cohorts(out),
        "by_family": ra.attribution(out, "family_names"),
        "by_rank": ra.attribution(out.assign(rank_band=pd.cut(
            out["rank"], [0, 5, 20, 1000], labels=["1-5", "6-20", "21+"]).astype(str)),
            "rank_band"),
        "by_flags": ra.attribution(out.assign(flagged=out["risk_flags"].fillna("")
                                              .astype(str).str.strip().ne("")
                                              .map({True: "flagged", False: "clean"})),
                                   "flagged"),
        "by_sector": ra.attribution(out, "sector"),
        "tags": fails["primary_tag"].value_counts().to_dict() if not fails.empty else {},
        "portfolio": port,
    }


def format_report(rep: dict) -> str:
    s = rep["summary"]
    lines = [f"Recommendation audit — {s['episodes']} episodes, {s['n']} matured at "
             f"{s['h']} sessions, {s['no_data']} with no data, {s['pending']} not yet entered, "
             f"{s['data_suspect']} set aside (suspected split/bonus)",
             f"  hit rate {s['hit_rate']}% | median return {s['median_ret']}% | "
             f"beat NIFTY 500 {s['beat_market_rate']}% | median excess {s['median_excess']}% "
             f"(t={_r(s['t_excess'])}) | vs Smallcap 250 {s['median_excess_smallcap']}% "
             f"(t={_r(s['t_excess_smallcap'])})",
             f"  grouped by entry week ({s['weeks']} weeks): t vs NIFTY 500 "
             f"{_r(s['t_excess_weekly'])}, vs Smallcap 250 {_r(s['t_excess_smallcap_weekly'])}",
             f"  median MFE {s['median_mfe']}% / MAE {s['median_mae']}% | plans {s['plans']}, "
             f"target-first {s['target_first_rate']}% of decided | failures {s['failures']}"]
    if "basket_ret" in s:
        lines.append(f"  paper basket {s['basket_ret']}% (max DD {s['basket_max_dd']}%) vs "
                     f"NIFTY 500 {s['market_ret']}% (max DD {s['market_max_dd']}%)")
    lines.append("\nCohorts:\n" + rep["cohorts"].to_string(index=False))
    for k in ("by_rank", "by_flags", "by_sector", "by_family"):
        lines.append(f"\n{k}:\n" + rep[k].head(15).to_string(index=False))
    lines.append(f"\nFailure primary tags: {rep['tags']}")
    return "\n".join(lines)


def _sqlable(df: pd.DataFrame) -> pd.DataFrame:
    """Timestamps → ISO text; everything else as is (None stays NULL, not "None")."""
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            out[c] = out[c].dt.strftime("%Y-%m-%d")
        elif out[c].dtype == object:
            out[c] = [v.strftime("%Y-%m-%d") if isinstance(v, (pd.Timestamp, datetime, date))
                      else v for v in out[c]]
    return out


# ── Read side (the page) ─────────────────────────────────────────────────────
def load_latest(db_path: Path | str = DB_PATH) -> dict:
    """The stored audit: episodes (+ the owner's notes), portfolio, last run and
    run history. Empty frames and run=None before the first audit. Never fetches."""
    conn = connect(db_path)
    try:
        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        eps = (pd.read_sql_query("SELECT * FROM audit_episodes", conn)
               if "audit_episodes" in tabs else pd.DataFrame())
        port = (pd.read_sql_query("SELECT * FROM audit_portfolio", conn,
                                  parse_dates=["date"]).set_index("date")
                if "audit_portfolio" in tabs else pd.DataFrame())
        notes = pd.read_sql_query("SELECT * FROM postmortem_notes", conn)
        run = conn.execute("SELECT as_of, created_at, summary_json FROM audit_runs "
                           "ORDER BY id DESC LIMIT 1").fetchone()
        history = pd.read_sql_query("SELECT as_of, created_at, summary_json FROM audit_runs "
                                    "ORDER BY id", conn)
    finally:
        conn.close()
    if not eps.empty:
        eps = eps.merge(notes, on="episode_id", how="left")
        eps["failure"] = eps["failure"].fillna(0).astype(bool)
        has_override = eps["tag_override"].notna() & (eps["tag_override"] != "")
        eps["review_tag"] = eps["tag_override"].where(has_override, eps["primary_tag"])
    return {"episodes": eps, "portfolio": port,
            "run": None if run is None else {"as_of": run[0], "created_at": run[1],
                                             "summary": json.loads(run[2] or "{}")},
            "history": history}


def save_note(episode_id: str, tag_override: str | None, note: str | None,
              db_path: Path | str = DB_PATH) -> None:
    """Upsert the owner's review of one episode. Empty override = keep the auto tag."""
    conn = connect(db_path)
    try:
        conn.execute("INSERT INTO postmortem_notes (episode_id, tag_override, note, updated_at) "
                     "VALUES (?,?,?,?) ON CONFLICT(episode_id) DO UPDATE SET "
                     "tag_override=excluded.tag_override, note=excluded.note, "
                     "updated_at=excluded.updated_at",
                     (episode_id, tag_override or None, (note or "").strip() or None,
                      datetime.now().isoformat(timespec="seconds")))
        conn.commit()
    finally:
        conn.close()


def write_monthly_report(rep: dict, as_of: date, out_dir: Path | None = None) -> Path:
    """reports/audit/YYYY-MM.md — overwritten by each run inside that month."""
    out_dir = out_dir or REPORTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{as_of:%Y-%m}.md"
    path.write_text(
        f"# Recommendation audit — {as_of:%B %Y}\n\n"
        f"Last run in the month: as of {as_of.isoformat()}. Generated by "
        f"`tools/rec_audit_job.py`. Returns are measured from the next session's open "
        f"and compared with benchmarks over the same dates.\n\n"
        f"```\n{format_report(rep)}\n```\n", encoding="utf-8")
    return path


def _r(v):
    return None if v is None else round(v, 2)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Recommendation audit")
    ap.add_argument("--as-of", type=lambda s: date.fromisoformat(s), default=None)
    ap.add_argument("--no-report", action="store_true",
                    help="skip writing reports/audit/YYYY-MM.md")
    a = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    rep = run_audit(as_of=a.as_of)
    print(format_report(rep))
    if not a.no_report:
        print(f"report -> {write_monthly_report(rep, a.as_of or date.today())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
