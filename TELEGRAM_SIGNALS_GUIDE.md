# Telegram Trading Signals Integration Guide

## Overview

The Trading Bramha dashboard now includes a **Telegram Signals** tab to:
1. Manually log trading signals from Telegram channels
2. Track signal performance (entry, exit, return %)
3. Measure strategy effectiveness
4. Aggregate signals from multiple channels

## Supported Channels

Currently integrated/documented:
- **@rohaninvestor** (Rohan Das) — RPCI Indicator strategy
- **TechnoFunda** — Technical + Fundamental analysis
- **Technical Trades Public Channel** — Pattern recognition
- Other custom channels (manual entry)

## What is RPCI?

**RPCI** (Rule-based Pattern Confidence Indicator) is Rohan Das's proprietary trading strategy:

### Key Features:
- **Automation:** Rule-based signals that simplify technical analysis
- **User Base:** 1500+ stock market traders using it
- **Validation:** SEBI-registered traders use it for institutional accounts
- **Track Record:** Consistent signals shared on Telegram & Twitter
- **Method:** Identifies stocks with:
  - Stronger trend structure
  - Better momentum
  - Relative performance (RS line)
  - Improving technical conditions

### Example Signal: MOTHERSON
```
Posted: 25 June 2026
Channel: Rohan Das (@rohaninvestor)
Strategy: RPCI Indicator
Timeframe: Medium-term (1-4 weeks)
Confidence: 8/10

Details:
- RPCI identified MOTHERSON as strong candidate
- SEBI RA confirmed on 27 June for next week accumulation
- Signal came BEFORE mainstream recommendation
- Entry: Accumulation zone (multiple entry points)
- Target: Multi-leg (higher targets as trend develops)
- Risk: Appropriate stops based on technical levels
```

## Dashboard: Telegram Signals Tab

### 1. Add Signal (Subsection)
**How to log a new signal:**

1. **Manual Entry:**
   - Channel: Name of Telegram channel
   - Symbol: Stock ticker (auto-uppercased)
   - Posted Date: When signal was shared
   - Strategy: RPCI, TechnoFunda, Chart Pattern, etc.
   - Timeframe: Intraday / Short / Medium / Long-term
   - Confidence: 1-10 rating
   - Prices: Entry, Target, Stop Loss (optional)
   - Notes: Paste key analysis from Telegram post

2. **Pre-filled Templates:**
   - Button: "Load Example: Rohan Das RPCI (MOTHERSON)"
   - Auto-populates known good signals for reference

3. **Add Button:**
   - Saves signal to persistent JSON storage
   - Assigns unique Signal ID (timestamp + channel + symbol)
   - Shows confirmation

### 2. Active Signals (Subsection)
**Track live positions:**

Each active signal shows:
- **Summary:**
  - Symbol & Strategy
  - Confidence level
  - Channel source
  - Posted date

- **Prices:**
  - Entry Price (if specified)
  - Target Price (if specified)
  - Stop Loss (if specified)

- **Actions:**
  - "Mark Active" — Move to active positions
  - "Partial Exit" — Take partial profit
  - "Close" — Exit position + record return %
  - "Cancel" — Invalidate signal

### 3. Signal History (Subsection)
**All signals (active + closed):**

Table view showing:
- Symbol | Channel | Strategy | Status | Confidence
- Entry | Target | Return % | Posted Date

**Export Options:**
- Download as CSV for external analysis
- Integrates with portfolio tracking systems

### 4. Statistics (Subsection)
**Performance metrics:**

**Key Metrics:**
- Total Signals (all-time)
- Active/Pending (current)
- Closed Signals (completed trades)
- Win Rate (% of profitable signals)
- Avg Return (mean return on closed signals)
- Total Return (sum of all returns)
- Best Signal (highest return)

**Breakdowns by:**
- Channel (Rohan Das, TechnoFunda, etc.)
- Strategy (RPCI, Technical, Pattern, etc.)

## Workflow Examples

### Example 1: Log Rohan Das RPCI Signal
```
1. Open Dashboard → "Telegram Signals" tab
2. Go to "Add Signal" subsection
3. Click "Load Example: Rohan Das RPCI (MOTHERSON)"
4. Review pre-filled data (optional: edit)
5. Click "Add Signal"
6. Signal stored with ID: 20260625_Rohan Das _MOTHER_0
```

### Example 2: Track Signal Through Lifecycle
```
1. Signal added → Status: PENDING
2. Market opens, stock moves → Click "Mark Active"
3. Entry confirmed → Status: ACTIVE, entry_date set
4. Partial profit taken → Click "Partial Exit", Status: PARTIAL
5. Exit at target → Click "Close", enter return %, Status: CLOSED
6. View in "Signal History" with realized return recorded
```

### Example 3: Measure Channel Performance
```
1. Open Dashboard → "Telegram Signals" tab → "Statistics"
2. View "Signals by Channel" breakdown
3. See which channels have highest win rate
4. Double-down on best-performing channels
5. Reduce exposure to underperforming channels
```

### Example 4: Track Strategy Effectiveness
```
1. Go to "Statistics" subsection
2. Check "Signals by Strategy" breakdown
3. Identify which strategies (RPCI, TechnoFunda, etc.) perform best
4. Allocate capital accordingly
5. A/B test new strategies by comparing their stats
```

## Using telegram_signals.py Programmatically

