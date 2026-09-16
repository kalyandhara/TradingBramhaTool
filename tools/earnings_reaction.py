#!/usr/bin/env python3
"""earnings_reaction.py — UI-2: the earnings-reaction column group.

The one real DATA gap the ScreeningMantis comparison found
(analyses/ScreeningMantis-Table-Gap-Analysis.md). Their table carries
`NEXT EARN · PAST EARN · -1D% · E-DAY% · +1D%`; this desk had the earnings
CALENDAR already and none of the reaction.

Reads the events `earnings_calendar` has cached and measures the three sessions
around the last one against bars the caller already holds. **No network call** —
a table render must not fetch, and a symbol with no cached events reports
absent rather than being fetched on the spot.

══ THE DEFINITION, PINNED BECAUSE IT IS GENUINELY AMBIGUOUS ═════════════════════

Indian results are usually announced **after the close**, and yfinance does not
carry the announcement TIME. So "the reaction day" cannot be resolved from the
data, and any single number claiming to be it is asserting something the source
does not say.

This module therefore does NOT pick one. It reports all three sessions and lets
the reader see which one moved:

    -1D%    the session BEFORE the event date  — positioning / leak
    E-DAY%  the session ON the event date      — reaction only if pre-open/intraday
    +1D%    the session AFTER the event date   — reaction if announced post-close

**For a post-close announcement the real reaction is `+1D%`, and for most Indian
large-caps that is the common case.** The triplet is the honest rendering: three
facts, one of which is the reaction, and the reader can tell which from the
shape. Collapsing them into a single "reaction %" would be inventing the
announcement time.

Each is a CLOSE-to-CLOSE return, so E-DAY% already contains any gap.

══ WHAT COUNTS AS THE EVENT BAR ═════════════════════════════════════════════════

The event date may not be a trading day (a Saturday result, a holiday). The bar
used is the FIRST session on or after the event date, and `snapped_days` reports
how far it moved. A caller showing a snapped row can say so; a caller ignoring it
still gets a defensible number rather than a hole.

Beyond `MAX_SNAP_DAYS` the event is treated as unmatchable rather than snapped to
some distant session — a "reaction" measured a week later is not one.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Optional

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import earnings_calendar as ec

log = logging.getLogger("earnings_reaction")

#: How far the event date may be snapped forward to find a trading session.
#: 5 covers a Saturday result plus a long weekend and a holiday; past that the
#: link between the announcement and the bar is too weak to call a reaction.
MAX_SNAP_DAYS = 5

#: Beyond this age, a "most recent results date" is not describing the company's
#: reporting — it is describing a feed that stopped covering it.
#:
#: Measured 2026-09-10: for micro-caps yfinance's calendar is years stale.
#: GENESYS's newest event is 2018-08-14, CENTUM's 2017-05-30, KOPRAN's
#: 2019-05-08 — companies that have reported ~25 quarters since. Rendering
#: "Past earn. 2018-08-14" would state that the company last reported in 2018,
#: which is FALSE; it reports quarterly and the feed simply has nothing recent.
#:
#: A quarterly reporter's last result is at most ~120 days old, so 400 is
#: generous and unambiguous: past it, the calendar is absent for this name and
#: BLANK is the honest rendering. This suppresses the DATE, not the company —
#: the coverage gap is real either way, and a blank cell states it correctly
#: while a 2018 date states something else.
MAX_EVENT_AGE_DAYS = 400


def _read_any(symbol: str) -> Optional[dict]:
    """The cached payload regardless of age, or None if there is no file."""
    p = ec._cache_path(symbol)
    try:
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8")) or None
    except Exception as e:                                   # pragma: no cover
        log.debug("earnings cache read failed (%s): %s", symbol, e)
        return None


def age_days(symbol: str) -> Optional[int]:
    """How old the cached calendar is, in days. None when there is no cache.

    Exposed so a caller can caption "calendar as of N days ago" instead of
    presenting a possibly-superseded NEXT date as current fact.
    """
    p = ec._cache_path(symbol)
    try:
        if not p.exists():
            return None
        return int((time.time() - p.stat().st_mtime) // 86400)
    except Exception:                                        # pragma: no cover
        return None


def _events(symbol: str, use_cache_only: bool = True) -> list[dict]:
    """Cached events for a symbol, newest first. Never fetches when cache-only.

    Cache-only is the default because these feed a TABLE. A column that fetches
    per row turns one render into hundreds of network calls, which is the trap
    the Hub's pledge and RS-walk columns are both shaped to avoid.
    """
    if use_cache_only:
        # NOT `ec._read_cache`: that enforces a 12-hour TTL because it guards a
        # FETCH decision — stale means "go and refresh". This is a DISPLAY read,
        # and a past earnings date does not go stale. Gating it on freshness made
        # every column blank on a cache that was merely a day old, which is how
        # this was found. The NEXT date can drift, so `age_days` is exposed and
        # the column says how old the calendar is rather than hiding it.
        payload = _read_any(symbol)
    else:
        payload = ec.fetch_earnings(symbol)
    if not payload:
        return []
    evs = [e for e in (payload.get("events") or []) if ec._as_date(e.get("date"))]
    return sorted(evs, key=lambda e: ec._as_date(e["date"]), reverse=True)


def next_earnings(symbol: str, today: Optional[date] = None,
                  use_cache_only: bool = True) -> Optional[date]:
    """The earliest event dated on or after `today`, or None.

    Keyed on the DATE rather than on `reported is None`: a result can sit
    unreported in the feed for days after it was announced, and a "next
    earnings" in the past is worse than a blank cell.
    """
    today = today or date.today()
    future = [ec._as_date(e["date"]) for e in _events(symbol, use_cache_only)]
    future = sorted(d for d in future if d and d >= today)
    return future[0] if future else None


def last_earnings(symbol: str, today: Optional[date] = None,
                  use_cache_only: bool = True) -> Optional[date]:
    """The latest event dated strictly before `today`, or None.

    None also when that event is older than `MAX_EVENT_AGE_DAYS`: see the
    constant. A stale feed must not render as a stale company.
    """
    today = today or date.today()
    past = [ec._as_date(e["date"]) for e in _events(symbol, use_cache_only)]
    past = sorted((d for d in past if d and d < today), reverse=True)
    if not past:
        return None
    # A years-old "most recent" result is a coverage gap wearing a date. See
    # MAX_EVENT_AGE_DAYS — reporting it would assert something false about the
    # company rather than something true about the feed.
    if (today - past[0]).days > MAX_EVENT_AGE_DAYS:
        return None
    return past[0]


def _bar_index(df: pd.DataFrame, target: date) -> tuple[Optional[int], int]:
    """(index of the first session on/after `target`, days snapped forward).

    Returns (None, 0) when the frame has no such session inside MAX_SNAP_DAYS —
    including the case where the event is more recent than the last bar, which is
    normal for a result announced today and must not be mistaken for missing
    data.
    """
    if df is None or df.empty:
        return None, 0
    idx = df.index
    if not isinstance(idx, pd.DatetimeIndex):
        return None, 0
    days = pd.Index([d.date() for d in idx])
    for slip in range(MAX_SNAP_DAYS + 1):
        want = target + pd.Timedelta(days=slip).to_pytimedelta()
        hits = [i for i, d in enumerate(days) if d == want]
        if hits:
            return hits[0], slip
    return None, 0


def _close_return(df: pd.DataFrame, i: int) -> Optional[float]:
    """Close-to-close return of bar `i`, per cent. None at the frame's edge."""
    if i is None or i <= 0 or i >= len(df):
        return None
    try:
        prev = float(df["close"].iloc[i - 1])
        cur = float(df["close"].iloc[i])
    except (KeyError, ValueError, IndexError):
        return None
    if not prev or prev != prev or cur != cur:
        return None
    return round((cur / prev - 1.0) * 100.0, 2)


