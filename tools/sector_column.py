#!/usr/bin/env python3
"""sector_column.py — the Sector column, attached to any symbol table.

Companion to `sectors.py` (which owns the vocabulary) and `columns.py` (which
owns the column's label, tooltip and format). This module owns exactly one
thing: getting the canonical sector onto a dataframe that has a symbol in it.

── Why a module and not three helpers in `dashboard_app` ──────────────────────
That is where they started. `test_monolith_ratchet` refused them, and it was
right for a better reason than line count: a helper defined inside the page
monolith is unreachable from a test, and "does the Sector column land in the
right place, and stay blank rather than guessing" is precisely the kind of claim
that should be pinned by a test rather than by opening the app and looking.

── The rule the attachment follows ────────────────────────────────────────────
A symbol the monthly cache has never seen renders BLANK. Not "Unknown", not the
nearest label, not the sector of a similarly-named listing. This is the same
rule `sectors.from_yahoo` holds by returning None and `smallcap_universe.cap_bucket`
holds by leaving a non-constituent's bucket empty: outside NSE's broadest
constituent list there is no macro sector to give a name, and saying so is the
honest reading.

Distinguish that from an UNREACHABLE cache, which adds no column at all — a
column of blanks would assert "none of these names has a sector", which is a
different and false claim.
"""
from __future__ import annotations

import streamlit as st

#: Columns that answer "what IS this name" rather than "what is it doing".
#: They lead the table, left of every measurement, because at 25 columns
#: "wherever dict order left it" means "behind a horizontal scroll".
IDENTITY_LEAD = ("cap_bucket", "sector")


@st.cache_data(ttl=3600, show_spinner=False)
def _month_map(period: str) -> dict:
    """The whole month's `{SYMBOL: sector}`, from the DB cache (B-64).

    Keyed on the PERIOD, not on the symbol list, so every table on the desk
    shares one entry: the map is ~750 rows, small enough to hold whole, and a
    per-table key would make eight tables pay eight reads for the same rows.
    """
    try:
        import sectors as _sx
        return _sx.lookup(period=period)
    except Exception:
        return {}


def symbol_sectors(symbols) -> dict:
    """`{SYMBOL: sector}` for these names. Free after the month's first call.

    Returns `{}` when the cache is unreachable — which `attach` reads as "add no
    column", never as "these names have no sector".
    """
    try:
        import portfolio_db as _pdb
        period = _pdb.current_period()
    except Exception:
        return {}
    have = _month_map(period)
    if not have:
        return {}
    out = {}
    for x in symbols:
        s_ = str(x).strip().upper()
        if s_ in have and have[s_]:
            out[s_] = have[s_]
    return out


def attach(df, symbol_col: str):
    """Return a copy of `df` with Sector beside the symbol.

    One seam, applied at every screener table on the desk, for the reason
    `columns.py` exists at all: before this, "which sector is this hit in" was
    answerable on the rotation grid and nowhere else, so a shortlist of eight
    names could be seven banks and no table would say so. Sector is the cheapest
    context a hit list can carry — an identity attribute, not a measurement, and
    no network call once the month's map is cached.

    Safe to call on a frame that has no such column, is empty, or is None; each
    returns the input untouched, so a call site never has to guard.
    """
    if df is None or getattr(df, "empty", True) or symbol_col not in df.columns:
        return df
    syms = [str(x).strip().upper() for x in df[symbol_col]]
    smap = symbol_sectors(syms)
    out = df.copy()
    if smap:
        out["sector"] = [smap.get(s, "") for s in syms]
    # The reorder runs even when nothing was added: `_hub_enrich` relies on it to
    # place Cap, and must not lose that placement when the sector cache is down.
    lead = [c for c in (symbol_col,) + IDENTITY_LEAD if c in out.columns]
    return out[lead + [c for c in out.columns if c not in lead]]
