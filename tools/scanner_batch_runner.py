#!/usr/bin/env python3
"""
scanner_batch_runner.py - Category-based batch execution of screeners.

Runs scanners in predefined batches by category, aggregates results,
and generates segregated reports for different use cases.
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import screener_pipeline as sp
import scanner_templates as sc
from opportunity_daily import _FetchRouter
import portfolio_db as db

log = logging.getLogger("scanner_batch")

DEFAULT_DAYS = 400
DEFAULT_TOP_N = 300
CACHE_DIR = Path(__file__).resolve().parent / "cache"
REPORTS_DIR = Path(__file__).resolve().parent / "reports" / "batch"


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
    # Simplified regime gates
    regime_gates = {
        "RISK-ON": {"min_score": 45, "max_names": None},
        "MIXED": {"min_score": 55, "max_names": 40},
        "RISK-OFF": {"min_score": 65, "max_names": 5},
    }
    
    gate = regime_gates.get(regime, regime_gates["MIXED"])
    
    if gate["min_score"]:
        df = df[df["max_score"] >= gate["min_score"]].copy()
    
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
    ) -> Path | None:
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
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        path = self.output_dir / f"entry_report_{ts}.xlsx"
        
        try:
            import openpyxl
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
        except ImportError:
            log.warning("openpyxl not installed, skipping Excel export")
            return None
    
    def generate_risk_report(
        self,
        all_results: dict[str, dict[str, list[dict]]],
        portfolio_symbols: list[str] | None = None,
    ) -> Path | None:
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
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        path = self.output_dir / f"risk_report_{ts}.xlsx"
        
        try:
            import openpyxl
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Risk Flags", index=False)
                
                if portfolio_symbols:
                    portfolio_risks = df[df["in_portfolio"]]
                    portfolio_risks.to_excel(writer, sheet_name="Portfolio at Risk", index=False)
            
            log.info(f"Risk report saved: {path}")
            return path
        except ImportError:
            log.warning("openpyxl not installed, skipping Excel export")
            return None
    
    def generate_confluence_report(
        self,
        confluence_df: pd.DataFrame,
        regime: str = "MIXED",
    ) -> Path | None:
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
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        path = self.output_dir / f"confluence_report_{ts}.xlsx"
        
        try:
            import openpyxl
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                top_picks.to_excel(writer, sheet_name="Top Picks", index=False)
                filtered_df.to_excel(writer, sheet_name="All Qualified", index=False)
            
            log.info(f"Confluence report saved: {path}")
            return path
        except ImportError:
            log.warning("openpyxl not installed, skipping Excel export")
            return None
    
    def generate_all_reports(
        self,
        all_results: dict[str, dict[str, list[dict]]],
        confluence_df: pd.DataFrame,
        regime: str = "MIXED",
    ) -> dict[str, Path | None]:
        """Generate all reports."""
        paths = {}
        
        # Entry report
        paths["entry"] = self.generate_entry_report(all_results, confluence_df)
        
        # Risk report
        portfolio_symbols = self._get_portfolio_symbols()
        paths["risk"] = self.generate_risk_report(all_results, portfolio_symbols)
        
        # Confluence report
        paths["confluence"] = self.generate_confluence_report(confluence_df, regime)
        
        return paths
    
    def _get_portfolio_symbols(self) -> list[str]:
        """Get portfolio symbols from database."""
        try:
            return db.get_portfolio_symbols() if hasattr(db, "get_portfolio_symbols") else []
        except Exception:
            return []


# ── Main Pipeline ───────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Batch screener execution with segregated reports")
    ap.add_argument("--universe", default="bhavcopy", choices=["bhavcopy", "screener"])
    ap.add_argument("--top-n", type=int, default=DEFAULT_TOP_N,
                    help=f"bhavcopy universe size (default {DEFAULT_TOP_N})")
    ap.add_argument("--days", type=int, default=DEFAULT_DAYS)
    ap.add_argument("--regime", default="MIXED", choices=["RISK-ON", "MIXED", "RISK-OFF"])
    ap.add_argument("--output-dir", default=str(REPORTS_DIR), type=str)
    
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
    
    # Save raw results to JSON
    ts = datetime.datetime.now().isoformat()
    meta = {
        "universe_mode": args.universe,
        "universe_size": len(universe),
        "days": args.days,
        "regime": args.regime,
        "generated_at": ts,
    }
    
    json_path = Path(args.output_dir) / f"batch_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        json.dump({"meta": meta, "results": all_results, "confluence": confluence_df.to_dict("records")}, f, indent=2, default=str)
    
    log.info(f"Raw results saved: {json_path}")
    log.info("Batch run complete")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
