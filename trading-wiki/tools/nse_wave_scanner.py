"""
NSE Top-Volume Multi-Setup Scanner
====================================

Run after market close to:
  1. Pull the top-N stocks by traded volume (full-market bhavcopy for N>20,
     NSE's "Most Active Securities" feed for N<=20).
  2. Fetch daily OHLC history for each via yfinance.
  3. Compute McDowell's OWL histogram (EMA(low,5) - EMA(low,35)), PTF RSI(9, 80/20
     bands), ATR(14), and EMA(21/50/200).
  4. Flag candidates for:
       - Flat Bottom Channel Breakout (Wave 3 entry, EW)
       - Wave 4 retracement -> Wave 5 catch (EW)
       - VCP (volatility-contraction base, lite heuristic)
       - ATR volatility breakout
       - EMA 21/50 cross (short-term momentum cross)
       - Golden/Death Cross (EMA 50/200)

See:
  trading-wiki/wiki/concepts/Elliott-Wave.md
  trading-wiki/wiki/concepts/McDowell-Probability-Matrix.md
  trading-wiki/wiki/strategies/EW-Flat-Bottom-Breakout.md
  trading-wiki/wiki/strategies/EW-Wave5-Catch.md
  trading-wiki/wiki/concepts/VCP.md
  trading-wiki/wiki/concepts/EMA.md
  trading-wiki/wiki/concepts/PMax.md (ATR usage)

Usage:
  py nse_wave_scanner.py [--top 10] [--lookback-base 20] [--lookback-swing 90]

Output is a shortlist printed to the console. This is a *candidate filter only* —
confirm setups manually (and score EW counts with the McDowell Probability Matrix)
before acting.
"""

import argparse
import io
import sys
import time
from datetime import date, timedelta

import pandas as pd
import requests
import yfinance as yf

NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}

NSE_VOLUME_URL = "https://www.nseindia.com/api/live-analysis-most-active-securities?index=volume"
NSE_BHAVCOPY_URL = "https://archives.nseindia.com/products/content/sec_bhavdata_full_{ds}.csv"


