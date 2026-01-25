# Quick Reference Guide

## Common Commands

### Docker Operations

```bash
# Start all trading instances
docker-compose up -d

# Stop all
docker-compose down

# View logs (all containers)
docker-compose logs -f

# View logs (specific container)
docker-compose logs -f trader-btc-binance-1h

# Restart specific container
docker-compose restart trader-btc-binance-1h

# Check status
docker-compose ps

# Rebuild images
docker-compose build --no-cache
```

### Adding New Trading Instance

1. **Create strategy config**

   ```bash
   cp config/strategies/btc_binance_1h.yaml config/strategies/my_new_strategy.yaml
   nano config/strategies/my_new_strategy.yaml
   ```

2. **Edit strategy parameters**

   ```yaml
   trading:
     exchange: kraken # Change exchange
     symbol: SOL/USDT # Change pair
     timeframe: 4h # Change timeframe
   # ... customize strategy
   ```

3. **Add to docker-compose.yml**

   ```yaml
   trader-sol-kraken-4h:
     build: .
     container_name: trader-sol-kraken-4h
     command: python apps/trader/main.py --config /app/config/strategies/my_new_strategy.yaml
     volumes:
       - ./data:/app/data
       - ./logs:/app/logs
       - ./config/strategies:/app/config/strategies:ro
     env_file:
       - .env
     restart: unless-stopped
     deploy:
       resources:
         limits:
           cpus: "0.5"
           memory: 512M
   ```

4. **Start new instance**
   ```bash
   docker-compose up -d trader-sol-kraken-4h
   ```

## File Locations

```
.env                              # API keys (secrets)
config/strategies/*.yaml          # Trading parameters (per instance)
data/trading.db                   # SQLite database (shared)
logs/                             # Application logs (shared)
Dockerfile                        # Container image definition
docker-compose.yml                # Multi-container orchestration
```

## Configuration Reference

### .env (Secrets Only)

```bash
BINANCE_API_KEY=xxx
BINANCE_API_SECRET=xxx
COINBASE_API_KEY=xxx
COINBASE_API_SECRET=xxx
DATABASE_URL=sqlite:///data/trading.db
LOG_LEVEL=INFO
```

### Strategy YAML (Trading Parameters)

```yaml
trading:
  exchange: binance|coinbase|kraken|bybit|etc
  symbol: BTC/USDT|ETH/USDT|any_pair
  timeframe: 1m|5m|15m|1h|4h|1d|etc

strategy:
  name: strategy_name
  indicators:
    - name: rsi
      period: 14
    - name: macd
      fast: 12
      slow: 26

  entry:
    long: [conditions]
    short: [conditions]

  exit:
    take_profit: 2.5 # percent
    stop_loss: 1.5 # percent

risk:
  position_size: 100
  max_open_positions: 3

execution:
  order_type: limit|market
```

## Supported Exchanges

Binance, Binance US, Coinbase, Coinbase Pro, Kraken, Bybit, OKX, Bitfinex, KuCoin, Gate.io, Huobi, Bitstamp, Gemini, and 90+ more via [CCXT](https://github.com/ccxt/ccxt#supported-cryptocurrency-exchange-markets)

## Supported Timeframes

1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 3d, 1w, 1M

## Troubleshooting

### Container won't start

```bash
docker-compose logs trader-btc-binance-1h
```

### Database locked

```bash
docker-compose down
docker-compose up -d
```

### Strategy config not loading

```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/strategies/test.yaml'))"
```

### Check available indicators

```bash
ls packages/indicators/
```

## Development Workflow

1. **Backfill data**

   ```bash
   docker-compose up backfiller
   ```

2. **Backtest strategy**

   ```bash
   docker-compose --profile testing up backtester
   ```

3. **Deploy live**

   ```bash
   docker-compose up -d trader-xxx
   ```

4. **Monitor**
   ```bash
   docker-compose logs -f
   ```

## Safety Checklist

- [ ] API keys in `.env`, not in strategy configs
- [ ] Backtest strategy before going live
- [ ] Start with small position sizes
- [ ] Set stop losses in strategy config
- [ ] Monitor logs regularly
- [ ] Backup database: `cp data/trading.db data/trading.db.backup`
- [ ] Test with paper trading first
- [ ] Resource limits set in docker-compose.yml
- [ ] Never commit `.env` to git

## Scaling Guide

| Instances | Recommended Resources |
| --------- | --------------------- |
| 1-3       | 2 CPU cores, 2GB RAM  |
| 4-10      | 4 CPU cores, 4GB RAM  |
| 11-20     | 8 CPU cores, 8GB RAM  |

Adjust `cpus` and `memory` in docker-compose.yml per container.

## Directory Structure

```
simple-bot/
├── .env                    # Secrets
├── docker-compose.yml      # Orchestration
├── Dockerfile              # Image definition
├── apps/                   # Applications
│   ├── trader/            # Live trading
│   ├── backtester/        # Strategy testing
│   └── backfiller/        # Data collection
├── packages/              # Reusable code
│   ├── exchange/          # CCXT wrapper
│   ├── execution/         # Order placement
│   ├── indicators/        # RSI, MACD, etc.
│   ├── database/          # SQLite ops
│   ├── risk/              # Risk management
│   └── logging/           # Logging
├── config/
│   ├── settings.py        # System config
│   ├── exchanges.py       # Exchange configs
│   └── strategies/        # Strategy YAMLs ← YOU EDIT THESE
├── data/                  # SQLite database (auto-created)
└── logs/                  # Application logs (auto-created)
```

## Key Principle

**Everything is dynamic. Nothing is hardcoded.**

- Want different exchange? Edit YAML
- Want different pair? Edit YAML
- Want different timeframe? Edit YAML
- Want different strategy? Edit YAML

**No code changes needed!**
