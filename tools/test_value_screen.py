#!/usr/bin/env python3
"""Tests for value_screen (B-49). No network: `screen` takes an injected
`derive`, so every case here is deterministic."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import value_screen as vs

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok   {name}")
    else:
        FAILURES.append(f"{name}{(' -- ' + detail) if detail else ''}")
        print(f"  FAIL {name} {detail}")


def payload(**kw):
    """A payload that passes every default criterion; override to break one."""
    base = dict(symbol="TEST.NS", available=True, long_name="Test Ltd",
                pe=13.6, ps=1.81, opm=22.0, roe=15.8, roce=19.6,
                debt_to_equity=0.10, revenue_cagr_3y=14.0,
                profit_cagr_3y=12.0, dilution_pct=0.0,
                interest_coverage=10.7, price=775.0, market_cap=5e10,
                sector="Consumer Cyclical", ps_source="yf")
    base.update(kw)
    return base


def test_card_passes_every_criterion():
    """The AGI Greenpac card's own figures must clear the default screen --
    a screen that rejects the example it was built from is misconfigured."""
    r = vs.evaluate(payload(), vs.Thresholds())
    check("card passes all", r["fails"] == 0 and r["unknowns"] == 0,
          f"passes={r['passes']} fails={r['fails']} unk={r['unknowns']}")
    check("all 10 criteria applied", r["applied"] == 10, str(r["applied"]))


def test_missing_value_is_unknown_not_fail():
    """The bug this screen was built around: yfinance returns
    returnOnEquity=None for AGI Greenpac. UNKNOWN must never count as FAIL."""
    r = vs.evaluate(payload(roe=None), vs.Thresholds())
    check("missing ROE -> UNKNOWN", r["verdicts"]["ROE %"]["state"] == vs.UNKNOWN)
    check("missing ROE not a fail", r["fails"] == 0, f"fails={r['fails']}")
    check("unknown counted once", r["unknowns"] == 1, f"unk={r['unknowns']}")
    check("still qualifies", vs.qualifies(r), "an under-reported name must survive")


def test_non_numeric_is_unknown():
    r = vs.evaluate(payload(pe="n/a"), vs.Thresholds())
    check("non-numeric -> UNKNOWN", r["verdicts"]["P/E"]["state"] == vs.UNKNOWN)


def test_each_bound_bites():
    """Every criterion must actually reject when crossed -- otherwise a bound is
    wired to the wrong comparison and the screen quietly lets everything through."""
    breaks = {
        "P/E": dict(pe=99.0), "P/S": dict(ps=99.0), "OPM %": dict(opm=1.0),
        "ROE %": dict(roe=1.0), "ROCE %": dict(roce=1.0),
        "D/E": dict(debt_to_equity=5.0),
        "Rev CAGR 3Y %": dict(revenue_cagr_3y=-5.0),
        "Profit CAGR 3Y %": dict(profit_cagr_3y=-5.0),
        "Dilution %": dict(dilution_pct=50.0),
        "Interest cover": dict(interest_coverage=0.5),
    }
    for label, kw in breaks.items():
        r = vs.evaluate(payload(**kw), vs.Thresholds())
        check(f"bound bites: {label}",
              r["verdicts"][label]["state"] == vs.FAIL and r["fails"] == 1,
              str(r["verdicts"][label]))
        check(f"rejected: {label}", not vs.qualifies(r))


def test_threshold_none_disables_criterion():
    th = vs.Thresholds(max_pe=None)
    r = vs.evaluate(payload(pe=999.0), th)
    check("None bound omits criterion", "P/E" not in r["verdicts"])
    check("applied drops to 9", r["applied"] == 9, str(r["applied"]))


def test_unknown_guard_is_data_quality_not_judgement():
    """Too many missing figures means NOT SCREENED, so the name is held back
    even though it has zero fails."""
    r = vs.evaluate(payload(roe=None, roce=None, opm=None, ps=None), vs.Thresholds())
    check("4 unknowns, 0 fails", r["fails"] == 0 and r["unknowns"] == 4)
    check("held back by unknown guard", not vs.qualifies(r, max_unknowns=3))
    check("admitted when guard relaxed", vs.qualifies(r, max_unknowns=4))


def test_screen_end_to_end_with_injected_derive():
    data = {
        "GOOD.NS": payload(symbol="GOOD.NS", roce=25.0),
        "ALSO.NS": payload(symbol="ALSO.NS", roce=18.0),
        "RICH.NS": payload(symbol="RICH.NS", pe=88.0),          # fails P/E
        "THIN.NS": payload(symbol="THIN.NS", roe=None, roce=None,
                           opm=None, ps=None),                   # too unknown
        "GONE.NS": {"symbol": "GONE.NS", "available": False},    # no statements
    }
    res = vs.screen(symbols=list(data), derive=lambda s: data[s],
                    with_governance=False, max_workers=2)
    got = [r["symbol"] for r in res["rows"]]
    check("only qualifying names returned", got == ["GOOD.NS", "ALSO.NS"], str(got))
    check("unavailable name not derived", res["derived"] == 4, str(res["derived"]))
    check("scanned counts every input", res["scanned"] == 5, str(res["scanned"]))
    check("rejected tallies the rest", res["rejected"] == 2, str(res["rejected"]))
    check("ROCE breaks the tie", got[0] == "GOOD.NS")
    check("thresholds recorded with the run",
          res["thresholds"]["min_roce"] == 15.0)


def test_screen_survives_a_raising_symbol():
    """One broken symbol must not kill a 500-name run."""
    def _derive(s):
        if s == "BOOM.NS":
            raise RuntimeError("yfinance blew up")
        return payload(symbol=s)
    res = vs.screen(symbols=["BOOM.NS", "OK.NS"], derive=_derive,
                    with_governance=False, max_workers=2)
    check("raising symbol skipped", [r["symbol"] for r in res["rows"]] == ["OK.NS"])
    check("scanned still counts it", res["scanned"] == 2)


def test_ranking_prefers_fewer_unknowns():
    data = {
        "FULL.NS": payload(symbol="FULL.NS", roce=16.0),
        "PART.NS": payload(symbol="PART.NS", roce=40.0, roe=None),
    }
    res = vs.screen(symbols=list(data), derive=lambda s: data[s],
                    with_governance=False, max_workers=2)
    got = [r["symbol"] for r in res["rows"]]
    check("more passes outranks higher ROCE", got == ["FULL.NS", "PART.NS"], str(got))


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
    print("All value_screen tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
