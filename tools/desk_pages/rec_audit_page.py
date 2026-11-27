"""Recommendation Audit page (A2, A3) — how every past recommendation did.

A3 adds a source picker (Opportunity shortlist / Hidden Treasures / raw scanner
hits, audited separately and never mixed), an equal-weight NIFTY 500 baseline,
and the "Proposed changes" log the owner accepts or rejects.

Reads only the stored audit (`rec_audit_job.load_latest`); nothing fetches on
open. "↻ Re-run audit" is the one fetch, and the scheduled `rec_audit` job does
the same after each close. Numbers are measured from the next session's open
and compared with NIFTY 500 / Smallcap 250 / the sector index over the same
dates — see trading-wiki `analyses/Recommendation-Audit-Roadmap.md`.

The post-mortem queue is where the owner reviews failures: override the auto
tag, write a note. Reviews live in their own table, so a re-run keeps them.
"""
from __future__ import annotations

from urllib.parse import quote

import pandas as pd
import streamlit as st

import rec_audit as ra
import rec_audit_job as job
import rec_audit_replay as rp

HORIZONS = ra.HORIZONS
#: Slice label → column (derived columns are added by `with_slices`).
SLICES: dict[str, str] = {
    "Scanner family": "family_names", "Sector": "sector", "Rank band": "rank_band",
    "Risk flags at pick": "flagged", "Plan source": "plan_source",
    "Model version": "model_version", "Market regime": "market_regime",
    "Days on list": "list_band",
}
#: A3: what each source can be sliced by.
SLICES_BY_SOURCE: dict[str, dict[str, str]] = {
    "opportunity": SLICES,
    "hidden_treasures": {"Rank band": "rank_band", "Pledge flag": "pledge_flag",
                         "Universe": "universe_kind", "Model version": "model_version"},
    "scanner": {"Scanner": "scanner", "Category": "category"},
}
REVIEW_TAGS: tuple[str, ...] = (*ra.TAG_ORDER, ra.UNEXPLAINED)
CARDS_PER_PAGE = 12


# ── Pure helpers (tested) ────────────────────────────────────────────────────
def with_slices(eps: pd.DataFrame) -> pd.DataFrame:
    """Add the derived slice columns: rank band, flagged/clean, days-on-list band."""
    if eps.empty:
        return eps
    d = eps.copy()
    if "rank" in d:                       # raw scanner hits carry no rank (A3)
        d["rank_band"] = pd.cut(pd.to_numeric(d["rank"], errors="coerce"), [0, 5, 20, 10**6],
                                labels=["1-5", "6-20", "21+"]).astype(str)
    d["flagged"] = (d.get("risk_flags", pd.Series("", index=d.index)).fillna("")
                    .astype(str).str.strip().ne("").map({True: "flagged", False: "clean"}))
    d["list_band"] = pd.cut(pd.to_numeric(d.get("appearances"), errors="coerce"),
                            [0, 1, 3, 10**6], labels=["once", "2-3 runs", "4+ runs"]
                            ).astype(str)
    return d


def review_queue(eps: pd.DataFrame, tag: str | None = None,
                 h: int = ra.HEADLINE_H) -> pd.DataFrame:
    """Matured failures, worst excess first; `tag` filters on the review tag
    (the owner's override where set, else the auto primary tag)."""
    if eps.empty or f"ret_{h}" not in eps:
        return eps.iloc[0:0]
    q = eps[eps["failure"].astype(bool) & eps[f"ret_{h}"].notna()]
    if tag:
        q = q[q["review_tag"] == tag]
    return q.sort_values(f"excess_{h}", na_position="last")


def tag_counts(eps: pd.DataFrame, h: int = ra.HEADLINE_H) -> dict[str, int]:
    q = review_queue(eps, h=h)
    return q["review_tag"].fillna(ra.UNEXPLAINED).value_counts().to_dict() if not q.empty else {}


def link(page: str, symbol: str) -> str:
    import ui_tables as uit
    return f"{uit.DASHBOARD_BASE}/?nav={page}&symbol={quote(str(symbol))}"


