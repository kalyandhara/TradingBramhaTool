#!/usr/bin/env python3
"""Tests for volume_anomaly (B-51). Offline: every network dependency of `scan`
is injectable, and the fixtures are the real 2026-08-28 rows."""
import sys, os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
import volume_anomaly as va

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok   {name}")
    else:
        FAILURES.append(f"{name}{(' -- ' + detail) if detail else ''}")
        print(f"  FAIL {name} {detail}")


def deal(sym, client, side, qty):
    return {"Symbol": sym, "Client Name": client, "Buy/Sell": side,
            "Quantity Traded": qty}


# ── churn detection ───────────────────────────────────────────────────────────
def test_matched_two_way_flow_is_churn():
    """The real MASTEK rows: Microcurves bought and sold the SAME 264,122."""
    d = [deal("MASTEK", "MICROCURVES TRADING PRIVATE LIMITED", "BUY", 264122),
         deal("MASTEK", "MICROCURVES TRADING PRIVATE LIMITED", "SELL", 264122)]
    c = va.detect_prop_churn(d, day_volume=5449060)
    check("churn quantity found", c["churn_qty"] == 264122, str(c["churn_qty"]))
    # churn_share is rounded to 4dp, so compare at that precision
    check("counted twice against volume",
          abs(c["churn_share"] - (264122 * 2 / 5449060)) < 1e-4, str(c["churn_share"]))
    check("share is a minority of volume, not the whole story",
          0.09 < c["churn_share"] < 0.10, str(c["churn_share"]))
    check("churner named", "MICROCURVES TRADING PRIVATE LIMITED" in c["churners"])


def test_near_match_still_counts():
    """OMAXE: Junomoneta bought 1,084,016 and sold 1,086,607 -- a desk may end the
    day slightly long and it is still a round-trip."""
    d = [deal("OMAXE", "JUNOMONETA FINSOL PRIVATE LIMITED", "BUY", 1084016),
         deal("OMAXE", "JUNOMONETA FINSOL PRIVATE LIMITED", "SELL", 1086607)]
    c = va.detect_prop_churn(d, day_volume=24953289)
    check("near-matched qty counts", c["churn_qty"] == 1084016, str(c["churn_qty"]))


def test_one_sided_is_not_churn():
    d = [deal("X", "FUND A", "BUY", 500000),
         deal("X", "FUND B", "BUY", 300000)]
    c = va.detect_prop_churn(d, day_volume=2000000)
    check("one-sided flow is not churn", c["churn_qty"] is None, str(c))


def test_lopsided_two_way_is_not_churn():
    """Bought a million, sold ten thousand -- that is accumulation with a trim,
    not a round-trip."""
    d = [deal("X", "FUND A", "BUY", 1000000), deal("X", "FUND A", "SELL", 10000)]
    c = va.detect_prop_churn(d, day_volume=3000000)
    check("lopsided is not churn", c["churn_qty"] is None, str(c))


def test_unparseable_quantities_are_skipped_not_crashed():
    d = [deal("X", "A", "BUY", "n/a"), deal("X", "A", "SELL", "1,234")]
    c = va.detect_prop_churn(d, day_volume=100000)
    check("bad qty tolerated", c["churn_qty"] is None, str(c))


def test_comma_formatted_quantities_parse():
    d = [deal("X", "A", "BUY", "1,000"), deal("X", "A", "SELL", "1,000")]
    c = va.detect_prop_churn(d, day_volume=10000)
    check("comma quantities parse", c["churn_qty"] == 1000.0, str(c["churn_qty"]))


# ── announcement matching ─────────────────────────────────────────────────────
SPIKE = datetime(2026, 8, 28)


def test_material_filing_in_window_matches():
    """The real FMGOETZE trigger: a Record Date filing the evening before."""
    anns = [{"date": "27-Aug-2026 18:20:54", "subject": "Record Date",
             "detail": "informed the Exchange that Record Date..."}]
    hits = va.match_announcements(anns, SPIKE, 7)
    check("record date matched", len(hits) == 1, str(hits))


def test_immaterial_filing_is_ignored():
    anns = [{"date": "28-Aug-2026 16:05:58", "subject": "Copy of Newspaper Publication",
             "detail": "has informed the Exchange about publication"}]
    check("newspaper publication ignored",
          va.match_announcements(anns, SPIKE, 7) == [])


