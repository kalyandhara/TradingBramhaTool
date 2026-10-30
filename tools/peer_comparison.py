#!/usr/bin/env python3
"""FP-1 — peer resolution + the fundamental peer group.

See wiki/analyses/Analyzer-Radar-Peers-Roadmap.md.

What this module is
-------------------
Given an anchor symbol, find the listed names that are *actually its peers* and
score every one of them through the SAME scorer the Stock Analyzer already uses
(`fundamental_score.score_all`). It adds no metric, no band and no opinion — the
whole point is that the anchor's six axes and its peers' six axes come out of one
scorer, so "cheaper than its peers" means what the donuts already mean.

Why peer resolution is two-stage
--------------------------------
The NSE constituent files carry an `industry` field, but it is NSE's *macro
sector* ("Financial Services" covers ~130 names) — far too coarse to call a peer
group. yfinance's `.info` industry is the fine one ("Insurance - Diversified"),
but it costs a network call per symbol, so tagging the whole market to answer one
question is absurd. So: the offline file narrows the candidate pool by macro
sector, and only that pool is tagged with the fine industry. Tags are cached to
disk (`cache/peer_tags.json`), so the first anchor in a sector pays the tagging
cost once and every later anchor in that sector is instant.

Guards, which are the substance of this phase
---------------------------------------------
- **MIN_PEERS** — below four tagged peers this returns a reason string, not a
  table. Two names side by side look like a comparison and are not one; yfinance
  industry tags are known to be coarse or missing for NSE mid/small-caps, and the
  honest output there is "too few peers", not a chart.
- **MAX_PEERS** — at most twelve peers are *scored*, ranked by market cap, because
  each scored name costs an `.info` call plus three statement calls. Tagging is
  cheap and cached; scoring is not.
- **Coverage travels with every row.** A peer whose statements did not resolve
  scores `None` on those axes and reports its coverage, exactly as the anchor does
  on the Stock Analyzer. A missing input must never arrive in the table as a low
  score — that would rank a company down for our data gap.
"""
from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

import pandas as pd

import fundamental_score as fscore

_log = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / "cache"
TAGS_FILE = CACHE_DIR / "peer_tags.json"
CONSTITUENT_FILES = (
    CACHE_DIR / "nse_niftytotalmarket_constituents.json",   # 754 names, superset
    CACHE_DIR / "nse_nifty500_constituents.json",
)

MIN_PEERS = 4          # below this we say "too few peers", never draw a comparison
MAX_PEERS = 12         # scored peers; each one is ~4 network calls
POOL_CAP = 220         # safety valve on how many names we will ever tag at once
TAG_TTL_DAYS = 30      # a company's industry does not change; its market cap does
_TAG_TTL = TAG_TTL_DAYS * 86400


# ──────────────────────────────────────────────────────────────────────────────
# Stage 0 — the offline candidate pool (no network)
# ──────────────────────────────────────────────────────────────────────────────
def _constituents() -> dict[str, dict]:
    """symbol -> {name, macro_sector} from the cached NSE constituent lists."""
    out: dict[str, dict] = {}
    for path in CONSTITUENT_FILES:
        if not path.exists():
            continue
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            _log.warning("peer_comparison: unreadable constituent file %s", path)
            continue
        for r in rows:
            sym = (r.get("symbol") or "").strip().upper()
            if sym and sym not in out:
                out[sym] = {"name": r.get("name") or sym,
                            "macro_sector": r.get("industry") or None}
    return out


def candidate_pool(anchor: str) -> tuple[list[str], str | None]:
    """(candidates, macro_sector) — every listed name sharing the anchor's NSE
    macro sector. Returns ([], None) when the anchor is not in the cached lists,
    which is a real answer: we have no defensible pool to search."""
    universe = _constituents()
    a = (anchor or "").strip().upper()
    row = universe.get(a)
    if not row or not row.get("macro_sector"):
        return [], None
    sector = row["macro_sector"]
    pool = [s for s, r in universe.items() if r.get("macro_sector") == sector]
    return pool[:POOL_CAP], sector


# ──────────────────────────────────────────────────────────────────────────────
# Stage 1 — fine industry tags (network, disk-cached)
# ──────────────────────────────────────────────────────────────────────────────
def _load_tags() -> dict[str, dict]:
    if not TAGS_FILE.exists():
        return {}
    try:
        return json.loads(TAGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_tags(tags: dict[str, dict]) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        TAGS_FILE.write_text(json.dumps(tags, indent=0, sort_keys=True),
                             encoding="utf-8")
    except Exception as exc:                    # a cache write must never break a page
        _log.warning("peer_comparison: could not write tag cache: %s", exc)


def _fetch_tag(symbol: str) -> dict | None:
    """One `.info` call — the fine industry + market cap. Deliberately NOT
    `scanner_templates.fetch_fundamentals_yf`, which also pulls the cashflow
    statement: at pool scale that would be hundreds of statement downloads to
    answer 'what industry is this'."""
    try:
        import yfinance as yf
        info = yf.Ticker(f"{symbol}.NS").info or {}
    except Exception:
        return None
    industry = info.get("industry")
    if not industry:
        return None
    mc = info.get("marketCap")
    return {
        "industry": industry,
        "sector": info.get("sector"),
        "name": info.get("longName") or info.get("shortName") or symbol,
        "market_cap_cr": round(mc / 1e7, 1) if isinstance(mc, (int, float)) else None,
        "ts": int(time.time()),
    }


def tag_symbols(symbols: list[str], *, progress_cb: Callable[[int, int], None] | None = None,
                max_workers: int = 8) -> dict[str, dict]:
    """Fine industry tags for `symbols`, reading and refreshing the disk cache.

    Symbols yfinance cannot tag are simply absent from the result — they drop out
    of the peer group rather than landing in it as an untagged row.
    """
    tags = _load_tags()
    now = time.time()
    stale = [s for s in symbols
             if now - (tags.get(s, {}).get("ts") or 0) > _TAG_TTL]

    done, total = 0, len(stale)
    if stale:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(_fetch_tag, s): s for s in stale}
            for fut in as_completed(futures):
                sym = futures[fut]
                done += 1
                if progress_cb is not None:
                    try:
                        progress_cb(done, total)
                    except Exception:
                        pass
                try:
                    t = fut.result()
                except Exception:
                    t = None
                if t:
                    tags[sym] = t
        _save_tags(tags)
    return {s: tags[s] for s in symbols if s in tags}


