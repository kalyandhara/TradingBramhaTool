"""FR-0 — shared style primitive for the dashboard's HTML surfaces.

Why this module exists
----------------------
dashboard_app.py has 19 `unsafe_allow_html` sites and every one of them
hard-codes its own hexes inline, so the same "card" or "chip" is re-invented
with slightly different padding and colour each time. The deep-dive report
(Fundamental-Deep-Dive-Report-Roadmap) is ~6 recipes reused ~40 times, which
would have made that worse. One token block plus six helpers is the difference
between the page looking designed and looking assembled.

Palette decision (recorded in the roadmap's design audit)
---------------------------------------------------------
The mockup that inspired the report is dark editorial (page ≈#0b0e14, gold,
mono figures) — which is the **chart tool's** theme, not this one. The Streamlit
dashboard is cream/brown (#fff8e1, #f7efe3, #fde0c0, #8d6e63). Porting the dark
skin here would clash with every existing card, so what carries over is the
*structure and the semantic roles*, mapped onto the hues already in use:

    accent / caution   amber-brown  (was gold)      — section dots, watch states
    good / confirmed   green                        — clean metrics, ▲ YoY
    risk / stretched   red                          — flags, ▼ YoY
    informational      blue                         — classification chips
    absent / muted     warm grey                    — micro-labels, DATA N/A

Two rules from the source design are worth keeping and are honoured by the
helpers below:
  * **A value's colour states its verdict** — P/E 95× is amber *because* it is
    stretched; D/E 0.02× is green *because* it is clean. Callers pass a tone.
  * **Border colour and weight encode emphasis** — hairline = normal card,
    2px accent = highest emphasis, coloured = a stated verdict.

The helpers return HTML strings and never import Streamlit, so they are
testable on their own and usable from any surface that can render HTML.
"""

from __future__ import annotations

from typing import Iterable

# ──────────────────────────────────────────────────────────────────────────────
# Tokens — the dashboard's existing hues, named by role
# ──────────────────────────────────────────────────────────────────────────────
TOKENS = {
    # surfaces
    "surface":     "#fffdf8",
    "surface_alt": "#f7efe3",
    "surface_warm": "#fff8e1",
    "border":      "#f0e0cc",
    "border_strong": "#e5cfae",
    # text
    "text":        "#3a2a1e",
    "text_body":   "#5c4a3a",
    "text_muted":  "#9a8778",
    # semantic roles
    "accent":      "#d97706",   # caution / watch / primary accent
    "accent_soft": "#fde0c0",
    "good":        "#16a34a",
    "good_soft":   "#e8f5e9",
    "risk":        "#dc2626",
    "risk_soft":   "#fef2f2",
    "info":        "#2563eb",
    "info_soft":   "#eef4ff",
    "absent":      "#9ca3af",
    "absent_soft": "#f3f4f6",
}

# tone -> (foreground, tint) used by chip/stat_card/callout
_TONE = {
    "good":    (TOKENS["good"],   TOKENS["good_soft"]),
    "risk":    (TOKENS["risk"],   TOKENS["risk_soft"]),
    "warn":    (TOKENS["accent"], TOKENS["accent_soft"]),
    "info":    (TOKENS["info"],   TOKENS["info_soft"]),
    "absent":  (TOKENS["absent"], TOKENS["absent_soft"]),
    "neutral": (TOKENS["text_body"], TOKENS["surface_alt"]),
}

MONO = "'Roboto Mono','Courier New',ui-monospace,monospace"

#: Rendered when a value has no source. Never substitute a neutral number —
#: a missing axis must render missing (the roadmap's core honesty device).
NA = "DATA N/A"


def tone_colors(tone: str) -> tuple[str, str]:
    """(foreground, tint) for a semantic tone; unknown tones read as neutral."""
    return _TONE.get(tone, _TONE["neutral"])


