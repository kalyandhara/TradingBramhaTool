#!/usr/bin/env python3
"""cvd_data_probe.py — can this desk compute a cumulative volume delta at all? (B-48)

B-48 has sat in the BUILD tier as *"answer the DATA question first, before any
indicator"*. This is that question, asked before a line of indicator is written.

── What CVD actually requires ────────────────────────────────────────────────
Cumulative volume delta sums **signed** volume: buy-initiated minus
sell-initiated. Deciding which side initiated a trade needs the trade printed
against the book — the aggressor side, or at minimum the bid/ask the trade
crossed. **The desk has none of that.** `intraday_store` holds OHLCV bars (5m,
15m, 1h); yfinance serves no tick stream and no bid/ask history. So a true CVD
is not computable here, and that is settled by the data rather than by effort.

What IS computable is a **proxy**: sign each bar's volume by the bar's own
direction. Every charting package that offers "CVD" on OHLC data is doing this,
usually without saying so.

── The question this probe decides ───────────────────────────────────────────
A proxy is worth having only if its answer is a property of the MARKET rather
than of the bar size you happen to hold. So, pre-committed before the run:

    PASS  the session's proxy CVD agrees in SIGN between 5-minute and 15-minute
          bars on **>= 90%** of symbol-sessions, and the two are correlated
          **>= 0.90** across sessions. Then the bar size is a display detail and
          an indicator can be built on it.
    FAIL  below either bar. Then "CVD" on this data is measuring the chart's
          resolution as much as the tape, and any indicator must carry its bar
          size as part of the SIGNAL rather than as a setting.

Two proxies are compared, because the choice between them is exactly the kind of
unstated decision this desk keeps finding inside inherited indicators:

    sign   up bar -> +volume, down bar -> -volume, doji -> 0   (close vs open)
    range  volume x (2 x (close - low) / (high - low) - 1)     (close's position
           in the bar's range; the Pine "buy pressure" convention)

CLI:
    py -3 -X utf8 tools/cvd_data_probe.py            # run against the store
"""
from __future__ import annotations

import io
import sys
from typing import Any

import numpy as np
import pandas as pd

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

#: Pre-committed pass bars. Written here before the first run, and quoted in
#: `analyses/CVD-Data-Probe`.
MIN_SIGN_AGREEMENT = 0.90
MIN_CORRELATION = 0.90

FINE, COARSE = "5m", "15m"


def signed_volume(df: pd.DataFrame, proxy: str = "sign") -> pd.Series:
    """Per-bar signed volume under one of the two proxies.

    Neither is order flow. Both are a guess about who was in a hurry, made from
    a bar that cannot say.
    """
    o, h, l, c = (df["open"].astype(float), df["high"].astype(float),
                  df["low"].astype(float), df["close"].astype(float))
    v = df["volume"].astype(float)
    if proxy == "sign":
        return v * np.sign(c - o)
    if proxy == "range":
        rng = (h - l).replace(0, np.nan)
        # 2*(c-l)/rng - 1 maps a close at the low to -1 and at the high to +1.
        frac = (2.0 * (c - l) / rng - 1.0).fillna(0.0)
        return v * frac
    raise ValueError(f"unknown proxy {proxy!r}")


def session_cvd(df: pd.DataFrame, proxy: str = "sign") -> pd.Series:
    """One signed-volume total per session, indexed by date."""
    if df is None or df.empty:
        return pd.Series(dtype=float)
    sv = signed_volume(df, proxy)
    return sv.groupby(df.index.date).sum()


def compare(fine: pd.DataFrame, coarse: pd.DataFrame,
            proxy: str = "sign") -> dict[str, Any]:
    """Session CVD from fine vs coarse bars, over the sessions they share."""
    a, b = session_cvd(fine, proxy), session_cvd(coarse, proxy)
    both = pd.concat([a.rename("fine"), b.rename("coarse")], axis=1).dropna()
    if len(both) < 5:
        return {"n_sessions": int(len(both)), "sign_agreement": None,
                "correlation": None}
    same = np.sign(both["fine"]) == np.sign(both["coarse"])
    # Normalised magnitude gap: how much of the fine-bar total survives the
    # coarser bars, when they agree on the side at all.
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = (both["coarse"].abs() / both["fine"].abs().replace(0, np.nan))
    return {
        "n_sessions": int(len(both)),
        "sign_agreement": float(same.mean()),
        "correlation": float(both["fine"].corr(both["coarse"])),
        "median_magnitude_ratio": float(ratio.median(skipna=True)),
        "flip_sessions": int((~same).sum()),
    }


def has_volume(df: pd.DataFrame) -> bool:
    """False for a series with no volume at all — an index quote, typically.

    Caught in the first run: `^NSEI` has no volume, so every signed total is
    zero, every session "agrees" on sign trivially, and it contributed 87
    sessions of free 100% to the pooled number. A symbol that cannot have a
    volume delta must not be counted as evidence that volume deltas are stable.
    """
    return df is not None and not df.empty and float(df["volume"].abs().sum()) > 0


