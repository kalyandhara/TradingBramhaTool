"""
yoga_dates.py — Ingest yoga-occurrence dates from Drik Panchang.

Two distinct Drik URL trees are handled:

  1. ``/panchang/yoga/daily/<name>-yoga-date-time.html``
     The 27 nakshatra yogas (Indra, Shool, ...). Markup uses
     ``dpCard dpElementCard`` with per-card permalink dates. Parser:
     ``_parse_element_card_page``.

  2. ``/yoga/<name>-yoga-date-time.html``
     The 8 auspicious / muhurta yogas in ASTRO_TRADING_GUIDE.md
     (Ravi, Sarvartha Siddhi, Amrit Siddhi, Dwipushkar, Tripushkar,
     Ravi Pushya, Guru Pushya, Maitreya). Markup uses ``dpAstroCard``
     with the full date in the title text. Parser: ``_parse_astro_card_page``.

Each occurrence becomes a :class:`YogaOccurrence` with start/end datetimes
and a derived *reverse-date* (next calendar day — per the cheat-sheet, the
trading day on which the market is expected to reverse, with daily H/L
break needed for confirmation).

Public API:
    from yoga_dates import (get_yoga_occurrences, upcoming_reverse_dates,
                             YOGA_SOURCES)
    occs = get_yoga_occurrences("dwipushkar", 2026)
    soon = upcoming_reverse_dates(list(YOGA_SOURCES), date.today(), days=60)

CLI:
    py -3 tools/yoga_dates.py dwipushkar 2026         # print table
    py -3 tools/yoga_dates.py indra 2026 --csv        # also dump CSV
    py -3 tools/yoga_dates.py ravipushya 2026 --refresh   # bypass cache
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import time
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

log = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / "cache" / "yoga"
CACHE_TTL_SECONDS = 30 * 24 * 3600

# Maps internal yoga key → (kind, URL path, display name).
#
#   kind ∈ {"element_card", "astro_card"} — selects the parser, since the
#   two Drik URL trees use materially different per-occurrence markup.
#
#   Adding a new yoga: visit the page in a browser, look at one occurrence
#   block's outermost <div class="dp...Card..."> class name to determine
#   the kind. Verify both with a small `curl ... | grep -c dpAstroCard`
#   (or dpElementCard) before adding — Drik 404s on unknown slugs, so the
#   loader fails loudly on bad ones, but a working URL with the wrong
#   parser fails silently with 0 occurrences.
YOGA_SOURCES: dict[str, tuple[str, str, str]] = {
    # /panchang/yoga/daily/ tree — the 27 nakshatra yogas (dpElementCard)
    "indra":           ("element_card",
                        "/panchang/yoga/daily/indra-yoga-date-time.html",
                        "Indra Yoga"),
    # /yoga/ tree — the 8 auspicious / muhurta yogas (dpAstroCard)
    "ravi":            ("astro_card",
                        "/yoga/ravi-yoga-date-time.html",
                        "Ravi Yoga"),
    "sarvarthasiddhi": ("astro_card",
                        "/yoga/sarvarthasiddhi-yoga-date-time.html",
                        "Sarvartha Siddhi Yoga"),
    "amritsiddhi":     ("astro_card",
                        "/yoga/amritsiddhi-yoga-date-time.html",
                        "Amrit Siddhi Yoga"),
    "dwipushkar":      ("astro_card",
                        "/yoga/dwipushkar-yoga-date-time.html",
                        "Dwipushkar Yoga"),
    "tripushkar":      ("astro_card",
                        "/yoga/tripushkar-yoga-date-time.html",
                        "Tripushkar Yoga"),
    "ravipushya":      ("astro_card",
                        "/yoga/ravipushya-yoga-date-time.html",
                        "Ravi Pushya Yoga"),
    "gurupushya":      ("astro_card",
                        "/yoga/gurupushya-yoga-date-time.html",
                        "Guru Pushya Yoga"),
    "maitreya":        ("astro_card",
                        "/yoga/maitreya-yoga-date-time.html",
                        "Maitreya Yoga"),
}

DRIK_BASE = "https://www.drikpanchang.com"


def display_name(yoga: str) -> str:
    """Pretty name for UI / DB rows / CSV output."""
    entry = YOGA_SOURCES.get(yoga.lower())
    return entry[2] if entry else yoga.title()

# Each occurrence is rendered as a <div class="dpCard dpElementCard"> block.
# Inside it, the page embeds:
#   • a permalink whose query string is the unambiguous start date:
#       <a href="/panchang/day-panchang.html?date=DD/MM/YYYY" ...>
#   • two <div class="dpValue ...">HH:MM <span>AM/PM</span>, <span>Mon DD</span></div>
#     blocks — the first is "Begins", the second is "Ends". The visible time
#     is split across span tags, so we strip HTML before matching the time.
#
# Pulling the year from the URL (not the ?year= request param) handles the
# year-boundary edge case correctly: an Indra Yoga that *starts* on Dec 30
# of year N appears under the year-N listing but its End span shows the next
# day, which can be Jan 1 of year N+1. With the start date from the URL and
# the end-day month from the End span text, we resolve end-year ourselves.
# Nested <div> structure inside each card means regex can't reliably balance
# the closing tag. Instead, split the page on the card *opening* and treat
# each segment up to the next opening (or end of page) as one card — the
# downstream parsing only cares about the URL date and the two dpValue
# blocks inside, both of which are contained within that slice.
_CARD_OPEN_RE = re.compile(r'<div class="dpCard[^"]*?dpElementCard"[^>]*?>',
                           re.DOTALL)
_DATE_URL_RE = re.compile(r"date=(\d{1,2})/(\d{1,2})/(\d{4})")
_VALUE_RE = re.compile(
    r'<div class="dpValue[^"]*?">(.*?)</div>',
    re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")
_TIME_RE = re.compile(
    r"(\d{1,2}):(\d{2})\s*([AP]M)\s*,\s*([A-Z][a-z]{2})\s*(\d{1,2})",
    re.IGNORECASE,
)
_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}


def _strip_tags(s: str) -> str:
    """Strip HTML tags and collapse &nbsp; into a normal space."""
    return _TAG_RE.sub("", s).replace("\xa0", " ").replace("&nbsp;", " ").strip()


@dataclass
class YogaOccurrence:
    yoga: str
    year: int
    start: datetime
    end: datetime

    @property
    def reverse_date(self) -> date:
        """Per ASTRO_TRADING_GUIDE.md §2: reverse-date = next calendar day
        after the yoga appears, *regardless of holidays/weekends*."""
        return self.start.date() + timedelta(days=1)

    @property
    def weekday(self) -> str:
        return self.start.strftime("%A")

    def to_dict(self) -> dict:
        return {
            "yoga": self.yoga,
            "year": self.year,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "reverse_date": self.reverse_date.isoformat(),
            "weekday": self.weekday,
        }


def _parse_value_block(block: str) -> tuple[int, int, str, int, int] | None:
    """A dpValue block looks like "09:05 <span>AM</span>, <span>Jan 03</span>".
    Strip tags then run the time regex. Returns (hour, minute, month_abbr,
    day, _) or None if it doesn't look like one of these blocks."""
    text = _strip_tags(block)
    m = _TIME_RE.search(text)
    if not m:
        return None
    hh, mm, ampm, mon_abbr, dd = m.groups()
    hour = int(hh) % 12 + (12 if ampm.upper() == "PM" else 0)
    return hour, int(mm), mon_abbr.title(), int(dd), 0