def reaction(symbol: str, df: pd.DataFrame, today: Optional[date] = None,
             use_cache_only: bool = True) -> dict[str, Any]:
    """The five-column group for one symbol.

    `df` must be a daily frame with a DatetimeIndex and a `close` column — the
    same frame the caller already fetched for its other columns. Nothing here
    downloads anything.

    Every field is independently optional: a symbol can have a known next date
    and no measurable past reaction (newly listed), or a past reaction and no
    scheduled next (calendar not published yet). Absent renders absent.
    """
    today = today or date.today()
    nxt = next_earnings(symbol, today, use_cache_only)
    last = last_earnings(symbol, today, use_cache_only)
    out: dict[str, Any] = {
        "next_earn": nxt,
        "past_earn": last,
        "earn_d_minus_1": None,
        "earn_day": None,
        "earn_d_plus_1": None,
        "snapped_days": 0,
    }
    if last is None or df is None or df.empty:
        return out
    i, slip = _bar_index(df, last)
    if i is None:
        return out
    out["snapped_days"] = slip
    out["earn_d_minus_1"] = _close_return(df, i - 1)
    out["earn_day"] = _close_return(df, i)
    out["earn_d_plus_1"] = _close_return(df, i + 1)
    return out


# ══ THE PEAD WALK ════════════════════════════════════════════════════════════
#
# `reaction()` above measures ONE event. The walk measures the last four, so the
# reader can see whether this name drifts after results at all — a single
# quarter's +8% is a coincidence, four in the same direction is a behaviour.
#
# ── THE MEASUREMENT, PINNED ──
#
#   D+1     close-to-close return of the session AFTER the event date.
#           This is the REACTION for a post-close announcement, which the
#           module docstring records as the common Indian large-cap case. The
#           walk commits to it — unlike the five-column group, which refuses to
#           pick — because a per-quarter triplet is four times as wide and the
#           question here is "does it drift", not "when was it announced".
#           That commitment is the walk's one real assumption; a name that
#           announces pre-open will have its reaction sitting in E-DAY instead
#           and read here as noise, not as drift.
#
#   D+5     cumulative close-to-close drift from the D+1 bar's close out five
#   D+20    (and twenty) further sessions. DRIFT IS MEASURED FROM THE REACTION
#           BAR'S CLOSE, NOT THE EVENT BAR'S — post-earnings-announcement drift
#           is by definition what happens AFTER the market has reacted. Folding
#           the jump into the drift would make every well-received result look
#           like it drifted, which is the classic way this effect is overstated.
#
# ── WHAT IS NOT MEASURED ──
#
# No surprise, no estimate, no direction expectation. yfinance's cached events
# carry no reliable consensus for Indian names, so this is a PRICE walk: what
# the stock did after each of its last four results. It says nothing about
# whether the result beat anything.
#
# ── UNBACKTESTED ──
#
# `consistency` counts agreement; it is NOT a validated signal and nothing in
# the pipeline scores or ranks on it. It is context on a card.

