"""sector_card.py — the sector-breadth day card, as a shareable PNG.

Why a PNG and not HTML
----------------------
The dashboard already answers "how did sectors do today" three ways (heatmap,
quadrant, orbit) and all three are interactive Plotly surfaces that live and die
inside the browser tab. None of them leaves the machine. Posting the read to
social media currently means cropping a screenshot by hand every session, which
is why it does not happen. A real raster card is the only format that survives
Twitter/X, LinkedIn and WhatsApp without being re-encoded into mush or having
its layout rewritten by someone else's CSS.

Rendering is Pillow, not Plotly+kaleido: kaleido is not installed, it pulls a
headless Chromium, and this card is a layout, not a plot. Pillow draws it in
~40ms with no new dependency.

Data cost is zero. Everything here is computed from frames the Sector Map page
has already fetched (`cached_fetch_sector_data`) plus the sentiment reading that
is already persisted daily — the card adds no network call of its own.

The module never imports Streamlit, so it is testable on its own and callable
from a cron job or a Telegram poster later. Same rule report_style follows, and
the palette comes from report_style so the card and the dashboard agree.
"""

from __future__ import annotations

import io
import math
from datetime import date
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFont

import report_style as rs

# ──────────────────────────────────────────────────────────────────────────────
# Canvas geometry — 1080 wide is the lowest common denominator that every
# platform accepts without downscaling. Height is computed from the row count so
# a sector index appearing or disappearing can never clip the footer.
# ──────────────────────────────────────────────────────────────────────────────
W          = 1080
PAD        = 56
ROW_H      = 58
HEAD_H     = 188
SUMMARY_H  = 132
FOOT_TOP   = 38           # rule + gap above the first footer line
FOOT_LINE  = 30
FOOT_BOT   = 30

#: Gap between the name column and the bar zone, and between bar and label.
GAP        = 30
#: Bars diverge either side of a centre line so a red sector reads as red *and*
#: as pointing the other way — colour alone fails for the ~8% of men who cannot
#: separate red from green. The half-width is derived at render time from the
#: measured name and label columns (see `_geometry`) and only clamped here.
BAR_HALF_MIN = 120
BAR_HALF_MAX = 340
BAR_H      = 26

#: The dashboard masthead's orange. Deliberately not TOKENS["accent"] (#a14a0b):
#: this is the wordmark, the one place the card is allowed to be brand rather
#: than palette, and it must match the header the reader sees on the app.
BRAND_ORANGE = "#ea580c"

#: A move smaller than this reads as flat rather than as direction. Scaled by
#: √period because dispersion grows with the square root of time — a 0.05% band
#: that correctly ignores intraday noise would call a whole quarter "flat".
FLAT_BAND_1D = 0.05


def flat_band(days: int) -> float:
    """Half-width of the dead band, in %, for a period of `days` sessions."""
    return round(FLAT_BAND_1D * math.sqrt(max(1, days)), 3)


# ──────────────────────────────────────────────────────────────────────────────
# Fonts — the report_style pair, resolved to files. Windows-native, no webfont,
# for the same reasons recorded on report_style.SANS / report_style.MONO.
# ──────────────────────────────────────────────────────────────────────────────
_SANS_FILES   = ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"]
_SANS_B_FILES = ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"]
_SANS_S_FILES = ["seguisb.ttf", "segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"]
_MONO_FILES   = ["CascadiaMono.ttf", "consola.ttf", "DejaVuSansMono.ttf"]
_MONO_B_FILES = ["CascadiaMono.ttf", "consolab.ttf", "DejaVuSansMono-Bold.ttf"]


def _font(candidates: Iterable[str], size: int):
    """First installed face from `candidates`, else Pillow's default at `size`.

    Never raises: a missing font must degrade the card's typography, not stop
    the card from being produced.
    """
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size)
    except TypeError:      # Pillow < 10 has no sized default
        return ImageFont.load_default()


