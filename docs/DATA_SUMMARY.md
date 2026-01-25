# Data Storage - Summary & Best Practices

## The Answer: One Shared Database, Smart Schema

### 🎯 Strategy

**Single SQLite database (`data/trading.db`) with two types of data:**

1. **Shared Market Data** - OHLCV candles, tickers
   - Same BTC/USDT 1h candle for all strategies
   - Populated once by backfiller
   - Read by all containers

2. **Isolated Trade Data** - Executed trades, positions, signals
   - Each strategy has unique `strategy_id`
   - No conflicts between containers
   - Easy per-strategy P&L tracking

### 📊 Schema Design

```
trading.db
│
├─ ohlcv_data           (Shared)
│  └─ UNIQUE(exchange, symbol, timeframe, timestamp)
│
├─ ticker_data          (Shared)
│  └─ UNIQUE(exchange, symbol, timestamp)
│
├─ strategy_metadata    (Registry)
│  └─ PRIMARY KEY(strategy_id)
│
├─ trades               (Isolated by strategy_id)
│  └─ FOREIGN KEY(strategy_id)
│
├─ positions            (Isolated by strategy_id)
│  └─ FOREIGN KEY(strategy_id)
│
└─ signals              (Isolated by strategy_id)
   └─ FOREIGN KEY(strategy_id)
```

### 🔑 Key Concepts

#### 1. Composite Key Partitioning

```sql
-- All market data queries use this pattern:
WHERE exchange = ? AND symbol = ? AND timeframe = ?

-- Creates natural partitions:
(binance, BTC/USDT, 1h)    → Partition 1
(binance, BTC/USDT, 15m)   → Partition 2
(binance, ETH/USDT, 1h)    → Partition 3
(coinbase, BTC/USD, 1h)    → Partition 4
```

**Benefit**: Each strategy only reads its partition. No scanning other data.

#### 2. Strategy ID Isolation

```sql
-- Each container has unique strategy_id:
strategy_id = 'trader-btc-binance-1h'
strategy_id = 'trader-eth-binance-15m'
strategy_id = 'trader-btc-coinbase-1h'

-- Trades are isolated:
INSERT INTO trades (strategy_id, ...) VALUES ('trader-btc-binance-1h', ...)
```

**Benefit**: No write conflicts. Each container writes to its own namespace.

#### 3. WAL Mode for Concurrency

```python
conn.execute("PRAGMA journal_mode=WAL")
```

**What it does**:

- Readers don't block writers
- Writers don't block readers
- Multiple containers can access database simultaneously

**Perfect for Docker multi-instance deployment!**

## 📈 Data Flow

### Backfiller → Market Data

```
Backfiller Container
    │
    ├─ Fetch from Binance API
    ├─ Fetch from Coinbase API
    ├─ Fetch from Kraken API
    │
    ▼
INSERT OR IGNORE INTO ohlcv_data
(exchange, symbol, timeframe, timestamp, open, high, low, close, volume)
    │
    ▼
Shared by all traders
```

### Traders → Read Market, Write Trades

```
Trader Container 1                Trader Container 2
    │                                 │
    ├─ SELECT ohlcv_data             ├─ SELECT ohlcv_data
    │  WHERE exchange='binance'      │  WHERE exchange='binance'
    │  AND symbol='BTC/USDT'         │  AND symbol='ETH/USDT'
    │  AND timeframe='1h'            │  AND timeframe='15m'
    │                                 │
    ├─ Calculate RSI                 ├─ Calculate RSI
    ├─ Generate Signal               ├─ Generate Signal
    ├─ Execute Trade                 ├─ Execute Trade
    │                                 │
    ▼                                 ▼
INSERT INTO trades                INSERT INTO trades
(strategy_id='btc-bin-1h', ...)  (strategy_id='eth-bin-15m', ...)
    │                                 │
    └─────────────┬───────────────────┘
                  │
                  ▼
         No Conflicts!
    (Different strategy_id values)
```

## 📏 Sizing Estimates

### Market Data

