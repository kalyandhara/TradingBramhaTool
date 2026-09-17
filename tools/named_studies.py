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
#:   UNRECORDED    — the study EXISTS and its subjects are known, but no result is
#:                   written anywhere this index can cite. Added 2026-09-11 while
#:                   indexing the last 14 files: four of them have no findable
#:                   write-up. That is the same disease as a stale claim seen from
#:                   the other side -- a measurement that left no trace -- and it is
#:                   better surfaced as a labelled state than hidden by a guess.
VERDICTS = ("POSITIVE", "NEGATIVE", "NULL", "INCONCLUSIVE", "MIXED", "UNRECORDED")

#: item     — the backlog anchor (B-xx), the authoritative write-up
#: tool     — the bespoke study file, or None when it ran through the shared harness
#: subjects — EXACT names as they appear in `scanner_templates.SCANNERS`, or a
#:            component label for things that are not registered scanners
#: verdict  — one of VERDICTS
#: headline — one short line; optional, and never the full result
STUDIES: tuple[dict, ...] = (
    {
        "item": "B-76", "tool": "order_block_rules_backtest.py",
        "date": "2026-09-13",
        # Subjects are the three OVERLAY rules, deliberately NOT "Order Block
        # Retest". That scanner was measured separately by the harness (-0.74%
        # @20d) and naming it here would let CHECK 0 read this study as a verdict
        # on the scanner, which it is not -- same B-73p0 reasoning.
        "subjects": ("order block target ladder", "order block stacked-zone bias",
                     "order block rejection entry"),
        "verdict": "NEGATIVE",
        "headline": ("target ladder is a NULL (paired -0.019R gross / -0.030R net vs "
                     "flat 2R, p=0.76 / 0.64) so it collapsed to 2R -- and the surviving "
                     "2R plan is -0.095R NET of costs; the stacked-zone bias gauge is "
                     "INVERTED (bullish lean +0.70% vs bearish +2.19% raw @20d, t=-9.05 "
                     "gross / -12.79 net; clustered by symbol -0.373pp on 38/50 and "
                     "-2.361pp on 40/44) and was RETIRED; early vs confirmed retest "
                     "undecidable (p=0.26 both cost bases, n~175/arm) so no difference "
                     "is claimed"),
        "source": "analyses/Order-Block-Rules-Measured",
    },
    {
        "item": "B-76c", "tool": "ob_bias_clustered.py", "date": "2026-09-13",
        "subjects": ("order block stacked-zone bias",),
        "verdict": "NEGATIVE",
        "headline": ("the clustering control B-76's pooled test could not supply: with "
                     "the SYMBOL as the unit (50 clusters) the inversion holds -- bullish "
                     "lean -0.373pp negative on 38/50 names, bearish -2.361pp on 40/44"),
        "source": "analyses/Order-Block-Rules-Measured",
    },
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
        "item": "B-73p0", "tool": "multibagger_conviction_study.py",
        "date": "2026-09-13",
        # The subject is the CORE, deliberately NOT "multibagger_candidates".
        # Naming the screen here would make CHECK 0 read it as measured, and the
        # study drops four of its seven legs -- the B-65r borrowing error, made
        # by a lint instead of by prose. The screen stays unmeasured on purpose.
        "subjects": ("institutional conviction core (FII+DII into small caps)",),
        "verdict": "NEGATIVE",
        "headline": ("pooled edge -2.07% @63d / -4.85% @126d vs an equal-length hold "
                     "of the same name (n=1,112, CIs exclude 0) -- but the sign FLIPS "
                     "by era (-3.27 / +5.24 / -8.19 @63d), so the honest claim is NO "
                     "STABLE EDGE; raw returns (+7.0 / +13.4 / +37.7%) are the market's"),
        "source": "analyses/Open-Backlog#B-73",
    },
    {
        "item": "B-74", "tool": "pmax_plan_study.py", "date": "2026-09-12",
        # PMax is a chart indicator, not a registered scanner, so the subject is
        # the component label -- same convention B-58 uses for detect_quasimodo.
        "subjects": ("pmaxSeries",),
        "verdict": "NEGATIVE",
        "headline": ("the SHIPPED plan returns -0.50R against an equal-length hold of the "
                     "same stock; a plain 20d hold gives back only -0.15R, and the drawn "
                     "trail used as a stop is worse again. B-74r: survives era-splitting "
                     "3/3 (-0.25 / -0.33 / -0.92R), worst in the LOWEST-drift window"),
        "source": "analyses/Open-Backlog#B-74",
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
    {
        "item": "B-43", "tool": "renko_backtest.py", "date": "2026-08-29",
        "subjects": ("Renko Flip (structure change)",),
        "verdict": "NULL",
        "headline": "flip edge ~0, negative on the long leg, beat buy&hold 0/23",
        "source": "analyses/Open-Backlog#B-43",
    },
    {
        "item": "B-43r", "tool": "renko_regime_study.py", "date": "2026-09-06",
        "subjects": ("Renko Flip (structure change)",),
        "verdict": "NEGATIVE",
        "headline": "cutting sideways chop made it SIGNIFICANTLY WORSE, not better",
        "source": "analyses/Open-Backlog#B-43r",
    },
    {
        "item": "B-32", "tool": "regime_backtest.py", "date": "2026-08-26",
        "subjects": ("opportunity_hub regime gate",),
        "verdict": "POSITIVE",
        "headline": "the RISK-OFF throttle's premise held, so B-33 has something to gate on",
        "source": "analyses/Open-Backlog#B-32",
    },
    {
        "item": "B-55", "tool": "svp_backtest.py", "date": "2026-08-29",
        "subjects": ("SVP.buildSignal",),
        "verdict": "NEGATIVE",
        "headline": "5 of 7 factors sign-inverted, corr -0.041, beat buy&hold 0/8",
        "source": "analyses/SVP-Signal-Backtest-Design",
    },
    {
        "item": "B-56", "tool": "svp_structure_backtest.py", "date": "2026-09-17",
        "subjects": ("SVPSTRUCT.read",),
        "verdict": "NEGATIVE",
        "headline": ("INVERTED: SELL +2.75% vs BUY +0.99% @20d, spread -1.77% "
                     "p_rot 0.041, 8 of 8 symbols; mirror deliberately not shipped"),
        "source": "analyses/SVP-Structure-Signal-Pre-Registration",
    },
    {
        "item": "ADX", "tool": "adx_di_backtest.py", "date": "2026-08-30",
        "subjects": ("adxdi",),
        "verdict": "MIXED",
        "headline": ("the bare DI cross LOSES (-0.93% @10d, p=0.02); the confirmed "
                     "up-state is positive (+1.82% @60d, p<0.005)"),
        "source": "concepts/ADX",
    },
    {
        "item": "FVG-fill", "tool": "fvg_fill_study.py", "date": "2026-07-22",
        "subjects": ("fvg",),
        "verdict": "NULL",
        "headline": ("gaps are not magnets: +2.1pp over a width-matched placebo on "
                     "Any Touch, no speed effect, no width effect"),
        "source": "concepts/Fair-Value-Gap",
    },
    {
        "item": "evmacd", "tool": "evwma_vwap_macd_backtest.py", "date": "2026-08-20",
        "subjects": ("evmacd",),
        "verdict": "NEGATIVE",
        "headline": "no edge; stop-and-reverse -29% against buy&hold +827%",
        "source": "analyses/Open-Backlog",
    },
    {
        "item": "FA-2", "tool": "fa2_rahu_kaal_study.py", "date": "2026-08-24",
        "subjects": ("rahu_kaal",),
        "verdict": "NULL",
        "headline": "+0.29bp return (p=0.76); the one p<0.05 range cell is a 15-min stub artifact",
        "source": "analyses/FA-2-Rahu-Kaal-Measured",
    },
    {
        "item": "FA-2b", "tool": "hora_study.py", "date": "2026-08-24",
        "subjects": ("hora",),
        "verdict": "NULL",
        "headline": ("weekday explains more than hora in every configuration, and the "
                     "per-lord ordering contradicts the tradition"),
        "source": "analyses/FA-2-Rahu-Kaal-Measured",
    },
    {
        "item": "SBC-vedha", "tool": "sbc_vedha_backtest.py", "date": "2026-08-17",
        "subjects": ("sbc_vedha",),
        "verdict": "NEGATIVE",
        "headline": "daily-vedha NIFTY event study: clean negative under 5,000x rotation",
        "source": "analyses/Contra-Strategy-Roadmap",
    },
    # ── The four with no findable write-up ────────────────────────────────────
    # Each RAN or was BUILT to run, and none has a result this index can cite. They
    # are indexed anyway: the mapping (tool -> subjects) is what CHECK 0 needs, and
    # UNRECORDED states the gap instead of hiding it behind a guessed verdict.
    {
        "item": "B-38", "tool": "funnel_backtest.py", "date": None,
        "subjects": ("TechnoFunda delete funnel",),
        "verdict": "UNRECORDED",
        "headline": "result not written up -- strategies/TechnoFunda-Delete-Funnel has no measured section",
        "source": "strategies/TechnoFunda-Delete-Funnel",
    },
    {
        "item": "SBC-15m", "tool": "sbc_backtest.py", "date": None,
        "subjects": ("sbc_reversal_windows",),
        "verdict": "UNRECORDED",
        "headline": "15-minute SBC reversal-window cross-check; no result located",
        "source": "analyses/Astro-Engine-Cross-Check",
    },
    {
        "item": "SBC-muhurat", "tool": "sbc_muhurat_backtest.py", "date": None,
        "subjects": ("abhijit_muhurat",),
        "verdict": "UNRECORDED",
        "headline": "Abhijit Muhurat reversal test; no result located",
        "source": "analyses/Astro-Engine-Cross-Check",
    },
    {
        "item": "B-30r", "tool": "newmoon_levels_backtest.py", "date": None,
        "subjects": ("newmoon_levels",),
        "verdict": "UNRECORDED",
        "headline": "new-moon highs/lows as S/R vs an adjacent day; no result located",
        "source": "analyses/Open-Backlog#B-30",
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


def unrecorded() -> list[dict]:
    """Studies whose result is not written anywhere this index can cite.

    Reported by `claims_lint` alongside the coverage gaps, for the same reason: a
    measurement with no write-up is debt, and debt that is not displayed does not
    get paid. An UNRECORDED entry should either gain a `source` with real numbers
    or be retired -- what it must not do is sit here looking indexed.
    """
    return [st for st in STUDIES if st["verdict"] == "UNRECORDED"]


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

    unr = unrecorded()
    print()
    print(f"  UNRECORDED — indexed, but no citable result: {len(unr)}")
    for st in unr:
        print(f"    - {st['item']:<12} {st['tool']}")
    if unr:
        print("      A measurement with no write-up is debt. Each should gain a source")
        print("      with real numbers, or be retired -- not sit here looking indexed.")

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
