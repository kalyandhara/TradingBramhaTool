"""Scanner-card and Watchlist cell helpers — card HTML fragments, rating colours,
confluence chips, SVP and RS-walk cells.

Extracted verbatim from dashboard_app.py (B-171 monolith ratchet, 2026-10-17).
dashboard_app re-imports every name, so callers are unchanged.
"""
from __future__ import annotations

import opportunity_hub as oh
import pandas as pd
import portfolio_db as db
import report_style as rs
import scanner_templates as sc
import screener_scraper as ss


# ── Overall Rating (M1) — one cross-system quality score /100 ──────────────────
# Fuses the four scoring frameworks already computed elsewhere in the app into a
# single triage number, independent of which scanner matched. Weights bias toward
# Minervini as the most-referenced framework on the wiki; tune them in the Scanner
# Hub sidebar (changes apply on the next scan). See
# wiki/analyses/Dashboard-UI-Roadmap.md Milestone 1.
def _rating_color(r: int | None) -> str:
    """Color scale for the Overall Rating badge (matches Market Terminal source)."""
    if r is None:
        return "#7a6858"
    if r >= 85:
        return "#166534"   # green
    if r >= 70:
        return "#a14a0b"   # amber
    if r >= 50:
        return "#6b7280"   # grey
    return "#b91c1c"       # red


def _scanner_stats_html(card: dict) -> str:
    """Compact stat row (RS · Vol Q · From pivot · Vol ×50d) + fail-risk chips.
    Renders only the fields the card actually carries, so scanners that don't
    emit the richer metadata degrade to nothing."""
    def chip(label: str, value: str, color: str = "#5c4a3a") -> str:
        return (
            f'<span style="display:inline-block;background:#f7efe3;border-radius:6px;'
            f'padding:2px 8px;margin:0 6px 4px 0;font-size:11px;color:{color};">'
            f'<b style="color:#7a6858;font-weight:600;">{label}</b> {value}</span>'
        )

    parts = []
    if "rs_rank" in card:
        rs = card["rs_rank"]
        parts.append(chip("RS", f"{rs:.0f}", "#166534" if rs >= 80 else "#5c4a3a"))
    if "base_q" in card:
        bq = card["base_q"]
        parts.append(chip("Base Q", f"{bq:.0f}", "#166534" if bq >= 65 else "#5c4a3a"))
    if card.get("vol_q"):
        parts.append(chip("Vol Q", card["vol_q"]))
    if "from_pivot" in card:
        parts.append(chip("From pivot", f'{card["from_pivot"]:+.1f}%'))
    if "vol_x50d" in card:
        vx = card["vol_x50d"]
        parts.append(chip("Vol ×50d", f"{vx:.1f}×", "#166534" if vx >= 1.5 else "#5c4a3a"))
    stats = "".join(parts)

    risks = card.get("fail_risk") or []
    risk_html = "".join(
        f'<span style="display:inline-block;background:#fef2f2;color:#b45309;'
        f'border:1px solid #fde0c0;border-radius:6px;padding:2px 8px;'
        f'margin:0 6px 4px 0;font-size:11px;">⚠ {r}</span>'
        for r in risks
    )
    if not stats and not risk_html:
        return ""
    return (f'<div style="margin:8px 0 4px 0;">{stats}{risk_html}</div>')


def _fam_of(row) -> list[str]:
    """Family list for a stored shortlist row.

    Rows written before the family columns existed carry NULL there, so the
    families are re-derived from the stored scanner list rather than rendering
    a blank — the mapping is deterministic, so an old row and a new one show
    the same thing.
    """
    stored = row.get("family_names") if hasattr(row, "get") else None
    if stored and pd.notna(stored):
        return [f.strip() for f in str(stored).split(",") if f.strip()]
    fired = [s.strip() for s in str(row.get("scanners") or "").split(",") if s.strip()]
    fams, _pts, _risk = oh.tally_evidence(fired)
    return fams


