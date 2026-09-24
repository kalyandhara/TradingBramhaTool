#!/usr/bin/env python3
"""SVP Structure — extracted from the monolith (B-87r, third page).

Moved VERBATIM: the body below is the `if current_page == "SVP Structure":`
block as it stood, dedented one level and wrapped in `render()`. Nothing was
renamed, reordered or improved in the move, for the reason the first extraction
recorded — a move and an edit in one commit is a move you cannot verify.

Three helpers from `dashboard_app` are lazy-imported inside `render()`:
`_with_chart_family`, `_chart_family_colcfg`, `_cols_mod`. All three are pure
functions that build URL columns and Streamlit column configs; they carry no
page state. A future extraction can lift them to a shared module (they have 16
call sites across the monolith), but that is a refactor, not part of this move.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

import report_style as rs


def render() -> None:
    import dashboard_app as _app
    _with_chart_family = _app._with_chart_family
    _chart_family_colcfg = _app._chart_family_colcfg

    import columns as _cols_registry
    def _cols_mod():
        return _cols_registry

    import sector_column as _sc

    st.subheader("SVP Structure")
    st.caption(
        "Volume-profile **structure** across the engine's retained sessions — where "
        "price sits against the composite value area and POC, what shapes the "
        "sessions printed, whether a trap run is in progress. Read from the SAME "
        "`session_volume_profile.js` the chart draws, via a headless Node pass, so "
        "the screen and the chart can never disagree."
    )
    st.markdown(
        rs.callout(
            "A bystander, deliberately.",
            "This page feeds NOTHING. It is not a registered scanner, it is not in "
            "the confluence pipeline, and it contributes no ranking weight. The SVP "
            "confluence SCORE was measured 2026-08-29 as a clean negative — "
            "corr(score, 20d fwd) = −0.041, deciles non-monotonic, BUY-high "
            "confidence performing WORSE than BUY-low, 5 of 7 factor families "
            "sign-inverted — so the score and its BUY/SELL direction are not shown "
            "here at all. What is shown is structure, which the chart card's own "
            "caveat says to read while ignoring the direction. If it ever earns a "
            "place in the pipeline it goes at the END of it, on measured accuracy, "
            "and that decision has not been taken.",
            tone="warn"),
        unsafe_allow_html=True)

    _svp_csv = Path(__file__).resolve().parent.parent / "cache" / "svp_screen.csv"
    if not _svp_csv.exists():
        st.info("No screen file yet. Build one with:")
        st.code("py -3 tools/svp_universe_export.py --index nifty500\n"
                "node tools/svp_screen_runner.js --dir tools/cache/svp_bars "
                "--out tools/cache/svp_screen.csv",
                language="bash")
    else:
        _svp = pd.read_csv(_svp_csv)
        _age = datetime.now() - datetime.fromtimestamp(_svp_csv.stat().st_mtime)
        _hrs = _age.total_seconds() / 3600
        st.caption(
            f"{len(_svp)} symbols · file written {_hrs:.1f}h ago · "
            f"as-of dates in the table are the LAST BAR per symbol, which is what "
            f"the structure describes — a stale bar makes a stale row, so both are "
            f"shown rather than one date for the page."
        )

        # Defaults are BUY + D, per the desk's stated use: this page is being read
        # as a long-idea lens. They are DEFAULTS and not restrictions — SELL and
        # HOLD stay computed and one click away, because a screen that can only
        # show one side stops being able to tell you the side is empty.
        _shapes_avail = sorted(_svp["last_shape"].dropna().unique())
        _c1, _c2, _c3 = st.columns(3)
        with _c1:
            _dirs = st.multiselect("Card read (confluence)", ["BUY", "SELL", "NEUTRAL"],
                                   default=["BUY"], key="svp_dir",
                                   help="The chart card's own confluence read — the "
                                        "same engine, same factors, same wording. "
                                        "Its DIRECTION measured negative on "
                                        "2026-08-29; the per-factor detail is the "
                                        "part that stands on its own.")
        with _c2:
            _shape = st.multiselect(
                "Last session shape", _shapes_avail,
                default=[x for x in ("D",) if x in _shapes_avail], key="svp_shape",
                help="D = directional. The BUY rule accepts P or D, so this "
                     "default hides P-shape BUYs — clear it to see them.")
        with _c3:
            _near = st.slider("Max |distance to composite POC| %", 0.0, 25.0, 25.0,
                              step=0.5, key="svp_poc",
                              help="POC is where most volume transacted — the "
                                   "structural magnet. This filters on PROXIMITY "
                                   "only; it implies no direction.")
        _va = st.multiselect("Value-area state",
                             sorted(_svp["va_state"].dropna().unique()),
                             default=[], key="svp_va")

        _f = _svp.copy()
        if _va:
            _f = _f[_f["va_state"].isin(_va)]
        if _shape:
            _f = _f[_f["last_shape"].isin(_shape)]
        _f = _f[_f["poc_dist_pct"].abs().fillna(999) <= _near]

        _c4, _c5 = st.columns(2)
        with _c4:
            _minagree = st.slider("Min agreement %", 0, 100, 0, step=5,
                                  key="svp_agree",
                                  help="How one-sided the factors are. This FILTERS, "
                                       "it does not rank — agreement is a facet of a "
                                       "composite whose direction measured negative, "
                                       "so sorting the page by it would rank on the "
                                       "discredited engine.")
        with _c5:
            _minfac = st.slider("Min factors", 0, 7, 0, step=1, key="svp_nfac",
                                help="How many named factors fired. More factors is "
                                     "more to READ, not more edge.")
        if _dirs:
            _f = _f[_f["sig_dir"].isin(_dirs)]
        _f = _f[pd.to_numeric(_f["agreement"], errors="coerce").fillna(0) >= _minagree]
        _f = _f[pd.to_numeric(_f["n_factors"], errors="coerce").fillna(0) >= _minfac]

        st.markdown(f"**{len(_f)} of {len(_svp)}** symbols match.")
        _show = _f[["symbol", "sig_dir", "sig_kind", "sig_conf", "agreement",
                    "bull_w", "bear_w", "n_factors", "invalidation", "sig_target",
                    "close", "sess_poc", "sess_val", "sess_vah",
                    "va_state", "poc_dist_pct",
                    "support_hvn", "resistance_hvn", "fast_below", "fast_above",
                    "last_shape", "shape_seq", "accum_dist",
                    "struct_read", "migration", "factors", "asof"]].copy()
        # Same action-icon family every other table on this desk carries, so a row
        # here reaches the chart, the analyzer and the watchlist without retyping
        # a symbol into another page.
        _show = _sc.attach(_show, "symbol")
        _show = _with_chart_family(_show, "symbol")
        st.dataframe(
            _show,
            use_container_width=True, hide_index=True,
            column_config={
                **_chart_family_colcfg(),
                # This table builds its config by hand, so the shared `sector`
                # definition is merged in rather than re-typed — one id, one
                # label, one tooltip (B-63a).
                **_cols_mod().configure("sector"),
                "sig_dir": st.column_config.TextColumn(
                    "card", help="The chart card's confluence direction. Carried as "
                                 "DATA to be tested, never as a ranking key — it "
                                 "measured negative on 2026-08-29."),
                "agreement": st.column_config.NumberColumn(
                    "agree %", format="%d%%",
                    help="How one-sided the factors are. 100% means nothing "
                         "disagreed — which is consistency, not correctness."),
                "invalidation": st.column_config.NumberColumn(
                    "breaks if", format="%.2f",
                    help="The card's own invalidation level: the price at which "
                         "this read stops holding. Populated on 286 of 500 rows."),
                "sig_target": st.column_config.NumberColumn(
                    "target", format="%.2f",
                    help="The card's target where it has one — 178 of 500 rows. "
                         "Blank means the structure offers none, not that the "
                         "number is missing."),
                "factors": st.column_config.TextColumn(
                    "factors (plain English)", width="large",
                    help="Every named factor, its weight, its direction and the "
                         "card's own wording. This is the part that reads the same "
                         "on the screen as on the chart."),
                "struct_read": st.column_config.TextColumn(
                    "struct", help="The SECOND construction (svp_structure_signal.js) "
                                   "— POC migration + HVN/LVN roles. MEASURED 2026-09-17 "
                                   "(B-56) and INVERTED: SELL days beat BUY days by "
                                   "1.77pp at 20 sessions, 8 of 8 symbols. Shown as "
                                   "structure, never as a direction to trade."),
                "migration_frac": st.column_config.NumberColumn(
                    "mig", format="%.2f",
                    help="Fraction of session-to-session POC steps agreeing in "
                         "sign. >= 0.60 is required to call a trend."),
                "support_hvn": st.column_config.NumberColumn(
                    "sup HVN", format="%.2f",
                    help="Nearest HIGH-volume node below — accepted price with "
                         "inventory to defend it. Stops belong behind this."),
                "resistance_hvn": st.column_config.NumberColumn(
                    "res HVN", format="%.2f",
                    help="Nearest high-volume node above — supply overhead, where "
                         "price stalls."),
                "fast_below": st.column_config.NumberColumn(
                    "fast ▼", format="%.2f",
                    help="Nearest LOW-volume node below. NOT support — thin trade, "
                         "price traverses it quickly. A stop here sits in the one "
                         "place the market moves through fastest."),
                "fast_above": st.column_config.NumberColumn(
                    "fast ▲", format="%.2f",
                    help="Nearest low-volume node above — a fast zone, so a target "
                         "beyond it is reachable quickly once entered."),
                "why": st.column_config.TextColumn(
                    "rules", width="medium",
                    help="Which named rules fired (or, for HOLD, which failed). "
                         "No weights — a disagreement is about a stated rule."),
                "poc_dist_pct": st.column_config.NumberColumn(
                    "vs POC %", format="%.2f%%",
                    help="Close against the composite POC. Sign is position, "
                         "not a verdict."),
                "va_pos": st.column_config.NumberColumn(
                    "VA pos", format="%.2f",
                    help="0 = value-area low, 1 = value-area high. Outside 0–1 "
                         "means price left the range."),
                "shape_seq": st.column_config.TextColumn(
                    "shapes", help="Oldest→newest. P = buying/short-covering, "
                                   "B = selling/liquidation, D = directional, "
                                   "I = balance."),
            })
        st.caption(
            "**A blank `res HVN` on a BUY row is meaningful, not missing.** "
            "Measured on the nifty500 run: `support_hvn` is populated on 37 of 37 "
            "BUY rows and `resistance_hvn` on 97 of 97 SELL rows, because each "
            "rule requires that node to exist. A BUY with no node above means "
            "price has run clear of every accepted zone — no overhead supply, "
            "which is the bullish reading — but it also means **there is no "
            "structural target**: the construction gives an entry and a stop "
            "(behind `sup HVN`) and nothing to aim at. Use `fast ▲` as the next "
            "reference, remembering it is a fast zone rather than a barrier."
        )
        st.caption(
            "**The `read` column is a SECOND, separate construction** "
            "(`svp_structure_signal.js`) — POC migration, HVN/LVN roles and the "
            "shape series, as named boolean rules with no weights, so a "
            "disagreement is about a stated rule rather than a number nobody can "
            "decompose. It does NOT use the confluence score.\n\n"
            "**MEASURED 2026-09-17 (B-56), and it came out INVERTED.** Over 8 "
            "liquid daily names and ~4,600 bars each, SELL days were followed by "
            "**+2.75%** at 20 sessions against BUY days' **+0.99%** — a spread of "
            "**−1.77%**, p_rot 0.041, and SELL beat BUY in **8 of 8** symbols. "
            "The read is backwards from its own hypothesis.\n\n"
            "**The mirror was NOT shipped, on purpose.** The pre-registration "
            "fixed that consequence before the run: a significant inversion on a "
            "skeptical prior is a reason to re-read the construction, not to flip "
            "the labels — and the window is a rising market, so \"SELL is "
            "followed by a bounce\" is what a mean-reversion artifact looks like. "
            "Flipping it would be a new hypothesis owing its own test. **This "
            "stays a bystander: no vote, no score, no confluence weight.**"
        )
        st.caption(
            "`sweep` and `exh` are the only two of seven factor families that "
            "measured the RIGHT way (+0.39 and +0.12). They are shown as flags and "
            "nothing sorts on them: +0.12 is near zero, and picking the winners out "
            "of an in-sample attribution is the overfit the SVP design "
            "pre-registered against. They are here for a future pre-registered "
            "test, not as a signal."
        )