def _parse_element_card_page(html: str, yoga: str, year: int) -> list[YogaOccurrence]:
    """Parser for the /panchang/yoga/daily/ tree (dpElementCard markup).

    Pulls each occurrence card, reads its start date from the per-card
    permalink URL, and the start/end times from the two dpValue blocks
    inside."""
    occurrences: list[YogaOccurrence] = []

    # Split on the card opening: parts[0] is the page chrome before any card,
    # parts[1:] are each card's body up to the next card (last card's body
    # bleeds into the page footer, but the URL+values inside it parse fine
    # because we read targeted sub-blocks rather than the whole slice).
    parts = _CARD_OPEN_RE.split(html)
    for card in parts[1:]:
        m_url = _DATE_URL_RE.search(card)
        if not m_url:
            continue
        d_day, d_mon, d_year = (int(x) for x in m_url.groups())
        start_date_from_url = date(d_year, d_mon, d_day)

        values = _VALUE_RE.findall(card)
        if len(values) < 2:
            continue
        begin = _parse_value_block(values[0])
        end = _parse_value_block(values[1])
        if not begin or not end:
            continue

        b_hour, b_min, b_mon, b_day, _ = begin
        e_hour, e_min, e_mon, e_day, _ = end

        # The Begins span's date should equal the URL date. (Sanity check.)
        if _MONTHS[b_mon] != d_mon or b_day != d_day:
            log.debug("card date mismatch: url=%s/%d span=%s/%d — skipping",
                      d_mon, d_day, b_mon, b_day)
            continue

        start = datetime(d_year, d_mon, d_day, b_hour, b_min)

        # End-day's month may roll into the next month, which itself may roll
        # into the next year (Dec -> Jan). Choose the smallest end-date >=
        # start that matches the End span's month+day.
        e_month_num = _MONTHS[e_mon]
        for candidate_year in (d_year, d_year + 1):
            try:
                end = datetime(candidate_year, e_month_num, e_day, e_hour, e_min)
            except ValueError:
                continue
            if timedelta(0) < end - start < timedelta(days=2):
                break
        else:
            log.debug("could not resolve end timestamp for %s — skipping", start)
            continue

        occurrences.append(YogaOccurrence(yoga=yoga, year=year, start=start, end=end))

    # De-duplicate (defensive — the page is clean today but tooltips/markup
    # can change). Sort by start time for stable output.
    seen = set()
    unique = []
    for occ in occurrences:
        key = (occ.start, occ.end)
        if key in seen:
            continue
        seen.add(key)
        unique.append(occ)
    unique.sort(key=lambda o: o.start)
    return unique


