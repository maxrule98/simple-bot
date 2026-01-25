# Trading Bot - Enterprise-Grade Architecture

A professional cryptocurrency trading bot with a clean, enterprise-grade architecture designed for **complete modularity and dynamic deployment**. Features separate applications for live trading, backtesting, and data management, with Docker-based orchestration for running multiple trading instances simultaneously.

## 🎯 Key Features

- 🐳 **Docker-First Architecture** - Deploy multiple instances with different strategies
- 📊 **Completely Dynamic** - Zero hardcoding: exchange, symbol, timeframe, strategy all configurable
- 💾 **SQLite database** - Shared persistent storage across all instances
- 📈 **YAML-based strategies** - Define strategies declaratively without code changes
- 🔄 **CCXT integration** - Access to 100+ cryptocurrency exchanges
- ⚡ **UV package management** - Fast dependency management
- 🧩 **Modular design** - Clean separation of concerns
- 🔀 **Horizontal scaling** - Run N trading instances in parallel

## 🏗️ Architecture Philosophy

### No Hardcoding - Complete Modularity

This bot is designed from the ground up to be **completely dynamic**:

- ❌ **NO** hardcoded exchanges in code
- ❌ **NO** hardcoded trading pairs
- ❌ **NO** hardcoded timeframes
- ❌ **NO** hardcoded strategies

Instead:

- ✅ All trading parameters defined in `config/strategies/*.yaml`
- ✅ Secrets (API keys) in `.env` (shared across instances)
- ✅ Each Docker container runs with different strategy config
- ✅ Easy to add new instances without code changes

### Docker-Based Multi-Instance Deployment

**Why Docker?**

- Run multiple trading strategies simultaneously
- Each container isolated with its own configuration
- Easy horizontal scaling
- Resource limits per instance
- Shared database across all instances

**Example Deployment:**

```
Container 1: BTC/USDT on Binance, 1h timeframe, RSI strategy
Container 2: ETH/USDT on Binance, 15m timeframe, Scalping strategy
Container 3: BTC/USD on Coinbase, 1h timeframe, Trend following
Container 4: SOL/USDT on Kraken, 4h timeframe, Mean reversion
... and so on
```

## 📁 Project Structure

```
simple-bot/
├── apps/                          # Standalone applications
│   ├── trader/                    # Live trading application
│   │   ├── main.py               # Entry point for live trading
│   │   └── utils/                # Trading-specific utilities
│   ├── backtester/               # Backtesting application
│   │   ├── main.py               # Entry point for backtesting
│   │   └── utils/                # Backtesting utilities
│   └── backfiller/               # Historical data collection
│       ├── main.py               # Entry point for data backfilling
│       └── utils/                # Backfiller utilities
│
├── packages/                      # Reusable packages/modules
│   ├── core/                     # Core trading bot logic
│   │   └── main.py
│   ├── exchange/                 # Exchange abstraction layer
│   │   └── main.py               # Dynamic exchange switching
│   ├── execution/                # Trade execution engine
│   │   └── main.py               # Order placement and management
│   ├── timeframes/               # Timeframe management
│   │   └── main.py               # Dynamic timeframe switching
│   └── indicators/               # Technical indicators
│       ├── main.py               # Indicator index/registry
│       ├── utils.py/             # Indicator utilities
│       ├── conventional/         # Traditional indicators
│       │   └── rsi/              # RSI indicator
│       │       ├── main.py
│       │       └── utils/
│       └── ML/                   # Machine learning indicators
│           └── ARIMA/            # ARIMA forecasting
│               ├── main.py
│               └── utils/
│
├── config/                        # Configuration management
│   ├── config.py                 # Main configuration module
│   └── strategies/               # Strategy configurations
│       └── test.yaml             # Example strategy config
│
├── data/                          # Data storage (auto-created)
│   └── trading.db                # SQLite database
│
├── pyproject.toml                # Dependencies and project metadata
└── README.md                      # This file
```

## 🏗️ Architecture Overview

### Applications (`apps/`)

The project uses a multi-application architecture where each app serves a specific purpose:

#### **Trader** (`apps/trader/`)

