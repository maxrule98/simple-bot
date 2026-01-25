# Copilot Instructions for AI Contributors

This document provides essential context and guidelines for AI assistants working on this trading bot codebase.

## 🎯 Project Philosophy

### Core Principles

1. **Zero Hardcoding** - Everything is dynamic and configurable
   - No hardcoded exchanges, symbols, timeframes, or strategies in code
   - All configuration via YAML files and environment variables
   - Code should work with ANY exchange, symbol, or timeframe

2. **Complete Modularity** - Clean separation of concerns
   - Each package has a single, well-defined responsibility
   - Packages are reusable across all applications
   - Applications orchestrate packages, don't duplicate logic

3. **Docker-First Deployment** - Horizontal scaling by design
   - Each container runs one trading strategy instance
   - Shared SQLite database across all containers (mounted volume)
   - Containers are stateless; state lives in database and config

4. **Data Layer Unification** - REST and WebSocket use same tables
   - Historical data via REST API → SQLite
   - Real-time data via WebSocket → Same SQLite tables
   - Strategies don't care about data source

## 📁 Project Structure

```
simple-bot/
├── apps/                    # Standalone executables (entry points)
│   ├── trader/             # Live trading with real money
│   ├── backtester/         # Historical strategy simulation
│   └── backfiller/         # Historical data collection
│
├── packages/               # Reusable modules (shared libraries)
│   ├── core/              # Central orchestration
│   ├── exchange/          # CCXT exchange abstraction (REST)
│   ├── websocket/         # CCXT Pro WebSocket streaming
│   ├── execution/         # Order placement and management
│   ├── timeframes/        # Dynamic timeframe handling
│   ├── indicators/        # Technical indicators
│   │   ├── conventional/  # RSI, MACD, Bollinger Bands, etc.
│   │   └── ML/           # ARIMA, LSTM, ML-based indicators
│   ├── database/          # Database connection and queries
│   ├── logging/           # Structured logging
│   ├── config/            # Configuration loading
│   └── strategies/        # Strategy execution engine
│
├── config/                # Configuration files
│   ├── config.py         # Main config module
│   └── strategies/       # YAML strategy definitions
│
├── docs/                 # Comprehensive documentation
│   ├── ARCHITECTURE.md   # Architecture diagrams
│   ├── DATABASE.md       # Database schema and strategy
│   ├── WEBSOCKET.md      # WebSocket integration guide
│   ├── DATA_STRATEGY.md  # Multi-instance data storage
│   ├── DATA_FLOW.md      # REST vs WebSocket comparison
│   ├── DATA_SUMMARY.md   # Data best practices
│   ├── QUICKSTART.md     # Quick reference
│   └── AUDIT.md          # Pre-implementation audit
│
├── data/                 # Database storage (Docker volume)
│   └── trading.db       # SQLite database
│
├── logs/                 # Application logs (Docker volume)
│
├── schema.py            # Database initialization script
├── pyproject.toml       # Python dependencies
├── Dockerfile           # Container image definition
└── docker-compose.yml   # Multi-container orchestration
```

## 🗄️ Database Schema

**Location**: `schema.py`

**Strategy**: One SQLite database, shared across all containers

### Tables

1. **ohlcv_data** - Market OHLCV data (shared)
   - Key: `(exchange, symbol, timeframe, timestamp)`
   - Stores: open, high, low, close, volume
   - Used by: ALL applications

2. **ticker_data** - Real-time ticker updates (shared)
   - Key: `(exchange, symbol, timestamp)`
   - Stores: bid, ask, last, volume

3. **strategy_metadata** - Strategy configurations
   - Key: `strategy_id`
   - Stores: name, exchange, symbol, timeframe, config JSON

4. **trades** - Executed trades (isolated by strategy_id)
   - Foreign key: `strategy_id`
   - Stores: order details, PNL, timestamps

5. **positions** - Current positions (isolated by strategy_id)
   - Foreign key: `strategy_id`
   - Stores: entry price, quantity, unrealized PNL

6. **signals** - Trading signals (isolated by strategy_id)
   - Foreign key: `strategy_id`
   - Stores: signal type, strength, metadata

7. **indicator_cache** - Computed indicator values
   - Key: `(exchange, symbol, timeframe, indicator_name, timestamp)`
   - Stores: cached indicator calculations

### Data Isolation Strategy

- **Market Data (OHLCV/Ticker)**: Shared across all strategies
  - No duplication when multiple strategies use same pair
  - Composite key ensures uniqueness

- **Trade Data (Trades/Positions/Signals)**: Isolated by `strategy_id`
  - Each container has unique `strategy_id`
  - No conflicts between instances

### Concurrency

- **WAL Mode**: Enabled for concurrent reads + writes
- **Write Strategy**:
  - Historical data: `INSERT OR IGNORE` (immutable)
  - Real-time data: `INSERT OR REPLACE` (updates forming candles)

