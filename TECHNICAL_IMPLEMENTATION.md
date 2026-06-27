# Technical Implementation Guide - VCP Pattern Detection & Dashboard

---

## 1. VCP PATTERN DETECTION ALGORITHM (Python)

### Basic VCP Detector Implementation

```python
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class VCPPattern:
    symbol: str
    start_date: str
    end_date: str
    contractions: int
    pivot_high: float
    pivot_low: float
    breakout_volume_avg: float
    recent_volume: float
    stage: str  # 'forming', 'complete', 'breakout'

class VCPDetector:
    def __init__(self, min_contractions=3, contraction_ratio=0.8):
        """
        min_contractions: Minimum number of contractions required (usually 3-4)
        contraction_ratio: Each contraction should be 0.7-0.9 of previous range
        """
        self.min_contractions = min_contractions
        self.contraction_ratio = contraction_ratio
    
    def detect_consolidations(self, df: pd.DataFrame) -> List[tuple]:
        """
        Find potential consolidation zones (low volatility areas).
        Returns list of (start_idx, end_idx, range_size) tuples
        """
        df['range'] = df['high'] - df['low']
        df['atr'] = self._calculate_atr(df, period=14)
        
        consolidations = []
        min_length = 5  # Min bars in consolidation
        threshold = df['atr'].rolling(20).mean() * 0.7  # Lower than average ATR
        
        i = 0
        while i < len(df):
            if df['atr'].iloc[i] < threshold.iloc[i]:
                start = i
                while i < len(df) and df['atr'].iloc[i] < threshold.iloc[i]:
                    i += 1
                
                if i - start >= min_length:
                    range_size = df['high'].iloc[start:i].max() - df['low'].iloc[start:i].min()
                    consolidations.append((start, i, range_size))
            else:
                i += 1
        
        return consolidations
    
    def is_vcp_pattern(self, df: pd.DataFrame, start_idx: int, end_idx: int) -> bool:
        """
        Check if consolidation between start_idx and end_idx is a VCP pattern.
        """
        # Extract segment
        segment = df.iloc[start_idx:end_idx]
        
        if len(segment) < self.min_contractions * 3:
            return False
        
        # Find pullbacks and rallies
        contractions = self._find_contractions(segment)
        
        if len(contractions) < self.min_contractions:
            return False
        
        # Check if each contraction is smaller than previous
        for i in range(1, len(contractions)):
            curr_range = contractions[i][1] - contractions[i][0]
            prev_range = contractions[i-1][1] - contractions[i-1][0]
            
            ratio = curr_range / prev_range if prev_range > 0 else 1
            if ratio > 1.0 or ratio < self.contraction_ratio:
                return False
        
        # Check volume pattern: lower on pullbacks, higher on rallies
        if not self._check_volume_pattern(segment, contractions):
            return False
        
        return True
    
    def _find_contractions(self, df: pd.DataFrame) -> List[tuple]:
        """Identify individual pullback zones within a consolidation."""
        contractions = []
        # Simple approach: find local lows and highs
        for i in range(1, len(df) - 1):
            if df['low'].iloc[i] < df['low'].iloc[i-1] and df['low'].iloc[i] < df['low'].iloc[i+1]:
                # Local low found
                contractions.append((df['low'].iloc[i], df['high'].iloc[i]))
        
        return contractions
    
    def _check_volume_pattern(self, df: pd.DataFrame, contractions: List[tuple]) -> bool:
        """Check if volume decreases on pullbacks and increases on rallies."""
        if len(df) < 10:
            return False
        
        avg_vol = df['volume'].mean()
        recent_vol = df['volume'].tail(5).mean()
        
        # Recent volume should be near or above average (potential breakout building)
        return recent_vol >= avg_vol * 0.8
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                np.abs(df['high'] - df['close'].shift()),
                np.abs(df['low'] - df['close'].shift())
            )
        )
        return df['tr'].rolling(period).mean()
    
    def get_entry_points(self, df: pd.DataFrame) -> List[VCPPattern]:
        """
        Scan dataframe for all VCP patterns and return entry opportunities.
        """
        patterns = []
        consolidations = self.detect_consolidations(df)
        
        for start_idx, end_idx, range_size in consolidations:
            if self.is_vcp_pattern(df, start_idx, end_idx):
                pivot_high = df['high'].iloc[start_idx:end_idx].max()
                pivot_low = df['low'].iloc[start_idx:end_idx].min()
                
                pattern = VCPPattern(
                    symbol=df['symbol'].iloc[0] if 'symbol' in df.columns else 'UNKNOWN',
                    start_date=str(df.index[start_idx]),
                    end_date=str(df.index[end_idx]),
                    contractions=self._count_contractions(df.iloc[start_idx:end_idx]),
                    pivot_high=pivot_high,
                    pivot_low=pivot_low,
                    breakout_volume_avg=df['volume'].iloc[start_idx:end_idx].mean(),
                    recent_volume=df['volume'].iloc[-5:].mean(),
                    stage='complete'
                )
                patterns.append(pattern)
        
        return patterns
    
    def _count_contractions(self, df: pd.DataFrame) -> int:
        """Count number of distinct contractions."""
        contractions = self._find_contractions(df)
        return len(contractions)
```

