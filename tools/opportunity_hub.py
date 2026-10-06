#!/usr/bin/env python3
"""
opportunity_hub.py — top-down Sector → Industry → Stock funnel (Phase 1).

The "Opportunity Hub" answers "Right Sector → Right Industry → Right Stock →
Right Pattern → Right Entry" as one connected flow, instead of a bottom-up
pattern scan over a flat universe. Phase 1 is pure composition — no new detectors:

  1. Score each stock's momentum (IBD-style weighted trailing return, reused from
     scanner_templates) and tag its sector / industry (yfinance .info, login-free,
     sharing the quality-gate's cached fetch).
  2. Rank SECTORS and INDUSTRIES bottom-up by their constituents' aggregate
     strength — leadership is derived from the very names we'll trade, in one
     consistent taxonomy (no index→constituents reconciliation needed).
  3. The dashboard then drills into the leading sectors/industries and runs the
     EXISTING Scanner Hub scanners on just those stocks (pattern + entry).

See wiki/analyses/Opportunity-Hub-Roadmap.md.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

_log = logging.getLogger(__name__)

import scanner_templates as sc


def _close(df) -> pd.Series | None:
    """Closing-price series with NaN bars dropped. yfinance occasionally returns a
    trailing NaN bar (holiday / incomplete session); _weighted_trailing_return
    anchors on the LAST close, so a NaN there yields a NaN momentum that then
    poisons the group ranking — drop them up front, same discipline as scan_pead."""
    if df is None or getattr(df, "empty", True):
        return None
    col = "close" if "close" in df.columns else ("Close" if "Close" in df.columns else None)
    if not col:
        return None
    c = df[col].dropna()
    return c if len(c) else None


def stock_strength(df) -> float | None:
    """Per-stock momentum = IBD-style weighted trailing return (reuses the scanner
    engine's own RS primitive so the funnel and the scanners agree on 'strength')."""
    c = _close(df)
    if c is None or len(c) < 30:
        return None
    try:
        v = sc._weighted_trailing_return(c)
    except Exception:
        return None
    if v is None or pd.isna(v):
        return None
    return round(float(v), 2)


def _one_constituent(sym: str, fetch_ohlcv) -> dict | None:
    """Tag + strength for a single symbol (the unit of work parallelised below)."""
    try:
        f = sc.fetch_fundamentals_yf(sym) or {}
    except Exception:
        f = {}
    sector = f.get("sector")
    try:
        df = fetch_ohlcv(sym)
    except Exception:
        df = None
    mom = stock_strength(df)
    if sector is None or mom is None:
        return None                        # need a sector AND a strength to place it
    c = _close(df)
    return {
        "symbol": sym,
        "sector": sector,
        "industry": f.get("industry") or "—",
        "momentum": mom,
        "last": round(float(c.iloc[-1]), 2) if c is not None else None,
        "roe_pct": f.get("roe_pct"),
        "opm_pct": f.get("opm_pct"),
        "pe": f.get("pe"),
        "market_cap_cr": f.get("market_cap_cr"),
    }


def build_constituent_table(symbols: list[str], fetch_ohlcv,
                            *, progress_cb=None, max_workers: int = 8) -> pd.DataFrame:
    """One row per stock that has BOTH a sector tag and a computable momentum:
    symbol · sector · industry · momentum · last · (roe/opm/pe/mcap for display).

    The per-symbol yfinance `.info` (sector tag) + OHLCV fetches are network-bound,
    so they run across a THREAD POOL (`max_workers`) — the funnel's build over a
    few-hundred-name universe drops from minutes (sequential) to tens of seconds.
    Both fetches are cached (scanner_templates' `.info` cache + the caller's OHLCV
    cache), so a re-run and the subsequent scanner pass reuse the work."""
    rows: list[dict] = []
    total = len(symbols)
    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_one_constituent, s, fetch_ohlcv) for s in symbols]
        for fut in as_completed(futures):
            done += 1
            if progress_cb is not None:
                try:
                    progress_cb(done, total)
                except Exception:
                    pass
            try:
                r = fut.result()
            except Exception:
                r = None
            if r:
                rows.append(r)
    return pd.DataFrame(rows)


