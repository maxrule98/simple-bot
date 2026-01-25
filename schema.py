"""
Database schema initialization for trading bot.

Creates all tables with proper indexes for multi-instance deployment.
Run this once to initialize the database, or import in packages/database/db.py
"""

# Enable WAL mode for better concurrent access
PRAGMA_WAL = "PRAGMA journal_mode=WAL;"
PRAGMA_FOREIGN_KEYS = "PRAGMA foreign_keys=ON;"

# =============================================================================
# MARKET DATA TABLES (Shared across all strategy instances)
# =============================================================================

CREATE_OHLCV_TABLE = """
CREATE TABLE IF NOT EXISTS ohlcv_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    
    UNIQUE(exchange, symbol, timeframe, timestamp)
);
"""

CREATE_OHLCV_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_ohlcv_lookup ON ohlcv_data(exchange, symbol, timeframe, timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_ohlcv_time ON ohlcv_data(timestamp);",
]

CREATE_TICKER_TABLE = """
CREATE TABLE IF NOT EXISTS ticker_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    bid REAL NOT NULL,
    ask REAL NOT NULL,
    last REAL NOT NULL,
    volume_24h REAL,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    
    UNIQUE(exchange, symbol, timestamp)
);
"""

CREATE_TICKER_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_ticker_lookup ON ticker_data(exchange, symbol, timestamp DESC);",
]

# =============================================================================
# STRATEGY & TRADE TABLES (Isolated per strategy instance)
# =============================================================================

CREATE_STRATEGY_METADATA_TABLE = """
CREATE TABLE IF NOT EXISTS strategy_metadata (
    strategy_id TEXT PRIMARY KEY,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    strategy_name TEXT NOT NULL,
    config_file TEXT NOT NULL,
    container_name TEXT,
    status TEXT DEFAULT 'active',
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);
"""

CREATE_STRATEGY_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_strategy_status ON strategy_metadata(status);",
]

CREATE_TRADES_TABLE = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id TEXT NOT NULL,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    
    order_id TEXT NOT NULL,
    side TEXT NOT NULL,
    order_type TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    cost REAL NOT NULL,
    fee REAL DEFAULT 0,
    fee_currency TEXT,
    
    timestamp INTEGER NOT NULL,
    status TEXT DEFAULT 'filled',
    
    pnl REAL DEFAULT 0,
    pnl_percent REAL DEFAULT 0,
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    
    FOREIGN KEY (strategy_id) REFERENCES strategy_metadata(strategy_id)
);
"""

CREATE_TRADES_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy_id, timestamp DESC);",
    "CREATE INDEX IF NOT EXISTS idx_trades_lookup ON trades(exchange, symbol, timestamp DESC);",
    "CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);",
]

CREATE_POSITIONS_TABLE = """
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id TEXT NOT NULL,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    
    side TEXT NOT NULL,
    entry_price REAL NOT NULL,
    quantity REAL NOT NULL,
    current_price REAL,
    
    stop_loss REAL,
    take_profit REAL,
    trailing_stop REAL,
    
    unrealized_pnl REAL DEFAULT 0,
    unrealized_pnl_percent REAL DEFAULT 0,
    
    opened_at INTEGER NOT NULL,
    updated_at INTEGER DEFAULT (strftime('%s', 'now')),
    
    status TEXT DEFAULT 'open',
    
    FOREIGN KEY (strategy_id) REFERENCES strategy_metadata(strategy_id)
);
"""

CREATE_POSITIONS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_positions_strategy ON positions(strategy_id, status);",
    "CREATE INDEX IF NOT EXISTS idx_positions_open ON positions(status, updated_at DESC);",
]

CREATE_SIGNALS_TABLE = """
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id TEXT NOT NULL,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    
    signal_type TEXT NOT NULL,
    confidence REAL,
    indicators TEXT,
    
    executed BOOLEAN DEFAULT 0,
    trade_id INTEGER,
    
    timestamp INTEGER NOT NULL,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    
    FOREIGN KEY (strategy_id) REFERENCES strategy_metadata(strategy_id),
    FOREIGN KEY (trade_id) REFERENCES trades(id)
);
"""

CREATE_SIGNALS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_signals_strategy ON signals(strategy_id, timestamp DESC);",
    "CREATE INDEX IF NOT EXISTS idx_signals_executed ON signals(executed, timestamp DESC);",
]

# =============================================================================
# COMPUTED DATA TABLES (Optional - for performance optimization)
# =============================================================================

CREATE_INDICATOR_CACHE_TABLE = """
CREATE TABLE IF NOT EXISTS indicator_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    indicator_name TEXT NOT NULL,
    
    timestamp INTEGER NOT NULL,
    value REAL NOT NULL,
    metadata TEXT,
    
    computed_at INTEGER DEFAULT (strftime('%s', 'now')),
    
    UNIQUE(exchange, symbol, timeframe, indicator_name, timestamp)
);
"""

CREATE_INDICATOR_CACHE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_indicator_lookup ON indicator_cache(exchange, symbol, timeframe, indicator_name, timestamp DESC);",
]

# =============================================================================
# ALL TABLES AND INDEXES (Execution Order)
# =============================================================================

ALL_TABLES = [
    # Market data
    CREATE_OHLCV_TABLE,
    CREATE_TICKER_TABLE,
    
    # Strategy & trades
    CREATE_STRATEGY_METADATA_TABLE,
    CREATE_TRADES_TABLE,
    CREATE_POSITIONS_TABLE,
    CREATE_SIGNALS_TABLE,
    
    # Computed data
    CREATE_INDICATOR_CACHE_TABLE,
]

ALL_INDEXES = (
    OHLCV_INDEXES +
    CREATE_TICKER_INDEXES +
    CREATE_STRATEGY_INDEXES +
    CREATE_TRADES_INDEXES +
    CREATE_POSITIONS_INDEXES +
    CREATE_SIGNALS_INDEXES +
    CREATE_INDICATOR_CACHE_INDEXES
)

# =============================================================================
# INITIALIZATION FUNCTION
# =============================================================================

def initialize_database(conn):
    """
    Initialize database with all tables and indexes.
    
    Args:
        conn: sqlite3 connection object
        
    Returns:
        bool: True if successful
    """
    try:
        cursor = conn.cursor()
        
        # Enable WAL mode for better concurrent access
        cursor.execute(PRAGMA_WAL)
        cursor.execute(PRAGMA_FOREIGN_KEYS)
        
        # Create all tables
        for table_sql in ALL_TABLES:
            cursor.execute(table_sql)
        
        # Create all indexes
        for index_sql in ALL_INDEXES:
            cursor.execute(index_sql)
        
        conn.commit()
        print("✅ Database initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        conn.rollback()
        return False


if __name__ == "__main__":
    """Run this script directly to initialize the database."""
    import sqlite3
    from pathlib import Path
    
    # Create data directory if it doesn't exist
    Path("data").mkdir(exist_ok=True)
    
    # Connect and initialize
    conn = sqlite3.connect("data/trading.db")
    initialize_database(conn)
    conn.close()
    
    print("\n📊 Database schema:")
    print("  - ohlcv_data (market data)")
    print("  - ticker_data (real-time prices)")
    print("  - strategy_metadata (strategy registry)")
    print("  - trades (executed trades)")
    print("  - positions (open positions)")
    print("  - signals (trading signals)")
    print("  - indicator_cache (computed indicators)")
    print("\n🚀 Ready to use!")
