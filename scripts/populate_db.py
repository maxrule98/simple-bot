#!/usr/bin/env python3
"""
Populate database with historical data for multiple symbols and timeframes.

This script automates the backfilling process by:
1. Iterating through configured exchanges
2. Fetching popular trading pairs
3. Running backfiller for each symbol/timeframe combination

Usage:
    python scripts/populate_db.py
    python scripts/populate_db.py --exchange mexc --days 365
    python scripts/populate_db.py --all  # Fetch maximum historical data
"""

import argparse
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from packages.logging.logger import setup_logger
from apps.backfiller.main import Backfiller

logger = setup_logger(__name__)

# =============================================================================
# CONFIGURATION: Popular symbols and timeframes
# =============================================================================

EXCHANGES = ["mexc"]

# Most liquid/popular trading pairs (focus on major coins)
POPULAR_SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "BNB/USDT",
    "SOL/USDT",
    "XRP/USDT",
]

# Common timeframes for trading strategies
POPULAR_TIMEFRAMES = [
    "1m",   # Scalping
    "5m",   # Short-term
    "15m",  # Intraday
    "1h",   # Swing trading
    "4h",   # Position trading
    "1d",   # Long-term
]

# Extended list (uncomment if needed)
# EXTENDED_SYMBOLS = [
#     "ADA/USDT", "AVAX/USDT", "DOGE/USDT", "DOT/USDT", "LINK/USDT",
#     "MATIC/USDT", "UNI/USDT", "LTC/USDT", "ATOM/USDT", "ETC/USDT",
# ]


async def populate_data(exchange: str, symbols: list, timeframes: list, days: int = None):
    """
    Populate database with historical data for given symbols and timeframes.
    
    Args:
        exchange: Exchange name (e.g., 'mexc')
        symbols: List of trading pairs (e.g., ['BTC/USDT', 'ETH/USDT'])
        timeframes: List of timeframes (e.g., ['1h', '4h', '1d'])
        days: Number of days to fetch (None = fetches all available history)
    """
    total_combinations = len(symbols) * len(timeframes)
    current = 0
    
    logger.info(f"🚀 Starting data population for {exchange}")
    logger.info(f"📊 Symbols: {len(symbols)}, Timeframes: {len(timeframes)}, Total: {total_combinations} combinations")
    logger.info("=" * 80)
    
    results = {
        "success": [],
        "failed": [],
        "skipped": []
    }
    
    for symbol in symbols:
        for timeframe in timeframes:
            current += 1
            
            logger.info(f"[{current}/{total_combinations}] Processing {symbol} {timeframe}")
            logger.info("-" * 80)
            
            try:
                # Create backfiller instance
                backfiller = Backfiller(exchange_name=exchange)
                
                # Run backfill (days=None means fetch all history)
                await backfiller.backfill(
                    symbol=symbol,
                    timeframe=timeframe,
                    days=days
                )
                
                # Close exchange connection
                await backfiller.exchange.close()
                
                results["success"].append((symbol, timeframe))
                logger.info(f"✅ Completed: {symbol} {timeframe}")
                
            except Exception as e:
                logger.error(f"❌ Failed: {symbol} {timeframe} - {e}")
                results["failed"].append((symbol, timeframe, str(e)))
            
            logger.info("-" * 80)
    
    # Summary
    logger.info("=" * 80)
    logger.info("📈 POPULATION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"✅ Successful: {len(results['success'])}/{total_combinations}")
    logger.info(f"❌ Failed: {len(results['failed'])}/{total_combinations}")
    
    if results["failed"]:
        logger.warning("Failed combinations:")
        for symbol, timeframe, error in results["failed"]:
            logger.warning(f"  - {symbol} {timeframe}: {error}")
    
    logger.info("🎉 Data population complete!")


async def main():
    parser = argparse.ArgumentParser(
        description="Populate database with historical market data"
    )
    
    parser.add_argument(
        "--exchange",
        type=str,
        default="mexc",
        choices=EXCHANGES,
        help="Exchange to fetch data from (default: mexc)"
    )
    
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        help="Specific symbols to fetch (default: popular symbols)"
    )
    
    parser.add_argument(
        "--timeframes",
        nargs="+",
        default=None,
        help="Specific timeframes to fetch (default: popular timeframes)"
    )
    
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Number of days to fetch (omit to fetch all available history)"
    )
    
    parser.add_argument(
        "--extended",
        action="store_true",
        help="Include extended symbol list (more altcoins)"
    )
    
    args = parser.parse_args()
    
    # Determine which symbols and timeframes to use
    symbols = args.symbols if args.symbols else POPULAR_SYMBOLS
    timeframes = args.timeframes if args.timeframes else POPULAR_TIMEFRAMES
    
    # if args.extended:
    #     symbols.extend(EXTENDED_SYMBOLS)
    
    # Display configuration
    logger.info("🔧 Configuration:")
    logger.info(f"  Exchange: {args.exchange}")
    logger.info(f"  Symbols: {', '.join(symbols)}")
    logger.info(f"  Timeframes: {', '.join(timeframes)}")
    
    if args.days:
        logger.info(f"  Days: {args.days}")
    else:
        logger.info(f"  Days: All available history")
    
    logger.info("")
    
    # Confirm before starting
    total = len(symbols) * len(timeframes)
    logger.warning(f"⚠️  This will run {total} backfill operations")
    
    if total > 20:
        response = input("Continue? [y/N]: ")
        if response.lower() != 'y':
            logger.info("Cancelled by user")
            return
    
    # Start population
    start_time = datetime.now()
    
    await populate_data(
        exchange=args.exchange,
        symbols=symbols,
        timeframes=timeframes,
        days=args.days
    )
    
    # Calculate duration
    duration = datetime.now() - start_time
    logger.info(f"⏱️  Total duration: {duration}")


if __name__ == "__main__":
    asyncio.run(main())
