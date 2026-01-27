# Simple Trading Bot

A fully modular, configuration-driven cryptocurrency trading bot with advanced ML integration, real-time data streaming, and institutional-grade features.

## 🎯 Project Vision

Build a **production-ready trading system** that is:

- **100% Dynamic** - Zero hardcoding of exchanges, symbols, timeframes, or strategies
- **Modular** - Clean separation between data collection, strategy execution, and order management
- **Scalable** - Run unlimited trading instances in parallel via Docker
- **ML-Ready** - First-class support for machine learning models and complex signal aggregation
- **Institutional-Grade** - True VWAP, real-time WebSocket streaming, sophisticated exit management

## 🚀 Current Status

### ✅ Completed Features

**Data Infrastructure:**

- ✅ SQLite database with WAL mode (concurrent read/write)
- ✅ Historical data backfilling via REST API (intelligent pagination, gap detection)
- ✅ Real-time WebSocket streaming (OHLCV, ticker, order book depth, trades)
- ✅ Unified data layer (REST and WebSocket use same tables)
- ✅ Multi-timeframe support (1m to 1M)
- ✅ 100+ exchange support via CCXT

**Monitoring & Visualization:**

- ✅ Grafana + Prometheus architecture designed (sub-second dashboard updates)
- ✅ Order book depth chart visualization (20 levels, cumulative quantities)
- ✅ Live metrics + historical data integration

**Architecture & Documentation:**

- ✅ Complete trader architecture designed (see [TRADER_ARCHITECTURE.md](docs/TRADER_ARCHITECTURE.md))
- ✅ Strategy plugin system designed
- ✅ Complex signal aggregation framework (technical + ML + order book)
- ✅ ML training pipeline designed (rolling window, continuous learning)
- ✅ True VWAP calculation using trades stream

### 🚧 In Progress / Next Steps

**Priority 1: Core Trading Runtime**

1. Implement `packages/execution/manager.py` - Order execution and management
2. Implement `packages/strategies/base.py` - Base strategy class with signal framework
3. Implement `packages/strategies/loader.py` - Dynamic strategy loading from YAML
4. Build `apps/trader/runtime.py` - Core trading loop (WebSocket → Strategy → Execution)
5. Implement signal generators: Technical, ML, OrderBook
6. Implement signal aggregator (voting, weighted, unanimous modes)
7. Build exit manager (tiered TP, trailing stops, time-based, ML-based)

**Priority 2: Example Strategies**

1. RSI mean reversion (simple technical)
2. Multi-timeframe confirmation strategy
3. Complex ML strategy (technical + ML + order book signals)
4. True VWAP mean reversion strategy

**Priority 3: ML Pipeline**

1. Implement `packages/ml/data_loader.py` - Rolling window data loading
2. Implement `packages/ml/feature_engineering.py` - Technical features + VWAP features
3. Implement `packages/ml/models/lstm.py` - LSTM model training
4. Implement `packages/ml/evaluation.py` - Backtesting and metrics
5. Implement `packages/ml/deployment.py` - Model versioning and hot-swap
6. Build continuous training service (daily retraining on rolling window)

**Priority 4: Monitoring**

1. Implement Prometheus metrics in WebSocket package
2. Create Grafana dashboard JSON
3. Set up Docker Compose with Prometheus + Pushgateway + Grafana

**Priority 5: Testing & Deployment**

1. Test strategies in paper mode (MEXC sandbox)
2. Implement backtester (historical strategy validation)
3. Deploy to production (live mode with real capital)

## 📁 Project Structure