# ── /yoga/ tree parser (dpAstroCard markup) ───────────────────────────────────
# Two sub-variants seen on this tree:
#
#   Variant A (Dwipushkar, Ravi, Sarvartha-Siddhi, Amrit-Siddhi, Tripushkar,
#              Ravi-Pushya, Guru-Pushya): a single content block
#       <div class="dpAstroCardContent">HH:MM <span>AM/PM</span>
#         <span>to </span>
#         <span>HH:MM <span>AM/PM</span>[, <span>Mon DD</span>]</span>
#       </div>
#   Variant B (Maitreya): two separate content blocks
#       <div class="...dpAstroCardMoment...">Begin: HH:MM AM/PM</div>
#       <div class="...dpAstroCardMoment...">End:   HH:MM AM/PM</div>
#     (no end-date suffix — same-day end assumed)
#
# Both share: a title block carrying the full English date.
# Match ANY dpAstroCardTitle div. We then filter out non-date titles (section
# headers like "Maitreya Yoga Days") in the loop body by requiring the title
# text to match the "Month DD, YYYY, Weekday" pattern. Doing the filtering
# here keeps the regex robust against title-class variants we haven't seen
# yet (Maitreya uses `dpFlexEqual dpAstroCardTitle `, others use
# `dpAstroCardTitle dpAstroCardTitleExt`, etc.).
_ASTRO_TITLE_SPLIT_RE = re.compile(
    r'<div class="[^"]*dpAstroCardTitle[^"]*"[^>]*>',
    re.DOTALL,
)
_ASTRO_TITLE_TEXT_RE = re.compile(
    r"([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4}),\s*([A-Z][a-z]+)",
)
_ASTRO_CONTENT_BLOCK_RE = re.compile(
    r'<div class="[^"]*dpAstroCardContent[^"]*"[^>]*>(.*?)</div>',
    re.DOTALL,
)
_TIME_ONLY_RE = re.compile(r"(\d{1,2}):(\d{2})\s*([AP]M)", re.IGNORECASE)
_FULL_MONTH_NAMES = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11,
    "December": 12,
}


def _time_at(date_obj: date, hour: int, minute: int) -> datetime:
    return datetime(date_obj.year, date_obj.month, date_obj.day, hour, minute)


