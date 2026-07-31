"""FR-5 — bull / base / bear business-size scenarios.

This is arithmetic, not a forecast, and the module is built so the UI can prove
that to the reader: every scenario carries the multiplier that produced it as a
printable string, so the number is checkable by hand rather than taken on trust.

What it is NOT
--------------
It is **not** [projection.py](projection.py). That module projects **price**,
from Elliott-Wave Fibonacci targets and VCP/harmonic measured moves, and it
answers "where might this trade". This one projects **the size of the business**
— revenue and net profit — from the company's own filed history, and answers
"how big might this company be". They are different objects with different
units and different failure modes, and the UI must never stack them in a way
that implies one confirms the other.

Where the bands come from
-------------------------
Rather than inventing a ±X% spread, the scenarios are anchored to what this
company has actually done:

* **Base** — the observed 3-year revenue CAGR, at the latest net margin.
* **Bull** — the best single year of revenue growth in the available history, at
  the best margin observed.
* **Bear** — the worst single year, at the worst margin observed. This can be
  negative, and is allowed to be.

That makes the spread a statement about the company's own volatility. The cost
is that four or five annual columns give only three growth observations, so the
band is wide and noisy — which the UI says out loud rather than hiding behind a
smooth-looking chart.

Net profit, not NOPAT
---------------------
The source mockup shows NOPAT bars. NOPAT needs EBIT and an effective tax rate
separated, and this stack has neither cleanly (tax provision is not exposed by
the FR-1 layer, and net_income ÷ EBIT conflates interest). So the projection
uses **net margin**, which is post-tax by definition, and the output is labelled
**net profit** rather than NOPAT. A documented deviation, not a silent one.
"""

from __future__ import annotations

from typing import Any

#: Years projected forward. Three, because the base rate is a 3-year CAGR and
#: extrapolating a 3-year rate further than it is long invites false precision.
HORIZON_YEARS = 3

#: Minimum annual observations. Two revenue points give one growth observation,
#: which cannot produce a bull/bear spread at all.
MIN_ANNUAL = 3

#: Compound-growth sanity cap, same discipline as projection.py's MAX_MOVE_PCT.
#: A company that grew 80% once will not do it three years running; without a
#: cap the bull bar reaches 5.8x and the chart becomes a cartoon. When the cap
#: binds the UI says so and prints the uncapped figure.
MAX_SUSTAINED_GROWTH_PCT = 40.0


def _f(v: Any) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if x != x else x


def _fy_label(period: str, years_ahead: int) -> str:
    """`2026-03-31` + 3 -> `FY29`."""
    try:
        yr = int(str(period)[:4]) + years_ahead
        return f"FY{yr % 100:02d}"
    except Exception:
        return f"+{years_ahead}y"


def _cr(v: float | None) -> str:
    return "—" if v is None else f"₹{v/1e7:,.0f} Cr"


