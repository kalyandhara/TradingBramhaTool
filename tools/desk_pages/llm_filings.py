"""Stock Analyzer section: NSE filings read by the local LLM (filing_reader).

Shows what is already stored without calling the model; the button reads the
latest filings (about 5 s each with qwen3-4b). Every row keeps the link to the
primary document, and the section says plainly what was read (NSE's
one-paragraph filing text, not the PDF) and that the labels are unmeasured.
"""
from __future__ import annotations

import html

import pandas as pd
import streamlit as st

import filing_reader as fr
import local_llm as ll

_CHIP = {"positive": ":green-badge[positive]", "negative": ":red-badge[negative]",
         "neutral": ":gray-badge[neutral]"}


@st.cache_data(ttl=60, show_spinner=False)
def _status() -> dict:
    return ll.status()


def render(symbol: str, n: int = 8) -> None:
    sym = str(symbol or "").upper().replace(".NS", "")
    if not sym:
        return
    st.markdown("**Filings, read by a local LLM**")
    stt = _status()
    tag = f"{ll.DEFAULT_MODEL}@v{fr.PROMPT_V}"
    where = (f"LM Studio at {stt['base_url']}" if stt["ok"]
             else "no LM Studio server is answering (start its local server)")
    st.caption(f"{tag} · {where}. A small local model's reading of the one-paragraph "
               "text NSE carries with each filing — not the PDF. Labels are unmeasured: "
               "read the source before acting on any of them.")
    a, b = st.columns([1, 3])
    if a.button(f"Read latest {n}", key=f"llmf_{sym}", disabled=not stt["ok"]):
        with st.spinner("Reading filings with the local model…"):
            res = fr.read_recent(sym, n=n)
        if res["state"] != "OK":
            st.warning(f"{res['state']}: {res['note']}")
    reads = fr.load_reads(sym)
    reads = reads[reads["model"] == tag] if not reads.empty else reads
    if reads.empty:
        b.caption("Nothing read yet for this symbol.")
        return
    tone = reads["sentiment"].value_counts().to_dict()
    b.caption(" · ".join(f"{k} {tone.get(k, 0)}" for k in fr.SENTIMENTS)
              + f" across {len(reads)} filings read")
    for _, r in reads.head(n).iterrows():
        chip = _CHIP.get(r["sentiment"], ":orange-badge[unreadable]")
        link = f" · [source]({r['file']})" if isinstance(r["file"], str) and r["file"] else ""
        mat = f" · {r['materiality']}" if pd.notna(r["materiality"]) else ""
        st.markdown(f"{chip} **{r['an_date'] or '—'}** {html.escape(str(r['subject'] or ''))}"
                    f"{mat}{link}  \n{html.escape(str(r['summary'] or r['error'] or ''))}")