## 🔌 Data Sources

### REST API (Historical Data)

- **Package**: `packages/exchange/`
- **Library**: CCXT (v4.4.42+)
- **Use Cases**: Backtesting, historical warmup, data backfilling
- **Data Flow**: Exchange REST → CCXT → Database → Strategy

### WebSocket (Real-Time Data)

- **Package**: `packages/websocket/`
- **Library**: CCXT Pro (optional dependency)
- **Use Cases**: Live trading, real-time signals
- **Data Flow**: Exchange WS → CCXT Pro → Database → Strategy
- **Storage**: Same tables as REST data (unified layer)

## 🐳 Docker Deployment

### Multi-Instance Pattern

Each container runs one strategy instance:

```yaml
trader-btc-binance-1h:
  environment:
    STRATEGY_CONFIG: btc_binance_1h.yaml
    STRATEGY_ID: btc-binance-1h
```

### Shared Resources

- **Database**: Mounted volume `/app/data/trading.db`
- **Logs**: Mounted volume `/app/logs/`
- **Secrets**: Shared `.env` file (API keys)

### Service Types

1. **Trader**: Live trading (apps/trader/main.py)
2. **Backtester**: Historical simulation (apps/backtester/main.py)
3. **Backfiller**: Data collection (apps/backfiller/main.py)

## 🎨 Code Conventions

### File Naming

- Packages: snake_case (`packages/exchange/main.py`)
- Classes: PascalCase (`class ExchangeManager`)
- Functions: snake_case (`def fetch_ohlcv()`)
- Constants: UPPER_CASE (`MAX_RETRIES = 3`)

### Package Structure

Each package follows this structure:

```
packages/example/
├── __init__.py          # Package exports
├── main.py              # Primary logic/classes
└── utils/               # Helper functions
    ├── __init__.py
    └── helpers.py
```

### Import Conventions

```python
# Standard library
import os
import sys
from datetime import datetime

# Third-party
import ccxt
import pandas as pd

# Local packages
from packages.database.db import DatabaseManager
from packages.logging.logger import setup_logger
```

### Error Handling

```python
try:
    result = exchange.fetch_ohlcv(symbol, timeframe)
except ccxt.NetworkError as e:
    logger.error(f"Network error: {e}")
except ccxt.ExchangeError as e:
    logger.error(f"Exchange error: {e}")
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
```

### Logging

```python
from packages.logging.logger import setup_logger

logger = setup_logger(__name__)
logger.info("Starting backfill process")
logger.warning("Rate limit approaching")
logger.error("Failed to fetch data", exc_info=True)
```

## 📝 Adding New Features

### New Indicator

1. Create folder: `packages/indicators/conventional/my_indicator/`
2. Add `main.py` with indicator logic
3. Add `utils/` folder for helpers if needed
4. Register in `packages/indicators/main.py`
5. Document in `packages/indicators/README.md`

Example structure:

```python
# packages/indicators/conventional/my_indicator/main.py
def calculate_my_indicator(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate MY indicator."""
    # Implementation
    return result
```

### New Strategy

1. Create YAML: `config/strategies/my_strategy.yaml`
2. Define parameters:

   ```yaml
   strategy:
     name: "My Strategy"
     exchange: "binance"
     symbol: "BTC/USDT"
     timeframe: "1h"

   indicators:
     - name: "RSI"
       params:
         period: 14

   entry:
     conditions:
       - "RSI < 30"

   exit:
     conditions:
       - "RSI > 70"
   ```

3. Add to `docker-compose.yml`:
   ```yaml
   trader-my-strategy:
     environment:
       STRATEGY_CONFIG: my_strategy.yaml
       STRATEGY_ID: my-strategy-001
   ```

### New Exchange Support

CCXT supports 100+ exchanges automatically. Just configure in YAML:

```yaml
strategy:
  exchange: "kraken" # or "coinbase", "kucoin", etc.
```

No code changes needed!

### New Application

1. Create folder: `apps/my_app/`
2. Add `main.py` entry point
3. Import and use packages from `packages/`
4. Add to `docker-compose.yml` if needed
5. Document in README.md

## 🧪 Testing Strategy

### Unit Tests

- Test individual functions in isolation
- Mock external dependencies (exchanges, database)
- Location: `tests/unit/`

### Integration Tests

- Test package interactions
- Use test database
- Location: `tests/integration/`

### Backtests

- Strategy validation using historical data
- Run via `apps/backtester/main.py`
- Compare against benchmarks

## 📚 Documentation Standards

### Docstrings

