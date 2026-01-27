# Grafana + Prometheus Real-Time Visualization

## Architecture Overview

```
                ┌─────────────┐
                │  WebSocket  │
                └──────┬──────┘
                       │
            ┌──────────┴──────────┐
            │                     │
            ▼                     ▼
    ┌──────────────┐      ┌─────────────┐
    │  Prometheus  │      │   SQLite/   │
    │  Pushgateway │      │  PostgreSQL │
    └──────┬───────┘      └─────────────┘
           │                      │
           │ query (100ms-1s)     │ query (historical)
           │                      │
           ▼                      ▼
    ┌──────────────────────────────────┐
    │          Grafana                 │
    │  - Live panels (Prometheus)      │
    │  - Analysis panels (Database)    │
    └──────────────────────────────────┘
```

## Why This Architecture?

**Problem**: Grafana polling SQLite has minimum practical refresh of 1-5 seconds, too slow for 1m timeframe tick-by-tick monitoring.

**Solution**: Dual data path

- **Prometheus** (in-memory): Sub-second updates for live monitoring
- **Database** (persistent): Historical analysis and indicators

### Advantages

✅ **Sub-second updates** - 100ms-1s refresh feels real-time  
✅ **No database hammering** - Prometheus queries are in-memory  
✅ **Instant push** - WebSocket → Prometheus ~1ms latency  
✅ **Historical persistence** - Database keeps everything for backtesting  
✅ **Scalable** - Prometheus handles high-frequency updates easily

### Trade-offs

⚠️ **Prometheus retention** - Default 15 days, then data deleted (DB has permanent history)  
⚠️ **Cardinality limits** - Don't create labels for every price level  
⚠️ **Dual maintenance** - Two systems to monitor

## Data Flow

### Live Data Path (Milliseconds → Seconds)

```
WebSocket tick → Update Prometheus metrics → Push to Pushgateway
                                           → Grafana queries (100ms-1s refresh)
```

### Historical Data Path (Persistent)

```
WebSocket tick → Store in SQLite/PostgreSQL → Grafana queries (5-10s refresh)
                                           → Backtest analysis
                                           → Indicator calculations
```

## Prometheus Metrics Structure

### Core Metrics

```python
from prometheus_client import Gauge, Counter, Histogram

# Price tracking
price_gauge = Gauge(
    'crypto_price',
    'Current price',
    ['exchange', 'symbol', 'type']  # type: last, bid, ask
)

# Trade counting
trade_counter = Counter(
    'crypto_trades_total',
    'Total trades',
    ['exchange', 'symbol', 'side']  # side: buy, sell
)

# Volume tracking
trade_volume = Gauge(
    'crypto_trade_volume',
    'Recent trade volume',
    ['exchange', 'symbol']
)
# Current forming candle (updated on every tick)
candle_open = Gauge('crypto_candle_open', 'Current candle open', ['exchange', 'symbol', 'timeframe'])
candle_high = Gauge('crypto_candle_high', 'Current candle high', ['exchange', 'symbol', 'timeframe'])
candle_low = Gauge('crypto_candle_low', 'Current candle low', ['exchange', 'symbol', 'timeframe'])
candle_close = Gauge('crypto_candle_close', 'Current candle close (last price)', ['exchange', 'symbol', 'timeframe'])
candle_volume = Gauge('crypto_candle_volume', 'Current candle volume', ['exchange', 'symbol', 'timeframe'])
# Order book metrics
orderbook_spread = Gauge(
    'crypto_spread',
    'Bid-ask spread',
    ['exchange', 'symbol']
)


```

### Example Push Implementation

