"""Glossary — a learning path through the desk's vocabulary, not an A–Z dump.

Tooltips explain one term at the moment you meet it. They cannot teach the ORDER
in which the ideas depend on each other, which is what a beginner is missing. This
page does that: the categories are arranged from "what am I even looking at" to
"how the desk decides", each with a one-line reason to read it, and every term
shows its simple explanation, the technical detail and a worked example, with its
related terms listed so the reader can follow the thread.

Explanatory content only: definitions live in `trading_glossary.py`; nothing here
is measured or votes in anything.
"""
from __future__ import annotations

import streamlit as st

import trading_glossary as glossary
import ui_help as help  # noqa: A001 — same alias the dashboard uses

#: (category, why read it at this point). Order IS the lesson plan. Any category
#: the glossary gains later that is not listed here is appended, never dropped.
PATH: list[tuple[str, str]] = [
    ("Market",           "Start here: what the market as a whole is doing."),
    ("Market Structure", "How to read a price chart: floors, ceilings and trends."),
    ("Indicator",        "The standard measurements drawn on top of price."),
    ("Volume",           "Whether real money is behind a move."),
    ("Fundamental",      "The business behind the ticker: size, profit, ownership."),
    ("Risk",             "How much you can lose, and how to size and exit a trade."),
    ("Pattern",          "Named chart shapes and what they are said to imply."),
    ("Regime",           "Whether conditions favour taking risk today."),
    ("Scanner",          "The setups this desk searches for, one by one."),
    ("Scanner Category", "How the scanners are grouped."),
    ("Analysis",         "How the desk combines signals into a ranked shortlist."),
]


def _ordered_categories() -> list[tuple[str, str]]:
    have = set(glossary.get_all_categories())
    out = [(c, why) for c, why in PATH if c in have]
    listed = {c for c, _ in out}
    out += [(c, "") for c in sorted(have - listed)]
    return out


def _term_block(term: str) -> None:
    d = glossary.get_definition(term)
    if d is None:
        return
    st.markdown(f"#### {d.term}")
    st.markdown(d.definition)
    with st.expander("More detail and an example"):
        st.markdown(f"**Technical detail.** {d.technical_detail}")
        st.markdown(f"**Example.** {d.example}")
    known = [r for r in d.related_terms if glossary.get_definition(r)]
    if known:
        st.caption("See also: " + " · ".join(known))


def render() -> None:
    st.subheader("Glossary")
    st.caption("A guided tour of the terms this desk uses, in the order they build on each other.")

    cats = _ordered_categories()
    total = sum(len(glossary.get_terms_by_category(c)) for c, _ in cats)

    q = st.text_input("Search for a term", placeholder="e.g. RSI, stop-loss, breadth",
                      key="glossary_page_search")
    if q.strip():
        hits = glossary.search_terms(q.strip())
        if not hits:
            st.info("No matching terms. Try a shorter word.")
            return
        st.write(f"{len(hits)} matching term(s)")
        for t in hits:
            _term_block(t)
            st.divider()
        return

    st.markdown(f"{total} terms in {len(cats)} sections. Read top to bottom the first time; "
                "use search afterwards.")
    mode = st.radio("View", ["Learning path", "A–Z"], horizontal=True,
                    key="glossary_page_view", label_visibility="collapsed")

    if mode == "A–Z":
        for t in sorted(sum((glossary.get_terms_by_category(c) for c, _ in cats), [])):
            _term_block(t)
            st.divider()
        return

    for n, (cat, why) in enumerate(cats, 1):
        terms = glossary.get_terms_by_category(cat)
        with st.expander(f"{n}. {cat}  ({len(terms)} terms)", expanded=(n == 1)):
            if why:
                st.markdown(f"*{why}*")
            for t in terms:
                _term_block(t)
                st.divider()
