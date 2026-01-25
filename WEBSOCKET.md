# WebSocket Data Strategy

## Overview

For **live trading**, we use WebSockets for real-time market data instead of polling REST APIs. The beauty of our schema: **WebSocket data flows into the exact same database tables**.

## Key Insight

```
REST API Data        WebSocket Data
     ↓                     ↓
     └──────┬──────────────┘
            ↓
    Same Database Tables
    • ohlcv_data
    • ticker_data
```

**No separate tables needed!** WebSockets just push data faster than REST.

## Data Sources Comparison

### Backfiller / Backtester (Historical)

```
REST API (CCXT)
    ↓
Fetch 1000 candles at once
    ↓
INSERT INTO ohlcv_data
```

**Use case**: Bulk historical data download

### Live Trader (Real-time)

```
WebSocket (CCXT Pro)
    ↓
Receive updates as they happen
    ↓
INSERT OR REPLACE INTO ohlcv_data
```

**Use case**: Real-time trading decisions

## Database Schema (Already Supports Both!)

### OHLCV Data Table

```sql
CREATE TABLE ohlcv_data (
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,

    UNIQUE(exchange, symbol, timeframe, timestamp)
);
```

**Works for both**:

- REST API: Insert bulk historical candles
- WebSocket: Insert/update current forming candle

### Why `INSERT OR REPLACE`?

**WebSocket Problem**: The current 1-minute candle updates continuously:

```
00:00:10 → BTC price: $45,000 (candle forming)
00:00:30 → BTC price: $45,100 (same candle, updated high)
00:00:50 → BTC price: $45,050 (same candle, updated close)
00:01:00 → Candle complete, new candle starts
```

**Solution**: Use `INSERT OR REPLACE` to update the current candle:

```sql
INSERT OR REPLACE INTO ohlcv_data
(exchange, symbol, timeframe, timestamp, open, high, low, close, volume)
VALUES ('binance', 'BTC/USDT', '1m', 1706140800, 45000, 45100, 44950, 45050, 123.45)
```

Each update **replaces** the candle at that timestamp until it's complete.

## WebSocket Package Structure

```
packages/websocket/
├── __init__.py
└── websocket.py          # WebSocket manager using CCXT Pro
```

### WebSocket Manager Features

1. **Real-time OHLCV Updates**

   ```python
   ws.watch_ohlcv('BTC/USDT', '1m')  # Updates as candle forms
   ```

2. **Real-time Ticker Updates**

   ```python
   ws.watch_ticker('BTC/USDT')  # Bid/ask/last price updates
   ```

3. **Trade Stream** (Optional)

   ```python
   ws.watch_trades('BTC/USDT')  # Individual trades
   ```

4. **Order Book** (Optional)
   ```python
   ws.watch_order_book('BTC/USDT')  # Depth updates
   ```

## CCXT Pro Support

**CCXT Pro** (paid extension) provides WebSocket support:

```bash
# Install CCXT Pro
pip install ccxt[pro]

# Or with UV
uv add "ccxt[pro]"
```

**Supported Exchanges with WebSockets**:

- Binance ✅
- Coinbase Pro ✅
- Kraken ✅
- Bybit ✅
- OKX ✅
- And 50+ more

See: https://docs.ccxt.com/en/latest/ccxt.pro.manual.html

## Data Flow Diagram

### Backfiller (Historical Data)

```
┌─────────────┐
│ Backfiller  │ (Runs once or scheduled)
└──────┬──────┘
       │
       │ REST API
       │ ccxt.fetch_ohlcv()
       │
       ▼
┌─────────────────────────────────────┐
│ Binance REST API                    │
│ "Give me last 1000 BTC/USDT 1h"     │
└─────────────────────────────────────┘
       │
       │ Returns: Array of 1000 candles
       │
       ▼
┌─────────────────────────────────────┐
│ for candle in candles:              │
│   INSERT OR IGNORE INTO ohlcv_data  │
└─────────────────────────────────────┘
       │
       ▼
   database
```

### Live Trader (Real-time Data)

```
┌─────────────┐
│ Live Trader │ (Runs continuously)
└──────┬──────┘
       │
       │ WebSocket
       │ ccxtpro.watch_ohlcv()
       │
       ▼
┌─────────────────────────────────────┐
│ Binance WebSocket                   │
│ "Push me updates for BTC/USDT 1m"   │
└─────────────────────────────────────┘
       │
       │ Pushes: Updates every second
       │
       ▼
┌──────────────────────────────────────┐
│ on_update(candle):                   │
│   INSERT OR REPLACE INTO ohlcv_data  │
└──────────────────────────────────────┘
       │
       ▼
   database (same table!)
```

## Live Trading Flow with WebSockets

```
┌──────────────────────────────────────────────────────────┐
│ Live Trader Container (trader-btc-binance-1h)            │
└──────────────────────────────────────────────────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
    ▼                 ▼                 ▼
┌─────────┐   ┌──────────────┐   ┌──────────┐
│ REST    │   │ WebSocket    │   │ Strategy │
│ (Hist)  │   │ (Real-time)  │   │ Logic    │
└────┬────┘   └──────┬───────┘   └────┬─────┘
     │               │                 │
     ▼               ▼                 │
  On startup:   Continuously:          │
  Fetch last    Update current         │
  100 candles   candle as it forms     │
     │               │                 │
     └───────┬───────┘                 │
             │                         │
             ▼                         │
      ┌─────────────┐                 │
      │ ohlcv_data  │                 │
      │ (Database)  │                 │
      └──────┬──────┘                 │
             │                        │
             └────────────────────────┘
                      │
                      ▼
              ┌──────────────┐
              │ Calculate    │
              │ Indicators   │
              │ (RSI, MACD)  │
              └──────┬───────┘
                     │
                     ▼
              ┌──────────────┐
              │ Generate     │
              │ Signal       │
              └──────┬───────┘
                     │
                     ▼
              ┌──────────────┐
              │ Execute      │
              │ Trade        │
              └──────────────┘
```