```python
# packages/websocket/websocket.py

from prometheus_client import push_to_gateway
import time

async def watch_order_book(self, symbol: str):
    """Watch order book and push depth chart data to Prometheus."""
    while self.running:
        orderbook = await self.exchange.watch_order_book(symbol)

        bids = orderbook.get('bids', [])[:20]  # Top 20 levels
        asks = orderbook.get('asks', [])[:20]

        # Calculate cumulative depth for visualization
        bid_cumulative = 0
        for i, (price, amount) in enumerate(bids):
            quantity = amount
            bid_cumulative += quantity

            # Push individual level metrics
            orderbook_bid_price.labels(
                exchange=self.exchange_name,
                symbol=symbol,
                level=str(i)
            ).set(price)

            orderbook_bid_quantity.labels(
                exchange=self.exchange_name,
                symbol=symbol,
                level=str(i)
            ).set(quantity)

            # Cumulative for depth chart
            orderbook_bid_cumulative.labels(
                exchange=self.exchange_name,
                symbol=symbol,
                level=str(i)
            ).set(bid_cumulative)

        # Same for asks
        ask_cumulative = 0
        for i, (price, amount) in enumerate(asks):
            quantity = amount
            ask_cumulative += quantity

            orderbook_ask_price.labels(
                exchange=self.exchange_name,
                symbol=symbol,
                level=str(i)
            ).set(price)

            orderbook_ask_quantity.labels(
                exchange=self.exchange_name,
                symbol=symbol,
                level=str(i)
            ).set(quantity)

            orderbook_ask_cumulative.labels(
                exchange=self.exchange_name,
                symbol=symbol,
                level=str(i)
            ).set(ask_cumulative)

        # Push aggregates
        orderbook_spread.labels(
            exchange=self.exchange_name,
            symbol=symbol
        ).set(asks[0][0] - bids[0][0])

        orderbook_total_bids.labels(
            exchange=self.exchange_name,
            symbol=symbol
        ).set(bid_cumulative * bids[0][0])  # Approximate USD value

        orderbook_total_asks.labels(
            exchange=self.exchange_name,
            symbol=symbol
        ).set(ask_cumulative * asks[0][0])

        # Batch push to gateway
        push_to_gateway(
            'pushgateway:9091',
            job=f'websocket_{self.exchange_name}',
            registry=registry
        )

            # 1. Update Prometheus metrics (instant, in-memory)
            price_gauge.labels(
                exchange=self.exchange_name,
                symbol=symbol,
                type='last'
            ).set(trade['price'])

            trade_counter.labels(
                exchange=self.exchange_name,
                symbol=symbol,
                side=trade['side']
            ).inc()

            trade_volume.labels(
                exchange=self.exchange_name,
                symbol=symbol
            ).set(trade['amount'])

            batch_trades.append(trade)

            # 2. Push to gateway every 100ms or 10 trades
            now = time.time()
            if len(batch_trades) >= 10 or (now - last_push) > 0.1:
                try:
                    push_to_gateway(
                        'pushgateway:9091',
                        job=f'websocket_{self.exchange_name}',
                        registry=registry
                    )
                    last_push = now
                    batch_trades = []
                except Exception as e:
                    self.logger.warning(f"Failed to push to Prometheus: {e}")

            # 3. Persist to database (async, doesn't block)
            asyncio.create_task(self._store_trade(trade))
```

## Grafana Dashboard Design

### Panel Layout