# ──────────────────────────────────────────────────────────────────────────────
# Stage 2 — the peer group
# ──────────────────────────────────────────────────────────────────────────────
def resolve_peers(anchor: str, *, max_peers: int = MAX_PEERS,
                  progress_cb: Callable[[int, int], None] | None = None) -> dict[str, Any]:
    """Resolve the anchor's peer group.

    Returns `{ok, reason, industry, macro_sector, anchor, peers, pool_size,
    tagged, n_same_industry}`. `ok=False` always carries a `reason` written for
    the user, because "we could not build a peer group" is a legitimate and
    common outcome for NSE mid/small-caps and must read as one.
    """
    a = (anchor or "").strip().upper()
    out: dict[str, Any] = {"ok": False, "anchor": a, "peers": [], "industry": None,
                           "macro_sector": None, "pool_size": 0, "tagged": 0,
                           "n_same_industry": 0, "reason": None, "tags": {},
                           "group_level": None, "group_label": None, "n_in_group": 0}

    pool, macro = candidate_pool(a)
    out["macro_sector"], out["pool_size"] = macro, len(pool)
    if not pool:
        out["reason"] = (f"{a} is not in the cached NIFTY-500 / Total-Market lists, "
                         "so there is no defensible pool to search for peers.")
        return out

    tags = tag_symbols(pool, progress_cb=progress_cb)
    out["tags"], out["tagged"] = tags, len(tags)

    anchor_tag = tags.get(a)
    if not anchor_tag:
        out["reason"] = f"yfinance has no industry tag for {a}, so its peer group is undefined."
        return out
    industry = anchor_tag["industry"]
    out["industry"] = industry

    same = [s for s, t in tags.items() if t.get("industry") == industry and s != a]
    out["n_same_industry"] = len(same)
    group, level, label = same, "industry", industry

    if len(same) < MIN_PEERS:
        fam = _family(industry)
        wider = [s for s, t in tags.items()
                 if _family(t.get("industry")) == fam and s != a]
        if len(wider) >= MIN_PEERS:
            group, level, label = wider, "family", fam
        else:
            out["reason"] = (
                f"Only {len(same)} tagged peer(s) in {industry}"
                + (f" and {len(wider)} across {fam} as a whole" if fam != industry else "")
                + f" - below the {MIN_PEERS}-name floor. Two or three names side by "
                  "side look like a comparison without being one, so none is drawn.")
            return out

    out["group_level"], out["group_label"] = level, label
    group.sort(key=lambda s: (tags[s].get("market_cap_cr") or -1), reverse=True)
    out["peers"] = group[:max_peers]
    out["n_in_group"] = len(group)
    out["ok"] = True
    return out


def _family(industry: str | None) -> str | None:
    """The industry FAMILY — yfinance industry strings are hierarchical by
    convention ("Insurance - Life", "Insurance - Diversified", "Banks - Regional"),
    so the text before the separator is a real, if implicit, parent level.

    This exists because the fine tag is too fine for this market. NIACL's exact
    industry has ONE other NSE name in it; IRCTC's has three. Refusing to compare
    is the right answer to a thin group but the wrong answer to a thin *bucket* —
    a life insurer and a general insurer are more comparable to each other than to
    nothing. So the ladder widens one rung and SAYS it widened, rather than
    quietly dropping the floor.
    """
    if not industry:
        return None
    for sep in (" - ", " — ", "—", "-"):
        if sep in industry:
            return industry.split(sep)[0].strip()
    return industry.strip()


def _blank_row(symbol: str, tag: dict | None, is_anchor: bool) -> dict:
    row = {"symbol": symbol, "is_anchor": is_anchor,
           "name": (tag or {}).get("name") or symbol,
           "market_cap_cr": (tag or {}).get("market_cap_cr"),
           "business": None, "entry": None, "coverage_have": 0, "coverage_total": 0}
    for axis in fscore.AXES:
        row[axis] = None
        row[f"{axis}_verdict"] = None
    return row