---

## 2. DATABASE SCHEMA (PostgreSQL)

### Core Tables

```sql
-- Stocks table
CREATE TABLE stocks (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    sector VARCHAR(50),
    market_cap BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Daily price data
CREATE TABLE daily_prices (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    date DATE NOT NULL,
    open DECIMAL(10, 2),
    high DECIMAL(10, 2),
    low DECIMAL(10, 2),
    close DECIMAL(10, 2),
    volume BIGINT,
    UNIQUE(stock_id, date)
);

-- Technical indicators (cached for fast retrieval)
CREATE TABLE indicators (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    date DATE NOT NULL,
    ma50 DECIMAL(10, 2),
    ma150 DECIMAL(10, 2),
    ma200 DECIMAL(10, 2),
    rs_rating DECIMAL(5, 2),
    atr14 DECIMAL(10, 2),
    UNIQUE(stock_id, date)
);

-- VCP Pattern Detection
CREATE TABLE vcp_patterns (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    pattern_start_date DATE,
    pattern_end_date DATE,
    pivot_high DECIMAL(10, 2),
    pivot_low DECIMAL(10, 2),
    num_contractions INTEGER,
    status VARCHAR(20),  -- 'forming', 'complete', 'breakout'
    breakout_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User portfolio
CREATE TABLE portfolios (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    stock_id INTEGER REFERENCES stocks(id),
    entry_price DECIMAL(10, 2),
    quantity INTEGER,
    entry_date DATE,
    stop_loss DECIMAL(10, 2),
    target_price DECIMAL(10, 2),
    exit_price DECIMAL(10, 2),
    exit_date DATE,
    status VARCHAR(20)  -- 'open', 'closed', 'stopped_out'
);

-- Price alerts
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    stock_id INTEGER REFERENCES stocks(id),
    alert_type VARCHAR(50),  -- 'price', 'vcp_pattern', 'volume'
    price_level DECIMAL(10, 2),
    condition VARCHAR(20),  -- 'above', 'below'
    is_active BOOLEAN DEFAULT TRUE,
    triggered_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for fast queries
CREATE INDEX idx_daily_prices_stock_date ON daily_prices(stock_id, date DESC);
CREATE INDEX idx_indicators_stock_date ON indicators(stock_id, date DESC);
CREATE INDEX idx_vcp_status ON vcp_patterns(status, created_at DESC);
```

---

## 3. BACKEND API (FastAPI with Python)

### Stock Screener Endpoint

