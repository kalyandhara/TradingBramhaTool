"""event_study.py — did NIFTY and the NSE sector indices move abnormally on
policy event days, compared with ordinary days?

Spec: docs/superpowers/specs/2026-10-26-policy-event-study-design.md

A measuring instrument, not a signal: every study run through it is
pre-registered on the wiki first, and a null result is calibration. The library
does no file or network I/O of its own except through the loaders, which take
injectable callables so the tests never touch the network.
"""
from __future__ import annotations

import logging
import warnings
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

MARKET = "^NSEI"
#: The 12 non-market series. ^CNXMEDIA is excluded: Yahoo serves one bar of it
#: (probed 2026-10-26), against 2010-11 starts for everything below.
SECTORS: list[str] = ["^NSEBANK", "^CNXIT", "^CNXPHARMA", "^CNXFMCG", "^CNXMETAL",
                      "^CNXINFRA", "^CNXREALTY", "^CNXENERGY", "^CNXAUTO",
                      "^CNXPSUBANK", "^CNXPSE", "NIFTY_FIN_SERVICE.NS"]
#: Rate-sensitive basket for the MPC directional tests (equal-weighted).
BASKET: list[str] = ["^NSEBANK", "^CNXPSUBANK", "^CNXREALTY", "^CNXAUTO",
                     "NIFTY_FIN_SERVICE.NS"]
DEFAULT_CACHE = Path(__file__).resolve().parent / "cache" / "event_study"

#: Allowed labels per event type. A label outside these is an error, not a
#: silently new bucket — a typo would otherwise become its own tiny sample.
EVENT_LABELS: dict[str, set[str]] = {
    "mpc": {"cut", "hike", "hold"},
    "budget": {"full", "interim"},
}

EVENT_COLUMNS = ["date", "event_type", "label", "scheduled", "time_ist",
                 "source_url", "notes"]


# --------------------------------------------------------------------------- #
# Events
# --------------------------------------------------------------------------- #

def load_events(path, types: list[str] | None = None,
                scheduled_only: bool = True) -> pd.DataFrame:
    """Read and validate the events CSV; validation runs on the whole file, so a
    bad row is caught even when it would have been filtered out."""
    df = pd.read_csv(Path(path), dtype=str, keep_default_na=False)
    missing = [c for c in EVENT_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"events file missing columns: {missing}")
    df = df[EVENT_COLUMNS].copy()
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    df["scheduled"] = df["scheduled"].astype(int)

    for _, r in df.iterrows():
        allowed = EVENT_LABELS.get(r["event_type"])
        if allowed is None:
            raise ValueError(f"unknown event_type {r['event_type']!r} on {r['date'].date()}")
        if r["label"] not in allowed:
            raise ValueError(f"unknown label {r['label']!r} for {r['event_type']} "
                             f"on {r['date'].date()}")
    dup = df.duplicated(["date", "event_type"], keep=False)
    if dup.any():
        raise ValueError("duplicate (date, event_type): "
                         + ", ".join(str(d.date()) for d in df.loc[dup, "date"].unique()))

    if types is not None:
        df = df[df["event_type"].isin(types)]
    if scheduled_only:
        df = df[df["scheduled"] == 1]
    return df.sort_values("date").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Prices
# --------------------------------------------------------------------------- #

def _yahoo_download(tickers: list[str], start: str) -> pd.DataFrame:
    import yfinance as yf
    return yf.download(tickers, start=start, interval="1d", auto_adjust=True,
                       group_by="ticker", progress=False, threads=True)