def _confluence_chips(n_scanners: int, families: list[str] | int | None) -> str:
    """The headline pair — raw scanner count beside the independent-family count.

    Both are shown on purpose. The raw count is what you asked the pipeline for;
    the family count is what the ranking actually spends, and the gap between
    them is the point: "7 scanners · 2 families" says six of those seven were
    reading the same fact about the chart.
    """
    if isinstance(families, int):
        fam_n, fam_list = families, []
    else:
        fam_list = list(families or [])
        fam_n = len(fam_list)
    detail = (" — " + ", ".join(fam_list)) if fam_list else ""
    # One family = no confluence at all, however many scanners fired.
    fam_tone = "good" if fam_n >= 3 else ("warn" if fam_n == 2 else "neutral")
    ffg, fbg = rs.tone_colors(fam_tone)
    return (
        f'<span class="tb-chip" title="Scanners that fired on this name" '
        f'style="background:{rs.TOKENS["surface_alt"]};'
        f'color:{rs.TOKENS["text_body"]};">{n_scanners} scanners</span>'
        f'<span class="tb-chip" title="Independent scanner families{detail}. '
        f'Correlated scanners are capped at their best member — this is what '
        f'the score spends." style="background:{fbg};color:{ffg};'
        f'font-weight:600;">{fam_n} famil{"y" if fam_n == 1 else "ies"}</span>')


def _card_trade_fundamentals_html(sym: str, card: dict) -> str:
    """CMP · PMax T1/T2/T3 (derived from trade plan) · PE — compact info strip."""
    def _cell(label: str, value: str, color: str = "#5c4a3a") -> str:
        return (
            f'<div style="display:inline-block;background:#f7efe3;border-radius:6px;'
            f'padding:3px 9px;margin:0 5px 4px 0;font-size:11px;">'
            f'<span style="color:#7a6858;font-weight:600;">{label}</span>'
            f'<span style="color:{color};font-weight:700;margin-left:4px;">{value}</span></div>'
        )

    parts: list[str] = []

    # CMP — last close (entry ≈ last close for all scanners)
    cmp = card.get("entry") or card.get("close")
    if cmp is not None:
        parts.append(_cell("CMP", f"₹{cmp:,.1f}"))

    # PMax targets derived from the trade plan emitted by the scanner.
    # T1 = primary target, T2 = 2R extension, T3 = 3R extension.
    entry = card.get("entry") or cmp
    stop  = card.get("stop")
    t1    = card.get("target")
    t2    = card.get("target2")
    if entry is not None and stop is not None and t1 is not None:
        risk = entry - stop
        if risk > 0:
            t2 = t2 or round(entry + 2 * risk, 1)
            t3 = round(entry + 3 * risk, 1)
            parts.append(_cell("T1", f"₹{t1:,.1f}", "#166534"))
            parts.append(_cell("T2", f"₹{t2:,.1f}", "#166534"))
            parts.append(_cell("T3", f"₹{t3:,.1f}", "#166534"))

    # Fundamentals — from cached yfinance .info (disk cache, not network).
    try:
        fund = sc.fetch_fundamentals_yf(sym) or {}
    except Exception:
        fund = {}

    pe = fund.get("pe")
    if pe is not None:
        pe_color = "#b45309" if pe > 40 else ("#166534" if pe < 20 else "#5c4a3a")
        parts.append(_cell("PE", f"{pe:.1f}×", pe_color))

    # PEG — <1 cheap-for-growth (green), >2 pricey (amber). 'calc' = derived from
    # PE/earnings-growth rather than the vendor's own ratio (marked with ~).
    peg = fund.get("peg")
    if peg is not None:
        peg_color = "#166534" if peg < 1 else ("#b45309" if peg > 2 else "#5c4a3a")
        peg_txt = f"{'~' if fund.get('peg_src') == 'calc' else ''}{peg:.2f}"
        parts.append(_cell("PEG", peg_txt, peg_color))

    eps = fund.get("eps")
    if eps is not None:
        parts.append(_cell("EPS", f"₹{eps:,.2f}", "#166534" if eps > 0 else "#b45309"))

    ebitda_cr = fund.get("ebitda_cr")
    if ebitda_cr is not None:
        # ≥1 lakh-crore → abbreviate to "L Cr", else plain "₹N Cr".
        _eb = (f"₹{ebitda_cr / 1e5:,.2f}L Cr" if abs(ebitda_cr) >= 1e5
               else f"₹{ebitda_cr:,.0f} Cr")
        parts.append(_cell("EBITDA", _eb, "#166534" if ebitda_cr > 0 else "#b45309"))

    # Cash-flow margin (OCF ÷ revenue). Positive & fat = cash-generative (green);
    # negative = burning operating cash (amber).
    cfm = fund.get("cf_margin_pct")
    if cfm is not None:
        parts.append(_cell("CF%", f"{cfm:.1f}%",
                           "#166534" if cfm > 0 else "#b45309"))

    # Promoter pledge — not in yfinance. Read the screener.in disk cache (pure
    # local read, no network); populated by the Scanner Hub "Fetch pledge %"
    # button. High pledge is a risk flag → red above 5%.
    pledge = fund.get("pledge_pct")
    if pledge is None:
        try:
            _plrec = ss.read_pledge_cache(sym)
            if _plrec is not None:
                pledge = _plrec.get("pledge_pct")
        except Exception:
            pledge = None
    if pledge is not None:
        parts.append(_cell("Pledge", f"{pledge:.1f}%",
                           "#b91c1c" if pledge > 5 else "#166534"))

    if not parts:
        return ""
    return f'<div style="margin:6px 0 2px 0;">{"".join(parts)}</div>'


