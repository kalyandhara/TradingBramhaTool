# SwingEdge-Style Scanner Dashboard Implementation Guide

*Building Pre-Built Pattern Scanners for Trading_Bramha*

---

## 1. DASHBOARD LAYOUT ANALYSIS

### SwingEdge UI Structure

```
┌─────────────────────────────────────────────────────────────┐
│ SwingEdge    Screener ▼  Sectors ▼  Tools ▼  More ▼    🔍   │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────┬─────────────────────────────────────┐
│    LEFT SIDEBAR         │       MAIN CONTENT AREA             │
│                         │                                     │
│ PRE-BUILT SCANNERS:     │ ┌─────────────────────────────────┐ │
│ • Custom Scanner        │ │ DARVAS BOX SCANNER              │ │
│ • Base Formation        │ │ Daily screens for validated...  │ │
│ • Momentum...           │ │ Last Updated: 23 Jun 2026       │ │
│ • Momentum Buildup      │ └─────────────────────────────────┘ │
│ • Downside Risk         │                                     │
│ • Darvas Box ✓          │ Recently Viewed:                    │
│ • Structural Breakout   │ [MIDHANI] [DHANBANK] [HSCL]...    │
│ • Rounding Bottom       │                                     │
│ • ETF Leaders           │ ┌─────────────────────────────────┐ │
│                         │ │ Watchlist Command Center        │ │
│ TODAY'S FOCUS:          │ │ ★ Star any card to save setup   │ │
│ • Near Pivot            │ └─────────────────────────────────┘ │
│ • VCP Coiling           │                                     │
│ • Pullback Entry        │ SCANNER RESULTS (Card Grid):       │
│ • 52-Week High Leaders  │                                     │
│ • Stage 2 Uptrend       │ ┌──────────┐ ┌──────────┐          │
│ • High RS               │ │SANSERA   │ │TALBROAUTO│          │
│                         │ │Fresh BO  │ │Fresh BO  │          │
│ BOARDS & WATCHLISTS:    │ │6.5% box  │ │7.4% box  │          │
│ • Today's Scanner...    │ │          │ │          │          │
│ • Scanner Results       │ │Why it's  │ │Why it's  │          │
│ • Community Watchlist   │ │interesting│ │interesting│         │
│ • ETF Rotation Board    │ │...       │ │...       │          │
│                         │ │[Analyze] │ │[Analyze] │          │
│                         │ └──────────┘ └──────────┘          │
│                         │                                     │
│                         │ ┌──────────┐ ┌──────────┐          │
│                         │ │CENTUM    │ │THYROCARE │          │
│                         │ │Inside box│ │Inside box│          │
│                         │ └──────────┘ └──────────┘          │
└─────────────────────────┴─────────────────────────────────────┘
```

---

## 2. PRE-BUILT SCANNER TYPES

### Category 1: BASE & FORMATION PATTERNS

#### **Darvas Box Scanner**
```json
{
  "id": "darvas_box",
  "name": "Darvas Box Scanner",
  "description": "Daily screens for stocks forming validated Darvas box structures",
  "pattern_type": "Consolidation/Breakout",
  "criteria": {
    "consolidation_range": "tight range with lower volatility",
    "box_confirmation": "52-week highs with controlled range",
    "breakout_readiness": "fresh close above box top",
    "overhead": "limited overhead resistance",
    "volume": "increasing on breakout"
  },
  "filters": [
    "RS rank >= 70",
    "Market cap >= 500 Cr",
    "Volume > 100K shares",
    "Price above key moving averages"
  ],
  "results_show": [
    "Box height %",
    "Current status (Fresh breakout, Inside box, etc)",
    "Number of boxes formed",
    "Entry point",
    "Target levels"
  ]
}
```

#### **Base Formation Scanner**
```json
{
  "id": "base_formation",
  "name": "Base Formation",
  "description": "Stocks building consolidation bases",
  "criteria": {
    "base_structure": "U-shaped or V-shaped formation",
    "duration": "4-12 weeks minimum",
    "pullback_pattern": "lower lows progressively less",
    "volume_pattern": "drying up at lows, expanding at highs"
  },
  "filters": [
    "Price above 200-day MA",
    "Base within 20% of all-time high"
  ]
}
```

