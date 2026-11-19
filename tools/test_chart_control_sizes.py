"""Chart Tool controls are big enough to hit and read — B-163.

Measured live 2026-10-13: the INDICATORS and range buttons were 17–18px tall
with 10px labels, the draw tools 24×22 — under the 24px minimum target size
(WCAG 2.5.8). This pins, from the stylesheet in chart_dashboard.html, that every
clickable control in the pane header, the range row and the draw toolbar
declares a height (or min-height) of at least 24px and a label of at least 11px.

Run:  python -m pytest tools/test_chart_control_sizes.py -q
"""
import re
from pathlib import Path

import pytest

HTML = (Path(__file__).resolve().parent / "chart_dashboard.html").read_text(encoding="utf-8")
STYLE = HTML.split("<style>", 1)[1].split("</style>", 1)[0]

MIN_TARGET = 24
MIN_LABEL = 11
CONTROLS = (".ph input[type=text]", ".ph select", ".ind-btn", ".nav-btn", ".qlink",
            ".range-btn", ".goto-date", ".theme-switch label", ".draw-btn")


def _rule(selector: str) -> str:
    """Body of the first top-level rule whose selector is exactly `selector`."""
    m = re.search(r"(?m)^" + re.escape(selector) + r"\s*\{([^}]*)\}", STYLE)
    assert m, f"no rule for {selector}"
    return m.group(1)


def _px(body: str, prop: str):
    m = re.search(r"(?<![-\w])" + prop + r"\s*:\s*([\d.]+)px", body)
    return float(m.group(1)) if m else None


@pytest.mark.parametrize("sel", CONTROLS)
def test_control_is_at_least_24px_tall(sel):
    body = _rule(sel)
    h = max(filter(None, (_px(body, "height"), _px(body, "min-height"))), default=None)
    assert h is not None and h >= MIN_TARGET, f"{sel}: height {h}"
    assert "box-sizing: border-box" in body, \
        f"{sel}: needs border-box so the border counts inside the 24px"


@pytest.mark.parametrize("sel", CONTROLS)
def test_control_label_is_at_least_11px(sel):
    size = _px(_rule(sel), "font-size")
    assert size is not None and size >= MIN_LABEL, f"{sel}: font-size {size}"


# ── B-164: Home and the Chart Tool read in the same two faces ────────────────
def _stack(s: str) -> list[str]:
    return [f.strip().strip("'\"") for f in s.split(",")]


def _var(name: str) -> str:
    m = re.search(r"--" + name + r"\s*:\s*([^;]+);", STYLE)
    assert m, f"--{name} not defined"
    return m.group(1)


def test_chart_fonts_match_home():
    import report_style as rs
    assert _stack(_var("font-sans")) == _stack(rs.SANS)
    assert _stack(_var("font-mono")) == _stack(rs.MONO)


def test_streamlit_config_fonts_match_home():
    import tomllib
    import report_style as rs
    cfg = tomllib.loads((Path(__file__).resolve().parent.parent / ".streamlit"
                         / "config.toml").read_text(encoding="utf-8"))["theme"]
    assert _stack(cfg["font"]) == _stack(rs.SANS)
    assert _stack(cfg["codeFont"]) == _stack(rs.MONO)


def test_chart_text_uses_the_font_tokens():
    assert "font-family: var(--font-sans)" in STYLE
    assert "Courier New" not in HTML.replace(_var("font-mono"), "")


def test_up_down_colours_live_in_one_place():
    """Owner decision 2026-10-14: keep TradingView teal/red on the chart, but as
    one definition each (CSS var + JS constant), not 83 hard-coded copies."""
    for hexc in ("#26a69a", "#ef5350"):
        assert HTML.lower().count(hexc) == 2, f"{hexc} hard-coded outside --up/--down and C_UP/C_DOWN"
    assert "const C_UP = '#26a69a', C_DOWN = '#ef5350';" in HTML
    assert re.search(r"--up:\s*#26a69a;", STYLE) and re.search(r"--down:\s*#ef5350;", STYLE)
