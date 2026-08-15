#!/usr/bin/env python3
"""
signal_processing_engine.py
Trading signal processing pipeline - Python implementation of GitHub repo.

This module integrates the financial-astrology-research/trading-signal-processing
architecture into Trading Bramha for:

1. TradingView signal ingestion & parsing
2. CSV-based indicator filtering (consensus validation)
3. Risk management parameter composition
4. Multi-exchange signal formatting (Zignaly, direct API)
5. Signal lifecycle tracking & performance logging

Reference:
  https://github.com/financial-astrology-research/trading-signal-processing

Usage:
  from signal_processing_engine import SignalProcessor, TradingViewSignal

  processor = SignalProcessor()
  tv_signal = {
      'action': 'entry',
      'side': 'long',
      'symbolCode': 'BTCUSDT',
      'stopLossPercent': 2.0,
      'date': '2026-06-28',
      'hour': '14'
  }

  filtered = processor.filter_signal(tv_signal)
  formatted = processor.format_for_zignaly(tv_signal)
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
import csv
from pathlib import Path

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class SignalAction(Enum):
    """Signal action types."""
    ENTRY = "entry"
    EXIT = "exit"


class SignalSide(Enum):
    """Signal side/direction."""
    LONG = "long"
    SHORT = "short"


class ExchangeType(Enum):
    """Exchange account types."""
    SPOT = "spot"
    FUTURES = "futures"
    MARGIN = "margin"


class OrderType(Enum):
    """Order types."""
    MARKET = "market"
    LIMIT = "limit"


class TradingViewSignal:
    """TradingView strategy signal container."""

    def __init__(
        self,
        action: str,
        side: str,
        symbol_code: str,
        date: str,
        hour: str,
        **kwargs
    ):
        """
        Initialize signal from TradingView payload.

        Args:
            action: 'entry' or 'exit'
            side: 'long' or 'short'
            symbol_code: Trading pair (e.g., 'BTCUSDT')
            date: Signal date (YYYY-MM-DD)
            hour: Signal hour (0-23)
            **kwargs: Additional parameters (stop loss %, trailing stops, etc.)
        """
        self.action = action
        self.side = side
        self.symbol_code = symbol_code
        self.date = date
        self.hour = hour
        self.timezone = kwargs.get('timezone', 'UTC')
        self.order_type = kwargs.get('order_type', 'market')
        self.symbol_id = kwargs.get('symbol_id', symbol_code)
        self.exchange_id = kwargs.get('exchange_id', 'binance')
        self.indicator_type = kwargs.get('indicator_type', 'unknown')
        self.indicator_period = kwargs.get('indicator_period', 0)

        # Risk management parameters
        self.stop_loss_percent = kwargs.get('stop_loss_percent')
        self.trailing_stop_trigger_percent = kwargs.get('trailing_stop_trigger_percent')
        self.trailing_stop_long_percent = kwargs.get('trailing_stop_long_percent')
        self.trailing_stop_short_percent = kwargs.get('trailing_stop_short_percent')

        # Processing flags
        self.skip_processing_filters = kwargs.get('skip_processing_filters', False)
        self.provider_env_key = kwargs.get('provider_env_key', 'ZIGNALY_PROVIDER_KEY')

        # Signal metadata
        self.signal_price = kwargs.get('signal_price')
        self.created_at = datetime.utcnow()

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'action': self.action,
            'side': self.side,
            'symbol_code': self.symbol_code,
            'date': self.date,
            'hour': self.hour,
            'timezone': self.timezone,
            'order_type': self.order_type,
            'symbol_id': self.symbol_id,
            'exchange_id': self.exchange_id,
            'indicator_type': self.indicator_type,
            'indicator_period': self.indicator_period,
            'stop_loss_percent': self.stop_loss_percent,
            'trailing_stop_trigger_percent': self.trailing_stop_trigger_percent,
            'trailing_stop_long_percent': self.trailing_stop_long_percent,
            'trailing_stop_short_percent': self.trailing_stop_short_percent,
            'skip_processing_filters': self.skip_processing_filters,
            'signal_price': self.signal_price,
        }


class SignalProcessor:
    """Process and filter trading signals for execution."""

    # Default position risk parameters
    DEFAULT_POSITION_SIZE_PERCENT = 25
    DEFAULT_LEVERAGE = 1
    DEFAULT_STOP_LOSS_PERCENT = 2.0
    DEFAULT_TRAILING_STOP_TRIGGER_PERCENT = 2.0
    DEFAULT_TRAILING_STOP_DISTANCE_PERCENT = 2.0

    def __init__(self, csv_indicators_dir: Optional[str] = None):
        """
        Initialize signal processor.

        Args:
            csv_indicators_dir: Directory containing CSV indicator files
        """
        self.csv_indicators_dir = Path(csv_indicators_dir) if csv_indicators_dir else None
        self.csv_cache = {}  # Cache loaded CSV files
        self.signal_history = []

    def load_csv_indicator(self, symbol: str, indicator_type: str = 'daily') -> Optional[pd.DataFrame]:
        """
        Load CSV indicator file for a symbol.

        Expected format:
        - Daily: columns [Date, Action] where Action is 'buy' or 'sell'
        - Hourly: columns [Date, Hour, Action]

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            indicator_type: 'daily' or 'hourly'

        Returns:
            DataFrame with indicator data, or None if not found
        """
        if not HAS_PANDAS or not self.csv_indicators_dir:
            return None

        cache_key = f"{symbol}_{indicator_type}"
        if cache_key in self.csv_cache:
            return self.csv_cache[cache_key]

        filename = f"ml-{symbol}-{indicator_type}-consensus.csv"
        filepath = self.csv_indicators_dir / filename

        try:
            if filepath.exists():
                df = pd.read_csv(filepath)
                self.csv_cache[cache_key] = df
                return df
        except Exception as e:
            print(f"Error loading CSV indicator {filename}: {e}")

        return None

    def filter_signal_by_csv_indicator(
        self,
        signal: TradingViewSignal,
        indicator_type: str = 'daily'
    ) -> bool:
        """
        Filter signal using CSV consensus indicator.

        Only entry signals are filtered. Exit signals pass through.

        Args:
            signal: TradingViewSignal to filter
            indicator_type: 'daily' or 'hourly'

        Returns:
            True if signal passes filter, False otherwise
        """
        # Exit signals always pass
        if signal.action == SignalAction.EXIT.value:
            return True

        # Skip filter if requested
        if signal.skip_processing_filters:
            return True

        # Load indicator CSV
        df = self.load_csv_indicator(signal.symbol_code, indicator_type)
        if df is None:
            print(f"No CSV indicator found for {signal.symbol_code}_{indicator_type}")
            return True  # Pass if no indicator available

        # Map signal side to action
        expected_action = "buy" if signal.side == SignalSide.LONG.value else "sell"

        # Determine signal date (adjust if after 9 AM UTC)
        signal_date = datetime.strptime(signal.date, '%Y-%m-%d')
        current_hour = datetime.utcnow().hour

        if current_hour >= 9:
            signal_date = signal_date + timedelta(days=1)

        check_date = signal_date.strftime('%Y-%m-%d')

        # Filter by date
        date_rows = df[df['Date'] == check_date]
        if date_rows.empty:
            print(f"No indicator data found for date {check_date}")
            return False

        # Get actions for this date
        actions = date_rows['Action'].unique().tolist()
        filter_pass = all(action == expected_action for action in actions)

        print(f"CSV Filter: {signal.symbol_code} {expected_action} on {check_date}")
        print(f"  Indicator actions: {actions}")
        print(f"  Filter pass: {filter_pass}")

        return filter_pass

    def get_default_risk_params(self) -> Dict:
        """Get default risk management parameters."""
        return {
            'position_size_percent': self.DEFAULT_POSITION_SIZE_PERCENT,
            'leverage': self.DEFAULT_LEVERAGE,
            'stop_loss_percent': self.DEFAULT_STOP_LOSS_PERCENT,
            'trailing_stop_trigger_percent': self.DEFAULT_TRAILING_STOP_TRIGGER_PERCENT,
            'trailing_stop_long_percent': self.DEFAULT_TRAILING_STOP_DISTANCE_PERCENT,
            'trailing_stop_short_percent': self.DEFAULT_TRAILING_STOP_DISTANCE_PERCENT,
        }

    def compose_zignaly_signal(
        self,
        signal: TradingViewSignal,
        exchange_type: str = 'futures'
    ) -> Dict:
        """
        Compose signal in Zignaly API format.

        Args:
            signal: TradingViewSignal
            exchange_type: 'spot' or 'futures'

        Returns:
            Zignaly-formatted signal dict
        """
        params = self.get_default_risk_params()

        # Override with signal-specific parameters
        if signal.stop_loss_percent:
            params['stop_loss_percent'] = signal.stop_loss_percent

        if signal.action == SignalAction.ENTRY.value:
            # Entry signal
            return {
                'type': 'entry',
                'exchange': 'Zignaly',
                'exchangeAccountType': exchange_type,
                'orderType': 'market',
                'pair': signal.symbol_code,
                'side': signal.side,
                'signalId': f"{signal.symbol_code}_{signal.side}",
                'positionSizePercentage': params['position_size_percent'],
                'stopLossPercentage': params['stop_loss_percent'] or False,
                'leverage': params['leverage'],
                'trailingStopTriggerPercentage': params['trailing_stop_trigger_percent'] or False,
                'trailingStopDistancePercentage': params[
                    'trailing_stop_long_percent' if signal.side == 'long' else 'trailing_stop_short_percent'
                ] or False,
                'providerKey': None,  # Set from environment
            }
        else:
            # Exit signal
            return {
                'type': 'exit',
                'exchange': 'Zignaly',
                'exchangeAccountType': exchange_type,
                'pair': signal.symbol_code,
                'side': signal.side,
                'signalId': f"{signal.symbol_code}_{signal.side}",
                'providerKey': None,  # Set from environment
            }

    def validate_signal(self, signal: TradingViewSignal) -> Tuple[bool, List[str]]:
        """
        Validate signal for required fields and valid ranges.

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        # Required fields
        if not signal.action or signal.action not in ['entry', 'exit']:
            errors.append(f"Invalid action: {signal.action}")

        if not signal.side or signal.side not in ['long', 'short']:
            errors.append(f"Invalid side: {signal.side}")

        if not signal.symbol_code:
            errors.append("Missing symbol_code")

        if not signal.date or not signal.hour:
            errors.append("Missing date or hour")

        # Validate percentages
        if signal.stop_loss_percent and (signal.stop_loss_percent < 0.01 or signal.stop_loss_percent > 100):
            errors.append(f"Stop loss percent out of range: {signal.stop_loss_percent}")

        return len(errors) == 0, errors

    def process_signal(
        self,
        signal: TradingViewSignal,
        apply_csv_filter: bool = True
    ) -> Dict:
        """
        Process a TradingView signal through the full pipeline.

        Args:
            signal: TradingViewSignal to process
            apply_csv_filter: Whether to apply CSV indicator filtering

        Returns:
            {
                'status': 'accepted' | 'rejected' | 'error',
                'signal_id': str,
                'reason': str,
                'zignaly_signal': dict (if accepted),
                'filter_passed': bool,
                'validation_errors': list
            }
        """
        # Validate
        is_valid, validation_errors = self.validate_signal(signal)
        if not is_valid:
            return {
                'status': 'error',
                'signal_id': f"{signal.symbol_code}_{signal.side}_{signal.date}",
                'reason': 'Signal validation failed',
                'validation_errors': validation_errors,
            }

        # Filter (if enabled)
        filter_passed = True
        if apply_csv_filter:
            filter_passed = self.filter_signal_by_csv_indicator(signal)

        # Compose Zignaly signal
        zignaly_signal = self.compose_zignaly_signal(signal)

        # Record in history
        self.signal_history.append({
            'timestamp': datetime.utcnow(),
            'signal': signal.to_dict(),
            'filter_passed': filter_passed,
            'zignaly_signal': zignaly_signal,
            'status': 'accepted' if filter_passed else 'rejected',
        })

        return {
            'status': 'accepted' if filter_passed else 'rejected',
            'signal_id': f"{signal.symbol_code}_{signal.side}",
            'reason': 'Signal passes all filters' if filter_passed else 'Signal rejected by CSV indicator',
            'zignaly_signal': zignaly_signal if filter_passed else None,
            'filter_passed': filter_passed,
        }

    def get_signal_statistics(self) -> Dict:
        """Get statistics on processed signals."""
        if not self.signal_history:
            return {
                'total_signals': 0,
                'accepted': 0,
                'rejected': 0,
                'accept_rate': 0,
                'by_symbol': {},
                'by_side': {},
            }

        total = len(self.signal_history)
        accepted = sum(1 for s in self.signal_history if s['status'] == 'accepted')
        rejected = total - accepted

        # By symbol
        by_symbol = {}
        for record in self.signal_history:
            symbol = record['signal']['symbol_code']
            if symbol not in by_symbol:
                by_symbol[symbol] = {'total': 0, 'accepted': 0}
            by_symbol[symbol]['total'] += 1
            if record['status'] == 'accepted':
                by_symbol[symbol]['accepted'] += 1

        # By side
        by_side = {}
        for record in self.signal_history:
            side = record['signal']['side']
            if side not in by_side:
                by_side[side] = {'total': 0, 'accepted': 0}
            by_side[side]['total'] += 1
            if record['status'] == 'accepted':
                by_side[side]['accepted'] += 1

        return {
            'total_signals': total,
            'accepted': accepted,
            'rejected': rejected,
            'accept_rate': round(accepted / total * 100, 1) if total > 0 else 0,
            'by_symbol': by_symbol,
            'by_side': by_side,
        }


def main():
    """Demo the signal processor."""
    print("=== Trading Signal Processor Demo ===\n")

    processor = SignalProcessor()

    # Create sample signal
    signal = TradingViewSignal(
        action='entry',
        side='long',
        symbol_code='BTCUSDT',
        date='2026-06-28',
        hour='14',
        stop_loss_percent=2.0,
        trailing_stop_trigger_percent=2.0,
    )

    print("Input Signal:")
    for key, val in signal.to_dict().items():
        print(f"  {key}: {val}")

    # Process signal (without CSV filter since no files)
    result = processor.process_signal(signal, apply_csv_filter=False)

    print("\nProcessing Result:")
    for key, val in result.items():
        if key != 'zignaly_signal':
            print(f"  {key}: {val}")

    print("\nZignaly Signal Format:")
    if result['zignaly_signal']:
        for key, val in result['zignaly_signal'].items():
            print(f"  {key}: {val}")

    # Statistics
    stats = processor.get_signal_statistics()
    print("\nStatistics:")
    print(f"  Total Signals: {stats['total_signals']}")
    print(f"  Accepted: {stats['accepted']}")
    print(f"  Accept Rate: {stats['accept_rate']}%")


if __name__ == '__main__':
    main()
