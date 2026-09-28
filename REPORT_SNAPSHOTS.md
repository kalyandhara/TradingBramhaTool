# Report Snapshots — stored on-demand reports with a last-run stamp

Every "generate on demand" report that used to live only in the browser session
now loads its **last stored run** on page open, shows *Last run <timestamp>*, and
refreshes on demand with the **↻** button next to it. A scheduled job rewrites
all of them after the close.

## What is stored

| Snapshot | Page | Feeds |
|---|---|---|
| `sector_index_data` | Sector Map | heatmap, rotation quadrant, RRG, shareable card |
| `sector_money_flow` | Sector Map, Home | Chaikin money-flow grid |
| `sector_turnover_share` | Sector Map | turnover-share rotation grid |
| `volume_shockers` | Home | Darvas volume shockers (bhavcopy + default-threshold result) |
| `trending` | Home | price movers, volume shockers, 52-week / all-time extremes |
| `institutional_volume` | Home | pocket-pivot bars with volume ≥ 5x the 50-day average, last 5 sessions (nifty500) |
| `cpr_vp_scan` | Home | CPR × Volume Profile confluence over the top-turnover names (setups on the last bar; context, not a signal) |
| `sentiment` | Market Sentiment | composite reading (also persisted by sentiment_index) |
| `market_health` | Market Sentiment | NIFTY / VIX + 60-name basket for the health gate |
| `finviz` | Market Sentiment | US index chips + breadth |
| `market_brief` | Market Sentiment | the morning brief card |
| `tv_scan` | TradingView | BrkoutGeek breakout scan at default thresholds |
| `bulk_deals`, `block_deals`, `insider_trading` | India Market Intel | BSE + NSE deal tables, 7-day insider filings |
| `gap_volume` | India Market Intel | gap & volume scan at default thresholds |

Storage: table `snapshots` in `tools/trading_bramha.db` — one row per snapshot
per day (a re-run replaces the day's row), payload pickled + zlib, run
timestamp, parameters, elapsed seconds, status and error. Rows older than 90
days are pruned, but the newest good row of each snapshot is always kept.

**Not** snapshotted, on purpose: Chartink / Pre-Breakout / High-Growth (need a
pasted browser cookie), Hidden Treasures, the daily opportunity shortlist,
scanner runs and orbit charts (already persisted by their own tables / dated
files), and anything symbol-specific.

## How they refresh

1. **Scheduled** — Scheduler Hub → *Report Snapshot Refresh*
   (`TradingBramha-SnapshotRefresh`, daily 16:30). Register it once from the
   hub. It runs `tools/snapshot_refresh.py --all`; one failing snapshot is
   logged and skipped, never aborting the run.
2. **On demand** — the ↻ button beside each report queues a recompute on the
   session's background job queue; the page stays live and the new run appears
   when it lands.
3. **On app start** — any snapshot older than the last weekday close is
   recomputed in a background thread. Toggle this in Scheduler Hub → *Report
   snapshots*. Pages never fetch on load; they show what is stored and flag it
   *⚠ older than the last close* until a refresh lands.

Scheduler Hub → *Report snapshots* also lists every snapshot with its last run,
status, size and error, and has **↻ Refresh all now (in-app)**.

## Sliders and parameters

The scheduled run computes each report at the page's default parameters and
stores the raw frames alongside. Moving a slider re-derives the view live from
the stored frames (RRG / heatmap period from the sector frames, Darvas
thresholds from the stored bhavcopy); a few scans that need a network call at
other thresholds (TradingView, gap & volume, insider date range) keep a
"run at these thresholds" button whose result lives in the session only.

## CLI

```
py -3 tools/snapshot_refresh.py --list          # names + last run
py -3 tools/snapshot_refresh.py --all           # everything
py -3 tools/snapshot_refresh.py --missing       # only those without a run today
py -3 tools/snapshot_refresh.py finviz tv_scan  # named
```

Code: `tools/snapshot_store.py` (SQLite), `tools/snapshot_registry.py`
(producers, no Streamlit), `tools/snapshot_refresh.py` (runner),
`snapshot_panel()` in `tools/dashboard_app.py` (badge + ↻).
Tests: `tools/test_snapshot_store.py`.

## Sending a table to Predictive Analysis

Home's **Institutional volume** and **Volume Shockers · Darvas** tables and the
**Watchlist** page each have a **→ Predictive Analysis (n)** button. It makes
that table's symbols the candidate list on Research › Predictive Analysis (with
a short note per name, e.g. `20.7x rvol · +7.7% · 2026-09-25`) and jumps there.
The list is stored in the settings table, so it survives a restart; sending
another table replaces it, and ✕ on the Predictive Analysis page clears it.
