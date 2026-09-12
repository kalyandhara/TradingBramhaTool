"""named_studies.py — the machine-readable index of measurements OUTSIDE B-19.

    py -3 tools/named_studies.py          # print the index + its own coverage gaps

WHY THIS EXISTS. `claims_lint`'s CHECK 0 catches a scanner that describes itself as
unmeasured while `cache/b19_verdicts/` holds its result. That works because the B-19
batch leaves one file per scanner — ground truth, no judgement.

**Every other measurement on this desk leaves no such file.** B-41m measured
`Liquidity Sweep` at +0.51% @20d through the shared harness and wrote its result into
the backlog as prose; nothing on disk associates the scanner with the finding. So
when both liquidity-sweep descriptions still said "Unmeasured." five days later, the
lint could not see it and a human had to. This index closes that gap.

── What an entry is, and what it deliberately is NOT ─────────────────────────────
An entry maps **subjects → a study that measured them**. It is an INDEX, not a
results database:

  * `headline` is optional and short. The authoritative numbers live in the backlog
    entry named by `source`; restating them here would create a second place for a
    figure to go stale, which is the exact failure this file is meant to reduce.
  * `verdict` is a coarse label, not a p-value. It answers "was this measured, and
    roughly how did it land", which is all a lint needs to know.

── The part that keeps the index itself honest ───────────────────────────────────
An index that silently falls behind is worse than none. `uncovered_tools()` lists
every `*_study.py` / `*_backtest.py` in `tools/` that no entry claims, and
`claims_lint` reports it. **A new study file is therefore a lint finding until it is
indexed** — the index cannot quietly rot, because the tree tells on it.

The seed set below is deliberately PARTIAL and says so. Entries were written only
where the mapping was verified against the backlog in the same session; everything
else surfaces as a coverage gap rather than being guessed at.
"""

from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent

#: Coarse outcome labels. Deliberately few: the lint only needs to know that a
#: measurement EXISTS and roughly which way it went.
#:   POSITIVE      — an edge that survived its own pass bar
#:   NEGATIVE      — measured the wrong way for what it claims
#:   NULL          — no measurable effect, adequately powered
#:   INCONCLUSIVE  — underpowered or aborted; NOT a null
#:   MIXED         — the signal and the plan disagree, or arms disagree
VERDICTS = ("POSITIVE", "NEGATIVE", "NULL", "INCONCLUSIVE", "MIXED")

#: item     — the backlog anchor (B-xx), the authoritative write-up
#: tool     — the bespoke study file, or None when it ran through the shared harness
#: subjects — EXACT names as they appear in `scanner_templates.SCANNERS`, or a
#:            component label for things that are not registered scanners
#: verdict  — one of VERDICTS
#: headline — one short line; optional, and never the full result
STUDIES: tuple[dict, ...] = (
    {
        "item": "B-41m", "tool": None, "date": "2026-09-06",
        "subjects": ("Liquidity Sweep", "Liquidity Sweep Bear"),
        "verdict": "MIXED",
        "headline": ("bull arm +0.51% @20d (p=0.005) net of costs, the only edge here "
                     "that survives them; bear arm negative but never significant"),
        "source": "analyses/Open-Backlog#B-41m",
    },
    {
        "item": "B-41p", "tool": "sweep_plan_study.py", "date": "2026-09-06",
        "subjects": ("Liquidity Sweep",),
        "verdict": "NEGATIVE",
        "headline": "the SHIPPED plan returns -0.06R against +0.50R unstopped; the stop is the defect",
        "source": "analyses/Open-Backlog#B-41p",
    },
    {
        "item": "B-57", "tool": "renko_shallow_quality_study.py", "date": "2026-09-07",
        "subjects": ("Shallow Flip (Renko, bounded correction)",),
        "verdict": "NULL",
        "headline": "-0.25% @20d, p_rot 0.714 against a state-matched baseline",
        "source": "analyses/Open-Backlog#B-57",
    },
    {
        "item": "B-58", "tool": "quasimodo_study.py", "date": "2026-09-11",
        "subjects": ("detect_quasimodo",),          # geometry only, no scanner registered
        "verdict": "NEGATIVE",
        "headline": "5,048 events, -0.64% p_rot 0.120; relaxing the CHOCH barely moves it",
        "source": "analyses/Open-Backlog#B-58",
    },
    {
        "item": "B-22r", "tool": "pcr_sign_study.py", "date": "2026-09-11",
        "subjects": ("sentiment_index.pcr_factor",),
        "verdict": "NULL",
        "headline": "483 sessions, +0.135% p_boot 0.58; factor 5 no longer scores",
        "source": "analyses/PCR-Sign-Convention-Pre-Registration",
    },
    {
        "item": "B-44r", "tool": "gamma_magnitude_backtest.py", "date": "2026-09-05",
        "subjects": ("gamma_exposure",),
        "verdict": "NEGATIVE",
        "headline": "both conventions tested; GEX retired as a research instrument",
        "source": "analyses/Open-Backlog#B-44r",
    },
    {
        "item": "B-44", "tool": "gamma_regime_backtest.py", "date": "2026-08-29",
        "subjects": ("gamma_exposure",),
        "verdict": "NULL",
        "source": "analyses/Open-Backlog#B-44",
    },
    {
        "item": "B-66", "tool": "sentiment_factor_edge.py", "date": "2026-09-10",
        "subjects": ("sentiment_index",),
        "verdict": "NULL",
        "headline": "no factor discriminates, nor the composite",
        "source": "analyses/Open-Backlog#B-66",
    },
    {
        "item": "B-59r", "tool": "psar_stai_edge.py", "date": "2026-09-10",
        "subjects": ("psar", "stai"),
        "verdict": "NULL",
        "headline": "neither twin's unique cells carry information",
        "source": "analyses/Open-Backlog#B-59r",
    },
    {
        "item": "B-67", "tool": "movers_edge.py", "date": "2026-09-11",
        "subjects": ("trending_stocks.price_movers_realtime",),
        "verdict": "NULL",
        "headline": "1,215 sessions, clean null on both legs",
        "source": "analyses/Open-Backlog#B-67",
    },
    {
        "item": "B-34", "tool": "hidden_treasures_backtest.py", "date": "2026-09-05",
        "subjects": ("hidden_treasures",),
        "verdict": "MIXED",
        "headline": "hit-rate WEAK; the lane's edge was traced to a drifting window bug",
        "source": "analyses/Open-Backlog#B-34",
    },
)