def _pct_tone(v) -> str:
    """Colour for a signed per-cent, or the muted token for an absent one."""
    if v is None:
        return rs.TOKENS["text_muted"]
    return rs.TOKENS["good"] if v > 0 else rs.TOKENS["risk"] if v < 0 else         rs.TOKENS["text_body"]


# B-75's four helpers live in `profit_walk_ui` rather than here. They are new
# UI code, and the B-87 ratchet's rule is that new UI code does not land in this
# file. `_pw()` is the whole of its footprint here: the call sites go straight
# through it, so mounting the column costs this file one function, not five.
def _pw():
    import profit_walk_ui as _pwu
    return _pwu


def _wl_rs_mom(df):
    """The RAW weighted trailing return behind `rs_walk`'s percentile.

    Computed straight from the frame the caller already holds — `rs_walk`'s own
    `weighted_return_asof`, not a second formula. The rank says where a name
    stands against the universe; this says what it actually returned, and a rank
    of 90 in a flat market is a different fact from a rank of 90 in a strong one.
    """
    try:
        import rs_walk as _rw
        return _rw.weighted_return_asof(df, offset=0)
    except Exception:
        return None


def _svp_cells(symbol: str, screen: dict) -> dict:
    """The two SVP cells for one row. One implementation, three mount points."""
    try:
        import svp_screen as _svp
        return _svp.cells(symbol, screen)
    except Exception:                                        # pragma: no cover
        return {"svp_hist_8w": "", "svp_factors": None}


def _svp_caption(screen: dict) -> str:
    """The staleness line every table showing these columns must print.

    The screen is built by a MANUAL two-command pipeline, not a scheduled job,
    so the file can be days old while the table around it is live. Presenting a
    stale profile as today's structure is the failure this caption exists to
    prevent, which is why the age is stated in hours and the as-of date is in
    the tooltip rather than both being left implicit.
    """
    if not screen or not screen.get("n"):
        return ""
    # The AS-OF range, not the file's mtime: rewriting the CSV to add a few
    # fresh names would reset the mtime and flatter every old row in it. The
    # dates below are what each row actually describes.
    lo, hi = screen.get("asof_min"), screen.get("asof_max")
    if lo and hi and lo != hi:
        when = f"bars from **{lo} – {hi}** (mixed)"
    elif hi:
        when = f"bars as of **{hi}**"
    else:
        age = screen.get("age_hours") or 0
        when = f"file written {age / 24:.1f} days ago"
    stale = False
    try:
        from datetime import date as _d
        stale = hi is not None and (_d.today() - _d.fromisoformat(str(hi))).days > 3
    except Exception:
        pass
    warn = " ⚠️ **stale** — rebuild before reading it as current" if stale else ""
    return (f"**SVP 8w / SVP fac** read from the session-profile screen — "
            f"{screen['n']} symbols, {when}{warn}. A name outside that screen "
            f"shows BLANK, which means no structure on file, not flat "
            f"structure. Structure only: the composite score and its BUY/SELL "
            f"direction measured a clean negative on 2026-08-29 and are not "
            f"shown anywhere on this desk.")


def _rs_walk_lookup() -> dict:
    """The stored RS-walk grid, or {} when none has been computed.

    Read-only and cheap. Every page that shows the column goes through this and
    `_rs_walk_cell` rather than formatting its own, so the `*` convention and the
    oldest-first order cannot drift between the Watchlist and the Scanner Hub.
    """
    try:
        return db.get_rs_walk()
    except Exception:
        return {}


def _rs_walk_cell(symbol: str, walk: dict) -> str:
    """One cell: `18 → 86 → 95 → 99`, with a trailing `*` for a non-constituent.

    Empty string when the symbol is not in the stored grid — a name nobody has
    ranked reads as blank, not as a rank of zero.
    """
    import rs_walk as _rw
    r = walk.get(str(symbol).strip().upper())
    if not r:
        return ""
    return _rw.format_walk(r) + ("" if r.get("in_universe") else " *")