def _parse_astro_card_page(html: str, yoga: str, year: int) -> list[YogaOccurrence]:
    """Parser for the /yoga/ tree (auspicious-yoga dpAstroCard markup).

    The title contains the full English date so we don't need to guess
    years from URL params. Variant detection is per-card: presence of
    "Begin:"/"End:" labels in separate content blocks switches us to
    the Maitreya-style two-block path."""
    occurrences: list[YogaOccurrence] = []

    parts = _ASTRO_TITLE_SPLIT_RE.split(html)
    # parts[0] is page chrome before the first title; parts[1:] is body-after-
    # title-open for each entry, bleeding into the next entry (we re-cut on
    # the next title's content via the split).
    for body in parts[1:]:
        # The body starts INSIDE the title div — first chunk until </div> is
        # the title text.
        title_end = body.find("</div>")
        if title_end < 0:
            continue
        title_text = _strip_tags(body[:title_end])
        m_title = _ASTRO_TITLE_TEXT_RE.search(title_text)
        if not m_title:
            continue
        mon_name, day_str, year_str, _weekday = m_title.groups()
        try:
            start_date = date(int(year_str), _FULL_MONTH_NAMES[mon_name], int(day_str))
        except (KeyError, ValueError):
            continue

        # Cards typically have ≤3 content blocks before the next title.
        content_blocks = _ASTRO_CONTENT_BLOCK_RE.findall(body[title_end:])[:3]
        if not content_blocks:
            continue

        # Variant B: separate "Begin:" / "End:" blocks
        begin_text = end_text = None
        for blk in content_blocks:
            txt = _strip_tags(blk)
            if "Begin" in txt and begin_text is None:
                begin_text = txt
            elif "End" in txt and end_text is None:
                end_text = txt

        if begin_text and end_text:
            mb = _TIME_ONLY_RE.search(begin_text)
            me = _TIME_ONLY_RE.search(end_text)
            if not mb or not me:
                continue
            bh, bm, bap = mb.groups()
            eh, em, eap = me.groups()
            start = _time_at(start_date,
                             int(bh) % 12 + (12 if bap.upper() == "PM" else 0),
                             int(bm))
            end = _time_at(start_date,
                           int(eh) % 12 + (12 if eap.upper() == "PM" else 0),
                           int(em))
            # If end comes out earlier than start, end is next day.
            if end <= start:
                end += timedelta(days=1)
            occurrences.append(YogaOccurrence(yoga=yoga, year=year, start=start, end=end))
            continue

        # Variant A: single content block with "HH:MM AM ... to ... HH:MM AM[, Mon DD]"
        # Use the first content block that contains both a time and " to ".
        for blk in content_blocks:
            txt = _strip_tags(blk)
            if " to " not in txt:
                continue
            before, after = txt.split(" to ", 1)
            mb = _TIME_ONLY_RE.search(before)
            me = _TIME_ONLY_RE.search(after)
            if not mb or not me:
                break
            bh, bm, bap = mb.groups()
            eh, em, eap = me.groups()
            start = _time_at(start_date,
                             int(bh) % 12 + (12 if bap.upper() == "PM" else 0),
                             int(bm))
            # Optional ", Mon DD" suffix tells us the end date explicitly.
            m_endday = re.search(
                r",\s*([A-Z][a-z]{2})\s*(\d{1,2})", after,
            )
            end_year = start_date.year
            if m_endday:
                end_mon = _MONTHS[m_endday.group(1).title()]
                end_day = int(m_endday.group(2))
                # Dec→Jan rollover
                if start_date.month == 12 and end_mon == 1:
                    end_year += 1
                end_date_obj = date(end_year, end_mon, end_day)
            else:
                end_date_obj = start_date  # same-day
            end = _time_at(end_date_obj,
                           int(eh) % 12 + (12 if eap.upper() == "PM" else 0),
                           int(em))
            if end <= start:
                end += timedelta(days=1)  # crossed midnight on a same-day entry
            occurrences.append(YogaOccurrence(yoga=yoga, year=year, start=start, end=end))
            break

    occurrences.sort(key=lambda o: o.start)
    return occurrences


_PARSERS = {
    "element_card": _parse_element_card_page,
    "astro_card":   _parse_astro_card_page,
}


def _cache_path(yoga: str, year: int) -> Path:
    return CACHE_DIR / f"{yoga}_{year}.json"


