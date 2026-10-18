"""Extracted dashboard pages — the destination B-87 documented and left empty.

B-87 deliberately did not create this package: *"an empty package is a claim
that work has started."* It is created now because work has.

══ WHY `desk_pages/` AND NOT THE DOCUMENTED `pages/` ═══════════════════════════

B-87 named `tools/pages/` as the destination. **That name is taken.** Streamlit
auto-discovers a directory called `pages/` next to the entrypoint and turns
every module in it into a page of its OWN multipage nav — so the first
extraction shipped a second, framework-generated navigation strip reading
"dashboard app / astro timing" above this desk's own nav, and `astro_timing.py`
became independently routable outside the dispatch that is supposed to own it.

Caught in the browser, not in review: nothing about the import fails, the page
still renders, and the only symptom is two navigations on screen. A convention
this repo documented for itself collided with a convention the framework
enforces silently, and the framework wins.

══ WHY A REGISTRY AND NOT ONE IMPORT PER PAGE ══════════════════════════════════

`dashboard_app.py` carries two ratchets, and the naive extraction moves them in
opposite directions: every page taken out drops ~700 LINES but adds an import
and a call site, so the MODULE-STATEMENT count creeps up with each one. A
refactor that makes one ratchet worse every time it makes the other better is a
refactor nobody will finish — and this repo has already raised the statement
ceiling twice (320 → 324) rather than lowering it once.

So the dispatch is paid for ONCE. `dashboard_app.py` gains exactly two
statements in total, ever:

    import pages
    if pages.handles(current_page): pages.render(current_page)

and each extraction after this one REMOVES a page's `if` block while adding
nothing — so the statement count now falls with every page, which is the
direction the ratchet was installed to enforce.

══ THE RULE FOR ADDING A PAGE ══════════════════════════════════════════════════

1. The page body must touch no module-level state in `dashboard_app.py` beyond
   what it can import for itself. Check it the way this one was checked, with
   `ast` rather than grep — a name used inside 700 lines is easy to miss.
2. Move it verbatim. Dedent and wrap in `render()`, change nothing else. A move
   and an edit in one commit is a move you cannot verify.
3. Add one line to `PAGES` below.
4. Delete the `if current_page == "..."` block from `dashboard_app.py` and
   lower the ratchets in `test_monolith_ratchet.py` to the new reading.

Modules are imported LAZILY, inside `render`. A page that pulls a heavy or
optional dependency at import time must not slow down — or break — every other
page on the dashboard just by existing in this registry.
"""
from __future__ import annotations

import importlib

#: page label (exactly as the nav writes it) -> module name in this package.
PAGES: dict[str, str] = {
    "Astro Timing": "astro_timing",
    "Telegram Signals": "telegram_signals",
    "SVP Structure": "svp_structure",
    "Scheduler Hub": "scheduler_hub",
    "Other Screeners": "other_screeners",
    "Pipeline Log": "pipeline_log",
    "High-Growth Screener": "high_growth_screener",
    "Sector wise Navigation": "sector_lobby",
    "Glossary": "glossary",
}


def handles(page: str | None) -> bool:
    """True when this package owns that page."""
    return page in PAGES


def render(page: str) -> None:
    """Import the page's module and run it.

    Raises KeyError for an unknown page rather than rendering nothing: a nav
    entry that silently draws a blank screen is the failure mode this registry
    would otherwise introduce, and it would look like a broken page rather than
    a missing registration.
    """
    mod = importlib.import_module(f"{__name__}.{PAGES[page]}")
    mod.render()


def home_header(cards, is_home: bool):
    """B-179. Home is not a registered page — it only borrows panes from
    `home_layout`. Lazy, like `render`, and one call site in the monolith."""
    return importlib.import_module(f"{__name__}.home_layout").header(cards, is_home)


def home_rail(db) -> None:
    """B-179. The left watchlist/sector rail on Home.

    Guarded: it renders before the centre block in the monolith, so an
    exception here would otherwise stop the script and leave the centre pane
    (the decision surface) blank. A broken rail is a warning in the rail.
    """
    try:
        importlib.import_module(f"{__name__}.home_layout").render_rail(db)
    except Exception as e:
        import logging
        import streamlit as st
        logging.getLogger(__name__).exception("home rail failed")
        st.warning(f"Watchlist rail unavailable: {e}")
