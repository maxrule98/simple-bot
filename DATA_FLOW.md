# Data Flow: REST vs WebSocket

## Complete Data Architecture

### Data Sources Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    Data Acquisition Layer                     │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  REST API (CCXT)              WebSocket (CCXT Pro)           │
│  ├─ Historical data           ├─ Real-time OHLCV             │
│  ├─ Bulk fetch (1000s)        ├─ Live ticker updates         │
│  ├─ Used by backfiller        ├─ Trades stream               │
│  └─ Used by backtester        └─ Used by live trader         │
│                                                               │
└─────────────────┬──────────────────────┬────────────────────┘
                  │                      │
                  ▼                      ▼
         ┌────────────────────────────────────┐
         │     Same Database Tables           │
         │  • ohlcv_data                      │
         │  • ticker_data                     │
         └────────────────────────────────────┘
                        │
                        ▼
                Strategy Queries
            (Doesn't care about source!)
```

## App-Specific Data Usage

### 1. Backfiller (Historical Data Collection)

```
┌──────────────┐
│  Backfiller  │
└──────┬───────┘
       │
       │ Uses: REST API (CCXT)
       │
       ▼
┌────────────────────────────────────────┐
│ exchange.fetch_ohlcv(                  │
│   symbol='BTC/USDT',                   │
│   timeframe='1h',                      │
│   limit=1000                           │
│ )                                      │
└───────────┬────────────────────────────┘
            │
            │ Returns: Array of 1000 candles
            │
            ▼
┌────────────────────────────────────────┐
│ for candle in candles:                 │
│   INSERT OR IGNORE INTO ohlcv_data     │
│   (exchange, symbol, timeframe, ...)   │
└────────────────────────────────────────┘

✅ Runs: Once or scheduled (daily/weekly)
✅ Purpose: Populate historical data
✅ Data Source: REST API only
```

### 2. Backtester (Historical Simulation)

```
┌──────────────┐
│  Backtester  │
└──────┬───────┘
       │
       │ Uses: Database (historical data)
       │
       ▼
┌────────────────────────────────────────┐
│ SELECT * FROM ohlcv_data               │
│ WHERE exchange = 'binance'             │
│   AND symbol = 'BTC/USDT'              │
│   AND timeframe = '1h'                 │
│   AND timestamp BETWEEN ? AND ?        │
│ ORDER BY timestamp                     │
└───────────┬────────────────────────────┘
            │
            │ Returns: Historical candles
            │
            ▼
┌────────────────────────────────────────┐
│ for candle in candles:                 │
│   calculate_indicators(candle)         │
│   generate_signal()                    │
│   simulate_trade()                     │
└────────────────────────────────────────┘

✅ Runs: On-demand for testing
✅ Purpose: Test strategy against history
✅ Data Source: Database (REST data)
```

### 3. Live Trader (Real-time Trading)

```
┌──────────────────────────────────────────┐
│  Live Trader                             │
└──────────────────────────────────────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
    ▼               ▼               ▼
┌─────────┐  ┌────────────┐  ┌──────────┐
│ Startup │  │ Real-time  │  │ Strategy │
│ (REST)  │  │ (WebSocket)│  │ Logic    │
└────┬────┘  └─────┬──────┘  └────┬─────┘
     │             │              │
     │ 1. Warmup   │ 2. Live      │ 3. Trade
     │             │              │
     ▼             ▼              ▼

1. WARMUP (REST API):
┌────────────────────────────────────────┐
│ exchange.fetch_ohlcv(                  │
│   symbol='BTC/USDT',                   │
│   timeframe='1h',                      │
│   limit=100  # Last 100 candles        │
│ )                                      │
└───────────┬────────────────────────────┘
            │
            ▼
   INSERT INTO ohlcv_data
   (pre-populate recent history)

2. LIVE STREAM (WebSocket):
┌────────────────────────────────────────┐
│ ws = WebSocketManager(exchange, [...]) │
│ await ws.watch_ohlcv('BTC/USDT', '1h') │
└───────────┬────────────────────────────┘
            │
            │ Continuous updates
            │
            ▼
┌────────────────────────────────────────┐
│ on_candle_update(candle):              │
│   INSERT OR REPLACE INTO ohlcv_data    │
│   (updates current forming candle)     │
└────────────────────────────────────────┘

3. STRATEGY (Queries Database):
┌────────────────────────────────────────┐
│ SELECT * FROM ohlcv_data               │
│ WHERE exchange = 'binance'             │
│   AND symbol = 'BTC/USDT'              │
│   AND timeframe = '1h'                 │
│ ORDER BY timestamp DESC                │
│ LIMIT 100                              │
└───────────┬────────────────────────────┘
            │
            │ Gets: Mix of historical + live data
            │
            ▼
┌────────────────────────────────────────┐
│ calculate_rsi(candles)                 │
│ if rsi < 30:                           │
│   execute_trade('buy')                 │
└────────────────────────────────────────┘

✅ Runs: Continuously
✅ Purpose: Execute real trades
✅ Data Source: REST (warmup) + WebSocket (live)
```

## Database Operations Comparison

### REST API → Database

```python
# Backfiller or warmup
candles = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=1000)

