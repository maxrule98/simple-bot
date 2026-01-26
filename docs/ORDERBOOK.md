# Order Book Streaming

## Overview

The WebSocket package now captures real-time order book depth, providing critical market microstructure data for advanced trading strategies.

## What is Order Book Data?

The order book shows all pending buy (bid) and sell (ask) orders at different price levels:

```
📚 Order Book Example (BTC/USDT)

Asks (Sellers):
  $104,850.50 × 0.5 BTC
  $104,850.00 × 1.2 BTC
  $104,849.50 × 2.1 BTC  ← Best Ask
  -------------------------  Spread = $1.00
  $104,848.50 × 1.8 BTC  ← Best Bid
  $104,848.00 × 0.9 BTC
  $104,847.50 × 1.5 BTC
Bids (Buyers):
```

## Why Order Book Matters

### 1. Liquidity Analysis

- **Deep order book** = Easy to buy/sell large amounts without moving price
- **Thin order book** = Large orders cause significant price impact

### 2. Market Sentiment

- **Bid-heavy** = More buyers → Bullish pressure
- **Ask-heavy** = More sellers → Bearish pressure

### 3. Price Discovery

- **Tight spread** = High liquidity, efficient market
- **Wide spread** = Low liquidity, volatile market

### 4. Entry/Exit Optimization

- Avoid entering when order book is thin (slippage risk)
- Target exits at price levels with strong support/resistance

## Database Schema

```sql
CREATE TABLE orderbook_data (
    exchange TEXT,
    symbol TEXT,
    timestamp INTEGER,

    -- Top 10 bids/asks stored as JSON
    bids TEXT,      -- [[price, amount], [price, amount], ...]
    asks TEXT,      -- [[price, amount], [price, amount], ...]

    -- Derived metrics
    bid_ask_spread REAL,
    mid_price REAL
);
```

**Example Row:**

```json
{
	"exchange": "mexc",
	"symbol": "BTC/USDT",
	"timestamp": 1737862800,
	"bids": [
		[104848.5, 1.8],
		[104848.0, 0.9],
		[104847.5, 1.5]
	],
	"asks": [
		[104849.5, 2.1],
		[104850.0, 1.2],
		[104850.5, 0.5]
	],
	"bid_ask_spread": 1.0,
	"mid_price": 104849.0
}
```

## Usage

### Basic WebSocket Streaming

```python
from packages.websocket.websocket import WebSocketManager
import sqlite3

# Connect to database
conn = sqlite3.connect('data/trading.db')

# Initialize WebSocket
ws = WebSocketManager(
    exchange_name='mexc',
    symbols=['BTC/USDT', 'ETH/USDT'],
    db_connection=conn,
    orderbook_depth=10  # Capture top 10 levels
)

# Start streaming (includes order book by default)
await ws.start(enable_orderbook=True)
```

### Query Order Book Data

```python
import json

# Get latest order book snapshot
cursor = conn.cursor()
cursor.execute("""
    SELECT bids, asks, bid_ask_spread, mid_price
    FROM orderbook_data
    WHERE exchange = 'mexc' AND symbol = 'BTC/USDT'
    ORDER BY timestamp DESC
    LIMIT 1
""")

bids_json, asks_json, spread, mid_price = cursor.fetchone()

# Parse JSON
bids = json.loads(bids_json)  # [[price, amount], ...]
asks = json.loads(asks_json)

# Best bid/ask
best_bid_price = bids[0][0]
best_ask_price = asks[0][0]

print(f"Spread: ${spread:.2f}")
print(f"Best Bid: ${best_bid_price:,.2f}")
print(f"Best Ask: ${best_ask_price:,.2f}")
```

## Strategy Applications

### 1. Liquidity-Based Entry/Exit

```python
def should_enter_position(orderbook):
    """Only enter if order book has sufficient liquidity."""
    bids = json.loads(orderbook['bids'])

    # Sum liquidity in top 5 bids
    total_bid_volume = sum(amount for price, amount in bids[:5])

    # Require at least 10 BTC of buy-side liquidity
    return total_bid_volume >= 10.0
```

### 2. Spread-Based Trading

```python
def is_favorable_spread(orderbook):
    """Check if spread is tight (liquid market)."""
    spread = orderbook['bid_ask_spread']
    mid_price = orderbook['mid_price']

    # Spread should be < 0.05% of mid price
    spread_pct = (spread / mid_price) * 100
    return spread_pct < 0.05
```

### 3. Order Book Imbalance

```python
def calculate_imbalance(orderbook):
    """
    Measure buy vs sell pressure.

    Returns:
        float: -1 to +1 (-1 = heavy sell, +1 = heavy buy)
    """
    bids = json.loads(orderbook['bids'])
    asks = json.loads(orderbook['asks'])

    bid_volume = sum(amount for price, amount in bids)
    ask_volume = sum(amount for price, amount in asks)

    total = bid_volume + ask_volume
    imbalance = (bid_volume - ask_volume) / total

    return imbalance  # +0.3 = 30% more buyers
```

### 4. Support/Resistance Detection

```python
def find_large_orders(orderbook, threshold_btc=5.0):
    """Identify price levels with large pending orders."""
    bids = json.loads(orderbook['bids'])
    asks = json.loads(orderbook['asks'])

    # Large buy orders = support levels
    support_levels = [price for price, amount in bids if amount >= threshold_btc]

    # Large sell orders = resistance levels
    resistance_levels = [price for price, amount in asks if amount >= threshold_btc]

    return support_levels, resistance_levels
```

## Real-Time Monitoring

Use the test script to see live order book updates:

```bash
uv run python scripts/test_websocket.py
```

This will stream for 30 seconds and show:

- Number of order book snapshots captured
- Latest order book with top 5 bids/asks
- Bid-ask spread
- Mid-market price

## Performance Considerations

### Update Frequency

- **High-frequency exchanges** (Binance): ~100ms updates
- **Medium-frequency exchanges** (Coinbase): ~500ms updates
- **Configurable depth**: 10 levels balances data size vs completeness

### Storage

- Each snapshot: ~500 bytes (10 levels × 2 sides)
- 1 update/second × 60 seconds × 60 minutes × 24 hours = 86,400 snapshots/day
- Daily storage per symbol: ~43 MB
- Weekly storage per symbol: ~300 MB

**Recommendation**: Prune old order book data after 7 days (keeps recent microstructure insights).

## Advanced Features (Future)

### 1. Order Book Reconstruction

Maintain full order book state in memory by applying deltas from WebSocket.

### 2. Bid-Ask Volume Weighted Average

Calculate VWAP using order book liquidity at each level.

### 3. Market Depth Visualization

Generate real-time depth charts showing bid/ask distribution.

### 4. Flash Crash Detection

Alert when order book suddenly empties (liquidity crisis).

## Integration with Strategy Engine

When building strategies, order book data is available alongside OHLCV:

```python
# Strategy checks both price action and order book
def should_exit(ohlcv, orderbook):
    # RSI says overbought
    rsi = calculate_rsi(ohlcv)

    # Order book shows heavy selling pressure
    imbalance = calculate_imbalance(orderbook)

    # Exit if both conditions met
    return rsi > 70 and imbalance < -0.2
```

## Testing

Run the test script to verify order book streaming:

```bash
# Stream BTC/USDT order book for 30 seconds
uv run python scripts/test_websocket.py

# Check database
sqlite3 data/trading.db "SELECT COUNT(*) FROM orderbook_data;"
```

---

**Key Takeaway**: Order book data provides real-time market microstructure insights that complement traditional OHLCV analysis, enabling more sophisticated entry/exit decisions based on actual liquidity and order flow.