def _close_frame(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Wide Close frame from whatever shape yfinance returned."""
    if isinstance(raw.columns, pd.MultiIndex):
        lv0 = raw.columns.get_level_values(0)
        out = {t: raw[(t, "Close")] for t in tickers if (t, "Close") in raw.columns}
        if not out and "Close" in lv0:            # (field, ticker) layout
            out = {t: raw[("Close", t)] for t in tickers if ("Close", t) in raw.columns}
    else:                                         # single ticker, flat columns
        out = {tickers[0]: raw["Close"]} if "Close" in raw.columns else {}
    df = pd.DataFrame(out)
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df.sort_index()


def _last_weekday_before(today: pd.Timestamp) -> pd.Timestamp:
    d = today.normalize() - pd.Timedelta(days=1)
    while d.weekday() >= 5:
        d -= pd.Timedelta(days=1)
    return d


def load_closes(tickers: list[str], start: str, download=None,
                cache_dir: Path | None = None, min_obs: int = 250,
                today: pd.Timestamp | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Wide close frame (NaN where a series has no bar) and the omitted tickers.

    The cache is reused only while it reaches the last weekday before `today`,
    so a stale cache silently shortening the sample cannot happen. A ticker with
    fewer than `min_obs` closes is omitted — it cannot carry an estimation
    window — and the caller reports it."""
    cache_dir = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE
    today = pd.Timestamp.today() if today is None else pd.Timestamp(today)
    cache = cache_dir / f"closes_{start}.csv"
    df = None
    if cache.exists():
        cached = pd.read_csv(cache, index_col=0, parse_dates=True)
        if (set(tickers) <= set(cached.columns)
                and cached.index.max() >= _last_weekday_before(today)):
            df = cached[tickers]
    if df is None:
        download = download or _yahoo_download
        df = _close_frame(download(tickers, start), tickers)
        df = df.reindex(columns=tickers)
        cache_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache)
    counts = df.notna().sum()
    omitted = [t for t in tickers if counts.get(t, 0) < min_obs]
    for t in omitted:
        log.warning("event_study: omitting %s (%d closes < %d)", t, counts.get(t, 0), min_obs)
    return df.drop(columns=omitted), omitted


#: NSE all-indices file names per ticker: current name first, then the pre-2016
#: "CNX" name. Yahoo's closes equal NSE's to the paisa (checked 2026-10-23, all 13).
NSE_NAMES: dict[str, tuple[str, ...]] = {
    "^NSEI": ("Nifty 50", "CNX Nifty"), "^NSEBANK": ("Nifty Bank", "CNX Bank"),
    "^CNXIT": ("Nifty IT", "CNX IT"), "^CNXPHARMA": ("Nifty Pharma", "CNX Pharma"),
    "^CNXFMCG": ("Nifty FMCG", "CNX FMCG"), "^CNXMETAL": ("Nifty Metal", "CNX Metal"),
    "^CNXINFRA": ("Nifty Infrastructure", "CNX Infrastructure"),
    "^CNXREALTY": ("Nifty Realty", "CNX Realty"), "^CNXENERGY": ("Nifty Energy", "CNX Energy"),
    "^CNXAUTO": ("Nifty Auto", "CNX Auto"), "^CNXPSUBANK": ("Nifty PSU Bank", "CNX PSU Bank"),
    "^CNXPSE": ("Nifty PSE", "CNX PSE"),
    "NIFTY_FIN_SERVICE.NS": ("Nifty Financial Services", "CNX Finance"),
}


def _nse_fetch_any_day(day):
    """NSE's all-indices file for exactly `day`, weekends included (special
    budget sessions). sector_rotation.fetch_nse_index_closes skips weekends by
    design, so this asks for the file directly; it shares that disk cache."""
    import io
    import requests
    import sector_rotation as sr
    cached = sr._nse_index_cache(day)
    if cached.exists():
        return pd.read_csv(cached)
    r = requests.get(sr.NSE_INDEX_CLOSE_URL.format(ddmmyyyy=day.strftime("%d%m%Y")),
                     headers=sr.NSE_HEADERS, timeout=20)
    if r.status_code != 200 or len(r.content) < 500 or b"Index Name" not in r.content[:2000]:
        return None
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(r.content)
    return pd.read_csv(io.BytesIO(r.content))


def patch_sessions(closes: pd.DataFrame, dates: pd.Series,
                   fetch=None) -> tuple[pd.DataFrame, list[pd.Timestamp]]:
    """Insert NSE closes for event dates Yahoo has no bar for.

    Yahoo never printed the special budget sessions (Sat 2015-02-28, Sat
    2020-02-01, Sun 2026-02-01) nor 2014-02-17. Snapping those to the next
    session would make d0 a two-session return — ~sqrt(2) larger, inflating a
    magnitude test — so the real session is restored instead. A row that exists
    with NIFTY missing (2014-02-17) is gap-filled; Yahoo's own values are kept. A date NSE has no
    file for was not a trading day and is left for snap_to_sessions."""
    fetch = fetch or _nse_fetch_any_day
    out = closes.copy()
    patched = []
    have = set(out.index[out[MARKET].notna()].normalize()) if MARKET in out else set()
    for d in sorted(set(pd.to_datetime(pd.Series(dates)).dt.normalize())):
        if d in have:                       # NIFTY printed that day: nothing to restore
            continue
        nse = fetch(d.date())
        if nse is None:
            continue
        vals = dict(zip(nse["Index Name"], pd.to_numeric(nse["Closing Index Value"],
                                                         errors="coerce")))
        row = {}
        for t in out.columns:
            for name in NSE_NAMES.get(t, ()):
                if name in vals and not np.isnan(vals[name]):
                    row[t] = float(vals[name])
                    break
        if MARKET not in row:
            continue
        if d in out.index:                  # row exists (other series printed): fill gaps only
            for t, v in row.items():
                if pd.isna(out.at[d, t]):
                    out.at[d, t] = v
        else:
            out.loc[d] = pd.Series(row)
        patched.append(d)
    return out.sort_index(), patched


