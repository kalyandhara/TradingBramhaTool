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


def _cell(score: int | None, tone_fn: Callable[[int | None], str]) -> str:
    """One axis cell: an in-cell bar carrying magnitude, tinted by tone.

    A bar rather than a bare heat tint, deliberately — tint alone puts the whole
    reading in hue, which fails for a colour-blind reader and turns a twelve-column
    table into a wash. The bar survives both.
    """
    import report_style as rs
    if score is None:
        return (f'<td style="text-align:right;color:{rs.TOKENS["absent"]};'
                f'font-size:10px;">n/a</td>')
    fg, bg = rs.tone_colors(tone_fn(score))
    return (f'<td style="text-align:right;padding:2px 8px;">'
            f'<div style="position:relative;height:18px;background:{bg};'
            f'border-radius:3px;overflow:hidden;">'
            f'<div style="position:absolute;left:0;top:0;bottom:0;width:{score}%;'
            f'background:{fg};opacity:.30;"></div>'
            f'<div class="tb-mono" style="position:relative;text-align:right;'
            f'padding-right:5px;line-height:18px;font-size:11px;color:{fg};'
            f'font-weight:600;">{score}</div></div></td>')


def table_html(df: pd.DataFrame, median: dict[str, float | None], anchor: str,
               *, tone_fn: Callable[[int | None], str] | None = None) -> str:
    """The peer table as standalone HTML.

    Layout follows current data-table practice for a wide comparison grid: sticky
    header, frozen identifier column (with the shadow that makes it read as a
    layer rather than a seam), z-order header > frozen column > body so nothing
    bleeds through at the intersection, dense 36px rows, numbers right-aligned.
    """
    import report_style as rs
    tone_fn = tone_fn or _default_tone
    t = rs.TOKENS

    heads = "".join(f'<th style="text-align:right;white-space:nowrap;">'
                    f'{a.replace("_", " ").title()}</th>' for a in fscore.AXES)

    rows_html = []
    for _, r in df.iterrows():
        is_anchor = bool(r["is_anchor"])
        tint = t["surface_warm"] if is_anchor else t["surface"]
        name = f'<b>{r["symbol"]}</b>' if is_anchor else r["symbol"]
        cov = f'{r["coverage_have"]}/{r["coverage_total"]}' if r["coverage_total"] else rs.NA
        cov_tone = ("good" if r["coverage_total"]
                    and r["coverage_have"] / r["coverage_total"] >= 0.8 else "warn")
        rows_html.append(
            f'<tr style="background:{tint};">'
            f'<td class="tb-peer-stick" style="background:{tint};">'
            f'{name}{" &#9666; analysed" if is_anchor else ""}'
            f'<div style="font-size:9.5px;color:{t["text_muted"]};">'
            f'{(r["name"] or "")[:34]}</div></td>'
            + "".join(_cell(_score_or_none(r[a]), tone_fn) for a in fscore.AXES)
            + f'<td style="font-size:10.5px;white-space:nowrap;">{r["business"] or rs.NA}</td>'
            f'<td style="font-size:10.5px;white-space:nowrap;">{r["entry"] or rs.NA}</td>'
            f'<td style="text-align:right;font-size:10.5px;'
            f'color:{rs.tone_colors(cov_tone)[0]};">{cov}</td></tr>'
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
        + '<td colspan="3"></td></tr>'
    )

    return f'''<style>
.tb-peer-wrap {{ max-height:520px; overflow:auto; border:1px solid {t["border"]};
  border-radius:8px; }}
.tb-peer {{ border-collapse:separate; border-spacing:0; width:100%;
  font-size:11.5px; color:{t["text"]}; }}
.tb-peer th {{ position:sticky; top:0; z-index:3; background:{t["surface_alt"]};
  font-size:10px; text-transform:uppercase; letter-spacing:.04em; padding:6px 8px;
  border-bottom:1px solid {t["border_strong"]}; }}
.tb-peer td {{ padding:4px 8px; height:36px;
  border-bottom:1px solid {t["border"]}; }}
.tb-peer-stick {{ position:sticky; left:0; z-index:2; text-align:left;
  box-shadow:2px 0 4px -2px rgba(0,0,0,.18); }}
.tb-peer th:first-child {{ position:sticky; left:0; z-index:4;
  box-shadow:2px 0 4px -2px rgba(0,0,0,.18); }}
</style>
<div class="tb-peer-wrap"><table class="tb-peer">
<thead><tr><th style="text-align:left;">Stock</th>{heads}
<th style="text-align:left;">Business</th><th style="text-align:left;">Entry</th>
<th style="text-align:right;">Cov.</th></tr></thead>
<tbody>{"".join(rows_html)}{median_row}</tbody></table></div>'''


def build(anchor: str, score_fn: Callable[[str], dict], *,
          max_peers: int = MAX_PEERS,
          tag_progress: Callable[[int, int], None] | None = None,
          score_progress: Callable[[int, int], None] | None = None) -> dict[str, Any]:
    """resolve_peers → score_peer_group → median, as one call for the page."""
    res = resolve_peers(anchor, max_peers=max_peers, progress_cb=tag_progress)
    if not res["ok"]:
        res["table"], res["median"] = None, None
        return res
    df = score_peer_group(anchor, res["peers"], score_fn,
                          tags=res.get("tags"), progress_cb=score_progress)
    res["table"], res["median"] = df, peer_median(df)
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
