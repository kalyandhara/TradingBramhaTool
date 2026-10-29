"""Setup Intelligence as one styled card (HTML), from `stock_council.SetupIntel`.

Presentation only: every word and number comes from the council's evidence, so
the panel can never disagree with the Judge below it. Text from the analysis is
escaped before it reaches the page.
"""
from __future__ import annotations

import html
import re
from typing import Any

import report_style as rs

FOLD_AFTER = 5
_TONE = {"good": "good", "neutral": "warn", "bad": "risk"}
# First number in a line, with its unit: 27, +46%, ₹111.8, 1.6x, 0.5%.
_NUM = re.compile(r"(?<![\w.])([+\-−]?₹?\d[\d,]*(?:\.\d+)?(?:%|x)?)")

DISCLAIMER = ("Derived automatically from historical market data by our research "
              "algorithms. May be incomplete or inaccurate and can change between "
              "scans. Research and educational study only — not investment advice "
              "or a recommendation to buy, sell, or hold any security.")


def _colours(tone: str) -> tuple[str, str]:
    return rs.tone_colors(_TONE.get(tone, "neutral"))


def _line(text: str) -> str:
    """Escaped factor text with its first number in bold."""
    return _NUM.sub(r"<b>\1</b>", html.escape(text), count=1)


def _factor_list(title: str, items: list[str], mark: str, colour: str,
                 t: dict[str, str]) -> str:
    head = (f'<div style="font-size:11px;font-weight:700;letter-spacing:.06em;'
            f'text-transform:uppercase;color:{colour};margin-bottom:6px;">'
            f'{html.escape(title)} · {len(items)}</div>')
    if not items:
        return head + f'<div style="color:{t["text_muted"]};font-size:13px;">None detected.</div>'

    def li(x: str) -> str:
        return (f'<li style="display:flex;gap:8px;margin:0 0 6px;line-height:1.45;">'
                f'<span style="color:{colour};font-weight:700;flex:none;width:12px;">'
                f'{mark}</span><span>{_line(x)}</span></li>')

    ul = 'style="list-style:none;margin:0;padding:0;font-size:13.5px;"'
    body = f'<ul {ul}>' + "".join(li(x) for x in items[:FOLD_AFTER]) + "</ul>"
    rest = items[FOLD_AFTER:]
    if rest:
        body += (f'<details><summary style="cursor:pointer;color:{t["info"]};'
                 f'font-size:12.5px;margin:2px 0 6px 20px;">+{len(rest)} more</summary>'
                 f'<ul {ul}>' + "".join(li(x) for x in rest) + "</ul></details>")
    return head + body


def _balance(intel: Any, t: dict[str, str]) -> str:
    b, r = intel.bull_conviction, intel.bear_conviction
    if b is None or r is None or (b + r) <= 0:
        return ""
    good, risk = rs.tone_colors("good")[0], rs.tone_colors("risk")[0]
    w = round(b / (b + r) * 100, 1)
    net = "" if intel.net_score is None else f" · net {intel.net_score:+.0f}"
    return (f'<div style="display:flex;align-items:center;gap:8px;font-size:12px;'
            f'color:{t["text_muted"]};min-width:220px;">'
            f'<span style="color:{good};font-weight:700;">Bull {b:.1f}</span>'
            f'<div style="flex:1;height:6px;border-radius:3px;background:{risk};overflow:hidden;">'
            f'<div style="width:{w}%;height:100%;background:{good};"></div></div>'
            f'<span style="color:{risk};font-weight:700;">Bear {r:.1f}</span>'
            f'<span>{net}</span></div>')


def render_html(intel: Any, t: dict[str, str]) -> str:
    fg, tint = _colours(intel.status_tone)
    pill = (f'<span style="background:{tint};color:{fg};border:1px solid {fg}33;'
            f'border-radius:999px;padding:3px 10px;font-size:12px;font-weight:700;">'
            f'{html.escape(intel.status_label)}</span>')
    header = (f'<div style="display:flex;flex-wrap:wrap;align-items:center;gap:10px 16px;'
              f'margin-bottom:12px;">'
              f'<div style="font-size:17px;font-weight:700;color:{t["text"]};">Setup Intelligence</div>'
              f'{pill}<div style="flex:1;"></div>{_balance(intel, t)}</div>')

    tiles = "".join(
        f'<div style="flex:1 1 140px;background:{t["surface"]};border:1px solid {t["border"]};'
        f'border-left:3px solid {_colours(tone)[0]};border-radius:8px;padding:7px 10px;">'
        f'<div style="font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;'
        f'color:{t["text_muted"]};">{html.escape(label)}</div>'
        f'<div style="font-size:14px;font-weight:700;color:{_colours(tone)[0]};margin-top:2px;">'
        f'{html.escape(value)}</div></div>'
        for label, value, tone in intel.chips)
    strip = f'<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px;">{tiles}</div>'

    good, risk = rs.tone_colors("good")[0], rs.tone_colors("risk")[0]
    col = 'style="flex:1 1 300px;min-width:0;"'
    factors = (f'<div style="display:flex;flex-wrap:wrap;gap:12px 28px;margin-bottom:12px;">'
               f'<div {col}>{_factor_list("Supporting", intel.bullish_factors, "✓", good, t)}</div>'
               f'<div {col}>{_factor_list("Risks", intel.risk_factors, "!", risk, t)}</div></div>')

    view = (f'<div style="background:{tint};border-left:3px solid {fg};border-radius:6px;'
            f'padding:9px 12px;font-size:13.5px;color:{t["text"]};">'
            f'{html.escape(intel.overall_view)}</div>'
            f'<div style="font-size:11px;color:{t["text_muted"]};margin-top:8px;line-height:1.4;">'
            f'{DISCLAIMER}</div>')

    return (f'<div style="background:{t["surface"]};border:1px solid {t["border"]};'
            f'border-radius:12px;padding:16px 18px;margin:6px 0 12px;color:{t["text_body"]};">'
            f'{header}{strip}{factors}{view}</div>')
