#!/usr/bin/env python3
"""
structured_logger.py — JSON-based structured logging for Trading Bramha.

Provides structured logging with:
  • JSON format for easy parsing (jq, grep, Elasticsearch)
  • Context enrichment (batch_id, scanner_name, symbol, etc.)
  • Rotating log files (daily rotation, 30-day retention)
  • Multiple output handlers (file, console, optionally Elasticsearch)
  • Performance metrics logging (execution time, memory usage)
  • Error tracking with stack traces
  • Context managers for automatic scope logging

Log Format:
    {
        "timestamp": "2026-10-12T18:11:53.286Z",
        "level": "INFO",
        "logger": "scanner_batch",
        "message": "Scanner completed",
        "context": {
            "batch_id": "entry_setups",
            "scanner_name": "Pullback Entry",
            "symbol": "RELIANCE",
            "hits": 23,
            "duration_ms": 125.3
        }
    }

Usage:
    # Basic logging
    from structured_logger import get_logger

    log = get_logger("my_module")
    log.info("Operation started")

    # With context
    log.info("Scanner hit", context={
        "scanner": "Pullback Entry",
        "symbol": "RELIANCE",
        "score": 78.5
    })

    # Context manager (automatic start/end logging)
    with log_context("batch_run", batch_id="entry"):
        # Your code here
        pass  # Automatically logs start/end + duration
"""

from __future__ import annotations

import json
import logging
import sys
import time
import traceback
from contextlib import contextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any

# ── Configuration ─────────────────────────────────────────────────────────────

DEFAULT_LOG_DIR = Path("logs")
DEFAULT_LOG_LEVEL = logging.INFO
LOG_RETENTION_DAYS = 30
MAX_LOG_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


# ── JSON Formatter ────────────────────────────────────────────────────────────


class JSONFormatter(logging.Formatter):
    """Format log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record

        Returns:
            JSON string
        """
        # Base log entry
        log_entry = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add context if present
        if hasattr(record, "context") and record.context:
            log_entry["context"] = record.context

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "context",
            ]:
                # Add custom fields to root level
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


# ── Structured Logger ─────────────────────────────────────────────────────────


class StructuredLogger:
    """
    Structured logger wrapper with context support.

    Wraps Python's logging.Logger and adds:
      • JSON formatting
      • Context enrichment
      • Performance tracking
      • Context managers
    """

    def __init__(self, logger: logging.Logger):
        """
        Initialize structured logger.

        Args:
            logger: Underlying Python logger
        """
        self._logger = logger
        self._default_context: dict[str, Any] = {}

    def set_default_context(self, **kwargs):
        """
        Set default context fields for all log messages.

        Args:
            **kwargs: Context key-value pairs

        Example:
            log.set_default_context(batch_id="entry_setups", run_id="20261012")
        """
        self._default_context.update(kwargs)

    def clear_default_context(self):
        """Clear all default context fields."""
        self._default_context.clear()

    def _log(self, level: int, message: str, context: dict[str, Any] | None = None, **kwargs):
        """
        Internal log method with context support.

        Args:
            level: Log level (logging.INFO, etc.)
            message: Log message
            context: Context dictionary
            **kwargs: Additional logger kwargs
        """
        # Merge default context with message context
        merged_context = {**self._default_context}
        if context:
            merged_context.update(context)

        # Create log record with context
        extra = kwargs.get("extra", {})
        extra["context"] = merged_context if merged_context else None
        kwargs["extra"] = extra

        self._logger.log(level, message, **kwargs)

    def debug(self, message: str, context: dict[str, Any] | None = None, **kwargs):
        """Log debug message."""
        self._log(logging.DEBUG, message, context, **kwargs)

    def info(self, message: str, context: dict[str, Any] | None = None, **kwargs):
        """Log info message."""
        self._log(logging.INFO, message, context, **kwargs)

    def warning(self, message: str, context: dict[str, Any] | None = None, **kwargs):
        """Log warning message."""
        self._log(logging.WARNING, message, context, **kwargs)

    def error(self, message: str, context: dict[str, Any] | None = None, **kwargs):
        """Log error message."""
        self._log(logging.ERROR, message, context, **kwargs)

    def critical(self, message: str, context: dict[str, Any] | None = None, **kwargs):
        """Log critical message."""
        self._log(logging.CRITICAL, message, context, **kwargs)

    def exception(self, message: str, context: dict[str, Any] | None = None, **kwargs):
        """Log exception with traceback."""
        kwargs["exc_info"] = True
        self._log(logging.ERROR, message, context, **kwargs)

    @contextmanager
    def context(self, **kwargs):
        """
        Context manager for temporary context fields.

        Args:
            **kwargs: Context key-value pairs

        Example:
            with log.context(batch_id="entry", scanner="Pullback"):
                log.info("Scanner started")  # Includes batch_id + scanner in context
        """
        # Save previous context
        previous = self._default_context.copy()

        # Add new context
        self._default_context.update(kwargs)

        try:
            yield self
        finally:
            # Restore previous context
            self._default_context = previous

    @contextmanager
    def timed(self, operation: str, context: dict[str, Any] | None = None):
        """
        Context manager for timed operations.

        Args:
            operation: Operation name
            context: Additional context

        Example:
            with log.timed("batch_scan", context={"batch": "entry"}):
                run_batch()  # Automatically logs duration
        """
        start_time = time.time()
        merged_context = context or {}

        self.info(f"{operation} started", context=merged_context)

        try:
            yield self
            duration_ms = (time.time() - start_time) * 1000
            merged_context["duration_ms"] = round(duration_ms, 2)
            self.info(f"{operation} completed", context=merged_context)

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            merged_context["duration_ms"] = round(duration_ms, 2)
            merged_context["error"] = str(e)
            self.exception(f"{operation} failed", context=merged_context)
            raise