```python
def fetch_market_data(exchange: str, symbol: str, timeframe: str, since: int) -> pd.DataFrame:
    """
    Fetch OHLCV data from exchange.

    Args:
        exchange: Exchange name (e.g., 'binance')
        symbol: Trading pair (e.g., 'BTC/USDT')
        timeframe: Candle timeframe (e.g., '1h')
        since: Start timestamp in milliseconds

    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume

    Raises:
        ExchangeError: If exchange API fails
        NetworkError: If network connection fails
    """
    # Implementation
```

### README Updates

When adding significant features:

1. Update main README.md
2. Add/update relevant docs/ file
3. Update QUICKSTART.md if it affects usage
4. Document in package-level README if applicable

## 🚨 Important Constraints

### What NOT to Do

❌ **Don't hardcode exchanges**

```python
# BAD
if exchange == "binance":
    # binance-specific code
```

✅ **Use CCXT abstraction**

```python
# GOOD
exchange_instance = getattr(ccxt, exchange_name)()
```

❌ **Don't hardcode symbols/timeframes**

```python
# BAD
symbol = "BTC/USDT"
timeframe = "1h"
```

✅ **Load from config**

```python
# GOOD
symbol = config['strategy']['symbol']
timeframe = config['strategy']['timeframe']
```

❌ **Don't duplicate logic between apps**

```python
# BAD - same code in trader and backtester
```

✅ **Extract to shared package**

```python
# GOOD - in packages/strategies/
```

## 🔍 Quick Reference

### Common Operations

**Initialize Database**:

```bash
python schema.py
```

**Build Docker Images**:

```bash
docker compose build
```

**Start All Containers**:

```bash
docker compose up -d
```

**View Logs**:

```bash
docker compose logs -f trader-btc-binance-1h
```

**Run Backtest**:

```bash
docker compose run backtester
```

### Key Files to Understand

1. **schema.py** - Database structure
2. **docker-compose.yml** - Deployment configuration
3. **docs/DATABASE.md** - Data architecture deep dive
4. **docs/WEBSOCKET.md** - Real-time data integration
5. **packages/websocket/websocket.py** - WebSocket implementation

### Environment Variables

Set in `.env`:

```bash
# Exchange API Keys (shared across containers)
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
COINBASE_API_KEY=your_key
COINBASE_API_SECRET=your_secret

# Database
DATABASE_PATH=/app/data/trading.db

# Logging
LOG_LEVEL=INFO
```

Set per-container in `docker-compose.yml`:

```yaml
STRATEGY_CONFIG: btc_binance_1h.yaml
STRATEGY_ID: btc-binance-1h
EXCHANGE: binance
SYMBOL: BTC/USDT
TIMEFRAME: 1h
```

## 🎯 Current Implementation Status

### ✅ Complete

- Database schema (7 tables, 13 indexes)
- WebSocket package (CCXT Pro integration)
- Docker infrastructure (Dockerfile + compose)
- Comprehensive documentation (8 docs files)
- Project structure (all folders and **init**.py)

### 🚧 Pending Implementation

- Core package (`packages/core/main.py`)
- Database package (`packages/database/db.py`)
- Exchange package (`packages/exchange/main.py`)
- Execution package (`packages/execution/main.py`)
- Indicators (RSI, MACD, etc.)
- Strategy engine (`packages/strategies/`)
- Application entry points (trader, backtester, backfiller)
- Logging setup (`packages/logging/logger.py`)

### 📦 Required Dependencies (to be added)

- sqlalchemy or aiosqlite (database ORM/async)
- pandas (data manipulation)
- numpy (numerical operations)
- pyyaml (YAML config loading)
- python-dotenv (environment variables)

## 💡 AI Assistant Tips

1. **Always check docs/** before implementing
   - DATABASE.md for data questions
   - WEBSOCKET.md for real-time data
   - ARCHITECTURE.md for design patterns

2. **Follow the modular pattern**
   - Apps orchestrate, packages implement
   - No business logic in apps

3. **Maintain configurability**
   - Never assume an exchange or symbol
   - Always use config/environment variables

4. **Test with multiple scenarios**
   - Different exchanges (Binance, Coinbase, Kraken)
   - Different symbols (BTC/USDT, ETH/USDT, etc.)
   - Different timeframes (1m, 15m, 1h, 1d)

5. **Document as you go**
   - Docstrings for all public functions
   - Update README for significant changes
   - Add examples in docs/ if introducing new patterns

## 📞 Getting Help

- Review [docs/QUICKSTART.md](docs/QUICKSTART.md) for common commands
- Check [docs/AUDIT.md](docs/AUDIT.md) for architecture review
- See [docs/DATABASE.md](docs/DATABASE.md) for schema questions
- Refer to [docs/WEBSOCKET.md](docs/WEBSOCKET.md) for real-time data

---

**Remember**: This is a dynamic, modular, Docker-first trading bot. Keep it that way! 🚀