def test_exchange_spurt_notice_is_not_a_cause():
    """The bug the first live run found: NSE files a "Spurt in Volume" notice
    BECAUSE volume spiked. Counting it as the cause is circular, and it labelled
    7 of 9 spikes CORPORATE_ACTION, starving the UNEXPLAINED bucket."""
    anns = [{"date": "28-Aug-2026 12:40:44", "subject": "Spurt in Volume",
             "detail": "Exchange has sought clarification"}]
    check("spurt notice excluded", va.match_announcements(anns, SPIKE, 7) == [])
    anns2 = [{"date": "28-Aug-2026 18:00:37", "subject": "Price movement",
              "detail": "clarification sought from the company"}]
    check("price movement notice excluded",
          va.match_announcements(anns2, SPIKE, 7) == [])


def test_reactive_check_runs_before_the_material_check():
    """A clarification reply quotes the company and routinely contains material
    words -- so the exclusion has to win, or the keyword leaks it back in."""
    anns = [{"date": "28-Aug-2026 12:00:00", "subject": "Spurt in Volume",
             "detail": "company replied that it has declared a dividend and an "
                       "acquisition is under consideration"}]
    check("reactive beats material", va.match_announcements(anns, SPIKE, 7) == [])


def test_filing_after_the_spike_is_excluded():
    """A scanner that credits tomorrow's filing for today's volume reads the future."""
    anns = [{"date": "02-Sep-2026 10:00:00", "subject": "Dividend", "detail": ""}]
    check("future filing excluded", va.match_announcements(anns, SPIKE, 7) == [])


def test_filing_outside_window_is_excluded():
    anns = [{"date": "01-Aug-2026 10:00:00", "subject": "Dividend", "detail": ""}]
    check("stale filing excluded", va.match_announcements(anns, SPIKE, 7) == [])


def test_keyword_may_live_in_the_detail_line():
    """JGCHEM's trigger was a generic 'Updates' subject with the substance in the
    detail -- matching on subject alone would have missed it."""
    anns = [{"date": "26-Aug-2026 16:27:41", "subject": "Updates",
             "detail": "regarding intimation of land purchased for expansion"}]
    check("detail line searched", len(va.match_announcements(anns, SPIKE, 7)) == 1)


def test_unparseable_date_is_skipped():
    anns = [{"date": "not a date", "subject": "Dividend", "detail": ""}]
    check("bad date skipped", va.match_announcements(anns, SPIKE, 7) == [])


# ── cause ordering ────────────────────────────────────────────────────────────
def test_filing_outranks_flow():
    """A filing explains WHY the flow happened; the flow only says that it did."""
    cause, _ = va.classify_cause(
        [{"date": "27-Aug-2026", "subject": "Dividend", "detail": ""}],
        {"churn_share": 0.9, "churners": ["X"], "churn_qty": 1}, 4)
    check("filing wins over churn", cause == va.CORPORATE_ACTION, cause)


def test_material_churn_is_prop_churn():
    cause, why = va.classify_cause([], {"churn_share": 0.42, "churners": ["MICROCURVES"],
                                        "churn_qty": 1}, 2)
    check("churn classified", cause == va.PROP_CHURN, cause)
    check("reason says not accumulation",
          any("not accumulation" in w for w in why), str(why))


def test_immaterial_churn_falls_through_to_deal_driven():
    cause, _ = va.classify_cause([], {"churn_share": 0.01, "churners": ["X"],
                                      "churn_qty": 1}, 3)
    check("tiny churn is incidental", cause == va.DEAL_DRIVEN, cause)


def test_nothing_found_is_unexplained():
    cause, why = va.classify_cause([], {"churn_share": None, "churners": [],
                                        "churn_qty": None}, 0)
    check("no evidence -> UNEXPLAINED", cause == va.UNEXPLAINED, cause)
    check("reason says unexplained by the FEEDS",
          any("free feeds" in w for w in why), str(why))


# ── end-to-end ────────────────────────────────────────────────────────────────
def _frame():
    """Real 2026-08-28 bhavcopy rows plus one dull control."""
    f = pd.DataFrame([
        {"symbol": "FMGOETZE", "volume": 18185623, "turnover": 1.082349e10,
         "close": 602.05, "prev_close": 545.55, "trade_date": "2026-08-28"},
        {"symbol": "MASTEK", "volume": 5449060, "turnover": 1.002877e10,
         "close": 1901.40, "prev_close": 1611.60, "trade_date": "2026-08-28"},
        {"symbol": "DULL", "volume": 100000, "turnover": 5.0e8,
         "close": 100.0, "prev_close": 99.5, "trade_date": "2026-08-28"},
    ])
    f.attrs["turnover_is_qty"] = False
    return f