### Category 2: MOMENTUM PATTERNS

#### **Momentum Continuation**
```json
{
  "id": "momentum_cont",
  "name": "Momentum Continuation",
  "description": "Stocks in strong uptrend momentum",
  "criteria": {
    "trend": "consistent higher highs, higher lows",
    "ma_alignment": "50 > 150 > 200 day moving averages",
    "rs_rating": "90+",
    "price_action": "closes near highs"
  }
}
```

#### **Momentum Buildup**
```json
{
  "id": "momentum_buildup",
  "name": "Momentum Buildup",
  "description": "Stocks building momentum before potential breakout",
  "criteria": {
    "rsi": "40-60 range (not overbought yet)",
    "macd": "positive and increasing",
    "volume": "gradually increasing",
    "range": "tightening consolidation"
  }
}
```

### Category 3: ADVANCED PATTERNS

#### **VCP Coiling** (Volatility Contraction Pattern)
```json
{
  "id": "vcp_coiling",
  "name": "VCP Coiling",
  "description": "Stocks with tight VCP consolidations ready to breakout",
  "criteria": {
    "consolidations": "3+ progressively tighter ranges",
    "contraction_ratio": "each range 70-90% of previous",
    "volume": "drying up significantly",
    "stage": "in established uptrend"
  }
}
```

#### **Pullback Entry**
```json
{
  "id": "pullback_entry",
  "name": "Pullback Entry",
  "description": "Quality stocks pulling back to support for entry",
  "criteria": {
    "pullback_size": "10-25% from recent high",
    "support": "bouncing at key moving average",
    "overall_trend": "still uptrending",
    "volume": "volume drying on pullback"
  }
}
```

#### **52-Week High Leaders**
```json
{
  "id": "52w_high_leaders",
  "name": "52-Week High Leaders",
  "description": "Strong momentum leaders near 52-week highs",
  "criteria": {
    "distance": "within 5% of 52-week high",
    "rs_rating": "90+",
    "earnings": "positive earnings growth",
    "trend": "Stage 2 or Stage 3 uptrend"
  }
}
```

#### **Stage 2 Uptrend**
```json
{
  "id": "stage2_uptrend",
  "name": "Stage 2 Uptrend",
  "description": "Stocks in middle of strong uptrends",
  "criteria": {
    "stage_analysis": "Stage 2 (base formation complete, trending)",
    "ma_alignment": "ascending moving averages",
    "price_position": "between 50-MA and previous high",
    "trend_strength": "accelerating moves"
  }
}
```

#### **High RS Leaders**
```json
{
  "id": "high_rs",
  "name": "High RS",
  "description": "Strongest performers outpacing the market",
  "criteria": {
    "rs_rating": "95+",
    "relative_strength": "outperforming Nifty 50",
    "market_cap": "all sizes",
    "sector": "leading sectors"
  }
}
```

#### **Structural Breakout**
```json
{
  "id": "structural_breakout",
  "name": "Structural Breakout",
  "description": "Stocks breaking above major resistance",
  "criteria": {
    "resistance": "breaking multi-month/year high",
    "volume": "expansion on breakout",
    "confirmation": "close above resistance, not just intraday",
    "prior_base": "solid base formation below"
  }
}
```

#### **Rounding Bottom**
```json
{
  "id": "rounding_bottom",
  "name": "Rounding Bottom",
  "description": "U-shaped bottoming patterns",
  "criteria": {
    "shape": "smooth U-shaped formation",
    "duration": "6-12+ weeks",
    "bottom": "clearly defined low point",
    "recovery": "steady rise from bottom"
  }
}
```

