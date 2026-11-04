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

Bulk and block deals (B-198): each poll also reads NSE's bulk.csv / block.csv
(the latest session only, published after the close) and emails any deal on
my names it has not sent before, in the same email. A failed deals read is
logged and skipped; it never blocks the filings.

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


def deal_key(d: dict) -> str:
    # Two tickets by one client in one name on one day are two deals, so the
    # side, size and type are part of the key, not just (symbol, client, date).
    return (f"deal|{d.get('date')}|{d.get('symbol')}|{d.get('client')}|"
            f"{d.get('side')}|{d.get('qty')}|{d.get('deal_type')}")


def new_deals(deals: Iterable[dict], names: dict[str, str], seen: set[str]) -> list[dict]:
    """Bulk/block deals on my names not sent before. Adds their keys to `seen`."""
    out = []
    for d in deals:
        why = names.get(_norm_sym(d.get("symbol", "")))
        k = deal_key(d)
        if not why or k in seen:
            continue
        seen.add(k)
        out.append({**d, "why": why})
    return out


def load_deals() -> list[dict]:
    """The latest session's NSE bulk + block deals, normalised. Raises on a
    failed read; the caller decides that a failed deals read is not fatal."""
    import block_deal_intel as bdi
    import india_market_intel as imi
    df = bdi.normalize_deals(nse_bulk=imi.fetch_nse_bulk_deals(),
                             nse_block=imi.fetch_nse_block_deals())
    return [] if df.empty else df.to_dict("records")


def _crore(v: float) -> str:
    return f"₹{v / 1e7:,.1f} Cr" if v >= 1e6 else f"₹{v:,.0f}"


def render_email(rows: list[dict], deals: list[dict] = ()) -> tuple[str, str]:
    rows = sorted(rows, key=lambda r: (_RANK.get(r["why"], 9), r.get("symbol", "")))
    deals = sorted(deals, key=lambda d: (_RANK.get(d["why"], 9), d.get("symbol", "")))
    n, nd = len(rows), len(deals)
    held = sum(r["why"] == "held" for r in rows) + sum(d["why"] == "held" for d in deals)
    parts = []
    if n:
        parts.append(f"{n} filing{'s' if n > 1 else ''}")
    if nd:
        parts.append(f"{nd} deal{'s' if nd > 1 else ''}")
    subject = ("Trading Bramha Filings · " + " · ".join(parts)
               + (f" · {held} on held" if held else ""))
    # A client that both bought and sold one name the same day is usually a
    # market-maker or arbitrage desk turning stock over, not taking a position.
    # Say so on both tickets, with the net, so the pair is not read as interest.
    net: dict[tuple, float] = {}
    sides: dict[tuple, set] = {}
    for d in deals:
        k = (d.get("symbol"), d.get("client"), d.get("date"))
        net[k] = net.get(k, 0.0) + (d["qty"] if d["side"] == "BUY" else -d["qty"])
        sides.setdefault(k, set()).add(d["side"])
    blocks = []
    for d in deals:
        k = (d.get("symbol"), d.get("client"), d.get("date"))
        trip = (f"\n  same client bought AND sold today · net {net[k]:+,.0f} sh: "
                f"likely intraday turnover, not a position"
                if sides[k] == {"BUY", "SELL"} else "")
        blocks.append(f"{d['symbol']} ({d['why']}) · {d['deal_type']} {d['side']}\n"
                      f"  {d.get('client') or 'client not named'} · {d['qty']:,.0f} sh "
                      f"@ ₹{d['price']:,.2f} = {_crore(d['value'])}\n"
                      f"  {d.get('date', '')} · {d.get('exchange', 'NSE')}{trip}")
    for r in rows:
        amt = f"  [{r['amount']} as filed]" if r.get("amount") else ""
        blocks.append(f"{r['symbol']} ({r['why']}) · {r['bucket']}{amt}\n"
                      f"  {r.get('headline') or r.get('category')}\n"
                      f"  {r.get('when', '')[:17]} · {r.get('pdf') or 'no PDF'}")
    body = ("\n\n".join(blocks)
            + "\n\nA news feed, not a signal: a filing is a reason to read the filing,"
            + " and a bulk/block deal says who traded, not why."
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
        print("NSE announcements endpoint did not answer — failed read")
    try:
        deals_raw, deals_err = load_deals(), None
    except Exception as exc:                 # a failed deals read never blocks filings
        deals_raw, deals_err = [], str(exc)
        print(f"NSE bulk/block deals read failed: {exc}")

    names = load_names()
    seen_list = _load_seen()
    seen = set(seen_list)
    fresh = new_filings(ff.material(raw), names, seen) if raw else []
    fresh_deals = new_deals(deals_raw, names, seen)
    print(f"{len(raw)} filings · {len(deals_raw)} deals · {len(names)} names watched · "
          f"{len(fresh)} new filings, {len(fresh_deals)} new deals on my names")
    # One line for Scheduler Hub -> History (job_audit). Printed before the send
    # so a failed send still leaves the counts on record.
    print("##RESULT "
          + (f"{len(raw)} filings · {len(fresh)} new" if raw else "filings read FAILED")
          + (f" · {len(deals_raw)} deals · {len(fresh_deals)} new" if deals_err is None
             else " · deals read FAILED")
          + f" · {len(names)} names")

    code = 0 if raw else 2               # a failed filings read is not a quiet day
    if not (fresh or fresh_deals):
        return code
    subject, body = render_email(fresh, fresh_deals)
    if a.dry_run:
        print(f"\n{subject}\n\n{body}")
        return code

    from alert_email_send import send
    print("  ✉ ", send(subject, body))
    ALERT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().isoformat(timespec="seconds")
    with FEED_PATH.open("a", encoding="utf-8") as f:
        for r in fresh:
            f.write(json.dumps({**r, "ts": stamp}, ensure_ascii=False) + "\n")
        # Deals ride the same feed so the digest's filings section shows them.
        for d in fresh_deals:
            f.write(json.dumps({
                "symbol": d["symbol"], "why": d["why"], "ts": stamp,
                "bucket": f"{d['deal_type']} {d['side']}",
                "headline": f"{d.get('client') or 'client not named'} · "
                            f"{d['qty']:,.0f} sh @ ₹{d['price']:,.2f} = {_crore(d['value'])}",
            }, ensure_ascii=False) + "\n")
    # Seen is written only AFTER the send succeeds: a failed send retries next poll.
    seen_list += [filing_key(r) for r in fresh] + [deal_key(d) for d in fresh_deals]
    SEEN_PATH.write_text(json.dumps(seen_list[-SEEN_KEEP:]), encoding="utf-8")
    return code


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.exit(main())
