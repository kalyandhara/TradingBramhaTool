"""pa_report.py — one ticker's Predictive Analysis page as a single PDF.

The page is a long scroll with half its content folded into expanders (council
drill-down, fundamental history, red flags, scenarios, concalls). This flattens
all of it — collapsed sections included — into one paginated, searchable
document for the ticker on screen.

Same doctrine as `opportunity_report.render_pdf`, whose `_Pager` this reuses:
no Streamlit import, matplotlib `Figure`/`PdfPages` directly (no pyplot global
state on Streamlit's worker threads), vector text so Ctrl+F works and print is
sharp, and the honesty lines travel inside the file — every page footer carries
the disclaimer, and the caveats the page states under each section are kept.

The caller builds the model (`dashboard_app._pa_pdf_model`) from what the page
already computed; this module only lays it out. Sections whose input is None
are skipped with a one-line "not available" note rather than silently dropped.
"""

from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Any

import opportunity_report as orep
import report_style as rs

_SANS, _MONO = orep._SANS, orep._MONO

DISCLAIMER = ("Automated research output, not investment advice and not a buy "
              "list. Verify every setup yourself.")

#: Sections of the live page this PDF deliberately does not reproduce, stated
#: in the file so their absence reads as a choice, not a gap.
NOT_INCLUDED = ("Interactive Chart Tool overlays (replaced by a static price "
                "chart), peer comparison and ownership flow are not included - "
                "open the dashboard for those.")

#: Hourly bars drawn in the PDF. The page plots everything Yahoo returns (~700
#: sessions); at print width that is a smear, so the PDF keeps the most recent
#: sessions and says so under the panel.
PDF_HOURLY_SESSIONS = 60


# ──────────────────────────────────────────────────────────────────────────────
# Shared page-level helpers (also used by the dashboard so the two never drift)
# ──────────────────────────────────────────────────────────────────────────────
def stage_label(mv: int) -> tuple[str, str]:
    """Minervini score (0-8) -> (stage label, colour)."""
    if mv >= 6:
        return "Stage-2 ideal band", "#16a34a"
    if mv >= 4:
        return "Stage-2 emerging", "#65a30d"
    if mv >= 2:
        return "Stage-1 base", "#d97706"
    return "Stage-3/4 caution", "#dc2626"


def smart_money(df, n: int = 60) -> dict[str, Any]:
    """Bar-level accumulation / distribution read over the last `n` sessions.

    A heuristic (close vs open + above-average volume), not delivery data and
    not measured against forward returns — the page says so and so does the PDF.
    """
    tail = df.tail(n)
    avg_vol = float(tail["volume"].mean())
    bars, acc, dist = [], 0, 0
    for c, o, v in zip(tail["close"].values, tail["open"].values, tail["volume"].values):
        c, o, v = float(c), float(o), float(v)
        if c > o and v > avg_vol:
            bars.append("#16a34a"); acc += 1
        elif c < o and v > avg_vol:
            bars.append("#dc2626"); dist += 1
        else:
            bars.append("#9ca3af")
    if acc > dist * 1.5:
        verdict, color = "Strong accumulation", "#16a34a"
    elif acc > dist:
        verdict, color = "Mild accumulation", "#65a30d"
    elif dist > acc * 1.5:
        verdict, color = "Strong distribution", "#dc2626"
    elif dist > acc:
        verdict, color = "Mild distribution", "#ea580c"
    else:
        verdict, color = "Neutral", "#6b7280"
    return {"bars": bars, "acc": acc, "dist": dist, "n": len(bars),
            "verdict": verdict, "color": color}


# ──────────────────────────────────────────────────────────────────────────────
# Text hygiene — DejaVu has no rupee sign or emoji, and matplotlib treats "$"
# as a mathtext delimiter. Every string from the engines passes through here.
# ──────────────────────────────────────────────────────────────────────────────
_EMOJI = re.compile("[\U0001F000-\U0001FFFF☀-⛿✀-➿️‍]")
_MD = re.compile(r"\*\*|__|`")


def clean(s: Any) -> str:
    if s is None:
        return "-"
    s = str(s).replace("₹", "Rs ").replace("$", r"\$")
    s = _MD.sub("", _EMOJI.sub("", s))
    return re.sub(r" {2,}", " ", re.sub(r"<[^>]+>", "", s)).strip()


def _f(v, fmt="{:,.2f}", suffix="") -> str:
    if v is None:
        return "-"
    try:
        return fmt.format(float(v)) + suffix
    except (TypeError, ValueError):
        return clean(v)


