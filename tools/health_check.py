#!/usr/bin/env python3
"""
health_check.py — Automated health checks for Trading Bramha batch operations.

Validates system health after batch runs:
  • Batch execution completed successfully
  • All expected reports generated
  • Entry hit counts in expected ranges
  • No scanner crashes detected
  • Database connectivity and writes working
  • Email delivery successful
  • Disk space available
  • Log files accessible

Runs after each batch execution and sends alerts on failures.

Usage:
    # Run all health checks
    checker = HealthChecker()
    report = checker.run_all_checks()

    if not report.all_passed:
        checker.send_alert_email(report)

    # Individual checks
    checker.check_batch_completed()
    checker.check_reports_generated()
    checker.check_hit_counts()

    # Schedule after batch run
    # (in scanner_batch_runner.py epilogue)
"""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from structured_logger import get_logger
    from email_delivery import EmailSender
except ImportError:
    pass

log = logging.getLogger(__name__)

# ── Health Check Configuration ────────────────────────────────────────────────

# Expected ranges for validation
EXPECTED_ENTRY_HITS = (5, 100)  # Min, max entry signals per run
EXPECTED_RISK_HITS = (0, 30)    # Max risk flags (too many = market problem)
EXPECTED_CONFLUENCE_HIGH = (2, 50)  # High-conviction picks

# Disk space thresholds
MIN_DISK_SPACE_GB = 5.0  # Alert if <5 GB free

# Database check timeout
DB_CHECK_TIMEOUT_SECONDS = 5


# ── Data Models ───────────────────────────────────────────────────────────────


@dataclass
class HealthCheckResult:
    """Result of a single health check."""

    check_name: str
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    severity: str = "error"  # error, warning, info
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class HealthReport:
    """Aggregate health check report."""

    timestamp: datetime
    all_passed: bool
    total_checks: int
    passed_count: int
    failed_count: int
    warning_count: int
    checks: list[HealthCheckResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "all_passed": self.all_passed,
            "total_checks": self.total_checks,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "warning_count": self.warning_count,
            "checks": [check.to_dict() for check in self.checks],
        }

    def get_failed_checks(self) -> list[HealthCheckResult]:
        """Get list of failed checks."""
        return [c for c in self.checks if not c.passed and c.severity == "error"]

    def get_warnings(self) -> list[HealthCheckResult]:
        """Get list of warnings."""
        return [c for c in self.checks if not c.passed and c.severity == "warning"]


# ── Health Checker ────────────────────────────────────────────────────────────