def pair_returns(closes: pd.DataFrame, ticker: str, market: str = MARKET) -> pd.DataFrame:
    """Log returns of `ticker` (r) and the market (m) on the dates BOTH printed.

    A day either series is missing is dropped before differencing, so a gap
    becomes one multi-day return, never a forward-filled zero."""
    both = closes[[ticker, market]].dropna()
    lr = np.log(both).diff().dropna()
    return lr.rename(columns={ticker: "r", market: "m"})


def snap_to_sessions(dates: pd.Series, index: pd.DatetimeIndex) -> tuple[np.ndarray, np.ndarray]:
    """Position of the first session on or after each date (-1 past the end),
    and whether that session differs from the date (a Saturday budget, say)."""
    d = pd.to_datetime(pd.Series(dates)).dt.normalize().to_numpy()
    pos = index.searchsorted(d, side="left")
    snapped = np.zeros(len(d), dtype=bool)
    out = np.full(len(d), -1, dtype=int)
    for i, p in enumerate(pos):
        if p < len(index):
            out[i] = p
            snapped[i] = index[p] != pd.Timestamp(d[i])
    return out, snapped


# --------------------------------------------------------------------------- #
# Abnormal returns
# --------------------------------------------------------------------------- #

#: Trading days relative to d0 (the session containing the announcement).
WINDOWS: dict[str, tuple[int, int]] = {"pre": (-5, -1), "day": (0, 0),
                                       "post": (1, 5), "drift": (0, 20)}
SPAN = (-5, 20)
EST = (-250, -11)
MIN_EST_OBS = 120


def market_model_ar(pr: pd.DataFrame, d0_pos: int, est: tuple[int, int] = EST,
                    min_obs: int = MIN_EST_OBS, model: str = "market") -> pd.Series | None:
    """Abnormal returns over SPAN, indexed by relative day (days past the data are
    absent). `pr` is pair_returns(); `d0_pos` a position in pr's own index.

    market: OLS of r on m over the estimation window; adjusted: beta 1, alpha 0
    (the sensitivity check). None when the estimation window is too short —
    both models require it, so the two never disagree about the sample."""
    lo, hi = max(0, d0_pos + est[0]), d0_pos + est[1] + 1
    if hi - lo < min_obs:
        return None
    if model == "market":
        beta, alpha = np.polyfit(pr["m"].to_numpy()[lo:hi], pr["r"].to_numpy()[lo:hi], 1)
    elif model == "adjusted":
        beta, alpha = 1.0, 0.0
    else:
        raise ValueError(f"unknown model {model!r}")
    s_lo, s_hi = max(0, d0_pos + SPAN[0]), min(len(pr), d0_pos + SPAN[1] + 1)
    seg = pr.iloc[s_lo:s_hi]
    ar = seg["r"].to_numpy() - (alpha + beta * seg["m"].to_numpy())
    return pd.Series(ar, index=np.arange(s_lo, s_hi) - d0_pos)


def _window_sum(s: pd.Series, w: tuple[int, int]) -> float | None:
    """Cumulative value over a window, or None if any day of it is missing."""
    days = range(w[0], w[1] + 1)
    if not all(d in s.index for d in days):
        return None
    return float(s.loc[list(days)].sum())