```
┌─────────────────────────────────────────────────────────┐
│ ROW 1: LIVE METRICS (Prometheus - 500ms refresh)       │
├─────────────────────────────────────────────────────────┤
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│ │ Last Price   │  │ Bid/Ask      │  │ Trade Count  │  │
│ │ $87,850.23   │  │ Spread: $0.01│  │ 1,247 (1m)   │  │
│ └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ ROW 2: LIVE TRADE FLOW (Prometheus - 500ms)            │
├─────────────────────────────────────────────────────────┤
│ ┌───────────────────────────────────────────────────┐   │
│ │ Buy/Sell Pressure (trades per second)            │   │
│ │ [=========BUY=========]  [===SELL===]            │   │
│ └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ ROW 3: UNIFIED CANDLESTICK CHART                        │
│        (DB historical + Prometheus live forming candle) │
├─────────────────────────────────────────────────────────┤
│ ┌───────────────────────────────────────────────────┐   │
│ │ Candlestick Chart (1m)                            │   │
│ │ [Past candles from DB] + [Live forming candle]   │   │
│ │ ▂▅▇█▅▃▁████ (seamless transition)                │   │
│ └───────────────────────────────────────────────────┘   │
│ ┌───────────────────────────────────────────────────┐   │
│ │ Volume Bars (from OHLCV data)                     │   │
│ └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ ROW 4: ORDER BOOK DEPTH (Prometheus - 500ms)           │
├─────────────────────────────────────────────────────────┤
│ ┌───────────────────────────────────────────────────┐   │
│ │ Order Book Depth Chart (Area Chart)              │   │
│ │                                                   │   │
│ │ BIDS (GREEN)          SPREAD          ASKS (RED) │   │
│ │    ████▓▓▓▒▒░░    |   $0.01   |   ░░▒▒▓▓▓████    │   │
│ │  2,590 BTC                           1,595 BTC   │   │
│ │  $614-$613                           $614-$616   │   │
│ │                                                   │   │
│ │ Visualization: Cumulative depth area chart       │   │
│ │ - X-axis: Price levels                           │   │
│ │ - Y-axis: Cumulative quantity                    │   │
│ │ - Green area (left): Bids building up            │   │
│ │ - Red area (right): Asks building up             │   │
│ └───────────────────────────────────────────────────┘   │
│                                                         │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│ │ Total Bids   │  │ Spread       │  │ Total Asks   │  │
│ │ $1.59M       │  │ $0.01 (0.1%) │  │ $0.98M       │  │
│ └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Order Book Depth Chart Implementation

The depth chart visualization (inspired by traditional trading platforms) requires:

**Grafana Panel Setup:**

1. **Panel Type**: Graph (Time series) or XY Chart plugin
2. **Queries**: Two series - bids (green) and asks (red)
3. **Display Mode**: Area fill with stacking
4. **X-Axis**: Price levels (sorted)
5. **Y-Axis**: Cumuchart - BIDS (green area)

# For each level (0-19), plot price vs cumulative quantity

crypto_orderbook_bid_cumulative{exchange="mexc", symbol="BTC/USDT"}

# Join with: crypto_orderbook_bid_price (for x-axis)

# Order book depth chart - ASKS (red area)

crypto_orderbook_ask_cumulative{exchange="mexc", symbol="BTC/USDT"}

# Join with: crypto_orderbook_ask_price (for x-axis)

# Order book spread

crypto_spread{exchange="mexc", symbol="BTC/USDT"}

# Total bid liquidity

crypto_total_bids{exchange="mexc", symbol="BTC/USDT"}

# Total ask liquidity

crypto_total_asks{exchange="mexc", symbol="BTC/USDT

# Bids (green area, left side)

# Query all bid levels and their cumulative quantities

sort_desc(
crypto_orderbook_bid_cumulative{exchange="mexc", symbol="BTC/USDT"}
)

# Asks (red area, right side)

# Query all ask levels and their cumulative quantities

sort_asc(
crypto_orderbook_ask_cumulative{exchange="mexc", symbol="BTC/USDT"}
)

````

**Grafana Transformation:**
1. Use "Organize fields" to rename series
2. Use "Join by field" to combine bid/ask data
3. X-axis: Use price from `crypto_orderbook_bid_price` / `crypto_orderbook_ask_price`
4. Y-axis: Use cumulative quantity

**Visual Styling:**
```json
{
  "fieldConfig": {
    "overrides": [
      {
        "matcher": { "id": "byName", "options": "bids" },
        "properties": [
          { "id": "color", "value": { "mode": "fixed", "fixedColor": "green" } },
          { "id": "custom.fillOpacity", "value": 50 },
          { "id": "custom.lineWidth", "value": 2 }
        ]
      },
      {
        "matcher": { "id": "byName", "options": "asks" },
        "properties": [
          { "id": "color", "value": { "mode": "fixed", "fixedColor": "red" } },
          { "id": "custom.fillOpacity", "value": 50 },
          { "id": "custom.lineWidth", "value": 2 }
        ]
      }
    ]
  }
}
````

**Key Design Note**: The candlestick chart combines two data sources:

- **Historical candles** (completed): Queried from database
- **Current forming candle**: Live OHLCV from Prometheus
- Grafana displays them seamlessly as one continuous chart

### PromQL Queries (Live Panels)

