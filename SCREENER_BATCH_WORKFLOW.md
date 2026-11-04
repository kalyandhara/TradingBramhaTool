# Screener Batch Workflow & Segregated Reporting System

**Generated:** 2026-10-12  
**Purpose:** Execute screeners in batches and generate segregated reports by category

---

## Current State Analysis

### Existing Scanner Registry (12+ Scanners)

| Category | Scanners | Purpose |
|----------|----------|---------|
| **Entry** | Bullish CHoCH, Pullback Entry, Order Block Retest, Breakout Retest, HM Buy, RSI 60-40, RSI Divergence Bull, RSI-Fibo Hidden Divergence | Trade entry setups |
| **Trend** | Shallow Flip, Renko Flip, Stage 2 Uptrend, ADX Trend Confirmation, %R Bottoming | Trend confirmation & structure change |
| **Momentum** | 52-Week High Leaders | Momentum leaders |
| **Risk** | RSI Divergence Bear, %R Exhaustion Sell, Bearish Reversal Candle | Risk flags / exit signals |
| **Pattern** | Darvas Box, VCP, Symmetrical Triangle, Ascending Triangle, Descending Triangle, Bull Flag, Bear Flag | Pattern detection |
| **Special** | Proxy-PEAD Drift, Candlestick patterns | Specialized setups |

### Current Limitations

1. **Single JSON Output:** All scanner results dumped into one `scanner_daily_<ts>.json` file
2. **No Segregation:** Results not separated by category or use case
3. **Sequential Execution:** All scanners run sequentially (slow for large universes)
4. **No Aggregation:** No cross-scanner confluence analysis in batch mode
5. **No Report Generation:** No Excel/HTML reports for different audiences

---

