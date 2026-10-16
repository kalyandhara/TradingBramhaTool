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
        "item": "B-114", "tool": "sbc_reading_backtest.py", "date": "2026-09-21",
        "subjects": ("structure break chain reading",),
        "verdict": "POSITIVE",
        "headline": ("150 names, 4,608 events (2,525 held / 2,083 failed): a break that "
                     "HELD beat one that FAILED by +1.28pp @20d, p<0.001 pooled -- and it "
                     "SURVIVES clustering (symbol as the unit: 133 names, mean +1.37pp, "
                     "median +1.04pp, 79/133 positive, p=0.0015). The graded quality score "
                     "does NOT rank on the same data (NORMAL -0.37% sits below WEAK "
                     "+0.52%), so the binary carries it. NOT tested against a do-nothing "
                     "baseline. BSE alone had said +16.05pp -- twelve times the powered "
                     "number, which is the floor's whole argument. B-115 then added the "
                     "missing arm: held breaks DO beat owning the same bars, +0.82pp @20d "
                     "(p=0.006; clustered 130 symbols, mean +0.67pp, 58% positive, "
                     "p=0.0297) -- real, and half the size of the two-bucket number. "
                     "Earlier BSE-only run: 41 events, 32 held vs 9 FAILED -- held breaks beat "
                     "failed ones by +7.1/+12.7/+16.1/+15.8pp at 5/10/20/60d "
                     "(p 0.064/0.009/0.039/0.064), and the failed bucket is 9 against "
                     "a pre-registered floor of 30, so nothing is claimed. The first "
                     "run was an ARTIFACT (41 held / 0 failed): `failed` resolves in "
                     "the bars AFTER a break, so at the break bar it is always False. "
                     "Neither secondary ladder ranks -- warn beats good, WEAK beats "
                     "STRONG"),
        "source": "analyses/SBC-Reading-BSE",
    },
    {
        "item": "B-48", "tool": "cvd_data_probe.py", "date": "2026-09-21",
        # Subject is the DATA, not a scanner: nothing in SCANNERS computes a
        # delta, and the point of the probe was to stop something from being
        # built that would have.
        "subjects": ("cumulative volume delta",),
        "verdict": "NEGATIVE",
        "headline": ("a true CVD is not computable without tick/bid-ask data, and the "
                     "OHLC proxy is bar-size dependent: 75.6% sign agreement and r=0.80 "
                     "between 5m and 15m session totals over 435 symbol-sessions, "
                     "against a pre-committed 90%/0.90. The two conventional proxies "
                     "disagree with EACH OTHER on 26% of the same bars"),
        "source": "analyses/CVD-Data-Probe",
    },
    {
        "item": "B-101", "tool": "bilateral_expansion_study.py",
        "date": "2026-09-20",
        "subjects": ("Symmetrical Triangle (bilateral)",),
        # Two runs. The first (28 coils) was INCONCLUSIVE by its own floor; the
        # second (270) is powered and settles it. The pair is kept because the
        # underpowered run is the argument for the floor.
        "verdict": "NULL",
        "headline": ("270 coils over 482 names, ~10y: a coil precedes an ORDINARY move "
                     "-- +0.32/-0.01/+0.23/-0.74pp |move| vs baseline at 5/10/20/60d, "
                     "p 0.27-0.98, sign not stable. The apex 50-75% band carries nothing "
                     "(in-band expands slightly LESS at every horizon, p 0.37-0.79). The "
                     "BILATERAL framing SURVIVES its falsifier: 42.7% up-share (105/141/"
                     "24 undecidable), inside the pre-committed 40-60%. The first run's "
                     "28-signal lean (+1.02 to +4.47pp) and its 29.2% up-share were both "
                     "noise, and the pre-registered floor is why neither was claimed"),
        "source": "analyses/Bilateral-Expansion-Pre-Registration",
    },
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
        "item": "B-94", "tool": "letter_levels_check.py", "date": "2026-09-19",
        "subjects": ("max_pain", "oi_walls", "read_levels"),
        "verdict": "MIXED",
        "headline": ("an outside letter's NIFTY max pain 23,300 reproduces "
                     "EXACTLY on the 2026-09-17 chain; its call wall 23,500 "
                     "reproduces only inside a +-10-strike window (ours ranks "
                     "the whole chain and returns 24,500); its put wall 23,100 "
                     "is our #8 put strike against 23,000's 80%-larger OI"),
        "source": "analyses/Open-Backlog#B-94",
    },
    {
        "item": "B-97", "tool": "pivot_timeframe_agreement.py",
        "date": "2026-09-19",
        "subjects": ("pivot_d", "pivot_w", "pivot_zone"),
        "verdict": "MIXED",
        "headline": ("daily and weekly pivot zones put a name on the same side "
                     "of the pivot 53.9% of 499 names (chance 41.8%, lift "
                     "+12.1) and on OPPOSITE sides 37.9%; median across 29 "
                     "month-ends 64.0% side / 27.3% opposite -- two readings, "
                     "not one in two resolutions"),
        "source": "analyses/Open-Backlog#B-97",
    },
    {
        "item": "B-42r", "tool": "pivot_len_agreement.py", "date": "2026-09-17",
        "subjects": ("read_market_structure",),
        "verdict": "MIXED",
        "headline": ("pivot_len 5 and 15 agree on state only 29.6% of 199 names; "
                     "17.6% read DOWNTREND vs UPTREND -- opposite, not coarser"),
        "source": "analyses/Open-Backlog#B-42r",
    },
    {
        "item": "B-9", "tool": "value_area_traverse_study.py", "date": "2026-09-17",
        "subjects": ("volume-profile value-area traverse",),
        "verdict": "NEGATIVE",
        "headline": ("the 80% rule traverses 45.5% of the time (95% CI 37.3-54.0, "
                     "n=134); lift over base -4.1pp p=0.422, not claimed"),
        "source": "analyses/Open-Backlog#B-9",
    },
    {
        "item": "B-8", "tool": "mean_reversion_stop_study.py", "date": "2026-09-17",
        "subjects": ("Mean Reversion (Connors RSI2)",),
        "verdict": "MIXED",
        "headline": ("the shipped session-low stop costs -0.64pp vs no stop "
                     "(p=0.0086, n=742, 300 names); 2-ATR costs nothing "
                     "measurable; LIQUID_50 alone had read -1.44pp"),
        "source": "analyses/Open-Backlog#B-8",
    },
    {
        "item": "B-92", "tool": "flag_pole_edge.py", "date": "2026-09-17",
        "subjects": ("Flag & Pole", "Inverted Flag & Pole"),
        "verdict": "MIXED",
        "headline": ("bull +0.71% @20d p=0.0499 (marginal pass), plan +0.36R on a "
                     "36.8% target rate; bear INVERTED +1.33% p=0.0005"),
        "source": "analyses/Flag-Pole-Pre-Registration",
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
    # ── Indexed 2026-10-14 (B-154 follow-up): nine study files the index had missed.
    {
        "item": "B-134", "tool": "ew_structure_study.py", "date": "2026-10-08",
        # The flag the elliott overlay prints as "⚠ Unusual B", scored through the
        # shipped elliott_wave.js at its default options.
        "subjects": ("EW unusual wave B flag",),
        "verdict": "NULL",
        "headline": ("unusual B vs normal B +0.17% @20d, p=0.281, n=13,077 vs 32,724 -- "
                     "neither a buy feature nor a valid warning; re-run after the B-137 "
                     "zigzag fix +0.09%, p=0.649. Stays a label"),
        "source": "analyses/Open-Backlog#B-134",
    },
    {
        "item": "B-135", "tool": "ew_structure_study.py", "date": "2026-10-08",
        "subjects": ("EW W-X-Y complex correction",),
        "verdict": "NULL",
        "headline": ("W-X-Y vs any correction ending in the same 61.8-78.6% band +0.36% "
                     "@20d, p=0.620, n=353 vs 28,210 -- the shape adds nothing over the "
                     "depth; re-run after B-137 -0.49%, p=0.557. Drawing aid only"),
        "source": "analyses/Open-Backlog#B-135",
    },
    {
        "item": "CHoCH", "tool": "choch_study.py", "date": "2026-10-07",
        # No backlog item of its own: the result lives in the scanner's description
        # and in one aside in the B-133-B-136 prior paragraph.
        "subjects": ("Bullish CHoCH (last 5 sessions)",),
        "verdict": "NULL",
        "headline": ("+0.24% @20d vs a bearish-structure baseline, p_rot 0.511, "
                     "n=15,851; +0.77% @60d, p_rot 0.263. PIPELINE_EXCLUDED, never votes"),
        "source": "analyses/Open-Backlog#B-134",
    },
    {
        "item": "B-122", "tool": "no_supply_gate_study.py", "date": "2026-09-23",
        "subjects": ("No-Supply (new high + clean volume)",),
        "verdict": "NULL",
        "headline": ("gate vs no gate on the Trend/Momentum family, paired by symbol, 24 "
                     "symbols / 8,580 signals / 1,728 gated: -0.118% @10d (p=0.79), "
                     "+0.157% @20d (p=0.25), +0.789% @60d (p=0.25) -- a subset, not a "
                     "better one"),
        "source": "analyses/Open-Backlog#B-122",
    },
    {
        "item": "B-90", "tool": "vwap_ema_agreement_study.py", "date": "2026-10-12",
        # The state was never built (B-90 says "do not build"); the vwap and ema20
        # overlays draw the two lines, not the agreement.
        "subjects": ("VWAP+EMA20 agreement state",),
        "verdict": "NEGATIVE",
        "headline": ("BELOW-both, hypothesised negative, was +0.12pp @1h / +0.16pp @2h "
                     "within-session, p<0.001 -- wrong sign. 5 names, 15m, 102 sessions; "
                     "the pooled day-level view does not show it"),
        "source": "analyses/Open-Backlog#B-90",
    },
    {
        "item": "B-98", "tool": "yearly_opening_range_study.py", "date": "2026-10-12",
        "subjects": ("January opening-range break",),
        "verdict": "NULL",
        "headline": ("442 names, 5,960 symbol-years: break excess -0.03 / -1.57 / -0.59pp "
                     "@20/60/120d, deciding by-year p=0.874 / 0.230 / 0.680; held vs "
                     "failed no separation. A level, not a scanner"),
        "source": "analyses/Open-Backlog#B-98",
    },
    {
        "item": "B-142", "tool": "valuation_edge_study.py", "date": "2026-10-12",
        "subjects": ("earnings-yield quintile at entry",),
        "verdict": "INCONCLUSIVE",
        "headline": ("thin run, 168 names: cheapest minus dearest +12.31pp @12m on ~5 "
                     "independent windows against a floor of 8; sign flips in 2024. "
                     "Reopens with B-141 depth"),
        "source": "analyses/Open-Backlog#B-142",
    },
    {
        "item": "CHoCH-f", "tool": "choch_filters_study.py", "date": "2026-10-07",
        "subjects": ("CHoCH inside an SMA200 uptrend", "CHoCH after a sell-side sweep"),
        "verdict": "UNRECORDED",
        "headline": ("only written as 'both FAIL' in an aside in the B-134 prior -- no "
                     "edge, p or n for either test anywhere"),
        "source": "analyses/Open-Backlog#B-134",
    },
    {
        "item": "PPV", "tool": "ppv_edge_study.py", "date": "2026-09-24",
        "subjects": ("pocket pivot volume bar",),
        "verdict": "UNRECORDED",
        "headline": ("no wiki write-up; only commit 80fa6e8's message (\"no forward-return "
                     "edge\", 24 symbols) and code comments -- no per-horizon numbers"),
        "source": "concepts/Pocket-Pivot",
    },
    {
        "item": "PPV-v", "tool": "ppv_variant_study.py", "date": "2026-09-24",
        "subjects": ("pocket pivot at RVOL 3x / 5x", "pocket pivot near a 20-day high"),
        "verdict": "UNRECORDED",
        "headline": ("no wiki write-up; commit 80fa6e8 calls all three variants clean "
                     "negatives (24 symbols, 9,879 signals) with no per-horizon numbers"),
        "source": "concepts/Pocket-Pivot",
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
    {
        "item": "B-147", "tool": "qullamaggie_edge_study.py", "date": "2026-10-14",
        "source": "analyses/Qullamaggie-Edge-Study",
        "subjects": ("Qullamaggie Breakout", "Episodic Pivot"),
        "verdict": "NULL",
        "headline": ("pre-registered, 459 names x 19y: Breakout +0.67pp @20d vs the "
                     "stock's ordinary bar, p=0.031 (bar 0.0125) -- NULL; +1.76pp @60d "
                     "p=0.005 not decisive. EP +0.47pp p=0.68 -- NULL. Right tail: 19% "
                     "reach +3R before the low-of-day stop, win/loss 2.66, +0.18R a "
                     "trade; the pre-registered R baseline was void (tiny R on ordinary "
                     "bars), post-hoc % plan +0.73% vs +0.12% (CI +0.29..+0.99). His "
                     "NIFTY SMA10>SMA20 filter did not help."),
    },
    {
        "item": "B-147b", "tool": "qullamaggie_breakout_retest.py", "date": "2026-10-14",
        "source": "analyses/Qullamaggie-Edge-Study",
        "subjects": ("Qullamaggie Breakout",),
        "verdict": "NULL",
        "headline": ("pre-registered confirmatory re-test of B-147's two Breakout leads on "
                     "424 names B-147 never saw (mostly small caps, 2021-26): 874 signals / "
                     "290 symbols. Decisive % plan vs the same plan on an ordinary bar with "
                     "a stop matched at 1.32x ATR14: +0.09pp a trade, p=0.85 (bar 0.025), "
                     "CI -0.56..+1.00 -- NULL. 60d forward +0.47pp p=0.68 -- the 60d lead "
                     "does not carry over. In-sample the matched-stop gap is +0.51pp "
                     "(p=0.028) but only +0.23pp vs a trend-matched bar."),
    },
    {
        "item": "B-132", "tool": "abcd_stop_study.py", "date": "2026-10-14",
        "source": "analyses/ABCD-Stop-Study",
        "subjects": ("AB=CD plan stop",),
        "verdict": "POSITIVE",
        "headline": ("pre-registered, nifty500[300:500] (fresh vs B-129r): AB=CD plan with "
                     "stop D - 2 x ATR14 +0.56%/trade vs +0.01% at the card's D - 0.5% "
                     "(paired by symbol +0.52pp, p=0.0019; own per-symbol p=0.012; 1,385 "
                     "trades / 183 symbols); 1 x ATR also passed (+0.37pp, p=0.010). "
                     "Stop-outs 67% -> 21%, but 43% now leave on the 10-bar time stop. "
                     "SHIPPED A2. Tier unchanged."),
    },
    {
        "item": "B-132r", "tool": "harmonic_tier_recheck.py", "date": "2026-10-14",
        "source": "analyses/ABCD-Stop-Study",
        "subjects": ("Harmonic Reversal (XABCD)",),
        "verdict": "POSITIVE",
        "headline": ("pre-registered re-run of B-129r's promotion check with B-132's AB=CD "
                     "stop (D - 2 x ATR14), nifty500 first 300 (out of sample for the stop). "
                     "R0 PASS (n=109, +1.10%). P: 2,349 signals / 281 symbols, @20d +0.55% "
                     "windows +0.33/+0.15/+1.06, clustered p=0.025, plan +0.04R (was -0.18R), "
                     "+0.55%/trade -> rule says PROMOTE (recommendation only). The window-2 pass "
                     "(-0.03 -> +0.15) came from calendar drift, not the stop; margins thin. "
                     "Tier unchanged -- owner's call."),
    },
    {
        "item": "B-95", "tool": "participant_oi_study.py", "date": "2026-10-15",
        "source": "analyses/FII-Short-Squeeze-Study",
        "subjects": ("FII index-futures extreme short",),
        "verdict": "NULL",
        "headline": ("pre-registered blind, 2016-2026, rotation p: FII >= 85% short in index "
                     "futures (261 sessions, 12 episodes) -> NIFTY +20 sessions -1.42pp vs "
                     "otherwise after a prior-move control, p=0.38 -- NULL, leaning AGAINST "
                     "the squeeze claim; entry days -3.55pp p=0.052 on 12 events. All "
                     "episodes 2020+."),
    },
    {
        "item": "B-174", "tool": "gmm_regime_study.py", "date": "2026-10-15",
        "source": "analyses/GMM-Regime-vs-Verdict",
        "subjects": ("Gaussian-mixture regime", "VOLATILE regime label"),
        "verdict": "NEGATIVE",
        "headline": ("pre-registered, NIFTY 2010-2026, Spearman with forward 20d vol: GMM "
                     "P(stressed) 0.226 vs VOLATILE 0.310 vs naive trailing vol 0.599 -- the "
                     "learned regime is significantly WORSE than the vol it is fed; closed, "
                     "regime stays rule-based."),
    },
    {
        "item": "B-172", "tool": "score_calibration_study.py", "date": "2026-10-15",
        "source": "analyses/Scanner-Score-Calibration",
        "subjects": ("scanner score", "best_score", "rank_score scanner term"),
        "verdict": "NULL",
        "headline": ("pre-registered census, 132k scored hits / 41 scanners: the 0-100 score "
                     "ranks hits within the scanner for 1-2 of 41 @20d (Renko Flip; ATH "
                     "Breakout fragile), INVERTED for Downside Risk; 38 no evidence. "
                     "B-172r (owner) on best_score's 30% of rank_score."),
    },
    {
        "item": "B-165r", "tool": "crt_edge_study.py", "date": "2026-10-15",
        "source": "analyses/Weekly-CRT-Sweep-Overlap",
        "subjects": ("weekly Candle Range Theory", "CRT"),
        "verdict": "NULL",
        "headline": ("pre-registered, 258 names x 750 bars, net costs, per-symbol t: weekly "
                     "bullish CRT -> 20d edge -0.16% (p 0.21) all events, -0.27% (p 0.09) "
                     "where no sweep fired; window signs flip. Detector only, no scanner."),
    },
    {
        "item": "B-175", "tool": "residual_momentum_study.py", "date": "2026-10-16",
        "source": "analyses/Residual-Momentum-vs-RS",
        "subjects": ("residual momentum", "RS rank"),
        "verdict": "NULL",
        "headline": ("pre-registered monthly IC, 58 dates x ~258 names: RS 0.036 (p 0.067), "
                     "residual momentum 0.044 (p 0.007), difference +0.008 (p 0.42) -- "
                     "not better than RS; no change."),
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
