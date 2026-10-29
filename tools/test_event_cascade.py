"""B-190 — reverse event cascade: stock → sector → events (tools/event_cascade.py)."""
import numpy as np
import pandas as pd

import event_cascade as ec

N = 400


def _closes(seed=0, beta=1.0, kick=None):
    """(stock, sector, market) close series on one business-day index. `kick`
    = {pos: (stock_ret, sector_ret)} adds an abnormal log return on that day."""
    idx = pd.bdate_range("2025-01-01", periods=N)
    rng = np.random.default_rng(seed)
    m = rng.normal(0, 0.01, N)
    sec = beta * m + rng.normal(0, 0.004, N)
    stk = sec + rng.normal(0, 0.004, N)
    for p, (ks, kx) in (kick or {}).items():
        stk[p] += ks
        sec[p] += kx
    as_close = lambda r: pd.Series(100 * np.exp(np.cumsum(r)), index=idx)
    return as_close(stk), as_close(sec), as_close(m)


def _ev(pos, kind="M", key="M:budget", expected=None, label="Budget (full)"):
    idx = pd.bdate_range("2025-01-01", periods=N)
    return {"date": str(idx[pos].date()), "kind": kind, "label": label,
            "status_key": key, "expected": expected}


def _build(stock, sector, market, events, ticker="^CNXINFRA"):
    return ec.build_cascade("HAL", stock, market, sector, events=events,
                            sector_ticker=ticker, sector_label="Capital Goods")


def _by_id(c):
    return {n["id"]: n for n in c["nodes"]}


# ── shape ─────────────────────────────────────────────────────────────────────
def test_nodes_are_a_flat_parent_pointer_tree():
    s, x, m = _closes()
    c = _build(s, x, m, [_ev(300), _ev(350, "E", "E", label="Results")])
    nodes = _by_id(c)
    assert nodes["stock"]["depth"] == 0 and nodes["stock"]["parent"] is None
    assert nodes["sector"]["parent"] == "stock" and nodes["sector"]["depth"] == 1
    evs = [n for n in c["nodes"] if n["depth"] == 2]
    assert len(evs) == 2 and all(n["parent"] == "sector" for n in evs)
    for n in evs:
        for k in ("kind", "label", "window", "move", "sector_move", "z",
                  "expected", "direction", "edge", "status"):
            assert k in n


def test_excess_and_z_pick_up_an_abnormal_day():
    s, x, m = _closes(kick={300: (0.06, 0.05)})
    ev = [n for n in _build(s, x, m, [_ev(300)])["nodes"] if n["depth"] == 2][0]
    assert ev["move"] > 4 and ev["sector_move"] > 3      # percent, d0..d+5
    assert ev["z"] > 2
    assert ev["direction"] == "up"
    assert ev["window"] == "d0..d+5"


# ── edges ─────────────────────────────────────────────────────────────────────
def test_edge_solid_only_for_measured_kinds():
    s, x, m = _closes(kick={300: (0.06, 0.0), 350: (0.06, 0.0)})
    evs = [n for n in _build(s, x, m, [_ev(300), _ev(350, "E", "E", label="Results")])["nodes"]
           if n["depth"] == 2]
    edges = {n["kind"]: n["edge"] for n in evs}
    assert edges == {"M": "solid", "E": "dashed"}
    assert evs[0]["status"].startswith("measured")


def test_edge_dotted_when_the_stock_only_rode_its_sector():
    s, x, m = _closes(kick={300: (0.05, 0.05)})          # all of it sector-wide
    ev = [n for n in _build(s, x, m, [_ev(300)])["nodes"] if n["depth"] == 2][0]
    assert ev["edge"] == "dotted"
    assert ev["measured"] is True                      # still says what is known


# ── expected vs actual ────────────────────────────────────────────────────────
def test_expected_direction_miss_is_flagged():
    s, x, m = _closes(kick={300: (-0.06, 0.0)})
    ev = [n for n in _build(s, x, m, [_ev(300, "E", "E", expected="up",
                                          label="Results")])["nodes"] if n["depth"] == 2][0]
    assert ev["direction"] == "down" and ev["miss"] is True


def test_earnings_events_carry_expected_from_surprise_sign():
    rows = ec.earnings_events({"events": [
        {"date": "2026-08-12", "surprise_pct": 7.5},
        {"date": "2026-05-12", "surprise_pct": -3.0},
        {"date": "2026-02-12", "surprise_pct": None}]})
    assert [r["expected"] for r in rows] == ["up", "down", None]
    assert all(r["kind"] == "E" for r in rows)


# ── missing pieces ────────────────────────────────────────────────────────────
def test_missing_sector_keeps_events_hanging_off_the_stock():
    s, _x, m = _closes()
    c = _build(s, None, m, [_ev(300)])
    nodes = _by_id(c)
    assert nodes["sector"]["missing"] is True
    ev = [n for n in c["nodes"] if n["depth"] == 2][0]
    assert ev["parent"] == "stock" and ev["sector_move"] is None
    assert ev["edge"] != "dotted"


def test_event_without_enough_history_is_dropped():
    s, x, m = _closes()
    c = _build(s, x, m, [_ev(30)])                      # < 120 estimation days
    assert [n for n in c["nodes"] if n["depth"] == 2] == []


def test_collect_survives_a_failing_source():
    s, x, m = _closes()
    idx = s.index

    def boom(_sym):
        raise RuntimeError("yahoo down")

    pol = pd.DataFrame({"date": [str(idx[300].date())], "event_type": ["budget"],
                        "label": ["full"]})
    c = ec.collect("HAL", s, m, x, sector_ticker="^CNXINFRA", sector_label="Capital Goods",
                   earnings_fn=boom, policy_fn=lambda: pol)
    assert c["missing"] == ["E"]
    assert [n["kind"] for n in c["nodes"] if n["depth"] == 2] == ["M"]


def test_collect_keeps_only_the_latest_events():
    s, x, m = _closes()
    idx = s.index
    pol = pd.DataFrame({"date": [str(idx[p].date()) for p in range(150, 390, 20)],
                        "event_type": ["mpc"] * 12, "label": ["hold"] * 12})
    c = ec.collect("HAL", s, m, x, sector_ticker="^CNXINFRA", sector_label="Capital Goods",
                   earnings_fn=lambda _s: {"events": []}, policy_fn=lambda: pol)
    evs = [n for n in c["nodes"] if n["depth"] == 2]
    assert len(evs) == ec.MAX_POLICY


# ── bottom line ───────────────────────────────────────────────────────────────
def test_summary_tallies_up_and_down_and_names_what_is_measured():
    s, x, m = _closes(kick={300: (0.06, 0.0), 350: (-0.06, 0.0)})
    c = _build(s, x, m, [_ev(300), _ev(350, "E", "E", label="Results")])
    assert c["up"] == 1 and c["down"] == 1
    assert "2 linked events" in c["text"] and "1 up" in c["text"] and "1 down" in c["text"]
    assert "measured" in c["text"]
