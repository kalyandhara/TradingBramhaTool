# Category-Weighted Confluence Scoring - Implementation Guide

**Status:** ✅ COMPLETED  
**Date:** 2026-10-12  
**Feature:** Quick Win #5 from Enhancement Backlog (Story 2.1.1)

---

## What Was Built

A category-weighted confluence scoring system that intelligently ranks stocks based on the **quality** of scanner signals, not just quantity.

### Key Features

1. **Category Weights**
   - Entry scanners: **2.0x** (highest value - actionable setups)
   - Momentum scanners: **1.8x** (strong continuation signals)
   - Trend scanners: **1.5x** (context/confirmation)
   - Pattern scanners: **1.2x** (geometric confirmation)
   - Risk scanners: **-1.0x** (penalty - contraindicators)
   - Neutral scanners: **0.0x** (informational only)

2. **Named Confluence Patterns**
   - **Pullback King**: Entry + Trend (score ≥ 3.5)
   - **Momentum Breakout**: Breakout + Momentum (score ≥ 3.5)
   - **Hidden Gem**: Single strong Entry signal (low confluence)
   - **Triple Threat**: Entry + Trend + Momentum (score ≥ 5.0)
   - **Risk-Off Warning**: Entry + Risk flags (proceed with caution)

3. **Quality Metrics**
   - Weighted score (category-adjusted)
   - Category diversity (# unique categories)
   - Entry signal presence
   - Risk flag presence
   - Max individual scanner score

---

## Real-World Impact

### Before (Raw Count Only)
```
Stock A: 3 pattern hits → Score: 3
Stock B: 2 entry + 1 trend → Score: 3
Stock C: 1 entry + 1 risk → Score: 2
```
All look similar, but Stock B has the best edge.

### After (Category-Weighted)
```
Stock A: Darvas + Triangle + VCP → Weighted: 3.6 (3 × 1.2)
Stock B: Pullback + Stage 2 + HM Buy → Weighted: 5.5 (2.0 + 1.5 + 2.0)
Stock C: Pullback + RSI Bear → Weighted: 1.0 (2.0 - 1.0)
```
Now Stock B ranks highest, Stock C is correctly penalized.

---

## How to Use

### 1. Basic Usage - Calculate Weighted Confluence

```python
import scanner_templates as sc
from confluence_scoring import aggregate_weighted_confluence

# Your existing batch results
all_results = {
    "entry_setups": {
        "Pullback Entry": [...],
        "HM Buy": [...],
    },
    "trend_context": {
        "Stage 2 Uptrend": [...],
    },
    # ... more batches
}

# Calculate weighted confluence
df = aggregate_weighted_confluence(all_results, sc.SCANNERS)

# Results include:
# - symbol
# - raw_hits (unweighted count)
# - weighted_score (category-weighted)
# - scanners (names)
# - categories (unique categories)
# - max_score (best individual score)
# - has_entry, has_risk
# - category_diversity
```

### 2. Filter by Quality Thresholds

```python
from confluence_scoring import filter_by_weighted_score

# High conviction picks (weighted score ≥ 3.0)
high_conviction = filter_by_weighted_score(
    df,
    min_weighted_score=3.0,
    require_entry=True,      # Must have at least one Entry scanner
    exclude_risk=False,      # Set True to exclude stocks with Risk flags
)
```

### 3. Detect Named Patterns

```python
from confluence_scoring import detect_confluence_patterns

# Add pattern matches to results
df_with_patterns = detect_confluence_patterns(df)

# Find all "Pullback King" setups
pullback_kings = df_with_patterns[
    df_with_patterns["matched_patterns"].str.contains("Pullback King")
]
```

### 4. Get Summary Statistics

```python
from confluence_scoring import get_confluence_summary

summary = get_confluence_summary(df)
print(f"High conviction count: {summary['high_conviction_count']}")
print(f"Entry signals: {summary['entry_signal_count']}")
print(f"Risk flags: {summary['risk_flag_count']}")
```

---

## Integration with Existing Code

### Option A: Update `opportunity_daily.py`

Replace the simple confluence counting with weighted scoring:

```python
# In opportunity_daily.py

from confluence_scoring import aggregate_weighted_confluence, filter_by_weighted_score
import scanner_templates as sc

def run_opportunity_daily():
    # ... existing universe building code ...
    
    # Run all scanners (existing code)
    all_results = run_all_batches(universe)
    
    # NEW: Calculate weighted confluence instead of simple count
    confluence_df = aggregate_weighted_confluence(all_results, sc.SCANNERS)
    
    # Apply quality filters
    high_quality = filter_by_weighted_score(
        confluence_df,
        min_weighted_score=3.0,
        require_entry=True,
    )
    
    # Use weighted_score instead of raw hit count for final ranking
    # ... rest of your existing code ...
```

### Option B: Create New Batch Runner (from SCREENER_BATCH_WORKFLOW.md)

Use weighted confluence in the new `scanner_batch_runner.py`:

```python
# In scanner_batch_runner.py (new file, as per workflow doc)

from confluence_scoring import (
    aggregate_weighted_confluence,
    get_confluence_summary,
    detect_confluence_patterns,
)

def run_all_batches(universe, days=400):
    # ... existing batch execution code ...
    
    # Calculate weighted confluence
    confluence_df = aggregate_weighted_confluence(all_results, sc.SCANNERS)
    
    # Add pattern detection
    confluence_df = detect_confluence_patterns(confluence_df)
    
    # Log summary
    summary = get_confluence_summary(confluence_df)
    log.info(f"Confluence: {summary['high_conviction_count']} high-conviction picks")
    
    return confluence_df
```

---

## Customization

### Adjust Category Weights

Edit `confluence_scoring.py` to tune weights based on your backtests:

```python
CATEGORY_WEIGHTS = {
    "Entry": 2.5,      # Increase if your entry scanners have exceptional edge
    "Momentum": 1.8,
    "Trend": 1.5,
    "Pattern": 1.0,    # Decrease if patterns are less reliable
    "Risk": -1.5,      # Increase penalty if risk flags are highly predictive
    "Neutral": 0.0,
}
```

### Add Custom Patterns

Define your own confluence patterns:

```python
CONFLUENCE_PATTERNS["My Pattern"] = {
    "description": "Custom setup description",
    "required_scanners": ["Specific Scanner Name"],
    "required_categories": ["Entry", "Momentum"],
    "min_weighted_score": 4.0,
    "min_category_diversity": 2,
    "notes": "Your trading notes",
}
```

---

## Testing

Run the built-in demo to verify everything works:

```bash
cd tools
python3 confluence_scoring.py
```

Expected output:
- Weighted confluence table
- Summary statistics
- High conviction picks
- Pattern matches

---

## Performance Notes

- **Speed**: Very fast - pure pandas operations, no API calls
- **Memory**: Minimal - operates on results already in memory
- **Compatibility**: Works with existing scanner_templates.py without modifications

---

## Next Steps

Once you're comfortable with weighted confluence, consider:

1. **Time-Decay Scoring (Story 2.1.2)**
   - Older signals decay in weight (1 day = 100%, 7 days = 25%)
   - Prioritizes fresh setups

2. **Historical Performance Weighting (Story 2.1.3)**
   - Auto-adjust weights quarterly based on scanner win rates
   - Data-driven weight optimization

3. **Excel Report Formatting (Story 3.1.1)**
   - Add weighted_score column to reports
   - Color-code by conviction level
   - Sort by weighted_score instead of raw hits

4. **Email Delivery (Story 5.1.1)**
   - Send only high-conviction picks (weighted_score ≥ 3.5)
   - Separate reports for different conviction levels

---

## Files Created

- `tools/confluence_scoring.py` - Main implementation (478 lines)
- `WEIGHTED_CONFLUENCE_GUIDE.md` - This documentation

---

## Validation

✅ Scanner categories identified (Entry, Trend, Momentum, Pattern, Risk, Neutral)  
✅ Weights assigned based on trading value  
✅ Tested with mock data - correct weighted scores  
✅ Named patterns detected correctly  
✅ Summary statistics accurate  
✅ Filtering functions work as expected  
✅ Zero breaking changes to existing code

---

**Ready to integrate into your workflow!**

To use immediately:
1. Import the functions in your existing scripts
2. Replace simple hit counts with weighted scores
3. Sort/filter by weighted_score instead of raw_hits
4. Enjoy better signal quality! 📈
