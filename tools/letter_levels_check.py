#!/usr/bin/env python3
"""letter_levels_check.py — recompute an outside letter's option levels (B-94)

[[sources/Bramesh-NIFTY-Gann-1x3-Higher-High-2026-09-18]] printed three
option-chain levels for the 2026-09-18 NIFTY session:

    max pain    23,300
    call wall   23,500   (its "primary ceiling")
    put wall    23,100   (its "major institutional floor")

Ten levels were quoted in that letter and **these three are the only ones this
desk can reproduce** — the Gann angles state no scaling and the trend-change
levels state no construction, so they are not checkable even in principle. That
asymmetry is the point: this is the cheapest reliability test available on a
source, and it scores the source against a tool that already exists rather than
against an opinion.

══ THIS FILE IS THE PRE-REGISTRATION ═══════════════════════════════════════════

Committed before it was run. The match rule and the reading bands below were
fixed in advance so the verdict could not be chosen after seeing the gap.

══ PRE-REGISTERED DESIGN ══════════════════════════════════════════════════════

  SOURCE SESSION   **2026-09-17**, primary. The letter is dated 2026-09-18 and
                   quotes the 2026-09-17 close (NIFTY 23,270, +61), so the
                   chain its author could actually see is the 17th's. Scoring
                   it against the 18th would be marking a forecast against data
                   that did not exist when it was written.
  ALSO REPORTED    2026-09-18 (did the levels describe the session they were
                   offered for?) and 2026-09-16 (is the number stable, or does
                   it move every session?). Neither can change the verdict.
  EXPIRY           the NEAREST, which for all three sessions is 2026-09-22 —
                   checked before writing this, so there is no expiry-day
                   ambiguity to resolve after the fact. The next expiry
                   (2026-09-29) is reported alongside, because a level that
                   only reproduces on a far month is a different claim.
                   Max pain is NEVER computed on pooled expiries; `option_chain`
                   refuses that, and this file does not work around it.
  TOOL             `option_chain.read_levels`, unmodified. Nothing is
                   reimplemented here — the same rule B-59 and B-97 followed.

  MATCH RULE (NIFTY strikes are 50 apart):
    EXACT    same strike
    NEAR     within one strike step (±50)
    MISS     further than one step

  READING, fixed in advance:
    3 of 3 EXACT            REPRODUCED — the block is sound, cite it
    >= 2 EXACT, rest NEAR   SUBSTANTIALLY REPRODUCED
    >= 2 within NEAR        LOOSE — right neighbourhood, not the same number
    otherwise               NOT REPRODUCED

  What a miss does NOT mean: the letter's levels could be computed off a live
  NSE option chain intraday, while this reads the settled bhavcopy. A gap is
  therefore evidence about REPRODUCIBILITY, not proof of an error, and the
  write-up must say so.

CLI:
  py -3 -X utf8 tools/letter_levels_check.py
"""
from __future__ import annotations

import datetime as dt
import sys

import option_chain as oc

#: What the letter printed. Frozen here so the comparison cannot drift.
LETTER = {"max_pain": 23300.0, "call_wall": 23500.0, "put_wall": 23100.0}
LETTER_SOURCE = "sources/Bramesh-NIFTY-Gann-1x3-Higher-High-2026-09-18"

#: NIFTY strike step. The NEAR band is exactly one step.
STRIKE_STEP = 50.0

PRIMARY_SESSION = "2026-09-17"
SESSIONS = ("2026-09-16", "2026-09-17", "2026-09-18")
NEAR_EXPIRY = "2026-09-22"
NEXT_EXPIRY = "2026-09-29"


def classify(ours: float | None, theirs: float) -> str:
    if ours is None:
        return "NO READ"
    gap = abs(ours - theirs)
    if gap < 1e-9:
        return "EXACT"
    if gap <= STRIKE_STEP + 1e-9:
        return "NEAR"
    return "MISS"


def verdict(marks: list[str]) -> tuple[str, str]:
    """The pre-registered bands. `marks` is the three primary classifications."""
    if "NO READ" in marks:
        return "INCONCLUSIVE", "a level could not be computed at all"
    exact = marks.count("EXACT")
    within = exact + marks.count("NEAR")
    if exact == 3:
        return ("REPRODUCED",
                "all three levels recomputed to the same strike — the "
                "option-chain block of this letter is sound and can be cited")
    if exact >= 2 and within == 3:
        return ("SUBSTANTIALLY REPRODUCED",
                f"{exact} of 3 exact and the rest within one strike")
    if within >= 2:
        return ("LOOSE",
                f"only {exact} exact; {within} of 3 land within one strike — "
                "the right neighbourhood, not the same numbers")
    return ("NOT REPRODUCED",
            f"{exact} exact, {within} of 3 within one strike")


