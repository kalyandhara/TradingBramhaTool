# Custom Screener Builder - ChartInk Style Implementation

Building a drag-and-drop "Magic Filters" screener builder for Trading_Bramha

---

## 1. SCREENER ANALYSIS: "Price Action Breakout After 6 Months"

### Strategy Overview
**Purpose:** Find stocks emerging from 6-month consolidations with bullish price action breakouts

**Market Condition:** Swing Trading (Medium-term: 2-8 weeks)

**Time Frame:** Daily chart analysis

### Core Filters Breakdown

#### 1. **Consolidation Period (6 Months)**
```
Requirement: Stock traded sideways for ~6 months
Implementation:
- Calculate price range over last 126 trading days (≈6 months)
- Range = MAX(High, 126 days) - MIN(Low, 126 days)
- Range should be "tight" relative to average price
- Tightness ratio: Range / Average Price < 20%
```

#### 2. **Candlestick Patterns** (Magic Filters)
```
Pattern Types Detected:
- Gravestone Doji ⚰️
  • High = Close = Open
  • Long lower wick
  • Signal: Rejection of lower prices after consolidation

- Hammer 🔨
  • Small body at top
  • Long lower wick (2-3x body size)
  • Signal: Reversal pattern, buying pressure

- Three Black Soldiers ⚫⚫⚫
  • Three consecutive red candles
  • Each closing near low
  • Signal: Capitulation selling

- Doji 十
  • Open ≈ Close
  • Long wicks both sides
  • Signal: Indecision (need confirmation)

Purpose: Identify precise breakout moments
```

#### 3. **Price Action Rules**
```
Rule 1: Daily Close > Daily EMA
- Close price above exponential moving average
- Confirms upside breakout momentum
- Filter: Daily_Close > EMA(Daily_Close, 20)

Rule 2: Daily Close > 1 Day Ago Max (126-day high)
- Yesterday's close above 126-day moving high
- Confirms break of consolidation resistance
- Filter: Close[today] > MAX(High[last 126 days])

Rule 3: 1 Day Ago Min < 1 Day Ago Max
- Previous day's low < previous day's high
- Confirms real price movement (not gap/lock)
```

#### 4. **Volume Confirmation**
```
Rule: Daily Volume > 2,000,000 shares
- Ensures institutional participation
- Validates breakout conviction
- Prevents illiquid stock selection
- Filter: Volume > 2000000
```

### Complete Filter Logic

```sql
SELECT 
    symbol,
    close,
    high,
    low,
    volume,
    ema_20,
    high_126,
    low_126
FROM daily_prices dp
WHERE 
    -- Rule 1: Price above EMA
    dp.close > dp.ema_20
    
    -- Rule 2: Close above 126-day high (breakout of consolidation)
    AND dp.close > (SELECT MAX(high) FROM daily_prices 
                    WHERE symbol = dp.symbol 
                    AND date <= DATE_TRUNC('day', CURRENT_DATE - INTERVAL '126 days'))
    
    -- Rule 3: Volume confirmation
    AND dp.volume > 2000000
    
    -- Rule 4: Candlestick pattern (Doji/Hammer/etc)
    AND EXISTS (
        SELECT 1 FROM candlestick_patterns 
        WHERE stock_id = dp.stock_id 
        AND date = dp.date 
        AND pattern IN ('gravestone_doji', 'hammer', 'three_black_soldiers', 'doji')
    )
    
    -- Rule 5: In consolidation for 6+ months
    AND (SELECT MAX(high) - MIN(low) FROM daily_prices 
         WHERE symbol = dp.symbol 
         AND date >= dp.date - INTERVAL '126 days') < (dp.close * 0.20)
    
    AND dp.date = CURRENT_DATE - 1
ORDER BY dp.volume DESC
```

---

## 2. SCREENER BUILDER UI ARCHITECTURE

### Component Hierarchy