def rank_groups(stock_df: pd.DataFrame, group_col: str,
                *, min_constituents: int = 3) -> pd.DataFrame:
    """Rank sectors or industries by aggregate constituent strength.

    strength = mean constituent momentum; also reports median, breadth (% of
    constituents with positive momentum), constituent count, and the strongest
    name. Groups with fewer than `min_constituents` members are dropped — a
    one-stock 'sector' is not a leadership signal.
    """
    if stock_df is None or stock_df.empty or group_col not in stock_df.columns:
        return pd.DataFrame()
    out = []
    for name, g in stock_df.groupby(group_col):
        g = g[g["momentum"].notna()]
        if len(g) < min_constituents:
            continue
        breadth = float((g["momentum"] > 0).mean() * 100.0)
        leader = g.loc[g["momentum"].idxmax()]
        out.append({
            group_col: name,
            "avg_momentum": round(float(g["momentum"].mean()), 2),
            "median_momentum": round(float(g["momentum"].median()), 2),
            "breadth_pct": round(breadth, 0),
            "count": int(len(g)),
            "leader": f'{leader["symbol"]} ({leader["momentum"]:+.0f}%)',
        })
    df = pd.DataFrame(out)
    if df.empty:
        return df
    return df.sort_values("avg_momentum", ascending=False).reset_index(drop=True)


def stocks_in_groups(stock_df: pd.DataFrame, group_col: str,
                     names: list[str]) -> list[str]:
    """Constituent symbols belonging to the chosen sectors/industries, strongest
    first — this is the narrowed list the pattern scanner then runs on."""
    if stock_df is None or stock_df.empty or not names:
        return []
    sel = stock_df[stock_df[group_col].isin(names)].sort_values(
        "momentum", ascending=False)
    return sel["symbol"].tolist()


# ──────────────────────────────────────────────────────────────────────────────
# Step 4 as a PIPELINE — every scanner over the leaders, in one pass
# ------------------------------------------------------------------------------
# Running one scanner at a time answers "does THIS pattern fire", which is the
# wrong question once the funnel has already narrowed the field. The useful
# question is "how many independent reads land on the same name". Both hubs run
# the pipeline below so the interactive funnel and the headless daily job can
# never disagree about what confluence means.
#
# The counting is where this gets subtle, so it is spelled out:
#
#   A stock in a clean uptrend near its highs mechanically fires 52-Week High
#   Leaders AND Momentum Continuation AND Stage 2 Uptrend AND Near Pivot AND
#   ATH Breakout. That is ONE fact reported five times, not five confirmations.
#   A raw scanner count therefore ranks pure-momentum names to the top — exactly
#   the cohort the backtest harness measured at or below a random-entry
#   baseline. So scanners are grouped into FAMILIES and each family contributes
#   only its single best member's weight.
#
# The raw count is still reported (it is what the user asked to see); the
# FAMILY count is what the ranking actually spends.
# ──────────────────────────────────────────────────────────────────────────────

#: Scanner name → family. Members of one family read the same underlying fact
#: about a chart, so they cannot vote independently.
SCANNER_FAMILIES: dict[str, tuple[str, ...]] = {
    "Trend/Momentum": (
        "52-Week High Leaders",
        "Momentum Continuation",
        "Stage 2 Uptrend",
        "ATH Breakout (all-time high)",
        "ADX Trend Confirmation",
        "No-Supply (new high + clean volume)",
    ),
    "Base/Contraction": (
        "VCP Coiling",
        "Minervini VCP (valchak)",
        "Base Formation",
        "High Tight Flag",
        "Darvas Box",
    ),
    "Breakout/Structure": (
        "Consolidation Breakout (6M–10Y)",
        "Structural Breakout",
        "IPO-Base Breakout",
    ),
    "Reversal": (
        "Double Bottom",
        "Falling Wedge",
        "Harmonic Reversal (XABCD)",
        "Rounding Bottom",
        "Early Reversal Detector",
        "%R Bottoming",
    ),
    "Entry Trigger": (
        "Pullback Entry",
        "Near Pivot",
        "Order Block Retest",
        "Breakout Retest",
        "RSI 60-40 Setup",
        "RSI Divergence Bull",
        "Candlestick Patterns",
        "FVG Pullback",
        "ICT Setup",
    ),
    "Event": (
        "PEAD Drift",
    ),
}

