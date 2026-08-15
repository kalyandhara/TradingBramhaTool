#!/usr/bin/env python3
"""
telegram_signals.py
Load and manage trading signals from Telegram channels (manual import).

Supports:
- Trading signal extraction (stock picks, entry/exit, strategy)
- Multi-channel signal aggregation
- Signal scoring & rating
- Alert generation
- Historical tracking

Usage:
  from telegram_signals import TelegramSignals
  ts = TelegramSignals()
  ts.load_signal_from_dict(rohan_das_rpci_signal)
  ts.get_active_signals()
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
import json
from pathlib import Path

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class SignalStatus(Enum):
    """Trading signal lifecycle status."""
    PENDING = "pending"      # Awaiting entry confirmation
    ACTIVE = "active"        # Position initiated
    PARTIAL = "partial"      # Partial exit taken
    CLOSED = "closed"        # Position fully exited
    CANCELLED = "cancelled"  # Signal invalidated
    EXPIRED = "expired"      # Outside validity window


class SignalSource(Enum):
    """Signal origin classification."""
    RPCI = "RPCI"              # Rohan Das RPCI Indicator
    TECHNOFUNDA = "TechnoFunda" # Technical + Fundamental
    CHART_PATTERN = "Chart Pattern"
    BREAKOUT = "Breakout"
    MOMENTUM = "Momentum"
    OTHER = "Other"


class TelegramSignal:
    """Single trading signal from Telegram source."""

    def __init__(self):
        self.signal_id = None
        self.channel = None
        self.posted_date = None
        self.symbol = None
        self.strategy = None
        self.signal_source = None
        self.entry_price = None
        self.target_price = None
        self.stop_loss = None
        self.timeframe = None
        self.confidence = None  # 1-10 scale
        self.status = SignalStatus.PENDING
        self.entry_date = None
        self.exit_date = None
        self.realized_return = None
        self.notes = ""
        self.metadata = {}  # Extra data (links, images, etc.)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'signal_id': self.signal_id,
            'channel': self.channel,
            'posted_date': str(self.posted_date) if self.posted_date else None,
            'symbol': self.symbol,
            'strategy': self.strategy,
            'signal_source': self.signal_source.value if isinstance(self.signal_source, SignalSource) else self.signal_source,
            'entry_price': self.entry_price,
            'target_price': self.target_price,
            'stop_loss': self.stop_loss,
            'timeframe': self.timeframe,
            'confidence': self.confidence,
            'status': self.status.value if isinstance(self.status, SignalStatus) else self.status,
            'entry_date': str(self.entry_date) if self.entry_date else None,
            'exit_date': str(self.exit_date) if self.exit_date else None,
            'realized_return': self.realized_return,
            'notes': self.notes,
            'metadata': self.metadata,
        }


class TelegramSignals:
    """Manage collection of trading signals from Telegram."""

    def __init__(self, signals_dir: Optional[str] = None):
        """
        Initialize signal manager.

        Args:
            signals_dir: Directory to store signal history (CSV/JSON)
        """
        self.signals: Dict[str, TelegramSignal] = {}
        self.signals_dir = Path(signals_dir) if signals_dir else Path.home() / '.trading_signals'
        self.signals_dir.mkdir(exist_ok=True)
        self.load_signals()

    def load_signals(self) -> None:
        """Load existing signals from storage."""
        json_file = self.signals_dir / 'signals.json'
        if json_file.exists():
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    for sig_id, sig_data in data.items():
                        signal = self._dict_to_signal(sig_data)
                        self.signals[sig_id] = signal
            except Exception as e:
                print(f"Error loading signals: {e}")

    def _dict_to_signal(self, data: Dict) -> TelegramSignal:
        """Convert dict to TelegramSignal."""
        sig = TelegramSignal()
        for key, value in data.items():
            if key == 'status' and value:
                setattr(sig, key, SignalStatus(value))
            elif key == 'signal_source' and value:
                try:
                    setattr(sig, key, SignalSource[value.upper().replace(' ', '_')])
                except (KeyError, AttributeError):
                    setattr(sig, key, value)
            elif key in ('posted_date', 'entry_date', 'exit_date') and value:
                try:
                    setattr(sig, key, datetime.fromisoformat(value).date())
                except (ValueError, TypeError):
                    setattr(sig, key, value)
            else:
                setattr(sig, key, value)
        return sig

    def add_signal_from_dict(self, data: Dict) -> TelegramSignal:
        """
        Add signal from dictionary (manual Telegram post).

        Expected keys:
            - symbol (required)
            - channel (required)
            - posted_date (required)
            - strategy
            - signal_source
            - entry_price
            - target_price
            - stop_loss
            - timeframe
            - confidence (1-10)
            - notes
        """
        signal = TelegramSignal()

        # Required fields
        signal.symbol = data.get('symbol', '').upper()
        signal.channel = data.get('channel', '')
        signal.posted_date = data.get('posted_date', date.today())

        # Optional fields
        signal.strategy = data.get('strategy', '')
        signal.timeframe = data.get('timeframe', '')
        signal.confidence = data.get('confidence', 5)
        signal.notes = data.get('notes', '')

        # Prices
        try:
            signal.entry_price = float(data.get('entry_price')) if data.get('entry_price') else None
        except (ValueError, TypeError):
            signal.entry_price = None

        try:
            signal.target_price = float(data.get('target_price')) if data.get('target_price') else None
        except (ValueError, TypeError):
            signal.target_price = None

        try:
            signal.stop_loss = float(data.get('stop_loss')) if data.get('stop_loss') else None
        except (ValueError, TypeError):
            signal.stop_loss = None

        # Source
        source = data.get('signal_source', 'OTHER')
        try:
            if isinstance(source, str):
                signal.signal_source = SignalSource[source.upper().replace(' ', '_')]
            else:
                signal.signal_source = source
        except (KeyError, AttributeError):
            signal.signal_source = SignalSource.OTHER

        # Metadata
        signal.metadata = data.get('metadata', {})

        # Generate ID
        signal.signal_id = self._generate_signal_id(signal)

        # Store
        self.signals[signal.signal_id] = signal
        self.save_signals()

        return signal

    def _generate_signal_id(self, signal: TelegramSignal) -> str:
        """Generate unique signal ID."""
        date_str = signal.posted_date.strftime('%Y%m%d') if signal.posted_date else 'unknown'
        channel_short = signal.channel[:10] if signal.channel else 'unknown'
        symbol = signal.symbol[:6] if signal.symbol else 'unknown'
        return f"{date_str}_{channel_short}_{symbol}_{len(self.signals)}"

    def update_signal(self, signal_id: str, **kwargs) -> Optional[TelegramSignal]:
        """Update signal fields (entry, exit, status, return)."""
        if signal_id not in self.signals:
            return None

        signal = self.signals[signal_id]

        for key, value in kwargs.items():
            if hasattr(signal, key):
                setattr(signal, key, value)

        # Calculate realized return if entry & exit filled
        if signal.entry_date and signal.exit_date and signal.entry_price and signal.realized_return is None:
            # We store realized_return separately as it may be provided
            pass

        self.save_signals()
        return signal

    def get_signal(self, signal_id: str) -> Optional[TelegramSignal]:
        """Retrieve single signal."""
        return self.signals.get(signal_id)

    def get_active_signals(self) -> List[TelegramSignal]:
        """Get all active/pending signals."""
        return [s for s in self.signals.values() if s.status in (SignalStatus.ACTIVE, SignalStatus.PENDING)]

    def get_signals_by_channel(self, channel: str) -> List[TelegramSignal]:
        """Get signals from specific Telegram channel."""
        return [s for s in self.signals.values() if s.channel.lower() == channel.lower()]

    def get_signals_by_symbol(self, symbol: str) -> List[TelegramSignal]:
        """Get all signals for a stock symbol."""
        return [s for s in self.signals.values() if s.symbol == symbol.upper()]

    def get_signals_by_date_range(self, start: date, end: date) -> List[TelegramSignal]:
        """Get signals posted in date range."""
        return [s for s in self.signals.values()
                if s.posted_date and start <= s.posted_date <= end]

    def get_winning_signals(self, min_return: float = 5.0) -> List[Tuple[TelegramSignal, float]]:
        """Get signals with positive return above threshold."""
        winners = []
        for signal in self.signals.values():
            if signal.realized_return and signal.realized_return >= min_return:
                winners.append((signal, signal.realized_return))
        return sorted(winners, key=lambda x: x[1], reverse=True)

    def get_signal_statistics(self) -> Dict:
        """Calculate performance statistics."""
        closed = [s for s in self.signals.values() if s.status == SignalStatus.CLOSED]

        if not closed:
            return {
                'total_signals': len(self.signals),
                'active_signals': len(self.get_active_signals()),
                'closed_signals': 0,
                'win_rate': 0,
                'avg_return': 0,
                'best_signal': None,
                'worst_signal': None,
            }

        returns = [s.realized_return for s in closed if s.realized_return is not None]
        winning = [r for r in returns if r > 0]

        best_sig = max(closed, key=lambda s: s.realized_return or 0, default=None)
        worst_sig = min(closed, key=lambda s: s.realized_return or 0, default=None)

        return {
            'total_signals': len(self.signals),
            'active_signals': len(self.get_active_signals()),
            'closed_signals': len(closed),
            'win_rate': round(len(winning) / len(returns) * 100, 1) if returns else 0,
            'avg_return': round(sum(returns) / len(returns), 2) if returns else 0,
            'total_return': round(sum(returns), 2) if returns else 0,
            'best_signal': best_sig.signal_id if best_sig else None,
            'best_return': best_sig.realized_return if best_sig else None,
            'worst_signal': worst_sig.signal_id if worst_sig else None,
            'worst_return': worst_sig.realized_return if worst_sig else None,
        }

    def save_signals(self) -> None:
        """Save signals to JSON."""
        try:
            json_file = self.signals_dir / 'signals.json'
            data = {sig_id: sig.to_dict() for sig_id, sig in self.signals.items()}
            with open(json_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving signals: {e}")

    def export_to_csv(self, filepath: str = None) -> Optional[str]:
        """Export signals to CSV."""
        if not HAS_PANDAS:
            print("pandas required for CSV export")
            return None

        if not filepath:
            filepath = self.signals_dir / 'signals_export.csv'

        try:
            data = [s.to_dict() for s in self.signals.values()]
            df = pd.DataFrame(data)
            df.to_csv(filepath, index=False)
            return str(filepath)
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            return None


if __name__ == '__main__':
    # Example: RPCI Signal from Rohan Das
    ts = TelegramSignals()

    rpci_signal = {
        'symbol': 'MOTHERSON',
        'channel': 'Rohan Das (@rohaninvestor)',
        'posted_date': date(2026, 6, 25),
        'strategy': 'RPCI Indicator',
        'signal_source': 'RPCI',
        'entry_price': None,  # Multiple entry zone
        'target_price': None,  # Multi-leg target
        'stop_loss': None,
        'timeframe': 'Medium-term (weeks)',
        'confidence': 8,
        'notes': (
            'RPCI identified MOTHERSON before SEBI RA recommendation. '
            'Stock recommended for next week accumulation. '
            'RPCI simplifies technical analysis with rule-based signals. '
            'Used by 1500+ traders including SEBI registered users.'
        ),
        'metadata': {
            'indicator': 'RPCI (Rule-based Pattern Confidence Indicator)',
            'user_count': '1500+',
            'feedback_channels': ['Telegram', 'Twitter'],
            'sebi_ra_confirmation': 'Yes (27 June)',
        }
    }

    signal = ts.add_signal_from_dict(rpci_signal)

    print("=== Rohan Das RPCI Signal ===")
    print(f"Signal ID: {signal.signal_id}")
    print(f"Stock: {signal.symbol}")
    print(f"Strategy: {signal.strategy}")
    print(f"Confidence: {signal.confidence}/10")
    print(f"Channel: {signal.channel}")
    print(f"\nNotes:\n{signal.notes}")

    print("\nMetadata:")
    for key, val in signal.metadata.items():
        print(f"  {key}: {val}")

    print("\n=== Statistics ===")
    stats = ts.get_signal_statistics()
    for key, val in stats.items():
        print(f"{key}: {val}")