def _read_cache(yoga: str, year: int) -> list[YogaOccurrence] | None:
    p = _cache_path(yoga, year)
    if not p.exists():
        return None
    if time.time() - p.stat().st_mtime > CACHE_TTL_SECONDS:
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return [YogaOccurrence(
            yoga=row["yoga"], year=row["year"],
            start=datetime.fromisoformat(row["start"]),
            end=datetime.fromisoformat(row["end"]),
        ) for row in data]
    except Exception as e:
        log.warning("yoga cache read failed for %s/%d: %s", yoga, year, e)
        return None


def _write_cache(yoga: str, year: int, occurrences: list[YogaOccurrence]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data = [{"yoga": o.yoga, "year": o.year,
             "start": o.start.isoformat(), "end": o.end.isoformat()}
            for o in occurrences]
    _cache_path(yoga, year).write_text(json.dumps(data, indent=2), encoding="utf-8")


def fetch_yoga(yoga: str, year: int) -> list[YogaOccurrence]:
    """Fetch + parse the page for one yoga in one year. No caching at this layer."""
    entry = YOGA_SOURCES.get(yoga.lower())
    if not entry:
        raise ValueError(
            f"Unknown yoga {yoga!r}. Known: {list(YOGA_SOURCES)}. "
            f"Add the (kind, url, display) entry to YOGA_SOURCES to enable new ones."
        )
    kind, url_path, _name = entry
    parser = _PARSERS[kind]
    r = requests.get(DRIK_BASE + url_path,
                     params={"year": str(year)},
                     timeout=15,
                     headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return parser(r.text, yoga.lower(), year)


def get_yoga_occurrences(yoga: str, year: int, *, refresh: bool = False
                         ) -> list[YogaOccurrence]:
    """Cache-aware fetch. `refresh=True` forces a re-fetch."""
    if not refresh:
        cached = _read_cache(yoga.lower(), year)
        if cached is not None:
            return cached
    occurrences = fetch_yoga(yoga, year)
    _write_cache(yoga.lower(), year, occurrences)
    return occurrences


def upcoming_reverse_dates(yogas: list[str], from_date: date,
                           days: int = 60) -> list[YogaOccurrence]:
    """Reverse-dates between [from_date, from_date+days) across the listed yogas.

    Spans year boundaries automatically by fetching whichever calendar years
    the window touches."""
    end = from_date + timedelta(days=days)
    years = sorted({from_date.year, end.year})

    found: list[YogaOccurrence] = []
    for yoga in yogas:
        for yr in years:
            try:
                for occ in get_yoga_occurrences(yoga, yr):
                    if from_date <= occ.reverse_date < end:
                        found.append(occ)
            except Exception as e:
                log.warning("could not load %s/%d: %s", yoga, yr, e)
    return sorted(found, key=lambda o: o.reverse_date)


# ── CLI ────────────────────────────────────────────────────────────────────────

def _cli() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("yoga", choices=sorted(YOGA_SOURCES),
                   help="yoga key (e.g. 'indra', 'dwipushkar')")
    p.add_argument("year", type=int, help="calendar year (e.g. 2026)")
    p.add_argument("--refresh", action="store_true",
                   help="bypass cache and re-fetch from drikpanchang.com")
    p.add_argument("--csv", action="store_true",
                   help="also write a sibling CSV next to the JSON cache")
    args = p.parse_args()

    occs = get_yoga_occurrences(args.yoga, args.year, refresh=args.refresh)
    print(f"{display_name(args.yoga)} — {args.year} — {len(occs)} occurrences\n")
    print(f"{'Start':<22} {'End':<22} {'Reverse-Date':<14} Weekday")
    print("-" * 70)
    for o in occs:
        print(f"{o.start.strftime('%Y-%m-%d %H:%M'):<22} "
              f"{o.end.strftime('%Y-%m-%d %H:%M'):<22} "
              f"{o.reverse_date.isoformat():<14} {o.weekday}")

    if args.csv:
        csv_path = CACHE_DIR / f"{args.yoga}_{args.year}.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["yoga", "year", "start", "end", "reverse_date", "weekday"])
            for o in occs:
                w.writerow([o.yoga, o.year, o.start.isoformat(),
                            o.end.isoformat(), o.reverse_date.isoformat(), o.weekday])
        print(f"\nCSV: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
