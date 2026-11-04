"""indicator_evidence.py — the NSE evidence line for each Chart Tool indicator (B-154).

    py -3 tools/indicator_evidence.py      # print every mapped key + self-check

The Indicator Browser shows, for every indicator, one plain-words line on what the
desk has MEASURED about it on NSE data — shown to every user, beginner or not
(owner decision 2026-10-13). This module is that line's single source.

── The rule for mapping ──────────────────────────────────────────────────────────
A key is mapped to a study ONLY where the study tested what the overlay draws or
signals. Close is not enough:

  * `oiwalls` is NOT mapped to B-94 — that checked the walls and max pain are
    COMPUTED right against an outside source, not whether price respects them.
  * `cpr` is NOT mapped to B-97 — that compared daily with weekly floor pivots,
    not the CPR band's effect on the next session.
  * `deltaprofile` is NOT mapped to B-48 — that probed cumulative volume delta
    estimated from NSE bars; the overlay draws Hyperliquid's real taker side.
  * `structure_chain` is NOT mapped to the CHoCH studies — they scored the
    "Bullish CHoCH (last 5 sessions)" scanner's own pivot-5 walk, a different
    detector from the overlay's `detect_structure_chain` (B-114 measured that one).
  * `vwap` / `ema20` are NOT mapped to B-90 — that scored the VWAP+EMA20
    AGREEMENT state, which was never built; the overlays draw the lines alone.
  * `ew2deg` is NOT mapped to B-134/B-135 — those ran the Elliott engine at its
    default swing size, which is what `elliott` draws; the larger degree was not
    scored.
  * `simplevol` is NOT mapped to B-122 — that scored the No-Supply FILTER on the
    new-high family, not the coloured bars; the pocket-pivot studies themselves
    are UNRECORDED.

Everything unmapped reads "Not measured on NSE yet", which is the honest default.

── Why the line is written by hand AND checked ───────────────────────────────────
A plain sentence needs a person; a verdict needs to stay true. So each entry
carries `expect`, the combined verdict the line was written against, and
`self_check()` recomputes it from `named_studies.STUDIES`. If a study is re-run
and its verdict changes, or a subject is renamed out of the index, claims_lint
reports the line as stale instead of the browser quietly showing it.
"""
from __future__ import annotations

import sys

import named_studies as ns

#: key → subjects (EXACT names in named_studies.STUDIES), the verdict the line was
#: written against, and the line itself. Items are cited from the index, not here.
EVIDENCE: dict[str, dict] = {
    "structure_chain": {
        "subjects": ("structure break chain reading",), "expect": "POSITIVE",
        "line": "A break that held went on to beat one that failed, and beat simply "
                "holding the stock over 20 days (about +0.8 points). The quality "
                "grade did not rank breaks — read held vs failed, not the grade.",
    },
    "orderblock": {
        "subjects": ("order block target ladder", "order block stacked-zone bias",
                     "order block rejection entry"), "expect": "NEGATIVE",
        "line": "The order-block trade plan lost money after costs, and the "
                "stacked-zone bias pointed the wrong way, so it was retired.",
    },
    "liquidity": {
        "subjects": ("Liquidity Sweep",), "expect": "MIXED",
        "line": "The bullish sweep is one of the few signals on this desk that beat "
                "costs (+0.51% over 20 days). The stop-based plan drawn with it did not: "
                "the stop itself cost the edge.",
    },
    "pmax": {
        "subjects": ("pmaxSeries",), "expect": "NEGATIVE",
        "line": "Trading PMax's flips did worse than simply holding the same "
                "stock, and using its line as a stop was worse again.",
    },
    "psar": {
        "subjects": ("psar",), "expect": "NULL",
        "line": "Where Parabolic SAR and SuperTrend AI disagree, "
                "neither one's call carried information.",
    },
    "stai": {
        "subjects": ("stai",), "expect": "NULL",
        "line": "Where SuperTrend AI and Parabolic SAR disagree, "
                "neither one's call carried information.",
    },
    "renko": {
        "subjects": ("Renko Flip (structure change)", "Shallow Flip (Renko, bounded correction)"),
        "expect": "NEGATIVE",
        "line": "Renko flips never beat buy-and-hold, and filtering out "
                "sideways chop made them worse, not better.",
    },
    "svp": {
        "subjects": ("SVP.buildSignal", "SVPSTRUCT.read"), "expect": "NEGATIVE",
        "line": "Both its BUY/SELL signal and its structure read pointed the "
                "wrong way more often than not. Read the profile shapes as "
                "description, not as signals.",
    },
    "flag_pole": {
        "subjects": ("Flag & Pole", "Inverted Flag & Pole"), "expect": "MIXED",
        "line": "Bull flags only just passed (+0.71% over 20 days); bear flags "
                "were followed by gains — the opposite of what the pattern claims.",
    },
    "adxdi": {
        "subjects": ("adxdi",), "expect": "MIXED",
        "line": "The bare +DI/−DI cross lost money; a confirmed up-trend state "
                "was positive over 60 days.",
    },
    "fvg": {
        "subjects": ("fvg",), "expect": "NULL",
        "line": "Gaps did not pull price back any more than random "
                "gaps of the same width.",
    },
    "evmacd": {
        "subjects": ("evmacd",), "expect": "NEGATIVE",
        "line": "Trading its stop-and-reverse signals lost heavily against "
                "simply holding.",
    },
    "elliott": {
        "subjects": ("EW unusual wave B flag", "EW W-X-Y complex correction"),
        "expect": "NULL",
        "line": "Two of its labels were tested: the '⚠ Unusual B' warning and the "
                "W-X-Y shape. Neither said anything about the next 20 days. The "
                "1-5 count itself has not been tested.",
    },
    "volprofile": {
        "subjects": ("volume-profile value-area traverse",), "expect": "NEGATIVE",
        "line": "The '80% value-area rule' failed: crossing the value area after "
                "re-entering it was no more likely than its base rate.",
    },
}

