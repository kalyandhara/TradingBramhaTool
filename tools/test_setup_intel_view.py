"""Setup Intelligence panel: conviction fields and the HTML view (setup_intel_view)."""
import report_style as rs
import stock_council as council
import setup_intel_view as siv


def _intel(bulls=5, risks=8, **kw):
    base = dict(status_label="Developing setup — not yet triggered", status_tone="neutral",
                chips=[("Relative strength", "Strong", "good"),
                       ("Breakout readiness", "Low", "bad"),
                       ("Accumulation", "Neutral", "neutral")],
                bullish_factors=[f"Bull line {i}" for i in range(bulls)],
                risk_factors=[f"Risk line {i}" for i in range(risks)],
                overall_view="Evidence is mixed; wait for a trigger.",
                bull_conviction=4.9, bear_conviction=3.6, net_score=8.0)
    base.update(kw)
    return council.SetupIntel(**base)


def test_setup_intelligence_carries_the_council_convictions():
    from test_cpr_vp import _frame
    prev = {"o": 100, "h": 101, "l": 99, "c": 100.5}
    df = _frame(n=260, prev=prev,
                last={"o": 100.6, "h": 101.5, "l": 100.4, "c": 101.2, "v": 3_000_000})
    bundle, bull, bear, card = council.run_council("TEST", df)
    intel = council.setup_intelligence(bundle, bull, bear, card)
    assert intel.bull_conviction == bull.conviction
    assert intel.bear_conviction == bear.conviction
    assert intel.net_score == card.net_score


def test_view_has_status_counts_and_every_factor():
    import re
    html = re.sub(r"<[^>]+>", "", siv.render_html(_intel(), rs.TOKENS))   # visible text
    assert "Developing setup — not yet triggered" in html
    assert "Supporting · 5" in html and "Risks · 8" in html
    for i in range(5):
        assert f"Bull line {i}" in html
    for i in range(8):
        assert f"Risk line {i}" in html            # folded lines are still on the page


def test_long_lists_fold_after_five_short_ones_do_not():
    html = siv.render_html(_intel(bulls=5, risks=8), rs.TOKENS)
    assert html.count("<details") == 1 and "+3 more" in html
    assert "<details" not in siv.render_html(_intel(bulls=2, risks=5), rs.TOKENS)


def test_tile_edge_takes_the_tone_colour():
    html = siv.render_html(_intel(), rs.TOKENS)
    good, risk = rs.tone_colors("good")[0], rs.tone_colors("risk")[0]
    assert f"border-left:3px solid {good}" in html     # Relative strength · Strong
    assert f"border-left:3px solid {risk}" in html     # Breakout readiness · Low


def test_balance_bar_splits_by_conviction_and_states_net():
    html = siv.render_html(_intel(), rs.TOKENS)
    assert "width:57.6%" in html                        # 4.9 / (4.9 + 3.6)
    assert "net +8" in html


def test_text_from_the_analysis_is_escaped():
    html = siv.render_html(_intel(bullish_factors=["<script>x</script> RSI 27"]), rs.TOKENS)
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_first_number_in_a_factor_is_emphasised():
    html = siv.render_html(_intel(risk_factors=["RSI 27 — momentum weak."]), rs.TOKENS)
    assert "RSI <b>27</b> — momentum weak." in html
