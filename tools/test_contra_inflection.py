#!/usr/bin/env python3
"""Tests for contra_inflection (B-50). No network: every case is a hand-built
quarterly series, and `screen` takes an injected `derive`."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import contra_inflection as ci

FAILURES: list[str] = []
CR = 1e7


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok   {name}")
    else:
        FAILURES.append(f"{name}{(' -- ' + detail) if detail else ''}")
        print(f"  FAIL {name} {detail}")


def q(period, rev, ebit, pat, *, opm_base=None, pat_yoy=None, rev_yoy=None):
    return {"period": period, "revenue": rev * CR, "ebit": ebit * CR,
            "net_income": pat * CR,
            "opm": round(ebit / rev * 100, 2) if rev else None,
            "net_margin": round(pat / rev * 100, 2) if rev else None,
            "opm_yoy_base": opm_base, "profit_yoy": pat_yoy, "revenue_yoy": rev_yoy}


def occl_like(**over):
    """The OCCL Ltd shape: margin collapse then a sharp, operating-led recovery
    to a new high. Figures are the real ones, in crore."""
    p = {"available": True, "symbol": "T.NS", "cfo_pat_ratio": 1.58,
         "debt_to_equity": 0.21, "interest_coverage": 8.0,
         "quarters": [
             q("2026-06-30", 219.7, 56.3, 40.3, opm_base=15.99, pat_yoy=206.33, rev_yoy=78.5),
             q("2026-03-31", 149.0, 18.2, 19.3),
             q("2025-12-31", 114.2, 9.7, 6.5),
             q("2025-09-30", 119.6, 12.9, 8.7),
             q("2025-06-30", 123.1, 19.7, 13.1),
         ]}
    p.update(over)
    return p


def test_occl_shape_is_inflecting():
    s = ci.extract_signals(occl_like())
    v = ci.classify(s)
    check("OCCL shape -> INFLECTING", v["verdict"] == ci.INFLECTING, v["verdict"])
    check("margin gain measured", s["opm_gain_pp"] == 9.64, str(s["opm_gain_pp"]))
    check("year-ago base used, not median", s["opm_base_source"] == "year_ago_q")
    check("PAT at a window high", s["new_high_pat"] is True)
    check("revenue at a window high", s["new_high_rev"] is True)
    check("streak counted", s["persistence_q"] == 2, str(s["persistence_q"]))


def test_recovery_is_not_a_breakout():
    """The distinction the module exists for: improving, but still below an
    earlier quarter, is mean reversion -- not a rising star."""
    p = occl_like(quarters=[
        q("2026-06-30", 150.0, 22.0, 18.0, opm_base=10.0, pat_yoy=140.0),
        q("2026-03-31", 140.0, 18.0, 14.0),
        q("2025-12-31", 130.0, 12.0, 9.0),
        q("2025-09-30", 200.0, 50.0, 44.0),      # an earlier, much better quarter
    ])
    s = ci.extract_signals(p)
    v = ci.classify(s)
    check("below prior peak -> RECOVERING", v["verdict"] == ci.RECOVERING, v["verdict"])
    check("new_high_pat is False", s["new_high_pat"] is False)
    check("reason names the shape",
          any("recovery toward trend" in r for r in v["reasons"]), str(v["reasons"]))


def test_other_income_jump_is_flagged():
    """PAT triples on flat EBIT -- the classic one-off. Must not read as a turnaround."""
    p = occl_like(quarters=[
        q("2026-06-30", 100.0, 10.0, 45.0, opm_base=9.0, pat_yoy=300.0),
        q("2026-03-31", 100.0, 10.5, 11.0),
        q("2025-12-31", 100.0, 10.2, 10.0),
        q("2025-09-30", 100.0, 10.1, 12.0),
    ])
    s = ci.extract_signals(p)
    v = ci.classify(s)
    check("PAT spike on flat EBIT -> ONE_OFF_SUSPECT",
          v["verdict"] == ci.ONE_OFF_SUSPECT, v["verdict"])
    check("operating_led is False", s["operating_led"] is False)


def test_profit_without_cash_is_flagged():
    v = ci.classify(ci.extract_signals(occl_like(cfo_pat_ratio=0.2)))
    check("weak OCF/PAT -> ONE_OFF_SUSPECT", v["verdict"] == ci.ONE_OFF_SUSPECT,
          v["verdict"])
    check("reason names cash", any("cash" in r for r in v["reasons"]), str(v["reasons"]))


def test_distressed_is_not_contra():
    v = ci.classify(ci.extract_signals(occl_like(debt_to_equity=4.0)))
    check("leverage disqualifies", v["verdict"] == ci.ONE_OFF_SUSPECT, v["verdict"])
    check("reason says distressed",
          any("distressed" in r for r in v["reasons"]), str(v["reasons"]))
    v2 = ci.classify(ci.extract_signals(occl_like(interest_coverage=0.4)))
    check("thin interest cover disqualifies", v2["verdict"] == ci.ONE_OFF_SUSPECT)


def test_one_good_quarter_is_not_a_trend():
    p = occl_like(quarters=[
        q("2026-06-30", 200.0, 50.0, 40.0, opm_base=10.0, pat_yoy=200.0),
        q("2026-03-31", 150.0, 30.0, 20.0),   # already high, so no streak below
        q("2025-12-31", 140.0, 32.0, 22.0),
        q("2025-09-30", 130.0, 20.0, 12.0),
    ])
    s = ci.extract_signals(p)
    check("streak is 1", s["persistence_q"] == 1, str(s["persistence_q"]))
    check("single quarter -> SINGLE_QUARTER",
          ci.classify(s)["verdict"] == ci.SINGLE_QUARTER)


def test_pat_may_outgrow_ebit_without_being_a_one_off():
    """Regression: `operating_led` used to demand EBIT keep PACE with PAT, which
    flags ordinary deleveraging (lower interest) and tax-rate changes as one-offs.
    EBIT +67% against PAT +100% is participation, not an accounting artefact."""
    p = occl_like(quarters=[
        q("2026-06-30", 200.0, 50.0, 40.0, opm_base=10.0, pat_yoy=200.0),
        q("2026-03-31", 150.0, 30.0, 20.0),
        q("2025-12-31", 140.0, 32.0, 22.0),
        q("2025-09-30", 130.0, 20.0, 12.0),
    ])
    s = ci.extract_signals(p)
    check("EBIT participated -> operating_led True", s["operating_led"] is True,
          str(s["operating_led"]))


def test_loss_making_base_cannot_be_inflecting():
    """Regression from the first live run: ITI Limited took the top INFLECTING
    slot on OPM 72.7% vs 3.9% while every prior quarter LOST money and revenue
    fell 40%. pat_yoy, operating_led and cfo_pat_ratio were all None, so each
    guard silently no-opped and silence was read as approval."""
    p = occl_like(cfo_pat_ratio=None, quarters=[
        q("2026-03-31", 60.0, 43.6, 375.1, opm_base=3.93, rev_yoy=-39.98),
        q("2025-12-31", 100.0, 8.0, -25.3),
        q("2025-09-30", 100.0, 5.0, -54.4),
        q("2025-06-30", 100.0, 2.0, -63.6),
    ])
    s = ci.extract_signals(p)
    check("loss in base detected", s["loss_in_base"] is True)
    check("guards could not run", s["operating_led"] is None
          and s["cfo_pat_ratio"] is None)
    v = ci.classify(s)
    check("unevaluated guards -> UNVERIFIED", v["verdict"] == ci.UNVERIFIED, v["verdict"])
    check("reason says unverified, not confirmed",
          any("unverified" in r for r in v["reasons"]), str(v["reasons"]))


def test_margin_gain_on_shrinking_revenue_is_not_a_rising_star():
    """Bayer CropScience shape: margin up 4.4pp, PAT at a window high, but revenue
    DOWN. Cost-cutting or mix, and it gets its own label rather than sharing
    INFLECTING with a business that is actually growing."""
    p = occl_like(quarters=[
        q("2026-06-30", 90.0, 19.9, 14.0, opm_base=17.75, pat_yoy=15.4, rev_yoy=-4.16),
        q("2026-03-31", 95.0, 18.0, 12.0),
        q("2025-12-31", 100.0, 17.0, 11.0),
        q("2025-09-30", 100.0, 16.0, 10.0),
    ])
    v = ci.classify(ci.extract_signals(p))
    check("shrinking top line -> MARGIN_LED", v["verdict"] == ci.MARGIN_LED, v["verdict"])
    check("reason names it margin not growth",
          any("margin, not growth" in r for r in v["reasons"]), str(v["reasons"]))


def test_flat_business_is_no_inflection():
    p = occl_like(quarters=[
        q("2026-06-30", 100.0, 12.0, 8.0, opm_base=12.1, pat_yoy=2.0),
        q("2026-03-31", 100.0, 12.1, 8.0),
        q("2025-12-31", 100.0, 12.0, 8.0),
        q("2025-09-30", 100.0, 12.2, 8.0),
    ])
    check("flat -> NO_INFLECTION",
          ci.classify(ci.extract_signals(p))["verdict"] == ci.NO_INFLECTION)


def test_short_series_is_insufficient_not_a_verdict():
    p = occl_like(quarters=[
        q("2026-06-30", 200.0, 50.0, 40.0, opm_base=10.0, pat_yoy=200.0),
        q("2026-03-31", 150.0, 20.0, 12.0),
    ])
    v = ci.classify(ci.extract_signals(p))
    check("2 quarters -> INSUFFICIENT_DATA", v["verdict"] == ci.INSUFFICIENT, v["verdict"])
    check("no quarters at all -> INSUFFICIENT",
          ci.classify(ci.extract_signals({"quarters": []}))["verdict"] == ci.INSUFFICIENT)


def test_median_fallback_is_reported_not_hidden():
    p = occl_like()
    p["quarters"][0]["opm_yoy_base"] = None        # no year-ago match
    s = ci.extract_signals(p)
    check("falls back to prior median", s["opm_base_source"] == "prior_median")
    # median of the four prior OPMs (12.21, 8.49, 10.79, 16.00) = 11.5
    check("base is the median of priors", s["opm_base"] == 11.5, str(s["opm_base"]))


def test_screen_filters_and_tallies():
    data = {
        "IN.NS":  occl_like(symbol="IN.NS"),
        "OFF.NS": occl_like(symbol="OFF.NS", cfo_pat_ratio=0.1),
    }
    res = ci.screen(symbols=list(data), derive=lambda s: data[s], max_workers=2)
    check("only wanted verdicts returned",
          [r["symbol"] for r in res["rows"]] == ["IN.NS"], str(res["rows"]))
    check("tally counts both", res["tally"][ci.INFLECTING] == 1
          and res["tally"][ci.ONE_OFF_SUSPECT] == 1, str(res["tally"]))
    check("params recorded with the run", res["params"]["min_persistence_q"] == 2)


def main() -> int:
    for fn in sorted([v for k, v in globals().items() if k.startswith("test_")],
                     key=lambda f: f.__code__.co_firstlineno):
        print(f"\n{fn.__name__}:")
        fn()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S):")
        for f in FAILURES:
            print("  -", f)
        return 1
    print("All contra_inflection tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