UNMEASURED_LINE = "Not measured on NSE yet."
#: What a reader sees as the label. NEGATIVE and NULL are the same thing to a
#: beginner — "this did not help" — so they share one.
LABEL = {"POSITIVE": "Measured edge", "NEGATIVE": "No edge found", "NULL": "No edge found",
         "MIXED": "Mixed", "INCONCLUSIVE": "Inconclusive", "UNRECORDED": "Not measured yet",
         None: "Not measured yet"}


def _studies_for(subjects) -> list[dict]:
    idx = ns.by_subject()
    seen, out = set(), []
    for s in subjects:
        for st in idx.get(s, []):
            if id(st) not in seen:
                seen.add(id(st)); out.append(st)
    return out


def combined(verdicts) -> str | None:
    """One verdict from several studies. Agreement is kept; a POSITIVE beside a
    NEGATIVE/NULL, or any MIXED, is MIXED; NEGATIVE beside NULL is NEGATIVE."""
    v = {x for x in verdicts if x != "UNRECORDED"}
    if not v:
        return None
    if len(v) == 1:
        return v.pop()
    if "MIXED" in v or "POSITIVE" in v:
        return "MIXED"
    if "NEGATIVE" in v:
        return "NEGATIVE"
    return "INCONCLUSIVE"


def evidence(keys) -> dict[str, dict]:
    """The payload the browser reads: key → {verdict, label, line, items}."""
    out = {}
    for k in keys:
        e = EVIDENCE.get(k)
        if not e:
            out[k] = {"verdict": None, "label": LABEL[None], "line": UNMEASURED_LINE, "items": []}
            continue
        st = _studies_for(e["subjects"])
        v = combined(s["verdict"] for s in st)
        out[k] = {"verdict": v, "label": LABEL.get(v, LABEL[None]), "line": e["line"],
                  "items": sorted({s["item"] for s in st})}
    return out


def positive_keys() -> set[str]:
    """Keys whose combined verdict is POSITIVE — the only ones the catalogue test
    lets use promise words (B-149)."""
    return {k for k, v in evidence(EVIDENCE).items() if v["verdict"] == "POSITIVE"}


def self_check() -> list[str]:
    """Problems claims_lint reports: a mapped subject the index no longer has, or a
    line whose verdict has moved since it was written."""
    idx = ns.by_subject()
    problems = []
    for k, e in EVIDENCE.items():
        missing = [s for s in e["subjects"] if s not in idx]
        if missing:
            problems.append(f"{k}: subject(s) not in named_studies: {', '.join(missing)}")
            continue
        got = combined(s["verdict"] for s in _studies_for(e["subjects"]))
        if got != e["expect"]:
            problems.append(f"{k}: line written for {e['expect']}, the index now says {got} — rewrite it")
    return problems


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    for k, v in evidence(EVIDENCE).items():
        print(f"{k:16s} {v['label']:14s} {', '.join(v['items'])}")
    probs = self_check()
    print("\nself-check:", "clean" if not probs else "")
    for p in probs:
        print("  -", p)
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