def fetch_top_volume_small(n=10):
    """Return the top-n NSE symbols by traded volume via the 'Most Active Securities'
    feed. This feed is capped at ~20 symbols by NSE, so use fetch_top_volume_bhavcopy
    for larger n."""
    session = requests.Session()
    session.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=10)
    resp = session.get(NSE_VOLUME_URL, headers=NSE_HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()["data"]
    data = sorted(data, key=lambda row: row["totalTradedVolume"], reverse=True)
    return [row["symbol"] for row in data[:n]]


def fetch_top_volume_bhavcopy(n=100, max_days_back=6):
    """Return the top-n NSE EQ symbols by traded volume from the latest available
    full bhavcopy CSV (covers the whole cash market, not just the top ~20)."""
    for i in range(max_days_back):
        ds = (date.today() - timedelta(days=i)).strftime("%d%m%Y")
        url = NSE_BHAVCOPY_URL.format(ds=ds)
        resp = requests.get(url, headers=NSE_HEADERS, timeout=15)
        if resp.status_code == 200 and len(resp.content) > 1000:
            df = pd.read_csv(io.StringIO(resp.text))
            df.columns = [c.strip() for c in df.columns]
            df["SERIES"] = df["SERIES"].str.strip()
            df = df[df["SERIES"] == "EQ"]
            df = df.sort_values("TTL_TRD_QNTY", ascending=False)
            return df["SYMBOL"].str.strip().head(n).tolist()
    raise RuntimeError("No bhavcopy CSV found in the last few days")


def fetch_top_volume(n=10):
    """Return the top-n NSE symbols by traded volume (cash market).
    Uses the small live feed for n <= 20, falls back to the full bhavcopy for larger n."""
    if n <= 20:
        return fetch_top_volume_small(n)
    return fetch_top_volume_bhavcopy(n)


def fetch_ohlc(symbol, period="2y", interval="1d"):
    """Fetch daily OHLC for an NSE symbol via yfinance (.NS suffix)."""
    df = yf.download(f"{symbol}.NS", period=period, interval=interval, progress=False)
    if df.empty:
        return df
    # yfinance returns MultiIndex columns for a single ticker in newer versions
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def compute_owl(df, short=5, long=35):
    """McDowell OWL: EMA(low, short) - EMA(low, long), as a histogram."""
    ema_short = df["Low"].ewm(span=short, adjust=False).mean()
    ema_long = df["Low"].ewm(span=long, adjust=False).mean()
    return ema_short - ema_long


def compute_rsi(df, length=9):
    """Wilder's RSI on close, for the PTF (80/20 band-penetration) read."""
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_atr(df, length=14):
    """Wilder's ATR."""
    prev_close = df["Close"].shift(1)
    tr = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - prev_close).abs(),
            (df["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / length, adjust=False).mean()


def compute_ema(df, length):
    return df["Close"].ewm(span=length, adjust=False).mean()


def detect_vcp_lite(df, base_window=50, lookback_recent=5, final_range_pct_max=10.0, near_pivot_pct=5.0):
    """
    Lite VCP heuristic (see concepts/VCP.md for the full 3-tier algorithm):
      - split the base_window bars before the most recent lookback_recent bars
        into 3 equal chunks
      - flag if each chunk's high-low range (% of midpoint) is smaller than the last
        (volatility contraction) and the final chunk's range <= final_range_pct_max
      - flag only if the latest close is within near_pivot_pct of the base high
        (i.e. price sitting at/near the pivot, not already broken out or far below)
    """
    total_needed = base_window + lookback_recent
    if len(df) < total_needed:
        return None

    base = df.iloc[-total_needed:-lookback_recent]
    n = len(base)
    chunk = n // 3
    if chunk < 3:
        return None

    chunks = [base.iloc[:chunk], base.iloc[chunk:2 * chunk], base.iloc[2 * chunk:]]

    def range_pct(c):
        high, low = c["High"].max(), c["Low"].min()
        mid = (high + low) / 2
        return (high - low) / mid * 100

    ranges = [range_pct(c) for c in chunks]
    contracting = ranges[0] > ranges[1] > ranges[2]
    final_tight = ranges[2] <= final_range_pct_max

    base_high = base["High"].max()
    latest = df.iloc[-1]
    near_pivot = abs(latest["Close"] - base_high) / base_high <= near_pivot_pct / 100

    if contracting and final_tight and near_pivot:
        return {
            "setup": "VCP-Lite",
            "contraction_pct": [round(float(r), 2) for r in ranges],
            "base_high": round(base_high, 2),
            "close": round(latest["Close"], 2),
            "rsi": round(latest["rsi"], 1),
        }
    return None


def detect_atr_breakout(df, lookback=20, atr_mult=1.5):
    """
    Flag a volatility breakout:
      - latest close exceeds the highest high of the prior `lookback` bars
      - and the day's move (close - prev close) exceeds atr_mult * ATR(14)
    """
    if len(df) < lookback + 2:
        return None

    prior = df.iloc[-(lookback + 1):-1]
    prior_high = prior["High"].max()

    latest = df.iloc[-1]
    prev = df.iloc[-2]
    move = latest["Close"] - prev["Close"]
    atr = latest["atr"]

    if latest["Close"] > prior_high and atr > 0 and move > atr_mult * atr:
        return {
            "setup": "ATR-Breakout",
            "prior_high": round(prior_high, 2),
            "close": round(latest["Close"], 2),
            "move": round(move, 2),
            "atr": round(atr, 2),
            "move_atr_ratio": round(move / atr, 2),
            "rsi": round(latest["rsi"], 1),
        }
    return None


def detect_ema_cross(df, fast=21, slow=50, lookback=3):
    """
    Flag a fresh EMA(fast) / EMA(slow) crossover within the last `lookback` bars.
    """
    if len(df) < slow + lookback + 2:
        return None

    diff = df["ema_fast"] - df["ema_slow"]
    for i in range(1, lookback + 1):
        prev_diff = diff.iloc[-i - 1]
        cur_diff = diff.iloc[-i]
        if prev_diff <= 0 and cur_diff > 0:
            direction = "Bullish"
            break
        if prev_diff >= 0 and cur_diff < 0:
            direction = "Bearish"
            break
    else:
        return None

    latest = df.iloc[-1]
    return {
        "setup": "EMA-Cross",
        "direction": direction,
        "fast": fast,
        "slow": slow,
        "bars_ago": i,
        "close": round(latest["Close"], 2),
        "rsi": round(latest["rsi"], 1),
    }


def detect_golden_cross(df, fast=50, slow=200, lookback=5):
    """
    Flag a fresh Golden Cross (EMA50 crosses above EMA200) or Death Cross
    (EMA50 crosses below EMA200) within the last `lookback` bars.
    """
    if len(df) < slow + lookback + 2:
        return None

    diff = df["ema50"] - df["ema200"]
    for i in range(1, lookback + 1):
        prev_diff = diff.iloc[-i - 1]
        cur_diff = diff.iloc[-i]
        if prev_diff <= 0 and cur_diff > 0:
            direction = "Golden Cross"
            break
        if prev_diff >= 0 and cur_diff < 0:
            direction = "Death Cross"
            break
    else:
        return None

    latest = df.iloc[-1]
    return {
        "setup": "Golden-Death-Cross",
        "direction": direction,
        "bars_ago": i,
        "close": round(latest["Close"], 2),
        "rsi": round(latest["rsi"], 1),
    }


def detect_flat_bottom_breakout(df, lookback_base=20, max_range_pct=8.0):
    """
    Flag a Flat Bottom Channel Breakout (Wave 3 entry) candidate:
      - the lookback_base bars before the latest bar formed a narrow horizontal
        channel (high-low range as % of channel midpoint <= max_range_pct)
      - latest close breaks above that channel's resistance (high)
      - OWL histogram is positive on the latest bar
    """
    if len(df) < lookback_base + 2:
        return None

    base = df.iloc[-(lookback_base + 1):-1]
    resistance = base["High"].max()
    support = base["Low"].min()
    midpoint = (resistance + support) / 2
    range_pct = (resistance - support) / midpoint * 100

    latest = df.iloc[-1]
    breakout = latest["Close"] > resistance
    owl_positive = latest["owl"] > 0

    if range_pct <= max_range_pct and breakout and owl_positive:
        return {
            "setup": "Flat-Bottom-Breakout",
            "channel_range_pct": round(range_pct, 2),
            "resistance": round(resistance, 2),
            "close": round(latest["Close"], 2),
            "owl": round(latest["owl"], 4),
            "rsi": round(latest["rsi"], 1),
        }
    return None


def detect_wave5_catch(df, lookback_swing=90, retrace_low=0.382, retrace_high=0.764):
    """
    Flag a Wave 4 retracement -> Wave 5 catch candidate:
      - find the highest high in the last lookback_swing bars (candidate Wave 3 top)
      - find the lowest low before that high, within the same window (candidate Wave 2 low)
      - check the current close's retracement of that Wave2->Wave3 leg falls in
        the 38.2-76.4% zone (per the EW-Wave5-Catch / re-labeling rule)
      - OWL histogram turning positive (latest > previous bar), i.e. bullish flip
    """
    if len(df) < lookback_swing + 2:
        return None

    window = df.iloc[-lookback_swing:]
    wave3_idx = window["High"].idxmax()
    wave3_high = window.loc[wave3_idx, "High"]

    pre_wave3 = window.loc[:wave3_idx]
    if len(pre_wave3) < 2:
        return None
    wave2_idx = pre_wave3["Low"].idxmin()
    wave2_low = pre_wave3.loc[wave2_idx, "Low"]

    leg = wave3_high - wave2_low
    if leg <= 0:
        return None

    latest = df.iloc[-1]
    prev = df.iloc[-2]
    retrace_pct = (wave3_high - latest["Close"]) / leg

    owl_flip = latest["owl"] > 0 and prev["owl"] <= 0

    if retrace_low <= retrace_pct <= retrace_high and owl_flip:
        wave5_target_low = wave3_high + 0.618 * leg
        wave5_target_high = wave3_high + 1.0 * leg
        return {
            "setup": "Wave5-Catch",
            "wave3_high": round(wave3_high, 2),
            "wave2_low": round(wave2_low, 2),
            "retrace_pct": round(retrace_pct * 100, 1),
            "wave5_target_low": round(wave5_target_low, 2),
            "wave5_target_high": round(wave5_target_high, 2),
            "close": round(latest["Close"], 2),
            "owl": round(latest["owl"], 4),
            "rsi": round(latest["rsi"], 1),
        }
    return None


def scan(symbols, lookback_base, lookback_swing):
    results = []
    for symbol in symbols:
        try:
            df = fetch_ohlc(symbol)
            min_bars = max(lookback_base, lookback_swing, 200) + 2
            if df.empty or len(df) < min_bars:
                # still try the shorter-lookback setups if we have enough for those
                if df.empty or len(df) < max(lookback_base, lookback_swing) + 2:
                    print(f"  {symbol}: insufficient data, skipping")
                    continue

            df["owl"] = compute_owl(df)
            df["rsi"] = compute_rsi(df)
            df["atr"] = compute_atr(df)
            df["ema_fast"] = compute_ema(df, 21)
            df["ema_slow"] = compute_ema(df, 50)
            df["ema50"] = df["ema_slow"]
            df["ema200"] = compute_ema(df, 200)

            hits = [
                detect_flat_bottom_breakout(df, lookback_base),
                detect_wave5_catch(df, lookback_swing),
                detect_vcp_lite(df),
                detect_atr_breakout(df),
                detect_ema_cross(df),
                detect_golden_cross(df),
            ]
            hits = [h for h in hits if h]

            for hit in hits:
                hit["symbol"] = symbol
                results.append(hit)

            if not hits:
                print(f"  {symbol}: no setup")

        except Exception as exc:
            print(f"  {symbol}: error ({exc})")

        time.sleep(0.5)  # be polite to data providers

    return results


def main():
    parser = argparse.ArgumentParser(description="NSE top-volume Elliott Wave scanner")
    parser.add_argument("--top", type=int, default=10, help="number of top-volume symbols to scan")
    parser.add_argument("--lookback-base", type=int, default=20, help="bars for flat-bottom base channel")
    parser.add_argument("--lookback-swing", type=int, default=90, help="bars for wave2->wave3 swing detection")
    args = parser.parse_args()

    print(f"Fetching top {args.top} NSE symbols by traded volume...")
    try:
        symbols = fetch_top_volume(args.top)
    except Exception as exc:
        print(f"Failed to fetch top-volume list: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Symbols:", ", ".join(symbols))
    print()
    print("Scanning for setups (EW Wave3/Wave5, VCP, ATR breakout, EMA cross, Golden/Death cross)...")
    results = scan(symbols, args.lookback_base, args.lookback_swing)

    print()
    if not results:
        print("No setups found in today's top-volume list.")
        return

    print(f"=== Shortlist ({len(results)} candidate(s)) ===")
    for r in results:
        if r["setup"] == "Flat-Bottom-Breakout":
            print(
                f"\n{r['symbol']}: Flat Bottom Channel Breakout (Wave 3 entry)\n"
                f"  channel range: {r['channel_range_pct']}% | resistance broken: {r['resistance']}\n"
                f"  close: {r['close']} | OWL: {r['owl']} | RSI(9): {r['rsi']}\n"
                f"  -> verify base quality + score with McDowell Probability Matrix before entry"
            )
        elif r["setup"] == "Wave5-Catch":
            print(
                f"\n{r['symbol']}: Wave 4 Retracement -> Wave 5 Catch\n"
                f"  Wave2 low: {r['wave2_low']} | Wave3 high: {r['wave3_high']}\n"
                f"  retrace of Wave3: {r['retrace_pct']}% (zone 38.2-76.4%)\n"
                f"  close: {r['close']} | OWL: {r['owl']} | RSI(9): {r['rsi']}\n"
                f"  Wave5 target zone: {r['wave5_target_low']} - {r['wave5_target_high']}\n"
                f"  -> wait for higher-low/higher-high confirmation, verify with MPM"
            )
        elif r["setup"] == "VCP-Lite":
            print(
                f"\n{r['symbol']}: VCP (volatility contraction, lite heuristic)\n"
                f"  contraction stages (range % of midpoint): {r['contraction_pct']}\n"
                f"  base high (pivot): {r['base_high']} | close: {r['close']} | RSI(9): {r['rsi']}\n"
                f"  -> watch for breakout above base high on rising volume (see concepts/VCP.md)"
            )
        elif r["setup"] == "ATR-Breakout":
            print(
                f"\n{r['symbol']}: ATR Volatility Breakout\n"
                f"  prior {args.lookback_base}-bar high: {r['prior_high']} | close: {r['close']}\n"
                f"  move: {r['move']} ({r['move_atr_ratio']}x ATR14={r['atr']}) | RSI(9): {r['rsi']}\n"
                f"  -> fresh expansion above range; confirm volume before chasing"
            )
        elif r["setup"] == "EMA-Cross":
            print(
                f"\n{r['symbol']}: {r['direction']} EMA{r['fast']}/EMA{r['slow']} Cross ({r['bars_ago']} bar(s) ago)\n"
                f"  close: {r['close']} | RSI(9): {r['rsi']}\n"
                f"  -> short-term momentum shift, see concepts/EMA.md"
            )
        elif r["setup"] == "Golden-Death-Cross":
            print(
                f"\n{r['symbol']}: {r['direction']} (EMA50/EMA200, {r['bars_ago']} bar(s) ago)\n"
                f"  close: {r['close']} | RSI(9): {r['rsi']}\n"
                f"  -> major trend regime shift signal"
            )


if __name__ == "__main__":
    main()
