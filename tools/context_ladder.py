"""B-187 — context ladder for the Stock Analyzer.

Market (NIFTY 50) → NSE sector index rungs, each with a trend word and 1D / 1M
change, plus one attribution line: was the stock's month the stock, its sector
or the market? Descriptive context, not a signal — nothing here is measured
against forward returns.

Idea from the eVector review ([[sources/Web-eVector-Event-Vector-Markets]]).
The thematic-index rung of the original sketch is not here: the
`sector_index_data` snapshot carries only the 11 sector indices, and a rung we
would have to guess is left out rather than invented.
"""
from __future__ import annotations

import pandas as pd

SMA_BARS = 20
SLOPE_BARS = 5        # the average "rising" = above its value 5 bars ago
MONTH_BARS = 21
MIXED_RATIO = 0.75    # runner-up within 75 % of the leader → "mixed"


def _close(obj) -> pd.Series | None:
    """A close series from a Series or a frame with `close` or `Close`."""
    if obj is None:
        return None
    if isinstance(obj, pd.DataFrame):
        col = "close" if "close" in obj.columns else "Close" if "Close" in obj.columns else None
        if col is None:
            return None
        obj = obj[col]
    s = pd.to_numeric(obj, errors="coerce").dropna()
    return s if len(s) else None


def trend_word(close) -> str | None:
    """Up: close above a rising 20-day average. Down: below a falling one.
    Mixed: anything else. None when there are too few bars."""
    s = _close(close)
    if s is None or len(s) < SMA_BARS + SLOPE_BARS:
        return None
    sma = s.rolling(SMA_BARS).mean()
    above = s.iloc[-1] > sma.iloc[-1]
    rising = sma.iloc[-1] > sma.iloc[-1 - SLOPE_BARS]
    if above and rising:
        return "Up"
    if not above and not rising:
        return "Down"
    return "Mixed"


def pct_change(close, bars: int) -> float | None:
    s = _close(close)
    if s is None or len(s) <= bars:
        return None
    return float((s.iloc[-1] / s.iloc[-1 - bars] - 1) * 100)


def attribution(stock: float | None, sector: float | None,
                market: float | None) -> tuple[str | None, str]:
    """Split the stock's move into stock-specific (stock − sector), sector
    (sector − market) and market parts; the largest names the verdict."""
    if stock is None or market is None:
        return None, "Not enough history to split the move."
    if sector is None:
        parts = {"mostly the stock": stock - market, "mostly the market": market}
        head = (f"Stock {stock:+.1f} % · market {market:+.1f} % "
                f"(sector index unknown)")
    else:
        parts = {"mostly the stock": stock - sector,
                 "mostly the sector": sector - market,
                 "mostly the market": market}
        head = f"Stock {stock:+.1f} % · sector {sector:+.1f} % · market {market:+.1f} %"
    ranked = sorted(parts.items(), key=lambda kv: abs(kv[1]), reverse=True)
    (lead, lv), (_, rv) = ranked[0], ranked[1]
    verdict = "mixed" if abs(rv) >= MIXED_RATIO * abs(lv) else lead
    detail = {"mostly the stock": f" ({lv:+.1f} pp over its {'sector' if sector is not None else 'market'})",
              "mostly the sector": f" (sector {lv:+.1f} pp over the market)",
              "mostly the market": "",
              "mixed": ""}[verdict]
    return verdict, f"{head} → {verdict}{detail}"


def sector_for(symbol: str, industry_map: dict[str, str]) -> tuple[str | None, str | None]:
    """(sector index ticker, NSE sector label) from the NIFTY 500 sector map.
    Off-index names give (None, None); unmapped sectors give (None, label)."""
    import nse_universe as nseu
    label = industry_map.get(symbol)
    return (nseu.index_for_sector(label) if label else None), label


def _rung(name: str, label: str, close) -> dict:
    s = _close(close)
    return {"rung": name, "label": label, "missing": s is None,
            "trend": trend_word(s), "d1": pct_change(s, 1),
            "m1": pct_change(s, MONTH_BARS)}


def build_ladder(stock, market, sector, *, sector_label: str | None,
                 sector_ticker: str | None) -> dict:
    rungs = [_rung("Market", "NIFTY 50", market)]
    if sector_ticker or sector_label:
        rungs.append(_rung("Sector", sector_label or sector_ticker, sector))
    sec = rungs[1] if len(rungs) > 1 else None
    verdict, text = attribution(pct_change(stock, MONTH_BARS),
                                sec["m1"] if sec else None, rungs[0]["m1"])
    return {"rungs": rungs, "verdict": verdict, "text": text}
