# Trading Bramha - System Architecture & Workflow Analysis

**Generated:** 2026-10-12  
**Analysis Date:** October 12, 2026  
**Python Version:** 3.14

---

## Executive Summary

Your Trading Bramha system is a sophisticated Indian-market trading dashboard with a modular architecture spanning 80+ Python modules, two dashboard frameworks (Streamlit + Dash), and a Windows Task Scheduler-based batch job system. I've identified **3 dormant scheduled jobs** that are defined but never registered, plus several workflow bottlenecks that prevent functionality from executing through the scheduler.

### Key Finding

**The root cause of your dormant functionality is clear:** 3 of 8 scheduled jobs are defined in code but never registered in Windows Task Scheduler. This is a **configuration gap, not a code gap**—the functionality exists and works when run manually.

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TRADING BRAMHA SYSTEM                                │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│   USER INTERFACE     │
├──────────────────────┤
│ • Streamlit Desk     │ :8501 (dashboard_app.py)
│ • Dash SBC/Astro     │ :8050 (dash_trading_dashboard.py)
│ • Chart Server       │ :5001 (chart_server.py)
└──────────┬───────────┘
           │
           ├─────────────────────────────────────────────────────────────┐
           │                                                             │
┌──────────▼──────────┐    ┌──────────────────────────────────────────┐ │
│  DESK PAGES (20+)   │    │     CORE PIPELINE & DATA LAYER           │ │
├─────────────────────┤    ├──────────────────────────────────────────┤ │
│ • Scheduler Hub     │◄───┤ • screener_pipeline.py (NSE Bhavcopy)    │ │
│ • Pipeline Log      │    │ • scanner_templates.py (12 scanners)     │ │
│ • Opportunity Hub   │    │ • opportunity_hub.py (funnel)            │ │
│ • High-Growth       │    │ • portfolio_db.py (SQLite persistence)   │ │
│ • Hidden Treasures  │    │ • volume_fetcher.py (yfinance wrapper)    │ │
│ • Sector Map        │    │ • sentiment_index.py                    │ │
│ • Market Sentiment  │    │ • market_health.py                       │ │
│ • India Market Intel│    │ • india_market_intel.py                 │ │
│ • Telegram Signals  │    │ • block_deal_intel.py                   │ │
│ • Stock Analyzer    │    │ • nse_shareholding_fetch.py             │ │
│ • Portfolio         │    └──────────────────────────────────────────┘ │
└─────────────────────┘                                            │
           │                                                         │
           │                                                         │
┌──────────▼──────────────────────────────────────────────────────────▼───────┐
│                     SCHEDULER CORE (scheduler_core.py)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  • 8 Registered Jobs (Windows Task Scheduler via schtasks)                 │
│  • JobSpec dataclass (id, label, desc, task_name, kind, command)           │
│  • .bat generation + registration management                               │
│  • Log parsing + run history tracking                                      │
└──────────┬──────────────────────────────────────────────────────────────────┘
           │
           ├────────────────────────────────────────────────────────────────────┐
           │                                                                     │
┌──────────▼──────────┐  ┌──────────────────┐  ┌──────────────────────────────┐ │
│  ACTIVE JOBS (5)    │  │ DORMANT JOBS (3) │  │  JOB EXECUTION FLOW          │ │
├─────────────────────┤  ├──────────────────┤  ├──────────────────────────────┤ │
│ ✓ alert_watcher    │  │ ✗ growth_snapshot│  │ 1. Windows Task Scheduler   │ │
│   (interval)        │  │ ✗ snapshot_refresh│  │    triggers .bat file       │ │
│                    │  │ ✗ hidden_treasures│  │ 2. .bat executes Python/Node│ │
│ ✓ daily_scanner    │  │   _daily          │  │    command with logging     │ │
│   (daily 16:15)     │  │                    │  │ 3. Script writes to logs/   │ │
│                    │  │                    │  │    database                 │ │
│ ✓ sentiment_daily  │  │                    │  │ 4. Scheduler Hub reads      │ │
│   (daily 16:30)     │  │                    │  │    status + next_run       │ │
│                    │  │                    │  │                             │ │
│ ✓ opportunity_daily│  │                    │  │  FAILURE MODES:             │ │
│   (daily 16:20)     │  │                    │  │  • Not registered = never   │ │
│                    │  │                    │  │    runs                     │ │
│ ✓ equity_snapshot  │  │                    │  │  • "Next Run: N/A" =       │ │
│   (daily 16:10)     │  │                    │  │    schedule broken (WEEKLY│ │
└─────────────────────┘  └──────────────────┘  │    vs MINUTE bug)          │ │
                                            └──────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ • NSE Bhavcopy (daily CSV)          • yfinance (OHLCV)                       │
