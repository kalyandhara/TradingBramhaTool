"""pa_report — the Predictive Analysis PDF renders, and its shared helpers hold."""

import re
from datetime import datetime
from types import SimpleNamespace as NS

import numpy as np
import pandas as pd

import pa_report as pr


def _df(n=300):
    idx = pd.bdate_range(end="2026-10-05", periods=n)
    c = 100 * np.exp(np.cumsum(np.random.default_rng(1).normal(0, .015, n)))
    vol = np.random.default_rng(2).integers(100_000, 1_000_000, n)
    return pd.DataFrame({"open": c * .995, "high": c * 1.01, "low": c * .99,
                         "close": c, "volume": vol}, index=idx)


def test_clean_strips_unrenderable_and_escapes_mathtext():
    assert pr.clean("₹100 **bold** 🚀 $5") == r"Rs 100 bold \$5"
    assert pr.clean(None) == "-"
    assert pr.clean("<b>x</b>") == "x"


def test_stage_label_bands():
    assert pr.stage_label(8)[0] == "Stage-2 ideal band"
    assert pr.stage_label(4)[0] == "Stage-2 emerging"
    assert pr.stage_label(2)[0] == "Stage-1 base"
    assert pr.stage_label(0)[0] == "Stage-3/4 caution"


def test_smart_money_counts_add_up():
    f = pr.smart_money(_df())
    assert f["n"] == 60 and len(f["bars"]) == 60
    assert f["acc"] + f["dist"] <= f["n"]


def test_render_minimal_model_is_a_pdf():
    """Only the always-present keys — every optional section must skip cleanly."""
    df = _df()
    m = {"symbol": "TEST", "as_of": "2026-10-05", "generated_at": datetime.now(),
         "regime": "UNKNOWN", "price": float(df["close"].iloc[-1]), "df": df}
    assert pr.render_pdf(m)[:5] == b"%PDF-"


def test_render_full_model_paginates():
    df = _df()
    pil = [NS(name="Trend", score=70, weight=.3, reason="above means ₹")] * 6
    card = NS(verdict="WATCH", conviction=6, net_score=10, entry=100., stop=95.,
              targets=[110.], rr=[2.0], risk_pct=5., size_pct=1., horizon="4w",
              bull_top="b", bear_top="r", invalidations=["x"], regime_note="n")
    m = {"symbol": "TEST", "as_of": "2026-10-05", "generated_at": datetime.now(),
         "regime": "MIXED", "price": 100., "df": df, "card": card,
         "bull": NS(conviction=6, pillars=pil, breakers=[]),
         "bear": NS(conviction=3, pillars=pil, breakers=["y"]),
         "intel": NS(status_label="ok", status_tone="good", chips=[("a", "b", "good")],
                     bullish_factors=["f"] * 10, risk_factors=[], overall_view="v"),
         "flow": {**pr.smart_money(df), "obv_trend": "rising", "cmf": .1},
         "red_flags": {"counts": {}, "flags": [
             {"state": "FLAG", "severity": "critical", "label": "L",
              "source": "s", "detail": "d"}] * 12}}
    out = pr.render_pdf(m)
    assert out[:5] == b"%PDF-"
    pages = int(re.search(rb"/Count (\d+)", out).group(1))
    assert pages >= 2
