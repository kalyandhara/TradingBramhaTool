#!/usr/bin/env python3
"""filings_watch.py — the always-on NSE filings listener for MY names.

`nse_filings_feed` reads the market-wide stream and buckets the material
filings, but only when a desk page is open. This is the scheduled half: every
interval during the session it reads today's stream, keeps the material filings
on names I care about, and emails the ones it has not sent before.

"My names", in priority order (a name is listed under its strongest reason):
  held       open positions
  watchlist  the default watchlist and every named list
  pick       the latest Opportunity Hub shortlist

Every new filing is also appended to cache/alerts/filings.jsonl, which the daily
digest reads for its "Filings on your names" section.

> [!important] A NEWS FEED, not a signal. A filing is a reason to read the
> filing. Amounts appear only when the filing's own text states one.

A failed NSE read exits 2 (the .bat logs FAILED) and sends nothing: a failed
read is not a quiet day.

CLI:
    py -3 -X utf8 tools/filings_watch.py            # poll once, email new filings
    py -3 -X utf8 tools/filings_watch.py --dry-run  # print, send nothing, mark nothing seen
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

ALERT_DIR = HERE / "cache" / "alerts"
SEEN_PATH = ALERT_DIR / "filings_seen.json"
FEED_PATH = ALERT_DIR / "filings.jsonl"
SEEN_KEEP = 2000                       # newest keys kept; a day is ~250 filings
IST = timezone(timedelta(hours=5, minutes=30))

_RANK = {"held": 0, "watchlist": 1, "pick": 2}


def _norm_sym(s: str) -> str:
    s = str(s or "").strip().upper()
    return s[:-3] if s.endswith(".NS") else s


def my_names(held: Iterable[str], watched: Iterable[str],
             picked: Iterable[str]) -> dict[str, str]:
    """symbol → why it is mine. A held name stays 'held' even if also watched."""
    out: dict[str, str] = {}
    for why, syms in (("held", held), ("watchlist", watched), ("pick", picked)):
        for s in syms:
            s = _norm_sym(s)
            if s and s not in out:
                out[s] = why
    return out


def load_names() -> dict[str, str]:
    import portfolio_db as db
    held = db.get_open_positions()["symbol"].tolist()
    watched = db.get_watchlist()["symbol"].tolist()
    for list_id in db.get_watchlists()["id"]:
        watched += db.get_watchlist_items(int(list_id))
    dates = db.get_opportunity_run_dates()
    picked = db.get_daily_opportunities(dates[0])["symbol"].tolist() if dates else []
    return my_names(held, watched, picked)


def filing_key(r: dict) -> str:
    return f"{r.get('symbol')}|{r.get('when')}|{r.get('category')}"


def new_filings(rows: Iterable[dict], names: dict[str, str], seen: set[str]) -> list[dict]:
    """Material filings on my names not sent before. Adds their keys to `seen`."""
    out = []
    for r in rows:
        why = names.get(_norm_sym(r.get("symbol", "")))
        k = filing_key(r)
        if not why or k in seen:
            continue
        seen.add(k)
        out.append({**r, "why": why})
    return out


def render_email(rows: list[dict]) -> tuple[str, str]:
    rows = sorted(rows, key=lambda r: (_RANK.get(r["why"], 9), r.get("symbol", "")))
    n = len(rows)
    held = sum(r["why"] == "held" for r in rows)
    subject = (f"Trading Bramha Filings · {n} filing{'s' if n > 1 else ''}"
               + (f" · {held} on held" if held else ""))
    blocks = []
    for r in rows:
        amt = f"  [{r['amount']} as filed]" if r.get("amount") else ""
        blocks.append(f"{r['symbol']} ({r['why']}) · {r['bucket']}{amt}\n"
                      f"  {r.get('headline') or r.get('category')}\n"
                      f"  {r.get('when', '')[:17]} · {r.get('pdf') or 'no PDF'}")
    body = ("\n\n".join(blocks)
            + "\n\nA news feed, not a signal: a filing is a reason to read the filing."
            + f"\n— Trading Bramha filings watch ({datetime.now():%Y-%m-%d %H:%M})")
    return subject, body


def _load_seen() -> list[str]:
    try:
        return json.loads(SEEN_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def main() -> int:
    ap = argparse.ArgumentParser(description="Email new NSE filings on my names.")
    ap.add_argument("--dry-run", action="store_true",
                    help="print new filings; send nothing, mark nothing seen")
    a = ap.parse_args()

    import nse_filings_feed as ff
    # Anchor the range to the IST date, not this machine's US-Eastern one: after
    # 14:30 ET filings carry tomorrow's IST date and a local-date range never
    # asked for them. Overlap a day (three on Monday, for the weekend); the seen
    # file keeps the overlap from re-sending.
    ist_today = datetime.now(IST).date()
    raw = ff.fetch(3 if ist_today.weekday() == 0 else 2, today=ist_today)
    if not raw:
        print("NSE announcements endpoint did not answer — failed read, nothing sent")
        print("##RESULT NSE did not answer — failed read")
        return 2
    names = load_names()
    seen_list = _load_seen()
    seen = set(seen_list)
    fresh = new_filings(ff.material(raw), names, seen)
    print(f"{len(raw)} filings · {len(names)} names watched · {len(fresh)} new on my names")
    # One line for Scheduler Hub -> History (job_audit). Printed before the send
    # so a failed send still leaves the counts on record.
    print(f"##RESULT {len(raw)} filings · {len(fresh)} new on {len(names)} names")

    if not fresh:
        return 0
    subject, body = render_email(fresh)
    if a.dry_run:
        print(f"\n{subject}\n\n{body}")
        return 0

    from alert_email_send import send
    print("  ✉ ", send(subject, body))
    ALERT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().isoformat(timespec="seconds")
    with FEED_PATH.open("a", encoding="utf-8") as f:
        for r in fresh:
            f.write(json.dumps({**r, "ts": stamp}, ensure_ascii=False) + "\n")
    # Seen is written only AFTER the send succeeds: a failed send retries next poll.
    seen_list += [filing_key(r) for r in fresh]
    SEEN_PATH.write_text(json.dumps(seen_list[-SEEN_KEEP:]), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.exit(main())
