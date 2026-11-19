import screener_eps_fetch as f

HTML = """
<html><body><section id="profit-loss"><table class="data-table">
<thead><tr><th></th><th>Mar 2022</th><th>Mar 2023</th><th>Mar 2024</th><th>TTM</th></tr></thead>
<tbody>
<tr><td class="text">Sales&nbsp;+</td><td>1,000</td><td>1,200</td><td>1,500</td><td>1,600</td></tr>
<tr><td class="text">Net Profit&nbsp;+</td><td>100</td><td>-20</td><td>150</td><td>170</td></tr>
<tr><td class="text">EPS in Rs</td><td>10.5</td><td>-2.0</td><td>15.25</td><td>17</td></tr>
<tr><td class="text">Dividend Payout %</td><td>20%</td><td>0%</td><td>25%</td><td></td></tr>
</tbody></table></section></body></html>
"""


def test_parses_annual_eps_and_ignores_ttm_as_a_year():
    r = f.parse_profit_loss(HTML)
    assert [p["period_end"] for p in r["periods"]] == ["2022-03-31", "2023-03-31", "2024-03-31"]
    assert [p["eps"] for p in r["periods"]] == [10.5, -2.0, 15.25]
    assert r["periods"][0]["sales"] == 1000.0 and r["periods"][1]["net_profit"] == -20.0
    assert r["ttm"]["eps"] == 17.0


def test_negative_eps_is_kept_not_dropped():
    assert f.parse_profit_loss(HTML)["periods"][1]["eps"] == -2.0


def test_unrecognised_markup_returns_empty_not_a_guess():
    assert f.parse_profit_loss("<html><body><p>hi</p></body></html>")["periods"] == []
    assert f.parse_profit_loss("<section id='profit-loss'></section>")["periods"] == []


def test_period_end_handles_december_and_garbage():
    assert f._period_end("Dec 2019") == "2019-12-31"
    assert f._period_end("Feb 2020") == "2020-02-29"
    assert f._period_end("TTM") is None and f._period_end("") is None


def test_years_span():
    r = f.parse_profit_loss(HTML)
    assert round(f.years(r["periods"]), 0) == 2.0


def test_basis_is_unknown_unless_exactly_one_signal():
    assert f.basis_of("<a>View Standalone</a>") == "consolidated"
    assert f.basis_of("<a>View Consolidated</a>") == "standalone"
    assert f.basis_of("<a>View Standalone</a><a>View Consolidated</a>") == "unknown"
    assert f.basis_of("<p>nothing</p>") == "unknown"