#: Display/count order for families.
FAMILY_ORDER: tuple[str, ...] = tuple(SCANNER_FAMILIES.keys())

#: Bearish scanners. These RUN — a distribution warning on a shortlisted name is
#: worth seeing — but a hit is evidence AGAINST the name, so it can never add to
#: a confluence count. It is surfaced as a risk flag instead.
#:
#: "Support Breakdown" stays in this tuple although it is now also in
#: PIPELINE_EXCLUDED, and the overlap is deliberate rather than dead config: the
#: exclusion stops the PIPELINE running it (so no flag is displayed), while this
#: tuple is what `scanner_tier()` reads to colour it as a RISK entry where it is
#: still listed and runnable in the Scanner Hub. Dropping it here would re-label a
#: retired bearish scanner as "unmeasured", which is the opposite of what happened
#: to it.
#: "Liquidity Sweep Bear" joined 2026-09-21 (B-105), and its absence is the
#: reason `test_risk_scanner_invariants.py` now exists. It shipped registered as
#: `category: "Risk"` and was never added here, so `scanner_tier()` read it as
#: `unmeasured`, `scanner_family()` found no family, and `tally_evidence`'s
#: fall-through — the branch that deliberately gives an unmapped NON-risk scanner
#: its own family of one — counted a BEARISH detector as a 0.5 vote FOR the name.
#: Verified live before the fix: `families=['Liquidity Sweep Bear'] points=0.5
#: riskflags=[]`. The category field had said which side it was on the whole time;
#: nothing was ambiguous, the two lists had simply drifted apart.
RISK_SCANNERS: tuple[str, ...] = ("Downside Risk", "Bearish Reversal Candle", "Support Breakdown", "RSI Divergence Bear", "%R Exhaustion Sell", "Liquidity Sweep Bear")

#: BILATERAL scanners — the neutral state (B-101). These RUN and are worth
#: seeing: a coil that is about to resolve is exactly the thing to have on a
#: watchlist. But a hit is evidence for NEITHER side, so like a risk flag it
#: carries zero weight and joins no family.
#:
#: This is a THIRD state, not a re-labelled risk flag, and the difference is not
#: cosmetic. A risk hit is evidence AGAINST the name — it argues for skipping it.
#: A bilateral hit argues for nothing; it says the direction is not yet knowable.
#: Folding it into RISK_SCANNERS would have been the cheap way to stop it voting
#: and would have printed "risk flag: Symmetrical Triangle" on a pattern that is
#: not bearish, which is the same species of lie as VCP's upward-only plan on a
#: coil (the very thing B-101 was raised about).
#:
#: `tally_evidence` must skip these explicitly. Its fall-through gives an
#: UNMAPPED non-risk scanner its own family of one — the honest default for a
#: new directional scanner, and exactly wrong here.
NEUTRAL_SCANNERS: tuple[str, ...] = ("Symmetrical Triangle (bilateral)",)

