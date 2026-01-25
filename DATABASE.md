# Database Architecture for Multi-Instance Trading Bot

## Overview

With multiple containers running different strategies on different exchanges/symbols/timeframes, we need a smart data storage strategy.

## Core Principle: Shared Market Data, Isolated Trade Data

```
┌─────────────────────────────────────────────────────────────┐
│                    trading.db (Shared)                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  📊 MARKET DATA (Shared - Read by all containers)           │
│  ├─ ohlcv_data          → Candlestick data                  │
│  ├─ ticker_data         → Real-time prices                  │
│  └─ order_book_data     → Depth data (optional)             │
│                                                              │
│  💼 TRADE DATA (Isolated - Per strategy instance)           │
│  ├─ trades              → Executed trades (strategy_id col) │
│  ├─ positions           → Open positions (strategy_id col)  │
│  ├─ signals             → Generated signals (strategy_id col)│
│  └─ strategy_metadata   → Strategy configs                  │
│                                                              │
│  📈 COMPUTED DATA (Cached - Can be shared)                  │
│  └─ indicator_cache     → Pre-computed indicators           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Why This Design?

### ✅ Shared Market Data

**Rationale**: BTC/USDT 1h candlestick from Binance is the same for all strategies.

**Benefits**:

- No data duplication
- Single backfiller populates data for all strategies
- Efficient storage
- Consistent data across strategies

### ✅ Isolated Trade Data

**Rationale**: Each strategy instance needs its own trade history.

**Benefits**:

- No conflicts between containers
- Easy per-strategy analysis
- Independent P&L tracking
- Clear attribution

### ✅ Partitioning by Composite Key

Use `(exchange, symbol, timeframe)` as natural partition key:

- Efficient querying
- Automatic data organization
- Easy to add new exchanges/symbols/timeframes

## Database Schema

### 1. Market Data Tables

#### `ohlcv_data` - Candlestick Data (Shared)

```sql
CREATE TABLE ohlcv_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange TEXT NOT NULL,           -- binance, coinbase, kraken
    symbol TEXT NOT NULL,             -- BTC/USDT, ETH/USDT
    timeframe TEXT NOT NULL,          -- 1m, 5m, 15m, 1h, 4h, 1d
    timestamp INTEGER NOT NULL,       -- Unix timestamp
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),

    -- Composite unique constraint
    UNIQUE(exchange, symbol, timeframe, timestamp)
);

-- Critical indexes for fast querying
CREATE INDEX idx_ohlcv_lookup ON ohlcv_data(exchange, symbol, timeframe, timestamp);
CREATE INDEX idx_ohlcv_time ON ohlcv_data(timestamp);
```

**Why This Works**:

- Composite unique constraint prevents duplicates
- All strategies querying "Binance BTC/USDT 1h" get same data
- Backfiller can safely insert without checking what strategies need data
- **Works for both REST API and WebSocket data** (same structure, different delivery)

**Data Sources**:

- **REST API** (backfiller): Bulk historical data via `ccxt.fetch_ohlcv()`
- **WebSocket** (live trader): Real-time updates via `ccxtpro.watch_ohlcv()`
- Both use `INSERT OR REPLACE` to handle updates to current forming candles

#### `ticker_data` - Real-time Price Data (Shared)

**Note**: This table is especially important for WebSocket live data, updated continuously.

```sql
CREATE TABLE ticker_data (
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

CREATE INDEX idx_ticker_lookup ON ticker_data(exchange, symbol, timestamp DESC);
```

### 2. Trade Data Tables (Per-Strategy Isolation)

#### `strategy_metadata` - Strategy Instance Registry

```sql
CREATE TABLE strategy_metadata (
    strategy_id TEXT PRIMARY KEY,     -- trader-btc-binance-1h
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    strategy_name TEXT NOT NULL,      -- RSI_Momentum, Scalping, etc.
    config_file TEXT NOT NULL,        -- btc_binance_1h.yaml
    container_name TEXT,              -- Docker container name
    status TEXT DEFAULT 'active',     -- active, paused, stopped
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX idx_strategy_status ON strategy_metadata(status);
```

#### `trades` - Executed Trades

```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id TEXT NOT NULL,        -- Foreign key to strategy_metadata
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,

    order_id TEXT NOT NULL,           -- Exchange order ID
    side TEXT NOT NULL,               -- buy, sell
    order_type TEXT NOT NULL,         -- limit, market
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    cost REAL NOT NULL,               -- quantity * price
    fee REAL DEFAULT 0,
    fee_currency TEXT,

    timestamp INTEGER NOT NULL,
    status TEXT DEFAULT 'filled',     -- filled, partial, cancelled

    -- P&L tracking
    pnl REAL DEFAULT 0,
    pnl_percent REAL DEFAULT 0,

    created_at INTEGER DEFAULT (strftime('%s', 'now')),

    FOREIGN KEY (strategy_id) REFERENCES strategy_metadata(strategy_id)
);

CREATE INDEX idx_trades_strategy ON trades(strategy_id, timestamp DESC);
CREATE INDEX idx_trades_lookup ON trades(exchange, symbol, timestamp DESC);
CREATE INDEX idx_trades_status ON trades(status);
```

#### `positions` - Open Positions

```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id TEXT NOT NULL,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,

    side TEXT NOT NULL,               -- long, short
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

    status TEXT DEFAULT 'open',       -- open, closed

    FOREIGN KEY (strategy_id) REFERENCES strategy_metadata(strategy_id)
);