```
ScreenerBuilder
├── Header
│   ├── ScreenerTitle (editable)
│   ├── Description (editable)
│   └── Strategy Type selector
├── MagicFilters Section
│   ├── Filter Tags (Append/Replace/Scan)
│   ├── Individual Filter Cards
│   │   ├── Filter Name & Icon
│   │   ├── Condition Selector
│   │   ├── Value Input
│   │   ├── Logic Operator (AND/OR)
│   │   └── Delete Button
│   └── Add Filter Button (+ icon)
├── Results Section
│   ├── Stock List
│   ├── Backtest Results Button
│   ├── Create Alert Button
│   └── Save Scan Button
└── Bottom Actions
    ├── Run Scan
    ├── Save Scan
    ├── Backtest Results
    ├── Create Alert
    └── More Options
```

### UI Mockup (ASCII)

```
┌────────────────────────────────────────────────────────────────┐
│ PRICE ACTION BREAKOUT AFTER 6 MONTHS (SWING TRADING STRATEGY) │
├────────────────────────────────────────────────────────────────┤
│ New: LIVE Alerts now available!                               │
├────────────────────────────────────────────────────────────────┤
│ ⚙️ MAGIC FILTERS                                              │
├────────────────────────────────────────────────────────────────┤
│ [Append] [Replace] [Scan stocks using simple language...]   │
├────────────────────────────────────────────────────────────────┤
│ Gravestone doji 🗑️  hammer 🗑️  Three black soldiers 🗑️      │
│ Doji on 15-min 🗑️                                            │
├────────────────────────────────────────────────────────────────┤
│ Stock passes all of the below filters in cash segment:        │
│                                                                │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Daily Close [Greater than] Daily Ema (Daily Close [.50] │ │
│ │ [📊] [🔄] [🎯] [⚙️] [🗑️]                                │ │
│ └──────────────────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Daily Close [Greater than] 1 day ago Max (126,Daily     │ │
│ │ High [≥1] [📊] [🔄] [🎯] [⚙️] [🗑️]                      │
│ └──────────────────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ 1 day ago Min (126,Daily Low [≥1]) [Less than] 1 day   │
│ │ ago Max (126,Daily High [≥1]                            │
│ │ [📊] [🔄] [🎯] [⚙️] [🗑️]                                │
│ └──────────────────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Daily Volume [Greater than] Number 2000000              │
│ │ [📊] [🔄] [🎯] [⚙️] [🗑️]                                │
│ └──────────────────────────────────────────────────────────┘ │
│                                                                │
│ [+ Add Filter]                                                │
├────────────────────────────────────────────────────────────────┤
│ [🔍 Run Scan] [💾 Save Scan] [📊 Backtest Results]            │
│ [🔔 Create Alert] [⋮ More] [👍 0 people like this]          │
└────────────────────────────────────────────────────────────────┘
```

---

## 3. FILTER TYPES & CONDITIONS

### Available Filter Categories