```
simple-bot/
├── apps/                         # Standalone applications (entry points)
│   ├── backfiller/               # ✅ Historical data collection
│   │   └── main.py               # Intelligent backfill with pagination & gap detection
│   ├── backtester/               # 🚧 Strategy backtesting (planned)
│   │   └── main.py               # Historical simulation with same strategy code
│   └── trader/                   # 🚧 Live/Paper trading (in progress)
│       ├── main.py               # Entry point
│       └── runtime.py            # Trading loop: WebSocket → Strategy → Execution
│
├── packages/                     # Reusable modules (shared libraries)
│   ├── database/                 # ✅ Database management
│   │   └── db.py                 # SQLite with WAL mode, query helpers
│   │
│   ├── logging/                  # ✅ Structured logging
│   │   └── logger.py             # File + console output
│   │
│   ├── websocket/                # ✅ Real-time streaming
│   │   └── websocket.py          # CCXT Pro: OHLCV, ticker, orderbook, trades
│   │
│   ├── execution/                # 🚧 Order execution (priority 1)
│   │   └── manager.py            # Order placement, fills, position tracking
│   │
│   ├── strategies/               # 🚧 Strategy engine (priority 1)
│   │   ├── base.py               # BaseStrategy class with signal framework
│   │   ├── loader.py             # Dynamic YAML-based strategy loading
│   │   ├── conventional/         # Pre-built strategies
│   │   │   ├── rsi_mean_reversion.py
│   │   │   ├── multi_timeframe.py
│   │   │   ├── complex_ml_strategy.py
│   │   │   └── vwap_strategy.py
│   │   └── custom/               # User-defined strategies
│   │
│   ├── signals/                  # 🚧 Signal generation (priority 1)
│   │   ├── types.py              # Signal, SignalType, SignalSource enums
│   │   ├── aggregator.py         # Voting, weighted, unanimous aggregation
│   │   ├── generators/
│   │   │   ├── technical.py      # RSI, MACD, Bollinger Bands signals
│   │   │   ├── ml.py             # ML model predictions
│   │   │   └── orderbook.py      # Order book imbalance signals
│   │   └── exits/
│   │       └── manager.py        # Tiered TP, trailing stops, time-based
│   │
│   ├── indicators/               # 🚧 Technical indicators (priority 2)
│   │   ├── conventional/         # RSI, MACD, BB, SMA, EMA, True VWAP
│   │   │   ├── rsi/
│   │   │   ├── macd/
│   │   │   ├── bollinger_bands/
│   │   │   └── vwap_true/        # True VWAP from trades stream
│   │   └── ml/                   # ARIMA, LSTM, ML-based indicators
│   │
│   ├── ml/                       # 🚧 Machine learning (priority 3)
│   │   ├── data_loader.py        # Rolling window data loading
│   │   ├── feature_engineering.py # Technical features + VWAP + lags
│   │   ├── models/
│   │   │   ├── lstm.py           # LSTM model
│   │   │   ├── random_forest.py
│   │   │   └── xgboost.py
│   │   ├── evaluation.py         # Backtest metrics, profit factor
│   │   └── deployment.py         # Model versioning, hot-swap
│   │
│   ├── prometheus/               # 🚧 Metrics (priority 4)
│   │   └── metrics.py            # Push metrics to Prometheus
│   │
│   ├── exchange/                 # 📋 Exchange abstraction (future)
│   │   └── exchange.py           # CCXT wrapper
│   │
│   └── core/                     # 📋 Core orchestration (future)
│       └── core.py               # Central coordination
│
├── config/                       # Configuration files
│   ├── settings.py               # ✅ App settings
│   ├── exchanges.py              # ✅ Exchange credentials
│   ├── strategies/               # ✅ Strategy YAML files
│   │   ├── btc_usdt_mexc_1m.yaml
│   │   ├── btc_ml_strategy.yaml  # Complex ML strategy config
│   │   └── btc_vwap_strategy.yaml # True VWAP mean reversion
│   └── ml/                       # 🚧 ML training configs
│       └── btc_lstm_config.yaml  # LSTM training parameters
│
├── scripts/                      # Utility scripts
│   ├── populate_db.py            # ✅ Multi-symbol backfill automation
│   ├── test_websocket.py         # ✅ WebSocket testing (30 sec validation)
│   ├── train_model.py            # 🚧 ML model training script
│   └── continuous_training.py    # 🚧 Continuous learning service
│
├── models/                       # ML model storage
│   ├── btc_lstm_v1.pkl           # Trained LSTM model
│   ├── feature_pipeline.pkl      # Feature engineering pipeline
│   └── metadata/                 # Model performance tracking
│
├── data/                         # Generated data (gitignored)
│   └── trading.db                # SQLite database (~218 MB)
│
├── logs/                         # Application logs (gitignored)
│   ├── backfiller.log
│   ├── trader.log
│   └── ml_training.log
│
├── docs/                         # Comprehensive documentation
│   ├── TRADER_ARCHITECTURE.md    # 🎯 Complete architecture design
│   ├── GRAFANA_PROMETHEUS.md     # Dashboard + monitoring setup
│   ├── DATABASE.md               # Database schema details
│   ├── WEBSOCKET.md              # WebSocket integration guide
│   ├── ORDERBOOK.md              # Order book & trade streaming
│   ├── ARCHITECTURE.md           # System architecture diagrams
│   ├── DATA_STRATEGY.md          # Multi-instance data storage
│   ├── DATA_FLOW.md              # REST vs WebSocket comparison
│   ├── DATA_SUMMARY.md           # Data handling best practices
│   ├── QUICKSTART.md             # Quick command reference
│   └── AUDIT.md                  # Pre-implementation audit
│
├── schema.py                     # ✅ Database initialization
├── pyproject.toml                # ✅ Dependencies (uv)
├── Dockerfile                    # 🚧 Container image
├── docker-compose.yml            # 🚧 Multi-container orchestration
└── README.md                     # This file
```

## 🏗️ Architecture Overview

### Core Design Principles

1. **Zero Hardcoding** - All configuration via YAML and environment variables
2. **Complete Modularity** - Clean separation of concerns, reusable packages
3. **Docker-First** - Horizontal scaling, each container = one strategy instance
4. **Data Layer Unification** - REST and WebSocket use same SQLite tables
5. **Strategy Plugin System** - Add strategies without modifying core code
6. **ML-First Design** - Machine learning as a first-class citizen

### Runtime Modes

**Live Trading** (`TRADING_MODE=live`)

