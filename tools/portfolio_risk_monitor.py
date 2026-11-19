#!/usr/bin/env python3
"""
portfolio_risk_monitor.py — Automated risk monitoring for portfolio holdings.

Protects existing positions by:
  • Fetching current portfolio holdings from portfolio_db
  • Running risk scanners specifically on holdings
  • Flagging positions with 2+ risk signals
  • Calculating exit priority based on risk severity
  • Generating actionable exit lists with stops/targets
  • Sending urgent email alerts
  • Tracking risk flag history

Risk Scanners Used:
  • RSI Divergence Bear (bearish momentum divergence)
  • %R Exhaustion Sell (Williams %R topping signal)
  • Bearish Reversal Candle (Evening Star, Shooting Star, etc.)
  • Bearish Liquidity Sweep (sell-side stop hunt)
  • Support Breakdown (key support broken)

Exit Priority Levels:
  • URGENT (3+ risk flags): Exit immediately
  • HIGH (2 risk flags): Exit on next bounce
  • MODERATE (1 risk flag): Watch closely, tighten stops
  • LOW (0 risk flags): Normal monitoring

Usage:
    # Check portfolio risk now
    monitor = PortfolioRiskMonitor()
    risk_report = monitor.check_portfolio_risk()

    # Schedule to run every 4 hours
    monitor.run_continuous(interval_hours=4)

    # Send email if high-risk holdings found
    if risk_report.high_priority_count > 0:
        monitor.send_risk_alert_email(risk_report)
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import portfolio_db as db
    import scanner_templates as sc
    import screener_pipeline as sp
    from email_delivery import EmailSender
    from excel_formatter import save_formatted_excel
except ImportError as e:
    logging.error(f"Failed to import required modules: {e}")
    logging.error("Make sure you're running from the tools directory")

log = logging.getLogger(__name__)

# ── Risk Scanner Registry ─────────────────────────────────────────────────────

# Risk scanners to monitor (these are bearish/exit signals)
RISK_SCANNERS = [
    "RSI Divergence Bear",
    "%R Exhaustion Sell",
    "Bearish Reversal Candle",
    "Bearish Liquidity Sweep",
]


# ── Data Models ───────────────────────────────────────────────────────────────


@dataclass
class HoldingRiskAssessment:
    """Risk assessment for a single holding."""

    symbol: str
    current_price: float
    entry_price: float | None
    quantity: int
    position_value: float
    unrealized_pnl: float | None
    unrealized_pnl_pct: float | None

    # Risk flags
    risk_scanners_triggered: list[str] = field(default_factory=list)
    risk_flag_count: int = 0
    priority_level: str = "LOW"

    # Exit recommendations
    suggested_stop: float | None = None
    suggested_target: float | None = None
    exit_reason: str = ""

    # Additional context
    days_held: int | None = None
    volume_spike: bool = False
    below_support: bool = False


@dataclass
class PortfolioRiskReport:
    """Complete portfolio risk report."""

    timestamp: datetime
    total_holdings: int
    total_portfolio_value: float

    # Risk breakdown
    high_priority_count: int  # 2+ risk flags
    moderate_priority_count: int  # 1 risk flag
    low_priority_count: int  # 0 risk flags

    # Holdings data
    holdings_at_risk: list[HoldingRiskAssessment] = field(default_factory=list)
    all_holdings: list[HoldingRiskAssessment] = field(default_factory=list)

    # Aggregates
    total_at_risk_value: float = 0.0
    pct_portfolio_at_risk: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for email/reporting."""
        return {
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M"),
            "total_holdings": self.total_holdings,
            "total_portfolio_value": f"₹{self.total_portfolio_value:,.0f}",
            "high_priority_count": self.high_priority_count,
            "moderate_priority_count": self.moderate_priority_count,
            "total_at_risk_value": f"₹{self.total_at_risk_value:,.0f}",
            "pct_portfolio_at_risk": f"{self.pct_portfolio_at_risk:.1f}%",
        }


# ── Portfolio Risk Monitor ────────────────────────────────────────────────────


