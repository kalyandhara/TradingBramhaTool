#!/usr/bin/env python3
"""
volume_fetcher.py
Enhanced volume data fetching from multiple sources with fallbacks.

Sources (in order of priority):
1. Yahoo Finance (yfinance) — Most reliable for NSE stocks
2. NSE Direct API (if available)
3. Cached local data

Usage:
  from volume_fetcher import VolumeFetcher
  vf = VolumeFetcher()
  df = vf.fetch_with_volume('RELIANCE', days=300)
  print(df[['close', 'volume']])
"""

from datetime import datetime, date, timedelta
from typing import Dict, Optional, Tuple
import logging

try:
    import pandas as pd
    import numpy as np
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

logger = logging.getLogger(__name__)


class VolumeFetcher:
    """Fetch OHLCV data with volume from multiple sources."""

    # Minimum thresholds
    MIN_BARS = 60
    # Minimum 10-day average TURNOVER in rupees, not a share count: shares x
    # price is what you can actually get in and out of, and a count alone
    # rejects the most tradable names for being expensive (MRF moves Rs 60 cr
    # on 4,656 shares). Same floor as screener_pipeline.MIN_TURNOVER and must be
    # kept in step with it: this class is the primary fetch path, that constant
    # is what the dashboard quotes back to the user, and the two disagreeing
    # would show a wrong number in the warning.
    MIN_TURNOVER = 10_000_000

    def __init__(self, verbose: bool = False):
        """
        Initialize volume fetcher.

        Args:
            verbose: Enable debug logging
        """
        self.verbose = verbose
        self.cache = {}  # Local cache of fetched data

        if verbose:
            logging.basicConfig(level=logging.DEBUG)

    def fetch_with_volume(
        self,
        symbol: str,
        days: int = 300,
        use_cache: bool = True,
        validate: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data with volume validation.

        Args:
            symbol: Stock symbol (e.g., 'RELIANCE')
            days: Number of days of history
            use_cache: Use cached data if available
            validate: Validate volume data quality

        Returns:
            pd.DataFrame with columns: [open, high, low, close, volume, adjclose]
            or None if fetch fails
        """
        if not HAS_PANDAS:
            logger.error("pandas required: pip install pandas")
            return None

        # Check cache
        cache_key = f"{symbol}_{days}"
        if use_cache and cache_key in self.cache:
            if self.verbose:
                logger.info(f"Using cached data for {symbol}")
            return self.cache[cache_key]

        # Try yfinance (primary source)
        df = self._fetch_yfinance(symbol, days)

        if df is None:
            logger.warning(f"Failed to fetch {symbol} from yfinance, trying NSE...")
            # Fallback to NSE (if available)
            df = self._fetch_nse_direct(symbol, days)

        if df is None:
            logger.error(f"Could not fetch data for {symbol} from any source")
            return None

        # Validate data quality
        if validate:
            if not self._validate_data(symbol, df):
                return None

        # Cache result
        if use_cache:
            self.cache[cache_key] = df

        return df

    def _fetch_yfinance(self, symbol: str, days: int) -> Optional[pd.DataFrame]:
        """Fetch from Yahoo Finance."""
        if not HAS_YFINANCE:
            logger.warning("yfinance not installed: pip install yfinance")
            return None

        ticker = f"{symbol}.NS"  # NSE format

        try:
            if self.verbose:
                logger.info(f"Fetching {ticker} from yfinance...")

            period = "max" if not days or days <= 0 else f"{days}d"
            df = yf.download(
                ticker,
                period=period,
                interval="1d",
                progress=False,
                auto_adjust=True
            )

            if df is None or df.empty:
                logger.warning(f"Empty data from yfinance for {ticker}")
                return None

            # Normalize column names
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0].lower() for c in df.columns]
            else:
                df.columns = [c.lower() for c in df.columns]

            # Ensure required columns exist
            required = ['open', 'high', 'low', 'close', 'volume']
            missing = [col for col in required if col not in df.columns]
            if missing:
                logger.error(f"Missing columns in yfinance data: {missing}")
                return None

            # Clean volume data (remove NaN, zero)
            df['volume'] = df['volume'].fillna(0)
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0)
            df['volume'] = df['volume'].astype(int)

            if self.verbose:
                logger.info(f"✓ Fetched {len(df)} bars for {symbol}")
                logger.info(f"  Date range: {df.index[0].date()} to {df.index[-1].date()}")
                logger.info(f"  Avg volume: {df['volume'].tail(10).mean():,.0f}")

            return df

        except Exception as e:
            logger.error(f"yfinance error for {ticker}: {e}")
            return None

    def _fetch_nse_direct(self, symbol: str, days: int) -> Optional[pd.DataFrame]:
        """
        Fallback: Fetch from NSE API directly.

        Note: NSE doesn't provide a direct public API for historical data.
        This is a placeholder for future integration with NSE scrip API
        or alternative sources like India VIX, NSE data portal, etc.
        """
        logger.warning("NSE direct API not yet implemented (use yfinance)")
        return None

    def _validate_data(self, symbol: str, df: pd.DataFrame) -> bool:
        """Validate data quality and volume."""
        if len(df) < self.MIN_BARS:
            logger.warning(
                f"{symbol}: Only {len(df)} bars (need ≥{self.MIN_BARS})"
            )
            return False

        # Check traded value
        avg_turnover = float((df['close'] * df['volume']).tail(10).mean())
        if avg_turnover < self.MIN_TURNOVER:
            logger.warning(
                f"{symbol}: Avg turnover Rs {avg_turnover / 1e7:,.2f} cr < "
                f"Rs {self.MIN_TURNOVER / 1e7:,.2f} cr (illiquid)"
            )
            return False

        # Check for too many NaN values
        nan_pct = df['volume'].isna().sum() / len(df) * 100
        if nan_pct > 10:
            logger.warning(f"{symbol}: {nan_pct:.1f}% NaN in volume data")
            return False

        if self.verbose:
            logger.info(f"✓ {symbol} data validation passed")

        return True

    def get_volume_stats(self, df: pd.DataFrame) -> Dict:
        """Get volume statistics."""
        if df is None or df.empty or 'volume' not in df.columns:
            return {}

        vol = df['volume']
        return {
            'avg_volume': float(vol.mean()),
            'median_volume': float(vol.median()),
            'max_volume': float(vol.max()),
            'min_volume': float(vol.min()),
            'vol_10d_avg': float(vol.tail(10).mean()),
            'vol_20d_avg': float(vol.tail(20).mean()),
            'vol_trend': 'increasing' if vol.tail(10).mean() > vol.tail(20).mean() else 'decreasing',
            'latest_volume': int(vol.iloc[-1]),
        }

    def fill_missing_volume(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fill missing volume data with forward/backward fill."""
        if df is None or 'volume' not in df.columns:
            return df

        df['volume'] = df['volume'].fillna(method='ffill')
        df['volume'] = df['volume'].fillna(method='bfill')
        df['volume'] = df['volume'].fillna(0)

        return df

    def scale_volume_for_chart(self, df: pd.DataFrame, target_max: float = 30000000) -> pd.DataFrame:
        """
        Scale volume to reasonable chart display values.

        Some charts have trouble with very large volume values (billions).
        This creates a scaled version for display.
        """
        if df is None or 'volume' not in df.columns:
            return df

        vol = df['volume'].copy()
        vol_max = vol.max()

        if vol_max == 0:
            return df

        # Scale to target max
        df['volume_scaled'] = (vol / vol_max) * target_max

        return df

    def compare_sources(self, symbol: str, days: int = 30) -> Dict:
        """
        Compare volume data from available sources.

        Useful for debugging missing/mismatched volume data.
        """
        results = {}

        # Try yfinance
        try:
            df_yf = self._fetch_yfinance(symbol, days)
            if df_yf is not None:
                results['yfinance'] = {
                    'bars': len(df_yf),
                    'avg_volume': df_yf['volume'].mean(),
                    'latest_volume': df_yf['volume'].iloc[-1],
                    'date_range': f"{df_yf.index[0].date()} to {df_yf.index[-1].date()}",
                }
            else:
                results['yfinance'] = {'error': 'No data'}
        except Exception as e:
            results['yfinance'] = {'error': str(e)}

        return results


def test_volume_fetcher():
    """Test volume fetcher with sample symbols."""
    vf = VolumeFetcher(verbose=True)

    test_symbols = ['RELIANCE', 'TCS', 'INFY', 'MOTHERSON']

    print("\n=== Testing Volume Fetcher ===\n")

    for symbol in test_symbols:
        print(f"Fetching {symbol}...")
        df = vf.fetch_with_volume(symbol, days=100)

        if df is not None:
            stats = vf.get_volume_stats(df)
            print(f"  [OK] {len(df)} bars fetched")
            print(f"    Avg Volume: {stats['avg_volume']:,.0f}")
            print(f"    Latest Volume: {stats['latest_volume']:,.0f}")
            print(f"    Volume Trend: {stats['vol_trend']}")
        else:
            print(f"  [ERROR] Failed to fetch {symbol}")

        print()

    print("=== Source Comparison ===\n")
    comparison = vf.compare_sources('RELIANCE', days=30)
    for source, data in comparison.items():
        print(f"{source}: {data}")


if __name__ == '__main__':
    if not HAS_YFINANCE:
        print("Installing yfinance...")
        import subprocess
        subprocess.check_call(['pip', 'install', 'yfinance', '-q'])

    test_volume_fetcher()
