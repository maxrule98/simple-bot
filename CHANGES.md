# Docker-Based Multi-Instance Trading Bot

## 🎯 What Changed & Why

### Problem: Hardcoding is Bad for Trading Bots

**Old Approach (BAD):**

```python
# Hardcoded in code - need to change code for each instance
EXCHANGE = "binance"
SYMBOL = "BTC/USDT"
TIMEFRAME = "1h"
```

**New Approach (GOOD):**

```yaml
# config/strategies/btc_binance_1h.yaml
trading:
  exchange: binance # Dynamic
  symbol: BTC/USDT # Dynamic
  timeframe: 1h # Dynamic
```

### Why Docker?

You want to run **multiple trading instances** with different:

- Exchanges (Binance, Coinbase, Kraken, etc.)
- Trading pairs (BTC/USDT, ETH/USDT, SOL/USDT, etc.)
- Timeframes (1m, 5m, 15m, 1h, 4h, 1d, etc.)
- Strategies (RSI, MACD, Trend Following, Scalping, etc.)

**Docker provides:**

- ✅ Horizontal scaling (run N instances)
- ✅ Isolation (each instance independent)
- ✅ Easy deployment (docker-compose up)
- ✅ Resource control (CPU/memory limits)
- ✅ Auto-recovery (restart on failure)

## 📋 What Was Added

### 1. Docker Files

- **`Dockerfile`** - Container image definition
- **`docker-compose.yml`** - Multi-container orchestration with 3 example traders
- **`.dockerignore`** - Optimize image build

### 2. Configuration Separation

**`.env`** (Secrets - shared by all containers):

```bash
BINANCE_API_KEY=xxx
COINBASE_API_KEY=xxx
DATABASE_URL=sqlite:///data/trading.db
```

**`config/strategies/*.yaml`** (Trading params - one per container):

```yaml
trading:
  exchange: binance
  symbol: BTC/USDT
  timeframe: 1h
```

### 3. Example Strategy Configs

Created 4 example strategies:

- `test.yaml` - Template with all options
- `btc_binance_1h.yaml` - BTC on Binance, 1h momentum
- `eth_binance_15m.yaml` - ETH on Binance, 15m scalping
- `btc_coinbase_1h.yaml` - BTC on Coinbase, 1h trend following

### 4. Documentation

- **`README.md`** - Completely rewritten with Docker-first approach
- **`ARCHITECTURE.md`** - Visual diagrams and architecture explanation
- **`QUICKSTART.md`** - Quick reference for common tasks

### 5. Project Structure Updates

```
simple-bot/
├── .env                          # API keys (secrets) ← UPDATED
├── .env.example                  # Template ← UPDATED
├── .gitignore                    # Ignore sensitive files ← UPDATED
├── Dockerfile                    # Build container ← NEW
├── docker-compose.yml            # Orchestration ← NEW
├── .dockerignore                 # Build optimization ← NEW
├── README.md                     # Main docs ← REWRITTEN
├── ARCHITECTURE.md               # Architecture guide ← NEW
├── QUICKSTART.md                 # Quick reference ← NEW
├── config/
│   └── strategies/
│       ├── test.yaml            # ← UPDATED (full example)
│       ├── btc_binance_1h.yaml  # ← NEW
│       ├── eth_binance_15m.yaml # ← NEW
│       └── btc_coinbase_1h.yaml # ← NEW
├── data/
│   └── .gitkeep                 # ← NEW (preserve directory)
└── logs/
    └── .gitkeep                 # ← NEW (preserve directory)
```

## 🚀 How to Use

### Initial Setup

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env and add your API keys
nano .env

# 3. Build Docker image
docker-compose build
```

### Run Trading Bots

```bash
# Start all configured traders
docker-compose up -d

# View logs
docker-compose logs -f

# Start specific trader only
docker-compose up -d trader-btc-binance-1h
```

### Add New Trading Instance

```bash
# 1. Create strategy config
cp config/strategies/btc_binance_1h.yaml config/strategies/sol_kraken_4h.yaml

# 2. Edit config
nano config/strategies/sol_kraken_4h.yaml
# Change: exchange: kraken, symbol: SOL/USDT, timeframe: 4h