def event_ar_table(closes: pd.DataFrame, events: pd.DataFrame,
                   sectors: list[str] = SECTORS,
                   windows: dict[str, tuple[int, int]] = WINDOWS,
                   model: str = "market") -> pd.DataFrame:
    """Long table: one row per (event, ticker, window) with the cumulative AR
    (`car`). MARKET rows hold the raw NIFTY log return over the window.

    d0 is snapped on the market's own sessions; a sector missing that session
    takes its next printed one. A window running past the data is omitted for
    that event only — the shorter windows keep it."""
    mkt = closes[MARKET].dropna()
    mkt_r = np.log(mkt).diff().dropna()
    pos, snapped = snap_to_sessions(events["date"], mkt_r.index)
    rows = []
    pairs = {t: pair_returns(closes, t) for t in sectors if t in closes.columns}
    for (_, ev), p, sn in zip(events.iterrows(), pos, snapped):
        if p < 0:
            continue
        d0 = mkt_r.index[p]
        base = {"event_date": ev["date"], "event_type": ev["event_type"],
                "label": ev["label"], "snapped": bool(sn), "session": d0}
        raw = pd.Series(mkt_r.to_numpy()[max(0, p + SPAN[0]):p + SPAN[1] + 1],
                        index=np.arange(max(0, p + SPAN[0]),
                                        min(len(mkt_r), p + SPAN[1] + 1)) - p)
        for wname, w in windows.items():
            v = _window_sum(raw, w)
            if v is not None:
                rows.append({**base, "ticker": MARKET, "window": wname, "car": v})
        for t, pr in pairs.items():
            q = int(pr.index.searchsorted(d0, side="left"))
            if q >= len(pr):
                continue
            ar = market_model_ar(pr, q, model=model)
            if ar is None:
                continue
            for wname, w in windows.items():
                v = _window_sum(ar, w)
                if v is not None:
                    rows.append({**base, "ticker": t, "window": wname, "car": v})
    cols = ["event_date", "event_type", "label", "snapped", "session",
            "ticker", "window", "car"]
    return pd.DataFrame(rows, columns=cols)


# --------------------------------------------------------------------------- #
# Nulls, corrections, intervals
# --------------------------------------------------------------------------- #

def candidate_positions(index: pd.DatetimeIndex, event_pos: np.ndarray, exclude: int = 10,
                        years: set[int] | None = None, months: set[int] | None = None,
                        margin: tuple[int, int] = (250, 20)) -> np.ndarray:
    """Positions eligible as pseudo-events for Null A: not within +/-`exclude` of
    any real event, inside `years`/`months` when given, and with room for an
    estimation window before and the drift window after."""
    n = len(index)
    ok = np.zeros(n, dtype=bool)
    ok[margin[0]:max(margin[0], n - margin[1])] = True
    for e in np.asarray(event_pos, dtype=int):
        if e >= 0:
            ok[max(0, e - exclude):min(n, e + exclude + 1)] = False
    if years is not None:
        ok &= np.isin(index.year, list(years))
    if months is not None:
        ok &= np.isin(index.month, list(months))
    return np.flatnonzero(ok)


def date_null(stat_fn, candidates: np.ndarray, n_events: int, draws: int = 10_000,
              seed: int = 7) -> np.ndarray:
    """Null A: the statistic recomputed on `draws` sets of `n_events` pseudo-event
    positions drawn without replacement from `candidates`."""
    return np.array([stat_fn(row) for row in draw_matrix(candidates, n_events, draws, seed)],
                    dtype=float)


def draw_matrix(candidates: np.ndarray, n_events: int, draws: int = 10_000,
                seed: int = 7) -> np.ndarray:
    """The pseudo-event position sets behind Null A, one sorted row per draw.
    Exposed so many statistics can share one set of draws, vectorised."""
    rng = np.random.default_rng(seed)
    cand = np.asarray(candidates)
    if len(cand) < n_events:
        raise ValueError(f"only {len(cand)} candidate days for {n_events} events")
    return np.sort(np.stack([rng.choice(cand, n_events, replace=False)
                             for _ in range(draws)]), axis=1)


def p_greater(real: float, null: np.ndarray) -> float:
    """One-sided p with the +1 correction; for a 'less' hypothesis negate both."""
    null = np.asarray(null, dtype=float)
    return float((1 + np.sum(null >= real)) / (1 + len(null)))


