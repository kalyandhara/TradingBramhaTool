import csv
import datetime as dt

import index_valuation as iv

HEAD = ["Index Name", "Index Date", "Closing Index Value", "P/E", "P/B", "Div Yield"]


def _write(tmp, day, rows):
    p = tmp / f"ind_close_all_{day.isoformat()}.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(HEAD)
        for r in rows:
            w.writerow(r)


def _mk(tmp, series):
    d0 = dt.date(2025, 6, 2)
    for i, (pe, pb, dy) in enumerate(series):
        d = d0 + dt.timedelta(days=i)
        _write(tmp, d, [["Nifty 50", d.strftime("%d-%m-%Y"), "24000", pe, pb, dy],
                        ["Nifty Bank", d.strftime("%d-%m-%Y"), "50000", "99", "9", "9"]])


def test_reads_only_the_requested_index(tmp_path):
    _mk(tmp_path, [("20", "3", "1.2")] * 3)
    assert {r["pe"] for r in iv.history("Nifty 50", tmp_path)} == {20.0}


def test_dash_and_zero_are_missing_not_zero(tmp_path):
    _mk(tmp_path, [("20", "3", "1.2"), ("-", "0", "")])
    h = iv.history("Nifty 50", tmp_path)
    assert h[-1]["pe"] is None and h[-1]["pb"] is None and h[-1]["dy"] is None


def test_percentile_is_position_in_window(tmp_path):
    _mk(tmp_path, [("22", "3", "1"), ("20", "3", "1"), ("21", "3", "1"), ("19", "3", "1")])
    s = iv.summary("Nifty 50", tmp_path)
    assert s["pe"]["value"] == 19.0 and s["pe"]["min"] == 19.0 and s["pe"]["pctile"] == 25


def test_latest_missing_value_gives_none_not_stale(tmp_path):
    _mk(tmp_path, [("22", "3", "1"), ("-", "3", "1")])
    assert iv.summary("Nifty 50", tmp_path)["pe"] is None
    assert iv.caption(iv.summary("Nifty 50", tmp_path)) == "Index valuation unavailable."


def test_caption_never_labels_cheap_or_expensive(tmp_path):
    _mk(tmp_path, [("30", "3", "1"), ("19", "3", "1")])
    c = iv.caption(iv.summary("Nifty 50", tmp_path)).lower()
    assert "not a verdict" in c
    # The disclaimer may MENTION "cheap"; the caption may not ASSERT a label.
    c = c.replace("whether the market is cheap", "")
    for w in ("undervalued", "overvalued", "bargain", "is cheap", "is expensive", "buy"):
        assert w not in c


def test_no_files_returns_none(tmp_path):
    assert iv.summary("Nifty 50", tmp_path) is None


def test_real_cache_if_present():
    s = iv.summary("Nifty 50")
    if s is None:
        return
    assert s["pe"] is None or (s["pe"]["min"] <= s["pe"]["value"] <= s["pe"]["max"])
