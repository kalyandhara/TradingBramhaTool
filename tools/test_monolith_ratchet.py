"""A ratchet on `dashboard_app.py` — B-87.

B-87 is "extract one page per session", explicitly *ongoing, no big bang*. An
ongoing item with no measurement is a wish: the file has been growing about 500
lines a week and nothing noticed, because no page body can be unit-tested — which
is the problem it describes.

So this is not a fix. It is a **ratchet**: the numbers below may go DOWN freely
and may not go UP without someone editing this file and saying why. That converts
"we should extract pages" from an intention into something that fails a build.

**Every number here is a debt, not a target.** None is a healthy value. They are
today's readings, recorded so the direction of travel is visible.

Why a ratchet rather than an extraction in this session: page bodies live inline
under `if current_page == "X":` at module scope and close over module-level
state, so moving one is a real refactor of the product's main surface, with no
page-level tests to catch a mistake. Doing it badly to close a P3 item would be
the worst trade on the page.

Run:  python -m pytest tools/test_monolith_ratchet.py -q
"""
from __future__ import annotations

import ast
import pathlib

import pytest

APP = pathlib.Path(__file__).resolve().parent / "dashboard_app.py"

#: Measured 2026-09-16. Lower these when work lands; never raise them silently.
MAX_LINES = 13_900          # actual 13,846
MAX_SILENT_HANDLERS = 11    # actual 11 — `except: pass` / `except: continue`
# Raised 320 -> 324 on 2026-09-18 for the two Home strips: the index charts and
# the breadth bars. Each contributed exactly two statements — an import and its
# `if current_page == "Home"` call site — while the fetches, the cards and the
# figures live in tools/index_strip.py and tools/breadth_strip.py. A feature
# that arrives as a module plus one call site is what this ratchet is meant to
# encourage, which is why these raises are recorded rather than silent.
MAX_MODULE_STATEMENTS = 324  # actual 324
MAX_RAW_HTML_RENDERS = 120  # actual ~112 `unsafe_allow_html=True`


@pytest.fixture(scope="module")
def src() -> str:
    return APP.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def tree(src) -> ast.Module:
    return ast.parse(src)


def _silent_handlers(tree: ast.Module) -> list[int]:
    """Lines of handlers whose entire body is `pass` or `continue`.

    Counted with `ast`, not grep: a docstring-only handler reads the same to a
    regex, and the point of the number is that it be trustworthy enough to gate on.
    """
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.ExceptHandler):
            continue
        body = [s for s in n.body
                if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
        if len(body) == 1 and isinstance(body[0], (ast.Pass, ast.Continue)):
            out.append(n.lineno)
    return out


def test_the_file_does_not_grow(src):
    n = len(src.splitlines())
    assert n <= MAX_LINES, (
        f"dashboard_app.py is {n} lines, over the {MAX_LINES} ratchet. Extract a "
        f"page into tools/pages/ rather than raising this number.")


def test_silent_exception_handlers_do_not_multiply(tree):
    """Bandit counts 117 of these across the tree (77 pass, 40 continue). They are
    mostly legitimate best-effort paths, which is exactly why the count needs a
    ceiling: each new one is individually defensible and the total is not."""
    found = _silent_handlers(tree)
    assert len(found) <= MAX_SILENT_HANDLERS, (
        f"{len(found)} silent handlers (was {MAX_SILENT_HANDLERS}) at lines "
        f"{found}. Log the exception at debug rather than swallowing it.")


def test_module_level_statements_do_not_multiply(tree):
    """Page bodies live at module scope, so this is a proxy for "how much of the
    product is unreachable from a test". It falls when a page is extracted."""
    n = len(tree.body)
    assert n <= MAX_MODULE_STATEMENTS, (
        f"{n} module-level statements, over {MAX_MODULE_STATEMENTS}.")


def test_raw_html_renders_do_not_multiply(src):
    n = src.count("unsafe_allow_html=True")
    assert n <= MAX_RAW_HTML_RENDERS, (
        f"{n} raw-HTML renders, over {MAX_RAW_HTML_RENDERS}. Prefer a helper in "
        f"report_style so the markup has one owner.")


def test_the_ratchet_numbers_are_close_to_reality(src, tree):
    """A ceiling far above the actual value is not a ratchet, it is decoration.

    If work lands that drops these a long way, this test fails and asks for the
    ceilings to be lowered — which is the only way a ratchet keeps its grip.
    """
    checks = [
        ("lines", len(src.splitlines()), MAX_LINES, 200),
        ("silent handlers", len(_silent_handlers(tree)), MAX_SILENT_HANDLERS, 3),
        ("module statements", len(tree.body), MAX_MODULE_STATEMENTS, 20),
        ("raw html", src.count("unsafe_allow_html=True"), MAX_RAW_HTML_RENDERS, 20),
    ]
    slack = [(name, actual, ceiling) for name, actual, ceiling, tol in checks
             if ceiling - actual > tol]
    assert not slack, (
        f"these ceilings are now far above reality — lower them: {slack}")


def test_the_pages_package_is_where_extraction_goes():
    """Documents the destination so the next session does not have to decide it.

    Not created empty: an empty package is a claim that work started. It appears
    with the first extracted page.
    """
    assert APP.is_file()
    pages = APP.parent / "pages"
    if pages.exists():
        assert (pages / "__init__.py").is_file(), (
            "tools/pages exists without __init__.py — half-made package")
