"""FR-2 — the one fundamental band scorer.

Why this is a module and not a function inside the page
-------------------------------------------------------
The deep-dive report wants six signal donuts; Radar-Chart-Analyzer-Fit RC-1
wants four radar axes over the same ideas. If those were scored separately the
dashboard would carry **two fundamental opinions** that disagree in the third
decimal and eventually in the verdict word. Both roadmaps therefore call for a
single shared scorer, and this is it. Anything that wants to say "the
fundamentals look like X" calls `score_all()`.

What it deliberately does NOT do
--------------------------------
There is **no overall /100 here.** The dashboard already carries the M1 technical
Overall Rating, the council verdict, and Setup Intelligence; a fourth number
badged "Overall" would be read as a competing master score. What this module
emits instead is a per-axis score, a verdict *word*, and a two-word
business-quality-vs-entry-price split — the same split the source mockup used to
keep "good business" from reading as "buy now".

Band calibration is judgement, and it is stated here rather than buried
-----------------------------------------------------------------------
Every band below is an explicit constant with the reasoning next to it, because
wrong bands are how a rating loses trust (the M1-weights lesson). They are tuned
for NSE listed equity, where quality compounders routinely trade at P/E 50-90 and
a 25% P/E would be cheap — US-calibrated bands would mark the whole market
overvalued. Change them here, once, and every consumer moves together.

Missing data never scores. An axis with no resolvable input returns
`score=None` and renders DATA N/A; it is never given a neutral 50, which would
read as "average" when it means "unknown".
"""

from __future__ import annotations

from typing import Any, Sequence

# ──────────────────────────────────────────────────────────────────────────────
# Band tables: (threshold, score) descending by quality, plus a floor score.
# `_band` walks them in order and takes the first threshold the value satisfies.
# ──────────────────────────────────────────────────────────────────────────────
# Lower-is-better metrics
_PE_BANDS   = ((15, 100), (25, 80), (40, 55), (60, 30))      # NSE compounders sit 40-70
_PB_BANDS   = ((2, 100), (4, 80), (8, 55), (12, 30))
_PEG_BANDS  = ((1.0, 100), (1.5, 80), (2.5, 55), (4.0, 30))  # Lynch's PEG<1 anchor
_D2E_BANDS  = ((0.25, 100), (0.5, 85), (1.0, 60), (2.0, 35))  # in ×, not %
# Debtor (receivable) days, NOT working-capital days. yfinance's Working Capital
# is current assets minus current liabilities, which includes cash and current
# investments — so a debt-free, cash-rich company posts a huge WC-days number
# and scored as "stretched" when it was the opposite. Receivable days measure
# actual collection stress and no amount of cash flatters them.
_DEBT_DAYS_BANDS = ((30, 100), (60, 80), (90, 55), (150, 30))

