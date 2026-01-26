"""
Backfiller application for populating historical market data.

Fetches historical OHLCV data from exchanges and stores in database.
Supports multiple exchanges, symbols, and timeframes dynamically.
"""

import os
import argparse
import asyncio
from datetime import datetime, timedelta
from time import sleep
from pathlib import Path
import ccxt.pro as ccxt

from packages.database.db import DatabaseManager
from packages.logging.logger import setup_logger
from dotenv import load_dotenv

# Get project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Load environment variables
load_dotenv()

logger = setup_logger(__name__)

# Timeframe durations in milliseconds
TIMEFRAME_MS = {
    '1m': 60 * 1000,
    '5m': 5 * 60 * 1000,
    '15m': 15 * 60 * 1000,
    '30m': 30 * 60 * 1000,
    '1h': 60 * 60 * 1000,
    '4h': 4 * 60 * 60 * 1000,
    '8h': 8 * 60 * 60 * 1000,
    '1d': 24 * 60 * 60 * 1000,
    '1w': 7 * 24 * 60 * 60 * 1000,
    '1M': 30 * 24 * 60 * 60 * 1000,
}


class Backfiller:
    """
    Historical data backfiller for cryptocurrency exchanges.
    
    Fetches OHLCV data via CCXT and stores in database.
    """
    
    def __init__(self, exchange_name: str):
        """
        Initialize backfiller.
        
        Args:
            exchange_name: Name of exchange (e.g., 'mexc')
        """
        self.exchange_name = exchange_name
        self.db = DatabaseManager()  # Uses default project root path
        
        # Initialize exchange
        try:
            exchange_class = getattr(ccxt, exchange_name)
            self.exchange = exchange_class({
                'enableRateLimit': True,
                'apiKey': os.getenv(f'{exchange_name.upper()}_API_KEY'),
                'secret': os.getenv(f'{exchange_name.upper()}_API_SECRET'),
            })
            logger.info(f"Connected to {exchange_name} exchange")
        except Exception as e:
            logger.error(f"Failed to initialize {exchange_name}: {e}")
            raise
    
    async def backfill(self, symbol: str, timeframe: str, days: int = None):
        """
        Intelligent backfiller that automatically:
        1. Fills forward from latest timestamp (get updates)
        2. Detects and fills gaps in existing data
        3. Fills backwards from earliest timestamp (get more history)
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '1h')
            days: If specified, only fetch last N days (limits historical fetch)
        """
        logger.info(f"Starting intelligent backfill: {symbol} {timeframe}")
        
        # Get timeframe duration
        tf_ms = TIMEFRAME_MS.get(timeframe)
        if not tf_ms:
            logger.error(f"Unknown timeframe: {timeframe}")
            return
        
        # Check existing data
        latest_ts = self.db.get_latest_timestamp(self.exchange_name, symbol, timeframe)
        earliest_ts = self.db.get_earliest_timestamp(self.exchange_name, symbol, timeframe)
        existing_count = self.db.get_data_count(self.exchange_name, symbol, timeframe)
        
        if existing_count > 0:
            logger.info(f"Found {existing_count} existing candles from {datetime.fromtimestamp(earliest_ts/1000)} to {datetime.fromtimestamp(latest_ts/1000)}")
        
        total_inserted = 0
        
        # Determine what to fetch based on existing data
        now = int(datetime.now().timestamp() * 1000)
        
        # Always fetch backward from now
        if days:
            # Limited fetch based on --days
            since_ts = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            target_start = max(since_ts, earliest_ts) if earliest_ts else since_ts
            logger.info(f"=== Phase 1: Fetching backward from now (last {days} days) ===")
            inserted = await self._fetch_range(symbol, timeframe, tf_ms, target_start, now)
            total_inserted += inserted
            logger.info(f"Phase 1 complete: {inserted} new candles")
        elif earliest_ts:
            # We have data - only fetch from now to just before our earliest data
            # This will pick up new candles at the top, then stop when hitting existing data
            logger.info(f"=== Phase 1: Fetching backward from now to {datetime.fromtimestamp(earliest_ts/1000)} ===")
            target_start = earliest_ts - (tf_ms * 10)  # Stop just before our existing data
            inserted = await self._fetch_range(symbol, timeframe, tf_ms, target_start, now)
            total_inserted += inserted
            logger.info(f"Phase 1 complete: {inserted} new candles")
        else:
            # No data at all - fetch everything from now back to 2017
            logger.info(f"=== Phase 1: Fetching all available history from now ===")
            target_start = int(datetime(2017, 1, 1).timestamp() * 1000)
            inserted = await self._fetch_range(symbol, timeframe, tf_ms, target_start, now)
            total_inserted += inserted
            logger.info(f"Phase 1 complete: {inserted} new candles")
        
        # PHASE 2: Detect and fill gaps
        if existing_count > 0:
            logger.info(f"=== Phase 2: Checking for gaps ===")
            all_gaps = self.db.find_gaps(self.exchange_name, symbol, timeframe, tf_ms)
            
            # Filter out known unfillable gaps
            gaps = [
                (start, end) for start, end in all_gaps
                if not self.db.is_unfillable_gap(self.exchange_name, symbol, timeframe, start, end)
            ]
            
            unfillable_count = len(all_gaps) - len(gaps)
            if unfillable_count > 0:
                logger.info(f"Skipping {unfillable_count} known unfillable gap(s)")
            
            if gaps:
                logger.info(f"Found {len(gaps)} fillable gap(s)")
                failed_gaps = []
                
                for i, (gap_start, gap_end) in enumerate(gaps, 1):
                    logger.info(f"Gap {i}/{len(gaps)}: {datetime.fromtimestamp(gap_start/1000)} to {datetime.fromtimestamp(gap_end/1000)}")
                    inserted = await self._fetch_range(symbol, timeframe, tf_ms, gap_start, gap_end)
                    
                    if inserted == 0:
                        # No data available for this gap - mark as unfillable
                        logger.warning(f"  ⚠️  No data available - marking as unfillable")
                        self.db.mark_unfillable_gap(self.exchange_name, symbol, timeframe, gap_start, gap_end)
                        failed_gaps.append((gap_start, gap_end))
                    else:
                        total_inserted += inserted
                
                filled_count = len(gaps) - len(failed_gaps)
                if filled_count > 0:
                    logger.info(f"Phase 2 complete: filled {filled_count} gap(s)")
                if failed_gaps:
                    logger.info(f"Failed to fill {len(failed_gaps)} gap(s) - no data available from exchange")
            elif unfillable_count == 0:
                logger.info("No gaps found")
        
        logger.info(f"✅ Backfill complete: {total_inserted} total new candles inserted")
    
    async def _fetch_range(self, symbol: str, timeframe: str, tf_ms: int, start_ts: int, end_ts: int) -> int:
        """
        Fetch data for a specific range (backward from end_ts to start_ts).
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            tf_ms: Timeframe in milliseconds
            start_ts: Start timestamp (target oldest)
            end_ts: End timestamp (start from here, going backward)
            
        Returns:
            Number of candles inserted
        """
        total_inserted = 0
        consecutive_empty = 0
        consecutive_no_inserts = 0  # Track batches with 0 inserts
        iterations = 0
        max_iterations = 10000
        last_oldest_ts = None  # Track last batch's oldest timestamp to detect duplicates
        
        # Always start from end_ts and work backward
        # Start with a reasonable batch size (500 candles back)
        since = end_ts - (500 * tf_ms)
        
        while iterations < max_iterations:
            iterations += 1
            
            # Check if we've reached the start
            if since <= start_ts:
                break
            
            # Fetch OHLCV data
            try:
                ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
            except ccxt.NetworkError as e:
                logger.warning(f"Network error, retrying in 5s: {e}")
                sleep(5)
                continue
            except ccxt.ExchangeError as e:
                logger.error(f"Exchange error: {e}")
                break
            
            if not ohlcv or len(ohlcv) == 0:
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    break
                
                # Move backward
                since -= (1000 * tf_ms)
                continue
            
            consecutive_empty = 0
            
            # Check for duplicate data (reached oldest available)
            oldest_ts = ohlcv[0][0]
            if last_oldest_ts is not None and oldest_ts >= last_oldest_ts:
                # We're getting the same or newer data - no more history available
                logger.debug(f"Reached oldest available data at {datetime.fromtimestamp(oldest_ts/1000)}")
                break
            last_oldest_ts = oldest_ts
            
            # Prepare batch
            batch = []
            for candle in ohlcv:
                timestamp, open_price, high, low, close, volume = candle
                # Only include candles within the requested range
                if start_ts <= timestamp <= end_ts:
                    batch.append({
                        'exchange': self.exchange_name,
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'timestamp': timestamp,
                        'open': open_price,
                        'high': high,
                        'low': low,
                        'close': close,
                        'volume': volume
                    })
            
            # Insert batch
            if batch:
                inserted = self.db.insert_ohlcv_batch(batch)
                total_inserted += inserted
                
                if inserted > 0:
                    logger.info(f"  + {inserted} candles | Range: {datetime.fromtimestamp(batch[0]['timestamp']/1000)} to {datetime.fromtimestamp(batch[-1]['timestamp']/1000)}")
                    consecutive_no_inserts = 0  # Reset counter on successful insert
                else:
                    consecutive_no_inserts += 1
                    # If we get 3 batches in a row with no inserts, we're in existing data - stop
                    if consecutive_no_inserts >= 3:
                        logger.debug(f"Hit existing data (3 consecutive batches with 0 inserts), stopping")
                        break
            
            # Move to next position - always backward
            # Calculate next since based on actual data returned to ensure continuous coverage
            # Step back by the number of candles we just received to maintain pagination
            oldest_ts = ohlcv[0][0]
            batch_size = len(ohlcv)
            since = oldest_ts - (batch_size * tf_ms)
            
            # Rate limiting
            sleep(self.exchange.rateLimit / 1000)
        
        return total_inserted
    
    async def backfill_multiple(self, configs: list):
        """
        Backfill multiple symbol/timeframe combinations.
        
        Args:
            configs: List of dicts with keys: symbol, timeframe, days
        """
        for config in configs:
            symbol = config['symbol']
            timeframe = config['timeframe']
            days = config.get('days', 30)
            
            logger.info(f"{'='*60}")
            logger.info(f"Backfilling: {symbol} {timeframe}")
            logger.info(f"{'='*60}")
            
            try:
                await self.backfill(symbol, timeframe, days)
            except Exception as e:
                logger.error(f"Failed to backfill {symbol} {timeframe}: {e}")
                continue
            
            # Small delay between symbols
            sleep(2)


