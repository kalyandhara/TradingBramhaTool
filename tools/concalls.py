"""concalls.py — FR-6's concall/announcement layer, the half that needs no LLM.

Why this exists
---------------
[[analyses/Fundamental-Deep-Dive-Report-Roadmap]] records FR-6 as *"all that
remains — still blocked on the same finding as M3: no LLM is configured in this
repo."* That is true of **half** of FR-6 and was being applied to all of it.

FR-6 as scoped is two separable things:

  1. **Management quotes via concall links** — locate the company's actual
     earnings-call transcripts and investor-meet filings.
  2. **LLM narration** of that material — *"only if an API key ever appears."*

(2) is genuinely blocked: the `anthropic` SDK is installed (0.94.0) but no
`ANTHROPIC_API_KEY` is set, so a call would fail at runtime. **(1) needs no LLM
at all**, and is available login-free right now.

Probed 2026-08-05, `api/corporate-announcements` → **HTTP 200**, 3,326 rows for
RELIANCE, carrying a dedicated subject category —
**"Analysts/Institutional Investor Meet/Con. Call Updates"** (174 rows) — and
direct `nsearchives` PDF links to the transcripts themselves
(`…_SE_Transcript.pdf`) and the audio recordings (`…_SE_AR.pdf`). Newest RELIANCE
transcript: 19-Jul-2026. This is the same NSE surface family as the shareholding
XBRL in `nse_shareholding_fetch`, and unlike `quote-equity` it is **not** behind
the 403 that SR-0 had to route around.

What this module deliberately does NOT do
-----------------------------------------
It does not summarise, paraphrase, score or characterise anything a management
team said. The roadmap's own instruction is explicit — ***"Do not let a template
pretend to be analysis"*** — and a rule-based "narrative" over concall text would
be exactly that: generated prose with the cadence of judgement and none of the
substance behind it. This module returns **dated links to primary documents** and
stops there. The reader does the reading.

That restraint is the same one `rrg` applies by omitting unmeasurable sectors and
`market_health` by returning NOT_CHECKED: when the honest output is "here is the
source, we cannot interpret it", say that rather than manufacture a reading.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import nse_shareholding_fetch as nsf

log = logging.getLogger(__name__)

HERE      = Path(__file__).resolve().parent
CACHE_DIR = HERE / "cache" / "concalls"
#: Announcements land continuously and a results-day transcript is the whole
#: point of the feature, so this cache is deliberately short — unlike the
#: ownership cache, whose filings are immutable once filed.
CACHE_TTL = 6 * 3600

ANN_URL = "https://www.nseindia.com/api/corporate-announcements"

#: NSE's own subject line for the category. Matched loosely because the string
#: carries punctuation that has changed shape before ("Con. Call" / "Con Call").
CONCALL_SUBJECT = re.compile(r"analyst|institutional investor|con\.?\s*call", re.I)

#: Second arm, and it is not optional. **Filing the transcript under the concall
#: subject is a convention, not a rule, and large filers routinely ignore it.**
#: Measured 2026-08-05 on INFY: of 52 rows carrying a transcript, **31 are filed
#: under the generic subject "Updates"** and only 16 under
#: "Analysts/Institutional Investor Meet/Con. Call". Subject-only matching put
#: INFY's newest transcript at **2023-04-18** when the true answer is
#: **2026-07-28** — a three-year-stale date rendered with total confidence for a
#: company that files every quarter.
#:
#: So a row also qualifies on the DOCUMENT itself. Deliberately narrow — specific
#: document nouns, not loose keywords — so that broadening the net does not drag
#: in every "Updates" row NSE holds.
CONCALL_DOC = re.compile(
    r"transcript|audio\s*record|earnings\s*call|con\.?\s*call|conference\s*call", re.I)

#: Document kinds, most informative first. Order matters: a transcript
#: attachment usually also mentions the call, so the specific test must win.
_KINDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("transcript",   re.compile(r"transcript", re.I)),
    ("audio",        re.compile(r"audio\s*record|_AR\.pdf|\baudio\b", re.I)),
    ("presentation", re.compile(r"presentation|investor\s*deck", re.I)),
    ("press",        re.compile(r"press\s*release|media\s*release", re.I)),
    # Scheduling notices — "will be participating", "intimation of", board
    # meeting notices. Useful as a calendar, useless as a quote source, so they
    # are labelled rather than mixed in with the documents that carry content.
    ("intimation",   re.compile(r"intimation|schedul|will be (participat|attend)|"
                                r"meeting of the board|notice of", re.I)),
)


def _cache_path(symbol: str) -> Path:
    return CACHE_DIR / f"{symbol.upper()}.json"


def _read_cache(symbol: str) -> list[dict] | None:
    p = _cache_path(symbol)
    try:
        if not p.exists() or (time.time() - p.stat().st_mtime) > CACHE_TTL:
            return None
        return json.loads(p.read_text(encoding="utf-8")) or None
    except Exception as e:
        log.debug("concall cache read failed (%s): %s", symbol, e)
        return None


def _write_cache(symbol: str, rows: list[dict]) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path(symbol).write_text(json.dumps(rows), encoding="utf-8")
    except Exception as e:
        log.debug("concall cache write failed (%s): %s", symbol, e)


_MEMO: dict[str, list[dict] | None] = {}


def _parse_dt(v: Any) -> datetime | None:
    """NSE stamps announcements '19-Jul-2026 18:06:37'."""
    s = str(v or "").strip()
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def fetch_announcements(symbol: str, use_cache: bool = True) -> list[dict] | None:
    """Every corporate announcement NSE holds for `symbol`, newest first.

    Returns None on a failed fetch — **not** an empty list. The distinction is
    the point: "we could not ask" and "the company has filed nothing" are
    different statements, and this repo has shipped the bug that conflates them
    more than once.
    """
    key = symbol.upper()
    if use_cache:
        if key in _MEMO:
            return _MEMO[key]
        cached = _read_cache(key)
        if cached is not None:
            _MEMO[key] = cached
            return cached

    try:
        session = nsf._new_session()
        r = session.get(ANN_URL, headers=nsf.HEADERS, timeout=25,
                        params={"index": "equities", "symbol": key})
        r.raise_for_status()
        rows = r.json()
    except Exception as e:
        log.warning("[%s] announcements fetch failed: %s", key, e)
        if use_cache:
            _MEMO[key] = None
        return None

    if not isinstance(rows, list):
        log.warning("[%s] announcements: unexpected payload %s", key, type(rows).__name__)
        if use_cache:
            _MEMO[key] = None
        return None

    if use_cache:
        _write_cache(key, rows)
        _MEMO[key] = rows
    return rows


def classify(row: dict) -> str:
    """Document kind for one announcement row: transcript / audio / presentation /
    press / intimation / other."""
    blob = " ".join(str(row.get(k) or "") for k in
                    ("desc", "attchmntText", "attchmntFile", "csvName"))
    for kind, pat in _KINDS:
        if pat.search(blob):
            return kind
    return "other"


def concall_items(symbol: str, limit: int = 20,
                  use_cache: bool = True) -> dict:
    """Concall / investor-meet filings for `symbol`, newest first, with coverage.

    Returns ``{state, items[], n_total, n_concall, n_transcripts, latest_transcript}``.
    `state` is OK when the feed was read and NOT_CHECKED when it could not be —
    never an empty list standing in for a failed fetch.
    """
    out: dict[str, Any] = {
        "state": "NOT_CHECKED", "items": [], "n_total": 0, "n_concall": 0,
        "n_transcripts": 0, "latest_transcript": None, "note": "",
    }

    rows = fetch_announcements(symbol, use_cache=use_cache)
    if rows is None:
        out["note"] = "NSE announcements feed unavailable"
        return out

    out["state"] = "OK"
    out["n_total"] = len(rows)

    items: list[dict] = []
    for r in rows:
        subject = str(r.get("desc") or "")
        doc_blob = " ".join(str(r.get(k) or "") for k in
                            ("attchmntText", "attchmntFile", "csvName"))
        # Either NSE filed it under the concall subject, or the attachment is
        # itself concall material filed under something generic. See CONCALL_DOC.
        if not (CONCALL_SUBJECT.search(subject + " " + doc_blob)
                or CONCALL_DOC.search(doc_blob)):
            continue
        dt = _parse_dt(r.get("an_dt") or r.get("sort_date") or r.get("dt"))
        items.append({
            "date":    dt.date().isoformat() if dt else None,
            "dt":      dt,
            "subject": subject,
            "text":    (str(r.get("attchmntText") or "").strip() or None),
            "file":    (str(r.get("attchmntFile") or "").strip() or None),
            "size":    r.get("attFileSize"),
            "kind":    classify(r),
        })

    items.sort(key=lambda x: x["dt"] or datetime.min, reverse=True)
    out["n_concall"] = len(items)

    transcripts = [i for i in items if i["kind"] == "transcript"]
    out["n_transcripts"] = len(transcripts)
    if transcripts:
        out["latest_transcript"] = transcripts[0]["date"]

    # Drop the sort key before handing rows out — a datetime does not belong in a
    # payload that Streamlit caches and JSON-serialises.
    for i in items:
        i.pop("dt", None)
    out["items"] = items[:limit]
    return out


if __name__ == "__main__":                      # python concalls.py RELIANCE INFY
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    for s in (sys.argv[1:] or ["RELIANCE"]):
        d = concall_items(s, limit=8)
        print(f"\n=== {s} — {d['state']} ===")
        if d["state"] != "OK":
            print("   ", d["note"])
            continue
        print(f"   {d['n_concall']} concall/investor rows of {d['n_total']} announcements · "
              f"{d['n_transcripts']} transcripts · latest {d['latest_transcript']}")
        for i in d["items"]:
            print(f"   {i['date']}  [{i['kind']:12s}] {(i['text'] or i['subject'])[:64]}")
            if i["file"]:
                print(f"       {i['file']}")