def score_peer_group(anchor: str, peers: list[str], score_fn: Callable[[str], dict],
                     *, tags: dict[str, dict] | None = None,
                     progress_cb: Callable[[int, int], None] | None = None,
                     max_workers: int = 4) -> pd.DataFrame:
    """One row per name (anchor first): the six axes, Business/Entry words, coverage.

    `score_fn(symbol) -> score_all()-shaped dict` is injected so the dashboard can
    pass its `st.cache_data`-wrapped version and the CLI a plain one; this module
    stays free of Streamlit. Scoring runs on a SMALL pool (4) rather than the
    tagging pool of 8 — each call is four yfinance downloads, and yfinance starts
    throttling well before the network does.
    """
    tags = tags or {}
    symbols = [anchor] + [p for p in peers if p != anchor]
    rows: dict[str, dict] = {}
    done, total = 0, len(symbols)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(score_fn, s): s for s in symbols}
        for fut in as_completed(futures):
            sym = futures[fut]
            done += 1
            if progress_cb is not None:
                try:
                    progress_cb(done, total)
                except Exception:
                    pass
            row = _blank_row(sym, tags.get(sym), sym == anchor)
            try:
                res = fut.result() or {}
            except Exception as exc:
                _log.warning("peer_comparison: scoring %s failed: %s", sym, exc)
                res = {}
            axes = res.get("axes") or {}
            for axis in fscore.AXES:
                a = axes.get(axis) or {}
                row[axis] = a.get("score")
                row[f"{axis}_verdict"] = a.get("verdict")
            row["business"] = (res.get("business") or {}).get("word")
            row["entry"] = (res.get("entry") or {}).get("word")
            cov = res.get("coverage") or {}
            row["coverage_have"], row["coverage_total"] = cov.get("have", 0), cov.get("total", 0)
            rows[sym] = row

    ordered = [rows[s] for s in symbols if s in rows]
    return pd.DataFrame(ordered)


def peer_median(df: pd.DataFrame) -> dict[str, float | None]:
    """Per-axis median of the PEERS (anchor excluded), for FP-2's radar overlay
    and for the 'vs peers' reading. Median, not mean: one loss-maker with a
    zeroed axis drags a six-name mean somewhere no company actually is."""
    if df is None or df.empty or "is_anchor" not in df.columns:
        return {a: None for a in fscore.AXES}
    peers = df[~df["is_anchor"]]
    out: dict[str, float | None] = {}
    for axis in fscore.AXES:
        vals = peers[axis].dropna() if axis in peers.columns else []
        out[axis] = round(float(vals.median()), 1) if len(vals) else None
    return out


# ──────────────────────────────────────────────────────────────────────────────
# FP-2 — the radar, as an OVERLAY
# ──────────────────────────────────────────────────────────────────────────────
def radar_figure(df: pd.DataFrame, median: dict[str, float | None], anchor: str,
                 *, compare: str | None = None):
    """Anchor vs peer median on the six axes, as a Plotly `Scatterpolar`.

    Why an overlay and never a solo trace
    -------------------------------------
    A radar of ONE company is decoration: the six donuts above it already state
    those numbers, more precisely and without the geometry. What a radar adds is
    the answer to a question the donuts cannot reach — *is this shape normal for
    this industry* — and that needs a second polygon. Hence the peer median is
    drawn always, not optionally.

    Two traces by default, three at the absolute most (`compare` names one peer
    for a head-to-head). Radar charts degrade badly past ~4 overlaid series, and
    this one is capped below that on purpose.

    Read SHAPE, never AREA. Polygon area scales as the square of the values and
    depends on axis order, so it is not a quantity; the caption on the page says
    so, and the axis order is fixed by `fscore.AXES` for the same reason — rotating
    the axes would change the apparent verdict for identical data.
    """
    import plotly.graph_objects as go
    import report_style as rs

    axes = list(fscore.AXES)
    labels = [fscore.AXIS_LABELS[a] for a in axes]

    def _vals(row_or_dict) -> list[float | None]:
        out = []
        for a in axes:
            v = (row_or_dict.get(a) if isinstance(row_or_dict, dict)
                 else row_or_dict[a])
            out.append(_score_or_none(v))
        return out

    arow = df[df["is_anchor"]]
    anchor_vals = _vals(arow.iloc[0]) if len(arow) else [None] * len(axes)
    med_vals = _vals(median or {})

    def _closed(vals):
        """Close the polygon: Plotly does not join the last vertex to the first."""
        return list(vals) + [vals[0]] if vals else vals

    theta = labels + [labels[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=_closed(med_vals), theta=theta, name="Peer median",
        fill="toself", fillcolor="rgba(154,160,166,.16)",
        line=dict(color=rs.TOKENS["text_muted"], width=2, dash="dot"),
        hovertemplate="%{theta}: %{r:.0f}<extra>Peer median</extra>",
    ))
    if compare:
        crow = df[df["symbol"] == compare]
        if len(crow):
            fig.add_trace(go.Scatterpolar(
                r=_closed(_vals(crow.iloc[0])), theta=theta, name=compare,
                fill="toself", fillcolor="rgba(37,99,235,.12)",
                line=dict(color=rs.TOKENS["info"], width=1.5),
                hovertemplate="%{theta}: %{r:.0f}<extra>" + compare + "</extra>",
            ))
    fig.add_trace(go.Scatterpolar(
        r=_closed(anchor_vals), theta=theta, name=anchor,
        fill="toself", fillcolor="rgba(217,119,6,.18)",
        line=dict(color=rs.TOKENS["accent"], width=2.5),
        hovertemplate="%{theta}: %{r:.0f}<extra>" + anchor + "</extra>",
    ))

    fig.update_layout(
        polar=dict(
            bgcolor=rs.TOKENS["surface"],
            radialaxis=dict(visible=True, range=[0, 100], tickvals=[25, 50, 75, 100],
                            tickfont=dict(size=9, color=rs.TOKENS["text_muted"]),
                            gridcolor=rs.TOKENS["border"], linecolor=rs.TOKENS["border"]),
            angularaxis=dict(tickfont=dict(size=10, color=rs.TOKENS["text_body"]),
                             gridcolor=rs.TOKENS["border"], linecolor=rs.TOKENS["border"]),
        ),
        showlegend=True,
        legend=dict(orientation="h", y=-0.08, font=dict(size=10)),
        margin=dict(l=60, r=60, t=20, b=40), height=340,
        paper_bgcolor="rgba(0,0,0,0)", font=dict(family=rs.SANS),
    )
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# FP-3 — peer-relative reading (rank), kept strictly apart from the scores
# ──────────────────────────────────────────────────────────────────────────────
#: Word for how the anchor sits against its group on one axis. The thresholds
#: are rank-based, not score-based, because this sentence is the one place the
#: table speaks in PEER-RELATIVE terms and it must not borrow the absolute scale.
def _rank_word(rank: int, n: int) -> str:
    if n <= 1:
        return "unranked"
    if rank == 1:
        return "best in group"
    if rank <= max(2, round(n * 0.25)):
        return "top quartile"
    if rank > n - max(1, round(n * 0.25)):
        return "bottom quartile"
    return "mid-pack"