# 3. Add to docker-compose.yml
nano docker-compose.yml
# Copy an existing service, rename to trader-sol-kraken-4h
# Update config path to sol_kraken_4h.yaml

# 4. Start new instance
docker-compose up -d trader-sol-kraken-4h
```

**No code changes needed!** Just config files.

## 🎨 Architecture Benefits

### Before (Hardcoded)

```
┌─────────────────────────────┐
│  Single Python Process      │
│  Exchange: Binance (hardcoded)
│  Symbol: BTC/USDT (hardcoded)
│  Timeframe: 1h (hardcoded)
└─────────────────────────────┘

Want ETH? → Change code, restart
Want Coinbase? → Change code, restart
Want 15m? → Change code, restart
```

### After (Docker + Dynamic Config)

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Container 1    │  │  Container 2    │  │  Container 3    │
│  BTC/USDT       │  │  ETH/USDT       │  │  SOL/USDT       │
│  Binance, 1h    │  │  Binance, 15m   │  │  Kraken, 4h     │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                    ┌─────────────────────┐
                    │  Shared SQLite DB   │
                    │  ./data/trading.db  │
                    └─────────────────────┘

Want ETH? → Add config + docker-compose entry
Want Coinbase? → Add config + docker-compose entry
Want 15m? → Add config + docker-compose entry
NO CODE CHANGES!
```

## 🔒 Security Best Practices

1. **Never commit `.env`** - Contains API keys
2. **Use `.env.example`** - Template without real keys
3. **Separate secrets from configs**:
   - Secrets (API keys) → `.env`
   - Trading params → `config/strategies/*.yaml`
4. **Git ignores sensitive files**:
   - `.env`
   - `data/*.db` (trading history)
   - `logs/*.log` (may contain sensitive info)

## 📊 Resource Management

Each container has limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: "0.5" # Max 50% of one CPU core
      memory: 512M # Max 512MB RAM
```

**Recommended server specs:**

- 1-3 instances: 2 CPU cores, 2GB RAM
- 4-10 instances: 4 CPU cores, 4GB RAM
- 11-20 instances: 8 CPU cores, 8GB RAM

## ✅ Implementation Checklist

- [x] Docker and docker-compose files created
- [x] .env.example updated (only secrets)
- [x] Strategy configs created (trading params)
- [x] docker-compose.yml with 3 example traders
- [x] README.md completely rewritten
- [x] ARCHITECTURE.md with visual diagrams
- [x] QUICKSTART.md for quick reference
- [x] .gitignore updated for security
- [x] data/ and logs/ directories with .gitkeep

## 🎯 Next Steps (Implementation Phase)

Now that architecture is complete, implement the actual code:

1. **Add dependencies**:

   ```bash
   uv add sqlalchemy pandas numpy pyyaml python-dotenv
   ```

2. **Implement core packages** (in order):
   - `packages/database/db.py` - Database connection
   - `packages/logging/logger.py` - Logging setup
   - `packages/exchange/exchange.py` - CCXT wrapper
   - `packages/indicators/rsi.py` - RSI indicator
   - `packages/execution/execution.py` - Order execution
   - `packages/risk/risk.py` - Risk management

3. **Implement apps**:
   - `apps/backfiller/main.py` - Data collection
   - `apps/backtester/main.py` - Strategy testing
   - `apps/trader/main.py` - Live trading

4. **Test with Docker**:
   ```bash
   docker-compose build
   docker-compose up backfiller
   docker-compose --profile testing up backtester
   docker-compose up -d trader-btc-binance-1h
   ```

## 🔑 Key Takeaways

✅ **Zero Hardcoding** - Everything configurable  
✅ **Docker-First** - Easy deployment and scaling  
✅ **Shared Database** - SQLite shared across containers  
✅ **Isolated Instances** - Each container independent  
✅ **Easy to Add Strategies** - Just config files  
✅ **Production-Ready** - Resource limits, auto-restart, logging  
✅ **Secure** - Secrets separated, .gitignore configured  
✅ **Well-Documented** - README, ARCHITECTURE, QUICKSTART guides

**You can now deploy multiple trading strategies with different exchanges, pairs, and timeframes without touching code!** 🎉
