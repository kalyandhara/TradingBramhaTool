"""opportunity_report.py — the day's Opportunity funnel as a shareable card,
a paste-able text post, and a detailed PDF.

Why this exists
---------------
The funnel now ends in a ranked shortlist that lives inside a Streamlit tab. It
cannot be read on a phone, filed with the week's notes, or shown to anybody
without screenshotting a browser. Three formats, one model:

    render_text()  paste into WhatsApp / Telegram — lightest, no attachment
    render_png()   1080px card for X / LinkedIn / WhatsApp — survives re-encoding
    render_pdf()   multi-page vector report — selectable text, prints sharp

Follows the doctrine already set by `sector_card`: no Streamlit import (so this
is testable standalone and callable from a cron job or a poster bot later), the
palette comes from `report_style` so exports and dashboard agree, and Pillow
draws the card because it is a layout, not a plot.

The PDF is matplotlib rather than a raster page. A detailed report is read by
searching it — Ctrl+F for a symbol has to work — and it has to print sharp. The
`Figure`/`PdfPages` pair is used directly instead of `pyplot` so no global
figure state is touched; Streamlit reruns this on its own threads.

What these artifacts MUST carry
-------------------------------
This is the first thing in the repo built to leave the machine, so the honesty
discipline stops being a matter of the reader's context and becomes the file's
own job. Every format states, without being asked:

  • the market regime the list was produced in — a shortlist built under a
    sub-200-SMA tape must never be re-read later, or by someone else, as though
    conditions had been good;
  • that confluence is agreement, not measured evidence;
  • which scanners have measured edge and which were measured and failed;
  • that it is an automated research output, not advice and not a buy list.

A card that travels without those is a tip sheet.
"""

from __future__ import annotations

import io
import textwrap
from datetime import date, datetime
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFont

import opportunity_hub as oh
import report_style as rs

# ──────────────────────────────────────────────────────────────────────────────
# Model — plain dicts, no rendering concerns, so one build feeds all three
# ──────────────────────────────────────────────────────────────────────────────

#: Human labels for the scanner tiers, used in every format.
TIER_LABEL = {
    "measured":   "measured edge",
    "weak":       "measured, no edge",
    "unmeasured": "unmeasured",
    "risk":       "bearish",
}

DISCLAIMER = ("Automated research output, not investment advice and not a buy "
              "list. Verify every setup yourself.")

CONFLUENCE_NOTE = ("Families collapse scanners that read the same fact, so five "
                   "trend scanners on one chart count once. No backtest yet "
                   "shows confluence itself predicts anything - this is "
                   "agreement, not evidence.")


def _split(val) -> list[str]:
    """Comma string or list -> clean list. Stored rows carry strings; live
    pipeline hits carry lists, and both reach this module."""
    if val is None:
        return []
    if isinstance(val, (list, tuple)):
        return [str(v).strip() for v in val if str(v).strip()]
    try:
        import pandas as pd
        if pd.isna(val):
            return []
    except Exception:
        pass
    return [s.strip() for s in str(val).split(",") if s.strip()]


def _num(val):
    """float or None — stored rows use NaN for absent, dicts use None."""
    if val is None:
        return None
    try:
        import pandas as pd
        if pd.isna(val):
            return None
    except Exception:
        pass
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def group_by_family(scanners: Iterable[str]) -> list[tuple[str, list[str]]]:
    """[(family, [scanner, ...]), ...] in canonical family order.

    The grouping is the explanation: it shows at a glance that four of a name's
    six hits were one family talking to itself.
    """
    buckets: dict[str, list[str]] = {}
    for s in scanners:
        fam = oh.scanner_family(s) or ("Bearish" if s in oh.RISK_SCANNERS else "Other")
        buckets.setdefault(fam, []).append(s)
    order = list(oh.FAMILY_ORDER) + ["Other", "Bearish"]
    return [(f, buckets[f]) for f in order if f in buckets]