def label_permutation(values: np.ndarray, labels: np.ndarray, a: str = "cut",
                      b: str = "hike", draws: int = 10_000,
                      seed: int = 7) -> tuple[float, np.ndarray]:
    """Null C: mean(a) - mean(b) with the a/b labels shuffled, sizes preserved."""
    values, labels = np.asarray(values, float), np.asarray(labels)
    keep = np.isin(labels, [a, b])
    v, lab = values[keep], labels[keep] == a
    real = float(v[lab].mean() - v[~lab].mean())
    rng = np.random.default_rng(seed)
    null = np.empty(draws)
    for i in range(draws):
        perm = rng.permutation(lab)
        null[i] = v[perm].mean() - v[~perm].mean()
    return real, null


def bootstrap_ci(values: np.ndarray, stat=np.mean, reps: int = 5_000,
                 level: float = 0.90, seed: int = 7) -> tuple[float, float]:
    """Percentile bootstrap CI over events."""
    v = np.asarray(values, float)
    rng = np.random.default_rng(seed)
    boots = np.array([stat(rng.choice(v, len(v), replace=True)) for _ in range(reps)])
    tail = (1 - level) / 2
    return float(np.quantile(boots, tail)), float(np.quantile(boots, 1 - tail))


def holm(p) -> np.ndarray:
    """Holm step-down adjusted p-values, original order, capped at 1."""
    p = np.asarray(p, float)
    m = len(p)
    order = np.argsort(p)
    adj = np.maximum.accumulate((m - np.arange(m)) * p[order])
    out = np.empty(m)
    out[order] = np.minimum(adj, 1.0)
    return out


def bh(p) -> np.ndarray:
    """Benjamini-Hochberg adjusted p-values (q), original order, capped at 1."""
    p = np.asarray(p, float)
    m = len(p)
    order = np.argsort(p)
    ranked = p[order] * m / np.arange(1, m + 1)
    adj = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(m)
    out[order] = np.minimum(adj, 1.0)
    return out


# --------------------------------------------------------------------------- #
# The study
# --------------------------------------------------------------------------- #

NA_SMALL = "n/a (n<5)"
MIN_BUCKET = 5
MIN_SECTORS_DISP = 6        # a dispersion needs at least this many sectors that day
MIN_BASKET = 3              # a basket mean needs at least this many members that day


@dataclass
class StudyConfig:
    draws: int = 10_000
    seed: int = 7
    boot: int = 5_000
    exclude: int = 10
    split: str = "2019-01-01"
    calendar_match: dict = field(default_factory=lambda: {"mpc": False, "budget": True})


def _rolling_ar(pr: pd.DataFrame, model: str) -> pd.Series:
    """Day-0 abnormal return for EVERY row of a pair, each with its own
    estimation window [-250, -11] — what market_model_ar gives for one d0,
    vectorised so the null can draw any day."""
    if model == "adjusted":
        return pr["r"] - pr["m"]
    span = EST[1] - EST[0] + 1
    lag = -EST[1]                                   # window ends 11 rows before d0
    roll = pr.rolling(span, min_periods=MIN_EST_OBS)
    mean = roll.mean()
    cov = pr["r"].rolling(span, min_periods=MIN_EST_OBS).cov(pr["m"])
    beta = cov / roll.var()["m"]
    alpha = mean["r"] - beta * mean["m"]
    return pr["r"] - (alpha.shift(lag) + beta.shift(lag) * pr["m"])


class _Panel:
    """Everything a statistic needs, as arrays on the market's session index."""

    def __init__(self, closes: pd.DataFrame, model: str = "market"):
        mkt = closes[MARKET].dropna()
        self.mkt_r = np.log(mkt).diff().dropna()
        self.index = self.mkt_r.index
        self.sectors = [t for t in SECTORS if t in closes.columns]
        self.ar = pd.DataFrame({t: _rolling_ar(pair_returns(closes, t), model).reindex(self.index)
                                for t in self.sectors}, index=self.index)
        a = self.ar.to_numpy()
        with _quiet():
            disp = np.nanstd(a, axis=1, ddof=1)
            b = self.ar[[t for t in BASKET if t in self.ar.columns]].to_numpy()
            bmean = np.nanmean(b, axis=1)
        self.disp = np.where(np.sum(~np.isnan(a), axis=1) >= MIN_SECTORS_DISP, disp, np.nan)
        self.basket = np.where(np.sum(~np.isnan(b), axis=1) >= MIN_BASKET, bmean, np.nan)
        self.abs_mkt = np.abs(self.mkt_r.to_numpy())

    @staticmethod
    def window_values(base: np.ndarray, w: tuple[int, int]) -> np.ndarray:
        """Sum of `base` over [pos+w0, pos+w1] for every pos (NaN past the edges
        or where any day in the window is missing)."""
        width = w[1] - w[0] + 1
        return (pd.Series(base).rolling(width, min_periods=width).sum()
                .shift(-w[1]).to_numpy())


