#!/usr/bin/env python3
"""columns.py — ONE definition per table column, for every dataframe on the desk.

B-63a. Counted before it was written: `st.dataframe` is called **43 times**
across `tools/` (42 in `dashboard_app.py`), `column_config` is built inline
**122 times**, `help=` is passed **121 times**, and **not one of those
definitions is shared**. So the same quantity is labelled, formatted and
explained differently depending on which page you opened, and a column improved
in one table reaches no other.

Two live examples of the drift this exists to end, both in `dashboard_app.py`
before the migration:

  * "Chg%" was defined at one line as `chg_pct` and forty lines later as
    `day_pct`, in the same function;
  * "Turnover Rs Cr" was defined twice inside that same function, and again in
    the volume-shockers table above it.

── What this module does, and does NOT do ─────────────────────────────────────
It **emits config**. It does not render, does not paginate, does not touch a
dataframe's values. `_paginated_df` stays the single render path. That
separation is why adopting this is safe one call site at a time: a table that
has not migrated keeps working exactly as it did.

── The rule that makes it worth having ────────────────────────────────────────
**One id, one label, one tooltip, one format.** A caller may override `label`
and `width` — a narrow column in a crowded table is a layout decision — but
**never** the format or the help text, because those two ARE the definition of
the number. `configure()` raises on any other override rather than accepting it
quietly; a column that needs a different format needs a different id.

── Why `help` lives here and not at the call site ─────────────────────────────
The reference table this came from (ScreeningMantis, 28 columns) is legible only
because every header carries an `i` tooltip. The tooltip is not decoration; it is
what makes the width affordable. Putting it in the definition means a column
cannot be added to a second table without its explanation following it.

── Units are part of the id, not a detail ─────────────────────────────────────
`turnover_cr` is crore. Raw-rupee turnover is deliberately NOT an alias of it:
the desk has both, they differ by 1e7, and aliasing them would silently mislabel
one by seven orders of magnitude. Two units, two ids, or neither.

CLI:
    py -3 tools/columns.py           # the registry, as a table
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, replace
from typing import Any, Iterable, Optional

#: Overrides a caller is allowed to pass. Format and help are the definition.
MUTABLE = ("label", "width")


@dataclass(frozen=True)
class ColSpec:
    """One column, defined once."""
    label: str
    help: Optional[str] = None
    kind: str = "number"                 # number | text | link | date | progress
    fmt: Optional[str] = None            # NumberColumn format string
    width: Optional[str] = None          # small | medium | large
    display_text: Optional[str] = None   # LinkColumn only


#: The registry. Ids are dataframe column names wherever the desk already has a
#: settled name for the quantity; ALIASES maps the other spellings onto them.
COLUMNS: dict[str, ColSpec] = {
    # ── identity ──────────────────────────────────────────────────────────────
    "symbol": ColSpec("Symbol", "NSE symbol.", "text", width="small"),
    "sector": ColSpec(
        "Sector",
        "NSE macro sector — the desk's canonical vocabulary (tools/sectors.py). "
        "Yahoo's sector/industry is stored as description but is not the join key.",
        "text", width="medium"),
    "cap_bucket": ColSpec("Cap", "Market-cap bucket.", "text", width="small"),

    # ── price ─────────────────────────────────────────────────────────────────
    "close": ColSpec("LTP", "Last traded price (the session's close).",
                     "number", "%.2f"),
    "chg": ColSpec("Chg", "Change vs the previous close, in rupees.",
                   "number", "%.2f"),
    "chg_pct": ColSpec("Chg%", "Change vs the previous close, per cent.",
                       "number", "%.2f%%"),
    "gap_pct": ColSpec("Gap%", "Today's OPEN vs the previous close, per cent — "
                               "the overnight move, before any intraday trading.",
                       "number", "%.2f%%"),
    "from_high_pct": ColSpec("From high %", "Distance below the period high.",
                             "number", "%.2f%%"),
    "from_low_pct": ColSpec("From low %", "Distance above the period low.",
                            "number", "%.2f%%"),
    "from_52w_high_pct": ColSpec(
        "52W high %", "Distance below the 52-week high (252 sessions).",
        "number", "%.2f%%"),

    # ── volume ────────────────────────────────────────────────────────────────
    # Four different RVOL bases were live at once before this module: a 20-day
    # mean, a 50-day mean, a 5d/20d ratio and a 5-SESSION MEDIAN. They are not
    # the same number and a reader comparing "2.4x" across two pages was
    # comparing nothing. The 20-day mean is the default; the median keeps its
    # own id because nse_oi_momentum chose a median deliberately, and folding
    # the two together would be a behaviour change dressed as a refactor.
    "rvol": ColSpec(
        "Vol spike",
        "Today's volume / its 20-day MEAN volume. 2.0x = twice normal.",
        "number", "%.1fx", width="small"),
    "rvol_median5": ColSpec(
        "Vol spike (5d med)",
        "Today's volume / its 5-session MEDIAN volume — a different base from "
        "the 20-day mean used elsewhere; do not compare the two numbers.",
        "number", "%.1fx", width="small"),
    "volume": ColSpec("Volume", "Shares traded in the session.", "number", "%d"),
    "sma_vol10": ColSpec("SMA vol(10)", "10-session mean volume.", "number", "%d"),
    # "localized" rather than a printf format: at crore scale the thousands
    # separator is worth more than a decimal place, and printf has no comma flag
    # (the Styler that used to supply "{:,.0f}" is gone — one formatter, not two).
    "turnover_cr": ColSpec(
        "Turnover ₹Cr",
        "Traded value in crore. Where this is derived from daily bars it is "
        "close x volume — a proxy for exchange turnover, not the bhavcopy figure.",
        "number", "localized"),

    # ── trend / structure ─────────────────────────────────────────────────────
    "rsi": ColSpec("RSI", "Wilder's RSI(14) on the daily close.",
                   "number", "%d", width="small"),
    "pct_from_20ema": ColSpec(
        "% from 20EMA", "Signed distance from the 20-period EMA.",
        "number", "%.2f%%"),
    "ema_cross_age": ColSpec(
        "EMA cross age",
        "Trading days since the 10-EMA last crossed the 20-EMA. Blank = no "
        "cross within the loaded history, not 'no cross ever'.",
        "number", "%d days", width="small"),
    "stage2_score": ColSpec(
        "Stage 2",
        "How many of the 7 Stage-2 conditions are met — a count, not a gate, so "
        "a name failing one leg stays visible.",
        "text", width="small"),
    "direction": ColSpec("Dir", "Direction of the move.", "text", width="small"),
    "cause": ColSpec("Cause", "Attributed reason for the move, where one is known.",
                     "text", width="medium"),

    # ── scoring ───────────────────────────────────────────────────────────────
    "score": ColSpec("Score", "Scanner score for this hit.", "number", "%.1f"),
    "rs_rank": ColSpec(
        "RS rank",
        "Relative-strength percentile 0-100 WITHIN THIS SCAN's matched set — "
        "not a universe-wide rank, so two scans' ranks are not comparable.",
        "number", "%d", width="small"),
    "confluence": ColSpec("Confluence", "Independent scanners that fired on this name.",
                          "number", "%d", width="small"),

    # ── sector grids ──────────────────────────────────────────────────────────
    "share_pct": ColSpec(
        "Share %", "This sector's slice of the universe's turnover. Sums to 100%.",
        "number", "%.2f%%"),
    "d_share_d": ColSpec(
        "Δ share 1D (pt)",
        "Change in that share vs yesterday, in percentage POINTS. "
        "3.70% -> 6.65% is +2.95 pt, not +80%.",
        "number", "%+.2f"),
    "d_share_w": ColSpec(
        "Δ share 1W (pt)", "Same, versus five trading days ago.",
        "number", "%+.2f"),
    "members": ColSpec("Members", "Constituents with usable history.",
                       "number", "%d", width="small"),

    # ── the chart-icon link family ────────────────────────────────────────────
    # display_text keeps a WORD beside the emoji: an emoji-only display_text
    # trips Streamlit's spurious edit-pencil rendering bug.
    "chart": ColSpec("Chart", "Chart Tool (in-app, :5001)", "link",
                     width="small", display_text="👁 Chart"),
    "analyze": ColSpec("Analyze", "Stock Analyzer (in-app)", "link",
                       width="small", display_text="↗ Analyze"),
    "tview": ColSpec("TView", "Open on TradingView", "link",
                     width="small", display_text="📈 TV"),
    "screener": ColSpec("Screener", "Open on Screener.in", "link",
                        width="small", display_text="📊 Screener"),
    "gfin": ColSpec("GFin", "Open on Google Finance", "link",
                    width="small", display_text="G Finance"),
}

#: Other spellings of the SAME quantity, mapped onto their id. Every entry here
#: is a drift that was live in the codebase. Units must match exactly — see the
#: module docstring on why raw-rupee turnover is not aliased to `turnover_cr`.
ALIASES: dict[str, str] = {
    "day_pct": "chg_pct",       # was a second "Chg%" in the same function
    "Chg%": "chg_pct",
    "multiple": "rvol",         # "x SMA10" / "x avg vol" — same ratio, two labels
    "vol_x": "rvol",
    "Symbol": "symbol",
    "Sector": "sector",
    "LTP": "close",
}

#: Ids in the chart-icon family, in display order.
CHART_FAMILY = ("chart", "analyze", "tview", "screener", "gfin")


def resolve(name: str) -> Optional[str]:
    """Map a dataframe column name onto a registry id, or None if unknown."""
    if name in COLUMNS:
        return name
    return ALIASES.get(name)


def spec(name: str) -> ColSpec:
    """The definition for a column. Raises on an unknown id — silence here is
    how a table ends up with an unexplained header."""
    key = resolve(name)
    if key is None:
        raise KeyError(f"no column spec for {name!r} — add it to columns.COLUMNS "
                       f"rather than defining it inline")
    return COLUMNS[key]


def _to_streamlit(s: ColSpec):
    import streamlit as st
    common: dict[str, Any] = {"help": s.help}
    if s.width:
        common["width"] = s.width
    if s.kind == "number":
        return st.column_config.NumberColumn(s.label, format=s.fmt, **common)
    if s.kind == "link":
        return st.column_config.LinkColumn(
            s.label, display_text=s.display_text, **common)
    if s.kind == "date":
        return st.column_config.DateColumn(s.label, **common)
    return st.column_config.TextColumn(s.label, **common)


def configure(*names: str, overrides: dict[str, dict] | None = None) -> dict:
    """`column_config` for the named columns, keyed by the name as passed.

    Keyed by what the caller passed, not by the resolved id, so a frame whose
    column is still called `day_pct` gets the `chg_pct` definition under its own
    name and needs no renaming to adopt this.

    `overrides={"close": {"width": "small"}}` may set only `label` and `width`.
    Anything else raises: the format and the tooltip ARE the definition, and a
    column needing a different one needs a different id.
    """
    overrides = overrides or {}
    bad = {k: sorted(set(v) - set(MUTABLE)) for k, v in overrides.items()
           if set(v) - set(MUTABLE)}
    if bad:
        raise ValueError(
            f"only {list(MUTABLE)} may be overridden; refused {bad}. "
            f"A column needing a different format or tooltip needs its own id "
            f"in columns.COLUMNS.")
    out = {}
    for n in names:
        s = spec(n)
        if n in overrides:
            s = replace(s, **overrides[n])
        out[n] = _to_streamlit(s)
    return out


def configure_df(df, *, extra: Iterable[str] = (),
                 overrides: dict[str, dict] | None = None) -> dict:
    """`column_config` for every column of `df` the registry knows about.

    Unknown columns are left alone — Streamlit renders them with its defaults,
    which is the right behaviour for a half-migrated table: adopting this must
    never blank out a column nobody has defined yet.
    """
    names = [c for c in list(df.columns) + list(extra) if resolve(str(c))]
    return configure(*names, overrides=overrides)


def main() -> int:
    # The Windows console defaults to cp1252 and this registry contains a Delta
    # and several emoji, so an un-reconfigured stdout kills the CLI on the very
    # machine the desk runs on. Streamlit itself is UTF-8 and unaffected.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # pragma: no cover
        pass
    rows = []
    for cid, s in sorted(COLUMNS.items()):
        rows.append((cid, s.kind, s.label, s.fmt or "", s.width or "",
                     (s.help or "")[:60]))
    w = [max(len(r[i]) for r in rows + [("id", "kind", "label", "fmt", "width", "help")])
         for i in range(6)]
    hdr = ("id", "kind", "label", "fmt", "width", "help (truncated)")
    print("  ".join(h.ljust(w[i]) for i, h in enumerate(hdr)))
    print("  ".join("-" * w[i] for i in range(6)))
    for r in rows:
        print("  ".join(str(r[i]).ljust(w[i]) for i in range(6)))
    print(f"\n{len(COLUMNS)} columns defined, {len(ALIASES)} aliases. "
          f"Only {list(MUTABLE)} may be overridden per call site.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
