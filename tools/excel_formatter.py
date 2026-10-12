#!/usr/bin/env python3
"""
excel_formatter.py — Professional Excel report formatting for Trading Bramha.

Provides a reusable Excel formatting system with:
  • Colored headers with professional styling
  • Conditional formatting (score-based color scales)
  • Frozen header rows for easy scrolling
  • Auto-adjusted column widths
  • Hyperlinks to TradingView charts
  • Number formatting (percentages, decimals)
  • Data validation dropdowns
  • Multiple sheet support with summary sheets

Usage:
    formatter = ExcelFormatter("output.xlsx")
    formatter.add_sheet(df, "Signals", format_as="signals")
    formatter.add_summary_sheet(summary_data)
    formatter.save()

Or use the quick helper:
    save_formatted_excel(df, "output.xlsx", format_as="signals")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import (
    Alignment,
    Border,
    Font,
    PatternFill,
    Side,
)
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.formatting.rule import ColorScaleRule, CellIsRule

log = logging.getLogger(__name__)

# ── Color Schemes ─────────────────────────────────────────────────────────────

@dataclass
class ColorScheme:
    """Color scheme for Excel formatting."""
    header_bg: str         # Header background color
    header_text: str       # Header text color
    high_good: str         # High score color (good)
    medium: str            # Medium score color
    low_bad: str           # Low score color (bad)
    risk_flag: str         # Risk/warning color
    neutral: str           # Neutral/default color


# Professional blue-green scheme
DEFAULT_SCHEME = ColorScheme(
    header_bg="1F4E78",      # Dark blue
    header_text="FFFFFF",    # White
    high_good="C6EFCE",      # Light green
    medium="FFEB9C",         # Light yellow
    low_bad="FFC7CE",        # Light red
    risk_flag="FF6B6B",      # Red
    neutral="F8F9FA",        # Light gray
)

# Dark theme (alternative)
DARK_SCHEME = ColorScheme(
    header_bg="2C3E50",      # Dark slate
    header_text="ECF0F1",    # Light gray
    high_good="27AE60",      # Green
    medium="F39C12",         # Orange
    low_bad="E74C3C",        # Red
    risk_flag="C0392B",      # Dark red
    neutral="34495E",        # Gray
)


# ── Format Presets ────────────────────────────────────────────────────────────

class FormatPresets:
    """Pre-configured formatting rules for different report types."""

    @staticmethod
    def signals() -> dict[str, Any]:
        """Format preset for scanner signals/entry reports."""
        return {
            "score_columns": ["score", "weighted_score", "max_score"],
            "percentage_columns": ["r:r", "rr", "rr_to_t2"],
            "price_columns": ["entry", "stop", "target", "close", "pivot"],
            "integer_columns": ["raw_hits", "category_diversity"],
            "chart_link_column": "symbol",
            "freeze_panes": "A2",  # Freeze header row
            "conditional_format": {
                "score": {"type": "3color", "min": 0, "mid": 50, "max": 100},
                "weighted_score": {"type": "3color", "min": 0, "mid": 3, "max": 6},
            },
            "column_widths": {
                "symbol": 12,
                "pattern_type": 25,
                "scanners": 40,
                "reasons": 60,
                "tags": 30,
            },
        }

    @staticmethod
    def risk() -> dict[str, Any]:
        """Format preset for risk reports."""
        return {
            "score_columns": ["score"],
            "price_columns": ["close", "stop", "target"],
            "chart_link_column": "symbol",
            "freeze_panes": "A2",
            "conditional_format": {
                "score": {"type": "3color", "min": 0, "mid": 50, "max": 100},
            },
            "highlight_risk": True,
        }

    @staticmethod
    def confluence() -> dict[str, Any]:
        """Format preset for confluence reports."""
        return {
            "score_columns": ["weighted_score", "max_score"],
            "integer_columns": ["raw_hits", "category_diversity"],
            "chart_link_column": "symbol",
            "freeze_panes": "A2",
            "conditional_format": {
                "weighted_score": {"type": "3color", "min": 0, "mid": 3, "max": 6},
                "raw_hits": {"type": "3color", "min": 1, "mid": 3, "max": 5},
            },
            "column_widths": {
                "symbol": 12,
                "scanners": 50,
                "categories": 30,
                "matched_patterns": 30,
            },
        }

    @staticmethod
    def portfolio() -> dict[str, Any]:
        """Format preset for portfolio holdings."""
        return {
            "score_columns": ["return_pct", "overall_rating"],
            "percentage_columns": ["weight", "return_pct", "day_change_pct"],
            "price_columns": ["entry_price", "current_price", "stop", "target"],
            "currency_columns": ["value", "pnl"],
            "freeze_panes": "A2",
            "conditional_format": {
                "return_pct": {"type": "3color", "min": -10, "mid": 0, "max": 10},
            },
        }


# ── Excel Formatter ───────────────────────────────────────────────────────────

class ExcelFormatter:
    """Professional Excel report formatter with multiple sheets and styling."""

    def __init__(
        self,
        output_path: str | Path,
        color_scheme: ColorScheme = None,
    ):
        """
        Initialize Excel formatter.

        Args:
            output_path: Path to save the Excel file
            color_scheme: Color scheme to use (default: DEFAULT_SCHEME)
        """
        self.output_path = Path(output_path)
        self.color_scheme = color_scheme or DEFAULT_SCHEME
        self.workbook = Workbook()
        # Remove default sheet
        if "Sheet" in self.workbook.sheetnames:
            del self.workbook["Sheet"]

        self.sheets_added = 0

    def add_sheet(
        self,
        df: pd.DataFrame,
        sheet_name: str,
        format_as: Literal["signals", "risk", "confluence", "portfolio", "custom"] = "custom",
        custom_format: dict[str, Any] | None = None,
    ) -> Worksheet:
        """
        Add a formatted sheet to the workbook.

        Args:
            df: DataFrame to write
            sheet_name: Name of the sheet
            format_as: Preset format type
            custom_format: Custom format options (overrides preset)

        Returns:
            The worksheet object
        """
        if df.empty:
            log.warning(f"Sheet '{sheet_name}' has no data, skipping")
            return None

        # Get format preset
        if format_as == "signals":
            fmt = FormatPresets.signals()
        elif format_as == "risk":
            fmt = FormatPresets.risk()
        elif format_as == "confluence":
            fmt = FormatPresets.confluence()
        elif format_as == "portfolio":
            fmt = FormatPresets.portfolio()
        else:
            fmt = {}

        # Override with custom format
        if custom_format:
            fmt.update(custom_format)

        # Create sheet
        ws = self.workbook.create_sheet(title=sheet_name)

        # Write data
        for r_idx, row in enumerate(df.itertuples(index=False), start=1):
            for c_idx, value in enumerate(row, start=1):
                cell = ws.cell(row=r_idx + 1, column=c_idx, value=value)

        # Write headers
        for c_idx, col_name in enumerate(df.columns, start=1):
            cell = ws.cell(row=1, column=c_idx, value=col_name)
            self._format_header(cell)

        # Apply column formatting
        self._apply_column_formats(ws, df, fmt)

        # Apply conditional formatting
        self._apply_conditional_formatting(ws, df, fmt)

        # Add chart links
        if "chart_link_column" in fmt:
            self._add_chart_links(ws, df, fmt["chart_link_column"])

        # Freeze panes
        if "freeze_panes" in fmt:
            ws.freeze_panes = fmt["freeze_panes"]

        # Auto-adjust column widths
        self._auto_adjust_columns(ws, df, fmt.get("column_widths", {}))

        self.sheets_added += 1
        return ws

    def add_summary_sheet(
        self,
        summary_data: dict[str, Any],
        sheet_name: str = "Summary",
    ) -> Worksheet:
        """
        Add a summary sheet with key metrics.

        Args:
            summary_data: Dict of metric_name: value
            sheet_name: Name of the summary sheet

        Returns:
            The worksheet object
        """
        ws = self.workbook.create_sheet(title=sheet_name, index=0)  # First sheet

        # Title
        ws["A1"] = "Report Summary"
        ws["A1"].font = Font(size=16, bold=True, color=self.color_scheme.header_text)
        ws["A1"].fill = PatternFill(
            start_color=self.color_scheme.header_bg,
            end_color=self.color_scheme.header_bg,
            fill_type="solid"
        )
        ws.merge_cells("A1:B1")

        # Metadata
        row = 3
        ws[f"A{row}"] = "Generated"
        ws[f"B{row}"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        ws[f"A{row}"].font = Font(bold=True)

        # Metrics
        row += 2
        ws[f"A{row}"] = "Metric"
        ws[f"B{row}"] = "Value"
        self._format_header(ws[f"A{row}"])
        self._format_header(ws[f"B{row}"])

        row += 1
        for metric, value in summary_data.items():
            ws[f"A{row}"] = metric.replace("_", " ").title()
            ws[f"B{row}"] = value

            # Format numbers
            if isinstance(value, float):
                ws[f"B{row}"].number_format = "0.00"

            row += 1

        # Auto-adjust columns
        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 20

        return ws

    def save(self) -> Path:
        """Save the workbook to disk."""
        if self.sheets_added == 0:
            log.warning("No sheets added, creating empty workbook")

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.workbook.save(self.output_path)
        log.info(f"Excel report saved: {self.output_path} ({self.sheets_added} sheets)")
        return self.output_path

    def _format_header(self, cell):
        """Apply header formatting to a cell."""
        cell.font = Font(
            bold=True,
            color=self.color_scheme.header_text,
            size=11
        )
        cell.fill = PatternFill(
            start_color=self.color_scheme.header_bg,
            end_color=self.color_scheme.header_bg,
            fill_type="solid"
        )
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = Border(
            bottom=Side(style="thick", color="000000")
        )

    def _apply_column_formats(
        self,
        ws: Worksheet,
        df: pd.DataFrame,
        fmt: dict[str, Any],
    ):
        """Apply number formatting to columns."""
        for col_idx, col_name in enumerate(df.columns, start=1):
            col_letter = get_column_letter(col_idx)

            # Score columns (0-100 scale, 1 decimal)
            if col_name in fmt.get("score_columns", []):
                for row in range(2, len(df) + 2):
                    ws[f"{col_letter}{row}"].number_format = "0.0"

            # Percentage columns
            elif col_name in fmt.get("percentage_columns", []):
                for row in range(2, len(df) + 2):
                    ws[f"{col_letter}{row}"].number_format = "0.00%"

            # Price columns (₹ with 2 decimals)
            elif col_name in fmt.get("price_columns", []):
                for row in range(2, len(df) + 2):
                    ws[f"{col_letter}{row}"].number_format = '"₹"#,##0.00'

            # Currency columns (₹ with 0 decimals)
            elif col_name in fmt.get("currency_columns", []):
                for row in range(2, len(df) + 2):
                    ws[f"{col_letter}{row}"].number_format = '"₹"#,##0'

            # Integer columns
            elif col_name in fmt.get("integer_columns", []):
                for row in range(2, len(df) + 2):
                    ws[f"{col_letter}{row}"].number_format = "0"

    def _apply_conditional_formatting(
        self,
        ws: Worksheet,
        df: pd.DataFrame,
        fmt: dict[str, Any],
    ):
        """Apply conditional formatting rules."""
        conditional = fmt.get("conditional_format", {})

        for col_name, rules in conditional.items():
            if col_name not in df.columns:
                continue

            col_idx = df.columns.get_loc(col_name) + 1
            col_letter = get_column_letter(col_idx)

            # Range: from row 2 to last row
            range_str = f"{col_letter}2:{col_letter}{len(df) + 1}"

            rule_type = rules.get("type", "3color")

            if rule_type == "3color":
                # Three-color scale (red -> yellow -> green)
                min_val = rules.get("min", 0)
                mid_val = rules.get("mid", 50)
                max_val = rules.get("max", 100)

                ws.conditional_formatting.add(
                    range_str,
                    ColorScaleRule(
                        start_type="num",
                        start_value=min_val,
                        start_color=self.color_scheme.low_bad,
                        mid_type="num",
                        mid_value=mid_val,
                        mid_color=self.color_scheme.medium,
                        end_type="num",
                        end_value=max_val,
                        end_color=self.color_scheme.high_good,
                    )
                )

            elif rule_type == "2color":
                # Two-color scale (white -> green)
                min_val = rules.get("min", 0)
                max_val = rules.get("max", 100)

                ws.conditional_formatting.add(
                    range_str,
                    ColorScaleRule(
                        start_type="num",
                        start_value=min_val,
                        start_color="FFFFFF",
                        end_type="num",
                        end_value=max_val,
                        end_color=self.color_scheme.high_good,
                    )
                )

            elif rule_type == "threshold":
                # Highlight cells above/below threshold
                threshold = rules.get("threshold", 50)
                operator = rules.get("operator", ">=")
                color = rules.get("color", self.color_scheme.high_good)

                ws.conditional_formatting.add(
                    range_str,
                    CellIsRule(
                        operator=operator,
                        formula=[threshold],
                        fill=PatternFill(
                            start_color=color,
                            end_color=color,
                            fill_type="solid"
                        )
                    )
                )

    def _add_chart_links(
        self,
        ws: Worksheet,
        df: pd.DataFrame,
        symbol_column: str,
    ):
        """Add TradingView chart hyperlinks to symbol column."""
        if symbol_column not in df.columns:
            return

        col_idx = df.columns.get_loc(symbol_column) + 1
        col_letter = get_column_letter(col_idx)

        for row_idx in range(2, len(df) + 2):
            cell = ws[f"{col_letter}{row_idx}"]
            symbol = cell.value

            if symbol:
                # TradingView NSE chart URL
                url = f"https://www.tradingview.com/chart/?symbol=NSE%3A{symbol}"
                cell.hyperlink = url
                cell.font = Font(color="0563C1", underline="single")  # Blue underline

    def _auto_adjust_columns(
        self,
        ws: Worksheet,
        df: pd.DataFrame,
        custom_widths: dict[str, int],
    ):
        """Auto-adjust column widths based on content."""
        for col_idx, col_name in enumerate(df.columns, start=1):
            col_letter = get_column_letter(col_idx)

            # Use custom width if specified
            if col_name in custom_widths:
                ws.column_dimensions[col_letter].width = custom_widths[col_name]
                continue

            # Calculate max width from header and data
            max_length = len(str(col_name))

            for row_idx in range(2, min(len(df) + 2, 102)):  # Check first 100 rows
                cell_value = ws[f"{col_letter}{row_idx}"].value
                if cell_value:
                    max_length = max(max_length, len(str(cell_value)))

            # Set width with limits
            adjusted_width = min(max(max_length + 2, 10), 60)
            ws.column_dimensions[col_letter].width = adjusted_width


# ── Quick Helper Functions ────────────────────────────────────────────────────

def save_formatted_excel(
    df: pd.DataFrame,
    output_path: str | Path,
    sheet_name: str = "Data",
    format_as: Literal["signals", "risk", "confluence", "portfolio", "custom"] = "signals",
    summary_data: dict[str, Any] | None = None,
) -> Path:
    """
    Quick helper to save a single DataFrame as a formatted Excel file.

    Args:
        df: DataFrame to save
        output_path: Path to save the Excel file
        sheet_name: Name of the sheet
        format_as: Format preset to use
        summary_data: Optional summary metrics to add as first sheet

    Returns:
        Path to the saved file

    Example:
        >>> df = pd.DataFrame({
        ...     "symbol": ["RELIANCE", "TCS"],
        ...     "score": [78.5, 82.0],
        ...     "entry": [2450.00, 3800.00],
        ... })
        >>> save_formatted_excel(df, "signals.xlsx", format_as="signals")
    """
    formatter = ExcelFormatter(output_path)

    if summary_data:
        formatter.add_summary_sheet(summary_data)

    formatter.add_sheet(df, sheet_name, format_as=format_as)
    return formatter.save()


def save_multi_sheet_excel(
    sheets: dict[str, tuple[pd.DataFrame, str]],
    output_path: str | Path,
    summary_data: dict[str, Any] | None = None,
) -> Path:
    """
    Save multiple DataFrames as a multi-sheet Excel file.

    Args:
        sheets: Dict of sheet_name → (DataFrame, format_preset)
        output_path: Path to save the Excel file
        summary_data: Optional summary metrics

    Returns:
        Path to the saved file

    Example:
        >>> sheets = {
        ...     "Entry Signals": (entry_df, "signals"),
        ...     "Risk Flags": (risk_df, "risk"),
        ...     "Confluence": (confluence_df, "confluence"),
        ... }
        >>> save_multi_sheet_excel(sheets, "batch_report.xlsx")
    """
    formatter = ExcelFormatter(output_path)

    if summary_data:
        formatter.add_summary_sheet(summary_data)

    for sheet_name, (df, format_as) in sheets.items():
        formatter.add_sheet(df, sheet_name, format_as=format_as)

    return formatter.save()


# ── Demo ──────────────────────────────────────────────────────────────────────

def _demo():
    """Demonstration of Excel formatting."""
    import numpy as np

    # Create sample data
    np.random.seed(42)

    signals_df = pd.DataFrame({
        "symbol": ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"],
        "pattern_type": [
            "Pullback Entry",
            "HM Buy",
            "Stage 2 Uptrend",
            "Breakout Retest",
            "Order Block Retest",
        ],
        "score": [78.5, 85.0, 72.0, 88.5, 65.0],
        "entry": [2450.00, 3800.00, 1520.00, 1650.00, 485.00],
        "stop": [2400.00, 3750.00, 1480.00, 1600.00, 470.00],
        "target": [2550.00, 3900.00, 1580.00, 1750.00, 510.00],
        "tags": [
            "EMA21, Volume",
            "Swing low",
            "ADX rising",
            "Volume spike",
            "Demand zone",
        ],
    })

    confluence_df = pd.DataFrame({
        "symbol": ["RELIANCE", "TCS", "INFY"],
        "raw_hits": [2, 3, 2],
        "weighted_score": [3.5, 5.5, 0.2],
        "scanners": [
            "Pullback Entry, Stage 2 Uptrend",
            "Pullback Entry, HM Buy, Stage 2 Uptrend",
            "Darvas Box, RSI Divergence Bear",
        ],
        "categories": ["Entry, Trend", "Entry, Trend", "Pattern, Risk"],
        "max_score": [82.0, 88.0, 70.0],
        "has_entry": [True, True, False],
        "has_risk": [False, False, True],
    })

    summary_data = {
        "total_symbols": 500,
        "signals_found": 45,
        "high_conviction_count": 12,
        "avg_score": 75.3,
        "max_score": 92.5,
    }

    # Test 1: Single sheet report
    print("Creating single-sheet report...")
    save_formatted_excel(
        signals_df,
        "demo_signals.xlsx",
        sheet_name="Entry Signals",
        format_as="signals",
        summary_data=summary_data,
    )
    print("✅ Created: demo_signals.xlsx")

    # Test 2: Multi-sheet report
    print("\nCreating multi-sheet report...")
    sheets = {
        "Entry Signals": (signals_df, "signals"),
        "Confluence": (confluence_df, "confluence"),
    }
    save_multi_sheet_excel(
        sheets,
        "demo_batch_report.xlsx",
        summary_data=summary_data,
    )
    print("✅ Created: demo_batch_report.xlsx")

    # Test 3: Advanced formatting
    print("\nCreating advanced formatted report...")
    formatter = ExcelFormatter("demo_advanced.xlsx")
    formatter.add_summary_sheet(summary_data, "Summary")
    formatter.add_sheet(signals_df, "Signals", format_as="signals")
    formatter.add_sheet(confluence_df, "Confluence", format_as="confluence")
    formatter.save()
    print("✅ Created: demo_advanced.xlsx")

    print("\n🎉 All demo files created successfully!")
    print("Open them in Excel to see the formatting.")


if __name__ == "__main__":
    _demo()