for candle in candles:
    timestamp, open, high, low, close, volume = candle

    # INSERT OR IGNORE - skip if already exists
    db.execute("""
        INSERT OR IGNORE INTO ohlcv_data
        (exchange, symbol, timeframe, timestamp, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ('binance', 'BTC/USDT', '1h', timestamp//1000, open, high, low, close, volume))

db.commit()
```

**When**: Bulk historical data  
**Operation**: `INSERT OR IGNORE` (skip duplicates)  
**Speed**: Batch insert 1000s at once

### WebSocket → Database

```python
# Live trader
async def on_ohlcv_update(candle):
    timestamp, open, high, low, close, volume = candle

    # INSERT OR REPLACE - update if exists, insert if new
    db.execute("""
        INSERT OR REPLACE INTO ohlcv_data
        (exchange, symbol, timeframe, timestamp, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ('binance', 'BTC/USDT', '1h', timestamp//1000, open, high, low, close, volume))

    db.commit()  # Commit immediately for real-time
```

**When**: Real-time updates  
**Operation**: `INSERT OR REPLACE` (update current candle)  
**Speed**: Single insert per update (sub-second)

## Why `INSERT OR REPLACE` for WebSocket?

### The Current Candle Problem

```
Timeframe: 1h
Current time: 14:35:27

Candle timestamp: 14:00:00 (current forming candle)

14:00:10 → BTC: $45,000 | High: $45,000 | Low: $44,950
          INSERT OR REPLACE (first insert)

14:05:32 → BTC: $45,100 | High: $45,100 | Low: $44,950
          INSERT OR REPLACE (update high)

14:23:45 → BTC: $45,050 | High: $45,100 | Low: $44,900
          INSERT OR REPLACE (update low)

14:59:59 → BTC: $45,075 | High: $45,100 | Low: $44,900
          INSERT OR REPLACE (final close)

15:00:00 → New candle starts!
```

**Solution**: Use `INSERT OR REPLACE` to continuously update the current candle.

The `UNIQUE(exchange, symbol, timeframe, timestamp)` constraint ensures:

- Only ONE row exists for each timestamp
- Updates replace the existing row
- Once candle is complete, it's never updated again

## File Structure for WebSocket

```
packages/websocket/
├── __init__.py
└── websocket.py          # WebSocketManager class

apps/trader/main.py       # Uses WebSocketManager
apps/backtester/main.py   # Doesn't use WebSocket (historical only)
apps/backfiller/main.py   # Doesn't use WebSocket (REST only)
```

## Complete Live Trading Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Docker Container: trader-btc-binance-1h                     │
└─────────────────────────────────────────────────────────────┘
                            │
                    ┌───────┴───────┐
                    │   Startup     │
                    └───────┬───────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
   Load Config      Connect Database    Fetch Historical
   (YAML)           (SQLite)            (REST - last 100)
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                    ┌───────┴───────┐
                    │ Start WebSocket│
                    └───────┬───────┘
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
        ws.watch_ohlcv()        ws.watch_ticker()
        (1h candles)            (bid/ask/last)
                │                       │
                │    Continuous         │
                │    Updates            │
                │                       │
                └───────────┬───────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │ Strategy Loop     │
                  │ (every 1 second)  │
                  └─────────┬─────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
        Query Database          Calculate Indicators
        (last 100 candles)      (RSI, MACD, etc.)
                │                       │
                └───────────┬───────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ Generate Signal  │
                   │ (buy/sell/hold)  │
                   └────────┬─────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
         Signal: BUY              Signal: HOLD
                │                       │
                ▼                       │
        Execute Trade                   │
        (via exchange API)              │
                │                       │
                ▼                       │
        INSERT INTO trades              │
        (record trade)                  │
                │                       │
                └───────────┬───────────┘
                            │
                            ▼
                    (repeat forever)
```

## Summary

### ✅ Same Tables, Different Sources

| App         | Data Source      | Database Operation                       | Purpose               |
| ----------- | ---------------- | ---------------------------------------- | --------------------- |
| Backfiller  | REST API         | `INSERT OR IGNORE`                       | Bulk historical       |
| Backtester  | Database         | `SELECT`                                 | Historical simulation |
| Live Trader | REST + WebSocket | `INSERT OR IGNORE` + `INSERT OR REPLACE` | Real-time trading     |

### ✅ Files & Folders

- `packages/websocket/websocket.py` - WebSocket manager
- `apps/trader/main.py` - Uses WebSocket for live data
- `apps/backfiller/main.py` - Uses REST for historical
- `apps/backtester/main.py` - Reads from database

### ✅ Dependencies

```toml
dependencies = [
    "ccxt>=4.4.42",        # REST API
    "ccxt[pro]>=4.4.42",   # WebSocket support
]
```

### ✅ Key Insight

**The strategy doesn't know (or care) whether data came from REST or WebSocket!**

Both sources populate the same tables. Strategy just queries the database. Clean separation of concerns. 🎯
