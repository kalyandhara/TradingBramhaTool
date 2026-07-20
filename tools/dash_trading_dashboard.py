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
import dash_html_components as html
import dash_core_components as dcc
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


class TradingDashboard:
    """Interactive Dash-based trading dashboard."""

    def __init__(self, port: int = 8050, debug: bool = True):
        """
        Initialize dashboard.

        Args:
            port: Port to run dashboard on
            debug: Enable debug mode
        """
        self.app = dash.Dash(__name__)
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
                html.H1('Trading Bramha — Interactive Dashboard',
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
                        options=[{'label': city, 'value': city}
                                for city in list(at.AstroIndicators.CITIES.keys())],
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
                    dates_list.append(d_temp.strftime('%m-%d'))
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

    def run(self):
        """Run the dashboard server."""
        print(f"Starting Trading Bramha Dash Dashboard on http://localhost:{self.port}")
        self.app.run_server(debug=self.debug, port=self.port)


if __name__ == '__main__':
    dashboard = TradingDashboard(port=8050, debug=True)
    dashboard.run()
