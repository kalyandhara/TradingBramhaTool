"""breadth_strip: the 50/200 SMA quadrants and their markup."""
import pandas as pd

import breadth_strip as bs


def _frame(closes):
    idx = pd.date_range("2024-01-01", periods=len(closes), freq="B")
    return pd.DataFrame({"Close": closes}, index=idx)


def _series(base: float, tail: list[float], n: int = 220) -> list[float]:
    """`n - len(tail)` bars at `base`, then `tail`."""
    return [base] * (n - len(tail)) + tail


# Engineered so each name lands in exactly one bucket:
#   both      — flat 100, last bar 120 (above both means)
#   neither   — flat 100, last bar 80
#   fast_only — 200 for most of the window, then 60 for the last 50, last 90:
#               above the 50 mean (~60.6) but below the 200 mean (~>100)
#   slow_only — 50 for most of the window, then 150 for the last 50, last 110:
#               below the 50 mean (~149) but above the 200 mean (~<100)
HIST = {
    "UP":   _frame(_series(100, [120])),
    "DOWN": _frame(_series(100, [80])),
    "REC":  _frame(_series(200, [60] * 49 + [90])),
    "PULL": _frame(_series(50, [150] * 49 + [110])),
    "NEW":  _frame([100.0] * 120),          # too young for the 200 SMA
}


def test_each_name_lands_in_its_quadrant():
    q = bs.sma_quadrants(HIST)
    assert q["counts"] == {"both": 1, "fast_only": 1, "slow_only": 1, "neither": 1}


def test_short_history_is_excluded_from_every_bucket():
    q = bs.sma_quadrants(HIST)
    assert q["covered"] == 4 and q["excluded"] == 1
    assert sum(q["counts"].values()) == q["covered"]
    assert abs(sum(q["pcts"].values()) - 100.0) < 1e-9


def test_members_filter_counts_short_and_missing_apart():
    # NEW is in the download but too young; GONE is not in the download at all.
    # Only NEW is "under 200 sessions" — GONE must not be told as that.
    q = bs.sma_quadrants(HIST, members={"UP", "DOWN", "NEW", "GONE"})
    assert q["covered"] == 2 and q["excluded"] == 1 and q["missing"] == 1
    assert q["counts"]["both"] == 1 and q["counts"]["neither"] == 1


def test_whole_download_has_nothing_missing():
    assert bs.sma_quadrants(HIST)["missing"] == 0


def test_no_coverage_is_none_not_zero_percent():
    q = bs.sma_quadrants({"NEW": HIST["NEW"]})
    assert q["covered"] == 0 and all(v is None for v in q["pcts"].values())
    assert bs.rs.NA in bs.quadrant_html(q, "NIFTY 500")


def test_quadrant_html_labels_universe_coverage_and_non_vote():
    q = bs.sma_quadrants(HIST)
    subs = [("NIFTY 50", bs.sma_quadrants(HIST, members={"UP"}))]
    html = bs.quadrant_html(q, "NIFTY 500", as_of="2026-11-20", subs=subs)
    for text in ("NIFTY 500", "50 / 200 SMA", "close 2026-11-20", "does not vote",
                 "Above both", "Above 50 only", "Above 200 only", "Below both",
                 "25.0%", "under 200 sessions excluded", "NIFTY 50",
                 '<span class="tb-mono">1</span> measured'):
        assert text in html, text


# The sub-indices this desk draws, as (label, members) — membership chosen so
# each line reads differently: Bank has a short-history name, Smallcap a name
# missing from the download, Midcap nothing to caveat.
SUBS = {"NIFTY 50": {"UP", "DOWN"}, "NIFTY Bank": {"UP", "REC", "NEW"},
        "NIFTY Midcap 150": {"PULL"}, "NIFTY Smallcap 250": {"DOWN", "GONE"}}


def test_sub_universes_are_bank_midcap150_smallcap250_inside_the_500():
    labels = [lbl for lbl, _ in bs.SUB_UNIVERSES]
    assert labels == ["NIFTY 50", "NIFTY Bank", "NIFTY Midcap 150", "NIFTY Smallcap 250"]
    import nse_universe as nu
    for _, key in bs.SUB_UNIVERSES:
        assert key in nu.INDEX_CSVS, key        # same CSV source as NIFTY 50 / 500


def test_sub_universe_members_skips_unreachable_lists(monkeypatch):
    lists = {"nifty50": {"UP"}, "niftybank": set(), "niftymidcap150": {"PULL"},
             "niftysmallcap250": {"DOWN"}}
    monkeypatch.setattr(bs, "index_members", lambda key: lists[key])
    got = bs.sub_universe_members()
    # An empty list is not drawn — never silently widened to the whole 500.
    assert list(got) == ["NIFTY 50", "NIFTY Midcap 150", "NIFTY Smallcap 250"]


