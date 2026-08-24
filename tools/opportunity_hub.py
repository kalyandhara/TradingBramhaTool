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
RISK_SCANNERS: tuple[str, ...] = ("Downside Risk", "Bearish Reversal Candle", "Support Breakdown", "RSI Divergence Bear", "%R Exhaustion Sell")

#: Registry entries the pipeline must not run.
#: "Zero-Debt Quality PEAD" declares ``fn = scan_pead`` — the IDENTICAL function
#: as "PEAD Drift". It only differs when routed through ``run_quality_pead()``
#: with its fundamentals gate, which a generic pipeline never calls. Left in, it
#: would silently turn every PEAD hit into two votes for the same detector.
PIPELINE_EXCLUDED: tuple[str, ...] = ("Zero-Debt Quality PEAD",)

#: Measured to BEAT a random-entry baseline (wiki/analyses/Backtest-Harness):
#: Falling Wedge +0.74% @20d (+0.14R), Harmonic Reversal +0.67% (+0.25R).
MEASURED_EDGE_SCANNERS: tuple[str, ...] = (
    "Falling Wedge",
    "Harmonic Reversal (XABCD)",
)

#: Measured and found AT OR BELOW that baseline. Kept for coverage and context,
#: but they must not carry the same weight as the two that were measured to
#: work. Order Block sits here on its raw forward edge (−0.74%) despite a mildly
#: positive +0.11R from its 2R targets.
MEASURED_WEAK_SCANNERS: tuple[str, ...] = (
    "Order Block Retest",
    "RSI 60-40 Setup",
    "VCP Coiling",
    "Structural Breakout",
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
    if name in MEASURED_EDGE_SCANNERS:
        return "measured"
    if name in MEASURED_WEAK_SCANNERS:
        return "weak"
    return "unmeasured"


def scanner_weight(name: str) -> float:
    """Edge points a hit from this scanner is worth before family capping."""
    return {"measured": WEIGHT_MEASURED, "weak": WEIGHT_WEAK,
            "unmeasured": WEIGHT_UNMEASURED, "risk": 0.0}[scanner_tier(name)]


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
        if scanner_family(n) is None and n not in RISK_SCANNERS:
            families.append(n)
            best_per_family[n] = scanner_weight(n)
    return families, round(sum(best_per_family.values()), 2), risk


def run_scanner_pipeline(symbols: list[str], fetch_for, *,
                         scanners: list[str] | None = None,
                         benchmark_df=None, progress_cb=None) -> dict[str, dict]:
    """Run every pipeline scanner over `symbols`; return one entry per name hit.

    `fetch_for(scanner_name) -> fetch_fn` is deliberately a FACTORY, not a single
    fetch function. Two scanners in the registry carry ``needs_full_history``
    (ATH and IPO-base breakout) and are meaningless on the default ~300-bar
    window: `scan_ath_breakout` only requires 250 bars, so handed a short frame
    it fires happily and reports a ~1-year high as an all-time high. Making the
    caller supply a per-scanner fetch means that rule is structural on every
    path instead of something each caller has to remember.

    Each returned value carries:
        scanners     — every scanner that fired, in run order
        families     — the distinct families those scanners belong to
        edge_points  — family-capped weight sum (what the ranking spends)
        raw_points   — uncapped weight sum (for transparency only)
        best_card    — the highest-scoring scanner card, for rendering
        best_scanner — which scanner produced it
        risk_flags   — bearish scanners that also fired (never a vote)
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
    return {s: h for s, h in hits.items() if h["best_card"] is not None}
