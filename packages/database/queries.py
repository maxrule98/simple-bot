"""
Centralized database queries for DRY principle.

All SQL queries are defined here as reusable functions to avoid duplication
across the codebase. This makes it easier to maintain, test, and optimize queries.
"""

from typing import List, Dict, Any, Optional
import sqlite3


# ============================================================================
# OHLCV Data Queries
# ============================================================================

def insert_ohlcv(
    conn: sqlite3.Connection,
    exchange: str,
    symbol: str,
    timeframe: str,
    timestamp: int,
    open_price: float,
    high: float,
    low: float,
    close: float,
    volume: float,
) -> bool:
    """
    Insert OHLCV data (ignore if duplicate).
    
    Args:
        conn: Database connection
        exchange: Exchange name
        symbol: Trading pair
        timeframe: Candle timeframe
        timestamp: Unix timestamp (ms)
        open_price: Open price
        high: High price
        low: Low price
        close: Close price
        volume: Volume
        
    Returns:
        True if inserted, False if duplicate
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO ohlcv_data 
        (exchange, symbol, timeframe, timestamp, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (exchange, symbol, timeframe, timestamp, open_price, high, low, close, volume),
    )
    conn.commit()
    return cursor.rowcount > 0


def insert_ohlcv_replace(
    conn: sqlite3.Connection,
    exchange: str,
    symbol: str,
    timeframe: str,
    timestamp: int,
    open_price: float,
    high: float,
    low: float,
    close: float,
    volume: float,
):
    """
    Insert or replace OHLCV data (for updating forming candles).
    
    Use this for real-time WebSocket data that updates as candles form.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO ohlcv_data
        (exchange, symbol, timeframe, timestamp, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (exchange, symbol, timeframe, timestamp, open_price, high, low, close, volume),
    )
    conn.commit()


def insert_ohlcv_batch(
    conn: sqlite3.Connection, data: List[Dict[str, Any]]
) -> int:
    """
    Insert multiple OHLCV records in batch.
    
    Args:
        conn: Database connection
        data: List of dicts with keys: exchange, symbol, timeframe, timestamp,
              open, high, low, close, volume
              
    Returns:
        Number of records inserted
    """
    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT OR IGNORE INTO ohlcv_data 
        (exchange, symbol, timeframe, timestamp, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                d["exchange"],
                d["symbol"],
                d["timeframe"],
                d["timestamp"],
                d["open"],
                d["high"],
                d["low"],
                d["close"],
                d["volume"],
            )
            for d in data
        ],
    )
    conn.commit()
    return cursor.rowcount


def get_ohlcv(
    conn: sqlite3.Connection,
    exchange: str,
    symbol: str,
    timeframe: str,
    since: Optional[int] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch OHLCV data from database.
    
    Args:
        conn: Database connection
        exchange: Exchange name
        symbol: Trading pair
        timeframe: Candle timeframe
        since: Optional start timestamp
        limit: Optional max records
        
    Returns:
        List of OHLCV dictionaries
    """
    cursor = conn.cursor()
    
    query = """
        SELECT timestamp, open, high, low, close, volume
        FROM ohlcv_data
        WHERE exchange = ? AND symbol = ? AND timeframe = ?
    """
    params = [exchange, symbol, timeframe]
    
    if since is not None:
        query += " AND timestamp >= ?"
        params.append(since)
    
    query += " ORDER BY timestamp ASC"
    
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)
    
    cursor.execute(query, params)
    
    return [
        {
            "timestamp": row[0],
            "open": row[1],
            "high": row[2],
            "low": row[3],
            "close": row[4],
            "volume": row[5],
        }
        for row in cursor.fetchall()
    ]


# ============================================================================
# Ticker Data Queries
# ============================================================================

def insert_ticker(
    conn: sqlite3.Connection,
    exchange: str,
    symbol: str,
    timestamp: int,
    bid: float,
    ask: float,
    last: float,
    volume_24h: float,
):
    """Insert ticker data."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO ticker_data
        (exchange, symbol, timestamp, bid, ask, last, volume_24h)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (exchange, symbol, timestamp, bid, ask, last, volume_24h),
    )
    conn.commit()


# ============================================================================
# Signal Queries
# ============================================================================

def insert_signal(
    conn: sqlite3.Connection,
    strategy_id: str,
    exchange: str,
    symbol: str,
    signal_type: str,
    signal_source: str,
    confidence: float,
    reason: str,
    metadata: str,
    timestamp: int,
):
    """Insert trading signal."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO signals (
            strategy_id, exchange, symbol, signal_type, signal_source,
            confidence, reason, metadata, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            strategy_id,
            exchange,
            symbol,
            signal_type,
            signal_source,
            confidence,
            reason,
            metadata,
            timestamp,
        ),
    )
    conn.commit()


def get_signals(
    conn: sqlite3.Connection,
    strategy_id: str,
    since: Optional[int] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Fetch signals for strategy."""
    cursor = conn.cursor()
    
    query = """
        SELECT signal_id, signal_type, signal_source, confidence, reason, 
               metadata, timestamp
        FROM signals
        WHERE strategy_id = ?
    """
    params = [strategy_id]
    
    if since is not None:
        query += " AND timestamp >= ?"
        params.append(since)
    
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    
    return [
        {
            "signal_id": row[0],
            "signal_type": row[1],
            "signal_source": row[2],
            "confidence": row[3],
            "reason": row[4],
            "metadata": row[5],
            "timestamp": row[6],
        }
        for row in cursor.fetchall()
    ]


