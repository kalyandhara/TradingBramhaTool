"""choch_scan.py — Bullish CHoCH screener (fresh change of character).

Finds stocks whose structure flipped from bearish to bullish within the last
N sessions: a daily close above the most recent confirmed swing high while
structure was bearish (the first counter-trend break). Same SMC swing walk as
`scanner_templates.detect_bos_choch`, but it keeps EVERY bullish CHoCH, so a
CHoCH followed by a BOS inside the window is still caught (the stock-level
`detect_bos_choch` would only report the later BOS).

A CHoCH is dropped if a later close breaks below a confirmed swing low
(structure flipped back bearish = failed CHoCH).

Usage:
    py -3 tools/choch_scan.py                      # Nifty 500, last 5 sessions
    py -3 tools/choch_scan.py --days 3 --pivot 15
    py -3 tools/choch_scan.py --universe totalmarket --displacement
    py -3 tools/choch_scan.py --symbols TCS,INFY,RELIANCE

Writes tools/cache/choch_scan_<ts>.csv and prints the table.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from breakout_scan import download_history  # noqa: E402

UNIVERSES = {
    "nifty500": HERE / "cache" / "nse_nifty500_constituents.json",
    "totalmarket": HERE / "cache" / "nse_niftytotalmarket_constituents.json",
}


def _body_ratio(o: float, h: float, l: float, c: float) -> float:
    rng = h - l
    return abs(c - o) / rng if rng > 0 else 0.0


def bullish_choch(df: pd.DataFrame, pivot_len: int = 5, lookback: int = 150,
                  within: int = 5, require_displacement: bool = False,
                  min_body_ratio: float = 0.5) -> dict | None:
    """Most recent surviving bullish CHoCH within the last `within` sessions."""
    n = len(df)
    if n < pivot_len * 4 + 20:
        return None
    h, l, c, o = (df[k].to_numpy(float) for k in ("high", "low", "close", "open"))
    swing_high = swing_low = None
    trend = 0
    choch = None   # (bar, level, leg_low, body_ratio)
    post_bos = 0
    for i in range(max(pivot_len * 2, n - lookback), n):
        j = i - pivot_len
        if j >= pivot_len:
            win_h = h[j - pivot_len: j + pivot_len + 1]
            win_l = l[j - pivot_len: j + pivot_len + 1]
            if h[j] == win_h.max():
                swing_high = float(h[j])
            if l[j] == win_l.min():
                swing_low = float(l[j])
        if swing_high is not None and c[i] > swing_high:
            br = _body_ratio(o[i], h[i], l[i], c[i])
            if require_displacement and br < min_body_ratio:
                continue
            if trend != 1:
                choch, post_bos = (i, swing_high, swing_low, br), 0
            else:
                post_bos += 1
            trend = 1
            swing_high = None
        elif swing_low is not None and c[i] < swing_low:
            trend, swing_low, choch = -1, None, None   # failed / bearish again
    if choch is None:
        return None
    idx, level, leg_low, br = choch
    bars_ago = n - 1 - idx
    if bars_ago > within - 1:
        return None
    last = float(c[-1])
    out = {
        "choch_date": pd.Timestamp(df.index[idx]).date().isoformat(),
        "bars_ago": bars_ago,
        "broken_level": round(level, 2),
        "close": round(last, 2),
        "pct_above_level": round((last / level - 1) * 100, 2),
        "body_ratio": round(float(br), 2),
        "displacement": bool(br >= min_body_ratio),
        "bos_after": post_bos,
        "leg_low": round(leg_low, 2) if leg_low else None,
    }
    if "volume" in df:
        v = df["volume"].to_numpy(float)
        base = v[max(0, idx - 20):idx].mean() if idx > 0 else 0
        out["break_rvol"] = round(float(v[idx] / base), 2) if base else None
    if leg_low:
        rng = level - leg_low
        out["ote_zone"] = f"{level - 0.79 * rng:.2f}-{level - 0.618 * rng:.2f}"
        out["risk_pct"] = round((last / leg_low - 1) * 100, 2)
    return out


def scan(frames: dict[str, pd.DataFrame], meta: dict[str, dict], **kw) -> pd.DataFrame:
    rows = []
    for sym, df in frames.items():
        try:
            r = bullish_choch(df, **kw)
        except Exception:
            r = None
        if r:
            rows.append({"symbol": sym, "industry": meta.get(sym, {}).get("industry", ""), **r})
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    return out.sort_values(["bars_ago", "displacement", "break_rvol"],
                           ascending=[True, False, False]).reset_index(drop=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--universe", choices=UNIVERSES, default="nifty500")
    p.add_argument("--symbols", help="comma list, overrides --universe")
    p.add_argument("--days", type=int, default=5, help="CHoCH within last N sessions")
    p.add_argument("--pivot", type=int, default=5, help="swing pivot length")
    p.add_argument("--displacement", action="store_true",
                   help="require strong-body break candle (ICT MSS)")
    a = p.parse_args()

    if a.symbols:
        meta = {s.strip().upper(): {} for s in a.symbols.split(",")}
    else:
        meta = {d["symbol"]: d for d in json.loads(UNIVERSES[a.universe].read_text())}
    syms = list(meta)
    print(f"Downloading {len(syms)} symbols…", file=sys.stderr)
    frames = download_history(syms, period="2y")
    res = scan(frames, meta, pivot_len=a.pivot, within=a.days,
               require_displacement=a.displacement)
    if res.empty:
        print("No bullish CHoCH found.")
        return
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M")
    path = HERE / "cache" / f"choch_scan_{ts}.csv"
    res.to_csv(path, index=False)
    with pd.option_context("display.max_rows", 500, "display.width", 200):
        print(res.to_string(index=False))
    print(f"\n{len(res)} stocks | saved {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
