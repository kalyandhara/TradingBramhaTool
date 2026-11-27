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
    "text_muted":  "#7a6858",
    # semantic roles
    # B-161 (2026-10-13): good/risk/accent/absent darkened so each reads at
    # >= 4.5:1 (WCAG AA) on every surface AND on its own *_soft tint. The old
    # 16a34a / d97706 / 9ca3af (hex) measured 3.24 / 3.13 / 2.50 on `surface`;
    # test_report_style_contrast.py pins the new values and bans the old ones.
    "accent":      "#a14a0b",   # caution / watch / primary accent
    "accent_soft": "#fde0c0",
    "good":        "#166534",
    "good_soft":   "#e8f5e9",
    "risk":        "#b91c1c",
    "risk_soft":   "#fef2f2",
    "info":        "#2563eb",
    "info_soft":   "#eef4ff",
    "absent":      "#636a75",   # still lighter than text_body: "no data"
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

# ──────────────────────────────────────────────────────────────────────────────
# Typography (UI-1) — two roles, no webfont
# ──────────────────────────────────────────────────────────────────────────────
# Until now nothing in this stack set a base family: every surface inherited
# Streamlit's stock face and Plotly's stock face, so the page read "classic" by
# default rather than by decision. These two constants are that decision, and
# `.streamlit/config.toml` points Streamlit's own widgets at the same pair so
# the injected HTML and the native chrome agree.
#
# Deliberately *not* Inter — this wiki records "purple-to-white gradient + Inter
# + 4 cards in a grid" as the tell of median AI output, and the cream/brown
# palette here is a stated aesthetic commitment worth not diluting.
#
# Deliberately no webfont link. The dashboard runs on localhost against local
# data; a Google Fonts request would add a network dependency and a flash of
# unstyled text on every Streamlit rerun, to install a face nobody asked for.
# Both stacks resolve to something installed on Windows 11.
SANS = ("'Segoe UI Variable Text','Segoe UI',system-ui,-apple-system,"
        "'Helvetica Neue',sans-serif")

# Order matters and it was wrong before: 'Roboto Mono' led, but it is not
# installed on Windows, so every figure on the dashboard fell through to
# Courier New — the most dated face in the stack was rendering the numbers the
# page is built around. Windows-native modern monos now win first.
MONO = ("ui-monospace,'Cascadia Mono','Segoe UI Mono',Consolas,"
        "'Roboto Mono','Courier New',monospace")

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
  --tb-font: {SANS};
  --tb-mono: {MONO};
}}
/* Named explicitly rather than left to inherit: the docstring promises these
   helpers work on any surface that can render HTML, so they must not depend on
   Streamlit's theme cascade being there. Scoped to .tb-* only — a global rule
   would stomp Streamlit's own chrome, which config.toml already handles. */