def _pct(v, signed: bool = True) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{v:+.2f}%" if signed else f"{v:.1f}%"


# ── Page ─────────────────────────────────────────────────────────────────────
def render() -> None:
    st.subheader("Recommendation Audit")
    src = st.segmented_control("Source", list(job.SOURCES), default="opportunity",
                               format_func=lambda k: job.SOURCES[k]["label"],
                               key="ra_src") or "opportunity"
    cfg = job.SOURCES[src]
    head, horizons = cfg["headline"], cfg["horizons"]
    data = job.load_latest(source=src)
    run, eps = data["run"], data["episodes"]

    top = st.columns([5, 1])
    if run is None:
        top[0].info("No audit stored yet. Run it once (about 3 minutes — it fetches "
                    "daily bars for every past pick), or register the **Recommendation "
                    "Audit** job in Scheduler Hub to run it after each close.")
    else:
        top[0].caption(
            f"As of **{run['as_of']}** · run {run['created_at'].replace('T', ' ')} · "
            f"{len(eps)} {'hits' if src == 'scanner' else 'picks'} since "
            f"{str(eps['rec_date'].min())[:10] if not eps.empty else '—'}. Entry = next "
            f"session's open; every return is compared with benchmarks over the same dates.")
    if top[1].button("↻ Re-run audit", key="ra_rerun", use_container_width=True):
        with st.spinner("Fetching prices and re-scoring every source…"):
            try:
                reps = job.run_all()
                any_rep = next(iter(reps.values()))
                job.write_monthly_report(reps, pd.Timestamp(any_rep["episodes_df"]["as_of"]
                                                            .iloc[0]).date())
                _replay_bars.clear()        # the re-run may have stored new bars
                _all_scores.clear()         # …and the nightly re-score may have run
                st.toast("Audit refreshed.")
            except Exception as e:
                st.error(f"Audit failed: {type(e).__name__}: {e}")
                return
        st.rerun()
    if run is None or eps.empty:
        return

    eps = with_slices(eps)
    h = st.segmented_control("Horizon (sessions)", horizons, default=head,
                             key=f"ra_h_{src}") or head
    _tiles(eps, data["portfolio"], h, head)

    tabs = st.tabs(["Monthly batches", "What worked", "Post-mortems", "Pick replay",
                    "Lessons", "All picks", "Proposed changes", "Run history"])
    with tabs[0]:
        _cohorts(eps, horizons)
    with tabs[1]:
        _attribution(eps, h, src)
    with tabs[2]:
        _postmortems(eps, head)
    with tabs[3]:
        _replay_tab(eps, head, src)
    with tabs[4]:
        _lessons_tab(eps, head, src)
    with tabs[5]:
        _all_picks(eps, h)
    with tabs[6]:
        _proposals(src)
    with tabs[7]:
        _history(data["history"])