- Real money, production exchange
- Uses `exchange.set_sandbox_mode(False)`
- WebSocket for real-time data
- Prometheus metrics pushed every 1 second

**Paper Trading** (`TRADING_MODE=paper`)

- Simulated orders, production data
- Uses `exchange.set_sandbox_mode(True)` (MEXC sandbox)
- Same code as live, different execution environment
- Test strategies before risking capital

**Backtesting** (`apps/backtester/`)

- Historical replay, no real-time data
- Reads from database (populated by backfiller)
- Same strategy code ensures consistency
- Validate before paper/live trading

### Applications (`apps/`)

#### **Backfiller** ✅ (Fully Implemented)

**Purpose**: Collect and maintain historical market data

**Features**:

- Intelligent backward pagination (present → earliest available)
- Automatic gap detection and filling
- Unfillable gap tracking (exchange outages)
- Resume support (only fetches new data)
- Multi-symbol/timeframe support

**Data Source**: CCXT REST API  
**Entry Point**: `apps/backfiller/main.py`

**Usage**:

```bash
# Single symbol
uv run python -m apps.backfiller.main --symbol BTC/USDT --timeframe 1h

# Multi-symbol automation
uv run python scripts/populate_db.py
```

#### **Trader** 🚧 (In Progress - Priority 1)

**Purpose**: Execute live/paper trades with real money or simulated orders

**Architecture**:

```
WebSocket Stream → Strategy (generates signals) → Execution (places orders) → Prometheus
```

**Components**:

1. **Runtime Loop** (`apps/trader/runtime.py`)
   - Subscribes to WebSocket streams (OHLCV, ticker, orderbook, trades)
   - Processes candles through strategy
   - Executes signals via execution manager
   - Publishes metrics to Prometheus

2. **Strategy Plugin** (loaded from YAML)
   - Generates signals from multiple sources (technical, ML, orderbook)
   - Aggregates signals with confidence voting
   - Returns buy/sell/close/partial_close signals

3. **Execution Manager** (`packages/execution/manager.py`)
   - Places orders via CCXT
   - Tracks fills and positions
   - Handles live vs paper mode switching

**Data Sources**:

- WebSocket (real-time): OHLCV, ticker, orderbook, trades
- Database (historical warmup): Last N candles for indicator calculation

**Entry Point**: `apps/trader/main.py`

**Usage** (when implemented):

```bash
# Paper trading
TRADING_MODE=paper uv run python -m apps.trader.main --config config/strategies/btc_ml_strategy.yaml

# Live trading
TRADING_MODE=live uv run python -m apps.trader.main --config config/strategies/btc_ml_strategy.yaml
```

#### **Backtester** 📋 (Planned - Priority 2)

**Purpose**: Simulate trades using historical data

**Architecture**:

```
Database (historical candles) → Strategy (same code as trader) → Simulated Execution → Report
```

**Key Features**:

- Uses **exact same strategy code** as live trader
- Fast-forward replay (days in seconds)
- Simulated fills with configurable slippage
- Performance metrics: win rate, profit factor, Sharpe ratio

**Data Source**: SQLite database (populated by backfiller)

**Entry Point**: `apps/backtester/main.py`

**Usage** (when implemented):

```bash
uv run python -m apps.backtester.main \
  --config config/strategies/btc_ml_strategy.yaml \
  --start 2026-01-01 \
  --end 2026-01-27
```

### Strategy Plugin System

**Goal**: Add new strategies without modifying core code.

**How it Works**:

1. **Define Strategy** (Python class):

   ```python
   # packages/strategies/conventional/my_strategy.py

   class MyStrategy(BaseStrategy):
       def on_candle(self, candle, timeframe):
           # Generate signals from technical, ML, orderbook
           signals = self.generate_signals()
           return self.aggregator.aggregate(signals)
   ```

2. **Configure Strategy** (YAML):

   ```yaml
   # config/strategies/my_strategy.yaml

   strategy:
     id: "my-strategy-001"
     name: "My Strategy"
     class: "MyStrategy" # Python class name

   market:
     exchange: "mexc"
     symbol: "BTC/USDT"
     primary_timeframe: "1m"

   parameters:
     # Strategy-specific parameters
   ```

3. **Run Strategy**:
   ```bash
   uv run python -m apps.trader.main --config config/strategies/my_strategy.yaml
   ```

**Strategy automatically loaded** via `StrategyLoader` - no core code changes needed!

### Signal Framework

Strategies generate **Signal objects** (not simple strings):

```python
@dataclass
class Signal:
    type: SignalType          # BUY, SELL, CLOSE, PARTIAL_CLOSE
    source: SignalSource      # TECHNICAL, ML_MODEL, ORDERBOOK
    confidence: float         # 0.0 to 1.0
    reason: str               # Human-readable explanation
    metadata: dict            # Additional context
    close_percentage: float   # For partial closes (0.5 = 50%)
```

**Signal Sources**:

1. **Technical**: RSI, MACD, Bollinger Bands, True VWAP
2. **ML Model**: LSTM/RandomForest/XGBoost predictions
3. **Order Book**: Bid/ask imbalance, liquidity analysis

**Signal Aggregation**:

- **Voting**: Majority wins
- **Weighted**: Confidence-weighted average
- **Unanimous**: All sources must agree
- **Threshold**: Must exceed confidence threshold (e.g., 0.6)

**Example**:

```
Technical Signal: BUY (confidence 0.75) - "RSI oversold at 28.5"
ML Signal:        BUY (confidence 0.82) - "LSTM predicts 2.5% upward movement"
OrderBook Signal: BUY (confidence 0.68) - "68% bid dominance"

Aggregated Signal: BUY (confidence 0.75) - Weighted average exceeds threshold ✓
```

### Complex Exit Management

Exit conditions can be arbitrarily complex:

1. **Stop Loss**: Fixed percentage (e.g., -1%)
2. **Take Profit**: Tiered levels (e.g., 33% @ +2%, 33% @ +4%, 34% @ +6%)
3. **Trailing Stop**: Dynamic (e.g., trail by 0.5% from highest price)
4. **Time-Based**: Exit after X minutes if no profit
5. **ML-Based**: Exit when ML model predicts reversal

**Example Exit Flow**:

```
Entry: $42,165.75 (0.0475 BTC)
  ↓
Price reaches +2% → Close 33% (0.0157 BTC) ✓
  ↓
Price reaches +4% → Close 33% (0.0157 BTC) ✓
  ↓
Price reaches +6% → Close remaining 34% (0.0161 BTC) ✓

Total PNL: +$79.02 (+3.95%)
```

### Multi-Timeframe Support

Strategies can analyze **any number of timeframes** simultaneously:

```yaml
market:
  primary_timeframe: "1m" # Execution timeframe
  timeframes:
    - "1m" # Ultra-short term
    - "5m" # Short term
    - "15m" # Medium term
    - "1h" # Long term
```

**No hardcoded "HTF" or "LTF"** - fully dynamic!

Strategy receives candles tagged with their timeframe:

```python
def on_candle(self, candle, timeframe):
    if timeframe == "1m":
        # Primary timeframe - check for entry
    elif timeframe == "5m":
        # Confirmation timeframe - validate trend
```

### Machine Learning Integration

**Training Pipeline**:

1. **Data Loading** - Rolling window from database (last 30 days)
2. **Feature Engineering** - 60+ features (RSI, MACD, lags, VWAP, time)
3. **Model Training** - LSTM/RandomForest/XGBoost
4. **Evaluation** - Backtest on validation set, calculate metrics
5. **Deployment** - Hot-swap if better than current model

**Continuous Learning**:

- Daily retraining on rolling 30-day window
- Database automatically includes historical + live data
- Models adapt to changing market conditions
- Versioning tracks performance over time

**Usage in Strategies**:

```python
class MLStrategy(BaseStrategy):
    def __init__(self, config):
        super().__init__(config)
        self.ml_generator = MLSignalGenerator(config['ml'])

    def generate_signals(self):
        # ML predictions as signals
        ml_signals = self.ml_generator.generate({'history': self.history})
        return ml_signals
```

### True VWAP (Trades Stream)

**Traditional VWAP** (from OHLCV):

```
Uses candle typical price: (high + low + close) / 3 × volume
```

**True VWAP** (from trades):

```
Uses actual trade executions: Σ(trade_price × trade_volume) / Σ(trade_volume)
```

**Why Better?**

- Institutional-grade accuracy
- Reflects actual market participant behavior
- Better support/resistance levels
- Real-time updates with every trade

**Implementation**:

```python
from packages.indicators.conventional.vwap_true.main import TrueVWAP

vwap_calc = TrueVWAP(db_connection)
vwap = vwap_calc.calculate(
    exchange="mexc",
    symbol="BTC/USDT",
    window_type="session"  # or "rolling", "anchored"
)
```

**Data Source**: `trades_data` table (populated by WebSocket)

### Monitoring & Visualization

**Grafana + Prometheus Architecture**:

```
WebSocket → Database → Grafana (historical SQL queries)
    ↓
  Prometheus → Grafana (live metrics, sub-second updates)
```

**Dual-Path Design**:

- **Live Metrics** (Prometheus): 500ms-1s refresh
  - Current price, volume, trades/sec
  - Current forming candle (OHLCV updates in real-time)
  - Order book depth (20 levels with cumulative quantities)
- **Historical Data** (Database): 5s refresh
  - Candlestick charts
  - Completed candles

**Dashboard Panels**:

1. Live price + volume
2. Trade flow visualization
3. Unified candlestick chart (historical + live)
4. Order book depth chart (green bids, red asks, cumulative)

**Setup**: See [docs/GRAFANA_PROMETHEUS.md](docs/GRAFANA_PROMETHEUS.md)

### Docker Deployment

Each Docker container runs **one strategy instance**:

```yaml
# docker-compose.yml

services:
  # Live trading - BTC 1m scalper
  trader-btc-live:
    command: python -m apps.trader.main
    environment:
      TRADING_MODE: "live"
      STRATEGY_CONFIG: "btc_scalper.yaml"
    volumes:
      - ./data:/app/data # Shared database
      - ./logs:/app/logs

  # Paper trading - ETH momentum
  trader-eth-paper:
    command: python -m apps.trader.main
    environment:
      TRADING_MODE: "paper"
      STRATEGY_CONFIG: "eth_momentum.yaml"
    volumes:
      - ./data:/app/data # Same database
      - ./logs:/app/logs

  # ML training service
  ml-trainer:
    command: python scripts/continuous_training.py
    volumes:
      - ./data:/app/data # Read training data
      - ./models:/app/models # Write trained models

  # Monitoring stack
  prometheus:
    image: prom/prometheus
    ports: ["9090:9090"]

  pushgateway:
    image: prom/pushgateway
    ports: ["9091:9091"]

  grafana:
    image: grafana/grafana
    ports: ["3000:3000"]
```

**Shared Resources**:

- Database: `/app/data/trading.db` (mounted volume)
- Logs: `/app/logs/` (mounted volume)
- API Keys: `.env` file (shared secrets)

**Horizontal Scaling**: Add new strategy = add new service in docker-compose.yml

## 📦 Packages (Reusable Modules)├── schema.py # Database table initialization

├── pyproject.toml # Dependencies (managed by uv)
├── docker-compose.yml # Container orchestration
└── README.md # This file

````

## 📦 Packages (Reusable Modules)

#### ✅ **Database** (`packages/database/`)
- SQLite connection management with WAL mode
- Query helpers for OHLCV, gaps, metadata
- Concurrent read/write support
- Used by: All applications

#### ✅ **Logging** (`packages/logging/`)
- Structured logging with timestamps
- File output (`logs/`) + console output
- Module-level loggers
- Used by: All applications

#### ✅ **WebSocket** (`packages/websocket/`)
- Real-time market data streaming via CCXT Pro
- **OHLCV updates**: 1m candles forming in real-time
- **Ticker updates**: Best bid/ask, volume
- **Order Book depth**: Top 10,000 bid/ask levels
- **Trade stream**: Individual executions for True VWAP calculation
- Stores in same tables as REST data (unified layer)
- Used by: Trader (live/paper)
- Documentation: [WEBSOCKET.md](docs/WEBSOCKET.md), [ORDERBOOK.md](docs/ORDERBOOK.md)