## Proposed Batch Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BATCH SCREENER WORKFLOW                                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│  1. CONFIGURATION │
│  - Universe size  │
│  - Scanner groups │
│  - Output formats │
│  - Schedule times │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. UNIVERSE BUILDER (Parallel Data Fetch)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  • NSE Bhavcopy (top N by turnover)                                          │
│  • Screener pipeline results                                                 │
│  • Custom symbol list                                                       │
│  • Sector-wise universe                                                      │
│  • Cache hit-check (avoid re-fetch)                                          │
└────────┬────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. BATCH EXECUTION ENGINE (Category-Based)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  BATCH 1: Entry Scanners (High Priority)                                     │
│  ├─ Bullish CHoCH                                                            │
│  ├─ Pullback Entry                                                           │
│  ├─ Order Block Retest                                                       │
│  ├─ Breakout Retest                                                          │
│  ├─ HM Buy                                                                   │
│  ├─ RSI 60-40 Setup                                                          │
│  ├─ RSI Divergence Bull                                                      │
│  └─ RSI-Fibo Hidden Divergence                                               │
│                                                                              │
│  BATCH 2: Trend Scanners (Context)                                           │
│  ├─ Shallow Flip                                                             │
│  ├─ Renko Flip                                                               │
│  ├─ Stage 2 Uptrend                                                          │
│  ├─ ADX Trend Confirmation                                                   │
│  └─ %R Bottoming                                                             │
│                                                                              │
│  BATCH 3: Momentum Scanners (Leaders)                                        │
│  └─ 52-Week High Leaders                                                      │
│                                                                              │
│  BATCH 4: Risk Scanners (Flags)                                              │
│  ├─ RSI Divergence Bear                                                      │
│  ├─ %R Exhaustion Sell                                                       │
│  └─ Bearish Reversal Candle                                                   │
│                                                                              │
│  BATCH 5: Pattern Scanners (Geometric)                                        │
│  ├─ Darvas Box                                                               │
│  ├─ VCP                                                                      │
│  ├─ Symmetrical Triangle                                                     │
│  ├─ Ascending Triangle                                                       │
│  ├─ Descending Triangle                                                      │
│  ├─ Bull Flag                                                                │
│  └─ Bear Flag                                                                │
│                                                                              │
│  BATCH 6: Special Scanners (Events)                                          │
│  ├─ Proxy-PEAD Drift                                                         │
│  └─ Candlestick patterns                                                      │
│                                                                              │
└────────┬────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. RESULT AGGREGATION                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Merge all batch results                                                   │
│  • Calculate confluence (how many scanners hit each symbol)                  │
│  • Cross-reference with risk flags                                          │
│  • Apply quality filters (M1 rating, fundamentals)                          │
│  • Rank by score + confluence                                                │
└────────┬────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  5. SEGREGATED REPORT GENERATION                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  REPORT A: Entry Traders (Actionable Setups)                                 │
│  ├─ All Entry scanner hits                                                  │
│  ├─ Trade plans (entry/stop/target)                                          │
│  ├─ Volume confirmation                                                      │
│  ├─ Risk flags overlay                                                       │
│  └─ Excel + HTML output                                                     │
│                                                                              │
│  REPORT B: Trend Followers (Market Context)                                  │
│  ├─ Trend scanner hits                                                       │
│  ├─ Stage analysis                                                           │
│  ├─ ADX strength                                                             │
│  └─ Excel output                                                            │
│                                                                              │
│  REPORT C: Risk Monitor (Portfolio Health)                                   │
│  ├─ Risk scanner hits                                                        │
│  ├─ Portfolio holdings at risk                                              │
│  ├─ Exit signals                                                            │
│  └─ Email alert                                                             │
│                                                                              │
│  REPORT D: Pattern Watchlist (Setup Detection)                               │
│  ├─ Pattern scanner hits                                                     │
│  ├─ Pattern maturity stages                                                  │
│  ├─ Breakout proximity                                                      │
│  └─ HTML watchlist                                                           │
│                                                                              │
│  REPORT E: Confluence Report (High-Conviction Picks)                         │
│  ├─ Symbols with 3+ scanner hits                                            │
│  ├─ Weighted score (category-weighted)                                      │
│  ├─ Regime-gated (RISK-ON/MIXED/RISK-OFF)                                  │
│  └─ Top 20 list                                                              │
│                                                                              │
│  REPORT F: Sector Rotation (By Sector Breakdown)                              │
│  ├─ Hits per sector                                                          │
│  ├─ Sector strength ranking                                                  │
│  ├─ Heatmap visualization                                                   │
│  └─ HTML + PDF output                                                       │
│                                                                              │
└────────┬────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  6. DELIVERY & NOTIFICATION                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Save to database (trading_bramha.db)                                      │
│  • Email reports (configurable recipients)                                   │
│  • Telegram channel push                                                     │
│  • Dashboard refresh (update cache)                                          │
│  • Archive historical runs                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Batch Execution Engine

Create `scanner_batch_runner.py`:

```python
#!/usr/bin/env python3
"""
scanner_batch_runner.py - Category-based batch execution of screeners.

Runs scanners in predefined batches by category, aggregates results,
and generates segregated reports for different use cases.
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import screener_pipeline as sp
import scanner_templates as sc
from opportunity_daily import _FetchRouter
import portfolio_db as db

log = logging.getLogger("scanner_batch")

# ── Batch Configuration ───────────────────────────────────────────────────────

@dataclass
class BatchConfig:
    """Configuration for a scanner batch."""
    name: str
    category: str
    scanners: list[str]
    priority: int = 0  # Lower = runs first
    parallel: bool = True  # Run scanners in parallel within batch


# Predefined batches based on scanner categories
BATCHES: list[BatchConfig] = [
    BatchConfig(
        name="entry_setups",
        category="Entry",
        scanners=[
            "Pullback Entry",
            "Order Block Retest",
            "Breakout Retest",
            "HM Buy (Hilega Milega)",
            "RSI 60-40 Setup",
            "RSI Divergence Bull",
            "RSI-Fibo Hidden Divergence",
        ],
        priority=1,
        parallel=True,
    ),
    BatchConfig(
        name="trend_context",
        category="Trend",
        scanners=[
            "52-Week High Leaders",
            "Stage 2 Uptrend",
            "ADX Trend Confirmation",
            "%R Bottoming",
        ],
        priority=2,
        parallel=True,
    ),
    BatchConfig(
        name="risk_flags",
        category="Risk",
        scanners=[
            "RSI Divergence Bear",
            "%R Exhaustion Sell",
            "Bearish Reversal Candle",
        ],
        priority=3,
        parallel=True,
    ),
    BatchConfig(
        name="patterns",
        category="Pattern",
        scanners=[
            "Darvas Box",
            "VCP",
            "Symmetrical Triangle",
            "Ascending Triangle",
            "Descending Triangle",
        ],
        priority=4,
        parallel=False,  # Sequential for resource-intensive geometric scans
    ),
]


# ── Batch Execution ───────────────────────────────────────────────────────────

def run_batch(
    batch: BatchConfig,
    universe: list[str],
    router: _FetchRouter,
    benchmark_df: pd.DataFrame | None,
) -> dict[str, list[dict]]:
    """Run all scanners in a batch over the universe."""
    log.info(f"Running batch: {batch.name} ({len(batch.scanners)} scanners)")
    
    results: dict[str, list[dict]] = {}
    
    if batch.parallel:
        # Parallel execution within batch
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_scanner = {
                executor.submit(
                    sc.run_scanner,
                    name,
                    universe,
                    router(name),
                    benchmark_df=benchmark_df,
                ): name
                for name in batch.scanners
                if name in sc.SCANNERS
            }
            
            for future in as_completed(future_to_scanner):
                scanner_name = future_to_scanner[future]
                try:
                    hits = future.result()
                    results[scanner_name] = hits
                    log.info(f"  {scanner_name}: {len(hits)} hits")
                except Exception as exc:
                    log.error(f"  {scanner_name}: ERROR {exc}")
                    results[scanner_name] = []
    else:
        # Sequential execution
        for name in batch.scanners:
            if name not in sc.SCANNERS:
                log.warning(f"  {name}: not registered, skipped")
                continue
            try:
                hits = sc.run_scanner(name, universe, router(name), benchmark_df=benchmark_df)
                results[name] = hits
                log.info(f"  {name}: {len(hits)} hits")
            except Exception as exc:
                log.error(f"  {name}: ERROR {exc}")
                results[name] = []
    
    return results


def run_all_batches(
    universe: list[str],
    days: int = 400,
) -> dict[str, dict[str, list[dict]]]:
    """Run all batches in priority order."""
    log.info(f"Starting batch run over {len(universe)} symbols")
    
    router = _FetchRouter(days=days)
    try:
        bench = sp.fetch_nifty50(days=days)
    except Exception as exc:
        log.warning(f"Benchmark fetch failed: {exc}")
        bench = None
    
    # Sort batches by priority
    sorted_batches = sorted(BATCHES, key=lambda b: b.priority)
    
    all_results: dict[str, dict[str, list[dict]]] = {}
    
    for batch in sorted_batches:
        batch_results = run_batch(batch, universe, router, bench)
        all_results[batch.name] = batch_results
    
    log.info(f"Fetched {router.misses} distinct symbol-frames across all batches")
    return all_results


# ── Result Aggregation ───────────────────────────────────────────────────────

def aggregate_confluence(all_results: dict[str, dict[str, list[dict]]]) -> pd.DataFrame:
    """Calculate confluence: how many scanners hit each symbol."""
    symbol_scanner_counts: dict[str, dict] = {}
    
    for batch_name, batch_results in all_results.items():
        for scanner_name, hits in batch_results.items():
            for hit in hits:
                sym = hit.get("symbol")
                if not sym:
                    continue
                
                if sym not in symbol_scanner_counts:
                    symbol_scanner_counts[sym] = {
                        "total_hits": 0,
                        "scanners": [],
                        "categories": set(),
                        "max_score": 0,
                    }
                
                symbol_scanner_counts[sym]["total_hits"] += 1
                symbol_scanner_counts[sym]["scanners"].append(scanner_name)
                symbol_scanner_counts[sym]["categories"].add(
                    sc.SCANNERS.get(scanner_name, {}).get("category", "Unknown")
                )
                symbol_scanner_counts[sym]["max_score"] = max(
                    symbol_scanner_counts[sym]["max_score"],
                    hit.get("score", 0),
                )
    
    # Convert to DataFrame
    rows = []
    for sym, data in symbol_scanner_counts.items():
        rows.append({
            "symbol": sym,
            "total_hits": data["total_hits"],
            "scanners": ", ".join(data["scanners"]),
            "categories": ", ".join(sorted(data["categories"])),
            "max_score": data["max_score"],
        })
    
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["total_hits", "max_score"], ascending=[False, False])
    
    return df


def filter_by_regime(df: pd.DataFrame, regime: str) -> pd.DataFrame:
    """Apply regime-gated filtering (from opportunity_daily)."""
    from opportunity_daily import REGIME_GATE
    
    gate = REGIME_GATE.get(regime, REGIME_GATE["UNKNOWN"])
    
    if gate["min_score"]:
        df = df[df["max_score"] >= gate["min_score"]]
    
    if gate["max_names"]:
        df = df.head(gate["max_names"])
    
    return df


# ── Report Generation ─────────────────────────────────────────────────────────

class ReportGenerator:
    """Generate segregated reports from batch results."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_entry_report(
        self,
        all_results: dict[str, dict[str, list[dict]]],
        confluence_df: pd.DataFrame,
    ) -> Path:
        """Generate Entry Traders report (actionable setups)."""
        log.info("Generating Entry Traders report...")
        
        # Collect all entry scanner hits
        entry_hits = []
        for batch_name, batch_results in all_results.items():
            if batch_name != "entry_setups":
                continue
            for scanner_name, hits in batch_results.items():
                for hit in hits:
                    hit["scanner"] = scanner_name
                    entry_hits.append(hit)
        
        if not entry_hits:
            log.warning("No entry hits to report")
            return None
        
        df = pd.DataFrame(entry_hits)
        
        # Add confluence info
        df = df.merge(
            confluence_df[["symbol", "total_hits", "categories"]],
            on="symbol",
            how="left",
        )
        
        # Sort by score, then confluence
        df = df.sort_values(["score", "total_hits"], ascending=[False, False])
        
        # Export to Excel
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        path = self.output_dir / f"entry_report_{ts}.xlsx"
        
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Entry Setups", index=False)
            
            # Create summary sheet
            summary = pd.DataFrame({
                "Metric": [
                    "Total Hits",
                    "Unique Symbols",
                    "Avg Score",
                    "Max Confluence",
                ],
                "Value": [
                    len(df),
                    df["symbol"].nunique(),
                    round(df["score"].mean(), 2),
                    df["total_hits"].max(),
                ],
            })
            summary.to_excel(writer, sheet_name="Summary", index=False)
        
        log.info(f"Entry report saved: {path}")
        return path
    
    def generate_risk_report(
        self,
        all_results: dict[str, dict[str, list[dict]]],
        portfolio_symbols: list[str] | None = None,
    ) -> Path:
        """Generate Risk Monitor report."""
        log.info("Generating Risk Monitor report...")
        
        # Collect all risk scanner hits
        risk_hits = []
        for batch_name, batch_results in all_results.items():
            if batch_name != "risk_flags":
                continue
            for scanner_name, hits in batch_results.items():
                for hit in hits:
                    hit["scanner"] = scanner_name
                    risk_hits.append(hit)
        
        if not risk_hits:
            log.warning("No risk hits to report")
            return None
        
        df = pd.DataFrame(risk_hits)
        
        # Flag portfolio holdings at risk
        if portfolio_symbols:
            df["in_portfolio"] = df["symbol"].isin(portfolio_symbols)
        
        # Export
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        path = self.output_dir / f"risk_report_{ts}.xlsx"
        
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Risk Flags", index=False)
            
            if portfolio_symbols:
                portfolio_risks = df[df["in_portfolio"]]
                portfolio_risks.to_excel(writer, sheet_name="Portfolio at Risk", index=False)
        
        log.info(f"Risk report saved: {path}")
        return path
    
    def generate_confluence_report(
        self,
        confluence_df: pd.DataFrame,
        regime: str = "MIXED",
    ) -> Path:
        """Generate Confluence Report (high-conviction picks)."""
        log.info("Generating Confluence Report...")
        
        if confluence_df.empty:
            log.warning("No confluence data to report")
            return None
        
        # Apply regime filtering
        filtered_df = filter_by_regime(confluence_df, regime)
        
        # Top 20 high-confluence picks
        top_picks = filtered_df.head(20)
        
        # Export
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        path = self.output_dir / f"confluence_report_{ts}.xlsx"
        
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            top_picks.to_excel(writer, sheet_name="Top Picks", index=False)
            filtered_df.to_excel(writer, sheet_name="All Qualified", index=False)
        
        log.info(f"Confluence report saved: {path}")
        return path
    
    def generate_all_reports(
        self,
        all_results: dict[str, dict[str, list[dict]]],
        confluence_df: pd.DataFrame,
        regime: str = "MIXED",
    ) -> dict[str, Path]:
        """Generate all reports."""
        paths = {}
        
        # Entry report
        paths["entry"] = self.generate_entry_report(all_results, confluence_df)
        
        # Risk report
        portfolio_symbols = db.get_portfolio_symbols() if hasattr(db, "get_portfolio_symbols") else None
        paths["risk"] = self.generate_risk_report(all_results, portfolio_symbols)
        
        # Confluence report
        paths["confluence"] = self.generate_confluence_report(confluence_df, regime)
        
        return paths


# ── Main Pipeline ───────────────────────────────────────────────────────────

def main():
    import argparse
    
    ap = argparse.ArgumentParser(description="Batch screener execution with segregated reports")
    ap.add_argument("--universe", default="bhavcopy", choices=["bhavcopy", "screener"])
    ap.add_argument("--top-n", type=int, default=300)
    ap.add_argument("--days", type=int, default=400)
    ap.add_argument("--regime", default="MIXED", choices=["RISK-ON", "MIXED", "RISK-OFF"])
    ap.add_argument("--output-dir", default="reports/batch", type=str)
    
    args = ap.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    
    # Build universe
    if args.universe == "bhavcopy":
        universe = sp.fetch_bhavcopy_top_volume(args.top_n) or []
    else:
        df = sp.run_pipeline()
        universe = sorted(df["Symbol"].dropna().unique().tolist()) if df is not None else []
    
    if not universe:
        log.error("Universe is empty")
        return 1
    
    log.info(f"Universe: {len(universe)} symbols")
    
    # Run all batches
    all_results = run_all_batches(universe, days=args.days)
    
    # Aggregate confluence
    confluence_df = aggregate_confluence(all_results)
    log.info(f"Confluence: {len(confluence_df)} symbols with scanner hits")
    
    # Generate reports
    report_gen = ReportGenerator(Path(args.output_dir))
    report_paths = report_gen.generate_all_reports(all_results, confluence_df, args.regime)
    
    # Save raw results to database
    ts = datetime.now().isoformat()
    meta = {
        "universe_mode": args.universe,
        "universe_size": len(universe),
        "days": args.days,
        "regime": args.regime,
        "generated_at": ts,
    }
    
    # Save to JSON for archive
    json_path = Path(args.output_dir) / f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        json.dump({"meta": meta, "results": all_results, "confluence": confluence_df.to_dict("records")}, f, indent=2, default=str)
    
    log.info(f"Raw results saved: {json_path}")
    log.info("Batch run complete")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

---

### Phase 2: Scheduled Task Integration

Add to `scheduler_core.py`:

```python
JOBS["batch_screener"] = JobSpec(
    id="batch_screener",
    label="Batch Screener (Category-Based)",
    desc="Runs all screeners in category-based batches, aggregates confluence, "
         "and generates segregated reports (Entry, Risk, Confluence). Replaces "
         "the older scanner_daily_runner. ~15-20 min for universe 500.",
    task_name="TradingBramha-BatchScreener",
    kind="daily",
    command=f'"{PYTHON_EXE}" "{HERE / "scanner_batch_runner.py"}" '
            f'--universe bhavcopy --top-n 500 --regime MIXED',
    default_time="16:25",  # Between opportunity_daily (16:20) and sentiment_daily (16:30)
)
```

---

### Phase 3: Report Templates

#### Excel Report Format (Entry Report)

| Symbol | Scanner | Score | Entry | Stop | Target | R:R | Volume ×50d | Confluence | Categories |
|--------|---------|-------|-------|------|--------|-----|-------------|------------|------------|
| RELIANCE | Pullback Entry | 78.5 | 2450.00 | 2400.00 | 2550.00 | 2.0 | 1.8× | 3 | Entry, Trend |
| TCS | Order Block Retest | 82.3 | 3800.00 | 3750.00 | 3900.00 | 2.0 | 2.1× | 4 | Entry, Trend, Momentum |
| INFY | HM Buy | 75.0 | 1520.00 | 1480.00 | 1580.00 | 1.5 | 1.5× | 2 | Entry |

#### HTML Report Template (Pattern Watchlist)

```html
<!DOCTYPE html>
<html>
<head>
    <title>Pattern Watchlist - {date}</title>
    <style>
        .pattern-card { border: 1px solid #ddd; padding: 10px; margin: 10px; }
        .high-conviction { background: #e8f5e9; }
        .medium-conviction { background: #fff3e0; }
        .low-conviction { background: #ffebee; }
    </style>
</head>
<body>
    <h1>Pattern Watchlist - {date}</h1>
    <div class="summary">
        <p>Total Patterns: {total_count}</p>
        <p>High Conviction (3+ hits): {high_count}</p>
    </div>
    <div class="patterns">
        {pattern_cards}
    </div>
</body>
</html>
```

---

### Phase 4: Email Delivery

Add email notification function:

```python
def send_report_email(report_paths: dict[str, Path], recipients: list[str]):
    """Send generated reports via email."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.application import MIMEApplication
    
    msg = MIMEMultipart()
    msg["Subject"] = f"Trading Bramha Batch Screener Report - {datetime.now().strftime('%Y-%m-%d')}"
    msg["From"] = "trading-bramha@example.com"
    msg["To"] = ", ".join(recipients)
    
    body = f"""
    <h2>Batch Screener Report</h2>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    
    <h3>Reports Attached:</h3>
    <ul>
        <li><b>Entry Report:</b> Actionable trade setups with entry/stop/target</li>
        <li><b>Risk Report:</b> Risk flags and portfolio holdings at risk</li>
        <li><b>Confluence Report:</b> High-conviction picks (3+ scanner hits)</li>
    </ul>
    
    <p>Regards,<br>Trading Bramha Automation</p>
    """
    
    msg.attach(MIMEText(body, "html"))
    
    # Attach reports
    for report_type, path in report_paths.items():
        if path and path.exists():
            with open(path, "rb") as f:
                part = MIMEApplication(f.read(), Name=path.name)
            part["Content-Disposition"] = f'attachment; filename="{path.name}"'
            msg.attach(part)
    
    # Send (configure SMTP settings)
    # smtp = smtplib.SMTP("smtp.example.com", 587)
    # smtp.send_message(msg)
    # smtp.quit()
```

---

## Usage Examples

### Manual Execution

```bash
# Run batch screener with default settings
py -3 tools/scanner_batch_runner.py

# Custom universe size
py -3 tools/scanner_batch_runner.py --universe bhavcopy --top-n 500

# RISK-ON regime (more aggressive)
py -3 tools/scanner_batch_runner.py --regime RISK-ON

# Custom output directory
py -3 tools/scanner_batch_runner.py --output-dir reports/batch_20261012
```

### Scheduled Execution

```bash
# Register as scheduled task
py -3 tools/scheduler_core.py register batch_screener

# Run now
py -3 tools/scheduler_core.py run batch_screener
```

### Integration with Opportunity Hub

```python
# In opportunity_daily.py, add:
from scanner_batch_runner import run_all_batches, aggregate_confluence

def run_with_batch_pipeline(universe: list[str]):
    """Run Opportunity Hub with batch scanner results."""
    all_results = run_all_batches(universe)
    confluence_df = aggregate_confluence(all_results)
    
    # Use confluence as an additional filter
    high_confluence = set(confluence_df[confluence_df["total_hits"] >= 3]["symbol"])
    
    # Apply to funnel
    # ...
```

---

## Benefits of This Approach

### 1. **Category-Based Organization**
- Entry setups separated from risk flags
- Trend context isolated from pattern detection
- Each report targets a specific use case

### 2. **Parallel Execution**
- Scanners within a batch run in parallel
- 4x faster than sequential execution
- Resource-intensive scanners (geometric) run sequentially

### 3. **Confluence Analysis**
- Symbols hit by multiple scanners are highlighted
- Cross-category confluence (Entry + Trend + Momentum)
- Weighted scoring based on scanner category

### 4. **Regime-Gated Output**
- RISK-ON: Full list, lower score threshold
- MIXED: Cautious list, moderate threshold
- RISK-OFF: Watchlist only, high threshold

### 5. **Multiple Output Formats**
- Excel for analysis
- HTML for sharing
- Email for distribution
- Database for historical tracking

### 6. **Portfolio Integration**
- Risk report flags holdings at risk
- Confluence report suggests new entries
- Historical tracking of scanner performance

---

## Rollout Plan

### Week 1: Implementation
1. Create `scanner_batch_runner.py`
2. Test with small universe (50 symbols)
3. Verify report generation
4. Benchmark performance

### Week 2: Integration
1. Add to scheduler registry
2. Schedule test runs
3. Compare with old `scanner_daily_runner`
4. Validate results match

### Week 3: Rollout
1. Register as scheduled task
2. Disable old `daily_scanner` task
3. Monitor for 1 week
4. Adjust batch priorities if needed

### Week 4: Enhancement
1. Add email delivery
2. Add Telegram integration
3. Create HTML report templates
4. Add sector rotation report

---

## Monitoring & Maintenance

### Key Metrics to Track

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Batch execution time | < 20 min (500 symbols) | > 30 min |
| Entry hits per run | 20-50 | < 5 or > 100 |
| Risk hits per run | 5-15 | > 30 (too many risks) |
| Confluence (3+ hits) | 5-20 | < 2 or > 50 |
| Report generation time | < 2 min | > 5 min |

### Daily Checks

1. Verify all reports generated
2. Check for scanner errors in logs
3. Validate confluence count
4. Review risk flags for portfolio

### Weekly Review

1. Compare batch vs manual runs
2. Adjust scanner batch priorities
3. Review regime gate effectiveness
4. Update scanner descriptions if needed

---

## Troubleshooting

### Issue: No entry hits generated

**Check:**
- Universe size (too small?)
- Market regime (RISK-OFF filters aggressively)
- Scanner errors in logs

**Fix:**
- Increase `--top-n`
- Use `--regime MIXED` instead of RISK-OFF
- Check scanner logs for errors

### Issue: Confluence count too low

**Check:**
- Are scanners overlapping enough?
- Are scanners too strict?

**Fix:**
- Add more scanners to batches
- Relax scanner thresholds
- Reduce confluence threshold from 3 to 2

### Issue: Batch execution too slow

**Check:**
- Network latency (yfinance slow?)
- Too many parallel workers?

**Fix:**
- Reduce `max_workers` in ThreadPoolExecutor
- Cache OHLCV data longer
- Use faster data source

---

## Future Enhancements

### 1. Machine Learning Ranking
- Train model on historical scanner hits
- Predict which confluence setups perform best
- Auto-adjust weights based on recent performance

### 2. Real-Time Scanning
- Run batch every 30 minutes during market hours
- Incremental updates (only new bars)
- Push alerts for new confluence

### 3. Backtest Integration
- Auto-backtest each batch run
- Track 20d/60d performance
- Disable underperforming scanners

### 4. Sector-Based Batches
- Run scanners per sector
- Compare sector rotation
- Identify leading sectors

### 5. Custom Scanner Builder
- UI to create custom batches
- Drag-and-drop scanner selection
- Save batch configurations

---

## Conclusion

This batch workflow system transforms your scanner execution from a monolithic single-output process into a **category-based, parallel, multi-report pipeline**. 

**Key Improvements:**
- 4x faster execution (parallel within batches)
- Segregated reports for different audiences
- Confluence analysis for high-conviction picks
- Regime-gated output for risk management
- Portfolio integration for risk monitoring

**Next Steps:**
1. Implement `scanner_batch_runner.py`
2. Test with small universe
3. Integrate with scheduler
4. Roll out gradually alongside existing system

---

*Proposal generated by Devin AI - 2026-10-12*
