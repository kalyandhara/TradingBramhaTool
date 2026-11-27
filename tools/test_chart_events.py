"""B-188 — event markers on the chart (tools/chart_events.py)."""
import numpy as np
import pandas as pd

import chart_events as ce


def _bars(n=80, start="2026-06-01", vol=1000.0):
    idx = pd.bdate_range(start, periods=n)
    rng = np.random.default_rng(0)
    close = 100 * np.cumprod(1 + rng.normal(0, 0.005, n))
    return pd.DataFrame({"close": close, "volume": np.full(n, vol)}, index=idx)


# ── sources → rows ────────────────────────────────────────────────────────────
def test_earnings_rows_carry_surprise_and_kind_e():
    rows = ce.earnings_rows({"events": [
        {"date": "2026-08-12", "surprise_pct": 7.5},
        {"date": "2026-05-20", "surprise_pct": None}]})
    assert [r["kind"] for r in rows] == ["E", "E"]
    assert "+7.5" in rows[0]["label"]
    assert ce.earnings_rows(None) == []


def test_announcement_rows_keep_material_and_skip_routine():
    rows = ce.announcement_rows([
        {"date": "12-Aug-2026 18:30:00", "subject": "Receipt of Order", "detail": ""},
        {"date": "13-Aug-2026 10:00:00", "subject": "Trading Window", "detail": ""},
        {"date": "14-Aug-2026 10:00:00", "subject": "Newspaper Publication", "detail": "order"},
    ])
    assert [(r["date"], r["kind"]) for r in rows] == [("2026-08-12", "N")]


def test_policy_rows_split_budget_and_mpc():
    df = pd.DataFrame({"date": ["2026-02-01", "2026-06-05"],
                       "event_type": ["budget", "mpc"], "label": ["full", "hold"]})
    rows = ce.policy_rows(df)
    assert [(r["kind"], r["status_key"]) for r in rows] == [("M", "M:budget"), ("M", "M:mpc")]
    assert "Budget" in rows[0]["label"] and "MPC hold" in rows[1]["label"]


def test_anomaly_needs_both_volume_and_move():
    df = _bars()
    df.iloc[60, df.columns.get_loc("volume")] = 5000     # volume only
    df.iloc[70, df.columns.get_loc("volume")] = 5000     # volume + big move
    df.iloc[70, df.columns.get_loc("close")] = df["close"].iloc[69] * 1.08
    dates = [r["date"] for r in ce.anomaly_rows(df)]
    assert dates == [str(df.index[70].date())]


def test_anomaly_ignores_too_short_history():
    assert ce.anomaly_rows(_bars(n=30)) == []


# ── merge / status ────────────────────────────────────────────────────────────
def test_merge_one_per_kind_per_day_and_n_folds_into_e():
    rows = [
        {"date": "2026-08-12", "kind": "E", "label": "Results", "status_key": "E"},
        {"date": "2026-08-12", "kind": "N", "label": "Outcome of board", "status_key": "N"},
        {"date": "2026-08-20", "kind": "N", "label": "Order A", "status_key": "N"},
        {"date": "2026-08-20", "kind": "N", "label": "Order B", "status_key": "N"},
    ]
    out = ce.merge(rows)
    assert [(r["date"], r["kind"]) for r in out] == [("2026-08-12", "E"), ("2026-08-20", "N")]
    assert "Outcome of board" in out[0]["note"]          # folded, not lost
    assert "+1 more" in out[1]["label"]


def test_status_is_measured_only_for_b184_policy_days():
    assert ce.status_for("M:budget").startswith("measured")
    assert "1.65" in ce.status_for("M:budget")
    assert ce.status_for("M:mpc").startswith("measured")
    for k in ("E", "N", "A"):
        assert ce.status_for(k).startswith("hypothesis")


def test_post_moves_snap_to_next_session():
    df = _bars()
    sat = (df.index[40] + pd.Timedelta(days=(5 - df.index[40].weekday()) % 7 or 7))
    row = ce.with_moves([{"date": str(sat.date()), "kind": "M", "label": "x",
                          "status_key": "M:budget"}], df)[0]
    nxt = df.index[df.index > sat][0]
    pos = df.index.get_loc(nxt)
    assert row["session"] == str(nxt.date())
    exp = (df["close"].iloc[pos + 5] / df["close"].iloc[pos - 1] - 1) * 100
    assert abs(row["r5"] - exp) < 1e-9


# ── orchestrator ──────────────────────────────────────────────────────────────
def test_collect_survives_a_failing_source():
    df = _bars()

    def boom(_sym):
        raise RuntimeError("NSE 403")

    res = ce.collect("HAL", df,
                     earnings_fn=lambda s: {"events": [{"date": str(df.index[50].date()),
                                                        "surprise_pct": None}]},
                     ann_fn=boom,
                     policy_fn=lambda: pd.DataFrame(columns=["date", "event_type", "label"]))
    assert "N" in res["missing"]
    assert [e["kind"] for e in res["events"]] == ["E"]
    assert res["events"][0]["status"].startswith("hypothesis")


def test_collect_drops_events_outside_the_bars():
    df = _bars()
    res = ce.collect("HAL", df,
                     earnings_fn=lambda s: {"events": [{"date": "2019-01-01", "surprise_pct": None}]},
                     ann_fn=lambda s: [],
                     policy_fn=lambda: pd.DataFrame(columns=["date", "event_type", "label"]))
    assert res["events"] == [] and res["missing"] == []


def test_announcements_match_subject_only_and_skip_chart_noise():
    """RELIANCE over 10 years drew 936 N markers, mostly 'Loss of Share
    Certificates' and 'Updates' whose detail line mentioned an order."""
    rows = ce.announcement_rows([
        {"date": "01-Aug-2026", "subject": "Loss of Share Certificates", "detail": "order"},
        {"date": "02-Aug-2026", "subject": "Updates", "detail": "acquisition of land"},
        {"date": "03-Aug-2026", "subject": "Allotment of ESOP/ESPS", "detail": ""},
        {"date": "04-Aug-2026", "subject": "Disclosure under SEBI Takeover Regulations", "detail": ""},
        {"date": "05-Aug-2026", "subject": "Acquisition", "detail": ""},
    ])
    assert [r["date"] for r in rows] == ["2026-08-05"]