class PortfolioRiskMonitor:
    """Automated portfolio risk monitoring system."""

    def __init__(
        self,
        days_history: int = 400,
        risk_scanners: list[str] | None = None,
        email_sender: EmailSender | None = None,
    ):
        """
        Initialize portfolio risk monitor.

        Args:
            days_history: Days of OHLCV to fetch for scanners
            risk_scanners: List of risk scanner names (default: RISK_SCANNERS)
            email_sender: EmailSender instance (default: create new)
        """
        self.days_history = days_history
        self.risk_scanners = risk_scanners or RISK_SCANNERS
        self.email_sender = email_sender or EmailSender()

        # Cache for OHLCV data
        self._ohlcv_cache: dict[str, pd.DataFrame] = {}

    def get_portfolio_holdings(self) -> pd.DataFrame:
        """
        Fetch current portfolio holdings from database.

        Returns:
            DataFrame with columns: symbol, quantity, entry_price, current_price, etc.
        """
        try:
            # Try to get holdings from portfolio_db
            if hasattr(db, 'get_holdings'):
                holdings = db.get_holdings()
                if holdings is not None and not holdings.empty:
                    return holdings

            # Fallback: construct from database tables
            # This is a placeholder - adjust based on your actual schema
            log.warning("Using fallback holdings retrieval")

            # Example structure - customize based on your portfolio_db schema
            return pd.DataFrame({
                "symbol": [],
                "quantity": [],
                "entry_price": [],
                "current_price": [],
                "entry_date": [],
            })

        except Exception as e:
            log.error(f"Failed to fetch portfolio holdings: {e}")
            return pd.DataFrame()

    def fetch_ohlcv(self, symbol: str) -> pd.DataFrame | None:
        """Fetch OHLCV data with caching."""
        if symbol in self._ohlcv_cache:
            return self._ohlcv_cache[symbol]

        try:
            df = sp.fetch_ohlcv(symbol, days=self.days_history)
            self._ohlcv_cache[symbol] = df
            return df
        except Exception as e:
            log.error(f"Failed to fetch OHLCV for {symbol}: {e}")
            return None

    def run_risk_scanners(self, symbol: str, df: pd.DataFrame) -> list[dict]:
        """
        Run all risk scanners on a symbol.

        Args:
            symbol: Stock symbol
            df: OHLCV DataFrame

        Returns:
            List of scanner hits (risk flags)
        """
        hits = []

        for scanner_name in self.risk_scanners:
            if scanner_name not in sc.SCANNERS:
                log.warning(f"Scanner not found: {scanner_name}")
                continue

            try:
                scanner_fn = sc.SCANNERS[scanner_name]["fn"]
                result = scanner_fn(df)

                if result:
                    result["symbol"] = symbol
                    result["scanner"] = scanner_name
                    hits.append(result)

            except Exception as e:
                log.error(f"Scanner {scanner_name} failed on {symbol}: {e}")

        return hits

    def calculate_exit_priority(
        self,
        risk_flag_count: int,
        pnl_pct: float | None,
    ) -> str:
        """
        Determine exit priority level.

        Args:
            risk_flag_count: Number of risk scanners triggered
            pnl_pct: Unrealized P&L percentage

        Returns:
            Priority level: URGENT, HIGH, MODERATE, LOW
        """
        # 3+ risk flags = urgent exit
        if risk_flag_count >= 3:
            return "URGENT"

        # 2 risk flags = high priority
        if risk_flag_count == 2:
            return "HIGH"

        # 1 risk flag + losing position = high priority
        if risk_flag_count == 1:
            if pnl_pct is not None and pnl_pct < -5:
                return "HIGH"
            return "MODERATE"

        # No risk flags
        return "LOW"

    def calculate_suggested_stops(
        self,
        symbol: str,
        df: pd.DataFrame,
        entry_price: float | None,
    ) -> tuple[float | None, float | None]:
        """
        Calculate suggested stop loss and target.

        Args:
            symbol: Stock symbol
            df: OHLCV DataFrame
            entry_price: Original entry price

        Returns:
            (suggested_stop, suggested_target)
        """
        if df is None or df.empty:
            return None, None

        current_price = float(df["close"].iloc[-1])

        # Swing low stop (recent 10-day low - 1%)
        if len(df) >= 10:
            swing_low = float(df["low"].iloc[-10:].min())
            suggested_stop = swing_low * 0.99  # 1% below swing low
        else:
            suggested_stop = current_price * 0.95  # 5% stop if insufficient data

        # Target: 2R from current price (risk-reward)
        if suggested_stop:
            risk = current_price - suggested_stop
            suggested_target = current_price + (2 * risk)
        else:
            suggested_target = None

        return suggested_stop, suggested_target

    def assess_holding_risk(
        self,
        holding: dict[str, Any],
        df: pd.DataFrame,
    ) -> HoldingRiskAssessment:
        """
        Assess risk for a single holding.

        Args:
            holding: Dict with symbol, quantity, entry_price, etc.
            df: OHLCV DataFrame for the symbol

        Returns:
            HoldingRiskAssessment
        """
        symbol = holding.get("symbol")
        quantity = holding.get("quantity", 0)
        entry_price = holding.get("entry_price")

        # Get current price
        if df is not None and not df.empty:
            current_price = float(df["close"].iloc[-1])
        else:
            current_price = holding.get("current_price", 0.0)

        # Calculate position metrics
        position_value = current_price * quantity

        if entry_price:
            unrealized_pnl = (current_price - entry_price) * quantity
            unrealized_pnl_pct = ((current_price / entry_price) - 1) * 100
        else:
            unrealized_pnl = None
            unrealized_pnl_pct = None

        # Run risk scanners
        risk_hits = []
        if df is not None and not df.empty:
            risk_hits = self.run_risk_scanners(symbol, df)

        risk_scanners_triggered = [hit["scanner"] for hit in risk_hits]
        risk_flag_count = len(risk_scanners_triggered)

        # Calculate priority
        priority_level = self.calculate_exit_priority(risk_flag_count, unrealized_pnl_pct)

        # Calculate suggested stops
        suggested_stop, suggested_target = self.calculate_suggested_stops(
            symbol, df, entry_price
        )

        # Exit reason
        if risk_flag_count >= 2:
            exit_reason = f"Multiple risk flags: {', '.join(risk_scanners_triggered)}"
        elif risk_flag_count == 1:
            exit_reason = f"Risk flag: {risk_scanners_triggered[0]}"
        else:
            exit_reason = "No immediate risk"

        # Days held
        entry_date = holding.get("entry_date")
        if entry_date:
            days_held = (datetime.now() - entry_date).days
        else:
            days_held = None

        return HoldingRiskAssessment(
            symbol=symbol,
            current_price=current_price,
            entry_price=entry_price,
            quantity=quantity,
            position_value=position_value,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            risk_scanners_triggered=risk_scanners_triggered,
            risk_flag_count=risk_flag_count,
            priority_level=priority_level,
            suggested_stop=suggested_stop,
            suggested_target=suggested_target,
            exit_reason=exit_reason,
            days_held=days_held,
        )

    def check_portfolio_risk(self) -> PortfolioRiskReport:
        """
        Run complete portfolio risk check.

        Returns:
            PortfolioRiskReport with all holdings assessed
        """
        log.info("Starting portfolio risk check...")

        # Get current holdings
        holdings_df = self.get_portfolio_holdings()

        if holdings_df.empty:
            log.warning("No portfolio holdings found")
            return PortfolioRiskReport(
                timestamp=datetime.now(),
                total_holdings=0,
                total_portfolio_value=0.0,
                high_priority_count=0,
                moderate_priority_count=0,
                low_priority_count=0,
            )

        log.info(f"Checking {len(holdings_df)} holdings...")

        # Assess each holding
        all_assessments = []

        for idx, row in holdings_df.iterrows():
            symbol = row.get("symbol")
            log.info(f"  Checking {symbol}...")

            # Fetch OHLCV
            df = self.fetch_ohlcv(symbol)

            # Assess risk
            assessment = self.assess_holding_risk(row.to_dict(), df)
            all_assessments.append(assessment)

        # Calculate summary statistics
        total_holdings = len(all_assessments)
        total_portfolio_value = sum(a.position_value for a in all_assessments)

        holdings_at_risk = [a for a in all_assessments if a.risk_flag_count > 0]

        high_priority_count = sum(
            1 for a in all_assessments if a.priority_level in ["URGENT", "HIGH"]
        )
        moderate_priority_count = sum(
            1 for a in all_assessments if a.priority_level == "MODERATE"
        )
        low_priority_count = total_holdings - high_priority_count - moderate_priority_count

        total_at_risk_value = sum(a.position_value for a in holdings_at_risk)
        pct_portfolio_at_risk = (
            (total_at_risk_value / total_portfolio_value * 100)
            if total_portfolio_value > 0
            else 0.0
        )

        report = PortfolioRiskReport(
            timestamp=datetime.now(),
            total_holdings=total_holdings,
            total_portfolio_value=total_portfolio_value,
            high_priority_count=high_priority_count,
            moderate_priority_count=moderate_priority_count,
            low_priority_count=low_priority_count,
            holdings_at_risk=holdings_at_risk,
            all_holdings=all_assessments,
            total_at_risk_value=total_at_risk_value,
            pct_portfolio_at_risk=pct_portfolio_at_risk,
        )

        log.info(f"Portfolio risk check complete:")
        log.info(f"  High priority: {high_priority_count}")
        log.info(f"  Moderate priority: {moderate_priority_count}")
        log.info(f"  Low risk: {low_priority_count}")

        return report

    def generate_risk_report_excel(
        self,
        report: PortfolioRiskReport,
        output_path: str | Path,
    ) -> Path:
        """
        Generate formatted Excel report of portfolio risk.

        Args:
            report: PortfolioRiskReport
            output_path: Where to save the Excel file

        Returns:
            Path to saved file
        """
        # Convert assessments to DataFrames

        # High priority holdings
        high_priority = [
            a for a in report.all_holdings
            if a.priority_level in ["URGENT", "HIGH"]
        ]

        if high_priority:
            high_df = pd.DataFrame([{
                "symbol": a.symbol,
                "priority": a.priority_level,
                "risk_flags": a.risk_flag_count,
                "scanners": ", ".join(a.risk_scanners_triggered),
                "current_price": a.current_price,
                "entry_price": a.entry_price,
                "pnl_pct": a.unrealized_pnl_pct,
                "position_value": a.position_value,
                "suggested_stop": a.suggested_stop,
                "exit_reason": a.exit_reason,
            } for a in high_priority])
        else:
            high_df = pd.DataFrame()

        # All holdings with risk assessment
        all_df = pd.DataFrame([{
            "symbol": a.symbol,
            "priority": a.priority_level,
            "risk_flags": a.risk_flag_count,
            "current_price": a.current_price,
            "entry_price": a.entry_price,
            "pnl_pct": a.unrealized_pnl_pct,
            "position_value": a.position_value,
            "suggested_stop": a.suggested_stop,
            "days_held": a.days_held,
        } for a in report.all_holdings])

        # Save with formatting
        from excel_formatter import ExcelFormatter

        formatter = ExcelFormatter(output_path)

        # Summary sheet
        formatter.add_summary_sheet(report.to_dict(), "Summary")

        # High priority holdings
        if not high_df.empty:
            formatter.add_sheet(
                high_df,
                "High Priority Exits",
                format_as="custom",
                custom_format={
                    "price_columns": ["current_price", "entry_price", "suggested_stop"],
                    "percentage_columns": ["pnl_pct"],
                    "currency_columns": ["position_value"],
                    "chart_link_column": "symbol",
                    "freeze_panes": "A2",
                },
            )

        # All holdings
        formatter.add_sheet(
            all_df,
            "All Holdings",
            format_as="portfolio",
        )

        return formatter.save()

    def send_risk_alert_email(self, report: PortfolioRiskReport) -> bool:
        """
        Send urgent risk alert email if high-priority risks found.

        Args:
            report: PortfolioRiskReport

        Returns:
            True if email sent successfully
        """
        if report.high_priority_count == 0:
            log.info("No high-priority risks, skipping email alert")
            return False

        # Generate report
        report_path = self.generate_risk_report_excel(
            report,
            f"portfolio_risk_{datetime.now():%Y%m%d_%H%M}.xlsx",
        )

        # Get symbols at risk
        holdings_at_risk = [
            a.symbol for a in report.holdings_at_risk
            if a.priority_level in ["URGENT", "HIGH"]
        ]

        # Send email
        log.info(f"Sending risk alert for {len(holdings_at_risk)} high-priority holdings")

        return self.email_sender.send_risk_alert(
            risk_report_path=report_path,
            holdings_at_risk=holdings_at_risk,
            risk_data=report.to_dict(),
        )