# ══ SECONDARY — added 2026-09-19, AFTER the primary run ══════════════════════
#
# Declared post-hoc, because it is. The primary came back with max pain EXACT
# and BOTH walls MISS, which is a strange shape: a max pain that lands on the
# same strike is strong evidence the author read the same chain with the same
# definition, and that makes two badly-missed walls look like a DEFINITIONAL
# gap rather than a data gap.
#
# The obvious candidate: `oi_walls` ranks the WHOLE chain, so on 2026-09-17 it
# returns 24,500 (10.4M) for calls and 22,000 (10.9M) for puts — strikes 5%
# away, which are far-OTM weekly inventory rather than anything defending a
# level. Most published "OI walls" are near-the-money.
#
# **This tests exactly one alternative, and it is not a swept parameter.**
# `option_chain.NEAR_STRIKES` already exists in the module (10 strikes each
# side, for its own "near" summary) and was written long before this letter.
# Trying window sizes until one fit would be fitting the source's number; using
# the constant the module already had is a test of a hypothesis.
def near_window_walls(raw, expiry: str) -> dict[str, float | None]:
    """Walls re-ranked inside the module's own ±NEAR_STRIKES window."""
    ch = oc.load_chain(raw, "NIFTY", expiry=expiry)
    if not ch:
        return {"call": None, "put": None}
    df, spot = ch.get("strikes"), ch.get("spot")
    if df is None or df.empty or not spot:
        return {"call": None, "put": None}
    n = oc.NEAR_STRIKES
    above = sorted(df[df["strike"] >= spot]["strike"])[:n]
    below = sorted(df[df["strike"] <= spot]["strike"])[-n:]
    w = df[df["strike"].isin(set(above) | set(below))]
    c = w[w["strike"] >= spot].nlargest(1, "call_oi")
    p = w[w["strike"] <= spot].nlargest(1, "put_oi")
    return {"call": float(c["strike"].iloc[0]) if not c.empty else None,
            "put": float(p["strike"].iloc[0]) if not p.empty else None}


def read(raw, expiry: str, trade_date) -> dict | None:
    return oc.read_levels("NIFTY", expiry=expiry, walls=3, raw=raw,
                          trade_date=trade_date)


def top_strike(rows, key: str) -> float | None:
    """The #1 wall from `read_levels`' ranked list, or None."""
    if not rows:
        return None
    r = rows[0]
    return float(r.get("strike")) if isinstance(r, dict) else float(r)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # pragma: no cover
        pass

    import requests
    import nse_oi_momentum as oi

    session = requests.Session()
    print(f"\nB-94 · recomputing [[{LETTER_SOURCE}]]'s option levels")
    print(f"  letter: max pain {LETTER['max_pain']:,.0f} · "
          f"call wall {LETTER['call_wall']:,.0f} · "
          f"put wall {LETTER['put_wall']:,.0f}")
    print(f"  primary session {PRIMARY_SESSION} (the close the letter quotes), "
          f"nearest expiry {NEAR_EXPIRY}\n")

    primary_marks: list[str] = []
    for sess in SESSIONS:
        day = dt.datetime.fromisoformat(sess)
        raw = oi._download_bhavcopy(session, day)
        if raw is None:
            print(f"  {sess}  no settled file")
            continue
        for expiry, tag in ((NEAR_EXPIRY, "near"), (NEXT_EXPIRY, "next")):
            r = read(raw, expiry, day)
            if not r:
                print(f"  {sess} / {expiry} ({tag})  no chain")
                continue
            mp = r.get("max_pain")
            cw = top_strike(r.get("resistance"), "resistance")
            pw = top_strike(r.get("support"), "support")
            marks = [classify(mp, LETTER["max_pain"]),
                     classify(cw, LETTER["call_wall"]),
                     classify(pw, LETTER["put_wall"])]
            star = "*" if (sess == PRIMARY_SESSION and expiry == NEAR_EXPIRY) else " "
            print(f" {star}{sess} / {expiry} ({tag})  spot "
                  f"{r.get('spot') or float('nan'):,.0f}")
            print(f"      max pain  {mp!s:>9}  vs {LETTER['max_pain']:,.0f}  {marks[0]}")
            print(f"      call wall {cw!s:>9}  vs {LETTER['call_wall']:,.0f}  {marks[1]}")
            print(f"      put wall  {pw!s:>9}  vs {LETTER['put_wall']:,.0f}  {marks[2]}")
            if star == "*":
                primary_marks = marks

    # Secondary, post-hoc: the same walls inside the module's own near window.
    day = dt.datetime.fromisoformat(PRIMARY_SESSION)
    raw = oi._download_bhavcopy(session, day)
    if raw is not None:
        nw = near_window_walls(raw, NEAR_EXPIRY)
        print(f"\n── SECONDARY (post-hoc): walls re-ranked inside the module's "
              f"own ±{oc.NEAR_STRIKES}-strike window, {PRIMARY_SESSION} ──")
        print(f"      call wall {nw['call']!s:>9}  vs "
              f"{LETTER['call_wall']:,.0f}  {classify(nw['call'], LETTER['call_wall'])}")
        print(f"      put wall  {nw['put']!s:>9}  vs "
              f"{LETTER['put_wall']:,.0f}  {classify(nw['put'], LETTER['put_wall'])}")

    if not primary_marks:
        print("\nVERDICT: INCONCLUSIVE — the primary session did not read.")
        return 1
    v, why = verdict(primary_marks)
    print(f"\nVERDICT ({PRIMARY_SESSION}, expiry {NEAR_EXPIRY}): {v}\n  {why}")
    print("  A gap is evidence about REPRODUCIBILITY, not proof of an error: "
          "the letter may have read a live intraday chain, this reads the "
          "settled bhavcopy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