#: Registry entries the pipeline must not run.
#: "Zero-Debt Quality PEAD" declares ``fn = scan_pead`` — the IDENTICAL function
#: as "PEAD Drift". It only differs when routed through ``run_quality_pead()``
#: with its fundamentals gate, which a generic pipeline never calls. Left in, it
#: would silently turn every PEAD hit into two votes for the same detector.
#:
#: "Renko Flip (structure change)" is a SCREEN, not a trigger, and the exclusion is how
#: that is enforced rather than merely worded. B-43 measured this exact engine's flips at
#: no forward edge (up-flip edge negative at every horizon; stop-and-reverse beat
#: buy-and-hold 0/23), so letting it into the confluence pipeline would spend ranking
#: weight on a detector known to carry none — and it fires in BOTH directions, so a hit is
#: not even evidence of a side. It stays visible in the Scanner Hub as a "what changed?"
#: filter and contributes nothing to the score.
#:
#: "VWAP Reclaim/Support" joins them 2026-09-06 on the same principle as Renko, one
#: step further along. B-43 excluded Renko for measuring NO edge; B-40 measured this
#: one as significantly NEGATIVE: −0.20% @10d (p=0.042), −0.45% @20d (p=0.0006),
#: −0.50% @60d (p=0.033) over 2745 signals, hit rate under 50% and median negative at
#: 5/10/20d once Indian delivery costs are paid. A reclaim selects bars that do WORSE
#: than a random bar from the same pool, so letting it vote in confluence does not
#: merely waste ranking weight — it spends it against the ranking.
#:
#: Demoting it to MEASURED_WEAK (0.25) was the first response and was not enough: a
#: weak weight still counts toward FULL_CONFLUENCE, so a negative detector could still
#: help push a name onto the shortlist. Exclusion is the only setting that makes it
#: contribute zero.
#:
#: It stays REGISTERED, visible and runnable in the Scanner Hub, and backtestable —
#: same as Renko. The measurement rules out a vote, not the view. Its complementary
#: anchored-VWAP-from-catalyst half (B-4/B-12) is a different mean and is untouched.
PIPELINE_EXCLUDED: tuple[str, ...] = ("Zero-Debt Quality PEAD",
                                      "Renko Flip (structure change)",
                                      # B-57 measured this at -0.25% @20d, p_rot=0.714,
                                      # against a state-matched baseline -- it failed its
                                      # pre-registered bar, so it screens but never votes.
                                      "Shallow Flip (Renko, bounded correction)",
                                      # RETIRED 2026-09-11. A RISK flag measured
                                      # POSITIVE: B-19 scored it +0.47% @20d /
                                      # +1.22% @60d on 2,880 signals -- names it
                                      # warned about went UP. It never voted (risk
                                      # scanners cannot), but it was DISPLAYED as a
                                      # bearish warning on shortlisted names, which
                                      # is its own kind of harm: a flag that steers
                                      # a reader away from names that outperformed.
                                      #
                                      # Honest about the strength of that evidence:
                                      # the verdict is "NO BEARISH EDGE [UNSTABLE]",
                                      # i.e. not sign-stable across walk-forward
                                      # windows, so "points the wrong way" is the
                                      # reading, not a significant inversion like
                                      # B-44r's GEX. What IS established is that the
                                      # bearish claim has no support, and a warning
                                      # with no support should not be shown.
                                      #
                                      # It stays REGISTERED, runnable in the Scanner
                                      # Hub and backtestable -- the GEX precedent
                                      # (B-44r): retired as a decision input, kept as
                                      # a view. Restoring it needs a NEW measurement
                                      # that finds a bearish edge, not a re-reading.
                                      "Support Breakdown",
                                      "VWAP Reclaim/Support")

#: Measured to be FULLY COVERED by the rest of the registry — zero unique
#: (symbol, as-of) cells across 110 NIFTY-500 names × 2,496 cells, on full listing
#: history. See analyses/Scanner-Overlap-Audit for the method and the numbers.
#:
#: These are hidden from the Scanner Hub's DEFAULT list and nothing else. They stay
#: registered, stay runnable behind the hub's "show covered" toggle, stay backtestable,
#: and stay in the confluence pipeline — because "covered" is a statement about
#: COVERAGE, not about quality. A covered scanner can still be the more precise way to
#: express a setup; what the measurement rules out is that removing it from the default
#: view loses a hit no other scanner flags. That is exactly B-35's invariant and nothing
#: more, which is why this list drives visibility rather than deletion.
#:
#: Re-derive after any scanner change:  py -3 tools/scanner_overlap.py --days 0
COVERED_SCANNERS: tuple[str, ...] = (
    # Zero unique cells in BOTH independent samples (see the stability rule below).
    # Counts shown as: 1500-day sample / full-listing-history sample.
    "52-Week High Leaders",             # 401 / 285 — 95% contained in Momentum Continuation
    "RSI Mid-Band Momentum",            # 269 / 200 — 93% contained in Pullback Entry
    "Base Formation",                   #  89 /  95 — 99% contained in Stage 2 Uptrend
    "RSI 60-40 Setup",                  #  91 /  84
    "Triple-RS 52W Cross",              #  70 /  63 — 99% contained in 52-Week High Leaders
    "ATH Breakout (all-time high)",     #  67 /  45
    "Consolidation Breakout (6M–10Y)",  #  17 /   8 — 100% contained in Pullback Entry
    "IPO-Base Breakout",                #  14 /   6
    "Minervini VCP (valchak)",          #   3 /   4 — containment is structural: its Trend
                                        #             Template gate tests what Stage 2 does
)