CREATE INDEX idx_positions_strategy ON positions(strategy_id, status);
CREATE INDEX idx_positions_open ON positions(status, updated_at DESC);
```

#### `signals` - Generated Trading Signals

```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id TEXT NOT NULL,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,

    signal_type TEXT NOT NULL,        -- buy, sell, hold
    confidence REAL,                  -- 0.0 to 1.0
    indicators TEXT,                  -- JSON: {"rsi": 28, "macd": 0.5}

    executed BOOLEAN DEFAULT 0,       -- Was this signal acted upon?
    trade_id INTEGER,                 -- If executed, link to trade

    timestamp INTEGER NOT NULL,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),

    FOREIGN KEY (strategy_id) REFERENCES strategy_metadata(strategy_id),
    FOREIGN KEY (trade_id) REFERENCES trades(id)
);

CREATE INDEX idx_signals_strategy ON signals(strategy_id, timestamp DESC);
CREATE INDEX idx_signals_executed ON signals(executed, timestamp DESC);
```

### 3. Computed Data Tables (Cached)

#### `indicator_cache` - Pre-computed Indicators

```sql
CREATE TABLE indicator_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    indicator_name TEXT NOT NULL,     -- rsi, macd, ema_50

    timestamp INTEGER NOT NULL,
    value REAL NOT NULL,              -- Indicator value
    metadata TEXT,                    -- JSON: additional data

    computed_at INTEGER DEFAULT (strftime('%s', 'now')),

    UNIQUE(exchange, symbol, timeframe, indicator_name, timestamp)
);