@contextmanager
def _quiet():
    """All-NaN rows are expected (a sector before its series starts); numpy's
    'mean of empty slice' warning about them is noise."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        yield


def _nanmean_rows(vals: np.ndarray, M: np.ndarray) -> np.ndarray:
    with _quiet():
        return np.nanmean(vals[M], axis=1)


def _na_row(test, set_, n):
    return {"test": test, "set": set_, "n": int(n), "real": None, "null_mean": None,
            "ratio": None, "p": NA_SMALL, "p_adj": None, "ci_lo": None, "ci_hi": None}


def _test_row(test, set_, vals, pos, M, cfg, sign=1.0):
    """Real statistic (mean over events, NaN events dropped) against the same
    statistic on each Null A draw. sign=-1 tests 'less than' by negation."""
    v = vals[pos]
    v = v[~np.isnan(v)]
    if len(v) < MIN_BUCKET:
        return _na_row(test, set_, len(v))
    real = float(v.mean())
    null = _nanmean_rows(vals, M)
    nm = float(np.nanmean(null))
    lo, hi = bootstrap_ci(v, reps=cfg.boot, seed=cfg.seed)
    return {"test": test, "set": set_, "n": int(len(v)), "real": real, "null_mean": nm,
            "ratio": real / nm if nm != 0 and not np.isnan(nm) else None,
            "p": p_greater(sign * real, sign * null), "p_adj": None,
            "ci_lo": lo, "ci_hi": hi}


def _set_null(panel, set_pos_all, years, months, n, cfg, seed_offset=0):
    cand = candidate_positions(panel.index, set_pos_all, exclude=cfg.exclude,
                               years=years, months=months)
    return draw_matrix(cand, n, cfg.draws, cfg.seed + seed_offset)


def _verdicts(primary, split_half, secondary) -> list[str]:
    """Spec section 3.4, applied mechanically."""
    out = []
    for set_ in sorted({r["set"] for r in primary}):
        promoted = None
        for r in (x for x in primary if x["set"] == set_):
            if not isinstance(r["p_adj"], float) or r["ratio"] is None:
                continue
            halves = [h for h in split_half if h["set"] == set_ and h["test"] == r["test"]]
            robust = len(halves) == 2 and all(
                isinstance(h["p"], float) and h["p"] < 0.10
                and h["ratio"] is not None and h["ratio"] >= 1.2 for h in halves)
            if r["p_adj"] < 0.05 and r["ratio"] >= 1.3 and robust:
                promoted = r
                break
        if promoted:
            out.append(f"PROMOTE: {set_} policy days are volatility events "
                       f"({promoted['test']} ratio {promoted['ratio']:.2f}x)")
        else:
            out.append(f"CALIBRATION: {set_} magnitude - no promotable effect")
    if secondary:
        s = {r["test"]: r for r in secondary}
        ok = (isinstance(s["S3"]["p"], float) and s["S3"]["p"] < 0.05
              and s["S1"]["real"] is not None and s["S1"]["real"] > 0
              and s["S2"]["real"] is not None and s["S2"]["real"] < 0)
        out.append("PROMOTE: MPC directional tilt (decision-conditional - not tradeable "
                   "before the announcement)" if ok
                   else "CALIBRATION: mpc directional - no promotable effect")
    return out


def _clean(o):
    """JSON-safe: numpy scalars to Python, NaN to None, Timestamps to ISO dates."""
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [_clean(v) for v in o]
    if isinstance(o, pd.Timestamp):
        return o.date().isoformat()
    if isinstance(o, (np.bool_, bool)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if np.isnan(o) else float(o)
    return o


def _directional(panel, e, e_all, years, cfg) -> list[dict]:
    rows = []
    for test, lab, sign, off in (("S1", "cut", 1.0, 2), ("S2", "hike", -1.0, 3)):
        bp = e.loc[e["label"] == lab, "pos"].to_numpy()
        if len(bp) < MIN_BUCKET:
            rows.append(_na_row(test, "mpc", len(bp)))
            continue
        BM = _set_null(panel, e_all["pos"].to_numpy(), years, None, len(bp), cfg, off)
        rows.append(_test_row(test, "mpc", panel.basket, bp, BM, cfg, sign=sign))
    ch = e[e["label"].isin(["cut", "hike"])]
    vals = panel.basket[ch["pos"].to_numpy()]
    keep = ~np.isnan(vals)
    labs = ch["label"].to_numpy()[keep]
    if min((labs == "cut").sum(), (labs == "hike").sum()) < MIN_BUCKET:
        rows.append(_na_row("S3", "mpc", keep.sum()))
    else:
        real, null = label_permutation(vals[keep], labs, draws=cfg.draws, seed=cfg.seed)
        rows.append({"test": "S3", "set": "mpc", "n": int(keep.sum()), "real": real,
                     "null_mean": float(null.mean()), "ratio": None,
                     "p": p_greater(real, null), "p_adj": None, "ci_lo": None, "ci_hi": None})
    return rows


def _exploratory(panel, set_, pos, M, cfg) -> list[dict]:
    """Per ticker x window: |CAR| and signed CAR (both tails), BH within the set.
    Multi-day windows here sum each day's own rolling-model AR — exploratory only."""
    bases = {MARKET: panel.mkt_r.to_numpy(),
             **{t: panel.ar[t].to_numpy() for t in panel.sectors}}
    rows = []
    for t, base in bases.items():
        for wname, w in WINDOWS.items():
            car = panel.window_values(base, w)
            for stat, vals, sgn in (("abs", np.abs(car), 1.0), ("up", car, 1.0),
                                    ("down", car, -1.0)):
                rows.append(_test_row(f"{t}|{wname}|{stat}", set_, vals, pos, M, cfg, sign=sgn))
    ps = [r["p"] for r in rows if isinstance(r["p"], float)]
    qs = iter(bh(ps)) if ps else iter(())
    for r in rows:
        if isinstance(r["p"], float):
            r["p_adj"] = float(next(qs))
    return rows