def build_model(rows: list[dict[str, Any]], *,
                as_of: date | None = None,
                regime: str | None = None,
                verdict: str | None = None,
                universe_size: int | None = None,
                candidates: int | None = None,
                lead_sectors: list[str] | None = None,
                lead_industries: list[str] | None = None,
                n_scanners: int | None = None,
                source: str = "Daily shortlist") -> dict[str, Any]:
    """Normalise a day's funnel output into the one model all formats read.

    `rows` accepts either stored `daily_opportunities` records or live pipeline
    hits — the two carry the same facts in slightly different containers, and
    normalising here keeps that difference out of three renderers.
    """
    out_rows: list[dict[str, Any]] = []
    for i, r in enumerate(rows, 1):
        scanners = _split(r.get("scanners"))
        fams = _split(r.get("family_names")) or _split(r.get("families"))
        if not fams or (len(fams) == 1 and fams[0].isdigit()):
            fams, _pts, _risk = oh.tally_evidence(scanners)
        risk = _split(r.get("risk_flags"))
        out_rows.append({
            "rank":       int(r.get("rank") or i),
            "symbol":     str(r.get("symbol") or "?"),
            "score":      _num(r.get("score")) or 0.0,
            "rating":     _num(r.get("overall_rating") if "overall_rating" in r
                               else r.get("overall")),
            "scanners":   scanners,
            "families":   fams,
            "by_family":  group_by_family(scanners),
            "risk_flags": risk,
            "sector":     (r.get("sector") or "-"),
            "industry":   (r.get("industry") or "-"),
            "close":      _num(r.get("close")),
            "entry":      _num(r.get("entry")),
            "stop":       _num(r.get("stop")),
            "target":     _num(r.get("target")),
            "best":       r.get("best_scanner") or "",
            "notes":      str(r.get("notes") or ""),
        })
    out_rows.sort(key=lambda r: r["rank"])

    return {
        "as_of":        as_of or date.today(),
        "generated_at": datetime.now(),
        "regime":       (regime or "UNKNOWN").upper(),
        "verdict":      verdict or "",
        "universe_size": universe_size,
        "candidates":   candidates,
        "lead_sectors": lead_sectors or [],
        "lead_industries": lead_industries or [],
        "n_scanners":   n_scanners if n_scanners is not None else len(oh.pipeline_scanners()),
        "source":       source,
        "rows":         out_rows,
        "n":            len(out_rows),
        "multi_family": sum(1 for r in out_rows if len(r["families"]) > 1),
        "with_measured": sum(1 for r in out_rows
                             if any(s in oh.MEASURED_EDGE_SCANNERS for s in r["scanners"])),
    }


def model_from_stored(df, *, as_of=None) -> dict[str, Any]:
    """Model from a `daily_opportunities` frame (the stored daily shortlist)."""
    if df is None or getattr(df, "empty", True):
        return build_model([], as_of=as_of)
    recs = df.to_dict("records")
    r0 = recs[0]
    d = as_of
    if d is None:
        try:
            d = date.fromisoformat(str(r0.get("run_date")))
        except Exception:
            d = None
    return build_model(
        recs, as_of=d,
        regime=r0.get("market_regime"), verdict=r0.get("market_verdict"),
        universe_size=(int(r0["universe_size"])
                       if _num(r0.get("universe_size")) else None),
        source="Daily shortlist (stored)")


def model_from_pipeline(pipe: dict[str, dict], *, regime=None, verdict=None,
                        candidates=None, lead_sectors=None,
                        lead_industries=None, n_scanners=None) -> dict[str, Any]:
    """Model from a live `run_scanner_pipeline` result (the manual funnel)."""
    ranked = sorted(pipe.values(), key=lambda h: h.get("rank_score") or 0,
                    reverse=True)
    rows = []
    for i, h in enumerate(ranked, 1):
        card = h.get("best_card") or {}
        rows.append({
            "rank": i, "symbol": h["symbol"],
            "score": h.get("rank_score") or 0.0,
            "overall_rating": h.get("overall"),
            "scanners": h.get("scanners") or [],
            "family_names": h.get("families") or [],
            "risk_flags": h.get("risk_flags") or [],
            "best_scanner": h.get("best_scanner"),
            "entry": card.get("entry"), "stop": card.get("stop"),
            "target": card.get("target"),
        })
    return build_model(rows, regime=regime, verdict=verdict,
                       candidates=candidates, lead_sectors=lead_sectors,
                       lead_industries=lead_industries, n_scanners=n_scanners,
                       source="Manual funnel (this session)")


