"""Every text colour the desk uses must be readable — B-161.

Measured 2026-10-13 on the live Home page: the gain green #16a34a read at 3.24:1
on the cream surface and the amber headings #d97706 at 3.13:1, against WCAG AA's
4.5:1 for normal text. They were also hard-coded outside the token table (26
times in dashboard_app.py alone), so fixing the token would not have reached them.

Pinned here:

* every TEXT token clears 4.5:1 on every page surface (surface, surface_alt,
  surface_warm, plain white for the PDF/email) AND on its own tint — the chip /
  callout pairing `_TONE` renders (fg on soft);
* "absent" stays lighter than body text (it means "no data", and must still
  read as de-emphasised) while passing;
* the retired colours do not come back anywhere in the Python code.

Run:  python -m pytest tools/test_report_style_contrast.py -q
"""
import re
from pathlib import Path

import pytest

import report_style as rs

AA = 4.5
SURFACES = ("surface", "surface_alt", "surface_warm")
WHITE = "#ffffff"
RETIRED = ("#16a34a", "#d97706", "#9ca3af", "#dc2626")   # B-161: failed AA as text


def _lum(hexcolor: str) -> float:
    h = hexcolor.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a: str, b: str) -> float:
    x, y = _lum(a), _lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


TEXT_TOKENS = ("text", "text_body", "text_muted", "good", "risk", "accent", "info", "absent")
TINT = {"good": "good_soft", "risk": "risk_soft", "accent": "accent_soft",
        "info": "info_soft", "absent": "absent_soft"}


@pytest.mark.parametrize("tok", TEXT_TOKENS)
def test_text_token_is_readable_on_every_surface(tok):
    fg = rs.TOKENS[tok]
    for s in SURFACES:
        assert contrast(fg, rs.TOKENS[s]) >= AA, f"{tok} {fg} on {s}"
    assert contrast(fg, WHITE) >= AA, f"{tok} {fg} on white"


@pytest.mark.parametrize("tok", sorted(TINT))
def test_tone_pair_is_readable(tok):
    fg, bg = rs.TOKENS[tok], rs.TOKENS[TINT[tok]]
    assert contrast(fg, bg) >= AA, f"{tok} {fg} on {TINT[tok]} {bg}"


def test_absent_still_reads_as_de_emphasised():
    s = rs.TOKENS["surface"]
    assert contrast(rs.TOKENS["absent"], s) < contrast(rs.TOKENS["text_body"], s)


def test_retired_colours_do_not_come_back():
    root = Path(__file__).resolve().parent
    files = [p for p in list(root.glob("*.py")) + list(root.glob("desk_pages/*.py"))
             if p.name != Path(__file__).name]
    hits = []
    for p in files:
        text = p.read_text(encoding="utf-8", errors="replace").lower()
        for col in RETIRED:
            for m in re.finditer(re.escape(col), text):
                line = text.count("\n", 0, m.start()) + 1
                hits.append(f"{p.name}:{line} {col}")
    assert not hits, "retired low-contrast colours: " + ", ".join(hits[:20])
