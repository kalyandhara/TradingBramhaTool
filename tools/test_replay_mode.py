"""Tests for replay_mode.js (window.RPM) — Multi-Chart dual pick replay, via node."""
import json
import os
import shutil
import subprocess

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
JS = os.path.join(HERE, "replay_mode.js").replace("\\", "/")
DAY = 86400
T0 = 1786060800          # 2026-08-07 00:00 UTC — daily bars are stamped at UTC midnight

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def rpm(expr: str, **data):
    binds = "".join(f"const {k} = {json.dumps(v)};\n" for k, v in data.items())
    script = (f"global.window = global; require({JS!r});\n{binds}"
              f"process.stdout.write(JSON.stringify({expr}));")
    out = subprocess.run(["node", "-"], input=script, capture_output=True,
                         text=True, encoding="utf-8")
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def _bars(n=40, px=100.0, step=1.0, vol=1000.0):
    return [{"time": T0 + i * DAY, "open": px + i * step - 0.5, "high": px + i * step + 1,
             "low": px + i * step - 1, "close": px + i * step, "volume": vol} for i in range(n)]


def test_day_time_is_utc_midnight():
    assert rpm("RPM.dayTime('2026-08-07')") == T0


def test_parse_replay():
    q = ("?symbol=PAUSHAKLTD&replay=2026-10-16&entry=828.06&stop=698.84&target=1180.37"
         "&sdate=2026-10-19&skind=S&sector=%5ECNXPHARMA&rank=4&label=HM%20Buy")
    r = rpm("RPM.parseReplay(q)", q=q)
    assert r["date"] == "2026-10-16" and r["cut"] == rpm("RPM.dayTime('2026-10-16')")
    assert (r["entry"], r["stop"], r["target"]) == (828.06, 698.84, 1180.37)
    assert (r["sdate"], r["skind"], r["sector"], r["rank"], r["label"]) == \
        ("2026-10-19", "S", "^CNXPHARMA", 4, "HM Buy")
    assert rpm("RPM.parseReplay('?symbol=X')") is None
    assert rpm("RPM.parseReplay('?replay=not-a-date')") is None
    # missing levels are null, not NaN
    r = rpm("RPM.parseReplay('?replay=2026-10-16')")
    assert r["entry"] is None and r["stop"] is None and r["skind"] is None


def test_cut_bars_never_keeps_a_bar_after_the_pick_day():
    bars = _bars()
    cut = T0 + 10 * DAY
    out = rpm("RPM.cutBars(b, c)", b=bars, c=cut)
    assert len(out) == 11 and max(b["time"] for b in out) == cut


def test_rebase_starts_at_the_entry_open():
    stock_entry_px = 200.0
    idx = _bars(px=1000.0, step=2.0)
    entry_t = T0 + 11 * DAY
    line = rpm("RPM.rebase(o, t, px)", o=idx, t=entry_t, px=stock_entry_px)
    assert line[0]["time"] == entry_t
    # index close on the entry day / index OPEN on the entry day × stock entry price
    o, c = idx[11]["open"], idx[11]["close"]
    assert line[0]["value"] == pytest.approx(stock_entry_px * c / o)
    assert all(p["time"] >= entry_t for p in line)


def test_rebase_falls_back_to_last_close_when_entry_day_missing():
    idx = [b for i, b in enumerate(_bars(px=1000.0)) if i != 11]
    entry_t = T0 + 11 * DAY
    line = rpm("RPM.rebase(o, t, 50)", o=idx, t=entry_t)
    assert line[0]["time"] == T0 + 12 * DAY
    assert line[0]["value"] == pytest.approx(50 * idx[11]["close"] / idx[10]["close"])
    assert rpm("RPM.rebase([], 1, 50)") == []


def test_volume_breakdown_first_close_below_20d_low_on_heavy_volume():
    bars = _bars(n=60)
    cut = T0 + 30 * DAY
    assert rpm("RPM.volumeBreakdown(b, c)", b=bars, c=cut) is None   # steady uptrend
    # day 40: close below the prior 20-day low on light volume -> not it
    bars[40].update(close=50.0, low=49.0, volume=1000.0)
    # day 45: close below the prior 20-day low on 2x volume -> V
    bars[45].update(close=40.0, low=39.0, volume=2000.0)
    assert rpm("RPM.volumeBreakdown(b, c)", b=bars, c=cut) == bars[45]["time"]
    # a breakdown before the pick does not count
    assert rpm("RPM.volumeBreakdown(b, c)", b=bars, c=T0 + 50 * DAY) is None


def test_markers():
    bars = _bars()
    r = {"cut": T0 + 10 * DAY, "sdate": "2026-08-21", "skind": "S"}
    m = rpm("RPM.markers(r, b, v)", r=r, b=bars, v=T0 + 20 * DAY)
    by = {x["text"]: x for x in m}
    assert by["PICK"]["time"] == T0 + 11 * DAY          # entry = the session after the pick
    assert by["S"]["time"] == rpm("RPM.dayTime('2026-08-21')")
    assert by["V"]["time"] == T0 + 20 * DAY
    assert [x["time"] for x in m] == sorted(x["time"] for x in m)
    assert {x["text"] for x in rpm("RPM.markers(r, b, null)", r={**r, "skind": "T"}, b=bars)} \
        == {"PICK", "T"}


def test_parse_replay_reads_ddate():
    assert rpm("RPM.parseReplay(q).ddate", q="?replay=2026-10-16&ddate=2026-10-30") == "2026-10-30"
    assert rpm("RPM.parseReplay(q).ddate", q="?replay=2026-10-16&ddate=junk") is None
    assert rpm("RPM.parseReplay(q).ddate", q="?replay=2026-10-16") is None


def test_d_marker_is_placed_and_sorted():
    r = rpm("RPM.markers(RPM.parseReplay(q), bars, null)",
            q="?replay=2026-08-07&ddate=2026-08-20&sdate=2026-08-25&skind=S", bars=_bars())
    d = [m for m in r if m["text"] == "D"]
    assert len(d) == 1 and d[0]["time"] == rpm("RPM.dayTime('2026-08-20')")
    assert d[0]["position"] == "aboveBar" and d[0]["shape"] == "arrowDown"
    assert [m["time"] for m in r] == sorted(m["time"] for m in r)
    assert not [m for m in rpm("RPM.markers(RPM.parseReplay(q), bars, null)",
                               q="?replay=2026-08-07", bars=_bars()) if m["text"] == "D"]
