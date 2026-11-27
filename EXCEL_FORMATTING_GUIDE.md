# Excel Report Formatting - Implementation Guide

**Status:** ✅ COMPLETED  
**Date:** 2026-10-12  
**Feature:** Quick Win #1 from Enhancement Backlog (Story 3.1.1)

---

## What Was Built

A professional Excel formatting system that transforms raw DataFrames into presentation-ready reports with:

- **Colored Headers**: Professional dark blue headers with white text
- **Conditional Formatting**: Score-based color scales (red → yellow → green)
- **Frozen Panes**: Headers stay visible while scrolling
- **Auto-Column Widths**: Columns sized perfectly for content
- **TradingView Links**: Click symbol to open chart
- **Number Formatting**: Proper display for scores, prices, percentages
- **Multi-Sheet Support**: Summary + multiple data sheets
- **Format Presets**: Pre-configured layouts for different report types

---

## Key Features

### 1. Format Presets

Four ready-to-use formats:

```python
# Signals/Entry Reports
format_as="signals"
- Score columns (0-100 scale)
- Price columns (₹ format)
- TradingView chart links
- Conditional formatting on scores

# Risk Reports
format_as="risk"
- Highlight risk flags
- Price and score formatting
- Chart links

# Confluence Reports
format_as="confluence"
- Weighted score formatting
- Category diversity metrics
- Pattern match highlighting

# Portfolio Reports
format_as="portfolio"
- Return percentages
- P&L in currency format
- Position weights
```

### 2. Visual Features

**Before (Plain CSV/Excel):**
```
| symbol   | score | entry  |
|----------|-------|--------|
| RELIANCE | 78.5  | 2450.0 |
```

**After (Formatted):**
```
╔═══════════╦═══════╦═══════════╗
║ Symbol    ║ Score ║ Entry     ║  ← Blue header, white text
╠═══════════╬═══════╬═══════════╣
║ RELIANCE  ║ 78.5  ║ ₹2,450.00 ║  ← Green (good score)
║           ║  ↑    ║           ║     Clickable link
║           ║ Click ║           ║     Formatted currency
╚═══════════╩═══════╩═══════════╝
```

### 3. Conditional Formatting

Automatic color scales based on score ranges:

- **0-50**: Red (low/bad)
- **50-75**: Yellow (medium)
- **75-100**: Green (high/good)

Custom ranges supported for weighted scores, confluence, etc.

---

## How to Use

### Quick Start - Single Sheet Report

```python
from excel_formatter import save_formatted_excel

# Your DataFrame
df = pd.DataFrame({
    "symbol": ["RELIANCE", "TCS", "INFY"],
    "score": [78.5, 85.0, 72.0],
    "entry": [2450.00, 3800.00, 1520.00],
    "stop": [2400.00, 3750.00, 1480.00],
})

# Save with formatting
save_formatted_excel(
    df,
    "entry_signals.xlsx",
    sheet_name="Entry Signals",
    format_as="signals",
)
```

Result: Professional Excel file with:
- Blue headers
- Score colors (green for 85, yellow for 72-78)
- Prices formatted as ₹2,450.00
- Clickable TradingView links on symbols

### Multi-Sheet Report with Summary

```python
from excel_formatter import save_multi_sheet_excel

# Define sheets
sheets = {
    "Entry Signals": (entry_df, "signals"),
    "Risk Flags": (risk_df, "risk"),
    "Confluence": (confluence_df, "confluence"),
}

# Add summary metrics
summary = {
    "total_symbols": 500,
    "signals_found": 45,
    "high_conviction_count": 12,
    "avg_score": 75.3,
}

# Save
save_multi_sheet_excel(
    sheets,
    "batch_report.xlsx",
    summary_data=summary,
)
```

Result: Multi-sheet Excel with:
- Summary sheet (first tab)
- Entry Signals tab (formatted for signals)
- Risk Flags tab (formatted for risk)
- Confluence tab (formatted for confluence)

### Advanced - Full Control

```python
from excel_formatter import ExcelFormatter

formatter = ExcelFormatter("custom_report.xlsx")

# Add summary sheet (appears first)
formatter.add_summary_sheet({
    "generated": datetime.now(),
    "universe_size": 500,
    "total_hits": 123,
})

# Add data sheets with different formats
formatter.add_sheet(signals_df, "Signals", format_as="signals")
formatter.add_sheet(risk_df, "Risk", format_as="risk")

# Custom formatting
formatter.add_sheet(
    custom_df,
    "Custom",
    format_as="custom",
    custom_format={
        "score_columns": ["my_score"],
        "freeze_panes": "A2",
        "conditional_format": {
            "my_score": {
                "type": "3color",
                "min": 0,
                "mid": 50,
                "max": 100,
            }
        },
    }
)

formatter.save()
```

---

## Integration Examples

### With Confluence Scoring