```python
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, desc
import pandas as pd
from typing import List, Optional

app = FastAPI()

# Database setup
DATABASE_URL = "postgresql://user:password@localhost/trading_bramha"
engine = create_engine(DATABASE_URL)

@app.get("/api/screener/vcp")
async def get_vcp_patterns(
    sort_by: str = "pivot_high",
    limit: int = Query(50, le=500)
):
    """
    Screen for stocks with complete VCP patterns ready for breakout.
    """
    with engine.connect() as conn:
        query = """
        SELECT 
            s.symbol,
            s.name,
            s.sector,
            vcp.pivot_high,
            vcp.pivot_low,
            vcp.num_contractions,
            dp.close,
            dp.volume,
            i.rs_rating,
            i.ma50,
            i.ma150,
            i.ma200
        FROM vcp_patterns vcp
        JOIN stocks s ON vcp.stock_id = s.id
        JOIN daily_prices dp ON s.id = dp.stock_id AND dp.date = vcp.pattern_end_date
        JOIN indicators i ON s.id = i.stock_id AND i.date = dp.date
        WHERE vcp.status = 'complete'
        AND i.rs_rating >= 70
        AND dp.close > i.ma50
        AND i.ma50 > i.ma150 AND i.ma150 > i.ma200
        ORDER BY {sort_by} DESC
        LIMIT {limit}
        """.format(sort_by=sort_by, limit=limit)
        
        result = conn.execute(query)
        columns = [col.name for col in result.keys()]
        data = [dict(zip(columns, row)) for row in result]
    
    return {"data": data, "count": len(data)}

@app.get("/api/stock/{symbol}/analysis")
async def get_stock_analysis(symbol: str):
    """
    Get detailed analysis for a specific stock including:
    - VCP pattern status
    - Technical indicators
    - Recent price action
    - Entry/exit recommendations
    """
    with engine.connect() as conn:
        # Get last 100 days of price data
        query = """
        SELECT 
            dp.date,
            dp.open,
            dp.high,
            dp.low,
            dp.close,
            dp.volume,
            i.ma50,
            i.ma150,
            i.ma200,
            i.rs_rating
        FROM daily_prices dp
        LEFT JOIN indicators i ON dp.stock_id = i.stock_id AND dp.date = i.date
        WHERE dp.stock_id = (SELECT id FROM stocks WHERE symbol = %s)
        ORDER BY dp.date DESC
        LIMIT 100
        """
        
        result = conn.execute(query, (symbol,))
        df = pd.DataFrame(result.fetchall())
        
        if df.empty:
            raise HTTPException(status_code=404, detail="Stock not found")
        
        # Detect VCP pattern on this data
        detector = VCPDetector()
        df['high'] = df[2]
        df['low'] = df[3]
        df['close'] = df[4]
        df['volume'] = df[5]
        
        patterns = detector.get_entry_points(df)
    
    return {
        "symbol": symbol,
        "current_price": float(df[4].iloc[0]),
        "vcp_patterns": [vars(p) for p in patterns],
        "indicators": {
            "rs_rating": float(df[9].iloc[0]) if pd.notna(df[9].iloc[0]) else None,
            "ma50": float(df[6].iloc[0]) if pd.notna(df[6].iloc[0]) else None,
            "ma150": float(df[7].iloc[0]) if pd.notna(df[7].iloc[0]) else None,
            "ma200": float(df[8].iloc[0]) if pd.notna(df[8].iloc[0]) else None,
        }
    }
```

---

## 4. FRONTEND COMPONENTS (React)

### Stock Chart with VCP Visualization

```jsx
import React, { useEffect, useState } from 'react';
import { createChart } from 'lightweight-charts';

const StockChart = ({ symbol, patterns }) => {
  const chartContainerRef = React.useRef();
  const [chart, setChart] = useState(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: '#1e1e1e' },
        textColor: '#d1d5db',
      },
      width: chartContainerRef.current.clientWidth,
      height: 500,
    });

    // Candlestick series
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
    });

    // Fetch price data
    fetch(`/api/stock/${symbol}/prices`)
      .then(res => res.json())
      .then(data => {
        candleSeries.setData(data.candles);

        // Draw VCP zones
        patterns.forEach(pattern => {
          const logicalRange = {
            from: new Date(pattern.start_date).getTime() / 1000,
            to: new Date(pattern.end_date).getTime() / 1000,
          };

          // Draw rectangle for consolidation zone
          const priceLevelLow = {
            price: pattern.pivot_low,
            color: '#ffd700',
            lineStyle: 2,
          };

          const priceLevelHigh = {
            price: pattern.pivot_high,
            color: '#ffd700',
            lineStyle: 2,
          };

          // Add price lines
          candleSeries.createPriceLine(priceLevelLow);
          candleSeries.createPriceLine(priceLevelHigh);
        });

        chart.timeScale().fitContent();
      });

    setChart(chart);

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [symbol, patterns]);

  return <div ref={chartContainerRef} style={{ width: '100%' }} />;
};

export default StockChart;
```

### Stock Screener Table

```jsx
import React, { useState, useEffect } from 'react';

const StockScreener = () => {
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState('pivot_high');

  useEffect(() => {
    fetch(`/api/screener/vcp?sort_by=${sortBy}`)
      .then(res => res.json())
      .then(data => {
        setStocks(data.data);
        setLoading(false);
      });
  }, [sortBy]);

  return (
    <div className="screener-container">
      <h2>VCP Pattern Screener</h2>
      
      <table className="stock-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Name</th>
            <th>Sector</th>
            <th>Current Price</th>
            <th>Pivot High</th>
            <th>Contractions</th>
            <th>RS Rating</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {stocks.map(stock => (
            <tr key={stock.symbol}>
              <td className="symbol-col">{stock.symbol}</td>
              <td>{stock.name}</td>
              <td>{stock.sector}</td>
              <td>{stock.close?.toFixed(2)}</td>
              <td className="pivot-high">{stock.pivot_high?.toFixed(2)}</td>
              <td>{stock.num_contractions}</td>
              <td className={`rs-rating ${stock.rs_rating >= 90 ? 'excellent' : 'good'}`}>
                {stock.rs_rating?.toFixed(1)}
              </td>
              <td>
                <button onClick={() => viewChart(stock.symbol)}>
                  View Chart
                </button>
                <button onClick={() => addToWatchlist(stock.symbol)}>
                  Add Alert
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default StockScreener;
```