def _tiles(eps: pd.DataFrame, port: pd.DataFrame, h: int, head: int) -> None:
    s = ra.summarise(eps, h)
    c = st.columns(7)
    c[0].metric("Picks judged", s["n"], help=f"Picks at least {h} sessions old. "
                f"{s['pending']} not yet entered, {s['no_data']} with no price data, "
                f"{s['data_suspect']} set aside for a suspected split/bonus "
                f"(a ≥{ra.SPLIT_SUSPECT_PCT:.0f}% one-day move).")
    c[1].metric("Went up", _pct(s["hit_rate"], False))
    c[2].metric("Median vs NIFTY 500", _pct(s["median_excess"]),
                help=f"{_pct(s['beat_market_rate'], False)} of picks beat it")
    c[3].metric("Median vs Smallcap 250", _pct(s["median_excess_smallcap"]),
                help="Most picks are small caps — this is the like-for-like benchmark.")
    c[4].metric("Median vs equal-weight", _pct(s.get("median_excess_ew")),
                help="Against the average NIFTY 500 stock over the same dates — the "
                     "'random pick from the pool' baseline. Today's constituents, so "
                     "names dropped from the index since are missing (a mild tilt).")
    tw = s.get("t_excess_weekly")
    c[5].metric("Significance (t)", "—" if tw is None else f"{tw:.2f}",
                help=f"Picks grouped by entry week ({s['weeks']} weeks): picks entered the "
                     "same week move together, so the per-pick t overstates confidence. "
                     "Below 2 is not significant.")
    if not port.empty and h == head:
        b, m = (port["basket"].iloc[-1] - 1) * 100, (port["market"].iloc[-1] - 1) * 100
        c[6].metric("₹1 in every pick", _pct(b), delta=f"{b - m:+.2f} pts vs NIFTY 500",
                    help=f"Each pick held {head} sessions from its entry open; "
                         "a shadow ₹1 in NIFTY 500 over the same dates.")
    if tw is not None and abs(tw) < 2:
        st.caption(f"⚠️ Not statistically significant at {h} sessions (t = {tw:.2f} over "
                   f"{s['weeks']} entry weeks). Treat slices below as leads, not findings.")
    if not port.empty and h == head:
        st.line_chart(((port[["basket", "market"]] - 1) * 100)
                      .rename(columns={"basket": "₹1 per pick", "market": "NIFTY 500 shadow"}),
                      height=220, y_label="% return")


def _cohorts(eps: pd.DataFrame, horizons: tuple[int, ...]) -> None:
    st.caption("Each month's picks, judged at each horizon: median return over NIFTY 500, "
               "and the share that beat it. A blank cell is a horizon not reached yet.")
    co = ra.cohorts(eps, horizons)
    if co.empty:
        st.info("No cohorts yet.")
        return
    # Unreached horizons are None in an object column, which renders "None".
    co = co.apply(lambda s: s if s.name == "month" else pd.to_numeric(s, errors="coerce"))
    cfg = {"month": "Month", "episodes": "Picks"}
    for hh in horizons:
        cfg[f"n_{hh}"] = st.column_config.NumberColumn(f"n {hh}d")
        cfg[f"med_excess_{hh}"] = st.column_config.NumberColumn(f"Median {hh}d", format="%+.2f%%")
        cfg[f"beat_{hh}"] = st.column_config.NumberColumn(f"Beat {hh}d", format="%.0f%%")
    st.dataframe(co, column_config=cfg, hide_index=True, use_container_width=True)


def _attribution(eps: pd.DataFrame, h: int, src: str = "opportunity") -> None:
    slices = SLICES_BY_SOURCE.get(src, SLICES)
    label = st.selectbox("Slice by", list(slices), key=f"ra_slice_{src}")
    col = slices[label]
    if col not in eps:
        st.info(f"No `{col}` recorded yet — it starts with picks made after 2026-10-22.")
        return
    att = ra.attribution(eps, col, h=h)
    st.dataframe(att, hide_index=True, use_container_width=True, column_config={
        col: label, "n": "Picks",
        "median_excess": st.column_config.NumberColumn("Median vs NIFTY 500", format="%+.2f%%"),
        "mean_excess": st.column_config.NumberColumn("Mean", format="%+.2f%%"),
        "beat_market_rate": st.column_config.NumberColumn("Beat", format="%.0f%%"),
        "t": st.column_config.NumberColumn("t (per pick)", format="%.2f"),
        "sufficient": st.column_config.CheckboxColumn(f"n ≥ {ra.MIN_N}")})
    st.caption(f"t here counts every pick separately, which overstates confidence when "
               f"picks overlap in time. Rows under {ra.MIN_N} picks are too small to read. "
               f"Testing many slices finds some 'winners' by chance — no weight changes "
               f"until a slice holds up across several monthly batches.")


