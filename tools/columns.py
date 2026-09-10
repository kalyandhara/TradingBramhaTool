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
#: `tone` and `pinned` are NOT mutable, and that is the point: a column that
#: means "up is good" here and nothing there is the drift this module exists to
#: stop. See `configure`'s docstring.


@dataclass(frozen=True)
class ColSpec:
    """One column, defined once."""
    label: str
    help: Optional[str] = None
    kind: str = "number"                 # number | text | link | date | progress
    fmt: Optional[str] = None            # NumberColumn format string
    width: Optional[str] = None          # small | medium | large
    display_text: Optional[str] = None   # LinkColumn only
    #: How this column CARRIES MEANING IN COLOUR. Part of the definition for the
    #: same reason the tooltip is: "+2.4%" tinted green on one page and plain on
    #: another is the same drift `label`/`help`/`fmt` were centralised to end.
    #:   None      no tint (identity, dates, text)
    #:   "signed"  positive green / negative red, tint PAIR not coloured text
    #:   "heat"    magnitude above a neutral floor warms toward the accent
    #:   "rank"    0-100 percentile, cool at the bottom, strong at the top
    #:   "zone"    categorical band label (R1 / PP-S1 / Near Pivot)
    tone: Optional[str] = None
    #: Kept visible while the table scrolls sideways. Only identity columns
    #: should set it — pinning a number pins the wrong half of the row.
    pinned: bool = False


