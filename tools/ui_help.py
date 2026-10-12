#!/usr/bin/env python3
"""
ui_help.py - Beginner-friendly help components for Streamlit.

Provides reusable UI components to add info icons with explanations
for technical terms throughout the dashboard.
"""

import streamlit as st
from trading_glossary import (
    get_definition,
    search_terms,
    get_terms_by_category,
    get_all_categories,
    generate_tooltip,
    generate_detailed_tooltip,
)


def info_icon(term: str, icon: str = "ℹ️", size: str = "16px") -> str:
    """
    Display an info icon with a simple tooltip explanation.
    
    Args:
        term: The technical term to explain
        icon: Icon to use (default: ℹ️)
        size: Icon size in pixels (default: 16px)
    
    Returns:
        HTML string with tooltip
    """
    defn = get_definition(term)
    if not defn:
        return f'<span style="font-size:{size};">{icon}</span>'
    
    return f"""
    <span style="cursor:help; border-bottom: 1px dotted #666; font-size:{size};"
          title="{defn.definition}">
        {icon}
    </span>
    """


def info_button(term: str, label: str = "What's this?") -> None:
    """
    Display a button that shows term explanation in an expander when clicked.
    
    Args:
        term: The technical term to explain
        label: Button label (default: "What's this?")
    """
    defn = get_definition(term)
    if not defn:
        st.warning(f"Term '{term}' not found in glossary")
        return
    
    with st.expander(label, expanded=False):
        st.markdown(f"**{defn.term}** ({defn.category})")
        st.markdown(f"*{defn.definition}*")
        st.markdown("---")
        st.markdown("**Technical Detail:**")
        st.markdown(defn.technical_detail)
        st.markdown("**Example:**")
        st.markdown(f"> {defn.example}")
        
        if defn.related_terms:
            st.markdown("**Related Terms:**")
            related = ", ".join([f"`{t}`" for t in defn.related_terms])
            st.markdown(related)


def info_card(term: str) -> None:
    """
    Display a formatted info card with full term explanation.
    
    Args:
        term: The technical term to explain
    """
    defn = get_definition(term)
    if not defn:
        st.warning(f"Term '{term}' not found in glossary")
        return
    
    st.markdown(f"""
    <div style="background:#f8f9fa; border-left:4px solid #ea580c; padding:15px; 
                border-radius:5px; margin:10px 0;">
        <strong>{defn.term}</strong><br/>
        <em style="color:#666;">{defn.category}</em><br/><br/>
        <b>Simple Explanation:</b><br/>
        {defn.definition}<br/><br/>
        <b>Technical Detail:</b><br/>
        {defn.technical_detail}<br/><br/>
        <b>Example:</b><br/>
        <span style="color:#666; font-style:italic;">{defn.example}</span>
    </div>
    """, unsafe_allow_html=True)


def labeled_field(label: str, term: str | None = None, value: str = "") -> None:
    """
    Display a labeled field with optional info icon.
    
    Args:
        label: Field label
        term: Technical term to explain (optional)
        value: Field value to display
    """
    cols = st.columns([3, 1])
    with cols[0]:
        if term:
            tooltip = info_icon(term)
            st.markdown(f"{label} {tooltip}", unsafe_allow_html=True)
        else:
            st.markdown(label)
    with cols[1]:
        st.markdown(f"**{value}**")


def scanner_help(scanner_name: str) -> None:
    """
    Display help for a specific scanner.
    
    Args:
        scanner_name: Name of the scanner
    """
    from scanner_templates import SCANNERS
    
    if scanner_name not in SCANNERS:
        st.warning(f"Scanner '{scanner_name}' not found")
        return
    
    scanner_info = SCANNERS[scanner_name]
    category = scanner_info.get("category", "Unknown")
    description = scanner_info.get("description", "No description available")
    
    st.markdown(f"**{scanner_name}**")
    st.caption(f"Category: {category}")
    st.markdown(description)
    
    # Show category explanation if available
    category_term = f"{category} Scanner"
    if get_definition(category_term):
        st.markdown("---")
        info_card(category_term)


def glossary_search() -> None:
    """
    Display a searchable glossary component.
    """
    st.subheader("Trading Glossary")
    
    search_query = st.text_input("Search for a term...", placeholder="e.g., RSI, VCP, Support")
    
    if search_query:
        matches = search_terms(search_query)
        if matches:
            st.write(f"Found {len(matches)} matching terms:")
            for term in matches:
                with st.expander(term):
                    info_card(term)
        else:
            st.info("No matching terms found")
    else:
        # Show all categories
        st.write("Browse by category:")
        for category in get_all_categories():
            with st.expander(f"{category} ({len(get_terms_by_category(category))} terms)"):
                for term in get_terms_by_category(category):
                    st.markdown(f"- **{term}**")


def tooltip_label(text: str, term: str) -> str:
    """
    Wrap text with a tooltip for a technical term.
    
    Args:
        text: The text to display
        term: The technical term to explain
    
    Returns:
        HTML string with tooltip
    """
    tooltip = info_icon(term)
    return f"{text} {tooltip}"