def rank_report(df: pd.DataFrame, anchor: str) -> dict[str, Any]:
    """Where the anchor stands INSIDE its group, per axis, plus a leader line.

    This is the one peer-relative reading in the feature, and it is deliberately
    reported as a RANK ("3rd of 10"), never as a smooth percentile. In a group of
    six to twelve names a percentile is a weak statistic dressed up as a precise
    one: the gap between 3rd and 4th of 8 is one company, not 12.5 points of
    anything. The six axis scores stay absolute (percentile of the NSE market)
    and the table labels the two readings separately — mixing an absolute score
    and a within-group rank in one column is the error the 2026-07 roadmap
    flagged and the reason this lives in its own function.

    Returns `{axes: {axis: {rank, n, word, best, best_score, anchor_score}},
    leader: {...}, runner_up: {...}, headline: str}`.
    """
    out: dict[str, Any] = {"axes": {}, "leader": None, "runner_up": None, "headline": ""}
    if df is None or df.empty:
        return out

    for axis in fscore.AXES:
        scored = [(r["symbol"], _score_or_none(r[axis])) for _, r in df.iterrows()]
        scored = [(s, v) for s, v in scored if v is not None]
        if not scored:
            out["axes"][axis] = None
            continue
        scored.sort(key=lambda t: t[1], reverse=True)
        best_sym, best_score = scored[0]
        rank = next((i + 1 for i, (s, _) in enumerate(scored) if s == anchor), None)
        a_score = next((v for s, v in scored if s == anchor), None)
        out["axes"][axis] = {
            "rank": rank, "n": len(scored),
            "word": _rank_word(rank, len(scored)) if rank else None,
            "best": best_sym, "best_score": best_score, "anchor_score": a_score,
        }

    # Group leader on the BUSINESS axes only — valuation is a statement about
    # price, and "leads its peer group" must not mean "is the cheapest".
    biz = [a for a in fscore._BUSINESS_AXES if out["axes"].get(a)]
    if biz:
        means: list[tuple[str, float]] = []
        for _, r in df.iterrows():
            vals = [_score_or_none(r[a]) for a in biz]
            vals = [v for v in vals if v is not None]
            if len(vals) >= max(2, len(biz) - 2):        # need most axes to rank fairly
                means.append((r["symbol"], sum(vals) / len(vals)))
        means.sort(key=lambda t: t[1], reverse=True)
        if means:
            out["leader"] = {"symbol": means[0][0], "score": round(means[0][1])}
        if len(means) > 1:
            out["runner_up"] = {"symbol": means[1][0], "score": round(means[1][1])}

    lead, run = out["leader"], out["runner_up"]
    if lead:
        who = ("It is the anchor" if lead["symbol"] == anchor
               else f"{anchor} is not the strongest name here")
        out["headline"] = (
            f"{lead['symbol']} has the strongest business profile in this group "
            f"(mean {lead['score']} across the five business axes)"
            + (f", with {run['symbol']} behind it at {run['score']}. " if run else ". ")
            + who + "."
        )
    return out


# ──────────────────────────────────────────────────────────────────────────────
# FP-4 — the technical columns (opt-in; a second, heavier network pass)
# ──────────────────────────────────────────────────────────────────────────────
#: Technical columns, in the order the 2026-07 mockup showed them, with the
#: direction that makes a value GOOD. `pct_from_52w_high` is stored positive as
#: "percent below the high", so smaller is better.
# `rs_pct` is NOT a percentile. `stock_council._relative_strength` returns
# 6-month (130-bar) outperformance against the Nifty in PERCENTAGE POINTS, so it
# is signed and unbounded — a name can read -30. The 2026-07 mockup showed "RS
# 100 = Best RS", which is a within-group percentile and a different quantity
# entirely; rendering ours under that heading would have been precisely the
# absolute-vs-peer-relative confusion the roadmap warned about. The column is
# therefore labelled "RS 6m" and carries a sign.
TECH_COLUMNS = (
    ("rs_pct",             "RS 6m", False),
    ("rsi",                "RSI",   None),      # None = no good/bad direction
    ("adx",                "ADX",   True),
    ("pct_from_52w_high",  "52w",   False),
    ("stage_label",        "Stage", None),
    ("from_pivot",         "Pivot", None),
)


