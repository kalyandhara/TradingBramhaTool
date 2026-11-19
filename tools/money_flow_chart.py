"""Ridgeline of daily sector money flow (CMF 21) over the last month.

One ridge per sector, strongest inflow today on top: green above its zero line,
red below, today's reading printed at the right. Data from
`money_flow.ridge_rows`; the drawing is all here so the monolith only calls it.
Where money went, not where it will go — nothing here is measured.
"""
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

import money_flow as mf

ROW_PX = 34          # height per ridge
AMPLITUDE = 0.85     # a reading at the clip edge reaches 0.85 rows: inflows and
                     # outflows both grow from the line, so more would merge rows


def _rgba(hex_colour: str, alpha: float) -> str:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def ridgeline(grid: dict[str, Any], tokens: dict[str, str]) -> go.Figure | None:
    """The figure, or None when the stored run carries no daily series."""
    rows = mf.ridge_rows(grid)
    dates = grid.get("series_dates") or []
    if not rows or not dates:
        return None
    clip = float(grid.get("clip", mf.HEAT_CLIP))
    k = AMPLITUDE / clip
    good, risk, muted = tokens["good"], tokens["risk"], tokens["text_muted"]
    n = len(rows)
    fig = go.Figure()
    for i, r in enumerate(rows):
        y0 = float(n - 1 - i)
        vals = r["values"][-len(dates):]
        x = dates[-len(vals):]
        base = [y0] * len(x)
        pos = [y0 + max(v or 0.0, 0.0) * k for v in vals]
        neg = [y0 + min(v or 0.0, 0.0) * k for v in vals]
        real = ["—" if v is None else f"{v:+.3f}" for v in vals]
        tip = (f"<b>{r['sector']}</b><br>%{{x}} · CMF %{{customdata}}"
               f"<br>{r['members']} stocks"
               + (" · low coverage" if r["low_coverage"] else "") + "<extra></extra>")
        for side, colour in ((pos, good), (neg, risk)):
            fig.add_trace(go.Scatter(x=x, y=base, mode="lines", hoverinfo="skip",
                                     line=dict(color=_rgba(muted, 0.35), width=0.6),
                                     showlegend=False))
            fig.add_trace(go.Scatter(x=x, y=side, mode="lines", fill="tonexty",
                                     fillcolor=_rgba(colour, 0.35),
                                     line=dict(color=colour, width=1.2),
                                     customdata=real, hovertemplate=tip,
                                     showlegend=False))
        t = r["today"]
        fig.add_annotation(x=1.0, xref="paper", xanchor="left", y=y0, yref="y",
                           text="—" if t is None else f"{t:+.3f}", showarrow=False,
                           font=dict(size=11, color=muted if t is None
                                     else good if t > 0 else risk))
    fig.update_layout(
        height=ROW_PX * n + 60, margin=dict(l=8, r=52, t=8, b=28),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hovermode="closest", font=dict(size=11, color=tokens["text"]),
        xaxis=dict(showgrid=False, tickformat="%d %b", nticks=5,
                   linecolor=_rgba(muted, 0.4)),
        yaxis=dict(tickvals=[float(n - 1 - i) for i in range(n)],
                   ticktext=[r["sector"] if len(r["sector"]) <= 26
                             else r["sector"][:25] + "…" for r in rows],
                   showgrid=False, zeroline=False,
                   range=[-AMPLITUDE - 0.1, n - 1 + AMPLITUDE + 0.1]),
    )
    return fig
