"""FII/DII daily flow strip — provisional equity cash-market figures from NSE.

Sits under the breadth strip on Home, after the divider. One card per
participant class: FII/FPI, DII, and their net. Numbers are ₹ Crore, the
unit NSE itself uses.

Data source: www.nseindia.com/api/fiidiiTradeReact — NSE's own JSON API for
provisional FII/DII equity cash-market data. No session cookie required from
this machine (Akamai gate appears inactive for this endpoint on the local
network). Falls back to DATA N/A gracefully if the fetch fails.

JSON schema (as of 2026-10):
  [{"buyValue":"17003.9","category":"FII/FPI","date":"21-Oct-2026",
    "netValue":"1022.32","sellValue":"15981.58"}, ...]

Fallback: if the fetch fails, every card renders DATA N/A — the page does
not die and no synthetic zero is displayed as a real figure.
"""
from __future__ import annotations

from dataclasses import dataclass

import requests

import report_style as rs

NSE_FII_URL = "https://www.nseindia.com/api/fiidiiTradeReact"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, */*",
    "Referer": "https://www.nseindia.com/",
}
_TIMEOUT = 10


@dataclass(frozen=True)
class FlowRow:
    category: str        # "FII/FPI", "DII", "Net (FII+DII)"
    buy: float | None
    sell: float | None
    net: float | None
    date: str | None     # "21-Oct-2026"


def _f(v) -> float | None:
    try:
        return float(str(v).replace(",", ""))
    except (ValueError, TypeError):
        return None


def fetch_flow() -> list[FlowRow]:
    """Download today's provisional FII/DII equity flow from NSE.

    Returns a list of FlowRow (FII/FPI first, DII second, Net third).
    Returns an empty list on any fetch or parse failure.
    """
    try:
        resp = requests.get(NSE_FII_URL, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []
    rows: list[FlowRow] = []
    fii_net: float | None = None
    dii_net: float | None = None
    date_val: str | None = None
    for item in data:
        cat = str(item.get("category", "")).strip()
        buy = _f(item.get("buyValue"))
        sell = _f(item.get("sellValue"))
        net = _f(item.get("netValue"))
        d = str(item.get("date", "")).strip() or None
        if d:
            date_val = d
        rows.append(FlowRow(category=cat, buy=buy, sell=sell, net=net, date=d or date_val))
        if "FII" in cat.upper():
            fii_net = net
        elif "DII" in cat.upper():
            dii_net = net
    if fii_net is not None and dii_net is not None:
        rows.append(FlowRow(category="Net (FII+DII)", buy=None, sell=None,
                            net=fii_net + dii_net, date=date_val))
    return rows


# ──────────────────────────────────────────────────────────────────────────────
# HTML card
# ──────────────────────────────────────────────────────────────────────────────
def _crore(v: float | None) -> str:
    if v is None:
        return rs.NA
    sign = "+" if v >= 0 else ""
    return f"{sign}₹{v:,.2f} Cr"


def flow_card_html(row: FlowRow) -> str:
    """A single flow card: category title, net value large, buy/sell small."""
    good, _ = rs.tone_colors("good")
    risk, _ = rs.tone_colors("risk")
    is_net = row.category.startswith("Net")
    net_color = good if (row.net or 0) >= 0 else risk

    head = (f'<div class="tb-micro" style="text-align:center;margin-bottom:4px;">'
            f'{row.category}</div>')

    if row.net is None:
        body = (f'<div class="tb-stat-val tb-na" style="text-align:center;">'
                f'{rs.NA}</div>'
                f'<div class="tb-micro" style="text-align:center;">no data</div>')
    else:
        net_sz = "18px" if is_net else "16px"
        net_w = "800" if is_net else "700"
        body = (f'<div class="tb-mono" style="font-size:{net_sz};font-weight:{net_w};'
                f'color:{net_color};text-align:center;margin:4px 0;">'
                f'{_crore(row.net)}</div>')
        if row.buy is not None and row.sell is not None:
            body += (
                f'<div style="display:flex;justify-content:space-between;'
                f'gap:4px;margin-top:3px;">'
                f'<span class="tb-micro" style="color:{good};">B {_crore(row.buy)}</span>'
                f'<span class="tb-micro" style="color:{risk};">S {_crore(row.sell)}</span>'
                f'</div>')
    foot = (f'<div class="tb-micro" style="text-align:center;margin-top:4px;">'
            f'NSE provisional · {row.date or "—"}</div>')
    return rs.card(head + body + foot, emphasis=is_net)


# ──────────────────────────────────────────────────────────────────────────────
# Streamlit surface
# ──────────────────────────────────────────────────────────────────────────────
def render() -> None:
    """Render the FII/DII flow strip. Called by dashboard_app inside _slots.market."""
    import streamlit as st

    @st.cache_data(ttl=1800, show_spinner=False)
    def _cached_flow():
        return fetch_flow()

    rows = _cached_flow()

    st.markdown(rs.wrap_row_css("tb_fiistrip"), unsafe_allow_html=True)
    with st.container(key="tb_fiistrip"):
        if not rows:
            st.caption("FII/DII flow — data unavailable (NSE provisional not yet published "
                       "or fetch failed)")
            return
        cols = st.columns(len(rows))
        for col, row in zip(cols, rows):
            with col:
                st.markdown(flow_card_html(row), unsafe_allow_html=True)
