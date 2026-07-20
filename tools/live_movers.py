"""
live_movers.py — Intraday top-movers feed for the quadrant dashboard.

Pipeline:
  1. fetch_intraday_movers(universe) → DataFrame of %change, volume, RS
  2. compute_ai_score(row)           → 0–100 composite (RS + trend + momentum + vol)
  3. classify_quadrant(row)          → Top / Potential / Growth / Volatile
  4. snapshot_movers()               → parquet cache under data/movers/

Intentionally lean. Real-time feed can be swapped in later by replacing
`_fetch_one` with a broker WebSocket call.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "movers"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
WIKI_LOG = ROOT / "trading-wiki" / "wiki" / "log.md"
WIKI_ENTITIES = ROOT / "trading-wiki" / "wiki" / "entities"

_CORE_UNIVERSE: list[str] = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "MARUTI.NS", "SUNPHARMA.NS", "TITAN.NS",
    "ULTRACEMCO.NS", "WIPRO.NS", "NESTLEIND.NS", "ASIANPAINT.NS", "BAJFINANCE.NS",
    "NUVOCO.NS", "GABRIEL.NS", "AEGISLOG.NS", "LTTS.NS", "GROWW.NS",
]


def _load_wiki_symbols() -> list[str]:
    """Every entity page in the wiki is a candidate ticker. Free universe expansion."""
    if not WIKI_ENTITIES.exists():
        return []
    syms = []
    for f in WIKI_ENTITIES.glob("*.md"):
        name = f.stem.upper()
        # Skip people/pages that aren't tickers (contain hyphens or lowercase)
        if "-" in name or not name.isalnum():
            continue
        syms.append(f"{name}.NS")
    return syms


DEFAULT_UNIVERSE: list[str] = sorted(set(_CORE_UNIVERSE + _load_wiki_symbols()))

BENCHMARK = "^CRSLDX"   # Nifty 500 TR index proxy; falls back to ^NSEI


# ── Fetch ─────────────────────────────────────────────────────────────────────

def _fetch_one(symbol: str) -> dict | None:
    """Pull today's OHLCV + prior close for a single symbol via yfinance."""
    try:
        import yfinance as yf
        t = yf.Ticker(symbol)
        fi = t.fast_info
        last = float(fi.get("lastPrice") or 0)
        prev = float(fi.get("previousClose") or 0)
        if not last or not prev:
            return None
        vol = float(fi.get("lastVolume") or 0)
        # 20-day avg volume for surge ratio
        hist = t.history(period="30d", interval="1d", auto_adjust=True)
        avg_vol = float(hist["Volume"].tail(20).mean()) if not hist.empty else 0.0
        pct = (last - prev) / prev * 100.0
        vol_surge = (vol / avg_vol) if avg_vol > 0 else 0.0
        # 52-week RS proxy: price vs 252-day median
        hist_1y = t.history(period="1y", interval="1d", auto_adjust=True)
        rs = 0.0
        if len(hist_1y) > 50:
            median = float(hist_1y["Close"].median())
            rs = (last / median - 1.0) * 100.0
        return {
            "symbol": symbol.replace(".NS", ""),
            "last": last,
            "prev": prev,
            "pct_change": pct,
            "volume": vol,
            "avg_vol_20d": avg_vol,
            "vol_surge": vol_surge,
            "rs_1y": rs,
        }
    except Exception as e:
        log.debug("fetch failed %s: %s", symbol, e)
        return None


def fetch_intraday_movers(universe: list[str] | None = None,
                          max_workers: int = 8) -> pd.DataFrame:
    """Parallel fetch %change / volume / RS for the universe."""
    syms = universe or DEFAULT_UNIVERSE
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_fetch_one, s): s for s in syms}
        for f in as_completed(futs):
            r = f.result()
            if r:
                rows.append(r)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["ai_score"] = df.apply(compute_ai_score, axis=1)
    df["quadrant"] = df.apply(classify_quadrant, axis=1)
    df["fetched_at"] = datetime.utcnow()
    return df.sort_values("ai_score", ascending=False).reset_index(drop=True)


# ── Scoring ───────────────────────────────────────────────────────────────────

def compute_ai_score(row: pd.Series) -> float:
    """Composite 0–100 score. Weights: RS 40%, momentum 30%, vol-surge 30%.

    Simple linear blend — tune once you have backtest data.
    """
    rs = _clip(row.get("rs_1y", 0.0), -50, 100)      # -50%..+100% → 0..1
    rs_n = (rs + 50) / 150.0

    mom = _clip(row.get("pct_change", 0.0), -10, 15)  # -10%..+15% → 0..1
    mom_n = (mom + 10) / 25.0

    vs = _clip(row.get("vol_surge", 0.0), 0, 5)       # 0x..5x → 0..1
    vs_n = vs / 5.0

    score = (0.4 * rs_n + 0.3 * mom_n + 0.3 * vs_n) * 100.0
    return round(float(score), 1)