#### **Downside Risk**
```json
{
  "id": "downside_risk",
  "name": "Downside Risk",
  "description": "Stocks at risk of breaking down",
  "criteria": {
    "trend": "breaking below key moving averages",
    "support": "losing support levels",
    "rs": "deteriorating relative strength",
    "volume": "increasing volume on down moves"
  }
}
```

#### **ETF Leaders**
```json
{
  "id": "etf_leaders",
  "name": "ETF Leaders",
  "description": "Top stocks in leading ETF/sectors",
  "criteria": {
    "sector": "in strongest performing sectors",
    "holdings": "major holdings in leading ETFs",
    "momentum": "leading sector momentum"
  }
}
```

#### **Structural Breakout**
```json
{
  "id": "near_pivot",
  "name": "Near Pivot",
  "description": "Stocks near key pivot points",
  "criteria": {
    "pivot": "within 2-3% of identified pivot",
    "risk": "tight stop-loss opportunity",
    "reward": "clear upside target"
  }
}
```

---

## 3. RESULT CARD COMPONENT DESIGN

### Card Layout (Key Features)

```jsx
<ScannerResultCard>
  ┌─────────────────────────────────┐
  │ [S] SANSERA                 ★ ✕  │  // Stock initial, name, favorite, delete
  ├─────────────────────────────────┤
  │ Fresh breakout  6.5% box  1d box │  // Pattern tags with measurements
  ├─────────────────────────────────┤
  │                                  │
  │ WHY IT'S INTERESTING:            │
  │ ✓ RS rank 100 — leader          │  // Checkbox bullets with reasons
  │ ✓ Fresh close above box top      │
  │ ✓ Within 1.8% of 52-week highs  │
  │ ✓ Limited overhead              │
  │                                  │
  ├─────────────────────────────────┤
  │ [📊 Analyze Setup]   [★] [🗑️]  │  // Action buttons
  └─────────────────────────────────┘

Card Data Structure:
{
  symbol: "SANSERA",
  name: "Sansera Engineering",
  initials: "S",
  pattern: {
    type: "Fresh breakout",
    measurements: ["6.5% box", "1d box"]
  },
  reasons: [
    {icon: "✓", text: "RS rank 100 — leader behaviour fits Darvas momentum bias"},
    {icon: "✓", text: "Fresh close above box top — Darvas breakout registered"},
    {icon: "✓", text: "Within 1.8% of 52-week highs — limited overhead"},
    {icon: "✓", text: "Tight 8.8% box height — controlled pause characteristic"}
  ],
  status: "Fresh breakout",
  isSaved: false,
  actions: ["Analyze", "Favorite", "Delete"]
}
```

### Card Styling

```css
.scanner-card {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  min-width: 320px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  transition: all 0.3s ease;
}

.scanner-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  border-color: #6366f1;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.stock-initial {
  width: 40px;
  height: 40px;
  border-radius: 6px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-right: 12px;
}

.pattern-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.tag {
  background: #f0f4ff;
  color: #4f46e5;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.reasons-list {
  padding: 12px 0;
}

.reason-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 8px;
  font-size: 13px;
  line-height: 1.4;
  color: #555;
}

.reason-icon {
  color: #10b981;
  margin-right: 8px;
  font-weight: bold;
}

.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.analyze-btn {
  flex: 1;
  background: #6366f1;
  color: white;
  border: none;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
}

.action-icon-btn {
  width: 36px;
  height: 36px;
  border: 1px solid #e0e0e0;
  background: white;
  border-radius: 6px;
  cursor: pointer;
}
```

---

## 4. DATABASE SCHEMA FOR SCANNERS

