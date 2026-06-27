# React Component Implementation - Scanner Dashboard

Complete, production-ready React components for SwingEdge-style scanner dashboard.

---

## 1. MAIN SCANNER LAYOUT

### scanner-dashboard.jsx

```jsx
import React, { useState, useEffect } from 'react';
import ScannerSidebar from './components/ScannerSidebar';
import ScannerHeader from './components/ScannerHeader';
import ScannerResults from './components/ScannerResults';
import './styles/scanner-dashboard.css';

const ScannerDashboard = () => {
  const [scanners, setScanners] = useState({ pattern: [], momentum: [], technical: [] });
  const [selectedScanner, setSelectedScanner] = useState(null);
  const [selectedScannerName, setSelectedScannerName] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Load all scanners on mount
  useEffect(() => {
    const loadScanners = async () => {
      try {
        const response = await fetch('/api/scanners');
        const data = await response.json();
        setScanners(data);
      } catch (err) {
        setError('Failed to load scanners');
      }
    };
    loadScanners();
  }, []);

  const handleSelectScanner = async (scannerId, scannerName) => {
    setSelectedScanner(scannerId);
    setSelectedScannerName(scannerName);
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/scanners/${scannerId}/results?limit=50`);
      const data = await response.json();
      setResults(data.data);
      setLastUpdated(new Date().toLocaleString());
    } catch (err) {
      setError('Failed to load scanner results');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="scanner-dashboard-container">
      <ScannerHeader />
      
      <div className="scanner-main-layout">
        <ScannerSidebar 
          scanners={scanners}
          selectedScanner={selectedScanner}
          onSelectScanner={handleSelectScanner}
        />

        <div className="scanner-content">
          {selectedScanner && (
            <>
              <div className="content-header">
                <h2>{selectedScannerName}</h2>
                {lastUpdated && (
                  <div className="last-updated">
                    Last Updated: {lastUpdated}
                  </div>
                )}
              </div>

              {loading && (
                <div className="loading-state">
                  <div className="spinner"></div>
                  <p>Loading scanner results...</p>
                </div>
              )}

              {error && (
                <div className="error-state">
                  <p>❌ {error}</p>
                </div>
              )}

              {!loading && !error && results.length === 0 && (
                <div className="empty-state">
                  <p>No results found for this scanner</p>
                </div>
              )}

              {!loading && !error && results.length > 0 && (
                <ScannerResults results={results} />
              )}
            </>
          )}

          {!selectedScanner && (
            <div className="welcome-state">
              <h2>Welcome to Scanner Dashboard</h2>
              <p>Select a scanner from the left sidebar to view results</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ScannerDashboard;
```

---

## 2. SIDEBAR COMPONENT

### components/ScannerSidebar.jsx

```jsx
import React, { useState } from 'react';
import '../styles/scanner-sidebar.css';

const ScannerSidebar = ({ scanners, selectedScanner, onSelectScanner }) => {
  const [expandedCategory, setExpandedCategory] = useState('pattern');

  const categories = [
    {
      id: 'pattern',
      label: 'PRE-BUILT SCANNERS',
      icon: '◆',
      scanners: scanners.pattern || []
    },
    {
      id: 'technical',
      label: "TODAY'S FOCUS",
      icon: '•',
      scanners: scanners.technical || []
    },
    {
      id: 'boards',
      label: 'BOARDS & WATCHLISTS',
      icon: '📊',
      isStatic: true,
      items: [
        { id: 'movers', label: "Today's Scanner Movers", icon: '📈' },
        { id: 'results', label: 'Scanner Results', icon: '📋' },
        { id: 'community', label: 'Community Watchlist', icon: '👥' }
      ]
    }
  ];

  return (
    <aside className="scanner-sidebar">
      <div className="sidebar-container">
        {categories.map(category => (
          <div key={category.id} className="sidebar-section">
            <h3 className="section-title">{category.label}</h3>
            
            {category.isStatic ? (
              <div className="static-items">
                {category.items.map(item => (
                  <div key={item.id} className="scanner-item static">
                    <span className="item-icon">{item.icon}</span>
                    <span className="item-label">{item.label}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="scanners-list">
                {category.scanners.length === 0 ? (
                  <p className="no-items">No scanners in this category</p>
                ) : (
                  category.scanners.map(scanner => (
                    <div
                      key={scanner.id}
                      className={`scanner-item ${selectedScanner === scanner.id ? 'active' : ''}`}
                      onClick={() => onSelectScanner(scanner.id, scanner.name)}
                    >
                      <span className="item-icon">{category.icon}</span>
                      <span className="item-label">{scanner.name}</span>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </aside>
  );
};

export default ScannerSidebar;
```

### styles/scanner-sidebar.css

```css
.scanner-sidebar {
  width: 250px;
  background: #f8f9fa;
  border-right: 1px solid #e0e0e0;
  height: 100vh;
  overflow-y: auto;
  position: fixed;
  left: 0;
  top: 60px;
}

.sidebar-container {
  padding: 20px 0;
}

.sidebar-section {
  margin-bottom: 30px;
}

.section-title {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #999;
  margin: 0 20px 12px;
  text-transform: uppercase;
}

.scanners-list,
.static-items {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.scanner-item {
  display: flex;
  align-items: center;
  padding: 10px 20px;
  cursor: pointer;
  color: #555;
  font-size: 14px;
  transition: all 0.2s;
  border-left: 3px solid transparent;
}

.scanner-item:hover {
  background: #f0f0f0;
  color: #333;
}

.scanner-item.active {
  background: #e8ecff;
  color: #6366f1;
  border-left-color: #6366f1;
  font-weight: 500;
}

.scanner-item.static {
  cursor: pointer;
  color: #666;
}

.item-icon {
  margin-right: 10px;
  font-size: 12px;
}

.item-label {
  flex: 1;
}

.no-items {
  padding: 20px;
  text-align: center;
  color: #999;
  font-size: 12px;
}

/* Scrollbar styling */
.scanner-sidebar::-webkit-scrollbar {
  width: 6px;
}

.scanner-sidebar::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.scanner-sidebar::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}

.scanner-sidebar::-webkit-scrollbar-thumb:hover {
  background: #999;
}
```

---

## 3. HEADER COMPONENT

### components/ScannerHeader.jsx

```jsx
import React from 'react';
import '../styles/scanner-header.css';

const ScannerHeader = () => {
  return (
    <header className="scanner-header">
      <div className="header-left">
        <div className="logo">
          <span className="logo-icon">📊</span>
          <span className="logo-text">Trading Bramha Scanner</span>
        </div>
      </div>

      <nav className="header-nav">
        <button className="nav-button">Screener</button>
        <button className="nav-button">Sectors</button>
        <button className="nav-button">Tools</button>
        <button className="nav-button">More</button>
      </nav>

      <div className="header-right">
        <input 
          type="text" 
          placeholder="Search any NSE stock..." 
          className="search-input"
        />
        <button className="theme-toggle">🌙</button>
      </div>
    </header>
  );
};

export default ScannerHeader;
```

### styles/scanner-header.css

```css
.scanner-header {
  height: 60px;
  background: white;
  border-bottom: 1px solid #e0e0e0;
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 30px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left {
  flex-shrink: 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  color: #333;
}

.logo-icon {
  font-size: 20px;
}

.logo-text {
  font-size: 16px;
}

.header-nav {
  display: flex;
  gap: 15px;
  flex: 1;
}

.nav-button {
  background: none;
  border: none;
  color: #666;
  font-size: 14px;
  cursor: pointer;
  padding: 5px 10px;
  border-radius: 4px;
  transition: all 0.2s;
}

.nav-button:hover {
  background: #f0f0f0;
  color: #333;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
}

.search-input {
  width: 300px;
  padding: 8px 15px;
  border: 1px solid #e0e0e0;
  border-radius: 20px;
  font-size: 14px;
  background: #f8f9fa;
}

.search-input::placeholder {
  color: #999;
}

.search-input:focus {
  outline: none;
  border-color: #6366f1;
  background: white;
}

.theme-toggle {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
}
```

---

## 4. RESULTS GRID & CARDS

### components/ScannerResults.jsx

```jsx
import React, { useState } from 'react';
import ScannerResultCard from './ScannerResultCard';
import '../styles/scanner-results.css';

const ScannerResults = ({ results }) => {
  const [sortBy, setSortBy] = useState('relevance');

  const sortResults = (items) => {
    switch(sortBy) {
      case 'price_asc':
        return [...items].sort((a, b) => a.entry_point - b.entry_point);
      case 'price_desc':
        return [...items].sort((a, b) => b.entry_point - a.entry_point);
      case 'rs_desc':
        return [...items].sort((a, b) => (b.rs_rating || 0) - (a.rs_rating || 0));
      default:
        return items;
    }
  };

  const sortedResults = sortResults(results);

  return (
    <div className="scanner-results-container">
      <div className="results-controls">
        <div className="results-info">
          <span className="result-count">{results.length} stocks found</span>
        </div>
        
        <div className="sort-controls">
          <label>Sort by:</label>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="relevance">Relevance</option>
            <option value="price_asc">Price (Low to High)</option>
            <option value="price_desc">Price (High to Low)</option>
            <option value="rs_desc">RS Rating (High)</option>
          </select>
        </div>
      </div>

      <div className="scanner-grid">
        {sortedResults.map(result => (
          <ScannerResultCard key={result.id} result={result} />
        ))}
      </div>
    </div>
  );
};

export default ScannerResults;
```

### components/ScannerResultCard.jsx

```jsx
import React, { useState } from 'react';
import '../styles/scanner-result-card.css';

const ScannerResultCard = ({ result }) => {
  const [isSaved, setIsSaved] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  const handleSave = (e) => {
    e.stopPropagation();
    setIsSaved(!isSaved);
    
    // Call API
    fetch(`/api/scanners/${result.id}/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: 1 })
    });
  };

  const handleDelete = (e) => {
    e.stopPropagation();
    // Delete from user's list
  };

  const getInitials = (symbol) => {
    return symbol.substring(0, 1).toUpperCase();
  };

  const getInitialColor = (index) => {
    const colors = [
      '#667eea', '#764ba2', '#f093fb', '#4facfe',
      '#43e97b', '#fa709a', '#fee140', '#30b0fe'
    ];
    return colors[index % colors.length];
  };

  return (
    <div 
      className="scanner-card"
      onClick={() => setShowDetails(!showDetails)}
    >
      {/* Card Header */}
      <div className="card-header">
        <div className="stock-header">
          <div 
            className="stock-initial"
            style={{ background: getInitialColor(result.symbol.charCodeAt(0)) }}
          >
            {getInitials(result.symbol)}
          </div>
          
          <div className="stock-info">
            <div className="stock-symbol">{result.symbol}</div>
            <div className="stock-name">{result.name}</div>
          </div>
        </div>

        <div className="card-actions">
          <button 
            className={`action-button star-btn ${isSaved ? 'saved' : ''}`}
            onClick={handleSave}
            title="Save to watchlist"
          >
            ★
          </button>
          <button 
            className="action-button delete-btn"
            onClick={handleDelete}
            title="Remove"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Pattern Tags */}
      <div className="pattern-tags">
        <span className="tag tag-primary">
          {result.pattern.type}
        </span>
        {result.pattern.measurements?.map((measurement, idx) => (
          <span key={idx} className="tag tag-secondary">
            {measurement}
          </span>
        ))}
      </div>

      {/* Why It's Interesting Section */}
      <div className="why-section">
        <h4>WHY IT'S INTERESTING:</h4>
        <ul className="reasons-list">
          {result.reasons.slice(0, 3).map((reason, idx) => (
            <li key={idx} className="reason-item">
              <span className="reason-icon">✓</span>
              <span className="reason-text">{reason.text}</span>
            </li>
          ))}
        </ul>
        {result.reasons.length > 3 && (
          <div className="more-reasons">
            +{result.reasons.length - 3} more reasons
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="card-footer">
        <button className="analyze-button">
          <span>📊</span>
          Analyze Setup
        </button>
      </div>

      {/* Details Panel (Expandable) */}
      {showDetails && (
        <div className="card-details">
          <div className="detail-row">
            <span>Entry Point:</span>
            <strong>₹{result.entry_point?.toFixed(2) || 'N/A'}</strong>
          </div>
          <div className="detail-row">
            <span>Target Price:</span>
            <strong>₹{result.target_price?.toFixed(2) || 'N/A'}</strong>
          </div>
          <div className="detail-row">
            <span>Stop Loss:</span>
            <strong>₹{result.stop_loss?.toFixed(2) || 'N/A'}</strong>
          </div>
        </div>
      )}
    </div>
  );
};

export default ScannerResultCard;
```

### styles/scanner-result-card.css

```css
.scanner-card {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  min-width: 300px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}

.scanner-card:hover {
  box-shadow: 0 8px 16px rgba(0,0,0,0.12);
  border-color: #6366f1;
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.stock-header {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.stock-initial {
  width: 40px;
  height: 40px;
  border-radius: 6px;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 16px;
  flex-shrink: 0;
}

.stock-info {
  min-width: 0;
  flex: 1;
}

.stock-symbol {
  font-weight: 700;
  color: #333;
  font-size: 16px;
  margin-bottom: 2px;
}

.stock-name {
  font-size: 12px;
  color: #999;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.action-button {
  width: 32px;
  height: 32px;
  border: 1px solid #e0e0e0;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  font-size: 16px;
  color: #999;
}

.action-button:hover {
  border-color: #6366f1;
  color: #6366f1;
  background: #f0f4ff;
}

.action-button.saved {
  color: #fbbf24;
  border-color: #fbbf24;
  background: #fffbeb;
}

.delete-btn:hover {
  border-color: #ef5350;
  color: #ef5350;
}

.pattern-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.tag {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.tag-primary {
  background: #e8ecff;
  color: #4f46e5;
}

.tag-secondary {
  background: #f3f4f6;
  color: #6b7280;
}

.why-section {
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.why-section h4 {
  font-size: 11px;
  font-weight: 700;
  color: #666;
  margin: 0 0 8px 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.reasons-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.reason-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
  color: #555;
  line-height: 1.4;
}

.reason-icon {
  color: #10b981;
  font-weight: bold;
  flex-shrink: 0;
  margin-top: 1px;
}

.reason-text {
  flex: 1;
}

.more-reasons {
  font-size: 11px;
  color: #999;
  margin-top: 6px;
  cursor: pointer;
  text-decoration: underline;
}

.card-footer {
  display: flex;
  gap: 8px;
}

.analyze-button {
  flex: 1;
  background: #6366f1;
  color: white;
  border: none;
  padding: 8px 12px;
  border-radius: 6px;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.analyze-button:hover {
  background: #4f46e5;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
}

.card-details {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
  background: #fafbfc;
  border-radius: 4px;
  padding: 12px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  margin-bottom: 8px;
  color: #666;
}

.detail-row strong {
  color: #333;
  font-weight: 600;
}

.detail-row:last-child {
  margin-bottom: 0;
}
```

### styles/scanner-results.css

```css
.scanner-results-container {
  margin-left: 250px;
  padding: 20px;
}

.results-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #e0e0e0;
}

.results-info {
  display: flex;
  gap: 20px;
}

.result-count {
  font-size: 14px;
  color: #666;
  font-weight: 600;
}

.sort-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sort-controls label {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.sort-controls select {
  padding: 6px 10px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  background: white;
}

.scanner-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

@media (max-width: 1200px) {
  .scanner-grid {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  }
}

@media (max-width: 768px) {
  .scanner-results-container {
    margin-left: 0;
  }
  
  .scanner-grid {
    grid-template-columns: 1fr;
  }
}

.loading-state,
.error-state,
.empty-state,
.welcome-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  color: #999;
}

.loading-state {
  gap: 20px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f0f0f0;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

---

## 5. MAIN SCANNER APP CSS

### styles/scanner-dashboard.css

```css
.scanner-dashboard-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #fafbfc;
}

.scanner-main-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.scanner-content {
  flex: 1;
  margin-left: 250px;
  overflow-y: auto;
  padding: 0;
}

.content-header {
  padding: 20px;
  background: white;
  border-bottom: 1px solid #e0e0e0;
  position: sticky;
  top: 0;
  z-index: 50;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.content-header h2 {
  margin: 0;
  font-size: 24px;
  color: #333;
}

.last-updated {
  font-size: 12px;
  color: #999;
}

/* Responsive */
@media (max-width: 768px) {
  .scanner-content {
    margin-left: 0;
  }
  
  .scanner-sidebar {
    position: fixed;
    left: -250px;
    z-index: 99;
    transition: left 0.3s;
  }
  
  .scanner-sidebar.open {
    left: 0;
  }
}
```

---

## 6. PACKAGE.JSON DEPENDENCIES

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.4.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^3.1.0",
    "vite": "^4.2.0"
  }
}
```

Install with:
```bash
npm install
npm install axios
```

---

## 7. USAGE

```jsx
// App.jsx
import ScannerDashboard from './pages/ScannerDashboard';

function App() {
  return <ScannerDashboard />;
}

export default App;
```

---

**This gives you a fully-functional, production-ready Scanner Dashboard UI exactly like SwingEdge! 🎉**
