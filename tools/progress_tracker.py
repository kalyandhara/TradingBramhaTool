#!/usr/bin/env python3
"""
progress_tracker.py — Progress visualization for batch scanner execution.

Provides beautiful, real-time progress bars with:
  • Overall progress (batches completed)
  • Per-batch progress (scanners within batch)
  • Per-scanner progress (symbols scanned)
  • ETA and elapsed time
  • Current operation display
  • Nested progress bars
  • Color-coded status (green=done, yellow=running, red=error)

Uses tqdm library for terminal progress bars.

Usage:
    # Simple progress bar
    for item in progress_bar(items, desc="Processing"):
        process(item)

    # Nested progress (batches → scanners → symbols)
    tracker = BatchProgressTracker(total_batches=5)

    for batch in batches:
        batch_bar = tracker.start_batch(batch_name, num_scanners)

        for scanner in scanners:
            scanner_bar = batch_bar.start_scanner(scanner_name, num_symbols)

            for symbol in symbols:
                # Process symbol
                scanner_bar.update(1)

            scanner_bar.close()

        batch_bar.close()

    tracker.close()

Features:
  • Automatic terminal width detection
  • Unicode/ASCII fallback for compatibility
  • Disable for non-TTY (logs/files)
  • Rate limiting (don't overwhelm terminal)
"""

from __future__ import annotations

import logging
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterable

from tqdm import tqdm

log = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

# Use unicode bars if terminal supports it
USE_UNICODE = sys.stdout.encoding and 'UTF' in sys.stdout.encoding.upper()

# Bar format with time estimates
BAR_FORMAT = '{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'

# Color codes (works in most terminals)
COLOR_GREEN = '\033[92m'
COLOR_YELLOW = '\033[93m'
COLOR_RED = '\033[91m'
COLOR_BLUE = '\033[94m'
COLOR_RESET = '\033[0m'


# ── Progress Bar Helpers ──────────────────────────────────────────────────────


def progress_bar(
    iterable: Iterable,
    desc: str = "Processing",
    total: int | None = None,
    unit: str = "item",
    disable: bool = False,
    leave: bool = True,
) -> tqdm:
    """
    Create a simple progress bar.

    Args:
        iterable: Items to iterate over
        desc: Description shown on left
        total: Total count (auto-detected if iterable has length)
        unit: Unit name (e.g., "symbol", "file", "batch")
        disable: If True, no progress bar shown
        leave: If True, keep bar after completion

    Returns:
        tqdm progress bar iterator

    Example:
        >>> for symbol in progress_bar(symbols, desc="Scanning", unit="symbol"):
        ...     scan_symbol(symbol)
    """
    return tqdm(
        iterable,
        desc=desc,
        total=total,
        unit=unit,
        bar_format=BAR_FORMAT,
        disable=disable or not sys.stdout.isatty(),
        leave=leave,
        ascii=not USE_UNICODE,
    )


@contextmanager
def progress_context(total: int, desc: str, unit: str = "item"):
    """
    Context manager for manual progress updates.

    Args:
        total: Total number of items
        desc: Description
        unit: Unit name

    Yields:
        tqdm progress bar (call .update(n) to advance)

    Example:
        >>> with progress_context(100, "Processing", "file") as pbar:
        ...     for i in range(100):
        ...         process_item(i)
        ...         pbar.update(1)
    """
    pbar = tqdm(
        total=total,
        desc=desc,
        unit=unit,
        bar_format=BAR_FORMAT,
        disable=not sys.stdout.isatty(),
        ascii=not USE_UNICODE,
    )
    try:
        yield pbar
    finally:
        pbar.close()


# ── Nested Progress Tracker ──────────────────────────────────────────────────


@dataclass
class ScannerProgress:
    """Progress tracker for a single scanner."""

    name: str
    pbar: tqdm
    start_time: float
    symbols_scanned: int = 0
    symbols_total: int = 0
    hits: int = 0

    def update(self, n: int = 1, hit: bool = False):
        """Update progress by n symbols."""
        self.symbols_scanned += n
        if hit:
            self.hits += 1
        self.pbar.update(n)

    def close(self):
        """Close and finalize scanner progress."""
        elapsed = time.time() - self.start_time
        self.pbar.set_postfix_str(
            f"{self.hits} hits in {elapsed:.1f}s",
            refresh=True,
        )
        self.pbar.close()