# ── Logger Setup ──────────────────────────────────────────────────────────────


def setup_structured_logging(
    name: str,
    log_dir: Path | str | None = None,
    log_level: int = DEFAULT_LOG_LEVEL,
    console_output: bool = True,
    json_console: bool = False,
) -> StructuredLogger:
    """
    Set up structured logging for a module.

    Args:
        name: Logger name (usually module name)
        log_dir: Directory for log files (default: logs/)
        log_level: Logging level
        console_output: Whether to also log to console
        json_console: Whether console output should be JSON (vs human-readable)

    Returns:
        StructuredLogger instance

    Example:
        log = setup_structured_logging("scanner_batch")
        log.info("Batch started")
    """
    if log_dir is None:
        log_dir = DEFAULT_LOG_DIR

    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Remove existing handlers
    logger.handlers.clear()

    # JSON file handler (rotating daily)
    json_log_file = log_dir / f"{name}.json"
    json_handler = TimedRotatingFileHandler(
        json_log_file,
        when="midnight",
        interval=1,
        backupCount=LOG_RETENTION_DAYS,
        encoding="utf-8",
    )
    json_handler.setLevel(log_level)
    json_handler.setFormatter(JSONFormatter())
    logger.addHandler(json_handler)

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        if json_console:
            # JSON format for console (e.g., piped to jq)
            console_handler.setFormatter(JSONFormatter())
        else:
            # Human-readable format for console
            console_formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
            console_handler.setFormatter(console_formatter)

        logger.addHandler(console_handler)

    return StructuredLogger(logger)


# ── Convenience Function ──────────────────────────────────────────────────────


_loggers: dict[str, StructuredLogger] = {}


def get_logger(name: str, **kwargs) -> StructuredLogger:
    """
    Get or create a structured logger.

    Args:
        name: Logger name
        **kwargs: Arguments passed to setup_structured_logging

    Returns:
        StructuredLogger instance

    Example:
        log = get_logger("my_module")
        log.info("Operation started")
    """
    if name not in _loggers:
        _loggers[name] = setup_structured_logging(name, **kwargs)

    return _loggers[name]


# ── Context Manager Shortcuts ─────────────────────────────────────────────────


@contextmanager
def log_context(logger_name: str, operation: str, **context):
    """
    Context manager for logging an operation with automatic start/end.

    Args:
        logger_name: Logger name
        operation: Operation name
        **context: Context fields

    Example:
        with log_context("batch", "scan_universe", batch_id="entry"):
            scan_symbols()
    """
    log = get_logger(logger_name)

    with log.timed(operation, context=context):
        yield log


# ── Performance Logging ───────────────────────────────────────────────────────