def column_with_help(column_name: str, term: str | None = None) -> str:
    """
    Generate a column name with optional help icon.
    
    Args:
        column_name: The column header
        term: Technical term to explain (optional)
    
    Returns:
        Column name with help icon
    """
    if term:
        return f"{column_name} {info_icon(term)}"
    return column_name


def beginner_mode_toggle() -> bool:
    """
    Display a toggle for beginner mode.
    
    Returns:
        True if beginner mode is enabled
    """
    if "beginner_mode" not in st.session_state:
        st.session_state.beginner_mode = True
    
    beginner_mode = st.toggle(
        "🎓 Beginner Mode",
        value=st.session_state.beginner_mode,
        help="Show explanations for technical terms",
    )
    st.session_state.beginner_mode = beginner_mode
    
    return beginner_mode


def explain_metric(label: str, value: str | float, term: str | None = None) -> None:
    """
    Display a metric with optional explanation.
    
    Args:
        label: Metric label
        value: Metric value
        term: Technical term to explain (optional)
    """
    if term and st.session_state.get("beginner_mode", True):
        with st.container():
            cols = st.columns([4, 1])
            with cols[0]:
                st.metric(label, value)
            with cols[1]:
                st.markdown(info_icon(term), unsafe_allow_html=True)
    else:
        st.metric(label, value)


def explain_parameter(param_name: str, term: str, default_value: any) -> any:
    """
    Display a parameter input with explanation.
    
    Args:
        param_name: Parameter name
        term: Technical term to explain
        default_value: Default parameter value
    
    Returns:
        User input value
    """
    if st.session_state.get("beginner_mode", True):
        with st.container():
            cols = st.columns([3, 1])
            with cols[0]:
                value = st.number_input(param_name, value=default_value)
            with cols[1]:
                st.markdown(info_icon(term), unsafe_allow_html=True)
        return value
    else:
        return st.number_input(param_name, value=default_value)


def batch_explain_terms(terms: list[str]) -> None:
    """
    Display explanations for multiple terms in a compact format.
    
    Args:
        terms: List of terms to explain
    """
    for term in terms:
        defn = get_definition(term)
        if defn:
            with st.expander(f"{term}"):
                st.markdown(f"*{defn.definition}*")
                st.caption(f"Technical: {defn.technical_detail[:100]}...")


def quick_reference() -> None:
    """
    Display a quick reference card with common terms.
    """
    common_terms = [
        "VCP",
        "RSI",
        "EMA",
        "Support",
        "Resistance",
        "Stop-loss",
        "Risk-Reward Ratio",
        "Volume",
        "Confluence",
    ]
    
    st.subheader("Quick Reference")
    
    cols = st.columns(3)
    for i, term in enumerate(common_terms):
        with cols[i % 3]:
            defn = get_definition(term)
            if defn:
                st.markdown(f"**{term}**")
                st.caption(defn.definition[:80] + "...")


# ── Streamlit Component Wrappers ───────────────────────────────────────────────

def st_info_help(term: str, icon: str = "ℹ️") -> None:
    """
    Streamlit component wrapper for info icon with expander.
    
    Usage:
        st_info_help("VCP")
    """
    info_button(term, f"{icon} Explain")


def st_tooltip(text: str, term: str) -> None:
    """
    Streamlit component wrapper for tooltip text.
    
    Usage:
        st_tooltip("Price is above EMA21", "EMA")
    """
    tooltip_html = tooltip_label(text, term)
    st.markdown(tooltip_html, unsafe_allow_html=True)


def st_glossary_sidebar() -> None:
    """
    Add glossary search to sidebar.
    """
    with st.sidebar:
        st.divider()
        st.subheader("📚 Glossary")
        
        search_query = st.text_input("Search terms...", key="glossary_search")
        
        if search_query:
            matches = search_terms(search_query)
            if matches:
                for term in matches[:5]:  # Show top 5 matches
                    with st.expander(term):
                        defn = get_definition(term)
                        if defn:
                            st.markdown(defn.definition)
            else:
                st.caption("No matches")
        
        if st.button("Full Glossary", key="full_glossary_btn"):
            st.session_state.show_glossary = True


# ── CSS for Tooltips ───────────────────────────────────────────────────────────

TOOLTIP_CSS = """
<style>
.tooltip {
    position: relative;
    display: inline-block;
    cursor: help;
    border-bottom: 1px dotted #666;
}

.tooltip .tooltiptext {
    visibility: hidden;
    width: 300px;
    background-color: #333;
    color: #fff;
    text-align: left;
    border-radius: 6px;
    padding: 10px;
    position: absolute;
    z-index: 1000;
    bottom: 125%;
    left: 50%;
    margin-left: -150px;
    opacity: 0;
    transition: opacity 0.3s;
    font-size: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
}

.tooltip:hover .tooltiptext {
    visibility: visible;
    opacity: 1;
}
</style>
"""


def inject_tooltip_css() -> None:
    """Inject tooltip CSS into the page."""
    st.markdown(TOOLTIP_CSS, unsafe_allow_html=True)


if __name__ == "__main__":
    # Test the components
    print("UI Help module loaded successfully!")
    print("Available functions:")
    print("- info_icon(term)")
    print("- info_button(term)")
    print("- info_card(term)")
    print("- glossary_search()")
    print("- beginner_mode_toggle()")