def stage_label(facts: dict) -> str:
    """A readable stage name over `stock_council._infer_stage`'s 1-4.

    The mockup showed labels the bare number cannot carry — "Continuation",
    "Stage 2 (Early)", "Failed Reclaim". These are a thin, stated heuristic on
    top of the same facts, not a new stage model, and each rule is written out
    so it can be argued with rather than trusted:

      Stage 2 within 10% of the 200SMA   -> "Stage 2 (Early)"   (young trend)
      Stage 2 with the full MA stack     -> "Continuation"      (established)
      Stage 1 but above the 50SMA        -> "Failed Reclaim"    (below the 200,
                                            bouncing, not yet a trend)
    Everything else keeps Weinstein's own word.
    """
    stage = facts.get("stage") or 0
    ext = facts.get("pct_above_sma200")
    if stage == 2:
        if ext is not None and ext < 10:
            return "Stage 2 (Early)"
        return "Continuation" if facts.get("ema_aligned") else "Stage 2"
    if stage == 3:
        return "Topping"
    if stage == 4:
        return "Stage 4"
    if stage == 1:
        price, s50, s200 = facts.get("price"), facts.get("sma50"), facts.get("sma200")
        if None not in (price, s50, s200) and price > s50 and price < s200:
            return "Failed Reclaim"
        return "Basing"
    return "—"


def _one_technical(symbol: str, df, nifty_df) -> dict | None:
    """RS / RSI / ADX / 52w / stage / pivot for one name, from the shared council
    evidence — the same numbers the Stock Analyzer's own read uses, so the peer
    row and the drill-down can never disagree about a peer's RSI."""
    import stock_council as council
    import scanner_templates as sc
    if df is None or len(df) < 60:
        return None
    try:
        facts = council.gather_evidence(symbol, df, nifty_df=nifty_df).facts
    except Exception as exc:
        _log.warning("peer_comparison: evidence for %s failed: %s", symbol, exc)
        return None

    from_pivot = None
    try:
        box = sc._darvas_box(df)
        if box and box.get("box_top"):
            last = float(df["close"].iloc[-1])
            from_pivot = round((last - box["box_top"]) / box["box_top"] * 100, 1)
    except Exception:
        from_pivot = None

    def _r(v, nd=1):
        return None if v is None else round(float(v), nd)

    return {
        "rs_pct": _r(facts.get("rs_pct"), 0),
        "rsi": _r(facts.get("rsi"), 0),
        "adx": _r(facts.get("adx"), 0),
        "pct_from_52w_high": _r(facts.get("pct_from_52w_high"), 1),
        "stage_label": stage_label(facts),
        "from_pivot": from_pivot,
    }


def technical_columns(symbols: list[str], fetch_ohlcv: Callable[[str], Any],
                      nifty_df=None, *,
                      progress_cb: Callable[[int, int], None] | None = None,
                      max_workers: int = 4) -> dict[str, dict]:
    """Technical read for each name. Opt-in on the page for a reason: this is a
    SECOND full network pass over the group (one OHLCV history per peer) on top
    of the four statement calls the fundamental table already paid."""
    out: dict[str, dict] = {}
    done, total = 0, len(symbols)

    def _work(sym: str):
        try:
            return sym, _one_technical(sym, fetch_ohlcv(sym), nifty_df)
        except Exception:
            return sym, None

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for fut in as_completed([ex.submit(_work, s) for s in symbols]):
            done += 1
            if progress_cb is not None:
                try:
                    progress_cb(done, total)
                except Exception:
                    pass
            try:
                sym, res = fut.result()
            except Exception:
                continue
            if res:
                out[sym] = res
    return out


def attach_technicals(df: pd.DataFrame, tech: dict[str, dict]) -> pd.DataFrame:
    """Merge the technical read onto the peer table, leaving gaps as None."""
    if df is None or df.empty:
        return df
    out = df.copy()
    for col, _label, _dir in TECH_COLUMNS:
        out[col] = [(tech.get(s) or {}).get(col) for s in out["symbol"]]
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Stage 3 — the table markup (pure; no Streamlit)
# ──────────────────────────────────────────────────────────────────────────────
def _default_tone(score: int | None) -> str:
    if score is None:
        return "absent"
    return "good" if score >= 70 else ("warn" if score >= 45 else "risk")


def _score_or_none(v: Any) -> int | None:
    """DataFrame-safe read of an axis score.

    A column holding a mix of ints and `None` becomes float64 with `NaN` in the
    gaps, and `NaN is None` is False — so an unscored axis rendered as the literal
    text `nan` in the first build of this table. That is exactly the failure the
    scorer's own no-neutral-50 rule exists to prevent, arriving through pandas
    instead of through the bands. Missing stays missing here too.
    """
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
        return int(round(float(v)))
    except (TypeError, ValueError):
        return None