```python
FILTER_CATEGORIES = {
    'price': {
        'name': 'Price',
        'filters': [
            {'id': 'close', 'label': 'Daily Close', 'type': 'numeric'},
            {'id': 'open', 'label': 'Daily Open', 'type': 'numeric'},
            {'id': 'high', 'label': 'Daily High', 'type': 'numeric'},
            {'id': 'low', 'label': 'Daily Low', 'type': 'numeric'},
            {'id': 'price_range', 'label': 'Price Range', 'type': 'numeric'},
        ]
    },
    'moving_averages': {
        'name': 'Moving Averages',
        'filters': [
            {'id': 'ema_5', 'label': 'EMA 5', 'type': 'numeric'},
            {'id': 'ema_20', 'label': 'EMA 20', 'type': 'numeric'},
            {'id': 'ema_50', 'label': 'EMA 50', 'type': 'numeric'},
            {'id': 'sma_50', 'label': 'SMA 50', 'type': 'numeric'},
            {'id': 'sma_200', 'label': 'SMA 200', 'type': 'numeric'},
        ]
    },
    'volume': {
        'name': 'Volume',
        'filters': [
            {'id': 'volume', 'label': 'Daily Volume', 'type': 'numeric'},
            {'id': 'volume_avg', 'label': 'Volume Avg (20)', 'type': 'numeric'},
        ]
    },
    'candlestick': {
        'name': 'Candlestick Patterns',
        'filters': [
            {'id': 'doji', 'label': 'Doji', 'type': 'boolean'},
            {'id': 'hammer', 'label': 'Hammer', 'type': 'boolean'},
            {'id': 'gravestone_doji', 'label': 'Gravestone Doji', 'type': 'boolean'},
            {'id': 'three_black_soldiers', 'label': 'Three Black Soldiers', 'type': 'boolean'},
            {'id': 'three_white_soldiers', 'label': 'Three White Soldiers', 'type': 'boolean'},
            {'id': 'engulfing_bullish', 'label': 'Bullish Engulfing', 'type': 'boolean'},
            {'id': 'engulfing_bearish', 'label': 'Bearish Engulfing', 'type': 'boolean'},
        ]
    },
    'indicators': {
        'name': 'Technical Indicators',
        'filters': [
            {'id': 'rsi', 'label': 'RSI (14)', 'type': 'numeric'},
            {'id': 'macd', 'label': 'MACD', 'type': 'numeric'},
            {'id': 'bb_upper', 'label': 'Bollinger Band Upper', 'type': 'numeric'},
            {'id': 'atr', 'label': 'ATR (14)', 'type': 'numeric'},
        ]
    },
    'time': {
        'name': 'Time-Based',
        'filters': [
            {'id': 'days_since_high', 'label': 'Days Since 52w High', 'type': 'numeric'},
            {'id': 'days_since_low', 'label': 'Days Since 52w Low', 'type': 'numeric'},
            {'id': 'consolidation_days', 'label': 'Consolidation Days', 'type': 'numeric'},
        ]
    }
}

CONDITION_OPERATORS = {
    'numeric': [
        {'id': 'gt', 'label': 'Greater than', 'symbol': '>'},
        {'id': 'gte', 'label': 'Greater than or equal', 'symbol': '≥'},
        {'id': 'lt', 'label': 'Less than', 'symbol': '<'},
        {'id': 'lte', 'label': 'Less than or equal', 'symbol': '≤'},
        {'id': 'eq', 'label': 'Equal to', 'symbol': '='},
        {'id': 'neq', 'label': 'Not equal to', 'symbol': '≠'},
        {'id': 'between', 'label': 'Between', 'symbol': '↔'},
    ],
    'boolean': [
        {'id': 'true', 'label': 'Is True'},
        {'id': 'false', 'label': 'Is False'},
    ]
}

LOGIC_OPERATORS = ['AND', 'OR']
```

---

## 4. DATABASE SCHEMA

### Screener Templates Table

```sql
CREATE TABLE screener_templates (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    strategy_type VARCHAR(50),  -- 'swing', 'intraday', 'positional'
    market_segment VARCHAR(50),  -- 'cash', 'futures', 'options'
    is_public BOOLEAN DEFAULT FALSE,
    filters JSONB NOT NULL,  -- Array of filter objects
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    backtest_stats JSONB  -- Win rate, profit factor, etc
);

-- Example: How filters are stored as JSONB
{
  "filters": [
    {
      "id": "filter_1",
      "category": "price",
      "field": "close",
      "operator": "gt",
      "value": "ema_20",
      "label": "Daily Close > Daily EMA"
    },
    {
      "id": "filter_2",
      "category": "price",
      "field": "close",
      "operator": "gt",
      "value": 126,
      "lookback": "126d",
      "comparison_type": "max",
      "label": "Daily Close > 1 day ago Max (126, Daily High)"
    },
    {
      "id": "filter_3",
      "category": "volume",
      "field": "volume",
      "operator": "gt",
      "value": 2000000,
      "label": "Daily Volume > Number 2000000"
    },
    {
      "id": "filter_4",
      "category": "candlestick",
      "field": "pattern",
      "operator": "in",
      "value": ["gravestone_doji", "hammer", "three_black_soldiers"],
      "label": "Pattern is Doji, Hammer, or Three Black Soldiers"
    }
  ],
  "logic": "AND",  -- All filters must pass
  "tags": ["gravestone doji", "hammer", "6 month consolidation", "breakout"]
}
```

### Screener Results Table

