#!/usr/bin/env python3
"""
dash_trading_dashboard.py
Plotly Dash-based interactive trading dashboard for Trading Bramha.

Integrates all Trading Bramha modules into an interactive web interface with:
- Real-time astrology timing
- Trading signal tracking
- Volume analysis
- Financial astrology indicators
- Signal processing pipeline
- Interactive charts & controls

Inspired by: https://github.com/nitinkaushik01/Plotly_Dash_Web_App_DataScience

Usage:
  python tools/dash_trading_dashboard.py
  # Access at http://localhost:8050
"""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd

# Add project to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Import Trading Bramha modules
try:
    import astro_trading as at
    import telegram_signals as tg
    import volume_fetcher as vf
    import financial_astrology_methods as fam
    import signal_processing_engine as spe
    import live_movers as lm
    HAS_MODULES = True
except ImportError as e:
    print(f"Warning: Could not import modules: {e}")
    HAS_MODULES = False

# Sarvatobhadra Chakra engine (independent of HAS_MODULES; only needs ephem)
try:
    import sarvatobhadra_chakra as sbc
    import sbc_scoring as sbcs
    import sbc_panchang as sbcp
    import sbc_aspects as sbca
    import sbc_confluence as sbccf
    import sbc_hora as sbch
    HAS_SBC = True
except ImportError as e:
    print(f"Warning: Could not import SBC modules: {e}")
    HAS_SBC = False

# Vedic reversal calendar (structured spine of the 2026-2027 PDF; stdlib-only so it
# loads even without ephem). Powers the forward-week hypothetical reversal card.
try:
    import vedic_reversal_calendar as vrc
    HAS_VRC = True
except ImportError as e:
    print(f"Warning: Could not import vedic_reversal_calendar: {e}")
    HAS_VRC = False