#: Sessions after the reaction bar that each drift leg spans.
DRIFT_LEGS = (5, 20)

#: Quarters walked by default. Four is one reporting year — enough for a
#: pattern to be visible and short enough to fit the ~300-bar frames the
#: pipeline already holds. A fifth quarter would routinely fall off the front
#: of those frames and render as a hole in every row.
WALK_QUARTERS = 4


def _drift_from(df: pd.DataFrame, i: int, sessions: int) -> Optional[float]:
    """Per-cent move from bar `i`'s close to bar `i + sessions`'s close.

    None when the frame ends first — a drift leg that runs past the last bar is
    INCOMPLETE, not zero, and the difference matters for a result announced
    three weeks ago whose +20 window is still running.
    """
    if i is None or i < 0:
        return None
    j = i + sessions
    if j >= len(df):
        return None
    try:
        base = float(df["close"].iloc[i])
        end = float(df["close"].iloc[j])
    except (KeyError, ValueError, IndexError):
        return None
    if not base or base != base or end != end:
        return None
    return round((end / base - 1.0) * 100.0, 2)


def pead_walk(symbol: str, df: pd.DataFrame, *, quarters: int = WALK_QUARTERS,
              today: Optional[date] = None,
              use_cache_only: bool = True) -> dict[str, Any]:
    """The post-earnings drift walk over the last `quarters` results.

    `df` is the daily frame the caller already holds — nothing here downloads
    anything, for the same reason `reaction()` does not: this feeds a render.

    Returns::

        {"symbol": str,
         "events": [{"date": date, "snapped_days": int,
                     "d1": float|None, "d5": float|None, "d20": float|None,
                     "complete": bool}, ...],   # newest first
         "consistency": int|None,   # of the events with a measurable d20, how
                                    # many drifted the SAME WAY as their own d1
         "measured": int}           # events with a d1 at all

    An empty `events` list is the honest answer for a name with no cached
    calendar, a stale one (see MAX_EVENT_AGE_DAYS), or a frame too short to
    reach back a year. Absent renders absent; the caller must not substitute a
    zero.
    """
    today = today or date.today()
    out: dict[str, Any] = {"symbol": symbol, "events": [],
                           "consistency": None, "measured": 0}
    if df is None or df.empty:
        return out

    past = [ec._as_date(e["date"]) for e in _events(symbol, use_cache_only)]
    past = sorted((d for d in past if d and d < today), reverse=True)
    # The same staleness rule `last_earnings` applies. A feed whose newest event
    # is from 2018 does not get to render a four-quarter walk of 2018 events.
    if not past or (today - past[0]).days > MAX_EVENT_AGE_DAYS:
        return out

    for ev in past[:quarters]:
        i, slip = _bar_index(df, ev)
        if i is None:
            continue                     # event outside the frame, or too new
        d1_i = i + 1
        row = {"date": ev, "snapped_days": slip,
               "d1": _close_return(df, d1_i), "complete": False}
        for leg in DRIFT_LEGS:
            row[f"d{leg}"] = (_drift_from(df, d1_i, leg)
                              if row["d1"] is not None else None)
        row["complete"] = all(row.get(f"d{leg}") is not None for leg in DRIFT_LEGS)
        out["events"].append(row)

    out["measured"] = sum(1 for r in out["events"] if r["d1"] is not None)
    agree = [r for r in out["events"]
             if r["d1"] is not None and r.get("d20") is not None and r["d1"] != 0]
    if agree:
        out["consistency"] = sum(1 for r in agree
                                 if (r["d20"] > 0) == (r["d1"] > 0))
        out["agreeable"] = len(agree)
    return out


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # pragma: no cover
        pass
    import argparse
    import json
    ap = argparse.ArgumentParser(description="Earnings reaction for one symbol")
    ap.add_argument("symbol")
    ap.add_argument("--bars", help="path to a cached _1d.json bar file "
                                   "(default: cache/cardinality/<SYM>_1d.json)")
    args = ap.parse_args()

    sym = args.symbol.upper()
    p = Path(args.bars) if args.bars else (
        HERE / "cache" / "cardinality" / f"{sym}_1d.json")
    df = None
    if p.exists():
        doc = json.loads(p.read_text(encoding="utf-8"))
        bars = doc.get("bars") or []
        df = pd.DataFrame({"close": [b["close"] for b in bars]},
                          index=pd.to_datetime([b["time"] for b in bars], unit="s"))
    else:
        print(f"no bars at {p} — dates only", file=sys.stderr)

    r = reaction(sym, df)
    print(f"{sym}")
    print(f"  next earnings : {r['next_earn'] or '—'}")
    print(f"  past earnings : {r['past_earn'] or '—'}"
          + (f"  (bar snapped +{r['snapped_days']}d)" if r["snapped_days"] else ""))
    for k, lab in (("earn_d_minus_1", "-1D%"), ("earn_day", "E-DAY%"),
                   ("earn_d_plus_1", "+1D%")):
        v = r[k]
        print(f"  {lab:>7} : {'—' if v is None else f'{v:+.2f}%'}")
    return 0


if __name__ == "__main__":                                   # pragma: no cover
    sys.exit(main())