def report_css() -> str:
    """The one <style> block. Inject once per page before any helper output."""
    t = TOKENS
    return f"""
<style>
:root {{
  --tb-surface: {t['surface']};      --tb-surface-alt: {t['surface_alt']};
  --tb-surface-warm: {t['surface_warm']};
  --tb-border: {t['border']};        --tb-border-strong: {t['border_strong']};
  --tb-text: {t['text']};            --tb-text-body: {t['text_body']};
  --tb-text-muted: {t['text_muted']};
  --tb-accent: {t['accent']};        --tb-good: {t['good']};
  --tb-risk: {t['risk']};            --tb-info: {t['info']};
  --tb-absent: {t['absent']};
  --tb-mono: {MONO};
}}
/* Micro-label: uppercase, letter-spaced, muted — names a figure without
   competing with it. */
.tb-micro {{
  font-size:10px; letter-spacing:.08em; text-transform:uppercase;
  color:var(--tb-text-muted); font-weight:600;
}}
/* Every figure is monospace so columns of numbers line up and digits do not
   reflow as values change. */
.tb-mono {{ font-family:var(--tb-mono); font-variant-numeric:tabular-nums; }}
/* Section header: a small accent dot, then an uppercase letter-spaced label. */
.tb-sec {{
  display:flex; align-items:center; gap:7px; margin:16px 0 8px 0;
  font-size:11px; letter-spacing:.09em; text-transform:uppercase;
  color:var(--tb-text-muted); font-weight:700;
}}
.tb-sec::before {{
  content:""; width:6px; height:6px; border-radius:50%;
  background:var(--tb-accent); flex-shrink:0;
}}
.tb-card {{
  background:var(--tb-surface); border:1px solid var(--tb-border);
  border-radius:11px; padding:14px 16px; margin:0 0 10px 0;
}}
.tb-card.tb-emph {{ border-width:2px; border-color:var(--tb-accent); }}
.tb-card-title {{ font-size:12px; font-weight:700; color:var(--tb-text); margin-bottom:6px; }}
.tb-chip {{
  display:inline-block; border-radius:99px; padding:2px 10px;
  margin:0 6px 5px 0; font-size:11px; font-weight:600; white-space:nowrap;
}}
/* Stat card: micro-label above, big mono value below, optional delta line. */
.tb-stat {{
  background:var(--tb-surface); border:1px solid var(--tb-border);
  border-radius:9px; padding:9px 11px; min-width:0;
}}
.tb-stat-val {{ font-family:var(--tb-mono); font-size:17px; font-weight:700; line-height:1.25; }}
.tb-stat-sub {{ font-size:10.5px; margin-top:2px; }}
.tb-strip {{ display:grid; gap:8px; margin:6px 0 4px 0; }}
/* Proportional bar with its value set inside the fill. */
.tb-bar-track {{
  background:var(--tb-surface-alt); border-radius:5px; height:22px;
  overflow:hidden; margin-top:3px;
}}
.tb-bar-fill {{
  height:100%; display:flex; align-items:center; padding:0 8px;
  font-family:var(--tb-mono); font-size:11px; font-weight:700; color:#fff;
  white-space:nowrap;
}}
/* Callout: 3px accent rail, bold coloured lead-in, muted body. */
.tb-callout {{
  border-left:3px solid var(--tb-accent); background:var(--tb-surface-alt);
  border-radius:0 7px 7px 0; padding:8px 12px; margin:6px 0;
  font-size:12.5px; color:var(--tb-text-body); line-height:1.5;
}}
.tb-na {{ color:var(--tb-absent); font-style:italic; }}
</style>
"""


# ──────────────────────────────────────────────────────────────────────────────
# The six helpers
# ──────────────────────────────────────────────────────────────────────────────
def card(body: str, title: str | None = None, emphasis: bool = False,
         tone: str | None = None) -> str:
    """Container. `emphasis` = 2px accent border (highest emphasis, use once per
    screen); `tone` colours the border to state a verdict."""
    cls = "tb-card tb-emph" if emphasis else "tb-card"
    style = ""
    if tone and not emphasis:
        fg, _ = tone_colors(tone)
        style = f' style="border-color:{fg};"'
    head = f'<div class="tb-card-title">{title}</div>' if title else ""
    return f'<div class="{cls}"{style}>{head}{body}</div>'


def chip(label: str, tone: str = "neutral", value: str | None = None) -> str:
    """Pill. Two uses: classification (sector, cap band) and verdict
    (`Entry: OVERVALUED`). The tone *is* the message, so pick it deliberately."""
    fg, bg = tone_colors(tone)
    inner = (f'<span style="opacity:.75;font-weight:500;">{label}</span> '
             f'<span class="tb-mono">{value}</span>') if value is not None else label
    return (f'<span class="tb-chip" style="background:{bg};color:{fg};'
            f'border:1px solid {fg}33;">{inner}</span>')