BASE = {"FMGOETZE": (226990.0, 250), "MASTEK": (94268.0, 250), "DULL": (95000.0, 250)}


def test_scan_end_to_end():
    res = va.scan(
        params=va.SpikeParams(min_multiple=10.0, min_turnover_cr=2.0),
        frame=_frame(),
        deals={"MASTEK": [deal("MASTEK", "MICROCURVES", "BUY", 264122),
                          deal("MASTEK", "MICROCURVES", "SELL", 264122)]},
        announcements_fn=lambda s: ([{"date": "27-Aug-2026 18:20:54",
                                      "subject": "Record Date", "detail": ""}]
                                    if s == "FMGOETZE" else []),
        baseline_fn=lambda s, d: BASE[s],
        market_caps={"FMGOETZE": 3.41e10},
        max_workers=2)
    syms = [r["symbol"] for r in res["rows"]]
    check("dull name filtered out", "DULL" not in syms, str(syms))
    check("both spikes found", set(syms) == {"FMGOETZE", "MASTEK"}, str(syms))
    check("sorted by multiple", syms[0] == "FMGOETZE", str(syms))

    by = {r["symbol"]: r for r in res["rows"]}
    check("FMGOETZE multiple", by["FMGOETZE"]["multiple"] == 80.1,
          str(by["FMGOETZE"]["multiple"]))
    check("MASTEK multiple", by["MASTEK"]["multiple"] == 57.8,
          str(by["MASTEK"]["multiple"]))
    check("turnover in crore", by["FMGOETZE"]["turnover_cr"] == 1082.3,
          str(by["FMGOETZE"]["turnover_cr"]))
    check("1-day return from bhavcopy prev_close",
          by["MASTEK"]["day_pct"] == 17.98, str(by["MASTEK"]["day_pct"]))
    check("pct of mcap when a cap is supplied",
          by["FMGOETZE"]["pct_mcap"] == 31.74, str(by["FMGOETZE"]["pct_mcap"]))
    check("FMGOETZE attributed to the filing",
          by["FMGOETZE"]["cause"] == va.CORPORATE_ACTION, by["FMGOETZE"]["cause"])
    # Measured, not assumed: the real round-trip is 9.7% of MASTEK's volume,
    # under CHURN_SHARE_MIN, so it is DEAL_DRIVEN with the churn share printed --
    # not PROP_CHURN. Guards against re-tuning the threshold to fit one example.
    check("MASTEK is deal-driven with partial churn",
          by["MASTEK"]["cause"] == va.DEAL_DRIVEN, by["MASTEK"]["cause"])
    check("churn share still reported on the row",
          0.09 < (by["MASTEK"]["churn_share"] or 0) < 0.10,
          str(by["MASTEK"]["churn_share"]))
    check("reason states the lower bound",
          any("lower bound" in w for w in by["MASTEK"]["reasons"]),
          str(by["MASTEK"]["reasons"]))
    check("tally counts causes", res["tally"][va.CORPORATE_ACTION] == 1
          and res["tally"][va.DEAL_DRIVEN] == 1, str(res["tally"]))


def test_short_history_is_skipped_not_scored():
    """A name listed three months ago has no meaningful one-year average, and a
    spike measured against 20 sessions is arithmetic, not a signal."""
    res = va.scan(params=va.SpikeParams(min_multiple=10.0, min_turnover_cr=2.0),
                  frame=_frame(), deals={}, announcements_fn=lambda s: [],
                  baseline_fn=lambda s, d: (1000.0, 12), max_workers=2)
    check("all skipped for short history", res["hits"] == 0, str(res["hits"]))
    check("skips are counted, not silent", res["skipped_short_history"] == 3,
          str(res["skipped_short_history"]))


def test_illiquid_spike_is_filtered_by_turnover():
    f = _frame()
    f.loc[len(f)] = {"symbol": "TINY", "volume": 900000, "turnover": 1.0e6,
                     "close": 1.1, "prev_close": 1.0, "trade_date": "2026-08-28"}
    res = va.scan(params=va.SpikeParams(min_multiple=5.0, min_turnover_cr=2.0),
                  frame=f, deals={}, announcements_fn=lambda s: [],
                  baseline_fn=lambda s, d: (BASE.get(s, (9000.0, 250)))
                  if s in BASE else (9000.0, 250), max_workers=2)
    check("illiquid spike filtered", "TINY" not in [r["symbol"] for r in res["rows"]],
          str([r["symbol"] for r in res["rows"]]))


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
    print("All volume_anomaly tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