def _cell(score: int | None, tone_fn: Callable[[int | None], str],
          *, best: bool = False, title: str = "") -> str:
    """One axis cell: an in-cell bar carrying magnitude, tinted by tone.

    A bar rather than a bare heat tint, deliberately — tint alone puts the whole
    reading in hue, which fails for a colour-blind reader and turns a twelve-column
    table into a wash. The bar survives both.

    `best` marks the group's top cell on this axis with a star. That star is the
    ONLY peer-relative mark in the table; the number beside it stays absolute.
    """
    import report_style as rs
    if score is None:
        return (f'<td style="text-align:right;color:{rs.TOKENS["absent"]};'
                f'font-size:10px;">n/a</td>')
    fg, bg = rs.tone_colors(tone_fn(score))
    star = '<span style="font-size:9px;opacity:.85;">&#9733;</span> ' if best else ""
    tip = f' title="{title}"' if title else ""
    return (f'<td style="text-align:right;padding:2px 8px;"{tip}>'
            f'<div style="position:relative;height:18px;background:{bg};'
            f'border-radius:3px;overflow:hidden;">'
            f'<div style="position:absolute;left:0;top:0;bottom:0;width:{score}%;'
            f'background:{fg};opacity:.30;"></div>'
            f'<div class="tb-mono" style="position:relative;text-align:right;'
            f'padding-right:5px;line-height:18px;font-size:11px;color:{fg};'
            f'font-weight:600;">{star}{score}</div></div></td>')


_STAGE_TONE = {
    "Continuation": "good", "Stage 2 (Early)": "good", "Stage 2": "good",
    "Topping": "warn", "Failed Reclaim": "risk", "Stage 4": "risk",
    "Basing": "neutral", "—": "absent",
}


def tech_text(value, col: str) -> str:
    """Display string for a technical value — the ONE formatter.

    It exists because the table and the head-to-head drill briefly disagreed:
    the table rendered 52w as "-3.2%" (percent below the high, signed for the
    reader) while the drill printed the raw stored 3.2, and RS as "+23" against
    a bare "23". Two presentations of one number inside one feature is precisely
    what this whole surface exists to avoid, so both now call this.
    """
    if value is None or (isinstance(value, float) and value != value):
        return "n/a"
    if col == "stage_label":
        return str(value)
    if col == "rs_pct":
        return f"{value:+.0f}"          # points of 6-month outperformance, signed
    if col == "pct_from_52w_high":
        return f"-{value:.1f}%"         # stored positive as "percent BELOW the high"
    if col == "from_pivot":
        return f"{value:+.1f}%"
    return f"{value:.0f}"               # rsi, adx


def _tech_tone(value, col: str) -> str:
    """good / risk / neutral for a technical value. RSI deliberately has no
    direction: 70 is strength or exhaustion depending on the rest of the row."""
    if value is None or (isinstance(value, float) and value != value):
        return "absent"
    if col == "stage_label":
        return _STAGE_TONE.get(str(value), "neutral")
    if col == "rs_pct":
        return "good" if value >= 10 else ("risk" if value <= -10 else "neutral")
    if col == "adx":
        return "good" if value >= 25 else ("risk" if value < 15 else "neutral")
    if col == "pct_from_52w_high":
        return "good" if value <= 10 else ("risk" if value >= 40 else "neutral")
    if col == "from_pivot":
        return "good" if -3 <= value <= 5 else ("risk" if value < -15 else "neutral")
    return "neutral"


def _tech_cell(value, col: str) -> str:
    """A technical cell. Plain figures, not bars.

    The six axis scores share one 0-100 scale, so a bar is comparable across
    them; RSI 62, ADX 28 and -14% from the high do not share a scale and a bar
    would invent one. Tone still encodes good/bad where the metric has a
    direction.
    """
    import report_style as rs
    tone = _tech_tone(value, col)
    if tone == "absent":
        return (f'<td style="text-align:right;color:{rs.TOKENS["absent"]};'
                f'font-size:10px;">n/a</td>')

    txt = tech_text(value, col)
    if col == "stage_label":
        fg, bg = rs.tone_colors(tone)
        return (f'<td style="text-align:center;white-space:nowrap;">'
                f'<span style="background:{bg};color:{fg};border-radius:3px;'
                f'padding:2px 6px;font-size:10px;font-weight:600;">{txt}</span></td>')

    return (f'<td style="text-align:right;" class="tb-mono">'
            f'<span style="font-size:11px;color:{rs.tone_colors(tone)[0]};">'
            f'{txt}</span></td>')


