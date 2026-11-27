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


def test_members_filter_and_missing_members_count_as_excluded():
    q = bs.sma_quadrants(HIST, members={"UP", "DOWN", "GONE"})
    assert q["covered"] == 2 and q["excluded"] == 1
    assert q["counts"]["both"] == 1 and q["counts"]["neither"] == 1


def test_no_coverage_is_none_not_zero_percent():
    q = bs.sma_quadrants({"NEW": HIST["NEW"]})
    assert q["covered"] == 0 and all(v is None for v in q["pcts"].values())
    assert bs.rs.NA in bs.quadrant_html(q, "NIFTY 500")


def test_quadrant_html_labels_universe_coverage_and_non_vote():
    q = bs.sma_quadrants(HIST)
    sub = ("NIFTY 50", bs.sma_quadrants(HIST, members={"UP"}))
    html = bs.quadrant_html(q, "NIFTY 500", as_of="2026-11-20", sub=sub)
    for text in ("NIFTY 500", "50 / 200 SMA", "close 2026-11-20", "does not vote",
                 "Above both", "Above 50 only", "Above 200 only", "Below both",
                 "25.0%", "under 200 sessions excluded", "NIFTY 50 (1 measured)"):
        assert text in html, text


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