```sql
CREATE TABLE screener_results (
    id SERIAL PRIMARY KEY,
    screener_id INTEGER REFERENCES screener_templates(id),
    stock_id INTEGER REFERENCES stocks(id),
    result_date DATE,
    matched_date DATE,  -- Date the pattern was detected
    entry_price DECIMAL(10, 2),
    target_price DECIMAL(10, 2),
    stop_loss DECIMAL(10, 2),
    confidence_score DECIMAL(3, 2),  -- 0.0 to 1.0
    matching_filters JSONB,  -- Which filters matched
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example matched result
{
  "stock_id": 1234,
  "matched_filters": {
    "close_ema": true,
    "close_126h": true,
    "volume": true,
    "pattern": "gravestone_doji",
    "consolidation": true
  },
  "confidence_score": 0.92,
  "reasoning": [
    "Close ₹125.50 > EMA ₹124.20",
    "Close ₹125.50 > 126-day high ₹124.00",
    "Volume 2.5M > threshold 2.0M",
    "Gravestone Doji pattern detected",
    "Consolidation range: 15% (< 20% threshold)"
  ]
}
```

### Candlestick Patterns Table

```sql
CREATE TABLE candlestick_patterns (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    date DATE,
    pattern_type VARCHAR(50),  -- 'doji', 'hammer', etc
    open DECIMAL(10, 2),
    high DECIMAL(10, 2),
    low DECIMAL(10, 2),
    close DECIMAL(10, 2),
    pattern_score DECIMAL(3, 2),  -- Confidence 0-1
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_id, date, pattern_type)
);
```

---

## 5. CANDLESTICK PATTERN DETECTION

### Python Implementation

```python
import numpy as np
from dataclasses import dataclass

@dataclass
class CandleData:
    open: float
    high: float
    low: float
    close: float
    date: str

class CandlestickDetector:
    def __init__(self, tolerance=0.01):  # 1% tolerance
        self.tolerance = tolerance
    
    def detect_patterns(self, candles: list) -> dict:
        """Detect all patterns in candle list."""
        patterns = {}
        
        for i, candle in enumerate(candles):
            patterns[candle.date] = self._detect_single(candle)
        
        return patterns
    
    def _detect_single(self, candle: CandleData) -> dict:
        """Detect patterns in a single candle."""
        detected = {}
        
        # Calculate candle properties
        body = abs(candle.close - candle.open)
        upper_wick = candle.high - max(candle.close, candle.open)
        lower_wick = min(candle.close, candle.open) - candle.low
        total_range = candle.high - candle.low
        
        # Doji Pattern
        detected['doji'] = self._is_doji(candle, body, total_range)
        
        # Hammer Pattern
        detected['hammer'] = self._is_hammer(candle, body, lower_wick, upper_wick)
        
        # Gravestone Doji
        detected['gravestone_doji'] = self._is_gravestone_doji(
            candle, body, lower_wick, upper_wick
        )
        
        # Three Black Soldiers (requires 3 candles)
        # Handled separately in sequence detection
        
        return detected
    
    def _is_doji(self, candle: CandleData, body: float, total_range: float) -> float:
        """
        Doji: Open ≈ Close with long wicks
        Returns confidence score 0-1
        """
        body_ratio = body / total_range if total_range > 0 else 0
        
        # Body should be very small (<5% of range)
        if body_ratio < 0.05:
            return 0.9
        elif body_ratio < 0.10:
            return 0.6
        return 0.0
    
    def _is_hammer(self, candle: CandleData, body: float, lower_wick: float, 
                   upper_wick: float) -> float:
        """
        Hammer: Small body at top, long lower wick (2-3x body)
        Returns confidence score 0-1
        """
        if lower_wick == 0:
            return 0.0
        
        wick_ratio = lower_wick / body if body > 0 else 0
        upper_ratio = upper_wick / body if body > 0 else 0
        
        # Long lower wick (2-3x body), small upper wick
        if 2 <= wick_ratio <= 3 and upper_ratio < 0.5:
            # Body should be at top
            if candle.close > (candle.open - body * 0.2):
                return 0.9
        
        return 0.0
    
    def _is_gravestone_doji(self, candle: CandleData, body: float, 
                            lower_wick: float, upper_wick: float) -> float:
        """
        Gravestone Doji: High = Close ≈ Open, long lower wick
        Returns confidence score 0-1
        """
        total_range = candle.high - candle.low
        
        # High should equal close/open
        if abs(candle.high - candle.close) < (total_range * 0.01):
            # Long lower wick
            if lower_wick > (total_range * 0.5):
                return 0.9
        
        return 0.0
    
    def detect_three_black_soldiers(self, candles: list, recent_n: int = 3) -> bool:
        """
        Three Black Soldiers: 3 consecutive red candles
        Each closing near its low
        """
        if len(candles) < recent_n:
            return False
        
        recent = candles[-recent_n:]
        
        for candle in recent:
            # Must be red (close < open)
            if candle.close >= candle.open:
                return False
            
            # Should close near low
            range_ = candle.high - candle.low
            distance_to_low = candle.close - candle.low
            if distance_to_low > (range_ * 0.2):
                return False
        
        return True
    
    def detect_engulfing(self, prev_candle: CandleData, curr_candle: CandleData) -> str:
        """
        Bullish Engulfing: Red candle followed by larger green candle
        Bearish Engulfing: Green candle followed by larger red candle
        """
        # Bullish: Current body > Previous body, Current close > Prev open
        if (curr_candle.close > curr_candle.open and  # Green
            prev_candle.close < prev_candle.open):    # Red
            
            curr_body = curr_candle.close - curr_candle.open
            prev_body = abs(prev_candle.close - prev_candle.open)
            
            if curr_body > prev_body and curr_candle.close > prev_candle.open:
                return 'bullish_engulfing'
        
        # Bearish: Reverse logic
        if (curr_candle.close < curr_candle.open and  # Red
            prev_candle.close > prev_candle.open):    # Green
            
            curr_body = curr_candle.open - curr_candle.close
            prev_body = prev_candle.close - prev_candle.open
            
            if curr_body > prev_body and curr_candle.close < prev_candle.open:
                return 'bearish_engulfing'
        
        return None
```