#: The stability rule, and why it is not just "whatever the last run said".
#:
#: The audit was run twice on independent samples — a 1500-day window and full listing
#: history. Three scanners DISAGREE between them, which is exactly the signature of a
#: sampling artefact rather than a property of the scanner:
#:
#:     High Tight Flag       1500d: 11 hits / 0 unique   full: 19 / 1
#:     Structural Breakout   1500d: 58 hits / 0 unique   full: 64 / 2
#:     Rounding Bottom       1500d: 89 hits / 1 unique   full: 75 / 0
#:
#: So the rule is: hide only what measures zero-unique in BOTH samples. All three above
#: stay VISIBLE. Hiding on a single run would have removed two scanners that do carry
#: unique hits (the first cut of this list did exactly that, and this is the correction).
#:
#: ATH Breakout and IPO-Base Breakout appear here only after the full-history re-run,
#: which is the first VALID measurement of them: on truncated frames ATH read a 261-bar
#: slice max as an "all-time" high and IPO-Base saw every stock as freshly listed. Their
#: counts fell 67→45 and 14→6 once fed real history, confirming both artefacts.
#:
#: Re-derive after any scanner change, and run it BOTH ways:
#:     py -3 tools/scanner_overlap.py                 # 1500-day sample
#:     py -3 tools/scanner_overlap.py --days 0        # full listing history


def core_scanners() -> list[str]:
    """Registry order, minus the measured-covered ones. The Hub's default list."""
    return [n for n in sc.SCANNERS if n not in COVERED_SCANNERS]


#: Measured to BEAT a random-entry baseline (wiki/analyses/Backtest-Harness).
#: RE-MEASURED 2026-09-23 (B-128 / B-129, LIQUID_50, 3 windows, 29bps):
#:   Falling Wedge -- CONFIRMED breakouts +1.37% @20d, +1.98% @60d, stable at
#:     10/20/60d; forming / pre-breakout cards -0.27%. The tier stands, and the
#:     old +0.74% was a dilution of it.
#:   Harmonic Reversal -- DEMOTED to the weak tier below (owner, B-129).
MEASURED_EDGE_SCANNERS: tuple[str, ...] = (
    "Falling Wedge",
)