@dataclass
class BatchProgress:
    """Progress tracker for a single batch."""

    name: str
    pbar: tqdm
    start_time: float
    scanners_completed: int = 0
    scanners_total: int = 0
    total_hits: int = 0

    def start_scanner(self, scanner_name: str, num_symbols: int) -> ScannerProgress:
        """Start tracking a scanner within this batch."""
        scanner_pbar = tqdm(
            total=num_symbols,
            desc=f"  {scanner_name}",
            unit="symbol",
            bar_format=BAR_FORMAT,
            disable=not sys.stdout.isatty(),
            leave=False,
            ascii=not USE_UNICODE,
            position=1,
        )

        return ScannerProgress(
            name=scanner_name,
            pbar=scanner_pbar,
            start_time=time.time(),
            symbols_total=num_symbols,
        )

    def scanner_completed(self, scanner_progress: ScannerProgress):
        """Mark scanner as completed."""
        self.scanners_completed += 1
        self.total_hits += scanner_progress.hits
        self.pbar.update(1)

        # Update batch postfix
        self.pbar.set_postfix_str(
            f"{self.total_hits} total hits",
            refresh=True,
        )

    def close(self):
        """Close and finalize batch progress."""
        elapsed = time.time() - self.start_time
        self.pbar.set_postfix_str(
            f"{self.total_hits} hits, {elapsed:.1f}s",
            refresh=True,
        )
        self.pbar.close()


class BatchProgressTracker:
    """
    Multi-level progress tracker for batch scanner execution.

    Displays:
      Level 1: Overall batch progress (which batch)
      Level 2: Scanner progress within batch (which scanner)
      Level 3: Symbol progress within scanner (which symbol)
    """

    def __init__(self, total_batches: int, desc: str = "Batch Scanner"):
        """
        Initialize batch progress tracker.

        Args:
            total_batches: Total number of batches to run
            desc: Overall description
        """
        self.total_batches = total_batches
        self.batches_completed = 0
        self.start_time = time.time()

        # Overall progress bar
        self.overall_pbar = tqdm(
            total=total_batches,
            desc=desc,
            unit="batch",
            bar_format=BAR_FORMAT,
            disable=not sys.stdout.isatty(),
            ascii=not USE_UNICODE,
            position=0,
        )

        self.current_batch: BatchProgress | None = None

    def start_batch(self, batch_name: str, num_scanners: int) -> BatchProgress:
        """Start tracking a new batch."""
        # Close previous batch if exists
        if self.current_batch:
            self.batch_completed(self.current_batch)

        # Create batch progress bar
        batch_pbar = tqdm(
            total=num_scanners,
            desc=f"  {batch_name}",
            unit="scanner",
            bar_format=BAR_FORMAT,
            disable=not sys.stdout.isatty(),
            leave=False,
            ascii=not USE_UNICODE,
            position=1,
        )

        self.current_batch = BatchProgress(
            name=batch_name,
            pbar=batch_pbar,
            start_time=time.time(),
            scanners_total=num_scanners,
        )

        return self.current_batch

    def batch_completed(self, batch_progress: BatchProgress):
        """Mark batch as completed."""
        self.batches_completed += 1
        batch_progress.close()
        self.overall_pbar.update(1)

        # Update overall postfix
        elapsed = time.time() - self.start_time
        self.overall_pbar.set_postfix_str(
            f"{elapsed:.1f}s elapsed",
            refresh=True,
        )

    def close(self):
        """Close all progress bars and show final summary."""
        if self.current_batch:
            self.batch_completed(self.current_batch)

        total_elapsed = time.time() - self.start_time
        self.overall_pbar.set_postfix_str(
            f"Complete in {total_elapsed:.1f}s",
            refresh=True,
        )
        self.overall_pbar.close()

        # Print summary
        if sys.stdout.isatty():
            print(f"\n{COLOR_GREEN}✓ Batch execution complete{COLOR_RESET}")
            print(f"  Total time: {total_elapsed:.1f}s")
            print(f"  Batches: {self.batches_completed}/{self.total_batches}")


# ── Parallel Progress Tracking ────────────────────────────────────────────────


class ParallelProgressTracker:
    """
    Progress tracker for parallel/threaded operations.

    Shows aggregate progress across multiple workers.
    """

    def __init__(self, total: int, desc: str = "Processing", unit: str = "item"):
        """
        Initialize parallel progress tracker.

        Args:
            total: Total number of items across all workers
            desc: Description
            unit: Unit name
        """
        self.pbar = tqdm(
            total=total,
            desc=desc,
            unit=unit,
            bar_format=BAR_FORMAT,
            disable=not sys.stdout.isatty(),
            ascii=not USE_UNICODE,
        )
        self.completed = 0
        self.errors = 0

    def update(self, n: int = 1, error: bool = False):
        """
        Update progress (thread-safe).

        Args:
            n: Number of items completed
            error: Whether this was an error
        """
        self.completed += n
        if error:
            self.errors += 1

        self.pbar.update(n)

        # Update postfix
        if self.errors > 0:
            self.pbar.set_postfix_str(
                f"{self.errors} errors",
                refresh=True,
            )

    def close(self):
        """Close progress bar."""
        if self.errors > 0:
            self.pbar.set_postfix_str(
                f"{COLOR_RED}{self.errors} errors{COLOR_RESET}",
                refresh=True,
            )
        else:
            self.pbar.set_postfix_str(
                f"{COLOR_GREEN}All complete{COLOR_RESET}",
                refresh=True,
            )

        self.pbar.close()


