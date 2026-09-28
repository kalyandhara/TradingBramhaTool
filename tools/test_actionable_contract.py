"""The `actionable` contract — B-128.

Scanners put entry / stop / target on cards whose own state says they are NOT a
trade yet: a flag not broken, a wedge still forming. The harness traded every
card, so those plans went into every published plan R. Flag & Pole was the one
that got caught: plan R −0.43 with WATCH cards traded, +0.26 without them, which
is what finally reproduced B-92.

The contract is one key. A card may carry levels for the reader and still say
`actionable: False`; the harness then measures its SIGNAL (that is the pattern)
and COUNTS its plan without simulating it.

Pinned here:
* the harness honours the key, and counts what it skips — never drops it;
* `actionable` missing means actionable (every existing scanner keeps working);
* the scanners known to emit watch-state plans set the key from their state;
* an AUDIT over every registered scanner on real bars: a card whose own label
  says WATCH / forming / pre-breakout / unbroken may not carry an actionable
  plan. This is the test that stops the next scanner doing it.

Run:  python -m pytest tools/test_actionable_contract.py -q
"""
import re

import numpy as np
import pandas as pd
import pytest

import backtest as bt
import scanner_templates as sc


def _frame(n=320, seed=3):
    rng = np.random.default_rng(seed)
    c = 100 + np.cumsum(rng.normal(0.05, 1.0, n))
    return pd.DataFrame({"open": c, "high": c + 1, "low": c - 1, "close": c,
                         "volume": np.full(n, 1e6)})


@pytest.fixture
def stub(monkeypatch):
    """Every 20th bar fires; alternate cards declare themselves non-actionable."""
    def fn(df):
        n = len(df)
        if n % 20:
            return None
        last = float(df["close"].iloc[-1])
        card = {"entry": last, "stop": last - 3, "target": last + 6}
        if (n // 20) % 2:
            card["actionable"] = False
        return card
    monkeypatch.setitem(sc.SCANNERS, "_stub_b128", {"fn": fn})
    return "_stub_b128"


def test_harness_skips_and_counts_non_actionable_plans(stub):
    df = _frame()
    r = bt.backtest_scanner(stub, ["X"], lambda s: df, signal_mode="fresh")
    rb = r["r_metrics"]
    assert rb["plans_not_actionable"] > 0
    assert rb["n_with_plan"] > 0
    # the SIGNAL side still sees every card
    assert r["n_signals"] == rb["plans_not_actionable"] + rb["plans_seen"]


def test_a_missing_key_means_actionable(monkeypatch):
    def fn(df):
        if len(df) % 20:
            return None
        last = float(df["close"].iloc[-1])
        return {"entry": last, "stop": last - 3, "target": last + 6}
    monkeypatch.setitem(sc.SCANNERS, "_stub_b128b", {"fn": fn})
    df = _frame()
    r = bt.backtest_scanner("_stub_b128b", ["X"], lambda s: df, signal_mode="fresh")
    assert r["r_metrics"].get("plans_not_actionable", 0) == 0
    assert r["r_metrics"]["n_with_plan"] > 0


def test_pooling_keeps_the_count():
    pooled = bt._pool_r_blocks([
        {"n_with_plan": 0, "plans_seen": 0, "plans_not_actionable": 5},
        {"n_with_plan": 2, "plans_seen": 2, "plans_not_actionable": 1,
         "target_hits": 1, "stop_hits": 1, "open_exits": 0, "time_exits": 0,
         "positive_rate": 50.0, "avg_R": 0.0},
    ])
    assert pooled["plans_not_actionable"] == 6


# ── the audit ────────────────────────────────────────────────────────────────

#: Words a card uses about ITSELF when it is not yet a trade.
NOT_A_TRADE = re.compile(
    r"\b(WATCH|forming|pre-?breakout|unbroken|approaching|awaiting|no room)\b", re.I)


def _self_label(card):
    parts = [str(card.get(k, "")) for k in
             ("pattern_type", "verdict", "state", "state_label", "signal")]
    parts += [str(t) for t in (card.get("tags") or [])]
    return " | ".join(parts)


def test_no_scanner_puts_an_actionable_plan_on_a_card_that_calls_itself_a_watch():
    import screener_pipeline as sp
    offenders: dict[str, str] = {}
    checked = 0
    for sym in ("RELIANCE", "TCS", "HDFCBANK", "ABB", "360ONE"):
        try:
            df = sp.fetch_ohlcv(sym, days=1500)
        except Exception:
            continue
        if df is None or len(df) < 400:
            continue
        for t in range(300, len(df) - 1, 20):
            sub = df.iloc[:t + 1]
            for name, spec in sc.SCANNERS.items():
                if spec.get("needs_full_history") or name in offenders:
                    continue
                try:
                    card = spec["fn"](sub)
                except Exception:
                    continue
                if not card or card.get("entry") is None:
                    continue
                checked += 1
                m = NOT_A_TRADE.search(_self_label(card))
                if m and card.get("actionable") is not False:
                    offenders[name] = f"{sym}@{t}: '{m.group(0)}' in {_self_label(card)[:120]}"
    if not checked:
        pytest.skip("no cached bars")
    assert not offenders, "\n".join(f"{k}: {v}" for k, v in offenders.items())