## Example: Live Trading Setup

### 1. Initialize on Startup

```python
# apps/trader/main.py
import asyncio
from packages.websocket.websocket import WebSocketManager
from packages.database.db import Database

# Load strategy config
config = load_yaml('config/strategies/btc_binance_1h.yaml')
exchange = config['trading']['exchange']
symbol = config['trading']['symbol']
timeframe = config['trading']['timeframe']

# Connect to database
db = Database('data/trading.db')

# First: Fetch historical data via REST (last 100 candles)
from packages.exchange.exchange import Exchange
rest_exchange = Exchange(exchange)
historical = rest_exchange.fetch_ohlcv(symbol, timeframe, limit=100)
db.bulk_insert_ohlcv(historical)

# Then: Start WebSocket for real-time updates
ws = WebSocketManager(exchange, [symbol], db.connection)
asyncio.create_task(ws.start())
```

### 2. Strategy Reads Latest Data

```python
# Strategy doesn't care if data came from REST or WebSocket!
def calculate_signals():
    # Get last 100 candles (mix of historical + real-time)
    candles = db.get_ohlcv(
        exchange='binance',
        symbol='BTC/USDT',
        timeframe='1h',
        limit=100
    )

    # Calculate indicators
    rsi = calculate_rsi(candles)

    # Generate signal
    if rsi < 30:
        return 'buy'
```

The strategy **doesn't know** if the candles came from:

- REST API (backfiller)
- WebSocket (live stream)

**Same table, same query!**

## Benefits of This Approach

### ✅ Unified Data Layer

```
Historical Data (REST) ──┐
                         ├──→ Same Tables ──→ Same Queries
Real-time Data (WS) ─────┘
```

**No code changes needed!** Strategy reads from `ohlcv_data` regardless of source.

### ✅ Seamless Transition

```
1. Backfiller populates historical data (REST)
2. Backtester tests strategy (reads from DB)
3. Live trader starts:
   - Loads historical data (REST)
   - Switches to WebSocket (real-time)
   - Strategy sees no difference!
```

### ✅ Fallback Support

```python
# If WebSocket disconnects, fall back to REST polling
try:
    await ws.watch_ohlcv(symbol, timeframe)
except WebSocketError:
    # Fallback: Poll REST API every 60 seconds
    while True:
        candles = rest_api.fetch_ohlcv(symbol, timeframe, limit=1)
        db.insert_ohlcv(candles[-1])
        await asyncio.sleep(60)
```

## Files & Folders for WebSocket Support

### New Package

```
packages/websocket/
├── __init__.py              # Package init
└── websocket.py             # WebSocketManager class
```

### Updated Apps

```
apps/trader/main.py          # Uses WebSocketManager for live data
apps/backtester/main.py      # Uses REST data only (historical)
apps/backfiller/main.py      # Uses REST data only (bulk fetch)
```

### Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    "ccxt>=4.4.42",          # Already have
    "ccxt[pro]",             # Add this for WebSocket support
    # ... other deps
]
```

Or:

```bash
uv add "ccxt[pro]"
```

## Database Queries (Same for REST & WebSocket!)

### Get Latest Candles

```python
def get_latest_candles(exchange, symbol, timeframe, limit=100):
    """
    Gets most recent candles.
    Could be from REST API or WebSocket - doesn't matter!
    """
    return db.execute("""
        SELECT timestamp, open, high, low, close, volume
        FROM ohlcv_data
        WHERE exchange = ? AND symbol = ? AND timeframe = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (exchange, symbol, timeframe, limit))
```

### Check if Current Candle is Forming

```python
def get_current_candle(exchange, symbol, timeframe):
    """
    Get the most recent (possibly incomplete) candle.
    WebSocket updates this continuously.
    """
    current_time = int(time.time())

    # Round down to timeframe boundary
    if timeframe == '1m':
        candle_start = (current_time // 60) * 60
    elif timeframe == '1h':
        candle_start = (current_time // 3600) * 3600
    # ... etc

    return db.execute("""
        SELECT * FROM ohlcv_data
        WHERE exchange = ? AND symbol = ?
          AND timeframe = ? AND timestamp = ?
    """, (exchange, symbol, timeframe, candle_start))
```

## Summary

### ✅ Current Schema Already Supports WebSockets

- `ohlcv_data` table stores candles (REST or WebSocket)
- `ticker_data` table stores real-time prices (REST or WebSocket)
- `UNIQUE(exchange, symbol, timeframe, timestamp)` constraint works for both
- `INSERT OR REPLACE` updates current forming candles

### ✅ New Files Needed

```
packages/websocket/
├── __init__.py
└── websocket.py       # WebSocketManager using CCXT Pro
```

### ✅ Updated Dependencies

```bash
uv add "ccxt[pro]"     # Adds WebSocket support
```

### ✅ Usage in Apps

```python
# apps/trader/main.py
# 1. Fetch historical (REST)
rest_exchange.fetch_ohlcv(symbol, timeframe, limit=100)

# 2. Start WebSocket (real-time)
ws = WebSocketManager(exchange, [symbol], db)
await ws.start()

# 3. Strategy queries database (doesn't care about source!)
candles = db.get_ohlcv(exchange, symbol, timeframe)
```

**No changes to database schema needed. It already works!** 🎯
