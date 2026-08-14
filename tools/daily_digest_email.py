#!/usr/bin/env python3
"""
daily_digest_email.py — Daily Market Digest email for Trading Bramha.

Composes a self-contained HTML email from live market data and sends it
via Gmail SMTP (App Password). Safe to run headlessly after market close
or first thing in the morning.

Data sources (all local, no external APIs beyond yfinance):
  • market_brief     → global index / commodity / FX quotes + sector breadth
  • sentiment_index  → composite 0-100 score + band
  • market_verdict   → STAND DOWN / SELECTIVE / TRADE / AGGRESSIVE
  • portfolio_db     → daily_opportunities, open positions, watchlist, alerts
  • panchang         → Rahu Kaal, Tithi, Hora (optional; skipped if ephem missing)

Gmail credentials are stored in the trading_bramha.db settings table:
  key "digest_gmail_user"     → sender address (e.g. kalyan.dhara@gmail.com)
  key "digest_gmail_app_pw"   → 16-char App Password (NOT your Google password)
  key "digest_to_email"       → recipient address (defaults to sender)

CLI:
  python daily_digest_email.py               # send today's digest
  python daily_digest_email.py --dry-run     # render HTML to stdout, no send
  python daily_digest_email.py --to foo@bar  # override recipient
  python daily_digest_email.py --configure   # interactive credential setup
"""

from __future__ import annotations

import argparse
import json
import smtplib
import sys
from datetime import date, datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import portfolio_db as db

IST = timezone(timedelta(hours=5, minutes=30))

# ──────────────────────────────────────────────────────────────────────────────
# Credential helpers
# ──────────────────────────────────────────────────────────────────────────────

def get_credentials() -> tuple[str | None, str | None, str | None]:
    """(sender, app_password, recipient) from the DB settings table."""
    sender = db.get_setting("digest_gmail_user")
    pw     = db.get_setting("digest_gmail_app_pw")
    to     = db.get_setting("digest_to_email") or sender
    return sender, pw, to


def configure_credentials() -> None:
    """Interactive prompts to store Gmail credentials in the DB."""
    db.init_db()
    print("=== Trading Bramha — Daily Digest Email Setup ===")
    print("You need a Gmail App Password (not your account password).")
    print("Create one at: https://myaccount.google.com/apppasswords\n")
    sender = input("Gmail sender address: ").strip()
    pw     = input("Gmail App Password (16 chars, no spaces): ").strip()
    to     = input(f"Recipient address [{sender}]: ").strip() or sender
    db.set_setting("digest_gmail_user", sender)
    db.set_setting("digest_gmail_app_pw", pw)
    db.set_setting("digest_to_email", to)
    print(f"\nSaved. Run without --configure to send today's digest to {to}.")


# ──────────────────────────────────────────────────────────────────────────────
# Data collection
# ──────────────────────────────────────────────────────────────────────────────

def _collect_market_brief() -> dict[str, Any]:
    try:
        import market_brief as mb
        snapshot  = mb.global_snapshot()
        breadth   = mb.sector_breadth()
        return {"snapshot": snapshot, "breadth": breadth, "error": None}
    except Exception as exc:
        return {"snapshot": None, "breadth": None, "error": str(exc)}


def _collect_sentiment() -> dict[str, Any]:
    try:
        import sentiment_index as si
        reading = si.compute_sentiment(persist=False)
        return reading
    except Exception as exc:
        return {"error": str(exc)}


def _collect_verdict(reading: dict[str, Any]) -> dict[str, Any]:
    try:
        import market_verdict as mv
        positions_df = db.get_open_positions()
        portfolio = None
        if not positions_df.empty and "entry_price" in positions_df.columns:
            portfolio = {"positions_count": len(positions_df)}
        return mv.build_verdict(reading, portfolio=portfolio)
    except Exception as exc:
        return {"verdict": "UNKNOWN", "error": str(exc)}