```sql
-- Scanner Template Definitions
CREATE TABLE scanner_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(50),  -- 'pattern', 'momentum', 'technical'
    sql_query TEXT,  -- The actual screening query
    filters JSONB,  -- JSON array of filter criteria
    result_fields JSONB,  -- JSON array of fields to display in results
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scanner Results (cached daily)
CREATE TABLE scanner_results (
    id SERIAL PRIMARY KEY,
    scanner_id INTEGER REFERENCES scanner_templates(id),
    stock_id INTEGER REFERENCES stocks(id),
    result_date DATE,
    pattern_data JSONB,  -- Pattern details: type, measurements, confidence
    reasons JSONB,  -- Array of 'why it's interesting' bullets
    entry_point DECIMAL(10, 2),
    target_price DECIMAL(10, 2),
    stop_loss DECIMAL(10, 2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(scanner_id, stock_id, result_date)
);

-- User Saved Scanner Results (Watchlist)
CREATE TABLE user_saved_scanners (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    result_id INTEGER REFERENCES scanner_results(id),
    notes TEXT,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scanner Performance Tracking
CREATE TABLE scanner_performance (
    id SERIAL PRIMARY KEY,
    scanner_id INTEGER REFERENCES scanner_templates(id),
    result_id INTEGER REFERENCES scanner_results(id),
    entry_price DECIMAL(10, 2),
    exit_price DECIMAL(10, 2),
    exit_date DATE,
    profit_loss DECIMAL(10, 2),
    win BOOLEAN,
    hold_days INTEGER
);

CREATE INDEX idx_scanner_results_date ON scanner_results(result_date DESC);
CREATE INDEX idx_scanner_results_active ON scanner_results(is_active);
CREATE INDEX idx_user_saved ON user_saved_scanners(user_id);
```

---

## 5. BACKEND API FOR SCANNERS

### FastAPI Endpoints

```python
from fastapi import FastAPI, Query
from datetime import date

app = FastAPI()

@app.get("/api/scanners")
async def list_all_scanners():
    """Get all available scanner templates."""
    with engine.connect() as conn:
        query = """
        SELECT id, name, description, category 
        FROM scanner_templates 
        ORDER BY category, name
        """
        result = conn.execute(query)
        scanners = [
            {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'category': row[3]
            }
            for row in result
        ]
    
    # Group by category
    grouped = {}
    for scanner in scanners:
        cat = scanner['category']
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(scanner)
    
    return grouped

@app.get("/api/scanners/{scanner_id}/results")
async def get_scanner_results(
    scanner_id: int,
    limit: int = Query(50, le=500),
    sort_by: str = "entry_point"
):
    """Get results for a specific scanner."""
    with engine.connect() as conn:
        query = f"""
        SELECT 
            sr.id,
            s.symbol,
            s.name,
            sr.pattern_data,
            sr.reasons,
            sr.entry_point,
            sr.target_price,
            sr.stop_loss,
            sr.result_date
        FROM scanner_results sr
        JOIN stocks s ON sr.stock_id = s.id
        WHERE sr.scanner_id = {scanner_id}
        AND sr.result_date = (SELECT MAX(result_date) FROM scanner_results WHERE scanner_id = {scanner_id})
        AND sr.is_active = TRUE
        ORDER BY sr.{sort_by} DESC
        LIMIT {limit}
        """
        
        result = conn.execute(query)
        results = [
            {
                'id': row[0],
                'symbol': row[1],
                'name': row[2],
                'pattern': json.loads(row[3]),
                'reasons': json.loads(row[4]),
                'entry_point': float(row[5]) if row[5] else None,
                'target_price': float(row[6]) if row[6] else None,
                'stop_loss': float(row[7]) if row[7] else None,
                'result_date': str(row[8])
            }
            for row in result
        ]
    
    return {'data': results, 'count': len(results)}

@app.post("/api/scanners/{result_id}/save")
async def save_scanner_result(
    result_id: int,
    user_id: int,
    notes: str = None
):
    """Save a scanner result to user's watchlist."""
    with engine.connect() as conn:
        insert_stmt = f"""
        INSERT INTO user_saved_scanners (user_id, result_id, notes)
        VALUES ({user_id}, {result_id}, '{notes}')
        ON CONFLICT DO NOTHING
        """
        conn.execute(insert_stmt)
        conn.commit()
    
    return {'status': 'saved'}

@app.get("/api/scanners/{scanner_id}/performance")
async def get_scanner_performance(scanner_id: int):
    """Get win rate and performance stats for a scanner."""
    with engine.connect() as conn:
        query = f"""
        SELECT 
            COUNT(*) as total_results,
            COUNT(CASE WHEN win = TRUE THEN 1 END) as wins,
            AVG(profit_loss) as avg_profit,
            MAX(profit_loss) as best_trade,
            MIN(profit_loss) as worst_trade,
            AVG(hold_days) as avg_hold_days
        FROM scanner_performance
        WHERE scanner_id = {scanner_id}
        AND exit_date IS NOT NULL
        """
        
        result = conn.execute(query).fetchone()
        total = result[0] or 0
        wins = result[1] or 0
        
        return {
            'total_results': total,
            'wins': wins,
            'win_rate': (wins / total * 100) if total > 0 else 0,
            'avg_profit': float(result[2]) if result[2] else 0,
            'best_trade': float(result[3]) if result[3] else 0,
            'worst_trade': float(result[4]) if result[4] else 0,
            'avg_hold_days': int(result[5]) if result[5] else 0
        }
```