def _cr(v) -> str:
    return "-" if v is None else f"Rs {float(v) / 1e7:,.0f} Cr"


# ──────────────────────────────────────────────────────────────────────────────
# Pager — the funnel's flowing cursor with this report's own footer, plus an
# embedded-axes helper for the charts.
# ──────────────────────────────────────────────────────────────────────────────
class _Pager(orep._Pager):
    def _footer(self):
        m = self.model
        self.fig.text(self.x0, orep.M_B / orep.PAGE_H - 0.028,
                      f'Trading Bramha · {m.get("page_title", "Predictive Analysis")} · {m["symbol"]} · '
                      f'price as of {m["as_of"]} · market {m["regime"]}',
                      fontsize=7, color=rs.TOKENS["text_muted"], family=_SANS)
        self.fig.text(self.x1, orep.M_B / orep.PAGE_H - 0.028, f"page {self.page}",
                      fontsize=7, color=rs.TOKENS["text_muted"], family=_SANS,
                      ha="right")
        self.fig.text(self.x0, orep.M_B / orep.PAGE_H - 0.046, DISCLAIMER,
                      fontsize=7, color=rs.TOKENS["accent"], family=_SANS)

    def axes(self, height: float):
        """Reserve `height` (figure fraction) and return an Axes spanning it."""
        self.space(height + 0.01)
        ax = self.fig.add_axes([self.x0, self.y - height, self.width, height])
        self.y -= height + 0.012
        return ax

    def axes_row(self, height: float, n: int, polar: tuple[int, ...] = (),
                 gap: float = 0.035):
        """Reserve `height` and return `n` side-by-side Axes; indices in `polar`
        get a polar projection (the year spiral)."""
        self.space(height + 0.01)
        w = (self.width - gap * (n - 1)) / n
        out = []
        for i in range(n):
            rect = [self.x0 + i * (w + gap), self.y - height, w, height]
            out.append(self.fig.add_axes(rect, projection="polar" if i in polar else None))
        self.y -= height + 0.012
        return out

    def heading(self, s: str):
        self.space(0.12)   # heading plus its first lines, never orphaned
        self.gap(0.006)
        self.rule()
        self.text(s.upper(), size=10.5, weight="bold", color=rs.TOKENS["text"],
                  dy=0.022)

    def label(self, s: str):
        self.space(0.03)
        self.text(s.upper(), size=7.8, weight="bold",
                  color=rs.TOKENS["text_muted"], dy=0.016)

    def kv(self, pairs: list[tuple[str, str]], cols: int = 3):
        """Label/value grid — the PDF form of the page's stat-card strips."""
        t = rs.TOKENS
        cw = self.width / cols
        for i in range(0, len(pairs), cols):
            self.space(0.034)
            for j, (k, v) in enumerate(pairs[i:i + cols]):
                self.fig.text(self.x0 + j * cw, self.y, clean(k).upper(),
                              fontsize=6.8, color=t["text_muted"], family=_SANS,
                              va="top", fontweight="bold")
                v = clean(v)
                lim = int(96 / cols)          # chars that fit a cell at 9.5pt
                v = v if len(v) <= lim else v[:lim - 1] + "…"
                self.fig.text(self.x0 + j * cw, self.y - 0.012, v,
                              fontsize=9.5, color=t["text"], family=_SANS,
                              va="top")
            self.y -= 0.032

    def bullets(self, items, color=None, empty="None detected."):
        if not items:
            self.para(empty, color=rs.TOKENS["text_muted"], size=8)
            return
        for it in items:
            self.para("- " + clean(it), size=8.3, color=color, chars=110)

    def table(self, header: list[str], rows: list[list[str]], widths: list[int]):
        """Monospaced fixed-width table — selectable text, aligns in print."""
        def line(cells):
            return "".join(clean(c)[:w - 1].ljust(w) for c, w in zip(cells, widths))
        self.space(0.03)
        self.text(line(header), size=7.4, family=_MONO, weight="bold",
                  color=rs.TOKENS["text_muted"], dy=0.0145)
        for r in rows:
            self.space(0.016)
            self.text(line(r), size=7.4, family=_MONO, color=rs.TOKENS["text"],
                      dy=0.0140)
        self.gap(0.004)