# ──────────────────────────────────────────────────────────────────────────────
# Text — for chat apps, where an image is heavier than the lines it carries
# ──────────────────────────────────────────────────────────────────────────────
def render_text(model: dict[str, Any], top: int = 10) -> str:
    rows = model["rows"][:top]
    out = [f'OPPORTUNITY FUNNEL - {model["as_of"].strftime("%d %b %Y")}',
           f'Market: {model["regime"]}']
    if model["verdict"]:
        out.append(model["verdict"])
    out.append("")
    if not rows:
        out.append("No name was caught by any scanner in the leading groups today.")
    for r in rows:
        ns, nf = len(r["scanners"]), len(r["families"])
        out.append(f'{r["rank"]}. {r["symbol"]}  score {r["score"]:.0f}'
                   + (f' - rating {r["rating"]:.0f}/100' if r["rating"] else ""))
        out.append(f'   {ns} {"scanner" if ns == 1 else "scanners"} / '
                   f'{nf} {"family" if nf == 1 else "families"} - {r["industry"]}')
        if r["risk_flags"]:
            out.append(f'   ! {", ".join(r["risk_flags"])} also fired (bearish)')
    if model["n"] > len(rows):
        out.append(f'... and {model["n"] - len(rows)} more.')
    out += ["", f'Ranked from {model["n_scanners"]} scanners over stocks in leading '
                f'sectors and industries.', CONFLUENCE_NOTE, DISCLAIMER]
    return "\n".join(out)


# ──────────────────────────────────────────────────────────────────────────────
# PNG card — geometry follows sector_card so the two read as one family
# ──────────────────────────────────────────────────────────────────────────────
W         = 1080
PAD       = 56
HEAD_H    = 176
SUMMARY_H = 128
#: The regime banner's height is computed per-card from the wrapped verdict
#: (see `render_png`) — a fixed height clipped the warning the card exists to
#: carry, so this one is deliberately NOT a constant.
ROW_H     = 88
FOOT_TOP  = 34
FOOT_LINE = 29
FOOT_BOT  = 30

BRAND_ORANGE = "#ea580c"

_SANS_FILES   = ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"]
_SANS_B_FILES = ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"]
_SANS_S_FILES = ["seguisb.ttf", "segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"]
_MONO_B_FILES = ["CascadiaMono.ttf", "consolab.ttf", "DejaVuSansMono-Bold.ttf"]


def _font(candidates: Iterable[str], size: int):
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


#: Regime -> tone. UNKNOWN is deliberately not neutral: an unassessed tape is a
#: caution, not an all-clear.
_REGIME_TONE = {"RISK-ON": "good", "MIXED": "warn", "RISK-OFF": "risk"}


def _regime_tone(regime: str) -> str:
    return _REGIME_TONE.get(regime, "warn")