def run_study(closes: pd.DataFrame, events: pd.DataFrame, cfg: StudyConfig | None = None,
              omitted: list[str] | None = None,
              patched: list[pd.Timestamp] | None = None) -> dict:
    """Run the pre-registered tests (spec section 3); returns a JSON-safe dict.

    `events` may hold scheduled and unscheduled rows: only scheduled rows are
    tested, unscheduled ones are listed under `unscheduled`. Real and null
    statistics are read from the same per-session arrays, so they can differ
    only in WHICH days they look at."""
    cfg = cfg or StudyConfig()
    panel, adj = _Panel(closes, "market"), _Panel(closes, "adjusted")
    pos_all, snapped = snap_to_sessions(events["date"], panel.index)
    ev = events.assign(pos=pos_all, snapped=snapped)
    ev = ev[ev["pos"] >= 0]
    split = pd.Timestamp(cfg.split)

    primary, secondary, split_half = [], [], []
    sensitivity, exploratory, unscheduled = [], [], []
    for set_ in sorted(ev["event_type"].unique()):
        e_all = ev[ev["event_type"] == set_]
        e = e_all[e_all["scheduled"] == 1]
        if e.empty:
            continue
        pos = e["pos"].to_numpy()
        all_pos = e_all["pos"].to_numpy()
        years = set(panel.index[pos].year)
        months = set(panel.index[pos].month) if cfg.calendar_match.get(set_) else None
        M = _set_null(panel, all_pos, years, months, len(pos), cfg)

        primary.append(_test_row("P1", set_, panel.abs_mkt, pos, M, cfg))
        primary.append(_test_row("P2", set_, panel.disp, pos, M, cfg))
        sensitivity.append(_test_row("P2-adjusted", set_, adj.disp, pos, M, cfg))
        if set_ == "mpc":
            sensitivity.append(_test_row("basket-adjusted|cut", set_, adj.basket,
                                         e.loc[e["label"] == "cut", "pos"].to_numpy(), M, cfg))

        for half, mask in ((f"before {cfg.split}", panel.index[pos] < split),
                           (f"from {cfg.split}", panel.index[pos] >= split)):
            hp = pos[mask]
            if len(hp) < MIN_BUCKET:
                split_half += [{"test": t, "set": set_, "half": half, "n": int(len(hp)),
                                "p": NA_SMALL, "ratio": None} for t in ("P1", "P2")]
                continue
            HM = _set_null(panel, all_pos, set(panel.index[hp].year), months, len(hp), cfg, 1)
            for t, vals in (("P1", panel.abs_mkt), ("P2", panel.disp)):
                r = _test_row(t, set_, vals, hp, HM, cfg)
                split_half.append({"test": t, "set": set_, "half": half, "n": r["n"],
                                   "p": r["p"], "ratio": r["ratio"]})

        if set_ == "mpc":
            secondary = _directional(panel, e, e_all, years, cfg)
        exploratory += _exploratory(panel, set_, pos, M, cfg)

        for _, u in e_all[e_all["scheduled"] == 0].iterrows():
            p = int(u["pos"])
            unscheduled.append({"set": set_, "date": u["date"], "label": u["label"],
                                "nifty_abs": panel.abs_mkt[p], "dispersion": panel.disp[p],
                                "basket_ar": panel.basket[p]})

    ps = [r["p"] for r in primary if isinstance(r["p"], float)]
    holm_p = iter(holm(ps)) if ps else iter(())
    for r in primary:
        if isinstance(r["p"], float):
            r["p_adj"] = float(next(holm_p))

    sched = ev[ev["scheduled"] == 1]
    meta = {"config": asdict(cfg), "omitted": list(omitted or []),
            "patched": list(patched or []),
            "sample": [panel.index[0], panel.index[-1]], "sectors": panel.sectors,
            "events": {s: int(n) for s, n in sched["event_type"].value_counts().sort_index().items()},
            "labels": {f"{s}:{l}": int(n) for (s, l), n
                       in sched.groupby(["event_type", "label"]).size().items()},
            "snapped": [d for d, s in zip(ev["date"], ev["snapped"]) if s]}
    return _clean({"meta": meta, "primary": primary, "secondary": secondary,
                   "split_half": split_half, "sensitivity": sensitivity,
                   "exploratory": exploratory, "unscheduled": unscheduled,
                   "verdicts": _verdicts(primary, split_half, secondary)})