def build(deep: dict | None) -> dict[str, Any] | None:
    """Scenario set, or None when there is not enough filed history."""
    d = deep or {}
    annual = [a for a in (d.get("annual") or []) if _f(a.get("revenue")) is not None]
    if len(annual) < MIN_ANNUAL:
        return None

    latest_rev = _f(annual[0]["revenue"])
    if latest_rev is None or latest_rev <= 0:
        return None

    # Observed year-over-year growth rates, newest first. `revenue_yoy` is
    # already gap-checked by the data layer, so a non-contiguous year is absent
    # rather than wrong.
    growths = [_f(a.get("revenue_yoy")) for a in annual]
    growths = [g for g in growths if g is not None]
    margins = [_f(a.get("net_margin")) for a in annual]
    margins = [m for m in margins if m is not None]
    if len(growths) < 2 or not margins:
        return None

    base_growth = _f(d.get("revenue_cagr_3y"))
    if base_growth is None:
        base_growth = sum(growths) / len(growths)
    base_margin = margins[0]
    bull_growth_raw, bear_growth = max(growths), min(growths)
    bull_margin, bear_margin = max(margins), min(margins)

    # The cap applies to EVERY growth rate, not just the bull. Capping only the
    # bull produced a Bull bar BELOW the Base bar on a fast grower (SWIGGY: 3Y
    # CAGR 41% vs a bull capped to 40%) — if sustaining 40%+ for three years is
    # implausible enough to cap, it is implausible in the base case too.
    capped = max(bull_growth_raw, base_growth) > MAX_SUSTAINED_GROWTH_PCT
    base_growth_raw = base_growth
    bull_growth = min(bull_growth_raw, MAX_SUSTAINED_GROWTH_PCT)
    base_growth = min(base_growth, MAX_SUSTAINED_GROWTH_PCT)

    # Enforce bull >= base >= bear by construction. A "bull case" that lands
    # below the base case is not a scenario set, it is a bug the reader has to
    # decode.
    bull_growth = max(bull_growth, base_growth)
    bear_growth = min(bear_growth, base_growth)
    bull_margin = max(bull_margin, base_margin)
    bear_margin = min(bear_margin, base_margin)

    # An exceptional year poisons the max-margin pick: ITC's best filed margin
    # is 46.5%, from the hotels-demerger year, against a ~27% norm. Projecting
    # that as a sustainable margin would treat a one-off gain as the bull path.
    # The arithmetic is left alone and the outlier is disclosed instead.
    med_margin = sorted(margins)[len(margins) // 2]
    outlier_margin = None
    if med_margin > 0 and bull_margin > med_margin * 1.5:
        period = next((a["period"] for a in annual
                       if _f(a.get("net_margin")) == bull_margin), None)
        outlier_margin = {
            "value": bull_margin, "median": med_margin, "period": period,
            "note": (f"The {bull_margin:.1f}% bull margin comes from "
                     f"{period or 'a single year'}, well above the {med_margin:.1f}% "
                     f"median of the filed years — most likely a one-off gain rather "
                     f"than a sustainable level. Read the bull profit bar with that "
                     f"in mind."),
        }

    n = HORIZON_YEARS
    target_label = _fy_label(annual[0]["period"], n)

    def project(growth_pct: float, margin_pct: float) -> tuple[float, float]:
        rev = latest_rev * ((1 + growth_pct / 100) ** n)
        return rev, rev * margin_pct / 100

    rows = []
    for name, g, m, how in (
        ("Bull", bull_growth, bull_margin,
         f"best observed year ({bull_growth_raw:+.1f}%)"
         + (f", capped to {MAX_SUSTAINED_GROWTH_PCT:.0f}%" if capped else "")
         + f" at the best observed margin ({bull_margin:.1f}%)"),
        ("Base", base_growth, base_margin,
         f"3-year revenue CAGR ({base_growth_raw:+.1f}%"
         + (f", capped to {MAX_SUSTAINED_GROWTH_PCT:.0f}%"
            if base_growth_raw > MAX_SUSTAINED_GROWTH_PCT else "")
         + f") at the latest margin ({base_margin:.1f}%)"),
        ("Bear", bear_growth, bear_margin,
         f"worst observed year ({bear_growth:+.1f}%) at the worst observed margin "
         f"({bear_margin:.1f}%)"),
    ):
        rev, profit = project(g, m)
        rows.append({
            "name": name,
            "growth_pct": round(g, 2),
            "margin_pct": round(m, 2),
            "revenue": rev,
            "profit": profit,
            "how": how,
            # The arithmetic, printable, so a reader can redo it by hand.
            "derivation": (f"{_cr(latest_rev)} × (1 {'+' if g >= 0 else '−'} "
                           f"{abs(g):.1f}%)^{n} = {_cr(rev)}; "
                           f"× {m:.1f}% margin = {_cr(profit)}"),
        })

    return {
        "horizon_years": n,
        "base_period": annual[0]["period"],
        "target_label": target_label,
        "latest_revenue": latest_rev,
        "latest_margin": base_margin,
        "scenarios": rows,
        "growth_observations": len(growths),
        "margin_observations": len(margins),
        "bull_capped": capped,
        "bull_growth_raw": bull_growth_raw,
        "growth_cap_pct": MAX_SUSTAINED_GROWTH_PCT,
        "outlier_margin": outlier_margin,
        "driver": _largest_driver(latest_rev, base_growth, bull_growth, bear_growth,
                                  base_margin, bull_margin, bear_margin, n),
    }


def _largest_driver(latest_rev: float, base_g: float, bull_g: float, bear_g: float,
                    base_m: float, bull_m: float, bear_m: float,
                    n: int) -> dict[str, Any]:
    """Which input actually moves the outcome — growth or margin.

    Each is varied across its own bull-to-bear range while the other is held at
    base, and the resulting profit spread is compared. The bigger spread is the
    thing worth watching, and it comes with a numeric threshold rather than an
    adjective.
    """
    def profit(g: float, m: float) -> float:
        return latest_rev * ((1 + g / 100) ** n) * m / 100

    growth_spread = profit(bull_g, base_m) - profit(bear_g, base_m)
    margin_spread = profit(base_g, bull_m) - profit(base_g, bear_m)

    if growth_spread >= margin_spread:
        return {
            "which": "revenue growth",
            "spread": growth_spread,
            "detail": (f"Revenue growth swings projected profit by {_cr(growth_spread)} "
                       f"across its own observed range, against {_cr(margin_spread)} "
                       f"for margin. Growth is the variable that decides this."),
            "threshold": (f"Track whether annual revenue growth holds above "
                          f"{base_g:.1f}% — the base path assumes it does. Sustained "
                          f"growth below that walks toward the bear bar."),
        }
    return {
        "which": "net margin",
        "spread": margin_spread,
        "detail": (f"Margin swings projected profit by {_cr(margin_spread)} across its "
                   f"own observed range, against {_cr(growth_spread)} for revenue "
                   f"growth. Margin is the variable that decides this."),
        "threshold": (f"Track whether net margin holds above {base_m:.1f}%. It has "
                      f"ranged {bear_m:.1f}%–{bull_m:.1f}% over the filed years, and "
                      f"that range moves the outcome more than growth does."),
    }


if __name__ == "__main__":   # py -3 tools/scenarios.py ITC TITAN
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import fundamentals_deep as fdeep

    for s in (sys.argv[1:] or ["ITC"]):
        res = build(fdeep.derive_fundamentals(s))
        print(f"\n=== {s} ===")
        if not res:
            print("  not enough filed history for scenarios")
            continue
        print(f"  base {res['base_period']} -> {res['target_label']} "
              f"({res['horizon_years']}y), {res['growth_observations']} growth obs")
        for r in res["scenarios"]:
            print(f"  {r['name']:<5} rev {_cr(r['revenue']):>14}  profit {_cr(r['profit']):>13}"
                  f"  | {r['how']}")
            print(f"        {r['derivation']}")
        print("  driver:", res["driver"]["which"], "|", res["driver"]["threshold"])
