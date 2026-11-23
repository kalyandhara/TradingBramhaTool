"""The chart server must not serve arbitrary files from tools/ (SBC_Tool-z5u).

`Flask(__name__, static_folder=str(HERE))` used to register Flask's built-in
static route at /tools/<path:filename>, which handed out trading_bramha.db
(with the digest's Gmail app password and the screener.in session cookie in
its settings table), rec_audit.db, source and configs to anyone on the LAN.
Every asset the chart page needs has an explicit route, so the built-in static
route must not exist at all.

    py -3 -m pytest tools/test_chart_server_static.py -q
"""
import chart_server as cs


def _get(path):
    with cs.app.test_client() as c:
        return c.get(path)


def test_no_builtin_static_route():
    rules = [str(r) for r in cs.app.url_map.iter_rules()]
    assert not [r for r in rules if r.startswith("/tools")], rules
    assert "static" not in cs.app.view_functions


def test_tools_files_are_not_served():
    for path in ("/tools/trading_bramha.db", "/tools/rec_audit.db",
                 "/tools/chart_server.py", "/tools/alert_config.json",
                 "/static/trading_bramha.db"):
        assert _get(path).status_code == 404, path


def test_page_assets_still_served():
    for path in ("/", "/manifest.webmanifest", "/sw.js", "/icon-192.png",
                 "/cpr.js", "/indicator_catalogue.js"):
        assert _get(path).status_code == 200, path