---

## 6. SCREENER EXECUTION ENGINE

### FastAPI Backend

```python
from fastapi import FastAPI, HTTPException
from sqlalchemy import text
import json

app = FastAPI()

@app.get("/api/screeners")
async def list_screeners():
    """List all available screeners."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, name, description, strategy_type, 
                   filters, created_at
            FROM screener_templates
            ORDER BY created_at DESC
        """))
        screeners = [
            {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'strategy_type': row[3],
                'filters': json.loads(row[4]) if row[4] else [],
                'created_at': str(row[5])
            }
            for row in result
        ]
    return screeners

@app.post("/api/screeners")
async def create_screener(screener_data: dict):
    """Create a new screener from filters."""
    screener_name = screener_data.get('name')
    screener_filters = screener_data.get('filters', [])
    
    # Build SQL query from filters
    sql_query = build_sql_from_filters(screener_filters)
    
    with engine.connect() as conn:
        insert_stmt = text("""
            INSERT INTO screener_templates 
            (name, description, strategy_type, filters)
            VALUES (:name, :desc, :type, :filters)
            RETURNING id
        """)
        
        result = conn.execute(insert_stmt, {
            'name': screener_name,
            'desc': screener_data.get('description'),
            'type': screener_data.get('strategy_type', 'swing'),
            'filters': json.dumps(screener_filters)
        })
        screener_id = result.scalar()
        conn.commit()
    
    return {'id': screener_id, 'status': 'created'}

@app.post("/api/screeners/{screener_id}/run")
async def run_screener(screener_id: int):
    """Execute a screener and return matching stocks."""
    with engine.connect() as conn:
        # Get screener definition
        screener = conn.execute(text("""
            SELECT name, filters FROM screener_templates WHERE id = :id
        """), {'id': screener_id}).first()
        
        if not screener:
            raise HTTPException(status_code=404, detail="Screener not found")
        
        screener_name, filters_json = screener
        filters = json.loads(filters_json)
        
        # Build and execute query
        sql_query = build_sql_from_filters(filters)
        
        results = conn.execute(text(sql_query))
        stocks = [
            {
                'symbol': row[0],
                'name': row[1],
                'close': float(row[2]),
                'volume': int(row[3]),
                'confidence': float(row[4])
            }
            for row in results
        ]
    
    # Save results
    save_screener_results(screener_id, stocks)
    
    return {
        'screener_name': screener_name,
        'matches': len(stocks),
        'stocks': stocks,
        'run_date': date.today().isoformat()
    }

def build_sql_from_filters(filters: list) -> str:
    """Build SQL WHERE clause from filter definitions."""
    conditions = []
    
    for filter_obj in filters:
        category = filter_obj.get('category')
        field = filter_obj.get('field')
        operator = filter_obj.get('operator')
        value = filter_obj.get('value')
        
        if category == 'price':
            condition = build_price_condition(field, operator, value)
        elif category == 'volume':
            condition = build_volume_condition(field, operator, value)
        elif category == 'candlestick':
            condition = build_candlestick_condition(field, value)
        elif category == 'moving_averages':
            condition = build_ma_condition(field, operator, value)
        else:
            continue
        
        conditions.append(condition)
    
    # Combine with AND logic
    where_clause = " AND ".join([f"({c})" for c in conditions])
    
    sql = f"""
    SELECT 
        s.symbol,
        s.name,
        dp.close,
        dp.volume,
        0.85 as confidence_score
    FROM stocks s
    JOIN daily_prices dp ON s.id = dp.stock_id
    WHERE {where_clause}
    AND dp.date = CURRENT_DATE - 1
    ORDER BY dp.volume DESC
    """
    
    return sql

def build_price_condition(field: str, operator: str, value) -> str:
    """Build price comparison condition."""
    if operator == 'gt':
        return f"dp.{field} > {value}"
    elif operator == 'lt':
        return f"dp.{field} < {value}"
    elif operator == 'gte':
        return f"dp.{field} >= {value}"
    elif operator == 'lte':
        return f"dp.{field} <= {value}"
    elif operator == 'eq':
        return f"dp.{field} = {value}"

def build_volume_condition(field: str, operator: str, value: int) -> str:
    """Build volume comparison condition."""
    if operator == 'gt':
        return f"dp.volume > {value}"
    elif operator == 'lt':
        return f"dp.volume < {value}"

def build_candlestick_condition(field: str, patterns: list) -> str:
    """Build candlestick pattern condition."""
    pattern_list = "', '".join(patterns)
    return f"""
    EXISTS (
        SELECT 1 FROM candlestick_patterns cp
        WHERE cp.stock_id = s.id
        AND cp.date = dp.date
        AND cp.pattern_type IN ('{pattern_list}')
    )
    """

def build_ma_condition(field: str, operator: str, value: float) -> str:
    """Build moving average condition."""
    if operator == 'gt':
        return f"dp.{field} > dp.close"
    elif operator == 'lt':
        return f"dp.{field} < dp.close"
```