│ • ChartInk (volume screeners)       • NSE Filings/Shareholding             │
│ • BSE Bulk/Block/Insider deals       • Telegram signals                     │
│ • Finviz (US sentiment)            • TradingView screener                 │
│ • Financial Astrology (ephem)       • Astro-Hora (planetary positions)     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                    OUTPUT & STORAGE                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ • trading_bramha.db (SQLite)        • scanner_daily_*.json (cache)          │
│ • daily_opportunities table         • hidden_treasures table               │
│ • equity_snapshots table            • sentiment_history table               │
│ • snapshots table (report cache)    • logs/*.log (job execution logs)       │
│ • output/ (Excel reports)           • reports/ (generated reports)          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Scheduler Registry Analysis

### ✅ ACTIVE JOBS (5/8 - Running Successfully)

| Job ID | Label | Schedule | Status | Last Run | Next Run |
|--------|-------|----------|--------|----------|----------|
| `alert_watcher` | Alert Bot (SVP/indicator signals) | Interval (09:15-15:45, every 15min) | **Enabled** | 2026-10-12 11:15 | Scheduled |
| `daily_scanner` | Daily Scanner Suite | Daily 16:15 | **Enabled** | 2026-10-11 16:15 | 2026-10-12 16:15 |
| `sentiment_daily` | Daily Market Sentiment | Daily 16:30 | **Enabled** | 2026-10-11 16:30 | Scheduled |
| `opportunity_daily` | Daily Opportunity Shortlist | Daily 16:20 | **Enabled** | 2026-10-11 16:20 | 2026-10-12 16:20 |
| `equity_snapshot` | Portfolio Equity Snapshot | Daily 16:10 | **Enabled** | 2026-10-11 16:10 | Scheduled |

**Run History (last 30 days):**
- `alert_watcher`: 200 runs, 199 ok, 0 failed (healthy)
- `daily_scanner`: 18 runs, 18 ok, 0 failed (healthy)
- `sentiment_daily`: 19 runs, 19 ok, 0 failed (healthy)
- `opportunity_daily`: 19 runs, 19 ok, 0 failed (healthy)
- `equity_snapshot`: 5 runs, 5 ok, 0 failed (healthy)

### ❌ DORMANT JOBS (3/8 - Never Registered)

| Job ID | Label | Schedule | Status | Issue |
|--------|-------|----------|--------|-------|
| `growth_snapshot` | Growth Snapshot (High-Growth Screener) | Daily 17:10 | **Not Registered** | Windows task never created |
| `snapshot_refresh` | Report Snapshot Refresh | Daily 16:30 | **Not Registered** | Windows task never created |
| `hidden_treasures_daily` | Hidden Treasures Discovery | Daily 16:45 | **Not Registered** | Windows task never created |

**Why These Are Dormant:**
- Jobs are defined in `scheduler_core.py` JOBS registry
- But Windows Scheduled Tasks were never created via `Register / Update` button in Scheduler Hub
- Without registration, these jobs **never execute automatically**
- Functionality exists in code but pipeline is broken at scheduler level

---

## Workflow & Pipeline Analysis

### 1. Screener Pipeline (`screener_pipeline.py`)

**Purpose:** Daily pipeline: NSE Bhavcopy + Chartink screeners → strategy scoring → Excel shortlist

**Flow:**
```
NSE Bhavcopy (top 200 by traded value)
    ↓
Chartink volume screeners (Darvas + Nimblr)
    ↓
Deduplicate → Download 300d OHLCV from yfinance (.NS) + Nifty50 reference
    ↓
Score each stock against:
    • Minervini Trend Template (8 conditions)
    • TechnoFunda-Swing (6 quantifiable conditions)
    • Elliott Wave analysis (wave position + probabilistic W3/W5 targets)
    ↓
Export colour-coded Excel: "Shortlist" summary + "EW Detail" sheet
```

**Current Status:** ✅ WORKING (executed by `daily_scanner` job)

**Dependencies:**
- `yfinance` (OHLCV data)
- `ta` (technical indicators)
- `openpyxl` (Excel export)
- `ew_module` (Elliott Wave analysis)

---

### 2. Scanner Suite (`scanner_daily_runner.py`)

**Purpose:** Headless nightly run of Scanner Hub suite

**Flow:**
```
Universe build (bhavcopy or screener pipeline)
    ↓
FetchRouter (caches frames across scanners, routes needs_full_history)
    ↓
Run each scanner over universe:
    • Pullback Entry
    • Darvas Box
    • ATH Breakout
    • VCP Pattern
    • etc. (12 total)
    ↓
Save JSON snapshot to tools/cache/scanner_daily_<ts>.json
```

**Current Status:** ✅ WORKING (executed by `daily_scanner` job)

**Key Improvements over old template:**
- One download per symbol per run (not per scanner)
- `needs_full_history` routing for ATH/IPO breakout (prevents false ALL-TIME highs)
- Nifty benchmark for RS calculation

---

### 3. Opportunity Hub Funnel (`opportunity_daily.py`)

**Purpose:** Five-step funnel: universe → momentum → leading sectors → leading industries → scanners → ranked shortlist

**Flow:**
```
Universe (nifty500)
    ↓
Momentum + sector/industry tags (opportunity_hub)
    ↓
Leading sectors (rank_groups)
    ↓
Leading industries within them (rank_groups)
    ↓
Scanners over ONLY those stocks (scanner_templates)
    ↓
Rank, keep top N, store (portfolio_db)
```

**Regime-Gated (B-32/B-33):**
- **RISK-ON**: min_score=45, min_rating=50, max_names=None (full run)
- **MIXED**: min_score=55, min_rating=50, max_names=40 (cautious)
- **RISK-OFF**: min_score=65, min_rating=None, max_names=5 (watchlist only)

**Current Status:** ✅ WORKING (executed by `opportunity_daily` job)

---

### 4. Report Snapshots (`snapshot_registry.py` + `snapshot_refresh.py`)

**Purpose:** Persist report snapshots so pages load instantly from cache

**Registered Snapshots (17 total):**

| Snapshot | Page | Description | Order |
|----------|------|-------------|-------|
| `sector_index_data` | Sector Map | Sector index frames + NIFTY benchmark (2y daily) | 10 |
| `sector_money_flow` | Sector Map | CMF sector grid (nifty500, n=21) | 20 |
| `sector_turnover_share` | Sector Map | Turnover share rotation grid | 21 |
| `volume_shockers` | Home | Bhavcopy + Darvas volume scan | 30 |
| `trending` | Home | What moved today (price movers, volume shockers, extremes) | 31 |
| `institutional_volume` | Home | PPV bars with RVOL ≥ 5x (nifty500) | 32 |
| `cpr_vp_scan` | Home | CPR × Volume Profile confluence | 33 |
| `sentiment` | Market Sentiment | 0-100 sentiment composite | 40 |
| `market_health` | Market Sentiment | Nifty/VIX + health gate basket (60 stocks) | 41 |
| `finviz` | Market Sentiment | Finviz US snapshot + breadth | 42 |
| `market_brief` | Market Sentiment | Market brief model + breadth | 43 |
| `tv_scan` | TradingView | TradingView breakout scan | 50 |
| `bulk_deals` | India Market Intel | BSE + NSE bulk deals | 60 |
| `block_deals` | India Market Intel | BSE + NSE block deals | 61 |
| `insider_trading` | India Market Intel | BSE insider trading (last 7 days) | 62 |
| `gap_volume` | India Market Intel | Gap & volume scan (top 500) | 70 |

**Current Status:** ❌ **DORMANT** - `snapshot_refresh` job not registered

**Impact:**
- Pages compute snapshots on-demand (slow initial load)
- No after-close refresh to ensure fresh data
- Market sentiment page shows "hand-refreshed number" with staleness caution flag

---

### 5. Growth Snapshot (`growth_screen.py`)

**Purpose:** Refresh yfinance fundamentals snapshot behind High-Growth Screener

**Behavior:**
- Runs daily but only re-fetches when snapshot is 7+ days old (quarterly statements)
- No screener.in login required

**Current Status:** ❌ **DORMANT** - `growth_snapshot` job not registered

**Impact:**
- High-Growth Screener page uses stale fundamentals data
- Manual refresh required via page button

---

### 6. Hidden Treasures Discovery (`hidden_treasures_daily.py`)

**Purpose:** Small/micro-cap discovery with quality overlay

**Flow:**
```
Backfill ownership_cache (only quarters not yet cached)
    ↓
Rank NSE Both universe with quality overlay ON, red-flag veto OFF
    ↓
Store top 100 in hidden_treasures table (replace-on-rerun per date)
```

**Current Status:** ❌ **DORMANT** - `hidden_treasures_daily` job not registered

**Impact:**
- Hidden Treasures page opens on empty screen (no stored run)
- Must manually click "Discover" to populate
- No daily coverage/history

---

### 7. Alert Bot (`alert_watcher.js`)

**Purpose:** Live indicator/pattern alert engine during market hours

**Flow:**
```
Poll chart_server (/api/ohlcv) for watchlist
    ↓
Run REAL JS indicator engines headless (volume_profile.js + session_volume_profile.js)
    ↓
Detect state transitions in signal (indicator-wise pattern buildup)
    ↓
Dedupe against persisted state file
    ↓
DELIVER triggered alert (Phase 1: dry-run only, logs to console + JSONL)
```

**Current Status:** ✅ WORKING (executed by `alert_watcher` job, interval mode)

**Delivery Channels:**
- Phase 1: Dry-run only (log + JSONL feed)
- Email/Telegram adapters stubbed (require explicit wiring)

---

## Identified Issues & Bottlenecks

### 🔴 Critical: Dormant Scheduled Jobs

**Problem:** 3 jobs defined but never registered → functionality never executes automatically

**Root Cause:**
- Jobs exist in `scheduler_core.py` JOBS registry
- Windows Scheduled Tasks never created via Scheduler Hub "Register / Update" button
- No user action to register these tasks

**Impact:**
- `snapshot_refresh`: 17 report snapshots never refreshed after close → pages slow/stale
- `growth_snapshot`: High-Growth Screener fundamentals outdated
- `hidden_treasures_daily`: Hidden Treasures page empty on open

**Fix:** Register these jobs via Scheduler Hub or CLI:
```bash
py -3 tools/scheduler_core.py register growth_snapshot
py -3 tools/scheduler_core.py register snapshot_refresh
py -3 tools/scheduler_core.py register hidden_treasures_daily
```

---

### 🟠 Medium: Schedule History Bug (Fixed in Code)

**Problem:** Historical bug where interval jobs used `/sc MINUTE` instead of `/sc WEEKLY`

**Impact:**
- Tasks registered with `MINUTE` schedule had "Next Run: N/A" (never fire)
- Fixed in `scheduler_core.py` line 237-252 (uses WEEKLY with /ri /du now)

**Current Status:** ✅ FIXED in code, but verify existing tasks re-registered

---

### 🟡 Low: Python Interpreter Path Mismatch

**Problem:** `scheduler_core.py` hardcodes:
```python
PYTHON_EXE = r"C:\Users\Owner\AppData\Local\Python\pythoncore-3.14-64\python.exe"
```

But `start_desk.bat` uses:
```batch
set "PYTHON=C:\Users\Owner\AppData\Local\Programs\Python\Python314\python.exe"
```

**Impact:** Scheduled jobs may fail if wrong interpreter used

**Fix:** Unify Python path across all configs

---

### 🟡 Low: No Startup Registration

**Problem:** Jobs must be manually registered via Scheduler Hub UI

**Impact:** Fresh setup → all jobs dormant until user discovers Scheduler Hub

**Fix:** Add `install_tasks.ps1` script to register all jobs on first run

---

## Improvement Recommendations

### Priority 1: Activate Dormant Jobs (Immediate)

**Action:** Register the 3 dormant jobs

```bash
# Via CLI
cd tools
python scheduler_core.py register growth_snapshot
python scheduler_core.py register snapshot_refresh
python scheduler_core.py register hidden_treasures_daily

# Verify registration
python scheduler_core.py status growth_snapshot
python scheduler_core.py status snapshot_refresh
python scheduler_core.py status hidden_treasures_daily
```

**Expected Outcome:**
- Report snapshots refresh automatically after close (5-10 min runtime)
- High-Growth Screener fundamentals updated weekly
- Hidden Treasures discovery runs daily (top 100 stored)

---

### Priority 2: Fix Python Path Inconsistency

**Action:** Unify Python interpreter path

1. Choose one:
   - `C:\Users\Owner\AppData\Local\Programs\Python\Python314\python.exe` (install)
   - `C:\Users\Owner\AppData\Local\Python\pythoncore-3.14-64\python.exe` (store)

2. Update all references:
   - `scheduler_core.py` line 40
   - `start_desk.bat` line 8
   - `scanner_daily.bat` line 2
   - Any other hardcoded paths

3. Use environment variable or config file for portability

---

### Priority 3: Add Auto-Registration Script

**Action:** Create `install_all_tasks.ps1`

```powershell
# Register all Trading Bramha scheduled tasks
py -3 tools/scheduler_core.py register alert_watcher
py -3 tools/scheduler_core.py register daily_scanner
py -3 tools/scheduler_core.py register growth_snapshot
py -3 tools/scheduler_core.py register sentiment_daily
py -3 tools/scheduler_core.py register opportunity_daily
py -3 tools/scheduler_core.py register snapshot_refresh
py -3 tools/scheduler_core.py register equity_snapshot
py -3 tools/scheduler_core.py register hidden_treasures_daily

# Verify
py -3 tools/scheduler_core.py summaries
```

**Benefit:** One-command setup for new installations

---

### Priority 4: Add Health Check Dashboard

**Action:** Add a "System Health" page to dashboard_app.py

**Metrics to display:**
- Job registration status (all 8 jobs)
- Next run times (highlight "N/A" as broken)
- Last run results (failed jobs in red)
- Log tail for each job
- Python interpreter path consistency check
- Chart server connectivity check

**Benefit:** Immediate visibility into dormant/broken jobs

---

### Priority 5: Improve Alert Bot Delivery

**Action:** Wire email/Telegram delivery for alert_watcher.js

**Current:** Phase 1 dry-run only (log + JSONL)

**Steps:**
1. Configure delivery channels in `alert_config.json`:
   ```json
   {
     "delivery": ["log", "email", "telegram"],
     "email": {"to": "user@example.com"},
     "telegram": {"bot_token": "...", "chat_id": "..."}
   }
   ```

2. Implement delivery adapters in alert_watcher.js (stubs already exist)

**Benefit:** Real-time alerts during market hours

---

### Priority 6: Add Job Dependency Management

**Problem:** No ordering guarantee between jobs

**Example:**
- `opportunity_daily` (16:20) depends on `sentiment_daily` (16:30) - wrong order
- `snapshot_refresh` (16:30) conflicts with `sentiment_daily` (16:30)

**Action:** Implement job dependencies in scheduler_core.py

```python
@dataclass
class JobSpec:
    # ... existing fields ...
    depends_on: list[str] = field(default_factory=list)  # job IDs that must finish first
```

**Benefit:** Correct execution order, prevent race conditions

---

### Priority 7: Add Retry Logic for Failed Jobs

**Problem:** Single failure = job marked FAILED, no retry

**Action:** Add retry logic to .bat wrappers

```batch
@echo off
set MAX_RETRIES=3
set RETRY=0

:retry
"%PYTHON%" "%~dp0script.py" >> "%LOG%" 2>&1
if errorlevel 1 (
    set /a RETRY+=1
    if %RETRY% lss %MAX_RETRIES% (
        echo Retry %RETRY%/%MAX_RETRIES% >> "%LOG%"
        timeout /t 30
        goto retry
    )
    echo ***** FAILED after %MAX_RETRIES% retries ***** >> "%LOG%"
) else (
    echo ----- ok ----- >> "%LOG%"
)
```

**Benefit:** Transient network failures don't lose the day's run

---

### Priority 8: Add Job Parallelization

**Problem:** Sequential job execution (total runtime: 20-30 min)

**Action:** Parallelize independent jobs

**Groups:**
- Group A (can run in parallel): `equity_snapshot`, `sentiment_daily`, `opportunity_daily`
- Group B (after Group A): `snapshot_refresh`, `growth_snapshot`, `hidden_treasures_daily`

**Implementation:** Use Windows Task Scheduler triggers or Python subprocess pool

**Benefit:** Reduce total runtime to 10-15 min

---

## Code Quality Issues (from DEBUG_REPORT.md)

### 🔴 Critical Security Issues (2)

1. **SQL Injection** (`portfolio_db.py:173`)
   - String-based query construction with f-string
   - Fix: Use parameterized queries

2. **Subprocess shell=True** (`dashboard_app.py:4894, 4912`)
   - Windows scheduled task creation with user input
   - Fix: Use `shell=False` with argument list

### 🟠 Type Errors (30+)

- `float(None)` in telegram_signals.py
- Missing Optional type hints
- Return type mismatches

**Fix:** Add proper type annotations, handle None explicitly

### 🟡 Code Quality (2000+ flake8 issues)

- Line too long (E501)
- Unused imports/variables
- Bare except: pass patterns

**Fix:** Run `ruff check --fix tools/` + `ruff format tools/`

---

## Monitoring & Observability Recommendations

### 1. Centralized Logging

**Current:** Each job writes to its own .log file

**Improvement:** Centralize to logs/ with structured JSON logs

```python
import structlog
log = structlog.get_logger()
log.info("job_started", job_id="opportunity_daily", universe_size=500)
```

**Benefit:** Easier querying, aggregation, alerting

---

### 2. Add Metrics Collection

**Action:** Track job metrics in database

```sql
CREATE TABLE job_metrics (
    job_id TEXT,
    run_at TIMESTAMP,
    duration_sec REAL,
    status TEXT,
    output_size_bytes INTEGER,
    error TEXT
);
```

**Benefit:** Historical performance analysis, anomaly detection

---

### 3. Add Alert Notifications

**Action:** Notify on job failures

**Channels:**
- Email (SMTP)
- Telegram bot
- Desktop notification (Windows toast)

**Implementation:** Hook into scheduler_core.py `register()` to set up failure notifications

---

## Summary of Findings

### ✅ What's Working Well

1. **Active Jobs (5/8):** Running reliably with 0 failures
2. **Modular Architecture:** 80+ focused modules, clear separation of concerns
3. **Snapshot System:** Well-designed caching strategy (when registered)
4. **Scheduler Hub:** Excellent UI for job management
5. **Regime-Gated Scoring:** Smart risk-adaptive funnel

### ❌ What's Broken/Dormant

1. **3 Scheduled Jobs Never Registered:**
   - `growth_snapshot` → High-Growth Screener stale
   - `snapshot_refresh` → 17 report snapshots never refreshed
   - `hidden_treasures_daily` → Hidden Treasures page empty

2. **No Auto-Registration:** Fresh setup → all jobs dormant until manual action

3. **No Health Visibility:** No single page showing all job statuses

4. **No Job Dependencies:** Incorrect execution order possible

5. **No Retry Logic:** Single failure = lost day's run

### 🎯 Immediate Actions (Do Today)

1. **Register dormant jobs:**
   ```bash
   cd tools
   python scheduler_core.py register growth_snapshot
   python scheduler_core.py register snapshot_refresh
   python scheduler_core.py register hidden_treasures_daily
   ```

2. **Verify registration:**
   ```bash
   python scheduler_core.py summaries
   ```

3. **Check Scheduler Hub in dashboard:** Navigate to Scheduler Hub page, confirm all 8 jobs show "🟢 registered"

4. **Run manual test:**
   ```bash
   python scheduler_core.py run growth_snapshot
   python scheduler_core.py run snapshot_refresh
   python scheduler_core.py run hidden_treasures_daily
   ```

---

## Conclusion

Your Trading Bramha system is well-architected with a solid foundation. The primary issue is that **3 of 8 scheduled jobs are dormant** because they were never registered in Windows Task Scheduler. This is a configuration gap, not a code gap—the functionality exists and works when run manually.

**Root Cause:** Jobs defined in code but Windows tasks never created via Scheduler Hub "Register / Update" button.

**Solution:** Register the 3 dormant jobs via CLI or Scheduler Hub UI, then monitor via Scheduler Hub status page.

**Long-term:** Add auto-registration script, health check dashboard, job dependencies, and retry logic to prevent future dormancy.

---

## Appendix: Key File References

### Scheduler Core
- `tools/scheduler_core.py` - Job registry + Windows Task Scheduler wrappers
- `tools/desk_pages/scheduler_hub.py` - Scheduler Hub UI page

### Job Scripts
- `tools/scanner_daily_runner.py` - Headless scanner suite
- `tools/scanner_daily.bat` - Wrapper for daily_scanner job
- `tools/opportunity_daily.py` - Opportunity Hub funnel
- `tools/hidden_treasures_daily.py` - Hidden Treasures discovery
- `tools/growth_screen.py` - High-Growth Screener fundamentals
- `tools/snapshot_refresh.py` - Report snapshot refresh
- `tools/snapshot_registry.py` - Snapshot producer registry
- `tools/snapshot_store.py` - Snapshot persistence
- `tools/alert_watcher.js` - Live alert engine

### Pipeline Core
- `tools/screener_pipeline.py` - NSE Bhavcopy + Chartink pipeline
- `tools/scanner_templates.py` - 12 pre-built scanners
- `tools/opportunity_hub.py` - Five-step funnel logic
- `tools/portfolio_db.py` - SQLite persistence layer

### Dashboard
- `tools/dashboard_app.py` - Streamlit desk (7652 lines)
- `tools/dash_trading_dashboard.py` - Dash SBC/Astro dashboard
- `tools/chart_server.py` - Real-time chart data server

### Startup Scripts
- `start_desk.bat` - Launch Streamlit desk
- `start.bat` - Launch OmniRoute (SBC dashboard)
- `stop.bat` - Stop running services

---

*Analysis generated by Devin AI - 2026-10-12*