def _wrap(d, text: str, font, max_w: float) -> list[str]:
    """Greedy wrap measured against the real font, not a character count."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if d.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_png(model: dict[str, Any], top: int = 8, scale: int = 1) -> bytes:
    """Draw the shareable card and return PNG bytes.

    `top` caps the rows so the card stays postable; the footer states the count
    that was left off rather than silently truncating the day's result.
    """
    t = rs.TOKENS
    rows = model["rows"][:top]

    # Everything that affects height is measured on a probe canvas BEFORE the
    # real one is sized. The first cut hard-coded the banner height and clipped
    # the regime warning mid-sentence at "Treat this list as a" — on the one
    # artifact built to leave the machine, where that sentence matters most.
    f_foot_probe = _font(_SANS_FILES, 21 * scale)
    f_meta_probe = _font(_SANS_FILES, 20 * scale)
    probe = Image.new("RGB", (10, 10))
    dp = ImageDraw.Draw(probe)
    max_foot_w = (W - 2 * PAD) * scale

    vlines = _wrap(dp, model["verdict"], f_meta_probe,
                   (W - 2 * PAD - 48) * scale)[:3] if model["verdict"] else []
    banner_h = 46 + 26 * len(vlines) + 20

    foot: list[tuple[str, str]] = []
    prov = (f'{model["n_scanners"]} scanners over '
            + (f'{model["candidates"]} stocks in leading sectors/industries'
               if model["candidates"] else "stocks in leading sectors/industries")
            + (f' (universe {model["universe_size"]})' if model["universe_size"] else ""))
    for line in _wrap(dp, prov, f_foot_probe, max_foot_w):
        foot.append((line, "text_body"))
    if model["n"] > len(rows):
        foot.append((f'Showing top {len(rows)} of {model["n"]} names.', "text_body"))
    for line in _wrap(dp, CONFLUENCE_NOTE, f_foot_probe, max_foot_w):
        foot.append((line, "text_muted"))
    for line in _wrap(dp, DISCLAIMER, f_foot_probe, max_foot_w):
        foot.append((line, "accent"))

    # A row carrying a bearish flag needs a third line; a fixed row height drew
    # that line straight through the next row's rule.
    row_h = [ROW_H + (22 if r["risk_flags"] else 0) for r in rows]
    body_h = sum(row_h) if rows else 96
    h = (HEAD_H + banner_h + SUMMARY_H + body_h
         + FOOT_TOP + FOOT_LINE * len(foot) + FOOT_BOT)

    img = Image.new("RGB", (W * scale, h * scale), t["surface"])
    d = ImageDraw.Draw(img)

    def S(v: float) -> int:
        return int(round(v * scale))

    f_title = _font(_SANS_B_FILES, S(44))
    f_micro = _font(_SANS_S_FILES, S(19))
    f_sym   = _font(_SANS_B_FILES, S(31))
    f_meta  = _font(_SANS_FILES,   S(20))
    f_val   = _font(_MONO_B_FILES, S(29))
    f_big   = _font(_MONO_B_FILES, S(46))
    f_sub   = _font(_SANS_FILES,   S(23))
    f_foot  = _font(_SANS_FILES,   S(21))
    f_brand = _font(_SANS_B_FILES, S(25))
    f_ban   = _font(_SANS_S_FILES, S(23))
    f_rank  = _font(_MONO_B_FILES, S(24))

    d.rectangle([0, 0, W * scale, S(10)], fill=BRAND_ORANGE)

    # ── Header ────────────────────────────────────────────────────────────────
    d.text((S(PAD), S(50)), "OPPORTUNITY FUNNEL", font=f_title, fill=t["text"])
    d.text((S(PAD), S(108)),
           model["as_of"].strftime("%d %B %Y").upper()
           + "  ·  SECTOR → INDUSTRY → STOCK → PATTERN",
           font=f_micro, fill=t["text_muted"])
    wm = "Trading Bramha"
    d.text((W * scale - S(PAD) - d.textlength(wm, font=f_brand), S(62)),
           wm, font=f_brand, fill=BRAND_ORANGE)

    # ── Regime banner — the context the list must never travel without ────────
    fg, bg = rs.tone_colors(_regime_tone(model["regime"]))
    by = S(HEAD_H - 26)
    bh = S(banner_h - 20)
    d.rectangle([S(PAD), by, W * scale - S(PAD), by + bh], fill=bg)
    d.rectangle([S(PAD), by, S(PAD + 7), by + bh], fill=fg)
    d.text((S(PAD + 24), by + S(14)), f'MARKET {model["regime"]}',
           font=f_ban, fill=fg)
    vy = by + S(44)
    for line in vlines:
        d.text((S(PAD + 24), vy), line, font=f_meta, fill=t["text_body"])
        vy += S(26)

    # ── Summary strip ─────────────────────────────────────────────────────────
    y = S(HEAD_H + banner_h)
    cell = (W - 2 * PAD) / 3
    for i, (label, val, sub, tone) in enumerate((
            ("NAMES CAUGHT",  model["n"],            "shortlisted",   "neutral"),
            ("MULTI-FAMILY",  model["multi_family"], "more than one read", "good"),
            ("MEASURED EDGE", model["with_measured"], "carry a proven scanner", "good"))):
        cx = S(PAD + cell * i)
        d.text((cx, y), label, font=f_micro, fill=t["text_muted"])
        col = rs.tone_colors(tone)[0] if val else t["absent"]
        d.text((cx, y + S(26)), str(val), font=f_big, fill=col)
        vw = d.textlength(str(val), font=f_big)
        d.text((cx + vw + S(12), y + S(46)), sub, font=f_sub, fill=t["text_muted"])

    # ── Ranked rows ───────────────────────────────────────────────────────────
    y = S(HEAD_H + banner_h + SUMMARY_H)
    if not rows:
        d.text((S(PAD), y + S(24)),
               "No name was caught by any scanner in the leading groups today.",
               font=f_meta, fill=t["text_muted"])
        y += S(96)
    for r, rh in zip(rows, row_h):
        d.line([S(PAD), y, W * scale - S(PAD), y], fill=t["border"], width=S(1))
        d.text((S(PAD), y + S(24)), f'#{r["rank"]}', font=f_rank, fill=t["text_muted"])
        sx = S(PAD + 56)
        d.text((sx, y + S(16)), r["symbol"], font=f_sym, fill=t["text"])

        ns, nf = len(r["scanners"]), len(r["families"])
        meta = (f'{ns} {"scanner" if ns == 1 else "scanners"} · '
                f'{nf} {"family" if nf == 1 else "families"} · {r["industry"]}')
        d.text((sx, y + S(53)), meta[:74], font=f_meta, fill=t["text_muted"])

        # Score, right-aligned, with a proportional bar under it.
        stxt = f'{r["score"]:.0f}'
        sw = d.textlength(stxt, font=f_val)
        rx = W * scale - S(PAD)
        d.text((rx - sw, y + S(18)), stxt, font=f_val, fill=t["text"])
        bar_w, frac = S(150), max(0.0, min(1.0, r["score"] / 100.0))
        bx = rx - bar_w
        d.rounded_rectangle([bx, y + S(56), rx, y + S(66)], radius=S(5),
                            fill=t["surface_alt"])
        if frac > 0:
            # A measured-edge hit colours the bar; agreement alone stays neutral.
            tone = "good" if any(s in oh.MEASURED_EDGE_SCANNERS
                                 for s in r["scanners"]) else "neutral"
            d.rounded_rectangle([bx, y + S(56), bx + int(bar_w * frac), y + S(66)],
                                radius=S(5), fill=rs.tone_colors(tone)[0])
        if r["risk_flags"]:
            d.text((sx, y + S(76)),
                   f'! {", ".join(r["risk_flags"])} also fired - bearish read',
                   font=f_micro, fill=rs.tone_colors("risk")[0])
        y += S(rh)

    # ── Footer ────────────────────────────────────────────────────────────────
    fy = y + S(16)
    d.line([S(PAD), fy, W * scale - S(PAD), fy], fill=t["border"], width=S(2))
    fy += S(18)
    for text, role in foot:
        d.text((S(PAD), fy), text, font=f_foot, fill=t[role])
        fy += S(FOOT_LINE)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
# PDF — vector, searchable, paginated. Figure/PdfPages directly: no pyplot, so
# no global figure state is touched on Streamlit's worker threads.
# ──────────────────────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = 8.27, 11.69          # A4 portrait, inches
M_L, M_R = 0.62, 0.62                 # margins, inches
M_T, M_B = 0.70, 0.80

#: Matplotlib's default face is DejaVu Sans. It has no rupee sign, so prices are
#: written bare rather than rendered as a tofu box next to a number.
_MONO = "DejaVu Sans Mono"
_SANS = "DejaVu Sans"


class _Pager:
    """A flowing text cursor over paginated matplotlib figures.

    Everything is placed in figure coordinates from a descending `y`. When a
    block will not fit, `space()` starts a new page — so a name's detail block
    is never split across a page break mid-sentence.
    """

    def __init__(self, pdf, model):
        from matplotlib.figure import Figure
        self._Figure = Figure
        self.pdf = pdf
        self.model = model
        self.fig = None
        self.y = 0.0
        self.page = 0
        self._new_page()

    # geometry helpers (figure fraction)
    @property
    def x0(self) -> float:
        return M_L / PAGE_W

    @property
    def x1(self) -> float:
        return 1 - M_R / PAGE_W

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    def _new_page(self):
        if self.fig is not None:
            self._footer()
            self.pdf.savefig(self.fig)
        self.fig = self._Figure(figsize=(PAGE_W, PAGE_H))
        self.page += 1
        self.y = 1 - M_T / PAGE_H
        # Brand rail, so a printed page is still recognisably from the desk.
        self.fig.patches.extend([
            __import__("matplotlib").patches.Rectangle(
                (0, 1 - 0.012), 1, 0.012, transform=self.fig.transFigure,
                facecolor=BRAND_ORANGE, edgecolor="none")])

    def _footer(self):
        m = self.model
        self.fig.text(self.x0, M_B / PAGE_H - 0.028,
                      f'Trading Bramha · Opportunity Funnel · '
                      f'{m["as_of"].isoformat()} · market {m["regime"]}',
                      fontsize=7, color=rs.TOKENS["text_muted"], family=_SANS)
        self.fig.text(self.x1, M_B / PAGE_H - 0.028, f'page {self.page}',
                      fontsize=7, color=rs.TOKENS["text_muted"], family=_SANS,
                      ha="right")
        self.fig.text(self.x0, M_B / PAGE_H - 0.046, DISCLAIMER,
                      fontsize=7, color=rs.TOKENS["accent"], family=_SANS)

    def space(self, need: float):
        """Ensure `need` (figure fraction) remains, else break the page."""
        if self.y - need < M_B / PAGE_H:
            self._new_page()

    def gap(self, dy: float):
        self.y -= dy

    def text(self, s: str, *, size=9, color=None, weight="normal", family=_SANS,
             dx=0.0, ha="left", dy=None):
        self.fig.text(self.x0 + dx if ha == "left" else self.x1, self.y, s,
                      fontsize=size, color=color or rs.TOKENS["text_body"],
                      fontweight=weight, family=family, ha=ha, va="top")
        if dy is not None:
            self.y -= dy

    def para(self, s: str, *, size=8.5, color=None, chars=112, dx=0.0,
             lead=0.0145):
        for line in textwrap.wrap(s, chars) or [""]:
            self.space(lead * 2)
            self.text(line, size=size, color=color, dx=dx)
            self.y -= lead

    def rule(self, pad=0.008):
        self.y -= pad
        self.fig.add_artist(__import__("matplotlib").lines.Line2D(
            [self.x0, self.x1], [self.y, self.y],
            transform=self.fig.transFigure, color=rs.TOKENS["border"],
            linewidth=0.8))
        self.y -= pad

    def close(self):
        self._footer()
        self.pdf.savefig(self.fig)


def render_pdf(model: dict[str, Any]) -> bytes:
    """The detailed report: context, method, ranked table, then a block per name."""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.backends.backend_pdf import PdfPages

    t = rs.TOKENS
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        p = _Pager(pdf, model)

        # ── Title ─────────────────────────────────────────────────────────────
        p.text("OPPORTUNITY FUNNEL", size=21, weight="bold", color=t["text"],
               dy=0.030)
        p.text(model["as_of"].strftime("%d %B %Y")
               + f'  ·  {model["source"]}', size=9.5, color=t["text_muted"],
               dy=0.022)
        p.rule()

        # ── Market context ────────────────────────────────────────────────────
        fg, _bg = rs.tone_colors(_regime_tone(model["regime"]))
        p.text(f'MARKET {model["regime"]}', size=11, weight="bold", color=fg,
               dy=0.019)
        if model["verdict"]:
            p.para(model["verdict"], color=t["text_body"])
        p.gap(0.008)

        # ── Provenance — how the list was narrowed ────────────────────────────
        p.text("HOW THIS LIST WAS BUILT", size=8, weight="bold",
               color=t["text_muted"], dy=0.018)
        steps = []
        if model["universe_size"]:
            steps.append(f'Universe: top {model["universe_size"]} NSE names by traded value.')
        if model["lead_sectors"]:
            steps.append("Leading sectors: " + ", ".join(model["lead_sectors"]) + ".")
        if model["lead_industries"]:
            steps.append("Leading industries: "
                         + ", ".join(model["lead_industries"][:8])
                         + ("..." if len(model["lead_industries"]) > 8 else "") + ".")
        if model["candidates"]:
            steps.append(f'{model["candidates"]} stocks sat in those leading groups.')
        steps.append(f'{model["n_scanners"]} scanners ran over those stocks; '
                     f'{model["n"]} names were caught.')
        for s in steps:
            p.para("- " + s)
        p.gap(0.010)

        # ── Method ────────────────────────────────────────────────────────────
        p.text("HOW IT IS RANKED", size=8, weight="bold", color=t["text_muted"],
               dy=0.018)
        p.para("Score = 0.45 x Overall Rating + 0.30 x best scanner score "
               "+ 0.25 x family-capped confluence.")
        p.para(CONFLUENCE_NOTE)
        p.para(f'Scanner tiers: measured edge (full weight) = '
               f'{", ".join(oh.MEASURED_EDGE_SCANNERS)}. Measured and found at or '
               f'below a random-entry baseline (quarter weight) = '
               f'{", ".join(oh.MEASURED_WEAK_SCANNERS)}. Everything else is '
               f'unmeasured (half weight). '
               f'{", ".join(oh.RISK_SCANNERS)} is bearish and never counts as '
               f'confluence - where it fired it is flagged below.')
        p.gap(0.012)

        # ── Ranked table ──────────────────────────────────────────────────────
        p.space(0.10)
        p.text("RANKED SHORTLIST", size=8, weight="bold", color=t["text_muted"],
               dy=0.020)
        hdr = f'{"#":<4}{"SYMBOL":<14}{"SCORE":>6}{"RATING":>8}{"SCAN":>6}{"FAM":>5}   INDUSTRY'
        p.text(hdr, size=7.6, family=_MONO, weight="bold", color=t["text_muted"],
               dy=0.015)
        for r in model["rows"]:
            p.space(0.016)
            rating = f'{r["rating"]:.0f}' if r["rating"] else "-"
            line = (f'{r["rank"]:<4}{r["symbol"][:13]:<14}{r["score"]:>6.1f}'
                    f'{rating:>8}{len(r["scanners"]):>6}{len(r["families"]):>5}   '
                    f'{str(r["industry"])[:34]}')
            p.text(line, size=7.6, family=_MONO, color=t["text"], dy=0.0145)
        if not model["rows"]:
            p.para("No name was caught by any scanner in the leading groups today. "
                   "That is a result about the tape, not a failure of the scan.",
                   color=t["text_muted"])

        # ── Per-name detail ───────────────────────────────────────────────────
        if model["rows"]:
            p._new_page()
            p.text("DETAIL", size=13, weight="bold", color=t["text"], dy=0.026)

        for r in model["rows"]:
            # Reserve enough for the whole block so a name never splits.
            p.space(0.045 + 0.016 * (len(r["by_family"]) + 3))
            p.rule()
            p.text(f'#{r["rank"]}  {r["symbol"]}', size=12, weight="bold",
                   color=t["text"])
            right = f'score {r["score"]:.1f}'
            if r["rating"]:
                right += f'   ·   rating {r["rating"]:.0f}/100'
            p.text(right, size=9, color=t["text_body"], ha="right", dy=0.022)
            p.text(f'{r["industry"]}  ·  {r["sector"]}', size=8,
                   color=t["text_muted"], dy=0.019)

            nf = len(r["families"])
            p.text(f'Caught by {len(r["scanners"])} scanner'
                   f'{"" if len(r["scanners"]) == 1 else "s"} across {nf} '
                   f'independent {"family" if nf == 1 else "families"}:',
                   size=8.5, color=t["text_body"], dy=0.017)
            for fam, members in r["by_family"]:
                labelled = ", ".join(
                    f'{m} [{TIER_LABEL[oh.scanner_tier(m)]}]' for m in members)
                p.para(f'{fam}: {labelled}', size=8, chars=104, dx=0.022,
                       color=t["text_body"])

            if r["entry"] and r["stop"]:
                plan = f'Scanner trade plan: entry {r["entry"]:.2f} · stop {r["stop"]:.2f}'
                if r["target"]:
                    plan += f' · target {r["target"]:.2f}'
                    if r["entry"] != r["stop"]:
                        rr = abs((r["target"] - r["entry"]) / (r["entry"] - r["stop"]))
                        plan += f'  (R:R {rr:.1f})'
                p.para(plan + " - levels the scanner computed, not a recommendation.",
                       size=8, dx=0.022, color=t["text_body"])

            if r["risk_flags"]:
                p.para(f'WARNING: {", ".join(r["risk_flags"])} also fired - there is '
                       f'a bearish read on this same chart.',
                       size=8, dx=0.022, color=rs.tone_colors("risk")[0])
            p.gap(0.008)

        p.close()

    return buf.getvalue()
