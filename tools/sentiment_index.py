#!/usr/bin/env python3
"""
sentiment_index.py — Market Sentiment Index (Phase 1, 4 home-data inputs).

Composite 0-100 gauge for NIFTY-wide sentiment, mapped to 5 bands. See
`trading-wiki/wiki/concepts/Market-Sentiment-Index.md` and the roadmap analysis
at `wiki/analyses/Market-Sentiment-Index-Roadmap-Fit-2026-07-14.md`.

Inputs (Raut-style but with disclosed technical replacements). The weights are
the roadmap page's own pre-registered v1 table, not a set invented here:
  1. Advance / Decline ratio          (weight 25, bhavcopy)
  2. Sector performance count         (weight 20, distinct NIFTY sector indices)
  3. NIFTY vs SMA200 regime           (weight 20, yfinance ^NSEI daily)
  4. PMax direction on NIFTY 1H       (weight 15, ATR-trailing band on ^NSEI 60m)
  5. PCR level + slope on NIFTY       (weight 20, F&O bhavcopy via `pcr.py`)
  ──────────────────────────────────────────────────
                                       total   100

Factor 5 wired 2026-09-10 (backlog B-22). Two things about it that must not be
lost, because both are the kind of thing this file has been burned by before:

  * **It ships NOT_CHECKED and stays that way for months.** `pcr.py` refuses to
    band an index PCR without a baseline of that index's OWN history, and none
    existed. So this module now STORES one (`pcr_index_history`, written on every
    compute) and scores the factor only once MIN_PCR_HISTORY observations exist.
    Until then factor 5 is NOT_CHECKED, is excluded from the composite, and the
    remaining 80 weight is renormalised to 100 exactly as a stale sector feed
    already is — i.e. **today's score is unchanged by this wiring.** That is the
    honest shape of the change: it starts the clock rather than inventing a
    reading to fill the slot.
  * **The sign convention is a GUESS and is labelled one.** Higher PCR scores as
    more bullish (the trend-following read). PCR has no fixed sign — the
    contrarian read is the exact opposite, and `pcr.py` declines to pick for
    precisely this reason. B-44r retired GEX outright after measuring that its
    naive convention was backwards for NSE, so this is a live risk, not a
    theoretical one. `sign_convention` and `convention_measured: False` ride in
    the persisted inputs so the eventual test can find them.

MEASURED 2026-09-10 (B-66, `tools/sentiment_factor_edge.py`) — READ THIS BEFORE
BUILDING ON THE SCORE. Every input above, AND the composite, was tested against
NIFTY's forward 5-day return as a tercile spread. **None discriminates:**

    A/D (proxy)   -0.03%  rho +0.00  p=0.855
    Sector        -0.01%  rho -0.00  p=0.908   (19y, n=4,649)
    Regime        -0.08%  rho -0.04  p=0.829   (18y, n=4,452)
    COMPOSITE     -0.12%  rho +0.01  p=0.703

PMax was measured separately (B-65r) and also does not discriminate. The two
deepest arms span 2008, 2013, 2020 and 2022, so this is a measurement rather
than a shortage of one.

Nothing here was deleted or re-weighted on that result — a null is not evidence
of harm, and there is no better-scoring input to move weight toward. But the
score DESCRIBES the current tape and does not FORECAST, and the band names
("Strong Buy") must not be read as advice. The page carries that caption.

Bands (matches the reference infographic):
    0-20   Strong Sell
   20-40   Sell
   40-55   Neutral
   55-80   Buy
   80-100  Strong Buy

Public API:
  compute_sentiment(persist=True) -> dict
  history(days=90)               -> pd.DataFrame

CLI:
  python sentiment_index.py           # compute + print + persist
  python sentiment_index.py --peek    # compute + print (no persist)
"""
from __future__ import annotations

import json
import logging
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portfolio_db as db
import screener_pipeline as sp
import sector_rotation as secrot

try:
    import yfinance as yf
except ImportError:
    sys.exit("Run:  py -3 -m pip install yfinance")

log = logging.getLogger("sentiment_index")

# ── Weights ─────────────────────────────────────────────────────────
#: These are the roadmap's v1 numbers (25/20/20/15/20), adopted verbatim when
#: factor 5 landed. The previous 30/25/25/20 was explicitly the "ships without
#: input #5" fallback, and the docstring there said the others re-normalise when
#: PCR arrives. Taking the pre-registered split rather than inventing a new one
#: keeps this out of the "floors all set in one session" bucket (B-21b).
W_ADV_DECL = 25
W_SECTOR   = 20
W_REGIME   = 20
W_PMAX_1H  = 15
W_PCR      = 20
W_TOTAL    = W_ADV_DECL + W_SECTOR + W_REGIME + W_PMAX_1H + W_PCR  # 100

