"""Backfill NIFTY's index-PCR baseline from NSE's F&O bhavcopy archive.

    py -3 tools/pcr_backfill.py --days 800            # fetch + cache, no DB writes
    py -3 tools/pcr_backfill.py --days 800 --write-db # then load the cache into the live table

`sentiment_index` ships factor 5 (PCR) as NOT_CHECKED until `MIN_PCR_HISTORY = 60`
sessions of NIFTY's own PCR are stored, and on 2026-09-11 it had one — the day it
started storing. That made the sign-convention test (B-22r) look blocked until
December.

It was not blocked. `nse_oi_momentum._download_bhavcopy(session, day)` takes an
ARBITRARY date and NSE's archive is date-templated, so the baseline can be
reconstructed instead of waited for. That is what this does.

Two properties worth stating because they are what make the backfill trustworthy:

  * **It does not reimplement anything.** Each day's file goes through the same
    `pcr.build_pcr_table(raw, CLASS_INDEX)` the live factor uses. A second PCR
    definition computed "just for the study" is exactly the drift B-24 is on the
    backlog for.
  * **`pcr_chg` needs no history.** `build_pcr_table` reconstructs the prior day's
    OI from `ChngInOpnIntrst` inside a single file, so the one-day slope is
    available per-file and the backfill has no ordering dependency.

The disk cache is the source of truth for the study; `--write-db` is a separate,
opt-in step because those rows land in the SAME table the live daily score ranks
against (see the warning in the pre-registration page).
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

import nse_oi_momentum as oim
import pcr

HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / "cache" / "pcr"
CACHE = CACHE_DIR / "nifty_index_pcr.csv"

#: NSE serves a trading holiday as an HTML error page rather than a 404, which
#: `_download_bhavcopy` already handles by checking the zip magic bytes. So a
#: missing day is normal and is NOT retried — roughly 30% of calendar days in any
#: window are weekends and holidays.
SYMBOL = "NIFTY"


def _load_cache() -> pd.DataFrame:
    if not CACHE.exists():
        return pd.DataFrame(columns=["reading_date", "pcr", "pcr_chg", "total_oi", "liquid"])
    df = pd.read_csv(CACHE)
    return df


def _save_cache(df: pd.DataFrame) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df = df.drop_duplicates(subset=["reading_date"], keep="last")
    df = df.sort_values("reading_date").reset_index(drop=True)
    df.to_csv(CACHE, index=False)


def backfill(days: int, symbol: str = SYMBOL, verbose: bool = True) -> pd.DataFrame:
    """Walk back `days` calendar days, caching one row per available session."""
    have = _load_cache()
    known = set(have["reading_date"].astype(str)) if not have.empty else set()
    session = requests.Session()
    rows: list[dict] = []
    misses = 0

    for back in range(1, days + 1):
        day = datetime.today() - timedelta(days=back)
        if day.weekday() >= 5:
            continue
        ymd = day.date().isoformat()
        if ymd in known:
            continue
        raw = oim._download_bhavcopy(session, day)
        if raw is None or raw.empty:
            misses += 1
            continue
        table = pcr.build_pcr_table(raw, pcr.CLASS_INDEX)
        row = table[table["symbol"] == symbol]
        if row.empty:
            misses += 1
            continue
        r = row.iloc[0]
        rows.append({
            "reading_date": ymd,
            "pcr": float(r["pcr"]),
            "pcr_chg": (float(r["pcr_chg"]) if pd.notna(r["pcr_chg"]) else None),
            "total_oi": float(r["total_oi"]),
            # Carried, not filtered on, so the study can apply the production
            # liquidity floor itself and report how many days it excluded.
            "liquid": bool(r["liquid"]),
        })
        if verbose and len(rows) % 25 == 0:
            print(f"  ... {len(rows)} sessions fetched (at {ymd})", flush=True)

    out = pd.concat([have, pd.DataFrame(rows)], ignore_index=True) if rows else have
    _save_cache(out)
    if verbose:
        print(f"fetched {len(rows)} new sessions, {misses} calendar days had no file "
              f"(weekends excluded before the request); cache now {len(out)} rows")
    return _load_cache()


def write_db(symbol: str = SYMBOL, verbose: bool = True) -> int:
    """Load the cached history into `pcr_index_history`, the live baseline table.

    Deliberately a separate command. These rows are what the daily factor ranks
    today's PCR against, so this is a live-state change, not a study step. It reuses
    `sentiment_index._record_pcr`, which is idempotent per (date, symbol) — so
    re-running is safe and a backfilled day that the live job later recomputes is
    simply overwritten with the same numbers.

    ── The liquidity floor is production's rule, not the study's (B-78) ──
    `_pcr_nifty` RETURNS BEFORE it records when `rec["liquid"]` is false, so the
    live table contains liquid sessions only — by construction, never as a filter
    anyone applied. The cache deliberately carries illiquid days instead (see
    `backfill`: "carried, not filtered on") so the study can apply the floor
    itself and report how many it dropped.

    Writing the cache verbatim therefore put days into the baseline that the live
    path could never have put there, and a percentile is a statement ABOUT its
    sample. Every one of the 543 rows cached on 2026-09-11 happened to be liquid,
    so nothing was corrupted — but the two paths disagreed on what the baseline
    IS, and that disagreement was one illiquid session away from being silent and
    permanent.
    """
    import sentiment_index as si

    df = _load_cache()
    if df.empty:
        print("nothing cached — run the backfill first")
        return 0
    n_all = len(df)
    if "liquid" in df.columns:
        df = df[df["liquid"].astype(bool)]
    skipped = n_all - len(df)
    n = 0
    for _, r in df.iterrows():
        si._record_pcr(str(r["reading_date"]), {
            "symbol": symbol,
            "pcr": float(r["pcr"]),
            "pcr_chg": (float(r["pcr_chg"]) if pd.notna(r["pcr_chg"]) else None),
            "total_oi": float(r["total_oi"]),
        })
        n += 1
    if verbose:
        stored = si.pcr_history(symbol)
        if skipped:
            print(f"skipped {skipped} cached session(s) below the production "
                  f"liquidity floor — the live path would not have stored them")
        print(f"wrote {n} rows; pcr_index_history now holds {len(stored)} sessions "
              f"for {symbol} (factor needs {si.MIN_PCR_HISTORY})")
    return n


def reconcile(symbol: str = SYMBOL) -> dict:
    """Compare the study cache against the live table. Read-only.

    The gap this exists to surface: the backfill cached **543** sessions on
    2026-09-11 and the study measured on them, while `--write-db` was never run —
    so the live table held **one** row and the dashboard told the reader "only 0 of
    60 baseline sessions stored" about a series that was already two years deep.
    Two stores, one of them silently empty, and nothing in either tool said so.

    Counting both is cheap; printing it on every run is cheaper than the month it
    took to notice. Reporting only — it never writes.
    """
    import sentiment_index as si

    cache = _load_cache()
    if "liquid" in cache.columns and not cache.empty:
        cache = cache[cache["liquid"].astype(bool)]
    live = si.pcr_history(symbol)
    return {
        "cache_sessions": int(len(cache)),
        "live_sessions": int(len(live)),
        "missing_from_live": int(max(0, len(cache) - len(live))),
        "min_history": si.MIN_PCR_HISTORY,
        "live_scores": len(live) >= si.MIN_PCR_HISTORY,
    }


def print_reconcile(symbol: str = SYMBOL) -> dict:
    """`reconcile`, rendered. Called on every CLI run so the gap cannot hide."""
    r = reconcile(symbol)
    print(f"cache (liquid): {r['cache_sessions']} sessions | "
          f"live pcr_index_history: {r['live_sessions']} sessions")
    if r["missing_from_live"]:
        print(f"  !! {r['missing_from_live']} cached session(s) are NOT in the live "
              f"table. The factor ranks today against the LIVE table, so it is "
              f"reading a shorter history than the study measured.")
        print(f"  reconcile with:  py -3 tools/pcr_backfill.py --days 0 --write-db")
    elif not r["live_scores"]:
        print(f"  live table is below MIN_PCR_HISTORY ({r['min_history']}) — the "
              f"factor will read NOT CHECKED until it is deeper")
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--days", type=int, default=800,
                    help="calendar days to walk back (default 800, about 2.2 years)")
    ap.add_argument("--symbol", default=SYMBOL)
    ap.add_argument("--write-db", action="store_true",
                    help="also load the cache into the live pcr_index_history table")
    ap.add_argument("--status", action="store_true",
                    help="compare cache against the live table and exit; fetches nothing")
    a = ap.parse_args()

    if a.status:
        print_reconcile(a.symbol)
        return 0

    df = backfill(a.days, a.symbol)
    if not df.empty:
        print(f"cache: {len(df)} sessions, {df['reading_date'].min()} to {df['reading_date'].max()}")
        print(f"  PCR  min {df['pcr'].min():.3f}  median {df['pcr'].median():.3f}  max {df['pcr'].max():.3f}")
        print(f"  illiquid days (below the production floor): {(~df['liquid'].astype(bool)).sum()}")
    if a.write_db:
        write_db(a.symbol)
    # Always, whether or not this run wrote: a cache deeper than the live table is
    # the B-78 failure, and it is invisible unless something counts both.
    print_reconcile(a.symbol)
    return 0


if __name__ == "__main__":
    sys.exit(main())