---

## 5. DAILY DATA UPDATE PIPELINE

### Scheduled Data Ingestion (APScheduler)

```python
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import yfinance as yf
import pandas as pd
from sqlalchemy import insert

scheduler = BackgroundScheduler()

@scheduler.scheduled_job('cron', hour=16, minute=30)  # After market close (4:30 PM IST)
def update_daily_prices():
    """Fetch and store daily price data for all stocks."""
    with engine.connect() as conn:
        # Get all stocks
        stocks_query = "SELECT id, symbol FROM stocks"
        stocks = conn.execute(stocks_query).fetchall()
        
        for stock_id, symbol in stocks:
            try:
                # Fetch data from yfinance
                df = yf.download(f'{symbol}.NS', period='1d')  # NSE suffix for India
                
                # Prepare data for insert
                data = {
                    'stock_id': stock_id,
                    'date': df.index[0].date(),
                    'open': df['Open'].iloc[0],
                    'high': df['High'].iloc[0],
                    'low': df['Low'].iloc[0],
                    'close': df['Close'].iloc[0],
                    'volume': df['Volume'].iloc[0]
                }
                
                # Insert or update
                insert_stmt = insert(daily_prices).values(data).on_conflict_do_update(
                    index_elements=['stock_id', 'date'],
                    set_=data
                )
                conn.execute(insert_stmt)
                
            except Exception as e:
                print(f"Error updating {symbol}: {e}")
        
        conn.commit()

@scheduler.scheduled_job('cron', hour=17, minute=0)  # After prices updated
def calculate_indicators():
    """Calculate technical indicators for all stocks."""
    with engine.connect() as conn:
        stocks = conn.execute("SELECT id FROM stocks").fetchall()
        
        for (stock_id,) in stocks:
            # Get last 200 days of price data
            prices_df = pd.read_sql(
                f"""SELECT date, close FROM daily_prices 
                   WHERE stock_id = {stock_id} 
                   ORDER BY date DESC LIMIT 200""",
                engine
            )
            
            if len(prices_df) >= 200:
                prices_df['ma50'] = prices_df['close'].rolling(50).mean()
                prices_df['ma150'] = prices_df['close'].rolling(150).mean()
                prices_df['ma200'] = prices_df['close'].rolling(200).mean()
                
                # Calculate RS rating (simple version)
                high_52w = prices_df['close'].max()
                low_52w = prices_df['close'].min()
                current = prices_df['close'].iloc[0]
                rs_rating = ((high_52w - current) / (high_52w - low_52w)) * 100
                
                # Insert indicators
                indicator_data = {
                    'stock_id': stock_id,
                    'date': prices_df['date'].iloc[0],
                    'ma50': prices_df['ma50'].iloc[0],
                    'ma150': prices_df['ma150'].iloc[0],
                    'ma200': prices_df['ma200'].iloc[0],
                    'rs_rating': rs_rating
                }
                
                insert_stmt = insert(indicators).values(indicator_data).on_conflict_do_update(
                    index_elements=['stock_id', 'date'],
                    set_=indicator_data
                )
                conn.execute(insert_stmt)
        
        conn.commit()

@scheduler.scheduled_job('cron', hour=17, minute=30)
def detect_vcp_patterns():
    """Run VCP pattern detection on all stocks."""
    detector = VCPDetector()
    
    with engine.connect() as conn:
        stocks = conn.execute("SELECT id, symbol FROM stocks").fetchall()
        
        for stock_id, symbol in stocks:
            # Get 100 days of price data
            prices_df = pd.read_sql(
                f"""SELECT date, open, high, low, close, volume 
                   FROM daily_prices 
                   WHERE stock_id = {stock_id} 
                   ORDER BY date DESC LIMIT 100""",
                engine
            )
            
            if len(prices_df) >= 20:
                patterns = detector.get_entry_points(prices_df)
                
                for pattern in patterns:
                    pattern_data = {
                        'stock_id': stock_id,
                        'pattern_start_date': pattern.start_date,
                        'pattern_end_date': pattern.end_date,
                        'pivot_high': pattern.pivot_high,
                        'pivot_low': pattern.pivot_low,
                        'num_contractions': pattern.contractions,
                        'status': pattern.stage
                    }
                    
                    # Insert if not exists
                    insert_stmt = insert(vcp_patterns).values(pattern_data).on_conflict_do_nothing()
                    conn.execute(insert_stmt)
        
        conn.commit()

# Start scheduler
if __name__ == '__main__':
    scheduler.start()
```