# ── Band mapping (score → label) ──────────────────────────────────────────────
BANDS = [
    (0,   20,  "Strong Sell"),
    (20,  40,  "Sell"),
    (40,  55,  "Neutral"),
    (55,  80,  "Buy"),
    (80, 101,  "Strong Buy"),
]


#: Third state, borrowed verbatim from market_health / red_flags: a component we
#: could not measure is neither bullish nor bearish, and must not be scored as
#: either.
NOT_CHECKED = "NOT_CHECKED"


def _band_for(score: float) -> str:
    for lo, hi, label in BANDS:
        if lo <= score < hi:
            return label
    return "Neutral"


# ── DB persistence ────────────────────────────────────────────────────────────
def _ensure_table() -> None:
    with db.get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sentiment_history (
                reading_date TEXT PRIMARY KEY,
                score        REAL NOT NULL,
                band         TEXT NOT NULL,
                inputs_json  TEXT NOT NULL,
                created_at   TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def _persist(reading: dict[str, Any]) -> None:
    _ensure_table()
    with db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO sentiment_history (reading_date, score, band, inputs_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(reading_date) DO UPDATE SET
                score = excluded.score,
                band  = excluded.band,
                inputs_json = excluded.inputs_json
            """,
            (reading["reading_date"], reading["score"], reading["band"],
             json.dumps(reading["inputs"], default=float)),
        )


def history(days: int = 90) -> pd.DataFrame:
    """Return the last `days` calendar days of persisted sentiment readings."""
    _ensure_table()
    with db.get_connection() as conn:
        df = pd.read_sql(
            "SELECT reading_date, score, band, inputs_json "
            "FROM sentiment_history ORDER BY reading_date DESC LIMIT ?",
            conn, params=(days,),
        )
    if not df.empty:
        df["reading_date"] = pd.to_datetime(df["reading_date"])
        df = df.sort_values("reading_date").reset_index(drop=True)
    return df


# ── Input #1: Advance / Decline from bhavcopy ────────────────────────────────
def _advance_decline() -> dict[str, Any]:
    """Compute advance/decline ratio from most recent NSE bhavcopy. Returns a
    dict with raw counts, factor ∈ [0, 1], and a score contribution."""
    import requests
    from datetime import timedelta

    session = requests.Session()
    try:
        session.get("https://www.nseindia.com/", headers=sp.NSE_HEADERS, timeout=15)
    except Exception:
        pass

    df = None
    for days_back in range(1, 6):
        cand = datetime.today() - timedelta(days=days_back)
        if cand.weekday() >= 5:
            continue
        df = sp._fetch_bhav_df(session, cand)
        if df is not None:
            break
    if df is None:
        log.warning("A/D: no bhavcopy available")
        return {"reading": "n/a", "factor": 0.5, "score": 0.5 * W_ADV_DECL,
                "advances": 0, "declines": 0, "unchanged": 0}

    df.columns = [c.strip().upper() for c in df.columns]
    ser_col   = next((c for c in df.columns if c in ("SERIES", "SCTYSRS")), None)
    close_col = next((c for c in df.columns if c in ("CLOSE", "CLSPRIC")), None)
    prev_col  = next((c for c in df.columns
                      if c in ("PREVCLOSE", "PREV_CLOSE", "PRVSCLSGPRIC")), None)
    if not (close_col and prev_col):
        log.warning("A/D: bhavcopy missing close/prev columns (%s)", list(df.columns)[:20])
        return {"reading": "n/a", "factor": 0.5, "score": 0.5 * W_ADV_DECL,
                "advances": 0, "declines": 0, "unchanged": 0}

    if ser_col:
        df = df[df[ser_col].astype(str).str.strip() == "EQ"]
    df = df[[close_col, prev_col]].apply(pd.to_numeric, errors="coerce").dropna()
    df = df[df[prev_col] > 0]

    advances  = int((df[close_col] > df[prev_col]).sum())
    declines  = int((df[close_col] < df[prev_col]).sum())
    unchanged = int((df[close_col] == df[prev_col]).sum())
    total = advances + declines
    # Ratio in [0, 1]: 1.0 = every stock up, 0.5 = balanced, 0.0 = every stock down.
    factor = 0.5 if total == 0 else advances / total
    return {
        "reading": f"{advances} Adv vs {declines} Decl",
        "factor": round(factor, 4),
        "score":  round(factor * W_ADV_DECL, 2),
        "advances": advances, "declines": declines, "unchanged": unchanged,
    }


# ── Input #2: Sector performance (green vs red count) ────────────────────────
#: A sector bar older than this is not "today's participation", whatever else it
#: is. Six calendar days clears a long weekend plus a holiday without letting a
#: genuinely frozen feed through.
MAX_STALE_DAYS = 6

#: Coverage floor, matching market_health's 50% rule. Below this the component is
#: NOT_CHECKED and contributes nothing — it does not degrade to a neutral 0.5,
#: because a confident-looking 0.5 is exactly the failure this guards against.
COVERAGE_FLOOR = 0.5


def _sector_perf() -> dict[str, Any]:
    """1-day change for every distinct NIFTY sector index in
    ``sector_rotation.SECTOR_INDEX_MAP``. Factor = (green + 0.5*flat) / scored.

    Carries coverage, and refuses to score below a floor (backlog **B-1**).

    Why this needed more than a coverage counter
    --------------------------------------------
    The 2026-08-02 and 08-03 readings both scored sector participation over **3
    indices where an earlier reading used 11**, and the backlog assumed a flaky
    partial fetch. It is not flaky and it is not partial — **Yahoo stopped
    updating 8 of the 11 NSE sector indices on 2026-07-17** while ^CNXIT,
    ^CNXPHARMA and ^NSEBANK kept going (verified 2026-08-05: the 8 stale feeds
    all carry an identical last bar of 2026-07-17, 19 days old).

    That makes the survivors a **structurally biased subsample**, not a random
    one — and on 08-03 all three happened to be green, producing factor 1.0, a
    full 25/25, feeding the composite's bullish verdict.

    **RE-CHECKED 2026-09-10, and the first version of this correction was WRONG.**
    Scoping B-66 I fetched all 11 with ``period="max"``, saw current bars through
    2026-09-10 on every one, and wrote "the freeze ended". The running dashboard
    said otherwise on the same afternoon: *"only 3/11 sector indices usable"*.
    Both were true, and the difference is the parameter:

    ==================  ================  =========================================
    ``period=``         rows for ^CNXAUTO  what the shipped path sees
    ==================  ================  =========================================
    ``"1mo"`` (shipped) **1**              one bar -> ``len(hist) < 2`` -> SKIPPED
    ``"2mo"``           7                  July 10 .. Sep 10, heavily gapped
    ``"3mo"``           28                 of ~64 trading days
    ``"max"``           3,681              full history, last bar today
    ==================  ================  =========================================

    So: **the data is NOT frozen — every ticker's last bar is today — but the feed
    is SPARSE over the outage window, and ``period="1mo"`` returns a single row
    for the 8 affected indices.** The component has therefore been reporting
    NOT_CHECKED for weeks against a feed that was quietly recovering.

    **The fix is not simply a wider window.** With ``period="3mo"`` those tickers
    return two bars, but the previous one can be many sessions old, and computing
    a change across that gap and printing it as "today's move" is precisely the
    trap the paragraph above warns about. A correct fix widens the window AND
    bounds the GAP BETWEEN the two bars it uses, the way ``MAX_STALE_DAYS`` bounds
    the age of the last one. Not done here — it is a behaviour change to a live
    component and belongs in its own commit.

    The lesson, recorded because it is the second time in one session: **verifying
    through a different code path than the one that ships proves nothing about the
    one that ships.** Same shape as the PWA service-worker cache trap.

    The old code fetched ``period="10d"``, which for a frozen ticker returns a
    single stub row, so ``len(hist) < 2`` skipped it *silently*. That silence was
    the bug. Worse, the obvious "fix" — widening the window so more tickers
    return two bars — would have been actively harmful: it would compute a change
    between two **July** closes and present it as today's move. So the window is
    widened AND every bar is age-checked; stale and missing are reported apart,
    because "the feed froze" and "the fetch failed" call for different responses.
    """
    tickers = sorted(set(secrot.SECTOR_INDEX_MAP.values()))
    n_expected = len(tickers)
    today = datetime.today().date()

    greens, reds, flats = 0, 0, 0
    details: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []
    missing: list[str] = []

    for tkr in tickers:
        try:
            # 1mo, not 10d: a frozen ticker must return enough history for its
            # last bar to be VISIBLE and datable, rather than collapsing to one
            # stub row that looks indistinguishable from a fetch failure.
            hist = yf.Ticker(tkr).history(period="1mo", interval="1d", auto_adjust=False)
            if hist is None:
                missing.append(tkr)
                continue
            # Drop rows with NaN close — yfinance sometimes returns a stub row for
            # today with all-NaN values before session data is finalised.
            hist = hist.dropna(subset=["Close"])
            if len(hist) < 2:
                missing.append(tkr)
                continue

            last_date = hist.index[-1].date()
            age_days = (today - last_date).days
            if age_days > MAX_STALE_DAYS:
                stale.append({"ticker": tkr, "last_bar": last_date.isoformat(),
                              "age_days": age_days})
                continue

            prev, last = float(hist["Close"].iloc[-2]), float(hist["Close"].iloc[-1])
            chg_pct = (last / prev - 1) * 100 if prev > 0 else 0.0
            if chg_pct > 0.05:  flat = False; greens += 1; color = "green"
            elif chg_pct < -0.05: flat = False; reds += 1;  color = "red"
            else:                 flat = True;  flats += 1;  color = "flat"
            details.append({"ticker": tkr, "chg_pct": round(chg_pct, 2),
                            "color": color, "last_bar": last_date.isoformat()})
        except Exception as e:
            log.debug("Sector %s fetch failed: %s", tkr, e)
            missing.append(tkr)

    scored = greens + reds + flats
    coverage = scored / n_expected if n_expected else 0.0

    out: dict[str, Any] = {
        "n_expected": n_expected, "n_scored": scored,
        "coverage": round(coverage, 3),
        "n_stale": len(stale), "n_missing": len(missing),
        "stale": stale, "missing": missing,
        "greens": greens, "reds": reds, "flats": flats,
        "details": details,
    }

    if coverage < COVERAGE_FLOOR:
        why = []
        if stale:
            oldest = max(s["age_days"] for s in stale)
            why.append(f"{len(stale)} stale (up to {oldest}d old)")
        if missing:
            why.append(f"{len(missing)} unavailable")
        log.warning("sector participation NOT_CHECKED — only %d/%d indices usable (%s)",
                    scored, n_expected, "; ".join(why) or "no reason recorded")
        out.update({
            "state": NOT_CHECKED,
            "reading": (f"NOT CHECKED — only {scored}/{n_expected} sector indices "
                        f"usable ({'; '.join(why) or 'no usable data'})"),
            "factor": None,
            "score": 0.0,
        })
        return out

    factor = (greens + 0.5 * flats) / scored
    note = f"  ({scored}/{n_expected} indices"
    if stale or missing:
        note += f"; {len(stale)} stale, {len(missing)} unavailable"
    note += ")"
    out.update({
        "state": "OK",
        "reading": f"{greens} Green / {reds} Red / {flats} Flat{note}",
        "factor": round(factor, 4),
        "score":  round(factor * W_SECTOR, 2),
    })
    return out


# ── Input #3: NIFTY vs SMA200 (regime gauge) ─────────────────────────────────
def _regime_sma200() -> dict[str, Any]:
    """NIFTY close vs its 200-DMA. Factor centred on 1.0: at SMA=0.5, 5% above=1.0,
    5% below=0.0, linearly interpolated in between and clipped."""
    try:
        hist = yf.Ticker("^NSEI").history(period="14mo", interval="1d", auto_adjust=False)
        if hist is None:
            raise RuntimeError("no NIFTY history")
        # yfinance occasionally returns an all-NaN stub for today's incomplete
        # session — drop it so SMA200 doesn't inherit the NaN.
        hist = hist.dropna(subset=["Close"])
        if len(hist) < 210:
            raise RuntimeError("insufficient NIFTY history")
        close = hist["Close"].astype(float)
        sma200 = close.rolling(200).mean()
        last_close = float(close.iloc[-1])
        last_sma   = float(sma200.iloc[-1])
        if not np.isfinite(last_sma) or last_sma <= 0:
            raise RuntimeError("SMA200 unavailable")
        dist_pct = (last_close / last_sma - 1) * 100
        # Map ±5% distance → factor in [0, 1] centred at 0.5.
        factor = np.clip(0.5 + dist_pct / 10.0, 0.0, 1.0)
        return {
            "reading": (f"NIFTY {last_close:,.0f} vs SMA200 {last_sma:,.0f} "
                        f"({dist_pct:+.2f}%)"),
            "factor": round(float(factor), 4),
            "score":  round(float(factor) * W_REGIME, 2),
            "close": round(last_close, 2), "sma200": round(last_sma, 2),
            "dist_pct": round(dist_pct, 2),
        }
    except Exception as e:
        log.warning("Regime: %s", e)
        return {"reading": "n/a", "factor": 0.5, "score": 0.5 * W_REGIME,
                "close": None, "sma200": None, "dist_pct": None}


def _pmax_walk(ema, atr, atr_mult: float, warm: int):
    """The PMax ratchet, as a SERIES rather than a final reading.

    Extracted 2026-09-10 for B-65r, which needs the direction at every bar to
    score the factor rather than just today's value. The loop is unchanged, byte
    for byte, from the one that used to sit inline in
    `_pmax_direction_nifty_1h` — that function now calls this and takes the last
    element, so **there is one ratchet, not two**. A copy would have drifted from
    the factor it is supposed to be measuring, which is the failure mode
    `columns.py` (B-63a) exists to prevent and `psar_overlap.js` avoids by
    lifting `pmaxSeries` out of the chart instead of reimplementing it.

    Returns (direction, long_stop, short_stop) arrays. Bars before `warm` carry
    direction 0 — "not yet knowable" — rather than the seed value of 1, because a
    seeded direction is not a reading and must not enter a measurement.
    """
    import numpy as _np
    n = len(ema)
    dirs = _np.zeros(n, int)
    longs = _np.full(n, _np.nan)
    shorts = _np.full(n, _np.nan)
    long_prev = short_prev = None
    direction = 1
    for i in range(warm, n):
        a = atr[i]
        long_stop  = ema[i] - atr_mult * a
        short_stop = ema[i] + atr_mult * a
        if long_prev is not None and ema[i] > long_prev:
            long_stop = max(long_stop, long_prev)
        if short_prev is not None and ema[i] < short_prev:
            short_stop = min(short_stop, short_prev)
        if direction == -1 and ema[i] > (short_prev if short_prev is not None else short_stop):
            direction = 1
        elif direction == 1 and ema[i] < (long_prev if long_prev is not None else long_stop):
            direction = -1
        long_prev, short_prev = long_stop, short_stop
        dirs[i] = direction
        longs[i] = long_stop
        shorts[i] = short_stop
    return dirs, longs, shorts


# ── Input #4: PMax direction on NIFTY 1H ─────────────────────────────────────
def _pmax_direction_nifty_1h(atr_len: int = 10, atr_mult: float = 3.0,
                              ma_len: int = 10) -> dict[str, Any]:
    """Port of the PMax logic used by the chart tool (tools/pmax.pine +
    the JS `pmaxSeries` in chart_dashboard.html) applied to NIFTY 1H.
    Factor = 1.0 if PMax dir is up (bullish trend), 0.0 if down. When we have
    a fresh flip we can weight it more, but for Phase 1 the binary is fine."""
    try:
        hist = yf.Ticker("^NSEI").history(period="60d", interval="1h", auto_adjust=False)
        if hist is None:
            raise RuntimeError("no NIFTY 1h history")
        hist = hist.dropna(subset=["Close"])
        if len(hist) < 40:
            raise RuntimeError("insufficient NIFTY 1h history")
        high = hist["High"].astype(float).values
        low  = hist["Low"].astype(float).values
        close = hist["Close"].astype(float).values
        n = len(close)

        # Wilder ATR
        tr = np.zeros(n)
        tr[0] = high[0] - low[0]
        for i in range(1, n):
            tr[i] = max(high[i] - low[i],
                        abs(high[i] - close[i - 1]),
                        abs(low[i]  - close[i - 1]))
        atr = np.zeros(n)
        atr[atr_len - 1] = tr[:atr_len].mean()
        for i in range(atr_len, n):
            atr[i] = (atr[i - 1] * (atr_len - 1) + tr[i]) / atr_len

        # EMA of hl2
        src = (high + low) / 2
        alpha = 2 / (ma_len + 1)
        ema = np.zeros(n)
        ema[0] = src[0]
        for i in range(1, n):
            ema[i] = alpha * src[i] + (1 - alpha) * ema[i - 1]

        dirs, longs, shorts = _pmax_walk(ema, atr, atr_mult,
                                         warm=max(atr_len, ma_len))
        # dirs[-1] == 0 means the walk never ran (series shorter than warm-up).
        # The inline version this replaced fell through with its seed direction
        # of 1 and pmax None, so that case is reproduced exactly rather than
        # allowed to become a silent behaviour change in a refactor.
        if int(dirs[-1]) == 0:
            direction, long_prev, short_prev = 1, None, None
        else:
            direction = int(dirs[-1])
            long_prev, short_prev = float(longs[-1]), float(shorts[-1])

        factor = 1.0 if direction == 1 else 0.0
        pmax_val = long_prev if direction == 1 else short_prev
        return {
            "reading": ("Bullish (PMax up)" if direction == 1
                        else "Bearish (PMax down)"),
            "factor": factor,
            "score":  factor * W_PMAX_1H,
            "direction": int(direction),
            "last_close": round(float(close[-1]), 2),
            "pmax": round(float(pmax_val), 2) if pmax_val is not None else None,
        }
    except Exception as e:
        log.warning("PMax 1H: %s", e)
        return {"reading": "n/a", "factor": 0.5, "score": 0.5 * W_PMAX_1H,
                "direction": 0, "last_close": None, "pmax": None}


# ── Input #5: PCR level + slope on NIFTY ─────────────────────────────────────
#: Observations of NIFTY's own PCR required before the factor is scored at all.
#: `pcr.py` will not band an index without a time-series baseline, and this is
#: that baseline's floor. 60 is the roadmap's own number for the weight-fitting
#: step ("after a month of logged data" → ≥60 sessions), reused rather than
#: invented so there is one threshold in the design, not two.
MIN_PCR_HISTORY = 60

#: Level vs slope split inside factor 5. The roadmap specified "absolute +
#: direction blend" without numbers; level carries the standing posture and
#: slope the day's shift, and level is the steadier of the two, so it takes the
#: larger share. UNMEASURED, like the sign convention — recorded here so the
#: eventual test has something to vary.
PCR_LEVEL_SHARE = 0.7

#: Which way a high PCR reads. "trend_following" = high PCR is bullish.
#: See the module docstring: this is a guess, and B-44r is why that matters.
PCR_SIGN_CONVENTION = "trend_following"


def _ensure_pcr_table() -> None:
    with db.get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pcr_index_history (
                reading_date TEXT NOT NULL,
                symbol       TEXT NOT NULL,
                pcr          REAL NOT NULL,
                pcr_chg      REAL,
                total_oi     REAL,
                created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (reading_date, symbol)
            )
            """
        )


def _record_pcr(reading_date: str, rec: dict[str, Any]) -> None:
    """Append today's index PCR to the baseline. Idempotent per (date, symbol).

    Written on EVERY compute, including the long stretch where the factor itself
    is NOT_CHECKED — storing is what eventually makes scoring possible, so it
    must not be conditional on being able to score.
    """
    _ensure_pcr_table()
    with db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO pcr_index_history (reading_date, symbol, pcr, pcr_chg, total_oi)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(reading_date, symbol) DO UPDATE SET
                pcr = excluded.pcr,
                pcr_chg = excluded.pcr_chg,
                total_oi = excluded.total_oi
            """,
            (reading_date, rec["symbol"], float(rec["pcr"]),
             rec.get("pcr_chg"), rec.get("total_oi")),
        )


def pcr_history(symbol: str = "NIFTY", before: str | None = None) -> pd.DataFrame:
    """Stored PCR baseline for one index, oldest first.

    `before` excludes today's own row, so the percentile is taken against PRIOR
    sessions only. Ranking a value inside a sample that contains it is a small
    bias, but it is the kind that turns an extreme into a merely-high reading on
    exactly the days the factor is supposed to speak up.
    """
    _ensure_pcr_table()
    sql = "SELECT reading_date, pcr, pcr_chg FROM pcr_index_history WHERE symbol = ?"
    params: list[Any] = [symbol]
    if before is not None:
        sql += " AND reading_date < ?"
        params.append(before)
    sql += " ORDER BY reading_date"
    with db.get_connection() as conn:
        return pd.read_sql(sql, conn, params=params)


def _pct_rank(value: float | None, sample) -> float | None:
    """Where `value` sits in `sample`, 0-100. Mirrors `pcr.stock_percentile`'s
    strict-less-than convention so the two surfaces cannot disagree on what a
    percentile means."""
    if value is None or not np.isfinite(value):
        return None
    arr = np.asarray([v for v in sample if v is not None and np.isfinite(v)], dtype=float)
    if arr.size == 0:
        return None
    return float((arr < value).sum() / arr.size * 100.0)


def pcr_factor(pcr: float | None, pcr_chg: float | None,
               hist: pd.DataFrame) -> dict[str, Any]:
    """Pure calibration: today's NIFTY PCR against its own stored past.

    Kept separate from the fetch so it can be tested without a network call and
    without a database — the whole of the interesting behaviour (the history
    floor, the blend, the slope falling back to level-only) lives here.

    Factor = 0.7 × level-percentile + 0.3 × slope-percentile, each in [0, 1],
    under the trend-following convention that a high or rising PCR is bullish.
    When the slope percentile is unavailable (no `pcr_chg` today, or no stored
    `pcr_chg` history) the level carries the whole factor rather than the blend
    silently scoring a missing half as neutral.
    """
    n_hist = 0 if hist is None or hist.empty else int(len(hist))
    out: dict[str, Any] = {
        "pcr": round(float(pcr), 4) if pcr is not None and np.isfinite(pcr) else None,
        "pcr_chg": (round(float(pcr_chg), 4)
                    if pcr_chg is not None and np.isfinite(pcr_chg) else None),
        "n_history": n_hist,
        "min_history": MIN_PCR_HISTORY,
        "sign_convention": PCR_SIGN_CONVENTION,
        "convention_measured": False,
    }

    if pcr is None or not np.isfinite(pcr):
        out.update({
            "state": NOT_CHECKED, "factor": None, "score": 0.0,
            "reading": "NOT CHECKED — no NIFTY index PCR available today",
        })
        return out

    if n_hist < MIN_PCR_HISTORY:
        out.update({
            "state": NOT_CHECKED, "factor": None, "score": 0.0,
            "reading": (f"NOT CHECKED — PCR {pcr:.2f} recorded, but only {n_hist} of "
                        f"{MIN_PCR_HISTORY} baseline sessions stored; an index PCR "
                        f"can only be ranked against its own past"),
        })
        return out

    level_pct = _pct_rank(float(pcr), hist["pcr"].tolist())
    slope_pct = (_pct_rank(float(pcr_chg), hist["pcr_chg"].tolist())
                 if pcr_chg is not None and np.isfinite(pcr_chg) else None)

    if slope_pct is None:
        factor = level_pct / 100.0
        blend = "level only (no slope percentile available)"
    else:
        factor = (PCR_LEVEL_SHARE * level_pct
                  + (1 - PCR_LEVEL_SHARE) * slope_pct) / 100.0
        blend = f"{PCR_LEVEL_SHARE:.0%} level / {1 - PCR_LEVEL_SHARE:.0%} slope"

    factor = float(np.clip(factor, 0.0, 1.0))
    out.update({
        "state": "OK",
        "level_pct": round(level_pct, 1) if level_pct is not None else None,
        "slope_pct": round(slope_pct, 1) if slope_pct is not None else None,
        "blend": blend,
        "factor": round(factor, 4),
        "score": round(factor * W_PCR, 2),
        "reading": (f"NIFTY PCR {pcr:.2f} — {level_pct:.0f}th pct of {n_hist} sessions"
                    + (f", one-day change {pcr_chg:+.2f} ({slope_pct:.0f}th pct)"
                       if slope_pct is not None else "")),
    })
    return out


def _pcr_nifty(reading_date: str, symbol: str = "NIFTY",
               record: bool = True) -> dict[str, Any]:
    """Fetch today's index PCR via `pcr.py`, store it, then calibrate it.

    No new network call and no second PCR implementation: `pcr.load()` is the
    same primitive the OI-Momentum page already consumes, which was the whole
    point of building it there instead of inside either consumer.
    """
    base = {"state": NOT_CHECKED, "factor": None, "score": 0.0,
            "pcr": None, "pcr_chg": None, "n_history": 0,
            "min_history": MIN_PCR_HISTORY, "symbol": symbol,
            "sign_convention": PCR_SIGN_CONVENTION, "convention_measured": False}
    try:
        import pcr as pcr_mod
        loaded = pcr_mod.load()
        if not loaded.get("ok"):
            raise RuntimeError(loaded.get("reason", "pcr.load() failed"))
        rec = pcr_mod.index_reading(loaded["index"], symbol)
        if rec is None:
            raise RuntimeError(f"{symbol} absent from the index PCR table")
        if not rec.get("liquid"):
            # pcr.py already wrote the reason; do not re-word it.
            return {**base, "pcr": rec.get("pcr"), "pcr_chg": rec.get("pcr_chg"),
                    "reading": f"NOT CHECKED — {rec.get('band_reason', 'illiquid')}"}
        if record:
            # Gated on the caller's persist flag: --peek must not write, for the
            # same reason it does not write sentiment_history. A peek that
            # silently extended the baseline would make the baseline depend on
            # how often somebody looked at it.
            try:
                _record_pcr(reading_date, rec)
            except Exception as e:                   # storing is best-effort
                log.warning("PCR history write failed: %s", e)
        hist = pcr_history(symbol, before=reading_date)
        out = pcr_factor(rec.get("pcr"), rec.get("pcr_chg"), hist)
        out["symbol"] = symbol
        out["pcr_date"] = loaded.get("date")
        return out
    except Exception as e:
        log.warning("PCR factor: %s", e)
        return {**base, "reading": f"NOT CHECKED — {e}"}


# ── Composite ─────────────────────────────────────────────────────────────────
def compute_sentiment(persist: bool = True) -> dict[str, Any]:
    """Compute the composite sentiment reading and (by default) persist it to
    trading_bramha.db under `sentiment_history`. Idempotent per calendar day —
    same-day recomputes overwrite the previous row."""
    today   = date.today().isoformat()
    ad      = _advance_decline()
    sector  = _sector_perf()
    regime  = _regime_sma200()
    pmax_1h = _pmax_direction_nifty_1h()
    pcr_nif = _pcr_nifty(today, record=persist)

    components = (
        ("advance_decline",    W_ADV_DECL, ad),
        ("sector_performance", W_SECTOR,   sector),
        ("regime_sma200",      W_REGIME,   regime),
        ("pmax_nifty_1h",      W_PMAX_1H,  pmax_1h),
        ("pcr_nifty",          W_PCR,      pcr_nif),
    )

    # A NOT_CHECKED component is EXCLUDED and the remaining weights are
    # renormalised, rather than contributing a silent 0. Straight summation would
    # have dropped a 25-weight component to zero score and read as bearish — an
    # unmeasured input must not masquerade as a bearish measurement. The reading
    # then carries what fraction of the weight was actually measurable, so a
    # 75%-coverage score is never mistaken for a 100% one.
    measured = [(n, w, c) for n, w, c in components if c.get("state") != NOT_CHECKED]
    measured_weight = sum(w for _, w, _ in measured)
    total_weight = sum(w for _, w, _ in components)
    raw = sum(c["score"] for _, _, c in measured)

    if measured_weight <= 0:
        score, band = 0.0, NOT_CHECKED
    else:
        score = round(raw * total_weight / measured_weight, 2)
        coverage = measured_weight / total_weight
        # Same floor the components use. A composite built on under half its
        # weight is not a sentiment reading, it is a guess with a number on it.
        band = _band_for(score) if coverage >= COVERAGE_FLOOR else NOT_CHECKED

    excluded = [n for n, _, c in components if c.get("state") == NOT_CHECKED]
    if excluded:
        log.warning("sentiment computed on %d/%d weight — excluded: %s",
                    measured_weight, total_weight, ", ".join(excluded))

    reading = {
        "reading_date": today,
        "score": score,
        "band":  band,
        "weight_measured": measured_weight,
        "weight_total": total_weight,
        "coverage": round(measured_weight / total_weight, 3) if total_weight else 0.0,
        "excluded": excluded,
        "inputs": {
            "advance_decline":  {"weight": W_ADV_DECL, **ad},
            "sector_performance": {"weight": W_SECTOR, **sector},
            "regime_sma200":    {"weight": W_REGIME, **regime},
            "pmax_nifty_1h":    {"weight": W_PMAX_1H, **pmax_1h},
            "pcr_nifty":        {"weight": W_PCR,      **pcr_nif},
        },
    }
    if persist:
        try:
            _persist(reading)
        except Exception as e:
            log.warning("persist failed: %s", e)
    return reading


# ── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
                        datefmt="%H:%M:%S")
    persist = "--peek" not in sys.argv
    r = compute_sentiment(persist=persist)
    print(json.dumps(r, indent=2, default=float))