def _collect_opportunities(run_date: str) -> list[dict]:
    try:
        conn = db.get_connection()
        rows = conn.execute(
            "SELECT rank, symbol, score, overall_rating, confluence, scanners, "
            "sector, industry, close, entry, stop, target, market_verdict "
            "FROM daily_opportunities WHERE run_date = ? ORDER BY rank LIMIT 10",
            (run_date,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def _collect_positions() -> list[dict]:
    try:
        df = db.get_open_positions()
        if df.empty:
            return []
        return df.to_dict("records")
    except Exception:
        return []


def _collect_panchang(today: date) -> dict[str, Any] | None:
    try:
        import panchang
        import ephem  # noqa: F401 — confirm dep present
        MUMBAI = panchang.Place(lat=19.076, lon=72.8777, tz_offset=5.5)
        now = datetime.now(IST)
        return panchang.panchang(today, MUMBAI, now)
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Color / tone helpers (email-safe, no CSS vars)
# ──────────────────────────────────────────────────────────────────────────────

_PALETTE = {
    "bg":         "#fffdf8",
    "bg_alt":     "#f7efe3",
    "border":     "#e5cfae",
    "text":       "#3a2a1e",
    "text_body":  "#5c4a3a",
    "text_muted": "#7a6858",
    "accent":     "#d97706",
    "accent_bg":  "#fde0c0",
    "good":       "#16a34a",
    "good_bg":    "#e8f5e9",
    "risk":       "#dc2626",
    "risk_bg":    "#fef2f2",
    "info":       "#2563eb",
    "info_bg":    "#eef4ff",
    "muted":      "#9ca3af",
    "muted_bg":   "#f3f4f6",
}

_VERDICT_COLOR = {
    "STAND DOWN": (_PALETTE["risk"],   _PALETTE["risk_bg"]),
    "SELECTIVE":  (_PALETTE["accent"], _PALETTE["accent_bg"]),
    "TRADE":      (_PALETTE["good"],   _PALETTE["good_bg"]),
    "AGGRESSIVE": (_PALETTE["good"],   _PALETTE["good_bg"]),
    "NO EDGE":    (_PALETTE["muted"],  _PALETTE["muted_bg"]),
    "UNKNOWN":    (_PALETTE["muted"],  _PALETTE["muted_bg"]),
}

_BAND_COLOR = {
    "Strong Sell": _PALETTE["risk"],
    "Sell":        _PALETTE["risk"],
    "Neutral":     _PALETTE["accent"],
    "Buy":         _PALETTE["good"],
    "Strong Buy":  _PALETTE["good"],
}

def _pct_color(pct: float | None) -> str:
    if pct is None:
        return _PALETTE["muted"]
    return _PALETTE["good"] if pct >= 0 else _PALETTE["risk"]

def _pct_arrow(pct: float | None) -> str:
    if pct is None:
        return "—"
    arrow = "▲" if pct >= 0 else "▼"
    return f"{arrow} {abs(pct):.2f}%"


# ──────────────────────────────────────────────────────────────────────────────
# HTML sections
# ──────────────────────────────────────────────────────────────────────────────

def _style() -> str:
    p = _PALETTE
    return f"""
<style>
  body {{ margin:0; padding:0; background:{p['bg']}; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif; color:{p['text']}; }}
  .wrap {{ max-width:640px; margin:0 auto; background:{p['bg']}; }}
  .header {{ background:{p['text']}; padding:24px 28px; }}
  .header-title {{ color:#fff; font-size:22px; font-weight:700; margin:0; letter-spacing:-0.3px; }}
  .header-sub {{ color:{p['border']}; font-size:13px; margin:4px 0 0; }}
  .section {{ padding:20px 28px 8px; }}
  .section-label {{ font-size:11px; font-weight:700; letter-spacing:0.8px; text-transform:uppercase;
                    color:{p['text_muted']}; margin:0 0 10px; padding-bottom:6px;
                    border-bottom:1px solid {p['border']}; }}
  table.quotes {{ width:100%; border-collapse:collapse; font-size:13px; }}
  table.quotes td {{ padding:5px 4px; border-bottom:1px solid {p['bg_alt']}; }}
  table.quotes .label {{ color:{p['text_body']}; width:55%; }}
  table.quotes .price {{ text-align:right; color:{p['text_muted']}; }}
  table.quotes .chg   {{ text-align:right; font-weight:600; width:90px; }}
  .group-head {{ font-size:10px; font-weight:700; text-transform:uppercase;
                 letter-spacing:0.6px; color:{p['muted']}; padding:8px 4px 3px; }}
  .verdict-pill {{ display:inline-block; padding:4px 14px; border-radius:20px;
                   font-size:13px; font-weight:700; letter-spacing:0.4px; }}
  .sentiment-bar-wrap {{ background:{p['bg_alt']}; border-radius:6px; height:10px; overflow:hidden; margin:8px 0 4px; }}
  .sentiment-bar {{ height:10px; border-radius:6px; }}
  .opp-row {{ border:1px solid {p['border']}; border-radius:6px; padding:10px 12px;
              margin-bottom:8px; background:{p['bg']}; }}
  .opp-symbol {{ font-size:15px; font-weight:700; color:{p['text']}; }}
  .opp-meta {{ font-size:12px; color:{p['text_muted']}; margin-top:2px; }}
  .chip {{ display:inline-block; font-size:10px; font-weight:600; padding:2px 7px;
           border-radius:10px; background:{p['info_bg']}; color:{p['info']}; margin:1px; }}
  .pos-row {{ border-bottom:1px solid {p['bg_alt']}; padding:7px 0; font-size:13px; }}
  .pos-row:last-child {{ border-bottom:none; }}
  .footer {{ padding:16px 28px 24px; font-size:11px; color:{p['text_muted']}; border-top:1px solid {p['border']}; }}
  .panchang-row {{ font-size:12px; color:{p['text_body']}; padding:3px 0; }}
  .panchang-key {{ color:{p['text_muted']}; display:inline-block; width:110px; }}
  .empty-note {{ color:{p['text_muted']}; font-size:13px; font-style:italic; padding:4px 0 12px; }}
</style>"""


def _header_html(today: date, verdict: str, verdict_color: tuple[str, str]) -> str:
    fg, bg = verdict_color
    weekday = today.strftime("%A")
    date_str = today.strftime("%d %B %Y")
    return f"""
<div class="header">
  <p class="header-title">Trading Bramha · Daily Digest</p>
  <p class="header-sub">{weekday}, {date_str} &nbsp;·&nbsp;
    <span style="color:{fg};background:{bg};padding:2px 10px;border-radius:10px;
                 font-weight:700;font-size:12px;">{verdict}</span>
  </p>
</div>"""


def _quotes_html(snapshot: dict[str, Any] | None) -> str:
    if not snapshot or snapshot.get("error"):
        return '<p class="empty-note">Market data unavailable.</p>'
    quotes = snapshot.get("quotes", [])
    if not quotes:
        return '<p class="empty-note">No quotes fetched.</p>'

    import market_brief as mb
    rows_by_group: dict[str, list] = {}
    for q in quotes:
        rows_by_group.setdefault(q["group"], []).append(q)

    html = '<table class="quotes">'
    for group_key, label in mb.GROUP_LABELS.items():
        group_quotes = rows_by_group.get(group_key, [])
        if not group_quotes:
            continue
        html += f'<tr><td colspan="3" class="group-head">{label}</td></tr>'
        for q in group_quotes:
            pct = q.get("change_pct")
            last = q.get("last")
            price_str = f"{last:,.2f}" if last is not None else "—"
            stale_note = " &#9888;" if q.get("stale") else ""
            html += (
                f'<tr>'
                f'  <td class="label">{q["label"]}{stale_note}</td>'
                f'  <td class="price">{price_str}</td>'
                f'  <td class="chg" style="color:{_pct_color(pct)}">{_pct_arrow(pct)}</td>'
                f'</tr>'
            )
    html += "</table>"
    return html


def _breadth_html(breadth: dict[str, Any] | None) -> str:
    if not breadth:
        return ""
    sectors = breadth.get("sectors", [])
    if not sectors:
        return ""
    red  = sum(1 for s in sectors if s.get("direction") == "red")
    green = sum(1 for s in sectors if s.get("direction") == "green")
    total = len(sectors)
    color = _PALETTE["risk"] if red > green else _PALETTE["good"]
    return (
        f'<p style="font-size:13px;margin:8px 0 0;color:{_PALETTE["text_body"]}">'
        f'Sector breadth: <strong style="color:{color}">'
        f'{green} of {total} sectors green</strong>'
        f'</p>'
    )


def _sentiment_html(reading: dict[str, Any]) -> str:
    score = reading.get("composite")
    band  = reading.get("band", "—")
    if score is None:
        return '<p class="empty-note">Sentiment score unavailable.</p>'
    bar_color = _BAND_COLOR.get(band, _PALETTE["accent"])
    pct = min(100, max(0, score))
    return f"""
<div>
  <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px;">
    <span style="font-weight:700;color:{bar_color}">{band}</span>
    <span style="color:{_PALETTE['text_muted']}">{score:.1f} / 100</span>
  </div>
  <div class="sentiment-bar-wrap">
    <div class="sentiment-bar" style="width:{pct}%;background:{bar_color}"></div>
  </div>
</div>"""


def _verdict_detail_html(verdict_dict: dict[str, Any]) -> str:
    verdict = verdict_dict.get("verdict", "UNKNOWN")
    instruction = verdict_dict.get("instruction", "")
    size_pct = verdict_dict.get("position_size_pct")
    max_trades = verdict_dict.get("max_trades")
    cautions = verdict_dict.get("caution", [])
    favorable = verdict_dict.get("favorable", [])

    fg, bg = _VERDICT_COLOR.get(verdict, (_PALETTE["muted"], _PALETTE["muted_bg"]))

    html = f"""
<div style="background:{bg};border-radius:8px;padding:12px 14px;margin-bottom:8px;">
  <div style="font-size:18px;font-weight:700;color:{fg};margin-bottom:4px;">{verdict}</div>
  <div style="font-size:13px;color:{_PALETTE['text_body']}">{instruction}</div>"""
    if size_pct is not None or max_trades is not None:
        html += f"""
  <div style="margin-top:8px;font-size:12px;color:{_PALETTE['text_muted']}">
    Position size: <strong style="color:{fg}">{size_pct}%</strong> &nbsp;·&nbsp;
    Max trades: <strong style="color:{fg}">{max_trades}</strong>
  </div>"""
    html += "</div>"

    if cautions:
        html += f'<div style="font-size:12px;color:{_PALETTE["risk"]};margin:4px 0">&#9888; ' + " &nbsp;&middot;&nbsp; ".join(cautions) + "</div>"
    if favorable:
        html += f'<div style="font-size:12px;color:{_PALETTE["good"]};margin:4px 0">&#10003; ' + " &nbsp;&middot;&nbsp; ".join(favorable) + "</div>"

    return html


def _opportunities_html(opps: list[dict]) -> str:
    if not opps:
        return '<p class="empty-note">No opportunities found for today\'s run.</p>'
    html = ""
    for o in opps[:8]:
        symbol   = o.get("symbol", "?")
        score    = o.get("score") or 0
        rating   = o.get("overall_rating") or 0
        scanners = o.get("scanners") or ""
        sector   = o.get("sector") or ""
        industry = o.get("industry") or ""
        close    = o.get("close")
        entry    = o.get("entry")
        stop     = o.get("stop")
        target   = o.get("target")

        scanner_chips = ""
        for s in (scanners.split(",") if scanners else []):
            s = s.strip()
            if s:
                scanner_chips += f'<span class="chip">{s}</span>'

        levels = ""
        if entry:
            levels += f"Entry {entry:.2f}"
        if stop:
            levels += f" · SL {stop:.2f}"
        if target:
            levels += f" · TGT {target:.2f}"

        meta_parts = []
        if sector:
            meta_parts.append(sector)
        if industry:
            meta_parts.append(industry)
        meta = " › ".join(meta_parts)

        html += f"""
<div class="opp-row">
  <div style="display:flex;justify-content:space-between;align-items:baseline;">
    <span class="opp-symbol">{o.get("rank","")}.&nbsp;{symbol}</span>
    <span style="font-size:12px;color:{_PALETTE['text_muted']}">Score {score:.2f} &nbsp;·&nbsp; M1 {rating}/5</span>
  </div>
  <div class="opp-meta">{meta}</div>
  <div style="margin:5px 0 2px">{scanner_chips}</div>
  <div style="font-size:12px;color:{_PALETTE['text_muted']};margin-top:3px">{levels}</div>
</div>"""
    return html


def _positions_html(positions: list[dict]) -> str:
    if not positions:
        return '<p class="empty-note">No open positions.</p>'
    html = ""
    for p in positions[:10]:
        symbol = p.get("symbol", "?")
        entry  = p.get("entry_price", 0)
        qty    = p.get("quantity", 0)
        sl     = p.get("stop_loss")
        tgt    = p.get("target")
        edate  = p.get("entry_date", "")
        notes  = p.get("notes") or ""
        cost   = entry * qty if entry and qty else None
        html += f"""
<div class="pos-row">
  <strong>{symbol}</strong>
  <span style="color:{_PALETTE['text_muted']};font-size:12px;margin-left:8px">
    {qty:.0f} @ {entry:.2f} · Entry {edate}
    {f"· SL {sl:.2f}" if sl else ""}
    {f"· TGT {tgt:.2f}" if tgt else ""}
    {f"· Cost ₹{cost:,.0f}" if cost else ""}
  </span>
  {f'<div style="font-size:11px;color:{_PALETTE["text_muted"]};margin-top:1px">{notes}</div>' if notes else ""}
</div>"""
    if len(positions) > 10:
        html += f'<p style="font-size:12px;color:{_PALETTE["text_muted"]}">… and {len(positions)-10} more</p>'
    return html


def _panchang_html(p: dict[str, Any] | None) -> str:
    if p is None:
        return ""
    rows = []
    tithi = p.get("tithi") or {}
    if tithi:
        rows.append(("Tithi", f"{tithi.get('name','')} · {tithi.get('paksha','')} · {tithi.get('completion_pct',0):.0f}% done"))
    moon = p.get("moon_nakshatra") or {}
    if moon:
        rows.append(("Nakshatra", f"{moon.get('nakshatra','')} pada {moon.get('pada','')} · Lord {moon.get('lord','')}"))
    sun = p.get("sun_times") or {}
    if sun:
        sr = sun.get("sunrise")
        ss = sun.get("sunset")
        if sr and ss:
            rows.append(("Sun", f"Rise {sr.strftime('%H:%M')} · Set {ss.strftime('%H:%M')} IST"))
    day_parts = p.get("day_parts") or {}
    rk = day_parts.get("rahu_kaal")
    if rk:
        rows.append(("Rahu Kaal", f"{rk[0].strftime('%H:%M')} – {rk[1].strftime('%H:%M')} IST"))
    retro = p.get("retrogrades") or []
    if retro:
        rows.append(("Retrogrades", ", ".join(retro)))
    if not rows:
        return ""
    html = ""
    for key, val in rows:
        html += f'<div class="panchang-row"><span class="panchang-key">{key}</span>{val}</div>'
    return html


# ──────────────────────────────────────────────────────────────────────────────
# Full HTML assembly
# ──────────────────────────────────────────────────────────────────────────────

def render_html(today: date | None = None) -> str:
    today = today or datetime.now(IST).date()

    # collect data
    market   = _collect_market_brief()
    reading  = _collect_sentiment()
    verdict  = _collect_verdict(reading)
    run_date = today.isoformat()
    opps     = _collect_opportunities(run_date)
    positions = _collect_positions()
    panch    = _collect_panchang(today)

    verdict_str = verdict.get("verdict", "UNKNOWN")
    v_colors    = _VERDICT_COLOR.get(verdict_str, (_PALETTE["muted"], _PALETTE["muted_bg"]))
    now_ist     = datetime.now(IST).strftime("%H:%M IST")

    snapshot = market.get("snapshot")
    breadth  = market.get("breadth")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Trading Bramha · Daily Digest · {today.strftime('%d %b %Y')}</title>
  {_style()}
</head>
<body>
<div class="wrap">

{_header_html(today, verdict_str, v_colors)}

<!-- VERDICT -->
<div class="section">
  <p class="section-label">Market Verdict</p>
  {_verdict_detail_html(verdict)}
</div>

<!-- SENTIMENT -->
<div class="section">
  <p class="section-label">Sentiment Index</p>
  {_sentiment_html(reading)}
</div>

<!-- GLOBAL MARKETS -->
<div class="section">
  <p class="section-label">Global Markets</p>
  {_quotes_html(snapshot)}
  {_breadth_html(breadth)}
</div>

<!-- OPPORTUNITIES -->
<div class="section">
  <p class="section-label">Today's Opportunities <span style="font-size:10px;font-weight:400;text-transform:none;color:{_PALETTE['text_muted']}">(daily funnel run)</span></p>
  {_opportunities_html(opps)}
</div>

<!-- PORTFOLIO -->
<div class="section">
  <p class="section-label">Open Positions</p>
  {_positions_html(positions)}
</div>"""

    # Panchang (optional)
    panchang_html = _panchang_html(panch)
    if panchang_html:
        html += f"""
<!-- PANCHANG -->
<div class="section">
  <p class="section-label">Panchang</p>
  {panchang_html}
</div>"""

    html += f"""

<div class="footer">
  Generated {now_ist} &nbsp;&middot;&nbsp; Trading Bramha &nbsp;&middot;&nbsp; Not investment advice.
</div>

</div><!-- /wrap -->
</body>
</html>"""
    return html


# ──────────────────────────────────────────────────────────────────────────────
# Send
# ──────────────────────────────────────────────────────────────────────────────

def send_digest(to_override: str | None = None, today: date | None = None) -> None:
    today = today or datetime.now(IST).date()
    sender, pw, recipient = get_credentials()
    recipient = to_override or recipient

    if not sender or not pw:
        sys.exit(
            "No Gmail credentials found. Run:\n"
            "  python daily_digest_email.py --configure"
        )
    if not recipient:
        sys.exit("No recipient address. Run --configure or pass --to.")

    print(f"Rendering digest for {today} …")
    html = render_html(today)

    subject = (
        f"Trading Bramha · Daily Digest · {today.strftime('%a %d %b %Y')}"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = recipient
    msg.attach(MIMEText(html, "html", "utf-8"))

    print(f"Sending to {recipient} via {sender} …")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, pw)
        smtp.sendmail(sender, [recipient], msg.as_bytes())
    print("Sent.")


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Send the daily Trading Bramha market digest email.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Render HTML and print to stdout; do not send.")
    ap.add_argument("--to", metavar="EMAIL",
                    help="Override recipient address for this run.")
    ap.add_argument("--configure", action="store_true",
                    help="Interactively store Gmail credentials.")
    ap.add_argument("--date", metavar="YYYY-MM-DD",
                    help="Override date (default: today IST).")
    args = ap.parse_args()

    db.init_db()

    if args.configure:
        configure_credentials()
        return

    today = date.fromisoformat(args.date) if args.date else datetime.now(IST).date()

    if args.dry_run:
        import io
        html = render_html(today)
        # Use a UTF-8 wrapper so special chars don't fail on Windows CP1252 consoles.
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        print(html)
        sys.stdout.flush()
        return

    send_digest(to_override=args.to, today=today)


if __name__ == "__main__":
    main()