### Load & Add Signals
```python
from telegram_signals import TelegramSignals
from datetime import date

ts = TelegramSignals()

# Add RPCI signal
rpci = {
    'symbol': 'MOTHERSON',
    'channel': 'Rohan Das (@rohaninvestor)',
    'posted_date': date(2026, 6, 25),
    'strategy': 'RPCI Indicator',
    'signal_source': 'RPCI',
    'timeframe': 'Medium-term',
    'confidence': 8,
    'notes': 'RPCI identified before SEBI RA confirmation...'
}

signal = ts.add_signal_from_dict(rpci)
print(f"Added: {signal.signal_id}")
```

### Query Signals
```python
# Get active signals
active = ts.get_active_signals()
print(f"Active: {len(active)} signals")

# Get Rohan Das signals
rohan_signals = ts.get_signals_by_channel('Rohan Das')

# Get all MOTHERSON signals
moth_signals = ts.get_signals_by_symbol('MOTHERSON')

# Get signals from last week
recent = ts.get_signals_by_date_range(date(2026, 6, 21), date(2026, 6, 28))
```

### Track Performance
```python
# Update signal on exit
ts.update_signal(
    signal_id='20260625_Rohan Das _MOTHER_0',
    status='closed',
    exit_date=date(2026, 7, 5),
    realized_return=12.5  # 12.5% profit
)

# Get statistics
stats = ts.get_signal_statistics()
print(f"Win Rate: {stats['win_rate']}%")
print(f"Avg Return: {stats['avg_return']}%")

# Get winning signals
winners = ts.get_winning_signals(min_return=5.0)
for signal, return_pct in winners:
    print(f"{signal.symbol}: +{return_pct}%")
```

### Export Signals
```python
# Export to CSV
csv_path = ts.export_to_csv('/path/to/signals.csv')

# Access JSON storage
# Signals stored in: ~/.trading_signals/signals.json
```

## Signal Statuses

| Status | Meaning | Action |
|--------|---------|--------|
| **PENDING** | Signal posted, awaiting entry confirmation | Review & confirm |
| **ACTIVE** | Entered position | Monitor & manage |
| **PARTIAL** | Partial exit taken | Continue tracking |
| **CLOSED** | Position fully exited | Record return % |
| **CANCELLED** | Signal invalidated (stop hit) | No longer tracked |
| **EXPIRED** | Signal outside validity window | Archived |

## Data Storage

### File Locations
```
~/.trading_signals/signals.json          # All signals (persistent)
~/.trading_signals/signals_export.csv    # CSV export (optional)
```

### Data Structure (JSON)
```json
{
  "20260625_Rohan Das _MOTHER_0": {
    "signal_id": "20260625_Rohan Das _MOTHER_0",
    "channel": "Rohan Das (@rohaninvestor)",
    "posted_date": "2026-06-25",
    "symbol": "MOTHERSON",
    "strategy": "RPCI Indicator",
    "signal_source": "RPCI",
    "entry_price": null,
    "target_price": null,
    "stop_loss": null,
    "timeframe": "Medium-term (1-4 weeks)",
    "confidence": 8,
    "status": "pending",
    "entry_date": null,
    "exit_date": null,
    "realized_return": null,
    "notes": "RPCI identified MOTHERSON...",
    "metadata": {
      "indicator": "RPCI",
      "user_count": "1500+",
      "sebi_ra_confirmation": "Yes (27 June)"
    }
  }
}
```

## Best Practices

1. **Log Promptly:** Add signals to dashboard same day they're posted (maintains accuracy)
2. **Include Context:** Copy relevant analysis from Telegram post into Notes field
3. **Be Objective:** Record entry/exit prices at actual execution (not target)
4. **Track Returns:** Always record realized % return when closing
5. **Review Weekly:** Check Statistics to identify best-performing channels/strategies
6. **Double-Check:** Verify data before closing signals (prevents recording errors)
7. **Backup:** Periodically export CSV as backup

## Limitations & Notes

- ✅ Manual entry (copy-paste from Telegram)
- ✅ Supports multiple channels
- ✅ Tracks any strategy type
- ✅ Persistent JSON storage
- ❌ Not a real-time bot (requires manual entry)
- ❌ No automatic Telegram API scraping (compliance reasons)
- ❌ No chart images/links stored (reference in Notes instead)

## Future Enhancements

- [ ] Telegram Bot integration (auto-log signals via bot)
- [ ] Image attachment support (screenshot of Telegram post)
- [ ] Alert system (notify when signal targets/stops hit)
- [ ] Performance by timeframe (intraday vs. swing vs. long-term)
- [ ] Sharpe ratio & other risk-adjusted metrics
- [ ] Correlation analysis (signal X performs well during Y condition)
- [ ] A/B testing framework for signal comparison
- [ ] Integration with actual broker APIs (auto-execute signals)

## Support & Questions

**Example signals to get started:**
- See "Load Example: Rohan Das RPCI (MOTHERSON)" button

**Documentation:**
- This file: `TELEGRAM_SIGNALS_GUIDE.md`
- Module code: `tools/telegram_signals.py` (well-commented)
- Dashboard: "Telegram Signals" tab in Streamlit

**Manual Storage Location:**
- `~/.trading_signals/signals.json`
- Edit directly if needed (JSON format)

---

**Last Updated:** June 28, 2026  
**Status:** Production Ready  
**Version:** 1.0