#: Measured and found AT OR BELOW that baseline. Kept for coverage and context,
#: but they must not carry the same weight as the two that were measured to
#: work. Order Block sits here on its raw forward edge (−0.74%) despite a mildly
#: positive +0.11R from its 2R targets.
#:
#: Both VWAP entries joined 2026-09-06 (B-40, B-40m) — they were sitting at
#: WEIGHT_UNMEASURED, which after measurement overstated them:
#:   • VWAP Mean Reversion — null (+0.19% @5d and @10d, p 0.51/0.57) and
#:     −0.19R once Indian delivery costs are paid. Weak, but not negative: it
#:     still earns a quarter-weight vote.
#:
#: VWAP Reclaim/Support was demoted here first and then moved OUT to
#: PIPELINE_EXCLUDED — it measured significantly negative, and a weak weight still
#: counts toward FULL_CONFLUENCE, so 0.25 was not low enough. This list is for
#: scanners that still vote; a scanner that must not vote belongs in the exclusion.
#: `VCP Coiling` left this list and came back on 2026-09-19, and the round trip
#: is worth reading rather than just the destination.
#:
#: It left because its weak tier came from B-19 (2026-09-02), which measured the
#: coarse three-window range test that `scan_vcp` used to be. That detector was
#: replaced by `detect_vcp_geometry`'s strict pivot walk, and B-19's number does
#: not describe a different hit set (the two agreed on 16 of 29 hits on a
#: 110-name check). Keeping it would have been the cheaper option and the wrong
#: one, so the scanner went back to `unmeasured` — which RAISED its weight from
#: 0.25 to 0.50, because "plausible, unproven" outranks "measured and it was not
#: good". It held that unearned 0.50 for exactly as long as it took to re-run.
#:
#: It came back because B-19r(VCP) re-measured the NEW detector through the same
#: harness (LIQUID_50, 3 windows, Indian delivery) against bands pre-registered
#: before the run: 3,233 OOS signals, +0.13% @20d, -0.22% @60d. It fails the bar
#: the way B-19's headline warned about — @20d is positive but NOT sign-stable
#: (windows +0.62*/+0.09/-0.28, only the first significant), and @60d is stable
#: and NEGATIVE. Positive on one horizon, not reproducible across windows.
#:
#: So the swap bought a harness-scoreable plan, one detector instead of two that
#: disagreed, and 2.7x more hits — and no edge. VCP Coiling is a context lens
#: under either detector. Verdict file: cache/b19_verdicts/VCP_Coiling.txt; the
#: retired detector's is beside it in _superseded/.
#: "Double Bottom" joined 2026-09-21, measured as a BY-PRODUCT of B-116 plumbing
#: the plan scoreboard through the walk-forward path: 1,519 OOS signals over
#: LIQUID_50, -0.17 / -0.26 / -0.61 / -1.58% at 5/10/20/60d, sign consistent in
#: all three windows at every horizon, p<0.05 in four window-horizons. It is
#: measured at-or-below a random-entry baseline, which is what this tier means,
#: so the weight drops 0.50 -> 0.25.
#:
#: NOT excluded, though the VWAP Reclaim precedent (measured significantly
#: negative -> PIPELINE_EXCLUDED) is the obvious next step and is the owner's
#: call: the same run that produced this number also showed the shared harness
#: has no notion of a FRESH signal (B-120), and a detector whose state persists
#: for several bars has its events counted several times. That doubt cuts
#: against trusting the magnitude, not against demoting on the sign — 1,519
#: signals negative at every horizon in every window is not a rounding error.
#: Re-measure under B-120's freshness rule before deciding exclusion.
MEASURED_WEAK_SCANNERS: tuple[str, ...] = (
    "Double Bottom",
    # B-129, owner decision 2026-09-23: its measured-edge tier rested on a pooled
    # +0.88% @20d that mixed a failing SHORT thesis (bearish patterns +0.72% when
    # scored long) with an unstable long one (bullish-only +1.07%, positive in 2
    # of 3 windows at every horizon). Now bullish-only in the scanner, and 0.25
    # here until a bullish-only re-measure earns more.
    # Re-measured 2026-10-05 (tools/harmonic_bull_remeasure.py, pre-registered;
    # 300 names, fresh, next-open fill): STAYS WEAK. @20d +0.55% but window 2
    # -0.03, and the plan is -0.18R. AB=CD carries the signal edge (clustered
    # p=0.0066) and its D-0.5% stop gives it back (68% stopped) -- B-132.
    "Harmonic Reversal (XABCD)",
    "Order Block Retest",
    "RSI 60-40 Setup",
    "Structural Breakout",
    "VCP Coiling",
    "VWAP Mean Reversion",
)

WEIGHT_MEASURED = 1.0      # measured to beat the baseline
WEIGHT_UNMEASURED = 0.5    # never measured — plausible, unproven
WEIGHT_WEAK = 0.25         # measured at or below the baseline

#: Family-capped edge points that count as full confluence. Two families where
#: one carries a measured-edge scanner, or three unmeasured ones.
FULL_CONFLUENCE = 2.0


def scanner_family(name: str) -> str | None:
    """Family a scanner belongs to, or None for risk/unmapped entries."""
    for fam, members in SCANNER_FAMILIES.items():
        if name in members:
            return fam
    return None


def scanner_tier(name: str) -> str:
    """``measured`` | ``weak`` | ``unmeasured`` | ``risk`` — what the backtest
    harness actually knows about this scanner. Drives both weight and colour."""
    if name in RISK_SCANNERS:
        return "risk"
    if name in NEUTRAL_SCANNERS:
        return "neutral"
    if name in MEASURED_EDGE_SCANNERS:
        return "measured"
    if name in MEASURED_WEAK_SCANNERS:
        return "weak"
    return "unmeasured"


