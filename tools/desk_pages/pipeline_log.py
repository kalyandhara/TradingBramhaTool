"""Pipeline Log page — extracted from dashboard_app.py (B-87r)."""
from __future__ import annotations

import streamlit as st
import screener_pipeline as sp


def render() -> None:
    st.subheader("Pipeline Log")
    st.caption(f"Tail of {sp.LOG_FILE}")
    if sp.LOG_FILE.exists():
        lines = sp.LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
        st.code("\n".join(lines[-200:]), language=None)
    else:
        st.info("No log file yet — run the pipeline at least once.")
