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
                "chart), the six-horizon board, peer comparison and ownership "
                "flow are not included - open the dashboard for those.")


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
                      f'Trading Bramha · Predictive Analysis · {m["symbol"]} · '
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


def render_pdf(m: dict[str, Any]) -> bytes:
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.backends.backend_pdf import PdfPages

    t = rs.TOKENS
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        p = _Pager(pdf, m)

        # ── Title ─────────────────────────────────────────────────────────────
        p.text(f'{m["symbol"]}  ·  PREDICTIVE ANALYSIS', size=19, weight="bold",
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


def file_name(symbol: str, when: datetime | None = None) -> str:
    return f"predictive-analysis-{symbol}-{(when or datetime.now()):%Y-%m-%d}.pdf"