def scanner_weight(name: str) -> float:
    """Edge points a hit from this scanner is worth before family capping."""
    return {"measured": WEIGHT_MEASURED, "weak": WEIGHT_WEAK,
            "unmeasured": WEIGHT_UNMEASURED, "risk": 0.0,
            "neutral": 0.0}[scanner_tier(name)]


def pipeline_scanners() -> list[str]:
    """Every registered scanner the pipeline runs, in registry order.

    Reads ``sc.SCANNERS`` rather than a hand-kept list so a newly-registered
    scanner joins the pipeline automatically — it lands in no family and is
    scored as unmeasured, which is the honest default for something brand new.
    """
    return [n for n in sc.SCANNERS if n not in PIPELINE_EXCLUDED]


def confluence_pct(edge_points: float) -> float:
    """Family-capped edge points → a 0-100 confluence component."""
    return min(float(edge_points) / FULL_CONFLUENCE, 1.0) * 100.0


def tally_evidence(fired: list[str]) -> tuple[list[str], float, list[str]]:
    """(families hit, family-capped edge points, risk flags) for one symbol.

    Public because the dashboard re-derives families for shortlist rows stored
    before the family columns existed — the mapping is deterministic, so an old
    row renders identically to a new one."""
    risk = [n for n in fired if n in RISK_SCANNERS]
    best_per_family: dict[str, float] = {}
    for n in fired:
        fam = scanner_family(n)
        if fam is None:
            continue                      # risk scanners and unmapped entries
        w = scanner_weight(n)
        if w > best_per_family.get(fam, 0.0):
            best_per_family[fam] = w
    families = [f for f in FAMILY_ORDER if f in best_per_family]
    # An unmapped, non-risk scanner still deserves a vote — count it as its own
    # family of one rather than dropping the evidence on the floor.
    for n in fired:
        if (scanner_family(n) is None and n not in RISK_SCANNERS
                and n not in NEUTRAL_SCANNERS):
            families.append(n)
            best_per_family[n] = scanner_weight(n)
    return families, round(sum(best_per_family.values()), 2), risk


def run_scanner_pipeline(symbols: list[str], fetch_for, *,
                         scanners: list[str] | None = None,
                         benchmark_df=None, progress_cb=None,
                         attach_pead: bool = True) -> dict[str, dict]:
    """Run every pipeline scanner over `symbols`; return one entry per name hit.

    `fetch_for(scanner_name) -> fetch_fn` is deliberately a FACTORY, not a single
    fetch function. Two scanners in the registry carry ``needs_full_history``
    (ATH and IPO-base breakout) and are meaningless on the default ~300-bar
    window: `scan_ath_breakout` only requires 250 bars, so handed a short frame
    it fires happily and reports a ~1-year high as an all-time high. Making the
    caller supply a per-scanner fetch means that rule is structural on every
    path instead of something each caller has to remember.

    **The factory must answer for a name it does not recognise**, returning the
    default-window fetch — which is what both shipped callers already do, since
    each discriminates on the single ``needs_full_history`` flag via
    ``SCANNERS.get(name, {})``. `DEFAULT_WINDOW` below is the documented way to
    ask for that frame without naming a scanner.

    Each returned value carries:
        scanners     — every scanner that fired, in run order
        families     — the distinct families those scanners belong to
        edge_points  — family-capped weight sum (what the ranking spends)
        raw_points   — uncapped weight sum (for transparency only)
        best_card    — the highest-scoring scanner card, for rendering
        best_scanner — which scanner produced it
        risk_flags   — bearish scanners that also fired (never a vote)
        pead         — the last-4-quarter post-earnings drift walk, PRESENT ONLY
                       when one could be measured. Context, never a vote: it is
                       computed after ranking and nothing scores on it.
    """
    names = list(scanners) if scanners else pipeline_scanners()
    names = [n for n in names if n in sc.SCANNERS]
    hits: dict[str, dict] = {}
    total = len(names)

    for i, name in enumerate(names, 1):
        if progress_cb is not None:
            try:
                progress_cb(i, total, name)
            except Exception:
                pass
        try:
            results = sc.run_scanner(name, symbols, fetch_for(name),
                                     benchmark_df=benchmark_df)
        except Exception as _exc:
            _log.warning("Scanner %r failed: %s", name, _exc, exc_info=True)
            continue                      # one broken scanner must not kill the run
        for card in results:
            sym = card.get("symbol")
            if not sym:
                continue
            h = hits.setdefault(sym, {"symbol": sym, "scanners": [],
                                      "best_score": 0.0, "best_card": None,
                                      "best_scanner": None})
            h["scanners"].append(name)
            # A bearish hit must never become the card we render as the setup.
            if name not in RISK_SCANNERS and (card.get("score") or 0) >= h["best_score"]:
                h["best_score"] = float(card.get("score") or 0)
                h["best_card"] = card
                h["best_scanner"] = name

    for h in hits.values():
        families, points, risk = tally_evidence(h["scanners"])
        h["families"] = families
        h["edge_points"] = points
        h["raw_points"] = round(sum(scanner_weight(n) for n in h["scanners"]), 2)
        h["risk_flags"] = risk
    # A name whose ONLY hit was bearish has no setup to show — drop it rather
    # than render a card with no pattern on it.
    hits = {s: h for s, h in hits.items() if h["best_card"] is not None}

    # ── The PEAD walk: a LAST stage, over the survivors only ──────────────────
    # Deliberately after the filter. It is CONTEXT on a shortlisted name, not a
    # filter and not a vote — nothing below reads `pead` when computing
    # edge_points, families or rank_score, and adding it here must not change
    # which names appear or in what order. Running it over the survivors also
    # keeps it to a few dozen cache lookups instead of the whole universe.
    if attach_pead:
        try:
            _fetch = fetch_for(DEFAULT_WINDOW)
        except Exception as _exc:
            # A factory that raises on an unknown name breaks the contract in the
            # docstring above. The walk is context, so it goes quiet rather than
            # taking the pipeline down with it.
            _log.warning("PEAD walk: fetch_for(%r) failed (%s)", DEFAULT_WINDOW, _exc)
        else:
            _attach_pead(hits, _fetch)
    return hits


