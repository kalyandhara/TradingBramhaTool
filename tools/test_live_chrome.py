"""live_chrome: freshness rule, tape markup."""
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