def test_sub_quadrants_follow_sub_universe_order_and_membership():
    subs = bs.sub_quadrants(HIST, SUBS)
    assert [lbl for lbl, _ in subs] == list(SUBS)
    q = dict(subs)
    assert q["NIFTY Bank"]["counts"] == {"both": 1, "fast_only": 1, "slow_only": 0,
                                         "neither": 0}
    assert q["NIFTY Bank"]["excluded"] == 1 and q["NIFTY Bank"]["missing"] == 0
    assert q["NIFTY Midcap 150"]["counts"]["slow_only"] == 1
    assert q["NIFTY Smallcap 250"]["covered"] == 1 and q["NIFTY Smallcap 250"]["missing"] == 1


def test_breadth_row_draws_every_sub_universe_with_its_coverage():
    html = bs.quadrant_html(bs.sma_quadrants(HIST), "NIFTY 500",
                            subs=bs.sub_quadrants(HIST, SUBS))
    for lbl in SUBS:
        assert lbl in html, lbl
    # one caveat for the 500 itself (NEW) and one for Bank (NEW)
    assert html.count("under 200 sessions excluded") == 2
    assert "not in the NIFTY 500 download" in html          # Smallcap's GONE
    assert html.count("measured") == 1 + len(SUBS)


def test_sub_universe_with_no_coverage_is_not_drawn():
    html = bs.quadrant_html(bs.sma_quadrants(HIST), "NIFTY 500",
                            subs=bs.sub_quadrants(HIST, {"NIFTY Bank": {"GONE"}}))
    assert "NIFTY Bank" not in html


def test_bucket_tables_work_for_each_sub_universe():
    for lbl, members in SUBS.items():
        q = bs.sma_quadrants(HIST, members=members)
        m = bs.quadrant_members(HIST, members=members)
        assert {k: len(v) for k, v in m.items()} == q["counts"], lbl
        assert set().union(*(set(v["Symbol"]) for v in m.values())) <= members


def test_universe_options_put_the_500_first_then_drawn_subs():
    assert bs.universe_options(SUBS) == ["NIFTY 500", *SUBS]
    assert bs.universe_options({}) == ["NIFTY 500"]


def test_strip_no_longer_draws_separate_sma_bars():
    titles = [b.title for b in bs.build_bars(HIST, None)]
    assert not any("SMA" in t for t in titles)


def test_members_tables_match_counts_and_carry_distances():
    q = bs.sma_quadrants(HIST)
    m = bs.quadrant_members(HIST)
    assert {k: len(v) for k, v in m.items()} == q["counts"]
    up = m["both"].iloc[0]
    assert up["Symbol"] == "UP" and up["Close"] == 120
    assert round(up["1D %"], 6) == 20.0 and up["% vs SMA50"] > 0 and up["% vs SMA200"] > 0
    assert m["neither"].iloc[0]["Symbol"] == "DOWN"


def test_members_rank_in_each_buckets_direction_and_respect_top():
    hist = {"A": _frame(_series(100, [110])), "B": _frame(_series(100, [130])),
            "C": _frame(_series(100, [120])),
            "X": _frame(_series(100, [90])), "Y": _frame(_series(100, [70]))}
    m = bs.quadrant_members(hist, top=2)
    assert list(m["both"]["Symbol"]) == ["B", "C"]          # strongest first
    assert list(m["neither"]["Symbol"]) == ["Y", "X"]       # weakest first
    assert m["fast_only"].empty and m["slow_only"].empty


def test_members_filter_applies_to_tables():
    m = bs.quadrant_members(HIST, members={"UP", "NEW"})
    assert sum(len(v) for v in m.values()) == 1


def test_bucket_tables_feed_the_hover_rows():
    import watch_rail as wr
    df = bs.quadrant_members(HIST)["both"].rename(columns={"Symbol": "symbol"})
    rows = wr.scan_rows(df, bs.BUCKET_COLUMNS, close_col="Close", pct_col="1D %")
    assert rows[0]["symbol"] == "UP" and rows[0]["chart"] == "UP.NS"
    assert rows[0]["close"] == 120 and round(rows[0]["day_pct"], 6) == 20.0
    assert rows[0]["extra"]["% vs SMA50"] > 0 and rows[0]["extra"]["% vs SMA200"] > 0


def test_last_close_date_is_newest_bar():
    assert bs.last_close_date(HIST) == HIST["UP"].index[-1].strftime("%Y-%m-%d")
    assert bs.last_close_date({}) is None