#: The registry. Ids are dataframe column names wherever the desk already has a
#: settled name for the quantity; ALIASES maps the other spellings onto them.
COLUMNS: dict[str, ColSpec] = {
    # ── identity ──────────────────────────────────────────────────────────────
    "symbol": ColSpec("Symbol", "NSE symbol.", "text", width="small", pinned=True),
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
                       "number", "%.2f%%", tone="signed"),
    "gap_pct": ColSpec("Gap%", "Today's OPEN vs the previous close, per cent — "
                               "the overnight move, before any intraday trading.",
                       "number", "%.2f%%", tone="signed"),
    "from_high_pct": ColSpec("From high %", "Distance below the period high.",
                             "number", "%.2f%%"),
    "from_low_pct": ColSpec("From low %", "Distance above the period low.",
                            "number", "%.2f%%"),
    "from_52w_high_pct": ColSpec(
        "52W high %", "Distance below the 52-week high (252 sessions).",
        "number", "%.2f%%", tone="signed"),

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
        "number", "%.1fx", width="small", tone="heat"),
    "rvol_median5": ColSpec(
        "Vol spike (5d med)",
        "Today's volume / its 5-session MEDIAN volume — a different base from "
        "the 20-day mean used elsewhere; do not compare the two numbers.",
        "number", "%.1fx", width="small", tone="heat"),
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
    # Signed, and the unit lives in the LABEL: "%d days" renders "1 days", and
    # the sign carries the direction, which is the whole reading.
    "ema_cross_age": ColSpec(
        "EMA cross (d)",
        "Trading days since the 10-EMA last crossed the 20-EMA, SIGNED: "
        "+12 = crossed above 12 sessions ago, -3 = crossed below 3 sessions "
        "ago. Blank = no cross within the loaded history, NOT 'no cross ever'.",
        "number", "%+d", width="small"),
    "stage2_score": ColSpec(
        "Stage 2",
        "How many of the 7 Stage-2 conditions are met — a count, not a gate, so "
        "a name failing one leg stays visible.",
        "text", width="small"),
    "direction": ColSpec("Dir", "Direction of the move.", "text", width="small"),
    "cause": ColSpec("Cause", "Attributed reason for the move, where one is known.",
                     "text", width="medium"),

    "pivot_d": ColSpec(
        "D-Pivot",
        "Which band today's close sits in against the DAILY floor pivots "
        "(computed from the prior bar): R1 / R1-PP / PP-S1 / S1, or Near ... "
        "when price is within 0.15% of a level.",
        "text", width="small"),
    "pivot_w": ColSpec(
        "W-Pivot", "The same band, against WEEKLY pivots.",
        "text", width="small"),
    "bo_gain_pct": ColSpec(
        "BO gain%",
        "Gain since the last close above its prior 20-bar high. Can be "
        "NEGATIVE — a breakout that faded is exactly what this shows.",
        "number", "%+.2f%%", tone="signed"),
    "bo_date": ColSpec(
        "BO date",
        "When that breakout happened. Read it WITH the gain: +3% from last week "
        "and +3% from four months ago are different situations.",
        "text", width="small"),
    "hist_price": ColSpec(
        "Hist. price",
        "Close on (or the last close before) the reference date you picked. "
        "Blank means the history does not reach that far back.",
        "number", "%.2f"),
    "gain_since_pct": ColSpec(
        "Gain% since",
        "Return from that reference date to today — the table re-bases on a "
        "date you choose rather than a fixed lookback.",
        "number", "%+.2f%%"),
    "rs_walk": ColSpec(
        "RS walk (T-30→T0)",
        "Universe-wide relative-strength percentile at T-30 / T-15 / T-5 / "
        "today, oldest first. A FIXED denominator (every constituent with "
        "history), unlike the scan-relative rs_rank — so the four numbers are "
        "one population over time. '?' = the name lacked history that far back, "
        "which is not the same as ranking weak.",
        "text", width="medium", tone="rank"),
    "notes": ColSpec(
        "Notes",
        "Your own note on this row. Editable in place where the table says so — "
        "click the cell, type, press Enter. Saved to `symbol_notes`, keyed by "
        "SYMBOL rather than by watchlist membership: one note per name, shared "
        "by every table that shows one, and it survives the name leaving your "
        "watchlist.",
        "text", width="large"),
    "minervini": ColSpec(
        "Minervini",
        "Minervini trend-template conditions met, out of 8 — a COUNT, not a "
        "gate, so a name failing one leg stays visible.",
        "text", width="small"),
    "technofunda": ColSpec(
        "TechnoFunda", "TechnoFunda conditions met, out of 6.",
        "text", width="small"),

    # ── scoring ───────────────────────────────────────────────────────────────
    "score": ColSpec("Score", "Scanner score for this hit.", "number", "%.1f"),
    "rs_rank": ColSpec(
        "RS rank",
        "Relative-strength percentile 0-100 WITHIN THIS SCAN's matched set — "
        "not a universe-wide rank, so two scans' ranks are not comparable.",
        "number", "%d", width="small", tone="rank"),
    "confluence": ColSpec("Confluence", "Independent scanners that fired on this name.",
                          "number", "%d", width="small"),

    # ── futures / OI (nse_oi_momentum) ────────────────────────────────────────
    # These are FUTURES quantities and stay separate from their cash-market
    # namesakes on purpose. `rvol_fut` in particular is futures volume over a
    # 5-session MEDIAN — a third base again, and mapping it to either equity
    # `rvol` id would be a silent redefinition of the number.
    "price_pct_fut": ColSpec(
        "Price %", "Futures price change for the session, per cent.",
        "number", "%.2f%%"),
    "oi_pct": ColSpec(
        "OI %", "Change in open interest for the session, per cent.",
        "number", "%.2f%%"),
    "rvol_fut": ColSpec(
        "RVol",
        "Today's FUTURES volume / the symbol's own median over the prior 5 "
        "settled sessions. 1.00x means it traded exactly as much as it usually "
        "does. Blank where the baseline is unavailable. Not comparable with the "
        "equity Vol spike, which uses a 20-day mean of cash volume.",
        "number", "%.2fx"),

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
    "Notes": "notes",
    # Spellings found in the 2026-09-10 sweep: same quantity, different label,
    # each defined inline at its own call site.
    "% Chg": "chg_pct",
    "Price": "close",
    "LTP ₹": "close",
    "Gap %": "gap_pct",
    "Price %": "price_pct_fut",
    "OI %": "oi_pct",
    "RVol": "rvol_fut",
}

#: Deliberately NOT aliased, with the reason, so the next sweep does not
#: "finish the job" by adding them:
#:   "Turnover ₹"      raw RUPEES, while `turnover_cr` is crore — 1e7 apart.
#:   "Pub Price ₹", "Mkt Cap ₹", "Basis %", "OI", "Breadth %", "Median %",
#:   "Avg Mom %", "# Stocks", "Move %"
#:                     each defined once and used once. Promoting a singleton
#:                     creates a shared id nothing else asks for, which is the
#:                     opposite of the point.
NOT_ALIASED = ("Turnover ₹", "Pub Price ₹", "Mkt Cap ₹", "Basis %", "Breadth %",
               "Median %", "Avg Mom %", "# Stocks", "Move %")

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
    if s.pinned:
        # Keeps identity visible while the row scrolls sideways — their table
        # pins the left block and it is why 28 columns stay navigable.
        common["pinned"] = True
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