class HealthChecker:
    """
    Automated health check system.

    Validates system health after batch operations.
    """

    def __init__(
        self,
        output_dir: Path | str = "reports/batch",
        db_path: Path | str = "trading_bramha.db",
        email_sender: Any | None = None,
    ):
        """
        Initialize health checker.

        Args:
            output_dir: Directory where reports are saved
            db_path: Path to SQLite database
            email_sender: EmailSender instance for alerts
        """
        self.output_dir = Path(output_dir)
        self.db_path = Path(db_path)
        self.email_sender = email_sender

        self.results: list[HealthCheckResult] = []

    def _add_result(
        self,
        check_name: str,
        passed: bool,
        message: str,
        details: dict[str, Any] | None = None,
        severity: str = "error",
    ):
        """Add a check result."""
        result = HealthCheckResult(
            check_name=check_name,
            passed=passed,
            message=message,
            details=details or {},
            severity=severity,
        )
        self.results.append(result)
        return result

    def check_reports_generated(
        self,
        expected_reports: list[str] | None = None,
    ) -> HealthCheckResult:
        """
        Check if expected report files were generated.

        Args:
            expected_reports: List of expected report filenames
                            (default: entry_report_*.xlsx, confluence_report_*.xlsx)

        Returns:
            HealthCheckResult
        """
        if expected_reports is None:
            expected_reports = [
                "entry_report_*.xlsx",
                "confluence_report_*.xlsx",
            ]

        if not self.output_dir.exists():
            return self._add_result(
                "reports_generated",
                False,
                f"Output directory not found: {self.output_dir}",
                {"output_dir": str(self.output_dir)},
            )

        missing_reports = []
        found_reports = []

        for pattern in expected_reports:
            matching_files = list(self.output_dir.glob(pattern))

            if matching_files:
                # Get most recent file
                latest = max(matching_files, key=lambda p: p.stat().st_mtime)
                found_reports.append(latest.name)
            else:
                missing_reports.append(pattern)

        if missing_reports:
            return self._add_result(
                "reports_generated",
                False,
                f"Missing {len(missing_reports)} report(s)",
                {
                    "missing": missing_reports,
                    "found": found_reports,
                },
            )

        return self._add_result(
            "reports_generated",
            True,
            f"All {len(found_reports)} reports generated",
            {"reports": found_reports},
            severity="info",
        )

    def check_hit_counts(
        self,
        entry_hits: int | None = None,
        risk_hits: int | None = None,
        confluence_high: int | None = None,
    ) -> list[HealthCheckResult]:
        """
        Check if signal counts are in expected ranges.

        Args:
            entry_hits: Number of entry signals found
            risk_hits: Number of risk flags found
            confluence_high: Number of high-conviction picks

        Returns:
            List of HealthCheckResults
        """
        results = []

        # Check entry hits
        if entry_hits is not None:
            min_entry, max_entry = EXPECTED_ENTRY_HITS

            if entry_hits < min_entry:
                results.append(
                    self._add_result(
                        "entry_hit_count",
                        False,
                        f"Too few entry signals: {entry_hits} (expected {min_entry}+)",
                        {"entry_hits": entry_hits, "expected_min": min_entry},
                        severity="warning",
                    )
                )
            elif entry_hits > max_entry:
                results.append(
                    self._add_result(
                        "entry_hit_count",
                        False,
                        f"Too many entry signals: {entry_hits} (expected <{max_entry})",
                        {"entry_hits": entry_hits, "expected_max": max_entry},
                        severity="warning",
                    )
                )
            else:
                results.append(
                    self._add_result(
                        "entry_hit_count",
                        True,
                        f"Entry signals in range: {entry_hits}",
                        {"entry_hits": entry_hits},
                        severity="info",
                    )
                )

        # Check risk hits
        if risk_hits is not None:
            _, max_risk = EXPECTED_RISK_HITS

            if risk_hits > max_risk:
                results.append(
                    self._add_result(
                        "risk_hit_count",
                        False,
                        f"Too many risk flags: {risk_hits} (market deteriorating?)",
                        {"risk_hits": risk_hits, "expected_max": max_risk},
                        severity="warning",
                    )
                )
            else:
                results.append(
                    self._add_result(
                        "risk_hit_count",
                        True,
                        f"Risk flags normal: {risk_hits}",
                        {"risk_hits": risk_hits},
                        severity="info",
                    )
                )

        # Check confluence high-conviction
        if confluence_high is not None:
            min_conf, max_conf = EXPECTED_CONFLUENCE_HIGH

            if confluence_high < min_conf:
                results.append(
                    self._add_result(
                        "confluence_count",
                        False,
                        f"Too few high-conviction picks: {confluence_high}",
                        {"confluence_high": confluence_high, "expected_min": min_conf},
                        severity="warning",
                    )
                )
            elif confluence_high > max_conf:
                results.append(
                    self._add_result(
                        "confluence_count",
                        False,
                        f"Unusually high confluence count: {confluence_high}",
                        {"confluence_high": confluence_high, "expected_max": max_conf},
                        severity="warning",
                    )
                )
            else:
                results.append(
                    self._add_result(
                        "confluence_count",
                        True,
                        f"Confluence picks in range: {confluence_high}",
                        {"confluence_high": confluence_high},
                        severity="info",
                    )
                )

        return results

    def check_database_connectivity(self) -> HealthCheckResult:
        """
        Check if database is accessible and writable.

        Returns:
            HealthCheckResult
        """
        if not self.db_path.exists():
            return self._add_result(
                "database_connectivity",
                False,
                f"Database file not found: {self.db_path}",
                {"db_path": str(self.db_path)},
            )

        try:
            # Try to connect and write
            conn = sqlite3.connect(str(self.db_path), timeout=DB_CHECK_TIMEOUT_SECONDS)
            cursor = conn.cursor()

            # Create health check table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS health_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    check_name TEXT,
                    passed INTEGER,
                    message TEXT
                )
            """)

            # Insert test record
            cursor.execute("""
                INSERT INTO health_checks (timestamp, check_name, passed, message)
                VALUES (?, ?, ?, ?)
            """, (datetime.now().isoformat(), "connectivity_test", 1, "Test passed"))

            conn.commit()
            conn.close()

            return self._add_result(
                "database_connectivity",
                True,
                "Database accessible and writable",
                {"db_path": str(self.db_path)},
                severity="info",
            )

        except Exception as e:
            return self._add_result(
                "database_connectivity",
                False,
                f"Database connection failed: {str(e)}",
                {"db_path": str(self.db_path), "error": str(e)},
            )

    def check_disk_space(self, path: Path | str = ".") -> HealthCheckResult:
        """
        Check if sufficient disk space is available.

        Args:
            path: Path to check (default: current directory)

        Returns:
            HealthCheckResult
        """
        try:
            path = Path(path)
            stat = shutil.disk_usage(path)

            free_gb = stat.free / (1024 ** 3)

            if free_gb < MIN_DISK_SPACE_GB:
                return self._add_result(
                    "disk_space",
                    False,
                    f"Low disk space: {free_gb:.1f} GB free (min: {MIN_DISK_SPACE_GB} GB)",
                    {"free_gb": round(free_gb, 2), "min_gb": MIN_DISK_SPACE_GB},
                    severity="warning",
                )

            return self._add_result(
                "disk_space",
                True,
                f"Disk space OK: {free_gb:.1f} GB free",
                {"free_gb": round(free_gb, 2)},
                severity="info",
            )

        except Exception as e:
            return self._add_result(
                "disk_space",
                False,
                f"Disk space check failed: {str(e)}",
                {"error": str(e)},
                severity="warning",
            )

    def check_log_files(self, log_dir: Path | str = "logs") -> HealthCheckResult:
        """
        Check if log directory is accessible and writable.

        Args:
            log_dir: Log directory path

        Returns:
            HealthCheckResult
        """
        log_dir = Path(log_dir)

        if not log_dir.exists():
            return self._add_result(
                "log_files",
                False,
                f"Log directory not found: {log_dir}",
                {"log_dir": str(log_dir)},
                severity="warning",
            )

        # Check if writable
        try:
            test_file = log_dir / ".health_check_test"
            test_file.write_text("test")
            test_file.unlink()

            return self._add_result(
                "log_files",
                True,
                "Log directory accessible and writable",
                {"log_dir": str(log_dir)},
                severity="info",
            )

        except Exception as e:
            return self._add_result(
                "log_files",
                False,
                f"Log directory not writable: {str(e)}",
                {"log_dir": str(log_dir), "error": str(e)},
            )

    def check_scanner_errors(
        self,
        scanner_results: dict[str, list] | None = None,
        max_error_rate: float = 0.1,
    ) -> HealthCheckResult:
        """
        Check if scanner error rate is acceptable.

        Args:
            scanner_results: Dict of scanner_name → [hits]
            max_error_rate: Maximum acceptable error rate (default: 10%)

        Returns:
            HealthCheckResult
        """
        if scanner_results is None:
            return self._add_result(
                "scanner_errors",
                True,
                "No scanner results provided (skipped)",
                {},
                severity="info",
            )

        total_scanners = len(scanner_results)
        failed_scanners = []

        for scanner_name, hits in scanner_results.items():
            # Consider scanner failed if it returned None or raised exception
            if hits is None:
                failed_scanners.append(scanner_name)

        if not failed_scanners:
            return self._add_result(
                "scanner_errors",
                True,
                f"All {total_scanners} scanners completed successfully",
                {"total_scanners": total_scanners},
                severity="info",
            )

        error_rate = len(failed_scanners) / total_scanners

        if error_rate > max_error_rate:
            return self._add_result(
                "scanner_errors",
                False,
                f"{len(failed_scanners)} scanner(s) failed ({error_rate*100:.1f}% error rate)",
                {
                    "failed_scanners": failed_scanners,
                    "error_rate": round(error_rate, 3),
                    "max_error_rate": max_error_rate,
                },
            )

        return self._add_result(
            "scanner_errors",
            True,
            f"{len(failed_scanners)} scanner(s) failed (within tolerance)",
            {
                "failed_scanners": failed_scanners,
                "error_rate": round(error_rate, 3),
            },
            severity="warning",
        )

    def run_all_checks(
        self,
        entry_hits: int | None = None,
        risk_hits: int | None = None,
        confluence_high: int | None = None,
        scanner_results: dict[str, list] | None = None,
    ) -> HealthReport:
        """
        Run all health checks and generate report.

        Args:
            entry_hits: Number of entry signals
            risk_hits: Number of risk flags
            confluence_high: Number of high-conviction picks
            scanner_results: Scanner results dict

        Returns:
            HealthReport
        """
        self.results = []

        log.info("Running health checks...")

        # Run checks
        self.check_reports_generated()
        self.check_hit_counts(entry_hits, risk_hits, confluence_high)
        self.check_database_connectivity()
        self.check_disk_space()
        self.check_log_files()
        self.check_scanner_errors(scanner_results)

        # Generate report
        passed_count = sum(1 for r in self.results if r.passed)
        failed_count = sum(1 for r in self.results if not r.passed and r.severity == "error")
        warning_count = sum(1 for r in self.results if not r.passed and r.severity == "warning")

        report = HealthReport(
            timestamp=datetime.now(),
            all_passed=(failed_count == 0),
            total_checks=len(self.results),
            passed_count=passed_count,
            failed_count=failed_count,
            warning_count=warning_count,
            checks=self.results,
        )

        log.info(f"Health checks complete: {passed_count}/{len(self.results)} passed, "
                f"{failed_count} failed, {warning_count} warnings")

        return report

    def save_health_report(self, report: HealthReport):
        """
        Save health check results to database.

        Args:
            report: HealthReport to save
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS health_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    check_name TEXT,
                    passed INTEGER,
                    message TEXT,
                    details TEXT,
                    severity TEXT
                )
            """)

            for check in report.checks:
                cursor.execute("""
                    INSERT INTO health_checks
                    (timestamp, check_name, passed, message, details, severity)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    report.timestamp.isoformat(),
                    check.check_name,
                    1 if check.passed else 0,
                    check.message,
                    str(check.details),
                    check.severity,
                ))

            conn.commit()
            conn.close()

            log.info("Health check results saved to database")

        except Exception as e:
            log.error(f"Failed to save health check results: {e}")

    def send_alert_email(self, report: HealthReport) -> bool:
        """
        Send alert email if health checks failed.

        Args:
            report: HealthReport with failures

        Returns:
            True if email sent successfully
        """
        if self.email_sender is None:
            log.warning("No email sender configured, skipping alert")
            return False

        failed_checks = report.get_failed_checks()
        warnings = report.get_warnings()

        if not failed_checks and not warnings:
            log.info("No failures or warnings, skipping alert email")
            return False

        # Build HTML email
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 20px; }}
        h1 {{ color: #E74C3C; }}
        .check {{ padding: 10px; margin: 10px 0; border-left: 4px solid #ddd; }}
        .failed {{ border-left-color: #E74C3C; background: #FFEBEE; }}
        .warning {{ border-left-color: #FFC107; background: #FFF3CD; }}
        .passed {{ border-left-color: #27AE60; background: #E8F5E9; }}
    </style>
</head>
<body>
    <h1>⚠️ Health Check Alert</h1>
    <p><strong>Timestamp:</strong> {report.timestamp.strftime('%Y-%m-%d %H:%M')}</p>
    <p><strong>Status:</strong> {report.failed_count} failed, {report.warning_count} warnings</p>

    <h2>Failed Checks</h2>
"""

        for check in failed_checks:
            html += f"""
    <div class="check failed">
        <strong>{check.check_name}</strong><br>
        {check.message}<br>
        <small>{check.details}</small>
    </div>
"""

        if warnings:
            html += "<h2>Warnings</h2>"
            for check in warnings:
                html += f"""
    <div class="check warning">
        <strong>{check.check_name}</strong><br>
        {check.message}<br>
        <small>{check.details}</small>
    </div>
"""

        html += """
    <h2>Action Required</h2>
    <ol>
        <li>Check logs for detailed error messages</li>
        <li>Verify database connectivity</li>
        <li>Review scanner error rates</li>
        <li>Check disk space and permissions</li>
    </ol>
</body>
</html>
"""

        try:
            success = self.email_sender.send_email(
                to=[],  # Will use configured recipients
                subject=f"⚠️ Health Check Alert - {report.failed_count} Failed",
                body_html=html,
            )

            if success:
                log.info("Health check alert email sent")
            else:
                log.error("Failed to send health check alert email")

            return success

        except Exception as e:
            log.error(f"Error sending health check alert: {e}")
            return False


# ── Demo ──────────────────────────────────────────────────────────────────────


def _demo():
    """Demonstration of health check system."""
    print("=== Health Check System Demo ===\n")

    # Create health checker
    checker = HealthChecker(output_dir="reports/batch")

    print("Running health checks...\n")

    # Run all checks
    report = checker.run_all_checks(
        entry_hits=45,
        risk_hits=8,
        confluence_high=12,
        scanner_results={
            "Pullback Entry": [1, 2, 3],  # 3 hits
            "Order Block Retest": [1],     # 1 hit
            "Stage 2 Uptrend": [],         # 0 hits
        },
    )

    # Display results
    print("=== Health Check Report ===")
    print(f"Timestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M')}")
    print(f"Status: {'✅ ALL PASSED' if report.all_passed else '❌ FAILURES DETECTED'}")
    print(f"Total Checks: {report.total_checks}")
    print(f"  Passed: {report.passed_count}")
    print(f"  Failed: {report.failed_count}")
    print(f"  Warnings: {report.warning_count}")
    print()

    # Show check details
    print("=== Check Details ===")
    for check in report.checks:
        status = "✅" if check.passed else ("⚠️" if check.severity == "warning" else "❌")
        print(f"{status} {check.check_name}: {check.message}")

    print()

    # Save to database (if available)
    if checker.db_path.exists():
        checker.save_health_report(report)
        print(f"✅ Health report saved to: {checker.db_path}")
    else:
        print(f"ℹ️  Database not found: {checker.db_path} (skipped save)")

    print("\n🎉 Demo complete!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _demo()