def by_subject() -> dict[str, list[dict]]:
    """subject -> every study that measured it (a subject can be measured twice)."""
    out: dict[str, list[dict]] = {}
    for st in STUDIES:
        for s in st["subjects"]:
            out.setdefault(s, []).append(st)
    return out


def study_files(root: pathlib.Path | None = None) -> set[str]:
    """Bespoke study/backtest files on disk, excluding their own tests."""
    root = root or HERE
    names = set()
    for pat in ("*_study.py", "*_backtest.py"):
        for p in root.glob(pat):
            if p.name.startswith("test_"):
                continue
            names.add(p.name)
    return names


def uncovered_tools(root: pathlib.Path | None = None) -> list[str]:
    """Study files that no entry claims — the index reporting its own staleness.

    This is the whole reason the index can be trusted to stay current: adding a
    study file without indexing it is a lint finding, so the gap is visible the
    day it appears rather than the day someone needs it.
    """
    claimed = {st["tool"] for st in STUDIES if st.get("tool")}
    return sorted(study_files(root) - claimed)


def _self_check() -> list[str]:
    """Problems with the index itself, not with the tree."""
    problems = []
    seen = set()
    for st in STUDIES:
        if st["verdict"] not in VERDICTS:
            problems.append(f"{st['item']}: unknown verdict {st['verdict']!r}")
        if not st["subjects"]:
            problems.append(f"{st['item']}: no subjects — the entry cannot be matched")
        if not st.get("source"):
            problems.append(f"{st['item']}: no source — the numbers must be traceable")
        tool = st.get("tool")
        if tool and not (HERE / tool).exists():
            problems.append(f"{st['item']}: tool {tool} does not exist")
        key = (st["item"], tool)
        if key in seen:
            problems.append(f"{st['item']}: duplicate entry")
        seen.add(key)
    return problems


def main() -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    print(f"named_studies — {len(STUDIES)} indexed measurements outside the B-19 batch")
    print()
    for st in sorted(STUDIES, key=lambda s: s["item"]):
        tool = st.get("tool") or "(shared harness)"
        print(f"  {st['item']:<8} {st['verdict']:<13} {tool}")
        print(f"           subjects: {', '.join(st['subjects'])}")
        if st.get("headline"):
            print(f"           {st['headline']}")
    print()

    problems = _self_check()
    print("  index self-check:", "clean" if not problems else f"{len(problems)} PROBLEM(S)")
    for p in problems:
        print(f"    - {p}")

    gaps = uncovered_tools()
    print()
    print(f"  COVERAGE GAPS — study files with no index entry: {len(gaps)}")
    for g in gaps:
        print(f"    - {g}")
    if gaps:
        print()
        print("  This list is expected to be non-empty and is not a failure. The seed")
        print("  set was written only where the mapping was verified; the rest are")
        print("  listed so they are indexed deliberately rather than guessed at.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