CREATE INDEX idx_indicator_lookup ON indicator_cache(
    exchange, symbol, timeframe, indicator_name, timestamp DESC
);
```

**Rationale**: RSI for BTC/USDT 1h at timestamp X is same regardless of strategy.

- Compute once, cache for all strategies
- Saves CPU and time
- Optional optimization

## Query Patterns

### 1. Get Latest OHLCV Data for a Strategy

```python
def get_latest_candles(exchange, symbol, timeframe, limit=100):
    """Get most recent N candles for strategy."""
    return db.execute("""
        SELECT timestamp, open, high, low, close, volume
        FROM ohlcv_data
        WHERE exchange = ? AND symbol = ? AND timeframe = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (exchange, symbol, timeframe, limit))
```

### 2. Get All Trades for a Strategy

```python
def get_strategy_trades(strategy_id):
    """Get all trades for specific strategy instance."""
    return db.execute("""
        SELECT * FROM trades
        WHERE strategy_id = ?
        ORDER BY timestamp DESC
    """, (strategy_id,))
```

### 3. Calculate Strategy Performance

```python
def get_strategy_performance(strategy_id):
    """Calculate P&L for strategy."""
    return db.execute("""
        SELECT
            COUNT(*) as total_trades,
            SUM(pnl) as total_pnl,
            AVG(pnl_percent) as avg_pnl_percent,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
            SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades
        FROM trades
        WHERE strategy_id = ?
    """, (strategy_id,))
```

### 4. Check if Data Exists Before Backfilling

```python
def get_data_range(exchange, symbol, timeframe):
    """Get earliest and latest timestamps for data."""
    return db.execute("""
        SELECT MIN(timestamp) as earliest, MAX(timestamp) as latest
        FROM ohlcv_data
        WHERE exchange = ? AND symbol = ? AND timeframe = ?
    """, (exchange, symbol, timeframe))
```

## Handling Concurrent Writes

### Problem: Multiple Containers Writing to SQLite

**SQLite Limitations**:

- Single writer at a time
- Concurrent reads are fine
- Writes lock the database briefly

**Solution: Smart Write Patterns**

#### 1. Market Data (Backfiller)

```python
# Use INSERT OR IGNORE to handle duplicates gracefully
cursor.execute("""
    INSERT OR IGNORE INTO ohlcv_data
    (exchange, symbol, timeframe, timestamp, open, high, low, close, volume)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""", data)
```

#### 2. Trade Data (Traders)

```python
# Each trader only writes its own strategy_id
# No conflicts since strategy_id is unique per container
cursor.execute("""
    INSERT INTO trades
    (strategy_id, exchange, symbol, timestamp, side, quantity, price)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", (strategy_id, ...))
```

#### 3. Use WAL Mode

```python
# In database initialization
conn.execute("PRAGMA journal_mode=WAL")
```

**WAL (Write-Ahead Logging) Benefits**:

- Better concurrent access
- Readers don't block writers
- Writers don't block readers
- Much better for multi-process access

## Data Partitioning Strategy

### Natural Partitioning by (exchange, symbol, timeframe)

```
ohlcv_data table conceptually partitioned:

Partition 1: (binance, BTC/USDT, 1h)
Partition 2: (binance, BTC/USDT, 15m)
Partition 3: (binance, ETH/USDT, 1h)
Partition 4: (coinbase, BTC/USD, 1h)
Partition 5: (kraken, SOL/USDT, 4h)
... etc
```

**Benefits**:

- Queries always filter by these columns (indexed)
- Data naturally organized
- Easy to backup/archive specific partitions
- Can split into separate tables if needed later

## Storage Estimates

### Market Data Growth

**OHLCV Data**:

```
1 minute data:
- 1 symbol, 1 exchange: ~525,600 rows/year (1 row/min)
- 10 symbols: ~5.2M rows/year
- Each row: ~50 bytes
- 10 symbols: ~260 MB/year

1 hour data:
- 1 symbol: ~8,760 rows/year (1 row/hour)
- 10 symbols: ~87,600 rows/year
- 10 symbols: ~4.4 MB/year
```

**Trade Data**:

```
Assuming 100 trades/day per strategy:
- 1 strategy: ~36,500 rows/year
- 10 strategies: ~365,000 rows/year
- Each row: ~100 bytes
- 10 strategies: ~36 MB/year
```

**Conclusion**: SQLite easily handles this. Can store years of data.

## Maintenance

### Archival Strategy

```sql
-- Archive old data (keep last 3 months)
DELETE FROM ohlcv_data
WHERE timestamp < strftime('%s', 'now', '-3 months');

-- Or move to archive table
INSERT INTO ohlcv_data_archive
SELECT * FROM ohlcv_data
WHERE timestamp < strftime('%s', 'now', '-3 months');
```

### Vacuum Regularly

```sql
-- Reclaim space after deletions
VACUUM;
```

### Backup Strategy

```bash
# Backup database daily
sqlite3 data/trading.db ".backup data/backup/trading_$(date +%Y%m%d).db"

# Or use simple copy (stop containers first)
docker-compose down
cp data/trading.db data/backup/
docker-compose up -d
```

## Summary

✅ **Shared market data** - BTC/USDT 1h is same for all strategies  
✅ **Isolated trade data** - Each strategy_id tracks its own trades  
✅ **Efficient partitioning** - (exchange, symbol, timeframe) composite key  
✅ **Proper indexing** - Fast queries for all patterns  
✅ **Concurrent access** - WAL mode handles multiple containers  
✅ **Scalable** - SQLite handles years of data easily  
✅ **Simple maintenance** - Archive old data, regular backups

**No need for complex sharding or separate databases. One smart schema does it all.** 🎯
