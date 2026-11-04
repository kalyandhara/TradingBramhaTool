"""live_chrome: freshness rule, tape/hero markup, sparkline geometry."""
from datetime import datetime, timedelta

import live_chrome as lc

NOW = datetime(2026, 10, 22, 11, 0)


def test_live_session_ages_by_the_clock():
    f = lambda m: lc.freshness(NOW - timedelta(minutes=m), stale=False, live=True, now=NOW)
    assert (f(5), f(15), f(16), f(60), f(61)) == ("green", "green", "orange", "orange", "red")


def test_live_session_ignores_the_stale_flag_in_favour_of_age():
    assert lc.freshness(NOW - timedelta(minutes=2), stale=True, live=True, now=NOW) == "green"


def test_closed_market_uses_last_close_not_age():
    old = NOW - timedelta(hours=10)
    assert lc.freshness(old, stale=False, live=False, now=NOW) == "green"
    assert lc.freshness(old, stale=True, live=False, now=NOW) == "red"


def test_fresh_dot_is_streamlit_colour_markdown():
    assert lc.fresh_dot(NOW, stale=False, live=False) == ":green[●]"


def test_tape_shows_dash_for_unread_quote_and_loops_twice():
    html = lc.tape_html([lc.Quote("NIFTY 50", 23146.15, 0.65),
                         lc.Quote("DAX", None, None)])
    assert html.count("23,146") == 2           # two copies = seamless loop
    assert "▲ +0.65%" in html
    assert html.count(">—</span>") == 2 and "0.00" not in html


def test_tape_escapes_labels():
    assert "S&amp;P 500" in lc.tape_html([lc.Quote("S&P 500", 5000.0, -1.0)])


def test_vix_formats_two_decimals_and_inverts_tile_colour():
    up_vix = lc._tile(lc.Quote("INDIA VIX", 16.68, 3.6, (15.0, 16.68)))
    assert "16.68" in up_vix and lc._DOWN in up_vix   # VIX rising is risk


def test_sparkline_needs_two_points_and_stays_in_box():
    assert lc.sparkline_svg((1.0,), "#fff") == ""
    svg = lc.sparkline_svg((10.0, 20.0, 15.0), "#fff", w=100, h=30)
    pts = svg.split('points="')[1].split('"')[0].split()
    ys = [float(p.split(",")[1]) for p in pts]
    assert pts[0].startswith("0.0,") and pts[-1].startswith("100.0,")
    assert min(ys) >= 2 and max(ys) <= 28


def test_hero_states_verdict_and_pulses_only_when_live():
    kw = dict(market_label="live · 11:00 IST", verdict="Trade light",
              instruction="Half size.", verdict_tone="warn", regime="RISK-ON",
              tiles=[lc.Quote("NIFTY 50", None, None)], today="Thursday")
    live = lc.hero_html(market_state="LIVE", **kw)
    closed = lc.hero_html(market_state="CLOSED", **kw)
    assert "Trade light" in live and "NIFTY RISK-ON" in live and "data n/a" in live
    assert 'class="tb-pulse"' in live and 'class="tb-pulse"' not in closed
    assert "Market closed" in closed


def test_tape_starts_with_the_hero_tiles():
    assert [lbl for _, lbl in lc.TAPE[:3]] == ["NIFTY 50", "BANK NIFTY", "INDIA VIX"]