# ──────────────────────────────────────────────────────────────────────────────
# Sections
# ──────────────────────────────────────────────────────────────────────────────
def _price_chart(p: _Pager, df):
    """Close with 50/200-day means over the last year, volume underneath."""
    t = rs.TOKENS
    d = df.tail(260)
    close = df["close"].astype(float)
    ax = p.axes(0.20)
    ax.plot(d.index, d["close"], color=t["text"], linewidth=1.1, label="Close")
    for n, col in ((50, "#2563eb"), (200, "#ea580c")):
        if len(close) >= n:
            ax.plot(d.index, close.rolling(n).mean().loc[d.index], color=col,
                    linewidth=0.9, label=f"{n}-day mean")
    ax.legend(fontsize=6.5, loc="upper left", frameon=False)
    ax.tick_params(labelsize=6.5, labelbottom=False)
    ax.grid(alpha=0.25, linewidth=0.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    vx = p.axes(0.05)
    up = (d["close"] >= d["open"]).values
    vx.bar(d.index, d["volume"], width=1.0,
           color=[t["good"] if u else t["risk"] for u in up], alpha=0.6)
    vx.tick_params(labelsize=6)
    vx.set_yticks([])
    for s in ("top", "right", "left"):
        vx.spines[s].set_visible(False)


def _flow_strip(p: _Pager, bars: list[str]):
    ax = p.axes(0.022)
    ax.bar(range(len(bars)), [1] * len(bars), width=0.9, color=bars)
    ax.set_xlim(-0.5, len(bars) - 0.5)
    ax.axis("off")


def _style(ax, size=6):
    ax.tick_params(labelsize=size)
    ax.grid(alpha=0.25, linewidth=0.5)
    for sp_ in ("top", "right"):
        ax.spines[sp_].set_visible(False)


def _candles(ax, d, date_fmt: str):
    """OHLC candles on an integer x (no weekend/overnight gaps), ~4 date ticks."""
    import numpy as np
    t = rs.TOKENS
    o, h, l, c = (d[k].astype(float).values for k in ("open", "high", "low", "close"))
    x = np.arange(len(d))
    col = [t["good"] if cc >= oo else t["risk"] for oo, cc in zip(o, c)]
    lw = 0.4 if len(d) > 150 else 0.7
    ax.vlines(x, l, h, colors=col, linewidth=lw)
    ax.bar(x, np.maximum(abs(c - o), (h - l) * 0.002), bottom=np.minimum(o, c),
           width=0.7, color=col, linewidth=0)
    ticks = np.linspace(0, len(d) - 1, min(4, len(d))).astype(int)
    ax.set_xticks(ticks)
    ax.set_xticklabels([d.index[i].strftime(date_fmt) for i in ticks])
    ax.set_xlim(-1, len(d))
    _style(ax)


#: date format per board panel, so each axis reads at its own scale
_TF_FMT = {"Hourly": "%d %b", "Daily": "%b %y", "Monthly": "%Y",
           "Half-yearly": "%Y", "Yearly": "%Y"}


def _six_horizons(p: _Pager, panels: list):
    t = rs.TOKENS
    p.heading("Six horizons")
    p.para("Hourly · Daily · Monthly · Half-yearly · Yearly · Year-on-year - one "
           "company at six scales. Context, not a signal.", size=8,
           color=t["text_muted"])
    notes = []
    for k, row in enumerate((panels[:3], panels[3:])):
        p.space(0.20)
        p.gap(0.004 if k == 0 else 0.022)
        for i, pn in enumerate(row):          # panel titles above their axes
            w = (p.width - 0.035 * 2) / 3
            p.fig.text(p.x0 + i * (w + 0.035), p.y, pn.name.upper(), fontsize=7.6,
                       fontweight="bold", color=t["text_muted"], family=_SANS, va="top")
        p.gap(0.018)
        axes = p.axes_row(0.16, len(row))
        for ax, pn in zip(axes, row):
            note = pn.note
            if not pn.ok:
                ax.axis("off")
                ax.text(0.5, 0.5, "Not shown - " + clean(pn.note or "no data"),
                        ha="center", va="center", fontsize=6.5, wrap=True,
                        color=t["text_muted"], transform=ax.transAxes)
                continue
            if pn.lines:
                newest = max(pn.lines)
                for lab in sorted(pn.lines):
                    s_ = pn.lines[lab]
                    now = lab == newest
                    ax.plot(s_.index, s_.values, linewidth=1.6 if now else 0.7,
                            color=t["accent"] if now else t["absent"],
                            alpha=1 if now else 0.6, label=lab)
                ax.axhline(0, color=t["border_strong"], linewidth=0.6)
                ax.set_xlabel("day of year", fontsize=6)
                ax.set_ylabel("% from 1 Jan", fontsize=6)
                ax.legend(fontsize=5, frameon=False, ncol=3, loc="upper left")
                _style(ax)
            else:
                d = pn.df
                if pn.name == "Hourly":
                    days = d.index.normalize()
                    keep = days.isin(days.unique()[-PDF_HOURLY_SESSIONS:])
                    d = d[keep]
                    note = (f"last {PDF_HOURLY_SESSIONS} sessions shown in print "
                            f"({len(d)} bars); " + (pn.note or ""))
                _candles(ax, d, _TF_FMT.get(pn.name, "%Y"))
            if note:
                notes.append(f"{pn.name}: " + clean(note))
    p.gap(0.022)                              # clear the x tick labels
    for n_ in notes:
        p.para(n_, size=7.2, color=t["text_muted"], chars=125, lead=0.0125)
    p.para("Half-yearly and yearly are resampled from daily bars (an OHLC aggregate "
           "of daily bars is the true period candle). Year-on-year rebases each "
           "calendar year to its own 1 January, so it compares SHAPE, not "
           "performance.", size=7.4, color=t["text_muted"], chars=125)


def _horizon_geometry(p: _Pager, df):
    import numpy as np
    import pandas as pd
    import matplotlib.dates as mdates
    import horizon_geometry as hgeo
    t = rs.TOKENS
    p.heading("Horizon geometry")
    p.space(0.36)
    p.fig.text(p.x0, p.y, "YEAR SPIRAL - angle = day of year, radius = close (log)",
               fontsize=7.6, fontweight="bold", color=t["text_muted"], family=_SANS,
               va="top")
    p.fig.text(p.x0 + p.width / 2 + 0.02, p.y,
               "PIVOT GEOMETRY - circles on major weekly swings", fontsize=7.6,
               fontweight="bold", color=t["text_muted"], family=_SANS, va="top")
    p.gap(0.02)
    ax_sp, ax_geo = p.axes_row(0.30, 2, polar=(0,), gap=0.06)

    # Year spiral. Radius is log10(close) with price labels - same picture as the
    # page's log radial axis, without matplotlib's fragile polar log scale.
    sp = hgeo.year_spiral(df)
    if len(sp) < 2:
        ax_sp.axis("off")
        ax_sp.text(0.5, 0.5, "Not shown - needs two calendar years", ha="center",
                   fontsize=7, color=t["text_muted"], transform=ax_sp.transAxes)
    else:
        newest = max(sp)
        cmap = __import__("matplotlib").colormaps["tab10"]
        for i, yr in enumerate(sorted(sp)):
            d = sp[yr]
            now = yr == newest
            ax_sp.plot(np.radians(d["theta"].values), np.log10(d["r"].values),
                       linewidth=1.6 if now else 0.7,
                       color=t["accent"] if now else cmap(i % 10),
                       alpha=1 if now else 0.6, label=yr)
        ax_sp.set_theta_zero_location("N")
        ax_sp.set_theta_direction(-1)
        ax_sp.set_xticks(np.radians(np.arange(12) * 30))
        ax_sp.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
                               "Aug", "Sep", "Oct", "Nov", "Dec"], fontsize=6)
        allr = np.log10(np.concatenate([sp[y]["r"].values for y in sp]))
        lo_r, hi_r = float(allr.min()), float(allr.max())
        pad = (hi_r - lo_r) * 0.08 or 0.05
        ax_sp.set_ylim(lo_r - pad, hi_r + pad)
        rt = np.linspace(lo_r, hi_r, 4)
        ax_sp.set_yticks(rt)
        ax_sp.set_yticklabels([f"{10 ** v:,.0f}" for v in rt], fontsize=5.5,
                              color=t["text_muted"])
        ax_sp.set_rlabel_position(100)
        ax_sp.grid(alpha=0.3, linewidth=0.5)
        ax_sp.legend(fontsize=5, frameon=False, loc="upper center",
                     bbox_to_anchor=(0.5, -0.06), ncol=min(6, len(sp)))

    # Pivot geometry
    geo = hgeo.pivot_geometry(df)
    if not geo.ok:
        ax_geo.axis("off")
        ax_geo.text(0.5, 0.5, "Not shown - " + clean(geo.note or "no data"),
                    ha="center", fontsize=7, color=t["text_muted"],
                    transform=ax_geo.transAxes)
    else:
        w = df["close"].astype(float).copy()
        w.index = pd.to_datetime(w.index)
        w = w.resample("W-FRI").last().dropna()
        ax_geo.plot(w.index, w.values, color=t["accent"], linewidth=1.0,
                    label="weekly close")
        for circ in geo.circles:
            xs, ys = hgeo.circle_path(geo, circ)
            xn = np.array([mdates.date2num(pd.Timestamp(x)) if x is not None else np.nan
                           for x in xs])
            yn = np.array([y if y is not None else np.nan for y in ys], dtype=float)
            ax_geo.plot(xn, yn, color=t["absent"], linewidth=0.5, alpha=0.55)
        pd_, pp_, _pk = zip(*geo.pivots)
        ax_geo.plot(pd_, pp_, color="#f5a623", linewidth=1.1, marker="s",
                    markersize=3, label="pivots")
        if geo.nodes:
            ax_geo.scatter([n["date"] for n in geo.nodes],
                           [n["price"] for n in geo.nodes], marker="D", s=18,
                           color=t["risk"], zorder=5, label="future nodes")
        ax_geo.axvline(w.index[-1], color=t["border_strong"], linewidth=0.7,
                       linestyle=":")
        lo, hi = min(pp_), max(pp_)
        ax_geo.set_yscale("log")
        ax_geo.set_ylim(lo * 0.6, hi * 1.6)
        tk = __import__("matplotlib").ticker
        yt = np.geomspace(lo * 0.6, hi * 1.6, 6)
        ax_geo.set_yticks(yt)
        ax_geo.yaxis.set_major_formatter(tk.FuncFormatter(
            lambda v, _: f"{v:,.0f}" if v >= 10 else f"{v:,.1f}"))
        ax_geo.yaxis.set_minor_formatter(tk.NullFormatter())
        ax_geo.yaxis.set_minor_locator(tk.NullLocator())
        ax_geo.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax_geo.legend(fontsize=5.5, frameon=False, loc="upper left")
        _style(ax_geo)
    p.gap(0.02)
    if geo.ok:
        p.para(clean(geo.note or ""), size=7.4, color=t["text_muted"], chars=125)
        if geo.nodes:
            p.label("Future nodes")
            p.table(["Node date", "Price", "Circles crossing"],
                    [[n["date"].strftime("%d %b %Y"), f'{n["price"]:,.2f}',
                      str(n["circles"])] for n in geo.nodes], [16, 14, 18])
    p.para("Context, not a signal. Pivot circles are computed in a fixed normalized "
           "space, so nodes do not move with zoom - drawn on date/price axes they can "
           "look like ellipses. A dense lattice always fits past turns; only nodes "
           "named before price arrives carry information.", size=7.4,
           color=t["text_muted"], chars=125)


