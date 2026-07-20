import { useState, useEffect, useRef, useCallback } from 'react';
import {
  createChart, CandlestickSeries, LineSeries, CrosshairMode, LineStyle
} from 'lightweight-charts';

// ─── Audio chime (Web Audio API — no file needed) ──────────────────────────────
function playChime() {
  try {
    const ctx   = new AudioContext();
    const notes = [523.25, 659.25, 783.99]; // C5 E5 G5
    notes.forEach((freq, i) => {
      const osc  = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'sine';
      osc.frequency.value = freq;
      const t = ctx.currentTime + i * 0.18;
      gain.gain.setValueAtTime(0, t);
      gain.gain.linearRampToValueAtTime(0.25, t + 0.04);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.55);
      osc.start(t);
      osc.stop(t + 0.6);
    });
  } catch { /* blocked by browser policy before first user gesture */ }
}

// ─── Browser OS notification ───────────────────────────────────────────────────
function fireOSNotification(market, results) {
  if (!results.length) return;
  if (!('Notification' in window) || Notification.permission !== 'granted') return;
  const label   = market === 'india' ? 'India 🇮🇳' : 'USA 🇺🇸';
  const tickers = results.slice(0, 5).map(r => r.ticker).join('  ·  ');
  const extra   = results.length > 5 ? `  +${results.length - 5} more` : '';
  new Notification(`📈 ${results.length} breakout${results.length > 1 ? 's' : ''} — ${label}`, {
    body: tickers + extra,
    tag:  `breakout-${market}`
  });
}

