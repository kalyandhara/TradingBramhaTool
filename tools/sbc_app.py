#!/usr/bin/env python3
"""
sbc_app.py — Sarvatobhadra Chakra market-timing dashboard (Streamlit).

Run:
  py -3 -m streamlit run tools/sbc_app.py

Panels (top to bottom):
  1. Header + live market bias gauge (malefic vs benefic vedas)
  2. Planetary placement table (nakshatra, pada, retrograde, nature)
  3. 9x9 SBC grid with color-coded veda-struck cells
  4. Sector scoreboard (nama-nakshatra bull/bear)
  5. Reversal-window timeline for the session

Educational tool. Not investment advice. See the disclaimer in the footer.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import streamlit as st

from sarvatobhadra_chakra import (
    NAKSHATRAS, PLANET_GLYPH, IST_OFFSET, compute_planets,
)
from sbc_scoring import (
    cast_vedas, market_bias, sector_scores, moon_reversal_windows,
    SECTOR_NAKSHATRA,
)

st.set_page_config(page_title="Sarvatobhadra Chakra",
                   page_icon="✦", layout="wide")

# --- palette ---------------------------------------------------------------
GOLD = "#d9b45b"
BG = "#0d0b1f"
PANEL = "#171334"
RED = "#e0524f"
GREEN = "#3fb57a"
DIM = "#6c6790"

st.markdown(f"""
<style>
.stApp {{ background:{BG}; }}
.sbc-title {{ font-family:'Cinzel',Georgia,serif; color:{GOLD};
  text-align:center; font-size:2.4rem; letter-spacing:.15em;
  margin:.2rem 0 0 0; }}
.sbc-sub {{ text-align:center; color:{DIM}; letter-spacing:.35em;
  font-size:.72rem; margin-bottom:1.2rem; }}
.sbc-panel {{ background:{PANEL}; border:1px solid #2a2550;
  border-radius:12px; padding:1rem 1.2rem; margin-bottom:1rem; }}
.sbc-h {{ color:{GOLD}; letter-spacing:.12em; font-size:.85rem;
  text-transform:uppercase; margin-bottom:.6rem; }}
.cell {{ display:inline-flex; align-items:center; justify-content:center;
  width:100%; aspect-ratio:1/1; border-radius:6px; font-size:.62rem;
  border:1px solid #2a2550; color:#cfc9f0; text-align:center;
  padding:2px; line-height:1.05; }}
.badge {{ padding:.15rem .55rem; border-radius:999px; font-size:.72rem;
  font-weight:600; }}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="sbc-title">SARVATOBHADRA CHAKRA</div>',
            unsafe_allow_html=True)
st.markdown('<div class="sbc-sub">VEDIC NAKSHATRA GRID &middot; VEDA BIAS '
            '&middot; REVERSAL WINDOWS</div>', unsafe_allow_html=True)

# --- controls --------------------------------------------------------------
c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    sel_date = st.date_input("Session date", value=date.today())
with c2:
    gran = st.selectbox("Reversal granularity", ["pada", "nakshatra"], index=0)
with c3:
    st.caption("Positions use PyEphem + Lahiri ayanamsa. Bias = weighted "
               "malefic vs benefic vedas across the live grid.")

now_utc = datetime.utcnow()
planets = compute_planets(now_utc)
vedas = cast_vedas(planets)
bias = market_bias(vedas)

# --- bias banner -----------------------------------------------------------
bias_color = {"BEARISH": RED, "BULLISH": GREEN, "MIXED": GOLD}[bias.label]
st.markdown(f"""
<div class="sbc-panel" style="text-align:center;">
  <span class="sbc-h">Market Bias</span><br>
  <span style="font-size:2rem;color:{bias_color};font-weight:700;">
    {bias.label}</span>
  <span style="color:{DIM};"> &nbsp; net {bias.net:+.3f}</span><br>
  <span style="color:{RED};">malefic {bias.malefic_score}</span> &nbsp;|&nbsp;
  <span style="color:{GREEN};">benefic {bias.benefic_score}</span>
</div>
""", unsafe_allow_html=True)

# --- planet table + reversal windows side by side --------------------------
left, right = st.columns([3, 2])

with left:
    st.markdown('<div class="sbc-h">Planetary Placement</div>',
                unsafe_allow_html=True)
    rows = []
    for name, ps in planets.items():
        rows.append({
            "Planet": f"{PLANET_GLYPH.get(name,'')} {name}",
            "Nakshatra": ps.nakshatra,
            "Pada": ps.pada,
            "Sidereal": f"{ps.sidereal_lon:.2f}°",
            "Motion": "Rx" if ps.retrograde else "D",
            "Nature": ps.nature,
        })
    st.dataframe(rows, hide_index=True, use_container_width=True)