# ── tint pairs, and why they live here ───────────────────────────────────────
# Captured from screeningmantis.com on 2026-09-10: the thing that makes a 28-column
# table scannable is not the font, it is that a positive number sits on a tinted
# CELL rather than being coloured text. Their pair is #11795d on #dff1ea; ours is
# the same idea in this desk's warm palette, so the tables stay in step with the
# PNG exports and cards that already use report_style.TOKENS.
#
# It belongs in the registry for the same reason `help` does: a quantity that
# reads "up is good" on one page and neutral on another is exactly the drift this
# module was built to end. `tone` is therefore NOT in MUTABLE.
#
# Streamlit's grid renders to CANVAS, so CSS cannot reach cell text. Background
# tint via a pandas Styler is the only sanctioned way in, which is why this emits
# a Styler rather than a stylesheet.
TINTS = {
    "pos":     ("#166534", "#e8f5e9"),   # text, tint
    "neg":     ("#b91c1c", "#fef2f2"),
    "heat_hi": ("#9a3412", "#ffedd5"),
    "heat_mid": ("#a16207", "#fff8e1"),
    "rank_hi": ("#1d4ed8", "#eef4ff"),
    "rank_lo": ("#6b7280", "#f3f4f6"),
}

#: rvol below this is ordinary volume and gets no tint — a heat scale with no
#: floor paints every row and communicates nothing.
RVOL_FLOOR = 1.5
#: rs_rank at or above this is "leading"; below RANK_LO is "lagging". Between
#: them the cell stays clean, because a percentile in the middle is not news.
RANK_HI, RANK_LO = 80, 20


def _tint_signed(v):
    if v is None or (isinstance(v, float) and v != v):
        return ""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return ""
    if x > 0:
        fg, bg = TINTS["pos"]
    elif x < 0:
        fg, bg = TINTS["neg"]
    else:
        return ""
    return f"color:{fg};background-color:{bg}"


def _tint_heat(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return ""
    if x != x or x < RVOL_FLOOR:
        return ""
    fg, bg = TINTS["heat_hi"] if x >= RVOL_FLOOR * 2 else TINTS["heat_mid"]
    return f"color:{fg};background-color:{bg}"


def _tint_rank(v):
    """Ranks arrive as numbers OR as a walk string ('92 -> 94 -> 35 -> 36').

    The walk is tinted on its LAST rung, because that is the current standing and
    the arrow before it is the history. Tinting on the first would colour a row
    by where it used to be.
    """
    x = None
    if isinstance(v, str):
        parts = [p.strip().rstrip("*") for p in v.replace("→", "->").split("->")]
        for p in reversed(parts):
            try:
                x = float(p)
                break
            except ValueError:
                continue
    else:
        try:
            x = float(v)
        except (TypeError, ValueError):
            return ""
    if x is None or x != x:
        return ""
    if x >= RANK_HI:
        fg, bg = TINTS["rank_hi"]
    elif x <= RANK_LO:
        fg, bg = TINTS["rank_lo"]
    else:
        return ""
    return f"color:{fg};background-color:{bg}"


_TINTERS = {"signed": _tint_signed, "heat": _tint_heat, "rank": _tint_rank}


def tint(df):
    """A pandas Styler tinting every column the registry gives a `tone`.

    Returns the frame unchanged (not a Styler) when nothing in it is toned, so a
    caller can hand the result straight to `st.dataframe` either way and an
    untoned table pays nothing.
    """
    cols = [c for c in df.columns
            if (k := resolve(str(c))) and COLUMNS[k].tone in _TINTERS]
    if not cols:
        return df
    st_ = df.style
    for c in cols:
        st_ = st_.map(_TINTERS[COLUMNS[resolve(str(c))].tone], subset=[c])
    return st_


#: Row height, in px. Theirs is 36 at 11px type; Streamlit will not let us set
#: the cell font, so 32 is the density that reads as tight WITHOUT shrinking the
#: text into the row's dead space. Chosen by looking at both, not by copying one.
ROW_HEIGHT = 32


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