def stat_card(label: str, value: str | None, sub: str | None = None,
              tone: str = "neutral") -> str:
    """One metric for the strip. `value=None` renders DATA N/A in muted italic
    rather than a dash that could be mistaken for zero."""
    fg, _ = tone_colors(tone)
    if value is None:
        val_html = f'<div class="tb-stat-val tb-na">{NA}</div>'
    else:
        val_html = f'<div class="tb-stat-val" style="color:{fg};">{value}</div>'
    sub_html = (f'<div class="tb-stat-sub" style="color:{TOKENS["text_muted"]};">{sub}</div>'
                if sub else "")
    return (f'<div class="tb-stat"><div class="tb-micro">{label}</div>'
            f'{val_html}{sub_html}</div>')


def strip(cards: Iterable[str], cols: int = 5) -> str:
    """Lay stat cards out in a responsive grid."""
    return (f'<div class="tb-strip" style="grid-template-columns:repeat({cols},1fr);">'
            f'{"".join(cards)}</div>')


def bar_row(label: str, value_text: str, pct: float, tone: str = "info",
            right: str | None = None, footnote: str | None = None) -> str:
    """Proportional bar with the value inside the fill and the derivation under
    it. `pct` is width 0-100; it is clamped so a runaway value cannot overflow."""
    fg, _ = tone_colors(tone)
    w = max(0.0, min(100.0, float(pct)))
    right_html = (f'<span style="float:right;color:{TOKENS["text_muted"]};'
                  f'font-size:11px;">{right}</span>') if right else ""
    foot = (f'<div style="font-size:10.5px;color:{TOKENS["text_muted"]};'
            f'margin-top:3px;">{footnote}</div>') if footnote else ""
    return (f'<div style="margin:8px 0;">'
            f'<div style="font-size:11.5px;font-weight:700;color:{fg};">{label}{right_html}</div>'
            f'<div class="tb-bar-track"><div class="tb-bar-fill" '
            f'style="width:{w:.1f}%;background:{fg};">{value_text}</div></div>{foot}</div>')


def callout(lead: str, body: str, tone: str = "warn") -> str:
    """Accent-railed panel: bold coloured lead-in, then muted body."""
    fg, bg = tone_colors(tone)
    return (f'<div class="tb-callout" style="border-left-color:{fg};background:{bg};">'
            f'<b style="color:{fg};">{lead}</b> {body}</div>')


def donut(value: str | None, caption: str, verdict: str | None = None,
          pct: float | None = None, tone: str = "neutral", size: int = 76) -> str:
    """Inline-SVG arc. No plotting dependency — this is a dial, not a chart.

    `pct` fills the arc 0-100. When `value` is None the arc renders as a faint
    absent-coloured track with a DATA N/A caption: a missing axis must look
    missing rather than resolve to a neutral middle.
    """
    fg, _ = tone_colors("absent" if value is None else tone)
    r = size / 2 - 7
    circ = 2 * 3.14159265 * r
    frac = 0.0 if (value is None or pct is None) else max(0.0, min(100.0, pct)) / 100
    dash = circ * frac
    centre = "" if value is None else (
        f'<text x="50%" y="52%" text-anchor="middle" dominant-baseline="middle" '
        f'font-family="{MONO}" font-size="15" font-weight="700" fill="{fg}">{value}</text>')
    verdict_html = (f'<div style="font-size:11px;font-weight:700;color:{fg};'
                    f'margin-top:2px;">{verdict}</div>') if verdict else ""
    na_html = ("" if value is not None else
               f'<div class="tb-na" style="font-size:11px;margin-top:2px;">{NA}</div>')
    return (
        f'<div style="text-align:center;">'
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        f'<circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" '
        f'stroke="{TOKENS["surface_alt"]}" stroke-width="6"/>'
        f'<circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="{fg}" '
        f'stroke-width="6" stroke-linecap="round" '
        f'stroke-dasharray="{dash:.2f} {circ:.2f}" '
        f'transform="rotate(-90 {size/2} {size/2})"/>'
        f'{centre}</svg>'
        f'{verdict_html}{na_html}'
        f'<div class="tb-micro" style="margin-top:3px;">{caption}</div></div>'
    )


def section(title: str) -> str:
    """`• SECTION NAME` header."""
    return f'<div class="tb-sec">{title}</div>'
