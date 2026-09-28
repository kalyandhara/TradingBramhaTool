"""simple_volume.py — Python port of simple_volume.js.

Bar-for-bar parity with the JS chart indicator is enforced by
test_simple_volume_parity.py so the scanner and chart cannot disagree
about a bar's colour.

Five colour classes:
  BLUE (ppv)   — Pocket Pivot Volume: up day beating every down day
                 within the last `ppv_len` trading days.
  GREEN (up)   — up day, volume above the volume MA.
  RED (down)   — down day, volume above the volume MA.
  ORANGE (dry) — volume at or below MA / dry_frac.
  GREY (noise) — everything else.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULTS = dict(ma_len=50, ppv_len=10, dry_frac=5)


def classify(df: pd.DataFrame, *,
             ma_len: int = 50,
             ppv_len: int = 10,
             dry_frac: int = 5) -> pd.DataFrame:
    """Classify every bar. Returns a DataFrame aligned to *df* with columns:
    kind (str), ma (float or NaN), volume (float).
    """
    def _col(name):
        return name if name in df.columns else name.lower()
    vol = df[_col("Volume")].values.astype(float)
    close = df[_col("Close")].values.astype(float)
    opn = df[_col("Open")].values.astype(float)
    n = len(vol)

    ma = np.full(n, np.nan)
    kinds = np.empty(n, dtype=object)

    cumvol = np.cumsum(vol)
    for i in range(ma_len - 1, n):
        if i >= ma_len:
            ma[i] = (cumvol[i] - cumvol[i - ma_len]) / ma_len
        else:
            ma[i] = cumvol[i] / ma_len

    for i in range(n):
        v = vol[i]
        up = close[i] >= opn[i]
        m = ma[i]
        kind = "noise"

        if not np.isnan(m) and v <= m / dry_frac:
            kind = "dry"
        elif up:
            hi_down = 0.0
            for j in range(max(0, i - ppv_len), i):
                if close[j] < opn[j]:
                    hi_down = max(hi_down, vol[j])
            if hi_down > 0 and v > hi_down:
                kind = "ppv"
            elif not np.isnan(m) and v > m:
                kind = "up"
        elif not np.isnan(m) and v > m:
            kind = "down"

        kinds[i] = kind

    return pd.DataFrame({
        "kind": kinds,
        "ma": ma,
        "volume": vol,
    }, index=df.index)


def stats(sv: pd.DataFrame) -> dict | None:
    """Summary stats from classify() output, matching the JS stats()."""
    if sv.empty:
        return None
    last = sv.iloc[-1]
    recent = sv.tail(20)
    m = last["ma"]
    v = last["volume"]
    return {
        "kind": last["kind"],
        "volume": v,
        "ma": m if not np.isnan(m) else None,
        "rvol": (v / m) * 100 if (not np.isnan(m) and m > 0) else None,
        "ppv20": int((recent["kind"] == "ppv").sum()),
        "dry20": int((recent["kind"] == "dry").sum()),
    }


def no_supply_window(sv: pd.DataFrame, window: int = 10) -> dict:
    """Check the last *window* bars for supply (red bars) and demand (ppv).

    Returns dict with:
      red_count   — number of red (down above MA) bars in the window
      dry_count   — number of dry bars in the window
      ppv_count   — number of pocket pivot bars in the window
      has_supply  — red_count > 0
      has_demand  — ppv_count > 0
    """
    tail = sv.tail(window)
    kinds = tail["kind"]
    red = int((kinds == "down").sum())
    dry = int((kinds == "dry").sum())
    ppv = int((kinds == "ppv").sum())
    return {
        "red_count": red,
        "dry_count": dry,
        "ppv_count": ppv,
        "has_supply": red > 0,
        "has_demand": ppv > 0,
    }