---

## 6. DAILY SCANNER JOB EXECUTION

### Automated Scanner Run

```python
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import date
import json

scheduler = BackgroundScheduler()

@scheduler.scheduled_job('cron', hour=17, minute=0)  # After market close
def run_all_scanners():
    """Execute all scanner templates and store results."""
    
    with engine.connect() as conn:
        # Get all scanner templates
        templates = conn.execute(
            "SELECT id, name, sql_query FROM scanner_templates"
        ).fetchall()
        
        for template_id, template_name, sql_query in templates:
            try:
                print(f"Running scanner: {template_name}")
                
                # Execute the scanner's SQL query
                result = conn.execute(sql_query)
                rows = result.fetchall()
                
                # Process results
                for row in rows:
                    stock_id = row[0]
                    symbol = row[1]
                    pattern_data = row[2]  # JSON
                    reasons = row[3]  # JSON
                    entry = row[4]
                    target = row[5]
                    stop = row[6]
                    
                    # Insert into scanner_results
                    insert_query = f"""
                    INSERT INTO scanner_results 
                    (scanner_id, stock_id, result_date, pattern_data, reasons, 
                     entry_point, target_price, stop_loss)
                    VALUES 
                    ({template_id}, {stock_id}, '{date.today()}', 
                     '{json.dumps(pattern_data)}', '{json.dumps(reasons)}',
                     {entry}, {target}, {stop})
                    ON CONFLICT (scanner_id, stock_id, result_date) 
                    DO UPDATE SET pattern_data = EXCLUDED.pattern_data
                    """
                    conn.execute(insert_query)
                
                conn.commit()
                print(f"✓ {template_name}: {len(rows)} results")
                
            except Exception as e:
                print(f"✗ Error running {template_name}: {e}")
                conn.rollback()

scheduler.start()
```

### Example Scanner Query (Darvas Box)

```python
"""
Darvas Box Scanner SQL Query
"""
DARVAS_BOX_QUERY = """
SELECT 
    s.id,
    s.symbol,
    json_build_object(
        'type', 'Fresh breakout',
        'box_height', ROUND((dp.high - dp.low) / dp.low * 100, 2),
        'status', CASE 
            WHEN dp.close > (52w_high - (52w_high * 0.01)) THEN 'Fresh breakout'
            WHEN dp.close > dp.low AND dp.close < dp.high * 0.95 THEN 'Inside box'
            ELSE 'Forming'
        END
    ) as pattern_data,
    json_build_array(
        json_build_object('text', 'RS rank ' || i.rs_rating || ' — leader behaviour fits Darvas'),
        json_build_object('text', 'Fresh close above box top — Darvas breakout registered'),
        json_build_object('text', 'Limited overhead resistance'),
        json_build_object('text', 'Tight consolidation range')
    ) as reasons,
    dp.close as entry_point,
    ROUND(dp.high * 1.15, 2) as target_price,
    ROUND(dp.low * 0.98, 2) as stop_loss

FROM stocks s
JOIN daily_prices dp ON s.id = dp.stock_id
JOIN indicators i ON s.id = i.stock_id AND i.date = dp.date
JOIN (
    SELECT stock_id, MAX(high) as 52w_high, MIN(low) as 52w_low
    FROM daily_prices
    WHERE date >= CURRENT_DATE - INTERVAL '52 weeks'
    GROUP BY stock_id
) wk52 ON s.id = wk52.stock_id

WHERE dp.date = CURRENT_DATE - 1
AND i.rs_rating >= 70
AND dp.close > i.ma50
AND i.ma50 > i.ma150 AND i.ma150 > i.ma200
AND dp.volume > (SELECT AVG(volume) FROM daily_prices WHERE stock_id = s.id AND date >= CURRENT_DATE - 20)
AND s.market_cap > 500000000  -- 500 Cr+
ORDER BY i.rs_rating DESC
"""
```