def classify_quadrant(row: pd.Series,
                      score_split: float = 50.0,
                      growth_split: float = 6.0) -> str:
    """Four-way split on AI-Score × %change."""
    s = row.get("ai_score", 0.0)
    g = row.get("pct_change", 0.0)
    if s >= score_split and g >= growth_split:
        return "Top"
    if s >= score_split and g < growth_split:
        return "Potential"
    if s < score_split and g >= growth_split:
        return "Volatile"
    return "Growth"


def _clip(x: float, lo: float, hi: float) -> float:
    try:
        return max(lo, min(hi, float(x)))
    except (TypeError, ValueError):
        return lo


# ── Snapshot ──────────────────────────────────────────────────────────────────

def snapshot_movers(df: pd.DataFrame) -> Path | None:
    """Append a snapshot to today's parquet file. Returns path."""
    if df is None or df.empty:
        return None
    day = datetime.utcnow().strftime("%Y-%m-%d")
    path = CACHE_DIR / f"{day}.parquet"
    if path.exists():
        try:
            existing = pd.read_parquet(path)
            df = pd.concat([existing, df], ignore_index=True)
        except Exception as e:
            log.warning("snapshot append failed, overwriting: %s", e)
    df.to_parquet(path, index=False)
    return path


# ── EOD summary → wiki log + PNG ──────────────────────────────────────────────

def write_eod_snapshot(df: pd.DataFrame | None = None) -> dict:
    """End-of-day: render quadrant PNG + append a markdown summary to wiki/log.md."""
    if df is None or df.empty:
        df = fetch_intraday_movers()
    if df is None or df.empty:
        return {"ok": False, "reason": "no data"}

    day = datetime.now().strftime("%Y-%m-%d")
    png_path = CACHE_DIR / f"{day}.png"

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        colours = {"Top": "#8B4513", "Potential": "#1f77b4",
                   "Volatile": "#e74c3c", "Growth": "#c9d648"}
        fig, ax = plt.subplots(figsize=(10, 7))
        for q, sub in df.groupby("quadrant"):
            ax.scatter(sub["ai_score"], sub["pct_change"],
                       s=(sub["vol_surge"].clip(0.5, 5) * 40),
                       c=colours.get(q, "#888"), label=q, edgecolors="#333", alpha=0.8)
            for _, r in sub.iterrows():
                ax.annotate(r["symbol"], (r["ai_score"], r["pct_change"]),
                            fontsize=7, ha="center", va="bottom")
        ax.axvline(50, ls=":", c="#aaa"); ax.axhline(6, ls=":", c="#aaa")
        ax.set_xlabel("AI-Score"); ax.set_ylabel("Growth % (today)")
        ax.set_title(f"Top Movers — {day}")
        ax.legend(loc="best", fontsize=8)
        fig.tight_layout(); fig.savefig(png_path, dpi=110); plt.close(fig)
    except Exception as e:
        log.warning("PNG render failed: %s", e)

    # Wiki log append (markdown)
    top5 = df.head(5)
    lines = [f"\n## {day} — Live Movers EOD\n",
             f"- Symbols scanned: **{len(df)}**  ·  Snapshot: `{png_path.name}`\n",
             "- Top 5 by AI-Score:\n"]
    for _, r in top5.iterrows():
        lines.append(f"  - **{r['symbol']}** · AI {r['ai_score']} · Δ {r['pct_change']:+.2f}%"
                     f" · Vol× {r['vol_surge']:.1f} · [[{r['symbol']}]] ({r['quadrant']})\n")
    try:
        if WIKI_LOG.exists():
            with WIKI_LOG.open("a", encoding="utf-8") as f:
                f.writelines(lines)
    except Exception as e:
        log.warning("wiki log append failed: %s", e)

    return {"ok": True, "png": str(png_path), "rows": len(df)}


# ── Quadrant-crossing detector (for alerts) ───────────────────────────────────

def detect_quadrant_crossings(prev: pd.DataFrame, curr: pd.DataFrame) -> pd.DataFrame:
    """Return rows where a symbol crossed *into* the 'Top' quadrant since prev snapshot."""
    if prev is None or prev.empty or curr is None or curr.empty:
        return pd.DataFrame()
    merged = curr.merge(prev[["symbol", "quadrant"]].rename(
        columns={"quadrant": "prev_quadrant"}), on="symbol", how="left")
    crossings = merged[(merged["quadrant"] == "Top") &
                       (merged["prev_quadrant"] != "Top")]
    return crossings[["symbol", "prev_quadrant", "quadrant",
                      "ai_score", "pct_change", "vol_surge"]]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = fetch_intraday_movers()
    if df.empty:
        print("No data (market closed or feed unavailable).")
    else:
        print(df[["symbol", "pct_change", "vol_surge", "rs_1y",
                  "ai_score", "quadrant"]].to_string(index=False))
        p = snapshot_movers(df)
        print(f"\nSnapshot: {p}")