# Higher-is-better metrics
# Growth is scored on a MEASURED DISTRIBUTION CURVE, not a band ladder — the one
# axis in this module that is, and the reason is worth stating.
#
# It used to share one table: (25,100),(15,80),(8,55),(3,30). Measured over a
# 150-name stride sample of the NIFTY-500 (`calibrate_growth_bands.py`, raw values
# in cache/growth_calibration.json, 2026-09-04):
#
#            metric            median   >=25%    p75    p90
#     revenue_cagr_3y           12.8%   18.8%   22.0   35.1
#     profit_cagr_3y            16.4%   31.0%   29.4   48.7
#     revenue_yoy               18.6%   35.3%   35.2   52.0
#
# That 25% ceiling handed a perfect 100 to a fifth of the market on revenue CAGR
# and over a THIRD on quarterly YoY. Across the whole sample the old table read
# STRONG for 39% of listed India and put 18% at 90+; inside an individual peer
# group of post-COVID compounders (jewellers, insurers) it pinned nearly every
# row at 90-100. **The peer table is what exposed it** — one company at 93 looks
# fine; ten companies all at 90-100 in a column is visibly not a measurement.
#
# Two things the fix needed, in order:
#
# 1. **Per-metric curves.** The three inputs are not interchangeable. Quarterly
#    YoY runs hotter than a 3-year CAGR (one soft base quarter lifts it), and
#    profit compounds faster than revenue through operating leverage. One shared
#    ladder scored the same company's growth well twice.
# 2. **Interpolation instead of steps.** Re-banding alone did not fix it: with
#    four rungs the axis median came out at 47, because averaging three step
#    scores drags the middle down (the rungs below the median are much further
#    from it than the rungs above). Steps also collapse 150 companies onto a
#    handful of values, which is its own kind of non-measurement. Interpolating
#    between percentile anchors puts the median company at exactly 55 and yields
#    65 distinct scores over the sample instead of a handful.
#
# Anchors map each metric's own percentiles onto the shared verdict scale:
# p10 -> 20, p25 -> 35, p50 -> 55, p75 -> 80, p90 -> 95, clamped to [10, 100].
# So the median NSE grower reads MODERATE (which is what median means), STRONG
# is roughly the top fifth, and only the genuine top decile approaches 100.
# Re-run calibrate_growth_bands.py and move these numbers when the market moves;
# they are a snapshot of a distribution, not a law.
_GROWTH_CURVES = {
    "revenue_cagr_3y": ((-0.5, 20), (4.6, 35), (12.8, 55), (22.0, 80), (35.1, 95)),
    "profit_cagr_3y":  ((-7.8, 20), (3.5, 35), (16.4, 55), (29.4, 80), (48.7, 95)),
    "revenue_yoy":     ((-0.5, 20), (10.5, 35), (18.6, 55), (35.2, 80), (52.0, 95)),
}
_ROE_BANDS    = ((25, 100), (18, 80), (12, 55), (8, 30))
_NPM_BANDS    = ((20, 100), (12, 75), (6, 50), (3, 25))
_FCFM_BANDS   = ((15, 100), (8, 75), (3, 50), (0, 30))       # FCF as % of revenue
_TREND_BANDS  = ((2, 100), (0, 70), (-2, 45))                # ROCE change, pp YoY
_CV_BANDS     = ((0.15, 100), (0.30, 70), (0.50, 40))        # margin coeff. of variation

_FLOOR = 10          # score for anything past the last band
_MIN_ANNUAL_FOR_CONSISTENCY = 3

# Verdict vocabularies, best-first. Cut points are shared: >=75, >=55, >=35, else.
_VERDICTS = {
    "valuation":            ("CHEAP", "FAIR", "STRETCHED", "OVERVALUED"),
    "growth":               ("STRONG", "MODERATE", "SLOWING", "WEAK"),
    "health":               ("STRONG", "SOLID", "STRETCHED", "WEAK"),
    "returns":              ("EXCELLENT", "GOOD", "AVERAGE", "POOR"),
    "capital_allocation":   ("DISCIPLINED", "BALANCED", "INVESTING", "POOR"),
    "earnings_consistency": ("CONSISTENT", "STEADY", "VOLATILE", "ERRATIC"),
}
_CUTS = (75, 55, 35)

AXES = tuple(_VERDICTS.keys())

AXIS_LABELS = {
    "valuation":            "Valuation",
    "growth":               "Growth",
    "health":               "Health",
    "returns":              "Returns",
    "capital_allocation":   "Capital Allocation",
    "earnings_consistency": "Earnings Consistency",
}

#: Axes describing the business itself. Valuation is excluded on purpose — it
#: describes the *price*, and mixing the two is exactly the error the
#: good-business-vs-bad-entry split exists to prevent.
_BUSINESS_AXES = ("growth", "health", "returns",
                  "capital_allocation", "earnings_consistency")


def _band(value: float | None, bands: Sequence[tuple[float, int]],
          lower_is_better: bool) -> int | None:
    """Map a value onto its band score, or None when the value is missing."""
    if value is None:
        return None
    for threshold, score in bands:
        if (value <= threshold) if lower_is_better else (value >= threshold):
            return score
    return _FLOOR


def _curve(value: float | None, metric: str) -> int | None:
    """Score a growth metric off its measured NSE distribution.

    Piecewise-linear between the percentile anchors in `_GROWTH_CURVES`, clamped
    to [10, 100] outside them: a 400% CAGR off a tiny base is not four times as
    impressive as 100%, and there is no evidence in the sample to separate them.
    `None` in, `None` out — a missing input is never scored (see module docstring).
    """
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v != v:                      # NaN
        return None
    pts = _GROWTH_CURVES[metric]
    if v <= pts[0][0]:
        return 10
    if v >= pts[-1][0]:
        return 100
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if v <= x1:
            return y1 if x1 == x0 else round(y0 + (y1 - y0) * (v - x0) / (x1 - x0))
    return 100