#: Asked of `fetch_for` when a caller wants the DEFAULT-WINDOW frame rather than
#: a particular scanner's. Deliberately NOT a scanner name.
#:
#: The first version of the PEAD walk resolved this frame with
#: ``next(n for n in sc.SCANNERS if not ...needs_full_history)`` — i.e. whichever
#: scanner happened to sit first in the registry dict. That worked, and it was
#: wrong: **registry order is not a contract.** Adding a scanner at the top of
#: `SCANNERS`, or reordering it, would silently change which scanner's fetch
#: backed the walk, with nothing to notice. The flag is the only thing
#: `fetch_for` discriminates on, so the honest way to ask is to say what is
#: wanted rather than to name a scanner that happens to want the same thing.
DEFAULT_WINDOW = "__default_window__"


def _attach_pead(hits: dict[str, dict], fetch) -> None:
    """Attach `hit["pead"]` in place; never raises, never fetches earnings.

    `fetch(symbol) -> DataFrame` is the DEFAULT-WINDOW fetch, resolved once by
    the caller (see `DEFAULT_WINDOW`). Taking the fetch function rather than the
    factory keeps the registry out of this function entirely — it has no opinion
    about scanners, which is the whole point after the ordering bug above.
    Asking for the full-history fetch here would turn a context column into a
    per-symbol download.

    The earnings side is cache-only by construction (`earnings_reaction` never
    fetches on a display read), so a name with no cached calendar simply gets no
    walk.

    A symbol that cannot be walked gets NO `pead` key at all rather than an
    empty one, so the renderer's "is there a walk" test stays a plain lookup and
    absent can never be confused with a measured zero.
    """
    try:
        import earnings_reaction as _er
    except Exception as _exc:                               # pragma: no cover
        _log.warning("PEAD walk unavailable: %s", _exc)
        return
    for sym, h in hits.items():
        try:
            df = fetch(sym)
            if df is None or len(df) == 0:
                continue
            walk = _er.pead_walk(sym, df)
        except Exception as _exc:
            _log.debug("PEAD walk failed for %s: %s", sym, _exc)
            continue
        if walk.get("events"):
            h["pead"] = walk
