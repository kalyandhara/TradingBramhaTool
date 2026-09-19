"""Tests for the extracted-page registry (B-87r).

    py -3 -m pytest tools/test_desk_pages.py -q

B-87 refused to extract a page because *"no page-level tests"* existed to catch
a mistake. That objection is answered here for the one structural thing that
CAN be tested without a browser: that the registry, the nav and the monolith
still agree about which pages exist and who owns them.

What is deliberately NOT tested: what the page renders. That needs Streamlit
running and was verified in the browser instead. A test that imported the page
module and asserted on `st` calls would pin the mock, not the page.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

import desk_pages

APP = pathlib.Path(__file__).resolve().parent / "dashboard_app.py"
HERE = pathlib.Path(__file__).resolve().parent


@pytest.fixture(scope="module")
def app_src() -> str:
    return APP.read_text(encoding="utf-8")


def test_every_registered_page_imports_and_has_render():
    """A registration pointing at a missing module fails only when a user
    clicks that nav entry, which is the worst time to find out."""
    assert desk_pages.PAGES, "the registry is empty — it should not exist yet"
    for label, mod_name in desk_pages.PAGES.items():
        import importlib
        mod = importlib.import_module(f"desk_pages.{mod_name}")
        assert callable(getattr(mod, "render", None)), (
            f"{label} -> desk_pages.{mod_name} has no callable render()")


def test_handles_is_exact_not_fuzzy():
    assert desk_pages.handles("Astro Timing")
    assert not desk_pages.handles("astro timing")   # the nav's exact label wins
    assert not desk_pages.handles("Home")
    assert not desk_pages.handles(None)


def test_unknown_page_raises_rather_than_rendering_nothing():
    """Silently drawing a blank screen would look like a broken page instead of
    a missing registration."""
    with pytest.raises(KeyError):
        desk_pages.render("Not A Page")


def test_extracted_pages_are_gone_from_the_monolith(app_src):
    """The move has to be a move. An extracted page whose `if` block is still
    in dashboard_app.py would render twice, or shadow the extracted copy."""
    tree = ast.parse(app_src)
    still_inline = []
    for n in tree.body:
        if not isinstance(n, ast.If):
            continue
        seg = ast.get_source_segment(app_src, n.test) or ""
        if "current_page" not in seg:
            continue
        for label in desk_pages.PAGES:
            if f'"{label}"' in seg:
                still_inline.append(label)
    assert not still_inline, (
        f"extracted but still inline in dashboard_app.py: {still_inline}")


def test_every_extracted_page_is_still_in_the_nav(app_src):
    """Extraction must not orphan a page. If the label vanished from the nav,
    the module is unreachable and the registry is a lie."""
    for label in desk_pages.PAGES:
        assert f'"{label}"' in app_src, (
            f"{label} is registered but no longer appears in dashboard_app.py "
            f"— check the nav groups")


def test_the_dispatch_is_paid_for_once(app_src):
    """The whole point of the registry: ONE call site, not one per page.

    If this grows to two, the statement ratchet starts creeping up again with
    every extraction and the refactor stops paying for itself.
    """
    assert app_src.count("dpages.render(") == 1
    assert app_src.count("dpages.handles(") == 1


def test_the_package_is_not_named_pages(app_src):
    """Streamlit auto-discovers a directory called `pages/` next to the
    entrypoint and builds its own multipage nav from it — which is exactly what
    happened on the first attempt, shipping a second navigation strip above the
    desk's own. B-87 documented `tools/pages/` as the destination; the name is
    taken, and this test is why nobody has to rediscover that.
    """
    assert not (HERE / "pages").exists(), (
        "tools/pages/ exists — Streamlit will treat it as a multipage app and "
        "render its own nav. The package is tools/desk_pages/ for that reason.")