# ============================================================================
# Trade Queries
# ============================================================================

def insert_trade(
    conn: sqlite3.Connection,
    strategy_id: str,
    exchange: str,
    symbol: str,
    timeframe: str,
    order_id: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float,
    cost: float,
    fee: float,
    timestamp: int,
    pnl: float = 0.0,
    pnl_percent: float = 0.0,
):
    """Insert trade record."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO trades (
            strategy_id, exchange, symbol, timeframe, order_id, side,
            order_type, quantity, price, cost, fee, timestamp, pnl, pnl_percent
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            strategy_id,
            exchange,
            symbol,
            timeframe,
            order_id,
            side,
            order_type,
            quantity,
            price,
            cost,
            fee,
            timestamp,
            pnl,
            pnl_percent,
        ),
    )
    conn.commit()


def get_trades(
    conn: sqlite3.Connection,
    strategy_id: str,
    since: Optional[int] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Fetch trades for strategy."""
    cursor = conn.cursor()
    
    query = """
        SELECT trade_id, order_id, side, order_type, quantity, price, 
               cost, fee, pnl, pnl_percent, timestamp
        FROM trades
        WHERE strategy_id = ?
    """
    params = [strategy_id]
    
    if since is not None:
        query += " AND timestamp >= ?"
        params.append(since)
    
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    
    return [
        {
            "trade_id": row[0],
            "order_id": row[1],
            "side": row[2],
            "order_type": row[3],
            "quantity": row[4],
            "price": row[5],
            "cost": row[6],
            "fee": row[7],
            "pnl": row[8],
            "pnl_percent": row[9],
            "timestamp": row[10],
        }
        for row in cursor.fetchall()
    ]


# ============================================================================
# Position Queries
# ============================================================================

def get_active_position(
    conn: sqlite3.Connection, strategy_id: str, symbol: str
) -> Optional[Dict[str, Any]]:
    """Get active position for strategy."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT position_id, side, entry_price, quantity, entry_time,
               unrealized_pnl, realized_pnl
        FROM positions
        WHERE strategy_id = ? AND symbol = ? AND status = 'open'
        ORDER BY entry_time DESC
        LIMIT 1
        """,
        (strategy_id, symbol),
    )
    
    row = cursor.fetchone()
    if row is None:
        return None
    
    return {
        "position_id": row[0],
        "side": row[1],
        "entry_price": row[2],
        "quantity": row[3],
        "entry_time": row[4],
        "unrealized_pnl": row[5],
        "realized_pnl": row[6],
    }


# ============================================================================
# Strategy Metadata Queries
# ============================================================================

def insert_or_update_strategy_metadata(
    conn: sqlite3.Connection,
    strategy_id: str,
    name: str,
    exchange: str,
    symbol: str,
    timeframe: str,
    config_json: str,
):
    """Insert or update strategy metadata."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO strategy_metadata
        (strategy_id, name, exchange, symbol, timeframe, config_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        (strategy_id, name, exchange, symbol, timeframe, config_json),
    )
    conn.commit()


def get_strategy_metadata(
    conn: sqlite3.Connection, strategy_id: str
) -> Optional[Dict[str, Any]]:
    """Get strategy metadata."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT name, exchange, symbol, timeframe, config_json, created_at, updated_at
        FROM strategy_metadata
        WHERE strategy_id = ?
        """,
        (strategy_id,),
    )
    
    row = cursor.fetchone()
    if row is None:
        return None
    
    return {
        "name": row[0],
        "exchange": row[1],
        "symbol": row[2],
        "timeframe": row[3],
        "config_json": row[4],
        "created_at": row[5],
        "updated_at": row[6],
    }


# ============================================================================
# Indicator Cache Queries
# ============================================================================

def insert_indicator_cache(
    conn: sqlite3.Connection,
    exchange: str,
    symbol: str,
    timeframe: str,
    indicator_name: str,
    timestamp: int,
    value: float,
):
    """Cache indicator value."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO indicator_cache
        (exchange, symbol, timeframe, indicator_name, timestamp, value)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (exchange, symbol, timeframe, indicator_name, timestamp, value),
    )
    conn.commit()


def get_indicator_cache(
    conn: sqlite3.Connection,
    exchange: str,
    symbol: str,
    timeframe: str,
    indicator_name: str,
    since: Optional[int] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Get cached indicator values."""
    cursor = conn.cursor()
    
    query = """
        SELECT timestamp, value
        FROM indicator_cache
        WHERE exchange = ? AND symbol = ? AND timeframe = ? AND indicator_name = ?
    """
    params = [exchange, symbol, timeframe, indicator_name]
    
    if since is not None:
        query += " AND timestamp >= ?"
        params.append(since)
    
    query += " ORDER BY timestamp ASC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    
    return [{"timestamp": row[0], "value": row[1]} for row in cursor.fetchall()]