// ─── In-app toast ──────────────────────────────────────────────────────────────
function Toast({ toasts, onDismiss }) {
  if (!toasts.length) return null;
  return (
    <div className="fixed bottom-5 right-5 flex flex-col gap-2 z-50">
      {toasts.map(t => (
        <div
          key={t.id}
          onClick={() => onDismiss(t.id)}
          className={`flex items-start gap-3 px-4 py-3 rounded-xl shadow-2xl cursor-pointer
            text-sm max-w-sm border transition-all
            ${t.type === 'success'
              ? 'bg-emerald-900/90 border-emerald-600 text-emerald-100'
              : 'bg-slate-800/90 border-slate-600 text-slate-200'}`}
        >
          <span className="text-lg leading-none mt-0.5">{t.icon}</span>
          <div>
            <p className="font-semibold">{t.title}</p>
            {t.body && <p className="text-xs opacity-75 mt-0.5">{t.body}</p>}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Alerts settings panel ─────────────────────────────────────────────────────
function AlertsPanel({
  soundOn, setSoundOn,
  notifPerm, requestNotifPerm,
  autoScan, setAutoScan,
  autoInterval, setAutoInterval,
  nextScanIn,
  alertHistory
}) {
  const intervals = [15, 30, 60];
  return (
    <div className="absolute right-0 top-12 w-80 bg-slate-800 border border-slate-700 rounded-2xl shadow-2xl z-50 p-4">
      <h3 className="text-slate-200 font-semibold mb-3 text-sm">Alert Settings</h3>

      {/* Browser notifications */}
      <div className="flex items-center justify-between py-2.5 border-b border-slate-700">
        <div>
          <p className="text-slate-300 text-sm">Browser notifications</p>
          <p className="text-slate-500 text-xs">OS-level popup, works when tab is hidden</p>
        </div>
        {notifPerm === 'granted' ? (
          <span className="text-xs text-emerald-400 font-medium">✓ Enabled</span>
        ) : notifPerm === 'denied' ? (
          <span className="text-xs text-rose-400">Blocked</span>
        ) : (
          <button
            onClick={requestNotifPerm}
            className="text-xs px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded-full transition-colors"
          >
            Allow
          </button>
        )}
      </div>

      {/* Sound */}
      <div className="flex items-center justify-between py-2.5 border-b border-slate-700">
        <div>
          <p className="text-slate-300 text-sm">Sound chime</p>
          <p className="text-slate-500 text-xs">3-note chord when breakouts are found</p>
        </div>
        <button
          onClick={() => { setSoundOn(v => !v); if (!soundOn) playChime(); }}
          className={`relative w-10 h-5 rounded-full transition-colors ${soundOn ? 'bg-emerald-500' : 'bg-slate-600'}`}
        >
          <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-all ${soundOn ? 'left-5' : 'left-0.5'}`} />
        </button>
      </div>

      {/* Auto-scan */}
      <div className="py-2.5 border-b border-slate-700">
        <div className="flex items-center justify-between mb-2">
          <div>
            <p className="text-slate-300 text-sm">Auto-scan</p>
            <p className="text-slate-500 text-xs">
              {autoScan && nextScanIn != null
                ? `Next scan in ${Math.floor(nextScanIn / 60)}m ${nextScanIn % 60}s`
                : 'Scans active market on schedule'}
            </p>
          </div>
          <button
            onClick={() => setAutoScan(v => !v)}
            className={`relative w-10 h-5 rounded-full transition-colors ${autoScan ? 'bg-emerald-500' : 'bg-slate-600'}`}
          >
            <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-all ${autoScan ? 'left-5' : 'left-0.5'}`} />
          </button>
        </div>
        <div className="flex gap-1.5 mt-1">
          {intervals.map(m => (
            <button
              key={m}
              onClick={() => setAutoInterval(m)}
              className={`flex-1 text-xs py-1 rounded-lg transition-colors ${
                autoInterval === m
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-700 text-slate-400 hover:text-white'
              }`}
            >
              {m}m
            </button>
          ))}
        </div>
      </div>

      {/* Alert history */}
      <div className="pt-2.5">
        <p className="text-slate-500 text-xs font-medium uppercase tracking-wide mb-2">Recent alerts</p>
        {alertHistory.length === 0 ? (
          <p className="text-slate-600 text-xs italic">No alerts yet</p>
        ) : (
          <div className="flex flex-col gap-1.5 max-h-40 overflow-y-auto">
            {alertHistory.map((a, i) => (
              <div key={i} className="flex items-start gap-2 text-xs">
                <span className="text-slate-600 tabular-nums shrink-0 mt-0.5">{a.time}</span>
                <span className={`shrink-0 ${a.market === 'india' ? 'text-orange-400' : 'text-blue-400'}`}>
                  {a.market === 'india' ? '🇮🇳' : '🇺🇸'}
                </span>
                {a.count > 0
                  ? <span className="text-emerald-400">{a.count} found: {a.tickers}</span>
                  : <span className="text-slate-600">0 breakouts</span>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Chart Panel ───────────────────────────────────────────────────────────────
function BreakoutChart({ ticker }) {
  const containerRef = useRef(null);
  const chartRef     = useRef(null);
  const [status, setStatus] = useState('idle');
  const [errMsg, setErrMsg] = useState('');

  useEffect(() => {
    if (!ticker || !containerRef.current) return;
    if (chartRef.current) { chartRef.current.remove(); chartRef.current = null; }

    let cancelled = false;
    setStatus('loading'); setErrMsg('');

    (async () => {
      try {
        const res  = await fetch('/api/chart', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ticker })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        if (cancelled) return;

        const { candles, consolidationHigh, consolidationLow } = data;
        const chart = createChart(containerRef.current, {
          layout:          { background: { color: '#1e293b' }, textColor: '#cbd5e1' },
          grid:            { vertLines: { color: '#334155' }, horzLines: { color: '#334155' } },
          crosshair:       { mode: CrosshairMode.Normal },
          rightPriceScale: { borderColor: '#475569' },
          timeScale:       { borderColor: '#475569', timeVisible: true },
          width: containerRef.current.clientWidth, height: 420
        });
        chartRef.current = chart;

        const cs = chart.addSeries(CandlestickSeries, {
          upColor: '#22c55e', downColor: '#ef4444',
          borderUpColor: '#22c55e', borderDownColor: '#ef4444',
          wickUpColor: '#22c55e', wickDownColor: '#ef4444'
        });
        cs.setData(candles.map((c, i) => ({
          time: c.time, open: c.open, high: c.high, low: c.low, close: c.close,
          ...(i === candles.length - 1
            ? { color: '#10b981', wickColor: '#10b981', borderColor: '#10b981' } : {})
        })));

        [
          { title: 'Consol. High', value: consolidationHigh },
          { title: 'Consol. Low',  value: consolidationLow  }
        ].forEach(({ title, value }) => {
          const s = chart.addSeries(LineSeries, {
            color: 'rgba(244,63,94,0.7)', lineWidth: 1, lineStyle: LineStyle.Dashed,
            priceLineVisible: false, crosshairMarkerVisible: false, title
          });
          s.setData(candles.map(c => ({ time: c.time, value })));
        });

        chart.timeScale().fitContent();
        const onResize = () => chartRef.current?.applyOptions({ width: containerRef.current.clientWidth });
        window.addEventListener('resize', onResize);
        setStatus('done');
        return () => window.removeEventListener('resize', onResize);
      } catch (err) {
        if (!cancelled) { setStatus('error'); setErrMsg(err.message); }
      }
    })();

    return () => {
      cancelled = true;
      if (chartRef.current) { chartRef.current.remove(); chartRef.current = null; }
    };
  }, [ticker]);

  return (
    <div className="rounded-2xl shadow-xl bg-slate-800 p-4 mt-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-slate-200 font-semibold text-sm">
          4H Chart — <span className="text-emerald-400 font-mono">{ticker}</span>
        </h3>
        <div className="flex items-center gap-4 text-xs text-slate-500">
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-6 border-t border-dashed border-rose-500/70"></span>
            Consolidation
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-sm bg-emerald-500"></span>
            Breakout candle
          </span>
        </div>
      </div>
      {status === 'loading' && (
        <div className="flex items-center justify-center h-[420px] text-slate-400 text-sm gap-2">
          <svg className="animate-spin h-4 w-4 text-emerald-500" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
          Loading chart…
        </div>
      )}
      {status === 'error' && (
        <div className="flex items-center justify-center h-[420px] text-rose-400 text-sm">{errMsg}</div>
      )}
      <div ref={containerRef} className={status !== 'done' ? 'invisible h-0 overflow-hidden' : ''} />
    </div>
  );
}

// ─── Progress Bar ───────────────────────────────────────────────────────────────
function ProgressBar({ scanned, total, found, lastTicker }) {
  const pct = total ? Math.round(scanned / total * 100) : 0;
  return (
    <div className="bg-slate-800 rounded-2xl p-4 mt-4 shadow-xl">
      <div className="flex items-center justify-between text-sm mb-2">
        <span className="text-slate-300 font-medium">
          Scanning… <span className="text-emerald-400">{found} breakout{found !== 1 ? 's' : ''} found</span>
        </span>
        <span className="text-slate-500 tabular-nums">{scanned} / {total} · {pct}%</span>
      </div>
      <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-emerald-500 to-teal-500 transition-all duration-200 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
      {lastTicker && <p className="text-slate-600 text-xs mt-1.5 font-mono truncate">{lastTicker}</p>}
    </div>
  );
}

// ─── Results Table ──────────────────────────────────────────────────────────────
function ResultsTable({ rows, selectedTicker, onSelect, market }) {
  if (!rows.length) return (
    <div className="bg-slate-800 rounded-2xl shadow-xl p-16 text-center text-slate-500 text-sm">
      No breakouts found — try scanning again.
    </div>
  );
  return (
    <div className="bg-slate-800 rounded-2xl shadow-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700">
              {['#','Ticker','Price','Breakout %','Size %','Rel. Volume','% from 20d Hi','% from 50d Hi','Range %']
                .map((h, i) => (
                  <th key={h} className={`px-4 py-3 text-slate-400 font-medium ${i < 2 ? 'text-left' : 'text-right'}`}>
                    {h}
                  </th>
                ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => {
              const sel = row.ticker === selectedTicker;
              return (
                <tr
                  key={row.ticker}
                  onClick={() => onSelect(row.ticker)}
                  className={`border-b border-slate-700 cursor-pointer transition-colors ${sel ? 'bg-slate-700/60' : 'hover:bg-slate-700/40'}`}
                >
                  <td className="px-4 py-3 text-slate-600 text-xs">{idx + 1}</td>
                  <td className="px-4 py-3">
                    <span className={`font-mono font-semibold ${sel ? 'text-emerald-300' : 'text-emerald-400'}`}>
                      {row.ticker}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-slate-200">
                    {market === 'india' ? `₹${row.price.toLocaleString('en-IN')}` : `$${row.price.toFixed(2)}`}
                  </td>
                  <td className="px-4 py-3 text-right text-emerald-400 font-medium">+{row.breakoutPercent}%</td>
                  <td className="px-4 py-3 text-right text-slate-300">{row.breakoutSize}%</td>
                  <td className="px-4 py-3 text-right font-semibold text-amber-400">{row.relVolume}×</td>
                  <td className={`px-4 py-3 text-right ${row.from20dHigh >= -2 ? 'text-emerald-400' : 'text-slate-400'}`}>
                    {row.from20dHigh > 0 ? '+' : ''}{row.from20dHigh}%
                  </td>
                  <td className={`px-4 py-3 text-right ${row.from50dHigh >= -2 ? 'text-emerald-400' : 'text-slate-400'}`}>
                    {row.from50dHigh > 0 ? '+' : ''}{row.from50dHigh}%
                  </td>
                  <td className="px-4 py-3 text-right text-slate-400">{row.rangePercent}%</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── App ────────────────────────────────────────────────────────────────────────
let toastIdCounter = 0;

export default function App() {
  const [market,         setMarket]         = useState('usa');
  const [loading,        setLoading]        = useState(false);
  const [lastScanned,    setLastScanned]    = useState(null);
  const [scanError,      setScanError]      = useState(null);
  const [results,        setResults]        = useState({ india: [], usa: [] });
  const [selectedTicker, setSelectedTicker] = useState({ india: null, usa: null });
  const [progress,       setProgress]       = useState(null);

  // Alerts state
  const [showAlerts,    setShowAlerts]    = useState(false);
  const [soundOn,       setSoundOn]       = useState(true);
  const [notifPerm,     setNotifPerm]     = useState(
    'Notification' in window ? Notification.permission : 'unsupported'
  );
  const [autoScan,      setAutoScan]      = useState(false);
  const [autoInterval,  setAutoInterval]  = useState(30); // minutes
  const [nextScanIn,    setNextScanIn]    = useState(null);
  const [alertHistory,  setAlertHistory]  = useState([]);
  const [toasts,        setToasts]        = useState([]);

  const esRef          = useRef(null);
  const autoTimerRef   = useRef(null);
  const countdownRef   = useRef(null);
  const marketRef      = useRef(market);
  const loadingRef     = useRef(loading);

  useEffect(() => { marketRef.current  = market;  }, [market]);
  useEffect(() => { loadingRef.current = loading; }, [loading]);

  // ── Toast helpers ──
  const addToast = useCallback((title, body, type = 'info', icon = '🔔') => {
    const id = ++toastIdCounter;
    setToasts(prev => [...prev, { id, title, body, type, icon }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 5000);
  }, []);
  const dismissToast = useCallback(id => setToasts(prev => prev.filter(t => t.id !== id)), []);

  // ── Notification permission ──
  const requestNotifPerm = async () => {
    if (!('Notification' in window)) return;
    const perm = await Notification.requestPermission();
    setNotifPerm(perm);
    if (perm === 'granted') addToast('Notifications enabled', 'You\'ll get OS alerts when breakouts are found.', 'success', '🔔');
  };

  // ── Core scan function ──
  const scan = useCallback((targetMarket) => {
    if (loadingRef.current) return;
    const mkt = targetMarket || marketRef.current;

    setLoading(true);
    setScanError(null);
    setProgress({ scanned: 0, total: 0, found: 0, ticker: '' });

    const es = new EventSource(`/api/scan?market=${mkt}`);
    esRef.current = es;

    es.onmessage = e => {
      const data = JSON.parse(e.data);

      if (data.type === 'progress') {
        setProgress({ scanned: data.scanned, total: data.total, found: data.found, ticker: data.ticker });

      } else if (data.type === 'done') {
        const found = data.results || [];

        setResults(prev => ({ ...prev, [mkt]: found }));
        setLastScanned(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
        if (found.length > 0)
          setSelectedTicker(prev => ({ ...prev, [mkt]: found[0].ticker }));

        // Alerts
        if (found.length > 0) {
          if (soundOn) playChime();
          fireOSNotification(mkt, found);
          const label   = mkt === 'india' ? 'India 🇮🇳' : 'USA 🇺🇸';
          const tickers = found.slice(0, 3).map(r => r.ticker).join(', ');
          addToast(
            `${found.length} breakout${found.length > 1 ? 's' : ''} — ${label}`,
            tickers + (found.length > 3 ? ` +${found.length - 3} more` : ''),
            'success', '📈'
          );
        } else {
          addToast(`Scan complete — ${mkt.toUpperCase()}`, 'No breakouts found this pass.', 'info', '🔍');
        }

        // History entry
        setAlertHistory(prev => [{
          time:    new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          market:  mkt,
          count:   found.length,
          tickers: found.slice(0, 4).map(r => r.ticker).join(', ')
        }, ...prev].slice(0, 20));

        // Tab title
        document.title = found.length > 0
          ? `(${found.length}) Breakout Scanner`
          : 'Breakout Scanner';

        setLoading(false);
        setProgress(null);
        es.close();
        esRef.current = null;

      } else if (data.type === 'error') {
        setScanError(data.message);
        setLoading(false);
        setProgress(null);
        es.close();
        esRef.current = null;
      }
    };

    es.onerror = () => {
      setScanError('Connection error — is the backend running on port 3001?');
      setLoading(false);
      setProgress(null);
      es.close();
      esRef.current = null;
    };
  }, [soundOn, addToast]);

  // ── Auto-scan timer ──
  useEffect(() => {
    clearInterval(autoTimerRef.current);
    clearInterval(countdownRef.current);
    setNextScanIn(null);

    if (!autoScan) return;

    const totalSecs = autoInterval * 60;
    let remaining   = totalSecs;

    setNextScanIn(remaining);

    countdownRef.current = setInterval(() => {
      remaining -= 1;
      setNextScanIn(remaining);
      if (remaining <= 0) {
        remaining = totalSecs;
        setNextScanIn(remaining);
        scan(marketRef.current);
      }
    }, 1000);

    return () => {
      clearInterval(autoTimerRef.current);
      clearInterval(countdownRef.current);
    };
  }, [autoScan, autoInterval, scan]);

  // Cleanup on unmount
  useEffect(() => () => {
    esRef.current?.close();
    clearInterval(countdownRef.current);
  }, []);

  const cancelScan = () => {
    esRef.current?.close();
    esRef.current = null;
    setLoading(false);
    setProgress(null);
  };

  // Close alerts panel on outside click
  useEffect(() => {
    if (!showAlerts) return;
    const handler = e => {
      if (!e.target.closest('#alerts-panel') && !e.target.closest('#alerts-btn'))
        setShowAlerts(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showAlerts]);

  const currentResults = results[market];
  const currentTicker  = selectedTicker[market];
  const totalAlertCount = results.usa.length + results.india.length;

  return (
    <div className="min-h-screen bg-slate-900 text-slate-200 flex flex-col">

      {/* ── Header ── */}
      <header className="border-b border-slate-700 bg-slate-900/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white">📈 Breakout Scanner</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              {lastScanned ? `Last scanned: ${lastScanned}` : 'Select a market and press Scan Now'}
              {autoScan && nextScanIn != null && (
                <span className="ml-2 text-emerald-600">
                  · auto in {Math.floor(nextScanIn / 60)}m {String(nextScanIn % 60).padStart(2, '0')}s
                </span>
              )}
            </p>
          </div>

          <div className="flex items-center gap-2">
            {scanError && <span className="text-rose-400 text-xs max-w-xs truncate">{scanError}</span>}

            {/* Alerts bell */}
            <div className="relative">
              <button
                id="alerts-btn"
                onClick={() => setShowAlerts(v => !v)}
                className={`relative p-2.5 rounded-xl transition-colors ${
                  showAlerts ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'
                }`}
                title="Alert settings"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                  <path strokeLinecap="round" strokeLinejoin="round"
                    d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6 6 0 10-12 0v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
                </svg>
                {(autoScan || totalAlertCount > 0) && (
                  <span className={`absolute -top-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-slate-900 ${autoScan ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                )}
              </button>

              {showAlerts && (
                <div id="alerts-panel">
                  <AlertsPanel
                    soundOn={soundOn}         setSoundOn={setSoundOn}
                    notifPerm={notifPerm}     requestNotifPerm={requestNotifPerm}
                    autoScan={autoScan}       setAutoScan={setAutoScan}
                    autoInterval={autoInterval} setAutoInterval={setAutoInterval}
                    nextScanIn={nextScanIn}
                    alertHistory={alertHistory}
                  />
                </div>
              )}
            </div>

            {/* Scan / Cancel */}
            {loading ? (
              <button onClick={cancelScan}
                className="flex items-center gap-2 px-5 py-2.5 bg-slate-700 hover:bg-slate-600 rounded-full text-slate-200 font-semibold text-sm transition-colors">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
                </svg>
                Cancel
              </button>
            ) : (
              <button onClick={() => scan()}
                className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full text-white font-semibold text-sm hover:opacity-90 transition-opacity shadow-lg shadow-emerald-900/30">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                </svg>
                Scan Now
              </button>
            )}
          </div>
        </div>
      </header>

      {/* ── Main ── */}
      <main className="max-w-7xl mx-auto w-full px-6 py-6 flex-1">

        {/* Market tabs */}
        <div className="flex gap-2 mb-5 items-center">
          {[
            { id: 'usa',   label: 'USA 🇺🇸' },
            { id: 'india', label: 'India 🇮🇳' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setMarket(tab.id)}
              className={`flex items-center gap-2 px-5 py-2 rounded-full text-sm font-medium transition-colors ${
                market === tab.id
                  ? 'bg-emerald-500 text-white shadow shadow-emerald-900/40'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              {tab.label}
              {results[tab.id].length > 0 && (
                <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                  market === tab.id ? 'bg-emerald-600 text-white' : 'bg-slate-700 text-slate-300'
                }`}>{results[tab.id].length}</span>
              )}
            </button>
          ))}
          <span className="ml-auto text-xs text-slate-600">~500 stocks · 8 concurrent</span>
        </div>

        {/* Progress */}
        {loading && progress && (
          <ProgressBar
            scanned={progress.scanned} total={progress.total}
            found={progress.found}    lastTicker={progress.ticker}
          />
        )}

        {/* Table */}
        <div className={loading && progress ? 'mt-4' : ''}>
          <ResultsTable
            rows={currentResults}
            selectedTicker={currentTicker}
            onSelect={t => setSelectedTicker(prev => ({ ...prev, [market]: t }))}
            market={market}
          />
        </div>

        {/* Chart */}
        {currentResults.length > 0 && (
          <div className="mt-6">
            <div className="flex items-center gap-3 mb-2">
              <label className="text-slate-400 text-xs font-medium uppercase tracking-wide">Chart</label>
              <select
                value={currentTicker || ''}
                onChange={e => setSelectedTicker(prev => ({ ...prev, [market]: e.target.value }))}
                className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                {currentResults.map(r => (
                  <option key={r.ticker} value={r.ticker}>
                    {r.ticker} — +{r.breakoutPercent}% · {r.relVolume}× vol
                  </option>
                ))}
              </select>
            </div>
            {currentTicker && <BreakoutChart key={currentTicker} ticker={currentTicker} />}
          </div>
        )}
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-slate-700 py-4 text-center text-slate-600 text-xs">
        For educational and research purposes only. Not financial advice.
      </footer>

      {/* ── Toast stack ── */}
      <Toast toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