class TradingDashboard:
    """Interactive Dash-based trading dashboard."""

    def __init__(self, port: int = 8050, debug: bool = True):
        """
        Initialize dashboard.

        Args:
            port: Port to run dashboard on
            debug: Enable debug mode
        """
        self.app = dash.Dash(__name__, title='Trading Bramha Dashboard')
        self.port = port
        self.debug = debug

        # Initialize data managers
        if HAS_MODULES:
            self.astro_engine = at.AstroIndicators()
            self.telegram_signals = tg.TelegramSignals()
            self.volume_fetcher = vf.VolumeFetcher(verbose=False)
            self.astrology_engine = fam.FinancialAstrologyEngine()
            self.signal_processor = spe.SignalProcessor()

        # Set up layout and callbacks
        self._setup_layout()
        self._setup_callbacks()

    def _setup_layout(self):
        """Setup dashboard layout."""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1('Trading Bramha Dashboard',
                        style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': 30}),
                html.P('Real-time trading analysis with astrology, signals, and financial indicators',
                       style={'textAlign': 'center', 'color': '#7f8c8d', 'fontSize': 14}),
            ], style={'padding': '20px', 'backgroundColor': '#ecf0f1', 'marginBottom': 20}),

            # Tab selection
            dcc.Tabs(id='tabs', value='tab-1', children=[
                # Tab 1: Astro Timing
                dcc.Tab(label='Astro Timing', value='tab-1', children=[
                    self._build_astro_tab()
                ]),

                # Tab 2: Trading Signals
                dcc.Tab(label='Trading Signals', value='tab-2', children=[
                    self._build_signals_tab()
                ]),

                # Tab 3: Volume Analysis
                dcc.Tab(label='Volume Analysis', value='tab-3', children=[
                    self._build_volume_tab()
                ]),

                # Tab 4: Financial Astrology
                dcc.Tab(label='Astrology Methods', value='tab-4', children=[
                    self._build_astrology_tab()
                ]),

                # Tab 5: Signal Processing
                dcc.Tab(label='Signal Processing', value='tab-5', children=[
                    self._build_signal_processing_tab()
                ]),

                # Tab 6: Live Movers (AI-Score × Growth quadrant)
                dcc.Tab(label='Live Movers', value='tab-6', children=[
                    self._build_movers_tab()
                ]),

                # Tab 7: Sarvatobhadra Chakra (Vedic nakshatra grid)
                dcc.Tab(label='Sarvatobhadra Chakra', value='tab-7', children=[
                    self._build_sbc_tab()
                ]),
            ])
        ], style={'fontFamily': 'Segoe UI, sans-serif', 'margin': '20px'})

    def _build_astro_tab(self):
        """Build astrology timing tab."""
        return html.Div([
            html.H3('Astro Trading Timing'),

            html.Div([
                html.Div([
                    html.Label('Select City:'),
                    dcc.Dropdown(
                        id='astro-city-select',
                        # `at` is only bound when the module import succeeded;
                        # fall back to a bare default so the app still starts.
                        options=[{'label': city, 'value': city}
                                for city in (list(at.AstroIndicators.CITIES.keys())
                                             if HAS_MODULES else ['Mumbai'])],
                        value='Mumbai'
                    )
                ], style={'width': '30%', 'display': 'inline-block', 'marginRight': '10%'}),

                html.Div([
                    html.Label('Select Date:'),
                    dcc.DatePickerSingle(
                        id='astro-date-select',
                        date=date.today()
                    )
                ], style={'width': '30%', 'display': 'inline-block'})
            ], style={'marginBottom': '20px'}),

            html.Div(id='astro-output'),

            dcc.Graph(id='astro-chart'),
        ])

    def _build_signals_tab(self):
        """Build trading signals tab."""
        return html.Div([
            html.H3('Trading Signals Tracker'),

            html.Div([
                html.Div([
                    html.Label('Signal Status:'),
                    dcc.Dropdown(
                        id='signal-status-filter',
                        options=[
                            {'label': 'All', 'value': 'all'},
                            {'label': 'Active', 'value': 'active'},
                            {'label': 'Closed', 'value': 'closed'},
                        ],
                        value='all'
                    )
                ], style={'width': '45%', 'display': 'inline-block'}),

                html.Div([
                    html.Button('Add Signal', id='add-signal-btn', n_clicks=0,
                               style={'marginTop': '25px', 'padding': '10px 20px'})
                ], style={'width': '45%', 'display': 'inline-block', 'textAlign': 'right'})
            ], style={'marginBottom': '20px'}),

            html.Div(id='signals-table'),
            html.Div(id='signals-stats'),
        ])

    def _build_volume_tab(self):
        """Build volume analysis tab."""
        return html.Div([
            html.H3('Volume Analysis'),

            html.Div([
                html.Label('Stock Symbol:'),
                dcc.Input(
                    id='volume-symbol-input',
                    type='text',
                    placeholder='Enter symbol (e.g., RELIANCE)',
                    value='RELIANCE',
                    style={'padding': '10px', 'width': '30%'}
                )
            ], style={'marginBottom': '20px'}),

            html.Div([
                html.Div(id='volume-stats', style={'width': '30%', 'display': 'inline-block', 'marginRight': '5%'}),
                html.Div(id='volume-status', style={'width': '30%', 'display': 'inline-block'}),
            ]),

            dcc.Graph(id='volume-chart'),
        ])

    def _build_astrology_tab(self):
        """Build financial astrology methods tab."""
        return html.Div([
            html.H3('Financial Astrology Methods'),

            html.Div([
                html.Div([
                    html.Label('Select Price:'),
                    dcc.Input(
                        id='fam-price-input',
                        type='number',
                        placeholder='Enter price',
                        value=1000,
                        style={'padding': '10px', 'width': '100%'}
                    )
                ], style={'width': '45%', 'display': 'inline-block'}),

                html.Div([
                    html.Label('Select Date:'),
                    dcc.DatePickerSingle(
                        id='fam-date-select',
                        date=date.today()
                    )
                ], style={'width': '45%', 'display': 'inline-block', 'marginLeft': '10%'})
            ], style={'marginBottom': '20px'}),

            html.Div(id='fam-output'),
        ])

    def _build_signal_processing_tab(self):
        """Build signal processing pipeline tab."""
        return html.Div([
            html.H3('Signal Processing Pipeline'),

            html.Div([
                html.Div([
                    html.Label('Signal Type:'),
                    dcc.RadioItems(
                        id='spe-action-select',
                        options=[
                            {'label': ' Entry', 'value': 'entry'},
                            {'label': ' Exit', 'value': 'exit'}
                        ],
                        value='entry',
                        labelStyle={'display': 'inline-block', 'marginRight': '20px'}
                    )
                ], style={'width': '45%', 'display': 'inline-block'}),

                html.Div([
                    html.Label('Position Side:'),
                    dcc.RadioItems(
                        id='spe-side-select',
                        options=[
                            {'label': ' Long', 'value': 'long'},
                            {'label': ' Short', 'value': 'short'}
                        ],
                        value='long',
                        labelStyle={'display': 'inline-block', 'marginRight': '20px'}
                    )
                ], style={'width': '45%', 'display': 'inline-block', 'marginLeft': '10%'})
            ], style={'marginBottom': '20px'}),

            html.Div([
                html.Div([
                    html.Label('Symbol:'),
                    dcc.Input(
                        id='spe-symbol-input',
                        type='text',
                        placeholder='BTCUSDT',
                        value='BTCUSDT',
                        style={'padding': '10px', 'width': '100%'}
                    )
                ], style={'width': '45%', 'display': 'inline-block'}),

                html.Div([
                    html.Label('Stop Loss %:'),
                    dcc.Input(
                        id='spe-sl-input',
                        type='number',
                        placeholder='2.0',
                        value=2.0,
                        step=0.1,
                        style={'padding': '10px', 'width': '100%'}
                    )
                ], style={'width': '45%', 'display': 'inline-block', 'marginLeft': '10%'})
            ], style={'marginBottom': '20px'}),

            html.Button('Process Signal', id='process-signal-btn', n_clicks=0,
                       style={'padding': '10px 20px', 'backgroundColor': '#3498db', 'color': 'white'}),

            html.Div(id='spe-output', style={'marginTop': '20px'}),
        ])

    def _build_movers_tab(self):
        """Live intraday movers scatter (AI-Score × %Change quadrant)."""
        return html.Div([
            html.H3('Live Top Movers — AI-Score × Growth'),
            html.P('Auto-refreshes every 5 minutes during market hours. '
                   'Bubbles: colour = quadrant, size = volume surge.',
                   style={'color': '#7f8c8d'}),
            html.Button('Refresh now', id='movers-refresh-btn', n_clicks=0,
                        style={'padding': '8px 16px', 'backgroundColor': '#27ae60',
                               'color': 'white', 'marginBottom': '10px', 'marginRight': '10px'}),
            html.Button('Write EOD snapshot', id='movers-eod-btn', n_clicks=0,
                        style={'padding': '8px 16px', 'backgroundColor': '#2980b9',
                               'color': 'white', 'marginBottom': '10px'}),
            html.Span(id='movers-status', style={'marginLeft': '15px', 'color': '#555'}),
            html.Div(id='movers-crossings', style={'marginTop': '10px', 'color': '#8B4513'}),
            dcc.Interval(id='movers-interval', interval=5 * 60 * 1000, n_intervals=0),
            dcc.Graph(id='movers-quadrant'),
            html.Div(id='movers-table', style={'marginTop': '15px'}),
        ])

    def _build_sbc_tab(self):
        """Sarvatobhadra Chakra — Vedic nakshatra grid + veda bias."""
        return html.Div([
            html.H3('Sarvatobhadra Chakra — Veda Bias & Reversal Windows'),
            html.P('Live 9x9 nakshatra grid. Malefic vs benefic veda scoring '
                   'drives the daily market bias, sector scores, and Moon '
                   'reversal windows. Positions: PyEphem + Lahiri ayanamsa.',
                   style={'color': '#7f8c8d'}),
            html.Div([
                html.Label('Session date:', style={'marginRight': '8px'}),
                dcc.DatePickerSingle(id='sbc-date-select', date=date.today()),
                html.Label('Reversal granularity:',
                           style={'marginLeft': '25px', 'marginRight': '8px'}),
                dcc.Dropdown(
                    id='sbc-granularity',
                    options=[{'label': 'Pada (~4/day)', 'value': 'pada'},
                             {'label': 'Nakshatra (~1/day)', 'value': 'nakshatra'}],
                    value='pada',
                    style={'width': '200px', 'display': 'inline-block',
                           'verticalAlign': 'middle'}),
                html.Label('Centre view:',
                           style={'marginLeft': '25px', 'marginRight': '8px'}),
                dcc.RadioItems(
                    id='sbc-view',
                    options=[{'label': ' SBC Chakra', 'value': 'chakra'},
                             {'label': ' Aspect Map', 'value': 'aspects'}],
                    value='chakra', inline=True,
                    style={'display': 'inline-block'}),
                dcc.Checklist(
                    id='sbc-vedha-blocks',
                    options=[{'label': ' Vedha Blocks', 'value': 'on'}],
                    value=[], inline=True,
                    style={'marginLeft': '20px', 'display': 'inline-block'}),
                html.Label('Vedha of:',
                           style={'marginLeft': '25px', 'marginRight': '8px'}),
                dcc.Dropdown(
                    id='sbc-planet-filter',
                    options=[{'label': lbl, 'value': val} for lbl, val in [
                        ('All planets', 'All'), ('☉ Sun', 'Sun'),
                        ('☽ Moon', 'Moon'), ('♂ Mars', 'Mars'),
                        ('☿ Mercury', 'Mercury'), ('♃ Jupiter', 'Jupiter'),
                        ('♀ Venus', 'Venus'), ('♄ Saturn', 'Saturn'),
                        ('☊ Rahu', 'Rahu'), ('☋ Ketu', 'Ketu')]],
                    value='All', clearable=False,
                    style={'width': '160px', 'display': 'inline-block',
                           'verticalAlign': 'middle'}),
                html.Button('Refresh', id='sbc-refresh-btn', n_clicks=0,
                            style={'marginLeft': '20px', 'padding': '8px 16px',
                                   'backgroundColor': '#d9b45b', 'color': '#0d0b1f',
                                   'border': 'none', 'borderRadius': '6px',
                                   'fontWeight': '600'}),
            ], style={'marginBottom': '14px', 'display': 'flex',
                      'alignItems': 'center'}),
            # Instrument confluence selector (Steps 1-4 -> actionable verdict)
            html.Div([
                html.Span('Instrument confluence:',
                          style={'color': '#d9b45b', 'fontWeight': '600',
                                 'marginRight': '10px'}),
                dcc.Dropdown(
                    id='sbc-instrument',
                    options=[{'label': s, 'value': s} for s in sbcs.SECTORS]
                    if HAS_SBC else [],
                    value='Gold',
                    style={'width': '220px', 'display': 'inline-block',
                           'verticalAlign': 'middle'}),
                html.Span('Runs Steps 1–4 for the pick → PROCEED / CAUTION / '
                          'STAND ASIDE with sizing.',
                          style={'color': '#7f8c8d', 'fontSize': '12px',
                                 'marginLeft': '10px'}),
                html.Label('Signals timeframe:',
                           style={'marginLeft': '25px', 'marginRight': '8px',
                                  'color': '#d9b45b', 'fontWeight': '600'}),
                dcc.RadioItems(
                    id='sbc-timeframe',
                    options=[{'label': f' {t}', 'value': t.lower()}
                             for t in ['Intraday', 'Swing', 'Positional']],
                    value='intraday', inline=True,
                    style={'display': 'inline-block'}),
            ], style={'marginBottom': '14px', 'display': 'flex',
                      'alignItems': 'center'}),
            # Birth Kundli inputs (optional natal overlay + Tara Bala)
            html.Div([
                html.Span('Birth Kundli (optional):',
                          style={'color': '#d9b45b', 'fontWeight': '600',
                                 'marginRight': '12px'}),
                dcc.Input(id='sbc-birth-date', type='text',
                          placeholder='Birth date YYYY-MM-DD',
                          style={'marginRight': '8px', 'padding': '6px',
                                 'width': '160px'}),
                dcc.Input(id='sbc-birth-time', type='text',
                          placeholder='Time HH:MM (IST)',
                          style={'marginRight': '8px', 'padding': '6px',
                                 'width': '130px'}),
                dcc.Input(id='sbc-birth-lat', type='number', placeholder='Lat',
                          style={'marginRight': '8px', 'padding': '6px',
                                 'width': '90px'}),
                dcc.Input(id='sbc-birth-lon', type='number', placeholder='Lon',
                          style={'marginRight': '8px', 'padding': '6px',
                                 'width': '90px'}),
                html.Span('Defaults to Delhi (28.61, 77.21) if lat/lon blank.',
                          style={'color': '#7f8c8d', 'fontSize': '12px'}),
            ], style={'marginBottom': '20px', 'display': 'flex',
                      'alignItems': 'center', 'flexWrap': 'wrap'}),
            html.Div(id='sbc-output'),
        ])

    def _setup_callbacks(self):
        """Setup Dash callbacks for interactivity."""

        @self.app.callback(
            [Output('astro-output', 'children'),
             Output('astro-chart', 'figure')],
            [Input('astro-city-select', 'value'),
             Input('astro-date-select', 'date')]
        )
        def update_astro(city, selected_date):
            if not HAS_MODULES:
                return html.Div('Modules not available'), {}

            try:
                d = datetime.strptime(selected_date, '%Y-%m-%d').date()
                astro = self.astro_engine
                astro.city = city
                timing = astro.get_trading_timing(d)

                # Summary metrics
                summary = html.Div([
                    html.Div([
                        html.H5(f"Lunar Phase: {timing['lunar_phase']['phase'].title()}"),
                        html.P(f"Illumination: {timing['lunar_phase']['illumination']}%"),
                        html.P(f"Market Intensity: {timing['market_intensity']}/100")
                    ], style={'width': '30%', 'display': 'inline-block', 'marginRight': '5%'}),

                    html.Div([
                        html.H5("Solar Timing (IST)"),
                        html.P(f"Sunrise: {timing['solar_timing']['sunrise']}"),
                        html.P(f"Sunset: {timing['solar_timing']['sunset']}"),
                    ], style={'width': '30%', 'display': 'inline-block', 'marginRight': '5%'}),

                    html.Div([
                        html.H5("Recommendations"),
                        html.Ul([html.Li(rec) for rec in timing['recommendations'][:2]])
                    ], style={'width': '30%', 'display': 'inline-block'})
                ])

                # Generate 30-day forecast chart
                dates_list = []
                illumination_list = []
                intensity_list = []

                for i in range(30):
                    d_temp = d + timedelta(days=i)
                    # real date objects: a '%m-%d' string gets parsed by Plotly
                    # as a YY-MM date and lands the axis in 2010
                    dates_list.append(d_temp)
                    lunar = astro.get_lunar_phase(d_temp)
                    illumination_list.append(lunar['illumination'])
                    timing_temp = astro.get_trading_timing(d_temp)
                    intensity_list.append(timing_temp['market_intensity'])

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=dates_list, y=illumination_list,
                    name='Lunar Illumination %',
                    line=dict(color='gold', width=2)
                ))
                fig.add_trace(go.Scatter(
                    x=dates_list, y=intensity_list,
                    name='Market Intensity',
                    line=dict(color='crimson', width=2),
                    yaxis='y2'
                ))
                fig.update_layout(
                    title='30-Day Lunar & Intensity Forecast',
                    xaxis_title='Date',
                    yaxis=dict(title='Illumination %'),
                    yaxis2=dict(title='Market Intensity', overlaying='y', side='right'),
                    hovermode='x unified',
                    height=500
                )

                return summary, fig

            except Exception as e:
                return html.Div(f'Error: {str(e)}'), {}

        @self.app.callback(
            Output('signals-table', 'children'),
            [Input('signal-status-filter', 'value')]
        )
        def update_signals(status_filter):
            if not HAS_MODULES:
                return html.Div('Modules not available')

            try:
                signals = self.telegram_signals.get_active_signals()

                rows = []
                for sig in signals:
                    rows.append(html.Tr([
                        html.Td(sig.symbol or '-'),
                        html.Td(sig.channel or '-'),
                        html.Td(sig.strategy or '-'),
                        html.Td(f"{sig.confidence}/10"),
                        html.Td(sig.status.value if hasattr(sig.status, 'value') else sig.status)
                    ]))

                return html.Table([
                    html.Thead(html.Tr([
                        html.Th('Symbol'),
                        html.Th('Channel'),
                        html.Th('Strategy'),
                        html.Th('Confidence'),
                        html.Th('Status')
                    ])),
                    html.Tbody(rows)
                ], style={'width': '100%', 'borderCollapse': 'collapse'})

            except Exception as e:
                return html.Div(f'Error loading signals: {str(e)}')

        @self.app.callback(
            Output('volume-chart', 'figure'),
            [Input('volume-symbol-input', 'value')]
        )
        def update_volume(symbol):
            if not HAS_MODULES or not symbol:
                return {}

            try:
                df = self.volume_fetcher.fetch_with_volume(symbol.upper(), days=100)
                if df is not None:
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=df.index,
                        y=df['volume'],
                        name='Volume',
                        marker=dict(color='steelblue')
                    ))
                    fig.update_layout(
                        title=f'{symbol.upper()} Volume',
                        xaxis_title='Date',
                        yaxis_title='Volume',
                        height=400
                    )
                    return fig
                else:
                    return {}
            except Exception as e:
                return {}

        @self.app.callback(
            Output('fam-output', 'children'),
            [Input('fam-price-input', 'value'),
             Input('fam-date-select', 'date')]
        )
        def update_fam(price, selected_date):
            if not HAS_MODULES or not price:
                return html.Div('Enter a price to analyze')

            try:
                d = datetime.strptime(selected_date, '%Y-%m-%d').date()
                signals = self.astrology_engine.generate_trading_signals(d, price=price)

                output = html.Div([
                    html.H5(f'McWhirter Trend: {signals["mcwhirter"]["trend"].upper()}'),
                    html.P(f'  Cycle Strength: {signals["mcwhirter"]["cycle_strength"]}/100'),

                    html.H5(f'Lunation: {signals["lunation"]["phase_type"].upper()}'),
                    html.P(f'  Illumination: {signals["lunation"]["moon_illumination"]}%'),

                    html.H5(f'Gann Price-Degree'),
                    html.P(f'  Price {price} = {signals["gann_price_degree"]["degree"]}° ({signals["gann_price_degree"]["zodiac_sign"]})'),

                    html.H5(f'Overall Bias: {signals["overall_bias"].upper()}'),
                    html.P(f'  Signal Strength: {signals["signal_strength"]}/100')
                ])

                return output

            except Exception as e:
                return html.Div(f'Error: {str(e)}')

        @self.app.callback(
            Output('spe-output', 'children'),
            [Input('process-signal-btn', 'n_clicks')],
            [dash.dependencies.State('spe-action-select', 'value'),
             dash.dependencies.State('spe-side-select', 'value'),
             dash.dependencies.State('spe-symbol-input', 'value'),
             dash.dependencies.State('spe-sl-input', 'value')]
        )
        def process_signal(n_clicks, action, side, symbol, stop_loss):
            if not HAS_MODULES or n_clicks == 0:
                return html.Div('')

            try:
                tv_signal = spe.TradingViewSignal(
                    action=action,
                    side=side,
                    symbol_code=symbol.upper(),
                    date=date.today().isoformat(),
                    hour=str(datetime.now().hour),
                    stop_loss_percent=stop_loss
                )

                result = self.signal_processor.process_signal(tv_signal, apply_csv_filter=False)

                output = html.Div([
                    html.H5(f'Status: {result["status"].upper()}'),
                    html.P(f'Signal ID: {result["signal_id"]}'),
                    html.P(f'Reason: {result["reason"]}'),

                    html.H5('Zignaly Format:') if result['zignaly_signal'] else None,
                    html.Pre(str(result.get('zignaly_signal', {})))
                ])

                return output

            except Exception as e:
                return html.Div(f'Error: {str(e)}')

        # ── Live Movers ───────────────────────────────────────────────────────
        self._prev_movers_df = None  # for quadrant-crossing detection

        @self.app.callback(
            [Output('movers-quadrant', 'figure'),
             Output('movers-table', 'children'),
             Output('movers-status', 'children'),
             Output('movers-crossings', 'children')],
            [Input('movers-interval', 'n_intervals'),
             Input('movers-refresh-btn', 'n_clicks'),
             Input('movers-eod-btn', 'n_clicks')]
        )
        def update_movers(_n, _clicks, _eod):
            if not HAS_MODULES:
                return {}, html.Div('live_movers module unavailable'), '', ''
            ctx = dash.callback_context
            trigger = ctx.triggered[0]['prop_id'] if ctx.triggered else ''
            try:
                df = lm.fetch_intraday_movers()
            except Exception as e:
                return {}, html.Div(f'Fetch error: {e}'), '', ''
            if df.empty:
                return {}, html.Div('No data (market closed or feed unavailable).'), '', ''

            lm.snapshot_movers(df)

            crossings_msg = ''
            if self._prev_movers_df is not None:
                cx = lm.detect_quadrant_crossings(self._prev_movers_df, df)
                if not cx.empty:
                    crossings_msg = '⚡ Crossed into Top: ' + ', '.join(
                        f"{r.symbol} (was {r.prev_quadrant})" for r in cx.itertuples())
            self._prev_movers_df = df.copy()

            if 'movers-eod-btn' in trigger:
                res = lm.write_eod_snapshot(df)
                crossings_msg = (crossings_msg + ' · ' if crossings_msg else '') + \
                                f"EOD written: {res.get('png', 'n/a')}"

            colours = {'Top': '#8B4513', 'Potential': '#1f77b4',
                       'Volatile': '#e74c3c', 'Growth': '#c9d648'}
            fig = go.Figure()
            for q, sub in df.groupby('quadrant'):
                fig.add_trace(go.Scatter(
                    x=sub['ai_score'], y=sub['pct_change'], mode='markers+text',
                    text=sub['symbol'], textposition='bottom center',
                    marker=dict(size=(sub['vol_surge'].clip(0.5, 5) * 8),
                                color=colours.get(q, '#888'),
                                line=dict(width=1, color='#333')),
                    name=q,
                    hovertemplate='<b>%{text}</b><br>AI: %{x}<br>Δ: %{y:.2f}%'
                                  '<br>Vol×: %{marker.size:.1f}<extra></extra>',
                ))
            fig.add_vline(x=50, line_dash='dot', line_color='#aaa')
            fig.add_hline(y=6, line_dash='dot', line_color='#aaa')
            fig.update_layout(
                xaxis_title='AI-Score', yaxis_title='Growth % (today)',
                height=600, template='plotly_white',
                title=f"Buy/Long Chart — {datetime.now().strftime('%d-%b-%Y %H:%M')}",
            )

            top = df.head(10)[['symbol', 'pct_change', 'vol_surge',
                               'rs_1y', 'ai_score', 'quadrant']].round(2)
            table = html.Table(
                [html.Tr([html.Th(c) for c in top.columns])] +
                [html.Tr([html.Td(v) for v in r])
                 for r in top.itertuples(index=False)],
                style={'width': '100%', 'borderCollapse': 'collapse'},
            )
            status = f"Refreshed {datetime.now().strftime('%H:%M:%S')} · {len(df)} symbols"
            return fig, table, status, crossings_msg

        @self.app.callback(
            Output('sbc-output', 'children'),
            [Input('sbc-date-select', 'date'),
             Input('sbc-granularity', 'value'),
             Input('sbc-refresh-btn', 'n_clicks'),
             Input('sbc-birth-date', 'value'),
             Input('sbc-birth-time', 'value'),
             Input('sbc-birth-lat', 'value'),
             Input('sbc-birth-lon', 'value'),
             Input('sbc-view', 'value'),
             Input('sbc-instrument', 'value'),
             Input('sbc-planet-filter', 'value'),
             Input('sbc-vedha-blocks', 'value'),
             Input('sbc-timeframe', 'value')]
        )
        def update_sbc(selected_date, granularity, _n,
                       birth_date, birth_time, birth_lat, birth_lon, view,
                       instrument, planet_filter, vedha_blocks, timeframe):
            if not HAS_SBC:
                return html.Div('SBC engine unavailable (PyEphem not installed).',
                                style={'color': '#c0392b'})
            try:
                return self._render_sbc(selected_date, granularity or 'pada',
                                        birth_date, birth_time,
                                        birth_lat, birth_lon, view or 'chakra',
                                        instrument or 'Gold',
                                        planet_filter or 'All',
                                        bool(vedha_blocks),
                                        timeframe or 'intraday')
            except Exception as e:  # pragma: no cover
                return html.Div(f'SBC error: {e}', style={'color': '#c0392b'})

    # ----- Sarvatobhadra Chakra rendering helpers -------------------------

    _SBC_GOLD = '#d9b45b'
    _SBC_RED = '#e0524f'
    _SBC_GREEN = '#3fb57a'
    _SBC_DIM = '#6c6790'
    _SBC_PANEL = '#171334'
    _SBC_BG = '#0d0b1f'

    def _sbc_cell_color(self, p):
        if p >= 1.0:
            return '#123d29'
        if p > 0:
            return '#16261f'
        if p <= -1.0:
            return '#3d1717'
        if p < 0:
            return '#261414'
        return self._SBC_PANEL

    def _sbc_chakra_figure(self, board, planets, pressure,
                           planet_filter='All'):
        """Draw the classical square chakra as an interactive Plotly figure.

        Every cell, glyph, and vedha line is placed from the real sbc_grid
        coordinates + geometric rays — nothing is hand-positioned. When
        `planet_filter` names a single graha, only that planet's vedha rays are
        drawn (highlighted), and the nakshatras it pierces are outlined.
        """
        import sbc_grid as grid
        gold, red, green, dim = (self._SBC_GOLD, self._SBC_RED,
                                 self._SBC_GREEN, self._SBC_DIM)
        fig = go.Figure()
        one = planet_filter if planet_filter and planet_filter != 'All' else None

        def xy(coord):                       # grid (row,col) -> plot (x,y)
            return coord[1], (grid.GRID_N - 1 - coord[0])

        occ = {}
        for n, ps in planets.items():
            occ.setdefault(ps.nakshatra, []).append(sbc.PLANET_GLYPH.get(n, n[0]))

        ring_bg = {0: None, 1: '#141031', 2: '#191634', 3: '#1d1940', 4: '#241f4a'}
        # cells
        for coord, cell in board.cells.items():
            x, y = xy(coord)
            fill = ring_bg.get(cell.ring, '#141031')
            line_c = '#2a2550'
            if cell.ctype == grid.CellType.NAKSHATRA:
                p = pressure.get(sbc.NAKSHATRAS.index(cell.label), 0.0) \
                    if cell.label in sbc.NAKSHATRAS else 0.0
                fill = self._sbc_cell_color(p)
                if occ.get(cell.label):
                    line_c = gold
            elif cell.ctype == grid.CellType.RASHI:
                fill = '#1a2440'
            elif cell.ctype == grid.CellType.VOWEL:
                fill = '#20183a'
            fig.add_shape(type='rect', x0=x - 0.5, y0=y - 0.5,
                          x1=x + 0.5, y1=y + 0.5, fillcolor=fill,
                          line=dict(color=line_c, width=1), layer='below')
            # label
            if cell.ctype == grid.CellType.NAKSHATRA:
                glyphs = ''.join(occ.get(cell.label, []))
                txt = (f"<b>{glyphs}</b><br>" if glyphs else "") + cell.label[:4]
                tcolor = gold if glyphs else '#cfc9f0'
            elif cell.ctype == grid.CellType.RASHI:
                txt, tcolor = cell.label[:3], '#8fb0e8'
            elif cell.ctype in (grid.CellType.VOWEL,):
                txt, tcolor = cell.label, dim
            elif cell.ctype == grid.CellType.CENTER:
                txt, tcolor = 'Poorna<br>Sat', gold
            else:
                txt, tcolor = '', dim
            if txt:
                fig.add_annotation(x=x, y=y, text=txt, showarrow=False,
                                   font=dict(size=9, color=tcolor),
                                   align='center')

        # vedha rays (filtered to one planet if requested) + pierced-cell marks
        ray_dash = {'sammukha': 'solid', 'vama': 'dot', 'dakshina': 'dash'}
        pierced = set()                      # coords pierced by the selected planet
        for n, ps in planets.items():
            if one and n != one:
                continue
            casts_all = n in sbcs.CASTS_ALL
            fast = abs(ps.speed_deg_per_day) > sbcs.FAST_THRESHOLD.get(n, 0.05)
            dirs = grid.active_directions(ps.retrograde, fast, casts_all)
            src = board.coord_of(ps.nakshatra)
            if src is None:
                continue
            col = red if ps.nature == 'malefic' else green
            width = 2.6 if one else 1.4
            op = 0.9 if one else 0.55
            for d in dirs:
                a, b = grid.ray_segment(src, d)
                (x0, y0), (x1, y1) = xy(a), xy(b)
                fig.add_shape(type='line', x0=x0, y0=y0, x1=x1, y1=y1,
                              line=dict(color=col, width=width,
                                        dash=ray_dash[d]), opacity=op,
                              layer='below')
                if one:
                    for c in grid.vedha_targets(board, src, d):
                        if board.nakshatra_at_coord(c):
                            pierced.add(c)
        # outline nakshatras the selected planet pierces
        for c in pierced:
            x, y = xy(c)
            fig.add_shape(type='rect', x0=x - 0.5, y0=y - 0.5, x1=x + 0.5,
                          y1=y + 0.5, fillcolor='rgba(0,0,0,0)',
                          line=dict(color=gold, width=2), layer='above')

        # planet markers (hover shows detail)
        px, py, ptext = [], [], []
        for n, ps in planets.items():
            src = board.coord_of(ps.nakshatra)
            if src is None:
                continue
            x, y = xy(src)
            px.append(x)
            py.append(y)
            mot = 'Rx' if ps.retrograde else 'Direct'
            ptext.append(f"{sbc.PLANET_GLYPH.get(n,'')} {n} · {ps.nakshatra} "
                         f"p{ps.pada} · {mot} · {ps.nature}")
        fig.add_trace(go.Scatter(
            x=px, y=py, mode='markers',
            marker=dict(size=6, color=gold, line=dict(color='#0d0b1f', width=1)),
            text=ptext, hoverinfo='text', name='planets'))

        n = grid.GRID_N
        fig.update_xaxes(visible=False, range=[-0.7, n - 0.3],
                         constrain='domain')
        fig.update_yaxes(visible=False, range=[-0.7, n - 0.3],
                         scaleanchor='x', scaleratio=1)
        fig.update_layout(
            height=620, margin=dict(l=10, r=10, t=30, b=10),
            paper_bgcolor=self._SBC_BG, plot_bgcolor=self._SBC_BG,
            showlegend=False,
            annotations=list(fig.layout.annotations) + [
                dict(x=(n - 1) / 2, y=n - 0.15, text='EAST', showarrow=False,
                     font=dict(size=11, color=dim)),
                dict(x=(n - 1) / 2, y=-0.55, text='WEST', showarrow=False,
                     font=dict(size=11, color=dim)),
                dict(x=-0.55, y=(n - 1) / 2, text='NORTH', showarrow=False,
                     textangle=-90, font=dict(size=11, color=dim)),
                dict(x=n - 0.45, y=(n - 1) / 2, text='SOUTH', showarrow=False,
                     textangle=90, font=dict(size=11, color=dim)),
            ])
        return fig

    def _aspect_map_figure(self, planets):
        """Zodiac wheel with planets + graha-drishti aspect lines."""
        import math
        gold, red, green, dim = (self._SBC_GOLD, self._SBC_RED,
                                 self._SBC_GREEN, self._SBC_DIM)
        fig = go.Figure()

        def ang(lon):                        # sidereal lon -> radians (Aries=right)
            return math.radians(lon)

        def pt(lon, r):
            a = ang(lon)
            return r * math.cos(a), r * math.sin(a)

        # rashi ring: 12 spokes + labels
        for k in range(12):
            x0, y0 = pt(k * 30, 0.98)
            x1, y1 = pt(k * 30, 1.12)
            fig.add_shape(type='line', x0=x0, y0=y0, x1=x1, y1=y1,
                          line=dict(color='#2a2550', width=1))
            lx, ly = pt(k * 30 + 15, 1.05)
            fig.add_annotation(x=lx, y=ly, text=sbca.RASHIS[k][:3],
                               showarrow=False, font=dict(size=9, color=dim))
        # outer + inner circle
        circle = [pt(d, 0.98) for d in range(0, 361, 4)]
        fig.add_trace(go.Scatter(
            x=[c[0] for c in circle], y=[c[1] for c in circle], mode='lines',
            line=dict(color='#2a2550', width=1), hoverinfo='skip',
            showlegend=False))

        # planet screen positions (at r=0.8)
        ppos = {n: pt(ps.sidereal_lon, 0.8) for n, ps in planets.items()}

        # aspect lines
        for a in sbca.compute_aspects(planets):
            x0, y0 = ppos[a.source]
            x1, y1 = ppos[a.target]
            col = red if a.nature == 'malefic' else green
            fig.add_shape(type='line', x0=x0, y0=y0, x1=x1, y1=y1,
                          line=dict(color=col, width=1.2,
                                    dash='dot' if a.special else 'solid'),
                          opacity=0.5, layer='below')

        # planet markers
        px, py, ptext, pmark = [], [], [], []
        for n, ps in planets.items():
            x, y = ppos[n]
            px.append(x)
            py.append(y)
            mot = 'Rx' if ps.retrograde else 'D'
            asp = ', '.join(t for t in sbca.aspect_summary(planets)[n]) or 'none'
            ptext.append(f"{sbc.PLANET_GLYPH.get(n,'')} {n} · "
                         f"{ps.nakshatra} · {mot}<br>aspects: {asp}")
            pmark.append(sbc.PLANET_GLYPH.get(n, n[0]))
        fig.add_trace(go.Scatter(
            x=px, y=py, mode='markers+text', text=pmark,
            textposition='middle center', textfont=dict(size=13, color=gold),
            marker=dict(size=20, color='#120f2b',
                        line=dict(color=gold, width=1)),
            hovertext=ptext, hoverinfo='text', showlegend=False))

        fig.update_xaxes(visible=False, range=[-1.25, 1.25])
        fig.update_yaxes(visible=False, range=[-1.25, 1.25],
                         scaleanchor='x', scaleratio=1)
        fig.update_layout(height=560, margin=dict(l=10, r=10, t=10, b=10),
                          paper_bgcolor=self._SBC_BG, plot_bgcolor=self._SBC_BG,
                          showlegend=False)
        return fig

    # North-Indian kundli house anchor points in a unit square (0..1).
    _KUNDLI_HOUSE_XY = {
        1: (0.50, 0.75), 2: (0.25, 0.90), 3: (0.10, 0.75), 4: (0.25, 0.50),
        5: (0.10, 0.25), 6: (0.25, 0.10), 7: (0.50, 0.25), 8: (0.75, 0.10),
        9: (0.90, 0.25), 10: (0.75, 0.50), 11: (0.90, 0.75), 12: (0.75, 0.90),
    }

    def _kundli_figure(self, natal):
        """North-Indian birth chart (fixed houses, whole-sign from Lagna)."""
        import sbc_natal as _natal
        gold, dim = self._SBC_GOLD, self._SBC_DIM
        fig = go.Figure()
        # frame: outer square, both diagonals, midpoint diamond
        seg = [((0, 0), (1, 0)), ((1, 0), (1, 1)), ((1, 1), (0, 1)),
               ((0, 1), (0, 0)), ((0, 0), (1, 1)), ((0, 1), (1, 0)),
               ((0.5, 0), (1, 0.5)), ((1, 0.5), (0.5, 1)),
               ((0.5, 1), (0, 0.5)), ((0, 0.5), (0.5, 0))]
        for (x0, y0), (x1, y1) in seg:
            fig.add_shape(type='line', x0=x0, y0=y0, x1=x1, y1=y1,
                          line=dict(color='#2a2550', width=1))
        # planets grouped by house
        by_house = {}
        for name, h in natal.house_of.items():
            by_house.setdefault(h, []).append(sbc.PLANET_GLYPH.get(name, name[0]))
        for h, (x, y) in self._KUNDLI_HOUSE_XY.items():
            rashi_idx = (natal.lagna_rashi_index + h - 1) % 12
            fig.add_annotation(x=x, y=y + 0.06, text=str(rashi_idx + 1),
                               showarrow=False,
                               font=dict(size=9, color=dim))
            glyphs = ' '.join(by_house.get(h, []))
            if glyphs:
                fig.add_annotation(x=x, y=y - 0.02, text=glyphs, showarrow=False,
                                   font=dict(size=13, color=gold))
        fig.add_annotation(x=0.5, y=0.5, text='Lagna',
                           showarrow=False, font=dict(size=8, color=dim))
        fig.update_xaxes(visible=False, range=[-0.05, 1.05])
        fig.update_yaxes(visible=False, range=[-0.05, 1.05],
                         scaleanchor='x', scaleratio=1)
        fig.update_layout(height=360, margin=dict(l=5, r=5, t=5, b=5),
                          paper_bgcolor=self._SBC_BG, plot_bgcolor=self._SBC_BG,
                          showlegend=False)
        return fig

    def _sbc_natal_panel(self, birth_date, birth_time, birth_lat, birth_lon,
                         today_moon_nak):
        """Birth Kundli + Tara Bala personal overlay (or a prompt if no birth)."""
        import sbc_natal as _natal
        gold, red, green, dim = (self._SBC_GOLD, self._SBC_RED,
                                 self._SBC_GREEN, self._SBC_DIM)
        panel_style = {'backgroundColor': self._SBC_PANEL,
                       'border': '1px solid #2a2550', 'borderRadius': '12px',
                       'padding': '14px 18px', 'marginBottom': '14px'}
        h_style = {'color': gold, 'letterSpacing': '.1em', 'fontSize': '13px',
                   'textTransform': 'uppercase', 'marginBottom': '8px'}
        if not birth_date:
            return html.Div([
                html.Div('Birth Kundli — Personal Overlay', style=h_style),
                html.P('Enter a birth date (and optionally time + place) above '
                       'to compute the natal chart, Lagna, and today’s '
                       'Tara Bala trade-timing filter for that native.',
                       style={'color': dim, 'fontSize': '13px'}),
            ], style=panel_style)
        # parse inputs
        try:
            bd = datetime.strptime(birth_date.strip(), '%Y-%m-%d')
        except Exception:
            return html.Div([html.Div('Birth Kundli', style=h_style),
                             html.P(f'Bad birth date "{birth_date}" — use '
                                    'YYYY-MM-DD.', style={'color': red})],
                            style=panel_style)
        hh, mm = 12, 0
        if birth_time:
            try:
                hh, mm = [int(x) for x in birth_time.strip().split(':')[:2]]
            except Exception:
                pass
        lat = float(birth_lat) if birth_lat not in (None, '') else 28.61
        lon = float(birth_lon) if birth_lon not in (None, '') else 77.21
        birth_ist = bd.replace(hour=hh, minute=mm)
        birth_utc = birth_ist - sbc.IST_OFFSET
        natal = _natal.compute_natal(birth_utc, lat, lon)
        tb = _natal.tara_bala(natal.moon_nakshatra, today_moon_nak)

        tcolor = {'green': green, 'yellow': gold, 'red': red}[tb.color]
        tara_card = html.Div([
            html.Div('Tara Bala — Today for this Native', style=h_style),
            html.Span(tb.verdict, style={'fontSize': '24px', 'fontWeight': '700',
                                         'color': tcolor}),
            html.Span(f'  {tb.tara_name} (tara {tb.tara})',
                      style={'color': '#cfc9f0'}),
            html.Br(),
            html.Span(f'{tb.meaning}. Count {tb.count} from birth star '
                      f'{natal.moon_nakshatra} → today’s Moon '
                      f'{today_moon_nak}.',
                      style={'color': dim, 'fontSize': '13px'}),
            html.Br(),
            html.Span('▲ FAVOURABLE = trade · CAUTION = trade light · '
                      'AVOID = sit out / defensive only.',
                      style={'color': dim, 'fontSize': '12px'}),
        ], style={'border': f'1px solid {tcolor}', 'borderRadius': '10px',
                  'padding': '12px 14px', 'backgroundColor': '#120f2b',
                  'marginBottom': '12px'})

        info = html.Div([
            html.Span(f'Lagna: {natal.lagna_rashi} ',
                      style={'color': gold, 'fontWeight': '600'}),
            html.Span(f'({natal.lagna_sidereal:.1f}° · {natal.lagna_nakshatra})   ',
                      style={'color': dim}),
            html.Span(f'Birth Moon: {natal.moon_nakshatra}',
                      style={'color': '#cfc9f0'}),
        ], style={'marginBottom': '10px', 'fontSize': '13px'})

        kundli = dcc.Graph(figure=self._kundli_figure(natal),
                           config={'displayModeBar': False})

        return html.Div([
            html.Div('Birth Kundli — Personal Overlay', style=h_style),
            tara_card, info,
            html.Div([
                html.Div(kundli, style={'width': '48%', 'display': 'inline-block',
                                        'verticalAlign': 'top'}),
                html.Div(html.P('North-Indian chart · fixed houses, sign '
                                'numbers rotate from the Lagna (house 1). '
                                'Glyphs show natal planet placements. '
                                'Numbers = rashi (1=Aries).',
                                style={'color': dim, 'fontSize': '12px'}),
                         style={'width': '50%', 'display': 'inline-block',
                                'verticalAlign': 'top', 'paddingLeft': '2%'}),
            ]),
        ], style=panel_style)

    # grouped sector map (label -> representative instrument for nama score)
    _GROUPED_SECTORS = [
        ('NIFTY 50 & BANKNIFTY', 'NIFTY 50'),
        ('Banking & Financials', 'Bank NIFTY'),
        ('IT & Technology', 'NIFTY IT'),
        ('FMCG, Luxury & Auto', 'NIFTY FMCG'),
        ('Defense, Metals & Energy', 'NIFTY Metal'),
        ('Pharma & Healthcare', 'NIFTY Pharma'),
        ('Realty & Construction', 'NIFTY Auto'),
        ('PSU & Energy (India)', 'NIFTY Energy'),
        ('XAUUSD — Gold', 'Gold'),
        ('XAGUSD — Silver', 'Silver'),
        ('BTC & Crypto', 'Bitcoin'),
        ('Currencies (INR/DXY/FX)', 'USD/INR'),
    ]

    def _astro_factors(self, planets, panchang):
        """The astro signal cards: (label, detail, sentiment green/red/neutral)."""
        import sbc_confluence as _cf
        out = []
        # Jupiter dignity (own Sag/Pis, exalt Cancer, debil Capricorn)
        jr = int(planets['Jupiter'].sidereal_lon // 30) % 12
        if jr in (8, 11) or jr == 3:
            out.append(('Jupiter in own/exalted sign',
                        'Bullish undercurrent', 'green'))
        elif jr == 9:
            out.append(('Jupiter debilitated (Capricorn)',
                        'Bearish drag on breadth', 'red'))
        else:
            out.append(('Jupiter neutral dignity',
                        'No strong Guru bias', 'neutral'))
        # weekday (benefic-lord day favourable)
        vlord = sbch.WEEKDAY_LORD[panchang.when_ist.weekday()]
        if vlord in sbch.BENEFIC:
            out.append((f'{panchang.vara} — {vlord} day',
                        'Favourable market day', 'green'))
        else:
            out.append((f'{panchang.vara} — {vlord} day',
                        'Malefic-lord day, stay nimble', 'red'))
        # tithi
        if panchang.tithi_name.endswith('Ashtami') and panchang.paksha == 'Krishna':
            out.append(('Krishna Ashtami',
                        'Inauspicious tithi, exercise caution', 'red'))
        else:
            out.append((panchang.tithi_name, 'Tithi within normal band',
                        'neutral'))
        # current nakshatra nature
        nat = _cf.NAKSHATRA_NATURE.get(panchang.nakshatra, 'Chara')
        tend = _cf.NATURE_TENDENCY[nat]
        senti = 'green' if tend > 0.1 else 'red' if tend < 0 else 'neutral'
        out.append((f'{panchang.nakshatra} ({_cf.NATURE_LABEL[nat]})',
                    'Volatile / caution nakshatra' if tend < 0
                    else 'Supportive nakshatra' if tend > 0.1
                    else 'Neutral nakshatra', senti))
        # bhadra
        if panchang.bhadra_active:
            out.append(('Bhadra active',
                        'Avoid major positions, high-risk period', 'red'))
        else:
            out.append(('No Bhadra', 'Panchang clear', 'green'))
        return out

    def _sbc_trading_signals_panel(self, planets, vedas, bias, panchang,
                                   windows, now_ist, timeframe, day):
        """Trading Signals — astro score, factor cards, reversal zone,
        sector map (/10) and best-time hora windows, per timeframe."""
        gold, red, green, dim = (self._SBC_GOLD, self._SBC_RED,
                                 self._SBC_GREEN, self._SBC_DIM)
        panel_style = {'backgroundColor': self._SBC_PANEL,
                       'border': '1px solid #2a2550', 'borderRadius': '12px',
                       'padding': '14px 18px', 'marginBottom': '14px'}
        h_style = {'color': gold, 'letterSpacing': '.1em', 'fontSize': '13px',
                   'textTransform': 'uppercase', 'marginBottom': '8px'}
        sc = {'green': green, 'red': red, 'neutral': dim}

        factors = self._astro_factors(planets, panchang)
        score = sum(1 if f[2] == 'green' else -1 if f[2] == 'red' else 0
                    for f in factors)
        verdict = ('BULLISH' if score >= 2 else 'BEARISH' if score <= -2
                   else 'NEUTRAL')
        vcolor = {'BULLISH': green, 'BEARISH': red, 'NEUTRAL': gold}[verdict]

        header = html.Div([
            html.Div(verdict, style={'textAlign': 'center', 'color': vcolor,
                                     'fontWeight': '700', 'fontSize': '22px'}),
            html.Div(f'Astro Score: {score:+d} · {panchang.vara} · '
                     f'{panchang.tithi_name} · {panchang.nakshatra} Nak · '
                     f'{timeframe.title()}',
                     style={'textAlign': 'center', 'color': dim,
                            'fontSize': '12px', 'marginBottom': '10px'}),
        ])

        factor_cards = [html.Div([
            html.Span('●', style={'color': sc[f[2]], 'marginRight': '8px'}),
            html.Span(f[0], style={'color': '#cfc9f0', 'fontWeight': '600',
                                   'fontSize': '13px'}),
            html.Br(),
            html.Span(f[1], style={'color': dim, 'fontSize': '12px',
                                   'marginLeft': '18px'}),
        ], style={'border': '1px solid #2a2550', 'borderRadius': '8px',
                  'padding': '8px 11px', 'marginBottom': '6px',
                  'backgroundColor': '#120f2b'}) for f in factors]

        # reversal zone
        nxt = next((w for w in windows if w.end_ist >= now_ist), None)
        rev = None
        if nxt is not None:
            rev = html.Div([
                html.Span('⚡ REVERSAL ZONE — possible bias shift approaching',
                          style={'color': gold, 'fontWeight': '700'}),
                html.Br(),
                html.Span(f'Next window {nxt.start_ist:%H:%M}–{nxt.end_ist:%H:%M} '
                          f'· {nxt.from_nakshatra} → {nxt.to_nakshatra}',
                          style={'color': '#e8d9a0', 'fontSize': '13px'}),
                html.Br(),
                html.Span(f'{bias.malefic_count} malefic vedhas active · '
                          'markets pivot ±10 min around hora/nak changes — '
                          'use as entry-timing filter, not standalone signal',
                          style={'color': dim, 'fontSize': '11px'}),
            ], style={'border': f'1px solid {red}', 'borderRadius': '10px',
                      'padding': '10px 14px', 'margin': '10px 0',
                      'backgroundColor': '#1f1420'})

        # best-time hora windows (intraday)
        best = sbch.best_windows(day if isinstance(day, datetime)
                                 else datetime(day.year, day.month, day.day))
        hora_row = None
        if timeframe == 'intraday' and best:
            chips = [html.Span(
                f'{h.start_ist:%H:%M}–{h.end_ist:%H:%M} '
                f'{sbch.GLYPH[h.lord]}{h.lord}',
                style={'border': f'1px solid {green}', 'borderRadius': '10px',
                       'padding': '3px 9px', 'margin': '3px', 'color': green,
                       'fontSize': '12px', 'display': 'inline-block'})
                for h in best]
            hora_row = html.Div([
                html.Div('Best entry windows (benefic hora)', style=h_style),
                html.Div(chips)], style={'marginTop': '10px'})

        # today's sector map (/10)
        sscores = {s.sector: s for s in sbcs.sector_scores(
            vedas, [i for _, i in self._GROUPED_SECTORS])}
        chips = []
        for label, inst in self._GROUPED_SECTORS:
            s = sscores.get(inst)
            score10 = round(((s.score if s else 0) + 1) / 2 * 10)
            arrow, acol = (('▲', green) if score10 > 5 else
                           ('▼', red) if score10 < 5 else ('—', dim))
            chips.append(html.Span([
                html.Span(arrow, style={'color': acol, 'fontWeight': '700'}),
                html.Span(f' {label} ', style={'color': '#cfc9f0'}),
                html.Span(f'{score10}/10', style={'color': acol,
                                                  'fontWeight': '600'}),
            ], style={'border': f'1px solid {acol}', 'borderRadius': '10px',
                      'padding': '3px 9px', 'margin': '3px',
                      'fontSize': '12px', 'display': 'inline-block',
                      'backgroundColor': '#120f2b'}))
        sector_map = html.Div([
            html.Div('Today’s Sector Map', style=h_style),
            html.Div(chips)], style={'marginTop': '10px'})

        return html.Div([
            html.Div('Trading Signals', style=h_style),
            header,
            html.Div(factor_cards),
            rev if rev else '',
            hora_row if hora_row else '',
            sector_map,
            html.P('Astro-technical read — planetary dignities, panchang and '
                   'vedha projections. Timing filter, not standalone advice.',
                   style={'color': dim, 'fontSize': '11px', 'marginTop': '8px'}),
        ], style=panel_style)

    def _sbc_badra_grid_panel(self, planets, vedas, bias, panchang,
                              vedha_blocks):
        """108 Badra Grid — 27 nakshatra chip-cards + final confluence call.

        Each card: the nakshatra, the planets pressing vedha on it (glyphs,
        coloured by nature), a net malefic/benefic marker (▲/▼) and ★ if a
        planet occupies it. With Vedha Blocks OFF (default) the malefic/benefic
        projection is shown per card; ON annotates cards where obstruction
        (malefic) dominates as 'blocked'.
        """
        gold, red, green, dim = (self._SBC_GOLD, self._SBC_RED,
                                 self._SBC_GREEN, self._SBC_DIM)
        panel_style = {'backgroundColor': self._SBC_PANEL,
                       'border': '1px solid #2a2550', 'borderRadius': '12px',
                       'padding': '14px 18px', 'marginBottom': '14px'}
        h_style = {'color': gold, 'letterSpacing': '.1em', 'fontSize': '13px',
                   'textTransform': 'uppercase', 'marginBottom': '8px'}

        # per-nakshatra: casters (planet,nature,weight), net, occupant
        casters = {n: [] for n in sbc.NAKSHATRAS}
        net = {n: 0.0 for n in sbc.NAKSHATRAS}
        support = {n: 0 for n in sbc.NAKSHATRAS}
        obstruct = {n: 0 for n in sbc.NAKSHATRAS}
        for v in vedas:
            if v.target_nakshatra not in casters:
                continue
            casters[v.target_nakshatra].append((v.planet, v.nature))
            net[v.target_nakshatra] += (v.weight if v.nature == 'benefic'
                                        else -v.weight)
            if v.nature == 'benefic':
                support[v.target_nakshatra] += 1
            else:
                obstruct[v.target_nakshatra] += 1
        occ = {n: [] for n in sbc.NAKSHATRAS}
        for name, ps in planets.items():
            occ[ps.nakshatra].append(name)

        cards = []
        for nak in sbc.NAKSHATRAS:
            p = net[nak]
            if p > 0:
                cc, marker = green, '▲'
            elif p < 0:
                cc, marker = red, '▼'
            else:
                cc, marker = dim, '·'
            occupied = bool(occ[nak])
            star = '★' if occupied else ''
            blocked = vedha_blocks and obstruct[nak] > support[nak]
            # pressing-planet glyphs coloured by nature
            seen = {}
            for pl, nat in casters[nak]:
                seen[pl] = nat
            glyph_row = [
                html.Span(sbc.PLANET_GLYPH.get(pl, pl[0]),
                          style={'color': red if nat == 'malefic' else green,
                                 'fontSize': '13px', 'marginRight': '2px'})
                for pl, nat in seen.items()]
            occ_glyphs = ''.join(sbc.PLANET_GLYPH.get(o, o[0]) for o in occ[nak])
            cards.append(html.Div([
                html.Div([
                    html.Span(nak[:3], style={'color': '#cfc9f0',
                                              'fontWeight': '600',
                                              'fontSize': '12px'}),
                    html.Span(occ_glyphs, style={'float': 'right',
                                                 'color': gold}),
                ]),
                html.Div(glyph_row or [html.Span('·', style={'color': dim})],
                         style={'margin': '3px 0', 'minHeight': '16px'}),
                html.Div([
                    html.Span(f'{marker}{star}',
                              style={'color': cc, 'fontWeight': '700'}),
                    html.Span(f' {p:+.1f}',
                              style={'color': dim, 'fontSize': '10px'}),
                    (html.Span(' ⓧ blocked',
                               style={'color': red, 'fontSize': '9px',
                                      'marginLeft': '4px'})
                     if blocked else ''),
                ]),
            ], style={
                'border': f'1px solid #2a2550', 'borderLeft': f'4px solid {cc}',
                'borderRadius': '8px', 'padding': '7px 9px',
                'backgroundColor': ('#241016' if p < 0 else
                                    '#0f2418' if p > 0 else '#141031')}))

        grid = html.Div(cards, style={
            'display': 'grid',
            'gridTemplateColumns': 'repeat(auto-fill, minmax(96px, 1fr))',
            'gap': '8px'})

        # info cards: current nakshatra, lord, day status, incoming vedha
        cur = panchang.nakshatra
        lord = sbc.nakshatra_lord(cur)
        day_status = ('Badra Active' if panchang.bhadra_active else 'Clear')
        info = html.Div([
            self._sbc_info_card('Current Nakshatra', cur, '#cfc9f0'),
            self._sbc_info_card('Nakshatra Lord',
                                f'{sbc.PLANET_GLYPH.get(lord,"")} {lord}',
                                '#cfc9f0'),
            self._sbc_info_card('Current Day Status', day_status,
                                red if panchang.bhadra_active else green),
            self._sbc_info_card(
                'Incoming Vedha',
                f'Support {support[cur]} · Obstruction {obstruct[cur]}',
                red if obstruct[cur] > support[cur] else green),
        ], style={'display': 'grid',
                  'gridTemplateColumns': 'repeat(auto-fit, minmax(160px, 1fr))',
                  'gap': '8px', 'marginTop': '12px'})

        # final confluence call (rolled up from the grid = market bias)
        vcolor = {'BEARISH': red, 'BULLISH': green, 'MIXED': gold}[bias.label]
        final = html.Div([
            html.Span('FINAL CONFLUENCE CALL  ', style={'color': dim,
                                                        'fontSize': '11px'}),
            html.Span(bias.label, style={'color': vcolor, 'fontWeight': '700',
                                         'fontSize': '18px'}),
            html.Span(f'  {bias.malefic_count} malefic vs {bias.benefic_count} '
                      f'benefic projections · net {bias.net:+.2f}'
                      + ('  · Badra blocks new positions'
                         if panchang.bhadra_active else ''),
                      style={'color': dim, 'fontSize': '12px'}),
        ], style={'border': f'2px solid {vcolor}', 'borderRadius': '10px',
                  'padding': '10px 14px', 'marginTop': '12px',
                  'backgroundColor': '#120f2b'})

        return html.Div([
            html.Div([
                html.Span('108 Badra Grid', style=h_style),
                html.Span(f'Vedha Blocks: {"ON" if vedha_blocks else "OFF"}',
                          style={'float': 'right', 'color': gold,
                                 'fontSize': '11px',
                                 'border': f'1px solid {gold}',
                                 'borderRadius': '10px', 'padding': '2px 8px'}),
            ]),
            grid, info, final,
            html.P('Each cell: planet glyphs = grahas casting vedha on that '
                   'nakshatra (red malefic / green benefic) · ▲ net benefic · '
                   '▼ net malefic · ★ planet-occupied. Final call rolls the '
                   'whole grid into the day bias.',
                   style={'color': dim, 'fontSize': '11px', 'marginTop': '8px'}),
        ], style=panel_style)

    def _sbc_info_card(self, label, value, vcolor):
        return html.Div([
            html.Div(label, style={'color': self._SBC_DIM, 'fontSize': '10px',
                                   'textTransform': 'uppercase',
                                   'letterSpacing': '.06em'}),
            html.Div(value, style={'color': vcolor, 'fontWeight': '600',
                                   'fontSize': '14px', 'marginTop': '2px'}),
        ], style={'border': '1px solid #2a2550', 'borderRadius': '8px',
                  'padding': '8px 11px', 'backgroundColor': '#120f2b'})

    def _sbc_confluence_panel(self, instrument, planets, vedas, bias,
                              panchang, windows, now_ist):
        """Per-instrument Steps 1-4 confluence -> actionable verdict card."""
        gold, red, green, dim = (self._SBC_GOLD, self._SBC_RED,
                                 self._SBC_GREEN, self._SBC_DIM)
        panel_style = {'backgroundColor': self._SBC_PANEL,
                       'border': '1px solid #2a2550', 'borderRadius': '12px',
                       'padding': '14px 18px', 'marginBottom': '14px'}
        h_style = {'color': gold, 'letterSpacing': '.1em', 'fontSize': '13px',
                   'textTransform': 'uppercase', 'marginBottom': '8px'}
        c = sbccf.evaluate(instrument, planets, vedas, bias, panchang)

        vcolor = {'PROCEED': green, 'PROCEED (guarded)': green,
                  'CAUTION': gold, 'STAND ASIDE': red}.get(c.verdict, gold)
        dcolor = {'BULLISH': green, 'BEARISH': red}.get(c.direction, dim)
        # next reversal window (timing gate) + REV WIN tag
        nxt = next((w for w in windows if w.end_ist >= now_ist), None)
        rev_tag = None
        if nxt is not None:
            live = nxt.start_ist <= now_ist <= nxt.end_ist
            mins = int((nxt.center_ist - now_ist).total_seconds() // 60)
            rev_tag = html.Span(
                ('● REV WIN LIVE' if live else f'REV WIN in {mins}m'),
                style={'color': gold, 'border': f'1px solid {gold}',
                       'borderRadius': '10px', 'padding': '2px 8px',
                       'fontSize': '12px', 'marginLeft': '10px'})

        verdict_row = html.Div([
            html.Span(f'{instrument} ({c.nakshatra})',
                      style={'color': '#cfc9f0', 'fontWeight': '600',
                             'marginRight': '12px'}),
            html.Span(c.verdict, style={'fontSize': '22px', 'fontWeight': '700',
                                        'color': vcolor}),
            html.Span(f'  {c.green}/4 GREEN · {c.size_band}',
                      style={'color': dim, 'marginLeft': '8px'}),
            html.Span(f'  ▸ {c.direction}',
                      style={'color': dcolor, 'fontWeight': '600',
                             'marginLeft': '8px'}),
            rev_tag if rev_tag else '',
        ], style={'marginBottom': '4px'})

        sub = html.Div(
            (f'Safe-haven inversion applies · ' if c.safe_haven else '') +
            f'{c.green} pass · {c.caution} caution · {c.fail} fail'
            + (f' · reversal window {nxt.start_ist:%H:%M}–{nxt.end_ist:%H:%M} '
               '(markets pivot ±10 min)' if nxt else ''),
            style={'color': dim, 'fontSize': '12px', 'marginBottom': '10px'})

        badge = {sbccf.PASS: green, sbccf.CAUTION: gold, sbccf.FAIL: red}
        step_cards = []
        for i, s in enumerate(c.steps, 1):
            bc = badge[s.status]
            step_cards.append(html.Div([
                html.Div([
                    html.Span(f'Step {i} — {s.name}',
                              style={'color': '#cfc9f0', 'fontWeight': '600'}),
                    html.Span(s.status, style={
                        'float': 'right', 'color': bc, 'fontWeight': '700',
                        'border': f'1px solid {bc}', 'borderRadius': '8px',
                        'padding': '1px 8px', 'fontSize': '11px'}),
                ]),
                html.Div(s.headline, style={'color': '#e8e4ff',
                                            'fontSize': '13px',
                                            'margin': '4px 0'}),
                html.Div(s.detail, style={'color': dim, 'fontSize': '11px'}),
            ], style={'border': f'1px solid #2a2550', 'borderLeft': f'4px solid {bc}',
                      'borderRadius': '8px', 'padding': '9px 12px',
                      'marginBottom': '7px', 'backgroundColor': '#120f2b'}))

        return html.Div([
            html.Div('Confluence — 6-Condition Analysis (Steps 1–4)',
                     style=h_style),
            verdict_row, sub,
            html.Div(step_cards),
            html.P('Verdict is the confluence of the four steps for the chosen '
                   'instrument. Not advice — timing/sizing aid only; combine '
                   'with your own risk management.',
                   style={'color': dim, 'fontSize': '11px', 'marginTop': '4px'}),
        ], style={**panel_style, 'border': f'2px solid {vcolor}'})

    def _sbc_reversal_card(self, today):
        """Forward-week HYPOTHETICAL reversal watch from the Vedic calendar spine.

        Reads `vedic_reversal_calendar.forward_window_view` so the card is
        forward-looking from `today`, not a static paste. Honest by construction:
        labelled hypothetical, references the null vedha backtest, shows when the
        calendar's sharp dates bracket vs land in the window.
        """
        if not HAS_VRC:
            return None
        gold, red, green, dim = (self._SBC_GOLD, self._SBC_RED,
                                 self._SBC_GREEN, self._SBC_DIM)
        panel_style = {'backgroundColor': self._SBC_PANEL,
                       'border': '1px solid #2a2550', 'borderRadius': '12px',
                       'padding': '14px 18px', 'marginBottom': '14px'}
        h_style = {'color': gold, 'letterSpacing': '.1em', 'fontSize': '13px',
                   'textTransform': 'uppercase', 'marginBottom': '8px'}
        v = vrc.forward_window_view(today, 7)
        w0, w1 = v['window']

        label = v['bias_label']
        bcol = red if 'BEARISH' in label else green if 'BULLISH' in label else gold

        def _marker(tag, tag_col, ev, delta_txt):
            if ev is None:
                body = [html.Span('—', style={'color': dim})]
            else:
                body = [
                    html.Div(f'{ev.day:%d %b}', style={
                        'color': '#cfc9f0', 'fontWeight': '700', 'fontSize': '14px'}),
                    html.Div(ev.title, style={'color': '#cfc9f0', 'fontSize': '12px'}),
                    html.Div(ev.place, style={'color': dim, 'fontSize': '10.5px'}),
                    html.Div(delta_txt, style={'color': tag_col, 'fontSize': '10.5px',
                                               'marginTop': '2px'}),
                ]
            return html.Div([
                html.Div(tag, style={'color': tag_col, 'fontSize': '10px',
                                     'letterSpacing': '.08em',
                                     'textTransform': 'uppercase',
                                     'marginBottom': '4px'}),
                *body,
            ], style={'flex': '1', 'border': f'1px solid {tag_col}',
                      'borderRadius': '8px', 'padding': '9px 11px',
                      'backgroundColor': '#120f2b', 'minWidth': '0'})

        prev_ev, next_ev = v['prev_catalyst'], v['next_catalyst']
        prev_delta = (f'{(today - prev_ev.day).days}d ago' if prev_ev else '')
        next_delta = (f'in {(next_ev.day - today).days}d' if next_ev else '')

        if v['in_window']:
            names = '; '.join(f'{e.day:%d %b} {e.title}' for e in v['in_window'])
            mid = _marker('This week', gold,
                          type('E', (), {'day': w0, 'title': names,
                                         'place': 'pinpoint event in-window'})(),
                          f'{w0:%d %b}–{w1:%d %b}')
            mid_flag = None
        else:
            mid = html.Div([
                html.Div('This week', style={'color': gold, 'fontSize': '10px',
                                             'letterSpacing': '.08em',
                                             'textTransform': 'uppercase',
                                             'marginBottom': '4px'}),
                html.Div(f'{w0:%d %b} – {w1:%d %b}', style={
                    'color': gold, 'fontWeight': '700', 'fontSize': '14px'}),
                html.Div('No pinpoint reversal date', style={
                    'color': '#cfc9f0', 'fontSize': '12px'}),
                html.Div('backdrop pressure only — watch, don’t act', style={
                    'color': dim, 'fontSize': '10.5px', 'marginTop': '2px'}),
            ], style={'flex': '1.3', 'border': f'1px solid {gold}',
                      'borderRadius': '8px', 'padding': '9px 11px',
                      'backgroundColor': '#1a1330', 'minWidth': '0'})
            mid_flag = None

        arrow = html.Span('→', style={'color': dim, 'alignSelf': 'center',
                                      'padding': '0 6px', 'fontSize': '16px'})
        timeline = html.Div([
            _marker('Passed', red, prev_ev, prev_delta), arrow,
            mid, arrow,
            _marker('Ahead', red, next_ev, next_delta),
        ], style={'display': 'flex', 'alignItems': 'stretch', 'gap': '0',
                  'flexWrap': 'wrap'})

        cluster_line = None
        if v['clusters']:
            c = v['clusters'][0]
            cluster_line = html.Div([
                html.Span('◆ ', style={'color': gold}),
                html.Span(f'{c.title} ', style={'color': '#cfc9f0',
                                                'fontWeight': '600'}),
                html.Span(f'({c.window[0]:%d %b}–{c.window[1]:%d %b}) — {c.note}',
                          style={'color': dim, 'fontSize': '12px'}),
            ], style={'marginTop': '10px', 'fontSize': '13px'})

        backdrop_chips = html.Div([
            html.Span(f'{s.title}', style={
                'display': 'inline-block', 'border': f'1px solid {self._SBC_GREEN}',
                'color': '#bfe6cf', 'borderRadius': '12px', 'padding': '2px 9px',
                'margin': '3px', 'fontSize': '11px', 'backgroundColor': '#101f18'})
            for s in v['states']
        ]) if v['states'] else None

        sector_chips = html.Div([
            html.Span(sec, style={
                'display': 'inline-block', 'border': '1px solid #2a2550',
                'color': '#cfc9f0', 'borderRadius': '8px', 'padding': '3px 10px',
                'margin': '3px', 'fontSize': '12px', 'backgroundColor': '#120f2b'})
            for sec in v['sectors']
        ])

        return html.Div([
            html.Div([
                html.Span('Forward-Week Reversal Watch', style=h_style),
            ]),
            html.Div([
                html.Span('HYPOTHETICAL', style={
                    'color': gold, 'border': f'1px solid {gold}',
                    'borderRadius': '999px', 'padding': '1px 8px',
                    'fontSize': '10px', 'letterSpacing': '.1em',
                    'fontWeight': '700', 'marginRight': '10px'}),
                html.Span(f'{w0:%d %b} – {w1:%d %b %Y}',
                          style={'color': '#cfc9f0', 'fontSize': '12px'}),
                html.Span(' · next 7 days from today',
                          style={'color': dim, 'fontSize': '11px',
                                 'fontStyle': 'italic'}),
                html.Span('   Bias: ', style={'color': dim, 'fontSize': '12px'}),
                html.Span(label, style={'color': bcol, 'fontWeight': '700'}),
            ], style={'marginBottom': '10px'}),
            (html.Div(v['bias_note'], style={'color': dim, 'fontSize': '12px',
                                             'marginBottom': '10px'})
             if v['bias_note'] else html.Span()),
            timeline,
            cluster_line or html.Span(),
            (html.Div([html.Div('Standing backdrop', style={
                'color': dim, 'fontSize': '10px', 'letterSpacing': '.08em',
                'textTransform': 'uppercase', 'margin': '10px 0 2px'}),
                backdrop_chips]) if backdrop_chips else html.Span()),
            html.Div('Sectors the calendar names', style={
                'color': dim, 'fontSize': '10px', 'letterSpacing': '.08em',
                'textTransform': 'uppercase', 'margin': '10px 0 2px'}),
            sector_chips,
            html.Div([
                html.Span('⚠ Watch-flag, not a signal. ',
                          style={'color': red, 'fontWeight': '600',
                                 'fontSize': '11.5px'}),
                html.Span("Restates a third-party speculative calendar. Our own "
                          "18-yr NIFTY backtest found SBC daily vedha has no timing "
                          "edge (lift ≈ 1.0, p n.s.) — treat every date as a reason "
                          "to watch harder, never to position. Price confirmation + "
                          "risk rules decide. Direction not implied.",
                          style={'color': dim, 'fontSize': '11.5px'}),
            ], style={'marginTop': '12px', 'borderTop': '1px solid #2a2550',
                      'paddingTop': '10px'}),
        ], style={**panel_style, 'borderLeft': f'3px solid {gold}'})

    # Per-planet crash weights (heavier malefics weigh more). Moon carried as a
    # mild baseline contributor. Max = 3+3+3+2+1+1 = 13.
    _CRASH_WEIGHT = {'Saturn': 3, 'Rahu': 3, 'Mars': 3, 'Ketu': 2,
                     'Sun': 1, 'Moon': 1}

    def _sbc_crash_monitor(self, planets, vedas):
        """Malefic-pressure gauge (0-13), banded like the reference SS.

        Score is geometry-driven so it VARIES: each planet contributes its weight
        scaled by how many currently-OCCUPIED nakshatras its vedha pierces
        (0 hits -> 0 · 1 hit -> 0.6 · 2+ hits -> 1.0 · concentrated confrontation).
        Not a validated crash predictor — see caveat + our null vedha backtest.
        """
        gold, red, green, dim = (self._SBC_GOLD, self._SBC_RED,
                                 self._SBC_GREEN, self._SBC_DIM)
        orange = '#e08a3c'
        panel_style = {'backgroundColor': self._SBC_PANEL,
                       'border': '1px solid #2a2550', 'borderRadius': '12px',
                       'padding': '14px 18px', 'marginBottom': '14px'}
        h_style = {'color': gold, 'letterSpacing': '.1em', 'fontSize': '13px',
                   'textTransform': 'uppercase', 'marginBottom': '8px'}

        occ = {ps.nakshatra for ps in planets.values()}
        contribs = []          # (planet, weight, hits, contribution)
        score = 0.0
        for pl, w in self._CRASH_WEIGHT.items():
            hit_naks = {v.target_nakshatra for v in vedas
                        if v.planet == pl and v.target_nakshatra in occ}
            n = len(hit_naks)
            inten = 0.0 if n == 0 else (1.0 if n >= 2 else 0.6)
            c = w * inten
            score += c
            contribs.append((pl, w, n, c))
        score = round(score)

        if score >= 11:
            band, bcol, act = ('CRASH RISK', red,
                               'Extreme malefic confluence — reduce risk / hedge, '
                               'avoid new entries.')
        elif score >= 8:
            band, bcol, act = ('STRONG REVERSAL', orange,
                               'Heavy pressure — trade lighter, expect volatility.')
        elif score >= 5:
            band, bcol, act = ('VOLATILITY', gold,
                               'Choppy — moderate pressure, nimble sizing.')
        else:
            band, bcol, act = ('NORMAL', green,
                               'Low malefic confluence flagged.')

        # meter (0..13) with band thresholds at 5 / 8 / 11
        fill = html.Div(style={'width': f'{score / 13 * 100:.0f}%',
                               'height': '100%', 'backgroundColor': bcol,
                               'borderRadius': '5px'})
        ticks = [html.Div(style={
            'position': 'absolute', 'left': f'{t / 13 * 100:.0f}%', 'top': '0',
            'bottom': '0', 'width': '1px', 'backgroundColor': '#3a3560'})
            for t in (5, 8, 11)]
        meter = html.Div([fill, *ticks], style={
            'position': 'relative', 'height': '12px', 'backgroundColor': '#120f2b',
            'border': '1px solid #2a2550', 'borderRadius': '6px',
            'overflow': 'hidden', 'margin': '4px 0 2px'})
        scale = html.Div([
            html.Span('0–4 Normal', style={'color': green}),
            html.Span('5–7 Volatility', style={'color': gold}),
            html.Span('8–10 Strong', style={'color': orange}),
            html.Span('11+ Crash', style={'color': red}),
        ], style={'display': 'flex', 'justifyContent': 'space-between',
                  'fontSize': '10px', 'marginBottom': '10px'})

        chips = []
        for pl, w, n, c in contribs:
            live = c > 0
            cc = red if live else dim
            chips.append(html.Span([
                html.Span(sbc.PLANET_GLYPH.get(pl, ''), style={'color': cc}),
                html.Span(f' {pl} +{w}', style={'color': '#cfc9f0' if live else dim}),
                html.Span(f' · {n} hit{"s" if n != 1 else ""}',
                          style={'color': dim, 'fontSize': '10px'}),
            ], style={'display': 'inline-block',
                      'border': f'1px solid {cc if live else "#2a2550"}',
                      'borderRadius': '10px', 'padding': '2px 9px', 'margin': '3px',
                      'fontSize': '12px', 'backgroundColor': '#120f2b',
                      'opacity': '1' if live else '0.5'}))

        return html.Div([
            html.Div('Crash Risk Monitor', style=h_style),
            html.Div([
                html.Span(str(score), style={'fontSize': '34px', 'fontWeight': '800',
                                             'color': bcol, 'lineHeight': '1'}),
                html.Span(' / 13', style={'color': dim, 'fontSize': '14px'}),
                html.Span(f'   {band}', style={'color': bcol, 'fontWeight': '700',
                                               'fontSize': '16px',
                                               'marginLeft': '10px'}),
            ], style={'marginBottom': '6px'}),
            meter, scale,
            html.Div(chips),
            html.Div(act, style={'color': '#e8d9a0', 'fontSize': '12px',
                                 'marginTop': '8px'}),
            html.Div([
                html.Span('⚠ Hypothetical gauge, not a prediction. ',
                          style={'color': red, 'fontWeight': '600',
                                 'fontSize': '11px'}),
                html.Span('Malefic vedha pressure is structurally common, so high '
                          'readings are frequent and — per our 18-yr NIFTY backtest '
                          '(no timing edge) — do NOT forecast crashes. A stress '
                          'thermometer, not a signal.',
                          style={'color': dim, 'fontSize': '11px'}),
            ], style={'marginTop': '10px', 'borderTop': '1px solid #2a2550',
                      'paddingTop': '8px'}),
        ], style={**panel_style, 'borderLeft': f'3px solid {bcol}'})

    def _sbc_sector_stress(self, vedas):
        """Broad Vedha Pressure — sectors ranked by net vedha on their nama-nak.

        For each sector's nakshatra: benefic planets (support) vs malefic planets
        (stress). net = benefic_weight - malefic_weight, clamped to +/-6 (the
        display scale). Ranked LEAST-STRESSED first — where to hide when the index
        is heavy. Modelled on the reference screenshot's 'BROAD VEDHA PRESSURE'.
        """
        import sbc_nama as _nama
        gold, red, green, dim = (self._SBC_GOLD, self._SBC_RED,
                                 self._SBC_GREEN, self._SBC_DIM)
        panel_style = {'backgroundColor': self._SBC_PANEL,
                       'border': '1px solid #2a2550', 'borderRadius': '12px',
                       'padding': '14px 18px', 'marginBottom': '14px'}
        h_style = {'color': gold, 'letterSpacing': '.1em', 'fontSize': '13px',
                   'textTransform': 'uppercase', 'marginBottom': '8px'}

        by_nak = {}
        for v in vedas:
            by_nak.setdefault(v.target_nakshatra, []).append(v)

        rows_data = []
        for sector in sbcs.SECTORS:
            r = _nama.resolve_nakshatra(sector)
            nak = r[0] if r else ''
            hits = by_nak.get(nak, [])
            ben_pl, mal_pl, seen = [], [], set()
            for v in hits:                        # preserve first-seen order
                key = (v.planet, v.nature)
                if key in seen:
                    continue
                seen.add(key)
                (ben_pl if v.nature == 'benefic' else mal_pl).append(v.planet)
            ben_w = sum(v.weight for v in hits if v.nature == 'benefic')
            mal_w = sum(v.weight for v in hits if v.nature == 'malefic')
            net = max(-6.0, min(6.0, ben_w - mal_w))
            rows_data.append((sector, nak, net, ben_pl, mal_pl))
        rows_data.sort(key=lambda x: x[2], reverse=True)   # least-stressed first

        def _glyphs(pls, col):
            return html.Span(' '.join(sbc.PLANET_GLYPH.get(p, p[:2]) for p in pls)
                             or '—', style={'color': col})

        rows = []
        for sector, nak, net, ben_pl, mal_pl in rows_data:
            if net <= -0.3:
                bcol, tag = red, 'BEARISH'
            elif net >= 0.3:
                bcol, tag = green, 'BULLISH'
            else:
                bcol, tag = gold, 'NEUTRAL'
            bar = html.Div(html.Div(style={
                'width': f'{abs(net) / 6 * 100:.0f}%', 'height': '100%',
                'backgroundColor': bcol, 'borderRadius': '4px'}),
                style={'flex': '1', 'height': '10px', 'backgroundColor': '#120f2b',
                       'border': '1px solid #2a2550', 'borderRadius': '5px',
                       'overflow': 'hidden', 'margin': '0 10px'})
            rows.append(html.Div([
                html.Span(sector, style={'width': '92px', 'color': '#cfc9f0',
                                         'fontSize': '13px', 'flexShrink': '0'}),
                bar,
                html.Span(f'{net:+.1f}/6.0', style={
                    'width': '62px', 'textAlign': 'right', 'color': bcol,
                    'fontSize': '12px', 'fontVariantNumeric': 'tabular-nums',
                    'flexShrink': '0'}),
                html.Span([_glyphs(ben_pl, green),
                           html.Span(' vs ', style={'color': dim,
                                                    'fontSize': '10px'}),
                           _glyphs(mal_pl, red)],
                          style={'width': '150px', 'textAlign': 'right',
                                 'fontSize': '12px', 'flexShrink': '0',
                                 'marginLeft': '10px'}),
                html.Span(tag, style={
                    'width': '62px', 'textAlign': 'center', 'color': bcol,
                    'fontSize': '9px', 'fontWeight': '700', 'letterSpacing': '.06em',
                    'border': f'1px solid {bcol}', 'borderRadius': '999px',
                    'padding': '2px 0', 'marginLeft': '10px', 'flexShrink': '0'}),
            ], style={'display': 'flex', 'alignItems': 'center',
                      'padding': '5px 0', 'borderBottom': '1px solid #1c1840'}))

        return html.Div([
            html.Div('Broad Vedha Pressure', style=h_style),
            html.P('Sectors ranked by net vedha on their nama-nakshatra — '
                   'benefic support (green) vs malefic stress (red). '
                   'Least-stressed first: where pressure is lightest right now.',
                   style={'color': dim, 'fontSize': '12px', 'marginBottom': '8px'}),
            html.Div(rows),
            html.Div('Hypothetical stress map, not a signal — vedha pressure has no '
                     'validated timing edge (see backtest). Use to compare relative '
                     'stress, not to predict direction.',
                     style={'color': dim, 'fontSize': '11px', 'marginTop': '8px',
                            'fontStyle': 'italic'}),
        ], style=panel_style)

    def _render_sbc(self, selected_date, granularity,
                    birth_date=None, birth_time=None,
                    birth_lat=None, birth_lon=None, view='chakra',
                    instrument='Gold', planet_filter='All',
                    vedha_blocks=False, timeframe='intraday'):
        d = datetime.strptime(selected_date, '%Y-%m-%d').date()
        now_utc = datetime.utcnow()
        planets = sbc.compute_planets(now_utc)
        vedas = sbcs.cast_vedas(planets)
        bias = sbcs.market_bias(vedas)
        scores = sbcs.sector_scores(vedas)
        windows = sbcs.moon_reversal_windows(d, granularity=granularity)
        now_ist = now_utc + sbc.IST_OFFSET
        panchang = sbcp.compute_panchang(now_ist)
        natal_panel = self._sbc_natal_panel(
            birth_date, birth_time, birth_lat, birth_lon,
            planets['Moon'].nakshatra)
        confluence_panel = self._sbc_confluence_panel(
            instrument, planets, vedas, bias, panchang, windows, now_ist)
        signals_panel = self._sbc_trading_signals_panel(
            planets, vedas, bias, panchang, windows, now_ist, timeframe, d)

        gold, red, green, dim = (self._SBC_GOLD, self._SBC_RED,
                                 self._SBC_GREEN, self._SBC_DIM)
        panel_style = {'backgroundColor': self._SBC_PANEL,
                       'border': '1px solid #2a2550', 'borderRadius': '12px',
                       'padding': '14px 18px', 'marginBottom': '14px'}
        h_style = {'color': gold, 'letterSpacing': '.1em', 'fontSize': '13px',
                   'textTransform': 'uppercase', 'marginBottom': '8px'}

        # bias banner
        bias_color = {'BEARISH': red, 'BULLISH': green, 'MIXED': gold}[bias.label]
        banner = html.Div([
            html.Div('Market Bias', style=h_style),
            html.Span(bias.label, style={'fontSize': '28px', 'fontWeight': '700',
                                         'color': bias_color}),
            html.Span(f'  net {bias.net:+.3f}', style={'color': dim}),
            html.Br(),
            html.Span(f'malefic {bias.malefic_score}', style={'color': red}),
            html.Span('   |   ', style={'color': dim}),
            html.Span(f'benefic {bias.benefic_score}', style={'color': green}),
        ], style={**panel_style, 'textAlign': 'center'})

        # panchang header (tithi / vara / nakshatra / karana / moon / sun)
        def _pchip(label, value, vcolor=None):
            return html.Div([
                html.Div(label, style={'color': dim, 'fontSize': '10px',
                                       'letterSpacing': '.08em',
                                       'textTransform': 'uppercase'}),
                html.Div(value, style={'color': vcolor or '#cfc9f0',
                                       'fontWeight': '600', 'fontSize': '14px'}),
            ], style={'textAlign': 'center', 'flex': '1', 'padding': '4px 8px'})
        panchang_bar = html.Div([
            _pchip('Nakshatra', panchang.nakshatra),
            _pchip('Tithi', panchang.tithi_name),
            _pchip('Vara', panchang.vara),
            _pchip('Karana', panchang.karana,
                   red if panchang.bhadra_active else '#cfc9f0'),
            _pchip('Moon°', f'{panchang.moon_lon:.1f}°'),
            _pchip('Sun°', f'{panchang.sun_lon:.1f}°'),
        ], style={**panel_style, 'display': 'flex', 'justifyContent': 'space-between'})

        # bhadra banner (only when active)
        bhadra_banner = None
        if panchang.bhadra_active:
            bhadra_banner = html.Div([
                html.Span('⚠ BHADRA ACTIVE NOW  ',
                          style={'color': red, 'fontWeight': '700',
                                 'fontSize': '15px'}),
                html.Span(sbcp.trading_note(panchang),
                          style={'color': '#e8d9a0', 'fontSize': '13px'}),
            ], style={**panel_style, 'border': f'1px solid {red}',
                      'backgroundColor': '#2a1414'})

        # planet table
        prows = [html.Tr([
            html.Td(f"{sbc.PLANET_GLYPH.get(n,'')} {n}",
                    style={'color': '#cfc9f0', 'padding': '4px 10px'}),
            html.Td(ps.nakshatra, style={'color': '#cfc9f0', 'padding': '4px 10px'}),
            html.Td(ps.pada, style={'color': dim, 'padding': '4px 10px'}),
            html.Td(f'{ps.sidereal_lon:.2f}°', style={'color': dim, 'padding': '4px 10px'}),
            html.Td('Rx' if ps.retrograde else 'D',
                    style={'color': red if ps.retrograde else green, 'padding': '4px 10px'}),
            html.Td(ps.nature, style={'color': red if ps.nature == 'malefic' else green,
                                      'padding': '4px 10px'}),
        ]) for n, ps in planets.items()]
        ptable = html.Div([
            html.Div('Planetary Placement', style=h_style),
            html.Table(
                [html.Tr([html.Th(c, style={'color': gold, 'textAlign': 'left',
                                            'padding': '4px 10px'})
                          for c in ['Planet', 'Nakshatra', 'Pada', 'Sidereal',
                                    'Motion', 'Nature']])] + prows,
                style={'width': '100%', 'borderCollapse': 'collapse',
                       'fontSize': '13px'}),
        ], style=panel_style)

        # reversal windows
        wcards = []
        for w in windows:
            live = w.start_ist <= now_ist <= w.end_ist
            edge = gold if live else '#2a2550'
            children = [html.B(f'{w.start_ist:%H:%M}–{w.end_ist:%H:%M}',
                               style={'color': gold})]
            if live:
                children.append(html.Span('  ● LIVE',
                                          style={'color': gold, 'fontWeight': '700'}))
            children += [html.Br(),
                         html.Span(f'{w.from_nakshatra} → {w.to_nakshatra}',
                                   style={'color': dim, 'fontSize': '12px'})]
            wcards.append(html.Div(children, style={
                'border': f'1px solid {edge}', 'borderRadius': '8px',
                'padding': '8px 11px', 'marginBottom': '6px',
                'backgroundColor': '#120f2b'}))
        wpanel = html.Div([
            html.Div('Reversal Windows (IST)', style=h_style),
            html.Div(wcards or [html.Span('No crossings in range.',
                                          style={'color': dim})]),
        ], style=panel_style)

        # grid
        pressure = {i: 0.0 for i in range(27)}
        occupant = {i: [] for i in range(27)}
        for v in vedas:
            if v.target_index < 0:      # Abhijit — not one of the 27 cells
                continue
            pressure[v.target_index] += (v.weight if v.nature == 'benefic'
                                         else -v.weight)
        for n, ps in planets.items():
            occupant[ps.nakshatra_index].append(sbc.PLANET_GLYPH.get(n, n[0]))
        gpanel = self._sbc_badra_grid_panel(
            planets, vedas, bias, panchang, vedha_blocks)

        # centre view — drawn square chakra OR zodiac aspect map (toggle)
        import sbc_grid as _grid
        board = _grid.build_board()
        if view == 'aspects':
            centre_fig = self._aspect_map_figure(planets)
            centre_title = 'Aspect Map — Graha Drishti'
            centre_note = ('Zodiac wheel · planets at sidereal longitude. '
                           'Lines = full aspects (drishti) — green benefic / '
                           'red malefic; solid = 7th (opposition), dotted = '
                           'special aspect (Mars 4/8, Jupiter 5/9, Saturn 3/10, '
                           'nodes 5/9). Hover a planet for its aspect list.')
        else:
            centre_fig = self._sbc_chakra_figure(board, planets, pressure,
                                                 planet_filter)
            who = (f' — {planet_filter} only'
                   if planet_filter and planet_filter != 'All' else '')
            centre_title = f'SBC Chakra — Vedha Lines{who}'
            centre_note = ('Concentric rings: nakshatras (outer) · consonants · '
                           'rashis · tithis+weekdays (centre). Lines = live '
                           'vedha rays — green benefic / red malefic; solid = '
                           'Sammukha (front, strong/Prathyak), dotted = Vaama '
                           '(left, fast planets), dashed = Dakshina (right, '
                           'retrograde).'
                           + (f' Showing only {planet_filter}’s projections; '
                              'gold-outlined cells are the nakshatras it pierces.'
                              if planet_filter and planet_filter != 'All'
                              else ' Hover a planet dot for detail.'))
        chakra_panel = html.Div([
            html.Div(centre_title, style=h_style),
            dcc.Graph(figure=centre_fig, config={'displayModeBar': False}),
            html.P(centre_note,
                   style={'color': dim, 'fontSize': '12px', 'marginTop': '4px'}),
        ], style=panel_style)

        # sector scoreboard
        scards = []
        for s in scores:
            scolor = {'BULLISH': green, 'BEARISH': red, 'NEUTRAL': gold}[s.label]
            pstr = ' '.join(sbc.PLANET_GLYPH.get(pl, pl) for pl in s.hitting_planets)
            scards.append(html.Div([
                html.B(s.sector, style={'color': '#cfc9f0'}),
                html.Span(f'{s.label} {s.score:+.2f}',
                          style={'float': 'right', 'color': scolor,
                                 'fontWeight': '600', 'fontSize': '13px'}),
                html.Br(),
                html.Span(f'{s.nakshatra}  {pstr}',
                          style={'color': dim, 'fontSize': '12px'}),
            ], style={'border': '1px solid #2a2550',
                      'borderLeft': f'4px solid {scolor}', 'borderRadius': '8px',
                      'padding': '8px 11px', 'backgroundColor': '#120f2b',
                      'width': '31%', 'display': 'inline-block',
                      'marginRight': '2%', 'marginBottom': '8px',
                      'verticalAlign': 'top'}))
        spanel = html.Div([
            html.Div('Sector Scoreboard (Nama-Nakshatra)', style=h_style),
            html.Div(scards),
        ], style=panel_style)

        disclaimer = html.Div([
            html.Span('EDUCATIONAL MODEL ONLY. ',
                      style={'color': red, 'fontWeight': '600'}),
            html.Span('Veda scoring is a deterministic model of the documented '
                      'mechanic, not classical-exact and not a certainty engine. '
                      'Reported accuracy for astro timing is ~40–60% on major '
                      'trends and lower on specific date/price calls — treat as '
                      'a supplementary input, not primary. Never trade solely on '
                      'astrological signals; use stops and position sizing. '
                      f'Computed {now_ist:%Y-%m-%d %H:%M} IST.',
                      style={'color': dim, 'fontSize': '12px'}),
        ], style={**panel_style, 'border': f'1px solid {red}'})

        # nama name-analysis panel (categorised instrument chips -> nakshatra)
        import sbc_nama as _nama
        # per-nakshatra net veda pressure -> chip colour
        nak_net = {}
        for v in vedas:
            if v.target_index < 0:
                continue
            nk = sbc.NAKSHATRAS[v.target_index]
            nak_net[nk] = nak_net.get(nk, 0.0) + (
                v.weight if v.nature == 'benefic' else -v.weight)

        def _nama_chip(name):
            res = _nama.resolve_nakshatra(name)
            nk = res[0] if res else '?'
            net = nak_net.get(nk, 0.0)
            if net > 0:
                cc, arrow = green, '▲'
            elif net < 0:
                cc, arrow = red, '▼'
            else:
                cc, arrow = dim, '·'
            return html.Span([
                html.Span(f'{name} ', style={'color': '#cfc9f0'}),
                html.Span(arrow, style={'color': cc, 'fontWeight': '700'}),
                html.Span(f' {nk[:4]}', style={'color': dim, 'fontSize': '10px'}),
            ], style={'display': 'inline-block', 'border': f'1px solid {cc}',
                      'borderRadius': '12px', 'padding': '3px 9px',
                      'margin': '3px', 'fontSize': '12px',
                      'backgroundColor': '#120f2b'})

        nama_cats = []
        for cat, items in _nama.NAMA_CATALOG.items():
            nama_cats.append(html.Div([
                html.Div(cat, style={'color': gold, 'fontSize': '11px',
                                     'textTransform': 'uppercase',
                                     'letterSpacing': '.08em',
                                     'margin': '8px 0 2px'}),
                html.Div([_nama_chip(i) for i in items]),
            ]))
        nama_panel = html.Div([
            html.Div('Nama Nakshatra — Name Analysis', style=h_style),
            html.P("Each instrument's first sound (akshara) places it on a "
                   "nakshatra; today's vedhas on that nakshatra set its lean. "
                   "▲ benefic-led · ▼ malefic-led · · untouched.",
                   style={'color': dim, 'fontSize': '12px', 'marginBottom': '4px'}),
            html.Div(nama_cats),
        ], style=panel_style)

        top_children = [panchang_bar]
        if bhadra_banner is not None:
            top_children.append(bhadra_banner)
        top_children.append(banner)
        top_children.append(self._sbc_crash_monitor(planets, vedas))
        # Forward-week card is locked to the REAL current date (IST), not the
        # DatePicker session date — it answers "what's ahead from now", so the
        # session date must not move it.
        reversal_card = self._sbc_reversal_card(now_ist.date())
        if reversal_card is not None:
            top_children.append(reversal_card)
        top_children.append(confluence_panel)
        top_children.append(signals_panel)

        return html.Div(top_children + [
            html.Div([
                html.Div(ptable, style={'width': '60%', 'display': 'inline-block',
                                        'verticalAlign': 'top', 'paddingRight': '1%'}),
                html.Div(wpanel, style={'width': '38%', 'display': 'inline-block',
                                        'verticalAlign': 'top'}),
            ]),
            chakra_panel, natal_panel, gpanel,
            self._sbc_sector_stress(vedas), spanel, nama_panel, disclaimer,
        ], style={'backgroundColor': self._SBC_BG, 'padding': '16px',
                  'borderRadius': '12px', 'fontFamily': 'Segoe UI, sans-serif'})

    def run(self):
        """Run the dashboard server."""
        print(f"Starting Trading Bramha Dash Dashboard on http://localhost:{self.port}")
        # Dash >=3 renamed run_server() -> run(); support both. Newer Dash
        # raises when run_server is even accessed, so guard the lookup.
        try:
            runner = self.app.run_server
        except Exception:
            runner = self.app.run
        runner(debug=self.debug, port=self.port)


if __name__ == '__main__':
    import os
    # Default to NO debug/reloader so start.bat runs a single, cleanly-killable
    # process. Set SBC_DEBUG=1 for the live-reload dev server.
    debug = os.environ.get('SBC_DEBUG', '0') == '1'
    port = int(os.environ.get('SBC_PORT', '8050'))
    dashboard = TradingDashboard(port=port, debug=debug)
    dashboard.run()
