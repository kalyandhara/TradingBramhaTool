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

Calibration is measured, not asserted (2026-09-04)
--------------------------------------------------
Every continuous input is scored against the measured NSE distribution of that
metric — `calibrate_bands.py` samples the NIFTY-500 and `_CURVES` holds the
resulting percentile anchors. A score therefore states a company's standing in
this market: 55 is the median NSE name, ~95 is the top decile.

It used to be hand-set bands, and they were wrong in a way that only showed up
when ten companies were put in a column (FP-1's peer table): the median Indian
company was scoring 100 on leverage, 80 on debtor days and 90+ on growth. Wrong
bands are how a rating loses trust — the M1-weights lesson — and intuition about
"good ROCE" or "high debt" turns out to be imported from a different market.

One metric resists calibration because yfinance does not carry it for most NSE
names — PEG, 11.5% coverage — and keeps an absolute, externally argued band with
the reasoning beside it. ROE was the other, until it was switched to the filed
statements (`fundamentals_deep`) and went from 13.5% to 100% coverage.

Change a curve here, once, and every consumer moves together.

Missing data never scores. An axis with no resolvable input returns
`score=None` and renders DATA N/A; it is never given a neutral 50, which would
read as "average" when it means "unknown".
"""

from __future__ import annotations

from typing import Any, Sequence

# ──────────────────────────────────────────────────────────────────────────────
# Scoring curves, measured — not bands, guessed
# ──────────────────────────────────────────────────────────────────────────────
# Every continuous input is scored against the MEASURED distribution of that
# metric across NSE, via `calibrate_bands.py` (200-name stride sample of the
# NIFTY-500, raw values in cache/band_calibration.json, 2026-09-04). Each curve
# maps that metric's own percentiles onto the shared verdict scale:
#
#     p10 -> 20    p25 -> 35    p50 -> 55    p75 -> 80    p90 -> 95
#
# interpolated in between and clamped outside. One shared shape on purpose: an
# axis has to mean "top decile = ~95, median = 55" on all six, or the six numbers
# on the donut strip stop being comparable to each other, which is the entire
# point of having one scorer.
#
# WHY THIS REPLACED HAND-SET BANDS. The FP-1 peer table showed nearly every peer
# scoring Growth 90-100. Measuring it showed the Growth ceiling (25% CAGR) was
# the 81st percentile of revenue CAGR and only the 65th of quarterly YoY, so a
# third of the market scored full marks. Calibrating the other five axes the same
# way found the same fault, in places worse:
#
#     metric          old band                 measured NSE median   old score at median
#     debt_to_equity  0.25x -> 100             0.21x                 100  (saturated)
#     debtor_days     30d -> 100, 60d -> 80    47.5d                  80  (saturated)
#     margin_cv       0.15 -> 100, 0.30 -> 70  0.19                   70
#     pe              15 -> 100, 40 -> 55      35.5x                  55  (about right)
#     roce_trend      0pp -> 70                -0.69pp                45
#     roe             12% -> 55, 18% -> 80     13.5%                  55  (about right)
#
# Two of Health's three inputs were handing the median Indian company a perfect
# or near-perfect score; only the axis's `min_drag` aggregation was hiding it.
#
# THINGS THE MEASUREMENT ITSELF ESTABLISHED, worth keeping in view:
#   - NSE is expensive: median P/E 35.7x, p90 92.5x. US-calibrated bands would
#     mark essentially the whole market overvalued.
#   - NSE is unlevered: median D/E 0.21x, and a quarter of the market under
#     0.06x. Leverage is a genuine outlier signal here, not a normal condition.
#   - Median NSE ROE is 13.5% and median ROCE 14.8%. The old ROE band happened to
#     be close (12% -> 55, 18% -> 80 against a measured p50 of 13.5 and p75 of
#     18.1), so this one was right by intuition — worth recording, because it is
#     the only band that was.
#   - ROCE is FALLING for most of the market: median trend -0.69pp YoY. A flat
#     ROCE is therefore an above-median outcome, which the old 0pp -> 70 band had
#     roughly right by accident.
#   - A quarter of listed India runs NEGATIVE free-cash-flow margin (p25 -5.6%).
#
# Re-run calibrate_bands.py and move these numbers when the market moves. They
# are a snapshot of a distribution, not a law.
_CURVES = {
    # valuation — lower is better, so the curve runs downhill
    "pe":              ((11.52, 95), (21.13, 80), (35.87, 55), (56.55, 35), (92.66, 20)),
    "pb":              ((1.59, 95), (2.39, 80), (4.49, 55), (8.85, 35), (15.11, 20)),
    # growth
    "revenue_cagr_3y": ((0.56, 20), (6.39, 35), (12.61, 55), (19.49, 80), (29.81, 95)),
    "profit_cagr_3y":  ((-5.9, 20), (4.72, 35), (18.71, 55), (32.16, 80), (55.5, 95)),
    "revenue_yoy":     ((-5.56, 20), (8.85, 35), (16.48, 55), (26.63, 80), (44.07, 95)),
    # health — lower is better
    "debt_to_equity":  ((0.01, 95), (0.06, 80), (0.21, 55), (0.74, 35), (1.51, 20)),
    "debtor_days":     ((8.7, 95), (20.4, 80), (47.5, 55), (79.6, 35), (137.3, 20)),
    # returns
    "roe":             ((4.58, 20), (9.62, 35), (13.47, 55), (18.11, 80), (27.88, 95)),
    "roce":            ((4.11, 20), (9.3, 35), (14.8, 55), (21.77, 80), (35.64, 95)),
    "npm":             ((3.13, 20), (6.61, 35), (12.56, 55), (23.72, 80), (38.15, 95)),
    # capital allocation
    "fcf_margin":      ((-41.38, 20), (-5.57, 35), (5.6, 55), (13.73, 80), (29.26, 95)),
    "roce_trend":      ((-6.08, 20), (-3.03, 35), (-0.69, 55), (1.38, 80), (6.48, 95)),
    # earnings consistency — lower is better
    "margin_cv":       ((0.05, 95), (0.09, 80), (0.19, 55), (0.42, 35), (0.89, 20)),
}

# ──────────────────────────────────────────────────────────────────────────────
# The ONE metric that still cannot be calibrated
# ──────────────────────────────────────────────────────────────────────────────
# PEG resolves for 23 of 200 names (11.5%) — yfinance's `.info` simply does not
# carry it for NSE. That is a finding about our data, not about the market, so it
# keeps an ABSOLUTE, externally-argued band: a curve fitted to the 11% that
# resolved would describe whichever names yfinance happens to populate. Lynch's
# PEG < 1 anchor is a real external reference and stands on its own. Valuation
# therefore runs on P/E + P/B alone for ~88% of names, which the coverage count
# already reports honestly.
#
# ROE used to be the second such metric (27 of 200 from `.info`). It is now
# derived from the filed statements instead and resolves for 200 of 200, so it
# is calibrated above. See `raw_metrics` for the preference order.
_PEG_BANDS = ((1.0, 100), (1.5, 80), (2.5, 55), (4.0, 30))   # Lynch's PEG<1 anchor

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
    """Score a metric off its measured NSE distribution (`_CURVES`).

    Piecewise-linear between the percentile anchors, clamped past either end.
    Curves run uphill for higher-is-better metrics and downhill for
    lower-is-better ones (P/E, D/E, debtor days, margin CV); the direction is
    read off the anchors themselves rather than passed in, so a curve and its
    direction cannot disagree.

    Clamping past the ends is deliberate. A 400% CAGR off a tiny base is not four
    times as impressive as 100%, a P/E of 900 is not meaningfully worse than 300,
    and the sample carries no evidence to separate either pair. Beyond the top
    anchor everything is 100 (or 10 at the bottom): past the 90th percentile the
    ranking has stopped being informative.

    `None` in, `None` out — a missing input is never scored (see the docstring).
    """
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v != v:                      # NaN
        return None

    pts = _CURVES[metric]
    ascending = pts[-1][1] >= pts[0][1]        # does a bigger value score better?
    if v <= pts[0][0]:
        return 10 if ascending else 100
    if v >= pts[-1][0]:
        return 100 if ascending else 10
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if v <= x1:
            return y1 if x1 == x0 else round(y0 + (y1 - y0) * (v - x0) / (x1 - x0))
    return 100 if ascending else 10


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
# Raw metric extraction — ONE path, used by the scorers and the calibrator
# ──────────────────────────────────────────────────────────────────────────────
def raw_metrics(fundamentals: dict | None, deep: dict | None) -> dict[str, float | None]:
    """Every continuous, curve-scored input, before any scoring.

    This is public and shared on purpose. `calibrate_bands.py` measures the NSE
    distribution of exactly these values to set the curves below, so if it
    extracted them itself the calibration would slowly stop describing what the
    scorer actually reads — the bands would be tuned for a metric nobody scores.
    One extractor means the measurement and the scoring can never drift apart.

    Only continuous metrics live here. The categorical inputs (FCF-negative
    streak, profitable-years and growth-years ratios) are deliberately absent:
    they are counts with a natural 0-100 reading, and a percentile curve over
    "3 of 4 years" would invent precision that the underlying tally does not have.
    """
    f, d = fundamentals or {}, deep or {}

    # Leverage and ROE: PREFER THE FILED STATEMENTS, fall back to `.info`.
    #
    # Both were already being derived by `fundamentals_deep` from the balance
    # sheet and simply not read here — the scorer took yfinance's `.info` figure,
    # which is absent for ~87% of NSE names. That gap was invisible until the
    # calibrator counted it (ROE resolved for 27 of 200), and it meant the
    # Returns axis was running on two of its three inputs for most of the market.
    #
    # Unit trap worth stating: `.info`'s debtToEquity is a PERCENT (195.0) while
    # the derived figure is already a RATIO (1.95). Mixing them silently would
    # have scaled every leverage score by 100.
    d2e_ratio = _f(d.get("debt_to_equity"))
    d2e_pct = _f(f.get("debt_to_equity"))       # yfinance reports this as a %
    annual = d.get("annual") or []
    revenue = _f(annual[0].get("revenue")) if annual else None
    fcf = _f(d.get("fcf"))
    roce, roce_prev = _f(d.get("roce")), _f(d.get("roce_prev"))

    quarters = d.get("quarters") or []
    revg = next((_f(q.get("revenue_yoy")) for q in quarters
                 if q.get("revenue_yoy") is not None), None)
    if revg is None:
        revg = _f(f.get("revenue_growth"))

    margins = [m for m in (_f(a.get("net_margin")) for a in annual) if m is not None]

    return {
        # valuation (lower is better)
        "pe": _f(f.get("pe")), "pb": _f(f.get("pb")), "peg": _f(f.get("peg")),
        # growth (higher is better)
        "revenue_cagr_3y": _f(d.get("revenue_cagr_3y")),
        "profit_cagr_3y": _f(d.get("profit_cagr_3y")),
        "revenue_yoy": revg,
        # health (lower is better)
        "debt_to_equity": (d2e_ratio if d2e_ratio is not None
                           else (None if d2e_pct is None else d2e_pct / 100.0)),
        "debtor_days": _f(d.get("debtor_days")),
        # returns (higher is better)
        "roe": _f(d.get("roe")) if d.get("roe") is not None else _f(f.get("roe")),
        "roce": roce, "npm": _f(f.get("npm")),
        # capital allocation (higher is better)
        "fcf_margin": (round(fcf / revenue * 100, 2)
                       if (fcf is not None and revenue not in (None, 0) and revenue > 0)
                       else None),
        "roce_trend": None if (roce is None or roce_prev is None) else round(roce - roce_prev, 2),
        # earnings consistency (lower is better)
        "margin_cv": _cv(margins),
    }


# ──────────────────────────────────────────────────────────────────────────────
# The six axes
# ──────────────────────────────────────────────────────────────────────────────
def _score_valuation(f: dict, d: dict) -> dict:
    m = raw_metrics(f, d)
    pe, pb, peg = m["pe"], m["pb"], m["peg"]

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
        ("pe",  _curve(pe, "pe"), f"P/E {pe:.1f}×" if pe else ""),
        ("pb",  _curve(pb, "pb"), f"P/B {pb:.1f}×" if pb else ""),
        ("peg", _band(peg, _PEG_BANDS, True), f"PEG {peg:.2f}×" if peg else ""),
    ])


def _score_growth(f: dict, d: dict) -> dict:
    m = raw_metrics(f, d)
    rev3, pro3, revg = m["revenue_cagr_3y"], m["profit_cagr_3y"], m["revenue_yoy"]

    # `raw_metrics` prefers OUR date-matched quarterly YoY over yfinance's
    # `revenueGrowth`; the two disagree materially (TITAN: 48% ours vs 80.5%
    # theirs) and ours is derived from the statements in the open. This only
    # re-derives which of the two won, for the driver line.
    quarters = d.get("quarters") or []
    yoy_src = ("latest Q" if any(q.get("revenue_yoy") is not None for q in quarters)
               else "yfinance")

    return _axis("growth", [
        ("revenue_cagr_3y", _curve(rev3, "revenue_cagr_3y"),
         f"Rev CAGR 3Y {rev3:.1f}%" if rev3 is not None else ""),
        ("profit_cagr_3y", _curve(pro3, "profit_cagr_3y"),
         f"Profit CAGR 3Y {pro3:.1f}%" if pro3 is not None else ""),
        ("revenue_yoy", _curve(revg, "revenue_yoy"),
         f"Rev YoY {revg:.1f}% ({yoy_src})" if revg is not None else ""),
    ])


def _score_health(f: dict, d: dict) -> dict:
    m = raw_metrics(f, d)
    d2e, dbd = m["debt_to_equity"], m["debtor_days"]
    streak = d.get("fcf_negative_streak")
    fcf_score = None
    fcf_text = ""
    if d.get("fcf") is not None or streak is not None:
        streak = int(streak or 0)
        fcf_score = 100 if streak == 0 else (50 if streak == 1 else _FLOOR)
        fcf_text = ("FCF positive" if streak == 0
                    else f"FCF negative {streak}y")
    return _axis("health", [
        ("debt_to_equity", _curve(d2e, "debt_to_equity"),
         f"D/E {d2e:.2f}×" if d2e is not None else ""),
        ("fcf", fcf_score, fcf_text),
        ("debtor_days", _curve(dbd, "debtor_days"),
         f"Debtor {dbd:.0f}d" if dbd is not None else ""),
    ], agg="min_drag")


def _score_returns(f: dict, d: dict) -> dict:
    m = raw_metrics(f, d)
    roe, roce, npm = m["roe"], m["roce"], m["npm"]
    return _axis("returns", [
        ("roe",  _curve(roe, "roe"), f"ROE {roe:.1f}%" if roe is not None else ""),
        ("roce", _curve(roce, "roce"), f"ROCE {roce:.1f}%" if roce is not None else ""),
        ("npm",  _curve(npm, "npm"), f"Net margin {npm:.1f}%" if npm is not None else ""),
    ])


def _score_capital_allocation(f: dict, d: dict) -> dict:
    """Newly computable: FR-1's cash-flow statements are what unlocked this axis.

    Two questions: does the business convert revenue into free cash, and is the
    return on the capital it employs rising or falling?
    """
    m = raw_metrics(f, d)
    fcf_margin, trend = m["fcf_margin"], m["roce_trend"]
    return _axis("capital_allocation", [
        ("fcf_margin", _curve(fcf_margin, "fcf_margin"),
         f"FCF margin {fcf_margin:.1f}%" if fcf_margin is not None else ""),
        ("roce_trend", _curve(trend, "roce_trend"),
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
    cv = raw_metrics(f, d)["margin_cv"]

    return _axis("earnings_consistency", [
        ("positive_years", round(pos_ratio * 100),
         f"{sum(1 for p in profits if p > 0)}/{len(profits)} profitable years"),
        ("growth_years", None if grow_ratio is None else round(grow_ratio * 100),
         "" if grow_ratio is None
         else f"{sum(1 for n, o in pairs if o > 0 and n > o)}/{len(pairs)} growth years"),
        ("margin_stability", _curve(cv, "margin_cv"),
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
