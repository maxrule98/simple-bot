# Trading Bot - Enterprise-Grade Architecture

A professional cryptocurrency trading bot with a clean, enterprise-grade architecture. Features separate applications for live trading, backtesting, and data management, with a modular package system for indicators, exchanges, and execution logic.

## Features

- 📊 **Multi-pair monitoring** - Scan multiple trading pairs simultaneously
- 💾 **SQLite database** - Persistent storage for price history and signals
- 📈 **Pluggable strategies** - Easy-to-extend strategy framework
- 🔄 **CCXT integration** - Access to 100+ cryptocurrency exchanges
- ⚡ **UV package management** - Fast dependency management
- 🧩 **Modular design** - Clean separation of concerns

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

- Python 3.12+
- [UV](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# Clone the repository
cd simple-bot

# Install dependencies
uv sync
```

### Running the Applications

#### Live Trading

```bash
uv run python apps/trader/main.py
```

#### Backtesting

```bash
uv run python apps/backtester/main.py
```

#### Data Backfilling

```bash
uv run python apps/backfiller/main.py
```

## ⚙️ Configuration

### Strategy Configuration (YAML)

Define strategies declaratively using YAML files in `config/strategies/`:

```yaml
# config/strategies/my_strategy.yaml
strategy:
  name: "my_custom_strategy"
  timeframe: "1h"
  pairs:
    - "BTC/USDT"
    - "ETH/USDT"
  indicators:
    - type: "RSI"
      period: 14
    - type: "MACD"
      fast: 12
      slow: 26
  signals:
    buy_threshold: 30
    sell_threshold: 70
```

### Main Configuration (`config/config.py`)

Central configuration for the entire application:

- Exchange credentials and settings
- Database connections
- API rate limits
- Logging levels
- Environment-specific settings

### Dynamic Exchange Switching

The `packages/exchange/` module allows runtime exchange switching:

- Binance
- Kraken
- Coinbase
- Bybit
- And 100+ others via CCXT

### Dynamic Timeframe Management

The `packages/timeframes/` module provides flexible timeframe handling:

- 1m, 5m, 15m, 30m
- 1h, 2h, 4h, 6h, 12h
- 1d, 3d, 1w, 1M
- Custom timeframes

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

```
packages/indicators/conventional/[indicator_name]/
├── main.py      # Indicator implementation
└── utils/       # Helper functions
```

### Machine Learning Indicators (`packages/indicators/ML/`)

Advanced ML-based indicators and forecasting:

- **ARIMA** (AutoRegressive Integrated Moving Average) - `ML/ARIMA/`
- **LSTM** (Long Short-Term Memory networks)
- **Random Forest** classifiers
- **Gradient Boosting** models
- **Neural Network** predictions

Each ML indicator follows the structure:

```
packages/indicators/ML/[model_name]/
├── main.py      # Model implementation
└── utils/       # Training, evaluation utilities
```

### Adding New Indicators

1. Create a new folder in `conventional/` or `ML/`
2. Add `main.py` with indicator logic
3. Add `utils/` folder for helper functions
4. Register in `packages/indicators/main.py`

## 🔄 Workflow

### Development Workflow

1. **Backfill Historical Data**

   ```bash
   uv run python apps/backfiller/main.py
   ```

   Populate database with historical OHLCV data

2. **Backtest Strategies**

   ```bash
   uv run python apps/backtester/main.py
   ```

   Test strategies against historical data

3. **Optimize and Refine**
   - Adjust strategy parameters in `config/strategies/`
   - Test different indicators
   - Tune entry/exit conditions

4. **Paper Trade**
   - Test with live data but no real orders
   - Verify strategy behavior in real-time

5. **Go Live**
   ```bash
   uv run python apps/trader/main.py
   ```
   Execute real trades with real money

### Consistency Between Backtesting and Live Trading

The architecture ensures that backtesting and live trading share the same code:

- Both use packages from `packages/`
- Same strategy logic
- Same execution engine
- Same indicator calculations

This eliminates discrepancies between simulated and real performance.

## 🧪 Development

### Adding Dependencies

```bash
# Production dependencies
uv add pandas numpy ta-lib

# Development dependencies
uv add --dev pytest black ruff mypy
```

### Code Quality

```bash
# Format code
uv run black apps/ packages/ config/

# Lint
uv run ruff check apps/ packages/ config/

# Type check
uv run mypy apps/ packages/ config/
```

### Testing

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=packages --cov=apps
```

## 🔧 Key Design Principles

### Modularity

- **Packages** are self-contained and reusable
- Each indicator, exchange, and timeframe is independent
- Easy to add new components without modifying existing code

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