---

## 7. REACT FRONTEND COMPONENTS

### Main Scanner Page

```jsx
import React, { useState, useEffect } from 'react';
import ScannerSidebar from './ScannerSidebar';
import ScannerResults from './ScannerResults';

const ScannerDashboard = () => {
  const [scanners, setScanners] = useState([]);
  const [selectedScanner, setSelectedScanner] = useState(null);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Fetch all scanners on mount
    fetch('/api/scanners')
      .then(res => res.json())
      .then(data => setScanners(data));
  }, []);

  const handleSelectScanner = (scannerId) => {
    setSelectedScanner(scannerId);
    setLoading(true);
    
    // Fetch results for selected scanner
    fetch(`/api/scanners/${scannerId}/results?limit=50`)
      .then(res => res.json())
      .then(data => {
        setResults(data.data);
        setLoading(false);
      });
  };

  return (
    <div className="scanner-dashboard">
      <ScannerSidebar 
        scanners={scanners}
        selectedScanner={selectedScanner}
        onSelectScanner={handleSelectScanner}
      />
      
      <div className="scanner-main">
        {selectedScanner && !loading && (
          <ScannerResults results={results} />
        )}
        {loading && <div>Loading...</div>}
      </div>
    </div>
  );
};

export default ScannerDashboard;
```

### Scanner Sidebar

```jsx
const ScannerSidebar = ({ scanners, selectedScanner, onSelectScanner }) => {
  return (
    <div className="scanner-sidebar">
      <div className="sidebar-section">
        <h3>PRE-BUILT SCANNERS</h3>
        {scanners.pattern && scanners.pattern.map(scanner => (
          <div
            key={scanner.id}
            className={`scanner-item ${selectedScanner === scanner.id ? 'active' : ''}`}
            onClick={() => onSelectScanner(scanner.id)}
          >
            <span className="scanner-icon">◆</span>
            {scanner.name}
          </div>
        ))}
      </div>

      <div className="sidebar-section">
        <h3>TODAY'S FOCUS</h3>
        {scanners.technical && scanners.technical.map(scanner => (
          <div
            key={scanner.id}
            className="scanner-item"
            onClick={() => onSelectScanner(scanner.id)}
          >
            <span className="scanner-icon">•</span>
            {scanner.name}
          </div>
        ))}
      </div>

      <div className="sidebar-section">
        <h3>BOARDS & WATCHLISTS</h3>
        <div className="scanner-item">📊 Today's Scanner Movers</div>
        <div className="scanner-item">📋 Scanner Results</div>
        <div className="scanner-item">👥 Community Watchlist</div>
      </div>
    </div>
  );
};
```

### Scanner Results Grid