def _postmortems(eps: pd.DataFrame, h: int = ra.HEADLINE_H) -> None:
    counts = tag_counts(eps, h)
    if not counts:
        st.success("No failures among the judged picks.")
        return
    st.caption(f"Failures at {h} sessions: return or excess ≤ "
               f"{ra.FAIL_RET_PCT:.0f}%, or the stop hit first. The tag is the first "
               "explanation that applies; override it and add a note after you look.")
    opts = [f"All ({sum(counts.values())})"] + [f"{t} ({n})" for t, n in counts.items()]
    pick = st.pills("Cause", opts, default=opts[0], key="ra_tag") or opts[0]
    tag = None if pick.startswith("All") else pick.rsplit(" (", 1)[0]
    q = review_queue(eps, tag, h)
    pages = max(1, -(-len(q) // CARDS_PER_PAGE))
    pg = st.number_input("Page", 1, pages, 1, key=f"ra_pg_{tag}") if pages > 1 else 1
    chunk = q.iloc[(pg - 1) * CARDS_PER_PAGE: pg * CARDS_PER_PAGE]
    cols = st.columns(3)
    for i, (_, r) in enumerate(chunk.iterrows()):
        with cols[i % 3]:
            _card(r, h)


def _card(r: pd.Series, h: int = ra.HEADLINE_H) -> None:
    with st.container(border=True):
        who = f" · {r['scanner']}" if pd.notna(r.get("scanner")) and r.get("scanner") else ""
        st.markdown(f"**{r['symbol']}**{who} · picked {str(r['rec_date'])[:10]} · "
                    f"rank {int(r['rank']) if pd.notna(r.get('rank')) else '—'}")
        st.markdown(f"{h}d **{_pct(r.get(f'ret_{h}'))}** · vs NIFTY 500 "
                    f"{_pct(r.get(f'excess_{h}'))} · vs sector {_pct(r.get(f'excess_sec_{h}'))}")
        st.caption(f"Best {_pct(r.get('mfe'))} / worst {_pct(r.get('mae'))} · "
                   f"plan {r['plan_outcome'] if pd.notna(r.get('plan_outcome')) else 'none'}")
        reviewed = pd.notna(r.get("tag_override")) and r.get("tag_override")
        st.markdown(f":red-badge[{r.get('review_tag') or ra.UNEXPLAINED}]"
                    + (" :blue-badge[reviewed]" if reviewed else ""))
        other = [t for t in str(r.get("tags") or "").split(", ") if t and t != r.get("review_tag")]
        if other:
            st.caption("Also: " + ", ".join(other))
        if r.get("family_names"):
            st.caption(f"Families: {r['family_names']}")
        if pd.notna(r.get("note")) and r.get("note"):
            st.caption(f"📝 {r['note']}")
        key = r["episode_id"]
        b1, b2 = st.columns(2)
        b1.link_button("Analyzer ↗", link("analyze", r["symbol"]), use_container_width=True)
        if b2.button("Replay", key=f"ra_rp_btn_{key}", use_container_width=True):
            _replay_dialog(r, h)
        with st.expander("Review"):
            auto = r.get("primary_tag") or ra.UNEXPLAINED
            choices = [f"(auto) {auto}", *REVIEW_TAGS]
            cur = r.get("tag_override")
            idx = choices.index(cur) if cur in choices else 0
            sel = st.selectbox("Cause", choices, index=idx, key=f"ra_tag_{key}")
            note = st.text_area("Note", value=r.get("note") if pd.notna(r.get("note")) else "",
                                key=f"ra_note_{key}", height=80)
            if st.button("Save review", key=f"ra_save_{key}"):
                job.save_note(key, None if sel.startswith("(auto)") else sel, note)
                st.toast(f"Saved review for {r['symbol']}.")
                st.rerun()


# ── Pick replay: the chart on the pick day beside what happened since ────────
@st.cache_data(ttl=600, show_spinner=False)
def _replay_bars(symbol: str) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """(symbol bars, NIFTY 500 bars) from the audit's price cache. Never fetches."""
    got = job.bars_for([symbol, job.MARKET])
    return got.get(symbol), got.get(job.MARKET)


def _replay_tab(eps: pd.DataFrame, h: int, src: str) -> None:
    st.caption("One pick at a time: the chart as the desk saw it on the pick day, beside "
               f"everything since. Winners beat NIFTY 500 by ≥ {rp.WIN_EXCESS_PCT:g}% at "
               f"{h} sessions; losers are the post-mortem failures.")
    kind = (st.pills("Show", ["Losers", "Winners", "All"], default="Losers",
                     key="ra_rp_kind") or "Losers").lower()
    tag = None
    if kind == "losers" and "review_tag" in eps:
        tags = sorted(t for t in eps["review_tag"].dropna().unique() if t)
        pick = st.selectbox("Cause", ["Any", *tags], key="ra_rp_tag")
        tag = None if pick == "Any" else pick
    cands = rp.replay_candidates(eps, kind, tag, h)
    st.caption("Plan results for these picks: **" + rp.scorecard_text(rp.scorecard(cands))
               + "** · ambiguous bars count as SL hit; no plan has a break-even rule, so "
                 "there is no cost-to-cost count.")
    if cands.empty:
        st.info("No picks match this filter.")
        return
    i = st.selectbox("Pick", list(cands.index), key=f"ra_rp_pick_{src}_{kind}_{tag}",
                     format_func=lambda j: rp.replay_label(cands.loc[j], h))
    _replay_view(cands.loc[i], h, "tab")


def _replay_view(r: pd.Series, h: int, key: str) -> None:
    bars, idx = _replay_bars(str(r["symbol"]))
    f = rp.replay_frame(r, bars, idx, h=h)
    if f["missing"]:
        st.info(f["missing"])
        return
    txt = rp._text
    _snapshot(r, f, h, key)
    parts = [f"rank {int(r['rank'])}" if rp._num(r.get("rank")) is not None else "",
             f"score {rp._num(r.get('score')):.1f}" if rp._num(r.get("score")) is not None else "",
             txt(r.get("family_names")) or txt(r.get("scanners")) or txt(r.get("scanner")),
             f"flags: {txt(r.get('risk_flags'))}" if txt(r.get("risk_flags")) else "",
             f"{rp._num(r.get('ext_vs_ema20')):+.1f}% vs 20 EMA"
             if rp._num(r.get("ext_vs_ema20")) is not None else "",
             f"plan: {txt(r.get('plan_source'))}" if txt(r.get("plan_source")) else "",
             f"regime: {txt(r.get('market_regime'))}" if txt(r.get("market_regime")) else "",
             f"RVol {f['rvol']:.0f}%" if f["rvol"] is not None else ""]
    st.caption("On the pick day — " + " · ".join(p for p in parts if p))
    st.plotly_chart(rp.replay_figure(f, r, h), use_container_width=True,
                    key=f"ra_rp_fig_{key}_{r.get('episode_id')}")
    if f["note"]:
        st.caption("⚠️ " + f["note"])
    if f["off_chart"]:
        st.caption("⚠️ Not drawn — more than " f"{rp.OFF_CHART_PCT:.0f}% from the pick-day "
                   "close, likely stale plan data: "
                   + ", ".join(f"{k} ₹{v:,.2f}" for k, v in f["off_chart"].items()))
    st.markdown(f"**{rp.footer_line(r, f)}**")
    tag = txt(r.get("review_tag"))
    others = [t for t in txt(r.get("tags")).split(", ") if t and t != tag]
    detail = [f"{h}d {_pct(r.get(f'ret_{h}'))}", f"vs NIFTY 500 {_pct(r.get(f'excess_{h}'))}",
              f"vs sector {_pct(r.get(f'excess_sec_{h}'))}",
              f"best {_pct(r.get('mfe'))} / worst {_pct(r.get('mae'))}"]
    if tag:
        detail.append(f"cause {tag}" + (f" (+{', '.join(others)})" if others else ""))
    if txt(r.get("note")):
        detail.append(f"📝 {txt(r.get('note'))}")
    st.caption(" · ".join(detail))
    import rec_rescore as rr
    scores, _ = _rescore_for(r)
    a, b = st.columns(2)
    a.link_button("Open in Multi-Chart ↗ (before / after, side by side)",
                  rp.multichart_url(r, f, ddate=rr.first_downgrade(scores)),
                  use_container_width=True)
    b.link_button("Analyzer ↗", link("analyze", r["symbol"]), use_container_width=True)


def _lessons_tab(eps: pd.DataFrame, h: int, src: str) -> None:
    """The learning database: what the judged picks had in common, losers vs winners."""
    st.caption(f"Every judged pick gets machine-readable lessons (✓ and ✗) from its stored "
               f"audit row. Below: each ✗ lesson's share of all judged picks, of losers "
               f"(audit failures at {h} sessions) and of winners. **Lift** = share of "
               "losers ÷ share of winners: near 1 means losers and winners had it equally "
               "often, so it did not sink the losers. Descriptive, not causal; thresholds "
               "are the audit's untested priors.")
    t = rp.lesson_table(eps, h)
    if t.empty:
        st.info("No judged picks yet.")
        return
    st.dataframe(t.drop(columns=["id"]), hide_index=True, use_container_width=True,
                 column_config={
                     "lesson": "Lesson", "picks": "Picks",
                     "pct_all": st.column_config.NumberColumn("% of all", format="%.1f%%"),
                     "pct_losers": st.column_config.NumberColumn("% of losers", format="%.1f%%"),
                     "pct_winners": st.column_config.NumberColumn("% of winners",
                                                                  format="%.1f%%"),
                     "lift": st.column_config.NumberColumn("Lift", format="%.1f×"),
                     "note": "Note"})
    st.download_button("Download lessons (JSON lines, one pick per line)",
                       rp.lessons_jsonl(eps, h), file_name=f"lessons_{src}.jsonl",
                       mime="application/json", key=f"ra_lessons_dl_{src}")
    if src == "opportunity":
        _decay_section(eps, h)


def _decay_section(eps: pd.DataFrame, h: int) -> None:
    """Median rating drift by session since entry, judged winners vs losers."""
    st.markdown("**Confidence decay**")
    st.caption("Median rating drift (vs the pick-day rating) by session since entry, for "
               f"picks judged at {h} sessions: winners vs losers (audit failures). Fills in "
               "as the nightly re-score accrues; descriptive, not causal.")
    t = rp.decay_table(eps, _all_scores(), h)
    if t.empty:
        st.info("No re-scored picks yet — tracking starts with the next nightly run.")
        return
    st.line_chart(t.set_index("sessions_since_entry")[["winners_median", "losers_median"]]
                  .rename(columns={"winners_median": "winners", "losers_median": "losers"}))
    st.dataframe(t, hide_index=True, use_container_width=True)


_BADGE = {"green": "green-badge", "amber": "orange-badge", "red": "red-badge",
          "grey": "gray-badge"}


def _snapshot(r: pd.Series, f: dict, h: int, key: str) -> None:
    """Decision snapshot: the numbers, the Green/Amber/Red verdict with thesis,
    process and outcome judged apart, and the MFE/MAE ladder."""
    s, v = rp.snapshot(r, f, h), rp.verdict(r, f, h)
    money = lambda x: "—" if x is None else rp._rs(x)          # noqa: E731
    with st.container(border=True):
        head = (f"**PICK AUDIT · {r['symbol']}** · picked {str(r['rec_date'])[:10]}"
                + (f" · rank #{s['rank']}" if s["rank"] is not None else "")
                + (f" · on shortlist {s['shortlist']}" if s["shortlist"] else ""))
        st.markdown(f"{head} &nbsp; :{_BADGE[s['colour']]}[{s['outcome']}]")
        scores, pick_uni = _rescore_for(r)
        rescore = [rp.drift_line(r, scores, pick_uni), rp.what_moved(r, scores, pick_uni),
                   rp.scanners_line(r, scores)]
        if r.get("source", "opportunity") == "opportunity":   # only shortlist picks are re-scored
            st.caption(" · ".join(x for x in rescore if x))
        c = st.columns(6)
        c[0].metric("Entry", money(s["entry"]))
        c[1].metric("Current", money(s["current"]))
        c[2].metric(f"{h}D return", _pct(s["ret_h"]))
        c[3].metric("To date", _pct(s["to_date"]))
        c[4].metric("vs NIFTY 500", _pct(s["vs_n500"]))
        c[5].metric("vs sector", _pct(s["vs_sector"]))
        left, right = st.columns([3, 2])
        with left:
            st.markdown("**Verdict** — process and outcome judged separately")
            st.markdown("  \n".join(f"{'✓' if ok else '✗'} {t}" for ok, t in v["items"])
                        + "".join(f"  \n{'✓' if ok else '✗'} {t} — {note}"
                                  for ok, t, note in v["stop"]))
            st.markdown("**Process on the pick day**")
            st.markdown("  \n".join(f"{'✓' if ok else '✗'} {lbl}" for ok, lbl in v["checks"]))
            st.caption("Green = thesis and process right · Amber = mixed · Red = both wrong. "
                       "Thesis = beat NIFTY 500 over the window; process uses only pick-day "
                       "facts and the audit's own thresholds.")
            ls = rp.lessons(r, h)
            if ls:
                st.markdown("**Lessons detected**")
                st.markdown("  \n".join(f"{'✓' if x['ok'] else '✗'} {x['text']}" for x in ls))
        with right:
            if not f["post"].empty:
                st.plotly_chart(rp.excursion_figure(r, f), use_container_width=True,
                                key=f"ra_rp_mfe_{key}_{r.get('episode_id')}")
                ins = rp.excursion_insight(r, f["levels"]["entry_px"])
                if ins:
                    st.caption(ins)
            if not scores.empty:
                st.markdown("**Confidence decay**")
                st.plotly_chart(rp.decay_figure(r, scores), use_container_width=True,
                                key=f"ra_rp_decay_{key}_{r.get('episode_id')}")
                st.caption("D = rating 15+ points below the pick day — a prior, not a "
                           "tested signal.")


@st.dialog("Pick replay", width="large")
def _replay_dialog(r: pd.Series, h: int) -> None:
    _replay_view(r, h, "dlg")


def _all_picks(eps: pd.DataFrame, h: int) -> None:
    cols = ["symbol", "scanner", "rec_date", "rank", "status", f"ret_{h}", f"excess_{h}",
            f"excess_sc_{h}", f"excess_ew_{h}", "mfe", "mae", "plan_outcome", "review_tag", "family_names",
            "sector", "appearances"]
    d = eps[[c for c in cols if c in eps]].copy()
    d["rec_date"] = d["rec_date"].astype(str).str[:10]
    d.insert(1, "open", d["symbol"].map(lambda s: link("analyze", s)))
    st.dataframe(d.sort_values("rec_date", ascending=False), hide_index=True,
                 use_container_width=True, column_config={
                     "open": st.column_config.LinkColumn("", display_text="↗", width="small"),
                     "rec_date": "Picked", f"ret_{h}": st.column_config.NumberColumn(
                         f"{h}d return", format="%+.2f%%"),
                     f"excess_{h}": st.column_config.NumberColumn("vs NIFTY 500", format="%+.2f%%"),
                     f"excess_sc_{h}": st.column_config.NumberColumn("vs Smallcap", format="%+.2f%%"),
                     f"excess_ew_{h}": st.column_config.NumberColumn("vs equal-weight",
                                                                    format="%+.2f%%"),
                     "mfe": st.column_config.NumberColumn("Best", format="%+.1f%%"),
                     "mae": st.column_config.NumberColumn("Worst", format="%+.1f%%"),
                     "review_tag": "Failure cause", "appearances": "Runs on list"})


def _proposals(src: str) -> None:
    st.caption(f"Proposed only from slices with ≥ {ra.MIN_N} picks, an entry-week "
               f"|t| ≥ {ra.PROPOSAL_T:g}, and a presence in ≥ {ra.PROPOSAL_MIN_MONTHS} monthly "
               "batches. Nothing here changes a weight: an accepted change is made in code "
               "and shows up as a new model version, which the 'Model version' slice then "
               "compares before and after. A rejected idea is not raised again.")
    d = job.load_decisions()
    d = d[d["source"] == src] if not d.empty else d
    if d.empty:
        st.info("No proposals: no slice has held up strongly enough yet.")
        return
    for _, r in d.iterrows():
        with st.container(border=True):
            badge = {"pending": ":orange-badge[pending]", "accepted": ":green-badge[accepted]",
                     "rejected": ":gray-badge[rejected]"}.get(r["decision"], r["decision"])
            st.markdown(f"{badge} {r['proposal']}")
            st.caption(f"Raised {str(r['created_at'])[:10]} · last seen as of {r['as_of']}"
                       + (f" · decided {str(r['decided_at'])[:10]}" if r.get("decided_at") else "")
                       + (f" · 📝 {r['note']}" if r.get("note") else ""))
            if r["decision"] == "pending":
                k = int(r["id"])
                note = st.text_input("Note", key=f"ra_dec_note_{k}")
                a, b = st.columns(2)
                if a.button("Accept", key=f"ra_acc_{k}", use_container_width=True):
                    job.decide(k, "accepted", note)
                    st.rerun()
                if b.button("Reject", key=f"ra_rej_{k}", use_container_width=True):
                    job.decide(k, "rejected", note)
                    st.rerun()


def _history(history: pd.DataFrame) -> None:
    st.caption("One row per audit run — how the headline moved as picks matured.")
    if history.empty:
        return
    import json
    s = history["summary_json"].map(lambda j: json.loads(j or "{}"))
    out = pd.DataFrame({
        "as of": history["as_of"], "run": history["created_at"].str.replace("T", " "),
        "judged": s.map(lambda x: x.get("n")),
        "median vs NIFTY 500": s.map(lambda x: x.get("median_excess")),
        "median vs Smallcap": s.map(lambda x: x.get("median_excess_smallcap")),
        "median vs equal-weight": s.map(lambda x: x.get("median_excess_ew")),
        "t (weekly)": s.map(lambda x: x.get("t_excess_weekly")),
        "failures": s.map(lambda x: x.get("failures"))})
    st.dataframe(out.iloc[::-1], hide_index=True, use_container_width=True)


# ── Pick re-score (spec 2026-11-26 pick-rescore §4) ──────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def _all_scores() -> pd.DataFrame:
    """Every stored nightly re-score row (rec_audit.db › pick_scores). Never fetches."""
    import rec_rescore_job as rj
    return rj.load_scores(db_path=rj.DB_PATH)


def _rescore_for(ep) -> tuple[pd.DataFrame, dict | None]:
    """(this pick's re-score rows, its pick-day universe row or None)."""
    import rec_rescore_job as rj
    s = _all_scores()
    s = s[s["episode_id"] == ep.get("episode_id")] if not s.empty else s
    try:
        pick = rj.pick_day_universe(str(ep.get("symbol")), str(ep.get("rec_date"))[:10])
    except Exception:                 # universe table not created yet on this DB
        pick = None
    return s, pick


# ── A3: the track-record line on Opportunity Hub cards ───────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def _track_record_cached() -> dict:
    return job.track_record()


def track_record_text(families, tr: dict | None = None, h: int = ra.HEADLINE_H) -> str:
    """'Audit 21d vs NIFTY 500: Trend/Momentum +1.9% (n 234) · … — not significant',
    or '' when no family of the card has an audited record yet. Plain text: the
    caller decides how to show it."""
    tr = _track_record_cached() if tr is None else tr
    # Only families with a readable record (n >= MIN_N), at most three: a card
    # line, not a table, and a 14-pick slice is noise either way.
    fams = [f for f in (families or []) if f in tr and (tr[f].get("n") or 0) >= ra.MIN_N][:3]
    if not fams:
        return ""
    parts = [f"{f} {tr[f]['median_excess']:+.1f}% (n {tr[f]['n']})" for f in fams
             if tr[f].get("median_excess") is not None]
    if not parts:
        return ""
    sig = any(abs(tr[f].get("t_weekly") or 0) >= 2 for f in fams)
    return (f"Audit {h}d vs NIFTY 500: " + " · ".join(parts)
            + ("" if sig else " — not significant"))