def table_html(df: pd.DataFrame, median: dict[str, float | None], anchor: str,
               *, tone_fn: Callable[[int | None], str] | None = None,
               ranks: dict | None = None, with_technicals: bool = False) -> str:
    """The peer table as standalone HTML.

    Layout follows current data-table practice for a wide comparison grid: sticky
    header, frozen identifier column (with the shadow that makes it read as a
    layer rather than a seam), z-order header > frozen column > body so nothing
    bleeds through at the intersection, dense 36px rows, numbers right-aligned.

    Two readings share this table and the header says which is which. **Every
    number in it is ABSOLUTE** — the six axes are percentiles of the NSE
    distribution, RS is versus the Nifty — and the only PEER-RELATIVE mark is the
    ★ on the group's best cell per axis. Mixing an absolute score and a
    within-group rank in one column, unlabelled, is exactly the trap the 2026-07
    roadmap flagged; the group header row exists to keep them apart.
    """
    import report_style as rs
    tone_fn = tone_fn or _default_tone
    t = rs.TOKENS
    ranks = (ranks or {}).get("axes") or {}
    tech_cols = [c for c in TECH_COLUMNS if c[0] in (df.columns if df is not None else [])] \
        if with_technicals else []

    heads = "".join(f'<th style="text-align:right;white-space:nowrap;">'
                    f'{fscore.AXIS_LABELS[a]}</th>' for a in fscore.AXES)
    tech_heads = "".join(f'<th style="text-align:{"center" if c == "stage_label" else "right"};'
                         f'white-space:nowrap;">{label}</th>' for c, label, _ in tech_cols)

    # Group header — the line that keeps the two readings apart.
    group_head = (
        f'<tr class="tb-peer-grp"><th style="text-align:left;"></th>'
        f'<th colspan="{len(fscore.AXES)}">Fundamental axes · absolute, 0-100 vs the NSE distribution</th>'
        f'<th colspan="3">Verdict &amp; coverage</th>'
        + (f'<th colspan="{len(tech_cols)}">Technicals · absolute (RS 6m = points of outperformance vs Nifty)</th>'
           if tech_cols else "")
        + '</tr>'
    )

    rows_html = []
    for _, r in df.iterrows():
        is_anchor = bool(r["is_anchor"])
        tint = t["surface_warm"] if is_anchor else t["surface"]
        name = f'<b>{r["symbol"]}</b>' if is_anchor else r["symbol"]
        cov = f'{r["coverage_have"]}/{r["coverage_total"]}' if r["coverage_total"] else rs.NA
        cov_tone = ("good" if r["coverage_total"]
                    and r["coverage_have"] / r["coverage_total"] >= 0.8 else "warn")

        axis_cells = []
        for a in fscore.AXES:
            info = ranks.get(a) or {}
            # Tie on the best score => every tied row is starred. Starring only
            # the one that happened to sort first would invent a ranking between
            # three companies that scored identically.
            _sc = _score_or_none(r[a])
            is_best = (info.get("n", 0) > 1 and _sc is not None
                       and _sc == info.get("best_score"))
            axis_cells.append(_cell(
                _sc, tone_fn, best=is_best,
                title=(f"best {fscore.AXIS_LABELS[a]} in this peer group"
                       if is_best else "")))

        rows_html.append(
            f'<tr style="background:{tint};">'
            f'<td class="tb-peer-stick" style="background:{tint};">'
            f'{name}{" &#9666; analysed" if is_anchor else ""}'
            f'<div style="font-size:9.5px;color:{t["text_muted"]};">'
            f'{(r["name"] or "")[:34]}</div></td>'
            + "".join(axis_cells)
            + f'<td style="font-size:10.5px;white-space:nowrap;">{r["business"] or rs.NA}</td>'
            f'<td style="font-size:10.5px;white-space:nowrap;">{r["entry"] or rs.NA}</td>'
            f'<td style="text-align:right;font-size:10.5px;'
            f'color:{rs.tone_colors(cov_tone)[0]};">{cov}</td>'
            + "".join(_tech_cell(r.get(c), c) for c, _l, _d in tech_cols)
            + '</tr>'
        )

    median_row = (
        f'<tr style="border-top:2px solid {t["border_strong"]};">'
        f'<td class="tb-peer-stick" style="background:{t["surface_alt"]};'
        f'font-style:italic;">Peer median<div style="font-size:9.5px;'
        f'color:{t["text_muted"]};">excludes {anchor}</div></td>'
        + "".join(f'<td style="text-align:right;" class="tb-mono">'
                  f'<span style="font-size:11px;color:{t["text_body"]};">'
                  f'{"&ndash;" if (median or {}).get(a) is None else median[a]}'
                  f'</span></td>' for a in fscore.AXES)
        + f'<td colspan="{3 + len(tech_cols)}"></td></tr>'
    )

    return f'''<style>
.tb-peer-wrap {{ max-height:520px; overflow:auto; border:1px solid {t["border"]};
  border-radius:8px; }}
.tb-peer {{ border-collapse:separate; border-spacing:0; width:100%;
  font-size:11.5px; color:{t["text"]}; }}
.tb-peer th {{ position:sticky; top:22px; z-index:3; background:{t["surface_alt"]};
  font-size:10px; text-transform:uppercase; letter-spacing:.04em; padding:6px 8px;
  border-bottom:1px solid {t["border_strong"]}; }}
.tb-peer .tb-peer-grp th {{ top:0; z-index:3; height:22px; padding:2px 8px;
  font-size:9px; letter-spacing:.06em; color:{t["text_muted"]};
  background:{t["surface"]}; border-bottom:1px solid {t["border"]};
  text-transform:uppercase; font-weight:600; text-align:left; }}
.tb-peer td {{ padding:4px 8px; height:36px;
  border-bottom:1px solid {t["border"]}; }}
.tb-peer-stick {{ position:sticky; left:0; z-index:2; text-align:left;
  box-shadow:2px 0 4px -2px rgba(0,0,0,.18); }}
.tb-peer th:first-child {{ position:sticky; left:0; z-index:4;
  box-shadow:2px 0 4px -2px rgba(0,0,0,.18); }}
</style>
<div class="tb-peer-wrap"><table class="tb-peer">
<thead>{group_head}<tr><th style="text-align:left;">Stock</th>{heads}
<th style="text-align:left;">Business</th><th style="text-align:left;">Entry</th>
<th style="text-align:right;">Cov.</th>{tech_heads}</tr></thead>
<tbody>{"".join(rows_html)}{median_row}</tbody></table></div>'''