# ──────────────────────────────────────────────────────────────────────────────
# Model — plain dict, no rendering concerns, so it can also feed a text post
# ──────────────────────────────────────────────────────────────────────────────
def build_model(sector_data: dict[str, Any],
                display_names: dict[str, str],
                period_return,
                days: int,
                period_label: str,
                sentiment: dict[str, Any] | None = None,
                as_of: date | None = None) -> dict[str, Any]:
    """Collapse the Sector Map's frames into everything the card needs.

    `period_return(df, days) -> float | None` is injected rather than imported
    so this module stays independent of dashboard_app (which imports Streamlit
    at module scope and would drag the whole app in).

    Sectors whose frame is missing or too short are *omitted*, never counted as
    flat — an unfetched index is not a neutral index, and the card states the
    number it actually measured.
    """
    band = flat_band(days)
    rows: list[dict[str, Any]] = []
    for ticker, name in display_names.items():
        df = sector_data.get(ticker)
        if df is None:
            continue
        ret = period_return(df, days)
        if ret is None:
            continue
        if ret > band:
            tone = "good"
        elif ret < -band:
            tone = "risk"
        else:
            tone = "neutral"
        rows.append({"ticker": ticker, "name": name, "ret": float(ret), "tone": tone})

    rows.sort(key=lambda r: r["ret"], reverse=True)
    greens = sum(1 for r in rows if r["tone"] == "good")
    reds   = sum(1 for r in rows if r["tone"] == "risk")
    flats  = sum(1 for r in rows if r["tone"] == "neutral")

    # The market-breadth line is opportunistic: it rides the sentiment reading
    # that is already persisted daily. Absent or stale, the card simply omits
    # the line rather than printing a stale number as if it were today's.
    ad_line = regime_line = None
    stale = False
    if sentiment:
        inputs = sentiment.get("inputs") or {}
        ad = inputs.get("advance_decline") or {}
        if ad.get("advances") or ad.get("declines"):
            ad_line = f'{ad.get("advances", 0):,} advancing · {ad.get("declines", 0):,} declining'
        reg = inputs.get("regime_sma200") or {}
        if reg.get("reading") and reg.get("reading") != "n/a":
            regime_line = str(reg["reading"])
        rd = sentiment.get("reading_date")
        stale = bool(rd and as_of and rd != (as_of.isoformat()))

    return {
        "as_of":        (as_of or date.today()),
        "period":       period_label,
        "flat_band":    band,
        "sectors":      rows,
        "greens":       greens,
        "reds":         reds,
        "flats":        flats,
        "total":        len(rows),
        "ad_line":      ad_line,
        "regime_line":  regime_line,
        "breadth_stale": stale,
        "breadth_date": (sentiment or {}).get("reading_date"),
    }


def render_text(model: dict[str, Any]) -> str:
    """The same model as a paste-able chat post, for WhatsApp/Telegram where an
    image is heavier than the three lines it carries."""
    d = model["as_of"].strftime("%d %b %Y")
    out = [f'SECTOR BREADTH — {d} ({model["period"]})', ""]
    out.append(f'{model["greens"]} green · {model["reds"]} red · '
               f'{model["flats"]} flat  (of {model["total"]} sector indices)')
    out.append("")
    for r in model["sectors"]:
        out.append(f'{r["ret"]:+6.2f}%  {r["name"]}')
    if model["ad_line"] or model["regime_line"]:
        out.append("")
        if model["ad_line"]:
            out.append(model["ad_line"])
        if model["regime_line"]:
            out.append(model["regime_line"])
    return "\n".join(out)


# ──────────────────────────────────────────────────────────────────────────────
# Render
# ──────────────────────────────────────────────────────────────────────────────
def _tone_hex(tone: str) -> str:
    fg, _ = rs.tone_colors(tone)
    return fg


def _footer_lines(model: dict[str, Any]) -> list[tuple[str, str]]:
    """(text, colour-role) for every footer line this card will actually draw.

    Built before the canvas is sized so the height can account for them — the
    first version hard-coded a footer height and clipped its own disclaimer the
    moment a stale-breadth line appeared.
    """
    out: list[tuple[str, str]] = []
    for line in (model["ad_line"], model["regime_line"]):
        if line:
            out.append((line, "text_body"))
    if model["breadth_stale"] and model["breadth_date"]:
        out.append((f'Breadth as of {model["breadth_date"]}', "accent"))
    out.append((f'Flat band ±{model["flat_band"]:.2f}%  ·  Not investment advice',
                "text_muted"))
    return out


def _geometry(d: ImageDraw.ImageDraw, rows: list[dict[str, Any]],
              f_sector, f_val, scale: int) -> tuple[float, float]:
    """(zero-line x, bar half-width) in *scaled* px, fitting the widest name and
    value actually present.

    Measured rather than assumed: with a fixed zero line, the longest bar plus
    its label ran past the right margin, and a longer sector name would have
    collided with the negative bars.
    """
    name_w  = max((d.textlength(r["name"], font=f_sector) for r in rows), default=0.0)
    label_w = max((d.textlength(f'{r["ret"]:+.2f}%', font=f_val) for r in rows),
                  default=0.0)
    avail = (W - 2 * PAD - 2 * GAP) * scale - name_w - label_w
    half = max(BAR_HALF_MIN * scale, min(BAR_HALF_MAX * scale, avail / 2))
    return PAD * scale + name_w + GAP * scale + half, half