```
1 hour timeframe, 1 symbol:
- 8,760 rows/year (24 hours × 365 days)
- ~50 bytes/row
- ~438 KB/year

10 symbols, 3 timeframes each:
- ~131 MB/year

Very manageable for SQLite.
```

### Trade Data

```
100 trades/day per strategy:
- 36,500 rows/year
- ~100 bytes/row
- ~3.6 MB/year per strategy

10 strategies:
- ~36 MB/year

SQLite handles this easily.
```

**Conclusion**: Years of data fit comfortably in SQLite.

## 🔧 Best Practices

### 1. Always Use WAL Mode

```python
# In database initialization
conn = sqlite3.connect("data/trading.db")
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA foreign_keys=ON")
```

### 2. Use Proper Indexes

```python
# Already in schema.py
CREATE INDEX idx_ohlcv_lookup ON ohlcv_data(exchange, symbol, timeframe, timestamp);
CREATE INDEX idx_trades_strategy ON trades(strategy_id, timestamp DESC);
```

### 3. Handle Duplicates Gracefully

```python
# Market data - OK to ignore duplicates
cursor.execute("""
    INSERT OR IGNORE INTO ohlcv_data (...)
    VALUES (?, ?, ?, ...)
""", data)

# Trade data - Should not have duplicates
cursor.execute("""
    INSERT INTO trades (...)
    VALUES (?, ?, ?, ...)
""", data)
```

### 4. Use Transactions for Batch Inserts

```python
# Backfiller inserting 1000 candles
with conn:
    for candle in candles:
        conn.execute("INSERT OR IGNORE INTO ohlcv_data (...) VALUES (...)", candle)
# Auto-commit on exit
```

### 5. Register Strategy on Startup

```python
# Each container registers itself
conn.execute("""
    INSERT OR REPLACE INTO strategy_metadata
    (strategy_id, exchange, symbol, timeframe, strategy_name, config_file, status)
    VALUES (?, ?, ?, ?, ?, ?, 'active')
""", (strategy_id, exchange, symbol, timeframe, strategy_name, config_file))
```

### 6. Regular Backups

```bash
# Daily backup
sqlite3 data/trading.db ".backup data/backup/trading_$(date +%Y%m%d).db"

# Or use simple copy (stop containers first for consistency)
docker-compose down
cp data/trading.db data/backup/
docker-compose up -d
```

### 7. Archive Old Data

```python
# Keep last 3 months, archive the rest
conn.execute("""
    DELETE FROM ohlcv_data
    WHERE timestamp < strftime('%s', 'now', '-3 months')
""")

# Reclaim space
conn.execute("VACUUM")
```

## ✅ Checklist for Implementation

- [ ] Create `data/` directory
- [ ] Run `python schema.py` to initialize database
- [ ] Enable WAL mode in database connection code
- [ ] Each container generates unique `strategy_id`
- [ ] Register strategy in `strategy_metadata` on startup
- [ ] Backfiller uses `INSERT OR IGNORE` for market data
- [ ] Traders query market data by (exchange, symbol, timeframe)
- [ ] Traders write trades with their `strategy_id`
- [ ] Set up daily backup cron job
- [ ] Monitor database size and vacuum periodically

## 🚀 Why This Works

✅ **No Data Duplication** - Market data shared  
✅ **No Write Conflicts** - strategy_id isolation  
✅ **Efficient Storage** - Composite key partitioning  
✅ **Fast Queries** - Proper indexes  
✅ **Concurrent Access** - WAL mode  
✅ **Scalable** - Handles years of data  
✅ **Simple** - One database file  
✅ **Maintainable** - Clear schema, easy backups

## 📚 Learn More

- **[DATABASE.md](DATABASE.md)** - Full schema documentation
- **[DATA_STRATEGY.md](DATA_STRATEGY.md)** - Visual diagrams and examples
- **[schema.py](schema.py)** - Executable schema initialization

## 🎓 Key Takeaway

**Use composite keys `(exchange, symbol, timeframe)` for natural partitioning and `strategy_id` for write isolation. Enable WAL mode. One database handles everything efficiently.**

That's it! 🎯
