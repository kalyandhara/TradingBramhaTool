"""participant_oi.py — NSE participant-wise F&O open interest (B-95).

    py -3 tools/participant_oi.py backfill --years 10     # fill the cache, politely
    py -3 tools/participant_oi.py show                     # latest FII / client ratios

NSE publishes one small CSV per session — `fao_participant_oi_DDMMYYYY.csv` on
nsearchives — splitting equity-derivative OI by participant class (Client, DII, FII,
Pro): index and stock futures long / short, and index / stock option calls and puts
long / short. B-95 probed it on 2026-10-14: fetchable for every date tried back to
2016. Nothing else on the desk reads it (`FII` elsewhere classifies shareholder names
in block deals; the F&O bhavcopy carries contract OI, not the participant split).

The ratio the letters quote — "FIIs 88% short" — is the FII share of index-futures
OI on the short side. This module only fetches and parses; whether that ratio
predicts anything is `participant_oi_study.py`'s question, pre-registered there.
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache" / "participant_oi"
URL = "https://nsearchives.nseindia.com/content/nsccl/fao_participant_oi_{d:%d%m%Y}.csv"
#: Same browser-like headers the desk already uses for nsearchives.
from nse_oi_momentum import NSE_HEADERS  # noqa: E402

PAUSE_S = 0.4               # between requests — one small file a session, no hurry
CLASSES = ("Client", "DII", "FII", "Pro")


def _norm(h: str) -> str:
    return " ".join(h.replace("\t", " ").split()).strip().lower()


def parse(text: str) -> dict[str, dict[str, float]] | None:
    """{class: {column: contracts}} from one file, or None if it is not one.

    The first line is a title; the second the header. Column names have drifted
    in whitespace over the years, so they are normalised before use.
    """
    # Some 2017 files use bare CR line endings, which the csv module refuses.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error:
        return None
    hdr_i = next((i for i, r in enumerate(rows) if r and _norm(r[0]) == "client type"), None)
    if hdr_i is None:
        return None
    hdr = [_norm(h) for h in rows[hdr_i]]
    out: dict[str, dict[str, float]] = {}
    for r in rows[hdr_i + 1:]:
        if not r or not r[0].strip():
            continue
        name = r[0].strip()
        vals = {}
        for h, v in zip(hdr[1:], r[1:]):
            try:
                vals[h] = float(str(v).replace(",", "").strip())
            except ValueError:
                continue
        out[name] = vals
    return out if all(c in out for c in CLASSES) else None


def index_futures_long_share(rec: dict[str, dict[str, float]], cls: str = "FII") -> float | None:
    """Long ÷ (long + short) of `cls`'s index-futures OI. 0.12 = "88% short"."""
    v = rec.get(cls) or {}
    lo, sh = v.get("future index long"), v.get("future index short")
    if lo is None or sh is None or lo + sh <= 0:
        return None
    return lo / (lo + sh)


def fetch(d: date, session: requests.Session | None = None) -> str | None:
    """The file for session `d`, from cache or NSE. None on a holiday / not found."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{d:%Y-%m-%d}.csv"
    miss = CACHE / f"{d:%Y-%m-%d}.none"
    if f.exists():
        return f.read_text(encoding="utf-8", errors="replace")
    if miss.exists():
        return None
    s = session or requests.Session()
    try:
        r = s.get(URL.format(d=d), headers=NSE_HEADERS, timeout=20)
    except requests.RequestException:
        return None                       # transient: not marked, retried next run
    if r.status_code == 404:
        miss.write_text("", encoding="utf-8")   # holiday / no file — don't ask again
        return None
    if not r.ok or parse(r.text) is None:
        return None
    f.write_text(r.text, encoding="utf-8")
    return r.text


def load(start: date | None = None) -> list[tuple[date, dict]]:
    """Every cached session in date order, parsed."""
    out = []
    for f in sorted(CACHE.glob("*.csv")):
        d = date.fromisoformat(f.stem)
        if start and d < start:
            continue
        rec = parse(f.read_text(encoding="utf-8", errors="replace"))
        if rec:
            out.append((d, rec))
    return out


def backfill(years: int, until: date | None = None) -> tuple[int, int]:
    until = until or date.today()
    d = until - timedelta(days=int(years * 365.25))
    s = requests.Session()
    got = miss = 0
    while d <= until:
        if d.weekday() < 5:
            cached = (CACHE / f"{d:%Y-%m-%d}.csv").exists() or (CACHE / f"{d:%Y-%m-%d}.none").exists()
            ok = fetch(d, s) is not None
            got += ok
            miss += not ok
            if not cached:
                time.sleep(PAUSE_S)
            if (got + miss) % 100 == 0:
                print(f"  {d}  cached {got}  missing {miss}", flush=True)
        d += timedelta(days=1)
    return got, miss


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backfill"); b.add_argument("--years", type=float, default=10)
    sub.add_parser("show")
    a = ap.parse_args(argv)
    if a.cmd == "backfill":
        got, miss = backfill(a.years)
        print(f"sessions cached: {got}, missing/holiday: {miss}")
    else:
        rows = load()
        for d, rec in rows[-5:]:
            f = index_futures_long_share(rec, "FII"); c = index_futures_long_share(rec, "Client")
            print(f"{d}  FII index fut long {f:.1%} (short {1 - f:.1%})  ·  client long {c:.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