.tb-card, .tb-chip, .tb-stat, .tb-callout, .tb-sec, .tb-micro,
.tb-bar-fill, .tb-card-title {{ font-family:var(--tb-font); }}
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
  border-radius:12px; padding:14px 16px; margin:0 0 10px 0;
  box-shadow:0 1px 2px rgba(58,42,30,.05),0 3px 10px rgba(58,42,30,.04);
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
  border-radius:8px; padding:9px 11px; min-width:0;
  box-shadow:0 1px 2px rgba(58,42,30,.04),0 2px 6px rgba(58,42,30,.03);
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
    missing rather than resolve to a neutral middle. Passing a `verdict` with a
    None value replaces that caption — an explicit state such as NO EARNINGS
    already says why there is no number, and DATA N/A under it would read as a
    second, vaguer excuse.
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
    na_html = ("" if (value is not None or verdict) else
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


def gauge(value: float | None, caption: str, *, lo: float = 0.0, hi: float = 100.0,
          bands: "list[tuple[float, str]] | None" = None, verdict: str | None = None,
          fmt: str = "{:.0f}", size: int = 132) -> str:
    """Semicircular banded gauge with a needle. Inline SVG, no plot dependency.

    The sibling of `donut`, for readings that live on a scale with MEANINGFUL
    REGIONS rather than a 0-100 fill. RSI 36 is not "36% of something" — it sits
    in a zone, and the zones are the information. A donut would draw it as a
    third-full ring and say nothing about oversold.

    `bands` is [(upper_bound, tone), ...] in ascending order, painted left to
    right along the arc. Absent bands render one neutral track.

    A None value draws the arc and the bands but NO needle, with the DATA N/A
    caption — same rule as `donut`: missing must look missing rather than park a
    needle at the left stop, which reads as a real extreme value.
    """
    import math
    r = size / 2 - 12
    cx, cy = size / 2, size / 2 + 2
    bands = bands or [(hi, "neutral")]
    span = max(hi - lo, 1e-9)

    def _pt(frac: float, rad: float) -> tuple[float, float]:
        ang = math.pi * (1.0 - max(0.0, min(1.0, frac)))
        return cx + rad * math.cos(ang), cy - rad * math.sin(ang)

    arcs, prev = [], lo
    for bound, tone in bands:
        f0, f1 = (prev - lo) / span, (min(bound, hi) - lo) / span
        if f1 <= f0:
            prev = bound
            continue
        x0, y0 = _pt(f0, r)
        x1, y1 = _pt(f1, r)
        col, _ = tone_colors(tone)
        # large-arc-flag is ALWAYS 0: the whole dial is a semicircle, so no band
        # can sweep more than 180 degrees. The first cut set it from the band's
        # fraction of the scale (>0.5), which is a different quantity — ADX's
        # 25-60 band is 58% of the scale but only 105 degrees of arc, and the
        # flag sent SVG the long way round, painting a detached wedge outside
        # the gauge. Fraction of scale is not sweep.
        arcs.append(f'<path d="M {x0:.2f} {y0:.2f} A {r:.2f} {r:.2f} 0 0 1 '
                    f'{x1:.2f} {y1:.2f}" fill="none" stroke="{col}" '
                    f'stroke-width="9" stroke-linecap="butt"/>')
        prev = bound

    needle = centre = ""
    if value is not None:
        frac = (float(value) - lo) / span
        nx, ny = _pt(frac, r - 20)
        fg = TOKENS["text"]
        needle = (f'<line x1="{cx:.2f}" y1="{cy:.2f}" x2="{nx:.2f}" y2="{ny:.2f}" '
                  f'stroke="{fg}" stroke-width="2.5" stroke-linecap="round"/>'
                  f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="3.5" fill="{fg}"/>')
        centre = (f'<text x="{cx:.2f}" y="{cy - 22:.2f}" text-anchor="middle" '
                  f'font-family="{MONO}" font-size="17" font-weight="700" '
                  f'fill="{fg}">{fmt.format(value)}</text>')

    verdict_html = (f'<div style="font-size:11px;font-weight:700;margin-top:-6px;">'
                    f'{verdict}</div>') if verdict else ""
    na_html = ("" if (value is not None or verdict) else
               f'<div class="tb-na" style="font-size:11px;margin-top:-6px;">{NA}</div>')
    return (
        f'<div style="text-align:center;">'
        f'<svg width="{size}" height="{size / 2 + 14:.0f}" '
        f'viewBox="0 0 {size} {size / 2 + 14:.0f}">'
        f'{"".join(arcs)}{needle}{centre}</svg>'
        f'{verdict_html}{na_html}'
        f'<div class="tb-micro" style="margin-top:2px;">{caption}</div></div>'
    )


def range_spectrum(low: float, high: float, price: float, *,
                   marks: "list[tuple[float, str]] | None" = None,
                   lo_label: str = "52W Low", hi_label: str = "52W High",
                   cur: str = "₹") -> str:
    """Where price sits inside a range, as a red-to-green gradient bar.

    The one thing the two 52-week numbers in the valuation strip cannot show:
    POSITION. "463-865, now 706" is three numbers to hold in your head; the bar
    is one glance. It is the same information, not new information, which is why
    it carries no verdict of its own.

    Colour runs red at the low end to green at the high end. That is a
    convention about POSITION IN RANGE, not a recommendation: near the high is
    green because it means strength, and this desk's own B-19 walk-forward put
    52-Week High Leaders at -0.51% @20d, so green here is emphatically not
    "buy". The caller's caption carries that.

    `marks` adds reference ticks as [(price, label), ...] — support, resistance,
    an entry. Marks outside the range are dropped rather than clamped: a clamped
    tick sits on the end cap and reads as though it were AT the extreme.
    """
    if not all(isinstance(v, (int, float)) for v in (low, high, price)):
        return ""
    if not (high > low):
        return ""
    span = high - low
    pos = max(0.0, min(1.0, (price - low) / span)) * 100.0

    tick_html = ""
    for mp, label in (marks or []):
        if not isinstance(mp, (int, float)) or not (low <= mp <= high):
            continue
        f = (mp - low) / span * 100.0
        tick_html += (
            f'<div style="position:absolute;left:{f:.2f}%;top:-15px;transform:translateX(-50%);'
            f'font-size:9px;color:{TOKENS["text_muted"]};white-space:nowrap;">{label}</div>'
            f'<div style="position:absolute;left:{f:.2f}%;top:0;width:2px;height:14px;'
            f'background:{TOKENS["text_muted"]};transform:translateX(-50%);"></div>'
        )

    return (
        f'<div style="margin:22px 0 4px 0;">'
        f'  <div style="position:relative;height:14px;border-radius:7px;'
        f'       background:linear-gradient(90deg,{TOKENS["risk"]} 0%,'
        f'       {TOKENS["accent"]} 45%,{TOKENS["good"]} 100%);">'
        f'    {tick_html}'
        f'    <div style="position:absolute;left:{pos:.2f}%;top:50%;'
        f'         transform:translate(-50%,-50%);width:16px;height:16px;'
        f'         border-radius:50%;background:{TOKENS["surface"]};'
        f'         border:3px solid {TOKENS["text"]};box-sizing:border-box;"></div>'
        f'    <div style="position:absolute;left:{pos:.2f}%;top:-17px;'
        f'         transform:translateX(-50%);font-family:{MONO};font-size:11px;'
        f'         font-weight:700;color:{TOKENS["text"]};white-space:nowrap;">'
        f'      {cur}{price:,.2f}</div>'
        f'  </div>'
        f'  <div style="display:flex;justify-content:space-between;margin-top:5px;">'
        f'    <span class="tb-micro">{lo_label} {cur}{low:,.2f}</span>'
        f'    <span class="tb-micro">{hi_label} {cur}{high:,.2f}</span>'
        f'  </div>'
        f'</div>'
    )


def section(title: str) -> str:
    """`• SECTION NAME` header."""
    return f'<div class="tb-sec">{title}</div>'
