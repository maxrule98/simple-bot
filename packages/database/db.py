"""
Database connection and query management for the trading bot.

Handles SQLite connections with WAL mode for concurrent access.
Uses the schema from schema.py for initialization.
"""

import sqlite3
import os
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from pathlib import Path

from packages.logging.logger import setup_logger

# Get project root (2 levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

logger = setup_logger(__name__)


class DatabaseManager:
    """
    Manages SQLite database connections and queries.
    
    Supports concurrent reads/writes via WAL mode.
    Thread-safe for multi-instance deployments.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file (default: PROJECT_ROOT/data/trading.db)
        """
        if db_path is None:
            db_path = str(PROJECT_ROOT / "data" / "trading.db")
        self.db_path = db_path
        
        # Ensure data directory exists
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database if it doesn't exist
        if not Path(db_path).exists():
            logger.info(f"Database not found at {db_path}, initializing...")
            self._initialize_database()
        else:
            logger.info(f"Connected to existing database at {db_path}")
    
    def _initialize_database(self):
        """Initialize database with schema from schema.py"""
        import schema
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Enable WAL mode and foreign keys
            cursor.execute(schema.PRAGMA_WAL)
            cursor.execute(schema.PRAGMA_FOREIGN_KEYS)
            
            # Create market data tables
            cursor.execute(schema.CREATE_OHLCV_TABLE)
            for index in schema.CREATE_OHLCV_INDEXES:
                cursor.execute(index)
            
            cursor.execute(schema.CREATE_TICKER_TABLE)
            for index in schema.CREATE_TICKER_INDEXES:
                cursor.execute(index)
            
            # Create strategy tables
            cursor.execute(schema.CREATE_STRATEGY_METADATA_TABLE)
            for index in schema.CREATE_STRATEGY_INDEXES:
                cursor.execute(index)
            
            cursor.execute(schema.CREATE_TRADES_TABLE)
            for index in schema.CREATE_TRADES_INDEXES:
                cursor.execute(index)
            
            cursor.execute(schema.CREATE_POSITIONS_TABLE)
            for index in schema.CREATE_POSITIONS_INDEXES:
                cursor.execute(index)
            
            cursor.execute(schema.CREATE_SIGNALS_TABLE)
            for index in schema.CREATE_SIGNALS_INDEXES:
                cursor.execute(index)
            
            cursor.execute(schema.CREATE_INDICATOR_CACHE_TABLE)
            for index in schema.CREATE_INDICATOR_CACHE_INDEXES:
                cursor.execute(index)
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        
        Yields:
            sqlite3.Connection: Database connection
            
        Example:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM ohlcv_data")
        """
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row  # Access columns by name
        try:
            yield conn
        finally:
            conn.close()
    
    def insert_ohlcv(self, exchange: str, symbol: str, timeframe: str, 
                     timestamp: int, open_price: float, high: float, 
                     low: float, close: float, volume: float) -> bool:
        """
        Insert OHLCV data (ignore if duplicate).
        
        Args:
            exchange: Exchange name (e.g., 'mexc')
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '1h')
            timestamp: Unix timestamp in milliseconds
            open_price: Open price
            high: High price
            low: Low price
            close: Close price
            volume: Trading volume
            
        Returns:
            True if inserted, False if duplicate
        """
        query = """
        INSERT OR IGNORE INTO ohlcv_data 
        (exchange, symbol, timeframe, timestamp, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    exchange, symbol, timeframe, timestamp,
                    open_price, high, low, close, volume
                ))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Failed to insert OHLCV data: {e}")
            return False
    
    def insert_ohlcv_batch(self, data: List[Dict[str, Any]]) -> int:
        """
        Insert multiple OHLCV records in batch.
        
        Args:
            data: List of OHLCV dictionaries with keys:
                  exchange, symbol, timeframe, timestamp, open, high, low, close, volume
                  
        Returns:
            Number of records inserted
        """
        query = """
        INSERT OR IGNORE INTO ohlcv_data 
        (exchange, symbol, timeframe, timestamp, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, [
                    (d['exchange'], d['symbol'], d['timeframe'], d['timestamp'],
                     d['open'], d['high'], d['low'], d['close'], d['volume'])
                    for d in data
                ])
                conn.commit()
                return cursor.rowcount
        except sqlite3.Error as e:
            logger.error(f"Failed to batch insert OHLCV data: {e}")
            return 0
    
    def get_ohlcv(self, exchange: str, symbol: str, timeframe: str,
                  since: Optional[int] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch OHLCV data from database.
        
        Args:
            exchange: Exchange name
            symbol: Trading pair
            timeframe: Candle timeframe
            since: Optional start timestamp
            limit: Optional max number of records
            
        Returns:
            List of OHLCV dictionaries
        """
        query = """
        SELECT timestamp, open, high, low, close, volume
        FROM ohlcv_data
        WHERE exchange = ? AND symbol = ? AND timeframe = ?
        """
        
        params = [exchange, symbol, timeframe]
        
        if since:
            query += " AND timestamp >= ?"
            params.append(since)
        
        query += " ORDER BY timestamp ASC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to fetch OHLCV data: {e}")
            return []
    
    def get_latest_timestamp(self, exchange: str, symbol: str, timeframe: str) -> Optional[int]:
        """
        Get the latest timestamp for a given exchange/symbol/timeframe.
        
        Args:
            exchange: Exchange name
            symbol: Trading pair
            timeframe: Candle timeframe
            
        Returns:
            Latest timestamp in milliseconds, or None if no data exists
        """
        query = """
        SELECT MAX(timestamp) as latest
        FROM ohlcv_data
        WHERE exchange = ? AND symbol = ? AND timeframe = ?
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (exchange, symbol, timeframe))
                result = cursor.fetchone()
                return result['latest'] if result['latest'] else None
        except sqlite3.Error as e:
            logger.error(f"Failed to get latest timestamp: {e}")
            return None
    
    def get_earliest_timestamp(self, exchange: str, symbol: str, timeframe: str) -> Optional[int]:
        """
        Get the earliest timestamp for a given exchange/symbol/timeframe.
        
        Args:
            exchange: Exchange name
            symbol: Trading pair
            timeframe: Candle timeframe
            
        Returns:
            Earliest timestamp in milliseconds, or None if no data exists
        """
        query = """
        SELECT MIN(timestamp) as earliest
        FROM ohlcv_data
        WHERE exchange = ? AND symbol = ? AND timeframe = ?
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (exchange, symbol, timeframe))
                result = cursor.fetchone()
                return result['earliest'] if result['earliest'] else None
        except sqlite3.Error as e:
            logger.error(f"Failed to get earliest timestamp: {e}")
            return None
    
    def get_data_count(self, exchange: str, symbol: str, timeframe: str) -> int:
        """
        Get count of records for a given exchange/symbol/timeframe.
        
        Args:
            exchange: Exchange name
            symbol: Trading pair
            timeframe: Candle timeframe
            
        Returns:
            Number of records
        """
        query = """
        SELECT COUNT(*) as count
        FROM ohlcv_data
        WHERE exchange = ? AND symbol = ? AND timeframe = ?
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (exchange, symbol, timeframe))
                result = cursor.fetchone()
                return result['count'] if result else 0
        except sqlite3.Error as e:
            logger.error(f"Failed to get data count: {e}")
            return 0
    
    def find_gaps(self, exchange: str, symbol: str, timeframe: str, tf_ms: int) -> List[tuple]:
        """
        Find gaps in OHLCV data where timestamps are missing.
        
        Args:
            exchange: Exchange name
            symbol: Trading pair
            timeframe: Candle timeframe
            tf_ms: Timeframe in milliseconds
            
        Returns:
            List of (gap_start, gap_end) tuples in milliseconds
        """
        query = """
        WITH RECURSIVE
        expected AS (
            SELECT 
                timestamp as ts,
                LEAD(timestamp) OVER (ORDER BY timestamp) as next_ts
            FROM ohlcv_data
            WHERE exchange = ? AND symbol = ? AND timeframe = ?
            ORDER BY timestamp
        )
        SELECT ts as gap_start, next_ts as gap_end
        FROM expected
        WHERE next_ts - ts > ?
        LIMIT 100
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # A gap is where the next timestamp is more than 2x the timeframe (allowing for small variations)
                cursor.execute(query, (exchange, symbol, timeframe, tf_ms * 2))
                gaps = [(row['gap_start'], row['gap_end']) for row in cursor.fetchall()]
                return gaps
        except sqlite3.Error as e:
            logger.error(f"Failed to find gaps: {e}")
            return []
    
    def is_unfillable_gap(self, exchange: str, symbol: str, timeframe: str, gap_start: int, gap_end: int) -> bool:
        """
        Check if a gap is marked as unfillable.
        
        Args:
            exchange: Exchange name
            symbol: Trading pair
            timeframe: Candle timeframe
            gap_start: Gap start timestamp (ms)
            gap_end: Gap end timestamp (ms)
            
        Returns:
            True if gap is marked as unfillable
        """
        query = """
            SELECT COUNT(*) as count FROM unfillable_gaps
            WHERE exchange = ? AND symbol = ? AND timeframe = ?
            AND gap_start = ? AND gap_end = ?
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (exchange, symbol, timeframe, gap_start, gap_end))
                result = cursor.fetchone()
                return result['count'] > 0 if result else False
        except sqlite3.Error as e:
            logger.error(f"Failed to check unfillable gap: {e}")
            return False
    
    def mark_unfillable_gap(self, exchange: str, symbol: str, timeframe: str, gap_start: int, gap_end: int) -> None:
        """
        Mark a gap as unfillable (no data available from exchange).
        
        Args:
            exchange: Exchange name
            symbol: Trading pair
            timeframe: Candle timeframe
            gap_start: Gap start timestamp (ms)
            gap_end: Gap end timestamp (ms)
        """
        query = """
            INSERT OR IGNORE INTO unfillable_gaps (exchange, symbol, timeframe, gap_start, gap_end)
            VALUES (?, ?, ?, ?, ?)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (exchange, symbol, timeframe, gap_start, gap_end))
                conn.commit()
                logger.debug(f"Marked gap as unfillable: {exchange} {symbol} {timeframe} {gap_start} -> {gap_end}")
        except sqlite3.Error as e:
            logger.error(f"Failed to mark unfillable gap: {e}")