with right:
    st.markdown('<div class="sbc-h">Reversal Windows (IST)</div>',
                unsafe_allow_html=True)
    windows = moon_reversal_windows(sel_date, granularity=gran)
    now_ist = datetime.utcnow() + IST_OFFSET
    if not windows:
        st.caption("No Moon boundary crossings in range.")
    for w in windows:
        live = w.start_ist <= now_ist <= w.end_ist
        edge = GOLD if live else "#2a2550"
        tag = " &nbsp;<b style='color:%s'>&#9679; LIVE</b>" % GOLD if live else ""
        st.markdown(f"""
        <div style="border:1px solid {edge};border-radius:8px;
          padding:.5rem .7rem;margin-bottom:.4rem;background:#120f2b;">
          <b style="color:{GOLD};">{w.start_ist:%H:%M}&ndash;{w.end_ist:%H:%M}</b>
          {tag}<br>
          <span style="color:{DIM};font-size:.78rem;">
          {w.from_nakshatra} &rarr; {w.to_nakshatra}</span>
        </div>""", unsafe_allow_html=True)

# --- SBC grid --------------------------------------------------------------
st.markdown('<div class="sbc-h">Sarvatobhadra Grid (27 Nakshatras)</div>',
            unsafe_allow_html=True)

# net veda pressure per nakshatra index
pressure = {i: 0.0 for i in range(27)}
occupant = {i: [] for i in range(27)}
for v in vedas:
    pressure[v.target_index] += (v.weight if v.nature == "benefic"
                                 else -v.weight)
for name, ps in planets.items():
    occupant[ps.nakshatra_index].append(PLANET_GLYPH.get(name, name[0]))

def cell_color(p: float) -> str:
    if p >= 1.0:
        return "#123d29"
    if p > 0:
        return "#16261f"
    if p <= -1.0:
        return "#3d1717"
    if p < 0:
        return "#261414"
    return "#171334"

# render as a 3-row x 9-col flow (27 cells) — compact and readable
for r in range(3):
    cols = st.columns(9)
    for c in range(9):
        idx = r * 9 + c
        nak = NAKSHATRAS[idx]
        p = pressure[idx]
        occ = "".join(occupant[idx])
        border = GOLD if occ else "#2a2550"
        with cols[c]:
            st.markdown(f"""
            <div class="cell" style="background:{cell_color(p)};
              border-color:{border};">
              <div><b style="color:{GOLD};">{occ}</b><br>
              {nak[:9]}<br>
              <span style="color:{DIM};">{p:+.1f}</span></div>
            </div>""", unsafe_allow_html=True)

st.caption("Gold border = planet-occupied nakshatra. Green = net benefic "
           "veda pressure, red = net malefic. Number = weighted net.")

# --- sector scoreboard -----------------------------------------------------
st.markdown('<div class="sbc-h">Sector Scoreboard (Nama-Nakshatra)</div>',
            unsafe_allow_html=True)
scores = sector_scores(vedas)
sc_cols = st.columns(3)
for i, s in enumerate(scores):
    col = sc_cols[i % 3]
    scolor = {"BULLISH": GREEN, "BEARISH": RED, "NEUTRAL": GOLD}[s.label]
    planets_str = " ".join(PLANET_GLYPH.get(p, p) for p in s.hitting_planets)
    with col:
        st.markdown(f"""
        <div style="border:1px solid #2a2550;border-left:4px solid {scolor};
          border-radius:8px;padding:.5rem .7rem;margin-bottom:.5rem;
          background:#120f2b;">
          <b style="color:#cfc9f0;">{s.sector}</b>
          <span class="badge" style="background:{scolor}22;color:{scolor};
            float:right;">{s.label} {s.score:+.2f}</span><br>
          <span style="color:{DIM};font-size:.75rem;">{s.nakshatra}
            &nbsp; {planets_str}</span>
        </div>""", unsafe_allow_html=True)

# --- footer ----------------------------------------------------------------
st.markdown(f"""
<div class="sbc-panel" style="border-color:{RED};margin-top:1rem;">
<span style="color:{RED};font-weight:600;">EDUCATIONAL MODEL ONLY.</span>
<span style="color:{DIM};font-size:.82rem;">
Sarvatobhadra veda scoring is a deterministic model of the documented mechanic,
not classical-exact and not a certainty engine. Planetary timing is one input
among many. Never trade solely on astrological signals; use stops and position
sizing. Positions: PyEphem + Lahiri ayanamsa, computed at
{(now_utc + IST_OFFSET):%Y-%m-%d %H:%M} IST.
</span></div>
""", unsafe_allow_html=True)
