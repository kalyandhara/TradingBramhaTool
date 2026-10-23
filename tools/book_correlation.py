#!/usr/bin/env python3
"""book_correlation.py — which names in a list move as one? (B-173)

From the LuxAlgo Machine Learning gap analysis (Correlation Clusters): the desk
reported sector exposure and nothing else, so five holdings in five different
sectors that all trade like one rate-sensitive bet looked diversified. This
reports the part sector labels miss.

── What it computes ───────────────────────────────────────────────────────────
* **Correlation** of daily log returns over the last ``window`` sessions
  (default 120), pairwise, on the dates both names traded. A pair with fewer
  than ``min_overlap`` shared sessions is left blank rather than guessed.
* **Clusters**: average-linkage hierarchical clustering on distance 1 − ρ, cut
  at ``cut_rho`` (default ρ ≥ 0.6 → distance 0.4). A name in no cluster with
  anyone is a singleton, and singletons are the independent part of the list.
* **Effective number of independent bets**, two readings:
    - ``n_eff`` — unweighted participation ratio of the correlation matrix's
      eigenvalues, (Σλ)² / Σλ². N for N uncorrelated names, 1 for N clones.
    - ``n_eff_weighted`` — 1 / (wᵀ R w) with w the position weights (summing to
      1). Equals N for N equal, uncorrelated positions; it falls as weight piles
      onto correlated names. Only meaningful for a book with weights.

── What it is NOT ─────────────────────────────────────────────────────────────
A description of co-movement over one past window, not a forecast. Correlations
rise in sell-offs, which is exactly when they matter, and a 120-day window from
a calm tape will understate that. Nothing here votes, scores or sizes.

Pure: closes in, numbers out. scipy for the clustering (already installed).
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

WINDOW = 120
MIN_OVERLAP = 60
CUT_RHO = 0.6


def returns_frame(closes: dict[str, pd.Series], window: int = WINDOW) -> pd.DataFrame:
    """Daily log returns, one column per symbol, last ``window`` sessions of the
    union calendar. Each series must be indexed by date."""
    cols = {}
    for sym, s in closes.items():
        if s is None or len(s) < 3:
            continue
        s = pd.Series(s).astype(float)
        s.index = pd.DatetimeIndex(pd.to_datetime(s.index)).tz_localize(None).normalize()
        s = s[~s.index.duplicated(keep="last")].sort_index()
        cols[sym] = np.log(s).diff()
    if not cols:
        return pd.DataFrame()
    r = pd.DataFrame(cols).sort_index()
    return r.iloc[-window:]


def correlation(rets: pd.DataFrame, min_overlap: int = MIN_OVERLAP) -> pd.DataFrame:
    return rets.corr(min_periods=min_overlap)


def clusters(corr: pd.DataFrame, cut_rho: float = CUT_RHO) -> list[list[str]]:
    """Groups of names whose average-linkage correlation clears ``cut_rho``,
    largest first; singletons last. Names with no usable correlation to anyone
    are returned as singletons."""
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import squareform

    names = list(corr.columns)
    if len(names) < 2:
        return [[n] for n in names]
    d = (1.0 - corr.fillna(0.0)).clip(lower=0.0).to_numpy(copy=True)
    np.fill_diagonal(d, 0.0)
    d = (d + d.T) / 2
    labels = fcluster(linkage(squareform(d, checks=False), method="average"),
                      t=1.0 - cut_rho, criterion="distance")
    groups: dict[int, list[str]] = {}
    for n, lab in zip(names, labels):
        groups.setdefault(int(lab), []).append(n)
    return sorted(groups.values(), key=lambda g: (-len(g), g))


def n_eff(corr: pd.DataFrame) -> float | None:
    """Participation ratio of the eigenvalues; blanks read as 0 correlation."""
    if corr.shape[0] == 0:
        return None
    r = corr.fillna(0.0).to_numpy(copy=True)
    np.fill_diagonal(r, 1.0)
    lam = np.clip(np.linalg.eigvalsh((r + r.T) / 2), 0, None)
    return float(lam.sum() ** 2 / (lam ** 2).sum()) if lam.sum() > 0 else None


def n_eff_weighted(corr: pd.DataFrame, weights: dict[str, float]) -> float | None:
    names = [n for n in corr.columns if weights.get(n, 0) > 0]
    if not names:
        return None
    w = np.array([weights[n] for n in names], dtype=float)
    w = w / w.sum()
    r = corr.loc[names, names].fillna(0.0).to_numpy(copy=True)
    np.fill_diagonal(r, 1.0)
    q = float(w @ r @ w)
    return 1.0 / q if q > 0 else None


def analyse(closes: dict[str, pd.Series], weights: dict[str, float] | None = None,
            window: int = WINDOW, cut_rho: float = CUT_RHO) -> dict[str, Any]:
    """Everything a page needs. ``weights`` optional (notional per symbol)."""
    rets = returns_frame(closes, window)
    corr = correlation(rets)
    usable = [c for c in corr.columns if corr[c].drop(c).notna().any()]
    corr = corr.loc[usable, usable]
    groups = clusters(corr, cut_rho)
    multi = [g for g in groups if len(g) > 1]
    rows = []
    for g in multi:
        sub = corr.loc[g, g].to_numpy(copy=True)
        iu = np.triu_indices(len(g), 1)
        rows.append({"names": ", ".join(g), "size": len(g),
                     "avg_rho": round(float(np.nanmean(sub[iu])), 2)})
    pairs = []
    cols = list(corr.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            v = corr.iat[i, j]
            if pd.notna(v):
                pairs.append((cols[i], cols[j], round(float(v), 2)))
    pairs.sort(key=lambda p: -p[2])
    return {
        "n": len(usable),
        "window": window, "cut_rho": cut_rho,
        "n_eff": round(n_eff(corr), 1) if len(usable) else None,
        "n_eff_weighted": (round(n_eff_weighted(corr, weights), 1)
                           if weights and len(usable) else None),
        "clusters": rows,
        "singletons": [g[0] for g in groups if len(g) == 1],
        "top_pairs": pairs[:5],
        "dropped": sorted(set(closes) - set(usable)),
    }


def summary_line(a: dict[str, Any]) -> str:
    """One sentence for the page, saying the number and what it is."""
    if not a.get("n"):
        return "Correlation: not enough overlapping history."
    s = (f"**{a['n']} names behave like ~{a['n_eff']} independent bets** "
         f"(daily returns, last {a['window']} sessions)")
    if a.get("n_eff_weighted") is not None:
        s += f"; weighted by position size, **~{a['n_eff_weighted']}**"
    s += (f". {len(a['clusters'])} group(s) move together at ρ ≥ {a['cut_rho']}"
          if a["clusters"] else f". No pair moves together at ρ ≥ {a['cut_rho']}")
    return s + ". Past co-movement, not a forecast — correlations rise in sell-offs."


def closes_from(symbols, fetch) -> dict[str, pd.Series]:
    """``fetch(symbol)`` -> daily bars with a ``date`` column or DatetimeIndex."""
    out = {}
    for s in symbols:
        try:
            df = fetch(s)
        except Exception:                    # one bad name, not the block
            df = None
        if df is None or getattr(df, "empty", True) or "close" not in df.columns:
            continue
        idx = pd.to_datetime(df["date"]) if "date" in df.columns else df.index
        out[s] = pd.Series(df["close"].to_numpy(dtype=float), index=idx)
    return out


def render(st, symbols, fetch, weights: dict[str, float] | None = None,
           key: str = "corr") -> None:
    """The page block: one summary line, then the groups and strongest pairs in
    an expander. Plain Streamlit elements only — no raw HTML on the page."""
    if len(list(symbols)) < 2:
        return
    a = analyse(closes_from(symbols, fetch), weights=weights)
    st.caption(summary_line(a))
    with st.expander("Correlation groups and strongest pairs", expanded=False):
        if a["clusters"]:
            st.dataframe(pd.DataFrame(a["clusters"]).rename(columns={
                "names": "Moves together", "size": "Names", "avg_rho": "Avg ρ"}),
                hide_index=True, key=f"{key}_groups")
        st.dataframe(pd.DataFrame(a["top_pairs"], columns=["A", "B", "ρ"]),
                     hide_index=True, key=f"{key}_pairs")
        if a["dropped"]:
            st.caption(f"Not enough shared history ({MIN_OVERLAP}+ sessions): "
                       f"{', '.join(a['dropped'])}.")
