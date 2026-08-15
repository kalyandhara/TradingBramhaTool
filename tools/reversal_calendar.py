"""
reversal_calendar.py — Combined yoga + lunar-phase reversal calendar (SQLite).

Pulls every event from yoga_dates.py (9 yogas across both Drik URL trees)
and lunar_phases.py (PyEphem full/new moons), persists them to a single
SQLite table, and exposes range-query helpers used by:

  • the chart-dashboard /api/reversal_events endpoint (chart_server.py)
  • any morning-prep script that wants "show me reversal candidates in
    the next 30 days, sorted by coincidence score"

Per the user's spec this is a *one-time-per-2-years* build — these dates
are deterministic (lunar is astronomy; yogas are Drik-published) and don't
change once Drik publishes the year. So we don't auto-refresh; rebuild
explicitly:

    py -3 tools/reversal_calendar.py build --years 2026 2027        # 2 years
    py -3 tools/reversal_calendar.py build --years 2026 2027 --refresh-yoga
    py -3 tools/reversal_calendar.py query --from 2026-06-01 --days 60
    py -3 tools/reversal_calendar.py stats

DB path: tools/reversal_calendar.db (gitignored; rebuildable in one cmd).

Schema:
    reversal_events(
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        event_date   TEXT    NOT NULL,   -- YYYY-MM-DD (IST), the day to mark
        event_type   TEXT    NOT NULL,   -- e.g. 'indra', 'full_moon'
        display_name TEXT    NOT NULL,   -- e.g. 'Indra Yoga', 'Full Moon'
        category     TEXT    NOT NULL,   -- 'auspicious_yoga' | 'nakshatra_yoga' | 'lunar_phase'
        start_ts     TEXT    NOT NULL,   -- ISO local datetime (with offset)
        end_ts       TEXT    NOT NULL,   -- ISO local datetime (with offset)
        weekday      TEXT    NOT NULL,
        source       TEXT    NOT NULL,   -- 'drikpanchang' | 'ephem'
        ingested_at  TEXT    NOT NULL,
        UNIQUE(event_date, event_type, start_ts)
    )

The (event_date, event_type, start_ts) UNIQUE constraint makes the builder
idempotent — re-running `build` for an already-ingested year is a safe no-op.
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytz

log = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "reversal_calendar.db"
IST = pytz.timezone("Asia/Kolkata")

# ── Category tagging — used by the chart indicator to color-code markers ──────
_AUSPICIOUS = {"ravi", "sarvarthasiddhi", "amritsiddhi", "dwipushkar",
               "tripushkar", "ravipushya", "gurupushya", "maitreya"}
_NAKSHATRA = {"indra"}


def _category_for(yoga_key: str) -> str:
    if yoga_key in _AUSPICIOUS:
        return "auspicious_yoga"
    if yoga_key in _NAKSHATRA:
        return "nakshatra_yoga"
    return "yoga"


# ── DB lifecycle ──────────────────────────────────────────────────────────────

def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    """Open the calendar DB (creates it + schema if missing)."""
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript("""
        CREATE TABLE IF NOT EXISTS reversal_events (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            event_date   TEXT    NOT NULL,
            event_type   TEXT    NOT NULL,
            display_name TEXT    NOT NULL,
            category     TEXT    NOT NULL,
            start_ts     TEXT    NOT NULL,
            end_ts       TEXT    NOT NULL,
            weekday      TEXT    NOT NULL,
            source       TEXT    NOT NULL,
            ingested_at  TEXT    NOT NULL,
            UNIQUE(event_date, event_type, start_ts)
        );
        CREATE INDEX IF NOT EXISTS idx_reversal_event_date
            ON reversal_events(event_date);
        CREATE INDEX IF NOT EXISTS idx_reversal_category
            ON reversal_events(category);
    """)
    con.commit()
    return con


# ── Builder ───────────────────────────────────────────────────────────────────

def _insert_event(con: sqlite3.Connection, *, event_date: date,
                  event_type: str, display_name: str, category: str,
                  start_ts: datetime, end_ts: datetime, source: str) -> bool:
    """Insert one event. Returns True if inserted, False if it was a
    duplicate (idempotent rebuild)."""
    try:
        con.execute(
            "INSERT INTO reversal_events "
            "(event_date, event_type, display_name, category, "
            " start_ts, end_ts, weekday, source, ingested_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (event_date.isoformat(), event_type, display_name, category,
             start_ts.isoformat(), end_ts.isoformat(),
             start_ts.strftime("%A"), source,
             datetime.now(timezone.utc).isoformat()),
        )
        return True
    except sqlite3.IntegrityError:
        return False  # UNIQUE constraint hit — already ingested


def build_calendar(years: list[int], *, refresh_yoga: bool = False,
                   db_path: Path = DB_PATH) -> dict:
    """Populate the DB for the given years. Returns per-source counts."""
    import yoga_dates as yd
    import lunar_phases as lp

    con = connect(db_path)
    counts: dict[str, int] = defaultdict(int)
    skipped: dict[str, int] = defaultdict(int)

    try:
        for yr in years:
            log.info("Ingesting yogas for %d ...", yr)
            for key, (_kind, _url, display) in yd.YOGA_SOURCES.items():
                try:
                    occs = yd.get_yoga_occurrences(key, yr, refresh=refresh_yoga)
                except Exception as e:
                    log.warning("  yoga %s/%d failed: %s", key, yr, e)
                    continue
                category = _category_for(key)
                for occ in occs:
                    # Times from Drik are New-Delhi local — pin IST tzinfo so
                    # the stored ISO string is unambiguous.
                    start_ist = IST.localize(occ.start) if occ.start.tzinfo is None else occ.start.astimezone(IST)
                    end_ist   = IST.localize(occ.end)   if occ.end.tzinfo   is None else occ.end.astimezone(IST)
                    inserted = _insert_event(
                        con,
                        event_date=start_ist.date(),
                        event_type=key,
                        display_name=display,
                        category=category,
                        start_ts=start_ist,
                        end_ts=end_ist,
                        source="drikpanchang",
                    )
                    counts[key] += int(inserted)
                    skipped[key] += int(not inserted)

            log.info("Ingesting lunar phases for %d ...", yr)
            for ev in lp.lunar_events_for_range(date(yr, 1, 1), date(yr, 12, 31)):
                display = "Full Moon" if ev["phase"] == "full_moon" else "New Moon"
                inserted = _insert_event(
                    con,
                    event_date=ev["date"],
                    event_type=ev["phase"],
                    display_name=display,
                    category="lunar_phase",
                    start_ts=ev["local"],
                    end_ts=ev["local"],  # phases are instants
                    source="ephem",
                )
                counts[ev["phase"]] += int(inserted)
                skipped[ev["phase"]] += int(not inserted)

        con.commit()
    finally:
        con.close()

    return {"inserted": dict(counts), "skipped_dupes": dict(skipped)}


# ── Query helpers ─────────────────────────────────────────────────────────────

def events_in_range(start: date, end: date, *, db_path: Path = DB_PATH
                    ) -> list[dict]:
    """All events with event_date in [start, end]. Returns a list of dicts."""
    con = connect(db_path)
    try:
        rows = con.execute(
            "SELECT event_date, event_type, display_name, category, "
            "       start_ts, end_ts, weekday "
            "FROM reversal_events "
            "WHERE event_date BETWEEN ? AND ? "
            "ORDER BY event_date, start_ts",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
    finally:
        con.close()
    return [dict(r) for r in rows]


def coincidence_scores(start: date, end: date, *, db_path: Path = DB_PATH
                       ) -> list[dict]:
    """Per-day count of overlapping events — the user's "sharper reversal"
    indicator. Returns rows sorted DESC by score, then date ASC."""
    con = connect(db_path)
    try:
        rows = con.execute(
            "SELECT event_date, COUNT(*) AS score, "
            "       GROUP_CONCAT(display_name, ' + ') AS events "
            "FROM reversal_events "
            "WHERE event_date BETWEEN ? AND ? "
            "GROUP BY event_date "
            "ORDER BY score DESC, event_date ASC",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
    finally:
        con.close()
    return [dict(r) for r in rows]


def db_stats(db_path: Path = DB_PATH) -> dict:
    """Summary of what's in the DB — useful for sanity-checking a build."""
    con = connect(db_path)
    try:
        total = con.execute("SELECT COUNT(*) AS n FROM reversal_events"
                            ).fetchone()["n"]
        by_cat = con.execute(
            "SELECT category, COUNT(*) AS n FROM reversal_events "
            "GROUP BY category ORDER BY n DESC"
        ).fetchall()
        date_range = con.execute(
            "SELECT MIN(event_date) AS first, MAX(event_date) AS last "
            "FROM reversal_events"
        ).fetchone()
    finally:
        con.close()
    return {
        "total": total,
        "by_category": {r["category"]: r["n"] for r in by_cat},
        "date_range": (date_range["first"], date_range["last"]),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def _cli() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="ingest the given years into the DB")
    p_build.add_argument("--years", type=int, nargs="+", required=True,
                         help="e.g. --years 2026 2027")
    p_build.add_argument("--refresh-yoga", action="store_true",
                         help="bypass yoga_dates.py disk cache (force re-scrape)")

    p_q = sub.add_parser("query", help="list events in a date window")
    p_q.add_argument("--from", dest="from_date", required=True,
                     help="YYYY-MM-DD")
    p_q.add_argument("--to", dest="to_date",
                     help="YYYY-MM-DD (alternative to --days)")
    p_q.add_argument("--days", type=int,
                     help="window size in days from --from (alternative to --to)")
    p_q.add_argument("--coincidence", action="store_true",
                     help="aggregate by date, show coincidence score")
    p_q.add_argument("--json", action="store_true",
                     help="emit JSON instead of human-readable table")

    sub.add_parser("stats", help="print DB summary")

    args = p.parse_args()

    if args.cmd == "build":
        res = build_calendar(args.years, refresh_yoga=args.refresh_yoga)
        print(f"\nBuild complete -> {DB_PATH}")
        print(f"  inserted:      {sum(res['inserted'].values())}")
        print(f"  skipped (dup): {sum(res['skipped_dupes'].values())}")
        for k in sorted(set(res["inserted"]) | set(res["skipped_dupes"])):
            i, s = res["inserted"].get(k, 0), res["skipped_dupes"].get(k, 0)
            print(f"    {k:20s}  +{i:<4d} (skipped {s})")

    elif args.cmd == "query":
        start = date.fromisoformat(args.from_date)
        if args.to_date:
            end = date.fromisoformat(args.to_date)
        elif args.days:
            end = start + timedelta(days=args.days - 1)
        else:
            end = start
        if args.coincidence:
            rows = coincidence_scores(start, end)
            if args.json:
                print(json.dumps(rows, indent=2))
            else:
                print(f"\nCoincidence scores {start} - {end}\n")
                print(f"{'Date':<12} Score  Events")
                print("-" * 80)
                for r in rows:
                    print(f"{r['event_date']:<12} {r['score']:<6} {r['events']}")
        else:
            rows = events_in_range(start, end)
            if args.json:
                print(json.dumps(rows, indent=2))
            else:
                print(f"\n{len(rows)} events {start} - {end}\n")
                print(f"{'Date':<12} {'Time':<6} {'Category':<18} Event")
                print("-" * 70)
                for r in rows:
                    t = r["start_ts"][11:16]
                    print(f"{r['event_date']:<12} {t:<6} "
                          f"{r['category']:<18} {r['display_name']} "
                          f"({r['weekday']})")

    elif args.cmd == "stats":
        s = db_stats()
        print(f"Total events:   {s['total']}")
        print(f"Date range:     {s['date_range'][0]} - {s['date_range'][1]}")
        print("By category:")
        for cat, n in s["by_category"].items():
            print(f"  {cat:<18} {n}")
        print(f"DB:             {DB_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