```promql
# Current last price
crypto_price{exchange="mexc", symbol="BTC/USDT", type="last"}

# Bid-ask spread
crypto_spread{exchange="mexc", symbol="BTC/USDT"}

# Buy pressure (trades per second, last 1m)
rate(crypto_trades_total{exchange="mexc", symbol="BTC/USDT", side="buy"}[1m])

# Sell pressure
rate(crypto_trades_total{exchange="mexc", symbol="BTC/USDT", side="sell"}[1m])

# Total trade volume (last 5m)
increase(crypto_trade_volume{exchange="mexc", symbol="BTC/USDT"}[5m])

# Order book depth (bids)
crypto_depth{exchange="mexc", symbol="BTC/USDT", side="bid"}

# Order book depth (asks)
crypto_depth{exchange="mexc", symbol="BTC/USDT", side="ask"}

# Current forming candle (for live chart append)
crypto_candle_open{exchange="mexc", symbol="BTC/USDT", timeframe="1m"}
crypto_candle_high{exchange="mexc", symbol="BTC/USDT", timeframe="1m"}
crypto_candle_low{exchange="mexc", symbol="BTC/USDT", timeframe="1m"}
crypto_candle_close{exchange="mexc", symbol="BTC/USDT", timeframe="1m"}
crypto_candle_volume{exchange="mexc", symbol="BTC/USDT", timeframe="1m"}
```

### SQL Queries (Historical Panels)

````sql
-- Candlestick chart (completed historical candles)
SELECT
  timestamp * 1000 as time,
  open, high, low, close, volume
FROM ohlcv_data
WHERE exchange = 'mexc'
  AND symbol = 'BTC/USDT'
  AND timeframe = '1m'
  AND timestamp > $__unixEpochFrom()
ORDER BY timestamp

-- Individual trades (for trade table)
SELECT
  timestamp * 1000 as time,
  side,
  price,
  amount,
  cost
FROM trades_stream
WHERE exchange = 'mexc'
  AND symbol = 'BTC/USDT'
  AND timestamp > $__unixEpochFrom()
ORDER BY timestamp DESC
LIMIT 100
## Docker Compose Configuration

```yaml
services:
  # Existing services (websocket, trader, etc.)...

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.retention.time=15d"
      - "--storage.tsdb.path=/prometheus"
      - "--web.enable-lifecycle"
    restart: unless-stopped

  pushgateway:
    image: prom/pushgateway:latest
    container_name: pushgateway
    ports:
      - "9091:9091"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
      - ./grafana/dashboards:/var/lib/grafana/dashboards
    depends_on:
      - prometheus
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_INSTALL_PLUGINS=frser-sqlite-datasource
      - GF_PATHS_PROVISIONING=/etc/grafana/provisioning
    restart: unless-stopped

volumes:
  prometheus-data:
  grafana-data:
````

### Prometheus Configuration

```yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 1s
  evaluation_interval: 1s

scrape_configs:
  - job_name: "pushgateway"
    honor_labels: true
    static_configs:
      - targets: ["pushgateway:9091"]
```

## Implementation Structure

```
simple-bot/
├── packages/
│   └── prometheus/
│       ├── __init__.py
│       ├── metrics.py          # Metric definitions
│       └── pusher.py            # Push logic with batching
│
├── prometheus/
│   └── prometheus.yml           # Prometheus config
│
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   ├── prometheus.yml   # Prometheus datasource
│   │   │   └── sqlite.yml       # SQLite datasource
│   │   └── dashboards/
│   │       └── dashboards.yml   # Dashboard auto-load config
│   └── dashboards/
│       └── trading.json         # Main trading dashboard
│
└── docker-compose.yml           # Add Prometheus + Grafana services
```

## Best Practices

### What to Store in Prometheus (Live Data)

- Current prices (last, bid, ask)
- Trade counts and rates
- Order book spread
- Recent volume (last 1-5 minutes)
- Current forming candle (open, high, low, close, volume)

### What to Store in Database (Historical Data)

- Completed OHLCV candles (all timeframes)
- Individual trades (complete history)
- Order book snapshots
- Strategy signals and positions (future)
- PNL history (future)

### Refresh Rate Guidelines

| Panel Type                | Data Source | Refresh Rate | Use Case             |
| ------------------------- | ----------- | ------------ | -------------------- |
| Price ticker              | Prometheus  | 500ms-1s     | See live ticks       |
| Trade flow                | Prometheus  | 1s           | Buy/sell pressure    |
| Order book                | Prometheus  | 500ms-1s     | Spread monitoring    |
| Candlesticks (historical) | Database    | 5s           | Completed candles    |
| Candlesticks (current)    | Prometheus  | 500ms-1s     | Forming candle       |
| Trade table               | Database    | 5s           | Recent trade history |

### Cardinality Management

**Good** (low cardinality):

```python
# ~10 unique label combinations
price_gauge.labels(exchange='mexc', symbol='BTC/USDT', type='last')
```

**Bad** (high cardinality):

```python
# ~1,000,000 unique combinations - will crash Prometheus!
price_gauge.labels(exchange='mexc', symbol='BTC/USDT', price_level='87850.23')
```

**Rule**: Keep unique label combinations < 10,000

## Migration Path to PostgreSQL

When SQLite becomes slow (>5GB or >10 queries/second):

1. **Install TimescaleDB** (PostgreSQL extension)

```bash
docker run -d --name timescaledb \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=password \
  timescale/timescaledb:latest-pg16
