# Data Storage Strategy - Visual Guide

## The Problem

Multiple containers running simultaneously, each with different:

- Exchange (Binance, Coinbase, Kraken)
- Symbol (BTC/USDT, ETH/USDT, SOL/USDT)
- Timeframe (1m, 5m, 1h, 4h, 1d)
- Strategy (RSI, MACD, Scalping, Trend)

**Question**: How to store data efficiently without conflicts?

## The Solution

**One database, smart schema with partitioning**

```
┌───────────────────────────────────────────────────────────────┐
│                     trading.db (SQLite)                       │
│                         WAL Mode                              │
└───────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌────────────────┐    ┌──────────────┐
│  MARKET DATA  │    │   TRADE DATA   │    │ CACHED DATA  │
│   (Shared)    │    │  (Isolated)    │    │  (Shared)    │
└───────────────┘    └────────────────┘    └──────────────┘
```

## Data Tables Overview

### 📊 Market Data (Shared - All Strategies Read)

```
┌─────────────────────────────────────────────────────────────┐
│  ohlcv_data                                                 │
├──────────────┬──────────┬──────────────┬──────────────────┤
│ exchange     │ symbol   │ timeframe    │ timestamp OHLCV  │
├──────────────┼──────────┼──────────────┼──────────────────┤
│ binance      │ BTC/USDT │ 1h           │ 1706140800 ...   │
│ binance      │ BTC/USDT │ 15m          │ 1706140800 ...   │
│ binance      │ ETH/USDT │ 1h           │ 1706140800 ...   │
│ coinbase     │ BTC/USD  │ 1h           │ 1706140800 ...   │
│ kraken       │ SOL/USDT │ 4h           │ 1706140800 ...   │
└──────────────┴──────────┴──────────────┴──────────────────┘

UNIQUE(exchange, symbol, timeframe, timestamp) ← Prevents duplicates
```

**Why Shared?**

- BTC/USDT 1h candle at timestamp X is same regardless of strategy
- Backfiller populates once, all strategies use it
- No data duplication

### 💼 Trade Data (Isolated - Per Strategy)

```
┌────────────────────────────────────────────────────────────┐
│  trades                                                     │
├──────────────┬──────────┬───────────┬─────────────────────┤
│ strategy_id  │ symbol   │ side      │ price qty pnl       │
├──────────────┼──────────┼───────────┼─────────────────────┤
│ btc-bin-1h   │ BTC/USDT │ buy       │ 45000 0.1 +150      │
│ btc-bin-1h   │ BTC/USDT │ sell      │ 46500 0.1 +150      │
│ eth-bin-15m  │ ETH/USDT │ buy       │ 2800 1.0 +50        │
│ eth-bin-15m  │ ETH/USDT │ sell      │ 2850 1.0 +50        │
│ btc-cb-1h    │ BTC/USD  │ buy       │ 45100 0.05 +75      │
└──────────────┴──────────┴───────────┴─────────────────────┘

Each strategy_id = one container's trades
No conflicts between containers
```

**Why Isolated?**

- Each strategy tracks its own P&L independently
- No write conflicts (each container writes to its own strategy_id)
- Easy per-strategy analysis

## Data Flow Diagram

### 1. Backfiller Populates Market Data

```
┌──────────────┐
│  BACKFILLER  │ (runs once or scheduled)
└──────┬───────┘
       │
       │ 1. Fetches from exchanges
       │    (CCXT: Binance, Coinbase, Kraken)
       │
       ▼
┌─────────────────────────────────────────┐
│  INSERT OR IGNORE INTO ohlcv_data       │
│  (exchange, symbol, timeframe, ...)     │
└─────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────┐
│  ohlcv_data                                    │
│  ✓ binance, BTC/USDT, 1h → Last 1000 candles  │
│  ✓ binance, BTC/USDT, 15m → Last 1000 candles │
│  ✓ binance, ETH/USDT, 1h → Last 1000 candles  │
│  ✓ coinbase, BTC/USD, 1h → Last 1000 candles  │
└────────────────────────────────────────────────┘
       │
       │ Shared by all strategies
       │
       ▼
```

### 2. Traders Read Market Data, Write Trade Data

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  TRADER 1    │  │  TRADER 2    │  │  TRADER 3    │
│  btc-bin-1h  │  │  eth-bin-15m │  │  btc-cb-1h   │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       │ SELECT          │ SELECT          │ SELECT
       │ ohlcv_data      │ ohlcv_data      │ ohlcv_data
       │ WHERE           │ WHERE           │ WHERE
       │ exchange=       │ exchange=       │ exchange=
       │ 'binance'       │ 'binance'       │ 'coinbase'
       │ symbol=         │ symbol=         │ symbol=
       │ 'BTC/USDT'      │ 'ETH/USDT'      │ 'BTC/USD'
       │ timeframe='1h'  │ timeframe='15m' │ timeframe='1h'
       │                 │                 │
       ▼                 ▼                 ▼
   (same data)      (same data)      (same data)
       │                 │                 │
       │ Compute         │ Compute         │ Compute
       │ Indicators      │ Indicators      │ Indicators
       │                 │                 │
       │ Generate        │ Generate        │ Generate
       │ Signals         │ Signals         │ Signals
       │                 │                 │
       │ Execute         │ Execute         │ Execute
       │ Trades          │ Trades          │ Trades
       │                 │                 │
       ▼                 ▼                 ▼
   INSERT INTO       INSERT INTO       INSERT INTO
   trades            trades            trades
   (strategy_id=     (strategy_id=     (strategy_id=
    'btc-bin-1h')     'eth-bin-15m')    'btc-cb-1h')
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
                         ▼
                  ┌─────────────┐
                  │   trades    │
                  │             │
                  │ All isolated│
                  │ by          │
                  │ strategy_id │
                  └─────────────┘