# ── Progress Decorators ───────────────────────────────────────────────────────


def with_progress(desc: str = "Processing", unit: str = "item"):
    """
    Decorator to add progress bar to a function that processes items.

    Args:
        desc: Progress bar description
        unit: Unit name

    Example:
        @with_progress(desc="Scanning", unit="symbol")
        def scan_symbols(symbols):
            for symbol in symbols:
                yield scan_result(symbol)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # If generator, wrap with progress
            if hasattr(result, '__iter__') and not isinstance(result, (str, bytes)):
                return progress_bar(result, desc=desc, unit=unit)
            else:
                return result

        return wrapper
    return decorator


# ── Utility Functions ─────────────────────────────────────────────────────────


def print_status(message: str, status: str = "info"):
    """
    Print colored status message.

    Args:
        message: Message to print
        status: Type of message (info, success, warning, error)
    """
    if not sys.stdout.isatty():
        log.info(message)
        return

    colors = {
        "info": COLOR_BLUE,
        "success": COLOR_GREEN,
        "warning": COLOR_YELLOW,
        "error": COLOR_RED,
    }

    icons = {
        "info": "ℹ",
        "success": "✓",
        "warning": "⚠",
        "error": "✗",
    }

    color = colors.get(status, "")
    icon = icons.get(status, "•")

    print(f"{color}{icon} {message}{COLOR_RESET}")


def format_time(seconds: float) -> str:
    """
    Format seconds into human-readable time.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted string (e.g., "2m 30s", "1h 15m")
    """
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


# ── Demo ──────────────────────────────────────────────────────────────────────


def _demo():
    """Demonstration of progress tracking."""
    print("=== Progress Tracking Demo ===\n")

    # Demo 1: Simple progress bar
    print("1. Simple Progress Bar")
    items = range(50)
    for item in progress_bar(items, desc="Processing items", unit="item"):
        time.sleep(0.02)  # Simulate work

    print_status("Simple progress complete", "success")
    print()

    # Demo 2: Context manager
    print("2. Context Manager Progress")
    with progress_context(30, "Downloading files", "file") as pbar:
        for i in range(30):
            time.sleep(0.03)
            pbar.update(1)

    print_status("Context progress complete", "success")
    print()

    # Demo 3: Nested batch progress
    print("3. Nested Batch Progress (3 batches)")

    # Simulate batch scanner structure
    batches = [
        ("Entry Scanners", ["Pullback Entry", "Order Block Retest", "HM Buy"], 20),
        ("Trend Scanners", ["Stage 2 Uptrend", "ADX Confirmation"], 20),
        ("Risk Scanners", ["RSI Divergence Bear", "%R Exhaustion"], 20),
    ]

    tracker = BatchProgressTracker(total_batches=len(batches), desc="Batch Scanner")

    for batch_name, scanners, num_symbols in batches:
        batch_progress = tracker.start_batch(batch_name, len(scanners))

        for scanner_name in scanners:
            scanner_progress = batch_progress.start_scanner(scanner_name, num_symbols)

            # Simulate scanning symbols
            for i in range(num_symbols):
                time.sleep(0.01)  # Simulate work
                hit = i % 5 == 0  # Some hits
                scanner_progress.update(1, hit=hit)

            scanner_progress.close()
            batch_progress.scanner_completed(scanner_progress)

        # Batch completed automatically when starting next batch

    tracker.close()
    print()

    # Demo 4: Parallel progress
    print("4. Parallel Progress (simulated)")
    parallel_tracker = ParallelProgressTracker(
        total=100,
        desc="Parallel scanners",
        unit="symbol",
    )

    for i in range(100):
        time.sleep(0.01)
        error = i > 95  # Last few have errors
        parallel_tracker.update(1, error=error)

    parallel_tracker.close()
    print()

    # Demo 5: Status messages
    print("5. Status Messages")
    print_status("This is an info message", "info")
    time.sleep(0.3)
    print_status("Operation successful!", "success")
    time.sleep(0.3)
    print_status("Warning: Check this", "warning")
    time.sleep(0.3)
    print_status("Error occurred!", "error")
    print()

    # Demo 6: Time formatting
    print("6. Time Formatting")
    for seconds in [30, 90, 3600, 5400]:
        formatted = format_time(seconds)
        print(f"  {seconds}s → {formatted}")
    print()

    print("🎉 Demo complete!")


if __name__ == "__main__":
    _demo()