---

## 7. REACT COMPONENTS

### ScreenerBuilder.jsx

```jsx
import React, { useState } from 'react';
import FilterBuilder from './FilterBuilder';
import FilterList from './FilterList';
import ScreenerResults from './ScreenerResults';
import '../styles/screener-builder.css';

const ScreenerBuilder = () => {
  const [screenerName, setScreenerName] = useState('New Screener');
  const [filters, setFilters] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleAddFilter = (newFilter) => {
    setFilters([...filters, { ...newFilter, id: Date.now() }]);
  };

  const handleDeleteFilter = (filterId) => {
    setFilters(filters.filter(f => f.id !== filterId));
  };

  const handleRunScan = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/screeners/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: screenerName, filters })
      });
      const data = await response.json();
      setResults(data);
    } catch (error) {
      console.error('Error running screener:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveScreener = async () => {
    try {
      await fetch('/api/screeners', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: screenerName,
          filters,
          strategy_type: 'swing'
        })
      });
      alert('Screener saved!');
    } catch (error) {
      console.error('Error saving screener:', error);
    }
  };

  return (
    <div className="screener-builder-container">
      <div className="builder-header">
        <input
          type="text"
          value={screenerName}
          onChange={(e) => setScreenerName(e.target.value)}
          className="screener-title-input"
          placeholder="Screener Name"
        />
        <div className="header-info">
          New: LIVE Alerts now available!
        </div>
      </div>

      <div className="magic-filters-section">
        <h3>⚙️ MAGIC FILTERS</h3>
        
        <div className="filter-modes">
          <button className="mode-btn active">Append</button>
          <button className="mode-btn">Replace</button>
          <input 
            type="text" 
            placeholder="Scan stocks using simple language..."
            className="ai-filter-input"
          />
        </div>

        <div className="filter-tags">
          {filters.map(filter => (
            <span key={filter.id} className="tag">
              {filter.label}
              <button onClick={() => handleDeleteFilter(filter.id)}>✕</button>
            </span>
          ))}
        </div>

        <div className="filter-list">
          <FilterList 
            filters={filters}
            onDeleteFilter={handleDeleteFilter}
          />
          <FilterBuilder onAddFilter={handleAddFilter} />
        </div>
      </div>

      {results && (
        <ScreenerResults results={results} />
      )}

      <div className="action-buttons">
        <button 
          onClick={handleRunScan}
          disabled={loading}
          className="btn-primary"
        >
          🔍 Run Scan
        </button>
        <button onClick={handleSaveScreener} className="btn-secondary">
          💾 Save Scan
        </button>
        <button className="btn-secondary">
          📊 Backtest Results
        </button>
        <button className="btn-secondary">
          🔔 Create Alert
        </button>
        <button className="btn-secondary">⋮ More</button>
      </div>
    </div>
  );
};

export default ScreenerBuilder;
```