```

### 3. Concurrent Read/Write Flow

```
Time: T0  ────────────────────────────────────────────

Container 1: READ ohlcv_data (binance, BTC/USDT, 1h)
Container 2: READ ohlcv_data (binance, ETH/USDT, 15m)
Container 3: READ ohlcv_data (coinbase, BTC/USD, 1h)

✅ All can read simultaneously (SQLite + WAL mode)

Time: T1  ────────────────────────────────────────────

Container 1: WRITE trades (strategy_id='btc-bin-1h')
Container 2: WRITE trades (strategy_id='eth-bin-15m')
Container 3: WRITE trades (strategy_id='btc-cb-1h')

✅ No conflicts - different strategy_id values
✅ WAL mode allows concurrent writes
```

## Composite Key Partitioning

Think of the data as logically partitioned:

```
ohlcv_data
│
├── Partition: (binance, BTC/USDT, 1h)
│   ├── 2026-01-01 00:00:00 → OHLCV
│   ├── 2026-01-01 01:00:00 → OHLCV
│   └── ...
│
├── Partition: (binance, BTC/USDT, 15m)
│   ├── 2026-01-01 00:00:00 → OHLCV
│   ├── 2026-01-01 00:15:00 → OHLCV
│   └── ...
│
├── Partition: (binance, ETH/USDT, 1h)
│   └── ...
│
└── Partition: (coinbase, BTC/USD, 1h)
    └── ...
```

**Benefits**:

- Queries always include (exchange, symbol, timeframe)
- Index makes these queries instant
- Data naturally organized
- Can archive old partitions easily

## Example Queries

### Query 1: Trader Needs Last 100 Candles

```sql
SELECT timestamp, open, high, low, close, volume
FROM ohlcv_data
WHERE exchange = 'binance'
  AND symbol = 'BTC/USDT'
  AND timeframe = '1h'
ORDER BY timestamp DESC
LIMIT 100;

-- ⚡ Fast: Uses idx_ohlcv_lookup index
-- ⚡ Returns only BTC/USDT 1h data
-- ⚡ No scanning of ETH or other symbols
```

### Query 2: Calculate Strategy Performance

```sql
SELECT
    COUNT(*) as total_trades,
    SUM(pnl) as total_pnl,
    AVG(pnl_percent) as avg_return,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses
FROM trades
WHERE strategy_id = 'btc-bin-1h';

-- ⚡ Fast: Uses idx_trades_strategy index
-- ⚡ Only reads one strategy's data
-- ⚡ No interference with other strategies
```

### Query 3: Backfiller Checks What Data Exists

```sql
SELECT MIN(timestamp) as earliest, MAX(timestamp) as latest
FROM ohlcv_data
WHERE exchange = 'binance'
  AND symbol = 'BTC/USDT'
  AND timeframe = '1h';

-- Knows what date range is already backfilled
-- Can fetch missing gaps
```

## Storage Efficiency

### Data Sharing Example

**Without Sharing (BAD):**

```
Container 1 DB: BTC/USDT 1h data (100 MB)
Container 2 DB: BTC/USDT 1h data (100 MB) ← DUPLICATE!
Container 3 DB: BTC/USDT 1h data (100 MB) ← DUPLICATE!

Total: 300 MB for same data
```

**With Sharing (GOOD):**

```
Shared DB:
├─ BTC/USDT 1h data (100 MB) ← ONCE
├─ ETH/USDT 15m data (50 MB)
└─ BTC/USD 1h data (100 MB)

Container 1: Reads BTC/USDT 1h
Container 2: Reads ETH/USDT 15m
Container 3: Reads BTC/USD 1h

Total: 250 MB (no duplication)
```

## Handling Concurrent Access

### WAL Mode (Write-Ahead Logging)

```python
conn.execute("PRAGMA journal_mode=WAL")
```

**How WAL Works:**

```
Without WAL:
  Writer locks entire DB → Readers blocked ❌

With WAL:
  Writer writes to WAL file → Readers read DB ✅
  Readers not blocked ✅
  Writers not blocked by readers ✅
```

**Perfect for multi-container deployment!**

## Summary Comparison

| Aspect                  | Single DB Per Container  | Shared DB Smart Schema          |
| ----------------------- | ------------------------ | ------------------------------- |
| Market data duplication | ❌ Yes - wasteful        | ✅ No - shared                  |
| Write conflicts         | ✅ None                  | ✅ None (strategy_id isolation) |
| Storage efficiency      | ❌ Poor                  | ✅ Excellent                    |
| Cross-strategy analysis | ❌ Hard                  | ✅ Easy                         |
| Backfiller complexity   | ❌ Must update all DBs   | ✅ Update once                  |
| Maintenance             | ❌ N databases to backup | ✅ One database                 |
| Scalability             | ❌ Grows linearly        | ✅ Sublinear growth             |

## Recommended Approach

✅ **One SQLite database (`trading.db`) with:**

- Market data tables (shared)
- Trade data tables (isolated by strategy_id)
- Proper indexing on composite keys
- WAL mode enabled
- Foreign keys enforced

**Result**: Clean, efficient, scalable multi-instance deployment! 🎯