```python
from confluence_scoring import aggregate_weighted_confluence
from excel_formatter import save_formatted_excel

# Calculate confluence
confluence_df = aggregate_weighted_confluence(all_results, sc.SCANNERS)

# Save with formatting
save_formatted_excel(
    confluence_df,
    "confluence_report.xlsx",
    sheet_name="High Conviction Picks",
    format_as="confluence",
    summary_data={
        "total_symbols": len(confluence_df),
        "high_conviction": (confluence_df["weighted_score"] >= 3.0).sum(),
        "avg_weighted_score": confluence_df["weighted_score"].mean(),
    }
)
```

### With Batch Scanner Results

```python
from excel_formatter import save_multi_sheet_excel

# Your batch results
entry_hits = []  # From entry batch
risk_hits = []   # From risk batch
confluence = []  # Aggregated

# Create multi-sheet report
sheets = {
    "Entry Setups": (pd.DataFrame(entry_hits), "signals"),
    "Risk Flags": (pd.DataFrame(risk_hits), "risk"),
    "Confluence": (pd.DataFrame(confluence), "confluence"),
}

summary = {
    "batch_run_time": datetime.now(),
    "universe_size": 500,
    "entry_signals": len(entry_hits),
    "risk_flags": len(risk_hits),
    "high_conviction": len([c for c in confluence if c["weighted_score"] >= 3.0]),
}

save_multi_sheet_excel(sheets, "daily_batch.xlsx", summary_data=summary)
```

### Replace Existing Report Generation

If you have existing code like:

```python
# OLD - Plain Excel export
df.to_excel("report.xlsx", index=False)
```

Replace with:

```python
# NEW - Formatted Excel export
from excel_formatter import save_formatted_excel

save_formatted_excel(df, "report.xlsx", format_as="signals")
```

**Same file, 10x better presentation!**

---

## Customization

### Custom Color Scheme

```python
from excel_formatter import ExcelFormatter, ColorScheme

# Define custom colors
dark_theme = ColorScheme(
    header_bg="2C3E50",      # Dark slate
    header_text="ECF0F1",    # Light gray
    high_good="27AE60",      # Green
    medium="F39C12",         # Orange
    low_bad="E74C3C",        # Red
    risk_flag="C0392B",      # Dark red
    neutral="34495E",        # Gray
)

# Use custom scheme
formatter = ExcelFormatter("report.xlsx", color_scheme=dark_theme)
```

### Custom Column Widths

```python
custom_format = {
    "column_widths": {
        "symbol": 12,
        "pattern_type": 25,
        "reasons": 60,  # Wide column for text
        "score": 10,
    }
}

formatter.add_sheet(df, "Data", custom_format=custom_format)
```

### Custom Conditional Formatting

```python
custom_format = {
    "conditional_format": {
        # 3-color scale
        "weighted_score": {
            "type": "3color",
            "min": 0,
            "mid": 3,
            "max": 6,
        },
        # Threshold highlighting
        "has_risk": {
            "type": "threshold",
            "threshold": True,
            "operator": "==",
            "color": "FF6B6B",  # Red
        },
        # 2-color scale (white to green)
        "confidence": {
            "type": "2color",
            "min": 0,
            "max": 100,
        },
    }
}
```

---

## Format Preset Details

### Signals Format
```python
FormatPresets.signals()
```
Ideal for: Entry reports, scanner signals, trade setups

Features:
- Score columns: 0-100 scale, 1 decimal, color scale
- Price columns: ₹ format with 2 decimals
- R:R columns: Percentage format
- Symbol column: TradingView chart links
- Frozen header row

Columns auto-detected:
- `score`, `weighted_score`, `max_score` → Score format
- `entry`, `stop`, `target`, `close` → Price format
- `r:r`, `rr`, `rr_to_t2` → Percentage format
- `symbol` → Chart links

### Confluence Format
```python
FormatPresets.confluence()
```
Ideal for: Confluence reports, pattern matches

Features:
- Weighted score: 0-6 scale, color from red to green
- Raw hits: Integer count with color scale
- Category diversity: Integer
- Pattern matches: Wide column for text

### Risk Format
```python
FormatPresets.risk()
```
Ideal for: Risk monitoring, portfolio health checks

Features:
- Score-based coloring
- Risk flag highlighting
- Chart links for quick review

### Portfolio Format
```python
FormatPresets.portfolio()
```
Ideal for: Holdings reports, P&L tracking

Features:
- Return percentages: Color scale (red negative, green positive)
- Currency columns: ₹ format with commas
- Weight percentages: Portfolio allocation
- P&L: Formatted currency

---

## Column Name Recognition

The formatter automatically detects column types by name:

**Score Columns** (0-100 scale, 1 decimal):
- `score`, `weighted_score`, `max_score`, `confidence`, `quality`

**Price Columns** (₹ format, 2 decimals):
- `entry`, `stop`, `target`, `close`, `pivot`, `price`

**Percentage Columns** (%, 2 decimals):
- `r:r`, `rr`, `return_pct`, `change_pct`, `weight`