def _verdict(axis: str, score: float | None) -> str | None:
    if score is None:
        return None
    words = _VERDICTS[axis]
    for cut, word in zip(_CUTS, words):
        if score >= cut:
            return word
    return words[-1]


def _axis(axis: str, parts: list[tuple[str, int | None, str]],
          agg: str = "mean") -> dict[str, Any]:
    """Combine an axis's sub-scores.

    `parts` is (metric name, band score, human-readable driver text). The axis
    score is normally the mean of the sub-scores that resolved — a company
    missing PEG is still scored on P/E and P/B rather than being penalised for a
    data gap. The driver line names only the metrics that actually counted, so
    the reader can see what the verdict rests on.

    `agg="min_drag"` blends the mean with the worst sub-score 50/50. Used where a
    single bad input is not compensable: 1.95× leverage does not become healthy
    because working capital is tight, and a plain mean was calling exactly that
    case "STRONG".
    """
    got = [(n, s, d) for n, s, d in parts if s is not None]
    missing = [n for n, s, _ in parts if s is None]
    if not got:
        return {"axis": axis, "label": AXIS_LABELS[axis], "score": None,
                "verdict": None, "drivers": "", "missing": missing,
                "n_used": 0, "n_possible": len(parts)}
    mean = sum(s for _, s, _ in got) / len(got)
    worst = min(s for _, s, _ in got)
    score = round(0.5 * mean + 0.5 * worst) if agg == "min_drag" else round(mean)
    return {
        "axis": axis, "label": AXIS_LABELS[axis],
        "score": score, "verdict": _verdict(axis, score),
        "drivers": ", ".join(d for _, _, d in got),
        "missing": missing, "n_used": len(got), "n_possible": len(parts),
    }


