"""help_panels.py — the beginner-mode explainers, lifted out of dashboard_app.py.

Moved VERBATIM in behaviour from seven inline blocks plus the Glossary page:
same toggle keys, same expander titles, same terms in the same order. Only the
location changed, so the monolith line ratchet stops paying for ~100 lines of
what is really data (a title and a list of glossary terms per page).

Explanatory content only. Nothing here is measured, scored, or votes in
anything — the definitions live in `trading_glossary.py`.

Adding help to a page = one entry in `PANELS` and one `help_panels.render("<page>")`
call; no new block in the monolith.
"""
from __future__ import annotations

import streamlit as st

import trading_glossary as glossary
import ui_help as help  # noqa: A001 — same alias dashboard_app uses

#: page -> (toggle key, [(expander title, [term | "**markdown header**", ...]), ...])
#: A term that starts with "**" is rendered as a markdown line, not looked up.
PANELS: dict[str, tuple[str, list[tuple[str, list[str]]]]] = {
    "hidden_treasures": ("hidden_treasures_beginner_mode", [
        ("Understanding Hidden Treasures",
         ["Market Cap", "Promoter Holding", "FII/DII", "ROCE", "OPM", "D/E Ratio"]),
    ]),
    "stock_analyzer": ("stock_analyzer_beginner_mode", [
        ("Understanding Technical Indicators",
         ["RSI", "EMA", "SMA", "ADX", "ATR"]),
        ("Understanding Market Structure",
         ["Support", "Resistance", "Uptrend", "Downtrend"]),
    ]),
    "portfolio": ("portfolio_beginner_mode", [
        ("Understanding Portfolio Risk Management",
         ["Stop-loss", "Risk-Reward Ratio", "Position Sizing", "Drawdown", "Capital"]),
    ]),
    "opportunity_hub": ("opportunity_hub_beginner_mode", [
        ("Understanding the Funnel",
         ["Confluence", "Conviction", "**Regime Gate**:", "RISK-ON", "MIXED", "RISK-OFF"]),
    ]),
    "scanner_hub": ("scanner_hub_beginner_mode", [
        ("Understanding Scanner Categories",
         ["Entry Scanner", "Trend Scanner", "Risk Scanner", "Pattern Scanner"]),
    ]),
    "market_sentiment": ("market_sentiment_beginner_mode", [
        ("Understanding Market Sentiment",
         ["Breadth", "Advance-Decline Ratio", "VIX", "Regime", "RISK-ON", "RISK-OFF"]),
    ]),
}


def render(page: str) -> bool:
    """Draw the page's toggle and, when on, its explainer expanders."""
    key, sections = PANELS[page]
    beginner_mode = help.beginner_mode_toggle(key=key)
    if beginner_mode:
        for title, terms in sections:
            with st.expander(title, expanded=False):
                for term in terms:
                    if term.startswith("**"):
                        st.markdown(term)
                    else:
                        help.info_card(term)
    return beginner_mode


def glossary_page() -> None:
    """The searchable Glossary page (opened by the nav ribbon's Glossary button)."""
    st.subheader("Trading Glossary")
    st.caption("Beginner-friendly explanations for all technical terms")

    beginner_mode = help.beginner_mode_toggle(key="glossary_page_beginner_mode")

    help.glossary_search()

    st.divider()

    help.quick_reference()

    st.divider()

    st.subheader("Browse by Category")

    for category in glossary.get_all_categories():
        with st.expander(f"{category} ({len(glossary.get_terms_by_category(category))} terms)"):
            for term in glossary.get_terms_by_category(category):
                if beginner_mode:
                    help.info_card(term)
                else:
                    st.markdown(f"- **{term}**")

    if st.button("Back to Dashboard", key="glossary_back"):
        st.session_state["show_glossary"] = False
        st.rerun()