- **Purpose**: Live trading operations with real money
- **Responsibility**: Executes trades on live markets based on signals
- **Shared Code**: Uses the same strategy logic as backtester for consistency
- **Entry Point**: `apps/trader/main.py`

#### **Backtester** (`apps/backtester/`)

- **Purpose**: Simulate trades using historical data
- **Responsibility**: Evaluate strategy performance before going live
- **Shared Code**: Reuses strategy and execution logic from packages
- **Entry Point**: `apps/backtester/main.py`

#### **Backfiller** (`apps/backfiller/`)

- **Purpose**: Populate historical market data
- **Responsibility**: Download and store historical OHLCV data for analysis
- **Entry Point**: `apps/backfiller/main.py`

### Packages (`packages/`)

Reusable, modular components shared across all applications:

#### **Core** (`packages/core/`)

- Central trading bot logic
- Orchestrates other packages
- Main coordination layer

#### **Exchange** (`packages/exchange/`)

- Exchange abstraction layer
- Dynamic exchange switching based on configuration
- Unified interface for all exchanges (via CCXT)
- Supports Binance, Kraken, Coinbase, and 100+ others

#### **Execution** (`packages/execution/`)

- Trade execution engine
- Places orders based on signals
- Manages order lifecycle
- Handles order confirmation and tracking

#### **Timeframes** (`packages/timeframes/`)

- Dynamic timeframe management
- Switch between 1m, 5m, 15m, 1h, 4h, 1d, etc.
- Modular design for easy timeframe addition
- Timeframe conversion utilities

#### **Indicators** (`packages/indicators/`)

- Indicator registry and management
- Two categories:
  - **Conventional** (`conventional/`): Traditional technical indicators
    - RSI, MACD, Bollinger Bands, etc.
  - **ML** (`ML/`): Machine learning-based indicators
    - ARIMA forecasting, LSTM predictions, etc.
- Each indicator in its own folder with utilities
- Example structure:
  - `packages/indicators/conventional/rsi/main.py`
  - `packages/indicators/ML/ARIMA/main.py`

### Configuration (`config/`)

#### **Main Config** (`config/config.py`)

- Central configuration module
- Manages app settings and parameters
- Environment-specific configurations

#### **Strategy Configs** (`config/strategies/`)