def _f(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if (f != f) else f          # NaN check without importing math


def _cv(values: list[float]) -> float | None:
    """Coefficient of variation (sd / |mean|) — scale-free volatility."""
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return None
    mean = sum(vals) / len(vals)
    if mean == 0:
        return None
    var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
    return (var ** 0.5) / abs(mean)


# ──────────────────────────────────────────────────────────────────────────────
# The six axes
# ──────────────────────────────────────────────────────────────────────────────
def _score_valuation(f: dict, d: dict) -> dict:
    pe, pb, peg = _f(f.get("pe")), _f(f.get("pb")), _f(f.get("peg"))

    # A loss-making company has no P/E and no PEG, which would leave P/B as the
    # only scoring input — and P/B alone called SWIGGY "CHEAP" while it was
    # burning cash with 0/4 profitable years. Book value cannot price equity
    # that has no earnings, so this returns an explicit NO EARNINGS state
    # instead of a number: unscored, but for a stated reason rather than a gap.
    annual = d.get("annual") or []
    latest_ni = _f(annual[0].get("net_income")) if annual else None
    loss_making = any(v is not None and v < 0
                      for v in (_f(f.get("npm")), _f(f.get("eps_ttm")), latest_ni))
    if pe is None and loss_making:
        drivers = "loss-making — P/E and PEG undefined"
        if pb is not None:
            drivers += f"; P/B {pb:.1f}× not scored alone"
        return {"axis": "valuation", "label": AXIS_LABELS["valuation"],
                "score": None, "verdict": "NO EARNINGS", "drivers": drivers,
                "missing": ["pe", "peg"], "n_used": 0, "n_possible": 3}

    return _axis("valuation", [
        ("pe",  _band(pe,  _PE_BANDS,  True), f"P/E {pe:.1f}×" if pe else ""),
        ("pb",  _band(pb,  _PB_BANDS,  True), f"P/B {pb:.1f}×" if pb else ""),
        ("peg", _band(peg, _PEG_BANDS, True), f"PEG {peg:.2f}×" if peg else ""),
    ])


def _score_growth(f: dict, d: dict) -> dict:
    rev3 = _f(d.get("revenue_cagr_3y"))
    pro3 = _f(d.get("profit_cagr_3y"))

    # Prefer OUR date-matched quarterly YoY over yfinance's `revenueGrowth`.
    # The two disagree materially (TITAN: 48% ours vs 80.5% theirs) and ours is
    # derived from the statements in the open, where the reader can check it.
    # yfinance's figure stays as the fallback for names with no quarterly frame.
    quarters = d.get("quarters") or []
    revg = next((_f(q.get("revenue_yoy")) for q in quarters
                 if q.get("revenue_yoy") is not None), None)
    yoy_src = "latest Q"
    if revg is None:
        revg, yoy_src = _f(f.get("revenue_growth")), "yfinance"

    return _axis("growth", [
        ("revenue_cagr_3y", _curve(rev3, "revenue_cagr_3y"),
         f"Rev CAGR 3Y {rev3:.1f}%" if rev3 is not None else ""),
        ("profit_cagr_3y", _curve(pro3, "profit_cagr_3y"),
         f"Profit CAGR 3Y {pro3:.1f}%" if pro3 is not None else ""),
        ("revenue_yoy", _curve(revg, "revenue_yoy"),
         f"Rev YoY {revg:.1f}% ({yoy_src})" if revg is not None else ""),
    ])


def _score_health(f: dict, d: dict) -> dict:
    # yfinance reports debtToEquity as a percentage; convert to × for the bands.
    d2e_pct = _f(f.get("debt_to_equity"))
    d2e = None if d2e_pct is None else d2e_pct / 100.0
    dbd = _f(d.get("debtor_days"))
    streak = d.get("fcf_negative_streak")
    fcf_score = None
    fcf_text = ""
    if d.get("fcf") is not None or streak is not None:
        streak = int(streak or 0)
        fcf_score = 100 if streak == 0 else (50 if streak == 1 else _FLOOR)
        fcf_text = ("FCF positive" if streak == 0
                    else f"FCF negative {streak}y")
    return _axis("health", [
        ("debt_to_equity", _band(d2e, _D2E_BANDS, True),
         f"D/E {d2e:.2f}×" if d2e is not None else ""),
        ("fcf", fcf_score, fcf_text),
        ("debtor_days", _band(dbd, _DEBT_DAYS_BANDS, True),
         f"Debtor {dbd:.0f}d" if dbd is not None else ""),
    ], agg="min_drag")


def _score_returns(f: dict, d: dict) -> dict:
    roe, roce, npm = _f(f.get("roe")), _f(d.get("roce")), _f(f.get("npm"))
    return _axis("returns", [
        ("roe",  _band(roe,  _ROE_BANDS, False), f"ROE {roe:.1f}%" if roe is not None else ""),
        ("roce", _band(roce, _ROE_BANDS, False), f"ROCE {roce:.1f}%" if roce is not None else ""),
        ("npm",  _band(npm,  _NPM_BANDS, False), f"Net margin {npm:.1f}%" if npm is not None else ""),
    ])


def _score_capital_allocation(f: dict, d: dict) -> dict:
    """Newly computable: FR-1's cash-flow statements are what unlocked this axis.

    Two questions: does the business convert revenue into free cash, and is the
    return on the capital it employs rising or falling?
    """
    fcf = _f(d.get("fcf"))
    annual = d.get("annual") or []
    revenue = _f(annual[0]["revenue"]) if annual else None
    fcf_margin = (round(fcf / revenue * 100, 2)
                  if (fcf is not None and revenue not in (None, 0) and revenue > 0)
                  else None)
    roce, roce_prev = _f(d.get("roce")), _f(d.get("roce_prev"))
    trend = None if (roce is None or roce_prev is None) else round(roce - roce_prev, 2)
    return _axis("capital_allocation", [
        ("fcf_margin", _band(fcf_margin, _FCFM_BANDS, False),
         f"FCF margin {fcf_margin:.1f}%" if fcf_margin is not None else ""),
        ("roce_trend", _band(trend, _TREND_BANDS, False),
         f"ROCE {trend:+.1f}pp YoY" if trend is not None else ""),
    ])


def _score_earnings_consistency(f: dict, d: dict) -> dict:
    """Consistency of *reported* earnings — explicitly not a consensus measure.

    The source mockup's version of this signal counted misses against analyst
    consensus, which has no free NSE source (established in
    PEAD-Scanner-Roadmap). What IS knowable is whether the company has actually
    delivered: profitable years, growing years, and a stable margin. The UI must
    label it as realised consistency so it is never read as "never missed".
    """
    annual = d.get("annual") or []
    profits = [_f(a.get("net_income")) for a in annual]
    margins = [_f(a.get("net_margin")) for a in annual]
    profits = [p for p in profits if p is not None]
    margins = [m for m in margins if m is not None]

    if len(profits) < _MIN_ANNUAL_FOR_CONSISTENCY:
        return _axis("earnings_consistency", [
            ("positive_years", None, ""), ("growth_years", None, ""),
            ("margin_stability", None, ""),
        ])

    pos_ratio = sum(1 for p in profits if p > 0) / len(profits)
    # `annual` is newest-first, so a "growth year" is a year that earned more
    # than the year after it in the list.
    pairs = list(zip(profits, profits[1:]))
    grow_ratio = (sum(1 for new, old in pairs if old > 0 and new > old) / len(pairs)
                  if pairs else None)
    cv = _cv(margins)

    return _axis("earnings_consistency", [
        ("positive_years", round(pos_ratio * 100),
         f"{sum(1 for p in profits if p > 0)}/{len(profits)} profitable years"),
        ("growth_years", None if grow_ratio is None else round(grow_ratio * 100),
         "" if grow_ratio is None
         else f"{sum(1 for n, o in pairs if o > 0 and n > o)}/{len(pairs)} growth years"),
        ("margin_stability", _band(cv, _CV_BANDS, True),
         f"margin CV {cv:.2f}" if cv is not None else ""),
    ])


_SCORERS = {
    "valuation": _score_valuation,
    "growth": _score_growth,
    "health": _score_health,
    "returns": _score_returns,
    "capital_allocation": _score_capital_allocation,
    "earnings_consistency": _score_earnings_consistency,
}


# ──────────────────────────────────────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────────────────────────────────────
def score_all(fundamentals: dict | None, deep: dict | None) -> dict[str, Any]:
    """Score every axis from the `.info` snapshot + the FR-1 statement layer.

    Returns `{axes: {name: result}, coverage: {...}, business: {...},
    entry: {...}}`. `coverage` counts the individual metric inputs that
    resolved across all axes — a *coverage* meter answering "how much of this
    read is actually measured", never a quality score.
    """
    f, d = fundamentals or {}, deep or {}
    axes = {name: fn(f, d) for name, fn in _SCORERS.items()}

    used = sum(a["n_used"] for a in axes.values())
    possible = sum(a["n_possible"] for a in axes.values())

    # Business quality = the mean of the business axes that scored. Emitted as a
    # WORD, not a number, so it cannot be mistaken for a fourth Overall Rating.
    biz = [axes[a]["score"] for a in _BUSINESS_AXES if axes[a]["score"] is not None]
    biz_score = round(sum(biz) / len(biz)) if biz else None
    if biz_score is None:
        biz_word = None
    elif biz_score >= 70:
        biz_word = "GOOD QUALITY"
    elif biz_score >= 50:
        biz_word = "MIXED QUALITY"
    else:
        biz_word = "WEAK QUALITY"

    val = axes["valuation"]
    return {
        "axes": axes,
        "coverage": {"have": used, "total": possible,
                     "missing": [m for a in axes.values() for m in a["missing"]]},
        # Deliberately two separate readings: a good business at a bad price is
        # the single most common way a fundamentals page misleads.
        "business": {"word": biz_word, "score": biz_score,
                     "axes_used": len(biz), "axes_possible": len(_BUSINESS_AXES)},
        "entry":    {"word": val["verdict"], "score": val["score"],
                     "drivers": val["drivers"]},
    }


if __name__ == "__main__":   # py -3 tools/fundamental_score.py ITC TITAN
    import sys, json
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
    import fundamentals_deep as fdeep
    import stock_council as council

    for sym in (sys.argv[1:] or ["ITC"]):
        res = score_all(council.fetch_fundamentals(sym), fdeep.derive_fundamentals(sym))
        print(f"\n=== {sym} ===")
        for name, a in res["axes"].items():
            print(f"  {a['label']:<22} {str(a['score']):>4}  {a['verdict'] or 'DATA N/A':<12}"
                  f" [{a['n_used']}/{a['n_possible']}]  {a['drivers']}")
        print("  business:", res["business"], "\n  entry:", res["entry"],
              "\n  coverage:", res["coverage"]["have"], "/", res["coverage"]["total"])