class PerformanceLogger:
    """
    Log performance metrics for operations.

    Tracks:
      • Execution time
      • Memory usage (optional)
      • Operation counts
      • Error rates
    """

    def __init__(self, logger: StructuredLogger):
        """
        Initialize performance logger.

        Args:
            logger: Structured logger instance
        """
        self.logger = logger
        self.metrics: dict[str, dict[str, Any]] = {}

    def record_operation(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        **context
    ):
        """
        Record a single operation.

        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            success: Whether operation succeeded
            **context: Additional context
        """
        if operation not in self.metrics:
            self.metrics[operation] = {
                "count": 0,
                "success_count": 0,
                "error_count": 0,
                "total_duration_ms": 0.0,
                "min_duration_ms": float("inf"),
                "max_duration_ms": 0.0,
            }

        m = self.metrics[operation]
        m["count"] += 1

        if success:
            m["success_count"] += 1
        else:
            m["error_count"] += 1

        m["total_duration_ms"] += duration_ms
        m["min_duration_ms"] = min(m["min_duration_ms"], duration_ms)
        m["max_duration_ms"] = max(m["max_duration_ms"], duration_ms)

        # Log individual operation
        self.logger.debug(
            f"{operation} recorded",
            context={
                "operation": operation,
                "duration_ms": round(duration_ms, 2),
                "success": success,
                **context,
            },
        )

    def log_summary(self):
        """Log performance summary for all operations."""
        for operation, m in self.metrics.items():
            avg_duration = m["total_duration_ms"] / m["count"] if m["count"] > 0 else 0
            error_rate = m["error_count"] / m["count"] if m["count"] > 0 else 0

            self.logger.info(
                f"Performance summary: {operation}",
                context={
                    "operation": operation,
                    "count": m["count"],
                    "success_count": m["success_count"],
                    "error_count": m["error_count"],
                    "error_rate_pct": round(error_rate * 100, 2),
                    "avg_duration_ms": round(avg_duration, 2),
                    "min_duration_ms": round(m["min_duration_ms"], 2),
                    "max_duration_ms": round(m["max_duration_ms"], 2),
                    "total_duration_ms": round(m["total_duration_ms"], 2),
                },
            )


# ── Demo ──────────────────────────────────────────────────────────────────────


def _demo():
    """Demonstration of structured logging."""
    print("=== Structured Logging Demo ===\n")

    # Create logger
    log = get_logger("demo", console_output=True, json_console=False)

    # Basic logging
    print("1. Basic Logging")
    log.info("Application started")
    log.debug("Debug information")
    log.warning("Warning message")
    print()

    # Logging with context
    print("2. Logging with Context")
    log.info("Scanner hit detected", context={
        "scanner": "Pullback Entry",
        "symbol": "RELIANCE",
        "score": 78.5,
    })
    print()

    # Context manager
    print("3. Context Manager")
    with log.context(batch_id="entry_setups", run_id="20261012"):
        log.info("Batch started")
        log.info("Scanner running", context={"scanner": "Pullback Entry"})
        log.info("Batch completed")
    print()

    # Timed operations
    print("4. Timed Operations")
    with log.timed("data_fetch", context={"symbols": 500}):
        time.sleep(0.5)  # Simulate work
    print()

    # Error logging
    print("5. Error Logging")
    try:
        raise ValueError("Something went wrong")
    except Exception:
        log.exception("Operation failed", context={"operation": "test"})
    print()

    # Performance logging
    print("6. Performance Logging")
    perf_logger = PerformanceLogger(log)

    for i in range(10):
        duration = 50 + (i * 5)  # Simulate varying durations
        success = i < 8  # Last 2 fail
        perf_logger.record_operation(
            "symbol_scan",
            duration_ms=duration,
            success=success,
            symbol=f"SYM{i}"
        )

    perf_logger.log_summary()
    print()

    # Nested contexts
    print("7. Nested Contexts")
    with log.context(batch="entry"):
        log.info("Batch started")

        with log.context(scanner="Pullback Entry"):
            log.info("Scanner started")

            with log.context(symbol="RELIANCE"):
                log.info("Scanning symbol")

    print()

    print("✅ Demo complete!")
    print(f"\nJSON logs saved to: logs/demo.json")
    print("View with: cat logs/demo.json | jq '.'")


if __name__ == "__main__":
    _demo()
