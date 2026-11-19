#!/usr/bin/env python3
"""
stock_council.py
Deterministic 3-perspective stock analysis "council" — no LLM, no API cost.

Pipeline:
    gather_evidence(df, nifty_df, fundamentals)  -> EvidenceBundle  (facts + 0-100 sub-scores)
        │
    bull_case(bundle)   -> Thesis   (supportive pillars, weighted)
    bear_case(bundle)   -> Thesis   (risk pillars, weighted, risk-of-ruin bias)
        │
    judge(bundle, bull, bear, regime) -> TradeCard  (verdict + entry/stop/target/size)

Every number traces to a rule in this file — auditable by design. Reuses the
existing screener_pipeline scorers and the `ta` indicators already in the repo.

Fundamentals are optional: pass a dict from fetch_fundamentals() (yfinance .info,
no login) or leave None to run technical-only. screener.in enrichment can be
layered in later via the same dict shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from ta.momentum import RSIIndicator
from ta.trend import ADXIndicator, MACD
from ta.volatility import AverageTrueRange

import screener_pipeline as sp
import scanner_templates as sc
import volume_profile as vp
import cpr_vp
import position_sizing as ps


# ──────────────────────────────────────────────────────────────────────────────
# Tunable weights — edit here to reshape how much each pillar moves the verdict.
# Bull and Bear pillars each contribute (pillar_score/100 * weight). Net drives
# the verdict thresholds in judge().
# ──────────────────────────────────────────────────────────────────────────────
BULL_WEIGHTS = {
    "trend":       25,   # EMA stack, stage, Minervini template
    "momentum":    20,   # RSI/MACD/ADX, RS vs Nifty
    "structure":   15,   # near 52w high, emerged from base
    "volume":      10,   # accumulation, breakout volume
    "quality":     15,   # ROE/ROCE/OPM/low debt
    "growth":      15,   # sales/earnings growth, reasonable PEG
}
BEAR_WEIGHTS = {
    "overextension": 20,  # RSI>75, far above 200EMA, climax
    "trend_break":   25,  # stage 3/4, below key MAs, RS rolling over
    "distribution":  15,  # volume drying / distribution days
    "fundamental":   20,  # high debt, poor margins, rich valuation
    "liquidity":     10,  # thin turnover
    "regime":        10,  # hostile market regime for longs
}

# Verdict thresholds on the regime-adjusted net score (bull_total - bear_total),
# expressed on a roughly -100..+100 scale.
BUY_THRESHOLD   = 25
AVOID_THRESHOLD = -10

# % of total capital risked per trade (for sizing). Owned by position_sizing so the
# council, portfolio_sim and the chart's risk box read one number; kept as a name
# here because callers cite `council.RISK_PER_TRADE_PCT`.
RISK_PER_TRADE_PCT = ps.RISK_PER_TRADE_PCT
ATR_STOP_MULT      = 1.5   # stop = entry - mult * ATR (fallback when no swing low)


# ──────────────────────────────────────────────────────────────────────────────
# Data structures
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class EvidenceBundle:
    symbol: str
    facts: dict[str, Any] = field(default_factory=dict)      # raw values
    subscores: dict[str, float] = field(default_factory=dict)  # 0-100 normalized
    notes: dict[str, str] = field(default_factory=dict)      # human-readable per key
    has_fundamentals: bool = False


@dataclass
class Pillar:
    name: str
    score: float            # 0-100
    weight: float
    reason: str

    @property
    def contribution(self) -> float:
        return self.score / 100.0 * self.weight


@dataclass
class Thesis:
    side: str               # "BULL" | "BEAR"
    pillars: list[Pillar]
    breakers: list[str]     # hard thesis-breakers found

    @property
    def total(self) -> float:
        return sum(p.contribution for p in self.pillars)

    @property
    def conviction(self) -> float:
        """0-10 scaled by how much of the available weight was captured."""
        max_w = sum(p.weight for p in self.pillars) or 1
        return round(self.total / max_w * 10, 1)


@dataclass
class TradeCard:
    verdict: str            # BUY | WATCH | AVOID
    conviction: float       # 0-10
    net_score: float
    entry: float | None
    stop: float | None
    targets: list[float]
    rr: list[float]
    risk_pct: float | None
    size_pct: float | None
    horizon: str
    bull_top: str
    bear_top: str
    invalidations: list[str]
    regime_note: str


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _lin(x: float, x0: float, x1: float) -> float:
    """Map x from [x0,x1] onto [0,100], clamped. x0->0, x1->100."""
    if x1 == x0:
        return 50.0
    return _clamp((x - x0) / (x1 - x0) * 100.0)


def _last(series: pd.Series) -> float | None:
    v = series.iloc[-1]
    return None if pd.isna(v) else float(v)


# ──────────────────────────────────────────────────────────────────────────────
# Fundamentals (yfinance .info — free, no login). screener.in can enrich later.
# ──────────────────────────────────────────────────────────────────────────────
def fetch_fundamentals(symbol: str) -> dict[str, Any]:
    """Best-effort fundamentals from yfinance. Returns {} on any failure so the
    council degrades gracefully to technical-only."""
    try:
        import yfinance as yf
        info = yf.Ticker(f"{symbol}.NS").info or {}
    except Exception:
        return {}

    def g(*keys):
        for k in keys:
            v = info.get(k)
            if v is not None:
                return v
        return None

    roe = g("returnOnEquity")
    opm = g("operatingMargins")
    npm = g("profitMargins")
    d2e = g("debtToEquity")
    rev_g = g("revenueGrowth")
    earn_g = g("earningsGrowth", "earningsQuarterlyGrowth")
    div_y = g("dividendYield")

    return {
        "market_cap":    g("marketCap"),
        "pe":            g("trailingPE"),
        "forward_pe":    g("forwardPE"),
        "peg":           g("pegRatio", "trailingPegRatio"),
        "pb":            g("priceToBook"),
        "roe":           roe * 100 if isinstance(roe, (int, float)) else None,      # -> %
        "opm":           opm * 100 if isinstance(opm, (int, float)) else None,      # -> %
        "npm":           npm * 100 if isinstance(npm, (int, float)) else None,      # -> %
        "debt_to_equity": d2e,                                                       # yf gives %
        "revenue_growth": rev_g * 100 if isinstance(rev_g, (int, float)) else None,  # -> %
        "earnings_growth": earn_g * 100 if isinstance(earn_g, (int, float)) else None,
        # NOT scaled by 100: unlike the margin/growth fields above (which yfinance
        # returns as fractions), dividendYield already comes back as a percentage
        # — TITAN reads 0.31 for ₹15 on a ₹4,850 price, ITC 5.59 for ₹16 on ₹285.
        # The old ×100 turned those into 31% and 559%.
        "dividend_yield": div_y if isinstance(div_y, (int, float)) else None,
        "sector":        g("sector"),
        "industry":      g("industry"),
        # Present in .info all along but never mapped; the deep-dive metric strip
        # (FR-1) reads them from here so a symbol with no filed statements still
        # shows EPS and book value.
        "eps_ttm":       g("trailingEps"),
        "book_value":    g("bookValue"),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Stage 1 — Evidence Gatherer
# ──────────────────────────────────────────────────────────────────────────────
def gather_evidence(
    symbol: str,
    df: pd.DataFrame,
    nifty_df: pd.DataFrame | None = None,
    fundamentals: dict[str, Any] | None = None,
) -> EvidenceBundle:
    b = EvidenceBundle(symbol=symbol)
    F, S, N = b.facts, b.subscores, b.notes

    close, high, low, vol = df["close"], df["high"], df["low"], df["volume"]
    price = float(close.iloc[-1])
    F["price"] = price

    # ── Moving-average stack ──
    ema20 = close.ewm(span=20, adjust=False).mean()
    sma50 = close.rolling(50).mean()
    sma150 = close.rolling(150).mean()
    sma200 = close.rolling(200).mean()
    e20, s50, s150, s200 = (_last(ema20), _last(sma50), _last(sma150), _last(sma200))
    F.update(ema20=e20, sma50=s50, sma150=s150, sma200=s200)

    stack_ok = all(v is not None for v in (e20, s50, s150, s200))
    aligned = bool(stack_ok and price > e20 > s50 > s150 > s200)
    inverted = bool(stack_ok and price < e20 < s50 < s150 < s200)
    F["ema_aligned"] = aligned
    F["ema_inverted"] = inverted

    # Distance above 200SMA — overextension gauge
    ext_pct = ((price - s200) / s200 * 100) if s200 else None
    F["pct_above_sma200"] = ext_pct

    # ── Stage analysis (Weinstein), heuristic from MA slope + price position ──
    stage = _infer_stage(price, s50, s200, sma200)
    F["stage"] = stage

    # ── Momentum indicators ──
    rsi = _last(RSIIndicator(close=close, window=14).rsi())
    adx = _last(ADXIndicator(high=high, low=low, close=close, window=14).adx())
    macd = MACD(close=close)
    macd_hist = _last(macd.macd_diff())
    atr = _last(AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range())
    F.update(rsi=rsi, adx=adx, macd_hist=macd_hist, atr=atr)
    F["atr_pct"] = (atr / price * 100) if atr else None

    # ── 52-week context ──
    high_52 = float(high.tail(252).max())
    low_52 = float(low.tail(252).min())
    F["high_52w"], F["low_52w"] = high_52, low_52
    F["pct_from_52w_high"] = (high_52 - price) / high_52 * 100 if high_52 else None
    F["pct_above_52w_low"] = (price - low_52) / low_52 * 100 if low_52 else None

    # ── Volume / accumulation ──
    vol_last = float(vol.iloc[-1])
    vol5 = float(vol.tail(5).mean())
    vol20 = float(vol.tail(20).mean())
    vol50 = float(vol.tail(50).mean())
    F.update(vol_last=vol_last, vol5=vol5, vol20=vol20, vol50=vol50)
    F["vol_ratio_last_50"] = vol_last / vol50 if vol50 else None
    F["vol_dryup"] = vol5 < vol20 * 0.9      # contraction (pre-breakout)
    F["turnover_cr"] = price * vol50 / 1e7   # ₹ crore median daily turnover

    # ── OBV slope (accumulation vs distribution) ──
    obv = (np.sign(close.diff().fillna(0)) * vol).cumsum()
    obv_slope = _slope(obv.tail(20))
    F["obv_slope"] = obv_slope

    # ── Relative strength vs Nifty ──
    rs_pct, rs_up = _relative_strength(close, nifty_df)
    F["rs_pct"] = rs_pct
    F["rs_uptrend"] = rs_up

    # ── Reuse existing repo scorers ──
    mv_score, mv_conds = sp.score_minervini(df, nifty_df=nifty_df)
    tf_score, tf_conds = sp.score_technofunda(df)
    F["minervini"] = mv_score
    F["technofunda"] = tf_score
    F["minervini_conds"] = mv_conds
    F["technofunda_conds"] = tf_conds

    # ── Swing low for stop placement (lowest low of last 10 bars) ──
    F["swing_low_10"] = float(low.tail(10).min())
    F["swing_high_20"] = float(high.tail(20).max())

    # ── Volume Profile — POC / value-area location (previously orphaned) ──
    # volume_profile.py was computed only on the chart; wire its price-vs-profile
    # read into the evidence so Setup Intelligence can speak to acceptance and the
    # POC magnet. Best-effort: any failure leaves vp_* absent and the panel simply
    # omits the volume-profile factors.
    # A trailing NaN yfinance gap bar (the repo's recurring OHLCV bug) makes the
    # histogram's hi=NaN and describe_position's "current price"=NaN, so drop NaN
    # OHLC rows first — the same dropna discipline used in scan_pead/opportunity_hub.
    try:
        vp_df = df.dropna(subset=["high", "low", "close", "volume"])
        profile = vp.compute_profile(vp_df)
        pos = vp.describe_position(vp_df, profile)
    except Exception:
        pos = None
    if pos:
        F["vp_zone"] = pos["zone"]                     # above_value | inside_value | below_value
        F["vp_poc"] = pos["poc"]
        F["vp_vah"] = pos["vah"]
        F["vp_val"] = pos["val"]
        F["vp_above_poc"] = pos["above_poc"]
        F["vp_poc_distance_pct"] = pos["poc_distance_pct"]
        F["vp_pct_volume_above_poc"] = pos["pct_volume_above_poc"]
        # HVN/LVN node position. These were computed by volume_profile.py and
        # drawn on the chart from the start, but describe_position's node fields
        # were dropped here — so the panel could say "above value" but not "on an
        # HVN" or "air pocket overhead", which is the actionable half.
        F["vp_at_hvn"] = pos["at_hvn"]
        F["vp_hvn_above_pct"] = pos["hvn_above_pct"]
        F["vp_hvn_below_pct"] = pos["hvn_below_pct"]
        F["vp_at_lvn"] = pos["at_lvn"]
        F["vp_lvn_above_pct"] = pos["lvn_above_pct"]
        F["vp_lvn_below_pct"] = pos["lvn_below_pct"]

    # ── CPR × Volume Profile (2026-09-28) — the two level systems finally meet.
    # Which CPR level sits inside a profile node, where the close sits against
    # the band, and the playbook setups on the last bar. Context, not a signal:
    # see cpr_vp.py's header. Best-effort like the profile read above.
    try:
        F["cpr_vp"] = cpr_vp.read(df.dropna(subset=["open", "high", "low", "close", "volume"]))
    except Exception:
        F["cpr_vp"] = None

    # ── RSI 60-40 with-trend setup (reuses the scanner, so the panel and the
    # Scanner Hub can never disagree about whether the setup is live) ──
    try:
        F["rsi_60_40"] = sc.scan_rsi_60_40(df)   # None or the hit dict
    except Exception:
        F["rsi_60_40"] = None

    # ── Fundamentals ──
    if fundamentals:
        b.has_fundamentals = True
        F["fundamentals"] = fundamentals

    _normalize_subscores(b)
    return b


def _infer_stage(price, s50, s200, sma200_series) -> int:
    """Weinstein 1-4 heuristic. 1=basing, 2=advancing, 3=topping, 4=declining."""
    if s200 is None or s50 is None:
        return 0
    s200_clean = sma200_series.dropna()
    rising200 = len(s200_clean) >= 20 and s200_clean.iloc[-1] > s200_clean.iloc[-20]
    if price > s200 and price > s50 and rising200:
        return 2
    if price > s200 and not rising200:
        return 3
    if price < s200 and s50 < s200:
        return 4
    return 1


def _slope(series: pd.Series) -> float:
    s = series.dropna()
    if len(s) < 3:
        return 0.0
    x = np.arange(len(s))
    y = s.values.astype(float)
    denom = (y.max() - y.min()) or 1.0
    return float(np.polyfit(x, y, 1)[0] / denom)   # normalized slope


def _relative_strength(close: pd.Series, nifty_df: pd.DataFrame | None):
    if nifty_df is None or len(nifty_df) < 130 or len(close) < 130:
        return None, None
    try:
        stock = close.copy()
        stock.index = pd.to_datetime(stock.index)
        nifty = nifty_df["close"].copy()
        nifty.index = pd.to_datetime(nifty.index)
        m = pd.concat([stock, nifty], axis=1, join="inner").dropna()
        m.columns = ["s", "n"]
        if len(m) < 130:
            return None, None
        rs_pct = (m["s"].iloc[-1] / m["s"].iloc[-130] - 1
                  - (m["n"].iloc[-1] / m["n"].iloc[-130] - 1)) * 100
        rs_line = m["s"] / m["n"]
        rs_up = float(rs_line.iloc[-1]) > float(rs_line.iloc[-30])
        return float(rs_pct), bool(rs_up)
    except Exception:
        return None, None


def _normalize_subscores(b: EvidenceBundle) -> None:
    """Turn raw facts into 0-100 sub-scores where 100 = maximally bullish."""
    F, S, N = b.facts, b.subscores, b.notes

    # Trend
    S["trend"] = 90 if F["ema_aligned"] else (10 if F["ema_inverted"] else 45)
    N["trend"] = ("Full EMA stack aligned (price>20>50>150>200)" if F["ema_aligned"]
                  else "Inverted MA stack — downtrend" if F["ema_inverted"]
                  else "Mixed MA structure")

    S["minervini"] = F["minervini"] / 8 * 100
    S["technofunda"] = F["technofunda"] / 6 * 100

    # Stage
    S["stage"] = {2: 90, 1: 55, 3: 35, 4: 10, 0: 45}[F["stage"]]
    N["stage"] = {2: "Stage 2 advancing", 1: "Stage 1 basing", 3: "Stage 3 topping",
                  4: "Stage 4 declining", 0: "Stage undetermined"}[F["stage"]]

    # Momentum
    rsi = F["rsi"]
    if rsi is None:
        S["rsi"] = 50.0
    elif rsi >= 75:
        S["rsi"] = 40.0   # overbought — not bullish for fresh entry
    else:
        S["rsi"] = _lin(rsi, 35, 65)
    N["rsi"] = f"RSI {rsi:.0f}" if rsi is not None else "RSI n/a"

    S["adx"] = _lin(F["adx"] or 0, 15, 40)
    S["macd"] = 75 if (F["macd_hist"] or 0) > 0 else 25
    S["rs"] = _lin(F["rs_pct"] or 0, -20, 30) if F["rs_pct"] is not None else 50

    # Structure
    pfh = F["pct_from_52w_high"]
    S["proximity_high"] = _lin(-(pfh or 100), -40, -2) if pfh is not None else 50
    N["proximity_high"] = f"{pfh:.0f}% below 52w high" if pfh is not None else "n/a"

    # Volume
    S["volume"] = 70 if F["vol_dryup"] else 45
    if (F["obv_slope"] or 0) > 0:
        S["volume"] = min(100, S["volume"] + 20)
    N["volume"] = ("Volume dry-up + OBV rising (accumulation)" if F["vol_dryup"] and (F["obv_slope"] or 0) > 0
                   else "Volume contracting" if F["vol_dryup"]
                   else "No clear accumulation")

    # Overextension (higher = more extended = bearish for entry)
    ext = F["pct_above_sma200"]
    S["overextension"] = _lin(ext or 0, 15, 60) if ext is not None else 30
    N["overextension"] = f"{ext:.0f}% above 200SMA" if ext is not None else "n/a"

    # Liquidity
    S["liquidity"] = _lin(F["turnover_cr"] or 0, 1, 25)
    N["liquidity"] = f"₹{F['turnover_cr']:.1f} Cr median daily turnover" if F.get("turnover_cr") else "n/a"

    # Fundamentals
    fu = F.get("fundamentals") or {}
    if b.has_fundamentals:
        S["roe"] = _lin(fu.get("roe") or 0, 5, 25) if fu.get("roe") is not None else 50
        S["opm"] = _lin(fu.get("opm") or 0, 5, 25) if fu.get("opm") is not None else 50
        # debt: yfinance debtToEquity is in %, lower is better
        d2e = fu.get("debt_to_equity")
        S["debt"] = (100 - _lin(d2e, 0, 150)) if d2e is not None else 50
        S["growth"] = _lin(fu.get("earnings_growth") or fu.get("revenue_growth") or 0, 0, 30) \
            if (fu.get("earnings_growth") is not None or fu.get("revenue_growth") is not None) else 50
        peg = fu.get("peg")
        S["valuation"] = (100 - _lin(peg, 0.5, 3.0)) if peg else (
            100 - _lin(fu.get("pe") or 30, 10, 60) if fu.get("pe") else 50)
        N["quality"] = _fmt_quality(fu)
        N["growth"] = _fmt_growth(fu)
        N["valuation"] = _fmt_valuation(fu)


def _fmt_quality(fu):
    parts = []
    if fu.get("roe") is not None: parts.append(f"ROE {fu['roe']:.0f}%")
    if fu.get("opm") is not None: parts.append(f"OPM {fu['opm']:.0f}%")
    if fu.get("debt_to_equity") is not None: parts.append(f"D/E {fu['debt_to_equity']:.0f}")
    return " · ".join(parts) or "n/a"


def _fmt_growth(fu):
    parts = []
    if fu.get("earnings_growth") is not None: parts.append(f"EPS growth {fu['earnings_growth']:.0f}%")
    if fu.get("revenue_growth") is not None: parts.append(f"Rev growth {fu['revenue_growth']:.0f}%")
    return " · ".join(parts) or "n/a"


def _fmt_valuation(fu):
    parts = []
    if fu.get("pe") is not None: parts.append(f"P/E {fu['pe']:.1f}")
    if fu.get("peg") is not None: parts.append(f"PEG {fu['peg']:.2f}")
    if fu.get("pb") is not None: parts.append(f"P/B {fu['pb']:.1f}")
    return " · ".join(parts) or "n/a"


# ──────────────────────────────────────────────────────────────────────────────
# Stage 2 — Bull & Bear (pure functions over the bundle)
# ──────────────────────────────────────────────────────────────────────────────
def bull_case(b: EvidenceBundle) -> Thesis:
    S, F = b.subscores, b.facts
    pillars: list[Pillar] = []
    breakers: list[str] = []

    trend = np.mean([S["trend"], S["stage"], S["minervini"]])
    pillars.append(Pillar("Trend", trend, BULL_WEIGHTS["trend"],
                          f"{b.notes['trend']}; {b.notes['stage']}; Minervini {F['minervini']}/8"))

    mom = np.mean([S["rsi"], S["adx"], S["macd"], S["rs"], S["technofunda"]])
    rs_txt = f"RS {F['rs_pct']:+.0f}% vs Nifty" if F.get("rs_pct") is not None else "RS n/a"
    pillars.append(Pillar("Momentum", mom, BULL_WEIGHTS["momentum"],
                          f"{b.notes['rsi']}, ADX {F['adx']:.0f}" if F.get('adx') else b.notes['rsi']
                          + f"; MACD {'+' if (F['macd_hist'] or 0) > 0 else '-'}; {rs_txt}"))

    pillars.append(Pillar("Structure", S["proximity_high"], BULL_WEIGHTS["structure"],
                          b.notes["proximity_high"]))
    pillars.append(Pillar("Volume", S["volume"], BULL_WEIGHTS["volume"], b.notes["volume"]))

    if b.has_fundamentals:
        quality = np.mean([S.get("roe", 50), S.get("opm", 50), S.get("debt", 50)])
        pillars.append(Pillar("Quality", quality, BULL_WEIGHTS["quality"], b.notes.get("quality", "n/a")))
        growth = np.mean([S.get("growth", 50), S.get("valuation", 50)])
        pillars.append(Pillar("Growth/Value", growth, BULL_WEIGHTS["growth"],
                              f"{b.notes.get('growth','n/a')}; {b.notes.get('valuation','n/a')}"))

    return Thesis("BULL", pillars, breakers)


def bear_case(b: EvidenceBundle) -> Thesis:
    S, F = b.subscores, b.facts
    pillars: list[Pillar] = []
    breakers: list[str] = []

    # Bear pillars score high (0-100) when the RISK is high.
    over = S["overextension"]
    if F.get("rsi") is not None and F["rsi"] >= 78:
        over = max(over, 80)
        breakers.append(f"RSI {F['rsi']:.0f} — climactic, high reversal risk")
    pillars.append(Pillar("Overextension", over, BEAR_WEIGHTS["overextension"], b.notes["overextension"]))

    # Trend break: inverse of trend health
    tb = 100 - np.mean([S["trend"], S["stage"]])
    if F["stage"] == 4:
        breakers.append("Stage 4 decline — MAs stacked bearishly")
    pillars.append(Pillar("Trend break", tb, BEAR_WEIGHTS["trend_break"],
                          f"{b.notes['stage']}; {'inverted MAs' if F['ema_inverted'] else 'trend intact' if F['ema_aligned'] else 'mixed MAs'}"))

    dist = 100 - S["volume"]
    if (F.get("obv_slope") or 0) < 0:
        dist = min(100, dist + 15)
    pillars.append(Pillar("Distribution", dist, BEAR_WEIGHTS["distribution"],
                          "OBV falling / no accumulation" if (F.get("obv_slope") or 0) < 0 else b.notes["volume"]))

    if b.has_fundamentals:
        fu = F.get("fundamentals") or {}
        fund_risk = 100 - np.mean([S.get("roe", 50), S.get("debt", 50), S.get("valuation", 50)])
        if (fu.get("debt_to_equity") or 0) > 200:
            breakers.append(f"D/E {fu['debt_to_equity']:.0f} — heavy leverage")
        pillars.append(Pillar("Fundamental risk", fund_risk, BEAR_WEIGHTS["fundamental"],
                              f"{b.notes.get('quality','n/a')}; {b.notes.get('valuation','n/a')}"))

    liq = 100 - S["liquidity"]
    if (F.get("turnover_cr") or 0) < 1:
        breakers.append(f"Thin liquidity (₹{F.get('turnover_cr', 0):.1f} Cr/day)")
    pillars.append(Pillar("Liquidity risk", liq, BEAR_WEIGHTS["liquidity"], b.notes["liquidity"]))

    return Thesis("BEAR", pillars, breakers)


# ──────────────────────────────────────────────────────────────────────────────
# Stage 3 — Judge
# ──────────────────────────────────────────────────────────────────────────────
def judge(
    b: EvidenceBundle,
    bull: Thesis,
    bear: Thesis,
    regime: str | None = None,
    total_capital: float | None = None,
) -> TradeCard:
    F = b.facts

    # Add a regime pillar to the bear side (hostile regime penalizes longs).
    regime = (regime or "").upper()
    regime_penalty = 0.0
    regime_note = "Regime neutral / not supplied"
    if "RISK-OFF" in regime or "RISK_OFF" in regime:
        regime_penalty = BEAR_WEIGHTS["regime"] * 0.8
        regime_note = "RISK-OFF regime — long convictions discounted"
    elif "RISK-ON" in regime or "RISK_ON" in regime:
        regime_penalty = -BEAR_WEIGHTS["regime"] * 0.4   # tailwind
        regime_note = "RISK-ON regime — supportive of longs"

    net = bull.total - bear.total - regime_penalty

    # Hard breakers cap the verdict at WATCH/AVOID regardless of net.
    hard_breaker = len(bear.breakers) > 0

    if net >= BUY_THRESHOLD and not hard_breaker:
        verdict = "BUY"
    elif net <= AVOID_THRESHOLD or (hard_breaker and net < BUY_THRESHOLD):
        verdict = "AVOID"
    else:
        verdict = "WATCH"

    conviction = round(_clamp((net + 50) / 100 * 10, 0, 10), 1)

    # ── Trade levels ──
    price = F["price"]
    atr = F.get("atr")
    swing_low = F.get("swing_low_10")
    swing_high = F.get("swing_high_20")
    high_52 = F.get("high_52w")

    entry = round(price, 2)
    stop = None
    if swing_low and swing_low < price:
        stop = round(min(swing_low, price - ATR_STOP_MULT * (atr or 0)), 2)
    elif atr:
        stop = round(price - ATR_STOP_MULT * atr, 2)

    targets, rr = [], []
    risk_per_share = (entry - stop) if (stop and entry > stop) else None
    if risk_per_share and risk_per_share > 0:
        cand = []
        if swing_high and swing_high > price:
            cand.append(swing_high)
        if high_52 and high_52 > price:
            cand.append(high_52)
        # ATR-multiple targets fill in the rest
        cand += [round(entry + m * risk_per_share, 2) for m in (2, 3)]
        seen = set()
        for t in sorted(cand):
            t = round(float(t), 2)
            if t <= entry or t in seen:
                continue
            seen.add(t)
            targets.append(t)
            rr.append(round((t - entry) / risk_per_share, 2))
        targets, rr = targets[:3], rr[:3]

    risk_pct = round(risk_per_share / entry * 100, 2) if risk_per_share else None
    # position size so that a stop-out loses RISK_PER_TRADE_PCT of capital
    size_pct = ps.size_pct_from_stop_pct(risk_pct, RISK_PER_TRADE_PCT)

    horizon = "positional (weeks-months)" if F["stage"] == 2 else \
              "swing (days-weeks)" if F["stage"] in (1, 3) else "avoid / short-only"

    bull_top = max(bull.pillars, key=lambda p: p.contribution)
    bear_top = max(bear.pillars, key=lambda p: p.contribution)

    invalidations = list(bear.breakers)
    if stop:
        invalidations.insert(0, f"Daily close below stop ₹{stop}")

    return TradeCard(
        verdict=verdict, conviction=conviction, net_score=round(net, 1),
        entry=entry, stop=stop, targets=targets, rr=rr,
        risk_pct=risk_pct, size_pct=size_pct, horizon=horizon,
        bull_top=f"{bull_top.name}: {bull_top.reason}",
        bear_top=f"{bear_top.name}: {bear_top.reason}",
        invalidations=invalidations, regime_note=regime_note,
    )


def run_council(
    symbol: str,
    df: pd.DataFrame,
    nifty_df: pd.DataFrame | None = None,
    fundamentals: dict[str, Any] | None = None,
    regime: str | None = None,
) -> tuple[EvidenceBundle, Thesis, Thesis, TradeCard]:
    """One-call convenience wrapper for the whole pipeline."""
    bundle = gather_evidence(symbol, df, nifty_df, fundamentals)
    bull = bull_case(bundle)
    bear = bear_case(bundle)
    card = judge(bundle, bull, bear, regime)
    return bundle, bull, bear, card


# ──────────────────────────────────────────────────────────────────────────────
# Stage 4 — Setup Intelligence (plain-language panel over the same evidence)
#
# Pure presentation logic: no new computation and no fetches. Every value here is
# derived from the bundle/theses/card the council already produced, so the panel
# can never disagree with the Judge's verdict.
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class SetupIntel:
    status_label: str
    status_tone: str                     # good | neutral | bad
    chips: list[tuple[str, str, str]]    # (label, value, tone)
    bullish_factors: list[str]
    risk_factors: list[str]
    overall_view: str
    # The Judge's own numbers, so the panel can draw the balance instead of
    # only quoting it in the overall-view sentence.
    bull_conviction: float | None = None
    bear_conviction: float | None = None
    net_score: float | None = None


def _band(score: float, labels: tuple[str, str, str],
          hi: float = 70.0, mid: float = 45.0) -> tuple[str, str]:
    """Map a 0-100 subscore onto (label, tone) using two cut points."""
    if score >= hi:
        return labels[0], "good"
    if score >= mid:
        return labels[1], "neutral"
    return labels[2], "bad"


def setup_intelligence(b: EvidenceBundle, bull: Thesis, bear: Thesis,
                       card: TradeCard) -> SetupIntel:
    """Turn the council's evidence into a scannable, plain-language setup panel."""
    F, S = b.facts, b.subscores

    # ── Status badge — mirrors the Judge so the two can never contradict ──
    status_label, status_tone = {
        "BUY":   ("Strong technical characteristics", "good"),
        "WATCH": ("Developing setup — not yet triggered", "neutral"),
        "AVOID": ("Weak technical characteristics", "bad"),
    }.get(card.verdict, ("Setup unclear", "neutral"))

    # ── Chips ──
    breakout = float(np.mean([S.get("proximity_high", 50), S.get("trend", 50)]))
    rs_label, rs_tone = _band(S.get("rs", 50), ("Strong", "Moderate", "Weak"))
    br_label, br_tone = _band(breakout, ("High", "Medium", "Low"))
    acc_label, acc_tone = _band(S.get("volume", 50),
                                ("Constructive", "Neutral", "Distributive"))
    chips = [
        ("Relative strength", rs_label, rs_tone),
        ("Breakout readiness", br_label, br_tone),
        ("Accumulation", acc_label, acc_tone),
    ]
    # Volume-profile location chip (only when the profile computed).
    vp_zone = F.get("vp_zone")
    if vp_zone:
        loc_label, loc_tone = {
            "above_value":  ("Above value", "good"),
            "inside_value": ("In value", "neutral"),
            "below_value":  ("Below value", "bad"),
        }.get(vp_zone, ("Unclear", "neutral"))
        chips.append(("Value-area location", loc_label, loc_tone))
    cv = F.get("cpr_vp")
    if cv:
        cpr_label, cpr_tone = {
            "above_tc": ("Above TC", "good"),
            "inside":   ("Inside CPR", "neutral"),
            "below_bc": ("Below BC", "bad"),
        }[cv["position"]]
        if cv["cpr_in_hvn"]:
            cpr_label += " · in HVN"
        chips.append(("CPR", cpr_label, cpr_tone))

    bulls: list[str] = []
    risks: list[str] = []

    # ── Trend / stage ──
    if F.get("ema_aligned"):
        bulls.append("Full EMA stack aligned (price > 20 > 50 > 150 > 200).")
    if F.get("ema_inverted"):
        risks.append("Inverted MA stack — established downtrend.")
    stage = F.get("stage")
    if stage == 2:
        bulls.append("Stage 2 advancing — institutional uptrend intact.")
    elif stage == 1:
        bulls.append("Stage 1 basing — accumulation phase, no trigger yet.")
    elif stage == 3:
        risks.append("Stage 3 topping — trend maturing, distribution risk.")
    elif stage == 4:
        risks.append("Stage 4 declining — no long edge here.")

    mv = F.get("minervini")
    if mv is not None:
        if mv >= 6:
            bulls.append(f"Minervini {mv}/8 — trend template largely met.")
        elif mv <= 3:
            risks.append(f"Minervini {mv}/8 — fails most trend-template gates.")

    # ── Momentum ──
    rsi = F.get("rsi")
    if rsi is not None:
        if rsi >= 75:
            risks.append(f"RSI {rsi:.0f} — overbought, poor fresh-entry location.")
        elif 50 <= rsi < 70:
            bulls.append(f"RSI {rsi:.0f} — constructive momentum.")
        elif rsi < 40:
            risks.append(f"RSI {rsi:.0f} — momentum weak.")

    macd_hist = F.get("macd_hist")
    if macd_hist is not None:
        if macd_hist > 0:
            bulls.append("MACD histogram positive — momentum improving.")
        else:
            risks.append("MACD histogram below zero — weak trend.")

    adx = F.get("adx")
    if adx is not None:
        if adx >= 25:
            bulls.append(f"ADX {adx:.0f} — trending strongly.")
        elif adx < 20:
            risks.append(f"ADX {adx:.0f} — no clear trend (chop).")

    rs_pct = F.get("rs_pct")
    if rs_pct is not None:
        if rs_pct > 0:
            bulls.append(f"RS {rs_pct:+.0f}% vs Nifty — outperforming.")
        else:
            risks.append(f"RS {rs_pct:+.0f}% vs Nifty — lagging the index.")
    if F.get("rs_uptrend"):
        bulls.append("RS line trending up — leadership confirmed.")

    # RSI 60-40 with-trend continuation setup (from the scanner).
    r6040 = F.get("rsi_60_40")
    if r6040:
        kind = "RSI-40 pullback at EMA support" if "Pullback" in r6040["pattern_type"] \
            else "RSI-60 breakout clearing the 20-day high"
        bulls.append(f"RSI 60-40 setup live — {kind} (with-trend continuation entry).")

    # ── Structure ──
    pfh = F.get("pct_from_52w_high")
    if pfh is not None:
        if pfh <= 10:
            bulls.append(f"{pfh:.0f}% below 52w high — trading near highs.")
        elif pfh > 25:
            risks.append(f"{pfh:.0f}% below 52w high — far from highs.")

    ext = F.get("pct_above_sma200")
    if ext is not None and ext >= 40:
        risks.append(f"{ext:.0f}% above 200SMA — extended, mean-reversion risk.")

    atr_pct = F.get("atr_pct")
    if atr_pct is not None:
        if 2.0 <= atr_pct <= 6.0:
            bulls.append(f"ATR {atr_pct:.1f}%/day — healthy volatility.")
        elif atr_pct > 8.0:
            risks.append(f"ATR {atr_pct:.1f}%/day — erratic, sizing risk.")

    # ── Volume / accumulation ──
    if F.get("vol_dryup"):
        bulls.append("Volume dry-up — range contracting (pre-breakout signature).")
    obv_slope = F.get("obv_slope")
    if obv_slope is not None:
        if obv_slope > 0:
            bulls.append("OBV rising — accumulation.")
        else:
            risks.append("OBV falling — distribution.")
    vr = F.get("vol_ratio_last_50")
    if vr is not None and vr >= 1.5:
        bulls.append(f"Recent volume expansion ({vr:.1f}x 50d average).")

    tcr = F.get("turnover_cr")
    if tcr is not None:
        if tcr >= 5:
            bulls.append(f"₹{tcr:.1f} Cr daily turnover — liquid enough to trade.")
        elif tcr < 2:
            risks.append(f"₹{tcr:.1f} Cr daily turnover — thin, slippage/exit risk.")

    # ── Volume profile — POC / value-area acceptance (previously orphaned) ──
    vp_zone = F.get("vp_zone")
    if vp_zone:
        poc = F.get("vp_poc")
        vah = F.get("vp_vah")
        val = F.get("vp_val")
        poc_dist = F.get("vp_poc_distance_pct")
        if vp_zone == "above_value":
            bulls.append(
                f"Trading above the value area (VAH ₹{vah:.0f}) — price accepted "
                f"higher, POC ₹{poc:.0f} now support beneath.")
        elif vp_zone == "below_value":
            risks.append(
                f"Trading below the value area (VAL ₹{val:.0f}) — POC ₹{poc:.0f} "
                f"overhead as resistance; supply not yet cleared.")
        else:  # inside_value
            if F.get("vp_above_poc"):
                bulls.append(
                    f"Inside value, above the POC (₹{poc:.0f}) — upper-half "
                    f"acceptance, control price as support.")
            else:
                risks.append(
                    f"Inside value, below the POC (₹{poc:.0f}) — must reclaim the "
                    f"control price for a clean long.")
        # A tight coil right on the control price is a decision point worth flagging.
        if poc_dist is not None and abs(poc_dist) <= 1.0:
            bulls.append(
                f"Price sitting on the POC (within {abs(poc_dist):.1f}%) — "
                f"high-volume fair-value pivot, tight-stop decision point.")

        # ── HVN / LVN node structure (wired 2026-08-09) ──
        # HVN = heavy prior business, acts as a magnet and S/R; LVN = air pocket
        # price traverses quickly. Structural context, not a signal: unmeasured,
        # like the value-area reads above.
        NEAR = 4.0            # % — a node this close is in play for a swing move
        hvn_above = F.get("vp_hvn_above_pct")
        hvn_below = F.get("vp_hvn_below_pct")
        lvn_above = F.get("vp_lvn_above_pct")

        if F.get("vp_at_hvn"):
            risks.append(
                "Price inside a high-volume node — heaviest prior business at this "
                "price; HVNs act as magnets, so expect rotation/chop here rather "
                "than a clean directional move.")
        elif F.get("vp_at_lvn"):
            risks.append(
                "Price inside a low-volume node — an air pocket with little prior "
                "business; poor support underfoot, so stops here are unreliable "
                "and moves through it tend to be fast in both directions.")

        if hvn_below is not None and hvn_below <= NEAR:
            bulls.append(
                f"High-volume node {hvn_below:.1f}% below — a volume shelf to fall "
                f"back on; the natural stop reference beneath price.")
        if hvn_above is not None and hvn_above <= NEAR:
            risks.append(
                f"High-volume node {hvn_above:.1f}% overhead — heavy prior business "
                f"to absorb before price can travel; the first real ceiling.")
        if lvn_above is not None and lvn_above <= NEAR and not (
                hvn_above is not None and hvn_above < lvn_above):
            bulls.append(
                f"Low-volume node {lvn_above:.1f}% overhead with no HVN in front of "
                f"it — thin air above; breakouts traverse an LVN quickly.")

    # ── CPR × Volume Profile confluence (2026-09-28) ──
    # The playbook: a CPR level inside a high-volume node is a decision zone
    # worth more than either alone; the setups are what the LAST bar did there.
    # Descriptions, unmeasured — the SVP composite from the same family scored
    # negative, so none of this is a BUY/SELL.
    cv = F.get("cpr_vp")
    if cv:
        lv = cv["levels"]
        conf = cpr_vp.confluence_text(cv)
        if cv["cpr_in_hvn"]:
            (bulls if cv["position"] == "above_tc" else risks).append(
                f"CPR band (₹{lv['bc']:.0f}–₹{lv['tc']:.0f}) sits inside a high-volume "
                f"node ({conf}) — "
                + ("price is holding above a volume-backed pivot; the band is the "
                   "natural stop reference." if cv["position"] == "above_tc" else
                   "heavy prior business right at today's pivot; expect a fight here "
                   "rather than a clean move."))
        elif cv["cpr_in_lvn"]:
            risks.append(
                f"CPR band (₹{lv['bc']:.0f}–₹{lv['tc']:.0f}) sits in a low-volume node — "
                f"a pivot in thin air; moves through it tend to be fast either way.")
        if cv["band"] == "narrow":
            bulls.append(
                f"Narrow CPR ({cv['width_pct']:.2f}% of price) — compressed value; "
                f"a trending session is more likely than a range day.")
        for name in cv["setups"]:
            text = cpr_vp.SETUP_LABELS[name]
            rv = f" (RVOL {cv['rvol']:.1f}x)" if cv.get("rvol") else ""
            (bulls if name in cpr_vp.BULLISH else risks).append(
                f"CPR × profile setup: {text}{rv} — last bar only, unmeasured.")

    # ── Fundamentals (only when yfinance actually returned them) ──
    if b.has_fundamentals:
        fu = F.get("fundamentals") or {}
        roe = fu.get("roe")
        if roe is not None and roe >= 15:
            bulls.append(f"ROE {roe:.0f}% — quality business.")
        d2e = fu.get("debt_to_equity")
        if d2e is not None and d2e > 150:
            risks.append(f"D/E {d2e:.0f} — heavily leveraged.")
        eg = fu.get("earnings_growth")
        if eg is not None and eg >= 15:
            bulls.append(f"EPS growth {eg:.0f}% — earnings expanding.")
        peg = fu.get("peg")
        if peg is not None and peg > 3:
            risks.append(f"PEG {peg:.2f} — richly valued vs growth.")

    # ── Regime + hard thesis-breakers ──
    if "RISK-OFF" in card.regime_note:
        risks.append("Market regime is currently risk-off — long setups discounted.")
    elif "RISK-ON" in card.regime_note:
        bulls.append("Market regime is risk-on — supportive of longs.")
    # Hard thesis-breakers are flagged distinctly — they may restate a factor
    # above, which is intentional emphasis rather than duplication.
    for br in bear.breakers:
        risks.append(f"⚠️ Thesis-breaker — {br}")

    # ── Overall view ──
    view_parts: list[str] = []
    if acc_label == "Constructive":
        view_parts.append("Short-term accumulation signals are visible.")
    if status_tone == "good":
        view_parts.append(f"{status_label} — momentum and institutional cues "
                          "show broad alignment.")
    elif status_tone == "neutral":
        view_parts.append(f"{status_label} — evidence is mixed; wait for a trigger.")
    else:
        view_parts.append(f"{status_label} — the bear case dominates.")
    view_parts.append(
        f"Bull conviction {bull.conviction}/10 vs bear {bear.conviction}/10 "
        f"(net {card.net_score:+.0f}) across {len(bulls)} supporting and "
        f"{len(risks)} risk factor(s)."
    )

    return SetupIntel(
        status_label=status_label,
        status_tone=status_tone,
        chips=chips,
        bullish_factors=bulls,
        risk_factors=risks,
        overall_view=" ".join(view_parts),
        bull_conviction=bull.conviction,
        bear_conviction=bear.conviction,
        net_score=card.net_score,
    )