def _lobby_fallback(anchor: str, res: dict) -> dict:
    """The Sector Lobby's rungs after this module's own: yfinance industry
    across NSE sectors, then screener.in's NSE basic industry. Handed the
    first-rung result so it is not resolved twice. No lobby overrides: the
    analyzer's first rung never applied them either."""
    import sector_lobby as sl
    return sl.lobby_members(anchor, resolve=lambda a, **k: res, overrides={})


def _climb_ladder(res: dict, lobby: Callable[[str, dict], dict],
                  max_peers: int) -> dict:
    """Fill `res` from the lobby ladder when the first rung found no group.

    Measured 2026-10-25 on a scanner run + watchlist (105 names): 53 failed the
    first rung outright because they are not in the NIFTY-500 / Total-Market
    files, and screener.in's basic-industry listing gave 4+ NSE peers for every
    one of the 10 checked. The lobby already climbed these rungs; the analyzer
    stopping at the first one was why the two pages disagreed about peers.
    """
    a = res["anchor"]
    try:
        lob = lobby(a, res) or {}
    except Exception as exc:                 # a scrape failure is a thin group
        _log.warning("peer_comparison: ladder failed for %s: %s", a, exc)
        lob = {}
    peers = [p for p in lob.get("members") or [] if p != a]
    if not lob.get("ok") or len(peers) < MIN_PEERS:
        res["reason"] = ((res.get("reason") or "") + " The wider search — the same "
                         "yfinance industry across every NSE sector, then NSE's basic "
                         "industry via screener.in — found no group either.").strip()
        return res
    tags = lob.get("tags") or {}
    peers.sort(key=lambda s: (tags.get(s, {}).get("market_cap_cr") or -1), reverse=True)
    res.update({
        "ok": True, "reason": None, "tags": tags, "peers": peers[:max_peers],
        "n_in_group": len(peers), "group_label": lob.get("label"),
        "group_level": lob.get("level"),
        "macro_sector": lob.get("macro_sector") or res.get("macro_sector"),
        "source": ("screener.in" if lob.get("source") == "screener.in"
                   else "yfinance-cross-sector"),
    })
    if res["source"] != "screener.in":
        res["industry"] = (tags.get(a) or {}).get("industry") or res.get("industry")
    return res


def source_label(res: dict) -> str:
    """One line for the page: where this peer group came from."""
    src, label = res.get("source"), res.get("group_label")
    if src == "screener.in":
        return (f"NSE basic industry <b>{label}</b>, via screener.in "
                f"({res.get('macro_sector') or 'NSE classification'})")
    if src == "yfinance-cross-sector":
        rung = "industry" if res.get("group_level") == "industry" else "industry family"
        return (f"yfinance {rung} <b>{label}</b>, searched across NSE sectors "
                f"({res.get('macro_sector') or 'several sectors'})")
    return f"yfinance industry <b>{label}</b>, within NSE sector {res.get('macro_sector')}"


def build(anchor: str, score_fn: Callable[[str], dict], *,
          max_peers: int = MAX_PEERS,
          tag_progress: Callable[[int, int], None] | None = None,
          score_progress: Callable[[int, int], None] | None = None,
          lobby: Callable[[str, dict], dict] | None = None) -> dict[str, Any]:
    """resolve_peers → (lobby ladder) → score_peer_group → median, as one call
    for the page. `res["source"]` says which rung produced the group."""
    anchor = (anchor or "").strip().upper()
    res = resolve_peers(anchor, max_peers=max_peers, progress_cb=tag_progress)
    res["anchor"], res["source"] = anchor, "yfinance"
    if not res["ok"]:
        res = _climb_ladder(res, lobby or _lobby_fallback, max_peers)
    if not res["ok"]:
        res["table"], res["median"], res["ranks"] = None, None, None
        return res
    df = score_peer_group(anchor, res["peers"], score_fn,
                          tags=res.get("tags"), progress_cb=score_progress)
    res["table"], res["median"] = df, peer_median(df)
    res["ranks"] = rank_report(df, anchor)
    return res


if __name__ == "__main__":      # py -3 tools/peer_comparison.py TITAN
    import sys
    sys.path.insert(0, str(HERE))
    import stock_council as council
    import fundamentals_deep as fdeep

    def _score(sym: str) -> dict:
        return fscore.score_all(council.fetch_fundamentals(sym),
                                fdeep.derive_fundamentals(sym))

    for anchor in (sys.argv[1:] or ["TITAN"]):
        r = build(anchor, _score,
                  tag_progress=lambda d, t: print(f"\r  tagging {d}/{t}", end=""),
                  score_progress=lambda d, t: print(f"\r  scoring {d}/{t}", end=""))
        print(f"\n=== {anchor} ===")
        print(f"  macro sector : {r['macro_sector']}  (pool {r['pool_size']}, tagged {r['tagged']})")
        print(f"  industry     : {r['industry']}  ({r['n_same_industry']} same-industry names)")
        if not r["ok"]:
            print("  NO PEER GROUP:", r["reason"])
            continue
        df = r["table"]
        cols = ["symbol", "is_anchor", "market_cap_cr", *fscore.AXES,
                "business", "entry", "coverage_have", "coverage_total"]
        print(df[cols].to_string(index=False))
        print("  peer median:", r["median"])