#### 🚧 **Execution** (`packages/execution/`) - Priority 1
- Order placement and management
- Position tracking (entry price, size, PNL)
- Live vs paper mode switching (`set_sandbox_mode`)
- Order lifecycle: pending → filled → closed
- Used by: Trader
- Documentation: [TRADER_ARCHITECTURE.md](docs/TRADER_ARCHITECTURE.md#step-3-order-execution)

#### 🚧 **Strategies** (`packages/strategies/`) - Priority 1
- **Base Strategy**: Abstract class with signal framework
- **Strategy Loader**: Dynamic loading from YAML
- **Conventional Strategies**: Pre-built (RSI, MACD, VWAP, etc.)
- **Custom Strategies**: User-defined
- Supports multi-timeframe analysis
- Used by: Trader, Backtester
- Documentation: [TRADER_ARCHITECTURE.md](docs/TRADER_ARCHITECTURE.md#strategy-plugin-architecture)

#### 🚧 **Signals** (`packages/signals/`) - Priority 1
- **Signal Types**: BUY, SELL, CLOSE, PARTIAL_CLOSE
- **Signal Sources**: Technical, ML Model, Order Book
- **Signal Aggregator**: Voting, weighted, unanimous modes
- **Exit Manager**: Tiered TP, trailing stops, time-based, ML-based
- Rich metadata (confidence, reasoning, context)
- Used by: Strategies
- Documentation: [TRADER_ARCHITECTURE.md](docs/TRADER_ARCHITECTURE.md#signal-framework)

#### 🚧 **Indicators** (`packages/indicators/`) - Priority 2
- **Conventional**: RSI, MACD, Bollinger Bands, SMA, EMA, True VWAP
- **ML-Based**: ARIMA, LSTM predictions
- **True VWAP**: Calculate from trades stream (not OHLCV approximation)
- Cached calculations in `indicator_cache` table
- Used by: Strategies, ML feature engineering
- Documentation: [TRADER_ARCHITECTURE.md](docs/TRADER_ARCHITECTURE.md#true-vwap-using-trades-stream)

#### 🚧 **ML** (`packages/ml/`) - Priority 3
- **Data Loader**: Rolling window from database (historical + live)
- **Feature Engineering**: 60+ features (technical, lags, VWAP, time)
- **Models**: LSTM, Random Forest, XGBoost
- **Evaluation**: Backtest metrics, profit factor, Sharpe ratio
- **Deployment**: Model versioning, hot-swap, continuous learning
- Used by: ML training service, ML signal generator
- Documentation: [TRADER_ARCHITECTURE.md](docs/TRADER_ARCHITECTURE.md#ml-model-training-pipeline)

#### 🚧 **Prometheus** (`packages/prometheus/`) - Priority 4
- Push metrics to Prometheus Pushgateway
- Live price, volume, trades/sec
- Current forming candle (OHLCV in real-time)
- Order book depth (20 levels, cumulative)
- Strategy metrics (position, PNL, signals)
- Used by: Trader
- Documentation: [GRAFANA_PROMETHEUS.md](docs/GRAFANA_PROMETHEUS.md)

#### 📋 **Exchange** (`packages/exchange/`) - Future
- CCXT abstraction layer
- Unified interface for 100+ exchanges
- Rate limiting, error handling
- Used by: Execution manager

#### 📋 **Core** (`packages/core/`) - Future
- Central orchestration logic
- Coordinates packages
- Used by: Trader

## 🚀 Quick Start & Usage

## 🚀 Quick Start & Usage

### Prerequisites

- Python 3.12+
- [UV](https://github.com/astral-sh/uv) package manager
- Exchange API keys (optional for public data)

### Setup

```bash
# 1. Install dependencies
cd simple-bot
uv sync

# 2. Configure environment (optional for authenticated access)
cp .env.example .env
nano .env  # Add your API keys

# 3. Initialize database
uv run python schema.py
````

### Current Workflow (Data Collection)

#### 1. Collect Historical Data

```bash
# Single symbol/timeframe
uv run python -m apps.backfiller.main --symbol BTC/USDT --timeframe 1h

# Multi-symbol automation (5 symbols × 6 timeframes)
uv run python scripts/populate_db.py
# Backfills: BTC, ETH, BNB, SOL, XRP (all /USDT)
# Timeframes: 1m, 5m, 15m, 1h, 4h, 1d
```

#### 2. Test Real-Time Streaming

```bash
# 30-second WebSocket validation
uv run python scripts/test_websocket.py

# Shows:
# - Live 1m candle updates (OHLCV forming in real-time)
# - Price movements (ticker)
# - Order book depth (10,000 levels)
# - Individual trade flow
```

#### 3. Verify Database

```bash
# Check database size
ls -lh data/trading.db

# Count records
sqlite3 data/trading.db "SELECT COUNT(*) FROM ohlcv_data;"
sqlite3 data/trading.db "SELECT COUNT(*) FROM trades_data;"
sqlite3 data/trading.db "SELECT COUNT(*) FROM orderbook_data;"
```

### Future Workflow (When Implemented)

#### 1. Train ML Model

```bash
# Train LSTM model on last 30 days
uv run python scripts/train_model.py \
  --config config/ml/btc_lstm_config.yaml \
  --mode train

# Evaluate model
uv run python scripts/train_model.py \
  --config config/ml/btc_lstm_config.yaml \
  --mode evaluate

# Deploy to production
uv run python scripts/train_model.py \
  --config config/ml/btc_lstm_config.yaml \
  --mode deploy
```

#### 2. Backtest Strategy

```bash
# Test strategy on historical data
uv run python -m apps.backtester.main \
  --config config/strategies/btc_ml_strategy.yaml \
  --start 2026-01-01 \
  --end 2026-01-27

# Output:
# - Win rate, profit factor, Sharpe ratio
# - Trade-by-trade log
# - PNL chart
```

#### 3. Paper Trade

```bash
# Test with live data, simulated orders (MEXC sandbox)
TRADING_MODE=paper uv run python -m apps.trader.main \
  --config config/strategies/btc_ml_strategy.yaml

# Monitor logs
tail -f logs/trader.log
```

#### 4. Live Trade

```bash
# ⚠️ REAL MONEY - Test thoroughly first!
TRADING_MODE=live uv run python -m apps.trader.main \
  --config config/strategies/btc_ml_strategy.yaml

# Monitor in real-time
docker compose logs -f trader-btc-live
```

#### 5. Run Multiple Strategies (Docker)

```bash
# Start all services
docker compose up -d

# Services:
# - trader-btc-live (live trading)
# - trader-eth-paper (paper trading)
# - ml-trainer (continuous learning)
# - prometheus (metrics)
# - grafana (dashboard)

# View dashboard
open http://localhost:3000

# Check logs
docker compose logs -f trader-btc-live
docker compose logs -f ml-trainer
```

## ⚙️ Configuration

## ⚙️ Configuration

### Environment Variables (`.env`)

```bash
# Exchange API Keys
MEXC_API_KEY=your_key
MEXC_API_SECRET=your_secret

BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret

# System
DATABASE_PATH=data/trading.db
LOG_LEVEL=INFO
```

### Strategy Configuration (YAML)

**Simple Technical Strategy**:

```yaml
# config/strategies/btc_rsi_strategy.yaml

strategy:
  id: "btc-rsi-001"
  name: "BTC RSI Mean Reversion"
  class: "RSIMeanReversion"

market:
  exchange: "mexc"
  symbol: "BTC/USDT"
  primary_timeframe: "1m"

parameters:
  rsi_period: 14
  rsi_oversold: 30
  rsi_overbought: 70
  position_size_pct: 2.0

exits:
  stop_loss_pct: 1.0
  take_profit_pct: 2.0
```

**Complex ML Strategy**:

```yaml
# config/strategies/btc_ml_strategy.yaml

strategy:
  id: "btc-ml-001"
  name: "BTC ML Multi-Signal"
  class: "ComplexMLStrategy"
  aggregation_mode: "weighted"
  signal_threshold: 0.6

market:
  exchange: "mexc"
  symbol: "BTC/USDT"
  primary_timeframe: "1m"
  timeframes: ["1m", "5m", "15m"]

# Technical signals
technical:
  rsi_period: 14
  rsi_oversold: 30
  rsi_overbought: 70

# ML model
ml:
  enabled: true
  model_path: "models/btc_lstm_v1.pkl"
  feature_pipeline_path: "models/feature_pipeline.pkl"

# Order book signals
orderbook:
  enabled: true
  imbalance_threshold: 0.65

# Complex exits
exits:
  stop_loss_pct: 1.0
  take_profit_levels:
    - target_pct: 2.0
      close_pct: 0.33
    - target_pct: 4.0
      close_pct: 0.33
    - target_pct: 6.0
      close_pct: 0.34
  max_hold_time_minutes: 60
  trailing_stop_pct: 0.5
```

**ML Training Configuration**:

```yaml
# config/ml/btc_lstm_config.yaml

training:
  model_name: "btc_lstm"
  model_type: "lstm"

data:
  exchange: "mexc"
  symbol: "BTC/USDT"
  timeframe: "1m"
  window_size_days: 30
  rolling_update: true
  update_frequency: "daily"

features:
  technical_indicators:
    - name: "RSI"
      params: { period: 14 }
    - name: "MACD"
      params: { fast: 12, slow: 26, signal: 9 }

  vwap_features:
    - name: "session_vwap"
      window_type: "session"
    - name: "rolling_vwap_60m"
      window_type: "rolling"
      window_minutes: 60

  lag_features:
    periods: [1, 5, 10, 20, 60]

target:
  type: "price_direction"
  lookahead_periods: 5
  threshold_pct: 0.5

model:
  lstm:
    layers: [128, 64, 32]
    dropout: 0.2
    batch_size: 64
    epochs: 100
```

See [TRADER_ARCHITECTURE.md](docs/TRADER_ARCHITECTURE.md) for complete configuration examples.

## 📊 Database Schema

### Core Tables

**Market Data** (shared across all strategies):

- `ohlcv_data` - Historical OHLCV candles
- `ticker_data` - Real-time ticker updates
- `orderbook_data` - Order book depth snapshots
- `trades_data` - Individual trade executions (for True VWAP)

**Strategy-Specific** (isolated by strategy_id):

- `strategy_metadata` - Strategy configurations
- `trades` - Executed trades with PNL
- `positions` - Current positions
- `signals` - Trading signals with metadata

**Performance & Caching**:

- `indicator_cache` - Cached indicator calculations
- `unfillable_gaps` - Tracked data gaps from exchange outages

**Key Features**:

- WAL mode for concurrent read/write
- Composite keys for efficient querying
- ~218 MB with 1M+ candles (30 symbol/timeframe combos)

See [DATABASE.md](docs/DATABASE.md) for complete schema.

## 📚 Documentation

**Core Documentation**:

- **[TRADER_ARCHITECTURE.md](docs/TRADER_ARCHITECTURE.md)** - 🎯 **Complete architecture design** (read this first!)
  - Runtime modes (live, paper, backtest)
  - Strategy plugin system
  - Signal framework (technical, ML, orderbook)
  - Complex exit management
  - Multi-timeframe support
  - ML training pipeline
  - True VWAP calculation
  - Complete working examples

- **[GRAFANA_PROMETHEUS.md](docs/GRAFANA_PROMETHEUS.md)** - Dashboard & monitoring setup
  - Dual-path architecture (Prometheus for live, DB for historical)
  - Order book depth chart visualization
  - Sub-second metrics updates

**Data Layer**:

- **[DATABASE.md](docs/DATABASE.md)** - Database schema and strategy
- **[WEBSOCKET.md](docs/WEBSOCKET.md)** - WebSocket integration guide
- **[ORDERBOOK.md](docs/ORDERBOOK.md)** - Order book & trade streaming
- **[DATA_STRATEGY.md](docs/DATA_STRATEGY.md)** - Multi-instance data storage
- **[DATA_FLOW.md](docs/DATA_FLOW.md)** - REST vs WebSocket comparison
- **[DATA_SUMMARY.md](docs/DATA_SUMMARY.md)** - Data handling best practices

**Other**:

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture diagrams
- **[QUICKSTART.md](docs/QUICKSTART.md)** - Quick command reference
- **[AUDIT.md](docs/AUDIT.md)** - Pre-implementation audit

## 🎯 Implementation Roadmap

### Phase 1: Core Trading Runtime (Weeks 1-2)

**Goal**: Get basic live/paper trading working

1. ✅ Database schema - DONE
2. ✅ WebSocket streaming - DONE
3. 🚧 Execution manager (`packages/execution/manager.py`)
   - Order placement via CCXT
   - Position tracking
   - Live vs paper mode switching
4. 🚧 Base strategy class (`packages/strategies/base.py`)
   - Signal framework
   - Multi-timeframe support
   - Position management
5. 🚧 Strategy loader (`packages/strategies/loader.py`)
   - Dynamic YAML loading
   - Class instantiation
6. 🚧 Trading runtime (`apps/trader/runtime.py`)
   - WebSocket → Strategy → Execution loop
   - Error handling and recovery
7. 🚧 Simple strategy (RSI mean reversion)
   - Test end-to-end flow

**Deliverable**: Paper trade RSI strategy on 1m BTC/USDT

### Phase 2: Signal Framework (Week 3)

**Goal**: Support complex strategies with multiple signal sources

1. Signal types and sources (`packages/signals/types.py`)
2. Technical signal generator (`packages/signals/generators/technical.py`)
3. Signal aggregator (`packages/signals/aggregator.py`)
   - Voting, weighted, unanimous modes
4. Exit manager (`packages/signals/exits/manager.py`)
   - Tiered take-profit
   - Trailing stops
   - Time-based exits
5. Multi-timeframe strategy example
6. Test complex entry/exit conditions

**Deliverable**: Multi-timeframe strategy with tiered exits

### Phase 3: Indicators & True VWAP (Week 4)

**Goal**: Build indicator library with True VWAP

1. RSI indicator (`packages/indicators/conventional/rsi/`)
2. MACD indicator (`packages/indicators/conventional/macd/`)
3. Bollinger Bands (`packages/indicators/conventional/bollinger_bands/`)
4. True VWAP (`packages/indicators/conventional/vwap_true/`)
   - Session, rolling, anchored windows
   - VWAP bands (2σ)
5. VWAP mean reversion strategy
6. Test True VWAP vs traditional VWAP

**Deliverable**: True VWAP strategy in paper mode

### Phase 4: ML Integration (Weeks 5-6)

**Goal**: Train and deploy ML models in strategies

1. Data loader (`packages/ml/data_loader.py`)
   - Rolling window loading
2. Feature engineering (`packages/ml/feature_engineering.py`)
   - Technical indicators
   - True VWAP features
   - Lag features
3. LSTM model (`packages/ml/models/lstm.py`)
4. Model evaluation (`packages/ml/evaluation.py`)
   - Backtest on validation set
5. Model deployment (`packages/ml/deployment.py`)
   - Versioning and hot-swap
6. ML signal generator (`packages/signals/generators/ml.py`)
7. Train initial model
8. Complex ML strategy (technical + ML + orderbook)

**Deliverable**: Live ML strategy with daily retraining

### Phase 5: Monitoring & Visualization (Week 7)

**Goal**: Deploy Grafana dashboard with live metrics

1. Prometheus metrics (`packages/prometheus/metrics.py`)
2. Docker Compose setup (Prometheus + Pushgateway + Grafana)
3. Grafana dashboard JSON
4. Order book depth chart
5. Live metrics row
6. Trade flow visualization

**Deliverable**: Real-time dashboard with sub-second updates

### Phase 6: Backtester & Validation (Week 8)

**Goal**: Validate strategies before live deployment

1. Backtester app (`apps/backtester/main.py`)
   - Historical replay
   - Same strategy code as trader
2. Simulated execution
   - Configurable slippage
   - Realistic fills
3. Performance metrics
   - Win rate, profit factor, Sharpe ratio
   - Trade-by-trade analysis
4. Backtest all strategies
5. Optimize parameters

**Deliverable**: Validated strategies with backtest reports

### Phase 7: Production Deployment (Week 9+)

**Goal**: Deploy to production with real capital

1. Docker multi-instance setup
2. Start with paper trading (1-2 weeks validation)
3. Deploy first live strategy (small capital)
4. Monitor performance
5. Gradually scale up
6. Add more strategies

**Deliverable**: Live trading bot in production

## 🛠️ Development

### Adding Dependencies

```bash
# Production
uv add pandas numpy scikit-learn torch

# Development
uv add --dev pytest black ruff mypy
```

### Code Quality

```bash
# Format
uv run black apps/ packages/ config/

# Type checking
uv run mypy apps/ packages/

# Linting
uv run ruff check apps/ packages/
```

### Testing

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=packages --cov=apps
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
- Check disk space if database growing
- WAL mode handles concurrent access automatically

**WebSocket Connection Errors**

- Check network connectivity
- Verify exchange supports WebSocket (CCXT Pro)
- Some exchanges require API keys for WebSocket

**ML Training Errors**

- Ensure sufficient historical data (30+ days recommended)
- Check GPU availability for LSTM training
- Monitor memory usage with large datasets

## ⚠️ Safety & Best Practices

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
