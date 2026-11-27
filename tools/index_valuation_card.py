"""index_valuation_card.py — the Streamlit surface for B-145 (kept out of the monolith)."""
from __future__ import annotations

import streamlit as st

import index_valuation as iv
import report_style as rs


def render() -> None:
    s = iv.summary("Nifty 50")
    if s is None:
        return
    st.markdown(rs.section("Index valuation (Nifty 50)"), unsafe_allow_html=True)
    cols = st.columns(3)
    for col, (k, label, fmt) in zip(cols, (("pe", "P/E", "{:.1f}×"), ("pb", "P/B", "{:.2f}×"),
                                           ("dy", "Dividend yield", "{:.2f}%"))):
        m = s.get(k)
        col.markdown(rs.stat_card(label, fmt.format(m["value"]) if m else None,
                                  f"{m['min']:.2f}–{m['max']:.2f} over {s['months']:.0f} mo" if m else None),
                     unsafe_allow_html=True)
    st.caption(iv.caption(s))