def _analyzer_scores(p: _Pager, sc_: dict):
    """Stock Analyzer's own score strip + Elliott-wave read (that page only)."""
    t = rs.TOKENS
    p.heading("Analyzer scores")
    p.kv([(k, str(v)) for k, v in sc_.get("pairs", [])], cols=3)
    if sc_.get("ew"):
        p.para(clean(sc_["ew"]), size=8.2, chars=118)
    p.para("Rule-count scores, not backtested probabilities.", size=7.4,
           color=t["text_muted"])


def render_pdf(m: dict[str, Any]) -> bytes:
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.backends.backend_pdf import PdfPages

    t = rs.TOKENS
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        p = _Pager(pdf, m)

        # ── Title ─────────────────────────────────────────────────────────────
        p.text(f'{m["symbol"]}  ·  {m.get("page_title", "Predictive Analysis").upper()}',
               size=19, weight="bold",
               color=t["text"], dy=0.028)
        sub = clean(m.get("long_name") or "")
        p.text((sub + "  ·  " if sub else "")
               + f'generated {m["generated_at"]:%d %b %Y %H:%M}',
               size=9, color=t["text_muted"], dy=0.020)
        chg = m.get("chg_pct")
        p.text(f'Rs {m["price"]:,.2f}'
               + (f'   {chg:+.2f}% on the day' if chg is not None else "")
               + (f'   ·   Overall Rating {m["rating"]:.0f}/100'
                  if m.get("rating") is not None else "   ·   Overall Rating n/a"),
               size=12, weight="bold", color=t["accent"], dy=0.022)
        if m.get("rating_breakdown"):
            p.para("Rating breakdown: " + "  ·  ".join(
                f"{k} {v}" for k, v in m["rating_breakdown"].items()), size=8)
        p.para(f'Market regime when generated: {m["regime"]}.', size=8,
               color=t["text_muted"])
        p.para(NOT_INCLUDED, size=7.6, color=t["text_muted"])

        if m.get("analyzer_scores"):
            _analyzer_scores(p, m["analyzer_scores"])

        # ── Stock summary ─────────────────────────────────────────────────────
        s = m.get("summary")
        if s:
            p.heading("Stock summary")
            p.kv([("Price", f'Rs {m["price"]:,.2f}'),
                  ("52W low - high", f'{s["lo52"]:,.0f} - {s["hi52"]:,.0f}'),
                  ("From 52W high", f'{s["pct_from_high"]:+.1f}%'),
                  ("Stage", f'{s["stage"]} ({s["mv"]}/8)'),
                  ("60d support", _f(s.get("support"), "{:,.0f}")),
                  ("60d resistance", _f(s.get("resistance"), "{:,.0f}"))])
            p.label("Minervini trend template")
            p.para("  ·  ".join(("PASS " if v else "fail ") + clean(k.split(" ", 1)[-1])
                                for k, v in s["conds"].items()), size=8, chars=118)
            p.label("Detected patterns (latest scan)")
            p.para(", ".join(s["patterns"]) if s["patterns"]
                   else "No patterns detected in latest scan.", size=8.3)

        # ── Smart money flow ──────────────────────────────────────────────────
        f = m.get("flow")
        if f:
            p.heading("Smart money flow")
            p.text(f["verdict"], size=10, weight="bold", color=f["color"])
            p.text(f'{f["acc"]} acc · {f["dist"]} dist · '
                   f'{f["n"] - f["acc"] - f["dist"]} neutral (last {f["n"]} sessions)',
                   size=8, color=t["text_muted"], ha="right", dy=0.020)
            _flow_strip(p, f["bars"])
            p.kv([("OBV trend (60d)", f.get("obv_trend") or "-"),
                  ("CMF (21)", _f(f.get("cmf"), "{:+.3f}"))], cols=3)
            p.para("Session flow is a bar-level heuristic (close vs open + "
                   "above-average volume) - not institutional delivery data, not "
                   "measured against forward returns.", size=7.6,
                   color=t["text_muted"])

        # ── Price chart ───────────────────────────────────────────────────────
        if m.get("df") is not None:
            p.heading("Price - last year")
            _price_chart(p, m["df"])

        # ── Setup intelligence + council ──────────────────────────────────────
        intel = m.get("intel")
        if intel is not None:
            p.heading("Setup intelligence")
            p.text(f"Setup status: {clean(intel.status_label)}", size=10,
                   weight="bold", color=t["text"], dy=0.020)
            p.kv([(lab, val) for lab, val, _tone in intel.chips], cols=4)
            p.label("Bullish factors")
            p.bullets(intel.bullish_factors, color=t["good"])
            p.label("Risk factors")
            p.bullets(intel.risk_factors, color=t["risk"])
            p.label("Overall view")
            p.para(clean(intel.overall_view), size=8.3)

        card = m.get("card")
        if card is not None:
            p.heading("Council - Bull / Bear / Judge")
            p.text(f"{card.verdict} - conviction {card.conviction}/10 "
                   f"(net {card.net_score:+.0f})", size=10.5, weight="bold",
                   color=t["text"], dy=0.020)
            if card.verdict == "AVOID":
                p.para("No long trade suggested. Levels below are reference only.",
                       size=8.3, color=t["risk"])
            if card.entry is not None:
                lab = "Ref price" if card.verdict == "AVOID" else "Entry"
                stop = (f"Rs {card.stop:,.2f} ({card.risk_pct}% risk)"
                        if card.stop else "-")
                p.para(f"{lab} Rs {card.entry:,.2f}  ·  Stop {stop}", size=8.5)
            if card.targets:
                p.para("Targets  " + "  ·  ".join(
                    f"T{i + 1} Rs {tg:,.2f} (R:R {r})"
                    for i, (tg, r) in enumerate(zip(card.targets, card.rr))), size=8.5)
            if m.get("size_note") and card.verdict != "AVOID":
                p.para(clean(m["size_note"]) + f"  ·  Horizon {card.horizon}", size=8.5)
            p.para(f"Bull's best: {clean(card.bull_top)}", size=8.3, color=t["good"])
            p.para(f"Bear's best: {clean(card.bear_top)}", size=8.3, color=t["risk"])
            p.para(clean(card.regime_note), size=8.3)
            if card.invalidations:
                p.para("Invalidation: " + "; ".join(clean(x) for x in card.invalidations),
                       size=8.3)
            for th, name in ((m.get("bull"), "Bull"), (m.get("bear"), "Bear")):
                if th is None:
                    continue
                p.label(f"{name} thesis - conviction {th.conviction}/10")
                p.table(["Pillar", "Score", "Wt", "Reasoning"],
                        [[pl.name, f"{pl.score:.0f}", f"{pl.weight}", pl.reason]
                         for pl in th.pillars], [22, 7, 6, 70])
                if th.breakers:
                    p.para("Thesis-breakers: " + "; ".join(clean(b) for b in th.breakers),
                           size=8, color=t["risk"])

        # ── Historical pattern metrics ────────────────────────────────────────
        pmx = m.get("pattern_metrics")
        if pmx:
            p.heading("Historical pattern metrics")
            pairs = []
            oh = pmx.get("overhead")
            if oh:
                pairs.append(("Overhead supply", f'{oh["pct"]:.0f}% · {oh["label"]}'))
            ex = pmx.get("extension")
            if ex and ex.get("score") is not None:
                pairs.append(("Extension", f'{ex["score"]:.0f} · {ex["band"]}'))
                if ex.get("rsi") is not None:
                    pairs.append(("RSI / 5d run", f'{ex["rsi"]:.0f} / {ex["run5_pct"]:+.1f}%'))
            vc = pmx.get("vcp")
            if vc:
                pairs += [("Base length", f'{vc["base_weeks"]:.0f} weeks'),
                          ("Base depth", f'{vc["depth_pct"]:.1f}%'),
                          ("Contractions", f'{vc["contractions"]}'
                           + (" (forming)" if vc.get("in_progress") else ""))]
            else:
                pairs.append(("Base / VCP", "none confirmed"))
            rd = pmx.get("radar")
            if rd and rd.get("score") is not None:
                pairs.append(("Radar mean", f'{rd["score"]:.1f}'))
            p.kv(pairs, cols=3)
            if rd:
                p.para("Radar axes: " + "  ·  ".join(
                    f"{k} {v:.0f}" for k, v in rd["axes"].items() if v is not None),
                    size=8)
            xv = pmx.get("exceptional_volume")
            if xv:
                p.label(f'Exceptional volume - sessions >= {xv["mult"]:.0f}x average '
                        f'({xv["count"]} found)')
                p.table(["Date", "Volume", "x avg"],
                        [[str(s_["date"])[:10], f'{s_["volume"]:,.0f}', f'{s_["ratio"]:.1f}x']
                         for s_ in xv["sessions"][:8]], [14, 18, 8])
            p.para("Descriptive only; none of these has been measured for forward "
                   "return here.", size=7.6, color=t["text_muted"])

        # ── Valuation, growth, fundamental signals ────────────────────────────
        fu = m.get("fundamentals")
        if fu:
            p.heading("Valuation & quality")
            p.kv(fu["valuation"], cols=3)
            if fu.get("growth"):
                p.label("Growth & quality - from financial statements")
                p.kv(fu["growth"], cols=3)
            elif not fu.get("statements"):
                p.para("No financial statements returned for this symbol - growth "
                       "figures are not shown rather than estimated.", size=8,
                       color=t["text_muted"])
        sig = m.get("signals")
        if sig:
            p.label("Fundamental signals")
            biz, ent = sig.get("business") or {}, sig.get("entry") or {}
            cov = sig.get("coverage") or {}
            p.para(f'Business: {biz.get("word") or "n/a"}  ·  Entry: '
                   f'{ent.get("word") or "n/a"}  ·  scored inputs '
                   f'{cov.get("have", 0)}/{cov.get("total", 0)}', size=8.5)
            p.table(["Axis", "Score", "Verdict", "Drivers"],
                    [[a.get("label", k), "-" if a.get("score") is None else str(a["score"]),
                      a.get("verdict") or "-", a.get("drivers") or "no inputs"]
                     for k, a in (sig.get("axes") or {}).items()], [24, 7, 16, 58])

        mo = m.get("momentum")
        if mo:
            p.label("Momentum (context, not a signal)")
            p.kv([("RSI 14", _f(mo.get("rsi"), "{:.1f}") + f' {mo.get("rsi_word") or ""}'),
                  ("ADX 14", _f(mo.get("adx"), "{:.1f}") + f' {mo.get("adx_word") or ""}')],
                 cols=3)

        # ── Six horizons + horizon geometry (same order as the page) ─────────
        if m.get("horizon_panels"):
            try:
                _six_horizons(p, m["horizon_panels"])
            except Exception as exc:          # a chart must not cost the report
                p.para(f"Six horizons could not be drawn ({type(exc).__name__}).",
                       size=8, color=t["text_muted"])
        if m.get("df") is not None:
            try:
                _horizon_geometry(p, m["df"])
            except Exception as exc:
                p.para(f"Horizon geometry could not be drawn ({type(exc).__name__}).",
                       size=8, color=t["text_muted"])

        # ── Collapsed sections, expanded ──────────────────────────────────────
        deep = m.get("deep") or {}
        annual, quarters = deep.get("annual") or [], deep.get("quarters") or []
        if annual or quarters:
            p.heading("Fundamental history")
            if annual:
                p.table(["Year", "Revenue", "Rev YoY", "Net profit", "Prof YoY",
                         "Margin", "OPM", "EPS"],
                        [[a["period"], _cr(a.get("revenue")),
                          _f(a.get("revenue_yoy"), "{:+.1f}", "%"),
                          _cr(a.get("net_income")),
                          _f(a.get("profit_yoy"), "{:+.1f}", "%"),
                          _f(a.get("net_margin"), "{:.1f}", "%"),
                          _f(a.get("opm"), "{:.1f}", "%"), _f(a.get("eps"))]
                         for a in annual], [12, 15, 10, 15, 10, 9, 8, 10])
            if quarters:
                p.label(f"Quarterly earnings - last {len(quarters)} reported")
                p.table(["Quarter", "Revenue", "EPS", "Profit YoY"],
                        [[str(q["period"])[:10], _cr(q.get("revenue")), _f(q.get("eps")),
                          _f(q.get("profit_yoy"), "{:+.1f}", "%")] for q in quarters],
                        [14, 16, 12, 12])
            p.para("Reported actuals only - no free NSE consensus feed, so no "
                   "beat/miss record is shown or approximated.", size=7.6,
                   color=t["text_muted"])

        rf = m.get("red_flags") or {}
        if rf.get("flags"):
            c = rf.get("counts") or {}
            p.heading("Red flags")
            p.para(f'Flagged {c.get("flagged", 0)}  ·  checked & clean '
                   f'{c.get("clean", 0)}  ·  not checked {c.get("not_checked", 0)}',
                   size=8.5)
            order = {"FLAG": 0, "NOT_CHECKED": 1, "CLEAN": 2}
            word = {"FLAG": "FLAG", "CLEAN": "CLEAN", "NOT_CHECKED": "NOT CHECKED"}
            for fl in sorted(rf["flags"], key=lambda x: (order.get(x["state"], 9),
                                                         x["severity"] != "critical")):
                col = (t["risk"] if fl["state"] == "FLAG" else
                       t["good"] if fl["state"] == "CLEAN" else t["text_muted"])
                p.space(0.04)
                p.text(f'[{word.get(fl["state"], fl["state"])}]  {clean(fl["label"])}',
                       size=8.6, weight="bold", color=col, dy=0.015)
                p.para(f'{fl["severity"]} · {clean(fl["source"])} - {clean(fl["detail"])}',
                       size=7.9, dx=0.02, chars=108)
            if not rf.get("no_critical_flags"):
                p.para("Not a clean bill of health: items marked NOT CHECKED live in "
                       "annual-report prose nothing here parses. An unexamined risk "
                       "is not an absent one.", size=7.6, color=t["text_muted"])

        sc_ = m.get("scenarios")
        if sc_:
            p.heading("Forward scenarios - business size")
            p.table(["Case", "Growth/yr", "Margin", "Revenue", "Net profit"],
                    [[r["name"], f'{r["growth_pct"]:+.1f}%', f'{r["margin_pct"]:.1f}%',
                      _cr(r.get("revenue")), _cr(r.get("profit"))]
                     for r in sc_["scenarios"]], [10, 12, 10, 18, 18])
            for r in sc_["scenarios"]:
                p.para(f'{r["name"]}: {clean(r.get("derivation"))}', size=7.6,
                       chars=118, color=t["text_body"])
            d_ = sc_.get("driver") or {}
            if d_:
                p.label(f'1 thing to track - {clean(d_.get("which"))}')
                p.para(f'{clean(d_.get("threshold"))}. {clean(d_.get("detail"))}', size=8.3)
            p.para("Arithmetic extrapolation of filed revenue and margin, not a "
                   "forecast - and a different object from the chart's price "
                   "projection; neither confirms the other.", size=7.6,
                   color=t["text_muted"])

        cc = m.get("concalls") or {}
        if cc.get("state") == "OK" and cc.get("items"):
            p.heading("Earnings calls & investor material")
            for i in cc["items"]:
                lab = clean(i.get("text") or i.get("subject") or "(no description)")
                p.para(f'{i.get("date") or "-"}  [{i.get("kind", "")}]  {lab[:150]}',
                       size=7.9, chars=118)
                if i.get("file"):
                    p.para(str(i["file"]), size=6.8, dx=0.02, chars=130,
                           color=t["text_muted"])

        p.close()
    return buf.getvalue()


def file_name(symbol: str, when: datetime | None = None,
              page: str = "predictive-analysis") -> str:
    return f"{page}-{symbol}-{(when or datetime.now()):%Y-%m-%d}.pdf"
