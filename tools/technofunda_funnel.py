"""technofunda_funnel.py — the 8-filter "delete funnel" as a watchlist sieve.

Implements [[strategies/TechnoFunda-Delete-Funnel]] (backlog B-38): a *subtractive*
funnel where each filter can only DELETE a name. A name is dropped by the FIRST
filter it fails (short-circuit), so the output is both a short survivor list and a
per-stage drop-off report showing where the universe died.

Doctrine (same as opportunity_hub / opportunity_report / sector_card)
--------------------------------------------------------------------
No Streamlit import. All data is INJECTED via a per-symbol context, so this module
is testable standalone and callable from a cron job. The caller (the dashboard, a
notebook, a test) is responsible for fetching:

    deep            fundamentals_deep.derive_fundamentals(symbol)   -> dict
    flags           red_flags.evaluate(symbol, ...)                 -> dict | None
    price           OHLCV DataFrame with lowercase 'close','volume' + DatetimeIndex
    bench_ret_12m   Nifty 12-month return as a fraction (e.g. 0.14)
    sector_ret_12m  the name's sector index 12-month return (optional)

The eight filters map 1:1 onto the strategy page; the code comments name the data
source each reuses and flag the two legs that are still first-cut (F2 CFO/PAT
proxy, F8 base-tightness heuristic) — the gaps B-38 records.

Missing-data policy (honesty)
-----------------------------
The funnel puts the burden of proof on the name: under the default `strict=True`,
a filter that CANNOT be evaluated DELETES the name ("no growth engine, no story —
next"). Set strict=False to let unverifiable filters pass with a caveat instead.
Two exceptions are hard-coded because they would otherwise empty the universe:
governance NOT_CHECKED items (auditor/related-party are always unsourced) and an
uncomputable D/E are recorded as caveats, never deletes — F3/F5 delete only on
*evidence* of a problem, matching "delete stretched balance sheets", not "delete
everything we couldn't measure".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

try:
    import pandas as pd
except Exception:                       # pragma: no cover - pandas always present in app
    pd = None

# Optional: the app's pivot-based VCP/base detector powers F8's base leg when
# available. Kept optional (and Streamlit-free) so the funnel still imports in a
# bare environment; F8 falls back to a range/up-volume heuristic without it.
try:
    import scanner_templates as _sc
except Exception:                       # pragma: no cover
    _sc = None


# ──────────────────────────────────────────────────────────────────────────────
# Thresholds — every gate value in one place, so a sweep (B-21-style) has a knob
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class Thresholds:
    # F1 growth
    min_rev_cagr_3y: float = 10.0        # %
    min_profit_cagr_3y: float = 10.0     # %
    growth_lookback_q: int = 6           # quarters to read when CAGR is absent
    min_positive_q: int = 4              # of those, how many must show +ve profit YoY
    # F3 leverage
    max_de: float = 1.0                  # debt / equity
    min_interest_cov: float = 3.0        # EBIT / interest
    # F2 cash conversion
    min_cfo_pat: float = 0.7             # Σ OCF / Σ PAT over the cycle
    # F4 capital efficiency
    min_roce: float = 15.0               # %
    min_roe: float = 15.0                # %
    roce_consistency_grace: float = 0.8  # prior-year ROCE may dip to grace×min
    # F6 trend
    # (200 DMA needs no threshold beyond price > SMA200)
    # F7 relative strength
    rs_lookback: int = 252               # ~12 trading months
    # F8 accumulation (first-cut heuristic)
    base_lookback: int = 20              # bars
    max_base_range: float = 0.15         # (high-low)/low over the base window
    min_up_vol_ratio: float = 1.0        # Σ up-day vol / Σ down-day vol must exceed


# ──────────────────────────────────────────────────────────────────────────────
# Result types
# ──────────────────────────────────────────────────────────────────────────────
PASS, DELETE, CAVEAT = "pass", "delete", "caveat"


@dataclass
class FilterOutcome:
    fid: str                 # "F3"
    label: str               # "Leverage"
    verdict: str             # PASS | DELETE | CAVEAT
    reason: str


@dataclass
class SymbolResult:
    symbol: str
    survived: bool
    deleted_at: Optional[str]            # filter id that killed it, or None
    outcomes: list[FilterOutcome]
    caveats: list[str] = field(default_factory=list)


@dataclass
class FunnelResult:
    survivors: list[str]
    results: dict[str, SymbolResult]
    dropoff: list[tuple[str, str, int]]  # (fid, label, n_deleted_here), funnel order
    n_in: int

    @property
    def n_out(self) -> int:
        return len(self.survivors)


# ──────────────────────────────────────────────────────────────────────────────
# Small numeric helpers on the injected price frame
# ──────────────────────────────────────────────────────────────────────────────
def _ret(close, n: int) -> Optional[float]:
    """Fractional return over the last `n` bars, or None if history is short."""
    if close is None or len(close) < n + 1:
        return None
    a, b = float(close.iloc[-1]), float(close.iloc[-1 - n])
    return None if b == 0 else a / b - 1.0


def _sma_last(close, n: int) -> Optional[float]:
    if close is None or len(close) < n:
        return None
    return float(close.tail(n).mean())


# ──────────────────────────────────────────────────────────────────────────────
# The eight filters. Each: (ctx, th, strict) -> FilterOutcome
# `ctx` is a plain dict; keys are documented in build_context().
# ──────────────────────────────────────────────────────────────────────────────
def _miss(fid: str, label: str, what: str, strict: bool) -> FilterOutcome:
    """Uniform handling of 'cannot evaluate' — delete under strict, else caveat."""
    if strict:
        return FilterOutcome(fid, label, DELETE, f"insufficient data ({what}) — deleted under strict")
    return FilterOutcome(fid, label, CAVEAT, f"insufficient data ({what}) — passed (lenient)")


def f1_growth(ctx, th: Thresholds, strict: bool) -> FilterOutcome:
    """Filter 1 — delete businesses that aren't actually growing.
    Source: fundamentals_deep 3Y CAGRs, falling back to the quarterly YoY trend."""
    d = ctx["deep"] or {}
    rc, pc = d.get("revenue_cagr_3y"), d.get("profit_cagr_3y")
    if rc is not None and pc is not None:
        if rc >= th.min_rev_cagr_3y and pc >= th.min_profit_cagr_3y:
            return FilterOutcome("F1", "Growth", PASS,
                                 f"3Y CAGR rev {rc:.0f}% / profit {pc:.0f}% ≥ thresholds")
        return FilterOutcome("F1", "Growth", DELETE,
                             f"3Y CAGR rev {rc:.0f}% / profit {pc:.0f}% below "
                             f"{th.min_rev_cagr_3y:.0f}/{th.min_profit_cagr_3y:.0f}")
    # Fallback: read the last N quarters' profit YoY.
    qs = [q for q in (d.get("quarters") or []) if q.get("profit_yoy") is not None]
    look = qs[:th.growth_lookback_q]
    if len(look) >= th.min_positive_q:
        pos = sum(1 for q in look if q["profit_yoy"] > 0)
        if pos >= th.min_positive_q:
            return FilterOutcome("F1", "Growth", PASS,
                                 f"{pos}/{len(look)} recent quarters +ve profit YoY")
        return FilterOutcome("F1", "Growth", DELETE,
                             f"only {pos}/{len(look)} recent quarters grew profit")
    return _miss("F1", "Growth", "no CAGR and <{} quarters".format(th.min_positive_q), strict)


def f2_cash(ctx, th: Thresholds, strict: bool) -> FilterOutcome:
    """Filter 2 — delete profits that never become cash. Primary test is the
    multi-year Σ OCF / Σ PAT ratio (cfo_pat_ratio); when that is absent it falls
    back to the FCF sign/streak proxy."""
    d = ctx["deep"] or {}
    ratio, years = d.get("cfo_pat_ratio"), d.get("cfo_pat_years")
    if ratio is not None:
        if ratio >= th.min_cfo_pat:
            return FilterOutcome("F2", "Cash", PASS,
                                 f"ΣOCF/ΣPAT {ratio:.2f} over {years}y ≥ {th.min_cfo_pat:.2f}")
        return FilterOutcome("F2", "Cash", DELETE,
                             f"ΣOCF/ΣPAT {ratio:.2f} over {years}y < {th.min_cfo_pat:.2f} "
                             f"— profits not converting to cash")
    # Fallback: FCF sign/streak proxy.
    fcf, streak = d.get("fcf"), d.get("fcf_negative_streak")
    if fcf is None and not d.get("fcf_history"):
        return _miss("F2", "Cash", "no CFO/PAT and no cash-flow history", strict)
    if fcf is not None and fcf > 0 and (streak or 0) == 0:
        return FilterOutcome("F2", "Cash", PASS, "FCF positive, no negative streak (proxy)")
    return FilterOutcome("F2", "Cash", DELETE,
                         f"FCF {'<=0' if (fcf is not None and fcf <= 0) else 'weak'}"
                         f"{f', {streak}y negative streak' if streak else ''} — profits not converting")


def f3_leverage(ctx, th: Thresholds, strict: bool) -> FilterOutcome:
    """Filter 3 — delete stretched balance sheets. D/E and interest coverage from
    the fundamentals_deep leverage keys added for this funnel. Deletes only on
    EVIDENCE of stretch: an uncomputable ratio is a caveat, not a kill."""
    d = ctx["deep"] or {}
    de, cov = d.get("debt_to_equity"), d.get("interest_coverage")
    bad = []
    if de is not None and de > th.max_de:
        bad.append(f"D/E {de:.2f} > {th.max_de:.1f}")
    if cov is not None and cov < th.min_interest_cov:
        bad.append(f"interest cover {cov:.1f}× < {th.min_interest_cov:.0f}×")
    if bad:
        return FilterOutcome("F3", "Leverage", DELETE, "; ".join(bad))
    if de is None and cov is None:
        # No debt figures at all — cannot confirm, but do not empty the universe.
        return FilterOutcome("F3", "Leverage", CAVEAT, "leverage not computable — unverified")
    return FilterOutcome("F3", "Leverage", PASS,
                         f"D/E {de if de is not None else 'n/a'}, "
                         f"cover {f'{cov:.1f}×' if cov is not None else 'no interest'}")


def f4_returns(ctx, th: Thresholds, strict: bool) -> FilterOutcome:
    """Filter 4 — delete poor capital efficiency. Gates on BOTH ROCE and ROE
    (consistently ≥ threshold), each with its prior year for a light
    'consistently' read. A name that clears ROCE but earns a poor ROE is levered
    into its capital-efficiency, which Filter 3 may not have caught."""
    d = ctx["deep"] or {}
    roce, roce_p = d.get("roce"), d.get("roce_prev")
    roe, roe_p = d.get("roe"), d.get("roe_prev")
    if roce is None and roe is None:
        return _miss("F4", "Returns", "no ROCE/ROE", strict)
    bad = []
    if roce is not None and roce < th.min_roce:
        bad.append(f"ROCE {roce:.0f}% < {th.min_roce:.0f}%")
    if roce_p is not None and roce_p < th.min_roce * th.roce_consistency_grace:
        bad.append(f"prior ROCE {roce_p:.0f}% below grace")
    if roe is not None and roe < th.min_roe:
        bad.append(f"ROE {roe:.0f}% < {th.min_roe:.0f}%")
    if roe_p is not None and roe_p < th.min_roe * th.roce_consistency_grace:
        bad.append(f"prior ROE {roe_p:.0f}% below grace")
    if bad:
        return FilterOutcome("F4", "Returns", DELETE, "; ".join(bad))
    parts = []
    if roce is not None:
        parts.append(f"ROCE {roce:.0f}%")
    if roe is not None:
        parts.append(f"ROE {roe:.0f}%")
    return FilterOutcome("F4", "Returns", PASS, ", ".join(parts) + " ≥ thresholds")


def f5_governance(ctx, th: Thresholds, strict: bool) -> FilterOutcome:
    """Filter 5 — delete governance red flags (HARD NO). red_flags.evaluate output.
    Deletes on any CRITICAL flag actually raised; NOT_CHECKED criticals (auditor /
    related-party are always unsourced) become a caveat, not a kill — otherwise no
    name could ever clear this stack (see red_flags.no_critical_flags)."""
    fl = ctx.get("flags")
    if not fl or not fl.get("flags"):
        return _miss("F5", "Governance", "no red-flag scan", strict)
    crit_raised, watch_raised, unchecked = [], [], 0
    for f in fl["flags"]:
        if f["state"] == "FLAG" and f["severity"] == "CRITICAL":
            crit_raised.append(f["label"])
        elif f["state"] == "FLAG":
            watch_raised.append(f["label"])
        elif f["state"] == "NOT_CHECKED" and f["severity"] == "CRITICAL":
            unchecked += 1
    if crit_raised:
        return FilterOutcome("F5", "Governance", DELETE,
                             "critical flag — " + ", ".join(crit_raised))
    note = []
    if watch_raised:
        note.append("watch: " + ", ".join(watch_raised))
    if unchecked:
        note.append(f"{unchecked} critical item(s) unverifiable")
    if note:
        return FilterOutcome("F5", "Governance", CAVEAT, "; ".join(note))
    return FilterOutcome("F5", "Governance", PASS, "no critical flags raised")


def f6_trend(ctx, th: Thresholds, strict: bool) -> FilterOutcome:
    """Filter 6 — delete anything below the 200 DMA. Injected price frame."""
    close = ctx.get("close")
    sma = _sma_last(close, 200)
    if sma is None:
        return _miss("F6", "200 DMA", "<200 bars", strict)
    last = float(close.iloc[-1])
    if last > sma:
        return FilterOutcome("F6", "200 DMA", PASS, f"{last:.0f} > 200DMA {sma:.0f}")
    return FilterOutcome("F6", "200 DMA", DELETE, f"{last:.0f} ≤ 200DMA {sma:.0f} — let price confirm")


def f7_rs(ctx, th: Thresholds, strict: bool) -> FilterOutcome:
    """Filter 7 — delete relative laggards. Stock 12m return vs Nifty AND, when a
    sector return is injected, vs its sector. Money flows to the clearest outcome."""
    r = _ret(ctx.get("close"), th.rs_lookback)
    bench = ctx.get("bench_ret_12m")
    if r is None or bench is None:
        return _miss("F7", "Rel. strength", "no 12m return / benchmark", strict)
    sect = ctx.get("sector_ret_12m")
    lag = []
    if r <= bench:
        lag.append(f"vs Nifty ({r*100:+.0f}% ≤ {bench*100:+.0f}%)")
    if sect is not None and r <= sect:
        lag.append(f"vs sector ({r*100:+.0f}% ≤ {sect*100:+.0f}%)")
    if lag:
        return FilterOutcome("F7", "Rel. strength", DELETE, "lagging " + "; ".join(lag))
    tail = "" if sect is None else f" and sector {sect*100:+.0f}%"
    return FilterOutcome("F7", "Rel. strength", PASS,
                         f"12m {r*100:+.0f}% leads Nifty {bench*100:+.0f}%{tail}")


def f8_accumulation(ctx, th: Thresholds, strict: bool) -> FilterOutcome:
    """Filter 8 — delete charts with no accumulation footprint. Base leg uses the
    app's pivot-based VCP detector (`detect_vcp_geometry` — contractions shrinking
    + volume drying) when available, falling back to a tight-range heuristic;
    either way the up/down volume ratio must show buyers, not distribution."""
    close, vol = ctx.get("close"), ctx.get("volume")
    if close is None or vol is None or len(close) < th.base_lookback:
        return _miss("F8", "Accumulation", f"<{th.base_lookback} bars", strict)

    # Up-volume dominance — the "volume expanding on up moves" half.
    win_c = close.tail(th.base_lookback)
    win_v = vol.tail(th.base_lookback)
    diff = win_c.diff().tail(th.base_lookback)
    up_v, dn_v = float(win_v[diff > 0].sum()), float(win_v[diff < 0].sum())
    up_ratio = up_v / dn_v if dn_v > 0 else float("inf")
    accum = up_ratio >= th.min_up_vol_ratio

    # Base leg — prefer the real VCP detector (needs high/low), else range width.
    df = ctx.get("price")
    vcp = None
    if (_sc is not None and df is not None and pd is not None and len(df) >= 90
            and {"high", "low"} <= set(getattr(df, "columns", []))):
        try:
            vcp = _sc.detect_vcp_geometry(df)
        except Exception:
            vcp = None
    if vcp is not None:
        base_desc = f"VCP base {vcp.get('footprint', '?')} ({vcp.get('n_contractions', '?')} contractions"
        base_desc += ", vol drying)" if vcp.get("vol_drying") else ")"
        if accum:
            return FilterOutcome("F8", "Accumulation", PASS,
                                 f"{base_desc}, up/down vol {up_ratio:.1f}×")
        return FilterOutcome("F8", "Accumulation", DELETE,
                             f"{base_desc} but up/down vol {up_ratio:.1f}× — distribution")

    # Fallback heuristic when no VCP geometry (or detector unavailable).
    lo, hi = float(win_c.min()), float(win_c.max())
    rng = (hi - lo) / lo if lo > 0 else 1.0
    tight = rng <= th.max_base_range
    if tight and accum:
        return FilterOutcome("F8", "Accumulation", PASS,
                             f"tight base {rng*100:.0f}% wide, up/down vol {up_ratio:.1f}× (heuristic)")
    why = []
    if not tight:
        why.append(f"no base — range {rng*100:.0f}% > {th.max_base_range*100:.0f}% and no VCP")
    if not accum:
        why.append(f"up/down vol {up_ratio:.1f}× — distribution")
    return FilterOutcome("F8", "Accumulation", DELETE, "; ".join(why))


#: Filters in funnel order. Fundamentals first (1–5), then price takes over (6–8).
FILTERS: list[tuple[str, str, Callable]] = [
    ("F1", "Growth",        f1_growth),
    ("F2", "Cash",          f2_cash),
    ("F3", "Leverage",      f3_leverage),
    ("F4", "Returns",       f4_returns),
    ("F5", "Governance",    f5_governance),
    ("F6", "200 DMA",       f6_trend),
    ("F7", "Rel. strength", f7_rs),
    ("F8", "Accumulation",  f8_accumulation),
]


# ──────────────────────────────────────────────────────────────────────────────
# Context builder + runners
# ──────────────────────────────────────────────────────────────────────────────
def build_context(symbol: str, *, deep: dict | None = None, flags: dict | None = None,
                  price=None, bench_ret_12m: float | None = None,
                  sector_ret_12m: float | None = None) -> dict[str, Any]:
    """Assemble one symbol's funnel context from already-fetched inputs.

    `price` is an OHLCV DataFrame with lowercase 'close' and 'volume' columns; the
    close/volume series are split out here so the filters stay frame-agnostic.
    """
    close = vol = None
    if price is not None and pd is not None and len(price):
        if "close" in price:
            close = price["close"].dropna()
        if "volume" in price:
            vol = price["volume"]
    return {
        "symbol": symbol.upper(),
        "deep": deep,
        "flags": flags,
        "price": price,          # raw OHLCV frame — F8's base detector needs high/low
        "close": close,
        "volume": vol,
        "bench_ret_12m": bench_ret_12m,
        "sector_ret_12m": sector_ret_12m,
    }


def run_one(ctx: dict, thresholds: Thresholds | None = None,
            strict: bool = True) -> SymbolResult:
    """Apply the funnel to one context, short-circuiting on the first delete."""
    th = thresholds or Thresholds()
    outcomes: list[FilterOutcome] = []
    caveats: list[str] = []
    for fid, label, fn in FILTERS:
        oc = fn(ctx, th, strict)
        outcomes.append(oc)
        if oc.verdict == CAVEAT:
            caveats.append(f"{oc.fid} {oc.reason}")
        if oc.verdict == DELETE:
            return SymbolResult(ctx["symbol"], False, fid, outcomes, caveats)
    return SymbolResult(ctx["symbol"], True, None, outcomes, caveats)


def run_funnel(contexts: list[dict], thresholds: Thresholds | None = None,
               strict: bool = True) -> FunnelResult:
    """Run the funnel over many contexts and return survivors + drop-off report."""
    th = thresholds or Thresholds()
    results: dict[str, SymbolResult] = {}
    killed_at: dict[str, int] = {fid: 0 for fid, _, _ in FILTERS}
    survivors: list[str] = []
    for ctx in contexts:
        r = run_one(ctx, th, strict)
        results[ctx["symbol"]] = r
        if r.survived:
            survivors.append(ctx["symbol"])
        else:
            killed_at[r.deleted_at] += 1
    dropoff = [(fid, label, killed_at[fid]) for fid, label, _ in FILTERS]
    return FunnelResult(survivors, results, dropoff, n_in=len(contexts))


def format_report(fr: FunnelResult) -> str:
    """Plain-text funnel drop-off — the 'where the universe died' view."""
    lines = [f"Delete-funnel: {fr.n_in} in → {fr.n_out} survive", ""]
    remaining = fr.n_in
    for fid, label, killed in fr.dropoff:
        remaining -= killed
        bar = "▓" * min(killed, 40)
        lines.append(f"  {fid} {label:<14} −{killed:<4} → {remaining:>4} left  {bar}")
    if fr.survivors:
        lines += ["", "Survivors: " + ", ".join(fr.survivors)]
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Synthetic demo — proves the engine with no network (real wiring is the caller's
# job: derive_fundamentals + red_flags.evaluate + cached OHLCV + Nifty return).
# ──────────────────────────────────────────────────────────────────────────────
def _demo_contexts() -> list[dict]:
    import numpy as np

    def price(trend: float, base_tight: bool, up_vol: bool, n: int = 300):
        idx = pd.date_range("2025-01-01", periods=n, freq="B")
        # A rising series (trend>0) ending in either a tight base or a wide swing.
        drift = np.linspace(0, trend, n)
        noise = (np.sin(np.linspace(0, 30, n)) * (0.01 if base_tight else 0.08))
        close = 100 * (1 + drift + noise)
        vols = np.full(n, 1e5)
        # Put more volume on up days if up_vol.
        chg = np.diff(close, prepend=close[0])
        vols = np.where(chg > 0, vols * (1.6 if up_vol else 0.6), vols)
        return pd.DataFrame({"close": close, "volume": vols}, index=idx)

    good_deep = dict(revenue_cagr_3y=22, profit_cagr_3y=30, quarters=[],
                     fcf=120, fcf_negative_streak=0, cfo_pat_ratio=1.1, cfo_pat_years=5,
                     debt_to_equity=0.3, interest_coverage=8.0,
                     roce=24, roce_prev=22, roe=21, roe_prev=20)
    clean_flags = {"flags": [
        {"state": "CLEAN", "severity": "CRITICAL", "label": "Pledge"},
        {"state": "NOT_CHECKED", "severity": "CRITICAL", "label": "Auditor"}]}

    ctxs = []
    # A — survives everything.
    ctxs.append(build_context("ALPHAOK", deep=good_deep, flags=clean_flags,
                              price=price(0.9, True, True), bench_ret_12m=0.12,
                              sector_ret_12m=0.20))
    # B — great fundamentals but pledged promoter → dies at F5.
    pledged = {"flags": [{"state": "FLAG", "severity": "CRITICAL",
                          "label": "Promoter pledge 60%"}]}
    ctxs.append(build_context("BETAPLEDGE", deep=good_deep, flags=pledged,
                              price=price(0.9, True, True), bench_ret_12m=0.12))
    # C — good business, clean, but below its 200 DMA → dies at F6.
    ctxs.append(build_context("GAMMADOWN", deep=good_deep, flags=clean_flags,
                              price=price(-0.4, True, True), bench_ret_12m=0.12))
    # D — stretched balance sheet → dies at F3.
    levered = dict(good_deep, debt_to_equity=2.4, interest_coverage=1.2)
    ctxs.append(build_context("DELTADEBT", deep=levered, flags=clean_flags,
                              price=price(0.9, True, True), bench_ret_12m=0.12))
    # E — no growth → dies at F1.
    flat = dict(good_deep, revenue_cagr_3y=2, profit_cagr_3y=-5)
    ctxs.append(build_context("EPSILONFLAT", deep=flat, flags=clean_flags,
                              price=price(0.9, True, True), bench_ret_12m=0.12))
    return ctxs


if __name__ == "__main__":   # py -3 tools/technofunda_funnel.py
    fr = run_funnel(_demo_contexts())
    print(format_report(fr))
    print()
    for sym, r in fr.results.items():
        tag = "✓ survives" if r.survived else f"✗ deleted at {r.deleted_at}"
        kill = next((o for o in r.outcomes if o.verdict == DELETE), None)
        print(f"{sym:<12} {tag}" + (f" — {kill.reason}" if kill else ""))