- YAML-based strategy definitions
- Declarative strategy configuration
- Easy strategy composition without code changes
- Example: `test.yaml`

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.12+ (for local development)
- [UV](https://github.com/astral-sh/uv) package manager (for local development)

### Setup

1. **Clone and Configure**

   ```bash
   cd simple-bot

   # Copy environment template
   cp .env.example .env

   # Edit .env and add your API keys
   nano .env
   ```

2. **Create Strategy Configurations**

   Strategy configs are in `config/strategies/*.yaml`. See examples:
   - `btc_binance_1h.yaml` - BTC on Binance, 1-hour timeframe
   - `eth_binance_15m.yaml` - ETH on Binance, 15-minute scalping
   - `btc_coinbase_1h.yaml` - BTC on Coinbase, 1-hour trend following

3. **Build Docker Image**

   ```bash
   docker-compose build
   ```

### Running with Docker (Recommended)

#### Start All Trading Instances

```bash
# Start all configured trading bots
docker-compose up -d

# View logs
docker-compose logs -f

# View specific bot logs
docker-compose logs -f trader-btc-binance-1h
```

#### Start Specific Instances

```bash
# Only run BTC trader
docker-compose up -d trader-btc-binance-1h

# Run multiple specific traders
docker-compose up -d trader-btc-binance-1h trader-eth-binance-15m
```

#### Backfill Historical Data

```bash
# Run backfiller to populate database
docker-compose up backfiller

# Check data
docker exec -it backfiller ls -lh /app/data
```

#### Run Backtests

```bash
# Backtester is in 'testing' profile
docker-compose --profile testing up backtester
```

### Running Locally (Development)

```bash
# Install dependencies
uv sync

# Run trader with specific strategy
uv run python apps/trader/main.py --config config/strategies/btc_binance_1h.yaml

# Run backfiller
uv run python apps/backfiller/main.py

# Run backtester
uv run python apps/backtester/main.py --config config/strategies/test.yaml
```

### Adding New Trading Instances

1. **Create Strategy Config**

   ```bash
   # Copy existing config
   cp config/strategies/btc_binance_1h.yaml config/strategies/sol_kraken_4h.yaml

   # Edit new config
   nano config/strategies/sol_kraken_4h.yaml
   ```

   ```yaml
   trading:
     exchange: kraken
     symbol: SOL/USDT
     timeframe: 4h
   # ... rest of strategy
   ```

2. **Add to docker-compose.yml**

   ```yaml
   trader-sol-kraken-4h:
     build: .
     container_name: trader-sol-kraken-4h
     command: python apps/trader/main.py --config /app/config/strategies/sol_kraken_4h.yaml
     volumes:
       - ./data:/app/data
       - ./logs:/app/logs
       - ./config/strategies:/app/config/strategies:ro
     env_file:
       - .env
     restart: unless-stopped
   ```

3. **Start New Instance**

   ```bash
   docker-compose up -d trader-sol-kraken-4h
   ```

**That's it!** No code changes needed.

## ⚙️ Configuration

### Architecture: Secrets vs Trading Parameters

**Clear Separation:**

| Configuration Type     | Location                   | Purpose                               | Shared?                 |
| ---------------------- | -------------------------- | ------------------------------------- | ----------------------- |
| **Secrets** (API keys) | `.env`                     | Authentication credentials            | ✅ Yes - all containers |
| **Trading Parameters** | `config/strategies/*.yaml` | Exchange, symbol, timeframe, strategy | ❌ No - per container   |

### 1. Environment Variables (`.env`) - Secrets Only

Contains **only** API credentials and system-wide settings. **Never** put trading parameters here.

```bash
# .env
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
COINBASE_API_KEY=your_key
COINBASE_API_SECRET=your_secret
DATABASE_URL=sqlite:///data/trading.db
LOG_LEVEL=INFO
```

### 2. Strategy Configuration (YAML) - Trading Parameters

Each strategy config defines **all** trading parameters dynamically:

```yaml
# config/strategies/my_strategy.yaml
trading:
  exchange: binance # Dynamic - change per instance
  symbol: BTC/USDT # Dynamic - any pair
  timeframe: 1h # Dynamic - any timeframe

strategy:
  name: "RSI_Strategy"
  indicators:
    - name: rsi
      period: 14
      overbought: 70
      oversold: 30

  entry:
    long:
      - rsi < 30
    short:
      - rsi > 70

  exit:
    take_profit: 2.5
    stop_loss: 1.5

risk:
  position_size: 100
  max_open_positions: 3
```

### 3. Supported Exchanges

All exchanges supported by [CCXT](https://github.com/ccxt/ccxt) - 100+ exchanges:

- Binance, Binance US
- Coinbase, Coinbase Pro
- Kraken
- Bybit
- OKX
- Bitfinex
- And many more...

Just change `exchange: binance` to `exchange: kraken` in your strategy YAML.

### 4. Supported Timeframes

- **Minutes**: 1m, 5m, 15m, 30m
- **Hours**: 1h, 2h, 4h, 6h, 12h
- **Days**: 1d, 3d
- **Weeks**: 1w
- **Months**: 1M

Just change `timeframe: 1h` to `timeframe: 15m` in your strategy YAML.

## 📊 Indicators

### Conventional Indicators (`packages/indicators/conventional/`)

Traditional technical analysis indicators:

- **RSI** (Relative Strength Index) - `conventional/rsi/`
- **MACD** (Moving Average Convergence Divergence)
- **Bollinger Bands**
- **Moving Averages** (SMA, EMA)
- **Stochastic Oscillator**
- And more...

Each indicator follows the structure:

````
packages/indicators/conventional/[indicator_name]/
├── maDeployment Workflow

### 1. Development & Testing

```bash
# Local development
uv sync
uv run python apps/backfiller/main.py
uv run python apps/backtester/main.py --config config/strategies/test.yaml
````

### 2. Create Strategy

```bash
# Copy template
cp config/strategies/test.yaml config/strategies/my_new_strategy.yaml

# Edit parameters
nano config/strategies/my_new_strategy.yaml
```

### 3. Backtest Strategy

```bash
# Test locally
uv run python apps/backtester/main.py --config config/strategies/my_new_strategy.yaml

# Or with Docker
docker-compose --profile testing up backtester
```

### 4. Deploy to Production

```bash
# Add to docker-compose.yml
nano docker-compose.yml

# Start new instance
docker-compose up -d trader-my-new-strategy

# Monitor
docker-compose logs -f trader-my-new-strategy
```

### 5. Scale Horizontally

```bash
# Add more strategies in docker-compose.yml
# Each container runs independently with shared database

docker-compose up -d  # Start all instances
```

## 🐳 Docker Commands Cheat Sheet

````bash
# Build
docker-compose build

# Start all
docker-compose up -d

# Start specific
docker-compose up -d trader-btc-binance-1h

# Stop all
docker-compose down

# Stop specific
docker-compose stop trader-btc-binance-1h

# View logs (all)
docker-compose logs -f

# View logs (specific)
docker-compose logs -f trader-btc-binance-1h

# Restart
docker-compose restart trader-btc-binance-1h

# View running containers
docker-compose ps

# Ex1. Zero Hardcoding

**Problem**: Traditional bots hardcode exchange/symbol/timeframe in code
**Solution**: Everything in YAML configs

```yaml
# Want to trade ETH instead of BTC? Just edit YAML
trading:
  symbol: ETH/USDT  # Was: BTC/USDT
````

### 2. Docker-First Deployment

**Problem**: Running multiple strategies means multiple processes to manage  
**Solution**: Docker containers with shared database

```bash
# Each strategy runs in isolated container
docker-compose up -d  # Starts all strategies
```

### 3. Horizontal Scalability

**Problem**: Can't easily add more strategies  
**Solution**: Add config + docker-compose entry = new instance

```yaml
# Add to docker-compose.yml - no code changes
trader-new-strategy:
  command: python apps/trader/main.py --config /app/config/strategies/new.yaml
```

### 4. Separation of Concerns

- **Apps** (`apps/`) - Specific use cases (trader, backtester, backfiller)
- **Packages** (`packages/`) - Reusable logic (indicators, execution, exchange)
- **Config** (`config/`) - All parameters (YAML files)
- **Secrets** (`.env`) - API credentials only

### 5. Shared Database

All containers share same SQLite database:

- Single source of truth for historical data
- Backfiller populates data once
- All traders read from same database
- No data duplication

### 6. Consistency

Backtester and Trader share exact same code:

- Same indicators from `packages/indicators/`
- Same execution logic from `packages/execution/`
- Same exchange wrapper from `packages/exchange/`
- ⚠️ **Test Thoroughly** - Always backtest before live trading
- 💰 **Start Small** - Use minimal capital initially
- 📄 **Paper Trade** - Test with live data but no real orders first
- 🛡️ **Risk Management** - Implement stop-losses and position sizing
- 👀 **Monitor Actively** - Check logs: `docker-compose logs -f`
- 🔐 **Secure API Keys** - Never commit `.env` to git
- ⏱️ **Enable Rate Limits** - Prevent exchange bans
- 📊 **Comprehensive Logging** - All containers log to `./logs/`
- 🚨 **Error Handling** - Containers auto-restart on failure
- 💾 **Backup Database** - Regular backups of `./data/trading.db`

### Resource Management

Each container has resource limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: "0.5" # Max CPU usage
      memory: 512M # Max memory
```

Adjust based on your server capacity.

### Adding Dependencies

```bash
# Production dependencies
uv add pandas numpy ta-lib

# Development dependencies
uv add --dev pytest black ruff mypy
```

### Code Quality

````bash
# Format code
uv run black apps/ packages/ config/

# LiDocker Issues

```bash
# Container won't start
docker-compose logs trader-btc-binance-1h

# Check container status
docker-compose ps

# Rebuild image
docker-compose build --no-cache

# Remove all and restart
docker-compose down -v
docker-compose up -d
````

### Database Issues

```bash
# Check database exists
ls -lh data/trading.db

# Database locked
# Stop all containers first
docker-compose down
docker-compose up -d
```

### Exchange Errors

- Verify API keys in `.env`
- Check exchange name matches CCXT: [supported exchanges](https://github.com/ccxt/ccxt#supported-cryptocurrency-exchange-markets)
- Enable rate limiting in strategy YAML
- Some exchanges require API keys even for public data

### Strategy Config Errors

```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/strategies/test.yaml'))"

# Check file is mounted in container
docker-compose exec trader-btc-binance-1h ls /app/config/strategies/
```

### Multiple Instances Not Working

- Check each uses different `container_name` in docker-compose.yml
- Ensure strategy configs have different filenames
- Verify all share same database volume: `./data:/app/data`

### Separation of Concerns

- **Apps** handle specific use cases (trading, backtesting, backfilling)
- **Packages** provide reusable functionality
- **Config** manages all settings declaratively

### Consistency

- Backtester and Trader share the same codebase
- What works in backtesting works in live trading
- No surprises when going from simulation to production

### Scalability

- Add new indicators by creating folders
- Support new exchanges through configuration
- Define new strategies with YAML files

### Maintainability

- Clear folder structure
- Each component has a single responsibility
- Easy to locate and update specific functionality

## 📦 Package Organization

### Why This Structure?

1. **`apps/`** - Separate applications keep concerns isolated
   - Each app can be run independently
   - Different entry points for different purposes
   - Easy to deploy specific functionality

2. **`packages/`** - Shared code prevents duplication
   - Single source of truth for business logic
   - Reusable across all applications
   - Easier testing and maintenance

3. **`config/`** - Configuration as code
   - YAML for strategies (non-developers can edit)
   - Python for complex configurations
   - Separation of code and configuration

## ⚠️ Safety & Best Practices

**Critical Guidelines:**

- **Test Thoroughly** - Always backtest before live trading
- **Start Small** - Use minimal capital initially
- **Paper Trade** - Test with live data but no real orders first
- **Risk Management** - Implement stop-losses and position sizing
- **Monitor Actively** - Never leave trading bots unattended
- **Secure API Keys** - Use environment variables, never commit keys
- **Enable Rate Limits** - Prevent exchange bans
- **Comprehensive Logging** - Track all actions for debugging
- **Error Handling** - Handle edge cases gracefully

## 🐛 Troubleshooting

### Import Errors

- Ensure you're running from project root
- Use `uv run python` not just `python`
- Check that all folders have proper structure

### Exchange Errors

- Verify exchange name is spelled correctly
- Enable rate limiting in configuration
- Some exchanges require API keys for public data
- Check exchange status (maintenance, downtime)

### Database Errors

- Ensure `data/` directory is writable
- Check available disk space
- Verify SQLite is properly installed

### Backtest vs Live Discrepancies

- Ensure both use same code from `packages/`
- Check for lookahead bias in indicators
- Verify slippage and fees are modeled
- Confirm identical strategy parameters

## 📚 Further Reading

### Project Components

- Review code in `packages/` to understand core functionality
- Check `apps/` for application-specific logic
- Examine `config/strategies/` for strategy examples

### External Resources

- [CCXT Documentation](https://docs.ccxt.com/) - Exchange integration
- [UV Documentation](https://github.com/astral-sh/uv) - Package manager
- [SQLite Documentation](https://www.sqlite.org/docs.html) - Database

## 🤝 Contributing

When adding new features:

1. **Indicators** - Add to `packages/indicators/conventional/` or `packages/indicators/ML/`
2. **Exchanges** - Extend `packages/exchange/main.py`
3. **Strategies** - Create YAML in `config/strategies/`
4. **Apps** - Add new application in `apps/` if needed
5. Follow the existing folder structure
6. Add utilities in respective `utils/` folders
7. Update this README with new functionality

## 📄 License

MIT

## ⚖️ Disclaimer

**Educational and Informational Purposes Only**

This software is provided for educational and informational purposes only. Cryptocurrency trading carries substantial risk of loss. You should never invest money that you cannot afford to lose.

The developers and contributors:

- Make no guarantees about profitability
- Are not responsible for any financial losses
- Provide no warranty of any kind
- Do not provide financial advice
- Recommend consulting financial professionals

**Use at your own risk.**
