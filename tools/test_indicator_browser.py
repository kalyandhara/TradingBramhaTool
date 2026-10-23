"""The card-style Indicator Browser keeps the rules it was built on — B-150 / B-152.

Static checks on indicator_browser.js and its wiring in chart_dashboard.html
(the behaviour itself was verified live on :5001, 2026-10-14):

* the page loads it, after the catalogue, and the INDICATORS button opens it
  unless the person chose the classic list — which stays reachable both ways;
* it never edits pane.indicators itself: add / remove go through the pane's
  classic checkbox, so ETF-mode refusal, RSI↔divergence coupling and
  savePaneCfg keep applying (B-148 hard rule);
* every localStorage access is wrapped, and favourites / recent use the keys
  B-152 named, global rather than per pane;
* text reaches innerHTML only through esc();
* the draft tag is driven by INDICATOR_CATALOGUE_STATUS, which is still "draft"
  until the owner approves the B-149 text.

Run:  python -m pytest tools/test_indicator_browser.py -q
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
JS = (HERE / "indicator_browser.js").read_text(encoding="utf-8")
HTML = (HERE / "chart_dashboard.html").read_text(encoding="utf-8")
CAT = (HERE / "indicator_catalogue.js").read_text(encoding="utf-8")


def test_page_loads_browser_after_catalogue():
    a = HTML.index('<script src="/indicator_catalogue.js"></script>')
    b = HTML.index('<script src="/indicator_browser.js"></script>')
    assert a < b


def test_indicators_button_opens_browser_and_classic_stays_reachable():
    assert "IB.open(pane)" in HTML and "IB.classicPreferred()" in HTML
    assert 'class="ind-cardview"' in HTML           # classic → cards
    assert 'data-act="classic"' in JS               # cards → classic


def test_never_writes_pane_indicators_directly():
    assert not re.search(r"\.indicators\.(add|delete|clear)\(", JS)
    assert "dispatchEvent(new Event('change'" in JS


def test_storage_is_wrapped_and_named():
    for key in ("tb_ind_favs", "tb_ind_recent"):
        assert f"'{key}'" in JS
    uses = re.findall(r"localStorage\.\w+\(", JS)
    assert uses and all(u in ("localStorage.getItem(", "localStorage.setItem(") for u in uses)
    # Each access sits inside a try on the same line, with its catch next to it.
    for line in [l for l in JS.splitlines() if "localStorage." in l and "//" not in l.split("localStorage.")[0]]:
        assert "try" in line, line.strip()


def test_label_text_is_escaped():
    for field in ("d.label", "d.short", "d.desc", "d.group"):
        for m in re.finditer(re.escape("${" + field), JS):
            assert False, f"unescaped {field} interpolated into markup at {m.start()}"
    assert "esc(d.label)" in JS and "esc(d.desc)" in JS


def test_draft_tag_follows_catalogue_status():
    assert "INDICATOR_CATALOGUE_STATUS" in JS and "Draft — under review" in JS
    assert re.search(r'window\.INDICATOR_CATALOGUE_STATUS = "(draft|approved)";', CAT)


# ── B-153 / B-155 / B-156 / B-157 ─────────────────────────────────────────────
def test_discover_is_the_landing_view_with_three_rows():
    assert "view = '__discover__'" in JS
    for row in ("Start here", "New on the desk", "More to explore"):
        assert row in JS
    start = re.search(r"const START_HERE = \[([^\]]*)\]", JS).group(1)
    keys = re.findall(r"'([a-z0-9_]+)'", start)
    defs = HTML.split("const INDICATOR_DEFS = [", 1)[1].split("\n];", 1)[0]
    assert keys and all(f"key:'{k}'" in defs for k in keys)
    assert "popular" not in JS.lower()          # one user: no usage ranking


def test_goal_chips_filter_by_catalogue_goals():
    assert "data-goal=" in JS and "(d.goals || []).includes(goal)" in JS
    assert "What do you want to see?" in JS


def test_keyboard_lives_inside_the_overlay_only():
    for k in ("ArrowDown", "e.shiftKey", "'f'", "'Escape'", "'/'"):
        assert k in JS
    assert "document.addEventListener('keydown'" not in JS
    assert "window.addEventListener('keydown'" not in JS


def test_learn_more_links_only_indicators_with_a_concept():
    assert "d.concept ?" in JS and "/learn/${encodeURIComponent(d.key)}" in JS


def test_learn_route_serves_concepts_and_nothing_else():
    import chart_server as cs
    cs.app.config["TESTING"] = True
    c = cs.app.test_client()
    r = c.get("/learn/rsi")
    assert r.status_code == 200 and b"Relative Strength" in r.data
    assert b"[[" not in r.data
    for bad in ("sma20", "RSI", "..%2Fchart_server", "nope"):
        assert c.get(f"/learn/{bad}").status_code == 404, bad
