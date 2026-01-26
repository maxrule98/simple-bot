# Simple Trading Bot

A modular cryptocurrency trading bot with SQLite storage and CCXT exchange integration. Currently features a working data collection system with plans for backtesting and live trading.

## 🎯 Key Features

- 🐳 **Docker-First Architecture** - Deploy multiple instances with different strategies
- 📊 **Completely Dynamic** - Zero hardcoding: exchange, symbol, timeframe, strategy all configurable
- 💾 **SQLite database** - Shared persistent storage across all instances
- 📈 **YAML-based strategies** - Define strategies declaratively without code changes
- 🔄 **CCXT integration** - Access to 100+ cryptocurrency exchanges
- 📡 **Real-time streaming** - WebSocket support for OHLCV, ticker, order book, and trades
- ⚡ **UV package management** - Fast dependency management
- 🧩 **Modular design** - Clean separation of concerns
- 🔀 **Horizontal scaling** - Run N trading instances in parallel

## 🏗️ Architecture Philosophy

### Configuration-Driven Design

Trading parameters are configured via YAML files rather than hardcoded:

- Exchange, symbol, timeframe defined in `config/strategies/*.yaml`
- API keys stored in `.env` file
- Easy to modify without changing code

### Multi-Instance Deployment (Planned)

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
├── apps/                         # Standalone applications
│   ├── backfiller/               # ✅ Historical data collector
│   │   └── main.py               # Intelligent backfill with pagination
│   ├── backtester/               # 📋 Strategy backtester (planned)
│   │   └── main.py               # Stub
│   └── trader/                   # 📋 Live trading (planned)
│       └── main.py               # Stub
│
├── packages/                     # Reusable modules
│   ├── database/                 # ✅ Database management
│   │   └── db.py                 # SQLite wrapper with WAL mode
│   ├── logging/                  # ✅ Structured logging
│   │   └── logger.py             # File + console logging
│   ├── websocket/                # ✅ Real-time streaming (implemented)
│   │   └── websocket.py          # CCXT Pro WebSocket manager
│   ├── indicators/               # 📋 Technical indicators
│   │   └── rsi.py                # RSI stub
│   ├── core/                     # 📋 Core logic (planned)
│   │   └── core.py               # Stub
│   ├── exchange/                 # 📋 Exchange abstraction (planned)
│   │   └── exchange.py           # Stub
│   ├── execution/                # 📋 Order execution (planned)
│   ├── timeframes/               # 📋 Timeframe utilities (planned)
│   ├── risk/                     # 📋 Risk management (planned)
│   └── utils/                    # Utility functions
│
├── config/                       # Configuration
│   ├── settings.py               # App settings
│   ├── exchanges.py              # Exchange credentials management
│   └── strategies/               # Strategy YAML files
│       ├── btc_usdt_mexc_1m.yaml
│       ├── btc_usdt_mexc_1h.yaml
│       ├── btc_usdt_mexc_4h.yaml
│       └── eth_usdt_mexc_15m.yaml
│
├── scripts/                      # Utility scripts
│   └── populate_db.py            # Automated multi-symbol backfill
│
├── data/                         # Generated data (gitignored)
│   └── trading.db                # SQLite database (~218 MB)
│
├── docs/                         # Documentation
│   ├── ARCHITECTURE.md           # Architecture diagrams
│   ├── DATABASE.md               # Database schema details
│   ├── WEBSOCKET.md              # WebSocket integration guide
│   ├── ORDERBOOK.md              # Order book & trade streaming
│   ├── DATA_STRATEGY.md          # Multi-instance data storage
│   ├── DATA_FLOW.md              # REST vs WebSocket comparison
│   └── QUICKSTART.md             # Quick reference
│
├── schema.py                     # Database table initialization
├── pyproject.toml                # Dependencies (managed by uv)
├── docker-compose.yml            # Container orchestration
└── README.md                     # This file
```

## 🏗️ Architecture Overview

### Applications (`apps/`)

The project uses a multi-application architecture where each app serves a specific purpose:

#### **Backfiller** (`apps/backfiller/`) ✅

- **Purpose**: Collect and maintain historical market data
- **Status**: Fully implemented and working
- **Features**:
  - Intelligent backward pagination from present to earliest available data
  - Automatic gap detection and filling
  - Unfillable gap tracking (exchange outages)
  - Resume support (fetches only new data on subsequent runs)
  - Multi-symbol/timeframe support
- **Data Source**: CCXT REST API
- **Entry Point**: `apps/backfiller/main.py`

#### **Backtester** (`apps/backtester/`) 📋

- **Purpose**: Simulate trades using historical data
- **Status**: Planned - stub only
- **Data Source**: SQLite database (populated by backfiller)
- **Will Use**: Strategy logic from `packages/strategies/`

#### **Trader** (`apps/trader/`) 📋

- **Purpose**: Execute live trades with real money
- **Status**: Planned - stub only
- **Data Source**: WebSocket streams (real-time) + REST API (historical warmup)
- **Will Use**: Same strategy logic as backtester for consistency

### Packages (`packages/`)

Reusable, modular components shared across all applications:

#### **Database** (`packages/database/`) ✅

- SQLite connection management with WAL mode
- Query helpers for OHLCV data, gaps, and metadata
- Concurrent read/write support
- Used by: backfiller (write), backtester/trader (read)

#### **Logging** (`packages/logging/`) ✅

- Structured logging with timestamps
- File output (`logs/`) and console output
- Module-level loggers
- Used by: all applications

#### **WebSocket** (`packages/websocket/`) ✅

- **Real-time market data streaming** via CCXT Pro
- **OHLCV updates**: 1m candles forming in real-time
- **Ticker updates**: Best bid/ask prices, volume
- **Order Book depth**: Top 10 bid/ask levels with liquidity
- **Trade stream**: Individual trades for order flow analysis
- Stores in same database tables as REST data (unified layer)
- Used by: live trader for sub-second updates
- Documentation: `docs/WEBSOCKET.md`, `docs/ORDERBOOK.md`

#### **Indicators** (`packages/indicators/`) 📋

- Technical indicators for strategy signals
- Currently: RSI stub only
- Planned: MACD, Bollinger Bands, moving averages, etc.
- Will support conventional and ML-based indicators

#### **Core** (`packages/core/`) 📋

- Central orchestration logic (planned)
- Will coordinate packages
- Strategy execution engine

#### **Exchange** (`packages/exchange/`) 📋

- Exchange abstraction layer (planned)
- Will provide unified interface via CCXT
- Support for 100+ exchanges

#### **Execution** (`packages/execution/`) 📋

- Order placement and management (planned)
- Will handle order lifecycle
- Position tracking

### Configuration (`config/`)

#### **Settings** (`config/settings.py`) ✅

- Application configuration
- Database paths, logging levels
- Used by all applications

#### **Exchange Config** (`config/exchanges.py`) ✅

- Exchange credentials management
- Loads API keys from `.env`
- Validates required credentials

#### **Strategy Configs** (`config/strategies/`) ✅

- YAML-based strategy definitions
- Examples: `btc_usdt_mexc_1m.yaml`, `eth_usdt_mexc_15m.yaml`
- Define: exchange, symbol, timeframe, indicators, entry/exit rules
- Will be used by backtester and trader

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- [UV](https://github.com/astral-sh/uv) package manager
- Exchange API keys (optional for public data)

### Setup

1. **Install Dependencies**

   ```bash
   cd simple-bot
   uv sync
   ```

2. **Configure Environment** (optional, for authenticated access)

   ```bash
   cp .env.example .env
   nano .env  # Add your API keys
   ```

3. **Initialize Database**

   ```bash
   uv run python schema.py
   ```

### Current Usage

#### Collect Historical Data

**Single symbol/timeframe:**

```bash
# Backfill specific data
uv run python -m apps.backfiller.main --symbol BTC/USDT --timeframe 1h