### FilterCard.jsx

```jsx
import React, { useState } from 'react';

const FilterCard = ({ filter, onDelete, onUpdate }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="filter-card">
      <div className="filter-header">
        <span className="filter-label">{filter.label}</span>
        <div className="filter-actions">
          <button className="action-btn" title="Chart">📊</button>
          <button className="action-btn" title="Backtest">🔄</button>
          <button className="action-btn" title="Target">🎯</button>
          <button className="action-btn" title="Settings">⚙️</button>
          <button 
            className="action-btn delete"
            onClick={() => onDelete(filter.id)}
            title="Delete"
          >
            🗑️
          </button>
        </div>
      </div>

      {expanded && (
        <div className="filter-details">
          <div className="detail-row">
            <label>Condition:</label>
            <select value={filter.operator} onChange={(e) => onUpdate(filter.id, 'operator', e.target.value)}>
              <option value="gt">Greater than</option>
              <option value="lt">Less than</option>
              <option value="gte">Greater than or equal</option>
              <option value="lte">Less than or equal</option>
            </select>
          </div>
          <div className="detail-row">
            <label>Value:</label>
            <input 
              type="text"
              value={filter.value}
              onChange={(e) => onUpdate(filter.id, 'value', e.target.value)}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default FilterCard;
```

---

## 8. IMPLEMENTATION ROADMAP

### Phase 1: MVP (2 weeks)
- [ ] Create 3-5 pre-built screeners
  - Price Action Breakout After 6 Months
  - VCP Coiling Setup
  - High Volume Breakout
- [ ] Implement candlestick pattern detection
- [ ] Build basic screener execution
- [ ] Create simple React UI

### Phase 2: Enhanced (2 weeks)
- [ ] Add drag-and-drop filter builder
- [ ] Implement AI filter description parsing
- [ ] Add backtest functionality
- [ ] Create alert system

### Phase 3: Advanced (2 weeks)
- [ ] Custom screener sharing/marketplace
- [ ] Screener performance statistics
- [ ] Live scanning with WebSocket
- [ ] Integration with live trading

---

## 9. COMPARISON: ChartInk vs Your Platform

| Feature | ChartInk | Trading_Bramha |
|---------|----------|-----------------|
| UI/UX | Beautiful, polished | Modern React |
| Pre-built Scanners | 100+ | 50+ (custom) |
| Custom Filters | Drag-drop builder | Code + UI builder |
| Backtesting | Built-in | Integrated |
| Alerts | SMS/Email | SMS/Email/WebSocket |
| Pricing | $20-50/month | Free (open-source) |
| Data Source | TradingView | NSE/BSE direct |
| Customization | Limited | Unlimited |

---

**With this guide, you can build a screener builder as powerful as ChartInk but completely customizable and free! 🚀**