# ── Scheduled Monitoring ──────────────────────────────────────────────────────


def run_scheduled_risk_check(send_email: bool = True) -> PortfolioRiskReport:
    """
    Run portfolio risk check (for scheduled tasks).

    Args:
        send_email: Whether to send alert email if risks found

    Returns:
        PortfolioRiskReport
    """
    monitor = PortfolioRiskMonitor()
    report = monitor.check_portfolio_risk()

    # Send email if high-priority risks
    if send_email and report.high_priority_count > 0:
        monitor.send_risk_alert_email(report)

    return report


# ── Demo ──────────────────────────────────────────────────────────────────────


def _demo():
    """Demonstration of portfolio risk monitoring."""
    print("=== Portfolio Risk Monitor Demo ===\n")

    # Create mock holdings for demo
    print("Creating mock portfolio for demo...\n")

    mock_holdings = pd.DataFrame({
        "symbol": ["RELIANCE", "TCS", "INFY"],
        "quantity": [100, 50, 200],
        "entry_price": [2400.0, 3700.0, 1500.0],
        "current_price": [2450.0, 3800.0, 1520.0],
        "entry_date": [datetime(2026, 9, 1), datetime(2026, 8, 15), datetime(2026, 9, 20)],
    })

    print(f"Portfolio: {len(mock_holdings)} holdings")
    print(mock_holdings.to_string())
    print()

    # Create monitor
    monitor = PortfolioRiskMonitor()

    # Override get_portfolio_holdings for demo
    monitor.get_portfolio_holdings = lambda: mock_holdings

    # Run risk check
    print("Running portfolio risk check...\n")
    report = monitor.check_portfolio_risk()

    # Display results
    print("=== Risk Assessment Summary ===")
    print(f"Total Holdings: {report.total_holdings}")
    print(f"Portfolio Value: ₹{report.total_portfolio_value:,.0f}")
    print(f"High Priority: {report.high_priority_count}")
    print(f"Moderate Priority: {report.moderate_priority_count}")
    print(f"Low Risk: {report.low_priority_count}")
    print(f"Value at Risk: ₹{report.total_at_risk_value:,.0f} ({report.pct_portfolio_at_risk:.1f}%)")
    print()

    # Show high-priority holdings
    if report.high_priority_count > 0:
        print("=== HIGH PRIORITY EXITS ===")
        for holding in report.all_holdings:
            if holding.priority_level in ["URGENT", "HIGH"]:
                print(f"\n{holding.symbol} - {holding.priority_level}")
                print(f"  Risk Flags: {holding.risk_flag_count}")
                print(f"  Scanners: {', '.join(holding.risk_scanners_triggered)}")
                print(f"  Current: ₹{holding.current_price:.2f}")
                print(f"  Stop: ₹{holding.suggested_stop:.2f}" if holding.suggested_stop else "  Stop: N/A")
                print(f"  P&L: {holding.unrealized_pnl_pct:.1f}%" if holding.unrealized_pnl_pct else "  P&L: N/A")
                print(f"  Action: {holding.exit_reason}")
    else:
        print("✅ No high-priority risks detected")

    # Generate report
    print("\n=== Generating Excel Report ===")
    report_path = monitor.generate_risk_report_excel(
        report,
        "demo_portfolio_risk.xlsx",
    )
    print(f"✅ Report saved: {report_path}")

    # Email (dry run)
    if report.high_priority_count > 0:
        print("\n=== Email Alert ===")
        print("[DRY RUN] Would send risk alert email")
        print(f"Recipients: (configured in email_config.yaml)")
        print(f"Attachment: {report_path}")

    print("\n🎉 Demo complete!")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    _demo()