def render_png(model: dict[str, Any], scale: int = 1) -> bytes:
    """Draw the card and return PNG bytes.

    `scale` multiplies every dimension for a retina export; 1 gives 1080px wide.
    """
    t = rs.TOKENS
    rows = model["sectors"]
    foot = _footer_lines(model)
    h = (HEAD_H + SUMMARY_H + ROW_H * len(rows)
         + FOOT_TOP + FOOT_LINE * len(foot) + FOOT_BOT)
    w = W

    img = Image.new("RGB", (w * scale, h * scale), t["surface"])
    d = ImageDraw.Draw(img)

    def S(v: float) -> int:
        return int(round(v * scale))

    f_title  = _font(_SANS_B_FILES, S(44))
    f_sub    = _font(_SANS_FILES,   S(23))
    f_micro  = _font(_SANS_S_FILES, S(19))
    f_sector = _font(_SANS_S_FILES, S(27))
    f_val    = _font(_MONO_B_FILES, S(26))
    f_big    = _font(_MONO_B_FILES, S(46))
    f_foot   = _font(_SANS_FILES,   S(21))
    f_brand  = _font(_SANS_B_FILES, S(25))

    # ── Top rail — the one piece of brand colour on the card ──────────────────
    d.rectangle([0, 0, w * scale, S(10)], fill=BRAND_ORANGE)

    # ── Header ────────────────────────────────────────────────────────────────
    y = S(52)
    d.text((S(PAD), y), "SECTOR BREADTH", font=f_title, fill=t["text"])
    y += S(56)
    d.text((S(PAD), y), model["as_of"].strftime("%d %B %Y").upper() +
           f'  ·  {model["period"]}  ·  NSE SECTOR INDICES',
           font=f_micro, fill=t["text_muted"])

    # Wordmark, right-aligned against the title baseline.
    wm = "Trading Bramha"
    wm_w = d.textlength(wm, font=f_brand)
    d.text((w * scale - S(PAD) - wm_w, S(64)), wm, font=f_brand, fill=BRAND_ORANGE)

    d.line([S(PAD), S(HEAD_H - 26), w * scale - S(PAD), S(HEAD_H - 26)],
           fill=t["border"], width=S(2))

    # ── Summary strip — three counts, mono so they align ──────────────────────
    y = S(HEAD_H)
    cell_w = (w - 2 * PAD) / 3
    for i, (label, count, tone) in enumerate((
            ("ADVANCING", model["greens"], "good"),
            ("DECLINING", model["reds"],   "risk"),
            ("FLAT",      model["flats"],  "neutral"))):
        cx = S(PAD + cell_w * i)
        d.text((cx, y), label, font=f_micro, fill=t["text_muted"])
        d.text((cx, y + S(28)), str(count), font=f_big, fill=_tone_hex(tone))
        cnt_w = d.textlength(str(count), font=f_big)
        d.text((cx + cnt_w + S(12), y + S(46)),
               f'of {model["total"]}', font=f_sub, fill=t["text_muted"])

    # ── Ranked sector rows ────────────────────────────────────────────────────
    y = S(HEAD_H + SUMMARY_H)
    bar_x, bar_half = _geometry(d, rows, f_sector, f_val, scale)
    peak = max((abs(r["ret"]) for r in rows), default=1.0) or 1.0

    for r in rows:
        cy = y + S(ROW_H / 2)
        col = _tone_hex(r["tone"])
        d.text((S(PAD), cy - S(15)), r["name"], font=f_sector, fill=t["text"])

        # Bar diverges from the zero line: direction is encoded by side as well
        # as by colour, so the card survives being read in greyscale.
        length = abs(r["ret"]) / peak * bar_half
        if r["tone"] == "neutral":
            # A flat sector gets a dot on the axis, not a hairline bar that
            # would imply a direction the dead band just said it does not have.
            d.ellipse([bar_x - S(5), cy - S(5), bar_x + S(5), cy + S(5)],
                      fill=t["absent"])
            lx = bar_x + S(18)
        elif r["ret"] > 0:
            d.rounded_rectangle([bar_x, cy - S(BAR_H / 2),
                                 bar_x + length, cy + S(BAR_H / 2)],
                                radius=S(5), fill=col)
            lx = bar_x + length + S(14)
        else:
            d.rounded_rectangle([bar_x - length, cy - S(BAR_H / 2),
                                 bar_x, cy + S(BAR_H / 2)],
                                radius=S(5), fill=col)
            lx = bar_x + S(14)

        d.text((lx, cy - S(14)), f'{r["ret"]:+.2f}%', font=f_val,
               fill=col if r["tone"] != "neutral" else t["text_muted"])
        y += S(ROW_H)

    # Zero line last, so it sits over the bars rather than under them.
    d.line([bar_x, S(HEAD_H + SUMMARY_H + 6), bar_x, y - S(6)],
           fill=t["border_strong"], width=S(2))

    # ── Footer ────────────────────────────────────────────────────────────────
    fy = y + S(18)
    d.line([S(PAD), fy, w * scale - S(PAD), fy], fill=t["border"], width=S(2))
    fy += S(20)
    for text, role in foot:
        d.text((S(PAD), fy), text, font=f_foot, fill=t[role])
        fy += S(FOOT_LINE)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