```jsx
const ScannerResults = ({ results }) => {
  return (
    <div className="scanner-results">
      <div className="results-header">
        <h2>Scanner Results</h2>
        <span className="result-count">{results.length} stocks found</span>
      </div>

      <div className="results-grid">
        {results.map(result => (
          <ScannerResultCard key={result.id} result={result} />
        ))}
      </div>
    </div>
  );
};

const ScannerResultCard = ({ result }) => {
  const [isSaved, setIsSaved] = useState(false);

  const handleSave = () => {
    fetch(`/api/scanners/${result.id}/save`, {
      method: 'POST',
      body: JSON.stringify({ user_id: 1 })
    }).then(() => setIsSaved(true));
  };

  return (
    <div className="scanner-card">
      <div className="card-header">
        <div className="stock-info">
          <div className="stock-initial">
            {result.symbol.charAt(0)}
          </div>
          <div>
            <div className="stock-name">{result.symbol}</div>
            <div className="stock-company">{result.name}</div>
          </div>
        </div>
        <button 
          className={`save-btn ${isSaved ? 'saved' : ''}`}
          onClick={handleSave}
        >
          ★
        </button>
      </div>

      <div className="pattern-tags">
        <span className="tag">{result.pattern.type}</span>
        {result.pattern.measurements?.map((m, i) => (
          <span key={i} className="tag">{m}</span>
        ))}
      </div>

      <div className="card-section">
        <h4>WHY IT'S INTERESTING:</h4>
        <ul className="reasons-list">
          {result.reasons.map((reason, i) => (
            <li key={i}>
              <span className="reason-icon">✓</span>
              {reason.text}
            </li>
          ))}
        </ul>
      </div>

      <div className="card-actions">
        <button className="analyze-btn">📊 Analyze Setup</button>
        <button className="action-btn">★</button>
        <button className="action-btn">🗑️</button>
      </div>
    </div>
  );
};
```

---

## 8. IMPLEMENTATION ROADMAP

### Phase 1: Core Scanner Infrastructure
- [ ] Create 5 most popular scanners (Darvas, VCP, Momentum, etc.)
- [ ] Implement scanner template engine
- [ ] Build daily batch job system
- [ ] Create React sidebar + grid layout

### Phase 2: Enhanced Scanner Features
- [ ] Add 5 more scanner templates
- [ ] Implement scanner performance tracking
- [ ] Add save/star functionality
- [ ] Create scanner results history

### Phase 3: Advanced Analytics
- [ ] Scanner performance statistics
- [ ] Win rate and profit factor calculation
- [ ] Scanner comparison view
- [ ] Custom scanner builder

---

## 9. KEY DIFFERENCES FROM MINERVINI GUIDE

| Aspect | Minervini Guide | SwingEdge Scanner |
|--------|----------------|--------------------|
| **Focus** | VCP pattern only | 10+ pattern types |
| **Presentation** | List/table view | Card grid layout |
| **Discovery** | Manual screening | Pre-built templates |
| **Ease of Use** | Learn the rules | Click and results |
| **Customization** | Build own criteria | Use templates |

---

## 10. SAMPLE SCANNER DEFINITIONS

Save these as SQL inserts into `scanner_templates`:

```sql
INSERT INTO scanner_templates (name, description, category) VALUES
('Darvas Box Scanner', 'Validated Darvas box structures with limited overhead', 'pattern'),
('Base Formation', 'Consolidation bases after major declines', 'pattern'),
('Momentum Continuation', 'Strong uptrend continuation setups', 'momentum'),
('Momentum Buildup', 'Momentum accumulation before breakouts', 'momentum'),
('VCP Coiling', 'Volatility contraction patterns ready to pop', 'pattern'),
('Pullback Entry', 'Quality stocks pulling back to support', 'technical'),
('52-Week High Leaders', 'Momentum leaders near 52-week highs', 'momentum'),
('Stage 2 Uptrend', 'Stocks in middle of strong uptrends', 'technical'),
('High RS Leaders', 'Strongest performers outpacing market', 'momentum'),
('Structural Breakout', 'Breaking above major resistance levels', 'pattern'),
('Rounding Bottom', 'U-shaped bottoming patterns', 'pattern'),
('Near Pivot', 'Stocks near key pivot points', 'technical');
```

---

**This design brings the discovery and ease-of-use of SwingEdge to your Trading_Bramha project while maintaining the strategic depth of Minervini's methodology.**
