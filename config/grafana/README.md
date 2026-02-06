# Grafana + Prometheus Monitoring Setup

## Quick Start

1. **Start all services** (traders + monitoring stack):

   ```bash
   docker compose up -d
   ```

2. **Access Grafana**:
   - URL: http://localhost:3000
   - Username: `admin`
   - Password: `admin` (change on first login)

3. **View real-time dashboard**:
   - Navigate to "Dashboards" → "Trading Bot Real-Time Monitor"
   - Refresh rate: 1 second (live updates)

## Services

| Service     | Port | Purpose                              |
| ----------- | ---- | ------------------------------------ |
| Grafana     | 3000 | Visualization & dashboards           |
| Prometheus  | 9090 | Metrics database (15 days retention) |
| Pushgateway | 9091 | Receives metrics from traders        |

## Architecture

```
Trading Bots → Pushgateway → Prometheus → Grafana
                  (9091)         (9090)     (3000)
```

## Available Metrics

### Price Metrics

- `crypto_price{exchange, symbol, type}` - Current price (last/bid/ask)
- `crypto_spread{exchange, symbol}` - Bid-ask spread

### Candle Metrics (Current Forming)

- `crypto_candle_open{exchange, symbol, timeframe}` - Candle open
- `crypto_candle_high{exchange, symbol, timeframe}` - Candle high
- `crypto_candle_low{exchange, symbol, timeframe}` - Candle low
- `crypto_candle_close{exchange, symbol, timeframe}` - Candle close (last price)
- `crypto_candle_volume{exchange, symbol, timeframe}` - Candle volume

### Trade Metrics

- `crypto_trades_total{exchange, symbol, side}` - Total trades counter
- `crypto_trade_volume{exchange, symbol}` - Rolling trade volume
- `crypto_trade_size{exchange, symbol}` - Trade size histogram

### Order Book Metrics

- `crypto_orderbook_bid_price{exchange, symbol, level}` - Bid price by level (0-9)
- `crypto_orderbook_ask_price{exchange, symbol, level}` - Ask price by level (0-9)
- `crypto_orderbook_bid_quantity{exchange, symbol, level}` - Bid quantity by level
- `crypto_orderbook_ask_quantity{exchange, symbol, level}` - Ask quantity by level
- `crypto_orderbook_bid_cumulative{exchange, symbol, level}` - Cumulative bids (depth chart)
- `crypto_orderbook_ask_cumulative{exchange, symbol, level}` - Cumulative asks (depth chart)
- `crypto_orderbook_total_bids{exchange, symbol}` - Total bid liquidity (USD value)
- `crypto_orderbook_total_asks{exchange, symbol}` - Total ask liquidity (USD value)

### Strategy Metrics

- `strategy_signals_total{strategy_id, signal_type}` - Signals generated
- `strategy_position_size{strategy_id, symbol}` - Current position size
- `strategy_pnl{strategy_id, symbol}` - Current PNL
- `strategy_trades_total{strategy_id, side}` - Trades executed

### Performance Metrics

- `websocket_latency_seconds{exchange, stream_type}` - WebSocket latency histogram

## Enabling Metrics in Code

The metrics are automatically pushed when WebSocket data is received. To enable:

```python
from packages.metrics import PrometheusMetrics

# Initialize (once per trading bot)
metrics = PrometheusMetrics(exchange="mexc")

# Update metrics (in WebSocket handlers)
metrics.update_price(symbol="BTC/USDT", last=43250.5, bid=43250.0, ask=43251.0)
metrics.update_candle(symbol="BTC/USDT", timeframe="1m",
                     open_=43200, high=43300, low=43180, close=43250, volume=12.5)
metrics.update_orderbook(symbol="BTC/USDT", bids=bids, asks=asks, depth=10)

# Push to Pushgateway (every 1-5 seconds)
metrics.push()
```

## Example Grafana Queries

### Live Price

```promql
crypto_price{symbol="BTC/USDT", type="last"}
```

### Trades Per Minute

```promql
rate(crypto_trades_total{symbol="BTC/USDT"}[1m])
```

### P95 WebSocket Latency

```promql
histogram_quantile(0.95, rate(websocket_latency_seconds_bucket[1m]))
```

### Order Book Imbalance

```promql
(crypto_orderbook_total_bids - crypto_orderbook_total_asks) /
(crypto_orderbook_total_bids + crypto_orderbook_total_asks)
```

## Customizing Dashboards

1. **Edit existing dashboard**:
   - Open dashboard in Grafana
   - Click "⚙️ Dashboard settings" → "JSON Model"
   - Edit and save

2. **Create new dashboard**:
   - Click "+" → "Dashboard"
   - Add panels with PromQL queries
   - Save to `config/grafana/dashboards/`

3. **Auto-reload dashboards**:
   - Dashboards in `config/grafana/dashboards/` are auto-loaded
   - Restart Grafana or wait 10 seconds for updates

## Troubleshooting

### No data in Grafana?

1. Check Pushgateway has metrics: http://localhost:9091
2. Check Prometheus scraping: http://localhost:9090/targets
3. Verify trading bots are running: `docker compose ps`

### Metrics not updating?

- Ensure `prometheus-client` is installed: `uv pip install prometheus-client`
- Check logs: `docker compose logs -f trader-btc-usdt-mexc-1m`
- Verify PROMETHEUS_PUSHGATEWAY env var

### High memory usage?

- Reduce Prometheus retention: `--storage.tsdb.retention.time=7d`
- Reduce scrape frequency: `scrape_interval: 5s`
- Limit orderbook depth: `depth=5` instead of `depth=10`

## Data Retention

- **Prometheus**: 15 days (in-memory + disk)
- **Database (SQLite)**: Permanent (historical analysis)

Use Prometheus for real-time monitoring, database for backtesting and historical analysis.

## Performance Tips

1. **Push frequency**: 1-5 seconds (balance freshness vs overhead)
2. **Orderbook depth**: 10 levels (depth=10) is usually sufficient
3. **Scrape interval**: 1s for live feel, 5s to reduce load
4. **Refresh rate**: 1s in Grafana (adjust based on preference)

## Security

⚠️ **Change default Grafana password!**

```bash
# In docker-compose.yml
environment:
  - GF_SECURITY_ADMIN_PASSWORD=your_secure_password
```

For production:

- Enable HTTPS (reverse proxy)
- Restrict ports (use internal networks)
- Set up authentication (OAuth, LDAP)