async def main():
    """Main entry point for backfiller"""
    parser = argparse.ArgumentParser(description='Backfill historical market data')
    parser.add_argument('--exchange', type=str, default='mexc', help='Exchange name')
    parser.add_argument('--symbol', type=str, help='Trading pair (e.g., BTC/USDT)')
    parser.add_argument('--timeframe', type=str, help='Timeframe (e.g., 1h)')
    parser.add_argument('--days', type=int, help='Days to backfill (omit to fetch all available history)')
    parser.add_argument('--all', action='store_true', help='Backfill all configured strategies')
    
    args = parser.parse_args()
    
    backfiller = Backfiller(args.exchange)
    
    if args.all:
        # Backfill all strategy configurations
        configs = [
            {'symbol': 'BTC/USDT', 'timeframe': '1h', 'days': None},  # All history
            {'symbol': 'BTC/USDT', 'timeframe': '4h', 'days': None},  # All history
            {'symbol': 'BTC/USDT', 'timeframe': '1m', 'days': 30},    # Last 30 days (1m is large)
            {'symbol': 'ETH/USDT', 'timeframe': '15m', 'days': None}, # All history
        ]
        await backfiller.backfill_multiple(configs)
    elif args.symbol and args.timeframe:
        # Backfill single symbol/timeframe
        await backfiller.backfill(args.symbol, args.timeframe, args.days)
    else:
        logger.error("Must specify --symbol and --timeframe, or use --all")
        return 1
    
    # Close exchange connection
    await backfiller.exchange.close()
    
    return 0


if __name__ == '__main__':
    exit(asyncio.run(main()))
