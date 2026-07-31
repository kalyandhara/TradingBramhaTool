"""The M1 Overall Rating — extracted so headless jobs can score too.

This logic used to live inside dashboard_app.py, which means it could only run
inside a Streamlit session. The daily Opportunity Hub job
([opportunity_daily.py](opportunity_daily.py)) needs the *same* rating the
interactive Hub shows, and a second implementation would guarantee the two
eventually disagree — the same one-scorer argument that put the fundamental
bands in a single module.

Nothing here touches Streamlit. `dashboard_app.py` imports these under its old
private names, so every existing call site is unchanged.
"""

from __future__ import annotations

import pandas as pd

import screener_pipeline as sp
import ew_module

#: Weights for the four rating components. Biased toward Minervini as the most
#: referenced framework in this wiki; tunable live from the Scanner Hub.
OVERALL_WEIGHTS = {"minervini": 0.35, "technofunda": 0.25, "canslim": 0.20, "ew": 0.20}


def compute_canslim(df: pd.DataFrame, nifty_df: pd.DataFrame | None) -> tuple:
    """
    Returns (score, conds, rs_pct, rs_line) where:
      score    — int, number of CANSLIM conditions that pass (max 4 computable)
      conds    — dict of condition_label → True/False/None
      rs_pct   — float, stock 12m return minus Nifty 12m return (outperformance %)
      rs_line  — pd.Series (normalized to 100 at start) or None
    """
    conds: dict = {}
    rs_pct: float = 0.0
    rs_line = None

    last = float(df["close"].iloc[-1])

    # N — New High: within 15% of 52-week high
    high_52 = float(df["high"].tail(252).max()) if len(df) >= 60 else float(df["high"].max())
    conds["N — Near 52w High (<15% below)"] = (high_52 - last) / high_52 < 0.15

    # S — Supply/Demand: today's volume ≥ 50-day average
    vol50 = float(df["volume"].tail(50).mean())
    vol_last = float(df["volume"].iloc[-1])
    conds["S — Volume ≥ 50d Average"] = vol_last >= vol50

    # M — Market direction: Nifty50 above its SMA200
    if nifty_df is not None and len(nifty_df) >= 200:
        nifty_sma200 = float(nifty_df["close"].rolling(200).mean().iloc[-1])
        conds["M — Market Above SMA200 (Uptrend)"] = float(nifty_df["close"].iloc[-1]) > nifty_sma200
    else:
        conds["M — Market Above SMA200 (Uptrend)"] = None

    # L — Leader: stock 12m return > Nifty 12m return (RS outperformance)
    if nifty_df is not None:
        nifty_aligned = nifty_df["close"].reindex(df.index, method="ffill")
        nifty_aligned = nifty_aligned.bfill()

        # RS Line normalized to 100 at first available point
        rs_raw = df["close"] / nifty_aligned.replace(0, float("nan"))
        rs_line = (rs_raw / rs_raw.iloc[0]) * 100

        lookback = min(252, len(df) - 1)
        if lookback >= 21:
            stock_12m = (float(df["close"].iloc[-1]) / float(df["close"].iloc[-lookback]) - 1) * 100
            nifty_12m = (float(nifty_aligned.iloc[-1]) / float(nifty_aligned.iloc[-lookback]) - 1) * 100
            rs_pct = stock_12m - nifty_12m

        conds["L — RS Leader (outperforms Nifty50)"] = rs_pct > 0
    else:
        conds["L — RS Leader (outperforms Nifty50)"] = None

    score = sum(1 for v in conds.values() if v is True)
    return score, conds, rs_pct, rs_line


def overall_rating(df: pd.DataFrame, nifty_df: pd.DataFrame | None,
                   weights: dict | None = None) -> tuple[int | None, dict]:
    """Return (rating 0-100, breakdown) fusing Minervini/8 + TechnoFunda/6 +
    CANSLIM/computable + EW confidence/100. Rating is None if scoring fails
    (e.g. too few bars). Each sub-score is normalised to 0-1 then weighted."""
    w = weights or OVERALL_WEIGHTS
    try:
        mv, _ = sp.score_minervini(df, nifty_df=nifty_df)          # 0-8
        tf, _ = sp.score_technofunda(df)                           # 0-6
        cs, cs_conds, _, _ = compute_canslim(df, nifty_df)         # 0-4 (some None)
        ew_conf = int(ew_module.analyze_ew(df).get("confidence", 0) or 0)  # 0-100
    except Exception:
        return None, {}

    # Normalise CANSLIM by the count of computable (non-None) conditions so a
    # missing benchmark doesn't silently deflate the score.
    computable = sum(1 for v in cs_conds.values() if v is not None)
    mv_n = mv / 8.0
    tf_n = tf / 6.0
    cs_n = (cs / computable) if computable else 0.0
    ew_n = ew_conf / 100.0

    rating = round(100 * (mv_n * w["minervini"] + tf_n * w["technofunda"]
                          + cs_n * w["canslim"] + ew_n * w["ew"]))
    return rating, {
        "Minervini": f"{mv}/8", "TechnoFunda": f"{tf}/6",
        "CANSLIM": f"{cs}/{computable}" if computable else "n/a",
        "EW conf": str(ew_conf),
    }