**Currency Columns** (₹ format, 0 decimals):
- `value`, `pnl`, `investment`, `market_value`

**Integer Columns**:
- `raw_hits`, `category_diversity`, `count`, `hits`

---

## Real-World Examples

### Daily Scanner Batch Report

```python
from excel_formatter import ExcelFormatter
from confluence_scoring import aggregate_weighted_confluence

# Run your batch scanners
all_results = run_all_batches(universe)
confluence_df = aggregate_weighted_confluence(all_results, sc.SCANNERS)

# Create formatted report
formatter = ExcelFormatter("daily_batch_2026-10-12.xlsx")

# Summary sheet
formatter.add_summary_sheet({
    "run_date": datetime.now().strftime("%Y-%m-%d"),
    "universe_size": len(universe),
    "total_signals": sum(len(hits) for batch in all_results.values() for hits in batch.values()),
    "high_conviction": (confluence_df["weighted_score"] >= 3.0).sum(),
    "entry_signals": confluence_df["has_entry"].sum(),
    "risk_flags": confluence_df["has_risk"].sum(),
})

# Entry signals sheet
entry_df = pd.DataFrame([
    hit for batch in all_results.values() if "entry" in batch
    for hits in batch.values() for hit in hits
])
formatter.add_sheet(entry_df, "Entry Signals", format_as="signals")

# Confluence sheet
formatter.add_sheet(confluence_df, "Confluence", format_as="confluence")

# Save
formatter.save()
```

### Portfolio Risk Monitor

```python
# Get holdings with risk flags
holdings = get_portfolio_holdings()
risk_flags = get_risk_scanner_hits(holdings["symbol"].tolist())

# Merge
portfolio_with_risk = holdings.merge(
    risk_flags,
    on="symbol",
    how="left"
)

# Format and save
save_formatted_excel(
    portfolio_with_risk,
    "portfolio_risk_monitor.xlsx",
    sheet_name="Holdings at Risk",
    format_as="portfolio",
    summary_data={
        "total_holdings": len(holdings),
        "holdings_at_risk": portfolio_with_risk["has_risk"].sum(),
        "total_exposure": portfolio_with_risk["value"].sum(),
    }
)
```

---

## Testing

Run the demo to verify everything works:

```bash
cd tools
python3 excel_formatter.py
```

Expected output:
```
Creating single-sheet report...
✅ Created: demo_signals.xlsx

Creating multi-sheet report...
✅ Created: demo_batch_report.xlsx

Creating advanced formatted report...
✅ Created: demo_advanced.xlsx

🎉 All demo files created successfully!
```

Open the generated files in Excel to see:
- Professional formatting
- Color scales working
- Clickable TradingView links
- Proper number formatting

---

## Requirements

- `pandas`
- `openpyxl` (install: `pip install openpyxl`)

---

## Performance Notes

- **Fast**: Pure Python, no external dependencies beyond openpyxl
- **Memory efficient**: Streams data to Excel, doesn't load entire file
- **File size**: Similar to plain Excel files
- **Compatibility**: Works with Excel 2007+ (`.xlsx` format)

---

## Troubleshooting

### Links not clickable
- Make sure symbol column name matches exactly (case-sensitive)
- TradingView requires exact NSE symbol format

### Colors not showing
- Open in Excel (not Google Sheets - limited support)
- Check Excel version (2007+ required for conditional formatting)

### Column widths too narrow
- Add custom widths in format dict:
  ```python
  custom_format = {"column_widths": {"my_column": 30}}
  ```

### Number format not applied
- Verify column names match expected patterns
- Add column to format preset explicitly

---

## Next Steps

Now that you have professional Excel reports:

1. **Integrate into opportunity_daily.py**
   - Replace plain `.to_excel()` with formatted export
   - Add summary sheet with run metadata

2. **Update scanner_batch_runner.py** (when built)
   - Use multi-sheet format for batch results
   - Separate sheets for each batch category

3. **Combine with Email Delivery (Next Quick Win)**
   - Attach formatted reports to automated emails
   - Much more professional than CSV attachments

4. **Add to Dashboard**
   - Generate formatted reports on-demand
   - Download button for current view

---

## Files Created

- `tools/excel_formatter.py` - Main implementation (586 lines)
- `EXCEL_FORMATTING_GUIDE.md` - This documentation
- Demo files:
  - `demo_signals.xlsx`
  - `demo_batch_report.xlsx`
  - `demo_advanced.xlsx`

---

## Validation

✅ Format presets work correctly  
✅ Conditional formatting applies properly  
✅ TradingView links generated  
✅ Multi-sheet reports created  
✅ Summary sheets formatted  
✅ Auto-column widths calculated  
✅ Number formats applied  
✅ Demo files generated successfully  
✅ Zero breaking changes to existing code

---

**Professional Excel reports are now just one function call away!** 📊

Open any demo file to see the quality difference. Your stakeholders will appreciate the upgrade.