def run(symbols: list[str], read_bars, proxies=("sign", "range")) -> dict[str, Any]:
    out: dict[str, Any] = {"per_symbol": {}, "proxies": {}, "no_volume": []}
    pooled = {p: {"agree": 0, "n": 0, "fine": [], "coarse": []} for p in proxies}

    for sym in symbols:
        fine, coarse = read_bars(sym, FINE), read_bars(sym, COARSE)
        if fine is None or coarse is None or fine.empty or coarse.empty:
            continue
        if not (has_volume(fine) and has_volume(coarse)):
            out["no_volume"].append(sym)
            continue
        row = {}
        for p in proxies:
            row[p] = compare(fine, coarse, p)
            a, b = session_cvd(fine, p), session_cvd(coarse, p)
            both = pd.concat([a.rename("f"), b.rename("c")], axis=1).dropna()
            pooled[p]["fine"] += both["f"].tolist()
            pooled[p]["coarse"] += both["c"].tolist()
            pooled[p]["agree"] += int((np.sign(both["f"]) == np.sign(both["c"])).sum())
            pooled[p]["n"] += len(both)
        out["per_symbol"][sym] = row

    for p in proxies:
        f = np.array(pooled[p]["fine"], float)
        c = np.array(pooled[p]["coarse"], float)
        n = pooled[p]["n"]
        out["proxies"][p] = {
            "n_symbol_sessions": n,
            "sign_agreement": (pooled[p]["agree"] / n) if n else None,
            "correlation": (float(np.corrcoef(f, c)[0, 1])
                            if n > 2 and f.std() and c.std() else None),
        }

    # The two proxies against EACH OTHER on the same bars: if they disagree, the
    # unstated choice between them is doing the work, not the data.
    out["proxy_agreement"] = _proxy_agreement(symbols, read_bars, proxies)
    out["verdict"] = verdict(out)
    return out


def _proxy_agreement(symbols, read_bars, proxies) -> dict[str, Any]:
    if len(proxies) < 2:
        return {}
    p1, p2 = proxies[0], proxies[1]
    agree = n = 0
    for sym in symbols:
        fine = read_bars(sym, FINE)
        if not has_volume(fine):
            continue
        a, b = session_cvd(fine, p1), session_cvd(fine, p2)
        both = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
        agree += int((np.sign(both["a"]) == np.sign(both["b"])).sum())
        n += len(both)
    return {"pair": f"{p1} vs {p2}", "n_symbol_sessions": n,
            "sign_agreement": (agree / n) if n else None}


def verdict(res: dict[str, Any]) -> str:
    """The pre-committed bar, applied mechanically."""
    m = (res.get("proxies") or {}).get("sign") or {}
    agree, corr = m.get("sign_agreement"), m.get("correlation")
    if agree is None or corr is None:
        return "INCOMPLETE — not enough overlapping sessions"
    if agree >= MIN_SIGN_AGREEMENT and corr >= MIN_CORRELATION:
        return (f"PASS — proxy CVD survives the bar size "
                f"({agree:.0%} sign agreement, r={corr:.2f})")
    return (f"FAIL — proxy CVD depends on the bar size "
            f"({agree:.0%} sign agreement, r={corr:.2f}); "
            f"bars are {MIN_SIGN_AGREEMENT:.0%} and {MIN_CORRELATION:.2f}")


def report(res: dict[str, Any]) -> str:
    L = ["CVD data probe (B-48) — 5m vs 15m session delta, same store, same sessions", ""]
    L.append(f"{'proxy':>7}{'symbol-sessions':>18}{'sign agree':>13}{'corr':>8}")
    for p, m in res["proxies"].items():
        a = "n/a" if m["sign_agreement"] is None else f"{m['sign_agreement']:.1%}"
        c = "n/a" if m["correlation"] is None else f"{m['correlation']:.2f}"
        L.append(f"{p:>7}{m['n_symbol_sessions']:>18}{a:>13}{c:>8}")
    pa = res.get("proxy_agreement") or {}
    if pa.get("sign_agreement") is not None:
        L += ["", f"the two proxies against each other on the SAME 5m bars: "
                  f"{pa['sign_agreement']:.1%} sign agreement over "
                  f"{pa['n_symbol_sessions']} symbol-sessions"]
    if res.get("no_volume"):
        L += ["", "excluded (no volume — an index quote cannot have a delta): "
                  + ", ".join(res["no_volume"])]
    L += ["", "per symbol (sign proxy):"]
    for sym, row in res["per_symbol"].items():
        m = row["sign"]
        if m["sign_agreement"] is None:
            L.append(f"  {sym:<14} too few sessions")
            continue
        L.append(f"  {sym:<14} {m['n_sessions']:>3} sessions · "
                 f"{m['sign_agreement']:.0%} agree · r={m['correlation']:.2f} · "
                 f"{m['flip_sessions']} sign flips · "
                 f"15m keeps {m['median_magnitude_ratio']:.2f}x the 5m magnitude")
    L += ["", f"VERDICT: {res['verdict']}"]
    return "\n".join(L)


def main() -> int:
    import intraday_store as istore

    cov = istore.coverage()
    symbols = sorted({r["symbol"] for _, r in cov.iterrows()
                      if r["interval"] in (FINE, COARSE)})
    res = run(symbols, lambda s, i: istore.read_bars(s, i))
    print(report(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