# With specific exchange
uv run python -m apps.backfiller.main --symbol ETH/USDT --timeframe 15m --exchange binance
```

**Multiple symbols/timeframes:**

```bash
# Run automated population script
uv run python scripts/populate_db.py

# This will backfill:
# - 5 symbols: BTC, ETH, BNB, SOL, XRP (all vs USDT)
# - 6 timeframes: 1m, 5m, 15m, 1h, 4h, 1d
# - All available history from MEXC
```

**Check database:**

```bash
ls -lh data/trading.db
sqlite3 data/trading.db "SELECT COUNT(*) FROM ohlcv_data;"
```

#### Test WebSocket Streaming

**Real-time market data:**

```bash
# Stream OHLCV, ticker, order book, and trades for 30 seconds
uv run python scripts/test_websocket.py

# Shows:
# - Live candle updates
# - Price movements
# - Order book depth (10 levels)
# - Individual trade flow
```

**Check captured data:**

```bash
sqlite3 data/trading.db "SELECT COUNT(*) FROM orderbook_data;"
sqlite3 data/trading.db "SELECT COUNT(*) FROM trades_stream;"
```

### Future Usage (When Implemented)

**Backtesting:**

```bash
uv run python -m apps.backtester.main --config config/strategies/btc_usdt_mexc_1h.yaml
```

**Live Trading:**

```bash
uv run python -m apps.trader.main --config config/strategies/btc_usdt_mexc_1h.yaml
```

## ⚙️ Configuration

### Environment Variables (`.env`)

API credentials for exchanges (optional for public data):

```bash
# Exchange API Keys
MEXC_API_KEY=your_key
MEXC_API_SECRET=your_secret

BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret

# System Settings
DATABASE_PATH=data/trading.db
LOG_LEVEL=INFO
```

### Strategy Configuration (YAML)

Strategy configs define trading parameters. Example from `config/strategies/btc_usdt_mexc_1h.yaml`:

```yaml
strategy:
  name: "BTC 1H Strategy"
  exchange: mexc
  symbol: BTC/USDT
  timeframe: 1h

indicators:
  rsi:
    period: 14
    overbought: 70
    oversold: 30

entry:
  long:
    - rsi < 30
  short:
    - rsi > 70

exit:
  take_profit_pct: 2.0
  stop_loss_pct: 1.0

risk:
  position_size_usd: 100
  max_positions: 3
```

### Supported Exchanges

All exchanges supported by [CCXT](https://github.com/ccxt/ccxt) work (100+ exchanges):

- Binance, Coinbase, Kraken, Bybit, OKX, MEXC, KuCoin, and many more

### Supported Timeframes

- Minutes: `1m`, `5m`, `15m`, `30m`
- Hours: `1h`, `2h`, `4h`, `6h`, `12h`
- Days: `1d`, `3d`
- Weeks: `1w`
- Months: `1M`

## 📊 Database

### Schema

See [docs/DATABASE.md](docs/DATABASE.md) for complete details.

**Current tables:**

- `ohlcv_data` - Historical price data (shared across all strategies)
- `ticker_data` - Real-time ticker updates
- `orderbook_data` - Order book depth snapshots (10 levels)
- `trades_stream` - Individual trade executions
- `strategy_metadata` - Strategy configurations
- `trades` - Executed trades (per strategy)
- `positions` - Current positions (per strategy)
- `signals` - Trading signals (per strategy)
- `indicator_cache` - Cached indicator calculations
- `unfillable_gaps` - Tracked gaps from exchange outages

**Key features:**

- WAL mode for concurrent read/write
- Composite keys for efficient querying
- ~218 MB with 1M+ candles across 30 symbol/timeframe combinations

## 📚 Documentation

Comprehensive documentation in [`docs/`](docs/):

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture and design
- **[DATABASE.md](docs/DATABASE.md)** - Database schema and strategy
- **[WEBSOCKET.md](docs/WEBSOCKET.md)** - WebSocket integration for real-time data
- **[ORDERBOOK.md](docs/ORDERBOOK.md)** - Order book and trade streaming guide
- **[DATA_STRATEGY.md](docs/DATA_STRATEGY.md)** - Multi-instance data storage approach
- **[DATA_FLOW.md](docs/DATA_FLOW.md)** - REST vs WebSocket data flow
- **[QUICKSTART.md](docs/QUICKSTART.md)** - Quick command reference

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

## 🛠️ Development

### Adding Dependencies

```bash
# Production
uv add pandas numpy ta-lib

# Development
uv add --dev pytest black ruff mypy
```

### Code Quality

```bash
# Format code
uv run black apps/ packages/ config/

# Type checking
uv run mypy apps/ packages/

# Linting
uv run ruff check apps/ packages/
```

## 🐛 Troubleshooting

### Common Issues

**Import Errors**

- Run from project root: `uv run python -m apps.backfiller.main`
- Check package imports use correct paths

**Exchange Errors**

- Verify exchange name matches CCXT (case-sensitive)
- Check API keys if using authenticated endpoints
- Some exchanges require API keys even for public data

**Database Issues**

- Ensure `data/` directory exists and is writable
- Check disk space if database is growing
- WAL mode handles concurrent access automatically

**Backfiller Stuck**

- Check logs in `logs/` directory
- Verify network connectivity
- Some exchanges have rate limits even for public data

## ⚠️ Safety & Best Practices

**When live trading is implemented:**

- ⚠️ **Test Thoroughly** - Always backtest strategies first
- 💰 **Start Small** - Use minimal capital initially
- 📄 **Paper Trade** - Verify with simulated trades before real money
- 🛡️ **Risk Management** - Implement stop-losses and position limits
- 👀 **Monitor Actively** - Check logs regularly
- 🔐 **Secure Credentials** - Never commit API keys to git
- ⏱️ **Respect Rate Limits** - Avoid exchange bans
- 📊 **Log Everything** - Maintain audit trail of all actions

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
