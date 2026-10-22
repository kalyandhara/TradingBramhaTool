"""Recommendation Audit page (A2) — how every past Opportunity Hub pick did.

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

HORIZONS = ra.HORIZONS
#: Slice label → column (derived columns are added by `with_slices`).
SLICES: dict[str, str] = {
    "Scanner family": "family_names", "Sector": "sector", "Rank band": "rank_band",
    "Risk flags at pick": "flagged", "Plan source": "plan_source",
    "Model version": "model_version", "Market regime": "market_regime",
    "Days on list": "list_band",
}
REVIEW_TAGS: tuple[str, ...] = (*ra.TAG_ORDER, ra.UNEXPLAINED)
CARDS_PER_PAGE = 12


# ── Pure helpers (tested) ────────────────────────────────────────────────────
def with_slices(eps: pd.DataFrame) -> pd.DataFrame:
    """Add the derived slice columns: rank band, flagged/clean, days-on-list band."""
    if eps.empty:
        return eps
    d = eps.copy()
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


def tag_counts(eps: pd.DataFrame) -> dict[str, int]:
    q = review_queue(eps)
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
    data = job.load_latest()
    run, eps = data["run"], data["episodes"]

    top = st.columns([5, 1])
    if run is None:
        top[0].info("No audit stored yet. Run it once (about 3 minutes — it fetches "
                    "daily bars for every past pick), or register the **Recommendation "
                    "Audit** job in Scheduler Hub to run it after each close.")
    else:
        top[0].caption(
            f"As of **{run['as_of']}** · run {run['created_at'].replace('T', ' ')} · "
            f"{len(eps)} picks since {str(eps['rec_date'].min())[:10]}. Entry = next "
            f"session's open; every return is compared with benchmarks over the same dates.")
    if top[1].button("↻ Re-run audit", key="ra_rerun", use_container_width=True):
        with st.spinner("Fetching prices and re-scoring every pick…"):
            try:
                rep = job.run_audit()
                job.write_monthly_report(rep, pd.Timestamp(rep["episodes_df"]["as_of"]
                                                           .iloc[0]).date())
                st.toast("Audit refreshed.")
            except Exception as e:
                st.error(f"Audit failed: {type(e).__name__}: {e}")
                return
        st.rerun()
    if run is None or eps.empty:
        return

    eps = with_slices(eps)
    h = st.segmented_control("Horizon (sessions)", HORIZONS, default=ra.HEADLINE_H,
                             key="ra_h") or ra.HEADLINE_H
    _tiles(eps, data["portfolio"], h)

    tabs = st.tabs(["Monthly batches", "What worked", "Post-mortems", "All picks",
                    "Run history"])
    with tabs[0]:
        _cohorts(eps)
    with tabs[1]:
        _attribution(eps, h)
    with tabs[2]:
        _postmortems(eps)
    with tabs[3]:
        _all_picks(eps, h)
    with tabs[4]:
        _history(data["history"])


def _tiles(eps: pd.DataFrame, port: pd.DataFrame, h: int) -> None:
    s = ra.summarise(eps, h)
    c = st.columns(6)
    c[0].metric("Picks judged", s["n"], help=f"Picks at least {h} sessions old. "
                f"{s['pending']} not yet entered, {s['no_data']} with no price data, "
                f"{s['data_suspect']} set aside for a suspected split/bonus "
                f"(a ≥{ra.SPLIT_SUSPECT_PCT:.0f}% one-day move).")
    c[1].metric("Went up", _pct(s["hit_rate"], False))
    c[2].metric("Median vs NIFTY 500", _pct(s["median_excess"]),
                help=f"{_pct(s['beat_market_rate'], False)} of picks beat it")
    c[3].metric("Median vs Smallcap 250", _pct(s["median_excess_smallcap"]),
                help="Most picks are small caps — this is the like-for-like benchmark.")
    tw = s.get("t_excess_weekly")
    c[4].metric("Significance (t)", "—" if tw is None else f"{tw:.2f}",
                help=f"Picks grouped by entry week ({s['weeks']} weeks): picks entered the "
                     "same week move together, so the per-pick t overstates confidence. "
                     "Below 2 is not significant.")
    if not port.empty and h == ra.HEADLINE_H:
        b, m = (port["basket"].iloc[-1] - 1) * 100, (port["market"].iloc[-1] - 1) * 100
        c[5].metric("₹1 in every pick", _pct(b), delta=f"{b - m:+.2f} pts vs NIFTY 500",
                    help=f"Each pick held {ra.HEADLINE_H} sessions from its entry open; "
                         "a shadow ₹1 in NIFTY 500 over the same dates.")
    if tw is not None and abs(tw) < 2:
        st.caption(f"⚠️ Not statistically significant at {h} sessions (t = {tw:.2f} over "
                   f"{s['weeks']} entry weeks). Treat slices below as leads, not findings.")
    if not port.empty and h == ra.HEADLINE_H:
        st.line_chart(((port[["basket", "market"]] - 1) * 100)
                      .rename(columns={"basket": "₹1 per pick", "market": "NIFTY 500 shadow"}),
                      height=220, y_label="% return")


def _cohorts(eps: pd.DataFrame) -> None:
    st.caption("Each month's picks, judged at each horizon: median return over NIFTY 500, "
               "and the share that beat it. A blank cell is a horizon not reached yet.")
    co = ra.cohorts(eps)
    if co.empty:
        st.info("No cohorts yet.")
        return
    # Unreached horizons are None in an object column, which renders "None".
    co = co.apply(lambda s: s if s.name == "month" else pd.to_numeric(s, errors="coerce"))
    cfg = {"month": "Month", "episodes": "Picks"}
    for hh in HORIZONS:
        cfg[f"n_{hh}"] = st.column_config.NumberColumn(f"n {hh}d")
        cfg[f"med_excess_{hh}"] = st.column_config.NumberColumn(f"Median {hh}d", format="%+.2f%%")
        cfg[f"beat_{hh}"] = st.column_config.NumberColumn(f"Beat {hh}d", format="%.0f%%")
    st.dataframe(co, column_config=cfg, hide_index=True, use_container_width=True)


def _attribution(eps: pd.DataFrame, h: int) -> None:
    label = st.selectbox("Slice by", list(SLICES), key="ra_slice")
    col = SLICES[label]
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


def _postmortems(eps: pd.DataFrame) -> None:
    counts = tag_counts(eps)
    if not counts:
        st.success("No failures among the judged picks.")
        return
    st.caption(f"Failures at {ra.HEADLINE_H} sessions: return or excess ≤ "
               f"{ra.FAIL_RET_PCT:.0f}%, or the stop hit first. The tag is the first "
               "explanation that applies; override it and add a note after you look.")
    opts = [f"All ({sum(counts.values())})"] + [f"{t} ({n})" for t, n in counts.items()]
    pick = st.pills("Cause", opts, default=opts[0], key="ra_tag") or opts[0]
    tag = None if pick.startswith("All") else pick.rsplit(" (", 1)[0]
    q = review_queue(eps, tag)
    pages = max(1, -(-len(q) // CARDS_PER_PAGE))
    pg = st.number_input("Page", 1, pages, 1, key=f"ra_pg_{tag}") if pages > 1 else 1
    chunk = q.iloc[(pg - 1) * CARDS_PER_PAGE: pg * CARDS_PER_PAGE]
    cols = st.columns(3)
    for i, (_, r) in enumerate(chunk.iterrows()):
        with cols[i % 3]:
            _card(r)


def _card(r: pd.Series) -> None:
    h = ra.HEADLINE_H
    with st.container(border=True):
        st.markdown(f"**{r['symbol']}** · picked {str(r['rec_date'])[:10]} · "
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
        a, b = st.columns(2)
        a.link_button("Analyzer ↗", link("analyze", r["symbol"]), use_container_width=True)
        b.link_button("Predict ↗", link("predict", r["symbol"]), use_container_width=True)
        with st.expander("Review"):
            key = r["episode_id"]
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


def _all_picks(eps: pd.DataFrame, h: int) -> None:
    cols = ["symbol", "rec_date", "rank", "status", f"ret_{h}", f"excess_{h}",
            f"excess_sc_{h}", "mfe", "mae", "plan_outcome", "review_tag", "family_names",
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
                     "mfe": st.column_config.NumberColumn("Best", format="%+.1f%%"),
                     "mae": st.column_config.NumberColumn("Worst", format="%+.1f%%"),
                     "review_tag": "Failure cause", "appearances": "Runs on list"})


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
        "t (weekly)": s.map(lambda x: x.get("t_excess_weekly")),
        "failures": s.map(lambda x: x.get("failures"))})
    st.dataframe(out.iloc[::-1], hide_index=True, use_container_width=True)
