"""
nse_announcements.py — free NSE corporate-announcements reader + a governance
keyword scan (Plan A for the auditor red flag).

The announcements feed reliably surfaces *events* — an auditor RESIGNATION or an
adverse/qualified-opinion filing. It does NOT contain the full audit opinion, so
this scan can only ever raise a FLAG on a positive hit; it never returns CLEAN,
because a qualified opinion can sit in the annual report without ever being
announced (absence is not proof). That asymmetry is deliberate and keeps the
FR-4 three-state contract honest.

  from nse_announcements import scan_auditor
  state, detail, as_of = scan_auditor("GENSOL")
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

import nse_shareholding_fetch as _nsf   # reuse the warmed NSE session + HEADERS

ANN_URL = ("https://www.nseindia.com/api/corporate-announcements"
           "?index=equities&symbol={sym}")

# Positive-hit patterns → FLAG. Kept narrow to avoid false alarms from routine
# "appointment/re-appointment of auditor" or "audit committee" notices.
_RESIGN = re.compile(
    r"resignation of (the |statutory )?auditor|auditor'?s? resignation|"
    r"auditor.{0,25}\bresign|cessation of (the |statutory )?auditor|"
    r"change (in|of) (the |statutory )?auditor", re.I)
_ADVERSE = re.compile(
    r"qualified opinion|adverse opinion|disclaimer of opinion|"
    r"qualification.{0,25}audit|audit.{0,25}qualification|"
    r"modified opinion", re.I)


def _parse_dt(s: str | None) -> datetime | None:
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y"):
        try:
            return datetime.strptime(str(s).strip(), fmt)
        except Exception:
            continue
    return None


def fetch_announcements(symbol: str, session=None) -> list[dict]:
    """Recent NSE announcements for a symbol as {date, subject, detail}."""
    session = session or _nsf._new_session()
    try:
        r = session.get(ANN_URL.format(sym=symbol.upper()),
                        headers=_nsf.HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []
    out = []
    if isinstance(data, list):
        for row in data:
            out.append({
                "date": row.get("an_dt") or row.get("sort_date"),
                "subject": (row.get("desc") or "").strip(),
                "detail": (row.get("attchmntText") or "").strip(),
            })
    return out


def scan_auditor(symbol: str, session=None, months: int = 24) -> tuple[str, str, str | None]:
    """(state, detail, as_of). FLAG on a resignation / adverse-opinion filing in
    the window; otherwise NOT_CHECKED (never CLEAN — see module docstring)."""
    anns = fetch_announcements(symbol, session)
    if not anns:
        return ("NOT_CHECKED",
                "Could not read NSE announcements — verify the audit opinion in "
                "the annual report.", None)
    cutoff = datetime.now() - timedelta(days=int(months * 31))
    scanned = 0
    for a in anns:
        d = _parse_dt(a["date"])
        if d and d < cutoff:
            continue
        scanned += 1
        text = f'{a["subject"]}  {a["detail"]}'
        if _RESIGN.search(text):
            return ("FLAG",
                    f"Auditor change/resignation filed on NSE ({a['date']}): "
                    f"“{a['subject'][:90]}” — verify whether it is a resignation "
                    f"or routine rotation.", a["date"])
        if _ADVERSE.search(text):
            return ("FLAG",
                    f"Adverse / qualified audit-opinion filing on NSE "
                    f"({a['date']}): “{a['subject'][:90]}”.", a["date"])
    return ("NOT_CHECKED",
            f"Scanned {scanned} NSE announcements (~{months}m); no auditor-"
            f"resignation or adverse/qualified-opinion filing found. A qualified "
            f"opinion in the annual report may not be announced — verify there.",
            None)


if __name__ == "__main__":   # py -3 tools/nse_announcements.py RELIANCE GENSOL
    import sys
    for s in (sys.argv[1:] or ["RELIANCE"]):
        print(s, "->", scan_auditor(s))