def _fmt(v, nd=4):
    if v is None:
        return "–"
    if isinstance(v, (str, int)):
        return str(v)
    return f"{v:.{nd}f}"


def render_markdown(result: dict) -> str:
    m = result["meta"]
    L = [f"# Policy Event Study — {', '.join(m['events'])}", "",
         f"- Sample: {m['sample'][0]} .. {m['sample'][1]}",
         f"- Scheduled events: {m['events']} · labels: {m['labels']}",
         f"- Sectors: {len(m['sectors'])} · omitted: {m['omitted'] or 'none'}",
         f"- Sessions patched from NSE (missing on Yahoo): {m.get('patched') or 'none'}",
         f"- Snapped to next session: {m['snapped'] or 'none'}",
         f"- Null A: {m['config']['draws']} matched random-date draws, exclusion "
         f"+/-{m['config']['exclude']} days, seed {m['config']['seed']}, "
         f"calendar-matched {m['config']['calendar_match']}", ""]

    def table(title, rows, cols):
        L.extend([f"## {title}", "", "| " + " | ".join(cols) + " |",
                  "|" + "|".join("---" for _ in cols) + "|"])
        L.extend("| " + " | ".join(_fmt(r.get(c)) for c in cols) + " |" for r in rows)
        L.append("")

    std = ["test", "set", "n", "real", "null_mean", "ratio", "p", "p_adj", "ci_lo", "ci_hi"]
    table("Primary (Holm, family alpha 0.05)", result["primary"], std)
    table("Split half", result["split_half"], ["test", "set", "half", "n", "ratio", "p"])
    if result["secondary"]:
        table("Secondary — MPC directional (raw p)", result["secondary"], std)
    table("Sensitivity — beta = 1", result["sensitivity"], std)
    if result["unscheduled"]:
        table("Unscheduled moves (not tested)", result["unscheduled"],
              ["set", "date", "label", "nifty_abs", "dispersion", "basket_ar"])
    L.extend(["## Verdicts", ""] + [f"- {v}" for v in result["verdicts"]] + [""])
    top = sorted((r for r in result["exploratory"] if isinstance(r["p_adj"], float)),
                 key=lambda r: r["p_adj"])[:15]
    table("Exploratory — 15 smallest BH q (no claims)", top, std)
    return "\n".join(L)