---

## 6. REAL-TIME ALERTS (WebSocket)

### Alert Service with WebSocket

```python
from fastapi import WebSocket
import asyncio
import json
from datetime import datetime

class AlertManager:
    def __init__(self):
        self.active_connections = {}
        self.price_alerts = {}  # {symbol: [alerts]}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        self.active_connections[user_id].remove(websocket)
    
    async def broadcast_alert(self, alert_data: dict):
        """Broadcast alert to all connected users with relevant alerts."""
        symbol = alert_data.get('symbol')
        message = json.dumps(alert_data)
        
        # Check all active connections for subscribed alerts
        for user_id, connections in self.active_connections.items():
            if symbol in self.price_alerts.get(user_id, {}):
                for connection in connections:
                    try:
                        await connection.send_text(message)
                    except Exception as e:
                        print(f"Error sending alert: {e}")
    
    async def check_price_alerts(self, symbol: str, price: float):
        """Check if any price alerts should be triggered."""
        with engine.connect() as conn:
            alerts = conn.execute(
                f"""SELECT id, user_id, price_level, condition 
                   FROM alerts 
                   WHERE stock_id = (SELECT id FROM stocks WHERE symbol = %s)
                   AND is_active = TRUE""",
                (symbol,)
            ).fetchall()
            
            for alert_id, user_id, price_level, condition in alerts:
                triggered = False
                
                if condition == 'above' and price > price_level:
                    triggered = True
                elif condition == 'below' and price < price_level:
                    triggered = True
                
                if triggered:
                    await self.broadcast_alert({
                        'type': 'price_alert',
                        'symbol': symbol,
                        'price': price,
                        'alert_id': alert_id,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    # Mark alert as triggered
                    conn.execute(
                        f"UPDATE alerts SET is_active = FALSE WHERE id = {alert_id}"
                    )
                    conn.commit()

alert_manager = AlertManager()

@app.websocket("/ws/alerts/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await alert_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming alert subscriptions/unsubscriptions
            command = json.loads(data)
            
            if command['action'] == 'subscribe':
                symbol = command['symbol']
                if user_id not in alert_manager.price_alerts:
                    alert_manager.price_alerts[user_id] = set()
                alert_manager.price_alerts[user_id].add(symbol)
            
            elif command['action'] == 'unsubscribe':
                symbol = command['symbol']
                if user_id in alert_manager.price_alerts:
                    alert_manager.price_alerts[user_id].discard(symbol)
    
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        alert_manager.disconnect(websocket, user_id)
```

---

## 7. PERFORMANCE OPTIMIZATION TIPS

1. **Database Indexes**: Create indexes on frequently queried columns (stock_id, date, status)
2. **Caching**: Use Redis to cache screener results for 1-2 hours
3. **Data Partitioning**: Partition price tables by date to speed up queries
4. **Batch Operations**: Insert/update prices in batches (100 rows at a time)
5. **Query Optimization**: Use EXPLAIN ANALYZE to optimize slow queries
6. **API Rate Limiting**: Implement rate limiting on public APIs
7. **Lazy Loading**: Load detailed analysis only when user clicks on a stock

---

## TESTING

```python
# Unit test for VCP detector
import unittest

class TestVCPDetector(unittest.TestCase):
    def setUp(self):
        self.detector = VCPDetector()
        # Load test data
        self.test_df = pd.read_csv('test_data.csv')
    
    def test_vcp_detection(self):
        patterns = self.detector.get_entry_points(self.test_df)
        self.assertGreater(len(patterns), 0)
    
    def test_volume_pattern_check(self):
        result = self.detector._check_volume_pattern(
            self.test_df, 
            [(10, 15), (12, 16)]
        )
        self.assertTrue(result)
```

---

**This guide provides the foundational code patterns needed to build your Trading_Bramha dashboard.**