```

2. **Migrate schema** (same tables, just change connection)

```python
# packages/database/db.py
DATABASE_TYPE = os.getenv('DATABASE_TYPE', 'sqlite')  # or 'postgresql'

if DATABASE_TYPE == 'postgresql':
    engine = create_engine('postgresql://user:pass@localhost/trading')
else:
    engine = create_engine('sqlite:///data/trading.db')
```

3. **Convert to hypertables** (automatic partitioning)

```sql
SELECT create_hypertable('ohlcv_data', 'timestamp');
SELECT create_hypertable('trades_stream', 'timestamp');
```

4. **Add continuous aggregates** (pre-calculated rollups)

```sql
CREATE MATERIALIZED VIEW ohlcv_5m
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('5 minutes', timestamp) AS bucket,
  exchange, symbol, timeframe,
  first(open, timestamp) as open,
  max(high) as high,
  min(low) as low,
  last(close, timestamp) as close,
  sum(volume) as volume
FROM ohlcv_data
GROUP BY bucket, exchange, symbol, timeframe;
```

**Result**: 10-100x faster queries, same code!

## Performance Tuning

### Prometheus Pushgateway Batching

```python
# Push every 100ms OR every 10 trades (whichever comes first)
BATCH_SIZE = 10
BATCH_INTERVAL = 0.1  # seconds

async def batch_pusher(self):
    """Background task to push metrics in batches."""
    while self.running:
        await asyncio.sleep(BATCH_INTERVAL)
        if self.metrics_dirty:
            push_to_gateway(...)
            self.metrics_dirty = False
```

### Grafana Query Optimization

```sql
-- Bad: Full table scan
SELECT * FROM ohlcv_data WHERE symbol = 'BTC/USDT'

-- Good: Use time filter (indexed)
SELECT * FROM ohlcv_data
WHERE symbol = 'BTC/USDT'
  AND timestamp > $__unixEpochFrom()
```

## Monitoring & Alerts

### Prometheus Alerts

```yaml
# prometheus/alerts.yml
groups:
  - name: trading
    interval: 10s
    rules:
      - alert: HighSpread
        expr: crypto_spread{exchange="mexc"} > 10
        for: 30s
        labels:
          severity: warning
        annotations:
          summary: "Spread too high: {{ $value }}"

      - alert: WebSocketDown
        expr: rate(crypto_trades_total[1m]) == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "No trades received in 1 minute"
```

### Grafana Alerts

Can alert on both Prometheus and Database queries:

- Price crosses threshold
- Indicator signals (RSI overbought/oversold)
- Strategy drawdown exceeds limit
- WebSocket connection lost

## Access URLs

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Pushgateway**: http://localhost:9091

## Next Steps

1. **Phase 1**: Implement Prometheus metrics in WebSocket package
2. **Phase 2**: Create Grafana dashboard with live + historical panels
3. **Phase 3**: Add indicator pre-calculation background task
4. **Phase 4**: Build custom alerting for trading signals

## References

- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)
- [TimescaleDB Time-Series](https://docs.timescale.com/)
- [CCXT Pro WebSocket](https://github.com/ccxt/ccxt/wiki/ccxt.pro)
